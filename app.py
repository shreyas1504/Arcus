
"""
QuantView — main Streamlit entry point.

Run with:
    streamlit run app.py

UI flow (managed via st.session_state["page"]):
    "welcome"  →  "setup"  →  "results"
                   ↑__________↙  (Edit Portfolio button in sidebar)

Page modules:
    src/pages/welcome.py   — landing screen
    src/pages/setup.py     — portfolio configuration form
    src/pages/results.py   — full analysis dashboard (9 sections)
"""

import datetime

import streamlit as st  # type: ignore

from config import BRAND_NAME, BRAND_ICON, DEFAULT_SIMULATIONS  # type: ignore
from src.ui.components import inject_global_css  # type: ignore
from src.pages.welcome import render_welcome  # type: ignore
from src.pages.setup import render_setup  # type: ignore
from src.pages.results import render_results  # type: ignore

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=BRAND_NAME,
    page_icon=BRAND_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_global_css()

# ── Session state defaults ────────────────────────────────────────────────────
_today = datetime.date.today()

if "page"             not in st.session_state: st.session_state.page             = "welcome"
if "tickers_raw"      not in st.session_state: st.session_state.tickers_raw      = ""
if "selected_tickers" not in st.session_state: st.session_state.selected_tickers = []
if "start_date"       not in st.session_state: st.session_state.start_date       = _today.replace(year=_today.year - 3)
if "end_date"         not in st.session_state: st.session_state.end_date         = _today
if "n_simulations"    not in st.session_state: st.session_state.n_simulations    = DEFAULT_SIMULATIONS
if "target_date"      not in st.session_state: st.session_state.target_date      = _today.replace(year=_today.year + 1)
if "investment"       not in st.session_state: st.session_state.investment       = 10_000

# ── Router ────────────────────────────────────────────────────────────────────
page = st.session_state.page

if page == "welcome":
    render_welcome()
elif page == "setup":
    render_setup()
elif page == "results":
    render_results()
