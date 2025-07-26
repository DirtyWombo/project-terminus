"""
Strategy S16: Correlation Pairs Trading
From The Compendium - Chapter 8: Pairs Trading Strategies

Signal Logic:
- Find highly correlated stock pairs (correlation > 0.8)
- Calculate rolling spread between normalized prices
- Buy spread when below -2 std dev, sell when above +2 std dev
- Market neutral strategy (long/short pair)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

class PairsTradingStrategy:
    """
    Correlation-Based Pairs Trading Strategy
    
    Market neutral approach using statistical arbitrage
    Exploits temporary divergences in correlated assets
    """
    
    def __init__(self, correlation_threshold=0.8, lookback_period=60, entry_threshold=2.0):
        self.correlation_threshold = correlation_threshold
        self.lookback_period = lookback_period
        self.entry_threshold = entry_threshold
        self.name = f"Pairs Trading (corr>{correlation_threshold})"
        
    def find_pairs(self, price_data, min_period=252):
        """Find highly correlated pairs from universe"""
        valid_symbols = []
        returns_data = {}
        
        # Calculate returns for each symbol
        for symbol, df in price_data.items():
            if len(df) >= min_period:
                returns = df['Close'].pct_change().dropna()
                if len(returns) >= min_period - 1:
                    valid_symbols.append(symbol)
                    returns_data[symbol] = returns
        
        # Find all possible pairs
        pairs = []
        for sym1, sym2 in combinations(valid_symbols, 2):
            # Align the return series
            ret1 = returns_data[sym1]
            ret2 = returns_data[sym2]
            
            # Get overlapping dates
            common_dates = ret1.index.intersection(ret2.index)
            if len(common_dates) >= min_period - 1:
                aligned_ret1 = ret1.reindex(common_dates)
                aligned_ret2 = ret2.reindex(common_dates)
                
                # Calculate correlation
                correlation = aligned_ret1.corr(aligned_ret2)
                
                if correlation >= self.correlation_threshold:
                    pairs.append({
                        'symbol1': sym1,
                        'symbol2': sym2,
                        'correlation': correlation,
                        'common_periods': len(common_dates)
                    })
        
        # Sort by correlation strength
        pairs = sorted(pairs, key=lambda x: x['correlation'], reverse=True)
        
        return pairs
    
    def calculate_pair_signals(self, symbol1, symbol2, price_data):
        """Calculate signals for a specific pair"""
        df1 = price_data[symbol1].copy()
        df2 = price_data[symbol2].copy()
        
        # Align data
        common_dates = df1.index.intersection(df2.index)
        df1 = df1.reindex(common_dates)
        df2 = df2.reindex(common_dates)
        
        if len(common_dates) < self.lookback_period + 10:
            return pd.DataFrame()
        
        # Normalize prices (use log prices for better statistical properties)
        df1['LogPrice'] = np.log(df1['Close'])
        df2['LogPrice'] = np.log(df2['Close'])
        
        # Calculate spread
        spread = df1['LogPrice'] - df2['LogPrice']
        
        # Calculate rolling statistics
        spread_mean = spread.rolling(window=self.lookback_period).mean()
        spread_std = spread.rolling(window=self.lookback_period).std()
        
        # Z-score of spread
        spread_zscore = (spread - spread_mean) / spread_std
        
        # Generate signals
        entry_long = spread_zscore <= -self.entry_threshold  # Buy spread (long sym1, short sym2)
        entry_short = spread_zscore >= self.entry_threshold   # Sell spread (short sym1, long sym2)
        
        # Exit signals (when spread returns to mean)
        exit_signal = abs(spread_zscore) <= 0.5
        
        signals = []
        
        # Process long spread signals
        for date in common_dates[entry_long.reindex(common_dates)]:
            try:
                price1 = df1.loc[date, 'Close']
                price2 = df2.loc[date, 'Close']
                zscore = spread_zscore.loc[date]
                
                # Calculate forward returns (for the spread)
                future_dates = [d for d in common_dates if d > date]
                
                if len(future_dates) >= 5:  # Need at least 5 days forward
                    # 5-day forward return
                    future_date_5d = future_dates[min(4, len(future_dates)-1)]
                    future_price1 = df1.loc[future_date_5d, 'Close']
                    future_price2 = df2.loc[future_date_5d, 'Close']
                    
                    # Spread return (long sym1, short sym2)
                    spread_return = (future_price1/price1 - 1) - (future_price2/price2 - 1)
                    
                    signal_data = {
                        'date': date,
                        'symbol1': symbol1,
                        'symbol2': symbol2,
                        'signal_type': 'pairs_long_spread',
                        'price1': price1,
                        'price2': price2,
                        'spread_zscore': zscore,
                        'correlation': None,  # Will be filled later
                        'forward_5d_spread': spread_return
                    }
                    signals.append(signal_data)
                    
            except (KeyError, IndexError):
                continue
        
        # Process short spread signals
        for date in common_dates[entry_short.reindex(common_dates)]:
            try:
                price1 = df1.loc[date, 'Close']
                price2 = df2.loc[date, 'Close']
                zscore = spread_zscore.loc[date]
                
                future_dates = [d for d in common_dates if d > date]
                
                if len(future_dates) >= 5:
                    future_date_5d = future_dates[min(4, len(future_dates)-1)]
                    future_price1 = df1.loc[future_date_5d, 'Close']
                    future_price2 = df2.loc[future_date_5d, 'Close']
                    
                    # Spread return (short sym1, long sym2)
                    spread_return = -(future_price1/price1 - 1) + (future_price2/price2 - 1)
                    
                    signal_data = {
                        'date': date,
                        'symbol1': symbol1,
                        'symbol2': symbol2,
                        'signal_type': 'pairs_short_spread',
                        'price1': price1,
                        'price2': price2,
                        'spread_zscore': zscore,
                        'correlation': None,
                        'forward_5d_spread': spread_return
                    }
                    signals.append(signal_data)
                    
            except (KeyError, IndexError):
                continue
        
        return pd.DataFrame(signals)
    
    def calculate_signals(self, price_data):
        """Calculate pairs trading signals for entire universe"""
        print("Finding highly correlated pairs...")
        pairs = self.find_pairs(price_data)
        
        if len(pairs) == 0:
            print("No correlated pairs found.")
            return pd.DataFrame()
        
        print(f"Found {len(pairs)} correlated pairs")
        
        all_signals = []
        
        # Process top pairs (limit to avoid excessive computation)
        top_pairs = pairs[:10]  # Top 10 most correlated pairs
        
        for i, pair in enumerate(top_pairs):
            print(f"Processing pair {i+1}/10: {pair['symbol1']}-{pair['symbol2']} (corr={pair['correlation']:.3f})")
            
            pair_signals = self.calculate_pair_signals(
                pair['symbol1'], 
                pair['symbol2'], 
                price_data
            )
            
            if not pair_signals.empty:
                # Add correlation info
                pair_signals['correlation'] = pair['correlation']
                all_signals.append(pair_signals)
        
        if all_signals:
            return pd.concat(all_signals, ignore_index=True)
        else:
            return pd.DataFrame()