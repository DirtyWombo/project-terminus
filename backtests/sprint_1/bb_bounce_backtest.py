# backtests/sprint_1/bb_bounce_backtest.py
import backtrader as bt
import pandas as pd
import os

class BollingerBounce(bt.Strategy):
    params = (('period', 20), ('devfactor', 2.0),)
    def __init__(self):
        self.bollinger = bt.indicators.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)
    def next(self):
        if not self.position:
            if self.data.close < self.bollinger.lines.bot: self.buy()
        else:
            if self.data.close > self.bollinger.lines.mid: self.sell()

# The run_backtest function is nearly identical to the previous script.
# The only change is `cerebro.addstrategy(BollingerBounce)`.
def run_backtest(ticker, data_dir, results_dir):
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(BollingerBounce) # <-- The only change
    data_path = os.path.join(data_dir, f'{ticker}.csv')
    if not os.path.exists(data_path): return
    data_feed = bt.feeds.PandasData(dataname=pd.read_csv(data_path, index_col='Date', parse_dates=True))
    cerebro.adddata(data_feed, name=ticker)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    print(f'Running BB Bounce backtest for {ticker}...')
    results = cerebro.run()

if __name__ == '__main__':
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    for ticker in UNIVERSE:
        run_backtest(ticker, '../../data/sprint_1', '../../results/sprint_1')