import numpy as np
import pandas as pd

def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """Calculates the Sharpe ratio of a returns stream."""
    if np.std(returns) == 0:
        return 0.0
    excess_returns = returns - risk_free_rate
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) # Annualized

def calculate_sortino_ratio(returns, risk_free_rate=0.0):
    """Calculates the Sortino ratio of a returns stream."""
    excess_returns = returns - risk_free_rate
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = np.std(downside_returns)
    if downside_std == 0:
        return 0.0
    return np.mean(excess_returns) / downside_std * np.sqrt(252) # Annualized

def calculate_max_drawdown(portfolio_values):
    """Calculates the maximum drawdown of a portfolio value series."""
    if portfolio_values.empty:
        return 0.0
    peak = portfolio_values.expanding(min_periods=1).max()
    drawdown = (portfolio_values - peak) / peak
    return drawdown.min()
