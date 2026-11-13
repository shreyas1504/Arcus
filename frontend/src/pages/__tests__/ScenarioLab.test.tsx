import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import fixture from '@/lib/__fixtures__/whatif-response.json';
import type { WhatIfResponse } from '@/lib/scenario';
import ScenarioLab from '../ScenarioLab';

const response = fixture as unknown as WhatIfResponse;

const severeResponse: WhatIfResponse = {
  ...response,
  severity: 'severe',
  portfolio: { ...response.portfolio!, severity: 'severe', typical_return: -0.0912 },
};

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
  localStorage.setItem('arcus-last-analysis', JSON.stringify({ tickers: ['DEMO1', 'DEMO2'], weights: [0.6, 0.4] }));
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

describe('ScenarioLab', () => {
  it('renders the fixture: range bar, precedent cards, path chart and holding rows', async () => {
    const fetchMock = mockFetch(jsonResponse(response));
    renderPage();
    ask();

    expect(await screen.findByTestId('scenario-result')).toBeInTheDocument();
    expect(screen.getByTestId('range-bar')).toBeInTheDocument();
    expect(screen.getByTestId('typical-return')).toHaveTextContent('−5.4%');
    expect(screen.getByTestId('path-chart')).toBeInTheDocument();
    for (const precedent of response.precedents) {
      expect(screen.getByTestId(`precedent-${precedent.event_id}`)).toHaveTextContent(precedent.name);
    }
    expect(screen.getByTestId('holding-DEMO1')).toBeInTheDocument();
    expect(screen.getByTestId('holding-DEMO2')).toBeInTheDocument();
    expect(screen.getByTestId('accuracy-panel')).toBeInTheDocument();

    const [body] = whatifBodies(fetchMock);
    expect(body.scenario).toBe('What if China blockades Taiwan?');
    expect(body.severity).toBe('typical');
    expect(body.holdings.map((h: { ticker: string }) => h.ticker)).toEqual(['DEMO1', 'DEMO2']);
  });

  it('tags each holding as actual or estimated', async () => {
    mockFetch(jsonResponse(response));
    renderPage();
    ask();

    expect(within(await screen.findByTestId('holding-DEMO1')).getByText('Actual')).toBeInTheDocument();
    expect(within(screen.getByTestId('holding-DEMO2')).getByText('Estimated')).toBeInTheDocument();
  });

  it('shows the low-confidence badge with its explanation', async () => {
    mockFetch(jsonResponse({ ...response, confidence: 'low' }));
    renderPage();
    ask();

    const badge = await screen.findByTestId('low-confidence');
    expect(badge).toHaveAttribute('role', 'status');
    expect(badge).toHaveTextContent(/low confidence/i);
    expect(badge).toHaveTextContent(/no past event is a close match/i);
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
    // No message field: the client uses its default copy (matches the backend's 503 wording).
    [503, { detail: { status: 'warming' } }, /temporarily unavailable/i],
  ])('shows a message, not zeros, on HTTP %i', async (status, body, message) => {
    mockFetch(jsonResponse(body, status));
    renderPage();
    ask();

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.queryByTestId('scenario-result')).not.toBeInTheDocument();
    expect(screen.queryByTestId('typical-return')).not.toBeInTheDocument();
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

  it('shows an empty state instead of numbers when the portfolio outcome is missing', async () => {
    mockFetch(jsonResponse({ ...response, portfolio: null, holdings: [], paths: [] }));
    renderPage();
    ask();

    expect(await screen.findByTestId('empty-outcome')).toBeInTheDocument();
    expect(screen.queryByTestId('typical-return')).not.toBeInTheDocument();
    expect(screen.queryByTestId('range-bar')).not.toBeInTheDocument();
  });

  it('asks for a portfolio when none is saved', () => {
    localStorage.clear();
    const fetchMock = mockFetch();
    renderPage();

    expect(screen.getByText('No portfolio found')).toBeInTheDocument();
    expect(screen.queryByLabelText('Describe a scenario')).not.toBeInTheDocument();
    expect(whatifBodies(fetchMock)).toEqual([]);
  });

  it('re-runs the request when the severity changes and updates the outcome', async () => {
    const fetchMock = mockFetch(jsonResponse(response), jsonResponse(severeResponse));
    renderPage();
    ask();

    expect(await screen.findByTestId('typical-return')).toHaveTextContent('−5.4%');
    fireEvent.click(screen.getByRole('radio', { name: 'Severe' }));

    await waitFor(() => expect(screen.getByTestId('typical-return')).toHaveTextContent('−9.1%'));
    expect(whatifBodies(fetchMock)).toHaveLength(2);
    expect(whatifBodies(fetchMock)[1].severity).toBe('severe');
    expect(screen.getByRole('radio', { name: 'Severe' })).toHaveAttribute('aria-checked', 'true');
  });

  it('opens source links in a new tab safely', async () => {
    mockFetch(jsonResponse(response));
    renderPage();
    ask();

    for (const precedent of response.precedents) {
      const link = within(await screen.findByTestId(`precedent-${precedent.event_id}`)).getByRole('link', { name: /source/i });
      expect(link).toHaveAttribute('href', precedent.source_url);
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    }
  });

  it('has labelled inputs and a text summary for the chart', async () => {
    mockFetch(jsonResponse(response));
    renderPage();

    expect(screen.getByLabelText('Describe a scenario').tagName).toBe('TEXTAREA');
    const group = screen.getByRole('radiogroup', { name: 'Severity' });
    expect(within(group).getAllByRole('radio').map((radio) => radio.textContent)).toEqual(['Mild', 'Typical', 'Severe']);

    ask();
    const chart = await screen.findByRole('img');
    const summaryId = chart.getAttribute('aria-describedby');
    expect(summaryId).toBeTruthy();
    const summary = document.getElementById(summaryId!);
    expect(summary).toHaveTextContent(/cumulative return/i);
    expect(summary).toHaveTextContent(response.precedents[0].name);
  });
});

describe('feature flag', () => {
  async function renderSidebar() {
    vi.resetModules();
    const { default: Sidebar } = await import('@/components/Sidebar');
    return render(
      <MemoryRouter>
        <Sidebar collapsed={false} setCollapsed={() => {}} mobileOpen={false} setMobileOpen={() => {}} isMobile={false} />
      </MemoryRouter>,
    );
  }

  async function renderAppAt(path: string) {
    vi.resetModules();
    window.history.pushState({}, '', path);
    const { default: App } = await import('@/App');
    return render(<App />);
  }

  it('flag off: no sidebar item and no route', async () => {
    vi.stubEnv('VITE_ENABLE_SCENARIOS', 'false');
    await renderSidebar();
    expect(screen.queryByText('Scenario Lab')).not.toBeInTheDocument();
    expect(document.querySelector('a[href="/dashboard/scenarios"]')).toBeNull();
  });

  it('flag off: the scenarios route falls through to not found', async () => {
    vi.stubEnv('VITE_ENABLE_SCENARIOS', 'false');
    await renderAppAt('/dashboard/scenarios');
    expect(screen.queryByLabelText('Describe a scenario')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Scenario Lab' })).not.toBeInTheDocument();
  });

  it('flag on: the sidebar item appears', async () => {
    vi.stubEnv('VITE_ENABLE_SCENARIOS', 'true');
    await renderSidebar();
    expect(document.querySelector('a[href="/dashboard/scenarios"]')).not.toBeNull();
  });
});
