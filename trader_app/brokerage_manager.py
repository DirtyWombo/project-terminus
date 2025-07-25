"""
Operation Badger - Stock Brokerage Manager
Advanced stock market trading interface
Handles Alpaca API integration for paper and live trading
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import pandas_market_calendars as mcal
import pandas as pd
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError
from dotenv import load_dotenv

load_dotenv()

class BrokerageManager:
    """
    Stock Brokerage Manager for Alpaca API integration
    Handles order placement, account management, and market data
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Alpaca API configuration
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        self.paper_trading = os.getenv('ALPACA_PAPER_TRADING', 'true').lower() == 'true'
        
        # Trading configuration
        self.pdt_protection = os.getenv('PDT_PROTECTION_ENABLED', 'true').lower() == 'true'
        self.max_day_trades = int(os.getenv('MAX_DAY_TRADES_PER_WEEK', '3'))
        self.pdt_threshold = float(os.getenv('ACCOUNT_VALUE_THRESHOLD', '25000'))
        
        # Market hours configuration
        self.market_timezone = os.getenv('MARKET_TIMEZONE', 'America/New_York')
        self.enable_premarket = os.getenv('ENABLE_PREMARKET_TRADING', 'false').lower() == 'true'
        self.enable_afterhours = os.getenv('ENABLE_AFTERHOURS_TRADING', 'false').lower() == 'true'
        
        # Initialize Alpaca API
        self.api = None
        self.market_calendar = mcal.get_calendar('NYSE')
        self.initialize_api()
        
        # Cache for market status
        self._market_status_cache = {}
        self._cache_timestamp = None
        
    def initialize_api(self):
        """Initialize Alpaca API connection"""
        try:
            if not self.api_key or not self.secret_key:
                raise ValueError("Alpaca API credentials not configured")
                
            self.api = tradeapi.REST(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url,
                api_version='v2'
            )
            
            # Test connection
            account = self.api.get_account()
            self.logger.info(f"Connected to Alpaca API - Account: {account.status}")
            
            if self.paper_trading:
                self.logger.info("Running in PAPER TRADING mode")
            else:
                self.logger.warning("Running in LIVE TRADING mode")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Alpaca API: {e}")
            raise
    
    def is_market_open(self) -> bool:
        """Check if market is currently open for trading"""
        try:
            clock = self.api.get_clock()
            
            # Check basic market hours
            if clock.is_open:
                return True
                
            # Check extended hours if enabled
            now = datetime.now(timezone.utc)
            
            if self.enable_premarket:
                # Pre-market: 4:00 AM - 9:30 AM ET
                market_open = clock.next_open.replace(hour=9, minute=0)  # 4 AM ET in UTC
                if now >= market_open.replace(hour=9, minute=0) and now < clock.next_open:
                    return True
                    
            if self.enable_afterhours:
                # After-hours: 4:00 PM - 8:00 PM ET
                market_close = clock.next_close
                after_hours_close = market_close.replace(hour=24, minute=0)  # 8 PM ET in UTC
                if now >= market_close and now < after_hours_close:
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking market status: {e}")
            return False
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get comprehensive market status information"""
        try:
            clock = self.api.get_clock()
            
            status = {
                'is_open': clock.is_open,
                'next_open': clock.next_open.isoformat(),
                'next_close': clock.next_close.isoformat(),
                'current_time': clock.timestamp.isoformat(),
                'extended_hours_available': self.enable_premarket or self.enable_afterhours
            }
            
            # Add trading session info
            now = datetime.now(timezone.utc)
            
            if clock.is_open:
                status['session'] = 'regular'
            elif self.enable_premarket and now < clock.next_open:
                status['session'] = 'premarket'
            elif self.enable_afterhours and now > clock.next_close:
                status['session'] = 'afterhours'
            else:
                status['session'] = 'closed'
                
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting market status: {e}")
            return {'is_open': False, 'session': 'unknown'}
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information and trading power"""
        try:
            account = self.api.get_account()
            
            account_info = {
                'account_id': account.id,
                'status': account.status,
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'equity': float(account.equity),
                'last_equity': float(account.last_equity),
                'day_trade_count': int(account.daytrade_count) if account.daytrade_count else 0,
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked,
                'transfers_blocked': account.transfers_blocked
            }
            
            # Add PDT status
            account_info['pdt_protection_active'] = self.pdt_protection
            account_info['can_day_trade'] = self._can_day_trade(account_info)
            
            return account_info
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return {}
    
    def _can_day_trade(self, account_info: Dict[str, Any]) -> bool:
        """Check if account can execute day trades"""
        if not self.pdt_protection:
            return True
            
        # PDT rule: Need $25k+ OR < 3 day trades in 5 business days
        if account_info['portfolio_value'] >= self.pdt_threshold:
            return True
            
        if account_info['day_trade_count'] < self.max_day_trades:
            return True
            
        return False
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            positions = self.api.list_positions()
            
            position_list = []
            for pos in positions:
                position_info = {
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'side': 'long' if float(pos.qty) > 0 else 'short',
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price)
                }
                position_list.append(position_info)
                
            return position_list
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def place_order(self, symbol: str, qty: float, side: str, order_type: str = 'market', 
                   time_in_force: str = 'day', limit_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place a stock order
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            qty: Quantity to trade
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', etc.
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            limit_price: Limit price for limit orders
        """
        try:
            # Validate market is open (unless extended hours enabled)
            if not self.is_market_open():
                raise ValueError("Market is closed and extended hours not enabled")
            
            # Validate PDT rules
            account_info = self.get_account_info()
            if not account_info.get('can_day_trade', False) and self._is_day_trade(symbol, side):
                raise ValueError("Day trade not allowed due to PDT restrictions")
            
            # Prepare order parameters
            order_params = {
                'symbol': symbol.upper(),
                'qty': qty,
                'side': side.lower(),
                'type': order_type.lower(),
                'time_in_force': time_in_force.lower()
            }
            
            if order_type.lower() == 'limit' and limit_price:
                order_params['limit_price'] = limit_price
            
            # Place order
            order = self.api.submit_order(**order_params)
            
            order_info = {
                'order_id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'order_type': order.order_type,
                'status': order.status,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None
            }
            
            self.logger.info(f"Order placed: {order_info}")
            return order_info
            
        except APIError as e:
            self.logger.error(f"Alpaca API error placing order: {e}")
            return {'error': str(e), 'success': False}
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return {'error': str(e), 'success': False}
    
    def _is_day_trade(self, symbol: str, side: str) -> bool:
        """Check if this would be a day trade"""
        try:
            # Get today's orders for this symbol
            orders = self.api.list_orders(
                status='filled',
                after=(datetime.now().date()).isoformat()
            )
            
            # Check if we have opposite side trades today
            opposite_side = 'sell' if side.lower() == 'buy' else 'buy'
            
            for order in orders:
                if order.symbol == symbol.upper() and order.side == opposite_side:
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking day trade status: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order"""
        try:
            order = self.api.get_order(order_id)
            
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'order_type': order.order_type,
                'status': order.status,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None,
                'filled_at': order.filled_at.isoformat() if order.filled_at else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting order status: {e}")
            return {'error': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        try:
            self.api.cancel_order(order_id)
            self.logger.info(f"Order {order_id} cancelled")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_recent_trades(self, symbol: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trade history"""
        try:
            orders = self.api.list_orders(
                status='filled',
                limit=limit,
                nested=True
            )
            
            trades = []
            for order in orders:
                if symbol and order.symbol != symbol.upper():
                    continue
                    
                trade_info = {
                    'order_id': order.id,
                    'symbol': order.symbol,
                    'qty': float(order.qty),
                    'side': order.side,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'filled_at': order.filled_at.isoformat() if order.filled_at else None,
                    'order_type': order.order_type
                }
                trades.append(trade_info)
                
            return trades
            
        except Exception as e:
            self.logger.error(f"Error getting trade history: {e}")
            return []
    
    def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price"""
        try:
            # Get latest trade
            trade = self.api.get_latest_trade(symbol)
            return float(trade.price) if trade else None
            
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Get current bid/ask quote"""
        try:
            quote = self.api.get_latest_quote(symbol)
            
            return {
                'symbol': symbol,
                'bid': float(quote.bid_price) if quote else None,
                'ask': float(quote.ask_price) if quote else None,
                'bid_size': int(quote.bid_size) if quote else None,
                'ask_size': int(quote.ask_size) if quote else None,
                'timestamp': quote.timestamp.isoformat() if quote and quote.timestamp else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting quote for {symbol}: {e}")
            return {'symbol': symbol, 'bid': None, 'ask': None}
    
    def close_all_positions(self) -> bool:
        """Emergency function to close all open positions"""
        try:
            self.api.close_all_positions()
            self.logger.warning("All positions closed via emergency protocol")
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing all positions: {e}")
            return False
    
    def get_buying_power(self) -> float:
        """Get available buying power"""
        try:
            account = self.api.get_account()
            return float(account.buying_power)
            
        except Exception as e:
            self.logger.error(f"Error getting buying power: {e}")
            return 0.0

# Create global instance
brokerage_manager = BrokerageManager()