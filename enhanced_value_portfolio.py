# enhanced_value_portfolio.py
import backtrader as bt
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

class RealisticTransactionCosts:
    """
    Comprehensive transaction cost model for realistic trading simulation
    """
    
    def __init__(self, stock_tier='mid_cap'):
        """
        Initialize transaction cost parameters based on stock liquidity tier
        
        Args:
            stock_tier: 'large_cap', 'mid_cap', 'small_cap'
        """
        self.stock_tier = stock_tier
        
        # Define cost parameters by stock tier
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
    
    def calculate_total_cost(self, trade_value, volatility=0.02, volume_ratio=0.01):
        """
        Calculate total transaction cost for a trade
        
        Args:
            trade_value: Dollar value of the trade
            volatility: Recent price volatility (default 2%)
            volume_ratio: Trade size as % of daily volume (default 1%)
            
        Returns:
            dict: Breakdown of all transaction costs
        """
        
        # 1. Base Commission (fixed)
        commission = abs(trade_value) * self.params['base_commission']
        
        # 2. Bid-Ask Spread Cost (always paid)
        spread_cost = abs(trade_value) * self.params['bid_ask_spread']
        
        # 3. Slippage (volatility and urgency dependent)
        volatility_multiplier = max(1.0, volatility / 0.02)  # Scale by normal volatility
        slippage = abs(trade_value) * self.params['slippage_factor'] * volatility_multiplier
        
        # 4. Market Impact (size and liquidity dependent)
        impact_multiplier = min(5.0, max(1.0, volume_ratio / 0.01))  # Scale by normal size
        market_impact = abs(trade_value) * self.params['market_impact_factor'] * impact_multiplier
        
        # 5. Timing Cost (random component for market timing)
        timing_cost = abs(trade_value) * np.random.normal(0, 0.0005)
        timing_cost = abs(timing_cost)  # Always a cost
        
        total_cost = commission + spread_cost + slippage + market_impact + timing_cost
        
        return {
            'commission': commission,
            'spread_cost': spread_cost,
            'slippage': slippage,
            'market_impact': market_impact,
            'timing_cost': timing_cost,
            'total_cost': total_cost,
            'cost_bps': (total_cost / abs(trade_value)) * 10000  # Basis points
        }

class EnhancedCommissionInfo(bt.CommInfoBase):
    """
    Enhanced commission model that includes realistic transaction costs
    """
    
    def __init__(self, cost_model):
        super().__init__()
        self.cost_model = cost_model
        self.trade_log = []
    
    def _getcommission(self, size, price, pseudoexec):
        """
        Calculate realistic commission including all transaction costs
        """
        trade_value = abs(size * price)
        
        # Estimate volatility (simplified - would use actual ATR in production)
        volatility = 0.025  # Assume 2.5% daily volatility for cloud stocks
        
        # Estimate volume ratio (simplified - would use actual volume data)  
        volume_ratio = min(0.02, trade_value / 50000)  # Assume moderate liquidity
        
        # Calculate comprehensive costs
        cost_breakdown = self.cost_model.calculate_total_cost(
            trade_value, volatility, volume_ratio
        )
        
        # Log trade costs for analysis
        self.trade_log.append({
            'trade_value': trade_value,
            'size': size,
            'price': price,
            'cost_breakdown': cost_breakdown
        })
        
        return cost_breakdown['total_cost']

class RiskManagedValuePortfolio(bt.Strategy):
    """
    Enhanced Value Portfolio with Portfolio-Level Stop-Loss and Position Concentration Limits
    """
    params = (
        ('num_positions', 2),
        ('rebalance_freq', 'quarterly'),
        ('position_sizing', 'risk_parity'),
        ('portfolio_stop_loss', 0.25),      # 25% portfolio drawdown limit
        ('max_position_weight', 0.30),      # 30% maximum per stock
        ('cost_model', None)
    )
    
    def __init__(self):
        # Set rebalancing timer
        if self.p.rebalance_freq == 'monthly':
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
        elif self.p.rebalance_freq == 'quarterly':
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], months=[1, 4, 7, 10], monthcarry=True)
        elif self.p.rebalance_freq == 'weekly':
            self.add_timer(when=bt.Timer.SESSION_START, weekdays=[1], weekcarry=True)
        
        # Risk management tracking
        self.portfolio_high_water_mark = 0
        self.portfolio_stopped_out = False
        self.stop_loss_triggered_date = None
        
        # Performance tracking
        self.rebalance_count = 0
        self.total_costs = 0
        self.equity_curve = []
        
        # Portfolio metrics
        self.max_drawdown = 0
        self.current_drawdown = 0
        
    def notify_timer(self, timer, when, *args, **kwargs):
        """Handle rebalancing timer events"""
        if not self.portfolio_stopped_out:
            self.rebalance()
    
    def next(self):
        """Called on every bar - monitor portfolio stop-loss"""
        current_value = self.broker.getvalue()
        
        # Update high water mark
        if current_value > self.portfolio_high_water_mark:
            self.portfolio_high_water_mark = current_value
        
        # Calculate current drawdown
        if self.portfolio_high_water_mark > 0:
            self.current_drawdown = (self.portfolio_high_water_mark - current_value) / self.portfolio_high_water_mark
            
            # Update max drawdown
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
        
        # Track equity curve
        self.equity_curve.append({
            'date': self.data.datetime.date(0),
            'value': current_value,
            'drawdown': self.current_drawdown,
            'high_water_mark': self.portfolio_high_water_mark
        })
        
        # Check portfolio stop-loss
        if (not self.portfolio_stopped_out and 
            self.current_drawdown >= self.p.portfolio_stop_loss):
            
            self.trigger_portfolio_stop_loss()
    
    def trigger_portfolio_stop_loss(self):
        """
        Trigger portfolio-level stop-loss: liquidate all positions and halt trading
        """
        print(f"\nPORTFOLIO STOP-LOSS TRIGGERED!")
        print(f"Date: {self.data.datetime.date(0)}")
        print(f"Current Drawdown: {self.current_drawdown:.2%}")
        print(f"Drawdown Limit: {self.p.portfolio_stop_loss:.2%}")
        print(f"Portfolio Value: ${self.broker.getvalue():,.2f}")
        print(f"High Water Mark: ${self.portfolio_high_water_mark:,.2f}")
        
        # Liquidate all positions
        for d in self.datas:
            if self.getposition(d).size != 0:
                self.close(data=d)
                print(f"Liquidated position in {d._name}")
        
        # Set stop-loss flag to halt further trading
        self.portfolio_stopped_out = True
        self.stop_loss_triggered_date = self.data.datetime.date(0)
        
        print("All trading halted for remainder of backtest")
    
    def rebalance(self):
        """Enhanced rebalancing with position concentration limits"""
        if self.portfolio_stopped_out:
            return  # No trading after stop-loss
            
        self.rebalance_count += 1
        
        # Simple factor scoring (volatility-based value proxy)
        factor_scores = {}
        for d in self.datas:
            try:
                recent_prices = [d.close[-i] for i in range(min(20, len(d)))]
                volatility = np.std(recent_prices) / np.mean(recent_prices)
                factor_scores[d._name] = 1 / (1 + volatility)
            except:
                factor_scores[d._name] = 0.5
        
        # Select top stocks
        ranked_stocks = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
        target_stocks = [stock for stock, score in ranked_stocks[:self.p.num_positions]]
        
        # Close positions not in target
        for d in self.datas:
            if self.getposition(d).size > 0 and d._name not in target_stocks:
                self.close(data=d)
        
        # Calculate weights with concentration limits
        if self.p.position_sizing == 'risk_parity':
            # Simplified risk parity
            volatilities = {}
            for d in self.datas:
                if d._name in target_stocks:
                    try:
                        recent_prices = [d.close[-i] for i in range(min(20, len(d)))]
                        vol = np.std(recent_prices) / np.mean(recent_prices)
                        volatilities[d._name] = vol
                    except:
                        volatilities[d._name] = 0.2
            
            total_inv_vol = sum(1/v for v in volatilities.values())
            raw_weights = {stock: (1/volatilities[stock]) / total_inv_vol 
                          for stock in target_stocks}
        else:
            # Equal weight
            weight_per_stock = 1.0 / len(target_stocks)
            raw_weights = {stock: weight_per_stock for stock in target_stocks}
        
        # Apply position concentration limits
        final_weights = self.apply_concentration_limits(raw_weights)
        
        # Execute trades
        for d in self.datas:
            if d._name in target_stocks:
                target_weight = final_weights[d._name]
                self.order_target_percent(data=d, target=target_weight)
    
    def apply_concentration_limits(self, raw_weights):
        """
        Apply position concentration limits (max 30% per stock)
        """
        final_weights = {}
        total_excess = 0
        
        # First pass: cap positions at max weight
        for stock, weight in raw_weights.items():
            if weight > self.p.max_position_weight:
                final_weights[stock] = self.p.max_position_weight
                total_excess += weight - self.p.max_position_weight
            else:
                final_weights[stock] = weight
        
        # Second pass: redistribute excess weight to non-capped positions
        if total_excess > 0:
            non_capped_stocks = [stock for stock, weight in final_weights.items() 
                               if weight < self.p.max_position_weight]
            
            if non_capped_stocks:
                excess_per_stock = total_excess / len(non_capped_stocks)
                for stock in non_capped_stocks:
                    # Add excess weight, but don't exceed cap
                    additional_weight = min(excess_per_stock, 
                                          self.p.max_position_weight - final_weights[stock])
                    final_weights[stock] += additional_weight
        
        # Normalize to ensure weights sum to 1.0
        total_weight = sum(final_weights.values())
        if total_weight > 0:
            final_weights = {stock: weight/total_weight for stock, weight in final_weights.items()}
        
        return final_weights
    
    def get_performance_metrics(self):
        """
        Calculate comprehensive performance metrics
        """
        if not self.equity_curve:
            return {}
        
        initial_value = self.equity_curve[0]['value']
        final_value = self.equity_curve[-1]['value']
        
        # Calculate returns
        total_return = (final_value - initial_value) / initial_value
        
        # Calculate annualized return (assuming 252 trading days per year)
        days = len(self.equity_curve)
        years = days / 252
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # Calculate total transaction costs
        if hasattr(self.broker, 'comminfo') and hasattr(self.broker.comminfo, 'trade_log'):
            total_costs = sum([trade['cost_breakdown']['total_cost'] 
                             for trade in self.broker.comminfo.trade_log])
        else:
            total_costs = 0
        
        return {
            'total_return_pct': total_return * 100,
            'annualized_return_pct': annualized_return * 100,
            'max_drawdown_pct': self.max_drawdown * 100,
            'final_value': final_value,
            'initial_value': initial_value,
            'total_costs': total_costs,
            'cost_impact_pct': (total_costs / initial_value) * 100,
            'rebalance_count': self.rebalance_count,
            'portfolio_stopped_out': self.portfolio_stopped_out,
            'stop_loss_date': str(self.stop_loss_triggered_date) if self.stop_loss_triggered_date else None,
            'equity_curve_length': len(self.equity_curve)
        }

def run_enhanced_value_portfolio(universe, data_dir, cost_tier='mid_cap', 
                                initial_cash=100000, **strategy_params):
    """
    Run enhanced Value Portfolio with risk management and transaction costs
    """
    
    print(f"\n=== ENHANCED VALUE PORTFOLIO WITH RISK MANAGEMENT ===")
    print(f"Portfolio Stop-Loss: {strategy_params.get('portfolio_stop_loss', 0.25):.0%}")
    print(f"Max Position Weight: {strategy_params.get('max_position_weight', 0.30):.0%}")
    print(f"Transaction Cost Tier: {cost_tier}")
    
    # Create cost model
    cost_model = RealisticTransactionCosts(cost_tier)
    
    # Initialize Cerebro
    cerebro = bt.Cerebro(stdstats=False)
    
    # Add data for all stocks
    for ticker in universe:
        data_path = os.path.join(data_dir, f'{ticker}.csv')
        if os.path.exists(data_path):
            df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
            cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
    
    # Add strategy
    cerebro.addstrategy(RiskManagedValuePortfolio, cost_model=cost_model, **strategy_params)
    
    # Set initial cash
    cerebro.broker.setcash(initial_cash)
    
    # Add enhanced commission model
    cerebro.broker.addcommissioninfo(EnhancedCommissionInfo(cost_model))
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    print(f"\nRunning backtest with initial cash: ${initial_cash:,.2f}")
    results = cerebro.run()
    strategy = results[0]
    
    # Get performance metrics
    performance = strategy.get_performance_metrics()
    
    # Get analyzer results
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
    trade_analysis = strategy.analyzers.trades.get_analysis()
    
    # Combine all results
    final_results = {
        'strategy_params': strategy_params,
        'cost_tier': cost_tier,
        'initial_cash': initial_cash,
        'performance': performance,
        'drawdown_analysis': {
            'max_drawdown_pct': drawdown_analysis.get('max', {}).get('drawdown', 0),
            'max_drawdown_period': drawdown_analysis.get('max', {}).get('len', 0)
        },
        'trade_analysis': {
            'total_trades': trade_analysis.get('total', {}).get('total', 0),
            'winning_trades': trade_analysis.get('won', {}).get('total', 0),
            'losing_trades': trade_analysis.get('lost', {}).get('total', 0),
            'win_rate_pct': (trade_analysis.get('won', {}).get('total', 0) / 
                           max(1, trade_analysis.get('total', {}).get('total', 1))) * 100
        },
        'risk_controls': {
            'portfolio_stop_loss_triggered': performance.get('portfolio_stopped_out', False),
            'stop_loss_date': performance.get('stop_loss_date'),
            'max_position_weight': strategy_params.get('max_position_weight', 0.30)
        }
    }
    
    return final_results, strategy

def test_risk_management_configurations():
    """
    Test different risk management configurations
    """
    
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/week_2_risk_management'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    print("=== WEEK 2: RISK MANAGEMENT IMPLEMENTATION ===")
    print("Testing enhanced Value Portfolio with risk controls")
    
    # Test configurations
    test_configs = [
        {
            'name': 'Baseline (No Risk Controls)',
            'params': {
                'num_positions': 2,
                'rebalance_freq': 'quarterly',
                'position_sizing': 'risk_parity',
                'portfolio_stop_loss': 1.0,  # 100% (effectively disabled)
                'max_position_weight': 1.0   # 100% (effectively disabled)
            }
        },
        {
            'name': 'Portfolio Stop-Loss Only (25%)',
            'params': {
                'num_positions': 2,
                'rebalance_freq': 'quarterly',
                'position_sizing': 'risk_parity',
                'portfolio_stop_loss': 0.25,  # 25% drawdown limit
                'max_position_weight': 1.0    # No concentration limit
            }
        },
        {
            'name': 'Concentration Limits Only (30%)',
            'params': {
                'num_positions': 2,
                'rebalance_freq': 'quarterly',
                'position_sizing': 'risk_parity',
                'portfolio_stop_loss': 1.0,   # No portfolio stop
                'max_position_weight': 0.30   # 30% max per stock
            }
        },
        {
            'name': 'Full Risk Controls (25% Stop + 30% Max)',
            'params': {
                'num_positions': 2,
                'rebalance_freq': 'quarterly',
                'position_sizing': 'risk_parity',
                'portfolio_stop_loss': 0.25,  # 25% drawdown limit
                'max_position_weight': 0.30   # 30% max per stock
            }
        }
    ]
    
    all_results = {}
    
    for config in test_configs:
        print(f"\n" + "="*60)
        print(f"Testing: {config['name']}")
        print("="*60)
        
        try:
            results, strategy = run_enhanced_value_portfolio(
                UNIVERSE, DATA_DIR, 
                cost_tier='mid_cap',
                initial_cash=100000,
                **config['params']
            )
            
            all_results[config['name']] = results
            
            # Print key results
            perf = results['performance']
            risk = results['risk_controls']
            
            print(f"Total Return: {perf['total_return_pct']:.1f}%")
            print(f"Annualized Return: {perf['annualized_return_pct']:.1f}%")
            print(f"Max Drawdown: {perf['max_drawdown_pct']:.1f}%")
            print(f"Cost Impact: {perf['cost_impact_pct']:.2f}%")
            print(f"Portfolio Stopped Out: {risk['portfolio_stop_loss_triggered']}")
            if risk['stop_loss_date']:
                print(f"Stop Loss Date: {risk['stop_loss_date']}")
            
        except Exception as e:
            print(f"Error testing {config['name']}: {e}")
            continue
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f'risk_management_test_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n" + "="*60)
    print("RISK MANAGEMENT TESTING COMPLETE")
    print("="*60)
    print(f"Results saved to: {results_file}")
    
    return results_file, all_results

if __name__ == '__main__':
    results_file, results = test_risk_management_configurations()