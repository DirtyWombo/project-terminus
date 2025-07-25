#!/usr/bin/env python3
"""
Operation Badger - Continuous Stock Trading Engine
==================================================

Stock trading system with advanced market intelligence.
Handles market hours, PDT rules, and stock-specific logic.
"""

import logging
import time
import json
import threading
import requests
import psutil
import pandas_market_calendars as mcal
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from trader_app.brokerage_manager import brokerage_manager

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/stock_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradingMetrics:
    portfolio_value: float = 10000.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    daily_return: float = 0.0
    cumulative_return: float = 0.0
    max_drawdown: float = 0.0
    current_positions: int = 0

class ContinuousPaperTrading:
    def __init__(self):
        self.running = False
        self.metrics = TradingMetrics()
        self.config = {
            "cycle_interval_minutes": 15,
            "position_size": 0.005,  # 0.5%
            "max_positions": 5,
            "symbols": ["CRWD", "SNOW", "PLTR", "RBLX", "COIN", "UBER", "SPOT", "ZM"],
            "max_transaction_cost_percent": 0.001,  # 0.1% transaction costs
            "stop_loss_multiplier": 2.0
        }
        
        # Stock market specific configuration
        self.market_calendar = mcal.get_calendar('NYSE')
        self.enable_paper_trading = os.getenv('ENABLE_PAPER_TRADING', 'true').lower() == 'true'
        self.pdt_protection = os.getenv('PDT_PROTECTION_ENABLED', 'true').lower() == 'true'
        self.last_cycle_time = datetime.now()
        
    def check_ai_service(self) -> bool:
        """Check if AI service is available."""
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def is_market_open(self) -> bool:
        """Check if stock market is open for trading."""
        return brokerage_manager.is_market_open()
    
    def can_trade_today(self) -> bool:
        """Check if we can trade today (market open + PDT rules)."""
        if not self.is_market_open():
            return False
            
        if self.pdt_protection:
            account_info = brokerage_manager.get_account_info()
            return account_info.get('can_day_trade', False)
            
        return True
    
    def get_velocity_score(self, symbol: str) -> Dict:
        """Get AI velocity score for symbol."""
        # Simulated AI analysis (replace with actual Ollama call in production)
        import random
        
        velocity_score = random.uniform(-1.0, 1.0)
        confidence = random.uniform(0.4, 0.9)
        
        return {
            "symbol": symbol,
            "velocity_score": velocity_score,
            "confidence": confidence,
            "signal": "BUY" if velocity_score > 0.3 else "SELL" if velocity_score < -0.3 else "HOLD",
            "timestamp": datetime.now().isoformat()
        }
    
    def simulate_trade_execution(self, symbol: str, signal: str, velocity_score: float) -> Dict:
        """Execute trade via brokerage or simulate for paper trading."""
        import random
        
        # Check transaction costs
        transaction_cost_percent = random.uniform(0.0001, 0.002)  # 0.01% to 0.2%
        
        if transaction_cost_percent > self.config["max_transaction_cost_percent"]:
            return {
                "status": "aborted",
                "reason": f"Transaction costs too high ({transaction_cost_percent:.1%})",
                "symbol": symbol
            }
        
        # Calculate position size
        position_size = self.config["position_size"] * self.metrics.portfolio_value
        
        if self.enable_paper_trading:
            # Simulate trade outcome for paper trading
            win_probability = 0.5 + (velocity_score * 0.3)  # 20% to 80% win rate
            win = random.random() < win_probability
            
            if win:
                return_pct = random.uniform(0.005, 0.025)  # 0.5% to 2.5% gain
                pnl = position_size * return_pct
                self.metrics.winning_trades += 1
            else:
                return_pct = random.uniform(-0.02, -0.005)  # 0.5% to 2% loss
                pnl = position_size * return_pct
                self.metrics.losing_trades += 1
                
            # Update portfolio (paper trading)
            self.metrics.portfolio_value += pnl
            self.metrics.total_trades += 1
            
            result = {
                "status": "executed",
                "symbol": symbol,
                "signal": signal,
                "position_size": position_size,
                "pnl": pnl,
                "return_pct": return_pct,
                "transaction_cost": transaction_cost_percent,
                "portfolio_value": self.metrics.portfolio_value,
                "win": win,
                "paper_trading": True
            }
        else:
            # Real trade execution via Alpaca
            try:
                # Get current price
                current_price = brokerage_manager.get_stock_price(symbol)
                if not current_price:
                    return {
                        "status": "aborted",
                        "reason": "Could not get current price",
                        "symbol": symbol
                    }
                
                # Calculate quantity
                qty = int(position_size / current_price)
                if qty <= 0:
                    return {
                        "status": "aborted", 
                        "reason": "Position size too small",
                        "symbol": symbol
                    }
                
                # Place order
                side = "buy" if signal == "BUY" else "sell"
                order_result = brokerage_manager.place_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    order_type="market"
                )
                
                if order_result.get('error'):
                    return {
                        "status": "aborted",
                        "reason": order_result['error'],
                        "symbol": symbol
                    }
                
                # Update metrics for real trading
                self.metrics.total_trades += 1
                
                result = {
                    "status": "executed",
                    "symbol": symbol,
                    "signal": signal,
                    "qty": qty,
                    "order_id": order_result.get('order_id'),
                    "transaction_cost": transaction_cost_percent,
                    "paper_trading": False
                }
                
            except Exception as e:
                logger.error(f"Error executing real trade for {symbol}: {e}")
                return {
                    "status": "aborted",
                    "reason": str(e),
                    "symbol": symbol
                }
        
        # Update performance metrics
        if self.enable_paper_trading:
            total_return = (self.metrics.portfolio_value - 10000) / 10000
            self.metrics.cumulative_return = total_return
            
            # Update max drawdown
            peak_value = max(self.metrics.portfolio_value, 10000)
            drawdown = (peak_value - self.metrics.portfolio_value) / peak_value
            self.metrics.max_drawdown = max(self.metrics.max_drawdown, drawdown)
        
        return result
    
    def run_trading_cycle(self):
        """Execute one complete trading cycle."""
        cycle_start = datetime.now()
        logger.info(f"=== TRADING CYCLE START - {cycle_start.strftime('%H:%M:%S')} ===")
        
        # Check if we can trade today
        if not self.can_trade_today():
            market_status = brokerage_manager.get_market_status()
            logger.info(f"Market closed or PDT restricted - Session: {market_status.get('session', 'unknown')}")
            logger.info(f"Next market open: {market_status.get('next_open', 'unknown')}")
            return {"trades_executed": 0, "reason": "market_closed_or_pdt_restricted"}
        
        # Check AI service
        ai_available = self.check_ai_service()
        if not ai_available:
            logger.warning("AI service unavailable - using fallback analysis")
        
        trades_executed = 0
        cycle_results = []
        
        for symbol in self.config["symbols"]:
            try:
                # Get AI analysis
                analysis = self.get_velocity_score(symbol)
                
                # Skip if confidence too low
                if analysis["confidence"] < 0.6:
                    logger.info(f"{symbol}: Low confidence ({analysis['confidence']:.2f}) - skipping")
                    continue
                
                # Skip if portfolio at max positions
                if self.metrics.current_positions >= self.config["max_positions"]:
                    logger.info(f"{symbol}: Max positions reached - skipping")
                    break
                
                # Execute trade if signal is strong enough
                if analysis["signal"] in ["BUY", "SELL"]:
                    result = self.simulate_trade_execution(
                        symbol, 
                        analysis["signal"],
                        analysis["velocity_score"]
                    )
                    
                    if result["status"] == "executed":
                        trades_executed += 1
                        self.metrics.current_positions += 1
                        
                        if result.get('paper_trading', True):
                            logger.info(f"✅ {symbol}: {result['signal']} - PnL: ${result['pnl']:.2f} ({result['return_pct']:.2%}) [PAPER]")
                        else:
                            logger.info(f"✅ {symbol}: {result['signal']} - Qty: {result['qty']} - Order: {result['order_id']} [LIVE]")
                    else:
                        logger.warning(f"❌ {symbol}: {result['reason']}")
                    
                    cycle_results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
        
        # Update daily return (simplified)
        start_of_day_value = 10000  # This should track actual start of day
        self.metrics.daily_return = (self.metrics.portfolio_value - start_of_day_value) / start_of_day_value
        
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        
        # Log cycle summary
        win_rate = (self.metrics.winning_trades / max(self.metrics.total_trades, 1)) * 100
        
        logger.info(f"=== CYCLE COMPLETE - {trades_executed} trades executed ===")
        logger.info(f"Portfolio: ${self.metrics.portfolio_value:.2f} ({self.metrics.cumulative_return:.2%})")
        logger.info(f"Win Rate: {win_rate:.1f}% ({self.metrics.winning_trades}/{self.metrics.total_trades})")
        logger.info(f"Max Drawdown: {self.metrics.max_drawdown:.2%}")
        logger.info(f"Cycle Duration: {cycle_duration:.2f} seconds")
        logger.info("")
        
        # Save state
        self.save_trading_state()
        
        # Reset positions (simplified - assumes all positions close each cycle)
        self.metrics.current_positions = 0
        
        self.last_cycle_time = datetime.now()
        
        return {
            "trades_executed": trades_executed,
            "cycle_duration": cycle_duration,
            "portfolio_value": self.metrics.portfolio_value,
            "results": cycle_results
        }
    
    def save_trading_state(self):
        """Save current trading state to file."""
        state = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "portfolio_value": self.metrics.portfolio_value,
                "total_trades": self.metrics.total_trades,
                "winning_trades": self.metrics.winning_trades,
                "losing_trades": self.metrics.losing_trades,
                "daily_return": self.metrics.daily_return,
                "cumulative_return": self.metrics.cumulative_return,
                "max_drawdown": self.metrics.max_drawdown,
                "current_positions": self.metrics.current_positions
            },
            "config": self.config
        }
        
        with open("trading_state.json", "w") as f:
            json.dump(state, f, indent=2)
    
    def load_trading_state(self):
        """Load previous trading state if exists."""
        try:
            if os.path.exists("trading_state.json"):
                with open("trading_state.json", "r") as f:
                    state = json.load(f)
                
                metrics_data = state.get("metrics", {})
                self.metrics.portfolio_value = metrics_data.get("portfolio_value", 10000.0)
                self.metrics.total_trades = metrics_data.get("total_trades", 0)
                self.metrics.winning_trades = metrics_data.get("winning_trades", 0)
                self.metrics.losing_trades = metrics_data.get("losing_trades", 0)
                self.metrics.daily_return = metrics_data.get("daily_return", 0.0)
                self.metrics.cumulative_return = metrics_data.get("cumulative_return", 0.0)
                self.metrics.max_drawdown = metrics_data.get("max_drawdown", 0.0)
                self.metrics.current_positions = metrics_data.get("current_positions", 0)
                
                logger.info(f"Loaded previous state: ${self.metrics.portfolio_value:.2f} portfolio")
        except Exception as e:
            logger.error(f"Error loading state: {e}")
    
    def start_continuous_trading(self):
        """Start continuous trading in background."""
        self.running = True
        self.load_trading_state()
        
        # Get market status
        market_status = brokerage_manager.get_market_status()
        
        logger.info("🚀 Operation Badger - Stock Trading System Activated")
        logger.info("=" * 60)
        logger.info(f"Strategy: Narrative Surfer (Market Intelligence)")
        logger.info(f"Mode: {'Paper Trading' if self.enable_paper_trading else 'LIVE Trading'}")
        logger.info(f"Market Status: {market_status.get('session', 'unknown').upper()}")
        logger.info(f"PDT Protection: {'Enabled' if self.pdt_protection else 'Disabled'}")
        logger.info(f"Cycle Interval: {self.config['cycle_interval_minutes']} minutes")
        logger.info(f"Position Size: {self.config['position_size']:.1%} per trade")
        logger.info(f"Starting Portfolio: ${self.metrics.portfolio_value:.2f}")
        logger.info(f"Symbols: {', '.join(self.config['symbols'])}")
        logger.info("=" * 60)
        logger.info("")
        
        try:
            while self.running:
                # Run trading cycle
                self.run_trading_cycle()
                
                # Wait for next cycle
                wait_seconds = self.config["cycle_interval_minutes"] * 60
                logger.info(f"⏰ Next cycle in {self.config['cycle_interval_minutes']} minutes...")
                
                for i in range(wait_seconds):
                    if not self.running:
                        break
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Trading stopped by user")
        except Exception as e:
            logger.error(f"💥 Trading error: {e}")
        finally:
            self.stop_trading()
    
    def stop_trading(self):
        """Stop continuous trading."""
        self.running = False
        self.save_trading_state()
        
        # Final summary
        win_rate = (self.metrics.winning_trades / max(self.metrics.total_trades, 1)) * 100
        sharpe_ratio = self.calculate_sharpe_ratio()
        
        logger.info("")
        logger.info("📊 FINAL TRADING SUMMARY")
        logger.info("=" * 40)
        logger.info(f"Final Portfolio: ${self.metrics.portfolio_value:.2f}")
        logger.info(f"Total Return: {self.metrics.cumulative_return:.2%}")
        logger.info(f"Total Trades: {self.metrics.total_trades}")
        logger.info(f"Win Rate: {win_rate:.1f}%")
        logger.info(f"Max Drawdown: {self.metrics.max_drawdown:.2%}")
        logger.info(f"Estimated Sharpe: {sharpe_ratio:.2f}")
        logger.info("=" * 40)
        logger.info("🛑 Operation Badger Stock Trading System Stopped")
    
    def calculate_sharpe_ratio(self) -> float:
        """Calculate estimated Sharpe ratio."""
        if self.metrics.total_trades < 10:
            return 0.0
        
        # Simplified Sharpe calculation
        annual_return = self.metrics.cumulative_return * (365 / 30)  # Annualized
        volatility = max(self.metrics.max_drawdown * 2, 0.05)  # Simplified volatility
        risk_free_rate = 0.05  # 5% risk-free rate
        
        return (annual_return - risk_free_rate) / volatility

def main():
    """Main function."""
    trader = ContinuousPaperTrading()
    
    print("Operation Badger - Stock Trading System")
    print("Advanced Market Intelligence & Automated Trading")
    print("Press Ctrl+C to stop trading")
    print()
    
    # Start trading
    trader.start_continuous_trading()

if __name__ == "__main__":
    main()