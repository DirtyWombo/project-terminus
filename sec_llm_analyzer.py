# SEC Filing LLM Analyzer
# Integrates real SEC 8-K filings with Llama 3.2 AI analysis
# Replaces simulation with production-ready alpha signal generation

import requests
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv
from sec_edgar_simple import SimpleSECClient
import time
import re

load_dotenv()

class SECLLMAnalyzer:
    """
    Production SEC filing analyzer using Llama 3.2
    Generates real velocity scores and confidence ratings
    """
    
    def __init__(self):
        self.llama_url = os.getenv('LLAMA_API_URL', 'http://localhost:11434')
        self.model = os.getenv('LLAMA_MODEL', 'llama3.2:latest')
        
        # SEC client for filing collection
        self.sec_client = SimpleSECClient()
        
        # Validated confidence threshold from alpha testing
        self.min_confidence_threshold = 0.75  # From successful validation
        
        print(f"SEC LLM Analyzer initialized")
        print(f"Llama URL: {self.llama_url}")
        print(f"Model: {self.model}")
        print(f"Minimum confidence threshold: {self.min_confidence_threshold}")
    
    def test_llama_connection(self) -> bool:
        """Test connection to local Llama service"""
        try:
            response = requests.get(f"{self.llama_url}/api/version", timeout=5)
            if response.status_code == 200:
                print("SUCCESS: Llama service connected")
                return True
            else:
                print("ERROR: Llama service not responding")
                return False
        except Exception as e:
            print(f"ERROR: Cannot connect to Llama service: {e}")
            return False
    
    def analyze_8k_filing(self, filing_text: str, symbol: str) -> Optional[Dict]:
        """
        Analyze 8-K filing using Llama 3.2 to generate velocity score
        
        Args:
            filing_text: Raw 8-K filing text
            symbol: Stock symbol
            
        Returns:
            Analysis dictionary with velocity_score and confidence
        """
        
        prompt = f"""Analyze this SEC 8-K filing for {symbol} and assess its impact on stock price.

FILING TEXT:
{filing_text[:2000]}

ANALYSIS REQUIREMENTS:
1. VELOCITY SCORE (-1.0 to +1.0): How will this news affect stock price?
   - Positive events (earnings beat, partnerships, acquisitions): +0.3 to +1.0
   - Neutral events (routine disclosures, minor changes): -0.2 to +0.2  
   - Negative events (lawsuits, resignations, guidance cuts): -1.0 to -0.3

2. CONFIDENCE (0.1 to 1.0): How certain are you about the impact?
   - High materiality, clear impact: 0.8-1.0
   - Moderate materiality: 0.5-0.8
   - Low materiality or unclear: 0.1-0.5

3. REASONING: Brief explanation of your assessment

Respond in this exact JSON format:
{{"velocity_score": 0.0, "confidence": 0.0, "reasoning": "explanation"}}"""

        try:
            # Call Llama API
            response = requests.post(
                f"{self.llama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for consistent analysis
                        "top_p": 0.8
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_output = result.get('response', '').strip()
                
                # Parse JSON response
                analysis = self._parse_llm_response(llm_output)
                
                if analysis:
                    analysis['symbol'] = symbol
                    analysis['analysis_timestamp'] = datetime.now().isoformat()
                    
                    print(f"  LLM Analysis: velocity={analysis['velocity_score']:.3f}, confidence={analysis['confidence']:.3f}")
                    return analysis
                else:
                    print("  ❌ Failed to parse LLM response")
                    return None
            else:
                print(f"  ❌ LLM API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"  ❌ LLM analysis error: {e}")
            return None
    
    def _parse_llm_response(self, llm_output: str) -> Optional[Dict]:
        """Parse structured JSON response from LLM"""
        try:
            # Try to find JSON in the response
            json_pattern = r'\\{[^}]*"velocity_score"[^}]*\\}'
            json_matches = re.findall(json_pattern, llm_output)
            
            if json_matches:
                json_str = json_matches[0]
                analysis = json.loads(json_str)
                
                # Validate required fields
                if ('velocity_score' in analysis and 
                    'confidence' in analysis and
                    isinstance(analysis['velocity_score'], (int, float)) and
                    isinstance(analysis['confidence'], (int, float))):
                    
                    # Clamp values to valid ranges
                    analysis['velocity_score'] = max(-1.0, min(1.0, float(analysis['velocity_score'])))
                    analysis['confidence'] = max(0.1, min(1.0, float(analysis['confidence'])))
                    
                    return analysis
            
            # Fallback: try to parse the entire response as JSON
            analysis = json.loads(llm_output.strip())
            if 'velocity_score' in analysis and 'confidence' in analysis:
                analysis['velocity_score'] = max(-1.0, min(1.0, float(analysis['velocity_score'])))
                analysis['confidence'] = max(0.1, min(1.0, float(analysis['confidence'])))
                return analysis
                
            return None
            
        except (json.JSONDecodeError, ValueError, KeyError):
            return None
    
    def generate_trading_signals(self, symbols: List[str], days_back: int = 30) -> pd.DataFrame:
        """
        Generate real trading signals from recent SEC filings
        
        This replaces the simulation with production alpha generation
        """
        print(f"\\nGENERATING REAL ALPHA SIGNALS")
        print(f"Symbols: {symbols}")
        print(f"Lookback: {days_back} days")
        print("="*50)
        
        # Test Llama connection first
        if not self.test_llama_connection():
            print("ERROR: Cannot proceed without Llama service")
            return pd.DataFrame()
        
        # Collect recent 8-K filings
        print("\\n1. Collecting SEC 8-K filings...")
        filings_df = self.sec_client.collect_recent_filings(symbols, days_back)
        
        if len(filings_df) == 0:
            print("ERROR: No recent SEC filings found")
            return pd.DataFrame()
        
        print(f"SUCCESS: Collected {len(filings_df)} SEC filings")
        
        # Analyze each filing with LLM
        print("\\n2. Analyzing filings with Llama 3.2...")
        
        signals = []
        
        for idx, filing in filings_df.iterrows():
            print(f"\\nAnalyzing {filing['symbol']} filing from {filing['filing_date']}...")
            
            # LLM analysis
            analysis = self.analyze_8k_filing(filing['filing_text'], filing['symbol'])
            
            if analysis:
                # Only keep high-confidence signals (from validated threshold)
                if analysis['confidence'] >= self.min_confidence_threshold:
                    signal = {
                        'symbol': filing['symbol'],
                        'filing_date': filing['filing_date'],
                        'accession_number': filing['accession_number'],
                        'velocity_score': analysis['velocity_score'],
                        'confidence': analysis['confidence'],
                        'reasoning': analysis.get('reasoning', ''),
                        'filing_text_length': filing['text_length'],
                        'analysis_timestamp': analysis['analysis_timestamp']
                    }
                    
                    signals.append(signal)
                    print(f"  HIGH-CONFIDENCE SIGNAL: {analysis['velocity_score']:.3f} ({analysis['confidence']:.3f})")
                else:
                    print(f"  Low confidence: {analysis['confidence']:.3f} < {self.min_confidence_threshold}")
            
            # Rate limiting for LLM
            time.sleep(1)
        
        # Create signals DataFrame
        signals_df = pd.DataFrame(signals)
        
        if len(signals_df) > 0:
            signals_df['filing_date'] = pd.to_datetime(signals_df['filing_date'])
            signals_df = signals_df.sort_values('filing_date', ascending=False)
            
            print(f"\\nSUCCESS: GENERATED {len(signals_df)} HIGH-CONFIDENCE TRADING SIGNALS")
            
            # Save signals
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"real_alpha_signals_{timestamp}.csv"
            signals_df.to_csv(filename, index=False)
            print(f"Signals saved to {filename}")
            
            # Summary statistics
            print(f"\\nSIGNAL SUMMARY:")
            print(f"Average velocity score: {signals_df['velocity_score'].mean():.3f}")
            print(f"Average confidence: {signals_df['confidence'].mean():.3f}")
            print(f"Positive signals: {(signals_df['velocity_score'] > 0).sum()}/{len(signals_df)}")
            
        else:
            print("\\nNo high-confidence signals generated")
        
        return signals_df
    
    def backtest_signals_preparation(self, signals_df: pd.DataFrame) -> Dict:
        """
        Prepare real signals for backtesting integration
        Returns metadata for backtesting framework
        """
        if len(signals_df) == 0:
            return {"status": "no_signals"}
        
        # Calculate signal statistics for backtesting
        stats = {
            "status": "ready",
            "total_signals": len(signals_df),
            "date_range": {
                "start": signals_df['filing_date'].min().isoformat(),
                "end": signals_df['filing_date'].max().isoformat()
            },
            "symbols": list(signals_df['symbol'].unique()),
            "signal_stats": {
                "mean_velocity": signals_df['velocity_score'].mean(),
                "mean_confidence": signals_df['confidence'].mean(),
                "positive_ratio": (signals_df['velocity_score'] > 0).mean()
            },
            "confidence_distribution": {
                "min": signals_df['confidence'].min(),
                "max": signals_df['confidence'].max(),
                "median": signals_df['confidence'].median()
            }
        }
        
        return stats


def test_production_alpha_generation():
    """Test production alpha signal generation"""
    
    print("="*60)
    print("PRODUCTION ALPHA SIGNAL GENERATION TEST")
    print("Expert-validated strategy with real SEC data + LLM analysis")
    print("="*60)
    
    # Test with subset of validated universe
    test_symbols = ['CRWD', 'SNOW', 'PLTR']
    
    analyzer = SECLLMAnalyzer()
    
    # Generate real trading signals
    signals_df = analyzer.generate_trading_signals(test_symbols, days_back=45)
    
    if len(signals_df) > 0:
        print(f"\\nSUCCESS! Generated {len(signals_df)} production trading signals")
        
        # Prepare for backtesting
        backtest_prep = analyzer.backtest_signals_preparation(signals_df)
        
        print(f"\\nBACKTESTING PREPARATION:")
        print(f"Status: {backtest_prep['status']}")
        print(f"Ready for robust backtesting framework integration")
        
        return True
    else:
        print("\\n⚠️ No production signals generated")
        print("Note: This may be normal if no recent high-impact 8-K filings exist")
        return False


if __name__ == "__main__":
    test_production_alpha_generation()