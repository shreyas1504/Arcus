"""Arcus Research API: filing-only answers with structured SEC citations."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from backend.config import RESEARCH_TICKER_UNIVERSE
from research.qa import QAResult, ResearchQA

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/research", tags=["research"])

DAILY_LIMIT = 20
CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
DEFAULT_RATE_DB = Path(
    os.getenv(
        "RESEARCH_RATE_DB",
        str(Path(os.getenv("RESEARCH_DATA_DIR", "research/data")) / "research_rate_limits.sqlite3"),
    )
)
_qa_service: ResearchQA | None = None
_qa_lock = threading.Lock()


def research_enabled() -> bool:
    return os.getenv("RESEARCH_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


class ResearchAskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    tickers: list[str] = Field(min_length=1, max_length=len(RESEARCH_TICKER_UNIVERSE))
    client_id: str | None = None

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        clean = value.strip()
        if len(clean) < 2:
            raise ValueError("Question is empty")
        return clean

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, values: list[str]) -> list[str]:
        clean = list(dict.fromkeys(value.strip().upper().replace(".", "-") for value in values))
        unsupported = sorted(set(clean) - set(RESEARCH_TICKER_UNIVERSE))
        if unsupported:
            raise ValueError(f"Unsupported research tickers: {', '.join(unsupported)}")
        return clean

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not CLIENT_ID_RE.fullmatch(value):
            raise ValueError("Invalid client_id")
        return value


class ResearchCitation(BaseModel):
    citation: int
    chunk_id: str
    ticker: str
    form: str
    filing_date: str
    year: str
    section: str
    url: str
    excerpt: str


class ResearchAskResponse(BaseModel):
    answer: str
    citations: list[ResearchCitation]
    latency_ms: int
    retrieved_sections: list[str]
    remaining_today: int


class DailyQuota:
    def __init__(self, path: Path = DEFAULT_RATE_DB, limit: int = DAILY_LIMIT):
        self.path = path
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_usage (
                    identity_hash TEXT NOT NULL,
                    day TEXT NOT NULL,
                    question_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (identity_hash, day)
                )
                """
            )

    def used(self, identity_hash: str, day: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT question_count FROM research_usage WHERE identity_hash = ? AND day = ?",
                (identity_hash, day),
            ).fetchone()
        return int(row[0]) if row else 0

    def consume(self, identity_hash: str, day: str) -> int:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            used = self.used_with_connection(connection, identity_hash, day)
            if used >= self.limit:
                connection.rollback()
                raise ValueError("Daily research limit reached")
            next_count = used + 1
            connection.execute(
                """
                INSERT INTO research_usage(identity_hash, day, question_count)
                VALUES (?, ?, ?)
                ON CONFLICT(identity_hash, day)
                DO UPDATE SET question_count = excluded.question_count
                """,
                (identity_hash, day, next_count),
            )
            connection.commit()
        return self.limit - next_count

    @staticmethod
    def used_with_connection(
        connection: sqlite3.Connection, identity_hash: str, day: str
    ) -> int:
        row = connection.execute(
            "SELECT question_count FROM research_usage WHERE identity_hash = ? AND day = ?",
            (identity_hash, day),
        ).fetchone()
        return int(row[0]) if row else 0


def _identity(req: ResearchAskRequest, request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    raw = f"client:{req.client_id}" if req.client_id else f"ip:{host}"
    salt = os.getenv("RATE_LIMIT_SALT", "arcus-research")
    return hashlib.sha256(f"{salt}:{raw}".encode("utf-8")).hexdigest()


def _is_automation(request: Request) -> bool:
    expected = os.getenv("AUTOMATION_KEY", "")
    supplied = request.headers.get("X-Automation-Key", "")
    return bool(expected) and hmac.compare_digest(supplied.encode(), expected.encode())


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def get_qa_service() -> ResearchQA:
    global _qa_service
    with _qa_lock:
        if _qa_service is None:
            _qa_service = ResearchQA()
        return _qa_service


def get_quota() -> DailyQuota:
    return DailyQuota()


@router.get("/status")
async def research_status() -> dict[str, Any]:
    if not research_enabled():
        return {"enabled": False, "ready": False}
    service = get_qa_service()
    ready = await run_in_threadpool(service.ready)
    return {
        "enabled": True,
        "ready": ready,
        "universe": RESEARCH_TICKER_UNIVERSE,
        "daily_limit": DAILY_LIMIT,
    }


@router.post("/ask", response_model=ResearchAskResponse)
async def ask_research(req: ResearchAskRequest, request: Request):
    if not research_enabled():
        raise HTTPException(status_code=404, detail="Arcus Research is disabled")

    automation = _is_automation(request)
    identity = _identity(req, request)
    day = _today()
    quota = get_quota()
    used = 0 if automation else await run_in_threadpool(quota.used, identity, day)
    if used >= quota.limit:
        raise HTTPException(
            status_code=429,
            detail={"message": "Daily research limit reached", "remaining": 0, "reset": "00:00 UTC"},
        )

    service = get_qa_service()
    started = time.perf_counter()
    try:
        result: QAResult = await run_in_threadpool(service.answer, req.question, req.tickers)
    except Exception as exc:
        logger.exception("Arcus Research request failed")
        raise HTTPException(status_code=503, detail="Research service temporarily unavailable") from exc

    try:
        remaining = quota.limit if automation else await run_in_threadpool(quota.consume, identity, day)
    except ValueError as exc:
        raise HTTPException(
            status_code=429,
            detail={"message": str(exc), "remaining": 0, "reset": "00:00 UTC"},
        ) from exc
    latency_ms = round((time.perf_counter() - started) * 1000)
    return ResearchAskResponse(
        answer=result.answer,
        citations=[ResearchCitation(**citation) for citation in result.citations],
        latency_ms=latency_ms,
        retrieved_sections=result.retrieved_sections,
        remaining_today=remaining,
    )

