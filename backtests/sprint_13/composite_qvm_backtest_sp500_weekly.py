# backtests/sprint_13/composite_qvm_backtest_sp500_weekly.py
"""
Sprint 13: Full S&P 500 Universe with Weekly Rebalancing

This is the final validation test of the Composite QVM strategy using:
- Full 216-stock S&P 500 universe (maximum available)
- Weekly rebalancing (every Monday)
- 20 positions
- Point-in-time fundamental data

Sprint 13 Success Criteria:
- Post-Cost Annualized Return > 15%
- Post-Cost Sharpe Ratio > 1.0  
- Max Drawdown < 25%
- Total Trades > 50
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

class CompositeQVMSP500WeeklyStrategy(bt.Strategy):
    """
    Sprint 13: Composite QVM Strategy with Weekly Rebalancing
    
    Final optimization of the QVM strategy with:
    - Full 216-stock S&P 500 universe
    - Weekly rebalancing for more trading opportunities
    - 20 positions for optimal diversification
    """
    
    params = (
        ('num_positions', 20),  # Same as Sprint 12
        ('universe', None),
        ('api_key', None)
    )

    def __init__(self):
        # WEEKLY REBALANCING - Key change from Sprint 12
        self.add_timer(when=bt.Timer.SESSION_START, weekdays=[1], weekcarry=True)
        self.universe = self.p.universe
        self.rebalance_count = 0
        
        # Initialize PIT data manager
        self.pit_manager = PITDataManager(api_key=self.p.api_key)
        
        print(f"SUCCESS: Sprint 13 Weekly Composite QVM Strategy initialized")
        print(f"SUCCESS: Universe size: {len(self.universe)} stocks")
        print(f"SUCCESS: Target positions: {self.params.num_positions}")
        print(f"SUCCESS: Rebalancing: WEEKLY (52x per year)")

    def notify_timer(self, timer, when, *args, **kwargs):
        self.rebalance_portfolio()

    def rebalance_portfolio(self):
        current_date = self.datas[0].datetime.date(0)
        date_str = current_date.strftime('%Y-%m-%d')
        
        # Less verbose output for weekly rebalancing
        if self.rebalance_count % 4 == 0:  # Print every 4 weeks
            print(f'\n--- Sprint 13 Weekly Rebalancing #{self.rebalance_count + 1} on {current_date} ---')
        
        self.rebalance_count += 1
        
        scores = {}
        valid_tickers = 0
        
        # Initialize scores for all tickers in the universe
        for ticker in self.universe:
            scores[ticker] = {'quality': -float('inf'), 'value': -float('inf'), 'momentum': -float('inf'), 'composite': 999}

        # --- STEP 1: Calculate Point-in-Time QVM Factors ---
        for ticker in self.universe:
            try:
                # Quality Factor: ROE using PIT fundamental data
                quality_score = calculate_quality_factor_pit(ticker, date_str, self.pit_manager)
                scores[ticker]['quality'] = quality_score
                
                # Value Factor: Earnings Yield using PIT fundamental data  
                value_score = calculate_value_factor_pit(ticker, date_str, self.pit_manager)
                scores[ticker]['value'] = value_score
                
                # Momentum Factor: 6-month price momentum
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
                # Silent fail for individual stocks
                pass

        # Print summary every 4 weeks
        if self.rebalance_count % 4 == 0:
            print(f"Valid factor calculations: {valid_tickers}/{len(self.universe)} stocks")

        # --- STEP 2: Rank stocks on each factor ---
        quality_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['quality'], reverse=True), 1)}
        value_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['value'], reverse=True), 1)}
        momentum_rank = {ticker: rank for rank, ticker in enumerate(
            sorted(scores, key=lambda x: scores[x]['momentum'], reverse=True), 1)}

        # --- STEP 3: Calculate Composite Score ---
        for ticker in self.universe:
            scores[ticker]['composite'] = quality_rank[ticker] + value_rank[ticker] + momentum_rank[ticker]

        # --- STEP 4: Select Final Portfolio ---
        ranked_by_composite = sorted(scores, key=lambda x: scores[x]['composite'])
        
        # Filter out stocks with invalid factors
        valid_ranked_stocks = [ticker for ticker in ranked_by_composite 
                              if all(scores[ticker][factor] != -float('inf') 
                                   for factor in ['quality', 'value', 'momentum'])]
        
        final_portfolio = valid_ranked_stocks[:self.p.num_positions]
        
        # Print portfolio changes every 4 weeks
        if self.rebalance_count % 4 == 0:
            print(f"Portfolio selected: {final_portfolio[:10]}{'...' if len(final_portfolio) > 10 else ''}")

        # --- EXECUTION ---
        target_weight = 1.0 / self.p.num_positions if final_portfolio else 0
        
        current_holdings = [d._name for d in self.datas if self.getposition(d).size > 0]
        
        # Track portfolio changes
        stocks_to_sell = [t for t in current_holdings if t not in final_portfolio]
        stocks_to_buy = [t for t in final_portfolio if t not in current_holdings]
        
        # Sell stocks no longer in the portfolio
        for ticker in stocks_to_sell:
            self.close(data=self.getdatabyname(ticker))
        
        # Buy stocks in the target portfolio
        for ticker in final_portfolio:
            data_feed = self.getdatabyname(ticker)
            if data_feed:
                self.order_target_percent(data=data_feed, target=target_weight)
        
        # Print trade summary every 4 weeks
        if self.rebalance_count % 4 == 0 and (stocks_to_sell or stocks_to_buy):
            print(f"Trades: Selling {len(stocks_to_sell)}, Buying {len(stocks_to_buy)}")
    
    def getdatabyname(self, name):
        """Get data feed by ticker name"""
        for d in self.datas:
            if hasattr(d, '_name') and d._name == name:
                return d
        return None

def load_full_sp500_universe():
    """Load the full curated S&P 500 universe (216 stocks)"""
    universe_file = 'data/sprint_12/curated_sp500_universe.txt'
    universe = []
    
    if os.path.exists(universe_file):
        with open(universe_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    universe.append(line)
    
    return universe

def run_sprint13_backtest():
    """
    Run the Sprint 13 Full S&P 500 Weekly Composite QVM backtest.
    """
    print("="*80)
    print("SPRINT 13: FULL S&P 500 WEEKLY QVM TEST")
    print("="*80)
    print("Testing Composite QVM strategy with:")
    print("- Full 216-stock S&P 500 universe")
    print("- Weekly rebalancing (52x per year)")
    print("- 20 positions")
    print("- Point-in-time fundamental data")
    print("="*80)
    
    # Load full S&P 500 universe
    universe = load_full_sp500_universe()
    if not universe:
        print("ERROR: Could not load S&P 500 universe")
        return None
    
    print(f"Universe loaded: {len(universe)} S&P 500 stocks")
    print(f"Sample tickers: {universe[:10]}")
    
    # API key from Sprint 11
    api_key = "zVj71CrDyYzfcyxrWkQ4"
    
    # Create results directory
    results_dir = 'results/sprint_13'
    os.makedirs(results_dir, exist_ok=True)
    
    # Extend bt.DataBase to include a get_df method
    bt.feeds.PandasData.get_df = lambda self: self.p.dataname.loc[self.p.fromdate:self.p.todate]
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(CompositeQVMSP500WeeklyStrategy, universe=universe, api_key=api_key)

    # Load price data for all stocks
    price_data_dir = 'data/sprint_12'
    loaded_count = 0
    
    print("\nLoading price data...")
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
                if loaded_count % 50 == 0:
                    print(f"  Loaded {loaded_count} stocks...")
            except Exception as e:
                print(f"ERROR loading {ticker}: {str(e)[:100]}")

    print(f"SUCCESS: Loaded price data for {loaded_count}/{len(universe)} stocks")

    # Set initial capital and commission
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% commission
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print(f'\nStarting Sprint 13 backtest with ${cerebro.broker.getvalue():,.2f}...')
    print("This may take 10-20 minutes due to weekly rebalancing of 216 stocks...")
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
    print('\n' + '='*80)
    print('SPRINT 13: FULL S&P 500 WEEKLY QVM RESULTS')
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
    
    # Sprint 13 Success Criteria Assessment
    print('\n' + '='*80)
    print('SPRINT 13 SUCCESS CRITERIA ASSESSMENT')
    print('='*80)
    
    criteria_results = []
    
    print(f"[TARGET] Post-Cost Annualized Return > 15%")
    return_pass = ann_return > 15
    print(f"   Result: {ann_return:.2f}% {'PASS' if return_pass else 'FAIL'}")
    criteria_results.append(return_pass)
    
    print(f"[TARGET] Post-Cost Sharpe Ratio > 1.0")
    sharpe_pass = sharpe_ratio > 1.0
    print(f"   Result: {sharpe_ratio:.2f} {'PASS' if sharpe_pass else 'FAIL'}")
    criteria_results.append(sharpe_pass)
    
    print(f"[TARGET] Max Drawdown < 25%")
    drawdown_pass = max_drawdown < 25
    print(f"   Result: {max_drawdown:.2f}% {'PASS' if drawdown_pass else 'FAIL'}")
    criteria_results.append(drawdown_pass)
    
    print(f"[TARGET] Total Trades > 50")
    trades_pass = total_trades > 50
    print(f"   Result: {total_trades} trades {'PASS' if trades_pass else 'FAIL'}")
    criteria_results.append(trades_pass)
    
    criteria_met = sum(criteria_results)
    print(f"\nOVERALL: {criteria_met}/4 criteria met")
    
    if criteria_met == 4:
        print("\n🎯 SUCCESS - STRATEGY READY FOR DEPLOYMENT!")
        print("All four criteria met. The QVM strategy is validated.")
    elif criteria_met >= 3:
        print("\n📈 NEAR SUCCESS - One criterion away from deployment")
    elif criteria_met >= 2:
        print("\n📊 PROGRESS - Weekly rebalancing shows improvement")
    else:
        print("\n📋 LEARNING - Further optimization needed")
    
    print("\n" + "="*80)
    print("SPRINT 13 SIGNIFICANCE")
    print("="*80)
    print("This represents our most comprehensive test:")
    print("✓ Maximum universe (216 S&P 500 stocks)")  
    print("✓ Highest frequency (weekly rebalancing)")
    print("✓ Professional methodology (point-in-time data)")
    print("✓ Institutional standards (4 success criteria)")

    # Save results
    results_data = {
        'test': 'Sprint 13 - Full S&P 500 Weekly QVM Strategy',
        'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'universe_size': len(universe),
        'data_coverage': loaded_count,
        'target_positions': 20,
        'rebalancing_frequency': 'Weekly',
        'methodology': 'Point-in-Time Sharadar SF1 Data on Full S&P 500 Universe',
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
        'significance': 'Final validation test with full universe and weekly rebalancing'
    }
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f'sprint13_sp500_weekly_qvm_results_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\nRESULTS: Results saved to: {results_file}")
    return results_data

if __name__ == '__main__':
    # Run the Sprint 13 Full S&P 500 Weekly QVM backtest
    run_sprint13_backtest()