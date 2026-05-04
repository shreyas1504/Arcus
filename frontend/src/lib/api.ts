import { TICKER_SECTOR_MAP } from '@/lib/mock-data';

// In production (Vercel / GitHub Pages), use Render backend; locally, use localhost
const BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://arcus-backend.onrender.com';

// ── Types ────────────────────────────────────────────────────────────────
export interface PortfolioRequest {
  tickers: string[];
  weights: number[];
  start_date: string;
  end_date: string;
  risk_free_rate?: number;
  benchmark?: string;
}

export interface MonteCarloRequest extends PortfolioRequest {
  n_days: number;
  n_simulations: number;
  initial_value: number;
}

// ── Helpers ──────────────────────────────────────────────────────────────
async function post(path: string, body: object) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new Error(`${path} failed: ${res.status} — ${text}`);
  }
  return res.json();
}

async function get(path: string) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

// ── Portfolio endpoints (v2 adapter) ─────────────────────────────────────
export const analyzePortfolio = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/analyze', req);

export const optimizePortfolio = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/optimize', req);

export const runMonteCarlo = (req: MonteCarloRequest) =>
  post('/api/v2/portfolio/monte-carlo', req);

export const runStressTest = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/stress-test', req);

export const getEfficientFrontier = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/efficient-frontier', req);

export const getRecommendations = (req: PortfolioRequest) =>
  post('/api/v2/portfolio/recommendations', req);

// ── Non-portfolio endpoints ──────────────────────────────────────────────
export const getMarketNews = () => get('/api/news/market');

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatPortfolioContext {
  holdings: { ticker: string; weight: number; currentPrice: number }[];
  metrics: {
    healthScore: number; sharpe: number; var95: number;
    cvar: number; beta: number; maxDrawdown: number;
    annualizedReturn?: number; volatility?: number;
    sortino?: number; alpha?: number;
  };
  investorProfile: { riskTolerance: string; targetReturn: number };
}

type ChatContextLike = ChatPortfolioContext | Record<string, unknown> | undefined;

export const sendChatMessage = async (
  message: string,
  portfolioContext?: ChatPortfolioContext | object,
  conversationHistory: ChatMessage[] = [],
): Promise<{ reply: string; fallback?: boolean; status503?: boolean }> => {
  try {
    // Chat goes to Vercel serverless function (same origin, always available)
    // Falls back to Render backend, then offline responses
    const chatEndpoints = [
      '/api/chat',              // Vercel serverless function (primary)
      `${BASE}/api/chat`,       // Render backend (fallback)
    ];

    let lastError: Error | null = null;
    let saw503 = false;

    for (const endpoint of chatEndpoints) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message,
            portfolio_context: portfolioContext,
            conversation_history: conversationHistory,
          }),
        });

        if (res.status === 503) {
          // This endpoint's AI is unavailable, try next
          saw503 = true;
          lastError = new Error('503');
          continue;
        }

        if (!res.ok) {
          lastError = new Error(`Chat failed: ${res.status}`);
          continue;
        }

        const data = await res.json();
        if (data.fallback && data.error) {
          // Server returned a fallback signal, try next endpoint
          lastError = new Error(data.error);
          continue;
        }

        return data;
      } catch (err) {
        lastError = err as Error;
        continue; // Try next endpoint
      }
    }

    // All endpoints failed — use offline fallback
    return { reply: getOfflineResponse(message, portfolioContext), fallback: true, status503: saw503 };
  } catch (err) {
    return { reply: getOfflineResponse(message, portfolioContext), fallback: true };
  }
};

export const getPopularTickers = () => get('/api/v2/portfolio/popular-tickers');

export const getDemoPortfolios = () => get('/api/v2/portfolio/demo-portfolios');

export const getSentiment = (ticker: string) => get(`/api/news/sentiment/${ticker}`);

// ── Stock price endpoint ─────────────────────────────────────────────────
export async function getStockPrice(ticker: string) {
  const res = await fetch(`${BASE}/api/portfolio/stock/${ticker}`);
  if (!res.ok) throw new Error('Price unavailable');
  const data = await res.json();
  return {
    ticker,
    price: data.current_price ?? data.price ?? 0,
    change: data.change ?? 0,
    changePercent: data.change_percent ?? 0,
    name: data.name ?? ticker,
  };
}

function normalizeChatContext(portfolioContext?: ChatContextLike): ChatPortfolioContext | null {
  if (!portfolioContext || typeof portfolioContext !== 'object') return null;
  const raw = portfolioContext as Record<string, any>;
  const holdingsRaw = Array.isArray(raw.holdings) ? raw.holdings : [];
  const metricsRaw = raw.metrics && typeof raw.metrics === 'object' ? raw.metrics : {};
  const investorRaw = raw.investorProfile && typeof raw.investorProfile === 'object' ? raw.investorProfile : {};

  const holdings = holdingsRaw
    .filter((holding) => holding && typeof holding === 'object' && holding.ticker)
    .map((holding) => ({
      ticker: String(holding.ticker).toUpperCase(),
      weight: Number(holding.weight) || 0,
      currentPrice: Number(holding.currentPrice) || 0,
    }));

  return {
    holdings,
    metrics: {
      healthScore: Number(metricsRaw.healthScore) || 0,
      sharpe: Number(metricsRaw.sharpe) || 0,
      var95: Number(metricsRaw.var95) || 0,
      cvar: Number(metricsRaw.cvar) || 0,
      beta: Number(metricsRaw.beta) || 0,
      maxDrawdown: Number(metricsRaw.maxDrawdown) || 0,
      annualizedReturn: metricsRaw.annualizedReturn != null ? Number(metricsRaw.annualizedReturn) : undefined,
      volatility: metricsRaw.volatility != null ? Number(metricsRaw.volatility) : undefined,
      sortino: metricsRaw.sortino != null ? Number(metricsRaw.sortino) : undefined,
      alpha: metricsRaw.alpha != null ? Number(metricsRaw.alpha) : undefined,
    },
    investorProfile: {
      riskTolerance: String(investorRaw.riskTolerance || 'Moderate'),
      targetReturn: Number(investorRaw.targetReturn) || 0.10,
    },
  };
}

function extractMetricFromMessage(message: string, patterns: RegExp[], isPercent = false): number | undefined {
  for (const pattern of patterns) {
    const match = message.match(pattern);
    if (!match) continue;
    const value = Number(match[1]);
    if (Number.isNaN(value)) continue;
    return isPercent ? value / 100 : value;
  }
  return undefined;
}

function withMessageDerivedMetrics(message: string, ctx: ChatPortfolioContext): ChatPortfolioContext {
  const derived = {
    sortino: ctx.metrics.sortino ?? extractMetricFromMessage(message, [
      /sortino ratio is\s*(-?\d+(?:\.\d+)?)/i,
      /sortino(?: ratio)?[:\s]+(-?\d+(?:\.\d+)?)/i,
    ]),
    sharpe: ctx.metrics.sharpe || extractMetricFromMessage(message, [
      /sharpe ratio is\s*(-?\d+(?:\.\d+)?)/i,
      /sharpe(?: ratio)?[:\s]+(-?\d+(?:\.\d+)?)/i,
    ]) || 0,
    beta: ctx.metrics.beta || extractMetricFromMessage(message, [
      /beta is\s*(-?\d+(?:\.\d+)?)/i,
      /beta[:\s]+(-?\d+(?:\.\d+)?)/i,
    ]) || 0,
    alpha: ctx.metrics.alpha ?? extractMetricFromMessage(message, [
      /alpha is\s*(-?\d+(?:\.\d+)?)%/i,
      /alpha[:\s]+(-?\d+(?:\.\d+)?)%/i,
    ], true),
    annualizedReturn: ctx.metrics.annualizedReturn ?? extractMetricFromMessage(message, [
      /annualized return is\s*(-?\d+(?:\.\d+)?)%/i,
      /annualized return[:\s]+(-?\d+(?:\.\d+)?)%/i,
    ], true),
    volatility: ctx.metrics.volatility ?? extractMetricFromMessage(message, [
      /volatility is\s*(-?\d+(?:\.\d+)?)%/i,
      /portfolio volatility is\s*(-?\d+(?:\.\d+)?)%/i,
      /volatility[:\s]+(-?\d+(?:\.\d+)?)%/i,
    ], true),
    var95: ctx.metrics.var95 || extractMetricFromMessage(message, [
      /var(?: at 95%)? is\s*(-?\d+(?:\.\d+)?)%/i,
      /value at risk(?: \(?95%?\)?)? is\s*(-?\d+(?:\.\d+)?)%/i,
    ], true) || 0,
    cvar: ctx.metrics.cvar || extractMetricFromMessage(message, [
      /cvar is\s*(-?\d+(?:\.\d+)?)%/i,
      /expected shortfall is\s*(-?\d+(?:\.\d+)?)%/i,
    ], true) || 0,
    maxDrawdown: ctx.metrics.maxDrawdown || extractMetricFromMessage(message, [
      /maximum drawdown is\s*(-?\d+(?:\.\d+)?)%/i,
      /max drawdown is\s*(-?\d+(?:\.\d+)?)%/i,
    ], true) || 0,
    healthScore: ctx.metrics.healthScore || extractMetricFromMessage(message, [
      /health score is\s*(\d+(?:\.\d+)?)/i,
      /health score[:\s]+(\d+(?:\.\d+)?)/i,
    ]) || 0,
  };

  return {
    ...ctx,
    metrics: {
      ...ctx.metrics,
      ...derived,
    },
  };
}

function fmtPct(value?: number, digits = 1) {
  if (value == null || Number.isNaN(value)) return 'n/a';
  return `${(value * 100).toFixed(digits)}%`;
}

function fmtNum(value?: number, digits = 2) {
  if (value == null || Number.isNaN(value)) return 'n/a';
  return value.toFixed(digits);
}

function topHoldingsSummary(ctx: ChatPortfolioContext) {
  return [...ctx.holdings]
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 3)
    .map((holding) => `${holding.ticker} ${fmtPct(holding.weight, 0)}`)
    .join(', ');
}

function topSectorSummary(ctx: ChatPortfolioContext) {
  const sectors = ctx.holdings.reduce<Record<string, number>>((acc, holding) => {
    const sector = TICKER_SECTOR_MAP[holding.ticker] ?? 'Other';
    acc[sector] = (acc[sector] || 0) + holding.weight;
    return acc;
  }, {});
  const [topSector, topWeight] = Object.entries(sectors).sort((a, b) => b[1] - a[1])[0] || ['Other', 0];
  return { topSector, topWeight };
}

function findTickerInMessage(message: string, ctx: ChatPortfolioContext) {
  const words = message.toUpperCase().match(/[A-Z]{1,6}/g) || [];
  return ctx.holdings.find((holding) => words.includes(holding.ticker));
}

function concentrationRiskLine(ctx: ChatPortfolioContext) {
  const topHolding = [...ctx.holdings].sort((a, b) => b.weight - a.weight)[0];
  if (!topHolding) return 'No holdings are available in the current portfolio context.';
  if (topHolding.weight >= 0.35) {
    return `Your biggest concentration risk is **${topHolding.ticker}** at roughly ${fmtPct(topHolding.weight, 0)} of the portfolio.`;
  }
  return `Your largest holding is **${topHolding.ticker}** at about ${fmtPct(topHolding.weight, 0)}, which is not extreme on its own but is still the first position to watch.`;
}

function buildSummaryResponse(ctx: ChatPortfolioContext) {
  const { topSector, topWeight } = topSectorSummary(ctx);
  const healthBand = ctx.metrics.healthScore >= 70 ? 'healthy' : ctx.metrics.healthScore >= 40 ? 'mixed' : 'fragile';
  return [
    `**Current Portfolio Summary**`,
    ``,
    `- Health Score: **${Math.round(ctx.metrics.healthScore)}/100** (${healthBand})`,
    `- Sharpe: **${fmtNum(ctx.metrics.sharpe)}**`,
    `- Annualized Return: **${fmtPct(ctx.metrics.annualizedReturn)}**`,
    `- Volatility: **${fmtPct(ctx.metrics.volatility)}**`,
    `- Beta: **${fmtNum(ctx.metrics.beta)}**`,
    `- Top holdings: **${topHoldingsSummary(ctx) || 'n/a'}**`,
    `- Largest sector tilt: **${topSector} ${fmtPct(topWeight, 0)}**`,
    ``,
    `Main takeaway: ${concentrationRiskLine(ctx).replace(/^Your /, 'your ')}`,
    ``,
    `Next step: ask which metric or holding you want to drill into first.`,
  ].join('\n');
}

function buildMetricResponse(message: string, ctx: ChatPortfolioContext) {
  const msg = message.toLowerCase();
  const hydratedCtx = withMessageDerivedMetrics(message, ctx);
  const { metrics } = hydratedCtx;
  const { topSector, topWeight } = topSectorSummary(hydratedCtx);
  const matchedHolding = findTickerInMessage(message, hydratedCtx);

  if (msg.includes('summary') || msg.includes('overview') || msg.includes('current portfolio')) {
    return buildSummaryResponse(hydratedCtx);
  }

  if (matchedHolding) {
    const sector = TICKER_SECTOR_MAP[matchedHolding.ticker] ?? 'Other';
    const concentrationView = matchedHolding.weight >= 0.2 ? 'one of your key exposures' : 'a smaller supporting position';
    return `**${matchedHolding.ticker} Snapshot**\n\n- **${matchedHolding.ticker}** is about **${fmtPct(matchedHolding.weight, 0)}** of your portfolio, which makes it ${concentrationView}.\n- Sector: **${sector}**\n- Current price in context: **$${fmtNum(matchedHolding.currentPrice)}**\n- If you are asking about risk, compare this holding against portfolio beta **${fmtNum(metrics.beta)}** and volatility **${fmtPct(metrics.volatility)}**.\n\nNext step: ask whether you should trim, hold, or add to ${matchedHolding.ticker}.`;
  }

  if (msg.includes('suggest') || msg.includes('recommend') || msg.includes('what should i do')) {
    return `**Suggestions Based on Current Portfolio**\n\n- ${concentrationRiskLine(hydratedCtx)}\n- Your health score is **${Math.round(metrics.healthScore)}/100**, with Sharpe **${fmtNum(metrics.sharpe)}** and volatility **${fmtPct(metrics.volatility)}**.\n- The clearest first action is usually trimming the biggest concentration source and adding a lower-correlation holding if your goal is smoother risk-adjusted returns.\n\nNext step: ask for 3 specific portfolio changes and I’ll suggest them in order.`;
  }

  if (msg.includes('sharpe')) {
    const verdict = metrics.sharpe >= 1.5 ? 'strong' : metrics.sharpe >= 1 ? 'decent' : metrics.sharpe >= 0 ? 'weak' : 'poor';
    return `**Sharpe Ratio**\n\n- Your Sharpe is **${fmtNum(metrics.sharpe)}**, which is a **${verdict}** level of risk-adjusted return.\n- This means the portfolio is generating ${verdict === 'poor' ? 'too little' : 'a reasonable amount of'} return for the volatility it takes.\n- With annualized return **${fmtPct(metrics.annualizedReturn)}** and volatility **${fmtPct(metrics.volatility)}**, the main way to improve Sharpe is usually trimming concentrated high-volatility exposure.\n\nNext step: ask which holding is hurting Sharpe the most.`;
  }

  if (msg.includes('sortino')) {
    return `**Sortino Ratio**\n\n- Your Sortino ratio is **${fmtNum(metrics.sortino)}**.\n- Sortino focuses only on downside volatility, so it tells you how efficiently the portfolio is handling bad risk rather than all volatility.\n- If Sortino is materially better than Sharpe, upside swings are not the main issue; downside protection is holding up better.\n\nNext step: compare Sortino and Sharpe together to see whether downside risk is your main problem.`;
  }

  if (msg.includes('alpha')) {
    return `**Alpha**\n\n- Your portfolio alpha is **${fmtPct(metrics.alpha)}**.\n- Positive alpha means you have outperformed what your market exposure alone would suggest; negative alpha means the portfolio has lagged that hurdle.\n- Read this alongside beta **${fmtNum(metrics.beta)}** so you separate stock selection from plain market risk.\n\nNext step: ask whether the alpha looks persistent or just market-driven.`;
  }

  if (msg.includes('information ratio')) {
    return `**Information Ratio**\n\n- Your information ratio is **${fmtNum((hydratedCtx.metrics as any).informationRatio ?? (hydratedCtx.metrics as any).information_ratio)}**.\n- This measures how consistently the portfolio has outperformed its benchmark per unit of tracking error.\n- Higher is better; low or negative values mean excess return has not been especially reliable.\n\nNext step: compare it against alpha to judge consistency versus magnitude.`;
  }

  if (msg.includes('var') || msg.includes('value at risk')) {
    return `**Value at Risk (95%)**\n\n- Your VaR is **${fmtPct(metrics.var95)}**.\n- In plain terms, on a rough day in the worst 5% range, the portfolio can reasonably lose around that amount or more.\n- Your CVaR is **${fmtPct(metrics.cvar)}**, which is the average of those worst outcomes and gives the better tail-risk read.\n\nNext step: ask which holdings are driving tail risk the most.`;
  }

  if (msg.includes('cvar') || msg.includes('expected shortfall')) {
    return `**CVaR / Expected Shortfall**\n\n- Your CVaR is **${fmtPct(metrics.cvar)}**.\n- CVaR looks beyond the VaR cutoff and estimates the average loss on the worst days, so it is the better measure of extreme downside.\n- Since your VaR is **${fmtPct(metrics.var95)}**, the gap between VaR and CVaR shows how nasty the tail gets once losses move beyond the initial threshold.\n\nNext step: ask whether your tail risk is acceptable for a ${hydratedCtx.investorProfile.riskTolerance.toLowerCase()} investor.`;
  }

  if (msg.includes('drawdown')) {
    return `**Maximum Drawdown**\n\n- Your max drawdown is **${fmtPct(metrics.maxDrawdown)}**.\n- That is the deepest peak-to-trough loss the portfolio profile implies, and it is the best gut-check for how painful a bad stretch can feel.\n- Pair it with beta **${fmtNum(metrics.beta)}** and volatility **${fmtPct(metrics.volatility)}** to judge whether the portfolio is taking more pain than you want.\n\nNext step: ask how to reduce drawdown without killing return.`;
  }

  if (msg.includes('beta') || msg.includes('market risk')) {
    const betaView = metrics.beta > 1.2 ? 'more sensitive to market swings than the market itself' : metrics.beta < 0.9 ? 'more defensive than the market' : 'moving broadly in line with the market';
    return `**Beta**\n\n- Your beta is **${fmtNum(metrics.beta)}**.\n- That means the portfolio is **${betaView}**.\n- If the market drops sharply, higher-beta holdings usually do the most damage first.\n\nNext step: ask which positions are likely pushing beta up.`;
  }

  if (msg.includes('volatility')) {
    return `**Volatility**\n\n- Your annualized volatility is **${fmtPct(metrics.volatility)}**.\n- That is the size of the portfolio’s typical swings over time, not the direction.\n- Combined with Sharpe **${fmtNum(metrics.sharpe)}**, this tells you whether the swings are being rewarded well enough.\n\nNext step: ask whether your volatility is high or low for a ${hydratedCtx.investorProfile.riskTolerance.toLowerCase()} investor.`;
  }

  if (msg.includes('calmar')) {
    return `**Calmar Ratio**\n\n- Your Calmar ratio is **${fmtNum((ctx.metrics as any).calmar ?? (ctx.metrics as any).calmar_ratio)}**.\n- Calmar compares return to maximum drawdown, so it is useful when you care more about deep losses than about day-to-day noise.\n- If Calmar is weak while return looks fine, the portfolio may be earning return in an uncomfortably painful way.\n\nNext step: compare Calmar with Sharpe to see whether drawdowns are the main weakness.`;
  }

  if (msg.includes('annualized return') || msg.includes('return')) {
    return `**Annualized Return**\n\n- Your annualized return is **${fmtPct(metrics.annualizedReturn)}** versus a target of **${fmtPct(hydratedCtx.investorProfile.targetReturn)}**.\n- That means you are ${metrics.annualizedReturn != null && metrics.annualizedReturn >= hydratedCtx.investorProfile.targetReturn ? 'meeting or beating' : 'below'} your stated return target.\n- The key question is whether that return is coming with acceptable risk, which is where Sharpe **${fmtNum(metrics.sharpe)}** and drawdown **${fmtPct(metrics.maxDrawdown)}** matter.\n\nNext step: ask whether the return is strong enough for the risk you are taking.`;
  }

  if (msg.includes('p/e') || msg.includes('overvalued') || msg.includes('valuation')) {
    return `**Valuation View**\n\n- I can comment on valuation only if weighted valuation metrics are available in the current analysis.\n- From the portfolio context I have here, the stronger practical signal is still concentration: ${concentrationRiskLine(ctx)}\n- If you want a valuation-specific read, ask from the Results page after the latest analysis has loaded.\n\nNext step: ask whether your largest holdings look too concentrated for their valuation risk.`;
  }

  if (msg.includes('stress') || msg.includes('crash') || msg.includes('2008') || msg.includes('covid') || msg.includes('rate hike') || msg.includes('dot-com')) {
    return `**Stress and Crash Read**\n\n- Your portfolio beta of **${fmtNum(metrics.beta)}** suggests stress losses would likely be around market-scale or larger if beta stays above 1.\n- VaR **${fmtPct(metrics.var95)}** and max drawdown **${fmtPct(metrics.maxDrawdown)}** already tell us the downside profile is not trivial.\n- ${concentrationRiskLine(ctx)}\n\nNext step: ask which defensive allocation would reduce crash sensitivity most.`;
  }

  if (msg.includes('sector') || msg.includes('correlation') || msg.includes('diversification') || msg.includes('concentration') || msg.includes('risk attribution')) {
    return `**Risk Intelligence**\n\n- Your largest sector tilt is **${topSector} ${fmtPct(topWeight, 0)}**.\n- ${concentrationRiskLine(ctx)}\n- If your biggest holding and biggest sector are the same theme, correlation risk is likely more important than the number of tickers alone.\n\nNext step: ask whether you are diversified by ticker count or by real economic exposure.`;
  }

  if (msg.includes('efficient frontier') || msg.includes('optimization') || msg.includes('rebalance') || msg.includes('weight')) {
    return `**Optimization / Rebalancing**\n\n- The first rebalance candidate is usually the biggest concentration source, not every holding equally.\n- ${concentrationRiskLine(ctx)}\n- If Sharpe **${fmtNum(metrics.sharpe)}** is mediocre while beta **${fmtNum(metrics.beta)}** is elevated, trimming the top risk contributor is usually the cleanest first move.\n\nNext step: ask which exact holding I would trim first and why.`;
  }

  if (msg.includes('monte carlo') || msg.includes('simulation') || msg.includes('future') || msg.includes('projection')) {
    return `**Simulation / Forward-Looking Read**\n\n- Your return profile of **${fmtPct(metrics.annualizedReturn)}** and volatility of **${fmtPct(metrics.volatility)}** imply a decent expected path, but with meaningful dispersion if volatility stays elevated.\n- The wider the volatility band, the less confidence you should have in any single forecast.\n- ${concentrationRiskLine(ctx)}\n\nNext step: ask whether the current return target looks realistic under your volatility level.`;
  }

  if (msg.includes('market mood') || msg.includes('watch for')) {
    return `**What to Watch Right Now**\n\n- Watch your biggest position first: ${concentrationRiskLine(ctx)}\n- Watch overall market sensitivity through beta **${fmtNum(metrics.beta)}**.\n- Watch whether volatility **${fmtPct(metrics.volatility)}** is being rewarded by Sharpe **${fmtNum(metrics.sharpe)}**.\n\nNext step: ask for the top 3 live risks in priority order.`;
  }

  return '';
}

// ── Offline AI fallback ──────────────────────────────────────────────────
function getOfflineResponse(message: string, portfolioContext?: ChatContextLike): string {
  const msg = message.toLowerCase();
  const ctx = normalizeChatContext(portfolioContext);

  if (ctx) {
    const contextualReply = buildMetricResponse(message, ctx);
    if (contextualReply) return contextualReply;
  }

  if (msg.includes('sharpe') || msg.includes('ratio')) {
    return "**Sharpe Ratio** measures risk-adjusted return — how much return you're getting per unit of risk.\n\n• **Above 1.0** — Good. You're being compensated for the risk.\n• **Above 2.0** — Excellent. Institutional-quality returns.\n• **Below 0** — A savings account would have beaten you.\n\nIt's calculated as: (Portfolio Return − Risk-Free Rate) ÷ Portfolio Volatility, annualised. The risk-free rate used is typically the 10-year Treasury yield (~4%).";
  }

  if (msg.includes('risk') || msg.includes('var') || msg.includes('volatility')) {
    return "**Portfolio Risk** comes in several flavours:\n\n• **Value at Risk (VaR 95%)** — The worst daily loss you'd expect 95% of the time. If VaR is -2.3%, on the worst 1-in-20 days, you'd lose at least 2.3%.\n• **Annualised Volatility** — How much your portfolio swings over a year. Below 15% is conservative, above 25% is aggressive.\n• **Max Drawdown** — The deepest peak-to-trough loss. This is the gut-check number.\n\nDiversification across uncorrelated assets is the primary tool for reducing portfolio risk.";
  }

  if (msg.includes('stress') || msg.includes('crash') || msg.includes('crisis')) {
    return "**Stress Testing** estimates how your portfolio would perform under historical crash scenarios:\n\n• **2008 Financial Crisis** — S&P 500 fell ~57% over 17 months\n• **2020 COVID Crash** — 34% drop in just 33 days, recovered in ~90 days\n• **2000 Dot-Com Bust** — 49% decline, took ~6 years to recover\n• **2022 Rate Hike** — 25% decline driven by aggressive Fed tightening\n\nYour estimated loss is calculated using your portfolio's **beta** × the benchmark loss. Higher beta = larger estimated losses.";
  }

  if (msg.includes('sector') || msg.includes('diversif') || msg.includes('allocation')) {
    return "**Sector Diversification** is crucial for risk management:\n\n• Aim for exposure across **4+ sectors** to avoid concentration risk\n• If any single sector exceeds **40%** of your portfolio, you're making a concentrated bet\n• Tech-heavy portfolios (common with FAANG stocks) tend to be highly correlated — they move together\n\nThe **Diversification Score** (0-100) measures average pairwise correlation. Above 65 = well diversified. Below 40 = most stocks are making the same bet.";
  }

  if (msg.includes('monte carlo') || msg.includes('simulat') || msg.includes('future') || msg.includes('predict')) {
    return "**Monte Carlo Simulation** projects possible futures for your portfolio:\n\n• Uses **Geometric Brownian Motion (GBM)** — the same model behind Black-Scholes option pricing\n• Runs 300+ independent paths based on your portfolio's historical drift and volatility\n• The **median line** shows the expected outcome\n• The **5th-95th percentile band** shows the range of likely scenarios\n\nKey insight: wider bands = more uncertainty = higher risk. If the 5th percentile is below your initial investment, there's a real chance of loss.";
  }

  if (msg.includes('beta')) {
    return "**Beta** measures how your portfolio amplifies market movements:\n\n• **Beta = 1.0** — Moves exactly with the S&P 500\n• **Beta > 1.0** — More volatile than the market (e.g., 1.3 means a 10% market drop hits you ~13%)\n• **Beta < 1.0** — More defensive (utilities, healthcare tend to have lower beta)\n\nBeta is computed by regressing your portfolio returns against S&P 500 daily returns. It's a key input for stress testing.";
  }

  if (msg.includes('rebalanc') || msg.includes('optim') || msg.includes('weight')) {
    return "**Portfolio Optimisation** finds the allocation that historically maximised risk-adjusted return:\n\n• Uses **Sharpe Maximisation** via constrained optimisation (SciPy SLSQP solver)\n• Constraints: long-only (no shorting), weights sum to 100%\n• The **Efficient Frontier** chart shows random portfolios plotted on a risk-return map\n• Your current allocation vs the optimal allocation are highlighted\n\n⚠️ The optimal weights are backward-looking — they show what *would have been* best historically, not a guarantee of future performance.";
  }

  if (msg.includes('health') || msg.includes('score')) {
    return "**Portfolio Health Score (0-100)** is a weighted composite of four risk metrics:\n\n• **Sharpe Ratio** (40 points) — Risk-adjusted return quality\n• **Value at Risk** (25 points) — Downside risk exposure\n• **Volatility** (20 points) — Overall price swing magnitude\n• **Concentration** (15 points) — Diversification of holdings\n\nScoring: **70+** = Healthy (green), **40-70** = Needs attention (yellow), **Below 40** = Concern (red).";
  }

  if (ctx) {
    return buildSummaryResponse(ctx);
  }

  return "I'm **Arcus AI**, your portfolio analytics assistant. I can explain any metric you see on the dashboard.\n\nTry asking about:\n• **Sharpe Ratio** — Risk-adjusted returns\n• **Portfolio Risk** — VaR, volatility, drawdowns\n• **Stress Testing** — Historical crash scenarios\n• **Monte Carlo** — Future projections\n• **Sector Diversification** — Concentration analysis\n• **Health Score** — Overall portfolio quality\n\n💡 *AI is temporarily connecting. Try asking a specific question about your portfolio metrics.*";
}
