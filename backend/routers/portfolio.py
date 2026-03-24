# ── backend/routers/portfolio.py ───────────────────────────────────────────
# pyre-ignore-all-errors
# REST endpoints for portfolio analytics.

import datetime

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
from fastapi import APIRouter, HTTPException  # type: ignore
from pydantic import BaseModel  # type: ignore

from backend.analytics.metrics import (  # type: ignore
    annualized_return,
    annualized_volatility,
    benchmark_comparison,
    calculate_beta,
    calculate_var,
    compute_alpha,
    compute_calmar_ratio,
    compute_correlation_matrix,
    compute_cvar,
    compute_information_ratio,
    compute_risk_contribution,
    compute_valuation_metrics,
    diversification_score,
    drawdown_series,
    interpret_beta,
    interpret_max_drawdown,
    interpret_return,
    interpret_sharpe,
    interpret_sortino,
    interpret_var,
    interpret_volatility,
    max_drawdown,
    portfolio_health_score,
    rolling_sharpe,
    sharpe_ratio,
    sortino_ratio,
)
from backend.data.fetcher import (  # type: ignore
    calculate_returns,
    download_prices,
    get_latest_prices,
    get_sector_map,
    sector_weights,
)
from backend.models.monte_carlo import simulate_individual, simulate_portfolio  # type: ignore
from backend.models.optimizer import optimize_sharpe  # type: ignore
from backend.config import ROLLING_WINDOW, DEMO_PORTFOLIOS, POPULAR_TICKERS  # type: ignore

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# ── Request / Response Models ─────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str
    investment: float = 10_000
    weights: list[float] | None = None


class MonteCarloRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str
    n_simulations: int = 300
    n_days: int = 252
    investment: float = 10_000


class OptimizeRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str


class SectorRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_data(tickers: list[str], start_date: str, end_date: str):
    prices, errors = download_prices(tickers, start_date, end_date)
    if prices.empty:
        raise HTTPException(status_code=400, detail="No price data loaded. Check tickers and date range.")
    tickers_valid = [t for t in tickers if t in prices.columns]
    if not tickers_valid:
        raise HTTPException(status_code=400, detail="None of the tickers returned data.")
    returns = calculate_returns(prices)
    tickers_valid = [t for t in tickers_valid if t in returns.columns]
    return tickers_valid, prices, returns, errors


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyze")
def analyze_portfolio(req: AnalyzeRequest):
    tickers, prices, returns, errors = _load_data(req.tickers, req.start_date, req.end_date)

    # Use custom weights if provided, otherwise equal weight
    if req.weights and len(req.weights) == len(tickers):
        w_arr = np.array(req.weights, dtype=float)
        w_arr = w_arr / w_arr.sum()  # normalize
    else:
        w_arr = np.array([1.0 / len(tickers)] * len(tickers))
    port_ret = (returns[tickers] * w_arr).sum(axis=1)

    ann_ret  = annualized_return(returns[tickers], w_arr)
    ann_vol  = annualized_volatility(returns[tickers], w_arr)
    shrp     = sharpe_ratio(port_ret)
    var      = calculate_var(port_ret)
    mdd      = max_drawdown(port_ret)
    sort     = sortino_ratio(port_ret)
    health, components = portfolio_health_score(shrp, var, ann_vol, w_arr)

    # CVaR
    cvar_95 = compute_cvar(port_ret, 0.95)

    # Calmar
    calmar = compute_calmar_ratio(port_ret)

    # Beta + Alpha + Information Ratio (need benchmark)
    beta = 1.0
    alpha_val = 0.0
    info_ratio = 0.0
    try:
        from backend.data.fetcher import download_benchmark  # type: ignore
        mkt_close = download_benchmark("^GSPC", req.start_date, req.end_date)
        if not mkt_close.empty:
            mkt_ret = mkt_close.pct_change().dropna()
            mkt_ret.index = pd.DatetimeIndex(mkt_ret.index).normalize()
            port_idx = pd.DatetimeIndex(port_ret.index).normalize()
            port_norm = port_ret.copy()
            port_norm.index = port_idx
            common = port_norm.index.intersection(mkt_ret.index)
            if len(common) > 10:
                beta = calculate_beta(port_norm.loc[common], mkt_ret.loc[common])
                alpha_val = compute_alpha(port_norm.loc[common], mkt_ret.loc[common])
                info_ratio = compute_information_ratio(port_norm.loc[common], mkt_ret.loc[common])
    except Exception:
        pass

    div_score = diversification_score(returns[tickers])

    # Correlation matrix
    corr_matrix = compute_correlation_matrix(returns[tickers])

    # Risk contribution
    risk_contrib = compute_risk_contribution(returns[tickers], w_arr)

    # Rolling Sharpe
    roll_shp = rolling_sharpe(port_ret, window=ROLLING_WINDOW).dropna()
    roll_sharpe_data = [
        {"date": d.isoformat(), "value": round(float(v), 4)}  # type: ignore[call-overload]
        for d, v in roll_shp.items() if not np.isnan(v)
    ]

    # Drawdown series
    dd = drawdown_series(port_ret)
    dd_data = [
        {"date": d.isoformat(), "value": round(float(v), 6)}  # type: ignore[call-overload]
        for d, v in dd.items()
    ]

    # Benchmark
    bmark = benchmark_comparison(port_ret, req.start_date, req.end_date)

    # Price history for chart
    norm_prices = prices[tickers] / prices[tickers].iloc[0] * 100
    price_history = {}
    for t in tickers:
        price_history[t] = [
            {"date": d.isoformat(), "value": round(float(v), 2)}  # type: ignore[call-overload]
            for d, v in norm_prices[t].items()
        ]

    # Latest prices
    latest = get_latest_prices(tickers)

    return {
        "tickers": tickers,
        "weights": w_arr.tolist(),
        "errors": errors,
        "latest_prices": latest,
        "price_history": price_history,
        "metrics": {
            "annualized_return": round(ann_ret, 6),
            "annualized_volatility": round(ann_vol, 6),
            "sharpe_ratio": round(shrp, 4),
            "value_at_risk": round(var, 6),
            "max_drawdown": round(mdd, 6),
            "sortino_ratio": round(sort, 4),
            "beta": round(beta, 4),  # type: ignore[call-overload]
            "cvar_95": round(cvar_95, 6),
            "alpha": round(alpha_val, 6),
            "information_ratio": round(info_ratio, 4),
            "calmar_ratio": round(calmar, 4),
            "health_score": health,
            "health_components": components,
            "diversification_score": round(div_score, 1),
        },
        "interpretations": {
            "return": interpret_return(ann_ret, req.investment),
            "volatility": interpret_volatility(ann_vol, req.investment),
            "sharpe": interpret_sharpe(shrp),
            "beta": interpret_beta(beta),
            "var": interpret_var(var, req.investment),
            "max_drawdown": interpret_max_drawdown(mdd, req.investment),
            "sortino": interpret_sortino(sort),
        },
        "rolling_sharpe": roll_sharpe_data,
        "drawdown": dd_data,
        "benchmark": bmark if bmark else None,
        "correlation_matrix": corr_matrix,
        "risk_contribution": risk_contrib,
    }


@router.post("/optimize")
def optimize_portfolio(req: OptimizeRequest):
    tickers, prices, returns, errors = _load_data(req.tickers, req.start_date, req.end_date)

    from backend.models.optimizer import optimize_momentum, optimize_risk_parity  # type: ignore

    sharpe_w = optimize_sharpe(returns[tickers])
    momentum_w = optimize_momentum(returns[tickers])
    risk_parity_w = optimize_risk_parity(returns[tickers])

    return {
        "optimal_weights": {t: round(float(w), 6) for t, w in zip(tickers, sharpe_w)},  # type: ignore[call-overload]
        "momentum_weights": {t: round(float(w), 6) for t, w in zip(tickers, momentum_w)},  # type: ignore[call-overload]
        "risk_parity_weights": {t: round(float(w), 6) for t, w in zip(tickers, risk_parity_w)},  # type: ignore[call-overload]
    }


@router.post("/monte-carlo")
def monte_carlo(req: MonteCarloRequest):
    tickers, prices, returns, errors = _load_data(req.tickers, req.start_date, req.end_date)

    portfolio_sims = simulate_portfolio(prices[tickers], n_simulations=req.n_simulations, n_days=req.n_days)

    final_values = portfolio_sims[:, -1]
    p5  = float(np.percentile(final_values, 5))
    p50 = float(np.median(final_values))
    p95 = float(np.percentile(final_values, 95))

    last_price = float(prices[tickers].iloc[-1].mean())
    scale = req.investment / last_price if last_price > 0 else 1.0

    # Sample paths for visualization (max 50 to keep payload reasonable)
    sample_count = min(50, req.n_simulations)
    sample_paths = portfolio_sims[:sample_count].tolist()

    return {
        "percentiles": {
            "p5":  round(p5 * scale, 2),  # type: ignore[call-overload]
            "p50": round(p50 * scale, 2),  # type: ignore[call-overload]
            "p95": round(p95 * scale, 2),  # type: ignore[call-overload]
        },
        "investment": req.investment,
        "n_simulations": req.n_simulations,
        "n_days": req.n_days,
        "sample_paths": sample_paths,
        "last_price": round(last_price, 2),  # type: ignore[call-overload]
        "scale": round(scale, 6),  # type: ignore[call-overload]
    }


@router.post("/sectors")
def portfolio_sectors(req: SectorRequest):
    tickers, prices, returns, errors = _load_data(req.tickers, req.start_date, req.end_date)
    eq_weights = [1.0 / len(tickers)] * len(tickers)
    s_map = get_sector_map(tickers)
    s_wts = sector_weights(tickers, eq_weights, s_map)
    return {"sectors": s_wts, "sector_map": s_map}


@router.post("/recommendations")
def get_recommendations(req: AnalyzeRequest):
    """Generate portfolio improvement recommendations based on metrics."""
    tickers, prices, returns, errors = _load_data(req.tickers, req.start_date, req.end_date)

    eq_weights = np.array([1.0 / len(tickers)] * len(tickers))
    port_ret = (returns[tickers] * eq_weights).sum(axis=1)

    ann_ret  = annualized_return(returns[tickers], eq_weights)
    ann_vol  = annualized_volatility(returns[tickers], eq_weights)
    shrp     = sharpe_ratio(port_ret)
    var      = calculate_var(port_ret)
    mdd      = max_drawdown(port_ret)
    sort     = sortino_ratio(port_ret)
    health, _ = portfolio_health_score(shrp, var, ann_vol, eq_weights)
    div_score = diversification_score(returns[tickers])

    # Sector analysis
    s_map = get_sector_map(tickers)
    s_wts = sector_weights(tickers, eq_weights.tolist(), s_map)

    # Optimal weights
    opt_w = optimize_sharpe(returns[tickers])

    recs: list[dict] = []

    # 1. Health score
    if health < 40:
        recs.append({"type": "critical", "title": "Portfolio Health Critical",
            "message": f"Your health score is {health}/100 (red zone). Consider reducing high-volatility positions and adding defensive assets like bonds or gold ETFs."})
    elif health < 70:
        recs.append({"type": "warning", "title": "Portfolio Health Moderate",
            "message": f"Health score of {health}/100 is in the yellow zone. Focus on improving your Sharpe ratio and reducing concentration risk."})

    # 2. Sharpe
    if shrp < 0:
        recs.append({"type": "critical", "title": "Negative Risk-Adjusted Return",
            "message": f"Sharpe ratio of {shrp:.2f} means you'd have earned more in a savings account. Consider rebalancing toward the optimal weights."})
    elif shrp < 1:
        recs.append({"type": "warning", "title": "Below-Average Risk-Adjusted Return",
            "message": f"Sharpe of {shrp:.2f} is below the 1.0 benchmark. The optimizer suggests shifting weight toward your strongest performers."})

    # 3. Diversification
    if div_score < 40:
        recs.append({"type": "warning", "title": "Low Diversification",
            "message": f"Score of {div_score:.0f}/100 means your stocks are highly correlated. Add assets from different sectors or include ETFs like GLD, TLT, or XLE."})

    # 4. Sector concentration
    for sector, weight in s_wts.items():
        if weight > 0.40 and sector != "Unknown":
            recs.append({"type": "warning", "title": f"Sector Concentration: {sector}",
                "message": f"{sector} represents {weight:.0%} of your portfolio (>40%). Consider diversifying into other sectors."})

    # 5. Max drawdown
    if mdd < -0.35:
        recs.append({"type": "critical", "title": "Severe Historical Drawdown",
            "message": f"Max drawdown of {abs(mdd):.1%} is severe. Consider adding defensive assets or setting stop-loss protections."})

    # 6. VaR
    dollar_var = abs(var) * req.investment
    if var < -0.03:
        recs.append({"type": "warning", "title": "High Daily Value at Risk",
            "message": f"On a bad day, you could lose ${dollar_var:,.0f} ({abs(var):.1%}). Consider reducing position sizes in your most volatile holdings."})

    # 7. Beta
    try:
        from backend.data.fetcher import download_benchmark  # type: ignore
        mkt_close = download_benchmark("^GSPC", req.start_date, req.end_date)
        if not mkt_close.empty:
            mkt_ret = mkt_close.pct_change().dropna()
            mkt_ret.index = pd.DatetimeIndex(mkt_ret.index).normalize()
            port_idx = pd.DatetimeIndex(port_ret.index).normalize()
            port_norm = port_ret.copy()
            port_norm.index = port_idx
            common = port_norm.index.intersection(mkt_ret.index)
            beta = calculate_beta(port_norm.loc[common], mkt_ret.loc[common]) if len(common) > 10 else 1.0
        else:
            beta = 1.0
    except Exception:
        beta = 1.0

    if beta > 1.3:
        recs.append({"type": "info", "title": "High Market Sensitivity",
            "message": f"Beta of {beta:.2f} means your portfolio amplifies market moves. In a 10% market drop, expect ~{beta*10:.0f}% loss. Consider adding low-beta stocks."})

    # 8. Optimal weight divergence
    max_deviation = max(abs(eq_weights - opt_w))
    if max_deviation > 0.15:
        top_stock = tickers[np.argmax(opt_w)]
        recs.append({"type": "info", "title": "Rebalancing Opportunity",
            "message": f"The optimizer suggests increasing {top_stock} to {opt_w[np.argmax(opt_w)]:.0%} (currently equal-weighted). Consider rebalancing toward optimal weights for better risk-adjusted returns."})

    # Always add a positive note if portfolio is healthy
    if health >= 70 and shrp > 1:
        recs.append({"type": "success", "title": "Strong Portfolio Performance",
            "message": f"Your portfolio scores {health}/100 with a Sharpe of {shrp:.2f}. You're being well-compensated for the risk you're taking. Stay the course and monitor for changes."})

    if not recs:
        recs.append({"type": "info", "title": "Portfolio Overview",
            "message": "Your portfolio metrics are within normal ranges. Continue monitoring and consider the optimal weights from the optimizer for potential improvements."})

    return {"recommendations": recs}


@router.get("/demo-portfolios")
async def demo_portfolios():
    return DEMO_PORTFOLIOS


@router.get("/popular-tickers")
async def popular_tickers():
    return POPULAR_TICKERS


# ── New Arcus V2 Endpoints ───────────────────────────────────────────────────

class EfficientFrontierRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str
    n_portfolios: int = 300


@router.post("/efficient-frontier")
def efficient_frontier(req: EfficientFrontierRequest):
    """Generate random portfolio weight combos for frontier visualization."""
    tickers, prices, returns, errors = _load_data(req.tickers, req.start_date, req.end_date)
    n = len(tickers)
    mean_returns = returns[tickers].mean() * 252
    cov_matrix = returns[tickers].cov() * 252

    frontier_points = []
    for _ in range(req.n_portfolios):
        w = np.random.dirichlet(np.ones(n))
        port_return = float(w @ mean_returns.values)
        port_vol = float(np.sqrt(w @ cov_matrix.values @ w))
        frontier_points.append({"risk": round(port_vol, 6), "return": round(port_return, 6)})

    # Current (equal weight)
    eq_w = np.array([1.0 / n] * n)
    curr_ret = float(eq_w @ mean_returns.values)
    curr_vol = float(np.sqrt(eq_w @ cov_matrix.values @ eq_w))

    # Optimal (max Sharpe)
    opt_w = optimize_sharpe(returns[tickers])
    opt_ret = float(opt_w @ mean_returns.values)
    opt_vol = float(np.sqrt(opt_w @ cov_matrix.values @ opt_w))

    return {
        "frontier_points": frontier_points,
        "current_portfolio": {"risk": round(curr_vol, 6), "return": round(curr_ret, 6)},
        "optimal_portfolio": {"risk": round(opt_vol, 6), "return": round(opt_ret, 6)},
    }


class StressTestRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str
    custom_drop: float | None = None


# Historical crash data: benchmark loss and approximate recovery days
_SCENARIOS = {
    "2008_financial_crisis": {"benchmark_loss": -0.57, "recovery_days": 480, "label": "2008 Financial Crisis"},
    "2020_covid_crash":      {"benchmark_loss": -0.34, "recovery_days": 90,  "label": "2020 COVID Crash"},
    "2022_rate_hike":        {"benchmark_loss": -0.25, "recovery_days": 200, "label": "2022 Rate Hike"},
    "2000_dot_com":          {"benchmark_loss": -0.49, "recovery_days": 720, "label": "2000 Dot-Com Bust"},
}

@router.post("/stress-test")
def stress_test(req: StressTestRequest):
    """Estimate portfolio loss under historical crash scenarios using beta."""
    tickers, prices, returns, errors = _load_data(req.tickers, req.start_date, req.end_date)
    eq_weights = np.array([1.0 / len(tickers)] * len(tickers))
    port_ret = (returns[tickers] * eq_weights).sum(axis=1)

    # Compute beta
    try:
        from backend.data.fetcher import download_benchmark  # type: ignore
        mkt_close = download_benchmark("^GSPC", req.start_date, req.end_date)
        if not mkt_close.empty:
            mkt_ret = mkt_close.pct_change().dropna()
            mkt_ret.index = pd.DatetimeIndex(mkt_ret.index).normalize()
            port_idx = pd.DatetimeIndex(port_ret.index).normalize()
            port_norm = port_ret.copy()
            port_norm.index = port_idx
            common = port_norm.index.intersection(mkt_ret.index)
            beta = calculate_beta(port_norm.loc[common], mkt_ret.loc[common]) if len(common) > 10 else 1.0
        else:
            beta = 1.0
    except Exception:
        beta = 1.0

    results = {}
    for key, scenario in _SCENARIOS.items():
        estimated_loss = round(beta * scenario["benchmark_loss"], 4)
        results[key] = {
            "label": scenario["label"],
            "benchmark_loss": scenario["benchmark_loss"],
            "estimated_loss": estimated_loss,
            "recovery_days": scenario["recovery_days"],
        }

    # Custom scenario
    if req.custom_drop is not None:
        custom_loss = round(beta * (-abs(req.custom_drop) / 100), 4)
        results["custom_crash"] = {
            "label": f"Custom -{abs(req.custom_drop):.0f}% Crash",
            "benchmark_loss": round(-abs(req.custom_drop) / 100, 4),
            "estimated_loss": custom_loss,
            "recovery_days": None,
        }

    return {"beta": round(beta, 4), "scenarios": results}


@router.get("/stock/{ticker}")
def get_stock_info(ticker: str):
    """Get fundamentals + 90-day price history for a single stock."""
    import yfinance as yf  # type: ignore
    ticker = ticker.upper()
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="3mo")
        price_history = [
            {"date": d.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
            for d, row in hist.iterrows()
        ] if not hist.empty else []

        return {
            "ticker": ticker,
            "info": {
                "name": info.get("shortName") or info.get("longName", ticker),
                "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "market_cap": info.get("marketCap"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "dividend_yield": info.get("dividendYield"),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "volume": info.get("volume"),
            },
            "price_history": price_history,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch data for {ticker}: {str(e)}")

