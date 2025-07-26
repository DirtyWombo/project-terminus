# features/qvm_factors.py
import pandas as pd

def calculate_quality_factor(fundamentals):
    """Calculates Return on Equity (ROE) as our Quality metric."""
    try:
        net_income = fundamentals['financials'].loc['Net Income']
        # Try multiple equity field names
        equity_fields = ['Stockholders Equity', 'Total Stockholder Equity', 'Common Stock Equity']
        
        stockholder_equity = None
        for field in equity_fields:
            if field in fundamentals['balance_sheet'].index:
                stockholder_equity = fundamentals['balance_sheet'].loc[field]
                break
        
        if stockholder_equity is None:
            return -float('inf')
        
        # Use the most recent year's data
        roe = net_income.iloc[0] / stockholder_equity.iloc[0]
        return roe
    except (KeyError, IndexError, ZeroDivisionError):
        return -float('inf') # Return a very bad score if data is missing

def calculate_value_factor(fundamentals):
    """Calculates Earnings Yield (EBIT/EV) as our Value metric."""
    try:
        ebit = fundamentals['financials'].loc['EBIT'].iloc[0]  # Fixed case sensitivity
        enterprise_value = fundamentals['info'].get('enterpriseValue')
        if ebit and enterprise_value and enterprise_value > 0:
            return ebit / enterprise_value
        return -float('inf')
    except (KeyError, IndexError, TypeError, ZeroDivisionError):
        return -float('inf')

def calculate_momentum_factor(price_data):
    """Calculates 6-month price momentum."""
    if len(price_data) < 126: # Approx. 6 months of trading days
        return -float('inf')
    
    # Calculate the return over the last 6 months
    momentum = (price_data['Close'].iloc[-1] / price_data['Close'].iloc[-126]) - 1
    return momentum