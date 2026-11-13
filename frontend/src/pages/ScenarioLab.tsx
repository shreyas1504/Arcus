import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, AlertTriangle, Compass, ExternalLink, Loader2, Send } from 'lucide-react';

import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { buildChatPortfolioContext } from '@/lib/portfolio-context';
import {
  askWhatIf,
  BacktestSummaryV2,
  ExposureRank,
  ImpactSource,
  MAX_SCENARIO_HOLDINGS,
  MetricCI,
  Resilience,
  ScenarioError,
  ScenarioReplay,
  scenarioHoldings,
  WhatIfResponseV2,
} from '@/lib/scenario';

const EXAMPLES = [
  'What if China blockades Taiwan?',
  'What if the Fed raises rates at its next meeting?',
  'What if a war in the Middle East disrupts oil supply?',
  'What if a major US bank fails?',
];

const SOURCE_LABEL: Record<ImpactSource, string> = {
  actual: 'Actual',
  estimated: 'Estimated',
  estimated_low_history: 'Estimated, short history',
};

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

const formatRecovery = (replay: ScenarioReplay): string => {
  if (!replay.recovery_known) return 'Recovery not estimated';
  if (replay.recovery_days === null) return 'Not within two years';
  if (replay.recovery_days === 0) return 'Never fell below start';
  return `${replay.recovery_days} trading days`;
};

const returnTone = (value: number | null | undefined): string => {
  if (value === null || value === undefined || value === 0) return 'text-foreground';
  return value < 0 ? 'text-destructive' : 'text-emerald-500';
};

function holdingMap(replay: ScenarioReplay): Map<string, ScenarioReplay['holdings'][number]> {
  return new Map(replay.holdings.map((holding) => [holding.ticker, holding]));
}

function ScenarioTable({ scenarios }: { scenarios: ScenarioReplay[] }) {
  const tickers = Array.from(
    new Set(scenarios.flatMap((scenario) => scenario.holdings.map((holding) => holding.ticker))),
  );
  return (
    <Card className="p-5" data-testid="scenario-table">
      <h2 className="font-display text-sm font-semibold text-foreground">Company-by-company scenario replay</h2>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        Each column is one past shock applied to today&apos;s holdings. Returns are the holding&apos;s 21-day move
        in that shock.
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[40rem] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">Ticker</th>
              {scenarios.map((scenario) => (
                <th key={scenario.event_id} className="py-2 pr-3 font-medium" data-testid={`scenario-col-${scenario.event_id}`}>
                  <div className="text-foreground">{scenario.name}</div>
                  <div className="font-mono font-normal">{scenario.date}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tickers.map((ticker) => (
              <tr key={ticker} className="border-b border-border/50" data-testid={`scenario-row-${ticker}`}>
                <td className="py-2 pr-3 font-mono font-semibold">{ticker}</td>
                {scenarios.map((scenario) => {
                  const holding = holdingMap(scenario).get(ticker);
                  return (
                    <td key={scenario.event_id} className="py-2 pr-3">
                      {holding ? (
                        <div>
                          <div className={`font-mono ${returnTone(holding.return_21d)}`}>
                            {formatReturn(holding.return_21d)}
                          </div>
                          <div className="text-[11px] text-muted-foreground">{SOURCE_LABEL[holding.source]}</div>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
            <tr className="border-t border-border" data-testid="scenario-portfolio-row">
              <td className="py-2 pr-3 font-semibold">Portfolio</td>
              {scenarios.map((scenario) => (
                <td key={scenario.event_id} className={`py-2 pr-3 font-mono ${returnTone(scenario.portfolio_return_21d)}`}>
                  {formatReturn(scenario.portfolio_return_21d)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function HistoricalSpan({ spanLow, spanHigh, count }: { spanLow: number; spanHigh: number; count: number }) {
  return (
    <Card className="p-5" data-testid="historical-span">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Historical span</div>
      <div className="mt-1 font-display text-2xl font-bold text-foreground">
        <span className={returnTone(spanLow)}>{formatReturn(spanLow)}</span>
        <span className="mx-2 text-muted-foreground">to</span>
        <span className={returnTone(spanHigh)}>{formatReturn(spanHigh)}</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Across these {count} past shock{count === 1 ? '' : 's'}, this portfolio&apos;s 21-day move ranged between these
        two outcomes. This is history applied to today&apos;s holdings, not a forecast range.
      </p>
    </Card>
  );
}

function ExposureRanking({ exposure }: { exposure: ExposureRank[] }) {
  return (
    <Card className="p-5" data-testid="exposure-ranking">
      <h2 className="font-display text-sm font-semibold text-foreground">Exposure ranking</h2>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        Which holdings took the largest share of the damage across the scenario replays.
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">Ticker</th>
              <th className="py-2 pr-3 font-medium">Mean contribution</th>
              <th className="py-2 font-medium">Most exposed</th>
            </tr>
          </thead>
          <tbody>
            {exposure.map((row) => (
              <tr key={row.ticker} className="border-b border-border/50" data-testid={`exposure-${row.ticker}`}>
                <td className="py-2 pr-3 font-mono font-semibold">{row.ticker}</td>
                <td className={`py-2 pr-3 font-mono ${returnTone(row.mean_contribution)}`}>
                  {formatReturn(row.mean_contribution)}
                </td>
                <td className="py-2 font-mono">
                  {row.most_exposed_count} of {row.scenarios}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function CrisisPanel({ crises }: { crises: ScenarioReplay[] }) {
  return (
    <div className="space-y-3" data-testid="crisis-replay">
      <h2 className="font-display text-sm font-semibold text-foreground">Crisis replay</h2>
      <p className="text-xs leading-5 text-muted-foreground">
        Fixed major crises (S&amp;P worst fall of −10% or worse within 63 days), replayed on your holdings.
      </p>
      {crises.map((crisis) => {
        const mostExposed = [...crisis.holdings].sort((a, b) => a.contribution - b.contribution || a.ticker.localeCompare(b.ticker))[0];
        return (
          <Card key={crisis.event_id} className="p-4" data-testid={`crisis-${crisis.event_id}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-semibold text-foreground">{crisis.name}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {crisis.date} · {CATEGORY_LABEL[crisis.category] ?? crisis.category}
                </div>
              </div>
              <a
                href={crisis.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                Source <ExternalLink size={12} />
              </a>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{crisis.trigger}</p>
            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-xs text-muted-foreground">Portfolio 21d</dt>
                <dd className={`font-mono ${returnTone(crisis.portfolio_return_21d)}`}>
                  {formatReturn(crisis.portfolio_return_21d)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">S&amp;P 21d</dt>
                <dd className={`font-mono ${returnTone(crisis.sp500_return_21d)}`}>
                  {formatReturn(crisis.sp500_return_21d)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Worst fall, 3 months</dt>
                <dd className={`font-mono ${returnTone(crisis.worst_drawdown_63d)}`}>
                  {formatReturn(crisis.worst_drawdown_63d)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">S&amp;P worst fall</dt>
                <dd className={`font-mono ${returnTone(crisis.sp500_worst_drawdown_63d)}`}>
                  {formatReturn(crisis.sp500_worst_drawdown_63d)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Recovery</dt>
                <dd className="font-mono">{formatRecovery(crisis)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Most exposed</dt>
                <dd className="font-mono">{mostExposed?.ticker ?? '—'}</dd>
              </div>
            </dl>
          </Card>
        );
      })}
    </div>
  );
}

function ResilienceSummary({ resilience }: { resilience: Resilience }) {
  return (
    <Card className="p-5" data-testid="resilience-summary">
      <h2 className="font-display text-sm font-semibold text-foreground">Resilience summary</h2>
      <p className="mt-2 text-sm leading-6 text-foreground">
        This portfolio fell more than the S&amp;P in{' '}
        <span className="font-mono font-semibold">
          {resilience.worse_than_sp500} of {resilience.crises_total}
        </span>{' '}
        crises
        {resilience.top_drivers.length > 0
          ? `; ${resilience.top_drivers.join(' and ')} drove most of the damage`
          : ''}
        .
      </p>
    </Card>
  );
}

function LimitsNote() {
  return (
    <p className="text-sm leading-6 text-muted-foreground" data-testid="limits">
      Arcus cannot predict whether or when a crisis happens. Each replay shows what happened, applied to
      today&apos;s holdings — not a forecast.
    </p>
  );
}

const metricText = (metric: MetricCI | null, format: (value: number) => string) =>
  metric ? `${format(metric.value)} (90% CI ${format(metric.ci_low)} to ${format(metric.ci_high)})` : '—';

function AccuracyPanel({ backtest }: { backtest: BacktestSummaryV2 }) {
  return (
    <Card className="p-5" data-testid="accuracy-panel">
      <h2 className="font-display text-sm font-semibold text-foreground">How accurate is this?</h2>
      {!backtest.available ? (
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Accuracy results are not published yet. They will come from a one-time conditional test on holdout
          events that the engine was never tuned on.
        </p>
      ) : (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <dt className="text-muted-foreground">Holdout events</dt>
          <dd className="font-mono">{backtest.holdout_events ?? '—'}</dd>
          <dt className="text-muted-foreground">21-day portfolio MAE</dt>
          <dd className="font-mono">{metricText(backtest.h1_mae, (v) => `${(v * 100).toFixed(1)} pts`)}</dd>
          <dt className="text-muted-foreground">Holding ranking</dt>
          <dd className="font-mono">{metricText(backtest.h2_rank, (v) => v.toFixed(2))}</dd>
          <dt className="text-muted-foreground">Worst-fall MAE</dt>
          <dd className="font-mono">{metricText(backtest.h3_drawdown_mae, (v) => `${(v * 100).toFixed(1)} pts`)}</dd>
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
  const [askedQuestion, setAskedQuestion] = useState('');
  const [result, setResult] = useState<WhatIfResponseV2 | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const run = async (scenario: string) => {
    if (!scenario || holdings.length === 0 || loading) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      setResult(await askWhatIf({ scenario, holdings, severity: 'typical' }));
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
    void run(question.trim());
  };

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
              Ask what a shock like this would do to your portfolio, company by company. Every number is a
              past event replayed on today&apos;s holdings — not a prediction of what happens next.
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
                  <p className="text-xs text-muted-foreground">
                    Using {holdings.length} holding{holdings.length === 1 ? '' : 's'}:{' '}
                    {holdings.map((holding) => holding.ticker).join(', ')}.
                    {trimmed > 0 && ` Only your ${MAX_SCENARIO_HOLDINGS} largest holdings are included; ${trimmed} smaller one${trimmed === 1 ? ' is' : 's are'} left out.`}
                  </p>
                  <Button type="submit" disabled={loading || !question.trim()} className="gap-2">
                    {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    {loading ? 'Replaying shocks…' : 'Run scenario'}
                  </Button>
                </div>
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
                      <strong>Low confidence.</strong> No past event is a close match for this question, so only
                      the crisis replay is shown.
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

                {result.narrative && (
                  <Card className="p-5" data-testid="narrative">
                    <p className="text-sm leading-6 text-foreground">{result.narrative}</p>
                  </Card>
                )}

                {result.scenarios.length > 0 && result.span_low !== null && result.span_high !== null && (
                  <HistoricalSpan spanLow={result.span_low} spanHigh={result.span_high} count={result.scenarios.length} />
                )}

                {result.scenarios.length > 0 && <ScenarioTable scenarios={result.scenarios} />}
                {result.exposure.length > 0 && <ExposureRanking exposure={result.exposure} />}
                {result.crises.length > 0 && <CrisisPanel crises={result.crises} />}
                {result.resilience && <ResilienceSummary resilience={result.resilience} />}

                <LimitsNote />
                <AccuracyPanel backtest={result.backtest} />

                {result.remaining_today !== null && (
                  <p className="text-right text-xs text-muted-foreground">{result.remaining_today} scenarios left today</p>
                )}
                {askedQuestion && <span className="sr-only">{askedQuestion}</span>}
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default ScenarioLab;
