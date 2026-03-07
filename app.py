"""
Portfolio Risk Tracker — main Streamlit entry point.

Run with:
    streamlit run app.py

UI flow (managed via st.session_state["page"]):
    "welcome"  →  "setup"  →  "results"
                   ↑__________↙  (Edit Portfolio button)
"""

import datetime
import numpy as np
import pandas as pd
import streamlit as st

from config import DEFAULT_DAYS, DEFAULT_SIMULATIONS, POPULAR_TICKERS
from src.analytics.metrics import (
    annualized_return,
    annualized_volatility,
    calculate_beta,
    calculate_var,
    interpret_beta,
    interpret_return,
    interpret_sharpe,
    interpret_var,
    interpret_volatility,
    portfolio_health_score,
    sharpe_ratio,
)
from src.data.fetcher import (
    calculate_returns,
    download_prices,
    get_data_availability,
    get_latest_prices,
    get_sector_map,
    resolve_tickers,
    sector_weights,
)
from src.models.monte_carlo import simulate_individual, simulate_portfolio
from src.models.optimizer import optimize_sharpe
from src.ui.charts import (
    monte_carlo_individual_chart,
    monte_carlo_portfolio_chart,
    optimal_weights_chart,
    price_chart,
    returns_chart,
    sector_pie_chart,
)
from src.ui.components import (
    display_health_score,
    display_sector_flags,
    latest_price_table,
    metric_card,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Risk Tracker",
    page_icon="📈",
    layout="wide",
)

# ── Session state defaults ────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "welcome"

_today = datetime.date.today()

if "tickers_raw" not in st.session_state:
    st.session_state.tickers_raw = ""   # no default — user must type their own
if "selected_tickers" not in st.session_state:
    st.session_state.selected_tickers = []  # tickers chosen via multiselect
if "start_date" not in st.session_state:
    st.session_state.start_date = _today.replace(year=_today.year - 3)  # default: 3 years ago
if "end_date" not in st.session_state:
    st.session_state.end_date = _today             # default: today
if "n_simulations" not in st.session_state:
    st.session_state.n_simulations = DEFAULT_SIMULATIONS
if "target_date" not in st.session_state:
    st.session_state.target_date = _today.replace(year=_today.year + 1)  # 1 year from today
if "investment" not in st.session_state:
    st.session_state.investment = 10_000


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — WELCOME
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "welcome":

    # Hide sidebar on welcome screen
    st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])

    with col_c:
        st.markdown(
            """
            <div style='text-align:center; padding-top:48px;'>
                <div style='font-size:4rem; line-height:1;'>📈</div>
                <h1 style='font-size:2.8rem; margin:12px 0 4px 0;'>Portfolio Risk Tracker</h1>
                <p style='font-size:1.1rem; color:#888; margin:0 0 28px 0;'>
                    Know <em>exactly</em> what risk you're taking — in plain English.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**What this tool does:**")
        st.markdown(
            "- Gives your portfolio a **Health Score from 0–100**\n"
            "- Calculates **Sharpe Ratio, VaR, Beta, Return & Volatility**\n"
            "- Finds the **optimal allocation** that maximises risk-adjusted return\n"
            "- Flags **sector concentration risk**\n"
            "- Runs **Monte Carlo simulations** to show your range of possible futures\n"
            "- Translates every number into **plain English + dollar amounts**"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Get Started →", type="primary", use_container_width=True):
            st.session_state.page = "setup"
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(
            "Powered by yfinance · Built with Streamlit · For educational purposes only."
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — SETUP
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "setup":

    st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 2, 1])

    with col_c:
        st.markdown("## Configure Your Portfolio")
        st.markdown(
            "Enter the stocks you want to analyse. You can use ticker symbols "
            "(**AAPL**) or company names (**nvidia**, **microsoft**)."
        )
        st.markdown("---")

        # ── Tickers ──────────────────────────────────────────────────────────
        st.markdown("#### Stocks to Track")

        selected_tickers = st.multiselect(
            "Choose from popular stocks",
            options=POPULAR_TICKERS,
            default=st.session_state.selected_tickers,
            placeholder="Search or pick tickers…",
            label_visibility="collapsed",
        )

        custom_raw = st.text_input(
            "Add more (company names or tickers, comma-separated)",
            value=st.session_state.tickers_raw,
            placeholder="e.g. nvidia, SHEL, berkshire",
            label_visibility="visible",
        )

        # Merge multiselect + custom text into one combined input string
        custom_list = [t.strip() for t in custom_raw.split(",") if t.strip()]
        combined_list = list(dict.fromkeys(selected_tickers + custom_list))  # deduplicate, preserve order
        tickers_raw = ", ".join(combined_list)

        if combined_list:
            st.caption(f"Stocks queued: **{', '.join(combined_list)}**")

        # ── Data availability checker ──────────────────────────────────────
        if combined_list:
            if st.button("Check data availability", use_container_width=False):
                with st.spinner("Fetching available date ranges…"):
                    avail = get_data_availability(combined_list)
                rows = []
                for ticker, info in avail.items():
                    if "error" in info:
                        rows.append({"Ticker": ticker, "First date": "—", "Last date": "—", "Trading days": f"Error: {info['error']}"})
                    else:
                        rows.append({
                            "Ticker": ticker,
                            "First date": str(info["first"]),
                            "Last date":  str(info["last"]),
                            "Trading days": f"{info['days']:,}",
                        })
                st.dataframe(
                    pd.DataFrame(rows).set_index("Ticker"),
                    use_container_width=True,
                )
                st.caption(
                    "Pick a **Start date** that falls within the First–Last range above. "
                    "Tickers with errors may be invalid or delisted."
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Historical date range ─────────────────────────────────────────────
        st.markdown("#### Historical Date Range")
        st.caption(
            "Set the history window used to calculate risk metrics. "
            "Move **Start date** back in time — the further back, the more data."
        )
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            start_date = st.date_input(
                "Start date",
                value=st.session_state.start_date,
                min_value=datetime.date(1900, 1, 1),
            )
        with dcol2:
            end_date = st.date_input(
                "End date",
                value=st.session_state.end_date,
                min_value=datetime.date(1900, 1, 1),
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Future prediction ─────────────────────────────────────────────────
        st.markdown("#### Future Price Prediction")
        st.caption(
            "Pick a future date. We'll run Monte Carlo simulations to project where "
            "your portfolio could be by then — with a best case, expected, and worst case."
        )
        target_date = st.date_input(
            "Predict until",
            value=st.session_state.target_date,
            min_value=_today + datetime.timedelta(days=1),   # must be in the future
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Advanced settings ─────────────────────────────────────────────────
        with st.expander("Advanced settings"):
            investment = st.number_input(
                "Portfolio value ($) — used to translate % metrics into dollars",
                min_value=1_000,
                max_value=10_000_000,
                value=st.session_state.investment,
                step=1_000,
            )
            n_simulations = st.slider(
                "Monte Carlo simulations", 100, 1000, st.session_state.n_simulations, 100
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")

        bcol1, bcol2 = st.columns([1, 2])
        with bcol1:
            if st.button("← Back", use_container_width=True):
                st.session_state.page = "welcome"
                st.rerun()
        with bcol2:
            if st.button("Analyse Portfolio →", type="primary", use_container_width=True):
                # Validate before proceeding
                _err = None
                if not combined_list:
                    _err = "Please select or enter at least one ticker or company name."
                elif start_date >= end_date:
                    _err = (
                        f"Start date ({start_date}) must be **before** end date ({end_date}). "
                        "Move the start date further back in time to capture historical data."
                    )
                elif target_date <= _today:
                    _err = "Predict Until date must be in the future."
                if _err:
                    st.error(_err)
                else:
                    st.session_state.tickers_raw = custom_raw
                    st.session_state.selected_tickers = selected_tickers
                    st.session_state.start_date = start_date
                    st.session_state.end_date = end_date
                    st.session_state.target_date = target_date
                    st.session_state.investment = investment
                    st.session_state.n_simulations = n_simulations
                    st.session_state.page = "results"
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — RESULTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "results":

    # Pull settings from session state
    tickers_raw    = st.session_state.tickers_raw
    start_date     = st.session_state.start_date
    end_date       = st.session_state.end_date
    n_simulations  = st.session_state.n_simulations
    target_date    = st.session_state.target_date
    investment     = st.session_state.investment

    # Convert target date to approximate trading days from today
    calendar_days = (target_date - _today).days
    n_days = max(30, int(calendar_days * 252 / 365))

    _selected  = st.session_state.get("selected_tickers", [])
    _custom    = [t.strip() for t in tickers_raw.split(",") if t.strip()]
    tickers_input = list(dict.fromkeys(_selected + _custom))

    # ── Top bar ───────────────────────────────────────────────────────────────
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown("# 📈 Portfolio Risk Tracker")
    with top_right:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Edit Portfolio", use_container_width=True):
            st.session_state.page = "setup"
            st.rerun()

    # ── Ticker resolution ─────────────────────────────────────────────────────
    with st.spinner("Resolving tickers…"):
        resolved = resolve_tickers(tickers_input)

    tickers = [r["symbol"] for r in resolved]

    if any(r["input"].upper() != r["symbol"] for r in resolved):
        st.info("Tickers resolved:")
        res_df = pd.DataFrame(resolved).rename(
            columns={"input": "You typed", "symbol": "Resolved symbol", "name": "Company"}
        )
        st.dataframe(res_df.set_index("You typed"), use_container_width=True)

    # ── Data fetch ────────────────────────────────────────────────────────────
    with st.spinner("Fetching market data…"):
        try:
            prices, fetch_errors = download_prices(tickers, start_date, end_date)
        except Exception as exc:
            st.error(f"Unexpected error fetching data: {exc}")
            st.stop()

        # Show per-ticker fetch errors so the user knows exactly what went wrong
        if fetch_errors:
            with st.expander(f"Data fetch details ({len(fetch_errors)} issue(s))", expanded=True):
                for ticker, reason in fetch_errors.items():
                    st.warning(f"**{ticker}**: {reason}")

        if prices.empty:
            st.error(
                f"No price data could be loaded for the selected date range "
                f"(**{start_date}** → **{end_date}**). "
                "Check that the tickers are valid and the date range covers trading days."
            )
            if st.button("← Go back and edit"):
                st.session_state.page = "setup"
                st.rerun()
            st.stop()

        missing = [t for t in tickers if t not in prices.columns]
        if missing:
            st.warning(
                f"No data for: {', '.join(missing)}. Continuing with the rest."
            )
            tickers = [t for t in tickers if t in prices.columns]

        if len(prices) < 10:
            st.error(
                f"Only {len(prices)} trading days returned ({start_date} → {end_date}). "
                "Widen the date range to at least a few weeks."
            )
            st.stop()

        returns = calculate_returns(prices)

    # ── Metrics ───────────────────────────────────────────────────────────────
    tickers = [t for t in tickers if t in returns.columns]
    eq_weights = np.array([1.0 / len(tickers)] * len(tickers))
    portfolio_returns = (returns * eq_weights).sum(axis=1)

    ann_ret = annualized_return(returns, eq_weights)
    ann_vol = annualized_volatility(returns, eq_weights)
    sharpe  = sharpe_ratio(portfolio_returns)
    beta    = calculate_beta(returns[tickers[0]], portfolio_returns)
    var     = calculate_var(portfolio_returns)
    health, components = portfolio_health_score(sharpe, var, ann_vol, eq_weights)

    # ── Hero: Health Score ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Portfolio Health Score")
    display_health_score(health, components)
    st.markdown("---")

    # ── Latest prices ─────────────────────────────────────────────────────────
    with st.spinner("Fetching latest prices…"):
        latest = get_latest_prices(tickers)

    st.subheader("Latest Stock Prices")
    latest_price_table(latest)

    # ── Price & returns charts ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Price History & Returns")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.plotly_chart(price_chart(prices), use_container_width=True)
    with col_chart2:
        st.plotly_chart(returns_chart(returns), use_container_width=True)

    # ── Portfolio metrics ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"Portfolio Metrics  ·  Equal-Weighted  ·  {start_date} → {end_date}")
    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card("Annualised Return",    f"{ann_ret:.2%}", interpret_return(ann_ret, investment))
        metric_card("Beta",                 f"{beta:.2f}",    interpret_beta(beta))
    with col2:
        metric_card("Annualised Volatility",f"{ann_vol:.2%}", interpret_volatility(ann_vol, investment))
        metric_card("Value at Risk (95%)",  f"{var:.2%}",     interpret_var(var, investment))
    with col3:
        metric_card("Sharpe Ratio",         f"{sharpe:.2f}",  interpret_sharpe(sharpe))

    # ── Portfolio optimisation ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Optimal Portfolio Weights (Sharpe-Maximised)")
    with st.spinner("Optimising…"):
        opt_weights = optimize_sharpe(returns)

    col_opt1, col_opt2 = st.columns([2, 1])
    with col_opt1:
        st.plotly_chart(optimal_weights_chart(tickers, opt_weights), use_container_width=True)
    with col_opt2:
        st.markdown("**Allocation**")
        for ticker, w in zip(tickers, opt_weights):
            st.write(f"**{ticker}**: {w:.2%}")
        st.caption(
            "_Weights that maximise historical Sharpe Ratio. "
            "Past optimisation does not guarantee future performance._"
        )

    # ── Sector concentration ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Sector Concentration")
    with st.spinner("Fetching sector data…"):
        s_map = get_sector_map(tickers)

    s_weights = sector_weights(tickers, opt_weights, s_map)
    col_sec1, col_sec2 = st.columns([2, 1])
    with col_sec1:
        st.plotly_chart(sector_pie_chart(s_weights), use_container_width=True)
    with col_sec2:
        st.markdown("**Sector Breakdown**")
        for sector, w in sorted(s_weights.items(), key=lambda x: -x[1]):
            st.write(f"**{sector}**: {w:.1%}")
        st.markdown("**Concentration Check**")
        display_sector_flags(s_weights)

    # ── Future Price Prediction ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"Future Price Prediction — by {target_date.strftime('%d %b %Y')}")
    st.caption(
        f"Based on {len(prices)} days of historical data, "
        f"running {n_simulations:,} simulations over ~{n_days} trading days "
        f"({calendar_days} calendar days)."
    )

    with st.spinner(f"Running {n_simulations} simulations…"):
        portfolio_sims = simulate_portfolio(prices, n_simulations=n_simulations, n_days=n_days)
        individual_sims = simulate_individual(prices, n_simulations=n_simulations, n_days=n_days)

    final_values = portfolio_sims[:, -1]
    p5  = float(np.percentile(final_values, 5))
    p50 = float(np.median(final_values))
    p95 = float(np.percentile(final_values, 95))

    # Scale to the user's actual investment amount
    last_price = float(prices.iloc[-1].mean())
    scale = investment / last_price if last_price > 0 else 1.0
    inv_p5  = p5  * scale
    inv_p50 = p50 * scale
    inv_p95 = p95 * scale

    # ── Projection cards ──────────────────────────────────────────────────────
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        st.markdown(
            f"""
            <div style='text-align:center; padding:20px 12px; border-radius:10px;
                        border: 2px solid #e74c3c;'>
                <div style='color:#e74c3c; font-size:0.85rem; font-weight:600;
                            text-transform:uppercase; letter-spacing:1px;'>
                    Pessimistic (5th %ile)
                </div>
                <div style='font-size:2rem; font-weight:800; color:#e74c3c; margin:8px 0;'>
                    ${inv_p5:,.0f}
                </div>
                <div style='font-size:0.8rem; color:#888;'>
                    1-in-20 chance of being below this
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pc2:
        st.markdown(
            f"""
            <div style='text-align:center; padding:20px 12px; border-radius:10px;
                        border: 2px solid #27ae60; background: rgba(39,174,96,0.05);'>
                <div style='color:#27ae60; font-size:0.85rem; font-weight:600;
                            text-transform:uppercase; letter-spacing:1px;'>
                    Expected (median)
                </div>
                <div style='font-size:2rem; font-weight:800; color:#27ae60; margin:8px 0;'>
                    ${inv_p50:,.0f}
                </div>
                <div style='font-size:0.8rem; color:#888;'>
                    Most likely outcome across all simulations
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pc3:
        st.markdown(
            f"""
            <div style='text-align:center; padding:20px 12px; border-radius:10px;
                        border: 2px solid #2980b9;'>
                <div style='color:#2980b9; font-size:0.85rem; font-weight:600;
                            text-transform:uppercase; letter-spacing:1px;'>
                    Optimistic (95th %ile)
                </div>
                <div style='font-size:2rem; font-weight:800; color:#2980b9; margin:8px 0;'>
                    ${inv_p95:,.0f}
                </div>
                <div style='font-size:0.8rem; color:#888;'>
                    1-in-20 chance of exceeding this
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Plain-English summary
    yrs = calendar_days / 365
    ret_pct = (inv_p50 - investment) / investment
    st.info(
        f"Starting from **${investment:,.0f}** today, there is a **90% probability** "
        f"your portfolio will be worth between **${inv_p5:,.0f}** and **${inv_p95:,.0f}** "
        f"by **{target_date.strftime('%d %b %Y')}** ({yrs:.1f} years). "
        f"The most likely outcome is **${inv_p50:,.0f}** "
        f"({'a gain' if ret_pct >= 0 else 'a loss'} of {abs(ret_pct):.1%}). "
        f"This is based on historical volatility and return — not a guarantee."
    )

    # ── Simulation chart ──────────────────────────────────────────────────────
    last_portfolio_price = float(prices.iloc[-1].mean())
    st.plotly_chart(
        monte_carlo_portfolio_chart(portfolio_sims, last_portfolio_price),
        use_container_width=True,
    )

    with st.expander("Individual Stock Simulations"):
        for ticker in tickers:
            st.plotly_chart(
                monte_carlo_individual_chart(ticker, individual_sims[ticker]),
                use_container_width=True,
            )

    st.markdown("---")
    st.caption(
        "Data sourced from Yahoo Finance via yfinance. "
        "For educational purposes only — not financial advice."
    )
