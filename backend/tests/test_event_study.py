"""
ARCUS — Event study tests

Covers headline classification and the earnings event-study maths in
analytics/event_study.py. Every price series here is synthetic and built from
an explicit list of daily returns, so each expected value is derived by hand
rather than snapshotted from the implementation.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import math

import pandas as pd
import pytest

from backend.analytics.event_study import (
    classify_headline,
    group_headlines_by_category,
    resolve_event_index,
    compute_event_metrics,
    summarize_events,
    study_ticker,
    DEFAULT_CATEGORY,
)

# ─────────────────────────────────────────────────────────────────────────────
# Headline classification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("headline,expected", [
    ("Apple Q3 earnings top estimates", "EARNINGS"),
    ("Nvidia EPS beats Wall Street consensus", "EARNINGS"),
    ("Retailer cuts full-year guidance", "EARNINGS"),
    ("Revenue climbs 12% at the chipmaker", "EARNINGS"),
    ("Fed holds rates steady", "POLICY"),
    ("FOMC minutes point to one more hike", "POLICY"),
    ("CPI inflation cools to 2.4%", "POLICY"),
    ("New tariff on imported steel announced", "POLICY"),
    ("Treasury yields slip", "POLICY"),
    ("OPEC weighs a production cut", "GEOPOLITICAL"),
    ("Sanctions tighten on exporters", "GEOPOLITICAL"),
    ("China factory output slows", "GEOPOLITICAL"),
    ("Election result rattles traders", "GEOPOLITICAL"),
    ("Airline unveils a new loyalty programme", "OTHER"),
])
def test_classify_headline_categories(headline, expected):
    assert classify_headline(headline) == expected


def test_classify_headline_is_case_insensitive():
    assert classify_headline("fed signals a pause") == "POLICY"
    assert classify_headline("FED SIGNALS A PAUSE") == "POLICY"


def test_classify_headline_matches_whole_words_only():
    # "fed" must not fire inside "confederate", "miss" not inside "mission"
    assert classify_headline("Confederate history museum reopens") == DEFAULT_CATEGORY
    assert classify_headline("Mission to Mars launches") == DEFAULT_CATEGORY


def test_classify_headline_precedence_is_earnings_then_policy():
    # A headline hitting two categories resolves to the earlier one in CATEGORY_ORDER
    assert classify_headline("Bank earnings beat as the Fed holds rates") == "EARNINGS"
    assert classify_headline("Fed rate path clouds China outlook") == "POLICY"


def test_classify_headline_handles_empty_input():
    assert classify_headline("") == DEFAULT_CATEGORY
    assert classify_headline(None) == DEFAULT_CATEGORY


def test_group_headlines_by_category():
    articles = [
        {"headline": "a", "category": "EARNINGS"},
        {"headline": "b", "category": "POLICY"},
        {"headline": "c", "category": "EARNINGS"},
        {"headline": "d"},  # missing category falls back to OTHER
    ]
    grouped = group_headlines_by_category(articles)
    assert sorted(grouped.keys()) == ["EARNINGS", "OTHER", "POLICY"]
    assert len(grouped["EARNINGS"]) == 2
    assert grouped["OTHER"][0]["headline"] == "d"


def test_group_headlines_by_category_empty():
    assert group_headlines_by_category([]) == {}


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic price fixtures
#
# 40 trading days. Day 0 of the event sits at position 25. The daily returns
# are specified exactly, so every window statistic below is hand-computable:
#
#   positions  5…24  (days -20…-1)  alternating +1% / -1%
#   position   25    (day 0)        +5%
#   positions  26…30 (days +1…+5)   +2%, -2%, +2%, -2%, 0%
#   everything else                 0%
# ─────────────────────────────────────────────────────────────────────────────

N_DAYS = 40
EVENT_POSITION = 25


def _prices_from_returns(returns, start=100.0):
    prices = [start]
    for r in returns[1:]:
        prices.append(prices[-1] * (1.0 + r))
    return prices


def _index():
    return pd.DatetimeIndex(pd.bdate_range("2024-01-01", periods=N_DAYS))


def _ticker_returns():
    returns = [0.0] * N_DAYS
    for offset in range(20):                      # days -20 … -1
        returns[EVENT_POSITION - 20 + offset] = 0.01 if offset % 2 == 0 else -0.01
    returns[EVENT_POSITION] = 0.05                # day 0
    for offset, r in enumerate([0.02, -0.02, 0.02, -0.02, 0.0]):  # days +1 … +5
        returns[EVENT_POSITION + 1 + offset] = r
    return returns


@pytest.fixture
def close():
    return pd.Series(_prices_from_returns(_ticker_returns()), index=_index())


@pytest.fixture
def volume():
    # 1,000 shares every day except a 3,500-share event day
    values = [1000.0] * N_DAYS
    values[EVENT_POSITION] = 3500.0
    return pd.Series(values, index=_index())


@pytest.fixture
def benchmark_close():
    # Flat except a single +1% move on day +1, so the benchmark's cumulative
    # return across the day -1 … +3 window is exactly 1%.
    returns = [0.0] * N_DAYS
    returns[EVENT_POSITION + 1] = 0.01
    return pd.Series(_prices_from_returns(returns), index=_index())


# ─────────────────────────────────────────────────────────────────────────────
# compute_event_metrics
# ─────────────────────────────────────────────────────────────────────────────


def test_abnormal_return_is_ticker_minus_benchmark_over_the_window(close, volume, benchmark_close):
    metrics = compute_event_metrics(close, volume, benchmark_close, EVENT_POSITION)

    # Window compounds the returns on days -1, 0, +1, +2, +3
    expected_ticker = 0.99 * 1.05 * 1.02 * 0.98 * 1.02 - 1.0
    expected_benchmark = 0.01

    assert metrics["ticker_return"] == pytest.approx(expected_ticker, rel=1e-9)
    assert metrics["benchmark_return"] == pytest.approx(expected_benchmark, rel=1e-9)
    assert metrics["abnormal_return"] == pytest.approx(expected_ticker - expected_benchmark, rel=1e-9)


def test_volatility_change_compares_five_days_after_to_twenty_before(close, volume, benchmark_close):
    metrics = compute_event_metrics(close, volume, benchmark_close, EVENT_POSITION)

    # Before: 20 returns of ±1%, mean 0 -> sample std = 0.01 * sqrt(20/19)
    expected_before = 0.01 * math.sqrt(20 / 19)
    # After: [2%, -2%, 2%, -2%, 0%], mean 0, sum of squares 1.6e-3 -> std = 0.02
    expected_after = 0.02

    assert metrics["volatility_before"] == pytest.approx(expected_before, rel=1e-9)
    assert metrics["volatility_after"] == pytest.approx(expected_after, rel=1e-9)
    assert metrics["volatility_change"] == pytest.approx(2 * math.sqrt(19 / 20) - 1, rel=1e-9)


def test_volume_spike_is_event_day_over_twenty_day_average(close, volume, benchmark_close):
    metrics = compute_event_metrics(close, volume, benchmark_close, EVENT_POSITION)
    assert metrics["volume_spike"] == pytest.approx(3.5, rel=1e-12)


def test_event_date_is_the_day_zero_trading_date(close, volume, benchmark_close):
    metrics = compute_event_metrics(close, volume, benchmark_close, EVENT_POSITION)
    assert metrics["date"] == close.index[EVENT_POSITION].date().isoformat()


def test_zero_abnormal_return_when_ticker_tracks_benchmark(close, volume):
    # Benchmark identical to the ticker -> the abnormal return must be exactly 0
    metrics = compute_event_metrics(close, volume, close.copy(), EVENT_POSITION)
    assert metrics["abnormal_return"] == pytest.approx(0.0, abs=1e-12)


def test_skips_event_without_enough_history_before(close, volume, benchmark_close):
    # Day 0 at position 10 leaves fewer than the 21 sessions the pre-window needs
    assert compute_event_metrics(close, volume, benchmark_close, 10) is None


def test_skips_event_without_enough_history_after(close, volume, benchmark_close):
    # Day 0 four sessions from the end cannot fill the +5 volatility window
    assert compute_event_metrics(close, volume, benchmark_close, N_DAYS - 4) is None


def test_skips_event_when_pre_period_has_no_volatility(volume, benchmark_close):
    flat = pd.Series([100.0] * N_DAYS, index=_index())
    assert compute_event_metrics(flat, volume, benchmark_close, EVENT_POSITION) is None


def test_skips_event_when_average_volume_is_zero(close, benchmark_close):
    no_volume = pd.Series([0.0] * N_DAYS, index=_index())
    assert compute_event_metrics(close, no_volume, benchmark_close, EVENT_POSITION) is None


# ─────────────────────────────────────────────────────────────────────────────
# resolve_event_index
# ─────────────────────────────────────────────────────────────────────────────


def test_announcement_before_the_close_reacts_the_same_day():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
    # 08:30 — before the 16:00 close
    assert resolve_event_index(index, pd.Timestamp("2024-01-03 08:30")) == 1


def test_announcement_after_the_close_reacts_the_next_session():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
    assert resolve_event_index(index, pd.Timestamp("2024-01-03 16:30")) == 2


def test_announcement_on_a_non_trading_day_rolls_forward():
    index = pd.DatetimeIndex(["2024-01-05", "2024-01-08"])  # Friday, Monday
    assert resolve_event_index(index, pd.Timestamp("2024-01-06 09:00")) == 1  # Saturday


def test_announcement_after_the_last_session_returns_none():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
    assert resolve_event_index(index, pd.Timestamp("2024-06-01 09:00")) is None


# ─────────────────────────────────────────────────────────────────────────────
# summarize_events
# ─────────────────────────────────────────────────────────────────────────────


def _event(abnormal, spike=2.0, vol_change=0.5):
    return {"abnormal_return": abnormal, "volume_spike": spike, "volatility_change": vol_change}


def test_summarize_events_mean_median_and_positive_share():
    events = [_event(0.10), _event(-0.02), _event(0.04), _event(-0.08)]
    summary = summarize_events(events)

    assert summary["n_events"] == 4
    assert summary["mean_abnormal_return"] == pytest.approx(0.01)   # (0.10 - 0.02 + 0.04 - 0.08)/4
    assert summary["median_abnormal_return"] == pytest.approx(0.01)  # mean of -0.02 and 0.04
    assert summary["mean_abs_abnormal_return"] == pytest.approx(0.06)
    assert summary["positive_share"] == pytest.approx(0.5)


def test_summarize_events_odd_count_median():
    summary = summarize_events([_event(0.01), _event(0.05), _event(-0.03)])
    assert summary["median_abnormal_return"] == pytest.approx(0.01)
    assert summary["positive_share"] == pytest.approx(2 / 3)


def test_summarize_events_averages_spike_and_volatility():
    events = [_event(0.01, spike=1.5, vol_change=0.2), _event(0.01, spike=2.5, vol_change=0.6)]
    summary = summarize_events(events)
    assert summary["mean_volume_spike"] == pytest.approx(2.0)
    assert summary["mean_volatility_change"] == pytest.approx(0.4)


def test_summarize_events_returns_none_for_no_events():
    # An empty study is an empty state, never a row of zeros
    assert summarize_events([]) is None


# ─────────────────────────────────────────────────────────────────────────────
# study_ticker
# ─────────────────────────────────────────────────────────────────────────────


def test_study_ticker_measures_a_usable_event(close, volume, benchmark_close):
    frame = pd.DataFrame({"close": close, "volume": volume})
    announced = pd.Timestamp(close.index[EVENT_POSITION]).replace(hour=9)

    events, skipped = study_ticker("TEST", frame, benchmark_close, [announced])

    assert skipped == []
    assert len(events) == 1
    assert events[0]["ticker"] == "TEST"
    assert events[0]["abnormal_return"] == pytest.approx(
        0.99 * 1.05 * 1.02 * 0.98 * 1.02 - 1.0 - 0.01, rel=1e-9
    )


def test_study_ticker_skips_and_reports_events_with_short_windows(close, volume, benchmark_close):
    frame = pd.DataFrame({"close": close, "volume": volume})
    usable = pd.Timestamp(close.index[EVENT_POSITION]).replace(hour=9)
    too_early = pd.Timestamp(close.index[2]).replace(hour=9)
    too_late = pd.Timestamp(close.index[N_DAYS - 2]).replace(hour=9)

    events, skipped = study_ticker("TEST", frame, benchmark_close, [usable, too_early, too_late])

    assert len(events) == 1
    assert len(skipped) == 2
    assert {s["reason"] for s in skipped} == {"incomplete price window"}
    assert all(s["ticker"] == "TEST" for s in skipped)


def test_study_ticker_reports_announcements_past_the_price_history(close, volume, benchmark_close):
    frame = pd.DataFrame({"close": close, "volume": volume})
    future = pd.Timestamp("2030-01-15 09:00")

    events, skipped = study_ticker("TEST", frame, benchmark_close, [future])

    assert events == []
    assert skipped[0]["reason"] == "no trading day after announcement"


def test_study_ticker_reports_missing_benchmark_overlap(close, volume):
    frame = pd.DataFrame({"close": close, "volume": volume})
    disjoint = pd.Series([100.0, 101.0], index=pd.DatetimeIndex(["2030-01-02", "2030-01-03"]))

    events, skipped = study_ticker("TEST", frame, disjoint, [pd.Timestamp("2024-02-01 09:00")])

    assert events == []
    assert skipped[0]["reason"] == "no overlapping price history"
