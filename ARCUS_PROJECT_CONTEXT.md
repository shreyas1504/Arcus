# Arcus — Full Project Context & Continuation Guide

> **Purpose**: Feed this file to any AI coding assistant so it can continue where we left off.
> **Last updated**: 2026-03-21 20:15 EST
> **Repo**: `/Users/shreyas/Desktop/portfolio-risk-tracker`
> **Rebrand**: Originally named "Pulse" — rebranded to **Arcus** (frontend only; internal code identifiers like variable names, file names, and CSS class names still reference "pulse" where they existed before)

---

## 1. What Is Arcus

A **full-stack portfolio risk analytics platform** migrated from a Streamlit app to:
- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS v4 + shadcn/ui + Recharts + Framer Motion
- **Backend**: FastAPI (Python) — all analytics logic ported from the original `src/` Streamlit code
- **AI Chatbot**: Anthropic Claude via `/api/chat` (comprehensive fallback system works without API key — 20+ topic categories)
- **Data**: yfinance (upgraded to 1.2.0 with subprocess isolation to avoid rate limiting)
- **News**: Live RSS feeds from Yahoo Finance, CNBC, MarketWatch, Reuters (no API key needed)
- **Design System**: Arcus — calm, precise, institutional aesthetic with sage green palette, Syne + DM Mono typography, signal-color status system

---

## 2. Project Structure

```
portfolio-risk-tracker/
├── backend/                         # FastAPI backend
│   ├── __init__.py
│   ├── main.py                      # FastAPI app, CORS, router registration
│   ├── config.py                    # Constants, demo portfolios, popular tickers
│   ├── analytics/
│   │   ├── __init__.py
│   │   └── metrics.py               # All risk metrics (Sharpe, VaR, beta, health score, etc.)
│   ├── data/
│   │   ├── __init__.py
│   │   └── fetcher.py               # yfinance via subprocess isolation + in-memory cache
│   ├── models/
│   │   ├── __init__.py
│   │   ├── monte_carlo.py           # GBM-based Monte Carlo simulation
│   │   └── optimizer.py             # 3 strategies: Sharpe, Momentum, Risk Parity
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── portfolio.py             # /api/portfolio/* (analyze, optimize, monte-carlo, sectors, recommendations)
│   │   ├── chat.py                  # /api/chat (Anthropic Claude + comprehensive fallback)
│   │   └── news.py                  # /api/news/* (live RSS from Yahoo, CNBC, MarketWatch, Reuters)
│   └── requirements.txt
│
├── frontend/                        # Next.js 16 frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx           # Root layout (Syne + DM Mono fonts, ThemeProvider, Navbar)
│   │   │   ├── page.tsx             # Landing page (/)
│   │   │   ├── dashboard/page.tsx   # Dashboard config form (/dashboard)
│   │   │   ├── dashboard/results/page.tsx  # Analysis results (/dashboard/results?tickers=...)
│   │   │   ├── chat/page.tsx        # Full chat page (/chat) — separate from floating chat
│   │   │   └── globals.css          # Arcus design system: 40+ CSS variables, light/dark theme
│   │   ├── components/
│   │   │   ├── navbar.tsx           # 48px sticky nav with Arcus globe logo, inverted pill nav, segmented theme toggle
│   │   │   ├── pulse-logo.tsx       # Arcus meridian-globe SVG + "Arcus" wordmark + "PORTFOLIO RISK ANALYTICS" subline
│   │   │   ├── theme-provider.tsx   # next-themes provider (data-theme attribute, arcus-theme storage key)
│   │   │   ├── theme-toggle.tsx     # Segmented pill: [◑ DARK] [○ LIGHT]
│   │   │   ├── news-ticker.tsx      # Scrolling market news bar (live RSS, DM Mono labels)
│   │   │   ├── floating-chat.tsx    # Floating chatbot (bottom-right, accent colors, "Arcus AI")
│   │   │   └── ui/                  # shadcn/ui components (badge, button, card, input, etc.)
│   │   └── lib/
│   │       ├── api.ts               # All API functions + TypeScript interfaces
│   │       └── utils.ts             # cn() utility
│   ├── package.json
│   └── next.config.ts
│
├── src/                             # ORIGINAL Streamlit app (reference only)
├── app.py                           # Original Streamlit entry point (not used)
├── config.py                        # Original Streamlit config (not used)
├── start.sh                         # Backend startup shortcut
├── PULSE_PROJECT_CONTEXT.md         # Original project context (pre-rebrand)
└── ARCUS_PROJECT_CONTEXT.md         # THIS FILE
```

---

## 3. Arcus Design System

### Rebrand: Pulse → Arcus
- All **user-facing text** renamed: "Pulse" → "Arcus", "Pulse AI" → "Arcus AI"
- Internal code identifiers (variable names, file names like `pulse-logo.tsx`, CSS class names) **intentionally kept** as-is to avoid breaking changes
- Logo replaced with Arcus meridian-globe SVG mark + "Arcus" wordmark
- localStorage theme key changed from `pulse-theme` → `arcus-theme`

### Typography
| Usage | Font | Size | Weight | Tracking |
|-------|------|------|--------|----------|
| Headings | Syne | 18–56px | 700–800 | -0.05em |
| Body/prose | Syne | 12–14px | 400–500 | normal |
| Data labels | DM Mono | 9px uppercase | 400 | 0.10em |
| Data values | DM Mono | 16–36px | 500 | -0.03em |
| Navigation | Syne | 12px | 500–600 | -0.01em |
| Chips/pills | DM Mono | 9–10px uppercase | 400–500 | 0.04–0.08em |

Fonts loaded via `next/font/google` in `layout.tsx` (not CSS `@import`).

### Color System (CSS Variables in `globals.css`)
| Variable | Light Mode | Dark Mode | Usage |
|----------|-----------|-----------|-------|
| `--bg-base` | `#EEF4EC` (sage green) | `#0a120a` | Page background |
| `--bg-surface` | `#FFFFFF` | `#141e14` | Card surfaces |
| `--bg-elevated` | `#F5F8F5` | `#1a2a1a` | Input fields |
| `--bg-subtle` | `#EBF0EB` | `#1e2e1e` | Pill backgrounds |
| `--text-primary` | `#1a2a1a` | `#d8ead8` | Headings, values |
| `--text-secondary` | `#4a6a4a` | `#8aaa8a` | Body text |
| `--text-muted` | `#7aaa7a` | `#5a7a5a` | Labels, hints |
| `--accent` | `#2a8a3a` | `#4dbb6d` | Primary action, links |
| `--signal-green` | `#2a8a5a` | `#4dbb7d` | Healthy/good status |
| `--signal-amber` | `#b8852a` | `#d4a43a` | Warning/moderate |
| `--signal-red` | `#b04a3a` | `#d46a5a` | At risk/bad |
| `--border-dim` | `rgba(60,100,60,0.07)` | `rgba(100,200,100,0.06)` | Subtle borders |
| `--border` | `rgba(60,100,60,0.12)` | `rgba(100,200,100,0.10)` | Standard borders |
| `--shadow-card` | `0 1px 3px rgba(26,42,26,0.06)` | `0 1px 3px rgba(0,0,0,0.20)` | Card elevation |

### Utility Classes (in `globals.css`)
| Class | Description |
|-------|-------------|
| `.arcus-card` | White surface, 1px dim border, 12px radius, card shadow, hover lift |
| `.arcus-divider` | Centered horizontal rule with label text |
| `.arcus-card-accent` | Accent-bg background card |
| `.arcus-card-alert` | Left red border card |
| `.arcus-card-warning` | Left amber border card |
| `.arcus-card-success` | Left green border card |
| `.reveal`, `.reveal-1`…`.reveal-4` | Staggered fade-up animation |

### Key UI Patterns
- **Inverted pill navigation**: Active state = dark bg (`--text-primary`) + light text (`--bg-surface`)
- **Segmented theme toggle**: `[◑ DARK] [○ LIGHT]` — DM Mono 10px uppercase, active segment gets surface bg
- **Section dividers**: `arcus-divider` with centered label between horizontal rules
- **Metric cards**: Signal-color background (`--signal-*-bg`), DM Mono 9px uppercase label, DM Mono 20px value
- **Chart design**: Horizontal-only grid lines (`stroke="var(--border-dim)"`), dark tooltip bg (`#2a3a2a`), DM Mono 10px axis ticks
- **Ticker pills**: Accent bg, white text, DM Mono 10px uppercase
- **Quick-question chips**: DM Mono 9px uppercase, accent-bg background, border, 16px radius

---

## 4. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/portfolio/analyze` | Full portfolio analysis (metrics, charts, benchmark) |
| POST | `/api/portfolio/optimize` | 3 strategies: Sharpe, Momentum, Risk Parity |
| POST | `/api/portfolio/monte-carlo` | GBM simulation with configurable paths/days |
| POST | `/api/portfolio/sectors` | Sector weights + sector map |
| POST | `/api/portfolio/recommendations` | AI-generated improvement suggestions |
| POST | `/api/chat` | Chatbot (Claude + 20-topic fallback) |
| GET | `/api/news/market` | Live market news from RSS (Yahoo, CNBC, MarketWatch, Reuters) |
| GET | `/api/news/ticker/{ticker}` | Ticker-specific news from Yahoo Finance RSS |
| GET | `/api/portfolio/demo-portfolios` | Demo portfolio configs |
| GET | `/api/portfolio/popular-tickers` | List of 50+ popular tickers |
| GET | `/health` | Health check |

---

## 5. Key Technical Decisions

### yfinance Subprocess Isolation
- All yfinance calls run in fresh subprocesses with JSON IPC
- 5-min/10-min TTL in-memory cache
- Upgraded from 0.2.57 → 1.2.0 (includes `curl_cffi`)
- All endpoints are sync `def` (runs in FastAPI threadpool)

### Live News (RSS Feeds)
- **No API key needed** — uses standard RSS from Yahoo Finance, CNBC, MarketWatch, Reuters
- Feeds fetched in parallel via ThreadPoolExecutor
- Deduplicated by headline, sorted by time, cached 5 minutes
- Ticker-specific news via Yahoo Finance RSS: `https://feeds.finance.yahoo.com/rss/2.0/headline?s={TICKER}`

### ML Optimizer (3 strategies)
- **Max Sharpe**: Classic mean-variance via SciPy SLSQP
- **Momentum**: 60% Sharpe + 40% 3-month cumulative return signal
- **Risk Parity**: Minimizes squared difference from equal risk contribution

### Chatbot Fallback System
- **20+ keyword categories** including: recommend, optimize, improve, add, buy, should I, what more, sharpe, VaR, beta, drawdown, volatility, sortino, returns, diversification, sectors, health, benchmark, Monte Carlo, CAPM, Efficient Frontier, MPT
- **Sector-aware recommendations**: Analyzes current sectors, identifies gaps, suggests specific ETFs (XLV, XLE, XLF, TLT, GLD, VNQ, etc.) with descriptions
- **Portfolio weakness detection**: Automatically flags high beta, low diversification, high volatility, severe drawdown, sector concentration > 50%
- Greetings, thanks, and follow-up responses handled naturally
- General fallback shows smart portfolio summary with all key metrics
- Works without Anthropic API key

### Arcus Design System (Frontend)
- **CSS Variable Architecture**: 40+ tokens defined in `globals.css` `:root` and `[data-theme="dark"]` blocks
- **Theme switching**: `next-themes` with `data-theme` attribute, `arcus-theme` localStorage key
- **Font loading**: `next/font/google` in `layout.tsx` (NOT CSS `@import` — this avoids Tailwind v4 `@import` order violations)
- **Component styling**: Inline styles using CSS variables (e.g., `style={{ color: "var(--text-primary)" }}`) for full theme reactivity
- **Chart colors**: Green palette `["#2a8a3a", "#4dbb6d", "#5aaa5a", "#b8852a", "#7aaa7a", "#2a8a5a", "#3aaa5a", "#6acc7a"]`
- **Dark tooltips**: `{ background: "#2a3a2a", border: "1px solid rgba(100,200,100,0.15)", color: "#d8ead8" }`

---

## 6. How to Run

```bash
# Terminal 1 — Backend (port 8000)
cd /Users/shreyas/Desktop/portfolio-risk-tracker
./start.sh                # shortcut for: python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend (port 3000)
cd /Users/shreyas/Desktop/portfolio-risk-tracker/frontend
npm run dev
```

Open: http://localhost:3000/dashboard

---

## 7. Current Status ✅

### Backend ✅
- [x] All analytics metrics ported (Sharpe, Sortino, VaR, Beta, Max Drawdown, Health Score, Diversification)
- [x] yfinance subprocess isolation with caching
- [x] Monte Carlo simulation (GBM)
- [x] 3-strategy optimizer (Sharpe, Momentum, Risk Parity)
- [x] Benchmark comparison vs S&P 500
- [x] AI chatbot (Claude + 20-topic comprehensive fallback)
- [x] Live news via RSS (Yahoo, CNBC, MarketWatch, Reuters)
- [x] Recommendations engine

### Frontend ✅
- [x] Arcus design system — 40+ CSS variables, light/dark theme, Syne + DM Mono typography
- [x] Arcus meridian-globe logo SVG + wordmark
- [x] 48px sticky navbar with inverted pill navigation and segmented theme toggle
- [x] Dashboard — Configure Portfolio form (searchable dropdown, date pickers, Quick Load, Advanced, two-column layout)
- [x] Dashboard — 15 analytics sections with signal-color status system
- [x] Dashboard results — Metric cards, price charts, rolling Sharpe, benchmarks, diversification, sectors, Monte Carlo, recommendations
- [x] Live scrolling news ticker at top (DM Mono labels, signal-red LIVE badge)
- [x] Floating chatbot (bottom-right, accent-colored, context-aware, "Arcus AI")
- [x] Full chat page with DM Mono suggestion chips
- [x] Dark/light theme switching (segmented pill toggle)
- [x] "Pulse" → "Arcus" rebrand across all user-facing text
- [x] Build passes cleanly (hydration fix applied to chat timestamps)

---

## 8. Usage Flow

1. Open http://localhost:3000 → Landing page with Arcus branding (sage green bg, globe logo, "Complete overview of your financial infrastructure")
2. Click "Dashboard" in navbar pill → http://localhost:3000/dashboard
3. **News Ticker** scrolls at top with live headlines from CNBC, Yahoo, MarketWatch, Reuters (DM Mono labels, signal-red LIVE badge)
4. **Configure Portfolio** (on /dashboard page, two-column layout):
   - Click "Quick Load" preset (e.g., "TECH HEAVY — YELLOW SCORE" in DM Mono pill chips)
   - OR search/select tickers from the dropdown (accent-colored ticker pills)
   - OR type custom tickers in the text input
   - Set date range and Monte Carlo prediction target (DM Mono 9px uppercase labels)
   - Click "Analyse Portfolio →" (accent-colored button)
5. **Navigates to /dashboard/results** page with query params
6. **Loading State** shows while data fetches (~15-30s) (accent-colored spinner, ticker pills)
7. **Results** render in order with `arcus-divider` section separators:
   1. Health Score gauge (0-100, signal-color ring, DM Mono score)
   2. Risk Metrics grid (Return, Volatility, Sharpe, Beta, VaR, Drawdown, Sortino — signal-color metric cards)
   3. Price History chart (normalized to 100, green palette, dark tooltip)
   4. Rolling Sharpe chart (60-day, accent gradient fill)
   5. Benchmark Comparison (portfolio vs S&P 500, accent-bg stat cards)
   6. Diversification Score (ring gauge, signal-color)
   7. Optimal Weights (3 strategies: Sharpe / Momentum / Risk Parity — inverted pill toggle)
   8. Sector Concentration (pie chart, `arcus-card-warning` for >40% concentration)
   9. Monte Carlo Simulation (paths + signal-color percentile cards)
   10. AI Recommendations (`arcus-card-accent` with alert/warning/success/info variants)
8. **"← Back" button** returns to /dashboard to reconfigure (Syne 12px, border-strong style)
9. **Floating Chatbot** (bottom-right accent-colored circle) — click to open, ask about portfolio metrics
10. **Full Chat Page** at http://localhost:3000/chat — "Arcus AI" header, DM Mono suggestion chips, accent-bg user bubbles

---

## 9. Next-Level Feature Ideas (Priority Order)

### 🔥 High Impact — Do These First

1. **Correlation Matrix Heatmap**
   - Backend: Return pairwise correlation matrix from `/analyze`
   - Frontend: Interactive heatmap using Recharts or custom SVG
   - Shows which stocks move together (red = high correlation, blue = low)

2. **Drawdown Chart**
   - Backend already returns drawdown series
   - Frontend: Add an area chart below the Rolling Sharpe showing drawdown over time
   - Highlight worst drawdown period

3. **Efficient Frontier Visualization**
   - Backend: Generate 100-200 random portfolio weights, compute risk/return for each
   - Frontend: Scatter plot with risk (x) vs return (y), highlight current portfolio + optimal
   - Shows the user WHERE their portfolio sits on the frontier

4. **Individual Stock Analysis Cards**
   - Click a ticker → Expand modal/card with: price chart, news, sector, P/E ratio, 52-week range
   - Uses yfinance `Ticker.info` for fundamentals + Yahoo RSS for news

5. **Watchlist / Saved Portfolios (LocalStorage)**
   - Save current portfolio config to browser localStorage
   - Quick-load saved portfolios without backend changes
   - Eventually migrate to Supabase when auth is added

### 💡 Medium Impact — Differentiators

6. **LSTM Price Prediction Model**
   - Add a lightweight LSTM using TensorFlow/PyTorch for short-term price prediction
   - Display predicted next-30-day trend alongside Monte Carlo
   - Show confidence interval + backtested accuracy

7. **Sentiment Analysis on News**
   - Use TextBlob or VADER on RSS headlines
   - Show sentiment gauge per ticker (bullish/neutral/bearish)
   - Aggregate into "Market Mood" indicator on dashboard

8. **Portfolio Stress Testing**
   - "What if the market crashes 20%?" → Show impact on your portfolio using beta
   - "What if interest rates rise 2%?" → Model interest rate sensitivity
   - Backend endpoint: `/api/portfolio/stress-test`

9. **Risk Attribution**
   - Show which stock contributes most to portfolio risk
   - Bar chart: each stock's risk contribution as % of total
   - Helps user identify which position to trim

10. **Export Report (PDF)**
    - Generate a PDF of the full analysis
    - Include all charts as images, metrics table, recommendations
    - Use html2canvas + jspdf on frontend

### 🚀 Long-Term — Production Features

11. **Authentication (Clerk)**
    - Sign up / Login with Google, GitHub, or email
    - Gate portfolio saving and advanced features behind auth

12. **Database (Supabase/PostgreSQL)**
    - Save portfolios, analysis history, user preferences
    - Track portfolio performance over time

13. **Price Alerts**
    - Set alerts when a stock hits a target price or VaR threshold breached
    - Email or browser push notifications
    - Backend: Celery + Redis for background price checking

14. **Social Sharing**
    - Share portfolio analysis as a public link
    - "Compare with friends" feature

15. **Mobile-Responsive Dashboard**
    - Currently desktop-first — add responsive breakpoints
    - Stack all cards on mobile, simplify charts

### 🎯 Additional Model & Feature Ideas

16. **Crypto & ETF Tracking**
    - Support BTC-USD, ETH-USD, SOL-USD alongside stocks
    - yfinance already supports these tickers
    - Show crypto-specific metrics (24hr volume, market cap)

17. **Backtesting Engine**
    - "What if I had started this portfolio 5 years ago?"
    - Backend: Loop through historical windows, compute cumulative returns
    - Frontend: Interactive year slider showing hypothetical growth

18. **Performance Attribution (Brinson Model)**
    - Break down returns into: allocation effect, selection effect, interaction effect
    - Shows whether your returns came from being in the right sectors or picking the right stocks

19. **Portfolio Comparison**
    - Compare two portfolios side-by-side
    - "My portfolio vs 60/40 stocks/bonds" or "vs all-SPY"
    - Dual-column layout with matching metrics

20. **Conditional Value at Risk (CVaR / Expected Shortfall)**
    - More conservative than VaR — shows the average loss in the worst 5% of days
    - Backend: Add CVaR computation to metrics.py
    - CVaR is preferred by institutional risk managers over VaR

21. **Regime Detection (Hidden Markov Model)**
    - Detect bull/bear/sideways market regimes from historical returns
    - Show current regime probability on dashboard
    - Adjust Monte Carlo parameters based on detected regime

22. **Factor Exposure Analysis (Fama-French)**
    - Decompose returns into Market, Size, Value, Momentum, Quality factors
    - Show which factors drive your portfolio's returns
    - Backend: Download factor data from Kenneth French's library

---

## 10. Environment / Dependencies

### Backend (conda python at /opt/anaconda3/bin/python)
- fastapi, uvicorn, pydantic
- yfinance==1.2.0, curl_cffi
- numpy, pandas, scipy
- anthropic (optional, for Claude AI)

### Frontend
- next@16.1.7, react@19, typescript
- tailwindcss@4, @tailwindcss/postcss
- framer-motion, recharts
- shadcn/ui components (manually installed)
- next-themes, lucide-react
- **Fonts**: Syne (400–800) + DM Mono (400–500) via `next/font/google`

---

## 11. Known Issues / Quirks

1. **yfinance rate limiting**: Subprocess + cache handles it. If it fails, wait 1-2 minutes.
2. **Pyre2 lint errors**: False positives for `backend.*` imports — handled with `# type: ignore` in `app.py`.
3. **Monte Carlo n_days**: Frontend calculates trading days from predict date approximately.
4. **RSS feeds**: May occasionally fail (network issues) — falls back to minimal message. Cached 5 min.
5. **CSS `@import` order**: Google Fonts MUST NOT be loaded via `@import url(...)` in `globals.css` — Tailwind v4's `@import "tailwindcss"` injects rules that break subsequent `@import url()` per CSS spec. Fonts are loaded via `next/font/google` in `layout.tsx` instead.
6. **Chat hydration**: `toLocaleTimeString()` produces different formats on server vs client. Fixed with `suppressHydrationWarning` on timestamp elements.
7. **File naming**: `pulse-logo.tsx` still named "pulse" — this is intentional to avoid import-chain changes. The component itself renders the Arcus logo.
8. **VS Code CSS lints**: `@theme` and `@apply` warnings are false positives — these are valid Tailwind v4 directives.

---

## 12. File Sizes Reference

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/src/app/globals.css` | ~242 | Arcus design system: 40+ CSS variables, light/dark theme, utility classes |
| `frontend/src/app/layout.tsx` | ~43 | Root layout: Syne + DM Mono fonts, ThemeProvider, Navbar |
| `frontend/src/app/page.tsx` | ~385 | Landing page: hero, stat cards, features grid, CTA |
| `frontend/src/app/dashboard/page.tsx` | ~697 | Dashboard config: ticker select, date pickers, sidebar, two-column layout |
| `frontend/src/app/dashboard/results/page.tsx` | ~802 | Results: health gauge, 7 metric cards, 6 charts, recommendations |
| `frontend/src/app/chat/page.tsx` | ~274 | Full chat page: Arcus AI, suggestion chips, message bubbles |
| `frontend/src/components/navbar.tsx` | ~156 | 48px sticky nav: globe logo, inverted pill nav, theme toggle, market badge |
| `frontend/src/components/pulse-logo.tsx` | ~64 | Arcus meridian-globe SVG + wordmark |
| `frontend/src/components/theme-toggle.tsx` | ~48 | Segmented [◑ DARK] [○ LIGHT] pill |
| `frontend/src/components/theme-provider.tsx` | ~21 | next-themes config (data-theme, arcus-theme key) |
| `frontend/src/components/news-ticker.tsx` | ~109 | Scrolling news bar: live RSS, DM Mono labels |
| `frontend/src/components/floating-chat.tsx` | ~272 | Floating chatbot: accent colors, context-aware |
| `frontend/src/lib/api.ts` | ~192 | API functions + TypeScript interfaces |
| `backend/routers/portfolio.py` | ~359 | Portfolio endpoints |
| `backend/routers/chat.py` | ~532 | Chat endpoint (20+ topic categories) |
| `backend/routers/news.py` | ~170 | Live RSS news endpoint |
| `backend/analytics/metrics.py` | ~226 | All metric functions |
| `backend/data/fetcher.py` | ~265 | yfinance subprocess fetcher |
| `backend/models/optimizer.py` | ~114 | 3 optimization strategies |
| `backend/models/monte_carlo.py` | ~41 | GBM simulation |
| `backend/config.py` | ~73 | Constants + demo portfolios |

---

## 13. Continuation Instructions

When continuing in any AI coding assistant:

1. **Start servers**: `./start.sh` (backend, port 8000) + `cd frontend && npm run dev` (port 3000)
2. **Open dashboard**: http://localhost:3000/dashboard
3. **Priority tasks**: See Section 9 — start with Correlation Heatmap, Drawdown Chart, or Efficient Frontier
4. **Styling rules**: Use CSS variables (`var(--accent)`, `var(--text-primary)`, etc.) — never hardcode hex colors. Use `fontFamily: "'DM Mono', monospace"` for data, `fontFamily: "'Syne', sans-serif"` for prose.
5. **Label format**: All data labels should be DM Mono, 9px, uppercase, `letterSpacing: "0.10em"`, `color: "var(--text-muted)"`
6. **Value format**: All data values should be DM Mono, `fontWeight: 500`, `letterSpacing: "-0.03em"`, `color: "var(--text-primary)"`
7. **Card pattern**: Use `.arcus-card` class or replicate its style (`background: var(--bg-surface)`, `border: 1px solid var(--border-dim)`, `borderRadius: 12px`)
8. **Testing**: Always test backend changes with `curl` before frontend integration
9. **Build check**: Run `cd frontend && npx next build` after changes
10. **Font warning**: Never use CSS `@import url(...)` for fonts in `globals.css` — this breaks Tailwind v4. Use `next/font/google` in `layout.tsx`.
11. **Keep this file updated**: After each major change, update this ARCUS_PROJECT_CONTEXT.md
