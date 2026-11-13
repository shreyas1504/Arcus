"""Per-holding factor model (PLAN.md 3a). Contract stub: implemented in C2.

Factors per stock
-----------------
Every stock: FACTOR_SPY, its sector ETF (SECTOR_ETF[sector], skipped when it is
SPY itself), FACTOR_RATES and FACTOR_OIL. Semiconductor stocks also get FACTOR_SEMIS.
A ticker missing from `sectors` is treated as Sector.BROAD and flagged "sector_unknown".

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
alpha -> 0 gives ordinary least squares.

Results
-------
n_obs < MIN_FIT_OBS: the ticker is omitted from the result.
n_obs < MIN_FACTOR_OBS: the fit is returned with flag "low_history".
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from scenario.enums import Sector

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
    raise NotImplementedError


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
    raise NotImplementedError


def estimate_return(fit: BetaFit, factor_moves: Mapping[str, float]) -> float:
    """Factor estimate of a stock's cumulative return: sum(beta_f * move_f), no intercept.

    `factor_moves` are cumulative factor moves over the same window (for example the
    21-day columns of a library event). Raises KeyError if a fitted factor is missing.
    """
    raise NotImplementedError
