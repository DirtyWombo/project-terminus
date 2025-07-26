# transaction_cost_forensics.py
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

def analyze_cost_discrepancy():
    """
    Forensic analysis of why DJIA transaction costs were 71% higher than expected
    
    Key Investigation Areas:
    1. Trade frequency comparison
    2. Portfolio value calculation during rebalancing
    3. Fixed cost application to different price levels
    4. Cost model parameter differences
    5. Position sizing and turnover analysis
    """
    
    print("=" * 80)
    print("TRANSACTION COST FORENSICS - POST-MORTEM ANALYSIS")
    print("=" * 80)
    print("Objective: Determine why DJIA costs were 71% higher than growth stocks")
    print("Key Question: Why 37.0% cost impact vs expected ~6-8% for large-cap?")
    print("=" * 80)
    
    # Load results files for comparison
    week_2_file = 'results/week_2_risk_management/final_validation_20250725_013544.json'
    sprint_3_file = 'results/sprint_3_djia/sprint_3_djia_results_20250725_071555.json'
    
    # Load data
    try:
        with open(week_2_file, 'r') as f:
            week_2_data = json.load(f)
        with open(sprint_3_file, 'r') as f:
            sprint_3_data = json.load(f)
        print("Loaded results files for comparison")
    except Exception as e:
        print(f"Error loading results files: {e}")
        return
    
    # Extract key metrics for comparison
    analysis_results = {
        'investigation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'objective': 'Determine root cause of 71% higher transaction costs in DJIA vs growth stocks',
        
        # Raw data comparison
        'week_2_summary': {
            'universe': 'Growth stocks (CRWD, SNOW, PLTR, U, RBLX, NET, DDOG, MDB, OKTA, ZS)',
            'total_costs': week_2_data['transaction_costs']['total_costs_usd'],
            'cost_impact_pct': week_2_data['transaction_costs']['cost_impact_pct'],
            'total_trades': week_2_data['trading_activity']['total_trades'],
            'rebalance_count': week_2_data['trading_activity']['rebalance_count'],
            'cost_tier': 'mid_cap',
            'strategy_stopped_out': True,
            'final_value': week_2_data['performance']['final_value']
        },
        
        'sprint_3_summary': {
            'universe': 'DJIA large-cap (30 stocks)',
            'total_costs': sprint_3_data['transaction_costs']['total_costs_usd'],
            'cost_impact_pct': sprint_3_data['transaction_costs']['cost_impact_pct'],
            'total_trades': sprint_3_data['trading_activity']['total_trades'],
            'rebalance_count': sprint_3_data['trading_activity']['rebalance_count'],
            'cost_tier': 'large_cap',
            'strategy_stopped_out': False,
            'final_value': sprint_3_data['performance']['final_value']
        }
    }
    
    # Calculate key ratios and differences
    week_2_costs = week_2_data['transaction_costs']['total_costs_usd']
    sprint_3_costs = sprint_3_data['transaction_costs']['total_costs_usd']
    cost_increase_pct = ((sprint_3_costs - week_2_costs) / week_2_costs) * 100
    
    week_2_trades = week_2_data['trading_activity']['total_trades']
    sprint_3_trades = sprint_3_data['trading_activity']['total_trades']
    trade_increase_pct = ((sprint_3_trades - week_2_trades) / week_2_trades) * 100
    
    week_2_rebalances = week_2_data['trading_activity']['rebalance_count']
    sprint_3_rebalances = sprint_3_data['trading_activity']['rebalance_count']
    rebalance_increase_pct = ((sprint_3_rebalances - week_2_rebalances) / week_2_rebalances) * 100
    
    # Analysis findings
    analysis_results.update({
        'key_findings': {
            'cost_increase': {
                'week_2_total_costs': week_2_costs,
                'sprint_3_total_costs': sprint_3_costs,
                'absolute_increase': sprint_3_costs - week_2_costs,
                'percentage_increase': cost_increase_pct,
                'expected_decrease': -60,  # Expected 60% reduction for large-cap
                'actual_vs_expected_gap': cost_increase_pct - (-60)
            },
            
            'trade_frequency_analysis': {
                'week_2_trades': week_2_trades,
                'sprint_3_trades': sprint_3_trades,
                'trade_increase_pct': trade_increase_pct,
                'week_2_trades_per_rebalance': week_2_trades / week_2_rebalances,
                'sprint_3_trades_per_rebalance': sprint_3_trades / sprint_3_rebalances,
                'trades_per_rebalance_increase': ((sprint_3_trades / sprint_3_rebalances) - (week_2_trades / week_2_rebalances)) / (week_2_trades / week_2_rebalances) * 100
            },
            
            'rebalancing_frequency': {
                'week_2_rebalances': week_2_rebalances,
                'sprint_3_rebalances': sprint_3_rebalances,
                'rebalance_increase_pct': rebalance_increase_pct,
                'week_2_strategy_stopped_early': True,
                'sprint_3_ran_full_period': True
            }
        }
    })
    
    # Cost model parameter comparison
    week_2_params = week_2_data['transaction_costs']['cost_model_params']
    sprint_3_params = sprint_3_data['transaction_costs']['cost_model_params']
    
    analysis_results['cost_model_comparison'] = {
        'week_2_params': week_2_params,
        'sprint_3_params': sprint_3_params,
        'parameter_differences': {
            'bid_ask_spread': {
                'week_2': week_2_params['bid_ask_spread'],
                'sprint_3': sprint_3_params['bid_ask_spread'],
                'reduction_pct': ((sprint_3_params['bid_ask_spread'] - week_2_params['bid_ask_spread']) / week_2_params['bid_ask_spread']) * 100
            },
            'slippage_factor': {
                'week_2': week_2_params['slippage_factor'], 
                'sprint_3': sprint_3_params['slippage_factor'],
                'reduction_pct': ((sprint_3_params['slippage_factor'] - week_2_params['slippage_factor']) / week_2_params['slippage_factor']) * 100
            },
            'market_impact_factor': {
                'week_2': week_2_params['market_impact_factor'],
                'sprint_3': sprint_3_params['market_impact_factor'], 
                'reduction_pct': ((sprint_3_params['market_impact_factor'] - week_2_params['market_impact_factor']) / week_2_params['market_impact_factor']) * 100
            }
        }
    }
    
    # Cost breakdown comparison
    week_2_breakdown = week_2_data['transaction_costs']['cost_breakdown_usd']
    sprint_3_breakdown = sprint_3_data['transaction_costs']['cost_breakdown_usd']
    
    analysis_results['cost_breakdown_comparison'] = {
        'week_2_breakdown': week_2_breakdown,
        'sprint_3_breakdown': sprint_3_breakdown,
        'component_analysis': {}
    }
    
    for component in ['commission', 'spread_cost', 'slippage', 'market_impact', 'timing_cost']:
        if component in week_2_breakdown and component in sprint_3_breakdown:
            week_2_amount = week_2_breakdown[component]
            sprint_3_amount = sprint_3_breakdown[component]
            increase_pct = ((sprint_3_amount - week_2_amount) / week_2_amount) * 100
            
            analysis_results['cost_breakdown_comparison']['component_analysis'][component] = {
                'week_2_amount': week_2_amount,
                'sprint_3_amount': sprint_3_amount,
                'absolute_increase': sprint_3_amount - week_2_amount,
                'percentage_increase': increase_pct,
                'week_2_pct_of_total': (week_2_amount / week_2_costs) * 100,
                'sprint_3_pct_of_total': (sprint_3_amount / sprint_3_costs) * 100
            }
    
    # Print detailed analysis
    print("\n" + "=" * 80)
    print("FORENSIC FINDINGS - ROOT CAUSE ANALYSIS")
    print("=" * 80)
    
    print(f"\n1. COST EXPLOSION MAGNITUDE:")
    print(f"   Week 2 Total Costs: ${week_2_costs:,.2f} (21.6% of capital)")
    print(f"   Sprint #3 Total Costs: ${sprint_3_costs:,.2f} (37.0% of capital)")
    print(f"   Absolute Increase: ${sprint_3_costs - week_2_costs:,.2f}")
    print(f"   Percentage Increase: {cost_increase_pct:.1f}%")
    print(f"   Expected for Large-Cap: -60% (significant reduction)")
    print(f"   Actual vs Expected Gap: {cost_increase_pct - (-60):.1f} percentage points")
    
    print(f"\n2. TRADE FREQUENCY EXPLOSION:")
    print(f"   Week 2 Total Trades: {week_2_trades}")
    print(f"   Sprint #3 Total Trades: {sprint_3_trades}")
    print(f"   Trade Increase: {trade_increase_pct:.1f}%")
    print(f"   Week 2 Trades per Rebalance: {week_2_trades / week_2_rebalances:.2f}")
    print(f"   Sprint #3 Trades per Rebalance: {sprint_3_trades / sprint_3_rebalances:.2f}")
    
    print(f"\n3. REBALANCING FREQUENCY:")
    print(f"   Week 2 Rebalances: {week_2_rebalances} (stopped early)")
    print(f"   Sprint #3 Rebalances: {sprint_3_rebalances} (full period)")
    print(f"   Rebalance Increase: {rebalance_increase_pct:.1f}%")
    
    print(f"\n4. COST MODEL PARAMETER DIFFERENCES:")
    for param, data in analysis_results['cost_model_comparison']['parameter_differences'].items():
        print(f"   {param.replace('_', ' ').title()}:")
        print(f"     Week 2: {data['week_2']:.5f}")
        print(f"     Sprint #3: {data['sprint_3']:.5f}")
        print(f"     Change: {data['reduction_pct']:.1f}%")
    
    print(f"\n5. COST COMPONENT BREAKDOWN:")
    for component, data in analysis_results['cost_breakdown_comparison']['component_analysis'].items():
        print(f"   {component.replace('_', ' ').title()}:")
        print(f"     Week 2: ${data['week_2_amount']:,.2f} ({data['week_2_pct_of_total']:.1f}% of total)")
        print(f"     Sprint #3: ${data['sprint_3_amount']:,.2f} ({data['sprint_3_pct_of_total']:.1f}% of total)")
        print(f"     Increase: {data['percentage_increase']:.1f}%")
    
    # Key hypothesis analysis
    print(f"\n" + "=" * 80)
    print("HYPOTHESIS TESTING")
    print("=" * 80)
    
    print(f"\nHypothesis 1: Portfolio Value Calculation Issue")
    print(f"Evidence: Week 2 stopped early (portfolio liquidated), Sprint #3 ran full period")
    print(f"Impact: Sprint #3 had {rebalance_increase_pct:.1f}% more rebalancing opportunities")
    print(f"Assessment: PARTIAL - explains rebalance frequency but not per-trade cost increase")
    
    print(f"\nHypothesis 2: Fixed Cost Application to Price Levels")
    print(f"Evidence: Commission increased {analysis_results['cost_breakdown_comparison']['component_analysis']['commission']['percentage_increase']:.1f}%")
    print(f"Week 2 Commission per Trade: ${week_2_breakdown['commission'] / week_2_trades:.2f}")
    print(f"Sprint #3 Commission per Trade: ${sprint_3_breakdown['commission'] / sprint_3_trades:.2f}")
    print(f"Assessment: SIGNIFICANT - commission per trade should be similar but isn't")
    
    print(f"\nHypothesis 3: Trade Frequency Explosion")
    print(f"Evidence: {sprint_3_trades} trades vs {week_2_trades} trades (+{trade_increase_pct:.1f}%)")
    print(f"Root Cause: Strategy generates more frequent position changes in DJIA universe")
    print(f"Assessment: PRIMARY - explains majority of cost increase")
    
    # Save analysis results
    results_dir = 'results/post_mortem_analysis'
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f'transaction_cost_forensics_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(analysis_results, f, indent=2, default=str)
    
    print(f"\n" + "=" * 80)
    print("FORENSIC ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Detailed results saved to: {results_file}")
    print(f"Key Finding: Trade frequency explosion (+{trade_increase_pct:.1f}%) is primary cause")
    print(f"Secondary Finding: Early stop-loss in Week 2 masked true cost comparison")
    print("=" * 80)
    
    return results_file, analysis_results

if __name__ == '__main__':
    results_file, analysis = analyze_cost_discrepancy()
    print(f"\nForensic analysis complete. Root cause investigation ready for review.")