# sprint_4_ma_crossover.py
import backtrader as bt
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

class RealisticTransactionCosts:
    """
    Validated transaction cost model (confirmed accurate in Post-Mortem)
    Using mid-cap parameters for small/mid-cap growth stock universe
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
        volatility_multiplier = max(1.0, volatility / 0.025)  # Scale by growth stock volatility
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
        
        # Growth stock assumptions (higher volatility than large-cap)
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

class GoldenCrossStrategy(bt.Strategy):
    """
    Double Moving Average Crossover (Golden Cross) Strategy
    
    Rules:
    - Buy when 50-day MA crosses above 200-day MA
    - Sell when 50-day MA crosses below 200-day MA
    - Simple trend-following momentum strategy
    """
    params = (
        ('fast_period', 50),      # 50-day MA (fast)
        ('slow_period', 200),     # 200-day MA (slow)
        ('cost_model', None)
    )
    
    def __init__(self):
        # Calculate moving averages
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.fast_period
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.slow_period
        )
        
        # Crossover signals
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0
        self.total_loss = 0
        self.trade_results = []
        
        # Track position entry price for P&L calculation
        self.entry_price = 0
        
    def next(self):
        """
        Execute Golden Cross logic
        """
        
        # Skip if we don't have enough data for slow MA
        if len(self.data) < self.p.slow_period:
            return
        
        # Buy signal: Fast MA crosses above Slow MA
        if self.crossover > 0 and not self.position:
            self.buy()
            self.entry_price = self.data.close[0]
            
        # Sell signal: Fast MA crosses below Slow MA  
        elif self.crossover < 0 and self.position:
            self.close()
    
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
            try:
                entry_date = trade.dtopen.date() if hasattr(trade.dtopen, 'date') else str(trade.dtopen)
                exit_date = trade.dtclose.date() if hasattr(trade.dtclose, 'date') else str(trade.dtclose)
            except:
                entry_date = 'N/A'
                exit_date = 'N/A'
                
            self.trade_results.append({
                'entry_date': entry_date,
                'exit_date': exit_date,
                'pnl': trade_pnl,
                'pnl_pct': trade_pnl_pct,
                'commission': getattr(trade, 'commission', 0)
            })
    
    def get_performance_metrics(self):
        """
        Calculate comprehensive performance metrics for Golden Cross
        """
        
        if self.trade_count == 0:
            return {
                'total_trades': 0,
                'win_rate_pct': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'expectancy': 0,
                'profit_factor': 0
            }
        
        # Basic trade statistics
        win_rate = (self.winning_trades / self.trade_count) * 100
        avg_profit = self.total_profit / max(1, self.winning_trades)
        avg_loss = self.total_loss / max(1, self.losing_trades)
        
        # Expectancy calculation
        if self.trade_count > 0:
            expectancy = (win_rate/100 * avg_profit) - ((100-win_rate)/100 * avg_loss)
        else:
            expectancy = 0
        
        # Profit factor
        profit_factor = self.total_profit / max(1, self.total_loss)
        
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
            'total_loss': self.total_loss
        }

def run_golden_cross_backtest(ticker, data_dir, initial_cash=10000):
    """
    Run Golden Cross backtest for a single stock with transaction costs
    """
    
    print(f"\nRunning Golden Cross backtest for {ticker}...")
    
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
    cerebro.addstrategy(GoldenCrossStrategy, cost_model=cost_model)
    
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
        'strategy': 'Golden Cross (50/200 MA)',
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
        
        # Trade details
        'trade_details': strategy.trade_results
    }
    
    # Print summary
    print(f"Results for {ticker}:")
    print(f"  Total Return: {total_return:.1f}%")
    print(f"  Sharpe Ratio: {results_data['performance']['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {results_data['performance']['max_drawdown_pct']:.1f}%")
    print(f"  Win Rate: {strategy_metrics['win_rate_pct']:.1f}%")
    print(f"  Total Trades: {strategy_metrics['total_trades']}")
    print(f"  Expectancy: ${strategy_metrics['expectancy']:.2f}")
    print(f"  Transaction Costs: ${total_costs:.2f} ({(total_costs / initial_cash) * 100:.2f}%)")
    
    return results_data

def run_sprint_4_golden_cross():
    """
    Run Golden Cross backtest across entire small/mid-cap growth universe
    """
    
    # Small/mid-cap growth universe (original from Sprint #1)
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/sprint_4_golden_cross'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    print("=" * 80)
    print("SPRINT #4: GOLDEN CROSS STRATEGY TEST")
    print("=" * 80)
    print("Strategy: Double Moving Average Crossover (50/200-day)")
    print("Universe: Small/Mid-Cap Growth Stocks (high volatility)")
    print("Paradigm: Pure momentum/trend-following")
    print("")
    print("Success Criteria:")
    print("- Aggregate Post-Cost Sharpe Ratio > 0.5")
    print("- Aggregate Win Rate > 40%")
    print("- Positive Expectancy (avg profit > avg loss)")
    print("=" * 80)
    
    # Run backtest for each stock
    all_results = {}
    
    for ticker in UNIVERSE:
        result = run_golden_cross_backtest(ticker, DATA_DIR)
        if result:
            all_results[ticker] = result
    
    if not all_results:
        print("No successful backtests completed")
        return None
    
    # Calculate aggregate metrics
    aggregate_metrics = calculate_aggregate_metrics(all_results)
    
    # Compile final results
    sprint_4_results = {
        'sprint': 'Sprint #4 - Golden Cross Test',
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'strategy': 'Double Moving Average Crossover (50/200-day)',
        'universe': UNIVERSE,
        'successful_tests': len(all_results),
        'individual_results': all_results,
        'aggregate_metrics': aggregate_metrics,
        'success_criteria_validation': validate_success_criteria(aggregate_metrics)
    }
    
    # Print aggregate results
    print_aggregate_results(aggregate_metrics, sprint_4_results['success_criteria_validation'])
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f'sprint_4_golden_cross_results_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(sprint_4_results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {results_file}")
    
    return results_file, sprint_4_results

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
    total_trades_list = []
    
    total_profit_all = 0
    total_loss_all = 0
    total_trades_all = 0
    total_winning_trades = 0
    
    for ticker, result in all_results.items():
        perf = result['performance']
        trading = result['trading']
        
        if perf['sharpe_ratio'] != 0:  # Valid sharpe ratio
            sharpe_ratios.append(perf['sharpe_ratio'])
        
        total_returns.append(perf['total_return_pct'])
        max_drawdowns.append(perf['max_drawdown_pct'])
        win_rates.append(trading['win_rate_pct'])
        expectancies.append(trading['expectancy'])
        total_trades_list.append(trading['total_trades'])
        
        # Aggregate for overall calculations  
        total_profit_all += trading.get('total_profit', 0)
        total_loss_all += trading.get('total_loss', 0)
        total_trades_all += trading.get('total_trades', 0)
        total_winning_trades += trading.get('winning_trades', 0)
    
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
        'stocks_tested': len(all_results),
        'profitable_stocks': len([r for r in all_results.values() if r['performance']['total_return_pct'] > 0])
    }
    
    return aggregate

def validate_success_criteria(aggregate_metrics):
    """
    Validate Sprint #4 success criteria
    """
    
    criteria = {
        'sharpe_ratio': {
            'target': '> 0.5',
            'actual': aggregate_metrics.get('avg_sharpe_ratio', 0),
            'achieved': aggregate_metrics.get('avg_sharpe_ratio', 0) > 0.5,
            'status': 'PASS' if aggregate_metrics.get('avg_sharpe_ratio', 0) > 0.5 else 'FAIL'
        },
        'win_rate': {
            'target': '> 40%',
            'actual': aggregate_metrics.get('aggregate_win_rate_pct', 0),
            'achieved': aggregate_metrics.get('aggregate_win_rate_pct', 0) > 40,
            'status': 'PASS' if aggregate_metrics.get('aggregate_win_rate_pct', 0) > 40 else 'FAIL'
        },
        'positive_expectancy': {
            'target': '> 0 (positive)',
            'actual': aggregate_metrics.get('aggregate_expectancy', 0),
            'achieved': aggregate_metrics.get('aggregate_expectancy', 0) > 0,
            'status': 'PASS' if aggregate_metrics.get('aggregate_expectancy', 0) > 0 else 'FAIL'
        }
    }
    
    all_criteria_met = all(c['achieved'] for c in criteria.values())
    
    return {
        'individual_criteria': criteria,
        'all_criteria_met': all_criteria_met,
        'deployment_ready': all_criteria_met
    }

def print_aggregate_results(aggregate_metrics, validation):
    """
    Print aggregate results and success criteria validation
    """
    
    print(f"\n" + "=" * 80)
    print("SPRINT #4 AGGREGATE RESULTS")
    print("=" * 80)
    
    print(f"\nAGGREGATE PERFORMANCE METRICS:")
    print(f"Average Sharpe Ratio: {aggregate_metrics['avg_sharpe_ratio']:.2f}")
    print(f"Average Total Return: {aggregate_metrics['avg_total_return_pct']:.1f}%")
    print(f"Average Max Drawdown: {aggregate_metrics['avg_max_drawdown_pct']:.1f}%")
    print(f"Average Win Rate: {aggregate_metrics['avg_win_rate_pct']:.1f}%")
    print(f"Average Expectancy: ${aggregate_metrics['avg_expectancy']:.2f}")
    
    print(f"\nAGGREGATE TRADING STATISTICS:")
    print(f"Total Trades (All Stocks): {aggregate_metrics['total_trades_all_stocks']}")
    print(f"Aggregate Win Rate: {aggregate_metrics['aggregate_win_rate_pct']:.1f}%")
    print(f"Aggregate Expectancy: ${aggregate_metrics['aggregate_expectancy']:.2f}")
    print(f"Profitable Stocks: {aggregate_metrics['profitable_stocks']}/{aggregate_metrics['stocks_tested']}")
    
    print(f"\nSUCCESS CRITERIA VALIDATION:")
    for criterion, data in validation['individual_criteria'].items():
        print(f"{criterion.replace('_', ' ').title()}:")
        print(f"  Target: {data['target']}")
        print(f"  Actual: {data['actual']:.2f}")
        print(f"  Status: {data['status']}")
    
    print(f"\nOVERALL ASSESSMENT:")
    print(f"All Criteria Met: {'YES' if validation['all_criteria_met'] else 'NO'}")
    print(f"Strategy Deployment Ready: {'YES' if validation['deployment_ready'] else 'NO'}")
    
    if validation['all_criteria_met']:
        print(f"\nSUCCESS! Golden Cross strategy validated for deployment.")
    else:
        print(f"\nStrategy does not meet all deployment criteria.")

if __name__ == '__main__':
    results_file, results = run_sprint_4_golden_cross()
    print(f"\nSprint #4 Golden Cross testing complete.")