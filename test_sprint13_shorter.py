#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Sprint 13 with a shorter time period to validate weekly rebalancing approach
"""

import sys
import os
import backtrader as bt
import pandas as pd
import json
from datetime import datetime

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from features.qvm_factors_pit import PITDataManager, calculate_quality_factor_pit, calculate_value_factor_pit, calculate_momentum_factor_pit

# Import the strategy class
from backtests.sprint_13.composite_qvm_backtest_sp500_weekly import CompositeQVMSP500WeeklyStrategy, load_full_sp500_universe

def run_sprint13_short_test():
    """
    Run Sprint 13 test with shorter time period (2 years) to validate approach
    """
    print("="*80)
    print("SPRINT 13 SHORT TEST - 2 Year Validation")
    print("="*80)
    print("Testing weekly rebalancing approach with:")
    print("- Full 216-stock S&P 500 universe")
    print("- Weekly rebalancing")
    print("- Shorter period: 2022-2023 (2 years)")
    print("="*80)
    
    # Load full S&P 500 universe
    universe = load_full_sp500_universe()
    if not universe:
        print("ERROR: Could not load S&P 500 universe")
        return None
    
    print(f"Universe loaded: {len(universe)} S&P 500 stocks")
    
    # API key
    api_key = "zVj71CrDyYzfcyxrWkQ4"
    
    # Create results directory
    results_dir = 'results/sprint_13'
    os.makedirs(results_dir, exist_ok=True)
    
    # Extend bt.DataBase
    bt.feeds.PandasData.get_df = lambda self: self.p.dataname.loc[self.p.fromdate:self.p.todate]
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(CompositeQVMSP500WeeklyStrategy, universe=universe, api_key=api_key)

    # Load price data for all stocks with date filtering
    price_data_dir = 'data/sprint_12'
    loaded_count = 0
    
    print("Loading price data for 2022-2023...")
    for ticker in universe:
        data_path = os.path.join(price_data_dir, f'{ticker}.csv')
        if os.path.exists(data_path):
            try:
                # Load and filter to 2022-2023
                df = pd.read_csv(data_path, index_col=0, parse_dates=True, skiprows=[1,2])
                df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                
                # Filter to 2022-2023 only
                df = df.loc['2022-01-01':'2023-12-31']
                
                if not df.empty:
                    cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
                    loaded_count += 1
                    if loaded_count % 50 == 0:
                        print(f"  Loaded {loaded_count} stocks...")
            except Exception as e:
                if loaded_count < 10:  # Only show first few errors
                    print(f"ERROR loading {ticker}: {str(e)[:100]}")

    print(f"SUCCESS: Loaded price data for {loaded_count}/{len(universe)} stocks")

    # Set initial capital and commission
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print(f'\nStarting 2-year Sprint 13 test with ${cerebro.broker.getvalue():,.2f}...')
    initial_value = cerebro.broker.getvalue()
    
    # Run backtest
    start_time = datetime.now()
    results = cerebro.run()
    end_time = datetime.now()
    
    strat = results[0]
    final_value = cerebro.broker.getvalue()

    # Extract results
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    returns_analysis = strat.analyzers.returns.get_analysis()
    trades_analysis = strat.analyzers.trades.get_analysis()
    
    sharpe_ratio = sharpe_analysis.get('sharperatio', 0) or 0
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0) or 0
    ann_return = returns_analysis.get('rnorm100', 0) or 0
    
    # Trade statistics
    total_trades = trades_analysis.get('total', {}).get('total', 0) or 0
    winning_trades = trades_analysis.get('won', {}).get('total', 0) or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_return = (final_value - initial_value) / initial_value * 100

    # Display results
    print('\n' + '='*80)
    print('SPRINT 13 SHORT TEST RESULTS (2022-2023)')
    print('='*80)
    print(f'Test Universe: {len(universe)} S&P 500 stocks')
    print(f'Data Coverage: {loaded_count} stocks with price data')
    print(f'Backtest Duration: {end_time - start_time}')
    print(f'Period: 2022-2023 (2 years)')
    print(f'Initial Portfolio Value: ${initial_value:,.2f}')
    print(f'Final Portfolio Value: ${final_value:,.2f}')
    print(f'Total Return: {total_return:.2f}%')
    print(f'Annualized Return: {ann_return:.2f}%')
    print(f'Sharpe Ratio: {sharpe_ratio:.2f}')
    print(f'Max Drawdown: {max_drawdown:.2f}%')
    print(f'Total Trades: {total_trades}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'Rebalances: {strat.rebalance_count}')
    
    # Extrapolate to 6-year period
    weekly_rebalances_2yr = strat.rebalance_count
    estimated_6yr_rebalances = weekly_rebalances_2yr * 3
    estimated_6yr_trades = total_trades * 3
    
    print('\n' + '='*50)
    print('EXTRAPOLATION TO 6-YEAR PERIOD')
    print('='*50)
    print(f'2-year rebalances: {weekly_rebalances_2yr}')
    print(f'2-year trades: {total_trades}')
    print(f'Estimated 6-year rebalances: ~{estimated_6yr_rebalances}')
    print(f'Estimated 6-year trades: ~{estimated_6yr_trades}')
    
    # Check if weekly approach addresses Sprint 12 issues
    sprint12_trades = 24  # From Sprint 12 results
    trade_improvement = (estimated_6yr_trades / sprint12_trades) if sprint12_trades > 0 else 0
    
    print(f'\nImprovement vs Sprint 12:')
    print(f'Sprint 12 trades (6yr): {sprint12_trades}')
    print(f'Estimated Sprint 13 trades: {estimated_6yr_trades}')
    print(f'Trade count improvement: {trade_improvement:.1f}x')
    
    # Quick success criteria check
    print('\n' + '='*50)
    print('PROJECTED SUCCESS CRITERIA (if 6-year)')
    print('='*50)
    
    trades_target_met = estimated_6yr_trades > 50
    print(f"Total Trades > 50: {estimated_6yr_trades} {'LIKELY PASS' if trades_target_met else 'LIKELY FAIL'}")
    
    # Save results
    results_data = {
        'test': 'Sprint 13 Short Test - 2 Year Validation',
        'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'period': '2022-2023 (2 years)',
        'universe_size': len(universe),
        'data_coverage': loaded_count,
        'total_return_pct': total_return,
        'annualized_return_pct': ann_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown_pct': max_drawdown,
        'total_trades': total_trades,
        'win_rate_pct': win_rate,
        'rebalances': strat.rebalance_count,
        'backtest_duration_seconds': (end_time - start_time).total_seconds(),
        'extrapolated_6yr_trades': estimated_6yr_trades,
        'extrapolated_6yr_rebalances': estimated_6yr_rebalances,
        'vs_sprint12_trade_improvement': trade_improvement
    }
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f'sprint13_short_test_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\nRESULTS: Short test results saved to: {results_file}")
    return results_data

if __name__ == "__main__":
    run_sprint13_short_test()