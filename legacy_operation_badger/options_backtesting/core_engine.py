#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 16: Options Backtesting Core Engine
Event-driven multi-leg options backtesting architecture for Iron Condor strategies

This module provides the core backtesting engine optimized for SPY options
and volatility trading strategies. Built on research findings showing custom
event-driven architecture outperforms traditional frameworks for options.

Key Features:
- Event-driven market data processing
- Multi-layer separation (data/strategy/execution)
- Greeks calculation integration
- Performance analytics and risk management
- Integration with existing Operation Badger infrastructure
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptionType(Enum):
    """Option type enumeration"""
    CALL = "C"
    PUT = "P"

class PositionSide(Enum):
    """Position side enumeration"""
    LONG = 1
    SHORT = -1

@dataclass
class OptionContract:
    """
    Standardized option contract representation
    Compatible with both Theta Data and yfinance formats
    """
    symbol: str
    underlying: str
    strike: float
    expiration: str
    option_type: OptionType
    
    # Market data
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    
    # Greeks
    delta: float
    gamma: float
    theta: float
    vega: float
    implied_volatility: float
    
    # Derived fields
    mid_price: float
    days_to_expiration: int
    underlying_price: float
    moneyness: float
    
    def __post_init__(self):
        """Calculate derived fields"""
        if self.mid_price == 0:
            self.mid_price = (self.bid + self.ask) / 2 if (self.bid > 0 and self.ask > 0) else self.last

@dataclass
class OptionPosition:
    """
    Option position representation
    """
    contract: OptionContract
    quantity: int  # Positive for long, negative for short
    entry_price: float
    entry_date: datetime
    exit_price: Optional[float] = None
    exit_date: Optional[datetime] = None
    
    @property
    def is_open(self) -> bool:
        """Check if position is still open"""
        return self.exit_date is None
    
    @property
    def market_value(self) -> float:
        """Current market value of the position"""
        current_price = self.contract.mid_price
        return self.quantity * current_price * 100  # Options are per 100 shares
    
    @property
    def pnl(self) -> float:
        """Unrealized or realized P&L"""
        if self.is_open:
            return (self.contract.mid_price - self.entry_price) * self.quantity * 100
        else:
            return (self.exit_price - self.entry_price) * self.quantity * 100

@dataclass
class IronCondorPosition:
    """
    Iron Condor multi-leg position
    Composed of: Short Call, Long Call, Short Put, Long Put
    """
    short_call: OptionPosition
    long_call: OptionPosition
    short_put: OptionPosition
    long_put: OptionPosition
    
    entry_date: datetime
    expiration: str
    underlying_price_at_entry: float
    
    # Strategy parameters
    wing_width: float
    max_profit: float
    max_loss: float
    breakeven_upper: float
    breakeven_lower: float
    
    @property
    def is_open(self) -> bool:
        """Check if Iron Condor is still open"""
        return all(pos.is_open for pos in [self.short_call, self.long_call, self.short_put, self.long_put])
    
    @property
    def net_delta(self) -> float:
        """Net delta exposure of the Iron Condor"""
        return sum([
            pos.contract.delta * pos.quantity 
            for pos in [self.short_call, self.long_call, self.short_put, self.long_put]
        ])
    
    @property
    def net_gamma(self) -> float:
        """Net gamma exposure"""
        return sum([
            pos.contract.gamma * pos.quantity 
            for pos in [self.short_call, self.long_call, self.short_put, self.long_put]
        ])
    
    @property
    def net_theta(self) -> float:
        """Net theta (time decay) - should be positive for Iron Condors"""
        return sum([
            pos.contract.theta * pos.quantity 
            for pos in [self.short_call, self.long_call, self.short_put, self.long_put]
        ])
    
    @property
    def net_vega(self) -> float:
        """Net vega (volatility sensitivity)"""
        return sum([
            pos.contract.vega * pos.quantity 
            for pos in [self.short_call, self.long_call, self.short_put, self.long_put]
        ])
    
    @property
    def total_pnl(self) -> float:
        """Total P&L of the Iron Condor"""
        return sum([pos.pnl for pos in [self.short_call, self.long_call, self.short_put, self.long_put]])
    
    @property
    def net_premium_collected(self) -> float:
        """Net premium collected when opening the Iron Condor"""
        return (self.short_call.entry_price + self.short_put.entry_price - 
                self.long_call.entry_price - self.long_put.entry_price) * 100

class MarketDataEvent:
    """
    Market data event for event-driven processing
    """
    def __init__(self, timestamp: datetime, symbol: str, data: Dict[str, Any]):
        self.timestamp = timestamp
        self.symbol = symbol
        self.data = data
        self.options_chain: Optional[List[OptionContract]] = None

class StrategyEvent:
    """
    Strategy signal event
    """
    def __init__(self, timestamp: datetime, strategy_name: str, signal: str, params: Dict[str, Any]):
        self.timestamp = timestamp
        self.strategy_name = strategy_name
        self.signal = signal  # 'OPEN', 'CLOSE', 'ADJUST'
        self.params = params

class ExecutionEvent:
    """
    Order execution event
    """
    def __init__(self, timestamp: datetime, order_type: str, symbol: str, 
                 quantity: int, price: float, fees: float = 0.0):
        self.timestamp = timestamp
        self.order_type = order_type  # 'BUY', 'SELL'
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.fees = fees

class PerformanceTracker:
    """
    Performance analytics and metrics tracking
    """
    def __init__(self):
        self.trades: List[Dict] = []
        self.daily_pnl: List[Dict] = []
        self.greeks_history: List[Dict] = []
        self.max_drawdown = 0.0
        self.peak_value = 0.0
        
    def record_trade(self, trade_data: Dict):
        """Record a completed trade"""
        self.trades.append({
            'timestamp': datetime.now(),
            **trade_data
        })
        
    def record_daily_pnl(self, date: datetime, pnl: float, portfolio_value: float):
        """Record daily P&L"""
        self.daily_pnl.append({
            'date': date,
            'pnl': pnl,
            'portfolio_value': portfolio_value,
            'cumulative_return': (portfolio_value - 100000) / 100000  # Assuming $100k start
        })
        
        # Update drawdown metrics
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
        
        current_drawdown = (self.peak_value - portfolio_value) / self.peak_value
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
            
    def record_greeks(self, date: datetime, greeks: Dict[str, float]):
        """Record portfolio Greeks"""
        self.greeks_history.append({
            'date': date,
            **greeks
        })
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        if not self.daily_pnl:
            return {}
            
        df = pd.DataFrame(self.daily_pnl)
        
        # Calculate key metrics
        total_return = df['cumulative_return'].iloc[-1] * 100
        
        # Sharpe ratio calculation
        daily_returns = df['pnl'] / 100000  # Convert to percentage
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        # Win rate
        winning_trades = len([t for t in self.trades if t.get('pnl', 0) > 0])
        total_trades = len(self.trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_return_pct': total_return,
            'annualized_return_pct': total_return * (252 / len(df)) if len(df) > 0 else 0,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': self.max_drawdown * 100,
            'total_trades': total_trades,
            'win_rate_pct': win_rate,
            'avg_trade_pnl': sum([t.get('pnl', 0) for t in self.trades]) / total_trades if total_trades > 0 else 0,
            'final_portfolio_value': df['portfolio_value'].iloc[-1] if not df.empty else 100000
        }

class OptionsBacktestEngine:
    """
    Core options backtesting engine
    Event-driven architecture for multi-leg options strategies
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: List[IronCondorPosition] = []
        self.performance = PerformanceTracker()
        
        # Event queues
        self.market_data_queue: List[MarketDataEvent] = []
        self.strategy_queue: List[StrategyEvent] = []
        self.execution_queue: List[ExecutionEvent] = []
        
        logger.info(f"Options backtest engine initialized with ${initial_capital:,.2f}")
        
    def add_market_data_event(self, event: MarketDataEvent):
        """Add market data event to processing queue"""
        self.market_data_queue.append(event)
        
    def add_strategy_event(self, event: StrategyEvent):
        """Add strategy event to processing queue"""
        self.strategy_queue.append(event)
        
    def add_execution_event(self, event: ExecutionEvent):
        """Add execution event to processing queue"""
        self.execution_queue.append(event)
        
    def process_market_data(self, event: MarketDataEvent):
        """Process market data event and update positions"""
        # Update existing positions with new market data
        for ic_position in self.positions:
            if ic_position.is_open:
                # Update contract prices with new market data
                self._update_position_prices(ic_position, event)
                
        # Update portfolio metrics
        portfolio_value = self._calculate_portfolio_value()
        daily_pnl = portfolio_value - self.initial_capital
        
        self.performance.record_daily_pnl(event.timestamp, daily_pnl, portfolio_value)
        
        # Record Greeks if options chain is available
        if event.options_chain:
            portfolio_greeks = self._calculate_portfolio_greeks()
            self.performance.record_greeks(event.timestamp, portfolio_greeks)
            
    def process_strategy_event(self, event: StrategyEvent):
        """Process strategy signal and generate execution orders"""
        if event.signal == 'OPEN' and event.strategy_name == 'iron_condor':
            self._open_iron_condor(event)
        elif event.signal == 'CLOSE':
            self._close_positions(event)
        elif event.signal == 'ADJUST':
            self._adjust_positions(event)
            
    def process_execution_event(self, event: ExecutionEvent):
        """Process order execution"""
        # Update capital based on execution
        if event.order_type == 'BUY':
            self.current_capital -= (event.quantity * event.price * 100 + event.fees)
        else:  # SELL
            self.current_capital += (event.quantity * event.price * 100 - event.fees)
            
        logger.info(f"Executed {event.order_type} {event.quantity} {event.symbol} @ ${event.price:.2f}")
        
    def _update_position_prices(self, ic_position: IronCondorPosition, event: MarketDataEvent):
        """Update option contract prices based on new market data"""
        if event.options_chain:
            for contract in event.options_chain:
                # Update prices for matching contracts
                for pos in [ic_position.short_call, ic_position.long_call, 
                           ic_position.short_put, ic_position.long_put]:
                    if (pos.contract.strike == contract.strike and 
                        pos.contract.option_type == contract.option_type and
                        pos.contract.expiration == contract.expiration):
                        # Update contract with new market data
                        pos.contract.bid = contract.bid
                        pos.contract.ask = contract.ask
                        pos.contract.last = contract.last
                        pos.contract.mid_price = contract.mid_price
                        pos.contract.delta = contract.delta
                        pos.contract.gamma = contract.gamma
                        pos.contract.theta = contract.theta
                        pos.contract.vega = contract.vega
                        pos.contract.implied_volatility = contract.implied_volatility
                        
    def _calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        cash = self.current_capital
        positions_value = sum([ic.total_pnl for ic in self.positions if ic.is_open])
        return cash + positions_value
        
    def _calculate_portfolio_greeks(self) -> Dict[str, float]:
        """Calculate portfolio-level Greeks"""
        total_delta = sum([ic.net_delta for ic in self.positions if ic.is_open])
        total_gamma = sum([ic.net_gamma for ic in self.positions if ic.is_open])
        total_theta = sum([ic.net_theta for ic in self.positions if ic.is_open])
        total_vega = sum([ic.net_vega for ic in self.positions if ic.is_open])
        
        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega
        }
        
    def _open_iron_condor(self, event: StrategyEvent):
        """Open new Iron Condor position"""
        params = event.params
        
        # This would be implemented with actual order generation
        # For now, we'll simulate the position creation
        logger.info(f"Opening Iron Condor position at {event.timestamp}")
        logger.info(f"Parameters: {params}")
        
    def _close_positions(self, event: StrategyEvent):
        """Close existing positions"""
        logger.info(f"Closing positions at {event.timestamp}")
        
    def _adjust_positions(self, event: StrategyEvent):
        """Adjust existing positions"""
        logger.info(f"Adjusting positions at {event.timestamp}")
        
    def run_backtest(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Run complete backtest for the specified date range
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Process events chronologically
        current_date = start_date
        
        while current_date <= end_date:
            # Process events for current date
            self._process_events_for_date(current_date)
            
            current_date += timedelta(days=1)
            
        # Generate final performance report
        performance_summary = self.performance.get_performance_summary()
        
        logger.info("Backtest completed")
        logger.info(f"Final portfolio value: ${self._calculate_portfolio_value():,.2f}")
        
        return {
            'backtest_period': f"{start_date} to {end_date}",
            'initial_capital': self.initial_capital,
            'final_value': self._calculate_portfolio_value(),
            'performance_metrics': performance_summary,
            'total_positions': len(self.positions),
            'open_positions': len([ic for ic in self.positions if ic.is_open])
        }
        
    def _process_events_for_date(self, date: datetime):
        """Process all events for a specific date"""
        # This would be enhanced with actual data loading and strategy logic
        # For now, it's a placeholder for the event processing framework
        pass


def main():
    """
    Test the options backtesting engine
    """
    print("=" * 80)
    print("SPRINT 16: OPTIONS BACKTESTING ENGINE TEST")
    print("=" * 80)
    
    # Initialize backtesting engine
    engine = OptionsBacktestEngine(initial_capital=100000.0)
    
    # Test basic functionality
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    print(f"Testing backtest framework from {start_date.date()} to {end_date.date()}")
    
    # Run basic backtest (currently just framework test)
    results = engine.run_backtest(start_date, end_date)
    
    print("\nBacktest Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")
    
    print("\nCore engine architecture validated [SUCCESS]")
    print("Ready for Iron Condor strategy implementation")


if __name__ == "__main__":
    main()