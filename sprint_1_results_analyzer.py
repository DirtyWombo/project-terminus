# sprint_1_results_analyzer.py
import backtrader as bt
import pandas as pd
import os
import json
from datetime import datetime

class GoldenCross(bt.Strategy):
    params = (('fast', 50), ('slow', 200),)
    def __init__(self):
        self.crossover = bt.indicators.CrossOver(
            bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.fast),
            bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.slow)
        )
    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy()
        elif self.crossover < 0: self.close()

class BollingerBounce(bt.Strategy):
    params = (('period', 20), ('devfactor', 2.0),)
    def __init__(self):
        self.bollinger = bt.indicators.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)
    def next(self):
        if not self.position:
            if self.data.close < self.bollinger.lines.bot: self.buy()
        else:
            if self.data.close > self.bollinger.lines.mid: self.sell()

class ValueFactorPortfolio(bt.Strategy):
    params = (('num_positions', 2),)
    def __init__(self):
        self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
    def notify_timer(self, timer, when, *args, **kwargs): self.rebalance()
    def rebalance(self):
        # Simplified for backtesting - using random selection instead of live P/E calls
        import random
        target_stocks = random.sample([d._name for d in self.datas], self.p.num_positions)
        for d in self.datas:
            if self.getposition(d).size > 0 and d._name not in target_stocks: self.close(data=d)
        target_weight = 1.0 / self.p.num_positions
        for d in self.datas:
            if d._name in target_stocks: self.order_target_percent(data=d, target=target_weight)

def run_strategy_analysis(strategy_class, strategy_name, universe, data_dir, results_dir):
    """Run backtest and capture detailed results"""
    results = {}
    
    for ticker in universe:
        cerebro = bt.Cerebro(stdstats=False)
        cerebro.addstrategy(strategy_class)
        
        data_path = os.path.join(data_dir, f'{ticker}.csv')
        if not os.path.exists(data_path): 
            continue
            
        try:
            data_feed = bt.feeds.PandasData(dataname=pd.read_csv(data_path, index_col='Date', parse_dates=True))
            cerebro.adddata(data_feed, name=ticker)
            cerebro.broker.setcash(10000.0)
            cerebro.broker.setcommission(commission=0.001)
            
            # Add analyzers
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            
            print(f'Running {strategy_name} backtest for {ticker}...')
            result = cerebro.run()[0]
            
            # Extract metrics
            sharpe = result.analyzers.sharpe.get_analysis().get('sharperatio', 0)
            if sharpe is None: sharpe = 0
            
            drawdown = result.analyzers.drawdown.get_analysis()
            trades = result.analyzers.trades.get_analysis()
            returns = result.analyzers.returns.get_analysis()
            
            final_value = cerebro.broker.getvalue()
            total_return = (final_value - 10000) / 10000 * 100
            
            results[ticker] = {
                'final_value': final_value,
                'total_return_pct': total_return,
                'sharpe_ratio': sharpe,
                'max_drawdown_pct': drawdown.get('max', {}).get('drawdown', 0),
                'total_trades': trades.get('total', {}).get('total', 0),
                'winning_trades': trades.get('won', {}).get('total', 0),
                'losing_trades': trades.get('lost', {}).get('total', 0),
                'win_rate_pct': (trades.get('won', {}).get('total', 0) / max(trades.get('total', {}).get('total', 1), 1)) * 100,
                'avg_win_pct': trades.get('won', {}).get('pnl', {}).get('average', 0),
                'avg_loss_pct': trades.get('lost', {}).get('pnl', {}).get('average', 0)
            }
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue
    
    return results

def run_portfolio_analysis(universe, data_dir, results_dir):
    """Run portfolio backtest with multiple assets"""
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(ValueFactorPortfolio)
    
    for ticker in universe:
        data_path = os.path.join(data_dir, f'{ticker}.csv')
        if os.path.exists(data_path):
            df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
            cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
    
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    print('Running Value Factor portfolio backtest...')
    result = cerebro.run()[0]
    
    # Extract metrics
    sharpe = result.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    if sharpe is None: sharpe = 0
    
    drawdown = result.analyzers.drawdown.get_analysis()
    trades = result.analyzers.trades.get_analysis()
    
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - 100000) / 100000 * 100
    
    return {
        'PORTFOLIO': {
            'final_value': final_value,
            'total_return_pct': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': drawdown.get('max', {}).get('drawdown', 0),
            'total_trades': trades.get('total', {}).get('total', 0),
            'winning_trades': trades.get('won', {}).get('total', 0),
            'losing_trades': trades.get('lost', {}).get('total', 0),
            'win_rate_pct': (trades.get('won', {}).get('total', 0) / max(trades.get('total', {}).get('total', 1), 1)) * 100
        }
    }

if __name__ == '__main__':
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/sprint_1'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    # Run all strategy analyses
    strategies = [
        (GoldenCross, 'MA_Crossover'),
        (BollingerBounce, 'Bollinger_Bounce')
    ]
    
    all_results = {}
    
    for strategy_class, strategy_name in strategies:
        print(f"\n=== Analyzing {strategy_name} ===")
        results = run_strategy_analysis(strategy_class, strategy_name, UNIVERSE, DATA_DIR, RESULTS_DIR)
        all_results[strategy_name] = results
    
    # Run portfolio analysis
    print(f"\n=== Analyzing Value Factor Portfolio ===")
    portfolio_results = run_portfolio_analysis(UNIVERSE, DATA_DIR, RESULTS_DIR)
    all_results['Value_Factor_Portfolio'] = portfolio_results
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f'sprint_1_analysis_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    print(f"Analysis complete for {len(all_results)} strategies across {len(UNIVERSE)} assets.")