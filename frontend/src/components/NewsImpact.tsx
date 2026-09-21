import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Newspaper } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine, LabelList } from 'recharts';
import { getEventImpact } from '@/lib/api';

// ── Types mirroring POST /api/news/event-impact ──────────────────────────
export interface EventRow {
  ticker: string;
  date: string;
  announced: string;
  abnormal_return: number;
  volatility_change: number;
  volume_spike: number;
}

export interface EventSummary {
  n_events: number;
  mean_abnormal_return: number;
  median_abnormal_return: number;
  mean_abs_abnormal_return: number;
  positive_share: number;
  mean_volume_spike: number;
  mean_volatility_change: number;
}

export interface Headline {
  id?: string;
  headline: string;
  source?: string;
  url?: string;
  category?: string;
}

export interface EventImpact {
  tickers_analyzed: string[];
  events: EventRow[];
  by_ticker: Record<string, EventSummary>;
  overall: EventSummary | null;
  skipped_count: number;
  methodology: string;
  headlines_by_category?: Record<string, Headline[]>;
}

export const METHODOLOGY_FALLBACK =
  'Earnings event study, window day -1 to +3, abnormal return vs SPY, data from Yahoo Finance';

const POSITIVE = '#3eb680'; // --signal-green
const NEGATIVE = '#f05451'; // --signal-red
const AXIS_INK = '#8B949E';
const CATEGORY_ORDER = ['EARNINGS', 'POLICY', 'GEOPOLITICAL', 'OTHER'];

// ── Formatting ───────────────────────────────────────────────────────────
// Exported so the numbers on screen are covered by tests rather than by eye.

/** Signed percentage, e.g. 0.0512 -> "+5.1%". */
export const formatSignedPercent = (value: number, digits = 1): string => {
  if (!Number.isFinite(value)) return '—';
  const pct = value * 100;
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(digits)}%`;
};

/** Unsigned percentage, e.g. 0.0857 -> "8.6%". */
export const formatPercent = (value: number, digits = 1): string =>
  Number.isFinite(value) ? `${(value * 100).toFixed(digits)}%` : '—';

/** Volume multiple, e.g. 2.839 -> "2.8x". */
export const formatMultiple = (value: number): string =>
  Number.isFinite(value) ? `${value.toFixed(1)}x` : '—';

/** Most recent event for each ticker, newest first. */
export const latestEventPerTicker = (events: EventRow[]): EventRow[] => {
  const latest = new Map<string, EventRow>();
  for (const event of events) {
    const current = latest.get(event.ticker);
    if (!current || event.date > current.date) latest.set(event.ticker, event);
  }
  return [...latest.values()].sort((a, b) => b.date.localeCompare(a.date));
};

/** Average abnormal return per ticker, largest absolute move first. */
export const abnormalReturnByTicker = (byTicker: Record<string, EventSummary>) =>
  Object.entries(byTicker)
    .map(([ticker, summary]) => ({
      ticker,
      value: summary.mean_abnormal_return * 100,
      n: summary.n_events,
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

// ── Pieces ───────────────────────────────────────────────────────────────

const Tile = ({ label, value, hint }: { label: string; value: string; hint?: string }) => (
  <div className="glass rounded-xl p-4">
    <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{label}</span>
    <div className="font-mono text-[22px] font-bold text-foreground mt-1">{value}</div>
    {hint && <div className="font-mono text-[10px] text-muted-foreground mt-0.5">{hint}</div>}
  </div>
);

/**
 * Direct value label per bar. Green and red separate poorly for deuteranopia
 * (CVD dE 6.4), so every bar carries its signed number as well as its colour.
 * Two label lists — Recharts anchors "top" above a bar and "bottom" below it,
 * so positive and negative bars each get a label on the outside.
 */
const barLabel = (side: 'positive' | 'negative') => (props: LabelProps) => {
  const value = Number(props.value);
  if (!Number.isFinite(value)) return null;
  if (side === 'positive' ? value < 0 : value >= 0) return null;
  return (
    <text
      x={Number(props.x)}
      y={Number(props.y) + (side === 'positive' ? -5 : 11)}
      textAnchor="middle"
      fill={AXIS_INK}
      fontFamily="JetBrains Mono"
      fontSize={10}
    >
      {`${value >= 0 ? '+' : ''}${value.toFixed(1)}%`}
    </text>
  );
};

type LabelProps = { x?: number | string; y?: number | string; value?: number | string };

/** One decimal keeps small ranges from collapsing into repeated tick labels. */
export const formatAxisPercent = (v: number): string => `${v.toFixed(1)}%`;

/**
 * Symmetric y-domain (in percent) around zero, with headroom for the value
 * labels. Symmetry keeps a +3% bar and a -3% bar the same length, so the eye
 * compares magnitudes correctly across the zero line.
 */
export const symmetricDomain = (values: number[]): [number, number] => {
  const maxAbs = Math.max(...values.map((v) => Math.abs(v)), 0.5);
  const bound = Number((maxAbs * 1.35).toPrecision(2));
  return [-bound, bound];
};

/** Five evenly spaced ticks across a symmetric domain, always including zero. */
export const symmetricTicks = ([low, high]: [number, number]): number[] =>
  [low, low / 2, 0, high / 2, high];

const EmptyState = ({ methodology, skipped }: { methodology: string; skipped: number }) => (
  <div className="py-8 text-center">
    <div className="font-mono text-xs text-muted-foreground">No earnings events could be measured</div>
    <div className="font-mono text-[10px] text-muted-foreground mt-2">
      {skipped > 0
        ? `${skipped} event${skipped === 1 ? '' : 's'} skipped for missing price or earnings data.`
        : 'Add holdings with reported earnings to see their historical reaction.'}
    </div>
    <div className="font-mono text-[10px] text-muted-foreground/70 mt-3">{methodology}</div>
  </div>
);

// ── Panel (presentational) ───────────────────────────────────────────────

export const NewsImpactPanel = ({
  data,
  isLoading,
  isError,
}: {
  data?: EventImpact;
  isLoading?: boolean;
  isError?: boolean;
}) => {
  const methodology = data?.methodology || METHODOLOGY_FALLBACK;

  const header = (
    <div className="flex items-center gap-2 mb-4">
      <Newspaper size={16} className="text-primary" />
      <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>NEWS IMPACT</span>
    </div>
  );

  if (isLoading) {
    return (
      <div className="glass rounded-xl p-4 sm:p-5 mb-8">
        {header}
        <div data-testid="news-impact-loading" className="h-[180px] rounded-xl shimmer" />
      </div>
    );
  }

  // A failed study shows an empty state. It never falls back to sample numbers.
  if (isError || !data || !data.overall || data.events.length === 0) {
    return (
      <div className="glass rounded-xl p-4 sm:p-5 mb-8">
        {header}
        <EmptyState methodology={methodology} skipped={data?.skipped_count ?? 0} />
      </div>
    );
  }

  const { overall } = data;
  const chartData = abnormalReturnByTicker(data.by_ticker);
  const chartDomain = symmetricDomain(chartData.map((d) => d.value));
  const recent = latestEventPerTicker(data.events);
  const grouped = data.headlines_by_category ?? {};
  const categories = CATEGORY_ORDER.filter((c) => (grouped[c]?.length ?? 0) > 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="glass rounded-xl p-4 sm:p-5 mb-8"
    >
      {header}

      {/* Summary tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <Tile
          label="Events analyzed"
          value={String(overall.n_events)}
          hint={`${data.tickers_analyzed.length} ticker${data.tickers_analyzed.length === 1 ? '' : 's'}`}
        />
        <Tile
          label="Avg abs abnormal return"
          value={formatPercent(overall.mean_abs_abnormal_return)}
          hint={`${formatPercent(overall.positive_share, 0)} positive`}
        />
        <Tile label="Avg volume spike" value={formatMultiple(overall.mean_volume_spike)} hint="vs 20-day average" />
        <Tile
          label="Avg volatility change"
          value={formatSignedPercent(overall.mean_volatility_change)}
          hint="5 days after vs 20 before"
        />
      </div>

      {/* Average abnormal return per ticker */}
      <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
        Avg abnormal return per ticker
      </span>
      <ResponsiveContainer width="100%" height={200} className="mt-3">
        <BarChart data={chartData} margin={{ top: 16, right: 8, bottom: 8, left: 8 }}>
          <XAxis
            dataKey="ticker"
            tick={{ fill: '#E6EDF3', fontSize: 11, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fill: AXIS_INK, fontSize: 10, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatAxisPercent}
            domain={chartDomain}
            ticks={symmetricTicks(chartDomain)}
            width={46}
          />
          <ReferenceLine y={0} stroke="rgba(139,148,158,0.4)" />
          <Tooltip
            cursor={{ fill: 'rgba(139,148,158,0.08)' }}
            contentStyle={{
              background: '#161B22',
              border: '1px solid rgba(56,189,148,0.2)',
              borderRadius: 8,
              fontFamily: 'JetBrains Mono',
              fontSize: 11,
            }}
            formatter={(v: number) => [`${v >= 0 ? '+' : ''}${v.toFixed(2)}%`, 'Avg abnormal return']}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={44} isAnimationActive={false}>
            {chartData.map((entry) => (
              <Cell key={entry.ticker} fill={entry.value >= 0 ? POSITIVE : NEGATIVE} />
            ))}
            <LabelList dataKey="value" position="top" content={barLabel('positive')} />
            <LabelList dataKey="value" position="bottom" content={barLabel('negative')} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Most recent event per ticker */}
      <div className="mt-5 overflow-x-auto">
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          Most recent earnings reaction
        </span>
        <table className="w-full mt-3">
          <thead>
            <tr className="border-b border-border">
              {['Ticker', 'Event date', 'Abnormal return', 'Volume spike', 'Volatility change'].map((h) => (
                <th key={h} className="text-left py-2 pr-2 label-mono whitespace-nowrap" style={{ color: 'hsl(214 10% 57%)' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recent.map((event) => (
              <tr key={event.ticker} className="border-b border-border/30 hover:bg-card-elevated/50 transition-colors">
                <td className="py-2.5 pr-3 font-mono text-xs font-medium text-foreground whitespace-nowrap">{event.ticker}</td>
                <td className="py-2.5 pr-3 font-mono text-xs text-muted-foreground whitespace-nowrap">{event.date}</td>
                <td
                  className={`py-2.5 pr-3 font-mono text-xs font-medium whitespace-nowrap ${
                    event.abnormal_return >= 0 ? 'text-signal-green' : 'text-signal-red'
                  }`}
                >
                  {formatSignedPercent(event.abnormal_return)}
                </td>
                <td className="py-2.5 pr-3 font-mono text-xs text-foreground whitespace-nowrap">
                  {formatMultiple(event.volume_spike)}
                </td>
                <td className="py-2.5 pr-2 font-mono text-xs text-foreground whitespace-nowrap">
                  {formatSignedPercent(event.volatility_change)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Today's headlines, grouped by the keyword rules */}
      {categories.length > 0 && (
        <div className="mt-5">
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
            Today's headlines by category
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-5 gap-y-3 mt-3">
            {categories.map((category) => (
              <div key={category}>
                <div className="font-mono text-[10px] text-primary/80 mb-1">
                  {category} · {grouped[category].length}
                </div>
                <ul className="space-y-1">
                  {grouped[category].slice(0, 3).map((article, i) => (
                    <li key={article.id ?? `${category}-${i}`} className="font-mono text-[11px] text-muted-foreground leading-snug">
                      {article.url && article.url !== '#' ? (
                        <a href={article.url} target="_blank" rel="noreferrer" className="hover:text-foreground transition-colors">
                          {article.headline}
                        </a>
                      ) : (
                        article.headline
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="font-mono text-[10px] text-muted-foreground/70 mt-5">
        {methodology}
        {data.skipped_count > 0 && ` · ${data.skipped_count} event${data.skipped_count === 1 ? '' : 's'} skipped for missing data`}
      </div>
    </motion.div>
  );
};

// ── Container ────────────────────────────────────────────────────────────

const NewsImpact = ({ tickers }: { tickers: string[] }) => {
  const clean = [...new Set(tickers.filter(Boolean).map((t) => t.toUpperCase()))].sort();

  const { data, isLoading, isError } = useQuery<EventImpact>({
    queryKey: ['event-impact', clean],
    queryFn: () => getEventImpact(clean),
    enabled: clean.length > 0,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  if (clean.length === 0) return null;

  return <NewsImpactPanel data={data} isLoading={isLoading} isError={isError} />;
};

export default NewsImpact;
