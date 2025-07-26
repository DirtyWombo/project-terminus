"""
Golden Cross Strategy - Full Robustness Testing
Integrates with existing Operation Badger testing framework

Tests performed:
1. Transaction Cost Analysis (TCA)
2. Parameter Sensitivity Analysis
3. Regime Analysis
4. Holdout Validation
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from golden_cross_strategy import GoldenCrossStrategy, get_small_midcap_universe, collect_price_data

# Import existing robustness testing modules
import subprocess
import sys
import os

class GoldenCrossRobustnessTester:
    """
    Comprehensive robustness testing for Golden Cross strategy
    Uses existing Operation Badger testing infrastructure
    """
    
    def __init__(self):
        self.strategy = GoldenCrossStrategy(short_window=50, long_window=200, trend_filter=True)
        self.results = {}
        
    def generate_trade_history(self, signals_df, initial_capital=100000):
        """
        Convert signals to trade history format for robustness testing
        """
        trades = []
        
        for i, signal in signals_df.iterrows():
            # Simulate trade execution
            trade = {
                'timestamp': signal['date'].strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': signal['symbol'],
                'side': 'buy',
                'quantity': int(initial_capital * 0.05 / signal['price']),  # 5% position size
                'price': signal['price'],
                'commission': 0,  # Will be calculated by TCA
                'slippage': 0,    # Will be calculated by TCA
                'signal_type': signal['signal_type'],
                'ma_50': signal['ma_50'],
                'ma_200': signal['ma_200']
            }
            trades.append(trade)
            
            # Add corresponding sell trade (5-day holding period)
            sell_date = signal['date'] + pd.Timedelta(days=5)
            sell_price = signal['price'] * (1 + signal['forward_5d'])
            
            sell_trade = {
                'timestamp': sell_date.strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': signal['symbol'],
                'side': 'sell',
                'quantity': trade['quantity'],
                'price': sell_price,
                'commission': 0,
                'slippage': 0,
                'signal_type': 'golden_cross_exit',
                'ma_50': signal['ma_50'],
                'ma_200': signal['ma_200']
            }
            trades.append(sell_trade)
        
        return pd.DataFrame(trades)
    
    def run_transaction_cost_analysis(self, signals_df):
        """
        Run TCA using existing infrastructure
        """
        print("Running Transaction Cost Analysis...")
        
        # Generate trade history
        trade_history = self.generate_trade_history(signals_df)
        
        # Save trade history for TCA
        trade_history.to_csv('golden_cross_trades.csv', index=False)
        
        # Calculate original performance metrics
        returns_5d = signals_df['forward_5d'].dropna()
        original_sharpe = (returns_5d.mean() / returns_5d.std()) * np.sqrt(252/5) if returns_5d.std() > 0 else 0
        original_win_rate = (returns_5d > 0).mean()
        original_mean_return = returns_5d.mean()
        
        # Simulate TCA impact (35 basis points per trade as per existing framework)
        cost_per_trade = 0.0035  # 35 basis points
        net_returns = returns_5d - (2 * cost_per_trade)  # Buy + sell costs
        
        net_sharpe = (net_returns.mean() / net_returns.std()) * np.sqrt(252/5) if net_returns.std() > 0 else 0
        net_win_rate = (net_returns > 0).mean()
        net_mean_return = net_returns.mean()
        
        tca_results = {
            'strategy': 'Golden Cross',
            'test_date': datetime.now().isoformat(),
            'original_performance': {
                'sharpe_ratio': float(original_sharpe),
                'win_rate': float(original_win_rate),
                'mean_return': float(original_mean_return),
                'sample_size': len(returns_5d)
            },
            'net_performance': {
                'sharpe_ratio': float(net_sharpe),
                'win_rate': float(net_win_rate),
                'mean_return': float(net_mean_return)
            },
            'cost_impact': {
                'cost_per_trade_bps': 35.0,
                'sharpe_degradation': float((original_sharpe - net_sharpe) / original_sharpe * 100) if original_sharpe != 0 else 0,
                'performance_impact': 'PASS' if net_sharpe > 1.0 else 'FAIL'
            }
        }
        
        # Save results
        with open('golden_cross_tca_results.json', 'w') as f:
            json.dump(tca_results, f, indent=2)
        
        return tca_results
    
    def run_parameter_sensitivity_analysis(self, price_data):
        """
        Test different parameter combinations
        """
        print("Running Parameter Sensitivity Analysis...")
        
        parameter_sets = [
            {'short': 20, 'long': 50, 'trend_filter': True},
            {'short': 30, 'long': 100, 'trend_filter': True},
            {'short': 50, 'long': 200, 'trend_filter': True},  # Original
            {'short': 100, 'long': 200, 'trend_filter': True},
            {'short': 50, 'long': 200, 'trend_filter': False},  # No trend filter
        ]
        
        sensitivity_results = {}
        
        for i, params in enumerate(parameter_sets):
            print(f"Testing parameter set {i+1}/5: MA({params['short']}/{params['long']}) Trend Filter: {params['trend_filter']}")
            
            # Create strategy with different parameters
            test_strategy = GoldenCrossStrategy(
                short_window=params['short'],
                long_window=params['long'],
                trend_filter=params['trend_filter']
            )
            
            # Generate signals
            signals = test_strategy.calculate_signals(price_data)
            
            if len(signals) > 10:  # Need minimum signals
                returns_5d = signals['forward_5d'].dropna()
                
                if len(returns_5d) > 0:
                    sharpe = (returns_5d.mean() / returns_5d.std()) * np.sqrt(252/5) if returns_5d.std() > 0 else 0
                    win_rate = (returns_5d > 0).mean()
                    mean_return = returns_5d.mean()
                    
                    sensitivity_results[f"params_{i+1}"] = {
                        'parameters': params,
                        'signals_count': len(signals),
                        'sharpe_ratio': float(sharpe),
                        'win_rate': float(win_rate),
                        'mean_return': float(mean_return),
                        'performance': 'STABLE' if sharpe > 1.0 else 'UNSTABLE'
                    }
        
        # Analyze stability
        sharpe_values = [r['sharpe_ratio'] for r in sensitivity_results.values()]
        stability_score = 1 - (np.std(sharpe_values) / np.mean(sharpe_values)) if np.mean(sharpe_values) > 0 else 0
        
        parameter_results = {
            'strategy': 'Golden Cross',
            'test_date': datetime.now().isoformat(),
            'parameter_combinations': sensitivity_results,
            'stability_analysis': {
                'stability_score': float(stability_score),
                'stable_parameters': sum(1 for r in sensitivity_results.values() if r['performance'] == 'STABLE'),
                'total_tested': len(sensitivity_results),
                'verdict': 'PASS' if stability_score > 0.7 else 'FAIL'
            }
        }
        
        # Save results
        with open('golden_cross_parameter_sensitivity.json', 'w') as f:
            json.dump(parameter_results, f, indent=2)
        
        return parameter_results
    
    def run_regime_analysis(self, signals_df, price_data):
        """
        Test performance across different market regimes
        """
        print("Running Regime Analysis...")
        
        # Define market regimes based on VIX levels (simplified)
        # In production, would use actual VIX data
        signals_df = signals_df.copy()
        signals_df['regime'] = 'NORMAL'  # Default
        
        # Simulate regime classification based on volatility
        for symbol in signals_df['symbol'].unique():
            symbol_data = price_data.get(symbol)
            if symbol_data is not None:
                for idx, row in signals_df[signals_df['symbol'] == symbol].iterrows():
                    date = row['date']
                    if date in symbol_data.index:
                        # Calculate rolling volatility
                        recent_vol = symbol_data.loc[:date, 'daily_return'].tail(20).std()
                        
                        if recent_vol > 0.05:
                            signals_df.loc[idx, 'regime'] = 'HIGH_VOL'
                        elif recent_vol < 0.02:
                            signals_df.loc[idx, 'regime'] = 'LOW_VOL'
        
        regime_results = {}
        
        for regime in signals_df['regime'].unique():
            regime_signals = signals_df[signals_df['regime'] == regime]
            
            if len(regime_signals) > 5:  # Minimum signals per regime
                returns_5d = regime_signals['forward_5d'].dropna()
                
                if len(returns_5d) > 0:
                    sharpe = (returns_5d.mean() / returns_5d.std()) * np.sqrt(252/5) if returns_5d.std() > 0 else 0
                    win_rate = (returns_5d > 0).mean()
                    mean_return = returns_5d.mean()
                    
                    regime_results[regime] = {
                        'signals_count': len(regime_signals),
                        'sharpe_ratio': float(sharpe),
                        'win_rate': float(win_rate),
                        'mean_return': float(mean_return),
                        'performance': 'ROBUST' if sharpe > 0.5 else 'WEAK'
                    }
        
        # Overall regime consistency
        regime_sharpes = [r['sharpe_ratio'] for r in regime_results.values()]
        consistency_score = 1 - (np.std(regime_sharpes) / np.mean(regime_sharpes)) if np.mean(regime_sharpes) > 0 else 0
        
        regime_analysis = {
            'strategy': 'Golden Cross',
            'test_date': datetime.now().isoformat(),
            'regime_performance': regime_results,
            'consistency_analysis': {
                'consistency_score': float(consistency_score),
                'robust_regimes': sum(1 for r in regime_results.values() if r['performance'] == 'ROBUST'),
                'total_regimes': len(regime_results),
                'verdict': 'PASS' if consistency_score > 0.6 else 'FAIL'
            }
        }
        
        # Save results
        with open('golden_cross_regime_analysis.json', 'w') as f:
            json.dump(regime_analysis, f, indent=2)
        
        return regime_analysis
    
    def run_holdout_validation(self, price_data):
        """
        Test on holdout period (most recent 6 months)
        """
        print("Running Holdout Validation...")
        
        # Split data: Training (older) vs Holdout (recent 6 months)
        holdout_start = pd.Timestamp.now().tz_localize(None) - pd.Timedelta(days=180)
        
        training_data = {}
        holdout_data = {}
        
        for symbol, df in price_data.items():
            # Ensure datetime index is timezone-naive for comparison
            df_copy = df.copy()
            if df_copy.index.tz is not None:
                df_copy.index = df_copy.index.tz_localize(None)
            
            split_date = holdout_start
            
            training_data[symbol] = df_copy[df_copy.index < split_date].copy()
            holdout_data[symbol] = df_copy[df_copy.index >= split_date].copy()
        
        # Generate signals on training data (already done in main validation)
        # Generate signals on holdout data
        holdout_signals = self.strategy.calculate_signals(holdout_data)
        
        if len(holdout_signals) > 10:  # Need minimum signals
            holdout_returns = holdout_signals['forward_5d'].dropna()
            
            if len(holdout_returns) > 0:
                holdout_sharpe = (holdout_returns.mean() / holdout_returns.std()) * np.sqrt(252/5) if holdout_returns.std() > 0 else 0
                holdout_win_rate = (holdout_returns > 0).mean()
                holdout_mean_return = holdout_returns.mean()
                
                # Compare to training performance (approximate from earlier validation)
                training_sharpe = 2.54  # From alpha validation
                training_win_rate = 0.619
                training_mean_return = 0.026
                
                degradation = {
                    'sharpe': (training_sharpe - holdout_sharpe) / training_sharpe if training_sharpe != 0 else 0,
                    'win_rate': (training_win_rate - holdout_win_rate) / training_win_rate if training_win_rate != 0 else 0,
                    'mean_return': (training_mean_return - holdout_mean_return) / abs(training_mean_return) if training_mean_return != 0 else 0
                }
                
                holdout_results = {
                    'strategy': 'Golden Cross',
                    'test_date': datetime.now().isoformat(),
                    'training_performance': {
                        'sharpe_ratio': training_sharpe,
                        'win_rate': training_win_rate,
                        'mean_return': training_mean_return
                    },
                    'holdout_performance': {
                        'sharpe_ratio': float(holdout_sharpe),
                        'win_rate': float(holdout_win_rate),
                        'mean_return': float(holdout_mean_return),
                        'sample_size': len(holdout_returns)
                    },
                    'degradation_analysis': {
                        'sharpe_degradation': float(degradation['sharpe']),
                        'win_rate_degradation': float(degradation['win_rate']),
                        'return_degradation': float(degradation['mean_return']),
                        'verdict': 'PASS' if holdout_sharpe > 0.5 and degradation['sharpe'] < 0.5 else 'FAIL'
                    }
                }
            else:
                holdout_results = {
                    'verdict': 'FAIL',
                    'reason': 'No valid holdout returns'
                }
        else:
            holdout_results = {
                'verdict': 'FAIL', 
                'reason': f'Insufficient holdout signals: {len(holdout_signals)}'
            }
        
        # Save results
        with open('golden_cross_holdout_validation.json', 'w') as f:
            json.dump(holdout_results, f, indent=2)
        
        return holdout_results
    
    def run_full_robustness_suite(self):
        """
        Run all robustness tests and generate final report
        """
        print("=" * 60)
        print("GOLDEN CROSS STRATEGY - FULL ROBUSTNESS TESTING")
        print("=" * 60)
        
        # Collect data
        universe = get_small_midcap_universe()
        price_data = collect_price_data(universe, period="3y")
        
        # Generate base signals
        signals_df = self.strategy.calculate_signals(price_data)
        print(f"Base signals generated: {len(signals_df)}")
        
        # Run all tests
        results = {}
        
        # 1. Transaction Cost Analysis
        results['tca'] = self.run_transaction_cost_analysis(signals_df)
        
        # 2. Parameter Sensitivity
        results['parameter_sensitivity'] = self.run_parameter_sensitivity_analysis(price_data)
        
        # 3. Regime Analysis
        results['regime_analysis'] = self.run_regime_analysis(signals_df, price_data)
        
        # 4. Holdout Validation
        results['holdout_validation'] = self.run_holdout_validation(price_data)
        
        # Generate final summary
        self.generate_final_report(results)
        
        return results
    
    def generate_final_report(self, results):
        """
        Generate comprehensive robustness testing report
        """
        print("\n" + "=" * 60)
        print("ROBUSTNESS TESTING FINAL REPORT")
        print("=" * 60)
        
        # Test results summary
        test_results = {
            'TCA': results['tca']['cost_impact'].get('performance_impact', 'FAIL'),
            'Parameter Sensitivity': results['parameter_sensitivity']['stability_analysis']['verdict'],
            'Regime Analysis': results['regime_analysis']['consistency_analysis']['verdict'],
            'Holdout Validation': results['holdout_validation'].get('degradation_analysis', {}).get('verdict', 'FAIL')
        }
        
        passed_tests = sum(1 for v in test_results.values() if v == 'PASS')
        total_tests = len(test_results)
        
        print(f"TESTS PASSED: {passed_tests}/{total_tests}")
        print("\nDetailed Results:")
        
        for test_name, result in test_results.items():
            status = "[PASS]" if result == 'PASS' else "[FAIL]"
            print(f"  {test_name}: {status}")
        
        # Final verdict
        if passed_tests >= 3:  # Need at least 3/4 tests passing
            print(f"\n[PASS] GOLDEN CROSS STRATEGY VALIDATED FOR PRODUCTION")
            print(f"Strategy meets {passed_tests}/4 robustness requirements")
            recommendation = "PROCEED with paper trading and portfolio integration"
        else:
            print(f"\n[FAIL] GOLDEN CROSS STRATEGY REQUIRES REFINEMENT")
            print(f"Strategy meets only {passed_tests}/4 robustness requirements")
            recommendation = "REFINE strategy parameters or consider alternative approaches"
        
        # Save comprehensive report
        final_report = {
            'strategy': 'Golden Cross (50/200 MA)',
            'test_date': datetime.now().isoformat(),
            'test_summary': test_results,
            'tests_passed': passed_tests,
            'total_tests': total_tests,
            'final_verdict': 'PASS' if passed_tests >= 3 else 'FAIL',
            'recommendation': recommendation,
            'detailed_results': results
        }
        
        with open('golden_cross_robustness_final_report.json', 'w') as f:
            json.dump(final_report, f, indent=2)
        
        print(f"\nRECOMMENDation: {recommendation}")
        print(f"\nFull results saved to: golden_cross_robustness_final_report.json")

if __name__ == "__main__":
    tester = GoldenCrossRobustnessTester()
    results = tester.run_full_robustness_suite()