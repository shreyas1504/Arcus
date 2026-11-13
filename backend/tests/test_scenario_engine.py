"""Blind tests for scenario/engine.py (PLAN.md 3c), written from the stub docstring only.

Small hand-built libraries with exact cosines (unit vectors), prices built so each
precedent's 21-day return is a chosen number, and expected values computed by hand
in the comments. No network, no model.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from scenario import engine
from scenario.engine import Calibration, EngineSettings, Library, WhatIfEngine
from scenario.enums import (
    FACTOR_NAMES,
    FACTOR_SPY,
    HORIZON_DAYS,
    PATH_DAYS,
    RECOVERY_DAYS,
    Category,
    Sector,
)
from scenario.schemas import Event, ParsedScenario, WhatIfRequest
from scenario.trading_calendar import add_trading_days, is_trading_day, next_trading_day


def _is_stub() -> bool:
    try:
        engine.weighted_quantile([1.0], [1.0], 0.5)
    except NotImplementedError:
        return True
    return False


# Until C3 lands, every test must fail with NotImplementedError and nothing else.
pytestmark = pytest.mark.xfail(
    _is_stub(), raises=NotImplementedError, strict=True, reason="scenario/engine.py is still the C0 stub"
)

DIM = 384
AS_OF = next_trading_day(date(2017, 6, 1))
SPY_COL = FACTOR_NAMES.index(FACTOR_SPY)


# ------------------------------------------------------------------ builders


def trading_days(start: date, end: date) -> list[date]:
    days, day = [], start
    while day <= end:
        if is_trading_day(day):
            days.append(day)
        day += timedelta(days=1)
    return days


DAYS = trading_days(date(2008, 1, 2), AS_OF)
INDEX = pd.DatetimeIndex(DAYS)


def unit(k: int) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    v[k] = 1.0
    return v


QUERY = unit(0)


def with_cosine(cos: float, k: int) -> np.ndarray:
    """A unit vector whose cosine with QUERY is exactly `cos`."""
    return (cos * unit(0) + math.sqrt(1.0 - cos * cos) * unit(k)).astype(np.float32)


def event(event_id: str, day: date, category: Category = Category.FINANCIAL_CREDIT) -> Event:
    assert is_trading_day(day)
    return Event(
        id=event_id,
        name=f"Test event {event_id}",
        date=day,
        onset="sudden",
        nature="adverse",
        category=category,
        regions=["us"],
        sectors=["broad"],
        trigger="A synthetic shock used only by the engine tests.",
        source_url="https://example.com/test",
        source_quote="A synthetic quote that is long enough to satisfy the schema rules.",
        split="dev",
        drafted_by="cursor",
    )


def make_library(specs: list[tuple[str, date, float, Category]]) -> Library:
    """specs: (id, date, cosine with QUERY, category). Embedding k is orthogonal to the others."""
    events = [event(i, d, c) for i, d, _, c in specs]
    embeddings = np.stack([with_cosine(cos, k + 1) for k, (_, _, cos, _) in enumerate(specs)])
    paths = np.zeros((len(specs), RECOVERY_DAYS + 1, len(FACTOR_NAMES)), dtype=np.float32)
    for k in range(len(specs)):
        paths[k, :, SPY_COL] = np.linspace(0.0, -0.01 * (k + 1), RECOVERY_DAYS + 1)
    rng = np.random.default_rng(0)
    history = pd.DataFrame(
        rng.normal(0.0, 0.01, (len(INDEX), len(FACTOR_NAMES))), index=INDEX, columns=list(FACTOR_NAMES)
    )
    context = pd.DataFrame(0.0, index=[e.id for e in events], columns=["vix", "baa10y", "gpr", "gpr_rise_5d"])
    return Library(
        events=events,
        embeddings=embeddings,
        factor_names=FACTOR_NAMES,
        factor_paths=paths,
        context=context,
        factor_history=history,
    )


def window(event_day: date) -> tuple[date, date]:
    """(t = 0, t = HORIZON_DAYS): the close on day -1 and the close of the 21st trading day."""
    return add_trading_days(event_day, -1), add_trading_days(event_day, HORIZON_DAYS - 1)


def stepped_prices(moves: dict[date, float], start: date = DAYS[0]) -> pd.Series:
    """Flat at 100, except over each event window, where it moves by exactly (1 + r) from t=0 to t=21.

    Between windows the price stays flat, so a negative move never regains its start.
    """
    windows = {window(d): r for d, r in moves.items()}
    level, values = 100.0, []
    for day in DAYS:
        for (t0, t21), r in windows.items():
            if t0 < day <= t21:
                n = DAYS.index(t21) - DAYS.index(t0)
                level *= (1.0 + r) ** (1.0 / n)
        values.append(level)
    series = pd.Series(values, index=INDEX)
    return series[series.index >= pd.Timestamp(start)]


def ipo_prices(start: date, seed: int = 7) -> pd.Series:
    """A stock listed on `start`: a random walk with no gaps from then to AS_OF."""
    rng = np.random.default_rng(seed)
    index = INDEX[INDEX >= pd.Timestamp(start)]
    return pd.Series(100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, len(index))), index=index)


def price_loader(prices: dict[str, pd.Series]):
    calls: list[tuple[list[str], date, date]] = []

    def load(tickers: list[str], start: date, end: date) -> pd.DataFrame:
        calls.append((list(tickers), start, end))
        cols = {t: prices[t] for t in tickers if t in prices}
        frame = pd.DataFrame(cols)
        return frame[(frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))]

    load.calls = calls
    return load


def build_engine(library: Library, prices: dict[str, pd.Series], *, q_hat=1.5, **settings) -> WhatIfEngine:
    def parse(_: str) -> ParsedScenario:
        raise AssertionError("parse must not be called when `parsed` is given")

    return WhatIfEngine(
        library,
        Calibration(q_hat=q_hat, settings=EngineSettings(**settings)),
        embed=lambda _: QUERY,
        parse=parse,
        load_prices=price_loader(prices),
        sectors=lambda tickers: {t: Sector.BROAD for t in tickers},
    )


PARSED = ParsedScenario(search_text="a synthetic shock")


def request(holdings: dict[str, float], severity: str = "typical") -> WhatIfRequest:
    return WhatIfRequest(
        scenario="What if a synthetic shock happens?",
        holdings=[{"ticker": t, "weight": w} for t, w in holdings.items()],
        severity=severity,
    )


# Four precedents far apart, plus the 21-day return of the "ACT" stock in each.
D_A, D_B, D_C, D_D = (next_trading_day(date(y, 3, 1)) for y in (2010, 2011, 2012, 2013))
MAIN = [
    ("event-a", D_A, 0.9, Category.FINANCIAL_CREDIT),
    ("event-b", D_B, 0.8, Category.FINANCIAL_CREDIT),
    ("event-c", D_C, 0.7, Category.FINANCIAL_CREDIT),
    ("event-d", D_D, 0.2, Category.FINANCIAL_CREDIT),
]
ACT_MOVES = {D_A: -0.10, D_B: -0.04, D_C: 0.02, D_D: -0.30}


def main_engine(**settings) -> WhatIfEngine:
    prices = {"ACT": stepped_prices(ACT_MOVES), "EST": ipo_prices(date(2015, 6, 1))}
    return build_engine(make_library(MAIN), prices, **({"similarity_threshold": 0.5, "category_bonus": 0.0} | settings))


# ------------------------------------------------------------------ weighted_quantile and recovery_days


def test_weighted_quantile_lower_definition():
    values, weights = [3.0, 1.0, 2.0, 4.0], [1.0, 1.0, 1.0, 1.0]
    # sorted 1,2,3,4 with cumulative weight .25,.5,.75,1
    assert engine.weighted_quantile(values, weights, 0.5) == 2.0
    assert engine.weighted_quantile(values, weights, 0.51) == 3.0
    assert engine.weighted_quantile(values, weights, 0.25) == 1.0
    assert engine.weighted_quantile(values, weights, 1.0) == 4.0


def test_weighted_median_known_case():
    # sorted -0.10 (w .5), 0.00 (w .125), 0.05 (w .375): cumulative .5, .625, 1
    values, weights = [0.05, -0.10, 0.00], [3.0, 4.0, 1.0]
    assert engine.weighted_quantile(values, weights, 0.5) == -0.10
    assert engine.weighted_quantile(values, weights, 0.6) == 0.00
    assert engine.weighted_quantile(values, weights, 0.75) == 0.05


def test_weighted_quantile_ignores_weight_scale():
    values = [0.3, 0.1, 0.2]
    assert engine.weighted_quantile(values, [1, 2, 1], 0.5) == engine.weighted_quantile(values, [10, 20, 10], 0.5)


def test_weighted_quantile_empty_raises():
    with pytest.raises(ValueError):
        engine.weighted_quantile([], [], 0.5)


def test_recovery_days_never_below_start_is_zero():
    assert engine.recovery_days([0.0, 0.01, 0.0, 0.02]) == 0


def test_recovery_days_first_day_back_after_minimum():
    # minimum at t=3; first t after it with path >= 0 is t=5 (t=1 is before the minimum)
    assert engine.recovery_days([0.0, 0.01, -0.02, -0.05, -0.01, 0.0, 0.03]) == 5


def test_unrecovered_share():
    """A path that never regains its start is unrecovered (None), not RECOVERY_DAYS."""
    assert engine.recovery_days([0.0, -0.01, -0.05, -0.04, -0.02]) is None
    assert engine.recovery_days([0.0, -0.03, float("nan"), float("nan")]) is None


def test_recovery_days_ignores_unobserved_tail():
    assert engine.recovery_days([0.0, -0.02, 0.01, float("nan")]) == 2


# ------------------------------------------------------------------ eligibility and scoring


def test_as_of_excludes_future_and_purged():
    as_of = add_trading_days(D_C, PATH_DAYS - 1)  # event-c's 63-day window is still open on as_of
    events = make_library(MAIN).events

    assert sorted(engine.eligible_precedents(events, as_of)) == [0, 1]
    assert sorted(engine.eligible_precedents(events, add_trading_days(as_of, 1))) == [0, 1, 2]
    assert engine.eligible_precedents(events, D_A) == []


def test_eligible_precedents_returns_library_rows():
    events = make_library(list(reversed(MAIN))).events  # event-d first
    assert sorted(engine.eligible_precedents(events, AS_OF)) == [0, 1, 2, 3]


def test_ranking_with_fake_embeddings():
    library = make_library(MAIN)
    scored = engine.score_precedents(QUERY, PARSED, library, AS_OF, EngineSettings(category_bonus=0.0))

    assert [library.events[s.index].id for s in scored] == ["event-a", "event-b", "event-c", "event-d"]
    assert [s.similarity for s in scored] == pytest.approx([0.9, 0.8, 0.7, 0.2], abs=1e-6)
    assert [s.score for s in scored] == pytest.approx([0.9, 0.8, 0.7, 0.2], abs=1e-6)


def test_score_ties_break_by_event_id():
    day1, day2 = next_trading_day(date(2010, 3, 1)), next_trading_day(date(2011, 3, 1))
    library = make_library([("zeta", day1, 0.6, Category.TERRORISM), ("alpha", day2, 0.6, Category.TERRORISM)])
    scored = engine.score_precedents(QUERY, PARSED, library, AS_OF, EngineSettings(category_bonus=0.0))
    assert [library.events[s.index].id for s in scored] == ["alpha", "zeta"]


def test_category_bonus_reorders():
    day1, day2 = next_trading_day(date(2010, 3, 1)), next_trading_day(date(2011, 3, 1))
    library = make_library([
        ("off-category", day1, 0.82, Category.ENERGY_OIL),
        ("same-category", day2, 0.80, Category.MONETARY_POLICY),
    ])
    parsed = ParsedScenario(search_text="rates", category=Category.MONETARY_POLICY)

    scored = engine.score_precedents(QUERY, parsed, library, AS_OF, EngineSettings(category_bonus=0.05))

    assert [library.events[s.index].id for s in scored] == ["same-category", "off-category"]
    assert scored[0].score == pytest.approx(0.85, abs=1e-6)
    assert scored[0].similarity == pytest.approx(0.80, abs=1e-6)  # the bonus never changes the cosine
    assert scored[1].score == pytest.approx(0.82, abs=1e-6)


def test_no_bonus_without_a_parsed_category():
    day1, day2 = next_trading_day(date(2010, 3, 1)), next_trading_day(date(2011, 3, 1))
    library = make_library([
        ("off-category", day1, 0.82, Category.ENERGY_OIL),
        ("same-category", day2, 0.80, Category.MONETARY_POLICY),
    ])
    scored = engine.score_precedents(QUERY, PARSED, library, AS_OF, EngineSettings(category_bonus=0.05))
    assert [library.events[s.index].id for s in scored] == ["off-category", "same-category"]


def test_scoring_skips_ineligible_events():
    library = make_library(MAIN)
    as_of = add_trading_days(D_C, PATH_DAYS - 1)
    scored = engine.score_precedents(QUERY, PARSED, library, as_of, EngineSettings())
    assert {library.events[s.index].id for s in scored} == {"event-a", "event-b"}


# ------------------------------------------------------------------ run: the hand-computed case
#
# Threshold 0.5 keeps a, b, c (cosines .9, .8, .7); d (.2) is below it.
# Weights = score / sum = .9/2.4, .8/2.4, .7/2.4 = .375, .3333, .2917.
# ACT returns: a -0.10, b -0.04, c +0.02.
#   median  (q .50): cumulative .375, .7083 -> -0.04
#   mild    (q .75): -> +0.02      severe (q .10): -> -0.10
#   mean   = .375*-.10 + .3333*-.04 + .2917*.02 = -0.045
#   |r - median| = .06, 0, .06 -> weighted median .06 -> spread .06
#   range  = -0.04 -/+ 1.5 * .06 = [-0.13, +0.05]


def test_weighted_median_and_range_end_to_end():
    response = main_engine().run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED)
    p = response.portfolio

    assert response.confidence == "normal"
    assert [x.event_id for x in response.precedents] == ["event-a", "event-b", "event-c"]
    assert [x.weight for x in response.precedents] == pytest.approx([0.375, 1 / 3, 0.7 / 2.4], abs=1e-6)
    assert [x.similarity for x in response.precedents] == pytest.approx([0.9, 0.8, 0.7], abs=1e-6)
    assert [x.portfolio_return_21d for x in response.precedents] == pytest.approx([-0.10, -0.04, 0.02], abs=1e-6)
    assert p.median_return == pytest.approx(-0.04, abs=1e-6)
    assert p.typical_return == pytest.approx(-0.04, abs=1e-6)
    assert p.mean_return == pytest.approx(-0.045, abs=1e-6)
    assert p.range_low == pytest.approx(-0.13, abs=1e-6)
    assert p.range_high == pytest.approx(0.05, abs=1e-6)


def test_precedent_sp500_return_comes_from_the_library():
    library = make_library(MAIN)
    response = main_engine().run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED)
    expected = {e.id: float(library.factor_paths[k, HORIZON_DAYS, SPY_COL]) for k, e in enumerate(library.events)}
    for precedent in response.precedents:
        assert precedent.sp500_return_21d == pytest.approx(expected[precedent.event_id], abs=1e-6)


def test_severity_ordering():
    engine_ = main_engine()
    out = {s: engine_.run(request({"ACT": 1.0}, s), as_of=AS_OF, parsed=PARSED) for s in ("mild", "typical", "severe")}

    assert out["mild"].portfolio.typical_return == pytest.approx(0.02, abs=1e-6)
    assert out["typical"].portfolio.typical_return == pytest.approx(-0.04, abs=1e-6)
    assert out["severe"].portfolio.typical_return == pytest.approx(-0.10, abs=1e-6)
    assert (
        out["mild"].portfolio.typical_return
        >= out["typical"].portfolio.typical_return
        >= out["severe"].portfolio.typical_return
    )
    for severity, response in out.items():
        assert response.severity == severity and response.portfolio.severity == severity
        assert response.portfolio.median_return == pytest.approx(-0.04, abs=1e-6)


def test_range_contains_median():
    for q_hat in (0.0, 0.5, 3.0):
        p = main_engine(q_hat=q_hat).run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED).portfolio
        assert p.range_low <= p.median_return <= p.range_high


def test_spread_floor_applies():
    # Only event-a is selected, so |r - median| is 0 and the spread floor sets the width.
    p = main_engine(similarity_threshold=0.85).run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED).portfolio
    assert p.range_high - p.range_low == pytest.approx(2 * 1.5 * engine.SPREAD_FLOOR, abs=1e-9)


def test_top_k_limits_selection():
    response = main_engine(top_k=2).run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED)
    assert [x.event_id for x in response.precedents] == ["event-a", "event-b"]
    assert sum(x.weight for x in response.precedents) == pytest.approx(1.0, abs=1e-6)


def test_as_of_excludes_future_and_purged_in_run():
    as_of = add_trading_days(D_C, PATH_DAYS - 1)
    response = main_engine().run(request({"ACT": 1.0}), as_of=as_of, parsed=PARSED)
    assert {x.event_id for x in response.precedents} == {"event-a", "event-b"}
    for precedent in response.precedents:
        assert add_trading_days(precedent.date, PATH_DAYS - 1) < as_of
    assert response.as_of == as_of


def test_low_confidence_widens_range():
    # Normal: only event-a passes 0.85, so the width is the spread floor.
    # Low: nothing passes 0.95, so every eligible event counts with equal weight:
    #   values -0.30, -0.10, -0.04, +0.02 -> median -0.10 (cumulative .25, .5)
    #   |r - median| = .20, 0, .06, .12 -> sorted 0, .06, .12, .20 -> .06; width 2 * 1.5 * .06 = .18
    normal = main_engine(similarity_threshold=0.85).run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED)
    low = main_engine(similarity_threshold=0.95).run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED)

    assert normal.confidence == "normal" and low.confidence == "low"
    assert low.portfolio.median_return == pytest.approx(-0.10, abs=1e-6)
    assert low.portfolio.mean_return == pytest.approx((-0.10 - 0.04 + 0.02 - 0.30) / 4, abs=1e-6)
    assert low.portfolio.range_high - low.portfolio.range_low == pytest.approx(0.18, abs=1e-6)
    assert (low.portfolio.range_high - low.portfolio.range_low) > (
        normal.portfolio.range_high - normal.portfolio.range_low
    )
    assert [x.event_id for x in low.precedents] == ["event-a", "event-b", "event-c", "event-d"]


# ------------------------------------------------------------------ run: holdings


def test_actual_vs_estimated_label():
    """ACT has prices across every window; EST listed after all of them, so it is estimated."""
    response = main_engine().run(request({"ACT": 0.6, "EST": 0.4}), as_of=AS_OF, parsed=PARSED)
    by_ticker = {h.ticker: h for h in response.holdings}

    assert by_ticker["ACT"].source == "actual"
    assert by_ticker["ACT"].actual_share == pytest.approx(1.0, abs=1e-6)
    assert by_ticker["ACT"].return_21d == pytest.approx(-0.045, abs=1e-6)
    assert by_ticker["EST"].source == "estimated"
    assert by_ticker["EST"].actual_share == pytest.approx(0.0, abs=1e-6)


def test_short_history_is_labelled_low_history():
    prices = {"ACT": stepped_prices(ACT_MOVES), "NEW": ipo_prices(add_trading_days(AS_OF, -60))}
    engine_ = build_engine(make_library(MAIN), prices, similarity_threshold=0.5, category_bonus=0.0)
    by_ticker = {h.ticker: h for h in engine_.run(request({"ACT": 0.5, "NEW": 0.5}), as_of=AS_OF, parsed=PARSED).holdings}
    assert by_ticker["NEW"].source == "estimated_low_history"


def test_contributions_sum_to_portfolio():
    response = main_engine().run(request({"ACT": 0.6, "EST": 0.4}), as_of=AS_OF, parsed=PARSED)

    for h in response.holdings:
        assert h.contribution == pytest.approx(h.weight * h.return_21d, abs=1e-9)
    assert sum(h.contribution for h in response.holdings) == pytest.approx(response.portfolio.mean_return, abs=1e-6)
    weights = [x.weight for x in response.precedents]
    returns = [x.portfolio_return_21d for x in response.precedents]
    assert sum(w * r for w, r in zip(weights, returns)) == pytest.approx(response.portfolio.mean_return, abs=1e-6)


def test_ticker_without_data_is_skipped_and_weights_renormalized():
    response = main_engine().run(request({"ACT": 0.5, "GHOST": 0.5}), as_of=AS_OF, parsed=PARSED)

    assert [s.ticker for s in response.skipped] == ["GHOST"]
    assert [h.ticker for h in response.holdings] == ["ACT"]
    assert response.holdings[0].weight == pytest.approx(1.0, abs=1e-9)
    assert response.portfolio.mean_return == pytest.approx(-0.045, abs=1e-6)


def test_single_holding():
    response = main_engine().run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED)

    assert len(response.holdings) == 1
    h = response.holdings[0]
    assert (h.ticker, h.weight, h.sector) == ("ACT", 1.0, "broad")
    assert h.contribution == pytest.approx(response.portfolio.mean_return, abs=1e-6)
    assert response.skipped == []


def test_parsed_argument_skips_the_model():
    main_engine().run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED)  # parse() raises if called


def test_prices_after_as_of_are_never_requested():
    prices = {"ACT": stepped_prices(ACT_MOVES)}
    loader = price_loader(prices)
    engine_ = WhatIfEngine(
        make_library(MAIN),
        Calibration(q_hat=1.5, settings=EngineSettings(similarity_threshold=0.5, category_bonus=0.0)),
        embed=lambda _: QUERY,
        parse=lambda _: PARSED,
        load_prices=loader,
        sectors=lambda tickers: {t: Sector.BROAD for t in tickers},
    )
    as_of = add_trading_days(D_C, PATH_DAYS + 5)
    engine_.run(request({"ACT": 1.0}), as_of=as_of, parsed=PARSED)
    assert loader.calls and all(pd.Timestamp(end) <= pd.Timestamp(as_of) for _, _, end in loader.calls)


# ------------------------------------------------------------------ run: drawdown and recovery


def test_unrecovered_precedent_counts_in_unrecovered_share():
    """One precedent whose price drops and stays down for the full 504 days."""
    day = next_trading_day(date(2010, 3, 1))
    library = make_library([("event-a", day, 0.9, Category.FINANCIAL_CREDIT)])
    engine_ = build_engine(library, {"ACT": stepped_prices({day: -0.20})}, similarity_threshold=0.5)

    p = engine_.run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED).portfolio

    assert p.unrecovered_share == pytest.approx(1.0)
    assert p.recovery_days_low is None and p.recovery_days_high is None
    assert p.worst_drawdown_63d == pytest.approx(-0.20, abs=1e-6)


def test_paths_start_at_zero_and_cover_the_selected_precedents():
    response = main_engine().run(request({"ACT": 1.0}), as_of=AS_OF, parsed=PARSED)
    assert {s.event_id for s in response.paths} <= {x.event_id for x in response.precedents}
    for series in response.paths:
        assert series.values[0] == 0.0
        assert len(series.values) <= PATH_DAYS + 1
