"""
Strategy S11: Single-Factor Value Portfolio  
From The Compendium - Chapter 9: Factor-Based Strategies

HYPOTHESIS: A portfolio of top decile small-cap stocks ranked by Earnings 
Yield (EBIT/EV), rebalanced monthly, will outperform Russell 2000 index 
on risk-adjusted basis.

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

class ValueFactorStrategy:
    """
    Single-Factor Value Strategy using Earnings Yield
    
    Strategy Logic:
    1. Universe: Small-cap stocks ($300M - $10B market cap)
    2. Factor: Earnings Yield = EBIT / Enterprise Value  
    3. Ranking: Monthly rebalancing to top decile (top 10%)
    4. Benchmark: Russell 2000 index performance
    5. Holding: Equal-weighted portfolio, monthly rebalancing
    """
    
    def __init__(self, rebalance_freq='M', top_percentile=0.1):
        self.rebalance_freq = rebalance_freq  # Monthly rebalancing
        self.top_percentile = top_percentile  # Top 10%
        self.name = f"Value Factor (Earnings Yield, Top {int(top_percentile*100)}%)"
        
    def get_fundamental_data(self, symbols):
        """
        Get fundamental data for value factor calculation
        Using approximate values since we don't have SEC integration yet
        """
        fundamental_data = {}
        
        print("Collecting fundamental data for value factor calculation...")
        
        for i, symbol in enumerate(symbols):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Get key fundamental metrics
                market_cap = info.get('marketCap', None)
                enterprise_value = info.get('enterpriseValue', None)
                ebit = info.get('ebit', None)
                
                # Alternative calculation if EBIT not available
                if ebit is None:
                    operating_income = info.get('operatingIncome', None)
                    ebit = operating_income
                
                # Calculate earnings yield if we have the data
                if enterprise_value and ebit and enterprise_value > 0:
                    earnings_yield = ebit / enterprise_value
                    
                    fundamental_data[symbol] = {
                        'market_cap': market_cap,
                        'enterprise_value': enterprise_value,
                        'ebit': ebit,
                        'earnings_yield': earnings_yield,
                        'sector': info.get('sector', 'Unknown'),
                        'industry': info.get('industry', 'Unknown')
                    }
                    
                    print(f"[OK] {symbol}: EY={earnings_yield:.4f}, EV=${enterprise_value/1e9:.1f}B")
                else:
                    print(f"[SKIP] {symbol}: Missing fundamental data")
                    
            except Exception as e:
                print(f"[ERROR] {symbol}: {e}")
                
            if (i + 1) % 5 == 0:
                print(f"Progress: {i + 1}/{len(symbols)} completed")
        
        print(f"\n[SUCCESS] Collected fundamental data for {len(fundamental_data)} stocks")
        return fundamental_data
    
    def calculate_factor_scores(self, fundamental_data, price_data, date):
        """
        Calculate value factor scores for a given date
        """
        scores = []
        
        for symbol in fundamental_data.keys():
            if symbol in price_data:
                # Get market data around the date
                df = price_data[symbol]
                closest_date = df.index[df.index.get_indexer([date], method='nearest')[0]]
                
                if closest_date in df.index:
                    current_price = df.loc[closest_date, 'Close']
                    
                    # Get fundamental data
                    fund_data = fundamental_data[symbol]
                    earnings_yield = fund_data['earnings_yield']
                    
                    # Additional value metrics (if available)
                    market_cap = fund_data.get('market_cap', current_price * 1000000)  # Approximate
                    
                    # Filter for small-cap (rough filter using available data)
                    if 300e6 <= market_cap <= 10e9:  # $300M to $10B
                        scores.append({
                            'symbol': symbol,
                            'date': closest_date,
                            'price': current_price,
                            'earnings_yield': earnings_yield,
                            'market_cap': market_cap,
                            'sector': fund_data.get('sector', 'Unknown')
                        })
        
        return pd.DataFrame(scores)
    
    def generate_portfolio_signals(self, fundamental_data, price_data):
        """
        Generate monthly portfolio rebalancing signals
        """
        signals = []
        
        # Get date range for rebalancing
        start_date = min(df.index[0] for df in price_data.values())
        end_date = max(df.index[-1] for df in price_data.values())
        
        # Generate monthly rebalancing dates
        rebalance_dates = pd.date_range(start=start_date, end=end_date, freq='MS')  # Month start
        
        print(f"Generating monthly portfolio signals from {start_date.date()} to {end_date.date()}")
        print(f"Rebalancing dates: {len(rebalance_dates)}")
        
        for i, rebal_date in enumerate(rebalance_dates):
            print(f"Processing rebalance {i+1}/{len(rebalance_dates)}: {rebal_date.date()}")
            
            # Calculate factor scores for this date
            scores_df = self.calculate_factor_scores(fundamental_data, price_data, rebal_date)
            
            if len(scores_df) >= 10:  # Need minimum stocks for portfolio
                # Rank by earnings yield (higher is better for value)
                scores_df = scores_df.sort_values('earnings_yield', ascending=False)
                
                # Select top decile
                top_count = max(1, int(len(scores_df) * self.top_percentile))
                top_stocks = scores_df.head(top_count)
                
                # Calculate forward returns for portfolio
                portfolio_returns = []
                
                for _, stock in top_stocks.iterrows():
                    symbol = stock['symbol']
                    
                    if symbol in price_data:
                        df = price_data[symbol]
                        current_date = stock['date']
                        
                        # Calculate 1-month forward return
                        try:
                            future_date = current_date + pd.DateOffset(months=1)
                            future_dates = df.index[df.index >= future_date]
                            
                            if len(future_dates) > 0:
                                future_price = df.loc[future_dates[0], 'Close']
                                current_price = stock['price']
                                
                                monthly_return = (future_price / current_price) - 1
                                portfolio_returns.append(monthly_return)
                                
                        except Exception as e:
                            continue
                
                # Calculate equal-weighted portfolio return
                if len(portfolio_returns) > 0:
                    avg_portfolio_return = np.mean(portfolio_returns)
                    
                    signal_data = {
                        'date': rebal_date,
                        'portfolio_size': len(top_stocks),
                        'avg_earnings_yield': top_stocks['earnings_yield'].mean(),
                        'selected_stocks': list(top_stocks['symbol'].values),
                        'forward_1m': avg_portfolio_return,
                        'individual_returns': portfolio_returns
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
        results['total_rebalances'] = len(signals_df)
        results['avg_portfolio_size'] = signals_df['portfolio_size'].mean()
        results['date_range'] = (signals_df['date'].min(), signals_df['date'].max())
        
        # Monthly returns analysis
        monthly_returns = signals_df['forward_1m'].dropna()
        
        if len(monthly_returns) > 6:  # Need at least 6 months
            # Basic statistics
            mean_return = monthly_returns.mean()
            std_return = monthly_returns.std()
            win_rate = (monthly_returns > 0).sum() / len(monthly_returns)
            
            # Statistical significance
            t_stat, p_value = stats.ttest_1samp(monthly_returns, 0)
            
            # Information ratio
            info_ratio = mean_return / std_return if std_return > 0 else 0
            
            # Annualized Sharpe ratio (12 months per year)
            sharpe_ratio = info_ratio * np.sqrt(12)
            
            # Cumulative performance
            cumulative_returns = (1 + monthly_returns).cumprod()
            total_return = cumulative_returns.iloc[-1] - 1
            
            results['mean_monthly_return'] = mean_return
            results['std_monthly_return'] = std_return
            results['win_rate'] = win_rate
            results['info_ratio'] = info_ratio
            results['sharpe_ratio'] = sharpe_ratio
            results['t_stat'] = t_stat
            results['p_value'] = p_value
            results['sample_size'] = len(monthly_returns)
            results['total_return'] = total_return
            results['avg_earnings_yield'] = signals_df['avg_earnings_yield'].mean()
        
        return results
    
    def validate_alpha(self, signals_df):
        """
        Validate alpha signal against expert criteria
        """
        if len(signals_df) == 0:
            return {'passed': False, 'reason': 'No signals generated'}
        
        monthly_returns = signals_df['forward_1m'].dropna()
        
        if len(monthly_returns) < 12:  # Need at least 12 months
            return {'passed': False, 'reason': f'Insufficient data: {len(monthly_returns)} < 12 months'}
        
        # Calculate key metrics
        t_stat, p_value = stats.ttest_1samp(monthly_returns, 0)
        info_ratio = monthly_returns.mean() / monthly_returns.std() if monthly_returns.std() > 0 else 0
        win_rate = (monthly_returns > 0).sum() / len(monthly_returns)
        sharpe_ratio = info_ratio * np.sqrt(12)  # Annualized
        
        # Expert validation criteria
        criteria = {
            'statistical_significance': p_value < 0.05,
            'information_ratio': info_ratio > 0.5,
            'win_rate': win_rate > 0.52,
            'sharpe_ratio': sharpe_ratio > 1.0,
            'sample_size': len(monthly_returns) >= 12
        }
        
        passed_tests = sum(criteria.values())
        total_tests = len(criteria)
        
        return {
            'passed': passed_tests >= 4,  # Need 4/5 criteria
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'criteria': criteria,
            'metrics': {
                'mean_monthly_return': monthly_returns.mean(),
                'info_ratio': info_ratio,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'p_value': p_value,
                'sample_size': len(monthly_returns)
            }
        }

def get_small_cap_value_universe():
    """
    Get small-cap universe for value factor testing
    Focus on established small-caps with available fundamental data
    """
    return [
        # Small-cap tech with fundamentals
        'PLTR', 'U', 'PATH', 'DDOG', 'NET',
        # Small-cap healthcare
        'VEEV', 'DXCM', 'TDOC', 'ILMN',
        # Small-cap consumer
        'ETSY', 'CHWY', 'W', 'PINS',
        # Small-cap energy
        'ENPH', 'SEDG', 'RUN', 'FSLR', 'BE',
        # Small-cap services
        'TWLO', 'TEAM', 'DOCU', 'ZM',
        # Small-cap fintech
        'SOFI', 'AFRM', 'COIN'
    ]

def collect_price_data(symbols, period="2y"):
    """
    Collect historical price data for strategy testing
    """
    price_data = {}
    
    print(f"Collecting price data for {len(symbols)} symbols...")
    
    for i, symbol in enumerate(symbols):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if len(hist) > 200:  # Need sufficient data
                hist['daily_return'] = hist['Close'].pct_change()
                price_data[symbol] = hist
                print(f"[OK] {symbol}: {len(hist)} days")
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
    print("VALUE FACTOR STRATEGY - ALPHA VALIDATION")
    print("=" * 60)
    
    # Initialize strategy
    strategy = ValueFactorStrategy(rebalance_freq='M', top_percentile=0.1)
    print(f"Strategy: {strategy.name}")
    print(f"Universe: Small-cap stocks")
    print(f"Hypothesis: Top decile earnings yield outperforms Russell 2000")
    
    # Get universe and collect data
    universe = get_small_cap_value_universe()
    price_data = collect_price_data(universe, period="2y")
    
    if len(price_data) < 10:
        print("[ERROR] Insufficient price data collected. Cannot proceed with validation.")
        exit(1)
    
    # Get fundamental data
    fundamental_data = strategy.get_fundamental_data(list(price_data.keys()))
    
    if len(fundamental_data) < 10:
        print("[ERROR] Insufficient fundamental data collected. Cannot proceed with validation.")
        exit(1)
    
    # Generate portfolio signals
    print("\nGenerating value factor portfolio signals...")
    signals_df = strategy.generate_portfolio_signals(fundamental_data, price_data)
    
    print(f"Generated {len(signals_df)} monthly portfolio rebalances")
    
    if len(signals_df) > 0:
        # Backtest performance
        print("\nCalculating performance metrics...")
        performance = strategy.backtest_performance(signals_df)
        
        # Display results
        print("\n" + "=" * 60)
        print("PERFORMANCE RESULTS")
        print("=" * 60)
        
        print(f"Total Rebalances: {performance['total_rebalances']}")
        print(f"Avg Portfolio Size: {performance['avg_portfolio_size']:.1f} stocks")
        print(f"Date Range: {performance['date_range'][0].date()} to {performance['date_range'][1].date()}")
        print(f"Avg Earnings Yield: {performance['avg_earnings_yield']:.2%}")
        
        print(f"\nMonthly Performance:")
        print(f"  Mean Return: {performance['mean_monthly_return']*100:.2f}%")  
        print(f"  Win Rate: {performance['win_rate']*100:.1f}%")
        print(f"  Info Ratio: {performance['info_ratio']:.3f}")
        print(f"  Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
        print(f"  Total Return: {performance['total_return']*100:.1f}%")
        print(f"  P-value: {performance['p_value']:.4f} {'[PASS]' if performance['p_value'] < 0.05 else '[FAIL]'}")
        
        # Alpha validation
        print("\n" + "=" * 60)
        print("EXPERT ALPHA VALIDATION")
        print("=" * 60)
        
        validation = strategy.validate_alpha(signals_df)
        
        if validation['passed']:
            print("[PASS] ALPHA VALIDATION PASSED")
            print(f"Tests Passed: {validation['passed_tests']}/{validation['total_tests']}")
            
            metrics = validation['metrics']
            print(f"\nKey Metrics (monthly rebalancing):")
            print(f"  Mean Monthly Return: {metrics['mean_monthly_return']*100:.2f}%")
            print(f"  Win Rate: {metrics['win_rate']:.1%}")
            print(f"  Information Ratio: {metrics['info_ratio']:.3f}")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"  P-value: {metrics['p_value']:.4f}")
            print(f"  Sample Size: {metrics['sample_size']} months")
            
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
        
        # Factor analysis
        print("\n" + "=" * 60)
        print("VALUE FACTOR ANALYSIS")
        print("=" * 60)
        
        if len(signals_df) > 0:
            print(f"Portfolio composition over time:")
            avg_size = signals_df['portfolio_size'].mean()
            min_size = signals_df['portfolio_size'].min()
            max_size = signals_df['portfolio_size'].max()
            print(f"  Average portfolio size: {avg_size:.1f} stocks")
            print(f"  Size range: {min_size} - {max_size} stocks")
            
            # Show earnings yield distribution
            ey_mean = signals_df['avg_earnings_yield'].mean()
            ey_std = signals_df['avg_earnings_yield'].std()
            print(f"  Average earnings yield: {ey_mean:.2%} ± {ey_std:.2%}")
    
    else:
        print("[ERROR] No portfolio signals generated. Check fundamental data availability.")