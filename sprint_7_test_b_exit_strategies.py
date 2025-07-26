#!/usr/bin/env python3
"""
Sprint 7 Test B: Exit Strategy Optimization
Test profit target and trailing stop exits with best parameters from Test A
"""

import backtrader as bt
import pandas as pd
import json
import os
from datetime import datetime

# Import the transaction cost model
from rsi_optimization_backtest import RealisticTransactionCosts

class RSIExitStrategyTester(bt.Strategy):
    """
    RSI Strategy with configurable exit strategies for Test B
    """
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 35), 
        ('rsi_overbought', 75),
        ('exit_strategy', 'rsi'),  # 'rsi', 'profit_target', 'trailing_stop'
        ('profit_target_pct', 4.0),  # 2x initial risk (2% stop = 4% target)
        ('stop_loss_pct', 2.0),      # Initial stop loss
        ('trailing_stop_pct', 1.5),  # Trailing stop percentage
        ('trailing_trigger_pct', 2.0), # Profit % to trigger trailing stop
        ('cost_model', None)
    )
    
    def __init__(self):
        self.rsi = bt.indicators.RelativeStrengthIndex(period=self.p.rsi_period)
        self.position_entry_price = 0
        self.trailing_stop_price = 0
        self.trailing_active = False
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.total_profit = 0
        self.trade_results = []
        
    def next(self):
        current_rsi = self.rsi[0] 
        current_price = self.data.close[0]
        
        # Entry Logic: RSI oversold
        if current_rsi < self.p.rsi_oversold and not self.position:
            order = self.buy()
            if order:
                self.position_entry_price = current_price
                self.trailing_active = False
                
        # Exit Logic: Based on strategy type
        elif self.position:
            self._handle_exit_logic(current_price, current_rsi)
    
    def _handle_exit_logic(self, current_price, current_rsi):
        """Handle different exit strategies"""
        entry_price = self.position_entry_price
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        if self.p.exit_strategy == 'rsi':
            # Original RSI exit
            if current_rsi > self.p.rsi_overbought:
                self.close()
            elif pnl_pct <= -self.p.stop_loss_pct:
                self.close()
                
        elif self.p.exit_strategy == 'profit_target':
            # Profit target exit
            if pnl_pct >= self.p.profit_target_pct:
                self.close()
            elif pnl_pct <= -self.p.stop_loss_pct:
                self.close()
                
        elif self.p.exit_strategy == 'trailing_stop':
            # Trailing stop exit
            if pnl_pct >= self.p.trailing_trigger_pct and not self.trailing_active:
                # Activate trailing stop
                self.trailing_stop_price = current_price * (1 - self.p.trailing_stop_pct/100)
                self.trailing_active = True
                
            if self.trailing_active:
                # Update trailing stop if price moved up
                new_stop = current_price * (1 - self.p.trailing_stop_pct/100)
                if new_stop > self.trailing_stop_price:
                    self.trailing_stop_price = new_stop
                
                # Exit if price hits trailing stop
                if current_price <= self.trailing_stop_price:
                    self.close()
            
            # Regular stop loss if trailing not active
            elif pnl_pct <= -self.p.stop_loss_pct:
                self.close()
    
    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_count += 1
            self.total_profit += trade.pnl
            self.trade_results.append(trade.pnl)
            if trade.pnl > 0:
                self.winning_trades += 1

def run_exit_strategy_test(ticker, exit_strategy, params):
    """Run backtest with specific exit strategy"""
    
    # Load data
    data_path = f"data/sprint_1/{ticker}.csv"
    if not os.path.exists(data_path):
        return None
    
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')
    
    # Create data feed
    data_feed = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open='Open',
        high='High',
        low='Low', 
        close='Close',
        volume='Volume',
        openinterest=None
    )
    
    # Setup cerebro
    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed, name=ticker)
    
    # Add strategy with parameters
    cerebro.addstrategy(
        RSIExitStrategyTester,
        rsi_period=params['rsi_period'],
        rsi_oversold=params['oversold_level'],
        rsi_overbought=params['overbought_level'],
        exit_strategy=exit_strategy,
        cost_model=RealisticTransactionCosts()
    )
    
    # Set initial capital
    cerebro.broker.setcash(10000)
    
    # Run backtest
    initial_value = cerebro.broker.getvalue()
    strategies = cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    strategy = strategies[0]
    
    # Calculate metrics
    total_return = (final_value - initial_value) / initial_value
    total_trades = strategy.trade_count
    win_rate = (strategy.winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate Sharpe ratio (simplified)
    if len(strategy.trade_results) > 1:
        import numpy as np
        returns = np.array(strategy.trade_results)
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        sharpe = (avg_return / std_return) if std_return > 0 else 0
    else:
        sharpe = 0
    
    # Calculate transaction costs
    cost_model = RealisticTransactionCosts()
    avg_trade_value = initial_value * 0.5  # Assume 50% position size
    cost_breakdown = cost_model.calculate_total_cost(avg_trade_value)
    cost_per_trade = cost_breakdown['total_cost']
    total_costs = total_trades * 2 * cost_per_trade  # Buy + sell
    
    return {
        'ticker': ticker,
        'exit_strategy': exit_strategy,
        'total_return_pct': total_return,
        'sharpe_ratio': sharpe,
        'win_rate_pct': win_rate,
        'total_trades': total_trades,
        'final_value': final_value,
        'total_costs_usd': total_costs,
        'cost_impact_pct': total_costs / initial_value
    }

def main():
    """Run Test B: Exit Strategy Optimization"""
    
    print("=" * 80)
    print("SPRINT 7 TEST B: EXIT STRATEGY OPTIMIZATION")
    print("=" * 80)
    
    # Load best parameters from Test A
    try:
        with open('sprint_7_test_b_params.json', 'r') as f:
            best_params = json.load(f)
    except FileNotFoundError:
        print("Error: sprint_7_test_b_params.json not found. Run Test A analysis first.")
        return
    
    print(f"Using optimized parameters from Test A:")
    print(f"  RSI Period: {best_params['rsi_period']}")
    print(f"  Oversold Level: {best_params['oversold_level']}")
    print(f"  Overbought Level: {best_params['overbought_level']}")
    
    # Test on best performing stock (ZS) and a few others
    test_stocks = ['ZS', 'CRWD', 'U']  # Best performers from Test A
    exit_strategies = ['rsi', 'profit_target', 'trailing_stop']
    
    results = []
    
    for ticker in test_stocks:
        print(f"\nTesting {ticker}...")
        
        for exit_strategy in exit_strategies:
            print(f"  Running {exit_strategy} exit strategy...")
            
            result = run_exit_strategy_test(ticker, exit_strategy, best_params)
            if result:
                results.append(result)
    
    # Create results summary
    if results:
        print("\n" + "=" * 80)
        print("TEST B RESULTS SUMMARY")
        print("=" * 80)
        
        # Group by exit strategy
        for strategy in exit_strategies:
            strategy_results = [r for r in results if r['exit_strategy'] == strategy]
            
            if strategy_results:
                avg_return = sum(r['total_return_pct'] for r in strategy_results) / len(strategy_results)
                avg_sharpe = sum(r['sharpe_ratio'] for r in strategy_results) / len(strategy_results)
                avg_win_rate = sum(r['win_rate_pct'] for r in strategy_results) / len(strategy_results)
                avg_trades = sum(r['total_trades'] for r in strategy_results) / len(strategy_results)
                
                print(f"\n{strategy.upper()} EXIT STRATEGY:")
                print(f"  Average Return: {avg_return*100:.1f}%")
                print(f"  Average Sharpe: {avg_sharpe:.2f}")
                print(f"  Average Win Rate: {avg_win_rate:.1f}%")
                print(f"  Average Trades: {avg_trades:.1f}")
                
                # Show individual stock results
                for result in strategy_results:
                    print(f"    {result['ticker']}: {result['total_return_pct']*100:6.1f}% return, "
                          f"{result['sharpe_ratio']:6.2f} Sharpe, {result['win_rate_pct']:5.1f}% win rate")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"results/sprint_7_rsi_optimization/test_b_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                'test': 'Sprint #7 Test B - Exit Strategy Optimization',
                'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'base_parameters': best_params,
                'exit_strategies_tested': exit_strategies,
                'test_stocks': test_stocks,
                'results': results
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
        # Determine best exit strategy
        strategy_performance = {}
        for strategy in exit_strategies:
            strategy_results = [r for r in results if r['exit_strategy'] == strategy]
            if strategy_results:
                avg_sharpe = sum(r['sharpe_ratio'] for r in strategy_results) / len(strategy_results)
                strategy_performance[strategy] = avg_sharpe
        
        if strategy_performance:
            best_exit = max(strategy_performance, key=strategy_performance.get)
            best_sharpe = strategy_performance[best_exit]
            
            print(f"\n" + "=" * 60)
            print("FINAL RECOMMENDATION")
            print("=" * 60)
            print(f"Best exit strategy: {best_exit.upper()}")
            print(f"Best average Sharpe ratio: {best_sharpe:.2f}")
            
            if best_sharpe > 1.0:
                print("SUCCESS: Strategy meets Sharpe ratio target!")
            else:
                print("Strategy still below target Sharpe ratio of 1.0")

if __name__ == "__main__":
    main()