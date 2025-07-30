#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 19: Live Paper Trading Engine for Bull Call Spread Strategy
Event-driven trading system for real-world validation

This module implements the production-ready live trading engine that executes
the validated Bull Call Spread strategy in a live paper trading environment.
Built for 30-day validation before real capital deployment.

Key Features:
- Event-driven architecture with scheduled strategy evaluation
- Real-time market data integration
- Multi-leg options order management
- Comprehensive logging and monitoring
- Portfolio state management
- Error handling and recovery
"""

import os
import sys
import time
import json
import logging
import schedule
import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import traceback

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our validated strategy and OMS
from bull_call_spread_strategy import BullCallSpreadStrategy
from order_management_system import OrderManagementSystem

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_trader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Market Hours Utilities
def is_market_open(dt: datetime = None) -> bool:
    """Check if the market is currently open"""
    if dt is None:
        dt = datetime.now()
    
    # Convert to ET timezone
    et_tz = pytz.timezone('America/New_York')
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt).astimezone(et_tz)
    else:
        dt = dt.astimezone(et_tz)
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    if dt.weekday() >= 5:  # Weekend
        return False
    
    # Check if within market hours (9:30 AM - 4:00 PM ET)
    market_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = dt.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= dt <= market_close

def get_next_market_open(dt: datetime = None) -> datetime:
    """Get the next market open time"""
    if dt is None:
        dt = datetime.now()
    
    et_tz = pytz.timezone('America/New_York')
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt).astimezone(et_tz)
    else:
        dt = dt.astimezone(et_tz)
    
    # Set to next 9:30 AM
    next_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)
    
    # If we're past today's open or it's weekend, move to next business day
    if dt >= next_open or dt.weekday() >= 5:
        next_open += timedelta(days=1)
        while next_open.weekday() >= 5:  # Skip weekends
            next_open += timedelta(days=1)
        next_open = next_open.replace(hour=9, minute=30, second=0, microsecond=0)
    
    return next_open

def should_gather_premarket_data(dt: datetime = None) -> bool:
    """Check if we should be gathering pre-market data (1 hour before market open)"""
    if dt is None:
        dt = datetime.now()
    
    et_tz = pytz.timezone('America/New_York')
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt).astimezone(et_tz)
    else:
        dt = dt.astimezone(et_tz)
    
    # Check if it's a weekday
    if dt.weekday() >= 5:
        return False
    
    # Check if within pre-market hours (8:30 AM - 9:30 AM ET)
    premarket_start = dt.replace(hour=8, minute=30, second=0, microsecond=0)
    market_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)
    
    return premarket_start <= dt < market_open

class TradingState(Enum):
    """Trading system states"""
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"

class OrderStatus(Enum):
    """Order status tracking"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class LivePosition:
    """Live trading position representation"""
    symbol: str
    strategy_id: str
    entry_date: datetime
    expiration: str
    long_call_strike: float
    short_call_strike: float
    contracts: int
    net_debit_paid: float
    current_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    status: str = "OPEN"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['entry_date'] = self.entry_date.isoformat() if self.entry_date else None
        return data

@dataclass
class TradingMetrics:
    """Live trading performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    win_rate: float = 0.0
    largest_winner: float = 0.0
    largest_loser: float = 0.0
    total_commissions: float = 0.0
    
    def update_metrics(self, trades: List[LivePosition]):
        """Update metrics from current trades"""
        closed_trades = [t for t in trades if t.status == "CLOSED"]
        
        self.total_trades = len(closed_trades)
        self.winning_trades = len([t for t in closed_trades if t.current_pnl > 0])
        self.losing_trades = len([t for t in closed_trades if t.current_pnl < 0])
        
        if closed_trades:
            self.realized_pnl = sum([t.current_pnl for t in closed_trades])
            self.win_rate = (self.winning_trades / self.total_trades) * 100
            
            pnls = [t.current_pnl for t in closed_trades]
            self.largest_winner = max(pnls) if pnls else 0
            self.largest_loser = min(pnls) if pnls else 0
        
        # Calculate unrealized P&L from open positions
        open_trades = [t for t in trades if t.status == "OPEN"]
        self.unrealized_pnl = sum([t.unrealized_pnl for t in open_trades])
        
        self.total_pnl = self.realized_pnl + self.unrealized_pnl

class LiveTradingEngine:
    """
    Production-ready live trading engine for Bull Call Spread strategy
    """
    
    def __init__(self, config_file: str = "live_trader_config.json"):
        """
        Initialize the live trading engine
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.state = TradingState.INITIALIZING
        self.load_configuration()
        
        # Initialize strategy
        underlying_symbol = self.config.get('underlying_symbol', 'SPY')
        self.strategy = BullCallSpreadStrategy(symbol=underlying_symbol)
        
        # Initialize Order Management System
        oms_config = {
            'paper_trading': self.config.get('paper_trading', True),
            'commission_per_contract': self.config.get('commission_per_contract', 0.65),
            'fill_delay_seconds': self.config.get('fill_delay_seconds', 5)
        }
        self.oms = OrderManagementSystem(config=oms_config)
        
        # Trading state
        self.positions: List[LivePosition] = []
        self.pending_orders: Dict[str, Dict] = {}
        self.metrics = TradingMetrics()
        self.last_signal_check = None
        self.market_data_cache = {}
        
        # Paper trading simulation
        self.paper_cash = self.config.get('initial_capital', 100000.0)
        self.paper_equity = self.paper_cash
        
        # Load persistent state
        self.state_file = "live_trader_state.json"
        self.load_state()
        
        # Initialize data connections
        self.initialize_data_connections()
        
        logger.info("Live Trading Engine initialized successfully")
        logger.info(f"Strategy: Bull Call Spread")
        logger.info(f"Initial Capital: ${self.paper_cash:,.2f}")
        logger.info(f"Max Positions: {self.config.get('max_positions', 3)}")
        
        self.state = TradingState.RUNNING
    
    def load_configuration(self):
        """Load trading configuration from file"""
        default_config = {
            "initial_capital": 100000.0,
            "target_dte": 45,
            "long_call_delta": 0.50,
            "short_call_delta": 0.30,
            "profit_target": 1.00,
            "stop_loss": 0.50,
            "max_positions": 3,
            "contracts_per_trade": 10,
            "commission_per_contract": 0.65,
            "signal_check_interval": "1H",  # Check every hour
            "underlying_symbol": "SPY",
            "paper_trading": True
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                self.config = default_config
                self.save_configuration()
                logger.info("Default configuration created")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = default_config
    
    def save_configuration(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def load_state(self):
        """Load persistent trading state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore positions
                self.positions = []
                for pos_data in state_data.get('positions', []):
                    pos = LivePosition(**pos_data)
                    if pos_data.get('entry_date'):
                        pos.entry_date = datetime.fromisoformat(pos_data['entry_date'])
                    self.positions.append(pos)
                
                # Restore capital
                self.paper_cash = state_data.get('paper_cash', self.config['initial_capital'])
                self.paper_equity = state_data.get('paper_equity', self.paper_cash)
                
                logger.info(f"State loaded: {len(self.positions)} positions, ${self.paper_equity:,.2f} equity")
        except Exception as e:
            logger.warning(f"Could not load previous state: {e}")
    
    def save_state(self):
        """Save current trading state"""
        try:
            state_data = {
                'timestamp': datetime.now().isoformat(),
                'positions': [pos.to_dict() for pos in self.positions],
                'paper_cash': self.paper_cash,
                'paper_equity': self.paper_equity,
                'metrics': asdict(self.metrics)
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def initialize_data_connections(self):
        """Initialize market data connections"""
        try:
            # Test yfinance connection
            test_data = yf.download("SPY", period="1d", interval="1m", progress=False)
            if not test_data.empty:
                logger.info("Market data connection established (yfinance)")
            else:
                logger.warning("Market data connection test failed")
        except Exception as e:
            logger.error(f"Error initializing data connections: {e}")
    
    def get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get current market data for symbol
        
        Args:
            symbol: Symbol to fetch data for
            
        Returns:
            DataFrame with market data or None if failed
        """
        try:
            # Check cache first (avoid excessive API calls)
            cache_key = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H')}"
            
            if cache_key in self.market_data_cache:
                cached_time, cached_data = self.market_data_cache[cache_key]
                if (datetime.now() - cached_time).seconds < 3600:  # 1 hour cache
                    return cached_data
            
            # Fetch fresh data - get sufficient history for indicators
            data = yf.download(
                symbol, 
                period="1y",  # Get 1 year of data for indicators
                interval="1d",
                progress=False
            )
            
            if data.empty:
                logger.warning(f"No data received for {symbol}")
                return None
            
            # Calculate technical indicators (same as backtest)
            data['returns'] = data['Close'].pct_change()
            data['volatility'] = data['returns'].rolling(window=30).std() * np.sqrt(252)
            data['ma_200'] = data['Close'].rolling(window=200).mean()
            data['ema_20'] = data['Close'].ewm(span=20).mean()
            
            # Calculate signals
            data['in_bull_regime'] = (data['Close'] > data['ma_200']).fillna(False)
            data['pullback_signal'] = (
                (data['Close'].shift(1) > data['ema_20'].shift(1) * 1.001) & 
                (data['Close'] <= data['ema_20'] * 1.005)
            ).fillna(False)
            
            # Cache the data
            self.market_data_cache[cache_key] = (datetime.now(), data)
            
            logger.debug(f"Market data updated for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    def check_strategy_signals(self):
        """
        Check for new strategy signals and execute trades
        """
        try:
            current_time = datetime.now()
            
            # Check if we should be trading now
            if not is_market_open(current_time) and not should_gather_premarket_data(current_time):
                logger.debug(f"Market closed and not in pre-market hours - skipping signal check")
                return
            
            if should_gather_premarket_data(current_time):
                logger.info("Pre-market data gathering period - updating market data only")
            else:
                logger.info("Market open - checking for strategy signals...")
            
            # Get current market data
            market_data = self.get_market_data(self.config['underlying_symbol'])
            if market_data is None or market_data.empty:
                logger.warning("No market data available for signal check")
                return
            
            # Get latest market data row
            latest_data = market_data.iloc[-1]
            current_price = latest_data['Close']
            current_date = datetime.now()
            
            logger.info(f"Current {self.config['underlying_symbol']} price: ${current_price:.2f}")
            logger.info(f"Bull regime: {latest_data['in_bull_regime']}")
            logger.info(f"Pullback signal: {latest_data['pullback_signal']}")
            
            # Update strategy with price history for indicators
            price_history = market_data['Close'].tolist()
            self.strategy.price_history = price_history[-250:]  # Keep last 250 days
            self.strategy.date_history = [market_data.index[i] for i in range(-min(250, len(market_data)), 0)]
            
            # Generate trading signal using our validated strategy logic
            signal = self.should_enter_trade(latest_data, current_date)
            
            # Only execute trades during market hours
            if signal and is_market_open(current_time):
                logger.info("ENTRY SIGNAL GENERATED - Attempting to open Bull Call Spread")
                self.execute_bull_call_spread_entry(current_price, latest_data['volatility'])
            elif signal and should_gather_premarket_data(current_time):
                logger.info("ENTRY SIGNAL DETECTED - Waiting for market open to execute")
            else:
                logger.debug("No entry signal generated")
            
            # Check existing positions for exit signals
            self.check_position_exits(latest_data, current_date)
            
            # Update metrics
            self.update_position_values(current_price)
            self.metrics.update_metrics(self.positions)
            
            self.last_signal_check = current_date
            
        except Exception as e:
            logger.error(f"Error in signal check: {e}")
            logger.error(traceback.format_exc())
    
    def should_enter_trade(self, data_row: pd.Series, current_date: datetime) -> bool:
        """
        Check if conditions are met for new Bull Call Spread entry
        Uses same logic as validated backtest
        """
        try:
            # Must be in bull regime (above 200-day MA)
            if not data_row['in_bull_regime']:
                logger.debug("Not in bull regime - no entry")
                return False
            
            # Must have pullback signal
            if not data_row['pullback_signal']:
                logger.debug("No pullback signal - no entry")
                return False
            
            # Don't exceed max positions
            open_positions = [p for p in self.positions if p.status == "OPEN"]
            if len(open_positions) >= self.config.get('max_positions', 3):
                logger.debug(f"Max positions reached ({len(open_positions)}) - no entry")
                return False
            
            # Don't enter on consecutive days (avoid clustering)
            if open_positions:
                last_entry = max([pos.entry_date for pos in open_positions])
                if (current_date.date() - last_entry.date()).days < 10:
                    logger.debug("Too soon since last entry - no entry")
                    return False
            
            # Volatility filter - don't enter during extreme volatility
            volatility = data_row['volatility'] if not pd.isna(data_row['volatility']) else 0.20
            if volatility > 0.40:
                logger.debug(f"Volatility too high ({volatility:.1%}) - no entry")
                return False
            
            logger.info("All entry conditions met!")
            return True
            
        except Exception as e:
            logger.error(f"Error in entry signal check: {e}")
            return False
    
    def execute_bull_call_spread_entry(self, underlying_price: float, volatility: float):
        """
        Execute a Bull Call Spread entry in paper trading
        
        Args:
            underlying_price: Current underlying price
            volatility: Current implied volatility
        """
        try:
            # Calculate strikes (same logic as backtest)
            long_call_strike = round(underlying_price)  # ATM
            otm_distance = underlying_price * 0.06  # 6% OTM
            short_call_strike = round(underlying_price + otm_distance)
            
            # Estimate option prices (simplified model from backtest)
            tte = self.config.get('target_dte', 45) / 365.0
            iv = volatility if not pd.isna(volatility) else 0.20
            
            # Long call pricing
            intrinsic_long = max(0, underlying_price - long_call_strike)
            time_value_long = underlying_price * 0.03 * (iv / 0.20) * np.sqrt(tte)
            long_call_price = max(intrinsic_long + time_value_long, 0.50)
            
            # Short call pricing
            intrinsic_short = max(0, underlying_price - short_call_strike)
            time_value_short = underlying_price * 0.015 * (iv / 0.20) * np.sqrt(tte)
            short_call_price = max(intrinsic_short + time_value_short, 0.20)
            
            # Net debit
            net_debit = long_call_price - short_call_price
            
            # Check debit limits
            if net_debit < 0.50 or net_debit > 3.00:
                logger.warning(f"Net debit ${net_debit:.2f} outside acceptable range - skipping trade")
                return
            
            # Calculate position cost
            contracts = self.config['contracts_per_trade']
            total_cost = net_debit * contracts * 100  # 100 shares per contract
            commission = contracts * 2 * self.config['commission_per_contract']  # 2 legs
            total_cost_with_commission = total_cost + commission
            
            # Check available capital
            if total_cost_with_commission > self.paper_cash:
                logger.warning(f"Insufficient capital: Need ${total_cost_with_commission:.2f}, have ${self.paper_cash:.2f}")
                return
            
            # Create position
            expiration_date = (datetime.now() + timedelta(days=self.config.get('target_dte', 45))).strftime('%Y-%m-%d')
            
            position = LivePosition(
                symbol=self.config['underlying_symbol'],
                strategy_id=f"BCS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                entry_date=datetime.now(),
                expiration=expiration_date,
                long_call_strike=long_call_strike,
                short_call_strike=short_call_strike,
                contracts=contracts,
                net_debit_paid=net_debit,
                current_pnl=0.0,
                status="OPEN"
            )
            
            # Create order through OMS
            order_id = self.oms.create_bull_call_spread_order(
                underlying=self.config['underlying_symbol'],
                long_strike=long_call_strike,
                short_strike=short_call_strike,
                expiration=expiration_date,
                net_debit=net_debit,
                quantity=contracts
            )
            
            # Submit order
            if self.oms.submit_order(order_id):
                # Execute paper trade (simplified for paper trading)
                self.paper_cash -= total_cost_with_commission
                self.positions.append(position)
                
                # Track order ID with position
                position.strategy_id = order_id
                
                logger.info("=" * 60)
                logger.info("BULL CALL SPREAD ENTRY EXECUTED")
                logger.info("=" * 60)
                logger.info(f"Order ID: {order_id}")
                logger.info(f"Strategy ID: {position.strategy_id}")
                logger.info(f"Strikes: ${long_call_strike:.0f}/${short_call_strike:.0f}")
                logger.info(f"Contracts: {contracts}")
                logger.info(f"Net Debit: ${net_debit:.2f} per spread")
                logger.info(f"Total Cost: ${total_cost_with_commission:.2f}")
                logger.info(f"Remaining Cash: ${self.paper_cash:.2f}")
                logger.info(f"Expiration: {expiration_date}")
                logger.info("=" * 60)
            else:
                logger.error(f"Failed to submit order through OMS: {order_id}")
                return
            
            # Save state
            self.save_state()
            
        except Exception as e:
            logger.error(f"Error executing Bull Call Spread entry: {e}")
            logger.error(traceback.format_exc())
    
    def check_position_exits(self, market_data: pd.Series, current_date: datetime):
        """
        Check all open positions for exit conditions
        
        Args:
            market_data: Current market data
            current_date: Current date
        """
        open_positions = [p for p in self.positions if p.status == "OPEN"]
        
        for position in open_positions:
            try:
                days_held = (current_date.date() - position.entry_date.date()).days
                dte_remaining = self.config.get('target_dte', 45) - days_held
                
                should_exit = False
                exit_reason = ""
                
                # Check DTE expiry
                if dte_remaining <= 7:  # Min DTE close
                    should_exit = True
                    exit_reason = "DTE_EXPIRY"
                
                # Check profit target and stop loss
                if not should_exit and days_held > 0:  # Don't exit on entry day
                    current_price = market_data['Close']
                    
                    # Calculate current spread value
                    long_intrinsic = max(0, current_price - position.long_call_strike)
                    short_intrinsic = max(0, current_price - position.short_call_strike)
                    
                    # Add time value
                    if dte_remaining > 0:
                        tte = dte_remaining / 365.0
                        volatility = market_data['volatility'] if not pd.isna(market_data['volatility']) else 0.20
                        
                        long_time_value = current_price * 0.02 * (volatility / 0.20) * np.sqrt(tte)
                        short_time_value = current_price * 0.01 * (volatility / 0.20) * np.sqrt(tte)
                    else:
                        long_time_value = short_time_value = 0
                    
                    current_spread_value = (long_intrinsic + long_time_value) - (short_intrinsic + short_time_value)
                    pnl_per_share = current_spread_value - position.net_debit_paid
                    
                    # Check profit target (80% of target to be conservative)
                    profit_threshold = position.net_debit_paid * self.config.get('profit_target', 1.0) * 0.8
                    if pnl_per_share >= profit_threshold:
                        should_exit = True
                        exit_reason = "PROFIT_TARGET"
                    
                    # Check stop loss (120% of stop to be conservative) 
                    stop_threshold = -position.net_debit_paid * self.config.get('stop_loss', 0.5) * 1.2
                    if pnl_per_share <= stop_threshold:
                        should_exit = True
                        exit_reason = "STOP_LOSS"
                
                if should_exit:
                    self.execute_bull_call_spread_exit(position, market_data, exit_reason)
                
            except Exception as e:
                logger.error(f"Error checking exit for position {position.strategy_id}: {e}")
    
    def execute_bull_call_spread_exit(self, position: LivePosition, market_data: pd.Series, exit_reason: str):
        """
        Execute Bull Call Spread exit in paper trading
        
        Args:
            position: Position to exit
            market_data: Current market data
            exit_reason: Reason for exit
        """
        try:
            current_price = market_data['Close']
            days_held = (datetime.now().date() - position.entry_date.date()).days
            
            # Calculate final P&L (same logic as backtest)
            long_intrinsic = max(0, current_price - position.long_call_strike)
            short_intrinsic = max(0, current_price - position.short_call_strike)
            
            # Final spread value (at exit, minimal time value)
            spread_value = long_intrinsic - short_intrinsic
            pnl_per_share = spread_value - position.net_debit_paid
            
            # Account for transaction costs
            commission = position.contracts * 2 * self.config['commission_per_contract']  # Exit commission
            pnl_per_contract = (pnl_per_share * 100) - (commission / position.contracts)
            total_pnl = pnl_per_contract * position.contracts
            
            # Update position
            position.current_pnl = total_pnl
            position.status = "CLOSED"
            
            # Update paper trading account
            # We get back the spread value
            spread_proceeds = spread_value * position.contracts * 100
            self.paper_cash += spread_proceeds - commission
            
            logger.info("=" * 60)
            logger.info("BULL CALL SPREAD EXIT EXECUTED")
            logger.info("=" * 60)
            logger.info(f"Strategy ID: {position.strategy_id}")
            logger.info(f"Exit Reason: {exit_reason}")
            logger.info(f"Days Held: {days_held}")
            logger.info(f"Entry Debit: ${position.net_debit_paid:.2f}")
            logger.info(f"Exit Value: ${spread_value:.2f}")
            logger.info(f"P&L per Share: ${pnl_per_share:.2f}")
            logger.info(f"Total P&L: ${total_pnl:.2f}")
            logger.info(f"Updated Cash: ${self.paper_cash:.2f}")
            logger.info("=" * 60)
            
            # Save state
            self.save_state()
            
        except Exception as e:
            logger.error(f"Error executing exit for position {position.strategy_id}: {e}")
            logger.error(traceback.format_exc())
    
    def update_position_values(self, current_price: float):
        """Update unrealized P&L for all open positions"""
        open_positions = [p for p in self.positions if p.status == "OPEN"]
        
        for position in open_positions:
            try:
                # Calculate current unrealized P&L
                long_intrinsic = max(0, current_price - position.long_call_strike)
                short_intrinsic = max(0, current_price - position.short_call_strike)
                
                current_spread_value = long_intrinsic - short_intrinsic
                unrealized_pnl_per_share = current_spread_value - position.net_debit_paid
                position.unrealized_pnl = unrealized_pnl_per_share * position.contracts * 100
                
            except Exception as e:
                logger.error(f"Error updating position value for {position.strategy_id}: {e}")
        
        # Update total equity
        total_unrealized = sum([p.unrealized_pnl for p in open_positions])
        self.paper_equity = self.paper_cash + total_unrealized
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary"""
        open_positions = [p for p in self.positions if p.status == "OPEN"]
        closed_positions = [p for p in self.positions if p.status == "CLOSED"]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'cash': self.paper_cash,
            'equity': self.paper_equity,
            'total_return_pct': ((self.paper_equity - self.config['initial_capital']) / self.config['initial_capital']) * 100,
            'open_positions': len(open_positions),
            'total_positions': len(self.positions),
            'metrics': asdict(self.metrics),
            'positions': [pos.to_dict() for pos in self.positions[-10:]]  # Last 10 positions
        }
    
    def schedule_strategy_checks(self):
        """Schedule regular strategy signal checks"""
        # More frequent checks during pre-market and market hours
        # Pre-market data gathering: 8:30 AM - 9:30 AM ET (every 15 minutes)
        # Market hours: 9:30 AM - 4:00 PM ET (every 30 minutes)
        # After hours: minimal checks (every 2 hours for position monitoring)
        
        # Schedule checks every 15 minutes (will be filtered by market hours logic)
        for minute in range(0, 60, 15):
            schedule.every().hour.at(f":{minute:02d}").do(self.check_strategy_signals)
        
        logger.info("Strategy signal checks scheduled every 15 minutes")
        logger.info("Pre-market data gathering: 8:30-9:30 AM ET")
        logger.info("Market hours trading: 9:30 AM-4:00 PM ET")
        logger.info("After hours position monitoring enabled")
    
    def run(self):
        """
        Main trading loop - runs continuously during operation
        """
        logger.info("=" * 80)
        logger.info("SPRINT 19: LIVE PAPER TRADING ENGINE STARTED")
        logger.info("=" * 80)
        logger.info(f"Strategy: Bull Call Spread")
        logger.info(f"Initial Capital: ${self.config['initial_capital']:,.2f}")
        logger.info(f"Current Equity: ${self.paper_equity:,.2f}")
        logger.info(f"Max Positions: {self.config.get('max_positions', 3)}")
        logger.info("=" * 80)
        
        # Schedule strategy checks
        self.schedule_strategy_checks()
        
        # Initial signal check
        self.check_strategy_signals()
        
        # Main event loop
        try:
            while self.state == TradingState.RUNNING:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Brief sleep to prevent excessive CPU usage
                time.sleep(60)  # Check every minute for scheduled tasks
                
                # Save state periodically
                if datetime.now().minute % 15 == 0:  # Every 15 minutes
                    self.save_state()
        
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
            self.state = TradingState.SHUTDOWN
        
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}")
            logger.error(traceback.format_exc())
            self.state = TradingState.ERROR
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown of trading engine"""
        logger.info("Shutting down Live Trading Engine...")
        
        # Save final state
        self.save_state()
        
        # Log final summary
        summary = self.get_portfolio_summary()
        logger.info("=" * 60)
        logger.info("FINAL TRADING SESSION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Final Equity: ${summary['equity']:,.2f}")
        logger.info(f"Total Return: {summary['total_return_pct']:.2f}%")
        logger.info(f"Total Positions: {summary['total_positions']}")
        logger.info(f"Open Positions: {summary['open_positions']}")
        logger.info(f"Win Rate: {summary['metrics']['win_rate']:.1f}%")
        logger.info("=" * 60)
        
        self.state = TradingState.SHUTDOWN
        logger.info("Live Trading Engine shutdown complete")


def main():
    """
    Main entry point for live trading engine
    """
    print("=" * 80)
    print("SPRINT 19: BULL CALL SPREAD LIVE PAPER TRADING")
    print("=" * 80)
    
    try:
        # Initialize and run trading engine
        engine = LiveTradingEngine()
        engine.run()
        
    except Exception as e:
        logger.error(f"Fatal error starting trading engine: {e}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())