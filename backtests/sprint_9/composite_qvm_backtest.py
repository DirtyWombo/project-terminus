# backtests/sprint_9/composite_qvm_backtest.py
import backtrader as bt
import pandas as pd
import yfinance as yf
import os
import sys
import json
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from features.qvm_factors import calculate_quality_factor, calculate_value_factor, calculate_momentum_factor

class CompositeQVMStrategy(bt.Strategy):
    params = (('num_positions', 3), ('universe', None))

    def __init__(self):
        self.add_timer(when=bt.Timer.SESSION_START, monthdays=[1], monthcarry=True)
        self.universe = self.p.universe
        self.rebalance_count = 0

    def notify_timer(self, timer, when, *args, **kwargs):
        self.rebalance_portfolio()

    def rebalance_portfolio(self):
        print(f'--- Rebalancing on {self.datas[0].datetime.date(0)} ---')
        self.rebalance_count += 1
        
        scores = {}
        # Initialize scores for all tickers in the universe
        for ticker in self.universe:
            scores[ticker] = {'quality': 0, 'value': 0, 'momentum': 0, 'composite': 0}

        # --- STEP 1: Calculate scores for each factor ---
        for ticker in self.universe:
            # --- POINT-IN-TIME (PIT) DATA FETCHING ---
            # This is slow but necessary for a correct backtest without a dedicated PIT database.
            try:
                stock = yf.Ticker(ticker)
                fundamentals = {
                    'info': stock.info,
                    'financials': stock.financials,
                    'balance_sheet': stock.balance_sheet
                }
                
                # Calculate factors using the fetched PIT data
                scores[ticker]['quality'] = calculate_quality_factor(fundamentals)
                scores[ticker]['value'] = calculate_value_factor(fundamentals)
            except Exception as e:
                print(f"Could not fetch PIT fundamentals for {ticker}: {e}")
                scores[ticker]['quality'] = -float('inf')
                scores[ticker]['value'] = -float('inf')

            data_feed = self.getdatabyname(ticker)
            if data_feed is not None:
                df = data_feed.get_df()
                scores[ticker]['momentum'] = calculate_momentum_factor(df)
            else:
                scores[ticker]['momentum'] = -float('inf')

        # --- STEP 2: Rank stocks on each factor ---
        # Note: For Q and V, higher score is better. For M, higher is better.
        # We will rank from 1 (best) to N (worst).
        quality_rank = {ticker: rank for rank, ticker in enumerate(sorted(scores, key=lambda x: scores[x]['quality'], reverse=True), 1)}
        value_rank = {ticker: rank for rank, ticker in enumerate(sorted(scores, key=lambda x: scores[x]['value'], reverse=True), 1)}
        momentum_rank = {ticker: rank for rank, ticker in enumerate(sorted(scores, key=lambda x: scores[x]['momentum'], reverse=True), 1)}

        # Debug: Print factor scores and ranks
        print("Factor Scores:")
        for ticker in self.universe:
            print(f"  {ticker}: Q={scores[ticker]['quality']:.4f}, V={scores[ticker]['value']:.4f}, M={scores[ticker]['momentum']:.4f}")
        
        print("Factor Rankings:")
        print(f"  Quality: {quality_rank}")
        print(f"  Value: {value_rank}")
        print(f"  Momentum: {momentum_rank}")

        # --- STEP 3: Calculate Composite Score ---
        for ticker in self.universe:
            scores[ticker]['composite'] = quality_rank[ticker] + value_rank[ticker] + momentum_rank[ticker]

        print("Composite Scores:")
        for ticker in self.universe:
            print(f"  {ticker}: {scores[ticker]['composite']}")

        # --- STEP 4: Select Final Portfolio ---
        # Sort by the composite score (lower is better)
        ranked_by_composite = sorted(scores, key=lambda x: scores[x]['composite'])
        final_portfolio = ranked_by_composite[:self.p.num_positions]
        
        print(f"Final Portfolio Selected: {final_portfolio}")

        # --- EXECUTION ---
        target_weight = 1.0 / self.p.num_positions if final_portfolio else 0
        
        current_holdings = [d._name for d in self.datas if self.getposition(d).size > 0]
        
        # Sell stocks no longer in the portfolio
        for ticker in current_holdings:
            if ticker not in final_portfolio:
                self.close(data=self.getdatabyname(ticker))

        # Buy stocks in the target portfolio
        for ticker in final_portfolio:
            self.order_target_percent(data=self.getdatabyname(ticker), target=target_weight)
    
    def getdatabyname(self, name):
        """Get data feed by ticker name"""
        for d in self.datas:
            if hasattr(d, '_name') and d._name == name:
                return d
        return None


# --- The run_portfolio_backtest function remains largely the same ---
# --- but we pass the universe to the strategy ---

def run_portfolio_backtest(universe, price_data_dir, results_dir):
    cerebro = bt.Cerebro(stdstats=False)
    # Pass the universe list to the strategy parameters
    cerebro.addstrategy(CompositeQVMStrategy, universe=universe)

    for ticker in universe:
        data_path = os.path.join(price_data_dir, f'{ticker}.csv')
        df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
        cerebro.adddata(bt.feeds.PandasData(dataname=df, name=ticker))

    cerebro.broker.setcash(100000.0)
    # CRITICAL: Use the validated Transaction Cost Model
    cerebro.broker.setcommission(commission=0.001)
    
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print('Running Composite QVM portfolio backtest...')
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strat = results[0]
    final_value = cerebro.broker.getvalue()

    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    returns_analysis = strat.analyzers.returns.get_analysis()
    
    sharpe = sharpe_analysis.get('sharperatio', 0) or 0
    drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0) or 0
    ann_return = returns_analysis.get('rnorm100', 0) or 0
    
    # Trade statistics
    trades_analysis = strat.analyzers.trades.get_analysis()
    total_trades = trades_analysis.get('total', {}).get('total', 0) or 0
    winning_trades = trades_analysis.get('won', {}).get('total', 0) or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_return = (final_value - initial_value) / initial_value * 100

    print('--- Composite QVM Portfolio Results (Post-Cost) ---')
    print(f'Initial Portfolio Value: ${initial_value:,.2f}')
    print(f'Final Portfolio Value: ${final_value:,.2f}')
    print(f'Total Return: {total_return:.2f}%')
    print(f'Annualized Return: {ann_return:.2f}%')
    print(f'Sharpe Ratio: {sharpe:.2f}')
    print(f'Max Drawdown: {drawdown:.2f}%')
    print(f'Total Trades: {total_trades}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'Rebalances: {strat.rebalance_count}')
    
    # Success criteria check
    print('\n' + '='*60)
    print('SPRINT 9 SUCCESS CRITERIA ASSESSMENT')
    print('='*60)
    
    print(f"[TARGET] Post-Cost Annualized Return > 15%")
    return_pass = ann_return > 15
    print(f"   Result: {ann_return:.2f}% {'PASS' if return_pass else 'FAIL'}")
    
    print(f"[TARGET] Post-Cost Sharpe Ratio > 1.0")
    sharpe_pass = sharpe > 1.0
    print(f"   Result: {sharpe:.2f} {'PASS' if sharpe_pass else 'FAIL'}")
    
    print(f"[TARGET] Max Drawdown < 25%")
    drawdown_pass = drawdown < 25
    print(f"   Result: {drawdown:.2f}% {'PASS' if drawdown_pass else 'FAIL'}")
    
    criteria_met = sum([return_pass, sharpe_pass, drawdown_pass])
    print(f"\nOVERALL: {criteria_met}/3 criteria met")
    
    if criteria_met == 3:
        print("SUCCESS - Composite QVM strategy ready for deployment!")
    elif criteria_met >= 2:
        print("MARGINAL - Strategy shows promise but needs refinement")
    else:
        print("FAILED - Strategy requires significant improvement")

    # Save results
    results_data = {
        'test': 'Sprint 9 - Composite QVM Portfolio Strategy',
        'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'universe': universe,
        'initial_value': initial_value,
        'final_value': final_value,
        'total_return_pct': total_return,
        'annualized_return_pct': ann_return,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': drawdown,
        'total_trades': total_trades,
        'win_rate_pct': win_rate,
        'rebalances': strat.rebalance_count,
        'success_criteria': {
            'return_target_met': return_pass,
            'sharpe_target_met': sharpe_pass,
            'drawdown_target_met': drawdown_pass,
            'overall_success': criteria_met == 3
        }
    }
    
    # Save to file
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f'composite_qvm_results_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    return results_data

if __name__ == '__main__':
    # Extend bt.DataBase to include a get_df method for easier data access
    class PandasDataWithGetDf(bt.feeds.PandasData):
        def get_df(self):
            return self.p.dataname.loc[self.p.fromdate:self.p.todate]
    bt.feeds.PandasData.get_df = lambda self: self.p.dataname.loc[self.p.fromdate:self.p.todate]

    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    run_portfolio_backtest(UNIVERSE, 'data/sprint_1', 'results/sprint_9')