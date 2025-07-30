#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 15 Cloud: QVM with Risk Parity Overlay - Final Validation

This script implements the final, most sophisticated version of the QVM strategy
with institutional-grade risk management through Inverse Volatility Weighting.

Key Features:
- Command-line argument support for parallel execution
- Google Cloud Storage integration for result collection
- Weekly rebalancing for maximum trading opportunities
- Risk Parity (Inverse Volatility Weighting) for drawdown control
- Optimized for containerized execution
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
        
        print(f'[DEBUG] Starting rebalance #{self.rebalance_count} on {current_date}')
        
        scores = {}
        valid_tickers = 0
        
        # Initialize scores
        print(f'[DEBUG] Initializing scores for {len(self.universe)} stocks')
        for ticker in self.universe:
            scores[ticker] = {'quality': -float('inf'), 'value': -float('inf'), 'momentum': -float('inf'), 'composite': 999}

        # Calculate QVM factors
        print(f'[DEBUG] Starting factor calculations...')
        for i, ticker in enumerate(self.universe):
            print(f'[DEBUG] Processing {ticker} ({i+1}/{len(self.universe)})')
            try:
                print(f'[DEBUG]   Calculating quality factor for {ticker}...')
                quality_score = calculate_quality_factor_pit(ticker, date_str, self.pit_manager)
                scores[ticker]['quality'] = quality_score
                print(f'[DEBUG]   Quality score: {quality_score}')
                
                print(f'[DEBUG]   Calculating value factor for {ticker}...')
                value_score = calculate_value_factor_pit(ticker, date_str, self.pit_manager)
                scores[ticker]['value'] = value_score
                print(f'[DEBUG]   Value score: {value_score}')
                
                print(f'[DEBUG]   Calculating momentum factor for {ticker}...')
                data_feed = self.getdatabyname(ticker)
                if data_feed is not None:
                    df = data_feed.get_df()
                    momentum_score = calculate_momentum_factor_pit(df)
                    scores[ticker]['momentum'] = momentum_score
                    print(f'[DEBUG]   Momentum score: {momentum_score}')
                else:
                    print(f'[DEBUG]   No data feed found for {ticker}')
                
                if (quality_score != -float('inf') and 
                    value_score != -float('inf') and 
                    momentum_score != -float('inf')):
                    valid_tickers += 1
                    print(f'[DEBUG]   {ticker} has valid scores')
                else:
                    print(f'[DEBUG]   {ticker} has invalid scores')
                
            except Exception as e:
                print(f'[DEBUG] ERROR processing {ticker}: {e}')
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
        
        # --- SPRINT 15: RISK PARITY (INVERSE VOLATILITY WEIGHTING) ---
        print(f'[RISK PARITY] Calculating inverse volatility weights for {len(final_portfolio)} stocks')
        
        volatilities = {}
        target_weights = {}
        
        if final_portfolio:
            # Calculate 60-day historical volatility for each stock
            for ticker in final_portfolio:
                try:
                    data_feed = self.getdatabyname(ticker)
                    if data_feed is not None:
                        df = data_feed.get_df()
                        # Calculate daily returns and 60-day rolling volatility
                        daily_returns = df['Close'].pct_change().dropna()
                        if len(daily_returns) >= 60:
                            volatility = daily_returns.tail(60).std()
                            if volatility > 0:
                                volatilities[ticker] = volatility
                                print(f'[RISK PARITY] {ticker}: volatility = {volatility:.4f}')
                            else:
                                print(f'[RISK PARITY] {ticker}: zero volatility, excluding from portfolio')
                        else:
                            print(f'[RISK PARITY] {ticker}: insufficient data (<60 days), excluding')
                    else:
                        print(f'[RISK PARITY] {ticker}: no data feed found, excluding')
                except Exception as e:
                    print(f'[RISK PARITY] {ticker}: error calculating volatility: {e}')
            
            # Calculate inverse volatility weights
            if volatilities:
                inverse_volatilities = {ticker: 1.0 / vol for ticker, vol in volatilities.items()}
                total_inverse_vol = sum(inverse_volatilities.values())
                
                if total_inverse_vol > 0:
                    for ticker, inv_vol in inverse_volatilities.items():
                        target_weights[ticker] = inv_vol / total_inverse_vol
                    
                    print(f'[RISK PARITY] Target weights calculated:')
                    for ticker, weight in target_weights.items():
                        print(f'[RISK PARITY]   {ticker}: {weight:.3f} ({weight*100:.1f}%)')
                else:
                    print(f'[RISK PARITY] ERROR: Total inverse volatility is zero')
            else:
                print(f'[RISK PARITY] ERROR: No valid volatilities calculated, falling back to equal weights')
                # Fallback to equal weighting if risk calculation fails
                target_weight = 1.0 / len(final_portfolio)
                target_weights = {ticker: target_weight for ticker in final_portfolio}
        
        # --- EXECUTION ---
        current_holdings = [d._name for d in self.datas if self.getposition(d).size > 0]
        
        # Sell stocks no longer in the portfolio
        for ticker in current_holdings:
            if ticker not in final_portfolio:
                print(f'[RISK PARITY] Selling {ticker} (no longer in portfolio)')
                self.close(data=self.getdatabyname(ticker))
        
        # Buy stocks in the target portfolio with risk-adjusted weights
        for ticker, weight in target_weights.items():
            data_feed = self.getdatabyname(ticker)
            if data_feed and weight > 0:
                print(f'[RISK PARITY] Setting {ticker} to {weight:.3f} weight')
                self.order_target_percent(data=data_feed, target=weight)
    
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
    print(f"[DEBUG] Worker {worker_id}: Starting backtest with {len(universe_subset)} stocks")
    print(f"[DEBUG] Stocks: {universe_subset}")
    print(f"[DEBUG] Rebalancing: {rebalance_freq}")
    
    # API key
    api_key = "zVj71CrDyYzfcyxrWkQ4"
    print(f"[DEBUG] Using API key: {api_key[:10]}...")
    
    # Extend bt.DataBase
    print("[DEBUG] Extending backtrader data feeds...")
    bt.feeds.PandasData.get_df = lambda self: self.p.dataname.loc[self.p.fromdate:self.p.todate]
    
    print("[DEBUG] Initializing Cerebro...")
    cerebro = bt.Cerebro(stdstats=False)
    print("[DEBUG] Adding strategy...")
    cerebro.addstrategy(CloudQVMStrategy, 
                       universe=universe_subset, 
                       api_key=api_key,
                       rebalance_frequency=rebalance_freq)

    # Load price data
    price_data_dir = 'data/sprint_12'
    loaded_count = 0
    
    print(f"[DEBUG] Loading price data from {price_data_dir}...")
    for i, ticker in enumerate(universe_subset):
        print(f"[DEBUG] Loading data for {ticker} ({i+1}/{len(universe_subset)})")
        data_path = os.path.join(price_data_dir, f'{ticker}.csv')
        print(f"[DEBUG] Looking for file: {data_path}")
        
        if os.path.exists(data_path):
            print(f"[DEBUG] File exists, reading CSV...")
            try:
                df = pd.read_csv(data_path, index_col=0, parse_dates=True, skiprows=[1,2])
                df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                print(f"[DEBUG] Data shape: {df.shape}, date range: {df.index[0]} to {df.index[-1]}")
                cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
                loaded_count += 1
                print(f"[DEBUG] Successfully added {ticker} to cerebro")
            except Exception as e:
                print(f"[DEBUG] ERROR loading {ticker}: {str(e)}")
        else:
            print(f"[DEBUG] WARNING: File not found for {ticker}")

    print(f"[DEBUG] Loaded {loaded_count}/{len(universe_subset)} stocks")

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
    
    # Save results to mounted volume for VM access
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f'results/sprint13_cloud_worker_{worker_id}_{timestamp}.json'
    
    # Ensure results directory exists
    os.makedirs('results', exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"Worker {worker_id} completed:")
    print(f"  Return: {ann_return:.2f}%")
    print(f"  Sharpe: {sharpe_ratio:.2f}")
    print(f"  Drawdown: {max_drawdown:.2f}%")
    print(f"  Trades: {total_trades}")
    
    # Try Python GCS upload directly
    print(f"Results saved to {results_file}")
    
    # Upload to GCS using Python client
    if bucket_name:
        try:
            print(f"Attempting direct GCS upload to gs://{bucket_name}/sprint13_results/")
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob_name = f"sprint13_results/{os.path.basename(results_file)}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(results_file)
            print(f"✅ Results successfully uploaded to gs://{bucket_name}/{blob_name}")
        except Exception as e:
            print(f"❌ Failed to upload to GCS: {e}")
            print(f"Results saved locally at {results_file}")
    else:
        print(f"No bucket specified, results saved locally at {results_file}")
    
    return results_data

def main():
    print("[DEBUG] Starting main function...")
    
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
    
    print("[DEBUG] Parsing arguments...")
    args = parser.parse_args()
    print(f"[DEBUG] Arguments parsed: start_idx={args.start_idx}, end_idx={args.end_idx}, worker_id={args.worker_id}")
    
    # Load universe subset
    print(f"[DEBUG] Loading universe subset from {args.universe_file}...")
    universe_subset = load_universe_subset(args.universe_file, args.start_idx, args.end_idx)
    print(f"[DEBUG] Loaded {len(universe_subset)} stocks: {universe_subset}")
    
    if not universe_subset:
        print(f"No stocks found in range {args.start_idx}-{args.end_idx}")
        return
    
    # Run backtest
    print("[DEBUG] Starting backtest...")
    run_cloud_backtest(universe_subset, args.rebalance_freq, args.worker_id, args.bucket)
    print("[DEBUG] Backtest completed!")

if __name__ == '__main__':
    main()