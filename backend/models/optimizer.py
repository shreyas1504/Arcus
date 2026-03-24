# ── backend/models/optimizer.py ────────────────────────────────────────────
# Portfolio optimisation via SciPy. Enhanced with momentum-based ML signals.

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
from scipy.optimize import minimize  # type: ignore

from backend.config import TRADING_DAYS  # type: ignore


def optimize_sharpe(returns: pd.DataFrame) -> np.ndarray:
    """Classic Sharpe ratio maximisation (mean-variance, long-only)."""
    n = returns.shape[1]
    init_weights = np.full(n, 1.0 / n)
    bounds = tuple((0.0, 1.0) for _ in range(n))
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}

    def negative_sharpe(weights: np.ndarray) -> float:
        port_ret = np.dot(weights, returns.mean()) * TRADING_DAYS
        port_vol = np.sqrt(np.dot(weights.T, returns.cov().dot(weights)) * TRADING_DAYS)
        if port_vol == 0:
            return 0.0
        return -port_ret / port_vol

    result = minimize(
        negative_sharpe,
        init_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    return result.x


def optimize_momentum(returns: pd.DataFrame, momentum_window: int = 63) -> np.ndarray:
    """Momentum-enhanced optimization.

    Combines the Sharpe-maximising objective with a momentum signal:
    stocks with strong recent returns (last 63 trading days ≈ 3 months)
    get a bias toward higher allocation.

    This is a simplified version of the cross-sectional momentum strategy
    used by quantitative hedge funds.
    """
    n = returns.shape[1]
    init_weights = np.full(n, 1.0 / n)
    bounds = tuple((0.0, 1.0) for _ in range(n))
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}

    # Compute momentum scores (recent cumulative return)
    recent = returns.tail(min(momentum_window, len(returns)))
    cumulative_returns = (1 + recent).prod() - 1  # type: ignore[union-attr]
    # Normalize to [0, 1] range
    mom_min = cumulative_returns.min()
    mom_range = cumulative_returns.max() - mom_min
    if mom_range > 0:
        momentum_scores = ((cumulative_returns - mom_min) / mom_range).values
    else:
        momentum_scores = np.full(n, 0.5)

    # Blend: 60% Sharpe objective + 40% momentum tilt
    momentum_weight = 0.4

    def objective(weights: np.ndarray) -> float:
        port_ret = np.dot(weights, returns.mean()) * TRADING_DAYS
        port_vol = np.sqrt(np.dot(weights.T, returns.cov().dot(weights)) * TRADING_DAYS)
        if port_vol == 0:
            return 0.0
        sharpe = port_ret / port_vol
        momentum_bonus = np.dot(weights, momentum_scores)
        # Minimize negative combined score
        return -(sharpe * (1 - momentum_weight) + momentum_bonus * momentum_weight)

    result = minimize(
        objective,
        init_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    return result.x


def optimize_risk_parity(returns: pd.DataFrame) -> np.ndarray:
    """Risk parity: allocate so each asset contributes equal risk.

    This approach doesn't chase returns — instead it ensures no single
    stock dominates portfolio risk.
    """
    n = returns.shape[1]
    init_weights = np.full(n, 1.0 / n)
    bounds = tuple((0.01, 1.0) for _ in range(n))
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}

    cov = returns.cov().values * TRADING_DAYS

    def risk_parity_objective(weights: np.ndarray) -> float:
        port_vol = np.sqrt(weights.T @ cov @ weights)
        if port_vol == 0:
            return 0.0
        # Marginal risk contribution of each asset
        mrc = cov @ weights / port_vol
        rc = weights * mrc  # risk contribution
        target_rc = port_vol / n  # equal risk contribution target
        return float(np.sum((rc - target_rc) ** 2))

    result = minimize(
        risk_parity_objective,
        init_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    return result.x
