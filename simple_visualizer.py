# simple_visualizer.py
import json
import pandas as pd
import matplotlib.pyplot as plt
import os

# Use matplotlib without GUI for Windows compatibility
plt.switch_backend('Agg')

def create_simple_performance_chart():
    """Create simple performance comparison chart"""
    
    # Load results
    results_file = 'results/sprint_1/sprint_1_analysis_20250725_003208.json'
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Create output directory
    output_dir = 'results/sprint_1/visualizations'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Extract strategy performance
    strategies = []
    returns = []
    
    # MA Crossover average
    ma_returns = [data['total_return_pct'] for data in results['MA_Crossover'].values()]
    strategies.append('MA Crossover')
    returns.append(sum(ma_returns) / len(ma_returns))
    
    # Bollinger Bounce average
    bb_returns = [data['total_return_pct'] for data in results['Bollinger_Bounce'].values()]
    strategies.append('Bollinger Bounce')
    returns.append(sum(bb_returns) / len(bb_returns))
    
    # Value Portfolio
    strategies.append('Value Portfolio')
    returns.append(results['Value_Factor_Portfolio']['PORTFOLIO']['total_return_pct'])
    
    # Create chart
    plt.figure(figsize=(10, 6))
    bars = plt.bar(strategies, returns, color=['blue', 'orange', 'green'])
    plt.title('Strategy Performance Comparison - Sprint #1', fontsize=14, fontweight='bold')
    plt.ylabel('Total Return (%)', fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, v in enumerate(returns):
        plt.text(i, v + max(returns) * 0.01, f'{v:.1f}%', ha='center', fontweight='bold')
    
    plt.tight_layout()
    chart_path = os.path.join(output_dir, 'performance_comparison.png')
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Performance chart saved to: {chart_path}")
    return chart_path

def create_trade_count_chart():
    """Create trade count comparison"""
    
    results_file = 'results/sprint_1/sprint_1_analysis_20250725_003208.json'
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    output_dir = 'results/sprint_1/visualizations'
    
    # Calculate average trades per strategy
    ma_trades = [data['total_trades'] for data in results['MA_Crossover'].values()]
    bb_trades = [data['total_trades'] for data in results['Bollinger_Bounce'].values()]
    
    strategies = ['MA Crossover', 'Bollinger Bounce', 'Value Portfolio']
    avg_trades = [
        sum(ma_trades) / len(ma_trades),
        sum(bb_trades) / len(bb_trades),
        results['Value_Factor_Portfolio']['PORTFOLIO']['total_trades']
    ]
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(strategies, avg_trades, color=['blue', 'orange', 'green'])
    plt.title('Average Trades per Strategy - Sprint #1', fontsize=14, fontweight='bold')
    plt.ylabel('Number of Trades', fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # Add value labels
    for i, v in enumerate(avg_trades):
        plt.text(i, v + max(avg_trades) * 0.01, f'{v:.1f}', ha='center', fontweight='bold')
    
    plt.tight_layout()
    chart_path = os.path.join(output_dir, 'trade_count_comparison.png')
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Trade count chart saved to: {chart_path}")
    return chart_path

if __name__ == '__main__':
    print("Generating performance visualizations...")
    
    try:
        perf_chart = create_simple_performance_chart()
        trades_chart = create_trade_count_chart()
        
        print("SUCCESS: Performance visualization complete!")
        print(f"Charts available in: results/sprint_1/visualizations/")
        
    except Exception as e:
        print(f"Error generating visualizations: {e}")