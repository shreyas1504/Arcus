import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Lock, Unlock, Plus, X, BookmarkPlus, Pencil, Check, Minus, Share2, ChevronRight, Lightbulb } from 'lucide-react';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import { useNavigate } from 'react-router-dom';
import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import AnimatedNumber from '@/components/AnimatedNumber';
import StockSearch from '@/components/StockSearch';
import Disclaimer from '@/components/legal/Disclaimer';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { MOCK_PORTFOLIO, TICKER_RISK_DB } from '@/lib/mock-data';
import { optimizePortfolio } from '@/lib/api';
import { useIsMobile } from '@/hooks/use-mobile';
import { toast } from 'sonner';
import { analyzePortfolio } from '@/lib/api';

// ── Tooltip text map ─────────────────────────────────────────────────────
const METRIC_TOOLTIPS: Record<string, string> = {
  'Health Score': 'A 0–100 composite score. >70 is healthy. Combines Sharpe, diversification, volatility, and drawdown.',
  'Sharpe': 'Return per unit of risk. (Return - Risk-Free Rate) / Std Dev. >1.0 good, >2.0 excellent.',
  'VaR 95%': 'Worst expected daily loss on 95% of trading days. -2.8% = you lose at most 2.8% on bad days.',
  'CVaR': 'Average loss on the worst 5% of days. More conservative than VaR.',
  'Beta': 'Sensitivity to market moves. 1.0 = moves with S&P 500. 1.5 = 50% more volatile.',
};

// ── Types ────────────────────────────────────────────────────────────────
interface MockColumn {
  id: string;
  label: string;
  weights: Record<string, number>;
  tickers: string[];
  locked: Record<string, boolean>;
}

type ScenarioKey = 'normal' | '2008' | 'covid' | 'rateHike' | 'dotcom';
const SCENARIOS: { key: ScenarioKey; label: string }[] = [
  { key: 'normal', label: 'Normal' },
  { key: '2008', label: '2008 Crisis' },
  { key: 'covid', label: 'COVID Crash' },
  { key: 'rateHike', label: 'Rate Hike' },
  { key: 'dotcom', label: 'Dot-Com Bust' },
];

const TECH_TICKERS = new Set(['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA', 'AMD', 'NFLX', 'CRM', 'ADBE']);

const DEFAULT_RISK = { annRet: 0.12, vol: 0.22, beta: 1.00, var95: -0.022, maxDD: -0.25, pe: 20 };

const TECH_SET = new Set(['AAPL','MSFT','NVDA','GOOGL','META','AMZN','TSLA','AMD','NFLX','CRM','ADBE','PLTR','SNOW','INTC','IBM','ORCL']);
const INDEX_SET = new Set(['VOO','SPY','VTI','QQQ']);

// Returns up to 3 specific, actionable Sharpe-improvement tips.
// Aware of what's already in the portfolio and what other sandboxes are doing.
const getSharpeRecs = (
  mockId: string,
  tickers: string[],
  weights: Record<string, number>,
  metrics: ReturnType<typeof calcMetrics>,
  allMocks: MockColumn[]
): string[] => {
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

  // ── 1. Cross-sandbox duplicate detection ────────────────────────────────
  for (const other of allMocks.filter(m => m.id !== mockId)) {
    const shared = tickers.filter(t => other.tickers.includes(t));
    const overlapRatio = shared.length / Math.max(tickers.length, other.tickers.length, 1);
    if (overlapRatio >= 0.85) {
      const wDiff = shared.reduce((s, t) => s + Math.abs((weights[t] || 0) - (other.weights[t] || 0)), 0);
      if (wDiff < 0.12) {
        const last = sorted[sorted.length - 1];
        recs.push(`Near-identical to ${other.label} (${Math.round(overlapRatio * 100)}% overlap). Swap ${last} for an uncorrelated asset (e.g. GLD, TLT, XOM) or try the Max Sharpe preset for a different allocation.`);
        break;
      }
    }
  }

  // ── 2. Single-stock concentration ───────────────────────────────────────
  if (topW > 0.35 && top && recs.length < 3) {
    const reduceAmt = topW - 0.20;
    const candidates = ['GLD', 'TLT', 'VOO', 'JNJ', 'JPM', 'XOM', 'PG'].filter(t => !tickers.includes(t));
    if (candidates.length > 0) {
      recs.push(`${top} = ${(topW * 100).toFixed(0)}% — reduce slider to 20%, add ${candidates[0]} at ${(reduceAmt * 100).toFixed(0)}%. Concentration >35% in one stock raises VaR and drags Sharpe. Est. Sharpe lift: +0.10–0.20.`);
    } else {
      const next = sorted.find(t => t !== top) ?? '';
      if (next) {
        const newNextW = (weights[next] || 0) + reduceAmt;
        recs.push(`${top} = ${(topW * 100).toFixed(0)}% — slide to 20%. Move freed ${(reduceAmt * 100).toFixed(0)}% into ${next} (${((weights[next] || 0) * 100).toFixed(0)}% → ${(newNextW * 100).toFixed(0)}%) to reduce single-stock risk.`);
      }
    }
  }

  // ── 3. Defensive hedge (GLD / TLT) ──────────────────────────────────────
  if (metrics.sharpe < 1.0 && recs.length < 3) {
    if (!hasGLD && !hasTLT) {
      const trimFrom = topW > 0.15 ? ` (trim ${top} slider ${(topW * 100).toFixed(0)}%→${Math.max(Math.round((topW - 0.12) * 100), 5)}%)` : '';
      const estSharpe = (metrics.sharpe + 0.18).toFixed(2);
      recs.push(`No hedge. Add GLD at 12%${trimFrom}. Gold's near-zero equity correlation cushions volatility. Estimated Sharpe: ${estSharpe}.`);
    } else if (hasGLD && gldW < 0.08) {
      const deficit = 0.12 - gldW;
      recs.push(`GLD at ${(gldW * 100).toFixed(0)}% is below the 8% threshold for meaningful hedging. Slide GLD up to 12% (reduce ${top} by ${(deficit * 100).toFixed(0)}%). Below 8%, correlation benefits barely register.`);
    } else if (hasTLT && tltW < 0.08) {
      recs.push(`TLT at ${(tltW * 100).toFixed(0)}% is too small to reduce equity beta. Increase TLT to 12–15% — bonds and equities historically rebalance profitably during volatility spikes.`);
    } else {
      recs.push(`Sharpe ${metrics.sharpe.toFixed(2)}: try Equal Weight preset to see if concentrated sliders are dragging risk-adjusted return below 1.0.`);
    }
  }

  // ── 4. Tech sector overweight ────────────────────────────────────────────
  if (techW > 0.55 && recs.length < 3) {
    const defensive = ['JNJ', 'JPM', 'XOM', 'PG', 'NEE', 'V', 'KO'].filter(t => !tickers.includes(t));
    if (defensive.length >= 2) {
      const trim = Math.round((techW - 0.40) * 100);
      recs.push(`${(techW * 100).toFixed(0)}% tech = highly correlated drawdowns. Cut tech by ${trim}% total → add ${defensive[0]} + ${defensive[1]} at ${Math.round(trim / 2)}% each. Cross-sector diversification lowers max drawdown during tech sell-offs.`);
    }
  }

  // ── 5. Too few holdings ──────────────────────────────────────────────────
  if (tickers.length < 4 && recs.length < 3) {
    const suggest = ['VOO', 'GLD', 'JNJ', 'JPM', 'XOM'].filter(t => !tickers.includes(t)).slice(0, 2);
    recs.push(`Only ${tickers.length} holding${tickers.length === 1 ? '' : 's'} — high unsystematic risk. Add ${suggest.join(' + ')}. Each uncorrelated stock cuts portfolio variance (Modern Portfolio Theory).`);
  }

  // ── 6. High beta ─────────────────────────────────────────────────────────
  if (metrics.beta > 1.3 && recs.length < 3) {
    const lowB = ['GLD', 'TLT', 'NEE', 'PG', 'KO', 'JNJ'].filter(t => !tickers.includes(t));
    if (lowB.length > 0) {
      const estBeta = (metrics.beta * 0.88).toFixed(2);
      recs.push(`Beta ${metrics.beta.toFixed(2)} means a 10% market drop hits you ~${(metrics.beta * 10).toFixed(0)}%. Add ${lowB[0]} (β≈0.3) at 12% → est. portfolio beta drops to ~${estBeta}.`);
    }
  }

  // ── 7. No index ETF anchor ───────────────────────────────────────────────
  if (!hasIndex && metrics.sharpe < 1.5 && recs.length < 3) {
    recs.push('No index ETF. A 20% VOO core eliminates unsystematic risk and historically anchors Sharpe above 1.0 for equity portfolios.');
  }

  // ── Healthy portfolio ────────────────────────────────────────────────────
  if (recs.length === 0) {
    recs.push(`Sharpe ${metrics.sharpe.toFixed(2)} is strong. Use Equal Weight or Max Sharpe preset to confirm you are near the efficient frontier.`);
  }

  return recs.slice(0, 3);
};

// ── Metric calculation ───────────────────────────────────────────────────
const calcMetrics = (tickers: string[], weights: Record<string, number>, scenario: ScenarioKey = 'normal', dynamicRiskDb: Record<string, any> = {}) => {
  const totalW = tickers.reduce((a, t) => a + (weights[t] || 0), 0);
  const norm = totalW > 0 ? totalW : 1;

  let pRet = 0, pVol = 0, pBeta = 0;
  for (const t of tickers) {
    const w = (weights[t] || 0) / norm;
    const risk = dynamicRiskDb[t] ?? TICKER_RISK_DB[t] ?? DEFAULT_RISK;
    let ret = risk.annRet;
    let vol = risk.vol;

    if (scenario === '2008') { ret *= 0.616; vol *= 2.5; }
    else if (scenario === 'covid') { ret *= 0.769; vol *= 2.0; }
    else if (scenario === 'rateHike') { ret *= 0.813; vol *= 1.5; }
    else if (scenario === 'dotcom' && TECH_TICKERS.has(t)) { ret *= 0.558; vol *= 3.0; }
    else if (scenario === 'dotcom') { ret *= 0.90; }

    pRet += w * ret;
    pVol += w * vol;
    pBeta += w * risk.beta;
  }

  const divFactor = Math.max(0.65, 1 - (tickers.length - 1) * 0.06);
  const adjVol = pVol * divFactor;
  const sharpe = adjVol > 0 ? (pRet - 0.04) / adjVol : 0;
  const var95 = -(1.645 * adjVol / Math.sqrt(252));
  const cvar = var95 * 1.4;
  const baseHealth = Math.round(
    Math.min(100, Math.max(0,
      Math.min(100, (sharpe / 2.0) * 100) * 0.40 +
      Math.min(100, Math.max(0, 100 - (Math.abs(var95) * 100 - 2) * (100 / 6))) * 0.30 +
      Math.min(100, Math.max(0, 100 - (adjVol * 100 - 10) * (100 / 30))) * 0.20 +
      (tickers.length >= 5 ? 100 : tickers.length >= 3 ? 80 : 50) * 0.10
    ))
  );

  return { sharpe, var95, healthScore: baseHealth, cvar, beta: pBeta, pRet, adjVol };
};

// ── Mini simulation chart data ───────────────────────────────────────────
const generateSimChart = (sharpe: number, vol: number): { value: number }[] => {
  const data: { value: number }[] = [{ value: 100 }];
  let seed = 42;
  const pseudoRandom = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  for (let w = 1; w <= 51; w++) {
    const prev = data[w - 1].value;
    const drift = (sharpe * vol) / 52;
    const noise = (pseudoRandom() - 0.5) * vol / Math.sqrt(52);
    data.push({ value: prev * (1 + drift + noise) });
  }
  return data;
};

// ── Load/save mocks from localStorage ────────────────────────────────────
const MOCKS_STORAGE = 'arcus-sandbox-mocks';

interface SavedMock { id: string; name: string; weights: Record<string, number>; tickers: string[]; savedAt: string }

const loadSavedMocks = (): MockColumn[] => {
  try {
    const raw = localStorage.getItem(MOCKS_STORAGE);
    if (!raw) return [];
    const saved: SavedMock[] = JSON.parse(raw);
    return saved.map(s => ({
      id: s.id,
      label: s.name,
      weights: s.weights,
      tickers: s.tickers || Object.keys(s.weights),
      locked: {},
    }));
  } catch { return []; }
};

// ── Component ────────────────────────────────────────────────────────────
const Sandbox = () => {
  const isMobile = useIsMobile();
  const navigate = useNavigate();

  const userPortfolio = useMemo(() => {
    try {
      const raw = JSON.parse(localStorage.getItem('arcus-portfolio') || 'null');
      if (raw?.holdings?.length > 0) {
        const filled = raw.holdings.filter((h: { ticker?: string }) => h.ticker);
        if (filled.length > 0) {
          const tickers = filled.map((h: { ticker: string }) => h.ticker);
          const n = tickers.length;
          const weights = Object.fromEntries(tickers.map((t: string) => [t, 1 / n]));
          return { tickers, weights };
        }
      }
    } catch { /* empty */ }
    return {
      tickers: MOCK_PORTFOLIO.tickers,
      weights: Object.fromEntries(MOCK_PORTFOLIO.tickers.map((t, i) => [t, MOCK_PORTFOLIO.weights[i]])),
    };
  }, []);

  const currentTickers = userPortfolio.tickers;
  const currentWeights = userPortfolio.weights;

  const savedMocks = useMemo(() => loadSavedMocks(), []);
  const defaultMocks: MockColumn[] = savedMocks.length > 0 ? savedMocks : [
    { id: 'a', label: 'MOCK A', weights: { ...currentWeights }, tickers: [...currentTickers], locked: {} },
  ];

  const [mocks, setMocks] = useState<MockColumn[]>(defaultMocks);
  const [scenario, setScenario] = useState<ScenarioKey>('normal');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [addingTickerTo, setAddingTickerTo] = useState<string | null>(null);
  const [applyingPreset, setApplyingPreset] = useState<Record<string, boolean>>({});
  const [applyDialogIdx, setApplyDialogIdx] = useState<number | null>(null);
  const [dynamicRiskDb, setDynamicRiskDb] = useState<Record<string, any>>({});
  const [showRecsFor, setShowRecsFor] = useState<Record<string, boolean>>({});
  const [mockAnalysisResults, setMockAnalysisResults] = useState<Record<string, any>>({});
  const [analyzingMockId, setAnalyzingMockId] = useState<string | null>(null);
  const [analysisMockDialogId, setAnalysisMockDialogId] = useState<string | null>(null);

  const currentMetrics = useMemo(() => calcMetrics(currentTickers, currentWeights, scenario, dynamicRiskDb), [currentTickers, currentWeights, scenario, dynamicRiskDb]);

  const addMock = () => {
    const labels = ['B', 'C', 'D', 'E'];
    const idx = mocks.length;
    const id = labels[idx] || `${idx + 1}`;
    setMocks([...mocks, { id, label: `MOCK ${id.toUpperCase()}`, weights: { ...currentWeights }, tickers: [...currentTickers], locked: {} }]);
  };

  const deleteMock = (mockId: string) => {
    setMocks(prev => prev.filter(m => m.id !== mockId));
  };

  const updateWeight = (mockIdx: number, ticker: string, value: number) => {
    setMocks(prev => {
      const newMocks = [...prev];
      const mock = { ...newMocks[mockIdx], weights: { ...newMocks[mockIdx].weights }, locked: { ...newMocks[mockIdx].locked } };
      const lockedSum = mock.tickers.filter(t => t !== ticker && mock.locked[t]).reduce((s, t) => s + (mock.weights[t] || 0), 0);
      const remaining = 1 - lockedSum - value;
      const unlocked = mock.tickers.filter(t => t !== ticker && !mock.locked[t]);
      const unlockSum = unlocked.reduce((s, t) => s + (mock.weights[t] || 0), 0);
      mock.weights[ticker] = Math.max(0, Math.min(1, value));
      if (unlocked.length > 0 && remaining >= 0) {
        for (const t of unlocked) {
          const ratio = unlockSum > 0 ? (mock.weights[t] || 0) / unlockSum : 1 / unlocked.length;
          mock.weights[t] = Math.max(0, remaining * ratio);
        }
      }
      newMocks[mockIdx] = mock;
      return newMocks;
    });
  };

  const toggleLock = (mockIdx: number, ticker: string) => {
    setMocks(prev => {
      const newMocks = [...prev];
      newMocks[mockIdx] = {
        ...newMocks[mockIdx],
        locked: { ...newMocks[mockIdx].locked, [ticker]: !newMocks[mockIdx].locked[ticker] },
      };
      return newMocks;
    });
  };

  const toggleSaveMock = (mock: MockColumn) => {
    try {
      const existingRaw = localStorage.getItem(MOCKS_STORAGE);
      const existing: SavedMock[] = existingRaw ? JSON.parse(existingRaw) : [];
      const isSaved = existing.some(e => e.id === mock.id);
      
      if (isSaved) {
        // Unsave
        const filtered = existing.filter(e => e.id !== mock.id);
        localStorage.setItem(MOCKS_STORAGE, JSON.stringify(filtered));
        toast.info(`${mock.label} unsaved`);
      } else {
        // Save
        existing.push({ id: mock.id, name: mock.label, weights: mock.weights, tickers: mock.tickers, savedAt: new Date().toISOString() });
        localStorage.setItem(MOCKS_STORAGE, JSON.stringify(existing));
        toast.success(`${mock.label} saved`);
      }
    } catch {
      toast.error('Failed to toggle save state');
    }
  };

  const startRename = (mock: MockColumn) => {
    setEditingId(mock.id);
    setEditName(mock.label);
  };

  const confirmRename = (mockIdx: number) => {
    if (editName.trim()) {
      setMocks(prev => {
        const newMocks = [...prev];
        newMocks[mockIdx] = { ...newMocks[mockIdx], label: editName.trim() };
        return newMocks;
      });
    }
    setEditingId(null);
  };

  const applyPreset = async (mockIdx: number, preset: string) => {
    const mock = mocks[mockIdx];

    if (preset === 'equal') {
      const n = mock.tickers.length;
      setMocks(prev => {
        const m = [...prev];
        m[mockIdx] = { ...m[mockIdx], weights: Object.fromEntries(mock.tickers.map(t => [t, 1 / n])) };
        return m;
      });
      return;
    }

    if (preset === 'reset') {
      setMocks(prev => {
        const m = [...prev];
        m[mockIdx] = { ...m[mockIdx], weights: { ...currentWeights }, tickers: [...currentTickers] };
        return m;
      });
      return;
    }

    if (preset === 'riskParity') {
      // 1/vol weighting from TICKER_RISK_DB
      const invVols = mock.tickers.map(t => 1 / (TICKER_RISK_DB[t]?.vol ?? DEFAULT_RISK.vol));
      const sumInvVols = invVols.reduce((a, v) => a + v, 0);
      if (sumInvVols === 0) { toast.error('No volatility data available'); return; }
      const newWeights: Record<string, number> = {};
      mock.tickers.forEach((t, i) => { newWeights[t] = invVols[i] / sumInvVols; });
      setMocks(prev => {
        const m = [...prev];
        m[mockIdx] = { ...m[mockIdx], weights: newWeights };
        return m;
      });
      toast.success('Risk Parity weights applied');
      return;
    }

    // maxSharpe / minVariance — call backend
    setApplyingPreset(prev => ({ ...prev, [mock.id]: true }));
    try {
      const n = mock.tickers.length;
      const req = {
        tickers: mock.tickers,
        weights: mock.tickers.map(() => 1 / n),
        start_date: '2022-01-01',
        end_date: new Date().toISOString().slice(0, 10),
      };
      const result = await optimizePortfolio(req);
      const strategies: { name: string; weights: { ticker: string; weight: number }[] }[] = result?.strategies ?? [];
      const strategyName = preset === 'maxSharpe' ? 'maxsharpe' : 'riskparity';
      const strat = strategies.find(s => s.name?.toLowerCase().replace(/[^a-z]/g, '').includes(strategyName.replace(/[^a-z]/g, ''))) ?? strategies[0];
      if (!strat?.weights?.length) throw new Error('No weights returned');
      const newWeights: Record<string, number> = {};
      for (const w of strat.weights) newWeights[w.ticker] = w.weight;
      setMocks(prev => {
        const m = [...prev];
        m[mockIdx] = { ...m[mockIdx], weights: newWeights };
        return m;
      });
      toast.success(`${preset === 'maxSharpe' ? 'Max Sharpe' : 'Min Variance'} weights applied`);
    } catch {
      toast.info('Using Risk Parity weights (backend offline).');
      // fallback: risk parity
      const invVols = mock.tickers.map(t => 1 / (TICKER_RISK_DB[t]?.vol ?? DEFAULT_RISK.vol));
      const sumInvVols = invVols.reduce((a, v) => a + v, 0);
      const newWeights: Record<string, number> = {};
      mock.tickers.forEach((t, i) => { newWeights[t] = invVols[i] / sumInvVols; });
      setMocks(prev => {
        const m = [...prev];
        m[mockIdx] = { ...m[mockIdx], weights: newWeights };
        return m;
      });
    } finally {
      setApplyingPreset(prev => ({ ...prev, [mock.id]: false }));
    }
  };

  const addTickerToMock = async (mockIdx: number, ticker: string) => {
    if (!ticker) return;
    
    // Optimistic UI update
    setMocks(prev => {
      const newMocks = [...prev];
      const mock = { ...newMocks[mockIdx], weights: { ...newMocks[mockIdx].weights }, tickers: [...newMocks[mockIdx].tickers] };
      if (!mock.tickers.includes(ticker)) {
        mock.tickers.push(ticker);
        mock.weights[ticker] = 0;
        const totalW = mock.tickers.reduce((s, t) => s + (mock.weights[t] || 0), 0);
        if (totalW > 0) {
          for (const t of mock.tickers) mock.weights[t] = (mock.weights[t] || 0) / totalW;
        } else {
          const n = mock.tickers.length;
          for (const t of mock.tickers) mock.weights[t] = 1 / n;
        }
      }
      newMocks[mockIdx] = mock;
      return newMocks;
    });
    setAddingTickerTo(null);

    // Fetch dynamic risk data if missing
    if (!TICKER_RISK_DB[ticker] && !dynamicRiskDb[ticker]) {
      try {
        const req = {
          tickers: [ticker],
          weights: [1],
          start_date: '2022-01-01',
          end_date: new Date().toISOString().slice(0, 10),
        };
        const result = await analyzePortfolio(req);
        if (result?.metrics) {
          const m = result.metrics;
          setDynamicRiskDb(prev => ({
            ...prev,
            [ticker]: {
              annRet: m.annualized_return ?? DEFAULT_RISK.annRet,
              vol: m.volatility ?? DEFAULT_RISK.vol,
              beta: m.beta ?? DEFAULT_RISK.beta,
              var95: m.var_95 ?? DEFAULT_RISK.var95,
              maxDD: m.max_drawdown ?? DEFAULT_RISK.maxDD,
              pe: DEFAULT_RISK.pe
            }
          }));
          toast.success(`Loaded market data for ${ticker}`);
        }
      } catch (err) {
        toast.info(`Using estimated risk data for ${ticker}.`);
      }
    }
  };

  const removeTickerFromMock = (mockIdx: number, ticker: string) => {
    setMocks(prev => {
      const newMocks = [...prev];
      const mock = { ...newMocks[mockIdx], weights: { ...newMocks[mockIdx].weights }, tickers: [...newMocks[mockIdx].tickers] };
      const removedW = mock.weights[ticker] || 0;
      mock.tickers = mock.tickers.filter(t => t !== ticker);
      delete mock.weights[ticker];
      const remaining = mock.tickers;
      const remainingSum = remaining.reduce((s, t) => s + (mock.weights[t] || 0), 0);
      if (remaining.length > 0) {
        for (const t of remaining) {
          const ratio = remainingSum > 0 ? (mock.weights[t] || 0) / remainingSum : 1 / remaining.length;
          mock.weights[t] = (mock.weights[t] || 0) + removedW * ratio;
        }
      }
      newMocks[mockIdx] = mock;
      return newMocks;
    });
  };

  const shareMock = (mock: MockColumn) => {
    const encoded = btoa(JSON.stringify({ name: mock.label, weights: mock.weights }));
    const url = `${window.location.origin}/Arcus/sandbox/view?mock=${encoded}`;
    navigator.clipboard.writeText(url).then(() => {
      toast.success('Link copied! Share your strategy with anyone.');
    }).catch(() => {
      toast.error('Could not copy to clipboard');
    });
  };

  const analyseMock = async (mock: MockColumn, offlineMetrics: ReturnType<typeof calcMetrics>) => {
    setAnalyzingMockId(mock.id);
    try {
      const n = mock.tickers.length;
      const req = {
        tickers: mock.tickers,
        weights: mock.tickers.map(t => mock.weights[t] ?? 1 / n),
        start_date: '2022-01-01',
        end_date: new Date().toISOString().slice(0, 10),
      };
      const result = await analyzePortfolio(req);
      setMockAnalysisResults(prev => ({ ...prev, [mock.id]: { ...result, _offline: false } }));
    } catch {
      setMockAnalysisResults(prev => ({
        ...prev,
        [mock.id]: {
          metrics: {
            health_score: offlineMetrics.healthScore,
            sharpe: offlineMetrics.sharpe,
            var_95: offlineMetrics.var95,
            beta: offlineMetrics.beta,
            cvar_95: offlineMetrics.cvar,
            annualized_return: offlineMetrics.pRet,
            volatility: offlineMetrics.adjVol,
          },
          _offline: true,
        },
      }));
      toast.info('Backend offline — showing estimated metrics');
    } finally {
      setAnalyzingMockId(null);
      setAnalysisMockDialogId(mock.id);
    }
  };

  const bestSharpeIdx = mocks.reduce((best, mock, i) => {
    const s = calcMetrics(mock.tickers, mock.weights, scenario, dynamicRiskDb).sharpe;
    return s > (best.sharpe || 0) ? { idx: i, sharpe: s } : best;
  }, { idx: -1, sharpe: currentMetrics.sharpe }).idx;

  // Apply strategy dialog data
  const applyDialogMock = applyDialogIdx !== null ? mocks[applyDialogIdx] : null;
  const totalPortfolioValue = (() => {
    try {
      const analysis = JSON.parse(localStorage.getItem('arcus-last-analysis') || '{}');
      return analysis?.metrics?.portfolio_value ?? 100000;
    } catch { return 100000; }
  })();

  return (
    <AppLayout title="Strategy Sandbox">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <BackButton to="/dashboard/results" />

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-foreground">Strategy Sandbox</h1>
          <p className="text-muted-foreground text-sm mt-1">Compare your portfolio against simulated alternatives in real-time.</p>
        </motion.div>

        <Disclaimer variant="compact" />

        {/* Scenario Toggle */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="flex flex-wrap gap-2 mt-2">
          {SCENARIOS.map(s => (
            <button
              key={s.key}
              onClick={() => setScenario(s.key)}
              className={`px-3 py-1.5 rounded-full font-mono text-[10px] uppercase tracking-wider transition-all ${
                scenario === s.key
                  ? s.key === 'normal' ? 'bg-primary text-primary-foreground' : 'bg-signal-amber/20 text-signal-amber border border-signal-amber/30'
                  : 'glass text-muted-foreground hover:text-foreground'
              }`}
            >
              {s.label}
            </button>
          ))}
        </motion.div>

        <div
          className="grid gap-4 mt-6"
          style={{
            gridTemplateColumns: isMobile
              ? '1fr'
              : `repeat(${1 + mocks.length + (mocks.length < 4 ? 1 : 0)}, minmax(0, 1fr))`,
          }}
        >
          {/* Current column */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Lock size={14} className="text-primary" />
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">CURRENT</span>
              {scenario !== 'normal' && (
                <span className="ml-auto font-mono text-[8px] px-2 py-0.5 rounded-full bg-signal-amber/10 text-signal-amber">
                  {SCENARIOS.find(s => s.key === scenario)?.label}
                </span>
              )}
            </div>
            <div className="space-y-3">
              {[
                { label: 'Health Score', value: currentMetrics.healthScore, fmt: (n: number) => Math.round(n).toString() },
                { label: 'Sharpe', value: currentMetrics.sharpe, fmt: (n: number) => n.toFixed(2) },
                { label: 'VaR 95%', value: currentMetrics.var95, fmt: (n: number) => `${(n * 100).toFixed(1)}%` },
                { label: 'CVaR', value: currentMetrics.cvar, fmt: (n: number) => `${(n * 100).toFixed(1)}%` },
                { label: 'Beta', value: currentMetrics.beta, fmt: (n: number) => n.toFixed(2) },
              ].map(m => (
                <div key={m.label} className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    {m.label}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="cursor-help text-primary/40 hover:text-primary transition-colors text-[10px]">ⓘ</span>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-[200px] text-xs">{METRIC_TOOLTIPS[m.label]}</TooltipContent>
                    </Tooltip>
                  </span>
                  <span className="font-mono text-sm text-foreground">{m.fmt(m.value)}</span>
                </div>
              ))}
            </div>

            <MiniSimChart sharpe={currentMetrics.sharpe} vol={currentMetrics.adjVol} />

            <div className="mt-4 space-y-3">
              <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>WEIGHTS</span>
              {currentTickers.map(t => (
                <div key={t} className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground w-12">{t}</span>
                  <div className="flex-1 h-1.5 bg-border rounded-full">
                    <div className="h-full bg-muted-foreground/30 rounded-full" style={{ width: `${(currentWeights[t] || 0) * 100}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground w-8 text-right">{((currentWeights[t] || 0) * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Mock columns */}
          <AnimatePresence mode="popLayout">
            {mocks.map((mock, mockIdx) => {
              const metrics = calcMetrics(mock.tickers, mock.weights, scenario, dynamicRiskDb);
              const totalW = mock.tickers.reduce((a, t) => a + (mock.weights[t] || 0), 0);
              const normalized = Math.abs(totalW - 1) < 0.01;
              const isBest = mockIdx === bestSharpeIdx;
              const isLoading = !!applyingPreset[mock.id];
              
              const isSavedLocally = (() => {
                try {
                  const items = JSON.parse(localStorage.getItem(MOCKS_STORAGE) || '[]');
                  return items.some((i: any) => i.id === mock.id);
                } catch { return false; }
              })();

              return (
                <motion.div
                  key={mock.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  transition={{ delay: 0.1 * (mockIdx + 1), duration: 0.15 }}
                  className="glass rounded-xl p-5 relative flex flex-col"
                >
                  {/* Header */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2 min-w-0">
                      {editingId === mock.id ? (
                        <div className="flex items-center gap-1">
                          <input
                            autoFocus
                            value={editName}
                            onChange={e => setEditName(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && confirmRename(mockIdx)}
                            onBlur={() => confirmRename(mockIdx)}
                            className="bg-transparent border-b border-primary font-mono text-[10px] uppercase tracking-wider text-primary w-20 outline-none"
                          />
                          <button onClick={() => confirmRename(mockIdx)}><Check size={10} className="text-primary" /></button>
                        </div>
                      ) : (
                        <button onClick={() => startRename(mock)} className="font-mono text-[10px] uppercase tracking-wider text-primary hover:underline flex items-center gap-1">
                          {mock.label} <Pencil size={8} />
                        </button>
                      )}
                      {isBest && <span className="bg-primary text-primary-foreground font-mono text-[8px] uppercase px-2 py-0.5 rounded-full whitespace-nowrap">BEST SHARPE ↑</span>}
                    </div>
                    <div className="flex items-center gap-1">
                      {/* Presets dropdown */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className={`font-mono text-[9px] text-muted-foreground hover:text-primary px-1.5 py-0.5 rounded glass transition-colors ${isLoading ? 'opacity-50' : ''}`} disabled={isLoading}>
                            {isLoading ? '...' : 'Presets ▾'}
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44">
                          <DropdownMenuItem onClick={() => applyPreset(mockIdx, 'equal')} className="cursor-pointer font-mono text-xs">Equal Weight</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => applyPreset(mockIdx, 'riskParity')} className="cursor-pointer font-mono text-xs">Risk Parity</DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => applyPreset(mockIdx, 'maxSharpe')} className="cursor-pointer font-mono text-xs">Max Sharpe ✦</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => applyPreset(mockIdx, 'minVariance')} className="cursor-pointer font-mono text-xs">Min Variance ✦</DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => applyPreset(mockIdx, 'reset')} className="cursor-pointer font-mono text-xs text-muted-foreground">Reset to Current</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      {/* Share button */}
                      <button onClick={() => shareMock(mock)} className="text-muted-foreground hover:text-primary transition-colors p-1" title="Share strategy link">
                        <Share2 size={11} />
                      </button>
                      <button onClick={() => toggleSaveMock(mock)} className={`transition-colors p-1 ${isSavedLocally ? 'text-primary' : 'text-muted-foreground hover:text-primary'}`} title={isSavedLocally ? 'Unsave mock' : 'Save mock'}>
                        <BookmarkPlus size={12} className={isSavedLocally ? 'fill-primary' : ''} />
                      </button>
                      <button onClick={() => deleteMock(mock.id)} className="text-muted-foreground hover:text-signal-red transition-colors p-1" title="Delete mock">
                        <X size={12} />
                      </button>
                    </div>
                  </div>

                  {/* Scenario badge */}
                  {scenario !== 'normal' && (
                    <span className="font-mono text-[8px] px-2 py-0.5 rounded-full bg-signal-amber/10 text-signal-amber block mb-2">
                      Scenario: {SCENARIOS.find(s => s.key === scenario)?.label}
                    </span>
                  )}

                  {/* Weight total badge */}
                  <span className={`font-mono text-[10px] block mb-2 ${normalized ? 'text-signal-green' : 'text-signal-amber'}`}>
                    Total: {(totalW * 100).toFixed(0)}% {normalized ? '✓' : ''}
                  </span>

                  {/* Metrics */}
                  <div className="space-y-3">
                    {[
                      { label: 'Health Score', value: metrics.healthScore, cValue: currentMetrics.healthScore, fmt: (n: number) => Math.round(n).toString() },
                      { label: 'Sharpe', value: metrics.sharpe, cValue: currentMetrics.sharpe, fmt: (n: number) => n.toFixed(2) },
                      { label: 'VaR 95%', value: metrics.var95, cValue: currentMetrics.var95, fmt: (n: number) => `${(n * 100).toFixed(1)}%` },
                      { label: 'CVaR', value: metrics.cvar, cValue: currentMetrics.cvar, fmt: (n: number) => `${(n * 100).toFixed(1)}%` },
                      { label: 'Beta', value: metrics.beta, cValue: currentMetrics.beta, fmt: (n: number) => n.toFixed(2) },
                    ].map(m => {
                      const delta = m.value - m.cValue;
                      const isGood = m.label === 'VaR 95%' || m.label === 'CVaR' ? delta < 0 : delta > 0;
                      return (
                        <div key={m.label} className="flex justify-between items-center">
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            {m.label}
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="cursor-help text-primary/40 hover:text-primary transition-colors text-[10px]">ⓘ</span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-[200px] text-xs">{METRIC_TOOLTIPS[m.label]}</TooltipContent>
                            </Tooltip>
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm text-foreground">
                              <AnimatedNumber value={m.value} format={m.fmt} duration={0.6} />
                            </span>
                            {Math.abs(delta) > 0.01 && (
                              <motion.span
                                key={m.value}
                                initial={{ opacity: 0, y: 4 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${isGood ? 'bg-signal-green/10 text-signal-green' : 'bg-signal-red/10 text-signal-red'}`}
                              >
                                {isGood ? '▲' : '▼'} {Math.abs(delta).toFixed(2)}
                              </motion.span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <MiniSimChart sharpe={metrics.sharpe} vol={metrics.adjVol} />

                  {/* Analyse button */}
                  <button
                    onClick={() => analyseMock(mock, metrics)}
                    disabled={analyzingMockId === mock.id}
                    className="mt-3 w-full flex items-center justify-center gap-1.5 glass border border-primary/20 hover:border-primary/40 text-primary rounded-lg py-1.5 font-mono text-[10px] transition-colors disabled:opacity-50"
                  >
                    {analyzingMockId === mock.id ? (
                      <><motion.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="inline-block">⟳</motion.span> Analysing...</>
                    ) : (
                      'Analyse Portfolio →'
                    )}
                  </button>

                  {/* Weights with lock/unlock */}
                  <div className="mt-4 space-y-3">
                    <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>WEIGHTS</span>
                    {mock.tickers.map(t => (
                        <div key={t} className="flex items-center gap-1.5">
                          <button onClick={() => toggleLock(mockIdx, t)} className="text-muted-foreground hover:text-primary transition-colors flex-shrink-0" title={mock.locked[t] ? 'Unlock' : 'Lock'}>
                            {mock.locked[t] ? <Lock size={10} /> : <Unlock size={10} />}
                          </button>
                          <span className="font-mono text-[10px] text-muted-foreground w-10 flex items-center gap-0.5">
                            {t}
                            {!TICKER_RISK_DB[t] && !dynamicRiskDb[t] && <span className="text-signal-amber text-[8px]" title="Using estimated risk data">~</span>}
                          </span>
                          <input
                            type="range" min="0" max="100"
                            value={Math.round((mock.weights[t] || 0) * 100)}
                            onChange={e => updateWeight(mockIdx, t, Number(e.target.value) / 100)}
                            disabled={mock.locked[t]}
                            className="flex-1 min-w-0 h-1.5 appearance-none bg-border rounded-full cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary disabled:opacity-40"
                          />
                          <span className="font-mono text-[10px] text-foreground w-8 text-right">{((mock.weights[t] || 0) * 100).toFixed(0)}%</span>
                          <button onClick={() => removeTickerFromMock(mockIdx, t)} className="text-muted-foreground hover:text-signal-red transition-colors flex-shrink-0" title="Remove ticker">
                            <Minus size={10} />
                          </button>
                        </div>
                      )
                    )}

                    {/* Add ticker */}
                    {addingTickerTo === mock.id ? (
                      <div className="flex items-center gap-1">
                        <div className="flex-1">
                          <StockSearch value="" onChange={() => {}} onSelect={t => addTickerToMock(mockIdx, t)} placeholder="Add stock..." />
                        </div>
                        <button onClick={() => setAddingTickerTo(null)} className="text-muted-foreground hover:text-foreground"><X size={12} /></button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setAddingTickerTo(mock.id)}
                        className="glass rounded-lg p-1.5 w-full text-center text-muted-foreground hover:text-primary font-mono text-[10px] transition-colors"
                      >
                        <Plus size={10} className="inline mr-1" /> Add Stock
                      </button>
                    )}
                  </div>

                  {/* Sharpe Recommendations */}
                  <div className="mt-4">
                    <button
                      onClick={() => setShowRecsFor(prev => ({ ...prev, [mock.id]: !prev[mock.id] }))}
                      className="flex items-center gap-1.5 w-full text-left"
                    >
                      <Lightbulb size={11} className="text-signal-amber flex-shrink-0" />
                      <span className="font-mono text-[10px] uppercase tracking-wider text-signal-amber">Sharpe Tips</span>
                      <ChevronRight size={10} className={`ml-auto text-muted-foreground transition-transform ${showRecsFor[mock.id] ? 'rotate-90' : ''}`} />
                    </button>
                    <AnimatePresence>
                      {showRecsFor[mock.id] && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-2 space-y-1.5">
                            {getSharpeRecs(mock.id, mock.tickers, mock.weights, metrics, mocks).map((rec, ri) => (
                              <div key={ri} className="flex items-start gap-1.5 rounded-md bg-signal-amber/5 border border-signal-amber/15 px-2.5 py-2">
                                <span className="font-mono text-signal-amber text-[9px] flex-shrink-0 mt-0.5">{ri + 1}.</span>
                                <p className="font-mono text-[10px] text-foreground/80 leading-relaxed">{rec}</p>
                              </div>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* Apply Strategy button — only on best sharpe card */}
                  {isBest && (
                    <button
                      onClick={() => setApplyDialogIdx(mockIdx)}
                      className="mt-4 w-full flex items-center justify-center gap-1.5 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-lg py-2 font-mono text-[10px] transition-colors"
                    >
                      Apply Strategy <ChevronRight size={11} />
                    </button>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>

          {/* Add mock column */}
          {mocks.length < 4 && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={addMock}
              className={`glass rounded-xl p-5 border-2 border-dashed border-border hover:border-primary/30 transition-colors flex flex-col items-center justify-center ${isMobile ? 'py-6' : 'min-h-[300px]'}`}
            >
              <Plus size={24} className="text-primary mb-2" />
              <span className="font-mono text-xs text-muted-foreground">ADD MOCK</span>
            </motion.button>
          )}
        </div>

        <Disclaimer variant="compact" />
      </div>

      {/* Apply Strategy Dialog */}
      <Dialog open={applyDialogIdx !== null} onOpenChange={open => !open && setApplyDialogIdx(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-mono text-sm">
              Apply {applyDialogMock?.label} to Your Portfolio
            </DialogTitle>
          </DialogHeader>
          {applyDialogMock && (() => {
            const totalW = applyDialogMock.tickers.reduce((s, t) => s + (applyDialogMock.weights[t] || 0), 0) || 1;
            return (
              <div className="space-y-4">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="font-mono text-[10px] text-muted-foreground text-left pb-2">Asset</th>
                      <th className="font-mono text-[10px] text-muted-foreground text-right pb-2">Current %</th>
                      <th className="font-mono text-[10px] text-muted-foreground text-right pb-2">New %</th>
                      <th className="font-mono text-[10px] text-muted-foreground text-right pb-2">Est. Change</th>
                      <th className="font-mono text-[10px] text-muted-foreground text-right pb-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {applyDialogMock.tickers.map(t => {
                      const newW = (applyDialogMock.weights[t] || 0) / totalW;
                      const curW = currentWeights[t] || 0;
                      const diff = newW - curW;
                      const dollarDiff = diff * totalPortfolioValue;
                      const action = Math.abs(diff) < 0.005 ? 'No change' : diff > 0 ? 'Buy more' : 'Reduce';
                      const actionColor = action === 'Buy more' ? 'text-signal-green' : action === 'Reduce' ? 'text-signal-red' : 'text-muted-foreground';
                      return (
                        <tr key={t} className="border-b border-border/50">
                          <td className="font-mono text-foreground py-2">{t}</td>
                          <td className="font-mono text-muted-foreground text-right py-2">{(curW * 100).toFixed(0)}%</td>
                          <td className="font-mono text-foreground text-right py-2">{(newW * 100).toFixed(0)}%</td>
                          <td className={`font-mono text-right py-2 ${dollarDiff >= 0 ? 'text-signal-green' : 'text-signal-red'}`}>
                            {dollarDiff >= 0 ? '+' : ''}${Math.abs(dollarDiff).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                          </td>
                          <td className={`font-mono text-right py-2 ${actionColor}`}>{action}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <p className="font-mono text-[10px] text-muted-foreground">
                  Based on estimated portfolio value of ${totalPortfolioValue.toLocaleString()}
                </p>
                <button
                  onClick={() => {
                    const totalW2 = applyDialogMock.tickers.reduce((s, t) => s + (applyDialogMock.weights[t] || 0), 0) || 1;
                    const normalizedWeights: Record<string, number> = {};
                    applyDialogMock.tickers.forEach(t => { normalizedWeights[t] = (applyDialogMock.weights[t] || 0) / totalW2; });
                    setApplyDialogIdx(null);
                    navigate('/dashboard', { state: { weights: normalizedWeights, tickers: applyDialogMock.tickers } });
                  }}
                  className="w-full bg-primary text-primary-foreground font-mono text-xs py-2.5 rounded-lg hover:opacity-90 transition-opacity"
                >
                  Load in Portfolio Builder →
                </button>
              </div>
            );
          })()}
        </DialogContent>
      </Dialog>
      {/* Mock Analysis Dialog */}
      <Dialog open={analysisMockDialogId !== null} onOpenChange={open => !open && setAnalysisMockDialogId(null)}>
        <DialogContent className="max-w-md">
          {(() => {
            const mock = mocks.find(m => m.id === analysisMockDialogId);
            const r = analysisMockDialogId ? mockAnalysisResults[analysisMockDialogId] : null;
            if (!mock || !r) return null;
            const m = r.metrics;
            const offlineMock = calcMetrics(mock.tickers, mock.weights, scenario, dynamicRiskDb);
            const rows = [
              { label: 'Health Score', value: m.health_score != null ? Math.round(m.health_score).toString() : offlineMock.healthScore.toString() },
              { label: 'Sharpe', value: (m.sharpe ?? offlineMock.sharpe).toFixed(2) },
              { label: 'VaR 95%', value: `${((m.var_95 ?? offlineMock.var95) * 100).toFixed(1)}%` },
              { label: 'Beta', value: (m.beta ?? offlineMock.beta).toFixed(2) },
              { label: 'Volatility', value: `${((m.volatility ?? offlineMock.adjVol) * 100).toFixed(1)}%` },
              { label: 'Ann. Return', value: `${((m.annualized_return ?? offlineMock.pRet) * 100).toFixed(1)}%` },
            ];
            return (
              <>
                <DialogHeader>
                  <DialogTitle className="font-mono text-sm flex items-center gap-2">
                    {mock.label} — Full Analysis
                    {r._offline && <span className="text-signal-amber text-[10px] font-normal">(estimated)</span>}
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-2">
                    {rows.map(row => (
                      <div key={row.label} className="glass rounded-lg p-3 text-center">
                        <p className="font-mono text-[9px] text-muted-foreground">{row.label}</p>
                        <p className="font-mono text-sm font-bold text-foreground mt-1">{row.value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-1">
                    <span className="font-mono text-[10px] text-signal-amber flex items-center gap-1"><Lightbulb size={11} /> Sharpe Tips</span>
                    {getSharpeRecs(mock.id, mock.tickers, mock.weights, offlineMock, mocks).map((rec, ri) => (
                      <div key={ri} className="flex items-start gap-1.5 rounded-md bg-signal-amber/5 border border-signal-amber/15 px-2.5 py-2">
                        <span className="font-mono text-signal-amber text-[9px] flex-shrink-0 mt-0.5">{ri + 1}.</span>
                        <p className="font-mono text-[10px] text-foreground/80 leading-relaxed">{rec}</p>
                      </div>
                    ))}
                  </div>
                  {r._offline && <p className="font-mono text-[10px] text-muted-foreground">Connect backend for historical analysis with real market data.</p>}
                  <button
                    onClick={() => {
                      const totalW = mock.tickers.reduce((s, t) => s + (mock.weights[t] || 0), 0) || 1;
                      const nw: Record<string, number> = {};
                      mock.tickers.forEach(t => { nw[t] = (mock.weights[t] || 0) / totalW; });
                      setAnalysisMockDialogId(null);
                      navigate('/dashboard', { state: { weights: nw, tickers: mock.tickers } });
                    }}
                    className="w-full bg-primary text-primary-foreground font-mono text-xs py-2.5 rounded-lg hover:opacity-90 transition-opacity"
                  >
                    Load in Portfolio Builder →
                  </button>
                </div>
              </>
            );
          })()}
        </DialogContent>
      </Dialog>

    </AppLayout>
  );
};

// ── Mini simulation chart ────────────────────────────────────────────────
const MiniSimChart = ({ sharpe, vol }: { sharpe: number; vol: number }) => {
  const data = useMemo(() => generateSimChart(sharpe, vol), [sharpe, vol]);
  const endValue = data[data.length - 1]?.value ?? 100;
  const isPositive = endValue >= 100;
  const color = isPositive ? '#3FB68B' : '#F0514F';

  return (
    <div className="mt-3">
      <span className="font-mono text-[9px] text-muted-foreground/60">12-month simulation</span>
      <div className="h-[96px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={`grad-${isPositive ? 'g' : 'r'}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.25} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={1.5}
              fill={`url(#grad-${isPositive ? 'g' : 'r'})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default Sandbox;
