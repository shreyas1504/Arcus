/**
 * These tests exist to stop sample data creeping back into the Results page.
 *
 * Every one of these components used to fall back to a MOCK_* constant when its
 * prop was missing, so an unreachable backend rendered a complete, plausible,
 * entirely fictional portfolio analysis. They must render an empty state
 * instead.
 */
import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import DataUnavailable from '@/components/DataUnavailable';
import PerformanceChart from '@/components/charts/PerformanceChart';
import DrawdownChart from '@/components/charts/DrawdownChart';
import MonteCarloChart from '@/components/charts/MonteCarloChart';
import RiskAttribution from '@/components/charts/RiskAttribution';
import SectorDonut from '@/components/charts/SectorDonut';
import EfficientFrontier from '@/components/charts/EfficientFrontier';
import CorrelationHeatmap from '@/components/CorrelationHeatmap';
import StressTestGrid from '@/components/StressTestGrid';

let rectSpy: ReturnType<typeof vi.spyOn>;
beforeAll(() => {
  rectSpy = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    width: 600, height: 240, top: 0, left: 0, right: 600, bottom: 240, x: 0, y: 0, toJSON: () => ({}),
  } as DOMRect);
});
afterAll(() => rectSpy.mockRestore());

describe('DataUnavailable', () => {
  it('names the thing that is missing', () => {
    render(<DataUnavailable label="Drawdown" />);
    expect(screen.getByText('Drawdown unavailable')).toBeInTheDocument();
  });

  it('falls back to a generic label', () => {
    render(<DataUnavailable />);
    expect(screen.getByText('Data unavailable')).toBeInTheDocument();
  });
});

// Each entry: component, and the sample values it used to invent.
const CHARTS: Array<[string, () => JSX.Element, (string | RegExp)[]]> = [
  ['PerformanceChart', () => <PerformanceChart />, []],
  ['DrawdownChart', () => <DrawdownChart />, []],
  ['MonteCarloChart', () => <MonteCarloChart />, []],
  ['RiskAttribution', () => <RiskAttribution />, [/NVDA/, /34\.2/]],
  ['SectorDonut', () => <SectorDonut />, [/Technology/, /65%/]],
  ['EfficientFrontier', () => <EfficientFrontier />, []],
  ['CorrelationHeatmap', () => <CorrelationHeatmap />, [/GOOGL/, /0\.88/]],
  ['StressTestGrid', () => <StressTestGrid />, [/2008 FINANCIAL CRISIS/, /512 days/]],
];

describe.each(CHARTS)('%s with no data', (name, renderFn, forbidden) => {
  it('renders an empty state, not sample data', () => {
    const { container } = render(renderFn());
    expect(container.querySelector('[data-testid="data-unavailable"]')).not.toBeNull();
  });

  it('renders none of the values it used to invent', () => {
    const { container } = render(renderFn());
    for (const pattern of forbidden) {
      expect(container.textContent ?? '').not.toMatch(pattern);
    }
  });
});

describe('charts still render real data when they have it', () => {
  it('RiskAttribution renders a chart, not an empty state', () => {
    // happy-dom does not lay out Recharts category ticks, so assert on the
    // chart surface rather than the tick text.
    const { container } = render(<RiskAttribution data={[{ ticker: 'ZZZZ', contribution: 12.5, color: '#38BDA4' }]} />);
    expect(container.querySelector('svg.recharts-surface')).not.toBeNull();
    expect(screen.queryByTestId('data-unavailable')).not.toBeInTheDocument();
  });

  it('StressTestGrid renders the scenarios it was given', () => {
    render(<StressTestGrid data={[{ name: 'CUSTOM SCENARIO', loss: -12.3, recoveryDays: 90 }]} />);
    expect(screen.getByText('CUSTOM SCENARIO')).toBeInTheDocument();
    expect(screen.queryByTestId('data-unavailable')).not.toBeInTheDocument();
  });

  it('CorrelationHeatmap renders the matrix it was given', () => {
    render(<CorrelationHeatmap data={{ tickers: ['AAA', 'BBB'], matrix: [[1, 0.5], [0.5, 1]] }} />);
    expect(screen.getAllByText('AAA').length).toBeGreaterThan(0);
    expect(screen.queryByTestId('data-unavailable')).not.toBeInTheDocument();
  });

  it('SectorDonut renders the breakdown it was given', () => {
    render(<SectorDonut data={[{ name: 'Energy', value: 100, color: '#F0514F' }]} />);
    expect(screen.queryByTestId('data-unavailable')).not.toBeInTheDocument();
  });
});

describe('no component imports sample data any more', () => {
  it('the mock module is not reachable from the Results charts', async () => {
    // A direct import would let a future change re-add a silent fallback.
    const sources = import.meta.glob(
      [
        '../components/charts/*.tsx',
        '../components/CorrelationHeatmap.tsx',
        '../components/StressTestGrid.tsx',
        '../components/DataUnavailable.tsx',
      ],
      { query: '?raw', import: 'default', eager: true },
    ) as Record<string, string>;

    const offenders = Object.entries(sources)
      .filter(([, src]) => src.includes('mock-data'))
      .map(([path]) => path);

    expect(offenders).toEqual([]);
  });
});
