import { getResearchClientId, resolveApiBase } from '@/lib/api';

// Types mirror scenario/schemas.py. Returns are fractions (-0.08 means -8%).

export type Category =
  | 'geopolitical_conflict'
  | 'terrorism'
  | 'trade_tariffs'
  | 'monetary_policy'
  | 'fiscal_debt'
  | 'financial_credit'
  | 'energy_oil'
  | 'pandemic_health'
  | 'disaster_supply'
  | 'tech_sector'
  | 'election_political';

export type Nature = 'adverse' | 'favorable';
export type Severity = 'mild' | 'typical' | 'severe';
export type Confidence = 'normal' | 'low';
export type ImpactSource = 'actual' | 'estimated' | 'estimated_low_history';
export type Sector =
  | 'technology'
  | 'financials'
  | 'energy'
  | 'health_care'
  | 'industrials'
  | 'consumer_discretionary'
  | 'consumer_staples'
  | 'utilities'
  | 'materials'
  | 'semiconductors'
  | 'broad';

export interface ParsedScenario {
  category: Category | null;
  nature?: Nature | null;
  regions: string[];
  sectors: Sector[];
  companies: string[];
  search_text: string;
  fallback: boolean;
}

export interface ScenarioHolding {
  ticker: string;
  weight: number;
}

export interface WhatIfRequest {
  scenario: string;
  holdings: ScenarioHolding[];
  severity: Severity;
  client_id?: string;
}

export interface Precedent {
  event_id: string;
  name: string;
  date: string;
  category: Category;
  nature: Nature;
  trigger: string;
  similarity: number;
  weight: number;
  sp500_return_21d: number | null;
  portfolio_return_21d: number | null;
  source_url: string;
}

export interface PortfolioOutcome {
  horizon_days: number;
  range_level: number;
  severity: Severity;
  typical_return: number;
  median_return: number;
  mean_return: number;
  range_low: number;
  range_high: number;
  worst_drawdown_63d: number;
  recovery_days_low: number | null;
  recovery_days_high: number | null;
  unrecovered_share: number;
}

export interface HoldingImpact {
  ticker: string;
  weight: number;
  sector: Sector;
  return_21d: number;
  contribution: number;
  source: ImpactSource;
  actual_share: number;
}

export interface SkippedTicker {
  ticker: string;
  reason: string;
}

export interface PathSeries {
  event_id: string;
  label: string;
  values: Array<number | null>;
}

export interface MetricCI {
  value: number;
  ci_low: number;
  ci_high: number;
}

export interface BacktestSummary {
  available: boolean;
  holdout_events: number | null;
  coverage_80: MetricCI | null;
  width_ratio: MetricCI | null;
  mae: MetricCI | null;
  mae_best_baseline: MetricCI | null;
  rank_corr: MetricCI | null;
  gate_passed: boolean | null;
  results_url: string | null;
}

export interface WhatIfResponse {
  scenario: string;
  parsed: ParsedScenario;
  as_of: string;
  severity: Severity;
  confidence: Confidence;
  precedents: Precedent[];
  portfolio: PortfolioOutcome | null;
  holdings: HoldingImpact[];
  skipped: SkippedTicker[];
  paths: PathSeries[];
  narrative: string;
  backtest: BacktestSummary;
  remaining_today: number | null;
}

export type ScenarioErrorKind = 'quota' | 'unavailable' | 'invalid' | 'disabled' | 'network' | 'unknown';

export class ScenarioError extends Error {
  kind: ScenarioErrorKind;
  status?: number;

  constructor(kind: ScenarioErrorKind, message: string, status?: number) {
    super(message);
    this.name = 'ScenarioError';
    this.kind = kind;
    this.status = status;
  }
}

export const MAX_SCENARIO_HOLDINGS = 25;

const BASE = resolveApiBase(import.meta.env.VITE_API_URL, window.location.hostname);

function detailMessage(detail: unknown): string | undefined {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === 'string') return message;
  }
  return undefined;
}

export async function askWhatIf(request: Omit<WhatIfRequest, 'client_id'>): Promise<WhatIfResponse> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/api/scenario/whatif`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...request, client_id: getResearchClientId() }),
    });
  } catch {
    throw new ScenarioError('network', 'Could not reach the Arcus server. Check your connection and try again.');
  }

  const payload = await res.json().catch(() => null);
  if (res.ok) return payload as WhatIfResponse;

  const message = detailMessage(payload?.detail);
  if (res.status === 429) {
    throw new ScenarioError('quota', message ?? 'Daily Scenario Lab limit reached. It resets at 00:00 UTC.', 429);
  }
  if (res.status === 503) {
    throw new ScenarioError('unavailable', message ?? 'Scenario Lab is temporarily unavailable. No estimate was produced.', 503);
  }
  if (res.status === 422) {
    throw new ScenarioError('invalid', 'The question or holdings could not be used. Check them and try again.', 422);
  }
  if (res.status === 404) {
    throw new ScenarioError('disabled', 'Scenario Lab is not available on this server.', 404);
  }
  throw new ScenarioError('unknown', message ?? `Scenario Lab request failed (${res.status}).`, res.status);
}

/** Holdings for the request: positive weights, at most MAX_SCENARIO_HOLDINGS (largest first). */
export function scenarioHoldings(holdings: Array<{ ticker: string; weight: number }>): ScenarioHolding[] {
  return holdings
    .filter((holding) => holding.ticker && Number.isFinite(holding.weight) && holding.weight > 0)
    .sort((a, b) => b.weight - a.weight)
    .slice(0, MAX_SCENARIO_HOLDINGS)
    .map((holding) => ({ ticker: holding.ticker.toUpperCase(), weight: holding.weight }));
}
