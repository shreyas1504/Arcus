import { motion } from 'framer-motion';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Line, ComposedChart } from 'recharts';
import DataUnavailable from '@/components/DataUnavailable';
import type { PerformancePoint } from '@/components/charts/PerformanceChart';
import type { MonteCarloPoint } from '@/components/charts/MonteCarloChart';

/**
 * Realised history against the Monte Carlo projection.
 *
 * This panel previously generated both series from sine waves and printed six
 * hardcoded statistics ("+18.7% Return", "1.84 Sharpe", "73% Gain Prob") for
 * every user, backend up or down. Both halves now come from the API, and each
 * renders an empty state when its data is missing.
 */

export interface PastVsFutureMetrics {
  annualized_return: number;
  max_drawdown: number;
  sharpe: number;
}

const AXIS = { fontSize: 10, fill: '#6E7681', fontFamily: 'JetBrains Mono' } as const;
const TOOLTIP = {
  background: '#161B22',
  border: '1px solid rgba(48,54,61,0.8)',
  borderRadius: 8,
  fontFamily: 'JetBrains Mono',
  fontSize: 11,
} as const;

const Chip = ({ tone, children }: { tone: 'green' | 'red' | 'primary'; children: React.ReactNode }) => {
  const cls = tone === 'green'
    ? 'bg-signal-green/10 text-signal-green'
    : tone === 'red'
      ? 'bg-signal-red/10 text-signal-red'
      : 'bg-primary/10 text-primary';
  return <span className={`font-mono text-[11px] px-2 py-0.5 rounded-full ${cls}`}>{children}</span>;
};

const signedPct = (v: number) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`;

const PastVsFuture = ({
  performance,
  monteCarlo,
  metrics,
  initialValue = 100000,
}: {
  performance?: PerformancePoint[];
  monteCarlo?: MonteCarloPoint[];
  metrics?: PastVsFutureMetrics;
  initialValue?: number;
}) => {
  // Projected outcomes come from the final Monte Carlo bucket, never a constant.
  const finalPoint = monteCarlo?.length ? monteCarlo[monteCarlo.length - 1] : null;
  const medianReturn = finalPoint ? finalPoint.p50 / initialValue - 1 : null;
  const downsideReturn = finalPoint ? finalPoint.p10 / initialValue - 1 : null;

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-5 mb-6">
      <div className="flex items-center gap-2 mb-6">
        <span className="label-mono text-primary">PAST VS FUTURE</span>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Realised */}
        <div className="glass-elevated rounded-lg p-4">
          <span className="font-mono text-[10px] uppercase tracking-wider text-primary mb-3 block">REALISED</span>
          {!performance?.length ? (
            <DataUnavailable label="Performance history" height={180} />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <AreaChart data={performance}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(48,54,61,0.5)" />
                  <XAxis dataKey="date" tick={AXIS} />
                  <YAxis tick={AXIS} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={TOOLTIP} />
                  <Area type="monotone" dataKey="portfolio" stroke="#38BDA4" fill="rgba(56,189,148,0.08)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
              {metrics && (
                <div className="flex flex-wrap gap-2 mt-3">
                  <Chip tone={metrics.annualized_return >= 0 ? 'green' : 'red'}>
                    {signedPct(metrics.annualized_return)} Ann. Return
                  </Chip>
                  <Chip tone="red">{signedPct(metrics.max_drawdown)} Drawdown</Chip>
                  <Chip tone="primary">{metrics.sharpe.toFixed(2)} Sharpe</Chip>
                </div>
              )}
            </>
          )}
        </div>

        {/* Projected */}
        <div className="glass-elevated rounded-lg p-4">
          <span className="font-mono text-[10px] uppercase tracking-wider text-primary mb-3 block">PROJECTED (MONTE CARLO)</span>
          {!monteCarlo?.length ? (
            <DataUnavailable label="Projection" height={180} />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <ComposedChart data={monteCarlo}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(48,54,61,0.5)" />
                  <XAxis dataKey="month" tick={AXIS} />
                  <YAxis tick={AXIS} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={TOOLTIP} />
                  <Area type="monotone" dataKey="p10" stroke="none" fill="rgba(240,81,79,0.1)" />
                  <Area type="monotone" dataKey="p90" stroke="none" fill="rgba(63,182,139,0.1)" />
                  <Line type="monotone" dataKey="p50" stroke="#38BDA4" strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
              {medianReturn !== null && downsideReturn !== null && (
                <div className="flex flex-wrap gap-2 mt-3">
                  <Chip tone="primary">{signedPct(medianReturn)} Median</Chip>
                  <Chip tone="red">{signedPct(downsideReturn)} 10th %ile</Chip>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default PastVsFuture;
