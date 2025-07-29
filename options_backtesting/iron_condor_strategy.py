#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 16: Short Iron Condor Strategy Implementation
Advanced volatility trading strategy for SPY options backtesting

This module implements a comprehensive Short Iron Condor strategy optimized for
SPY volatility trading. Built for systematic backtesting with professional-grade
risk management and Greeks monitoring.

Strategy Overview:
- Sell OTM call and put (collect premium)
- Buy further OTM call and put (limit risk)
- Profit from time decay and low volatility
- Delta-neutral strategy with defined risk/reward

Key Features:
- Automated strike selection based on delta/moneyness
- Dynamic position sizing and risk management
- Greeks-based adjustment triggers
- Integration with historical options data
- Performance analytics and reporting
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
    OptionContract, OptionType, OptionPosition, IronCondorPosition,
    OptionsBacktestEngine, MarketDataEvent, StrategyEvent, ExecutionEvent
)
from options_backtesting.historical_manager import HistoricalOptionsManager
from options_backtesting.greeks_engine import GreeksEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IronCondorSignal(Enum):
    """Iron Condor trading signals"""
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    ADJUST = "ADJUST"
    HOLD = "HOLD"

@dataclass
class IronCondorParameters:
    """
    Iron Condor strategy parameters
    """
    # Strike selection
    target_dte: int = 30              # Target days to expiration
    delta_short_call: float = 0.15    # Delta for short call
    delta_short_put: float = -0.15    # Delta for short put
    wing_width: float = 10.0          # Width between short and long strikes
    
    # Entry criteria
    min_premium_collected: float = 0.30  # Minimum net credit (as % of wing width)
    max_bid_ask_spread: float = 0.15     # Maximum spread as % of mid price
    min_open_interest: int = 100         # Minimum open interest per leg
    min_volume: int = 10                 # Minimum volume per leg
    
    # Risk management
    profit_target: float = 0.50          # Take profit at 50% of max profit
    stop_loss: float = 2.0               # Stop loss at 200% of premium collected
    max_loss_pct: float = 0.10           # Max loss as % of wing width
    
    # Greeks limits
    max_delta: float = 10.0              # Maximum portfolio delta
    max_gamma: float = 50.0              # Maximum gamma exposure
    max_vega: float = 100.0              # Maximum vega exposure
    
    # Timing
    min_dte_close: int = 7               # Close position if DTE <= 7
    max_dte_open: int = 45               # Don't open if DTE > 45
    
    # Position management
    max_positions: int = 5               # Maximum concurrent positions
    position_size: float = 10000.0       # Dollar amount per position
    
    def __post_init__(self):
        """Validate parameters"""
        if self.delta_short_call <= 0 or self.delta_short_call >= 0.5:
            raise ValueError("Short call delta must be between 0 and 0.5")
        
        if self.delta_short_put >= 0 or self.delta_short_put <= -0.5:
            raise ValueError("Short put delta must be between -0.5 and 0")
        
        if self.wing_width <= 0:
            raise ValueError("Wing width must be positive")

class IronCondorStrategy:
    """
    Professional Short Iron Condor trading strategy
    """
    
    def __init__(self, parameters: IronCondorParameters = None, 
                 data_manager: HistoricalOptionsManager = None,
                 greeks_engine: GreeksEngine = None):
        """
        Initialize Iron Condor strategy
        
        Args:
            parameters: Strategy parameters
            data_manager: Historical options data manager
            greeks_engine: Greeks calculation engine
        """
        self.params = parameters or IronCondorParameters()
        self.data_manager = data_manager or HistoricalOptionsManager()
        self.greeks_engine = greeks_engine or GreeksEngine()
        
        # Strategy state
        self.active_positions: List[IronCondorPosition] = []
        self.closed_positions: List[IronCondorPosition] = []
        self.current_date: Optional[datetime] = None
        self.underlying_price: float = 0.0
        
        # Performance tracking
        self.trades_opened = 0
        self.trades_closed = 0
        self.total_premium_collected = 0.0
        self.total_pnl = 0.0
        
        logger.info("Iron Condor strategy initialized")
        logger.info(f"Target DTE: {self.params.target_dte}")
        logger.info(f"Short deltas: Call {self.params.delta_short_call}, Put {self.params.delta_short_put}")
        logger.info(f"Wing width: ${self.params.wing_width}")
        
    def generate_signal(self, date: datetime, options_chain: List[OptionContract]) -> IronCondorSignal:
        """
        Generate trading signal based on market conditions
        
        Args:
            date: Current date
            options_chain: Available options contracts
            
        Returns:
            Trading signal
        """
        self.current_date = date
        
        if not options_chain:
            return IronCondorSignal.HOLD
        
        # Update underlying price
        self.underlying_price = options_chain[0].underlying_price
        
        # Update Greeks engine with current options data
        self.greeks_engine.update_volatility_surface(options_chain)
        
        # Check existing positions first
        if self.active_positions:
            # Check for close/adjust signals
            for position in self.active_positions:
                if self._should_close_position(position, options_chain):
                    return IronCondorSignal.CLOSE
                elif self._should_adjust_position(position, options_chain):
                    return IronCondorSignal.ADJUST
        
        # Check for new entry opportunities
        if (len(self.active_positions) < self.params.max_positions and 
            self._should_open_new_position(options_chain)):
            return IronCondorSignal.OPEN
        
        return IronCondorSignal.HOLD
    
    def _should_open_new_position(self, options_chain: List[OptionContract]) -> bool:
        """Check if conditions are right for opening new Iron Condor"""
        
        # Find suitable options for Iron Condor
        condor_strikes = self._find_iron_condor_strikes(options_chain)
        
        if not condor_strikes:
            return False
        
        # Check minimum premium requirement
        estimated_premium = self._estimate_premium_collected(condor_strikes, options_chain)
        min_premium = self.params.min_premium_collected * self.params.wing_width
        
        if estimated_premium < min_premium:
            logger.debug(f"Premium too low: ${estimated_premium:.2f} < ${min_premium:.2f}")
            return False
        
        # Check data quality requirements
        if not self._validate_data_quality(condor_strikes, options_chain):
            return False
        
        return True
    
    def _should_close_position(self, position: IronCondorPosition, 
                             options_chain: List[OptionContract]) -> bool:
        """Check if position should be closed"""
        
        # Close if approaching expiration
        if position.short_call.contract.days_to_expiration <= self.params.min_dte_close:
            logger.info(f"Closing position due to DTE: {position.short_call.contract.days_to_expiration}")
            return True
        
        # Update position prices
        self._update_position_prices(position, options_chain)
        
        # Check profit target
        current_pnl = position.total_pnl
        max_profit = position.max_profit
        
        if current_pnl >= max_profit * self.params.profit_target:
            logger.info(f"Profit target reached: ${current_pnl:.2f} >= ${max_profit * self.params.profit_target:.2f}")
            return True
        
        # Check stop loss
        premium_collected = position.net_premium_collected
        stop_loss_threshold = -premium_collected * self.params.stop_loss
        
        if current_pnl <= stop_loss_threshold:
            logger.info(f"Stop loss triggered: ${current_pnl:.2f} <= ${stop_loss_threshold:.2f}")
            return True
        
        return False
    
    def _should_adjust_position(self, position: IronCondorPosition, 
                              options_chain: List[OptionContract]) -> bool:
        """Check if position needs adjustment"""
        
        # Calculate current portfolio Greeks
        portfolio_positions = [
            {'contract': pos.contract, 'quantity': pos.quantity}
            for ic_pos in self.active_positions
            for pos in [ic_pos.short_call, ic_pos.long_call, ic_pos.short_put, ic_pos.long_put]
        ]
        
        portfolio_greeks = self.greeks_engine.calculate_portfolio_greeks(
            portfolio_positions, self.underlying_price
        )
        
        # Check Greeks limits
        if abs(portfolio_greeks['portfolio_delta']) > self.params.max_delta:
            logger.info(f"Delta adjustment needed: {portfolio_greeks['portfolio_delta']:.2f}")
            return True
        
        if abs(portfolio_greeks['portfolio_gamma']) > self.params.max_gamma:
            logger.info(f"Gamma adjustment needed: {portfolio_greeks['portfolio_gamma']:.2f}")
            return True
        
        return False
    
    def _find_iron_condor_strikes(self, options_chain: List[OptionContract]) -> Optional[Dict[str, float]]:
        """
        Find suitable strikes for Iron Condor based on delta targets
        
        Args:
            options_chain: Available options contracts
            
        Returns:
            Dictionary with strike levels or None if not found
        """
        
        # Filter to target expiration
        target_contracts = []
        
        for contract in options_chain:
            dte_diff = abs(contract.days_to_expiration - self.params.target_dte)
            if dte_diff <= 7:  # Within 7 days of target
                target_contracts.append(contract)
        
        if not target_contracts:
            return None
        
        # Separate calls and puts
        calls = [c for c in target_contracts if c.option_type == OptionType.CALL]
        puts = [c for c in target_contracts if c.option_type == OptionType.PUT]
        
        if not calls or not puts:
            return None
        
        # Find short call (target delta around 0.15)
        short_call = self._find_closest_delta_option(calls, self.params.delta_short_call)
        if not short_call:
            return None
        
        # Find short put (target delta around -0.15)
        short_put = self._find_closest_delta_option(puts, self.params.delta_short_put)
        if not short_put:
            return None
        
        # Calculate long strikes
        long_call_strike = short_call.strike + self.params.wing_width
        long_put_strike = short_put.strike - self.params.wing_width
        
        # Verify long options exist
        long_call = self._find_option_by_strike(calls, long_call_strike)
        long_put = self._find_option_by_strike(puts, long_put_strike)
        
        if not long_call or not long_put:
            return None
        
        return {
            'short_call_strike': short_call.strike,
            'long_call_strike': long_call.strike,
            'short_put_strike': short_put.strike,
            'long_put_strike': long_put.strike,
            'expiration': short_call.expiration,
            'days_to_expiration': short_call.days_to_expiration
        }
    
    def _find_closest_delta_option(self, contracts: List[OptionContract], 
                                 target_delta: float) -> Optional[OptionContract]:
        """Find option with delta closest to target"""
        best_contract = None
        best_delta_diff = float('inf')
        
        # If no contracts have meaningful delta, use moneyness as approximation
        contracts_with_delta = [c for c in contracts if abs(c.delta) > 0.01]
        
        if not contracts_with_delta:
            # Fallback to moneyness-based selection
            if target_delta > 0:  # Call option - want OTM (moneyness > 1)
                valid_contracts = [c for c in contracts if c.moneyness > 1.0 and c.bid > 0]
                if valid_contracts:
                    # Pick contract with moneyness closest to desired level
                    target_moneyness = 1.0 + abs(target_delta) * 0.5  # Rough approximation
                    best_contract = min(valid_contracts, 
                                      key=lambda c: abs(c.moneyness - target_moneyness))
            else:  # Put option - want OTM (moneyness < 1)
                valid_contracts = [c for c in contracts if c.moneyness < 1.0 and c.bid > 0]
                if valid_contracts:
                    # Pick contract with moneyness closest to desired level
                    target_moneyness = 1.0 - abs(target_delta) * 0.5  # Rough approximation
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
    
    def _find_option_by_strike(self, contracts: List[OptionContract], 
                             target_strike: float) -> Optional[OptionContract]:
        """Find option contract by strike price"""
        for contract in contracts:
            if abs(contract.strike - target_strike) < 0.01:  # Allow small rounding errors
                return contract
        return None
    
    def _estimate_premium_collected(self, strikes: Dict[str, float], 
                                  options_chain: List[OptionContract]) -> float:
        """Estimate net premium that would be collected"""
        
        # Find contracts for each leg
        short_call = self._find_option_by_strike(
            [c for c in options_chain if c.option_type == OptionType.CALL],
            strikes['short_call_strike']
        )
        
        short_put = self._find_option_by_strike(
            [c for c in options_chain if c.option_type == OptionType.PUT],
            strikes['short_put_strike']
        )
        
        long_call = self._find_option_by_strike(
            [c for c in options_chain if c.option_type == OptionType.CALL],
            strikes['long_call_strike']
        )
        
        long_put = self._find_option_by_strike(
            [c for c in options_chain if c.option_type == OptionType.PUT],
            strikes['long_put_strike']
        )
        
        if not all([short_call, short_put, long_call, long_put]):
            return 0.0
        
        # Calculate net credit (sell short options, buy long options)
        net_credit = (short_call.bid + short_put.bid - long_call.ask - long_put.ask)
        
        return net_credit
    
    def _validate_data_quality(self, strikes: Dict[str, float], 
                             options_chain: List[OptionContract]) -> bool:
        """Validate data quality for Iron Condor legs"""
        
        # Find all leg contracts
        legs = []
        
        for option_type, strike_key in [(OptionType.CALL, 'short_call_strike'),
                                       (OptionType.CALL, 'long_call_strike'),
                                       (OptionType.PUT, 'short_put_strike'),
                                       (OptionType.PUT, 'long_put_strike')]:
            
            contracts = [c for c in options_chain if c.option_type == option_type]
            leg = self._find_option_by_strike(contracts, strikes[strike_key])
            
            if not leg:
                return False
            
            legs.append(leg)
        
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
    
    def _update_position_prices(self, position: IronCondorPosition, 
                              options_chain: List[OptionContract]):
        """Update position prices with current market data"""
        
        for pos in [position.short_call, position.long_call, position.short_put, position.long_put]:
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
                    break
    
    def create_iron_condor_position(self, strikes: Dict[str, float], 
                                  options_chain: List[OptionContract]) -> Optional[IronCondorPosition]:
        """
        Create Iron Condor position from strike information
        
        Args:
            strikes: Strike levels dictionary
            options_chain: Available options contracts
            
        Returns:
            IronCondorPosition object or None if creation failed
        """
        try:
            # Find all leg contracts
            calls = [c for c in options_chain if c.option_type == OptionType.CALL]
            puts = [c for c in options_chain if c.option_type == OptionType.PUT]
            
            short_call_contract = self._find_option_by_strike(calls, strikes['short_call_strike'])
            long_call_contract = self._find_option_by_strike(calls, strikes['long_call_strike'])
            short_put_contract = self._find_option_by_strike(puts, strikes['short_put_strike'])
            long_put_contract = self._find_option_by_strike(puts, strikes['long_put_strike'])
            
            if not all([short_call_contract, long_call_contract, short_put_contract, long_put_contract]):
                logger.error("Could not find all required option contracts")
                return None
            
            # Create option positions
            short_call_pos = OptionPosition(
                contract=short_call_contract,
                quantity=-1,  # Short position
                entry_price=short_call_contract.bid,
                entry_date=self.current_date
            )
            
            long_call_pos = OptionPosition(
                contract=long_call_contract,
                quantity=1,   # Long position
                entry_price=long_call_contract.ask,
                entry_date=self.current_date
            )
            
            short_put_pos = OptionPosition(
                contract=short_put_contract,
                quantity=-1,  # Short position
                entry_price=short_put_contract.bid,
                entry_date=self.current_date
            )
            
            long_put_pos = OptionPosition(
                contract=long_put_contract,
                quantity=1,   # Long position
                entry_price=long_put_contract.ask,
                entry_date=self.current_date
            )
            
            # Calculate strategy metrics
            net_credit = (short_call_pos.entry_price + short_put_pos.entry_price - 
                         long_call_pos.entry_price - long_put_pos.entry_price)
            
            max_profit = net_credit * 100  # Per contract
            max_loss = (self.params.wing_width - net_credit) * 100
            
            breakeven_upper = strikes['short_call_strike'] + net_credit
            breakeven_lower = strikes['short_put_strike'] - net_credit
            
            # Create Iron Condor position
            iron_condor = IronCondorPosition(
                short_call=short_call_pos,
                long_call=long_call_pos,
                short_put=short_put_pos,
                long_put=long_put_pos,
                entry_date=self.current_date,
                expiration=strikes['expiration'],
                underlying_price_at_entry=self.underlying_price,
                wing_width=self.params.wing_width,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_upper=breakeven_upper,
                breakeven_lower=breakeven_lower
            )
            
            logger.info(f"Created Iron Condor: ${strikes['short_put_strike']:.0f}/${strikes['short_call_strike']:.0f} "
                       f"short, ${strikes['long_put_strike']:.0f}/${strikes['long_call_strike']:.0f} long")
            logger.info(f"Net credit: ${net_credit:.2f}, Max profit: ${max_profit:.0f}, Max loss: ${max_loss:.0f}")
            
            return iron_condor
            
        except Exception as e:
            logger.error(f"Failed to create Iron Condor position: {e}")
            return None
    
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
                'total_premium_collected': self.total_premium_collected
            }
        
        win_rate = winning_trades / total_trades * 100
        
        trade_pnls = [p.total_pnl for p in self.closed_positions]
        total_pnl = sum(trade_pnls)
        avg_trade_pnl = total_pnl / total_trades
        
        # Calculate profit factor
        gross_profit = sum([pnl for pnl in trade_pnls if pnl > 0])
        gross_loss = abs(sum([pnl for pnl in trade_pnls if pnl < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
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
            'total_premium_collected': self.total_premium_collected
        }


def main():
    """
    Test the Iron Condor strategy
    """
    print("=" * 80)
    print("SPRINT 16: IRON CONDOR STRATEGY TEST")
    print("=" * 80)
    
    # Initialize strategy with default parameters
    params = IronCondorParameters(
        target_dte=30,
        delta_short_call=0.15,
        delta_short_put=-0.15,
        wing_width=10.0,
        profit_target=0.50,
        stop_loss=2.0
    )
    
    strategy = IronCondorStrategy(parameters=params)
    
    print(f"Strategy Parameters:")
    print(f"  Target DTE: {params.target_dte}")
    print(f"  Short Call Delta: {params.delta_short_call}")
    print(f"  Short Put Delta: {params.delta_short_put}")
    print(f"  Wing Width: ${params.wing_width}")
    print(f"  Profit Target: {params.profit_target:.0%}")
    print(f"  Stop Loss: {params.stop_loss:.0%}")
    
    # Test with current options data
    print(f"\nTesting with current SPY options data...")
    
    current_date = datetime.now()
    options_chain = strategy.data_manager.get_options_chain('SPY', current_date.strftime('%Y-%m-%d'))
    
    if options_chain:
        print(f"Retrieved {len(options_chain)} option contracts")
        
        # Generate signal
        signal = strategy.generate_signal(current_date, options_chain)
        print(f"Generated signal: {signal.value}")
        
        # Test Iron Condor strike finding
        strikes = strategy._find_iron_condor_strikes(options_chain)
        if strikes:
            print(f"\nIron Condor strikes found:")
            print(f"  Short Put: ${strikes['short_put_strike']:.0f}")
            print(f"  Long Put: ${strikes['long_put_strike']:.0f}")
            print(f"  Short Call: ${strikes['short_call_strike']:.0f}")
            print(f"  Long Call: ${strikes['long_call_strike']:.0f}")
            print(f"  Expiration: {strikes['expiration']}")
            print(f"  DTE: {strikes['days_to_expiration']}")
            
            # Estimate premium
            premium = strategy._estimate_premium_collected(strikes, options_chain)
            print(f"  Estimated Net Credit: ${premium:.2f}")
        else:
            print("No suitable Iron Condor strikes found")
        
        # Test performance metrics (empty for now)
        performance = strategy.get_strategy_performance()
        print(f"\nStrategy Performance:")
        for key, value in performance.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    else:
        print("No options data available for testing")
    
    print("\nIron Condor Strategy test completed [SUCCESS]")


if __name__ == "__main__":
    main()