# QuantView — Portfolio Risk Tracker

Most retail investors stare at a list of stock tickers with no real sense of whether their portfolio is diversified, how much they could lose on a bad day, or whether the mix of assets is actually worth the risk. QuantView fixes that.

You pick your stocks, set a date range, and the tool gives you a single **Portfolio Health Score** backed by real quantitative models — Sharpe Ratio, Value at Risk, Beta, sector concentration — all explained in plain English, not just raw numbers. It also runs Monte Carlo simulations to show you a range of possible futures for your portfolio.

> Built with Python + Streamlit. All models written from scratch — no black boxes.

---

## What It Does

| Feature | What it tells you |
|---|---|
| **Portfolio Health Score (0–100)** | One number that summarises everything. Green (>70) is healthy, yellow (40–70) needs attention, red (<40) is a concern. |
| **Annualised Return & Volatility** | Historical growth rate and swing magnitude, shown in dollar terms for your actual portfolio size. |
| **Sharpe Ratio** | How much return are you getting per unit of risk? Above 1 is good; below 0 means a savings account would have beaten you. |
| **Beta vs S&P 500** | How much your portfolio amplifies market swings. Beta of 1.3 = a 10% market drop hits you for ~13%. Computed against real S&P 500 returns, not individual stock correlations. |
| **Value at Risk (95%)** | The worst daily loss you'd expect on a bad day. "On the worst 5% of days, you'd lose X%." |
| **Max Drawdown** | The deepest peak-to-trough loss over the date range — the gut-check number. |
| **Sortino Ratio** | Like Sharpe, but only penalises downside volatility, not the good kind of swings. |
| **Rolling Sharpe** | How your risk-adjusted returns have shifted over time — not just a single historical average. |
| **Benchmark Comparison** | Side-by-side portfolio vs S&P 500: return, Sharpe, volatility, and alpha. |
| **Diversification Score** | Are your stocks truly independent, or secretly making the same bet? Backed by a correlation matrix. |
| **Optimal Portfolio Weights** | The allocation that historically maximised risk-adjusted return, solved via constrained mathematical optimisation. |
| **Sector Concentration** | What percentage of your portfolio sits in each GICS sector. Flags any sector above 40%. |
| **Monte Carlo Simulation** | Up to 1,000 simulated future paths for your portfolio using Geometric Brownian Motion. Shows median, 5th–95th percentile band, and projected portfolio value in dollars. |

---

## How the Models Work

### 1. Portfolio Health Score

The health score is a weighted composite of four risk metrics, each mapped to a 0–100 scale:

```python
# src/analytics/metrics.py

def portfolio_health_score(sharpe, var_daily, vol_annual, weights):
    # Sharpe: 0 → 2 maps to 0 → 40 points
    sharpe_score = np.clip(sharpe / 2.0 * 40, 0, 40)

    # VaR: -5% → -1% daily loss maps to 0 → 25 points
    var_score = np.clip((var_daily + 0.05) / 0.04 * 25, 0, 25)

    # Volatility: 35% → 10% annual maps to 0 → 20 points
    vol_score = np.clip((0.35 - vol_annual) / 0.25 * 20, 0, 20)

    # Concentration: max weight 100% → 25% maps to 0 → 15 points
    conc_score = np.clip((1.0 - max(weights)) / 0.75 * 15, 0, 15)

    return sharpe_score + var_score + vol_score + conc_score
```

The weights — **Sharpe (40), VaR (25), Volatility (20), Concentration (15)** — reflect how much each factor matters to portfolio health in practice.

---

### 2. Sharpe Ratio

Answers: *"For every unit of risk I'm taking, how much return am I actually getting?"*

```python
# src/analytics/metrics.py

def sharpe_ratio(portfolio_returns, risk_free_rate=0.04):
    daily_rf = risk_free_rate / 252          # annual rate → daily
    excess   = portfolio_returns - daily_rf  # return above risk-free
    return (excess.mean() / excess.std()) * np.sqrt(252)  # annualise
```

The `sqrt(252)` converts the daily ratio to an annualised figure. Above 1 is generally good; above 2 is excellent; below 0 means cash was a better bet.

---

### 3. Beta (Portfolio vs S&P 500)

Beta measures how much your whole portfolio moves relative to the market — **not** how one stock moves relative to another. This version fetches real S&P 500 daily returns and regresses your equal-weighted portfolio against them:

```python
# src/pages/results.py  →  _compute_metrics()

mkt_raw   = yf.download("^GSPC", start=start_date, end=end_date, auto_adjust=True)
mkt_ret   = mkt_raw["Close"].squeeze().pct_change().dropna()

# Align dates between portfolio and market (timezone-normalised)
common    = port_returns.index.intersection(mkt_ret.index)
beta      = calculate_beta(port_returns.loc[common], mkt_ret.loc[common])
```

```python
# src/analytics/metrics.py

def calculate_beta(portfolio_returns, market_returns):
    cov = np.cov(portfolio_returns, market_returns)
    return cov[0, 1] / cov[1, 1]   # Cov(portfolio, market) / Var(market)
```

A beta > 1 means your portfolio is more volatile than the market. A beta < 1 means it's more defensive.

---

### 4. Value at Risk (Historical Simulation)

Answers: *"On the worst 5% of days, how much would I lose?"*

```python
# src/analytics/metrics.py

def calculate_var(portfolio_returns, confidence_level=0.95):
    return float(np.percentile(portfolio_returns, (1 - confidence_level) * 100))
    # Returns e.g. -0.023  →  "lose 2.3% on a bad day"
```

No normality assumption — we use the actual 5th percentile of observed daily returns. What happened historically, not what a bell curve predicts.

---

### 5. Annualised Volatility (Covariance Matrix)

Two stocks that always move together are riskier as a pair than two that offset each other. The covariance matrix captures all pairwise relationships:

```python
# src/analytics/metrics.py

def annualized_volatility(returns, weights):
    w   = np.array(weights)
    cov = returns.cov() * 252          # annualise the covariance matrix
    return float(np.sqrt(w.T @ cov @ w))  # classic portfolio variance formula
```

The `w.T @ cov @ w` is standard portfolio variance — it captures every pairwise stock correlation, not just individual volatilities added together.

---

### 6. Sortino Ratio

Like Sharpe, but only punishes *downside* volatility. Upward swings aren't a risk — why penalise them?

```python
# src/analytics/metrics.py

def sortino_ratio(portfolio_returns, risk_free_rate=0.04):
    daily_rf      = risk_free_rate / 252
    excess        = portfolio_returns - daily_rf
    downside      = excess[excess < 0]              # only negative returns
    downside_std  = np.sqrt((downside**2).mean())   # downside deviation
    return (excess.mean() / downside_std) * np.sqrt(252)
```

A Sortino above 1 is generally good. If it's much higher than your Sharpe, your volatility is mostly upside — a good sign.

---

### 7. Diversification Score

Measures how independently your stocks move. Derived from the average pairwise correlation across all your holdings:

```python
# src/analytics/metrics.py

def diversification_score(returns):
    corr     = returns.corr()
    n        = len(corr)
    mask     = ~np.eye(n, dtype=bool)
    avg_corr = corr.where(mask).stack().mean()   # average off-diagonal correlation
    # 0 = perfectly correlated → 100 = completely independent
    return float(np.clip((1 - avg_corr) * 100, 0, 100))
```

Score above 65 = well diversified. Below 40 = most of your stocks are making the same bet.

---

### 8. Portfolio Optimisation (Sharpe Maximisation)

What allocation would have produced the best risk-adjusted return historically? Solved via SciPy's SLSQP constrained minimiser:

```python
# src/models/optimizer.py

def optimize_sharpe(returns):
    n = returns.shape[1]

    def negative_sharpe(weights):
        port_ret = np.dot(weights, returns.mean()) * 252
        port_vol = np.sqrt(np.dot(weights.T, returns.cov().dot(weights)) * 252)
        return -port_ret / port_vol   # minimise negative Sharpe = maximise Sharpe

    result = minimize(
        negative_sharpe,
        x0=np.full(n, 1/n),                       # start: equal weights
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,                   # long-only, no shorting
        constraints={"type": "eq", "fun": lambda w: np.sum(w) - 1}
    )
    return result.x
```

The solver explores thousands of weight combinations and converges on the one with the highest Sharpe. Long-only constraint means no borrowing or short positions.

---

### 9. Monte Carlo Simulation (Geometric Brownian Motion)

To project future prices, QuantView uses GBM — the same mathematical model that underpins the Black-Scholes options pricing formula. It models price as a random walk where returns are log-normally distributed.

The core equation:

```
S(t+1) = S(t) × exp( (μ - σ²/2) × dt + σ × √dt × ε )
```

Where `μ` is historical daily drift, `σ` is daily volatility, and `ε` is a random standard normal shock.

```python
# src/models/monte_carlo.py

def simulate_portfolio(prices, n_simulations=300, n_days=252):
    daily_returns = prices.pct_change().dropna()
    last_price    = float(prices.iloc[-1].mean())
    mu            = float(daily_returns.mean().mean())   # historical drift
    sigma         = float(daily_returns.std().mean())    # historical volatility

    rng    = np.random.default_rng()
    shocks = rng.standard_normal((n_simulations, n_days))  # vectorised — all paths at once

    # Itô correction: (μ - σ²/2) keeps the expected price path correct under log-normal dynamics
    log_returns = (mu - 0.5 * sigma**2) + sigma * shocks
    paths       = last_price * np.exp(np.cumsum(log_returns, axis=1))

    return paths   # shape: (n_simulations, n_days)
```

All 300–1,000 paths are computed in a single NumPy operation — no Python loops. The `μ - σ²/2` term is the Itô correction that prevents the expected price from drifting upward due to Jensen's inequality in log-normal distributions.

---

## Project Structure

```
portfolio-risk-tracker/
├── app.py                         # Entry point — 57 lines, just routing
├── config.py                      # All constants (RISK_FREE_RATE, thresholds, demo portfolios)
├── requirements.txt
├── src/
│   ├── pages/                     # ← One file per page (added in latest refactor)
│   │   ├── welcome.py             # Landing screen (render_welcome)
│   │   ├── setup.py               # Portfolio config form (render_setup)
│   │   └── results.py             # Full analysis dashboard — 8 section functions
│   ├── data/
│   │   └── fetcher.py             # All yfinance I/O — prices, sectors, ticker resolution
│   ├── analytics/
│   │   └── metrics.py             # All risk calculations + plain-English interpret functions
│   ├── models/
│   │   ├── monte_carlo.py         # GBM simulation (portfolio + per-stock)
│   │   └── optimizer.py           # SciPy SLSQP Sharpe maximisation
│   └── ui/
│       ├── icons.py               # ← Lucide icon library (30+ inline SVG icons)
│       ├── charts.py              # All Plotly interactive charts
│       └── components.py          # Streamlit UI blocks (health score, metric cards, sidebar)
└── tests/
    ├── test_metrics.py
    └── test_monte_carlo.py
```

### Why the pages/ split?

The original `app.py` was 716 lines with all three pages and all nine analysis sections mixed together. It's now 57 lines — just session state defaults and a 3-line router:

```python
# app.py
if page == "welcome":  render_welcome()
elif page == "setup":  render_setup()
elif page == "results": render_results()
```

Each page is self-contained. `results.py` further breaks the analysis into eight clearly named section functions (`_section_health`, `_section_risk`, `_section_benchmark`, etc.) so you can find and edit any part instantly.

---

## Icon System (Lucide)

QuantView uses [Lucide](https://lucide.dev) icons embedded as inline SVGs — no CDN, no JavaScript, fully reliable inside Streamlit's HTML renderer.

```python
# src/ui/icons.py

def icon(name: str, size: int = 16, color: str = "currentColor") -> str:
    paths = _ICONS.get(name, _ICONS["minus"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        f'{paths}</svg>'
    )
```

Icons are used in section headers, metric card labels, sidebar navigation links, and the welcome page feature grid. To add a new icon, drop its SVG path string into the `_ICONS` dict in `src/ui/icons.py`.

| Location | Icons used |
|---|---|
| Section headers | activity, dollar-sign, line-chart, shield-alert, bar-chart-2, git-branch, sliders, pie-chart, shuffle |
| Metric cards | trending-up, zap, arrow-down, waves, scale, alert-triangle, gauge |
| Sidebar nav | one icon per section link |
| Sidebar health badge | heart-pulse |
| Sidebar portfolio chip | layers |
| Welcome feature grid | activity, shield-alert, bar-chart-2, git-branch, sliders, shuffle |

---

## Tech Stack

| Tool | Why |
|---|---|
| **Python 3.11+** | Core language |
| **Streamlit 1.52+** | Web dashboard — interactive, no frontend code required |
| **yfinance** | Free historical price data and sector metadata from Yahoo Finance |
| **NumPy / Pandas** | All numerical computation and data manipulation |
| **SciPy** | Portfolio optimisation via SLSQP constrained minimiser |
| **Plotly** | Interactive charts (zoom, hover, export) |
| **Lucide** | Icon set — embedded as inline SVG, no CDN dependency |
| **pytest** | Unit tests for core analytics and simulation functions |

---

## Getting Started

### 1. Clone

```bash
git clone https://github.com/shreyas1504/portfolio-risk-tracker.git
cd portfolio-risk-tracker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 4. Run tests

```bash
python -m pytest tests/ -v
```

---

## Usage Tips

- **Start date**: Use `2020-01-01` or earlier — the more history, the more meaningful the risk metrics
- **End date**: Defaults to today automatically
- **Predict until**: Any future date — 1–2 years ahead gives a good Monte Carlo spread
- **Quick Load**: Use the three demo portfolio buttons (Volatile, Tech Heavy, Diversified) to see the platform in action without entering anything
- **Stock picker**: Choose from the built-in dropdown of 50+ popular tickers, or type any company name (e.g. `nvidia`, `berkshire`) — the tool resolves it to the correct ticker symbol automatically
- **Check data availability**: Click the button after selecting stocks to see exactly what date range each ticker supports before committing to a date range

---

## Limitations

- All metrics are backward-looking — past performance does not predict future results
- Monte Carlo assumes constant historical drift and volatility (GBM is a simplification of real market dynamics)
- Sector data comes from Yahoo Finance's classification, which occasionally lags or is missing for some tickers
- The optimiser finds the historically best allocation, not necessarily the optimal future allocation
- Beta and benchmark comparison require a working internet connection to fetch S&P 500 data

---

## Changelog

### Latest (March 2026)
- **Refactored app.py** from 716 lines to 57 — split into `src/pages/welcome.py`, `src/pages/setup.py`, `src/pages/results.py`
- **Added Lucide icon system** (`src/ui/icons.py`) — 30+ inline SVG icons across all UI components
- **Fixed Beta calculation** — now correctly measures portfolio vs S&P 500 (previously was first stock vs portfolio)
- **Fixed sector weights** — use equal weights consistently (previously used optimised weights for sector pie chart only)
- **Fixed Monte Carlo text** — dollar signs in `st.info()` were triggering Streamlit's LaTeX renderer
- **Fixed sidebar layout** — "Edit Portfolio" button no longer overlapped by disclaimer text
- **Dynamic demo portfolio dates** — end dates now use today's date; predict dates are 1 year forward

---

## Disclaimer

This tool is for educational and demonstration purposes only. It does not constitute financial advice. Always do your own research before making investment decisions.
