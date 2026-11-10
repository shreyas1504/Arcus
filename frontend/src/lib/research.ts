export const RESEARCH_UNIVERSE = new Set([
  'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AVGO',
  'JPM', 'BAC', 'GS', 'MS', 'WFC', 'BRK-B', 'V', 'MA', 'JNJ', 'UNH',
  'LLY', 'PFE', 'MU',
]);

export function supportedPortfolioTickers(
  holdings: Array<{ ticker: string }>,
): string[] {
  return Array.from(new Set(
    holdings
      .map((holding) => holding.ticker.trim().toUpperCase().replace('.', '-'))
      .filter((ticker) => RESEARCH_UNIVERSE.has(ticker)),
  ));
}

