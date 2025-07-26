# sprint_8_data_loader.py
import yfinance as yf
import pandas as pd
import os
import time

UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
DATA_DIR = 'data/sprint_8'

def get_fundamental_data():
    """
    Downloads and saves key financial statement data for the universe.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    all_fundamentals = {}

    print("Downloading fundamental data...")
    for ticker in UNIVERSE:
        print(f"Fetching data for {ticker}...")
        stock = yf.Ticker(ticker)
        
        # We need info, financials, and balance sheet
        info = stock.info
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        
        # Check if we got the data we need
        if not financials.empty and not balance_sheet.empty:
            all_fundamentals[ticker] = {
                'info': info,
                'financials': financials,
                'balance_sheet': balance_sheet
            }
        else:
            print(f"WARNING: Could not retrieve complete fundamental data for {ticker}")
        
        time.sleep(1) # Be respectful to the API

    # Save the data to a single file for easy loading later
    # Using pickle to preserve the DataFrame structures
    pd.to_pickle(all_fundamentals, os.path.join(DATA_DIR, 'fundamental_data.pkl'))
    print(f"\nFundamental data saved to {os.path.join(DATA_DIR, 'fundamental_data.pkl')}")

if __name__ == '__main__':
    # We also still need the price data from Sprint #1
    # Assuming it's already downloaded in 'data/sprint_1'
    get_fundamental_data()