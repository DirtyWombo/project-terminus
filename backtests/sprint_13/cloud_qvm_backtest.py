#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 13 Cloud: Parallel QVM Backtest for Google Cloud Platform

This script is designed to run in a cloud environment with parallel execution.
Each instance processes a subset of the S&P 500 universe and uploads results
to Google Cloud Storage.

Key Features:
- Command-line argument support for parallel execution
- Google Cloud Storage integration for result collection
- Optimized for containerized execution
- Supports both weekly and bi-weekly rebalancing
"""

import argparse
import backtrader as bt
import pandas as pd
import os
import sys
import json
import time
from datetime import datetime
from google.cloud import storage

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from features.qvm_factors_pit import PITDataManager, calculate_quality_factor_pit, calculate_value_factor_pit, calculate_momentum_factor_pit

class CloudQVMStrategy(bt.Strategy):
    """
    Cloud-optimized QVM Strategy for parallel execution
    """
    
    params = (
        ('num_positions', 20),
        ('universe', None),
        ('api_key', None),
        ('rebalance_frequency', 'biweekly')  # 'weekly' or 'biweekly'
    )

    def __init__(self):
        # Configure rebalancing frequency
        if self.p.rebalance_frequency == 'weekly':
            self.add_timer(when=bt.Timer.SESSION_START, weekdays=[1], weekcarry=True)
        elif self.p.rebalance_frequency == 'biweekly':
            # Rebalance every 2 weeks (1st and 15th, approximately)
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1, 15], monthcarry=True)
        else:
            # Default to monthly
            self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
            
        self.universe = self.p.universe
        self.rebalance_count = 0
        
        # Initialize PIT data manager
        self.pit_manager = PITDataManager(api_key=self.p.api_key)
        
        print(f"Cloud QVM Strategy initialized: {len(self.universe)} stocks, {self.p.rebalance_frequency} rebalancing")

    def notify_timer(self, timer, when, *args, **kwargs):
        self.rebalance_portfolio()

    def rebalance_portfolio(self):
        current_date = self.datas[0].datetime.date(0)
        date_str = current_date.strftime('%Y-%m-%d')
        
        self.rebalance_count += 1
        
        # Reduce verbosity for cloud execution
        if self.rebalance_count % 10 == 1:
            print(f'Rebalancing #{self.rebalance_count} on {current_date}')
        
        scores = {}
        valid_tickers = 0
        
        # Initialize scores
        for ticker in self.universe:
            scores[ticker] = {'quality': -float('inf'), 'value': -float('inf'), 'momentum': -float('inf'), 'composite': 999}

        # Calculate QVM factors
        for ticker in self.universe:
            try:
                quality_score = calculate_quality_factor_pit(ticker, date_str, self.pit_manager)
                scores[ticker]['quality'] = quality_score
                
                value_score = calculate_value_factor_pit(ticker, date_str, self.pit_manager)
                scores[ticker]['value'] = value_score
                
                data_feed = self.getdatabyname(ticker)
                if data_feed is not None:
                    df = data_feed.get_df()
                    momentum_score = calculate_momentum_factor_pit(df)
                    scores[ticker]['momentum'] = momentum_score
                
                if (quality_score != -float('inf') and 
                    value_score != -float('inf') and 
                    momentum_score != -float('inf')):
                    valid_tickers += 1
                
            except Exception:
                pass  # Silent fail for cloud execution

        # Rank and select portfolio
        quality_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['quality'], reverse=True), 1)}
        value_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['value'], reverse=True), 1)}
        momentum_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['momentum'], reverse=True), 1)}

        for ticker in self.universe:
            scores[ticker]['composite'] = quality_rank[ticker] + value_rank[ticker] + momentum_rank[ticker]

        ranked_by_composite = sorted(scores, key=lambda x: scores[x]['composite'])
        valid_ranked_stocks = [ticker for ticker in ranked_by_composite 
                              if all(scores[ticker][factor] != -float('inf') 
                                   for factor in ['quality', 'value', 'momentum'])]
        
        final_portfolio = valid_ranked_stocks[:self.p.num_positions]
        
        # Execute trades
        target_weight = 1.0 / self.p.num_positions if final_portfolio else 0
        current_holdings = [d._name for d in self.datas if self.getposition(d).size > 0]
        
        for ticker in current_holdings:
            if ticker not in final_portfolio:
                self.close(data=self.getdatabyname(ticker))

        for ticker in final_portfolio:
            data_feed = self.getdatabyname(ticker)
            if data_feed:
                self.order_target_percent(data=data_feed, target=target_weight)
    
    def getdatabyname(self, name):
        for d in self.datas:
            if hasattr(d, '_name') and d._name == name:
                return d
        return None

def upload_to_gcs(bucket_name, source_file, destination_blob):
    """Upload a file to Google Cloud Storage"""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob)
        blob.upload_from_filename(source_file)
        print(f"Results uploaded to gs://{bucket_name}/{destination_blob}")
        return True
    except Exception as e:
        print(f"Failed to upload to GCS: {e}")
        return False

def load_universe_subset(universe_file, start_idx, end_idx):
    """Load a subset of the universe for parallel processing"""
    universe = []
    
    if os.path.exists(universe_file):
        with open(universe_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    universe.append(line)
    
    # Return the specified subset
    return universe[start_idx:end_idx]

def run_cloud_backtest(universe_subset, rebalance_freq, worker_id, bucket_name):
    """
    Run backtest on a subset of the universe for cloud parallel execution
    """
    print(f"Worker {worker_id}: Starting backtest with {len(universe_subset)} stocks")
    print(f"Stocks: {universe_subset}")
    print(f"Rebalancing: {rebalance_freq}")
    
    # API key
    api_key = "zVj71CrDyYzfcyxrWkQ4"
    
    # Extend bt.DataBase
    bt.feeds.PandasData.get_df = lambda self: self.p.dataname.loc[self.p.fromdate:self.p.todate]
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(CloudQVMStrategy, 
                       universe=universe_subset, 
                       api_key=api_key,
                       rebalance_frequency=rebalance_freq)

    # Load price data
    price_data_dir = 'data/sprint_12'
    loaded_count = 0
    
    for ticker in universe_subset:
        data_path = os.path.join(price_data_dir, f'{ticker}.csv')
        if os.path.exists(data_path):
            try:
                df = pd.read_csv(data_path, index_col=0, parse_dates=True, skiprows=[1,2])
                df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
                loaded_count += 1
            except Exception as e:
                print(f"Error loading {ticker}: {str(e)[:50]}")

    print(f"Loaded {loaded_count}/{len(universe_subset)} stocks")

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
        'worker_id': worker_id,
        'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'universe_subset': universe_subset,
        'universe_size': len(universe_subset),
        'data_coverage': loaded_count,
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
        'backtest_duration_seconds': (end_time - start_time).total_seconds()
    }
    
    # Save results locally
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f'sprint13_cloud_worker_{worker_id}_{timestamp}.json'
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"Worker {worker_id} completed:")
    print(f"  Return: {ann_return:.2f}%")
    print(f"  Sharpe: {sharpe_ratio:.2f}")
    print(f"  Drawdown: {max_drawdown:.2f}%")
    print(f"  Trades: {total_trades}")
    
    # Upload to cloud storage if bucket specified
    if bucket_name:
        gcs_path = f"sprint13_results/{results_file}"
        upload_to_gcs(bucket_name, results_file, gcs_path)
    
    return results_data

def main():
    parser = argparse.ArgumentParser(description='Cloud QVM Backtest Worker')
    parser.add_argument('--start-idx', type=int, required=True, help='Start index for universe subset')
    parser.add_argument('--end-idx', type=int, required=True, help='End index for universe subset')
    parser.add_argument('--worker-id', type=str, required=True, help='Unique worker identifier')
    parser.add_argument('--rebalance-freq', type=str, default='biweekly', 
                       choices=['weekly', 'biweekly', 'monthly'], help='Rebalancing frequency')
    parser.add_argument('--bucket', type=str, help='GCS bucket name for results')
    parser.add_argument('--universe-file', type=str, 
                       default='data/sprint_12/curated_sp500_universe.txt',
                       help='Path to universe file')
    
    args = parser.parse_args()
    
    # Load universe subset
    universe_subset = load_universe_subset(args.universe_file, args.start_idx, args.end_idx)
    
    if not universe_subset:
        print(f"No stocks found in range {args.start_idx}-{args.end_idx}")
        return
    
    # Run backtest
    run_cloud_backtest(universe_subset, args.rebalance_freq, args.worker_id, args.bucket)

if __name__ == '__main__':
    main()