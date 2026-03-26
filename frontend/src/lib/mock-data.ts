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
  'BRK.B': 412.30, 'PFE': 28.90, 'LLY': 782.30,
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
