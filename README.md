# Portfolio Risk Tracker

Most retail investors stare at a list of stock tickers with no real sense of whether their portfolio is diversified, how much they could lose on a bad day, or whether the mix of assets is actually worth the risk. This project is my attempt to fix that.

You pick your stocks, set a date range, and the tool gives you a single **Portfolio Health Score** backed by real quantitative models — Sharpe Ratio, Value at Risk, Beta, sector concentration — all explained in plain English, not just raw numbers. It also runs Monte Carlo simulations to show you a range of possible futures for your portfolio.

I built this to get hands-on with financial modelling, portfolio theory, and Python data tooling. Everything from the risk calculations to the optimiser to the simulations is written from scratch using standard scientific Python libraries.

---

## What It Does

| Feature | Description |
|---|---|
| **Portfolio Health Score (0–100)** | One composite number that summarises your portfolio's risk-return profile. Green (>70) means healthy, yellow (40–70) needs work, red (<40) is a concern. |
| **Annualised Return & Volatility** | Historical growth rate and swing magnitude, translated into dollar amounts for your actual portfolio size. |
| **Sharpe Ratio** | Measures how much return you're getting per unit of risk. Above 1 is generally good; below 0 means a risk-free account would have done better. |
| **Beta** | How much your portfolio amplifies or dampens market moves. A beta of 1.3 means a 10% market drop hits you for roughly 13%. |
| **Value at Risk (95%)** | The worst daily loss you'd expect on a bad day — shown in both percentage and dollar terms. |
| **Optimal Portfolio Weights** | The allocation that historically maximised risk-adjusted return, solved via constrained mathematical optimisation. |
| **Sector Concentration Analysis** | What percentage of your portfolio sits in each GICS sector, with a warning if any single sector exceeds 40%. |
| **Monte Carlo Simulation** | 300 possible future paths for your portfolio using Geometric Brownian Motion, showing the median, the 5th–95th percentile band, and a future value projection for your investment. |

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

The weights — Sharpe (40), VaR (25), Volatility (20), Concentration (15) — reflect how much each factor matters to overall portfolio health in practice.

---

### 2. Sharpe Ratio

The Sharpe ratio measures risk-adjusted return. It answers the question: *"For every unit of risk I'm taking, how much am I getting paid?"*

```python
# src/analytics/metrics.py

def sharpe_ratio(portfolio_returns, risk_free_rate=0.04):
    daily_rf = risk_free_rate / 252          # convert annual rate to daily
    excess = portfolio_returns - daily_rf    # excess return over risk-free
    return (excess.mean() / excess.std()) * np.sqrt(252)  # annualise
```

The `sqrt(252)` annualises the ratio from daily to yearly. A Sharpe above 1 is generally considered good; above 2 is excellent.

---

### 3. Value at Risk (VaR)

VaR answers: *"On a typical bad day (worst 5% of days), how much could I lose?"* We use the historical simulation method — no normality assumption, just the 5th percentile of actual observed daily returns.

```python
# src/analytics/metrics.py

def calculate_var(portfolio_returns, confidence_level=0.95):
    return float(np.percentile(portfolio_returns, (1 - confidence_level) * 100))
    # Returns a negative number, e.g. -0.023 means "lose 2.3% on a bad day"
```

---

### 4. Annualised Volatility

Portfolio volatility accounts for how individual stocks move relative to each other — not just their individual swings. Two stocks that always move together are riskier as a pair than two that offset each other.

```python
# src/analytics/metrics.py

def annualized_volatility(returns, weights):
    w = np.array(weights)
    cov = returns.cov() * 252          # annualise the covariance matrix
    return float(np.sqrt(w.T @ cov @ w))  # classic portfolio variance formula
```

The `w.T @ cov @ w` is the matrix form of portfolio variance — it captures every pairwise correlation between your holdings, not just individual stock volatilities.

---

### 5. Portfolio Optimisation (Sharpe Maximisation)

Given a set of stocks, what allocation would have produced the best risk-adjusted return historically? This is a constrained optimisation problem solved with SciPy's SLSQP solver.

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
        x0=np.full(n, 1/n),                        # start from equal weights
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,                   # long-only: no short selling
        constraints={"type": "eq", "fun": lambda w: np.sum(w) - 1}  # must sum to 1
    )
    return result.x
```

The solver explores thousands of weight combinations and converges on the one that maximises Sharpe. The long-only constraint keeps weights between 0 and 1 — no borrowing or short positions.

---

### 6. Monte Carlo Simulation (Geometric Brownian Motion)

To project future prices, we use GBM — the same mathematical model that underpins the Black-Scholes options pricing formula. It models price as a random walk where returns are log-normally distributed.

The core equation is:

```
S(t+1) = S(t) × exp( (μ - σ²/2) + σ × ε )
```

Where `μ` is the historical daily drift, `σ` is daily volatility, and `ε` is a random standard normal shock.

```python
# src/models/monte_carlo.py

def simulate_portfolio(prices, n_simulations=300, n_days=252):
    daily_returns = prices.pct_change().dropna()
    last_price = float(prices.iloc[-1].mean())
    mu = float(daily_returns.mean().mean())       # historical drift
    sigma = float(daily_returns.std().mean())     # historical volatility

    rng = np.random.default_rng()
    shocks = rng.standard_normal((n_simulations, n_days))  # all paths at once

    # Ito correction: (μ - σ²/2) adjusts for log-normal drift
    log_returns = (mu - 0.5 * sigma**2) + sigma * shocks
    paths = last_price * np.exp(np.cumsum(log_returns, axis=1))

    return paths  # shape: (n_simulations, n_days)
```

The whole simulation is vectorised — all 300 paths are computed in a single NumPy operation instead of a Python loop. The `μ - σ²/2` term is the Itô correction that ensures the expected price path is correct under log-normal dynamics.

---

## Project Structure

```
portfolio-risk-tracker/
├── app.py                      # Streamlit entry point — 3-page flow (Welcome → Setup → Results)
├── config.py                   # All constants (risk-free rate, thresholds, popular tickers)
├── requirements.txt
├── src/
│   ├── data/
│   │   └── fetcher.py          # All yfinance I/O — price download, sector fetch,
│   │                           # ticker resolution by company name, data availability checker
│   ├── analytics/
│   │   └── metrics.py          # Sharpe, Beta, VaR, volatility, health score,
│   │                           # plain-English interpretations
│   ├── models/
│   │   ├── monte_carlo.py      # GBM simulation — portfolio-level and per-stock
│   │   └── optimizer.py        # SciPy SLSQP Sharpe maximisation
│   └── ui/
│       ├── charts.py           # All Plotly interactive charts
│       └── components.py       # Streamlit building blocks (health score hero, metric cards)
└── tests/
    ├── test_metrics.py
    └── test_monte_carlo.py
```

---

## Tech Stack

| Tool | Why |
|---|---|
| **Python 3.11+** | Core language |
| **Streamlit** | Web dashboard — fast to build, interactive out of the box |
| **yfinance** | Free historical price data and sector metadata from Yahoo Finance |
| **NumPy / Pandas** | All numerical computation and data manipulation |
| **SciPy** | Portfolio optimisation via SLSQP constrained minimiser |
| **Plotly** | Interactive charts (zoom, hover, export) |
| **pytest** | Unit tests for core analytics and simulation functions |

---

## Getting Started

### 1. Clone

```bash
git clone https://github.com/your-username/portfolio-risk-tracker.git
cd portfolio-risk-tracker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

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
- **End date**: Any past date, e.g. `2025-12-31`
- **Predict until**: Any future date — 1–2 years ahead gives a good simulation spread
- **Stock picker**: Choose from the built-in dropdown of 50+ popular tickers, or type any company name (e.g. `nvidia`, `berkshire`) — the tool resolves it to the right symbol automatically
- **Check data availability**: Click the button after selecting stocks to see exactly what date range each ticker supports

---

## Limitations

- All metrics are backward-looking — past performance does not predict future results
- Monte Carlo assumes constant historical drift and volatility, which is a simplification of real market dynamics
- Sector data depends on Yahoo Finance's classification, which occasionally lags or is missing for some tickers
- The optimiser finds the historically best allocation, not necessarily the future best

---

## Disclaimer

This tool is for educational and demonstration purposes only. It does not constitute financial advice. Always do your own research before making investment decisions.
