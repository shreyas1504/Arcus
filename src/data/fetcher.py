# ── src/data/fetcher.py ────────────────────────────────────────────────────
# All yfinance I/O lives here. Nothing outside this file should import yfinance.

import os
import tempfile

import yfinance as yf
import pandas as pd

# yfinance writes SQLite caches (tz, cookies, ISIN); point them to a
# guaranteed-writable temp directory so they never hit "unable to open database
# file" errors, then pre-initialise all three DB managers synchronously so
# Streamlit's multi-threaded sessions don't race to create the SQLite files.
_yf_cache = os.path.join(tempfile.gettempdir(), "yfinance_cache")
os.makedirs(_yf_cache, exist_ok=True)

try:
    yf.set_tz_cache_location(_yf_cache)
except AttributeError:
    pass  # older yfinance versions don't have this API — safe to ignore

# Belt-and-suspenders: directly patch all three manager classes so that even if
# set_tz_cache_location only updates one of them, the rest still point at the
# writable temp dir.  Then force-open every SQLite file now (import time, in
# the main thread) before any concurrent Streamlit session can race to create it.
try:
    from yfinance.cache import _TzDBManager, _CookieDBManager, _ISINDBManager
    for _mgr in (_TzDBManager, _CookieDBManager, _ISINDBManager):
        _mgr.set_location(_yf_cache)
    _TzDBManager.get_database()
    _CookieDBManager.get_database()
    _ISINDBManager.get_database()
except Exception:
    pass  # non-critical — worst case yfinance falls back to its default path


def resolve_ticker(query: str) -> tuple[str, str]:
    """
    Resolve a company name, partial name, or ticker string to a valid symbol.

    Strategy:
      1. Try the input as-is (fast path for valid tickers like "AAPL").
      2. Fall back to yf.Search to handle company names like "nvidia" or "apple".

    Returns:
        (symbol, display_name)  e.g. ("NVDA", "NVIDIA Corporation")
    """
    query_clean = query.strip()
    query_upper = query_clean.upper()

    # Fast path: check if the input itself is a valid ticker with recent data
    try:
        hist = yf.Ticker(query_upper).history(period="5d")
        if not hist.empty:
            info = yf.Ticker(query_upper).info
            name = info.get("longName") or info.get("shortName") or query_upper
            return query_upper, name
    except Exception:
        pass

    # Search by company name / partial string
    try:
        results = yf.Search(query_clean, max_results=10).quotes
        for r in results:
            if r.get("quoteType") in ("EQUITY", "ETF"):
                symbol = r.get("symbol", query_upper)
                name = r.get("longname") or r.get("shortname") or symbol
                return symbol, name
    except Exception:
        pass

    # Give up — return the uppercased input and let downstream fail gracefully
    return query_upper, query_upper


def resolve_tickers(queries: list[str]) -> list[dict]:
    """
    Resolve a list of user inputs to ticker symbols.

    Returns a list of dicts:
        [{"input": "nvidia", "symbol": "NVDA", "name": "NVIDIA Corporation"}, ...]
    """
    return [
        {"input": q, "symbol": symbol, "name": name}
        for q in queries
        for symbol, name in [resolve_ticker(q)]
    ]


def download_prices(tickers: list[str], start, end) -> tuple[pd.DataFrame, dict]:
    """
    Download adjusted close prices for a list of tickers.

    Returns:
        (prices_df, errors_dict)
        prices_df  — flat DataFrame, ticker symbols as columns
        errors_dict — {ticker: error_message} for any that failed
    """
    frames: dict[str, pd.Series] = {}
    errors: dict[str, str] = {}

    for ticker in tickers:
        try:
            # auto_adjust is True by default in modern yfinance; omit to avoid
            # version-specific behaviour differences
            hist = yf.Ticker(ticker).history(start=str(start), end=str(end))
            if hist.empty:
                errors[ticker] = "empty response (no trading data for this date range)"
            elif "Close" not in hist.columns:
                errors[ticker] = f"unexpected columns: {list(hist.columns)}"
            else:
                frames[ticker] = hist["Close"]
        except Exception as exc:
            errors[ticker] = str(exc)

    if not frames:
        return pd.DataFrame(), errors

    df = pd.DataFrame(frames)

    # Strip timezone: tz-aware → tz_convert(None); tz-naive → leave as-is
    if df.index.tz is not None:
        df.index = df.index.tz_convert(None)

    return df.dropna(how="all").dropna(), errors


def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily percentage returns from a price DataFrame."""
    return prices.pct_change().dropna()


def get_latest_prices(tickers: list[str]) -> dict:
    """Fetch the most recent closing price for each ticker."""
    result = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            price = stock.history(period="1d")["Close"].iloc[-1]
            result[ticker] = round(float(price), 2)
        except Exception:
            result[ticker] = None
    return result


def get_data_availability(tickers: list[str]) -> dict[str, dict]:
    """
    For each ticker return the earliest and latest date with price data.

    Returns:
        {ticker: {"first": date, "last": date, "days": int}} on success
        {ticker: {"error": str}} on failure
    """
    result = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="max")
            if hist.empty:
                result[ticker] = {"error": "no data found"}
            else:
                idx = hist.index
                if idx.tz is not None:
                    idx = idx.tz_convert(None)
                first = idx[0].date()
                last  = idx[-1].date()
                result[ticker] = {"first": first, "last": last, "days": len(hist)}
        except Exception as exc:
            result[ticker] = {"error": str(exc)}
    return result


def get_sector_map(tickers: list[str]) -> dict:
    """
    Return {ticker: sector_name} using yfinance .info.
    Falls back to 'Unknown' if sector data is unavailable.
    """
    sector_map = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            sector_map[ticker] = info.get("sector", "Unknown")
        except Exception:
            sector_map[ticker] = "Unknown"
    return sector_map


def sector_weights(tickers: list[str], weights, sector_map: dict) -> dict:
    """
    Aggregate portfolio weights by sector.

    Args:
        tickers: list of ticker strings
        weights: array-like of floats summing to 1
        sector_map: {ticker: sector}

    Returns:
        {sector: total_weight}
    """
    aggregated: dict[str, float] = {}
    for ticker, w in zip(tickers, weights):
        sector = sector_map.get(ticker, "Unknown")
        aggregated[sector] = aggregated.get(sector, 0.0) + w
    return aggregated
