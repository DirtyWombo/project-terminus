#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cardea: Slack AI Agent for Live Options Trading
Sister to Janus - focused on equity options and Bull Call Spread strategy

Named after Cardea, the Roman goddess of hinges and thresholds, who worked
closely with Janus to protect doorways. While Janus opens the doors to
opportunity, Cardea executes and protects the trades.

This agent provides comprehensive monitoring and control for the Sprint 19
live paper trading validation of the Bull Call Spread strategy.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from threading import Thread
import traceback
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cardea_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CARDEA_SLACK_BOT_TOKEN = os.environ.get("CARDEA_SLACK_BOT_TOKEN")
CARDEA_SLACK_APP_TOKEN = os.environ.get("CARDEA_SLACK_APP_TOKEN")
CARDEA_API_SECRET = os.environ.get("CARDEA_API_SECRET", "cardea-default-secret")

if not CARDEA_SLACK_BOT_TOKEN:
    raise ValueError("CARDEA_SLACK_BOT_TOKEN environment variable not set!")
if not CARDEA_SLACK_APP_TOKEN:
    raise ValueError("CARDEA_SLACK_APP_TOKEN environment variable not set!")

app = App(token=CARDEA_SLACK_BOT_TOKEN)

# State file locations
TRADER_STATE_FILE = "live_trader_state.json"
OMS_STATE_FILE = "oms_state.json" 
CONFIG_FILE = "live_trader_config.json"
LOG_FILE = "live_trader.log"

# Helper Functions
def load_json_file(filename: str) -> dict:
    """Load JSON file with error handling"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
    return {}

def get_system_status():
    """Get comprehensive system status"""
    try:
        trader_state = load_json_file(TRADER_STATE_FILE)
        oms_state = load_json_file(OMS_STATE_FILE)
        config = load_json_file(CONFIG_FILE)
        
        # Check if system is running
        system_running = False
        last_update = trader_state.get('timestamp', '')
        if last_update:
            try:
                last_dt = datetime.fromisoformat(last_update.replace('Z', ''))
                minutes_since = (datetime.now() - last_dt).total_seconds() / 60
                system_running = minutes_since < 30  # Running if updated within 30 min
            except:
                pass
        
        # Portfolio metrics
        equity = trader_state.get('paper_equity', 0.0)
        cash = trader_state.get('paper_cash', 0.0)  
        initial_capital = config.get('initial_capital', 100000.0)
        total_return = ((equity - initial_capital) / initial_capital) * 100
        
        # Position metrics
        positions = trader_state.get('positions', [])
        open_positions = [p for p in positions if p.get('status') == 'OPEN']
        closed_positions = [p for p in positions if p.get('status') == 'CLOSED']
        
        # Win rate calculation
        if closed_positions:
            winning_trades = [p for p in closed_positions if p.get('current_pnl', 0) > 0]
            win_rate = (len(winning_trades) / len(closed_positions)) * 100
        else:
            win_rate = 0.0
        
        # Order metrics
        orders = oms_state.get('orders', [])
        active_orders = [o for o in orders if o.get('status') in ['PENDING', 'SUBMITTED']]
        
        return {
            "success": True,
            "data": {
                "system_running": system_running,
                "last_update": last_update[:19] if last_update else "Never",
                "portfolio": {
                    "equity": equity,
                    "cash": cash,
                    "total_return_pct": total_return,
                    "initial_capital": initial_capital
                },
                "positions": {
                    "open": len(open_positions),
                    "total": len(positions),
                    "win_rate": win_rate
                },
                "orders": {
                    "active": len(active_orders),
                    "total": len(orders)
                },
                "strategy": config.get('underlying_symbol', 'SPY'),
                "max_positions": config.get('max_positions', 3),
                "contracts_per_trade": config.get('contracts_per_trade', 10)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {"success": False, "message": f"Error: {e}"}

def get_positions_detail():
    """Get detailed position information"""
    try:
        trader_state = load_json_file(TRADER_STATE_FILE)
        positions = trader_state.get('positions', [])
        
        open_positions = [p for p in positions if p.get('status') == 'OPEN']
        recent_closed = [p for p in positions if p.get('status') == 'CLOSED'][-5:]  # Last 5 closed
        
        return {
            "success": True,
            "data": {
                "open_positions": open_positions,
                "recent_closed": recent_closed
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return {"success": False, "message": f"Error: {e}"}

def get_recent_logs(lines: int = 20):
    """Get recent log entries"""
    try:
        if not os.path.exists(LOG_FILE):
            return {"success": False, "message": "Log file not found"}
        
        with open(LOG_FILE, 'r') as f:
            log_lines = f.readlines()
        
        # Get last N lines
        recent_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
        
        return {
            "success": True,
            "data": {
                "lines": [line.strip() for line in recent_lines],
                "total_lines": len(log_lines)
            }
        }
        
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {"success": False, "message": f"Error: {e}"}

def get_performance_metrics():
    """Get performance analytics"""
    try:
        trader_state = load_json_file(TRADER_STATE_FILE)
        config = load_json_file(CONFIG_FILE)
        
        positions = trader_state.get('positions', [])
        closed_positions = [p for p in positions if p.get('status') == 'CLOSED']
        
        if not closed_positions:
            return {
                "success": True,
                "data": {
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "avg_pnl": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0,
                    "total_pnl": 0.0
                }
            }
        
        # Calculate metrics
        pnls = [p.get('current_pnl', 0) for p in closed_positions]
        winning_trades = [pnl for pnl in pnls if pnl > 0]
        
        return {
            "success": True,
            "data": {
                "total_trades": len(closed_positions),
                "win_rate": (len(winning_trades) / len(closed_positions)) * 100,
                "avg_pnl": sum(pnls) / len(pnls),
                "best_trade": max(pnls) if pnls else 0,
                "worst_trade": min(pnls) if pnls else 0,
                "total_pnl": sum(pnls),
                "gross_profit": sum(winning_trades),
                "gross_loss": abs(sum([pnl for pnl in pnls if pnl < 0]))
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {"success": False, "message": f"Error: {e}"}

def emergency_stop():
    """Emergency stop procedure - close all positions and halt trading"""
    try:
        # In paper trading, we'll simulate this by updating state
        trader_state = load_json_file(TRADER_STATE_FILE)
        
        # Mark all open positions as emergency closed
        positions = trader_state.get('positions', [])
        emergency_closed = 0
        
        for position in positions:
            if position.get('status') == 'OPEN':
                position['status'] = 'EMERGENCY_CLOSED'
                position['exit_date'] = datetime.now().isoformat()
                position['exit_reason'] = 'EMERGENCY_STOP'
                emergency_closed += 1
        
        # Save updated state
        trader_state['emergency_stop'] = True
        trader_state['emergency_stop_time'] = datetime.now().isoformat()
        
        with open(TRADER_STATE_FILE, 'w') as f:
            json.dump(trader_state, f, indent=2, default=str)
        
        return {
            "success": True,
            "message": f"Emergency stop executed. Closed {emergency_closed} positions.",
            "positions_closed": emergency_closed
        }
        
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        return {"success": False, "message": f"Emergency stop failed: {e}"}

def get_market_data():
    """Get current SPY market data"""
    try:
        import yfinance as yf
        spy = yf.Ticker("SPY")
        hist = spy.history(period="2d")  # Get 2 days to calculate change
        
        if hist.empty:
            return {"success": False, "message": "No market data available"}
        
        current_price = float(hist['Close'].iloc[-1])
        prev_price = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
        change = current_price - prev_price
        change_pct = (change / prev_price) * 100 if prev_price > 0 else 0
        
        return {
            "success": True,
            "data": {
                "symbol": "SPY",
                "current_price": current_price,
                "change": change,
                "change_pct": change_pct,
                "volume": int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return {"success": False, "message": f"Market data error: {e}"}

# Slack Command Handlers

@app.command("/cardea-status")
def cardea_status_command(ack, respond):
    """Complete system health and portfolio overview"""
    ack()
    
    try:
        status_result = get_system_status()
        market_result = get_market_data()
        
        if not status_result["success"]:
            respond(f"❌ System Status Error: {status_result['message']}")
            return
        
        data = status_result["data"]
        
        # Build status message
        status_emoji = "🟢" if data["system_running"] else "🔴"
        return_emoji = "📈" if data["portfolio"]["total_return_pct"] >= 0 else "📉"
        
        message = f"""
{status_emoji} **CARDEA SYSTEM STATUS** {status_emoji}
*Bull Call Spread Live Trading Engine*

**SYSTEM HEALTH:**
• Status: {'RUNNING' if data['system_running'] else 'STOPPED'}
• Last Update: {data['last_update']}
• Strategy: {data['strategy']} Bull Call Spreads

**PORTFOLIO OVERVIEW:**
{return_emoji} Total Equity: ${data['portfolio']['equity']:,.2f}
💰 Available Cash: ${data['portfolio']['cash']:,.2f}  
📊 Total Return: {data['portfolio']['total_return_pct']:+.2f}%
🎯 Target Capital: ${data['portfolio']['initial_capital']:,.2f}

**POSITION SUMMARY:**
📍 Open Positions: {data['positions']['open']}/{data['max_positions']}
📈 Total Trades: {data['positions']['total']}
🎯 Win Rate: {data['positions']['win_rate']:.1f}%

**ORDER MANAGEMENT:**
⏳ Active Orders: {data['orders']['active']}
📋 Total Orders: {data['orders']['total']}
🎛️ Contracts/Trade: {data['contracts_per_trade']}
"""

        if market_result["success"]:
            market_data = market_result["data"]
            change_emoji = "📈" if market_data["change"] >= 0 else "📉"
            message += f"""
**MARKET DATA:**
{change_emoji} SPY: ${market_data['current_price']:.2f} ({market_data['change']:+.2f}, {market_data['change_pct']:+.2f}%)
"""

        respond(message)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        respond(f"❌ Status command error: {e}")

@app.command("/cardea-positions")
def cardea_positions_command(ack, respond):
    """Display summary of all open options positions with P&L"""
    ack()
    
    try:
        positions_result = get_positions_detail()
        
        if not positions_result["success"]:
            respond(f"❌ Positions Error: {positions_result['message']}")
            return
        
        data = positions_result["data"]
        open_positions = data["open_positions"]
        recent_closed = data["recent_closed"]
        
        if not open_positions and not recent_closed:
            respond("📋 **CARDEA POSITIONS**\n\n*No positions found*")
            return
        
        message = "📋 **CARDEA POSITIONS**\n*Bull Call Spread Portfolio*\n\n"
        
        # Open positions
        if open_positions:
            message += "🟢 **OPEN POSITIONS:**\n"
            total_unrealized = 0
            
            for pos in open_positions:
                entry_date = pos.get('entry_date', '')[:10]  # YYYY-MM-DD
                strikes = f"${pos.get('long_call_strike', 0):.0f}/${pos.get('short_call_strike', 0):.0f}"
                contracts = pos.get('contracts', 0)
                debit = pos.get('net_debit_paid', 0)
                unrealized_pnl = pos.get('unrealized_pnl', 0)
                total_unrealized += unrealized_pnl
                
                pnl_emoji = "📈" if unrealized_pnl >= 0 else "📉"
                
                message += f"• {entry_date} | {strikes} | {contracts}x | ${debit:.2f} debit\n"
                message += f"  {pnl_emoji} Unrealized P&L: ${unrealized_pnl:+,.2f}\n\n"
            
            message += f"💰 **Total Unrealized P&L: ${total_unrealized:+,.2f}**\n\n"
        
        # Recent closed positions
        if recent_closed:
            message += "⚪ **RECENT CLOSED POSITIONS:**\n"
            
            for pos in recent_closed[-3:]:  # Show last 3
                entry_date = pos.get('entry_date', '')[:10]
                exit_date = pos.get('exit_date', '')[:10] if pos.get('exit_date') else 'N/A'
                strikes = f"${pos.get('long_call_strike', 0):.0f}/${pos.get('short_call_strike', 0):.0f}"
                pnl = pos.get('current_pnl', 0)
                
                pnl_emoji = "✅" if pnl > 0 else "❌"
                
                message += f"• {entry_date}-{exit_date} | {strikes} | {pnl_emoji} ${pnl:+,.2f}\n"
        
        respond(message)
        
    except Exception as e:
        logger.error(f"Error in positions command: {e}")
        respond(f"❌ Positions command error: {e}")

@app.command("/cardea-logs")
def cardea_logs_command(ack, respond):
    """Show recent trading activity logs"""
    ack()
    
    try:
        logs_result = get_recent_logs(15)  # Get last 15 lines
        
        if not logs_result["success"]:
            respond(f"❌ Logs Error: {logs_result['message']}")
            return
        
        data = logs_result["data"]
        log_lines = data["lines"]
        
        if not log_lines:
            respond("📋 **CARDEA LOGS**\n\n*No recent logs found*")
            return
        
        message = f"📋 **CARDEA RECENT LOGS**\n*Last {len(log_lines)} entries*\n\n```\n"
        
        # Format logs for Slack
        for line in log_lines[-10:]:  # Show last 10 to avoid message limits
            # Truncate very long lines
            if len(line) > 100:
                line = line[:97] + "..."
            message += line + "\n"
        
        message += "```"
        
        respond(message)
        
    except Exception as e:
        logger.error(f"Error in logs command: {e}")
        respond(f"❌ Logs command error: {e}")

@app.command("/cardea-performance")
def cardea_performance_command(ack, respond):
    """Portfolio performance and trading metrics"""
    ack()
    
    try:
        perf_result = get_performance_metrics()
        
        if not perf_result["success"]:
            respond(f"❌ Performance Error: {perf_result['message']}")
            return
        
        data = perf_result["data"]
        
        if data["total_trades"] == 0:
            respond("📊 **CARDEA PERFORMANCE**\n\n*No completed trades yet*")
            return
        
        # Calculate additional metrics
        profit_factor = data["gross_profit"] / data["gross_loss"] if data["gross_loss"] > 0 else float('inf')
        
        message = f"""
📊 **CARDEA PERFORMANCE METRICS**
*Bull Call Spread Strategy Analytics*

**TRADING STATISTICS:**
📈 Total Trades: {data['total_trades']}
🎯 Win Rate: {data['win_rate']:.1f}%
💰 Average P&L: ${data['avg_pnl']:+,.2f}
🚀 Best Trade: ${data['best_trade']:+,.2f}
⚠️ Worst Trade: ${data['worst_trade']:+,.2f}

**PROFITABILITY:**
💵 Total P&L: ${data['total_pnl']:+,.2f}
📈 Gross Profit: ${data['gross_profit']:,.2f}
📉 Gross Loss: ${abs(data['gross_loss']):,.2f}
⚡ Profit Factor: {profit_factor:.2f}

**STRATEGY VALIDATION:**
🎯 Target Win Rate: >80% (Backtest: 84.6%)
📊 Target Profit Factor: >2.0
⏱️ Avg Hold Time: ~7-14 days (target)
"""
        
        respond(message)
        
    except Exception as e:
        logger.error(f"Error in performance command: {e}")
        respond(f"❌ Performance command error: {e}")

@app.command("/cardea-emergency-stop")
def cardea_emergency_stop_command(ack, respond):
    """Emergency shutdown - liquidate all positions and halt trading"""
    ack()
    
    try:
        # Confirm this is intentional
        stop_result = emergency_stop()
        
        if stop_result["success"]:
            message = f"""
🚨 **EMERGENCY STOP EXECUTED** 🚨

{stop_result['message']}

**ACTIONS TAKEN:**
• All open positions marked for closure
• Trading engine halted
• Emergency flag set in system state

⚠️ **Manual intervention required to restart system**
Use `/cardea-status` to verify stop completion.
"""
        else:
            message = f"❌ **EMERGENCY STOP FAILED**\n{stop_result['message']}"
        
        respond(message)
        
        # Also log this critical action
        logger.critical(f"EMERGENCY STOP triggered via Slack command. Result: {stop_result}")
        
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        respond(f"❌ Emergency stop error: {e}")

@app.command("/cardea-market")
def cardea_market_command(ack, respond):
    """Current market data and regime analysis"""
    ack()
    
    try:
        market_result = get_market_data()
        
        if not market_result["success"]:
            respond(f"❌ Market Data Error: {market_result['message']}")
            return
        
        data = market_result["data"]
        
        # Get additional market context
        config = load_json_file(CONFIG_FILE)
        
        change_emoji = "📈" if data["change"] >= 0 else "📉"
        volume_text = f"{data['volume']:,}" if data['volume'] > 0 else "N/A"
        
        message = f"""
📊 **CARDEA MARKET DATA**
*Current market conditions for {data['symbol']}*

**PRICE ACTION:**
{change_emoji} Current: ${data['current_price']:.2f}
📊 Change: ${data['change']:+.2f} ({data['change_pct']:+.2f}%)
📊 Volume: {volume_text}

**STRATEGY CONTEXT:**
🎯 Underlying: {config.get('underlying_symbol', 'SPY')}
⏰ Target DTE: {config.get('target_dte', 45)} days
🎚️ Max Positions: {config.get('max_positions', 3)}

**ENTRY CONDITIONS:**
• Bull regime: SPY > 200-day MA
• Pullback signal: Touch 20-day EMA
• Volatility filter: <40% IV
• Position spacing: 10+ days
"""
        
        respond(message)
        
    except Exception as e:
        logger.error(f"Error in market command: {e}")
        respond(f"❌ Market command error: {e}")

@app.command("/cardea-help")
def cardea_help_command(ack, respond):
    """Show all available Cardea commands"""
    ack()
    
    help_message = """
🛡️ **CARDEA COMMAND CENTER** 🛡️
*Your AI guardian for Bull Call Spread trading*

**SYSTEM MONITORING (4 commands):**
• `/cardea-status` - Complete system health + portfolio overview
• `/cardea-positions` - All open positions with real-time P&L
• `/cardea-logs` - Recent trading activity and system logs
• `/cardea-performance` - Trading metrics and strategy analytics

**MARKET INTELLIGENCE (1 command):**
• `/cardea-market` - Current SPY data and entry conditions

**EMERGENCY CONTROLS (1 command):**
• `/cardea-emergency-stop` - 🚨 Liquidate all positions and halt system

**INFORMATION:**
• `/cardea-help` - Show this command list

---
**ABOUT CARDEA:**
Named after the Roman goddess who protected thresholds and worked with Janus. While Janus opens doors to opportunity, Cardea executes and guards the trades.

**CURRENT MISSION:**
30-day paper trading validation of Bull Call Spread strategy
Target: 17.7% annualized returns with <5% drawdown

*Sister AI to Janus • Built for Sprint 19 Live Trading*
"""
    
    respond(help_message)

# Alert System
def send_slack_alert(message: str, channel: str = None):
    """Send alert message to Slack"""
    try:
        # Try to send to specific channel, fallback to DM to self if channel not found
        app.client.chat_postMessage(
            channel=channel or "general",  # Remove # to try just channel name
            text=f"**CARDEA ALERT**\n{message}"
        )
        logger.info(f"Slack alert sent: {message}")
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")
        # Don't spam logs with repeated channel errors

def monitor_system_alerts():
    """Background thread to monitor for alert conditions"""
    while True:
        try:
            status = get_system_status()
            
            if status["success"]:
                data = status["data"]
                
                # System down alert
                if not data["system_running"]:
                    send_slack_alert("⚠️ SYSTEM DOWN: Live trading engine is not responding!")
                
                # Performance alerts
                if data["portfolio"]["total_return_pct"] < -5.0:  # 5% drawdown
                    send_slack_alert(f"📉 DRAWDOWN ALERT: Portfolio down {abs(data['portfolio']['total_return_pct']):.1f}%")
                
                # Position limit alert
                if data["positions"]["open"] >= data["max_positions"]:
                    send_slack_alert(f"🚨 MAX POSITIONS: {data['positions']['open']}/{data['max_positions']} positions open")
            
            time.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            logger.error(f"Error in alert monitoring: {e}")
            time.sleep(60)  # Wait 1 minute on error

# Main execution
def main():
    """Start Cardea Slack agent"""
    logger.info("Starting Cardea - AI Guardian for Bull Call Spread Trading")
    
    try:
        # Start alert monitoring in background
        alert_thread = Thread(target=monitor_system_alerts, daemon=True)
        alert_thread.start()
        
        # Start Slack bot
        handler = SocketModeHandler(app, CARDEA_SLACK_APP_TOKEN)
        
        logger.info("Cardea is online and monitoring your trades")
        handler.start()
        
    except KeyboardInterrupt:
        logger.info("Cardea shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in Cardea agent: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()