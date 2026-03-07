# ── src/ui/components.py ───────────────────────────────────────────────────
# Reusable Streamlit UI building blocks.

import streamlit as st

from config import HEALTH_RED_MAX, HEALTH_YELLOW_MAX, SECTOR_CONCENTRATION_THRESHOLD


# ── Health Score ──────────────────────────────────────────────────────────────

def health_score_color(score: float) -> str:
    if score < HEALTH_RED_MAX:
        return "#e74c3c"       # red
    elif score < HEALTH_YELLOW_MAX:
        return "#f39c12"       # amber
    else:
        return "#27ae60"       # green


def health_score_label(score: float) -> str:
    if score < HEALTH_RED_MAX:
        return "Needs Attention"
    elif score < HEALTH_YELLOW_MAX:
        return "Fair"
    else:
        return "Healthy"


def display_health_score(score: float, components: dict) -> None:
    """
    Hero element: large coloured score + breakdown expander.
    """
    color = health_score_color(score)
    label = health_score_label(score)

    st.markdown(
        f"""
        <div style="text-align:center; padding:24px 0 8px 0;">
            <div style="font-size:5rem; font-weight:800; color:{color}; line-height:1;">
                {score:.0f}
            </div>
            <div style="font-size:1.3rem; color:{color}; font-weight:600; margin-top:4px;">
                {label}
            </div>
            <div style="font-size:0.9rem; color:#888; margin-top:4px;">
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
            st.markdown(
                f"**{component}** — {pts}/{max_pts} pts",
            )
            st.progress(pct)


# ── Metric card ───────────────────────────────────────────────────────────────

def metric_card(label: str, value: str, interpretation: str) -> None:
    """
    Display a metric with its plain-English interpretation below it.
    Uses st.metric for the number and a small italic caption for context.
    """
    st.metric(label=label, value=value)
    st.caption(f"_{interpretation}_")


# ── Latest price table ────────────────────────────────────────────────────────

def latest_price_table(latest_prices: dict) -> None:
    import pandas as pd

    rows = []
    for ticker, price in latest_prices.items():
        rows.append({
            "Ticker": ticker,
            "Latest Price": f"${price:,.2f}" if price is not None else "N/A",
        })
    st.dataframe(pd.DataFrame(rows).set_index("Ticker"), use_container_width=True)


# ── Sector flags ──────────────────────────────────────────────────────────────

def display_sector_flags(sector_weights: dict) -> None:
    """Warn if any sector exceeds the concentration threshold."""
    flagged = {s: w for s, w in sector_weights.items() if w > SECTOR_CONCENTRATION_THRESHOLD}
    if flagged:
        for sector, weight in flagged.items():
            st.warning(
                f"**Concentration risk:** {sector} makes up {weight:.1%} of your portfolio "
                f"(threshold: {SECTOR_CONCENTRATION_THRESHOLD:.0%}). "
                f"Consider diversifying across sectors to reduce single-sector exposure."
            )
    else:
        st.success(
            f"No sector exceeds {SECTOR_CONCENTRATION_THRESHOLD:.0%} of the portfolio. "
            "Sector diversification looks healthy."
        )
