#!/usr/bin/env python3
"""
Point-in-Time (PIT) Fundamental Data Loader for Nasdaq Data Link (Sharadar)

This module provides functionality to fetch historical, as-reported fundamental 
data for companies using the Sharadar SF1 database via Nasdaq Data Link API.

This solves the critical lookahead bias problem identified in Sprint 9 by providing
true point-in-time fundamental data as it was known on specific historical dates.

Usage:
    loader = PITDataLoader(api_key="YOUR_API_KEY")
    fundamentals = loader.get_fundamentals('CRWD', '2021-01-01')
    print(fundamentals)

Requirements:
    pip install nasdaqdatalink pandas
"""

import nasdaqdatalink
import pandas as pd
from datetime import datetime, timedelta
import warnings

class PITDataLoader:
    """
    Point-in-Time fundamental data loader using Nasdaq Data Link (Sharadar).
    
    This class provides methods to fetch historical fundamental data as it was
    reported and known on specific dates, eliminating lookahead bias.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the PIT data loader.
        
        Args:
            api_key (str): Nasdaq Data Link API key. If None, expects environment variable.
        """
        if api_key:
            nasdaqdatalink.ApiConfig.api_key = api_key
        
        # Suppress pandas warnings for cleaner output
        warnings.filterwarnings('ignore', category=FutureWarning)
        
        # Common Sharadar fundamental metrics mapping
        self.fundamental_metrics = {
            # Income Statement
            'revenue': 'REVENUE',
            'gross_profit': 'GP', 
            'operating_income': 'OPINC',
            'net_income': 'NETINC',
            'eps': 'EPS',
            'ebit': 'EBIT',
            'ebitda': 'EBITDA',
            
            # Balance Sheet  
            'total_assets': 'ASSETS',
            'total_liabilities': 'LIABILITIES',
            'stockholders_equity': 'EQUITY',
            'cash': 'CASH',
            'debt': 'DEBT',
            'shares_outstanding': 'SHARESWA',
            
            # Valuation Metrics
            'market_cap': 'MARKETCAP',
            'enterprise_value': 'EV',
            'pe_ratio': 'PE',
            'pb_ratio': 'PB',
            'ev_ebitda': 'EVEBITDA'
        }
    
    def get_fundamentals(self, ticker, as_of_date, dimension='MRQ'):
        """
        Fetch point-in-time fundamental data for a given ticker and date.
        
        Args:
            ticker (str): Stock ticker symbol (e.g., 'CRWD')
            as_of_date (str): Date in 'YYYY-MM-DD' format (e.g., '2021-01-01')
            dimension (str): Time dimension - 'MRQ' (Most Recent Quarter) or 'MRY' (Most Recent Year)
            
        Returns:
            dict: Dictionary containing fundamental metrics as they were known on as_of_date
        """
        try:
            # Convert string date to datetime for comparison
            target_date = datetime.strptime(as_of_date, '%Y-%m-%d')
            
            print(f"Fetching PIT fundamentals for {ticker} as of {as_of_date}...")
            
            # Fetch Sharadar SF1 data for the ticker
            # The 'datekey' parameter ensures we get data as reported up to that date
            sf1_data = nasdaqdatalink.get(
                f'SHARADAR/SF1',
                ticker=ticker,
                dimension=dimension,
                paginate=True
            )
            
            if sf1_data is None or sf1_data.empty:
                print(f"Warning: No fundamental data found for {ticker}")
                return {}
            
            # Filter data to only include records available as of the target date
            # The 'datekey' in Sharadar represents when the data was reported/available
            pit_data = sf1_data[sf1_data['datekey'] <= as_of_date]
            
            if pit_data.empty:
                print(f"Warning: No fundamental data available for {ticker} as of {as_of_date}")
                return {}
            
            # Get the most recent record as of the target date
            latest_record = pit_data.loc[pit_data['datekey'].idxmax()]
            
            # Extract key fundamental metrics
            fundamentals = {}
            
            for metric_name, sharadar_code in self.fundamental_metrics.items():
                if sharadar_code in latest_record.index:
                    value = latest_record[sharadar_code]
                    if pd.notna(value):  # Only include non-null values
                        fundamentals[metric_name] = float(value)
            
            # Add metadata
            fundamentals['_metadata'] = {
                'ticker': ticker,
                'as_of_date': as_of_date,
                'report_date': str(latest_record['datekey']),
                'dimension': dimension,
                'data_source': 'Sharadar SF1'
            }
            
            print(f"✅ Successfully fetched {len(fundamentals)-1} fundamental metrics")
            return fundamentals
            
        except Exception as e:
            print(f"ERROR: Error fetching fundamentals for {ticker}: {str(e)}")
            return {}
    
    def get_quality_metrics(self, ticker, as_of_date):
        """
        Get quality-focused metrics for QVM analysis.
        
        Args:
            ticker (str): Stock ticker symbol
            as_of_date (str): Date in 'YYYY-MM-DD' format
            
        Returns:
            dict: Quality metrics including ROE, ROA, profit margins
        """
        fundamentals = self.get_fundamentals(ticker, as_of_date)
        
        if not fundamentals:
            return {}
        
        quality_metrics = {}
        
        # Calculate Return on Equity (ROE)
        if 'net_income' in fundamentals and 'stockholders_equity' in fundamentals:
            if fundamentals['stockholders_equity'] != 0:
                quality_metrics['roe'] = fundamentals['net_income'] / fundamentals['stockholders_equity']
        
        # Calculate Return on Assets (ROA)  
        if 'net_income' in fundamentals and 'total_assets' in fundamentals:
            if fundamentals['total_assets'] != 0:
                quality_metrics['roa'] = fundamentals['net_income'] / fundamentals['total_assets']
        
        # Calculate Profit Margin
        if 'net_income' in fundamentals and 'revenue' in fundamentals:
            if fundamentals['revenue'] != 0:
                quality_metrics['profit_margin'] = fundamentals['net_income'] / fundamentals['revenue']
        
        return quality_metrics
    
    def get_value_metrics(self, ticker, as_of_date):
        """
        Get value-focused metrics for QVM analysis.
        
        Args:
            ticker (str): Stock ticker symbol  
            as_of_date (str): Date in 'YYYY-MM-DD' format
            
        Returns:
            dict: Value metrics including P/E, P/B, EV/EBITDA
        """
        fundamentals = self.get_fundamentals(ticker, as_of_date)
        
        if not fundamentals:
            return {}
        
        value_metrics = {}
        
        # Extract direct value metrics from Sharadar
        for metric in ['pe_ratio', 'pb_ratio', 'ev_ebitda']:
            if metric in fundamentals:
                value_metrics[metric] = fundamentals[metric]
        
        # Calculate Earnings Yield (inverse of P/E)
        if 'pe_ratio' in fundamentals and fundamentals['pe_ratio'] != 0:
            value_metrics['earnings_yield'] = 1 / fundamentals['pe_ratio']
        
        # Calculate EV/Revenue if available
        if 'enterprise_value' in fundamentals and 'revenue' in fundamentals:
            if fundamentals['revenue'] != 0:
                value_metrics['ev_revenue'] = fundamentals['enterprise_value'] / fundamentals['revenue']
        
        return value_metrics

def test_pit_data_loader():
    """
    Test function to validate PIT data loading meets Sprint 10 success criteria.
    
    Success Criteria: Fetch and display quarterly financial statements for CRWD
    as they were known on January 1st, 2021.
    """
    print("="*80)
    print("SPRINT 10 SUCCESS CRITERIA TEST")
    print("="*80)
    print("Objective: Fetch CRWD fundamentals as known on 2021-01-01")
    print("Expected: Display quarterly financial statements (Revenue, Net Income, etc.)")
    print()
    
    # NOTE: This requires a valid Nasdaq Data Link API key
    # For demonstration, we'll show the expected structure
    
    loader = PITDataLoader()  # API key should be set via environment variable
    
    try:
        # Test the core functionality
        fundamentals = loader.get_fundamentals('CRWD', '2021-01-01')
        
        if fundamentals:
            print("SUCCESS: Point-in-Time data retrieved successfully!")
            print()
            print("Financial Statements for CRWD as known on 2021-01-01:")
            print("-" * 60)
            
            # Display key financial metrics
            for metric, value in fundamentals.items():
                if metric != '_metadata':
                    if isinstance(value, float):
                        if abs(value) > 1000000:  # Display in millions
                            print(f"{metric.replace('_', ' ').title()}: ${value/1000000:.1f}M")
                        else:
                            print(f"{metric.replace('_', ' ').title()}: ${value:,.2f}")
            
            print("\nMetadata:")
            print(f"Report Date: {fundamentals['_metadata']['report_date']}")
            print(f"Data Source: {fundamentals['_metadata']['data_source']}")
            
        else:
            print("FAILED: Could not retrieve point-in-time data")
            print("This may be due to:")
            print("1. Missing Nasdaq Data Link API key")
            print("2. No subscription to Sharadar database")
            print("3. Network connectivity issues")
            
    except Exception as e:
        print(f"TEST FAILED: {str(e)}")
        print("\nTo complete this test, you need:")
        print("1. Valid Nasdaq Data Link API key")
        print("2. Subscription to Core plan ($50/month)")
        print("3. Install nasdaqdatalink: pip install nasdaqdatalink")

if __name__ == "__main__":
    test_pit_data_loader()