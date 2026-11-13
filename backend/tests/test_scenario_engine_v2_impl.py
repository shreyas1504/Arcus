"""Implementer tests for engine v2 (Claude, C4b-engine).

Cursor's blind tests live in test_scenario_engine_v2.py; these are separate on purpose.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.tests.test_scenario_engine_impl import AS_OF, _event, _library, _request
from scenario import engine as E
from scenario.enums import RECOVERY_DAYS, Confidence, Sector
from scenario.schemas import BacktestSummaryV2, ParsedScenario, ScenarioReplay, WhatIfResponseV2

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_V2 = ROOT / "frontend/src/lib/__fixtures__/whatif-response-v2.json"


def _gen():
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen_fixture", ROOT / "scripts/gen_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------ pure rules


@pytest.mark.parametrize(
    "days,known,bucket",
    [(0, True, "never_fell"), (1, True, "1-21"), (21, True, "1-21"), (22, True, "22-63"), (63, True, "22-63"),
     (64, True, "64-126"), (126, True, "64-126"), (127, True, "127-252"), (252, True, "127-252"),
     (253, True, "253-504"), (504, True, "253-504"), (None, True, "not_within_504"), (None, False, "unknown")],
)
def test_recovery_bucket(days, known, bucket):
    assert E.recovery_bucket(days, known) == bucket


@pytest.mark.parametrize("days,known", [(-1, True), (505, True), (10, False)])
def test_recovery_bucket_rejects(days, known):
    with pytest.raises(ValueError):
        E.recovery_bucket(days, known)


def test_exposure_and_resilience_match_the_fixture_rules():
    data = json.loads(FIXTURE_V2.read_text())
    gen = _gen()
    scenarios = [ScenarioReplay.model_validate(r) for r in data["scenarios"]]
    crises = [ScenarioReplay.model_validate(r) for r in data["crises"]]
    ours = E.exposure_ranking(scenarios)
    expected = gen.exposure_rule(data["scenarios"])
    assert [r.ticker for r in ours] == [e["ticker"] for e in expected]
    for rank, want in zip(ours, expected):
        assert rank.mean_contribution == pytest.approx(want["mean_contribution"], abs=1e-6)
        assert (rank.most_exposed_count, rank.scenarios) == (want["most_exposed_count"], want["scenarios"])
    assert E.resilience_summary(crises).model_dump() == gen.resilience_rule(data["crises"])
    assert E.exposure_ranking([]) == []


def test_crisis_events_rule():
    # 21-day S&P falls: a -15%, b -2% (not a crisis), c -12% (favorable) and d -20% (adverse)
    # within 63 trading days (one episode, named by its adverse deepest member), e too recent.
    events = [_event("a-crash", "2015-03-02"), _event("b-calm", "2015-09-01"),
              _event("c-rescue", "2016-03-01"), _event("d-crash", "2016-04-01"), _event("e-too-recent", "2018-05-01")]
    events[2] = events[2].model_copy(update={"nature": "favorable"})
    lib = _library(events, [-0.15, -0.02, -0.12, -0.20, -0.30])
    assert [lib.events[i].id for i in E.crisis_events(lib, AS_OF)] == ["a-crash", "d-crash"]


def test_crisis_episode_prefers_adverse_even_if_shallower():
    events = [_event("x-rescue", "2015-03-02"), _event("y-crash", "2015-04-01")]
    events[0] = events[0].model_copy(update={"nature": "favorable"})
    lib = _library(events, [-0.25, -0.11])
    assert [lib.events[i].id for i in E.crisis_events(lib, AS_OF)] == ["y-crash"]


def test_crisis_needs_the_fall_within_21_days():
    events = [_event("slow-burn", "2015-03-02")]
    lib = _library(events, [-0.02])
    lib.factor_paths[0, 30:64, :] = -0.25  # a later crash inside 63 days, not within 21
    assert E.crisis_events(lib, AS_OF) == []


# ------------------------------------------------------------------ run_v2


def _world():
    events = [_event(f"shock-{i}", d) for i, d in enumerate(["2015-03-02", "2015-09-01", "2016-03-01", "2016-09-01"])]
    lib = _library(events, [-0.15, -0.02, 0.03, -0.11])
    days = pd.bdate_range("2014-01-01", "2018-05-31")
    spy = lib.factor_history.loc[days, "SPY"]
    prices = pd.DataFrame({"AAA": 100 * (1 + spy).cumprod(), "BBB": 50 * (1 + 0.5 * spy).cumprod()}, index=days)
    return lib, prices


def _engine_v2(lib, prices, *, threshold=0.0, backtest_v2=None):
    settings = E.EngineSettings(similarity_threshold=threshold, category_bonus=0.0)
    calibration = E.Calibration(q_hat=0.0, settings=settings, backtest_v2=backtest_v2 or BacktestSummaryV2(available=False))
    return E.WhatIfEngine(
        lib, calibration, embed=lambda text: np.eye(1, 8, 0, dtype=np.float32)[0],
        parse=lambda text: ParsedScenario(search_text=text, fallback=True),
        load_prices=lambda tickers, start, end: prices[[t for t in tickers if t in prices]],
        sectors=lambda tickers: {t: Sector.BROAD for t in tickers},
    )


def test_run_v2_is_consistent():
    lib, prices = _world()
    response = _engine_v2(lib, prices).run_v2(_request("AAA", "BBB"), as_of=AS_OF)
    assert isinstance(response, WhatIfResponseV2) and response.confidence is Confidence.NORMAL
    assert 1 <= len(response.scenarios) <= 5
    returns = [s.portfolio_return_21d for s in response.scenarios]
    assert response.span_low == min(returns) and response.span_high == max(returns)
    assert [lib.events[i].id for i in E.crisis_events(lib, AS_OF)] == [c.event_id for c in response.crises]
    for replay in response.scenarios + response.crises:
        assert replay.recovery_source == "actual"  # both stocks traded throughout
        assert sum(h.weight for h in replay.holdings) == pytest.approx(1.0)


def test_run_v2_low_confidence_returns_crises_only():
    lib, prices = _world()
    response = _engine_v2(lib, prices, threshold=1.01).run_v2(_request("AAA"), as_of=AS_OF)
    assert response.confidence is Confidence.LOW
    assert response.scenarios == [] and response.span_low is None and response.exposure == []
    assert response.crises


def test_run_v2_actual_only_fallback_hides_estimated_recovery():
    lib, prices = _world()
    young = prices.copy()
    young.loc[young.index < pd.Timestamp("2016-06-01"), "BBB"] = np.nan  # BBB listed later: estimated in 2015 replays
    fallback = BacktestSummaryV2(available=True, recovery_shown_from="actual_only")
    response = _engine_v2(lib, young, backtest_v2=fallback).run_v2(_request("AAA", "BBB"), as_of=AS_OF)
    for replay in response.scenarios + response.crises:
        if replay.recovery_source != "actual":
            assert replay.recovery_days is None and replay.recovery_known is False
        for holding in replay.holdings:
            if holding.source.value != "actual":
                assert holding.recovery_days is None


def test_run_v2_unknown_ticker_skipped():
    lib, prices = _world()
    response = _engine_v2(lib, prices).run_v2(_request("AAA", "ZZZZ"), as_of=AS_OF)
    assert [s.ticker for s in response.skipped] == ["ZZZZ"]
    assert all(len(r.holdings) == 1 for r in response.scenarios)
