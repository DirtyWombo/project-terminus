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
import argparse
from google.cloud import storage

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

def run_portfolio_backtest(ticker, price_data_dir, results_bucket_name):
    """
    Runs the QVM backtest for a SINGLE ticker and uploads the results to GCS.
    """
    cerebro = bt.Cerebro(stdstats=False)
    # The universe is now just the single ticker this worker is responsible for.
    cerebro.addstrategy(CompositeQVMSP500WeeklyStrategy, universe=[ticker], api_key="zVj71CrDyYzfcyxrWkQ4")

    # Load the price data for the single ticker
    data_path = os.path.join(price_data_dir, f'{ticker}.csv')
    if not os.path.exists(data_path):
        print(f"Data for {ticker} not found. Skipping.")
        return

    try:
        # Handle yfinance multi-level CSV format  
        df = pd.read_csv(data_path, index_col=0, parse_dates=True, skiprows=[1,2])
        df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
        # Ensure proper column order for backtrader
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))
    except Exception as e:
        print(f"ERROR loading {ticker}: {str(e)[:100]}")
        return

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001) # Using simplified costs for now
    
    # Add all the necessary performance analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print(f'Running QVM backtest for {ticker}...')
    
    # Extend bt.DataBase to include a get_df method
    bt.feeds.PandasData.get_df = lambda self: self.p.dataname.loc[self.p.fromdate:self.p.todate]
    
    results = cerebro.run()
    strat = results[0]

    # --- This section creates a clean dictionary of the final results ---
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
    ann_return = strat.analyzers.returns.get_analysis().get('rnorm100', 0) or 0
    total_trades = strat.analyzers.trades.get_analysis().get('total', {}).get('total', 0) or 0
    winning_trades = strat.analyzers.trades.get_analysis().get('won', {}).get('total', 0) or 0
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

    result_data = {
        'ticker': ticker,
        'annualized_return': ann_return,
        'sharpe_ratio': sharpe,
        'max_drawdown': drawdown,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'final_value': cerebro.broker.getvalue()
    }

    # --- This section saves the results to a file and uploads it to our cloud bucket ---
    result_filename = f'{ticker}_results.json'
    with open(result_filename, 'w') as f:
        json.dump(result_data, f)

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(results_bucket_name)
        blob = bucket.blob(f'sprint_13/{result_filename}') # Saves to a 'sprint_13' folder in the bucket
        blob.upload_from_filename(result_filename)
        print(f"--- Results for {ticker} uploaded to GCS ---")
    except Exception as e:
        print(f"ERROR: Could not upload results for {ticker} to GCS. {e}")

if __name__ == '__main__':
    # --- This block allows the script to be run from the command line with arguments ---
    parser = argparse.ArgumentParser(description='Run a QVM backtest for a single ticker.')
    parser.add_argument('--ticker', required=True, type=str, help='The stock ticker to backtest (e.g., AAPL).')
    args = parser.parse_args()

    # We now run the backtest for only the single ticker passed in from the command line
    run_portfolio_backtest(
        ticker=args.ticker,
        price_data_dir='data/sprint_12_sp500', # Make sure your S&P 500 price data is in this folder
        results_bucket_name='operation-badger-quant-results-bucket' # The unique bucket name we created
    )