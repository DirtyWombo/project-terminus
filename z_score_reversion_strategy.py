"""
Strategy S10: Z-Score Mean Reversion
From The Compendium - Chapter 6: Mean Reversion Strategies

Signal Logic:
- Calculate Z-score of price relative to rolling mean/std
- Buy when Z-score < -2 (price significantly below mean)
- Sell when Z-score > 0 (price returns to mean)
- Lookback period: 50 days for mean/std calculation
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class ZScoreReversionStrategy:
    """
    Z-Score Mean Reversion Strategy
    
    Statistical approach to mean reversion
    More precise than Bollinger Bands, uses standard deviations
    """
    
    def __init__(self, lookback_period=50, entry_threshold=-2.0, exit_threshold=0.0, volume_filter=True):
        self.lookback_period = lookback_period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.volume_filter = volume_filter
        self.name = f"Z-Score Reversion ({lookback_period}p, {entry_threshold}σ)"
        
    def calculate_signals(self, price_data):
        """Calculate Z-score reversion signals for given price data"""
        signals = []
        
        for symbol, df in price_data.items():
            if len(df) < self.lookback_period + 10:
                continue
                
            # Calculate rolling statistics
            df['Price_Mean'] = df['Close'].rolling(window=self.lookback_period).mean()
            df['Price_Std'] = df['Close'].rolling(window=self.lookback_period).std()
            
            # Calculate Z-score
            df['Z_Score'] = (df['Close'] - df['Price_Mean']) / df['Price_Std']
            df['Z_Score_prev'] = df['Z_Score'].shift(1)
            
            # Entry signal: Z-score crosses below threshold
            entry_signal = (df['Z_Score'] <= self.entry_threshold) & (df['Z_Score_prev'] > self.entry_threshold)
            
            # Alternative: Z-score simply below threshold
            # entry_signal = df['Z_Score'] <= self.entry_threshold
            
            buy_signal = entry_signal
            
            # Volume filter
            if self.volume_filter:
                avg_volume = df['Volume'].rolling(window=20).mean()
                volume_adequate = df['Volume'] > (0.8 * avg_volume)
                buy_signal = buy_signal & volume_adequate
            
            # Calculate forward returns
            df['forward_1d'] = df['Close'].shift(-1) / df['Close'] - 1
            df['forward_3d'] = df['Close'].shift(-3) / df['Close'] - 1
            df['forward_5d'] = df['Close'].shift(-5) / df['Close'] - 1
            df['forward_10d'] = df['Close'].shift(-10) / df['Close'] - 1
            
            # Calculate expected return to mean
            df['return_to_mean'] = (df['Price_Mean'] - df['Close']) / df['Close']
            
            # Extract buy signals
            buy_signals = df[buy_signal].copy()
            
            for _, row in buy_signals.iterrows():
                if not pd.isna(row['forward_1d']):
                    signal_data = {
                        'symbol': symbol,
                        'date': row.name,
                        'signal_type': 'z_score_reversion',
                        'price': row['Close'],
                        'z_score': row['Z_Score'],
                        'price_mean': row['Price_Mean'],
                        'price_std': row['Price_Std'],
                        'return_to_mean': row['return_to_mean'],
                        'volume': row['Volume'],
                        'forward_1d': row['forward_1d'],
                        'forward_3d': row['forward_3d'],
                        'forward_5d': row['forward_5d'],
                        'forward_10d': row['forward_10d']
                    }
                    signals.append(signal_data)
        
        return pd.DataFrame(signals)