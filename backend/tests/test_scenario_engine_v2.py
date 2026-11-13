"""Blind tests for Scenario Lab engine v2 helpers (PLAN.md section "v2").

Written from PLAN v2 and the stub docstrings of crisis_events, recovery_bucket,
exposure_ranking, resilience_summary and WhatIfEngine.run_v2 only. Expected values
are hand-computed in the comments. No network, no model. Marked xfail while the
v2 stubs still raise NotImplementedError.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from scenario import engine
from scenario.engine import (
    CRISIS_DRAWDOWN,
    RECOVERY_BUCKETS,
    Calibration,
    EngineSettings,
    Library,
    WhatIfEngine,
)
from scenario.enums import (
    FACTOR_NAMES,
    FACTOR_SPY,
    PATH_DAYS,
    RECOVERY_DAYS,
    Category,
    Sector,
)
from scenario.schemas import (
    Event,
    ParsedScenario,
    ScenarioHolding,
    ScenarioReplay,
    WhatIfRequest,
)
from scenario.trading_calendar import add_trading_days, is_trading_day, next_trading_day


def _is_v2_stub() -> bool:
    try:
        engine.recovery_bucket(0, True)
    except NotImplementedError:
        return True
    return False


pytestmark = pytest.mark.xfail(
    _is_v2_stub(),
    raises=NotImplementedError,
    strict=True,
    reason="scenario/engine.py v2 helpers are still stubs",
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
    return (cos * unit(0) + math.sqrt(1.0 - cos * cos) * unit(k)).astype(np.float32)


def event(
    event_id: str,
    day: date,
    *,
    cluster_id: str | None = None,
    category: Category = Category.FINANCIAL_CREDIT,
) -> Event:
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
        trigger="A synthetic shock used only by the engine v2 tests.",
        source_url="https://example.com/test",
        source_quote="A synthetic quote that is long enough to satisfy the schema rules.",
        split="dev",
        drafted_by="cursor",
        cluster_id=cluster_id,
    )


def spy_path(trough: float) -> np.ndarray:
    """Cumulative SPY path: linear to `trough` by PATH_DAYS, then flat to RECOVERY_DAYS.

    Monotone decline from 0, so worst drawdown within PATH_DAYS equals `trough`.
    """
    path = np.zeros(RECOVERY_DAYS + 1, dtype=np.float32)
    for t in range(PATH_DAYS + 1):
        path[t] = trough * (t / PATH_DAYS)
    path[PATH_DAYS:] = trough
    return path


def make_library(specs: list[tuple[str, date, float, str | None]]) -> Library:
    """specs: (id, date, spy_trough, cluster_id). Cosines are arbitrary (not used by crisis_events)."""
    events = [event(i, d, cluster_id=c) for i, d, _, c in specs]
    embeddings = np.stack([with_cosine(0.5, k + 1) for k in range(len(specs))])
    paths = np.zeros((len(specs), RECOVERY_DAYS + 1, len(FACTOR_NAMES)), dtype=np.float32)
    for k, (_, _, trough, _) in enumerate(specs):
        paths[k, :, SPY_COL] = spy_path(trough)
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


def holding(ticker: str, weight: float, contribution: float, *, sector: Sector = Sector.BROAD) -> ScenarioHolding:
    return ScenarioHolding(
        ticker=ticker,
        weight=weight,
        sector=sector,
        return_21d=contribution / weight if weight else 0.0,
        contribution=contribution,
        source="actual",
        recovery_days=0,
    )


def replay(
    event_id: str,
    holdings: list[ScenarioHolding],
    *,
    day: date = date(2010, 3, 1),
    portfolio_return_21d: float | None = None,
    worst_drawdown_63d: float = -0.05,
    sp500_worst_drawdown_63d: float | None = -0.04,
    similarity: float | None = 0.6,
) -> ScenarioReplay:
    total = sum(h.contribution for h in holdings)
    port = total if portfolio_return_21d is None else portfolio_return_21d
    path = [0.0] + [float(port) * t / PATH_DAYS for t in range(1, PATH_DAYS)] + [float(port)]
    assert len(path) == PATH_DAYS + 1
    return ScenarioReplay(
        event_id=event_id,
        name=f"Replay {event_id}",
        date=day,
        category=Category.FINANCIAL_CREDIT,
        nature="adverse",
        trigger="Synthetic replay for exposure and resilience tests.",
        similarity=similarity,
        source_url=f"https://example.com/{event_id}",
        portfolio_return_21d=port,
        sp500_return_21d=-0.02,
        worst_drawdown_63d=worst_drawdown_63d,
        sp500_worst_drawdown_63d=sp500_worst_drawdown_63d,
        recovery_days=10,
        recovery_known=True,
        recovery_source="actual",
        path=path,
        holdings=holdings,
    )


# ------------------------------------------------------------------ recovery_bucket


def test_recovery_bucket_never_fell():
    assert engine.recovery_bucket(0, True) == "never_fell"


def test_recovery_bucket_ranges():
    assert engine.recovery_bucket(1, True) == "1-21"
    assert engine.recovery_bucket(21, True) == "1-21"
    assert engine.recovery_bucket(22, True) == "22-63"
    assert engine.recovery_bucket(63, True) == "22-63"
    assert engine.recovery_bucket(64, True) == "64-126"
    assert engine.recovery_bucket(126, True) == "64-126"
    assert engine.recovery_bucket(127, True) == "127-252"
    assert engine.recovery_bucket(252, True) == "127-252"
    assert engine.recovery_bucket(253, True) == "253-504"
    assert engine.recovery_bucket(504, True) == "253-504"


def test_recovery_bucket_not_within_504_when_none_and_known():
    assert engine.recovery_bucket(None, True) == "not_within_504"


def test_recovery_bucket_unknown_when_none_and_not_known():
    assert engine.recovery_bucket(None, False) == "unknown"


def test_recovery_bucket_rejects_negative_and_over_horizon():
    with pytest.raises(ValueError):
        engine.recovery_bucket(-1, True)
    with pytest.raises(ValueError):
        engine.recovery_bucket(RECOVERY_DAYS + 1, True)


def test_recovery_bucket_rejects_days_when_not_known():
    with pytest.raises(ValueError):
        engine.recovery_bucket(10, False)


def test_recovery_bucket_labels_are_the_declared_set():
    for days, known in ((0, True), (10, True), (40, True), (100, True), (200, True), (300, True), (None, True), (None, False)):
        assert engine.recovery_bucket(days, known) in RECOVERY_BUCKETS


# ------------------------------------------------------------------ exposure_ranking


def test_exposure_ranking_empty():
    assert engine.exposure_ranking([]) == []


def test_exposure_ranking_hand_built():
    # Replay 1: A −0.10, B −0.02 → A most exposed
    # Replay 2: A −0.04, B −0.06 → B most exposed
    # Replay 3: A −0.01, B +0.02 → A most exposed (only negative)
    # Means: A = (−0.10−0.04−0.01)/3 = −0.05; B = (−0.02−0.06+0.02)/3 = −0.02
    # most_exposed: A=2, B=1; sorted by mean ascending → A then B
    r1 = replay("r1", [holding("A", 0.5, -0.10), holding("B", 0.5, -0.02)])
    r2 = replay("r2", [holding("A", 0.5, -0.04), holding("B", 0.5, -0.06)])
    r3 = replay("r3", [holding("A", 0.5, -0.01), holding("B", 0.5, 0.02)])
    ranked = engine.exposure_ranking([r1, r2, r3])
    assert [row.ticker for row in ranked] == ["A", "B"]
    assert ranked[0].mean_contribution == pytest.approx(-0.05)
    assert ranked[0].most_exposed_count == 2
    assert ranked[0].scenarios == 3
    assert ranked[1].mean_contribution == pytest.approx(-0.02)
    assert ranked[1].most_exposed_count == 1
    assert ranked[1].scenarios == 3


def test_exposure_ranking_tie_breaks_alphabetically_for_most_exposed():
    # Equal contributions −0.05: alphabetical first ticker wins the most-exposed count.
    r = replay("tie", [holding("ZZ", 0.5, -0.05), holding("AA", 0.5, -0.05)])
    ranked = engine.exposure_ranking([r])
    by_ticker = {row.ticker: row for row in ranked}
    assert by_ticker["AA"].most_exposed_count == 1
    assert by_ticker["ZZ"].most_exposed_count == 0


def test_exposure_ranking_ignores_non_negative_most_exposed():
    # All contributions >= 0 → most_exposed_count stays 0 for everyone.
    r = replay("up", [holding("A", 0.6, 0.03), holding("B", 0.4, 0.02)])
    ranked = engine.exposure_ranking([r])
    assert all(row.most_exposed_count == 0 for row in ranked)


def test_exposure_ranking_partial_coverage():
    # C appears in only one of two replays → scenarios=1 for C.
    r1 = replay("r1", [holding("A", 0.5, -0.08), holding("B", 0.5, -0.02)])
    r2 = replay("r2", [holding("A", 0.4, -0.04), holding("C", 0.6, -0.06)])
    ranked = engine.exposure_ranking([r1, r2])
    by_ticker = {row.ticker: row for row in ranked}
    assert by_ticker["A"].scenarios == 2
    assert by_ticker["B"].scenarios == 1
    assert by_ticker["C"].scenarios == 1
    assert by_ticker["C"].mean_contribution == pytest.approx(-0.06)
    # r1 most exposed A; r2 most exposed C
    assert by_ticker["A"].most_exposed_count == 1
    assert by_ticker["C"].most_exposed_count == 1


# ------------------------------------------------------------------ resilience_summary


def test_resilience_summary_hand_built():
    # Crisis 1: portfolio dd −0.20 < S&P −0.15 → worse
    # Crisis 2: portfolio dd −0.05 > S&P −0.12 → not worse
    # Crisis 3: no S&P comparison → excluded from crises_total
    # Exposure across crises: A most exposed in c1 and c2 (contrib −0.10, −0.08);
    # B most exposed never (less negative). top_drivers: A only with count>0 → ["A"]
    # Wait: c1 holdings A−0.12 B−0.04 → A; c2 A−0.03 B−0.08 → B; c3 A−0.05 B−0.01 → A
    # most_exposed: A=2, B=1 → top_drivers ["A","B"]
    c1 = replay(
        "c1",
        [holding("A", 0.5, -0.12), holding("B", 0.5, -0.04)],
        worst_drawdown_63d=-0.20,
        sp500_worst_drawdown_63d=-0.15,
        similarity=None,
    )
    c2 = replay(
        "c2",
        [holding("A", 0.5, -0.03), holding("B", 0.5, -0.08)],
        worst_drawdown_63d=-0.05,
        sp500_worst_drawdown_63d=-0.12,
        similarity=None,
    )
    c3 = replay(
        "c3",
        [holding("A", 0.5, -0.05), holding("B", 0.5, -0.01)],
        worst_drawdown_63d=-0.07,
        sp500_worst_drawdown_63d=None,
        similarity=None,
    )
    summary = engine.resilience_summary([c1, c2, c3])
    assert summary.crises_total == 2
    assert summary.worse_than_sp500 == 1
    assert summary.top_drivers == ["A", "B"]


def test_resilience_summary_empty():
    summary = engine.resilience_summary([])
    assert summary.crises_total == 0
    assert summary.worse_than_sp500 == 0
    assert summary.top_drivers == []


def test_resilience_summary_top_drivers_order():
    # Equal most_exposed_count: order by mean_contribution ascending, then ticker.
    # Both A and B most-exposed once; means A=-0.10, B=-0.05 → ["A","B"]
    c1 = replay(
        "c1",
        [holding("A", 0.5, -0.10), holding("B", 0.5, -0.01)],
        worst_drawdown_63d=-0.15,
        sp500_worst_drawdown_63d=-0.10,
        similarity=None,
    )
    c2 = replay(
        "c2",
        [holding("A", 0.5, -0.01), holding("B", 0.5, -0.05)],
        worst_drawdown_63d=-0.12,
        sp500_worst_drawdown_63d=-0.10,
        similarity=None,
    )
    summary = engine.resilience_summary([c1, c2])
    assert summary.top_drivers == ["A", "B"]


# ------------------------------------------------------------------ crisis_events


def test_crisis_events_requires_drawdown_at_or_below_threshold():
    # trough −0.10 qualifies; −0.09 does not. CRISIS_DRAWDOWN is −0.10.
    assert CRISIS_DRAWDOWN == -0.10
    d_ok = next_trading_day(date(2010, 3, 1))
    d_mild = next_trading_day(date(2011, 3, 1))
    library = make_library(
        [
            ("deep", d_ok, -0.10, None),
            ("mild", d_mild, -0.09, None),
        ]
    )
    indices = engine.crisis_events(library, AS_OF)
    assert [library.events[i].id for i in indices] == ["deep"]


def test_crisis_events_eligibility_window_must_close_before_as_of():
    # Event whose PATH_DAYS window has not closed before as_of is excluded even if deep.
    recent = add_trading_days(AS_OF, -(PATH_DAYS // 2))
    old = next_trading_day(date(2010, 6, 1))
    library = make_library(
        [
            ("old-deep", old, -0.20, None),
            ("too-recent", recent, -0.20, None),
        ]
    )
    assert add_trading_days(recent, PATH_DAYS - 1) >= AS_OF
    assert add_trading_days(old, PATH_DAYS - 1) < AS_OF
    indices = engine.crisis_events(library, AS_OF)
    assert [library.events[i].id for i in indices] == ["old-deep"]


def test_crisis_events_keeps_earliest_per_cluster():
    d1 = next_trading_day(date(2010, 1, 4))
    d2 = next_trading_day(date(2011, 1, 3))
    d3 = next_trading_day(date(2012, 1, 3))
    library = make_library(
        [
            ("cluster-early", d1, -0.15, "gfc"),
            ("cluster-late", d2, -0.25, "gfc"),
            ("solo", d3, -0.12, None),
        ]
    )
    indices = engine.crisis_events(library, AS_OF)
    assert [library.events[i].id for i in indices] == ["cluster-early", "solo"]


def test_crisis_events_same_date_tie_breaks_by_event_id():
    day = next_trading_day(date(2010, 5, 3))
    library = make_library(
        [
            ("z-late-id", day, -0.15, "same-day"),
            ("a-early-id", day, -0.15, "same-day"),
        ]
    )
    # Same cluster and date: keep the one with the alphabetically first id? Stub: "Ties on
    # date go by event id" for the kept set ordering / earliest. Within a cluster the
    # earliest qualifying event is kept; same date → by event id.
    indices = engine.crisis_events(library, AS_OF)
    assert [library.events[i].id for i in indices] == ["a-early-id"]


def test_crisis_events_sorted_by_date():
    d_late = next_trading_day(date(2012, 4, 2))
    d_early = next_trading_day(date(2009, 4, 1))
    library = make_library(
        [
            ("later", d_late, -0.14, None),
            ("earlier", d_early, -0.14, None),
        ]
    )
    indices = engine.crisis_events(library, AS_OF)
    assert [library.events[i].id for i in indices] == ["earlier", "later"]


# ------------------------------------------------------------------ WhatIfEngine.run_v2 (contract)


def window(event_day: date) -> tuple[date, date]:
    return add_trading_days(event_day, -1), add_trading_days(event_day, 20)


def stepped_prices(moves: dict[date, float]) -> pd.Series:
    windows = {window(d): r for d, r in moves.items()}
    level, values = 100.0, []
    for day in DAYS:
        for (t0, t21), r in windows.items():
            if t0 < day <= t21:
                n = DAYS.index(t21) - DAYS.index(t0)
                level *= (1.0 + r) ** (1.0 / n)
        values.append(level)
    return pd.Series(values, index=INDEX)


def price_loader(prices: dict[str, pd.Series]):
    def load(tickers: list[str], start: date, end: date) -> pd.DataFrame:
        cols = {t: prices[t] for t in tickers if t in prices}
        frame = pd.DataFrame(cols)
        return frame[(frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))]

    return load


def build_run_v2_engine(library: Library, prices: dict[str, pd.Series], **settings) -> WhatIfEngine:
    return WhatIfEngine(
        library,
        Calibration(q_hat=1.0, settings=EngineSettings(similarity_threshold=0.5, category_bonus=0.0, **settings)),
        embed=lambda _: QUERY,
        parse=lambda _: ParsedScenario(search_text="a synthetic shock"),
        load_prices=price_loader(prices),
        sectors=lambda tickers: {t: Sector.BROAD for t in tickers},
    )


def test_run_v2_low_confidence_has_empty_scenarios_and_span():
    # Only a weak cosine (0.2) below threshold 0.5 → confidence LOW, scenarios=[], span None.
    d = next_trading_day(date(2010, 3, 1))
    events = [event("weak", d)]
    embeddings = np.stack([with_cosine(0.2, 1)])
    paths = np.zeros((1, RECOVERY_DAYS + 1, len(FACTOR_NAMES)), dtype=np.float32)
    paths[0, :, SPY_COL] = spy_path(-0.15)
    history = pd.DataFrame(0.0, index=INDEX, columns=list(FACTOR_NAMES))
    context = pd.DataFrame(0.0, index=["weak"], columns=["vix", "baa10y", "gpr", "gpr_rise_5d"])
    library = Library(
        events=events,
        embeddings=embeddings,
        factor_names=FACTOR_NAMES,
        factor_paths=paths,
        context=context,
        factor_history=history,
    )
    eng = build_run_v2_engine(library, {"ACT": stepped_prices({d: -0.05})})
    response = eng.run_v2(
        WhatIfRequest(scenario="What if a weak match?", holdings=[{"ticker": "ACT", "weight": 1.0}]),
        as_of=AS_OF,
        parsed=ParsedScenario(search_text="a synthetic shock"),
    )
    assert response.confidence.value == "low"
    assert response.scenarios == []
    assert response.span_low is None and response.span_high is None
    assert response.crises  # crisis replay still returned
    assert response.narrative  # render_v2 filled it


def test_run_v2_scenarios_span_is_min_max_of_portfolio_returns():
    d1 = next_trading_day(date(2010, 3, 1))
    d2 = next_trading_day(date(2011, 3, 1))
    specs = [
        ("close-a", d1, 0.9),
        ("close-b", d2, 0.8),
    ]
    events = [event(i, d) for i, d, _ in specs]
    embeddings = np.stack([with_cosine(cos, k + 1) for k, (_, _, cos) in enumerate(specs)])
    paths = np.zeros((2, RECOVERY_DAYS + 1, len(FACTOR_NAMES)), dtype=np.float32)
    for k in range(2):
        paths[k, :, SPY_COL] = spy_path(-0.12)
    history = pd.DataFrame(0.0, index=INDEX, columns=list(FACTOR_NAMES))
    context = pd.DataFrame(0.0, index=[e.id for e in events], columns=["vix", "baa10y", "gpr", "gpr_rise_5d"])
    library = Library(
        events=events,
        embeddings=embeddings,
        factor_names=FACTOR_NAMES,
        factor_paths=paths,
        context=context,
        factor_history=history,
    )
    moves = {d1: -0.10, d2: -0.04}
    eng = build_run_v2_engine(library, {"ACT": stepped_prices(moves)})
    response = eng.run_v2(
        WhatIfRequest(scenario="What if two close shocks?", holdings=[{"ticker": "ACT", "weight": 1.0}]),
        as_of=AS_OF,
        parsed=ParsedScenario(search_text="a synthetic shock"),
    )
    assert response.confidence.value == "normal"
    assert 1 <= len(response.scenarios) <= 5
    returns = [s.portfolio_return_21d for s in response.scenarios]
    assert response.span_low == min(returns)
    assert response.span_high == max(returns)
    assert response.exposure  # exposure_ranking(scenarios)
    for row in response.scenarios:
        assert row.similarity is not None
        assert abs(sum(h.contribution for h in row.holdings) - row.portfolio_return_21d) < 1e-6
    for row in response.crises:
        assert row.similarity is None
