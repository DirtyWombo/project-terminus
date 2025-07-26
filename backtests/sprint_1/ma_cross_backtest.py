# backtests/sprint_1/ma_cross_backtest.py
import backtrader as bt
import pandas as pd
import os

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

def run_backtest(ticker, data_dir, results_dir):
    cerebro = bt.Cerebro(stdstats=False) # We'll add our own stats
    cerebro.addstrategy(GoldenCross)
    data_path = os.path.join(data_dir, f'{ticker}.csv')
    if not os.path.exists(data_path): return
    data_feed = bt.feeds.PandasData(dataname=pd.read_csv(data_path, index_col='Date', parse_dates=True))
    cerebro.adddata(data_feed, name=ticker)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    print(f'Running MA Cross backtest for {ticker}...')
    results = cerebro.run()
    # ... (documentation logic will be added later) ...

if __name__ == '__main__':
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    if not os.path.exists('../../results/sprint_1'): os.makedirs('../../results/sprint_1')
    for ticker in UNIVERSE:
        run_backtest(ticker, '../../data/sprint_1', '../../results/sprint_1')