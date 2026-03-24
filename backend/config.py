# ── backend/config.py ──────────────────────────────────────────────────────
# Central constants for the Pulse backend. Ported from the Streamlit config.

import datetime as _dt

# ── Brand ─────────────────────────────────────────────────────────────────────
BRAND_NAME    = "Pulse"
BRAND_TAGLINE = "Institutional-grade portfolio intelligence. For everyone."

# ── Risk & finance constants ───────────────────────────────────────────────────
RISK_FREE_RATE       = 0.04
VAR_CONFIDENCE_LEVEL = 0.95
TRADING_DAYS         = 252
ROLLING_WINDOW       = 60

# ── Simulation defaults ────────────────────────────────────────────────────────
DEFAULT_SIMULATIONS = 300
DEFAULT_DAYS        = 252

# ── UI defaults ───────────────────────────────────────────────────────────────
DEFAULT_TICKERS    = "AAPL,MSFT,GOOGL"
DEFAULT_START_DATE = "2020-01-01"
DEFAULT_END_DATE   = "2024-12-31"
BENCHMARK_TICKER   = "^GSPC"
BENCHMARK_NAME     = "S&P 500"

# ── Demo portfolios ───────────────────────────────────────────────────────────
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
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO",
    "JPM", "BAC", "GS", "MS", "WFC", "BRK-B", "V", "MA",
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
    "WMT", "COST", "HD", "MCD", "SBUX", "NKE", "PG", "KO", "PEP",
    "XOM", "CVX", "COP", "SLB",
    "BA", "CAT", "GE", "RTX", "HON",
    "AMD", "INTC", "QCOM", "MU", "TSM",
    "SPY", "QQQ", "IWM", "GLD", "TLT",
    "SHEL", "BABA", "SONY", "SAP", "TM",
]

# ── Health score thresholds ───────────────────────────────────────────────────
HEALTH_RED_MAX    = 40
HEALTH_YELLOW_MAX = 70

# ── Sector concentration flag threshold ───────────────────────────────────────
SECTOR_CONCENTRATION_THRESHOLD = 0.40
