"""
Alpha Kernel - Core Trading Signal Generation
===========================================

MATHEMATICAL SPECIFICATION:

This module implements the core Alpha Kernel formula that combines multiple signal sources
into a unified trading decision with institutional-grade position sizing.

## Core Alpha Formula:
Final_Score = Σ(Wi × Si) where:
- W = Weight vector [W_ml, W_ai, W_sentiment, W_technical]  
- S = Signal vector [S_ml, S_ai, S_sentiment, S_technical]
- Default weights: [0.40, 0.30, 0.20, 0.10] (sum = 1.0)

## Signal Components:

### 1. ML Signal (S_ml):
- Input: ML prediction ∈ {-1, 0, 1}
- Output: Direct mapping to [-1, 1] range
- Formula: S_ml = ML_prediction

### 2. AI Signal (S_ai):
- Enhanced quantitative extraction from Llama AI
- Formula: S_ai = (0.6 × directional_bias × signal_strength) + (0.4 × factor_signal)
- Where factor_signal = Σ(bullish_factors) - Σ(bearish_factors)
- Clipped to [-1, 1] range

### 3. Sentiment Signal (S_sentiment):
- Weighted average of news and social sentiment
- Formula: S_sentiment = ((news_sentiment × news_count) + (social_sentiment × social_count)) / total_mentions
- Volume scaling: × min(1.0, total_mentions / 100)

### 4. Technical Signal (S_technical):
- Confluence-weighted technical analysis
- Formula: S_technical = ((trend_direction + momentum) / 2) × (confluence_score / 100)

## Decision Thresholds:
- STRONG_BUY: Final_Score ≥ 0.6
- BUY: 0.3 ≤ Final_Score < 0.6  
- HOLD: -0.3 < Final_Score < 0.3
- SELL: -0.6 < Final_Score ≤ -0.3
- STRONG_SELL: Final_Score ≤ -0.6

## Position Sizing Integration:
Uses advanced PositionSizingEngine with Kelly Criterion, volatility scaling,
regime adjustment, and multi-layer risk management.

This addresses expert critique requirements for mathematical rigor and 
quantitative signal combination.
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional
from .position_sizing import create_position_sizing_engine

logging.basicConfig(level=logging.INFO)

class AlphaKernel:
    """
    Core trading signal generation engine.
    
    Combines multiple signal sources into a unified trading decision.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize alpha kernel with configuration."""
        self.config = config or self._get_default_config()
        self.position_engine = create_position_sizing_engine()
        
    def _get_default_config(self) -> Dict:
        """Default configuration for signal weighting."""
        return {
            # Signal weights (must sum to 1.0)
            "ml_weight": 0.40,          # ML model prediction weight
            "ai_weight": 0.30,          # AI analysis weight  
            "sentiment_weight": 0.20,   # Market sentiment weight
            "technical_weight": 0.10,   # Technical confluence weight
            
            # Signal thresholds
            "buy_threshold": 0.3,       # Minimum score for buy signal
            "sell_threshold": -0.3,     # Maximum score for sell signal
            "strong_buy_threshold": 0.6, # Strong conviction buy
            "strong_sell_threshold": -0.6, # Strong conviction sell
            
            # Position sizing parameters
            "base_position_size": 0.02,  # 2% base position
            "max_position_size": 0.05,   # 5% maximum position
            "volatility_scaling": True,   # Scale by volatility
            "confidence_scaling": True    # Scale by signal confidence
        }
    
    def calculate_final_signal(
        self, 
        ml_prediction: int,
        ai_analysis: Dict,
        sentiment_scores: Dict,
        technical_signals: Dict,
        market_volatility: float = 0.02,
        portfolio_value: float = 10000.0,
        current_positions: Dict = None,
        market_regime: str = "neutral",
        asset_volatility: float = None,
        win_rate: float = None,
        avg_win_loss_ratio: float = None
    ) -> Dict:
        """
        Calculate final trading signal from multiple inputs.
        
        Args:
            ml_prediction: ML model output (-1, 0, 1)
            ai_analysis: AI analysis with confidence scores
            sentiment_scores: Market sentiment data
            technical_signals: Technical analysis signals
            market_volatility: Current market volatility (0-1 scale)
            
        Returns:
            Dict containing final signal, confidence, and position sizing
        """
        
        # 1. Normalize ML prediction to [-1, 1] scale
        ml_signal = float(ml_prediction)
        
        # 2. Extract AI signal components (enhanced quantitative method)
        ai_confidence = ai_analysis.get('confidence', 0.5)
        
        # Use enhanced quantitative AI signal extraction
        ai_signal = self._extract_quantitative_ai_signal(ai_analysis) * ai_confidence
        
        # 3. Calculate sentiment signal
        sentiment_signal = self._calculate_sentiment_signal(sentiment_scores)
        
        # 4. Calculate technical signal
        technical_signal = self._calculate_technical_signal(technical_signals)
        
        # 5. Combine signals using weighted formula
        final_score = (
            self.config["ml_weight"] * ml_signal +
            self.config["ai_weight"] * ai_signal +
            self.config["sentiment_weight"] * sentiment_signal +
            self.config["technical_weight"] * technical_signal
        )
        
        # 6. Generate trading decision
        decision = self._generate_decision(final_score)
        
        # 7. Calculate position size using advanced position sizing engine
        position_result = self.position_engine.calculate_position_size(
            signal_score=final_score,
            signal_confidence=abs(final_score),
            portfolio_value=portfolio_value,
            market_volatility=market_volatility,
            current_positions=current_positions,
            market_regime=market_regime,
            asset_volatility=asset_volatility,
            win_rate=win_rate,
            avg_win_loss_ratio=avg_win_loss_ratio
        )
        
        position_size = position_result["position_size"]
        
        # 8. Create detailed explanation
        explanation = self._generate_explanation(
            ml_signal, ai_signal, sentiment_signal, technical_signal, final_score
        )
        
        return {
            "final_score": final_score,
            "decision": decision,
            "position_size": position_size,
            "confidence": abs(final_score),
            "components": {
                "ml_signal": ml_signal,
                "ai_signal": ai_signal,
                "sentiment_signal": sentiment_signal,
                "technical_signal": technical_signal
            },
            "explanation": explanation,
            "market_volatility": market_volatility,
            "position_sizing_details": position_result,
            "risk_amount": position_result["risk_amount"],
            "stop_loss_distance": position_result["stop_loss_distance"]
        }
    
    def _convert_ai_recommendation(self, recommendation: str) -> float:
        """Convert AI text recommendation to numeric signal."""
        recommendation = recommendation.upper()
        if recommendation == "STRONG_BUY":
            return 1.0
        elif recommendation == "BUY" or recommendation == "BULLISH":
            return 0.8
        elif recommendation == "STRONG_SELL":
            return -1.0
        elif recommendation == "SELL" or recommendation == "BEARISH":
            return -0.8
        else:  # HOLD, NEUTRAL, etc.
            return 0.0
    
    def _extract_quantitative_ai_signal(self, ai_analysis: Dict) -> float:
        """
        Extract quantitative signal from enhanced AI analysis.
        
        This addresses expert critique: Use AI's numerical outputs directly.
        """
        # Check if we have enhanced quantitative AI output
        if "directional_bias" in ai_analysis and "signal_strength" in ai_analysis:
            directional_bias = ai_analysis.get("directional_bias", 0.0)
            signal_strength = ai_analysis.get("signal_strength", 0.0)
            velocity_score = ai_analysis.get("velocity_score", 0.5)  # NEW: Narrative velocity
            
            # NARRATIVE SURFER STRATEGY: Combine signals with velocity emphasis
            ai_signal = directional_bias * signal_strength * velocity_score
            
            # Also factor in bullish/bearish factor weights
            bullish_factors = ai_analysis.get("bullish_factors", [])
            bearish_factors = ai_analysis.get("bearish_factors", [])
            
            bullish_weight = sum(factor.get("weight", 0) * factor.get("impact", 0) 
                               for factor in bullish_factors if isinstance(factor, dict))
            bearish_weight = sum(factor.get("weight", 0) * abs(factor.get("impact", 0)) 
                               for factor in bearish_factors if isinstance(factor, dict))
            
            # Combine all quantitative signals
            factor_signal = bullish_weight - bearish_weight
            
            # Weighted combination
            final_ai_signal = (0.6 * ai_signal) + (0.4 * factor_signal)
            
            return max(-1.0, min(1.0, final_ai_signal))  # Clip to [-1, 1]
        
        # Fallback to old method for backward compatibility
        recommendation = ai_analysis.get('recommendation', 'HOLD')
        return self._convert_ai_recommendation(recommendation)
    
    def _calculate_sentiment_signal(self, sentiment_scores: Dict) -> float:
        """
        Calculate combined sentiment signal from multiple sources.
        
        Expected sentiment_scores format:
        {
            "news_sentiment": float (-1 to 1),
            "social_sentiment": float (-1 to 1),
            "news_count": int,
            "social_count": int
        }
        """
        news_sentiment = sentiment_scores.get("news_sentiment", 0.0)
        social_sentiment = sentiment_scores.get("social_sentiment", 0.0)
        news_count = sentiment_scores.get("news_count", 0)
        social_count = sentiment_scores.get("social_count", 0)
        
        # Weight by volume of mentions (more mentions = higher confidence)
        total_mentions = news_count + social_count
        if total_mentions == 0:
            return 0.0
        
        # Weighted average of sentiment sources
        weighted_sentiment = (
            (news_sentiment * news_count + social_sentiment * social_count) / 
            total_mentions
        )
        
        # Apply mention volume scaling (more mentions = stronger signal)
        volume_scaling = min(1.0, total_mentions / 100.0)  # Cap at 100 mentions
        
        return weighted_sentiment * volume_scaling
    
    def _calculate_technical_signal(self, technical_signals: Dict) -> float:
        """
        Calculate technical analysis signal.
        
        Expected technical_signals format:
        {
            "confluence_score": float (0-100),
            "trend_direction": float (-1 to 1),
            "momentum": float (-1 to 1)
        }
        """
        confluence_score = technical_signals.get("confluence_score", 50) / 100.0  # Normalize to 0-1
        trend_direction = technical_signals.get("trend_direction", 0.0)
        momentum = technical_signals.get("momentum", 0.0)
        
        # Combine trend and momentum, weighted by confluence
        technical_signal = (trend_direction + momentum) / 2.0
        
        # Scale by confluence score (higher confluence = stronger signal)
        return technical_signal * confluence_score
    
    def _generate_decision(self, final_score: float) -> str:
        """Generate trading decision from final score."""
        if final_score >= self.config["strong_buy_threshold"]:
            return "STRONG_BUY"
        elif final_score >= self.config["buy_threshold"]:
            return "BUY"
        elif final_score <= self.config["strong_sell_threshold"]:
            return "STRONG_SELL"
        elif final_score <= self.config["sell_threshold"]:
            return "SELL"
        else:
            return "HOLD"
    
    def _calculate_position_size(
        self, 
        final_score: float, 
        confidence: float, 
        market_volatility: float
    ) -> float:
        """
        Calculate position size based on signal strength and market conditions.
        
        Formula: position_size = base_size * confidence_factor * volatility_factor
        """
        # Start with base position size
        position_size = self.config["base_position_size"]
        
        # Scale by signal confidence if enabled
        if self.config["confidence_scaling"]:
            confidence_factor = min(2.0, 1.0 + confidence)  # 1.0 to 2.0 multiplier
            position_size *= confidence_factor
        
        # Scale by volatility if enabled (higher volatility = smaller position)
        if self.config["volatility_scaling"]:
            volatility_factor = 1.0 / (1.0 + market_volatility * 10)  # Reduce size in high vol
            position_size *= volatility_factor
        
        # Ensure within bounds
        position_size = max(0.005, min(position_size, self.config["max_position_size"]))
        
        return position_size
    
    def _generate_explanation(
        self, 
        ml_signal: float, 
        ai_signal: float, 
        sentiment_signal: float, 
        technical_signal: float, 
        final_score: float
    ) -> str:
        """Generate human-readable explanation of the trading decision."""
        
        components = [
            f"ML: {ml_signal:+.2f} (weight: {self.config['ml_weight']:.0%})",
            f"AI: {ai_signal:+.2f} (weight: {self.config['ai_weight']:.0%})",
            f"Sentiment: {sentiment_signal:+.2f} (weight: {self.config['sentiment_weight']:.0%})",
            f"Technical: {technical_signal:+.2f} (weight: {self.config['technical_weight']:.0%})"
        ]
        
        # Identify strongest component
        signals = [
            ("ML", ml_signal * self.config['ml_weight']),
            ("AI", ai_signal * self.config['ai_weight']),
            ("Sentiment", sentiment_signal * self.config['sentiment_weight']),
            ("Technical", technical_signal * self.config['technical_weight'])
        ]
        
        strongest = max(signals, key=lambda x: abs(x[1]))
        
        explanation = (
            f"Final Score: {final_score:+.3f} | "
            f"Strongest Signal: {strongest[0]} ({strongest[1]:+.3f}) | "
            f"Components: {' | '.join(components)}"
        )
        
        return explanation
    
    def update_config(self, new_config: Dict) -> None:
        """Update kernel configuration."""
        self.config.update(new_config)
        
        # Validate weights sum to 1.0
        weight_sum = (
            self.config["ml_weight"] + 
            self.config["ai_weight"] + 
            self.config["sentiment_weight"] + 
            self.config["technical_weight"]
        )
        
        if abs(weight_sum - 1.0) > 0.01:
            logging.warning(f"Signal weights sum to {weight_sum:.3f}, not 1.0. Consider rebalancing.")
    
    def get_config(self) -> Dict:
        """Get current configuration."""
        return self.config.copy()


# Factory function for easy instantiation
def create_alpha_kernel(config: Optional[Dict] = None) -> AlphaKernel:
    """Create and return configured AlphaKernel instance."""
    return AlphaKernel(config)


# Example usage and testing
if __name__ == "__main__":
    # Create kernel with default config
    kernel = create_alpha_kernel()
    
    # Example signal calculation
    example_result = kernel.calculate_final_signal(
        ml_prediction=1,
        ai_analysis={
            "confidence": 0.85,
            "recommendation": "BUY"
        },
        sentiment_scores={
            "news_sentiment": 0.3,
            "social_sentiment": 0.6,
            "news_count": 25,
            "social_count": 150
        },
        technical_signals={
            "confluence_score": 75,
            "trend_direction": 0.4,
            "momentum": 0.2
        },
        market_volatility=0.025
    )
    
    print("Example Alpha Kernel Result:")
    print(f"Decision: {example_result['decision']}")
    print(f"Final Score: {example_result['final_score']:.3f}")
    print(f"Position Size: {example_result['position_size']:.1%}")
    print(f"Explanation: {example_result['explanation']}")