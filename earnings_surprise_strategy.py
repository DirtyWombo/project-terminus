"""
Strategy S21: Earnings Surprise
From The Compendium - Chapter 10: Event-Driven Strategies

Signal Logic:
- Buy after positive earnings surprise (actual > estimate)
- Additional filter: Revenue beat and guidance raise
- Hold for 5-10 days post-earnings (momentum continuation)
- Focus on small/mid-caps for less efficient reactions
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class EarningsSurpriseStrategy:
    """
    Earnings Surprise Strategy
    
    Event-driven approach exploiting post-earnings momentum
    Works best in small/mid-caps with less analyst coverage
    """
    
    def __init__(self, surprise_threshold=0.05, volume_multiplier=2.0):
        self.surprise_threshold = surprise_threshold  # 5% earnings beat
        self.volume_multiplier = volume_multiplier
        self.name = f"Earnings Surprise ({surprise_threshold:.1%} beat)"
        
    def simulate_earnings_events(self, price_data):
        """
        Simulate earnings events based on volume spikes and price gaps
        In production: integrate with actual earnings calendar API
        """
        earnings_events = []
        
        for symbol, df in price_data.items():
            if len(df) < 60:  # Need sufficient history
                continue
            
            # Calculate volume and price metrics
            df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
            df['Price_Gap'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)
            df['Price_Change'] = df['Close'].pct_change()
            
            # Identify potential earnings days (high volume + significant price movement)
            earnings_candidates = df[
                (df['Volume_Ratio'] > 3.0) &  # 3x volume spike
                (abs(df['Price_Gap']) > 0.05) &  # 5%+ gap
                (abs(df['Price_Change']) > 0.08)  # 8%+ daily move
            ]
            
            # Simulate earnings surprise based on positive price reaction
            for date, row in earnings_candidates.iterrows():
                # Positive surprise = positive gap + positive daily return
                if row['Price_Gap'] > 0.03 and row['Price_Change'] > 0.05:
                    
                    # Calculate forward returns
                    try:
                        # Get future prices for forward returns
                        future_dates = df.index[df.index > date]
                        
                        if len(future_dates) >= 10:
                            # 5-day and 10-day forward returns
                            future_5d = df.loc[future_dates[4], 'Close']
                            future_10d = df.loc[future_dates[9], 'Close']
                            current_close = row['Close']
                            
                            forward_5d = (future_5d / current_close) - 1
                            forward_10d = (future_10d / current_close) - 1
                            
                            earnings_events.append({
                                'symbol': symbol,
                                'date': date,
                                'signal_type': 'earnings_surprise',
                                'price': current_close,
                                'price_gap': row['Price_Gap'],
                                'price_change': row['Price_Change'],
                                'volume_ratio': row['Volume_Ratio'],
                                'volume': row['Volume'],
                                'surprise_estimate': row['Price_Gap'],  # Using gap as proxy
                                'forward_5d': forward_5d,
                                'forward_10d': forward_10d
                            })
                            
                    except (KeyError, IndexError):
                        continue
        
        return pd.DataFrame(earnings_events)
    
    def calculate_signals(self, price_data):
        """Calculate earnings surprise signals for given price data"""
        print("Simulating earnings events based on volume/price patterns...")
        
        signals_df = self.simulate_earnings_events(price_data)
        
        if signals_df.empty:
            return pd.DataFrame()
        
        # Filter for significant positive surprises
        significant_surprises = signals_df[
            (signals_df['surprise_estimate'] >= self.surprise_threshold) &
            (signals_df['volume_ratio'] >= self.volume_multiplier)
        ]
        
        print(f"Found {len(significant_surprises)} earnings surprise signals")
        
        return significant_surprises
    
    def get_earnings_calendar(self, symbols, start_date, end_date):
        """
        Placeholder for real earnings calendar integration
        In production: use Alpha Vantage, Quandl, or similar API
        """
        # This would integrate with real earnings data
        # Example structure:
        earnings_calendar = [
            # {
            #     'symbol': 'AAPL',
            #     'earnings_date': '2024-01-25',
            #     'estimate_eps': 2.11,
            #     'actual_eps': 2.18,
            #     'surprise_pct': 0.033,
            #     'revenue_estimate': 117.9e9,
            #     'revenue_actual': 119.6e9
            # }
        ]
        
        return earnings_calendar