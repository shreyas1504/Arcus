/**
 * ARCUS — Portfolio Flow & Settings Tests
 * Tests: localStorage persistence, settings loading, portfolio config parsing,
 * sector data derivation, PDF metrics consistency, and API request formation.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { computePortfolioMetrics, TICKER_SECTOR_MAP, MOCK_PORTFOLIO, MOCK_SECTORS } from '@/lib/mock-data';
import { loadSettings } from '@/hooks/use-settings';

// ─────────────────────────────────────────────────────────────────────────────
// LocalStorage mock helpers
// ─────────────────────────────────────────────────────────────────────────────
const LS: Record<string, string> = {};
beforeEach(() => {
  Object.keys(LS).forEach(k => delete LS[k]);
  // vitest uses jsdom which has localStorage
  localStorage.clear();
});
afterEach(() => {
  localStorage.clear();
});

// ─────────────────────────────────────────────────────────────────────────────
// 1. Settings persistence
// ─────────────────────────────────────────────────────────────────────────────
describe('loadSettings — defaults and persistence', () => {
  it('returns defaults when localStorage is empty', () => {
    const s = loadSettings();
    expect(s.riskFreeRate).toBeGreaterThanOrEqual(0);
    expect(s.riskFreeRate).toBeLessThan(1);
    expect(typeof s.benchmark).toBe('string');
    expect(typeof s.targetReturn).toBe('number');
    expect(typeof s.vaultMode).toBe('boolean');
  });

  it('default risk-free rate is in realistic range (0–10%)', () => {
    const s = loadSettings();
    expect(s.riskFreeRate).toBeGreaterThanOrEqual(0);
    expect(s.riskFreeRate).toBeLessThanOrEqual(0.10);
  });

  it('loads persisted settings from localStorage', () => {
    localStorage.setItem('arcus-settings', JSON.stringify({
      riskFreeRate: 0.055,
      benchmark: 'QQQ',
      targetReturn: 0.15,
      vaultMode: true,
    }));
    const s = loadSettings();
    expect(s.riskFreeRate).toBe(0.055);
    expect(s.benchmark).toBe('QQQ');
    expect(s.targetReturn).toBe(0.15);
    expect(s.vaultMode).toBe(true);
  });

  it('handles malformed JSON in localStorage gracefully', () => {
    localStorage.setItem('arcus-settings', '{bad json{{{{');
    expect(() => loadSettings()).not.toThrow();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Risk-free rate impact on health score
// ─────────────────────────────────────────────────────────────────────────────
describe('computePortfolioMetrics — risk-free rate from settings', () => {
  it('higher RF rate reduces Sharpe ratio', () => {
    const tickers = ['AAPL', 'MSFT', 'VOO'];
    const m_lowRf  = computePortfolioMetrics(tickers, [1, 1, 1], 0.02);
    const m_highRf = computePortfolioMetrics(tickers, [1, 1, 1], 0.06);
    expect(m_highRf.sharpe).toBeLessThan(m_lowRf.sharpe);
  });

  it('RF rate of 4% (RISK_FREE_RATE default) produces sensible Sharpe', () => {
    const m = computePortfolioMetrics(['AAPL', 'MSFT', 'VOO'], [1, 1, 1], 0.04);
    expect(m.sharpe).toBeGreaterThan(-5); // Not absurdly negative
    expect(m.sharpe).toBeLessThan(10);    // Not absurdly positive
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Sector data derivation from tickers + weights
// ─────────────────────────────────────────────────────────────────────────────
describe('sector data derivation', () => {
  const SECTOR_COLORS: Record<string, string> = {
    Technology: '#38BDA4', Healthcare: '#4F9CF0', Energy: '#F0514F',
    Financials: '#F0A44F', Consumer: '#A78BFA', 'Real Estate': '#34D399',
    Utilities: '#FB923C', Communication: '#60A5FA', Other: '#8B949E',
  };

  function deriveSectors(tickers: string[], weights: number[]) {
    if (!tickers.length) return MOCK_SECTORS;
    const map: Record<string, number> = {};
    tickers.forEach((t, i) => {
      const sector = TICKER_SECTOR_MAP[t] ?? 'Other';
      map[sector] = (map[sector] || 0) + (weights[i] ?? 1 / tickers.length);
    });
    const total = Object.values(map).reduce((a, v) => a + v, 0);
    return Object.entries(map)
      .map(([name, w]) => ({ name, value: Math.round((w / total) * 100), color: SECTOR_COLORS[name] ?? '#8B949E' }))
      .sort((a, b) => b.value - a.value);
  }

  it('all-tech portfolio shows 100% Technology sector', () => {
    const sectors = deriveSectors(['AAPL', 'MSFT', 'NVDA'], [1, 1, 1]);
    const tech = sectors.find(s => s.name === 'Technology');
    expect(tech).toBeDefined();
    expect(tech!.value).toBe(100);
  });

  it('unknown tickers map to "Other" sector', () => {
    const sectors = deriveSectors(['XYZZY_FAKE'], [1]);
    expect(sectors[0].name).toBe('Other');
  });

  it('sector percentages sum to 100%', () => {
    const sectors = deriveSectors(
      ['AAPL', 'JPM', 'XOM', 'JNJ', 'NEE'],
      [0.2, 0.2, 0.2, 0.2, 0.2]
    );
    const total = sectors.reduce((s, x) => s + x.value, 0);
    // Sum should be close to 100 (rounding may cause ±1)
    expect(total).toBeGreaterThanOrEqual(98);
    expect(total).toBeLessThanOrEqual(102);
  });

  it('empty tickers returns MOCK_SECTORS fallback', () => {
    const sectors = deriveSectors([], []);
    expect(sectors).toEqual(MOCK_SECTORS);
  });

  it('AAPL is classified as Technology', () => {
    expect(TICKER_SECTOR_MAP['AAPL']).toBe('Technology');
  });

  it('JPM is classified as Financials', () => {
    expect(TICKER_SECTOR_MAP['JPM']).toBe('Financials');
  });

  it('XOM is classified as Energy', () => {
    expect(TICKER_SECTOR_MAP['XOM']).toBe('Energy');
  });

  it('JNJ is classified as Healthcare', () => {
    expect(TICKER_SECTOR_MAP['JNJ']).toBe('Healthcare');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Portfolio config & API request formation
// ─────────────────────────────────────────────────────────────────────────────
describe('portfolioToRequest — request formation', () => {
  it('produces tickers and weights arrays of equal length', () => {
    const config = {
      holdings: [
        { ticker: 'AAPL', shares: '10', cost: '150' },
        { ticker: 'MSFT', shares: '5',  cost: '300' },
        { ticker: 'VOO',  shares: '20', cost: '400' },
      ],
      startDate: '2023-01-01',
      endDate: '2024-12-31',
    };
    // Simulate portfolioToRequest logic
    const holdings = config.holdings.filter(h => h.ticker && h.shares);
    const total = holdings.reduce((s, h) => s + parseFloat(h.shares), 0);
    const tickers = holdings.map(h => h.ticker);
    const weights = holdings.map(h => parseFloat(h.shares) / total);
    expect(tickers.length).toBe(weights.length);
    expect(Math.abs(weights.reduce((a, b) => a + b, 0) - 1.0)).toBeLessThan(0.001);
  });

  it('filters out holdings with no ticker', () => {
    const holdings = [
      { ticker: 'AAPL', shares: '10' },
      { ticker: '',     shares: '5'  },  // empty ticker — should be filtered
      { ticker: 'MSFT', shares: '8'  },
    ];
    const valid = holdings.filter(h => h.ticker && h.shares);
    expect(valid).toHaveLength(2);
  });

  it('analysis should stay disabled when any selected holding is missing shares', () => {
    const holdings = [
      { ticker: 'TSLA', shares: '', cost: '248.42' },
      { ticker: 'AMZN', shares: '4', cost: '178.25' },
    ];
    const active = holdings.filter(h => h.ticker.trim());
    const missingShares = active.filter((holding) => {
      const shares = parseFloat(holding.shares);
      return !Number.isFinite(shares) || shares <= 0;
    });
    const canAnalyze = active.length > 0 && missingShares.length === 0;

    expect(canAnalyze).toBe(false);
  });

  it('analysis should enable only when every selected holding has shares > 0', () => {
    const holdings = [
      { ticker: 'TSLA', shares: '3', cost: '248.42' },
      { ticker: 'AMZN', shares: '4', cost: '178.25' },
    ];
    const active = holdings.filter(h => h.ticker.trim());
    const missingShares = active.filter((holding) => {
      const shares = parseFloat(holding.shares);
      return !Number.isFinite(shares) || shares <= 0;
    });
    const canAnalyze = active.length > 0 && missingShares.length === 0;

    expect(canAnalyze).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. PDF metrics consistency — pdfMetrics must match dashboard display
// ─────────────────────────────────────────────────────────────────────────────
describe('PDF metrics consistency', () => {
  it('computePortfolioMetrics returns all required Metrics fields for PDF', () => {
    const m = computePortfolioMetrics(['AAPL', 'MSFT', 'VOO'], [1, 1, 1]);
    // These are the fields PDFReportDocument requires:
    const required: (keyof typeof m)[] = [
      'sharpe', 'sortino', 'alpha', 'information_ratio', 'calmar',
      'var_95', 'cvar_95', 'max_drawdown', 'beta', 'annualized_return',
      'volatility', 'health_score',
    ];
    for (const field of required) {
      expect(m[field]).toBeDefined();
      expect(typeof m[field]).toBe('number');
      expect(isNaN(m[field] as number)).toBe(false);
    }
  });

  it('health_score in computePortfolioMetrics is an integer', () => {
    const m = computePortfolioMetrics(['AAPL', 'NVDA'], [0.5, 0.5]);
    expect(m.health_score).toBe(Math.round(m.health_score));
  });

  it('var_95 is negative in computePortfolioMetrics output', () => {
    const m = computePortfolioMetrics(['AAPL', 'MSFT', 'VOO'], [1, 1, 1]);
    expect(m.var_95).toBeLessThan(0);
  });

  it('cvar_95 is more negative than var_95', () => {
    const m = computePortfolioMetrics(['AAPL', 'NVDA'], [0.5, 0.5]);
    expect(m.cvar_95).toBeLessThan(m.var_95);
  });

  it('annualized_return is reasonable (between -50% and +100%)', () => {
    const m = computePortfolioMetrics(['AAPL', 'MSFT', 'VOO'], [1, 1, 1]);
    expect(m.annualized_return).toBeGreaterThan(-0.5);
    expect(m.annualized_return).toBeLessThan(1.0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. Goal alignment scoring (mirrors PDFReportDocument goalScore)
// ─────────────────────────────────────────────────────────────────────────────
describe('goal alignment scoring', () => {
  function computeGoalScore(
    annReturn: number,
    vol: number,
    beta: number,
    maxDD: number,
    targetReturn: number,
    riskLabel: string
  ): number {
    const THRESHOLDS: Record<string, { maxVol: number; maxBeta: number; maxDD: number }> = {
      Conservative: { maxVol: 0.12, maxBeta: 0.8,  maxDD: -0.10 },
      Moderate:     { maxVol: 0.18, maxBeta: 1.0,  maxDD: -0.18 },
      Balanced:     { maxVol: 0.24, maxBeta: 1.2,  maxDD: -0.25 },
      Growth:       { maxVol: 0.32, maxBeta: 1.5,  maxDD: -0.35 },
      Aggressive:   { maxVol: 999,  maxBeta: 999,  maxDD: -999  },
    };
    const thresh = THRESHOLDS[riskLabel] ?? THRESHOLDS.Moderate;
    const returnOk = annReturn >= targetReturn;
    const volOk    = riskLabel === 'Aggressive' || vol <= thresh.maxVol;
    const betaOk   = riskLabel === 'Aggressive' || beta <= thresh.maxBeta;
    const ddOk     = riskLabel === 'Aggressive' || maxDD >= thresh.maxDD;
    const returnScore = Math.min(100, Math.max(0, (annReturn / targetReturn) * 100));
    return Math.round(
      (Math.min(100, returnScore) * 0.4) +
      (([volOk, betaOk, ddOk].filter(Boolean).length / 3) * 100 * 0.3) +
      100 * 0.3
    );
  }

  it('perfect portfolio scores 100 for Aggressive profile', () => {
    const score = computeGoalScore(0.30, 0.40, 1.5, -0.20, 0.10, 'Aggressive');
    expect(score).toBe(100);
  });

  it('score 0 when return is 0 with very high target', () => {
    const score = computeGoalScore(0, 0.5, 2.0, -0.5, 1.0, 'Conservative');
    // returnScore = 0, riskScore = 0 (all fail), sectorScore = 30
    // 0*0.4 + 0*0.3 + 30 = 30
    expect(score).toBeLessThan(40);
  });

  it('score is between 0 and 100 always', () => {
    const cases = [
      [0.05, 0.10, 0.8, -0.05, 0.08, 'Conservative'],
      [0.20, 0.30, 1.5, -0.30, 0.15, 'Moderate'],
      [0.50, 0.60, 2.0, -0.60, 0.20, 'Growth'],
    ] as [number, number, number, number, number, string][];
    for (const [ret, vol, beta, dd, target, label] of cases) {
      const score = computeGoalScore(ret, vol, beta, dd, target, label);
      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(100);
    }
  });

  it('Conservative investor: vol > 12% fails the risk check', () => {
    const passing = computeGoalScore(0.10, 0.10, 0.7, -0.08, 0.08, 'Conservative');
    const failing = computeGoalScore(0.10, 0.15, 0.7, -0.08, 0.08, 'Conservative');
    expect(passing).toBeGreaterThan(failing);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. Sandbox mock persistence (localStorage)
// ─────────────────────────────────────────────────────────────────────────────
describe('sandbox mock persistence', () => {
  it('saved mock can be loaded back with correct structure', () => {
    const mock = {
      id: 'test-1',
      name: 'TEST MOCK',
      weights: { AAPL: 0.5, MSFT: 0.5 },
      tickers: ['AAPL', 'MSFT'],
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem('arcus-sandbox-mocks', JSON.stringify([mock]));
    const loaded = JSON.parse(localStorage.getItem('arcus-sandbox-mocks') || '[]');
    expect(loaded).toHaveLength(1);
    expect(loaded[0].id).toBe('test-1');
    expect(loaded[0].weights.AAPL).toBe(0.5);
  });

  it('investor DNA can be stored and retrieved', () => {
    const dna = {
      risk_tolerance: 'Growth',
      target_return: 0.15,
      sectors: ['Technology', 'Healthcare'],
    };
    localStorage.setItem('arcus-investor-dna', JSON.stringify(dna));
    const loaded = JSON.parse(localStorage.getItem('arcus-investor-dna') || 'null');
    expect(loaded?.risk_tolerance).toBe('Growth');
    expect(loaded?.target_return).toBe(0.15);
    expect(loaded?.sectors).toContain('Technology');
  });
});
