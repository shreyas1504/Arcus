# Vercel Serverless Function for Arcus AI Chat
# This runs on Vercel's infrastructure — always available, no cold starts

import os
import json
from http.server import BaseHTTPRequestHandler


# ── System prompt builder ────────────────────────────────────────────────

def _build_system_prompt(ctx: dict | None) -> str:
    base = (
        "You are Arcus AI, a portfolio analytics assistant built into the Arcus platform. "
        "You have access to the user's live portfolio data.\n\n"
    )

    if not ctx:
        return base + (
            "No portfolio data is currently loaded. "
            "Help the user understand financial concepts clearly. "
            "Rules: Under 200 words unless needed. Markdown bullets. "
            "End with one actionable next step."
        )

    parts: list[str] = []

    # Parse holdings
    holdings = ctx.get("holdings", [])
    if holdings:
        holdings_str = ", ".join(
            f"{h.get('ticker', '?')} ({h.get('weight', 0) * 100:.0f}%)"
            for h in holdings if h.get("ticker")
        )
        parts.append(f"Holdings: {holdings_str}")

    # Parse metrics
    metrics = ctx.get("metrics")
    if isinstance(metrics, dict):
        metric_parts = []
        field_map = {
            "healthScore": "Health Score",
            "health_score": "Health Score",
            "sharpe": "Sharpe",
            "var95": "VaR 95%",
            "var_95": "VaR 95%",
            "cvar": "CVaR",
            "cvar_95": "CVaR",
            "beta": "Beta",
            "maxDrawdown": "Max Drawdown",
            "max_drawdown": "Max Drawdown",
            "annualizedReturn": "Ann. Return",
            "annualized_return": "Ann. Return",
            "volatility": "Volatility",
            "sortino": "Sortino",
            "alpha": "Alpha",
        }
        for key, label in field_map.items():
            val = metrics.get(key)
            if val is not None and label not in [m.split(" ")[0] for m in metric_parts]:
                if "Return" in label or "Drawdown" in label or "VaR" in label or "CVaR" in label or "Volatility" in label or "Alpha" in label:
                    metric_parts.append(f"{label} {val * 100:.1f}%")
                elif label == "Health Score":
                    metric_parts.append(f"{label} {val:.0f}/100")
                else:
                    metric_parts.append(f"{label} {val:.2f}")
        if metric_parts:
            parts.append(f"Metrics: {', '.join(metric_parts)}")

    # Parse investor profile
    profile = ctx.get("investorProfile") or ctx.get("investor_dna")
    if isinstance(profile, dict):
        risk = profile.get("riskTolerance") or profile.get("risk_tolerance") or "Moderate"
        target = profile.get("targetReturn") or profile.get("target_return") or 0.10
        parts.append(f"Investor: {risk} risk, targeting {target * 100:.0f}% annual return")

    context_block = "\n".join(parts)

    return (
        f"{base}{context_block}\n\n"
        "Rules: Reference specific numbers from the portfolio data when available. "
        "Be specific about tickers and weights. "
        "Under 200 words unless the user asks for detail. Use markdown bullets. "
        "End with one actionable next step."
    )


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        message = data.get("message", "")
        conversation_history = data.get("conversation_history", [])
        portfolio_context = data.get("portfolio_context")

        api_key = os.environ.get("NVIDIA_API_KEY")

        if not api_key:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "NVIDIA_API_KEY not configured",
                "fallback": True
            }).encode())
            return

        # Build system prompt
        system_prompt = _build_system_prompt(portfolio_context)

        # Build messages
        messages = []
        for msg in conversation_history:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": msg.get("content", "")})
        
        # Minimax optimization: Prepend system prompt to the latest user message
        # because some models hang or fail when given a "system" role.
        final_message = f"SYSTEM CONTEXT:\n{system_prompt}\n\nUSER MESSAGE:\n{message}"
        messages.append({"role": "user", "content": final_message})

        try:
            import urllib.request
            import ssl
            
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta/llama3-70b-instruct",
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
            
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=60) as response:
                res_body = response.read()
                res_json = json.loads(res_body)
                reply = res_json["choices"][0]["message"]["content"]

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "reply": reply,
                "fallback": False
            }).encode())

        except Exception as e:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": f"AI temporarily unavailable: {str(e)}",
                "fallback": True
            }).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Health check."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "service": "arcus-ai-chat"}).encode())
