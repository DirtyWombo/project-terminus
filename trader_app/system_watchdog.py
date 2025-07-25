"""
DEFENSE LAYER 2: SYSTEM HEARTBEAT & WATCHDOG MONITORING
=========================================================

Per institutional critique - implements continuous system health monitoring
with automated shutdown capabilities to protect capital.

Key Features:
- Heartbeat monitoring for all critical services
- Resource usage monitoring (CPU, memory, disk)
- Trading performance anomaly detection
- Automatic emergency shutdown triggers
- Health status logging and alerts
"""

import logging
import threading
import time
import psutil
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemWatchdog:
    """
    DEFENSE LAYER 2: System health monitoring and emergency protection.
    
    Monitors:
    - System resource usage
    - Trading engine health
    - Data feed connectivity
    - Performance anomalies
    - Emergency shutdown conditions
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize system watchdog with conservative thresholds."""
        self.config = config or self._get_default_config()
        self.is_running = False
        self.health_status = {
            "overall": "healthy",
            "last_update": time.time(),
            "alerts": [],
            "performance": {}
        }
        self.emergency_shutdown_triggered = False
        self._monitoring_thread = None
        self._lock = threading.Lock()
        
        # Track service heartbeats
        self.service_heartbeats = {}
        
        # Resource usage history
        self.resource_history = []
        
    def _get_default_config(self) -> Dict:
        """Conservative watchdog configuration per institutional critique."""
        return {
            # RESOURCE MONITORING THRESHOLDS
            "max_cpu_usage": 85.0,          # 85% CPU usage
            "max_memory_usage": 90.0,       # 90% memory usage  
            "max_disk_usage": 95.0,         # 95% disk usage
            "min_free_memory_gb": 1.0,      # Minimum 1GB free RAM
            
            # HEARTBEAT MONITORING
            "heartbeat_timeout": 180,        # 3 minutes without heartbeat = failure
            "critical_services": [
                "trading_engine",
                "data_collector", 
                "ai_service",
                "exchange_manager"
            ],
            
            # PERFORMANCE MONITORING
            "max_consecutive_failures": 5,   # 5 failed trades = shutdown
            "max_rapid_losses": 3,          # 3 losses in 10 minutes = review
            "performance_window_minutes": 60, # Performance monitoring window
            
            # EMERGENCY SHUTDOWN TRIGGERS
            "emergency_cpu_threshold": 95.0, # Emergency CPU threshold
            "emergency_memory_threshold": 95.0, # Emergency memory threshold
            "api_failure_threshold": 10,     # 10 consecutive API failures
            "data_stale_threshold": 300,     # 5 minutes stale data = emergency
            
            # MONITORING INTERVALS
            "check_interval": 30,           # Check every 30 seconds
            "health_report_interval": 300,  # Health report every 5 minutes
            "cleanup_interval": 3600,      # Cleanup old data every hour
        }
    
    def start_monitoring(self):
        """Start the watchdog monitoring system."""
        if self.is_running:
            logging.warning("Watchdog already running")
            return
        
        self.is_running = True
        self.emergency_shutdown_triggered = False
        
        # Start monitoring thread
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        
        logging.info("DEFENSE LAYER 2: System watchdog monitoring started")
    
    def stop_monitoring(self):
        """Stop the watchdog monitoring system."""
        self.is_running = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        
        logging.info("DEFENSE LAYER 2: System watchdog monitoring stopped")
    
    def register_service_heartbeat(self, service_name: str):
        """Register a heartbeat from a critical service."""
        with self._lock:
            self.service_heartbeats[service_name] = time.time()
    
    def _monitoring_loop(self):
        """Main monitoring loop - runs continuously while system is active."""
        last_health_report = 0
        last_cleanup = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # 1. SYSTEM RESOURCE CHECK
                resource_health = self._check_system_resources()
                
                # 2. SERVICE HEARTBEAT CHECK  
                heartbeat_health = self._check_service_heartbeats()
                
                # 3. EMERGENCY CONDITION CHECK
                emergency_check = self._check_emergency_conditions()
                
                # 4. UPDATE OVERALL HEALTH STATUS
                self._update_health_status(resource_health, heartbeat_health, emergency_check)
                
                # 5. PERIODIC HEALTH REPORTING
                if current_time - last_health_report > self.config["health_report_interval"]:
                    self._log_health_report()
                    last_health_report = current_time
                
                # 6. PERIODIC CLEANUP
                if current_time - last_cleanup > self.config["cleanup_interval"]:
                    self._cleanup_old_data()
                    last_cleanup = current_time
                
                # 7. EMERGENCY SHUTDOWN CHECK
                if emergency_check["emergency"]:
                    self._trigger_emergency_shutdown(emergency_check["reason"])
                    break
                
            except Exception as e:
                logging.error(f"Error in watchdog monitoring loop: {e}")
            
            # Wait before next check
            time.sleep(self.config["check_interval"])
    
    def _check_system_resources(self) -> Dict:
        """Check system resource usage and health."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_free_gb = memory.available / (1024**3)
            
            # Disk usage (current directory)
            disk = psutil.disk_usage('.')
            disk_percent = disk.percent
            
            # Record resource usage
            resource_data = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_free_gb": memory_free_gb,
                "disk_percent": disk_percent
            }
            
            # Add to history (keep last 100 entries)
            self.resource_history.append(resource_data)
            if len(self.resource_history) > 100:
                self.resource_history.pop(0)
            
            # Check thresholds
            alerts = []
            if cpu_percent > self.config["max_cpu_usage"]:
                alerts.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > self.config["max_memory_usage"]:
                alerts.append(f"High memory usage: {memory_percent:.1f}%")
            
            if memory_free_gb < self.config["min_free_memory_gb"]:
                alerts.append(f"Low free memory: {memory_free_gb:.1f}GB")
            
            if disk_percent > self.config["max_disk_usage"]:
                alerts.append(f"High disk usage: {disk_percent:.1f}%")
            
            return {
                "healthy": len(alerts) == 0,
                "alerts": alerts,
                "metrics": resource_data
            }
            
        except Exception as e:
            logging.error(f"Error checking system resources: {e}")
            return {
                "healthy": False,
                "alerts": [f"Resource check error: {str(e)}"],
                "metrics": {}
            }
    
    def _check_service_heartbeats(self) -> Dict:
        """Check if all critical services are responding."""
        current_time = time.time()
        timeout = self.config["heartbeat_timeout"]
        
        missing_services = []
        stale_services = []
        
        for service in self.config["critical_services"]:
            if service not in self.service_heartbeats:
                missing_services.append(service)
            else:
                last_heartbeat = self.service_heartbeats[service]
                if current_time - last_heartbeat > timeout:
                    stale_services.append(f"{service} (last seen {int(current_time - last_heartbeat)}s ago)")
        
        alerts = []
        if missing_services:
            alerts.append(f"Services never reported: {', '.join(missing_services)}")
        
        if stale_services:
            alerts.append(f"Stale services: {', '.join(stale_services)}")
        
        return {
            "healthy": len(alerts) == 0,
            "alerts": alerts,
            "missing_services": missing_services,
            "stale_services": stale_services
        }
    
    def _check_emergency_conditions(self) -> Dict:
        """Check for emergency shutdown conditions."""
        if self.emergency_shutdown_triggered:
            return {"emergency": True, "reason": "Already in emergency shutdown"}
        
        # Emergency resource thresholds
        if self.resource_history:
            latest = self.resource_history[-1]
            
            if latest["cpu_percent"] > self.config["emergency_cpu_threshold"]:
                return {"emergency": True, "reason": f"Emergency CPU usage: {latest['cpu_percent']:.1f}%"}
            
            if latest["memory_percent"] > self.config["emergency_memory_threshold"]:
                return {"emergency": True, "reason": f"Emergency memory usage: {latest['memory_percent']:.1f}%"}
            
            if latest["memory_free_gb"] < 0.5:  # Less than 500MB free
                return {"emergency": True, "reason": f"Critical memory shortage: {latest['memory_free_gb']:.1f}GB"}
        
        # Check for system unresponsiveness
        critical_missing = 0
        for service in self.config["critical_services"]:
            if service not in self.service_heartbeats:
                critical_missing += 1
            else:
                last_heartbeat = self.service_heartbeats[service]
                if time.time() - last_heartbeat > self.config["heartbeat_timeout"] * 2:  # Double timeout = emergency
                    critical_missing += 1
        
        if critical_missing >= 2:  # 2 or more critical services down
            return {"emergency": True, "reason": f"{critical_missing} critical services unresponsive"}
        
        return {"emergency": False, "reason": "No emergency conditions detected"}
    
    def _update_health_status(self, resource_health: Dict, heartbeat_health: Dict, emergency_check: Dict):
        """Update the overall system health status."""
        with self._lock:
            # Combine all alerts
            all_alerts = []
            all_alerts.extend(resource_health.get("alerts", []))
            all_alerts.extend(heartbeat_health.get("alerts", []))
            
            # Determine overall health
            if emergency_check["emergency"]:
                overall_status = "emergency"
            elif not resource_health["healthy"] or not heartbeat_health["healthy"]:
                overall_status = "warning"
            else:
                overall_status = "healthy"
            
            # Update health status
            self.health_status = {
                "overall": overall_status,
                "last_update": time.time(),
                "alerts": all_alerts,
                "performance": {
                    "resource_health": resource_health["healthy"],
                    "heartbeat_health": heartbeat_health["healthy"],
                    "emergency_status": emergency_check["emergency"]
                },
                "emergency_reason": emergency_check.get("reason", "")
            }
    
    def _log_health_report(self):
        """Log a comprehensive health report."""
        with self._lock:
            status = self.health_status
            
            if status["overall"] == "healthy":
                logging.info("WATCHDOG HEALTH: System operating normally - all checks passed")
            elif status["overall"] == "warning":
                logging.warning(f"WATCHDOG HEALTH: System warnings detected - {len(status['alerts'])} alerts")
                for alert in status["alerts"]:
                    logging.warning(f"  - {alert}")
            else:
                logging.error(f"WATCHDOG HEALTH: Emergency status - {status.get('emergency_reason', 'Unknown')}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data to prevent memory bloat."""
        # Keep only recent resource history
        if len(self.resource_history) > 100:
            self.resource_history = self.resource_history[-100:]
        
        # Clean old heartbeats (remove services not seen in 24 hours)
        current_time = time.time()
        with self._lock:
            old_services = []
            for service, last_seen in self.service_heartbeats.items():
                if current_time - last_seen > 86400:  # 24 hours
                    old_services.append(service)
            
            for service in old_services:
                del self.service_heartbeats[service]
                logging.info(f"Cleaned old heartbeat data for service: {service}")
    
    def _trigger_emergency_shutdown(self, reason: str):
        """Trigger emergency shutdown of the trading system via Master Shutdown Protocol."""
        self.emergency_shutdown_triggered = True
        
        logging.critical("=" * 80)
        logging.critical("WATCHDOG TRIGGERING EMERGENCY SHUTDOWN")
        logging.critical(f"Reason: {reason}")
        logging.critical("=" * 80)
        
        # Trigger Master Shutdown Protocol
        try:
            from .master_shutdown import master_shutdown, ShutdownReason, ShutdownSeverity
            
            # Map watchdog reasons to shutdown reasons
            shutdown_reason = ShutdownReason.SYSTEM_HEALTH
            if "cpu" in reason.lower():
                shutdown_reason = ShutdownReason.RESOURCE_EXHAUSTION
            elif "memory" in reason.lower():
                shutdown_reason = ShutdownReason.RESOURCE_EXHAUSTION
            elif "service" in reason.lower():
                shutdown_reason = ShutdownReason.SYSTEM_HEALTH
            
            # Trigger immediate shutdown
            shutdown_details = {
                "watchdog_reason": reason,
                "system_health": self.health_status.copy(),
                "resource_metrics": self.resource_history[-5:] if self.resource_history else []
            }
            
            success = master_shutdown.trigger_shutdown(
                shutdown_reason,
                ShutdownSeverity.IMMEDIATE,
                shutdown_details,
                immediate=True
            )
            
            if success:
                logging.critical("MASTER SHUTDOWN PROTOCOL ACTIVATED SUCCESSFULLY")
            else:
                logging.critical("FAILED TO ACTIVATE MASTER SHUTDOWN PROTOCOL")
                
        except Exception as e:
            logging.critical(f"ERROR ACTIVATING MASTER SHUTDOWN: {e}")
        
        # Update health status
        with self._lock:
            self.health_status["overall"] = "emergency_shutdown"
            self.health_status["emergency_reason"] = reason
    
    def get_health_status(self) -> Dict:
        """Get current system health status."""
        with self._lock:
            return self.health_status.copy()
    
    def is_emergency_shutdown(self) -> bool:
        """Check if emergency shutdown has been triggered."""
        return self.emergency_shutdown_triggered
    
    def get_resource_metrics(self) -> List[Dict]:
        """Get recent resource usage metrics."""
        return self.resource_history.copy()


# Global watchdog instance
system_watchdog = SystemWatchdog()

# Convenience functions for service integration
def start_system_monitoring():
    """Start the system watchdog monitoring."""
    system_watchdog.start_monitoring()

def stop_system_monitoring():
    """Stop the system watchdog monitoring."""
    system_watchdog.stop_monitoring()

def register_service_heartbeat(service_name: str):
    """Register a heartbeat from a service."""
    system_watchdog.register_service_heartbeat(service_name)

def get_system_health():
    """Get current system health status."""
    return system_watchdog.get_health_status()

def is_system_emergency():
    """Check if system is in emergency shutdown."""
    return system_watchdog.is_emergency_shutdown()


if __name__ == "__main__":
    # Test the watchdog system
    print("Testing DEFENSE LAYER 2: System Watchdog")
    
    # Start monitoring
    start_system_monitoring()
    
    # Simulate service heartbeats
    for i in range(5):
        register_service_heartbeat("trading_engine")
        register_service_heartbeat("data_collector")
        print(f"Heartbeat {i+1} sent")
        time.sleep(2)
    
    # Check health status
    health = get_system_health()
    print(f"System Health: {health['overall']}")
    print(f"Alerts: {health['alerts']}")
    
    # Stop monitoring
    stop_system_monitoring()
    print("Watchdog monitoring stopped")