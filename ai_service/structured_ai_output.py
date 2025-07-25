"""
Structured AI Output Engine
============================

Converts Janus AI prose output to structured JSON with numerical confidence scores.
This addresses the expert critique requirement for machine-readable AI signals.

Features:
1. Structured JSON output with numerical scores
2. Confidence calibration and validation
3. Signal strength quantification
4. Factor-based analysis with weights
5. Machine-readable decision support
"""

import json
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO)

class MarketDirection(Enum):
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH" 
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"

class ConfidenceLevel(Enum):
    VERY_HIGH = "VERY_HIGH"  # 0.8-1.0
    HIGH = "HIGH"            # 0.6-0.8
    MEDIUM = "MEDIUM"        # 0.4-0.6
    LOW = "LOW"              # 0.2-0.4
    VERY_LOW = "VERY_LOW"    # 0.0-0.2

@dataclass
class MarketFactor:
    """Individual market factor with quantified impact."""
    name: str
    impact_score: float      # [-1.0, 1.0] impact on price
    confidence: float        # [0.0, 1.0] confidence in factor
    weight: float           # [0.0, 1.0] importance weight
    explanation: str
    
@dataclass
class StructuredMarketAnalysis:
    """Structured AI market analysis output."""
    # Core directional analysis
    directional_bias: float          # [-1.0, 1.0] overall direction
    signal_strength: float           # [0.0, 1.0] strength of signal
    confidence: float               # [0.0, 1.0] overall confidence
    velocity_score: float           # [-1.0, 1.0] narrative velocity acceleration
    
    # Market direction classification
    market_direction: MarketDirection
    confidence_level: ConfidenceLevel
    
    # Factor analysis
    bullish_factors: List[MarketFactor]
    bearish_factors: List[MarketFactor]
    neutral_factors: List[MarketFactor]
    
    # Quantitative scores
    bullish_score: float            # [0.0, 1.0] weighted bullish factors
    bearish_score: float            # [0.0, 1.0] weighted bearish factors
    net_sentiment: float            # [-1.0, 1.0] bullish_score - bearish_score
    
    # Risk assessment
    risk_level: str                 # LOW, MEDIUM, HIGH
    volatility_expectation: float   # [0.0, 1.0] expected volatility
    
    # Metadata
    analysis_timestamp: str
    model_version: str
    symbol: str
    
    # Raw AI output (for reference)
    raw_analysis: Optional[str] = None

class StructuredAIOutputEngine:
    """
    Engine to convert prose AI output to structured JSON format.
    """
    
    def __init__(self):
        """Initialize the structured output engine."""
        self.logger = logging.getLogger(__name__)
        
        # Confidence calibration parameters
        self.confidence_keywords = {
            'very_high': ['certain', 'definite', 'strong conviction', 'highly confident', 'very likely'],
            'high': ['confident', 'likely', 'probable', 'strong indication', 'clear signal'],
            'medium': ['moderate', 'possible', 'suggests', 'indicates', 'some evidence'],
            'low': ['uncertain', 'unclear', 'mixed signals', 'limited evidence', 'weak'],
            'very_low': ['very uncertain', 'no clear direction', 'conflicting', 'unreliable']
        }
        
        # Direction keywords
        self.direction_keywords = {
            'strong_bullish': ['very bullish', 'extremely bullish', 'strong buy', 'major upside'],
            'bullish': ['bullish', 'positive', 'upward', 'buy', 'upside potential'],
            'neutral': ['neutral', 'sideways', 'hold', 'mixed', 'balanced'],
            'bearish': ['bearish', 'negative', 'downward', 'sell', 'downside risk'],
            'strong_bearish': ['very bearish', 'extremely bearish', 'strong sell', 'major downside']
        }
        
        # Factor extraction patterns
        self.factor_patterns = {
            'bullish': [
                r'bullish factor[s]?[:\-]?\s*(.+?)(?=bearish|neutral|$)',
                r'positive[s]?[:\-]?\s*(.+?)(?=negative|bearish|$)',
                r'upside[s]?[:\-]?\s*(.+?)(?=downside|bearish|$)'
            ],
            'bearish': [
                r'bearish factor[s]?[:\-]?\s*(.+?)(?=bullish|neutral|$)',
                r'negative[s]?[:\-]?\s*(.+?)(?=positive|bullish|$)',
                r'downside[s]?[:\-]?\s*(.+?)(?=upside|bullish|$)'
            ],
            'neutral': [
                r'neutral factor[s]?[:\-]?\s*(.+?)(?=bullish|bearish|$)',
                r'mixed[:\-]?\s*(.+?)(?=bullish|bearish|$)'
            ]
        }
    
    def extract_confidence(self, text: str) -> tuple[float, ConfidenceLevel]:
        """Extract confidence score from text."""
        text_lower = text.lower()
        
        # Score based on keyword presence
        confidence_score = 0.5  # Default medium confidence
        confidence_level = ConfidenceLevel.MEDIUM
        
        for level, keywords in self.confidence_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if level == 'very_high':
                        confidence_score = 0.9
                        confidence_level = ConfidenceLevel.VERY_HIGH
                    elif level == 'high':
                        confidence_score = 0.75
                        confidence_level = ConfidenceLevel.HIGH
                    elif level == 'medium':
                        confidence_score = 0.5
                        confidence_level = ConfidenceLevel.MEDIUM
                    elif level == 'low':
                        confidence_score = 0.25
                        confidence_level = ConfidenceLevel.LOW
                    elif level == 'very_low':
                        confidence_score = 0.1
                        confidence_level = ConfidenceLevel.VERY_LOW
                    break
        
        # Adjust based on hedge words
        hedge_words = ['might', 'could', 'perhaps', 'possibly', 'maybe']
        for hedge in hedge_words:
            if hedge in text_lower:
                confidence_score *= 0.8  # Reduce confidence
                break
        
        return confidence_score, confidence_level
    
    def extract_direction(self, text: str) -> tuple[float, MarketDirection]:
        """Extract directional bias from text."""
        text_lower = text.lower()
        
        # Default neutral
        direction_score = 0.0
        direction = MarketDirection.NEUTRAL
        
        # Score based on directional keywords
        for dir_type, keywords in self.direction_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if dir_type == 'strong_bullish':
                        direction_score = 0.8
                        direction = MarketDirection.STRONG_BULLISH
                    elif dir_type == 'bullish':
                        direction_score = 0.4
                        direction = MarketDirection.BULLISH
                    elif dir_type == 'neutral':
                        direction_score = 0.0
                        direction = MarketDirection.NEUTRAL
                    elif dir_type == 'bearish':
                        direction_score = -0.4
                        direction = MarketDirection.BEARISH
                    elif dir_type == 'strong_bearish':
                        direction_score = -0.8
                        direction = MarketDirection.STRONG_BEARISH
                    break
        
        return direction_score, direction
    
    def extract_factors(self, text: str) -> Dict[str, List[MarketFactor]]:
        """Extract market factors from text."""
        factors = {
            'bullish': [],
            'bearish': [],
            'neutral': []
        }
        
        for factor_type, patterns in self.factor_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    factor_text = match.group(1).strip()
                    
                    # Split into individual factors
                    individual_factors = self._parse_factor_list(factor_text)
                    
                    for factor_info in individual_factors:
                        factor = MarketFactor(
                            name=factor_info['name'],
                            impact_score=factor_info['impact'],
                            confidence=factor_info['confidence'],
                            weight=factor_info['weight'],
                            explanation=factor_info['explanation']
                        )
                        factors[factor_type].append(factor)
        
        return factors
    
    def _parse_factor_list(self, factor_text: str) -> List[Dict]:
        """Parse a list of factors from text."""
        factors = []
        
        # Split by common delimiters
        factor_items = re.split(r'[,;]|\n|\s*-\s*|\s*\*\s*|\s*\d+\.\s*', factor_text)
        
        for item in factor_items:
            item = item.strip()
            if len(item) < 10:  # Skip very short items
                continue
                
            # Estimate impact and confidence from text
            impact_score = self._estimate_impact(item)
            confidence_score = self._estimate_factor_confidence(item)
            weight = self._estimate_weight(item)
            
            factors.append({
                'name': item[:50] + '...' if len(item) > 50 else item,
                'impact': impact_score,
                'confidence': confidence_score,
                'weight': weight,
                'explanation': item
            })
        
        return factors
    
    def _estimate_impact(self, text: str) -> float:
        """Estimate impact score from factor text."""
        text_lower = text.lower()
        
        # Strong impact words
        strong_positive = ['significant', 'major', 'strong', 'substantial', 'dramatic']
        strong_negative = ['weak', 'minor', 'slight', 'limited', 'small']
        
        impact = 0.5  # Default moderate impact
        
        for word in strong_positive:
            if word in text_lower:
                impact = 0.8
                break
        
        for word in strong_negative:
            if word in text_lower:
                impact = 0.2
                break
        
        return impact
    
    def _estimate_factor_confidence(self, text: str) -> float:
        """Estimate confidence score for individual factor."""
        confidence, _ = self.extract_confidence(text)
        return confidence
    
    def _estimate_weight(self, text: str) -> float:
        """Estimate factor importance weight."""
        text_lower = text.lower()
        
        # High importance words
        high_importance = ['key', 'critical', 'major', 'primary', 'main', 'important']
        low_importance = ['minor', 'secondary', 'less important', 'small']
        
        weight = 0.5  # Default moderate weight
        
        for word in high_importance:
            if word in text_lower:
                weight = 0.8
                break
        
        for word in low_importance:
            if word in text_lower:
                weight = 0.2
                break
        
        return weight
    
    def calculate_quantitative_scores(self, factors: Dict[str, List[MarketFactor]]) -> Dict[str, float]:
        """Calculate quantitative scores from factors."""
        # Calculate weighted scores
        bullish_score = 0.0
        bearish_score = 0.0
        
        total_weight = 0.0
        
        for factor in factors['bullish']:
            weighted_impact = factor.impact_score * factor.weight * factor.confidence
            bullish_score += weighted_impact
            total_weight += factor.weight
        
        for factor in factors['bearish']:
            weighted_impact = factor.impact_score * factor.weight * factor.confidence
            bearish_score += weighted_impact
            total_weight += factor.weight
        
        # Normalize scores
        if total_weight > 0:
            bullish_score = bullish_score / total_weight
            bearish_score = bearish_score / total_weight
        
        # Calculate net sentiment
        net_sentiment = bullish_score - bearish_score
        
        return {
            'bullish_score': min(1.0, max(0.0, bullish_score)),
            'bearish_score': min(1.0, max(0.0, bearish_score)),
            'net_sentiment': max(-1.0, min(1.0, net_sentiment))
        }
    
    def assess_risk_level(self, confidence: float, signal_strength: float, factors: Dict) -> tuple[str, float]:
        """Assess risk level and volatility expectation."""
        # Risk assessment based on confidence and signal clarity
        factor_count = len(factors['bullish']) + len(factors['bearish'])
        factor_agreement = abs(len(factors['bullish']) - len(factors['bearish'])) / max(factor_count, 1)
        
        risk_score = 1.0 - (confidence * factor_agreement)
        
        if risk_score < 0.3:
            risk_level = "LOW"
            volatility_expectation = 0.2
        elif risk_score < 0.6:
            risk_level = "MEDIUM" 
            volatility_expectation = 0.5
        else:
            risk_level = "HIGH"
            volatility_expectation = 0.8
        
        # Adjust volatility based on signal strength
        volatility_expectation *= (1.0 + signal_strength)
        volatility_expectation = min(1.0, volatility_expectation)
        
        return risk_level, volatility_expectation
    
    def convert_to_structured_output(
        self, 
        raw_ai_output: str, 
        symbol: str = "UNKNOWN",
        model_version: str = "1.0"
    ) -> StructuredMarketAnalysis:
        """
        Convert raw AI prose to structured JSON output.
        
        Args:
            raw_ai_output: Raw AI text analysis
            symbol: Trading symbol being analyzed
            model_version: AI model version
            
        Returns:
            StructuredMarketAnalysis object
        """
        self.logger.info(f"Converting AI output to structured format for {symbol}")
        
        try:
            # Extract core components
            confidence, confidence_level = self.extract_confidence(raw_ai_output)
            directional_bias, market_direction = self.extract_direction(raw_ai_output)
            factors = self.extract_factors(raw_ai_output)
            
            # Calculate quantitative scores
            quant_scores = self.calculate_quantitative_scores(factors)
            
            # Calculate signal strength (based on factor agreement and confidence)
            factor_count = len(factors['bullish']) + len(factors['bearish'])
            signal_strength = confidence * min(1.0, factor_count / 5.0)  # Normalize to 5 factors
            
            # Risk assessment
            risk_level, volatility_expectation = self.assess_risk_level(
                confidence, signal_strength, factors
            )
            
            # Create structured analysis
            structured_analysis = StructuredMarketAnalysis(
                directional_bias=directional_bias,
                signal_strength=signal_strength,
                confidence=confidence,
                market_direction=market_direction,
                confidence_level=confidence_level,
                bullish_factors=factors['bullish'],
                bearish_factors=factors['bearish'],
                neutral_factors=factors['neutral'],
                bullish_score=quant_scores['bullish_score'],
                bearish_score=quant_scores['bearish_score'],
                net_sentiment=quant_scores['net_sentiment'],
                risk_level=risk_level,
                volatility_expectation=volatility_expectation,
                analysis_timestamp=datetime.now().isoformat(),
                model_version=model_version,
                symbol=symbol,
                raw_analysis=raw_ai_output
            )
            
            self.logger.info(f"Structured analysis created: direction={directional_bias:.2f}, "
                           f"confidence={confidence:.2f}, signal_strength={signal_strength:.2f}")
            
            return structured_analysis
            
        except Exception as e:
            self.logger.error(f"Error converting AI output to structured format: {e}")
            
            # Return default neutral analysis on error
            return StructuredMarketAnalysis(
                directional_bias=0.0,
                signal_strength=0.0,
                confidence=0.1,
                market_direction=MarketDirection.NEUTRAL,
                confidence_level=ConfidenceLevel.VERY_LOW,
                bullish_factors=[],
                bearish_factors=[],
                neutral_factors=[],
                bullish_score=0.0,
                bearish_score=0.0,
                net_sentiment=0.0,
                risk_level="HIGH",
                volatility_expectation=0.9,
                analysis_timestamp=datetime.now().isoformat(),
                model_version=model_version,
                symbol=symbol,
                raw_analysis=raw_ai_output
            )
    
    def to_json(self, structured_analysis: StructuredMarketAnalysis) -> str:
        """Convert structured analysis to JSON string."""
        return json.dumps(asdict(structured_analysis), indent=2, default=str)
    
    def to_alpha_kernel_format(self, structured_analysis: StructuredMarketAnalysis) -> Dict:
        """
        Convert structured analysis to Alpha Kernel compatible format.
        
        Returns:
            Dictionary compatible with Alpha Kernel's _extract_quantitative_ai_signal method
        """
        return {
            "directional_bias": structured_analysis.directional_bias,
            "signal_strength": structured_analysis.signal_strength,
            "confidence": structured_analysis.confidence,
            "bullish_factors": [
                {
                    "weight": factor.weight,
                    "impact": factor.impact_score
                }
                for factor in structured_analysis.bullish_factors
            ],
            "bearish_factors": [
                {
                    "weight": factor.weight,
                    "impact": factor.impact_score
                }
                for factor in structured_analysis.bearish_factors
            ],
            "net_sentiment": structured_analysis.net_sentiment,
            "risk_level": structured_analysis.risk_level,
            "recommendation": structured_analysis.market_direction.value
        }


# Factory function
def create_structured_ai_engine() -> StructuredAIOutputEngine:
    """Create and return configured StructuredAIOutputEngine."""
    return StructuredAIOutputEngine()


# Example usage and testing
if __name__ == "__main__":
    # Create engine
    engine = create_structured_ai_engine()
    
    # Example raw AI output
    example_raw_output = """
    Based on the current market analysis, I have a high confidence bullish outlook for BTC-USD.

    Bullish factors:
    - Strong institutional adoption continuing
    - Technical breakout above key resistance levels
    - Positive regulatory developments in major markets
    - Increasing on-chain activity and whale accumulation

    Bearish factors:
    - Some profit-taking pressure at current levels
    - Macroeconomic uncertainties remain

    Overall, the bullish factors significantly outweigh the bearish ones. 
    I expect continued upward momentum with moderate volatility.
    """
    
    # Convert to structured format
    structured_output = engine.convert_to_structured_output(
        example_raw_output, 
        symbol="BTC-USD", 
        model_version="1.0"
    )
    
    # Print results
    print("Structured AI Output:")
    print(f"Direction: {structured_output.directional_bias:.2f}")
    print(f"Confidence: {structured_output.confidence:.2f}")
    print(f"Signal Strength: {structured_output.signal_strength:.2f}")
    print(f"Bullish Score: {structured_output.bullish_score:.2f}")
    print(f"Bearish Score: {structured_output.bearish_score:.2f}")
    print(f"Risk Level: {structured_output.risk_level}")
    
    # Alpha Kernel format
    alpha_format = engine.to_alpha_kernel_format(structured_output)
    print(f"\nAlpha Kernel Format: {alpha_format}")
    
    # JSON output
    json_output = engine.to_json(structured_output)
    print(f"\nJSON Output:\n{json_output}")