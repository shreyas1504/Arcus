# ── backend/routers/chat.py ────────────────────────────────────────────────
# AI chatbot endpoint powered by Arcus AI.
# Accepts live portfolio context and conversation history.

import os
import logging
from fastapi import APIRouter, HTTPException  # type: ignore
from pydantic import BaseModel  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


# ── Request / Response models ─────────────────────────────────────────────

class HoldingContext(BaseModel):
    ticker: str
    weight: float = 0
    currentPrice: float = 0


class MetricsContext(BaseModel):
    healthScore: float | None = None
    sharpe: float | None = None
    var95: float | None = None
    cvar: float | None = None
    beta: float | None = None
    maxDrawdown: float | None = None
    annualizedReturn: float | None = None
    volatility: float | None = None
    sortino: float | None = None
    alpha: float | None = None


class InvestorProfile(BaseModel):
    riskTolerance: str = "Moderate"
    targetReturn: float = 0.10


class PortfolioContext(BaseModel):
    holdings: list[HoldingContext] = []
    metrics: MetricsContext | None = None
    investorProfile: InvestorProfile | None = None


class HistoryMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[HistoryMessage] = []
    portfolio_context: PortfolioContext | dict | None = None


class ChatResponse(BaseModel):
    reply: str
    fallback: bool = False


# ── System prompt builder ─────────────────────────────────────────────────

def _build_system_prompt(ctx: PortfolioContext | dict | None) -> str:
    base = (
        "You are Arcus AI, a portfolio analytics assistant. "
        "You have the user's live data.\n\n"
    )

    # Handle raw dict from old frontend format
    if isinstance(ctx, dict):
        ctx = _dict_to_portfolio_context(ctx)

    if not ctx or (not ctx.holdings and not ctx.metrics):
        return base + (
            "No portfolio data is currently loaded. "
            "Help the user understand financial concepts clearly. "
            "Rules: Under 200 words unless needed. Markdown bullets. "
            "End with one actionable next step."
        )

    parts: list[str] = []

    if ctx.holdings:
        holdings_str = ", ".join(
            f"{h.ticker} ({h.weight * 100:.0f}%, ${h.currentPrice:,.2f})"
            for h in ctx.holdings if h.ticker
        )
        parts.append(f"Holdings: {holdings_str}")

    if ctx.metrics:
        m = ctx.metrics
        metrics_parts: list[str] = []
        if m.healthScore is not None:
            metrics_parts.append(f"Health Score {m.healthScore:.0f}/100")
        if m.sharpe is not None:
            metrics_parts.append(f"Sharpe {m.sharpe:.2f}")
        if m.sortino is not None:
            metrics_parts.append(f"Sortino {m.sortino:.2f}")
        if m.var95 is not None:
            metrics_parts.append(f"VaR {m.var95 * 100:.1f}%")
        if m.cvar is not None:
            metrics_parts.append(f"CVaR {m.cvar * 100:.1f}%")
        if m.beta is not None:
            metrics_parts.append(f"Beta {m.beta:.2f}")
        if m.maxDrawdown is not None:
            metrics_parts.append(f"Max Drawdown {m.maxDrawdown * 100:.1f}%")
        if m.annualizedReturn is not None:
            metrics_parts.append(f"Ann. Return {m.annualizedReturn * 100:.1f}%")
        if m.volatility is not None:
            metrics_parts.append(f"Volatility {m.volatility * 100:.1f}%")
        if m.alpha is not None:
            metrics_parts.append(f"Alpha {m.alpha * 100:.1f}%")
        if metrics_parts:
            parts.append(f"Metrics: {', '.join(metrics_parts)}")

    if ctx.investorProfile:
        ip = ctx.investorProfile
        parts.append(
            f"Investor: {ip.riskTolerance} risk, "
            f"targeting {ip.targetReturn * 100:.0f}% annual return"
        )

    context_block = "\n".join(parts)

    return (
        f"{base}{context_block}\n\n"
        "Rules: Reference specific numbers always. Be specific on tickers. "
        "Under 200 words unless needed. Markdown bullets. "
        "End with one actionable next step."
    )


def _dict_to_portfolio_context(raw: dict) -> PortfolioContext:
    """Convert legacy frontend format to structured PortfolioContext."""
    holdings: list[HoldingContext] = []
    metrics_ctx: MetricsContext | None = None
    investor_ctx: InvestorProfile | None = None

    # Try portfolio sub-key (raw localStorage format)
    portfolio = raw.get("portfolio") or {}
    if isinstance(portfolio, dict):
        raw_holdings = portfolio.get("holdings", [])
        n = len(raw_holdings) if raw_holdings else 0
        for h in raw_holdings:
            if isinstance(h, dict) and h.get("ticker"):
                holdings.append(HoldingContext(
                    ticker=h["ticker"],
                    weight=1.0 / n if n > 0 else 0,
                    currentPrice=0,
                ))

    # Try metrics sub-key
    raw_metrics = raw.get("metrics")
    if isinstance(raw_metrics, dict):
        metrics_ctx = MetricsContext(
            healthScore=raw_metrics.get("health_score"),
            sharpe=raw_metrics.get("sharpe"),
            var95=raw_metrics.get("var_95"),
            cvar=raw_metrics.get("cvar_95"),
            beta=raw_metrics.get("beta"),
            maxDrawdown=raw_metrics.get("max_drawdown"),
            annualizedReturn=raw_metrics.get("annualized_return"),
            volatility=raw_metrics.get("volatility"),
            sortino=raw_metrics.get("sortino"),
            alpha=raw_metrics.get("alpha"),
        )

    # Try investor DNA
    dna = raw.get("investor_dna") or raw.get("investorProfile")
    if isinstance(dna, dict):
        investor_ctx = InvestorProfile(
            riskTolerance=dna.get("risk_tolerance") or dna.get("riskTolerance") or "Moderate",
            targetReturn=dna.get("target_return") or dna.get("targetReturn") or 0.10,
        )

    return PortfolioContext(
        holdings=holdings,
        metrics=metrics_ctx,
        investorProfile=investor_ctx,
    )


# ── Chat endpoint ─────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    api_key = os.getenv("NVIDIA_API_KEY")

    # Build context
    ctx = req.portfolio_context
    system_prompt = _build_system_prompt(ctx)

    # Build messages list from conversation history + new message
    messages: list[dict[str, str]] = []
    for msg in req.conversation_history:
        role = "assistant" if msg.role == "assistant" else "user"
        messages.append({"role": role, "content": msg.content})
        
    # Minimax optimization: Prepend system prompt to the latest user message
    # because some models hang or fail when given a "system" role.
    final_message = f"SYSTEM CONTEXT:\n{system_prompt}\n\nUSER MESSAGE:\n{req.message}"
    messages.append({"role": "user", "content": final_message})

    # If no API key, return 503 so frontend knows AI is unavailable
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail={"error": "AI unavailable — NVIDIA_API_KEY not set", "fallback": True},
        )

    try:
        import urllib.request
        import urllib.error
        import json
        import ssl
        
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "minimaxai/minimax-m2.7",
            "messages": messages,
            "temperature": 1,
            "top_p": 0.95,
            "max_tokens": 1024,
            "stream": False
        }
        
        # macOS Python local certificate fix
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        req_obj = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req_obj, context=ssl_ctx, timeout=60) as response:
            res_body = response.read()
            res_json = json.loads(res_body)
            reply = res_json["choices"][0]["message"]["content"]
            
        return ChatResponse(reply=reply, fallback=False)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        logger.error(f"Arcus AI API HTTP Error: {e.code} - {err_body}")
        raise HTTPException(
            status_code=503,
            detail={"error": f"NVIDIA API Error: {e.code} - {err_body}", "fallback": True},
        )
    except Exception as e:
        logger.error(f"Arcus AI API error: {e}")
        raise HTTPException(
            status_code=503,
            detail={"error": f"AI temporarily unavailable: {str(e)}", "fallback": True},
        )
