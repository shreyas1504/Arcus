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
