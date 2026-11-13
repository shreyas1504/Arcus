"""Backtest checks (PLAN.md Step 4): no leakage, engine-consistent maths, honest metrics."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scenario import backtest as bt
from scenario import engine as E
from scenario import trading_calendar
from scenario.enums import FACTOR_NAMES, PATH_DAYS, RECOVERY_DAYS, Sector, Split
from scenario.schemas import Event, ParsedScenario, WhatIfRequest

F = list(FACTOR_NAMES)
STOCKS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]
SECTORS = {"AAA": Sector.TECHNOLOGY, "BBB": Sector.TECHNOLOGY, "CCC": Sector.FINANCIALS,
           "DDD": Sector.ENERGY, "EEE": Sector.UTILITIES, "FFF": Sector.SEMICONDUCTORS}


def _event(i: int, day: date, category: str, nature: str) -> Event:
    return Event.model_validate(
        {
            "id": f"shock-{i:02d}", "name": f"Example shock {i}", "date": day.isoformat(), "onset": "sudden",
            "nature": nature, "category": category, "regions": ["us"], "sectors": ["broad"],
            "trigger": "An example shock happens to an example market today.",
            "source_url": "https://example.com/source",
            "source_quote": "An example quote that is long enough to pass the schema length check.",
            "split": "dev", "drafted_by": "claude", "verified_by": "cursor",
        }
    )


@pytest.fixture(scope="module")
def world():
    """A small library, prices and query vectors with real structure (betas, moves)."""
    rng = np.random.default_rng(7)
    days = pd.DatetimeIndex([pd.Timestamp(d) for d in E._calendar()[0] if date(2009, 1, 1) <= d <= date(2017, 12, 29)])
    factors = pd.DataFrame(rng.normal(0, 0.01, (len(days), len(F))), index=days, columns=F)
    betas = {s: rng.uniform(0.5, 1.5, len(F)) * (rng.random(len(F)) < 0.4) for s in STOCKS}
    returns = pd.DataFrame({s: factors.to_numpy() @ betas[s] + rng.normal(0, 0.004, len(days)) for s in STOCKS}, index=days)
    prices = 100 * (1 + returns).cumprod()
    prices.loc[prices.index < pd.Timestamp("2013-06-03"), "FFF"] = np.nan  # a later listing

    categories = ["financial_credit", "energy_oil", "geopolitical_conflict", "monetary_policy"]
    event_days = [d for d in E._calendar()[0] if date(2012, 1, 3) <= d <= date(2016, 12, 1)][::45]
    events = [_event(i, d, categories[i % 4], "adverse" if i % 3 else "favorable") for i, d in enumerate(event_days)]
    n = len(events)
    pos = {d: k for k, d in enumerate(days)}
    paths = np.full((n, RECOVERY_DAYS + 1, len(F)), np.nan, dtype=np.float32)
    levels = (1 + factors).cumprod()
    for i, e in enumerate(events):
        start = pos[pd.Timestamp(E._path_dates(e.date, 0)[0])]
        window = levels.iloc[start : start + RECOVERY_DAYS + 1].to_numpy()
        paths[i, : len(window)] = window / window[0] - 1
    emb = rng.normal(size=(n, 16)).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    queries = rng.normal(size=(n, 16))
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    library = E.Library(events=events, embeddings=emb, factor_names=tuple(F), factor_paths=paths,
                        context=pd.DataFrame(index=[e.id for e in events]), factor_history=factors)
    return library, prices, queries


@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(bt, "MIN_ELIGIBLE", 5)
    monkeypatch.setattr(bt, "MIN_HISTORY", 120)
    monkeypatch.setattr(bt, "N_RANDOM", 8)
    monkeypatch.setattr(bt, "SIZE_RANGE", (2, 4))


def _cases(world, **kw):
    library, prices, queries = world
    return bt.build_cases(library, prices, SECTORS, queries, **kw)


# ------------------------------------------------------------------ maths


def test_weighted_quantile_columns_matches_engine():
    rng = np.random.default_rng(1)
    for _ in range(50):
        k, p = rng.integers(1, 8), rng.integers(1, 6)
        values, weights = rng.normal(size=(k, p)), rng.random(k) + 0.01
        for q in (0.1, 0.5, 0.75, 0.9):
            expected = [E.weighted_quantile(values[:, c], weights, q) for c in range(p)]
            np.testing.assert_allclose(bt.weighted_quantile_columns(values, weights, q), expected)


@pytest.mark.parametrize("threshold,use_actual", [(-1.0, True), (-1.0, False), (2.0, True)])
def test_vectorized_prediction_matches_whatif_engine(world, small, threshold, use_actual):
    library, prices, queries = world
    cases, _ = _cases(world)
    case = cases[-1]
    settings = bt.Settings(threshold, 0.05, 0.1, 1.0, False, use_actual)
    q_hat = 1.3
    pred = bt.predict(case, settings)
    j = [e.id for e in library.events].index(case.event.id)
    engine = E.WhatIfEngine(
        library, E.Calibration(q_hat=q_hat, settings=settings.engine_settings()),
        embed=lambda text: queries[j], parse=None,
        load_prices=lambda tickers, start, end: prices[tickers],
        sectors=lambda tickers: {t: SECTORS[t] for t in tickers},
    )
    for p in (0, 3, len(case.weights) - 1):
        holdings = [{"ticker": s, "weight": float(w)} for s, w in zip(case.stocks, case.weights[p]) if w > 0]
        parsed = ParsedScenario(search_text="x", category=case.event.category, nature=case.event.nature)
        response = engine.run(WhatIfRequest(scenario="what if", holdings=holdings), as_of=case.event.date, parsed=parsed)
        assert response.portfolio.median_return == pytest.approx(pred.median[p], abs=1e-9)
        assert response.portfolio.range_low == pytest.approx(pred.median[p] - q_hat * pred.spread[p], abs=1e-9)
        assert response.portfolio.range_high == pytest.approx(pred.median[p] + q_hat * pred.spread[p], abs=1e-9)
        assert [x.event_id for x in response.precedents] == pred.used[: settings.top_k]


# ------------------------------------------------------------------ leakage


def test_no_future_precedents(world, small):
    library, _, _ = world
    cases, _ = _cases(world)
    assert cases
    for case in cases:
        for i in case.eligible:
            precedent = library.events[i]
            assert trading_calendar.add_trading_days(precedent.date, PATH_DAYS - 1) < case.event.date


def test_betas_fit_before_event(world, small):
    library, prices, queries = world
    clean, _ = _cases(world)
    target = clean[-1]
    keep = {pd.Timestamp(d) for d in E._path_dates(target.event.date, 21)[::21]}  # realized endpoints
    poisoned = prices.copy()
    after = (poisoned.index >= pd.Timestamp(target.event.date)) & ~poisoned.index.isin(keep)
    poisoned.loc[after] = 1e6
    dirty, _ = bt.build_cases(library, poisoned, SECTORS, queries, only=[target.event.id])
    for key, matrix in target.estimates.items():
        np.testing.assert_allclose(dirty[0].estimates[key], matrix)
    np.testing.assert_allclose(dirty[0].y_stock, target.y_stock)


def test_holdout_untouched_during_tuning(world, small):
    cases, _ = _cases(world)
    cases[0].split = Split.HOLDOUT
    with pytest.raises(bt.BacktestError, match="holdout"):
        bt.tune(cases)


def test_settings_hash_changes_with_settings_and_q():
    a = bt.settings_hash(bt.DEFAULT_SETTINGS, 1.2)
    assert a == bt.settings_hash(bt.DEFAULT_SETTINGS, 1.2)
    assert a != bt.settings_hash(bt.DEFAULT_SETTINGS, 1.3)
    assert a != bt.settings_hash(bt.Settings(0.6, 0.05, 0.0, 1.0, False, True), 1.2)


def test_holdout_cli_refuses_without_permission(monkeypatch):
    monkeypatch.delenv("SCENARIO_RUN_HOLDOUT", raising=False)
    assert bt.main(["holdout"]) == 2


# ------------------------------------------------------------------ calibration and metrics


def test_conformal_coverage_synthetic():
    rng = np.random.default_rng(3)
    calibration = [np.abs(rng.standard_t(4, size=rng.integers(5, 300))) for _ in range(400)]
    q = bt.conformal_q(calibration)
    test = [np.abs(rng.standard_t(4, size=rng.integers(5, 300))) for _ in range(400)]
    coverage = np.mean([np.mean(s <= q) for s in test])
    assert 0.77 <= coverage <= 0.83


def _scores(**overrides) -> bt.EventScores:
    base = dict(event_id="e", category="energy_oil", n_portfolios=10, coverage=0.8, width=0.1, mae=0.05,
                rank=0.3, b1_mae=0.06, b2_mae=0.07, b3_mae=0.08, b3_width=0.2, low_confidence=False)
    return bt.EventScores(**(base | overrides))


def test_event_weighting():
    summary = bt.summarize([_scores(n_portfolios=206, coverage=1.0), _scores(n_portfolios=6, coverage=0.0)], resamples=50)
    assert summary["coverage_80"]["value"] == pytest.approx(0.5)


def test_bootstrap_resamples_events():
    same = bt.summarize([_scores(), _scores()], resamples=200)
    assert same["mae"]["ci_low"] == same["mae"]["ci_high"] == pytest.approx(0.05)
    mixed = bt.summarize([_scores(mae=0.01, event_id="a"), _scores(mae=0.09, event_id="b")], resamples=200)
    assert mixed["mae"]["ci_low"] < 0.05 < mixed["mae"]["ci_high"]


def test_width_ratio_and_improvement():
    summary = bt.summarize([_scores(width=0.1, b3_width=0.2, mae=0.045, b1_mae=0.05, b2_mae=0.09, b3_mae=0.07)], resamples=10)
    assert summary["width_ratio"]["value"] == pytest.approx(0.5)
    assert summary["mae_best_baseline"]["value"] == pytest.approx(0.05)
    assert summary["mae_improvement"]["value"] == pytest.approx(0.10)


def test_gate_thresholds():
    summary = bt.summarize([_scores(coverage=0.8, width=0.1, b3_width=0.2, mae=0.04, b1_mae=0.05, rank=0.35)], resamples=10)
    assert all(bt.gate(summary).values())
    worse = bt.summarize([_scores(coverage=0.9, width=0.19, b3_width=0.2, mae=0.049, b1_mae=0.05, rank=0.1)], resamples=10)
    assert not any(bt.gate(worse).values())


def test_baselines_scored_on_same_cases(world, small):
    cases, _ = _cases(world)
    case = cases[-1]
    b1, b2 = bt.baseline_predictions(case)
    assert b1.shape == b2.shape == case.b3_median.shape == (len(case.weights),)
    score = bt.score_event(case, bt.DEFAULT_SETTINGS, 1.0)
    pred = bt.predict(case, bt.DEFAULT_SETTINGS)
    assert score.b1_mae == pytest.approx(np.mean(np.abs(pred.y - b1)))
    assert score.n_portfolios == len(pred.y)


def test_portfolios_are_equal_weight_and_include_archetypes(world, small):
    cases, _ = _cases(world)
    case = cases[-1]
    np.testing.assert_allclose(case.weights.sum(axis=1), 1.0)
    assert case.portfolio_names[: bt.N_RANDOM] == [f"random-{p:03d}" for p in range(bt.N_RANDOM)]
    assert "balanced" in case.portfolio_names


def test_grid_contains_defaults():
    assert bt.DEFAULT_SETTINGS in bt.grid()
    assert len(bt.grid()) == np.prod([len(v) for v in bt.GRID.values()])


# ------------------------------------------------------------------ ship gate (C5)


def test_ship_gate():
    path = Path(bt.EVAL_DIR) / "calibration.json"
    if not path.exists() or json.loads(path.read_text()).get("stage") != "holdout":
        pytest.skip("the holdout has not been run (C5)")
    calibration = json.loads(path.read_text())
    assert all(calibration["holdout_gate"].values()), calibration["holdout_gate"]


def test_diagnostics_reports_forecast_and_conditional(world, small):
    library, prices, queries = world
    cases, _ = _cases(world)
    table = bt.diagnostics(library, prices, SECTORS, cases, bt.DEFAULT_SETTINGS)
    assert len(table) == len(cases)
    for column in ("forecast_engine", "forecast_zero", "conditional_beta_spx", "conditional_factor_a1.0", "rank_factor_a0.1"):
        assert column in table and table[column].notna().any()
    # Given the true factor moves, the factor model must beat predicting zero on this world.
    assert table["conditional_factor_a0.1"].mean() < table["forecast_zero"].mean()


def test_dev_run_never_makes_the_engine_available():
    source = Path(bt.__file__).read_text()
    assert '"calibration_dev.json"' in source
    assert 'EVAL_DIR / "calibration.json").write_text' not in source
