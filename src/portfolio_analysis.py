import yfinance as yf
import pandas as pd
import numpy as np
from scipy.optimize import minimize

def download_data(tickers, start_date, end_date):
    """
    Download stock price data using yfinance.
    
    Args:
        tickers: str or list of ticker symbols
        start_date: start date for data download
        end_date: end date for data download
    
    Returns:
        DataFrame with date index and tickers as columns (Close prices)
    """
    # Convert single ticker to list for consistent handling
    if isinstance(tickers, str):
        tickers = [tickers]
    
    # Download data - yfinance returns MultiIndex when multiple tickers
    data = yf.download(tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)
    
    # Extract Close prices
    if len(tickers) == 1:
        # Single ticker: data is already a DataFrame with MultiIndex columns
        if 'Close' in data.columns:
            df = data['Close'].to_frame(name=tickers[0])
        else:
            df = data[('Close', tickers[0])].to_frame(name=tickers[0])
    else:
        # Multiple tickers: extract Close prices for each ticker
        df = pd.DataFrame()
        for ticker in tickers:
            if ('Close', ticker) in data.columns:
                df[ticker] = data[('Close', ticker)]
            elif ticker in data.columns.get_level_values(0):
                df[ticker] = data[ticker]['Close']
    
    # Ensure date index and drop any rows with NaN
    return df.dropna()

def calculate_returns(prices):
    """
    Calculate log returns from price DataFrame.
    
    Args:
        prices: DataFrame with date index and tickers as columns
    
    Returns:
        DataFrame of log returns: np.log(prices / prices.shift(1))
    """
    return np.log(prices / prices.shift(1)).dropna()

def optimize_portfolio(returns):
    num_assets = returns.shape[1]
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0, 1) for _ in range(num_assets))

    def negative_sharpe(weights):
        port_ret = np.dot(weights, returns.mean()) * 252
        port_vol = np.sqrt(np.dot(weights.T, returns.cov().dot(weights)) * 252)
        return -port_ret / port_vol

    result = minimize(negative_sharpe, num_assets * [1./num_assets], method='SLSQP', bounds=bounds, constraints=constraints)
    return result.x

def monte_carlo_simulation(prices, n_simulations=500, n_days=252):
    """
    Monte Carlo simulation for portfolio value using historical mean and covariance.
    
    Args:
        prices: DataFrame with date index and tickers as columns
        n_simulations: number of simulation paths
        n_days: number of days to simulate forward
    
    Returns:
        numpy array of shape (n_simulations, n_days) representing portfolio value over time
    """
    # Calculate log returns
    returns = calculate_returns(prices)
    
    # Calculate portfolio-level statistics (equal weights assumed for portfolio-level simulation)
    # Portfolio return is average of individual asset returns
    portfolio_returns = returns.mean(axis=1)
    
    # Annualized mean return and volatility
    mean_return = portfolio_returns.mean() * 252  # Annualized
    volatility = portfolio_returns.std() * np.sqrt(252)  # Annualized
    
    # Starting portfolio value (average of last prices)
    last_price = prices.iloc[-1].mean()
    
    # Daily drift and volatility
    daily_drift = mean_return / 252
    daily_vol = volatility / np.sqrt(252)
    
    # Generate simulations
    simulations = np.zeros((n_simulations, n_days))
    
    for i in range(n_simulations):
        price = last_price
        for t in range(n_days):
            # Geometric Brownian Motion: dS = S * (mu*dt + sigma*dW)
            price *= np.exp(daily_drift - 0.5 * daily_vol**2 + daily_vol * np.random.normal())
            simulations[i, t] = price
    
    return simulations

def monte_carlo_simulation_individual(prices, n_simulations=300, n_days=252):
    """
    Monte Carlo simulation for individual stocks.
    
    Args:
        prices: DataFrame with date index and tickers as columns
        n_simulations: number of simulation paths per ticker
        n_days: number of days to simulate forward
    
    Returns:
        dict with ticker keys and numpy arrays of shape (n_simulations, n_days)
    """
    simulations_dict = {}
    tickers = prices.columns
    
    # Calculate log returns once
    returns = calculate_returns(prices)

    for ticker in tickers:
        # Get historical returns for this ticker
        ticker_returns = returns[ticker]
        
        # Annualized statistics
        mean_return = ticker_returns.mean() * 252  # Annualized
        volatility = ticker_returns.std() * np.sqrt(252)  # Annualized
        
        # Starting price
        last_price = prices[ticker].iloc[-1]
        
        # Daily drift and volatility
        daily_drift = mean_return / 252
        daily_vol = volatility / np.sqrt(252)
        
        # Generate simulations
        simulations = np.zeros((n_simulations, n_days))
        
        for i in range(n_simulations):
            price = last_price
            for t in range(n_days):
                # Geometric Brownian Motion
                price *= np.exp(daily_drift - 0.5 * daily_vol**2 + daily_vol * np.random.normal())
                simulations[i, t] = price
        
        simulations_dict[ticker] = simulations

    return simulations_dict
