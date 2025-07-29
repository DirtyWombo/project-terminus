#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 16: Unified Historical Options Data Manager
Integrates Theta Data (historical) + yfinance (current) for seamless backtesting

This module provides a unified interface for accessing historical options data
from multiple sources, with intelligent caching and data quality validation.
Built to integrate with the existing Operation Badger infrastructure.

Key Features:
- Unified API for Theta Data and yfinance
- Intelligent caching with Operation Badger patterns
- Data quality validation and standardization
- Performance optimization for large-scale backtesting
- Integration with core options backtesting engine
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
import sqlite3
from pathlib import Path
import hashlib
from enum import Enum

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from options_data.theta_data_client import ThetaDataClient
from options_data.yfinance_options_client import YFinanceOptionsClient
from options_backtesting.core_engine import OptionContract, OptionType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSource(Enum):
    """Data source enumeration"""
    THETA_DATA = "theta_data"
    YFINANCE = "yfinance"
    CACHE = "cache"

class HistoricalOptionsManager:
    """
    Unified historical options data manager
    Integrates multiple data sources with intelligent caching
    """
    
    def __init__(self, cache_dir: str = "options_cache", enable_cache: bool = True):
        """
        Initialize historical options manager
        
        Args:
            cache_dir: Directory for caching options data
            enable_cache: Whether to enable local caching
        """
        self.cache_dir = Path(cache_dir)
        self.enable_cache = enable_cache
        
        # Create cache directory
        if enable_cache:
            self.cache_dir.mkdir(exist_ok=True)
            self.db_path = self.cache_dir / "options_cache.db"
            self._init_cache_db()
        
        # Initialize data clients
        self.theta_client = ThetaDataClient()
        self.yf_client = YFinanceOptionsClient()
        
        # Data quality thresholds
        self.min_volume_threshold = 10
        self.max_spread_pct = 0.5  # 50% max bid-ask spread
        self.min_open_interest = 5
        
        logger.info("Historical Options Manager initialized")
        logger.info(f"Cache directory: {self.cache_dir}")
        logger.info(f"Cache enabled: {enable_cache}")
        
    def _init_cache_db(self):
        """Initialize SQLite cache database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create cache metadata table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cache_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key TEXT UNIQUE,
                        symbol TEXT,
                        date TEXT,
                        data_source TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        file_path TEXT,
                        data_quality_score REAL,
                        contract_count INTEGER
                    )
                """)
                
                # Create data quality metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS data_quality (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key TEXT,
                        zero_bid_pct REAL,
                        zero_iv_pct REAL,
                        wide_spreads_pct REAL,
                        avg_volume REAL,
                        total_open_interest INTEGER,
                        quality_score REAL,
                        FOREIGN KEY (cache_key) REFERENCES cache_metadata(cache_key)
                    )
                """)
                
                conn.commit()
                logger.info("Cache database initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize cache database: {e}")
            
    def _generate_cache_key(self, symbol: str, date: str, data_source: str) -> str:
        """Generate unique cache key"""
        key_string = f"{symbol}_{date}_{data_source}"
        return hashlib.md5(key_string.encode()).hexdigest()
        
    def get_options_chain(self, symbol: str, date: str, 
                         prefer_theta: bool = True) -> List[OptionContract]:
        """
        Get options chain for a specific symbol and date
        
        Args:
            symbol: Underlying symbol (e.g., 'SPY')
            date: Date in YYYY-MM-DD format
            prefer_theta: Whether to prefer Theta Data over yfinance
            
        Returns:
            List of OptionContract objects
        """
        logger.info(f"Requesting options chain for {symbol} on {date}")
        
        # Check cache first
        if self.enable_cache:
            cached_data = self._get_from_cache(symbol, date)
            if cached_data:
                logger.info(f"Retrieved {len(cached_data)} contracts from cache")
                return cached_data
        
        # Determine data source priority
        sources = [DataSource.THETA_DATA, DataSource.YFINANCE] if prefer_theta else [DataSource.YFINANCE, DataSource.THETA_DATA]
        
        for source in sources:
            try:
                if source == DataSource.THETA_DATA:
                    raw_data = self._get_theta_data(symbol, date)
                    if raw_data is not None and not raw_data.empty:
                        contracts = self._convert_to_contracts(raw_data, DataSource.THETA_DATA)
                        break
                        
                elif source == DataSource.YFINANCE:
                    # For current/recent dates, use yfinance
                    if self._is_recent_date(date):
                        raw_data = self._get_yfinance_data(symbol)
                        if raw_data is not None and not raw_data.empty:
                            contracts = self._convert_to_contracts(raw_data, DataSource.YFINANCE)
                            break
                    else:
                        logger.info(f"Date {date} too old for yfinance, skipping")
                        continue
                        
            except Exception as e:
                logger.warning(f"Failed to get data from {source.value}: {e}")
                continue
        else:
            logger.error(f"Failed to retrieve options data for {symbol} on {date}")
            return []
        
        # Validate and filter data quality
        contracts = self._validate_data_quality(contracts)
        
        # Cache the results
        if self.enable_cache and contracts:
            self._save_to_cache(symbol, date, contracts, source)
            
        logger.info(f"Retrieved {len(contracts)} quality contracts for {symbol} on {date}")
        return contracts
        
    def _get_theta_data(self, symbol: str, date: str) -> Optional[pd.DataFrame]:
        """Get data from Theta Data"""
        try:
            return self.theta_client.get_spy_options_chain(date, save_to_disk=False)
        except Exception as e:
            logger.warning(f"Theta Data error: {e}")
            return None
            
    def _get_yfinance_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get current data from yfinance"""
        try:
            return self.yf_client.get_current_spy_options_chain(save_to_disk=False)
        except Exception as e:
            logger.warning(f"yfinance error: {e}")
            return None
            
    def _is_recent_date(self, date: str, days_threshold: int = 30) -> bool:
        """Check if date is recent enough for yfinance"""
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d')
            return (datetime.now() - target_date).days <= days_threshold
        except:
            return False
            
    def _convert_to_contracts(self, df: pd.DataFrame, source: DataSource) -> List[OptionContract]:
        """Convert DataFrame to OptionContract objects"""
        contracts = []
        
        for _, row in df.iterrows():
            try:
                # Handle different column naming between sources
                if source == DataSource.THETA_DATA:
                    option_type = OptionType.CALL if row.get('option_type', 'C') == 'C' else OptionType.PUT
                else:  # yfinance
                    option_type = OptionType.CALL if row.get('option_type', 'C') == 'C' else OptionType.PUT
                
                contract = OptionContract(
                    symbol=row.get('contract_symbol', f"{row.get('underlying', 'SPY')}{row.get('expiration', '')}{option_type.value}{int(row.get('strike', 0)*1000):08d}"),
                    underlying=row.get('underlying', 'SPY'),
                    strike=float(row.get('strike', 0)),
                    expiration=row.get('expiration', ''),
                    option_type=option_type,
                    
                    # Market data (handle NaN values)
                    bid=float(row.get('bid', 0)) if pd.notna(row.get('bid', 0)) else 0.0,
                    ask=float(row.get('ask', 0)) if pd.notna(row.get('ask', 0)) else 0.0,
                    last=float(row.get('last', 0)) if pd.notna(row.get('last', 0)) else 0.0,
                    volume=int(row.get('volume', 0)) if pd.notna(row.get('volume', 0)) else 0,
                    open_interest=int(row.get('open_interest', 0)) if pd.notna(row.get('open_interest', 0)) else 0,
                    
                    # Greeks (handle NaN values)
                    delta=float(row.get('delta', 0)) if pd.notna(row.get('delta', 0)) else 0.0,
                    gamma=float(row.get('gamma', 0)) if pd.notna(row.get('gamma', 0)) else 0.0,
                    theta=float(row.get('theta', 0)) if pd.notna(row.get('theta', 0)) else 0.0,
                    vega=float(row.get('vega', 0)) if pd.notna(row.get('vega', 0)) else 0.0,
                    implied_volatility=float(row.get('implied_volatility', 0)) if pd.notna(row.get('implied_volatility', 0)) else 0.0,
                    
                    # Derived fields (handle NaN values)
                    mid_price=float(row.get('mid_price', 0)) if pd.notna(row.get('mid_price', 0)) else 0.0,
                    days_to_expiration=int(row.get('days_to_expiration', 0)) if pd.notna(row.get('days_to_expiration', 0)) else 0,
                    underlying_price=float(row.get('underlying_price', 0)) if pd.notna(row.get('underlying_price', 0)) else 0.0,
                    moneyness=float(row.get('moneyness', 1.0)) if pd.notna(row.get('moneyness', 1.0)) else 1.0
                )
                
                contracts.append(contract)
                
            except Exception as e:
                logger.warning(f"Failed to convert row to contract: {e}")
                continue
                
        return contracts
        
    def _validate_data_quality(self, contracts: List[OptionContract]) -> List[OptionContract]:
        """Filter contracts based on data quality criteria"""
        if not contracts:
            return contracts
            
        initial_count = len(contracts)
        
        # Filter criteria
        quality_contracts = []
        
        for contract in contracts:
            # Skip if no bid/ask or wide spreads
            if contract.bid <= 0 or contract.ask <= 0:
                continue
                
            spread_pct = (contract.ask - contract.bid) / contract.mid_price if contract.mid_price > 0 else 1.0
            if spread_pct > self.max_spread_pct:
                continue
                
            # Skip low volume/open interest (except for very short DTE)
            if contract.days_to_expiration > 7:
                if contract.volume < self.min_volume_threshold and contract.open_interest < self.min_open_interest:
                    continue
            
            # Skip if IV is unreasonable
            if contract.implied_volatility <= 0 or contract.implied_volatility > 5.0:  # 500% IV cap
                continue
                
            quality_contracts.append(contract)
            
        filtered_count = len(quality_contracts)
        logger.info(f"Data quality filter: {initial_count} -> {filtered_count} contracts ({(filtered_count/initial_count*100):.1f}% kept)")
        
        return quality_contracts
        
    def _get_from_cache(self, symbol: str, date: str) -> Optional[List[OptionContract]]:
        """Retrieve options chain from cache"""
        if not self.enable_cache:
            return None
            
        try:
            cache_key = self._generate_cache_key(symbol, date, "any")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT file_path, data_source FROM cache_metadata 
                    WHERE symbol = ? AND date = ?
                    ORDER BY created_at DESC LIMIT 1
                """, (symbol, date))
                
                result = cursor.fetchone()
                if not result:
                    return None
                    
                file_path, data_source = result
                
                # Load cached data
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    return self._convert_to_contracts(df, DataSource(data_source))
                    
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
            
        return None
        
    def _save_to_cache(self, symbol: str, date: str, contracts: List[OptionContract], source: DataSource):
        """Save options chain to cache"""
        if not self.enable_cache or not contracts:
            return
            
        try:
            cache_key = self._generate_cache_key(symbol, date, source.value)
            
            # Convert contracts back to DataFrame for storage
            df_data = []
            for contract in contracts:
                df_data.append({
                    'symbol': contract.symbol,
                    'underlying': contract.underlying,
                    'strike': contract.strike,
                    'expiration': contract.expiration,
                    'option_type': contract.option_type.value,
                    'bid': contract.bid,
                    'ask': contract.ask,
                    'last': contract.last,
                    'volume': contract.volume,
                    'open_interest': contract.open_interest,
                    'delta': contract.delta,
                    'gamma': contract.gamma,
                    'theta': contract.theta,
                    'vega': contract.vega,
                    'implied_volatility': contract.implied_volatility,
                    'mid_price': contract.mid_price,
                    'days_to_expiration': contract.days_to_expiration,
                    'underlying_price': contract.underlying_price,
                    'moneyness': contract.moneyness
                })
                
            df = pd.DataFrame(df_data)
            
            # Save to file
            file_path = self.cache_dir / f"{cache_key}.csv"
            df.to_csv(file_path, index=False)
            
            # Calculate data quality metrics
            quality_metrics = self._calculate_quality_metrics(df)
            
            # Save metadata to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO cache_metadata 
                    (cache_key, symbol, date, data_source, file_path, data_quality_score, contract_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (cache_key, symbol, date, source.value, str(file_path), 
                      quality_metrics['quality_score'], len(contracts)))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO data_quality 
                    (cache_key, zero_bid_pct, zero_iv_pct, wide_spreads_pct, avg_volume, total_open_interest, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (cache_key, quality_metrics['zero_bid_pct'], quality_metrics['zero_iv_pct'],
                      quality_metrics['wide_spreads_pct'], quality_metrics['avg_volume'],
                      quality_metrics['total_open_interest'], quality_metrics['quality_score']))
                
                conn.commit()
                
            logger.info(f"Cached {len(contracts)} contracts for {symbol} on {date}")
            
        except Exception as e:
            logger.error(f"Cache save error: {e}")
            
    def _calculate_quality_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate data quality metrics"""
        if df.empty:
            return {'quality_score': 0.0, 'zero_bid_pct': 100.0, 'zero_iv_pct': 100.0, 
                   'wide_spreads_pct': 100.0, 'avg_volume': 0.0, 'total_open_interest': 0}
        
        zero_bid_pct = (df['bid'] == 0).mean() * 100
        zero_iv_pct = (df['implied_volatility'] == 0).mean() * 100
        
        # Calculate spread percentage
        df['spread_pct'] = np.where(df['mid_price'] > 0, 
                                   (df['ask'] - df['bid']) / df['mid_price'], 0)
        wide_spreads_pct = (df['spread_pct'] > 0.1).mean() * 100
        
        avg_volume = df['volume'].mean()
        total_open_interest = df['open_interest'].sum()
        
        # Calculate overall quality score (0-100)
        quality_score = 100.0
        quality_score -= min(zero_bid_pct, 50)  # Penalize zero bids (max -50)
        quality_score -= min(zero_iv_pct * 2, 30)  # Penalize zero IV (max -30)
        quality_score -= min(wide_spreads_pct / 2, 20)  # Penalize wide spreads (max -20)
        quality_score = max(quality_score, 0)
        
        return {
            'quality_score': quality_score,
            'zero_bid_pct': zero_bid_pct,
            'zero_iv_pct': zero_iv_pct,
            'wide_spreads_pct': wide_spreads_pct,
            'avg_volume': avg_volume,
            'total_open_interest': int(total_open_interest)
        }
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enable_cache:
            return {'cache_enabled': False}
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM cache_metadata")
                total_cached = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(data_quality_score) FROM cache_metadata")
                avg_quality = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT SUM(contract_count) FROM cache_metadata")
                total_contracts = cursor.fetchone()[0] or 0
                
                return {
                    'cache_enabled': True,
                    'cached_datasets': total_cached,
                    'total_contracts_cached': total_contracts,
                    'average_quality_score': round(avg_quality, 2),
                    'cache_directory': str(self.cache_dir)
                }
                
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {'cache_enabled': True, 'error': str(e)}
            
    def clear_cache(self, older_than_days: int = 30):
        """Clear old cache entries"""
        if not self.enable_cache:
            return
            
        try:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get files to delete
                cursor.execute("""
                    SELECT file_path FROM cache_metadata 
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))
                
                files_to_delete = cursor.fetchall()
                
                # Delete files
                for (file_path,) in files_to_delete:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                
                # Delete database records
                cursor.execute("DELETE FROM cache_metadata WHERE created_at < ?", 
                              (cutoff_date.isoformat(),))
                cursor.execute("DELETE FROM data_quality WHERE cache_key NOT IN (SELECT cache_key FROM cache_metadata)")
                
                conn.commit()
                
                logger.info(f"Cleared {len(files_to_delete)} old cache entries")
                
        except Exception as e:
            logger.error(f"Cache clear error: {e}")


def main():
    """
    Test the unified historical options manager
    """
    print("=" * 80)
    print("SPRINT 16: HISTORICAL OPTIONS MANAGER TEST")
    print("=" * 80)
    
    # Initialize manager
    manager = HistoricalOptionsManager(enable_cache=True)
    
    # Test with current date (should use yfinance)
    current_date = datetime.now().strftime('%Y-%m-%d')
    print(f"Testing current date: {current_date}")
    
    contracts = manager.get_options_chain('SPY', current_date)
    print(f"Retrieved {len(contracts)} contracts for current date")
    
    if contracts:
        # Show sample contracts
        print("\nSample contracts:")
        for i, contract in enumerate(contracts[:5]):
            print(f"  {i+1}. {contract.symbol}: ${contract.strike} {contract.option_type.value} "
                  f"exp={contract.expiration} bid=${contract.bid:.2f} ask=${contract.ask:.2f}")
    
    # Test with historical date (should attempt Theta Data, fallback to cache/error)
    historical_date = "2024-01-15"
    print(f"\nTesting historical date: {historical_date}")
    
    historical_contracts = manager.get_options_chain('SPY', historical_date)
    print(f"Retrieved {len(historical_contracts)} contracts for historical date")
    
    # Show cache statistics
    cache_stats = manager.get_cache_stats()
    print(f"\nCache Statistics:")
    for key, value in cache_stats.items():
        print(f"  {key}: {value}")
    
    print("\nHistorical Options Manager test completed [SUCCESS]")


if __name__ == "__main__":
    main()