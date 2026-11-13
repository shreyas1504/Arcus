"""Market data snapshot and library build (PLAN.md Step 2).

C1 covers scenario/data.py: downloads are checked, hashed into manifest.json, and any
failure stops the run without writing a manifest. Every test here is offline: the
network fetch is replaced by synthetic bytes. The library-build tests land in C2.
"""

from __future__ import annotations

import io
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from scenario import data

START = date(2015, 1, 1)
END = date(2020, 12, 31)


def _days(last: date = END) -> pd.DatetimeIndex:
    return pd.bdate_range(START, last)


def _synthetic(spec: data.Spec, last: date = END) -> bytes:
    """Well-formed raw bytes in each source's own format."""
    days = _days(last)
    values = np.linspace(100.0, 120.0, len(days))
    if spec.source == "yfinance":
        frame = pd.DataFrame(
            {"Open": values, "High": values, "Low": values, "Close": values, "Adj Close": values, "Volume": 1000},
            index=pd.Index(days, name="Date"),
        )
        return frame.to_csv(date_format="%Y-%m-%d").encode()
    if spec.source == "fred":
        frame = pd.DataFrame({"observation_date": days.strftime("%Y-%m-%d"), spec.name: values})
        return frame.to_csv(index=False).encode()
    if spec.source == "gpr":
        frame = pd.DataFrame({"DAY": days.strftime("%Y%m%d").astype(int), "GPRD": values})
        buffer = io.BytesIO()
        frame.to_stata(buffer, write_index=False)
        return buffer.getvalue()
    if spec.source == "epu":
        frame = pd.DataFrame(
            {"day": days.day, "month": days.month, "year": days.year, "daily_policy_index": values}
        )
        return frame.to_csv(index=False).encode()
    raise AssertionError(spec.source)


def _fetch_ok(spec, start, end):
    return _synthetic(spec)


def test_specs_cover_every_series():
    names = {s.name for s in data.specs(START, END)}
    assert set(data.YF_TICKERS) == {"SPY", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "SOXX"}
    assert names == set(data.YF_TICKERS) | set(data.FRED_SERIES) | {"GPR_DAILY", "EPU_DAILY"}
    assert set(data.FRED_SERIES) == {"DGS10", "DCOILBRENTEU", "VIXCLS", "BAA10Y"}


def test_download_writes_files_and_manifest(tmp_path):
    manifest = data.download_all(START, END, tmp_path, fetch=_fetch_ok)
    written = json.loads((tmp_path / data.MANIFEST_NAME).read_text())
    assert written["series"] == manifest["series"]
    assert len(written["series"]) == len(data.specs(START, END))
    by_name = {s.name: s for s in data.specs(START, END)}
    for name, entry in written["series"].items():
        raw = (tmp_path / entry["file"]).read_bytes()
        assert entry["sha256"] == data._sha256(raw)
        assert entry["file"] == data.file_name(by_name[name], START, END)  # keyed by date range
        assert entry["first"] == "2015-01-01" and entry["last"] == "2020-12-31"
    assert not list(tmp_path.glob("*.part"))


def test_snapshot_round_trips(tmp_path):
    data.download_all(START, END, tmp_path, fetch=_fetch_ok)
    manifest, frames = data.load_snapshot(tmp_path)
    assert set(frames) == set(manifest["series"])
    assert frames["SPY"].index.is_monotonic_increasing
    assert frames["GPR_DAILY"]["GPRD"].iloc[0] == pytest.approx(100.0)


def test_failed_download_fails_loudly_without_manifest(tmp_path):
    def fetch(spec, start, end):
        if spec.name == "DCOILBRENTEU":
            raise ConnectionError("simulated outage")
        return _synthetic(spec)

    with pytest.raises(data.DownloadError, match="DCOILBRENTEU"):
        data.download_all(START, END, tmp_path, fetch=fetch)
    assert not (tmp_path / data.MANIFEST_NAME).exists()


def test_empty_and_stale_series_are_rejected(tmp_path):
    def stale(spec, start, end):
        if spec.name == "VIXCLS":
            return _synthetic(spec, last=date(2019, 6, 28))  # ends 18 months early
        return _synthetic(spec)

    with pytest.raises(data.DownloadError, match="VIXCLS.*stale"):
        data.download_all(START, END, tmp_path, fetch=stale)

    spy = next(s for s in data.specs(START, END) if s.name == "SPY")
    header_only = b"Date,Open,High,Low,Close,Adj Close,Volume\n"
    with pytest.raises(data.DownloadError, match="rows"):
        data.check_series(spy, data.read_series(spy, header_only), START, END)


def test_missing_values_are_kept_not_filled():
    dgs10 = next(s for s in data.specs(START, END) if s.name == "DGS10")
    lines = _synthetic(dgs10).decode().splitlines()
    assert lines[1].startswith("2015-01-01,")
    lines[2] = lines[2].split(",")[0] + ","  # FRED leaves a holiday blank
    lines[3] = lines[3].split(",")[0] + ",."  # older FRED files use "."
    frame = data.read_series(dgs10, ("\n".join(lines) + "\n").encode())
    assert frame["DGS10"].iloc[1:3].isna().all()
    assert len(frame) == len(lines) - 1  # no rows dropped or added


def test_tampered_file_is_refused(tmp_path):
    data.download_all(START, END, tmp_path, fetch=_fetch_ok)
    entry = json.loads((tmp_path / data.MANIFEST_NAME).read_text())["series"]["SPY"]
    path = tmp_path / entry["file"]
    path.write_bytes(path.read_bytes().replace(b"100", b"101", 1))
    with pytest.raises(data.DownloadError, match="SHA256"):
        data.load_snapshot(tmp_path)


# =========================================================================== library build (C2)

import hashlib
from pathlib import Path

from scenario import build_library as lib_build
from scenario.enums import FACTOR_NAMES
from scenario.schemas import Event

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "scenario"
F = list(FACTOR_NAMES)
FRED_NAMES = ("DGS10", "DCOILBRENTEU", "VIXCLS", "BAA10Y")


def _frames(days: pd.DatetimeIndex, *, seed: int = 0, spy: pd.Series | None = None, **overrides) -> dict:
    """Synthetic snapshot frames in scenario.data's in-memory shapes."""
    rng = np.random.default_rng(seed)
    frames: dict[str, pd.DataFrame] = {}
    for name in lib_build.ETF_NAMES:
        levels = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, len(days))))
        frames[name] = pd.DataFrame({"Adj Close": levels}, index=days)
    if spy is not None:
        frames["SPY"] = pd.DataFrame({"Adj Close": spy.to_numpy()}, index=spy.index)
    frames["DGS10"] = pd.DataFrame({"DGS10": 3 + np.cumsum(rng.normal(0, 0.02, len(days)))}, index=days)
    frames["DCOILBRENTEU"] = pd.DataFrame({"DCOILBRENTEU": 60 * np.exp(np.cumsum(rng.normal(0, 0.01, len(days))))}, index=days)
    frames["VIXCLS"] = pd.DataFrame({"VIXCLS": 20 + rng.normal(0, 1, len(days))}, index=days)
    frames["BAA10Y"] = pd.DataFrame({"BAA10Y": 2 + rng.normal(0, 0.05, len(days))}, index=days)
    frames["GPR_DAILY"] = pd.DataFrame({"GPRD": 100 + rng.normal(0, 5, len(days))}, index=days)
    frames.update(overrides)
    return frames


def _ev(event_id: str, day: str, sectors=("broad",)) -> Event:
    return Event.model_validate(
        {
            "id": event_id, "name": f"Example {event_id}", "date": day, "onset": "sudden", "nature": "adverse",
            "category": "financial_credit", "regions": ["us"], "sectors": list(sectors),
            "trigger": "An example shock happens to an example market today.",
            "source_url": "https://example.com/source",
            "source_quote": "An example quote that is long enough to pass the schema length check.",
            "split": "holdout" if day >= "2023-01-01" else "dev", "drafted_by": "claude",
        }
    )


def _embed(texts: list[str]) -> np.ndarray:
    out = np.zeros((len(texts), 8), dtype=np.float32)
    for i, text in enumerate(texts):
        out[i, int(hashlib.sha256(text.encode()).hexdigest(), 16) % 8] = 1.0
        out[i, len(text) % 8] += 0.5
    return out


DAYS = pd.bdate_range("2015-01-01", "2016-12-30")


def test_build_is_deterministic(tmp_path):
    frames, events = _frames(DAYS), [_ev("a-shock", "2015-06-01"), _ev("b-shock", "2016-02-01")]
    first = lib_build.write(lib_build.build(frames, events, _embed), tmp_path / "one", manifest_sha256="x")
    second = lib_build.write(lib_build.build(frames, events, _embed), tmp_path / "two", manifest_sha256="x")
    assert first == second


def test_paths_start_at_zero_and_masked():
    events = [_ev("late-shock", "2016-12-01")]
    built = lib_build.build(_frames(DAYS), events, _embed)
    paths = built.factor_paths[0]
    assert paths.shape == (lib_build.RECOVERY_DAYS + 1, len(F))
    assert np.all(paths[0] == 0.0)
    observed = int(np.isfinite(paths[:, F.index("SPY")]).sum())
    assert observed == 1 + int((DAYS > pd.Timestamp("2016-12-01")).sum()) + 1  # t=0 (day -1), day 0, later days
    assert np.all(np.isnan(paths[observed:]))


def test_known_value_lehman():
    # SPY Adj Close, from the committed fixture (yfinance, 2026-11 snapshot):
    #   2008-09-12 (day -1) 90.481834 ; 2008-10-13 (t = 21) 73.149475
    #   73.149475 / 90.481834 - 1 = -0.191556
    spy = pd.read_csv(FIXTURES / "spy_2008_adj_close.csv", index_col="date", parse_dates=["date"])["Adj Close"]
    built = lib_build.build(_frames(spy.index, spy=spy), [_ev("lehman-example", "2008-09-15", ("financials",))], _embed)
    assert built.factor_paths[0, 21, F.index("SPY")] == pytest.approx(-0.191556, abs=0.001)


def test_context_is_day_minus_one():
    frames = _frames(DAYS)
    vix = frames["VIXCLS"].copy()
    vix.loc[pd.Timestamp("2015-06-01"), "VIXCLS"] = 99.0  # day 0 must not leak in
    vix.loc[pd.Timestamp("2015-05-29"), "VIXCLS"] = 31.5  # day -1
    frames["VIXCLS"] = vix
    built = lib_build.build(frames, [_ev("a-shock", "2015-06-01")], _embed)
    assert built.context[0, lib_build.CONTEXT_NAMES.index("vix")] == pytest.approx(31.5)


def test_rates_are_point_changes():
    frames = _frames(DAYS)
    rates = pd.Series(3.0, index=DAYS)
    rates[DAYS >= pd.Timestamp("2015-06-01")] = 3.5
    frames["DGS10"] = pd.DataFrame({"DGS10": rates})
    built = lib_build.build(frames, [_ev("a-shock", "2015-06-01")], _embed)
    assert built.factor_paths[0, 1, F.index("DGS10_CHG")] == pytest.approx(0.5)


def test_fred_holiday_carries_last_print_but_long_gap_is_nan():
    frames = _frames(DAYS)
    brent = frames["DCOILBRENTEU"].copy()
    brent.loc[pd.Timestamp("2015-06-02")] = np.nan  # one missing print: last value is used
    brent.loc[pd.Timestamp("2015-07-01") : pd.Timestamp("2015-07-15")] = np.nan  # long gap: NaN
    frames["DCOILBRENTEU"] = brent
    levels, _ = lib_build.levels_from_frames(frames)
    assert levels.loc["2015-06-02", "BRENT"] == pytest.approx(brent.loc["2015-06-01", "DCOILBRENTEU"])
    assert np.isnan(levels.loc["2015-07-14", "BRENT"])


def test_brent_non_negative():
    frames = _frames(DAYS)
    brent = frames["DCOILBRENTEU"].copy()
    brent.iloc[10, 0] = -37.6
    frames["DCOILBRENTEU"] = brent
    with pytest.raises(lib_build.BuildError, match="Brent"):
        lib_build.build(frames, [_ev("a-shock", "2015-06-01")], _embed)


def test_soxx_proxy_before_2001():
    days = pd.bdate_range("2000-01-03", "2002-12-31")
    frames = _frames(days)
    soxx = frames["SOXX"].copy()
    soxx[soxx.index < pd.Timestamp("2001-07-13")] = np.nan
    frames["SOXX"] = soxx
    built = lib_build.build(
        frames, [_ev("chips-2000", "2000-09-22", ("semiconductors",)), _ev("chips-2002", "2002-03-01", ("semiconductors",))], _embed
    )
    assert "semis_proxy" in built.flags["chips-2000"]
    assert np.all(np.isnan(built.factor_paths[0, :, F.index("SOXX")]))
    assert "semis_proxy" not in built.flags.get("chips-2002", [])


def _spy_with_moves(moves: dict[str, float]) -> pd.Series:
    rng = np.random.default_rng(3)
    returns = pd.Series(rng.normal(0, 0.01, len(DAYS)), index=DAYS)
    for day, move in moves.items():
        returns[pd.Timestamp(day)] = move
    return 100 * (1 + returns).cumprod()


def test_date_check_flags_quiet_event():
    spy = _spy_with_moves({"2015-06-01": 0.0001, "2015-06-02": 0.0002, "2015-06-03": -0.0001})
    built = lib_build.build(_frames(DAYS, spy=spy), [_ev("quiet-shock", "2015-06-01")], _embed)
    assert "date_check_quiet" in built.flags["quiet-shock"]


def test_date_check_big_move_reversal_is_not_quiet():
    # A big day-0 move that reverses (the 2001 surprise cut, the 2010 flash crash) is a reaction.
    spy = _spy_with_moves({"2015-06-01": 0.05, "2015-06-02": -0.045, "2015-06-03": 0.0})
    built = lib_build.build(_frames(DAYS, spy=spy), [_ev("reversal-shock", "2015-06-01")], _embed)
    assert "date_check_quiet" not in built.flags.get("reversal-shock", [])


def test_date_check_flags_move_the_day_before():
    spy = _spy_with_moves({"2015-05-29": -0.06, "2015-06-01": 0.001, "2015-06-02": 0.0, "2015-06-03": 0.0})
    built = lib_build.build(_frames(DAYS, spy=spy), [_ev("late-dated", "2015-06-01")], _embed)
    assert "date_check_earlier" in built.flags["late-dated"]


def test_event_on_non_trading_day_is_rejected():
    with pytest.raises(lib_build.BuildError, match="trading day"):
        lib_build.build(_frames(DAYS), [_ev("a-shock", "2015-06-01")], _embed)  # sanity: works
        lib_build.build(_frames(DAYS[DAYS != pd.Timestamp("2015-06-01")]), [_ev("a-shock", "2015-06-01")], _embed)


def test_embeddings_are_normalized_and_use_trigger_name_category():
    seen: list[str] = []

    def embed(texts):
        seen.extend(texts)
        return np.full((len(texts), 4), 3.0)

    built = lib_build.build(_frames(DAYS), [_ev("a-shock", "2015-06-01")], embed)
    assert np.linalg.norm(built.embeddings[0]) == pytest.approx(1.0)
    assert seen == ["An example shock happens to an example market today. Example a-shock financial credit"]


def test_embeddings_match_onnx_embedder():
    from research import embedder

    if not (embedder.DEFAULT_MODEL_DIR / "model.onnx").exists():
        pytest.skip("BGE ONNX model not present (CI has no research assets)")
    model = embedder.OnnxEmbedder()
    built = lib_build.build(_frames(DAYS), [_ev("a-shock", "2015-06-01")], lambda t: model.encode(t))
    direct = model.encode([lib_build.embedding_text(built.events[0])])[0]
    assert float(built.embeddings[0] @ direct) >= 0.999


def test_assets_under_size_budget(tmp_path, monkeypatch):
    days = pd.bdate_range("2000-01-03", "2016-12-30")
    events = [_ev(f"shock-{i}", str(d.date())) for i, d in enumerate(days[200:-600:25][:150])]
    built = lib_build.build(_frames(days), events, _embed)
    lib_build.write(built, tmp_path, manifest_sha256="x")
    assert (tmp_path / "library.npz").stat().st_size < lib_build.SIZE_BUDGET_BYTES
    monkeypatch.setattr(lib_build, "SIZE_BUDGET_BYTES", 1000)
    with pytest.raises(lib_build.BuildError, match="budget"):
        lib_build.write(built, tmp_path / "small", manifest_sha256="x")


def test_load_library_round_trip(tmp_path):
    events = [_ev("a-shock", "2015-06-01"), _ev("b-shock", "2016-02-01")]
    built = lib_build.build(_frames(DAYS), events, _embed)
    lib_build.write(built, tmp_path, manifest_sha256="abc")
    library = lib_build.load_library(tmp_path)
    assert [e.id for e in library.events] == ["a-shock", "b-shock"]
    assert library.factor_paths.shape == (2, lib_build.RECOVERY_DAYS + 1, len(F))
    assert list(library.factor_history.columns) == F
    assert list(library.context.index) == ["a-shock", "b-shock"]
    np.testing.assert_array_equal(library.embeddings, built.embeddings)


def test_real_event_files_load_sorted_and_unique():
    events = lib_build.load_events()
    assert len(events) == len({e.id for e in events}) >= 140
    assert [e.date for e in events] == sorted(e.date for e in events)
