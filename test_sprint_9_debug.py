#!/usr/bin/env python3
"""
Quick debug test for Sprint 9 composite QVM strategy
"""

import backtrader as bt
import pandas as pd
import yfinance as yf
import os
import sys
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))
from features.qvm_factors import calculate_quality_factor, calculate_value_factor, calculate_momentum_factor

class DebugCompositeQVMStrategy(bt.Strategy):
    params = (('num_positions', 3), ('universe', None))

    def __init__(self):
        self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
        self.universe = self.p.universe
        self.rebalance_count = 0

    def notify_timer(self, timer, when, *args, **kwargs):
        if self.rebalance_count < 2:  # Only run first 2 rebalances for debugging
            self.rebalance_portfolio()

    def rebalance_portfolio(self):
        print(f'--- Rebalancing on {self.datas[0].datetime.date(0)} ---')
        self.rebalance_count += 1
        
        scores = {}
        # Initialize scores for all tickers in the universe
        for ticker in self.universe:
            scores[ticker] = {'quality': 0, 'value': 0, 'momentum': 0, 'composite': 0}

        # --- STEP 1: Calculate scores for each factor ---
        for ticker in self.universe:
            try:
                # For debug, just calculate momentum to avoid slow API calls
                df = self.getdatabyname(ticker).get_df()
                scores[ticker]['momentum'] = calculate_momentum_factor(df)
                # Use dummy values for quality and value to test ranking
                scores[ticker]['quality'] = 0.1 if ticker in ['CRWD', 'OKTA'] else 0.05
                scores[ticker]['value'] = 0.2 if ticker in ['DDOG', 'NET'] else 0.1
            except Exception as e:
                print(f"Error calculating for {ticker}: {e}")
                scores[ticker]['quality'] = -float('inf')
                scores[ticker]['value'] = -float('inf')
                scores[ticker]['momentum'] = -float('inf')

        # --- STEP 2: Rank stocks on each factor ---
        quality_rank = {ticker: rank for rank, ticker in enumerate(sorted(scores, key=lambda x: scores[x]['quality'], reverse=True), 1)}
        value_rank = {ticker: rank for rank, ticker in enumerate(sorted(scores, key=lambda x: scores[x]['value'], reverse=True), 1)}
        momentum_rank = {ticker: rank for rank, ticker in enumerate(sorted(scores, key=lambda x: scores[x]['momentum'], reverse=True), 1)}

        # Debug: Print factor scores and ranks
        print("Factor Scores:")
        for ticker in self.universe:
            print(f"  {ticker}: Q={scores[ticker]['quality']:.4f}, V={scores[ticker]['value']:.4f}, M={scores[ticker]['momentum']:.4f}")
        
        print("Factor Rankings:")
        print(f"  Quality: {quality_rank}")
        print(f"  Value: {value_rank}")
        print(f"  Momentum: {momentum_rank}")

        # --- STEP 3: Calculate Composite Score ---
        for ticker in self.universe:
            scores[ticker]['composite'] = quality_rank[ticker] + value_rank[ticker] + momentum_rank[ticker]

        print("Composite Scores:")
        for ticker in self.universe:
            print(f"  {ticker}: {scores[ticker]['composite']}")

        # --- STEP 4: Select Final Portfolio ---
        ranked_by_composite = sorted(scores, key=lambda x: scores[x]['composite'])
        final_portfolio = ranked_by_composite[:self.p.num_positions]
        
        print(f"Final Portfolio Selected: {final_portfolio}")

# Quick test function
def debug_test():
    # Extend bt.DataBase to include a get_df method
    bt.feeds.PandasData.get_df = lambda self: self.p.dataname.loc[self.p.fromdate:self.p.todate]
    
    cerebro = bt.Cerebro(stdstats=False)
    universe = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    cerebro.addstrategy(DebugCompositeQVMStrategy, universe=universe)

    # Load just a few stocks for quick testing
    for ticker in universe[:5]:  # Just first 5 stocks
        data_path = os.path.join('data/sprint_1', f'{ticker}.csv')
        if os.path.exists(data_path):
            df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
            cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    print('Running debug test...')
    results = cerebro.run()

if __name__ == '__main__':
    debug_test()