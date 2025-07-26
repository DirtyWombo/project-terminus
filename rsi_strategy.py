"""
Strategy S08: RSI Oversold/Overbought
From The Compendium - Chapter 6: Mean Reversion Strategies

Signal Logic:
- Buy when RSI < 30 (oversold condition)
- Sell when RSI > 70 (overbought condition) 
- Hold while RSI between 30-70
- Standard parameters: 14-period RSI
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class RSIStrategy:
    """
    RSI (Relative Strength Index) Mean Reversion Strategy
    
    Contrarian approach - buy oversold, sell overbought
    Works best in ranging/sideways markets
    """
    
    def __init__(self, rsi_period=14, oversold_threshold=30, overbought_threshold=70, volume_filter=True):
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.volume_filter = volume_filter
        self.name = f"RSI ({rsi_period}p, {oversold_threshold}/{overbought_threshold})"
        
    def calculate_rsi(self, price_series, period):
        """Calculate RSI indicator"""
        delta = price_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def calculate_signals(self, price_data):
        """Calculate RSI signals for given price data"""
        signals = []
        
        for symbol, df in price_data.items():
            if len(df) < self.rsi_period + 10:
                continue
                
            # Calculate RSI
            df['RSI'] = self.calculate_rsi(df['Close'], self.rsi_period)
            df['RSI_prev'] = df['RSI'].shift(1)
            
            # Oversold condition (buy signal)
            oversold_entry = (df['RSI'] < self.oversold_threshold) & (df['RSI_prev'] >= self.oversold_threshold)
            
            # Alternative: RSI rising from oversold
            # oversold_entry = (df['RSI'] < self.oversold_threshold) & (df['RSI'] > df['RSI_prev'])
            
            buy_signal = oversold_entry
            
            # Volume filter
            if self.volume_filter:
                avg_volume = df['Volume'].rolling(window=20).mean()
                volume_adequate = df['Volume'] > (0.5 * avg_volume)  # At least 50% average volume
                buy_signal = buy_signal & volume_adequate
            
            # Calculate forward returns
            df['forward_1d'] = df['Close'].shift(-1) / df['Close'] - 1
            df['forward_3d'] = df['Close'].shift(-3) / df['Close'] - 1
            df['forward_5d'] = df['Close'].shift(-5) / df['Close'] - 1
            df['forward_10d'] = df['Close'].shift(-10) / df['Close'] - 1
            
            # Calculate return to RSI neutral (50)
            # Approximate target price when RSI would be ~50
            recent_volatility = df['Close'].pct_change().rolling(window=20).std()
            df['target_return'] = recent_volatility * 2  # Rough estimate
            
            # Extract buy signals
            buy_signals = df[buy_signal].copy()
            
            for _, row in buy_signals.iterrows():
                if not pd.isna(row['forward_1d']):
                    signal_data = {
                        'symbol': symbol,
                        'date': row.name,
                        'signal_type': 'rsi_oversold',
                        'price': row['Close'],
                        'rsi': row['RSI'],
                        'volume': row['Volume'],
                        'target_return': row.get('target_return', np.nan),
                        'forward_1d': row['forward_1d'],
                        'forward_3d': row['forward_3d'],
                        'forward_5d': row['forward_5d'],
                        'forward_10d': row['forward_10d']
                    }
                    signals.append(signal_data)
        
        return pd.DataFrame(signals)