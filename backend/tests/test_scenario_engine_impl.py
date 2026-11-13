"""Implementer tests for scenario/engine.py (Claude, C3).

Cursor's blind tests live in test_scenario_engine.py; these cover the details C3
added or corrected (see the engine docstring) and the production wiring.
"""

from __future__ import annotations

import json
import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from scenario import engine as E
from scenario.enums import FACTOR_NAMES, PATH_DAYS, RECOVERY_DAYS, Confidence, ImpactSource, Sector
from scenario.schemas import Event, ParsedScenario, WhatIfRequest

F = list(FACTOR_NAMES)
AS_OF = date(2018, 6, 1)


def _event(event_id: str, day: str, category: str = "financial_credit") -> Event:
    return Event.model_validate(
        {
            "id": event_id, "name": f"Example {event_id}", "date": day, "onset": "sudden", "nature": "adverse",
            "category": category, "regions": ["us"], "sectors": ["broad"],
            "trigger": "An example shock happens to an example market today.",
            "source_url": "https://example.com/source",
            "source_quote": "An example quote that is long enough to pass the schema length check.",
            "split": "dev", "drafted_by": "claude", "verified_by": "cursor",
        }
    )


def _library(events: list[Event], spy_21d: list[float], *, soxx_nan: bool = False) -> E.Library:
    n = len(events)
    paths = np.zeros((n, RECOVERY_DAYS + 1, len(F)), dtype=np.float32)
    for i, move in enumerate(spy_21d):
        ramp = np.linspace(0, move, 22)
        paths[i, :22, :] = ramp[:, None]
        paths[i, 22:, :] = move
    if soxx_nan:
        paths[:, :, F.index("SOXX")] = np.nan
    emb = np.eye(n, 8, dtype=np.float32)
    days = pd.bdate_range("2014-01-01", "2018-12-31")
    rng = np.random.default_rng(0)
    history = pd.DataFrame(rng.normal(0, 0.01, (len(days), len(F))), index=days, columns=F)
    return E.Library(
        events=events, embeddings=emb, factor_names=tuple(F), factor_paths=paths,
        context=pd.DataFrame(index=[e.id for e in events]), factor_history=history,
    )


def _engine(library, *, prices=None, sectors=None, threshold=0.5, calls=None):
    def load_prices(tickers, start, end):
        if calls is not None:
            calls.append((tuple(tickers), start, end))
        return prices if prices is not None else pd.DataFrame()

    settings = E.EngineSettings(similarity_threshold=threshold, category_bonus=0.0)
    return E.WhatIfEngine(
        library, E.Calibration(q_hat=1.5, settings=settings),
        embed=lambda text: np.eye(1, 8, 0, dtype=np.float32)[0],
        parse=lambda text: ParsedScenario(search_text=text, fallback=True),
        load_prices=load_prices,
        sectors=sectors or (lambda tickers: {t: Sector.BROAD for t in tickers}),
    )


def _request(*tickers):
    return WhatIfRequest(scenario="what if", holdings=[{"ticker": t, "weight": 1} for t in tickers])


# ------------------------------------------------------------------ recovery


def test_recovery_ignores_a_later_unrelated_crash():
    # Dips, regains its start on day 4, rallies, then a crash 400 days later goes lower.
    path = [0.0, -0.01, -0.02, -0.01, 0.01] + [0.5] * 395 + [-0.2] * 105
    assert E.recovery_days(path) == 4


def test_recovery_trough_is_within_the_shock_window():
    path = [0.0] + [-0.05] * PATH_DAYS + [0.01] * 10
    assert E.recovery_days(path) == PATH_DAYS + 1


def test_recovery_none_when_never_regained_in_observed_part():
    assert E.recovery_days([0.0, -0.1, -0.05, None, 0.2]) is None


# ------------------------------------------------------------------ engine behaviour


def test_prices_on_or_after_as_of_are_never_used_and_loader_called_once():
    events = [_event("a-shock", "2015-06-01")]
    days = pd.bdate_range("2014-01-01", "2018-12-31")
    prices = pd.DataFrame({"AAA": np.linspace(100, 150, len(days))}, index=days)
    prices.loc[prices.index >= pd.Timestamp(AS_OF), "AAA"] = 1e9  # poison
    calls = []
    response = _engine(_library(events, [-0.05]), prices=prices, threshold=0.0, calls=calls).run(
        _request("AAA"), as_of=AS_OF
    )
    assert len(calls) == 1 and calls[0][2] == AS_OF
    assert calls[0][1] <= date(2015, 5, 29)
    assert abs(response.holdings[0].return_21d) < 0.1


def test_soxx_proxy_uses_xlk_before_soxx_listed():
    events = [_event("old-chip-shock", "2000-09-22", "tech_sector")]
    lib = _library(events, [-0.10], soxx_nan=True)
    days = pd.bdate_range("2015-01-01", "2018-05-31")
    rng = np.random.default_rng(1)
    hist = lib.factor_history
    chip = 1.0 * hist.loc[days, "SPY"] + 0.5 * hist.loc[days, "SOXX"] + rng.normal(0, 0.001, len(days))
    prices = pd.DataFrame({"CHIP": 100 * (1 + chip).cumprod()}, index=days)
    engine = _engine(lib, prices=prices, threshold=0.0, sectors=lambda t: {"CHIP": Sector.SEMICONDUCTORS})
    response = engine.run(_request("CHIP"), as_of=AS_OF)
    holding = response.holdings[0]
    assert holding.source is ImpactSource.ESTIMATED
    assert math.isfinite(holding.return_21d) and holding.return_21d < 0


def test_low_confidence_uses_every_eligible_event_equally():
    events = [_event(f"shock-{i}", d) for i, d in enumerate(["2015-03-02", "2015-09-01", "2016-03-01", "2016-09-01"])]
    lib = _library(events, [-0.10, -0.02, 0.03, 0.08])
    days = pd.bdate_range("2014-01-01", "2018-05-31")
    prices = pd.DataFrame({"AAA": 100 * (1 + lib.factor_history.loc[days, "SPY"]).cumprod()}, index=days)
    response = _engine(lib, prices=prices, threshold=1.01).run(_request("AAA"), as_of=AS_OF)  # no cosine can clear 1.01
    assert response.confidence is Confidence.LOW
    assert all(p.weight == pytest.approx(0.25) for p in response.precedents)


def test_unknown_ticker_is_skipped_and_rest_renormalized():
    events = [_event("a-shock", "2015-06-01")]
    days = pd.bdate_range("2014-01-01", "2018-05-31")
    prices = pd.DataFrame({"AAA": np.linspace(100, 120, len(days))}, index=days)
    response = _engine(_library(events, [-0.05]), prices=prices, threshold=0.0).run(
        _request("AAA", "ZZZZ"), as_of=AS_OF
    )
    assert [s.ticker for s in response.skipped] == ["ZZZZ"]
    assert response.holdings[0].weight == pytest.approx(1.0)


def test_no_price_data_gives_empty_state_not_numbers():
    events = [_event("a-shock", "2015-06-01")]
    response = _engine(_library(events, [-0.05]), threshold=0.0).run(_request("AAA"), as_of=AS_OF)
    assert response.portfolio is None and response.holdings == []
    assert response.skipped[0].reason == "no price data"


def test_context_weight_is_rejected():
    lib = _library([_event("a-shock", "2015-06-01")], [-0.05])
    with pytest.raises(ValueError, match="context_weight"):
        E.score_precedents(np.ones(8), ParsedScenario(search_text="x"), lib, AS_OF, E.EngineSettings(context_weight=0.1))


# ------------------------------------------------------------------ production wiring


def test_build_default_engine_needs_assets_and_calibration(tmp_path, monkeypatch):
    from backend.tests.test_scenario_build import DAYS, _embed, _ev, _frames
    from scenario import build_library

    with pytest.raises(E.EngineUnavailable, match="assets"):
        E.build_default_engine(tmp_path / "missing")

    built = build_library.build(_frames(DAYS), [_ev("a-shock", "2015-06-01")], _embed)
    build_library.write(built, tmp_path, manifest_sha256="x")
    monkeypatch.setenv("SCENARIO_CALIBRATION", str(tmp_path / "calibration.json"))
    with pytest.raises(E.EngineUnavailable, match="calibration"):
        E.build_default_engine(tmp_path)

    (tmp_path / "calibration.json").write_text(
        json.dumps({"q_hat": 1.2, "settings": {"alpha": 0.5}, "backtest": {"available": False}})
    )
    engine = E.build_default_engine(tmp_path)
    assert isinstance(engine, E.WhatIfEngine)
    assert engine.calibration.q_hat == 1.2 and engine.calibration.settings.alpha == 0.5


def test_load_calibration_rejects_context_weight(tmp_path):
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"q_hat": 1.0, "settings": {"context_weight": 0.2}, "backtest": {"available": False}}))
    with pytest.raises(ValueError, match="context_weight"):
        E.load_calibration(path)


def test_negative_q_hat_rejected():
    with pytest.raises(ValueError):
        E.WhatIfEngine(
            _library([_event("a-shock", "2015-06-01")], [0.0]), E.Calibration(q_hat=-1.0),
            embed=None, parse=None, load_prices=None, sectors=None,
        )


def test_nature_penalty_demotes_opposite_events():
    events = [_event("rescue", "2015-06-01"), _event("crash", "2015-09-01")]
    events[0] = events[0].model_copy(update={"nature": "favorable"})
    lib = _library(events, [0.05, -0.05])
    query = np.array([1.0, 0.9, 0, 0, 0, 0, 0, 0])  # closer to "rescue"
    parsed = ParsedScenario(search_text="x", nature="adverse")
    off = E.score_precedents(query, parsed, lib, AS_OF, E.EngineSettings(category_bonus=0.0))
    on = E.score_precedents(query, parsed, lib, AS_OF, E.EngineSettings(category_bonus=0.0, nature_penalty=0.2))
    assert [lib.events[s.index].id for s in off] == ["rescue", "crash"]
    assert [lib.events[s.index].id for s in on] == ["crash", "rescue"]
    unknown = E.score_precedents(query, ParsedScenario(search_text="x"), lib, AS_OF, E.EngineSettings(nature_penalty=0.2))
    assert [lib.events[s.index].id for s in unknown] == ["rescue", "crash"]  # no nature parsed: no penalty
