"""
Strategy S05: Momentum Breakout
From The Compendium - Chapter 5: Trend Following Strategies

Signal Logic:
- Buy when price breaks above 20-day high with volume confirmation
- Additional filter: Price must be above 50-day MA (trend confirmation)
- Sell on 10-day low break or stop loss
- Momentum measured by rate of change over 10 days
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class MomentumBreakoutStrategy:
    """
    Momentum Breakout Strategy
    
    Trend following approach that buys strength
    Works best in trending markets with clear direction
    """
    
    def __init__(self, breakout_period=20, trend_period=50, momentum_period=10, volume_multiplier=1.5):
        self.breakout_period = breakout_period
        self.trend_period = trend_period
        self.momentum_period = momentum_period
        self.volume_multiplier = volume_multiplier
        self.name = f"Momentum Breakout ({breakout_period}p)"
        
    def calculate_signals(self, price_data):
        """Calculate momentum breakout signals for given price data"""
        signals = []
        
        for symbol, df in price_data.items():
            if len(df) < max(self.breakout_period, self.trend_period) + 10:
                continue
                
            # Calculate indicators
            df['High_Max'] = df['High'].rolling(window=self.breakout_period).max()
            df['Low_Min'] = df['Low'].rolling(window=self.breakout_period).min()
            df['MA_Trend'] = df['Close'].rolling(window=self.trend_period).mean()
            
            # Momentum calculation (rate of change)
            df['Momentum'] = df['Close'].pct_change(periods=self.momentum_period)
            
            # Volume analysis
            df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
            
            # Previous day values
            df['High_Max_prev'] = df['High_Max'].shift(1)
            
            # Breakout conditions
            price_breakout = df['Close'] > df['High_Max_prev']  # New high
            trend_confirmation = df['Close'] > df['MA_Trend']   # Above trend MA
            volume_confirmation = df['Volume'] > (self.volume_multiplier * df['Volume_MA'])
            momentum_positive = df['Momentum'] > 0.02  # At least 2% momentum
            
            buy_signal = price_breakout & trend_confirmation & volume_confirmation & momentum_positive
            
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
                        'signal_type': 'momentum_breakout',
                        'price': row['Close'],
                        'breakout_level': row['High_Max_prev'],
                        'trend_ma': row['MA_Trend'],
                        'momentum': row['Momentum'],
                        'volume': row['Volume'],
                        'volume_ma': row['Volume_MA'],
                        'forward_1d': row['forward_1d'],
                        'forward_3d': row['forward_3d'],
                        'forward_5d': row['forward_5d'],
                        'forward_10d': row['forward_10d']
                    }
                    signals.append(signal_data)
        
        return pd.DataFrame(signals)