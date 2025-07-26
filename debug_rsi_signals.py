# debug_rsi_signals.py
# Debug RSI signal generation

import backtrader as bt
import pandas as pd
import numpy as np
import os

class SimpleRSIDebugStrategy(bt.Strategy):
    """
    Simplified RSI strategy for debugging signal generation
    """
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
    )
    
    def __init__(self):
        self.rsi = bt.indicators.RelativeStrengthIndex(period=self.p.rsi_period)
        self.signal_count = 0
        self.entry_signals = 0
        self.exit_signals = 0
        
    def next(self):
        if len(self.data) < self.p.rsi_period:
            return
            
        current_rsi = self.rsi[0]
        
        # Count signals
        if current_rsi < self.p.rsi_oversold:
            self.entry_signals += 1
            if not self.position:
                self.buy()
                print(f"Day {len(self.data)}: RSI={current_rsi:.1f} - BUY SIGNAL")
                
        elif current_rsi > self.p.rsi_overbought and self.position:
            self.exit_signals += 1
            self.close()
            print(f"Day {len(self.data)}: RSI={current_rsi:.1f} - SELL SIGNAL")

def debug_rsi_signals(ticker='MDB'):
    """
    Debug RSI signal generation for a single stock
    """
    
    DATA_DIR = 'data/sprint_1'
    
    # Load data
    data_path = os.path.join(DATA_DIR, f'{ticker}.csv')
    df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
    
    print(f"Debugging RSI signals for {ticker}")
    print(f"Data period: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Total bars: {len(df)}")
    
    # Quick RSI analysis
    closes = df['Close'].values
    
    # Calculate RSI manually to check ranges
    def calculate_rsi(prices, period=14):
        deltas = np.diff(prices)
        gain = np.where(deltas > 0, deltas, 0)
        loss = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.convolve(gain, np.ones(period)/period, mode='valid')
        avg_loss = np.convolve(loss, np.ones(period)/period, mode='valid')
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    rsi_values = calculate_rsi(closes)
    
    print(f"\nRSI Analysis:")
    print(f"RSI Min: {np.min(rsi_values):.1f}")
    print(f"RSI Max: {np.max(rsi_values):.1f}")
    print(f"RSI Mean: {np.mean(rsi_values):.1f}")
    print(f"Times RSI < 30: {np.sum(rsi_values < 30)}")
    print(f"Times RSI < 35: {np.sum(rsi_values < 35)}")
    print(f"Times RSI > 70: {np.sum(rsi_values > 70)}")
    print(f"Times RSI > 65: {np.sum(rsi_values > 65)}")
    
    # Run backtrader debug
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=df))
    cerebro.addstrategy(SimpleRSIDebugStrategy)
    cerebro.broker.setcash(10000)
    
    print(f"\nRunning backtrader simulation...")
    results = cerebro.run()
    strategy = results[0]
    
    print(f"Entry signals generated: {strategy.entry_signals}")
    print(f"Exit signals generated: {strategy.exit_signals}")
    print(f"Final portfolio value: ${cerebro.broker.getvalue():.2f}")

if __name__ == '__main__':
    debug_rsi_signals('MDB')