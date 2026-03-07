# ── src/models/monte_carlo.py ──────────────────────────────────────────────
# Geometric Brownian Motion simulations. Logic is identical to the original;
# only the function signatures and module location changed.

import numpy as np
import pandas as pd


def simulate_portfolio(
    prices: pd.DataFrame,
    n_simulations: int = 300,
    n_days: int = 252,
) -> np.ndarray:
    """
    Simulate future portfolio price paths using GBM.

    Models the portfolio as a single asset with the average return and
    volatility across all constituent stocks.

    Returns:
        ndarray of shape (n_simulations, n_days)
    """
    daily_returns = prices.pct_change().dropna()
    last_price = float(prices.iloc[-1].mean())
    mu = float(daily_returns.mean().mean())
    sigma = float(daily_returns.std().mean())

    rng = np.random.default_rng()
    shocks = rng.standard_normal((n_simulations, n_days))

    # Vectorised GBM: each row is one path
    log_returns = (mu - 0.5 * sigma ** 2) + sigma * shocks
    paths = last_price * np.exp(np.cumsum(log_returns, axis=1))

    return paths


def simulate_individual(
    prices: pd.DataFrame,
    n_simulations: int = 300,
    n_days: int = 252,
) -> dict[str, np.ndarray]:
    """
    Simulate future price paths for each individual stock.

    Returns:
        {ticker: ndarray of shape (n_simulations, n_days)}
    """
    rng = np.random.default_rng()
    result = {}

    for ticker in prices.columns:
        series = prices[ticker]
        daily_ret = series.pct_change().dropna()
        last_price = float(series.iloc[-1])
        mu = float(daily_ret.mean())
        sigma = float(daily_ret.std())

        shocks = rng.standard_normal((n_simulations, n_days))
        log_returns = (mu - 0.5 * sigma ** 2) + sigma * shocks
        paths = last_price * np.exp(np.cumsum(log_returns, axis=1))
        result[ticker] = paths

    return result
