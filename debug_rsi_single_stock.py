#!/usr/bin/env python3
"""
Sprint 7.1 Task 2 & 3: Debug single stock RSI backtest with logging
"""

import backtrader as bt
import pandas as pd
import os
from datetime import datetime

class DebugRSIStrategy(bt.Strategy):
    """Simple RSI strategy with heavy debug logging"""
    
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 30),  # Start with 30, then test 45
        ('rsi_overbought', 70),
    )
    
    def __init__(self):
        self.rsi = bt.indicators.RelativeStrengthIndex(period=self.p.rsi_period)
        self.bar_count = 0
        
    def next(self):
        self.bar_count += 1
        current_rsi = self.rsi[0]
        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0)
        
        # Log every bar for first 20 bars, then every 10th bar
        if self.bar_count <= 20 or self.bar_count % 10 == 0:
            print(f"Bar {self.bar_count}: {current_date}, Price: ${current_price:.2f}, "
                  f"RSI: {current_rsi:.2f}, Position: {bool(self.position)}")
        
        # ALWAYS log RSI extreme conditions
        if current_rsi <= self.p.rsi_oversold:
            print(f"*** OVERSOLD: {current_date}, RSI: {current_rsi:.2f} <= {self.p.rsi_oversold}")
            
        if current_rsi >= self.p.rsi_overbought:
            print(f"*** OVERBOUGHT: {current_date}, RSI: {current_rsi:.2f} >= {self.p.rsi_overbought}")
        
        # Entry logic with logging
        if current_rsi < self.p.rsi_oversold and not self.position:
            print(f"==> BUY SIGNAL: {current_date}, RSI: {current_rsi:.2f}, Price: ${current_price:.2f}")
            order = self.buy()
            if order:
                print(f"==> BUY ORDER PLACED")
            else:
                print(f"==> BUY ORDER FAILED!")
                
        # Exit logic with logging  
        elif self.position and current_rsi > self.p.rsi_overbought:
            print(f"==> SELL SIGNAL: {current_date}, RSI: {current_rsi:.2f}, Price: ${current_price:.2f}")
            order = self.close()
            if order:
                print(f"==> SELL ORDER PLACED")
    
    def notify_trade(self, trade):
        if trade.isclosed:
            print(f"TRADE CLOSED: PnL: ${trade.pnl:.2f}")

def run_debug_backtest(ticker, rsi_oversold_level=30):
    """Run debug backtest on single stock"""
    
    print(f"\n{'='*60}")
    print(f"DEBUG BACKTEST: {ticker} with RSI oversold = {rsi_oversold_level}")
    print(f"{'='*60}")
    
    # Load data
    data_path = f"data/sprint_1/{ticker}.csv"
    if not os.path.exists(data_path):
        print(f"Error: Data file not found for {ticker}")
        return None
    
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')
    
    # Create backtrader data feed
    data_feed = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open='Open',
        high='High', 
        low='Low',
        close='Close',
        volume='Volume',
        openinterest=None
    )
    
    # Create cerebro engine
    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed, name=ticker)
    cerebro.addstrategy(DebugRSIStrategy, rsi_oversold=rsi_oversold_level)
    
    # Set initial cash
    cerebro.broker.setcash(10000)
    
    print(f"Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}")
    print(f"Starting backtest...\n")
    
    # Run backtest
    results = cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    print(f"\nFinal Portfolio Value: ${final_value:.2f}")
    print(f"Total Return: ${final_value - 10000:.2f}")
    
    return results

def main():
    """Main debugging function"""
    
    print("Sprint 7.1 Task 2 & 3: RSI Debug Analysis")
    print("This will show us exactly what the RSI strategy is doing")
    
    # Task 2: Debug with normal parameters
    print("\n=== TASK 2: NORMAL PARAMETERS (RSI oversold = 30) ===")
    run_debug_backtest('CRWD', rsi_oversold_level=30)
    
    # Task 3: "Idiot check" with loose parameters  
    print("\n=== TASK 3: LOOSE PARAMETERS (RSI oversold = 45) ===")
    run_debug_backtest('CRWD', rsi_oversold_level=45)
    
if __name__ == "__main__":
    main()