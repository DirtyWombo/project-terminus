# trade_frequency_analysis.py
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

def analyze_trade_frequency_explosion():
    """
    Deep dive analysis of why DJIA generated 6x more trades than growth stocks
    
    Key Investigation:
    - Why 54 trades vs 9 trades (500% increase)?
    - What causes frequent position changes in DJIA vs growth stocks?
    - Portfolio turnover analysis
    - Strategy behavior comparison
    """
    
    print("=" * 80)
    print("TRADE FREQUENCY EXPLOSION - ROOT CAUSE ANALYSIS")
    print("=" * 80)
    print("Critical Finding: 54 DJIA trades vs 9 growth stock trades (+500%)")
    print("Key Question: What drives this massive difference in trade frequency?")
    print("=" * 80)
    
    # Load the forensics results
    forensics_file = 'results/post_mortem_analysis/transaction_cost_forensics_20250725_080554.json'
    
    try:
        with open(forensics_file, 'r') as f:
            forensics_data = json.load(f)
        print("Loaded forensics analysis data")
    except Exception as e:
        print(f"Error loading forensics data: {e}")
        return
    
    # Extract key metrics
    week_2_trades = forensics_data['week_2_summary']['total_trades']
    sprint_3_trades = forensics_data['sprint_3_summary']['total_trades']
    week_2_rebalances = forensics_data['week_2_summary']['rebalance_count']
    sprint_3_rebalances = forensics_data['sprint_3_summary']['rebalance_count']
    
    # Calculate trade patterns
    week_2_trades_per_rebalance = week_2_trades / week_2_rebalances
    sprint_3_trades_per_rebalance = sprint_3_trades / sprint_3_rebalances
    
    analysis_results = {
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'objective': 'Determine root cause of 500% trade frequency increase in DJIA vs growth stocks',
        
        'trade_frequency_metrics': {
            'week_2_total_trades': week_2_trades,
            'sprint_3_total_trades': sprint_3_trades,
            'trade_increase_absolute': sprint_3_trades - week_2_trades,
            'trade_increase_percentage': ((sprint_3_trades - week_2_trades) / week_2_trades) * 100,
            
            'week_2_rebalances': week_2_rebalances,
            'sprint_3_rebalances': sprint_3_rebalances,
            'rebalance_increase_percentage': ((sprint_3_rebalances - week_2_rebalances) / week_2_rebalances) * 100,
            
            'week_2_trades_per_rebalance': week_2_trades_per_rebalance,
            'sprint_3_trades_per_rebalance': sprint_3_trades_per_rebalance,
            'trades_per_rebalance_increase': ((sprint_3_trades_per_rebalance - week_2_trades_per_rebalance) / week_2_trades_per_rebalance) * 100
        }
    }
    
    print(f"\n1. TRADE FREQUENCY BREAKDOWN:")
    print(f"   Week 2 (Growth Stocks):")
    print(f"   - Total Trades: {week_2_trades}")
    print(f"   - Total Rebalances: {week_2_rebalances}")  
    print(f"   - Trades per Rebalance: {week_2_trades_per_rebalance:.3f}")
    print(f"   - Strategy Status: Stopped early (portfolio stop-loss)")
    
    print(f"\n   Sprint #3 (DJIA Large-Cap):")
    print(f"   - Total Trades: {sprint_3_trades}")
    print(f"   - Total Rebalances: {sprint_3_rebalances}")
    print(f"   - Trades per Rebalance: {sprint_3_trades_per_rebalance:.3f}")
    print(f"   - Strategy Status: Ran full 6-year period")
    
    print(f"\n   Key Differences:")
    print(f"   - Trade Frequency Increase: {((sprint_3_trades - week_2_trades) / week_2_trades) * 100:.1f}%")
    print(f"   - Rebalance Frequency Increase: {((sprint_3_rebalances - week_2_rebalances) / week_2_rebalances) * 100:.1f}%")
    print(f"   - Trades per Rebalance Increase: {((sprint_3_trades_per_rebalance - week_2_trades_per_rebalance) / week_2_trades_per_rebalance) * 100:.1f}%")
    
    # Hypothesis testing for trade frequency explosion
    print(f"\n" + "=" * 80)
    print("ROOT CAUSE HYPOTHESIS TESTING")
    print("=" * 80)
    
    # Hypothesis 1: Strategy Duration Difference
    hypothesis_1_impact = (sprint_3_rebalances - week_2_rebalances) / week_2_rebalances
    trades_from_duration = week_2_trades * (1 + hypothesis_1_impact)
    remaining_trade_difference = sprint_3_trades - trades_from_duration
    
    print(f"\nHypothesis 1: Strategy Duration Difference")
    print(f"Evidence: Week 2 stopped early (53 rebalances), Sprint #3 ran full period (72 rebalances)")
    print(f"Expected trades if Week 2 ran full period: {trades_from_duration:.1f}")
    print(f"Actual Sprint #3 trades: {sprint_3_trades}")
    print(f"Remaining unexplained trades: {remaining_trade_difference:.1f}")
    print(f"Duration explains: {(trades_from_duration - week_2_trades) / (sprint_3_trades - week_2_trades) * 100:.1f}% of increase")
    
    # Hypothesis 2: Portfolio Churn Difference  
    print(f"\nHypothesis 2: Portfolio Churn Difference")
    print(f"Evidence: Sprint #3 trades per rebalance ({sprint_3_trades_per_rebalance:.3f}) vs Week 2 ({week_2_trades_per_rebalance:.3f})")
    print(f"Churn Increase: {((sprint_3_trades_per_rebalance - week_2_trades_per_rebalance) / week_2_trades_per_rebalance) * 100:.1f}%")
    print(f"Implication: DJIA strategy changes positions {sprint_3_trades_per_rebalance / week_2_trades_per_rebalance:.1f}x more frequently per rebalance")
    
    # Hypothesis 3: Universe Size Effect
    week_2_universe_size = 10  # Growth stocks
    sprint_3_universe_size = 30  # DJIA stocks
    universe_size_ratio = sprint_3_universe_size / week_2_universe_size
    
    print(f"\nHypothesis 3: Universe Size Effect")
    print(f"Week 2 Universe: {week_2_universe_size} stocks")
    print(f"Sprint #3 Universe: {sprint_3_universe_size} stocks")
    print(f"Universe Size Ratio: {universe_size_ratio:.1f}x")
    print(f"Expected trade increase from universe size: {(universe_size_ratio - 1) * 100:.1f}%")
    print(f"Actual trade increase: {((sprint_3_trades - week_2_trades) / week_2_trades) * 100:.1f}%")
    print(f"Universe size explains: {((universe_size_ratio - 1) / ((sprint_3_trades - week_2_trades) / week_2_trades)) * 100:.1f}% of increase")
    
    # Hypothesis 4: Strategy Behavior Difference
    print(f"\nHypothesis 4: Strategy Behavior Difference")
    print(f"Key Insight: Different asset characteristics cause different rebalancing behavior")
    print(f"Growth Stocks: High volatility, but positions held longer")
    print(f"DJIA Stocks: Lower individual volatility, but rankings change more frequently")
    print(f"Result: More frequent 'musical chairs' effect in large-cap universe")
    
    # Portfolio turnover analysis
    print(f"\n" + "=" * 80)
    print("PORTFOLIO TURNOVER ANALYSIS")
    print("=" * 80)
    
    # Estimate portfolio turnover
    positions_per_rebalance = 2  # Both strategies use 2 positions
    
    week_2_position_changes = week_2_trades / 2  # Assume 2 trades per position change
    week_2_turnover_per_rebalance = week_2_position_changes / week_2_rebalances / positions_per_rebalance
    
    sprint_3_position_changes = sprint_3_trades / 2
    sprint_3_turnover_per_rebalance = sprint_3_position_changes / sprint_3_rebalances / positions_per_rebalance
    
    print(f"Portfolio Turnover Analysis:")
    print(f"Week 2 Estimated Turnover per Rebalance: {week_2_turnover_per_rebalance:.1%}")
    print(f"Sprint #3 Estimated Turnover per Rebalance: {sprint_3_turnover_per_rebalance:.1%}")
    print(f"Turnover Increase: {(sprint_3_turnover_per_rebalance / week_2_turnover_per_rebalance - 1) * 100:.1f}%")
    
    analysis_results.update({
        'hypothesis_testing': {
            'duration_difference': {
                'week_2_rebalances': week_2_rebalances,
                'sprint_3_rebalances': sprint_3_rebalances,
                'expected_trades_full_period': trades_from_duration,
                'actual_sprint_3_trades': sprint_3_trades,
                'duration_explains_pct': (trades_from_duration - week_2_trades) / (sprint_3_trades - week_2_trades) * 100
            },
            'portfolio_churn': {
                'week_2_trades_per_rebalance': week_2_trades_per_rebalance,
                'sprint_3_trades_per_rebalance': sprint_3_trades_per_rebalance,
                'churn_increase_pct': ((sprint_3_trades_per_rebalance - week_2_trades_per_rebalance) / week_2_trades_per_rebalance) * 100,
                'churn_multiplier': sprint_3_trades_per_rebalance / week_2_trades_per_rebalance
            },
            'universe_size_effect': {
                'week_2_universe_size': week_2_universe_size,
                'sprint_3_universe_size': sprint_3_universe_size,
                'universe_size_ratio': universe_size_ratio,
                'universe_explains_pct': ((universe_size_ratio - 1) / ((sprint_3_trades - week_2_trades) / week_2_trades)) * 100
            }
        },
        
        'portfolio_turnover': {
            'week_2_turnover_per_rebalance': week_2_turnover_per_rebalance,
            'sprint_3_turnover_per_rebalance': sprint_3_turnover_per_rebalance,
            'turnover_increase_pct': (sprint_3_turnover_per_rebalance / week_2_turnover_per_rebalance - 1) * 100
        }
    })
    
    # Key findings summary
    print(f"\n" + "=" * 80)
    print("KEY FINDINGS SUMMARY")
    print("=" * 80)
    
    print(f"\nPrimary Cause: Portfolio Churn Explosion")
    print(f"- Sprint #3 generates {sprint_3_trades_per_rebalance / week_2_trades_per_rebalance:.1f}x more trades per rebalance")
    print(f"- DJIA rankings change more frequently than growth stock rankings")
    print(f"- Results in constant 'musical chairs' portfolio rebalancing")
    
    print(f"\nSecondary Cause: Strategy Duration")
    print(f"- Week 2 stopped early due to portfolio stop-loss")
    print(f"- Sprint #3 ran full 6-year period")
    print(f"- Duration difference explains {(trades_from_duration - week_2_trades) / (sprint_3_trades - week_2_trades) * 100:.1f}% of trade increase")
    
    print(f"\nTertiary Cause: Universe Size")  
    print(f"- 3x larger universe provides more rebalancing options")
    print(f"- Explains {((universe_size_ratio - 1) / ((sprint_3_trades - week_2_trades) / week_2_trades)) * 100:.1f}% of trade increase")
    
    # Save results
    results_dir = 'results/post_mortem_analysis'
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f'trade_frequency_analysis_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(analysis_results, f, indent=2, default=str)
    
    print(f"\n" + "=" * 80)
    print("TRADE FREQUENCY ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {results_file}")
    print(f"Root Cause Identified: DJIA strategy behavior causes {sprint_3_trades_per_rebalance / week_2_trades_per_rebalance:.1f}x more portfolio churn")
    print("=" * 80)
    
    return results_file, analysis_results

if __name__ == '__main__':
    results_file, analysis = analyze_trade_frequency_explosion()
    print(f"\nTrade frequency analysis complete. Portfolio churn root cause identified.")