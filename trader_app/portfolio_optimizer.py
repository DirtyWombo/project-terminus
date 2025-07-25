"""
Advanced Portfolio Optimizer - Tier 3 Feature
============================================

Purpose: Implement Modern Portfolio Theory (MPT) for optimal capital allocation.
Implementation: Calculates the Efficient Frontier and identifies the portfolio with the maximum Sharpe Ratio.
Upgrade Path: Integration with more advanced optimization models (e.g., Black-Litterman, Risk Parity).
"""

import logging
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Assuming these are accessible from the trader_app context
from .models import db, Price, Position
from .exchange_manager import exchange_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PortfolioOptimizer:
    """
    Implements advanced portfolio optimization techniques based on Modern Portfolio Theory.
    """

    def __init__(self, lookback_days: int = 90, risk_free_rate: float = 0.02):
        self.lookback_days = lookback_days
        self.risk_free_rate = risk_free_rate
        self.asset_symbols = self._get_available_assets()

    def _get_available_assets(self) -> List[str]:
        """
        Get a list of all assets available for optimization.
        For now, this will be the unique symbols in the Price table.
        """
        try:
            # In a real system, this might come from a config or a specific table
            symbols = db.session.query(Price.symbol).distinct().all()
            return [s[0] for s in symbols]
        except Exception as e:
            logging.error(f"Error getting available assets: {e}")
            return ["BTC-USD", "ETH-USD", "SOL-USD"] # Fallback

    def get_historical_data(self) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for all available assets.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
            prices_query = Price.query.filter(
                Price.symbol.in_(self.asset_symbols),
                Price.timestamp >= cutoff_date
            ).order_by(Price.timestamp.asc()).all()

            if not prices_query:
                logging.warning("No historical price data found for optimization.")
                return None

            df = pd.DataFrame([(p.timestamp, p.symbol, float(p.close)) for p in prices_query], columns=['timestamp', 'symbol', 'price'])
            price_matrix = df.pivot(index='timestamp', columns='symbol', values='price').ffill()
            
            # Ensure we have enough data
            if len(price_matrix) < 20:
                logging.warning(f"Insufficient historical data for optimization: {len(price_matrix)} days.")
                return None
                
            return price_matrix

        except Exception as e:
            logging.error(f"Error fetching historical data: {e}")
            return None

    def calculate_performance_metrics(self, price_data: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        """
        Calculate expected returns and the covariance matrix for the assets.
        """
        # Calculate daily returns
        returns = price_data.pct_change().dropna()
        
        # Calculate annualized expected returns
        expected_returns = returns.mean() * 252  # 252 trading days in a year
        
        # Calculate annualized covariance matrix
        cov_matrix = returns.cov() * 252
        
        return expected_returns, cov_matrix

    def _calculate_portfolio_performance(self, weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> Tuple[float, float, float]:
        """Helper function to calculate portfolio stats."""
        portfolio_return = np.sum(weights * expected_returns)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
        return portfolio_return, portfolio_volatility, sharpe_ratio

    def find_optimal_portfolio(self, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> Tuple[Dict, Dict]:
        """
        Find the optimal portfolio with the maximum Sharpe Ratio.
        """
        num_assets = len(expected_returns)
        args = (expected_returns, cov_matrix)

        # Constraint: sum of weights is 1
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})

        # Bounds for each weight (0 to 1)
        bounds = tuple((0, 1) for asset in range(num_assets))

        # Initial guess (equal distribution)
        initial_weights = num_assets * [1. / num_assets,]

        # Objective function to minimize (negative Sharpe Ratio)
        def neg_sharpe_ratio(weights, expected_returns, cov_matrix, risk_free_rate):
            p_return, p_vol, _ = self._calculate_portfolio_performance(weights, expected_returns, cov_matrix)
            return -(p_return - risk_free_rate) / p_vol

        # Perform the optimization
        optimal_result = minimize(neg_sharpe_ratio, initial_weights, args=args,
                                  method='SLSQP', bounds=bounds, constraints=constraints)

        optimal_weights = optimal_result.x
        
        # Performance of the optimal portfolio
        opt_return, opt_vol, opt_sharpe = self._calculate_portfolio_performance(optimal_weights, expected_returns, cov_matrix)

        optimal_allocation = dict(zip(expected_returns.index, optimal_weights))
        performance_summary = {
            'expected_return': opt_return,
            'volatility': opt_vol,
            'sharpe_ratio': opt_sharpe
        }
        
        return optimal_allocation, performance_summary

    def generate_efficient_frontier(self, expected_returns: pd.Series, cov_matrix: pd.DataFrame, num_portfolios: int = 100) -> List[Dict]:
        """
        Generate a series of portfolios that form the Efficient Frontier.
        """
        num_assets = len(expected_returns)
        results = np.zeros((3, num_portfolios))
        
        # We will also store the weights for each portfolio
        weights_record = []

        for i in range(num_portfolios):
            # Generate random weights
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)
            weights_record.append(weights)
            
            # Calculate portfolio performance
            p_return, p_vol, _ = self._calculate_portfolio_performance(weights, expected_returns, cov_matrix)
            
            results[0,i] = p_return
            results[1,i] = p_vol
            results[2,i] = (p_return - self.risk_free_rate) / p_vol

        frontier_data = []
        for i in range(num_portfolios):
            frontier_data.append({
                'return': results[0,i],
                'volatility': results[1,i],
                'sharpe_ratio': results[2,i],
                'weights': dict(zip(expected_returns.index, weights_record[i]))
            })
            
        return frontier_data

    def get_rebalancing_recommendations(self, current_portfolio: Dict[str, float], optimal_allocation: Dict[str, float]) -> List[Dict]:
        """
        Compare current portfolio to optimal allocation and generate rebalancing trades.
        """
        recommendations = []
        current_total_value = sum(current_portfolio.values())

        if current_total_value == 0:
            logging.info("No current portfolio value, cannot generate rebalancing trades.")
            return []

        for asset, optimal_weight in optimal_allocation.items():
            target_value = current_total_value * optimal_weight
            current_value = current_portfolio.get(asset, 0.0)
            value_diff = target_value - current_value

            # Only recommend trades above a certain threshold to avoid dust trades
            if abs(value_diff) > 0.01 * current_total_value: # 1% of portfolio value
                action = 'BUY' if value_diff > 0 else 'SELL'
                recommendations.append({
                    'symbol': asset,
                    'action': action,
                    'value_to_trade': abs(value_diff),
                    'current_weight': current_value / current_total_value,
                    'target_weight': optimal_weight
                })
        
        return recommendations

    def run_optimization(self) -> Optional[Dict]:
        """
        Run the full portfolio optimization process.
        """
        logging.info("Starting portfolio optimization process...")
        
        # 1. Get historical data
        price_data = self.get_historical_data()
        if price_data is None:
            return None

        # 2. Calculate metrics
        expected_returns, cov_matrix = self.calculate_performance_metrics(price_data)

        # 3. Find optimal portfolio (max Sharpe Ratio)
        optimal_allocation, performance_summary = self.find_optimal_portfolio(expected_returns, cov_matrix)

        # 4. Generate Efficient Frontier for plotting
        efficient_frontier = self.generate_efficient_frontier(expected_returns, cov_matrix)
        
        # 5. Get rebalancing recommendations
        # This requires getting the current portfolio state
        # For now, we'll use a placeholder. This will be integrated later.
        current_portfolio_values = {s: 0 for s in self.asset_symbols} # Placeholder
        rebalancing_trades = self.get_rebalancing_recommendations(current_portfolio_values, optimal_allocation)

        logging.info(f"Optimal portfolio found with Sharpe Ratio: {performance_summary['sharpe_ratio']:.2f}")

        return {
            'optimal_allocation': optimal_allocation,
            'optimal_performance': performance_summary,
            'efficient_frontier': efficient_frontier,
            'rebalancing_recommendations': rebalancing_trades,
            'last_updated': datetime.now().isoformat()
        }

# Factory function for easy integration
def create_portfolio_optimizer() -> PortfolioOptimizer:
    return PortfolioOptimizer()

if __name__ == '__main__':
    # This is for testing purposes and requires a running app context
    # You would typically run this within the Flask app shell
    print("Portfolio Optimizer module created. Run within the app context for testing.")
