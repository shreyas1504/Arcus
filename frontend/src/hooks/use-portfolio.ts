export interface PortfolioConfig {
  holdings: Array<{ ticker: string; shares: string; cost: string }>;
  startDate: string;
  endDate: string;
  livePrices?: Record<string, number>;
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

export function portfolioToRequest(
  config: PortfolioConfig,
  settings?: { riskFreeRate?: number; benchmark?: string },
) {
  const filled = config.holdings.filter((h) => h.ticker);
  const n = filled.length;
  if (n === 0) return null;
  const notionals = filled.map((holding) => {
    const shares = parseFloat(holding.shares);
    const livePrice = config.livePrices?.[holding.ticker.toUpperCase()];
    const cost = parseFloat(holding.cost);

    if (Number.isFinite(shares) && shares > 0) {
      const price = Number.isFinite(livePrice) && livePrice > 0
        ? livePrice
        : Number.isFinite(cost) && cost > 0
          ? cost
          : 1;
      return shares * price;
    }

    if (Number.isFinite(livePrice) && livePrice > 0) return livePrice;
    if (Number.isFinite(cost) && cost > 0) return cost;
    return 1;
  });
  const totalNotional = notionals.reduce((sum, value) => sum + value, 0);
  const weights = totalNotional > 0
    ? notionals.map((value) => value / totalNotional)
    : filled.map(() => 1 / n);

  return {
    tickers: filled.map((h) => h.ticker),
    weights,
    start_date: config.startDate,
    end_date: config.endDate,
    ...(settings?.riskFreeRate !== undefined && { risk_free_rate: settings.riskFreeRate }),
    ...(settings?.benchmark && { benchmark: settings.benchmark }),
  };
}
