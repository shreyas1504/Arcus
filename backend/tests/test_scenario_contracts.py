"""Scenario Lab contracts (PLAN.md Step 0): schemas, enums, calendar, stubs, fixture."""

from __future__ import annotations

import importlib.util
import inspect
import json
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from scenario import engine, factors, narrative, parse, trading_calendar
from scenario.enums import (
    FACTOR_NAMES,
    SECTOR_ETF,
    Category,
    Sector,
    Severity,
    sector_from_yfinance,
)
from scenario.schemas import (
    Event,
    ParsedScenario,
    PathSeries,
    PortfolioOutcome,
    WhatIfRequest,
    WhatIfResponse,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "frontend/src/lib/__fixtures__/whatif-response.json"


def _event(**overrides) -> dict:
    base = {
        "id": "example-event-2008",
        "name": "Example event",
        "date": "2008-09-15",
        "onset": "sudden",
        "nature": "adverse",
        "category": "financial_credit",
        "regions": ["us"],
        "sectors": ["financials"],
        "trigger": "An example firm files for bankruptcy after talks to sell it fail.",
        "source_url": "https://example.com/source",
        "source_quote": "This is an example quote that is long enough to pass the length check.",
        "split": "dev",
        "drafted_by": "cursor",
        "verified_by": None,
        "cluster_id": None,
    }
    return base | overrides


def _request(holdings, scenario="What if oil spikes?") -> dict:
    return {"scenario": scenario, "holdings": holdings}


# ------------------------------------------------------------------ fixture


def test_fixture_validates_against_response_model():
    WhatIfResponse.model_validate(json.loads(FIXTURE.read_text()))


def test_fixture_is_reproducible_from_generator():
    spec = importlib.util.spec_from_file_location("gen_fixture", ROOT / "scripts/gen_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build() == json.loads(FIXTURE.read_text())


def test_fixture_is_clearly_synthetic():
    data = json.loads(FIXTURE.read_text())
    assert all(h["ticker"].startswith("DEMO") for h in data["holdings"])
    assert all(p["name"].startswith("Example") for p in data["precedents"])
    assert all(p["source_url"].startswith("https://example.com/") for p in data["precedents"])
    assert data["backtest"]["available"] is False


def test_fixture_contributions_sum_to_mean():
    data = json.loads(FIXTURE.read_text())
    total = sum(h["contribution"] for h in data["holdings"])
    assert total == pytest.approx(data["portfolio"]["mean_return"], abs=1e-5)


# ------------------------------------------------------------------ request


@pytest.mark.parametrize(
    "payload",
    [
        _request([]),
        _request([{"ticker": f"T{i}", "weight": 1} for i in range(26)]),
        _request([{"ticker": "AAPL", "weight": -1}]),
        _request([{"ticker": "AAPL", "weight": 0}]),
        _request([{"ticker": "", "weight": 1}]),
        _request([{"ticker": "NOT A TICKER", "weight": 1}]),
        _request([{"ticker": "AAPL", "weight": 1}], scenario="x"),
        _request([{"ticker": "AAPL", "weight": 1}], scenario="   "),
        _request([{"ticker": "AAPL", "weight": 1}], scenario="x" * 501),
        _request([{"ticker": "AAPL", "weight": 1}]) | {"client_id": "short"},
        _request([{"ticker": "AAPL", "weight": 1}]) | {"severity": "apocalyptic"},
        _request([{"ticker": "AAPL", "weight": 1}]) | {"unexpected": 1},
    ],
)
def test_request_rejects_bad_holdings(payload):
    with pytest.raises(ValidationError):
        WhatIfRequest.model_validate(payload)


def test_weights_normalized():
    req = WhatIfRequest.model_validate(_request([{"ticker": "aapl", "weight": 2}, {"ticker": "MSFT", "weight": 2}]))
    assert [(h.ticker, h.weight) for h in req.holdings] == [("AAPL", 0.5), ("MSFT", 0.5)]
    assert req.severity is Severity.TYPICAL


def test_duplicate_tickers_merged():
    req = WhatIfRequest.model_validate(
        _request([{"ticker": "AAPL", "weight": 1}, {"ticker": " aapl ", "weight": 1}, {"ticker": "BRK.B", "weight": 2}])
    )
    assert {h.ticker: h.weight for h in req.holdings} == {"AAPL": 0.5, "BRK-B": 0.5}


def test_scenario_whitespace_collapsed():
    req = WhatIfRequest.model_validate(_request([{"ticker": "AAPL", "weight": 1}], scenario="  What   if\n oil  "))
    assert req.scenario == "What if oil"


# ------------------------------------------------------------------ enums and parsed


def test_category_enum_closed():
    assert len(Category) == 11
    with pytest.raises(ValidationError):
        Event.model_validate(_event(category="alien_invasion"))
    with pytest.raises(ValidationError):
        ParsedScenario.model_validate({"category": "alien_invasion", "search_text": "x"})


def test_parsed_scenario_nature_is_optional_and_closed():
    assert ParsedScenario(search_text="x").nature is None
    assert ParsedScenario(search_text="x", nature="adverse").nature == "adverse"
    with pytest.raises(ValidationError):
        ParsedScenario.model_validate({"search_text": "x", "nature": "terrible"})


def test_parsed_scenario_cannot_carry_numbers():
    with pytest.raises(ValidationError):
        ParsedScenario.model_validate({"search_text": "oil shock", "expected_return": -0.2})


def test_every_sector_etf_is_a_factor():
    assert set(SECTOR_ETF.values()) <= set(FACTOR_NAMES)
    assert len(FACTOR_NAMES) == len(set(FACTOR_NAMES)) == 13


def test_sector_from_yfinance():
    assert sector_from_yfinance("Technology", "Semiconductors") is Sector.SEMICONDUCTORS
    assert sector_from_yfinance("Financial Services") is Sector.FINANCIALS
    assert sector_from_yfinance("Real Estate") is Sector.BROAD
    assert sector_from_yfinance(None) is Sector.BROAD


# ------------------------------------------------------------------ event model


def test_event_valid():
    event = Event.model_validate(_event())
    assert event.date == date(2008, 9, 15)


@pytest.mark.parametrize(
    "overrides",
    [
        {"split": "holdout"},
        {"date": "2023-03-13", "split": "dev"},
        {"verified_by": "cursor"},
        {"id": "Not A Slug"},
        {"cluster_id": "Bad_Cluster"},
        {"source_url": "http://example.com/insecure"},
        {"source_quote": "too short"},
        {"regions": []},
        {"trigger": "x" * 281},
        {"extra_field": 1},
    ],
)
def test_event_rejects(overrides):
    with pytest.raises(ValidationError):
        Event.model_validate(_event(**overrides))


def test_holdout_event_valid():
    assert Event.model_validate(_event(date="2023-03-13", split="holdout", verified_by="claude")).split == "holdout"


# ------------------------------------------------------------------ response pieces


def test_portfolio_range_must_contain_median():
    base = {
        "severity": "typical", "typical_return": -0.05, "median_return": -0.05, "mean_return": -0.05,
        "range_low": -0.08, "range_high": -0.02, "worst_drawdown_63d": -0.07, "unrecovered_share": 0.0,
    }
    PortfolioOutcome.model_validate(base)
    with pytest.raises(ValidationError):
        PortfolioOutcome.model_validate(base | {"range_high": -0.06})
    with pytest.raises(ValidationError):
        PortfolioOutcome.model_validate(base | {"worst_drawdown_63d": 0.01})


def test_path_starts_at_zero():
    PathSeries(event_id="e", label="e", values=[0.0, -0.01, None])
    with pytest.raises(ValidationError):
        PathSeries(event_id="e", label="e", values=[0.01, 0.0])


# ------------------------------------------------------------------ trading calendar


def test_calendar_known_closures():
    for closed in ("2001-09-11", "2001-09-14", "2012-10-29", "2012-10-30", "2025-01-09", "2026-11-26"):
        assert not trading_calendar.is_trading_day(date.fromisoformat(closed))
    assert trading_calendar.is_trading_day(date(2008, 9, 15))
    assert not trading_calendar.is_trading_day(date(2008, 9, 13))  # Saturday


def test_calendar_arithmetic():
    assert trading_calendar.next_trading_day(date(2001, 9, 11)) == date(2001, 9, 17)
    assert trading_calendar.add_trading_days(date(2026, 11, 25), 1) == date(2026, 11, 27)
    assert trading_calendar.add_trading_days(date(2026, 11, 27), -1) == date(2026, 11, 25)
    assert trading_calendar.add_trading_days(date(2008, 9, 15), 0) == date(2008, 9, 15)
    with pytest.raises(ValueError):
        trading_calendar.add_trading_days(date(2008, 9, 13), 1)
    with pytest.raises(ValueError):
        trading_calendar.is_trading_day(date(1990, 1, 2))


def test_holiday_file_is_plausible():
    closed = trading_calendar.closed_days()
    per_year = Counter(d.year for d in closed)
    first, last = trading_calendar.coverage()
    for year in range(first.year, last.year + 1):
        assert 8 <= per_year[year] <= 13, year
    assert all(d.weekday() < 5 for d in closed)


# ------------------------------------------------------------------ stubs (the frozen signatures)

SIGNATURES = {
    factors.fit_betas: ["stock_returns", "factor_returns", "as_of", "sectors", "alpha", "stress_only", "window_years"],
    factors.estimate_return: ["fit", "factor_moves"],
    factors.factors_for: ["sector"],
    parse.parse_scenario: ["text", "client"],
    narrative.render: ["response"],
    engine.eligible_precedents: ["events", "as_of"],
    engine.score_precedents: ["query_embedding", "parsed", "library", "as_of", "settings"],
    engine.weighted_quantile: ["values", "weights", "q"],
    engine.recovery_days: ["path"],
    engine.WhatIfEngine.__init__: ["self", "library", "calibration", "embed", "parse", "load_prices", "sectors"],
    engine.WhatIfEngine.run: ["self", "request", "as_of", "parsed"],
}


@pytest.mark.parametrize("func", list(SIGNATURES), ids=lambda f: f.__qualname__)
def test_contract_signatures(func):
    assert list(inspect.signature(func).parameters) == SIGNATURES[func]


# ------------------------------------------------------------------ engine plumbing


@pytest.fixture
def clean_engine(monkeypatch):
    engine.reset_engine()
    yield monkeypatch
    engine.reset_engine()


def test_fake_engine_echoes_request(clean_engine):
    clean_engine.setenv("SCENARIO_FAKE", "1")
    req = WhatIfRequest.model_validate(
        {"scenario": "What if oil spikes?", "holdings": [{"ticker": "AAPL", "weight": 1}], "severity": "severe"}
    )
    response = engine.get_engine().run(req)
    assert response.scenario == "What if oil spikes?"
    assert response.severity is Severity.SEVERE
    assert engine.get_engine() is engine.get_engine()


def test_get_engine_unavailable_without_assets(clean_engine, tmp_path):
    clean_engine.delenv("SCENARIO_FAKE", raising=False)
    clean_engine.setattr(engine, "ASSETS_DIR", tmp_path)  # hermetic: ignore locally built assets
    with pytest.raises(engine.EngineUnavailable):
        engine.get_engine()


def test_library_dataclass_shape():
    lib = engine.Library(
        events=[Event.model_validate(_event())],
        embeddings=np.zeros((1, 384), dtype=np.float32),
        factor_names=FACTOR_NAMES,
        factor_paths=np.zeros((1, 505, len(FACTOR_NAMES)), dtype=np.float32),
        context=pd.DataFrame(),
        factor_history=pd.DataFrame(),
    )
    assert lib.factor_paths.shape[2] == len(lib.factor_names)


# =========================================================================== v2 contract (C4b-contract)

from scenario.schemas import (  # noqa: E402
    ExposureRank,
    Resilience,
    ScenarioHolding,
    ScenarioReplay,
    WhatIfResponseV2,
)

FIXTURE_V2 = ROOT / "frontend/src/lib/__fixtures__/whatif-response-v2.json"


def _gen_fixture_module():
    spec = importlib.util.spec_from_file_location("gen_fixture", ROOT / "scripts/gen_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v2() -> dict:
    return json.loads(FIXTURE_V2.read_text())


def test_v2_fixture_validates_and_is_reproducible():
    WhatIfResponseV2.model_validate(_v2())
    assert _gen_fixture_module().build_v2() == _v2()


def test_v2_fixture_is_clearly_synthetic():
    data = _v2()
    rows = data["scenarios"] + data["crises"]
    assert all(h["ticker"].startswith("DEMO") for r in rows for h in r["holdings"])
    assert all(r["name"].startswith("Example") and r["source_url"].startswith("https://example.com/") for r in rows)
    assert data["backtest"]["available"] is True
    assert data["backtest"]["holdout_events"] == 32
    assert data["backtest"]["gate_passed"] is True


def test_v2_fixture_follows_the_documented_rules():
    gen, data = _gen_fixture_module(), _v2()
    assert data["exposure"] == gen.exposure_rule(data["scenarios"])
    assert data["resilience"] == gen.resilience_rule(data["crises"])


def _replay(**overrides) -> dict:
    replay = _v2()["scenarios"][0]
    return replay | overrides


def test_replay_contributions_must_sum():
    ScenarioReplay.model_validate(_replay())
    with pytest.raises(ValidationError, match="sum"):
        ScenarioReplay.model_validate(_replay(portfolio_return_21d=0.5))


def test_replay_recovery_days_need_known_recovery():
    ScenarioReplay.model_validate(_replay(recovery_days=None, recovery_known=False))
    with pytest.raises(ValidationError, match="recovery"):
        ScenarioReplay.model_validate(_replay(recovery_days=12, recovery_known=False))


@pytest.mark.parametrize(
    "overrides",
    [
        {"path": [0.01, 0.0]},
        {"worst_drawdown_63d": 0.02},
        {"recovery_source": "guessed"},
        {"holdings": []},
        {"similarity": 1.5},
        {"extra": 1},
    ],
)
def test_replay_rejects(overrides):
    with pytest.raises(ValidationError):
        ScenarioReplay.model_validate(_replay(**overrides))


def test_response_v2_span_and_similarity_rules():
    data = _v2()
    with pytest.raises(ValidationError, match="span"):
        WhatIfResponseV2.model_validate(data | {"span_low": -0.5})
    with pytest.raises(ValidationError, match="crisis"):
        WhatIfResponseV2.model_validate(data | {"crises": [data["crises"][0] | {"similarity": 0.4}]})
    with pytest.raises(ValidationError, match="similarity"):
        WhatIfResponseV2.model_validate(data | {"scenarios": [data["scenarios"][0] | {"similarity": None}],
                                                "span_low": data["scenarios"][0]["portfolio_return_21d"],
                                                "span_high": data["scenarios"][0]["portfolio_return_21d"]})
    low = data | {"confidence": "low", "scenarios": [], "exposure": []}
    with pytest.raises(ValidationError, match="span"):
        WhatIfResponseV2.model_validate(low)
    WhatIfResponseV2.model_validate(low | {"span_low": None, "span_high": None})


def test_exposure_and_resilience_bounds():
    with pytest.raises(ValidationError):
        ExposureRank(ticker="A", mean_contribution=-0.1, most_exposed_count=4, scenarios=3)
    with pytest.raises(ValidationError):
        Resilience(worse_than_sp500=3, crises_total=2)
    with pytest.raises(ValidationError):
        Resilience(worse_than_sp500=0, crises_total=2, top_drivers=["A", "B", "C"])
    with pytest.raises(ValidationError):
        ScenarioHolding(ticker="A", weight=1.2, sector="broad", return_21d=0.0, contribution=0.0, source="actual")


V2_SIGNATURES = {
    engine.WhatIfEngine.run_v2: ["self", "request", "as_of", "parsed"],
    engine.crisis_events: ["library", "as_of"],
    engine.recovery_bucket: ["days", "known"],
    engine.exposure_ranking: ["replays"],
    engine.resilience_summary: ["crises"],
    narrative.render_v2: ["response"],
}


@pytest.mark.parametrize("func", list(V2_SIGNATURES), ids=lambda f: f.__qualname__)
def test_v2_contract_signatures(func):
    assert list(inspect.signature(func).parameters) == V2_SIGNATURES[func]


def test_v2_constants():
    assert engine.CRISIS_DRAWDOWN == -0.10
    assert engine.RECOVERY_BUCKETS == (
        "never_fell", "1-21", "22-63", "64-126", "127-252", "253-504", "not_within_504", "unknown",
    )


def test_fake_engine_run_v2_echoes_request(clean_engine):
    clean_engine.setenv("SCENARIO_FAKE", "1")
    req = WhatIfRequest.model_validate({"scenario": "What if oil spikes?", "holdings": [{"ticker": "AAPL", "weight": 1}]})
    response = engine.get_engine().run_v2(req)
    assert isinstance(response, WhatIfResponseV2)
    assert response.scenario == "What if oil spikes?"
