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
import threading
from datetime import datetime

import pandas as pd

logger = logging.getLogger("pulse.fetcher")


# ── In-memory price cache ────────────────────────────────────────────────────

_price_cache: dict[str, tuple[datetime, pd.DataFrame, dict]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes

# Lock management for price downloads (double-checked locking)
_price_locks: dict[str, threading.Lock] = {}
_price_locks_mutex = threading.Lock()

def _get_price_lock(key: str) -> threading.Lock:
    with _price_locks_mutex:
        if key not in _price_locks:
            _price_locks[key] = threading.Lock()
        return _price_locks[key]


# ── Benchmark cache ──────────────────────────────────────────────────────────

_benchmark_cache: dict[str, tuple[datetime, pd.Series]] = {}
_BENCHMARK_CACHE_TTL = 600  # 10 minutes

_benchmark_locks: dict[str, threading.Lock] = {}
_benchmark_locks_mutex = threading.Lock()

def _get_benchmark_lock(key: str) -> threading.Lock:
    with _benchmark_locks_mutex:
        if key not in _benchmark_locks:
            _benchmark_locks[key] = threading.Lock()
        return _benchmark_locks[key]


# ── Live prices cache ────────────────────────────────────────────────────────

_latest_prices_cache: dict[str, tuple[datetime, dict]] = {}
_LATEST_PRICES_CACHE_TTL = 300  # 5 minutes
_latest_prices_lock = threading.Lock()


# ── Sector cache ─────────────────────────────────────────────────────────────

_sector_cache: dict[str, str] = {}
_sector_lock = threading.Lock()

try:
    from backend.data.common_tickers import COMMON_TICKER_INFO
    for _t, _info in COMMON_TICKER_INFO.items():
        _sector_cache[_t.upper()] = _info["sector"]
except Exception as _e:
    logger.error(f"Failed to pre-populate sector cache: {_e}")


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

    # Lock acquisition and double-checked caching
    lock = _get_price_lock(key)
    with lock:
        if key in _price_cache:
            cached_time, cached_df, cached_errors = _price_cache[key]
            age = (datetime.now() - cached_time).total_seconds()
            if age < _CACHE_TTL_SECONDS:
                logger.info(f"download_prices: cache hit after lock wait (age={age:.0f}s)")
                return cached_df.copy(), cached_errors.copy()
            else:
                del _price_cache[key]

        logger.info(f"download_prices: cache miss, downloading. tickers={tickers}, start={start}, end={end}")

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

    lock = _get_benchmark_lock(key)
    with lock:
        if key in _benchmark_cache:
            cached_time, cached_series = _benchmark_cache[key]
            if (datetime.now() - cached_time).total_seconds() < _BENCHMARK_CACHE_TTL:
                logger.info(f"download_benchmark: cache hit after lock wait for {ticker}")
                return cached_series.copy()
            else:
                del _benchmark_cache[key]

        logger.info(f"download_benchmark: cache miss, downloading {ticker}, {start} to {end}")

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
    """Get latest prices concurrently (with 5-minute cache)."""
    key = "-".join(sorted(t.upper() for t in tickers))
    now = datetime.now()

    # Check cache first
    if key in _latest_prices_cache:
        cached_time, cached_data = _latest_prices_cache[key]
        if (now - cached_time).total_seconds() < _LATEST_PRICES_CACHE_TTL:
            logger.info("get_latest_prices: cache hit")
            return cached_data.copy()

    with _latest_prices_lock:
        # Double check cache
        if key in _latest_prices_cache:
            cached_time, cached_data = _latest_prices_cache[key]
            if (now - cached_time).total_seconds() < _LATEST_PRICES_CACHE_TTL:
                logger.info("get_latest_prices: cache hit after lock wait")
                return cached_data.copy()

        logger.info(f"get_latest_prices: cache miss, fetching concurrently. tickers={tickers}")

        def fetch_ticker_price(t: str) -> float | None:
            try:
                import yfinance as yf
                h = yf.Ticker(t).history(period="5d")
                if not h.empty and "Close" in h.columns:
                    return round(float(h["Close"].iloc[-1]), 2)
            except Exception:
                pass
            return None

        result = {}
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(len(tickers), 10)) as executor:
            future_to_ticker = {executor.submit(fetch_ticker_price, t): t for t in tickers}
            for future in as_completed(future_to_ticker):
                t = future_to_ticker[future]
                try:
                    price = future.result()
                except Exception:
                    price = None
                result[t] = price

        _latest_prices_cache[key] = (now, result)
        return result


def get_sector_map(tickers: list[str]) -> dict:
    """Get sector map (cached in memory with concurrent fallback)."""
    result = {}
    missing = []

    # Check cache first
    for t in tickers:
        t_upper = t.upper()
        if t_upper in _sector_cache:
            result[t] = _sector_cache[t_upper]
        else:
            missing.append(t_upper)

    if not missing:
        return result

    with _sector_lock:
        # Double check cache
        still_missing = []
        for t in missing:
            if t in _sector_cache:
                result[t] = _sector_cache[t]
            else:
                still_missing.append(t)

        if not still_missing:
            # Reconstruct original case keys for result
            return {t: _sector_cache[t.upper()] for t in tickers}

        logger.info(f"get_sector_map: cache miss for tickers={still_missing}, fetching concurrently")

        def fetch_sector_online(t: str) -> str:
            try:
                import yfinance as yf
                info = yf.Ticker(t).info or {}
                return info.get("sector", "Unknown")
            except Exception:
                return "Unknown"

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(len(still_missing), 10)) as executor:
            future_to_ticker = {executor.submit(fetch_sector_online, t): t for t in still_missing}
            for future in as_completed(future_to_ticker):
                t = future_to_ticker[future]
                try:
                    sector = future.result()
                except Exception:
                    sector = "Unknown"
                _sector_cache[t] = sector

        # Reconstruct original case keys for result
        return {t: _sector_cache[t.upper()] for t in tickers}


def sector_weights(tickers: list[str], weights, sector_map: dict) -> dict:
    aggregated: dict[str, float] = {}
    for ticker, w in zip(tickers, weights):
        sector = sector_map.get(ticker, "Unknown")
        aggregated[sector] = aggregated.get(sector, 0.0) + w
    return aggregated
