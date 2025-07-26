"""
Strategy S18: VIX Mean Reversion
From The Compendium - Chapter 7: Volatility Strategies

Signal Logic:
- Buy market when VIX > 30 (extreme fear, oversold market)
- Sell market when VIX < 15 (complacency, overbought market)
- Hold SPY/QQQ as market proxy
- VIX tends to mean revert to ~20 level
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class VIXMeanReversionStrategy:
    """
    VIX Mean Reversion Strategy
    
    Contrarian strategy based on volatility extremes
    Uses fear/greed cycles in market sentiment
    """
    
    def __init__(self, high_vix_threshold=30, low_vix_threshold=15, market_proxy='SPY'):
        self.high_vix_threshold = high_vix_threshold
        self.low_vix_threshold = low_vix_threshold
        self.market_proxy = market_proxy
        self.name = f"VIX Mean Reversion ({high_vix_threshold}/{low_vix_threshold})"
        
    def get_vix_data(self, period="2y"):
        """Get VIX data from Yahoo Finance"""
        try:
            vix_ticker = yf.Ticker("^VIX")
            vix_data = vix_ticker.history(period=period)
            return vix_data
        except Exception as e:
            print(f"Error fetching VIX data: {e}")
            return pd.DataFrame()
    
    def calculate_signals(self, price_data):
        """Calculate VIX mean reversion signals"""
        # Get VIX data
        vix_data = self.get_vix_data()
        
        if vix_data.empty:
            print("No VIX data available")
            return pd.DataFrame()
        
        # Get market proxy data
        if self.market_proxy not in price_data:
            print(f"Market proxy {self.market_proxy} not in price data")
            return pd.DataFrame()
        
        market_data = price_data[self.market_proxy].copy()
        
        # Align VIX and market data
        common_dates = vix_data.index.intersection(market_data.index)
        
        if len(common_dates) < 50:
            print("Insufficient overlapping data between VIX and market")
            return pd.DataFrame()
        
        vix_aligned = vix_data.reindex(common_dates)
        market_aligned = market_data.reindex(common_dates)
        
        # Create combined dataframe
        df = pd.DataFrame({
            'VIX': vix_aligned['Close'],
            'Market_Price': market_aligned['Close'],
            'Market_Volume': market_aligned['Volume']
        })
        
        # Calculate additional VIX metrics
        df['VIX_MA'] = df['VIX'].rolling(window=20).mean()
        df['VIX_Std'] = df['VIX'].rolling(window=20).std()
        df['VIX_ZScore'] = (df['VIX'] - df['VIX_MA']) / df['VIX_Std']
        
        # Previous day values
        df['VIX_prev'] = df['VIX'].shift(1)
        
        # Signal conditions
        # Buy market when VIX spikes (extreme fear)
        vix_spike = (df['VIX'] >= self.high_vix_threshold) & (df['VIX_prev'] < self.high_vix_threshold)
        
        # Alternative: VIX simply above threshold
        # vix_high = df['VIX'] >= self.high_vix_threshold
        
        buy_signal = vix_spike
        
        # Calculate forward returns for market proxy
        df['forward_1d'] = df['Market_Price'].shift(-1) / df['Market_Price'] - 1
        df['forward_3d'] = df['Market_Price'].shift(-3) / df['Market_Price'] - 1
        df['forward_5d'] = df['Market_Price'].shift(-5) / df['Market_Price'] - 1
        df['forward_10d'] = df['Market_Price'].shift(-10) / df['Market_Price'] - 1
        
        signals = []
        
        # Extract buy signals
        buy_dates = df[buy_signal].index
        
        for date in buy_dates:
            if not pd.isna(df.loc[date, 'forward_1d']):
                signal_data = {
                    'symbol': self.market_proxy,
                    'date': date,
                    'signal_type': 'vix_mean_reversion',
                    'market_price': df.loc[date, 'Market_Price'],
                    'vix_level': df.loc[date, 'VIX'],
                    'vix_zscore': df.loc[date, 'VIX_ZScore'],
                    'vix_ma': df.loc[date, 'VIX_MA'],
                    'volume': df.loc[date, 'Market_Volume'],
                    'forward_1d': df.loc[date, 'forward_1d'],
                    'forward_3d': df.loc[date, 'forward_3d'],
                    'forward_5d': df.loc[date, 'forward_5d'],
                    'forward_10d': df.loc[date, 'forward_10d']
                }
                signals.append(signal_data)
        
        return pd.DataFrame(signals)