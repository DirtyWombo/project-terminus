# sprint_5_comparative_analysis.py
# Sprint #5 Final Comparative Analysis: Baseline vs Volume Filter vs ADX Filter

import json
import pandas as pd
from datetime import datetime
import os

def load_results_files():
    """
    Load all three strategy results files
    """
    
    # Load Sprint #4 baseline results
    baseline_file = 'results/sprint_4_golden_cross/sprint_4_golden_cross_results_20250725_082546.json'
    
    # Find the latest volume and ADX filter results
    results_dir = 'results/sprint_5_filtered_crossover'
    
    volume_files = [f for f in os.listdir(results_dir) if f.startswith('volume_filter_results_')]
    adx_files = [f for f in os.listdir(results_dir) if f.startswith('adx_filter_results_')]
    
    # Get latest files (most recent timestamp)
    volume_file = os.path.join(results_dir, sorted(volume_files)[-1]) if volume_files else None
    adx_file = os.path.join(results_dir, sorted(adx_files)[-1]) if adx_files else None
    
    results = {}
    
    # Load baseline
    try:
        with open(baseline_file, 'r') as f:
            results['baseline'] = json.load(f)
        print(f"Loaded baseline results from: {baseline_file}")
    except Exception as e:
        print(f"Error loading baseline: {e}")
        return None
    
    # Load volume filter
    if volume_file:
        try:
            with open(volume_file, 'r') as f:
                results['volume_filter'] = json.load(f)
            print(f"Loaded volume filter results from: {volume_file}")
        except Exception as e:
            print(f"Error loading volume filter: {e}")
            return None
    
    # Load ADX filter
    if adx_file:
        try:
            with open(adx_file, 'r') as f:
                results['adx_filter'] = json.load(f)
            print(f"Loaded ADX filter results from: {adx_file}")
        except Exception as e:
            print(f"Error loading ADX filter: {e}")
            return None
    
    return results

def create_comparison_table(results):
    """
    Create side-by-side comparison table of all three strategies
    """
    
    # Extract key metrics for comparison
    comparison_data = []
    
    for strategy_name, data in results.items():
        aggregate = data['aggregate_metrics']
        
        # Format strategy name
        if strategy_name == 'baseline':
            display_name = 'Baseline Golden Cross'
            strategy_desc = 'No filters'
        elif strategy_name == 'volume_filter':
            display_name = 'Golden Cross + Volume Filter'  
            strategy_desc = 'Volume > 150% of 20-day avg'
        elif strategy_name == 'adx_filter':
            display_name = 'Golden Cross + ADX Filter'
            strategy_desc = 'ADX > 25'
        
        comparison_data.append({
            'Strategy': display_name,
            'Filter': strategy_desc,
            'Avg Sharpe Ratio': aggregate.get('avg_sharpe_ratio', 0),
            'Avg Total Return (%)': aggregate.get('avg_total_return_pct', 0),
            'Aggregate Win Rate (%)': aggregate.get('aggregate_win_rate_pct', 0),
            'Aggregate Expectancy ($)': aggregate.get('aggregate_expectancy', 0),
            'Total Trades': aggregate.get('total_trades_all_stocks', 0),
            'Profitable Stocks': f"{aggregate.get('profitable_stocks', 0)}/{aggregate.get('stocks_tested', 0)}",
            'Avg Max Drawdown (%)': aggregate.get('avg_max_drawdown_pct', 0)
        })
        
        # Add filter effectiveness if applicable
        if strategy_name != 'baseline':
            if 'total_signals_generated' in aggregate:
                filter_pass_rate = aggregate.get('aggregate_filter_pass_rate_pct', 0)
                comparison_data[-1]['Filter Pass Rate (%)'] = filter_pass_rate
    
    return pd.DataFrame(comparison_data)

def evaluate_success_criteria(results):
    """
    Evaluate Sprint #5 success criteria for each strategy
    """
    
    criteria_results = {}
    
    for strategy_name, data in results.items():
        aggregate = data['aggregate_metrics']
        
        sharpe_ratio = aggregate.get('avg_sharpe_ratio', 0)
        win_rate = aggregate.get('aggregate_win_rate_pct', 0)
        
        sharpe_pass = sharpe_ratio > 0.5
        win_rate_pass = win_rate > 40
        overall_pass = sharpe_pass and win_rate_pass
        
        criteria_results[strategy_name] = {
            'sharpe_ratio': sharpe_ratio,
            'sharpe_pass': sharpe_pass,
            'win_rate': win_rate,
            'win_rate_pass': win_rate_pass,
            'overall_pass': overall_pass
        }
    
    return criteria_results

def analyze_filter_effectiveness(results):
    """
    Analyze how effective each filter was at improving signal quality
    """
    
    filter_analysis = {}
    
    baseline_metrics = results['baseline']['aggregate_metrics']
    
    for strategy_name, data in results.items():
        if strategy_name == 'baseline':
            continue
            
        aggregate = data['aggregate_metrics']
        
        # Compare vs baseline
        sharpe_improvement = aggregate.get('avg_sharpe_ratio', 0) - baseline_metrics.get('avg_sharpe_ratio', 0)
        win_rate_improvement = aggregate.get('aggregate_win_rate_pct', 0) - baseline_metrics.get('aggregate_win_rate_pct', 0)
        
        filter_analysis[strategy_name] = {
            'filter_pass_rate': aggregate.get('aggregate_filter_pass_rate_pct', 0),
            'signals_generated': aggregate.get('total_signals_generated', 0),
            'signals_filtered': aggregate.get('total_signals_filtered', 0),
            'sharpe_improvement': sharpe_improvement,
            'win_rate_improvement': win_rate_improvement,
            'trades_vs_baseline': aggregate.get('total_trades_all_stocks', 0) - baseline_metrics.get('total_trades_all_stocks', 0)
        }
    
    return filter_analysis

def generate_sprint_5_report(results):
    """
    Generate comprehensive Sprint #5 final report
    """
    
    print("=" * 100)
    print("SPRINT #5 FINAL REPORT: FILTERED CROSSOVER STRATEGY COMPARISON")
    print("=" * 100)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing Period: 2018-2023 (6 years)")
    print(f"Universe: Small/Mid-Cap Growth Stocks (10 stocks)")
    print("")
    
    # Create comparison table
    comparison_df = create_comparison_table(results)
    
    print("STRATEGY PERFORMANCE COMPARISON:")
    print("=" * 100)
    print(comparison_df.to_string(index=False, float_format='%.2f'))
    print("")
    
    # Success criteria evaluation
    criteria_results = evaluate_success_criteria(results)
    
    print("SUCCESS CRITERIA EVALUATION:")
    print("=" * 60)
    print("Target: Sharpe Ratio > 0.5 AND Win Rate > 40%")
    print("")
    
    for strategy_name, criteria in criteria_results.items():
        if strategy_name == 'baseline':
            display_name = 'Baseline Golden Cross'
        elif strategy_name == 'volume_filter':
            display_name = 'Volume Filter'
        elif strategy_name == 'adx_filter':
            display_name = 'ADX Filter'
            
        print(f"{display_name}:")
        print(f"  Sharpe Ratio: {criteria['sharpe_ratio']:.2f} - {'PASS' if criteria['sharpe_pass'] else 'FAIL'}")
        print(f"  Win Rate: {criteria['win_rate']:.1f}% - {'PASS' if criteria['win_rate_pass'] else 'FAIL'}")
        print(f"  Overall: {'SUCCESS' if criteria['overall_pass'] else 'FAILED'}")
        print("")
    
    # Filter effectiveness analysis
    filter_analysis = analyze_filter_effectiveness(results)
    
    print("FILTER EFFECTIVENESS ANALYSIS:")
    print("=" * 60)
    
    for strategy_name, analysis in filter_analysis.items():
        if strategy_name == 'volume_filter':
            filter_name = 'Volume Filter (Volume > 150% of 20-day avg)'
        elif strategy_name == 'adx_filter':
            filter_name = 'ADX Filter (ADX > 25)'
            
        print(f"{filter_name}:")
        print(f"  Filter Pass Rate: {analysis['filter_pass_rate']:.1f}%")
        print(f"  Signals Generated: {analysis['signals_generated']}")
        print(f"  Signals Passed: {analysis['signals_filtered']}")
        print(f"  Sharpe Improvement vs Baseline: {analysis['sharpe_improvement']:+.2f}")
        print(f"  Win Rate Improvement vs Baseline: {analysis['win_rate_improvement']:+.1f}%")
        print(f"  Trade Count Change vs Baseline: {analysis['trades_vs_baseline']:+d}")
        print("")
    
    # Final assessment
    print("SPRINT #5 FINAL ASSESSMENT:")
    print("=" * 60)
    
    any_success = any(criteria['overall_pass'] for criteria in criteria_results.values())
    
    if any_success:
        successful_strategies = [name for name, criteria in criteria_results.items() if criteria['overall_pass']]
        print(f"SUCCESS! The following strategies met success criteria:")
        for strategy in successful_strategies:
            print(f"  - {strategy}")
    else:
        print("FAILED: No strategy met the success criteria (Sharpe > 0.5 AND Win Rate > 40%)")
        
        # Find best performing strategy
        best_strategy = max(criteria_results.keys(), 
                          key=lambda x: (criteria_results[x]['sharpe_ratio'] + criteria_results[x]['win_rate']/100))
        
        best_criteria = criteria_results[best_strategy]
        print(f"\nBest Performing Strategy: {best_strategy}")
        print(f"  Sharpe: {best_criteria['sharpe_ratio']:.2f} (target: >0.5)")
        print(f"  Win Rate: {best_criteria['win_rate']:.1f}% (target: >40%)")
    
    print("")
    print("KEY INSIGHTS:")
    print("- Both filters dramatically reduced trading activity vs baseline")
    print("- Volume Filter: More selective than ADX Filter")
    print("- ADX Filter: Generated more trades but lower win rate")
    print("- Neither filter achieved target performance thresholds")
    print("- Golden Cross strategy appears unsuitable for this universe regardless of filters")
    
    return comparison_df, criteria_results, filter_analysis

def save_sprint_5_final_results(comparison_df, criteria_results, filter_analysis):
    """
    Save Sprint #5 final comparative results
    """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save comparison table as CSV
    csv_file = f'results/sprint_5_comparative_analysis_{timestamp}.csv'
    comparison_df.to_csv(csv_file, index=False)
    
    # Save detailed analysis as JSON
    json_file = f'results/sprint_5_final_analysis_{timestamp}.json'
    
    final_results = {
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sprint': 'Sprint #5 - Filtered Crossover Strategy Test',
        'objective': 'Test if Volume or ADX filters can improve Golden Cross performance',
        'success_criteria': 'Sharpe Ratio > 0.5 AND Win Rate > 40%',
        'comparison_table': comparison_df.to_dict('records'),
        'success_criteria_results': criteria_results,
        'filter_effectiveness': filter_analysis,
        'final_assessment': {
            'sprint_success': any(criteria['overall_pass'] for criteria in criteria_results.values()),
            'best_strategy': max(criteria_results.keys(), 
                               key=lambda x: (criteria_results[x]['sharpe_ratio'] + criteria_results[x]['win_rate']/100)),
            'recommendation': 'Neither filter achieved target performance. Golden Cross strategy appears fundamentally unsuitable for this volatile growth stock universe.'
        }
    }
    
    with open(json_file, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"Results saved to:")
    print(f"  CSV: {csv_file}")
    print(f"  JSON: {json_file}")
    
    return csv_file, json_file

if __name__ == '__main__':
    print("Loading Sprint #5 results files...")
    
    results = load_results_files()
    if results is None:
        print("Failed to load results files.")
        exit(1)
    
    print(f"\nLoaded {len(results)} strategy results.")
    print("\nGenerating comparative analysis...")
    
    comparison_df, criteria_results, filter_analysis = generate_sprint_5_report(results)
    
    print("\nSaving final results...")
    csv_file, json_file = save_sprint_5_final_results(comparison_df, criteria_results, filter_analysis)
    
    print(f"\nSprint #5 Comparative Analysis Complete!")