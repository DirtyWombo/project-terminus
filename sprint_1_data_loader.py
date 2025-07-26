# sprint_1_data_loader.py (Version 2 - Hardened)
import yfinance as yf
import pandas as pd
import os

# Define the universe and timeframe for this sprint
UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
START_DATE = '2018-01-01'
END_DATE = '2023-12-31'
DATA_DIR = 'data/sprint_1'

def download_sprint_data():
    """
    Downloads daily OHLCV data for the sprint universe and cleans any
    rows with NaN values, which typically occur before a stock's IPO date.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    print(f"Downloading data for {len(UNIVERSE)} tickers...")
    
    # Download all data at once
    data = yf.download(UNIVERSE, start=START_DATE, end=END_DATE)
    
    for ticker in UNIVERSE:
        # Correctly slice the multi-level DataFrame for the specific ticker
        ticker_df = data.loc[:, (slice(None), ticker)]
        ticker_df.columns = ticker_df.columns.droplevel(1) # Remove the ticker level from columns
        
        # --- CRITICAL FIX: Remove all rows with NaN values ---
        cleaned_df = ticker_df.dropna()
        
        if not cleaned_df.empty:
            file_path = os.path.join(DATA_DIR, f'{ticker}.csv')
            cleaned_df.to_csv(file_path)
            print(f"Saved CLEANED data for {ticker} to {file_path}")
        else:
            print(f"Could not download sufficient data for {ticker}")

if __name__ == '__main__':
    download_sprint_data()