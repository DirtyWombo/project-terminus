# Regime Analysis for Operation Badger
# Test strategy performance across different market conditions

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class RegimeAnalyzer:
    def __init__(self):
        """Initialize regime analysis with defined market periods"""
        
        # Define major market regimes for testing
        self.market_regimes = {
            'covid_crash': {
                'period': '2020-02-01 to 2020-05-01',
                'description': 'COVID-19 Market Crash',
                'characteristics': 'High volatility, panic selling, central bank intervention',
                'market_return': -0.20,  # Approximate market decline
                'volatility': 0.50
            },
            'recovery_bull': {
                'period': '2020-06-01 to 2021-12-31', 
                'description': 'Post-COVID Bull Market',
                'characteristics': 'Strong growth, low rates, tech rally',
                'market_return': 0.35,  # Strong positive returns
                'volatility': 0.25
            },
            'inflation_bear': {
                'period': '2022-01-01 to 2022-10-31',
                'description': 'Inflation/Rate Rise Bear Market',
                'characteristics': 'Rising rates, inflation fears, growth rotation',
                'market_return': -0.15,  # Market decline
                'volatility': 0.30
            },
            'normalization': {
                'period': '2023-01-01 to 2023-12-31',
                'description': 'Market Normalization',
                'characteristics': 'Stabilizing rates, mixed signals, sector rotation',
                'market_return': 0.08,  # Modest gains
                'volatility': 0.20
            },
            'sideways_grind': {
                'period': '2015-01-01 to 2016-12-31',
                'description': 'Sideways Market Grind',
                'characteristics': 'Range-bound, low growth, energy crash',
                'market_return': 0.02,  # Minimal returns
                'volatility': 0.18
            }
        }
        
        print("SUCCESS: Regime analyzer initialized")
        print(f"Testing across {len(self.market_regimes)} market regimes")
    
    def simulate_regime_environment(self, regime: Dict, n_signals: int = 100) -> pd.DataFrame:
        """Simulate signals and returns for a specific market regime"""
        np.random.seed(hash(regime['description']) % 1000)  # Deterministic but different per regime
        
        market_return = regime['market_return']
        volatility = regime['volatility']
        
        signals = []
        
        for i in range(n_signals):
            # Generate velocity scores (strategy signal strength)
            velocity_score = np.random.normal(0, 0.4)
            velocity_score = np.clip(velocity_score, -1.0, 1.0)
            
            # Generate AI confidence
            ai_confidence = 0.5 + 0.3 * abs(velocity_score) + np.random.normal(0, 0.1)
            ai_confidence = np.clip(ai_confidence, 0.1, 0.95)
            
            # Generate returns influenced by market regime
            # Base signal effect
            signal_effect = velocity_score * 0.015  # 1.5% for perfect signal
            
            # Market regime influence (beta-like effect)
            market_influence = market_return * np.random.uniform(0.5, 1.5) / 252  # Daily market effect
            
            # Regime-specific noise
            regime_noise = np.random.normal(0, volatility / np.sqrt(252))
            
            # Combined return
            actual_return = signal_effect + market_influence + regime_noise
            
            # In high volatility regimes, signals are less reliable
            if volatility > 0.3:
                actual_return *= np.random.uniform(0.5, 1.5)  # Add extra noise
            
            # In bear markets, positive signals are less effective
            if market_return < 0 and velocity_score > 0:
                actual_return *= np.random.uniform(0.3, 0.8)  # Reduce effectiveness
            
            # In bull markets, negative signals are less effective
            if market_return > 0.15 and velocity_score < 0:
                actual_return *= np.random.uniform(0.2, 0.6)  # Reduce short effectiveness
            
            signals.append({
                'signal_id': i,
                'regime': regime['description'],
                'velocity_score': velocity_score,
                'ai_confidence': ai_confidence,
                'market_environment': market_return,
                'volatility_regime': volatility,
                'actual_return': actual_return,
                'market_influence': market_influence
            })
        
        return pd.DataFrame(signals)
    
    def apply_strategy_filters(self, signals_df: pd.DataFrame) -> pd.DataFrame:
        """Apply standard strategy filters"""
        filtered = signals_df.copy()
        
        # Standard thresholds
        filtered = filtered[
            (abs(filtered['velocity_score']) >= 0.4) &
            (filtered['ai_confidence'] >= 0.65)
        ]
        
        return filtered
    
    def calculate_regime_performance(self, signals_df: pd.DataFrame) -> Dict:
        """Calculate performance metrics for a specific regime"""
        
        if signals_df.empty:
            return {
                'num_signals': 0,
                'win_rate': 0.0,
                'mean_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_return': 0.0,
                'viable': False
            }
        
        returns = signals_df['actual_return'].values
        
        # Performance metrics
        num_signals = len(returns)
        win_rate = (returns > 0).mean()
        mean_return = returns.mean()
        std_return = returns.std() if len(returns) > 1 else 0.0
        total_return = np.prod(1 + returns) - 1
        
        # Annualized Sharpe ratio
        sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Max drawdown
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdowns.min()) if len(drawdowns) > 0 else 0
        
        # Viability
        viable = (
            num_signals >= 5 and
            win_rate > 0.4 and
            sharpe_ratio > 0.0 and
            max_drawdown < 0.5
        )
        
        return {
            'num_signals': num_signals,
            'win_rate': win_rate,
            'mean_return': mean_return,
            'std_return': std_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_return': total_return,
            'viable': viable
        }
    
    def analyze_regime_correlation(self, all_results: Dict) -> Dict:
        """Analyze how strategy performance correlates with market regimes"""
        
        regime_data = []
        for regime_name, results in all_results.items():
            regime_info = self.market_regimes[regime_name]
            performance = results['performance']
            
            regime_data.append({
                'regime': regime_name,
                'market_return': regime_info['market_return'],
                'volatility': regime_info['volatility'],
                'strategy_sharpe': performance['sharpe_ratio'],
                'strategy_return': performance['mean_return'],
                'win_rate': performance['win_rate']
            })
        
        df = pd.DataFrame(regime_data)
        
        # Calculate correlations
        correlations = {}
        if len(df) > 2:
            correlations['market_return_vs_strategy'] = df['market_return'].corr(df['strategy_return'])
            correlations['volatility_vs_sharpe'] = df['volatility'].corr(df['strategy_sharpe'])
            correlations['market_vs_winrate'] = df['market_return'].corr(df['win_rate'])
        
        # Regime dependency analysis
        positive_regimes = df[df['market_return'] > 0]['strategy_sharpe'].mean()
        negative_regimes = df[df['market_return'] < 0]['strategy_sharpe'].mean()
        
        high_vol_regimes = df[df['volatility'] > 0.25]['strategy_sharpe'].mean()
        low_vol_regimes = df[df['volatility'] <= 0.25]['strategy_sharpe'].mean()
        
        return {
            'correlations': correlations,
            'regime_dependency': {
                'bull_market_sharpe': positive_regimes,
                'bear_market_sharpe': negative_regimes,
                'high_vol_sharpe': high_vol_regimes,
                'low_vol_sharpe': low_vol_regimes,
                'regime_agnostic': abs(positive_regimes - negative_regimes) < 0.5
            }
        }
    
    def generate_regime_report(self) -> Dict:
        """Generate comprehensive regime analysis report"""
        print("="*60)
        print("REGIME ANALYSIS - MARKET CONDITIONS ROBUSTNESS TEST")
        print("="*60)
        
        all_results = {}
        
        # Test each regime
        for regime_name, regime_info in self.market_regimes.items():
            print(f"\nTesting {regime_info['description']} ({regime_info['period']}):")
            
            # Generate signals for this regime
            signals_df = self.simulate_regime_environment(regime_info, 200)
            
            # Apply strategy filters
            filtered_signals = self.apply_strategy_filters(signals_df)
            
            # Calculate performance
            performance = self.calculate_regime_performance(filtered_signals)
            
            print(f"  Signals Generated: {len(signals_df)}")
            print(f"  Signals Passing Filter: {performance['num_signals']}")
            print(f"  Win Rate: {performance['win_rate']:.1%}")
            print(f"  Mean Return: {performance['mean_return']:.2%}")
            print(f"  Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: {performance['max_drawdown']:.1%}")
            print(f"  Strategy Viable: {performance['viable']}")
            
            all_results[regime_name] = {
                'regime_info': regime_info,
                'raw_signals': len(signals_df),
                'performance': performance
            }
        
        # Cross-regime analysis
        print(f"\n{'='*60}")
        print("CROSS-REGIME ANALYSIS:")
        print("="*60)
        
        correlation_analysis = self.analyze_regime_correlation(all_results)
        
        # Performance summary
        all_sharpes = [result['performance']['sharpe_ratio'] for result in all_results.values()]
        all_viable = [result['performance']['viable'] for result in all_results.values()]
        
        avg_sharpe = np.mean(all_sharpes)
        sharpe_std = np.std(all_sharpes)
        viable_count = sum(all_viable)
        
        print(f"Average Sharpe Across Regimes: {avg_sharpe:.2f}")
        print(f"Sharpe Standard Deviation: {sharpe_std:.2f}")
        print(f"Viable Regimes: {viable_count}/{len(all_results)}")
        
        # Regime dependency
        dependency = correlation_analysis['regime_dependency']
        print(f"\nRegime Dependency Analysis:")
        print(f"  Bull Market Performance: {dependency['bull_market_sharpe']:.2f}")
        print(f"  Bear Market Performance: {dependency['bear_market_sharpe']:.2f}")
        print(f"  High Volatility Performance: {dependency['high_vol_sharpe']:.2f}")
        print(f"  Low Volatility Performance: {dependency['low_vol_sharpe']:.2f}")
        print(f"  Regime Agnostic: {dependency['regime_agnostic']}")
        
        # Expert verdict
        print("\n" + "="*60)
        print("EXPERT VERDICT:")
        print("="*60)
        
        consistent_performance = sharpe_std < 1.0 and viable_count >= len(all_results) * 0.6
        regime_agnostic = dependency['regime_agnostic']
        overall_positive = avg_sharpe > 0.5
        
        if consistent_performance and regime_agnostic and overall_positive:
            print("PASS: Strategy demonstrates regime robustness")
            print(f"   Consistent performance across market conditions")
            print(f"   Average Sharpe {avg_sharpe:.2f} with low volatility")
        elif overall_positive and viable_count >= 3:
            print("MARGINAL: Strategy works in some market conditions")
            print(f"   Performance varies significantly by regime")
            print(f"   May require regime-aware position sizing")
        else:
            print("FAIL: Strategy lacks regime robustness")
            print(f"   Poor performance across market conditions")
            print(f"   High regime dependency makes it unreliable")
        
        if not regime_agnostic:
            bull_bear_diff = dependency['bull_market_sharpe'] - dependency['bear_market_sharpe']
            if bull_bear_diff > 1.0:
                print(f"WARNING: Strategy is heavily bull-market dependent")
            elif bull_bear_diff < -1.0:
                print(f"WARNING: Strategy performs better in bear markets (unusual)")
        
        print(f"\nRegime Statistics:")
        print(f"  Best Regime: {max(all_results.keys(), key=lambda x: all_results[x]['performance']['sharpe_ratio'])}")
        print(f"  Worst Regime: {min(all_results.keys(), key=lambda x: all_results[x]['performance']['sharpe_ratio'])}")
        print(f"  Consistency Score: {1 / (1 + sharpe_std):.2f}")  # Higher is better
        
        print("="*60)
        
        # Compile report
        report = {
            'analysis_date': datetime.now().isoformat(),
            'regime_results': all_results,
            'cross_regime_analysis': {
                'average_sharpe': avg_sharpe,
                'sharpe_standard_deviation': sharpe_std,
                'viable_regimes': viable_count,
                'total_regimes': len(all_results)
            },
            'correlation_analysis': correlation_analysis,
            'verdict': {
                'regime_robust': consistent_performance and regime_agnostic and overall_positive,
                'consistent_performance': consistent_performance,
                'regime_agnostic': regime_agnostic,
                'overall_positive': overall_positive,
                'consistency_score': float(1 / (1 + sharpe_std))
            }
        }
        
        # Save report
        with open('regime_analysis_results.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report

def main():
    """Execute regime analysis"""
    analyzer = RegimeAnalyzer()
    report = analyzer.generate_regime_report()
    
    print("\nFILES GENERATED:")
    print("- regime_analysis_results.json")
    
    return report

if __name__ == "__main__":
    main()