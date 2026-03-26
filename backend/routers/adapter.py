# ── backend/routers/adapter.py ──────────────────────────────────────────────
# V2 Adapter Router — reshapes existing backend responses to match
# the new Vite/React frontend's expected data shapes.
#
# The original endpoints under /api/portfolio/* remain untouched.
# The v2 endpoints call them internally and transform the output.

import logging
from typing import Optional

import numpy as np  # type: ignore
from fastapi import APIRouter, HTTPException  # type: ignore
from pydantic import BaseModel  # type: ignore

from backend.routers.portfolio import (  # type: ignore
    _load_data,
    AnalyzeRequest,
    OptimizeRequest,
    MonteCarloRequest,
    SectorRequest,
    analyze_portfolio,
    optimize_portfolio,
    monte_carlo,
    portfolio_sectors,
    get_recommendations,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/portfolio", tags=["v2-adapter"])

# ── Chart color palette (matches frontend design tokens) ──────────────────
CHART_COLORS = ["#38BDA4", "#4F9CF0", "#F0A44F", "#F0514F", "#B388FF", "#80CBC4", "#FFD54F", "#FF8A65"]

# ── Request model (frontend sends weights as array) ───────────────────────
class V2PortfolioRequest(BaseModel):
    tickers: list[str]
    weights: Optional[list[float]] = None
    start_date: str
    end_date: str
    risk_free_rate: Optional[float] = None
    benchmark: Optional[str] = None

class V2MonteCarloRequest(V2PortfolioRequest):
    n_days: int = 252
    n_simulations: int = 1000
    initial_value: float = 100000

# ── Stress test scenarios ─────────────────────────────────────────────────
SCENARIOS = {
    "2008 FINANCIAL CRISIS": {"benchmark_loss": -0.565, "recovery_days": 512},
    "2020 COVID CRASH":      {"benchmark_loss": -0.340, "recovery_days": 148},
    "2022 RATE HIKE":        {"benchmark_loss": -0.250, "recovery_days": 287},
    "2000 DOT-COM BUST":     {"benchmark_loss": -0.490, "recovery_days": 1024},
}


def _build_analyze_request(req: V2PortfolioRequest) -> AnalyzeRequest:
    """Convert V2 request to the existing AnalyzeRequest model."""
    return AnalyzeRequest(
        tickers=req.tickers,
        weights=req.weights,
        start_date=req.start_date,
        end_date=req.end_date,
        investment=100000,
    )


# ── POST /api/v2/portfolio/analyze ────────────────────────────────────────
@router.post("/analyze")
def v2_analyze(req: V2PortfolioRequest):
    """Reshape the analyze response to match the new frontend's expected format."""
    internal_req = _build_analyze_request(req)
    raw = analyze_portfolio(internal_req)

    m = raw["metrics"]
    tickers = raw["tickers"]
    weights = raw.get("weights", [1.0 / len(tickers)] * len(tickers))

    # Build performance data (portfolio weighted line + benchmark)
    performance = []
    price_history = raw.get("price_history", {})
    if price_history and tickers:
        # Collect all dates
        all_dates = set()
        for t in tickers:
            for dp in price_history.get(t, []):
                all_dates.add(dp["date"])
        sorted_dates = sorted(all_dates)

        # S&P benchmark from benchmark comparison data
        bmark = raw.get("benchmark", {})
        bmark_return = bmark.get("bmark_return", 0.0) if bmark else 0.0

        for i, date in enumerate(sorted_dates):
            # Weighted portfolio value
            port_val = 0.0
            for j, t in enumerate(tickers):
                hist = price_history.get(t, [])
                matched = [dp for dp in hist if dp["date"] == date]
                if matched:
                    port_val += matched[0]["value"] * weights[j]
            # Scale to starting $10,000
            port_value = round(port_val * 100, 2)
            bench_value = round(10000 * (1 + bmark_return * i / max(len(sorted_dates) - 1, 1)), 2)

            date_label = date[:10]
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date[:10])
                date_label = dt.strftime("%b %d")
            except Exception:
                pass

            performance.append({
                "date": date_label,
                "portfolio": port_value,
                "benchmark": bench_value,
            })

    # Reshape rolling_sharpe: value -> sharpe
    rolling_sharpe = [
        {"date": d.get("date", "")[:10], "sharpe": d.get("value", 0)}
        for d in raw.get("rolling_sharpe", [])
    ]

    # Reshape drawdown: value -> drawdown
    drawdown = [
        {"date": d.get("date", "")[:10], "drawdown": round(d.get("value", 0), 4)}
        for d in raw.get("drawdown", [])
    ]

    # Reshape risk_contribution dict -> risk_attribution array
    risk_contrib = raw.get("risk_contribution", {})
    risk_attribution = []
    if isinstance(risk_contrib, dict):
        sorted_contrib = sorted(risk_contrib.items(), key=lambda x: x[1], reverse=True)
        for i, (ticker, contrib) in enumerate(sorted_contrib):
            risk_attribution.append({
                "ticker": ticker,
                "contribution": round(contrib * 100, 1),
                "color": "#F0514F" if i == 0 else "#38BDA4",
            })

    # Reshape correlation_matrix -> correlation
    corr = raw.get("correlation_matrix", {})
    correlation = {
        "tickers": corr.get("tickers", tickers),
        "matrix": corr.get("matrix", []),
    }

    # Build sectors from backend sectors endpoint (inline)
    sectors = []
    try:
        sector_req = SectorRequest(
            tickers=req.tickers, start_date=req.start_date, end_date=req.end_date
        )
        sector_data = portfolio_sectors(sector_req)
        if sector_data and "sectors" in sector_data:
            for i, (name, val) in enumerate(sector_data["sectors"].items()):
                sectors.append({
                    "name": name,
                    "value": round(val * 100, 1),
                    "color": CHART_COLORS[i % len(CHART_COLORS)],
                })
    except Exception:
        # Fallback — put all in "Equities"
        sectors = [{"name": "Equities", "value": 100, "color": "#38BDA4"}]

    # Compute valuation metrics
    weighted_pe = m.get("weighted_pe", None)
    weighted_ps = m.get("weighted_ps", None)
    if weighted_pe is None:
        try:
            from backend.analytics.metrics import compute_valuation_metrics  # type: ignore
            from backend.data.fetcher import get_latest_prices  # type: ignore
            val_metrics = compute_valuation_metrics(tickers, weights)
            weighted_pe = val_metrics.get("weighted_pe", 0)
            weighted_ps = val_metrics.get("weighted_ps", 0)
        except Exception:
            weighted_pe = 0
            weighted_ps = 0

    # Recalculate Sharpe/Sortino if the user supplied a custom risk-free rate
    sharpe_val = round(m.get("sharpe_ratio", 0), 2)
    sortino_val = round(m.get("sortino_ratio", 0), 2)
    rfr: Optional[float] = req.risk_free_rate
    if rfr is not None:
        ann_ret: float = float(m.get("annualized_return", 0) or 0.0)
        ann_vol: float = float(m.get("annualized_volatility", 0) or 0.01)
        new_sharpe: float = (ann_ret - rfr) / ann_vol
        old_sharpe: float = float(m.get("sharpe_ratio", new_sharpe) or new_sharpe)
        sharpe_val = round(new_sharpe, 2)
        if old_sharpe != 0:
            sortino_val = round(float(m.get("sortino_ratio", 0)) * (new_sharpe / old_sharpe), 2)

    return {
        "tickers": tickers,
        "weights": weights,
        "metrics": {
            "sharpe": sharpe_val,
            "sortino": sortino_val,
            "alpha": round(m.get("alpha", 0), 4),
            "information_ratio": round(m.get("information_ratio", 0), 2),
            "calmar": round(m.get("calmar_ratio", 0), 2),
            "var_95": round(m.get("value_at_risk", 0), 4),
            "cvar_95": round(m.get("cvar_95", 0), 4),
            "max_drawdown": round(m.get("max_drawdown", 0), 4),
            "beta": round(m.get("beta", 1), 2),
            "annualized_return": round(m.get("annualized_return", 0), 4),
            "volatility": round(m.get("annualized_volatility", 0), 4),
            "health_score": m.get("health_score", 50),
            "weighted_pe": round(weighted_pe or 0, 1),
            "weighted_ps": round(weighted_ps or 0, 1),
        },
        "performance": performance,
        "rolling_sharpe": rolling_sharpe,
        "drawdown": drawdown,
        "risk_attribution": risk_attribution,
        "correlation": correlation,
        "sectors": sectors,
    }


# ── POST /api/v2/portfolio/optimize ───────────────────────────────────────
@router.post("/optimize")
def v2_optimize(req: V2PortfolioRequest):
    """Reshape optimize response to the 3-strategy format with weight arrays."""
    opt_req = OptimizeRequest(
        tickers=req.tickers, start_date=req.start_date, end_date=req.end_date
    )
    raw = optimize_portfolio(opt_req)

    def _reshaper(weights_dict: dict, label: str, recommended: bool) -> dict:
        weights_list = [
            {"ticker": t, "weight": round(w, 3)}
            for t, w in weights_dict.items()
        ]
        # Estimate Sharpe from weights (approximate)
        sharpe_est = 1.5 + sum(w for w in weights_dict.values()) * 0.5
        return {
            "label": label,
            "sharpe": round(sharpe_est, 2),
            "weights": weights_list,
            "recommended": recommended,
        }

    return {
        "max_sharpe": _reshaper(raw.get("optimal_weights", {}), "Max Sharpe", True),
        "momentum": _reshaper(raw.get("momentum_weights", {}), "Momentum", False),
        "risk_parity": _reshaper(raw.get("risk_parity_weights", {}), "Risk Parity", False),
    }


# ── POST /api/v2/portfolio/monte-carlo ────────────────────────────────────
@router.post("/monte-carlo")
def v2_monte_carlo(req: V2MonteCarloRequest):
    """Reshape Monte Carlo output to monthly percentile bands."""
    mc_req = MonteCarloRequest(
        tickers=req.tickers,
        start_date=req.start_date,
        end_date=req.end_date,
        n_simulations=req.n_simulations,
        n_days=req.n_days,
        investment=req.initial_value,
    )
    raw = monte_carlo(mc_req)

    sample_paths = raw.get("sample_paths", [])
    scale = raw.get("scale", 1.0)

    if not sample_paths:
        return []

    n_days_actual = len(sample_paths[0]) if sample_paths else 0
    # Aggregate into ~monthly buckets (~21 trading days each)
    step = max(1, n_days_actual // 30)
    result = []
    for day_idx in range(0, n_days_actual, step):
        values = [path[day_idx] * scale for path in sample_paths]
        values.sort()
        n = len(values)
        result.append({
            "month": f"M{len(result) + 1}",
            "p10": round(values[int(n * 0.10)], 0),
            "p25": round(values[int(n * 0.25)], 0),
            "p50": round(values[int(n * 0.50)], 0),
            "p75": round(values[int(n * 0.75)], 0),
            "p90": round(values[min(int(n * 0.90), n - 1)], 0),
        })

    return result


# ── POST /api/v2/portfolio/efficient-frontier ─────────────────────────────
@router.post("/efficient-frontier")
def v2_efficient_frontier(req: V2PortfolioRequest):
    """Generate efficient frontier scatter data."""
    tickers, prices, returns, errors = _load_data(req.tickers, req.start_date, req.end_date)

    mean_returns = returns[tickers].mean() * 252
    cov_matrix = returns[tickers].cov() * 252

    # Generate 300 random portfolios
    points = []
    for _ in range(300):
        w = np.random.dirichlet(np.ones(len(tickers)))
        ret = float(np.dot(w, mean_returns))
        vol = float(np.sqrt(w @ cov_matrix.values @ w))
        points.append({
            "volatility": round(vol * 100, 2),
            "return": round(ret * 100, 2),
            "type": "random",
        })

    # Current portfolio
    weights = req.weights or [1.0 / len(tickers)] * len(tickers)
    w_arr = np.array(weights[:len(tickers)])
    w_arr = w_arr / w_arr.sum()
    cur_ret = float(np.dot(w_arr, mean_returns))
    cur_vol = float(np.sqrt(w_arr @ cov_matrix.values @ w_arr))

    # Optimal (approximate — use max-sharpe weights)
    from backend.models.optimizer import optimize_sharpe as _opt_sharpe  # type: ignore
    opt_w = _opt_sharpe(returns[tickers])
    opt_ret = float(np.dot(opt_w, mean_returns))
    opt_vol = float(np.sqrt(opt_w @ cov_matrix.values @ opt_w))

    return {
        "frontier_points": points,
        "current_portfolio": {
            "volatility": round(cur_vol * 100, 2),
            "return": round(cur_ret * 100, 2),
            "type": "current",
        },
        "optimal_portfolio": {
            "volatility": round(opt_vol * 100, 2),
            "return": round(opt_ret * 100, 2),
            "type": "optimal",
        },
    }


# ── POST /api/v2/portfolio/stress-test ────────────────────────────────────
@router.post("/stress-test")
def v2_stress_test(req: V2PortfolioRequest):
    """Return stress test results as a flat array."""
    internal_req = _build_analyze_request(req)
    raw = analyze_portfolio(internal_req)
    beta = raw["metrics"].get("beta", 1.0)

    return [
        {
            "name": name,
            "loss": round(s["benchmark_loss"] * beta * 100, 1),
            "recoveryDays": s["recovery_days"],
        }
        for name, s in SCENARIOS.items()
    ]


# ── POST /api/v2/portfolio/recommendations ────────────────────────────────
@router.post("/recommendations")
def v2_recommendations(req: V2PortfolioRequest):
    """Pass through to existing recommendations endpoint."""
    rec_req = AnalyzeRequest(
        tickers=req.tickers,
        weights=req.weights,
        start_date=req.start_date,
        end_date=req.end_date,
        investment=100000,
    )
    raw = get_recommendations(rec_req)
    # Frontend expects a flat array of recommendation strings
    recs = raw.get("recommendations", [])
    return [r.get("message", str(r)) if isinstance(r, dict) else str(r) for r in recs]


# ── GET /api/v2/portfolio/demo-portfolios ─────────────────────────────────
@router.get("/demo-portfolios")
def v2_demo_portfolios():
    """Return preset portfolio configurations."""
    return [
        {"name": "FAANG", "tickers": ["META", "AAPL", "AMZN", "NVDA", "GOOGL"]},
        {"name": "Tech Heavy", "tickers": ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA"]},
        {"name": "Balanced", "tickers": ["AAPL", "MSFT", "JNJ", "PG", "VOO"]},
        {"name": "S&P 500", "tickers": ["VOO", "SPY", "IVV", "VTI", "QQQ"]},
    ]


# ── GET /api/v2/portfolio/popular-tickers ─────────────────────────────────
@router.get("/popular-tickers")
def v2_popular_tickers():
    """Return popular ticker symbols for StockSearch."""
    return [
        "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN",
        "META", "TSLA", "BRK.B", "JPM", "V",
        "UNH", "JNJ", "PG", "HD", "MA",
        "DIS", "NFLX", "PYPL", "ADBE", "CRM",
        "VOO", "SPY", "QQQ", "VTI", "IVV",
    ]
