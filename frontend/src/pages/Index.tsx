import { useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, GitBranch, Zap, ChevronRight, CheckCircle, X, Calculator, PlayCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import ArcusLogo from '@/components/ArcusLogo';
import NewsTicker from '@/components/NewsTicker';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1, delayChildren: 0.2 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const features = [
  { icon: Activity, title: 'Complete Risk Analysis', desc: 'Sharpe, VaR, CVaR, Beta, Max Drawdown — all in one place with institutional-grade calculations.' },
  { icon: GitBranch, title: 'Strategy Sandbox', desc: 'Compare your portfolio against simulated alternatives side by side with real-time delta analysis.' },
  { icon: Zap, title: 'Arcus AI', desc: 'Portfolio-aware chatbot that understands your positions, risk profile, and market conditions.' },
];

const comparison = [
  { feature: 'Sharpe Ratio', robinhood: false, pc: false, arcus: true },
  { feature: 'VaR / CVaR', robinhood: false, pc: false, arcus: true },
  { feature: 'Monte Carlo', robinhood: false, pc: false, arcus: true },
  { feature: 'Risk Contribution', robinhood: false, pc: false, arcus: true },
  { feature: 'Stress Testing', robinhood: false, pc: false, arcus: true },
  { feature: 'AI Chatbot', robinhood: false, pc: false, arcus: true },
  { feature: 'Risk Fingerprint', robinhood: false, pc: false, arcus: true },
  { feature: 'Portfolio Tracking', robinhood: true, pc: true, arcus: true },
];

const demoPortfolio = {
  holdings: [
    { ticker: 'AAPL', shares: '15', cost: '148.20' },
    { ticker: 'NVDA', shares: '5', cost: '620.00' },
    { ticker: 'MSFT', shares: '8', cost: '320.00' },
    { ticker: 'GOOGL', shares: '12', cost: '132.50' },
    { ticker: 'VOO', shares: '40', cost: '388.00' },
  ],
  livePrices: {
    AAPL: 182.63,
    NVDA: 875.40,
    MSFT: 378.91,
    GOOGL: 165.22,
    VOO: 465.18,
  },
  startDate: '2023-01-01',
  endDate: '2024-12-31',
};

const demoInvestorDna = {
  risk_tolerance: 'Growth',
  target_return: 0.15,
  sectors: ['Technology', 'Consumer'],
};

const demoOutput = [
  { label: 'Portfolio Value', value: '$42.7K', detail: 'sample market value' },
  { label: 'Sharpe Ratio', value: '1.84', detail: 'risk-adjusted return' },
  { label: 'VaR 95%', value: '-3.2%', detail: 'sample daily downside' },
];

const seedDemoResults = () => {
  localStorage.setItem('arcus-portfolio', JSON.stringify(demoPortfolio));
  localStorage.setItem('arcus-portfolio-draft', JSON.stringify({
    holdings: demoPortfolio.holdings,
    startDate: demoPortfolio.startDate,
    endDate: demoPortfolio.endDate,
  }));
  localStorage.setItem('arcus-investor-dna', JSON.stringify(demoInvestorDna));
  localStorage.removeItem('arcus-last-analysis');
};

const DemoRecording = () => (
  <div className="relative min-h-[340px] overflow-hidden rounded-xl border border-border bg-card-elevated p-3">
    <div className="flex items-center gap-1.5 border-b border-border/80 pb-3">
      <span className="h-2.5 w-2.5 rounded-full bg-signal-red" />
      <span className="h-2.5 w-2.5 rounded-full bg-signal-amber" />
      <span className="h-2.5 w-2.5 rounded-full bg-signal-green" />
      <span className="ml-3 font-mono text-[10px] text-muted-foreground">arcus.app/dashboard</span>
    </div>

    <div className="relative mt-4 h-[284px]">
      <motion.div
        className="absolute inset-0 rounded-lg border border-border bg-background/80 p-4"
        animate={{ opacity: [1, 1, 0, 0, 1] }}
        transition={{ duration: 9, repeat: Infinity, times: [0, 0.36, 0.43, 0.92, 1] }}
      >
        <span className="label-mono">ADD HOLDINGS</span>
        <div className="mt-3 space-y-2">
          {demoPortfolio.holdings.map((holding, index) => (
            <motion.div
              key={holding.ticker}
              className="grid grid-cols-[1fr_54px_72px] gap-2 rounded-lg border border-border bg-card px-3 py-2"
              initial={false}
              animate={{ opacity: [0, 1, 1], x: [-12, 0, 0] }}
              transition={{ duration: 9, repeat: Infinity, delay: index * 0.28, times: [0, 0.12, 1] }}
            >
              <span className="font-mono text-xs font-bold text-primary">{holding.ticker}</span>
              <span className="font-mono text-[11px] text-foreground">{holding.shares}</span>
              <span className="font-mono text-[11px] text-muted-foreground">${holding.cost}</span>
            </motion.div>
          ))}
        </div>
        <motion.div
          className="mt-4 rounded-lg bg-primary py-2.5 text-center font-mono text-[11px] font-bold text-primary-foreground"
          animate={{ scale: [1, 1, 1.03, 1] }}
          transition={{ duration: 9, repeat: Infinity, times: [0, 0.62, 0.68, 1] }}
        >
          Analyse Portfolio
        </motion.div>
      </motion.div>

      <motion.div
        className="absolute inset-0 rounded-lg border border-border bg-background/80 p-4"
        animate={{ opacity: [0, 0, 1, 1, 0] }}
        transition={{ duration: 9, repeat: Infinity, times: [0, 0.4, 0.48, 0.86, 0.94] }}
      >
        <div className="flex items-center justify-between">
          <span className="label-mono">RISK REPORT</span>
          <span className="rounded-full bg-primary/10 px-2 py-1 font-mono text-[10px] text-primary">Growth · 15%</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2">
          {demoOutput.map((item, index) => (
            <motion.div
              key={item.label}
              className="rounded-lg border border-border bg-card p-3"
              animate={{ y: [10, 0, 0], opacity: [0, 1, 1] }}
              transition={{ duration: 9, repeat: Infinity, delay: 3.7 + index * 0.18, times: [0, 0.1, 1] }}
            >
              <span className="font-mono text-[9px] uppercase text-muted-foreground">{item.label}</span>
              <div className="mt-1 font-mono text-base font-bold text-foreground">{item.value}</div>
            </motion.div>
          ))}
        </div>
        <div className="mt-4 rounded-lg border border-border bg-card p-3">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-[10px] text-muted-foreground">Monte Carlo range</span>
            <span className="font-mono text-[10px] text-signal-green">1,000 sims</span>
          </div>
          <svg width="100%" height="84" viewBox="0 0 320 84" preserveAspectRatio="none">
            <motion.path
              d="M0 58 C45 42 65 66 104 48 C145 30 168 44 202 24 C240 4 276 32 320 14"
              fill="none"
              stroke="#38BDA4"
              strokeWidth="3"
              strokeLinecap="round"
              initial={false}
              animate={{ pathLength: [0, 1, 1] }}
              transition={{ duration: 9, repeat: Infinity, times: [0.47, 0.66, 1] }}
            />
            <path d="M0 70 C58 54 96 74 144 56 C204 34 250 48 320 28" fill="none" stroke="#4F9CF0" strokeWidth="1.5" strokeOpacity="0.55" />
          </svg>
        </div>
        <div className="mt-3 flex gap-2">
          {['Stress tests', 'Risk contribution', 'AI insights'].map((label) => (
            <span key={label} className="rounded-full bg-primary/10 px-2.5 py-1 font-mono text-[10px] text-primary">{label}</span>
          ))}
        </div>
      </motion.div>

      <motion.div
        className="absolute h-5 w-5 rounded-full border-2 border-primary bg-primary/25 shadow-[0_0_18px_rgba(56,189,164,0.6)]"
        animate={{ x: [18, 126, 242, 164, 164, 250], y: [38, 76, 214, 246, 246, 50], scale: [1, 1, 1.25, 0.82, 1, 1] }}
        transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  </div>
);

const HowItWorksModal = ({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-h-[92vh] max-w-[920px] overflow-y-auto border-border bg-background p-4 sm:p-6">
      <DialogHeader>
        <DialogTitle className="font-display text-2xl font-extrabold text-foreground">See how Arcus calculates risk</DialogTitle>
        <DialogDescription>
          A quick animated walkthrough using dummy values, then you can start your own analysis.
        </DialogDescription>
      </DialogHeader>

      <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
        <DemoRecording />

        <div className="space-y-4">
          <div className="glass rounded-xl p-4">
            <span className="label-mono">DUMMY VALUES USED</span>
            <div className="mt-3 space-y-2">
              {demoPortfolio.holdings.map((holding) => (
                <div key={holding.ticker} className="grid grid-cols-[1fr_auto] gap-3 rounded-lg bg-card-elevated px-3 py-2">
                  <span className="font-mono text-xs font-bold text-primary">{holding.ticker}</span>
                  <span className="font-mono text-xs text-foreground">{holding.shares} shares @ ${holding.cost}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Date range: Jan 1, 2023 to Dec 31, 2024. Profile: Growth. Target return: 15% per year.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {demoOutput.map((item) => (
              <div key={item.label} className="glass-elevated rounded-lg p-3">
                <span className="font-mono text-[9px] uppercase text-muted-foreground">{item.label}</span>
                <div className="mt-1 font-mono text-lg font-bold text-foreground">{item.value}</div>
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Link to="/dashboard/results" onClick={seedDemoResults} className="flex-1">
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} className="w-full rounded-xl border border-border px-4 py-3 text-sm font-semibold text-foreground transition-colors hover:bg-card-elevated">
                <PlayCircle size={15} className="mr-1.5 inline" /> View Demo Results
              </motion.button>
            </Link>
            <Link to="/onboarding" className="flex-1">
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} className="w-full rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground">
                <Calculator size={15} className="mr-1.5 inline" /> Get Started to Analyse
              </motion.button>
            </Link>
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>
);

const Landing = () => {
  const [howItWorksOpen, setHowItWorksOpen] = useState(false);

  return (
  <div className="min-h-screen bg-background teal-grid-bg">
    {/* News ticker at very top */}
    <NewsTicker />

    {/* Navbar — pushed down by ticker */}
    <nav className="glass-navbar h-[52px] flex items-center px-6 justify-between sticky top-9 z-50">
      <div className="flex items-center gap-2">
        <ArcusLogo size={28} />
        <span className="font-display font-extrabold text-foreground text-lg">Arcus</span>
      </div>
      <div className="flex gap-2 sm:gap-3">
        <Link to="/onboarding" className="px-4 py-2 rounded-full text-sm bg-primary text-primary-foreground font-semibold hover:bg-accent-bright transition-colors">
          Get Started <ChevronRight size={14} className="inline ml-1" />
        </Link>
      </div>
    </nav>

    {/* Hero */}
    <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-14 sm:pt-24 pb-12 sm:pb-16 text-center">
      <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }} className="flex items-center justify-center gap-3 mb-8">
        <ArcusLogo size={48} />
        <span className="font-display font-extrabold text-foreground text-[32px]">Arcus</span>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="font-display font-extrabold text-[34px] sm:text-5xl md:text-[64px] leading-[1.05] text-foreground"
      >
        Institutional-Grade<br />Portfolio Analytics.
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="font-mono text-primary text-lg mt-6"
      >
        Sharpe ratios. VaR. Monte Carlo. In seconds.
      </motion.p>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
        className="flex flex-col sm:flex-row gap-3 justify-center items-center mt-8"
      >
        <Link to="/onboarding">
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} className="px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-sm">
            Get Started <ChevronRight size={14} className="inline ml-1" />
          </motion.button>
        </Link>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.96 }}
          onClick={() => setHowItWorksOpen(true)}
          className="px-6 py-3 rounded-xl border border-border text-foreground font-semibold text-sm hover:bg-card transition-colors"
        >
          See how it works
        </motion.button>
      </motion.div>

      {/* Floating dashboard preview */}
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6, duration: 0.8 }} className="mt-16 mx-auto max-w-2xl">
        <div className="glass rounded-2xl p-6 animate-float" style={{ perspective: '1000px' }}>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'SHARPE', value: '1.84', change: '+0.12', positive: true },
              { label: 'VAR 95%', value: '-3.2%', change: '±0.4%', positive: false },
              { label: 'HEALTH', value: '78', change: 'GOOD', positive: true },
            ].map((m) => (
              <div key={m.label} className="glass-elevated rounded-lg p-3 text-left">
                <span className="label-mono">{m.label}</span>
                <div className="font-mono text-xl font-bold text-foreground mt-1">{m.value}</div>
                <span className={`font-mono text-[10px] ${m.positive ? 'text-signal-green' : 'text-signal-red'}`}>{m.change}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 h-16 rounded-lg glass-elevated flex items-center justify-center overflow-hidden">
            <svg width="100%" height="40" viewBox="0 0 300 40" preserveAspectRatio="none" className="px-4">
              <polyline points="0,30 20,25 40,28 60,18 80,22 100,15 120,20 140,12 160,18 180,10 200,14 220,8 240,12 260,6 280,10 300,5" fill="none" stroke="#38BDA4" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
        </div>
      </motion.div>
    </section>

    {/* Stats bar */}
    <section className="border-b border-border py-6">
      <div className="max-w-4xl mx-auto flex flex-wrap justify-center gap-8 md:gap-16 px-6">
        {[
          { value: '15+', label: 'Analytics' },
          { value: 'Institutional', label: 'Grade Analysis' },
          { value: 'Real-time', label: 'AI Insights' },
        ].map((s) => (
          <div key={s.label} className="text-center">
            <div className="font-mono text-2xl font-bold text-foreground">{s.value}</div>
            <div className="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">{s.label}</div>
          </div>
        ))}
      </div>
    </section>

    {/* Feature cards */}
    <motion.section variants={stagger} initial="hidden" whileInView="show" viewport={{ once: true }} className="max-w-5xl mx-auto px-6 py-20">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {features.map((f) => (
          <motion.div key={f.title} variants={fadeUp} className="glass rounded-xl p-6 card-hover-glow">
            <f.icon size={24} className="text-primary mb-4" />
            <h3 className="font-display font-bold text-foreground text-lg">{f.title}</h3>
            <p className="text-muted-foreground text-sm mt-2 leading-relaxed">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </motion.section>

    {/* Comparison table */}
    <section className="max-w-xl mx-auto px-6 pb-20">
      <h2 className="font-display font-extrabold text-2xl text-foreground text-center mb-8">What you get vs. the alternatives</h2>
      <div className="glass rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 label-mono">Feature</th>
              <th className="px-3 py-3 label-mono text-center">Robinhood</th>
              <th className="px-3 py-3 label-mono text-center">Personal Capital</th>
              <th className="px-3 py-3 label-mono text-center text-primary">Arcus</th>
            </tr>
          </thead>
          <tbody>
            {comparison.map((row) => (
              <tr key={row.feature} className="border-b border-border/50 hover:bg-card-elevated/50 transition-colors">
                <td className="px-4 py-2.5 text-sm text-foreground">{row.feature}</td>
                <td className="px-3 py-2.5 text-center">{row.robinhood ? <CheckCircle size={15} className="text-signal-green mx-auto" /> : <X size={15} className="text-muted-foreground/30 mx-auto" />}</td>
                <td className="px-3 py-2.5 text-center">{row.pc ? <CheckCircle size={15} className="text-signal-green mx-auto" /> : <X size={15} className="text-muted-foreground/30 mx-auto" />}</td>
                <td className="px-3 py-2.5 text-center"><CheckCircle size={15} className="text-primary mx-auto" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>

    {/* CTA footer */}
    <section className="text-center py-20 border-t border-border">
      <h2 className="font-display font-extrabold text-3xl text-foreground">Ready to see your real risk exposure?</h2>
      <Link to="/onboarding">
        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} className="mt-8 px-8 py-4 rounded-xl bg-primary text-primary-foreground font-bold text-base">
          Get Started Free <ChevronRight size={16} className="inline ml-1" />
        </motion.button>
      </Link>
    </section>

    <HowItWorksModal open={howItWorksOpen} onOpenChange={setHowItWorksOpen} />
  </div>
  );
};

export default Landing;
