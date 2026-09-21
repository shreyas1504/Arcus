import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import {
  NewsImpactPanel,
  METHODOLOGY_FALLBACK,
  formatSignedPercent,
  formatPercent,
  formatMultiple,
  latestEventPerTicker,
  abnormalReturnByTicker,
  type EventImpact,
} from '@/components/NewsImpact';

// Recharts measures its container, which happy-dom reports as 0x0; pin a size
// so ResponsiveContainer renders its children.
let describeSpy: ReturnType<typeof vi.spyOn>;
beforeAll(() => {
  describeSpy = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    width: 600, height: 200, top: 0, left: 0, right: 600, bottom: 200, x: 0, y: 0, toJSON: () => ({}),
  } as DOMRect);
});
afterAll(() => describeSpy.mockRestore());

const event = (ticker: string, date: string, abnormal: number) => ({
  ticker,
  date,
  announced: date,
  abnormal_return: abnormal,
  volatility_change: 0.25,
  volume_spike: 3.2,
});

const DATA: EventImpact = {
  tickers_analyzed: ['AAPL', 'NVDA'],
  events: [
    event('AAPL', '2025-07-31', 0.0412),
    event('AAPL', '2025-05-01', -0.0188),
    event('NVDA', '2025-08-27', -0.0630),
  ],
  by_ticker: {
    AAPL: {
      n_events: 2, mean_abnormal_return: 0.0112, median_abnormal_return: 0.0112,
      mean_abs_abnormal_return: 0.03, positive_share: 0.5,
      mean_volume_spike: 1.89, mean_volatility_change: -0.1,
    },
    NVDA: {
      n_events: 1, mean_abnormal_return: -0.0630, median_abnormal_return: -0.0630,
      mean_abs_abnormal_return: 0.063, positive_share: 0,
      mean_volume_spike: 2.4, mean_volatility_change: 0.32,
    },
  },
  overall: {
    n_events: 3, mean_abnormal_return: -0.0135, median_abnormal_return: -0.0188,
    mean_abs_abnormal_return: 0.041, positive_share: 0.3333,
    mean_volume_spike: 2.8391, mean_volatility_change: 0.1199,
  },
  skipped_count: 2,
  methodology: METHODOLOGY_FALLBACK,
  headlines_by_category: {
    EARNINGS: [{ id: 'e1', headline: 'Chipmaker tops earnings estimates', url: '#' }],
    POLICY: [{ id: 'p1', headline: 'Fed holds rates steady', url: 'https://example.com/fed' }],
  },
};

// ─────────────────────────────────────────────────────────────────────────
// Formatting helpers
// ─────────────────────────────────────────────────────────────────────────

describe('formatting', () => {
  it('formats signed percentages with an explicit sign', () => {
    expect(formatSignedPercent(0.0512)).toBe('+5.1%');
    expect(formatSignedPercent(-0.0512)).toBe('-5.1%');
    expect(formatSignedPercent(0)).toBe('+0.0%');
  });

  it('formats unsigned percentages', () => {
    expect(formatPercent(0.0857)).toBe('8.6%');
    expect(formatPercent(0.3333, 0)).toBe('33%');
  });

  it('formats volume multiples', () => {
    expect(formatMultiple(2.8391)).toBe('2.8x');
    expect(formatMultiple(1)).toBe('1.0x');
  });

  it('returns an em dash rather than NaN for missing numbers', () => {
    expect(formatSignedPercent(NaN)).toBe('—');
    expect(formatPercent(undefined as unknown as number)).toBe('—');
    expect(formatMultiple(Infinity)).toBe('—');
  });

  it('keeps only the newest event per ticker, newest first', () => {
    const rows = latestEventPerTicker(DATA.events);
    expect(rows.map((r) => [r.ticker, r.date])).toEqual([
      ['NVDA', '2025-08-27'],
      ['AAPL', '2025-07-31'],
    ]);
  });

  it('orders the chart by absolute move and converts to percent', () => {
    const bars = abnormalReturnByTicker(DATA.by_ticker);
    expect(bars.map((b) => b.ticker)).toEqual(['NVDA', 'AAPL']);
    expect(bars[0].value).toBeCloseTo(-6.3, 6);
    expect(bars[1].value).toBeCloseTo(1.12, 6);
  });
});

// ─────────────────────────────────────────────────────────────────────────
// Panel rendering
// ─────────────────────────────────────────────────────────────────────────

describe('NewsImpactPanel', () => {
  it('renders the summary tiles from the study', () => {
    render(<NewsImpactPanel data={DATA} />);
    expect(screen.getByText('3')).toBeInTheDocument();      // events analyzed
    expect(screen.getByText('4.1%')).toBeInTheDocument();   // avg abs abnormal return
    expect(screen.getByText('2.8x')).toBeInTheDocument();   // avg volume spike
    expect(screen.getByText('+12.0%')).toBeInTheDocument(); // avg volatility change
    expect(screen.getByText('2 tickers')).toBeInTheDocument();
  });

  it('renders the most recent event per ticker in the table', () => {
    render(<NewsImpactPanel data={DATA} />);
    const table = screen.getByRole('table');
    const rows = within(table).getAllByRole('row').slice(1); // drop the header
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText('NVDA')).toBeInTheDocument();
    expect(within(rows[0]).getByText('-6.3%')).toBeInTheDocument();
    expect(within(rows[1]).getByText('AAPL')).toBeInTheDocument();
    expect(within(rows[1]).getByText('+4.1%')).toBeInTheDocument();
  });

  it('groups todays headlines by category', () => {
    render(<NewsImpactPanel data={DATA} />);
    expect(screen.getByText('EARNINGS · 1')).toBeInTheDocument();
    expect(screen.getByText('POLICY · 1')).toBeInTheDocument();
    expect(screen.getByText('Fed holds rates steady')).toBeInTheDocument();
  });

  it('shows the methodology note and the skipped-event count', () => {
    render(<NewsImpactPanel data={DATA} />);
    expect(
      screen.getByText(/Earnings event study, window day -1 to \+3, abnormal return vs SPY, data from Yahoo Finance/),
    ).toBeInTheDocument();
    expect(screen.getByText(/2 events skipped for missing data/)).toBeInTheDocument();
  });

  it('labels every bar with its signed value, so colour is never the only cue', () => {
    const { container } = render(<NewsImpactPanel data={DATA} />);
    const labels = [...container.querySelectorAll('text')].map((t) => t.textContent);
    expect(labels).toContain('-6.3%');
    expect(labels).toContain('+1.1%');
  });

  it('shows a loading placeholder while the study is running', () => {
    render(<NewsImpactPanel isLoading />);
    expect(screen.getByTestId('news-impact-loading')).toBeInTheDocument();
  });

  it('shows an empty state on error — no sample numbers', () => {
    render(<NewsImpactPanel isError />);
    expect(screen.getByText('No earnings events could be measured')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByText(METHODOLOGY_FALLBACK)).toBeInTheDocument();
  });

  it('shows an empty state when every event was skipped', () => {
    const empty: EventImpact = {
      tickers_analyzed: [], events: [], by_ticker: {}, overall: null,
      skipped_count: 4, methodology: METHODOLOGY_FALLBACK,
    };
    render(<NewsImpactPanel data={empty} />);
    expect(screen.getByText('No earnings events could be measured')).toBeInTheDocument();
    expect(screen.getByText(/4 events skipped for missing price or earnings data/)).toBeInTheDocument();
  });

  it('shows an empty state when there is no data at all', () => {
    render(<NewsImpactPanel />);
    expect(screen.getByText('No earnings events could be measured')).toBeInTheDocument();
    expect(
      screen.getByText(/Add holdings with reported earnings to see their historical reaction/),
    ).toBeInTheDocument();
  });
});
