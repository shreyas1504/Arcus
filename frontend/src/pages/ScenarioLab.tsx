import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertCircle, AlertTriangle, Compass, ExternalLink, Loader2, Send } from 'lucide-react';

import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { buildChatPortfolioContext } from '@/lib/portfolio-context';
import {
  askWhatIf,
  BacktestSummary,
  HoldingImpact,
  ImpactSource,
  MAX_SCENARIO_HOLDINGS,
  MetricCI,
  PathSeries,
  PortfolioOutcome,
  Precedent,
  ScenarioError,
  scenarioHoldings,
  Severity,
  WhatIfResponse,
} from '@/lib/scenario';

const EXAMPLES = [
  'What if China blockades Taiwan?',
  'What if the Fed raises rates at its next meeting?',
  'What if a war in the Middle East disrupts oil supply?',
  'What if a major US bank fails?',
];

const SEVERITIES: Array<{ value: Severity; label: string; hint: string }> = [
  { value: 'mild', label: 'Mild', hint: 'A milder outcome among the precedents' },
  { value: 'typical', label: 'Typical', hint: 'The weighted median of the precedents' },
  { value: 'severe', label: 'Severe', hint: 'A severe outcome among the precedents' },
];

const SOURCE_LABEL: Record<ImpactSource, string> = {
  actual: 'Actual',
  estimated: 'Estimated',
  estimated_low_history: 'Estimated, short history',
};

const SOURCE_HINT: Record<ImpactSource, string> = {
  actual: 'Uses the stock\'s real prices during the precedents',
  estimated: 'Estimated from the stock\'s sensitivity to market, sector, rates and oil',
  estimated_low_history: 'Estimated from less than six months of price history',
};

const PATH_COLORS = ['hsl(var(--primary))', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];

const CATEGORY_LABEL: Record<string, string> = {
  geopolitical_conflict: 'Geopolitical conflict',
  terrorism: 'Terrorism',
  trade_tariffs: 'Trade and tariffs',
  monetary_policy: 'Monetary policy',
  fiscal_debt: 'Fiscal and debt',
  financial_credit: 'Financial and credit',
  energy_oil: 'Energy and oil',
  pandemic_health: 'Pandemic and health',
  disaster_supply: 'Disaster and supply chain',
  tech_sector: 'Tech sector',
  election_political: 'Election and political',
};

const formatReturn = (value: number | null | undefined): string => {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const pct = value * 100;
  const sign = pct > 0 ? '+' : pct < 0 ? '−' : '';
  return `${sign}${Math.abs(pct).toFixed(1)}%`;
};

const formatShare = (value: number): string => `${Math.round(value * 100)}%`;

const formatDays = (low: number | null, high: number | null): string => {
  if (low === null || high === null) return 'Not enough history';
  if (low === high) return `${low} trading days`;
  return `${low}–${high} trading days`;
};

const returnTone = (value: number | null | undefined): string => {
  if (value === null || value === undefined || value === 0) return 'text-foreground';
  return value < 0 ? 'text-destructive' : 'text-emerald-500';
};

function RangeBar({ outcome }: { outcome: PortfolioOutcome }) {
  const low = Math.min(outcome.range_low, outcome.typical_return, 0);
  const high = Math.max(outcome.range_high, outcome.typical_return, 0);
  const span = high - low || 1;
  const position = (value: number) => `${((value - low) / span) * 100}%`;
  return (
    <div className="mt-4" data-testid="range-bar">
      <div className="relative h-3 rounded-full bg-muted" aria-hidden="true">
        <div
          className="absolute h-3 rounded-full bg-primary/30"
          style={{ left: position(outcome.range_low), right: `calc(100% - ${position(outcome.range_high)})` }}
        />
        <div className="absolute top-[-3px] h-[18px] w-0.5 bg-muted-foreground/60" style={{ left: position(0) }} />
        <div
          className="absolute top-[-4px] h-5 w-1.5 -translate-x-1/2 rounded-full bg-primary"
          style={{ left: position(outcome.typical_return) }}
        />
      </div>
      <div className="mt-2 flex justify-between font-mono text-xs text-muted-foreground">
        <span>{formatReturn(outcome.range_low)}</span>
        <span>{formatReturn(outcome.range_high)}</span>
      </div>
    </div>
  );
}

function OutcomeCard({ response, outcome }: { response: WhatIfResponse; outcome: PortfolioOutcome }) {
  const level = formatShare(outcome.range_level);
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {SEVERITIES.find((s) => s.value === outcome.severity)?.label} {outcome.horizon_days}-day return
          </div>
          <div className={`mt-1 font-display text-4xl font-bold ${returnTone(outcome.typical_return)}`} data-testid="typical-return">
            {formatReturn(outcome.typical_return)}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">
            {level} range: {formatReturn(outcome.range_low)} to {formatReturn(outcome.range_high)}
          </div>
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <dt className="text-muted-foreground">Median</dt>
          <dd className="font-mono">{formatReturn(outcome.median_return)}</dd>
          <dt className="text-muted-foreground">Worst drop, 63 days</dt>
          <dd className="font-mono">{formatReturn(outcome.worst_drawdown_63d)}</dd>
          <dt className="text-muted-foreground">Recovery</dt>
          <dd className="font-mono">{formatDays(outcome.recovery_days_low, outcome.recovery_days_high)}</dd>
          <dt className="text-muted-foreground">Never recovered</dt>
          <dd className="font-mono">{formatShare(outcome.unrecovered_share)} of precedents</dd>
        </dl>
      </div>
      <RangeBar outcome={outcome} />
      {response.narrative && <p className="mt-4 text-sm leading-6 text-foreground">{response.narrative}</p>}
    </Card>
  );
}

function PathChart({ paths, precedents, horizon }: { paths: PathSeries[]; precedents: Precedent[]; horizon: number }) {
  const length = Math.max(...paths.map((path) => path.values.length));
  const rows = Array.from({ length }, (_, t) => {
    const row: Record<string, number | null> = { t };
    paths.forEach((path) => {
      const value = path.values[t];
      row[path.event_id] = value === null || value === undefined ? null : value * 100;
    });
    return row;
  });
  const summaryId = 'scenario-path-summary';
  return (
    <Card className="p-5">
      <h2 className="font-display text-sm font-semibold text-foreground">Your portfolio after each precedent</h2>
      <p id={summaryId} className="mt-1 text-xs leading-5 text-muted-foreground">
        Cumulative return over {length - 1} trading days after {paths.length} precedent
        {paths.length === 1 ? '' : 's'}.{' '}
        {precedents
          .filter((precedent) => paths.some((path) => path.event_id === precedent.event_id))
          .map((precedent) => `${precedent.name}: ${formatReturn(precedent.portfolio_return_21d)} after ${horizon} days.`)
          .join(' ')}
      </p>
      <div className="mt-4 h-64" role="img" aria-describedby={summaryId} data-testid="path-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="t" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
            <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" unit="%" width={48} />
            <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
            <ReferenceLine x={horizon} stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" />
            <Tooltip
              formatter={(value: number) => `${value.toFixed(1)}%`}
              labelFormatter={(t) => `Day ${t}`}
              contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {paths.map((path, index) => (
              <Line
                key={path.event_id}
                type="monotone"
                dataKey={path.event_id}
                name={path.label}
                stroke={PATH_COLORS[index % PATH_COLORS.length]}
                dot={false}
                strokeWidth={2}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function HoldingsTable({ holdings, horizon }: { holdings: HoldingImpact[]; horizon: number }) {
  return (
    <Card className="p-5">
      <h2 className="font-display text-sm font-semibold text-foreground">Impact by holding</h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">Ticker</th>
              <th className="py-2 pr-3 font-medium">Weight</th>
              <th className="py-2 pr-3 font-medium">{horizon}-day return</th>
              <th className="py-2 pr-3 font-medium">Contribution</th>
              <th className="py-2 font-medium">Basis</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((holding) => (
              <tr key={holding.ticker} className="border-b border-border/50" data-testid={`holding-${holding.ticker}`}>
                <td className="py-2 pr-3 font-mono font-semibold">{holding.ticker}</td>
                <td className="py-2 pr-3 font-mono">{formatShare(holding.weight)}</td>
                <td className={`py-2 pr-3 font-mono ${returnTone(holding.return_21d)}`}>{formatReturn(holding.return_21d)}</td>
                <td className={`py-2 pr-3 font-mono ${returnTone(holding.contribution)}`}>{formatReturn(holding.contribution)}</td>
                <td className="py-2">
                  <span
                    title={SOURCE_HINT[holding.source]}
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      holding.source === 'actual'
                        ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                        : 'bg-amber-500/15 text-amber-700 dark:text-amber-400'
                    }`}
                  >
                    {SOURCE_LABEL[holding.source]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function PrecedentCards({ precedents, horizon }: { precedents: Precedent[]; horizon: number }) {
  return (
    <div className="space-y-3">
      <h2 className="font-display text-sm font-semibold text-foreground">Closest historical precedents</h2>
      {precedents.map((precedent) => (
        <Card key={precedent.event_id} className="p-4" data-testid={`precedent-${precedent.event_id}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-semibold text-foreground">{precedent.name}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">
                {precedent.date} · {CATEGORY_LABEL[precedent.category] ?? precedent.category} ·{' '}
                {precedent.nature === 'favorable' ? 'Favorable' : 'Adverse'}
              </div>
            </div>
            <div className="text-right font-mono text-xs text-muted-foreground">
              <div>Similarity {precedent.similarity.toFixed(2)}</div>
              <div>Weight {formatShare(precedent.weight)}</div>
            </div>
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{precedent.trigger}</p>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex gap-4 font-mono">
              <span>
                S&amp;P 500 {horizon}d:{' '}
                <span className={returnTone(precedent.sp500_return_21d)}>{formatReturn(precedent.sp500_return_21d)}</span>
              </span>
              <span>
                Your portfolio {horizon}d:{' '}
                <span className={returnTone(precedent.portfolio_return_21d)}>{formatReturn(precedent.portfolio_return_21d)}</span>
              </span>
            </div>
            <a
              href={precedent.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              Source <ExternalLink size={12} />
            </a>
          </div>
        </Card>
      ))}
    </div>
  );
}

const metricText = (metric: MetricCI | null, format: (value: number) => string) =>
  metric ? `${format(metric.value)} (90% CI ${format(metric.ci_low)} to ${format(metric.ci_high)})` : '—';

function AccuracyPanel({ backtest }: { backtest: BacktestSummary }) {
  return (
    <Card className="p-5" data-testid="accuracy-panel">
      <h2 className="font-display text-sm font-semibold text-foreground">How accurate is this?</h2>
      {!backtest.available ? (
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Accuracy results are not published yet. They will come from a one-time test on events from 2023
          onward that the engine was never tuned on.
        </p>
      ) : (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <dt className="text-muted-foreground">Holdout events</dt>
          <dd className="font-mono">{backtest.holdout_events ?? '—'}</dd>
          <dt className="text-muted-foreground">80% range contained the outcome</dt>
          <dd className="font-mono">{metricText(backtest.coverage_80, formatShare)}</dd>
          <dt className="text-muted-foreground">Typical-outcome error</dt>
          <dd className="font-mono">{metricText(backtest.mae, (v) => `${(v * 100).toFixed(1)} pts`)}</dd>
          <dt className="text-muted-foreground">Best simple baseline error</dt>
          <dd className="font-mono">{metricText(backtest.mae_best_baseline, (v) => `${(v * 100).toFixed(1)} pts`)}</dd>
          <dt className="text-muted-foreground">Ranking of holdings</dt>
          <dd className="font-mono">{metricText(backtest.rank_corr, (v) => v.toFixed(2))}</dd>
          {backtest.results_url && (
            <dd className="sm:col-span-2">
              <a href={backtest.results_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                Full results
              </a>
            </dd>
          )}
        </dl>
      )}
    </Card>
  );
}

const ScenarioLab = () => {
  const context = useMemo(() => buildChatPortfolioContext(), []);
  const allHoldings = useMemo(
    () => (context?.holdings ?? []).map((holding) => ({ ticker: holding.ticker, weight: holding.weight })),
    [context],
  );
  const holdings = useMemo(() => scenarioHoldings(allHoldings), [allHoldings]);
  const trimmed = allHoldings.filter((holding) => holding.weight > 0).length - holdings.length;

  const [question, setQuestion] = useState('');
  const [severity, setSeverity] = useState<Severity>('typical');
  const [askedQuestion, setAskedQuestion] = useState('');
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const run = async (scenario: string, level: Severity) => {
    if (!scenario || holdings.length === 0 || loading) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      setResult(await askWhatIf({ scenario, holdings, severity: level }));
      setAskedQuestion(scenario);
    } catch (requestError) {
      setError(requestError instanceof ScenarioError || requestError instanceof Error
        ? requestError.message
        : 'Scenario Lab request failed.');
    } finally {
      setLoading(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void run(question.trim(), severity);
  };

  const changeSeverity = (level: Severity) => {
    setSeverity(level);
    if (askedQuestion && level !== severity) void run(askedQuestion, level);
  };

  const outcome = result?.portfolio ?? null;
  const horizon = outcome?.horizon_days ?? 21;

  return (
    <AppLayout title="Scenario Lab">
      <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
        <BackButton to="/dashboard" label="Back to Dashboard" />

        <div className="mb-6 flex items-start gap-3">
          <div className="rounded-xl border border-primary/20 bg-primary/10 p-2.5">
            <Compass className="text-primary" size={22} />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Scenario Lab</h1>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
              Ask what happens to your portfolio if an event occurs. Every number comes from real historical
              precedents and your holdings. The AI only reads your question; it never produces a number.
            </p>
          </div>
        </div>

        {holdings.length === 0 ? (
          <Card className="p-8 text-center">
            <h2 className="font-display font-semibold text-foreground">No portfolio found</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              Add your holdings and run an analysis first. Scenario Lab uses your weights.
            </p>
            <Button asChild className="mt-4">
              <Link to="/dashboard">Go to Dashboard</Link>
            </Button>
          </Card>
        ) : (
          <div className="space-y-5">
            <Card className="p-5">
              <form onSubmit={submit} className="space-y-4">
                <div>
                  <label htmlFor="scenario-question" className="font-display text-sm font-semibold text-foreground">
                    Describe a scenario
                  </label>
                  <Textarea
                    id="scenario-question"
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    maxLength={500}
                    rows={3}
                    placeholder="What if China blockades Taiwan?"
                    className="mt-2 resize-none"
                  />
                  <div className="mt-1 text-right font-mono text-[10px] text-muted-foreground">{question.length}/500</div>
                </div>

                <div className="flex flex-wrap gap-2" aria-label="Example scenarios">
                  {EXAMPLES.map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => setQuestion(example)}
                      className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                    >
                      {example}
                    </button>
                  ))}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div role="radiogroup" aria-label="Severity" className="inline-flex rounded-lg border border-border p-0.5">
                    {SEVERITIES.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        role="radio"
                        aria-checked={severity === option.value}
                        title={option.hint}
                        disabled={loading}
                        onClick={() => changeSeverity(option.value)}
                        className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                          severity === option.value ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                  <Button type="submit" disabled={loading || !question.trim()} className="gap-2">
                    {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    {loading ? 'Finding precedents…' : 'Run scenario'}
                  </Button>
                </div>

                <p className="text-xs text-muted-foreground">
                  Using {holdings.length} holding{holdings.length === 1 ? '' : 's'}:{' '}
                  {holdings.map((holding) => holding.ticker).join(', ')}.
                  {trimmed > 0 && ` Only your ${MAX_SCENARIO_HOLDINGS} largest holdings are included; ${trimmed} smaller one${trimmed === 1 ? ' is' : 's are'} left out.`}
                </p>
              </form>
            </Card>

            {error && (
              <div role="alert" className="flex gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                <AlertCircle size={18} className="flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {result && (
              <div className="space-y-5" data-testid="scenario-result">
                {result.confidence === 'low' && (
                  <div role="status" className="flex gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-800 dark:text-amber-300" data-testid="low-confidence">
                    <AlertTriangle size={18} className="flex-shrink-0" />
                    <span>
                      <strong>Low confidence.</strong> No past event is a close match for this question, so the range
                      uses every eligible precedent and is wider than usual.
                    </span>
                  </div>
                )}
                {result.parsed.fallback && (
                  <p className="text-xs text-muted-foreground">
                    The question could not be classified, so precedents were matched on its wording alone.
                  </p>
                )}

                {result.skipped.length > 0 && (
                  <div className="rounded-xl border border-border p-4 text-sm" data-testid="skipped">
                    <div className="font-semibold text-foreground">Not included</div>
                    <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                      {result.skipped.map((item) => (
                        <li key={item.ticker}><span className="font-mono">{item.ticker}</span>: {item.reason}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {outcome ? (
                  <>
                    <OutcomeCard response={result} outcome={outcome} />
                    {result.paths.length > 0 && (
                      <PathChart paths={result.paths} precedents={result.precedents} horizon={horizon} />
                    )}
                    {result.holdings.length > 0 && <HoldingsTable holdings={result.holdings} horizon={horizon} />}
                  </>
                ) : (
                  <Card className="p-6 text-center" data-testid="empty-outcome">
                    <h2 className="font-display font-semibold text-foreground">No estimate available</h2>
                    <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
                      There was not enough price history for these holdings to measure this scenario. No number is
                      shown rather than a guess.
                    </p>
                  </Card>
                )}

                {result.precedents.length > 0 && <PrecedentCards precedents={result.precedents} horizon={horizon} />}
                <AccuracyPanel backtest={result.backtest} />

                {result.remaining_today !== null && (
                  <p className="text-right text-xs text-muted-foreground">{result.remaining_today} scenarios left today</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default ScenarioLab;
