import { useState } from 'react';
import { motion } from 'framer-motion';
import { Lock, Plus, Info } from 'lucide-react';
import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import AnimatedNumber from '@/components/AnimatedNumber';
import { MOCK_PORTFOLIO } from '@/lib/mock-data';
import { useIsMobile } from '@/hooks/use-mobile';

interface MockColumn {
  id: string;
  label: string;
  weights: Record<string, number>;
}

const tickers = MOCK_PORTFOLIO.tickers;
const currentWeights = Object.fromEntries(tickers.map((t, i) => [t, MOCK_PORTFOLIO.weights[i]]));

const calcMetrics = (weights: Record<string, number>) => {
  const totalW = Object.values(weights).reduce((a, b) => a + b, 0);
  const norm = totalW > 0 ? totalW : 1;
  const nvdaW = (weights['NVDA'] || 0) / norm;
  return {
    sharpe: 1.84 + (nvdaW - 0.2) * 2 + (weights['VOO'] || 0) * 0.5,
    var95: -3.2 + nvdaW * 5 - (weights['VOO'] || 0) * 3,
    healthScore: Math.round(78 + ((weights['VOO'] || 0) - 0.2) * 30 - nvdaW * 20),
    cvar: -4.8 + nvdaW * 6 - (weights['VOO'] || 0) * 4,
    beta: 0.93 + (nvdaW - 0.2) * 1.5,
  };
};

const Sandbox = () => {
  const isMobile = useIsMobile();
  const [mocks, setMocks] = useState<MockColumn[]>([
    { id: 'a', label: 'MOCK A', weights: { ...currentWeights, NVDA: 0.15, VOO: 0.25 } },
  ]);

  const currentMetrics = calcMetrics(currentWeights);

  const addMock = () => {
    const labels = ['B', 'C', 'D'];
    const id = labels[mocks.length - 1] || `${mocks.length + 1}`;
    setMocks([...mocks, { id, label: `MOCK ${id.toUpperCase()}`, weights: { ...currentWeights } }]);
  };

  const updateWeight = (mockIdx: number, ticker: string, value: number) => {
    const newMocks = [...mocks];
    newMocks[mockIdx].weights[ticker] = value;
    setMocks(newMocks);
  };

  const bestSharpeIdx = mocks.reduce((best, mock, i) => {
    const s = calcMetrics(mock.weights).sharpe;
    return s > (best.sharpe || 0) ? { idx: i, sharpe: s } : best;
  }, { idx: -1, sharpe: currentMetrics.sharpe }).idx;

  return (
    <AppLayout title="Strategy Sandbox">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <BackButton to="/dashboard/results" />

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-foreground">Strategy Sandbox</h1>
          <p className="text-muted-foreground text-sm mt-1">Compare your portfolio against simulated alternatives in real-time.</p>
        </motion.div>

        <div
          className="grid gap-4 mt-8"
          style={{
            gridTemplateColumns: isMobile
              ? '1fr'
              : `repeat(${1 + mocks.length + (mocks.length < 3 ? 1 : 0)}, minmax(0, 1fr))`,
          }}
        >
          {/* Current column */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Lock size={14} className="text-primary" />
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">CURRENT</span>
            </div>
            <div className="space-y-3">
              {[
                { label: 'Health Score', value: currentMetrics.healthScore, fmt: (n: number) => Math.round(n).toString() },
                { label: 'Sharpe', value: currentMetrics.sharpe, fmt: (n: number) => n.toFixed(2) },
                { label: 'VaR 95%', value: currentMetrics.var95, fmt: (n: number) => `${n.toFixed(1)}%` },
                { label: 'CVaR', value: currentMetrics.cvar, fmt: (n: number) => `${n.toFixed(1)}%` },
                { label: 'Beta', value: currentMetrics.beta, fmt: (n: number) => n.toFixed(2) },
              ].map((m) => (
                <div key={m.label} className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    {m.label}
                    <Info size={10} className="text-primary/40 cursor-help" />
                  </span>
                  <span className="font-mono text-sm text-foreground">{m.fmt(m.value)}</span>
                </div>
              ))}
            </div>
            <div className="mt-6 space-y-3">
              <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>WEIGHTS</span>
              {tickers.map((t) => (
                <div key={t} className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground w-12">{t}</span>
                  <div className="flex-1 h-1.5 bg-border rounded-full">
                    <div className="h-full bg-muted-foreground/30 rounded-full" style={{ width: `${currentWeights[t] * 100}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground w-8 text-right">{(currentWeights[t] * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Mock columns */}
          {mocks.map((mock, mockIdx) => {
            const metrics = calcMetrics(mock.weights);
            const totalW = Object.values(mock.weights).reduce((a, b) => a + b, 0);
            const normalized = Math.abs(totalW - 1) < 0.01;
            const isBest = mockIdx === bestSharpeIdx;

            return (
              <motion.div key={mock.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 * (mockIdx + 1) }} className="glass rounded-xl p-5 relative">
                <div className="flex items-center justify-between mb-4">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-primary">{mock.label}</span>
                  {isBest && (
                    <span className="bg-primary text-primary-foreground font-mono text-[8px] uppercase px-2 py-0.5 rounded-full whitespace-nowrap">BEST SHARPE ↑</span>
                  )}
                </div>
                {!normalized && (
                  <span className="font-mono text-[10px] text-signal-amber animate-pulse block mb-2">NORMALISING... ({(totalW * 100).toFixed(0)}%)</span>
                )}
                <div className="space-y-3">
                  {[
                    { label: 'Health Score', value: metrics.healthScore, cValue: currentMetrics.healthScore, fmt: (n: number) => Math.round(n).toString() },
                    { label: 'Sharpe', value: metrics.sharpe, cValue: currentMetrics.sharpe, fmt: (n: number) => n.toFixed(2) },
                    { label: 'VaR 95%', value: metrics.var95, cValue: currentMetrics.var95, fmt: (n: number) => `${n.toFixed(1)}%` },
                    { label: 'CVaR', value: metrics.cvar, cValue: currentMetrics.cvar, fmt: (n: number) => `${n.toFixed(1)}%` },
                    { label: 'Beta', value: metrics.beta, cValue: currentMetrics.beta, fmt: (n: number) => n.toFixed(2) },
                  ].map((m) => {
                    const delta = m.value - m.cValue;
                    const isGood = m.label === 'VaR 95%' || m.label === 'CVaR' ? delta < 0 : delta > 0;
                    return (
                      <div key={m.label} className="flex justify-between items-center">
                        <span className="text-xs text-muted-foreground">{m.label}</span>
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
                <div className="mt-6 space-y-3">
                  <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>WEIGHTS</span>
                  {tickers.map((t) => (
                    <div key={t} className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-muted-foreground w-12">{t}</span>
                      <input
                        type="range" min="0" max="100"
                        value={(mock.weights[t] || 0) * 100}
                        onChange={(e) => updateWeight(mockIdx, t, Number(e.target.value) / 100)}
                        className="flex-1 min-w-0 h-1.5 appearance-none bg-border rounded-full cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                      />
                      <span className="font-mono text-[10px] text-foreground w-8 text-right">{((mock.weights[t] || 0) * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            );
          })}

          {/* Add mock column */}
          {mocks.length < 3 && (
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

        <p className="font-mono text-[10px] text-muted-foreground/50 mt-4 text-center">
          ⚠ FOR INFORMATIONAL PURPOSES ONLY. Not financial advice. Past performance is not indicative of future results.
        </p>
      </div>
    </AppLayout>
  );
};

export default Sandbox;
