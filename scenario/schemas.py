"""Pydantic contracts for Scenario Lab (PLAN.md Step 0).

Frozen after C0 is merged: a change needs this file, the frontend fixture
(scripts/gen_fixture.py) and a STATUS.md note in the same commit.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scenario.enums import (
    HORIZON_DAYS,
    PATH_DAYS,
    RANGE_LEVEL,
    TOP_K,
    Category,
    Confidence,
    ImpactSource,
    Nature,
    Onset,
    Region,
    Sector,
    Severity,
    Split,
    Tool,
    split_for,
)

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TICKER_RE = re.compile(r"^[A-Z0-9^][A-Z0-9.\-^]{0,9}$")
CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
MAX_HOLDINGS = 25


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- events


class Event(_Strict):
    """One curated market shock. `trigger` is written as known on day 0."""

    id: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=120)
    date: date  # first trading day the market could react
    onset: Onset
    nature: Nature
    category: Category
    regions: list[Region] = Field(min_length=1)
    sectors: list[Sector] = Field(min_length=1)
    trigger: str = Field(min_length=20, max_length=280)
    source_url: str = Field(pattern=r"^https://\S+$")
    source_quote: str = Field(min_length=40, max_length=600)
    split: Split
    drafted_by: Tool
    verified_by: Tool | None = None
    cluster_id: str | None = None

    @field_validator("id", "cluster_id")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        if value is not None and not SLUG_RE.fullmatch(value):
            raise ValueError("must be a lowercase-hyphen slug")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> Event:
        if self.split != split_for(self.date):
            raise ValueError(f"split must be {split_for(self.date).value} for {self.date}")
        if self.verified_by is not None and self.verified_by == self.drafted_by:
            raise ValueError("verified_by must differ from drafted_by")
        return self


# --------------------------------------------------------------------------- request


class ParsedScenario(_Strict):
    """What the language model may return: interpretation only, never numbers."""

    category: Category | None = None
    nature: Nature | None = None  # adverse or favorable, judged from the cause (user-approved 2026-11-13)
    regions: list[Region] = Field(default_factory=list, max_length=8)
    sectors: list[Sector] = Field(default_factory=list, max_length=8)
    companies: list[str] = Field(default_factory=list, max_length=10)
    search_text: str = Field(min_length=1, max_length=500)
    fallback: bool = False  # True when parsing failed and raw text is used


class Holding(_Strict):
    ticker: str
    weight: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def _ticker(cls, value: str) -> str:
        clean = value.strip().upper().replace(".", "-")
        if not TICKER_RE.fullmatch(clean):
            raise ValueError("invalid ticker")
        return clean


class WhatIfRequest(_Strict):
    scenario: str = Field(min_length=2, max_length=500)
    holdings: list[Holding] = Field(min_length=1, max_length=MAX_HOLDINGS)
    severity: Severity = Severity.TYPICAL
    client_id: str | None = None

    @field_validator("scenario")
    @classmethod
    def _scenario(cls, value: str) -> str:
        clean = " ".join(value.split())
        if len(clean) < 2:
            raise ValueError("scenario is empty")
        return clean

    @field_validator("client_id")
    @classmethod
    def _client_id(cls, value: str | None) -> str | None:
        if value is not None and not CLIENT_ID_RE.fullmatch(value):
            raise ValueError("invalid client_id")
        return value

    @model_validator(mode="after")
    def _merge_and_normalize(self) -> WhatIfRequest:
        merged: dict[str, float] = {}
        for holding in self.holdings:
            merged[holding.ticker] = merged.get(holding.ticker, 0.0) + holding.weight
        total = sum(merged.values())
        self.holdings = [Holding(ticker=t, weight=w / total) for t, w in merged.items()]
        return self


# --------------------------------------------------------------------------- response


class Precedent(_Strict):
    event_id: str
    name: str
    date: date
    category: Category
    nature: Nature
    trigger: str
    similarity: float = Field(ge=-1, le=1)
    weight: float = Field(ge=0, le=1)  # similarity weight used in the quantiles
    sp500_return_21d: float | None  # None when the window is not complete
    portfolio_return_21d: float | None
    source_url: str


class PortfolioOutcome(_Strict):
    """All returns are fractions (-0.08 means -8%), over HORIZON_DAYS trading days."""

    horizon_days: int = HORIZON_DAYS
    range_level: float = RANGE_LEVEL
    severity: Severity
    typical_return: float  # the outcome for the selected severity
    median_return: float  # similarity-weighted median of precedent outcomes
    mean_return: float  # similarity-weighted mean; equals the sum of holding contributions
    range_low: float
    range_high: float
    worst_drawdown_63d: float = Field(le=0)
    recovery_days_low: int | None = Field(default=None, ge=0)
    recovery_days_high: int | None = Field(default=None, ge=0)
    unrecovered_share: float = Field(ge=0, le=1)  # share of precedents not recovered in 504 days

    @model_validator(mode="after")
    def _ordered(self) -> PortfolioOutcome:
        if not self.range_low <= self.median_return <= self.range_high:
            raise ValueError("range must contain the median")
        if (
            self.recovery_days_low is not None
            and self.recovery_days_high is not None
            and self.recovery_days_low > self.recovery_days_high
        ):
            raise ValueError("recovery range is reversed")
        return self


class HoldingImpact(_Strict):
    ticker: str
    weight: float = Field(ge=0, le=1)
    sector: Sector
    return_21d: float  # similarity-weighted mean across precedents
    contribution: float  # weight x return_21d; contributions sum to PortfolioOutcome.mean_return
    source: ImpactSource  # the dominant source across precedents
    actual_share: float = Field(ge=0, le=1)  # share of precedent weight with actual prices


class SkippedTicker(_Strict):
    ticker: str
    reason: str


class PathSeries(_Strict):
    """Cumulative portfolio return after one precedent, t = 0..PATH_DAYS (t=0 is day -1 close, 0.0)."""

    event_id: str
    label: str
    values: list[float | None] = Field(min_length=1, max_length=PATH_DAYS + 1)

    @field_validator("values")
    @classmethod
    def _starts_at_zero(cls, values: list[float | None]) -> list[float | None]:
        if values[0] != 0.0:
            raise ValueError("paths start at 0.0")
        return values


class MetricCI(_Strict):
    value: float
    ci_low: float
    ci_high: float


class BacktestSummary(_Strict):
    """Holdout results from scenario/eval/calibration.json; `available` is False until C5."""

    available: bool
    holdout_events: int | None = None
    coverage_80: MetricCI | None = None
    width_ratio: MetricCI | None = None
    mae: MetricCI | None = None
    mae_best_baseline: MetricCI | None = None
    rank_corr: MetricCI | None = None
    gate_passed: bool | None = None
    results_url: str | None = None


class WhatIfResponse(_Strict):
    scenario: str
    parsed: ParsedScenario
    as_of: date
    severity: Severity
    confidence: Confidence
    precedents: list[Precedent] = Field(max_length=TOP_K)
    portfolio: PortfolioOutcome | None  # None: no usable data, show an empty state
    holdings: list[HoldingImpact]
    skipped: list[SkippedTicker] = Field(default_factory=list)
    paths: list[PathSeries] = Field(default_factory=list, max_length=TOP_K)
    narrative: str
    backtest: BacktestSummary
    remaining_today: int | None = None
