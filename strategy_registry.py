"""
Strategy Registry - Central hub for all implemented strategies
From The Compendium - Complete strategy library

Organizes all 28 strategies by category and priority
Provides unified interface for strategy testing and validation
"""

from golden_cross_strategy import GoldenCrossStrategy
from triple_ma_strategy import TripleMAStrategy
from macd_crossover_strategy import MACDCrossoverStrategy
from momentum_breakout_strategy import MomentumBreakoutStrategy
from bollinger_bounce_strategy import BollingerBounceStrategy
from rsi_strategy import RSIStrategy
from z_score_reversion_strategy import ZScoreReversionStrategy
from pairs_trading_strategy import PairsTradingStrategy
from vix_mean_reversion_strategy import VIXMeanReversionStrategy
from earnings_surprise_strategy import EarningsSurpriseStrategy
from value_factor_strategy import ValueFactorStrategy
from quality_factor_strategy import QualityFactorStrategy
from profitability_factor_strategy import ProfitabilityFactorStrategy
from sector_pairs_strategy import SectorPairsStrategy
from garch_forecasting_strategy import GARCHForecastingStrategy

class StrategyRegistry:
    """
    Central registry for all implemented trading strategies
    Provides organized access to strategy library
    """
    
    def __init__(self):
        self.strategies = self._initialize_strategies()
        
    def _initialize_strategies(self):
        """Initialize all available strategies"""
        return {
            # TREND FOLLOWING STRATEGIES (Chapter 5)
            'S02_golden_cross': {
                'class': GoldenCrossStrategy,
                'name': 'Golden Cross (50/200 MA)',
                'category': 'trend_following',
                'priority': 'high',
                'status': 'implemented',
                'params': {'short_window': 50, 'long_window': 200, 'trend_filter': True},
                'description': '50/200-day MA crossover with trend filter'
            },
            
            'S03_triple_ma': {
                'class': TripleMAStrategy,
                'name': 'Triple MA System',
                'category': 'trend_following', 
                'priority': 'high',
                'status': 'implemented',
                'params': {'short_window': 10, 'medium_window': 20, 'long_window': 50},
                'description': 'Three MA alignment system (10/20/50)'
            },
            
            'S04_macd': {
                'class': MACDCrossoverStrategy,
                'name': 'MACD Crossover',
                'category': 'trend_following',
                'priority': 'high', 
                'status': 'implemented',
                'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                'description': 'MACD bullish crossover with histogram filter'
            },
            
            'S05_momentum_breakout': {
                'class': MomentumBreakoutStrategy,
                'name': 'Momentum Breakout',
                'category': 'trend_following',
                'priority': 'high',
                'status': 'implemented', 
                'params': {'breakout_period': 20, 'volume_multiplier': 1.5},
                'description': '20-day high breakout with volume confirmation'
            },
            
            # MEAN REVERSION STRATEGIES (Chapter 6)
            'S07_bollinger_bounce': {
                'class': BollingerBounceStrategy,
                'name': 'Bollinger Bounce',
                'category': 'mean_reversion',
                'priority': 'high',
                'status': 'implemented',
                'params': {'period': 20, 'std_dev': 2.0, 'trend_filter': False},
                'description': 'Buy at lower Bollinger Band, sell at middle'
            },
            
            'S08_rsi': {
                'class': RSIStrategy,
                'name': 'RSI Oversold/Overbought',
                'category': 'mean_reversion',
                'priority': 'high',
                'status': 'implemented',
                'params': {'rsi_period': 14, 'oversold_threshold': 30, 'overbought_threshold': 70},
                'description': 'RSI mean reversion at extreme levels'
            },
            
            'S10_zscore': {
                'class': ZScoreReversionStrategy,
                'name': 'Z-Score Reversion',
                'category': 'mean_reversion',
                'priority': 'medium',
                'status': 'implemented',
                'params': {'lookback_period': 50, 'entry_threshold': -2.0},
                'description': 'Statistical mean reversion using Z-scores'
            },
            
            # PAIRS TRADING STRATEGIES (Chapter 8)
            'S16_pairs_correlation': {
                'class': PairsTradingStrategy,
                'name': 'Correlation Pairs',
                'category': 'pairs_trading',
                'priority': 'medium',
                'status': 'implemented',
                'params': {'correlation_threshold': 0.8, 'entry_threshold': 2.0},
                'description': 'Market neutral pairs based on correlation'
            },
            
            'S17_sector_pairs': {
                'class': SectorPairsStrategy,
                'name': 'Sector Pairs',
                'category': 'pairs_trading',
                'priority': 'medium',
                'status': 'implemented',
                'params': {'entry_threshold': 2.0},
                'description': 'Sector-neutral pairs trading'
            },
            
            # VOLATILITY STRATEGIES (Chapter 7)
            'S18_vix_reversion': {
                'class': VIXMeanReversionStrategy,
                'name': 'VIX Mean Reversion',
                'category': 'volatility',
                'priority': 'medium',
                'status': 'implemented',
                'params': {'high_vix_threshold': 30, 'low_vix_threshold': 15},
                'description': 'Buy market on VIX spikes (fear contrarian)'
            },
            
            'S20_garch_forecasting': {
                'class': GARCHForecastingStrategy,
                'name': 'GARCH Forecasting',
                'category': 'volatility',
                'priority': 'medium',
                'status': 'implemented',
                'params': {'lookback_period': 60, 'vol_threshold': 0.2},
                'description': 'Volatility forecasting using GARCH model'
            },
            
            # FACTOR STRATEGIES (Chapter 9)
            'S11_value_factor': {
                'class': ValueFactorStrategy,
                'name': 'Single-Factor Value',
                'category': 'factor_based',
                'priority': 'high',
                'status': 'implemented',
                'params': {'rebalance_freq': 'M', 'top_percentile': 0.1},
                'description': 'Top decile earnings yield portfolio'
            },
            
            'S13_quality_factor': {
                'class': QualityFactorStrategy,
                'name': 'Quality Factor',
                'category': 'factor_based',
                'priority': 'medium',
                'status': 'implemented',
                'params': {'rebalance_freq': 'M', 'top_percentile': 0.2},
                'description': 'High quality metrics: ROE, ROA, low debt'
            },
            
            'S14_profitability_factor': {
                'class': ProfitabilityFactorStrategy,
                'name': 'Profitability Factor',
                'category': 'factor_based',
                'priority': 'medium',
                'status': 'implemented',
                'params': {'rebalance_freq': 'M', 'top_percentile': 0.2},
                'description': 'Superior profit generation ability'
            },
            
            # EVENT-DRIVEN STRATEGIES (Chapter 10)
            'S21_earnings_surprise': {
                'class': EarningsSurpriseStrategy,
                'name': 'Earnings Surprise',
                'category': 'event_driven',
                'priority': 'medium',
                'status': 'implemented',
                'params': {'surprise_threshold': 0.05, 'volume_multiplier': 2.0},
                'description': 'Post-earnings momentum on positive surprises'
            },
            
            # PLACEHOLDER STRATEGIES (Not yet implemented)
            'S09_statistical_arbitrage': {
                'class': None,
                'name': 'Statistical Arbitrage',
                'category': 'mean_reversion',
                'priority': 'low',
                'status': 'not_implemented',
                'params': {},
                'description': 'Complex statistical arbitrage model'
            },
            
            'S12_multi_factor': {
                'class': None,
                'name': 'Multi-Factor Model',
                'category': 'factor_based',
                'priority': 'medium',
                'status': 'not_implemented', 
                'params': {},
                'description': 'Multiple factor combination model'
            },
            
            'S15_cointegration_pairs': {
                'class': None,
                'name': 'Cointegration Pairs',
                'category': 'pairs_trading',
                'priority': 'medium',
                'status': 'not_implemented',
                'params': {},
                'description': 'Pairs trading using cointegration'
            },
            
            'S19_volatility_surface': {
                'class': None,
                'name': 'Volatility Surface',
                'category': 'volatility',
                'priority': 'low',
                'status': 'not_implemented',
                'params': {},
                'description': 'Options volatility surface arbitrage'
            },
            
            'S22_ma_arbitrage': {
                'class': None,
                'name': 'M&A Arbitrage',
                'category': 'event_driven',
                'priority': 'low',
                'status': 'not_implemented',
                'params': {},
                'description': 'Merger arbitrage opportunities'
            },
            
            'S24_sentiment_analysis': {
                'class': None,
                'name': 'Sentiment Analysis',
                'category': 'alternative_data',
                'priority': 'low',
                'status': 'not_implemented',
                'params': {},
                'description': 'News/social media sentiment signals'
            },
            
            'S27_random_forest': {
                'class': None,
                'name': 'Random Forest Signals',
                'category': 'machine_learning',
                'priority': 'low',
                'status': 'not_implemented',
                'params': {},
                'description': 'ML-based signal generation'
            },
            
            'S28_deep_learning': {
                'class': None,
                'name': 'Deep Learning Alpha',
                'category': 'machine_learning',
                'priority': 'future',
                'status': 'not_implemented',
                'params': {},
                'description': 'Neural network alpha discovery'
            }
        }
    
    def get_strategies_by_category(self, category):
        """Get all strategies in a specific category"""
        return {k: v for k, v in self.strategies.items() 
                if v['category'] == category}
    
    def get_strategies_by_priority(self, priority):
        """Get all strategies with specific priority"""
        return {k: v for k, v in self.strategies.items() 
                if v['priority'] == priority}
    
    def get_implemented_strategies(self):
        """Get only implemented strategies"""
        return {k: v for k, v in self.strategies.items() 
                if v['status'] == 'implemented'}
    
    def get_strategy(self, strategy_id):
        """Get specific strategy by ID"""
        return self.strategies.get(strategy_id)
    
    def create_strategy_instance(self, strategy_id, custom_params=None):
        """Create instance of a strategy with optional custom parameters"""
        strategy_info = self.strategies.get(strategy_id)
        
        if not strategy_info:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        if strategy_info['status'] != 'implemented':
            raise ValueError(f"Strategy {strategy_id} not yet implemented")
        
        strategy_class = strategy_info['class']
        params = strategy_info['params'].copy()
        
        # Override with custom parameters if provided
        if custom_params:
            params.update(custom_params)
        
        return strategy_class(**params)
    
    def list_strategies(self, include_not_implemented=False):
        """List all strategies with their details"""
        strategies_list = []
        
        for strategy_id, info in self.strategies.items():
            if not include_not_implemented and info['status'] != 'implemented':
                continue
                
            strategies_list.append({
                'id': strategy_id,
                'name': info['name'],
                'category': info['category'],
                'priority': info['priority'],
                'status': info['status'],
                'description': info['description']
            })
        
        return strategies_list
    
    def get_strategy_stats(self):
        """Get statistics about strategy implementation"""
        total = len(self.strategies)
        implemented = len([s for s in self.strategies.values() if s['status'] == 'implemented'])
        
        by_category = {}
        by_priority = {}
        
        for strategy in self.strategies.values():
            # Count by category
            cat = strategy['category']
            if cat not in by_category:
                by_category[cat] = {'total': 0, 'implemented': 0}
            by_category[cat]['total'] += 1
            if strategy['status'] == 'implemented':
                by_category[cat]['implemented'] += 1
            
            # Count by priority
            pri = strategy['priority']
            if pri not in by_priority:
                by_priority[pri] = {'total': 0, 'implemented': 0}
            by_priority[pri]['total'] += 1
            if strategy['status'] == 'implemented':
                by_priority[pri]['implemented'] += 1
        
        return {
            'total_strategies': total,
            'implemented_strategies': implemented,
            'implementation_rate': implemented / total,
            'by_category': by_category,
            'by_priority': by_priority
        }

if __name__ == "__main__":
    # Demo usage
    registry = StrategyRegistry()
    
    print("=" * 60)
    print("STRATEGY REGISTRY - IMPLEMENTATION STATUS")
    print("=" * 60)
    
    stats = registry.get_strategy_stats()
    print(f"Total Strategies: {stats['total_strategies']}")
    print(f"Implemented: {stats['implemented_strategies']}")
    print(f"Implementation Rate: {stats['implementation_rate']:.1%}")
    
    print(f"\nBy Category:")
    for cat, counts in stats['by_category'].items():
        print(f"  {cat}: {counts['implemented']}/{counts['total']}")
    
    print(f"\nBy Priority:")
    for pri, counts in stats['by_priority'].items():
        print(f"  {pri}: {counts['implemented']}/{counts['total']}")
    
    print(f"\nImplemented Strategies:")
    implemented = registry.list_strategies(include_not_implemented=False)
    for strategy in implemented:
        print(f"  {strategy['id']}: {strategy['name']} ({strategy['category']})")
    
    # Example: Create strategy instance
    print(f"\nExample - Creating Golden Cross strategy:")
    golden_cross = registry.create_strategy_instance('S02_golden_cross')
    print(f"Strategy: {golden_cross.name}")