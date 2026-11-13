import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import fixture from '@/lib/__fixtures__/whatif-response-v2.json';
import type { WhatIfResponseV2 } from '@/lib/scenario';
import ScenarioLab from '../ScenarioLab';

const response = fixture as unknown as WhatIfResponseV2;

function jsonResponse(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

type Reply = ReturnType<typeof jsonResponse> | Error;

/** Answers /api/scenario/whatif with `replies` in order; other app requests get an empty body. */
function mockFetch(...replies: Reply[]) {
  const queue = [...replies];
  const fn = vi.fn(async (url: string) => {
    if (!String(url).includes('/api/scenario/whatif')) return jsonResponse({});
    const reply = queue.length > 1 ? queue.shift()! : queue[0];
    if (reply instanceof Error) throw reply;
    return reply;
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

function whatifBodies(fn: ReturnType<typeof mockFetch>) {
  return fn.mock.calls
    .filter(([url]) => String(url).includes('/api/scenario/whatif'))
    .map((call) => JSON.parse((call as unknown as [string, RequestInit])[1].body as string));
}

function seedPortfolio() {
  localStorage.setItem('arcus-last-analysis', JSON.stringify({ tickers: ['DEMO1', 'DEMO2', 'DEMO3'], weights: [0.5, 0.3, 0.2] }));
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/dashboard/scenarios']}>
        <ScenarioLab />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function ask(question = 'What if China blockades Taiwan?') {
  fireEvent.change(screen.getByLabelText('Describe a scenario'), { target: { value: question } });
  fireEvent.click(screen.getByRole('button', { name: /run scenario/i }));
}

beforeEach(() => {
  localStorage.clear();
  seedPortfolio();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe('ScenarioLab v2', () => {
  it('renders the v2 fixture: scenario table, exposure, span, crises, resilience and limits', async () => {
    const fetchMock = mockFetch(jsonResponse(response));
    renderPage();
    ask();

    expect(await screen.findByTestId('scenario-result')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-table')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-row-DEMO1')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-row-DEMO2')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-col-example-strait-closure')).toHaveTextContent('Example: strait closure');

    const span = screen.getByTestId('historical-span');
    expect(span).toHaveTextContent('Historical span');
    expect(span).toHaveTextContent('−7.4%');
    expect(span).toHaveTextContent('−2.8%');
    expect(span).toHaveTextContent(/history/i);

    expect(screen.getByTestId('exposure-ranking')).toBeInTheDocument();
    expect(screen.getByTestId('exposure-DEMO1')).toHaveTextContent('3 of 3');

    expect(screen.getByTestId('crisis-replay')).toBeInTheDocument();
    expect(screen.getByTestId('crisis-example-bank-collapse')).toHaveTextContent('Example: bank collapse');
    expect(screen.getByTestId('crisis-example-pandemic-crash')).toBeInTheDocument();

    const resilience = screen.getByTestId('resilience-summary');
    expect(resilience).toHaveTextContent('1 of 2');
    expect(resilience).toHaveTextContent('DEMO1');

    expect(screen.getByTestId('limits')).toHaveTextContent(/cannot predict/i);
    expect(screen.getByTestId('limits')).toHaveTextContent(/today's holdings/i);
    expect(screen.getByTestId('accuracy-panel')).toBeInTheDocument();

    const [body] = whatifBodies(fetchMock);
    expect(body.scenario).toBe('What if China blockades Taiwan?');
    expect(body.severity).toBe('typical');
    expect(body.holdings.map((h: { ticker: string }) => h.ticker)).toEqual(['DEMO1', 'DEMO2', 'DEMO3']);
  });

  it('tags holdings in the scenario table as actual or estimated', async () => {
    mockFetch(jsonResponse(response));
    renderPage();
    ask();

    const row = await screen.findByTestId('scenario-row-DEMO1');
    expect(within(row).getAllByText('Actual').length).toBeGreaterThan(0);
    expect(within(row).getAllByText('Estimated').length).toBeGreaterThan(0);
  });

  it('shows the low-confidence badge with its explanation', async () => {
    mockFetch(jsonResponse({
      ...response,
      confidence: 'low',
      scenarios: [],
      span_low: null,
      span_high: null,
      exposure: [],
    }));
    renderPage();
    ask();

    const badge = await screen.findByTestId('low-confidence');
    expect(badge).toHaveAttribute('role', 'status');
    expect(badge).toHaveTextContent(/low confidence/i);
    expect(badge).toHaveTextContent(/no past event is a close match/i);
    expect(screen.queryByTestId('scenario-table')).not.toBeInTheDocument();
    expect(screen.queryByTestId('historical-span')).not.toBeInTheDocument();
    expect(screen.getByTestId('crisis-replay')).toBeInTheDocument();
  });

  it('hides the badge at normal confidence', async () => {
    mockFetch(jsonResponse(response));
    renderPage();
    ask();

    await screen.findByTestId('scenario-result');
    expect(screen.queryByTestId('low-confidence')).not.toBeInTheDocument();
  });

  it.each([
    [429, { detail: { message: 'Daily limit reached.' } }, /daily limit reached/i],
    [503, { detail: { status: 'warming' } }, /temporarily unavailable/i],
  ])('shows a message, not zeros, on HTTP %i', async (status, body, message) => {
    mockFetch(jsonResponse(body, status));
    renderPage();
    ask();

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.queryByTestId('scenario-result')).not.toBeInTheDocument();
    expect(screen.queryByTestId('historical-span')).not.toBeInTheDocument();
    expect(screen.queryByText(/0\.0%/)).not.toBeInTheDocument();
  });

  it('shows a message, not zeros, on a network error', async () => {
    mockFetch(new TypeError('Failed to fetch'));
    renderPage();
    ask();

    expect(await screen.findByRole('alert')).toHaveTextContent(/could not reach the arcus server/i);
    expect(screen.queryByTestId('scenario-result')).not.toBeInTheDocument();
    expect(screen.queryByText(/0\.0%/)).not.toBeInTheDocument();
  });

  it('shows crises and limits when there are no close scenario matches', async () => {
    mockFetch(jsonResponse({
      ...response,
      confidence: 'low',
      scenarios: [],
      span_low: null,
      span_high: null,
      exposure: [],
    }));
    renderPage();
    ask();

    await screen.findByTestId('scenario-result');
    expect(screen.queryByTestId('scenario-table')).not.toBeInTheDocument();
    expect(screen.getByTestId('crisis-replay')).toBeInTheDocument();
    expect(screen.getByTestId('limits')).toBeInTheDocument();
  });

  it('lists skipped tickers without inventing numbers for them', async () => {
    mockFetch(jsonResponse({
      ...response,
      skipped: [{ ticker: 'ZZZZ', reason: 'no price history' }],
    }));
    renderPage();
    ask();

    const skipped = await screen.findByTestId('skipped');
    expect(skipped).toHaveTextContent('ZZZZ');
    expect(skipped).toHaveTextContent('no price history');
  });

  it('shows the empty portfolio state when there are no holdings', async () => {
    localStorage.clear();
    mockFetch(jsonResponse(response));
    renderPage();

    expect(screen.getByText(/no portfolio found/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /run scenario/i })).not.toBeInTheDocument();
  });

  it('fills an example question into the form', async () => {
    mockFetch(jsonResponse(response));
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /what if a major us bank fails/i }));
    expect(screen.getByLabelText('Describe a scenario')).toHaveValue('What if a major US bank fails?');
  });

  it('disables submit while a request is in flight', async () => {
    let resolveRequest: (value: ReturnType<typeof jsonResponse>) => void = () => undefined;
    const pending = new Promise<ReturnType<typeof jsonResponse>>((resolve) => {
      resolveRequest = resolve;
    });
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (!String(url).includes('/api/scenario/whatif')) return jsonResponse({});
      return pending;
    }));
    renderPage();
    ask();
    expect(await screen.findByRole('button', { name: /replaying shocks/i })).toBeDisabled();
    resolveRequest(jsonResponse(response));
    await waitFor(() => expect(screen.getByRole('button', { name: /run scenario/i })).toBeEnabled());
  });
});
