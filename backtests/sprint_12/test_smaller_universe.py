# backtests/sprint_12/test_smaller_universe.py
"""
Test Sprint 12 approach with smaller universe to validate methodology
before running full 216-stock backtest.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from backtests.sprint_12.composite_qvm_backtest_sp500 import run_sprint12_backtest, load_sp500_universe

# Test with smaller universe
def test_smaller_universe():
    """Test with top 50 S&P 500 stocks by market cap"""
    
    # Top 50 largest S&P 500 companies  
    TOP_50_SP500 = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'ABBV', 'PFE', 'KO',
        'BAC', 'AVGO', 'PEP', 'COST', 'TMO', 'WMT', 'DIS', 'ABT', 'CRM', 'ACN',
        'LIN', 'MRK', 'VZ', 'DHR', 'TXN', 'NKE', 'ORCL', 'ADBE', 'CMCSA', 'T',
        'WFC', 'PM', 'BMY', 'RTX', 'NEE', 'COP', 'UNP', 'IBM', 'AMD', 'LOW'
    ]
    
    # Get actual available universe
    full_universe = load_sp500_universe()
    
    # Filter to only tickers we have data for
    test_universe = [ticker for ticker in TOP_50_SP500 if ticker in full_universe]
    
    print(f"Testing with {len(test_universe)} stocks from top 50 S&P 500")
    print(f"Test universe: {test_universe[:10]}{'...' if len(test_universe) > 10 else ''}")
    
    # Create a temporary universe file for testing
    test_universe_file = 'data/sprint_12/test_universe.txt'
    with open(test_universe_file, 'w') as f:
        f.write("# Test Universe - Top S&P 500 Stocks\n")
        f.write(f"# Total tickers: {len(test_universe)}\n\n")
        for ticker in test_universe:
            f.write(f"{ticker}\n")
    
    # Temporarily replace the universe loader function
    original_load_func = load_sp500_universe
    
    def load_test_universe():
        return test_universe
    
    # Monkey patch the function
    import backtests.sprint_12.composite_qvm_backtest_sp500 as backtest_module
    backtest_module.load_sp500_universe = load_test_universe
    
    try:
        # Run the test
        results = run_sprint12_backtest()
        return results
    finally:
        # Restore original function
        backtest_module.load_sp500_universe = original_load_func
        
        # Clean up test file
        if os.path.exists(test_universe_file):
            os.remove(test_universe_file)

if __name__ == '__main__':
    test_smaller_universe()