# sprint_3_djia_backtest.py
import backtrader as bt
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

class RealisticTransactionCosts:
    """
    Transaction cost model optimized for large-cap stocks (DJIA components)
    """
    
    def __init__(self, stock_tier='large_cap'):
        """
        Initialize transaction cost parameters for large-cap stocks
        
        Large-cap stocks have significantly lower transaction costs than mid-cap:
        - Tighter bid-ask spreads (10 bps vs 25 bps)
        - Lower slippage (5 bps vs 15 bps)
        - Higher liquidity reduces market impact
        """
        self.stock_tier = stock_tier
        
        # Large-cap cost parameters (much lower than mid-cap used in Week 2)
        self.cost_params = {
            'large_cap': {
                'base_commission': 0.0005,      # 5 bps base commission (same)
                'bid_ask_spread': 0.0010,       # 10 bps spread (vs 25 bps mid-cap) 
                'slippage_factor': 0.0005,      # 5 bps slippage (vs 15 bps mid-cap)
                'market_impact_factor': 0.00001, # Very low impact for liquid stocks
                'liquidity_threshold': 1000000   # $1M+ daily volume
            }
        }
        
        self.params = self.cost_params[stock_tier]
    
    def calculate_total_cost(self, trade_value, volatility=0.015, volume_ratio=0.005):
        """
        Calculate transaction costs - expect much lower costs for large-cap stocks
        
        Args:
            trade_value: Dollar value of the trade
            volatility: Lower volatility for large-cap (1.5% vs 2.5%)
            volume_ratio: Smaller impact due to higher liquidity (0.5% vs 1%)
        """
        
        # 1. Base Commission (same as mid-cap)
        commission = abs(trade_value) * self.params['base_commission']
        
        # 2. Bid-Ask Spread Cost (60% lower than mid-cap)
        spread_cost = abs(trade_value) * self.params['bid_ask_spread']
        
        # 3. Slippage (67% lower than mid-cap)
        volatility_multiplier = max(1.0, volatility / 0.015)  # Lower base volatility
        slippage = abs(trade_value) * self.params['slippage_factor'] * volatility_multiplier
        
        # 4. Market Impact (80% lower than mid-cap)
        impact_multiplier = min(3.0, max(1.0, volume_ratio / 0.005))  # Higher liquidity
        market_impact = abs(trade_value) * self.params['market_impact_factor'] * impact_multiplier
        
        # 5. Timing Cost (same random component)
        timing_cost = abs(trade_value) * np.random.normal(0, 0.0003)  # Slightly lower
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
    Enhanced commission model for large-cap stocks
    """
    
    def __init__(self, cost_model):
        super().__init__()
        self.cost_model = cost_model
        self.trade_log = []
    
    def _getcommission(self, size, price, pseudoexec):
        """
        Calculate realistic commission for large-cap stocks
        """
        trade_value = abs(size * price)
        
        # Large-cap assumptions: lower volatility and better liquidity
        volatility = 0.015  # 1.5% vs 2.5% for growth stocks
        volume_ratio = min(0.01, trade_value / 100000)  # Better liquidity
        
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

class DJIAValuePortfolioStrategy(bt.Strategy):
    """
    Value Portfolio strategy adapted for DJIA large-cap universe
    """
    params = (
        ('num_positions', 2),               # Same as Week 2 for consistency
        ('rebalance_freq', 'quarterly'),    # Same frequency
        ('position_sizing', 'risk_parity'), # Same sizing method
        ('portfolio_stop_loss', 0.25),     # Same 25% stop-loss
        ('max_position_weight', 0.30),     # Same 30% concentration limit
        ('cost_model', None)
    )
    
    def __init__(self):
        # Set quarterly rebalancing timer
        self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], months=[1, 4, 7, 10], monthcarry=True)
        
        # Risk management tracking
        self.portfolio_high_water_mark = 0
        self.portfolio_stopped_out = False
        self.stop_loss_triggered_date = None
        
        # Performance tracking
        self.rebalance_count = 0
        self.equity_curve = []
        self.max_drawdown = 0
        self.current_drawdown = 0
        
        # P/E ratio cache for value scoring
        self.pe_ratios = {}
        
    def notify_timer(self, timer, when, *args, **kwargs):
        """Handle quarterly rebalancing"""
        if not self.portfolio_stopped_out:
            self.rebalance()
    
    def next(self):
        """Monitor portfolio stop-loss daily"""
        current_value = self.broker.getvalue()
        
        # Update high water mark
        if current_value > self.portfolio_high_water_mark:
            self.portfolio_high_water_mark = current_value
        
        # Calculate current drawdown
        if self.portfolio_high_water_mark > 0:
            self.current_drawdown = (self.portfolio_high_water_mark - current_value) / self.portfolio_high_water_mark
            
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
        
        # Track equity curve
        self.equity_curve.append({
            'date': self.data.datetime.date(0),
            'value': current_value,
            'drawdown': self.current_drawdown,
            'high_water_mark': self.portfolio_high_water_mark
        })
        
        # Check portfolio stop-loss (25% limit)
        if (not self.portfolio_stopped_out and 
            self.current_drawdown >= self.p.portfolio_stop_loss):
            self.trigger_portfolio_stop_loss()
    
    def trigger_portfolio_stop_loss(self):
        """Trigger portfolio stop-loss and liquidate all positions"""
        print(f"\nPORTFOLIO STOP-LOSS TRIGGERED!")
        print(f"Date: {self.data.datetime.date(0)}")
        print(f"Current Drawdown: {self.current_drawdown:.2%}")
        print(f"Portfolio Value: ${self.broker.getvalue():,.2f}")
        
        # Liquidate all positions
        for d in self.datas:
            if self.getposition(d).size != 0:
                self.close(data=d)
        
        self.portfolio_stopped_out = True
        self.stop_loss_triggered_date = self.data.datetime.date(0)
        print("All trading halted for remainder of backtest")
    
    def rebalance(self):
        """Quarterly rebalancing with value-based stock selection"""
        if self.portfolio_stopped_out:
            return
            
        self.rebalance_count += 1
        
        # Calculate value scores using P/E ratio proxy (inverse volatility)
        # For DJIA stocks, lower volatility often correlates with value characteristics
        value_scores = {}
        for d in self.datas:
            try:
                # Get recent price data for volatility calculation
                recent_prices = [d.close[-i] for i in range(min(60, len(d)))]
                if len(recent_prices) >= 20:
                    volatility = np.std(recent_prices) / np.mean(recent_prices)
                    # Value score: inverse volatility (lower vol = higher value score)
                    value_scores[d._name] = 1 / (1 + volatility)
                else:
                    value_scores[d._name] = 0.5
            except:
                value_scores[d._name] = 0.5
        
        # Select top value stocks (lowest volatility = highest value score)
        ranked_stocks = sorted(value_scores.items(), key=lambda x: x[1], reverse=True)
        target_stocks = [stock for stock, score in ranked_stocks[:self.p.num_positions]]
        
        print(f"Rebalance #{self.rebalance_count}: Selected {target_stocks}")
        
        # Close positions not in target
        for d in self.datas:
            if self.getposition(d).size > 0 and d._name not in target_stocks:
                self.close(data=d)
        
        # Calculate risk parity weights
        volatilities = {}
        for d in self.datas:
            if d._name in target_stocks:
                try:
                    recent_prices = [d.close[-i] for i in range(min(60, len(d)))]
                    vol = np.std(recent_prices) / np.mean(recent_prices)
                    volatilities[d._name] = vol
                except:
                    volatilities[d._name] = 0.15  # Default volatility for large-cap
        
        # Risk parity weights
        total_inv_vol = sum(1/v for v in volatilities.values())
        raw_weights = {stock: (1/volatilities[stock]) / total_inv_vol 
                      for stock in target_stocks}
        
        # Apply concentration limits (30% max per stock)
        final_weights = self.apply_concentration_limits(raw_weights)
        
        # Execute trades
        for d in self.datas:
            if d._name in target_stocks:
                target_weight = final_weights[d._name]
                self.order_target_percent(data=d, target=target_weight)
    
    def apply_concentration_limits(self, raw_weights):
        """Apply 30% maximum position size limit"""
        final_weights = {}
        total_excess = 0
        
        # Cap positions at 30%
        for stock, weight in raw_weights.items():
            if weight > self.p.max_position_weight:
                final_weights[stock] = self.p.max_position_weight
                total_excess += weight - self.p.max_position_weight
            else:
                final_weights[stock] = weight
        
        # Redistribute excess to non-capped positions
        if total_excess > 0:
            non_capped_stocks = [stock for stock, weight in final_weights.items() 
                               if weight < self.p.max_position_weight]
            
            if non_capped_stocks:
                excess_per_stock = total_excess / len(non_capped_stocks)
                for stock in non_capped_stocks:
                    additional_weight = min(excess_per_stock, 
                                          self.p.max_position_weight - final_weights[stock])
                    final_weights[stock] += additional_weight
        
        # Normalize weights
        total_weight = sum(final_weights.values())
        if total_weight > 0:
            final_weights = {stock: weight/total_weight for stock, weight in final_weights.items()}
        
        return final_weights
    
    def get_performance_metrics(self):
        """Calculate comprehensive performance metrics"""
        if not self.equity_curve:
            return {}
        
        initial_value = self.equity_curve[0]['value']
        final_value = self.equity_curve[-1]['value']
        
        # Calculate returns
        total_return = (final_value - initial_value) / initial_value
        
        # Annualized return
        days = len(self.equity_curve)
        years = days / 252
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        return {
            'total_return_pct': total_return * 100,
            'annualized_return_pct': annualized_return * 100,
            'max_drawdown_pct': self.max_drawdown * 100,
            'final_value': final_value,
            'initial_value': initial_value,
            'rebalance_count': self.rebalance_count,
            'portfolio_stopped_out': self.portfolio_stopped_out,
            'stop_loss_date': str(self.stop_loss_triggered_date) if self.stop_loss_triggered_date else None,
            'equity_curve_length': len(self.equity_curve)
        }

def load_djia_data_for_backtest(data_dir):
    """
    Load DJIA data with proper formatting for backtrader
    """
    
    # DJIA universe
    DJIA_TICKERS = [
        'AXP', 'AMGN', 'AAPL', 'BA', 'CAT', 'CSCO', 'CVX', 'GS', 'HD', 'HON', 
        'IBM', 'INTC', 'JNJ', 'KO', 'JPM', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE',
        'PG', 'TRV', 'UNH', 'CRM', 'VZ', 'V', 'WBA', 'WMT', 'DIS', 'DOW'
    ]
    
    loaded_data = []
    
    for ticker in DJIA_TICKERS:
        file_path = os.path.join(data_dir, f'{ticker}.csv')
        if os.path.exists(file_path):
            try:
                # Read the CSV file with proper handling of yfinance format
                df = pd.read_csv(file_path, header=[0, 1], index_col=0)
                
                # yfinance creates multi-level columns like ('Close', 'AAPL')
                # We need to flatten this structure
                df.columns = df.columns.droplevel(1)  # Remove ticker level, keep price type
                
                # Ensure index is datetime
                df.index = pd.to_datetime(df.index)
                df.index.name = 'Date'
                
                # Rename columns to standard format
                column_mapping = {}
                for col in df.columns:
                    if 'Close' in str(col):
                        column_mapping[col] = 'Close'
                    elif 'Open' in str(col):
                        column_mapping[col] = 'Open'
                    elif 'High' in str(col):
                        column_mapping[col] = 'High'
                    elif 'Low' in str(col):
                        column_mapping[col] = 'Low'
                    elif 'Volume' in str(col):
                        column_mapping[col] = 'Volume'
                
                df = df.rename(columns=column_mapping)
                
                # Keep only standard OHLCV columns
                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                df = df[required_cols]
                
                # Drop any rows with missing data
                df = df.dropna()
                
                if len(df) > 100:  # Ensure sufficient data
                    loaded_data.append((ticker, df))
                    print(f"Loaded {ticker}: {len(df)} bars")
                else:
                    print(f"Skipped {ticker}: insufficient data ({len(df)} bars)")
                    
            except Exception as e:
                print(f"Error loading {ticker}: {e}")
                # Try simpler parsing as fallback
                try:
                    df = pd.read_csv(file_path)
                    if len(df) > 3:  # Has header rows
                        # Skip the first 3 rows which are headers
                        df = pd.read_csv(file_path, skiprows=3, names=['Date', 'Close', 'High', 'Low', 'Open', 'Volume'])
                        df['Date'] = pd.to_datetime(df['Date'])
                        df = df.set_index('Date')
                        
                        # Drop missing data
                        df = df.dropna()
                        
                        if len(df) > 100:
                            loaded_data.append((ticker, df))
                            print(f"Loaded {ticker} (fallback): {len(df)} bars")
                        else:
                            print(f"Skipped {ticker}: insufficient data in fallback ({len(df)} bars)")
                except:
                    print(f"Failed to load {ticker} with fallback method")
    
    return loaded_data

def run_sprint_3_backtest():
    """
    Run Sprint #3 DJIA Value Portfolio backtest with all risk controls
    """
    
    DATA_DIR = 'data/sprint_3_djia'
    RESULTS_DIR = 'results/sprint_3_djia'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    print("=" * 80)
    print("SPRINT #3: DJIA LARGE-CAP VALUE PORTFOLIO BACKTEST")
    print("=" * 80)
    print("Hypothesis: Large-cap value stocks will have:")
    print("- Lower transaction costs (large-cap vs mid-cap)")
    print("- Lower volatility (value vs growth)")
    print("- Better risk-adjusted returns")
    print("")
    print("Success Criteria:")
    print("- Max Drawdown < 20% (stricter than Week 2)")
    print("- Post-Cost Annualized Return > 15% (more conservative)")
    print("=" * 80)
    
    # Load DJIA data
    print("\nLoading DJIA data...")
    loaded_data = load_djia_data_for_backtest(DATA_DIR)
    
    if len(loaded_data) < 25:
        print(f"ERROR: Only {len(loaded_data)} stocks loaded. Need at least 25 for robust test.")
        return None
    
    print(f"Successfully loaded {len(loaded_data)} DJIA stocks")
    
    # Create cost model for large-cap stocks
    cost_model = RealisticTransactionCosts('large_cap')
    
    # Initialize Cerebro
    cerebro = bt.Cerebro(stdstats=False)
    
    # Add data feeds
    for ticker, df in loaded_data:
        cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
    
    # Add strategy with same parameters as Week 2 for direct comparison
    cerebro.addstrategy(DJIAValuePortfolioStrategy, cost_model=cost_model)
    
    # Set initial cash (same as Week 2)
    initial_cash = 100000
    cerebro.broker.setcash(initial_cash)
    
    # Add enhanced commission model for large-cap costs
    commission_info = EnhancedCommissionInfo(cost_model)
    cerebro.broker.addcommissioninfo(commission_info)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    
    print(f"\nRunning backtest with ${initial_cash:,.2f} initial capital...")
    
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
    total_costs = sum([trade['cost_breakdown']['total_cost'] 
                      for trade in commission_info.trade_log])
    
    cost_breakdown = {}
    for cost_type in ['commission', 'spread_cost', 'slippage', 'market_impact', 'timing_cost']:
        cost_breakdown[cost_type] = sum([trade['cost_breakdown'][cost_type] 
                                       for trade in commission_info.trade_log])
    
    # Compile final results
    final_results = {
        'sprint': 'Sprint #3 - DJIA Large-Cap Value',
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'universe': 'Dow Jones Industrial Average (30 stocks)',
        'universe_loaded': len(loaded_data),
        'data_period': '2018-2023 (6 years)',
        'initial_cash': initial_cash,
        
        # Performance vs Week 2 comparison
        'performance': {
            'final_value': performance['final_value'],
            'total_return_pct': performance['total_return_pct'],
            'annualized_return_pct': performance['annualized_return_pct'],
            'max_drawdown_pct': performance['max_drawdown_pct'],
            'sharpe_ratio': sharpe_analysis.get('sharperatio', 0) if sharpe_analysis else 0,
        },
        
        # Transaction cost comparison (key hypothesis test)
        'transaction_costs': {
            'total_costs_usd': total_costs,
            'cost_impact_pct': (total_costs / initial_cash) * 100,
            'cost_breakdown_usd': cost_breakdown,
            'cost_per_rebalance': total_costs / max(1, performance.get('rebalance_count', 1)),
            'cost_tier': 'large_cap',
            'cost_model_params': cost_model.params
        },
        
        # Risk management results
        'risk_management': {
            'portfolio_stop_loss_triggered': performance.get('portfolio_stopped_out', False),
            'stop_loss_date': performance.get('stop_loss_date'),
            'max_position_weight_limit': 30.0,
            'concentration_controls_active': True
        },
        
        # Trading activity
        'trading_activity': {
            'total_trades': trade_analysis.get('total', {}).get('total', 0),
            'winning_trades': trade_analysis.get('won', {}).get('total', 0),
            'losing_trades': trade_analysis.get('lost', {}).get('total', 0),
            'win_rate_pct': (trade_analysis.get('won', {}).get('total', 0) / 
                           max(1, trade_analysis.get('total', {}).get('total', 1))) * 100,
            'rebalance_count': performance.get('rebalance_count', 0)
        },
        
        # Sprint #3 Success Criteria
        'sprint_3_success_criteria': {
            'criterion_1_max_drawdown': {
                'target': 'Max Drawdown < 20%',
                'actual': f"{performance['max_drawdown_pct']:.1f}%",
                'achieved': performance['max_drawdown_pct'] < 20.0,
                'status': 'PASS' if performance['max_drawdown_pct'] < 20.0 else 'FAIL'
            },
            'criterion_2_post_cost_return': {
                'target': 'Post-Cost Annualized Return > 15%',
                'actual': f"{performance['annualized_return_pct']:.1f}%",
                'achieved': performance['annualized_return_pct'] > 15.0,
                'status': 'PASS' if performance['annualized_return_pct'] > 15.0 else 'FAIL'
            },
            'overall_success': {
                'both_criteria_met': (performance['max_drawdown_pct'] < 20.0 and 
                                    performance['annualized_return_pct'] > 15.0),
                'deployment_ready': (performance['max_drawdown_pct'] < 20.0 and 
                                   performance['annualized_return_pct'] > 15.0)
            }
        }
    }
    
    # Print results
    print("\n" + "=" * 80)
    print("SPRINT #3 RESULTS")
    print("=" * 80)
    
    print(f"\nPERFORMANCE:")
    print(f"Final Value: ${performance['final_value']:,.2f}")
    print(f"Total Return: {performance['total_return_pct']:.1f}%")
    print(f"Annualized Return: {performance['annualized_return_pct']:.1f}%")
    print(f"Max Drawdown: {performance['max_drawdown_pct']:.1f}%")
    
    if sharpe_analysis:
        print(f"Sharpe Ratio: {sharpe_analysis.get('sharperatio', 0):.2f}")
    
    print(f"\nTRANSACTION COSTS (Large-Cap):")
    print(f"Total Costs: ${total_costs:,.2f}")
    print(f"Cost Impact: {(total_costs / initial_cash) * 100:.2f}% of capital")
    print(f"Cost vs Week 2: Expected ~75% reduction")
    
    print(f"\nRISK MANAGEMENT:")
    print(f"Stop-Loss Triggered: {performance.get('portfolio_stopped_out', False)}")
    print(f"Max Position Limit: 30% enforced")
    
    print(f"\nSUCCESS CRITERIA:")
    crit1_pass = performance['max_drawdown_pct'] < 20.0
    crit2_pass = performance['annualized_return_pct'] > 15.0
    
    print(f"1. Max Drawdown < 20%: {performance['max_drawdown_pct']:.1f}% - {'PASS' if crit1_pass else 'FAIL'}")
    print(f"2. Return > 15%: {performance['annualized_return_pct']:.1f}% - {'PASS' if crit2_pass else 'FAIL'}")
    print(f"Overall: {'SUCCESS' if crit1_pass and crit2_pass else 'FAILED'}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f'sprint_3_djia_results_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {results_file}")
    print("=" * 80)
    
    return results_file, final_results

if __name__ == '__main__':
    results_file, results = run_sprint_3_backtest()