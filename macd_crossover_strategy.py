"""
Strategy S04: MACD Crossover  
From The Compendium - Chapter 5: Moving Average Strategies

Signal Logic:
- Buy when MACD line crosses above signal line (bullish crossover)
- Additional filter: MACD histogram must be increasing
- Sell when MACD crosses below signal line
- Standard parameters: 12/26/9 EMA periods
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class MACDCrossoverStrategy:
    """
    MACD (Moving Average Convergence Divergence) Strategy
    
    Uses momentum oscillator to identify trend changes
    More responsive than simple MA crossovers
    """
    
    def __init__(self, fast_period=12, slow_period=26, signal_period=9, histogram_filter=True):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.histogram_filter = histogram_filter
        self.name = f"MACD ({fast_period}/{slow_period}/{signal_period})"
        
    def calculate_macd(self, price_series):
        """Calculate MACD indicator components"""
        # Calculate EMAs
        ema_fast = price_series.ewm(span=self.fast_period).mean()
        ema_slow = price_series.ewm(span=self.slow_period).mean()
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD)
        signal_line = macd_line.ewm(span=self.signal_period).mean()
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
        
    def calculate_signals(self, price_data):
        """Calculate MACD crossover signals for given price data"""
        signals = []
        
        for symbol, df in price_data.items():
            if len(df) < self.slow_period + self.signal_period + 10:
                continue
                
            # Calculate MACD components
            macd_line, signal_line, histogram = self.calculate_macd(df['Close'])
            
            df['MACD'] = macd_line
            df['MACD_Signal'] = signal_line
            df['MACD_Histogram'] = histogram
            
            # Previous values for crossover detection
            df['MACD_prev'] = df['MACD'].shift(1)
            df['MACD_Signal_prev'] = df['MACD_Signal'].shift(1)
            df['MACD_Histogram_prev'] = df['MACD_Histogram'].shift(1)
            
            # Bullish crossover: MACD crosses above signal
            bullish_cross = (df['MACD'] > df['MACD_Signal']) & (df['MACD_prev'] <= df['MACD_Signal_prev'])
            
            # Histogram filter: histogram should be increasing
            if self.histogram_filter:
                histogram_increasing = df['MACD_Histogram'] > df['MACD_Histogram_prev']
                buy_signal = bullish_cross & histogram_increasing
            else:
                buy_signal = bullish_cross
            
            # Additional filter: MACD should be above zero line (optional)
            # macd_positive = df['MACD'] > 0
            # buy_signal = buy_signal & macd_positive
            
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
                        'signal_type': 'macd_bullish_crossover',
                        'price': row['Close'],
                        'macd': row['MACD'],
                        'macd_signal': row['MACD_Signal'],
                        'macd_histogram': row['MACD_Histogram'],
                        'volume': row['Volume'],
                        'forward_1d': row['forward_1d'],
                        'forward_3d': row['forward_3d'],
                        'forward_5d': row['forward_5d'],
                        'forward_10d': row['forward_10d']
                    }
                    signals.append(signal_data)
        
        return pd.DataFrame(signals)