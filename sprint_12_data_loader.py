# sprint_12_data_loader.py
# Sprint 12: S&P 500 Universe Data Loading
import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime
from sp500_ticker_fetcher import get_sp500_tickers

# Define the universe and timeframe for Sprint 12
START_DATE = '2018-01-01'
END_DATE = '2023-12-31'
DATA_DIR = 'data/sprint_12'

def download_sp500_data(batch_size=50, delay=1.0):
    """
    Downloads daily OHLCV data for the entire S&P 500 universe.
    
    Args:
        batch_size (int): Number of tickers to download at once
        delay (float): Delay between batches to avoid rate limiting
    """
    # Get S&P 500 universe
    universe = get_sp500_tickers()
    
    if not universe:
        print("ERROR: Could not fetch S&P 500 tickers")
        return
    
    print(f"Starting S&P 500 data download for {len(universe)} tickers...")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Batch size: {batch_size}, Delay between batches: {delay}s")
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    successful_downloads = 0
    failed_downloads = []
    
    # Process in batches to avoid overwhelming the API
    for i in range(0, len(universe), batch_size):
        batch = universe[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(universe) + batch_size - 1) // batch_size
        
        print(f"\n--- Processing Batch {batch_num}/{total_batches} ---")
        print(f"Tickers: {batch[:5]}{'...' if len(batch) > 5 else ''}")
        
        try:
            # Download batch data
            batch_data = yf.download(batch, start=START_DATE, end=END_DATE, progress=False)
            
            # Process each ticker in the batch
            for ticker in batch:
                try:
                    if len(batch) == 1:
                        # Single ticker - data is not multi-level
                        ticker_df = batch_data.copy()
                    else:
                        # Multiple tickers - extract specific ticker data
                        ticker_df = batch_data.loc[:, (slice(None), ticker)]
                        if ticker_df.empty:
                            continue
                        ticker_df.columns = ticker_df.columns.droplevel(1)
                    
                    # Clean data - remove NaN rows (typically pre-IPO dates)
                    cleaned_df = ticker_df.dropna()
                    
                    if not cleaned_df.empty and len(cleaned_df) > 252:  # At least 1 year of data
                        file_path = os.path.join(DATA_DIR, f'{ticker}.csv')
                        cleaned_df.to_csv(file_path)
                        successful_downloads += 1
                        print(f"  SUCCESS {ticker}: {len(cleaned_df)} bars saved")
                    else:
                        failed_downloads.append(f"{ticker} (insufficient data)")
                        print(f"  FAILED {ticker}: insufficient data ({len(cleaned_df) if not cleaned_df.empty else 0} bars)")
                        
                except Exception as e:
                    failed_downloads.append(f"{ticker} (error: {str(e)[:50]})")
                    print(f"  FAILED {ticker}: {str(e)[:50]}")
            
            # Rate limiting delay between batches
            if i + batch_size < len(universe):
                print(f"  Waiting {delay}s before next batch...")
                time.sleep(delay)
                
        except Exception as e:
            print(f"  ERROR: Batch download failed: {e}")
            for ticker in batch:
                failed_downloads.append(f"{ticker} (batch error)")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SPRINT 12 DATA DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"Total tickers attempted: {len(universe)}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {len(failed_downloads)}")
    print(f"Success rate: {successful_downloads/len(universe)*100:.1f}%")
    
    if failed_downloads:
        print(f"\nFailed tickers ({len(failed_downloads)}):")
        for failure in failed_downloads[:20]:  # Show first 20 failures
            print(f"  - {failure}")
        if len(failed_downloads) > 20:
            print(f"  ... and {len(failed_downloads)-20} more")
    
    # Save universe file with successful tickers
    successful_tickers = []
    for ticker in universe:
        file_path = os.path.join(DATA_DIR, f'{ticker}.csv')
        if os.path.exists(file_path):
            successful_tickers.append(ticker)
    
    universe_file = os.path.join(DATA_DIR, 'sp500_universe_available.txt')
    with open(universe_file, 'w') as f:
        f.write(f"# S&P 500 Universe with Available Data - Sprint 12\n")
        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total tickers: {len(successful_tickers)}\n\n")
        for ticker in sorted(successful_tickers):
            f.write(f"{ticker}\n")
    
    print(f"\nFinal universe saved to: {universe_file}")
    print(f"Data directory: {DATA_DIR}")
    
    return successful_tickers

if __name__ == '__main__':
    # Download S&P 500 data with conservative settings
    successful_tickers = download_sp500_data(batch_size=25, delay=2.0)
    
    if successful_tickers:
        print(f"\nSUCCESS: Sprint 12 data ready with {len(successful_tickers)} tickers")
    else:
        print("\nFAILED: No data downloaded successfully")