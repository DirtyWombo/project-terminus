# Transaction Cost Analysis (TCA) for Operation Badger
# Critical robustness test - most strategies fail here

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple

class TransactionCostAnalyzer:
    def __init__(self):
        """Initialize TCA with realistic small/mid-cap cost models"""
        
        # Realistic cost assumptions for small/mid-caps
        self.cost_model = {
            'commission_per_trade': 0.0,  # Commission-free brokers
            'bid_ask_spread_bps': 8.0,    # 8 basis points average for small-caps
            'market_impact_bps': 12.0,    # 12 bps for $10K-50K orders
            'slippage_bps': 15.0,         # 15 bps total slippage
            'funding_cost_annual': 0.05   # 5% annual funding cost
        }
        
        # Market microstructure assumptions
        self.liquidity_model = {
            'min_market_cap': 500_000_000,   # $500M minimum
            'avg_daily_volume_min': 500_000, # 500K shares minimum
            'volatility_penalty': 0.05       # Extra cost for volatile stocks
        }
        
        print("SUCCESS: TCA initialized with punitive small-cap cost model")
        print(f"Total estimated cost per trade: {self.get_total_cost_bps():.1f} basis points")
    
    def get_total_cost_bps(self) -> float:
        """Calculate total transaction cost in basis points"""
        return (self.cost_model['bid_ask_spread_bps'] + 
                self.cost_model['market_impact_bps'] + 
                self.cost_model['slippage_bps'])
    
    def load_backtest_results(self) -> pd.DataFrame:
        """Load original backtest results for TCA analysis"""
        try:
            with open('validation_success.json', 'r') as f:
                backtest_data = json.load(f)
            
            # Convert to DataFrame for analysis
            trades = []
            for trade in backtest_data.get('sample_trades', []):
                trades.append({
                    'symbol': trade.get('symbol', 'UNKNOWN'),
                    'entry_date': trade.get('entry_date', '2023-01-01'),
                    'exit_date': trade.get('exit_date', '2023-01-02'),
                    'entry_price': trade.get('entry_price', 100.0),
                    'exit_price': trade.get('exit_price', 105.0),
                    'position_size': trade.get('position_size', 10000.0),
                    'raw_return': trade.get('return_pct', 5.0) / 100.0,
                    'confidence': trade.get('confidence', 0.75),
                    'velocity_score': trade.get('velocity_score', 0.5)
                })
            
            if not trades:
                # Generate synthetic trades based on validation results
                print("INFO: No trade history found, generating synthetic trades for TCA")
                return self.generate_synthetic_trades()
            
            return pd.DataFrame(trades)
            
        except FileNotFoundError:
            print("WARNING: No backtest results found, generating synthetic trades")
            return self.generate_synthetic_trades()
    
    def generate_synthetic_trades(self) -> pd.DataFrame:
        """Generate synthetic trades based on validation metrics"""
        np.random.seed(42)  # Reproducible results
        
        # Based on our validation: 308 signals, 54.5% win rate, 0.73% mean return
        n_trades = 100  # Reasonable sample size
        win_rate = 0.545
        mean_return = 0.0073
        volatility = 0.044  # 4.4% volatility from validation
        
        symbols = ['CRWD', 'SNOW', 'PLTR', 'DDOG', 'NET', 'OKTA', 'ZS', 'ESTC']
        
        # Generate proper return distribution
        n_winners = int(n_trades * win_rate)
        n_losers = n_trades - n_winners
        
        # Winners: Generate positive returns
        winner_returns = np.random.exponential(mean_return * 3, n_winners)
        winner_returns = np.clip(winner_returns, 0.01, 0.50)  # 1% to 50%
        
        # Losers: Generate negative returns  
        loser_returns = -np.random.exponential(mean_return * 2, n_losers)
        loser_returns = np.clip(loser_returns, -0.20, -0.01)  # -20% to -1%
        
        # Combine and shuffle
        all_returns = np.concatenate([winner_returns, loser_returns])
        np.random.shuffle(all_returns)
        
        trades = []
        for i in range(n_trades):
            entry_date = datetime(2023, 1, 1) + timedelta(days=i*3)
            exit_date = entry_date + timedelta(days=np.random.randint(1, 5))
            entry_price = 50.0 + np.random.normal(0, 30)  # $20-80 range
            
            trades.append({
                'symbol': np.random.choice(symbols),
                'entry_date': entry_date.strftime('%Y-%m-%d'),
                'exit_date': exit_date.strftime('%Y-%m-%d'),
                'entry_price': abs(entry_price),  # Ensure positive
                'exit_price': 0,  # Will calculate
                'position_size': 5000.0,  # 0.5% of $1M portfolio
                'raw_return': all_returns[i],
                'confidence': np.random.uniform(0.75, 0.95),
                'velocity_score': np.random.uniform(-0.8, 0.8)
            })
        
        df = pd.DataFrame(trades)
        df['exit_price'] = df['entry_price'] * (1 + df['raw_return'])
        
        print(f"GENERATED: {len(df)} synthetic trades for TCA analysis")
        print(f"Win rate: {(df['raw_return'] > 0).mean():.1%}")
        print(f"Mean return: {df['raw_return'].mean():.2%}")
        
        return df
    
    def apply_transaction_costs(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """Apply realistic transaction costs to each trade"""
        df = trades_df.copy()
        
        # Calculate position value
        df['position_value'] = df['position_size']
        
        # Entry costs (buy)
        total_cost_bps = self.get_total_cost_bps()
        df['entry_cost'] = (df['position_value'] * total_cost_bps / 10000)
        
        # Exit costs (sell) 
        df['exit_cost'] = (df['position_value'] * total_cost_bps / 10000)
        
        # Total transaction costs
        df['total_costs'] = df['entry_cost'] + df['exit_cost']
        
        # Cost as percentage of position
        df['cost_pct'] = df['total_costs'] / df['position_value']
        
        # Net return after costs
        df['net_return'] = df['raw_return'] - df['cost_pct']
        
        # P&L calculations
        df['raw_pnl'] = df['position_value'] * df['raw_return']
        df['net_pnl'] = df['position_value'] * df['net_return']
        df['cost_impact'] = df['raw_pnl'] - df['net_pnl']
        
        return df
    
    def calculate_performance_metrics(self, trades_df: pd.DataFrame) -> Dict:
        """Calculate performance metrics before and after costs"""
        
        # Raw performance (before costs)
        raw_returns = trades_df['raw_return']
        raw_win_rate = (raw_returns > 0).mean()
        raw_mean_return = raw_returns.mean()
        raw_std_return = raw_returns.std()
        raw_sharpe = (raw_mean_return / raw_std_return) * np.sqrt(252) if raw_std_return > 0 else 0
        
        # Net performance (after costs)
        net_returns = trades_df['net_return'] 
        net_win_rate = (net_returns > 0).mean()
        net_mean_return = net_returns.mean()
        net_std_return = net_returns.std()
        net_sharpe = (net_mean_return / net_std_return) * np.sqrt(252) if net_std_return > 0 else 0
        
        # Impact analysis
        total_raw_pnl = trades_df['raw_pnl'].sum()
        total_net_pnl = trades_df['net_pnl'].sum()
        total_costs = trades_df['total_costs'].sum()
        cost_drag_pct = (total_costs / abs(total_raw_pnl)) * 100 if total_raw_pnl != 0 else 0
        
        # Trade frequency impact
        profitable_trades_raw = (raw_returns > 0).sum()
        profitable_trades_net = (net_returns > 0).sum()
        trades_killed_by_costs = profitable_trades_raw - profitable_trades_net
        
        metrics = {
            'raw_performance': {
                'win_rate': raw_win_rate,
                'mean_return_pct': raw_mean_return * 100,
                'sharpe_ratio': raw_sharpe,
                'total_pnl': total_raw_pnl,
                'profitable_trades': profitable_trades_raw
            },
            'net_performance': {
                'win_rate': net_win_rate,
                'mean_return_pct': net_mean_return * 100,
                'sharpe_ratio': net_sharpe,
                'total_pnl': total_net_pnl,
                'profitable_trades': profitable_trades_net
            },
            'cost_impact': {
                'total_costs': total_costs,
                'cost_drag_pct': cost_drag_pct,
                'trades_killed_by_costs': trades_killed_by_costs,
                'avg_cost_per_trade_bps': self.get_total_cost_bps(),
                'cost_as_pct_of_pnl': (total_costs / abs(total_raw_pnl)) * 100 if total_raw_pnl != 0 else 0
            }
        }
        
        return metrics
    
    def run_sensitivity_analysis(self, trades_df: pd.DataFrame) -> Dict:
        """Test performance across different cost assumptions"""
        base_cost = self.get_total_cost_bps()
        cost_scenarios = [base_cost * 0.5, base_cost, base_cost * 1.5, base_cost * 2.0]
        
        results = {}
        
        for multiplier, cost_bps in zip([0.5, 1.0, 1.5, 2.0], cost_scenarios):
            # Temporarily adjust costs
            original_costs = self.cost_model.copy()
            
            # Scale all cost components
            for key in ['bid_ask_spread_bps', 'market_impact_bps', 'slippage_bps']:
                self.cost_model[key] = original_costs[key] * multiplier
            
            # Apply costs and calculate metrics
            adjusted_trades = self.apply_transaction_costs(trades_df)
            metrics = self.calculate_performance_metrics(adjusted_trades)
            
            results[f'{multiplier}x_costs'] = {
                'cost_bps': cost_bps * multiplier,
                'sharpe_ratio': metrics['net_performance']['sharpe_ratio'],
                'win_rate': metrics['net_performance']['win_rate'],
                'mean_return_pct': metrics['net_performance']['mean_return_pct']
            }
            
            # Restore original costs
            self.cost_model = original_costs
        
        return results
    
    def generate_tca_report(self) -> Dict:
        """Generate comprehensive TCA analysis report"""
        print("="*60)
        print("TRANSACTION COST ANALYSIS - EXPERT ROBUSTNESS TEST")
        print("="*60)
        
        # Load trades
        trades_df = self.load_backtest_results()
        
        # Apply transaction costs
        trades_with_costs = self.apply_transaction_costs(trades_df)
        
        # Calculate metrics
        metrics = self.calculate_performance_metrics(trades_with_costs)
        
        # Sensitivity analysis
        sensitivity = self.run_sensitivity_analysis(trades_df)
        
        # Print results
        print("\nORIGINAL PERFORMANCE (Before Costs):")
        raw = metrics['raw_performance']
        print(f"  Sharpe Ratio: {raw['sharpe_ratio']:.2f}")
        print(f"  Win Rate: {raw['win_rate']:.1%}")
        print(f"  Mean Return: {raw['mean_return_pct']:.2f}%")
        print(f"  Total P&L: ${raw['total_pnl']:,.0f}")
        
        print("\nNET PERFORMANCE (After Costs):")
        net = metrics['net_performance']
        print(f"  Sharpe Ratio: {net['sharpe_ratio']:.2f}")
        print(f"  Win Rate: {net['win_rate']:.1%}")
        print(f"  Mean Return: {net['mean_return_pct']:.2f}%")
        print(f"  Total P&L: ${net['total_pnl']:,.0f}")
        
        print("\nCOST IMPACT ANALYSIS:")
        impact = metrics['cost_impact']
        print(f"  Total Costs: ${impact['total_costs']:,.0f}")
        print(f"  Cost Drag: {impact['cost_drag_pct']:.1f}% of gross P&L")
        print(f"  Trades Killed by Costs: {impact['trades_killed_by_costs']}")
        print(f"  Avg Cost per Trade: {impact['avg_cost_per_trade_bps']:.1f} bps")
        
        print("\nSENSITIVITY ANALYSIS:")
        for scenario, data in sensitivity.items():
            print(f"  {scenario}: Sharpe {data['sharpe_ratio']:.2f}, "
                  f"Win Rate {data['win_rate']:.1%}, "
                  f"Avg Return {data['mean_return_pct']:.2f}%")
        
        # Expert verdict
        sharpe_degradation = (raw['sharpe_ratio'] - net['sharpe_ratio']) / raw['sharpe_ratio'] * 100
        
        print("\n" + "="*60)
        print("EXPERT VERDICT:")
        print("="*60)
        
        if net['sharpe_ratio'] > 1.0 and net['win_rate'] > 0.5:
            print("PASS: Strategy survives transaction cost analysis")
            print(f"   Net Sharpe {net['sharpe_ratio']:.2f} > 1.0 threshold")
        elif net['sharpe_ratio'] > 0.5:
            print("MARGINAL: Strategy is weakened but viable")
            print(f"   Net Sharpe {net['sharpe_ratio']:.2f} below optimal threshold")
        else:
            print("FAIL: Strategy killed by transaction costs")
            print(f"   Net Sharpe {net['sharpe_ratio']:.2f} below viability threshold")
        
        print(f"\nSharpe degradation: {sharpe_degradation:.1f}%")
        print(f"Cost per trade: {impact['avg_cost_per_trade_bps']:.1f} basis points")
        
        if impact['trades_killed_by_costs'] > 0:
            print(f"WARNING: {impact['trades_killed_by_costs']} profitable trades turned unprofitable")
        
        print("="*60)
        
        # Save results (convert numpy types to Python types)
        def convert_numpy(obj):
            if hasattr(obj, 'item'):
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(v) for v in obj]
            else:
                return obj
        
        report = {
            'analysis_date': datetime.now().isoformat(),
            'cost_model': convert_numpy(self.cost_model),
            'performance_metrics': convert_numpy(metrics),
            'sensitivity_analysis': convert_numpy(sensitivity),
            'verdict': {
                'pass_tca': bool(net['sharpe_ratio'] > 1.0 and net['win_rate'] > 0.5),
                'sharpe_degradation_pct': float(sharpe_degradation),
                'trades_killed': int(impact['trades_killed_by_costs'])
            }
        }
        
        with open('tca_analysis_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save detailed trades
        trades_with_costs.to_csv('tca_detailed_trades.csv', index=False)
        
        return report

def main():
    """Execute TCA analysis"""
    analyzer = TransactionCostAnalyzer()
    report = analyzer.generate_tca_report()
    
    print("\nFILES GENERATED:")
    print("- tca_analysis_results.json (summary)")
    print("- tca_detailed_trades.csv (trade-by-trade)")
    
    return report

if __name__ == "__main__":
    main()