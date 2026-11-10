import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { askResearch, getResearchClientId, ResearchCitation } from '@/lib/api';
import { supportedPortfolioTickers } from '@/lib/research';
import { ResearchAnswer } from '@/pages/Research';

const citation: ResearchCitation = {
  citation: 1,
  chunk_id: 'AAPL:test:1',
  ticker: 'AAPL',
  form: '10-K',
  filing_date: '2025-09-27',
  year: '2025',
  section: 'Item 1A Risk Factors',
  url: 'https://www.sec.gov/Archives/example.htm',
  excerpt: 'The company depends on third-party manufacturing.',
};

describe('Arcus Research', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('keeps only unique indexed portfolio tickers', () => {
    expect(supportedPortfolioTickers([
      { ticker: 'aapl' },
      { ticker: 'AAPL' },
      { ticker: 'BRK.B' },
      { ticker: 'SPY' },
    ])).toEqual(['AAPL', 'BRK-B']);
  });

  it('renders model citations as safe SEC links', () => {
    render(
      <ResearchAnswer
        answer="Apple identifies manufacturing dependency as a risk [1]."
        citations={[citation]}
      />,
    );
    const inline = screen.getByLabelText('Open citation 1 on SEC.gov');
    expect(inline).toHaveAttribute('href', citation.url);
    expect(inline).toHaveAttribute('rel', 'noreferrer');
    expect(screen.getByText('Item 1A Risk Factors')).toBeInTheDocument();
  });

  it('renders the exact not-found response without sources', () => {
    render(<ResearchAnswer answer="Not found in the filings." citations={[]} />);
    expect(screen.getByText('Not found in the filings.')).toBeInTheDocument();
    expect(screen.queryByText('SEC sources')).not.toBeInTheDocument();
  });

  it('persists an anonymous research client id', () => {
    const first = getResearchClientId();
    const second = getResearchClientId();
    expect(first).toBe(second);
    expect(localStorage.getItem('arcus-research-client-id')).toBe(first);
  });

  it('sends the question, selected tickers, and client id', async () => {
    localStorage.setItem('arcus-research-client-id', 'research_test_client_123');
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        answer: 'Answer [1].',
        citations: [citation],
        latency_ms: 900,
        retrieved_sections: ['AAPL:Item 1A Risk Factors'],
        remaining_today: 19,
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await askResearch('What are the risks?', ['AAPL']);

    const [, options] = fetchMock.mock.calls[0];
    expect(JSON.parse(options.body)).toEqual({
      question: 'What are the risks?',
      tickers: ['AAPL'],
      client_id: 'research_test_client_123',
    });
  });

  it('surfaces the backend quota message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({
        detail: { message: 'Daily research limit reached', remaining: 0 },
      }),
    }));

    await expect(askResearch('Question?', ['AAPL']))
      .rejects.toThrow('Daily research limit reached');
  });
});

