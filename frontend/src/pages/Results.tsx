import { useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { motion } from 'framer-motion';
import { Activity, TrendingUp, TrendingDown, Shield, BarChart2, AlertTriangle, Zap, GitBranch, Download, ChevronRight, CheckCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import AppLayout from '@/components/AppLayout';
import PDFReportDocument from '@/components/PDFReportDocument';
import BackButton from '@/components/BackButton';
import MetricCard from '@/components/MetricCard';
import HealthGauge from '@/components/HealthGauge';
import PerformanceChart from '@/components/charts/PerformanceChart';
import DrawdownChart from '@/components/charts/DrawdownChart';
import MonteCarloChart from '@/components/charts/MonteCarloChart';
import RiskAttribution from '@/components/charts/RiskAttribution';
import SectorDonut from '@/components/charts/SectorDonut';
import EfficientFrontier from '@/components/charts/EfficientFrontier';
import CorrelationHeatmap from '@/components/CorrelationHeatmap';
import StressTestGrid from '@/components/StressTestGrid';
import PastVsFuture from '@/components/PastVsFuture';
import FullReport from '@/components/FullReport';
import { MOCK_PORTFOLIO, MOCK_SPARKLINES, MOCK_OPTIMAL_WEIGHTS, MOCK_STOCK_PRICES, TICKER_SECTOR_MAP, computePortfolioMetrics } from '@/lib/mock-data';
import { openChatWithMessage } from '@/components/FloatingChat';
import { analyzePortfolio, optimizePortfolio, runMonteCarlo, runStressTest, getEfficientFrontier, getRecommendations } from '@/lib/api';
import { usePortfolioConfig, portfolioToRequest } from '@/hooks/use-portfolio';

const askAI = (question: string) => {
  openChatWithMessage.dispatchEvent(new CustomEvent('open', { detail: { message: question } }));
};

const SectionHeader = ({ label, chatQuestion }: { label: string; chatQuestion?: string }) => (
  <div className="flex items-center justify-between mb-4">
    <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>{label}</span>
    {chatQuestion && (
      <button onClick={() => askAI(chatQuestion)} className="font-mono text-[10px] text-primary/60 hover:text-primary flex items-center gap-1 transition-colors border border-primary/20 hover:border-primary/40 rounded-full px-2.5 py-1">
        <Zap size={10} /> Ask AI →
      </button>
    )}
  </div>
);

const Results = () => {
  const config = usePortfolioConfig();
  const req = config ? portfolioToRequest(config) : null;

  const { data: analysis, isLoading } = useQuery({
    queryKey: ['analyze', req],
    queryFn: () => analyzePortfolio(req!),
    enabled: !!req,
    staleTime: 5 * 60 * 1000,
  });

  const { data: optimize } = useQuery({
    queryKey: ['optimize', req],
    queryFn: () => optimizePortfolio(req!),
    enabled: !!req,
    staleTime: 5 * 60 * 1000,
  });

  const { data: monteCarlo } = useQuery({
    queryKey: ['monte-carlo', req],
    queryFn: () => runMonteCarlo({ ...req!, n_days: 252, n_simulations: 1000, initial_value: 100000 }),
    enabled: !!req,
    staleTime: 5 * 60 * 1000,
  });

  const { data: stressTests } = useQuery({
    queryKey: ['stress-test', req],
    queryFn: () => runStressTest(req!),
    enabled: !!req,
    staleTime: 5 * 60 * 1000,
  });

  const { data: frontier } = useQuery({
    queryKey: ['frontier', req],
    queryFn: () => getEfficientFrontier(req!),
    enabled: !!req,
    staleTime: 5 * 60 * 1000,
  });

  // Cache analysis for chat context
  useEffect(() => {
    if (analysis) localStorage.setItem('arcus-last-analysis', JSON.stringify(analysis));
  }, [analysis]);

  // Use real metrics or fallback to mock
  // When backend is unavailable, compute from the user's actual tickers
  const userTickers = config?.holdings.filter(h => h.ticker).map(h => h.ticker) ?? [];
  const userShares  = config?.holdings.filter(h => h.ticker).map(h => parseFloat(h.shares) || 1) ?? [];
  const rawMetrics = analysis?.metrics
    ?? (userTickers.length > 0 ? computePortfolioMetrics(userTickers, userShares) : MOCK_PORTFOLIO.metrics);

  const tickers = analysis?.tickers ?? (userTickers.length > 0 ? userTickers : MOCK_PORTFOLIO.tickers);
  const weights = analysis?.weights ?? MOCK_PORTFOLIO.weights;
  const optWeights = optimize ?? MOCK_OPTIMAL_WEIGHTS;

  // Use health_score directly from rawMetrics:
  //  - backend: computed by Python portfolio_health_score() from real historical data
  //  - offline: computed by computePortfolioMetrics() with concentration penalty per ticker combo
  // Both sources already produce portfolio-specific values; no override needed.
  const m = rawMetrics;


  // Build P&L rows from the user's actual holdings when API is unavailable
  type PnlRow = { ticker: string; shares: number; cost_basis: number | null; current_price: number | null; days?: number };
  const pnlRows: PnlRow[] = (() => {
    if (analysis?.pnl) return analysis.pnl;
    const holdings = config?.holdings.filter(h => h.ticker && h.shares) ?? [];
    if (holdings.length === 0) return MOCK_PORTFOLIO.pnl;
    const startMs = config?.startDate ? new Date(config.startDate).getTime() : null;
    const days = startMs ? Math.round((Date.now() - startMs) / 86_400_000) : null;
    return holdings.map(h => ({
      ticker: h.ticker,
      shares: parseFloat(h.shares),
      current_price: MOCK_STOCK_PRICES[h.ticker] ?? null,
      cost_basis: h.cost
        ? parseFloat(h.cost)
        : MOCK_STOCK_PRICES[h.ticker]
          ? parseFloat((MOCK_STOCK_PRICES[h.ticker] * 0.82).toFixed(2))
          : null,
      days,
    }));
  })();

  const tickerStr = tickers.join(' · ');
  const dateRange = config ? `${config.startDate} — ${config.endDate}` : 'JAN 2023 — DEC 2024';

  const handleExportPDF = async () => {
    const { default: html2canvas } = await import('html2canvas');
    const { default: jsPDF } = await import('jspdf');

    const dna = (() => { try { return JSON.parse(localStorage.getItem('arcus-investor-dna') || 'null'); } catch { return null; } })();

    // Always use the freshest data — what was last rendered on the dashboard
    const cachedAnalysis = (() => {
      try { return JSON.parse(localStorage.getItem('arcus-last-analysis') || 'null'); } catch { return null; }
    })();

    // Use live analysis metrics if available, else the cached snapshot, else current `m`
    const pdfMetrics = analysis?.metrics ?? cachedAnalysis?.metrics ?? m;
    const pdfTickers = analysis?.tickers ?? cachedAnalysis?.tickers ?? tickers;
    const pdfWeights = analysis?.weights ?? cachedAnalysis?.weights ?? weights;
    const pdfPnl = analysis?.pnl ?? cachedAnalysis?.pnl ?? pnlRows;

    // Mount report into a visible-but-offscreen container so the browser actually paints it
    const container = document.createElement('div');
    container.style.cssText = 'position:fixed;top:0;left:0;width:794px;z-index:99999;pointer-events:none;transform:translateX(-9999px);';
    document.body.appendChild(container);

    const root = createRoot(container);
    await new Promise<void>(resolve => {
      root.render(
        <PDFReportDocument
          tickers={pdfTickers}
          weights={pdfWeights}
          metrics={pdfMetrics}
          pnlRows={pdfPnl}
          dateRange={dateRange}
          dna={dna}
        />
      );
      // Double RAF + 600ms ensures React commits AND browser paints before capture
      requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 600)));
    });

    const el = container.querySelector('#arcus-pdf-report') as HTMLElement;
    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    });

    root.unmount();
    document.body.removeChild(container);

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const imgH = (canvas.height * pageW) / canvas.width;
    let y = 0;
    while (y < imgH) {
      pdf.addImage(imgData, 'PNG', 0, -y, pageW, imgH);
      y += pageH;
      if (y < imgH) pdf.addPage();
    }
    pdf.save(`arcus-report-${pdfTickers.join('-')}.pdf`);
  };

  return (
    <AppLayout title="Portfolio Analysis">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 arcus-print-root overflow-x-hidden">
        <BackButton to="/dashboard" />

        {/* Top bar */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 sm:mb-8">
          <div>
            <h1 className="font-display font-extrabold text-xl sm:text-2xl text-foreground">Portfolio Analysis</h1>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <span className="font-mono text-xs text-muted-foreground break-all">{tickerStr}</span>
              <span className="font-mono text-[10px] bg-card-elevated text-muted-foreground px-2 py-0.5 rounded-full whitespace-nowrap">{dateRange}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            {isLoading && <span className="font-mono text-[10px] text-primary animate-pulse">LOADING...</span>}
            <span className="hidden md:block font-mono text-[10px] text-muted-foreground">LAST UPDATED: {new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}</span>
            <button data-export-btn onClick={handleExportPDF} className="glass rounded-lg px-3 py-2 font-mono text-xs text-foreground hover:teal-glow transition-all flex items-center gap-2">
              <Download size={14} className="text-primary" /> Export PDF
            </button>
          </div>
        </motion.div>

        {/* Goal Alignment Analysis */}
        {(() => {
          const dna = (() => { try { return JSON.parse(localStorage.getItem('arcus-investor-dna') || 'null'); } catch { return null; } })();
          if (!dna) return null;

          const riskLabel = dna?.risk_tolerance || 'Moderate';
          const targetReturn = dna?.target_return ?? 0.10;
          const targetReturnPct = (targetReturn * 100).toFixed(0);
          const userSectors: string[] = dna?.sectors || [];

          // ── Risk tolerance thresholds ──
          const RISK_THRESHOLDS: Record<string, { maxVol: number; maxBeta: number; maxDD: number }> = {
            'Conservative': { maxVol: 0.12, maxBeta: 0.8, maxDD: -0.10 },
            'Moderate':     { maxVol: 0.18, maxBeta: 1.0, maxDD: -0.18 },
            'Balanced':     { maxVol: 0.24, maxBeta: 1.2, maxDD: -0.25 },
            'Growth':       { maxVol: 0.32, maxBeta: 1.5, maxDD: -0.35 },
            'Aggressive':   { maxVol: 999,  maxBeta: 999, maxDD: -999 },
          };

          const thresholds = RISK_THRESHOLDS[riskLabel] || RISK_THRESHOLDS['Moderate'];
          const actualReturn = m.annualized_return;
          const actualVol = m.volatility;
          const actualBeta = m.beta ?? 1.0;
          const actualDD = m.max_drawdown;

          // ── Return alignment (0-100) ──
          const returnRatio = targetReturn > 0 ? actualReturn / targetReturn : 1;
          const returnScore = Math.min(100, Math.max(0, returnRatio * 100));
          const returnOnTrack = actualReturn >= targetReturn;

          // ── Risk alignment (0-100) ──
          const volOk = riskLabel === 'Aggressive' || actualVol <= thresholds.maxVol;
          const betaOk = riskLabel === 'Aggressive' || actualBeta <= thresholds.maxBeta;
          const ddOk = riskLabel === 'Aggressive' || actualDD >= thresholds.maxDD; // DD is negative
          const riskChecks = [volOk, betaOk, ddOk];
          const riskScore = riskLabel === 'Aggressive' ? 100 : (riskChecks.filter(Boolean).length / 3) * 100;

          // ── Sector alignment (0-100) ──
          // Use API sectors if available, otherwise derive from tickers via local map
          const portfolioSectors: string[] = analysis?.sectors?.length
            ? analysis.sectors.map((s: any) => s.name)
            : [...new Set(tickers.map((t: string) => TICKER_SECTOR_MAP[t]).filter(Boolean))];
          const matchedSectors = userSectors.filter(s => portfolioSectors.some(ps => ps.toLowerCase().includes(s.toLowerCase())));
          const sectorScore = userSectors.length > 0 ? (matchedSectors.length / userSectors.length) * 100 : 100;
          const missingSectors = userSectors.filter(s => !portfolioSectors.some(ps => ps.toLowerCase().includes(s.toLowerCase())));

          // ── Overall Goal Score ──
          const goalScore = Math.round(returnScore * 0.4 + riskScore * 0.3 + sectorScore * 0.3);

          const scoreColor = goalScore >= 70 ? 'text-signal-green' : goalScore >= 40 ? 'text-signal-amber' : 'text-signal-red';
          const scoreBg = goalScore >= 70 ? 'bg-signal-green/10' : goalScore >= 40 ? 'bg-signal-amber/10' : 'bg-signal-red/10';
          const scoreLabel = goalScore >= 70 ? 'Well Aligned' : goalScore >= 40 ? 'Needs Attention' : 'Misaligned';

          const statusIcon = (ok: boolean) => ok
            ? <CheckCircle size={14} className="text-signal-green flex-shrink-0" />
            : <AlertTriangle size={14} className="text-signal-amber flex-shrink-0" />;

          return (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-5 mb-6">
              {/* Header with Goal Score */}
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <Shield size={16} className="text-primary" />
                  <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>GOAL ALIGNMENT</span>
                </div>
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${scoreBg}`}>
                  <span className={`font-mono text-xl font-bold ${scoreColor}`}>{goalScore}</span>
                  <span className={`font-mono text-[9px] uppercase tracking-wider ${scoreColor}`}>{scoreLabel}</span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Target Return Card */}
                <div className="glass-elevated rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp size={14} className="text-primary" />
                    <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Target Return</span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    {statusIcon(returnOnTrack)}
                    <span className={`font-mono text-sm font-bold ${returnOnTrack ? 'text-signal-green' : 'text-signal-amber'}`}>
                      {returnOnTrack ? 'On Track' : 'Below Target'}
                    </span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <div className="flex justify-between">
                      <span className="text-[11px] text-muted-foreground">Your Target</span>
                      <span className="font-mono text-xs font-bold text-foreground">{targetReturnPct}% / yr</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[11px] text-muted-foreground">Actual Return</span>
                      <span className={`font-mono text-xs font-bold ${returnOnTrack ? 'text-signal-green' : 'text-signal-amber'}`}>{(actualReturn * 100).toFixed(1)}% / yr</span>
                    </div>
                    {!returnOnTrack && (
                      <div className="flex justify-between border-t border-border/30 pt-2">
                        <span className="text-[11px] text-muted-foreground">Gap</span>
                        <span className="font-mono text-xs text-signal-red">-{((targetReturn - actualReturn) * 100).toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                  {/* Mini bar */}
                  <div className="mt-3 h-1.5 bg-border rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all ${returnOnTrack ? 'bg-signal-green' : 'bg-signal-amber'}`} style={{ width: `${Math.min(100, returnScore)}%` }} />
                  </div>
                </div>

                {/* Risk Tolerance Card */}
                <div className="glass-elevated rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Activity size={14} className="text-primary" />
                    <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Risk Tolerance · {riskLabel}</span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    {statusIcon(riskScore >= 67)}
                    <span className={`font-mono text-sm font-bold ${riskScore >= 67 ? 'text-signal-green' : riskScore >= 33 ? 'text-signal-amber' : 'text-signal-red'}`}>
                      {riskScore >= 67 ? 'Within Limits' : riskScore >= 33 ? 'Partially Exceeded' : 'Exceeded'}
                    </span>
                  </div>
                  <div className="space-y-2 mt-3">
                    {riskLabel !== 'Aggressive' ? (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-muted-foreground">Volatility</span>
                          <div className="flex items-center gap-1.5">
                            <span className={`font-mono text-[10px] ${volOk ? 'text-signal-green' : 'text-signal-red'}`}>{(actualVol * 100).toFixed(1)}%</span>
                            <span className="text-[9px] text-muted-foreground/60">/ {(thresholds.maxVol * 100)}%</span>
                            {volOk ? <CheckCircle size={10} className="text-signal-green" /> : <AlertTriangle size={10} className="text-signal-red" />}
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-muted-foreground">Beta</span>
                          <div className="flex items-center gap-1.5">
                            <span className={`font-mono text-[10px] ${betaOk ? 'text-signal-green' : 'text-signal-red'}`}>{actualBeta.toFixed(2)}</span>
                            <span className="text-[9px] text-muted-foreground/60">/ {thresholds.maxBeta}</span>
                            {betaOk ? <CheckCircle size={10} className="text-signal-green" /> : <AlertTriangle size={10} className="text-signal-red" />}
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-muted-foreground">Max Drawdown</span>
                          <div className="flex items-center gap-1.5">
                            <span className={`font-mono text-[10px] ${ddOk ? 'text-signal-green' : 'text-signal-red'}`}>{(actualDD * 100).toFixed(1)}%</span>
                            <span className="text-[9px] text-muted-foreground/60">/ {(thresholds.maxDD * 100)}%</span>
                            {ddOk ? <CheckCircle size={10} className="text-signal-green" /> : <AlertTriangle size={10} className="text-signal-red" />}
                          </div>
                        </div>
                      </>
                    ) : (
                      <p className="text-[11px] text-muted-foreground">Aggressive profile — no risk limits applied.</p>
                    )}
                  </div>
                </div>

                {/* Sector Alignment Card */}
                <div className="glass-elevated rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <BarChart2 size={14} className="text-primary" />
                    <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Sector Alignment</span>
                  </div>
                  {userSectors.length > 0 ? (
                    <>
                      <div className="flex items-center gap-2 mb-2">
                        {statusIcon(sectorScore >= 50)}
                        <span className={`font-mono text-sm font-bold ${sectorScore >= 75 ? 'text-signal-green' : sectorScore >= 50 ? 'text-signal-amber' : 'text-signal-red'}`}>
                          {matchedSectors.length}/{userSectors.length} Sectors Covered
                        </span>
                      </div>
                      <div className="space-y-1.5 mt-3">
                        {userSectors.map(s => {
                          const matched = portfolioSectors.some(ps => ps.toLowerCase().includes(s.toLowerCase()));
                          return (
                            <div key={s} className="flex items-center gap-2">
                              {matched ? <CheckCircle size={10} className="text-signal-green" /> : <AlertTriangle size={10} className="text-signal-amber" />}
                              <span className={`font-mono text-[10px] ${matched ? 'text-foreground' : 'text-muted-foreground'}`}>{s}</span>
                            </div>
                          );
                        })}
                      </div>
                      {missingSectors.length > 0 && (
                        <p className="text-[10px] text-signal-amber mt-3 border-t border-border/30 pt-2">
                          Consider adding exposure to {missingSectors.join(', ')}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-[11px] text-muted-foreground">No sector preferences set during onboarding.</p>
                  )}
                </div>
              </div>

              {/* Actionable Summary */}
              {goalScore < 70 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="mt-4 p-3 rounded-lg bg-card-elevated border border-border/50">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">RECOMMENDATIONS</span>
                  <ul className="mt-2 space-y-1">
                    {!returnOnTrack && (
                      <li className="text-[12px] text-foreground/80 flex items-start gap-2">
                        <ChevronRight size={12} className="text-primary mt-0.5 flex-shrink-0" />
                        Portfolio returns ({(actualReturn * 100).toFixed(1)}%) are below your {targetReturnPct}% target. Consider higher-growth assets or extending your time horizon.
                      </li>
                    )}
                    {!volOk && riskLabel !== 'Aggressive' && (
                      <li className="text-[12px] text-foreground/80 flex items-start gap-2">
                        <ChevronRight size={12} className="text-primary mt-0.5 flex-shrink-0" />
                        Volatility ({(actualVol * 100).toFixed(1)}%) exceeds your {riskLabel} threshold ({(thresholds.maxVol * 100)}%). Diversify with lower-volatility holdings.
                      </li>
                    )}
                    {!betaOk && riskLabel !== 'Aggressive' && (
                      <li className="text-[12px] text-foreground/80 flex items-start gap-2">
                        <ChevronRight size={12} className="text-primary mt-0.5 flex-shrink-0" />
                        Beta ({actualBeta.toFixed(2)}) exceeds the {thresholds.maxBeta} limit for {riskLabel} investors. Add defensive positions or index funds.
                      </li>
                    )}
                    {!ddOk && riskLabel !== 'Aggressive' && (
                      <li className="text-[12px] text-foreground/80 flex items-start gap-2">
                        <ChevronRight size={12} className="text-primary mt-0.5 flex-shrink-0" />
                        Max drawdown ({(actualDD * 100).toFixed(1)}%) is worse than your {(thresholds.maxDD * 100)}% comfort zone. Consider stop-loss strategies.
                      </li>
                    )}
                    {missingSectors.length > 0 && (
                      <li className="text-[12px] text-foreground/80 flex items-start gap-2">
                        <ChevronRight size={12} className="text-primary mt-0.5 flex-shrink-0" />
                        Missing exposure to {missingSectors.join(', ')}. Add sector ETFs or individual stocks to align with your preferences.
                      </li>
                    )}
                  </ul>
                </motion.div>
              )}
            </motion.div>
          );
        })()}

        {/* Plain English Summary Banner */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="glass rounded-xl p-5 mb-6 border-l-[3px] border-primary">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">YOUR PORTFOLIO</span>
                <span className="text-muted-foreground">·</span>
                <span className="font-mono text-[10px] uppercase tracking-wider text-primary">HEALTH SCORE {m.health_score}</span>
              </div>
              <p className="text-[15px] font-medium text-foreground leading-snug">
                Solid performance with elevated risk. Your portfolio is doing well — consider diversifying for stability.
              </p>
              <p className="text-[13px] text-secondary mt-2">
                In the analysis period you made {(m.annualized_return * 100).toFixed(1)}% but your portfolio can swing hard — on a bad day you could lose around {Math.abs(m.var_95 * 100).toFixed(1)}%.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-mono text-[11px] text-signal-green">↑ +{(m.annualized_return * 100).toFixed(1)}% return</span>
              <span className="font-mono text-[11px] text-primary">Sharpe {m.sharpe.toFixed(2)}</span>
              <span className="font-mono text-[11px] text-signal-red">▼ {(m.max_drawdown * 100).toFixed(1)}% drop</span>
            </div>
          </div>
        </motion.div>

        {/* Metric Cards Row 1 */}
        <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-[120px] rounded-xl shimmer" />)
          ) : (
            <>
              <MetricCard icon={Activity} label="SHARPE RATIO" value={m.sharpe} format={(n) => n.toFixed(2)} change={0.12} sparklineData={MOCK_SPARKLINES.sharpe} delay={0.15} chatQuestion={`My Sharpe ratio is ${m.sharpe.toFixed(2)}. Explain what this means in simple terms and whether it's good or bad for my portfolio.`} />
              <MetricCard icon={Activity} label="SORTINO RATIO" value={m.sortino} format={(n) => n.toFixed(2)} change={0.18} sparklineData={MOCK_SPARKLINES.sortino} delay={0.2} chatQuestion={`My Sortino ratio is ${m.sortino.toFixed(2)}. What does this tell me about my downside risk?`} />
              <MetricCard icon={TrendingUp} label="ALPHA" value={m.alpha * 100} format={(n) => `${n.toFixed(1)}%`} change={0.5} changeLabel="+0.5%" sparklineData={MOCK_SPARKLINES.alpha} delay={0.25} chatQuestion={`My portfolio alpha is ${(m.alpha * 100).toFixed(1)}%. Explain what alpha means and whether I'm outperforming.`} />
              <MetricCard icon={GitBranch} label="INFO RATIO" value={m.information_ratio} format={(n) => n.toFixed(2)} change={0.04} delay={0.3} chatQuestion={`My information ratio is ${m.information_ratio.toFixed(2)}. What does this tell me about my portfolio performance?`} />
            </>
          )}
        </div>

        {/* Health Score */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass rounded-xl p-6 mb-6 cursor-pointer" onClick={() => askAI(`My portfolio health score is ${m.health_score}/100. Break down what's driving this score.`)}>
          <HealthGauge score={m.health_score} />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
            {[
              { label: 'Diversification', value: '72%', color: 'text-primary' },
              { label: 'Concentration', value: '34%', color: 'text-signal-amber' },
              { label: 'Volatility', value: `${(m.volatility * 100).toFixed(1)}%`, color: 'text-foreground' },
              { label: 'Liquidity', value: 'High', color: 'text-signal-green' },
            ].map((s) => (
              <div key={s.label} className="glass-elevated rounded-lg p-3 text-center">
                <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>{s.label}</span>
                <div className={`font-mono text-lg font-bold mt-1 ${s.color}`}>{s.value}</div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Full Report Card */}
        <FullReport />

        {/* Metric Cards Row 2 */}
        <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-[120px] rounded-xl shimmer" />)
          ) : (
            <>
              <MetricCard icon={Shield} label="VAR 95%" value={m.var_95 * 100} format={(n) => `${n.toFixed(1)}%`} change={-0.3} changeLabel="±0.3%" sparklineData={MOCK_SPARKLINES.var_95} delay={0.35} chatQuestion={`My VaR at 95% is ${(m.var_95 * 100).toFixed(1)}%. Explain Value at Risk in simple language — what could I actually lose?`} />
              <MetricCard icon={Shield} label="CVAR 95%" value={m.cvar_95 * 100} format={(n) => `${n.toFixed(1)}%`} change={-0.2} sparklineData={MOCK_SPARKLINES.cvar_95} delay={0.4} chatQuestion={`My CVaR is ${(m.cvar_95 * 100).toFixed(1)}%. What is Expected Shortfall and how does it differ from VaR?`} />
              <MetricCard icon={TrendingDown} label="MAX DRAWDOWN" value={m.max_drawdown * 100} format={(n) => `${n.toFixed(1)}%`} change={-1.2} sparklineData={MOCK_SPARKLINES.max_drawdown} delay={0.45} chatQuestion={`My maximum drawdown is ${(m.max_drawdown * 100).toFixed(1)}%. What does this mean and should I be worried?`} />
              <MetricCard icon={Activity} label="BETA" value={m.beta} format={(n) => n.toFixed(2)} change={-0.03} sparklineData={MOCK_SPARKLINES.beta} delay={0.5} chatQuestion={`My portfolio Beta is ${m.beta.toFixed(2)}. Explain Beta in plain English — am I taking too much market risk?`} />
            </>
          )}
        </div>

        {/* Metric Cards Row 3 */}
        <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          <MetricCard icon={BarChart2} label="CALMAR RATIO" value={m.calmar} format={(n) => n.toFixed(2)} change={0.08} delay={0.55} chatQuestion={`My Calmar ratio is ${m.calmar.toFixed(2)}. What does this tell me about return vs drawdown risk?`} />
          <MetricCard icon={TrendingUp} label="ANN. RETURN" value={m.annualized_return * 100} format={(n) => `${n.toFixed(1)}%`} change={2.1} changeLabel="+2.1%" sparklineData={MOCK_SPARKLINES.annualized_return} delay={0.6} chatQuestion={`My annualized return is ${(m.annualized_return * 100).toFixed(1)}%. How does this compare to the market?`} />
          <MetricCard icon={Activity} label="VOLATILITY" value={m.volatility * 100} format={(n) => `${n.toFixed(1)}%`} change={-0.8} changeLabel="-0.8%" delay={0.65} chatQuestion={`My portfolio volatility is ${(m.volatility * 100).toFixed(1)}%. What does this mean for my risk?`} />
          <MetricCard icon={BarChart2} label="WTD AVG P/E" value={m.weighted_pe} format={(n) => n.toFixed(1)} delay={0.7} chatQuestion={`My weighted average P/E is ${m.weighted_pe?.toFixed(1) ?? '—'}. Is my portfolio overvalued?`} />
        </div>

        {/* P&L Table */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass rounded-xl p-4 sm:p-5 mb-8 overflow-x-auto">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={16} className="text-primary" />
            <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>PROFIT & LOSS</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {['Ticker', 'Qty', 'Cost', 'Price', 'P&L $', 'P&L %'].map((h) => (
                  <th key={h} className="text-left py-2 pr-2 label-mono whitespace-nowrap" style={{ color: 'hsl(214 10% 57%)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pnlRows.map((row) => {
                const hasPnl = row.current_price != null && row.cost_basis != null;
                const pnlDollar = hasPnl ? (row.current_price - row.cost_basis) * row.shares : null;
                const pnlPct = hasPnl ? ((row.current_price - row.cost_basis) / row.cost_basis) * 100 : null;
                const positive = pnlDollar != null && pnlDollar >= 0;
                return (
                  <tr key={row.ticker} className="border-b border-border/30 hover:bg-card-elevated/50 transition-colors">
                    <td className="py-2.5 pr-3 font-mono text-xs font-medium text-foreground whitespace-nowrap">{row.ticker}</td>
                    <td className="py-2.5 pr-3 font-mono text-xs text-foreground whitespace-nowrap">{row.shares}</td>
                    <td className="py-2.5 pr-3 font-mono text-xs text-muted-foreground whitespace-nowrap">{row.cost_basis != null ? `$${row.cost_basis.toFixed(2)}` : '—'}</td>
                    <td className="py-2.5 pr-3 font-mono text-xs text-foreground whitespace-nowrap">{row.current_price != null ? `$${row.current_price.toFixed(2)}` : '—'}</td>
                    <td className={`py-2.5 pr-3 font-mono text-xs font-medium whitespace-nowrap ${pnlDollar != null ? (positive ? 'text-signal-green' : 'text-signal-red') : 'text-muted-foreground'}`}>
                      {pnlDollar != null ? `${positive ? '+' : ''}$${pnlDollar.toFixed(2)}` : '—'}
                    </td>
                    <td className={`py-2.5 pr-2 font-mono text-xs whitespace-nowrap ${pnlPct != null ? (positive ? 'text-signal-green' : 'text-signal-red') : 'text-muted-foreground'}`}>
                      {pnlPct != null ? `${positive ? '+' : ''}${pnlPct.toFixed(1)}%` : '—'}
                    </td>
                  </tr>
                );
              })}
              <tr className="border-t-2 border-border">
                <td className="py-2.5 pr-3 font-mono text-xs font-bold text-foreground">TOTAL</td>
                <td colSpan={3} />
                <td className="py-2.5 pr-2 font-mono text-xs font-bold text-signal-green whitespace-nowrap">
                  {(() => {
                    const total = pnlRows.reduce((a, r) => r.current_price != null && r.cost_basis != null ? a + (r.current_price - r.cost_basis) * r.shares : a, 0);
                    return `${total >= 0 ? '+' : ''}$${total.toFixed(2)}`;
                  })()}
                </td>
                <td colSpan={1} />
              </tr>
            </tbody>
          </table>
        </motion.div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div>
            <SectionHeader label="PERFORMANCE" chatQuestion="Explain my portfolio performance chart — what trends do you see and what should I watch?" />
            <PerformanceChart data={analysis?.performance} />
          </div>
          <div>
            <SectionHeader label="DRAWDOWN" chatQuestion="Explain what my drawdown chart means and whether my worst periods are concerning." />
            <DrawdownChart data={analysis?.drawdown} />
          </div>
        </div>

        {/* Past vs Future */}
        <PastVsFuture />

        {/* Risk Intelligence */}
        <SectionHeader label="RISK INTELLIGENCE" chatQuestion="Give me an overview of my portfolio's risk intelligence — risk attribution, correlation, and sector concentration." />
        <div className="flex flex-col gap-4 mb-6">
          <RiskAttribution data={analysis?.risk_attribution} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <CorrelationHeatmap data={analysis?.correlation} />
            <SectorDonut data={analysis?.sectors} />
          </div>
        </div>

        {/* Efficient Frontier + Optimal Weights */}
        <SectionHeader label="EFFICIENT FRONTIER & OPTIMIZATION" chatQuestion="Show me where my portfolio sits on the efficient frontier and explain what the efficient frontier means." />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <EfficientFrontier data={frontier} />
          <div className="glass rounded-xl p-5">
            <span className="label-mono mb-4 block" style={{ color: 'hsl(214 10% 57%)' }}>OPTIMAL WEIGHTS</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {Object.values(optWeights).map((strat: any) => (
                <div key={strat.label} className="glass-elevated rounded-lg p-3 relative">
                  {strat.recommended && (
                    <span className="absolute -top-2 right-2 bg-primary text-primary-foreground font-mono text-[8px] uppercase px-2 py-0.5 rounded-full">RECOMMENDED</span>
                  )}
                  <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{strat.label}</span>
                  <div className="font-mono text-lg font-bold text-foreground mt-1">{strat.sharpe?.toFixed(2) ?? '—'}</div>
                  <div className="space-y-1.5 mt-3">
                    {strat.weights?.map((w: any) => (
                      <div key={w.ticker} className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-muted-foreground w-12">{w.ticker}</span>
                        <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                          <div className="h-full bg-primary rounded-full" style={{ width: `${w.weight * 100}%` }} />
                        </div>
                        <span className="font-mono text-[10px] text-foreground w-8 text-right">{(w.weight * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sandbox Preview */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>STRATEGY SANDBOX</span>
            <Link to="/dashboard/mock" className="text-primary font-mono text-xs flex items-center gap-1 hover:text-accent-bright transition-colors">
              Open Full Sandbox <ChevronRight size={12} />
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {['CURRENT', 'MOCK A'].map((label, i) => (
              <div key={label} className="glass-elevated rounded-lg p-4">
                <span className={`font-mono text-[10px] uppercase tracking-wider ${i === 0 ? 'text-muted-foreground' : 'text-primary'}`}>{label}</span>
                <div className="space-y-2 mt-3">
                  <div className="flex justify-between"><span className="text-xs text-muted-foreground">Health Score</span><span className="font-mono text-sm text-foreground">{i === 0 ? m.health_score : Math.min(100, m.health_score + 4)}</span></div>
                  <div className="flex justify-between"><span className="text-xs text-muted-foreground">Sharpe</span><span className="font-mono text-sm text-foreground">{i === 0 ? m.sharpe.toFixed(2) : (m.sharpe + 0.17).toFixed(2)}</span></div>
                  <div className="flex justify-between"><span className="text-xs text-muted-foreground">CVaR</span><span className="font-mono text-sm text-foreground">{i === 0 ? `${(m.cvar_95 * 100).toFixed(1)}%` : `${(m.cvar_95 * 100 + 0.9).toFixed(1)}%`}</span></div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Monte Carlo + Stress Testing */}
        <SectionHeader label="SIMULATION & STRESS TESTING" chatQuestion="Explain my Monte Carlo simulation results and stress test outcomes — what are the key takeaways?" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <MonteCarloChart data={monteCarlo} />
          <StressTestGrid data={stressTests} />
        </div>
      </div>
    </AppLayout>
  );
};

export default Results;
