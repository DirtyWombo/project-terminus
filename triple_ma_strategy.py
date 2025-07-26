"""
Strategy S03: Triple MA System
From The Compendium - Chapter 5: Moving Average Strategies

Signal Logic:
- Buy when short MA > medium MA > long MA (aligned trend)
- Sell when alignment breaks (any MA crosses below another)
- Default periods: 10/20/50 day moving averages
- Volume confirmation for signal strength
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class TripleMAStrategy:
    """
    Triple Moving Average Crossover Strategy
    
    More sophisticated than double MA - requires alignment of three MAs
    Reduces false signals but may lag trend changes
    """
    
    def __init__(self, short_window=10, medium_window=20, long_window=50, volume_filter=True):
        self.short_window = short_window
        self.medium_window = medium_window
        self.long_window = long_window
        self.volume_filter = volume_filter
        self.name = f"Triple MA ({short_window}/{medium_window}/{long_window})"
        
    def calculate_signals(self, price_data):
        """Calculate Triple MA signals for given price data"""
        signals = []
        
        for symbol, df in price_data.items():
            if len(df) < self.long_window + 10:
                continue
                
            # Calculate moving averages
            df['MA_Short'] = df['Close'].rolling(window=self.short_window).mean()
            df['MA_Medium'] = df['Close'].rolling(window=self.medium_window).mean()
            df['MA_Long'] = df['Close'].rolling(window=self.long_window).mean()
            
            # Previous day values for crossover detection
            df['MA_Short_prev'] = df['MA_Short'].shift(1)
            df['MA_Medium_prev'] = df['MA_Medium'].shift(1)
            df['MA_Long_prev'] = df['MA_Long'].shift(1)
            
            # Triple alignment conditions
            current_aligned = (df['MA_Short'] > df['MA_Medium']) & (df['MA_Medium'] > df['MA_Long'])
            prev_aligned = (df['MA_Short_prev'] > df['MA_Medium_prev']) & (df['MA_Medium_prev'] > df['MA_Long_prev'])
            
            # Buy signal: Transition to full alignment
            buy_signal = current_aligned & ~prev_aligned
            
            # Sell signal: Alignment breaks
            sell_signal = ~current_aligned & prev_aligned
            
            # Volume filter
            if self.volume_filter:
                avg_volume = df['Volume'].rolling(window=20).mean()
                volume_surge = df['Volume'] > (1.2 * avg_volume)
                buy_signal = buy_signal & volume_surge
            
            # Calculate forward returns
            df['forward_1d'] = df['Close'].shift(-1) / df['Close'] - 1
            df['forward_3d'] = df['Close'].shift(-3) / df['Close'] - 1
            df['forward_5d'] = df['Close'].shift(-5) / df['Close'] - 1
            df['forward_10d'] = df['Close'].shift(-10) / df['Close'] - 1
            
            # Extract buy signals
            buy_signals = df[buy_signal].copy()
            
            for _, row in buy_signals.iterrows():
                if not pd.isna(row['forward_1d']):
                    signal_data = {
                        'symbol': symbol,
                        'date': row.name,
                        'signal_type': 'triple_ma_alignment',
                        'price': row['Close'],
                        'ma_short': row['MA_Short'],
                        'ma_medium': row['MA_Medium'],
                        'ma_long': row['MA_Long'],
                        'volume': row['Volume'],
                        'forward_1d': row['forward_1d'],
                        'forward_3d': row['forward_3d'],
                        'forward_5d': row['forward_5d'],
                        'forward_10d': row['forward_10d']
                    }
                    signals.append(signal_data)
        
        return pd.DataFrame(signals)