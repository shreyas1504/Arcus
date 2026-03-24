# ── backend/routers/chat.py ────────────────────────────────────────────────
# AI chatbot endpoint powered by Anthropic Claude.
# Enhanced fallback with comprehensive, interactive responses.

import os
import random
from fastapi import APIRouter, HTTPException  # type: ignore
from pydantic import BaseModel  # type: ignore

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    portfolio_context: dict | None = None


class ChatResponse(BaseModel):
    reply: str


SYSTEM_PROMPT = """You are Arcus AI, an expert financial advisor built into the Arcus portfolio analytics platform.

You have deep knowledge of:
- Portfolio theory (Modern Portfolio Theory, CAPM, Efficient Frontier)
- Risk metrics (Sharpe Ratio, Sortino Ratio, VaR, Beta, Max Drawdown, Volatility)
- Portfolio optimization and diversification
- Market sectors and asset allocation
- Monte Carlo simulation and forward-looking risk assessment

When a user asks a question:
1. Use the portfolio context provided to give specific, data-driven answers
2. Explain financial concepts in clear, accessible language
3. Provide actionable recommendations when appropriate
4. Reference specific numbers from their portfolio
5. Be encouraging but honest about risks

Keep responses concise, insightful, and professional. Use bullet points for clarity.
Format important numbers in bold. Never give specific buy/sell advice — frame as educational insights."""


def _build_context_string(ctx: dict | None) -> str:
    if not ctx:
        return "No portfolio data is currently loaded."

    metrics = ctx.get("metrics", {})
    tickers = ctx.get("tickers", [])

    parts = [
        f"Portfolio holdings: {', '.join(tickers)}",
        f"Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}",
        f"Sortino Ratio: {metrics.get('sortino_ratio', 'N/A')}",
        f"Annualized Return: {metrics.get('annualized_return', 'N/A')}",
        f"Annualized Volatility: {metrics.get('annualized_volatility', 'N/A')}",
        f"Value at Risk (95%): {metrics.get('value_at_risk', 'N/A')}",
        f"Max Drawdown: {metrics.get('max_drawdown', 'N/A')}",
        f"Beta: {metrics.get('beta', 'N/A')}",
        f"Health Score: {metrics.get('health_score', 'N/A')}/100",
        f"Diversification Score: {metrics.get('diversification_score', 'N/A')}/100",
    ]

    benchmark = ctx.get("benchmark")
    if benchmark:
        parts.append(f"Benchmark ({benchmark.get('name', 'S&P 500')}): Alpha = {benchmark.get('alpha', 'N/A')}")

    sectors = ctx.get("sectors")
    if sectors:
        parts.append(f"Sector Exposure: {sectors}")

    return "\n".join(parts)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")

    context_str = _build_context_string(req.portfolio_context)
    user_message = f"Portfolio Context:\n{context_str}\n\nUser Question: {req.message}"

    # If no API key, return a helpful simulated response
    if not api_key:
        return ChatResponse(reply=_fallback_response(req.message, req.portfolio_context))  # type: ignore[call-arg]

    try:
        import anthropic  # type: ignore
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return ChatResponse(reply=message.content[0].text)  # type: ignore[call-arg]
    except ImportError:
        return ChatResponse(reply=_fallback_response(req.message, req.portfolio_context))  # type: ignore[call-arg]
    except Exception as e:
        return ChatResponse(reply=_fallback_response(req.message, req.portfolio_context))  # type: ignore[call-arg]


def _fmt(val: float, kind: str = "pct") -> str:
    """Format a metric value for display."""
    if kind == "pct":
        return f"**{abs(val):.1%}**"
    elif kind == "ratio":
        return f"**{val:.2f}**"
    elif kind == "score":
        return f"**{val:.0f}/100**"
    elif kind == "dollar":
        return f"**${abs(val):,.0f}**"
    return f"**{val}**"


def _fallback_response(question: str, ctx: dict | None) -> str:
    """Comprehensive fallback when Claude API is not available."""
    q = question.lower().strip()
    metrics = (ctx or {}).get("metrics", {})
    tickers = (ctx or {}).get("tickers", [])
    benchmark = (ctx or {}).get("benchmark")
    sectors = (ctx or {}).get("sectors")
    has_data = bool(tickers)

    # ── Sharpe Ratio ─────────────────────────────────────────────────────
    if "sharpe" in q:
        val = metrics.get("sharpe_ratio")
        if isinstance(val, (int, float)):
            if val > 1.5:
                return (f"Your Sharpe ratio of {_fmt(val, 'ratio')} is excellent! You're generating strong "
                        f"returns relative to risk.\n\n"
                        f"• A Sharpe above **1.5** puts you in the top tier\n"
                        f"• Your risk-adjusted performance is beating most active fund managers\n"
                        f"• Keep monitoring — high Sharpe periods can mean-revert")
            elif val > 1:
                return (f"Your Sharpe ratio of {_fmt(val, 'ratio')} is solid — you're earning good risk-adjusted returns.\n\n"
                        f"To push it higher:\n"
                        f"• Check the **Optimal Weights** section — the optimizer may suggest a better allocation\n"
                        f"• Reduce your highest-volatility position\n"
                        f"• Consider adding uncorrelated assets (bonds, gold)")
            elif val > 0:
                return (f"Your Sharpe ratio of {_fmt(val, 'ratio')} is below the **1.0** benchmark.\n\n"
                        f"This means returns don't fully compensate for risk. Try:\n"
                        f"• Shifting weight toward stocks the momentum optimizer favors\n"
                        f"• Reducing high-volatility positions\n"
                        f"• Adding uncorrelated assets (GLD, TLT, XLE)\n"
                        f"• Check the Risk Parity weights for a more balanced approach")
            else:
                return (f"Your Sharpe ratio of {_fmt(val, 'ratio')} is negative — you'd have earned more in a risk-free account.\n\n"
                        f"This often happens in bear markets. Consider:\n"
                        f"• Whether your holdings align with your risk tolerance\n"
                        f"• Adding defensive assets like bonds (TLT) or gold (GLD)\n"
                        f"• Reducing position sizes until conditions improve")
        return ("The **Sharpe ratio** measures risk-adjusted return — how much return you earn per unit of risk.\n\n"
                "• Above **1.0** = Good\n• Above **2.0** = Excellent\n• Below **0** = You'd earn more risk-free\n\n"
                "Load a portfolio to see yours!")

    # ── Drawdown ─────────────────────────────────────────────────────────
    if "drawdown" in q:
        val = metrics.get("max_drawdown")
        if isinstance(val, (int, float)):
            severity = "severe — this indicates high downside risk" if val < -0.30 else "moderate — within acceptable range" if val < -0.20 else "mild — your portfolio has been relatively stable"
            return (f"Your max drawdown is {_fmt(val)} — the worst peak-to-trough decline in your portfolio.\n\n"
                    f"**Assessment**: {severity}\n\n"
                    f"Ways to reduce drawdown:\n"
                    f"• Add defensive assets (bonds, utilities, consumer staples)\n"
                    f"• Use the Risk Parity optimizer for more balanced risk\n"
                    f"• Set stop-loss thresholds at around **-15%** per position")
        return ("**Max drawdown** measures the largest drop from a peak to a trough in your portfolio's history.\n\n"
                "• Below **-20%** = Moderate risk\n• Below **-35%** = Severe risk\n\n"
                "It's one of the most important metrics for understanding real downside risk.")

    # ── Risk / VaR ───────────────────────────────────────────────────────
    if "risk" in q or " var " in q or q.startswith("var") or "value at risk" in q:
        val = metrics.get("value_at_risk")
        if isinstance(val, (int, float)):
            dollar = abs(val) * 10000  # assume $10k default
            return (f"Your daily **Value at Risk (95%)** is {_fmt(val)}.\n\n"
                    f"This means on the worst 5% of trading days, expect to lose at least this much.\n"
                    f"For a **$10,000** portfolio, that's about {_fmt(dollar, 'dollar')} at risk on bad days.\n\n"
                    f"To manage VaR:\n"
                    f"• Diversify across uncorrelated sectors\n"
                    f"• Reduce leverage and concentrated positions\n"
                    f"• The Risk Parity optimizer helps equalize risk contribution")
        return ("**Value at Risk (VaR)** estimates the maximum expected loss per day at 95% confidence.\n\n"
                "Example: A VaR of **-2.5%** means on the worst 5% of days, you'd lose at least 2.5% of your portfolio.\n\n"
                "It's a standard institutional risk metric used by banks and hedge funds.")

    # ── Diversification ──────────────────────────────────────────────────
    if "diversi" in q or "concentrated" in q or "correlat" in q:
        val = metrics.get("diversification_score")
        sect = sectors or {}
        if isinstance(val, (int, float)):
            sector_note = ""
            if sect:
                top_sector = max(sect, key=lambda k: sect[k]) if sect else ""
                top_weight = sect.get(top_sector, 0)
                if top_weight > 0.4:
                    sector_note = f"\n\n⚠️ **{top_sector}** makes up **{top_weight:.0%}** of your portfolio — that's high concentration."
            return (f"Your diversification score is {_fmt(val, 'score')}.\n"
                    f"{'✅ Well-diversified! Your holdings have low correlations.' if val > 65 else '⚠️ Your holdings are quite correlated.'}"
                    f"{sector_note}\n\n"
                    f"To improve diversification:\n"
                    f"• Add assets from different sectors (energy, healthcare, finance)\n"
                    f"• Include ETFs like **GLD** (gold), **TLT** (bonds), **XLE** (energy)\n"
                    f"• The Risk Parity optimizer helps spread risk evenly")
        return ("**Diversification** reduces risk by combining assets that don't move together.\n\n"
                "A score of **100** = perfectly uncorrelated holdings (impossible in practice).\n"
                "A score below **40** = your stocks move almost in lockstep — risky!\n\n"
                "Common diversifiers: Gold (GLD), Treasury bonds (TLT), international stocks, real estate (VNQ).")

    # ── Health Score ─────────────────────────────────────────────────────
    if "health" in q or "score" in q or "overall" in q or "summary" in q:
        val = metrics.get("health_score")
        if isinstance(val, (int, float)):
            color = "🟢 excellent" if val >= 70 else ("🟡 moderate" if val >= 40 else "🔴 needs attention")
            components = metrics.get("health_components", {})
            comp_str = ""
            if components:
                comp_str = "\n\n**Score breakdown:**\n" + "\n".join(f"• {k}: **{v}** pts" for k, v in components.items())
            return (f"Your portfolio health score is {_fmt(val, 'score')} — {color}.\n\n"
                    f"This composite score weighs:\n"
                    f"• Sharpe ratio (40 pts) — risk-adjusted return\n"
                    f"• VaR (25 pts) — daily downside risk\n"
                    f"• Volatility (20 pts) — price swings\n"
                    f"• Concentration (15 pts) — diversification"
                    f"{comp_str}")
        return ("The **health score** is a 0-100 composite rating.\n\n"
                "• 🟢 **70-100** = Healthy portfolio\n"
                "• 🟡 **40-69** = Some issues to address\n"
                "• 🔴 **0-39** = Critical — needs rebalancing\n\n"
                "Load a portfolio to see yours!")

    # ── Beta ─────────────────────────────────────────────────────────────
    if "beta" in q or "market" in q and "sens" in q:
        val = metrics.get("beta")
        if isinstance(val, (int, float)):
            impact = f"a **10%** market drop would hit your portfolio for roughly **{val * 10:.0f}%**"
            return (f"Your portfolio beta is {_fmt(val, 'ratio')} vs the S&P 500.\n\n"
                    f"• {'Your portfolio amplifies market moves — ' + impact if val > 1 else 'Your portfolio is less volatile than the market — good for stability.'}\n\n"
                    f"**Beta guide:**\n"
                    f"• β = **1.0** → moves with the market\n"
                    f"• β > **1.0** → amplifies moves (more aggressive)\n"
                    f"• β < **1.0** → dampens moves (more defensive)\n"
                    f"• β < **0** → moves opposite to market (rare)")
        return ("**Beta** measures how your portfolio moves relative to the S&P 500.\n\n"
                "• β = **1.0** → tracks the market exactly\n"
                "• β = **1.5** → 50% more volatile than the market\n"
                "• β = **0.5** → half as volatile as the market")

    # ── Volatility ───────────────────────────────────────────────────────
    if "volatil" in q or "vol " in q or q == "vol":
        val = metrics.get("annualized_volatility")
        if isinstance(val, (int, float)):
            return (f"Your annualized volatility is {_fmt(val)}.\n\n"
                    f"{'Low volatility — your portfolio is relatively stable.' if val < 0.15 else 'Moderate volatility.' if val < 0.25 else 'High volatility — expect large daily swings.'}\n\n"
                    f"For a **$10,000** portfolio, you'd typically see daily swings of about "
                    f"{_fmt(val / (252**0.5) * 10000, 'dollar')}.\n\n"
                    f"To reduce volatility: add bonds (TLT), low-beta stocks, or use the Risk Parity optimizer.")
        return ("**Volatility** measures how much your portfolio's value swings.\n\n"
                "• Below **15%** annualized = Low (stable)\n"
                "• **15-25%** = Moderate\n"
                "• Above **25%** = High (expect big swings)")

    # ── Sortino ──────────────────────────────────────────────────────────
    if "sortino" in q:
        val = metrics.get("sortino_ratio")
        if isinstance(val, (int, float)):
            return (f"Your Sortino ratio is {_fmt(val, 'ratio')}.\n\n"
                    f"Unlike Sharpe, Sortino only penalizes **downside** volatility (not upside gains).\n"
                    f"{'Excellent — you have strong returns with limited downside risk!' if val > 2 else 'Good — decent downside protection.' if val > 1 else 'Below average — your portfolio has significant downside risk.'}\n\n"
                    f"• Above **2.0** = Excellent downside management\n"
                    f"• Above **1.0** = Acceptable\n"
                    f"• Below **0** = Downside dominates returns")
        return ("The **Sortino ratio** is like the Sharpe ratio, but only counts downside volatility.\n\n"
                "It's a better measure if you care more about losses than gains (which most investors do!).")

    # ── Returns ──────────────────────────────────────────────────────────
    if "return" in q or "performance" in q or "gain" in q:
        val = metrics.get("annualized_return")
        if isinstance(val, (int, float)):
            return (f"Your annualized return is {_fmt(val)}.\n\n"
                    f"{'🎯 Strong performance! You\'re beating the historical average stock market return of ~10%.' if val > 0.10 else 'Positive but below the historical market average of ~10%.' if val > 0 else '📉 Negative returns over this period.'}\n\n"
                    f"For a **$10,000** investment, this translates to roughly "
                    f"**${val * 10000:+,.0f}** per year.\n\n"
                    f"Check the **Benchmark Comparison** section to see how you stack up against the S&P 500.")
        return "**Annualized return** is your portfolio's yearly growth rate. The historical S&P 500 average is about **10%** per year."

    # ── Recommend / Optimize / Improve / Add / What else ─────────────────
    if any(w in q for w in ["recommend", "optim", "improv", "better", "rebalanc", "fix",
                             "change", "adjust", "suggest", "add", "what else",
                             "more", "buy", "new stock", "which stock", "what stock",
                             "should i", "could i", "can i", "what to", "how to make",
                             "enhance", "boost", "upgrade", "strengthen"]):
        if has_data:
            shrp = metrics.get("sharpe_ratio", 0)
            vol = metrics.get("annualized_volatility", 0)
            div = metrics.get("diversification_score", 50)
            beta_val = metrics.get("beta", 1)
            mdd = metrics.get("max_drawdown", 0)
            sect = sectors or {}

            # Figure out which sectors are missing
            all_sectors = {"Technology", "Healthcare", "Financial Services", "Energy",
                          "Consumer Cyclical", "Consumer Defensive", "Industrials",
                          "Utilities", "Real Estate", "Basic Materials", "Communication Services"}
            current_sectors = set(sect.keys()) if sect else set()
            missing_sectors = all_sectors - current_sectors

            # Sector-to-ETF map
            sector_etfs = {
                "Healthcare": ("XLV", "Healthcare ETF — Johnson & Johnson, UnitedHealth, Pfizer"),
                "Energy": ("XLE", "Energy ETF — Exxon, Chevron, ConocoPhillips"),
                "Financial Services": ("XLF", "Financials ETF — JPM, BRK-B, Bank of America"),
                "Consumer Defensive": ("XLP", "Consumer Staples ETF — Procter & Gamble, Walmart, Costco"),
                "Utilities": ("XLU", "Utilities ETF — NextEra, Duke Energy, Southern Co"),
                "Real Estate": ("VNQ", "Real Estate ETF — diversified REITs"),
                "Industrials": ("XLI", "Industrials ETF — Caterpillar, Honeywell, GE"),
                "Basic Materials": ("XLB", "Materials ETF — Linde, Sherwin-Williams"),
            }

            tips = []
            specific_adds = []

            # 1. Diversification-based suggestions
            if isinstance(div, (int, float)) and div < 60:
                tips.append("📊 **Diversification is low** — your stocks move too much in lockstep.")
                for missed in sorted(missing_sectors)[:3]:  # type: ignore[index]
                    entry = sector_etfs.get(missed)
                    if entry:
                        etf, desc = entry
                        specific_adds.append(f"• Add **{etf}** — {desc}")

            # 2. High volatility suggestions
            if isinstance(vol, (int, float)) and vol > 0.22:
                tips.append("🌊 **Volatility is high** — consider stabilizers:")
                specific_adds.append("• Add **TLT** — 20-year Treasury bonds (negative correlation to stocks)")
                specific_adds.append("• Add **GLD** — Gold ETF (hedge against market crashes)")

            # 3. High beta
            if isinstance(beta_val, (int, float)) and beta_val > 1.3:
                tips.append(f"⚡ **Beta is {beta_val:.2f}** — your portfolio amplifies market swings.")
                specific_adds.append("• Add **XLU** or **XLP** — low-beta defensive sectors")
                specific_adds.append("• Add **BRK-B** — Berkshire Hathaway (historically lower beta)")

            # 4. Sharpe improvement
            if isinstance(shrp, (int, float)) and shrp < 1:
                tips.append("📉 **Sharpe below 1.0** — you're not being compensated enough for risk.")
                specific_adds.append("• Switch to the **Momentum optimizer** weights — it favors trending stocks")
                specific_adds.append("• Reduce your worst-performing position and reallocate to **SPY** (market index)")

            # 5. Drawdown protection
            if isinstance(mdd, (int, float)) and mdd < -0.25:
                tips.append(f"📉 **Max drawdown of {mdd:.0%}** is severe.")
                specific_adds.append("• Consider **SPLV** — S&P 500 Low Volatility ETF")

            # 6. Sector concentration
            concentrated = [k for k, v in sect.items() if v > 0.5]
            if concentrated:
                tips.append(f"⚠️ **{concentrated[0]}** is over 50% of your portfolio!")

            # Always add general best practices
            if not specific_adds:
                specific_adds = [
                    "• Add **GLD** (gold) — uncorrelated to stocks, great hedge",
                    "• Add **TLT** (bonds) — negative correlation during crashes",
                    "• Add **VNQ** (real estate) — income + diversification",
                    "• Add **XLE** (energy) — inflation hedge and low tech correlation",
                ]

            response = f"🎯 **Recommendations for {', '.join(tickers)}:**\n\n"
            if tips:
                response += "\n".join(tips) + "\n\n"
            response += "**Specific additions to consider:**\n" + "\n".join(list(specific_adds)[:5])  # type: ignore[index]
            response += ("\n\n**Strategy tip:** Try the **Risk Parity** optimizer to see how "
                        "to balance risk across all positions. Then compare with **Momentum** "
                        "weights to find the sweet spot.")
            return response

        return ("Here are general portfolio improvement strategies:\n\n"
                "**Stocks/ETFs to consider adding:**\n"
                "• **SPY** — S&P 500 index (the benchmark)\n"
                "• **GLD** — Gold (hedge against crashes)\n"
                "• **TLT** — Treasury bonds (negative correlation)\n"
                "• **XLE** — Energy sector (inflation hedge)\n"
                "• **VNQ** — Real estate (income + diversification)\n"
                "• **XLV** — Healthcare (defensive growth)\n\n"
                "**General rules:**\n"
                "• No single sector > **40%** of portfolio\n"
                "• Keep Sharpe above **1.0**\n"
                "• Rebalance quarterly\n"
                "• Dollar-cost average instead of timing the market\n\n"
                "Load a portfolio to get personalized recommendations!")

    # ── Compare / Benchmark / S&P ────────────────────────────────────────
    if any(w in q for w in ["benchmark", "s&p", "sp500", "compare", "versus", "vs "]):
        if benchmark:
            alpha = benchmark.get("alpha", 0)
            return (f"**Portfolio vs S&P 500:**\n\n"
                    f"• Alpha: **{'+' if alpha >= 0 else ''}{alpha * 100:.2f}%** {'✅ outperforming!' if alpha > 0 else '❌ underperforming'}\n"
                    f"• Your Sharpe: **{benchmark.get('port_sharpe', 0):.2f}** vs S&P: **{benchmark.get('bmark_sharpe', 0):.2f}**\n"
                    f"• Your Volatility: **{benchmark.get('port_vol', 0):.1%}** vs S&P: **{benchmark.get('bmark_vol', 0):.1%}**\n\n"
                    f"{'Your portfolio is beating the market! 🎯' if benchmark.get('outperformed') else 'The S&P 500 is winning — consider whether your active choices justify the extra risk.'}")
        return ("The **S&P 500** is the most common benchmark for U.S. stock portfolios.\n\n"
                "**Alpha** = your excess return above the benchmark.\n"
                "• Positive alpha = you're adding value beyond just holding SPY\n"
                "• Negative alpha = you'd have done better in an index fund")

    # ── Monte Carlo ──────────────────────────────────────────────────────
    if "monte carlo" in q or "simulation" in q or "predict" in q or "future" in q or "forecast" in q:
        return ("**Monte Carlo simulation** projects thousands of possible future paths for your portfolio.\n\n"
                "It uses **Geometric Brownian Motion (GBM)** — the same model used by major banks.\n\n"
                "The 3 scenarios shown:\n"
                "• 🔴 **5th percentile** — worst-case (things go badly)\n"
                "• 🟢 **50th percentile** — expected outcome (most likely)\n"
                "• 🔵 **95th percentile** — best-case (things go very well)\n\n"
                "The wider the spread, the more uncertain (volatile) your portfolio is.\n\n"
                "Check the Monte Carlo section of your analysis to see your projections!")

    # ── Sector questions ─────────────────────────────────────────────────
    if any(w in q for w in ["sector", "industry", "tech", "technology", "energy", "finance", "healthcare"]):
        if sectors:
            sector_lines = [f"• **{k}**: {v:.0%}" for k, v in sorted(sectors.items(), key=lambda x: -x[1])]
            concentrated = [k for k, v in sectors.items() if v > 0.4]
            warning = ""
            if concentrated:
                warning = f"\n\n⚠️ **High concentration in {', '.join(concentrated)}** — consider adding exposure to other sectors."
            return f"Your sector allocation:\n\n" + "\n".join(sector_lines) + warning
        return ("**Sector diversification** is crucial for reducing risk.\n\n"
                "Common sectors: Technology, Healthcare, Financials, Energy, Consumer, Industrials\n\n"
                "Rule of thumb: No single sector should exceed **40%** of your portfolio.\n"
                "Load a portfolio to see your sector breakdown!")

    # ── What is / Explain / How does ─────────────────────────────────────
    if any(w in q for w in ["what is", "what's", "explain", "define", "how does", "how do", "tell me about", "meaning"]):
        # Try to match topic
        if "capm" in q or "capital asset" in q:
            return ("**CAPM (Capital Asset Pricing Model)** estimates expected return based on risk:\n\n"
                    "**Expected Return = Risk-Free Rate + β × (Market Return − Risk-Free Rate)**\n\n"
                    "Key insight: You should only take risk that's compensated. If your portfolio's beta is 1.3, "
                    "you should expect **30%** more return than the risk-free rate to justify the extra risk.")
        if "efficient frontier" in q or "frontier" in q:
            return ("The **Efficient Frontier** shows the best possible return for each level of risk.\n\n"
                    "Our optimizer finds the portfolio on this frontier:\n"
                    "• **Max Sharpe** = highest return per unit of risk\n"
                    "• **Momentum** = tilts toward trending stocks\n"
                    "• **Risk Parity** = equal risk contribution from each asset")
        if "mpt" in q or "modern portfolio" in q:
            return ("**Modern Portfolio Theory (MPT)** by Harry Markowitz shows that diversification reduces risk.\n\n"
                    "Key principles:\n"
                    "• Don't look at stocks in isolation — look at how they interact\n"
                    "• An optimal portfolio maximizes return for a given risk level\n"
                    "• Correlation is key: low-correlation assets reduce overall portfolio risk")

    # ── Greetings / casual ───────────────────────────────────────────────
    if any(w in q for w in ["hello", "hi ", "hey", "good morning", "good afternoon", "sup", "yo"]) or q in ["hi", "hey", "hello"]:
        if has_data:
            health = metrics.get("health_score", "?")
            return (f"Hey! 👋 I'm Arcus AI, your portfolio analyst.\n\n"
                    f"I can see you're analyzing **{', '.join(tickers)}** with a health score of **{health}/100**.\n\n"
                    f"What would you like to know? I can help with:\n"
                    f"• Risk metrics (Sharpe, VaR, Beta, Drawdown)\n"
                    f"• How to improve your portfolio\n"
                    f"• Comparing against the S&P 500\n"
                    f"• Explaining any financial concept")
        return ("Hey! 👋 I'm Arcus AI, your portfolio analytics assistant.\n\n"
                "Load a portfolio on the dashboard and I can help with:\n"
                "• Analyzing your risk metrics\n"
                "• Strategies to improve performance\n"
                "• Explaining financial concepts\n"
                "• Comparing against benchmarks\n\n"
                "Try asking: *\"What is Sharpe ratio?\"* or *\"How does diversification help?\"*")

    # ── Thanks ───────────────────────────────────────────────────────────
    if any(w in q for w in ["thank", "thanks", "thx", "cheers", "appreciate"]):
        return random.choice([
            "You're welcome! Let me know if you have any other questions about your portfolio. 📊",
            "Happy to help! Feel free to ask about any other metrics or strategies. 🎯",
            "Anytime! I'm here whenever you need portfolio insights. 💡",
        ])

    # ── Yes/No/OK (follow-up) ────────────────────────────────────────────
    if q in ["yes", "no", "ok", "okay", "sure", "yep", "nope", "got it"]:
        if has_data:
            return ("Great! Here are some things you can ask me about:\n\n"
                    "• *\"How can I improve my portfolio?\"*\n"
                    "• *\"Explain my Sharpe ratio\"*\n"
                    "• *\"Am I too concentrated in tech?\"*\n"
                    "• *\"What does my beta mean?\"*\n"
                    "• *\"Compare me against the S&P 500\"*")
        return "What would you like to know? Try asking about Sharpe ratio, VaR, diversification, or any financial concept!"

    # ── Comprehensive general fallback ────────────────────────────────────
    if has_data:
        # Build a smart summary based on the portfolio
        health = metrics.get("health_score", 0)
        shrp = metrics.get("sharpe_ratio", 0)
        vol = metrics.get("annualized_volatility", 0)
        ret = metrics.get("annualized_return", 0)
        beta = metrics.get("beta", 1)
        div = metrics.get("diversification_score", 50)

        insights = []
        if isinstance(health, (int, float)):
            status = "🟢 healthy" if health >= 70 else "🟡 moderate" if health >= 40 else "🔴 needs attention"
            insights.append(f"**Health Score**: {health:.0f}/100 ({status})")
        if isinstance(ret, (int, float)):
            insights.append(f"**Return**: {ret:.1%} annualized {'📈' if ret > 0 else '📉'}")
        if isinstance(shrp, (int, float)):
            insights.append(f"**Sharpe**: {shrp:.2f} {'✅' if shrp > 1 else '⚠️'}")
        if isinstance(vol, (int, float)):
            insights.append(f"**Volatility**: {vol:.1%} {'(low)' if vol < 0.15 else '(moderate)' if vol < 0.25 else '(high)'}")
        if isinstance(beta, (int, float)):
            insights.append(f"**Beta**: {beta:.2f} vs S&P 500")
        if isinstance(div, (int, float)):
            insights.append(f"**Diversification**: {div:.0f}/100")

        return (f"Here's a quick summary of your portfolio ({', '.join(tickers)}):\n\n"
                + "\n".join(f"• {i}" for i in insights)
                + "\n\n**Ask me anything specific!** For example:\n"
                "• *\"How can I improve my Sharpe ratio?\"*\n"
                "• *\"Am I too concentrated?\"*\n"
                "• *\"What does my beta mean?\"*\n"
                "• *\"Explain Monte Carlo simulations\"*\n"
                "• *\"Compare me against the S&P 500\"*")

    return ("I'm **Arcus AI**, your portfolio analytics assistant! 🚀\n\n"
            "I can help you understand:\n"
            "• **Risk metrics** — Sharpe, VaR, Beta, Drawdown, Sortino\n"
            "• **Portfolio optimization** — 3 strategies to improve your allocation\n"
            "• **Diversification** — sector concentration and correlation\n"
            "• **Financial concepts** — CAPM, Efficient Frontier, MPT\n"
            "• **S&P 500 comparison** — are you beating the market?\n\n"
            "Load a portfolio on the dashboard first, then come back to me for personalized insights!\n\n"
            "Or try asking: *\"What is Sharpe ratio?\"* or *\"How does Monte Carlo work?\"*")
