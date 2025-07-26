# backtests/sprint_1/value_factor_backtest.py
import backtrader as bt
import pandas as pd
import yfinance as yf
import os

class ValueFactorPortfolio(bt.Strategy):
    params = (('num_positions', 2),) # Top 20% of 10 stocks
    def __init__(self):
        self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
    def notify_timer(self, timer, when, *args, **kwargs): self.rebalance()
    def rebalance(self):
        pe_ratios = {}
        for d in self.datas:
            try: pe_ratios[d._name] = yf.Ticker(d._name).info.get('trailingPE', float('inf'))
            except: pe_ratios[d._name] = float('inf')
        ranked = sorted(pe_ratios.items(), key=lambda item: item[1])
        target_stocks = [item[0] for item in ranked[:self.p.num_positions]]
        for d in self.datas:
            if self.getposition(d).size > 0 and d._name not in target_stocks: self.close(data=d)
        target_weight = 1.0 / self.p.num_positions
        for d in self.datas:
            if d._name in target_stocks: self.order_target_percent(data=d, target=target_weight)

def run_portfolio_backtest(universe, data_dir, results_dir):
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(ValueFactorPortfolio)
    for ticker in universe:
        data_path = os.path.join(data_dir, f'{ticker}.csv')
        df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
        cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    print('Running Value Factor portfolio backtest...')
    results = cerebro.run()

if __name__ == '__main__':
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    run_portfolio_backtest(UNIVERSE, '../../data/sprint_1', '../../results/sprint_1')