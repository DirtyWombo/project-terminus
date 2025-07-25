"""
Operation Badger - Stock Universe Manager
Defines and manages the tradable stock universe
Advanced stock selection and market intelligence
"""

import os
import logging
import json
import requests
import yfinance as yf
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class StockInfo:
    """Information about a tradable stock"""
    symbol: str
    name: str
    sector: str
    market_cap: float
    avg_volume: int
    price: float
    beta: float
    volatility: float
    is_active: bool = True

class StockUniverse:
    """
    Manages the universe of tradable stocks
    Focuses on liquid, high-quality equities
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configuration - EXPERT PIVOT: Small/Mid-Cap Focus
        # Large-caps (FAANG) are too efficient for 15-min narrative strategy
        # Small/mid-caps have less HFT coverage, narrative effects last longer
        self.focus_stocks = os.getenv('FOCUS_STOCKS', 'CRWD,SNOW,PLTR,RBLX,COIN,UBER,SPOT,ZM,SHOP,SQ,PYPL,ROKU,TWLO,OKTA,DDOG,NET').split(',')
        self.min_market_cap = 500_000_000    # $500M minimum (small-cap floor)
        self.max_market_cap = 50_000_000_000 # $50B maximum (avoid mega-caps)
        self.min_avg_volume = 500_000        # 500K shares daily (still liquid)
        self.max_volatility = 0.8            # 80% max (small-caps more volatile)
        
        # Stock universe
        self.stocks: Dict[str, StockInfo] = {}
        self.sectors: Set[str] = set()
        
        # Cache
        self._last_update = None
        self._update_interval = timedelta(hours=24)  # Update daily
        
        # Initialize universe
        self.initialize_universe()
    
    def initialize_universe(self):
        """Initialize the stock universe with focus stocks"""
        self.logger.info("Initializing stock universe...")
        
        # Start with focus stocks
        for symbol in self.focus_stocks:
            symbol = symbol.strip().upper()
            stock_info = self.get_stock_info(symbol)
            if stock_info:
                self.stocks[symbol] = stock_info
                self.sectors.add(stock_info.sector)
        
        # Add small/mid-cap growth stocks (Russell 2000 style)
        # Focus on: SaaS, fintech, biotech, emerging tech companies
        additional_stocks = [
            # Cloud/SaaS (high narrative sensitivity)
            'CRWD', 'SNOW', 'DDOG', 'NET', 'OKTA', 'ZS', 'ESTC', 'CFLT',
            # Fintech (regulatory/earnings sensitive)  
            'SQ', 'PYPL', 'COIN', 'SOFI', 'UPST', 'AFRM', 'HOOD',
            # Growth Tech (momentum driven)
            'PLTR', 'RBLX', 'U', 'PATH', 'FVRR', 'UBER', 'LYFT',
            # Biotech (FDA/trial sensitive)
            'MRNA', 'BNTX', 'NVAX', 'SGEN', 'BMRN', 'ALNY',
            # Consumer Digital (earnings sensitive)
            'ROKU', 'SPOT', 'ZM', 'DOCU', 'PTON', 'SNAP',
            # ETFs for regime detection
            'IWM', 'QQQ'  # Russell 2000 + Nasdaq
        ]
        
        for symbol in additional_stocks:
            if symbol not in self.stocks:
                stock_info = self.get_stock_info(symbol)
                if stock_info and self.is_suitable_for_trading(stock_info):
                    self.stocks[symbol] = stock_info
                    self.sectors.add(stock_info.sector)
        
        self._last_update = datetime.now()
        self.logger.info(f"Initialized universe with {len(self.stocks)} stocks across {len(self.sectors)} sectors")
    
    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """Get detailed information about a stock"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get recent price data for volatility calculation
            hist = ticker.history(period="1y")
            if hist.empty:
                self.logger.warning(f"No price history for {symbol}")
                return None
            
            # Calculate metrics
            current_price = hist['Close'].iloc[-1]
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5)  # Annualized volatility
            avg_volume = hist['Volume'].mean()
            
            # Extract stock information
            stock_info = StockInfo(
                symbol=symbol,
                name=info.get('longName', symbol),
                sector=info.get('sector', 'Unknown'),
                market_cap=info.get('marketCap', 0),
                avg_volume=int(avg_volume),
                price=float(current_price),
                beta=info.get('beta', 1.0) or 1.0,
                volatility=float(volatility),
                is_active=True
            )
            
            return stock_info
            
        except Exception as e:
            self.logger.error(f"Error getting info for {symbol}: {e}")
            return None
    
    def is_suitable_for_trading(self, stock_info: StockInfo) -> bool:
        """Check if stock meets small/mid-cap trading criteria"""
        # Check market cap range (avoid mega-caps AND micro-caps)
        if stock_info.market_cap < self.min_market_cap:
            return False
        if stock_info.market_cap > self.max_market_cap:
            return False  # NEW: Exclude mega-caps (too efficient for narrative strategy)
        
        # Check volume (still need liquidity)
        if stock_info.avg_volume < self.min_avg_volume:
            return False
        
        # Check volatility (small-caps can be more volatile)
        if stock_info.volatility > self.max_volatility:
            return False
        
        # Check price (avoid penny stocks)
        if stock_info.price < 5.0:  # Lowered from $10 for small-caps
            return False
        
        return True
    
    def get_tradable_symbols(self) -> List[str]:
        """Get list of symbols suitable for trading"""
        return [symbol for symbol, info in self.stocks.items() if info.is_active]
    
    def get_focus_symbols(self) -> List[str]:
        """Get focus stocks for primary strategy"""
        return [s.strip().upper() for s in self.focus_stocks if s.strip().upper() in self.stocks]
    
    def get_symbols_by_sector(self, sector: str) -> List[str]:
        """Get symbols in a specific sector"""
        return [
            symbol for symbol, info in self.stocks.items() 
            if info.sector == sector and info.is_active
        ]
    
    def get_high_beta_stocks(self, min_beta: float = 1.5) -> List[str]:
        """Get high-beta stocks for momentum strategies"""
        return [
            symbol for symbol, info in self.stocks.items()
            if info.beta >= min_beta and info.is_active
        ]
    
    def get_low_volatility_stocks(self, max_vol: float = 0.25) -> List[str]:
        """Get low-volatility stocks for conservative strategies"""
        return [
            symbol for symbol, info in self.stocks.items()
            if info.volatility <= max_vol and info.is_active
        ]
    
    def get_etf_symbols(self) -> List[str]:
        """Get ETF symbols for market regime detection"""
        etfs = ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VGK', 'EEM']
        return [etf for etf in etfs if etf in self.stocks]
    
    def update_universe(self, force: bool = False):
        """Update stock universe with latest data"""
        if not force and self._last_update:
            time_since_update = datetime.now() - self._last_update
            if time_since_update < self._update_interval:
                return
        
        self.logger.info("Updating stock universe...")
        
        # Update existing stocks
        updated_count = 0
        for symbol in list(self.stocks.keys()):
            try:
                updated_info = self.get_stock_info(symbol)
                if updated_info:
                    self.stocks[symbol] = updated_info
                    updated_count += 1
                else:
                    # Deactivate if can't get info
                    self.stocks[symbol].is_active = False
                    
            except Exception as e:
                self.logger.error(f"Error updating {symbol}: {e}")
        
        self._last_update = datetime.now()
        self.logger.info(f"Updated {updated_count} stocks in universe")
    
    def get_market_regime_indicators(self) -> Dict[str, float]:
        """Get key market indicators for regime detection"""
        indicators = {}
        
        try:
            # SPY for overall market
            spy = yf.Ticker('SPY')
            spy_hist = spy.history(period="3mo")
            
            if not spy_hist.empty:
                spy_price = spy_hist['Close'].iloc[-1]
                spy_sma_20 = spy_hist['Close'].tail(20).mean()
                spy_sma_50 = spy_hist['Close'].tail(50).mean() if len(spy_hist) >= 50 else spy_sma_20
                
                indicators['spy_price'] = spy_price
                indicators['spy_vs_sma20'] = (spy_price - spy_sma_20) / spy_sma_20
                indicators['spy_vs_sma50'] = (spy_price - spy_sma_50) / spy_sma_50
                indicators['spy_sma20_vs_sma50'] = (spy_sma_20 - spy_sma_50) / spy_sma_50
            
            # VIX for volatility regime
            vix = yf.Ticker('^VIX')
            vix_hist = vix.history(period="1mo")
            
            if not vix_hist.empty:
                vix_level = vix_hist['Close'].iloc[-1]
                indicators['vix_level'] = vix_level
                indicators['vix_regime'] = 'high' if vix_level > 25 else 'medium' if vix_level > 15 else 'low'
            
        except Exception as e:
            self.logger.error(f"Error getting market indicators: {e}")
        
        return indicators
    
    def save_universe(self, filepath: str = "stock_universe.json"):
        """Save universe to file"""
        try:
            universe_data = {
                'last_update': self._last_update.isoformat() if self._last_update else None,
                'stocks': {
                    symbol: {
                        'name': info.name,
                        'sector': info.sector,
                        'market_cap': info.market_cap,
                        'avg_volume': info.avg_volume,
                        'price': info.price,
                        'beta': info.beta,
                        'volatility': info.volatility,
                        'is_active': info.is_active
                    }
                    for symbol, info in self.stocks.items()
                },
                'sectors': list(self.sectors)
            }
            
            with open(filepath, 'w') as f:
                json.dump(universe_data, f, indent=2)
                
            self.logger.info(f"Universe saved to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving universe: {e}")
    
    def load_universe(self, filepath: str = "stock_universe.json"):
        """Load universe from file"""
        try:
            if not os.path.exists(filepath):
                return False
                
            with open(filepath, 'r') as f:
                universe_data = json.load(f)
            
            # Load stocks
            self.stocks = {}
            for symbol, data in universe_data.get('stocks', {}).items():
                self.stocks[symbol] = StockInfo(
                    symbol=symbol,
                    name=data['name'],
                    sector=data['sector'],
                    market_cap=data['market_cap'],
                    avg_volume=data['avg_volume'],
                    price=data['price'],
                    beta=data['beta'],
                    volatility=data['volatility'],
                    is_active=data['is_active']
                )
            
            # Load sectors
            self.sectors = set(universe_data.get('sectors', []))
            
            # Load last update time
            if universe_data.get('last_update'):
                self._last_update = datetime.fromisoformat(universe_data['last_update'])
            
            self.logger.info(f"Universe loaded from {filepath} - {len(self.stocks)} stocks")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading universe: {e}")
            return False
    
    def get_universe_summary(self) -> Dict:
        """Get summary statistics of the universe"""
        active_stocks = [info for info in self.stocks.values() if info.is_active]
        
        if not active_stocks:
            return {}
        
        total_market_cap = sum(s.market_cap for s in active_stocks)
        avg_volatility = sum(s.volatility for s in active_stocks) / len(active_stocks)
        avg_beta = sum(s.beta for s in active_stocks) / len(active_stocks)
        
        return {
            'total_stocks': len(active_stocks),
            'sectors': len(self.sectors),
            'total_market_cap': total_market_cap,
            'avg_volatility': avg_volatility,
            'avg_beta': avg_beta,
            'focus_stocks': len(self.get_focus_symbols()),
            'last_update': self._last_update.isoformat() if self._last_update else None
        }

# Global instance
stock_universe = StockUniverse()