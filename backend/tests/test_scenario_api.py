"""Scenario Lab API (PLAN.md Step 5), against FakeEngine and stub engines (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import research as research_router
from backend.routers import scenario as scenario_router
from scenario import engine as engine_module
from scenario.engine import EngineUnavailable, FakeEngine
from scenario.schemas import SkippedTicker, WhatIfRequest, WhatIfResponse

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "frontend/src/lib/__fixtures__/whatif-response.json"
CLIENT_ID = "scenario_test_client_aaaa"

app = FastAPI()
app.include_router(scenario_router.router)


def body(**overrides) -> dict:
    payload = {
        "scenario": "What if China blockades Taiwan?",
        "holdings": [{"ticker": "NVDA", "weight": 0.6}, {"ticker": "XOM", "weight": 0.4}],
        "severity": "typical",
        "client_id": CLIENT_ID,
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not ...}


class StubEngine:
    """Records requests; returns the fixture, optionally with edits, or raises."""

    def __init__(self, *, error: Exception | None = None, update: dict | None = None):
        self.error = error
        self.update = update or {}
        self.requests: list[WhatIfRequest] = []
        self._fixture = WhatIfResponse.model_validate(json.loads(FIXTURE.read_text()))

    def run(self, request: WhatIfRequest, **_: object) -> WhatIfResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self._fixture.model_copy(update={"scenario": request.scenario, **self.update}, deep=True)


@pytest.fixture
def quota(tmp_path: Path):
    return research_router.DailyQuota(tmp_path / "scenario_quota.sqlite3", limit=scenario_router.DAILY_LIMIT)


@pytest.fixture
def enabled(monkeypatch, quota):
    monkeypatch.setenv("SCENARIO_ENABLED", "true")
    monkeypatch.setenv("SCENARIO_FAKE", "1")
    monkeypatch.delenv("AUTOMATION_KEY", raising=False)
    monkeypatch.setattr(scenario_router, "get_quota", lambda: quota)
    engine_module.reset_engine()
    yield monkeypatch
    engine_module.reset_engine()
    app.dependency_overrides.clear()


@pytest.fixture
def client(enabled):
    return TestClient(app)


def use_engine(engine) -> None:
    app.dependency_overrides[scenario_router.engine_dependency] = lambda: engine


# ------------------------------------------------------------------ flag


def test_disabled_returns_404(monkeypatch, quota):
    monkeypatch.delenv("SCENARIO_ENABLED", raising=False)
    monkeypatch.setenv("SCENARIO_FAKE", "1")
    monkeypatch.setattr(scenario_router, "get_quota", lambda: quota)
    client = TestClient(app)
    assert client.post("/api/scenario/whatif", json=body()).status_code == 404
    assert client.post("/api/scenario/whatif", json=body(holdings=[])).status_code == 404
    assert client.get("/api/scenario/status").json() == {"enabled": False, "status": "disabled"}
    assert quota.used("anything", "2026-11-13") == 0


# ------------------------------------------------------------------ validation


@pytest.mark.parametrize(
    "overrides",
    [
        {"holdings": []},
        {"holdings": [{"ticker": f"T{i}", "weight": 1} for i in range(26)]},
        {"holdings": [{"ticker": "NVDA", "weight": -1}]},
        {"holdings": [{"ticker": "NVDA", "weight": 0}]},
        {"holdings": [{"ticker": "", "weight": 1}]},
        {"holdings": [{"ticker": "NOT A TICKER", "weight": 1}]},
        {"holdings": ...},
        {"scenario": "x"},
        {"scenario": "x" * 501},
        {"scenario": ...},
        {"severity": "apocalyptic"},
        {"client_id": "short"},
        {"unexpected": 1},
    ],
    ids=[
        "no-holdings", "26-holdings", "negative-weight", "zero-weight", "empty-ticker",
        "bad-ticker", "missing-holdings", "short-scenario", "long-scenario", "missing-scenario",
        "bad-severity", "bad-client-id", "extra-field",
    ],
)
def test_bad_holdings_422(client, quota, overrides):
    response = client.post("/api/scenario/whatif", json=body(**overrides))
    assert response.status_code == 422
    identity = research_router._identity(WhatIfRequest.model_validate(body()), _NoClientRequest())
    assert quota.used(identity, research_router._today()) == 0


class _NoClientRequest:
    """Identity comes from client_id, so the connecting host is irrelevant."""

    client = None


# ------------------------------------------------------------------ happy path


def test_response_matches_schema(client):
    response = client.post("/api/scenario/whatif", json=body(severity="severe"))
    assert response.status_code == 200
    data = WhatIfResponse.model_validate(response.json())
    assert data.scenario == "What if China blockades Taiwan?"
    assert data.severity == "severe"
    assert data.remaining_today == scenario_router.DAILY_LIMIT - 1


def test_fake_engine_numbers_are_the_fixture_numbers(client):
    fixture = json.loads(FIXTURE.read_text())
    data = client.post("/api/scenario/whatif", json=body()).json()
    assert data["portfolio"] == fixture["portfolio"]
    assert data["holdings"] == fixture["holdings"]
    assert data["paths"] == fixture["paths"]


def test_request_is_normalized_before_the_engine(client):
    engine = StubEngine()
    use_engine(engine)
    response = client.post(
        "/api/scenario/whatif",
        json=body(holdings=[{"ticker": "nvda", "weight": 2}, {"ticker": "NVDA", "weight": 1}, {"ticker": "brk.b", "weight": 1}]),
    )
    assert response.status_code == 200
    assert [(h.ticker, h.weight) for h in engine.requests[0].holdings] == [("NVDA", 0.75), ("BRK-B", 0.25)]


# ------------------------------------------------------------------ quota


def test_quota_429_after_limit(client):
    for index in range(scenario_router.DAILY_LIMIT):
        response = client.post("/api/scenario/whatif", json=body())
        assert response.status_code == 200, index
        assert response.json()["remaining_today"] == scenario_router.DAILY_LIMIT - index - 1
    blocked = client.post("/api/scenario/whatif", json=body())
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["remaining"] == 0


def test_quota_is_per_client(client):
    for _ in range(scenario_router.DAILY_LIMIT):
        client.post("/api/scenario/whatif", json=body())
    other = client.post("/api/scenario/whatif", json=body(client_id="scenario_test_client_bbbb"))
    assert other.status_code == 200


def test_quota_is_separate_from_research(client, quota):
    research_quota = research_router.get_quota
    assert scenario_router.get_quota() is quota
    assert research_quota is not scenario_router.get_quota
    assert scenario_router.DEFAULT_RATE_DB.name == "scenario_rate_limits.sqlite3"


def test_automation_bypasses_quota(enabled, client):
    enabled.setenv("AUTOMATION_KEY", "scenario-automation-secret")
    for _ in range(scenario_router.DAILY_LIMIT + 3):
        response = client.post(
            "/api/scenario/whatif", json=body(), headers={"X-Automation-Key": "scenario-automation-secret"}
        )
        assert response.status_code == 200
        assert response.json()["remaining_today"] == scenario_router.DAILY_LIMIT
    assert client.post("/api/scenario/whatif", json=body()).json()["remaining_today"] == scenario_router.DAILY_LIMIT - 1


def test_wrong_automation_key_is_counted(enabled, client):
    enabled.setenv("AUTOMATION_KEY", "scenario-automation-secret")
    response = client.post("/api/scenario/whatif", json=body(), headers={"X-Automation-Key": "wrong"})
    assert response.json()["remaining_today"] == scenario_router.DAILY_LIMIT - 1


def test_failed_request_does_not_consume_quota(client):
    use_engine(StubEngine(error=RuntimeError("yfinance down")))
    assert client.post("/api/scenario/whatif", json=body()).status_code == 503
    app.dependency_overrides.clear()
    assert client.post("/api/scenario/whatif", json=body()).json()["remaining_today"] == scenario_router.DAILY_LIMIT - 1


# ------------------------------------------------------------------ honesty


def test_unknown_ticker_reported(client):
    skipped = [SkippedTicker(ticker="ZZZZ", reason="no price history")]
    use_engine(StubEngine(update={"skipped": skipped}))
    data = client.post(
        "/api/scenario/whatif",
        json=body(holdings=[{"ticker": "NVDA", "weight": 1}, {"ticker": "ZZZZ", "weight": 1}]),
    ).json()
    assert data["skipped"] == [{"ticker": "ZZZZ", "reason": "no price history"}]


def test_price_source_down_returns_503_without_numbers(client):
    use_engine(StubEngine(error=RuntimeError("yfinance: no data")))
    response = client.post("/api/scenario/whatif", json=body())
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert set(detail) == {"message"}
    assert not any(char.isdigit() for char in detail["message"])


def test_empty_state_passes_through(client):
    use_engine(StubEngine(update={"portfolio": None, "holdings": [], "paths": []}))
    data = client.post("/api/scenario/whatif", json=body()).json()
    assert data["portfolio"] is None
    assert data["holdings"] == [] and data["paths"] == []


def test_engine_unavailable_during_run_returns_503(client):
    use_engine(StubEngine(error=EngineUnavailable("assets missing")))
    response = client.post("/api/scenario/whatif", json=body())
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "warming"


# ------------------------------------------------------------------ status and warm-up


def test_status_reports_warming(enabled, client):
    enabled.delenv("SCENARIO_FAKE")
    engine_module.reset_engine()
    assert client.get("/api/scenario/status").json() == {
        "enabled": True, "status": "warming", "daily_limit": scenario_router.DAILY_LIMIT,
    }
    whatif = client.post("/api/scenario/whatif", json=body())
    assert whatif.status_code == 503
    assert whatif.json()["detail"]["status"] == "warming"


def test_status_ready_with_fake_engine(client):
    status = client.get("/api/scenario/status").json()
    assert status == {"enabled": True, "status": "ready", "fake": True, "daily_limit": scenario_router.DAILY_LIMIT}
    assert isinstance(engine_module.get_engine(), FakeEngine)


def test_router_is_registered_in_main():
    from backend.main import app as main_app

    assert {"/api/scenario/status", "/api/scenario/whatif"} <= set(main_app.openapi()["paths"])
