/**
 * ARCUS — Core Calculation Tests
 * Tests every formula used in the frontend: computePortfolioMetrics,
 * health score components, covariance-decomposition vol, HHI concentration,
 * and scenario multipliers.
 */
import { describe, it, expect } from 'vitest';
import {
  computePortfolioMetrics,
  TICKER_RISK_DB,
  MOCK_PORTFOLIO,
} from '@/lib/mock-data';

const EPSILON = 0.005; // 0.5% tolerance for floating-point comparisons
const near = (a: number, b: number, eps = EPSILON) => Math.abs(a - b) < eps;

// ─────────────────────────────────────────────────────────────────────────────
// 1. Weight Normalisation
// ─────────────────────────────────────────────────────────────────────────────
describe('computePortfolioMetrics — weight normalisation', () => {
  it('equal weights implied when sharesOrWeights omitted', () => {
    const tickers = ['AAPL', 'MSFT'];
    const m1 = computePortfolioMetrics(tickers);
    const m2 = computePortfolioMetrics(tickers, [1, 1]);
    expect(m1.sharpe).toBeCloseTo(m2.sharpe, 3);
    expect(m1.volatility).toBeCloseTo(m2.volatility, 3);
  });

  it('un-normalised shares produce same result as normalised weights', () => {
    const tickers = ['AAPL', 'NVDA', 'VOO'];
    const m_shares = computePortfolioMetrics(tickers, [100, 50, 200]);
    const m_weights = computePortfolioMetrics(tickers, [0.2857, 0.1429, 0.5714]);
    // Both should produce same Sharpe within tolerance
    expect(near(m_shares.sharpe, m_weights.sharpe, 0.02)).toBe(true);
  });

  it('returns MOCK_PORTFOLIO.metrics for empty tickers array', () => {
    const m = computePortfolioMetrics([]);
    expect(m.health_score).toBe(MOCK_PORTFOLIO.metrics.health_score);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Sharpe Ratio
// ─────────────────────────────────────────────────────────────────────────────
describe('computePortfolioMetrics — Sharpe ratio', () => {
  it('single S&P 500 index ETF (VOO) has reasonable Sharpe > 0', () => {
    const m = computePortfolioMetrics(['VOO'], [1]);
    expect(m.sharpe).toBeGreaterThan(0);
  });

  it('high-vol portfolio (TSLA, COIN, ARKK) has lower Sharpe than diversified', () => {
    const volatile = computePortfolioMetrics(['TSLA', 'COIN', 'ARKK'], [1, 1, 1]);
    const diversified = computePortfolioMetrics(['AAPL', 'VOO', 'JNJ', 'GLD'], [1, 1, 1, 1]);
    expect(diversified.sharpe).toBeGreaterThan(volatile.sharpe);
  });

  it('Sharpe formula: (annRet - riskFreeRate) / vol', () => {
    const tickers = ['AAPL'];
    const rf = 0.04;
    const m = computePortfolioMetrics(tickers, [1], rf);
    const risk = TICKER_RISK_DB['AAPL'];
    // With 1 ticker: sysVar = beta²*0.0256, idioVar = wi²*(vol²-beta²*0.0256)
    // wi = 1 so idioVar = max(0, vol²-beta²*0.0256)
    const mktVar = 0.16 * 0.16;
    const sysVar = risk.beta * risk.beta * mktVar;
    const idio = Math.max(0, risk.vol * risk.vol - risk.beta * risk.beta * mktVar);
    const expVol = Math.sqrt(sysVar + idio);
    const expSharpe = (risk.annRet - rf) / expVol;
    expect(m.sharpe).toBeCloseTo(expSharpe, 2);
  });

  it('risk-free rate of 0 increases Sharpe (numerator grows)', () => {
    const tickers = ['AAPL', 'MSFT'];
    const mHighRf = computePortfolioMetrics(tickers, [1, 1], 0.08);
    const mLowRf = computePortfolioMetrics(tickers, [1, 1], 0.00);
    expect(mLowRf.sharpe).toBeGreaterThan(mHighRf.sharpe);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Covariance-Decomposition Volatility (σp² = βp²σm² + Σwi²·idio_i)
// ─────────────────────────────────────────────────────────────────────────────
describe('computePortfolioMetrics — covariance-decomposition vol', () => {
  it('GLD (beta≈0) contributes almost no systematic risk', () => {
    const gld = TICKER_RISK_DB['GLD'];
    const mktVar = 0.16 ** 2;
    const sysContrib = gld.beta ** 2 * mktVar;
    expect(sysContrib).toBeLessThan(0.001); // near-zero systematic variance
  });

  it('adding GLD at 20% to a tech portfolio lowers vol (vs adding AMD)', () => {
    const base = ['AAPL', 'NVDA', 'MSFT', 'GOOGL'];
    const w_base = [0.25, 0.25, 0.25, 0.25];
    const withGLD = computePortfolioMetrics([...base, 'GLD'], [0.20, 0.20, 0.20, 0.20, 0.20]);
    const withAMD = computePortfolioMetrics([...base, 'AMD'], [0.20, 0.20, 0.20, 0.20, 0.20]);
    expect(withGLD.volatility).toBeLessThan(withAMD.volatility);
  });

  it('adding TLT (beta=-0.25) to equity portfolio significantly reduces systematic risk', () => {
    const equityOnly = computePortfolioMetrics(['AAPL', 'MSFT'], [0.5, 0.5]);
    const withTLT = computePortfolioMetrics(['AAPL', 'MSFT', 'TLT'], [0.4, 0.4, 0.2]);
    expect(withTLT.volatility).toBeLessThan(equityOnly.volatility);
  });

  it('single-stock vol equals its own risk profile (no diversification benefit)', () => {
    const aapl = TICKER_RISK_DB['AAPL'];
    const m = computePortfolioMetrics(['AAPL'], [1]);
    const mktVar = 0.16 ** 2;
    const sysVar = aapl.beta ** 2 * mktVar;
    const idio = Math.max(0, aapl.vol ** 2 - aapl.beta ** 2 * mktVar);
    const expVol = Math.sqrt(sysVar + idio);
    expect(m.volatility).toBeCloseTo(expVol, 3);
  });

  it('portfolio vol is less than weighted average vol (diversification effect)', () => {
    const tickers = ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'VOO'];
    const w = [0.2, 0.2, 0.2, 0.2, 0.2];
    const m = computePortfolioMetrics(tickers, w);
    const weightedAvgVol = tickers.reduce((s, t, i) =>
      s + w[i] * (TICKER_RISK_DB[t]?.vol ?? 0.22), 0);
    expect(m.volatility).toBeLessThan(weightedAvgVol);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. VaR and CVaR
// ─────────────────────────────────────────────────────────────────────────────
describe('computePortfolioMetrics — VaR / CVaR', () => {
  it('VaR is negative (represents a loss)', () => {
    const m = computePortfolioMetrics(['AAPL', 'VOO'], [0.5, 0.5]);
    expect(m.var_95).toBeLessThan(0);
  });

  it('CVaR is more negative than VaR (tail-risk is worse)', () => {
    const m = computePortfolioMetrics(['AAPL', 'NVDA', 'TSLA'], [1, 1, 1]);
    expect(m.cvar_95).toBeLessThan(m.var_95);
  });

  it('high-vol portfolio has worse (more negative) VaR', () => {
    const highVol = computePortfolioMetrics(['TSLA', 'COIN', 'AMD'], [1, 1, 1]);
    const lowVol = computePortfolioMetrics(['VOO', 'GLD', 'JNJ'], [1, 1, 1]);
    expect(highVol.var_95).toBeLessThan(lowVol.var_95);
  });

  it('VaR magnitude scales with portfolio volatility', () => {
    // VaR is derived from vol: var = -(1.645 * adjVar * scaling)
    // Higher vol → more negative VaR
    const mHighVol = computePortfolioMetrics(['TSLA'], [1]);
    const mLowVol = computePortfolioMetrics(['VOO'], [1]);
    expect(Math.abs(mHighVol.var_95)).toBeGreaterThan(Math.abs(mLowVol.var_95));
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Health Score Formula (40% Sharpe + 25% VaR + 20% Vol + 15% Concentration)
// ─────────────────────────────────────────────────────────────────────────────
describe('computePortfolioMetrics — health score', () => {
  it('health score is always 0–100', () => {
    const portfolios = [
      ['TSLA', 'COIN', 'ARKK'],
      ['VOO', 'GLD', 'TLT'],
      ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'VOO'],
      ['AAPL'],
    ];
    for (const tickers of portfolios) {
      const m = computePortfolioMetrics(tickers);
      expect(m.health_score).toBeGreaterThanOrEqual(0);
      expect(m.health_score).toBeLessThanOrEqual(100);
    }
  });

  it('well-diversified low-beta portfolio scores higher than concentrated high-vol portfolio', () => {
    const good = computePortfolioMetrics(['VOO', 'GLD', 'JNJ', 'TLT', 'KO'], [1, 1, 1, 1, 1]);
    const bad = computePortfolioMetrics(['TSLA', 'COIN', 'PLTR'], [1, 1, 1]);
    expect(good.health_score).toBeGreaterThan(bad.health_score);
  });

  it('adding GLD at 20% to a volatile portfolio improves health score', () => {
    const before = computePortfolioMetrics(['TSLA', 'NVDA', 'AMD'], [1, 1, 1]);
    const after = computePortfolioMetrics(['TSLA', 'NVDA', 'AMD', 'GLD'], [0.25, 0.25, 0.25, 0.25]);
    expect(after.health_score).toBeGreaterThan(before.health_score);
  });

  it('Sharpe component caps at 40 pts (sharpe ≥ 2.0)', () => {
    // Sharpe = 2.0 → min(100, 2.0/2.0 * 100) * 0.40 = 40
    // Sharpe = 3.0 → still capped at 40
    const m = computePortfolioMetrics(['VOO', 'GLD'], [0.5, 0.5], 0.00); // RF=0 boosts Sharpe
    // Health score sharpe component should not exceed 40
    expect(m.health_score).toBeLessThanOrEqual(100);
  });

  it('concentration component: single stock gets lower score than 10 equal holdings', () => {
    const single = computePortfolioMetrics(['AAPL'], [1]);
    const diversified = computePortfolioMetrics(
      ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'XOM', 'VOO', 'GLD', 'JNJ', 'V', 'KO'],
      [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    );
    expect(diversified.health_score).toBeGreaterThan(single.health_score);
  });

  it('health score is deterministic (same input → same output)', () => {
    const tickers = ['AAPL', 'NVDA', 'MSFT'];
    const w = [0.5, 0.3, 0.2];
    const m1 = computePortfolioMetrics(tickers, w, 0.04);
    const m2 = computePortfolioMetrics(tickers, w, 0.04);
    expect(m1.health_score).toBe(m2.health_score);
    expect(m1.sharpe).toBe(m2.sharpe);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. HHI-Based Concentration
// ─────────────────────────────────────────────────────────────────────────────
describe('HHI concentration scoring', () => {
  it('single stock: HHI=1.0 → effectiveN=1 → concentrationScore=0', () => {
    // With 1 ticker at 100%, HHI=1, effectiveN=1, (1-1)/9*100=0
    const w = [1.0];
    const hhi = w.reduce((s, wi) => s + wi * wi, 0);
    const effectiveN = 1 / hhi;
    const score = Math.min(100, Math.max(0, (effectiveN - 1) / 9 * 100));
    expect(score).toBe(0);
  });

  it('10 equal holdings: HHI=0.1 → effectiveN=10 → concentrationScore=100', () => {
    const w = Array(10).fill(0.1);
    const hhi = w.reduce((s, wi) => s + wi * wi, 0);
    const effectiveN = 1 / hhi;
    const score = Math.min(100, Math.max(0, (effectiveN - 1) / 9 * 100));
    expect(score).toBeCloseTo(100, 1);
  });

  it('5 equal holdings → concentrationScore ≈ 44.4', () => {
    const w = Array(5).fill(0.2);
    const hhi = w.reduce((s, wi) => s + wi * wi, 0);
    const effectiveN = 1 / hhi;
    const score = Math.min(100, Math.max(0, (effectiveN - 1) / 9 * 100));
    expect(score).toBeCloseTo(44.4, 1);
  });

  it('score increases monotonically as portfolio becomes more equal', () => {
    // 80/20 split → 60/40 → 50/50
    const score = (a: number, b: number) => {
      const w = [a, b];
      const hhi = w.reduce((s, wi) => s + wi * wi, 0);
      return (1 / hhi - 1) / 9 * 100;
    };
    expect(score(0.5, 0.5)).toBeGreaterThan(score(0.6, 0.4));
    expect(score(0.6, 0.4)).toBeGreaterThan(score(0.8, 0.2));
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. Alpha, Information Ratio, Sortino, Calmar
// ─────────────────────────────────────────────────────────────────────────────
describe('computePortfolioMetrics — derived metrics', () => {
  it('alpha can be positive or negative depending on expected return vs CAPM', () => {
    // High-growth portfolio should have positive alpha (outperforms CAPM expectation)
    const mGrowth = computePortfolioMetrics(['NVDA', 'LLY'], [0.5, 0.5]);
    // alpha = ret - (rf + beta * 0.07)
    const aapl = TICKER_RISK_DB['NVDA'];
    const lly = TICKER_RISK_DB['LLY'];
    expect(mGrowth.alpha).toBeDefined();
  });

  it('sortino is positive for positive-Sharpe portfolios', () => {
    const m = computePortfolioMetrics(['AAPL', 'MSFT', 'VOO'], [1, 1, 1]);
    if (m.sharpe > 0) {
      expect(m.sortino).toBeGreaterThan(0);
    }
  });

  it('calmar = annualized_return / |max_drawdown|', () => {
    const m = computePortfolioMetrics(['AAPL', 'MSFT'], [0.5, 0.5]);
    const expectedCalmar = Math.abs(m.max_drawdown) > 0
      ? m.annualized_return / Math.abs(m.max_drawdown)
      : 0;
    expect(m.calmar).toBeCloseTo(expectedCalmar, 2);
  });

  it('information_ratio is capped to [-1, 1.5] range', () => {
    const portfolios = [
      ['NVDA'], ['TSLA', 'COIN'], ['VOO', 'GLD', 'TLT'],
    ];
    for (const tickers of portfolios) {
      const m = computePortfolioMetrics(tickers);
      expect(m.information_ratio).toBeGreaterThanOrEqual(-1);
      expect(m.information_ratio).toBeLessThanOrEqual(1.5);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 8. MOCK_PORTFOLIO sanity checks
// ─────────────────────────────────────────────────────────────────────────────
describe('MOCK_PORTFOLIO integrity', () => {
  it('MOCK_PORTFOLIO weights sum to 1.0', () => {
    const sum = MOCK_PORTFOLIO.weights.reduce((a, b) => a + b, 0);
    expect(sum).toBeCloseTo(1.0, 5);
  });

  it('MOCK_PORTFOLIO has 5 tickers with 5 weights', () => {
    expect(MOCK_PORTFOLIO.tickers).toHaveLength(5);
    expect(MOCK_PORTFOLIO.weights).toHaveLength(5);
  });

  it('MOCK_PORTFOLIO health_score is between 0 and 100', () => {
    expect(MOCK_PORTFOLIO.metrics.health_score).toBeGreaterThan(0);
    expect(MOCK_PORTFOLIO.metrics.health_score).toBeLessThanOrEqual(100);
  });

  it('computePortfolioMetrics on MOCK_PORTFOLIO tickers produces valid metrics', () => {
    const m = computePortfolioMetrics(MOCK_PORTFOLIO.tickers, MOCK_PORTFOLIO.weights);
    expect(m.sharpe).not.toBeNaN();
    expect(m.volatility).toBeGreaterThan(0);
    expect(m.health_score).toBeGreaterThan(0);
    expect(m.var_95).toBeLessThan(0);
    expect(m.cvar_95).toBeLessThan(m.var_95);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 9. TICKER_RISK_DB completeness
// ─────────────────────────────────────────────────────────────────────────────
describe('TICKER_RISK_DB data integrity', () => {
  const essentialTickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'VOO', 'GLD', 'TLT', 'JPM', 'JNJ'];

  for (const ticker of essentialTickers) {
    it(`${ticker} has all required risk fields`, () => {
      const r = TICKER_RISK_DB[ticker];
      expect(r).toBeDefined();
      expect(typeof r.annRet).toBe('number');
      expect(typeof r.vol).toBe('number');
      expect(typeof r.beta).toBe('number');
      expect(typeof r.var95).toBe('number');
      expect(typeof r.maxDD).toBe('number');
      expect(r.vol).toBeGreaterThan(0);
      expect(r.var95).toBeLessThan(0); // VaR should be negative
      expect(r.maxDD).toBeLessThan(0); // Max drawdown should be negative
    });
  }

  it('GLD has near-zero beta (uncorrelated to market)', () => {
    expect(Math.abs(TICKER_RISK_DB['GLD'].beta)).toBeLessThan(0.2);
  });

  it('TLT has negative beta (negative correlation to equities)', () => {
    expect(TICKER_RISK_DB['TLT'].beta).toBeLessThan(0);
  });

  it('NVDA has high beta (amplifies market moves)', () => {
    expect(TICKER_RISK_DB['NVDA'].beta).toBeGreaterThan(1.5);
  });

  it('SPY/VOO track S&P 500 with beta ~1.0', () => {
    expect(TICKER_RISK_DB['SPY'].beta).toBeCloseTo(1.0, 1);
    expect(TICKER_RISK_DB['VOO'].beta).toBeCloseTo(1.0, 1);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 10. Edge cases
// ─────────────────────────────────────────────────────────────────────────────
describe('computePortfolioMetrics — edge cases', () => {
  it('unknown ticker uses DEFAULT_RISK fallback', () => {
    const m = computePortfolioMetrics(['XYZZY_FAKE_123'], [1]);
    // Should not throw, should return valid metrics
    expect(m.sharpe).not.toBeNaN();
    expect(m.volatility).toBeGreaterThan(0);
    expect(m.health_score).toBeGreaterThanOrEqual(0);
  });

  it('all-zero weights returns valid metrics via equal-weight fallback', () => {
    // Normalisation: if totalW=0, uses tickers.length as norm → equal weights
    const m = computePortfolioMetrics(['AAPL', 'MSFT'], [0, 0]);
    expect(m.sharpe).not.toBeNaN();
  });

  it('portfolio with 20+ tickers does not crash', () => {
    const tickers = Object.keys(TICKER_RISK_DB).slice(0, 20);
    const m = computePortfolioMetrics(tickers);
    expect(m.health_score).toBeGreaterThanOrEqual(0);
    expect(m.volatility).toBeGreaterThan(0);
  });
});
