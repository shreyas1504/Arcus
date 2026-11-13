"""Build the Scenario Lab event library from the raw snapshot (PLAN.md Step 2).

    python -m scenario.build_library                  # scenario/raw -> scenario/assets
    python -m scenario.build_library --raw DIR --out DIR

Inputs: scenario/raw (scenario.data snapshot, SHA256-checked) and scenario/events/*.jsonl.
Outputs (layout in scenario/ASSETS.md): library.npz, factor_history.npz, library.json,
and scenario/eval/build_report.md listing events that failed the date check.

Data rules
- The trading calendar is SPY's own bar dates.
- ETFs use Adj Close (total return). Brent and the 10-year yield come from FRED on
  their own calendars; each SPY date takes the latest FRED observation at most
  STALE_DAYS calendar days old (a holiday print), otherwise NaN. Nothing is
  interpolated and nothing is invented.
- Paths: t = 0 is the close on day -1; t = k the close of the k-th trading day from
  day 0. ETFs and Brent are cumulative simple returns, DGS10_CHG is the change in
  percentage points. Days not yet observed are NaN.
- Context is read at the close on day -1.
- Date check, over SPY and the event's sector ETFs, with z = daily return / the
  standard deviation of the 60 daily returns ending on day -2 (day -1 stays out):
    "date_check_quiet"   no single-day |z| above QUIET_Z on day 0, +1 or +2
    "date_check_earlier" day -1 has |z| >= EARLIER_Z and >= EARLIER_RATIO x the
                         largest |z| on days 0..+2 (the news may have been out a day early)
  Single days are used, not the 3-day net move, because a big day-0 move followed by
  a reversal (the 2001 surprise Fed cut, the 2010 flash crash) nets out to nothing.
  Flags are for a human to review; the build never changes or drops an event.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from scenario.enums import (
    FACTOR_NAMES,
    FACTOR_OIL,
    FACTOR_RATES,
    FACTOR_SEMIS,
    FACTOR_SPY,
    RECOVERY_DAYS,
    SECTOR_ETF,
)
from scenario.schemas import Event

ROOT = Path(__file__).resolve().parent
EVENTS_DIR = ROOT / "events"
ASSETS_DIR = ROOT / "assets"
REPORT_PATH = ROOT / "eval" / "build_report.md"

LIBRARY_VERSION = 1
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
CONTEXT_NAMES = ("vix", "baa10y", "gpr", "gpr_rise_5d")
STALE_DAYS = 5
QUIET_Z = 1.5
EARLIER_Z = 3.0
EARLIER_RATIO = 1.5
VOL_WINDOW = 60
SIZE_BUDGET_BYTES = 15 * 1024 * 1024
ETF_NAMES = tuple(n for n in FACTOR_NAMES if n not in (FACTOR_RATES, FACTOR_OIL))


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class BuiltLibrary:
    events: list[Event]
    embeddings: np.ndarray  # (n, d) float32
    factor_paths: np.ndarray  # (n, RECOVERY_DAYS + 1, F) float32
    context: np.ndarray  # (n, 4) float32
    history_dates: np.ndarray  # (T,) int32 yyyymmdd
    history_returns: np.ndarray  # (T, F) float32
    flags: dict[str, list[str]]
    checks: dict[str, dict]  # date-check details per event id


# --------------------------------------------------------------------------- inputs


def load_events(events_dir: Path = EVENTS_DIR) -> list[Event]:
    events = [
        Event.model_validate_json(line)
        for path in sorted(events_dir.glob("*.jsonl"))
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    if len({e.id for e in events}) != len(events):
        raise BuildError("duplicate event ids")
    return sorted(events, key=lambda e: (e.date, e.id))


def embedding_text(event: Event) -> str:
    return f"{event.trigger} {event.name} {event.category.value.replace('_', ' ')}"


def _asof(series: pd.Series, calendar: pd.DatetimeIndex) -> pd.Series:
    """Latest observation at or before each calendar date, at most STALE_DAYS old."""
    clean = series.dropna().sort_index()
    if clean.empty:
        return pd.Series(np.nan, index=calendar)
    left = pd.DataFrame({"date": calendar})
    right = pd.DataFrame({"date": clean.index, "value": clean.to_numpy(dtype=float)})
    merged = pd.merge_asof(
        left, right, on="date", direction="backward", tolerance=pd.Timedelta(days=STALE_DAYS)
    )
    return pd.Series(merged["value"].to_numpy(), index=calendar)


def levels_from_frames(frames: Mapping[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(factor levels, context levels), both on SPY's calendar."""
    calendar = pd.DatetimeIndex(frames[FACTOR_SPY].dropna(subset=["Adj Close"]).index).normalize()
    levels = pd.DataFrame(index=calendar)
    for name in ETF_NAMES:
        adj = frames[name]["Adj Close"].copy()
        adj.index = pd.DatetimeIndex(adj.index).normalize()
        levels[name] = adj.reindex(calendar)
    brent = frames["DCOILBRENTEU"]["DCOILBRENTEU"]
    if (brent.dropna() <= 0).any():
        raise BuildError("Brent has non-positive prices")
    levels[FACTOR_OIL] = _asof(brent, calendar)
    levels[FACTOR_RATES] = _asof(frames["DGS10"]["DGS10"], calendar)

    gpr = frames["GPR_DAILY"]["GPRD"]
    context = pd.DataFrame(
        {
            "vix": _asof(frames["VIXCLS"]["VIXCLS"], calendar),
            "baa10y": _asof(frames["BAA10Y"]["BAA10Y"], calendar),
            "gpr": _asof(gpr, calendar),
        },
        index=calendar,
    )
    context["gpr_rise_5d"] = context["gpr"] - context["gpr"].shift(5)
    return levels[list(FACTOR_NAMES)], context


def daily_returns(levels: pd.DataFrame) -> pd.DataFrame:
    out = levels.pct_change(fill_method=None)
    out[FACTOR_RATES] = levels[FACTOR_RATES].diff()
    return out


# --------------------------------------------------------------------------- per event


def event_paths(levels: pd.DataFrame, start_pos: int, horizon: int = RECOVERY_DAYS) -> np.ndarray:
    """(horizon + 1, F) cumulative paths from calendar row `start_pos` (the day -1 close)."""
    window = levels.iloc[start_pos : start_pos + horizon + 1].to_numpy(dtype=float)
    out = np.full((horizon + 1, levels.shape[1]), np.nan)
    base = window[0]
    rates = list(levels.columns).index(FACTOR_RATES)
    with np.errstate(invalid="ignore", divide="ignore"):
        rel = window / base - 1.0
    rel[:, rates] = window[:, rates] - base[rates]
    out[: len(window)] = rel
    return out


def date_check(returns: pd.DataFrame, start_pos: int, etfs: Sequence[str]) -> dict:
    """Single-day reactions around an event; `start_pos` is the day -1 row of `returns`."""
    series = {}
    for name in dict.fromkeys([FACTOR_SPY, *etfs]):
        col = returns[name]
        trailing = col.iloc[max(0, start_pos - VOL_WINDOW) : start_pos].dropna()
        days = [start_pos + k for k in (1, 2, 3) if start_pos + k < len(col)]
        if len(trailing) < VOL_WINDOW // 2 or not days or float(trailing.std()) <= 0:
            series[name] = None
            continue
        sd = float(trailing.std())
        after = [abs(float(col.iloc[i])) / sd for i in days if np.isfinite(col.iloc[i])]
        before = float(col.iloc[start_pos])
        if not after or not np.isfinite(before):
            series[name] = None
            continue
        series[name] = {"z_before": round(abs(before) / sd, 2), "z_after": round(max(after), 2)}
    measured = [d for d in series.values() if d is not None]
    z_after = max((d["z_after"] for d in measured), default=None)
    z_before = max((d["z_before"] for d in measured), default=None)
    return {
        "measurable": bool(measured),
        "quiet": z_after is not None and z_after <= QUIET_Z,
        "earlier": z_before is not None and z_before >= EARLIER_Z and z_before >= EARLIER_RATIO * z_after,
        "z_after": z_after,
        "z_before": z_before,
        "series": series,
    }


def build(
    frames: Mapping[str, pd.DataFrame],
    events: Sequence[Event],
    embed: Callable[[list[str]], np.ndarray],
) -> BuiltLibrary:
    levels, context_levels = levels_from_frames(frames)
    returns = daily_returns(levels)
    calendar = levels.index
    positions = {d: i for i, d in enumerate(calendar)}

    paths, contexts, flags, checks = [], [], {}, {}
    for event in events:
        day0 = pd.Timestamp(event.date)
        if day0 not in positions:
            raise BuildError(f"{event.id}: {event.date} is not an SPY trading day")
        start = positions[day0] - 1
        if start < 0:
            raise BuildError(f"{event.id}: no close before {event.date}")
        path = event_paths(levels, start)
        paths.append(path)
        contexts.append(context_levels.iloc[start][list(CONTEXT_NAMES)].to_numpy(dtype=float))

        event_flags = []
        if not np.isfinite(path[0, list(FACTOR_NAMES).index(FACTOR_SEMIS)]):
            event_flags.append("semis_proxy")
        etfs = [SECTOR_ETF[s] for s in event.sectors if SECTOR_ETF[s] != FACTOR_SPY]
        check = date_check(returns, start, etfs)
        checks[event.id] = check
        if check["quiet"]:
            event_flags.append("date_check_quiet")
        if check["earlier"]:
            event_flags.append("date_check_earlier")
        if not check["measurable"]:
            event_flags.append("date_check_unmeasurable")
        if event_flags:
            flags[event.id] = event_flags

    vectors = np.asarray(embed([embedding_text(e) for e in events]), dtype=np.float32)
    if vectors.shape[0] != len(events):
        raise BuildError("embedder returned the wrong number of vectors")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.maximum(norms, 1e-12)

    history = returns.iloc[1:]
    return BuiltLibrary(
        events=list(events),
        embeddings=vectors.astype(np.float32),
        factor_paths=np.asarray(paths, dtype=np.float32),
        context=np.asarray(contexts, dtype=np.float32),
        history_dates=np.asarray(history.index.strftime("%Y%m%d").astype(int), dtype=np.int32),
        history_returns=history.to_numpy(dtype=np.float32),
        flags=flags,
        checks=checks,
    )


# --------------------------------------------------------------------------- output


def _write_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    """np.savez with fixed zip timestamps, so identical inputs give identical bytes."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, array in arrays.items():
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, np.ascontiguousarray(array), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, buffer.getvalue())


def write(library: BuiltLibrary, out_dir: Path, *, manifest_sha256: str) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_npz(
        out_dir / "library.npz",
        {"embeddings": library.embeddings, "factor_paths": library.factor_paths, "context": library.context},
    )
    _write_npz(
        out_dir / "factor_history.npz",
        {"dates": library.history_dates, "returns": library.history_returns},
    )
    meta = {
        "version": LIBRARY_VERSION,
        "built_from_manifest_sha256": manifest_sha256,
        "factor_names": list(FACTOR_NAMES),
        "context_names": list(CONTEXT_NAMES),
        "embedding_model": EMBEDDING_MODEL,
        "events": [json.loads(e.model_dump_json()) for e in library.events],
        "flags": {k: library.flags[k] for k in sorted(library.flags)},
    }
    (out_dir / "library.json").write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n")
    size = (out_dir / "library.npz").stat().st_size
    if size > SIZE_BUDGET_BYTES:
        raise BuildError(f"library.npz is {size} bytes, over the {SIZE_BUDGET_BYTES} budget")
    return {
        name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
        for name in ("library.npz", "factor_history.npz", "library.json")
    }


def report(library: BuiltLibrary, hashes: Mapping[str, str]) -> str:
    lines = [
        "# Scenario Lab library build report",
        "",
        f"Events: {len(library.events)}. Library arrays: embeddings {library.embeddings.shape}, "
        f"factor_paths {library.factor_paths.shape}, context {library.context.shape}.",
        "",
        "| File | SHA256 |",
        "|---|---|",
        *[f"| {name} | `{sha}` |" for name, sha in hashes.items()],
        "",
        "## Date check",
        "z = a single day's return divided by the standard deviation of the 60 daily returns "
        "ending on day -2, over SPY and the event's sector ETFs. Flags are for review; the build "
        "never changes or drops an event.",
        "",
        f"### Moved the day before (day -1 |z| >= {EARLIER_Z} and >= {EARLIER_RATIO}x days 0..+2)",
        "The news may have been public a day earlier than the event date. **Check each against its source.**",
        "",
        "| Event | Date | Day -1 |z| | Max |z| days 0..+2 |",
        "|---|---|---|---|",
        *[
            f"| {e.id} | {e.date} | {library.checks[e.id]['z_before']} | {library.checks[e.id]['z_after']} |"
            for e in library.events
            if "date_check_earlier" in library.flags.get(e.id, [])
        ],
        "",
        f"### Quiet (no single-day |z| above {QUIET_Z} on days 0..+2)",
        "The market barely reacted. Usually the date is right and the shock was small or expected; "
        "these events still teach the engine that some shocks don't move markets.",
        "",
        "| Event | Date | Category | Max |z| days 0..+2 |",
        "|---|---|---|---|",
        *[
            f"| {e.id} | {e.date} | {e.category.value} | {library.checks[e.id]['z_after']} |"
            for e in library.events
            if "date_check_quiet" in library.flags.get(e.id, [])
        ],
    ]
    unmeasurable = [e.id for e in library.events if "date_check_unmeasurable" in library.flags.get(e.id, [])]
    proxy = [e.id for e in library.events if "semis_proxy" in library.flags.get(e.id, [])]
    lines += [
        "",
        f"Not measurable (window runs past the data): {', '.join(unmeasurable) or 'none'}.",
        "",
        f"SOXX not yet listed (XLK stands in for semiconductors): {len(proxy)} events.",
        "",
    ]
    return "\n".join(lines)


def load_library(assets_dir: Path = ASSETS_DIR):
    """Read the built assets into engine.Library (the engine's in-memory form)."""
    from scenario.engine import Library

    meta = json.loads((assets_dir / "library.json").read_text())
    if meta["version"] != LIBRARY_VERSION or tuple(meta["factor_names"]) != FACTOR_NAMES:
        raise BuildError("library.json does not match this code's version or factor order")
    events = [Event.model_validate(e) for e in meta["events"]]
    with np.load(assets_dir / "library.npz", allow_pickle=False) as arrays:
        embeddings, factor_paths, context = arrays["embeddings"], arrays["factor_paths"], arrays["context"]
    with np.load(assets_dir / "factor_history.npz", allow_pickle=False) as arrays:
        dates, returns = arrays["dates"], arrays["returns"]
    history = pd.DataFrame(
        returns, index=pd.to_datetime(dates.astype(str), format="%Y%m%d"), columns=list(FACTOR_NAMES)
    )
    return Library(
        events=events,
        embeddings=embeddings,
        factor_names=FACTOR_NAMES,
        factor_paths=factor_paths,
        context=pd.DataFrame(context, index=[e.id for e in events], columns=list(meta["context_names"])),
        factor_history=history,
    )


def main(argv: list[str] | None = None) -> int:
    from research.embedder import shared_embedder
    from scenario import data

    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=data.RAW_DIR)
    parser.add_argument("--out", type=Path, default=ASSETS_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)

    manifest, frames = data.load_snapshot(args.raw)
    manifest_sha = hashlib.sha256((args.raw / data.MANIFEST_NAME).read_bytes()).hexdigest()
    embedder = shared_embedder()
    library = build(frames, load_events(), lambda texts: embedder.encode(texts))
    hashes = write(library, args.out, manifest_sha256=manifest_sha)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report(library, hashes))
    flagged = sum("date_check_quiet" in f for f in library.flags.values())
    print(f"built {len(library.events)} events; {flagged} flagged by the date check; report: {args.report}")
    for name, sha in hashes.items():
        print(f"  {name} {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
