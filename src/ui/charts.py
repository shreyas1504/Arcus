# ── src/ui/charts.py ───────────────────────────────────────────────────────
# All Plotly figures. Functions return go.Figure objects; the caller renders
# them with st.plotly_chart(fig, use_container_width=True).

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from config import SECTOR_CONCENTRATION_THRESHOLD, COLORS


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


# ── Correlation heatmap ───────────────────────────────────────────────────────

def correlation_heatmap(returns: pd.DataFrame) -> go.Figure:
    """Colour-coded correlation matrix — red = correlated, green = independent."""
    corr = returns.corr().round(2)
    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale=[
            [0.0,  COLORS["success"]],
            [0.5,  "#F5F0EB"],
            [1.0,  COLORS["danger"]],
        ],
        zmin=-1, zmax=1,
        aspect="auto",
    )
    fig.update_layout(
        title="Correlation Matrix",
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text_primary"]),
        coloraxis_colorbar=dict(
            title="Corr",
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["-1", "-0.5", "0", "0.5", "1"],
        ),
        margin=dict(t=60, b=20, l=20, r=20),
    )
    fig.update_traces(textfont=dict(size=13, color="white"))
    return fig


# ── Benchmark overlay chart ───────────────────────────────────────────────────

def benchmark_overlay_chart(prices: pd.DataFrame, bmark_returns: pd.Series,
                             benchmark_name: str = "S&P 500") -> go.Figure:
    """Portfolio (equal-weighted, rebased) vs benchmark on same chart."""
    eq_w = np.array([1.0 / prices.shape[1]] * prices.shape[1])
    port_ret = prices.pct_change().dropna()
    port_daily = (port_ret * eq_w).sum(axis=1)

    # Normalize both indexes to midnight — prices index has a time offset
    # (e.g. 05:00:00) from tz stripping in fetcher.py, while bmark_returns
    # uses midnight timestamps; without this the intersection is always empty.
    port_daily.index    = pd.DatetimeIndex(port_daily.index).normalize()
    bmark_norm          = bmark_returns.copy()
    bmark_norm.index    = pd.DatetimeIndex(bmark_returns.index).normalize()

    common = port_daily.index.intersection(bmark_norm.index)
    port_cumul  = (1 + port_daily.loc[common]).cumprod() * 100
    bmark_cumul = (1 + bmark_norm.loc[common]).cumprod() * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=port_cumul.index, y=port_cumul.values,
        mode="lines", name="Your Portfolio",
        line=dict(color=COLORS["accent"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=bmark_cumul.index, y=bmark_cumul.values,
        mode="lines", name=benchmark_name,
        line=dict(color=COLORS["text_secondary"], width=2, dash="dot"),
    ))
    fig.update_layout(
        title=f"Portfolio vs {benchmark_name} (rebased to 100)",
        xaxis_title="Date",
        yaxis_title="Growth of $100",
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text_primary"]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ── Rolling Sharpe chart ──────────────────────────────────────────────────────

def rolling_sharpe_chart(rolling_sharpe_series: pd.Series, window: int) -> go.Figure:
    """Line chart of rolling Sharpe ratio over time."""
    fig = go.Figure()

    # Zero line
    fig.add_hline(y=0, line=dict(color=COLORS["text_secondary"], dash="dot", width=1))
    fig.add_hline(y=1, line=dict(color=COLORS["success"], dash="dot", width=1),
                  annotation_text="Good (1.0)", annotation_position="right")

    # Colour-fill above/below zero
    pos = rolling_sharpe_series.clip(lower=0)
    neg = rolling_sharpe_series.clip(upper=0)

    fig.add_trace(go.Scatter(
        x=rolling_sharpe_series.index, y=pos,
        fill="tozeroy", mode="none",
        fillcolor="rgba(0,200,150,0.2)", name="Positive Sharpe",
    ))
    fig.add_trace(go.Scatter(
        x=rolling_sharpe_series.index, y=neg,
        fill="tozeroy", mode="none",
        fillcolor="rgba(255,71,87,0.2)", name="Negative Sharpe",
    ))
    fig.add_trace(go.Scatter(
        x=rolling_sharpe_series.index, y=rolling_sharpe_series,
        mode="lines", name="Rolling Sharpe",
        line=dict(color=COLORS["accent"], width=1.5),
    ))

    fig.update_layout(
        title=f"Rolling Sharpe Ratio ({window}-day window)",
        xaxis_title="Date",
        yaxis_title="Sharpe Ratio",
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(color=COLORS["text_primary"]),
        hovermode="x unified",
        showlegend=False,
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
