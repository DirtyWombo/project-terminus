"""
Strategy S13: Quality Factor
From The Compendium - Chapter 9: Factor-Based Strategies

Signal Logic:
- Select stocks with high quality metrics: ROE, ROA, low debt/equity
- Monthly rebalancing to top quality quintile 
- Focus on consistent earnings growth and stable margins
- Avoid companies with declining fundamentals
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class QualityFactorStrategy:
    """
    Quality Factor Strategy
    
    Selects companies with superior fundamental quality metrics
    Long-term outperformance through quality premium
    """
    
    def __init__(self, rebalance_freq='M', top_percentile=0.2):
        self.rebalance_freq = rebalance_freq
        self.top_percentile = top_percentile  # Top 20%
        self.name = f"Quality Factor (Top {int(top_percentile*100)}%)"
        
    def calculate_quality_score(self, fundamental_data):
        """Calculate composite quality score"""
        scores = []
        
        for symbol, data in fundamental_data.items():
            try:
                # Quality metrics (using available data)
                roe = data.get('returnOnEquity', 0) / 100 if data.get('returnOnEquity') else 0
                roa = data.get('returnOnAssets', 0) / 100 if data.get('returnOnAssets') else 0 
                debt_ratio = data.get('debtToEquity', 100) / 100 if data.get('debtToEquity') else 1
                profit_margin = data.get('profitMargins', 0) if data.get('profitMargins') else 0
                
                # Quality score (higher is better)
                quality_score = (
                    roe * 0.3 +  # 30% weight on ROE
                    roa * 0.2 +  # 20% weight on ROA
                    profit_margin * 0.2 +  # 20% weight on margins
                    max(0, (1 - debt_ratio)) * 0.3  # 30% weight on low debt (inverted)
                )
                
                scores.append({
                    'symbol': symbol,
                    'quality_score': quality_score,
                    'roe': roe,
                    'roa': roa,
                    'debt_ratio': debt_ratio,
                    'profit_margin': profit_margin
                })
                
            except Exception:
                continue
        
        return pd.DataFrame(scores)
    
    def calculate_signals(self, price_data):
        """Calculate quality factor signals"""
        # Simulate fundamental data collection
        fundamental_data = self.get_fundamental_data(list(price_data.keys()))
        
        if len(fundamental_data) < 10:
            return pd.DataFrame()
        
        # Calculate quality scores
        quality_scores = self.calculate_quality_score(fundamental_data)
        
        if len(quality_scores) == 0:
            return pd.DataFrame()
        
        # Select top quality stocks
        quality_scores = quality_scores.sort_values('quality_score', ascending=False)
        top_count = max(1, int(len(quality_scores) * self.top_percentile))
        top_quality = quality_scores.head(top_count)
        
        signals = []
        
        # Generate monthly signals for quality portfolio
        start_date = min(df.index[0] for df in price_data.values() if len(df) > 0)
        end_date = max(df.index[-1] for df in price_data.values() if len(df) > 0)
        
        # Monthly rebalancing dates
        rebalance_dates = pd.date_range(start=start_date, end=end_date, freq='MS')[:12]  # Limit to 12 months
        
        for rebal_date in rebalance_dates:
            portfolio_returns = []
            
            for _, stock in top_quality.iterrows():
                symbol = stock['symbol']
                
                if symbol in price_data:
                    df = price_data[symbol]
                    
                    # Find closest trading date
                    closest_date = df.index[df.index.get_indexer([rebal_date], method='nearest')[0]]
                    
                    if closest_date in df.index:
                        try:
                            # Calculate 1-month forward return
                            current_price = df.loc[closest_date, 'Close']
                            future_date = closest_date + pd.DateOffset(months=1)
                            future_dates = df.index[df.index >= future_date]
                            
                            if len(future_dates) > 0:
                                future_price = df.loc[future_dates[0], 'Close']
                                monthly_return = (future_price / current_price) - 1
                                portfolio_returns.append(monthly_return)
                                
                        except Exception:
                            continue
            
            if len(portfolio_returns) > 0:
                avg_return = np.mean(portfolio_returns)
                
                signals.append({
                    'date': rebal_date,
                    'signal_type': 'quality_factor',
                    'portfolio_size': len(portfolio_returns),
                    'avg_quality_score': top_quality['quality_score'].mean(),
                    'forward_1m': avg_return
                })
        
        return pd.DataFrame(signals)
    
    def get_fundamental_data(self, symbols):
        """Simulate fundamental data for quality metrics"""
        fundamental_data = {}
        
        for symbol in symbols[:15]:  # Limit for demo
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Extract quality-relevant metrics
                fundamental_data[symbol] = {
                    'returnOnEquity': info.get('returnOnEquity'),
                    'returnOnAssets': info.get('returnOnAssets'),
                    'debtToEquity': info.get('debtToEquity'),
                    'profitMargins': info.get('profitMargins'),
                    'operatingMargins': info.get('operatingMargins'),
                    'grossMargins': info.get('grossMargins')
                }
                
            except Exception:
                continue
        
        return fundamental_data