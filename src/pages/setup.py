"""
Page 2 — Portfolio setup / configuration form.
Called by app.py when st.session_state.page == "setup".
"""

import datetime

import pandas as pd
import streamlit as st

from config import BRAND_NAME, COLORS, DEMO_PORTFOLIOS, POPULAR_TICKERS
from src.data.fetcher import get_data_availability


def render_setup() -> None:
    # Hide sidebar on this page
    st.markdown(
        "<style>[data-testid='stSidebar']{display:none}</style>",
        unsafe_allow_html=True,
    )

    _today = datetime.date.today()
    col_l, col_c, col_r = st.columns([1, 2, 1])

    with col_c:
        st.markdown(
            f"<h2 style='color:{COLORS['text_primary']};'>Configure Your Portfolio</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='color:{COLORS['text_secondary']};'>"
            "Enter tickers or company names — or load a sample portfolio to see the platform in action."
            "</p>",
            unsafe_allow_html=True,
        )

        # ── Quick-load demo portfolios ─────────────────────────────────────────
        st.markdown(
            f"<div style='font-size:0.78rem; font-weight:600; text-transform:uppercase; "
            f"letter-spacing:0.08em; color:{COLORS['text_secondary']}; margin-bottom:8px;'>"
            "Quick Load</div>",
            unsafe_allow_html=True,
        )
        demo_cols = st.columns(len(DEMO_PORTFOLIOS))
        for i, (demo_name, demo_cfg) in enumerate(DEMO_PORTFOLIOS.items()):
            with demo_cols[i]:
                if st.button(demo_name, width="stretch"):
                    st.session_state.selected_tickers = demo_cfg["tickers"]
                    st.session_state.tickers_raw      = ""
                    st.session_state.start_date       = datetime.date.fromisoformat(demo_cfg["start"])
                    st.session_state.end_date         = datetime.date.fromisoformat(demo_cfg["end"])
                    st.session_state.target_date      = datetime.date.fromisoformat(demo_cfg["predict"])
                    st.session_state.investment       = demo_cfg["investment"]
                    st.session_state.page             = "results"
                    st.rerun()

        st.markdown("---")

        # ── Ticker selection ───────────────────────────────────────────────────
        st.markdown(
            f"<div style='font-size:0.9rem; font-weight:700; color:{COLORS['text_primary']}; "
            "margin-bottom:6px;'>Stocks to Track</div>",
            unsafe_allow_html=True,
        )

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
        )

        custom_list   = [t.strip() for t in custom_raw.split(",") if t.strip()]
        combined_list = list(dict.fromkeys(selected_tickers + custom_list))

        if combined_list:
            st.caption(f"Stocks queued: **{', '.join(combined_list)}**")

        # Check data availability button
        if combined_list:
            if st.button("Check data availability", use_container_width=False):
                with st.spinner("Fetching available date ranges…"):
                    avail = get_data_availability(combined_list)
                rows = []
                for ticker, info in avail.items():
                    if "error" in info:
                        rows.append({
                            "Ticker": ticker, "First date": "—", "Last date": "—",
                            "Trading days": f"Error: {info['error']}",
                        })
                    else:
                        rows.append({
                            "Ticker": ticker,
                            "First date": str(info["first"]),
                            "Last date":  str(info["last"]),
                            "Trading days": f"{info['days']:,}",
                        })
                st.dataframe(pd.DataFrame(rows).set_index("Ticker"), width="stretch")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Date range ────────────────────────────────────────────────────────
        st.markdown(
            f"<div style='font-size:0.9rem; font-weight:700; color:{COLORS['text_primary']}; "
            "margin-bottom:6px;'>Historical Date Range</div>",
            unsafe_allow_html=True,
        )
        st.caption("The history window used to calculate all risk metrics.")
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

        # ── Monte Carlo target date ────────────────────────────────────────────
        st.markdown(
            f"<div style='font-size:0.9rem; font-weight:700; color:{COLORS['text_primary']}; "
            "margin-bottom:6px;'>Monte Carlo Prediction Target</div>",
            unsafe_allow_html=True,
        )
        st.caption("Monte Carlo simulations will project your portfolio to this date.")
        target_date = st.date_input(
            "Predict until",
            value=st.session_state.target_date,
            min_value=_today + datetime.timedelta(days=1),
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Advanced settings ─────────────────────────────────────────────────
        with st.expander("Advanced settings"):
            investment = st.number_input(
                "Portfolio value ($)",
                min_value=1_000,
                max_value=10_000_000,
                value=st.session_state.investment,
                step=1_000,
            )
            n_simulations = st.slider(
                "Monte Carlo simulations",
                100, 1000,
                st.session_state.n_simulations,
                100,
            )

        st.markdown("<br>")
        st.markdown("---")

        # ── Navigation buttons ────────────────────────────────────────────────
        bcol1, bcol2 = st.columns([1, 2])
        with bcol1:
            if st.button("← Back", width="stretch"):
                st.session_state.page = "welcome"
                st.rerun()
        with bcol2:
            if st.button("Analyse Portfolio →", type="primary", width="stretch"):
                _err = None
                if not combined_list:
                    _err = "Please select or enter at least one ticker."
                elif start_date >= end_date:
                    _err = f"Start date ({start_date}) must be before end date ({end_date})."
                elif target_date <= _today:
                    _err = "Predict Until must be a future date."

                if _err:
                    st.error(_err)
                else:
                    st.session_state.tickers_raw      = custom_raw
                    st.session_state.selected_tickers = selected_tickers
                    st.session_state.start_date       = start_date
                    st.session_state.end_date         = end_date
                    st.session_state.target_date      = target_date
                    st.session_state.investment       = investment
                    st.session_state.n_simulations    = n_simulations
                    st.session_state.page             = "results"
                    st.rerun()
