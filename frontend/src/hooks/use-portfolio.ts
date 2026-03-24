export interface PortfolioConfig {
  holdings: Array<{ ticker: string; shares: string; cost: string }>;
  startDate: string;
  endDate: string;
}

const SAVED_KEY = 'arcus-portfolio';

export function usePortfolioConfig(): PortfolioConfig | null {
  const raw = localStorage.getItem(SAVED_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function portfolioToRequest(config: PortfolioConfig) {
  const filled = config.holdings.filter((h) => h.ticker);
  const n = filled.length;
  if (n === 0) return null;
  return {
    tickers: filled.map((h) => h.ticker),
    weights: filled.map(() => 1 / n),
    start_date: config.startDate,
    end_date: config.endDate,
  };
}
