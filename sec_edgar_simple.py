# Simplified SEC EDGAR Integration
# Using alternative approach with manual CIK mapping

import requests
import pandas as pd
import json
import time
from datetime import datetime, timedelta
import re
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class SimpleSECClient:
    """
    Simplified SEC EDGAR client with manual CIK mapping
    Focus on getting real 8-K filings for our validated universe
    """
    
    def __init__(self):
        self.user_agent = os.getenv('EDGAR_USER_AGENT', 'Operation Badger Trading System contact@example.com')
        
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept-Encoding': 'gzip, deflate',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        
        # Manual CIK mapping for our validated universe
        # These are the actual SEC CIKs for our small/mid-cap stocks
        self.symbol_to_cik = {
            'CRWD': '0001535527',  # CrowdStrike
            'SNOW': '0001640147',  # Snowflake
            'DDOG': '0001561550',  # Datadog
            'NET': '0001477333',   # Cloudflare
            'OKTA': '0001660134',  # Okta
            'PLTR': '0001321655',  # Palantir
            'RBLX': '0001315098',  # Roblox
            'COIN': '0001679788',  # Coinbase
            'ROKU': '0001428439',  # Roku
            'ZM': '0001585521',    # Zoom
            'PYPL': '0001633917',  # PayPal
            'SPOT': '0001639920',  # Spotify
            'DOCU': '0001261333'   # DocuSign
        }
        
        self.submissions_url = "https://data.sec.gov/submissions"
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.11  # Stay under 10 requests per second
        
        print(f"SEC EDGAR Simple Client initialized")
        print(f"Tracking {len(self.symbol_to_cik)} symbols with known CIKs")
        
    def _rate_limit(self):
        """Enforce SEC rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def get_recent_8k_filings(self, symbol: str, days_back: int = 60) -> List[Dict]:
        """
        Get recent 8-K filings for a symbol using known CIK
        
        Args:
            symbol: Stock ticker symbol
            days_back: How many days back to search
            
        Returns:
            List of 8-K filing dictionaries
        """
        if symbol not in self.symbol_to_cik:
            print(f"CIK not available for {symbol}")
            return []
            
        cik = self.symbol_to_cik[symbol]
        
        try:
            self._rate_limit()
            
            # Get company submissions using CIK
            url = f"{self.submissions_url}/CIK{cik}.json"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            filings = data.get('filings', {}).get('recent', {})
            
            if not filings:
                return []
            
            # Filter for 8-K filings in date range
            cutoff_date = datetime.now() - timedelta(days=days_back)
            recent_8k_filings = []
            
            forms = filings.get('form', [])
            filing_dates = filings.get('filingDate', [])
            accession_numbers = filings.get('accessionNumber', [])
            primary_documents = filings.get('primaryDocument', [])
            
            for i in range(len(forms)):
                if forms[i] == '8-K':
                    try:
                        filing_date = datetime.strptime(filing_dates[i], '%Y-%m-%d')
                        
                        if filing_date >= cutoff_date:
                            filing_info = {
                                'symbol': symbol,
                                'cik': cik,
                                'filing_date': filing_dates[i],
                                'accession_number': accession_numbers[i],
                                'primary_document': primary_documents[i],
                                'filing_url': f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession_numbers[i].replace('-', '')}/{primary_documents[i]}"
                            }
                            
                            recent_8k_filings.append(filing_info)
                            
                    except (ValueError, IndexError):
                        continue
            
            print(f"Found {len(recent_8k_filings)} recent 8-K filings for {symbol}")
            return recent_8k_filings
            
        except Exception as e:
            print(f"Error getting 8-K filings for {symbol}: {e}")
            return []
    
    def download_filing_text(self, filing_info: Dict) -> Optional[str]:
        """
        Download and extract text from 8-K filing
        
        Returns simplified text content for LLM analysis
        """
        try:
            self._rate_limit()
            
            response = requests.get(filing_info['filing_url'], headers=self.headers, timeout=20)
            response.raise_for_status()
            
            content = response.text
            
            # Extract meaningful text from HTML
            text = self._extract_8k_text(content)
            
            print(f"Downloaded 8-K content: {len(text)} characters")
            return text
            
        except Exception as e:
            print(f"Error downloading filing: {e}")
            return None
    
    def _extract_8k_text(self, html_content: str) -> str:
        """
        Extract key information from 8-K HTML content
        Focus on Item disclosures which contain material events
        """
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html_content)
            
            # Clean whitespace
            text = re.sub(r'\\s+', ' ', text.strip())
            
            # Look for 8-K Item sections (Item 1.01, 2.02, etc.)
            # These contain the actual material event disclosures
            item_patterns = [
                r'Item\\s+[0-9]+\\.[0-9]+[^\\n]*[\\s\\S]*?(?=Item\\s+[0-9]+\\.[0-9]+|SIGNATURES|$)',
                r'ITEM\\s+[0-9]+\\.[0-9]+[^\\n]*[\\s\\S]*?(?=ITEM\\s+[0-9]+\\.[0-9]+|SIGNATURES|$)'
            ]
            
            items = []
            for pattern in item_patterns:
                items.extend(re.findall(pattern, text, re.IGNORECASE))
            
            if items:
                # Combine all item disclosures
                combined_text = ' '.join(items)
                
                # Focus on most relevant sections for trading decisions
                # Look for key terms that indicate material events
                relevant_keywords = [
                    'earnings', 'revenue', 'acquisition', 'merger', 'partnership',
                    'agreement', 'contract', 'settlement', 'lawsuit', 'regulatory',
                    'management', 'resignation', 'appointment', 'restructuring',
                    'guidance', 'outlook', 'material', 'significant'
                ]
                
                # Score sections by relevance
                sentences = combined_text.split('. ')
                relevant_sentences = []
                
                for sentence in sentences:
                    score = sum(1 for keyword in relevant_keywords 
                              if keyword.lower() in sentence.lower())
                    if score > 0:
                        relevant_sentences.append((score, sentence))
                
                if relevant_sentences:
                    # Sort by relevance and take top content
                    relevant_sentences.sort(reverse=True, key=lambda x: x[0])
                    top_content = '. '.join([sent[1] for sent in relevant_sentences[:10]])
                    return top_content[:3000]  # Limit for LLM processing
                else:
                    return combined_text[:3000]
            else:
                # Fallback to first part of document
                return text[:3000]
                
        except Exception as e:
            print(f"Error extracting text: {e}")
            return html_content[:3000]
    
    def collect_recent_filings(self, symbols: List[str], days_back: int = 30) -> pd.DataFrame:
        """
        Collect recent 8-K filings for multiple symbols
        Returns DataFrame ready for AI analysis
        """
        all_filings = []
        
        print(f"\\nCollecting 8-K filings for {len(symbols)} symbols...")
        
        for symbol in symbols:
            print(f"\\nProcessing {symbol}...")
            
            filings = self.get_recent_8k_filings(symbol, days_back)
            
            for filing in filings:
                # Download filing content
                content = self.download_filing_text(filing)
                
                if content and len(content.strip()) > 200:  # Minimum useful content
                    filing_record = {
                        'symbol': symbol,
                        'filing_date': filing['filing_date'],
                        'accession_number': filing['accession_number'],
                        'cik': filing['cik'],
                        'filing_text': content,
                        'text_length': len(content),
                        'filing_url': filing['filing_url'],
                        'retrieved_at': datetime.now().isoformat()
                    }
                    
                    all_filings.append(filing_record)
                    print(f"  Added filing: {filing['filing_date']} ({len(content)} chars)")
                
                # Small delay between downloads
                time.sleep(0.3)
        
        df = pd.DataFrame(all_filings)
        
        if len(df) > 0:
            df['filing_date'] = pd.to_datetime(df['filing_date'])
            df = df.sort_values('filing_date', ascending=False)
            
        print(f"\\n*** COLLECTION COMPLETE ***")
        print(f"Total 8-K filings collected: {len(df)}")
        
        return df


def test_simple_sec_integration():
    """Test the simplified SEC integration"""
    
    print("="*60)
    print("SEC EDGAR SIMPLE INTEGRATION TEST")
    print("="*60)
    
    # Test with validated universe subset
    test_symbols = ['CRWD', 'SNOW', 'PLTR']
    
    client = SimpleSECClient()
    
    print("\\nTesting with manual CIK mapping...")
    
    # Test recent filings collection
    filings_df = client.collect_recent_filings(test_symbols, days_back=45)
    
    if len(filings_df) > 0:
        print(f"\\n*** SUCCESS! ***")
        print(f"Collected {len(filings_df)} recent 8-K filings")
        
        print("\\nFiling summary:")
        print(filings_df[['symbol', 'filing_date', 'text_length']].head(10))
        
        # Save results
        filings_df.to_csv('sec_8k_filings.csv', index=False)
        print("\\nResults saved to sec_8k_filings.csv")
        
        # Show sample content
        if len(filings_df) > 0:
            print("\\nSample filing content (first 500 chars):")
            print("-" * 50)
            print(filings_df.iloc[0]['filing_text'][:500] + "...")
            print("-" * 50)
        
        return True
    else:
        print("\\nNo 8-K filings found in test period")
        return False


if __name__ == "__main__":
    test_simple_sec_integration()