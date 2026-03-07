"""
Basic unit tests for src/models/monte_carlo.py

Run with:
    python -m pytest tests/
"""

import numpy as np
import pandas as pd
import pytest

from src.models.monte_carlo import simulate_individual, simulate_portfolio


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_prices():
    """Synthetic price DataFrame with two tickers."""
    rng = np.random.default_rng(42)
    n = 500
    aapl = 150 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, n)))
    msft = 300 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n)))
    return pd.DataFrame({"AAPL": aapl, "MSFT": msft})


# ── simulate_portfolio ────────────────────────────────────────────────────────

def test_portfolio_output_shape(sample_prices):
    sims = simulate_portfolio(sample_prices, n_simulations=50, n_days=30)
    assert sims.shape == (50, 30)


def test_portfolio_all_positive(sample_prices):
    """GBM paths should never produce negative prices."""
    sims = simulate_portfolio(sample_prices, n_simulations=100, n_days=60)
    assert (sims > 0).all()


def test_portfolio_first_value_near_last_price(sample_prices):
    """
    The first simulated value should be in the same ballpark as the last observed price.
    Allow a ±50% band to accommodate daily volatility drift.
    """
    last_price = float(sample_prices.iloc[-1].mean())
    sims = simulate_portfolio(sample_prices, n_simulations=200, n_days=1)
    median_first = float(np.median(sims[:, 0]))
    assert last_price * 0.5 < median_first < last_price * 1.5


def test_portfolio_different_seeds_differ(sample_prices):
    """Two runs should produce different paths (non-deterministic)."""
    sims1 = simulate_portfolio(sample_prices, n_simulations=10, n_days=10)
    sims2 = simulate_portfolio(sample_prices, n_simulations=10, n_days=10)
    assert not np.array_equal(sims1, sims2)


# ── simulate_individual ───────────────────────────────────────────────────────

def test_individual_returns_dict(sample_prices):
    result = simulate_individual(sample_prices, n_simulations=30, n_days=20)
    assert isinstance(result, dict)
    assert set(result.keys()) == set(sample_prices.columns)


def test_individual_shapes(sample_prices):
    result = simulate_individual(sample_prices, n_simulations=50, n_days=40)
    for ticker, sims in result.items():
        assert sims.shape == (50, 40), f"Wrong shape for {ticker}: {sims.shape}"


def test_individual_all_positive(sample_prices):
    result = simulate_individual(sample_prices, n_simulations=100, n_days=30)
    for ticker, sims in result.items():
        assert (sims > 0).all(), f"Negative prices in {ticker} simulation"


def test_individual_starts_near_last_price(sample_prices):
    """Median of first simulated day should be close to the last observed price."""
    result = simulate_individual(sample_prices, n_simulations=200, n_days=1)
    for ticker, sims in result.items():
        last_price = float(sample_prices[ticker].iloc[-1])
        median_first = float(np.median(sims[:, 0]))
        assert last_price * 0.5 < median_first < last_price * 1.5, (
            f"{ticker}: last={last_price:.2f}, median_first={median_first:.2f}"
        )
