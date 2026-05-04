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

function normalizeWeights(weights: number[]): number[] {
  const cleaned = weights.map((weight) => (Number.isFinite(weight) && weight > 0 ? weight : 0));
  const total = cleaned.reduce((sum, weight) => sum + weight, 0);
  if (total <= 0) return cleaned;
  return cleaned.map((weight) => weight / total);
}

function sameTickerSet(a: string[], b: string[]) {
  if (a.length !== b.length) return false;
  return a.every((ticker, index) => ticker.toUpperCase() === b[index]?.toUpperCase());
}

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
    const analysisWeightsRaw: number[] = Array.isArray(rawAnalysis?.weights) ? rawAnalysis.weights : [];
    const analysisWeights = normalizeWeights(analysisWeightsRaw.map((weight) => Number(weight) || 0));
    const metrics = rawAnalysis?.metrics || {};
    const latestPrices: Record<string, number> = rawAnalysis?.latest_prices || rawPortfolio?.livePrices || {};

    const portfolioTickers = portfolioHoldings.map((holding) => holding.ticker.toUpperCase());
    const useAnalysisHoldings = analysisTickers.length > 0
      && analysisWeights.length === analysisTickers.length
      && (portfolioTickers.length === 0 || sameTickerSet(analysisTickers, portfolioTickers));

    const holdings = useAnalysisHoldings
      ? analysisTickers.map((ticker, index) => ({
          ticker: ticker.toUpperCase(),
          weight: analysisWeights[index] ?? 1 / analysisTickers.length,
          currentPrice: latestPrices[ticker.toUpperCase()] ?? 0,
        }))
      : portfolioHoldings.map((holding, index) => ({
          ticker: holding.ticker.toUpperCase(),
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
