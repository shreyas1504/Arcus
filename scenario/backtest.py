"""Scenario Lab backtest, tuning and calibration (PLAN.md Step 4 and section 2b).

    python -m scenario.backtest download-universe   # stock prices + sectors, SHA256 manifest
    python -m scenario.backtest dev                 # v1 forecast (kept as evidence): results_forecast_v1.md
    python -m scenario.backtest dev-v2              # v2 stress test: H1-H4 on dev, threshold, crises
    python -m scenario.backtest diagnostics         # forecast vs conditional accuracy on dev
    python -m scenario.backtest holdout             # C5 only: refuses unless SCENARIO_RUN_HOLDOUT=1

How a test event is scored (no hindsight)
- The question is the event's own day-0 `trigger`, embedded like a user question.
- Parsing is assumed correct: the event's own category and nature are used ("oracle
  parse"). results.md also reports the no-parse fallback as a lower bound.
- Precedents are only events whose 63-day window closed before the event
  (engine.eligible_precedents), and betas are fitted on prices before it.
- Portfolios: N_RANDOM random equal-weight portfolios of 5-15 stocks that had prices
  on day -1 and day +21 and at least MIN_HISTORY days of history, plus 6 archetypes.
- The outcome is the portfolio's realized 21-day return from the day -1 close.

The engine's maths is re-implemented here in vectorized form (portfolio returns are
linear in holdings), and test_scenario_backtest checks it against WhatIfEngine.run.

Metrics are event-weighted (each event counts once, however many portfolios) and get
90% bootstrap intervals that resample whole events. The conformal width q_hat is the
event-weighted 80% quantile of |y - median| / spread over the dev cases, each of
which was predicted only from earlier events.

Caveats written into results.md: the stock universe is today's large caps
(survivorship bias); dev metrics are in-sample for the tuned settings; the language-
model baseline is only run on the holdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from scenario import engine as E
from scenario.enums import (
    FACTOR_NAMES,
    FACTOR_SEMIS,
    FACTOR_SPY,
    HORIZON_DAYS,
    PATH_DAYS,
    RANGE_LEVEL,
    RECOVERY_DAYS,
    Sector,
    Split,
    sector_from_yfinance,
)
from scenario.factors import fit_betas
from scenario.schemas import BacktestSummary, Event, MetricCI

ROOT = Path(__file__).resolve().parent
UNIVERSE_DIR = Path(os.getenv("SCENARIO_UNIVERSE_DIR", str(ROOT / "raw" / "universe")))
EVAL_DIR = ROOT / "eval"

# Long-listed US large caps across sectors. Sectors are fetched from Yahoo at download
# time, never typed here. Today's names: survivorship bias, stated in results.md.
UNIVERSE: tuple[str, ...] = (
    # technology and semiconductors
    "AAPL", "MSFT", "ORCL", "CSCO", "INTC", "IBM", "QCOM", "TXN", "ADBE", "HPQ", "AMAT", "MU",
    "NVDA", "AMD", "ADI", "KLAC", "LRCX", "ACN", "INTU", "CRM", "GOOGL", "META", "AVGO", "MCHP",
    # financials
    "JPM", "BAC", "C", "WFC", "GS", "MS", "AXP", "USB", "PNC", "BK", "SCHW", "AIG", "MET",
    "TRV", "ALL", "CB", "MMC", "BLK", "SPGI",
    # health care
    "JNJ", "PFE", "MRK", "ABT", "LLY", "BMY", "AMGN", "UNH", "MDT", "GILD", "CVS", "CI", "TMO",
    "SYK", "BDX",
    # energy
    "XOM", "CVX", "COP", "SLB", "OXY", "EOG", "HAL", "DVN", "APA",
    # industrials
    "GE", "HON", "MMM", "CAT", "DE", "BA", "LMT", "RTX", "UNP", "UPS", "FDX", "EMR", "GD", "NOC",
    "ITW", "CSX", "WM",
    # consumer discretionary
    "AMZN", "HD", "MCD", "NKE", "SBUX", "LOW", "TGT", "TJX", "F", "BBY",
    # consumer staples
    "PG", "KO", "PEP", "WMT", "COST", "CL", "KMB", "GIS", "MO", "SYY", "KR", "HSY",
    # utilities
    "DUK", "SO", "NEE", "D", "AEP", "EXC", "ED", "XEL", "SRE", "PEG",
    # materials
    "SHW", "APD", "ECL", "NUE", "FCX", "NEM", "IP",
    # communication
    "T", "VZ", "DIS", "CMCSA",
)

N_RANDOM = 200
SIZE_RANGE = (5, 15)
MIN_ELIGIBLE = 15
MIN_HISTORY = 252
BOOTSTRAP_RESAMPLES = 2000
SEED = 0
LOW_Q = (1 - RANGE_LEVEL) / 2
HIGH_Q = 1 - LOW_Q
FIT_COMBOS = ((0.1, False), (0.1, True), (1.0, False), (1.0, True))
GRID = {
    "similarity_threshold": (0.50, 0.55, 0.60, 0.65, 0.70),
    "category_bonus": (0.0, 0.05, 0.10),
    "nature_penalty": (0.0, 0.1, 0.3),
    "alpha": (0.1, 1.0),
    "stress_only": (False, True),
    "use_actual": (True, False),
}
ARCHETYPES = {
    "tech-heavy": {Sector.TECHNOLOGY, Sector.SEMICONDUCTORS},
    "semis": {Sector.SEMICONDUCTORS},
    "defensive": {Sector.CONSUMER_STAPLES, Sector.UTILITIES, Sector.HEALTH_CARE},
    "financials": {Sector.FINANCIALS},
    "energy": {Sector.ENERGY},
}
ARCHETYPE_MAX = 10


class BacktestError(RuntimeError):
    pass


# --------------------------------------------------------------------------- universe


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_universe(out_dir: Path = UNIVERSE_DIR, end: date | None = None) -> dict:
    """Adjusted closes and Yahoo sectors for UNIVERSE. Failures are recorded, never filled."""
    import yfinance as yf

    end = end or date.today()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "end": end.isoformat(),
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tickers": {},
        "failed": {},
    }
    for ticker in UNIVERSE:
        try:
            bars = yf.download(
                ticker, start="1998-12-01", end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=False, actions=False, progress=False, threads=False,
            )
            if bars is None or bars.empty:
                raise BacktestError("no rows")
            if isinstance(bars.columns, pd.MultiIndex):
                bars = bars.xs(ticker, axis=1, level=-1)
            series = bars["Adj Close"].dropna()
            series.index = pd.DatetimeIndex(series.index).tz_localize(None).normalize()
            if len(series) < 500:
                raise BacktestError(f"only {len(series)} rows")
            info = yf.Ticker(ticker).info or {}
            if not info.get("sector"):
                raise BacktestError("Yahoo has no sector")
            raw = series.to_frame("adj_close").to_csv(date_format="%Y-%m-%d", float_format="%.10g").encode()
            (out_dir / f"{ticker}.csv").write_bytes(raw)
            manifest["tickers"][ticker] = {
                "file": f"{ticker}.csv",
                "sha256": _sha256(raw),
                "rows": int(len(series)),
                "first": series.index[0].date().isoformat(),
                "last": series.index[-1].date().isoformat(),
                "sector": sector_from_yfinance(info.get("sector"), info.get("industry")).value,
                "yahoo_sector": info.get("sector"),
                "yahoo_industry": info.get("industry"),
            }
        except Exception as exc:  # noqa: BLE001 - recorded in the manifest
            manifest["failed"][ticker] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"{'ok  ' if ticker in manifest['tickers'] else 'FAIL'} {ticker}", flush=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def load_universe(raw_dir: Path = UNIVERSE_DIR) -> tuple[pd.DataFrame, dict[str, Sector], str]:
    """(adjusted closes, sectors, manifest sha256); refuses any file whose hash changed."""
    manifest_bytes = (raw_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    columns, sectors = {}, {}
    for ticker, entry in sorted(manifest["tickers"].items()):
        raw = (raw_dir / entry["file"]).read_bytes()
        if _sha256(raw) != entry["sha256"]:
            raise BacktestError(f"{entry['file']}: SHA256 does not match the universe manifest")
        frame = pd.read_csv(raw_dir / entry["file"], index_col=0, parse_dates=True)
        columns[ticker] = frame["adj_close"]
        sectors[ticker] = Sector(entry["sector"])
    return pd.DataFrame(columns).sort_index(), sectors, _sha256(manifest_bytes)


# --------------------------------------------------------------------------- vectorized engine maths


def weighted_quantile_columns(values: np.ndarray, weights: np.ndarray, q: float) -> np.ndarray:
    """engine.weighted_quantile applied to every column of `values` (rows share `weights`)."""
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    order = np.argsort(values, axis=0, kind="stable")
    sorted_values = np.take_along_axis(values, order, axis=0)
    cumulative = np.cumsum(weights[order], axis=0) / weights.sum()
    idx = np.argmax(cumulative >= q - 1e-12, axis=0)
    return sorted_values[idx, np.arange(values.shape[1])]


@dataclass(frozen=True)
class Settings:
    similarity_threshold: float
    category_bonus: float
    nature_penalty: float
    alpha: float
    stress_only: bool
    use_actual: bool
    top_k: int = 5

    def engine_settings(self) -> E.EngineSettings:
        return E.EngineSettings(
            alpha=self.alpha, stress_only=self.stress_only, category_bonus=self.category_bonus,
            context_weight=0.0, similarity_threshold=self.similarity_threshold, top_k=self.top_k,
            nature_penalty=self.nature_penalty, use_actual=self.use_actual,
        )


DEFAULT_SETTINGS = Settings(0.5, 0.05, 0.0, 1.0, False, True)


@dataclass
class Case:
    """One test event, ready to be scored under any Settings."""

    event: Event
    split: Split
    eligible: np.ndarray  # library rows usable as precedents
    eligible_ids: list[str]
    cosine: np.ndarray  # (n_eligible,) query vs precedent
    same_category: np.ndarray  # bool (n_eligible,)
    other_nature: np.ndarray  # bool (n_eligible,)
    stocks: list[str]
    y_stock: np.ndarray  # (S,) realized 21-day returns
    actual: np.ndarray  # (n_eligible, S) actual 21-day returns in each precedent, NaN if none
    estimates: dict[tuple[float, bool], np.ndarray]  # (alpha, stress) -> (n_eligible, S), NaN if no fit
    weights: np.ndarray  # (P, S) portfolio weights
    portfolio_names: list[str]
    beta_spy: np.ndarray  # (S,) for baseline 2
    spy_moves: np.ndarray  # (n_eligible,) SPY 21-day move per precedent
    b3_median: np.ndarray  # (P,) baseline 3 (random 21-day window)
    b3_low: np.ndarray
    b3_high: np.ndarray
    # v2 (conditional stress test): the event as the scenario
    betas: dict[tuple[float, bool], np.ndarray] = field(default_factory=dict)  # (S, F), NaN rows: no fit
    scenario_paths: np.ndarray | None = None  # (RECOVERY_DAYS + 1, F) this event's factor paths, SOXX proxied
    realized_paths: np.ndarray | None = None  # (S, RECOVERY_DAYS + 1) stocks' real cumulative paths, NaN unobserved


@dataclass
class Prediction:
    median: np.ndarray  # (P,)
    spread: np.ndarray  # (P,)
    y: np.ndarray  # (P,)
    stock_pred: np.ndarray  # (S,)
    low_confidence: bool
    used: list[str]


def predict(case: Case, settings: Settings) -> Prediction:
    score = case.cosine + settings.category_bonus * case.same_category - settings.nature_penalty * case.other_nature
    order = sorted(range(len(score)), key=lambda k: (-score[k], case.eligible_ids[k]))
    selected = [k for k in order if case.cosine[k] >= settings.similarity_threshold][: settings.top_k]
    if selected:
        raw = np.maximum(score[selected], 0.0)
        w = raw / raw.sum() if raw.sum() > 0 else np.full(len(selected), 1.0 / len(selected))
        low = False
    else:
        selected = order
        w = np.full(len(selected), 1.0 / len(selected))
        low = True

    actual = case.actual[selected]
    estimate = case.estimates[(settings.alpha, settings.stress_only)][selected]
    if settings.use_actual:
        returns = np.where(np.isfinite(actual), actual, estimate)
    else:
        returns = np.where(np.isfinite(estimate), estimate, actual)

    usable = np.all(np.isfinite(returns), axis=0)  # stocks with a value in every precedent
    held = case.weights * usable
    totals = held.sum(axis=1, keepdims=True)
    held = np.divide(held, totals, out=np.zeros_like(held), where=totals > 0)
    returns = np.where(np.isfinite(returns), returns, 0.0)

    port = returns @ held.T  # (k, P)
    median = weighted_quantile_columns(port, w, 0.5)
    spread = np.maximum(weighted_quantile_columns(np.abs(port - median), w, 0.5), E.SPREAD_FLOOR)
    return Prediction(
        median=median,
        spread=spread,
        y=held @ case.y_stock,
        stock_pred=w @ returns,
        low_confidence=low,
        used=[case.eligible_ids[k] for k in selected],
    )


# --------------------------------------------------------------------------- building cases


def _moves_21d(library: E.Library) -> np.ndarray:
    """(n, F) 21-day factor moves with SOXX's pre-listing NaN replaced by XLK (engine rule)."""
    moves = library.factor_paths[:, HORIZON_DAYS, :].astype(float).copy()
    names = list(library.factor_names)
    for name, proxy in E.PROXY_FOR.items():
        col, pcol = names.index(name), names.index(proxy)
        missing = ~np.isfinite(moves[:, col])
        moves[missing, col] = moves[missing, pcol]
    return moves


def _window_returns(prices: pd.DataFrame, event: Event) -> pd.Series:
    dates = E._path_dates(event.date, HORIZON_DAYS)
    start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[HORIZON_DAYS])
    if start not in prices.index or end not in prices.index:
        return pd.Series(np.nan, index=prices.columns)
    return prices.loc[end] / prices.loc[start] - 1.0


def _portfolios(stocks: list[str], sectors: dict[str, Sector], rng: np.random.Generator) -> tuple[np.ndarray, list[str]]:
    rows, names = [], []
    index = {s: i for i, s in enumerate(stocks)}
    for p in range(N_RANDOM):
        size = int(rng.integers(SIZE_RANGE[0], SIZE_RANGE[1] + 1))
        picks = rng.choice(len(stocks), size=min(size, len(stocks)), replace=False)
        row = np.zeros(len(stocks))
        row[picks] = 1.0 / len(picks)
        rows.append(row)
        names.append(f"random-{p:03d}")
    for name, wanted in ARCHETYPES.items():
        members = sorted(s for s in stocks if sectors[s] in wanted)[:ARCHETYPE_MAX]
        if len(members) >= 3:
            row = np.zeros(len(stocks))
            row[[index[m] for m in members]] = 1.0 / len(members)
            rows.append(row)
            names.append(name)
    balanced = []
    for sector in Sector:
        members = sorted(s for s in stocks if sectors[s] is sector)
        if members:
            balanced.append(members[0])
    if len(balanced) >= 3:
        row = np.zeros(len(stocks))
        row[[index[m] for m in balanced]] = 1.0 / len(balanced)
        rows.append(row)
        names.append("balanced")
    return np.asarray(rows), names


def build_cases(
    library: E.Library,
    prices: pd.DataFrame,
    sectors: dict[str, Sector],
    query_vectors: np.ndarray,
    splits: Iterable[Split] = (Split.DEV,),
    *,
    only: Sequence[str] | None = None,
) -> tuple[list[Case], list[dict]]:
    """Cases for every event in `splits` with at least MIN_ELIGIBLE precedents."""
    splits = set(splits)
    prices = prices.sort_index()
    daily = prices.pct_change(fill_method=None)
    rolling = prices / prices.shift(HORIZON_DAYS) - 1.0  # 21-day window ending on each date
    moves = _moves_21d(library)
    names = list(library.factor_names)
    spy_col = names.index(FACTOR_SPY)
    scenario_paths_all = library.factor_paths.astype(float).copy()
    for name, proxy in E.PROXY_FOR.items():
        col, pcol = names.index(name), names.index(proxy)
        missing = ~np.isfinite(scenario_paths_all[:, :, col])
        scenario_paths_all[:, :, col][missing] = scenario_paths_all[:, :, pcol][missing]
    actual_all = np.vstack([_window_returns(prices, e).reindex(prices.columns).to_numpy() for e in library.events])
    columns = list(prices.columns)

    cases, skipped = [], []
    for j, event in enumerate(library.events):
        if event.split not in splits or (only is not None and event.id not in only):
            continue
        as_of = event.date
        eligible = np.asarray(E.eligible_precedents(library.events, as_of), dtype=int)
        if len(eligible) < MIN_ELIGIBLE:
            skipped.append({"id": event.id, "reason": f"only {len(eligible)} eligible precedents"})
            continue
        realized = _window_returns(prices, event)
        history = prices[prices.index < pd.Timestamp(as_of)].notna().sum()
        stocks = [s for s in columns if math.isfinite(realized.get(s, math.nan)) and history[s] >= MIN_HISTORY]
        if len(stocks) < SIZE_RANGE[1]:
            skipped.append({"id": event.id, "reason": f"only {len(stocks)} stocks with prices"})
            continue
        cols = [columns.index(s) for s in stocks]

        estimates, beta_sets = {}, {}
        for alpha, stress in FIT_COMBOS:
            fits = fit_betas(daily[stocks], library.factor_history, as_of,
                             sectors={s: sectors[s] for s in stocks}, alpha=alpha, stress_only=stress)
            betas = np.full((len(stocks), len(names)), np.nan)
            for k, s in enumerate(stocks):
                if s in fits:
                    betas[k] = 0.0
                    for factor, beta in fits[s].betas.items():
                        betas[k, names.index(factor)] = beta
            estimates[(alpha, stress)] = moves[eligible] @ np.nan_to_num(betas).T
            estimates[(alpha, stress)][:, ~np.isfinite(betas).all(axis=1)] = np.nan
            beta_sets[(alpha, stress)] = betas

        window = daily[stocks][(daily.index < pd.Timestamp(as_of))].tail(3 * 252)
        spy = library.factor_history[FACTOR_SPY].reindex(window.index)
        beta_spy = np.array([
            float(np.cov(pd.concat([window[s], spy], axis=1).dropna().T)[0, 1] / spy.var())
            if window[s].notna().sum() > 60 else 1.0
            for s in stocks
        ])

        rng = np.random.default_rng(int(hashlib.sha256(f"{SEED}:{event.id}".encode()).hexdigest()[:8], 16))
        weights, portfolio_names = _portfolios(stocks, sectors, rng)

        past = rolling[stocks][rolling.index < pd.Timestamp(as_of)].to_numpy()
        valid = np.isfinite(past).astype(float) @ (weights > 0).T.astype(float) == (weights > 0).sum(axis=1)
        port_past = np.where(valid, np.nan_to_num(past) @ weights.T, np.nan)
        b3_low, b3_median, b3_high = np.nanquantile(port_past, [LOW_Q, 0.5, HIGH_Q], axis=0)

        path_dates = [pd.Timestamp(d) if d is not None else None for d in E._path_dates(event.date, RECOVERY_DAYS)]
        realized_levels = np.full((len(stocks), RECOVERY_DAYS + 1), np.nan)
        for t, d in enumerate(path_dates):
            if d is not None and d in prices.index:
                realized_levels[:, t] = prices.loc[d, stocks].to_numpy(dtype=float)
        realized_paths = realized_levels / realized_levels[:, :1] - 1.0
        cases.append(
            Case(
                event=event,
                split=event.split,
                eligible=eligible,
                eligible_ids=[library.events[i].id for i in eligible],
                cosine=np.clip(library.embeddings[eligible].astype(float) @ query_vectors[j], -1, 1),
                same_category=np.array([library.events[i].category == event.category for i in eligible]),
                other_nature=np.array([library.events[i].nature != event.nature for i in eligible]),
                stocks=stocks,
                y_stock=realized[stocks].to_numpy(dtype=float),
                actual=actual_all[np.ix_(eligible, cols)],
                estimates=estimates,
                weights=weights,
                portfolio_names=portfolio_names,
                beta_spy=beta_spy,
                spy_moves=moves[eligible, spy_col],
                b3_median=b3_median,
                b3_low=b3_low,
                b3_high=b3_high,
                betas=beta_sets,
                scenario_paths=scenario_paths_all[j],
                realized_paths=realized_paths,
            )
        )
    return cases, skipped


# --------------------------------------------------------------------------- metrics


@dataclass
class EventScores:
    event_id: str
    category: str
    n_portfolios: int
    coverage: float
    width: float  # median 80% width
    mae: float
    rank: float  # Spearman across stocks (NaN if undefined)
    b1_mae: float
    b2_mae: float
    b3_mae: float
    b3_width: float
    low_confidence: bool
    precedents: list[str] = field(default_factory=list)


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return math.nan
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


def baseline_predictions(case: Case) -> tuple[np.ndarray, np.ndarray]:
    """(baseline 1, baseline 2) point predictions per portfolio, from fixed (untuned) inputs."""
    returns = np.where(np.isfinite(case.actual), case.actual, case.estimates[(1.0, False)])
    usable = np.all(np.isfinite(returns), axis=0)
    held = case.weights * usable
    held = held / np.maximum(held.sum(axis=1, keepdims=True), 1e-12)
    b1 = np.nan_to_num(returns).mean(axis=0) @ held.T
    same = case.same_category
    category_move = case.spy_moves[same].mean() if same.any() else case.spy_moves.mean()
    b2 = (held @ case.beta_spy) * category_move
    return b1, b2


def score_event(case: Case, settings: Settings, q_hat: float) -> EventScores:
    pred = predict(case, settings)
    half = q_hat * pred.spread
    b1, b2 = baseline_predictions(case)
    y = pred.y
    return EventScores(
        event_id=case.event.id,
        category=case.event.category.value,
        n_portfolios=len(y),
        coverage=float(np.mean(np.abs(y - pred.median) <= half + 1e-12)),
        width=float(np.median(2 * half)),
        mae=float(np.mean(np.abs(y - pred.median))),
        rank=_spearman(pred.stock_pred, case.y_stock),
        b1_mae=float(np.mean(np.abs(y - b1))),
        b2_mae=float(np.mean(np.abs(y - b2))),
        b3_mae=float(np.mean(np.abs(y - case.b3_median))),
        b3_width=float(np.median(case.b3_high - case.b3_low)),
        low_confidence=pred.low_confidence,
        precedents=pred.used[: settings.top_k],
    )


def event_weighted_mae(cases: Sequence[Case], settings: Settings) -> float:
    return float(np.mean([np.mean(np.abs(p.y - p.median)) for p in (predict(c, settings) for c in cases)]))


def conformal_q(scores_by_event: Sequence[np.ndarray], level: float = RANGE_LEVEL) -> float:
    """Event-weighted `level` quantile of nonconformity scores (each event weighs 1)."""
    scores = [np.asarray(s, dtype=float) for s in scores_by_event if len(s)]
    if not scores:
        raise BacktestError("no scores to calibrate on")
    weights = [np.full(len(s), 1.0 / len(s)) for s in scores]
    return E.weighted_quantile(np.concatenate(scores), np.concatenate(weights), level)


def calibrate_q(cases: Sequence[Case], settings: Settings) -> float:
    """conformal_q of |y - median| / spread over cases predicted only from earlier events."""
    scores = []
    for case in cases:
        pred = predict(case, settings)
        scores.append(np.abs(pred.y - pred.median) / pred.spread)
    return conformal_q(scores)


def summarize(scores: Sequence[EventScores], *, resamples: int = BOOTSTRAP_RESAMPLES, seed: int = SEED) -> dict:
    """Point values and 90% event-bootstrap intervals for every section 2b metric."""
    table = pd.DataFrame([asdict(s) for s in scores])

    def stats(frame: pd.DataFrame) -> dict[str, float]:
        best = min(frame["b1_mae"].mean(), frame["b2_mae"].mean(), frame["b3_mae"].mean())
        return {
            "coverage_80": frame["coverage"].mean(),
            "width_ratio": frame["width"].median() / frame["b3_width"].median(),
            "mae": frame["mae"].mean(),
            "mae_best_baseline": best,
            "mae_improvement": 1 - frame["mae"].mean() / best,
            "rank_corr": frame["rank"].mean(),
            "b1_mae": frame["b1_mae"].mean(),
            "b2_mae": frame["b2_mae"].mean(),
            "b3_mae": frame["b3_mae"].mean(),
            "low_confidence_share": frame["low_confidence"].mean(),
        }

    point = stats(table)
    rng = np.random.default_rng(seed)
    draws = [stats(table.iloc[rng.integers(0, len(table), len(table))]) for _ in range(resamples)]
    out = {}
    for key, value in point.items():
        samples = np.array([d[key] for d in draws], dtype=float)
        out[key] = {
            "value": float(value),
            "ci_low": float(np.nanquantile(samples, 0.05)),
            "ci_high": float(np.nanquantile(samples, 0.95)),
        }
    out["events"] = int(len(table))
    out["cases"] = int(table["n_portfolios"].sum())
    return out


def gate(summary: dict) -> dict[str, bool]:
    """Section 2b hard gate G1-G4 (G5 compares dev and holdout and is checked in C5)."""
    return {
        "G1_coverage_75_85": 0.75 <= summary["coverage_80"]["value"] <= 0.85,
        "G2_width_ratio_le_0.85": summary["width_ratio"]["value"] <= 0.85,
        "G3_mae_10pct_better": summary["mae_improvement"]["value"] >= 0.10,
        "G4_rank_corr_ge_0.30": summary["rank_corr"]["value"] >= 0.30,
    }


# --------------------------------------------------------------------------- tuning


def grid() -> list[Settings]:
    keys = list(GRID)
    return [Settings(**dict(zip(keys, values))) for values in product(*(GRID[k] for k in keys))]


def tune(cases: Sequence[Case]) -> tuple[Settings, list[tuple[Settings, float]]]:
    """Pick the settings with the lowest event-weighted dev MAE. Refuses holdout events."""
    if any(c.split is not Split.DEV for c in cases):
        raise BacktestError("tune() was given a holdout event; tuning must only see dev")
    results = [(s, event_weighted_mae(cases, s)) for s in grid()]
    order = list(GRID)
    defaults = asdict(DEFAULT_SETTINGS)
    best = min(results, key=lambda r: (round(r[1], 10), sum(getattr(r[0], k) != defaults[k] for k in order)))
    return best[0], results


def settings_hash(settings: Settings, q_hat: float) -> str:
    payload = json.dumps({"settings": asdict(settings), "q_hat": round(q_hat, 12)}, sort_keys=True)
    return _sha256(payload.encode())


def holdout_ids_hash(library: E.Library) -> str:
    ids = sorted(e.id for e in library.events if e.split is Split.HOLDOUT)
    return _sha256("\n".join(ids).encode())


# --------------------------------------------------------------------------- reports


def _fmt(metric: dict, pct: bool = True) -> str:
    if pct:
        return f"{metric['value']:.1%} [{metric['ci_low']:.1%}, {metric['ci_high']:.1%}]"
    return f"{metric['value']:.2f} [{metric['ci_low']:.2f}, {metric['ci_high']:.2f}]"


def write_dev_report(
    path: Path, *, settings: Settings, q_hat: float, summary: dict, default_summary: dict,
    fallback_summary: dict, scores: Sequence[EventScores], skipped: Sequence[dict], tuning: Sequence,
    hashes: dict[str, str], universe_size: int,
) -> None:
    passes = gate(summary)
    top = sorted(tuning, key=lambda r: r[1])[:5]
    lines = [
        "# Scenario Lab backtest results",
        "",
        "## Dev split (1999–2022): tuning and calibration",
        "",
        "**These dev numbers are in-sample for the chosen settings and for the 80% width, so they flatter the method. "
        "The honest test is the one-time 2023+ holdout (C5).**",
        "",
        f"- Events scored: **{summary['events']}**; cases (event × portfolio): {summary['cases']}. "
        f"Skipped: {len(skipped)} (fewer than {MIN_ELIGIBLE} earlier precedents, mostly 1999–2002).",
        f"- Portfolios per event: {N_RANDOM} random equal-weight ({SIZE_RANGE[0]}–{SIZE_RANGE[1]} stocks) plus archetypes, "
        f"from a universe of {universe_size} US large caps.",
        f"- Settings grid: {len(tuning)} combinations; chosen by lowest event-weighted MAE.",
        f"- Chosen settings: `{json.dumps(asdict(settings), sort_keys=True)}`",
        f"- Calibrated q_hat (80% width multiplier): **{q_hat:.3f}**",
        "",
        "| Metric (event-weighted, 90% bootstrap CI) | Tuned | Untuned defaults | No-parse fallback |",
        "|---|---|---|---|",
        f"| G1 · 80% range coverage (target 75–85%) | {_fmt(summary['coverage_80'])} | {_fmt(default_summary['coverage_80'])} | {_fmt(fallback_summary['coverage_80'])} |",
        f"| G2 · width ÷ random-window width (≤ 0.85) | {_fmt(summary['width_ratio'], False)} | {_fmt(default_summary['width_ratio'], False)} | {_fmt(fallback_summary['width_ratio'], False)} |",
        f"| Typical-outcome MAE | {_fmt(summary['mae'])} | {_fmt(default_summary['mae'])} | {_fmt(fallback_summary['mae'])} |",
        f"| Best baseline MAE | {_fmt(summary['mae_best_baseline'])} | | |",
        f"| G3 · MAE improvement vs best baseline (≥ 10%) | {_fmt(summary['mae_improvement'])} | {_fmt(default_summary['mae_improvement'])} | {_fmt(fallback_summary['mae_improvement'])} |",
        f"| G4 · rank correlation across stocks (≥ 0.30) | {_fmt(summary['rank_corr'], False)} | {_fmt(default_summary['rank_corr'], False)} | {_fmt(fallback_summary['rank_corr'], False)} |",
        f"| Low-confidence share | {_fmt(summary['low_confidence_share'])} | {_fmt(default_summary['low_confidence_share'])} | {_fmt(fallback_summary['low_confidence_share'])} |",
        "",
        "Baselines (MAE): "
        f"1 · average of all past events {_fmt(summary['b1_mae'])}; "
        f"2 · beta × category-average S&P move {_fmt(summary['b2_mae'])}; "
        f"3 · random 21-day window {_fmt(summary['b3_mae'])}. "
        "Baseline 4 (language model guessing) is run on the holdout only.",
        "",
        "Gate preview on dev (not the gate; the holdout is): "
        + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in passes.items()),
        "",
        "### Five best settings on dev MAE",
        "| MAE | settings |",
        "|---|---|",
        *[f"| {m:.4f} | `{json.dumps(asdict(s), sort_keys=True)}` |" for s, m in top],
        "",
        "### Coverage by category (dev)",
        "| Category | Events | Coverage | MAE |",
        "|---|---|---|---|",
    ]
    frame = pd.DataFrame([asdict(s) for s in scores])
    for category, group in frame.groupby("category"):
        lines.append(f"| {category} | {len(group)} | {group['coverage'].mean():.0%} | {group['mae'].mean():.1%} |")
    lines += [
        "",
        "### Per event (dev, tuned settings)",
        "| Event | Coverage | MAE | Best baseline MAE | Rank | Low conf. | Precedents used |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in scores:
        rank = "—" if math.isnan(s.rank) else f"{s.rank:.2f}"
        lines.append(
            f"| {s.event_id} | {s.coverage:.0%} | {s.mae:.1%} | {min(s.b1_mae, s.b2_mae, s.b3_mae):.1%} | {rank} | "
            f"{'yes' if s.low_confidence else ''} | {', '.join(s.precedents[:5])} |"
        )
    lines += [
        "",
        "### Skipped events",
        *[f"- {s['id']}: {s['reason']}" for s in skipped],
        "",
        "### Caveats",
        "- **Survivorship bias:** the stock universe is today's large caps. Stocks that failed or were delisted "
        "are missing, which likely makes past portfolios look calmer than real ones.",
        "- **Oracle parse:** the tuned column assumes the parser classifies category and nature correctly. "
        "The no-parse column is the lower bound if it never does.",
        "- **In-sample:** settings and q_hat were chosen on these same events. Expect the holdout to be worse.",
        "- **Few events:** about one hundred dev events; the intervals are wide.",
        "- **Not yet measured:** recovery-range coverage and the language-model baseline (holdout, C5).",
        "",
        "### Reproducibility",
        *[f"- {k}: `{v}`" for k, v in hashes.items()],
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def _metric_ci(summary: dict, key: str) -> MetricCI:
    m = summary[key]
    return MetricCI(value=m["value"], ci_low=m["ci_low"], ci_high=m["ci_high"])


# --------------------------------------------------------------------------- diagnostics


def _sector_betas(case: Case, library: E.Library, prices: pd.DataFrame, sectors: dict[str, Sector], alpha: float) -> np.ndarray:
    names = list(library.factor_names)
    fits = fit_betas(prices[case.stocks].pct_change(fill_method=None), library.factor_history, case.event.date,
                     sectors={s: sectors[s] for s in case.stocks}, alpha=alpha)
    betas = np.zeros((len(case.stocks), len(names)))
    for k, s in enumerate(case.stocks):
        for factor, beta in fits.get(s, None).betas.items() if s in fits else []:
            betas[k, names.index(factor)] = beta
    return betas


def diagnostics(library: E.Library, prices: pd.DataFrame, sectors: dict[str, Sector], cases: Sequence[Case],
                settings: Settings, *, seed: int = SEED) -> pd.DataFrame:
    """Per dev event: forecast errors (engine, 5 random precedents, zero) and conditional
    errors given the event's own real factor moves (multi-factor betas, beta x S&P)."""
    moves = _moves_21d(library)
    names = list(library.factor_names)
    spy = names.index(FACTOR_SPY)
    ids = [e.id for e in library.events]
    rng = np.random.default_rng(seed)
    rows = []
    for case in cases:
        j = ids.index(case.event.id)
        pred = predict(case, settings)
        held, y = case.weights, pred.y
        pick = rng.choice(len(case.eligible), min(5, len(case.eligible)), replace=False)
        random5 = np.median(case.estimates[(1.0, False)][pick] @ held.T, axis=0)
        row = {
            "event_id": case.event.id,
            "spy_21d": float(moves[j, spy]),
            "forecast_engine": float(np.mean(np.abs(y - pred.median))),
            "forecast_random5": float(np.mean(np.abs(y - random5))),
            "forecast_zero": float(np.mean(np.abs(y))),
            "rank_forecast": _spearman(pred.stock_pred, case.y_stock),
            "conditional_beta_spx": float(np.mean(np.abs(y - (held @ case.beta_spy) * moves[j, spy]))),
            "rank_beta_spx": _spearman(case.beta_spy * moves[j, spy], case.y_stock),
        }
        for alpha in (0.1, 1.0):
            stock = _sector_betas(case, library, prices, sectors, alpha) @ moves[j]
            row[f"conditional_factor_a{alpha}"] = float(np.mean(np.abs(y - held @ stock)))
            row[f"rank_factor_a{alpha}"] = _spearman(stock, case.y_stock)
        rows.append(row)
    return pd.DataFrame(rows)


def write_diagnostics(path: Path, table: pd.DataFrame, settings: Settings) -> None:
    rng = np.random.default_rng(SEED)

    def ci(series: pd.Series) -> str:
        draws = [series.sample(len(series), replace=True, random_state=int(rng.integers(1 << 31))).mean() for _ in range(2000)]
        return f"{series.mean():.4f} [{np.quantile(draws, 0.05):.4f}, {np.quantile(draws, 0.95):.4f}]"

    big = table[table["spy_21d"].abs() > 0.05]
    cols = [c for c in table.columns if c not in ("event_id", "spy_21d")]
    lines = [
        "# Scenario Lab dev diagnostics",
        "",
        f"Dev events: {len(table)} ({len(big)} with an S&P move above 5% in 21 days). Event-weighted means, "
        "90% bootstrap CI over events. Forecast settings: "
        f"`{json.dumps(asdict(settings), sort_keys=True)}`.",
        "",
        "- **Forecast** = the engine's question as designed: what happens next, from past precedents.",
        "- **Conditional** = given the event's own real 21-day factor moves (\"if it plays out like this\"), "
        "how well the portfolio impact is estimated. Not a forecast: it shows what the factor model "
        "does once a path is assumed.",
        "",
        "| Measure | All dev events | S&P moved > 5% |",
        "|---|---|---|",
        *[f"| {c} | {ci(table[c].dropna())} | {ci(big[c].dropna())} |" for c in cols],
        "",
        "MAE rows are 21-day portfolio return errors; rank rows are Spearman correlations across stocks.",
        "",
    ]
    path.write_text("\n".join(lines))


# --------------------------------------------------------------------------- v2: conditional stress test


BUCKET_ORDER = [b for b in E.RECOVERY_BUCKETS if b != "unknown"]
CONTROLS_PATH = EVAL_DIR / "controls.txt"


def _rows_drawdown(paths: np.ndarray) -> np.ndarray:
    """Worst fall per row of cumulative paths (rows must be finite)."""
    wealth = 1.0 + paths
    return np.minimum(0.0, np.min(wealth / np.maximum.accumulate(wealth, axis=1) - 1.0, axis=1))


def _bucket(path: np.ndarray) -> str:
    values = [float(v) if np.isfinite(v) else None for v in path]
    days = E.recovery_days(values)
    known = days is not None or all(v is not None for v in values)
    return E.recovery_bucket(days, known)


def _portfolio_paths(stock_paths: np.ndarray, held: np.ndarray) -> np.ndarray:
    """(P, T) portfolio paths; NaN wherever any held stock is unobserved."""
    finite = np.isfinite(stock_paths)
    counts = finite.T.astype(float) @ (held > 0).T.astype(float)  # (T, P)
    paths = (np.nan_to_num(stock_paths).T @ held.T)  # (T, P)
    paths[counts < (held > 0).sum(axis=1)] = np.nan
    return paths.T


@dataclass
class ConditionalScores:
    event_id: str
    category: str
    n_portfolios: int
    h1_mae: float
    h1_base: float
    h2_rank: float
    h3_mae: float
    h3_base: float
    h3_cases: int
    h4_cases: int
    h4_within1: float
    h4_exact: float
    h4_exact_base: float


def conditional_score(case: Case, alpha: float, stress: bool) -> ConditionalScores:
    """Score one event as a scenario: pre-event betas x the event's real factor paths,
    against the stocks' real moves (PLAN v2 gate). Baseline: portfolio beta x the S&P path."""
    betas = case.betas[(alpha, stress)]
    usable = np.all(np.isfinite(betas), axis=1)
    held = case.weights * usable
    held = np.divide(held, held.sum(axis=1, keepdims=True), out=np.zeros_like(held), where=held.sum(axis=1, keepdims=True) > 0)

    stock_paths = np.nan_to_num(betas) @ case.scenario_paths.T  # (S, T); NaN where the scenario path is NaN
    stock_paths[:, ~np.all(np.isfinite(case.scenario_paths), axis=1)] = np.nan
    estimate = _portfolio_paths(stock_paths, held)
    spy = case.scenario_paths[:, FACTOR_NAMES.index(FACTOR_SPY)]
    baseline = (held @ case.beta_spy)[:, None] * spy[None, :]
    real = _portfolio_paths(case.realized_paths, held)

    y = held @ case.y_stock
    h1 = float(np.mean(np.abs(y - estimate[:, HORIZON_DAYS])))
    h1_base = float(np.mean(np.abs(y - baseline[:, HORIZON_DAYS])))
    h2 = _spearman(stock_paths[usable, HORIZON_DAYS], case.y_stock[usable])

    window = slice(0, PATH_DAYS + 1)
    ok = np.all(np.isfinite(real[:, window]), axis=1) & np.all(np.isfinite(estimate[:, window]), axis=1)
    if ok.any():
        dd_real = _rows_drawdown(real[ok, window])
        h3 = float(np.mean(np.abs(_rows_drawdown(estimate[ok, window]) - dd_real)))
        h3_base = float(np.mean(np.abs(_rows_drawdown(baseline[ok, window]) - dd_real)))
    else:
        h3 = h3_base = math.nan

    within, exact, exact_base = [], [], []
    for p in range(len(held)):
        truth = _bucket(real[p])
        if truth == "unknown":
            continue
        guess, base = _bucket(estimate[p]), _bucket(baseline[p])
        exact.append(guess == truth)
        exact_base.append(base == truth)
        within.append(guess != "unknown" and abs(BUCKET_ORDER.index(guess) - BUCKET_ORDER.index(truth)) <= 1)
    return ConditionalScores(
        event_id=case.event.id, category=case.event.category.value, n_portfolios=len(held),
        h1_mae=h1, h1_base=h1_base, h2_rank=h2, h3_mae=h3, h3_base=h3_base, h3_cases=int(ok.sum()),
        h4_cases=len(exact),
        h4_within1=float(np.mean(within)) if within else math.nan,
        h4_exact=float(np.mean(exact)) if exact else math.nan,
        h4_exact_base=float(np.mean(exact_base)) if exact_base else math.nan,
    )


def summarize_v2(scores: Sequence[ConditionalScores], *, resamples: int = BOOTSTRAP_RESAMPLES, seed: int = SEED) -> dict:
    table = pd.DataFrame([asdict(s) for s in scores])

    def stats(frame: pd.DataFrame) -> dict[str, float]:
        return {
            "h1_mae": frame["h1_mae"].mean(),
            "h1_base": frame["h1_base"].mean(),
            "h1_improvement": 1 - frame["h1_mae"].mean() / frame["h1_base"].mean(),
            "h2_rank": frame["h2_rank"].mean(),
            "h3_mae": frame["h3_mae"].mean(),
            "h3_base": frame["h3_base"].mean(),
            "h3_improvement": 1 - frame["h3_mae"].mean() / frame["h3_base"].mean(),
            "h4_within1": frame["h4_within1"].mean(),
            "h4_exact": frame["h4_exact"].mean(),
            "h4_exact_base": frame["h4_exact_base"].mean(),
        }

    point = stats(table)
    rng = np.random.default_rng(seed)
    draws = [stats(table.iloc[rng.integers(0, len(table), len(table))]) for _ in range(resamples)]
    out = {}
    for key, value in point.items():
        samples = np.array([d[key] for d in draws], dtype=float)
        out[key] = {"value": float(value), "ci_low": float(np.nanquantile(samples, 0.05)),
                    "ci_high": float(np.nanquantile(samples, 0.95))}
    out["events"] = int(len(table))
    out["h4_events"] = int(table["h4_within1"].notna().sum())
    out["h4_cases"] = int(table["h4_cases"].sum())
    return out


def gate_v2(summary: dict) -> dict[str, bool]:
    """PLAN v2 gate H1-H4 (pass marks fixed 2026-11-13). H5 compares dev and holdout in C5."""
    return {
        "H1_factor_10pct_better_than_beta": summary["h1_improvement"]["value"] >= 0.10,
        "H2_rank_ge_0.30": summary["h2_rank"]["value"] >= 0.30,
        "H3_drawdown_10pct_better_than_beta": summary["h3_improvement"]["value"] >= 0.10,
        "H4_within_one_bucket_ge_75pct_and_exact_ge_baseline": (
            summary["h4_within1"]["value"] >= 0.75 and summary["h4_exact"]["value"] >= summary["h4_exact_base"]["value"]
        ),
    }


def tune_v2(cases: Sequence[Case]) -> tuple[tuple[float, bool], dict]:
    """Ridge strength and stress betas by event-weighted H1 MAE, then H2 (dev only)."""
    if any(c.split is not Split.DEV for c in cases):
        raise BacktestError("tune_v2() was given a holdout event; tuning must only see dev")
    table = {}
    for combo in FIT_COMBOS:
        rows = [conditional_score(c, *combo) for c in cases]
        table[combo] = (float(np.mean([r.h1_mae for r in rows])), float(np.nanmean([r.h2_rank for r in rows])))
    best = min(table, key=lambda k: (round(table[k][0], 10), -table[k][1]))
    return best, table


def control_threshold(library: E.Library, embed, controls_path: Path = CONTROLS_PATH) -> tuple[float, list[tuple[str, float]]]:
    """max(0.5, 95th percentile of each off-topic control's best cosine against the library)."""
    questions = [line.strip() for line in controls_path.read_text().splitlines() if line.strip() and not line.startswith("#")]
    vectors = np.asarray(embed(questions), dtype=float)
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    best = (vectors @ library.embeddings.astype(float).T).max(axis=1)
    return max(0.5, float(np.quantile(best, 0.95))), sorted(zip(questions, best.tolist()), key=lambda r: -r[1])


def write_crises(library: E.Library, as_of: date | None = None) -> list[int]:
    """scenario/eval/crises.md: the crisis replay set under engine.crisis_events."""
    as_of = as_of or date.today()
    rows = E.crisis_events(library, as_of)
    spy = library.factor_names.index(FACTOR_SPY)
    lines = [
        "# Crisis replay set",
        "",
        f"As of {as_of}. Rule (user-approved 2026-11-13): the S&P fell 10% or more within 21 trading days; "
        "events within 63 trading days of each other form one episode, named by its adverse event with the "
        "deepest fall. (The first rule, a 10% fall anywhere in 63 days, gave 34 events, including some that "
        "only came before a crash, such as the December 2019 US–China deal two months before COVID.)",
        "",
        "| Crisis | Date | S&P worst fall, 21 days | S&P worst fall, 63 days |",
        "|---|---|---|---|",
    ]
    for i in rows:
        path = [float(v) for v in library.factor_paths[i, :, spy]]
        lines.append(f"| {library.events[i].name} (`{library.events[i].id}`) | {library.events[i].date} | "
                     f"{E._drawdown(path[: HORIZON_DAYS + 1]):+.1%} | {E._drawdown(path[: PATH_DAYS + 1]):+.1%} |")
    (EVAL_DIR / "crises.md").write_text("\n".join(lines) + "\n")
    return rows


def write_v2_reports(*, library, cases, skipped, combo, tuning, summary, threshold, controls, real_best,
                     hashes, universe_size) -> None:
    gate = gate_v2(summary)

    def f(key: str, pct: bool = True) -> str:
        return _fmt(summary[key], pct)

    lines = [
        "# Scenario Lab backtest results (v2: stress test)",
        "",
        "Plan v2 measures the claim the page makes: **if a shock like this happens, what does it do to this "
        "portfolio?** Each dev event (1999–2022) is the scenario; betas use only prices before it; the estimate "
        "uses that event's real factor moves and is compared with the stocks' real moves. Baseline: portfolio "
        "beta × the S&P path. Pass marks were fixed in PLAN.md before this run.",
        "",
        "**Dev results are in-sample for the two tuned choices (ridge strength, stress betas). The one-time "
        "2023+ holdout (C5) is the gate.** The forecast results from C4 are kept in `results_forecast_v1.md`.",
        "",
        f"- Events: **{summary['events']}** ({len(skipped)} skipped, mostly 1999–2002 with too few precedents); "
        f"portfolios per event: {N_RANDOM} random + archetypes from {universe_size} US large caps.",
        f"- Tuned on dev: alpha = {combo[0]}, stress betas = {combo[1]} "
        "(by H1 MAE, then H2; all four shown below).",
        f"- Recovery-time cases with a known real recovery: {summary['h4_cases']} across {summary['h4_events']} events.",
        "",
        "| Gate v2 | Pass mark | Dev result [90% CI] | |",
        "|---|---|---|---|",
        f"| H1 · 21-day portfolio MAE, factor vs beta × S&P | ≥ 10% lower | {f('h1_mae')} vs {f('h1_base')}: "
        f"{f('h1_improvement')} lower | {'pass' if gate['H1_factor_10pct_better_than_beta'] else 'FAIL'} |",
        f"| H2 · holding ranking (Spearman) | ≥ 0.30 | {f('h2_rank', False)} | {'pass' if gate['H2_rank_ge_0.30'] else 'FAIL'} |",
        f"| H3 · worst fall within 63 days, MAE | ≥ 10% lower | {f('h3_mae')} vs {f('h3_base')}: {f('h3_improvement')} lower | "
        f"{'pass' if gate['H3_drawdown_10pct_better_than_beta'] else 'FAIL'} |",
        f"| H4 · recovery time, within one bucket | ≥ 75% and exact ≥ baseline | within one {f('h4_within1')}; exact "
        f"{f('h4_exact')} vs baseline {f('h4_exact_base')} | "
        f"{'pass' if gate['H4_within_one_bucket_ge_75pct_and_exact_ge_baseline'] else 'FAIL'} |",
        "",
        "H4 buckets: never fell, 1–21, 22–63, 64–126, 127–252, 253–504 trading days, not within 504. "
        "Only cases whose real recovery is known (recovered, or observed for all 504 days) are scored.",
        "",
        "### Ridge strength and stress betas (dev)",
        "| alpha | stress betas | H1 MAE | H2 rank |",
        "|---|---|---|---|",
        *[f"| {a} | {st} | {m:.4f} | {r:.3f} |" for (a, st), (m, r) in tuning.items()],
        "",
        "### Low-confidence threshold (off-topic controls)",
        f"Threshold = max(0.5, 95th percentile of the controls' best cosine) = **{threshold:.3f}**. "
        f"Real dev questions (event triggers) above it: {np.mean([b >= threshold for b in real_best]):.0%} "
        f"(median best cosine {np.median(real_best):.3f}).",
        "",
        "| Highest-scoring controls | best cosine |",
        "|---|---|",
        *[f"| {q} | {b:.3f} |" for q, b in controls[:5]],
        "",
        "### Per event (dev)",
        "| Event | H1 MAE | baseline | H2 rank | H3 MAE | baseline | H4 within one | H4 exact | baseline exact |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in cases:
        r = conditional_score(c, *combo)
        def pct(v): return "—" if v != v else f"{v:.1%}"
        def num(v): return "—" if v != v else f"{v:.2f}"
        lines.append(f"| {r.event_id} | {pct(r.h1_mae)} | {pct(r.h1_base)} | {num(r.h2_rank)} | {pct(r.h3_mae)} | "
                     f"{pct(r.h3_base)} | {pct(r.h4_within1)} | {pct(r.h4_exact)} | {pct(r.h4_exact_base)} |")
    lines += [
        "",
        "### Caveats",
        "- **Conditional, not a forecast:** these numbers say how well Arcus replays a scenario on a portfolio "
        "once the scenario's market path is given. They say nothing about whether or when a shock happens.",
        "- **Survivorship bias:** the universe is today's large caps.",
        "- **Few events:** about one hundred; the intervals are wide.",
        "",
        "### Reproducibility",
        *[f"- {k}: `{v}`" for k, v in hashes.items()],
        "",
    ]
    (EVAL_DIR / "results.md").write_text("\n".join(lines))

    write_crises(library)


def run_dev_v2() -> dict:
    from research.embedder import shared_embedder

    t0 = time.time()
    library, prices, cases, skipped, hashes = _prepare([Split.DEV])
    print(f"built {len(cases)} dev cases ({len(skipped)} skipped) in {time.time() - t0:.0f}s", flush=True)
    combo, tuning = tune_v2(cases)
    summary = summarize_v2([conditional_score(c, *combo) for c in cases])
    embedder = shared_embedder()
    threshold, controls = control_threshold(library, lambda texts: embedder.encode(texts))
    real_best = [float(np.max(c.cosine)) for c in cases]
    write_v2_reports(library=library, cases=cases, skipped=skipped, combo=combo, tuning=tuning, summary=summary,
                     threshold=threshold, controls=controls, real_best=real_best, hashes=hashes,
                     universe_size=prices.shape[1])
    v1_dev = json.loads((EVAL_DIR / "calibration_forecast_v1_dev.json").read_text())["settings"]
    settings = E.EngineSettings(
        alpha=combo[0], stress_only=combo[1], category_bonus=v1_dev["category_bonus"], context_weight=0.0,
        similarity_threshold=threshold, top_k=5, nature_penalty=v1_dev["nature_penalty"], use_actual=True,
    )
    calibration = {
        "stage": "dev",
        "version": 2,
        "q_hat": 0.0,
        "settings": asdict(settings),
        "settings_sha256": _sha256(json.dumps(asdict(settings), sort_keys=True).encode()),
        "holdout_ids_sha256": holdout_ids_hash(library),
        "data_sha256": hashes,
        "dev_v2": summary,
        "dev_gate_v2": gate_v2(summary),
        "backtest": BacktestSummary(available=False).model_dump(),
        "backtest_v2": {"available": False},
    }
    (EVAL_DIR / "calibration_dev.json").write_text(json.dumps(calibration, indent=1, sort_keys=True) + "\n")
    print(f"done in {time.time() - t0:.0f}s; combo {combo}; threshold {threshold:.3f}")
    print(json.dumps({k: v for k, v in summary.items() if isinstance(v, dict)}, indent=1))
    print(json.dumps(gate_v2(summary), indent=1))
    return calibration


# --------------------------------------------------------------------------- C5: one-time holdout (gate v2)

HOLDOUT_MARKER = EVAL_DIR / "holdout_run.json"
CORE_GATES = ("H1_factor_10pct_better_than_beta", "H2_rank_ge_0.30", "H3_drawdown_10pct_better_than_beta",
              "H5_dev_and_holdout_agree")
H4_GATE = "H4_within_one_bucket_ge_75pct_and_exact_ge_baseline"


def h5_agree(dev: dict, holdout: dict) -> bool:
    """H5: H1-H3 point the same way on dev and holdout (improvement or rank above zero)."""
    keys = ("h1_improvement", "h2_rank", "h3_improvement")
    return all((dev[k]["value"] > 0) == (holdout[k]["value"] > 0) for k in keys)


def _ci(summary: dict, key: str) -> MetricCI | None:
    m = summary.get(key)
    if not m or any(not math.isfinite(m[x]) for x in ("value", "ci_low", "ci_high")):
        return None
    return MetricCI(value=m["value"], ci_low=m["ci_low"], ci_high=m["ci_high"])


def holdout_outcome(gate: dict[str, bool]) -> str:
    """Pre-registered (PLAN v2): any of H1-H3 or H5 failing stops; H4 alone failing
    shows recovery from actual prices only."""
    if not all(gate[k] for k in CORE_GATES):
        return "stop"
    return "all" if gate[H4_GATE] else "actual_only"


def run_holdout_v2() -> dict:
    if os.getenv("SCENARIO_RUN_HOLDOUT") != "1":
        raise BacktestError("the holdout runs once, after the user writes 'run holdout'; set SCENARIO_RUN_HOLDOUT=1")
    if HOLDOUT_MARKER.exists():
        raise BacktestError(f"the holdout has already been run ({HOLDOUT_MARKER}); it runs once")
    dev = json.loads((EVAL_DIR / "calibration_dev.json").read_text())
    if _sha256(json.dumps(dev["settings"], sort_keys=True).encode()) != dev["settings_sha256"]:
        raise BacktestError("dev settings do not match their frozen hash")
    t0 = time.time()
    library, prices, cases, skipped, hashes = _prepare([Split.HOLDOUT])
    if holdout_ids_hash(library) != dev["holdout_ids_sha256"]:
        raise BacktestError("the holdout events changed since the dev run")
    combo = (dev["settings"]["alpha"], dev["settings"]["stress_only"])
    scores = [conditional_score(c, *combo) for c in cases]
    summary = summarize_v2(scores)
    gate = gate_v2(summary)
    gate["H5_dev_and_holdout_agree"] = h5_agree(dev["dev_v2"], summary)
    outcome = holdout_outcome(gate)
    run_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    marker = {"run_at": run_at, "outcome": outcome, "gate": gate, "holdout_v2": summary,
              "settings_sha256": dev["settings_sha256"], "holdout_ids_sha256": dev["holdout_ids_sha256"],
              "events": [s.event_id for s in scores], "skipped": skipped, "data_sha256": hashes}
    HOLDOUT_MARKER.write_text(json.dumps(marker, indent=1, sort_keys=True) + "\n")
    _append_holdout_report(summary, gate, outcome, scores, skipped, run_at, combo)

    if outcome != "stop":
        backtest_v2 = BacktestSummaryV2(
            available=True, holdout_events=summary["events"],
            h1_mae=_ci(summary, "h1_mae"), h1_mae_baseline=_ci(summary, "h1_base"), h2_rank=_ci(summary, "h2_rank"),
            h3_drawdown_mae=_ci(summary, "h3_mae"), h3_drawdown_mae_baseline=_ci(summary, "h3_base"),
            h4_within_one_bucket=_ci(summary, "h4_within1"), h4_exact_bucket=_ci(summary, "h4_exact"),
            h4_exact_bucket_baseline=_ci(summary, "h4_exact_base"),
            gate_passed=all(gate.values()), recovery_shown_from=outcome,
        )
        calibration = {**dev, "stage": "holdout", "holdout_run_at": run_at, "holdout_v2": summary,
                       "holdout_gate": gate, "backtest_v2": json.loads(backtest_v2.model_dump_json())}
        (EVAL_DIR / "calibration.json").write_text(json.dumps(calibration, indent=1, sort_keys=True) + "\n")
    print(f"holdout done in {time.time() - t0:.0f}s: {len(scores)} events, outcome {outcome}")
    print(json.dumps(gate, indent=1))
    return marker


def _append_holdout_report(summary, gate, outcome, scores, skipped, run_at, combo) -> None:
    def f(key: str, pct: bool = True) -> str:
        return "—" if not _ci(summary, key) else _fmt(summary[key], pct)

    verdict = {"all": "**Passed.** The engine may serve answers; recovery is shown for all holdings.",
               "actual_only": "**H1–H3 and H5 passed; H4 failed.** Pre-registered fallback: recovery times are "
                              "shown only where they come from actual prices.",
               "stop": "**Failed (H1, H2, H3 or H5).** Pre-registered: stop; no calibration.json is written; "
                       "the user decides."}[outcome]
    lines = [
        "",
        f"## Holdout (2023+): run once on {run_at}",
        "",
        f"Frozen dev settings (alpha {combo[0]}, stress betas {combo[1]}); settings and holdout-event hashes "
        f"verified before the run. Events scored: **{summary['events']}** ({len(skipped)} skipped: "
        f"{', '.join(s['id'] for s in skipped) or 'none'}). Recovery cases with a known real recovery: "
        f"{summary['h4_cases']} across {summary['h4_events']} events.",
        "",
        "| Gate v2 | Pass mark | Holdout [90% CI] | |",
        "|---|---|---|---|",
        f"| H1 · 21-day MAE vs beta × S&P | ≥ 10% lower | {f('h1_mae')} vs {f('h1_base')}: {f('h1_improvement')} lower | "
        f"{'pass' if gate['H1_factor_10pct_better_than_beta'] else 'FAIL'} |",
        f"| H2 · holding ranking | ≥ 0.30 | {f('h2_rank', False)} | {'pass' if gate['H2_rank_ge_0.30'] else 'FAIL'} |",
        f"| H3 · 63-day worst fall MAE | ≥ 10% lower | {f('h3_mae')} vs {f('h3_base')}: {f('h3_improvement')} lower | "
        f"{'pass' if gate['H3_drawdown_10pct_better_than_beta'] else 'FAIL'} |",
        f"| H4 · recovery within one bucket | ≥ 75% and exact ≥ baseline | {f('h4_within1')}; exact {f('h4_exact')} vs "
        f"{f('h4_exact_base')} | {'pass' if gate[H4_GATE] else 'FAIL'} |",
        f"| H5 · H1–H3 agree with dev | must match | | {'pass' if gate['H5_dev_and_holdout_agree'] else 'FAIL'} |",
        "",
        verdict,
        "",
        "| Event | H1 MAE | baseline | H2 rank | H3 MAE | baseline | H4 within one | H4 exact | baseline exact |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in scores:
        def pct(v): return "—" if v != v else f"{v:.1%}"
        def num(v): return "—" if v != v else f"{v:.2f}"
        lines.append(f"| {r.event_id} | {pct(r.h1_mae)} | {pct(r.h1_base)} | {num(r.h2_rank)} | {pct(r.h3_mae)} | "
                     f"{pct(r.h3_base)} | {pct(r.h4_within1)} | {pct(r.h4_exact)} | {pct(r.h4_exact_base)} |")
    lines.append("")
    with open(EVAL_DIR / "results.md", "a") as handle:
        handle.write("\n".join(lines))


# --------------------------------------------------------------------------- CLI


def _prepare(splits: Iterable[Split]):
    from research.embedder import shared_embedder
    from scenario.build_library import ASSETS_DIR, load_library

    library = load_library(ASSETS_DIR)
    prices, sectors, universe_sha = load_universe()
    embedder = shared_embedder()
    queries = np.asarray(embedder.encode([e.trigger for e in library.events]), dtype=float)
    queries /= np.maximum(np.linalg.norm(queries, axis=1, keepdims=True), 1e-12)
    cases, skipped = build_cases(library, prices, sectors, queries, splits)
    hashes = {
        "library.npz": _sha256((ASSETS_DIR / "library.npz").read_bytes()),
        "library.json": _sha256((ASSETS_DIR / "library.json").read_bytes()),
        "universe manifest": universe_sha,
    }
    return library, prices, cases, skipped, hashes


def _no_parse(cases: Sequence[Case]) -> list[Case]:
    """The same cases with no category or nature (parser fallback)."""
    out = []
    for c in cases:
        clone = Case(**{**c.__dict__})
        clone.same_category = np.zeros_like(c.same_category)
        clone.other_nature = np.zeros_like(c.other_nature)
        out.append(clone)
    return out


def run_dev() -> dict:
    t0 = time.time()
    library, prices, cases, skipped, hashes = _prepare([Split.DEV])
    print(f"built {len(cases)} dev cases ({len(skipped)} skipped) in {time.time() - t0:.0f}s", flush=True)
    settings, tuning = tune(cases)
    q_hat = calibrate_q(cases, settings)
    scores = [score_event(c, settings, q_hat) for c in cases]
    summary = summarize(scores)
    default_q = calibrate_q(cases, DEFAULT_SETTINGS)
    default_summary = summarize([score_event(c, DEFAULT_SETTINGS, default_q) for c in cases])
    fallback_cases = _no_parse(cases)
    fallback_summary = summarize([score_event(c, settings, q_hat) for c in fallback_cases])

    write_dev_report(
        EVAL_DIR / "results_forecast_v1.md", settings=settings, q_hat=q_hat, summary=summary,
        default_summary=default_summary, fallback_summary=fallback_summary, scores=scores,
        skipped=skipped, tuning=tuning, hashes=hashes, universe_size=prices.shape[1],
    )
    calibration = {
        "stage": "dev",
        "q_hat": q_hat,
        "settings": asdict(settings.engine_settings()),
        "settings_sha256": settings_hash(settings, q_hat),
        "holdout_ids_sha256": holdout_ids_hash(library),
        "data_sha256": hashes,
        "dev": {k: v for k, v in summary.items()},
        "dev_gate_preview": gate(summary),
        "backtest": BacktestSummary(available=False).model_dump(),
    }
    # The engine serves only from calibration.json, which only an approved holdout run (C5)
    # writes. Dev output never makes the engine "available".
    (EVAL_DIR / "calibration_forecast_v1_dev.json").write_text(json.dumps(calibration, indent=1, sort_keys=True) + "\n")
    print(f"done in {time.time() - t0:.0f}s; settings {asdict(settings)}; q_hat {q_hat:.3f}")
    print(json.dumps({k: v for k, v in summary.items() if isinstance(v, dict)}, indent=1))
    return calibration


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["download-universe", "dev", "dev-v2", "crises", "diagnostics", "holdout"])
    args = parser.parse_args(argv)
    if args.command == "download-universe":
        manifest = download_universe()
        print(f"{len(manifest['tickers'])} tickers, {len(manifest['failed'])} failed: {manifest['failed']}")
        return 0
    if args.command == "dev":
        run_dev()
        return 0
    if args.command == "crises":
        from scenario.build_library import ASSETS_DIR, load_library

        rows = write_crises(load_library(ASSETS_DIR))
        print((EVAL_DIR / "crises.md").read_text())
        return 0
    if args.command == "dev-v2":
        run_dev_v2()
        return 0
    if args.command == "diagnostics":
        library, prices, cases, _, _ = _prepare([Split.DEV])
        _, sectors, _ = load_universe()
        dev = json.loads((EVAL_DIR / "calibration_forecast_v1_dev.json").read_text())
        settings = Settings(**{k: dev["settings"][k] for k in asdict(DEFAULT_SETTINGS)})
        table = diagnostics(library, prices, sectors, cases, settings)
        write_diagnostics(EVAL_DIR / "diagnostics.md", table, settings)
        print((EVAL_DIR / "diagnostics.md").read_text())
        return 0
    if os.getenv("SCENARIO_RUN_HOLDOUT") != "1":
        print("The holdout runs once, in C5, after the user writes 'run holdout' in STATUS.md. "
              "Set SCENARIO_RUN_HOLDOUT=1 only then.", file=sys.stderr)
        return 2
    run_holdout_v2()
    return 0


if __name__ == "__main__":
    sys.exit(main())
