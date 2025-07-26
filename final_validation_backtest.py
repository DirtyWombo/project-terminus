# final_validation_backtest.py
import backtrader as bt
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from enhanced_value_portfolio import RiskManagedValuePortfolio, RealisticTransactionCosts, EnhancedCommissionInfo

def run_final_validation():
    """
    Run the final validation backtest with all risk controls AND transaction costs
    
    This is the definitive test to validate our success criteria:
    1. Max Drawdown < 25%
    2. Post-Cost Return > 25% annualized
    """
    
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/week_2_risk_management'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    print("=" * 80)
    print("FINAL VALIDATION BACKTEST - WEEK 2")
    print("=" * 80)
    print("Testing Value Portfolio with FULL risk management + transaction costs")
    print("\nSuccess Criteria:")
    print("- Max Drawdown < 25%")
    print("- Post-Cost Annualized Return > 25%")
    print("\nRisk Controls Enabled:")
    print("- Portfolio Stop-Loss: 25% drawdown limit")
    print("- Position Concentration: 30% maximum per stock")
    print("- Transaction Costs: Mid-cap realistic model")
    print("=" * 80)
    
    # Create cost model
    cost_model = RealisticTransactionCosts('mid_cap')
    
    # Initialize Cerebro
    cerebro = bt.Cerebro(stdstats=False)
    
    # Add data for all stocks
    data_loaded = 0
    for ticker in UNIVERSE:
        data_path = os.path.join(DATA_DIR, f'{ticker}.csv')
        if os.path.exists(data_path):
            df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
            cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
            data_loaded += 1
            print(f"Loaded data for {ticker}")
    
    print(f"\nData loaded for {data_loaded} stocks")
    
    # Strategy parameters - optimized configuration from Sprint #2
    strategy_params = {
        'num_positions': 2,                # Risk parity works best with 2 stocks
        'rebalance_freq': 'quarterly',     # Cost-efficient rebalancing
        'position_sizing': 'risk_parity',  # Risk-managed position sizing
        'portfolio_stop_loss': 0.25,      # 25% portfolio drawdown limit
        'max_position_weight': 0.30,      # 30% concentration limit per stock
    }
    
    # Add strategy
    cerebro.addstrategy(RiskManagedValuePortfolio, cost_model=cost_model, **strategy_params)
    
    # Set initial cash
    initial_cash = 100000
    cerebro.broker.setcash(initial_cash)
    
    # Add enhanced commission model with realistic transaction costs
    commission_info = EnhancedCommissionInfo(cost_model)
    cerebro.broker.addcommissioninfo(commission_info)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    
    print(f"\nRunning final validation backtest...")
    print(f"Initial Capital: ${initial_cash:,.2f}")
    
    # Run backtest
    results = cerebro.run()
    strategy = results[0]
    
    # Get performance metrics
    performance = strategy.get_performance_metrics()
    
    # Get analyzer results
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
    trade_analysis = strategy.analyzers.trades.get_analysis()
    sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
    
    # Calculate transaction costs
    if hasattr(commission_info, 'trade_log'):
        total_costs = sum([trade['cost_breakdown']['total_cost'] 
                          for trade in commission_info.trade_log])
        cost_breakdown = {}
        for cost_type in ['commission', 'spread_cost', 'slippage', 'market_impact', 'timing_cost']:
            cost_breakdown[cost_type] = sum([trade['cost_breakdown'][cost_type] 
                                           for trade in commission_info.trade_log])
    else:
        total_costs = 0
        cost_breakdown = {}
    
    # Compile comprehensive results
    final_results = {
        'validation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'strategy_config': strategy_params,
        'universe': UNIVERSE,
        'data_period': '2018-2023 (6 years)',
        'initial_cash': initial_cash,
        
        # Core Performance Metrics
        'performance': {
            'final_value': performance['final_value'],
            'total_return_pct': performance['total_return_pct'],
            'annualized_return_pct': performance['annualized_return_pct'],
            'max_drawdown_pct': performance['max_drawdown_pct'],
            'sharpe_ratio': sharpe_analysis.get('sharperatio', 0) if sharpe_analysis else 0,
        },
        
        # Transaction Cost Analysis
        'transaction_costs': {
            'total_costs_usd': total_costs,
            'cost_impact_pct': (total_costs / initial_cash) * 100,
            'cost_breakdown_usd': cost_breakdown,
            'cost_per_rebalance': total_costs / max(1, performance.get('rebalance_count', 1)),
            'cost_model_params': cost_model.params
        },
        
        # Risk Management Results
        'risk_management': {
            'portfolio_stop_loss_triggered': performance.get('portfolio_stopped_out', False),
            'stop_loss_date': performance.get('stop_loss_date'),
            'max_drawdown_vs_limit': {
                'actual_max_drawdown_pct': performance['max_drawdown_pct'],
                'drawdown_limit_pct': 25.0,
                'within_limit': performance['max_drawdown_pct'] <= 25.0
            },
            'position_concentration': {
                'max_position_weight_limit': 30.0,
                'concentration_controls_active': True
            }
        },
        
        # Trade Analysis
        'trading_activity': {
            'total_trades': trade_analysis.get('total', {}).get('total', 0),
            'winning_trades': trade_analysis.get('won', {}).get('total', 0),
            'losing_trades': trade_analysis.get('lost', {}).get('total', 0),
            'win_rate_pct': (trade_analysis.get('won', {}).get('total', 0) / 
                           max(1, trade_analysis.get('total', {}).get('total', 1))) * 100,
            'rebalance_count': performance.get('rebalance_count', 0),
            'avg_trades_per_rebalance': (trade_analysis.get('total', {}).get('total', 0) / 
                                       max(1, performance.get('rebalance_count', 1)))
        },
        
        # Success Criteria Validation
        'success_criteria': {
            'criterion_1_max_drawdown': {
                'target': 'Max Drawdown < 25%',
                'actual': f"{performance['max_drawdown_pct']:.1f}%",
                'achieved': performance['max_drawdown_pct'] < 25.0,
                'status': 'PASS' if performance['max_drawdown_pct'] < 25.0 else 'FAIL'
            },
            'criterion_2_post_cost_return': {
                'target': 'Post-Cost Annualized Return > 25%',
                'actual': f"{performance['annualized_return_pct']:.1f}%",
                'achieved': performance['annualized_return_pct'] > 25.0,
                'status': 'PASS' if performance['annualized_return_pct'] > 25.0 else 'FAIL'
            },
            'overall_validation': {
                'both_criteria_met': (performance['max_drawdown_pct'] < 25.0 and 
                                    performance['annualized_return_pct'] > 25.0),
                'deployment_ready': (performance['max_drawdown_pct'] < 25.0 and 
                                   performance['annualized_return_pct'] > 25.0)
            }
        }
    }
    
    # Print detailed results
    print("\n" + "=" * 80)
    print("FINAL VALIDATION RESULTS")
    print("=" * 80)
    
    print(f"\nPERFORMANCE SUMMARY:")
    print(f"Final Portfolio Value: ${performance['final_value']:,.2f}")
    print(f"Total Return: {performance['total_return_pct']:.1f}%")
    print(f"Annualized Return: {performance['annualized_return_pct']:.1f}%")
    print(f"Max Drawdown: {performance['max_drawdown_pct']:.1f}%")
    if sharpe_analysis:
        print(f"Sharpe Ratio: {sharpe_analysis.get('sharperatio', 0):.2f}")
    
    print(f"\nTRANSACTION COST ANALYSIS:")
    print(f"Total Transaction Costs: ${total_costs:,.2f}")
    print(f"Cost Impact: {(total_costs / initial_cash) * 100:.2f}% of capital")
    print(f"Cost per Rebalance: ${total_costs / max(1, performance.get('rebalance_count', 1)):,.2f}")
    
    if cost_breakdown:
        print(f"Cost Breakdown:")
        for cost_type, amount in cost_breakdown.items():
            print(f"  - {cost_type.replace('_', ' ').title()}: ${amount:.2f}")
    
    print(f"\nRISK MANAGEMENT STATUS:")
    print(f"Portfolio Stop-Loss Triggered: {performance.get('portfolio_stopped_out', False)}")
    if performance.get('stop_loss_date'):
        print(f"Stop-Loss Date: {performance.get('stop_loss_date')}")
    print(f"Max Position Concentration: 30% (enforced)")
    
    print(f"\nTRADING ACTIVITY:")
    print(f"Total Trades: {trade_analysis.get('total', {}).get('total', 0)}")
    print(f"Win Rate: {(trade_analysis.get('won', {}).get('total', 0) / max(1, trade_analysis.get('total', {}).get('total', 1))) * 100:.1f}%")
    print(f"Rebalances: {performance.get('rebalance_count', 0)}")
    
    print(f"\nSUCCESS CRITERIA VALIDATION:")
    print(f"Criterion 1 - Max Drawdown < 25%:")
    print(f"  - Target: < 25.0%")
    print(f"  - Actual: {performance['max_drawdown_pct']:.1f}%")
    print(f"  - Status: {'PASS' if performance['max_drawdown_pct'] < 25.0 else 'FAIL'}")
    
    print(f"\nCriterion 2 - Post-Cost Return > 25% annualized:")
    print(f"  - Target: > 25.0%")
    print(f"  - Actual: {performance['annualized_return_pct']:.1f}%")
    print(f"  - Status: {'PASS' if performance['annualized_return_pct'] > 25.0 else 'FAIL'}")
    
    overall_pass = (performance['max_drawdown_pct'] < 25.0 and 
                   performance['annualized_return_pct'] > 25.0)
    
    print(f"\nOVERALL VALIDATION:")
    print(f"Both Criteria Met: {'YES' if overall_pass else 'NO'}")
    print(f"Deployment Ready: {'YES' if overall_pass else 'NO'}")
    
    if overall_pass:
        print(f"\nSUCCESS! Strategy meets all deployment criteria.")
    else:
        print(f"\nStrategy does not meet deployment criteria.")
        if performance['max_drawdown_pct'] >= 25.0:
            print(f"   - Max drawdown ({performance['max_drawdown_pct']:.1f}%) exceeds 25% limit")
        if performance['annualized_return_pct'] <= 25.0:
            print(f"   - Annualized return ({performance['annualized_return_pct']:.1f}%) below 25% minimum")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f'final_validation_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {results_file}")
    print("=" * 80)
    
    return results_file, final_results

if __name__ == '__main__':
    results_file, results = run_final_validation()