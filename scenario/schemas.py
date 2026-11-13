"""Pydantic contracts for Scenario Lab (PLAN.md Step 0).

Frozen after C0 is merged: a change needs this file, the frontend fixture
(scripts/gen_fixture.py) and a STATUS.md note in the same commit.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

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


# =========================================================================== v2: stress test
# PLAN.md section "v2" (approved 2026-11-13). Added next to v1; the router and page switch
# to v2 in U4b, and v1 is removed in C6 cleanup. Every replay is history applied to today's
# holdings, never a forecast.

RecoverySource = Literal["actual", "estimated", "mixed"]
CONTRIBUTION_TOLERANCE = 1e-6


class ScenarioHolding(_Strict):
    """One holding replayed through one past shock."""

    ticker: str
    weight: float = Field(ge=0, le=1)
    sector: Sector
    return_21d: float  # actual if it traded then, else factor estimate (see `source`)
    contribution: float  # weight x return_21d
    source: ImpactSource
    recovery_days: int | None = Field(default=None, ge=0)  # None: not recovered, unknown, or not shown


class ScenarioReplay(_Strict):
    """A past shock replayed on the user's holdings: what happened, applied to today."""

    event_id: str
    name: str
    date: date
    category: Category
    nature: Nature
    trigger: str
    similarity: float | None = Field(ge=-1, le=1)  # None for crisis-replay rows
    source_url: str
    portfolio_return_21d: float
    sp500_return_21d: float | None
    worst_drawdown_63d: float = Field(le=0)
    sp500_worst_drawdown_63d: float | None = Field(le=0)
    recovery_days: int | None = Field(ge=0)  # trading days to regain the start; see recovery_known
    recovery_known: bool  # True: recovered, or observed for all 504 days without recovering
    recovery_source: RecoverySource
    path: list[float | None] = Field(min_length=1, max_length=PATH_DAYS + 1)  # cumulative, t = 0..63
    holdings: list[ScenarioHolding] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> ScenarioReplay:
        if self.path[0] != 0.0:
            raise ValueError("paths start at 0.0")
        if not self.recovery_known and self.recovery_days is not None:
            raise ValueError("recovery_days must be None when recovery is not known")
        total = sum(h.contribution for h in self.holdings)
        if abs(total - self.portfolio_return_21d) > CONTRIBUTION_TOLERANCE:
            raise ValueError("holding contributions must sum to portfolio_return_21d")
        return self


class ExposureRank(_Strict):
    """How much of the damage one holding drove across the replays."""

    ticker: str
    mean_contribution: float
    most_exposed_count: int = Field(ge=0)  # replays where it had the most negative contribution
    scenarios: int = Field(ge=1)

    @model_validator(mode="after")
    def _count(self) -> ExposureRank:
        if self.most_exposed_count > self.scenarios:
            raise ValueError("most_exposed_count cannot exceed scenarios")
        return self


class Resilience(_Strict):
    """How the portfolio held up across the crisis replays."""

    worse_than_sp500: int = Field(ge=0)  # crises where its 63-day worst fall was deeper than the S&P's
    crises_total: int = Field(ge=0)  # crises with an S&P comparison
    top_drivers: list[str] = Field(default_factory=list, max_length=2)

    @model_validator(mode="after")
    def _count(self) -> Resilience:
        if self.worse_than_sp500 > self.crises_total:
            raise ValueError("worse_than_sp500 cannot exceed crises_total")
        return self


class BacktestSummaryV2(_Strict):
    """Gate v2 holdout results (H1-H4); `available` is False until C5."""

    available: bool
    holdout_events: int | None = None
    h1_mae: MetricCI | None = None  # 21-day portfolio MAE, factor estimate
    h1_mae_baseline: MetricCI | None = None  # beta x S&P
    h2_rank: MetricCI | None = None
    h3_drawdown_mae: MetricCI | None = None
    h3_drawdown_mae_baseline: MetricCI | None = None
    h4_within_one_bucket: MetricCI | None = None
    h4_exact_bucket: MetricCI | None = None
    h4_exact_bucket_baseline: MetricCI | None = None
    gate_passed: bool | None = None
    recovery_shown_from: Literal["all", "actual_only"] | None = None  # "actual_only" if H4 failed
    results_url: str | None = None


class WhatIfResponseV2(_Strict):
    scenario: str
    parsed: ParsedScenario
    as_of: date
    confidence: Confidence
    scenarios: list[ScenarioReplay] = Field(default_factory=list, max_length=TOP_K)  # empty when LOW
    span_low: float | None = None  # min portfolio_return_21d over scenarios (history, not a forecast)
    span_high: float | None = None
    exposure: list[ExposureRank] = Field(default_factory=list)
    crises: list[ScenarioReplay] = Field(default_factory=list)
    resilience: Resilience | None = None
    skipped: list[SkippedTicker] = Field(default_factory=list)
    narrative: str
    backtest: BacktestSummaryV2
    remaining_today: int | None = None

    @model_validator(mode="after")
    def _consistent(self) -> WhatIfResponseV2:
        if any(s.similarity is None for s in self.scenarios):
            raise ValueError("scenario rows carry a similarity")
        if any(c.similarity is not None for c in self.crises):
            raise ValueError("crisis rows have no similarity")
        if self.scenarios:
            returns = [s.portfolio_return_21d for s in self.scenarios]
            if self.span_low != min(returns) or self.span_high != max(returns):
                raise ValueError("span must be the min and max of the scenario returns")
        elif self.span_low is not None or self.span_high is not None:
            raise ValueError("span is None when there are no scenarios")
        return self
