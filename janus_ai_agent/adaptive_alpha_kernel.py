"""
Adaptive Alpha Kernel - Enhanced with Meta-Model Integration
===========================================================

This module integrates the meta-model optimizer with the Alpha Kernel
to provide dynamic signal weighting based on market conditions.

Day 1 Implementation: Replace static weights with learned optimal weights
Upgrade Path: Real-time weight optimization with advanced market regime detection
"""

import logging
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
import os

from .alpha_kernel import AlphaKernel
from .meta_signal_optimizer import create_meta_signal_optimizer, MetaSignalOptimizer

logging.basicConfig(level=logging.INFO)

class AdaptiveAlphaKernel(AlphaKernel):
    """
    Enhanced Alpha Kernel with dynamic signal weighting
    
    Replaces static weights with meta-model predictions based on:
    - Current market conditions
    - Historical performance patterns
    - Signal strength characteristics
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize adaptive alpha kernel"""
        super().__init__(config)
        
        # Initialize meta-model optimizer
        self.meta_optimizer = create_meta_signal_optimizer()
        self.use_meta_model = True
        self.last_meta_update = None
        
        # Model persistence
        self.model_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'shared_models', 
            'meta_signal_optimizer.joblib'
        )
        
        # Try to load existing model
        if os.path.exists(self.model_path):
            self.meta_optimizer.load_model(self.model_path)
        
        # Track performance for adaptive learning
        self.performance_history = []
        
    def calculate_adaptive_signal(
        self,
        ml_prediction: int,
        ai_analysis: Dict,
        sentiment_scores: Dict,
        technical_signals: Dict,
        market_volatility: float = 0.02,
        market_regime: str = "neutral"
    ) -> Dict:
        """
        Calculate final trading signal with adaptive weighting
        
        Args:
            ml_prediction: ML model output (-1, 0, 1)
            ai_analysis: AI analysis with confidence scores
            sentiment_scores: Market sentiment data
            technical_signals: Technical analysis signals
            market_volatility: Current market volatility
            market_regime: Current market regime (bull/bear/neutral)
            
        Returns:
            Enhanced signal result with adaptive weights
        """
        
        # 1. Calculate individual signal components (same as base kernel)
        ml_signal = float(ml_prediction)
        ai_signal = self._extract_quantitative_ai_signal(ai_analysis)
        sentiment_signal = self._calculate_sentiment_signal(sentiment_scores)
        technical_signal = self._calculate_technical_signal(technical_signals)
        
        # 2. Get optimal weights from meta-model
        if self.use_meta_model and self.meta_optimizer.is_trained:
            weight_prediction = self.meta_optimizer.predict_optimal_weights(
                ml_signal=ml_signal,
                ai_signal=ai_signal,
                sentiment_signal=sentiment_signal,
                technical_signal=technical_signal,
                market_regime=market_regime,
                volatility=market_volatility,
                volume_ratio=self._estimate_volume_ratio()
            )
            
            # Use predicted weights
            weights = {
                'ml_weight': weight_prediction.ml_weight,
                'ai_weight': weight_prediction.ai_weight,
                'sentiment_weight': weight_prediction.sentiment_weight,
                'technical_weight': weight_prediction.technical_weight
            }
            
            expected_return = weight_prediction.expected_return
            meta_confidence = weight_prediction.confidence
            
            logging.info(f"Using adaptive weights: ML={weights['ml_weight']:.2f}, "
                        f"AI={weights['ai_weight']:.2f}, Sentiment={weights['sentiment_weight']:.2f}, "
                        f"Technical={weights['technical_weight']:.2f}")
            
        else:
            # Fallback to static weights
            weights = {
                'ml_weight': self.config['ml_weight'],
                'ai_weight': self.config['ai_weight'],
                'sentiment_weight': self.config['sentiment_weight'],
                'technical_weight': self.config['technical_weight']
            }
            expected_return = 0.0
            meta_confidence = 0.5
            
            logging.info("Using fallback static weights")
        
        # 3. Calculate final score with adaptive weights
        final_score = (
            weights['ml_weight'] * ml_signal +
            weights['ai_weight'] * ai_signal +
            weights['sentiment_weight'] * sentiment_signal +
            weights['technical_weight'] * technical_signal
        )
        
        # 4. Generate trading decision
        decision = self._generate_decision(final_score)
        
        # 5. Calculate adaptive position size
        position_size = self._calculate_adaptive_position_size(
            final_score,
            meta_confidence,
            market_volatility,
            expected_return
        )
        
        # 6. Create enhanced explanation
        explanation = self._generate_adaptive_explanation(
            ml_signal, ai_signal, sentiment_signal, technical_signal,
            weights, final_score, expected_return, meta_confidence
        )
        
        # 7. Return enhanced result
        result = {
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
            "adaptive_weights": weights,
            "expected_return": expected_return,
            "meta_confidence": meta_confidence,
            "market_regime": market_regime,
            "explanation": explanation,
            "market_volatility": market_volatility,
            "weight_source": "meta_model" if self.use_meta_model and self.meta_optimizer.is_trained else "static"
        }
        
        # Track performance for continuous learning
        self._track_prediction_performance(result)
        
        return result
    
    def _calculate_adaptive_position_size(
        self,
        final_score: float,
        meta_confidence: float,
        market_volatility: float,
        expected_return: float
    ) -> float:
        """
        Calculate position size with enhanced adaptive factors
        """
        # Start with base position size
        position_size = self.config["base_position_size"]
        
        # 1. Scale by signal strength
        signal_strength = abs(final_score)
        position_size *= (1.0 + signal_strength)
        
        # 2. Scale by meta-model confidence
        position_size *= (0.5 + meta_confidence * 0.5)
        
        # 3. Scale by expected return (higher expected return = larger position)
        if expected_return > 0:
            return_factor = min(2.0, 1.0 + expected_return * 10)
            position_size *= return_factor
        
        # 4. Adjust for volatility
        if self.config["volatility_scaling"]:
            volatility_factor = 1.0 / (1.0 + market_volatility * 15)
            position_size *= volatility_factor
        
        # 5. Ensure within bounds
        position_size = max(0.005, min(position_size, self.config["max_position_size"]))
        
        return position_size
    
    def _generate_adaptive_explanation(
        self,
        ml_signal: float,
        ai_signal: float,
        sentiment_signal: float,
        technical_signal: float,
        weights: Dict[str, float],
        final_score: float,
        expected_return: float,
        meta_confidence: float
    ) -> str:
        """
        Generate explanation with adaptive weight information
        """
        # Calculate weighted contributions
        contributions = {
            "ML": ml_signal * weights['ml_weight'],
            "AI": ai_signal * weights['ai_weight'],
            "Sentiment": sentiment_signal * weights['sentiment_weight'],
            "Technical": technical_signal * weights['technical_weight']
        }
        
        # Find strongest contributor
        strongest = max(contributions.items(), key=lambda x: abs(x[1]))
        
        # Format components with adaptive weights
        components = [
            f"ML: {ml_signal:+.2f}×{weights['ml_weight']:.2f}={contributions['ML']:+.3f}",
            f"AI: {ai_signal:+.2f}×{weights['ai_weight']:.2f}={contributions['AI']:+.3f}",
            f"Sentiment: {sentiment_signal:+.2f}×{weights['sentiment_weight']:.2f}={contributions['Sentiment']:+.3f}",
            f"Technical: {technical_signal:+.2f}×{weights['technical_weight']:.2f}={contributions['Technical']:+.3f}"
        ]
        
        weight_source = "adaptive" if self.use_meta_model and self.meta_optimizer.is_trained else "static"
        
        explanation = (
            f"Final Score: {final_score:+.3f} ({weight_source} weights) | "
            f"Expected Return: {expected_return:+.4f} | "
            f"Meta Confidence: {meta_confidence:.2f} | "
            f"Strongest: {strongest[0]} ({strongest[1]:+.3f}) | "
            f"Components: {' | '.join(components)}"
        )
        
        return explanation
    
    def _estimate_volume_ratio(self) -> float:
        """
        Estimate current volume ratio for meta-model
        
        This is a simplified implementation - in production,
        you'd have access to real-time volume data
        """
        # Return neutral volume ratio for now
        return 1.0
    
    def _track_prediction_performance(self, result: Dict):
        """
        Track prediction performance for continuous learning
        """
        try:
            performance_record = {
                'timestamp': datetime.now(),
                'final_score': result['final_score'],
                'decision': result['decision'],
                'expected_return': result['expected_return'],
                'meta_confidence': result['meta_confidence'],
                'weights': result['adaptive_weights'],
                'market_regime': result['market_regime']
            }
            
            self.performance_history.append(performance_record)
            
            # Keep only recent history (last 100 predictions)
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
                
        except Exception as e:
            logging.error(f"Error tracking performance: {e}")
    
    def update_meta_model(self, force_retrain: bool = False) -> bool:
        """
        Update meta-model with new data
        
        Args:
            force_retrain: Force retraining regardless of schedule
            
        Returns:
            True if update was successful
        """
        try:
            # Check if retraining is needed
            if not force_retrain and not self.meta_optimizer.should_retrain():
                return True
            
            logging.info("Updating meta-model with new data...")
            
            # Train the meta-model
            if self.meta_optimizer.train_meta_model():
                # Save the updated model
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                self.meta_optimizer.save_model(self.model_path)
                
                self.last_meta_update = datetime.now()
                logging.info("Meta-model updated successfully")
                return True
            else:
                logging.error("Failed to train meta-model")
                return False
                
        except Exception as e:
            logging.error(f"Error updating meta-model: {e}")
            return False
    
    def get_meta_model_status(self) -> Dict:
        """
        Get status of meta-model
        """
        performance = self.meta_optimizer.get_performance_summary()
        
        return {
            'is_trained': self.meta_optimizer.is_trained,
            'last_training': self.meta_optimizer.last_training_time.isoformat() if self.meta_optimizer.last_training_time else None,
            'last_update': self.last_meta_update.isoformat() if self.last_meta_update else None,
            'performance': performance,
            'should_retrain': self.meta_optimizer.should_retrain(),
            'use_meta_model': self.use_meta_model,
            'model_path': self.model_path
        }
    
    def enable_meta_model(self, enabled: bool = True):
        """
        Enable or disable meta-model usage
        """
        self.use_meta_model = enabled
        logging.info(f"Meta-model {'enabled' if enabled else 'disabled'}")
    
    def get_recent_performance(self) -> Dict:
        """
        Get recent performance statistics
        """
        if not self.performance_history:
            return {'message': 'No performance history available'}
        
        recent = self.performance_history[-20:]  # Last 20 predictions
        
        avg_confidence = np.mean([p['meta_confidence'] for p in recent])
        avg_expected_return = np.mean([p['expected_return'] for p in recent])
        
        decisions = [p['decision'] for p in recent]
        decision_counts = {
            'BUY': decisions.count('BUY'),
            'SELL': decisions.count('SELL'),
            'HOLD': decisions.count('HOLD'),
            'STRONG_BUY': decisions.count('STRONG_BUY'),
            'STRONG_SELL': decisions.count('STRONG_SELL')
        }
        
        return {
            'total_predictions': len(recent),
            'average_confidence': avg_confidence,
            'average_expected_return': avg_expected_return,
            'decision_distribution': decision_counts,
            'latest_prediction': recent[-1] if recent else None
        }


# Factory function for easy integration
def create_adaptive_alpha_kernel(config: Optional[Dict] = None) -> AdaptiveAlphaKernel:
    """Create configured adaptive alpha kernel"""
    return AdaptiveAlphaKernel(config)


# Example usage
if __name__ == "__main__":
    # Create adaptive kernel
    adaptive_kernel = create_adaptive_alpha_kernel()
    
    # Example prediction
    result = adaptive_kernel.calculate_adaptive_signal(
        ml_prediction=1,
        ai_analysis={
            "confidence": 0.85,
            "directional_bias": 0.6,
            "signal_strength": 0.8
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
        market_volatility=0.025,
        market_regime="bull"
    )
    
    print("Adaptive Alpha Kernel Result:")
    print(f"Decision: {result['decision']}")
    print(f"Final Score: {result['final_score']:.3f}")
    print(f"Expected Return: {result['expected_return']:.4f}")
    print(f"Meta Confidence: {result['meta_confidence']:.2f}")
    print(f"Weight Source: {result['weight_source']}")
    print(f"Explanation: {result['explanation']}")