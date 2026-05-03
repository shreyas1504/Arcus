import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Wallet, TrendingUp, TrendingDown, CalendarDays,
  Shield, BarChart2, ArrowUpRight, ArrowDownRight, Minus,
  UserCircle, Sparkles, Eye, EyeOff,
} from 'lucide-react';
import AppLayout from '@/components/AppLayout';
import { usePortfolioConfig } from '@/hooks/use-portfolio';
import { loadSettings } from '@/hooks/use-settings';
import { MOCK_STOCK_PRICES, computePortfolioMetrics } from '@/lib/mock-data';

// ── RAG (Red / Amber / Green) model ─────────────────────────────────────

type RAGLevel = 'green' | 'amber' | 'red';

const ragColor = (l: RAGLevel) =>
  l === 'green' ? 'text-signal-green' : l === 'amber' ? 'text-signal-amber' : 'text-signal-red';

const ragBg = (l: RAGLevel) =>
  l === 'green'
    ? 'bg-signal-green/10 border-signal-green/20'
    : l === 'amber'
    ? 'bg-signal-amber/10 border-signal-amber/20'
    : 'bg-signal-red/10 border-signal-red/20';

const ragGlow = (l: RAGLevel) =>
  l === 'green'
    ? '0 0 40px rgba(63,182,139,.15), 0 0 80px rgba(63,182,139,.05)'
    : l === 'amber'
    ? '0 0 40px rgba(240,164,79,.15), 0 0 80px rgba(240,164,79,.05)'
    : '0 0 40px rgba(240,81,79,.12), 0 0 80px rgba(240,81,79,.04)';

const ragGradient = (l: RAGLevel) =>
  l === 'green'
    ? 'from-signal-green/5 via-transparent to-primary/5'
    : l === 'amber'
    ? 'from-signal-amber/5 via-transparent to-primary/5'
    : 'from-signal-red/5 via-transparent to-primary/5';

const classifyGainLoss = (pct: number): RAGLevel =>
  pct >= 3 ? 'green' : pct >= -3 ? 'amber' : 'red';

const classifyMetric = (label: string, value: number): RAGLevel => {
  switch (label) {
    case 'sharpe':     return value >= 1 ? 'green' : value >= 0.5 ? 'amber' : 'red';
    case 'health':     return value >= 70 ? 'green' : value >= 40 ? 'amber' : 'red';
    case 'volatility': return value <= 15 ? 'green' : value <= 25 ? 'amber' : 'red';
    case 'drawdown':   return value >= -15 ? 'green' : value >= -30 ? 'amber' : 'red';
    case 'beta':       return (value >= 0.8 && value <= 1.2) ? 'green' : (value >= 0.5 && value <= 1.5) ? 'amber' : 'red';
    default:           return 'amber';
  }
};

const fmtDate = (d: string) => {
  try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); }
  catch { return d; }
};

const daysBetween = (a: string, b: string) => {
  try { return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 86_400_000); }
  catch { return 0; }
};

// ── Animated counter ────────────────────────────────────────────────────

const AnimVal = ({ value, prefix = '' }: { value: number; prefix?: string }) => {
  const [disp, setDisp] = useState(0);
  useEffect(() => {
    const start = disp;
    const diff = value - start;
    const dur = 1200;
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - t0) / dur, 1);
      setDisp(start + diff * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);
  return <>{prefix}{disp.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</>;
};

// ── RAG Dot ─────────────────────────────────────────────────────────────

const RAGDot = ({ level }: { level: RAGLevel }) => {
  const c = level === 'green' ? 'bg-signal-green' : level === 'amber' ? 'bg-signal-amber' : 'bg-signal-red';
  return (
    <span className="relative flex items-center justify-center w-2.5 h-2.5">
      <span className={`absolute inset-0 rounded-full ${c} opacity-30 animate-ping`} />
      <span className={`relative w-2 h-2 rounded-full ${c}`} />
    </span>
  );
};

// ── Metric pill ─────────────────────────────────────────────────────────

const MetricPill = ({ label, value, unit, rag, delay = 0 }: {
  label: string; value: string; unit?: string; rag: RAGLevel; delay?: number;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className={`flex items-center justify-between gap-3 rounded-xl border px-4 py-3 ${ragBg(rag)} backdrop-blur-sm`}
  >
    <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
    <span className={`font-mono text-sm font-bold ${ragColor(rag)}`}>
      {value}{unit && <span className="text-[10px] ml-0.5 font-normal opacity-70">{unit}</span>}
    </span>
  </motion.div>
);

// ═════════════════════════════════════════════════════════════════════════
//  PROFILE PAGE
// ═════════════════════════════════════════════════════════════════════════

const Profile = () => {
  const config = usePortfolioConfig();
  const settings = loadSettings();
  const [vaultMode, setVaultMode] = useState(settings.vaultMode);
  const dna = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('arcus-investor-dna') || 'null'); } catch { return null; }
  }, []);

  const tickers = config?.holdings.filter(h => h.ticker).map(h => h.ticker.toUpperCase()) ?? [];
  const shares  = config?.holdings.filter(h => h.ticker).map(h => parseFloat(h.shares) || 0) ?? [];
  const costs   = config?.holdings.filter(h => h.ticker).map(h => parseFloat(h.cost) || 0) ?? [];

  // Portfolio value — uses mock prices (same source as Dashboard)
  const totalMarketValue = tickers.reduce((sum, t, i) => {
    const price = MOCK_STOCK_PRICES[t] || 0;
    return sum + (shares[i] || 0) * price;
  }, 0);

  const totalCostBasis = tickers.reduce((sum, _, i) => sum + (shares[i] || 0) * (costs[i] || 0), 0);
  const totalGainLoss  = totalMarketValue - totalCostBasis;
  const totalGainPct   = totalCostBasis > 0 ? (totalGainLoss / totalCostBasis) * 100 : 0;
  const gainRag        = classifyGainLoss(totalGainPct);
  const isPositive     = totalGainLoss >= 0;

  const startDate  = config?.startDate ?? '2023-01-01';
  const today      = new Date().toISOString().split('T')[0];
  const holdDays   = daysBetween(startDate, today);
  const hasPort    = tickers.length > 0;

  const m = computePortfolioMetrics(tickers, shares.length > 0 ? shares : undefined, settings.riskFreeRate);

  const investorName = dna?.name || 'Investor';
  const riskProfile  = dna?.risk_tolerance || 'Moderate';

  return (
    <AppLayout title="My Profile">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center gap-3 mb-1.5">
            <UserCircle size={20} className="text-primary" />
            <h1 className="font-display font-bold text-xl text-foreground">My Profile</h1>
          </div>
          <p className="font-mono text-[11px] text-muted-foreground">
            Your portfolio snapshot and investor identity at a glance.
          </p>
        </motion.div>

        {/* ─────────────────────────────────────────────────────────────
            WALLET CARD
        ───────────────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 0.05, type: 'spring', stiffness: 200, damping: 24 }}
          className={`relative rounded-2xl overflow-hidden border border-border/60 mb-6 bg-gradient-to-br ${ragGradient(hasPort ? gainRag : 'amber')}`}
          style={{ boxShadow: hasPort ? ragGlow(gainRag) : ragGlow('amber') }}
        >
          {/* Background mesh */}
          <div className="absolute inset-0 teal-grid-bg opacity-40 pointer-events-none" />
          <div className="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-primary/3 rounded-full blur-2xl pointer-events-none" />

          <div className="relative p-6 sm:p-8">

            {/* Top row */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-primary/15 border border-primary/20 flex items-center justify-center">
                  <Wallet size={18} className="text-primary" />
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground block">Portfolio Wallet</span>
                  <span className="font-display text-xs font-semibold text-foreground">{investorName}</span>
                </div>
              </div>
              <button
                onClick={() => setVaultMode(v => !v)}
                className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-lg hover:bg-card-elevated"
                title={vaultMode ? 'Show values' : 'Hide values'}
              >
                {vaultMode ? <EyeOff size={14} /> : <Eye size={14} />}
                <span className="font-mono text-[9px] uppercase">{vaultMode ? 'Hidden' : 'Visible'}</span>
              </button>
            </div>

            {/* Total Value */}
            <div className="mb-6">
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground/70 mb-1 block">
                Total Portfolio Value
              </span>
              {hasPort ? (
                <div className="font-mono text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight leading-none">
                  {vaultMode ? '$•••,•••.••' : <AnimVal value={totalMarketValue} prefix="$" />}
                </div>
              ) : (
                <div className="font-mono text-3xl font-bold text-muted-foreground/40">No portfolio yet</div>
              )}
            </div>

            {/* Gain / Loss strip */}
            {hasPort && totalCostBasis > 0 && (
              <motion.div
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className={`inline-flex items-center gap-2.5 rounded-xl border px-4 py-2.5 mb-6 ${ragBg(gainRag)}`}
              >
                <RAGDot level={gainRag} />
                {isPositive
                  ? <ArrowUpRight size={16} className={ragColor(gainRag)} />
                  : totalGainLoss === 0
                    ? <Minus size={16} className={ragColor(gainRag)} />
                    : <ArrowDownRight size={16} className={ragColor(gainRag)} />}
                <span className={`font-mono text-lg font-bold ${ragColor(gainRag)}`}>
                  {vaultMode
                    ? '•••.••'
                    : `${isPositive ? '+' : ''}$${Math.abs(totalGainLoss).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                </span>
                <span className={`font-mono text-sm font-semibold ${ragColor(gainRag)}`}>
                  ({isPositive ? '+' : ''}{totalGainPct.toFixed(2)}%)
                </span>
                <span className="font-mono text-[9px] text-muted-foreground uppercase ml-1">
                  {isPositive ? 'Gain' : totalGainLoss === 0 ? 'Flat' : 'Loss'} since invested
                </span>
              </motion.div>
            )}

            {/* Date range */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="flex flex-wrap items-center gap-4 text-muted-foreground"
            >
              <div className="flex items-center gap-1.5">
                <CalendarDays size={13} className="text-primary" />
                <span className="font-mono text-[10px]">Invested from</span>
                <span className="font-mono text-[10px] font-semibold text-foreground">{fmtDate(startDate)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CalendarDays size={13} className="text-primary" />
                <span className="font-mono text-[10px]">Analysed till</span>
                <span className="font-mono text-[10px] font-semibold text-foreground">{fmtDate(today)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-[10px] text-muted-foreground/60">·</span>
                <span className="font-mono text-[10px] font-semibold text-primary">{holdDays} days</span>
              </div>
            </motion.div>

            {/* Holdings chips */}
            {hasPort && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }} className="flex flex-wrap gap-1.5 mt-5">
                {tickers.map(t => (
                  <span key={t} className="font-mono text-[10px] bg-primary/10 text-primary px-2.5 py-0.5 rounded-full border border-primary/15">{t}</span>
                ))}
              </motion.div>
            )}
          </div>

          {/* Card bottom accent stripe */}
          <div className="h-1 bg-gradient-to-r from-primary/40 via-primary to-primary/40" />
        </motion.div>

        {/* ─────────────────────────────────────────────────────────────
            RAG DIAGNOSTICS GRID
        ───────────────────────────────────────────────────────────── */}
        {hasPort && (
          <>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="mb-4">
              <div className="flex items-center gap-2 mb-1">
                <Sparkles size={14} className="text-primary" />
                <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Portfolio Diagnostics</span>
              </div>
              <p className="font-mono text-[10px] text-muted-foreground/60">
                RAG health indicators —
                <span className="text-signal-green"> Green</span> = healthy ·
                <span className="text-signal-amber"> Amber</span> = caution ·
                <span className="text-signal-red"> Red</span> = action needed
              </p>
            </motion.div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              <MetricPill label="Health Score"       value={`${m.health_score}`}                  unit="/100" rag={classifyMetric('health', m.health_score)}      delay={0.35} />
              <MetricPill label="Sharpe Ratio"       value={m.sharpe.toFixed(2)}                             rag={classifyMetric('sharpe', m.sharpe)}              delay={0.4}  />
              <MetricPill label="Annualised Return"  value={`${(m.annualized_return * 100).toFixed(1)}`} unit="%" rag={m.annualized_return >= 0.10 ? 'green' : m.annualized_return >= 0.05 ? 'amber' : 'red'} delay={0.45} />
              <MetricPill label="Volatility"         value={`${(m.volatility * 100).toFixed(1)}`} unit="%"   rag={classifyMetric('volatility', m.volatility * 100)} delay={0.5}  />
              <MetricPill label="Max Drawdown"       value={`${(m.max_drawdown * 100).toFixed(1)}`} unit="%" rag={classifyMetric('drawdown', m.max_drawdown * 100)} delay={0.55} />
              <MetricPill label="Beta"               value={m.beta.toFixed(2)}                               rag={classifyMetric('beta', m.beta)}                  delay={0.6}  />
            </div>
          </>
        )}

        {/* ─────────────────────────────────────────────────────────────
            INVESTOR DNA
        ───────────────────────────────────────────────────────────── */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="glass rounded-xl p-5 mb-4">
          <div className="flex items-center gap-2 mb-5 pb-3 border-b border-border">
            <Shield size={14} className="text-primary" />
            <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>INVESTOR DNA</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="text-center">
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground block mb-1">Risk Profile</span>
              <span className="font-mono text-sm font-bold text-foreground">{riskProfile}</span>
            </div>
            <div className="text-center">
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground block mb-1">Target Return</span>
              <span className="font-mono text-sm font-bold text-foreground">
                {dna?.target_return ? `${(dna.target_return * 100).toFixed(0)}%` : `${(settings.targetReturn * 100).toFixed(0)}%`}
              </span>
            </div>
            <div className="text-center">
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground block mb-1">Sectors</span>
              <span className="font-mono text-[11px] font-bold text-foreground">
                {dna?.sectors?.length ? dna.sectors.join(', ') : 'All'}
              </span>
            </div>
          </div>
        </motion.div>

        {/* ─────────────────────────────────────────────────────────────
            ANALYSIS CONFIG
        ───────────────────────────────────────────────────────────── */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.55 }} className="glass rounded-xl p-5">
          <div className="flex items-center gap-2 mb-5 pb-3 border-b border-border">
            <BarChart2 size={14} className="text-primary" />
            <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>ANALYSIS CONFIG</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="text-center">
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground block mb-1">Benchmark</span>
              <span className="font-mono text-sm font-bold text-foreground">{settings.benchmark}</span>
            </div>
            <div className="text-center">
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground block mb-1">Risk-Free Rate</span>
              <span className="font-mono text-sm font-bold text-foreground">{(settings.riskFreeRate * 100).toFixed(1)}%</span>
            </div>
            <div className="text-center">
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground block mb-1">Holdings</span>
              <span className="font-mono text-sm font-bold text-primary">{tickers.length}</span>
            </div>
          </div>
        </motion.div>
      </div>
    </AppLayout>
  );
};

export default Profile;
