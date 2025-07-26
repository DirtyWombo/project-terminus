# performance_visualizer.py
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import numpy as np

class PerformanceVisualizer:
    def __init__(self, results_file):
        with open(results_file, 'r') as f:
            self.results = json.load(f)
        self.output_dir = 'results/sprint_1/visualizations'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def create_strategy_comparison_chart(self):
        """Create comparison chart of all strategies"""
        strategies = []
        returns = []
        sharpe_ratios = []
        max_drawdowns = []
        win_rates = []
        
        # Extract data from results
        for strategy_name, strategy_data in self.results.items():
            if strategy_name == 'Value_Factor_Portfolio':
                strategies.append('Value Portfolio')
                portfolio_data = strategy_data['PORTFOLIO']
                returns.append(portfolio_data['total_return_pct'])
                sharpe_ratios.append(0 if pd.isna(portfolio_data['sharpe_ratio']) else portfolio_data['sharpe_ratio'])
                max_drawdowns.append(portfolio_data['max_drawdown_pct'])
                win_rates.append(portfolio_data['win_rate_pct'])
            else:
                # Calculate averages for single-stock strategies
                stock_returns = [data['total_return_pct'] for data in strategy_data.values()]
                stock_sharpes = [0 if pd.isna(data['sharpe_ratio']) else data['sharpe_ratio'] 
                               for data in strategy_data.values()]
                stock_drawdowns = [data['max_drawdown_pct'] for data in strategy_data.values()]
                stock_win_rates = [data['win_rate_pct'] for data in strategy_data.values()]
                
                strategies.append(strategy_name.replace('_', ' '))
                returns.append(np.mean(stock_returns))
                sharpe_ratios.append(np.mean(stock_sharpes))
                max_drawdowns.append(np.mean(stock_drawdowns))
                win_rates.append(np.mean(stock_win_rates))
        
        # Create comparison chart
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Strategy Performance Comparison - Sprint #1', fontsize=16, fontweight='bold')
        
        # Returns comparison
        bars1 = ax1.bar(strategies, returns, color=['#2E8B57', '#4169E1', '#DC143C'])
        ax1.set_title('Total Returns (%)', fontweight='bold')
        ax1.set_ylabel('Return (%)')
        ax1.grid(True, alpha=0.3)
        for i, v in enumerate(returns):
            ax1.text(i, v + max(returns) * 0.01, f'{v:.1f}%', ha='center', fontweight='bold')
        
        # Sharpe ratios
        bars2 = ax2.bar(strategies, sharpe_ratios, color=['#2E8B57', '#4169E1', '#DC143C'])
        ax2.set_title('Sharpe Ratios', fontweight='bold')
        ax2.set_ylabel('Sharpe Ratio')
        ax2.grid(True, alpha=0.3)
        for i, v in enumerate(sharpe_ratios):
            ax2.text(i, v + max(sharpe_ratios) * 0.05, f'{v:.2f}', ha='center', fontweight='bold')
        
        # Max drawdowns
        bars3 = ax3.bar(strategies, max_drawdowns, color=['#CD853F', '#CD853F', '#CD853F'])
        ax3.set_title('Maximum Drawdowns (%)', fontweight='bold')
        ax3.set_ylabel('Drawdown (%)')
        ax3.grid(True, alpha=0.3)
        for i, v in enumerate(max_drawdowns):
            ax3.text(i, v + max(max_drawdowns) * 0.01, f'{v:.1f}%', ha='center', fontweight='bold')
        
        # Win rates
        bars4 = ax4.bar(strategies, win_rates, color=['#228B22', '#4169E1', '#FF6347'])
        ax4.set_title('Win Rates (%)', fontweight='bold')
        ax4.set_ylabel('Win Rate (%)')
        ax4.grid(True, alpha=0.3)
        ax4.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='Break-even')
        for i, v in enumerate(win_rates):
            ax4.text(i, v + max(win_rates) * 0.01, f'{v:.1f}%', ha='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'strategy_comparison.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        return os.path.join(self.output_dir, 'strategy_comparison.png')
    
    def create_stock_performance_heatmap(self):
        """Create heatmap showing performance by stock and strategy"""
        stocks = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
        strategies = ['MA_Crossover', 'Bollinger_Bounce']
        
        # Create performance matrix
        performance_matrix = []
        
        for strategy in strategies:
            strategy_row = []
            for stock in stocks:
                if stock in self.results[strategy]:
                    return_pct = self.results[strategy][stock]['total_return_pct']
                    strategy_row.append(return_pct)
                else:
                    strategy_row.append(0)
            performance_matrix.append(strategy_row)
        
        # Create heatmap
        plt.figure(figsize=(12, 6))
        sns.heatmap(performance_matrix, 
                    xticklabels=stocks, 
                    yticklabels=[s.replace('_', ' ') for s in strategies],
                    annot=True, 
                    fmt='.2f', 
                    cmap='RdYlGn', 
                    center=0,
                    cbar_kws={'label': 'Return (%)'})
        
        plt.title('Stock Performance by Strategy - Sprint #1', fontsize=14, fontweight='bold')
        plt.xlabel('Stocks', fontweight='bold')
        plt.ylabel('Strategies', fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'stock_performance_heatmap.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        return os.path.join(self.output_dir, 'stock_performance_heatmap.png')
    
    def create_trade_frequency_analysis(self):
        """Analyze trade frequency across strategies"""
        strategies = []
        avg_trades = []
        min_trades = []
        max_trades = []
        
        for strategy_name, strategy_data in self.results.items():
            if strategy_name != 'Value_Factor_Portfolio':
                trades_per_stock = [data['total_trades'] for data in strategy_data.values()]
                strategies.append(strategy_name.replace('_', ' '))
                avg_trades.append(np.mean(trades_per_stock))
                min_trades.append(np.min(trades_per_stock))
                max_trades.append(np.max(trades_per_stock))
        
        # Create trade frequency chart
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Trade Frequency Analysis - Sprint #1', fontsize=16, fontweight='bold')
        
        # Average trades per stock
        bars1 = ax1.bar(strategies, avg_trades, color=['#4169E1', '#DC143C'])
        ax1.set_title('Average Trades per Stock', fontweight='bold')
        ax1.set_ylabel('Number of Trades')
        ax1.grid(True, alpha=0.3)
        for i, v in enumerate(avg_trades):
            ax1.text(i, v + max(avg_trades) * 0.01, f'{v:.1f}', ha='center', fontweight='bold')
        
        # Trade frequency range
        x_pos = np.arange(len(strategies))
        ax2.bar(x_pos, avg_trades, yerr=[np.array(avg_trades) - np.array(min_trades), 
                                        np.array(max_trades) - np.array(avg_trades)], 
                capsize=5, color=['#4169E1', '#DC143C'], alpha=0.7)
        ax2.set_title('Trade Frequency Range (Min-Max)', fontweight='bold')
        ax2.set_ylabel('Number of Trades')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(strategies)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'trade_frequency_analysis.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        return os.path.join(self.output_dir, 'trade_frequency_analysis.png')
    
    def create_risk_return_scatter(self):
        """Create risk-return scatter plot"""
        plt.figure(figsize=(10, 8))
        
        colors = ['red', 'blue', 'green']
        markers = ['o', 's', '^']
        
        strategy_idx = 0
        for strategy_name, strategy_data in self.results.items():
            returns = []
            drawdowns = []
            labels = []
            
            if strategy_name == 'Value_Factor_Portfolio':
                returns.append(strategy_data['PORTFOLIO']['total_return_pct'])
                drawdowns.append(strategy_data['PORTFOLIO']['max_drawdown_pct'])
                labels.append('Portfolio')
            else:
                for stock, data in strategy_data.items():
                    returns.append(data['total_return_pct'])
                    drawdowns.append(data['max_drawdown_pct'])
                    labels.append(f"{strategy_name.split('_')[0]}_{stock}")
            
            plt.scatter(drawdowns, returns, 
                       c=colors[strategy_idx], 
                       marker=markers[strategy_idx],
                       s=100, 
                       alpha=0.7,
                       label=strategy_name.replace('_', ' '))
            strategy_idx += 1
        
        plt.xlabel('Maximum Drawdown (%)', fontweight='bold')
        plt.ylabel('Total Return (%)', fontweight='bold')
        plt.title('Risk-Return Analysis - Sprint #1', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Add quadrant lines
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        plt.axvline(x=10, color='red', linestyle='--', alpha=0.5, label='10% DD Threshold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'risk_return_scatter.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        return os.path.join(self.output_dir, 'risk_return_scatter.png')
    
    def generate_summary_report(self):
        """Generate summary visualization report"""
        report_paths = []
        
        print("Generating performance visualizations...")
        
        # Generate all charts
        report_paths.append(self.create_strategy_comparison_chart())
        print("✅ Strategy comparison chart created")
        
        report_paths.append(self.create_stock_performance_heatmap())
        print("✅ Stock performance heatmap created")
        
        report_paths.append(self.create_trade_frequency_analysis())
        print("✅ Trade frequency analysis created")
        
        report_paths.append(self.create_risk_return_scatter())
        print("✅ Risk-return scatter plot created")
        
        # Create summary report
        summary = {
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'charts_generated': report_paths,
            'total_strategies_analyzed': len(self.results),
            'visualization_directory': self.output_dir
        }
        
        summary_file = os.path.join(self.output_dir, 'visualization_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📊 All visualizations saved to: {self.output_dir}")
        print(f"📋 Summary report: {summary_file}")
        
        return summary

if __name__ == '__main__':
    # Use the results from our earlier analysis
    results_file = 'results/sprint_1/sprint_1_analysis_20250725_003208.json'
    
    if os.path.exists(results_file):
        visualizer = PerformanceVisualizer(results_file)
        summary = visualizer.generate_summary_report()
        print("\n🎯 Performance visualization complete!")
    else:
        print(f"❌ Results file not found: {results_file}")
        print("Please run the sprint_1_results_analyzer.py first.")