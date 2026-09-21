import { useQuery } from '@tanstack/react-query';
import { getSentiment } from '@/lib/api';

export interface Sentiment {
  ticker: string;
  score: number;
  label: 'BULLISH' | 'NEUTRAL' | 'BEARISH';
  confidence: number;
  headline_count: number;
}

const LABEL_STYLES: Record<Sentiment['label'], string> = {
  BULLISH: 'text-signal-green border-signal-green/40 bg-signal-green/10',
  NEUTRAL: 'text-muted-foreground border-border bg-card-elevated/50',
  BEARISH: 'text-signal-red border-signal-red/40 bg-signal-red/10',
};

/**
 * Renders the VADER headline sentiment for one ticker.
 * Exported separately from the query so it can be unit tested without a network layer.
 */
export const SentimentPill = ({ sentiment }: { sentiment: Sentiment }) => {
  const style = LABEL_STYLES[sentiment.label] ?? LABEL_STYLES.NEUTRAL;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] font-medium whitespace-nowrap ${style}`}
      title={`${sentiment.headline_count} headline${sentiment.headline_count === 1 ? '' : 's'} · score ${sentiment.score.toFixed(2)}`}
    >
      {sentiment.label}
      <span className="opacity-70">{sentiment.headline_count}</span>
    </span>
  );
};

const SentimentBadge = ({ ticker }: { ticker: string }) => {
  const { data, isLoading, isError } = useQuery<Sentiment>({
    queryKey: ['sentiment', ticker],
    queryFn: () => getSentiment(ticker),
    enabled: !!ticker,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  if (isLoading) {
    return <span data-testid="sentiment-loading" className="inline-block h-4 w-16 rounded-full shimmer align-middle" />;
  }

  // No invented sentiment: a failed feed or a ticker with no headlines shows an em dash.
  if (isError || !data || data.headline_count === 0) {
    return <span className="font-mono text-[10px] text-muted-foreground">—</span>;
  }

  return <SentimentPill sentiment={data} />;
};

export default SentimentBadge;
