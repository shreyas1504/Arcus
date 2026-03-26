/**
 * PDFReportDocument — rendered off-screen, captured by html2canvas → jsPDF.
 * White background, print-friendly. Includes every section from the dashboard.
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

export interface PDFReportDocumentProps {
  tickers: string[];
  weights: number[];
  metrics: Metrics;
  pnlRows: PnlRow[];
  dateRange: string;
  dna: GoalDNA | null;
}

/* ── shared style tokens ── */
const TEAL = '#0f766e';
const BORDER = '#e2e8f0';
const MUTED = '#64748b';
const DARK = '#0f172a';
const GREEN = '#16a34a';
const AMBER = '#d97706';
const RED = '#dc2626';
const MONO = 'monospace';
const SANS = 'system-ui, sans-serif';

const cell: React.CSSProperties = {
  padding: '7px 10px', fontFamily: MONO, fontSize: 10,
  borderBottom: `1px solid ${BORDER}`, color: DARK, verticalAlign: 'middle',
};
const th: React.CSSProperties = {
  ...cell, fontSize: 8, textTransform: 'uppercase', letterSpacing: '0.08em',
  color: MUTED, background: '#f1f5f9', fontWeight: 700,
};

/* ── small reusable pieces ── */
const SectionTitle = ({ children }: { children: React.ReactNode }) => (
  <div style={{
    fontSize: 8, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.14em',
    color: TEAL, fontFamily: MONO, borderBottom: `2px solid ${TEAL}`,
    paddingBottom: 4, marginBottom: 10, marginTop: 20,
  }}>{children}</div>
);

const MetricBox = ({ label, value, sub, warn }: { label: string; value: string; sub?: string; warn?: boolean }) => (
  <div style={{
    border: `1px solid ${warn ? '#fde68a' : BORDER}`,
    borderRadius: 6, padding: '10px 12px',
    background: warn ? '#fffbeb' : '#f8fafc',
  }}>
    <div style={{ fontSize: 7.5, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: MONO, marginBottom: 3 }}>{label}</div>
    <div style={{ fontSize: 18, fontWeight: 800, color: warn ? AMBER : DARK, fontFamily: MONO, lineHeight: 1 }}>{value ?? '—'}</div>
    {sub && <div style={{ fontSize: 8, color: MUTED, marginTop: 2, fontFamily: MONO }}>{sub}</div>}
  </div>
);

const Tag = ({ ok, text }: { ok: boolean; text: string }) => (
  <span style={{
    display: 'inline-block', fontSize: 8, fontWeight: 700, padding: '2px 6px',
    borderRadius: 4, background: ok ? '#dcfce7' : '#fee2e2',
    color: ok ? GREEN : RED, fontFamily: MONO,
  }}>{text}</span>
);

/* ── main component ── */
const PDFReportDocument = ({ tickers, weights, metrics: m, pnlRows, dateRange, dna }: PDFReportDocumentProps) => {
  const safe = (n: number | undefined | null, fn: (x: number) => string) =>
    n != null && !isNaN(n) ? fn(n) : '—';

  const totalPnl = pnlRows.reduce((a, r) =>
    r.current_price != null && r.cost_basis != null
      ? a + (r.current_price - r.cost_basis) * r.shares : a, 0);

  const generatedAt = new Date().toLocaleString('en-US', { dateStyle: 'long', timeStyle: 'short' });
  const scoreColor = (m.health_score ?? 0) >= 70 ? GREEN : (m.health_score ?? 0) >= 40 ? AMBER : RED;

  const riskLabel    = dna?.risk_tolerance ?? 'Moderate';
  const targetReturn = dna?.target_return ?? 0.10;
  const userSectors  = dna?.sectors ?? [];

  const RISK_THRESHOLDS: Record<string, { maxVol: number; maxBeta: number; maxDD: number }> = {
    Conservative: { maxVol: 0.12, maxBeta: 0.8,  maxDD: -0.10 },
    Moderate:     { maxVol: 0.18, maxBeta: 1.0,  maxDD: -0.18 },
    Balanced:     { maxVol: 0.24, maxBeta: 1.2,  maxDD: -0.25 },
    Growth:       { maxVol: 0.32, maxBeta: 1.5,  maxDD: -0.35 },
    Aggressive:   { maxVol: 999,  maxBeta: 999,  maxDD: -999  },
  };
  const thresh = RISK_THRESHOLDS[riskLabel] ?? RISK_THRESHOLDS.Moderate;
  const returnOk = m.annualized_return >= targetReturn;
  const volOk    = riskLabel === 'Aggressive' || (m.volatility ?? 0) <= thresh.maxVol;
  const betaOk   = riskLabel === 'Aggressive' || (m.beta ?? 1)       <= thresh.maxBeta;
  const ddOk     = riskLabel === 'Aggressive' || (m.max_drawdown ?? 0) >= thresh.maxDD;
  const goalScore = Math.round(
    (Math.min(100, ((m.annualized_return / targetReturn) * 100)) * 0.4) +
    (([volOk, betaOk, ddOk].filter(Boolean).length / 3) * 100 * 0.3) +
    100 * 0.3
  );

  const methodology = [
    { metric: 'Sharpe Ratio',       formula: '(Return − Risk-Free Rate) / Volatility',              value: safe(m.sharpe,             n => n.toFixed(2)), note: 'Measures return per unit of total risk. >1.0 is good; >2.0 is excellent.' },
    { metric: 'Sortino Ratio',      formula: '(Return − Risk-Free Rate) / Downside Deviation',       value: safe(m.sortino,            n => n.toFixed(2)), note: 'Like Sharpe but only penalises downside volatility. Better measure for asymmetric portfolios.' },
    { metric: 'Alpha',              formula: 'Portfolio Return − (Rf + β × Market Premium)',         value: safe(m.alpha,              n => `${(n * 100).toFixed(2)}%`), note: 'Excess return above what the market risk alone would predict. Positive = outperforming.' },
    { metric: 'Information Ratio',  formula: 'Alpha / Tracking Error',                               value: safe(m.information_ratio,  n => n.toFixed(2)), note: 'Consistency of outperformance. >0.5 is strong.' },
    { metric: 'Beta',               formula: 'Cov(Portfolio, Market) / Var(Market)',                 value: safe(m.beta,               n => n.toFixed(2)), note: '1.0 = moves with market. <1 = defensive. >1 = amplified market moves.' },
    { metric: 'VaR 95%',            formula: 'Historical 5th-percentile daily return',               value: safe(m.var_95,             n => `${(n * 100).toFixed(2)}%`), note: 'Max expected daily loss on 95% of trading days.' },
    { metric: 'CVaR / Exp. Shortfall', formula: 'Mean of returns below VaR threshold',              value: safe(m.cvar_95,            n => `${(n * 100).toFixed(2)}%`), note: 'Average loss on the worst 5% of days. More conservative than VaR.' },
    { metric: 'Max Drawdown',       formula: '(Trough − Peak) / Peak',                              value: safe(m.max_drawdown,       n => `${(n * 100).toFixed(2)}%`), note: 'Worst historical peak-to-trough loss. Key indicator of downside resilience.' },
    { metric: 'Calmar Ratio',       formula: 'Annualised Return / |Max Drawdown|',                  value: safe(m.calmar,             n => n.toFixed(2)), note: 'Return earned per unit of drawdown risk. >1.0 is considered good.' },
    { metric: 'Annualised Return',  formula: '(End Value / Start Value)^(252/N) − 1',               value: safe(m.annualized_return,  n => `${(n * 100).toFixed(2)}%`), note: 'Compounded annual growth rate over the analysis period.' },
    { metric: 'Volatility',         formula: 'Annualised Std Dev of Daily Returns × √252',          value: safe(m.volatility,         n => `${(n * 100).toFixed(2)}%`), note: 'Annualised standard deviation of daily returns. Measures price dispersion.' },
    { metric: 'Health Score',       formula: 'Sharpe(40%) + VaR(25%) + Volatility(20%) + Concentration(15%)', value: `${m.health_score ?? '—'}/100`, note: 'Arcus composite quality score — integrates risk-adjusted return, tail risk, and diversification.' },
    { metric: 'Wtd Avg P/E',        formula: 'Σ(Ticker Weight × P/E Ratio)',                        value: m.weighted_pe != null ? m.weighted_pe.toFixed(1) : '—', note: 'Portfolio-level valuation multiple. Compare to S&P 500 avg (~22x) for context.' },
  ];

  const recs: { type: 'warn' | 'ok' | 'info'; title: string; body: string }[] = [];
  if (!returnOk) recs.push({ type: 'warn', title: 'Return Gap', body: `Actual return (${safe(m.annualized_return, n => (n * 100).toFixed(1))}%) is below your ${(targetReturn * 100).toFixed(0)}% target. Consider higher-growth assets or reviewing your time horizon.` });
  if (!volOk)    recs.push({ type: 'warn', title: 'Volatility Exceeded', body: `Volatility (${safe(m.volatility, n => (n * 100).toFixed(1))}%) exceeds the ${(thresh.maxVol * 100)}% limit for a ${riskLabel} profile. Diversify with lower-volatility holdings or add bond exposure.` });
  if (!betaOk)   recs.push({ type: 'warn', title: 'High Beta', body: `Beta of ${safe(m.beta, n => n.toFixed(2))} exceeds the ${thresh.maxBeta} limit. Adding defensive positions (utilities, consumer staples, bonds) would reduce market sensitivity.` });
  if (!ddOk)     recs.push({ type: 'warn', title: 'Drawdown Risk', body: `Max drawdown (${safe(m.max_drawdown, n => (n * 100).toFixed(1))}%) exceeds your ${(thresh.maxDD * 100).toFixed(0)}% comfort zone. Consider stop-loss strategies or protective puts.` });
  if ((m.sharpe ?? 0) >= 1.5) recs.push({ type: 'ok', title: 'Strong Sharpe', body: `A Sharpe of ${safe(m.sharpe, n => n.toFixed(2))} indicates excellent risk-adjusted performance. Maintain the current strategy and rebalance quarterly.` });
  if ((m.calmar ?? 0) >= 1.0) recs.push({ type: 'ok', title: 'Good Calmar Ratio', body: `Calmar ratio of ${safe(m.calmar, n => n.toFixed(2))} shows strong return relative to drawdown risk. Portfolio withstands market turbulence well.` });
  if ((m.beta ?? 1) > 1.2)   recs.push({ type: 'info', title: 'Market Amplification', body: `Beta > 1.2 means the portfolio amplifies market moves. This boosts gains in bull markets but accelerates losses in downturns. Suitable for Growth/Aggressive profiles only.` });
  if (recs.length === 0)      recs.push({ type: 'ok', title: 'Portfolio Aligned', body: 'All key metrics are within your risk tolerance and goal parameters. Continue monitoring and rebalance if any single position exceeds 30% of total weight.' });

  const recColor = { warn: { bg: '#fff1f2', border: '#fecdd3', title: RED }, ok: { bg: '#f0fdf4', border: '#bbf7d0', title: GREEN }, info: { bg: '#eff6ff', border: '#bfdbfe', title: '#2563eb' } };

  return (
    <div id="arcus-pdf-report" style={{ width: 794, background: '#fff', fontFamily: SANS, color: DARK, padding: '36px 44px', boxSizing: 'border-box' }}>

      {/* ── HEADER ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: `3px solid ${TEAL}`, paddingBottom: 16, marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 26, fontWeight: 900, color: TEAL, letterSpacing: '-0.03em', fontFamily: MONO }}>ARCUS</div>
          <div style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>Portfolio Risk & Analysis Report</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, fontFamily: MONO, fontWeight: 700 }}>{tickers.join(' · ')}</div>
          <div style={{ fontSize: 10, color: MUTED, marginTop: 2, fontFamily: MONO }}>{dateRange}</div>
          <div style={{ fontSize: 9, color: MUTED, marginTop: 2 }}>Generated {generatedAt}</div>
        </div>
      </div>

      {/* ── HEALTH SCORE BANNER ── */}
      <div style={{ background: '#f0fdf4', border: `1px solid ${TEAL}40`, borderRadius: 10, padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 18, marginBottom: 4 }}>
        <div style={{ textAlign: 'center', minWidth: 70 }}>
          <div style={{ fontSize: 40, fontWeight: 900, color: scoreColor, fontFamily: MONO, lineHeight: 1 }}>{m.health_score ?? '—'}</div>
          <div style={{ fontSize: 7.5, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: MONO }}>/ 100 Health</div>
        </div>
        <div style={{ borderLeft: `1px solid ${BORDER}`, paddingLeft: 18, flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
            {(m.health_score ?? 0) >= 70 ? 'Portfolio is healthy and well-structured.' : (m.health_score ?? 0) >= 40 ? 'Portfolio needs some attention.' : 'Portfolio has significant risk concerns.'}
          </div>
          <div style={{ fontSize: 10, color: MUTED, lineHeight: 1.5 }}>
            Annualised return <strong>{safe(m.annualized_return, n => `${(n*100).toFixed(1)}%`)}</strong> · Volatility <strong>{safe(m.volatility, n => `${(n*100).toFixed(1)}%`)}</strong> · Sharpe <strong>{safe(m.sharpe, n => n.toFixed(2))}</strong> — {(m.sharpe ?? 0) >= 1.5 ? 'excellent' : (m.sharpe ?? 0) >= 1.0 ? 'good' : 'below average'} risk-adjusted return · Max drawdown <strong>{safe(m.max_drawdown, n => `${(n*100).toFixed(1)}%`)}</strong>
          </div>
        </div>
        <div style={{ textAlign: 'right', minWidth: 100 }}>
          <div style={{ fontSize: 9, color: MUTED, fontFamily: MONO }}>Investor Profile</div>
          <div style={{ fontSize: 12, fontWeight: 700, fontFamily: MONO }}>{riskLabel}</div>
          <div style={{ fontSize: 10, color: TEAL, fontFamily: MONO }}>Target {(targetReturn * 100).toFixed(0)}% / yr</div>
          <div style={{ marginTop: 4 }}><Tag ok={goalScore >= 70} text={`Goal Score ${goalScore}`} /></div>
        </div>
      </div>

      {/* ── CORE METRICS ── */}
      <SectionTitle>Core Performance Metrics</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 7 }}>
        <MetricBox label="Sharpe Ratio"    value={safe(m.sharpe,            n => n.toFixed(2))}              sub="Risk-adj return" />
        <MetricBox label="Sortino Ratio"   value={safe(m.sortino,           n => n.toFixed(2))}              sub="Downside risk" />
        <MetricBox label="Alpha"           value={safe(m.alpha,             n => `${(n*100).toFixed(1)}%`)}  sub="vs benchmark" />
        <MetricBox label="Info Ratio"      value={safe(m.information_ratio, n => n.toFixed(2))}              sub="Consistency" />
        <MetricBox label="VaR 95%"         value={safe(m.var_95,            n => `${(n*100).toFixed(1)}%`)}  sub="Tail risk" warn={Math.abs(m.var_95 ?? 0) > 0.04} />
        <MetricBox label="CVaR 95%"        value={safe(m.cvar_95,           n => `${(n*100).toFixed(1)}%`)}  sub="Exp. shortfall" warn={Math.abs(m.cvar_95 ?? 0) > 0.06} />
        <MetricBox label="Max Drawdown"    value={safe(m.max_drawdown,      n => `${(n*100).toFixed(1)}%`)}  sub="Worst decline" warn={!ddOk} />
        <MetricBox label="Beta"            value={safe(m.beta,              n => n.toFixed(2))}              sub="Market sens." warn={!betaOk} />
        <MetricBox label="Ann. Return"     value={safe(m.annualized_return, n => `${(n*100).toFixed(1)}%`)}  sub="Per year" />
        <MetricBox label="Volatility"      value={safe(m.volatility,        n => `${(n*100).toFixed(1)}%`)}  sub="Ann. std dev" warn={!volOk} />
        <MetricBox label="Calmar Ratio"    value={safe(m.calmar,            n => n.toFixed(2))}              sub="Return/drawdown" />
        <MetricBox label="Wtd Avg P/E"     value={m.weighted_pe != null ? m.weighted_pe.toFixed(1) : '—'}    sub="Valuation" />
      </div>

      {/* ── GOAL ALIGNMENT ── */}
      {dna && (
        <>
          <SectionTitle>Goal Alignment Analysis</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: '12px 14px', background: '#f8fafc' }}>
              <div style={{ fontSize: 8, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: MONO, marginBottom: 6 }}>Target Return</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: returnOk ? GREEN : AMBER, marginBottom: 6 }}>{returnOk ? '✓ On Track' : '⚠ Below Target'}</div>
              <div style={{ fontSize: 10, color: MUTED, lineHeight: 1.7 }}>
                <div>Target: <strong style={{ color: DARK }}>{(targetReturn * 100).toFixed(0)}% / yr</strong></div>
                <div>Actual: <strong style={{ color: returnOk ? GREEN : AMBER }}>{safe(m.annualized_return, n => `${(n*100).toFixed(1)}%`)} / yr</strong></div>
                {!returnOk && <div style={{ color: RED }}>Gap: -{safe(m.annualized_return, n => ((targetReturn - n) * 100).toFixed(1))}%</div>}
              </div>
            </div>
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: '12px 14px', background: '#f8fafc' }}>
              <div style={{ fontSize: 8, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: MONO, marginBottom: 6 }}>Risk · {riskLabel}</div>
              <div style={{ fontSize: 10, color: MUTED, lineHeight: 1.8 }}>
                <div>Volatility: <strong style={{ color: volOk ? GREEN : RED }}>{safe(m.volatility, n => `${(n*100).toFixed(1)}%`)}</strong> {volOk ? '✓' : `✗ max ${(thresh.maxVol*100)}%`}</div>
                <div>Beta: <strong style={{ color: betaOk ? GREEN : RED }}>{safe(m.beta, n => n.toFixed(2))}</strong> {betaOk ? '✓' : `✗ max ${thresh.maxBeta}`}</div>
                <div>Drawdown: <strong style={{ color: ddOk ? GREEN : RED }}>{safe(m.max_drawdown, n => `${(n*100).toFixed(1)}%`)}</strong> {ddOk ? '✓' : `✗ max ${(thresh.maxDD*100)}%`}</div>
              </div>
            </div>
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: '12px 14px', background: '#f8fafc' }}>
              <div style={{ fontSize: 8, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, fontFamily: MONO, marginBottom: 6 }}>Sector Preferences</div>
              {userSectors.length > 0
                ? <div style={{ fontSize: 10, color: MUTED, lineHeight: 1.8 }}>{userSectors.map(s => <div key={s}>· {s}</div>)}</div>
                : <div style={{ fontSize: 10, color: MUTED }}>No sector preferences set.</div>}
            </div>
          </div>
        </>
      )}

      {/* ── HOLDINGS & P&L ── */}
      <SectionTitle>Holdings & Profit / Loss</SectionTitle>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>{['Ticker', 'Shares', 'Weight', 'Cost Basis', 'Current', 'P&L ($)', 'P&L (%)', 'Days'].map(h => <th key={h} style={th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {pnlRows.map((row, i) => {
            const has = row.current_price != null && row.cost_basis != null;
            const pnlD = has ? (row.current_price! - row.cost_basis!) * row.shares : null;
            const pnlP = has ? ((row.current_price! - row.cost_basis!) / row.cost_basis!) * 100 : null;
            const pos  = pnlD != null && pnlD >= 0;
            const w    = weights[i] != null ? `${(weights[i] * 100).toFixed(1)}%` : '—';
            return (
              <tr key={row.ticker} style={{ background: i % 2 === 0 ? '#fff' : '#f8fafc' }}>
                <td style={{ ...cell, fontWeight: 700, color: TEAL }}>{row.ticker}</td>
                <td style={cell}>{row.shares}</td>
                <td style={cell}>{w}</td>
                <td style={cell}>{row.cost_basis != null ? `$${row.cost_basis.toFixed(2)}` : '—'}</td>
                <td style={cell}>{row.current_price != null ? `$${row.current_price.toFixed(2)}` : '—'}</td>
                <td style={{ ...cell, fontWeight: 600, color: pnlD != null ? (pos ? GREEN : RED) : MUTED }}>
                  {pnlD != null ? `${pos ? '+' : ''}$${pnlD.toFixed(2)}` : '—'}
                </td>
                <td style={{ ...cell, color: pnlP != null ? (pos ? GREEN : RED) : MUTED }}>
                  {pnlP != null ? `${pos ? '+' : ''}${pnlP.toFixed(1)}%` : '—'}
                </td>
                <td style={cell}>{row.days ?? '—'}</td>
              </tr>
            );
          })}
          <tr style={{ borderTop: `2px solid ${DARK}`, background: '#f0fdf4' }}>
            <td style={{ ...cell, fontWeight: 800 }}>TOTAL</td>
            <td style={cell} colSpan={4} />
            <td style={{ ...cell, fontWeight: 800, color: totalPnl >= 0 ? GREEN : RED }}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
            </td>
            <td style={cell} colSpan={2} />
          </tr>
        </tbody>
      </table>

      {/* ── METHODOLOGY ── */}
      <SectionTitle>Full Report — Metric Methodology</SectionTitle>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>{['Metric', 'Formula', 'Your Value', 'Interpretation'].map(h => <th key={h} style={th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {methodology.map((r, i) => (
            <tr key={r.metric} style={{ background: i % 2 === 0 ? '#fff' : '#f8fafc' }}>
              <td style={{ ...cell, fontWeight: 700, whiteSpace: 'nowrap', width: 120 }}>{r.metric}</td>
              <td style={{ ...cell, color: MUTED, fontFamily: MONO, fontSize: 8 }}>{r.formula}</td>
              <td style={{ ...cell, fontWeight: 700, color: TEAL, whiteSpace: 'nowrap', width: 72 }}>{r.value}</td>
              <td style={{ ...cell, color: MUTED, fontSize: 9 }}>{r.note}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* ── AI ANALYSIS SUMMARY ── */}
      <SectionTitle>Full Report — AI Analysis Summary</SectionTitle>
      <div style={{ background: '#f0fdf4', border: `1px solid ${TEAL}30`, borderRadius: 8, padding: '14px 16px', fontSize: 10, lineHeight: 1.7, color: DARK }}>
        <p style={{ margin: '0 0 8px 0' }}>
          Your portfolio has a <strong>Sharpe ratio of {safe(m.sharpe, n => n.toFixed(2))}</strong>,
          indicating {(m.sharpe ?? 0) >= 1.5 ? 'excellent' : (m.sharpe ?? 0) >= 1.0 ? 'above-average' : 'below-average'} risk-adjusted returns{(m.sharpe ?? 0) >= 1.0 ? ' — you are being well-compensated for the risk taken' : '. Consider rebalancing to improve this ratio'}.
        </p>
        <p style={{ margin: '0 0 8px 0' }}>
          Annualised return of <strong>{safe(m.annualized_return, n => `${(n*100).toFixed(1)}%`)}</strong> vs your{' '}
          <strong>{(targetReturn * 100).toFixed(0)}% target</strong> — {returnOk ? 'you are on track' : 'you are below target; consider reviewing your asset allocation'}.
          Portfolio volatility of <strong>{safe(m.volatility, n => `${(n*100).toFixed(1)}%`)}</strong> is {volOk ? 'within' : 'above'} the {riskLabel.toLowerCase()} investor threshold of {(thresh.maxVol * 100)}%.
        </p>
        <p style={{ margin: '0 0 8px 0' }}>
          Beta of <strong>{safe(m.beta, n => n.toFixed(2))}</strong> — your portfolio {(m.beta ?? 1) > 1.1 ? 'amplifies market moves, which increases both gains and losses during market swings' : 'moves roughly in line with the broader market'}.
          Maximum historical drawdown of <strong>{safe(m.max_drawdown, n => `${(n*100).toFixed(1)}%`)}</strong> — {ddOk ? 'within your comfort zone' : 'exceeds your risk tolerance; consider protective strategies'}.
        </p>
        <p style={{ margin: 0 }}>
          CVaR of <strong>{safe(m.cvar_95, n => `${(n*100).toFixed(1)}%`)}</strong> means on your worst 5% of days, you could expect to lose approximately this percentage of portfolio value.
          The Calmar ratio of <strong>{safe(m.calmar, n => n.toFixed(2))}</strong> reflects {(m.calmar ?? 0) >= 1.0 ? 'strong' : 'moderate'} return earned per unit of drawdown risk taken.
        </p>
      </div>

      {/* ── RECOMMENDATIONS ── */}
      <SectionTitle>Full Report — Recommendations</SectionTitle>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {recs.map((r, i) => {
          const c = recColor[r.type];
          return (
            <div key={i} style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 6, padding: '10px 14px', fontSize: 10 }}>
              <strong style={{ color: c.title }}>{r.title}:</strong>{' '}
              <span style={{ color: DARK }}>{r.body}</span>
            </div>
          );
        })}
      </div>

      {/* ── GLOSSARY ── */}
      <SectionTitle>Glossary</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 24px' }}>
        {[
          ['Sharpe Ratio',     'Return per unit of total risk. Higher is better.'],
          ['Sortino Ratio',    'Like Sharpe, but only counts downside risk.'],
          ['Alpha',            'Excess return above market-risk-adjusted benchmark.'],
          ['Beta',             'Market sensitivity. 1.0 = moves with S&P 500.'],
          ['VaR 95%',          'Max loss expected 95% of the time on a given day.'],
          ['CVaR',             'Average loss on your very worst days (bottom 5%).'],
          ['Max Drawdown',     'Biggest historical peak-to-trough loss.'],
          ['Calmar Ratio',     'Annual return divided by max drawdown.'],
          ['Info Ratio',       'Consistency of outperformance vs benchmark.'],
          ['Health Score',     'Arcus composite quality score out of 100.'],
          ['Volatility',       'Annualised std deviation of daily returns.'],
          ['Wtd Avg P/E',      'Portfolio valuation — earnings multiple.'],
        ].map(([term, def]) => (
          <div key={term} style={{ display: 'flex', gap: 8, padding: '3px 0', borderBottom: `1px solid ${BORDER}`, fontSize: 9 }}>
            <span style={{ fontFamily: MONO, color: TEAL, fontWeight: 700, minWidth: 110 }}>{term}</span>
            <span style={{ color: MUTED }}>{def}</span>
          </div>
        ))}
      </div>

      {/* ── FOOTER ── */}
      <div style={{ marginTop: 24, paddingTop: 14, borderTop: `1px solid ${BORDER}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 8, color: MUTED }}><strong style={{ color: TEAL }}>ARCUS</strong> · Portfolio Analytics · {generatedAt}</div>
        <div style={{ fontSize: 7.5, color: MUTED, maxWidth: 360, textAlign: 'right' }}>For informational purposes only. Not investment advice. Past performance does not guarantee future results.</div>
      </div>
    </div>
  );
};

export default PDFReportDocument;
