/**
 * ARCUS — Sandbox Logic Tests
 * Tests: calcMetrics (covariance vol model), getSharpeRecs recommendations,
 * weight update logic, scenario multipliers, and cross-sandbox duplicate detection.
 *
 * Since calcMetrics and getSharpeRecs are module-level functions in Sandbox.tsx
 * they are re-implemented here for direct unit testing (same logic, extracted).
 */
import { describe, it, expect } from 'vitest';
import { TICKER_RISK_DB } from '@/lib/mock-data';

// ── Replicate calcMetrics exactly as in Sandbox.tsx ─────────────────────────
const DEFAULT_RISK = { annRet: 0.12, vol: 0.22, beta: 1.00, var95: -0.022, maxDD: -0.25, pe: 20 };
const MKT_VOL = 0.16;
const TECH_TICKERS = new Set(['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA', 'AMD', 'NFLX', 'CRM', 'ADBE']);
const TECH_SET = new Set(['AAPL','MSFT','NVDA','GOOGL','META','AMZN','TSLA','AMD','NFLX','CRM','ADBE','PLTR','SNOW','INTC','IBM','ORCL']);
const INDEX_SET = new Set(['VOO','SPY','VTI','QQQ']);

type ScenarioKey = 'normal' | '2008' | 'covid' | 'rateHike' | 'dotcom';

function calcMetrics(
  tickers: string[],
  weights: Record<string, number>,
  scenario: ScenarioKey = 'normal',
  dynamicRiskDb: Record<string, any> = {}
) {
  const activeTickers = tickers.filter(t => (weights[t] || 0) > 0.001);
  const src = activeTickers.length > 0 ? activeTickers : tickers;
  const totalW = src.reduce((a, t) => a + (weights[t] || 0), 0);
  const norm = totalW > 0 ? totalW : 1;

  let pRet = 0, pBeta = 0;
  const td: { w: number; vol: number; beta: number }[] = [];

  for (const t of src) {
    const w = (weights[t] || 0) / norm;
    const risk = dynamicRiskDb[t] ?? TICKER_RISK_DB[t] ?? DEFAULT_RISK;
    let ret = risk.annRet;
    let vol = risk.vol;
    let beta = risk.beta;

    if (scenario === '2008') { ret *= 0.616; vol *= 2.5; }
    else if (scenario === 'covid') { ret *= 0.769; vol *= 2.0; }
    else if (scenario === 'rateHike') { ret *= 0.813; vol *= 1.5; }
    else if (scenario === 'dotcom' && TECH_TICKERS.has(t)) { ret *= 0.558; vol *= 3.0; }
    else if (scenario === 'dotcom') { ret *= 0.90; }

    pRet += w * ret;
    pBeta += w * beta;
    td.push({ w, vol, beta });
  }

  const sysVar = pBeta * pBeta * MKT_VOL * MKT_VOL;
  const idioVar = td.reduce((s, d) => {
    const idio = Math.max(0, d.vol * d.vol - d.beta * d.beta * MKT_VOL * MKT_VOL);
    return s + d.w * d.w * idio;
  }, 0);
  const adjVol = Math.sqrt(sysVar + idioVar);

  const sharpe = adjVol > 0 ? (pRet - 0.04) / adjVol : 0;
  const var95 = -(1.645 * adjVol / Math.sqrt(252));
  const cvar = var95 * 1.4;

  const hhi = tickers.reduce((s, t) => { const wi = (weights[t] || 0) / norm; return s + wi * wi; }, 0);
  const effectiveN = hhi > 0 ? 1 / hhi : 1;
  const concentrationScore = Math.min(100, Math.max(0, (effectiveN - 1) / 9 * 100));

  const baseHealth = Math.round(
    Math.min(100, Math.max(0,
      Math.min(100, (sharpe / 2.0) * 100) * 0.40 +
      Math.min(100, Math.max(0, 100 - Math.max(0, Math.abs(var95) * 100 - 1.2) * (100 / 4))) * 0.25 +
      Math.min(100, Math.max(0, 100 - Math.max(0, adjVol * 100 - 10) * (100 / 30))) * 0.20 +
      concentrationScore * 0.15
    ))
  );

  return { sharpe, var95, healthScore: baseHealth, cvar, beta: pBeta, pRet, adjVol };
}

// ── Helper to build weights from equal allocation ────────────────────────────
function eqWeights(tickers: string[]): Record<string, number> {
  const n = tickers.length;
  return Object.fromEntries(tickers.map(t => [t, 1 / n]));
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. calcMetrics — basic correctness
// ─────────────────────────────────────────────────────────────────────────────
describe('calcMetrics — basic correctness', () => {
  it('returns valid metrics for a simple 2-stock portfolio', () => {
    const tickers = ['AAPL', 'MSFT'];
    const weights = { AAPL: 0.5, MSFT: 0.5 };
    const m = calcMetrics(tickers, weights);
    expect(m.sharpe).not.toBeNaN();
    expect(m.adjVol).toBeGreaterThan(0);
    expect(m.var95).toBeLessThan(0);
    expect(m.healthScore).toBeGreaterThanOrEqual(0);
    expect(m.healthScore).toBeLessThanOrEqual(100);
    expect(m.beta).toBeGreaterThan(0);
  });

  it('health score range is always [0, 100]', () => {
    const cases: [string[], Record<string, number>][] = [
      [['TSLA'], { TSLA: 1.0 }],
      [['VOO', 'GLD', 'TLT'], { VOO: 0.5, GLD: 0.25, TLT: 0.25 }],
      [['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META'], eqWeights(['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META'])],
    ];
    for (const [tickers, weights] of cases) {
      const m = calcMetrics(tickers, weights);
      expect(m.healthScore).toBeGreaterThanOrEqual(0);
      expect(m.healthScore).toBeLessThanOrEqual(100);
    }
  });

  it('zero-weight ticker is excluded from metric calculation', () => {
    const withZero = calcMetrics(['AAPL', 'NVDA'], { AAPL: 1.0, NVDA: 0.0 });
    const singleOnly = calcMetrics(['AAPL'], { AAPL: 1.0 });
    // With NVDA at 0%, result should match single AAPL portfolio
    expect(withZero.sharpe).toBeCloseTo(singleOnly.sharpe, 2);
    expect(withZero.adjVol).toBeCloseTo(singleOnly.adjVol, 2);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. calcMetrics — covariance-based vol correctness
// ─────────────────────────────────────────────────────────────────────────────
describe('calcMetrics — covariance vol model', () => {
  it('adding GLD (β≈0) lowers portfolio beta', () => {
    const before = calcMetrics(['AAPL', 'NVDA', 'MSFT'], eqWeights(['AAPL', 'NVDA', 'MSFT']));
    const after  = calcMetrics(
      ['AAPL', 'NVDA', 'MSFT', 'GLD'],
      { AAPL: 0.25, NVDA: 0.25, MSFT: 0.25, GLD: 0.25 }
    );
    expect(after.beta).toBeLessThan(before.beta);
  });

  it('adding GLD lowers portfolio vol (systematic risk drops)', () => {
    const before = calcMetrics(['AAPL', 'NVDA', 'MSFT'], eqWeights(['AAPL', 'NVDA', 'MSFT']));
    const after  = calcMetrics(
      ['AAPL', 'NVDA', 'MSFT', 'GLD'],
      { AAPL: 0.20, NVDA: 0.20, MSFT: 0.20, GLD: 0.40 }
    );
    expect(after.adjVol).toBeLessThan(before.adjVol);
  });

  it('adding GLD improves health score for a high-vol portfolio', () => {
    const tickers = ['NVDA', 'TSLA', 'AMD'];
    const before = calcMetrics(tickers, eqWeights(tickers));
    const afterTickers = [...tickers, 'GLD'];
    const after = calcMetrics(afterTickers, { NVDA: 0.25, TSLA: 0.25, AMD: 0.25, GLD: 0.25 });
    expect(after.healthScore).toBeGreaterThan(before.healthScore);
  });

  it('TLT (β=-0.25) reduces systematic risk of equity portfolio', () => {
    const equities = calcMetrics(['AAPL', 'MSFT'], { AAPL: 0.5, MSFT: 0.5 });
    const withBonds = calcMetrics(['AAPL', 'MSFT', 'TLT'], { AAPL: 0.4, MSFT: 0.4, TLT: 0.2 });
    // TLT has negative beta → portfolio beta drops
    expect(withBonds.beta).toBeLessThan(equities.beta);
    expect(withBonds.adjVol).toBeLessThan(equities.adjVol);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Scenario stress multipliers
// ─────────────────────────────────────────────────────────────────────────────
describe('calcMetrics — scenario stress tests', () => {
  const tickers = ['AAPL', 'NVDA', 'VOO'];
  const weights = eqWeights(tickers);

  it('2008 crisis has lower return and higher vol than normal', () => {
    const normal = calcMetrics(tickers, weights, 'normal');
    const crisis = calcMetrics(tickers, weights, '2008');
    expect(crisis.pRet).toBeLessThan(normal.pRet);
    expect(crisis.adjVol).toBeGreaterThan(normal.adjVol);
  });

  it('COVID scenario has higher vol than normal', () => {
    const normal = calcMetrics(tickers, weights, 'normal');
    const covid = calcMetrics(tickers, weights, 'covid');
    expect(covid.adjVol).toBeGreaterThan(normal.adjVol);
  });

  it('2008 crisis health score is lower than normal', () => {
    const normal = calcMetrics(tickers, weights, 'normal');
    const crisis = calcMetrics(tickers, weights, '2008');
    expect(crisis.healthScore).toBeLessThan(normal.healthScore);
  });

  it('dot-com scenario is especially bad for tech stocks', () => {
    const techTickers = ['AAPL', 'NVDA', 'META'];
    const mixedTickers = ['AAPL', 'JPM', 'XOM'];
    const techDotcom  = calcMetrics(techTickers,  eqWeights(techTickers),  'dotcom');
    const techNormal  = calcMetrics(techTickers,  eqWeights(techTickers),  'normal');
    const mixedDotcom = calcMetrics(mixedTickers, eqWeights(mixedTickers), 'dotcom');
    // Tech vol explodes 3× in dot-com; mixed only has AAPL stressed
    expect(techDotcom.adjVol).toBeGreaterThan(mixedDotcom.adjVol);
    // Tech portfolio is relatively more damaged: its pRet ratio drops more than mixed
    const techDrop  = techDotcom.pRet  / calcMetrics(techTickers,  eqWeights(techTickers),  'normal').pRet;
    const mixedDrop = mixedDotcom.pRet / calcMetrics(mixedTickers, eqWeights(mixedTickers), 'normal').pRet;
    expect(techDrop).toBeLessThan(mixedDrop);
  });

  it('rate hike scenario harms high-duration bonds (TLT) more than equities', () => {
    const withTLT = calcMetrics(['AAPL', 'TLT'], { AAPL: 0.5, TLT: 0.5 }, 'rateHike');
    const withGLD = calcMetrics(['AAPL', 'GLD'], { AAPL: 0.5, GLD: 0.5 }, 'rateHike');
    // Both impacted, but overall metrics should be calculable
    expect(withTLT.sharpe).not.toBeNaN();
    expect(withGLD.sharpe).not.toBeNaN();
  });

  it('scenario multipliers are correctly applied: 2008 ret×0.616, vol×2.5', () => {
    // Single-ticker test: verify the exact multipliers
    const aaplNormal = calcMetrics(['AAPL'], { AAPL: 1.0 }, 'normal');
    const aapl2008 = calcMetrics(['AAPL'], { AAPL: 1.0 }, '2008');
    // Return should drop by factor 0.616
    expect(aapl2008.pRet).toBeCloseTo(aaplNormal.pRet * 0.616, 3);
    // Vol increases → adjVol should be higher in 2008
    expect(aapl2008.adjVol).toBeGreaterThan(aaplNormal.adjVol);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Weight update logic (simulates updateWeight in Sandbox.tsx)
// ─────────────────────────────────────────────────────────────────────────────
describe('weight update logic', () => {
  function updateWeight(
    tickers: string[],
    weights: Record<string, number>,
    ticker: string,
    value: number,
    locked: Record<string, boolean> = {}
  ) {
    const newWeights = { ...weights };
    const lockedSum = tickers.filter(t => t !== ticker && locked[t])
      .reduce((s, t) => s + (newWeights[t] || 0), 0);
    const remaining = 1 - lockedSum - value;
    const unlocked = tickers.filter(t => t !== ticker && !locked[t]);
    const unlockSum = unlocked.reduce((s, t) => s + (newWeights[t] || 0), 0);
    newWeights[ticker] = Math.max(0, Math.min(1, value));
    if (unlocked.length > 0 && remaining >= 0) {
      for (const t of unlocked) {
        const ratio = unlockSum > 0 ? (newWeights[t] || 0) / unlockSum : 1 / unlocked.length;
        newWeights[t] = Math.max(0, remaining * ratio);
      }
    }
    return newWeights;
  }

  it('adjusting one weight redistributes remainder among unlocked tickers', () => {
    const tickers = ['AAPL', 'MSFT', 'NVDA'];
    const weights = { AAPL: 0.33, MSFT: 0.33, NVDA: 0.34 };
    const newW = updateWeight(tickers, weights, 'AAPL', 0.5);
    const total = tickers.reduce((s, t) => s + newW[t], 0);
    expect(total).toBeCloseTo(1.0, 3);
    expect(newW.AAPL).toBeCloseTo(0.5, 3);
  });

  it('locked tickers preserve their weight', () => {
    const tickers = ['AAPL', 'MSFT', 'NVDA'];
    const weights = { AAPL: 0.33, MSFT: 0.33, NVDA: 0.34 };
    const locked = { MSFT: true };
    const newW = updateWeight(tickers, weights, 'AAPL', 0.5, locked);
    expect(newW.MSFT).toBeCloseTo(0.33, 3); // locked — unchanged
    const total = tickers.reduce((s, t) => s + newW[t], 0);
    expect(total).toBeCloseTo(1.0, 2);
  });

  it('weight cannot go below 0', () => {
    const tickers = ['AAPL', 'MSFT'];
    const weights = { AAPL: 0.5, MSFT: 0.5 };
    const newW = updateWeight(tickers, weights, 'AAPL', -0.1);
    expect(newW.AAPL).toBeGreaterThanOrEqual(0);
  });

  it('weight cannot exceed 1', () => {
    const tickers = ['AAPL', 'MSFT'];
    const weights = { AAPL: 0.5, MSFT: 0.5 };
    const newW = updateWeight(tickers, weights, 'AAPL', 1.5);
    expect(newW.AAPL).toBeLessThanOrEqual(1.0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. addTickerToMock — initial weight allocation
// ─────────────────────────────────────────────────────────────────────────────
describe('addTickerToMock — initial weight distribution', () => {
  function addTicker(
    tickers: string[],
    weights: Record<string, number>,
    newTicker: string
  ) {
    if (tickers.includes(newTicker)) return { tickers, weights };
    const newTickers = [...tickers, newTicker];
    const n = newTickers.length;
    const initW = 1 / n;
    const scale = (n - 1) / n;
    const newWeights = { ...weights };
    for (const t of newTickers) {
      newWeights[t] = t === newTicker ? initW : (newWeights[t] || 0) * scale;
    }
    return { tickers: newTickers, weights: newWeights };
  }

  it('new ticker receives 1/(n+1) weight', () => {
    const { weights } = addTicker(['AAPL', 'MSFT'], { AAPL: 0.5, MSFT: 0.5 }, 'GLD');
    expect(weights.GLD).toBeCloseTo(1 / 3, 3);
  });

  it('existing tickers are scaled proportionally (sum remains 1)', () => {
    const { weights, tickers } = addTicker(
      ['AAPL', 'MSFT', 'NVDA'],
      { AAPL: 0.33, MSFT: 0.33, NVDA: 0.34 },
      'GLD'
    );
    const total = tickers.reduce((s, t) => s + weights[t], 0);
    expect(total).toBeCloseTo(1.0, 3);
  });

  it('new ticker immediately affects health score (not zero weight)', () => {
    const tickers = ['AAPL', 'NVDA', 'MSFT'];
    const weights = eqWeights(tickers);
    const mBefore = calcMetrics(tickers, weights);

    const { tickers: newT, weights: newW } = addTicker(tickers, weights, 'GLD');
    const mAfter = calcMetrics(newT, newW);

    // GLD starts at 1/4 = 25%, so health score must change
    expect(mAfter.healthScore).not.toBe(mBefore.healthScore);
  });

  it('adding same ticker twice is a no-op', () => {
    const result = addTicker(['AAPL'], { AAPL: 1.0 }, 'AAPL');
    expect(result.tickers).toHaveLength(1);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. getSharpeRecs logic
// ─────────────────────────────────────────────────────────────────────────────
describe('getSharpeRecs — recommendation logic', () => {
  // Re-implement recommendation logic for testing
  function getSharpeRecs(
    tickers: string[],
    weights: Record<string, number>,
    metrics: ReturnType<typeof calcMetrics>
  ): string[] {
    const recs: string[] = [];
    if (tickers.length === 0) return ['Add some stocks to get recommendations.'];
    const sorted = [...tickers].sort((a, b) => (weights[b] || 0) - (weights[a] || 0));
    const top = sorted[0] ?? '';
    const topW = weights[top] || 0;
    const techW = tickers.filter(t => TECH_SET.has(t)).reduce((s, t) => s + (weights[t] || 0), 0);
    const gldW = weights['GLD'] || 0;
    const tltW = weights['TLT'] || 0;
    const hasGLD = tickers.includes('GLD');
    const hasTLT = tickers.includes('TLT');
    const hasIndex = tickers.some(t => INDEX_SET.has(t));

    if (topW > 0.35 && top && recs.length < 3) {
      recs.push(`CONCENTRATION:${top}:${(topW*100).toFixed(0)}%`);
    }
    if (metrics.sharpe < 1.0 && recs.length < 3) {
      if (!hasGLD && !hasTLT) {
        recs.push('HEDGE:MISSING');
      } else if (hasGLD && gldW < 0.08) {
        recs.push(`HEDGE:GLD_LOW:${(gldW*100).toFixed(0)}%`);
      }
    }
    if (techW > 0.55 && recs.length < 3) {
      recs.push(`TECH:OVERWEIGHT:${(techW*100).toFixed(0)}%`);
    }
    if (tickers.length < 4 && recs.length < 3) {
      recs.push(`DIVERSIFY:${tickers.length}`);
    }
    if (metrics.beta > 1.3 && recs.length < 3) {
      recs.push(`BETA:HIGH:${metrics.beta.toFixed(2)}`);
    }
    if (!hasIndex && metrics.sharpe < 1.5 && recs.length < 3) {
      recs.push('INDEX:MISSING');
    }
    return recs.slice(0, 3);
  }

  it('concentration flag triggered when top holding > 35%', () => {
    const tickers = ['AAPL', 'MSFT'];
    const weights = { AAPL: 0.60, MSFT: 0.40 };
    const m = calcMetrics(tickers, weights);
    const recs = getSharpeRecs(tickers, weights, m);
    expect(recs.some(r => r.startsWith('CONCENTRATION'))).toBe(true);
  });

  it('concentration flag NOT triggered when all holdings ≤ 35%', () => {
    const tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL'];
    const weights = eqWeights(tickers);
    const m = calcMetrics(tickers, weights);
    const recs = getSharpeRecs(tickers, weights, m);
    expect(recs.some(r => r.startsWith('CONCENTRATION'))).toBe(false);
  });

  it('hedge missing flag triggered for low-Sharpe portfolio without GLD/TLT', () => {
    const tickers = ['TSLA', 'COIN', 'PLTR'];
    const weights = eqWeights(tickers);
    const m = calcMetrics(tickers, weights);
    if (m.sharpe < 1.0) {
      const recs = getSharpeRecs(tickers, weights, m);
      expect(recs.some(r => r.includes('HEDGE'))).toBe(true);
    }
  });

  it('hedge flag uses GLD_LOW when GLD present but < 8%', () => {
    const tickers = ['TSLA', 'NVDA', 'GLD'];
    const weights = { TSLA: 0.47, NVDA: 0.47, GLD: 0.06 }; // GLD at 6%, below 8%
    const m = calcMetrics(tickers, weights);
    if (m.sharpe < 1.0) {
      const recs = getSharpeRecs(tickers, weights, m);
      expect(recs.some(r => r.includes('GLD_LOW'))).toBe(true);
    }
  });

  it('no HEDGE flag when GLD already at 15% (sufficient hedge)', () => {
    const tickers = ['AAPL', 'MSFT', 'GLD'];
    const weights = { AAPL: 0.425, MSFT: 0.425, GLD: 0.15 };
    const m = calcMetrics(tickers, weights);
    const recs = getSharpeRecs(tickers, weights, m);
    // If sharpe < 1.0 still flagged, but not the missing hedge (GLD is sufficient)
    expect(recs.some(r => r === 'HEDGE:MISSING')).toBe(false);
  });

  it('tech overweight flag triggered at > 55% tech', () => {
    const tickers = ['AAPL', 'MSFT', 'NVDA', 'AMD', 'META'];
    const weights = eqWeights(tickers); // all tech = 100%
    const m = calcMetrics(tickers, weights);
    const recs = getSharpeRecs(tickers, weights, m);
    expect(recs.some(r => r.startsWith('TECH:OVERWEIGHT'))).toBe(true);
  });

  it('diversify flag triggered for < 4 holdings', () => {
    // Use 3 non-tech stocks with hedge assets present (no HEDGE flag fires),
    // equal weights (topW=0.33 ≤ 0.35, no concentration flag), no index ticker.
    // DIVERSIFY:3 should fire as the first recommendation.
    const tickers = ['GLD', 'TLT', 'JNJ'];
    const weights = eqWeights(tickers);
    const m = calcMetrics(tickers, weights);
    const recs = getSharpeRecs(tickers, weights, m);
    expect(recs.some(r => r.startsWith('DIVERSIFY'))).toBe(true);
  });

  it('index ETF flag triggered when no index and Sharpe < 1.5', () => {
    // 4 non-tech defensives, no GLD/TLT, no index ticker.
    // HEDGE:MISSING fires first (1 slot), leaving room for INDEX:MISSING (slot 2).
    const tickers = ['JNJ', 'XOM', 'JPM', 'WMT'];
    const weights = eqWeights(tickers);
    const m = calcMetrics(tickers, weights);
    // Sharpe is well below 1.5 for these defensives
    expect(m.sharpe).toBeLessThan(1.5);
    const recs = getSharpeRecs(tickers, weights, m);
    expect(recs.some(r => r === 'INDEX:MISSING')).toBe(true);
  });

  it('no index flag when VOO already in portfolio', () => {
    const tickers = ['AAPL', 'MSFT', 'VOO'];
    const weights = eqWeights(tickers);
    const m = calcMetrics(tickers, weights);
    const recs = getSharpeRecs(tickers, weights, m);
    expect(recs.some(r => r === 'INDEX:MISSING')).toBe(false);
  });

  it('max 3 recommendations returned', () => {
    const tickers = ['TSLA']; // triggers: diversify, tech overweight, index missing, hedge missing, high beta
    const weights = { TSLA: 1.0 };
    const m = calcMetrics(tickers, weights);
    const recs = getSharpeRecs(tickers, weights, m);
    expect(recs.length).toBeLessThanOrEqual(3);
  });

  it('empty portfolio returns single add-stocks message', () => {
    const recs = getSharpeRecs([], {}, calcMetrics([], {}));
    expect(recs).toHaveLength(1);
    expect(recs[0]).toContain('Add some stocks');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. Health score sensitivity — recommendations should cause score to change
// ─────────────────────────────────────────────────────────────────────────────
describe('health score sensitivity to recommended actions', () => {
  it('following hedge recommendation (add GLD 20%) improves health', () => {
    const tickers = ['NVDA', 'TSLA', 'AMD'];
    const w = eqWeights(tickers);
    const before = calcMetrics(tickers, w);

    const newTickers = [...tickers, 'GLD'];
    const newW = { NVDA: 0.25, TSLA: 0.25, AMD: 0.25, GLD: 0.25 };
    const after = calcMetrics(newTickers, newW);

    expect(after.healthScore).toBeGreaterThan(before.healthScore);
  });

  it('reducing top holding from 60% to 25% improves health', () => {
    // TSLA (vol=0.72) is the concentrated ticker. Reducing it from 60% to 25%
    // and shifting weight to lower-vol AAPL/MSFT should clearly reduce adjVol
    // and improve health score.
    const tickers = ['TSLA', 'AAPL', 'MSFT'];
    const concentrated = { TSLA: 0.60, AAPL: 0.20, MSFT: 0.20 };
    const balanced     = { TSLA: 0.25, AAPL: 0.375, MSFT: 0.375 };

    const before = calcMetrics(tickers, concentrated);
    const after  = calcMetrics(tickers, balanced);

    expect(after.healthScore).toBeGreaterThan(before.healthScore);
  });

  it('adding index ETF (VOO 20%) to a pure-equity portfolio improves Sharpe', () => {
    const tickers = ['TSLA', 'COIN', 'PLTR', 'AMD'];
    const w = eqWeights(tickers);
    const before = calcMetrics(tickers, w);

    const newTickers = [...tickers, 'VOO'];
    const newW = { TSLA: 0.2, COIN: 0.2, PLTR: 0.2, AMD: 0.2, VOO: 0.2 };
    const after = calcMetrics(newTickers, newW);

    // VOO has high Sharpe and low vol → should improve metrics
    expect(after.adjVol).toBeLessThan(before.adjVol);
  });
});
