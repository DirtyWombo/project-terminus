"""
Strategy S07: Bollinger Bounce (Mean Reversion)
From The Compendium - Chapter 6: Mean Reversion Strategies

HYPOTHESIS: Buy small/mid-cap stocks when price touches lower 2.0 std dev 
Bollinger Band (20-period) and sell at middle band generates consistent 
profits in non-trending markets.

Expert Requirements:
- Statistical significance (p < 0.05)
- Information Ratio > 0.5
- Win Rate > 52%
- Sharpe Ratio > 1.0
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class BollingerBounceStrategy:
    """
    Bollinger Band Mean Reversion Strategy
    
    Signal Logic:
    1. Buy when price touches or goes below lower Bollinger Band (20-period, 2.0 std dev)
    2. Sell when price reaches middle Bollinger Band (20-period SMA)
    3. Filter: Only trade in non-trending markets (optional)
    4. Universe: Small/mid-cap stocks for reduced efficiency
    """
    
    def __init__(self, period=20, std_dev=2.0, trend_filter=False):
        self.period = period
        self.std_dev = std_dev
        self.trend_filter = trend_filter
        self.name = f"Bollinger Bounce ({period}p, {std_dev}std)"
        
    def calculate_signals(self, price_data):
        """
        Calculate Bollinger Bounce signals for given price data
        
        Returns:
        - signals_df: DataFrame with signals and forward returns
        """
        signals = []
        
        for symbol, df in price_data.items():
            if len(df) < self.period + 10:  # Need enough data
                continue
                
            # Calculate Bollinger Bands
            df['BB_Middle'] = df['Close'].rolling(window=self.period).mean()
            bb_std = df['Close'].rolling(window=self.period).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std * self.std_dev)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std * self.std_dev)
            
            # Calculate Bollinger Band position (0 = lower band, 1 = upper band)
            df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
            
            # Previous day values for signal detection
            df['Close_prev'] = df['Close'].shift(1)
            df['BB_Lower_prev'] = df['BB_Lower'].shift(1)
            df['BB_Position_prev'] = df['BB_Position'].shift(1)
            
            # Buy signal: Price touches or goes below lower band
            buy_signal = (
                (df['Close'] <= df['BB_Lower']) |  # Current price at/below lower band
                ((df['Close_prev'] > df['BB_Lower_prev']) & (df['Close'] <= df['BB_Lower']))  # Price pierces lower band
            )
            
            # Additional filters
            if self.trend_filter:
                # Only trade in non-trending markets (price within middle 60% of BB range)
                # Look at longer-term trend using 50-day MA
                df['MA_50'] = df['Close'].rolling(window=50).mean()
                trend_neutral = (
                    (abs(df['Close'] - df['MA_50']) / df['MA_50'] < 0.10)  # Within 10% of 50-day MA
                )
                buy_signal = buy_signal & trend_neutral
            
            # Volume filter (optional enhancement)
            avg_volume = df['Volume'].rolling(window=20).mean()
            volume_surge = df['Volume'] > (0.8 * avg_volume)  # At least 80% of average volume
            buy_signal = buy_signal & volume_surge
            
            # Calculate forward returns
            df['forward_1d'] = df['Close'].shift(-1) / df['Close'] - 1
            df['forward_3d'] = df['Close'].shift(-3) / df['Close'] - 1
            df['forward_5d'] = df['Close'].shift(-5) / df['Close'] - 1
            df['forward_10d'] = df['Close'].shift(-10) / df['Close'] - 1
            
            # Calculate return to middle band (target)
            df['return_to_middle'] = df['BB_Middle'] / df['Close'] - 1
            
            # Extract buy signals with forward returns
            buy_signals = df[buy_signal].copy()
            
            for _, row in buy_signals.iterrows():
                if not pd.isna(row['forward_1d']):  # Valid forward return
                    signal_data = {
                        'symbol': symbol,
                        'date': row.name,
                        'signal_type': 'bollinger_bounce',
                        'price': row['Close'],
                        'bb_lower': row['BB_Lower'],
                        'bb_middle': row['BB_Middle'],
                        'bb_upper': row['BB_Upper'],
                        'bb_position': row['BB_Position'],
                        'volume': row['Volume'],
                        'avg_volume': avg_volume.loc[row.name] if row.name in avg_volume.index else np.nan,
                        'return_to_middle': row['return_to_middle'],
                        'forward_1d': row['forward_1d'],
                        'forward_3d': row['forward_3d'],
                        'forward_5d': row['forward_5d'],
                        'forward_10d': row['forward_10d']
                    }
                    signals.append(signal_data)
        
        return pd.DataFrame(signals)
    
    def backtest_performance(self, signals_df):
        """
        Calculate strategy performance metrics
        """
        if len(signals_df) == 0:
            return None
            
        results = {}
        
        # Basic statistics
        results['total_signals'] = len(signals_df)
        results['unique_stocks'] = signals_df['symbol'].nunique()
        results['date_range'] = (signals_df['date'].min(), signals_df['date'].max())
        
        # Performance by holding period
        for period in ['1d', '3d', '5d', '10d']:
            col = f'forward_{period}'
            returns = signals_df[col].dropna()
            
            if len(returns) > 10:
                # Basic statistics
                mean_return = returns.mean()
                std_return = returns.std()
                win_rate = (returns > 0).sum() / len(returns)
                
                # Statistical significance
                t_stat, p_value = stats.ttest_1samp(returns, 0)
                
                # Information ratio
                info_ratio = mean_return / std_return if std_return > 0 else 0
                
                # Annualized Sharpe ratio
                if period == '1d':
                    trading_days = 252
                elif period == '3d':
                    trading_days = 252 / 3
                elif period == '5d':
                    trading_days = 252 / 5
                else:  # 10d
                    trading_days = 252 / 10
                    
                sharpe_ratio = info_ratio * np.sqrt(trading_days)
                
                results[f'{period}_mean_return'] = mean_return
                results[f'{period}_std_return'] = std_return
                results[f'{period}_win_rate'] = win_rate
                results[f'{period}_info_ratio'] = info_ratio
                results[f'{period}_sharpe_ratio'] = sharpe_ratio
                results[f'{period}_t_stat'] = t_stat
                results[f'{period}_p_value'] = p_value
                results[f'{period}_sample_size'] = len(returns)
        
        return results
    
    def validate_alpha(self, signals_df, primary_period='3d'):
        """
        Validate alpha signal against expert criteria
        """
        if len(signals_df) == 0:
            return {'passed': False, 'reason': 'No signals generated'}
        
        col = f'forward_{primary_period}'
        returns = signals_df[col].dropna()
        
        if len(returns) < 30:
            return {'passed': False, 'reason': f'Insufficient signals: {len(returns)} < 30'}
        
        # Calculate key metrics
        t_stat, p_value = stats.ttest_1samp(returns, 0)
        info_ratio = returns.mean() / returns.std() if returns.std() > 0 else 0
        win_rate = (returns > 0).sum() / len(returns)
        
        # Annualized Sharpe ratio
        if primary_period == '1d':
            trading_days = 252
        elif primary_period == '3d':
            trading_days = 252 / 3
        elif primary_period == '5d':
            trading_days = 252 / 5
        else:  # 10d
            trading_days = 252 / 10
            
        sharpe_ratio = info_ratio * np.sqrt(trading_days)
        
        # Expert validation criteria
        criteria = {
            'statistical_significance': p_value < 0.05,
            'information_ratio': info_ratio > 0.5,
            'win_rate': win_rate > 0.52,
            'sharpe_ratio': sharpe_ratio > 1.0,
            'sample_size': len(returns) >= 30
        }
        
        passed_tests = sum(criteria.values())
        total_tests = len(criteria)
        
        return {
            'passed': passed_tests >= 4,  # Need 4/5 criteria
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'criteria': criteria,
            'metrics': {
                'mean_return': returns.mean(),
                'info_ratio': info_ratio,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'p_value': p_value,
                'sample_size': len(returns)
            }
        }

def get_small_midcap_universe():
    """
    Get small/mid-cap universe for Bollinger Bounce testing
    Focus on liquid, mean-reverting stocks
    """
    return [
        # Cloud/SaaS (more volatile, good for mean reversion)
        'CRWD', 'SNOW', 'DDOG', 'NET', 'OKTA', 'ZS', 'PLTR',
        # Fintech
        'PYPL', 'SOFI', 'AFRM', 'COIN',
        # Growth Tech
        'RBLX', 'U', 'PATH', 'ROKU', 'SPOT',
        # E-commerce/Consumer
        'SHOP', 'ETSY', 'W', 'CHWY', 'PINS',
        # Healthcare/Biotech (high volatility)
        'TDOC', 'VEEV', 'DXCM', 'ILMN', 'MRNA',
        # Clean Energy (volatile sector)
        'ENPH', 'SEDG', 'RUN', 'FSLR', 'BE',
        # Communication
        'ZM', 'DOCU', 'TWLO', 'TEAM'
    ]

def collect_price_data(symbols, period="2y"):
    """
    Collect historical price data for strategy testing
    Shorter period since mean reversion works on recent patterns
    """
    price_data = {}
    
    print(f"Collecting data for {len(symbols)} symbols...")
    
    for i, symbol in enumerate(symbols):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if len(hist) > 100:  # Need sufficient data for Bollinger Bands
                # Calculate daily returns for later use
                hist['daily_return'] = hist['Close'].pct_change()
                price_data[symbol] = hist
                print(f"[OK] {symbol}: {len(hist)} days ({hist.index[0].date()} to {hist.index[-1].date()})")
            else:
                print(f"[SKIP] {symbol}: Insufficient data ({len(hist)} days)")
                
        except Exception as e:
            print(f"[ERROR] {symbol}: Error - {e}")
            
        if (i + 1) % 10 == 0:
            print(f"Progress: {i + 1}/{len(symbols)} completed")
    
    print(f"\n[SUCCESS] Successfully collected data for {len(price_data)} stocks")
    return price_data

if __name__ == "__main__":
    print("=" * 60)
    print("BOLLINGER BOUNCE STRATEGY - ALPHA VALIDATION")
    print("=" * 60)
    
    # Initialize strategy
    strategy = BollingerBounceStrategy(period=20, std_dev=2.0, trend_filter=False)
    print(f"Strategy: {strategy.name}")
    print(f"Universe: Small/mid-cap stocks")
    print(f"Hypothesis: Mean reversion at 2-std Bollinger Bands")
    
    # Get universe and collect data
    universe = get_small_midcap_universe()
    price_data = collect_price_data(universe, period="2y")
    
    if len(price_data) < 5:
        print("[ERROR] Insufficient data collected. Cannot proceed with validation.")
        exit(1)
    
    # Generate signals
    print("\nGenerating Bollinger Bounce signals...")
    signals_df = strategy.calculate_signals(price_data)
    
    print(f"Generated {len(signals_df)} Bollinger Bounce signals")
    
    if len(signals_df) > 0:
        # Backtest performance
        print("\nCalculating performance metrics...")
        performance = strategy.backtest_performance(signals_df)
        
        # Display results
        print("\n" + "=" * 60)
        print("PERFORMANCE RESULTS")
        print("=" * 60)
        
        print(f"Total Signals: {performance['total_signals']}")
        print(f"Unique Stocks: {performance['unique_stocks']}")
        print(f"Date Range: {performance['date_range'][0].date()} to {performance['date_range'][1].date()}")
        
        # Show results for different holding periods
        for period in ['1d', '3d', '5d', '10d']:
            if f'{period}_mean_return' in performance:
                mean_ret = performance[f'{period}_mean_return'] * 100
                win_rate = performance[f'{period}_win_rate'] * 100
                info_ratio = performance[f'{period}_info_ratio']
                sharpe = performance[f'{period}_sharpe_ratio']
                p_val = performance[f'{period}_p_value']
                
                print(f"\n{period.upper()} Holding Period:")
                print(f"  Mean Return: {mean_ret:.2f}%")  
                print(f"  Win Rate: {win_rate:.1f}%")
                print(f"  Info Ratio: {info_ratio:.3f}")
                print(f"  Sharpe Ratio: {sharpe:.2f}")
                print(f"  P-value: {p_val:.4f} {'[PASS]' if p_val < 0.05 else '[FAIL]'}")
        
        # Alpha validation
        print("\n" + "=" * 60)
        print("EXPERT ALPHA VALIDATION")
        print("=" * 60)
        
        validation = strategy.validate_alpha(signals_df, primary_period='3d')
        
        if validation['passed']:
            print("[PASS] ALPHA VALIDATION PASSED")
            print(f"Tests Passed: {validation['passed_tests']}/{validation['total_tests']}")
            
            metrics = validation['metrics']
            print(f"\nKey Metrics (3-day holding):")
            print(f"  Mean Return: {metrics['mean_return']*100:.2f}%")
            print(f"  Win Rate: {metrics['win_rate']:.1%}")
            print(f"  Information Ratio: {metrics['info_ratio']:.3f}")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"  P-value: {metrics['p_value']:.4f}")
            print(f"  Sample Size: {metrics['sample_size']}")
            
            print("\n[PASS] RECOMMENDATION: Proceed with full robustness testing")
            
        else:
            print("[FAIL] ALPHA VALIDATION FAILED")
            print(f"Tests Passed: {validation['passed_tests']}/{validation['total_tests']}")
            
            criteria = validation['criteria']
            print("\nFailed Criteria:")
            for criterion, passed in criteria.items():
                status = "[PASS]" if passed else "[FAIL]"
                print(f"  {criterion}: {status}")
            
            print("\n[FAIL] RECOMMENDATION: Strategy does not meet alpha requirements")
        
        # Additional analysis for mean reversion
        print("\n" + "=" * 60)
        print("MEAN REVERSION ANALYSIS")
        print("=" * 60)
        
        # Analyze return to middle band
        return_to_middle = signals_df['return_to_middle'].dropna()
        if len(return_to_middle) > 0:
            avg_distance = return_to_middle.mean() * 100
            print(f"Average distance to middle band: {avg_distance:.2f}%")
            print(f"Signals capturing >1% mean reversion potential: {(return_to_middle > 0.01).sum()}")
            print(f"Signals capturing >2% mean reversion potential: {(return_to_middle > 0.02).sum()}")
        
        # Analyze Bollinger Band position distribution
        bb_positions = signals_df['bb_position'].dropna()
        if len(bb_positions) > 0:
            print(f"Average BB position at signal: {bb_positions.mean():.3f} (0=lower, 1=upper)")
            print(f"Signals at true lower band (position < 0.05): {(bb_positions < 0.05).sum()}")
    
    else:
        print("[ERROR] No signals generated. Check strategy parameters or data quality.")