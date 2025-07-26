"""
Strategy S14: Profitability Factor
From The Compendium - Chapter 9: Factor-Based Strategies

Signal Logic:
- Select stocks with high profitability metrics: Gross margins, Operating margins, ROI
- Monthly rebalancing to top profitability quintile
- Focus on companies with consistent profit generation
- Exclude loss-making companies
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class ProfitabilityFactorStrategy:
    """
    Profitability Factor Strategy
    
    Targets companies with superior profit generation ability
    Academic factor with proven long-term alpha
    """
    
    def __init__(self, rebalance_freq='M', top_percentile=0.2):
        self.rebalance_freq = rebalance_freq
        self.top_percentile = top_percentile
        self.name = f"Profitability Factor (Top {int(top_percentile*100)}%)"
        
    def calculate_profitability_score(self, fundamental_data):
        """Calculate composite profitability score"""
        scores = []
        
        for symbol, data in fundamental_data.items():
            try:
                # Profitability metrics
                gross_margin = data.get('grossMargins', 0) if data.get('grossMargins') else 0
                operating_margin = data.get('operatingMargins', 0) if data.get('operatingMargins') else 0
                profit_margin = data.get('profitMargins', 0) if data.get('profitMargins') else 0
                roe = data.get('returnOnEquity', 0) / 100 if data.get('returnOnEquity') else 0
                roic = data.get('returnOnCapital', 0) / 100 if data.get('returnOnCapital') else 0
                
                # Skip companies with negative profitability
                if profit_margin <= 0:
                    continue
                
                # Profitability score (higher is better)
                profitability_score = (
                    gross_margin * 0.2 +      # 20% weight on gross margins
                    operating_margin * 0.3 +  # 30% weight on operating margins  
                    profit_margin * 0.2 +     # 20% weight on net margins
                    roe * 0.15 +              # 15% weight on ROE
                    roic * 0.15               # 15% weight on ROIC
                )
                
                scores.append({
                    'symbol': symbol,
                    'profitability_score': profitability_score,
                    'gross_margin': gross_margin,
                    'operating_margin': operating_margin,
                    'profit_margin': profit_margin,
                    'roe': roe,
                    'roic': roic
                })
                
            except Exception:
                continue
        
        return pd.DataFrame(scores)
    
    def calculate_signals(self, price_data):
        """Calculate profitability factor signals"""
        # Get fundamental data
        fundamental_data = self.get_fundamental_data(list(price_data.keys()))
        
        if len(fundamental_data) < 10:
            return pd.DataFrame()
        
        # Calculate profitability scores
        profitability_scores = self.calculate_profitability_score(fundamental_data)
        
        if len(profitability_scores) == 0:
            return pd.DataFrame()
        
        # Select top profitability stocks
        profitability_scores = profitability_scores.sort_values('profitability_score', ascending=False)
        top_count = max(1, int(len(profitability_scores) * self.top_percentile))
        top_profitable = profitability_scores.head(top_count)
        
        signals = []
        
        # Generate monthly signals
        start_date = min(df.index[0] for df in price_data.values() if len(df) > 0)
        end_date = max(df.index[-1] for df in price_data.values() if len(df) > 0)
        
        rebalance_dates = pd.date_range(start=start_date, end=end_date, freq='MS')[:12]
        
        for rebal_date in rebalance_dates:
            portfolio_returns = []
            
            for _, stock in top_profitable.iterrows():
                symbol = stock['symbol']
                
                if symbol in price_data:
                    df = price_data[symbol]
                    closest_date = df.index[df.index.get_indexer([rebal_date], method='nearest')[0]]
                    
                    if closest_date in df.index:
                        try:
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
                    'signal_type': 'profitability_factor',
                    'portfolio_size': len(portfolio_returns),
                    'avg_profitability_score': top_profitable['profitability_score'].mean(),
                    'forward_1m': avg_return
                })
        
        return pd.DataFrame(signals)
    
    def get_fundamental_data(self, symbols):
        """Get fundamental data for profitability analysis"""
        fundamental_data = {}
        
        for symbol in symbols[:15]:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                fundamental_data[symbol] = {
                    'grossMargins': info.get('grossMargins'),
                    'operatingMargins': info.get('operatingMargins'),
                    'profitMargins': info.get('profitMargins'),
                    'returnOnEquity': info.get('returnOnEquity'),
                    'returnOnCapital': info.get('returnOnAssets')  # Proxy for ROIC
                }
                
            except Exception:
                continue
        
        return fundamental_data