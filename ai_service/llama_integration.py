"""
Llama AI Integration for CyberJackal MKVI
Provides intelligent market analysis and predictive insights
"""

import os
import json
import logging
import requests
import re
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LlamaAnalyzer:
    """
    Llama-powered market analysis and prediction service
    """
    
    def __init__(self):
        self.llama_url = os.getenv("LLAMA_API_URL", "http://localhost:11434")  # Ollama default
        self.model_name = os.getenv("LLAMA_MODEL", "llama3.2:latest")
        self.max_tokens = int(os.getenv("LLAMA_MAX_TOKENS", "1000"))
        self.temperature = float(os.getenv("LLAMA_TEMPERATURE", "0.7"))
        
    def _make_llama_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Make request to Llama API via Ollama with enhanced JSON formatting
        """
        try:
            # Enhanced prompt with stronger JSON enforcement
            enhanced_prompt = f"""CRITICAL INSTRUCTION: You MUST respond with ONLY valid JSON. No explanations, no additional text, no markdown formatting.

{prompt}

MANDATORY: Your response must start with {{ and end with }}. Nothing else."""

            payload = {
                "model": self.model_name,
                "prompt": enhanced_prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "stop": ["```", "Note:", "Explanation:", "Here is", "The analysis"]
                }
            }
            
            response = requests.post(
                f"{self.llama_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Llama API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Llama API: {e}")
            return None
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Robust JSON extraction from AI response with multiple fallback strategies.
        Addresses expert critique: Force structured JSON output.
        """
        if not response_text:
            return None
        
        # Strategy 1: Direct JSON parsing
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract JSON from text using regex
        json_patterns = [
            r'\{.*\}',  # Match anything between first { and last }
            r'```json\s*(\{.*?\})\s*```',  # Extract from markdown code blocks
            r'```\s*(\{.*?\})\s*```',  # Extract from general code blocks
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Find JSON-like structure
        start = response_text.find('{')
        end = response_text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            try:
                json_candidate = response_text[start:end+1]
                return json.loads(json_candidate)
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Clean common issues and retry
        cleaned_text = response_text.strip()
        # Remove common prefixes
        prefixes_to_remove = [
            "Here is the JSON:", "Here's the analysis:", "```json", "```", 
            "The analysis is:", "Analysis:", "JSON:"
        ]
        for prefix in prefixes_to_remove:
            if cleaned_text.startswith(prefix):
                cleaned_text = cleaned_text[len(prefix):].strip()
        
        # Remove common suffixes
        suffixes_to_remove = ["```", "That's the analysis.", "End of analysis."]
        for suffix in suffixes_to_remove:
            if cleaned_text.endswith(suffix):
                cleaned_text = cleaned_text[:-len(suffix)].strip()
        
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass
        
        logger.warning(f"Failed to extract JSON from response: {response_text[:200]}...")
        return None
    
    def _validate_required_fields(self, data: Dict, required_fields: Dict[str, type]) -> Dict[str, Any]:
        """
        Validate that response contains required fields with correct types.
        """
        validated_data = {}
        
        for field, expected_type in required_fields.items():
            if field in data:
                value = data[field]
                # Type conversion if needed
                if expected_type == float and isinstance(value, (int, str)):
                    try:
                        validated_data[field] = float(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert {field} to float: {value}")
                        validated_data[field] = 0.0
                elif expected_type == int and isinstance(value, (float, str)):
                    try:
                        validated_data[field] = int(float(value))
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert {field} to int: {value}")
                        validated_data[field] = 0
                elif isinstance(value, expected_type):
                    validated_data[field] = value
                else:
                    logger.warning(f"Type mismatch for {field}: expected {expected_type}, got {type(value)}")
                    # Provide default based on type
                    if expected_type == float:
                        validated_data[field] = 0.0
                    elif expected_type == int:
                        validated_data[field] = 0
                    elif expected_type == str:
                        validated_data[field] = str(value)
                    elif expected_type == list:
                        validated_data[field] = []
                    elif expected_type == dict:
                        validated_data[field] = {}
            else:
                # Provide default for missing fields
                if expected_type == float:
                    validated_data[field] = 0.0
                elif expected_type == int:
                    validated_data[field] = 0
                elif expected_type == str:
                    validated_data[field] = "UNKNOWN"
                elif expected_type == list:
                    validated_data[field] = []
                elif expected_type == dict:
                    validated_data[field] = {}
                    
                logger.warning(f"Missing required field {field}, using default")
        
        return validated_data
    
    def analyze_market_sentiment(self, news_data: Dict, social_data: Dict, price_data: Dict) -> Dict[str, Any]:
        """
        Analyze market sentiment using Llama
        """
        prompt = f"""
        You are a senior quantitative analyst at a leading crypto hedge fund. Analyze the following market data and provide your professional assessment.

        MARKET DATA:
        - News Sentiment: {news_data.get('sentiment_label', 'Unknown')} ({news_data.get('article_count', 0)} articles)
        - Social Sentiment: {social_data.get('sentiment_label', 'Unknown')} ({social_data.get('mention_count', 0)} mentions)
        - Trending Topics: {', '.join(social_data.get('trending_topics', []))}
        - Price Change 24h: {price_data.get('price_change_24h', 'Unknown')}%
        - Market Regime: {price_data.get('regime', 'Unknown')}

        Provide your analysis in JSON format with these exact keys:
        {{
            "overall_sentiment": "BULLISH/BEARISH/NEUTRAL",
            "confidence_score": 0.85,
            "key_factors": ["factor1", "factor2", "factor3"],
            "risk_assessment": "LOW/MEDIUM/HIGH",
            "market_outlook": "1-2 sentence outlook",
            "recommended_action": "BUY/SELL/HOLD"
        }}

        Respond ONLY with valid JSON, no additional text.
        """
        
        response = self._make_llama_request(prompt)
        
        if response and 'response' in response:
            # Use robust JSON extraction
            analysis = self._extract_json_from_response(response['response'])
            
            if analysis:
                # Validate required fields for sentiment analysis
                required_fields = {
                    "overall_sentiment": str,
                    "confidence_score": float,
                    "key_factors": list,
                    "risk_assessment": str,
                    "market_outlook": str,
                    "recommended_action": str
                }
                
                validated_analysis = self._validate_required_fields(analysis, required_fields)
                
                # Ensure confidence_score is within valid range
                validated_analysis["confidence_score"] = max(0.0, min(1.0, validated_analysis["confidence_score"]))
                
                return validated_analysis
            else:
                logger.error("Failed to extract JSON from Llama sentiment response")
                return self._get_fallback_analysis()
        
        return self._get_fallback_analysis()
    
    def generate_speculative_analysis(self, symbol: str, context_data: Dict) -> Dict[str, Any]:
        """
        Generate quantitative speculative analysis for alpha kernel integration.
        
        This addresses expert critique: AI must output structured, numerical data
        that can be directly ingested by the decision engine.
        """
        prompt = f"""
        As a senior quantitative analyst, provide QUANTITATIVE analysis for {symbol} trading signals.

        CONTEXT DATA:
        - Current Price: ${context_data.get('current_price', 'N/A')}
        - 24h Change: {context_data.get('price_change_24h', 0):.2%}
        - 7d Change: {context_data.get('price_change_7d', 0):.2%}
        - Volume: {context_data.get('volume', 'N/A')}
        - News Sentiment: {context_data.get('average_sentiment', 0):.2f}
        - Market Regime: {context_data.get('current_regime', 'Unknown')}
        - Recent Headlines: {context_data.get('recent_headlines', [])}

        CRITICAL: Provide QUANTITATIVE analysis in EXACT JSON format for algorithmic trading:
        {{
            "recommendation": "BUY|SELL|HOLD|STRONG_BUY|STRONG_SELL",
            "confidence": 0.85,
            "directional_bias": 0.6,
            "signal_strength": 0.8,
            "time_horizon_days": 7,
            "bullish_factors": [
                {{"factor": "ETF_INFLOWS", "weight": 0.3, "impact": 0.7}},
                {{"factor": "TECHNICAL_BREAKOUT", "weight": 0.25, "impact": 0.6}},
                {{"factor": "SENTIMENT_SURGE", "weight": 0.2, "impact": 0.5}}
            ],
            "bearish_factors": [
                {{"factor": "REGULATORY_RISK", "weight": 0.4, "impact": -0.3}},
                {{"factor": "PROFIT_TAKING", "weight": 0.3, "impact": -0.2}}
            ],
            "price_targets": {{
                "support_1": {context_data.get('current_price', 50000) * 0.95},
                "support_2": {context_data.get('current_price', 50000) * 0.90},
                "resistance_1": {context_data.get('current_price', 50000) * 1.05},
                "resistance_2": {context_data.get('current_price', 50000) * 1.10},
                "target_7d": {context_data.get('current_price', 50000) * 1.03}
            }},
            "risk_metrics": {{
                "expected_volatility": 0.025,
                "max_adverse_move": 0.08,
                "probability_of_profit": 0.65
            }},
            "narrative_strength": 0.7,
            "momentum_score": 0.6,
            "velocity_score": 0.65,
            "short_term_outlook": "Brief technical summary",
            "medium_term_outlook": "Brief fundamental summary"
        }}

        RESPOND ONLY WITH VALID JSON. ALL NUMERIC VALUES MUST BE NUMBERS, NOT STRINGS.
        """
        
        response = self._make_llama_request(prompt)
        
        if response and 'response' in response:
            # Use robust JSON extraction
            analysis = self._extract_json_from_response(response['response'])
            
            if analysis:
                # Validate required fields for speculative analysis
                required_fields = {
                    "recommendation": str,
                    "confidence": float,
                    "directional_bias": float,
                    "signal_strength": float,
                    "time_horizon_days": int,
                    "bullish_factors": list,
                    "bearish_factors": list,
                    "price_targets": dict,
                    "risk_metrics": dict,
                    "narrative_strength": float,
                    "momentum_score": float,
                    "velocity_score": float,
                    "short_term_outlook": str,
                    "medium_term_outlook": str
                }
                
                validated_analysis = self._validate_required_fields(analysis, required_fields)
                
                # Ensure critical numeric fields are within valid ranges
                validated_analysis["confidence"] = max(0.0, min(1.0, validated_analysis["confidence"]))
                validated_analysis["directional_bias"] = max(-1.0, min(1.0, validated_analysis["directional_bias"]))
                validated_analysis["signal_strength"] = max(0.0, min(1.0, validated_analysis["signal_strength"]))
                validated_analysis["narrative_strength"] = max(0.0, min(1.0, validated_analysis["narrative_strength"]))
                validated_analysis["momentum_score"] = max(0.0, min(1.0, validated_analysis["momentum_score"]))
                validated_analysis["velocity_score"] = max(-1.0, min(1.0, validated_analysis["velocity_score"]))
                
                # Validate recommendation is one of expected values
                valid_recommendations = ["BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL"]
                if validated_analysis["recommendation"] not in valid_recommendations:
                    validated_analysis["recommendation"] = "HOLD"
                    logger.warning(f"Invalid recommendation received, defaulting to HOLD")
                
                return validated_analysis
            else:
                logger.error("Failed to extract JSON from Llama speculative analysis")
                return self._get_fallback_speculative_analysis(symbol)
        
        return self._get_fallback_speculative_analysis(symbol)
    
    def generate_risk_assessment(self, portfolio_data: Dict, market_data: Dict) -> Dict[str, Any]:
        """
        Generate comprehensive risk assessment using Llama
        """
        prompt = f"""
        As a risk management expert, assess the portfolio risk based on the following data:

        PORTFOLIO DATA:
        - Portfolio Value: ${portfolio_data.get('value', 0):,.2f}
        - Sharpe Ratio: {portfolio_data.get('sharpe_ratio', 0):.3f}
        - Max Drawdown: {portfolio_data.get('max_drawdown', 0):.1%}
        - Volatility: {portfolio_data.get('volatility', 0):.1%}
        - Beta: {portfolio_data.get('beta', 1.0):.3f}

        MARKET DATA:
        - Market Regime: {market_data.get('regime', 'Unknown')}
        - Bull Probability: {market_data.get('bull_probability', 50)}%
        - Confluence Score: {market_data.get('confluence_score', 50)}/100

        Provide risk assessment in JSON format:
        {{
            "overall_risk": "LOW/MEDIUM/HIGH",
            "risk_score": 0.65,
            "risk_factors": ["factor1", "factor2"],
            "recommendations": ["rec1", "rec2"],
            "position_sizing": "REDUCE/MAINTAIN/INCREASE",
            "market_timing": "FAVORABLE/NEUTRAL/UNFAVORABLE"
        }}

        Respond ONLY with valid JSON.
        """
        
        response = self._make_llama_request(prompt)
        
        if response and 'response' in response:
            # Use robust JSON extraction
            assessment = self._extract_json_from_response(response['response'])
            
            if assessment:
                # Validate required fields for risk assessment
                required_fields = {
                    "overall_risk": str,
                    "risk_score": float,
                    "risk_factors": list,
                    "recommendations": list,
                    "position_sizing": str,
                    "market_timing": str
                }
                
                validated_assessment = self._validate_required_fields(assessment, required_fields)
                
                # Ensure risk_score is within valid range
                validated_assessment["risk_score"] = max(0.0, min(1.0, validated_assessment["risk_score"]))
                
                # Validate enum fields
                valid_risk_levels = ["LOW", "MEDIUM", "HIGH"]
                if validated_assessment["overall_risk"] not in valid_risk_levels:
                    validated_assessment["overall_risk"] = "MEDIUM"
                
                valid_position_sizing = ["REDUCE", "MAINTAIN", "INCREASE"]
                if validated_assessment["position_sizing"] not in valid_position_sizing:
                    validated_assessment["position_sizing"] = "MAINTAIN"
                
                valid_market_timing = ["FAVORABLE", "NEUTRAL", "UNFAVORABLE"]
                if validated_assessment["market_timing"] not in valid_market_timing:
                    validated_assessment["market_timing"] = "NEUTRAL"
                
                return validated_assessment
            else:
                logger.error("Failed to extract JSON from Llama risk assessment")
                return self._get_fallback_risk_assessment()
        
        return self._get_fallback_risk_assessment()
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when Llama is unavailable"""
        return {
            "overall_sentiment": "NEUTRAL",
            "confidence_score": 0.5,
            "key_factors": ["Llama analysis unavailable", "Using fallback data"],
            "risk_assessment": "MEDIUM",
            "market_outlook": "Analysis service temporarily unavailable",
            "recommended_action": "HOLD"
        }
    
    def _get_fallback_speculative_analysis(self, symbol: str) -> Dict[str, Any]:
        """Quantitative fallback analysis when Llama is unavailable"""
        return {
            "recommendation": "HOLD",
            "confidence": 0.5,
            "directional_bias": 0.0,
            "signal_strength": 0.0,
            "time_horizon_days": 7,
            "bullish_factors": [
                {"factor": "AI_SERVICE_UNAVAILABLE", "weight": 0.0, "impact": 0.0}
            ],
            "bearish_factors": [
                {"factor": "AI_SERVICE_UNAVAILABLE", "weight": 0.0, "impact": 0.0}
            ],
            "price_targets": {
                "support_1": 45000,
                "support_2": 42000,
                "resistance_1": 52000,
                "resistance_2": 55000,
                "target_7d": 50000
            },
            "risk_metrics": {
                "expected_volatility": 0.02,
                "max_adverse_move": 0.05,
                "probability_of_profit": 0.5
            },
            "narrative_strength": 0.5,
            "momentum_score": 0.5,
            "velocity_score": 0.5,
            "short_term_outlook": f"AI analysis for {symbol} temporarily unavailable",
            "medium_term_outlook": "Fallback to neutral assessment"
        }
    
    def _get_fallback_risk_assessment(self) -> Dict[str, Any]:
        """Fallback risk assessment when Llama is unavailable"""
        return {
            "overall_risk": "MEDIUM",
            "risk_score": 0.5,
            "risk_factors": ["AI analysis unavailable"],
            "recommendations": ["Reconnect Llama service", "Use manual analysis"],
            "position_sizing": "MAINTAIN",
            "market_timing": "NEUTRAL"
        }

# Global instance
llama_analyzer = LlamaAnalyzer()