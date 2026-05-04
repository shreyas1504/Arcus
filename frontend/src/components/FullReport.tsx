import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, ChevronDown, ChevronUp, CheckCircle, AlertTriangle, Zap, SendHorizontal, MessageSquare } from 'lucide-react';
import { MOCK_AI_RECOMMENDATIONS } from '@/lib/mock-data';
import { useNavigate } from 'react-router-dom';
import { openArcusChat } from '@/lib/chat-launcher';

const tabs = ['Summary', 'Methodology', 'AI Analysis', 'Recommendations'] as const;
type Tab = typeof tabs[number];

const glossary = [
  { term: 'Sharpe Ratio', def: 'How much return you get per unit of risk. Higher is better.' },
  { term: 'VaR', def: 'The maximum you could lose on a bad day (95% confidence).' },
  { term: 'CVaR', def: 'The average loss on your very worst days.' },
  { term: 'Beta', def: 'How much your portfolio moves vs the market. 1.0 = same as market.' },
  { term: 'Max Drawdown', def: "The biggest peak-to-trough drop you've experienced." },
  { term: 'Health Score', def: "Arcus's overall rating of your portfolio. Out of 100." },
];

const recCategories = ['RISK', 'ALLOCATION', 'VALUATION', 'PROJECTION'];

export interface FullReportProps {
  metrics: {
    sharpe?: number;
    var_95?: number;
    cvar_95?: number;
    beta?: number;
    max_drawdown?: number;
    health_score?: number;
    healthScore?: number;
  };
  tickers?: string[];
}

const FullReport = ({ metrics: m, tickers = [] }: FullReportProps) => {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('Summary');
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const [openMethodology, setOpenMethodology] = useState<string | null>(null);
  const [followUp, setFollowUp] = useState('');
  const navigate = useNavigate();

  const sendToChat = (message: string) => {
    openArcusChat(message);
  };

  const methodologyItems = [
    { metric: 'Sharpe Ratio', formula: '(Portfolio Return − Risk-Free Rate) / Portfolio Volatility', plain: 'For every unit of risk you take, this is how much return you get.', result: `${m.sharpe?.toFixed(2)} — above average (benchmark: ~1.0)` },
    { metric: 'VaR (Value at Risk)', formula: 'Historical simulation at 95th percentile of daily return distribution', plain: "On 95% of days, you won't lose more than this amount.", result: `${(m.var_95 * 100).toFixed(1)}% — meaning -$3,200 on a $100K portfolio` },
    { metric: 'CVaR (Expected Shortfall)', formula: 'Average of all returns below the VaR threshold', plain: "On your very worst days, this is what you'd typically lose.", result: `${(m.cvar_95 * 100).toFixed(1)}% — more conservative metric than VaR` },
    { metric: 'Beta', formula: 'Covariance(portfolio, benchmark) / Variance(benchmark)', plain: 'How closely your portfolio moves with the S&P 500.', result: `${m.beta?.toFixed(2)} — your portfolio moves close to the market` },
    { metric: 'Max Drawdown', formula: '(Trough value − Peak value) / Peak value', plain: 'The biggest drop from a peak before recovery.', result: `${(m.max_drawdown * 100).toFixed(1)}%` },
    { metric: 'Health Score', formula: 'Weighted composite of Sharpe, Drawdown, Diversification, VaR', plain: "Arcus's overall rating of your portfolio quality.", result: `${Math.round(m.health_score || m.healthScore || 0)}/100` },
    { metric: 'Monte Carlo Simulation', formula: 'Geometric Brownian Motion — simulates thousands of return paths', plain: 'We run 1,000 versions of the future using your historical returns and volatility, then show you the range of likely outcomes.', result: '' },
    { metric: 'Efficient Frontier', formula: 'Modern Portfolio Theory — Markowitz mean-variance optimization', plain: 'The curve showing every possible mix of your assets that gives the best return for a given level of risk.', result: '' },
    { metric: 'Correlation Matrix', formula: 'Pearson correlation of daily returns between each pair of assets', plain: 'Shows which of your stocks move together. High correlation means less real diversification than you think.', result: '' },
  ];

  const topTicker = tickers.length > 0 ? tickers[0] : 'your largest holding';
  const secondTicker = tickers.length > 1 ? tickers[1] : 'other assets';

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full glass rounded-xl p-4 border-l-[3px] border-primary flex items-center justify-between card-hover-glow transition-all"
      >
        <div className="flex items-center gap-3">
          <FileText size={20} className="text-primary" />
          <div className="text-left">
            <span className="font-display font-bold text-base text-foreground block">Full Report</span>
            <span className="text-[13px] text-muted-foreground">Detailed methodology, AI analysis, and plain-English summary</span>
          </div>
        </div>
        {expanded ? <ChevronUp size={18} className="text-primary" /> : <ChevronDown size={18} className="text-primary" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            className="overflow-hidden"
          >
            <div className="glass rounded-b-xl border-t-0 p-5 -mt-3 pt-6">
              {/* Tab bar */}
              <div className="flex gap-4 border-b border-border pb-3 mb-5">
                {tabs.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`font-mono text-xs uppercase tracking-wider pb-2 transition-all relative ${activeTab === tab ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}
                  >
                    {tab}
                    {activeTab === tab && <motion.div layoutId="report-tab" className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary rounded-full" />}
                  </button>
                ))}
              </div>

              {/* SUMMARY TAB */}
              {activeTab === 'Summary' && (
                <div className="space-y-4">
                  <p className="font-display font-bold text-lg text-foreground leading-snug">
                    Your portfolio is moderately healthy — strong returns, but you're taking more risk than most investors at your level.
                  </p>

                  <div className="rounded-lg p-4" style={{ background: 'rgba(63,182,139,0.08)', border: '1px solid rgba(63,182,139,0.2)' }}>
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle size={16} className="text-signal-green" />
                      <span className="text-sm font-semibold text-signal-green">What's working</span>
                    </div>
                    <ul className="space-y-1.5 text-sm text-foreground/85 leading-relaxed">
                      <li>• Your Sharpe ratio of {m.sharpe.toFixed(2)} means you're getting good returns for the risk you're taking</li>
                      <li>• MSFT and AAPL are your most stable holdings — they're pulling their weight</li>
                      <li>• You're well diversified across 5 sectors which reduces your overall risk</li>
                    </ul>
                  </div>

                  <div className="rounded-lg p-4" style={{ background: 'rgba(240,164,79,0.08)', border: '1px solid rgba(240,164,79,0.2)' }}>
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle size={16} className="text-signal-amber" />
                      <span className="text-sm font-semibold text-signal-amber">What to watch</span>
                    </div>
                    <ul className="space-y-1.5 text-sm text-foreground/85 leading-relaxed">
                      <li>• {topTicker} makes up a significant portion of your total risk — if it drops, your whole portfolio feels it</li>
                      <li>• Your portfolio has a Beta of {m.beta?.toFixed(2)} — it moves with the market</li>
                      <li>• In the worst 5% of days, you could lose {(m.cvar_95 * 100).toFixed(1)}% — that's your CVaR</li>
                    </ul>
                  </div>

                  <div className="rounded-lg p-4" style={{ background: 'rgba(56,189,164,0.08)', border: '1px solid rgba(56,189,164,0.2)' }}>
                    <div className="flex items-center gap-2 mb-2">
                      <Zap size={16} className="text-primary" />
                      <span className="text-sm font-semibold text-primary">Bottom line</span>
                    </div>
                    <p className="text-sm text-foreground/85 leading-relaxed">
                      Overall you're in good shape, but consider trimming {topTicker} slightly and adding a defensive position to balance out the risk.
                    </p>
                  </div>

                  {/* Glossary */}
                  <button onClick={() => setGlossaryOpen(!glossaryOpen)} className="text-sm text-primary hover:text-accent-bright transition-colors">
                    What do these terms mean? {glossaryOpen ? '−' : '+'}
                  </button>
                  <AnimatePresence>
                    {glossaryOpen && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                        <div className="glass-elevated rounded-lg p-4 space-y-2">
                          {glossary.map((g) => (
                            <div key={g.term} className="flex gap-4">
                              <span className="font-mono text-[11px] text-primary w-28 flex-shrink-0">{g.term}</span>
                              <span className="text-[13px] text-foreground/80">{g.def}</span>
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}

              {/* METHODOLOGY TAB */}
              {activeTab === 'Methodology' && (
                <div className="space-y-1">
                  {methodologyItems.map((item) => (
                    <div key={item.metric} className="border-b border-border/30 last:border-0">
                      <button
                        onClick={() => setOpenMethodology(openMethodology === item.metric ? null : item.metric)}
                        className="w-full flex items-center justify-between py-3 text-left"
                      >
                        <span className="font-mono text-xs text-foreground">{item.metric}</span>
                        <ChevronDown size={14} className={`text-primary transition-transform ${openMethodology === item.metric ? 'rotate-180' : ''}`} />
                      </button>
                      <AnimatePresence>
                        {openMethodology === item.metric && (
                          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden pb-3">
                            <div className="pl-2 space-y-1.5">
                              <p className="font-mono text-[11px] text-muted-foreground">{item.formula}</p>
                              <p className="text-[13px] text-foreground/80">{item.plain}</p>
                              {item.result && <p className="text-[13px] text-primary font-medium">Your result: {item.result}</p>}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  ))}
                </div>
              )}

              {/* AI ANALYSIS TAB */}
              {activeTab === 'AI Analysis' && (
                <div className="space-y-4">
                  <div className="glass-elevated rounded-lg p-4 border-l-2 border-primary">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap size={16} className="text-primary" />
                      <span className="font-mono text-[10px] uppercase tracking-wider text-primary">ARCUS AI ANALYSIS</span>
                    </div>
                    <div className="text-sm text-foreground/85 leading-[1.7] space-y-3">
                      <p>Your portfolio shows a <span className="font-mono text-primary font-medium">Sharpe ratio of {m.sharpe?.toFixed(2)}</span>, indicating strong risk-adjusted returns compared to typical benchmarks. This means you're being well-compensated for the risk you're taking.</p>
                      <p>However, concentration risk should be monitored. <span className="font-mono text-primary font-medium">{topTicker}</span> contributes heavily to your total portfolio risk. This asymmetric risk contribution means a significant {topTicker} drawdown would disproportionately impact your returns.</p>
                      <p>Your <span className="font-mono text-primary font-medium">Beta of {m.beta?.toFixed(2)}</span> suggests the portfolio moves roughly in line with the market. Our simulation models show a high probability of achieving moderate annual return targets.</p>
                      <p>Recommendation: Consider ensuring your allocations are properly distributed. If {topTicker} exceeds 25% of your portfolio weight, consider taking profits and redistributing to {secondTicker} for improved diversification.</p>
                    </div>
                  </div>
                  <div className="glass-elevated rounded-lg flex items-center px-3 py-2">
                    <input
                      value={followUp}
                      onChange={(e) => setFollowUp(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter' && followUp.trim()) { sendToChat(followUp); setFollowUp(''); } }}
                      placeholder="Ask a follow-up about this analysis..."
                      className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground/50 outline-none"
                    />
                    <button onClick={() => { if (followUp.trim()) { sendToChat(followUp); setFollowUp(''); } }} className="text-primary hover:text-accent-bright ml-2">
                      <SendHorizontal size={14} />
                    </button>
                  </div>
                </div>
              )}

              {/* RECOMMENDATIONS TAB */}
              {activeTab === 'Recommendations' && (
                <div className="space-y-3">
                  {MOCK_AI_RECOMMENDATIONS.map((rec, i) => (
                    <div key={i} className="glass-elevated rounded-lg p-4 border-l-2 border-primary">
                      <span className="font-mono text-[9px] uppercase tracking-wider bg-primary/15 text-primary px-2 py-0.5 rounded-full">{recCategories[i]}</span>
                      <p className="text-sm text-foreground/85 leading-relaxed mt-2">{rec}</p>
                      <div className="flex gap-3 mt-3">
                        <button onClick={() => sendToChat(`Explain this recommendation: ${rec} — and tell me how to act on it.`)} className="font-mono text-[10px] text-primary flex items-center gap-1 hover:text-accent-bright transition-colors">
                          <MessageSquare size={12} /> Discuss in AI Chat →
                        </button>
                        <button onClick={() => navigate('/dashboard/mock')} className="font-mono text-[10px] text-primary flex items-center gap-1 hover:text-accent-bright transition-colors">
                          Apply to Sandbox
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default FullReport;
