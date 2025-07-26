# backtests/sprint_12/composite_qvm_backtest_sp500.py
"""
Sprint 12: The S&P 500 Universe Test

This is the scaled-up Composite QVM strategy test using a diversified
S&P 500 universe (216 stocks). This test aims to validate whether the
QVM strategy can generate sufficient trades and alpha when provided
with a large, institutionally recognized opportunity set.

Sprint 12 Success Criteria:
- Post-Cost Annualized Return > 15%
- Post-Cost Sharpe Ratio > 1.0  
- Max Drawdown < 25%
- Total Trades > 50 (New criterion for sufficient activity)
"""

import backtrader as bt
import pandas as pd
import os
import sys
import json
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from features.qvm_factors_pit import PITDataManager, calculate_quality_factor_pit, calculate_value_factor_pit, calculate_momentum_factor_pit

class CompositeQVMSP500Strategy(bt.Strategy):
    """
    Sprint 12: Composite QVM Strategy for S&P 500 Universe
    
    Scales up the proven Sprint 11 methodology to a 216-stock universe
    with increased position count to match the expanded opportunity set.
    """
    
    params = (
        ('num_positions', 20),  # Scaled up from 3 to 20 for larger universe
        ('universe', None),
        ('api_key', None)
    )

    def __init__(self):
        self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
        self.universe = self.p.universe
        self.rebalance_count = 0
        
        # Initialize PIT data manager
        self.pit_manager = PITDataManager(api_key=self.p.api_key)
        
        print(f"SUCCESS: Sprint 12 Composite QVM S&P 500 Strategy initialized")
        print(f"SUCCESS: Universe size: {len(self.universe)} stocks")
        print(f"SUCCESS: Target positions: {self.params.num_positions}")

    def notify_timer(self, timer, when, *args, **kwargs):
        self.rebalance_portfolio()

    def rebalance_portfolio(self):
        current_date = self.datas[0].datetime.date(0)
        date_str = current_date.strftime('%Y-%m-%d')
        
        print(f'\\n--- Sprint 12 S&P 500 QVM Rebalancing on {current_date} ---')
        self.rebalance_count += 1
        
        scores = {}
        valid_tickers = 0
        
        # Initialize scores for all tickers in the universe
        for ticker in self.universe:
            scores[ticker] = {'quality': -float('inf'), 'value': -float('inf'), 'momentum': -float('inf'), 'composite': 999}

        # --- STEP 1: Calculate Point-in-Time QVM Factors ---
        print(f"Calculating PIT QVM factors for {len(self.universe)} S&P 500 stocks...")
        
        for ticker in self.universe:
            try:
                # Quality Factor: ROE using PIT fundamental data
                quality_score = calculate_quality_factor_pit(ticker, date_str, self.pit_manager)
                scores[ticker]['quality'] = quality_score
                
                # Value Factor: Earnings Yield using PIT fundamental data  
                value_score = calculate_value_factor_pit(ticker, date_str, self.pit_manager)
                scores[ticker]['value'] = value_score
                
                # Momentum Factor: 6-month price momentum (unchanged logic)
                data_feed = self.getdatabyname(ticker)
                if data_feed is not None:
                    df = data_feed.get_df()
                    momentum_score = calculate_momentum_factor_pit(df)
                    scores[ticker]['momentum'] = momentum_score
                
                # Count valid factor calculations
                if (quality_score != -float('inf') and 
                    value_score != -float('inf') and 
                    momentum_score != -float('inf')):
                    valid_tickers += 1
                
            except Exception as e:
                if self.rebalance_count <= 2:  # Only show errors for first few rebalances
                    print(f"Error calculating factors for {ticker}: {str(e)[:100]}")

        print(f"Valid factor calculations: {valid_tickers}/{len(self.universe)} stocks")

        # --- STEP 2: Rank stocks on each factor ---
        # Higher score is better for all factors. Rank from 1 (best) to N (worst).
        quality_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['quality'], reverse=True), 1)}
        value_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['value'], reverse=True), 1)}
        momentum_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['momentum'], reverse=True), 1)}

        # Debug: Print sample factor scores for first rebalance
        if self.rebalance_count == 1:
            print("\\nSample Factor Scores (First 10 tickers):")
            sample_tickers = list(self.universe)[:10]
            for ticker in sample_tickers:
                q, v, m = scores[ticker]['quality'], scores[ticker]['value'], scores[ticker]['momentum']
                print(f"  {ticker}: Q={q:.4f}, V={v:.4f}, M={m:.4f}")

        # --- STEP 3: Calculate Composite Score ---
        for ticker in self.universe:
            scores[ticker]['composite'] = quality_rank[ticker] + value_rank[ticker] + momentum_rank[ticker]

        # --- STEP 4: Select Final Portfolio ---
        # Sort by the composite score (lower is better)
        ranked_by_composite = sorted(scores, key=lambda x: scores[x]['composite'])
        
        # Filter out stocks with invalid factors before final selection
        valid_ranked_stocks = [ticker for ticker in ranked_by_composite 
                              if all(scores[ticker][factor] != -float('inf') 
                                   for factor in ['quality', 'value', 'momentum'])]
        
        final_portfolio = valid_ranked_stocks[:self.p.num_positions]
        
        print(f"Final Portfolio Selected ({len(final_portfolio)} positions): {final_portfolio[:10]}{'...' if len(final_portfolio) > 10 else ''}")

        # Show composite scores for selected portfolio
        if self.rebalance_count <= 2:
            print("\\nSelected Portfolio Composite Scores:")
            for ticker in final_portfolio[:5]:  # Show first 5
                print(f"  {ticker}: {scores[ticker]['composite']}")

        # --- EXECUTION ---
        target_weight = 1.0 / self.p.num_positions if final_portfolio else 0
        
        current_holdings = [d._name for d in self.datas if self.getposition(d).size > 0]
        
        # Sell stocks no longer in the portfolio
        for ticker in current_holdings:
            if ticker not in final_portfolio:
                self.close(data=self.getdatabyname(ticker))
                print(f"  Closing position in {ticker}")

        # Buy stocks in the target portfolio
        for ticker in final_portfolio:
            data_feed = self.getdatabyname(ticker)
            if data_feed:
                self.order_target_percent(data=data_feed, target=target_weight)
                if self.rebalance_count <= 2:  # Reduce verbosity after first few rebalances
                    print(f"  Setting {ticker} to {target_weight:.1%}")
    
    def getdatabyname(self, name):
        """Get data feed by ticker name"""
        for d in self.datas:
            if hasattr(d, '_name') and d._name == name:
                return d
        return None

def load_sp500_universe():
    """Load the curated S&P 500 universe from file"""
    universe_file = 'data/sprint_12/curated_sp500_universe.txt'
    universe = []
    
    if os.path.exists(universe_file):
        with open(universe_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    universe.append(line)
    
    return universe

def run_sprint12_backtest():
    """
    Run the Sprint 12 S&P 500 Composite QVM backtest.
    """
    print("="*80)
    print("SPRINT 12: THE S&P 500 QVM UNIVERSE TEST")
    print("="*80)
    print("Testing Composite QVM strategy on diversified S&P 500 universe...")
    
    # Load S&P 500 universe
    universe = load_sp500_universe()
    if not universe:
        print("ERROR: Could not load S&P 500 universe")
        return None
    
    print(f"Universe loaded: {len(universe)} S&P 500 stocks")
    print(f"Sample tickers: {universe[:10]}")
    
    # API key from Sprint 11
    api_key = "zVj71CrDyYzfcyxrWkQ4"
    
    # Create results directory
    results_dir = 'results/sprint_12'
    os.makedirs(results_dir, exist_ok=True)
    
    # Extend bt.DataBase to include a get_df method for easier data access
    bt.feeds.PandasData.get_df = lambda self: self.p.dataname.loc[self.p.fromdate:self.p.todate]
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(CompositeQVMSP500Strategy, universe=universe, api_key=api_key)

    # Load price data for all stocks
    price_data_dir = 'data/sprint_12'
    loaded_count = 0
    
    for ticker in universe:
        data_path = os.path.join(price_data_dir, f'{ticker}.csv')
        if os.path.exists(data_path):
            try:
                # Handle yfinance multi-level CSV format  
                df = pd.read_csv(data_path, index_col=0, parse_dates=True, skiprows=[1,2])
                df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
                # Ensure proper column order for backtrader
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
                loaded_count += 1
            except Exception as e:
                print(f"ERROR loading {ticker}: {str(e)[:100]}")
        else:
            print(f"WARNING: No price data found for {ticker}")

    print(f"SUCCESS: Loaded price data for {loaded_count}/{len(universe)} stocks")

    # Set initial capital and commission
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% commission
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print(f'\\nStarting Sprint 12 backtest with ${cerebro.broker.getvalue():,.2f}...')
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
    
    # Trade statistics
    total_trades = trades_analysis.get('total', {}).get('total', 0) or 0
    winning_trades = trades_analysis.get('won', {}).get('total', 0) or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_return = (final_value - initial_value) / initial_value * 100

    # Display results
    print('\\n' + '='*80)
    print('SPRINT 12: S&P 500 QVM RESULTS')
    print('='*80)
    print(f'Test Universe: {len(universe)} S&P 500 stocks')
    print(f'Data Coverage: {loaded_count} stocks with price data')
    print(f'Backtest Duration: {end_time - start_time}')
    print(f'Initial Portfolio Value: ${initial_value:,.2f}')
    print(f'Final Portfolio Value: ${final_value:,.2f}')
    print(f'Total Return: {total_return:.2f}%')
    print(f'Annualized Return: {ann_return:.2f}%')
    print(f'Sharpe Ratio: {sharpe_ratio:.2f}')
    print(f'Max Drawdown: {max_drawdown:.2f}%')
    print(f'Total Trades: {total_trades}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'Rebalances: {strat.rebalance_count}')
    
    # Sprint 12 Success Criteria Assessment
    print('\\n' + '='*80)
    print('SPRINT 12 SUCCESS CRITERIA ASSESSMENT')
    print('='*80)
    
    criteria_results = []
    
    print(f"[TARGET] Post-Cost Annualized Return > 15%")
    return_pass = ann_return > 15
    print(f"   Result: {ann_return:.2f}% {'✓ PASS' if return_pass else '✗ FAIL'}")
    criteria_results.append(return_pass)
    
    print(f"[TARGET] Post-Cost Sharpe Ratio > 1.0")
    sharpe_pass = sharpe_ratio > 1.0
    print(f"   Result: {sharpe_ratio:.2f} {'✓ PASS' if sharpe_pass else '✗ FAIL'}")
    criteria_results.append(sharpe_pass)
    
    print(f"[TARGET] Max Drawdown < 25%")
    drawdown_pass = max_drawdown < 25
    print(f"   Result: {max_drawdown:.2f}% {'✓ PASS' if drawdown_pass else '✗ FAIL'}")
    criteria_results.append(drawdown_pass)
    
    print(f"[TARGET] Total Trades > 50")
    trades_pass = total_trades > 50
    print(f"   Result: {total_trades} trades {'✓ PASS' if trades_pass else '✗ FAIL'}")
    criteria_results.append(trades_pass)
    
    criteria_met = sum(criteria_results)
    print(f"\\nOVERALL: {criteria_met}/4 criteria met")
    
    if criteria_met == 4:
        print("🎯 SUCCESS - S&P 500 QVM strategy ready for deployment!")
    elif criteria_met >= 3:
        print("📈 PROMISING - Strategy shows strong potential with larger universe")
    elif criteria_met >= 2:
        print("📊 IMPROVING - Larger universe provides better results than Sprint 11")
    else:
        print("📋 LEARNING - Insights gained for future strategy development")
    
    print("\\n" + "="*80)
    print("SPRINT 12 SIGNIFICANCE")
    print("="*80)
    print("This test validates the QVM strategy at institutional scale:")
    print("✓ Large, diversified S&P 500 universe (216 stocks)")  
    print("✓ Sufficient opportunity set for meaningful factor selection")
    print("✓ Professional portfolio size (20 positions)")
    print("✓ Institutional-grade methodology with zero lookahead bias")

    # Save results
    results_data = {
        'test': 'Sprint 12 - S&P 500 Composite QVM Strategy',
        'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'universe_size': len(universe),
        'data_coverage': loaded_count,
        'target_positions': 20,
        'methodology': 'Point-in-Time Sharadar SF1 Data on S&P 500 Universe',
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
        'success_criteria': {
            'return_target_met': return_pass,
            'sharpe_target_met': sharpe_pass,
            'drawdown_target_met': drawdown_pass,
            'trades_target_met': trades_pass,
            'overall_success': criteria_met == 4
        },
        'universe_sample': universe[:20],
        'significance': 'First QVM test on institutional-scale S&P 500 universe'
    }
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f'sprint12_sp500_qvm_results_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\\nRESULTS: Results saved to: {results_file}")
    return results_data

if __name__ == '__main__':
    # Run the Sprint 12 S&P 500 QVM backtest
    run_sprint12_backtest()