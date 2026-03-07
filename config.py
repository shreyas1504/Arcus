# ── config.py ──────────────────────────────────────────────────────────────
# Central place for all constants. Edit here; everywhere else imports these.

# Risk & finance constants
RISK_FREE_RATE = 0.04          # Annual risk-free rate (4% — approx current T-bill)
VAR_CONFIDENCE_LEVEL = 0.95    # 95th-percentile Value at Risk
TRADING_DAYS = 252             # Trading days per year

# Simulation defaults
DEFAULT_SIMULATIONS = 300
DEFAULT_DAYS = 252

# UI defaults
DEFAULT_TICKERS = "AAPL,MSFT,GOOGL"
DEFAULT_START_DATE = "2020-01-01"
DEFAULT_END_DATE = "2024-12-31"

# Popular tickers shown in the setup-page multiselect dropdown
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

# Health score thresholds
HEALTH_RED_MAX = 40
HEALTH_YELLOW_MAX = 70
# > 70 = green

# Sector concentration flag threshold (40%)
SECTOR_CONCENTRATION_THRESHOLD = 0.40
