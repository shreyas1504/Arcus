"""
Page 1 — Welcome / landing screen.
Called by app.py when st.session_state.page == "welcome".
"""

import streamlit as st

from config import BRAND_NAME, BRAND_TAGLINE, BRAND_ICON, COLORS
from src.ui.icons import icon


def render_welcome() -> None:
    # Hide sidebar on this page
    st.markdown(
        "<style>[data-testid='stSidebar']{display:none}</style>",
        unsafe_allow_html=True,
    )

    col_l, col_c, col_r = st.columns([1, 2, 1])

    with col_c:
        # ── Hero header ───────────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style='text-align:center; padding-top:60px;'>
                <div style='font-size:3.5rem; line-height:1;'>{BRAND_ICON}</div>
                <h1 style='font-size:3rem; margin:14px 0 6px 0;
                           background: linear-gradient(135deg, {COLORS['accent']}, {COLORS['success']});
                           -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
                    {BRAND_NAME}
                </h1>
                <p style='font-size:1.05rem; color:{COLORS['text_secondary']}; margin:0 0 36px 0;'>
                    {BRAND_TAGLINE}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Feature grid ──────────────────────────────────────────────────────
        features = [
            ("activity",     "Health Score",    "One composite score — how healthy is your portfolio?"),
            ("shield-alert", "Risk Metrics",    "Sharpe, VaR, Beta, Max Drawdown, Sortino — all in plain English"),
            ("bar-chart-2",  "Benchmark",       "Are you actually beating the S&P 500 on a risk-adjusted basis?"),
            ("git-branch",   "Correlation",     "Are your stocks truly diversified, or secretly the same bet?"),
            ("sliders",      "Optimal Weights", "The allocation that historically maximised risk-adjusted return"),
            ("shuffle",      "Monte Carlo",     "300 simulations of where your portfolio ends up in 1–3 years"),
        ]

        col_f1, col_f2 = st.columns(2)
        for i, (ico, title, desc) in enumerate(features):
            col = col_f1 if i % 2 == 0 else col_f2
            with col:
                st.markdown(
                    f"""
                    <div style='background:{COLORS['bg_card']}; border:1px solid {COLORS['border']};
                                border-radius:10px; padding:14px 16px; margin-bottom:10px;'>
                        <div style='font-size:0.88rem; font-weight:700; color:{COLORS['accent']};
                                    display:flex; align-items:center; gap:7px;'>
                            {icon(ico, size=15, color=COLORS['accent'])}{title}
                        </div>
                        <div style='font-size:0.78rem; color:{COLORS['text_secondary']};
                                    margin-top:5px;'>{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Get Started →", type="primary", width="stretch"):
            st.session_state.page = "setup"
            st.rerun()

        st.markdown(
            f"<div style='text-align:center; margin-top:16px; font-size:0.73rem; "
            f"color:{COLORS['text_secondary']};'>"
            "Powered by yfinance · Built with Streamlit · For educational purposes only.</div>",
            unsafe_allow_html=True,
        )
