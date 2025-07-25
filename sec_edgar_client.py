# SEC EDGAR API Client - Real Filing Integration
# Replaces simulation with actual SEC 8-K material event filings

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

class SECEdgarClient:
    """
    SEC EDGAR API client for fetching real 8-K filings
    
    The SEC requires a User-Agent header identifying your company/email
    Rate limit: 10 requests per second maximum
    """
    
    def __init__(self):
        # SEC requires User-Agent header
        self.user_agent = os.getenv('EDGAR_USER_AGENT', 'Operation Badger Trading System contact@example.com')
        
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
        
        self.base_url = "https://data.sec.gov/api/xbrl"
        self.submissions_url = "https://data.sec.gov/submissions"
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 10 requests per second max
        
        print(f"SEC EDGAR Client initialized")
        print(f"User-Agent: {self.user_agent}")
        
    def _rate_limit(self):
        """Enforce SEC rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def get_company_cik(self, symbol: str) -> Optional[str]:
        """
        Get Company Central Index Key (CIK) from stock symbol
        Required for SEC API calls
        """
        try:
            self._rate_limit()
            
            # SEC company tickers JSON endpoint
            url = "https://data.sec.gov/api/xbrl/companytickers.json"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            companies = response.json()
            
            # Search for symbol
            for key, company in companies.items():
                if company.get('ticker', '').upper() == symbol.upper():
                    cik = str(company['cik_str']).zfill(10)  # Pad to 10 digits
                    print(f"Found CIK for {symbol}: {cik}")
                    return cik
                    
            print(f"CIK not found for symbol: {symbol}")
            return None
            
        except Exception as e:
            print(f"Error getting CIK for {symbol}: {e}")
            return None
    
    def get_recent_filings(self, symbol: str, form_type: str = "8-K", 
                          days_back: int = 90) -> List[Dict]:
        """
        Get recent SEC filings for a company
        
        Args:
            symbol: Stock ticker symbol
            form_type: SEC form type (default 8-K for material events)
            days_back: How many days back to search
            
        Returns:
            List of filing metadata dictionaries
        """
        try:
            # Get CIK first
            cik = self.get_company_cik(symbol)
            if not cik:
                return []
            
            self._rate_limit()
            
            # Get company submissions
            url = f"{self.submissions_url}/CIK{cik}.json"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract recent filings
            filings = data.get('filings', {}).get('recent', {})
            
            if not filings:
                return []
            
            # Filter for specific form type and date range
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            recent_filings = []
            
            for i in range(len(filings.get('form', []))):
                form = filings['form'][i]
                filing_date = filings['filingDate'][i]
                accession_number = filings['accessionNumber'][i]
                
                if form == form_type:
                    try:
                        file_date = datetime.strptime(filing_date, '%Y-%m-%d')
                        
                        if file_date >= cutoff_date:
                            filing_info = {
                                'symbol': symbol,
                                'cik': cik,
                                'form': form,
                                'filing_date': filing_date,
                                'accession_number': accession_number,
                                'primary_document': filings['primaryDocument'][i],
                                'primary_doc_description': filings['primaryDocDescription'][i]
                            }
                            
                            recent_filings.append(filing_info)
                            
                    except (ValueError, IndexError) as e:
                        continue
            
            print(f"Found {len(recent_filings)} recent {form_type} filings for {symbol}")
            return recent_filings
            
        except Exception as e:
            print(f"Error getting recent filings for {symbol}: {e}")
            return []
    
    def get_filing_content(self, filing_info: Dict) -> Optional[str]:
        """
        Download and extract text content from SEC filing
        
        Args:
            filing_info: Filing metadata dictionary from get_recent_filings
            
        Returns:
            Raw text content of the filing
        """
        try:
            cik = filing_info['cik']
            accession = filing_info['accession_number'].replace('-', '')
            primary_doc = filing_info['primary_document']
            
            # Construct EDGAR document URL
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"
            
            self._rate_limit()
            
            response = requests.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            
            content = response.text
            
            # Extract text from HTML/XML content
            text_content = self._extract_text_from_filing(content)
            
            print(f"Downloaded filing content: {len(text_content)} characters")
            return text_content
            
        except Exception as e:
            print(f"Error downloading filing content: {e}")
            return None
    
    def _extract_text_from_filing(self, html_content: str) -> str:
        """
        Extract readable text from SEC filing HTML/XML
        
        This is a simplified version - production would use more sophisticated parsing
        """
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html_content)
            
            # Clean up whitespace
            text = re.sub(r'\\s+', ' ', text)
            text = text.strip()
            
            # Focus on key sections for 8-K filings
            # Look for Item disclosures (Item 1.01, 2.02, etc.)
            item_pattern = r'(Item\\s+\\d+\\.\\d+[^\\n]*[\\s\\S]*?)(?=Item\\s+\\d+\\.\\d+|$)'
            items = re.findall(item_pattern, text, re.IGNORECASE)
            
            if items:
                # Return the most substantial item disclosure
                longest_item = max(items, key=len)
                return longest_item[:5000]  # Limit to 5000 chars for LLM processing
            else:
                # Fallback: return first 5000 characters
                return text[:5000]
                
        except Exception as e:
            print(f"Error extracting text: {e}")
            return html_content[:5000]  # Fallback to raw content
    
    def get_filings_for_symbols(self, symbols: List[str], 
                               days_back: int = 30) -> pd.DataFrame:
        """
        Get recent 8-K filings for multiple symbols
        
        Returns DataFrame with filing information ready for analysis
        """
        all_filings = []
        
        print(f"\\nFetching SEC filings for {len(symbols)} symbols...")
        
        for symbol in symbols:
            print(f"Processing {symbol}...")
            
            try:
                filings = self.get_recent_filings(symbol, "8-K", days_back)
                
                for filing in filings:
                    # Get filing content
                    content = self.get_filing_content(filing)
                    
                    if content and len(content.strip()) > 100:  # Minimum content threshold
                        filing_record = {
                            'symbol': symbol,
                            'filing_date': filing['filing_date'],
                            'accession_number': filing['accession_number'],
                            'form_type': filing['form'],
                            'content': content,
                            'content_length': len(content),
                            'retrieved_at': datetime.now().isoformat()
                        }
                        
                        all_filings.append(filing_record)
                
                # Small delay between symbols to be respectful
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue
        
        df = pd.DataFrame(all_filings)
        
        if len(df) > 0:
            df['filing_date'] = pd.to_datetime(df['filing_date'])
            df = df.sort_values('filing_date', ascending=False)
            
        print(f"\\nCollected {len(df)} SEC filings total")
        return df


def test_sec_integration():
    """Test the SEC EDGAR integration with a few symbols"""
    
    print("="*60)
    print("SEC EDGAR API INTEGRATION TEST")
    print("="*60)
    
    # Test with a few symbols from our validated universe
    test_symbols = ['CRWD', 'SNOW', 'PLTR']
    
    client = SECEdgarClient()
    
    # Test individual functions
    print("\\n1. Testing CIK lookup...")
    for symbol in test_symbols:
        cik = client.get_company_cik(symbol)
        print(f"{symbol}: {cik}")
    
    print("\\n2. Testing recent filings...")
    filings_df = client.get_filings_for_symbols(test_symbols, days_back=60)
    
    if len(filings_df) > 0:
        print(f"\\nSuccess! Found {len(filings_df)} recent filings:")
        print(filings_df[['symbol', 'filing_date', 'form_type', 'content_length']].head())
        
        # Save test results
        filings_df.to_csv('test_sec_filings.csv', index=False)
        print("\\nTest results saved to test_sec_filings.csv")
        
        return True
    else:
        print("\\nNo filings found in test period")
        return False


if __name__ == "__main__":
    test_sec_integration()