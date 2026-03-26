// ── Per-ticker risk profiles (historical approximations) ──────────────────
// annRet: 3-yr annualised return, vol: annualised volatility, beta: vs S&P500
// var95: typical daily 95% VaR (negative), maxDD: historical max drawdown
export const TICKER_RISK_DB: Record<string, {
  annRet: number; vol: number; beta: number; var95: number; maxDD: number; pe: number;
}> = {
  'AAPL':    { annRet: 0.22,  vol: 0.28,  beta: 1.20, var95: -0.028, maxDD: -0.27, pe: 29 },
  'MSFT':    { annRet: 0.28,  vol: 0.26,  beta: 0.90, var95: -0.025, maxDD: -0.22, pe: 35 },
  'GOOGL':   { annRet: 0.18,  vol: 0.30,  beta: 1.05, var95: -0.030, maxDD: -0.33, pe: 24 },
  'NVDA':    { annRet: 0.52,  vol: 0.58,  beta: 1.75, var95: -0.055, maxDD: -0.66, pe: 65 },
  'AMZN':    { annRet: 0.24,  vol: 0.32,  beta: 1.15, var95: -0.032, maxDD: -0.40, pe: 60 },
  'META':    { annRet: 0.35,  vol: 0.38,  beta: 1.25, var95: -0.038, maxDD: -0.55, pe: 25 },
  'TSLA':    { annRet: 0.28,  vol: 0.72,  beta: 1.90, var95: -0.065, maxDD: -0.74, pe: 55 },
  'AMD':     { annRet: 0.38,  vol: 0.52,  beta: 1.60, var95: -0.050, maxDD: -0.60, pe: 40 },
  'SPY':     { annRet: 0.12,  vol: 0.16,  beta: 1.00, var95: -0.016, maxDD: -0.19, pe: 22 },
  'VOO':     { annRet: 0.12,  vol: 0.16,  beta: 0.99, var95: -0.016, maxDD: -0.19, pe: 22 },
  'QQQ':     { annRet: 0.16,  vol: 0.22,  beta: 1.15, var95: -0.022, maxDD: -0.30, pe: 30 },
  'VTI':     { annRet: 0.11,  vol: 0.17,  beta: 1.00, var95: -0.017, maxDD: -0.20, pe: 21 },
  'IVV':     { annRet: 0.12,  vol: 0.16,  beta: 0.99, var95: -0.016, maxDD: -0.19, pe: 22 },
  'GLD':     { annRet: 0.08,  vol: 0.14,  beta: 0.05, var95: -0.014, maxDD: -0.20, pe: 0  },
  'TLT':     { annRet: -0.04, vol: 0.14,  beta: -0.25,var95: -0.012, maxDD: -0.46, pe: 0  },
  'JPM':     { annRet: 0.18,  vol: 0.24,  beta: 1.10, var95: -0.024, maxDD: -0.26, pe: 12 },
  'BAC':     { annRet: 0.14,  vol: 0.28,  beta: 1.30, var95: -0.028, maxDD: -0.32, pe: 11 },
  'V':       { annRet: 0.20,  vol: 0.22,  beta: 0.95, var95: -0.022, maxDD: -0.23, pe: 30 },
  'MA':      { annRet: 0.20,  vol: 0.22,  beta: 0.95, var95: -0.022, maxDD: -0.24, pe: 35 },
  'JNJ':     { annRet: 0.06,  vol: 0.14,  beta: 0.55, var95: -0.014, maxDD: -0.18, pe: 15 },
  'UNH':     { annRet: 0.16,  vol: 0.20,  beta: 0.65, var95: -0.020, maxDD: -0.22, pe: 22 },
  'LLY':     { annRet: 0.45,  vol: 0.30,  beta: 0.40, var95: -0.028, maxDD: -0.22, pe: 55 },
  'XOM':     { annRet: 0.15,  vol: 0.24,  beta: 0.85, var95: -0.024, maxDD: -0.42, pe: 14 },
  'CVX':     { annRet: 0.14,  vol: 0.22,  beta: 0.80, var95: -0.022, maxDD: -0.40, pe: 14 },
  'COST':    { annRet: 0.22,  vol: 0.22,  beta: 0.75, var95: -0.022, maxDD: -0.20, pe: 50 },
  'WMT':     { annRet: 0.18,  vol: 0.18,  beta: 0.55, var95: -0.018, maxDD: -0.18, pe: 28 },
  'KO':      { annRet: 0.06,  vol: 0.14,  beta: 0.55, var95: -0.014, maxDD: -0.18, pe: 23 },
  'PG':      { annRet: 0.08,  vol: 0.14,  beta: 0.50, var95: -0.014, maxDD: -0.17, pe: 25 },
  'NFLX':    { annRet: 0.30,  vol: 0.44,  beta: 1.30, var95: -0.040, maxDD: -0.55, pe: 40 },
  'DIS':     { annRet: -0.04, vol: 0.28,  beta: 1.10, var95: -0.028, maxDD: -0.45, pe: 70 },
  'NEE':     { annRet: 0.06,  vol: 0.18,  beta: 0.55, var95: -0.018, maxDD: -0.30, pe: 18 },
  'PLTR':    { annRet: 0.22,  vol: 0.60,  beta: 1.85, var95: -0.058, maxDD: -0.72, pe: 80 },
  'COIN':    { annRet: 0.40,  vol: 0.90,  beta: 2.10, var95: -0.082, maxDD: -0.80, pe: 30 },
  'ARKK':    { annRet: -0.10, vol: 0.58,  beta: 1.70, var95: -0.052, maxDD: -0.80, pe: 0  },
  'GS':      { annRet: 0.18,  vol: 0.26,  beta: 1.30, var95: -0.026, maxDD: -0.30, pe: 12 },
  'BLK':     { annRet: 0.16,  vol: 0.24,  beta: 1.15, var95: -0.024, maxDD: -0.28, pe: 20 },
};

const DEFAULT_RISK = { annRet: 0.12, vol: 0.22, beta: 1.00, var95: -0.022, maxDD: -0.25, pe: 20 };

/**
 * Compute realistic portfolio metrics from user's actual tickers + equal weights.
 * Used when the backend API is unavailable (GitHub Pages deployment).
 */
export const computePortfolioMetrics = (
  tickers: string[],
  sharesOrWeights?: number[],
  riskFreeRate = 0.05,
) => {
  if (tickers.length === 0) return MOCK_PORTFOLIO.metrics;

  // Normalise weights (equal if not provided)
  const rawW = sharesOrWeights && sharesOrWeights.length === tickers.length
    ? sharesOrWeights : tickers.map(() => 1);
  const totalW = rawW.reduce((a, b) => a + b, 0);
  const w = rawW.map(x => x / totalW);

  // Weighted portfolio metrics
  const pRet  = tickers.reduce((s, t, i) => s + w[i] * (TICKER_RISK_DB[t] ?? DEFAULT_RISK).annRet, 0);
  const pVol  = tickers.reduce((s, t, i) => s + w[i] * (TICKER_RISK_DB[t] ?? DEFAULT_RISK).vol, 0);
  const pBeta = tickers.reduce((s, t, i) => s + w[i] * (TICKER_RISK_DB[t] ?? DEFAULT_RISK).beta, 0);
  const pVar  = tickers.reduce((s, t, i) => s + w[i] * (TICKER_RISK_DB[t] ?? DEFAULT_RISK).var95, 0);
  const pDD   = tickers.reduce((s, t, i) => s + w[i] * (TICKER_RISK_DB[t] ?? DEFAULT_RISK).maxDD, 0);
  const pPE   = tickers.reduce((s, t, i) => s + w[i] * (TICKER_RISK_DB[t] ?? DEFAULT_RISK).pe, 0);

  // Diversification benefit: more tickers → lower actual vol vs sum-of-weights
  const divFactor = Math.max(0.65, 1 - (tickers.length - 1) * 0.06);
  const adjVol = pVol * divFactor;
  const adjVar = pVar * (divFactor * 0.9);
  const adjDD  = pDD  * (divFactor * 0.92);

  // Derived metrics
  const rf = riskFreeRate;
  const sharpe            = adjVol > 0 ? (pRet - rf) / adjVol : 0;
  const sortino           = Math.abs(adjVar) > 0 ? (pRet - rf) / Math.abs(adjVar * Math.sqrt(252)) : 0;
  const alpha             = pRet - (rf + pBeta * 0.07);   // market premium 7%
  const information_ratio = Math.min(1.5, Math.max(-1, alpha / Math.max(0.01, adjVol * 0.4)));
  const calmar            = Math.abs(adjDD) > 0 ? pRet / Math.abs(adjDD) : 0;
  const cvar_95           = adjVar * 1.45;

  // Concentration penalty for very few tickers
  const concentrationPenalty = tickers.length < 3 ? 0.85 : tickers.length < 5 ? 0.92 : 1.0;

  const health_score = Math.round(
    Math.min(100, Math.max(0,
      Math.min(100, (sharpe / 2.0) * 100) * 0.40 +
      Math.min(100, Math.max(0, 100 - (Math.abs(adjVar) * 100 - 2) * (100 / 6))) * 0.30 +
      Math.min(100, Math.max(0, 100 - (adjVol * 100 - 10) * (100 / 30))) * 0.20 +
      Math.min(100, Math.max(0, 100 - (Math.abs(adjDD) * 100 - 5) * (100 / 35))) * 0.10
    ) * concentrationPenalty
  ));

  return {
    sharpe:            Math.round(sharpe * 100) / 100,
    sortino:           Math.round(Math.min(4, sortino) * 100) / 100,
    alpha:             Math.round(alpha * 1000) / 1000,
    information_ratio: Math.round(information_ratio * 100) / 100,
    calmar:            Math.round(calmar * 100) / 100,
    var_95:            Math.round(adjVar * 1000) / 1000,
    cvar_95:           Math.round(cvar_95 * 1000) / 1000,
    max_drawdown:      Math.round(adjDD * 1000) / 1000,
    beta:              Math.round(pBeta * 100) / 100,
    annualized_return: Math.round(pRet * 1000) / 1000,
    volatility:        Math.round(adjVol * 1000) / 1000,
    health_score,
    weighted_pe:       Math.round(pPE * 10) / 10,
    weighted_ps:       0,
  };
};

export const MOCK_PORTFOLIO = {
  tickers: ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'VOO'],
  weights: [0.25, 0.20, 0.20, 0.15, 0.20],
  metrics: {
    sharpe: 1.84,
    sortino: 2.31,
    alpha: 0.043,
    information_ratio: 0.71,
    calmar: 1.22,
    var_95: -0.032,
    cvar_95: -0.048,
    max_drawdown: -0.184,
    beta: 0.93,
    annualized_return: 0.187,
    volatility: 0.142,
    health_score: 78,
    weighted_pe: 28.4,
    weighted_ps: 6.2,
  },
  pnl: [
    { ticker: 'AAPL', shares: 15, cost_basis: 148.20, current_price: 182.63, days: 420 },
    { ticker: 'NVDA', shares: 5, cost_basis: 620.00, current_price: 875.40, days: 310 },
    { ticker: 'MSFT', shares: 8, cost_basis: 320.00, current_price: 378.91, days: 380 },
    { ticker: 'GOOGL', shares: 12, cost_basis: 132.50, current_price: 165.22, days: 290 },
    { ticker: 'VOO', shares: 40, cost_basis: 388.00, current_price: 465.18, days: 500 },
  ],
};


export const MOCK_PERFORMANCE_DATA = Array.from({ length: 60 }, (_, i) => {
  const base = 10000;
  const portfolioGrowth = base * (1 + 0.003 * i + Math.sin(i * 0.3) * 200);
  const benchmarkGrowth = base * (1 + 0.002 * i + Math.sin(i * 0.25) * 150);
  return {
    date: new Date(2023, 0, 1 + i * 6).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    portfolio: Math.round(portfolioGrowth),
    benchmark: Math.round(benchmarkGrowth),
  };
});

export const MOCK_ROLLING_SHARPE = Array.from({ length: 50 }, (_, i) => ({
  date: new Date(2023, 0, 1 + i * 7).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  sharpe: 1.2 + Math.sin(i * 0.2) * 0.8 + Math.random() * 0.3,
}));

export const MOCK_DRAWDOWN = Array.from({ length: 60 }, (_, i) => {
  const val = -Math.abs(Math.sin(i * 0.15) * 0.15 + Math.sin(i * 0.4) * 0.05);
  return {
    date: new Date(2023, 0, 1 + i * 6).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    drawdown: Math.round(val * 1000) / 1000,
  };
});

export const MOCK_MONTE_CARLO = Array.from({ length: 30 }, (_, i) => {
  const base = 100000;
  const t = i / 29;
  return {
    month: `M${i + 1}`,
    p10: Math.round(base * (1 + t * 0.02 - 0.08 * t)),
    p25: Math.round(base * (1 + t * 0.06)),
    p50: Math.round(base * (1 + t * 0.12)),
    p75: Math.round(base * (1 + t * 0.18)),
    p90: Math.round(base * (1 + t * 0.28)),
  };
});

export const MOCK_RISK_ATTRIBUTION = [
  { ticker: 'NVDA', contribution: 34.2, color: '#F0514F' },
  { ticker: 'AAPL', contribution: 24.8, color: '#38BDA4' },
  { ticker: 'MSFT', contribution: 18.1, color: '#38BDA4' },
  { ticker: 'GOOGL', contribution: 13.4, color: '#38BDA4' },
  { ticker: 'VOO', contribution: 9.5, color: '#38BDA4' },
];

export const MOCK_CORRELATION = {
  tickers: ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'VOO'],
  matrix: [
    [1.00, 0.72, 0.81, 0.76, 0.88],
    [0.72, 1.00, 0.68, 0.65, 0.71],
    [0.81, 0.68, 1.00, 0.79, 0.85],
    [0.76, 0.65, 0.79, 1.00, 0.82],
    [0.88, 0.71, 0.85, 0.82, 1.00],
  ],
};

export const MOCK_SECTORS = [
  { name: 'Technology', value: 65, color: '#38BDA4' },
  { name: 'Index Fund', value: 20, color: '#4F9CF0' },
  { name: 'Communication', value: 15, color: '#F0A44F' },
];

export const MOCK_EFFICIENT_FRONTIER = Array.from({ length: 40 }, (_, i) => ({
  volatility: 8 + Math.random() * 20,
  return: 4 + Math.random() * 18,
  type: 'random' as 'random' | 'current' | 'optimal',
})).concat([
  { volatility: 14.2, return: 18.7, type: 'current' as 'random' | 'current' | 'optimal' },
  { volatility: 11.8, return: 19.2, type: 'optimal' as 'random' | 'current' | 'optimal' },
]);

export const MOCK_STRESS_TESTS = [
  { name: '2008 FINANCIAL CRISIS', loss: -38.4, recoveryDays: 512 },
  { name: '2020 COVID CRASH', loss: -23.1, recoveryDays: 148 },
  { name: '2022 RATE HIKE', loss: -18.7, recoveryDays: 287 },
  { name: '2000 DOT-COM BUST', loss: -44.2, recoveryDays: 1024 },
];

export const MOCK_OPTIMAL_WEIGHTS = {
  max_sharpe: {
    label: 'Max Sharpe',
    sharpe: 2.14,
    weights: [
      { ticker: 'AAPL', weight: 0.30 },
      { ticker: 'NVDA', weight: 0.15 },
      { ticker: 'MSFT', weight: 0.25 },
      { ticker: 'GOOGL', weight: 0.10 },
      { ticker: 'VOO', weight: 0.20 },
    ],
    recommended: true,
  },
  momentum: {
    label: 'Momentum',
    sharpe: 1.92,
    weights: [
      { ticker: 'AAPL', weight: 0.20 },
      { ticker: 'NVDA', weight: 0.35 },
      { ticker: 'MSFT', weight: 0.20 },
      { ticker: 'GOOGL', weight: 0.05 },
      { ticker: 'VOO', weight: 0.20 },
    ],
    recommended: false,
  },
  risk_parity: {
    label: 'Risk Parity',
    sharpe: 1.68,
    weights: [
      { ticker: 'AAPL', weight: 0.22 },
      { ticker: 'NVDA', weight: 0.12 },
      { ticker: 'MSFT', weight: 0.22 },
      { ticker: 'GOOGL', weight: 0.18 },
      { ticker: 'VOO', weight: 0.26 },
    ],
    recommended: false,
  },
};

export const MOCK_AI_RECOMMENDATIONS = [
  "Your NVDA position contributes 34.2% of total portfolio risk despite being only 20% of weight. Consider trimming to 15% for better risk-adjusted returns.",
  "Portfolio Sharpe of 1.84 is strong, but concentration in tech (65%) creates sector-specific tail risk. Adding 10% allocation to healthcare could improve diversification.",
  "Current beta of 0.93 is well-aligned with your Growth risk profile. VaR suggests max daily loss of 3.2% at 95% confidence.",
  "Monte Carlo simulation shows 82% probability of achieving your 15% annual return target over the next 12 months.",
];

// Ticker → Sector mapping for offline sector alignment detection
export const TICKER_SECTOR_MAP: Record<string, string> = {
  // Technology
  'AAPL': 'Technology', 'MSFT': 'Technology', 'NVDA': 'Technology', 'GOOGL': 'Technology',
  'CRM': 'Technology',  'ADBE': 'Technology',  'AMD': 'Technology',  'INTC': 'Technology',
  'IBM': 'Technology',  'ORCL': 'Technology',  'PLTR': 'Technology', 'SNOW': 'Technology',
  // Healthcare
  'UNH': 'Healthcare',  'JNJ': 'Healthcare',  'PFE': 'Healthcare',  'ABBV': 'Healthcare',
  'TMO': 'Healthcare',  'MRK': 'Healthcare',  'LLY': 'Healthcare',
  // Energy
  'XOM': 'Energy',  'CVX': 'Energy',  'COP': 'Energy',  'SLB': 'Energy',
  'EOG': 'Energy',  'MPC': 'Energy',
  // Financials
  'JPM': 'Financials', 'V': 'Financials',   'MA': 'Financials',  'BAC': 'Financials',
  'GS': 'Financials',  'MS': 'Financials',  'BLK': 'Financials', 'BRK.B': 'Financials',
  'PYPL': 'Financials', 'COIN': 'Financials',
  // Consumer
  'AMZN': 'Consumer', 'TSLA': 'Consumer', 'HD': 'Consumer',   'NKE': 'Consumer',
  'SBUX': 'Consumer', 'MCD': 'Consumer',  'WMT': 'Consumer',  'COST': 'Consumer',
  'KO': 'Consumer',   'PEP': 'Consumer',  'PG': 'Consumer',   'DIS': 'Consumer',
  'NFLX': 'Consumer', 'UBER': 'Consumer', 'SPOT': 'Consumer', 'SHOP': 'Consumer',
  // Real Estate
  'AMT': 'Real Estate', 'PLD': 'Real Estate', 'CCI': 'Real Estate',
  'SPG': 'Real Estate', 'O': 'Real Estate',   'WELL': 'Real Estate',
  // Utilities
  'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities',
  'D': 'Utilities',   'AEP': 'Utilities', 'SRE': 'Utilities',
};

// Static price snapshot used for offline P&L calculation (mirrors StockSearch STOCK_DB)
export const MOCK_STOCK_PRICES: Record<string, number> = {
  'AAPL': 182.63, 'MSFT': 378.91, 'GOOGL': 165.22, 'AMZN': 178.25, 'NVDA': 875.40,
  'META': 485.39, 'TSLA': 248.42, 'JPM': 198.45, 'JNJ': 156.78, 'V': 278.90,
  'UNH': 492.15, 'XOM': 108.45, 'WMT': 165.34, 'MA': 458.90, 'PG': 158.90,
  'LLY': 782.30, 'HD': 345.67, 'CVX': 155.20, 'MRK': 125.40, 'ABBV': 168.90,
  'COST': 725.80, 'KO': 60.45, 'PEP': 172.30, 'AMD': 165.23, 'INTC': 31.45,
  'NFLX': 628.90, 'DIS': 98.45, 'ADBE': 478.60, 'CRM': 265.40, 'PYPL': 62.30,
  'UBER': 72.45, 'SPOT': 285.60, 'SHOP': 78.90, 'SQ': 68.20, 'PLTR': 22.80,
  'SNOW': 162.30, 'COIN': 225.40, 'SPY': 512.40, 'QQQ': 438.92, 'VOO': 465.18,
  'VTI': 245.60, 'IVV': 510.20, 'GLD': 218.90, 'TLT': 92.30, 'ARKK': 48.90,
  'BTC-USD': 67420.00, 'ETH-USD': 3520.00, 'BA': 215.60, 'CAT': 328.90,
  'GS': 425.60, 'MS': 92.30, 'IBM': 185.40, 'ORCL': 125.60, 'T': 17.20,
  'VZ': 38.90, 'NKE': 98.45, 'SBUX': 92.30, 'MCD': 285.60, 'PFE': 28.90,
  'TMO': 565.40, 'BAC': 38.20, 'BLK': 825.40, 'COP': 112.30, 'SLB': 46.80,
  'EOG': 128.50, 'MPC': 178.90, 'NEE': 73.20, 'DUK': 101.50, 'SO': 82.30,
  'D': 45.60, 'AEP': 94.20, 'SRE': 72.80, 'AMT': 185.40, 'PLD': 112.60,
  'CCI': 98.30, 'SPG': 152.40, 'O': 54.20, 'WELL': 98.70,
  'BRK.B': 412.30,
};

export const MOCK_SPARKLINES: Record<string, number[]> = {
  sharpe: [1.2, 1.4, 1.6, 1.5, 1.7, 1.8, 1.84],
  sortino: [1.8, 2.0, 1.9, 2.1, 2.2, 2.3, 2.31],
  alpha: [0.02, 0.03, 0.035, 0.04, 0.038, 0.042, 0.043],
  var_95: [-0.04, -0.038, -0.035, -0.033, -0.031, -0.032, -0.032],
  cvar_95: [-0.06, -0.055, -0.052, -0.05, -0.049, -0.048, -0.048],
  max_drawdown: [-0.22, -0.20, -0.19, -0.185, -0.184, -0.184, -0.184],
  beta: [0.98, 0.96, 0.95, 0.94, 0.93, 0.93, 0.93],
  annualized_return: [0.12, 0.14, 0.15, 0.16, 0.17, 0.18, 0.187],
};
