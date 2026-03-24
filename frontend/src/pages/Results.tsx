import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, TrendingUp, TrendingDown, Shield, BarChart2, AlertTriangle, Zap, GitBranch, Download, ChevronRight, CheckCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import AppLayout from '@/components/AppLayout';
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
import { MOCK_PORTFOLIO, MOCK_SPARKLINES, MOCK_OPTIMAL_WEIGHTS } from '@/lib/mock-data';
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
  const m = analysis?.metrics ?? MOCK_PORTFOLIO.metrics;
  const tickers = analysis?.tickers ?? MOCK_PORTFOLIO.tickers;
  const weights = analysis?.weights ?? MOCK_PORTFOLIO.weights;
  const optWeights = optimize ?? MOCK_OPTIMAL_WEIGHTS;

  const tickerStr = tickers.join(' · ');
  const dateRange = config ? `${config.startDate} — ${config.endDate}` : 'JAN 2023 — DEC 2024';

  return (
    <AppLayout title="Portfolio Analysis">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <BackButton to="/dashboard" />

        {/* Top bar */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="font-display font-extrabold text-2xl text-foreground">Portfolio Analysis</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="font-mono text-xs text-muted-foreground">{tickerStr}</span>
              <span className="font-mono text-[10px] bg-card-elevated text-muted-foreground px-2 py-0.5 rounded-full">{dateRange}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isLoading && <span className="font-mono text-[10px] text-primary animate-pulse">LOADING...</span>}
            <span className="font-mono text-[10px] text-muted-foreground">LAST UPDATED: {new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}</span>
            <button className="glass rounded-lg px-4 py-2 font-mono text-xs text-foreground hover:teal-glow transition-all flex items-center gap-2">
              <Download size={14} className="text-primary" /> Export PDF
            </button>
          </div>
        </motion.div>

        {/* Dynamic Profile Conflict + Investor DNA */}
        {(() => {
          const dna = (() => { try { return JSON.parse(localStorage.getItem('arcus-investor-dna') || 'null'); } catch { return null; } })();
          const riskLabel = dna?.risk_tolerance || 'Moderate';
          const targetReturn = dna?.target_return ? `${(dna.target_return * 100).toFixed(0)}%` : '10%';
          const sectors: string[] = dna?.sectors || [];
          const isConflict = ['Conservative', 'Moderate'].includes(riskLabel) && (m.beta ?? 0) > 1.2;
          return (
            <>
              {isConflict && (
                <motion.div initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} className="glass rounded-xl p-4 mb-4 border-l-4 border-signal-amber flex items-start gap-3">
                  <AlertTriangle size={16} className="text-signal-amber mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-signal-amber">PROFILE CONFLICT</span>
                    <p className="text-sm text-foreground/80 mt-1">You indicated <span className="text-foreground font-medium">{riskLabel}</span> risk, but your Beta of <span className="font-mono text-foreground">{m.beta?.toFixed(2) ?? '—'}</span> suggests Growth/Aggressive exposure.</p>
                  </div>
                </motion.div>
              )}
              {dna && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-4 mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Shield size={14} className="text-primary" />
                    <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>INVESTOR DNA</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div className="glass-elevated rounded-lg p-3">
                      <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Risk Profile</span>
                      <div className="font-mono text-sm font-bold text-foreground mt-1">{riskLabel}</div>
                    </div>
                    <div className="glass-elevated rounded-lg p-3">
                      <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Target Return</span>
                      <div className="font-mono text-sm font-bold text-primary mt-1">{targetReturn} / yr</div>
                    </div>
                    {sectors.length > 0 && (
                      <div className="glass-elevated rounded-lg p-3 col-span-2 sm:col-span-1">
                        <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Preferred Sectors</span>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {sectors.map((s: string) => (
                            <span key={s} className="font-mono text-[9px] bg-primary/10 text-primary px-1.5 py-0.5 rounded">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </>
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
            <div className="flex items-center gap-3 flex-shrink-0">
              <span className="font-mono text-[11px] text-signal-green">↑ +{(m.annualized_return * 100).toFixed(1)}% return</span>
              <span className="text-primary text-xs">·</span>
              <span className="font-mono text-[11px] text-primary">Sharpe {m.sharpe.toFixed(2)}</span>
              <span className="text-primary text-xs">·</span>
              <span className="font-mono text-[11px] text-signal-red">▼ {(m.max_drawdown * 100).toFixed(1)}% worst drop</span>
            </div>
          </div>
        </motion.div>

        {/* Metric Cards Row 1 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
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
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
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
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
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
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          <MetricCard icon={BarChart2} label="CALMAR RATIO" value={m.calmar} format={(n) => n.toFixed(2)} change={0.08} delay={0.55} chatQuestion={`My Calmar ratio is ${m.calmar.toFixed(2)}. What does this tell me about return vs drawdown risk?`} />
          <MetricCard icon={TrendingUp} label="ANN. RETURN" value={m.annualized_return * 100} format={(n) => `${n.toFixed(1)}%`} change={2.1} changeLabel="+2.1%" sparklineData={MOCK_SPARKLINES.annualized_return} delay={0.6} chatQuestion={`My annualized return is ${(m.annualized_return * 100).toFixed(1)}%. How does this compare to the market?`} />
          <MetricCard icon={Activity} label="VOLATILITY" value={m.volatility * 100} format={(n) => `${n.toFixed(1)}%`} change={-0.8} changeLabel="-0.8%" delay={0.65} chatQuestion={`My portfolio volatility is ${(m.volatility * 100).toFixed(1)}%. What does this mean for my risk?`} />
          <MetricCard icon={BarChart2} label="WTD AVG P/E" value={m.weighted_pe} format={(n) => n.toFixed(1)} delay={0.7} chatQuestion={`My weighted average P/E is ${m.weighted_pe?.toFixed(1) ?? '—'}. Is my portfolio overvalued?`} />
        </div>

        {/* P&L Table */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass rounded-xl p-5 mb-8 overflow-x-auto">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={16} className="text-primary" />
            <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>PROFIT & LOSS</span>
          </div>
          <table className="w-full min-w-[600px]">
            <thead>
              <tr className="border-b border-border">
                {['Ticker', 'Shares', 'Cost Basis', 'Current', 'P&L ($)', 'P&L (%)', 'Days'].map((h) => (
                  <th key={h} className="text-left py-2 label-mono" style={{ color: 'hsl(214 10% 57%)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_PORTFOLIO.pnl.map((row) => {
                const pnlDollar = (row.current_price - row.cost_basis) * row.shares;
                const pnlPct = ((row.current_price - row.cost_basis) / row.cost_basis) * 100;
                const positive = pnlDollar >= 0;
                return (
                  <tr key={row.ticker} className="border-b border-border/30 hover:bg-card-elevated/50 transition-colors">
                    <td className="py-3 font-mono text-sm font-medium text-foreground">{row.ticker}</td>
                    <td className="py-3 font-mono text-sm text-foreground">{row.shares}</td>
                    <td className="py-3 font-mono text-sm text-muted-foreground">${row.cost_basis.toFixed(2)}</td>
                    <td className="py-3 font-mono text-sm text-foreground">${row.current_price.toFixed(2)}</td>
                    <td className={`py-3 font-mono text-sm font-medium ${positive ? 'text-signal-green' : 'text-signal-red'}`}>{positive ? '+' : ''}${pnlDollar.toFixed(2)}</td>
                    <td className={`py-3 font-mono text-sm ${positive ? 'text-signal-green' : 'text-signal-red'}`}>{positive ? '+' : ''}{pnlPct.toFixed(1)}%</td>
                    <td className="py-3 font-mono text-sm text-muted-foreground">{row.days}</td>
                  </tr>
                );
              })}
              <tr className="border-t-2 border-border">
                <td className="py-3 font-mono text-sm font-bold text-foreground">TOTAL</td>
                <td colSpan={3} />
                <td className="py-3 font-mono text-sm font-bold text-signal-green">
                  +${MOCK_PORTFOLIO.pnl.reduce((a, r) => a + (r.current_price - r.cost_basis) * r.shares, 0).toFixed(2)}
                </td>
                <td colSpan={2} />
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <RiskAttribution data={analysis?.risk_attribution} />
          <CorrelationHeatmap data={analysis?.correlation} />
          <SectorDonut data={analysis?.sectors} />
        </div>

        {/* Efficient Frontier + Optimal Weights */}
        <SectionHeader label="EFFICIENT FRONTIER & OPTIMIZATION" chatQuestion="Show me where my portfolio sits on the efficient frontier and explain what the efficient frontier means." />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <EfficientFrontier data={frontier} />
          <div className="glass rounded-xl p-5">
            <span className="label-mono mb-4 block" style={{ color: 'hsl(214 10% 57%)' }}>OPTIMAL WEIGHTS</span>
            <div className="grid grid-cols-3 gap-3">
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
