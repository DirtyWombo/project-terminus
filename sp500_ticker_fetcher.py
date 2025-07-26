# sp500_ticker_fetcher.py
# Sprint 12: S&P 500 Universe Expansion
import pandas as pd
import requests
from datetime import datetime

def get_sp500_tickers():
    """
    Scrapes the current list of S&P 500 tickers from Wikipedia.
    Returns a list of tickers formatted for yfinance.
    """
    print("Fetching S&P 500 ticker list from Wikipedia...")
    
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        table = pd.read_html(url)
        tickers = table[0]['Symbol'].tolist()
        
        # Wikipedia tickers sometimes have '.', which needs to be replaced with '-' for yfinance
        tickers = [ticker.replace('.', '-') for ticker in tickers]
        
        print(f"SUCCESS: Retrieved {len(tickers)} S&P 500 tickers")
        return tickers
        
    except Exception as e:
        print(f"ERROR: Failed to fetch S&P 500 tickers: {e}")
        return []

def save_sp500_universe(filename='sp500_universe.txt'):
    """
    Fetch S&P 500 tickers and save to file for reference.
    """
    tickers = get_sp500_tickers()
    
    if tickers:
        with open(filename, 'w') as f:
            f.write(f"# S&P 500 Universe - Retrieved {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total tickers: {len(tickers)}\n\n")
            for ticker in sorted(tickers):
                f.write(f"{ticker}\n")
        
        print(f"SUCCESS: S&P 500 universe saved to {filename}")
        return tickers
    else:
        print("ERROR: No tickers to save")
        return []

if __name__ == '__main__':
    # Fetch and save the S&P 500 universe
    universe = save_sp500_universe()
    
    if universe:
        print(f"\nSAMPLE TICKERS: {universe[:10]}")
        print(f"TOTAL COUNT: {len(universe)}")
    else:
        print("FAILED: Could not retrieve S&P 500 universe")