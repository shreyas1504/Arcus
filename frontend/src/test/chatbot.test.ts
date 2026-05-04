import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { sendChatMessage } from '@/lib/api';
import { openArcusChat, consumePendingArcusChatMessage, ARCUS_CHAT_EVENT } from '@/lib/chat-launcher';
import { buildChatPortfolioContext, derivePortfolioWeights } from '@/lib/portfolio-context';
import { portfolioToRequest } from '@/hooks/use-portfolio';

describe('chatbot portfolio context', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('derives value-weighted portfolio weights from shares and live prices', () => {
    const weights = derivePortfolioWeights(
      [
        { ticker: 'AAPL', shares: '10', cost: '150' },
        { ticker: 'MSFT', shares: '5', cost: '300' },
      ],
      { AAPL: 200, MSFT: 400 },
    );

    expect(weights[0]).toBeCloseTo(0.5, 3);
    expect(weights[1]).toBeCloseTo(0.5, 3);
    expect(weights.reduce((sum, value) => sum + value, 0)).toBeCloseTo(1, 6);
  });

  it('falls back to cost basis and equal-weight defaults when pricing is missing', () => {
    const costWeighted = derivePortfolioWeights(
      [
        { ticker: 'AAPL', shares: '10', cost: '100' },
        { ticker: 'MSFT', shares: '5', cost: '400' },
      ],
    );
    expect(costWeighted[0]).toBeCloseTo(1 / 3, 3);
    expect(costWeighted[1]).toBeCloseTo(2 / 3, 3);

    const equalWeighted = derivePortfolioWeights([
      { ticker: 'AAPL' },
      { ticker: 'MSFT' },
      { ticker: 'VOO' },
    ]);
    expect(equalWeighted).toEqual([1 / 3, 1 / 3, 1 / 3]);
  });

  it('builds chat context from latest analysis when analysis exists', () => {
    localStorage.setItem('arcus-last-analysis', JSON.stringify({
      tickers: ['AAPL', 'MSFT'],
      weights: [0.7, 0.3],
      latest_prices: { AAPL: 210.12, MSFT: 401.55 },
      metrics: {
        health_score: 82,
        sharpe: 1.46,
        var_95: -0.031,
        cvar_95: -0.044,
        beta: 1.08,
        max_drawdown: -0.18,
        annualized_return: 0.16,
        volatility: 0.19,
      },
    }));
    localStorage.setItem('arcus-investor-dna', JSON.stringify({
      risk_tolerance: 'Growth',
      target_return: 0.15,
    }));
    localStorage.setItem('arcus-portfolio', JSON.stringify({
      holdings: [
        { ticker: 'AAPL', shares: '10', cost: '150' },
        { ticker: 'MSFT', shares: '5', cost: '250' },
      ],
      livePrices: { AAPL: 210.12, MSFT: 401.55 },
    }));

    const context = buildChatPortfolioContext();
    expect(context).toBeDefined();
    expect(context?.holdings).toEqual([
      { ticker: 'AAPL', weight: 0.7, currentPrice: 210.12 },
      { ticker: 'MSFT', weight: 0.3, currentPrice: 401.55 },
    ]);
    expect(context?.metrics.healthScore).toBe(82);
    expect(context?.investorProfile.riskTolerance).toBe('Growth');
  });

  it('falls back to saved holdings when no analysis is cached', () => {
    localStorage.setItem('arcus-investor-dna', JSON.stringify({
      risk_tolerance: 'Moderate',
      target_return: 0.1,
    }));
    localStorage.setItem('arcus-portfolio', JSON.stringify({
      holdings: [
        { ticker: 'AAPL', shares: '10', cost: '100' },
        { ticker: 'MSFT', shares: '5', cost: '400' },
      ],
    }));

    const context = buildChatPortfolioContext();
    expect(context?.holdings.map((holding) => holding.ticker)).toEqual(['AAPL', 'MSFT']);
    expect(context?.holdings[0].weight).toBeCloseTo(1 / 3, 3);
    expect(context?.holdings[1].weight).toBeCloseTo(2 / 3, 3);
    expect(context?.investorProfile.targetReturn).toBe(0.1);
  });

  it('forms portfolio analysis requests using value-based weights', () => {
    const request = portfolioToRequest(
      {
        holdings: [
          { ticker: 'AAPL', shares: '10', cost: '100' },
          { ticker: 'MSFT', shares: '5', cost: '400' },
        ],
        livePrices: { AAPL: 200, MSFT: 400 },
        startDate: '2023-01-01',
        endDate: '2024-12-31',
      },
      { riskFreeRate: 0.04, benchmark: 'SPY' },
    );

    expect(request?.tickers).toEqual(['AAPL', 'MSFT']);
    expect(request?.weights[0]).toBeCloseTo(0.5, 3);
    expect(request?.weights[1]).toBeCloseTo(0.5, 3);
    expect(request?.risk_free_rate).toBe(0.04);
    expect(request?.benchmark).toBe('SPY');
  });
});

describe('chat launcher flow', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('stores and dispatches trimmed Ask AI prompts', () => {
    const handler = vi.fn();
    window.addEventListener(ARCUS_CHAT_EVENT, handler);

    openArcusChat('  Explain my Sharpe ratio  ');

    expect(sessionStorage.getItem('arcus-chat-pending-message')).toBe('Explain my Sharpe ratio');
    expect(handler).toHaveBeenCalledTimes(1);
    const event = handler.mock.calls[0][0] as CustomEvent<{ message: string }>;
    expect(event.detail.message).toBe('Explain my Sharpe ratio');

    window.removeEventListener(ARCUS_CHAT_EVENT, handler);
  });

  it('consumes pending prompts exactly once', () => {
    sessionStorage.setItem('arcus-chat-pending-message', 'What is my biggest risk?');

    expect(consumePendingArcusChatMessage()).toBe('What is my biggest risk?');
    expect(consumePendingArcusChatMessage()).toBe('');
  });
});

describe('chat API behavior', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('returns a live AI reply from the primary endpoint', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ reply: 'Your largest risk is concentration in NVDA.' }),
    } as Response);

    const result = await sendChatMessage('What is my biggest risk?', {
      holdings: [{ ticker: 'NVDA', weight: 0.4, currentPrice: 900 }],
      metrics: { healthScore: 62, sharpe: 1.1, var95: -0.03, cvar: -0.05, beta: 1.3, maxDrawdown: -0.26 },
      investorProfile: { riskTolerance: 'Growth', targetReturn: 0.15 },
    });

    expect(result.reply).toContain('largest risk');
    expect(result.fallback).toBeUndefined();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('falls back to the secondary endpoint after a primary 503', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ reply: 'The backend fallback answered your question.' }),
      } as Response);

    const result = await sendChatMessage('How should I rebalance?');

    expect(result.reply).toContain('fallback answered');
    expect(result.fallback).toBeUndefined();
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it('returns offline guidance when both online endpoints fail', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response);

    const result = await sendChatMessage('Explain Sharpe ratio');

    expect(result.fallback).toBe(true);
    expect(result.status503).toBe(true);
    expect(result.reply).toContain('Sharpe Ratio');
  });

  it('returns a portfolio-specific summary when the user asks for a current portfolio overview and live APIs fail', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response);

    const result = await sendChatMessage('Give summary of my current portfolio', {
      holdings: [
        { ticker: 'AAPL', weight: 0.5, currentPrice: 200 },
        { ticker: 'MSFT', weight: 0.3, currentPrice: 400 },
        { ticker: 'VOO', weight: 0.2, currentPrice: 500 },
      ],
      metrics: {
        healthScore: 72,
        sharpe: 1.24,
        var95: -0.028,
        cvar: -0.041,
        beta: 1.07,
        maxDrawdown: -0.18,
        annualizedReturn: 0.14,
        volatility: 0.19,
      },
      investorProfile: { riskTolerance: 'Moderate', targetReturn: 0.1 },
    });

    expect(result.fallback).toBe(true);
    expect(result.reply).toContain('Current Portfolio Summary');
    expect(result.reply).toContain('Health Score: **72/100**');
    expect(result.reply).toContain('Top holdings: **AAPL 50%, MSFT 30%, VOO 20%**');
  });

  it('returns a metric-specific portfolio answer for Ask AI prompts when live APIs fail', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response);

    const result = await sendChatMessage(
      'My Sharpe ratio is 1.24. Explain what this means in simple terms and whether it is good or bad for my portfolio.',
      {
        holdings: [
          { ticker: 'NVDA', weight: 0.4, currentPrice: 900 },
          { ticker: 'MSFT', weight: 0.35, currentPrice: 400 },
          { ticker: 'VOO', weight: 0.25, currentPrice: 500 },
        ],
        metrics: {
          healthScore: 68,
          sharpe: 1.24,
          var95: -0.031,
          cvar: -0.045,
          beta: 1.19,
          maxDrawdown: -0.22,
          annualizedReturn: 0.15,
          volatility: 0.21,
        },
        investorProfile: { riskTolerance: 'Growth', targetReturn: 0.15 },
      },
    );

    expect(result.fallback).toBe(true);
    expect(result.reply).toContain('Sharpe Ratio');
    expect(result.reply).toContain('Your Sharpe is **1.24**');
    expect(result.reply).toContain('holding is hurting Sharpe the most');
  });

  it('returns offline guidance when fetch throws unexpectedly', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('network down'));

    const result = await sendChatMessage('How risky is my portfolio?');

    expect(result.fallback).toBe(true);
    expect(result.reply).toContain('Portfolio Risk');
  });

  it('uses the offline generic helper for arbitrary questions when all endpoints fail', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response);

    const result = await sendChatMessage('Hello there');

    expect(result.fallback).toBe(true);
    expect(result.reply).toContain('Arcus AI');
  });
});
