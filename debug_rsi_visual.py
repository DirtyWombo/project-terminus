#!/usr/bin/env python3
"""
Sprint 7.1 Task 1: Visual RSI Indicator Analysis
Debug script to visualize RSI levels for CRWD, SNOW, PLTR
"""

import pandas as pd
import matplotlib.pyplot as plt
import pandas_ta as ta
import os

def load_stock_data(ticker):
    """Load stock data from CSV file"""
    data_path = f"data/sprint_1/{ticker}.csv"
    if not os.path.exists(data_path):
        print(f"Error: Data file not found for {ticker}")
        return None
    
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')
    return df

def calculate_and_plot_rsi(ticker, rsi_period=14):
    """Calculate RSI and create visualization"""
    print(f"\nAnalyzing {ticker}...")
    
    # Load data
    df = load_stock_data(ticker)
    if df is None:
        return
    
    # Calculate RSI
    df['RSI'] = ta.rsi(df['Close'], length=rsi_period)
    
    # Print RSI statistics
    rsi_stats = df['RSI'].describe()
    print(f"{ticker} RSI Statistics (period={rsi_period}):")
    print(f"  Min RSI: {rsi_stats['min']:.2f}")
    print(f"  Max RSI: {rsi_stats['max']:.2f}")
    print(f"  Mean RSI: {rsi_stats['mean']:.2f}")
    
    # Count extreme RSI levels
    oversold_30 = (df['RSI'] <= 30).sum()
    oversold_25 = (df['RSI'] <= 25).sum()
    oversold_20 = (df['RSI'] <= 20).sum()
    overbought_70 = (df['RSI'] >= 70).sum()
    overbought_75 = (df['RSI'] >= 75).sum()
    overbought_80 = (df['RSI'] >= 80).sum()
    
    total_bars = len(df.dropna())
    
    print(f"  RSI <= 30: {oversold_30} bars ({oversold_30/total_bars*100:.1f}%)")
    print(f"  RSI <= 25: {oversold_25} bars ({oversold_25/total_bars*100:.1f}%)")
    print(f"  RSI <= 20: {oversold_20} bars ({oversold_20/total_bars*100:.1f}%)")
    print(f"  RSI >= 70: {overbought_70} bars ({overbought_70/total_bars*100:.1f}%)")
    print(f"  RSI >= 75: {overbought_75} bars ({overbought_75/total_bars*100:.1f}%)")
    print(f"  RSI >= 80: {overbought_80} bars ({overbought_80/total_bars*100:.1f}%)")
    
    # Create plots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Price plot
    ax1.plot(df.index, df['Close'], label=f'{ticker} Close Price', color='blue', linewidth=1)
    ax1.set_title(f'{ticker} Stock Price')
    ax1.set_ylabel('Price ($)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # RSI plot
    ax2.plot(df.index, df['RSI'], label=f'RSI ({rsi_period})', color='purple', linewidth=1)
    ax2.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Overbought (70)')
    ax2.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Oversold (30)')
    ax2.axhline(y=75, color='red', linestyle=':', alpha=0.5, label='Extreme OB (75)')
    ax2.axhline(y=25, color='green', linestyle=':', alpha=0.5, label='Extreme OS (25)')
    ax2.axhline(y=80, color='darkred', linestyle=':', alpha=0.5, label='Max OB (80)')
    ax2.axhline(y=20, color='darkgreen', linestyle=':', alpha=0.5, label='Max OS (20)')
    
    ax2.set_title(f'{ticker} RSI Indicator')
    ax2.set_ylabel('RSI')
    ax2.set_xlabel('Date')
    ax2.set_ylim(0, 100)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'rsi_analysis_{ticker.lower()}.png', dpi=300, bbox_inches='tight')
    # plt.show()  # Skip interactive display to avoid timeout
    
    return df

def main():
    """Main analysis function"""
    print("Sprint 7.1 Task 1: RSI Visual Analysis")
    print("=" * 50)
    
    # Check if pandas_ta is available
    try:
        import pandas_ta as ta
    except ImportError:
        print("Error: pandas_ta not installed. Install with: pip install pandas_ta")
        return
    
    # Analyze the three target stocks
    tickers = ['CRWD', 'SNOW', 'PLTR']
    
    for ticker in tickers:
        df = calculate_and_plot_rsi(ticker)
        if df is not None:
            print(f"[OK] {ticker} analysis complete")
        else:
            print(f"[FAIL] {ticker} analysis failed")
        print("-" * 30)
    
    print("\nSUMMARY:")
    print("Check the generated PNG files for visual RSI analysis")
    print("This will show us if RSI ever reaches the trigger levels needed for trades")

if __name__ == "__main__":
    main()