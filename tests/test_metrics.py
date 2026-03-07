"""
Basic unit tests for src/analytics/metrics.py

Run with:
    python -m pytest tests/
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.metrics import (
    annualized_return,
    annualized_volatility,
    calculate_beta,
    calculate_var,
    portfolio_health_score,
    sharpe_ratio,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def flat_returns():
    """Zero returns every day — edge-case baseline."""
    return pd.Series(np.zeros(252))


@pytest.fixture
def positive_returns():
    """Steady 0.05% daily gain — should produce positive Sharpe."""
    return pd.Series(np.full(252, 0.0005))


@pytest.fixture
def sample_df():
    """Two-asset return DataFrame for multi-asset metrics."""
    rng = np.random.default_rng(42)
    data = rng.normal(0.0005, 0.01, size=(252, 2))
    return pd.DataFrame(data, columns=["AAPL", "MSFT"])


# ── sharpe_ratio ──────────────────────────────────────────────────────────────

def test_sharpe_zero_returns(flat_returns):
    """All-zero returns → Sharpe is 0 (no standard deviation)."""
    assert sharpe_ratio(flat_returns) == 0.0


def test_sharpe_positive_for_uptrend(positive_returns):
    """Consistently positive returns should produce a positive Sharpe."""
    assert sharpe_ratio(positive_returns) > 0


def test_sharpe_returns_float(positive_returns):
    assert isinstance(sharpe_ratio(positive_returns), float)


# ── calculate_beta ────────────────────────────────────────────────────────────

def test_beta_identical_series():
    """A stock identical to the market should have beta ≈ 1."""
    market = pd.Series(np.random.default_rng(0).normal(0, 0.01, 252))
    beta = calculate_beta(market, market)
    assert abs(beta - 1.0) < 1e-6


def test_beta_double_market():
    """A series that is exactly 2× the market should have beta ≈ 2."""
    rng = np.random.default_rng(1)
    market = pd.Series(rng.normal(0, 0.01, 252))
    stock = market * 2
    beta = calculate_beta(stock, market)
    assert abs(beta - 2.0) < 0.1


# ── calculate_var ─────────────────────────────────────────────────────────────

def test_var_is_negative(sample_df):
    """VaR on any realistic return series should be a negative number."""
    returns = sample_df.mean(axis=1)
    var = calculate_var(returns)
    assert var < 0


def test_var_in_plausible_range(sample_df):
    """95% VaR on daily returns should be between -20% and 0%."""
    returns = sample_df.mean(axis=1)
    var = calculate_var(returns)
    assert -0.20 < var < 0


# ── annualized_return / volatility ────────────────────────────────────────────

def test_annualized_return_equal_weights(sample_df):
    weights = [0.5, 0.5]
    result = annualized_return(sample_df, weights)
    assert isinstance(result, float)


def test_annualized_volatility_positive(sample_df):
    weights = [0.5, 0.5]
    vol = annualized_volatility(sample_df, weights)
    assert vol > 0


def test_annualized_volatility_single_asset():
    """Single-asset portfolio: annualised vol should equal std * sqrt(252)."""
    rng = np.random.default_rng(7)
    data = pd.DataFrame({"A": rng.normal(0, 0.01, 252)})
    weights = [1.0]
    vol = annualized_volatility(data, weights)
    expected = data["A"].std() * np.sqrt(252)
    assert abs(vol - expected) < 1e-6


# ── portfolio_health_score ────────────────────────────────────────────────────

def test_health_score_range():
    """Health score must always be in [0, 100]."""
    score, _ = portfolio_health_score(
        sharpe=1.0, var_daily=-0.02, vol_annual=0.15, weights=[0.5, 0.5]
    )
    assert 0 <= score <= 100


def test_health_score_components_sum():
    """Component scores must sum to the total."""
    score, components = portfolio_health_score(
        sharpe=1.5, var_daily=-0.015, vol_annual=0.12, weights=[0.33, 0.33, 0.34]
    )
    assert abs(sum(components.values()) - score) < 0.1


def test_health_score_perfect_portfolio():
    """Excellent metrics should produce a score above 70."""
    score, _ = portfolio_health_score(
        sharpe=2.5, var_daily=-0.005, vol_annual=0.08, weights=[0.25, 0.25, 0.25, 0.25]
    )
    assert score > 70


def test_health_score_poor_portfolio():
    """Poor metrics should produce a score below 40."""
    score, _ = portfolio_health_score(
        sharpe=-0.5, var_daily=-0.08, vol_annual=0.50, weights=[1.0]
    )
    assert score < 40
