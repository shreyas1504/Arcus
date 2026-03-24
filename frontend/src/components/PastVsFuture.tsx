import { motion } from 'framer-motion';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Line, ComposedChart } from 'recharts';

const pastData = Array.from({ length: 12 }, (_, i) => ({
  month: new Date(2023, i).toLocaleDateString('en-US', { month: 'short' }),
  value: 100000 * (1 + 0.015 * i + Math.sin(i * 0.5) * 0.03),
}));

const futureData = Array.from({ length: 12 }, (_, i) => ({
  month: new Date(2024, i).toLocaleDateString('en-US', { month: 'short' }),
  p10: 100000 * (1 + 0.187) * (1 - 0.01 * i + Math.sin(i * 0.3) * 0.02 - 0.005 * i),
  p50: 100000 * (1 + 0.187) * (1 + 0.012 * i),
  p90: 100000 * (1 + 0.187) * (1 + 0.025 * i + Math.sin(i * 0.4) * 0.02),
}));

const PastVsFuture = () => (
  <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-5 mb-6">
    <div className="flex items-center gap-2 mb-6">
      <span className="label-mono text-primary">PAST VS FUTURE</span>
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Past */}
      <div className="glass-elevated rounded-lg p-4">
        <span className="font-mono text-[10px] uppercase tracking-wider text-primary mb-3 block">PAST 12 MONTHS</span>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={pastData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(48,54,61,0.5)" />
            <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#6E7681', fontFamily: 'JetBrains Mono' }} />
            <YAxis tick={{ fontSize: 10, fill: '#6E7681', fontFamily: 'JetBrains Mono' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
            <Tooltip contentStyle={{ background: '#161B22', border: '1px solid rgba(48,54,61,0.8)', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }} />
            <Area type="monotone" dataKey="value" stroke="#38BDA4" fill="rgba(56,189,148,0.08)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
        <div className="flex gap-3 mt-3">
          <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-signal-green/10 text-signal-green">+18.7% Return</span>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-signal-red/10 text-signal-red">-18.4% Drawdown</span>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary">1.84 Sharpe</span>
        </div>
      </div>

      {/* Future */}
      <div className="glass-elevated rounded-lg p-4">
        <span className="font-mono text-[10px] uppercase tracking-wider text-primary mb-3 block">NEXT 12 MONTHS (PROJECTED)</span>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={futureData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(48,54,61,0.5)" />
            <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#6E7681', fontFamily: 'JetBrains Mono' }} />
            <YAxis tick={{ fontSize: 10, fill: '#6E7681', fontFamily: 'JetBrains Mono' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
            <Tooltip contentStyle={{ background: '#161B22', border: '1px solid rgba(48,54,61,0.8)', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }} />
            <Area type="monotone" dataKey="p10" stroke="none" fill="rgba(240,81,79,0.1)" />
            <Area type="monotone" dataKey="p90" stroke="none" fill="rgba(63,182,139,0.1)" />
            <Line type="monotone" dataKey="p50" stroke="#38BDA4" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="flex gap-3 mt-3">
          <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary">+14.2% Median</span>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-signal-red/10 text-signal-red">-12.3% Downside</span>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-signal-green/10 text-signal-green">73% Gain Prob</span>
        </div>
      </div>
    </div>
  </motion.div>
);

export default PastVsFuture;
