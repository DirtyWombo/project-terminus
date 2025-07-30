#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 18: Bull Call Spread Strategy Implementation
Simple directional options strategy for SPY backtesting

This module implements a Bull Call Spread strategy that profits from upward
price movements in SPY. The strategy uses regime filtering and technical
indicators to time entries during market uptrends.

Strategy Overview:
- Buy ATM call (long position)
- Sell OTM call (short position) 
- Profit from underlying price appreciation
- Limited risk and limited reward

Key Features:
- 200-day moving average regime filter
- 20-day EMA pullback entry trigger
- Systematic strike selection based on delta
- Risk management with profit targets and stop losses
- Integration with existing options backtesting infrastructure
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass, field
from enum import Enum

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from options_backtesting.core_engine import (
    OptionContract, OptionType, OptionPosition,
    OptionsBacktestEngine, MarketDataEvent, StrategyEvent, ExecutionEvent
)
from options_backtesting.historical_manager import HistoricalOptionsManager
from options_backtesting.greeks_engine import GreeksEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BullCallSpreadSignal(Enum):
    """Bull Call Spread trading signals"""
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    HOLD = "HOLD"

@dataclass
class BullCallSpreadParameters:
    """
    Bull Call Spread strategy parameters
    """
    # Strike selection
    target_dte: int = 45              # Target days to expiration
    long_call_delta: float = 0.50     # Delta for long call (ATM)
    short_call_delta: float = 0.30    # Delta for short call (OTM)
    
    # Entry criteria
    regime_filter_period: int = 200   # Moving average period for regime filter
    pullback_ema_period: int = 20     # EMA period for pullback detection
    min_net_debit: float = 0.50       # Minimum net debit paid
    max_net_debit: float = 3.00       # Maximum net debit paid
    
    # Data quality requirements
    max_bid_ask_spread: float = 0.15  # Maximum spread as % of mid price
    min_open_interest: int = 100      # Minimum open interest per leg
    min_volume: int = 10              # Minimum volume per leg
    
    # Risk management
    profit_target: float = 1.00       # Take profit at 100% of debit paid
    stop_loss: float = 0.50           # Stop loss at 50% of debit paid
    
    # Timing
    min_dte_close: int = 7            # Close position if DTE <= 7
    max_dte_open: int = 60            # Don't open if DTE > 60
    
    # Position management
    max_positions: int = 3            # Maximum concurrent positions
    position_size: float = 10000.0    # Dollar amount per position
    
    def __post_init__(self):
        """Validate parameters"""
        if self.long_call_delta <= 0 or self.long_call_delta >= 1.0:
            raise ValueError("Long call delta must be between 0 and 1")
        
        if self.short_call_delta <= 0 or self.short_call_delta >= 1.0:
            raise ValueError("Short call delta must be between 0 and 1")
        
        if self.short_call_delta >= self.long_call_delta:
            raise ValueError("Short call delta must be less than long call delta")

@dataclass
class BullCallSpreadPosition:
    """
    Bull Call Spread position representation
    """
    long_call: OptionPosition
    short_call: OptionPosition
    entry_date: datetime
    expiration: str
    underlying_price_at_entry: float
    net_debit_paid: float
    max_profit: float
    max_loss: float
    breakeven: float
    exit_date: Optional[datetime] = None
    exit_reason: Optional[str] = None
    
    @property
    def is_open(self) -> bool:
        """Check if spread is still open"""
        return self.exit_date is None
    
    @property
    def total_pnl(self) -> float:
        """Calculate current P&L of the spread"""
        if not self.is_open:
            # Closed position - use exit prices
            long_pnl = (self.long_call.exit_price - self.long_call.entry_price) * self.long_call.quantity * 100
            short_pnl = (self.short_call.exit_price - self.short_call.entry_price) * self.short_call.quantity * 100
        else:
            # Open position - use current prices
            long_current = self.long_call.contract.mid_price
            short_current = self.short_call.contract.mid_price
            
            long_pnl = (long_current - self.long_call.entry_price) * self.long_call.quantity * 100
            short_pnl = (short_current - self.short_call.entry_price) * self.short_call.quantity * 100
        
        return long_pnl + short_pnl
    
    @property
    def days_to_expiration(self) -> int:
        """Get days to expiration"""
        return self.long_call.contract.days_to_expiration

class BullCallSpreadStrategy:
    """
    Professional Bull Call Spread trading strategy
    """
    
    def __init__(self, parameters: BullCallSpreadParameters = None, 
                 data_manager: HistoricalOptionsManager = None,
                 greeks_engine: GreeksEngine = None):
        """
        Initialize Bull Call Spread strategy
        
        Args:
            parameters: Strategy parameters
            data_manager: Historical options data manager
            greeks_engine: Greeks calculation engine
        """
        self.params = parameters or BullCallSpreadParameters()
        self.data_manager = data_manager or HistoricalOptionsManager()
        self.greeks_engine = greeks_engine or GreeksEngine()
        
        # Strategy state
        self.active_positions: List[BullCallSpreadPosition] = []
        self.closed_positions: List[BullCallSpreadPosition] = []
        self.current_date: Optional[datetime] = None
        self.underlying_price: float = 0.0
        
        # Technical indicators
        self.price_history: List[float] = []
        self.date_history: List[datetime] = []
        
        # Performance tracking
        self.trades_opened = 0
        self.trades_closed = 0
        self.total_debit_paid = 0.0
        self.total_pnl = 0.0
        
        logger.info("Bull Call Spread strategy initialized")
        logger.info(f"Target DTE: {self.params.target_dte}")
        logger.info(f"Long call delta: {self.params.long_call_delta}")
        logger.info(f"Short call delta: {self.params.short_call_delta}")
        
    def generate_signal(self, date: datetime, options_chain: List[OptionContract], 
                       underlying_price: float) -> BullCallSpreadSignal:
        """
        Generate trading signal based on market conditions
        
        Args:
            date: Current date
            options_chain: Available options contracts
            underlying_price: Current underlying price
            
        Returns:
            Trading signal
        """
        self.current_date = date
        self.underlying_price = underlying_price
        
        # Update price history
        self.price_history.append(underlying_price)
        self.date_history.append(date)
        
        # Keep only last 250 days of history
        if len(self.price_history) > 250:
            self.price_history = self.price_history[-250:]
            self.date_history = self.date_history[-250:]
        
        if not options_chain:
            return BullCallSpreadSignal.HOLD
        
        # Update Greeks engine with current options data
        self.greeks_engine.update_volatility_surface(options_chain)
        
        # Check existing positions first
        if self.active_positions:
            for position in self.active_positions:
                if self._should_close_position(position, options_chain):
                    return BullCallSpreadSignal.CLOSE
        
        # Check for new entry opportunities
        if (len(self.active_positions) < self.params.max_positions and 
            self._should_open_new_position(options_chain)):
            return BullCallSpreadSignal.OPEN
        
        return BullCallSpreadSignal.HOLD
    
    def _should_open_new_position(self, options_chain: List[OptionContract]) -> bool:
        """Check if conditions are right for opening new Bull Call Spread"""
        
        # Need sufficient price history
        if len(self.price_history) < max(self.params.regime_filter_period, self.params.pullback_ema_period):
            return False
        
        # Regime filter: Only trade when above 200-day MA
        if not self._is_in_bull_regime():
            logger.debug("Not in bull regime - staying out")
            return False
        
        # Entry trigger: Price touches 20-day EMA after being above it
        if not self._is_pullback_entry_signal():
            logger.debug("No pullback entry signal")
            return False
        
        # Find suitable options for Bull Call Spread
        spread_strikes = self._find_bull_call_spread_strikes(options_chain)
        
        if not spread_strikes:
            logger.debug("No suitable strikes found")
            return False
        
        # Check net debit requirements
        estimated_debit = self._estimate_net_debit(spread_strikes, options_chain)
        
        if estimated_debit < self.params.min_net_debit or estimated_debit > self.params.max_net_debit:
            logger.debug(f"Debit outside range: ${estimated_debit:.2f}")
            return False
        
        # Check data quality requirements
        if not self._validate_data_quality(spread_strikes, options_chain):
            logger.debug("Data quality check failed")
            return False
        
        logger.info(f"Bull Call Spread entry conditions met - debit: ${estimated_debit:.2f}")
        return True
    
    def _should_close_position(self, position: BullCallSpreadPosition, 
                             options_chain: List[OptionContract]) -> bool:
        """Check if position should be closed"""
        
        # Close if approaching expiration
        if position.days_to_expiration <= self.params.min_dte_close:
            logger.info(f"Closing position due to DTE: {position.days_to_expiration}")
            return True
        
        # Update position prices
        self._update_position_prices(position, options_chain)
        
        # Check profit target
        current_pnl = position.total_pnl
        profit_target_amount = position.net_debit_paid * 100 * self.params.profit_target
        
        if current_pnl >= profit_target_amount:
            logger.info(f"Profit target reached: ${current_pnl:.2f} >= ${profit_target_amount:.2f}")
            return True
        
        # Check stop loss
        stop_loss_amount = -position.net_debit_paid * 100 * self.params.stop_loss
        
        if current_pnl <= stop_loss_amount:
            logger.info(f"Stop loss triggered: ${current_pnl:.2f} <= ${stop_loss_amount:.2f}")
            return True
        
        return False
    
    def _is_in_bull_regime(self) -> bool:
        """Check if market is in bullish regime using 200-day MA"""
        if len(self.price_history) < self.params.regime_filter_period:
            return False
        
        ma_200 = np.mean(self.price_history[-self.params.regime_filter_period:])
        current_price = self.price_history[-1]
        
        return current_price > ma_200
    
    def _is_pullback_entry_signal(self) -> bool:
        """Check for pullback to 20-day EMA entry signal"""
        if len(self.price_history) < self.params.pullback_ema_period + 5:
            return False
        
        # Calculate 20-day EMA
        prices = np.array(self.price_history[-self.params.pullback_ema_period-5:])
        alpha = 2.0 / (self.params.pullback_ema_period + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]
        
        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
        
        current_price = prices[-1]
        current_ema = ema[-1]
        prev_price = prices[-2]
        prev_ema = ema[-2]
        
        # Entry signal: Price was above EMA, now touching/below EMA
        # This indicates a pullback in an uptrend
        was_above_ema = prev_price > prev_ema * 1.001  # Small buffer
        now_at_ema = current_price <= current_ema * 1.005  # Small buffer
        
        return was_above_ema and now_at_ema
    
    def _find_bull_call_spread_strikes(self, options_chain: List[OptionContract]) -> Optional[Dict[str, Any]]:
        """
        Find suitable strikes for Bull Call Spread based on delta targets
        
        Args:
            options_chain: Available options contracts
            
        Returns:
            Dictionary with strike levels or None if not found
        """
        
        # Filter to target expiration
        target_contracts = []
        
        for contract in options_chain:
            dte_diff = abs(contract.days_to_expiration - self.params.target_dte)
            if dte_diff <= 7 and contract.option_type == OptionType.CALL:  # Within 7 days of target
                target_contracts.append(contract)
        
        if not target_contracts:
            return None
        
        # Find long call (target delta around 0.50 - ATM)
        long_call = self._find_closest_delta_option(target_contracts, self.params.long_call_delta)
        if not long_call:
            return None
        
        # Find short call (target delta around 0.30 - OTM)
        short_call = self._find_closest_delta_option(target_contracts, self.params.short_call_delta)
        if not short_call:
            return None
        
        # Verify short call strike is higher than long call strike
        if short_call.strike <= long_call.strike:
            return None
        
        return {
            'long_call_strike': long_call.strike,
            'short_call_strike': short_call.strike,
            'expiration': long_call.expiration,
            'days_to_expiration': long_call.days_to_expiration,
            'long_call_contract': long_call,
            'short_call_contract': short_call
        }
    
    def _find_closest_delta_option(self, contracts: List[OptionContract], 
                                 target_delta: float) -> Optional[OptionContract]:
        """Find option with delta closest to target"""
        best_contract = None
        best_delta_diff = float('inf')
        
        # If no contracts have meaningful delta, use moneyness as approximation
        contracts_with_delta = [c for c in contracts if abs(c.delta) > 0.01]
        
        if not contracts_with_delta:
            # Fallback to moneyness-based selection for calls
            if target_delta >= 0.4:  # ATM call
                valid_contracts = [c for c in contracts if 0.95 <= c.moneyness <= 1.05 and c.bid > 0]
            else:  # OTM call
                valid_contracts = [c for c in contracts if c.moneyness > 1.0 and c.bid > 0]
            
            if valid_contracts:
                target_moneyness = 1.0 + (0.5 - target_delta) * 0.4  # Rough approximation
                best_contract = min(valid_contracts, 
                                  key=lambda c: abs(c.moneyness - target_moneyness))
        else:
            # Use delta-based selection
            for contract in contracts_with_delta:
                delta_diff = abs(contract.delta - target_delta)
                if delta_diff < best_delta_diff:
                    best_delta_diff = delta_diff
                    best_contract = contract
        
        return best_contract
    
    def _estimate_net_debit(self, strikes: Dict[str, Any], 
                          options_chain: List[OptionContract]) -> float:
        """Estimate net debit that would be paid"""
        
        long_call = strikes['long_call_contract']
        short_call = strikes['short_call_contract']
        
        # Net debit = long call ask - short call bid
        net_debit = long_call.ask - short_call.bid
        
        return net_debit
    
    def _validate_data_quality(self, strikes: Dict[str, Any], 
                             options_chain: List[OptionContract]) -> bool:
        """Validate data quality for Bull Call Spread legs"""
        
        long_call = strikes['long_call_contract']
        short_call = strikes['short_call_contract']
        
        legs = [long_call, short_call]
        
        # Validate each leg
        for leg in legs:
            # Check bid-ask spread
            if leg.ask > 0 and leg.bid > 0:
                spread_pct = (leg.ask - leg.bid) / leg.mid_price if leg.mid_price > 0 else 1.0
                if spread_pct > self.params.max_bid_ask_spread:
                    logger.debug(f"Wide spread: {spread_pct:.2%} for {leg.symbol}")
                    return False
            
            # Check volume and open interest
            if leg.volume < self.params.min_volume:
                logger.debug(f"Low volume: {leg.volume} for {leg.symbol}")
                return False
                
            if leg.open_interest < self.params.min_open_interest:
                logger.debug(f"Low OI: {leg.open_interest} for {leg.symbol}")
                return False
        
        return True
    
    def _update_position_prices(self, position: BullCallSpreadPosition, 
                              options_chain: List[OptionContract]):
        """Update position prices with current market data"""
        
        for pos in [position.long_call, position.short_call]:
            # Find matching contract in current chain
            for contract in options_chain:
                if (contract.strike == pos.contract.strike and
                    contract.option_type == pos.contract.option_type and
                    contract.expiration == pos.contract.expiration):
                    
                    # Update prices
                    pos.contract.bid = contract.bid
                    pos.contract.ask = contract.ask
                    pos.contract.last = contract.last
                    pos.contract.mid_price = contract.mid_price
                    pos.contract.delta = contract.delta
                    pos.contract.gamma = contract.gamma
                    pos.contract.theta = contract.theta
                    pos.contract.vega = contract.vega
                    pos.contract.implied_volatility = contract.implied_volatility
                    pos.contract.days_to_expiration = contract.days_to_expiration
                    break
    
    def create_bull_call_spread_position(self, strikes: Dict[str, Any]) -> Optional[BullCallSpreadPosition]:
        """
        Create Bull Call Spread position from strike information
        
        Args:
            strikes: Strike levels dictionary
            
        Returns:
            BullCallSpreadPosition object or None if creation failed
        """
        try:
            long_call_contract = strikes['long_call_contract']
            short_call_contract = strikes['short_call_contract']
            
            # Create option positions
            long_call_pos = OptionPosition(
                contract=long_call_contract,
                quantity=1,   # Long position
                entry_price=long_call_contract.ask,
                entry_date=self.current_date
            )
            
            short_call_pos = OptionPosition(
                contract=short_call_contract,
                quantity=-1,  # Short position
                entry_price=short_call_contract.bid,
                entry_date=self.current_date
            )
            
            # Calculate strategy metrics
            net_debit = long_call_pos.entry_price - short_call_pos.entry_price
            strike_width = short_call_contract.strike - long_call_contract.strike
            
            max_profit = strike_width - net_debit  # Per share
            max_loss = net_debit  # Per share
            breakeven = long_call_contract.strike + net_debit
            
            # Create Bull Call Spread position
            bull_call_spread = BullCallSpreadPosition(
                long_call=long_call_pos,
                short_call=short_call_pos,
                entry_date=self.current_date,
                expiration=strikes['expiration'],
                underlying_price_at_entry=self.underlying_price,
                net_debit_paid=net_debit,
                max_profit=max_profit * 100,  # Per contract
                max_loss=max_loss * 100,      # Per contract
                breakeven=breakeven
            )
            
            logger.info(f"Created Bull Call Spread: ${long_call_contract.strike:.0f}/${short_call_contract.strike:.0f}")
            logger.info(f"Net debit: ${net_debit:.2f}, Max profit: ${max_profit * 100:.0f}, Max loss: ${max_loss * 100:.0f}")
            logger.info(f"Breakeven: ${breakeven:.2f}")
            
            self.trades_opened += 1
            self.total_debit_paid += net_debit * 100
            
            return bull_call_spread
            
        except Exception as e:
            logger.error(f"Failed to create Bull Call Spread position: {e}")
            return None
    
    def close_position(self, position: BullCallSpreadPosition, 
                      options_chain: List[OptionContract], reason: str = "Manual"):
        """Close a Bull Call Spread position"""
        
        try:
            # Update prices one more time
            self._update_position_prices(position, options_chain)
            
            # Set exit prices and date
            position.long_call.exit_price = position.long_call.contract.bid
            position.short_call.exit_price = position.short_call.contract.ask
            position.long_call.exit_date = self.current_date
            position.short_call.exit_date = self.current_date
            position.exit_date = self.current_date
            position.exit_reason = reason
            
            # Calculate final P&L
            final_pnl = position.total_pnl
            self.total_pnl += final_pnl
            self.trades_closed += 1
            
            # Move to closed positions
            if position in self.active_positions:
                self.active_positions.remove(position)
            self.closed_positions.append(position)
            
            logger.info(f"Closed Bull Call Spread - P&L: ${final_pnl:.2f}, Reason: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get comprehensive strategy performance metrics"""
        
        total_trades = len(self.closed_positions)
        winning_trades = len([p for p in self.closed_positions if p.total_pnl > 0])
        
        if total_trades == 0:
            return {
                'total_trades': 0,
                'active_positions': len(self.active_positions),
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_trade_pnl': 0.0,
                'profit_factor': 0.0,
                'gross_profit': 0.0,
                'gross_loss': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'total_debit_paid': self.total_debit_paid,
                'return_on_risk': 0.0
            }
        
        win_rate = winning_trades / total_trades * 100
        
        trade_pnls = [p.total_pnl for p in self.closed_positions]
        total_pnl = sum(trade_pnls)
        avg_trade_pnl = total_pnl / total_trades
        
        # Calculate profit factor
        gross_profit = sum([pnl for pnl in trade_pnls if pnl > 0])
        gross_loss = abs(sum([pnl for pnl in trade_pnls if pnl < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Return on risk (total P&L / total premium at risk)
        return_on_risk = (total_pnl / self.total_debit_paid) * 100 if self.total_debit_paid > 0 else 0
        
        return {
            'total_trades': total_trades,
            'active_positions': len(self.active_positions),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_trade_pnl': avg_trade_pnl,
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'best_trade': max(trade_pnls) if trade_pnls else 0,
            'worst_trade': min(trade_pnls) if trade_pnls else 0,
            'total_debit_paid': self.total_debit_paid,
            'return_on_risk': return_on_risk
        }


def main():
    """
    Test the Bull Call Spread strategy
    """
    print("=" * 80)
    print("SPRINT 18: BULL CALL SPREAD STRATEGY TEST")
    print("=" * 80)
    
    # Initialize strategy with default parameters
    params = BullCallSpreadParameters(
        target_dte=45,
        long_call_delta=0.50,
        short_call_delta=0.30,
        profit_target=1.00,
        stop_loss=0.50
    )
    
    strategy = BullCallSpreadStrategy(parameters=params)
    
    print(f"Strategy Parameters:")
    print(f"  Target DTE: {params.target_dte}")
    print(f"  Long Call Delta: {params.long_call_delta}")
    print(f"  Short Call Delta: {params.short_call_delta}")
    print(f"  Profit Target: {params.profit_target:.0%}")
    print(f"  Stop Loss: {params.stop_loss:.0%}")
    print(f"  Regime Filter: {params.regime_filter_period}-day MA")
    print(f"  Entry Trigger: {params.pullback_ema_period}-day EMA pullback")
    
    # Test performance metrics (empty for now)
    performance = strategy.get_strategy_performance()
    print(f"\nStrategy Performance:")
    for key, value in performance.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print("\nBull Call Spread Strategy test completed [SUCCESS]")


if __name__ == "__main__":
    main()