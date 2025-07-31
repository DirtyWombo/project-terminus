"""
Meta-Model Signal Optimizer - Tier 1 Implementation
==================================================

Expert guidance: "Your entire PnL engine is currently based on arbitrary, static weights. 
This is the single biggest flaw in the alpha generation process."

Day 1 Implementation: Meta-model that learns optimal signal weights from historical performance
Upgrade Path: Advanced gradient boosting with real-time optimization and regime awareness
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import shap

# Database imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from trader_app.models import db, Trade, Price

logging.basicConfig(level=logging.INFO)

@dataclass
class MetaModelPrediction:
    """Container for meta-model predictions"""
    ml_weight: float
    ai_weight: float
    sentiment_weight: float
    technical_weight: float
    expected_return: float
    confidence: float
    market_regime: str
    prediction_timestamp: datetime

@dataclass
class MetaModelPerformance:
    """Container for meta-model performance metrics"""
    r2_score: float
    mse: float
    feature_importance: Dict[str, float]
    training_samples: int
    validation_samples: int
    last_updated: datetime

class MetaSignalOptimizer:
    """
    Day 1 Implementation: Meta-model for dynamic signal weighting
    
    Replaces static weights with learned optimal combinations based on:
    - Historical performance data
    - Market regime conditions
    - Signal strength patterns
    """
    
    def __init__(self, lookback_days: int = 90):
        self.lookback_days = lookback_days
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42
        )
        self.is_trained = False
        self.last_training_time = None
        self.performance_metrics = None
        self.feature_names = [
            'ml_signal', 'ai_signal', 'sentiment_signal', 'technical_signal',
            'market_regime_bull', 'market_regime_bear', 'market_regime_neutral',
            'volatility', 'volume_ratio'
        ]
        self.fallback_weights = {
            'ml_weight': 0.40,
            'ai_weight': 0.30,
            'sentiment_weight': 0.20,
            'technical_weight': 0.10
        }
        
    def prepare_training_data(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Prepare training data from historical trades and market data
        
        Returns:
            Tuple of (features, targets) or None if insufficient data
        """
        try:
            # Get historical trades
            cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
            trades = Trade.query.filter(Trade.timestamp >= cutoff_date).all()
            
            if len(trades) < 20:  # Minimum trades for training
                logging.warning(f"Insufficient trades for meta-model training: {len(trades)}")
                return None
            
            features = []
            targets = []
            
            for trade in trades:
                # Get market context at trade time
                market_context = self._get_market_context_at_time(trade.timestamp, trade.symbol)
                
                if market_context is None:
                    continue
                
                # Calculate forward return (target variable)
                forward_return = self._calculate_forward_return(trade)
                
                if forward_return is None:
                    continue
                
                # Create feature vector
                feature_vector = [
                    market_context['ml_signal'],
                    market_context['ai_signal'],
                    market_context['sentiment_signal'],
                    market_context['technical_signal'],
                    1.0 if market_context['market_regime'] == 'bull' else 0.0,
                    1.0 if market_context['market_regime'] == 'bear' else 0.0,
                    1.0 if market_context['market_regime'] == 'neutral' else 0.0,
                    market_context['volatility'],
                    market_context['volume_ratio']
                ]
                
                features.append(feature_vector)
                targets.append(forward_return)
            
            if len(features) < 10:
                logging.warning(f"Insufficient feature data for training: {len(features)}")
                return None
            
            logging.info(f"Prepared {len(features)} training samples for meta-model")
            return np.array(features), np.array(targets)
            
        except Exception as e:
            logging.error(f"Error preparing training data: {e}")
            return None
    
    def _get_market_context_at_time(self, timestamp: datetime, symbol: str) -> Optional[Dict]:
        """
        Get market context at specific time for feature generation
        
        This is a simplified version - in production, you'd store signal history
        """
        try:
            # For Day 1 implementation, we'll use synthetic market context
            # In production, you'd store historical signal values
            
            # Get price data around the trade time
            price_data = Price.query.filter(
                Price.symbol == symbol,
                Price.timestamp <= timestamp,
                Price.timestamp >= timestamp - timedelta(hours=1)
            ).order_by(Price.timestamp.desc()).first()
            
            if not price_data:
                return None
            
            # Calculate basic market indicators
            recent_prices = Price.query.filter(
                Price.symbol == symbol,
                Price.timestamp <= timestamp,
                Price.timestamp >= timestamp - timedelta(days=1)
            ).order_by(Price.timestamp.desc()).limit(24).all()
            
            if len(recent_prices) < 5:
                return None
            
            prices = [float(p.close) for p in recent_prices]
            volumes = [float(p.volume) for p in recent_prices]
            
            # Calculate synthetic signals for training
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns) if len(returns) > 1 else 0.02
            
            # Synthetic signal generation (replace with actual signal history in production)
            ml_signal = np.random.normal(0, 0.3)  # Mock ML signal
            ai_signal = np.random.normal(0, 0.25)  # Mock AI signal
            sentiment_signal = np.random.normal(0, 0.2)  # Mock sentiment
            technical_signal = np.random.normal(0, 0.15)  # Mock technical
            
            # Market regime classification (simplified)
            if np.mean(returns) > 0.01:
                market_regime = 'bull'
            elif np.mean(returns) < -0.01:
                market_regime = 'bear'
            else:
                market_regime = 'neutral'
            
            return {
                'ml_signal': ml_signal,
                'ai_signal': ai_signal,
                'sentiment_signal': sentiment_signal,
                'technical_signal': technical_signal,
                'market_regime': market_regime,
                'volatility': volatility,
                'volume_ratio': volumes[0] / np.mean(volumes) if len(volumes) > 1 else 1.0
            }
            
        except Exception as e:
            logging.error(f"Error getting market context: {e}")
            return None
    
    def _calculate_forward_return(self, trade: Trade) -> Optional[float]:
        """
        Calculate forward return for trade (target variable)
        """
        try:
            # Get price 1 hour after trade
            future_price = Price.query.filter(
                Price.symbol == trade.symbol,
                Price.timestamp >= trade.timestamp,
                Price.timestamp <= trade.timestamp + timedelta(hours=1)
            ).order_by(Price.timestamp.asc()).first()
            
            if not future_price:
                return None
            
            # Calculate return based on trade direction
            trade_price = float(trade.price)
            future_price_value = float(future_price.close)
            
            if trade.type == 'BUY':
                return (future_price_value - trade_price) / trade_price
            else:  # SELL
                return (trade_price - future_price_value) / trade_price
                
        except Exception as e:
            logging.error(f"Error calculating forward return: {e}")
            return None
    
    def train_meta_model(self) -> bool:
        """
        Train the meta-model on historical data
        
        Returns:
            True if training successful, False otherwise
        """
        try:
            # Prepare training data
            training_data = self.prepare_training_data()
            if training_data is None:
                logging.error("Failed to prepare training data")
                return False
            
            X, y = training_data
            
            # Time series split for validation
            tscv = TimeSeriesSplit(n_splits=3)
            
            # Train the model
            self.model.fit(X, y)
            
            # Validate performance
            validation_scores = []
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                # Fit on training set
                temp_model = GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=4,
                    random_state=42
                )
                temp_model.fit(X_train, y_train)
                
                # Validate
                val_pred = temp_model.predict(X_val)
                val_score = r2_score(y_val, val_pred)
                validation_scores.append(val_score)
            
            # Calculate performance metrics
            train_pred = self.model.predict(X)
            train_r2 = r2_score(y, train_pred)
            train_mse = mean_squared_error(y, train_pred)
            val_r2 = np.mean(validation_scores)
            
            # Feature importance
            feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
            
            self.performance_metrics = MetaModelPerformance(
                r2_score=train_r2,
                mse=train_mse,
                feature_importance=feature_importance,
                training_samples=len(X),
                validation_samples=len(X) // 3,  # Approximate
                last_updated=datetime.now()
            )
            
            self.is_trained = True
            self.last_training_time = datetime.now()
            
            logging.info(f"Meta-model trained successfully:")
            logging.info(f"  Training R²: {train_r2:.3f}")
            logging.info(f"  Validation R²: {val_r2:.3f}")
            logging.info(f"  Training samples: {len(X)}")
            logging.info(f"  Top features: {sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:3]}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error training meta-model: {e}")
            return False
    
    def predict_optimal_weights(
        self,
        ml_signal: float,
        ai_signal: float,
        sentiment_signal: float,
        technical_signal: float,
        market_regime: str = "neutral",
        volatility: float = 0.02,
        volume_ratio: float = 1.0
    ) -> MetaModelPrediction:
        """
        Predict optimal signal weights for current market conditions
        
        Returns:
            MetaModelPrediction with optimal weights and expected return
        """
        try:
            if not self.is_trained:
                logging.warning("Meta-model not trained, using fallback weights")
                return self._get_fallback_prediction(market_regime)
            
            # Prepare feature vector
            feature_vector = np.array([[
                ml_signal,
                ai_signal,
                sentiment_signal,
                technical_signal,
                1.0 if market_regime == 'bull' else 0.0,
                1.0 if market_regime == 'bear' else 0.0,
                1.0 if market_regime == 'neutral' else 0.0,
                volatility,
                volume_ratio
            ]])
            
            # Get prediction
            expected_return = self.model.predict(feature_vector)[0]
            
            # Calculate weights using SHAP values
            weights = self._calculate_weights_from_shap(feature_vector, ml_signal, ai_signal, sentiment_signal, technical_signal)
            
            # Calculate confidence based on model certainty
            confidence = self._calculate_prediction_confidence(feature_vector, expected_return)
            
            return MetaModelPrediction(
                ml_weight=weights['ml_weight'],
                ai_weight=weights['ai_weight'],
                sentiment_weight=weights['sentiment_weight'],
                technical_weight=weights['technical_weight'],
                expected_return=expected_return,
                confidence=confidence,
                market_regime=market_regime,
                prediction_timestamp=datetime.now()
            )
            
        except Exception as e:
            logging.error(f"Error predicting optimal weights: {e}")
            return self._get_fallback_prediction(market_regime)
    
    def _calculate_weights_from_shap(
        self,
        feature_vector: np.ndarray,
        ml_signal: float,
        ai_signal: float,
        sentiment_signal: float,
        technical_signal: float
    ) -> Dict[str, float]:
        """
        Calculate optimal weights using SHAP importance values
        """
        try:
            # Get SHAP values
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(feature_vector)[0]
            
            # Extract signal-specific SHAP values
            signal_shap_values = shap_values[:4]  # First 4 features are signals
            
            # Calculate weights based on absolute SHAP importance
            abs_shap_values = np.abs(signal_shap_values)
            
            # Handle case where all SHAP values are zero
            if np.sum(abs_shap_values) == 0:
                return self.fallback_weights
            
            # Normalize to create weights
            normalized_weights = abs_shap_values / np.sum(abs_shap_values)
            
            return {
                'ml_weight': normalized_weights[0],
                'ai_weight': normalized_weights[1],
                'sentiment_weight': normalized_weights[2],
                'technical_weight': normalized_weights[3]
            }
            
        except Exception as e:
            logging.error(f"Error calculating SHAP weights: {e}")
            return self.fallback_weights
    
    def _calculate_prediction_confidence(self, feature_vector: np.ndarray, prediction: float) -> float:
        """
        Calculate confidence in the prediction
        """
        try:
            # Use ensemble variance as confidence measure
            # Get predictions from individual trees
            tree_predictions = []
            for tree in self.model.estimators_:
                tree_pred = tree[0].predict(feature_vector)[0]
                tree_predictions.append(tree_pred)
            
            # Calculate variance (higher variance = lower confidence)
            prediction_variance = np.var(tree_predictions)
            
            # Convert to confidence score (0-1)
            confidence = 1.0 / (1.0 + prediction_variance * 100)
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logging.error(f"Error calculating confidence: {e}")
            return 0.5  # Default moderate confidence
    
    def _get_fallback_prediction(self, market_regime: str) -> MetaModelPrediction:
        """
        Get fallback prediction when meta-model is not available
        """
        # Adjust weights slightly based on market regime
        if market_regime == 'bull':
            weights = {
                'ml_weight': 0.35,
                'ai_weight': 0.35,
                'sentiment_weight': 0.20,
                'technical_weight': 0.10
            }
        elif market_regime == 'bear':
            weights = {
                'ml_weight': 0.45,
                'ai_weight': 0.25,
                'sentiment_weight': 0.15,
                'technical_weight': 0.15
            }
        else:  # neutral
            weights = self.fallback_weights
        
        return MetaModelPrediction(
            ml_weight=weights['ml_weight'],
            ai_weight=weights['ai_weight'],
            sentiment_weight=weights['sentiment_weight'],
            technical_weight=weights['technical_weight'],
            expected_return=0.0,
            confidence=0.5,
            market_regime=market_regime,
            prediction_timestamp=datetime.now()
        )
    
    def should_retrain(self) -> bool:
        """
        Check if meta-model should be retrained
        """
        if not self.is_trained:
            return True
        
        if self.last_training_time is None:
            return True
        
        # Retrain weekly
        days_since_training = (datetime.now() - self.last_training_time).days
        return days_since_training >= 7
    
    def get_performance_summary(self) -> Dict:
        """
        Get summary of meta-model performance
        """
        if not self.is_trained or self.performance_metrics is None:
            return {
                'status': 'not_trained',
                'message': 'Meta-model not trained yet'
            }
        
        return {
            'status': 'trained',
            'r2_score': self.performance_metrics.r2_score,
            'mse': self.performance_metrics.mse,
            'training_samples': self.performance_metrics.training_samples,
            'last_updated': self.performance_metrics.last_updated.isoformat(),
            'top_features': sorted(
                self.performance_metrics.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def save_model(self, filepath: str) -> bool:
        """
        Save trained meta-model to disk
        """
        try:
            if not self.is_trained:
                logging.warning("Cannot save untrained model")
                return False
            
            model_data = {
                'model': self.model,
                'performance_metrics': self.performance_metrics,
                'last_training_time': self.last_training_time,
                'feature_names': self.feature_names
            }
            
            joblib.dump(model_data, filepath)
            logging.info(f"Meta-model saved to {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, filepath: str) -> bool:
        """
        Load trained meta-model from disk
        """
        try:
            if not os.path.exists(filepath):
                logging.info(f"Model file not found: {filepath}")
                return False
            
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.performance_metrics = model_data['performance_metrics']
            self.last_training_time = model_data['last_training_time']
            self.feature_names = model_data['feature_names']
            self.is_trained = True
            
            logging.info(f"Meta-model loaded from {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"Error loading model: {e}")
            return False


# Factory function
def create_meta_signal_optimizer(lookback_days: int = 90) -> MetaSignalOptimizer:
    """Create configured meta-signal optimizer"""
    return MetaSignalOptimizer(lookback_days=lookback_days)


# Example usage
if __name__ == "__main__":
    # Create optimizer
    optimizer = create_meta_signal_optimizer()
    
    # Train model
    if optimizer.train_meta_model():
        print("Training successful!")
        
        # Get performance summary
        performance = optimizer.get_performance_summary()
        print(f"Performance: {performance}")
        
        # Test prediction
        prediction = optimizer.predict_optimal_weights(
            ml_signal=0.5,
            ai_signal=0.3,
            sentiment_signal=0.2,
            technical_signal=0.1,
            market_regime="bull"
        )
        
        print(f"Optimal weights: ML={prediction.ml_weight:.2f}, AI={prediction.ai_weight:.2f}")
        print(f"Expected return: {prediction.expected_return:.4f}")
        print(f"Confidence: {prediction.confidence:.2f}")
    else:
        print("Training failed")