# ── backend/analytics/event_study.py ──────────────────────────────────────
# Event study on earnings announcements, plus keyword classification of live
# headlines.
#
# Everything here is deliberately transparent: the keyword lists are literal,
# the event window is a constant, and any event whose price history is
# incomplete is *skipped and counted* rather than filled in. Nothing in this
# module invents a number.

import re
import time
import logging
import statistics
from datetime import datetime

import pandas as pd

from backend.data.fetcher import download_ohlcv, get_earnings_dates

logger = logging.getLogger("pulse.event_study")


# ── Headline classification ─────────────────────────────────────────────────

EVENT_KEYWORDS: dict[str, list[str]] = {
    "EARNINGS": ["earnings", "eps", "revenue", "guidance", "beat", "miss"],
    "POLICY": ["fed", "rates", "fomc", "inflation", "cpi", "tariff", "treasury"],
    "GEOPOLITICAL": ["war", "sanctions", "election", "conflict", "opec", "china"],
}

# Checked in this order; the first category with a keyword hit wins.
CATEGORY_ORDER = ["EARNINGS", "POLICY", "GEOPOLITICAL"]
DEFAULT_CATEGORY = "OTHER"

_KEYWORD_PATTERNS = {
    category: re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE)
    for category, words in EVENT_KEYWORDS.items()
}


def classify_headline(text: str) -> str:
    """Bucket a headline into EARNINGS / POLICY / GEOPOLITICAL / OTHER.

    Whole-word keyword match, first category in CATEGORY_ORDER wins. Returns
    OTHER when nothing matches — there is no probabilistic guessing here.
    """
    if not text:
        return DEFAULT_CATEGORY
    for category in CATEGORY_ORDER:
        if _KEYWORD_PATTERNS[category].search(text):
            return category
    return DEFAULT_CATEGORY


def group_headlines_by_category(articles: list[dict]) -> dict[str, list[dict]]:
    """Group already-classified articles by their category field."""
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        category = article.get("category") or DEFAULT_CATEGORY
        grouped.setdefault(category, []).append(article)
    return grouped


# ── Event window constants ──────────────────────────────────────────────────

PRE_WINDOW_DAYS = 1       # day -1
POST_WINDOW_DAYS = 3      # day +3
VOL_BEFORE_DAYS = 20      # daily returns over days -20 … -1
VOL_AFTER_DAYS = 5        # daily returns over days +1 … +5
VOLUME_LOOKBACK_DAYS = 20  # average volume over days -20 … -1

BENCHMARK = "SPY"
QUARTERS = 8

METHODOLOGY = (
    "Earnings event study, window day -1 to +3, abnormal return vs SPY, "
    "data from Yahoo Finance"
)

# Trading days of history needed on each side of the event day.
_DAYS_NEEDED_BEFORE = VOL_BEFORE_DAYS + 1   # returns on days -20…-1 need the close at -21
_DAYS_NEEDED_AFTER = VOL_AFTER_DAYS         # returns on days +1…+5 need the close at +5

MARKET_CLOSE_HOUR = 16  # announcements at/after 16:00 exchange time react the next session


def resolve_event_index(index: pd.DatetimeIndex, announced: pd.Timestamp) -> int | None:
    """Trading-day position that carries the price reaction to an announcement.

    An announcement at or after the 16:00 close is reacted to on the following
    session, so day 0 is the first trading day strictly after it. Otherwise day
    0 is the first trading day on or after the announcement date. Returns None
    when the announcement falls past the end of the price history.
    """
    after_close = announced.hour >= MARKET_CLOSE_HOUR
    day = pd.Timestamp(announced.date())
    positions = index.searchsorted(day, side="right" if after_close else "left")
    position = int(positions)
    if position >= len(index):
        return None
    return position


def compute_event_metrics(
    close: pd.Series,
    volume: pd.Series,
    benchmark_close: pd.Series,
    event_position: int,
) -> dict | None:
    """Abnormal return, volatility change and volume spike for a single event.

    `close`, `volume` and `benchmark_close` must share one trading-day index,
    and `event_position` is day 0 within it. Returns None when the window runs
    off either end of the history — the caller counts that as a skip.
    """
    n = len(close)
    first_needed = event_position - _DAYS_NEEDED_BEFORE
    last_needed = event_position + _DAYS_NEEDED_AFTER
    if first_needed < 0 or last_needed > n - 1:
        return None

    # (1) Cumulative return over days -1…+3 is the close at +3 over the close at
    # -2, for the ticker and for the benchmark. The difference is the abnormal
    # return.
    window_start = event_position - PRE_WINDOW_DAYS - 1
    window_end = event_position + POST_WINDOW_DAYS
    base_price = float(close.iloc[window_start])
    base_benchmark = float(benchmark_close.iloc[window_start])
    if base_price <= 0 or base_benchmark <= 0:
        return None

    ticker_return = float(close.iloc[window_end]) / base_price - 1.0
    benchmark_return = float(benchmark_close.iloc[window_end]) / base_benchmark - 1.0
    abnormal_return = ticker_return - benchmark_return

    # (2) Volatility: daily-return standard deviation over the 5 sessions after
    # the event against the 20 sessions before it.
    daily_returns = close.pct_change()
    vol_before = float(daily_returns.iloc[event_position - VOL_BEFORE_DAYS:event_position].std(ddof=1))
    vol_after = float(daily_returns.iloc[event_position + 1:event_position + 1 + VOL_AFTER_DAYS].std(ddof=1))
    if not (vol_before > 0) or pd.isna(vol_after):
        return None
    volatility_change = vol_after / vol_before - 1.0

    # (3) Volume spike: event-day volume over the prior 20-session average.
    avg_volume = float(volume.iloc[event_position - VOLUME_LOOKBACK_DAYS:event_position].mean())
    event_volume = float(volume.iloc[event_position])
    if not (avg_volume > 0):
        return None
    volume_spike = event_volume / avg_volume

    return {
        "date": close.index[event_position].date().isoformat(),
        "ticker_return": ticker_return,
        "benchmark_return": benchmark_return,
        "abnormal_return": abnormal_return,
        "volatility_before": vol_before,
        "volatility_after": vol_after,
        "volatility_change": volatility_change,
        "volume_spike": volume_spike,
    }


def summarize_events(events: list[dict]) -> dict | None:
    """Mean / median / positive share across a list of event rows.

    Returns None for an empty list — an empty summary is an empty state, not a
    row of zeros.
    """
    if not events:
        return None
    abnormal = [e["abnormal_return"] for e in events]
    positive = [a for a in abnormal if a > 0]
    return {
        "n_events": len(events),
        "mean_abnormal_return": statistics.fmean(abnormal),
        "median_abnormal_return": statistics.median(abnormal),
        "mean_abs_abnormal_return": statistics.fmean([abs(a) for a in abnormal]),
        "positive_share": len(positive) / len(abnormal),
        "mean_volume_spike": statistics.fmean([e["volume_spike"] for e in events]),
        "mean_volatility_change": statistics.fmean([e["volatility_change"] for e in events]),
    }


def study_ticker(
    ticker: str,
    frame: pd.DataFrame,
    benchmark_close: pd.Series,
    announcements: list[pd.Timestamp],
) -> tuple[list[dict], list[dict]]:
    """Run the event study for one ticker. Returns (events, skipped)."""
    events: list[dict] = []
    skipped: list[dict] = []

    aligned = frame.join(benchmark_close.rename("benchmark"), how="inner").dropna()
    if aligned.empty:
        return [], [{"ticker": ticker, "date": None, "reason": "no overlapping price history"}]

    for announced in announcements:
        announced_date = pd.Timestamp(announced).date().isoformat()
        position = resolve_event_index(aligned.index, pd.Timestamp(announced))
        if position is None:
            skipped.append({"ticker": ticker, "date": announced_date, "reason": "no trading day after announcement"})
            continue

        metrics = compute_event_metrics(
            aligned["close"], aligned["volume"], aligned["benchmark"], position
        )
        if metrics is None:
            skipped.append({"ticker": ticker, "date": announced_date, "reason": "incomplete price window"})
            continue

        metrics["ticker"] = ticker
        metrics["announced"] = announced_date
        events.append(metrics)

    return events, skipped


# ── Orchestration ───────────────────────────────────────────────────────────

_event_cache: dict[str, tuple[float, dict]] = {}
_EVENT_CACHE_TTL = 21600  # 6 hours


def _past_announcements(dates: list[pd.Timestamp], quarters: int) -> list[pd.Timestamp]:
    """Last `quarters` announcements that have already happened, newest first."""
    now = pd.Timestamp.now(tz="UTC")
    past = []
    for value in dates:
        stamp = pd.Timestamp(value)
        comparable = stamp if stamp.tz is not None else stamp.tz_localize("UTC")
        if comparable <= now:
            past.append(stamp)
    past.sort(reverse=True)
    return past[:quarters]


def run_event_study(tickers: list[str], quarters: int = QUARTERS) -> dict:
    """Earnings event study across `tickers`, benchmarked against SPY.

    Cached for 6 hours. On a data failure the affected tickers appear in
    `skipped` and contribute nothing to the averages.
    """
    clean = [t.strip().upper() for t in tickers if t and t.strip()]
    clean = sorted(set(clean))
    if not clean:
        return _empty_result([], quarters)

    cache_key = f"{'-'.join(clean)}|{quarters}"
    cached = _event_cache.get(cache_key)
    if cached and time.time() - cached[0] < _EVENT_CACHE_TTL:
        logger.info("run_event_study: cache hit")
        return cached[1]

    # ~8 quarters of events plus the 20-day pre-window: 3 calendar years is
    # comfortably enough, and yfinance is cheap on daily bars.
    end = datetime.now().date()
    # DateOffset rather than replace(year=...), which raises on 29 February.
    start = (pd.Timestamp(end) - pd.DateOffset(years=3)).date()

    earnings, earnings_errors = get_earnings_dates(clean, limit=quarters * 3)
    frames, price_errors = download_ohlcv(clean + [BENCHMARK], start, end)

    benchmark_frame = frames.get(BENCHMARK)
    if benchmark_frame is None or benchmark_frame.empty:
        logger.warning("run_event_study: no benchmark history, returning empty result")
        result = _empty_result(clean, quarters)
        result["skipped"] = [
            {"ticker": t, "date": None, "reason": f"{BENCHMARK} price history unavailable"} for t in clean
        ]
        result["skipped_count"] = len(clean)
        _event_cache[cache_key] = (time.time(), result)
        return result

    benchmark_close = benchmark_frame["close"]

    all_events: list[dict] = []
    all_skipped: list[dict] = []
    by_ticker: dict[str, dict] = {}

    for ticker in clean:
        frame = frames.get(ticker)
        if frame is None or frame.empty:
            reason = price_errors.get(ticker, "price history unavailable")
            all_skipped.append({"ticker": ticker, "date": None, "reason": reason})
            continue

        announcements = _past_announcements(earnings.get(ticker, []), quarters)
        if not announcements:
            reason = earnings_errors.get(ticker, "no reported earnings dates")
            all_skipped.append({"ticker": ticker, "date": None, "reason": reason})
            continue

        events, skipped = study_ticker(ticker, frame, benchmark_close, announcements)
        all_events.extend(events)
        all_skipped.extend(skipped)

        summary = summarize_events(events)
        if summary:
            by_ticker[ticker] = summary

    all_events.sort(key=lambda e: e["date"], reverse=True)

    result = {
        "tickers_requested": clean,
        "tickers_analyzed": sorted(by_ticker.keys()),
        "quarters": quarters,
        "benchmark": BENCHMARK,
        "window": {"pre_days": PRE_WINDOW_DAYS, "post_days": POST_WINDOW_DAYS},
        "events": all_events,
        "by_ticker": by_ticker,
        "overall": summarize_events(all_events),
        "skipped": all_skipped,
        "skipped_count": len(all_skipped),
        "methodology": METHODOLOGY,
    }
    _event_cache[cache_key] = (time.time(), result)
    return result


def _empty_result(tickers: list[str], quarters: int) -> dict:
    return {
        "tickers_requested": tickers,
        "tickers_analyzed": [],
        "quarters": quarters,
        "benchmark": BENCHMARK,
        "window": {"pre_days": PRE_WINDOW_DAYS, "post_days": POST_WINDOW_DAYS},
        "events": [],
        "by_ticker": {},
        "overall": None,
        "skipped": [],
        "skipped_count": 0,
        "methodology": METHODOLOGY,
    }
