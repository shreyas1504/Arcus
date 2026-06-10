# ── backend/data/common_tickers.py ───────────────────────────────────────────
# Predefined sector, PE and PS values for popular tickers.
# This avoids slow yfinance network calls on initial dashboard load.

COMMON_TICKER_INFO = {
    # Technology
    'AAPL': {'sector': 'Technology', 'pe': 29.0, 'ps': 7.5},
    'MSFT': {'sector': 'Technology', 'pe': 35.0, 'ps': 11.5},
    'GOOGL': {'sector': 'Technology', 'pe': 24.0, 'ps': 6.0},
    'NVDA': {'sector': 'Technology', 'pe': 65.0, 'ps': 22.0},
    'CRM': {'sector': 'Technology', 'pe': 30.0, 'ps': 6.2},
    'ADBE': {'sector': 'Technology', 'pe': 32.0, 'ps': 9.5},
    'AMD': {'sector': 'Technology', 'pe': 40.0, 'ps': 8.0},
    'INTC': {'sector': 'Technology', 'pe': 31.0, 'ps': 2.2},
    'IBM': {'sector': 'Technology', 'pe': 20.0, 'ps': 2.8},
    'ORCL': {'sector': 'Technology', 'pe': 28.0, 'ps': 6.0},
    'PLTR': {'sector': 'Technology', 'pe': 80.0, 'ps': 18.5},
    'SNOW': {'sector': 'Technology', 'pe': 0.0, 'ps': 12.0},
    'AVGO': {'sector': 'Technology', 'pe': 35.0, 'ps': 12.5},
    'QCOM': {'sector': 'Technology', 'pe': 22.0, 'ps': 4.5},
    'MU': {'sector': 'Technology', 'pe': 25.0, 'ps': 4.0},
    'TSM': {'sector': 'Technology', 'pe': 26.0, 'ps': 8.0},
    'ARKK': {'sector': 'Technology', 'pe': 0.0, 'ps': 0.0},
    
    # Healthcare
    'UNH': {'sector': 'Healthcare', 'pe': 22.0, 'ps': 1.2},
    'JNJ': {'sector': 'Healthcare', 'pe': 15.0, 'ps': 4.0},
    'PFE': {'sector': 'Healthcare', 'pe': 12.0, 'ps': 3.0},
    'ABBV': {'sector': 'Healthcare', 'pe': 14.0, 'ps': 4.2},
    'TMO': {'sector': 'Healthcare', 'pe': 28.0, 'ps': 4.8},
    'MRK': {'sector': 'Healthcare', 'pe': 15.0, 'ps': 3.8},
    'LLY': {'sector': 'Healthcare', 'pe': 55.0, 'ps': 12.0},
    
    # Energy
    'XOM': {'sector': 'Energy', 'pe': 14.0, 'ps': 1.1},
    'CVX': {'sector': 'Energy', 'pe': 14.0, 'ps': 1.1},
    'COP': {'sector': 'Energy', 'pe': 12.0, 'ps': 2.2},
    'SLB': {'sector': 'Energy', 'pe': 15.0, 'ps': 2.0},
    'EOG': {'sector': 'Energy', 'pe': 10.0, 'ps': 2.0},
    'MPC': {'sector': 'Energy', 'pe': 8.0, 'ps': 0.8},
    
    # Financials
    'JPM': {'sector': 'Financials', 'pe': 12.0, 'ps': 2.8},
    'V': {'sector': 'Financials', 'pe': 30.0, 'ps': 15.0},
    'MA': {'sector': 'Financials', 'pe': 35.0, 'ps': 16.0},
    'BAC': {'sector': 'Financials', 'pe': 11.0, 'ps': 2.0},
    'GS': {'sector': 'Financials', 'pe': 12.0, 'ps': 2.2},
    'MS': {'sector': 'Financials', 'pe': 15.0, 'ps': 2.5},
    'BLK': {'sector': 'Financials', 'pe': 20.0, 'ps': 5.0},
    'BRK.B': {'sector': 'Financials', 'pe': 18.0, 'ps': 2.4},
    'PYPL': {'sector': 'Financials', 'pe': 15.0, 'ps': 2.0},
    'COIN': {'sector': 'Financials', 'pe': 30.0, 'ps': 8.0},
    'SPY': {'sector': 'Financials', 'pe': 22.0, 'ps': 3.0},
    'VOO': {'sector': 'Financials', 'pe': 22.0, 'ps': 3.0},
    'QQQ': {'sector': 'Financials', 'pe': 30.0, 'ps': 4.5},
    'VT': {'sector': 'Financials', 'pe': 18.0, 'ps': 2.0},
    'VTI': {'sector': 'Financials', 'pe': 21.0, 'ps': 2.5},
    'IVV': {'sector': 'Financials', 'pe': 22.0, 'ps': 3.0},
    'IWM': {'sector': 'Financials', 'pe': 18.0, 'ps': 1.8},
    'WFC': {'sector': 'Financials', 'pe': 11.0, 'ps': 2.2},
    
    # Consumer
    'AMZN': {'sector': 'Consumer', 'pe': 60.0, 'ps': 3.2},
    'TSLA': {'sector': 'Consumer', 'pe': 55.0, 'ps': 7.0},
    'HD': {'sector': 'Consumer', 'pe': 22.0, 'ps': 2.2},
    'NKE': {'sector': 'Consumer', 'pe': 28.0, 'ps': 3.2},
    'SBUX': {'sector': 'Consumer', 'pe': 24.0, 'ps': 3.0},
    'MCD': {'sector': 'Consumer', 'pe': 25.0, 'ps': 6.0},
    'WMT': {'sector': 'Consumer', 'pe': 28.0, 'ps': 0.7},
    'COST': {'sector': 'Consumer', 'pe': 50.0, 'ps': 1.2},
    'KO': {'sector': 'Consumer', 'pe': 23.0, 'ps': 5.8},
    'PEP': {'sector': 'Consumer', 'pe': 24.0, 'ps': 2.6},
    'PG': {'sector': 'Consumer', 'pe': 25.0, 'ps': 4.8},
    'DIS': {'sector': 'Consumer', 'pe': 70.0, 'ps': 2.2},
    'NFLX': {'sector': 'Consumer', 'pe': 40.0, 'ps': 6.2},
    'UBER': {'sector': 'Consumer', 'pe': 35.0, 'ps': 3.5},
    'SPOT': {'sector': 'Consumer', 'pe': 50.0, 'ps': 4.8},
    'SHOP': {'sector': 'Consumer', 'pe': 60.0, 'ps': 11.5},
    
    # Real Estate
    'AMT': {'sector': 'Real Estate', 'pe': 40.0, 'ps': 12.0},
    'PLD': {'sector': 'Real Estate', 'pe': 32.0, 'ps': 10.0},
    'CCI': {'sector': 'Real Estate', 'pe': 38.0, 'ps': 11.0},
    'SPG': {'sector': 'Real Estate', 'pe': 16.0, 'ps': 4.2},
    'O': {'sector': 'Real Estate', 'pe': 45.0, 'ps': 8.5},
    'WELL': {'sector': 'Real Estate', 'pe': 28.0, 'ps': 6.8},
    
    # Utilities
    'NEE': {'sector': 'Utilities', 'pe': 18.0, 'ps': 4.0},
    'DUK': {'sector': 'Utilities', 'pe': 16.0, 'ps': 2.8},
    'SO': {'sector': 'Utilities', 'pe': 18.0, 'ps': 3.2},
    'D': {'sector': 'Utilities', 'pe': 14.0, 'ps': 2.2},
    'AEP': {'sector': 'Utilities', 'pe': 17.0, 'ps': 2.5},
    'SRE': {'sector': 'Utilities', 'pe': 19.0, 'ps': 2.8},
    
    # Industrials
    'BA': {'sector': 'Industrials', 'pe': 0.0, 'ps': 1.8},
    'CAT': {'sector': 'Industrials', 'pe': 15.0, 'ps': 2.2},
    'GE': {'sector': 'Industrials', 'pe': 22.0, 'ps': 2.0},
    'RTX': {'sector': 'Industrials', 'pe': 19.0, 'ps': 1.8},
    'HON': {'sector': 'Industrials', 'pe': 21.0, 'ps': 3.0},
    
    # Other / Bonds / Commodity
    'GLD': {'sector': 'Other', 'pe': 0.0, 'ps': 0.0},
    'TLT': {'sector': 'Other', 'pe': 0.0, 'ps': 0.0},
}
