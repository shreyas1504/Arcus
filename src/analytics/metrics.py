# ── src/analytics/metrics.py ───────────────────────────────────────────────
# Pure numeric functions. No Streamlit, no plotting, no I/O.

import numpy as np
import pandas as pd

from config import RISK_FREE_RATE, VAR_CONFIDENCE_LEVEL, TRADING_DAYS


# ── Core metrics ─────────────────────────────────────────────────────────────

def sharpe_ratio(portfolio_returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float:
    """Annualised Sharpe ratio for a series of daily portfolio returns."""
    daily_rf = risk_free_rate / TRADING_DAYS
    excess = portfolio_returns - daily_rf
    if excess.std() == 0:
        return 0.0
    return float((excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS))


def calculate_beta(stock_returns, market_returns) -> float:
    """Beta of stock relative to market proxy."""
    # Flatten to 1D float arrays to handle DataFrames, Series, or arrays equally
    sr = np.asarray(stock_returns, dtype=float).flatten()
    mr = np.asarray(market_returns, dtype=float).flatten()
    if len(sr) != len(mr) or len(mr) < 2:
        return 1.0
    var_market = np.var(mr)
    if var_market == 0:
        return 1.0
    cov_matrix = np.cov(sr, mr)
    return float(cov_matrix[0][1] / var_market)


def calculate_var(portfolio_returns: pd.Series, confidence_level: float = VAR_CONFIDENCE_LEVEL) -> float:
    """Daily Value at Risk at the given confidence level (negative number)."""
    return float(np.percentile(portfolio_returns, (1 - confidence_level) * 100))


def annualized_return(returns: pd.DataFrame, weights) -> float:
    """Weighted annualised portfolio return."""
    weighted = (returns * weights).sum(axis=1)
    return float(weighted.mean() * TRADING_DAYS)


def annualized_volatility(returns: pd.DataFrame, weights) -> float:
    """Weighted annualised portfolio volatility."""
    w = np.array(weights)
    cov = returns.cov() * TRADING_DAYS
    return float(np.sqrt(w.T @ cov.values @ w))


# ── Portfolio Health Score ────────────────────────────────────────────────────

def portfolio_health_score(
    sharpe: float,
    var_daily: float,
    vol_annual: float,
    weights,
) -> tuple[float, dict]:
    """
    Composite health score from 0 to 100.

    Scoring breakdown:
      Sharpe ratio  → up to 40 pts  (2.0 = perfect)
      VaR (daily)   → up to 25 pts  (≥ -1% = perfect, ≤ -5% = 0)
      Volatility    → up to 20 pts  (≤ 10% annual = perfect, ≥ 35% = 0)
      Concentration → up to 15 pts  (equal weight = perfect, 100% in one = 0)

    Returns:
        (total_score, component_scores_dict)
    """
    w = np.array(weights)

    # Sharpe: 0 → 2 maps to 0 → 40 pts
    sharpe_score = float(np.clip(sharpe / 2.0 * 40, 0, 40))

    # VaR: -5% → -1% maps to 0 → 25 pts
    var_score = float(np.clip((var_daily + 0.05) / 0.04 * 25, 0, 25))

    # Volatility: 35% → 10% maps to 0 → 20 pts
    vol_score = float(np.clip((0.35 - vol_annual) / 0.25 * 20, 0, 20))

    # Concentration: max weight 100% → 25% maps to 0 → 15 pts
    max_w = float(w.max())
    conc_score = float(np.clip((1.0 - max_w) / 0.75 * 15, 0, 15))

    total = sharpe_score + var_score + vol_score + conc_score

    components = {
        "Sharpe (40 pts)": round(sharpe_score, 1),
        "VaR (25 pts)": round(var_score, 1),
        "Volatility (20 pts)": round(vol_score, 1),
        "Concentration (15 pts)": round(conc_score, 1),
    }
    return round(total, 1), components


# ── Plain-English interpretations ────────────────────────────────────────────

def interpret_return(ann_return: float, investment: float = 10_000) -> str:
    end_value = investment * (1 + ann_return)
    direction = "grew" if ann_return >= 0 else "shrank"
    return (
        f"Your portfolio {direction} at {ann_return:.1%} per year. "
        f"A ${investment:,.0f} investment would be worth ${end_value:,.0f} after one year."
    )


def interpret_volatility(vol: float, investment: float = 10_000) -> str:
    monthly_swing = investment * vol / np.sqrt(12)
    label = "low" if vol < 0.15 else ("moderate" if vol < 0.25 else "high")
    return (
        f"Annualised volatility of {vol:.1%} is {label}. "
        f"Expect monthly swings of roughly ±${monthly_swing:,.0f} on a ${investment:,.0f} portfolio."
    )


def interpret_sharpe(sharpe: float) -> str:
    if sharpe > 2:
        quality = "excellent — top-tier risk-adjusted performance"
    elif sharpe > 1:
        quality = "good — you're being rewarded well for the risk taken"
    elif sharpe > 0:
        quality = "below average — returns don't compensate well for risk"
    else:
        quality = "poor — you'd have done better in a risk-free account"
    return f"Sharpe of {sharpe:.2f} is {quality}."


def interpret_beta(beta: float) -> str:
    direction = "amplifies" if beta > 1 else ("dampens" if beta < 1 else "moves with")
    return (
        f"Beta of {beta:.2f} means your portfolio {direction} market moves. "
        f"If the S&P 500 drops 10%, expect your portfolio to move roughly {beta * -10:.1f}%."
    )


def interpret_var(var: float, investment: float = 10_000) -> str:
    dollar_loss = abs(var) * investment
    return (
        f"On a bad day (worst 5% of days), your portfolio could lose more than {abs(var):.2%} — "
        f"about ${dollar_loss:,.0f} on a ${investment:,.0f} portfolio."
    )
