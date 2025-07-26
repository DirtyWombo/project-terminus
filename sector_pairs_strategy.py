"""
Strategy S17: Sector Pairs Trading
From The Compendium - Chapter 8: Pairs Trading Strategies

Signal Logic:
- Trade pairs within same sector (e.g., AAPL vs MSFT in tech)
- Calculate relative strength between sector leaders
- Buy underperformer, sell outperformer when spread widens
- Market neutral within sector exposure
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

class SectorPairsStrategy:
    """
    Sector-Neutral Pairs Trading Strategy
    
    Market neutral pairs within same sector
    Exploits relative mispricing between similar companies
    """
    
    def __init__(self, lookback_period=60, entry_threshold=2.0):
        self.lookback_period = lookback_period
        self.entry_threshold = entry_threshold
        self.name = f"Sector Pairs (±{entry_threshold}σ)"
        
        # Define sector groupings
        self.sector_groups = {
            'technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'PLTR', 'NET', 'DDOG'],
            'healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRNA', 'VEEV', 'DXCM', 'ILMN'],
            'finance': ['JPM', 'BAC', 'WFC', 'GS', 'PYPL', 'SOFI', 'AFRM', 'COIN'],
            'consumer': ['AMZN', 'TSLA', 'HD', 'MCD', 'SHOP', 'ETSY', 'CHWY', 'PINS'],
            'energy': ['XOM', 'CVX', 'COP', 'ENPH', 'SEDG', 'RUN', 'FSLR', 'BE']
        }
    
    def find_sector_pairs(self, price_data, min_correlation=0.6):
        """Find pairs within each sector"""
        sector_pairs = []
        
        for sector, symbols in self.sector_groups.items():
            # Filter symbols that exist in price_data
            available_symbols = [s for s in symbols if s in price_data]
            
            if len(available_symbols) < 2:
                continue
            
            # Calculate returns for correlation analysis
            returns_data = {}
            for symbol in available_symbols:
                df = price_data[symbol]
                if len(df) > 252:  # Need at least 1 year
                    returns = df['Close'].pct_change().dropna()
                    returns_data[symbol] = returns
            
            # Find correlated pairs within sector
            for sym1, sym2 in combinations(returns_data.keys(), 2):
                ret1 = returns_data[sym1]
                ret2 = returns_data[sym2]
                
                # Align returns
                common_dates = ret1.index.intersection(ret2.index)
                if len(common_dates) > 252:
                    aligned_ret1 = ret1.reindex(common_dates)
                    aligned_ret2 = ret2.reindex(common_dates)
                    
                    correlation = aligned_ret1.corr(aligned_ret2)
                    
                    if correlation >= min_correlation:
                        sector_pairs.append({
                            'sector': sector,
                            'symbol1': sym1,
                            'symbol2': sym2,
                            'correlation': correlation
                        })
        
        return sector_pairs
    
    def calculate_pair_signals(self, symbol1, symbol2, price_data, sector):
        """Calculate signals for a sector pair"""
        df1 = price_data[symbol1].copy()
        df2 = price_data[symbol2].copy()
        
        # Align data
        common_dates = df1.index.intersection(df2.index)
        df1 = df1.reindex(common_dates)
        df2 = df2.reindex(common_dates)
        
        if len(common_dates) < self.lookback_period + 10:
            return pd.DataFrame()
        
        # Calculate relative performance ratio
        df1['Price1'] = df1['Close']
        df2['Price2'] = df2['Close']
        
        # Ratio of normalized prices
        price_ratio = df1['Price1'] / df2['Price2']
        
        # Rolling statistics
        ratio_mean = price_ratio.rolling(window=self.lookback_period).mean()
        ratio_std = price_ratio.rolling(window=self.lookback_period).std()
        
        # Z-score of ratio
        ratio_zscore = (price_ratio - ratio_mean) / ratio_std
        
        # Generate signals
        # Buy symbol1, sell symbol2 when ratio is oversold (symbol1 underperforming)
        long_sym1_signal = ratio_zscore <= -self.entry_threshold
        
        # Buy symbol2, sell symbol1 when ratio is overbought (symbol1 outperforming)  
        long_sym2_signal = ratio_zscore >= self.entry_threshold
        
        signals = []
        
        # Process long symbol1 signals
        for date in common_dates[long_sym1_signal.reindex(common_dates)]:
            try:
                price1 = df1.loc[date, 'Price1']
                price2 = df2.loc[date, 'Price2']
                zscore = ratio_zscore.loc[date]
                
                # 5-day forward return for the pair
                future_dates = [d for d in common_dates if d > date]
                
                if len(future_dates) >= 5:
                    future_date = future_dates[4]
                    future_price1 = df1.loc[future_date, 'Price1']
                    future_price2 = df2.loc[future_date, 'Price2']
                    
                    # Pair return (long sym1, short sym2)
                    pair_return = (future_price1/price1 - 1) - (future_price2/price2 - 1)
                    
                    signals.append({
                        'date': date,
                        'sector': sector,
                        'symbol1': symbol1,
                        'symbol2': symbol2,
                        'signal_type': f'sector_pairs_long_{symbol1}',
                        'price1': price1,
                        'price2': price2,
                        'ratio_zscore': zscore,
                        'forward_5d_pair': pair_return
                    })
                    
            except (KeyError, IndexError):
                continue
        
        # Process long symbol2 signals
        for date in common_dates[long_sym2_signal.reindex(common_dates)]:
            try:
                price1 = df1.loc[date, 'Price1']
                price2 = df2.loc[date, 'Price2']
                zscore = ratio_zscore.loc[date]
                
                future_dates = [d for d in common_dates if d > date]
                
                if len(future_dates) >= 5:
                    future_date = future_dates[4]
                    future_price1 = df1.loc[future_date, 'Price1']
                    future_price2 = df2.loc[future_date, 'Price2']
                    
                    # Pair return (long sym2, short sym1)
                    pair_return = (future_price2/price2 - 1) - (future_price1/price1 - 1)
                    
                    signals.append({
                        'date': date,
                        'sector': sector,
                        'symbol1': symbol1,
                        'symbol2': symbol2,
                        'signal_type': f'sector_pairs_long_{symbol2}',
                        'price1': price1,
                        'price2': price2,
                        'ratio_zscore': zscore,
                        'forward_5d_pair': pair_return
                    })
                    
            except (KeyError, IndexError):
                continue
        
        return pd.DataFrame(signals)
    
    def calculate_signals(self, price_data):
        """Calculate sector pairs signals for entire universe"""
        print("Finding sector pairs...")
        pairs = self.find_sector_pairs(price_data)
        
        if len(pairs) == 0:
            return pd.DataFrame()
        
        print(f"Found {len(pairs)} sector pairs")
        
        all_signals = []
        
        # Process top pairs from each sector
        sectors_processed = set()
        for pair in pairs[:8]:  # Limit computation
            if pair['sector'] not in sectors_processed:
                print(f"Processing {pair['sector']} pair: {pair['symbol1']}-{pair['symbol2']}")
                
                pair_signals = self.calculate_pair_signals(
                    pair['symbol1'],
                    pair['symbol2'], 
                    price_data,
                    pair['sector']
                )
                
                if not pair_signals.empty:
                    all_signals.append(pair_signals)
                
                sectors_processed.add(pair['sector'])
        
        if all_signals:
            return pd.concat(all_signals, ignore_index=True)
        else:
            return pd.DataFrame()