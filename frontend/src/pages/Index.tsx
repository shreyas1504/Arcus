import { motion } from 'framer-motion';
import { Activity, GitBranch, Zap, ChevronRight, CheckCircle, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import ArcusLogo from '@/components/ArcusLogo';
import NewsTicker from '@/components/NewsTicker';
import FloatingChat from '@/components/FloatingChat';

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

const Landing = () => (
  <div className="min-h-screen bg-background teal-grid-bg">
    {/* News ticker at very top */}
    <NewsTicker />

    {/* Navbar — pushed down by ticker */}
    <nav className="glass-navbar h-[52px] flex items-center px-6 justify-between sticky top-9 z-50">
      <div className="flex items-center gap-2">
        <ArcusLogo size={28} />
        <span className="font-display font-extrabold text-foreground text-lg">Arcus</span>
      </div>
      <div className="flex gap-3">
        <Link to="/dashboard" className="px-4 py-1.5 rounded-full text-sm text-muted-foreground hover:text-foreground transition-colors">Dashboard</Link>
        <Link to="/onboarding" className="px-4 py-2 rounded-full text-sm bg-primary text-primary-foreground font-semibold hover:bg-accent-bright transition-colors">
          Get Started <ChevronRight size={14} className="inline ml-1" />
        </Link>
      </div>
    </nav>

    {/* Hero */}
    <section className="max-w-5xl mx-auto px-6 pt-24 pb-16 text-center">
      <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }} className="flex items-center justify-center gap-3 mb-8">
        <ArcusLogo size={48} />
        <span className="font-display font-extrabold text-foreground text-[32px]">Arcus</span>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="font-display font-extrabold text-5xl md:text-[64px] leading-[1.05] text-foreground"
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
        className="flex gap-3 justify-center mt-8"
      >
        <Link to="/onboarding">
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} className="px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-sm">
            Get Started <ChevronRight size={14} className="inline ml-1" />
          </motion.button>
        </Link>
        <Link to="/dashboard/results">
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} className="px-6 py-3 rounded-xl border border-border text-foreground font-semibold text-sm hover:bg-card transition-colors">
            See how it works
          </motion.button>
        </Link>
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
          <div className="mt-3 h-16 rounded-lg glass-elevated flex items-center justify-center">
            <svg width="100%" height="40" className="px-4">
              <polyline points="0,30 20,25 40,28 60,18 80,22 100,15 120,20 140,12 160,18 180,10 200,14 220,8 240,12 260,6 280,10 300,5" fill="none" stroke="#38BDA4" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
        </div>
      </motion.div>
    </section>

    {/* Stats bar */}
    <section className="border-b border-border py-6">
      <div className="max-w-4xl mx-auto flex justify-center gap-16">
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
    <section className="max-w-4xl mx-auto px-6 pb-20">
      <h2 className="font-display font-extrabold text-2xl text-foreground text-center mb-8">What you get vs. the alternatives</h2>
      <div className="glass rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left p-4 label-mono">Feature</th>
              <th className="p-4 label-mono text-center">Robinhood</th>
              <th className="p-4 label-mono text-center">Personal Capital</th>
              <th className="p-4 label-mono text-center text-primary">Arcus</th>
            </tr>
          </thead>
          <tbody>
            {comparison.map((row) => (
              <tr key={row.feature} className="border-b border-border/50 hover:bg-card-elevated/50 transition-colors">
                <td className="p-4 text-sm text-foreground">{row.feature}</td>
                <td className="p-4 text-center">{row.robinhood ? <CheckCircle size={16} className="text-signal-green mx-auto" /> : <X size={16} className="text-muted-foreground/30 mx-auto" />}</td>
                <td className="p-4 text-center">{row.pc ? <CheckCircle size={16} className="text-signal-green mx-auto" /> : <X size={16} className="text-muted-foreground/30 mx-auto" />}</td>
                <td className="p-4 text-center"><CheckCircle size={16} className="text-primary mx-auto" /></td>
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

    <FloatingChat />
  </div>
);

export default Landing;
