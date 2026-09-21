import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const getSentiment = vi.fn();
vi.mock('@/lib/api', () => ({ getSentiment: (t: string) => getSentiment(t) }));

import SentimentBadge, { SentimentPill } from '@/components/SentimentBadge';

const renderWithQuery = (ui: React.ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

describe('SentimentPill', () => {
  it('renders the label and headline count', () => {
    render(<SentimentPill sentiment={{ ticker: 'AAPL', score: 0.42, label: 'BULLISH', confidence: 0.84, headline_count: 7 }} />);
    expect(screen.getByText('BULLISH')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('colours BULLISH green, BEARISH red and NEUTRAL grey', () => {
    const base = { ticker: 'AAPL', score: 0, confidence: 0, headline_count: 1 };
    const { container: bull } = render(<SentimentPill sentiment={{ ...base, label: 'BULLISH' }} />);
    const { container: bear } = render(<SentimentPill sentiment={{ ...base, label: 'BEARISH' }} />);
    const { container: neut } = render(<SentimentPill sentiment={{ ...base, label: 'NEUTRAL' }} />);
    expect(bull.querySelector('span')?.className).toContain('text-signal-green');
    expect(bear.querySelector('span')?.className).toContain('text-signal-red');
    expect(neut.querySelector('span')?.className).toContain('text-muted-foreground');
  });
});

describe('SentimentBadge', () => {
  beforeEach(() => {
    getSentiment.mockReset();
  });

  it('shows a loading placeholder while the request is in flight', () => {
    getSentiment.mockReturnValue(new Promise(() => {}));
    renderWithQuery(<SentimentBadge ticker="AAPL" />);
    expect(screen.getByTestId('sentiment-loading')).toBeInTheDocument();
  });

  it('renders the sentiment once loaded', async () => {
    getSentiment.mockResolvedValue({ ticker: 'MSFT', score: -0.3, label: 'BEARISH', confidence: 0.6, headline_count: 4 });
    renderWithQuery(<SentimentBadge ticker="MSFT" />);
    await waitFor(() => expect(screen.getByText('BEARISH')).toBeInTheDocument());
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('falls back to an em dash when the request fails — never a fabricated label', async () => {
    getSentiment.mockRejectedValue(new Error('backend down'));
    renderWithQuery(<SentimentBadge ticker="NVDA" />);
    // the badge retries once before giving up, so allow for the retry delay
    await waitFor(() => expect(screen.getByText('—')).toBeInTheDocument(), { timeout: 5000 });
    expect(screen.queryByText('NEUTRAL')).not.toBeInTheDocument();
  });

  it('falls back to an em dash when there are no headlines', async () => {
    getSentiment.mockResolvedValue({ ticker: 'XYZ', score: 0, label: 'NEUTRAL', confidence: 0, headline_count: 0 });
    renderWithQuery(<SentimentBadge ticker="XYZ" />);
    await waitFor(() => expect(screen.getByText('—')).toBeInTheDocument());
  });
});
