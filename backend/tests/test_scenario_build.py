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
