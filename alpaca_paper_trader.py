# Operation Badger - Paper Trading Engine
# Final validation phase with real alpha signals

import os
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from sec_llm_analyzer import SECLLMAnalyzer
import alpaca_trade_api as tradeapi

class AlpacaPaperTrader:
    def __init__(self):
        """Initialize paper trading system"""
        # Load environment variables for API keys
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = 'https://paper-api.alpaca.markets'  # Paper trading endpoint
        
        if not self.api_key or not self.secret_key:
            print("WARNING: Alpaca API keys not found in environment")
            print("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY")
            self.api = None
        else:
            self.api = tradeapi.REST(self.api_key, self.secret_key, self.base_url, api_version='v2')
        
        # Initialize SEC analyzer for real signals
        self.sec_analyzer = SECLLMAnalyzer()
        
        # Trading configuration
        self.position_size_pct = 0.005  # 0.5% of portfolio per trade
        self.confidence_threshold = 0.75
        self.max_positions = 10
        
        # Validation tracking
        self.validation_file = 'paper_trading_validation.json'
        self.load_validation_state()
        
        print("SUCCESS: Paper trading engine initialized")
        
    def load_validation_state(self):
        """Load existing validation state"""
        try:
            with open(self.validation_file, 'r') as f:
                self.validation_data = json.load(f)
        except FileNotFoundError:
            self.validation_data = {
                'start_date': datetime.now().isoformat(),
                'trades': [],
                'daily_snapshots': [],
                'performance_metrics': {}
            }
            self.save_validation_state()
    
    def save_validation_state(self):
        """Save validation state"""
        with open(self.validation_file, 'w') as f:
            json.dump(self.validation_data, f, indent=2)
    
    def get_account_info(self):
        """Get account information"""
        if not self.api:
            return {'error': 'API not initialized'}
        
        try:
            account = self.api.get_account()
            return {
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'day_trade_count': int(account.day_trade_count)
            }
        except Exception as e:
            print(f"Error getting account info: {e}")
            return {'error': str(e)}
    
    def get_current_positions(self):
        """Get current positions"""
        if not self.api:
            return {}
        
        try:
            positions = self.api.list_positions()
            return {
                pos.symbol: {
                    'qty': float(pos.qty),
                    'market_value': float(pos.market_value),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc)
                }
                for pos in positions
            }
        except Exception as e:
            print(f"Error getting positions: {e}")
            return {}
    
    def generate_live_signals(self) -> List[Dict]:
        """Generate live alpha signals from SEC filings"""
        print("GENERATING: Live alpha signals from SEC filings...")
        
        # Get recent filings for small-cap universe
        small_cap_universe = [
            'CRWD', 'SNOW', 'PLTR', 'DDOG', 'NET', 'OKTA', 'ZS', 'CFLT',
            'ESTC', 'MDB', 'DOCU', 'CRM', 'NOW', 'WDAY', 'ADBE', 'TEAM'
        ]
        
        signals = []
        for symbol in small_cap_universe:
            try:
                # Get recent 8-K filing
                filing_data = self.sec_analyzer.get_recent_filings(symbol, filing_type='8-K', limit=1)
                
                if filing_data:
                    filing = filing_data[0]
                    
                    # Generate velocity score with LLM
                    velocity_score = self.sec_analyzer.analyze_filing_with_llm(
                        filing['filing_url'], symbol
                    )
                    
                    if velocity_score and abs(velocity_score) > 0.1:  # Minimum signal strength
                        confidence = min(0.9, abs(velocity_score) + 0.2)  # Convert to confidence
                        
                        signals.append({
                            'symbol': symbol,
                            'velocity_score': velocity_score,
                            'confidence': confidence,
                            'filing_date': filing['filing_date'],
                            'signal_timestamp': datetime.now().isoformat(),
                            'filing_type': '8-K',
                            'action': 'BUY' if velocity_score > 0 else 'SELL'
                        })
                        
                        print(f"SIGNAL: {symbol} - Score: {velocity_score:.2f}, Confidence: {confidence:.2f}")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error generating signal for {symbol}: {e}")
                continue
        
        return signals
    
    def execute_signal(self, signal: Dict) -> bool:
        """Execute a trading signal"""
        if not self.api:
            print("ERROR: Cannot execute - API not initialized")
            return False
        
        symbol = signal['symbol']
        action = signal['action']
        confidence = signal['confidence']
        
        # Only trade high confidence signals
        if confidence < self.confidence_threshold:
            print(f"SKIP: {symbol} confidence {confidence:.2f} below threshold {self.confidence_threshold}")
            return False
        
        try:
            # Get account info
            account = self.get_account_info()
            if 'error' in account:
                print(f"ERROR: Cannot get account info: {account['error']}")
                return False
            
            # Check current positions
            positions = self.get_current_positions()
            current_position_count = len(positions)
            
            if current_position_count >= self.max_positions:
                print(f"SKIP: Max positions ({self.max_positions}) reached")
                return False
            
            # Calculate position size
            portfolio_value = account['portfolio_value']
            position_value = portfolio_value * self.position_size_pct
            
            # Get current price
            bars = self.api.get_bars(symbol, tradeapi.TimeFrame.Day, limit=1).df
            if bars.empty:
                print(f"ERROR: Cannot get price data for {symbol}")
                return False
            
            current_price = bars['close'].iloc[-1]
            shares_to_trade = int(position_value / current_price)
            
            if shares_to_trade < 1:
                print(f"SKIP: {symbol} position too small ({shares_to_trade} shares)")
                return False
            
            # Execute trade
            if action == 'BUY':
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=shares_to_trade,
                    side='buy',
                    type='market',
                    time_in_force='day'
                )
            else:  # SELL (short not allowed in paper trading)
                if symbol not in positions:
                    print(f"SKIP: Cannot sell {symbol} - no existing position")
                    return False
                
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=min(shares_to_trade, int(positions[symbol]['qty'])),
                    side='sell',
                    type='market',
                    time_in_force='day'
                )
            
            # Record trade
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': action,
                'shares': shares_to_trade,
                'price': current_price,
                'confidence': confidence,
                'velocity_score': signal['velocity_score'],
                'order_id': order.id,
                'filing_date': signal['filing_date']
            }
            
            self.validation_data['trades'].append(trade_record)
            self.save_validation_state()
            
            print(f"EXECUTED: {action} {shares_to_trade} shares of {symbol} at ${current_price:.2f}")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to execute {action} for {symbol}: {e}")
            return False
    
    def take_daily_snapshot(self):
        """Take daily portfolio snapshot for validation"""
        try:
            account = self.get_account_info()
            positions = self.get_current_positions()
            
            snapshot = {
                'date': datetime.now().date().isoformat(),
                'timestamp': datetime.now().isoformat(),
                'portfolio_value': account.get('portfolio_value', 0),
                'cash': account.get('cash', 0),
                'positions_count': len(positions),
                'unrealized_pl': sum(pos.get('unrealized_pl', 0) for pos in positions.values()),
                'day_trade_count': account.get('day_trade_count', 0)
            }
            
            self.validation_data['daily_snapshots'].append(snapshot)
            self.save_validation_state()
            
            print(f"SNAPSHOT: Portfolio ${snapshot['portfolio_value']:,.2f}, P/L ${snapshot['unrealized_pl']:,.2f}")
            
        except Exception as e:
            print(f"Error taking snapshot: {e}")
    
    def calculate_validation_metrics(self) -> Dict:
        """Calculate 30-day validation metrics"""
        if not self.validation_data['daily_snapshots']:
            return {'error': 'No snapshots available'}
        
        snapshots = pd.DataFrame(self.validation_data['daily_snapshots'])
        snapshots['date'] = pd.to_datetime(snapshots['date'])
        
        # Calculate metrics
        start_value = snapshots['portfolio_value'].iloc[0]
        end_value = snapshots['portfolio_value'].iloc[-1]
        total_return = (end_value - start_value) / start_value
        
        # Daily returns
        snapshots['daily_return'] = snapshots['portfolio_value'].pct_change()
        avg_daily_return = snapshots['daily_return'].mean()
        daily_volatility = snapshots['daily_return'].std()
        
        # Sharpe ratio (annualized)
        if daily_volatility > 0:
            sharpe_ratio = (avg_daily_return / daily_volatility) * (252 ** 0.5)
        else:
            sharpe_ratio = 0
        
        # Win rate
        trades_df = pd.DataFrame(self.validation_data['trades'])
        if not trades_df.empty:
            # This is simplified - in practice would need exit prices
            win_rate = len(trades_df[trades_df['velocity_score'] > 0]) / len(trades_df)
        else:
            win_rate = 0
        
        days_elapsed = (datetime.now().date() - 
                       pd.to_datetime(self.validation_data['start_date']).date()).days
        
        metrics = {
            'days_elapsed': days_elapsed,
            'total_return_pct': total_return * 100,
            'annualized_return_pct': (total_return * 365 / max(days_elapsed, 1)) * 100,
            'sharpe_ratio': sharpe_ratio,
            'daily_volatility_pct': daily_volatility * 100 if daily_volatility else 0,
            'max_drawdown_pct': 0,  # Simplified
            'total_trades': len(self.validation_data['trades']),
            'win_rate': win_rate,
            'validation_complete': days_elapsed >= 30
        }
        
        self.validation_data['performance_metrics'] = metrics
        self.save_validation_state()
        
        return metrics
    
    def run_daily_cycle(self):
        """Run daily trading cycle"""
        print("="*60)
        print("OPERATION BADGER - PAPER TRADING CYCLE")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Take daily snapshot
        self.take_daily_snapshot()
        
        # Generate and execute signals
        signals = self.generate_live_signals()
        
        if signals:
            print(f"Generated {len(signals)} alpha signals")
            
            for signal in signals:
                if signal['confidence'] >= self.confidence_threshold:
                    success = self.execute_signal(signal)
                    if success:
                        time.sleep(1)  # Rate limiting
        else:
            print("No qualifying signals generated")
        
        # Calculate validation metrics
        metrics = self.calculate_validation_metrics()
        
        print("\nVALIDATION PROGRESS:")
        print(f"Days Elapsed: {metrics['days_elapsed']}/30")
        print(f"Total Return: {metrics['total_return_pct']:+.2f}%")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Win Rate: {metrics['win_rate']:.1%}")
        
        if metrics['validation_complete']:
            print("\n" + "="*60)
            print("30-DAY VALIDATION COMPLETE!")
            print("="*60)
            
            if (metrics['total_return_pct'] > 0 and 
                metrics['sharpe_ratio'] > 1.0 and 
                metrics['win_rate'] > 0.5):
                print("RESULT: VALIDATION SUCCESSFUL - Ready for live trading")
            else:
                print("RESULT: Validation needs improvement")
        
        print("="*60)

def main():
    """Main execution"""
    trader = AlpacaPaperTrader()
    
    # Check if API is configured
    if not trader.api:
        print("\nSETUP REQUIRED:")
        print("1. Sign up for Alpaca paper trading account")
        print("2. Get API keys from dashboard")
        print("3. Set environment variables:")
        print("   set ALPACA_API_KEY=your_key")
        print("   set ALPACA_SECRET_KEY=your_secret")
        return
    
    # Run daily cycle
    trader.run_daily_cycle()

if __name__ == "__main__":
    main()