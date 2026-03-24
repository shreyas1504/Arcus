# Arcus — Portfolio Analytics Platform

**Institutional-grade portfolio analytics.** Sharpe ratios. VaR. Monte Carlo. In seconds.

🌐 **Live Demo:** [shreyas1504.github.io/Arcus](https://shreyas1504.github.io/Arcus/)

---

## What It Does

Arcus gives retail investors the same risk analytics that hedge funds use — without the complexity. Pick your stocks, set a date range, and get a full quantitative breakdown with plain-English interpretations.

| Feature | What It Tells You |
|---|---|
| **Health Score (0–100)** | One number summarising portfolio quality. Green (>70) = healthy. |
| **Sharpe / Sortino Ratio** | Risk-adjusted return — are you being rewarded for the risk you're taking? |
| **Beta vs S&P 500** | How much your portfolio amplifies market swings. |
| **Value at Risk (95%)** | Worst expected daily loss on a bad day. |
| **Max Drawdown** | Deepest peak-to-trough loss — the gut-check number. |
| **Monte Carlo Simulation** | 300+ simulated future paths using Geometric Brownian Motion. |
| **Efficient Frontier** | Random portfolios plotted on a risk-return map with your current vs optimal allocation. |
| **Stress Testing** | Estimated losses under 2008 Crisis, COVID Crash, Dot-Com Bust, and custom scenarios. |
| **AI Chat (Arcus AI)** | Ask questions about your portfolio in natural language — powered by Claude. |
| **Sector Analysis** | GICS sector breakdown with concentration warnings. |
| **Correlation Heatmap** | Pairwise stock correlations — are your holdings truly diversified? |

---

## Tech Stack

### Backend
| Tool | Purpose |
|---|---|
| **FastAPI** | REST API with automatic OpenAPI docs |
| **Python 3.11+** | Core analytics engine |
| **NumPy / Pandas** | Numerical computation and data manipulation |
| **SciPy** | Portfolio optimisation (SLSQP constrained minimiser) |
| **yfinance** | Historical price data from Yahoo Finance |
| **Anthropic Claude** | AI chatbot for portfolio Q&A |

### Frontend
| Tool | Purpose |
|---|---|
| **React 18 + TypeScript** | Component-based UI |
| **Vite** | Lightning-fast build tooling |
| **Tailwind CSS** | Utility-first styling with dark theme |
| **Framer Motion** | Smooth animations and transitions |
| **Recharts** | Interactive financial charts |
| **Shadcn/ui** | Accessible component library |

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm

### 1. Clone

```bash
git clone https://github.com/shreyas1504/Arcus.git
cd Arcus
```

### 2. Backend Setup

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Open

- **Frontend:** [http://localhost:8080](http://localhost:8080)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Project Structure

```
Arcus/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Constants and demo portfolios
│   ├── analytics/
│   │   └── metrics.py          # All risk calculations + interpretations
│   ├── data/
│   │   └── fetcher.py          # yfinance data fetching + caching
│   ├── models/
│   │   ├── monte_carlo.py      # GBM simulation engine
│   │   └── optimizer.py        # Sharpe maximisation solver
│   └── routers/
│       ├── portfolio.py        # /api/portfolio/* endpoints
│       ├── chat.py             # AI chatbot endpoint
│       ├── news.py             # Live market news feed
│       └── adapter.py          # /api/v2/* adapter layer
├── frontend/
│   ├── src/
│   │   ├── pages/              # Index, Onboarding, Dashboard, Results, Chat
│   │   ├── components/         # Reusable UI components + charts
│   │   └── lib/                # API client, utilities
│   ├── vite.config.ts
│   └── package.json
└── .github/
    └── workflows/
        └── deploy.yml          # Auto-deploy to GitHub Pages
```

---

## Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/portfolio/analyze` | Full portfolio analysis with all metrics |
| `POST` | `/api/portfolio/monte-carlo` | Monte Carlo simulation |
| `POST` | `/api/portfolio/efficient-frontier` | Efficient frontier computation |
| `POST` | `/api/portfolio/stress-test` | Historical stress test scenarios |
| `POST` | `/api/v2/chat` | AI chatbot conversation |
| `GET` | `/api/news/market` | Live RSS market news feed |

---

## Disclaimer

This tool is for educational and demonstration purposes only. It does not constitute financial advice. Always do your own research before making investment decisions.

---

**Built by [Sai Shreyas Vyamajala](https://github.com/shreyas1504)**
