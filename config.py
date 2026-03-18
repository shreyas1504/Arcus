# ── config.py ──────────────────────────────────────────────────────────────
# Central place for all constants. Edit here; everywhere else imports these.

# ── Brand ─────────────────────────────────────────────────────────────────────
BRAND_NAME    = "QuantView"
BRAND_TAGLINE = "Institutional-grade portfolio intelligence. For everyone."
BRAND_ICON    = "⬡"

# ── Color palette ─────────────────────────────────────────────────────────────
COLORS = {
    "bg_primary":    "#0F1117",
    "bg_card":       "#1A1D2E",
    "bg_card_hover": "#222640",
    "accent":        "#4F8EF7",
    "accent_soft":   "rgba(79,142,247,0.12)",
    "success":       "#00C896",
    "success_soft":  "rgba(0,200,150,0.12)",
    "danger":        "#FF4757",
    "danger_soft":   "rgba(255,71,87,0.12)",
    "warning":       "#FFB700",
    "warning_soft":  "rgba(255,183,0,0.12)",
    "text_primary":  "#FFFFFF",
    "text_secondary":"#8B9BB4",
    "border":        "rgba(255,255,255,0.08)",
}

# ── Risk & finance constants ───────────────────────────────────────────────────
RISK_FREE_RATE       = 0.04    # Annual risk-free rate (4% — approx current T-bill)
VAR_CONFIDENCE_LEVEL = 0.95    # 95th-percentile Value at Risk
TRADING_DAYS         = 252     # Trading days per year
ROLLING_WINDOW       = 60      # Rolling window for rolling Sharpe (trading days)

# ── Simulation defaults ────────────────────────────────────────────────────────
DEFAULT_SIMULATIONS = 300
DEFAULT_DAYS        = 252

# ── UI defaults ───────────────────────────────────────────────────────────────
DEFAULT_TICKERS    = "AAPL,MSFT,GOOGL"
DEFAULT_START_DATE = "2020-01-01"
DEFAULT_END_DATE   = "2024-12-31"
BENCHMARK_TICKER   = "^GSPC"   # S&P 500
BENCHMARK_NAME     = "S&P 500"

# ── Demo portfolios (sample portfolio button) ─────────────────────────────────
import datetime as _dt
_today_str   = _dt.date.today().isoformat()
_predict_str = _dt.date.today().replace(year=_dt.date.today().year + 1).isoformat()

DEMO_PORTFOLIOS = {
    "Volatile — Red Score":  {
        "tickers":  ["TSLA", "NVDA", "AMD", "COIN", "PLTR"],
        "start":    "2021-01-01",
        "end":      _today_str,
        "predict":  _predict_str,
        "investment": 10_000,
    },
    "Tech Heavy — Yellow Score": {
        "tickers":  ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
        "start":    "2022-01-01",
        "end":      _today_str,
        "predict":  _predict_str,
        "investment": 10_000,
    },
    "Diversified — Green Score": {
        "tickers":  ["AAPL", "JPM", "XOM", "JNJ", "SPY"],
        "start":    "2020-01-01",
        "end":      _today_str,
        "predict":  _predict_str,
        "investment": 10_000,
    },
}

# ── Popular tickers ───────────────────────────────────────────────────────────
POPULAR_TICKERS = [
    # US Mega-cap Tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO",
    # US Finance
    "JPM", "BAC", "GS", "MS", "WFC", "BRK-B", "V", "MA",
    # US Healthcare / Pharma
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
    # US Consumer / Retail
    "WMT", "COST", "HD", "MCD", "SBUX", "NKE", "PG", "KO", "PEP",
    # US Energy
    "XOM", "CVX", "COP", "SLB",
    # US Industrials / Aerospace
    "BA", "CAT", "GE", "RTX", "HON",
    # US Semiconductor
    "AMD", "INTC", "QCOM", "MU", "TSM",
    # ETFs
    "SPY", "QQQ", "IWM", "GLD", "TLT",
    # International
    "SHEL", "BABA", "SONY", "SAP", "TM",
]

# ── Health score thresholds ───────────────────────────────────────────────────
HEALTH_RED_MAX    = 40
HEALTH_YELLOW_MAX = 70

# ── Sector concentration flag threshold ───────────────────────────────────────
SECTOR_CONCENTRATION_THRESHOLD = 0.40
