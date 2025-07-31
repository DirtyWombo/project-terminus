#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 19: Live Monitoring Dashboard for Bull Call Spread Trading
Real-time system oversight and performance monitoring

This module provides a comprehensive monitoring dashboard for the live trading
engine, displaying real-time portfolio metrics, position status, and system
health indicators.

Key Features:
- Real-time portfolio performance display
- Live position tracking with P&L
- System health and status monitoring
- Order execution monitoring
- Performance metrics visualization
- Alert and notification system
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from collections import deque
import curses
import signal
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('dashboard.log')]
)
logger = logging.getLogger(__name__)

@dataclass
class DashboardMetrics:
    """Dashboard metrics snapshot"""
    timestamp: datetime
    equity: float
    cash: float
    total_return_pct: float
    day_pnl: float
    open_positions: int
    total_positions: int
    win_rate: float
    active_orders: int
    system_status: str
    last_signal_check: str
    current_price: float
    in_bull_regime: bool

class LiveMonitoringDashboard:
    """
    Real-time monitoring dashboard for live trading system
    """
    
    def __init__(self, refresh_interval: int = 5):
        """
        Initialize monitoring dashboard
        
        Args:
            refresh_interval: Data refresh interval in seconds
        """
        self.refresh_interval = refresh_interval
        self.running = False
        
        # Data sources
        self.trader_state_file = "live_trader_state.json"
        self.oms_state_file = "oms_state.json"
        self.config_file = "live_trader_config.json"
        
        # Metrics history for trends
        self.metrics_history = deque(maxlen=100)  # Keep last 100 data points
        
        # Display state
        self.screen = None
        self.current_metrics = None
        
        # Alert system
        self.alerts = deque(maxlen=50)
        self.alert_thresholds = {
            'max_drawdown_pct': -5.0,
            'min_win_rate': 50.0,
            'max_open_positions': 5
        }
        
        logger.info("Live Monitoring Dashboard initialized")
    
    def load_trader_state(self) -> Optional[Dict[str, Any]]:
        """Load current trading engine state"""
        try:
            if os.path.exists(self.trader_state_file):
                with open(self.trader_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading trader state: {e}")
        return None
    
    def load_oms_state(self) -> Optional[Dict[str, Any]]:
        """Load current order management state"""
        try:
            if os.path.exists(self.oms_state_file):
                with open(self.oms_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading OMS state: {e}")
        return None
    
    def load_config(self) -> Dict[str, Any]:
        """Load trading configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        return {'initial_capital': 100000.0}
    
    def get_current_spy_price(self) -> float:
        """Get current SPY price (simplified)"""
        try:
            import yfinance as yf
            spy = yf.Ticker("SPY")
            hist = spy.history(period="1d", interval="1m")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Error fetching SPY price: {e}")
        return 0.0
    
    def collect_metrics(self) -> Optional[DashboardMetrics]:
        """Collect current system metrics"""
        try:
            trader_state = self.load_trader_state()
            oms_state = self.load_oms_state()
            config = self.load_config()
            
            if not trader_state:
                return None
            
            # Extract metrics
            equity = trader_state.get('paper_equity', 0.0)
            cash = trader_state.get('paper_cash', 0.0)
            initial_capital = config.get('initial_capital', 100000.0)
            
            total_return_pct = ((equity - initial_capital) / initial_capital) * 100
            
            # Position metrics
            positions = trader_state.get('positions', [])
            open_positions = len([p for p in positions if p.get('status') == 'OPEN'])
            total_positions = len(positions)
            
            # Calculate win rate
            closed_positions = [p for p in positions if p.get('status') == 'CLOSED']
            if closed_positions:
                winning_positions = len([p for p in closed_positions if p.get('current_pnl', 0) > 0])
                win_rate = (winning_positions / len(closed_positions)) * 100
            else:
                win_rate = 0.0
            
            # Day P&L (simplified - would need time-series data for accurate calculation)
            metrics = trader_state.get('metrics', {})
            day_pnl = metrics.get('unrealized_pnl', 0.0)
            
            # Order metrics
            active_orders = 0
            if oms_state:
                orders = oms_state.get('orders', [])
                active_orders = len([o for o in orders if o.get('status') in ['PENDING', 'SUBMITTED']])
            
            # System status
            system_status = "RUNNING" if trader_state.get('timestamp') else "UNKNOWN"
            last_update = trader_state.get('timestamp', '')
            if last_update:
                last_dt = datetime.fromisoformat(last_update.replace('Z', ''))
                minutes_since = (datetime.now() - last_dt).total_seconds() / 60
                if minutes_since > 30:  # No update in 30 minutes
                    system_status = "STALE"
            
            return DashboardMetrics(
                timestamp=datetime.now(),
                equity=equity,
                cash=cash,
                total_return_pct=total_return_pct,
                day_pnl=day_pnl,
                open_positions=open_positions,
                total_positions=total_positions,
                win_rate=win_rate,
                active_orders=active_orders,
                system_status=system_status,
                last_signal_check=last_update[:19] if last_update else "N/A",
                current_price=self.get_current_spy_price(),
                in_bull_regime=True  # Would need market data integration
            )
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return None
    
    def check_alerts(self, metrics: DashboardMetrics):
        """Check for alert conditions"""
        try:
            current_time = datetime.now()
            
            # Drawdown alert
            if metrics.total_return_pct < self.alert_thresholds['max_drawdown_pct']:
                self.add_alert("WARNING", f"Drawdown exceeded: {metrics.total_return_pct:.1f}%")
            
            # Win rate alert
            if metrics.win_rate < self.alert_thresholds['min_win_rate'] and metrics.total_positions >= 5:
                self.add_alert("WARNING", f"Low win rate: {metrics.win_rate:.1f}%")
            
            # Position count alert
            if metrics.open_positions > self.alert_thresholds['max_open_positions']:
                self.add_alert("INFO", f"High position count: {metrics.open_positions}")
            
            # System health alert
            if metrics.system_status != "RUNNING":
                self.add_alert("ERROR", f"System status: {metrics.system_status}")
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def add_alert(self, level: str, message: str):
        """Add alert to queue"""
        alert = {
            'timestamp': datetime.now(),
            'level': level,
            'message': message
        }
        self.alerts.append(alert)
        logger.info(f"ALERT [{level}]: {message}")
    
    def format_currency(self, value: float) -> str:
        """Format currency with appropriate color"""
        if value >= 0:
            return f"${value:,.2f}"
        else:
            return f"-${abs(value):,.2f}"
    
    def format_percentage(self, value: float) -> str:
        """Format percentage with appropriate color"""
        return f"{value:+.2f}%"
    
    def draw_header(self, stdscr, y_offset: int = 0):
        """Draw dashboard header"""
        header_lines = [
            "=" * 80,
            "OPERATION BADGER - SPRINT 19 LIVE TRADING DASHBOARD",  
            "Bull Call Spread Strategy - Paper Trading Validation",
            "=" * 80
        ]
        
        for i, line in enumerate(header_lines):
            if y_offset + i < curses.LINES - 1:
                stdscr.addstr(y_offset + i, 0, line[:curses.COLS-1])
        
        return len(header_lines)
    
    def draw_system_status(self, stdscr, metrics: DashboardMetrics, y_offset: int):
        """Draw system status section"""
        if y_offset >= curses.LINES - 1:
            return 0
        
        status_color = curses.color_pair(1) if metrics.system_status == "RUNNING" else curses.color_pair(2)
        
        lines = [
            "",
            "SYSTEM STATUS",
            "-" * 40,
            f"Status: {metrics.system_status}",
            f"Last Update: {metrics.last_signal_check}",
            f"Current SPY: ${metrics.current_price:.2f}",
            f"Bull Regime: {'YES' if metrics.in_bull_regime else 'NO'}",
            f"Active Orders: {metrics.active_orders}"
        ]
        
        for i, line in enumerate(lines):
            if y_offset + i < curses.LINES - 1:
                if i == 3:  # Status line
                    stdscr.addstr(y_offset + i, 0, line[:curses.COLS-1], status_color)
                else:
                    stdscr.addstr(y_offset + i, 0, line[:curses.COLS-1])
        
        return len(lines)
    
    def draw_portfolio_metrics(self, stdscr, metrics: DashboardMetrics, y_offset: int):
        """Draw portfolio performance section"""
        if y_offset >= curses.LINES - 1:
            return 0
        
        return_color = curses.color_pair(1) if metrics.total_return_pct >= 0 else curses.color_pair(2)
        
        lines = [
            "",
            "PORTFOLIO PERFORMANCE",
            "-" * 40,
            f"Total Equity: {self.format_currency(metrics.equity)}",
            f"Available Cash: {self.format_currency(metrics.cash)}",
            f"Total Return: {self.format_percentage(metrics.total_return_pct)}",
            f"Day P&L: {self.format_currency(metrics.day_pnl)}",
            ""
        ]
        
        for i, line in enumerate(lines):
            if y_offset + i < curses.LINES - 1:
                if i == 5:  # Total return line
                    stdscr.addstr(y_offset + i, 0, line[:curses.COLS-1], return_color)
                else:
                    stdscr.addstr(y_offset + i, 0, line[:curses.COLS-1])
        
        return len(lines)
    
    def draw_position_summary(self, stdscr, metrics: DashboardMetrics, y_offset: int):
        """Draw position summary section"""
        if y_offset >= curses.LINES - 1:
            return 0
        
        lines = [
            "POSITION SUMMARY", 
            "-" * 40,
            f"Open Positions: {metrics.open_positions}",
            f"Total Positions: {metrics.total_positions}",
            f"Win Rate: {metrics.win_rate:.1f}%",
            ""
        ]
        
        for i, line in enumerate(lines):
            if y_offset + i < curses.LINES - 1:
                stdscr.addstr(y_offset + i, 0, line[:curses.COLS-1])
        
        return len(lines)
    
    def draw_recent_alerts(self, stdscr, y_offset: int):
        """Draw recent alerts section"""
        if y_offset >= curses.LINES - 1:
            return 0
        
        lines = ["RECENT ALERTS", "-" * 40]
        
        if not self.alerts:
            lines.append("No recent alerts")
        else:
            # Show last 5 alerts
            for alert in list(self.alerts)[-5:]:
                timestamp = alert['timestamp'].strftime('%H:%M:%S')  
                level = alert['level']
                message = alert['message']
                alert_line = f"[{timestamp}] {level}: {message}"
                lines.append(alert_line[:curses.COLS-1])
        
        for i, line in enumerate(lines):
            if y_offset + i < curses.LINES - 1:
                if i >= 2 and len(lines) > 2:  # Alert lines
                    if "ERROR" in line:
                        stdscr.addstr(y_offset + i, 0, line, curses.color_pair(2))
                    elif "WARNING" in line:
                        stdscr.addstr(y_offset + i, 0, line, curses.color_pair(3))
                    else:
                        stdscr.addstr(y_offset + i, 0, line)
                else:
                    stdscr.addstr(y_offset + i, 0, line)
        
        return len(lines)
    
    def draw_footer(self, stdscr, y_offset: int):
        """Draw dashboard footer"""
        if y_offset >= curses.LINES - 2:
            return 0
        
        footer_lines = [
            "",
            f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Press 'q' to quit | Refresh: {self.refresh_interval}s"
        ]
        
        for i, line in enumerate(footer_lines):
            if y_offset + i < curses.LINES - 1:
                stdscr.addstr(y_offset + i, 0, line[:curses.COLS-1])
        
        return len(footer_lines)
    
    def draw_dashboard(self, stdscr):
        """Draw complete dashboard"""
        try:
            stdscr.clear()
            
            if not self.current_metrics:
                stdscr.addstr(0, 0, "Loading metrics...")
                stdscr.refresh()
                return
            
            y_pos = 0
            
            # Draw sections
            y_pos += self.draw_header(stdscr, y_pos)
            y_pos += self.draw_system_status(stdscr, self.current_metrics, y_pos)
            y_pos += self.draw_portfolio_metrics(stdscr, self.current_metrics, y_pos)
            y_pos += self.draw_position_summary(stdscr, self.current_metrics, y_pos)
            y_pos += self.draw_recent_alerts(stdscr, y_pos)
            self.draw_footer(stdscr, y_pos)
            
            stdscr.refresh()
            
        except Exception as e:
            logger.error(f"Error drawing dashboard: {e}")
    
    def update_metrics(self):
        """Update metrics in background thread"""
        while self.running:
            try:
                new_metrics = self.collect_metrics()
                if new_metrics:
                    self.current_metrics = new_metrics
                    self.metrics_history.append(new_metrics)
                    self.check_alerts(new_metrics)
                
                time.sleep(self.refresh_interval)
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                time.sleep(self.refresh_interval)
    
    def run_terminal_dashboard(self):
        """Run the terminal-based dashboard"""
        def signal_handler(signum, frame):
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        def main_loop(stdscr):
            # Initialize colors
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Positive
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Negative/Error
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Warning
            
            # Configure terminal
            stdscr.nodelay(True)
            stdscr.timeout(1000)  # 1 second timeout for getch()
            
            self.screen = stdscr
            self.running = True
            
            # Start metrics update thread
            metrics_thread = threading.Thread(target=self.update_metrics, daemon=True)
            metrics_thread.start()
            
            # Initial metrics load
            self.current_metrics = self.collect_metrics()
            
            # Main display loop
            while self.running:
                try:
                    self.draw_dashboard(stdscr)
                    
                    # Check for quit command
                    ch = stdscr.getch()
                    if ch == ord('q') or ch == ord('Q'):
                        self.running = False
                        break
                    
                    time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                    
                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"Error in main dashboard loop: {e}")
                    time.sleep(1)
        
        try:
            curses.wrapper(main_loop)
        except Exception as e:
            logger.error(f"Error running terminal dashboard: {e}")
        finally:
            self.running = False
    
    def run_console_dashboard(self):
        """Run simple console-based dashboard (fallback)"""
        self.running = True
        
        print("=" * 80)
        print("OPERATION BADGER - LIVE TRADING CONSOLE DASHBOARD")
        print("=" * 80)
        print("Press Ctrl+C to quit")
        print()
        
        try:
            while self.running:
                metrics = self.collect_metrics()
                if metrics:
                    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
                    
                    print("=" * 80)
                    print("BULL CALL SPREAD LIVE TRADING DASHBOARD")
                    print("=" * 80)
                    print(f"Time: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"System Status: {metrics.system_status}")
                    print()
                    print("PORTFOLIO:")
                    print(f"  Equity: {self.format_currency(metrics.equity)}")
                    print(f"  Cash: {self.format_currency(metrics.cash)}")
                    print(f"  Total Return: {self.format_percentage(metrics.total_return_pct)}")
                    print(f"  Day P&L: {self.format_currency(metrics.day_pnl)}")
                    print()
                    print("POSITIONS:")
                    print(f"  Open: {metrics.open_positions}")
                    print(f"  Total: {metrics.total_positions}")
                    print(f"  Win Rate: {metrics.win_rate:.1f}%")
                    print()
                    print("MARKET:")
                    print(f"  SPY Price: ${metrics.current_price:.2f}")
                    print(f"  Bull Regime: {'YES' if metrics.in_bull_regime else 'NO'}")
                    print(f"  Active Orders: {metrics.active_orders}")
                    
                    if self.alerts:
                        print()
                        print("RECENT ALERTS:")
                        for alert in list(self.alerts)[-3:]:
                            timestamp = alert['timestamp'].strftime('%H:%M:%S')
                            print(f"  [{timestamp}] {alert['level']}: {alert['message']}")
                    
                    print()
                    print("Press Ctrl+C to quit")
                
                time.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            self.running = False
            print("\nDashboard stopped by user")
        except Exception as e:
            logger.error(f"Error in console dashboard: {e}")
            print(f"Dashboard error: {e}")
    
    def run(self, use_terminal: bool = True):
        """
        Run the monitoring dashboard
        
        Args:
            use_terminal: Use terminal-based UI if True, console if False
        """
        print("Starting Live Monitoring Dashboard...")
        
        if use_terminal:
            try:
                self.run_terminal_dashboard()
            except Exception as e:
                logger.error(f"Terminal dashboard failed: {e}")
                print("Falling back to console dashboard...")
                self.run_console_dashboard()
        else:
            self.run_console_dashboard()
    
    def generate_daily_report(self) -> str:
        """Generate daily performance report"""
        try:
            metrics = self.collect_metrics()
            if not metrics:
                return "No metrics available for report"
            
            report_lines = [
                "DAILY TRADING REPORT",
                "=" * 50,
                f"Date: {datetime.now().strftime('%Y-%m-%d')}",
                f"Strategy: Bull Call Spread",
                "",
                "PORTFOLIO PERFORMANCE:",
                f"  Total Equity: {self.format_currency(metrics.equity)}",
                f"  Total Return: {self.format_percentage(metrics.total_return_pct)}",
                f"  Day P&L: {self.format_currency(metrics.day_pnl)}",
                "",
                "POSITION SUMMARY:",
                f"  Open Positions: {metrics.open_positions}",
                f"  Total Positions: {metrics.total_positions}",
                f"  Win Rate: {metrics.win_rate:.1f}%",
                "",
                "SYSTEM STATUS:",
                f"  Status: {metrics.system_status}",
                f"  Active Orders: {metrics.active_orders}",
                f"  Last Update: {metrics.last_signal_check}",
                ""
            ]
            
            if self.alerts:
                report_lines.extend([
                    "RECENT ALERTS:",
                    *[f"  [{a['timestamp'].strftime('%H:%M:%S')}] {a['level']}: {a['message']}" 
                      for a in list(self.alerts)[-10:]]
                ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            return f"Error generating report: {e}"


def main():
    """
    Main entry point for monitoring dashboard
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Trading Monitoring Dashboard')
    parser.add_argument('--console', action='store_true', help='Use console mode instead of terminal UI')
    parser.add_argument('--refresh', type=int, default=5, help='Refresh interval in seconds')
    parser.add_argument('--report', action='store_true', help='Generate daily report and exit')
    
    args = parser.parse_args()
    
    dashboard = LiveMonitoringDashboard(refresh_interval=args.refresh)
    
    if args.report:
        report = dashboard.generate_daily_report()
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime('%Y%m%d')
        filename = f"daily_report_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        print(f"\nReport saved to {filename}")
    else:
        dashboard.run(use_terminal=not args.console)


if __name__ == "__main__":
    main()