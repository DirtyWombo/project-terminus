#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 19: Live Trading System Launcher
Launch and manage the complete live trading infrastructure

This script orchestrates the startup and management of all Sprint 19 components:
- Live Trading Engine
- Order Management System  
- Monitoring Dashboard
- System health checks

Usage:
    python launch_sprint19.py --component [trader|dashboard|all]
    python launch_sprint19.py --test-system
    python launch_sprint19.py --status
"""

import os
import sys
import json
import time
import subprocess
import threading
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Sprint19Launcher:
    """
    System launcher and orchestrator for Sprint 19 live trading
    """
    
    def __init__(self):
        self.components = {
            'trader': {
                'script': 'live_trader.py',
                'description': 'Live Trading Engine',
                'process': None,
                'required_files': ['live_trader.py', 'bull_call_spread_strategy.py', 'order_management_system.py']
            },
            'dashboard': {
                'script': 'live_monitoring_dashboard.py',
                'description': 'Live Monitoring Dashboard',
                'process': None,
                'required_files': ['live_monitoring_dashboard.py']
            }
        }
        
        self.required_config_files = [
            'live_trader_config.json'
        ]
        
        logger.info("Sprint 19 Launcher initialized")
    
    def check_system_prerequisites(self) -> bool:
        """Check if all required files and dependencies are present"""
        logger.info("Checking system prerequisites...")
        
        all_good = True
        
        # Check required Python files
        for component_name, component_info in self.components.items():
            for required_file in component_info['required_files']:
                if not os.path.exists(required_file):
                    logger.error(f"Required file missing: {required_file}")
                    all_good = False
                else:
                    logger.debug(f"Found required file: {required_file}")
        
        # Check configuration files
        for config_file in self.required_config_files:
            if not os.path.exists(config_file):
                logger.error(f"Required config file missing: {config_file}")
                all_good = False
            else:
                logger.debug(f"Found config file: {config_file}")
        
        # Check Python dependencies
        required_packages = [
            'yfinance', 'pandas', 'numpy', 'schedule'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                logger.debug(f"Package available: {package}")
            except ImportError:
                logger.error(f"Required package missing: {package}")
                logger.error(f"Install with: pip install {package}")
                all_good = False
        
        if all_good:
            logger.info("[SUCCESS] All system prerequisites satisfied")
        else:
            logger.error("[FAILED] System prerequisites check failed")
        
        return all_good
    
    def validate_configuration(self) -> bool:
        """Validate trading configuration"""
        logger.info("Validating configuration...")
        
        try:
            with open('live_trader_config.json', 'r') as f:
                config = json.load(f)
            
            # Validate required configuration keys
            required_keys = [
                'initial_capital', 'target_dte', 'long_call_delta', 
                'short_call_delta', 'profit_target', 'stop_loss',
                'max_positions', 'contracts_per_trade', 'underlying_symbol'
            ]
            
            for key in required_keys:
                if key not in config:
                    logger.error(f"Missing required config key: {key}")
                    return False
            
            # Validate configuration values
            if config['initial_capital'] <= 0:
                logger.error("Initial capital must be positive")
                return False
            
            if config['max_positions'] <= 0 or config['max_positions'] > 10:
                logger.error("Max positions must be between 1 and 10")
                return False
            
            if not (0 < config['long_call_delta'] < 1 and 0 < config['short_call_delta'] < 1):
                logger.error("Delta values must be between 0 and 1")
                return False
            
            if config['short_call_delta'] >= config['long_call_delta']:
                logger.error("Short call delta must be less than long call delta")
                return False
            
            logger.info("[SUCCESS] Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def create_startup_summary(self) -> str:
        """Create system startup summary"""
        try:
            with open('live_trader_config.json', 'r') as f:
                config = json.load(f)
            
            summary_lines = [
                "=" * 80,
                "SPRINT 19: LIVE PAPER TRADING SYSTEM STARTUP",
                "=" * 80,
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Strategy: Bull Call Spread",
                f"Mode: {'Paper Trading' if config.get('paper_trading', True) else 'LIVE TRADING'}",
                "",
                "STRATEGY CONFIGURATION:",
                f"  Initial Capital: ${config['initial_capital']:,.2f}",
                f"  Target DTE: {config['target_dte']} days",
                f"  Long Call Delta: {config['long_call_delta']:.2f}",
                f"  Short Call Delta: {config['short_call_delta']:.2f}",
                f"  Profit Target: {config['profit_target']:.0%}",
                f"  Stop Loss: {config['stop_loss']:.0%}",
                f"  Max Positions: {config['max_positions']}",
                f"  Contracts per Trade: {config['contracts_per_trade']}",
                f"  Underlying: {config['underlying_symbol']}",
                "",
                "SYSTEM COMPONENTS:",
                f"  [OK] Live Trading Engine",
                f"  [OK] Order Management System",
                f"  [OK] Bull Call Spread Strategy",
                f"  [OK] Live Monitoring Dashboard",
                f"  [OK] Comprehensive Logging",
                "",
                "SUCCESS CRITERIA (30-Day Validation):",
                f"  [TARGET] System Stability: No crashes/restarts",
                f"  [TARGET] Execution Fidelity: >95% signal accuracy",
                f"  [TARGET] Performance Tracking: <10% backtest deviation",
                f"  [TARGET] Order Fill Rate: >90% successful fills",
                "=" * 80
            ]
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            return f"Error creating startup summary: {e}"
    
    def launch_component(self, component_name: str) -> bool:
        """Launch a specific system component"""
        if component_name not in self.components:
            logger.error(f"Unknown component: {component_name}")
            return False
        
        component = self.components[component_name]
        
        if component['process'] is not None:
            logger.warning(f"Component {component_name} is already running")
            return True
        
        try:
            logger.info(f"Launching {component['description']}...")
            
            # Launch component as subprocess
            process = subprocess.Popen(
                [sys.executable, component['script']],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            component['process'] = process
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if process.poll() is None:
                logger.info(f"[SUCCESS] {component['description']} started successfully (PID: {process.pid})")
                return True
            else:
                # Process exited immediately
                stdout, stderr = process.communicate()
                logger.error(f"[FAILED] {component['description']} failed to start")
                if stderr:
                    logger.error(f"Error output: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error launching {component_name}: {e}")
            return False
    
    def stop_component(self, component_name: str) -> bool:
        """Stop a specific system component"""
        if component_name not in self.components:
            logger.error(f"Unknown component: {component_name}")
            return False
        
        component = self.components[component_name]
        
        if component['process'] is None:
            logger.info(f"Component {component_name} is not running")
            return True
        
        try:
            logger.info(f"Stopping {component['description']}...")
            
            # Terminate process
            component['process'].terminate()
            
            # Wait for termination
            try:
                component['process'].wait(timeout=10)
                logger.info(f"[SUCCESS] {component['description']} stopped successfully")
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop gracefully
                logger.warning(f"Force killing {component['description']}...")
                component['process'].kill()
                component['process'].wait()
                logger.info(f"[SUCCESS] {component['description']} force stopped")
            
            component['process'] = None
            return True
            
        except Exception as e:
            logger.error(f"Error stopping {component_name}: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Dict]:
        """Get current status of all components"""
        status = {}
        
        for component_name, component_info in self.components.items():
            if component_info['process'] is None:
                status[component_name] = {
                    'status': 'STOPPED',
                    'pid': None,
                    'description': component_info['description']
                }
            else:
                if component_info['process'].poll() is None:
                    status[component_name] = {
                        'status': 'RUNNING',
                        'pid': component_info['process'].pid,
                        'description': component_info['description']
                    }
                else:
                    status[component_name] = {
                        'status': 'CRASHED',
                        'pid': None,
                        'description': component_info['description']
                    }
                    component_info['process'] = None
        
        return status
    
    def print_system_status(self):
        """Print formatted system status"""
        status = self.get_system_status()
        
        print("\n" + "=" * 60)
        print("SPRINT 19 SYSTEM STATUS")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for component_name, component_status in status.items():
            status_color = component_status['status']
            pid_info = f" (PID: {component_status['pid']})" if component_status['pid'] else ""
            
            print(f"{component_status['description']:.<40} {status_color}{pid_info}")
        
        print("=" * 60)
    
    def test_system_integration(self) -> bool:
        """Test system integration and connectivity"""
        logger.info("Testing system integration...")
        
        tests_passed = 0
        total_tests = 4
        
        # Test 1: Strategy import
        try:
            from bull_call_spread_strategy import BullCallSpreadStrategy
            logger.info("[SUCCESS] Bull Call Spread strategy import successful")
            tests_passed += 1
        except Exception as e:
            logger.error(f"✗ Strategy import failed: {e}")
        
        # Test 2: OMS import
        try:
            from order_management_system import OrderManagementSystem
            oms = OrderManagementSystem()
            logger.info("[SUCCESS] Order Management System initialization successful")
            tests_passed += 1
        except Exception as e:
            logger.error(f"✗ OMS initialization failed: {e}")
        
        # Test 3: Market data connectivity
        try:
            import yfinance as yf
            data = yf.download("SPY", period="1d", progress=False)
            if not data.empty:
                logger.info("[SUCCESS] Market data connectivity successful")
                tests_passed += 1
            else:
                logger.error("✗ Market data connectivity failed - no data")
        except Exception as e:
            logger.error(f"✗ Market data test failed: {e}")
        
        # Test 4: Configuration validation
        if self.validate_configuration():
            tests_passed += 1
        
        success_rate = (tests_passed / total_tests) * 100
        logger.info(f"System integration test: {tests_passed}/{total_tests} tests passed ({success_rate:.0f}%)")
        
        return tests_passed == total_tests
    
    def launch_full_system(self) -> bool:
        """Launch the complete trading system"""
        logger.info("Launching complete Sprint 19 trading system...")
        
        # Print startup summary
        print(self.create_startup_summary())
        
        # Launch trader first
        if not self.launch_component('trader'):
            logger.error("Failed to launch trading engine - aborting")
            return False
        
        # Wait a moment for trader to initialize
        time.sleep(5)
        
        # Launch dashboard
        logger.info("Launching dashboard in 5 seconds...")
        logger.info("Note: Dashboard will run in terminal mode. Press 'q' to quit dashboard.")
        time.sleep(5)
        
        if not self.launch_component('dashboard'):
            logger.warning("Dashboard failed to launch - continuing with trader only")
        
        return True
    
    def shutdown_all(self):
        """Shutdown all system components"""
        logger.info("Shutting down all system components...")
        
        for component_name in self.components.keys():
            self.stop_component(component_name)
        
        logger.info("System shutdown complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Sprint 19 Live Trading System Launcher')
    parser.add_argument('--component', choices=['trader', 'dashboard', 'all'], 
                       default='all', help='Component to launch')
    parser.add_argument('--test-system', action='store_true', 
                       help='Run system integration tests')
    parser.add_argument('--status', action='store_true', 
                       help='Show system status')
    parser.add_argument('--stop', action='store_true',
                       help='Stop all components')
    
    args = parser.parse_args()
    
    launcher = Sprint19Launcher()
    
    # Handle different command modes
    if args.status:
        launcher.print_system_status()
        return 0
    
    if args.stop:
        launcher.shutdown_all()
        return 0
    
    if args.test_system:
        print("Running system integration tests...")
        if launcher.test_system_integration():
            print("[SUCCESS] All integration tests passed - system ready for deployment")
            return 0
        else:
            print("[FAILED] Integration tests failed - resolve issues before deployment")
            return 1
    
    # Check prerequisites
    if not launcher.check_system_prerequisites():
        logger.error("Prerequisites check failed - cannot launch")
        return 1
    
    # Launch requested components
    try:
        if args.component == 'all':
            success = launcher.launch_full_system()
        elif args.component == 'trader':
            success = launcher.launch_component('trader')
        elif args.component == 'dashboard':
            success = launcher.launch_component('dashboard')
        
        if success:
            print("\nSystem launched successfully!")
            print("Monitor system status with: python launch_sprint19.py --status")
            print("Stop system with: python launch_sprint19.py --stop")
            
            # Keep launcher running for monitoring
            if args.component == 'all':
                try:
                    while True:
                        time.sleep(10)
                        # Check for crashed components
                        status = launcher.get_system_status()
                        for comp_name, comp_status in status.items():
                            if comp_status['status'] == 'CRASHED':
                                logger.error(f"Component {comp_name} has crashed!")
                except KeyboardInterrupt:
                    logger.info("Shutdown requested by user")
                    launcher.shutdown_all()
            
            return 0
        else:
            logger.error("System launch failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Launch interrupted by user")
        launcher.shutdown_all()
        return 0
    except Exception as e:
        logger.error(f"Launch error: {e}")
        launcher.shutdown_all()
        return 1


if __name__ == "__main__":
    exit(main())