#!/usr/bin/env python3
"""
Sprint 7.2 Analysis Report Generator
Analyze RSI optimization results and prepare for Test B
"""

import json
import pandas as pd
from pathlib import Path

def load_latest_results():
    """Load the latest RSI optimization results"""
    results_dir = Path("results/sprint_7_rsi_optimization")
    latest_file = sorted(results_dir.glob("*.json"))[-1]
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    print(f"Loaded results from: {latest_file}")
    return data

def analyze_results(data):
    """Analyze optimization results and create summary"""
    
    print("\n" + "="*80)
    print("SPRINT 7.2 RSI OPTIMIZATION RESULTS ANALYSIS")
    print("="*80)
    
    # Extract key metrics
    universe = data['universe']
    param_grid = data['parameter_grid']
    total_combinations = param_grid['total_combinations']
    
    print(f"Universe: {len(universe)} stocks")
    print(f"Parameter combinations tested: {total_combinations}")
    print(f"RSI Periods: {param_grid['rsi_periods']}")
    print(f"Oversold Levels: {param_grid['oversold_levels']}")  
    print(f"Overbought Levels: {param_grid['overbought_levels']}")
    
    # Analyze individual stock results
    print(f"\n{'='*60}")
    print("INDIVIDUAL STOCK PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    
    stock_summary = []
    
    for ticker in universe:
        stock_data = data['individual_stock_results'][ticker]
        best_result = stock_data['best_result']
        
        # Get best parameters
        best_params = best_result['parameters']
        best_perf = best_result['performance']
        
        stock_summary.append({
            'ticker': ticker,
            'best_sharpe': best_perf['sharpe_ratio'],
            'best_return_pct': best_perf['total_return_pct'] * 100,
            'best_win_rate': best_perf['win_rate_pct'],
            'total_trades': best_perf['total_trades'],
            'max_drawdown': best_perf['max_drawdown_pct'] * 100,
            'rsi_period': best_params['rsi_period'],
            'oversold': best_params['oversold_level'],
            'overbought': best_params['overbought_level']
        })
        
        print(f"{ticker:4} | Sharpe: {best_perf['sharpe_ratio']:6.2f} | "
              f"Return: {best_perf['total_return_pct']*100:6.1f}% | "
              f"Win Rate: {best_perf['win_rate_pct']:4.1f}% | "
              f"Trades: {best_perf['total_trades']:2d} | "
              f"Params: {best_params['rsi_period']}-{best_params['oversold_level']}-{best_params['overbought_level']}")
    
    # Create DataFrame for analysis
    df = pd.DataFrame(stock_summary)
    
    print(f"\n{'='*60}")
    print("AGGREGATE ANALYSIS")
    print(f"{'='*60}")
    
    # Filter stocks with actual trades
    traded_stocks = df[df['total_trades'] > 0]
    
    print(f"Stocks generating trades: {len(traded_stocks)}/{len(df)}")
    
    if len(traded_stocks) > 0:
        print(f"Average Sharpe Ratio: {traded_stocks['best_sharpe'].mean():.2f}")
        print(f"Average Return: {traded_stocks['best_return_pct'].mean():.1f}%")
        print(f"Average Win Rate: {traded_stocks['best_win_rate'].mean():.1f}%")
        print(f"Average Trades per Stock: {traded_stocks['total_trades'].mean():.1f}")
        print(f"Average Max Drawdown: {traded_stocks['max_drawdown'].mean():.1f}%")
        
        # Parameter frequency analysis
        print(f"\nMOST COMMON OPTIMAL PARAMETERS:")
        print(f"RSI Period: {traded_stocks['rsi_period'].mode().iloc[0] if len(traded_stocks['rsi_period'].mode()) > 0 else 'N/A'}")
        print(f"Oversold Level: {traded_stocks['oversold'].mode().iloc[0] if len(traded_stocks['oversold'].mode()) > 0 else 'N/A'}")
        print(f"Overbought Level: {traded_stocks['overbought'].mode().iloc[0] if len(traded_stocks['overbought'].mode()) > 0 else 'N/A'}")
        
        # Sprint 7 success criteria check
        print(f"\n{'='*60}")
        print("SPRINT 7 SUCCESS CRITERIA ASSESSMENT")
        print(f"{'='*60}")
        
        avg_sharpe = traded_stocks['best_sharpe'].mean()
        avg_win_rate = traded_stocks['best_win_rate'].mean()
        avg_drawdown = traded_stocks['max_drawdown'].mean()
        
        print(f"[TARGET] Post-Cost Sharpe > 1.0")
        print(f"   Result: {avg_sharpe:.2f} {'PASS' if avg_sharpe > 1.0 else 'FAIL'}")
        
        print(f"[TARGET] Win Rate > 45%")
        print(f"   Result: {avg_win_rate:.1f}% {'PASS' if avg_win_rate > 45 else 'FAIL'}")
        
        print(f"[TARGET] Max Drawdown < 15%")
        print(f"   Result: {avg_drawdown:.1f}% {'PASS' if avg_drawdown < 15 else 'FAIL'}")
        
        criteria_met = sum([avg_sharpe > 1.0, avg_win_rate > 45, avg_drawdown < 15])
        print(f"\nOVERALL: {criteria_met}/3 criteria met")
        
        if criteria_met >= 2:
            print("MARGINAL - Strategy shows promise but needs refinement")
        elif criteria_met >= 1:
            print("POOR - Strategy requires significant improvement")
        else:
            print("FAILED - Strategy not viable in current form")
            
    else:
        print("NO TRADES GENERATED - Strategy parameters too restrictive")
    
    # Recommend best overall parameters for Test B
    if len(traded_stocks) > 0:
        best_stock = traded_stocks.loc[traded_stocks['best_sharpe'].idxmax()]
        
        print(f"\n{'='*60}")
        print("RECOMMENDATION FOR TEST B (EXIT STRATEGY OPTIMIZATION)")
        print(f"{'='*60}")
        
        print(f"Best performing stock: {best_stock['ticker']}")
        print(f"Recommended parameters for Test B:")
        print(f"  RSI Period: {int(best_stock['rsi_period'])}")
        print(f"  Oversold Level: {int(best_stock['oversold'])}")
        print(f"  Overbought Level: {int(best_stock['overbought'])}")
        print(f"  Performance: {best_stock['best_return_pct']:.1f}% return, {best_stock['best_sharpe']:.2f} Sharpe")
        
        return {
            'best_params': {
                'rsi_period': int(best_stock['rsi_period']),
                'oversold_level': int(best_stock['oversold']),
                'overbought_level': int(best_stock['overbought'])
            },
            'test_b_ready': True
        }
    else:
        print("\nCannot proceed to Test B - no viable parameters found")
        return {'test_b_ready': False}

def main():
    """Main analysis function"""
    try:
        results = load_latest_results()
        recommendation = analyze_results(results)
        
        # Save recommendation for Test B
        if recommendation['test_b_ready']:
            with open('sprint_7_test_b_params.json', 'w') as f:
                json.dump(recommendation['best_params'], f, indent=2)
            print(f"\nTest B parameters saved to sprint_7_test_b_params.json")
        
    except Exception as e:
        print(f"Error analyzing results: {e}")

if __name__ == "__main__":
    main()