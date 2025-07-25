# Parameter Sensitivity Analysis for Operation Badger
# Test strategy robustness across parameter variations

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Tuple
import itertools

class ParameterSensitivityAnalyzer:
    def __init__(self):
        """Initialize parameter sensitivity testing"""
        
        # Current strategy parameters from .env
        self.base_parameters = {
            'MIN_VELOCITY_SCORE': 0.4,
            'MIN_AI_CONFIDENCE': 0.65,
            'POSITION_SIZE_PERCENT': 0.5,
            'MAX_CONCURRENT_POSITIONS': 5,
            'MIN_MARKET_CAP': 500_000_000,
            'MAX_MARKET_CAP': 50_000_000_000
        }
        
        # Parameter ranges for sensitivity testing
        self.parameter_ranges = {
            'MIN_VELOCITY_SCORE': [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            'MIN_AI_CONFIDENCE': [0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85],
            'POSITION_SIZE_PERCENT': [0.25, 0.5, 0.75, 1.0],
            'MAX_CONCURRENT_POSITIONS': [3, 5, 8, 10]
        }
        
        print("SUCCESS: Parameter sensitivity analyzer initialized")
        print(f"Base parameters: {self.base_parameters}")
    
    def generate_test_signals(self, n_signals: int = 500) -> pd.DataFrame:
        """Generate synthetic signals for parameter testing"""
        np.random.seed(123)  # Different seed from TCA
        
        # Create realistic signal distribution
        signals = []
        for i in range(n_signals):
            # Generate velocity scores with realistic distribution
            velocity_score = np.random.normal(0, 0.4)  # Centered around 0
            velocity_score = np.clip(velocity_score, -1.0, 1.0)
            
            # Generate AI confidence (correlated with abs(velocity_score))
            base_confidence = 0.3 + 0.4 * abs(velocity_score)  # Higher confidence for stronger signals
            ai_confidence = base_confidence + np.random.normal(0, 0.1)
            ai_confidence = np.clip(ai_confidence, 0.1, 0.95)
            
            # Generate market cap (log-normal distribution)
            market_cap = np.random.lognormal(np.log(5e9), 1.5)  # ~$5B median
            market_cap = np.clip(market_cap, 100e6, 200e9)  # $100M to $200B
            
            # Generate actual return (correlated with velocity score + noise)
            signal_strength = velocity_score * ai_confidence  # Combined signal
            expected_return = signal_strength * 0.02  # 2% for perfect signal
            actual_return = expected_return + np.random.normal(0, 0.05)  # Add noise
            
            signals.append({
                'signal_id': i,
                'velocity_score': velocity_score,
                'ai_confidence': ai_confidence,
                'market_cap': market_cap,
                'expected_return': expected_return,
                'actual_return': actual_return,
                'timestamp': datetime(2023, 1, 1).isoformat()
            })
        
        return pd.DataFrame(signals)
    
    def apply_parameter_filter(self, signals_df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Apply parameter filters to signals"""
        filtered = signals_df.copy()
        
        # Apply velocity score threshold
        filtered = filtered[
            abs(filtered['velocity_score']) >= params['MIN_VELOCITY_SCORE']
        ]
        
        # Apply confidence threshold  
        filtered = filtered[
            filtered['ai_confidence'] >= params['MIN_AI_CONFIDENCE']
        ]
        
        # Apply market cap filters
        filtered = filtered[
            (filtered['market_cap'] >= params['MIN_MARKET_CAP']) &
            (filtered['market_cap'] <= params['MAX_MARKET_CAP'])
        ]
        
        # Simulate concurrent position limits (simple approximation)
        max_positions = params['MAX_CONCURRENT_POSITIONS']
        if len(filtered) > max_positions * 20:  # Assume 20 trades per position over time
            # Keep only the highest confidence signals
            filtered = filtered.nlargest(max_positions * 20, 'ai_confidence')
        
        return filtered
    
    def calculate_strategy_performance(self, signals_df: pd.DataFrame, params: Dict) -> Dict:
        """Calculate performance metrics for given parameters"""
        
        if signals_df.empty:
            return {
                'num_signals': 0,
                'win_rate': 0.0,
                'mean_return': 0.0,
                'sharpe_ratio': 0.0,
                'information_ratio': 0.0,
                'max_drawdown': 0.0,
                'viable': False
            }
        
        returns = signals_df['actual_return'].values
        
        # Basic performance metrics
        num_signals = len(returns)
        win_rate = (returns > 0).mean()
        mean_return = returns.mean()
        std_return = returns.std() if len(returns) > 1 else 0.0
        
        # Risk-adjusted metrics
        sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Information ratio (excess return per unit of tracking error)
        # Simplified: using standard deviation as tracking error
        information_ratio = mean_return / std_return if std_return > 0 else 0
        
        # Simple max drawdown calculation
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdowns.min()) if len(drawdowns) > 0 else 0
        
        # Viability check
        viable = (
            num_signals >= 20 and  # Minimum statistical sample
            win_rate > 0.45 and    # Reasonable win rate
            sharpe_ratio > 0.5 and # Positive risk-adjusted return
            mean_return > 0        # Positive expected return
        )
        
        return {
            'num_signals': num_signals,
            'win_rate': win_rate,
            'mean_return': mean_return,
            'std_return': std_return,
            'sharpe_ratio': sharpe_ratio,
            'information_ratio': information_ratio,
            'max_drawdown': max_drawdown,
            'viable': viable
        }
    
    def run_single_parameter_sweep(self, param_name: str, signals_df: pd.DataFrame) -> Dict:
        """Test sensitivity to a single parameter"""
        results = {}
        
        for param_value in self.parameter_ranges[param_name]:
            # Create test parameters
            test_params = self.base_parameters.copy()
            test_params[param_name] = param_value
            
            # Apply filters
            filtered_signals = self.apply_parameter_filter(signals_df, test_params)
            
            # Calculate performance
            performance = self.calculate_strategy_performance(filtered_signals, test_params)
            
            results[param_value] = performance
        
        return results
    
    def run_multi_parameter_grid_search(self, signals_df: pd.DataFrame, 
                                       max_combinations: int = 50) -> List[Dict]:
        """Test combinations of parameters (limited grid search)"""
        
        # Create smaller ranges for grid search to avoid explosion
        grid_ranges = {
            'MIN_VELOCITY_SCORE': [0.3, 0.4, 0.5],
            'MIN_AI_CONFIDENCE': [0.6, 0.65, 0.75],
            'POSITION_SIZE_PERCENT': [0.5, 1.0],
            'MAX_CONCURRENT_POSITIONS': [5, 8]
        }
        
        # Generate all combinations
        param_names = list(grid_ranges.keys())
        param_values = list(grid_ranges.values())
        combinations = list(itertools.product(*param_values))
        
        # Limit combinations if too many
        if len(combinations) > max_combinations:
            # Sample random combinations
            np.random.seed(456)
            selected_indices = np.random.choice(len(combinations), max_combinations, replace=False)
            combinations = [combinations[i] for i in selected_indices]
        
        results = []
        for combo in combinations:
            # Create parameter set
            test_params = self.base_parameters.copy()
            for param_name, param_value in zip(param_names, combo):
                test_params[param_name] = param_value
            
            # Apply filters and calculate performance
            filtered_signals = self.apply_parameter_filter(signals_df, test_params)
            performance = self.calculate_strategy_performance(filtered_signals, test_params)
            
            # Store result
            result = {
                'parameters': test_params.copy(),
                'performance': performance
            }
            results.append(result)
        
        # Sort by Sharpe ratio
        results.sort(key=lambda x: x['performance']['sharpe_ratio'], reverse=True)
        
        return results
    
    def analyze_parameter_stability(self, single_param_results: Dict) -> Dict:
        """Analyze how stable performance is across parameter changes"""
        analysis = {}
        
        for param_name, param_results in single_param_results.items():
            sharpe_ratios = [result['sharpe_ratio'] for result in param_results.values()]
            win_rates = [result['win_rate'] for result in param_results.values()]
            num_signals = [result['num_signals'] for result in param_results.values()]
            
            # Calculate stability metrics
            sharpe_std = np.std(sharpe_ratios)
            sharpe_range = max(sharpe_ratios) - min(sharpe_ratios)
            
            # Count viable parameter settings
            viable_count = sum(1 for result in param_results.values() if result['viable'])
            total_count = len(param_results)
            
            analysis[param_name] = {
                'sharpe_std': sharpe_std,
                'sharpe_range': sharpe_range,
                'viable_ratio': viable_count / total_count,
                'max_sharpe': max(sharpe_ratios),
                'min_sharpe': min(sharpe_ratios),
                'stable': sharpe_std < 0.5 and viable_count >= total_count * 0.5
            }
        
        return analysis
    
    def generate_sensitivity_report(self) -> Dict:
        """Generate comprehensive parameter sensitivity report"""
        print("="*60)
        print("PARAMETER SENSITIVITY ANALYSIS - ROBUSTNESS TEST")
        print("="*60)
        
        # Generate test signals
        signals_df = self.generate_test_signals(500)
        print(f"Generated {len(signals_df)} test signals for analysis")
        
        # Test baseline performance
        baseline_filtered = self.apply_parameter_filter(signals_df, self.base_parameters)
        baseline_performance = self.calculate_strategy_performance(baseline_filtered, self.base_parameters)
        
        print(f"\nBASELINE PERFORMANCE (Current Parameters):")
        print(f"  Signals Passed Filter: {baseline_performance['num_signals']}")
        print(f"  Win Rate: {baseline_performance['win_rate']:.1%}")
        print(f"  Sharpe Ratio: {baseline_performance['sharpe_ratio']:.2f}")
        print(f"  Information Ratio: {baseline_performance['information_ratio']:.2f}")
        print(f"  Strategy Viable: {baseline_performance['viable']}")
        
        # Single parameter sweeps
        print(f"\nSINGLE PARAMETER SENSITIVITY:")
        single_param_results = {}
        
        for param_name in self.parameter_ranges.keys():
            param_results = self.run_single_parameter_sweep(param_name, signals_df)
            single_param_results[param_name] = param_results
            
            # Find best value for this parameter
            best_value = max(param_results.keys(), 
                           key=lambda x: param_results[x]['sharpe_ratio'])
            best_sharpe = param_results[best_value]['sharpe_ratio']
            
            print(f"  {param_name}:")
            print(f"    Current: {self.base_parameters[param_name]} "
                  f"(Sharpe: {param_results.get(self.base_parameters[param_name], {}).get('sharpe_ratio', 'N/A'):.2f})")
            print(f"    Best: {best_value} (Sharpe: {best_sharpe:.2f})")
        
        # Parameter stability analysis
        stability_analysis = self.analyze_parameter_stability(single_param_results)
        
        print(f"\nPARAMETER STABILITY ANALYSIS:")
        for param_name, analysis in stability_analysis.items():
            stability_status = "STABLE" if analysis['stable'] else "UNSTABLE"
            print(f"  {param_name}: {stability_status}")
            print(f"    Sharpe Range: {analysis['sharpe_range']:.2f}")
            print(f"    Viable Settings: {analysis['viable_ratio']:.1%}")
        
        # Multi-parameter optimization
        print(f"\nMULTI-PARAMETER OPTIMIZATION:")
        grid_results = self.run_multi_parameter_grid_search(signals_df)
        
        # Show top 5 parameter combinations
        print("  Top 5 Parameter Combinations:")
        for i, result in enumerate(grid_results[:5]):
            params = result['parameters']
            perf = result['performance']
            print(f"    #{i+1}: Sharpe {perf['sharpe_ratio']:.2f}, "
                  f"Win Rate {perf['win_rate']:.1%}, "
                  f"Signals {perf['num_signals']}")
            print(f"        Velocity: {params['MIN_VELOCITY_SCORE']}, "
                  f"Confidence: {params['MIN_AI_CONFIDENCE']}")
        
        # Expert verdict
        print("\n" + "="*60)
        print("EXPERT VERDICT:")
        print("="*60)
        
        overall_stable = sum(1 for analysis in stability_analysis.values() 
                           if analysis['stable']) >= len(stability_analysis) * 0.7
        
        best_combo_sharpe = grid_results[0]['performance']['sharpe_ratio'] if grid_results else 0
        baseline_sharpe = baseline_performance['sharpe_ratio']
        
        if overall_stable and best_combo_sharpe > 1.0:
            print("PASS: Strategy shows parameter robustness")
            print(f"   Most parameters are stable across ranges")
            print(f"   Best combination achieves Sharpe {best_combo_sharpe:.2f}")
        elif best_combo_sharpe > baseline_sharpe * 1.5:
            print("MARGINAL: Strategy can be improved with parameter tuning")
            print(f"   Current parameters suboptimal")
            print(f"   Optimization potential exists")
        else:
            print("FAIL: Strategy is parameter-sensitive and brittle")
            print(f"   Performance collapses with parameter changes")
            print(f"   Likely overfit to specific settings")
        
        stability_count = sum(1 for analysis in stability_analysis.values() if analysis['stable'])
        print(f"\nStable parameters: {stability_count}/{len(stability_analysis)}")
        print(f"Baseline vs Best Sharpe: {baseline_sharpe:.2f} vs {best_combo_sharpe:.2f}")
        
        print("="*60)
        
        # Compile report
        report = {
            'analysis_date': datetime.now().isoformat(),
            'baseline_parameters': self.base_parameters,
            'baseline_performance': baseline_performance,
            'single_parameter_results': single_param_results,
            'stability_analysis': stability_analysis,
            'grid_search_results': grid_results[:10],  # Top 10 only
            'verdict': {
                'overall_stable': overall_stable,
                'parameter_robust': best_combo_sharpe > 1.0 and overall_stable,
                'optimization_potential': best_combo_sharpe > baseline_sharpe * 1.2,
                'stable_parameter_count': stability_count,
                'baseline_sharpe': baseline_sharpe,
                'best_sharpe': best_combo_sharpe
            }
        }
        
        # Save report
        with open('parameter_sensitivity_results.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report

def main():
    """Execute parameter sensitivity analysis"""
    analyzer = ParameterSensitivityAnalyzer()
    report = analyzer.generate_sensitivity_report()
    
    print("\nFILES GENERATED:")
    print("- parameter_sensitivity_results.json")
    
    return report

if __name__ == "__main__":
    main()