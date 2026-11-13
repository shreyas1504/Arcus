"""What-if engine (PLAN.md 3c).

`FakeEngine` serves the frontend fixture when SCENARIO_FAKE=1. The real engine loads
from scenario/assets plus calibration.json; until the backtest (C4) has written a
calibration, `get_engine()` raises EngineUnavailable and the router answers 503.
No number is ever invented to stand in for a missing calibration or price.

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
               - nature_penalty * [parsed.nature set and != event.nature]
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
(C3 correction: the trough is taken within the first PATH_DAYS, the same 63-day shock
window as the drawdown. Over the whole 504 days a later, unrelated crash - 2008 after
an August 2006 precedent - became "the minimum" and a 4-day recovery read as none.)

Details added in C3 (consistent with the above)
-----------------------------------------------
- The query embedding is embed(parsed.search_text), L2-normalized.
- as_of defaults to today. Prices come from one load_prices(tickers, start, as_of)
  call covering the 3-year beta window and every precedent window; rows on or after
  as_of are dropped before use.
- A holding is usable only if it has an actual or estimated 21-day return in every
  precedent the quantiles use; otherwise it is skipped with the reason.
- Before SOXX listed (July 2001) its move is NaN; a semiconductor fit then uses the
  XLK move in its place (the library flags these events "semis_proxy").
- Holding paths: actual prices when the stock has a close on every observed day of
  the window, otherwise the factor path sum(beta_f * factor_path_f).
- unrecovered_share and the recovery range use the precedent weights;
  recovery_days_low/high are the 10th and 90th weighted percentiles of the
  precedents that recovered (None when none did).
- use_actual=False uses the factor estimate even when actual prices exist (a stock
  with no fit still uses its actual prices). C4 tests both on the dev split.
- context_weight must be 0 in Phase 1: the assets hold no market-context history to
  compare a live question against. A non-zero value raises ValueError.
"""

from __future__ import annotations

import json
import math
import os
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from scenario import trading_calendar
from scenario.enums import (
    FACTOR_SEMIS,
    FACTOR_SPY,
    HORIZON_DAYS,
    PATH_DAYS,
    RECOVERY_DAYS,
    SEVERITY_QUANTILE,
    TOP_K,
    Confidence,
    ImpactSource,
    Sector,
)
from scenario.factors import BetaFit, estimate_return, fit_betas
from scenario.schemas import (
    BacktestSummary,
    BacktestSummaryV2,
    Event,
    ExposureRank,
    Resilience,
    ScenarioHolding,
    ScenarioReplay,
    WhatIfResponseV2,
    HoldingImpact,
    ParsedScenario,
    PathSeries,
    PortfolioOutcome,
    Precedent,
    SkippedTicker,
    WhatIfRequest,
    WhatIfResponse,
)

SPREAD_FLOOR = 0.005
RECOVERY_LOW_Q = 0.10
RECOVERY_HIGH_Q = 0.90
BETA_WINDOW_DAYS = 3 * 366 + 10
PROXY_FOR = {FACTOR_SEMIS: "XLK"}
ROOT = Path(__file__).resolve().parent
FIXTURE_PATH = Path(
    os.getenv(
        "SCENARIO_FIXTURE",
        str(ROOT.parent / "frontend/src/lib/__fixtures__/whatif-response.json"),
    )
)
ASSETS_DIR = Path(os.getenv("SCENARIO_ASSETS_DIR", str(ROOT / "assets")))
FIXTURE_V2_PATH = Path(
    os.getenv(
        "SCENARIO_FIXTURE_V2",
        str(ROOT.parent / "frontend/src/lib/__fixtures__/whatif-response-v2.json"),
    )
)
CRISIS_DRAWDOWN = -0.10  # PLAN v2 crisis set rule
RECOVERY_BUCKETS: tuple[str, ...] = (
    "never_fell", "1-21", "22-63", "64-126", "127-252", "253-504", "not_within_504", "unknown",
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
    nature_penalty: float = 0.0  # tuned in C4; 0 keeps the pre-approval behaviour
    use_actual: bool = True  # False: factor estimates even when actual prices exist (C4 tests both)


@dataclass(frozen=True)
class Calibration:
    """From scenario/eval/calibration.json. Defaults exist for tests only."""

    q_hat: float
    settings: EngineSettings = field(default_factory=EngineSettings)
    backtest: BacktestSummary = field(default_factory=lambda: BacktestSummary(available=False))
    backtest_v2: BacktestSummaryV2 = field(default_factory=lambda: BacktestSummaryV2(available=False))


@dataclass(frozen=True)
class ScoredPrecedent:
    index: int  # row in Library
    similarity: float  # cosine
    score: float  # cosine + bonuses


# --------------------------------------------------------------------------- calendar


@lru_cache(maxsize=1)
def _calendar() -> tuple[tuple[date, ...], dict[date, int]]:
    first, last = trading_calendar.coverage()
    days = []
    day = first
    while day <= last:
        if trading_calendar.is_trading_day(day):
            days.append(day)
        day += timedelta(days=1)
    return tuple(days), {d: i for i, d in enumerate(days)}


def _path_dates(event_date: date, horizon: int) -> list[date | None]:
    """Calendar date of each path index t = 0..horizon (None past the calendar)."""
    days, pos = _calendar()
    start = pos[event_date] - 1
    return [days[start + t] if 0 <= start + t < len(days) else None for t in range(horizon + 1)]


# --------------------------------------------------------------------------- helpers


def eligible_precedents(events: Sequence[Event], as_of: date) -> list[int]:
    """Indices of events whose full PATH_DAYS window closed before `as_of`."""
    return [
        i
        for i, event in enumerate(events)
        if event.date < as_of and trading_calendar.add_trading_days(event.date, PATH_DAYS - 1) < as_of
    ]


def score_precedents(
    query_embedding: np.ndarray,
    parsed: ParsedScenario,
    library: Library,
    as_of: date,
    settings: EngineSettings,
) -> list[ScoredPrecedent]:
    """Every eligible event, scored and sorted (see module docstring)."""
    if settings.context_weight != 0:
        raise ValueError("context_weight must be 0: the assets have no live market-context history")
    query = np.asarray(query_embedding, dtype=float).ravel()
    norm = float(np.linalg.norm(query))
    if norm > 0:
        query = query / norm
    scored = []
    for i in eligible_precedents(library.events, as_of):
        vector = np.asarray(library.embeddings[i], dtype=float)
        vnorm = float(np.linalg.norm(vector))
        cosine = float(vector @ query / vnorm) if vnorm > 0 else 0.0
        cosine = max(-1.0, min(1.0, cosine))
        match = parsed.category is not None and parsed.category == library.events[i].category
        bonus = settings.category_bonus if match else 0.0
        mismatch = parsed.nature is not None and parsed.nature != library.events[i].nature
        penalty = settings.nature_penalty if mismatch else 0.0
        scored.append(ScoredPrecedent(index=i, similarity=cosine, score=cosine + bonus - penalty))
    return sorted(scored, key=lambda s: (-s.score, library.events[s.index].id))


def weighted_quantile(values: Sequence[float], weights: Sequence[float], q: float) -> float:
    """Lower weighted quantile: sort by value, normalize weights, return the smallest
    value whose cumulative weight is >= q. Raises ValueError on empty input."""
    vals = np.asarray(values, dtype=float)
    wts = np.asarray(weights, dtype=float)
    if vals.size == 0 or vals.size != wts.size:
        raise ValueError("values and weights must be non-empty and the same length")
    if np.any(wts < 0) or not np.all(np.isfinite(wts)) or not np.all(np.isfinite(vals)):
        raise ValueError("weights must be finite and >= 0, values finite")
    total = float(wts.sum())
    if total <= 0:
        raise ValueError("weights sum to zero")
    order = np.argsort(vals, kind="stable")
    cumulative = np.cumsum(wts[order]) / total
    idx = int(np.searchsorted(cumulative, q - 1e-12, side="left"))
    return float(vals[order][min(idx, vals.size - 1)])


def recovery_days(path: Sequence[float]) -> int | None:
    """Trading days until a cumulative path regains its start after the shock.

    0 if the path never goes below 0 within the first PATH_DAYS. Otherwise the first
    t after its minimum over t <= PATH_DAYS with path[t] >= 0. None if that never
    happens within the observed (non-NaN) part of the path.
    """
    observed: list[float] = []
    for value in path:
        if value is None or not math.isfinite(float(value)):
            break
        observed.append(float(value))
    window = observed[: PATH_DAYS + 1]
    if len(window) <= 1 or min(window[1:]) >= 0:
        return 0
    trough = int(np.argmin(window))
    for t in range(trough + 1, len(observed)):
        if observed[t] >= 0:
            return t
    return None


def _drawdown(path: Sequence[float | None]) -> float:
    wealth = 1.0 + np.asarray([v for v in path if v is not None and math.isfinite(v)], dtype=float)
    if wealth.size == 0:
        return 0.0
    peaks = np.maximum.accumulate(wealth)
    return float(min(0.0, np.min(wealth / peaks - 1.0)))



# --------------------------------------------------------------------------- v2 (stress test) contract
# PLAN.md section "v2". Stubs written in C4b-contract; implemented in C4b-engine. Cursor's
# blind tests (test_scenario_engine_v2.py) are written against these docstrings.


def crisis_events(library: Library, as_of: date) -> list[int]:
    """Library rows that form the crisis replay set as of `as_of`, sorted by date.

    An event qualifies if (1) it is eligible (eligible_precedents: its 63-day window closed
    before as_of) and (2) the S&P's worst fall within its window is CRISIS_DRAWDOWN or worse,
    where worst fall = min over t <= PATH_DAYS of (1 + p_t) / max_{s<=t}(1 + p_s) - 1 on the
    library's cumulative FACTOR_SPY path. Only the earliest qualifying event per cluster_id is
    kept; an event without a cluster_id is its own cluster. Ties on date go by event id.
    """
    spy = library.factor_names.index(FACTOR_SPY)
    qualifying = []
    for i in eligible_precedents(library.events, as_of):
        path = [float(v) for v in library.factor_paths[i, : PATH_DAYS + 1, spy]]
        if _drawdown(path) <= CRISIS_DRAWDOWN:
            qualifying.append(i)
    seen: set[str] = set()
    out = []
    for i in sorted(qualifying, key=lambda k: (library.events[k].date, library.events[k].id)):
        event = library.events[i]
        cluster = event.cluster_id or f"event:{event.id}"
        if cluster not in seen:
            seen.add(cluster)
            out.append(i)
    return out


def recovery_bucket(days: int | None, known: bool) -> str:
    """The H4 bucket (one of RECOVERY_BUCKETS) for a recovery time in trading days.

    days == 0 -> "never_fell"; 1-21 -> "1-21"; 22-63 -> "22-63"; 64-126 -> "64-126";
    127-252 -> "127-252"; 253-504 -> "253-504"; days is None and known -> "not_within_504";
    days is None and not known -> "unknown". Raises ValueError for negative days, for days
    above RECOVERY_DAYS, or for days given with known=False.
    """
    if days is None:
        return "not_within_504" if known else "unknown"
    if not known:
        raise ValueError("days given with known=False")
    if days < 0 or days > RECOVERY_DAYS:
        raise ValueError(f"recovery days must be 0..{RECOVERY_DAYS}")
    if days == 0:
        return "never_fell"
    for upper, label in ((21, "1-21"), (63, "22-63"), (126, "64-126"), (252, "127-252")):
        if days <= upper:
            return label
    return "253-504"


def exposure_ranking(replays: Sequence[ScenarioReplay]) -> list[ExposureRank]:
    """Which holdings drove the damage across `replays`.

    For each ticker held in the replays: mean_contribution = mean of its contribution over
    the replays that hold it; scenarios = that number of replays; most_exposed_count = the
    number of replays in which it had the lowest contribution AND that contribution was
    below 0 (ties: the alphabetically first ticker). Sorted by mean_contribution ascending
    (most damage first), then ticker. Empty input -> [].
    """
    contributions: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for replay in replays:
        rows = sorted(replay.holdings, key=lambda h: (h.contribution, h.ticker))
        if rows and rows[0].contribution < 0:
            counts[rows[0].ticker] = counts.get(rows[0].ticker, 0) + 1
        for holding in replay.holdings:
            contributions.setdefault(holding.ticker, []).append(holding.contribution)
    ranks = [
        ExposureRank(
            ticker=ticker,
            mean_contribution=float(sum(values) / len(values)),
            most_exposed_count=counts.get(ticker, 0),
            scenarios=len(values),
        )
        for ticker, values in contributions.items()
    ]
    return sorted(ranks, key=lambda r: (r.mean_contribution, r.ticker))


def resilience_summary(crises: Sequence[ScenarioReplay]) -> Resilience:
    """How the portfolio held up across the crisis replays.

    crises_total = crises with a sp500_worst_drawdown_63d; worse_than_sp500 = those where
    worst_drawdown_63d < sp500_worst_drawdown_63d (a deeper fall); top_drivers = up to 2
    tickers from exposure_ranking(crises) with most_exposed_count > 0, ordered by
    most_exposed_count descending, then mean_contribution ascending, then ticker.
    """
    compared = [c for c in crises if c.sp500_worst_drawdown_63d is not None]
    worse = sum(1 for c in compared if c.worst_drawdown_63d < c.sp500_worst_drawdown_63d)
    drivers = sorted(
        (r for r in exposure_ranking(crises) if r.most_exposed_count > 0),
        key=lambda r: (-r.most_exposed_count, r.mean_contribution, r.ticker),
    )
    return Resilience(worse_than_sp500=worse, crises_total=len(compared), top_drivers=[r.ticker for r in drivers[:2]])


def _render_v2_or_empty(render, response: WhatIfResponseV2) -> str:
    """render_v2 is Cursor's (U4b). Until it lands, the stub raises; the page then shows
    the structured replays without a narrative rather than an invented sentence."""
    try:
        return render(response)
    except NotImplementedError:
        return ""


# --------------------------------------------------------------------------- engine


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
        if calibration.q_hat < 0:
            raise ValueError("q_hat must be >= 0")
        self.library = library
        self.calibration = calibration
        self._embed = embed
        self._parse = parse
        self._load_prices = load_prices
        self._sectors = sectors
        self._factor_index = {name: i for i, name in enumerate(library.factor_names)}

    # ----------------------------------------------------------------- per-event pieces

    def _factor_value(self, event_index: int, t: int, name: str) -> float:
        paths = self.library.factor_paths
        value = float(paths[event_index, t, self._factor_index[name]])
        if not math.isfinite(value) and name in PROXY_FOR:
            value = float(paths[event_index, t, self._factor_index[PROXY_FOR[name]]])
        return value

    def _factor_estimate(self, fit: BetaFit, event_index: int, t: int) -> float:
        moves = {name: self._factor_value(event_index, t, name) for name in fit.betas}
        return estimate_return(fit, moves)

    @staticmethod
    def _close(series: pd.Series | None, day: date | None) -> float:
        if series is None or day is None:
            return math.nan
        value = series.get(pd.Timestamp(day), math.nan)
        try:
            return float(value)
        except (TypeError, ValueError):
            return math.nan

    def _holding_21d(
        self, series: pd.Series | None, fit: BetaFit | None, event_index: int
    ) -> tuple[float, ImpactSource] | None:
        dates = _path_dates(self.library.events[event_index].date, HORIZON_DAYS)
        start, end = self._close(series, dates[0]), self._close(series, dates[HORIZON_DAYS])
        prefer_actual = self.calibration.settings.use_actual or fit is None
        if prefer_actual and math.isfinite(start) and math.isfinite(end) and start > 0:
            return end / start - 1.0, ImpactSource.ACTUAL
        if fit is not None:
            value = self._factor_estimate(fit, event_index, HORIZON_DAYS)
            if math.isfinite(value):
                low = "low_history" in fit.flags
                return value, ImpactSource.ESTIMATED_LOW_HISTORY if low else ImpactSource.ESTIMATED
        return None

    def _holding_path(
        self,
        ticker: str,
        event_index: int,
        horizon: int,
        prices: pd.DataFrame,
        fits: Mapping[str, BetaFit],
        as_of: date,
    ) -> tuple[np.ndarray, str]:
        """One holding's cumulative path t = 0..horizon and where it came from:
        "actual" (closes on every observed day), "estimated" (factor path), "partial"
        (closes with gaps, no fit) or "none"."""
        dates = _path_dates(self.library.events[event_index].date, horizon)
        observed = [d is not None and d < as_of for d in dates]
        n_obs = sum(observed)
        series = prices[ticker] if ticker in prices.columns else None
        closes = np.array([self._close(series, d) if ok else math.nan for d, ok in zip(dates, observed)])
        use_actual = self.calibration.settings.use_actual or ticker not in fits
        if use_actual and n_obs and np.all(np.isfinite(closes[:n_obs])) and closes[0] > 0:
            return closes / closes[0] - 1.0, "actual"
        if ticker in fits:
            return np.array([self._factor_estimate(fits[ticker], event_index, t) for t in range(horizon + 1)]), "estimated"
        if math.isfinite(closes[0]) and closes[0] > 0:
            return closes / closes[0] - 1.0, "partial"
        return np.full(horizon + 1, math.nan), "none"

    def _mask(self, event_index: int, horizon: int, values: np.ndarray, as_of: date) -> list[float | None]:
        dates = _path_dates(self.library.events[event_index].date, horizon)
        out: list[float | None] = [
            float(values[t]) if d is not None and d < as_of and math.isfinite(float(values[t])) else None
            for t, d in enumerate(dates)
        ]
        out[0] = 0.0
        return out

    def _portfolio_path(
        self,
        event_index: int,
        horizon: int,
        weights: Mapping[str, float],
        prices: pd.DataFrame,
        fits: Mapping[str, BetaFit],
        as_of: date,
    ) -> list[float | None]:
        total = np.zeros(horizon + 1)
        for ticker, weight in weights.items():
            path, _ = self._holding_path(ticker, event_index, horizon, prices, fits, as_of)
            total = total + weight * path
        return self._mask(event_index, horizon, total, as_of)

    def run_v2(
        self,
        request: WhatIfRequest,
        *,
        as_of: date | None = None,
        parsed: ParsedScenario | None = None,
    ) -> WhatIfResponseV2:
        """Stress-test answer (PLAN v2): replays of the closest past shocks and the crises.

        - as_of defaults to today; `parsed` skips the model call; precedent search, scoring,
          threshold and top_k are exactly as in run() (score_precedents + selection).
        - confidence LOW (no cosine >= similarity_threshold): `scenarios` is empty, the span
          is None, and only the crisis replay is returned.
        - Each replay (scenarios and crises alike), per holding: the actual 21-day return
          when settings.use_actual and the stock has closes at t = 0 and t = HORIZON_DAYS,
          else the factor estimate (as in run()); contribution = weight x return_21d;
          portfolio_return_21d = the sum of contributions. path = the portfolio path for
          t = 0..PATH_DAYS. worst_drawdown_63d from that path (as in run()).
          sp500_return_21d and sp500_worst_drawdown_63d come from the library SPY path.
        - Recovery: recovery_days(long path, t = 0..RECOVERY_DAYS) as in run();
          recovery_known = recovered, or the path is observed for all RECOVERY_DAYS days.
          recovery_source = "actual" if every holding used actual prices for the long path,
          "estimated" if none did, else "mixed". Per holding, recovery_days uses that
          holding's own path. If calibration backtest.recovery_shown_from == "actual_only"
          (the pre-registered H4 fallback), recovery fields that do not come only from
          actual prices are None and recovery_known is False.
        - crises = crisis_events(library, as_of) replayed (similarity None); exposure =
          exposure_ranking(scenarios); resilience = resilience_summary(crises) (None if no
          crises); span_low/high = min/max of scenario portfolio_return_21d.
        - Holdings with no actual price and no factor fit for every replayed event are
          listed in `skipped` and the rest are renormalized (as in run()).
        - narrative = narrative.render_v2(response).
        """
        from scenario.narrative import render_v2

        as_of = as_of or date.today()
        settings = self.calibration.settings
        parsed = parsed if parsed is not None else self._parse(request.scenario)
        query = np.asarray(self._embed(parsed.search_text), dtype=float)
        scored = score_precedents(query, parsed, self.library, as_of, settings)
        selected = [s for s in scored if s.similarity >= settings.similarity_threshold][: settings.top_k]
        confidence = Confidence.NORMAL if selected else Confidence.LOW
        crisis_rows = crisis_events(self.library, as_of)
        needed = sorted({s.index for s in selected} | set(crisis_rows))

        base = {
            "scenario": request.scenario,
            "parsed": parsed,
            "as_of": as_of,
            "confidence": confidence,
            "backtest": self.calibration.backtest_v2,
            "narrative": "",
        }
        tickers = [h.ticker for h in request.holdings]
        if not needed:
            response = WhatIfResponseV2(**base)
            return response.model_copy(update={"narrative": _render_v2_or_empty(render_v2, response)})

        sector_map = {t: s for t, s in dict(self._sectors(tickers)).items() if t in tickers}
        earliest = min(_path_dates(self.library.events[i].date, 0)[0] for i in needed)
        start = min(earliest, as_of - timedelta(days=BETA_WINDOW_DAYS))
        prices = self._clean_prices(self._load_prices(tickers, start, as_of), tickers, as_of)
        fits: dict[str, BetaFit] = {}
        if not prices.empty:
            fits = fit_betas(
                prices.pct_change(fill_method=None), self.library.factor_history, as_of,
                sectors=sector_map, alpha=settings.alpha, stress_only=settings.stress_only,
            )

        values: dict[str, dict[int, tuple[float, ImpactSource]]] = {}
        skipped: list[SkippedTicker] = []
        for ticker in tickers:
            series = prices[ticker] if ticker in prices.columns else None
            row = {}
            for i in needed:
                value = self._holding_21d(series, fits.get(ticker), i)
                if value is None:
                    break
                row[i] = value
            if len(row) == len(needed):
                values[ticker] = row
            elif series is None:
                skipped.append(SkippedTicker(ticker=ticker, reason="no price data"))
            else:
                skipped.append(SkippedTicker(ticker=ticker, reason="not enough price history to estimate"))
        if not values:
            response = WhatIfResponseV2(**base, skipped=skipped)
            return response.model_copy(update={"narrative": _render_v2_or_empty(render_v2, response)})

        raw = {h.ticker: h.weight for h in request.holdings if h.ticker in values}
        weights = {t: w / sum(raw.values()) for t, w in raw.items()}
        actual_only = self.calibration.backtest_v2.recovery_shown_from == "actual_only"

        def replay(i: int, similarity: float | None) -> ScenarioReplay:
            event = self.library.events[i]
            holdings = []
            total_path = np.zeros(RECOVERY_DAYS + 1)
            kinds = []
            for ticker, weight in weights.items():
                ret, source = values[ticker][i]
                path, kind = self._holding_path(ticker, i, RECOVERY_DAYS, prices, fits, as_of)
                kinds.append(kind)
                total_path = total_path + weight * path
                own = recovery_days(self._mask(i, RECOVERY_DAYS, path, as_of))
                price_based = kind in ("actual", "partial")
                holdings.append(
                    ScenarioHolding(
                        ticker=ticker, weight=weight, sector=sector_map.get(ticker, Sector.BROAD),
                        return_21d=ret, contribution=weight * ret, source=source,
                        recovery_days=None if (actual_only and not price_based) else own,
                    )
                )
            long_path = self._mask(i, RECOVERY_DAYS, total_path, as_of)
            days = recovery_days(long_path)
            known = days is not None or all(v is not None for v in long_path)
            if all(k in ("actual", "partial") for k in kinds):
                recovery_source = "actual"
            elif all(k == "estimated" for k in kinds):
                recovery_source = "estimated"
            else:
                recovery_source = "mixed"
            if actual_only and recovery_source != "actual":
                days, known = None, False
            spy_path = [float(v) for v in self.library.factor_paths[i, : PATH_DAYS + 1, self._factor_index[FACTOR_SPY]]]
            spy_21 = spy_path[HORIZON_DAYS] if len(spy_path) > HORIZON_DAYS else math.nan
            spy_finite = all(math.isfinite(v) for v in spy_path)
            return ScenarioReplay(
                event_id=event.id, name=event.name, date=event.date, category=event.category,
                nature=event.nature, trigger=event.trigger, similarity=similarity, source_url=event.source_url,
                portfolio_return_21d=float(sum(h.contribution for h in holdings)),
                sp500_return_21d=spy_21 if math.isfinite(spy_21) else None,
                worst_drawdown_63d=_drawdown(long_path[: PATH_DAYS + 1]),
                sp500_worst_drawdown_63d=_drawdown(spy_path) if spy_finite else None,
                recovery_days=days, recovery_known=known, recovery_source=recovery_source,
                path=long_path[: PATH_DAYS + 1], holdings=holdings,
            )

        scenarios = [replay(s.index, s.similarity) for s in selected]
        crises = [replay(i, None) for i in crisis_rows]
        returns = [r.portfolio_return_21d for r in scenarios]
        response = WhatIfResponseV2(
            **base,
            scenarios=scenarios,
            span_low=min(returns) if returns else None,
            span_high=max(returns) if returns else None,
            exposure=exposure_ranking(scenarios),
            crises=crises,
            resilience=resilience_summary(crises) if crises else None,
            skipped=skipped,
        )
        return response.model_copy(update={"narrative": _render_v2_or_empty(render_v2, response)})

    @staticmethod
    def _clean_prices(prices: pd.DataFrame | None, tickers: list[str], as_of: date) -> pd.DataFrame:
        if prices is None or prices.empty:
            return pd.DataFrame()
        frame = prices.copy()
        index = pd.DatetimeIndex(frame.index)
        if index.tz is not None:
            index = index.tz_localize(None)
        frame.index = index.normalize()
        frame = frame[frame.index < pd.Timestamp(as_of)]
        keep = [t for t in tickers if t in frame.columns]
        return frame[keep].sort_index()

    # ----------------------------------------------------------------- run

    def run(
        self,
        request: WhatIfRequest,
        *,
        as_of: date | None = None,
        parsed: ParsedScenario | None = None,
    ) -> WhatIfResponse:
        """Answer one request as of `as_of` (default: today). `parsed` skips the model call."""
        from scenario.narrative import render

        as_of = as_of or date.today()
        settings = self.calibration.settings
        parsed = parsed if parsed is not None else self._parse(request.scenario)
        query = np.asarray(self._embed(parsed.search_text), dtype=float)
        scored = score_precedents(query, parsed, self.library, as_of, settings)
        events = self.library.events

        selected = [s for s in scored if s.similarity >= settings.similarity_threshold][: settings.top_k]
        if selected:
            confidence = Confidence.NORMAL
            qset, shown = selected, selected
            raw = np.array([max(s.score, 0.0) for s in qset])
            qweights = raw / raw.sum() if raw.sum() > 0 else np.full(len(qset), 1.0 / len(qset))
            shown_weights = [float(w) for w in qweights]
        else:
            confidence = Confidence.LOW
            qset, shown = scored, scored[: settings.top_k]
            qweights = np.full(len(qset), 1.0 / len(qset)) if qset else np.array([])
            shown_weights = [1.0 / len(qset)] * len(shown) if qset else []

        base = {
            "scenario": request.scenario,
            "parsed": parsed,
            "as_of": as_of,
            "severity": request.severity,
            "confidence": confidence,
            "backtest": self.calibration.backtest,
            "narrative": "",
        }
        if not qset:
            response = WhatIfResponse(**base, precedents=[], portfolio=None, holdings=[], paths=[])
            return response.model_copy(update={"narrative": render(response)})

        tickers = [h.ticker for h in request.holdings]
        sector_map = {t: s for t, s in dict(self._sectors(tickers)).items() if t in tickers}
        needed = sorted({s.index for s in qset} | {s.index for s in shown})
        earliest = min(_path_dates(events[i].date, 0)[0] for i in needed)
        start = min(earliest, as_of - timedelta(days=BETA_WINDOW_DAYS))
        prices = self._clean_prices(self._load_prices(tickers, start, as_of), tickers, as_of)
        fits: dict[str, BetaFit] = {}
        if not prices.empty:
            fits = fit_betas(
                prices.pct_change(fill_method=None),
                self.library.factor_history,
                as_of,
                sectors=sector_map,
                alpha=settings.alpha,
                stress_only=settings.stress_only,
            )

        per_holding: dict[str, dict[int, tuple[float, ImpactSource]]] = {}
        skipped: list[SkippedTicker] = []
        for ticker in tickers:
            series = prices[ticker] if ticker in prices.columns else None
            values = {}
            for i in needed:
                value = self._holding_21d(series, fits.get(ticker), i)
                if value is None:
                    break
                values[i] = value
            if len(values) == len(needed):
                per_holding[ticker] = values
            elif series is None:
                skipped.append(SkippedTicker(ticker=ticker, reason="no price data"))
            else:
                skipped.append(SkippedTicker(ticker=ticker, reason="not enough price history to estimate"))

        precedent_returns: dict[int, float] = {}
        holdings: list[HoldingImpact] = []
        portfolio = None
        paths: list[PathSeries] = []
        if per_holding:
            raw_weights = {h.ticker: h.weight for h in request.holdings if h.ticker in per_holding}
            total_weight = sum(raw_weights.values())
            weights = {t: w / total_weight for t, w in raw_weights.items()}
            for i in needed:
                precedent_returns[i] = float(sum(weights[t] * per_holding[t][i][0] for t in weights))

            qidx = [s.index for s in qset]
            returns = [precedent_returns[i] for i in qidx]
            median = weighted_quantile(returns, qweights, 0.5)
            typical = weighted_quantile(returns, qweights, SEVERITY_QUANTILE[request.severity])
            spread = max(weighted_quantile([abs(r - median) for r in returns], qweights, 0.5), SPREAD_FLOOR)
            half = self.calibration.q_hat * spread

            for ticker, weight in weights.items():
                ret = float(sum(w * per_holding[ticker][i][0] for w, i in zip(qweights, qidx)))
                actual_share = float(
                    sum(w for w, i in zip(qweights, qidx) if per_holding[ticker][i][1] is ImpactSource.ACTUAL)
                )
                if actual_share >= 0.5:
                    source = ImpactSource.ACTUAL
                elif ticker in fits and "low_history" in fits[ticker].flags:
                    source = ImpactSource.ESTIMATED_LOW_HISTORY
                else:
                    source = ImpactSource.ESTIMATED
                holdings.append(
                    HoldingImpact(
                        ticker=ticker,
                        weight=weight,
                        sector=sector_map.get(ticker, Sector.BROAD),
                        return_21d=ret,
                        contribution=weight * ret,
                        source=source,
                        actual_share=min(1.0, actual_share),
                    )
                )

            short = {i: self._portfolio_path(i, PATH_DAYS, weights, prices, fits, as_of) for i in qidx}
            long = {i: self._portfolio_path(i, RECOVERY_DAYS, weights, prices, fits, as_of) for i in qidx}
            drawdowns = [_drawdown(short[i]) for i in qidx]
            worst = weighted_quantile(drawdowns, qweights, SEVERITY_QUANTILE[request.severity])

            recovered: list[int] = []
            recovered_w: list[float] = []
            known_w = unrecovered_w = 0.0
            for w, i in zip(qweights, qidx):
                days = recovery_days(long[i])
                if days is not None:
                    recovered.append(days)
                    recovered_w.append(float(w))
                    known_w += float(w)
                elif all(v is not None for v in long[i]):
                    known_w += float(w)
                    unrecovered_w += float(w)
            portfolio = PortfolioOutcome(
                severity=request.severity,
                typical_return=typical,
                median_return=median,
                mean_return=float(sum(h.contribution for h in holdings)),
                range_low=median - half,
                range_high=median + half,
                worst_drawdown_63d=min(0.0, worst),
                recovery_days_low=int(weighted_quantile(recovered, recovered_w, RECOVERY_LOW_Q)) if recovered else None,
                recovery_days_high=int(weighted_quantile(recovered, recovered_w, RECOVERY_HIGH_Q)) if recovered else None,
                unrecovered_share=unrecovered_w / known_w if known_w > 0 else 0.0,
            )
            for s in shown:
                values = short.get(s.index) or self._portfolio_path(s.index, PATH_DAYS, weights, prices, fits, as_of)
                event = events[s.index]
                paths.append(
                    PathSeries(event_id=event.id, label=f"{event.name} ({event.date.isoformat()})", values=values)
                )

        precedents = []
        for s, weight in zip(shown, shown_weights):
            event = events[s.index]
            spy = float(self.library.factor_paths[s.index, HORIZON_DAYS, self._factor_index[FACTOR_SPY]])
            precedents.append(
                Precedent(
                    event_id=event.id,
                    name=event.name,
                    date=event.date,
                    category=event.category,
                    nature=event.nature,
                    trigger=event.trigger,
                    similarity=s.similarity,
                    weight=min(1.0, max(0.0, float(weight))),
                    sp500_return_21d=spy if math.isfinite(spy) else None,
                    portfolio_return_21d=precedent_returns.get(s.index),
                    source_url=event.source_url,
                )
            )

        response = WhatIfResponse(
            **base, precedents=precedents, portfolio=portfolio, holdings=holdings, skipped=skipped, paths=paths
        )
        return response.model_copy(update={"narrative": render(response)})


# --------------------------------------------------------------------------- production wiring


def load_calibration(path: Path) -> Calibration:
    data = json.loads(path.read_text())
    settings = EngineSettings(**data["settings"])
    if settings.context_weight != 0:
        raise ValueError("calibration sets context_weight, which Phase 1 assets cannot support")
    return Calibration(
        q_hat=float(data["q_hat"]),
        settings=settings,
        backtest=BacktestSummary.model_validate(data.get("backtest", {"available": False})),
        backtest_v2=BacktestSummaryV2.model_validate(data.get("backtest_v2", {"available": False})),
    )


def _calibration_path(assets_dir: Path) -> Path:
    explicit = os.getenv("SCENARIO_CALIBRATION")
    if explicit:
        return Path(explicit)
    shipped = assets_dir / "calibration.json"
    return shipped if shipped.exists() else ROOT / "eval" / "calibration.json"


_price_cache: dict[tuple, pd.Series] = {}
_sector_cache: dict[str, Sector] = {}


def yahoo_adjusted_closes(tickers: list[str], start: date, end: date) -> pd.DataFrame:
    """Adjusted closes per ticker, downloaded one ticker at a time and never filled.

    (backend.data.fetcher.download_prices drops every date on which any ticker is
    missing, which would erase history before the youngest holding listed.)
    """
    import yfinance as yf

    columns = {}
    for ticker in tickers:
        key = (ticker, start, end)
        if key not in _price_cache:
            bars = yf.download(
                ticker,
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=False,
            )
            if bars is None or bars.empty:
                continue
            if isinstance(bars.columns, pd.MultiIndex):
                bars = bars.xs(ticker, axis=1, level=-1)
            series = bars["Adj Close"].dropna()
            series.index = pd.DatetimeIndex(series.index).tz_localize(None).normalize()
            _price_cache[key] = series
        columns[ticker] = _price_cache[key]
    return pd.DataFrame(columns)


def yahoo_sectors(tickers: list[str]) -> dict[str, Sector]:
    """Sector per ticker from yfinance sector and industry; unknown tickers are omitted."""
    import yfinance as yf

    from scenario.enums import sector_from_yfinance

    out = {}
    for ticker in tickers:
        if ticker not in _sector_cache:
            try:
                info = yf.Ticker(ticker).info or {}
            except Exception:  # noqa: BLE001 - unknown sector -> factors flag "sector_unknown"
                continue
            if not info.get("sector"):
                continue
            _sector_cache[ticker] = sector_from_yfinance(info.get("sector"), info.get("industry"))
        out[ticker] = _sector_cache[ticker]
    return out


def build_default_engine(assets_dir: Path = ASSETS_DIR) -> WhatIfEngine:
    from research.embedder import shared_embedder
    from scenario.build_library import load_library
    from scenario.parse import parse_scenario

    if not (assets_dir / "library.npz").exists():
        raise EngineUnavailable(f"Scenario Lab assets are not loaded ({assets_dir})")
    calibration_path = _calibration_path(assets_dir)
    if not calibration_path.exists():
        raise EngineUnavailable("Scenario Lab has no calibration yet (the backtest has not run)")
    return WhatIfEngine(
        load_library(assets_dir),
        load_calibration(calibration_path),
        embed=lambda text: shared_embedder().encode([text])[0],
        parse=parse_scenario,
        load_prices=yahoo_adjusted_closes,
        sectors=yahoo_sectors,
    )


class FakeEngine:
    """Serves the frontend fixture so the router and page can be built before C3."""

    def __init__(self, fixture_path: Path = FIXTURE_PATH) -> None:
        self._fixture = WhatIfResponse.model_validate(json.loads(fixture_path.read_text()))

    def run(self, request: WhatIfRequest, **_: object) -> WhatIfResponse:
        return self._fixture.model_copy(
            update={"scenario": request.scenario, "severity": request.severity}, deep=True
        )

    def run_v2(self, request: WhatIfRequest, **_: object) -> WhatIfResponseV2:
        fixture = WhatIfResponseV2.model_validate(json.loads(FIXTURE_V2_PATH.read_text()))
        return fixture.model_copy(update={"scenario": request.scenario}, deep=True)


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
        try:
            _engine = build_default_engine()
        except EngineUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced as 503, never as fake numbers
            raise EngineUnavailable(f"Scenario Lab failed to load: {type(exc).__name__}") from exc
        return _engine


def reset_engine() -> None:
    """Tests only."""
    global _engine
    with _engine_lock:
        _engine = None
