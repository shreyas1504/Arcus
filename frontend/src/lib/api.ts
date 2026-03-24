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
  return post('/api/chat', {
    message,
    portfolio_context: portfolioContext,
  });
};

export const getPopularTickers = () => get('/api/v2/portfolio/popular-tickers');

export const getDemoPortfolios = () => get('/api/v2/portfolio/demo-portfolios');

export const getSentiment = (ticker: string) => get(`/api/news/sentiment/${ticker}`);
