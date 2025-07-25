"""
MASTER SHUTDOWN PROTOCOL
========================

Per institutional critique - implements comprehensive emergency shutdown
capabilities to protect capital during system failures or market emergencies.

The Master Shutdown Protocol is the ultimate defense mechanism that can:
1. Immediately halt all trading operations
2. Close all open positions (if safe to do so)
3. Cancel all pending orders
4. Lock the system in safe mode
5. Send emergency notifications to operators
6. Save system state for post-mortem analysis

This system implements multiple shutdown triggers:
- Manual emergency shutdown
- Automatic triggered shutdowns (watchdog, drawdown, etc.)
- Market emergency shutdowns (flash crashes, API failures)
- System health emergency shutdowns (resource exhaustion)
"""

import logging
import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ShutdownReason(Enum):
    """Enumeration of possible shutdown reasons."""
    MANUAL = "manual_operator_initiated"
    PORTFOLIO_DRAWDOWN = "portfolio_drawdown_exceeded"
    SYSTEM_HEALTH = "system_health_failure"
    MARKET_EMERGENCY = "market_emergency_detected"
    API_FAILURE = "exchange_api_failure"
    DATA_STALENESS = "market_data_stale"
    RESOURCE_EXHAUSTION = "system_resource_exhaustion"
    TRADING_ERRORS = "consecutive_trading_errors"
    SECURITY_BREACH = "security_threat_detected"
    UNKNOWN = "unknown_trigger"

class ShutdownSeverity(Enum):
    """Shutdown severity levels."""
    GRACEFUL = "graceful"        # Normal shutdown, close positions safely
    IMMEDIATE = "immediate"      # Fast shutdown, cancel orders only
    EMERGENCY = "emergency"      # Instant shutdown, no position closing

class MasterShutdownProtocol:
    """
    MASTER SHUTDOWN PROTOCOL
    
    The ultimate trading system safety mechanism that can immediately
    halt all operations and protect capital during emergencies.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the master shutdown protocol."""
        self.config = config or self._get_default_config()
        self.is_shutdown = False
        self.shutdown_reason = None
        self.shutdown_time = None
        self.shutdown_severity = None
        self.shutdown_data = {}
        self._lock = threading.Lock()
        
        # Callback functions for different shutdown actions
        self.shutdown_callbacks = {
            'halt_trading': [],
            'cancel_orders': [],
            'close_positions': [],
            'send_alerts': [],
            'save_state': []
        }
        
        # Shutdown triggers and their enabled status
        self.triggers_enabled = {
            'portfolio_drawdown': True,
            'system_health': True,
            'market_emergency': True,
            'api_failure': True,
            'data_staleness': True,
            'resource_exhaustion': True,
            'trading_errors': True,
            'security_breach': True
        }
        
        # Shutdown statistics
        self.shutdown_history = []
        
    def _get_default_config(self) -> Dict:
        """Default master shutdown configuration."""
        return {
            # SHUTDOWN TRIGGERS
            "max_portfolio_drawdown": 0.20,        # 20% max drawdown
            "max_consecutive_errors": 10,          # 10 consecutive trading errors
            "max_api_failures": 15,               # 15 consecutive API failures
            "max_data_staleness_minutes": 10,     # 10 minutes stale data
            "critical_memory_threshold_gb": 0.5,  # 500MB critical memory
            "critical_cpu_threshold": 98.0,       # 98% critical CPU
            
            # SHUTDOWN BEHAVIOR
            "default_severity": "immediate",       # Default shutdown severity
            "position_close_timeout": 60,         # 60 seconds to close positions
            "order_cancel_timeout": 30,           # 30 seconds to cancel orders
            "state_save_timeout": 10,             # 10 seconds to save state
            
            # NOTIFICATIONS
            "emergency_contacts": [],              # Emergency contact list
            "slack_emergency_channel": None,      # Emergency Slack channel
            "webhook_urls": [],                   # Emergency webhook URLs
            
            # RECOVERY
            "auto_recovery_enabled": False,       # Auto-recovery disabled by default
            "recovery_grace_period": 3600,       # 1 hour before allowing recovery
            "manual_override_required": True,    # Require manual override for recovery
            
            # LOGGING
            "shutdown_log_file": "master_shutdown.log",
            "detailed_logging": True,
            "save_system_snapshot": True
        }
    
    def register_shutdown_callback(self, action: str, callback: Callable):
        """Register a callback function for shutdown actions."""
        if action in self.shutdown_callbacks:
            self.shutdown_callbacks[action].append(callback)
            logging.info(f"Registered shutdown callback for action: {action}")
        else:
            logging.error(f"Invalid shutdown action: {action}")
    
    def trigger_shutdown(
        self, 
        reason: ShutdownReason, 
        severity: ShutdownSeverity = None,
        details: Dict = None,
        immediate: bool = False
    ) -> bool:
        """
        Trigger the master shutdown protocol.
        
        Args:
            reason: The reason for shutdown
            severity: Shutdown severity level
            details: Additional shutdown details
            immediate: Skip checks and shutdown immediately
            
        Returns:
            bool: True if shutdown was successful
        """
        with self._lock:
            # Check if already shutdown
            if self.is_shutdown:
                logging.warning(f"Shutdown already in progress. Current reason: {self.shutdown_reason}")
                return False
            
            # Validate shutdown trigger
            if not immediate and not self._validate_shutdown_trigger(reason):
                logging.warning(f"Shutdown trigger validation failed for reason: {reason}")
                return False
            
            # Set shutdown state
            self.is_shutdown = True
            self.shutdown_reason = reason
            self.shutdown_time = datetime.now()
            self.shutdown_severity = severity or ShutdownSeverity(self.config["default_severity"])
            self.shutdown_data = details or {}
            
            logging.critical("="*80)
            logging.critical("MASTER SHUTDOWN PROTOCOL ACTIVATED")
            logging.critical(f"Reason: {reason.value}")
            logging.critical(f"Severity: {self.shutdown_severity.value}")
            logging.critical(f"Time: {self.shutdown_time}")
            logging.critical(f"Details: {details}")
            logging.critical("="*80)
            
            # Execute shutdown sequence
            success = self._execute_shutdown_sequence()
            
            # Log shutdown to history
            self._log_shutdown_to_history(success)
            
            return success
    
    def _validate_shutdown_trigger(self, reason: ShutdownReason) -> bool:
        """Validate if the shutdown trigger is enabled and appropriate."""
        # Map shutdown reasons to trigger names
        trigger_map = {
            ShutdownReason.PORTFOLIO_DRAWDOWN: 'portfolio_drawdown',
            ShutdownReason.SYSTEM_HEALTH: 'system_health',
            ShutdownReason.MARKET_EMERGENCY: 'market_emergency',
            ShutdownReason.API_FAILURE: 'api_failure',
            ShutdownReason.DATA_STALENESS: 'data_staleness',
            ShutdownReason.RESOURCE_EXHAUSTION: 'resource_exhaustion',
            ShutdownReason.TRADING_ERRORS: 'trading_errors',
            ShutdownReason.SECURITY_BREACH: 'security_breach'
        }
        
        trigger_name = trigger_map.get(reason)
        if trigger_name:
            return self.triggers_enabled.get(trigger_name, True)
        
        # Manual and unknown shutdowns are always allowed
        return True
    
    def _execute_shutdown_sequence(self) -> bool:
        """Execute the complete shutdown sequence."""
        try:
            sequence_start = time.time()
            
            # Phase 1: Immediate halt of new trading
            logging.critical("SHUTDOWN PHASE 1: Halting all new trading operations")
            self._execute_callbacks('halt_trading')
            
            # Phase 2: Cancel pending orders (if not emergency severity)
            if self.shutdown_severity != ShutdownSeverity.EMERGENCY:
                logging.critical("SHUTDOWN PHASE 2: Cancelling all pending orders")
                self._execute_callbacks('cancel_orders')
            
            # Phase 3: Close positions (only for graceful shutdown)
            if self.shutdown_severity == ShutdownSeverity.GRACEFUL:
                logging.critical("SHUTDOWN PHASE 3: Closing all open positions")
                self._execute_callbacks('close_positions')
            
            # Phase 4: Send emergency notifications
            logging.critical("SHUTDOWN PHASE 4: Sending emergency notifications")
            self._execute_callbacks('send_alerts')
            
            # Phase 5: Save system state
            logging.critical("SHUTDOWN PHASE 5: Saving system state")
            self._execute_callbacks('save_state')
            self._save_shutdown_state()
            
            sequence_duration = time.time() - sequence_start
            logging.critical(f"MASTER SHUTDOWN COMPLETED in {sequence_duration:.2f} seconds")
            
            return True
            
        except Exception as e:
            logging.critical(f"CRITICAL ERROR during shutdown sequence: {e}")
            return False
    
    def _execute_callbacks(self, action: str):
        """Execute all registered callbacks for a specific action."""
        callbacks = self.shutdown_callbacks.get(action, [])
        
        for callback in callbacks:
            try:
                callback(self.shutdown_reason, self.shutdown_severity, self.shutdown_data)
                logging.info(f"Successfully executed {action} callback")
            except Exception as e:
                logging.error(f"Error executing {action} callback: {e}")
    
    def _save_shutdown_state(self):
        """Save detailed shutdown state for analysis."""
        try:
            shutdown_state = {
                "shutdown_time": self.shutdown_time.isoformat(),
                "reason": self.shutdown_reason.value,
                "severity": self.shutdown_severity.value,
                "details": self.shutdown_data,
                "system_info": self._get_system_snapshot(),
                "config": self.config.copy()
            }
            
            # Save to file
            timestamp = self.shutdown_time.strftime("%Y%m%d_%H%M%S")
            filename = f"shutdown_state_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(shutdown_state, f, indent=2, default=str)
            
            logging.info(f"Shutdown state saved to: {filename}")
            
        except Exception as e:
            logging.error(f"Error saving shutdown state: {e}")
    
    def _get_system_snapshot(self) -> Dict:
        """Get a snapshot of current system state."""
        try:
            import psutil
            
            # Basic system info
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('.').percent,
                "process_count": len(psutil.pids()),
                "uptime_seconds": time.time() - psutil.boot_time()
            }
            
            # Try to get trading-specific info
            try:
                from .system_watchdog import get_system_health
                snapshot["watchdog_health"] = get_system_health()
            except:
                pass
            
            return snapshot
            
        except Exception as e:
            logging.error(f"Error creating system snapshot: {e}")
            return {"error": str(e)}
    
    def _log_shutdown_to_history(self, success: bool):
        """Log the shutdown event to history."""
        history_entry = {
            "timestamp": self.shutdown_time.isoformat(),
            "reason": self.shutdown_reason.value,
            "severity": self.shutdown_severity.value,
            "success": success,
            "details": self.shutdown_data.copy()
        }
        
        self.shutdown_history.append(history_entry)
        
        # Keep only last 100 shutdown events
        if len(self.shutdown_history) > 100:
            self.shutdown_history.pop(0)
    
    def manual_shutdown(self, operator: str = "unknown", reason: str = "manual_intervention"):
        """Trigger a manual shutdown by an operator."""
        details = {
            "operator": operator,
            "manual_reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.trigger_shutdown(
            ShutdownReason.MANUAL, 
            ShutdownSeverity.GRACEFUL,
            details
        )
    
    def emergency_shutdown(self, emergency_reason: str):
        """Trigger an immediate emergency shutdown."""
        details = {
            "emergency_reason": emergency_reason,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.trigger_shutdown(
            ShutdownReason.UNKNOWN,
            ShutdownSeverity.EMERGENCY,
            details,
            immediate=True
        )
    
    def is_system_shutdown(self) -> bool:
        """Check if the system is currently in shutdown state."""
        return self.is_shutdown
    
    def get_shutdown_status(self) -> Dict:
        """Get current shutdown status and details."""
        with self._lock:
            if not self.is_shutdown:
                return {"shutdown": False, "operational": True}
            
            return {
                "shutdown": True,
                "operational": False,
                "reason": self.shutdown_reason.value if self.shutdown_reason else "unknown",
                "severity": self.shutdown_severity.value if self.shutdown_severity else "unknown",
                "shutdown_time": self.shutdown_time.isoformat() if self.shutdown_time else None,
                "details": self.shutdown_data.copy()
            }
    
    def attempt_recovery(self, operator: str, override_code: str = None) -> bool:
        """Attempt to recover from shutdown state (requires manual override)."""
        if not self.is_shutdown:
            logging.info("System not in shutdown state, no recovery needed")
            return True
        
        if self.config["manual_override_required"] and not override_code:
            logging.error("Manual override code required for recovery")
            return False
        
        # Check grace period
        if self.shutdown_time:
            grace_period = self.config["recovery_grace_period"]
            time_since_shutdown = (datetime.now() - self.shutdown_time).total_seconds()
            
            if time_since_shutdown < grace_period:
                logging.error(f"Recovery blocked: {grace_period - time_since_shutdown:.0f}s remaining in grace period")
                return False
        
        # Reset shutdown state
        with self._lock:
            self.is_shutdown = False
            self.shutdown_reason = None
            self.shutdown_time = None
            self.shutdown_severity = None
            self.shutdown_data = {}
        
        logging.warning(f"SYSTEM RECOVERY: Shutdown state cleared by operator: {operator}")
        return True
    
    def get_shutdown_history(self) -> List[Dict]:
        """Get the history of shutdown events."""
        return self.shutdown_history.copy()
    
    def disable_trigger(self, trigger_name: str):
        """Disable a specific shutdown trigger."""
        if trigger_name in self.triggers_enabled:
            self.triggers_enabled[trigger_name] = False
            logging.warning(f"Shutdown trigger disabled: {trigger_name}")
    
    def enable_trigger(self, trigger_name: str):
        """Enable a specific shutdown trigger."""
        if trigger_name in self.triggers_enabled:
            self.triggers_enabled[trigger_name] = True
            logging.info(f"Shutdown trigger enabled: {trigger_name}")


# Global master shutdown instance
master_shutdown = MasterShutdownProtocol()

# Convenience functions for easy integration
def trigger_emergency_shutdown(reason: str):
    """Trigger an immediate emergency shutdown."""
    return master_shutdown.emergency_shutdown(reason)

def trigger_manual_shutdown(operator: str = "system", reason: str = "manual"):
    """Trigger a manual graceful shutdown."""
    return master_shutdown.manual_shutdown(operator, reason)

def is_system_operational() -> bool:
    """Check if the system is operational (not shutdown)."""
    return not master_shutdown.is_system_shutdown()

def get_shutdown_status() -> Dict:
    """Get current shutdown status."""
    return master_shutdown.get_shutdown_status()

def register_shutdown_callback(action: str, callback: Callable):
    """Register a callback for shutdown actions."""
    master_shutdown.register_shutdown_callback(action, callback)


if __name__ == "__main__":
    # Test the master shutdown protocol
    print("Testing MASTER SHUTDOWN PROTOCOL")
    
    # Test manual shutdown
    print("\n1. Testing manual shutdown...")
    success = trigger_manual_shutdown("test_operator", "testing_shutdown_system")
    print(f"Manual shutdown success: {success}")
    
    # Check status
    status = get_shutdown_status()
    print(f"Shutdown status: {status}")
    
    # Test recovery
    print("\n2. Testing recovery...")
    recovery_success = master_shutdown.attempt_recovery("test_operator", "override123")
    print(f"Recovery success: {recovery_success}")
    
    # Check operational status
    print(f"System operational: {is_system_operational()}")
    
    print("\nMaster shutdown protocol test completed")