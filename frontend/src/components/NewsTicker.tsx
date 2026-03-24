import { useQuery } from '@tanstack/react-query';
import { getMarketNews } from '@/lib/api';

const FALLBACK_NEWS = [
  { type: 'ticker' as const, symbol: 'AAPL', change: '+1.24%', positive: true },
  { type: 'ticker' as const, symbol: 'NVDA', change: '-0.83%', positive: false },
  { type: 'headline' as const, text: 'Fed holds rates steady at 5.25%' },
  { type: 'ticker' as const, symbol: 'MSFT', change: '+0.61%', positive: true },
  { type: 'headline' as const, text: 'S&P 500 rises 0.41% on tech gains' },
  { type: 'ticker' as const, symbol: 'TSLA', change: '-2.14%', positive: false },
  { type: 'ticker' as const, symbol: 'BTC', change: '$67,420', positive: true },
  { type: 'headline' as const, text: 'Nvidia earnings beat estimates by 18%' },
  { type: 'ticker' as const, symbol: 'SPY', change: '+0.38%', positive: true },
  { type: 'headline' as const, text: '10-year Treasury yield falls to 4.21%' },
  { type: 'ticker' as const, symbol: 'AMZN', change: '+0.94%', positive: true },
  { type: 'headline' as const, text: 'Oil rises 1.2% on OPEC output cut' },
  { type: 'ticker' as const, symbol: 'GOOGL', change: '+1.12%', positive: true },
  { type: 'headline' as const, text: 'Gold hits $2,340 all-time high' },
];

const TickerContent = ({ items }: { items: typeof FALLBACK_NEWS }) => (
  <div className="flex items-center gap-0 whitespace-nowrap">
    {items.map((item, i) => (
      <span key={i} className="flex items-center gap-1.5 mx-3">
        {item.type === 'ticker' ? (
          <>
            <span className="font-mono text-[11px] text-primary">{item.symbol}</span>
            <span className={`font-mono text-[11px] ${item.positive ? 'text-signal-green' : 'text-signal-red'}`}>{item.change}</span>
          </>
        ) : (
          <span className="font-mono text-[11px] text-muted-foreground">{item.text}</span>
        )}
        <span className="text-primary text-[11px] ml-1.5">·</span>
      </span>
    ))}
  </div>
);

const NewsTicker = () => {
  const { data: liveNews } = useQuery({
    queryKey: ['news-market'],
    queryFn: getMarketNews,
    refetchInterval: 5 * 60 * 1000,
    staleTime: 5 * 60 * 1000,
  });

  // Map live API news to display format, fall back to hardcoded
  let displayItems = FALLBACK_NEWS;
  try {
    if (liveNews) {
      const newsArray = Array.isArray(liveNews) ? liveNews : (liveNews as any)?.news;
      if (Array.isArray(newsArray) && newsArray.length > 0) {
        displayItems = newsArray.map((item: any) => ({
          type: 'headline' as const,
          text: item.headline || item.title || '',
          symbol: undefined as string | undefined,
          change: undefined as string | undefined,
          positive: undefined as boolean | undefined,
        }));
      }
    }
  } catch {
    // Fallback to hardcoded on any parsing error
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-[60] h-9 flex items-center overflow-hidden"
      style={{ background: '#0D1117', borderBottom: '1px solid rgba(56,189,148,0.2)' }}
    >
      {/* LIVE badge — fixed left */}
      <div className="flex-shrink-0 w-20 flex items-center gap-1.5 px-3 h-full z-10">
        <span className="w-1.5 h-1.5 rounded-full bg-signal-red animate-[pulse-dot_1.5s_ease-in-out_infinite]" />
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-signal-red font-medium">LIVE</span>
      </div>

      {/* Scrolling content */}
      <div className="flex-1 overflow-hidden">
        <div className="flex animate-[marquee_90s_linear_infinite] hover:[animation-play-state:paused]" style={{ width: 'max-content' }}>
          <TickerContent items={displayItems as typeof FALLBACK_NEWS} />
          <TickerContent items={displayItems as typeof FALLBACK_NEWS} />
        </div>
      </div>

      {/* Markets label — fixed right */}
      <div className="flex-shrink-0 w-20 flex items-center justify-center h-full z-10">
        <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Markets</span>
      </div>
    </div>
  );
};

export default NewsTicker;
