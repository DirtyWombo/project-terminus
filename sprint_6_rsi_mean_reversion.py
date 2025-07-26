# sprint_6_rsi_mean_reversion.py
# Sprint #6 Test A: RSI Mean Reversion Strategy

import backtrader as bt
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

class RealisticTransactionCosts:
    """
    Validated transaction cost model (confirmed accurate)
    """
    
    def __init__(self, stock_tier='mid_cap'):
        self.stock_tier = stock_tier
        
        # Mid-cap cost parameters (validated as accurate)
        self.cost_params = {
            'mid_cap': {
                'base_commission': 0.0005,      # 5 bps base commission  
                'bid_ask_spread': 0.0025,       # 25 bps average spread
                'slippage_factor': 0.0015,      # 15 bps base slippage
                'market_impact_factor': 0.00005, # Moderate impact
                'liquidity_threshold': 100000    # $100K+ daily volume
            }
        }
        
        self.params = self.cost_params[stock_tier]
    
    def calculate_total_cost(self, trade_value, volatility=0.025, volume_ratio=0.01):
        """
        Calculate total transaction cost for a trade
        (Model validated as accurate in Post-Mortem analysis)
        """
        
        # 1. Base Commission (fixed)
        commission = abs(trade_value) * self.params['base_commission']
        
        # 2. Bid-Ask Spread Cost (always paid)
        spread_cost = abs(trade_value) * self.params['bid_ask_spread']
        
        # 3. Slippage (volatility and urgency dependent)
        volatility_multiplier = max(1.0, volatility / 0.025)
        slippage = abs(trade_value) * self.params['slippage_factor'] * volatility_multiplier
        
        # 4. Market Impact (size and liquidity dependent)
        impact_multiplier = min(5.0, max(1.0, volume_ratio / 0.01))
        market_impact = abs(trade_value) * self.params['market_impact_factor'] * impact_multiplier
        
        # 5. Timing Cost (random component)
        timing_cost = abs(trade_value) * np.random.normal(0, 0.0005)
        timing_cost = abs(timing_cost)
        
        total_cost = commission + spread_cost + slippage + market_impact + timing_cost
        
        return {
            'commission': commission,
            'spread_cost': spread_cost,
            'slippage': slippage,
            'market_impact': market_impact,
            'timing_cost': timing_cost,
            'total_cost': total_cost,
            'cost_bps': (total_cost / abs(trade_value)) * 10000
        }

class EnhancedCommissionInfo(bt.CommInfoBase):
    """
    Enhanced commission model with validated transaction costs
    """
    
    def __init__(self, cost_model):
        super().__init__()
        self.cost_model = cost_model
        self.trade_log = []
    
    def _getcommission(self, size, price, pseudoexec):
        """
        Calculate realistic commission for growth stocks
        """
        trade_value = abs(size * price)
        
        # Growth stock assumptions
        volatility = 0.035  # 3.5% daily volatility for growth stocks
        volume_ratio = min(0.02, trade_value / 50000)
        
        cost_breakdown = self.cost_model.calculate_total_cost(
            trade_value, volatility, volume_ratio
        )
        
        self.trade_log.append({
            'trade_value': trade_value,
            'size': size,
            'price': price,
            'cost_breakdown': cost_breakdown
        })
        
        return cost_breakdown['total_cost']

class RSIMeanReversionStrategy(bt.Strategy):
    """
    RSI Mean Reversion Strategy
    
    Entry Rules:
    1. RSI drops below 30 (oversold condition)
    2. Maximum 3 simultaneous positions
    
    Exit Rules:
    1. RSI rises above 70 (overbought condition), OR
    2. Stop-loss at -8%
    
    Hypothesis: RSI extremes identify temporary price dislocations in growth stocks
    """
    params = (
        ('rsi_period', 14),       # 14-period RSI
        ('rsi_oversold', 30),     # RSI <30 = oversold entry
        ('rsi_overbought', 70),   # RSI >70 = overbought exit
        ('stop_loss_pct', 8.0),   # 8% stop-loss
        ('max_positions', 3),     # Maximum 3 simultaneous positions
        ('cost_model', None)
    )
    
    def __init__(self):
        # RSI indicator
        self.rsi = bt.indicators.RelativeStrengthIndex(
            period=self.p.rsi_period
        )
        
        # Track positions and entry prices for stop-loss
        self.position_entry_prices = {}
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0
        self.total_loss = 0
        self.trade_results = []
        
        # Signal tracking
        self.oversold_signals = 0
        self.trades_from_oversold = 0
        self.stop_loss_exits = 0
        self.rsi_exits = 0
        
        # Position management
        self.position_count = 0
        
    def next(self):
        """
        Execute RSI Mean Reversion logic
        """
        
        # Skip if insufficient data for RSI
        if len(self.data) < self.p.rsi_period:
            return
        
        current_rsi = self.rsi[0]
        current_price = self.data.close[0]
        
        # Entry Logic: RSI oversold and position limits
        if (current_rsi < self.p.rsi_oversold and 
            not self.position and 
            self.position_count < self.p.max_positions):
            
            self.oversold_signals += 1
            
            # Buy on oversold condition
            order = self.buy()
            if order:
                self.position_entry_prices[self.data._name] = current_price
                self.position_count += 1
                self.trades_from_oversold += 1
        
        # Exit Logic: RSI overbought OR stop-loss
        elif self.position:
            entry_price = self.position_entry_prices.get(self.data._name, current_price)
            
            # Calculate current P&L percentage
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Exit on overbought condition
            if current_rsi > self.p.rsi_overbought:
                self.close()
                self.rsi_exits += 1
                
            # Exit on stop-loss
            elif pnl_pct <= -self.p.stop_loss_pct:
                self.close()
                self.stop_loss_exits += 1
    
    def notify_order(self, order):
        """
        Track order status for position management
        """
        if order.status in [order.Completed]:
            if order.isbuy():
                # Position opened
                pass
            else:
                # Position closed
                if self.data._name in self.position_entry_prices:
                    del self.position_entry_prices[self.data._name]
                self.position_count = max(0, self.position_count - 1)
    
    def notify_trade(self, trade):
        """
        Track trade results for analysis
        """
        if trade.isclosed:
            self.trade_count += 1
            
            # Calculate trade P&L
            trade_pnl = trade.pnl
            trade_pnl_pct = trade.pnlcomm / max(1, trade.value) * 100 if trade.value != 0 else 0
            
            # Track win/loss statistics
            if trade_pnl > 0:
                self.winning_trades += 1
                self.total_profit += trade_pnl
            else:
                self.losing_trades += 1
                self.total_loss += abs(trade_pnl)
            
            # Store trade details
            self.trade_results.append({
                'pnl': trade_pnl,
                'pnl_pct': trade_pnl_pct,
                'commission': getattr(trade, 'commission', 0)
            })
    
    def get_performance_metrics(self):
        """
        Calculate comprehensive performance metrics for RSI strategy
        """
        
        if self.trade_count == 0:
            return {
                'total_trades': 0,
                'win_rate_pct': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'expectancy': 0,
                'profit_factor': 0,
                'oversold_signals': self.oversold_signals,
                'trades_from_oversold': self.trades_from_oversold,
                'signal_conversion_rate_pct': 0,
                'stop_loss_exits': self.stop_loss_exits,
                'rsi_exits': self.rsi_exits
            }
        
        # Basic trade statistics
        win_rate = (self.winning_trades / self.trade_count) * 100
        avg_profit = self.total_profit / max(1, self.winning_trades)
        avg_loss = self.total_loss / max(1, self.losing_trades)
        
        # Expectancy calculation
        expectancy = (win_rate/100 * avg_profit) - ((100-win_rate)/100 * avg_loss)
        
        # Profit factor
        profit_factor = self.total_profit / max(1, self.total_loss)
        
        # Signal conversion rate
        signal_conversion_rate = (self.trades_from_oversold / max(1, self.oversold_signals)) * 100
        
        return {
            'total_trades': self.trade_count,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_pct': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'expectancy': expectancy,
            'profit_factor': profit_factor,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'oversold_signals': self.oversold_signals,
            'trades_from_oversold': self.trades_from_oversold,
            'signal_conversion_rate_pct': signal_conversion_rate,
            'stop_loss_exits': self.stop_loss_exits,
            'rsi_exits': self.rsi_exits
        }

def run_rsi_mean_reversion_backtest(ticker, data_dir, initial_cash=10000):
    """
    Run RSI Mean Reversion backtest for a single stock
    """
    
    print(f"\nRunning RSI Mean Reversion backtest for {ticker}...")
    
    # Load data
    data_path = os.path.join(data_dir, f'{ticker}.csv')
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        return None
    
    try:
        df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
        print(f"Loaded {len(df)} bars for {ticker}")
    except Exception as e:
        print(f"Error loading data for {ticker}: {e}")
        return None
    
    # Create cost model
    cost_model = RealisticTransactionCosts('mid_cap')
    
    # Initialize Cerebro
    cerebro = bt.Cerebro(stdstats=False)
    
    # Add data
    cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
    
    # Add strategy
    cerebro.addstrategy(RSIMeanReversionStrategy, cost_model=cost_model)
    
    # Set initial cash
    cerebro.broker.setcash(initial_cash)
    
    # Add enhanced commission model
    commission_info = EnhancedCommissionInfo(cost_model)
    cerebro.broker.addcommissioninfo(commission_info)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    results = cerebro.run()
    strategy = results[0]
    
    # Get final portfolio value
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - initial_cash) / initial_cash * 100
    
    # Get analyzer results
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
    sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
    trade_analysis = strategy.analyzers.trades.get_analysis()
    
    # Get strategy-specific metrics
    strategy_metrics = strategy.get_performance_metrics()
    
    # Calculate transaction costs
    total_costs = sum([trade['cost_breakdown']['total_cost'] 
                      for trade in commission_info.trade_log])
    
    cost_breakdown = {}
    for cost_type in ['commission', 'spread_cost', 'slippage', 'market_impact', 'timing_cost']:
        cost_breakdown[cost_type] = sum([trade['cost_breakdown'][cost_type] 
                                       for trade in commission_info.trade_log])
    
    # Compile results
    results_data = {
        'ticker': ticker,
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'strategy': 'RSI Mean Reversion',
        'universe': 'Small/Mid-Cap Growth',
        'data_period': f"{df.index[0].date()} to {df.index[-1].date()}",
        'initial_cash': initial_cash,
        
        # Performance metrics
        'performance': {
            'final_value': final_value,
            'total_return_pct': total_return,
            'max_drawdown_pct': drawdown_analysis.get('max', {}).get('drawdown', 0),
            'sharpe_ratio': sharpe_analysis.get('sharperatio', 0) if sharpe_analysis else 0,
        },
        
        # Trading metrics
        'trading': strategy_metrics,
        
        # Transaction costs
        'transaction_costs': {
            'total_costs_usd': total_costs,
            'cost_impact_pct': (total_costs / initial_cash) * 100,
            'cost_breakdown_usd': cost_breakdown,
            'cost_per_trade': total_costs / max(1, strategy_metrics['total_trades'])
        },
        
        # RSI-specific analysis
        'rsi_analysis': {
            'strategy_type': 'RSI Mean Reversion (RSI <30 entry, >70 exit)',
            'oversold_signals': strategy_metrics['oversold_signals'],
            'trades_executed': strategy_metrics['trades_from_oversold'],
            'signal_conversion_rate_pct': strategy_metrics['signal_conversion_rate_pct'],
            'stop_loss_exits': strategy_metrics['stop_loss_exits'],
            'rsi_exits': strategy_metrics['rsi_exits']
        }
    }
    
    # Print summary
    sharpe_ratio = results_data['performance']['sharpe_ratio']
    sharpe_display = f"{sharpe_ratio:.2f}" if sharpe_ratio is not None else "N/A"
    
    print(f"Results for {ticker}:")
    print(f"  Total Return: {total_return:.1f}%")
    print(f"  Sharpe Ratio: {sharpe_display}")
    print(f"  Win Rate: {strategy_metrics['win_rate_pct']:.1f}%")
    print(f"  Total Trades: {strategy_metrics['total_trades']}")
    print(f"  Oversold Signals: {strategy_metrics['oversold_signals']}")
    print(f"  Signal Conversion: {strategy_metrics['signal_conversion_rate_pct']:.1f}%")
    print(f"  Expectancy: ${strategy_metrics['expectancy']:.2f}")
    
    return results_data

def run_sprint_6_rsi_test():
    """
    Run RSI Mean Reversion test across entire universe
    """
    
    # Small/mid-cap growth universe
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/sprint_6_mean_reversion'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    print("=" * 80)
    print("SPRINT #6 TEST A: RSI MEAN REVERSION STRATEGY")
    print("=" * 80)
    print("Strategy: RSI Mean Reversion (Buy RSI <30, Sell RSI >70)")
    print("Risk Management: 8% stop-loss, max 3 positions")
    print("Hypothesis: RSI extremes identify temporary price dislocations")
    print("=" * 80)
    
    # Run backtest for each stock
    all_results = {}
    
    for ticker in UNIVERSE:
        result = run_rsi_mean_reversion_backtest(ticker, DATA_DIR)
        if result:
            all_results[ticker] = result
    
    if not all_results:
        print("No successful backtests completed")
        return None
    
    # Calculate aggregate metrics
    aggregate_metrics = calculate_aggregate_metrics(all_results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f'rsi_mean_reversion_results_{timestamp}.json')
    
    rsi_results = {
        'test': 'Sprint #6 Test A - RSI Mean Reversion',
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'strategy': 'RSI Mean Reversion (RSI <30 entry, >70 exit, 8% stop)',
        'universe': UNIVERSE,
        'successful_tests': len(all_results),
        'individual_results': all_results,
        'aggregate_metrics': aggregate_metrics
    }
    
    with open(results_file, 'w') as f:
        json.dump(rsi_results, f, indent=2, default=str)
    
    print(f"\n" + "=" * 60)
    print("RSI MEAN REVERSION TEST COMPLETE")
    print("=" * 60)
    print_aggregate_results(aggregate_metrics, "RSI Mean Reversion")
    print(f"Results saved to: {results_file}")
    
    return results_file, rsi_results

def calculate_aggregate_metrics(all_results):
    """
    Calculate aggregate performance metrics across all stocks
    """
    
    if not all_results:
        return {}
    
    # Extract metrics from all stocks
    sharpe_ratios = []
    total_returns = []
    max_drawdowns = []
    win_rates = []
    expectancies = []
    
    total_profit_all = 0
    total_loss_all = 0
    total_trades_all = 0
    total_winning_trades = 0
    total_oversold_signals = 0
    total_trades_from_oversold = 0
    total_stop_loss_exits = 0
    total_rsi_exits = 0
    
    for ticker, result in all_results.items():
        perf = result['performance']
        trading = result['trading']
        
        if perf['sharpe_ratio'] is not None and perf['sharpe_ratio'] != 0:
            sharpe_ratios.append(perf['sharpe_ratio'])
        
        total_returns.append(perf['total_return_pct'])
        max_drawdowns.append(perf['max_drawdown_pct'])
        win_rates.append(trading['win_rate_pct'])
        expectancies.append(trading['expectancy'])
        
        # Aggregate for overall calculations
        total_profit_all += trading.get('total_profit', 0)
        total_loss_all += trading.get('total_loss', 0)
        total_trades_all += trading.get('total_trades', 0)
        total_winning_trades += trading.get('winning_trades', 0)
        total_oversold_signals += trading.get('oversold_signals', 0)
        total_trades_from_oversold += trading.get('trades_from_oversold', 0)
        total_stop_loss_exits += trading.get('stop_loss_exits', 0)
        total_rsi_exits += trading.get('rsi_exits', 0)
    
    # Calculate aggregate metrics
    aggregate = {
        'avg_sharpe_ratio': np.mean(sharpe_ratios) if sharpe_ratios else 0,
        'avg_total_return_pct': np.mean(total_returns),
        'avg_max_drawdown_pct': np.mean(max_drawdowns),
        'avg_win_rate_pct': np.mean(win_rates),
        'avg_expectancy': np.mean(expectancies),
        'total_trades_all_stocks': total_trades_all,
        'aggregate_win_rate_pct': (total_winning_trades / max(1, total_trades_all)) * 100,
        'aggregate_expectancy': (total_profit_all - total_loss_all) / max(1, total_trades_all),
        'total_oversold_signals': total_oversold_signals,
        'total_trades_from_oversold': total_trades_from_oversold,
        'aggregate_signal_conversion_pct': (total_trades_from_oversold / max(1, total_oversold_signals)) * 100,
        'total_stop_loss_exits': total_stop_loss_exits,
        'total_rsi_exits': total_rsi_exits,
        'stocks_tested': len(all_results),
        'profitable_stocks': len([r for r in all_results.values() if r['performance']['total_return_pct'] > 0])
    }
    
    return aggregate

def print_aggregate_results(aggregate_metrics, strategy_name):
    """
    Print aggregate results for the RSI strategy
    """
    
    print(f"\nAGGREGATE PERFORMANCE METRICS ({strategy_name}):")
    print(f"Average Sharpe Ratio: {aggregate_metrics['avg_sharpe_ratio']:.2f}")
    print(f"Average Total Return: {aggregate_metrics['avg_total_return_pct']:.1f}%")
    print(f"Average Win Rate: {aggregate_metrics['avg_win_rate_pct']:.1f}%")
    print(f"Average Max Drawdown: {aggregate_metrics['avg_max_drawdown_pct']:.1f}%")
    print(f"Average Expectancy: ${aggregate_metrics['avg_expectancy']:.2f}")
    
    print(f"\nAGGREGATE TRADING STATISTICS:")
    print(f"Total Trades: {aggregate_metrics['total_trades_all_stocks']}")
    print(f"Aggregate Win Rate: {aggregate_metrics['aggregate_win_rate_pct']:.1f}%")
    print(f"Aggregate Expectancy: ${aggregate_metrics['aggregate_expectancy']:.2f}")
    
    print(f"\nRSI SIGNAL ANALYSIS:")
    print(f"Total Oversold Signals: {aggregate_metrics['total_oversold_signals']}")
    print(f"Trades From Oversold: {aggregate_metrics['total_trades_from_oversold']}")
    print(f"Signal Conversion Rate: {aggregate_metrics['aggregate_signal_conversion_pct']:.1f}%")
    print(f"Stop-Loss Exits: {aggregate_metrics['total_stop_loss_exits']}")
    print(f"RSI Exits: {aggregate_metrics['total_rsi_exits']}")
    
    print(f"\nSUCCESS CRITERIA CHECK:")
    sharpe_pass = aggregate_metrics['avg_sharpe_ratio'] > 0.5
    win_rate_pass = aggregate_metrics['aggregate_win_rate_pct'] > 40
    drawdown_pass = aggregate_metrics['avg_max_drawdown_pct'] < 15
    
    print(f"Sharpe Ratio > 0.5: {aggregate_metrics['avg_sharpe_ratio']:.2f} - {'PASS' if sharpe_pass else 'FAIL'}")
    print(f"Win Rate > 40%: {aggregate_metrics['aggregate_win_rate_pct']:.1f}% - {'PASS' if win_rate_pass else 'FAIL'}")
    print(f"Max Drawdown < 15%: {aggregate_metrics['avg_max_drawdown_pct']:.1f}% - {'PASS' if drawdown_pass else 'FAIL'}")
    print(f"Overall: {'SUCCESS' if sharpe_pass and win_rate_pass and drawdown_pass else 'FAILED'}")

if __name__ == '__main__':
    results_file, results = run_sprint_6_rsi_test()
    print(f"\nSprint #6 RSI Mean Reversion test complete.")