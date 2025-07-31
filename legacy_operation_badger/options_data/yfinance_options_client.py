#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 16: YFinance Options Pipeline (Fallback)
Options data acquisition using yfinance for immediate testing

This module provides a fallback options data source for Sprint 16 development.
While limited to current data, it enables us to validate the backtesting framework
architecture before integrating with premium data providers.

Key Features:
- Current SPY options chain retrieval
- Greeks calculation estimation
- Data structure compatible with Theta Data format
- Immediate testing capability for Iron Condor development
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YFinanceOptionsClient:
    """
    YFinance-based options data client for Sprint 16 development
    Provides current options data in standardized format for backtesting framework validation
    """
    
    def __init__(self):
        """
        Initialize YFinance options client
        """
        # Create data directory structure
        self.data_dir = "options_data/spy_chains"
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info("YFinance Options client initialized")
        logger.info(f"Data directory: {self.data_dir}")
    
    def get_current_spy_options_chain(self, save_to_disk: bool = True) -> pd.DataFrame:
        """
        Retrieve current SPY options chain using yfinance
        
        Args:
            save_to_disk: Whether to save data locally
            
        Returns:
            DataFrame with current options chain data
        """
        logger.info("Fetching current SPY options chain from yfinance")
        
        try:
            # Get SPY ticker object
            spy = yf.Ticker("SPY")
            
            # Get current stock price
            current_price = spy.history(period='1d')['Close'].iloc[-1]
            logger.info(f"Current SPY price: ${current_price:.2f}")
            
            # Get options expiration dates
            expirations = spy.options
            logger.info(f"Available expirations: {len(expirations)} dates")
            
            all_contracts = []
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Process each expiration
            for exp_date in expirations[:8]:  # Limit to first 8 expirations for testing
                try:
                    # Get options chain for this expiration
                    options_chain = spy.option_chain(exp_date)
                    
                    # Process calls
                    calls = options_chain.calls
                    calls['option_type'] = 'C'
                    calls['expiration'] = exp_date
                    
                    # Process puts
                    puts = options_chain.puts
                    puts['option_type'] = 'P'
                    puts['expiration'] = exp_date
                    
                    # Combine calls and puts
                    exp_options = pd.concat([calls, puts], ignore_index=True)
                    all_contracts.append(exp_options)
                    
                    logger.info(f"Processed {len(exp_options)} contracts for {exp_date}")
                    
                except Exception as e:
                    logger.warning(f"Failed to get options for expiration {exp_date}: {str(e)}")
                    continue
            
            if not all_contracts:
                logger.error("No options data retrieved")
                return pd.DataFrame()
            
            # Combine all expirations
            df = pd.concat(all_contracts, ignore_index=True)
            
            # Standardize column names and add calculations
            df = self._standardize_options_data(df, current_price, current_date)
            
            if save_to_disk and not df.empty:
                self._save_options_chain(df, current_date)
            
            logger.info(f"Successfully retrieved {len(df)} option contracts")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching current options chain: {str(e)}")
            return pd.DataFrame()
    
    def _standardize_options_data(self, df: pd.DataFrame, underlying_price: float, date: str) -> pd.DataFrame:
        """
        Standardize yfinance options data to match Theta Data format
        
        Args:
            df: Raw yfinance options DataFrame
            underlying_price: Current underlying price
            date: Current date string
            
        Returns:
            Standardized DataFrame
        """
        try:
            # Rename columns to match our standard format
            column_mapping = {
                'contractSymbol': 'contract_symbol',
                'lastTradeDate': 'last_trade_date',
                'impliedVolatility': 'implied_volatility',
                'openInterest': 'open_interest',
                'contractSize': 'contract_size',
                'lastPrice': 'last'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Add standard columns
            df['date'] = date
            df['underlying'] = 'SPY'
            df['underlying_price'] = underlying_price
            
            # Ensure required columns exist
            required_columns = ['bid', 'ask', 'last', 'volume', 'open_interest', 
                              'implied_volatility', 'strike', 'option_type', 'expiration']
            
            for col in required_columns:
                if col not in df.columns:
                    df[col] = 0
            
            # Calculate additional fields
            df['mid_price'] = (df['bid'] + df['ask']) / 2
            df['bid_ask_spread'] = df['ask'] - df['bid']
            df['spread_pct'] = np.where(df['mid_price'] > 0, 
                                      df['bid_ask_spread'] / df['mid_price'], 0)
            
            # Calculate days to expiration
            df['days_to_expiration'] = df['expiration'].apply(
                lambda x: (datetime.strptime(x, '%Y-%m-%d') - datetime.strptime(date, '%Y-%m-%d')).days
            )
            
            # Calculate moneyness
            df['moneyness'] = np.where(
                df['option_type'] == 'C',
                df['strike'] / underlying_price,
                underlying_price / df['strike']
            )
            
            # Estimate Greeks (simplified calculations for testing)
            df = self._estimate_greeks(df, underlying_price)
            
            # Clean and sort data
            df = df.dropna(subset=['strike', 'expiration'])
            df = df.sort_values(['expiration', 'strike', 'option_type'])
            df = df.reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error standardizing options data: {str(e)}")
            return df
    
    def _estimate_greeks(self, df: pd.DataFrame, underlying_price: float) -> pd.DataFrame:
        """
        Estimate Greeks using simplified Black-Scholes approximations
        Note: These are rough estimates for testing purposes only
        
        Args:
            df: Options DataFrame
            underlying_price: Current underlying price
            
        Returns:
            DataFrame with estimated Greeks
        """
        try:
            # Risk-free rate assumption (simplified)
            risk_free_rate = 0.05
            
            # Calculate time to expiration in years
            df['time_to_exp_years'] = df['days_to_expiration'] / 365.0
            
            # Simplified Delta calculation
            df['delta'] = np.where(
                df['option_type'] == 'C',
                np.maximum(0, np.minimum(1, 0.5 + (underlying_price - df['strike']) / (underlying_price * 0.3))),
                np.maximum(-1, np.minimum(0, -0.5 + (underlying_price - df['strike']) / (underlying_price * 0.3)))
            )
            
            # Simplified Gamma (highest near ATM)
            df['gamma'] = np.exp(-0.5 * ((df['strike'] - underlying_price) / (underlying_price * 0.2)) ** 2) / (underlying_price * np.sqrt(2 * np.pi) * 0.2)
            df['gamma'] = df['gamma'] * 0.01  # Scale appropriately
            
            # Simplified Theta (time decay, negative for long positions)
            df['theta'] = -df['implied_volatility'] * underlying_price * df['gamma'] * np.sqrt(df['time_to_exp_years']) / (2 * np.sqrt(2 * np.pi))
            df['theta'] = df['theta'] / 365  # Daily theta
            
            # Simplified Vega (volatility sensitivity)
            df['vega'] = underlying_price * df['gamma'] * np.sqrt(df['time_to_exp_years']) / 100
            
            # Clean up temporary columns
            df = df.drop(['time_to_exp_years'], axis=1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error estimating Greeks: {str(e)}")
            return df
    
    def _save_options_chain(self, df: pd.DataFrame, date: str) -> None:
        """
        Save options chain data to disk
        
        Args:
            df: Options chain DataFrame
            date: Date string for filename
        """
        try:
            filename = f"{self.data_dir}/SPY_options_chain_current_{date}.csv"
            df.to_csv(filename, index=False)
            logger.info(f"Saved options chain to {filename}")
            
            # Also save summary statistics
            summary = {
                'date': date,
                'data_source': 'yfinance',
                'total_contracts': int(len(df)),
                'calls': int(len(df[df['option_type'] == 'C'])),
                'puts': int(len(df[df['option_type'] == 'P'])),
                'unique_expirations': int(df['expiration'].nunique()),
                'strike_range': f"${df['strike'].min():.2f} - ${df['strike'].max():.2f}",
                'underlying_price': float(df['underlying_price'].iloc[0]) if not df.empty else 0,
                'avg_iv': float(df['implied_volatility'].mean()),
                'total_volume': int(df['volume'].sum()),
                'total_open_interest': int(df['open_interest'].sum()),
                'expirations': sorted(df['expiration'].unique().tolist())
            }
            
            summary_file = f"{self.data_dir}/SPY_summary_current_{date}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving options chain: {str(e)}")
    
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
            'avg_volume': df['volume'].mean() if 'volume' in df.columns else 0,
            'atm_contracts': len(df[abs(df['moneyness'] - 1.0) < 0.05]) if 'moneyness' in df.columns else 0
        }
        
        # Add warnings for data quality issues
        if validation['metrics']['zero_bid_pct'] > 50:
            validation['warnings'].append("High percentage of zero bids")
        
        if validation['metrics']['zero_iv_pct'] > 20:
            validation['warnings'].append("High percentage of zero IV values")
        
        if validation['metrics']['wide_spreads_pct'] > 30:
            validation['warnings'].append("High percentage of wide spreads (>10%)")
        
        if validation['metrics']['atm_contracts'] < 10:
            validation['warnings'].append("Few at-the-money contracts available")
        
        return validation
    
    def get_iron_condor_strikes(self, df: pd.DataFrame, target_dte: int = 30, 
                               delta_short: float = 0.10) -> Dict[str, float]:
        """
        Find suitable strikes for Iron Condor strategy
        
        Args:
            df: Options chain DataFrame
            target_dte: Target days to expiration
            delta_short: Target delta for short strikes
            
        Returns:
            Dictionary with recommended strikes
        """
        try:
            # Filter to target expiration (closest to target DTE)
            df_exp = df[abs(df['days_to_expiration'] - target_dte) <= 7].copy()
            
            if df_exp.empty:
                logger.warning(f"No options found near {target_dte} DTE")
                return {}
            
            # Get the closest expiration
            target_exp = df_exp.iloc[0]['expiration']
            df_target = df_exp[df_exp['expiration'] == target_exp].copy()
            
            underlying_price = df_target['underlying_price'].iloc[0]
            
            # Find call and put strikes near target delta
            calls = df_target[df_target['option_type'] == 'C'].copy()
            puts = df_target[df_target['option_type'] == 'P'].copy()
            
            # Short call (OTM call with delta ~ target_delta)
            short_call_candidates = calls[calls['delta'].between(delta_short - 0.05, delta_short + 0.05)]
            if short_call_candidates.empty:
                short_call_candidates = calls[calls['strike'] > underlying_price].head(3)
            
            # Short put (OTM put with delta ~ -target_delta)
            short_put_candidates = puts[puts['delta'].between(-delta_short - 0.05, -delta_short + 0.05)]
            if short_put_candidates.empty:
                short_put_candidates = puts[puts['strike'] < underlying_price].tail(3)
            
            if short_call_candidates.empty or short_put_candidates.empty:
                logger.warning("Could not find suitable short strikes")
                return {}
            
            # Select best strikes (highest premium)
            short_call_strike = short_call_candidates.loc[short_call_candidates['bid'].idxmax(), 'strike']
            short_put_strike = short_put_candidates.loc[short_put_candidates['bid'].idxmax(), 'strike']
            
            # Long strikes (further OTM)
            wing_width = 10  # $10 wings
            long_call_strike = short_call_strike + wing_width
            long_put_strike = short_put_strike - wing_width
            
            iron_condor = {
                'expiration': target_exp,
                'days_to_expiration': int(df_target.iloc[0]['days_to_expiration']),
                'underlying_price': float(underlying_price),
                'short_call_strike': float(short_call_strike),
                'long_call_strike': float(long_call_strike),
                'short_put_strike': float(short_put_strike),
                'long_put_strike': float(long_put_strike),
                'wing_width': wing_width
            }
            
            logger.info(f"Iron Condor strikes found: {iron_condor}")
            return iron_condor
            
        except Exception as e:
            logger.error(f"Error finding Iron Condor strikes: {str(e)}")
            return {}


def main():
    """
    Test the YFinance options client
    """
    print("=" * 80)
    print("SPRINT 16: YFINANCE OPTIONS PIPELINE TEST")
    print("=" * 80)
    
    # Initialize client
    client = YFinanceOptionsClient()
    
    print("Testing current SPY options chain retrieval")
    
    # Fetch current options chain
    options_df = client.get_current_spy_options_chain()
    
    if not options_df.empty:
        print(f"\nSuccessfully retrieved {len(options_df)} option contracts")
        
        # Display sample data
        print("\nSample contracts:")
        sample_cols = ['strike', 'expiration', 'option_type', 'bid', 'ask', 
                      'implied_volatility', 'delta', 'days_to_expiration']
        print(options_df[sample_cols].head(10))
        
        # Validate data quality
        validation = client.validate_data_quality(options_df)
        print(f"\nData Quality Validation:")
        print(f"Valid: {validation['is_valid']}")
        print(f"Warnings: {len(validation['warnings'])}")
        print(f"Errors: {len(validation['errors'])}")
        
        for warning in validation['warnings']:
            print(f"Warning: {warning}")
        
        for error in validation['errors']:
            print(f"Error: {error}")
        
        print(f"\nData Metrics:")
        for key, value in validation['metrics'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        # Test Iron Condor strike selection
        iron_condor = client.get_iron_condor_strikes(options_df)
        if iron_condor:
            print(f"\nIron Condor Example:")
            print(f"  Expiration: {iron_condor['expiration']}")
            print(f"  Underlying: ${iron_condor['underlying_price']:.2f}")
            print(f"  Short Call: ${iron_condor['short_call_strike']:.2f}")
            print(f"  Long Call: ${iron_condor['long_call_strike']:.2f}")
            print(f"  Short Put: ${iron_condor['short_put_strike']:.2f}")
            print(f"  Long Put: ${iron_condor['long_put_strike']:.2f}")
        
    else:
        print("Failed to retrieve options chain data")


if __name__ == "__main__":
    main()