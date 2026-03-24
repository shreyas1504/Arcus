# ── backend/analytics/metrics.py ───────────────────────────────────────────
# Pure numeric functions. Ported from src/analytics/metrics.py.

import numpy as np
import pandas as pd
import yfinance as yf

from backend.config import RISK_FREE_RATE, VAR_CONFIDENCE_LEVEL, TRADING_DAYS, ROLLING_WINDOW, BENCHMARK_TICKER, BENCHMARK_NAME


# ── Core metrics ─────────────────────────────────────────────────────────────

def sharpe_ratio(portfolio_returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float:
    daily_rf = risk_free_rate / TRADING_DAYS
    excess = portfolio_returns - daily_rf
    if excess.std() == 0:
        return 0.0
    return float((excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS))


def calculate_beta(stock_returns, market_returns) -> float:
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
    return float(np.percentile(portfolio_returns, (1 - confidence_level) * 100))


def annualized_return(returns: pd.DataFrame, weights) -> float:
    weighted = (returns * weights).sum(axis=1)
    return float(weighted.mean() * TRADING_DAYS)


def annualized_volatility(returns: pd.DataFrame, weights) -> float:
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
    w = np.array(weights)
    sharpe_score = float(np.clip(sharpe / 2.0 * 40, 0, 40))
    var_score = float(np.clip((var_daily + 0.05) / 0.04 * 25, 0, 25))
    vol_score = float(np.clip((0.35 - vol_annual) / 0.25 * 20, 0, 20))
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


# ── Additional metrics ───────────────────────────────────────────────────────

def max_drawdown(portfolio_returns: pd.Series) -> float:
    cumulative = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    return float(drawdown.min())


def drawdown_series(portfolio_returns: pd.Series) -> pd.Series:
    cumulative = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative.cummax()
    return (cumulative - rolling_max) / rolling_max


def sortino_ratio(portfolio_returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float:
    daily_rf = risk_free_rate / TRADING_DAYS
    excess = portfolio_returns - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    return float((excess.mean() / downside.std()) * np.sqrt(TRADING_DAYS))


def rolling_sharpe(portfolio_returns: pd.Series,
                   window: int = ROLLING_WINDOW,
                   risk_free_rate: float = RISK_FREE_RATE) -> pd.Series:
    daily_rf = risk_free_rate / TRADING_DAYS
    excess = portfolio_returns - daily_rf
    roll_mean = excess.rolling(window).mean()
    roll_std  = excess.rolling(window).std()
    return (roll_mean / roll_std) * np.sqrt(TRADING_DAYS)


def benchmark_comparison(portfolio_returns: pd.Series,
                         start_date, end_date,
                         risk_free_rate: float = RISK_FREE_RATE) -> dict:
    try:
        from backend.data.fetcher import download_benchmark
        bmark_close = download_benchmark(BENCHMARK_TICKER, start_date, end_date)
        if bmark_close.empty:
            return {}

        bmark_ret = bmark_close.pct_change().dropna()

        port_idx  = pd.DatetimeIndex(portfolio_returns.index).normalize()
        bmark_idx = pd.DatetimeIndex(bmark_ret.index).normalize()

        port_norm  = portfolio_returns.copy()
        port_norm.index = port_idx
        bmark_norm = bmark_ret.copy()
        bmark_norm.index = bmark_idx

        common = port_norm.index.intersection(bmark_norm.index)
        if len(common) < 10:
            return {}

        p_ret = port_norm.loc[common]
        b_ret = bmark_norm.loc[common]

        p_ann  = float(p_ret.mean() * TRADING_DAYS)
        b_ann  = float(b_ret.mean() * TRADING_DAYS)
        p_vol  = float(p_ret.std() * np.sqrt(TRADING_DAYS))
        b_vol  = float(b_ret.std() * np.sqrt(TRADING_DAYS))
        p_shrp = sharpe_ratio(p_ret, risk_free_rate)
        b_shrp = sharpe_ratio(b_ret, risk_free_rate)
        alpha  = p_ann - b_ann

        return {
            "name":             BENCHMARK_NAME,
            "bmark_return":     b_ann,
            "bmark_sharpe":     b_shrp,
            "bmark_vol":        b_vol,
            "port_return":      p_ann,
            "port_sharpe":      p_shrp,
            "port_vol":         p_vol,
            "alpha":            alpha,
            "outperformed":     p_shrp > b_shrp,
        }
    except Exception:
        return {}


def diversification_score(returns: pd.DataFrame) -> float:
    if returns.shape[1] < 2:
        return 50.0
    corr = returns.corr().values
    n = corr.shape[0]
    mask = ~np.eye(n, dtype=bool)
    avg_corr = float(corr[mask].mean())
    score = (1 - avg_corr) / 2 * 100
    return float(np.clip(score, 0, 100))


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

def interpret_max_drawdown(mdd: float, investment: float = 10_000) -> str:
    dollar_loss = abs(mdd) * investment
    label = "severe" if mdd < -0.40 else ("significant" if mdd < -0.20 else "moderate")
    return (
        f"The worst historical peak-to-trough loss was {abs(mdd):.1%} ({label}). "
        f"On a ${investment:,.0f} portfolio that would have been a ${dollar_loss:,.0f} drawdown."
    )

def interpret_sortino(sortino: float) -> str:
    if sortino > 2:
        quality = "excellent — strong returns with limited downside"
    elif sortino > 1:
        quality = "good — downside risk is well-compensated"
    elif sortino > 0:
        quality = "below average — limited reward for the downside risk taken"
    else:
        quality = "poor — returns don't justify the downside volatility"
    return f"Sortino of {sortino:.2f} is {quality}."


# ── New Arcus V2 metrics ─────────────────────────────────────────────────────

def compute_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """Conditional Value at Risk (Expected Shortfall).
    Average loss in the worst (1 - confidence)% of days.
    """
    var_threshold = returns.quantile(1 - confidence)
    tail_losses = returns[returns <= var_threshold]
    return float(tail_losses.mean()) if len(tail_losses) > 0 else 0.0


def compute_alpha(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = RISK_FREE_RATE,
) -> float:
    """Jensen's Alpha — excess return above CAPM prediction."""
    beta = calculate_beta(portfolio_returns, benchmark_returns)
    port_ann = float(portfolio_returns.mean() * TRADING_DAYS)
    bench_ann = float(benchmark_returns.mean() * TRADING_DAYS)
    return float(port_ann - (risk_free_rate + beta * (bench_ann - risk_free_rate)))


def compute_information_ratio(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """Information Ratio = Active Return / Tracking Error."""
    active_returns = portfolio_returns - benchmark_returns
    if active_returns.std() == 0:
        return 0.0
    return float(
        (active_returns.mean() * TRADING_DAYS) / (active_returns.std() * (TRADING_DAYS ** 0.5))
    )


def compute_calmar_ratio(returns: pd.Series) -> float:
    """Calmar Ratio = Annualized Return / |Max Drawdown|."""
    ann_ret = float(returns.mean() * TRADING_DAYS)
    mdd = max_drawdown(returns)
    return float(ann_ret / abs(mdd)) if mdd != 0 else 0.0


def compute_correlation_matrix(returns_df: pd.DataFrame) -> dict:
    """Pairwise correlation matrix for all tickers."""
    corr = returns_df.corr().round(3)
    return {
        "tickers": list(corr.columns),
        "matrix": corr.values.tolist(),
    }


def compute_risk_contribution(returns_df: pd.DataFrame, weights: np.ndarray) -> dict:
    """Each ticker's marginal contribution to total portfolio risk."""
    cov = returns_df.cov().values * TRADING_DAYS
    w = np.array(weights, dtype=float)
    portfolio_var = float(w @ cov @ w)
    if portfolio_var == 0:
        return {t: 0.0 for t in returns_df.columns}
    marginal = cov @ w
    risk_contrib = w * marginal / portfolio_var
    return {
        str(ticker): round(float(rc), 6)
        for ticker, rc in zip(returns_df.columns, risk_contrib)
    }


def compute_valuation_metrics(tickers: list[str], weights: list[float]) -> dict:
    """Weighted average P/E and P/S ratios via yfinance Ticker.info."""
    pe_values: list[tuple[float, float]] = []
    ps_values: list[tuple[float, float]] = []
    for ticker, weight in zip(tickers, weights):
        try:
            info = yf.Ticker(ticker).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            ps = info.get("priceToSalesTrailing12Months")
            if pe:
                pe_values.append((float(pe), float(weight)))
            if ps:
                ps_values.append((float(ps), float(weight)))
        except Exception:
            pass
    total_pe_w = sum(w for _, w in pe_values)
    total_ps_w = sum(w for _, w in ps_values)
    weighted_pe = sum(pe * w for pe, w in pe_values) / total_pe_w if total_pe_w else None
    weighted_ps = sum(ps * w for ps, w in ps_values) / total_ps_w if total_ps_w else None
    return {"weighted_pe": round(weighted_pe, 2) if weighted_pe else None,
            "weighted_ps": round(weighted_ps, 2) if weighted_ps else None}
