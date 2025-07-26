# backtests/sprint_8/qvm_backtest.py
import backtrader as bt
import pandas as pd
import os
import sys
import numpy as np
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from features.qvm_factors import calculate_quality_factor, calculate_value_factor, calculate_momentum_factor

class QVMStrategy(bt.Strategy):
    params = (
        ('num_positions', 3), # Top 3 stocks from our 10-stock universe
        ('quality_threshold', 0.05), # Minimum ROE of 5% (adjusted for growth stocks)
        ('rebalance_frequency', 30), # Rebalance every 30 days
    )

    def __init__(self):
        self.fundamental_data = pd.read_pickle('data/sprint_8/fundamental_data.pkl')
        self.days_since_rebalance = 0
        self.current_portfolio = []
        
        # Performance tracking
        self.rebalance_count = 0
        self.portfolio_values = []
        
        print(f"QVM Strategy initialized with {len(self.fundamental_data)} stocks")
        print(f"Available tickers: {list(self.fundamental_data.keys())}")

    def next(self):
        """Called on every bar"""
        self.days_since_rebalance += 1
        
        # Rebalance monthly
        if self.days_since_rebalance >= self.params.rebalance_frequency:
            self.rebalance_portfolio()
            self.days_since_rebalance = 0
            
        # Track portfolio value
        self.portfolio_values.append(self.broker.getvalue())

    def rebalance_portfolio(self):
        """Execute the QVM screening process"""
        current_date = self.datas[0].datetime.date(0)
        print(f'\n--- QVM Rebalancing on {current_date} ---')
        self.rebalance_count += 1
        
        # Get current data for momentum calculations
        current_data = {}
        for d in self.datas:
            if hasattr(d, '_name'):
                ticker = d._name
                # Create DataFrame from current backtrader data
                df_data = []
                for i in range(min(len(d), 252)):  # Up to 1 year of data
                    idx = -i-1
                    if abs(idx) <= len(d):
                        df_data.append({
                            'Close': d.close[idx],
                            'Date': d.datetime.date(idx)
                        })
                
                if df_data:
                    df = pd.DataFrame(df_data[::-1])  # Reverse to chronological order
                    df.set_index('Date', inplace=True)
                    current_data[ticker] = df
        
        # --- SCREEN 1: QUALITY ---
        quality_screened_stocks = []
        quality_scores = {}
        
        for ticker in self.fundamental_data.keys():
            if ticker in current_data:  # Only consider stocks with price data
                roe = calculate_quality_factor(self.fundamental_data[ticker])
                quality_scores[ticker] = roe
                if roe > self.params.quality_threshold:
                    quality_screened_stocks.append(ticker)
        
        print(f"Quality scores: {quality_scores}")
        print(f"Quality screen passed ({len(quality_screened_stocks)}): {quality_screened_stocks}")
        
        if not quality_screened_stocks:
            print("No stocks passed quality screen - holding cash")
            self._close_all_positions()
            return

        # --- SCREEN 2: VALUE ---
        value_scores = {}
        for ticker in quality_screened_stocks:
            value_scores[ticker] = calculate_value_factor(self.fundamental_data[ticker])
        
        # Rank by value (higher is better) and take the top half
        valid_value_scores = {k: v for k, v in value_scores.items() if v != -float('inf')}
        
        if not valid_value_scores:
            print("No stocks have valid value scores - holding cash")
            self._close_all_positions()
            return
            
        ranked_by_value = sorted(valid_value_scores.items(), key=lambda item: item[1], reverse=True)
        num_value_survivors = max(1, len(ranked_by_value) // 2)
        value_screened_stocks = [item[0] for item in ranked_by_value[:num_value_survivors]]
        
        print(f"Value scores: {value_scores}")
        print(f"Value screen passed ({len(value_screened_stocks)}): {value_screened_stocks}")

        # --- SCREEN 3: MOMENTUM ---
        momentum_scores = {}
        for ticker in value_screened_stocks:
            if ticker in current_data:
                momentum_scores[ticker] = calculate_momentum_factor(current_data[ticker])

        # Rank by momentum and select our final portfolio
        valid_momentum_scores = {k: v for k, v in momentum_scores.items() if v != -float('inf')}
        
        if not valid_momentum_scores:
            print("No stocks have valid momentum scores - holding cash")
            self._close_all_positions()
            return
            
        ranked_by_momentum = sorted(valid_momentum_scores.items(), key=lambda item: item[1], reverse=True)
        final_portfolio = [item[0] for item in ranked_by_momentum[:self.params.num_positions]]
        
        print(f"Momentum scores: {momentum_scores}")
        print(f"Final Portfolio Selected ({len(final_portfolio)}): {final_portfolio}")

        # --- EXECUTION ---
        self._execute_rebalance(final_portfolio)
        self.current_portfolio = final_portfolio

    def _execute_rebalance(self, target_portfolio):
        """Execute the portfolio rebalance"""
        target_weight = 1.0 / len(target_portfolio) if target_portfolio else 0
        
        # Close positions not in target portfolio
        for d in self.datas:
            if hasattr(d, '_name'):
                ticker = d._name
                if ticker not in target_portfolio and self.getposition(d).size != 0:
                    print(f"  Closing position in {ticker}")
                    self.close(data=d)

        # Open/adjust positions in target portfolio
        for ticker in target_portfolio:
            data_feed = self._get_data_by_name(ticker)
            if data_feed:
                current_weight = self._get_position_weight(data_feed)
                print(f"  Setting {ticker} to {target_weight:.1%} (current: {current_weight:.1%})")
                self.order_target_percent(data=data_feed, target=target_weight)

    def _close_all_positions(self):
        """Close all open positions"""
        for d in self.datas:
            if self.getposition(d).size != 0:
                self.close(data=d)

    def _get_data_by_name(self, name):
        """Get data feed by ticker name"""
        for d in self.datas:
            if hasattr(d, '_name') and d._name == name:
                return d
        return None

    def _get_position_weight(self, data_feed):
        """Calculate current position weight"""
        position = self.getposition(data_feed)
        if position.size == 0:
            return 0.0
        
        position_value = position.size * data_feed.close[0]
        portfolio_value = self.broker.getvalue()
        return position_value / portfolio_value if portfolio_value > 0 else 0.0

def run_portfolio_backtest(universe, price_data_dir, results_dir):
    """Run the QVM portfolio backtest"""
    
    # Create results directory
    os.makedirs(results_dir, exist_ok=True)
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(QVMStrategy)

    # Load price data for all stocks
    for ticker in universe:
        data_path = os.path.join(price_data_dir, f'{ticker}.csv')
        if os.path.exists(data_path):
            df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
            data_feed = bt.feeds.PandasData(dataname=df, name=ticker)
            cerebro.adddata(data_feed)
            print(f"Added data for {ticker}: {len(df)} bars")
        else:
            print(f"Warning: No data file found for {ticker}")

    # Set initial capital and commission
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001, margin=None, mult=1.0)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print(f'\nStarting QVM portfolio backtest with ${cerebro.broker.getvalue():,.2f}...')
    initial_value = cerebro.broker.getvalue()
    
    # Run backtest
    results = cerebro.run()
    strat = results[0]
    
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - initial_value) / initial_value

    # Extract results
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    returns_analysis = strat.analyzers.returns.get_analysis()
    trades_analysis = strat.analyzers.trades.get_analysis()
    
    sharpe_ratio = sharpe_analysis.get('sharperatio', 0) or 0
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0) or 0
    ann_return = returns_analysis.get('rnorm100', 0) or (total_return * 100)
    
    # Trade statistics
    total_trades = trades_analysis.get('total', {}).get('total', 0) or 0
    winning_trades = trades_analysis.get('won', {}).get('total', 0) or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    # Display results
    print('\n' + '='*80)
    print('QVM PORTFOLIO BACKTEST RESULTS')
    print('='*80)
    print(f'Initial Portfolio Value: ${initial_value:,.2f}')
    print(f'Final Portfolio Value: ${final_value:,.2f}')
    print(f'Total Return: {total_return*100:.2f}%')
    print(f'Annualized Return: {ann_return:.2f}%')
    print(f'Sharpe Ratio: {sharpe_ratio:.2f}')
    print(f'Max Drawdown: {max_drawdown:.2f}%')
    print(f'Total Trades: {total_trades}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'Rebalances: {strat.rebalance_count}')
    
    # Success criteria check
    print('\n' + '='*60)
    print('SPRINT 8 SUCCESS CRITERIA ASSESSMENT')
    print('='*60)
    
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
    
    criteria_met = sum(criteria_results)
    print(f"\nOVERALL: {criteria_met}/3 criteria met")
    
    if criteria_met == 3:
        print("SUCCESS - QVM strategy ready for deployment!")
    elif criteria_met >= 2:
        print("MARGINAL - Strategy shows promise but needs refinement")
    else:
        print("FAILED - Strategy requires significant improvement")

    # Save results
    results_data = {
        'test': 'Sprint 8 - QVM Multi-Factor Portfolio Strategy',
        'test_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'universe': universe,
        'initial_value': initial_value,
        'final_value': final_value,
        'total_return_pct': total_return * 100,
        'annualized_return_pct': ann_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown_pct': max_drawdown,
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f'qvm_results_{timestamp}.json')
    
    import json
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    
    return results_data

if __name__ == '__main__':
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    run_portfolio_backtest(UNIVERSE, 'data/sprint_1', 'results/sprint_8')