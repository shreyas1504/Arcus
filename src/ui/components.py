# ── src/ui/components.py ───────────────────────────────────────────────────
# Reusable Streamlit UI building blocks.

import streamlit as st
import pandas as pd

from config import (
    HEALTH_RED_MAX, HEALTH_YELLOW_MAX,
    SECTOR_CONCENTRATION_THRESHOLD,
    COLORS, BRAND_NAME, BRAND_TAGLINE, BRAND_ICON,
)
from src.ui.icons import icon


# ── Global CSS injection ──────────────────────────────────────────────────────

def inject_global_css() -> None:
    """Inject QuantView brand styles into the Streamlit app."""
    st.markdown(
        f"""
        <style>
        /* ── Base ── */
        .stApp {{
            background-color: {COLORS['bg_primary']};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {COLORS['bg_card']} !important;
            border-right: 1px solid {COLORS['border']};
        }}

        /* ── Typography ── */
        h1, h2, h3, h4 {{
            color: {COLORS['text_primary']} !important;
            font-weight: 700 !important;
        }}
        p, li, span, label {{
            color: {COLORS['text_secondary']};
        }}

        /* ── Metric cards ── */
        .qv-metric-card {{
            background: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 20px 22px;
            margin-bottom: 14px;
            transition: border-color 0.2s;
        }}
        .qv-metric-card:hover {{
            border-color: {COLORS['accent']};
        }}
        .qv-metric-label {{
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: {COLORS['text_secondary']};
            margin-bottom: 6px;
        }}
        .qv-metric-value {{
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.1;
            color: {COLORS['text_primary']};
        }}
        .qv-metric-sub {{
            font-size: 0.78rem;
            color: {COLORS['text_secondary']};
            margin-top: 8px;
            line-height: 1.4;
        }}
        .qv-metric-badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-top: 8px;
        }}

        /* ── Section divider ── */
        .qv-section-header {{
            font-size: 1.1rem;
            font-weight: 700;
            color: {COLORS['text_primary']};
            padding: 6px 0 12px 0;
            border-bottom: 1px solid {COLORS['border']};
            margin-bottom: 18px;
        }}

        /* ── Benchmark card ── */
        .qv-bench-card {{
            background: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        .qv-bench-title {{
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {COLORS['text_secondary']};
            margin-bottom: 8px;
        }}
        .qv-bench-value {{
            font-size: 1.6rem;
            font-weight: 800;
            color: {COLORS['text_primary']};
        }}
        .qv-bench-sub {{
            font-size: 0.76rem;
            color: {COLORS['text_secondary']};
            margin-top: 4px;
        }}

        /* ── Sidebar nav links ── */
        .qv-nav-link {{
            display: block;
            padding: 8px 12px;
            border-radius: 8px;
            color: {COLORS['text_secondary']};
            font-size: 0.88rem;
            font-weight: 500;
            text-decoration: none;
            margin-bottom: 2px;
            transition: background 0.15s, color 0.15s;
        }}
        .qv-nav-link:hover {{
            background: {COLORS['accent_soft']};
            color: {COLORS['accent']};
        }}

        /* ── Streamlit native overrides ── */
        div[data-testid="stMetricValue"] {{
            font-size: 1.8rem !important;
            color: {COLORS['text_primary']} !important;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {COLORS['text_secondary']} !important;
        }}
        .stButton > button {{
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}
        .stButton > button[kind="primary"] {{
            background: {COLORS['accent']} !important;
            border: none !important;
        }}
        div[data-testid="stExpander"] {{
            background: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(health: float | None = None, tickers: list | None = None) -> None:
    """Render the persistent QuantView sidebar with nav links."""
    with st.sidebar:
        # Brand
        st.markdown(
            f"""
            <div style="padding: 8px 0 24px 0;">
                <div style="font-size:1.6rem; font-weight:900;
                            color:{COLORS['text_primary']}; letter-spacing:-0.5px;">
                    {BRAND_ICON} {BRAND_NAME}
                </div>
                <div style="font-size:0.72rem; color:{COLORS['text_secondary']};
                            margin-top:2px;">
                    {BRAND_TAGLINE}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Portfolio summary chip
        if tickers:
            st.markdown(
                f"""
                <div style="background:{COLORS['bg_card']}; border:1px solid {COLORS['border']};
                            border-radius:8px; padding:10px 12px; margin-bottom:20px;">
                    <div style="font-size:0.72rem; color:{COLORS['text_secondary']};
                                text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;
                                display:flex; align-items:center; gap:5px;">
                        {icon("layers", size=11, color=COLORS['text_secondary'])} Portfolio
                    </div>
                    <div style="font-size:0.88rem; color:{COLORS['text_primary']}; font-weight:600;">
                        {" · ".join(tickers)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Health score mini badge
        if health is not None:
            color = health_score_color(health)
            label = health_score_label(health)
            st.markdown(
                f"""
                <div style="background:{COLORS['bg_card']}; border:1px solid {color}33;
                            border-radius:8px; padding:12px; margin-bottom:20px; text-align:center;">
                    <div style="margin-bottom:4px;">
                        {icon("heart-pulse", size=20, color=color)}
                    </div>
                    <div style="font-size:2rem; font-weight:900; color:{color};">
                        {health:.0f}
                    </div>
                    <div style="font-size:0.75rem; color:{color}; font-weight:600;
                                text-transform:uppercase; letter-spacing:0.05em;">
                        {label}
                    </div>
                    <div style="font-size:0.7rem; color:{COLORS['text_secondary']}; margin-top:2px;">
                        Health Score / 100
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Navigation
        nav_links = [
            ("health-score",    "activity",     "Health Score"),
            ("latest-prices",   "dollar-sign",  "Latest Prices"),
            ("price-history",   "line-chart",   "Price History"),
            ("risk-metrics",    "shield-alert", "Risk Metrics"),
            ("benchmark",       "bar-chart-2",  "Benchmark"),
            ("diversification", "git-branch",   "Diversification"),
            ("optimal-weights", "sliders",      "Optimal Weights"),
            ("sectors",         "pie-chart",    "Sector Concentration"),
            ("simulation",      "shuffle",      "Monte Carlo"),
        ]
        nav_items = "".join(
            f'<a href="#{anchor}" class="qv-nav-link" style="display:flex; align-items:center; gap:8px;">'
            f'{icon(ico, size=14, color="currentColor")}'
            f'<span>{label}</span></a>'
            for anchor, ico, label in nav_links
        )
        st.markdown(
            f"""
            <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.1em;
                        color:{COLORS['text_secondary']}; margin-bottom:8px; font-weight:600;">
                Navigate
            </div>
            {nav_items}
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Edit portfolio button
        if st.button(f"✎  Edit Portfolio", width="stretch"):
            st.session_state.page = "setup"
            st.rerun()

        st.markdown(
            f"""
            <div style="text-align:center; margin-top:12px;
                        font-size:0.68rem; color:{COLORS['text_secondary']};">
                For educational purposes only.<br>Not financial advice.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Health Score ──────────────────────────────────────────────────────────────

def health_score_color(score: float) -> str:
    if score < HEALTH_RED_MAX:
        return COLORS["danger"]
    elif score < HEALTH_YELLOW_MAX:
        return COLORS["warning"]
    return COLORS["success"]


def health_score_label(score: float) -> str:
    if score < HEALTH_RED_MAX:
        return "Needs Attention"
    elif score < HEALTH_YELLOW_MAX:
        return "Fair"
    return "Healthy"


def display_health_score(score: float, components: dict) -> None:
    color = health_score_color(score)
    label = health_score_label(score)

    st.markdown(
        f"""
        <div style="text-align:center; padding:32px 0 16px 0;">
            <div style="font-size:5.5rem; font-weight:900; color:{color};
                        line-height:1; letter-spacing:-2px;">
                {score:.0f}
            </div>
            <div style="font-size:1.2rem; color:{color}; font-weight:700;
                        margin-top:6px; text-transform:uppercase; letter-spacing:0.1em;">
                {label}
            </div>
            <div style="font-size:0.85rem; color:{COLORS['text_secondary']}; margin-top:4px;">
                Portfolio Health Score &nbsp;/&nbsp; 100
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Score breakdown"):
        for component, pts in components.items():
            max_pts = int(component.split("(")[1].replace(" pts)", ""))
            pct = pts / max_pts
            bar_color = health_score_color(pct * 100)
            col_l, col_r = st.columns([3, 1])
            with col_l:
                st.markdown(f"<span style='color:{COLORS['text_primary']};font-weight:600;'>{component}</span>", unsafe_allow_html=True)
                st.progress(pct)
            with col_r:
                st.markdown(
                    f"<div style='text-align:right; font-size:1.2rem; font-weight:800; color:{bar_color}; padding-top:4px;'>{pts}/{max_pts}</div>",
                    unsafe_allow_html=True,
                )


# ── Metric card ───────────────────────────────────────────────────────────────

def metric_card(label: str, value: str, interpretation: str,
                status: str = "neutral", icon_name: str = "") -> None:
    """
    Professional metric card with colour-coded left border.
    status: "good" | "warn" | "bad" | "neutral"
    """
    border_color = {
        "good":    COLORS["success"],
        "warn":    COLORS["warning"],
        "bad":     COLORS["danger"],
        "neutral": COLORS["accent"],
    }.get(status, COLORS["accent"])

    badge_bg = {
        "good":    COLORS["success_soft"],
        "warn":    COLORS["warning_soft"],
        "bad":     COLORS["danger_soft"],
        "neutral": COLORS["accent_soft"],
    }.get(status, COLORS["accent_soft"])

    badge_text = {
        "good": "Good", "warn": "Caution", "bad": "Risk", "neutral": "",
    }.get(status, "")

    badge_html = (
        f"<span style='background:{badge_bg}; color:{border_color}; "
        f"padding:2px 10px; border-radius:20px; font-size:0.7rem; "
        f"font-weight:700; text-transform:uppercase; letter-spacing:0.05em;'>"
        f"{badge_text}</span>"
        if badge_text else ""
    )

    icon_html = (
        f'<span style="margin-right:6px; opacity:0.7;">'
        f'{icon(icon_name, size=13, color=COLORS["text_secondary"])}</span>'
        if icon_name else ""
    )

    st.markdown(
        f"""
        <div class="qv-metric-card" style="border-left: 3px solid {border_color};">
            <div class="qv-metric-label" style="display:flex; align-items:center;">
                {icon_html}{label}
            </div>
            <div class="qv-metric-value" style="color:{border_color};">{value}</div>
            {badge_html}
            <div class="qv-metric-sub">{interpretation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Benchmark card ────────────────────────────────────────────────────────────

def benchmark_card(bmark_data: dict) -> None:
    """Side-by-side portfolio vs S&P 500 comparison."""
    if not bmark_data:
        st.warning("Could not load benchmark data.")
        return

    p_ret   = bmark_data["port_return"]
    b_ret   = bmark_data["bmark_return"]
    p_shrp  = bmark_data["port_sharpe"]
    b_shrp  = bmark_data["bmark_sharpe"]
    p_vol   = bmark_data["port_vol"]
    b_vol   = bmark_data["bmark_vol"]
    alpha   = bmark_data["alpha"]
    name    = bmark_data["name"]
    won     = bmark_data["outperformed"]

    alpha_color = COLORS["success"] if alpha >= 0 else COLORS["danger"]
    alpha_sign  = "+" if alpha >= 0 else ""

    c1, c2, c3 = st.columns([5, 1, 5])

    with c1:
        st.markdown(
            f"""
            <div class="qv-bench-card" style="border-color:{COLORS['accent']}44;">
                <div class="qv-bench-title" style="color:{COLORS['accent']};">
                    Your Portfolio
                </div>
                <div class="qv-bench-value">{p_ret:.1%}</div>
                <div class="qv-bench-sub">Annual Return</div>
                <div style="margin-top:12px; display:flex; justify-content:space-around;">
                    <div>
                        <div style="font-size:1.1rem; font-weight:800;
                                    color:{COLORS['text_primary']};">{p_shrp:.2f}</div>
                        <div style="font-size:0.7rem; color:{COLORS['text_secondary']};">Sharpe</div>
                    </div>
                    <div>
                        <div style="font-size:1.1rem; font-weight:800;
                                    color:{COLORS['text_primary']};">{p_vol:.1%}</div>
                        <div style="font-size:0.7rem; color:{COLORS['text_secondary']};">Volatility</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; justify-content:center;
                        height:100%; padding-top:40px;">
                <div style="font-size:1.4rem; font-weight:900;
                            color:{COLORS['text_secondary']};">vs</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="qv-bench-card" style="border-color:{COLORS['text_secondary']}44;">
                <div class="qv-bench-title">{name}</div>
                <div class="qv-bench-value">{b_ret:.1%}</div>
                <div class="qv-bench-sub">Annual Return</div>
                <div style="margin-top:12px; display:flex; justify-content:space-around;">
                    <div>
                        <div style="font-size:1.1rem; font-weight:800;
                                    color:{COLORS['text_primary']};">{b_shrp:.2f}</div>
                        <div style="font-size:0.7rem; color:{COLORS['text_secondary']};">Sharpe</div>
                    </div>
                    <div>
                        <div style="font-size:1.1rem; font-weight:800;
                                    color:{COLORS['text_primary']};">{b_vol:.1%}</div>
                        <div style="font-size:0.7rem; color:{COLORS['text_secondary']};">Volatility</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Alpha summary
    verdict = "outperformed" if won else "underperformed"
    verdict_color = COLORS["success"] if won else COLORS["danger"]
    st.markdown(
        f"""
        <div style="text-align:center; margin-top:14px; padding:12px;
                    background:{COLORS['bg_card']}; border-radius:8px;
                    border:1px solid {COLORS['border']};">
            <span style="font-size:1.1rem; font-weight:800; color:{alpha_color};">
                Alpha: {alpha_sign}{alpha:.1%}
            </span>
            &nbsp;&nbsp;
            <span style="font-size:0.85rem; color:{verdict_color};">
                Your portfolio <b>{verdict}</b> the {name} on risk-adjusted basis
                (Sharpe {p_shrp:.2f} vs {b_shrp:.2f})
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Diversification score ─────────────────────────────────────────────────────

def display_diversification_score(score: float, worst_pair: tuple | None = None) -> None:
    """Display diversification score with plain-English verdict."""
    if score >= 65:
        color, label, desc = (
            COLORS["success"], "Well Diversified",
            "Your stocks move relatively independently — genuine risk reduction."
        )
    elif score >= 40:
        color, label, desc = (
            COLORS["warning"], "Moderately Diversified",
            "Some independent movement, but correlated pockets exist."
        )
    else:
        color, label, desc = (
            COLORS["danger"], "Poorly Diversified",
            "Most of your stocks move together — you may be taking concentrated risk."
        )

    st.markdown(
        f"""
        <div style="background:{COLORS['bg_card']}; border:1px solid {color}44;
                    border-radius:12px; padding:20px 24px; margin-bottom:14px;">
            <div style="display:flex; align-items:center; gap:16px;">
                <div style="font-size:2.4rem; font-weight:900; color:{color};
                            min-width:60px; text-align:center;">{score:.0f}</div>
                <div>
                    <div style="font-size:1rem; font-weight:700; color:{color};">{label}</div>
                    <div style="font-size:0.82rem; color:{COLORS['text_secondary']};
                                margin-top:3px;">{desc}</div>
                    {"<div style='font-size:0.8rem; color:" + COLORS['text_secondary'] + "; margin-top:6px;'>Most correlated pair: <b style=color:" + COLORS['warning'] + ";>" + worst_pair[0] + " & " + worst_pair[1] + "</b> (" + f"{worst_pair[2]:.0%}" + " correlated)</div>" if worst_pair else ""}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Section header with anchor ────────────────────────────────────────────────

def section_header(title: str, anchor: str, subtitle: str = "",
                   icon_name: str = "") -> None:
    icon_html = (
        f'<span style="margin-right:8px; opacity:0.85;">'
        f'{icon(icon_name, size=18, color=COLORS["accent"])}</span>'
        if icon_name else ""
    )
    sub_html = (
        f"<div style='font-size:0.82rem; color:{COLORS['text_secondary']}; "
        f"margin-top:4px; padding-left:2px;'>{subtitle}</div>"
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div id="{anchor}" style="padding-top:8px;">
            <div class="qv-section-header"
                 style="display:flex; align-items:center; gap:4px;">
                {icon_html}<span>{title}</span>
            </div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Latest price table ────────────────────────────────────────────────────────

def latest_price_table(latest_prices: dict) -> None:
    rows = [
        {"Ticker": t, "Latest Price": f"${p:,.2f}" if p is not None else "N/A"}
        for t, p in latest_prices.items()
    ]
    st.dataframe(pd.DataFrame(rows).set_index("Ticker"), width="stretch")


# ── Sector flags ──────────────────────────────────────────────────────────────

def display_sector_flags(sector_weights_map: dict) -> None:
    flagged = {s: w for s, w in sector_weights_map.items()
               if w > SECTOR_CONCENTRATION_THRESHOLD}
    if flagged:
        for sector, weight in flagged.items():
            st.warning(
                f"**Concentration risk:** {sector} is {weight:.1%} of your portfolio "
                f"(threshold: {SECTOR_CONCENTRATION_THRESHOLD:.0%}). "
                "Consider diversifying across sectors."
            )
    else:
        st.success(
            f"No sector exceeds {SECTOR_CONCENTRATION_THRESHOLD:.0%}. "
            "Sector diversification looks healthy."
        )
