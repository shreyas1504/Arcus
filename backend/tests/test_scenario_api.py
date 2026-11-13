"""Scenario Lab API (PLAN.md Step 5), against FakeEngine and stub engines (no network)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import research as research_router
from backend.routers import scenario as scenario_router
from research import fetch_assets as research_fetch
from scenario import engine as engine_module
from scenario import fetch_assets as scenario_fetch
from scenario import narrative as scenario_narrative
from scenario.engine import EngineUnavailable, FakeEngine
from scenario.schemas import SkippedTicker, WhatIfRequest, WhatIfResponse, WhatIfResponseV2

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "frontend/src/lib/__fixtures__/whatif-response.json"
FIXTURE_V2 = ROOT / "frontend/src/lib/__fixtures__/whatif-response-v2.json"
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
    """Records requests; returns the v2 fixture, optionally with edits, or raises."""

    def __init__(self, *, error: Exception | None = None, update: dict | None = None):
        self.error = error
        self.update = update or {}
        self.requests: list[WhatIfRequest] = []
        self._fixture = WhatIfResponseV2.model_validate(json.loads(FIXTURE_V2.read_text()))

    def run_v2(self, request: WhatIfRequest, **_: object) -> WhatIfResponseV2:
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
    data = WhatIfResponseV2.model_validate(response.json())
    assert data.scenario == "What if China blockades Taiwan?"
    assert data.remaining_today == scenario_router.DAILY_LIMIT - 1
    assert data.scenarios
    assert data.crises
    assert data.exposure
    assert data.resilience is not None


def test_fake_engine_numbers_are_the_fixture_numbers(client):
    fixture = json.loads(FIXTURE_V2.read_text())
    data = client.post("/api/scenario/whatif", json=body()).json()
    assert data["scenarios"] == fixture["scenarios"]
    assert data["crises"] == fixture["crises"]
    assert data["exposure"] == fixture["exposure"]
    assert data["span_low"] == fixture["span_low"]
    assert data["span_high"] == fixture["span_high"]
    assert data["resilience"] == fixture["resilience"]


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


def test_empty_scenarios_passes_through(client):
    from scenario.enums import Confidence

    use_engine(StubEngine(update={
        "scenarios": [], "span_low": None, "span_high": None, "exposure": [], "confidence": Confidence.LOW,
    }))
    data = client.post("/api/scenario/whatif", json=body()).json()
    assert data["scenarios"] == []
    assert data["span_low"] is None and data["span_high"] is None
    assert data["confidence"] == "low"


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


# ------------------------------------------------------------------ asset download


@pytest.fixture
def asset_archive(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    for name in scenario_fetch.MEMBERS:
        (source / name).write_bytes(name.encode())
    path = tmp_path / "scenario-assets.tar.gz"
    return path, scenario_fetch.pack(source, path)


def serve_archive(monkeypatch, path: Path) -> list[str]:
    calls: list[str] = []

    class Response:
        def __init__(self, data: bytes):
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, size):
            yield self.data

    def fake_get(url, **_):
        calls.append(url)
        return Response(path.read_bytes())

    monkeypatch.setattr(research_fetch.requests, "get", fake_get)
    return calls


def test_assets_fetch_extracts_members_once(tmp_path, monkeypatch, asset_archive):
    path, sha = asset_archive
    calls = serve_archive(monkeypatch, path)
    target = tmp_path / "assets"

    assert scenario_fetch.fetch(target, "https://example.test/s.tgz", sha)["status"] == "downloaded"
    for name in scenario_fetch.MEMBERS:
        assert (target / name).read_bytes() == name.encode()
    assert scenario_fetch.fetch(target, "https://example.test/s.tgz", sha)["status"] == "present"
    assert len(calls) == 1


def test_assets_sha_mismatch_refuses(tmp_path, monkeypatch, asset_archive):
    path, _ = asset_archive
    serve_archive(monkeypatch, path)
    target = tmp_path / "assets"

    with pytest.raises(SystemExit, match="Checksum mismatch"):
        scenario_fetch.fetch(target, "https://example.test/s.tgz", "0" * 64)
    assert not any((target / name).exists() for name in scenario_fetch.MEMBERS)


def test_assets_fetch_refuses_without_pinned_sha(tmp_path):
    with pytest.raises(SystemExit, match="SCENARIO_ASSET_SHA256"):
        scenario_fetch.fetch(tmp_path, "https://example.test/s.tgz", "")


def test_assets_archive_missing_member_refuses(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "library.npz").write_bytes(b"x")
    with pytest.raises(SystemExit, match="library.json"):
        scenario_fetch.pack(source, tmp_path / "out.tar.gz")


# ------------------------------------------------------------------ narrative template

NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def fixture_response(**updates) -> WhatIfResponse:
    response = WhatIfResponse.model_validate(json.loads(FIXTURE.read_text()))
    return response.model_copy(update={"narrative": "", **updates}, deep=True)


def allowed_numbers(response: WhatIfResponse) -> set[str]:
    """Every response number in the formats the template may print."""
    allowed: set[str] = set()
    p = response.portfolio
    if p is not None:
        for value in (p.typical_return, p.median_return, p.range_low, p.range_high,
                      p.worst_drawdown_63d, p.unrecovered_share):
            allowed.add(f"{value * 100:.1f}".replace("-0.0", "0.0"))
        allowed.add(f"{p.range_level * 100:.0f}")
        allowed.add(str(p.horizon_days))
        allowed.update(str(v) for v in (p.recovery_days_low, p.recovery_days_high) if v is not None)
    return allowed


def test_narrative_numbers_all_come_from_the_response():
    response = fixture_response()
    text = scenario_narrative.render(response)
    assert "-5.4%" in text and "-9.0%" in text and "-1.7%" in text and "80%" in text
    assert "between 34 and 118 trading days" in text
    assert set(NUMBER.findall(text)) <= allowed_numbers(response)


def test_narrative_has_no_advice_words():
    for severity in ("mild", "typical", "severe"):
        portfolio = fixture_response().portfolio.model_copy(update={"severity": severity})
        text = scenario_narrative.render(fixture_response(severity=severity, portfolio=portfolio)).lower()
        assert not re.search(r"\b(buy|sell|should|recommend|guarantee\w*)\b", text)


def test_narrative_low_confidence_sentence():
    low = scenario_narrative.render(fixture_response(confidence="low"))
    normal = scenario_narrative.render(fixture_response())
    assert "no close precedent" in low
    assert "no close precedent" not in normal


def test_narrative_without_portfolio_states_no_data_and_no_numbers():
    text = scenario_narrative.render(fixture_response(portfolio=None, holdings=[]))
    assert scenario_narrative.NO_DATA in text
    assert NUMBER.findall(text) == []


def test_narrative_unrecovered_share_and_missing_recovery():
    portfolio = fixture_response().portfolio.model_copy(
        update={"recovery_days_low": None, "recovery_days_high": None, "unrecovered_share": 0.4}
    )
    response = fixture_response(portfolio=portfolio)
    text = scenario_narrative.render(response)
    assert "trading days" not in text
    assert "40.0% of those precedents had not regained it" in text
    assert set(NUMBER.findall(text)) <= allowed_numbers(response)
