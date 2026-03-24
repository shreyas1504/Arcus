// In production (GitHub Pages), use Render backend; locally, use localhost
const BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://arcus-backend.onrender.com';

// ── Types ────────────────────────────────────────────────────────────────
export interface PortfolioRequest {
  tickers: string[];
  weights: number[];
  start_date: string;
  end_date: string;
}

export interface MonteCarloRequest extends PortfolioRequest {
  n_days: number;
  n_simulations: number;
  initial_value: number;
}

// ── Helpers ──────────────────────────────────────────────────────────────
async function post(path: string, body: object) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new Error(`${path} failed: ${res.status} — ${text}`);
  }
  return res.json();
}

async function get(path: string) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

// ── Portfolio endpoints (v2 adapter) ─────────────────────────────────────
export const analyzePortfolio = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/analyze', req);

export const optimizePortfolio = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/optimize', req);

export const runMonteCarlo = (req: MonteCarloRequest) =>
  post('/api/v2/portfolio/monte-carlo', req);

export const runStressTest = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/stress-test', req);

export const getEfficientFrontier = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/efficient-frontier', req);

export const getRecommendations = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/recommendations', req);

// ── Non-portfolio endpoints ──────────────────────────────────────────────
export const getMarketNews = () => get('/api/news/market');

export const sendChatMessage = async (message: string, portfolioContext?: object) => {
  try {
    return await post('/api/chat', {
      message,
      portfolio_context: portfolioContext,
    });
  } catch {
    // Offline fallback — smart pre-built responses when backend is unavailable
    return { reply: getOfflineResponse(message) };
  }
};

export const getPopularTickers = () => get('/api/v2/portfolio/popular-tickers');

export const getDemoPortfolios = () => get('/api/v2/portfolio/demo-portfolios');

export const getSentiment = (ticker: string) => get(`/api/news/sentiment/${ticker}`);

// ── Offline AI fallback ──────────────────────────────────────────────────
// Provides intelligent pre-built responses when backend is unreachable
function getOfflineResponse(message: string): string {
  const msg = message.toLowerCase();

  if (msg.includes('sharpe') || msg.includes('ratio')) {
    return "**Sharpe Ratio** measures risk-adjusted return — how much return you're getting per unit of risk.\n\n• **Above 1.0** — Good. You're being compensated for the risk.\n• **Above 2.0** — Excellent. Institutional-quality returns.\n• **Below 0** — A savings account would have beaten you.\n\nIt's calculated as: (Portfolio Return − Risk-Free Rate) ÷ Portfolio Volatility, annualised. The risk-free rate used is typically the 10-year Treasury yield (~4%).";
  }

  if (msg.includes('risk') || msg.includes('var') || msg.includes('volatility')) {
    return "**Portfolio Risk** comes in several flavours:\n\n• **Value at Risk (VaR 95%)** — The worst daily loss you'd expect 95% of the time. If VaR is -2.3%, on the worst 1-in-20 days, you'd lose at least 2.3%.\n• **Annualised Volatility** — How much your portfolio swings over a year. Below 15% is conservative, above 25% is aggressive.\n• **Max Drawdown** — The deepest peak-to-trough loss. This is the gut-check number.\n\nDiversification across uncorrelated assets is the primary tool for reducing portfolio risk.";
  }

  if (msg.includes('stress') || msg.includes('crash') || msg.includes('crisis')) {
    return "**Stress Testing** estimates how your portfolio would perform under historical crash scenarios:\n\n• **2008 Financial Crisis** — S&P 500 fell ~57% over 17 months\n• **2020 COVID Crash** — 34% drop in just 33 days, recovered in ~90 days\n• **2000 Dot-Com Bust** — 49% decline, took ~6 years to recover\n• **2022 Rate Hike** — 25% decline driven by aggressive Fed tightening\n\nYour estimated loss is calculated using your portfolio's **beta** × the benchmark loss. Higher beta = larger estimated losses.";
  }

  if (msg.includes('sector') || msg.includes('diversif') || msg.includes('allocation')) {
    return "**Sector Diversification** is crucial for risk management:\n\n• Aim for exposure across **4+ sectors** to avoid concentration risk\n• If any single sector exceeds **40%** of your portfolio, you're making a concentrated bet\n• Tech-heavy portfolios (common with FAANG stocks) tend to be highly correlated — they move together\n\nThe **Diversification Score** (0-100) measures average pairwise correlation. Above 65 = well diversified. Below 40 = most stocks are making the same bet.";
  }

  if (msg.includes('monte carlo') || msg.includes('simulat') || msg.includes('future') || msg.includes('predict')) {
    return "**Monte Carlo Simulation** projects possible futures for your portfolio:\n\n• Uses **Geometric Brownian Motion (GBM)** — the same model behind Black-Scholes option pricing\n• Runs 300+ independent paths based on your portfolio's historical drift and volatility\n• The **median line** shows the expected outcome\n• The **5th-95th percentile band** shows the range of likely scenarios\n\nKey insight: wider bands = more uncertainty = higher risk. If the 5th percentile is below your initial investment, there's a real chance of loss.";
  }

  if (msg.includes('beta')) {
    return "**Beta** measures how your portfolio amplifies market movements:\n\n• **Beta = 1.0** — Moves exactly with the S&P 500\n• **Beta > 1.0** — More volatile than the market (e.g., 1.3 means a 10% market drop hits you ~13%)\n• **Beta < 1.0** — More defensive (utilities, healthcare tend to have lower beta)\n\nBeta is computed by regressing your portfolio returns against S&P 500 daily returns. It's a key input for stress testing.";
  }

  if (msg.includes('rebalanc') || msg.includes('optim') || msg.includes('weight')) {
    return "**Portfolio Optimisation** finds the allocation that historically maximised risk-adjusted return:\n\n• Uses **Sharpe Maximisation** via constrained optimisation (SciPy SLSQP solver)\n• Constraints: long-only (no shorting), weights sum to 100%\n• The **Efficient Frontier** chart shows random portfolios plotted on a risk-return map\n• Your current allocation vs the optimal allocation are highlighted\n\n⚠️ The optimal weights are backward-looking — they show what *would have been* best historically, not a guarantee of future performance.";
  }

  if (msg.includes('health') || msg.includes('score')) {
    return "**Portfolio Health Score (0-100)** is a weighted composite of four risk metrics:\n\n• **Sharpe Ratio** (40 points) — Risk-adjusted return quality\n• **Value at Risk** (25 points) — Downside risk exposure\n• **Volatility** (20 points) — Overall price swing magnitude\n• **Concentration** (15 points) — Diversification of holdings\n\nScoring: **70+** = Healthy (green), **40-70** = Needs attention (yellow), **Below 40** = Concern (red).";
  }

  // Default response
  return "I'm **Arcus AI**, your portfolio analytics assistant. I can explain any metric you see on the dashboard.\n\nTry asking about:\n• **Sharpe Ratio** — Risk-adjusted returns\n• **Portfolio Risk** — VaR, volatility, drawdowns\n• **Stress Testing** — Historical crash scenarios\n• **Monte Carlo** — Future projections\n• **Sector Diversification** — Concentration analysis\n• **Health Score** — Overall portfolio quality\n\n💡 *For live AI-powered analysis with Claude, run the backend locally with `uvicorn backend.main:app --port 8000`*";
}
