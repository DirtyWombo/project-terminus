# value_portfolio_optimizer.py
import backtrader as bt
import pandas as pd
import yfinance as yf
import os
import json
import numpy as np
from datetime import datetime
from itertools import product

class EnhancedValuePortfolio(bt.Strategy):
    params = (
        ('num_positions', 2),
        ('rebalance_freq', 'monthly'),  # 'weekly', 'biweekly', 'monthly', 'quarterly'
        ('stop_loss_pct', 0.0),         # 0 = no stop loss, 0.15 = 15% stop
        ('position_sizing', 'equal'),    # 'equal', 'volatility', 'risk_parity'
        ('factor_method', 'pe_only'),    # 'pe_only', 'multi_factor'
    )
    
    def __init__(self):
        # Set rebalancing timer based on frequency
        if self.p.rebalance_freq == 'weekly':
            self.add_timer(when=bt.Timer.SESSION_START, weekdays=[1], weekcarry=True)
        elif self.p.rebalance_freq == 'biweekly': 
            self.add_timer(when=bt.Timer.SESSION_START, weekdays=[1], weeks=[1, 3], weekcarry=True)
        elif self.p.rebalance_freq == 'monthly':
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
        elif self.p.rebalance_freq == 'quarterly':
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], months=[1, 4, 7, 10], monthcarry=True)
        
        # Portfolio tracking
        self.positions_dict = {}
        self.last_rebalance = None
        self.trade_log = []
        
        # Risk management
        self.entry_prices = {}
        
    def notify_timer(self, timer, when, *args, **kwargs):
        self.rebalance()
    
    def next(self):
        # Check stop losses if enabled
        if self.p.stop_loss_pct > 0:
            self.check_stop_losses()
    
    def check_stop_losses(self):
        """Check and execute stop losses"""
        for d in self.datas:
            position = self.getposition(d)
            if position.size > 0 and d._name in self.entry_prices:
                current_price = d.close[0]
                entry_price = self.entry_prices[d._name]
                loss_pct = (entry_price - current_price) / entry_price
                
                if loss_pct >= self.p.stop_loss_pct:
                    self.close(data=d)
                    print(f"Stop loss triggered for {d._name}: {loss_pct:.2%}")
    
    def rebalance(self):
        """Enhanced rebalancing with multiple factor methods"""
        current_date = self.data.datetime.date(0)
        print(f"Rebalancing portfolio on {current_date}")
        
        # Get factor scores for all stocks
        factor_scores = self.calculate_factor_scores()
        
        # Select top stocks
        ranked_stocks = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
        target_stocks = [stock for stock, score in ranked_stocks[:self.p.num_positions]]
        
        print(f"Selected stocks: {target_stocks}")
        
        # Close positions not in target list
        for d in self.datas:
            if self.getposition(d).size > 0 and d._name not in target_stocks:
                self.close(data=d)
                if d._name in self.entry_prices:
                    del self.entry_prices[d._name]
        
        # Calculate position weights
        weights = self.calculate_position_weights(target_stocks)
        
        # Open/adjust positions
        for d in self.datas:
            if d._name in target_stocks:
                target_weight = weights.get(d._name, 0)
                if target_weight > 0:
                    self.order_target_percent(data=d, target=target_weight)
                    self.entry_prices[d._name] = d.close[0]
        
        self.last_rebalance = current_date
    
    def calculate_factor_scores(self):
        """Calculate factor scores based on method"""
        scores = {}
        
        if self.p.factor_method == 'pe_only':
            # Simple P/E based scoring (lower is better)
            for d in self.datas:
                try:
                    # Simulate P/E ratios (in real implementation, use actual data)
                    # Using price volatility as proxy for fundamental attractiveness
                    recent_prices = [d.close[-i] for i in range(min(20, len(d)))]
                    volatility = np.std(recent_prices) / np.mean(recent_prices)
                    # Lower volatility = higher score (value proxy)
                    scores[d._name] = 1 / (1 + volatility)
                except:
                    scores[d._name] = 0.5
                    
        elif self.p.factor_method == 'multi_factor':
            # Multi-factor scoring (momentum + value proxy)
            for d in self.datas:
                try:
                    # Value component (volatility-based proxy)
                    recent_prices = [d.close[-i] for i in range(min(20, len(d)))]
                    volatility = np.std(recent_prices) / np.mean(recent_prices)
                    value_score = 1 / (1 + volatility)
                    
                    # Momentum component (recent performance)
                    momentum_score = (d.close[0] - d.close[-20]) / d.close[-20] if len(d) >= 20 else 0
                    momentum_score = max(-0.5, min(0.5, momentum_score))  # Clip extreme values
                    
                    # Combined score (70% value, 30% momentum)
                    scores[d._name] = 0.7 * value_score + 0.3 * (0.5 + momentum_score)
                except:
                    scores[d._name] = 0.5
        
        return scores
    
    def calculate_position_weights(self, target_stocks):
        """Calculate position weights based on sizing method"""
        weights = {}
        
        if self.p.position_sizing == 'equal':
            # Equal weight allocation
            weight_per_stock = 1.0 / len(target_stocks)
            for stock in target_stocks:
                weights[stock] = weight_per_stock
                
        elif self.p.position_sizing == 'volatility':
            # Inverse volatility weighting
            volatilities = {}
            for d in self.datas:
                if d._name in target_stocks:
                    try:
                        recent_prices = [d.close[-i] for i in range(min(20, len(d)))]
                        vol = np.std(recent_prices) / np.mean(recent_prices)
                        volatilities[d._name] = vol
                    except:
                        volatilities[d._name] = 0.2  # Default volatility
            
            # Inverse volatility weights
            inv_vol_sum = sum(1/v for v in volatilities.values())
            for stock in target_stocks:
                weights[stock] = (1/volatilities[stock]) / inv_vol_sum
                
        elif self.p.position_sizing == 'risk_parity':
            # Risk parity (simplified - equal risk contribution)
            # For simplicity, using inverse volatility but normalized differently
            volatilities = {}
            for d in self.datas:
                if d._name in target_stocks:
                    try:
                        recent_prices = [d.close[-i] for i in range(min(20, len(d)))]
                        vol = np.std(recent_prices) / np.mean(recent_prices)
                        volatilities[d._name] = vol
                    except:
                        volatilities[d._name] = 0.2
            
            # Risk parity weights (each position contributes equal risk)
            risk_budgets = {stock: 1/len(target_stocks) for stock in target_stocks}
            total_inv_vol = sum(1/vol for vol in volatilities.values())
            
            for stock in target_stocks:
                weights[stock] = risk_budgets[stock] * (1/volatilities[stock]) / total_inv_vol * len(target_stocks)
        
        return weights

def run_value_portfolio_optimization(universe, data_dir, results_dir):
    """Run comprehensive optimization of Value Portfolio strategy"""
    
    # Define optimization parameters
    param_grid = {
        'num_positions': [2, 3, 4, 5],
        'rebalance_freq': ['weekly', 'biweekly', 'monthly', 'quarterly'],
        'stop_loss_pct': [0.0, 0.05, 0.10, 0.15],
        'position_sizing': ['equal', 'volatility', 'risk_parity'],
        'factor_method': ['pe_only', 'multi_factor']
    }
    
    # Create all parameter combinations (limit for testing)
    all_combinations = list(product(*param_grid.values()))
    print(f"Total parameter combinations: {len(all_combinations)}")
    
    # Limit to reasonable subset for initial testing
    test_combinations = all_combinations[::len(all_combinations)//20]  # Test every 20th combination
    print(f"Testing {len(test_combinations)} parameter combinations")
    
    optimization_results = []
    
    for i, params in enumerate(test_combinations):
        param_dict = dict(zip(param_grid.keys(), params))
        print(f"\nTesting combination {i+1}/{len(test_combinations)}: {param_dict}")
        
        try:
            # Run backtest with current parameters
            result = run_single_portfolio_test(universe, data_dir, param_dict)
            if result:
                result['parameters'] = param_dict
                optimization_results.append(result)
                print(f"Result: {result['total_return_pct']:.1f}% return, {result['max_drawdown_pct']:.1f}% drawdown")
        except Exception as e:
            print(f"Error testing parameters {param_dict}: {e}")
            continue
    
    return optimization_results

def run_single_portfolio_test(universe, data_dir, params):
    """Run single backtest with given parameters"""
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(EnhancedValuePortfolio, **params)
    
    # Add all stocks to cerebro
    for ticker in universe:
        data_path = os.path.join(data_dir, f'{ticker}.csv')
        if os.path.exists(data_path):
            df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
            cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
    
    # Set up broker
    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    results = cerebro.run()
    
    if not results:
        return None
    
    result = results[0]
    final_value = cerebro.broker.getvalue()
    
    # Extract metrics
    sharpe = result.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    if sharpe is None: 
        sharpe = 0
    
    drawdown = result.analyzers.drawdown.get_analysis()
    trades = result.analyzers.trades.get_analysis()
    
    return {
        'final_value': final_value,
        'total_return_pct': (final_value - initial_cash) / initial_cash * 100,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': drawdown.get('max', {}).get('drawdown', 0),
        'total_trades': trades.get('total', {}).get('total', 0),
        'winning_trades': trades.get('won', {}).get('total', 0),
        'win_rate_pct': (trades.get('won', {}).get('total', 0) / max(trades.get('total', {}).get('total', 1), 1)) * 100
    }

def analyze_optimization_results(results):
    """Analyze optimization results and find best configurations"""
    
    if not results:
        return {}
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(results)
    
    # Extract parameter columns
    param_cols = list(results[0]['parameters'].keys())
    for col in param_cols:
        df[col] = df['parameters'].apply(lambda x: x[col])
    
    # Sort by different criteria
    top_by_return = df.nlargest(5, 'total_return_pct')
    top_by_sharpe = df.nlargest(5, 'sharpe_ratio')
    top_by_risk_adj = df.assign(risk_adj_return=df['total_return_pct'] / (df['max_drawdown_pct'] + 1))\
                       .nlargest(5, 'risk_adj_return')
    
    analysis = {
        'total_combinations_tested': len(results),
        'top_by_return': top_by_return[['total_return_pct', 'max_drawdown_pct', 'sharpe_ratio'] + param_cols].to_dict('records'),
        'top_by_sharpe': top_by_sharpe[['total_return_pct', 'max_drawdown_pct', 'sharpe_ratio'] + param_cols].to_dict('records'),
        'top_by_risk_adjusted': top_by_risk_adj[['total_return_pct', 'max_drawdown_pct', 'sharpe_ratio'] + param_cols].to_dict('records'),
        'parameter_sensitivity': {}
    }
    
    # Parameter sensitivity analysis
    for param in param_cols:
        param_analysis = df.groupby(param)[['total_return_pct', 'max_drawdown_pct', 'sharpe_ratio']].mean()
        analysis['parameter_sensitivity'][param] = param_analysis.to_dict('index')
    
    return analysis

if __name__ == '__main__':
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/sprint_2'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    print("=== Value Portfolio Optimization - Sprint #2 ===")
    print(f"Universe: {len(UNIVERSE)} stocks")
    print(f"Optimization target: Reduce drawdown while maintaining returns")
    
    # Run optimization
    optimization_results = run_value_portfolio_optimization(UNIVERSE, DATA_DIR, RESULTS_DIR)
    
    if optimization_results:
        # Analyze results
        analysis = analyze_optimization_results(optimization_results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(RESULTS_DIR, f'value_portfolio_optimization_{timestamp}.json')
        
        with open(results_file, 'w') as f:
            json.dump({
                'optimization_results': optimization_results,
                'analysis': analysis,
                'test_date': timestamp
            }, f, indent=2, default=str)
        
        print(f"\nOptimization complete!")
        print(f"Results saved to: {results_file}")
        print(f"Best configuration by return: {analysis['top_by_return'][0]['total_return_pct']:.1f}%")
        print(f"Best configuration by risk-adj return: {analysis['top_by_risk_adjusted'][0]['total_return_pct']:.1f}%")
        
    else:
        print("No optimization results generated. Check data and parameters.")