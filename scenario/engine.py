"""What-if engine (PLAN.md 3c). Contract stub: WhatIfEngine is implemented in C3.

`FakeEngine`, `get_engine()` and `EngineUnavailable` are live now so the router and
page can be built against the fixture (SCENARIO_FAKE=1).

Definitions (blind tests are written against these)
---------------------------------------------------
Path index: t = 0 is the close on day -1 (value 0.0); t = k is the close of the k-th
trading day starting with day 0. 21-day return = path[HORIZON_DAYS].

Eligible precedents for `as_of`: events with
    add_trading_days(event.date, PATH_DAYS - 1) < as_of
i.e. the whole 63-day window closed before as_of. This both forbids future events
and purges events whose window overlaps as_of. Paths are masked (NaN) from as_of on.

Scoring: score = cosine(query, event embedding)
               + category_bonus * [parsed.category == event.category]
               + context_weight * context_similarity (0 unless enabled by calibration)
Sorted by score descending, ties by event id ascending. Selection keeps up to top_k
events whose cosine >= similarity_threshold.

Confidence: LOW when no eligible event has cosine >= similarity_threshold. Then the
quantiles use every eligible event with equal weights, and `precedents` shows the
top_k by score for reference.

Weights: w_i = max(score_i, 0) / sum over selected; all zero -> equal weights.

Quantiles: weighted_quantile (lower weighted quantile, see the function).
    median_return  = weighted_quantile(r, w, 0.5)
    typical_return = weighted_quantile(r, w, SEVERITY_QUANTILE[severity])
    mean_return    = sum(w_i * r_i)
Range: spread = max(weighted_quantile(|r - median|, w, 0.5), SPREAD_FLOOR)
       range = median -/+ calibration.q_hat * spread

Per holding and precedent: ACTUAL when the stock has a close at both t = 0 and
t = HORIZON_DAYS; otherwise factors.estimate_return(fit, library 21-day factor moves).
ESTIMATED_LOW_HISTORY when the fit has the "low_history" flag. A ticker with no fit
and no actual prices is listed in `skipped` and the rest are renormalized.
HoldingImpact.return_21d = sum(w_i * r_hi); contribution = weight * return_21d.

Drawdown: per precedent, min over t <= PATH_DAYS of (1 + p_t) / max_{s<=t}(1 + p_s) - 1;
worst_drawdown_63d = weighted_quantile of those at the severity quantile.
Recovery: see recovery_days(). unrecovered_share is over precedents whose path is
either recovered or observed for all RECOVERY_DAYS days.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from scenario.enums import TOP_K, Sector
from scenario.schemas import (
    BacktestSummary,
    Event,
    ParsedScenario,
    WhatIfRequest,
    WhatIfResponse,
)

SPREAD_FLOOR = 0.005
FIXTURE_PATH = Path(
    os.getenv(
        "SCENARIO_FIXTURE",
        str(Path(__file__).resolve().parent.parent / "frontend/src/lib/__fixtures__/whatif-response.json"),
    )
)


class EngineUnavailable(RuntimeError):
    """Assets are not loaded; the router answers 503."""


@dataclass(frozen=True)
class Library:
    """In-memory form of scenario/assets (layout in scenario/ASSETS.md). Row i = events[i]."""

    events: list[Event]
    embeddings: np.ndarray  # (n, 384) float32, L2-normalized
    factor_names: tuple[str, ...]  # FACTOR_NAMES
    factor_paths: np.ndarray  # (n, RECOVERY_DAYS + 1, F) float32 cumulative, NaN-masked
    context: pd.DataFrame  # index event id; columns vix, baa10y, gpr, gpr_rise_5d (day -1)
    factor_history: pd.DataFrame  # DatetimeIndex, FACTOR_NAMES columns, daily returns


@dataclass(frozen=True)
class EngineSettings:
    alpha: float = 1.0
    stress_only: bool = False
    category_bonus: float = 0.05
    context_weight: float = 0.0
    similarity_threshold: float = 0.5
    top_k: int = TOP_K


@dataclass(frozen=True)
class Calibration:
    """From scenario/eval/calibration.json. Defaults exist for tests only."""

    q_hat: float
    settings: EngineSettings = field(default_factory=EngineSettings)
    backtest: BacktestSummary = field(default_factory=lambda: BacktestSummary(available=False))


@dataclass(frozen=True)
class ScoredPrecedent:
    index: int  # row in Library
    similarity: float  # cosine
    score: float  # cosine + bonuses


def eligible_precedents(events: Sequence[Event], as_of: date) -> list[int]:
    """Indices of events whose full PATH_DAYS window closed before `as_of`."""
    raise NotImplementedError


def score_precedents(
    query_embedding: np.ndarray,
    parsed: ParsedScenario,
    library: Library,
    as_of: date,
    settings: EngineSettings,
) -> list[ScoredPrecedent]:
    """Every eligible event, scored and sorted (see module docstring)."""
    raise NotImplementedError


def weighted_quantile(values: Sequence[float], weights: Sequence[float], q: float) -> float:
    """Lower weighted quantile: sort by value, normalize weights, return the smallest
    value whose cumulative weight is >= q. Raises ValueError on empty input."""
    raise NotImplementedError


def recovery_days(path: Sequence[float]) -> int | None:
    """Trading days until a cumulative path regains its start.

    0 if the path never goes below 0 after t = 0. Otherwise the first t after the
    path's minimum with path[t] >= 0. None if that never happens within the
    observed (non-NaN) part of the path.
    """
    raise NotImplementedError


class WhatIfEngine:
    def __init__(
        self,
        library: Library,
        calibration: Calibration,
        *,
        embed: Callable[[str], np.ndarray],
        parse: Callable[[str], ParsedScenario],
        load_prices: Callable[[list[str], date, date], pd.DataFrame],
        sectors: Callable[[list[str]], Mapping[str, Sector]],
    ) -> None:
        """Dependencies are injected so tests can use fakes.

        load_prices(tickers, start, end) returns adjusted closes (DatetimeIndex,
        one column per ticker that has data). It may omit tickers; it must not
        fill gaps.
        """
        raise NotImplementedError

    def run(
        self,
        request: WhatIfRequest,
        *,
        as_of: date | None = None,
        parsed: ParsedScenario | None = None,
    ) -> WhatIfResponse:
        """Answer one request as of `as_of` (default: today). `parsed` skips the model call."""
        raise NotImplementedError


class FakeEngine:
    """Serves the frontend fixture so the router and page can be built before C3."""

    def __init__(self, fixture_path: Path = FIXTURE_PATH) -> None:
        self._fixture = WhatIfResponse.model_validate(json.loads(fixture_path.read_text()))

    def run(self, request: WhatIfRequest, **_: object) -> WhatIfResponse:
        return self._fixture.model_copy(
            update={"scenario": request.scenario, "severity": request.severity}, deep=True
        )


_engine: FakeEngine | WhatIfEngine | None = None
_engine_lock = threading.Lock()


def _fake_enabled() -> bool:
    return os.getenv("SCENARIO_FAKE", "").lower() in {"1", "true", "yes", "on"}


def get_engine() -> FakeEngine | WhatIfEngine:
    """FastAPI dependency. Raises EngineUnavailable when the real engine can't load."""
    global _engine
    with _engine_lock:
        if _fake_enabled():
            if not isinstance(_engine, FakeEngine):
                _engine = FakeEngine()
            return _engine
        if isinstance(_engine, WhatIfEngine):
            return _engine
        _engine = None
    raise EngineUnavailable("Scenario Lab assets are not loaded")


def reset_engine() -> None:
    """Tests only."""
    global _engine
    with _engine_lock:
        _engine = None
