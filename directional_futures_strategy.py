"""
Project Terminus - Directional Futures Strategy
200MA/20EMA trend following strategy for /MES futures
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

class MarketRegime(Enum):
    """Market regime classifications"""
    BULL = "Bull"
    BEAR = "Bear"
    NEUTRAL = "Neutral"

class SignalType(Enum):
    """Trading signal types"""
    BUY = "Buy"
    SELL = "Sell"
    HOLD = "Hold"
    CLOSE = "Close"

class DirectionalFuturesStrategy:
    """
    200MA/20EMA Directional Strategy for /MES Futures
    
    Strategy Rules:
    1. Bull Market: SPY > 200MA
    2. Entry: Price touches 20EMA in bull market
    3. Exit: Stop loss or trend reversal
    """
    
    def __init__(self, 
                 ma_long_period: int = 200,
                 ma_short_period: int = 20,
                 stop_loss_points: float = 10.0):
        """
        Initialize strategy parameters
        
        Args:
            ma_long_period: Period for long-term MA (default 200)
            ma_short_period: Period for short-term EMA (default 20)
            stop_loss_points: Stop loss in points (default 10 = $50 risk)
        """
        self.ma_long_period = ma_long_period
        self.ma_short_period = ma_short_period
        self.stop_loss_points = stop_loss_points
        
        # Strategy state
        self.current_regime = MarketRegime.NEUTRAL
        self.last_signal = SignalType.HOLD
        self.position_entry_price = None
        self.position_stop_loss = None
        
        # Price history for indicator calculation
        self.price_history = []
        self.indicators = {}
    
    def update_price_history(self, price: float, timestamp: datetime):
        """Add new price to history and update indicators"""
        self.price_history.append({
            'timestamp': timestamp,
            'price': price
        })
        
        # Keep only necessary history (MA long period + buffer)
        max_history = self.ma_long_period + 50
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]
        
        # Update indicators if we have enough data
        if len(self.price_history) >= self.ma_long_period:
            self._calculate_indicators()
    
    def _calculate_indicators(self):
        """Calculate technical indicators"""
        # Convert to pandas for easier calculation
        df = pd.DataFrame(self.price_history)
        
        # Simple Moving Average (200-day)
        df['SMA_200'] = df['price'].rolling(window=self.ma_long_period).mean()
        
        # Exponential Moving Average (20-day)
        df['EMA_20'] = df['price'].ewm(span=self.ma_short_period, adjust=False).mean()
        
        # Store latest values
        self.indicators = {
            'current_price': df['price'].iloc[-1],
            'sma_200': df['SMA_200'].iloc[-1],
            'ema_20': df['EMA_20'].iloc[-1],
            'prev_price': df['price'].iloc[-2] if len(df) > 1 else None,
            'prev_ema_20': df['EMA_20'].iloc[-2] if len(df) > 1 else None
        }
        
        # Update market regime
        self._update_market_regime()
    
    def _update_market_regime(self):
        """Determine current market regime"""
        if not self.indicators or pd.isna(self.indicators['sma_200']):
            self.current_regime = MarketRegime.NEUTRAL
            return
        
        current_price = self.indicators['current_price']
        sma_200 = self.indicators['sma_200']
        
        # Bull market: Price above 200MA
        if current_price > sma_200:
            self.current_regime = MarketRegime.BULL
        # Bear market: Price below 200MA  
        elif current_price < sma_200:
            self.current_regime = MarketRegime.BEAR
        else:
            self.current_regime = MarketRegime.NEUTRAL
    
    def generate_signal(self) -> Tuple[SignalType, Dict]:
        """
        Generate trading signal based on current market conditions
        
        Returns:
            Tuple of (signal_type, signal_details)
        """
        if not self.indicators or pd.isna(self.indicators['sma_200']):
            return SignalType.HOLD, {"reason": "Insufficient data"}
        
        current_price = self.indicators['current_price']
        ema_20 = self.indicators['ema_20']
        prev_price = self.indicators['prev_price']
        prev_ema_20 = self.indicators['prev_ema_20']
        
        signal_details = {
            'regime': self.current_regime.value,
            'current_price': current_price,
            'sma_200': self.indicators['sma_200'],
            'ema_20': ema_20,
            'timestamp': datetime.now()
        }
        
        # Check if we have an open position
        if self.position_entry_price is not None:
            # Check stop loss
            if current_price <= self.position_stop_loss:
                signal_details['reason'] = "Stop loss hit"
                signal_details['exit_price'] = current_price
                self.position_entry_price = None
                self.position_stop_loss = None
                return SignalType.CLOSE, signal_details
            
            # Check regime change (exit on bear market)
            if self.current_regime != MarketRegime.BULL:
                signal_details['reason'] = "Market regime changed to non-bull"
                signal_details['exit_price'] = current_price
                self.position_entry_price = None
                self.position_stop_loss = None
                return SignalType.CLOSE, signal_details
            
            # Hold position
            signal_details['reason'] = "Position open, conditions still valid"
            return SignalType.HOLD, signal_details
        
        # Look for new entry signals (only in bull market)
        if self.current_regime == MarketRegime.BULL:
            # Check for EMA touch/pullback completion
            if prev_price and prev_ema_20:
                # Price crossed above EMA (pullback completion)
                if prev_price <= prev_ema_20 and current_price > ema_20:
                    signal_details['reason'] = "Bullish EMA crossover after pullback"
                    signal_details['entry_price'] = current_price
                    signal_details['stop_loss'] = current_price - self.stop_loss_points
                    
                    # Set position tracking
                    self.position_entry_price = current_price
                    self.position_stop_loss = current_price - self.stop_loss_points
                    
                    return SignalType.BUY, signal_details
        
        # No signal
        signal_details['reason'] = f"No signal in {self.current_regime.value} market"
        return SignalType.HOLD, signal_details
    
    def get_strategy_state(self) -> Dict:
        """Get current strategy state and indicators"""
        return {
            'regime': self.current_regime.value,
            'last_signal': self.last_signal.value,
            'position_open': self.position_entry_price is not None,
            'position_entry': self.position_entry_price,
            'position_stop_loss': self.position_stop_loss,
            'indicators': self.indicators.copy() if self.indicators else {},
            'data_points': len(self.price_history)
        }
    
    def backtest(self, historical_data: List[Dict]) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            historical_data: List of {'timestamp', 'price'} dicts
            
        Returns:
            Backtest results dictionary
        """
        trades = []
        equity_curve = [25000]  # Starting with Apex 25K
        
        for data_point in historical_data:
            # Update price history
            self.update_price_history(
                data_point['price'], 
                data_point['timestamp']
            )
            
            # Generate signal
            signal, details = self.generate_signal()
            
            # Execute trades
            if signal == SignalType.BUY:
                trades.append({
                    'type': 'entry',
                    'price': details['entry_price'],
                    'timestamp': details['timestamp'],
                    'stop_loss': details['stop_loss']
                })
            
            elif signal == SignalType.CLOSE and trades and trades[-1]['type'] == 'entry':
                entry_trade = trades[-1]
                pnl = (details['exit_price'] - entry_trade['price']) * 5  # $5 per point
                
                trades.append({
                    'type': 'exit',
                    'price': details['exit_price'],
                    'timestamp': details['timestamp'],
                    'pnl': pnl,
                    'reason': details['reason']
                })
                
                # Update equity
                equity_curve.append(equity_curve[-1] + pnl)
        
        # Calculate statistics
        winning_trades = [t for t in trades if t.get('type') == 'exit' and t['pnl'] > 0]
        losing_trades = [t for t in trades if t.get('type') == 'exit' and t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in trades if t.get('type') == 'exit')
        win_rate = len(winning_trades) / len([t for t in trades if t.get('type') == 'exit']) if trades else 0
        
        return {
            'total_trades': len([t for t in trades if t.get('type') == 'exit']),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'final_equity': equity_curve[-1],
            'max_drawdown': self._calculate_max_drawdown(equity_curve),
            'sharpe_ratio': self._calculate_sharpe_ratio(equity_curve),
            'trades': trades
        }
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown from equity curve"""
        if len(equity_curve) < 2:
            return 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        
        for value in equity_curve[1:]:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, equity_curve: List[float], periods_per_year: int = 252) -> float:
        """Calculate Sharpe ratio from equity curve"""
        if len(equity_curve) < 2:
            return 0.0
        
        returns = pd.Series(equity_curve).pct_change().dropna()
        if len(returns) == 0:
            return 0.0
        
        avg_return = returns.mean()
        std_return = returns.std()
        
        if std_return == 0:
            return 0.0
        
        return (avg_return * np.sqrt(periods_per_year)) / std_return

def test_strategy():
    """Test the directional futures strategy"""
    print("=" * 60)
    print("🎯 DIRECTIONAL FUTURES STRATEGY TEST")
    print("=" * 60)
    
    # Create strategy instance
    strategy = DirectionalFuturesStrategy()
    
    # Generate sample data (normally would come from Databento)
    sample_data = []
    base_price = 4500.0
    timestamp = datetime.now() - timedelta(days=250)
    
    # Create trending market data
    for i in range(500):
        # Add some noise and trend
        if i < 200:
            price = base_price + i * 0.5 + np.random.normal(0, 2)
        else:
            price = base_price + 100 + (i - 200) * 0.3 + np.random.normal(0, 3)
        
        sample_data.append({
            'timestamp': timestamp,
            'price': price
        })
        timestamp += timedelta(hours=1)
    
    # Run backtest
    print("\n📊 Running Backtest...")
    results = strategy.backtest(sample_data)
    
    print(f"\n📈 Backtest Results:")
    print(f"   Total Trades: {results['total_trades']}")
    print(f"   Win Rate: {results['win_rate']:.1%}")
    print(f"   Total P&L: ${results['total_pnl']:,.2f}")
    print(f"   Final Equity: ${results['final_equity']:,.2f}")
    print(f"   Max Drawdown: {results['max_drawdown']:.1%}")
    print(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    
    # Show current state
    state = strategy.get_strategy_state()
    print(f"\n🔍 Current Strategy State:")
    print(f"   Market Regime: {state['regime']}")
    print(f"   Data Points: {state['data_points']}")
    print(f"   Position Open: {state['position_open']}")

if __name__ == "__main__":
    test_strategy()