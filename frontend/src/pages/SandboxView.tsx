import { useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import AppLayout from '@/components/AppLayout';
import { TICKER_RISK_DB } from '@/lib/mock-data';
import Disclaimer from '@/components/legal/Disclaimer';

const DEFAULT_RISK = { annRet: 0.12, vol: 0.22, beta: 1.00 };

interface SharedMock {
  name: string;
  weights: Record<string, number>;
}

const SandboxView = () => {
  const [params] = useSearchParams();

  const mock = useMemo<SharedMock | null>(() => {
    const encoded = params.get('mock');
    if (!encoded) return null;
    try {
      return JSON.parse(atob(encoded));
    } catch {
      return null;
    }
  }, [params]);

  if (!mock) {
    return (
      <AppLayout title="Strategy View">
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <p className="text-muted-foreground font-mono text-sm">Invalid or missing strategy link.</p>
          <Link to="/dashboard" className="text-primary font-mono text-sm hover:underline">Analyze your own portfolio →</Link>
        </div>
      </AppLayout>
    );
  }

  const tickers = Object.keys(mock.weights);
  const totalW = tickers.reduce((s, t) => s + (mock.weights[t] || 0), 0) || 1;

  let pRet = 0, pVol = 0, pBeta = 0;
  for (const t of tickers) {
    const w = (mock.weights[t] || 0) / totalW;
    const risk = TICKER_RISK_DB[t] ?? DEFAULT_RISK;
    pRet += w * risk.annRet;
    pVol += w * risk.vol;
    pBeta += w * risk.beta;
  }
  const divFactor = Math.max(0.65, 1 - (tickers.length - 1) * 0.06);
  const adjVol = pVol * divFactor;
  const sharpe = adjVol > 0 ? (pRet - 0.04) / adjVol : 0;
  const var95 = -(1.645 * adjVol / Math.sqrt(252));
  const healthScore = Math.round(
    Math.min(100, Math.max(0,
      Math.min(100, (sharpe / 2.0) * 100) * 0.40 +
      Math.min(100, Math.max(0, 100 - (Math.abs(var95) * 100 - 2) * (100 / 6))) * 0.30 +
      Math.min(100, Math.max(0, 100 - (adjVol * 100 - 10) * (100 / 30))) * 0.20 +
      (tickers.length >= 5 ? 100 : tickers.length >= 3 ? 80 : 50) * 0.10
    ))
  );

  return (
    <AppLayout title="Strategy View">
      <div className="max-w-xl mx-auto px-4 py-8">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <span className="font-mono text-xs uppercase tracking-wider text-primary">{mock.name}</span>
            <span className="font-mono text-[9px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">READ-ONLY</span>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { label: 'Health Score', value: healthScore.toString() },
              { label: 'Sharpe', value: sharpe.toFixed(2) },
              { label: 'VaR 95%', value: `${(var95 * 100).toFixed(1)}%` },
              { label: 'Beta', value: pBeta.toFixed(2) },
              { label: 'Ann. Return', value: `${(pRet * 100).toFixed(1)}%` },
              { label: 'Volatility', value: `${(adjVol * 100).toFixed(1)}%` },
            ].map(m => (
              <div key={m.label} className="glass-elevated rounded-lg p-3 text-center">
                <p className="font-mono text-[9px] text-muted-foreground uppercase mb-1">{m.label}</p>
                <p className="font-mono text-base font-bold text-foreground">{m.value}</p>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Weights</span>
            {tickers.map(t => {
              const pct = ((mock.weights[t] || 0) / totalW) * 100;
              return (
                <div key={t} className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground w-14">{t}</span>
                  <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                    <div className="h-full bg-primary rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-foreground w-10 text-right">{pct.toFixed(0)}%</span>
                </div>
              );
            })}
          </div>

          <div className="mt-8 pt-4 border-t border-border text-center">
            <p className="font-mono text-[10px] text-muted-foreground mb-3">Want to analyse your own portfolio?</p>
            <Link
              to="/dashboard"
              className="inline-block bg-primary text-primary-foreground font-mono text-xs px-6 py-2.5 rounded-lg hover:opacity-90 transition-opacity"
            >
              Analyze your own portfolio →
            </Link>
          </div>
        </motion.div>

        <Disclaimer variant="compact" />
      </div>
    </AppLayout>
  );
};

export default SandboxView;
