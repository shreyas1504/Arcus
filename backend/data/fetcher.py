# ── backend/data/fetcher.py ────────────────────────────────────────────────
# All yfinance I/O. Ported from src/data/fetcher.py.
# Uses subprocess isolation to avoid rate-limit state in long-running servers.
# Includes in-memory cache to avoid repeated API calls.

import os
import time
import json
import logging
import tempfile
import hashlib
import subprocess
import sys
from datetime import datetime

import pandas as pd

logger = logging.getLogger("pulse.fetcher")


# ── In-memory price cache ────────────────────────────────────────────────────

_price_cache: dict[str, tuple[datetime, pd.DataFrame, dict]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _cache_key(tickers: list[str], start, end) -> str:
    raw = f"{sorted(tickers)}-{start}-{end}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── Subprocess-based yfinance fetch ──────────────────────────────────────────

_FETCH_SCRIPT = '''
import sys, json
import yfinance as yf

tickers = json.loads(sys.argv[1])
start = sys.argv[2]
end = sys.argv[3]

result = {"frames": {}, "errors": {}}
for ticker in tickers:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end)
        if hist.empty:
            result["errors"][ticker] = "empty response"
        elif "Close" not in hist.columns:
            result["errors"][ticker] = f"unexpected columns: {list(hist.columns)}"
        else:
            # Send back as JSON: list of [timestamp_ms, price] pairs
            data = []
            for idx, val in hist["Close"].items():
                ts = int(idx.timestamp() * 1000) if hasattr(idx, 'timestamp') else str(idx)
                data.append([ts, float(val)])
            result["frames"][ticker] = data
    except Exception as exc:
        result["errors"][ticker] = str(exc)

print(json.dumps(result))
'''


def download_prices(tickers: list[str], start, end) -> tuple[pd.DataFrame, dict]:
    """Download price data using a subprocess to avoid rate-limit issues.

    yfinance rate limits accumulate in long-running processes. Running
    the fetch in a fresh subprocess ensures a clean session each time.
    Results are cached for 5 minutes to minimize API calls.
    """
    # Check cache first
    key = _cache_key(tickers, start, end)
    if key in _price_cache:
        cached_time, cached_df, cached_errors = _price_cache[key]
        age = (datetime.now() - cached_time).total_seconds()
        if age < _CACHE_TTL_SECONDS:
            logger.info(f"download_prices: cache hit (age={age:.0f}s)")
            return cached_df.copy(), cached_errors.copy()
        else:
            del _price_cache[key]

    logger.info(f"download_prices: tickers={tickers}, start={start}, end={end}")

    try:
        proc = subprocess.run(
            [sys.executable, "-c", _FETCH_SCRIPT, json.dumps(tickers), str(start), str(end)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if proc.returncode != 0:
            logger.error(f"  Subprocess failed: {proc.stderr[:500]}")
            return pd.DataFrame(), {t: f"subprocess error: {proc.stderr[:200]}" for t in tickers}

        data = json.loads(proc.stdout)
        frames_raw = data.get("frames", {})
        errors = data.get("errors", {})

        if not frames_raw:
            logger.warning(f"  No frames returned. Errors: {errors}")
            return pd.DataFrame(), errors

        # Reconstruct DataFrame from JSON
        frames: dict[str, pd.Series] = {}
        for ticker, pairs in frames_raw.items():
            dates = [pd.Timestamp(ts, unit="ms") for ts, _ in pairs]
            values = [v for _, v in pairs]
            frames[ticker] = pd.Series(values, index=dates, name=ticker)

        df = pd.DataFrame(frames)
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        df.index = pd.DatetimeIndex(df.index).normalize()
        result = df.dropna(how="all").dropna()

        # Cache the result
        _price_cache[key] = (datetime.now(), result.copy(), errors.copy())
        logger.info(f"  Success: {result.shape[0]} rows, tickers={list(result.columns)}")

        return result, errors

    except subprocess.TimeoutExpired:
        logger.error("  Subprocess timed out")
        return pd.DataFrame(), {t: "timeout" for t in tickers}
    except Exception as exc:
        logger.error(f"  Unexpected error: {exc}")
        return pd.DataFrame(), {t: str(exc) for t in tickers}


_benchmark_cache: dict[str, tuple[datetime, pd.Series]] = {}
_BENCHMARK_CACHE_TTL = 600  # 10 minutes


def download_benchmark(ticker: str, start, end) -> pd.Series:
    """Download benchmark (e.g. ^GSPC) price data via subprocess.

    Returns the Close price as a pd.Series (tz-naive, normalized index),
    or an empty Series if the download fails.
    """
    key = f"{ticker}-{start}-{end}"
    if key in _benchmark_cache:
        cached_time, cached_series = _benchmark_cache[key]
        if (datetime.now() - cached_time).total_seconds() < _BENCHMARK_CACHE_TTL:
            logger.info(f"download_benchmark: cache hit for {ticker}")
            return cached_series.copy()
        else:
            del _benchmark_cache[key]

    logger.info(f"download_benchmark: {ticker}, {start} to {end}")

    script = '''
import sys, json
import yfinance as yf
ticker = sys.argv[1]
start = sys.argv[2]
end = sys.argv[3]
try:
    t = yf.Ticker(ticker)
    hist = t.history(start=start, end=end)
    if hist.empty or "Close" not in hist.columns:
        print(json.dumps({"error": "empty or no Close"}))
    else:
        data = []
        for idx, val in hist["Close"].items():
            ts = int(idx.timestamp() * 1000) if hasattr(idx, "timestamp") else str(idx)
            data.append([ts, float(val)])
        print(json.dumps({"data": data}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
'''
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script, ticker, str(start), str(end)],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            result = json.loads(proc.stdout)
            if "data" in result and result["data"]:
                pairs = result["data"]
                dates = [pd.Timestamp(ts, unit="ms") for ts, _ in pairs]
                values = [v for _, v in pairs]
                series = pd.Series(values, index=dates, name=ticker)
                if series.index.tz is not None:
                    series.index = series.index.tz_convert(None)
                series.index = pd.DatetimeIndex(series.index).normalize()
                _benchmark_cache[key] = (datetime.now(), series.copy())
                logger.info(f"  Benchmark success: {len(series)} rows")
                return series
            else:
                logger.warning(f"  Benchmark error: {result.get('error', 'unknown')}")
    except Exception as exc:
        logger.error(f"  Benchmark subprocess error: {exc}")

    return pd.Series(dtype=float)


def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna()


def get_latest_prices(tickers: list[str]) -> dict:
    """Get latest prices using subprocess."""
    script = '''
import sys, json
import yfinance as yf
tickers = json.loads(sys.argv[1])
result = {}
for t in tickers:
    try:
        h = yf.Ticker(t).history(period="5d")
        if not h.empty and "Close" in h.columns:
            result[t] = round(float(h["Close"].iloc[-1]), 2)
        else:
            result[t] = None
    except:
        result[t] = None
print(json.dumps(result))
'''
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script, json.dumps(tickers)],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except Exception:
        pass
    return {t: None for t in tickers}


def get_sector_map(tickers: list[str]) -> dict:
    """Get sector map using subprocess."""
    script = '''
import sys, json
import yfinance as yf
tickers = json.loads(sys.argv[1])
result = {}
for t in tickers:
    try:
        info = yf.Ticker(t).info
        result[t] = info.get("sector", "Unknown")
    except:
        result[t] = "Unknown"
print(json.dumps(result))
'''
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script, json.dumps(tickers)],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except Exception:
        pass
    return {t: "Unknown" for t in tickers}


def sector_weights(tickers: list[str], weights, sector_map: dict) -> dict:
    aggregated: dict[str, float] = {}
    for ticker, w in zip(tickers, weights):
        sector = sector_map.get(ticker, "Unknown")
        aggregated[sector] = aggregated.get(sector, 0.0) + w
    return aggregated
