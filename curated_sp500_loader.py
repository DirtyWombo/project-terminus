# curated_sp500_loader.py
# Sprint 12: Curated Large-Cap S&P 500 Universe
import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime

# Curated S&P 500 universe - major companies across sectors
CURATED_SP500 = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'CRM', 'ORCL', 'ADBE', 'NFLX',
    'INTC', 'AMD', 'CSCO', 'IBM', 'QCOM', 'AVGO', 'TXN', 'MU', 'NOW', 'INTU',
    
    # Healthcare
    'UNH', 'JNJ', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'LLY', 'DHR', 'BMY',
    'AMGN', 'GILD', 'CVS', 'MDT', 'CI', 'HUM', 'SYK', 'BDX', 'ZTS', 'REGN',
    
    # Financials  
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'COF', 'AXP', 'USB', 'TFC',
    'PNC', 'BK', 'STT', 'BLK', 'SCHW', 'CB', 'PGR', 'AON', 'MMC', 'AIG',
    
    # Consumer Discretionary
    'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'BKNG', 'MAR', 'HLT',
    'ABNB', 'CMG', 'ORLY', 'AZO', 'LULU', 'DECK', 'DPZ', 'YUM', 'ULTA', 'LVS',
    
    # Consumer Staples
    'PG', 'KO', 'PEP', 'WMT', 'COST', 'MDLZ', 'CL', 'KMB', 'GIS', 'K',
    'HSY', 'CPB', 'CAG', 'SJM', 'CHD', 'MKC', 'TSN', 'HRL', 'CLX', 'KHC',
    
    # Communication Services
    'GOOG', 'DIS', 'CMCSA', 'VZ', 'T', 'NFLX', 'TMUS', 'CHTR', 'EA', 'ATVI',
    'PARA', 'WBD', 'DISH', 'FOXA', 'FOX', 'MTCH', 'PINS', 'SNAP', 'TWTR', 'ROKU',
    
    # Industrials
    'BA', 'CAT', 'UNP', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'MMM', 'GE',
    'EMR', 'ETN', 'ITW', 'PH', 'CMI', 'FDX', 'NSC', 'CSX', 'NOC', 'GD',
    
    # Energy
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'MPC', 'VLO', 'KMI', 'OKE',
    'WMB', 'EPD', 'ET', 'LNG', 'FANG', 'DVN', 'BKR', 'HAL', 'MRO', 'APA',
    
    # Utilities
    'NEE', 'SO', 'DUK', 'AEP', 'EXC', 'XEL', 'D', 'PCG', 'SRE', 'PEG',
    'ED', 'EIX', 'AWK', 'ATO', 'CMS', 'DTE', 'NI', 'LNT', 'EVRG', 'ES',
    
    # Materials  
    'LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM', 'DOW', 'DD', 'PPG', 'NUE',
    'VMC', 'MLM', 'PKG', 'AMCR', 'AVY', 'CF', 'FMC', 'LYB', 'ALB', 'MOS',
    
    # Real Estate
    'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'SPG', 'DLR', 'O', 'SBAC', 'WY',
    'AVB', 'EQR', 'VTR', 'ESS', 'MAA', 'UDR', 'CPT', 'HST', 'REG', 'BXP'
]

START_DATE = '2018-01-01'
END_DATE = '2023-12-31'
DATA_DIR = 'data/sprint_12'

def download_curated_sp500_data(batch_size=20, delay=1.5):
    """
    Downloads data for curated S&P 500 universe with better error handling.
    """
    print(f"Starting curated S&P 500 data download for {len(CURATED_SP500)} tickers...")
    print(f"Date range: {START_DATE} to {END_DATE}")
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    successful_downloads = 0
    failed_downloads = []
    
    # Process in smaller batches
    for i in range(0, len(CURATED_SP500), batch_size):
        batch = CURATED_SP500[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(CURATED_SP500) + batch_size - 1) // batch_size
        
        print(f"\n--- Processing Batch {batch_num}/{total_batches} ---")
        print(f"Tickers: {', '.join(batch[:5])}{'...' if len(batch) > 5 else ''}")
        
        try:
            # Download batch with individual ticker handling
            for ticker in batch:
                try:
                    # Download individual ticker to avoid batch failures
                    ticker_data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
                    
                    if not ticker_data.empty:
                        # Clean data
                        cleaned_df = ticker_data.dropna()
                        
                        if len(cleaned_df) > 252:  # At least 1 year of data
                            file_path = os.path.join(DATA_DIR, f'{ticker}.csv')
                            cleaned_df.to_csv(file_path)
                            successful_downloads += 1
                            print(f"  SUCCESS {ticker}: {len(cleaned_df)} bars")
                        else:
                            failed_downloads.append(f"{ticker} (insufficient data: {len(cleaned_df)} bars)")
                            print(f"  FAILED {ticker}: insufficient data ({len(cleaned_df)} bars)")
                    else:
                        failed_downloads.append(f"{ticker} (no data returned)")
                        print(f"  FAILED {ticker}: no data returned")
                        
                except Exception as e:
                    error_msg = str(e)[:100]
                    failed_downloads.append(f"{ticker} (error: {error_msg})")
                    print(f"  FAILED {ticker}: {error_msg}")
                
                # Small delay between individual tickers
                time.sleep(0.2)
            
            # Delay between batches
            if i + batch_size < len(CURATED_SP500):
                print(f"  Waiting {delay}s before next batch...")
                time.sleep(delay)
                
        except Exception as e:
            print(f"  ERROR: Batch processing failed: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SPRINT 12 CURATED S&P 500 DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"Total tickers attempted: {len(CURATED_SP500)}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {len(failed_downloads)}")
    print(f"Success rate: {successful_downloads/len(CURATED_SP500)*100:.1f}%")
    
    if failed_downloads:
        print(f"\nFirst 10 failed tickers:")
        for failure in failed_downloads[:10]:
            print(f"  - {failure}")
    
    # Create updated universe file
    successful_tickers = []
    for ticker in CURATED_SP500:
        file_path = os.path.join(DATA_DIR, f'{ticker}.csv')
        if os.path.exists(file_path):
            successful_tickers.append(ticker)
    
    universe_file = os.path.join(DATA_DIR, 'curated_sp500_universe.txt')
    with open(universe_file, 'w') as f:
        f.write(f"# Curated S&P 500 Universe - Sprint 12\n")
        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total tickers: {len(successful_tickers)}\n\n")
        for ticker in sorted(successful_tickers):
            f.write(f"{ticker}\n")
    
    print(f"\nFinal universe saved to: {universe_file}")
    return successful_tickers

if __name__ == '__main__':
    successful_tickers = download_curated_sp500_data(batch_size=15, delay=1.0)
    print(f"\nSUCCESS: Sprint 12 ready with {len(successful_tickers)} tickers")