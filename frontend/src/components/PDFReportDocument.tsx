/**
 * PDFReportDocument — off-screen component captured by html2canvas → jsPDF.
 * Rendered with a white background and print-friendly typography so the PDF
 * looks professional, not like a dark-mode screenshot.
 */

interface Metrics {
  sharpe: number; sortino: number; alpha: number; information_ratio: number;
  calmar: number; var_95: number; cvar_95: number; max_drawdown: number;
  beta: number; annualized_return: number; volatility: number;
  health_score: number; weighted_pe?: number;
}

interface PnlRow {
  ticker: string; shares: number;
  cost_basis: number | null; current_price: number | null; days?: number;
}

interface GoalDNA {
  risk_tolerance?: string; target_return?: number; sectors?: string[];
}

interface PDFReportDocumentProps {
  tickers: string[];
  weights: number[];
  metrics: Metrics;
  pnlRows: PnlRow[];
  dateRange: string;
  dna: GoalDNA | null;
}

const TEAL = '#0f766e';
const BORDER = '#e2e8f0';
const MUTED = '#64748b';
const DARK = '#0f172a';

const cell: React.CSSProperties = {
  padding: '8px 12px',
  fontFamily: 'monospace',
  fontSize: 11,
  borderBottom: `1px solid ${BORDER}`,
  color: DARK,
};

const thStyle: React.CSSProperties = {
  ...cell,
  fontSize: 9,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: MUTED,
  background: '#f8fafc',
  fontWeight: 700,
};

const MetricBox = ({ label, value, sub }: { label: string; value: string; sub?: string }) => (
  <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: '12px 14px', background: '#f8fafc', minWidth: 0 }}>
    <div style={{ fontSize: 8, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: 'monospace', marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 20, fontWeight: 800, color: DARK, fontFamily: 'monospace', lineHeight: 1 }}>{value}</div>
    {sub && <div style={{ fontSize: 9, color: MUTED, marginTop: 3, fontFamily: 'monospace' }}>{sub}</div>}
  </div>
);

const SectionTitle = ({ children }: { children: React.ReactNode }) => (
  <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em', color: TEAL, fontFamily: 'monospace', borderBottom: `2px solid ${TEAL}`, paddingBottom: 4, marginBottom: 12, marginTop: 24 }}>
    {children}
  </div>
);

const PDFReportDocument = ({ tickers, weights, metrics: m, pnlRows, dateRange, dna }: PDFReportDocumentProps) => {
  const totalPnl = pnlRows.reduce((a, r) => r.current_price != null && r.cost_basis != null ? a + (r.current_price - r.cost_basis) * r.shares : a, 0);
  const generatedAt = new Date().toLocaleString('en-US', { dateStyle: 'long', timeStyle: 'short' });

  const scoreColor = m.health_score >= 70 ? '#16a34a' : m.health_score >= 40 ? '#d97706' : '#dc2626';

  const riskLabel = dna?.risk_tolerance ?? 'Moderate';
  const targetReturn = dna?.target_return ?? 0.10;
  const userSectors = dna?.sectors ?? [];

  const RISK_THRESHOLDS: Record<string, { maxVol: number; maxBeta: number; maxDD: number }> = {
    Conservative: { maxVol: 0.12, maxBeta: 0.8, maxDD: -0.10 },
    Moderate:     { maxVol: 0.18, maxBeta: 1.0, maxDD: -0.18 },
    Balanced:     { maxVol: 0.24, maxBeta: 1.2, maxDD: -0.25 },
    Growth:       { maxVol: 0.32, maxBeta: 1.5, maxDD: -0.35 },
    Aggressive:   { maxVol: 999,  maxBeta: 999, maxDD: -999 },
  };
  const thresh = RISK_THRESHOLDS[riskLabel] ?? RISK_THRESHOLDS.Moderate;
  const returnOnTrack = m.annualized_return >= targetReturn;
  const volOk = riskLabel === 'Aggressive' || m.volatility <= thresh.maxVol;
  const betaOk = riskLabel === 'Aggressive' || (m.beta ?? 1) <= thresh.maxBeta;
  const ddOk   = riskLabel === 'Aggressive' || m.max_drawdown >= thresh.maxDD;

  const methodologyRows = [
    { metric: 'Sharpe Ratio', formula: '(Return − Risk-Free Rate) / Volatility', value: m.sharpe.toFixed(2), note: 'Above 1.0 is considered good.' },
    { metric: 'Sortino Ratio', formula: '(Return − Risk-Free Rate) / Downside Deviation', value: m.sortino.toFixed(2), note: 'Like Sharpe but only penalises downside risk.' },
    { metric: 'Alpha', formula: 'Portfolio Return − (Risk-Free + Beta × Market Premium)', value: `${(m.alpha * 100).toFixed(2)}%`, note: 'Positive alpha = outperforming the market on a risk-adjusted basis.' },
    { metric: 'Information Ratio', formula: 'Alpha / Tracking Error', value: m.information_ratio.toFixed(2), note: 'Consistency of outperformance relative to benchmark.' },
    { metric: 'Beta', formula: 'Cov(Portfolio, Market) / Var(Market)', value: (m.beta ?? 1).toFixed(2), note: '1.0 moves with market; <1 defensive; >1 amplified.' },
    { metric: 'VaR 95%', formula: 'Historical 5th-percentile daily return', value: `${(m.var_95 * 100).toFixed(2)}%`, note: 'Max expected loss on 95% of trading days.' },
    { metric: 'CVaR 95%', formula: 'Mean of returns below VaR threshold', value: `${(m.cvar_95 * 100).toFixed(2)}%`, note: 'Average loss on worst 5% of days.' },
    { metric: 'Max Drawdown', formula: '(Trough − Peak) / Peak', value: `${(m.max_drawdown * 100).toFixed(2)}%`, note: 'Worst historical peak-to-trough decline.' },
    { metric: 'Calmar Ratio', formula: 'Annualised Return / |Max Drawdown|', value: m.calmar.toFixed(2), note: 'Return earned per unit of drawdown risk.' },
    { metric: 'Health Score', formula: 'Sharpe (40%) + VaR (25%) + Volatility (20%) + Concentration (15%)', value: `${m.health_score}/100`, note: 'Arcus composite portfolio quality score.' },
  ];

  return (
    <div id="arcus-pdf-report" style={{ width: 794, background: '#ffffff', fontFamily: 'system-ui, sans-serif', color: DARK, padding: '40px 48px', boxSizing: 'border-box' }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, borderBottom: `3px solid ${TEAL}`, paddingBottom: 20 }}>
        <div>
          <div style={{ fontSize: 28, fontWeight: 900, color: TEAL, letterSpacing: '-0.03em', fontFamily: 'monospace' }}>ARCUS</div>
          <div style={{ fontSize: 13, color: MUTED, marginTop: 2 }}>Portfolio Risk & Analysis Report</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, fontFamily: 'monospace', color: DARK, fontWeight: 700 }}>{tickers.join(' · ')}</div>
          <div style={{ fontSize: 10, color: MUTED, marginTop: 2, fontFamily: 'monospace' }}>{dateRange}</div>
          <div style={{ fontSize: 9, color: MUTED, marginTop: 2 }}>Generated {generatedAt}</div>
        </div>
      </div>

      {/* ── Health Score banner ── */}
      <div style={{ background: '#f0fdf4', border: `1px solid ${TEAL}30`, borderRadius: 10, padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 20, marginBottom: 4 }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 42, fontWeight: 900, color: scoreColor, fontFamily: 'monospace', lineHeight: 1 }}>{m.health_score}</div>
          <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: 'monospace' }}>Health Score / 100</div>
        </div>
        <div style={{ borderLeft: `1px solid ${BORDER}`, paddingLeft: 20, flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: DARK, marginBottom: 4 }}>
            {m.health_score >= 70 ? 'Portfolio is healthy and well-structured.' : m.health_score >= 40 ? 'Portfolio needs some attention.' : 'Portfolio has significant risk concerns.'}
          </div>
          <div style={{ fontSize: 11, color: MUTED, lineHeight: 1.5 }}>
            Annualised return of <strong>{(m.annualized_return * 100).toFixed(1)}%</strong> with volatility of <strong>{(m.volatility * 100).toFixed(1)}%</strong>.
            Sharpe ratio of <strong>{m.sharpe.toFixed(2)}</strong> — {m.sharpe >= 1.5 ? 'excellent' : m.sharpe >= 1.0 ? 'good' : 'below average'} risk-adjusted return.
            Maximum drawdown of <strong>{(m.max_drawdown * 100).toFixed(1)}%</strong>.
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 10, color: MUTED, fontFamily: 'monospace' }}>Investor Profile</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: DARK, fontFamily: 'monospace' }}>{riskLabel}</div>
          <div style={{ fontSize: 10, color: TEAL, fontFamily: 'monospace' }}>Target: {(targetReturn * 100).toFixed(0)}% / yr</div>
        </div>
      </div>

      {/* ── Core Metrics Grid ── */}
      <SectionTitle>Core Performance Metrics</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 4 }}>
        <MetricBox label="Sharpe Ratio"    value={m.sharpe.toFixed(2)}                         sub="Risk-adj return" />
        <MetricBox label="Sortino Ratio"   value={m.sortino.toFixed(2)}                        sub="Downside risk" />
        <MetricBox label="Alpha"           value={`${(m.alpha * 100).toFixed(1)}%`}            sub="vs benchmark" />
        <MetricBox label="Info Ratio"      value={m.information_ratio.toFixed(2)}              sub="Consistency" />
        <MetricBox label="VaR 95%"         value={`${(m.var_95 * 100).toFixed(1)}%`}           sub="Daily tail risk" />
        <MetricBox label="CVaR 95%"        value={`${(m.cvar_95 * 100).toFixed(1)}%`}          sub="Expected shortfall" />
        <MetricBox label="Max Drawdown"    value={`${(m.max_drawdown * 100).toFixed(1)}%`}     sub="Worst decline" />
        <MetricBox label="Beta"            value={(m.beta ?? 1).toFixed(2)}                    sub="Market sensitivity" />
        <MetricBox label="Ann. Return"     value={`${(m.annualized_return * 100).toFixed(1)}%`} sub="Per year" />
        <MetricBox label="Volatility"      value={`${(m.volatility * 100).toFixed(1)}%`}       sub="Ann. std dev" />
        <MetricBox label="Calmar Ratio"    value={m.calmar.toFixed(2)}                         sub="Return / drawdown" />
        <MetricBox label="Wtd Avg P/E"     value={m.weighted_pe != null ? m.weighted_pe.toFixed(1) : '—'} sub="Valuation" />
      </div>

      {/* ── Goal Alignment ── */}
      {dna && (
        <>
          <SectionTitle>Goal Alignment</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            {/* Target Return */}
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: '12px 14px', background: '#f8fafc' }}>
              <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: 'monospace', marginBottom: 6 }}>Target Return</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: returnOnTrack ? '#16a34a' : '#d97706' }}>{returnOnTrack ? '✓ On Track' : '⚠ Below Target'}</div>
              <div style={{ marginTop: 6, fontSize: 10, color: MUTED }}>
                <div>Target: <strong style={{ color: DARK }}>{(targetReturn * 100).toFixed(0)}% / yr</strong></div>
                <div>Actual: <strong style={{ color: returnOnTrack ? '#16a34a' : '#d97706' }}>{(m.annualized_return * 100).toFixed(1)}% / yr</strong></div>
                {!returnOnTrack && <div style={{ color: '#dc2626', marginTop: 2 }}>Gap: -{((targetReturn - m.annualized_return) * 100).toFixed(1)}%</div>}
              </div>
            </div>
            {/* Risk Tolerance */}
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: '12px 14px', background: '#f8fafc' }}>
              <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: 'monospace', marginBottom: 6 }}>Risk · {riskLabel}</div>
              <div style={{ fontSize: 10, color: MUTED, lineHeight: 1.8 }}>
                <div>Volatility: <strong style={{ color: volOk ? '#16a34a' : '#dc2626' }}>{(m.volatility * 100).toFixed(1)}%</strong> {volOk ? '✓' : `✗ (max ${(thresh.maxVol * 100)}%)`}</div>
                <div>Beta: <strong style={{ color: betaOk ? '#16a34a' : '#dc2626' }}>{(m.beta ?? 1).toFixed(2)}</strong> {betaOk ? '✓' : `✗ (max ${thresh.maxBeta})`}</div>
                <div>Drawdown: <strong style={{ color: ddOk ? '#16a34a' : '#dc2626' }}>{(m.max_drawdown * 100).toFixed(1)}%</strong> {ddOk ? '✓' : `✗ (max ${(thresh.maxDD * 100)}%)`}</div>
              </div>
            </div>
            {/* Sector */}
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: '12px 14px', background: '#f8fafc' }}>
              <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: 'monospace', marginBottom: 6 }}>Sector Preferences</div>
              {userSectors.length > 0 ? (
                <div style={{ fontSize: 10, color: MUTED, lineHeight: 1.8 }}>
                  {userSectors.map(s => <div key={s}>· {s}</div>)}
                </div>
              ) : (
                <div style={{ fontSize: 10, color: MUTED }}>No sector preferences set.</div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ── Portfolio Holdings & P&L ── */}
      <SectionTitle>Holdings & Profit / Loss</SectionTitle>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
        <thead>
          <tr>
            {['Ticker', 'Shares', 'Weight', 'Cost Basis', 'Current Price', 'P&L ($)', 'P&L (%)', 'Days Held'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pnlRows.map((row, i) => {
            const hasPnl = row.current_price != null && row.cost_basis != null;
            const pnlD = hasPnl ? (row.current_price! - row.cost_basis!) * row.shares : null;
            const pnlP = hasPnl ? ((row.current_price! - row.cost_basis!) / row.cost_basis!) * 100 : null;
            const pos = pnlD != null && pnlD >= 0;
            const w = weights[i] != null ? `${(weights[i] * 100).toFixed(1)}%` : '—';
            return (
              <tr key={row.ticker} style={{ background: i % 2 === 0 ? '#ffffff' : '#f8fafc' }}>
                <td style={{ ...cell, fontWeight: 700, color: TEAL }}>{row.ticker}</td>
                <td style={cell}>{row.shares}</td>
                <td style={cell}>{w}</td>
                <td style={cell}>{row.cost_basis != null ? `$${row.cost_basis.toFixed(2)}` : '—'}</td>
                <td style={cell}>{row.current_price != null ? `$${row.current_price.toFixed(2)}` : '—'}</td>
                <td style={{ ...cell, color: pnlD != null ? (pos ? '#16a34a' : '#dc2626') : MUTED, fontWeight: 600 }}>
                  {pnlD != null ? `${pos ? '+' : ''}$${pnlD.toFixed(2)}` : '—'}
                </td>
                <td style={{ ...cell, color: pnlP != null ? (pos ? '#16a34a' : '#dc2626') : MUTED }}>
                  {pnlP != null ? `${pos ? '+' : ''}${pnlP.toFixed(1)}%` : '—'}
                </td>
                <td style={cell}>{row.days ?? '—'}</td>
              </tr>
            );
          })}
          <tr style={{ borderTop: `2px solid ${DARK}`, background: '#f0fdf4' }}>
            <td style={{ ...cell, fontWeight: 800 }}>TOTAL</td>
            <td style={cell} colSpan={4} />
            <td style={{ ...cell, fontWeight: 800, color: totalPnl >= 0 ? '#16a34a' : '#dc2626' }}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
            </td>
            <td style={cell} colSpan={2} />
          </tr>
        </tbody>
      </table>

      {/* ── Methodology ── */}
      <SectionTitle>Metric Methodology</SectionTitle>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
        <thead>
          <tr>
            {['Metric', 'Formula', 'Your Value', 'Interpretation'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {methodologyRows.map((r, i) => (
            <tr key={r.metric} style={{ background: i % 2 === 0 ? '#ffffff' : '#f8fafc' }}>
              <td style={{ ...cell, fontWeight: 700, whiteSpace: 'nowrap' }}>{r.metric}</td>
              <td style={{ ...cell, color: MUTED, fontFamily: 'monospace', fontSize: 9 }}>{r.formula}</td>
              <td style={{ ...cell, fontWeight: 700, color: TEAL, whiteSpace: 'nowrap' }}>{r.value}</td>
              <td style={{ ...cell, color: MUTED }}>{r.note}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* ── Recommendations ── */}
      <SectionTitle>Key Recommendations</SectionTitle>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {!returnOnTrack && (
          <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, padding: '10px 14px', fontSize: 11 }}>
            <strong style={{ color: '#d97706' }}>Return Gap:</strong> Portfolio return ({(m.annualized_return * 100).toFixed(1)}%) is below your {(targetReturn * 100).toFixed(0)}% target. Consider higher-growth assets or reviewing the time horizon.
          </div>
        )}
        {!volOk && (
          <div style={{ background: '#fff1f2', border: '1px solid #fecdd3', borderRadius: 6, padding: '10px 14px', fontSize: 11 }}>
            <strong style={{ color: '#dc2626' }}>Volatility Exceeded:</strong> Volatility ({(m.volatility * 100).toFixed(1)}%) exceeds the {(thresh.maxVol * 100)}% limit for a {riskLabel} profile. Diversify with lower-volatility holdings.
          </div>
        )}
        {!ddOk && (
          <div style={{ background: '#fff1f2', border: '1px solid #fecdd3', borderRadius: 6, padding: '10px 14px', fontSize: 11 }}>
            <strong style={{ color: '#dc2626' }}>Drawdown Risk:</strong> Max drawdown ({(m.max_drawdown * 100).toFixed(1)}%) exceeds the {(thresh.maxDD * 100).toFixed(0)}% comfort zone. Consider stop-loss strategies or defensive rebalancing.
          </div>
        )}
        {m.sharpe >= 1.5 && (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 6, padding: '10px 14px', fontSize: 11 }}>
            <strong style={{ color: '#16a34a' }}>Strong Sharpe:</strong> A Sharpe of {m.sharpe.toFixed(2)} indicates excellent risk-adjusted performance. Maintain current strategy.
          </div>
        )}
        {m.beta != null && m.beta > 1.2 && (
          <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, padding: '10px 14px', fontSize: 11 }}>
            <strong style={{ color: '#d97706' }}>High Beta:</strong> Beta of {m.beta.toFixed(2)} amplifies market moves. Adding defensive assets (bonds, low-beta ETFs) would reduce market sensitivity.
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <div style={{ marginTop: 32, paddingTop: 16, borderTop: `1px solid ${BORDER}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 9, color: MUTED }}>
          <strong style={{ color: TEAL }}>ARCUS</strong> · Portfolio Analytics · Generated {generatedAt}
        </div>
        <div style={{ fontSize: 8, color: MUTED, maxWidth: 340, textAlign: 'right' }}>
          This report is for informational purposes only and does not constitute investment advice. Past performance does not guarantee future results.
        </div>
      </div>
    </div>
  );
};

export default PDFReportDocument;
