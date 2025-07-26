"""
Strategy Batch Tester - Unified testing framework
Runs multiple strategies through alpha validation pipeline

Integrates with existing robustness testing infrastructure
Enables systematic comparison across strategy universe
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from strategy_registry import StrategyRegistry
from golden_cross_strategy import get_small_midcap_universe, collect_price_data
import warnings
warnings.filterwarnings('ignore')

class StrategyBatchTester:
    """
    Batch testing framework for systematic strategy validation
    
    Features:
    - Alpha validation for all implemented strategies
    - Performance comparison and ranking
    - Correlation analysis between strategies
    - Automated report generation
    """
    
    def __init__(self, universe_func=None, data_period="2y"):
        self.registry = StrategyRegistry()
        self.universe_func = universe_func or get_small_midcap_universe
        self.data_period = data_period
        self.results = {}
        
    def collect_market_data(self):
        """Collect market data for testing universe"""
        print("Collecting market data for strategy testing...")
        universe = self.universe_func()
        price_data = collect_price_data(universe, period=self.data_period)
        
        # Add market indices for VIX strategy
        indices = ['SPY', 'QQQ', 'IWM']  # S&P 500, NASDAQ, Russell 2000
        for index in indices:
            if index not in price_data:
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(index)
                    hist = ticker.history(period=self.data_period)
                    if len(hist) > 100:
                        hist['daily_return'] = hist['Close'].pct_change()
                        price_data[index] = hist
                        print(f"[OK] Added index: {index}")
                except Exception as e:
                    print(f"[ERROR] Failed to add {index}: {e}")
        
        return price_data
    
    def test_single_strategy(self, strategy_id, price_data):
        """Test a single strategy and return results"""
        try:
            strategy_info = self.registry.get_strategy(strategy_id)
            
            if not strategy_info or strategy_info['status'] != 'implemented':
                return None
            
            print(f"\nTesting {strategy_id}: {strategy_info['name']}")
            
            # Create strategy instance
            strategy = self.registry.create_strategy_instance(strategy_id)
            
            # Generate signals
            signals_df = strategy.calculate_signals(price_data)
            
            if len(signals_df) == 0:
                return {
                    'strategy_id': strategy_id,
                    'name': strategy_info['name'],
                    'category': strategy_info['category'],
                    'status': 'no_signals',
                    'signals_count': 0,
                    'error': 'No signals generated'
                }
            
            # Calculate basic performance metrics
            results = self.calculate_performance_metrics(signals_df, strategy_info)
            
            print(f"  Signals: {len(signals_df)}")
            print(f"  Performance: {results.get('summary', 'N/A')}")
            
            return results
            
        except Exception as e:
            print(f"  ERROR testing {strategy_id}: {str(e)}")
            return {
                'strategy_id': strategy_id,
                'name': strategy_info.get('name', 'Unknown'),
                'category': strategy_info.get('category', 'Unknown'),
                'status': 'error',
                'error': str(e)
            }
    
    def calculate_performance_metrics(self, signals_df, strategy_info, primary_holding='5d'):
        """Calculate standardized performance metrics for any strategy"""
        
        # Determine appropriate holding period based on strategy type
        if strategy_info['category'] == 'factor_based':
            primary_holding = 'forward_1m'  # Monthly for factor strategies
        elif 'forward_5d' in signals_df.columns:
            primary_holding = 'forward_5d'
        elif 'forward_3d' in signals_df.columns:
            primary_holding = 'forward_3d'
        else:
            primary_holding = 'forward_1d'
        
        # Handle different column naming conventions
        if primary_holding not in signals_df.columns:
            if primary_holding == 'forward_5d' and '5d' in str(signals_df.columns):
                primary_holding = [col for col in signals_df.columns if '5d' in col][0]
            elif primary_holding == 'forward_1m' and 'forward_1m' in signals_df.columns:
                primary_holding = 'forward_1m'
            else:
                # Default to first forward return column found
                forward_cols = [col for col in signals_df.columns if 'forward' in col.lower()]
                if forward_cols:
                    primary_holding = forward_cols[0]
                else:
                    return self.create_error_result(strategy_info, "No forward return columns found")
        
        try:
            returns = signals_df[primary_holding].dropna()
            
            if len(returns) == 0:
                return self.create_error_result(strategy_info, "No valid returns")
            
            # Basic statistics
            mean_return = returns.mean()
            std_return = returns.std()
            win_rate = (returns > 0).mean()
            
            # Risk metrics
            if std_return > 0:
                info_ratio = mean_return / std_return
                
                # Annualize based on holding period
                if '1d' in primary_holding:
                    sharpe_ratio = info_ratio * np.sqrt(252)
                elif '3d' in primary_holding:
                    sharpe_ratio = info_ratio * np.sqrt(252/3)
                elif '5d' in primary_holding:
                    sharpe_ratio = info_ratio * np.sqrt(252/5)
                elif '10d' in primary_holding:
                    sharpe_ratio = info_ratio * np.sqrt(252/10)
                elif '1m' in primary_holding:
                    sharpe_ratio = info_ratio * np.sqrt(12)
                else:
                    sharpe_ratio = info_ratio  # Unknown period
            else:
                info_ratio = 0
                sharpe_ratio = 0
            
            # Statistical significance
            from scipy import stats
            t_stat, p_value = stats.ttest_1samp(returns, 0)
            
            # Alpha validation criteria (simplified)
            criteria_met = 0
            if p_value < 0.05:
                criteria_met += 1
            if info_ratio > 0.5:
                criteria_met += 1
            if win_rate > 0.52:
                criteria_met += 1
            if sharpe_ratio > 1.0:
                criteria_met += 1
            if len(returns) >= 30:
                criteria_met += 1
            
            alpha_passed = criteria_met >= 4
            
            # Create summary
            summary = f"Sharpe {sharpe_ratio:.2f}, Win {win_rate:.1%}, Signals {len(returns)}"
            
            return {
                'strategy_id': strategy_info.get('id', 'unknown'),
                'name': strategy_info['name'],
                'category': strategy_info['category'],
                'priority': strategy_info['priority'],
                'status': 'tested',
                'signals_count': len(signals_df),
                'valid_returns': len(returns),
                'holding_period': primary_holding,
                'mean_return': float(mean_return),
                'std_return': float(std_return),
                'win_rate': float(win_rate),
                'info_ratio': float(info_ratio),
                'sharpe_ratio': float(sharpe_ratio),
                'p_value': float(p_value),
                'criteria_met': criteria_met,
                'alpha_passed': alpha_passed,
                'summary': summary,
                'test_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            return self.create_error_result(strategy_info, f"Calculation error: {str(e)}")
    
    def create_error_result(self, strategy_info, error_msg):
        """Create standardized error result"""
        return {
            'strategy_id': strategy_info.get('id', 'unknown'),
            'name': strategy_info['name'],
            'category': strategy_info['category'],
            'status': 'error',
            'error': error_msg
        }
    
    def run_batch_test(self, strategy_ids=None):
        """Run batch test on specified strategies or all implemented ones"""
        
        if strategy_ids is None:
            # Test all implemented strategies
            implemented = self.registry.get_implemented_strategies()
            strategy_ids = list(implemented.keys())
        
        print("=" * 60)
        print("STRATEGY BATCH TESTING - ALPHA VALIDATION")
        print("=" * 60)
        print(f"Testing {len(strategy_ids)} strategies")
        
        # Collect market data once
        price_data = self.collect_market_data()
        
        if len(price_data) < 10:
            print("ERROR: Insufficient market data collected")
            return None
        
        print(f"Market data collected: {len(price_data)} symbols")
        
        # Test each strategy
        results = []
        
        for i, strategy_id in enumerate(strategy_ids):
            print(f"\n[{i+1}/{len(strategy_ids)}] Testing {strategy_id}...")
            
            result = self.test_single_strategy(strategy_id, price_data)
            
            if result:
                results.append(result)
        
        self.results = results
        return results
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        if not self.results:
            print("No results available. Run batch test first.")
            return
        
        print("\n" + "=" * 60)
        print("BATCH TESTING SUMMARY REPORT")
        print("=" * 60)
        
        # Overall statistics
        total_tested = len(self.results)
        successful_tests = len([r for r in self.results if r['status'] == 'tested'])
        alpha_passed = len([r for r in self.results if r.get('alpha_passed', False)])
        
        print(f"Total Strategies Tested: {total_tested}")
        print(f"Successful Tests: {successful_tests}")
        print(f"Alpha Validation Passed: {alpha_passed}")
        print(f"Alpha Pass Rate: {alpha_passed/successful_tests:.1%}" if successful_tests > 0 else "N/A")
        
        # Top performers
        successful_results = [r for r in self.results if r['status'] == 'tested']
        if successful_results:
            # Sort by Sharpe ratio
            by_sharpe = sorted(successful_results, key=lambda x: x.get('sharpe_ratio', -999), reverse=True)
            
            print(f"\nTop 5 Strategies by Sharpe Ratio:")
            for i, result in enumerate(by_sharpe[:5]):
                sharpe = result.get('sharpe_ratio', 0)
                win_rate = result.get('win_rate', 0)
                signals = result.get('signals_count', 0)
                status = "[PASS]" if result.get('alpha_passed', False) else "[FAIL]"
                print(f"  {i+1}. {result['name']}: Sharpe {sharpe:.2f}, Win {win_rate:.1%}, Signals {signals} {status}")
            
            # By category
            print(f"\nResults by Category:")
            by_category = {}
            for result in successful_results:
                cat = result['category']
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(result)
            
            for category, cat_results in by_category.items():
                passed = len([r for r in cat_results if r.get('alpha_passed', False)])
                avg_sharpe = np.mean([r.get('sharpe_ratio', 0) for r in cat_results])
                print(f"  {category}: {passed}/{len(cat_results)} passed, Avg Sharpe {avg_sharpe:.2f}")
        
        # Failed tests
        failed_results = [r for r in self.results if r['status'] != 'tested']
        if failed_results:
            print(f"\nFailed Tests ({len(failed_results)}):")
            for result in failed_results:
                print(f"  {result['name']}: {result.get('error', 'Unknown error')}")
    
    def save_results(self, filename=None):
        """Save results to JSON file"""
        if not self.results:
            print("No results to save")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"strategy_batch_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'test_metadata': {
                    'test_date': datetime.now().isoformat(),
                    'data_period': self.data_period,
                    'total_strategies': len(self.results)
                },
                'results': self.results
            }, f, indent=2)
        
        print(f"Results saved to: {filename}")
        return filename

if __name__ == "__main__":
    # Demo usage
    tester = StrategyBatchTester(data_period="2y")
    
    # Test specific strategies
    test_strategies = [
        'S02_golden_cross',
        'S03_triple_ma', 
        'S04_macd',
        'S07_bollinger_bounce',
        'S08_rsi'
    ]
    
    # Run batch test
    results = tester.run_batch_test(test_strategies)
    
    # Generate report
    tester.generate_summary_report()
    
    # Save results
    tester.save_results()