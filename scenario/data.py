"""Download the raw market data snapshot for the event library (PLAN.md Step 2).

    python -m scenario.data                     # 1998-12-01 to today
    python -m scenario.data --end 2026-11-12    # a fixed snapshot

Every file lands in scenario/raw/ (gitignored) with the date range in its name, and
scenario/raw/manifest.json records a SHA256 per file. Nothing is ever filled in: a
download that fails, comes back empty or is stale stops the run with a non-zero exit,
and the manifest is only written when every series succeeded.

Sources
- yfinance daily bars: SPY, the 9 SPDR sector ETFs, SOXX
- FRED CSV endpoint (no key): DGS10, DCOILBRENTEU, VIXCLS, BAA10Y
- Caldara-Iacoviello daily Geopolitical Risk index (matteoiacoviello.com/gpr.htm)
- Baker-Bloom-Davis daily Economic Policy Uncertainty index (policyuncertainty.com)

If downloads fail locally with SSL errors, set SSL_CERT_FILE to certifi's bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from scenario.enums import FACTOR_NAMES, FACTOR_OIL, FACTOR_RATES

RAW_DIR = Path(os.getenv("SCENARIO_RAW_DIR", str(Path(__file__).resolve().parent / "raw")))
MANIFEST_NAME = "manifest.json"
START = date(1998, 12, 1)

YF_TICKERS: tuple[str, ...] = tuple(n for n in FACTOR_NAMES if n not in (FACTOR_RATES, FACTOR_OIL))
FRED_SERIES: tuple[str, ...] = ("DGS10", "DCOILBRENTEU", "VIXCLS", "BAA10Y")
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}&coed={end}"
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.dta"
EPU_URL = "https://www.policyuncertainty.com/media/All_Daily_Policy_Data.csv"

# First bar later than START (fund inception): the Select Sector SPDRs' Yahoo history
# starts 1998-12-22 and SOXX's in July 2001. The check allows these, nothing earlier.
LATE_START: dict[str, date] = {
    **{etf: date(1998, 12, 22) for etf in ("XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB")},
    "SOXX": date(2001, 7, 13),
}
MIN_ROWS = 1000
RETRIES = 3


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class Spec:
    name: str  # series name used by the build
    source: str  # yfinance | fred | gpr | epu
    url: str
    suffix: str
    max_lag_days: int  # the newest row may be at most this many days before `end`


def specs(start: date, end: date) -> list[Spec]:
    out = [
        Spec(t, "yfinance", f"yfinance:{t}", "csv", max_lag_days=7) for t in YF_TICKERS
    ]
    out += [
        Spec(s, "fred", FRED_URL.format(sid=s, start=start, end=end), "csv", max_lag_days=21)
        for s in FRED_SERIES
    ]
    out.append(Spec("GPR_DAILY", "gpr", GPR_URL, "dta", max_lag_days=45))
    out.append(Spec("EPU_DAILY", "epu", EPU_URL, "csv", max_lag_days=45))
    return out


# --------------------------------------------------------------------------- fetchers


def _http_get(url: str) -> bytes:
    import requests

    # requests' default User-Agent: FRED's CDN stalls requests with unfamiliar agents.
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def _fetch_yfinance(ticker: str, start: date, end: date) -> bytes:
    import yfinance as yf

    bars = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),  # yfinance's end is exclusive
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if bars is None or bars.empty:
        raise DownloadError(f"yfinance returned no rows for {ticker}")
    if isinstance(bars.columns, pd.MultiIndex):
        bars = bars.xs(ticker, axis=1, level=-1)
    bars = bars[["Open", "High", "Low", "Close", "Adj Close", "Volume"]]
    bars.index = pd.DatetimeIndex(bars.index).tz_localize(None).normalize()
    bars.index.name = "Date"
    return bars.to_csv(date_format="%Y-%m-%d", float_format="%.10g").encode()


# --------------------------------------------------------------------------- parsing


def read_series(spec: Spec, raw: bytes) -> pd.DataFrame:
    """Parse a raw file into a DataFrame with a sorted, unique DatetimeIndex."""
    if spec.source == "yfinance":
        frame = pd.read_csv(io.BytesIO(raw), index_col="Date", parse_dates=["Date"])
    elif spec.source == "fred":
        frame = pd.read_csv(io.BytesIO(raw), na_values=["."])
        if list(frame.columns) != ["observation_date", spec.name]:
            raise DownloadError(f"FRED {spec.name}: unexpected header {list(frame.columns)}")
        frame = frame.set_index(pd.to_datetime(frame.pop("observation_date")))
    elif spec.source == "gpr":
        frame = pd.read_stata(io.BytesIO(raw))
        if "DAY" not in frame or "GPRD" not in frame:
            raise DownloadError(f"GPR: unexpected columns {list(frame.columns)}")
        frame = frame.set_index(pd.to_datetime(frame.pop("DAY").astype(int).astype(str), format="%Y%m%d"))
    elif spec.source == "epu":
        frame = pd.read_csv(io.BytesIO(raw))
        if list(frame.columns) != ["day", "month", "year", "daily_policy_index"]:
            raise DownloadError(f"EPU: unexpected header {list(frame.columns)}")
        frame.index = pd.to_datetime(frame[["year", "month", "day"]])
        frame = frame[["daily_policy_index"]]
    else:  # pragma: no cover
        raise ValueError(spec.source)
    frame.index.name = "date"
    if not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
        raise DownloadError(f"{spec.name}: dates are not sorted and unique")
    return frame


def check_series(spec: Spec, frame: pd.DataFrame, start: date, end: date) -> dict:
    """Fail loudly on empty, short, late-starting or stale data. Returns coverage facts."""
    values = frame.dropna(how="all")
    if len(values) < MIN_ROWS:
        raise DownloadError(f"{spec.name}: only {len(values)} rows")
    first, last = values.index[0].date(), values.index[-1].date()
    expected_first = max(start, LATE_START.get(spec.name, start))
    if first > expected_first + timedelta(days=10):
        raise DownloadError(f"{spec.name}: first row {first}, expected near {expected_first}")
    if last < end - timedelta(days=spec.max_lag_days):
        raise DownloadError(f"{spec.name}: newest row {last} is stale for end {end}")
    return {"rows": int(len(values)), "first": first.isoformat(), "last": last.isoformat()}


# --------------------------------------------------------------------------- driver


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _with_retries(fn: Callable[[], bytes], label: str) -> bytes:
    error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            return fn()
        except Exception as exc:  # network, HTTP, empty data
            error = exc
            if attempt < RETRIES - 1:
                time.sleep(2 * (attempt + 1))
    raise DownloadError(f"{label}: {error}") from error


def fetch_raw(spec: Spec, start: date, end: date) -> bytes:
    if spec.source == "yfinance":
        return _with_retries(lambda: _fetch_yfinance(spec.name, start, end), spec.name)
    return _with_retries(lambda: _http_get(spec.url), spec.name)


def file_name(spec: Spec, start: date, end: date) -> str:
    return f"{spec.name}_{start.isoformat()}_{end.isoformat()}.{spec.suffix}"


def download_all(
    start: date = START,
    end: date | None = None,
    raw_dir: Path = RAW_DIR,
    *,
    fetch: Callable[[Spec, date, date], bytes] = fetch_raw,
) -> dict:
    """Download every series, check it, and write the files plus manifest.json.

    Raises DownloadError naming every failed series; the manifest is not written then.
    """
    end = end or date.today()
    if end <= start:
        raise ValueError("end must be after start")
    raw_dir.mkdir(parents=True, exist_ok=True)

    entries: dict[str, dict] = {}
    failures: list[str] = []
    for spec in specs(start, end):
        try:
            raw = fetch(spec, start, end)
            coverage = check_series(spec, read_series(spec, raw), start, end)
        except Exception as exc:
            failures.append(f"{spec.name}: {exc}")
            print(f"FAILED {spec.name}: {exc}", file=sys.stderr)
            continue
        name = file_name(spec, start, end)
        tmp = raw_dir / (name + ".part")
        tmp.write_bytes(raw)
        tmp.replace(raw_dir / name)
        entries[spec.name] = {
            "file": name,
            "source": spec.source,
            "url": spec.url,
            "sha256": _sha256(raw),
            "bytes": len(raw),
            **coverage,
        }
        print(f"ok {spec.name}: {coverage['rows']} rows, {coverage['first']} to {coverage['last']}")

    if failures:
        raise DownloadError(f"{len(failures)} series failed; manifest not written:\n  " + "\n  ".join(failures))

    manifest = {
        "version": 1,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "downloaded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "series": entries,
    }
    tmp = raw_dir / (MANIFEST_NAME + ".part")
    tmp.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    tmp.replace(raw_dir / MANIFEST_NAME)
    return manifest


def load_snapshot(raw_dir: Path = RAW_DIR) -> tuple[dict, dict[str, pd.DataFrame]]:
    """Read manifest.json and every series, refusing any file whose SHA256 changed."""
    manifest = json.loads((raw_dir / MANIFEST_NAME).read_text())
    start, end = date.fromisoformat(manifest["start"]), date.fromisoformat(manifest["end"])
    by_name = {s.name: s for s in specs(start, end)}
    frames: dict[str, pd.DataFrame] = {}
    for name, entry in manifest["series"].items():
        raw = (raw_dir / entry["file"]).read_bytes()
        if _sha256(raw) != entry["sha256"]:
            raise DownloadError(f"{entry['file']}: SHA256 does not match manifest.json")
        frames[name] = read_series(by_name[name], raw)
    missing = set(by_name) - set(frames)
    if missing:
        raise DownloadError(f"manifest.json is missing series: {sorted(missing)}")
    return manifest, frames


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--start", type=date.fromisoformat, default=START)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)
    try:
        manifest = download_all(args.start, args.end, args.raw_dir)
    except DownloadError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"wrote {len(manifest['series'])} series and {args.raw_dir / MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
