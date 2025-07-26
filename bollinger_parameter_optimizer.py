# bollinger_parameter_optimizer.py
import backtrader as bt
import pandas as pd
import os
import json
import numpy as np
from datetime import datetime
from itertools import product

class OptimizedBollingerBounce(bt.Strategy):
    params = (
        ('period', 20),
        ('devfactor', 2.0),
        ('exit_method', 'middle'),      # 'middle', 'top', 'trailing'
        ('position_sizing', 'fixed'),   # 'fixed', 'atr_based', 'volatility'
        ('entry_confirmation', False),  # Volume confirmation
        ('stop_loss_pct', 0.0),        # Stop loss percentage
    )
    
    def __init__(self):
        self.bollinger = bt.indicators.BollingerBands(
            period=self.p.period, 
            devfactor=self.p.devfactor
        )
        
        # Additional indicators for enhancements
        if self.p.entry_confirmation:
            self.volume_sma = bt.indicators.SimpleMovingAverage(
                self.data.volume, period=20
            )
        
        if self.p.position_sizing == 'atr_based':
            self.atr = bt.indicators.ATR(period=14)
        
        # Trade tracking
        self.entry_price = None
        self.entry_date = None
        self.trade_log = []
        
    def next(self):
        current_position = self.position.size
        
        # Entry logic
        if not current_position:
            if self.should_enter():
                size = self.calculate_position_size()
                self.buy(size=size)
                self.entry_price = self.data.close[0]
                self.entry_date = self.data.datetime.date(0)
        
        # Exit logic
        else:
            if self.should_exit():
                self.close()
            elif self.p.stop_loss_pct > 0 and self.entry_price:
                # Check stop loss
                loss_pct = (self.entry_price - self.data.close[0]) / self.entry_price
                if loss_pct >= self.p.stop_loss_pct:
                    self.close()
    
    def should_enter(self):
        """Enhanced entry logic with optional confirmations"""
        # Basic Bollinger entry: price below lower band
        basic_signal = self.data.close < self.bollinger.lines.bot
        
        if not basic_signal:
            return False
        
        # Optional volume confirmation
        if self.p.entry_confirmation:
            volume_ok = self.data.volume[0] > self.volume_sma[0] * 1.2
            return volume_ok
        
        return True
    
    def should_exit(self):
        """Enhanced exit logic based on exit method"""
        if self.p.exit_method == 'middle':
            return self.data.close > self.bollinger.lines.mid
        
        elif self.p.exit_method == 'top':
            return self.data.close > self.bollinger.lines.top
            
        elif self.p.exit_method == 'trailing':
            # Simplified trailing stop: exit if price drops from peak
            if hasattr(self, 'peak_price'):
                self.peak_price = max(self.peak_price, self.data.close[0])
                trailing_stop = self.peak_price * 0.95  # 5% trailing
                return self.data.close[0] < trailing_stop
            else:
                self.peak_price = self.data.close[0]
                return False
        
        return False
    
    def calculate_position_size(self):
        """Calculate position size based on method"""
        if self.p.position_sizing == 'fixed':
            return None  # Use default size
        
        elif self.p.position_sizing == 'atr_based':
            if len(self.atr) > 0:
                # Risk 1% of portfolio per trade
                risk_per_trade = self.broker.getvalue() * 0.01
                atr_value = self.atr[0]
                if atr_value > 0:
                    shares = int(risk_per_trade / atr_value)
                    return max(1, shares)
            return None
        
        elif self.p.position_sizing == 'volatility':
            # Inverse volatility sizing
            recent_prices = [self.data.close[-i] for i in range(min(10, len(self.data)))]
            if len(recent_prices) > 1:
                volatility = np.std(recent_prices) / np.mean(recent_prices)
                if volatility > 0:
                    # Lower volatility = larger position
                    vol_factor = 0.02 / volatility  # Target 2% volatility
                    portfolio_value = self.broker.getvalue()
                    position_value = portfolio_value * min(vol_factor, 0.1)  # Max 10%
                    shares = int(position_value / self.data.close[0])
                    return max(1, shares)
            return None
        
        return None

def run_bollinger_optimization(ticker, data_dir, results_dir):
    """Run comprehensive Bollinger Bounce optimization for single stock"""
    
    # Parameter grid for optimization
    param_grid = {
        'period': [10, 15, 20, 25, 30],
        'devfactor': [1.5, 2.0, 2.5, 3.0],
        'exit_method': ['middle', 'top', 'trailing'],
        'position_sizing': ['fixed', 'atr_based', 'volatility'],
        'entry_confirmation': [False, True],
        'stop_loss_pct': [0.0, 0.05, 0.10]
    }
    
    # Create subset of combinations for testing (limit for speed)
    all_combinations = list(product(*param_grid.values()))
    # Test every 10th combination to get representative sample
    test_combinations = all_combinations[::10]
    
    print(f"Testing {len(test_combinations)} parameter combinations for {ticker}")
    
    optimization_results = []
    
    for i, params in enumerate(test_combinations):
        param_dict = dict(zip(param_grid.keys(), params))
        
        try:
            result = run_single_bollinger_test(ticker, data_dir, param_dict)
            if result:
                result['parameters'] = param_dict
                optimization_results.append(result)
                
                if i % 10 == 0:  # Progress update every 10 tests
                    print(f"Completed {i+1}/{len(test_combinations)} tests for {ticker}")
                    
        except Exception as e:
            print(f"Error testing {ticker} with params {param_dict}: {e}")
            continue
    
    return optimization_results

def run_single_bollinger_test(ticker, data_dir, params):
    """Run single Bollinger backtest with given parameters"""
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(OptimizedBollingerBounce, **params)
    
    # Load data
    data_path = os.path.join(data_dir, f'{ticker}.csv')
    if not os.path.exists(data_path):
        return None
    
    df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed, name=ticker)
    
    # Set up broker
    initial_cash = 10000.0
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
    if sharpe is None or np.isnan(sharpe):
        sharpe = 0
    
    drawdown = result.analyzers.drawdown.get_analysis()
    trades = result.analyzers.trades.get_analysis()
    
    total_trades = trades.get('total', {}).get('total', 0)
    winning_trades = trades.get('won', {}).get('total', 0)
    
    return {
        'ticker': ticker,
        'final_value': final_value,
        'total_return_pct': (final_value - initial_cash) / initial_cash * 100,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': drawdown.get('max', {}).get('drawdown', 0),
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'win_rate_pct': (winning_trades / max(total_trades, 1)) * 100,
        'profit_factor': abs(trades.get('won', {}).get('pnl', {}).get('total', 0)) / 
                        max(abs(trades.get('lost', {}).get('pnl', {}).get('total', 1)), 1)
    }

def analyze_bollinger_results(all_results):
    """Analyze optimization results across all stocks"""
    
    if not all_results:
        return {}
    
    # Flatten results for analysis
    flattened_results = []
    for ticker_results in all_results.values():
        flattened_results.extend(ticker_results)
    
    if not flattened_results:
        return {}
    
    # Convert to DataFrame
    df = pd.DataFrame(flattened_results)
    
    # Extract parameter columns
    param_cols = list(flattened_results[0]['parameters'].keys())
    for col in param_cols:
        df[col] = df['parameters'].apply(lambda x: x[col])
    
    # Calculate aggregate metrics by parameter combination
    param_combo_results = []
    
    # Group by parameter combination
    param_groups = df.groupby(param_cols)
    
    for params, group in param_groups:
        param_dict = dict(zip(param_cols, params))
        
        # Calculate aggregated performance
        avg_return = group['total_return_pct'].mean()
        avg_win_rate = group['win_rate_pct'].mean()
        avg_sharpe = group['sharpe_ratio'].mean()
        avg_drawdown = group['max_drawdown_pct'].mean()
        avg_trades = group['total_trades'].mean()
        
        # Risk-adjusted return
        risk_adj_return = avg_return / (avg_drawdown + 1)
        
        param_combo_results.append({
            'parameters': param_dict,
            'avg_return_pct': avg_return,
            'avg_win_rate_pct': avg_win_rate,
            'avg_sharpe_ratio': avg_sharpe,
            'avg_max_drawdown_pct': avg_drawdown,
            'avg_total_trades': avg_trades,
            'risk_adjusted_return': risk_adj_return,
            'num_stocks_tested': len(group)
        })
    
    # Sort by different criteria
    combo_df = pd.DataFrame(param_combo_results)
    
    analysis = {
        'total_combinations_tested': len(combo_df),
        'total_individual_tests': len(flattened_results),
        'best_by_return': combo_df.nlargest(5, 'avg_return_pct').to_dict('records'),
        'best_by_win_rate': combo_df.nlargest(5, 'avg_win_rate_pct').to_dict('records'),
        'best_by_risk_adjusted': combo_df.nlargest(5, 'risk_adjusted_return').to_dict('records'),
        'best_by_sharpe': combo_df.nlargest(5, 'avg_sharpe_ratio').to_dict('records')
    }
    
    # Parameter sensitivity analysis
    analysis['parameter_impact'] = {}
    for param in param_cols:
        if param in ['period', 'devfactor', 'stop_loss_pct']:  # Numeric parameters
            param_impact = combo_df.groupby(param)[['avg_return_pct', 'avg_win_rate_pct', 'risk_adjusted_return']].mean()
            analysis['parameter_impact'][param] = param_impact.to_dict('index')
    
    return analysis

if __name__ == '__main__':
    # Test on subset of universe for speed
    UNIVERSE = ['CRWD', 'DDOG', 'MDB', 'OKTA', 'ZS']  # Top 5 performers from Sprint #1
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/sprint_2'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    print("=== Bollinger Bounce Parameter Optimization - Sprint #2 ===")
    print(f"Testing {len(UNIVERSE)} stocks for parameter optimization")
    
    all_results = {}
    
    for ticker in UNIVERSE:
        print(f"\nOptimizing Bollinger parameters for {ticker}...")
        ticker_results = run_bollinger_optimization(ticker, DATA_DIR, RESULTS_DIR)
        if ticker_results:
            all_results[ticker] = ticker_results
            print(f"Completed {len(ticker_results)} tests for {ticker}")
    
    if all_results:
        # Analyze results
        analysis = analyze_bollinger_results(all_results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(RESULTS_DIR, f'bollinger_optimization_{timestamp}.json')
        
        with open(results_file, 'w') as f:
            json.dump({
                'individual_results': all_results,
                'analysis': analysis,
                'test_date': timestamp
            }, f, indent=2, default=str)
        
        print(f"\nBollinger optimization complete!")
        print(f"Results saved to: {results_file}")
        
        if analysis.get('best_by_return'):
            best = analysis['best_by_return'][0]
            print(f"Best configuration: {best['avg_return_pct']:.1f}% avg return, {best['avg_win_rate_pct']:.1f}% win rate")
        
    else:
        print("No optimization results generated. Check data and parameters.")