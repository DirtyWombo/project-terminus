"""
Risk Analytics Module
====================

Comprehensive risk management analytics including:
1. Value at Risk (VaR) calculations
2. Expected Shortfall (ES/CVaR)
3. Risk attribution and decomposition
4. Stress testing scenarios
5. Risk monitoring and validation
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from scipy import stats
from datetime import datetime, timedelta
import warnings

logging.basicConfig(level=logging.INFO)

class RiskAnalytics:
    """
    Comprehensive risk analytics engine for portfolio risk management.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize risk analytics with configuration."""
        self.config = config or self._get_default_config()
        
    def _get_default_config(self) -> Dict:
        """Default risk analytics configuration."""
        return {
            # VaR parameters
            "var_confidence_levels": [0.95, 0.99],
            "var_holding_period": 1,  # 1 day
            "var_lookback_days": 250,  # 1 year of data
            
            # Risk limits
            "max_portfolio_var_95": 0.05,  # 5% max daily VaR
            "max_portfolio_var_99": 0.08,  # 8% max daily VaR
            "max_component_var": 0.02,     # 2% max per component
            
            # Stress testing
            "stress_scenarios": {
                "market_crash": -0.20,      # -20% market move
                "flash_crash": -0.10,       # -10% instant move
                "volatility_spike": 3.0,    # 3x normal volatility
                "liquidity_crisis": 0.50    # 50% wider spreads
            },
            
            # Model validation
            "backtest_confidence": 0.95,
            "exception_threshold": 0.05,    # 5% acceptable exception rate
            "min_observations": 100         # Minimum data points for VaR
        }
    
    def calculate_var(
        self, 
        returns: np.ndarray, 
        confidence_level: float = 0.95,
        method: str = "historical"
    ) -> Dict:
        """
        Calculate Value at Risk using multiple methodologies.
        
        Args:
            returns: Array of portfolio returns
            confidence_level: Confidence level (0.95 or 0.99)
            method: VaR method ("historical", "parametric", "monte_carlo")
            
        Returns:
            Dict containing VaR calculations and metadata
        """
        if len(returns) < self.config["min_observations"]:
            return {
                "var": 0.0,
                "method": method,
                "confidence_level": confidence_level,
                "error": f"Insufficient data: {len(returns)} < {self.config['min_observations']}"
            }
        
        # Remove NaN values and outliers
        clean_returns = self._clean_returns(returns)
        
        if method == "historical":
            var_value = self._historical_var(clean_returns, confidence_level)
        elif method == "parametric":
            var_value = self._parametric_var(clean_returns, confidence_level)
        elif method == "monte_carlo":
            var_value = self._monte_carlo_var(clean_returns, confidence_level)
        else:
            raise ValueError(f"Unknown VaR method: {method}")
        
        # Calculate Expected Shortfall (Conditional VaR)
        expected_shortfall = self._calculate_expected_shortfall(clean_returns, confidence_level)
        
        return {
            "var": var_value,
            "expected_shortfall": expected_shortfall,
            "method": method,
            "confidence_level": confidence_level,
            "observations": len(clean_returns),
            "mean_return": np.mean(clean_returns),
            "volatility": np.std(clean_returns),
            "skewness": stats.skew(clean_returns),
            "kurtosis": stats.kurtosis(clean_returns),
            "var_percentage": abs(var_value) * 100,
            "es_percentage": abs(expected_shortfall) * 100
        }
    
    def _historical_var(self, returns: np.ndarray, confidence_level: float) -> float:
        """Calculate Historical VaR using empirical quantiles."""
        return np.percentile(returns, (1 - confidence_level) * 100)
    
    def _parametric_var(self, returns: np.ndarray, confidence_level: float) -> float:
        """Calculate Parametric VaR assuming normal distribution."""
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Z-score for confidence level
        z_score = stats.norm.ppf(1 - confidence_level)
        
        # VaR calculation
        var_value = mean_return + z_score * std_return
        
        return var_value
    
    def _monte_carlo_var(
        self, 
        returns: np.ndarray, 
        confidence_level: float, 
        simulations: int = 10000
    ) -> float:
        """Calculate Monte Carlo VaR using simulated returns."""
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Generate random returns
        np.random.seed(42)  # For reproducible results
        simulated_returns = np.random.normal(mean_return, std_return, simulations)
        
        # Calculate VaR from simulated distribution
        return np.percentile(simulated_returns, (1 - confidence_level) * 100)
    
    def _calculate_expected_shortfall(self, returns: np.ndarray, confidence_level: float) -> float:
        """Calculate Expected Shortfall (Conditional VaR)."""
        var_threshold = self._historical_var(returns, confidence_level)
        tail_losses = returns[returns <= var_threshold]
        
        if len(tail_losses) == 0:
            return var_threshold
        
        return np.mean(tail_losses)
    
    def _clean_returns(self, returns: np.ndarray) -> np.ndarray:
        """Clean returns data by removing NaN and extreme outliers."""
        # Remove NaN values
        clean_returns = returns[~np.isnan(returns)]
        
        # Remove extreme outliers (beyond 5 standard deviations)
        mean_return = np.mean(clean_returns)
        std_return = np.std(clean_returns)
        outlier_threshold = 5 * std_return
        
        clean_returns = clean_returns[
            np.abs(clean_returns - mean_return) <= outlier_threshold
        ]
        
        return clean_returns
    
    def calculate_portfolio_var(
        self, 
        positions: Dict[str, float], 
        asset_returns: Dict[str, np.ndarray],
        confidence_level: float = 0.95
    ) -> Dict:
        """
        Calculate portfolio VaR considering correlations between assets.
        
        Args:
            positions: Dict of {asset: position_weight}
            asset_returns: Dict of {asset: returns_array}
            confidence_level: VaR confidence level
            
        Returns:
            Dict with portfolio VaR and component contributions
        """
        # Align all return series to common dates
        aligned_returns = self._align_return_series(asset_returns)
        
        if not aligned_returns:
            return {"error": "No common return data available"}
        
        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(positions, aligned_returns)
        
        # Calculate portfolio VaR
        portfolio_var = self.calculate_var(portfolio_returns, confidence_level, method="historical")
        
        # Calculate component VaR contributions
        component_vars = self._calculate_component_var(
            positions, aligned_returns, confidence_level
        )
        
        # Calculate marginal VaR
        marginal_vars = self._calculate_marginal_var(
            positions, aligned_returns, confidence_level
        )
        
        return {
            "portfolio_var": portfolio_var,
            "component_vars": component_vars,
            "marginal_vars": marginal_vars,
            "diversification_benefit": sum(component_vars.values()) - abs(portfolio_var["var"]),
            "portfolio_returns_used": len(portfolio_returns)
        }
    
    def _align_return_series(self, asset_returns: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Align return series to common length."""
        if not asset_returns:
            return {}
        
        # Find minimum length
        min_length = min(len(returns) for returns in asset_returns.values())
        
        # Truncate all series to minimum length
        aligned = {
            asset: returns[-min_length:] 
            for asset, returns in asset_returns.items()
        }
        
        return aligned
    
    def _calculate_portfolio_returns(
        self, 
        positions: Dict[str, float], 
        asset_returns: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """Calculate portfolio returns from position weights and asset returns."""
        portfolio_returns = np.zeros(len(next(iter(asset_returns.values()))))
        
        for asset, weight in positions.items():
            if asset in asset_returns:
                portfolio_returns += weight * asset_returns[asset]
        
        return portfolio_returns
    
    def _calculate_component_var(
        self, 
        positions: Dict[str, float], 
        asset_returns: Dict[str, np.ndarray], 
        confidence_level: float
    ) -> Dict[str, float]:
        """Calculate component VaR for each asset."""
        component_vars = {}
        
        for asset in positions.keys():
            if asset in asset_returns:
                # Calculate standalone VaR for this asset
                asset_var = self.calculate_var(asset_returns[asset], confidence_level)
                
                # Scale by position weight
                component_vars[asset] = abs(asset_var["var"]) * abs(positions[asset])
        
        return component_vars
    
    def _calculate_marginal_var(
        self, 
        positions: Dict[str, float], 
        asset_returns: Dict[str, np.ndarray], 
        confidence_level: float
    ) -> Dict[str, float]:
        """Calculate marginal VaR (change in portfolio VaR for small position change)."""
        base_portfolio_returns = self._calculate_portfolio_returns(positions, asset_returns)
        base_var = self.calculate_var(base_portfolio_returns, confidence_level)["var"]
        
        marginal_vars = {}
        delta = 0.01  # 1% position change
        
        for asset in positions.keys():
            if asset in asset_returns:
                # Create modified positions
                modified_positions = positions.copy()
                modified_positions[asset] += delta
                
                # Calculate new portfolio VaR
                modified_returns = self._calculate_portfolio_returns(modified_positions, asset_returns)
                modified_var = self.calculate_var(modified_returns, confidence_level)["var"]
                
                # Marginal VaR = change in VaR / change in position
                marginal_vars[asset] = (modified_var - base_var) / delta
        
        return marginal_vars
    
    def stress_test_portfolio(
        self, 
        positions: Dict[str, float], 
        asset_returns: Dict[str, np.ndarray]
    ) -> Dict:
        """
        Perform stress testing on portfolio under various scenarios.
        
        Args:
            positions: Current portfolio positions
            asset_returns: Historical return data
            
        Returns:
            Dict with stress test results
        """
        stress_results = {}
        
        for scenario_name, shock_magnitude in self.config["stress_scenarios"].items():
            scenario_results = {}
            
            if scenario_name == "market_crash":
                # Apply uniform shock to all assets
                shocked_returns = {
                    asset: returns + shock_magnitude 
                    for asset, returns in asset_returns.items()
                }
            elif scenario_name == "volatility_spike":
                # Multiply volatility by shock magnitude
                shocked_returns = {
                    asset: returns * shock_magnitude 
                    for asset, returns in asset_returns.items()
                }
            else:
                # Default: uniform shock
                shocked_returns = {
                    asset: returns + shock_magnitude 
                    for asset, returns in asset_returns.items()
                }
            
            # Calculate portfolio returns under stress
            stressed_portfolio_returns = self._calculate_portfolio_returns(
                positions, shocked_returns
            )
            
            # Calculate metrics under stress
            scenario_results = {
                "portfolio_return": np.sum(stressed_portfolio_returns[-1:]),  # Latest return
                "var_95": self.calculate_var(stressed_portfolio_returns, 0.95)["var"],
                "var_99": self.calculate_var(stressed_portfolio_returns, 0.99)["var"],
                "max_loss": np.min(stressed_portfolio_returns),
                "volatility": np.std(stressed_portfolio_returns)
            }
            
            stress_results[scenario_name] = scenario_results
        
        return stress_results
    
    def validate_var_model(
        self, 
        historical_returns: np.ndarray, 
        var_forecasts: np.ndarray, 
        confidence_level: float = 0.95
    ) -> Dict:
        """
        Validate VaR model accuracy using backtesting.
        
        Args:
            historical_returns: Actual returns
            var_forecasts: VaR forecasts for same periods
            confidence_level: VaR confidence level
            
        Returns:
            Dict with validation results
        """
        if len(historical_returns) != len(var_forecasts):
            return {"error": "Mismatched array lengths"}
        
        # Count VaR exceptions (actual loss > VaR prediction)
        exceptions = np.sum(historical_returns < var_forecasts)
        exception_rate = exceptions / len(historical_returns)
        
        # Expected exception rate
        expected_rate = 1 - confidence_level
        
        # Kupiec likelihood ratio test
        kupiec_stat = self._kupiec_test(exceptions, len(historical_returns), expected_rate)
        
        # Christoffersen independence test
        christoffersen_stat = self._christoffersen_test(
            historical_returns, var_forecasts, confidence_level
        )
        
        return {
            "total_observations": len(historical_returns),
            "exceptions": exceptions,
            "exception_rate": exception_rate,
            "expected_rate": expected_rate,
            "exception_ratio": exception_rate / expected_rate,
            "kupiec_statistic": kupiec_stat,
            "christoffersen_statistic": christoffersen_stat,
            "model_performance": self._assess_model_performance(exception_rate, expected_rate),
            "var_accuracy": 1 - abs(exception_rate - expected_rate)
        }
    
    def _kupiec_test(self, exceptions: int, observations: int, expected_rate: float) -> float:
        """Kupiec likelihood ratio test for VaR model validation."""
        if exceptions == 0 or exceptions == observations:
            return 0.0
        
        observed_rate = exceptions / observations
        
        # Likelihood ratio statistic
        lr_stat = -2 * (
            exceptions * np.log(expected_rate) + 
            (observations - exceptions) * np.log(1 - expected_rate) -
            exceptions * np.log(observed_rate) - 
            (observations - exceptions) * np.log(1 - observed_rate)
        )
        
        return lr_stat
    
    def _christoffersen_test(
        self, 
        returns: np.ndarray, 
        var_forecasts: np.ndarray, 
        confidence_level: float
    ) -> float:
        """Christoffersen independence test for VaR clustering."""
        # Create exception indicator series
        exceptions = (returns < var_forecasts).astype(int)
        
        # Count transitions
        n00 = np.sum((exceptions[:-1] == 0) & (exceptions[1:] == 0))
        n01 = np.sum((exceptions[:-1] == 0) & (exceptions[1:] == 1))
        n10 = np.sum((exceptions[:-1] == 1) & (exceptions[1:] == 0))
        n11 = np.sum((exceptions[:-1] == 1) & (exceptions[1:] == 1))
        
        # Avoid division by zero
        if n00 + n01 == 0 or n10 + n11 == 0:
            return 0.0
        
        # Calculate transition probabilities
        pi_01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0
        pi_11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0
        pi = (n01 + n11) / (n00 + n01 + n10 + n11)
        
        # Likelihood ratio statistic
        if pi_01 > 0 and pi_11 > 0 and pi > 0:
            lr_ind = -2 * (
                n00 * np.log(1 - pi) + n01 * np.log(pi) +
                n10 * np.log(1 - pi) + n11 * np.log(pi) -
                n00 * np.log(1 - pi_01) - n01 * np.log(pi_01) -
                n10 * np.log(1 - pi_11) - n11 * np.log(pi_11)
            )
        else:
            lr_ind = 0.0
        
        return lr_ind
    
    def _assess_model_performance(self, observed_rate: float, expected_rate: float) -> str:
        """Assess VaR model performance based on exception rates."""
        ratio = observed_rate / expected_rate
        
        if 0.8 <= ratio <= 1.2:
            return "Excellent"
        elif 0.6 <= ratio <= 1.4:
            return "Good"
        elif 0.4 <= ratio <= 1.6:
            return "Acceptable"
        else:
            return "Poor"
    
    def generate_risk_report(
        self, 
        portfolio_data: Dict, 
        returns_data: Dict[str, np.ndarray]
    ) -> Dict:
        """
        Generate comprehensive risk report.
        
        Args:
            portfolio_data: Current portfolio positions and values
            returns_data: Historical returns for all assets
            
        Returns:
            Comprehensive risk report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "portfolio_summary": portfolio_data,
            "risk_metrics": {},
            "stress_tests": {},
            "model_validation": {},
            "risk_limits": {},
            "recommendations": []
        }
        
        # Calculate portfolio VaR
        if returns_data:
            portfolio_var = self.calculate_portfolio_var(
                portfolio_data.get("positions", {}), 
                returns_data
            )
            report["risk_metrics"] = portfolio_var
            
            # Stress testing
            stress_results = self.stress_test_portfolio(
                portfolio_data.get("positions", {}), 
                returns_data
            )
            report["stress_tests"] = stress_results
            
            # Check risk limits
            report["risk_limits"] = self._check_risk_limits(portfolio_var)
        
        # Generate recommendations
        report["recommendations"] = self._generate_risk_recommendations(report)
        
        return report
    
    def _check_risk_limits(self, portfolio_var: Dict) -> Dict:
        """Check if portfolio risk metrics exceed limits."""
        limits_status = {}
        
        if "portfolio_var" in portfolio_var:
            var_95 = abs(portfolio_var["portfolio_var"].get("var", 0))
            limits_status["var_95_limit"] = {
                "current": var_95,
                "limit": self.config["max_portfolio_var_95"],
                "exceeded": var_95 > self.config["max_portfolio_var_95"]
            }
        
        return limits_status
    
    def _generate_risk_recommendations(self, report: Dict) -> List[str]:
        """Generate risk management recommendations based on report."""
        recommendations = []
        
        # Check VaR limits
        risk_limits = report.get("risk_limits", {})
        if risk_limits.get("var_95_limit", {}).get("exceeded", False):
            recommendations.append("Portfolio VaR exceeds limits. Consider reducing position sizes.")
        
        # Check stress test results
        stress_tests = report.get("stress_tests", {})
        for scenario, results in stress_tests.items():
            if results.get("max_loss", 0) < -0.20:  # >20% loss in stress
                recommendations.append(f"High loss potential in {scenario}. Review hedging strategies.")
        
        # Check diversification
        if "component_vars" in report.get("risk_metrics", {}):
            component_vars = report["risk_metrics"]["component_vars"]
            if component_vars and max(component_vars.values()) > self.config["max_component_var"]:
                recommendations.append("High concentration risk detected. Consider diversification.")
        
        return recommendations


# Factory function
def create_risk_analytics(config: Optional[Dict] = None) -> RiskAnalytics:
    """Create and return configured RiskAnalytics instance."""
    return RiskAnalytics(config)


# Example usage
if __name__ == "__main__":
    # Create risk analytics engine
    risk_engine = create_risk_analytics()
    
    # Example VaR calculation
    np.random.seed(42)
    sample_returns = np.random.normal(-0.001, 0.02, 250)  # 250 days of returns
    
    var_result = risk_engine.calculate_var(sample_returns, confidence_level=0.95)
    
    print("VaR Calculation Result:")
    print(f"95% VaR: {var_result['var']:.4f} ({var_result['var_percentage']:.2f}%)")
    print(f"Expected Shortfall: {var_result['expected_shortfall']:.4f}")
    print(f"Method: {var_result['method']}")
    print(f"Observations: {var_result['observations']}")
    print(f"Volatility: {var_result['volatility']:.4f}")