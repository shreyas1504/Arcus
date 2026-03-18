"""
Page 3 — Results / analysis dashboard.
Called by app.py when st.session_state.page == "results".

Layout
------
render_results()
  ├── _load_data()            fetch prices, compute returns
  ├── _compute_metrics()      all portfolio statistics
  ├── _section_health()       Section 1 — Health Score
  ├── _section_prices()       Section 2 — Latest Prices + Price History
  ├── _section_risk()         Section 3 — Risk Metrics + Rolling Sharpe
  ├── _section_benchmark()    Section 4 — Benchmark vs S&P 500
  ├── _section_diversification() Section 5 — Correlation / Diversification
  ├── _section_optimizer()    Section 6 — Optimal Weights
  ├── _section_sectors()      Section 7 — Sector Concentration
  └── _section_montecarlo()   Section 8 — Monte Carlo Simulation
"""

import datetime

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from config import BRAND_NAME, BRAND_ICON, COLORS, ROLLING_WINDOW
from src.analytics.metrics import (
    annualized_return,
    annualized_volatility,
    benchmark_comparison,
    calculate_beta,
    calculate_var,
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
from src.data.fetcher import (
    calculate_returns,
    download_prices,
    get_latest_prices,
    get_sector_map,
    resolve_tickers,
    sector_weights,
)
from src.models.monte_carlo import simulate_individual, simulate_portfolio
from src.models.optimizer import optimize_sharpe
from src.ui.charts import (
    benchmark_overlay_chart,
    correlation_heatmap,
    monte_carlo_individual_chart,
    monte_carlo_portfolio_chart,
    optimal_weights_chart,
    price_chart,
    returns_chart,
    rolling_sharpe_chart,
    sector_pie_chart,
)
from src.ui.components import (
    benchmark_card,
    display_diversification_score,
    display_health_score,
    display_sector_flags,
    latest_price_table,
    metric_card,
    render_sidebar,
    section_header,
)


# ── Status helpers (used by risk metrics section) ─────────────────────────────
def _sharpe_status(s):  return "good" if s > 1   else ("warn" if s > 0   else "bad")
def _vol_status(v):     return "good" if v < 0.15 else ("warn" if v < 0.25 else "bad")
def _var_status(v):     return "good" if v > -0.02 else ("warn" if v > -0.04 else "bad")
def _beta_status(b):    return "good" if 0.5 < b < 1.2 else ("warn" if b < 1.5 else "bad")
def _mdd_status(m):     return "good" if m > -0.20 else ("warn" if m > -0.35 else "bad")
def _sortino_status(s): return "good" if s > 1   else ("warn" if s > 0   else "bad")


# ══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def _load_data(tickers_input, start_date, end_date):
    """
    Resolve tickers → download prices → compute returns.
    Returns (tickers, prices, returns) or calls st.stop() on fatal error.
    """
    # Resolve ticker symbols / company names
    with st.spinner("Resolving tickers…"):
        resolved = resolve_tickers(tickers_input)
    tickers = [r["symbol"] for r in resolved]

    if any(r["input"].upper() != r["symbol"] for r in resolved):
        with st.expander("Ticker resolution"):
            res_df = pd.DataFrame(resolved).rename(
                columns={"input": "You typed", "symbol": "Resolved", "name": "Company"}
            )
            st.dataframe(res_df.set_index("You typed"), width="stretch")

    # Download price data
    with st.spinner("Fetching market data…"):
        try:
            prices, fetch_errors = download_prices(tickers, start_date, end_date)
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            st.stop()

        if fetch_errors:
            with st.expander(f"Data issues ({len(fetch_errors)})", expanded=True):
                for ticker, reason in fetch_errors.items():
                    st.warning(f"**{ticker}**: {reason}")

        if prices.empty:
            st.error("No price data loaded. Check tickers and date range.")
            if st.button("← Go back"):
                st.session_state.page = "setup"
                st.rerun()
            st.stop()

        missing = [t for t in tickers if t not in prices.columns]
        if missing:
            st.warning(f"No data for: {', '.join(missing)}. Continuing with the rest.")
            tickers = [t for t in tickers if t in prices.columns]

        if len(prices) < 10:
            st.error(f"Only {len(prices)} trading days. Widen the date range.")
            st.stop()

        returns = calculate_returns(prices)

    tickers = [t for t in tickers if t in returns.columns]
    return tickers, prices, returns


# ══════════════════════════════════════════════════════════════════════════════
#  METRIC COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def _compute_metrics(tickers, prices, returns, start_date, end_date):
    """
    Compute all portfolio-level statistics.
    Returns a dict of named metrics ready for display sections.
    """
    eq_weights = np.array([1.0 / len(tickers)] * len(tickers))
    port_ret   = (returns * eq_weights).sum(axis=1)

    ann_ret  = annualized_return(returns, eq_weights)
    ann_vol  = annualized_volatility(returns, eq_weights)
    sharpe   = sharpe_ratio(port_ret)
    var      = calculate_var(port_ret)
    mdd      = max_drawdown(port_ret)
    sortino  = sortino_ratio(port_ret)
    health, components = portfolio_health_score(sharpe, var, ann_vol, eq_weights)

    # Beta — portfolio returns vs S&P 500 market returns
    try:
        mkt_raw   = yf.download("^GSPC", start=str(start_date), end=str(end_date),
                                 progress=False, auto_adjust=True)
        mkt_close = mkt_raw["Close"].squeeze()
        mkt_ret   = mkt_close.pct_change().dropna()
        mkt_ret.index   = pd.DatetimeIndex(mkt_ret.index).normalize()
        port_idx        = pd.DatetimeIndex(port_ret.index).normalize()
        port_norm       = port_ret.copy()
        port_norm.index = port_idx
        common = port_norm.index.intersection(mkt_ret.index)
        beta = calculate_beta(port_norm.loc[common], mkt_ret.loc[common]) if len(common) > 10 else 1.0
    except Exception:
        beta = 1.0

    div_score   = diversification_score(returns)
    roll_sharpe = rolling_sharpe(port_ret, window=ROLLING_WINDOW)

    return {
        "eq_weights":  eq_weights,
        "port_ret":    port_ret,
        "ann_ret":     ann_ret,
        "ann_vol":     ann_vol,
        "sharpe":      sharpe,
        "var":         var,
        "mdd":         mdd,
        "sortino":     sortino,
        "health":      health,
        "components":  components,
        "beta":        beta,
        "div_score":   div_score,
        "roll_sharpe": roll_sharpe,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

def _section_health(health, components):
    section_header(
        "Health Score", "health-score",
        "A composite 0–100 score measuring your portfolio's risk-return quality.",
        icon_name="activity",
    )
    display_health_score(health, components)


def _section_prices(tickers, prices, returns):
    st.markdown("---")
    section_header("Latest Prices", "latest-prices", icon_name="dollar-sign")
    with st.spinner("Fetching latest prices…"):
        latest = get_latest_prices(tickers)
    latest_price_table(latest)

    st.markdown("---")
    section_header(
        "Price History", "price-history",
        "Normalised to 100 for direct performance comparison.",
        icon_name="line-chart",
    )
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(price_chart(prices), width="stretch")
    with col2:
        st.plotly_chart(returns_chart(returns), width="stretch")


def _section_risk(metrics, tickers, start_date, end_date, investment):
    st.markdown("---")
    section_header(
        "Risk Metrics", "risk-metrics",
        f"Equal-weighted portfolio · {start_date} → {end_date}",
        icon_name="shield-alert",
    )

    ann_ret  = metrics["ann_ret"]
    ann_vol  = metrics["ann_vol"]
    sharpe   = metrics["sharpe"]
    var      = metrics["var"]
    mdd      = metrics["mdd"]
    sortino  = metrics["sortino"]
    beta     = metrics["beta"]
    roll_shp = metrics["roll_sharpe"]

    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card("Annualised Return",     f"{ann_ret:.2%}",
                    interpret_return(ann_ret, investment),
                    "good" if ann_ret > 0 else "bad",
                    icon_name="trending-up")
        metric_card("Sharpe Ratio",          f"{sharpe:.2f}",
                    interpret_sharpe(sharpe), _sharpe_status(sharpe),
                    icon_name="zap")
        metric_card("Max Drawdown",          f"{mdd:.1%}",
                    interpret_max_drawdown(mdd, investment), _mdd_status(mdd),
                    icon_name="arrow-down")

    with col2:
        metric_card("Annualised Volatility", f"{ann_vol:.2%}",
                    interpret_volatility(ann_vol, investment), _vol_status(ann_vol),
                    icon_name="waves")
        metric_card("Sortino Ratio",         f"{sortino:.2f}",
                    interpret_sortino(sortino), _sortino_status(sortino),
                    icon_name="scale")

    with col3:
        metric_card("Value at Risk (95%)",   f"{var:.2%}",
                    interpret_var(var, investment), _var_status(var),
                    icon_name="alert-triangle")
        metric_card("Beta",                  f"{beta:.2f}",
                    interpret_beta(beta), _beta_status(beta),
                    icon_name="gauge")

    st.markdown("<br>", unsafe_allow_html=True)
    valid_roll = roll_shp.dropna()
    if len(valid_roll) > 0:
        st.plotly_chart(rolling_sharpe_chart(valid_roll, ROLLING_WINDOW), width="stretch")


def _section_benchmark(port_ret, start_date, end_date, prices):
    st.markdown("---")
    section_header(
        "Benchmark Comparison", "benchmark",
        "How your portfolio stacks up against the S&P 500.",
        icon_name="bar-chart-2",
    )

    with st.spinner("Loading S&P 500 benchmark…"):
        bmark = benchmark_comparison(port_ret, start_date, end_date)

    if bmark:
        benchmark_card(bmark)
        st.markdown("<br>", unsafe_allow_html=True)
        st.plotly_chart(
            benchmark_overlay_chart(prices, bmark["bmark_returns"]),
            width="stretch",
        )
    else:
        st.warning("Could not load benchmark data. Check your internet connection.")


def _section_diversification(returns, div_score):
    st.markdown("---")
    section_header(
        "Diversification Analysis", "diversification",
        "Are your stocks truly independent, or secretly the same bet?",
        icon_name="git-branch",
    )

    # Find worst-correlated pair
    worst_pair = None
    if returns.shape[1] >= 2:
        corr        = returns.corr()
        mask        = ~np.eye(len(corr), dtype=bool)
        corr_nd     = corr.where(mask)
        pair        = corr_nd.stack().idxmax()
        worst_pair  = (pair[0], pair[1], corr_nd.stack().max())

    display_diversification_score(div_score, worst_pair)
    st.plotly_chart(correlation_heatmap(returns), width="stretch")


def _section_optimizer(tickers, returns):
    st.markdown("---")
    section_header(
        "Optimal Portfolio Weights", "optimal-weights",
        "The allocation that historically maximised risk-adjusted return (Sharpe).",
        icon_name="sliders",
    )

    with st.spinner("Optimising…"):
        opt_weights = optimize_sharpe(returns)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(optimal_weights_chart(tickers, opt_weights), width="stretch")
    with col2:
        st.markdown(
            f"<div style='font-size:0.82rem; font-weight:700; color:{COLORS['text_primary']}; "
            "margin-bottom:10px;'>Optimal Allocation</div>",
            unsafe_allow_html=True,
        )
        for ticker, w in zip(tickers, opt_weights):
            color = COLORS["accent"] if w > 0.20 else COLORS["text_secondary"]
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; "
                f"padding:6px 0; border-bottom:1px solid {COLORS['border']};'>"
                f"<span style='font-weight:600; color:{COLORS['text_primary']};'>{ticker}</span>"
                f"<span style='font-weight:700; color:{color};'>{w:.1%}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<div style='font-size:0.72rem; color:{COLORS['text_secondary']}; margin-top:10px;'>"
            "Historical optimisation only. Past allocation does not guarantee future performance."
            "</div>",
            unsafe_allow_html=True,
        )


def _section_sectors(tickers, eq_weights):
    st.markdown("---")
    section_header(
        "Sector Concentration", "sectors",
        "What percentage of your portfolio sits in each sector.",
        icon_name="pie-chart",
    )

    with st.spinner("Fetching sector data…"):
        s_map = get_sector_map(tickers)

    s_wts = sector_weights(tickers, eq_weights, s_map)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(sector_pie_chart(s_wts), width="stretch")
    with col2:
        st.markdown(
            f"<div style='font-size:0.82rem; font-weight:700; color:{COLORS['text_primary']}; "
            "margin-bottom:10px;'>Sector Breakdown</div>",
            unsafe_allow_html=True,
        )
        for sector, w in sorted(s_wts.items(), key=lambda x: -x[1]):
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; "
                f"padding:5px 0; border-bottom:1px solid {COLORS['border']};'>"
                f"<span style='color:{COLORS['text_secondary']};'>{sector}</span>"
                f"<span style='font-weight:700; color:{COLORS['text_primary']};'>{w:.1%}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)
        display_sector_flags(s_wts)


def _section_montecarlo(prices, tickers, n_simulations, n_days,
                         calendar_days, target_date, investment):
    st.markdown("---")
    section_header(
        "Monte Carlo Simulation", "simulation",
        f"Projecting your portfolio to {target_date.strftime('%d %b %Y')} "
        f"with {n_simulations:,} simulations.",
        icon_name="shuffle",
    )

    with st.spinner(f"Running {n_simulations:,} simulations…"):
        portfolio_sims  = simulate_portfolio(prices, n_simulations=n_simulations, n_days=n_days)
        individual_sims = simulate_individual(prices, n_simulations=n_simulations, n_days=n_days)

    # Percentile outcomes
    final_values = portfolio_sims[:, -1]
    p5   = float(np.percentile(final_values, 5))
    p50  = float(np.median(final_values))
    p95  = float(np.percentile(final_values, 95))

    last_price = float(prices.iloc[-1].mean())
    scale      = investment / last_price if last_price > 0 else 1.0
    inv_p5, inv_p50, inv_p95 = p5 * scale, p50 * scale, p95 * scale

    # Projection cards
    pc1, pc2, pc3 = st.columns(3)
    for col, label, val, color, note in [
        (pc1, "Pessimistic", inv_p5,  COLORS["danger"],
         "5th percentile — 1-in-20 chance of being below this"),
        (pc2, "Expected",    inv_p50, COLORS["success"],
         "Median — most likely outcome"),
        (pc3, "Optimistic",  inv_p95, COLORS["accent"],
         "95th percentile — 1-in-20 chance of exceeding this"),
    ]:
        with col:
            ret_pct = (val - investment) / investment
            sign    = "+" if ret_pct >= 0 else ""
            st.markdown(
                f"""
                <div style='text-align:center; padding:24px 16px; border-radius:12px;
                            background:{COLORS['bg_card']}; border:1px solid {color}44;'>
                    <div style='font-size:0.72rem; font-weight:700; text-transform:uppercase;
                                letter-spacing:0.1em; color:{color}; margin-bottom:8px;'>
                        {label}
                    </div>
                    <div style='font-size:2.2rem; font-weight:900; color:{color};'>
                        ${val:,.0f}
                    </div>
                    <div style='font-size:1rem; font-weight:700;
                                color:{color}; opacity:0.8; margin-top:4px;'>
                        {sign}{ret_pct:.1%}
                    </div>
                    <div style='font-size:0.72rem; color:{COLORS["text_secondary"]}; margin-top:8px;'>
                        {note}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    yrs     = calendar_days / 365
    ret_pct = (inv_p50 - investment) / investment
    st.info(
        f"Starting from \${investment:,.0f} today, there is a 90% probability your portfolio "
        f"will be worth between \${inv_p5:,.0f} and \${inv_p95:,.0f} "
        f"by {target_date.strftime('%d %b %Y')} ({yrs:.1f} years). "
        f"The most likely outcome is \${inv_p50:,.0f} "
        f"({'a gain' if ret_pct >= 0 else 'a loss'} of {abs(ret_pct):.1%}). "
        "Based on historical volatility — not a guarantee."
    )

    last_portfolio_price = float(prices.iloc[-1].mean())
    st.plotly_chart(
        monte_carlo_portfolio_chart(portfolio_sims, last_portfolio_price),
        width="stretch",
    )

    with st.expander("Individual Stock Simulations"):
        for ticker in tickers:
            st.plotly_chart(
                monte_carlo_individual_chart(ticker, individual_sims[ticker]),
                width="stretch",
            )


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def render_results() -> None:
    _today = datetime.date.today()

    # Pull state
    tickers_raw   = st.session_state.tickers_raw
    start_date    = st.session_state.start_date
    end_date      = st.session_state.end_date
    n_simulations = st.session_state.n_simulations
    target_date   = st.session_state.target_date
    investment    = st.session_state.investment

    calendar_days = (target_date - _today).days
    n_days        = max(30, int(calendar_days * 252 / 365))

    _selected     = st.session_state.get("selected_tickers", [])
    _custom       = [t.strip() for t in tickers_raw.split(",") if t.strip()]
    tickers_input = list(dict.fromkeys(_selected + _custom))

    # ── Load & validate data ──────────────────────────────────────────────────
    tickers, prices, returns = _load_data(tickers_input, start_date, end_date)

    # ── Compute all metrics ───────────────────────────────────────────────────
    metrics = _compute_metrics(tickers, prices, returns, start_date, end_date)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    render_sidebar(health=metrics["health"], tickers=tickers)

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:10px; padding-bottom:8px;">
            <span style="font-size:1.8rem; font-weight:900;
                         background:linear-gradient(135deg,{COLORS['accent']},{COLORS['success']});
                         -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                {BRAND_ICON} {BRAND_NAME}
            </span>
            <span style="font-size:0.82rem; color:{COLORS['text_secondary']};">
                {", ".join(tickers)} &nbsp;·&nbsp; {start_date} → {end_date}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Sections ──────────────────────────────────────────────────────────────
    _section_health(metrics["health"], metrics["components"])
    _section_prices(tickers, prices, returns)
    _section_risk(metrics, tickers, start_date, end_date, investment)
    _section_benchmark(metrics["port_ret"], start_date, end_date, prices)
    _section_diversification(returns, metrics["div_score"])
    _section_optimizer(tickers, returns)
    _section_sectors(tickers, metrics["eq_weights"])
    _section_montecarlo(prices, tickers, n_simulations, n_days,
                         calendar_days, target_date, investment)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center; font-size:0.72rem; color:{COLORS['text_secondary']};'>"
        f"Data sourced from Yahoo Finance via yfinance. "
        f"{BRAND_NAME} is for educational purposes only — not financial advice.</div>",
        unsafe_allow_html=True,
    )
