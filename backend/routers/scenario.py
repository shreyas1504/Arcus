"""Arcus Scenario Lab API: what-if questions answered from historical precedents."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from backend.routers.research import DailyQuota, _identity, _is_automation, _today
from scenario.engine import EngineUnavailable, FakeEngine, WhatIfEngine, get_engine
from scenario.schemas import WhatIfRequest, WhatIfResponseV2

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scenario", tags=["scenario"])

DAILY_LIMIT = 20
DEFAULT_RATE_DB = Path(
    os.getenv(
        "SCENARIO_RATE_DB",
        str(Path(os.getenv("RESEARCH_DATA_DIR", "research/data")) / "scenario_rate_limits.sqlite3"),
    )
)


def scenario_enabled() -> bool:
    return os.getenv("SCENARIO_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def get_quota() -> DailyQuota:
    return DailyQuota(DEFAULT_RATE_DB, limit=DAILY_LIMIT)


def require_enabled() -> None:
    if not scenario_enabled():
        raise HTTPException(status_code=404, detail="Scenario Lab is disabled")


def engine_dependency() -> FakeEngine | WhatIfEngine:
    try:
        return get_engine()
    except EngineUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": "Scenario Lab is warming up. Try again shortly.", "status": "warming"},
        ) from exc


@router.get("/status")
async def scenario_status() -> dict[str, Any]:
    if not scenario_enabled():
        return {"enabled": False, "status": "disabled"}
    try:
        engine = await run_in_threadpool(get_engine)
    except EngineUnavailable:
        return {"enabled": True, "status": "warming", "daily_limit": DAILY_LIMIT}
    return {
        "enabled": True,
        "status": "ready",
        "fake": isinstance(engine, FakeEngine),
        "daily_limit": DAILY_LIMIT,
    }


@router.post("/whatif", response_model=WhatIfResponseV2, dependencies=[Depends(require_enabled)])
async def what_if(
    req: WhatIfRequest,
    request: Request,
    engine: FakeEngine | WhatIfEngine = Depends(engine_dependency),
) -> WhatIfResponseV2:
    automation = _is_automation(request)
    identity = _identity(req, request)
    day = _today()
    quota = get_quota()
    used = 0 if automation else await run_in_threadpool(quota.used, identity, day)
    if used >= quota.limit:
        raise HTTPException(
            status_code=429,
            detail={"message": "Daily Scenario Lab limit reached", "remaining": 0, "reset": "00:00 UTC"},
        )

    try:
        response: WhatIfResponseV2 = await run_in_threadpool(engine.run_v2, req)
    except EngineUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": "Scenario Lab is warming up. Try again shortly.", "status": "warming"},
        ) from exc
    except Exception as exc:
        logger.exception("Scenario Lab request failed")
        raise HTTPException(
            status_code=503,
            detail={"message": "Market data is temporarily unavailable. No estimate was produced."},
        ) from exc

    try:
        remaining = quota.limit if automation else await run_in_threadpool(quota.consume, identity, day)
    except ValueError as exc:
        raise HTTPException(
            status_code=429,
            detail={"message": str(exc), "remaining": 0, "reset": "00:00 UTC"},
        ) from exc
    return response.model_copy(update={"remaining_today": remaining})
