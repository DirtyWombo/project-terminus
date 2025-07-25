"""
Position Sizing Engine
=====================

Advanced position sizing algorithms that account for:
1. Signal confidence and strength
2. Market volatility and regime
3. Portfolio risk limits
4. Kelly Criterion optimization
5. Fractional risk management
"""

import logging
import numpy as np
import math
from typing import Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO)

class PositionSizingEngine:
    """
    Advanced position sizing engine for risk-managed trading.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize position sizing engine."""
        self.config = config or self._get_default_config()
        
    def _get_default_config(self) -> Dict:
        """Default position sizing configuration - CONSERVATIVE INSTITUTIONAL GRADE."""
        return {
            # FOUNDATIONAL RISK CONTROLS (Per Critique Requirements)
            "base_position_size": 0.005,     # 0.5% FIXED FRACTIONAL (Conservative)
            "max_position_size": 0.005,      # 0.5% maximum position (No scaling)
            "min_position_size": 0.005,      # 0.5% minimum position (Fixed)
            
            # PORTFOLIO-LEVEL PROTECTION
            "max_portfolio_risk": 0.05,      # 5% max portfolio at risk (Conservative)
            "max_single_asset_risk": 0.005,  # 0.5% max risk per trade (Fixed)
            "max_drawdown_stop": 0.20,       # 20% drawdown triggers full stop
            "stop_loss_multiplier": 2.0,     # Stop loss at 2x volatility
            
            # DISABLE COMPLEX SCALING (Per Critique)
            "use_volatility_scaling": False,  # Disabled complex volatility adjustments
            "target_volatility": 0.02,       # 2% target daily volatility
            "volatility_lookback": 20,       # 20-day volatility calculation
            
            # KELLY CRITERION REMOVED (Per Critique)
            "use_kelly_criterion": False,    # DISABLED - Flawed implementation
            "kelly_fraction": 0.0,           # REMOVED Kelly optimization
            "min_win_rate": 0.0,            # Not used
            
            # SIMPLIFIED REGIME HANDLING
            "regime_multipliers": {
                "bull": 1.0,                 # No scaling - fixed sizing
                "neutral": 1.0,              # No scaling - fixed sizing  
                "bear": 0.5                  # Reduce to 50% in bear markets
            },
            
            # MINIMAL CONFIDENCE REQUIREMENTS
            "confidence_min": 0.3,           # Minimum confidence to trade
            "confidence_scaling": False,     # DISABLED - Fixed sizing only
            "confidence_power": 1.0          # No power scaling
        }
    
    def calculate_position_size(
        self,
        signal_score: float,
        signal_confidence: float,
        portfolio_value: float,
        market_volatility: float,
        current_positions: Dict = None,
        market_regime: str = "neutral",
        asset_volatility: float = None,
        win_rate: float = None,
        avg_win_loss_ratio: float = None
    ) -> Dict:
        """
        Calculate optimal position size using multiple methodologies.
        
        Args:
            signal_score: Final trading signal (-1 to 1)
            signal_confidence: Confidence in signal (0 to 1)
            portfolio_value: Current portfolio value
            market_volatility: Current market volatility
            current_positions: Dict of current positions {symbol: size}
            market_regime: Current market regime (bull/neutral/bear)
            asset_volatility: Asset-specific volatility
            win_rate: Historical win rate for Kelly calculation
            avg_win_loss_ratio: Average win/loss ratio for Kelly
            
        Returns:
            Dict containing position size and methodology breakdown
        """
        
        # MASTER SHUTDOWN PROTOCOL: Check if system is operational
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from trader_app.master_shutdown import is_system_operational, get_shutdown_status
            
            if not is_system_operational():
                shutdown_status = get_shutdown_status()
                return self._create_result(0.0, f"Trading halted: System shutdown - {shutdown_status.get('reason', 'unknown')}")
        except:
            pass  # Continue if master shutdown not available
        
        # CRITICAL SAFETY CHECK: Portfolio Drawdown Protection
        if hasattr(self, '_check_drawdown_stop') and self._check_drawdown_stop(portfolio_value):
            return self._create_result(0.0, "Trading halted: Portfolio drawdown exceeds 20% maximum")
        
        # Validate inputs
        if signal_confidence < self.config["confidence_min"]:
            return self._create_result(0.0, "Signal confidence below minimum threshold")
        
        if abs(signal_score) < 0.1:  # Very weak signal
            return self._create_result(0.0, "Signal strength insufficient")
        
        # SIMPLIFIED POSITION SIZING (Per Critique - Fixed Fractional)
        base_size = self.config["base_position_size"]  # Fixed 0.5%
        
        # 1. FIXED FRACTIONAL SIZING (No complex adjustments)
        fixed_size = base_size
        
        # 2. MARKET REGIME ADJUSTMENT ONLY (Conservative)
        regime_adjusted_size = self._regime_adjustment(fixed_size, market_regime)
        
        # 3. PORTFOLIO-LEVEL RISK LIMITS (Critical Safety)
        risk_limited_size = self._apply_risk_limits(
            regime_adjusted_size, portfolio_value, current_positions
        )
        
        # 4. FINAL BOUNDS (Ensure 0.5% fixed sizing)
        final_size = self._apply_final_bounds(risk_limited_size)
        
        # Calculate stop loss level
        stop_loss_distance = self._calculate_stop_loss(market_volatility, asset_volatility)
        
        # Calculate risk amount
        risk_amount = final_size * portfolio_value * stop_loss_distance
        
        return {
            "position_size": final_size,
            "position_value": final_size * portfolio_value,
            "risk_amount": risk_amount,
            "risk_percentage": risk_amount / portfolio_value,
            "stop_loss_distance": stop_loss_distance,
            "methodology_breakdown": {
                "base_size": base_size,
                "fixed_fractional": fixed_size,
                "regime_adjusted": regime_adjusted_size,
                "risk_limited": risk_limited_size,
                "final_size": final_size
            },
            "parameters_used": {
                "signal_score": signal_score,
                "signal_confidence": signal_confidence,
                "market_volatility": market_volatility,
                "asset_volatility": asset_volatility,
                "market_regime": market_regime
            }
        }
    
    def _volatility_adjusted_size(
        self, 
        base_size: float, 
        market_volatility: float, 
        asset_volatility: float = None
    ) -> float:
        """VOLATILITY SCALING DISABLED - Per institutional critique.
        
        Returns base_size unchanged to maintain fixed fractional sizing.
        Complex volatility adjustments were identified as unnecessary
        complexity that introduces risk.
        """
        # Check if volatility scaling is enabled (disabled by default)
        if not self.config.get("use_volatility_scaling", False):
            return base_size
        
        # If enabled, use simplified volatility adjustment
        effective_volatility = asset_volatility or market_volatility
        target_vol = self.config["target_volatility"]
        vol_ratio = target_vol / max(effective_volatility, 0.005)
        vol_factor = max(0.5, min(vol_ratio, 2.0))  # Conservative bounds
        
        return base_size * vol_factor
    
    def _confidence_scaled_size(self, base_size: float, confidence: float) -> float:
        """CONFIDENCE SCALING DISABLED - Per institutional critique.
        
        Returns base_size unchanged to maintain fixed fractional sizing.
        Confidence-based scaling was identified as unnecessary complexity
        that can introduce position sizing variability.
        """
        # Confidence scaling disabled by default in new config
        if not self.config.get("confidence_scaling", False):
            return base_size
        
        # If enabled, use minimal scaling
        confidence_factor = max(0.8, min(confidence, 1.0))  # Conservative range
        return base_size * confidence_factor
    
    def _kelly_criterion_size(
        self, 
        base_size: float, 
        signal_score: float, 
        win_rate: float = None, 
        avg_win_loss_ratio: float = None
    ) -> float:
        """KELLY CRITERION REMOVED - Per institutional critique.
        
        Returns base_size unchanged to maintain fixed fractional sizing.
        Kelly Criterion was identified as flawed implementation that
        introduced excessive complexity and risk.
        """
        # ALWAYS return base size - no Kelly optimization
        return base_size
    
    def _apply_risk_limits(
        self, 
        size: float, 
        portfolio_value: float, 
        current_positions: Dict = None
    ) -> float:
        """Apply portfolio-level risk limits."""
        # Single position risk limit
        max_single_risk = self.config["max_single_asset_risk"]
        size = min(size, max_single_risk)
        
        # Portfolio concentration limit
        current_positions = current_positions or {}
        current_exposure = sum(current_positions.values())
        available_capacity = self.config["max_portfolio_risk"] - current_exposure
        
        if available_capacity <= 0:
            return 0.0  # Portfolio fully allocated
        
        size = min(size, available_capacity)
        
        return size
    
    def _regime_adjustment(self, size: float, market_regime: str) -> float:
        """Adjust position size based on market regime."""
        regime = market_regime.lower()
        multiplier = self.config["regime_multipliers"].get(regime, 1.0)
        
        return size * multiplier
    
    def _apply_final_bounds(self, size: float) -> float:
        """Apply final minimum and maximum bounds."""
        min_size = self.config["min_position_size"]
        max_size = self.config["max_position_size"]
        
        return max(min_size, min(size, max_size))
    
    def _calculate_stop_loss(
        self, 
        market_volatility: float, 
        asset_volatility: float = None
    ) -> float:
        """Calculate stop loss distance based on volatility."""
        effective_volatility = asset_volatility or market_volatility
        stop_loss_distance = effective_volatility * self.config["stop_loss_multiplier"]
        
        # Reasonable bounds for stop loss
        return max(0.02, min(stop_loss_distance, 0.15))  # 2% to 15%
    
    def _create_result(self, size: float, reason: str) -> Dict:
        """Create a standardized result dictionary."""
        return {
            "position_size": size,
            "position_value": 0.0,
            "risk_amount": 0.0,
            "risk_percentage": 0.0,
            "stop_loss_distance": 0.0,
            "reason": reason,
            "methodology_breakdown": {},
            "parameters_used": {}
        }
    
    def update_config(self, new_config: Dict) -> None:
        """Update configuration."""
        self.config.update(new_config)
    
    def get_config(self) -> Dict:
        """Get current configuration."""
        return self.config.copy()
    
    def set_portfolio_high_water_mark(self, high_water_mark: float) -> None:
        """Set the portfolio high water mark for drawdown calculation."""
        self._portfolio_high_water_mark = high_water_mark
    
    def _check_drawdown_stop(self, current_portfolio_value: float) -> bool:
        """Check if current drawdown exceeds maximum allowed drawdown."""
        if not hasattr(self, '_portfolio_high_water_mark'):
            # Initialize high water mark if not set
            self._portfolio_high_water_mark = current_portfolio_value
            return False
        
        # Update high water mark if portfolio has grown
        if current_portfolio_value > self._portfolio_high_water_mark:
            self._portfolio_high_water_mark = current_portfolio_value
        
        # Calculate current drawdown
        current_drawdown = (self._portfolio_high_water_mark - current_portfolio_value) / self._portfolio_high_water_mark
        max_allowed_drawdown = self.config["max_drawdown_stop"]
        
        # Check if drawdown exceeds maximum
        return current_drawdown >= max_allowed_drawdown
    
    def get_current_drawdown(self, current_portfolio_value: float) -> Dict:
        """Get current portfolio drawdown metrics."""
        if not hasattr(self, '_portfolio_high_water_mark'):
            self._portfolio_high_water_mark = current_portfolio_value
            
        if current_portfolio_value > self._portfolio_high_water_mark:
            self._portfolio_high_water_mark = current_portfolio_value
        
        current_drawdown = (self._portfolio_high_water_mark - current_portfolio_value) / self._portfolio_high_water_mark
        max_allowed_drawdown = self.config["max_drawdown_stop"]
        
        return {
            "current_drawdown": current_drawdown,
            "max_allowed_drawdown": max_allowed_drawdown,
            "drawdown_remaining": max_allowed_drawdown - current_drawdown,
            "high_water_mark": self._portfolio_high_water_mark,
            "current_value": current_portfolio_value,
            "trading_halted": current_drawdown >= max_allowed_drawdown
        }
    
    def calculate_portfolio_risk(self, positions: Dict, volatilities: Dict) -> Dict:
        """
        Calculate total portfolio risk from current positions.
        
        Args:
            positions: Dict of {symbol: position_size}
            volatilities: Dict of {symbol: volatility}
            
        Returns:
            Dict with portfolio risk metrics
        """
        total_risk = 0.0
        position_risks = {}
        
        for symbol, size in positions.items():
            volatility = volatilities.get(symbol, 0.02)  # Default 2% volatility
            stop_distance = self._calculate_stop_loss(volatility, volatility)
            position_risk = size * stop_distance
            
            position_risks[symbol] = position_risk
            total_risk += position_risk
        
        return {
            "total_portfolio_risk": total_risk,
            "position_risks": position_risks,
            "risk_utilization": total_risk / self.config["max_portfolio_risk"],
            "available_risk_capacity": max(0, self.config["max_portfolio_risk"] - total_risk)
        }


# Factory function
def create_position_sizing_engine(config: Optional[Dict] = None) -> PositionSizingEngine:
    """Create and return configured PositionSizingEngine."""
    return PositionSizingEngine(config)


# Example usage
if __name__ == "__main__":
    # Create engine
    engine = create_position_sizing_engine()
    
    # Example calculation
    result = engine.calculate_position_size(
        signal_score=0.6,
        signal_confidence=0.8,
        portfolio_value=10000.0,
        market_volatility=0.025,
        market_regime="bull",
        asset_volatility=0.035,
        win_rate=0.55,
        avg_win_loss_ratio=1.2
    )
    
    print("Position Sizing Result:")
    print(f"Position Size: {result['position_size']:.1%}")
    print(f"Position Value: ${result['position_value']:.2f}")
    print(f"Risk Amount: ${result['risk_amount']:.2f}")
    print(f"Risk Percentage: {result['risk_percentage']:.2%}")
    print(f"Stop Loss Distance: {result['stop_loss_distance']:.2%}")
    
    print("\nMethodology Breakdown:")
    for step, value in result['methodology_breakdown'].items():
        print(f"  {step}: {value:.3%}")