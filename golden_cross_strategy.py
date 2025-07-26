"""
Strategy S02: Double MA Crossover (Golden Cross)
From The Compendium - Chapter 5: Moving Average Strategies

HYPOTHESIS: 50/200-day Golden Cross + long-term trend filter provides 
statistically significant edge in small/mid-cap universe.

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

class GoldenCrossStrategy:
    """
    Double Moving Average Crossover Strategy
    
    Signal Logic:
    1. Buy when 50-day MA crosses above 200-day MA (Golden Cross)
    2. Additional filter: Price must be above 200-day MA (long-term trend)
    3. Sell when 50-day MA crosses below 200-day MA (Death Cross)
    4. Universe: Small/mid-cap stocks for reduced HFT competition
    """
    
    def __init__(self, short_window=50, long_window=200, trend_filter=True):
        self.short_window = short_window
        self.long_window = long_window
        self.trend_filter = trend_filter
        self.name = f"Golden Cross ({short_window}/{long_window})"
        
    def calculate_signals(self, price_data):
        """
        Calculate Golden Cross signals for given price data
        
        Returns:
        - signals_df: DataFrame with signals and forward returns
        """
        signals = []
        
        for symbol, df in price_data.items():
            if len(df) < self.long_window + 10:  # Need enough data
                continue
                
            # Calculate moving averages
            df['MA_50'] = df['Close'].rolling(window=self.short_window).mean()
            df['MA_200'] = df['Close'].rolling(window=self.long_window).mean()
            
            # Calculate signal conditions
            df['MA_50_prev'] = df['MA_50'].shift(1)
            df['MA_200_prev'] = df['MA_200'].shift(1)
            
            # Golden Cross: 50-day MA crosses above 200-day MA
            golden_cross = (
                (df['MA_50'] > df['MA_200']) & 
                (df['MA_50_prev'] <= df['MA_200_prev'])
            )
            
            # Death Cross: 50-day MA crosses below 200-day MA
            death_cross = (
                (df['MA_50'] < df['MA_200']) & 
                (df['MA_50_prev'] >= df['MA_200_prev'])
            )
            
            # Trend filter: Price above 200-day MA
            if self.trend_filter:
                trend_up = df['Close'] > df['MA_200']
                golden_cross = golden_cross & trend_up
            
            # Generate signals
            df['signal'] = 0
            df.loc[golden_cross, 'signal'] = 1   # Buy signal
            df.loc[death_cross, 'signal'] = -1   # Sell signal
            
            # Calculate forward returns
            df['forward_1d'] = df['Close'].shift(-1) / df['Close'] - 1
            df['forward_3d'] = df['Close'].shift(-3) / df['Close'] - 1
            df['forward_5d'] = df['Close'].shift(-5) / df['Close'] - 1
            df['forward_10d'] = df['Close'].shift(-10) / df['Close'] - 1
            df['forward_20d'] = df['Close'].shift(-20) / df['Close'] - 1
            
            # Extract buy signals with forward returns
            buy_signals = df[df['signal'] == 1].copy()
            
            for _, row in buy_signals.iterrows():
                if not pd.isna(row['forward_1d']):  # Valid forward return
                    signal_data = {
                        'symbol': symbol,
                        'date': row.name,
                        'signal_type': 'golden_cross',
                        'price': row['Close'],
                        'ma_50': row['MA_50'],
                        'ma_200': row['MA_200'],
                        'volume': row['Volume'],
                        'forward_1d': row['forward_1d'],
                        'forward_3d': row['forward_3d'],
                        'forward_5d': row['forward_5d'],
                        'forward_10d': row['forward_10d'],
                        'forward_20d': row['forward_20d']
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
        for period in ['1d', '3d', '5d', '10d', '20d']:
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
                elif period == '10d':
                    trading_days = 252 / 10
                else:  # 20d
                    trading_days = 252 / 20
                    
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
    
    def validate_alpha(self, signals_df, primary_period='5d'):
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
        elif primary_period == '10d':
            trading_days = 252 / 10
        else:  # 20d
            trading_days = 252 / 20
            
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
    Get small/mid-cap universe for Golden Cross testing
    Focus on liquid, narrative-sensitive stocks
    """
    return [
        # Cloud/SaaS
        'CRWD', 'SNOW', 'DDOG', 'NET', 'OKTA', 'ZS', 'PLTR',
        # Fintech
        'SQ', 'PYPL', 'SOFI', 'AFRM', 'COIN',
        # Growth Tech
        'RBLX', 'U', 'PATH', 'ROKU', 'SPOT',
        # E-commerce/Consumer
        'SHOP', 'ETSY', 'W', 'CHWY', 'PINS',
        # Healthcare/Biotech
        'TDOC', 'VEEV', 'DXCM', 'ILMN', 'MRNA',
        # Industrial/Materials
        'ENPH', 'SEDG', 'RUN', 'FSLR', 'BE',
        # Communication
        'ZM', 'DOCU', 'TWLO', 'TEAM', 'ZEN'
    ]

def collect_price_data(symbols, period="3y"):
    """
    Collect historical price data for strategy testing
    """
    price_data = {}
    
    print(f"Collecting data for {len(symbols)} symbols...")
    
    for i, symbol in enumerate(symbols):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if len(hist) > 300:  # Need sufficient data for 200-day MA
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
    print("GOLDEN CROSS STRATEGY - ALPHA VALIDATION")
    print("=" * 60)
    
    # Initialize strategy
    strategy = GoldenCrossStrategy(short_window=50, long_window=200, trend_filter=True)
    print(f"Strategy: {strategy.name}")
    print(f"Universe: Small/mid-cap stocks")
    print(f"Hypothesis: 50/200-day Golden Cross with trend filter")
    
    # Get universe and collect data
    universe = get_small_midcap_universe()
    price_data = collect_price_data(universe, period="3y")
    
    if len(price_data) < 5:
        print("[ERROR] Insufficient data collected. Cannot proceed with validation.")
        exit(1)
    
    # Generate signals
    print("\nGenerating Golden Cross signals...")
    signals_df = strategy.calculate_signals(price_data)
    
    print(f"Generated {len(signals_df)} Golden Cross signals")
    
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
        for period in ['5d', '10d', '20d']:
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
        
        validation = strategy.validate_alpha(signals_df, primary_period='5d')
        
        if validation['passed']:
            print("[PASS] ALPHA VALIDATION PASSED")
            print(f"Tests Passed: {validation['passed_tests']}/{validation['total_tests']}")
            
            metrics = validation['metrics']
            print(f"\nKey Metrics (5-day holding):")
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
    
    else:
        print("[ERROR] No signals generated. Check strategy parameters or data quality.")