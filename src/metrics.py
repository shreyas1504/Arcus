import numpy as np

def sharpe_ratio(returns, risk_free_rate=0.01):
    """
    Calculate annualized Sharpe ratio.
    
    Args:
        returns: array-like of daily returns
        risk_free_rate: annual risk-free rate (default 0.01 = 1%)
    
    Returns:
        Annualized Sharpe ratio
    """
    # Convert to numpy array if needed
    returns = np.array(returns)
    
    # Daily risk-free rate
    daily_rf = risk_free_rate / 252
    
    # Excess returns
    excess_returns = returns - daily_rf
    
    # Annualized mean and std
    annualized_mean = np.mean(excess_returns) * 252
    annualized_std = np.std(returns) * np.sqrt(252)
    
    # Avoid division by zero
    if annualized_std == 0:
        return 0.0
    
    return annualized_mean / annualized_std

def calculate_beta(stock_returns, market_returns):
    """
    Calculate beta of stock relative to market.
    
    Args:
        stock_returns: array-like of daily stock returns
        market_returns: array-like of daily market returns
    
    Returns:
        Beta coefficient
    """
    stock_returns = np.array(stock_returns)
    market_returns = np.array(market_returns)
    
    # Calculate covariance and variance
    cov = np.cov(stock_returns, market_returns)[0][1]
    var_market = np.var(market_returns)
    
    # Avoid division by zero
    if var_market == 0:
        return 0.0
    
    return cov / var_market

def calculate_var(returns, confidence_level=0.95):
    """
    Calculate Value at Risk (VaR) at specified confidence level.
    
    Args:
        returns: array-like of daily returns
        confidence_level: confidence level (default 0.95 = 95%)
    
    Returns:
        VaR as a positive number representing the maximum expected loss
        (negative of the percentile on the loss side)
    """
    returns = np.array(returns)
    
    # Calculate the percentile on the negative side (losses)
    # For 95% confidence, we want the 5th percentile of returns (worst case)
    percentile = (1 - confidence_level) * 100
    var_value = np.percentile(returns, percentile)
    
    # Return as positive number (loss amount)
    # If var_value is already negative, return its absolute value
    # If positive, return negative (unusual but possible)
    return abs(var_value) if var_value < 0 else -var_value
