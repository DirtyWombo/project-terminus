"""
Strategy S20: GARCH Volatility Forecasting
From The Compendium - Chapter 7: Volatility Strategies

Signal Logic:
- Use GARCH model to forecast volatility
- Buy when realized volatility < predicted volatility (vol expansion expected)
- Sell when realized volatility > predicted volatility (vol contraction expected)
- Trade volatility-sensitive assets (options proxies)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class GARCHForecastingStrategy:
    """
    GARCH Volatility Forecasting Strategy
    
    Simplified GARCH implementation for volatility prediction
    Trades on volatility mean reversion patterns
    """
    
    def __init__(self, lookback_period=60, vol_threshold=0.2):
        self.lookback_period = lookback_period
        self.vol_threshold = vol_threshold  # 20% volatility threshold
        self.name = f"GARCH Forecasting ({lookback_period}p)"
        
    def estimate_simple_garch(self, returns):
        """
        Simplified GARCH(1,1) estimation
        In production: use proper GARCH library like arch
        """
        # Calculate squared returns (proxy for variance)
        squared_returns = returns ** 2
        
        # Simple GARCH approximation using rolling statistics
        # Variance = omega + alpha * lagged_squared_return + beta * lagged_variance
        
        # Rolling variance (long-term average)
        long_term_var = squared_returns.rolling(window=self.lookback_period).mean()
        
        # Short-term variance
        short_term_var = squared_returns.rolling(window=10).mean()
        
        # GARCH forecast (simplified)
        # Higher weight on recent variance
        alpha = 0.1  # ARCH parameter
        beta = 0.8   # GARCH parameter
        omega = long_term_var * (1 - alpha - beta)
        
        forecasted_var = omega + alpha * squared_returns.shift(1) + beta * short_term_var.shift(1)
        forecasted_vol = np.sqrt(forecasted_var)
        
        return forecasted_vol
    
    def calculate_signals(self, price_data):
        """Calculate GARCH volatility signals"""
        signals = []
        
        # Focus on highly liquid, volatility-sensitive stocks
        vol_sensitive_symbols = []
        for symbol, df in price_data.items():
            if len(df) > self.lookback_period + 20:
                # Check if stock has sufficient volatility to be worth trading
                returns = df['Close'].pct_change().dropna()
                if returns.std() > 0.02:  # At least 2% daily volatility
                    vol_sensitive_symbols.append(symbol)
        
        print(f"Analyzing volatility for {len(vol_sensitive_symbols)} symbols")
        
        for symbol in vol_sensitive_symbols[:10]:  # Limit for computation
            df = price_data[symbol].copy()
            
            # Calculate returns
            df['returns'] = df['Close'].pct_change()
            df = df.dropna()
            
            if len(df) < self.lookback_period + 20:
                continue
            
            # Calculate realized volatility (rolling)
            df['realized_vol'] = df['returns'].rolling(window=20).std() * np.sqrt(252)
            
            # Estimate GARCH forecasted volatility
            df['forecasted_vol'] = self.estimate_simple_garch(df['returns']) * np.sqrt(252)
            
            # Calculate volatility spread
            df['vol_spread'] = df['realized_vol'] - df['forecasted_vol']
            
            # Generate signals
            # Buy when realized vol < forecasted vol (expect vol expansion)
            vol_buy_signal = (df['vol_spread'] < -self.vol_threshold) & (df['forecasted_vol'] > 0.15)
            
            # Sell when realized vol > forecasted vol (expect vol contraction)  
            vol_sell_signal = (df['vol_spread'] > self.vol_threshold) & (df['realized_vol'] > 0.3)
            
            # Calculate forward returns
            df['forward_1d'] = df['Close'].shift(-1) / df['Close'] - 1
            df['forward_3d'] = df['Close'].shift(-3) / df['Close'] - 1
            df['forward_5d'] = df['Close'].shift(-5) / df['Close'] - 1
            
            # Process buy signals (expect volatility increase helps returns)
            buy_dates = df[vol_buy_signal].index
            
            for date in buy_dates:
                if not pd.isna(df.loc[date, 'forward_5d']):
                    signal_data = {
                        'symbol': symbol,
                        'date': date,
                        'signal_type': 'garch_vol_expansion',
                        'price': df.loc[date, 'Close'],
                        'realized_vol': df.loc[date, 'realized_vol'],
                        'forecasted_vol': df.loc[date, 'forecasted_vol'],
                        'vol_spread': df.loc[date, 'vol_spread'],
                        'forward_1d': df.loc[date, 'forward_1d'],
                        'forward_3d': df.loc[date, 'forward_3d'],
                        'forward_5d': df.loc[date, 'forward_5d']
                    }
                    signals.append(signal_data)
            
            # Process sell signals (expect volatility decrease, short opportunity)
            sell_dates = df[vol_sell_signal].index
            
            for date in sell_dates:
                if not pd.isna(df.loc[date, 'forward_5d']):
                    # Invert returns for short position
                    signal_data = {
                        'symbol': symbol,
                        'date': date,
                        'signal_type': 'garch_vol_contraction',
                        'price': df.loc[date, 'Close'],
                        'realized_vol': df.loc[date, 'realized_vol'],
                        'forecasted_vol': df.loc[date, 'forecasted_vol'],
                        'vol_spread': df.loc[date, 'vol_spread'],
                        'forward_1d': -df.loc[date, 'forward_1d'],  # Short position
                        'forward_3d': -df.loc[date, 'forward_3d'],
                        'forward_5d': -df.loc[date, 'forward_5d']
                    }
                    signals.append(signal_data)
        
        return pd.DataFrame(signals)
    
    def calculate_volatility_metrics(self, signals_df):
        """Calculate additional volatility-specific metrics"""
        if len(signals_df) == 0:
            return {}
        
        # Analyze volatility forecasting accuracy
        vol_accuracy = {}
        
        expansion_signals = signals_df[signals_df['signal_type'] == 'garch_vol_expansion']
        contraction_signals = signals_df[signals_df['signal_type'] == 'garch_vol_contraction']
        
        vol_accuracy['expansion_signals'] = len(expansion_signals)
        vol_accuracy['contraction_signals'] = len(contraction_signals)
        
        if len(expansion_signals) > 0:
            vol_accuracy['avg_vol_spread_expansion'] = expansion_signals['vol_spread'].mean()
            vol_accuracy['expansion_win_rate'] = (expansion_signals['forward_5d'] > 0).mean()
        
        if len(contraction_signals) > 0:
            vol_accuracy['avg_vol_spread_contraction'] = contraction_signals['vol_spread'].mean()
            vol_accuracy['contraction_win_rate'] = (contraction_signals['forward_5d'] > 0).mean()
        
        return vol_accuracy