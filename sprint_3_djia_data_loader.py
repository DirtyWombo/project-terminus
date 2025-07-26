# sprint_3_djia_data_loader.py
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

def load_djia_data():
    """
    Download historical data for DJIA components (large-cap value universe)
    """
    
    # DJIA 30 components as specified in Sprint #3 directive
    DJIA_UNIVERSE = [
        'AXP', 'AMGN', 'AAPL', 'BA', 'CAT', 'CSCO', 'CVX', 'GS', 'HD', 'HON', 
        'IBM', 'INTC', 'JNJ', 'KO', 'JPM', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE',
        'PG', 'TRV', 'UNH', 'CRM', 'VZ', 'V', 'WBA', 'WMT', 'DIS', 'DOW'
    ]
    
    # Data parameters - same period as previous tests for consistency
    START_DATE = '2018-01-01'
    END_DATE = '2023-12-31'
    
    print("=" * 80)
    print("SPRINT #3: DJIA DATA LOADER")
    print("=" * 80)
    print(f"Universe: Dow Jones Industrial Average (30 stocks)")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Objective: Test large-cap value hypothesis")
    print("=" * 80)
    
    # Create data directory
    data_dir = 'data/sprint_3_djia'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}")
    
    # Download data for each stock
    successful_downloads = []
    failed_downloads = []
    
    for i, ticker in enumerate(DJIA_UNIVERSE, 1):
        try:
            print(f"[{i:2d}/30] Downloading {ticker}...", end=' ')
            
            # Download data
            data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
            
            if data.empty:
                print("No data")
                failed_downloads.append(ticker)
                continue
            
            # Clean and prepare data
            data = data.copy()
            data.index.name = 'Date'
            
            # Ensure we have required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_columns):
                print("Missing columns")
                failed_downloads.append(ticker)
                continue
            
            # Handle any NaN values
            data = data.dropna()
            
            if len(data) < 100:  # Minimum data points
                print("Insufficient data")
                failed_downloads.append(ticker)
                continue
            
            # Save to CSV
            file_path = os.path.join(data_dir, f'{ticker}.csv')
            data.to_csv(file_path)
            
            print(f"OK {len(data)} bars saved")
            successful_downloads.append(ticker)
            
        except Exception as e:
            print(f"ERROR: {str(e)[:50]}")
            failed_downloads.append(ticker)
    
    # Summary
    print("\n" + "=" * 80)
    print("DJIA DATA DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"Successful Downloads: {len(successful_downloads)}/30")
    print(f"Failed Downloads: {len(failed_downloads)}/30")
    
    if successful_downloads:
        print(f"\nSuccessfully Downloaded:")
        for ticker in successful_downloads:
            print(f"   {ticker}")
    
    if failed_downloads:
        print(f"\nFailed Downloads:")
        for ticker in failed_downloads:
            print(f"   {ticker}")
    
    # Data quality check
    if successful_downloads:
        print(f"\nData Quality Check:")
        sample_file = os.path.join(data_dir, f'{successful_downloads[0]}.csv')
        sample_data = pd.read_csv(sample_file, index_col='Date', parse_dates=True)
        
        print(f"Sample Stock: {successful_downloads[0]}")
        print(f"Date Range: {sample_data.index[0].date()} to {sample_data.index[-1].date()}")
        print(f"Total Trading Days: {len(sample_data)}")
        print(f"Columns: {list(sample_data.columns)}")
        
        # Check for any obvious data issues
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in sample_data.columns:
                if (sample_data[col] <= 0).any():
                    print(f"Warning: {col} has zero or negative values")
                if sample_data[col].isnull().any():
                    print(f"Warning: {col} has missing values")
    
    print("\n" + "=" * 80)
    
    if len(successful_downloads) >= 25:  # Need at least 25 out of 30 for robust test
        print("DATA READY FOR SPRINT #3 BACKTESTING")
        print("Large-cap value universe successfully prepared!")
    else:
        print("WARNING: Insufficient data for robust backtesting")
        print("Consider manual data verification or alternative data sources")
    
    print("=" * 80)
    
    return {
        'universe': DJIA_UNIVERSE,
        'successful': successful_downloads,
        'failed': failed_downloads,
        'data_dir': data_dir,
        'period': f"{START_DATE} to {END_DATE}"
    }

if __name__ == '__main__':
    results = load_djia_data()
    print(f"\nUniverse ready for Sprint #3: {len(results['successful'])} stocks available")