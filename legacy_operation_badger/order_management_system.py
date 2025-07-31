#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 19: Order Management System for Multi-Leg Options Trading
Professional-grade order management for Bull Call Spread execution

This module handles all order routing, execution, and management for multi-leg
options strategies. Built for paper trading validation with real broker
integration capabilities.

Key Features:
- Multi-leg options order construction
- Order lifecycle management
- Fill simulation and validation
- Error handling and recovery
- Real-time order status tracking
- Integration with live trading engine
"""

import os
import json
import time
import uuid
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import traceback

# Configure logging
logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderSide(Enum):
    """Order sides"""
    BUY = "BUY"
    SELL = "SELL"
    BUY_TO_OPEN = "BUY_TO_OPEN"
    SELL_TO_OPEN = "SELL_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class InstrumentType(Enum):
    """Instrument types"""
    STOCK = "STOCK"
    OPTION = "OPTION"
    SPREAD = "SPREAD"

@dataclass
class OptionContract:
    """Option contract specification"""
    symbol: str
    underlying: str
    strike: float
    expiration: str
    option_type: str  # "CALL" or "PUT"
    multiplier: int = 100
    
    def get_option_symbol(self) -> str:
        """Generate standard option symbol"""
        # Format: UNDERLYING + YYMMDD + C/P + STRIKE
        exp_date = datetime.strptime(self.expiration, '%Y-%m-%d')
        exp_str = exp_date.strftime('%y%m%d')
        strike_str = f"{int(self.strike * 1000):08d}"
        return f"{self.underlying}{exp_str}{self.option_type[0]}{strike_str}"

@dataclass
class OrderLeg:
    """Individual leg of a multi-leg order"""
    instrument_type: InstrumentType
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.LIMIT
    limit_price: Optional[float] = None
    option_contract: Optional[OptionContract] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        data = {
            'instrument_type': self.instrument_type.value,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'order_type': self.order_type.value
        }
        
        if self.limit_price is not None:
            data['limit_price'] = self.limit_price
            
        if self.option_contract:
            data['option_contract'] = asdict(self.option_contract)
            
        return data

@dataclass
class MultiLegOrder:
    """Multi-leg order representation"""
    order_id: str
    strategy_type: str
    legs: List[OrderLeg]
    net_debit_credit: float
    order_type: OrderType = OrderType.LIMIT
    time_in_force: str = "DAY"
    quantity: int = 1  # Number of spreads
    status: OrderStatus = OrderStatus.PENDING
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    fill_price: Optional[float] = None
    commission: float = 0.0
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['legs'] = [leg.to_dict() for leg in self.legs]
        if self.submitted_at:
            data['submitted_at'] = self.submitted_at.isoformat()
        if self.filled_at:
            data['filled_at'] = self.filled_at.isoformat()
        return data

class OrderManagementSystem:
    """
    Professional Order Management System for multi-leg options trading
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Order Management System
        
        Args:
            config: OMS configuration dictionary
        """
        self.config = config or self.get_default_config()
        
        # Order tracking
        self.active_orders: Dict[str, MultiLegOrder] = {}
        self.completed_orders: Dict[str, MultiLegOrder] = {}
        self.order_history: List[MultiLegOrder] = []
        
        # Paper trading simulation
        self.paper_trading = self.config.get('paper_trading', True)
        self.fill_delay_seconds = self.config.get('fill_delay_seconds', 5)
        self.rejection_rate = self.config.get('rejection_rate', 0.02)  # 2% rejection rate
        
        # Thread pool for order processing
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="OMS")
        
        # State persistence
        self.state_file = "oms_state.json"
        self.load_state()
        
        logger.info("Order Management System initialized")
        logger.info(f"Paper trading mode: {self.paper_trading}")
        logger.info(f"Fill delay: {self.fill_delay_seconds}s")
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default OMS configuration"""
        return {
            'paper_trading': True,
            'fill_delay_seconds': 5,
            'rejection_rate': 0.02,
            'max_order_value': 50000.0,
            'commission_per_contract': 0.65,
            'enable_partial_fills': True,
            'market_hours_only': True,
            'max_spread_width': 20.0
        }
    
    def load_state(self):
        """Load persistent OMS state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore orders
                for order_data in state_data.get('orders', []):
                    order = self.dict_to_order(order_data)
                    if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]:
                        self.active_orders[order.order_id] = order
                    else:
                        self.completed_orders[order.order_id] = order
                    self.order_history.append(order)
                
                logger.info(f"OMS state loaded: {len(self.active_orders)} active, {len(self.completed_orders)} completed orders")
        except Exception as e:
            logger.warning(f"Could not load OMS state: {e}")
    
    def save_state(self):
        """Save current OMS state"""
        try:
            state_data = {
                'timestamp': datetime.now().isoformat(),
                'orders': [order.to_dict() for order in self.order_history]
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving OMS state: {e}")
    
    def dict_to_order(self, order_data: Dict[str, Any]) -> MultiLegOrder:
        """Convert dictionary back to MultiLegOrder"""
        # Convert leg dictionaries back to OrderLeg objects
        legs = []
        for leg_data in order_data['legs']:
            option_contract = None
            if leg_data.get('option_contract'):
                option_contract = OptionContract(**leg_data['option_contract'])
            
            leg = OrderLeg(
                instrument_type=InstrumentType(leg_data['instrument_type']),
                symbol=leg_data['symbol'],
                side=OrderSide(leg_data['side']),
                quantity=leg_data['quantity'],
                order_type=OrderType(leg_data['order_type']),
                limit_price=leg_data.get('limit_price'),
                option_contract=option_contract
            )
            legs.append(leg)
        
        # Create order
        order = MultiLegOrder(
            order_id=order_data['order_id'],
            strategy_type=order_data['strategy_type'],
            legs=legs,
            net_debit_credit=order_data['net_debit_credit'],
            order_type=OrderType(order_data['order_type']),
            time_in_force=order_data['time_in_force'],
            quantity=order_data['quantity'],
            status=OrderStatus(order_data['status']),
            fill_price=order_data.get('fill_price'),
            commission=order_data.get('commission', 0.0),
            notes=order_data.get('notes', '')
        )
        
        # Parse dates
        if order_data.get('submitted_at'):
            order.submitted_at = datetime.fromisoformat(order_data['submitted_at'])
        if order_data.get('filled_at'):
            order.filled_at = datetime.fromisoformat(order_data['filled_at'])
        
        return order
    
    def create_bull_call_spread_order(self, underlying: str, long_strike: float, 
                                    short_strike: float, expiration: str, 
                                    net_debit: float, quantity: int = 1) -> str:
        """
        Create a Bull Call Spread order
        
        Args:
            underlying: Underlying symbol (e.g., "SPY")
            long_strike: Strike price of long call
            short_strike: Strike price of short call
            expiration: Expiration date (YYYY-MM-DD)
            net_debit: Net debit to pay for the spread
            quantity: Number of spreads to trade
            
        Returns:
            Order ID for tracking
        """
        try:
            # Generate unique order ID
            order_id = f"BCS_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create option contracts
            long_call = OptionContract(
                symbol=f"{underlying}_CALL_{long_strike}_{expiration}",
                underlying=underlying,
                strike=long_strike,
                expiration=expiration,
                option_type="CALL"
            )
            
            short_call = OptionContract(
                symbol=f"{underlying}_CALL_{short_strike}_{expiration}",
                underlying=underlying,
                strike=short_strike,
                expiration=expiration,
                option_type="CALL"
            )
            
            # Create order legs
            legs = [
                OrderLeg(
                    instrument_type=InstrumentType.OPTION,
                    symbol=long_call.get_option_symbol(),
                    side=OrderSide.BUY_TO_OPEN,
                    quantity=quantity,
                    order_type=OrderType.LIMIT,
                    option_contract=long_call
                ),
                OrderLeg(
                    instrument_type=InstrumentType.OPTION,
                    symbol=short_call.get_option_symbol(),
                    side=OrderSide.SELL_TO_OPEN,
                    quantity=quantity,
                    order_type=OrderType.LIMIT,
                    option_contract=short_call
                )
            ]
            
            # Create multi-leg order
            order = MultiLegOrder(
                order_id=order_id,
                strategy_type="BULL_CALL_SPREAD",
                legs=legs,
                net_debit_credit=net_debit,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                commission=self.calculate_commission(legs, quantity)
            )
            
            logger.info(f"Created Bull Call Spread order: {order_id}")
            logger.info(f"  Long Call: {underlying} ${long_strike} CALL {expiration}")
            logger.info(f"  Short Call: {underlying} ${short_strike} CALL {expiration}")
            logger.info(f"  Net Debit: ${net_debit:.2f}")
            logger.info(f"  Quantity: {quantity} spreads")
            
            return order_id
            
        except Exception as e:
            logger.error(f"Error creating Bull Call Spread order: {e}")
            raise
    
    def create_bull_call_spread_exit_order(self, underlying: str, long_strike: float,
                                         short_strike: float, expiration: str,
                                         net_credit: float, quantity: int = 1) -> str:
        """
        Create exit order for Bull Call Spread
        
        Args:
            underlying: Underlying symbol
            long_strike: Strike price of long call
            short_strike: Strike price of short call  
            expiration: Expiration date
            net_credit: Net credit to receive for closing
            quantity: Number of spreads to close
            
        Returns:
            Order ID for tracking
        """
        try:
            # Generate unique order ID
            order_id = f"BCS_EXIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create option contracts
            long_call = OptionContract(
                symbol=f"{underlying}_CALL_{long_strike}_{expiration}",
                underlying=underlying,
                strike=long_strike,
                expiration=expiration,  
                option_type="CALL"
            )
            
            short_call = OptionContract(
                symbol=f"{underlying}_CALL_{short_strike}_{expiration}",
                underlying=underlying,
                strike=short_strike,
                expiration=expiration,
                option_type="CALL"
            )
            
            # Create exit legs (reverse of entry)
            legs = [
                OrderLeg(
                    instrument_type=InstrumentType.OPTION,
                    symbol=long_call.get_option_symbol(),
                    side=OrderSide.SELL_TO_CLOSE,
                    quantity=quantity,
                    order_type=OrderType.LIMIT,
                    option_contract=long_call
                ),
                OrderLeg(
                    instrument_type=InstrumentType.OPTION,
                    symbol=short_call.get_option_symbol(),
                    side=OrderSide.BUY_TO_CLOSE,
                    quantity=quantity,
                    order_type=OrderType.LIMIT,
                    option_contract=short_call
                )
            ]
            
            # Create multi-leg exit order
            order = MultiLegOrder(
                order_id=order_id,
                strategy_type="BULL_CALL_SPREAD_EXIT",
                legs=legs,
                net_debit_credit=-net_credit,  # Negative for credit received
                order_type=OrderType.LIMIT,
                quantity=quantity,
                commission=self.calculate_commission(legs, quantity)
            )
            
            logger.info(f"Created Bull Call Spread exit order: {order_id}")
            logger.info(f"  Net Credit: ${net_credit:.2f}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"Error creating Bull Call Spread exit order: {e}")
            raise
    
    def submit_order(self, order_id: str) -> bool:
        """
        Submit order for execution
        
        Args:
            order_id: Order ID to submit
            
        Returns:
            True if submitted successfully, False otherwise
        """
        try:
            if order_id not in self.active_orders:
                # Find order in history
                order = None
                for hist_order in self.order_history:
                    if hist_order.order_id == order_id:
                        order = hist_order
                        break
                
                if not order:
                    logger.error(f"Order {order_id} not found")
                    return False
                
                # Add to active orders
                self.active_orders[order_id] = order
            else:
                order = self.active_orders[order_id]
            
            # Validate order
            if not self.validate_order(order):
                order.status = OrderStatus.REJECTED
                order.notes = "Order validation failed"
                self.move_to_completed(order_id)
                return False
            
            # Submit order
            if self.paper_trading:
                success = self.submit_paper_order(order)
            else:
                success = self.submit_live_order(order)
            
            if success:
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = datetime.now()
                logger.info(f"Order {order_id} submitted successfully")
            else:
                order.status = OrderStatus.REJECTED
                order.notes = "Submission failed"
                self.move_to_completed(order_id)
                
            self.save_state()
            return success
            
        except Exception as e:
            logger.error(f"Error submitting order {order_id}: {e}")
            return False
    
    def validate_order(self, order: MultiLegOrder) -> bool:
        """
        Validate order before submission
        
        Args:
            order: Order to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check order value limits
            total_value = abs(order.net_debit_credit) * order.quantity * 100
            if total_value > self.config['max_order_value']:
                logger.warning(f"Order value ${total_value:.2f} exceeds limit ${self.config['max_order_value']:.2f}")
                return False
            
            # Check spread width for spreads
            if order.strategy_type in ["BULL_CALL_SPREAD", "BULL_CALL_SPREAD_EXIT"]:
                if len(order.legs) >= 2:
                    strikes = [leg.option_contract.strike for leg in order.legs if leg.option_contract]
                    if len(strikes) >= 2:
                        spread_width = abs(max(strikes) - min(strikes))
                        if spread_width > self.config['max_spread_width']:
                            logger.warning(f"Spread width ${spread_width:.2f} exceeds limit ${self.config['max_spread_width']:.2f}")
                            return False
            
            # Check market hours if required
            if self.config['market_hours_only']:
                now = datetime.now()
                # Simplified market hours check (9:30 AM - 4:00 PM ET, weekdays)
                if now.weekday() >= 5:  # Weekend
                    logger.warning("Markets closed - weekend")
                    return False
                
                # Note: Real implementation would handle holidays and exact market hours
            
            logger.debug(f"Order {order.order_id} validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return False
    
    def submit_paper_order(self, order: MultiLegOrder) -> bool:
        """
        Submit order in paper trading mode
        
        Args:
            order: Order to submit
            
        Returns:
            True if submitted successfully
        """
        try:
            # Simulate random rejection
            import random
            if random.random() < self.rejection_rate:
                logger.info(f"Paper order {order.order_id} randomly rejected (simulation)")
                return False
            
            # Schedule fill processing
            self.executor.submit(self.process_paper_fill, order.order_id)
            
            logger.info(f"Paper order {order.order_id} submitted for processing")
            return True
            
        except Exception as e:
            logger.error(f"Error in paper order submission: {e}")
            return False
    
    def submit_live_order(self, order: MultiLegOrder) -> bool:
        """
        Submit order to live broker (placeholder for real implementation)
        
        Args:
            order: Order to submit
            
        Returns:
            True if submitted successfully
        """
        # This would integrate with actual broker API (Alpaca, Interactive Brokers, etc.)
        logger.warning("Live order submission not implemented - using paper trading")
        return self.submit_paper_order(order)
    
    def process_paper_fill(self, order_id: str):
        """
        Process paper trading fill with realistic delay
        
        Args:
            order_id: Order ID to process
        """
        try:
            # Simulate fill delay
            time.sleep(self.fill_delay_seconds)
            
            if order_id not in self.active_orders:
                logger.warning(f"Order {order_id} not found in active orders")
                return
            
            order = self.active_orders[order_id]
            
            # Simulate fill at requested price (paper trading assumption)
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.now()
            order.fill_price = abs(order.net_debit_credit)
            
            # Move to completed
            self.move_to_completed(order_id)
            
            logger.info(f"Paper order {order_id} filled at ${order.fill_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error processing paper fill for {order_id}: {e}")
    
    def move_to_completed(self, order_id: str):
        """Move order from active to completed"""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            self.completed_orders[order_id] = order
            del self.active_orders[order_id]
            self.save_state()
    
    def calculate_commission(self, legs: List[OrderLeg], quantity: int) -> float:
        """
        Calculate total commission for order
        
        Args:
            legs: Order legs
            quantity: Number of spreads
            
        Returns:
            Total commission
        """
        total_contracts = sum([leg.quantity for leg in legs]) * quantity
        return total_contracts * self.config['commission_per_contract']
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Get current status of order
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Order status or None if not found
        """
        if order_id in self.active_orders:
            return self.active_orders[order_id].status
        elif order_id in self.completed_orders:
            return self.completed_orders[order_id].status
        else:
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel active order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        try:
            if order_id not in self.active_orders:
                logger.warning(f"Cannot cancel order {order_id} - not active")
                return False
            
            order = self.active_orders[order_id]
            
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                logger.warning(f"Cannot cancel order {order_id} - status: {order.status}")
                return False
            
            order.status = OrderStatus.CANCELLED
            order.notes = "Cancelled by user"
            
            self.move_to_completed(order_id)
            
            logger.info(f"Order {order_id} cancelled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_order_summary(self) -> Dict[str, Any]:
        """Get comprehensive order summary"""
        total_orders = len(self.order_history)
        filled_orders = len([o for o in self.order_history if o.status == OrderStatus.FILLED])
        rejected_orders = len([o for o in self.order_history if o.status == OrderStatus.REJECTED])
        
        total_commission = sum([o.commission for o in self.order_history])
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_orders': total_orders,
            'active_orders': len(self.active_orders),
            'completed_orders': len(self.completed_orders),
            'filled_orders': filled_orders,
            'rejected_orders': rejected_orders,
            'fill_rate': (filled_orders / total_orders * 100) if total_orders > 0 else 0,
            'total_commission': total_commission,
            'active_order_ids': list(self.active_orders.keys()),
            'recent_orders': [o.to_dict() for o in self.order_history[-5:]]
        }
    
    def shutdown(self):
        """Graceful shutdown of OMS"""
        logger.info("Shutting down Order Management System...")
        
        # Cancel all active orders
        for order_id in list(self.active_orders.keys()):
            self.cancel_order(order_id)
        
        # Save final state
        self.save_state()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        logger.info("Order Management System shutdown complete")


def main():
    """
    Test the Order Management System
    """
    print("=" * 60)
    print("ORDER MANAGEMENT SYSTEM TEST")
    print("=" * 60)
    
    # Initialize OMS
    oms = OrderManagementSystem()
    
    # Create test Bull Call Spread order
    order_id = oms.create_bull_call_spread_order(
        underlying="SPY",
        long_strike=400.0,
        short_strike=420.0,
        expiration="2024-02-16",
        net_debit=2.50,
        quantity=1
    )
    
    print(f"Created order: {order_id}")
    
    # Submit order
    success = oms.submit_order(order_id)
    print(f"Order submission: {'SUCCESS' if success else 'FAILED'}")
    
    # Wait for fill
    print("Waiting for fill...")
    time.sleep(6)
    
    # Check status
    status = oms.get_order_status(order_id)
    print(f"Final status: {status}")
    
    # Get summary
    summary = oms.get_order_summary()
    print("\nOMS Summary:")
    for key, value in summary.items():
        if key != 'recent_orders':
            print(f"  {key}: {value}")
    
    print("\nOrder Management System test completed")


if __name__ == "__main__":
    main()