# transaction_cost_analyzer.py
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
            'large_cap': {
                'base_commission': 0.0005,      # 5 bps base commission
                'bid_ask_spread': 0.0010,       # 10 bps average spread
                'slippage_factor': 0.0005,      # 5 bps base slippage
                'market_impact_factor': 0.00001, # Very low for liquid stocks
                'liquidity_threshold': 1000000   # $1M+ daily volume
            },
            'mid_cap': {
                'base_commission': 0.0005,      # 5 bps base commission  
                'bid_ask_spread': 0.0025,       # 25 bps average spread (our universe)
                'slippage_factor': 0.0015,      # 15 bps base slippage
                'market_impact_factor': 0.00005, # Moderate impact
                'liquidity_threshold': 100000    # $100K+ daily volume
            },
            'small_cap': {
                'base_commission': 0.0005,      # 5 bps base commission
                'bid_ask_spread': 0.0050,       # 50 bps average spread
                'slippage_factor': 0.0030,      # 30 bps base slippage
                'market_impact_factor': 0.0001, # High impact for illiquid
                'liquidity_threshold': 10000     # $10K+ daily volume
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
        # Represents adverse selection and timing delays
        timing_cost = abs(trade_value) * np.random.normal(0, 0.0005)  # ±5bps random
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

class ValuePortfolioWithCosts(bt.Strategy):
    """
    Value Portfolio strategy with realistic transaction costs
    """
    params = (
        ('num_positions', 2),
        ('rebalance_freq', 'quarterly'),
        ('position_sizing', 'risk_parity'),
        ('cost_model', None)
    )
    
    def __init__(self):
        # Set rebalancing timer
        if self.p.rebalance_freq == 'monthly':
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
        elif self.p.rebalance_freq == 'quarterly':
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], months=[1, 4, 7, 10], monthcarry=True)
        
        self.rebalance_count = 0
        self.total_costs = 0
        
    def notify_timer(self, timer, when, *args, **kwargs):
        self.rebalance()
    
    def rebalance(self):
        """Rebalance with cost awareness"""
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
        
        # Calculate weights (equal or risk parity)
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
            weights = {stock: (1/volatilities[stock]) / total_inv_vol 
                      for stock in target_stocks}
        else:
            # Equal weight
            weight_per_stock = 1.0 / len(target_stocks)
            weights = {stock: weight_per_stock for stock in target_stocks}
        
        # Execute trades
        for d in self.datas:
            if d._name in target_stocks:
                target_weight = weights[d._name]
                self.order_target_percent(data=d, target=target_weight)

class BollingerBounceWithCosts(bt.Strategy):
    """
    Bollinger Bounce strategy with realistic transaction costs
    """
    params = (
        ('period', 30),
        ('devfactor', 1.5),
        ('cost_model', None)
    )
    
    def __init__(self):
        self.bollinger = bt.indicators.BollingerBands(
            period=self.p.period, 
            devfactor=self.p.devfactor
        )
        self.trade_count = 0
        
    def next(self):
        if not self.position:
            if self.data.close < self.bollinger.lines.bot:
                self.buy()
                self.trade_count += 1
        else:
            if self.data.close > self.bollinger.lines.mid:
                self.close()

def run_strategy_with_costs(strategy_class, strategy_name, universe, data_dir, 
                           cost_tier='mid_cap', **strategy_params):
    """
    Run strategy with realistic transaction costs
    """
    
    print(f"\n=== Testing {strategy_name} with {cost_tier} transaction costs ===")
    
    # Create cost model
    cost_model = RealisticTransactionCosts(cost_tier)
    
    results = {}
    
    for ticker in universe:
        try:
            cerebro = bt.Cerebro(stdstats=False)
            
            # Add strategy
            if strategy_class == ValuePortfolioWithCosts:
                # Portfolio strategy needs all data
                for t in universe:
                    data_path = os.path.join(data_dir, f'{t}.csv')
                    if os.path.exists(data_path):
                        df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
                        cerebro.adddata(bt.feeds.PandasData(dataname=df, name=t))
                
                cerebro.addstrategy(strategy_class, cost_model=cost_model, **strategy_params)
                initial_cash = 100000.0
                cerebro.broker.setcash(initial_cash)
                
                # Use enhanced commission model
                cerebro.broker.addcommissioninfo(EnhancedCommissionInfo(cost_model))
                
                # Run once for portfolio
                result = cerebro.run()[0]
                final_value = cerebro.broker.getvalue()
                
                results['PORTFOLIO'] = {
                    'final_value': final_value,
                    'total_return_pct': (final_value - initial_cash) / initial_cash * 100,
                    'rebalance_count': result.rebalance_count,
                    'total_cost_estimate': sum([trade['cost_breakdown']['total_cost'] 
                                              for trade in cerebro.broker.comminfo.trade_log])
                }
                break  # Portfolio strategy only needs one run
                
            else:
                # Single stock strategy
                data_path = os.path.join(data_dir, f'{ticker}.csv')
                if not os.path.exists(data_path):
                    continue
                
                df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
                cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
                cerebro.addstrategy(strategy_class, cost_model=cost_model, **strategy_params)
                
                initial_cash = 10000.0
                cerebro.broker.setcash(initial_cash)
                
                # Use enhanced commission model
                commission_info = EnhancedCommissionInfo(cost_model)
                cerebro.broker.addcommissioninfo(commission_info)
                
                # Add analyzers
                cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
                
                result = cerebro.run()[0]
                final_value = cerebro.broker.getvalue()
                
                trades = result.analyzers.trades.get_analysis()
                total_trades = trades.get('total', {}).get('total', 0)
                
                # Calculate cost impact
                total_costs = sum([trade['cost_breakdown']['total_cost'] 
                                 for trade in commission_info.trade_log])
                avg_cost_per_trade = total_costs / max(1, total_trades)
                
                results[ticker] = {
                    'final_value': final_value,
                    'total_return_pct': (final_value - initial_cash) / initial_cash * 100,
                    'total_trades': total_trades,
                    'total_costs': total_costs,
                    'avg_cost_per_trade': avg_cost_per_trade,
                    'cost_impact_pct': (total_costs / initial_cash) * 100,
                    'trade_count': getattr(result, 'trade_count', total_trades)
                }
                
                print(f"{ticker}: {results[ticker]['total_return_pct']:.1f}% return, "
                      f"{results[ticker]['cost_impact_pct']:.2f}% cost impact")
                
        except Exception as e:
            print(f"Error testing {ticker}: {e}")
            continue
    
    return results

def compare_with_without_costs():
    """
    Compare strategy performance with and without realistic transaction costs
    """
    
    UNIVERSE = ['CRWD', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/week_1_costs'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    print("=== WEEK 1: TRANSACTION COST INTEGRATION ===")
    print("Testing impact of realistic transaction costs on optimized strategies")
    
    # Test 1: Value Portfolio with costs
    print("\n" + "="*60)
    print("1. VALUE PORTFOLIO COST ANALYSIS")
    print("="*60)
    
    value_results_with_costs = run_strategy_with_costs(
        ValuePortfolioWithCosts,
        "Value Portfolio with Costs",
        UNIVERSE,
        DATA_DIR,
        cost_tier='mid_cap',
        num_positions=2,
        rebalance_freq='quarterly',
        position_sizing='risk_parity'
    )
    
    # Test 2: Bollinger Bounce with costs
    print("\n" + "="*60)
    print("2. BOLLINGER BOUNCE COST ANALYSIS")
    print("="*60)
    
    bollinger_results_with_costs = run_strategy_with_costs(
        BollingerBounceWithCosts,
        "Bollinger Bounce with Costs",
        UNIVERSE,
        DATA_DIR,
        cost_tier='mid_cap',
        period=30,
        devfactor=1.5
    )
    
    # Compile results
    cost_analysis = {
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cost_tier': 'mid_cap',
        'value_portfolio_results': value_results_with_costs,
        'bollinger_bounce_results': bollinger_results_with_costs,
        'cost_model_parameters': RealisticTransactionCosts('mid_cap').params
    }
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f'transaction_cost_analysis_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(cost_analysis, f, indent=2, default=str)
    
    print(f"\n" + "="*60)
    print("TRANSACTION COST ANALYSIS COMPLETE")
    print("="*60)
    print(f"Results saved to: {results_file}")
    
    # Summary analysis
    if value_results_with_costs.get('PORTFOLIO'):
        vp_return = value_results_with_costs['PORTFOLIO']['total_return_pct']
        vp_costs = value_results_with_costs['PORTFOLIO']['total_cost_estimate']
        print(f"Value Portfolio: {vp_return:.1f}% return, ${vp_costs:.0f} total costs")
    
    if bollinger_results_with_costs:
        bb_returns = [data['total_return_pct'] for data in bollinger_results_with_costs.values()]
        bb_costs = [data['cost_impact_pct'] for data in bollinger_results_with_costs.values()]
        avg_bb_return = np.mean(bb_returns)
        avg_bb_cost_impact = np.mean(bb_costs)
        print(f"Bollinger Bounce: {avg_bb_return:.1f}% avg return, {avg_bb_cost_impact:.2f}% avg cost impact")
    
    return results_file

if __name__ == '__main__':
    results_file = compare_with_without_costs()
