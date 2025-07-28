#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 13: Single Ticker QVM Backtest for Cloud Execution
Designed for one-VM-per-ticker parallel processing

This script:
- Accepts a single ticker as command-line argument
- Runs the QVM backtest for that ticker only
- Saves results directly to Google Cloud Storage
- Optimized for fault isolation and simplicity
"""

import argparse
import backtrader as bt
import pandas as pd
import os
import sys
import json
from datetime import datetime
from google.cloud import storage

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from features.qvm_factors_pit import PITDataManager, calculate_quality_factor_pit, calculate_value_factor_pit, calculate_momentum_factor_pit

class SingleTickerQVMStrategy(bt.Strategy):
    """
    QVM Strategy for a single ticker - simplified for cloud execution
    """
    
    params = (
        ('ticker', None),
        ('api_key', None),
        ('rebalance_frequency', 'biweekly')
    )

    def __init__(self):
        # Configure rebalancing frequency
        if self.p.rebalance_frequency == 'weekly':
            self.add_timer(when=bt.Timer.SESSION_START, weekdays=[1], weekcarry=True)
        elif self.p.rebalance_frequency == 'biweekly':
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1, 15], monthcarry=True)
        else:
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
            
        self.ticker = self.p.ticker
        self.rebalance_count = 0
        self.trades = []
        
        # Initialize PIT data manager
        self.pit_manager = PITDataManager(api_key=self.p.api_key)
        
        print(f"Single Ticker QVM Strategy initialized for {self.ticker}")

    def notify_timer(self, timer, when, *args, **kwargs):
        self.evaluate_and_trade()

    def evaluate_and_trade(self):
        current_date = self.datas[0].datetime.date(0)
        date_str = current_date.strftime('%Y-%m-%d')
        
        self.rebalance_count += 1
        
        try:
            # Calculate QVM factors for this ticker
            quality_score = calculate_quality_factor_pit(self.ticker, date_str, self.pit_manager)
            value_score = calculate_value_factor_pit(self.ticker, date_str, self.pit_manager)
            
            # Get price data for momentum
            df = pd.DataFrame({
                'close': [self.data.close[i] for i in range(-252, 1)] if len(self.data) > 252 else []
            })
            momentum_score = calculate_momentum_factor_pit(df) if len(df) > 20 else -float('inf')
            
            # Simple trading logic: go long if all factors are positive
            if (quality_score > 0 and value_score > 0 and momentum_score > 0):
                if self.position.size == 0:
                    self.order_target_percent(target=0.95)  # Use 95% of capital
                    self.trades.append({
                        'date': date_str,
                        'action': 'BUY',
                        'quality': quality_score,
                        'value': value_score,
                        'momentum': momentum_score
                    })
            else:
                if self.position.size > 0:
                    self.close()
                    self.trades.append({
                        'date': date_str,
                        'action': 'SELL',
                        'quality': quality_score,
                        'value': value_score,
                        'momentum': momentum_score
                    })
                    
        except Exception as e:
            # Continue even if factor calculation fails
            print(f"Factor calculation failed for {self.ticker} on {date_str}: {str(e)[:100]}")

def save_to_gcs(bucket_name, blob_name, data):
    """Save results to Google Cloud Storage"""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Convert to JSON and upload
        json_data = json.dumps(data, indent=2)
        blob.upload_from_string(json_data, content_type='application/json')
        
        print(f"Results saved to gs://{bucket_name}/{blob_name}")
        return True
    except Exception as e:
        print(f"Failed to save to GCS: {e}")
        # Save locally as fallback
        local_file = f"/tmp/{os.path.basename(blob_name)}"
        with open(local_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Results saved locally to {local_file}")
        return False

def run_single_ticker_backtest(ticker, bucket_name, rebalance_freq='biweekly'):
    """Run backtest for a single ticker"""
    print(f"Starting backtest for {ticker}")
    print(f"Rebalancing: {rebalance_freq}")
    
    # API key
    api_key = "zVj71CrDyYzfcyxrWkQ4"
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(SingleTickerQVMStrategy, 
                       ticker=ticker, 
                       api_key=api_key,
                       rebalance_frequency=rebalance_freq)

    # Load price data
    price_data_dir = '/app/data/sprint_12'  # Docker container path
    data_path = os.path.join(price_data_dir, f'{ticker}.csv')
    
    if not os.path.exists(data_path):
        # Try alternate path
        price_data_dir = 'data/sprint_12'  # Local path
        data_path = os.path.join(price_data_dir, f'{ticker}.csv')
    
    if os.path.exists(data_path):
        try:
            df = pd.read_csv(data_path, index_col=0, parse_dates=True, skiprows=[1,2])
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
        except Exception as e:
            print(f"Error loading data for {ticker}: {str(e)}")
            return None
    else:
        print(f"No price data found for {ticker}")
        return None

    # Set capital and commission
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    initial_value = cerebro.broker.getvalue()
    
    # Run backtest
    start_time = datetime.now()
    results = cerebro.run()
    end_time = datetime.now()
    
    strat = results[0]
    final_value = cerebro.broker.getvalue()

    # Extract results
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    returns_analysis = strat.analyzers.returns.get_analysis()
    trades_analysis = strat.analyzers.trades.get_analysis()
    
    sharpe_ratio = sharpe_analysis.get('sharperatio', 0) or 0
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0) or 0
    ann_return = returns_analysis.get('rnorm100', 0) or 0
    
    total_trades = trades_analysis.get('total', {}).get('total', 0) or 0
    winning_trades = trades_analysis.get('won', {}).get('total', 0) or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_return = (final_value - initial_value) / initial_value * 100

    # Create results
    results_data = {
        'ticker': ticker,
        'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'rebalancing_frequency': rebalance_freq,
        'initial_value': initial_value,
        'final_value': final_value,
        'total_return_pct': total_return,
        'annualized_return_pct': ann_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown_pct': max_drawdown,
        'total_trades': total_trades,
        'win_rate_pct': win_rate,
        'rebalances': strat.rebalance_count,
        'backtest_duration_seconds': (end_time - start_time).total_seconds(),
        'trade_history': strat.trades
    }
    
    # Save to GCS
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_name = f"sprint13_results/{ticker}_{rebalance_freq}_{timestamp}.json"
    
    save_to_gcs(bucket_name, blob_name, results_data)
    
    # Print summary
    print(f"\n{ticker} Backtest Complete:")
    print(f"  Return: {ann_return:.2f}%")
    print(f"  Sharpe: {sharpe_ratio:.2f}")
    print(f"  Drawdown: {max_drawdown:.2f}%")
    print(f"  Trades: {total_trades}")
    
    return results_data

def main():
    parser = argparse.ArgumentParser(description='Single Ticker QVM Backtest')
    parser.add_argument('--ticker', required=True, help='Stock ticker to backtest')
    parser.add_argument('--bucket', required=True, help='GCS bucket name for results')
    parser.add_argument('--rebalance-freq', default='biweekly', 
                       choices=['weekly', 'biweekly', 'monthly'], 
                       help='Rebalancing frequency')
    
    args = parser.parse_args()
    
    # Run backtest
    run_single_ticker_backtest(args.ticker, args.bucket, args.rebalance_freq)

if __name__ == '__main__':
    main()