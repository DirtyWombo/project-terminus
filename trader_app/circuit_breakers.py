"""
Circuit Breakers System
======================

Advanced circuit breaker system to halt trading under dangerous conditions:
1. Volatility spike breakers
2. API health monitoring
3. Stale data detection
4. Market anomaly detection
5. System health monitoring
"""

import logging
import time
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)

class BreakStatus(Enum):
    """Circuit breaker status enumeration."""
    ACTIVE = "ACTIVE"       # Trading allowed
    TRIGGERED = "TRIGGERED" # Trading halted
    COOLING = "COOLING"     # Cooling down period
    DISABLED = "DISABLED"   # Breaker disabled

@dataclass
class BreakEvent:
    """Circuit breaker event data."""
    breaker_name: str
    trigger_time: datetime
    trigger_reason: str
    severity: str
    trigger_value: Any
    threshold_value: Any
    cooling_period_minutes: int

class CircuitBreakerSystem:
    """
    Comprehensive circuit breaker system for trading risk management.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize circuit breaker system."""
        self.config = config or self._get_default_config()
        self.breakers = {}
        self.triggered_events = []
        self.last_checks = {}
        self._initialize_breakers()
        
    def _get_default_config(self) -> Dict:
        """Default circuit breaker configuration."""
        return {
            # Volatility breakers
            "volatility_spike_threshold": 0.15,      # 15% daily volatility
            "volatility_lookback_hours": 24,         # Look back period
            "volatility_cooling_minutes": 30,        # Cool down period
            
            # Price movement breakers
            "price_spike_threshold": 0.20,           # 20% price move
            "price_spike_timeframe_minutes": 5,      # Within 5 minutes
            "price_spike_cooling_minutes": 15,       # Cool down period
            
            # API health breakers
            "api_timeout_seconds": 10,               # API timeout threshold
            "api_max_failures": 3,                   # Max consecutive failures
            "api_failure_window_minutes": 10,        # Failure counting window
            "api_cooling_minutes": 5,                # API cool down
            
            # Data freshness breakers
            "max_data_age_minutes": 5,               # Max acceptable data age
            "stale_data_cooling_minutes": 2,         # Quick recovery for data
            
            # Market anomaly breakers
            "volume_spike_multiplier": 10.0,         # 10x normal volume
            "volume_cooling_minutes": 10,            # Volume spike cooling
            "spread_spike_multiplier": 5.0,          # 5x normal spread
            "spread_cooling_minutes": 5,             # Spread spike cooling
            
            # System health breakers
            "memory_usage_threshold": 0.90,          # 90% memory usage
            "cpu_usage_threshold": 0.95,             # 95% CPU usage
            "disk_usage_threshold": 0.95,            # 95% disk usage
            "system_cooling_minutes": 10,            # System health cooling
            
            # Global settings
            "master_kill_switch": False,             # Global disable
            "enable_logging": True,                  # Log all events
            "alert_on_trigger": True,                # Send alerts
            "auto_recovery": True                    # Auto-recover after cooling
        }
    
    def _initialize_breakers(self):
        """Initialize all circuit breakers."""
        self.breakers = {
            "volatility_spike": BreakStatus.ACTIVE,
            "price_spike": BreakStatus.ACTIVE,
            "api_health": BreakStatus.ACTIVE,
            "stale_data": BreakStatus.ACTIVE,
            "volume_anomaly": BreakStatus.ACTIVE,
            "spread_anomaly": BreakStatus.ACTIVE,
            "system_health": BreakStatus.ACTIVE,
            "master_switch": BreakStatus.ACTIVE
        }
    
    def check_all_breakers(
        self, 
        market_data: Dict, 
        system_metrics: Optional[Dict] = None
    ) -> Dict:
        """
        Check all circuit breakers and return trading permission status.
        
        Args:
            market_data: Current market data including prices, volume, etc.
            system_metrics: System performance metrics
            
        Returns:
            Dict with overall status and individual breaker results
        """
        if self.config["master_kill_switch"]:
            return self._create_result(False, "Master kill switch activated")
        
        breaker_results = {}
        
        # Check each breaker type
        breaker_results["volatility_spike"] = self._check_volatility_spike(market_data)
        breaker_results["price_spike"] = self._check_price_spike(market_data)
        breaker_results["api_health"] = self._check_api_health(market_data)
        breaker_results["stale_data"] = self._check_stale_data(market_data)
        breaker_results["volume_anomaly"] = self._check_volume_anomaly(market_data)
        breaker_results["spread_anomaly"] = self._check_spread_anomaly(market_data)
        
        if system_metrics:
            breaker_results["system_health"] = self._check_system_health(system_metrics)
        
        # Determine overall trading permission
        trading_allowed = all(
            result["allowed"] for result in breaker_results.values()
        )
        
        # Update breaker statuses
        for breaker_name, result in breaker_results.items():
            if not result["allowed"] and self.breakers[breaker_name] == BreakStatus.ACTIVE:
                self._trigger_breaker(breaker_name, result["reason"], result.get("trigger_value"))
            elif result["allowed"] and self.breakers[breaker_name] == BreakStatus.TRIGGERED:
                self._recover_breaker(breaker_name)
        
        return {
            "trading_allowed": trading_allowed,
            "timestamp": datetime.now().isoformat(),
            "breaker_results": breaker_results,
            "triggered_breakers": [
                name for name, status in self.breakers.items() 
                if status == BreakStatus.TRIGGERED
            ],
            "active_events": len([e for e in self.triggered_events if self._is_event_active(e)])
        }
    
    def _check_volatility_spike(self, market_data: Dict) -> Dict:
        """Check for volatility spike conditions."""
        try:
            current_volatility = market_data.get("volatility", 0.0)
            volatility_threshold = self.config["volatility_spike_threshold"]
            
            if current_volatility > volatility_threshold:
                return {
                    "allowed": False,
                    "reason": f"Volatility spike detected: {current_volatility:.3f} > {volatility_threshold:.3f}",
                    "trigger_value": current_volatility,
                    "threshold": volatility_threshold
                }
            
            return {"allowed": True, "reason": "Volatility within normal range"}
            
        except Exception as e:
            logging.error(f"Error checking volatility spike: {e}")
            return {"allowed": False, "reason": f"Volatility check error: {e}"}
    
    def _check_price_spike(self, market_data: Dict) -> Dict:
        """Check for sudden price spike conditions."""
        try:
            price_change = market_data.get("price_change_5min", 0.0)
            price_threshold = self.config["price_spike_threshold"]
            
            if abs(price_change) > price_threshold:
                return {
                    "allowed": False,
                    "reason": f"Price spike detected: {price_change:.3f} > ±{price_threshold:.3f}",
                    "trigger_value": price_change,
                    "threshold": price_threshold
                }
            
            return {"allowed": True, "reason": "Price movement within normal range"}
            
        except Exception as e:
            logging.error(f"Error checking price spike: {e}")
            return {"allowed": False, "reason": f"Price spike check error: {e}"}
    
    def _check_api_health(self, market_data: Dict) -> Dict:
        """Check API health and connectivity."""
        try:
            # Check if we have recent successful API responses
            last_api_success = market_data.get("last_api_success")
            api_error_count = market_data.get("api_error_count", 0)
            
            if last_api_success:
                time_since_success = (datetime.now() - last_api_success).total_seconds()
                max_age = self.config["api_timeout_seconds"]
                
                if time_since_success > max_age:
                    return {
                        "allowed": False,
                        "reason": f"API timeout: {time_since_success:.1f}s since last success",
                        "trigger_value": time_since_success,
                        "threshold": max_age
                    }
            
            # Check error count
            max_errors = self.config["api_max_failures"]
            if api_error_count >= max_errors:
                return {
                    "allowed": False,
                    "reason": f"Too many API errors: {api_error_count} >= {max_errors}",
                    "trigger_value": api_error_count,
                    "threshold": max_errors
                }
            
            return {"allowed": True, "reason": "API health normal"}
            
        except Exception as e:
            logging.error(f"Error checking API health: {e}")
            return {"allowed": False, "reason": f"API health check error: {e}"}
    
    def _check_stale_data(self, market_data: Dict) -> Dict:
        """Check for stale market data."""
        try:
            last_update = market_data.get("last_update")
            if not last_update:
                return {
                    "allowed": False,
                    "reason": "No timestamp available for market data",
                    "trigger_value": None,
                    "threshold": None
                }
            
            if isinstance(last_update, str):
                last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            
            time_since_update = (datetime.now() - last_update.replace(tzinfo=None)).total_seconds() / 60
            max_age_minutes = self.config["max_data_age_minutes"]
            
            if time_since_update > max_age_minutes:
                return {
                    "allowed": False,
                    "reason": f"Stale data detected: {time_since_update:.1f} minutes old",
                    "trigger_value": time_since_update,
                    "threshold": max_age_minutes
                }
            
            return {"allowed": True, "reason": "Data freshness acceptable"}
            
        except Exception as e:
            logging.error(f"Error checking data freshness: {e}")
            return {"allowed": False, "reason": f"Data freshness check error: {e}"}
    
    def _check_volume_anomaly(self, market_data: Dict) -> Dict:
        """Check for volume anomalies."""
        try:
            current_volume = market_data.get("volume", 0)
            average_volume = market_data.get("average_volume", 1)
            
            if average_volume > 0:
                volume_ratio = current_volume / average_volume
                threshold = self.config["volume_spike_multiplier"]
                
                if volume_ratio > threshold:
                    return {
                        "allowed": False,
                        "reason": f"Volume spike: {volume_ratio:.1f}x normal volume",
                        "trigger_value": volume_ratio,
                        "threshold": threshold
                    }
            
            return {"allowed": True, "reason": "Volume within normal range"}
            
        except Exception as e:
            logging.error(f"Error checking volume anomaly: {e}")
            return {"allowed": False, "reason": f"Volume anomaly check error: {e}"}
    
    def _check_spread_anomaly(self, market_data: Dict) -> Dict:
        """Check for bid-ask spread anomalies."""
        try:
            current_spread = market_data.get("bid_ask_spread", 0)
            normal_spread = market_data.get("normal_spread", 0.001)
            
            if normal_spread > 0:
                spread_ratio = current_spread / normal_spread
                threshold = self.config["spread_spike_multiplier"]
                
                if spread_ratio > threshold:
                    return {
                        "allowed": False,
                        "reason": f"Spread anomaly: {spread_ratio:.1f}x normal spread",
                        "trigger_value": spread_ratio,
                        "threshold": threshold
                    }
            
            return {"allowed": True, "reason": "Spread within normal range"}
            
        except Exception as e:
            logging.error(f"Error checking spread anomaly: {e}")
            return {"allowed": False, "reason": f"Spread anomaly check error: {e}"}
    
    def _check_system_health(self, system_metrics: Dict) -> Dict:
        """Check system health metrics."""
        try:
            memory_usage = system_metrics.get("memory_usage", 0.0)
            cpu_usage = system_metrics.get("cpu_usage", 0.0)
            disk_usage = system_metrics.get("disk_usage", 0.0)
            
            # Check memory usage
            if memory_usage > self.config["memory_usage_threshold"]:
                return {
                    "allowed": False,
                    "reason": f"High memory usage: {memory_usage:.1%}",
                    "trigger_value": memory_usage,
                    "threshold": self.config["memory_usage_threshold"]
                }
            
            # Check CPU usage
            if cpu_usage > self.config["cpu_usage_threshold"]:
                return {
                    "allowed": False,
                    "reason": f"High CPU usage: {cpu_usage:.1%}",
                    "trigger_value": cpu_usage,
                    "threshold": self.config["cpu_usage_threshold"]
                }
            
            # Check disk usage
            if disk_usage > self.config["disk_usage_threshold"]:
                return {
                    "allowed": False,
                    "reason": f"High disk usage: {disk_usage:.1%}",
                    "trigger_value": disk_usage,
                    "threshold": self.config["disk_usage_threshold"]
                }
            
            return {"allowed": True, "reason": "System health normal"}
            
        except Exception as e:
            logging.error(f"Error checking system health: {e}")
            return {"allowed": False, "reason": f"System health check error: {e}"}
    
    def _trigger_breaker(self, breaker_name: str, reason: str, trigger_value: Any = None):
        """Trigger a circuit breaker."""
        self.breakers[breaker_name] = BreakStatus.TRIGGERED
        
        # Create event record
        event = BreakEvent(
            breaker_name=breaker_name,
            trigger_time=datetime.now(),
            trigger_reason=reason,
            severity="HIGH",
            trigger_value=trigger_value,
            threshold_value=self._get_threshold_for_breaker(breaker_name),
            cooling_period_minutes=self._get_cooling_period(breaker_name)
        )
        
        self.triggered_events.append(event)
        
        if self.config["enable_logging"]:
            logging.warning(f"CIRCUIT BREAKER TRIGGERED: {breaker_name} - {reason}")
        
        if self.config["alert_on_trigger"]:
            self._send_alert(event)
    
    def _recover_breaker(self, breaker_name: str):
        """Recover a circuit breaker after cooling period."""
        if not self.config["auto_recovery"]:
            return
        
        # Check if cooling period has passed
        latest_event = self._get_latest_event(breaker_name)
        if latest_event and self._is_cooling_complete(latest_event):
            self.breakers[breaker_name] = BreakStatus.ACTIVE
            
            if self.config["enable_logging"]:
                logging.info(f"CIRCUIT BREAKER RECOVERED: {breaker_name}")
    
    def _get_threshold_for_breaker(self, breaker_name: str) -> Any:
        """Get threshold value for a specific breaker."""
        threshold_map = {
            "volatility_spike": self.config["volatility_spike_threshold"],
            "price_spike": self.config["price_spike_threshold"],
            "api_health": self.config["api_max_failures"],
            "stale_data": self.config["max_data_age_minutes"],
            "volume_anomaly": self.config["volume_spike_multiplier"],
            "spread_anomaly": self.config["spread_spike_multiplier"],
            "system_health": 0.90  # Generic threshold
        }
        return threshold_map.get(breaker_name, "Unknown")
    
    def _get_cooling_period(self, breaker_name: str) -> int:
        """Get cooling period for a specific breaker."""
        cooling_map = {
            "volatility_spike": self.config["volatility_cooling_minutes"],
            "price_spike": self.config["price_spike_cooling_minutes"],
            "api_health": self.config["api_cooling_minutes"],
            "stale_data": self.config["stale_data_cooling_minutes"],
            "volume_anomaly": self.config["volume_cooling_minutes"],
            "spread_anomaly": self.config["spread_cooling_minutes"],
            "system_health": self.config["system_cooling_minutes"]
        }
        return cooling_map.get(breaker_name, 5)  # Default 5 minutes
    
    def _get_latest_event(self, breaker_name: str) -> Optional[BreakEvent]:
        """Get the most recent event for a specific breaker."""
        events = [e for e in self.triggered_events if e.breaker_name == breaker_name]
        return max(events, key=lambda x: x.trigger_time) if events else None
    
    def _is_cooling_complete(self, event: BreakEvent) -> bool:
        """Check if cooling period is complete for an event."""
        cooling_duration = timedelta(minutes=event.cooling_period_minutes)
        return datetime.now() - event.trigger_time > cooling_duration
    
    def _is_event_active(self, event: BreakEvent) -> bool:
        """Check if an event is still active (within cooling period)."""
        return not self._is_cooling_complete(event)
    
    def _send_alert(self, event: BreakEvent):
        """Send alert for circuit breaker trigger."""
        alert_message = (
            f"🚨 CIRCUIT BREAKER TRIGGERED: {event.breaker_name}\n"
            f"Reason: {event.trigger_reason}\n"
            f"Time: {event.trigger_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Cooling Period: {event.cooling_period_minutes} minutes"
        )
        
        # Here you would integrate with your alert system
        # For now, just log the alert
        logging.critical(alert_message)
    
    def _create_result(self, allowed: bool, reason: str) -> Dict:
        """Create standardized result dictionary."""
        return {
            "trading_allowed": allowed,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "breaker_results": {},
            "triggered_breakers": [],
            "active_events": 0
        }
    
    def manually_trigger_breaker(self, breaker_name: str, reason: str = "Manual trigger"):
        """Manually trigger a specific circuit breaker."""
        if breaker_name in self.breakers:
            self._trigger_breaker(breaker_name, reason)
            return True
        return False
    
    def manually_reset_breaker(self, breaker_name: str):
        """Manually reset a specific circuit breaker."""
        if breaker_name in self.breakers:
            self.breakers[breaker_name] = BreakStatus.ACTIVE
            if self.config["enable_logging"]:
                logging.info(f"CIRCUIT BREAKER MANUALLY RESET: {breaker_name}")
            return True
        return False
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report of all circuit breakers."""
        active_events = [e for e in self.triggered_events if self._is_event_active(e)]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "master_kill_switch": self.config["master_kill_switch"],
            "breaker_statuses": dict(self.breakers),
            "active_events_count": len(active_events),
            "total_events_count": len(self.triggered_events),
            "recent_events": [
                {
                    "breaker": e.breaker_name,
                    "trigger_time": e.trigger_time.isoformat(),
                    "reason": e.trigger_reason,
                    "is_active": self._is_event_active(e)
                }
                for e in sorted(self.triggered_events, key=lambda x: x.trigger_time, reverse=True)[:10]
            ],
            "configuration": self.config
        }


# Factory function
def create_circuit_breaker_system(config: Optional[Dict] = None) -> CircuitBreakerSystem:
    """Create and return configured CircuitBreakerSystem."""
    return CircuitBreakerSystem(config)


# Example usage
if __name__ == "__main__":
    # Create circuit breaker system
    circuit_breakers = create_circuit_breaker_system()
    
    # Example market data
    example_market_data = {
        "volatility": 0.05,  # 5% volatility
        "price_change_5min": 0.03,  # 3% price change
        "last_api_success": datetime.now(),
        "api_error_count": 0,
        "last_update": datetime.now().isoformat(),
        "volume": 1000000,
        "average_volume": 500000,
        "bid_ask_spread": 0.001,
        "normal_spread": 0.0005
    }
    
    # Check all breakers
    result = circuit_breakers.check_all_breakers(example_market_data)
    
    print("Circuit Breaker Check Result:")
    print(f"Trading Allowed: {result['trading_allowed']}")
    print(f"Triggered Breakers: {result['triggered_breakers']}")
    
    # Get status report
    status = circuit_breakers.get_status_report()
    print(f"\nSystem Status: {len(status['recent_events'])} recent events")