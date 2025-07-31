#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cardea Web UI Server
Serves the Cardea web interface with real-time data integration

This provides a web-based dashboard identical to Janus but adapted for
Bull Call Spread options trading monitoring.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template_string, jsonify, send_from_directory
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# State file locations (same as Cardea Slack agent)
TRADER_STATE_FILE = "live_trader_state.json"
OMS_STATE_FILE = "oms_state.json"
CONFIG_FILE = "live_trader_config.json"
LOG_FILE = "live_trader.log"

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
    """Get comprehensive system status (same as Cardea Slack agent)"""
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

@app.route('/')
def index():
    """Serve the Cardea web UI"""
    try:
        with open('cardea_web_ui.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except Exception as e:
        logger.error(f"Error serving UI: {e}")
        return f"<h1>Cardea UI Error</h1><p>Could not load interface: {e}</p>", 500

@app.route('/api/cardea/status')
def api_status():
    """API endpoint for system status"""
    return jsonify(get_system_status())

@app.route('/api/cardea/positions')
def api_positions():
    """API endpoint for positions"""
    return jsonify(get_positions_detail())

@app.route('/api/cardea/market')
def api_market():
    """API endpoint for market data"""
    return jsonify(get_market_data())

@app.route('/api/cardea/performance')
def api_performance():
    """API endpoint for performance metrics"""
    try:
        trader_state = load_json_file(TRADER_STATE_FILE)
        config = load_json_file(CONFIG_FILE)
        
        positions = trader_state.get('positions', [])
        closed_positions = [p for p in positions if p.get('status') == 'CLOSED']
        
        if not closed_positions:
            return jsonify({
                "success": True,
                "data": {
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "avg_pnl": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0,
                    "total_pnl": 0.0
                }
            })
        
        # Calculate metrics
        pnls = [p.get('current_pnl', 0) for p in closed_positions]
        winning_trades = [pnl for pnl in pnls if pnl > 0]
        
        return jsonify({
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
        })
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Cardea Web UI",
        "timestamp": datetime.now().isoformat()
    })

def main():
    """Start Cardea web server"""
    logger.info("Starting Cardea Web UI Server")
    logger.info("Sister interface to Janus - Bull Call Spread Guardian")
    
    try:
        # Check if HTML file exists
        if not os.path.exists('cardea_web_ui.html'):
            logger.error("cardea_web_ui.html not found!")
            return
        
        logger.info("Cardea Web UI available at: http://localhost:5001")
        logger.info("API endpoints:")
        logger.info("  /api/cardea/status - System status")
        logger.info("  /api/cardea/positions - Position details")
        logger.info("  /api/cardea/market - Market data")
        logger.info("  /api/cardea/performance - Performance metrics")
        
        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("Cardea Web UI shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in Cardea Web UI: {e}")

if __name__ == "__main__":
    main()