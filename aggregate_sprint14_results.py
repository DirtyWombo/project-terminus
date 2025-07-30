#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 14 Results Aggregation Script
Compile and analyze all worker results from the weekly QVM backtest
"""

import json
import os
from datetime import datetime
from google.cloud import storage

def aggregate_sprint14_results():
    """Download and aggregate all Sprint 14 results"""
    print("=" * 80)
    print("SPRINT 15: QVM WITH RISK PARITY - FINAL VALIDATION RESULTS")
    print("=" * 80)
    
    # Initialize GCS client
    client = storage.Client(project='operation-badger-quant')
    bucket = client.bucket('operation-badger-quant-results-bucket')
    
    # Download all results
    blobs = bucket.list_blobs(prefix='sprint13_results/')
    all_results = []
    
    print("\nDownloading results from all workers...")
    for blob in blobs:
        if blob.name.endswith('.json'):
            try:
                content = blob.download_as_text()
                result = json.loads(content)
                all_results.append(result)
                print(f"Downloaded: {result['worker_id']} - {result['universe_size']} stocks")
            except Exception as e:
                print(f"Failed to download {blob.name}: {e}")
    
    if not all_results:
        print("No results found!")
        return
    
    # Calculate aggregated metrics
    print(f"\nProcessing results from {len(all_results)} workers...")
    
    total_trades = sum(r.get('total_trades', 0) for r in all_results)
    total_rebalances = sum(r.get('rebalances', 0) for r in all_results)
    total_universe_size = sum(r.get('universe_size', 0) for r in all_results)
    total_data_coverage = sum(r.get('data_coverage', 0) for r in all_results)
    
    # Performance metrics (averages)
    returns = [r.get('annualized_return_pct', 0) for r in all_results if r.get('annualized_return_pct')]
    sharpe_ratios = [r.get('sharpe_ratio', 0) for r in all_results if r.get('sharpe_ratio')]
    drawdowns = [r.get('max_drawdown_pct', 0) for r in all_results if r.get('max_drawdown_pct')]
    win_rates = [r.get('win_rate_pct', 0) for r in all_results if r.get('win_rate_pct')]
    
    aggregated_metrics = {
        'strategy': 'QVM with Risk Parity Overlay (Final Validation)',
        'sprint': 15,
        'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_workers': len(all_results),
        'total_universe_size': total_universe_size,
        'total_data_coverage': total_data_coverage,
        'coverage_percentage': (total_data_coverage / total_universe_size * 100) if total_universe_size > 0 else 0,
        'total_trades': total_trades,
        'total_rebalances': total_rebalances,
        'avg_annualized_return_pct': sum(returns) / len(returns) if returns else 0,
        'avg_sharpe_ratio': sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0,
        'avg_max_drawdown_pct': sum(drawdowns) / len(drawdowns) if drawdowns else 0,
        'avg_win_rate_pct': sum(win_rates) / len(win_rates) if win_rates else 0,
        'rebalancing_frequency': 'weekly'
    }
    
    # Create complete summary
    sprint14_summary = {
        'sprint_14_summary': aggregated_metrics,
        'individual_worker_results': all_results
    }
    
    # Save aggregated results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f'sprint15_final_results_{timestamp}.json'
    
    with open(results_file, 'w') as f:
        json.dump(sprint14_summary, f, indent=2)
    
    print(f"\nSPRINT 14 FINAL RESULTS SAVED TO: {results_file}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SPRINT 15: QVM WITH RISK PARITY - FINAL VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Strategy: QVM with Risk Parity Overlay (Final Validation)")
    print(f"Total Workers: {aggregated_metrics['total_workers']}")
    print(f"Universe Coverage: {aggregated_metrics['total_universe_size']} stocks ({aggregated_metrics['coverage_percentage']:.1f}%)")
    print(f"Rebalancing: {aggregated_metrics['rebalancing_frequency']} ({aggregated_metrics['total_rebalances']} total rebalances)")
    print(f"Total Trades: {aggregated_metrics['total_trades']}")
    print()
    print("PERFORMANCE METRICS:")
    print(f"  Annualized Return: {aggregated_metrics['avg_annualized_return_pct']:.2f}%")
    print(f"  Sharpe Ratio: {aggregated_metrics['avg_sharpe_ratio']:.3f}")
    print(f"  Max Drawdown: {aggregated_metrics['avg_max_drawdown_pct']:.2f}%")
    print(f"  Win Rate: {aggregated_metrics['avg_win_rate_pct']:.1f}%")
    print()
    print("DEPLOYMENT CRITERIA ASSESSMENT:")
    print(f"  Annualized Return > 15%: {aggregated_metrics['avg_annualized_return_pct']:.2f}% {'PASS' if aggregated_metrics['avg_annualized_return_pct'] > 15 else 'FAIL'}")
    print(f"  Sharpe Ratio > 1.0: {aggregated_metrics['avg_sharpe_ratio']:.3f} {'PASS' if aggregated_metrics['avg_sharpe_ratio'] > 1.0 else 'FAIL'}")
    print(f"  Max Drawdown < 25%: {aggregated_metrics['avg_max_drawdown_pct']:.2f}% {'PASS' if aggregated_metrics['avg_max_drawdown_pct'] < 25 else 'FAIL'}")
    print(f"  Total Trades > 50: {aggregated_metrics['total_trades']} {'PASS' if aggregated_metrics['total_trades'] > 50 else 'FAIL'}")
    print("=" * 80)
    
    return sprint14_summary, results_file

if __name__ == '__main__':
    aggregate_sprint14_results()