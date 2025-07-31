"""
Ecosystem Analysis Engine - Enhanced Janus Feature
================================================

Provides comprehensive ecosystem analysis including:
- Parent chain analysis (ETH, SOL, BTC)
- Related meme coins and ecosystem tokens
- Cross-asset correlations and momentum
- Ecosystem-wide sentiment and trends
- Layer 2 and ecosystem health metrics
"""

import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trader_app.models import db, Price, Position
from trader_app import config_manager
from ai_service.llama_integration import LlamaAnalyzer

logging.basicConfig(level=logging.INFO)

class EcosystemAnalyzer:
    """
    Enhanced ecosystem analysis for comprehensive chain and meme coin coverage
    """
    
    def __init__(self):
        self.config = config_manager.get_config()
        self.llama_analyzer = LlamaAnalyzer()
        
        # Define ecosystem mappings
        self.ecosystems = {
            "ethereum": {
                "parent": "ETH-USD",
                "ecosystem_tokens": ["PEPE-USD", "SHIB-USD"],
                "layer2": ["MATIC-USD", "OP-USD", "ARB-USD"],
                "defi": ["UNI-USD", "AAVE-USD", "LINK-USD"],
                "name": "Ethereum Ecosystem"
            },
            "solana": {
                "parent": "SOL-USD", 
                "ecosystem_tokens": ["WIF-USD", "BONK-USD"],
                "layer2": [],  # Solana doesn't have L2s
                "defi": ["RAY-USD", "SRM-USD"],
                "name": "Solana Ecosystem"
            },
            "bitcoin": {
                "parent": "BTC-USD",
                "ecosystem_tokens": ["DOGE-USD"],  # Bitcoin-inspired
                "layer2": [],
                "defi": [],
                "name": "Bitcoin Ecosystem"
            }
        }
        
        # Command mappings for flexible input
        self.command_mappings = {
            "ETH": "ethereum",
            "ETH-USD": "ethereum", 
            "ETHEREUM": "ethereum",
            "SOL": "solana",
            "SOL-USD": "solana",
            "SOLANA": "solana",
            "BTC": "bitcoin",
            "BTC-USD": "bitcoin", 
            "BITCOIN": "bitcoin"
        }
        
    def analyze_ecosystem(self, ecosystem_input: str) -> Dict[str, Any]:
        """
        Comprehensive ecosystem analysis
        
        Args:
            ecosystem_input: Chain symbol (ETH, SOL, BTC) or full name
            
        Returns:
            Complete ecosystem analysis including all related tokens
        """
        # Normalize input
        ecosystem_key = self.command_mappings.get(ecosystem_input.upper())
        if not ecosystem_key:
            return {"error": f"Ecosystem '{ecosystem_input}' not supported. Use: ETH, SOL, or BTC"}
            
        ecosystem = self.ecosystems[ecosystem_key]
        
        # Get all tokens in ecosystem
        all_tokens = [ecosystem["parent"]]
        all_tokens.extend(ecosystem["ecosystem_tokens"])
        all_tokens.extend(ecosystem["layer2"])
        all_tokens.extend(ecosystem["defi"])
        
        # Filter to only tokens we actually track
        tracked_tokens = self._get_tracked_tokens(all_tokens)
        
        if not tracked_tokens:
            return {"error": f"No tracked tokens found for {ecosystem['name']}"}
        
        # Perform comprehensive analysis
        analysis = {
            "ecosystem": ecosystem["name"],
            "timestamp": datetime.now().isoformat(),
            "parent_chain": self._analyze_parent_chain(ecosystem["parent"]),
            "meme_coins": self._analyze_meme_coins(ecosystem["ecosystem_tokens"]),
            "ecosystem_health": self._calculate_ecosystem_health(tracked_tokens),
            "correlation_matrix": self._calculate_ecosystem_correlations(tracked_tokens),
            "momentum_analysis": self._analyze_ecosystem_momentum(tracked_tokens),
            "sentiment_analysis": self._analyze_ecosystem_sentiment(ecosystem_key, tracked_tokens),
            "ai_insights": self._generate_ecosystem_ai_analysis(ecosystem, tracked_tokens),
            "trading_recommendations": self._generate_trading_recommendations(ecosystem, tracked_tokens)
        }
        
        return analysis
    
    def _get_tracked_tokens(self, token_list: List[str]) -> List[str]:
        """Filter token list to only those we actually track"""
        try:
            # Get list of symbols we have price data for
            tracked_symbols = db.session.query(Price.symbol).distinct().all()
            tracked_symbols = [symbol[0] for symbol in tracked_symbols]
            
            # Filter to only tokens we track
            tracked_tokens = [token for token in token_list if token in tracked_symbols]
            return tracked_tokens
        except Exception as e:
            logging.warning(f"Error getting tracked tokens: {e}")
            # Fallback to known tokens
            return [token for token in token_list if token in ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "WIF-USD", "PEPE-USD", "BONK-USD", "SHIB-USD"]]
    
    def _analyze_parent_chain(self, parent_symbol: str) -> Dict[str, Any]:
        """Analyze the parent blockchain"""
        try:
            # Get recent price data
            cutoff_date = datetime.now() - timedelta(days=7)
            prices = Price.query.filter(
                Price.symbol == parent_symbol,
                Price.timestamp >= cutoff_date
            ).order_by(Price.timestamp.desc()).limit(100).all()
            
            if not prices:
                return {"error": f"No price data for {parent_symbol}"}
            
            # Calculate metrics
            price_series = pd.Series([float(p.close) for p in reversed(prices)])
            returns = price_series.pct_change().dropna()
            
            current_price = float(prices[0].close)
            price_7d_ago = float(prices[-1].close) if len(prices) > 1 else current_price
            return_7d = (current_price - price_7d_ago) / price_7d_ago
            volatility_7d = returns.std() * np.sqrt(24 * 7)  # Annualized
            
            return {
                "symbol": parent_symbol,
                "current_price": current_price,
                "return_7d": return_7d,
                "return_7d_percent": return_7d * 100,
                "volatility_7d": volatility_7d,
                "trend": "bullish" if return_7d > 0.02 else "bearish" if return_7d < -0.02 else "neutral",
                "price_momentum": "strong" if abs(return_7d) > 0.05 else "moderate" if abs(return_7d) > 0.02 else "weak"
            }
        except Exception as e:
            logging.error(f"Error analyzing parent chain {parent_symbol}: {e}")
            return {"error": f"Analysis failed for {parent_symbol}"}
    
    def _analyze_meme_coins(self, meme_symbols: List[str]) -> Dict[str, Any]:
        """Analyze meme coins in the ecosystem"""
        tracked_memes = self._get_tracked_tokens(meme_symbols)
        
        if not tracked_memes:
            return {"message": "No meme coins tracked in this ecosystem"}
        
        meme_analysis = {}
        total_return = 0
        total_volatility = 0
        count = 0
        
        for symbol in tracked_memes:
            try:
                # Get recent data
                cutoff_date = datetime.now() - timedelta(days=7)
                prices = Price.query.filter(
                    Price.symbol == symbol,
                    Price.timestamp >= cutoff_date
                ).order_by(Price.timestamp.desc()).limit(100).all()
                
                if len(prices) < 2:
                    continue
                
                # Calculate metrics
                current_price = float(prices[0].close)
                price_7d_ago = float(prices[-1].close)
                return_7d = (current_price - price_7d_ago) / price_7d_ago
                
                price_series = pd.Series([float(p.close) for p in reversed(prices)])
                returns = price_series.pct_change().dropna()
                volatility = returns.std() * np.sqrt(24 * 7)
                
                meme_analysis[symbol] = {
                    "return_7d_percent": return_7d * 100,
                    "volatility": volatility,
                    "momentum": "explosive" if return_7d > 0.20 else "strong" if return_7d > 0.10 else "moderate" if return_7d > 0.05 else "weak"
                }
                
                total_return += return_7d
                total_volatility += volatility
                count += 1
                
            except Exception as e:
                logging.warning(f"Error analyzing meme coin {symbol}: {e}")
                continue
        
        if count > 0:
            meme_analysis["aggregate"] = {
                "average_return_7d_percent": (total_return / count) * 100,
                "average_volatility": total_volatility / count,
                "meme_coin_count": count,
                "ecosystem_meme_sentiment": "bullish" if total_return > 0.1 else "bearish" if total_return < -0.1 else "neutral"
            }
        
        return meme_analysis
    
    def _calculate_ecosystem_health(self, tracked_tokens: List[str]) -> Dict[str, Any]:
        """Calculate overall ecosystem health metrics"""
        try:
            health_scores = []
            positive_performers = 0
            total_volume = 0
            
            for symbol in tracked_tokens:
                cutoff_date = datetime.now() - timedelta(days=7)
                prices = Price.query.filter(
                    Price.symbol == symbol,
                    Price.timestamp >= cutoff_date
                ).order_by(Price.timestamp.desc()).limit(50).all()
                
                if len(prices) < 2:
                    continue
                
                # Calculate health score based on price action and volume
                current_price = float(prices[0].close)
                price_7d_ago = float(prices[-1].close)
                return_7d = (current_price - price_7d_ago) / price_7d_ago
                
                # Volume trend (if available)
                volumes = [float(p.volume) for p in prices if hasattr(p, 'volume') and p.volume]
                avg_volume = np.mean(volumes) if volumes else 1000000  # Default fallback
                
                # Health score: positive returns + volume consistency
                health_score = max(0, min(100, 50 + (return_7d * 500)))  # Scale to 0-100
                health_scores.append(health_score)
                
                if return_7d > 0:
                    positive_performers += 1
                    
                total_volume += avg_volume
            
            if not health_scores:
                return {"error": "Insufficient data for health calculation"}
            
            overall_health = np.mean(health_scores)
            positive_ratio = positive_performers / len(tracked_tokens)
            
            # Determine health status
            if overall_health > 70 and positive_ratio > 0.6:
                status = "excellent"
            elif overall_health > 55 and positive_ratio > 0.4:
                status = "good"
            elif overall_health > 40:
                status = "fair"
            else:
                status = "poor"
            
            return {
                "overall_health_score": round(overall_health, 1),
                "health_status": status,
                "positive_performers": positive_performers,
                "total_tokens_analyzed": len(tracked_tokens),
                "positive_performer_ratio": round(positive_ratio * 100, 1),
                "ecosystem_volume_trend": "high" if total_volume > 10000000 else "moderate"
            }
            
        except Exception as e:
            logging.error(f"Error calculating ecosystem health: {e}")
            return {"error": "Health calculation failed"}
    
    def _calculate_ecosystem_correlations(self, tracked_tokens: List[str]) -> Dict[str, Any]:
        """Calculate correlation matrix for ecosystem tokens"""
        try:
            if len(tracked_tokens) < 2:
                return {"message": "Need at least 2 tokens for correlation analysis"}
            
            # Get 30-day price data for all tokens
            cutoff_date = datetime.now() - timedelta(days=30)
            
            price_data = {}
            for symbol in tracked_tokens:
                prices = Price.query.filter(
                    Price.symbol == symbol,
                    Price.timestamp >= cutoff_date
                ).order_by(Price.timestamp.asc()).all()
                
                if len(prices) >= 10:  # Minimum data points
                    price_series = pd.Series([float(p.close) for p in prices])
                    returns = price_series.pct_change().dropna()
                    price_data[symbol] = returns
            
            if len(price_data) < 2:
                return {"error": "Insufficient data for correlation analysis"}
            
            # Calculate correlation matrix
            returns_df = pd.DataFrame(price_data)
            correlation_matrix = returns_df.corr()
            
            # Extract meaningful correlations
            correlations = {}
            high_correlations = []
            
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    token1 = correlation_matrix.columns[i]
                    token2 = correlation_matrix.columns[j]
                    corr_value = correlation_matrix.iloc[i, j]
                    
                    correlations[f"{token1}-{token2}"] = round(corr_value, 3)
                    
                    if abs(corr_value) > 0.7:
                        high_correlations.append({
                            "pair": f"{token1} - {token2}",
                            "correlation": round(corr_value, 3),
                            "strength": "very high" if abs(corr_value) > 0.8 else "high"
                        })
            
            # Calculate average correlation
            corr_values = [abs(v) for v in correlations.values()]
            avg_correlation = np.mean(corr_values) if corr_values else 0
            
            return {
                "correlation_pairs": correlations,
                "high_correlations": high_correlations,
                "average_correlation": round(avg_correlation, 3),
                "ecosystem_cohesion": "strong" if avg_correlation > 0.6 else "moderate" if avg_correlation > 0.4 else "weak",
                "diversification_benefit": "low" if avg_correlation > 0.7 else "moderate" if avg_correlation > 0.5 else "high"
            }
            
        except Exception as e:
            logging.error(f"Error calculating correlations: {e}")
            return {"error": "Correlation analysis failed"}
    
    def _analyze_ecosystem_momentum(self, tracked_tokens: List[str]) -> Dict[str, Any]:
        """Analyze momentum across the ecosystem"""
        try:
            momentum_data = {}
            timeframes = {"24h": 1, "7d": 7, "30d": 30}
            
            for timeframe, days in timeframes.items():
                cutoff_date = datetime.now() - timedelta(days=days)
                returns = []
                
                for symbol in tracked_tokens:
                    prices = Price.query.filter(
                        Price.symbol == symbol,
                        Price.timestamp >= cutoff_date
                    ).order_by(Price.timestamp.asc()).all()
                    
                    if len(prices) >= 2:
                        start_price = float(prices[0].close)
                        end_price = float(prices[-1].close)
                        return_pct = ((end_price - start_price) / start_price) * 100
                        returns.append(return_pct)
                
                if returns:
                    avg_return = np.mean(returns)
                    momentum_data[timeframe] = {
                        "average_return_percent": round(avg_return, 2),
                        "positive_tokens": sum(1 for r in returns if r > 0),
                        "total_tokens": len(returns),
                        "momentum_strength": "strong" if avg_return > 5 else "moderate" if avg_return > 1 else "weak" if avg_return > -1 else "negative"
                    }
            
            # Overall momentum assessment
            if "7d" in momentum_data:
                momentum_trend = momentum_data["7d"]["momentum_strength"]
                momentum_consistency = len([tf for tf in momentum_data.values() if tf["momentum_strength"] in ["strong", "moderate"]])
            else:
                momentum_trend = "unknown"
                momentum_consistency = 0
            
            return {
                "timeframe_analysis": momentum_data,
                "overall_momentum": momentum_trend,
                "momentum_consistency": f"{momentum_consistency}/3 timeframes positive",
                "ecosystem_direction": "bullish" if momentum_trend in ["strong", "moderate"] else "bearish" if momentum_trend == "negative" else "neutral"
            }
            
        except Exception as e:
            logging.error(f"Error analyzing momentum: {e}")
            return {"error": "Momentum analysis failed"}
    
    def _analyze_ecosystem_sentiment(self, ecosystem_key: str, tracked_tokens: List[str]) -> Dict[str, Any]:
        """Analyze sentiment across the ecosystem"""
        try:
            # This would integrate with existing sentiment analysis
            # For now, provide structure for future enhancement
            
            return {
                "overall_sentiment": "neutral",
                "news_sentiment": 0.0,
                "social_sentiment": 0.0,
                "ecosystem_mentions": 0,
                "trending_topics": [],
                "sentiment_source": "placeholder - integrate with existing sentiment engine"
            }
            
        except Exception as e:
            logging.error(f"Error analyzing sentiment: {e}")
            return {"error": "Sentiment analysis failed"}
    
    def _generate_ecosystem_ai_analysis(self, ecosystem: Dict, tracked_tokens: List[str]) -> Dict[str, Any]:
        """Generate AI-powered ecosystem analysis"""
        try:
            # Prepare context for AI analysis
            ecosystem_context = {
                "ecosystem_name": ecosystem["name"],
                "parent_chain": ecosystem["parent"],
                "tracked_tokens": tracked_tokens,
                "analysis_type": "ecosystem_comprehensive"
            }
            
            # Generate AI analysis using existing Llama integration
            ai_analysis = self.llama_analyzer.generate_speculative_analysis(
                ecosystem["parent"], 
                ecosystem_context
            )
            
            # If AI analysis fails, provide structured fallback
            if not ai_analysis or "error" in str(ai_analysis):
                return {
                    "ecosystem_outlook": f"Comprehensive analysis for {ecosystem['name']} ecosystem",
                    "key_opportunities": ["Ecosystem expansion", "Cross-chain growth", "Meme coin momentum"],
                    "risk_factors": ["Market correlation", "Ecosystem concentration", "Regulatory uncertainty"],
                    "ai_recommendation": "HOLD",
                    "confidence": 0.6,
                    "analysis_source": "fallback_structured_analysis"
                }
            
            return ai_analysis
            
        except Exception as e:
            logging.error(f"Error generating AI analysis: {e}")
            return {"error": "AI analysis failed", "fallback": "enabled"}
    
    def _generate_trading_recommendations(self, ecosystem: Dict, tracked_tokens: List[str]) -> Dict[str, Any]:
        """Generate actionable trading recommendations"""
        try:
            recommendations = {
                "primary_opportunities": [],
                "risk_management": [],
                "position_sizing": {},
                "entry_strategies": [],
                "ecosystem_plays": []
            }
            
            # Analyze each token for opportunities
            for symbol in tracked_tokens:
                cutoff_date = datetime.now() - timedelta(days=7)
                prices = Price.query.filter(
                    Price.symbol == symbol,
                    Price.timestamp >= cutoff_date
                ).order_by(Price.timestamp.desc()).limit(50).all()
                
                if len(prices) >= 2:
                    current_price = float(prices[0].close)
                    price_7d_ago = float(prices[-1].close)
                    return_7d = (current_price - price_7d_ago) / price_7d_ago
                    
                    if return_7d > 0.10:  # Strong performer
                        recommendations["primary_opportunities"].append(f"{symbol}: Strong momentum (+{return_7d*100:.1f}%)")
                    elif return_7d < -0.10:  # Potential dip buy
                        recommendations["primary_opportunities"].append(f"{symbol}: Potential dip buy (-{abs(return_7d)*100:.1f}%)")
            
            # General ecosystem recommendations
            if ecosystem["parent"] in ["ETH-USD", "SOL-USD"]:
                recommendations["ecosystem_plays"].extend([
                    "Consider ecosystem diversification across meme coins",
                    "Monitor parent chain performance for ecosystem health",
                    "Watch for narrative-driven momentum in meme tokens"
                ])
            
            recommendations["risk_management"].extend([
                "Limit ecosystem exposure to 15-20% of portfolio",
                "Use correlation analysis for position sizing",
                "Set stop-losses for volatile meme positions"
            ])
            
            return recommendations
            
        except Exception as e:
            logging.error(f"Error generating recommendations: {e}")
            return {"error": "Recommendation generation failed"}

def create_ecosystem_analyzer():
    """Factory function to create EcosystemAnalyzer instance"""
    return EcosystemAnalyzer()