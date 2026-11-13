"""Per-holding factor model (PLAN.md 3a).

Factors per stock
-----------------
Every stock: FACTOR_SPY, its sector ETF (SECTOR_ETF[sector], skipped when it is
SPY itself), FACTOR_RATES and FACTOR_OIL. Semiconductor stocks also get FACTOR_SEMIS.
A ticker missing from `sectors` is treated as Sector.BROAD and flagged "sector_unknown".
If FACTOR_SEMIS has any NaN inside a semiconductor stock's window (SOXX starts in
2001-07), SOXX is dropped for that stock and the fit is flagged "semis_proxy"
(XLK then stands in for the semiconductor factor).

Rows used
---------
Dates d with  as_of - window_years years <= d < as_of  (never on or after as_of),
after dropping rows where the stock or any of its factors is NaN.
`stress_only=True` keeps only rows where FACTOR_SPY < STRESS_SPY_RETURN.

Estimator
---------
Ridge with an unpenalized intercept. Columns of X are standardized to unit variance
over the rows used, then  b_std = argmin ||y_c - X_std b||^2 + alpha * n_obs * ||b||^2
(y_c, X_std demeaned), and betas are mapped back to raw units: beta_j = b_std_j / sd_j.
alpha -> 0 gives ordinary least squares. A factor column with zero variance over the
rows used gets beta 0 and is left out of the solve.

Results
-------
n_obs < MIN_FIT_OBS: the ticker is omitted from the result.
n_obs < MIN_FACTOR_OBS: the fit is returned with flag "low_history".
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from scenario.enums import (
    FACTOR_NAMES,
    FACTOR_OIL,
    FACTOR_RATES,
    FACTOR_SEMIS,
    FACTOR_SPY,
    SECTOR_ETF,
    Sector,
)

STRESS_SPY_RETURN = -0.01
MIN_FACTOR_OBS = 126
MIN_FIT_OBS = 20


@dataclass(frozen=True)
class BetaFit:
    ticker: str
    sector: Sector
    betas: dict[str, float]  # factor name -> beta in raw units
    intercept: float  # daily, raw units
    r2: float
    n_obs: int
    flags: tuple[str, ...] = field(default_factory=tuple)  # "low_history", "sector_unknown", "semis_proxy"


def factors_for(sector: Sector) -> tuple[str, ...]:
    """The factor columns used for a stock in `sector`, in FACTOR_NAMES order."""
    wanted = {FACTOR_SPY, SECTOR_ETF[sector], FACTOR_RATES, FACTOR_OIL}
    if sector is Sector.SEMICONDUCTORS:
        wanted.add(FACTOR_SEMIS)
    return tuple(name for name in FACTOR_NAMES if name in wanted)


def fit_betas(
    stock_returns: pd.DataFrame,
    factor_returns: pd.DataFrame,
    as_of: date,
    *,
    sectors: Mapping[str, Sector],
    alpha: float = 1.0,
    stress_only: bool = False,
    window_years: int = 3,
) -> dict[str, BetaFit]:
    """Fit one BetaFit per column of `stock_returns` (daily simple returns, DatetimeIndex).

    `factor_returns` has DatetimeIndex and FACTOR_NAMES columns (see scenario.enums).
    """
    if alpha < 0:
        raise ValueError("alpha must be >= 0")
    end = pd.Timestamp(as_of)
    start = end - pd.DateOffset(years=window_years)
    stocks = _window(stock_returns, start, end)
    factors = _window(factor_returns, start, end)

    fits: dict[str, BetaFit] = {}
    for ticker in stocks.columns:
        flags: list[str] = []
        sector = sectors.get(ticker)
        if sector is None:
            sector = Sector.BROAD
            flags.append("sector_unknown")
        columns = list(factors_for(sector))

        frame = pd.concat([stocks[ticker].rename("__y__"), factors[columns]], axis=1, join="inner")
        frame = frame.dropna(subset=["__y__", *[c for c in columns if c != FACTOR_SEMIS]])
        if FACTOR_SEMIS in columns and frame[FACTOR_SEMIS].isna().any():
            columns.remove(FACTOR_SEMIS)
            flags.append("semis_proxy")
        frame = frame.dropna(subset=["__y__", *columns])
        if stress_only:
            frame = frame[frame[FACTOR_SPY] < STRESS_SPY_RETURN]

        n_obs = len(frame)
        if n_obs < MIN_FIT_OBS:
            continue
        if n_obs < MIN_FACTOR_OBS:
            flags.append("low_history")

        betas, intercept, r2 = _ridge(
            frame["__y__"].to_numpy(dtype=float), frame[columns].to_numpy(dtype=float), alpha
        )
        fits[ticker] = BetaFit(
            ticker=ticker,
            sector=sector,
            betas={name: float(beta) for name, beta in zip(columns, betas)},
            intercept=intercept,
            r2=r2,
            n_obs=n_obs,
            flags=tuple(flags),
        )
    return fits


def _window(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    index = pd.DatetimeIndex(frame.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    index = index.normalize()
    out = frame.copy()
    out.index = index
    return out[(index >= start) & (index < end)]


def _ridge(y: np.ndarray, x: np.ndarray, alpha: float) -> tuple[np.ndarray, float, float]:
    """Ridge on standardized columns with an unpenalized intercept (see module docstring)."""
    n = len(y)
    x_mean = x.mean(axis=0)
    y_mean = float(y.mean())
    sd = x.std(axis=0)
    live = sd > 1e-12
    betas = np.zeros(x.shape[1])
    if live.any():
        x_std = (x[:, live] - x_mean[live]) / sd[live]
        y_c = y - y_mean
        gram = x_std.T @ x_std + alpha * n * np.eye(int(live.sum()))
        b_std = np.linalg.solve(gram, x_std.T @ y_c)
        betas[live] = b_std / sd[live]
    intercept = y_mean - float(x_mean @ betas)
    residual = y - intercept - x @ betas
    total = float(((y - y_mean) ** 2).sum())
    r2 = 1.0 - float((residual**2).sum()) / total if total > 0 else 0.0
    return betas, intercept, r2


def estimate_return(fit: BetaFit, factor_moves: Mapping[str, float]) -> float:
    """Factor estimate of a stock's cumulative return: sum(beta_f * move_f), no intercept.

    `factor_moves` are cumulative factor moves over the same window (for example the
    21-day columns of a library event). Raises KeyError if a fitted factor is missing.
    """
    return float(sum(beta * float(factor_moves[name]) for name, beta in fit.betas.items()))
