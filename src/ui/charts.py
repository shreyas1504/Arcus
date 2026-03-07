# ── src/ui/charts.py ───────────────────────────────────────────────────────
# All Plotly figures. Functions return go.Figure objects; the caller renders
# them with st.plotly_chart(fig, use_container_width=True).

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from config import SECTOR_CONCENTRATION_THRESHOLD


# ── Price & return charts ─────────────────────────────────────────────────────

def price_chart(prices: pd.DataFrame) -> go.Figure:
    """Normalised price chart (rebased to 100) for easy comparison."""
    rebased = prices / prices.iloc[0] * 100
    fig = px.line(
        rebased,
        title="Normalised Price History (rebased to 100)",
        labels={"value": "Price (rebased)", "variable": "Ticker", "index": "Date"},
        template="plotly_white",
    )
    fig.update_layout(legend_title_text="Ticker", hovermode="x unified")
    return fig


def returns_chart(returns: pd.DataFrame) -> go.Figure:
    """Daily return chart for all tickers."""
    fig = px.line(
        returns,
        title="Daily Returns",
        labels={"value": "Daily Return", "variable": "Ticker", "index": "Date"},
        template="plotly_white",
    )
    fig.update_layout(legend_title_text="Ticker", hovermode="x unified")
    fig.update_yaxes(tickformat=".1%")
    return fig


# ── Monte Carlo charts ────────────────────────────────────────────────────────

def monte_carlo_portfolio_chart(simulations: np.ndarray, last_price: float) -> go.Figure:
    """
    Plot sampled Monte Carlo paths for the portfolio.
    Renders at most 100 paths for performance; shows median + 5/95 percentile bands.
    """
    n_days = simulations.shape[1]
    x = list(range(n_days))

    fig = go.Figure()

    # Draw a random sample of paths (max 100) as thin traces
    sample_idx = np.random.choice(len(simulations), size=min(100, len(simulations)), replace=False)
    for i in sample_idx:
        fig.add_trace(go.Scatter(
            x=x, y=simulations[i],
            mode="lines",
            line=dict(color="royalblue", width=0.4),
            opacity=0.25,
            showlegend=False,
            hoverinfo="skip",
        ))

    # Median path
    median = np.median(simulations, axis=0)
    fig.add_trace(go.Scatter(
        x=x, y=median,
        mode="lines",
        line=dict(color="white", width=2),
        name="Median path",
    ))

    # 5th / 95th percentile band
    p5 = np.percentile(simulations, 5, axis=0)
    p95 = np.percentile(simulations, 95, axis=0)
    fig.add_trace(go.Scatter(
        x=x + x[::-1],
        y=list(p95) + list(p5[::-1]),
        fill="toself",
        fillcolor="rgba(65,105,225,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="5th–95th percentile",
    ))

    fig.update_layout(
        title="Portfolio Monte Carlo Simulation",
        xaxis_title="Trading Days",
        yaxis_title="Portfolio Value ($)",
        template="plotly_dark",
        hovermode="x",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def monte_carlo_individual_chart(ticker: str, simulations: np.ndarray) -> go.Figure:
    """Monte Carlo paths for a single stock."""
    n_days = simulations.shape[1]
    x = list(range(n_days))

    fig = go.Figure()

    sample_idx = np.random.choice(len(simulations), size=min(80, len(simulations)), replace=False)
    for i in sample_idx:
        fig.add_trace(go.Scatter(
            x=x, y=simulations[i],
            mode="lines",
            line=dict(color="mediumpurple", width=0.5),
            opacity=0.3,
            showlegend=False,
            hoverinfo="skip",
        ))

    median = np.median(simulations, axis=0)
    fig.add_trace(go.Scatter(
        x=x, y=median,
        mode="lines",
        line=dict(color="white", width=2),
        name="Median",
    ))

    fig.update_layout(
        title=f"Monte Carlo Simulation: {ticker}",
        xaxis_title="Trading Days",
        yaxis_title="Price ($)",
        template="plotly_dark",
        showlegend=False,
    )
    return fig


# ── Sector pie chart ──────────────────────────────────────────────────────────

def sector_pie_chart(sector_weights: dict) -> go.Figure:
    """
    Donut chart of portfolio weight by sector.
    Sectors exceeding the concentration threshold are highlighted with a pull.
    """
    labels = list(sector_weights.keys())
    values = list(sector_weights.values())
    pulls = [0.08 if v > SECTOR_CONCENTRATION_THRESHOLD else 0 for v in values]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        pull=pulls,
        textinfo="label+percent",
        hovertemplate="%{label}: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        title="Sector Concentration",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        margin=dict(t=60, b=60),
    )
    return fig


# ── Optimal weights bar chart ─────────────────────────────────────────────────

def optimal_weights_chart(tickers: list, weights) -> go.Figure:
    """Horizontal bar chart of optimised portfolio weights."""
    fig = go.Figure(go.Bar(
        x=list(weights),
        y=tickers,
        orientation="h",
        marker_color="steelblue",
        text=[f"{w:.1%}" for w in weights],
        textposition="outside",
    ))
    fig.update_layout(
        title="Optimal Portfolio Weights (Sharpe-Maximised)",
        xaxis=dict(tickformat=".0%", title="Weight"),
        yaxis_title="Ticker",
        template="plotly_white",
        margin=dict(l=80),
    )
    return fig
