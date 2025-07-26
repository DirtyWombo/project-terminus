# rsi_optimization_backtest.py
# Sprint #7 Test A: RSI Parameter Optimization Grid Search

import backtrader as bt
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
import itertools

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

class OptimizedRSIStrategy(bt.Strategy):
    """
    Optimized RSI Strategy with Configurable Parameters
    
    Entry Rules:
    1. RSI drops below oversold_level (configurable)
    2. Maximum 3 simultaneous positions
    
    Exit Rules:
    1. RSI rises above overbought_level (configurable), OR
    2. Stop-loss at -8%
    
    Purpose: Test different RSI parameter combinations for optimization
    """
    params = (
        ('rsi_period', 14),           # RSI period (10, 14, 21)
        ('rsi_oversold', 30),         # Oversold level (20, 25, 30)
        ('rsi_overbought', 70),       # Overbought level (70, 75, 80)
        ('stop_loss_pct', 8.0),       # 8% stop-loss
        ('max_positions', 3),         # Maximum 3 simultaneous positions
        ('cost_model', None)
    )
    
    def __init__(self):
        # RSI indicator with configurable period
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
        Execute Optimized RSI logic with configurable parameters
        """
        
        # Skip if insufficient data for RSI
        if len(self.data) < self.p.rsi_period:
            return
        
        current_rsi = self.rsi[0]
        current_price = self.data.close[0]
        
        # TASK 2: DEBUG LOGGING - Log every bar to see what's happening
        if hasattr(self, '_debug_count'):
            self._debug_count += 1
        else:
            self._debug_count = 1
            
        # Log every 50th bar to avoid spam, but show key moments
        if (self._debug_count % 50 == 0 or 
            current_rsi < 35 or current_rsi > 65 or  # Near trigger levels
            self.position):  # When we have a position
            print(f"DEBUG [{self.data._name}] Date: {self.data.datetime.date(0)}, "
                  f"Price: ${current_price:.2f}, RSI: {current_rsi:.1f}, "
                  f"Position: {bool(self.position)}, Count: {self.position_count}")
            
        # Log all oversold conditions
        if current_rsi < self.p.rsi_oversold:
            print(f"*** OVERSOLD SIGNAL [{self.data._name}] "
                  f"Date: {self.data.datetime.date(0)}, RSI: {current_rsi:.1f} "
                  f"(threshold: {self.p.rsi_oversold}), Position: {bool(self.position)}")
                  
        # Log all overbought conditions  
        if current_rsi > self.p.rsi_overbought:
            print(f"*** OVERBOUGHT SIGNAL [{self.data._name}] "
                  f"Date: {self.data.datetime.date(0)}, RSI: {current_rsi:.1f} "
                  f"(threshold: {self.p.rsi_overbought}), Position: {bool(self.position)}")
        
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
        Calculate comprehensive performance metrics
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

def run_single_rsi_optimization(ticker, data_dir, rsi_period, oversold_level, overbought_level, initial_cash=10000):
    """
    Run RSI backtest with specific parameters for a single stock
    """
    
    # Load data
    data_path = os.path.join(data_dir, f'{ticker}.csv')
    if not os.path.exists(data_path):
        return None
    
    try:
        df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
    except Exception as e:
        return None
    
    # Create cost model
    cost_model = RealisticTransactionCosts('mid_cap')
    
    # Initialize Cerebro
    cerebro = bt.Cerebro(stdstats=False)
    
    # Add data
    cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
    
    # Add strategy with specific parameters
    cerebro.addstrategy(
        OptimizedRSIStrategy, 
        rsi_period=rsi_period,
        rsi_oversold=oversold_level,
        rsi_overbought=overbought_level,
        cost_model=cost_model
    )
    
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
    
    # Get strategy-specific metrics
    strategy_metrics = strategy.get_performance_metrics()
    
    # Calculate transaction costs
    total_costs = sum([trade['cost_breakdown']['total_cost'] 
                      for trade in commission_info.trade_log])
    
    # Get Sharpe ratio (handle None/NaN)
    sharpe_ratio = sharpe_analysis.get('sharperatio', 0) if sharpe_analysis else 0
    if sharpe_ratio is None or np.isnan(sharpe_ratio):
        sharpe_ratio = 0
    
    # Compile results
    return {
        'ticker': ticker,
        'parameters': {
            'rsi_period': rsi_period,
            'oversold_level': oversold_level,
            'overbought_level': overbought_level
        },
        'performance': {
            'total_return_pct': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': drawdown_analysis.get('max', {}).get('drawdown', 0),
            'win_rate_pct': strategy_metrics['win_rate_pct'],
            'expectancy': strategy_metrics['expectancy'],
            'total_trades': strategy_metrics['total_trades']
        },
        'transaction_costs': {
            'total_costs_usd': total_costs,
            'cost_impact_pct': (total_costs / initial_cash) * 100
        }
    }

def run_rsi_parameter_grid_search():
    """
    Run comprehensive RSI parameter optimization across entire universe
    """
    
    # Small/mid-cap growth universe
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/sprint_7_rsi_optimization'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    # Parameter grid - adjusted for realistic RSI levels in growth stocks
    RSI_PERIODS = [10, 14, 21]
    OVERSOLD_LEVELS = [25, 30, 35]  # Adjusted higher for growth stocks
    OVERBOUGHT_LEVELS = [65, 70, 75]  # Adjusted lower for more frequent exits
    
    print("=" * 80)
    print("SPRINT #7 TEST A: RSI PARAMETER OPTIMIZATION GRID SEARCH")
    print("=" * 80)
    print(f"Testing {len(RSI_PERIODS)} x {len(OVERSOLD_LEVELS)} x {len(OVERBOUGHT_LEVELS)} = {len(RSI_PERIODS) * len(OVERSOLD_LEVELS) * len(OVERBOUGHT_LEVELS)} parameter combinations")
    print(f"RSI Periods: {RSI_PERIODS}")
    print(f"Oversold Levels: {OVERSOLD_LEVELS}")
    print(f"Overbought Levels: {OVERBOUGHT_LEVELS}")
    print("=" * 80)
    
    # Store all results
    all_results = {}
    optimization_results = {}
    
    total_combinations = len(RSI_PERIODS) * len(OVERSOLD_LEVELS) * len(OVERBOUGHT_LEVELS)
    combination_count = 0
    
    # Test each stock across all parameter combinations
    for ticker in UNIVERSE:
        print(f"\nOptimizing parameters for {ticker}...")
        
        ticker_results = []
        best_sharpe = -999
        best_params = None
        best_result = None
        
        # Grid search across all parameter combinations
        for rsi_period, oversold, overbought in itertools.product(RSI_PERIODS, OVERSOLD_LEVELS, OVERBOUGHT_LEVELS):
            combination_count += 1
            
            # Run backtest with specific parameters
            result = run_single_rsi_optimization(ticker, DATA_DIR, rsi_period, oversold, overbought)
            
            if result:
                ticker_results.append(result)
                
                # Track best Sharpe ratio for this stock
                if result['performance']['sharpe_ratio'] > best_sharpe:
                    best_sharpe = result['performance']['sharpe_ratio']
                    best_params = (rsi_period, oversold, overbought)
                    best_result = result
        
        # Store results for this ticker
        all_results[ticker] = {
            'all_combinations': ticker_results,
            'best_parameters': best_params,
            'best_result': best_result,
            'best_sharpe': best_sharpe
        }
        
        if best_result:
            print(f"  Best parameters: RSI({best_params[0]}) {best_params[1]}/{best_params[2]}")
            print(f"  Best Sharpe: {best_sharpe:.3f}")
            print(f"  Win Rate: {best_result['performance']['win_rate_pct']:.1f}%")
            print(f"  Total Trades: {best_result['performance']['total_trades']}")
        
        print(f"  Progress: {combination_count}/{total_combinations * len(UNIVERSE)} tests completed")
    
    # Analyze optimization results across universe
    optimization_summary = analyze_optimization_results(all_results)
    
    # Save comprehensive results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f'rsi_grid_search_results_{timestamp}.json')
    
    optimization_results = {
        'test': 'Sprint #7 Test A - RSI Parameter Grid Search',
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'parameter_grid': {
            'rsi_periods': RSI_PERIODS,
            'oversold_levels': OVERSOLD_LEVELS,
            'overbought_levels': OVERBOUGHT_LEVELS,
            'total_combinations': total_combinations
        },
        'universe': UNIVERSE,
        'individual_stock_results': all_results,
        'optimization_summary': optimization_summary
    }
    
    with open(results_file, 'w') as f:
        json.dump(optimization_results, f, indent=2, default=str)
    
    print(f"\n" + "=" * 60)
    print("RSI PARAMETER OPTIMIZATION COMPLETE")
    print("=" * 60)
    print_optimization_summary(optimization_summary)
    print(f"Results saved to: {results_file}")
    
    return results_file, optimization_results

def analyze_optimization_results(all_results):
    """
    Analyze optimization results to find best overall parameters
    """
    
    # Track parameter frequency and performance
    param_performance = {}
    stock_count = len([r for r in all_results.values() if r['best_result'] is not None])
    
    if stock_count == 0:
        return {}
    
    # Collect best parameters for each stock
    best_params_list = []
    best_sharpes = []
    best_win_rates = []
    
    for ticker, results in all_results.items():
        if results['best_result']:
            params = results['best_parameters']
            best_params_list.append(params)
            best_sharpes.append(results['best_result']['performance']['sharpe_ratio'])
            best_win_rates.append(results['best_result']['performance']['win_rate_pct'])
            
            # Track parameter combinations
            if params not in param_performance:
                param_performance[params] = {
                    'count': 0,
                    'total_sharpe': 0,
                    'total_win_rate': 0,
                    'stocks': []
                }
            
            param_performance[params]['count'] += 1
            param_performance[params]['total_sharpe'] += results['best_result']['performance']['sharpe_ratio']
            param_performance[params]['total_win_rate'] += results['best_result']['performance']['win_rate_pct']
            param_performance[params]['stocks'].append(ticker)
    
    # Find most common best parameters
    most_common_params = max(param_performance.keys(), key=lambda x: param_performance[x]['count'])
    
    # Calculate averages for most common params
    common_perf = param_performance[most_common_params]
    avg_sharpe_common = common_perf['total_sharpe'] / common_perf['count']
    avg_win_rate_common = common_perf['total_win_rate'] / common_perf['count']
    
    return {
        'stocks_optimized': stock_count,
        'most_common_best_params': {
            'rsi_period': most_common_params[0],
            'oversold_level': most_common_params[1],
            'overbought_level': most_common_params[2],
            'frequency': common_perf['count'],
            'avg_sharpe': avg_sharpe_common,
            'avg_win_rate': avg_win_rate_common,
            'successful_stocks': common_perf['stocks']
        },
        'overall_averages': {
            'avg_best_sharpe': np.mean(best_sharpes),
            'avg_best_win_rate': np.mean(best_win_rates),
            'sharpe_improvement_potential': np.mean(best_sharpes) - 0,  # vs baseline of 0
        },
        'parameter_distribution': {str(k): v for k, v in param_performance.items()}
    }

def print_optimization_summary(summary):
    """
    Print optimization summary results
    """
    
    if not summary:
        print("No optimization results to display")
        return
    
    print(f"\nOPTIMIZATION SUMMARY:")
    print(f"Stocks Successfully Optimized: {summary['stocks_optimized']}/10")
    
    print(f"\nMOST EFFECTIVE PARAMETER SET:")
    common = summary['most_common_best_params']
    print(f"RSI Period: {common['rsi_period']}")
    print(f"Oversold Level: {common['oversold_level']}")
    print(f"Overbought Level: {common['overbought_level']}")
    print(f"Optimal for {common['frequency']} stocks: {', '.join(common['successful_stocks'])}")
    print(f"Average Sharpe: {common['avg_sharpe']:.3f}")
    print(f"Average Win Rate: {common['avg_win_rate']:.1f}%")
    
    print(f"\nOVERALL OPTIMIZATION IMPACT:")
    overall = summary['overall_averages']
    print(f"Average Best Sharpe Ratio: {overall['avg_best_sharpe']:.3f}")
    print(f"Average Best Win Rate: {overall['avg_best_win_rate']:.1f}%")
    print(f"Sharpe Improvement vs Baseline: {overall['sharpe_improvement_potential']:+.3f}")

if __name__ == '__main__':
    results_file, results = run_rsi_parameter_grid_search()
    print(f"\nSprint #7 Test A: RSI Parameter Optimization complete.")