import type { ChatPortfolioContext } from '@/lib/api';

type HoldingLike = {
  ticker: string;
  shares?: string;
  cost?: string;
};

type SavedPortfolioLike = {
  holdings?: HoldingLike[];
  livePrices?: Record<string, number>;
};

function parsePositiveNumber(value: unknown): number | null {
  const parsed = typeof value === 'number' ? value : parseFloat(String(value ?? ''));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function derivePortfolioWeights(
  holdings: HoldingLike[],
  livePrices?: Record<string, number>,
): number[] {
  const filtered = holdings.filter((holding) => holding.ticker);
  if (!filtered.length) return [];

  const notionals = filtered.map((holding) => {
    const shares = parsePositiveNumber(holding.shares);
    const livePrice = parsePositiveNumber(livePrices?.[holding.ticker.toUpperCase()]);
    const cost = parsePositiveNumber(holding.cost);

    if (shares) return shares * (livePrice ?? cost ?? 1);
    if (livePrice) return livePrice;
    if (cost) return cost;
    return 1;
  });

  const total = notionals.reduce((sum, value) => sum + value, 0);
  if (!Number.isFinite(total) || total <= 0) {
    return filtered.map(() => 1 / filtered.length);
  }

  return notionals.map((value) => value / total);
}

export function buildChatPortfolioContext(): ChatPortfolioContext | undefined {
  try {
    const rawAnalysis = JSON.parse(localStorage.getItem('arcus-last-analysis') || '{}');
    const rawDNA = JSON.parse(localStorage.getItem('arcus-investor-dna') || '{}');
    const rawPortfolio = JSON.parse(localStorage.getItem('arcus-portfolio') || '{}') as SavedPortfolioLike;

    const portfolioHoldings = (rawPortfolio?.holdings || []).filter((holding) => holding?.ticker);
    const portfolioWeights = derivePortfolioWeights(portfolioHoldings, rawPortfolio?.livePrices);

    const analysisTickers: string[] = Array.isArray(rawAnalysis?.tickers) ? rawAnalysis.tickers : [];
    const analysisWeights: number[] = Array.isArray(rawAnalysis?.weights) ? rawAnalysis.weights : [];
    const metrics = rawAnalysis?.metrics || {};
    const latestPrices: Record<string, number> = rawAnalysis?.latest_prices || rawPortfolio?.livePrices || {};

    const holdings = analysisTickers.length > 0
      ? analysisTickers.map((ticker, index) => ({
          ticker,
          weight: analysisWeights[index] ?? 1 / analysisTickers.length,
          currentPrice: latestPrices[ticker] ?? 0,
        }))
      : portfolioHoldings.map((holding, index) => ({
          ticker: holding.ticker,
          weight: portfolioWeights[index] ?? 1 / Math.max(portfolioHoldings.length, 1),
          currentPrice: latestPrices[holding.ticker.toUpperCase()] ?? 0,
        }));

    return {
      holdings,
      metrics: {
        healthScore: metrics.health_score ?? 0,
        sharpe: metrics.sharpe ?? 0,
        var95: metrics.var_95 ?? 0,
        cvar: metrics.cvar_95 ?? 0,
        beta: metrics.beta ?? 1,
        maxDrawdown: metrics.max_drawdown ?? 0,
        annualizedReturn: metrics.annualized_return,
        volatility: metrics.volatility,
        sortino: metrics.sortino,
        alpha: metrics.alpha,
      },
      investorProfile: {
        riskTolerance: rawDNA?.risk_tolerance || 'Moderate',
        targetReturn: rawDNA?.target_return || 0.10,
      },
    };
  } catch {
    return undefined;
  }
}
