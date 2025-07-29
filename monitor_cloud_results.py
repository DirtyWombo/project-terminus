#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operation Badger - Cloud Results Monitor
Simple script to monitor and aggregate results from parallel cloud backtests

Usage:
    python monitor_cloud_results.py --bucket operation-badger-quant-results
"""

import argparse
import json
import subprocess
import os
from datetime import datetime

def list_results(bucket_name, prefix='sprint13_results/'):
    """List all result files in the GCS bucket"""
    cmd = f"gsutil ls gs://{bucket_name}/{prefix}"
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            return files
        else:
            print(f"Error listing bucket: {result.stderr}")
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []

def download_result(file_path, local_dir='cloud_results'):
    """Download a single result file"""
    os.makedirs(local_dir, exist_ok=True)
    
    filename = os.path.basename(file_path)
    local_path = os.path.join(local_dir, filename)
    
    cmd = f"gsutil cp {file_path} {local_path}"
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return local_path
        else:
            print(f"Error downloading {file_path}: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception downloading {file_path}: {e}")
        return None

def aggregate_results(bucket_name):
    """Download and aggregate all results from the bucket"""
    print(f"*** Monitoring results in gs://{bucket_name}/sprint13_results/")
    
    # List all result files
    result_files = list_results(bucket_name)
    json_files = [f for f in result_files if f.endswith('.json')]
    
    print(f"📊 Found {len(json_files)} completed backtests")
    
    if not json_files:
        print("No results found yet. VMs may still be running.")
        return None
    
    # Download and parse all results
    all_results = []
    failed_downloads = 0
    
    for i, file_path in enumerate(json_files):
        ticker = os.path.basename(file_path).split('_')[0]
        print(f"  Downloading {i+1}/{len(json_files)}: {ticker}...", end='')
        
        local_path = download_result(file_path)
        if local_path:
            try:
                with open(local_path, 'r') as f:
                    data = json.load(f)
                    all_results.append(data)
                print(" ✅")
            except Exception as e:
                print(f" ❌ Parse error: {e}")
                failed_downloads += 1
        else:
            print(" ❌ Download failed")
            failed_downloads += 1
    
    if not all_results:
        print("❌ No results could be downloaded")
        return None
    
    print(f"\n✅ Successfully processed {len(all_results)} results")
    if failed_downloads > 0:
        print(f"⚠️  Failed to process {failed_downloads} results")
    
    # Calculate aggregate metrics
    total_trades = sum(r.get('total_trades', 0) for r in all_results)
    
    # Performance metrics (weighted by number of trades)
    weighted_returns = []
    weighted_sharpes = []
    all_drawdowns = []
    
    for r in all_results:
        trades = r.get('total_trades', 0)
        if trades > 0:
            weighted_returns.append(r.get('annualized_return_pct', 0) * trades)
            weighted_sharpes.append(r.get('sharpe_ratio', 0) * trades)
        all_drawdowns.append(r.get('max_drawdown_pct', 0))
    
    avg_return = sum(weighted_returns) / total_trades if total_trades > 0 else 0
    avg_sharpe = sum(weighted_sharpes) / total_trades if total_trades > 0 else 0
    max_drawdown = max(all_drawdowns) if all_drawdowns else 0
    
    # Summary statistics
    summary = {
        'aggregation_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_tickers_completed': len(all_results),
        'total_trades': total_trades,
        'weighted_avg_return_pct': avg_return,
        'weighted_avg_sharpe': avg_sharpe,
        'max_drawdown_pct': max_drawdown,
        'individual_ticker_results': len(all_results)
    }
    
    # Display results
    print("\n" + "=" * 60)
    print("📈 SPRINT 13 CLOUD BACKTEST - AGGREGATE RESULTS")
    print("=" * 60)
    print(f"Tickers Completed: {summary['total_tickers_completed']}")
    print(f"Total Trades: {summary['total_trades']}")
    print(f"Weighted Avg Return: {summary['weighted_avg_return_pct']:.2f}%")
    print(f"Weighted Avg Sharpe: {summary['weighted_avg_sharpe']:.2f}")
    print(f"Max Drawdown: {summary['max_drawdown_pct']:.2f}%")
    
    # Check success criteria
    print("\n📊 Success Criteria Check:")
    print(f"  Returns > 15%: {'✅ PASS' if avg_return > 15 else '❌ FAIL'} ({avg_return:.2f}%)")
    print(f"  Sharpe > 1.0: {'✅ PASS' if avg_sharpe > 1.0 else '❌ FAIL'} ({avg_sharpe:.2f})")
    print(f"  Drawdown < 25%: {'✅ PASS' if max_drawdown < 25 else '❌ FAIL'} ({max_drawdown:.2f}%)")
    print(f"  Trades > 50: {'✅ PASS' if total_trades > 50 else '❌ FAIL'} ({total_trades})")
    
    # Save aggregate results
    output_file = f"sprint13_cloud_aggregate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'summary': summary,
            'individual_results': all_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    return summary

def main():
    parser = argparse.ArgumentParser(description='Monitor Operation Badger Cloud Results')
    parser.add_argument('--bucket', required=True, help='GCS bucket name')
    parser.add_argument('--watch', action='store_true', help='Continuously monitor (updates every 60s)')
    
    args = parser.parse_args()
    
    if args.watch:
        print("👁️  Watching for results... Press Ctrl+C to stop")
        import time
        while True:
            aggregate_results(args.bucket)
            print("\n⏳ Waiting 60 seconds before next check...")
            time.sleep(60)
    else:
        aggregate_results(args.bucket)

if __name__ == '__main__':
    main()