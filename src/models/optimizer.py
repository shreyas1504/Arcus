# ── src/models/optimizer.py ────────────────────────────────────────────────
# Portfolio optimisation via SciPy. Logic identical to the original.

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from config import TRADING_DAYS


def optimize_sharpe(returns: pd.DataFrame) -> np.ndarray:
    """
    Find portfolio weights that maximise the Sharpe ratio.

    Constraints:
      - weights sum to 1
      - each weight in [0, 1]  (long-only)

    Returns:
        ndarray of optimal weights, same length as returns.columns
    """
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
