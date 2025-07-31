#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 16: Theta Data Options Pipeline
Professional-grade options data acquisition for volatility trading strategies

This module provides the core infrastructure for downloading and managing
historical SPY options chains from Theta Data for Iron Condor backtesting.

Key Features:
- Historical options chain retrieval
- Greeks and IV calculation integration
- Data validation and storage
- SPY-focused optimization for volatility strategies
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThetaDataClient:
    """
    Professional options data client for Theta Data API
    Optimized for SPY options chain acquisition and Iron Condor backtesting
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Theta Data client
        
        Args:
            api_key: Theta Data API key (optional for free tier)
        """
        self.api_key = api_key
        self.base_url = "https://api.thetadata.us/v2"
        self.session = requests.Session()
        
        # Set headers for API requests
        if self.api_key:
            self.session.headers.update({
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            })
        
        # Create data directory structure
        self.data_dir = "options_data/spy_chains"
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info("Theta Data client initialized")
        logger.info(f"Data directory: {self.data_dir}")
        
    def get_spy_options_chain(self, date: str, save_to_disk: bool = True) -> pd.DataFrame:
        """
        Retrieve complete SPY options chain for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format
            save_to_disk: Whether to save data locally
            
        Returns:
            DataFrame with complete options chain data
        """
        logger.info(f"Fetching SPY options chain for {date}")
        
        try:
            # Convert date to required format
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            
            # Build API endpoint for SPY options chain
            endpoint = f"{self.base_url}/snapshot/option/chain"
            params = {
                'root': 'SPY',
                'date': date,
                'format': 'json'
            }
            
            # Make API request
            response = self.session.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Process and structure the options data
                options_df = self._process_options_chain(data, date)
                
                if save_to_disk and not options_df.empty:
                    self._save_options_chain(options_df, date)
                
                logger.info(f"Successfully retrieved {len(options_df)} option contracts for {date}")
                return options_df
                
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error fetching options chain for {date}: {str(e)}")
            return pd.DataFrame()
    
    def _process_options_chain(self, raw_data: Dict, date: str) -> pd.DataFrame:
        """
        Process raw API response into structured DataFrame
        
        Args:
            raw_data: Raw API response data
            date: Date string for the data
            
        Returns:
            Processed DataFrame with standardized columns
        """
        try:
            if 'response' not in raw_data:
                logger.warning("No response data found in API response")
                return pd.DataFrame()
            
            contracts = []
            
            for contract_data in raw_data['response']:
                # Extract key contract information
                contract = {
                    'date': date,
                    'underlying': 'SPY',
                    'strike': contract_data.get('strike', 0),
                    'expiration': contract_data.get('exp', ''),
                    'option_type': contract_data.get('right', ''),  # 'C' or 'P'
                    'bid': contract_data.get('bid', 0),
                    'ask': contract_data.get('ask', 0),
                    'last': contract_data.get('last', 0),
                    'volume': contract_data.get('size', 0),
                    'open_interest': contract_data.get('open_interest', 0),
                    'implied_volatility': contract_data.get('iv', 0),
                    'delta': contract_data.get('delta', 0),
                    'gamma': contract_data.get('gamma', 0),
                    'theta': contract_data.get('theta', 0),
                    'vega': contract_data.get('vega', 0),
                    'underlying_price': contract_data.get('underlying_price', 0)
                }
                
                # Calculate mid price and spreads
                if contract['bid'] > 0 and contract['ask'] > 0:
                    contract['mid_price'] = (contract['bid'] + contract['ask']) / 2
                    contract['bid_ask_spread'] = contract['ask'] - contract['bid']
                    contract['spread_pct'] = contract['bid_ask_spread'] / contract['mid_price'] if contract['mid_price'] > 0 else 0
                else:
                    contract['mid_price'] = contract['last']
                    contract['bid_ask_spread'] = 0
                    contract['spread_pct'] = 0
                
                # Calculate days to expiration
                if contract['expiration']:
                    try:
                        exp_date = datetime.strptime(contract['expiration'], '%Y%m%d')
                        current_date = datetime.strptime(date, '%Y-%m-%d')
                        contract['days_to_expiration'] = (exp_date - current_date).days
                    except:
                        contract['days_to_expiration'] = 0
                else:
                    contract['days_to_expiration'] = 0
                
                # Calculate moneyness
                if contract['underlying_price'] > 0 and contract['strike'] > 0:
                    if contract['option_type'] == 'C':
                        contract['moneyness'] = contract['strike'] / contract['underlying_price']
                    else:  # Put
                        contract['moneyness'] = contract['underlying_price'] / contract['strike']
                else:
                    contract['moneyness'] = 0
                
                contracts.append(contract)
            
            df = pd.DataFrame(contracts)
            
            if not df.empty:
                # Sort by expiration, strike, and option type
                df = df.sort_values(['expiration', 'strike', 'option_type'])
                df = df.reset_index(drop=True)
                
                logger.info(f"Processed {len(df)} contracts")
                logger.info(f"Date range: {df['expiration'].min()} to {df['expiration'].max()}")
                logger.info(f"Strike range: ${df['strike'].min():.2f} to ${df['strike'].max():.2f}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing options chain data: {str(e)}")
            return pd.DataFrame()
    
    def _save_options_chain(self, df: pd.DataFrame, date: str) -> None:
        """
        Save options chain data to disk
        
        Args:
            df: Options chain DataFrame
            date: Date string for filename
        """
        try:
            filename = f"{self.data_dir}/SPY_options_chain_{date}.csv"
            df.to_csv(filename, index=False)
            logger.info(f"Saved options chain to {filename}")
            
            # Also save summary statistics
            summary = {
                'date': date,
                'total_contracts': len(df),
                'calls': len(df[df['option_type'] == 'C']),
                'puts': len(df[df['option_type'] == 'P']),
                'unique_expirations': df['expiration'].nunique(),
                'strike_range': f"${df['strike'].min():.2f} - ${df['strike'].max():.2f}",
                'underlying_price': df['underlying_price'].iloc[0] if not df.empty else 0,
                'avg_iv': df['implied_volatility'].mean(),
                'total_volume': df['volume'].sum(),
                'total_open_interest': df['open_interest'].sum()
            }
            
            summary_file = f"{self.data_dir}/SPY_summary_{date}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving options chain: {str(e)}")
    
    def load_options_chain(self, date: str) -> pd.DataFrame:
        """
        Load previously saved options chain from disk
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            DataFrame with options chain data
        """
        try:
            filename = f"{self.data_dir}/SPY_options_chain_{date}.csv"
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                logger.info(f"Loaded {len(df)} contracts from {filename}")
                return df
            else:
                logger.warning(f"No saved data found for {date}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading options chain for {date}: {str(e)}")
            return pd.DataFrame()
    
    def get_date_range_chains(self, start_date: str, end_date: str, 
                            weekdays_only: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Retrieve options chains for a date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            weekdays_only: Only fetch data for weekdays
            
        Returns:
            Dictionary mapping dates to DataFrames
        """
        logger.info(f"Fetching options chains from {start_date} to {end_date}")
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        chains = {}
        current_date = start
        
        while current_date <= end:
            # Skip weekends if requested
            if weekdays_only and current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Check if we already have this data
            existing_df = self.load_options_chain(date_str)
            if not existing_df.empty:
                chains[date_str] = existing_df
                logger.info(f"Using cached data for {date_str}")
            else:
                # Fetch new data
                df = self.get_spy_options_chain(date_str)
                if not df.empty:
                    chains[date_str] = df
                
                # Rate limiting - be respectful to the API
                time.sleep(1)
            
            current_date += timedelta(days=1)
        
        logger.info(f"Retrieved options chains for {len(chains)} dates")
        return chains
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Validate options chain data quality for backtesting
        
        Args:
            df: Options chain DataFrame
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'metrics': {}
        }
        
        if df.empty:
            validation['is_valid'] = False
            validation['errors'].append("DataFrame is empty")
            return validation
        
        # Check for required columns
        required_cols = ['strike', 'expiration', 'option_type', 'bid', 'ask', 
                        'implied_volatility', 'delta', 'underlying_price']
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            validation['is_valid'] = False
            validation['errors'].append(f"Missing required columns: {missing_cols}")
        
        # Check data quality metrics
        validation['metrics'] = {
            'total_contracts': len(df),
            'zero_bid_pct': (df['bid'] == 0).mean() * 100,
            'zero_iv_pct': (df['implied_volatility'] == 0).mean() * 100,
            'wide_spreads_pct': (df['spread_pct'] > 0.1).mean() * 100 if 'spread_pct' in df.columns else 0,
            'avg_volume': df['volume'].mean() if 'volume' in df.columns else 0
        }
        
        # Add warnings for data quality issues
        if validation['metrics']['zero_bid_pct'] > 50:
            validation['warnings'].append("High percentage of zero bids")
        
        if validation['metrics']['zero_iv_pct'] > 20:
            validation['warnings'].append("High percentage of zero IV values")
        
        if validation['metrics']['wide_spreads_pct'] > 30:
            validation['warnings'].append("High percentage of wide spreads (>10%)")
        
        return validation


def main():
    """
    Test the Theta Data client with sample SPY options chain
    """
    print("=" * 80)
    print("SPRINT 16: THETA DATA OPTIONS PIPELINE TEST")
    print("=" * 80)
    
    # Initialize client (using free tier for testing)
    client = ThetaDataClient()
    
    # Test with a recent date
    test_date = "2024-01-15"  # Monday to ensure market was open
    
    print(f"Testing SPY options chain retrieval for {test_date}")
    
    # Fetch options chain
    options_df = client.get_spy_options_chain(test_date)
    
    if not options_df.empty:
        print(f"\n✅ Successfully retrieved {len(options_df)} option contracts")
        
        # Display sample data
        print("\nSample contracts:")
        print(options_df[['strike', 'expiration', 'option_type', 'bid', 'ask', 
                         'implied_volatility', 'delta', 'days_to_expiration']].head(10))
        
        # Validate data quality
        validation = client.validate_data_quality(options_df)
        print(f"\n📊 Data Quality Validation:")
        print(f"Valid: {validation['is_valid']}")
        print(f"Warnings: {len(validation['warnings'])}")
        print(f"Errors: {len(validation['errors'])}")
        
        for warning in validation['warnings']:
            print(f"⚠️  {warning}")
        
        for error in validation['errors']:
            print(f"❌ {error}")
        
        print(f"\n📈 Data Metrics:")
        for key, value in validation['metrics'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
    else:
        print("❌ Failed to retrieve options chain data")
        print("This might be due to:")
        print("  1. Free tier limitations")
        print("  2. API endpoint changes")
        print("  3. Network connectivity issues")
        print("  4. Date format or market hours")


if __name__ == "__main__":
    main()