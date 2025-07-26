# simple_bollinger_optimizer.py
import backtrader as bt
import pandas as pd
import os
import json
import numpy as np
from datetime import datetime

class SimpleBollingerOptimizer(bt.Strategy):
    params = (
        ('period', 20),
        ('devfactor', 2.0),
    )
    
    def __init__(self):
        self.bollinger = bt.indicators.BollingerBands(
            period=self.p.period, 
            devfactor=self.p.devfactor
        )
        
    def next(self):
        if not self.position:
            if self.data.close < self.bollinger.lines.bot:
                self.buy()
        else:
            if self.data.close > self.bollinger.lines.mid:
                self.close()

def test_parameter_combination(ticker, data_dir, period, devfactor):
    """Test single parameter combination"""
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(SimpleBollingerOptimizer, period=period, devfactor=devfactor)
    
    # Load data
    data_path = os.path.join(data_dir, f'{ticker}.csv')
    if not os.path.exists(data_path):
        return None
    
    df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed, name=ticker)
    
    # Set up broker
    initial_cash = 10000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    results = cerebro.run()
    
    if not results:
        return None
    
    result = results[0]
    final_value = cerebro.broker.getvalue()
    
    # Extract metrics
    sharpe = result.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    if sharpe is None or np.isnan(sharpe):
        sharpe = 0
    
    trades = result.analyzers.trades.get_analysis()
    total_trades = trades.get('total', {}).get('total', 0)
    winning_trades = trades.get('won', {}).get('total', 0)
    
    return {
        'ticker': ticker,
        'period': period,
        'devfactor': devfactor,
        'final_value': final_value,
        'total_return_pct': (final_value - initial_cash) / initial_cash * 100,
        'sharpe_ratio': sharpe,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'win_rate_pct': (winning_trades / max(total_trades, 1)) * 100
    }

def run_bollinger_grid_search():
    """Run parameter grid search for Bollinger strategy"""
    
    UNIVERSE = ['CRWD', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/sprint_2'
    
    # Parameter ranges
    periods = [10, 15, 20, 25, 30]
    devfactors = [1.5, 2.0, 2.5, 3.0]
    
    print("=== Bollinger Parameter Grid Search ===")
    print(f"Testing {len(periods)} periods x {len(devfactors)} deviations = {len(periods) * len(devfactors)} combinations")
    print(f"Across {len(UNIVERSE)} stocks = {len(periods) * len(devfactors) * len(UNIVERSE)} total tests")
    
    all_results = []
    
    total_tests = len(periods) * len(devfactors) * len(UNIVERSE)
    completed_tests = 0
    
    for period in periods:
        for devfactor in devfactors:
            print(f"\nTesting Period={period}, Deviation={devfactor}")
            
            for ticker in UNIVERSE:
                result = test_parameter_combination(ticker, DATA_DIR, period, devfactor)
                if result:
                    all_results.append(result)
                
                completed_tests += 1
                if completed_tests % 10 == 0:
                    print(f"Progress: {completed_tests}/{total_tests} tests completed")
    
    # Analyze results
    if all_results:
        df = pd.DataFrame(all_results)
        
        # Best configurations overall
        best_overall = df.nlargest(10, 'total_return_pct')
        best_by_sharpe = df.nlargest(10, 'sharpe_ratio')
        best_by_win_rate = df.nlargest(10, 'win_rate_pct')
        
        # Parameter analysis
        param_analysis = {}
        
        # Average performance by period
        period_performance = df.groupby('period')[['total_return_pct', 'win_rate_pct', 'sharpe_ratio']].mean()
        param_analysis['by_period'] = period_performance.to_dict('index')
        
        # Average performance by deviation factor
        devfactor_performance = df.groupby('devfactor')[['total_return_pct', 'win_rate_pct', 'sharpe_ratio']].mean()
        param_analysis['by_devfactor'] = devfactor_performance.to_dict('index')
        
        # Best parameter combination across all stocks
        param_combo_performance = df.groupby(['period', 'devfactor'])[['total_return_pct', 'win_rate_pct', 'sharpe_ratio']].mean()
        param_combo_performance = param_combo_performance.reset_index()
        best_combo = param_combo_performance.loc[param_combo_performance['total_return_pct'].idxmax()]
        
        analysis = {
            'total_tests': len(all_results),
            'best_overall_configs': best_overall.to_dict('records'),
            'best_by_sharpe': best_by_sharpe.to_dict('records'),
            'best_by_win_rate': best_by_win_rate.to_dict('records'),
            'parameter_analysis': param_analysis,
            'optimal_parameters': {
                'period': int(best_combo['period']),
                'devfactor': float(best_combo['devfactor']),
                'expected_return': float(best_combo['total_return_pct']),
                'expected_win_rate': float(best_combo['win_rate_pct'])
            }
        }
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(RESULTS_DIR, f'bollinger_grid_search_{timestamp}.json')
        
        with open(results_file, 'w') as f:
            json.dump({
                'all_results': all_results,
                'analysis': analysis,
                'test_date': timestamp
            }, f, indent=2, default=str)
        
        print(f"\nBollinger optimization complete!")
        print(f"Results saved to: {results_file}")
        print(f"Optimal parameters: Period={analysis['optimal_parameters']['period']}, DevFactor={analysis['optimal_parameters']['devfactor']}")
        print(f"Expected performance: {analysis['optimal_parameters']['expected_return']:.1f}% return, {analysis['optimal_parameters']['expected_win_rate']:.1f}% win rate")
        
        return results_file
    
    return None

if __name__ == '__main__':
    run_bollinger_grid_search()