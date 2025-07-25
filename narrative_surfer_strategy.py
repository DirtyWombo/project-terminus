"""
NARRATIVE SURFER STRATEGY
=========================

Per expert recommendation - Simple, elegant baseline strategy that demonstrates
the principle of "sophisticated alpha signal + simple execution".

Strategy Components:
1. Sophisticated Alpha Signal: AI-detected narrative velocity acceleration
2. Robust Filter: Automated safety checks and risk management  
3. Simple Trigger: Basic technical indicators for tactical entry/exit timing

This strategy embodies the expert's "sniper rifle" philosophy - precise,
targeted, and effective rather than complex for complexity's sake.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TradingSignal(Enum):
    """Trading signal types."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

@dataclass
class NarrativeSurferSignal:
    """Output of the Narrative Surfer strategy."""
    symbol: str
    signal: TradingSignal
    velocity_score: float      # Core narrative velocity (-1 to 1)
    confidence: float          # AI confidence (0 to 1)
    risk_score: float         # Overall risk assessment (0 to 1)
    entry_reason: str         # Human-readable reason
    timestamp: datetime

class NarrativeSurferStrategy:
    """
    NARRATIVE SURFER STRATEGY
    
    Elegant strategy focusing on narrative velocity acceleration detection.
    
    Core Edge: AI detects acceleration in narrative velocity before others
    Simple Execution: Clean entry/exit rules with basic technical confirmation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the Narrative Surfer strategy."""
        self.config = config or self._get_default_config()
        self.position_history = {}
        self.signal_history = []
        
    def _get_default_config(self) -> Dict:
        """Default configuration for Narrative Surfer strategy."""
        return {
            # NARRATIVE DETECTION THRESHOLDS
            "min_velocity_score": 0.4,         # Minimum narrative velocity for signal
            "min_ai_confidence": 0.65,         # Minimum AI confidence threshold
            "velocity_acceleration_threshold": 0.2,  # Rate of velocity increase
            
            # TECHNICAL CONFIRMATION (Simple filters)
            "rsi_oversold": 30,                # RSI oversold level
            "rsi_overbought": 70,              # RSI overbought level
            "use_rsi_filter": True,            # Enable RSI filtering
            "volume_spike_threshold": 2.0,     # 2x average volume
            
            # RISK MANAGEMENT
            "max_risk_score": 0.7,            # Maximum risk score to trade
            "position_timeout_hours": 24,      # Max time to hold position
            "stop_loss_atr_multiple": 2.0,    # Stop loss distance
            
            # PORTFOLIO LIMITS
            "max_concurrent_positions": 3,     # Max positions at once
            "cooldown_period_minutes": 60,     # Cooldown between signals
            
            # MEME COIN SPECIALIZATION
            "meme_coin_symbols": ["DOGE-USD", "WIF-USD", "PEPE-USD", "BONK-USD", "SHIB-USD"],
            "meme_velocity_multiplier": 1.5,   # Boost velocity for meme coins
            "meme_confidence_boost": 0.1,      # Confidence boost for meme coins
        }
    
    def analyze_symbol(
        self, 
        symbol: str, 
        ai_analysis: Dict, 
        market_data: Dict,
        current_positions: Dict = None
    ) -> Optional[NarrativeSurferSignal]:
        """
        Analyze a symbol using the Narrative Surfer strategy.
        
        Returns trading signal if opportunity detected, None otherwise.
        """
        try:
            # 1. Extract AI narrative velocity analysis
            velocity_score = ai_analysis.get("velocity_score", 0.0)
            confidence = ai_analysis.get("confidence", 0.0)
            directional_bias = ai_analysis.get("directional_bias", 0.0)
            
            # 2. Apply meme coin boost if applicable
            if symbol in self.config["meme_coin_symbols"]:
                velocity_score *= self.config["meme_velocity_multiplier"]
                confidence += self.config["meme_confidence_boost"]
                confidence = min(1.0, confidence)  # Cap at 1.0
            
            # 3. Check if signal meets minimum thresholds
            if abs(velocity_score) < self.config["min_velocity_score"]:
                return None
                
            if confidence < self.config["min_ai_confidence"]:
                return None
            
            # 4. Apply technical confirmation filter
            if not self._technical_confirmation(symbol, market_data, directional_bias):
                return None
            
            # 5. Check position limits and cooldowns
            if not self._position_management_check(symbol, current_positions):
                return None
            
            # 6. Calculate risk score
            risk_score = self._calculate_risk_score(ai_analysis, market_data)
            if risk_score > self.config["max_risk_score"]:
                return None
            
            # 7. Generate trading signal
            signal = self._determine_signal_strength(velocity_score, confidence, directional_bias)
            
            # 8. Create entry reason
            entry_reason = self._generate_entry_reason(
                symbol, velocity_score, confidence, directional_bias, risk_score
            )
            
            return NarrativeSurferSignal(
                symbol=symbol,
                signal=signal,
                velocity_score=velocity_score,
                confidence=confidence,
                risk_score=risk_score,
                entry_reason=entry_reason,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logging.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def _technical_confirmation(
        self, 
        symbol: str, 
        market_data: Dict, 
        directional_bias: float
    ) -> bool:
        """
        Simple technical confirmation filter.
        
        Expert's guidance: Use basic indicators ONLY for tactical timing,
        not as the primary edge.
        """
        if not self.config["use_rsi_filter"]:
            return True
        
        try:
            # Mock RSI calculation (in real implementation, calculate from price data)
            rsi = market_data.get("rsi", 50)  # Default neutral RSI
            
            # For buy signals, prefer RSI not overbought
            if directional_bias > 0:
                return rsi < self.config["rsi_overbought"]
            
            # For sell signals, prefer RSI not oversold
            elif directional_bias < 0:
                return rsi > self.config["rsi_oversold"]
            
            return True
            
        except Exception as e:
            logging.warning(f"Technical confirmation error for {symbol}: {e}")
            return True  # Default to allowing trade if technical check fails
    
    def _position_management_check(
        self, 
        symbol: str, 
        current_positions: Dict = None
    ) -> bool:
        """Check position limits and cooldown periods."""
        current_positions = current_positions or {}
        
        # Check maximum concurrent positions
        if len(current_positions) >= self.config["max_concurrent_positions"]:
            return False
        
        # Check if already have position in this symbol
        if symbol in current_positions:
            return False
        
        # Check cooldown period
        last_signal_time = self.position_history.get(symbol, datetime.min)
        cooldown_minutes = self.config["cooldown_period_minutes"]
        
        if (datetime.now() - last_signal_time).total_seconds() < (cooldown_minutes * 60):
            return False
        
        return True
    
    def _calculate_risk_score(self, ai_analysis: Dict, market_data: Dict) -> float:
        """Calculate overall risk score for the trade."""
        try:
            # Base risk from AI analysis
            ai_risk = ai_analysis.get("risk_metrics", {}).get("expected_volatility", 0.025)
            
            # Market volatility risk
            market_volatility = market_data.get("volatility", 0.025)
            
            # Volume risk (low volume = higher risk)
            volume = market_data.get("volume", 1000000)
            avg_volume = market_data.get("avg_volume", 1000000)
            volume_risk = max(0, 1 - (volume / avg_volume))  # Higher risk if volume low
            
            # Combine risk factors
            combined_risk = (
                0.4 * ai_risk + 
                0.4 * market_volatility + 
                0.2 * volume_risk
            )
            
            return min(1.0, combined_risk)
            
        except Exception as e:
            logging.warning(f"Risk calculation error: {e}")
            return 0.5  # Default moderate risk
    
    def _determine_signal_strength(
        self, 
        velocity_score: float, 
        confidence: float, 
        directional_bias: float
    ) -> TradingSignal:
        """Determine signal strength based on velocity and confidence."""
        
        # Calculate combined signal strength
        signal_strength = abs(velocity_score) * confidence
        
        # Determine direction
        direction = 1 if (velocity_score > 0 and directional_bias > 0) else -1
        
        # Classify signal strength
        if signal_strength > 0.8:
            return TradingSignal.STRONG_BUY if direction > 0 else TradingSignal.STRONG_SELL
        elif signal_strength > 0.6:
            return TradingSignal.BUY if direction > 0 else TradingSignal.SELL
        else:
            return TradingSignal.HOLD
    
    def _generate_entry_reason(
        self, 
        symbol: str, 
        velocity_score: float, 
        confidence: float, 
        directional_bias: float, 
        risk_score: float
    ) -> str:
        """Generate human-readable entry reason."""
        direction = "bullish" if velocity_score > 0 else "bearish"
        strength = "strong" if abs(velocity_score) > 0.7 else "moderate"
        confidence_level = "high" if confidence > 0.8 else "medium"
        
        reason = f"Narrative Surfer: {strength} {direction} velocity ({velocity_score:.2f}) "
        reason += f"with {confidence_level} AI confidence ({confidence:.2f}). "
        
        if symbol in self.config["meme_coin_symbols"]:
            reason += f"Meme coin specialization applied. "
        
        reason += f"Risk: {risk_score:.2f}"
        
        return reason
    
    def update_position_history(self, symbol: str):
        """Update position history for cooldown tracking."""
        self.position_history[symbol] = datetime.now()
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status and metrics."""
        return {
            "strategy_name": "Narrative Surfer",
            "total_signals": len(self.signal_history),
            "recent_signals": self.signal_history[-10:] if self.signal_history else [],
            "position_cooldowns": {
                symbol: (datetime.now() - timestamp).total_seconds() / 60
                for symbol, timestamp in self.position_history.items()
            },
            "config": self.config
        }


# Test the strategy
if __name__ == "__main__":
    print("Testing NARRATIVE SURFER STRATEGY")
    
    # Initialize strategy
    strategy = NarrativeSurferStrategy()
    
    # Mock AI analysis with high velocity
    mock_ai_analysis = {
        "velocity_score": 0.8,
        "confidence": 0.75,
        "directional_bias": 0.6,
        "risk_metrics": {"expected_volatility": 0.03}
    }
    
    # Mock market data
    mock_market_data = {
        "price": 50000,
        "volume": 2000000,
        "avg_volume": 1000000,
        "volatility": 0.025,
        "rsi": 45
    }
    
    # Test analysis
    signal = strategy.analyze_symbol("BTC-USD", mock_ai_analysis, mock_market_data)
    
    if signal:
        print(f"Signal Generated: {signal.signal.value}")
        print(f"Velocity Score: {signal.velocity_score:.3f}")
        print(f"Confidence: {signal.confidence:.3f}")
        print(f"Risk Score: {signal.risk_score:.3f}")
        print(f"Reason: {signal.entry_reason}")
    else:
        print("No signal generated")
    
    # Test meme coin
    meme_signal = strategy.analyze_symbol("DOGE-USD", mock_ai_analysis, mock_market_data)
    
    if meme_signal:
        print(f"\nMeme Coin Signal: {meme_signal.signal.value}")
        print(f"Boosted Velocity: {meme_signal.velocity_score:.3f}")
        print(f"Reason: {meme_signal.entry_reason}")
    
    print("\nNarrative Surfer strategy test completed")