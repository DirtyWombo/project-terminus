# enhanced_backtest_framework.py
import backtrader as bt
import pandas as pd
import os
import json
from datetime import datetime
import numpy as np

class TradeLogger:
    """Enhanced trade logging for detailed analysis"""
    def __init__(self):
        self.trades = []
        self.daily_values = []
    
    def log_trade(self, trade_data):
        self.trades.append(trade_data)
    
    def log_daily_value(self, date, value, cash, position_value):
        self.daily_values.append({
            'date': date.strftime('%Y-%m-%d'),
            'portfolio_value': value,
            'cash': cash,
            'position_value': position_value
        })

class EnhancedGoldenCross(bt.Strategy):
    params = (('fast', 50), ('slow', 200),)
    
    def __init__(self):
        self.crossover = bt.indicators.CrossOver(
            bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.fast),
            bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.slow)
        )
        self.trade_logger = TradeLogger()
        self.entry_price = None
        self.entry_date = None
        
    def next(self):
        # Log daily portfolio value
        current_value = self.broker.getvalue()
        cash = self.broker.getcash()
        position_value = current_value - cash
        self.trade_logger.log_daily_value(self.data.datetime.date(0), current_value, cash, position_value)
        
        if not self.position:
            if self.crossover > 0:
                self.entry_price = self.data.close[0]
                self.entry_date = self.data.datetime.date(0)
                self.buy()
        elif self.crossover < 0:
            self.close()
    
    def notify_trade(self, trade):
        if trade.isclosed:
            trade_data = {
                'entry_date': self.entry_date.strftime('%Y-%m-%d') if self.entry_date else None,
                'exit_date': self.data.datetime.date(0).strftime('%Y-%m-%d'),
                'entry_price': float(self.entry_price) if self.entry_price else None,
                'exit_price': float(self.data.close[0]),
                'pnl': float(trade.pnl),
                'pnl_pct': float(trade.pnl / abs(trade.value) * 100) if trade.value != 0 else 0,
                'size': float(trade.size),
                'value': float(trade.value),
                'commission': float(trade.commission),
                'duration_days': (self.data.datetime.date(0) - self.entry_date).days if self.entry_date else 0
            }
            self.trade_logger.log_trade(trade_data)

class EnhancedBollingerBounce(bt.Strategy):
    params = (('period', 20), ('devfactor', 2.0),)
    
    def __init__(self):
        self.bollinger = bt.indicators.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)
        self.trade_logger = TradeLogger()
        self.entry_price = None
        self.entry_date = None
        
    def next(self):
        # Log daily portfolio value
        current_value = self.broker.getvalue()
        cash = self.broker.getcash()
        position_value = current_value - cash
        self.trade_logger.log_daily_value(self.data.datetime.date(0), current_value, cash, position_value)
        
        if not self.position:
            if self.data.close < self.bollinger.lines.bot:
                self.entry_price = self.data.close[0]
                self.entry_date = self.data.datetime.date(0)
                self.buy()
        else:
            if self.data.close > self.bollinger.lines.mid:
                self.sell()
    
    def notify_trade(self, trade):
        if trade.isclosed:
            trade_data = {
                'entry_date': self.entry_date.strftime('%Y-%m-%d') if self.entry_date else None,
                'exit_date': self.data.datetime.date(0).strftime('%Y-%m-%d'),
                'entry_price': float(self.entry_price) if self.entry_price else None,
                'exit_price': float(self.data.close[0]),
                'pnl': float(trade.pnl),
                'pnl_pct': float(trade.pnl / abs(trade.value) * 100) if trade.value != 0 else 0,
                'size': float(trade.size),
                'value': float(trade.value),
                'commission': float(trade.commission),
                'duration_days': (self.data.datetime.date(0) - self.entry_date).days if self.entry_date else 0
            }
            self.trade_logger.log_trade(trade_data)

def run_enhanced_backtest(strategy_class, strategy_name, ticker, data_dir, results_dir):
    """Run enhanced backtest with detailed logging"""
    
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(strategy_class)
    
    data_path = os.path.join(data_dir, f'{ticker}.csv')
    if not os.path.exists(data_path):
        return None
    
    try:
        # Load data
        df = pd.read_csv(data_path, index_col='Date', parse_dates=True)
        data_feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data_feed, name=ticker)
        
        # Set up broker
        cerebro.broker.setcash(10000.0)
        cerebro.broker.setcommission(commission=0.001)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        print(f'Running enhanced {strategy_name} backtest for {ticker}...')
        
        # Run backtest
        result = cerebro.run()[0]
        
        # Extract results
        final_value = cerebro.broker.getvalue()
        total_return = (final_value - 10000) / 10000 * 100
        
        # Get analyzer results
        sharpe = result.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        if sharpe is None: sharpe = 0
        
        drawdown = result.analyzers.drawdown.get_analysis()
        trades = result.analyzers.trades.get_analysis()
        
        # Compile comprehensive results
        enhanced_results = {
            'ticker': ticker,
            'strategy': strategy_name,
            'summary': {
                'final_value': final_value,
                'total_return_pct': total_return,
                'sharpe_ratio': sharpe,
                'max_drawdown_pct': drawdown.get('max', {}).get('drawdown', 0),
                'total_trades': trades.get('total', {}).get('total', 0),
                'winning_trades': trades.get('won', {}).get('total', 0),
                'losing_trades': trades.get('lost', {}).get('total', 0),
                'win_rate_pct': (trades.get('won', {}).get('total', 0) / max(trades.get('total', {}).get('total', 1), 1)) * 100,
                'avg_win_pct': trades.get('won', {}).get('pnl', {}).get('average', 0),
                'avg_loss_pct': trades.get('lost', {}).get('pnl', {}).get('average', 0),
                'profit_factor': abs(trades.get('won', {}).get('pnl', {}).get('total', 0) / max(abs(trades.get('lost', {}).get('pnl', {}).get('total', 1)), 1))
            },
            'detailed_trades': result.trade_logger.trades,
            'daily_values': result.trade_logger.daily_values[-50:],  # Last 50 days for space
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return enhanced_results
        
    except Exception as e:
        print(f"Error processing {ticker}: {e}")
        return None

def analyze_trade_patterns(results):
    """Analyze trade patterns for insights"""
    if not results or not results['detailed_trades']:
        return {}
    
    trades = pd.DataFrame(results['detailed_trades'])
    
    analysis = {
        'trade_duration_stats': {
            'avg_duration_days': trades['duration_days'].mean() if not trades.empty else 0,
            'min_duration_days': trades['duration_days'].min() if not trades.empty else 0,
            'max_duration_days': trades['duration_days'].max() if not trades.empty else 0
        },
        'monthly_performance': {},
        'trade_size_analysis': {
            'avg_trade_size': trades['size'].mean() if not trades.empty else 0,
            'avg_trade_value': trades['value'].mean() if not trades.empty else 0
        }
    }
    
    # Monthly breakdown
    if not trades.empty:
        trades['exit_month'] = pd.to_datetime(trades['exit_date']).dt.to_period('M')
        monthly = trades.groupby('exit_month')['pnl'].sum()
        analysis['monthly_performance'] = {str(k): float(v) for k, v in monthly.items()}
    
    return analysis

if __name__ == '__main__':
    UNIVERSE = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX']  # Subset for testing
    DATA_DIR = 'data/sprint_1'
    RESULTS_DIR = 'results/sprint_1/enhanced'
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    strategies = [
        (EnhancedGoldenCross, 'Enhanced_MA_Crossover'),
        (EnhancedBollingerBounce, 'Enhanced_Bollinger_Bounce')
    ]
    
    all_enhanced_results = {}
    
    for strategy_class, strategy_name in strategies:
        print(f"\n=== Running Enhanced {strategy_name} ===")
        strategy_results = {}
        
        for ticker in UNIVERSE:
            result = run_enhanced_backtest(strategy_class, strategy_name, ticker, DATA_DIR, RESULTS_DIR)
            if result:
                # Add trade pattern analysis
                result['trade_patterns'] = analyze_trade_patterns(result)
                strategy_results[ticker] = result
        
        all_enhanced_results[strategy_name] = strategy_results
    
    # Save enhanced results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    enhanced_file = os.path.join(RESULTS_DIR, f'enhanced_analysis_{timestamp}.json')
    
    with open(enhanced_file, 'w') as f:
        json.dump(all_enhanced_results, f, indent=2, default=str)
    
    print(f"\nEnhanced results saved to: {enhanced_file}")
    print(f"Enhanced analysis complete with detailed trade logging and pattern analysis.")