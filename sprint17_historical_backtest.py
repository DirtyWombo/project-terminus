#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 17: Full-Scale Historical Iron Condor Backtest
5-year validation test for SPY Short Iron Condor strategy

This script performs the definitive backtest required for Sprint 17,
testing the Iron Condor strategy across multiple market regimes from 2019-2023.

Key Features:
- 5-year historical backtest (2019-2023)
- Realistic Iron Condor simulation based on historical volatility
- Transaction costs and slippage modeling
- Complete performance analytics
- Go/No-Go decision criteria validation
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import logging
from typing import Dict, List, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HistoricalIronCondorBacktest:
    """
    Comprehensive Iron Condor backtesting with realistic historical simulation
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Strategy parameters (from Sprint 16)
        self.target_dte = 30
        self.delta_short = 0.12
        self.wing_width = 10.0
        self.profit_target = 0.50  # 50% of max profit
        self.stop_loss = 2.0       # 200% of credit
        self.min_dte_close = 7
        
        # Transaction costs
        self.commission_per_contract = 0.65  # Per contract commission
        self.slippage_per_contract = 0.05   # Slippage estimate
        
        # Position sizing
        self.contracts_per_trade = 10  # Trade 10 contracts per Iron Condor
        self.max_positions = 3         # Maximum concurrent positions
        
        # Tracking
        self.trades = []
        self.daily_pnl = []
        self.active_positions = []
        
        logger.info(f"Historical Iron Condor Backtest initialized")
        logger.info(f"Initial capital: ${initial_capital:,.2f}")
        logger.info(f"Strategy: {self.contracts_per_trade} contracts per trade, max {self.max_positions} positions")
        
    def download_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Download historical SPY data for the backtest period"""
        logger.info(f"Downloading {symbol} data from {start_date} to {end_date}")
        
        # Download SPY historical data
        spy = yf.download(symbol, start=start_date, end=end_date)
        
        # Calculate historical volatility (30-day)
        spy['returns'] = spy['Close'].pct_change()
        spy['volatility'] = spy['returns'].rolling(window=30).std() * np.sqrt(252)
        
        # Calculate VIX proxy (simplified)
        spy['vix_proxy'] = spy['volatility'] * 100
        
        logger.info(f"Downloaded {len(spy)} days of data")
        return spy
        
    def simulate_iron_condor_entry(self, date: datetime, underlying_price: float, 
                                 volatility: float) -> Dict[str, Any]:
        """
        Simulate Iron Condor entry based on market conditions
        
        Returns position details including expected credit and strikes
        """
        # Calculate approximate strikes based on delta
        # Using simplified Black-Scholes approximation
        iv = volatility
        tte = self.target_dte / 365.0
        
        # Short strikes (approximate based on delta)
        short_call_strike = underlying_price * (1 + self.delta_short * iv * np.sqrt(tte))
        short_put_strike = underlying_price * (1 - self.delta_short * iv * np.sqrt(tte))
        
        # Round to nearest dollar
        short_call_strike = round(short_call_strike)
        short_put_strike = round(short_put_strike)
        
        # Long strikes
        long_call_strike = short_call_strike + self.wing_width
        long_put_strike = short_put_strike - self.wing_width
        
        # Estimate credit based on volatility and time
        # Higher volatility = higher premium
        # This is a simplified model based on historical Iron Condor credits
        base_credit_pct = 0.15  # Base 15% of wing width
        vol_multiplier = volatility / 0.15  # Adjust for volatility (baseline 15%)
        
        credit_per_spread = self.wing_width * base_credit_pct * vol_multiplier
        
        # Apply bid-ask spread penalty
        credit_per_spread *= 0.95  # 5% haircut for spreads
        
        # Total position credit (before costs)
        gross_credit = credit_per_spread * self.contracts_per_trade * 100
        
        # Transaction costs
        total_commission = self.commission_per_contract * 4 * self.contracts_per_trade  # 4 legs
        total_slippage = self.slippage_per_contract * 4 * self.contracts_per_trade * 100
        
        net_credit = gross_credit - total_commission - total_slippage
        
        position = {
            'entry_date': date,
            'underlying_price': underlying_price,
            'volatility': volatility,
            'short_call': short_call_strike,
            'long_call': long_call_strike,
            'short_put': short_put_strike,
            'long_put': long_put_strike,
            'gross_credit': gross_credit,
            'net_credit': net_credit,
            'max_loss': (self.wing_width * 100 * self.contracts_per_trade) - net_credit,
            'contracts': self.contracts_per_trade,
            'dte': self.target_dte,
            'status': 'open'
        }
        
        return position
        
    def check_position_exit(self, position: Dict, current_date: datetime, 
                          current_price: float, current_vol: float) -> Tuple[bool, float, str]:
        """
        Check if position should be closed and calculate P&L
        
        Returns: (should_close, pnl, reason)
        """
        # Calculate days held
        days_held = (current_date - position['entry_date']).days
        dte_remaining = position['dte'] - days_held
        
        # Check minimum DTE
        if dte_remaining <= self.min_dte_close:
            # Calculate final P&L at near expiration
            pnl = self._calculate_position_pnl(position, current_price, dte_remaining, current_vol)
            return True, pnl, 'min_dte'
            
        # Calculate current P&L
        current_pnl = self._calculate_position_pnl(position, current_price, dte_remaining, current_vol)
        
        # Check profit target
        if current_pnl >= position['net_credit'] * self.profit_target:
            return True, current_pnl, 'profit_target'
            
        # Check stop loss
        if current_pnl <= -position['net_credit'] * self.stop_loss:
            return True, current_pnl, 'stop_loss'
            
        return False, current_pnl, 'hold'
        
    def _calculate_position_pnl(self, position: Dict, current_price: float, 
                              dte_remaining: int, current_vol: float) -> float:
        """
        Calculate position P&L based on current market conditions
        
        Simplified model based on:
        - Price movement relative to strikes
        - Time decay (theta)
        - Volatility changes (vega)
        """
        initial_credit = position['net_credit']
        
        # Time decay component (positive for Iron Condor)
        days_held = position['dte'] - dte_remaining
        time_decay_pct = (days_held / position['dte']) * 0.7  # Assume 70% decay by expiration
        time_value = initial_credit * time_decay_pct
        
        # Price movement component
        # Check if price breached any strikes
        if current_price > position['short_call']:
            # Call side is in trouble
            intrinsic_loss = (current_price - position['short_call']) * 100 * position['contracts']
            intrinsic_loss = min(intrinsic_loss, position['max_loss'])  # Cap at max loss
            
        elif current_price < position['short_put']:
            # Put side is in trouble
            intrinsic_loss = (position['short_put'] - current_price) * 100 * position['contracts']
            intrinsic_loss = min(intrinsic_loss, position['max_loss'])  # Cap at max loss
            
        else:
            # Price still between strikes - no intrinsic loss
            intrinsic_loss = 0
            
        # Volatility component (simplified)
        vol_change = (current_vol - position['volatility']) / position['volatility']
        vol_impact = -vol_change * initial_credit * 0.5  # Negative vega for short options
        
        # Total P&L
        total_pnl = time_value - intrinsic_loss + vol_impact
        
        # Apply exit costs
        if dte_remaining > self.min_dte_close:
            exit_costs = self.commission_per_contract * 4 * position['contracts']
            exit_costs += self.slippage_per_contract * 4 * position['contracts'] * 100
            total_pnl -= exit_costs
            
        return total_pnl
        
    def should_enter_position(self, date: datetime, volatility: float, 
                            active_count: int) -> bool:
        """
        Determine if we should enter a new Iron Condor position
        
        Entry criteria:
        - Not at max positions
        - Sufficient volatility (VIX > 12)
        - Not in extreme volatility (VIX < 40)
        - Proper market hours/conditions
        """
        if active_count >= self.max_positions:
            return False
            
        vix_proxy = volatility * 100
        
        # Don't trade in very low volatility (premium too low)
        if vix_proxy < 12:
            return False
            
        # Don't trade in extreme volatility (too risky)
        if vix_proxy > 40:
            return False
            
        # Simple entry frequency - try to maintain positions
        if active_count < self.max_positions:
            # Random entry with 10% probability when conditions are met
            if np.random.random() < 0.10:
                return True
                
        return False
        
    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Run complete historical backtest
        """
        logger.info("=" * 80)
        logger.info("SPRINT 17: HISTORICAL IRON CONDOR BACKTEST")
        logger.info("=" * 80)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        
        # Download historical data
        spy_data = self.download_historical_data('SPY', start_date, end_date)
        
        # Initialize tracking
        portfolio_value = []
        daily_returns = []
        
        # Main backtest loop
        for i, (date, row) in enumerate(spy_data.iterrows()):
            try:
                current_vol = float(row['volatility'])
                if np.isnan(current_vol) or current_vol == 0:
                    continue
            except (ValueError, TypeError):
                continue
                
            current_price = float(row['Close'])
            
            # Check existing positions
            positions_to_close = []
            
            for i, position in enumerate(self.active_positions):
                should_close, pnl, reason = self.check_position_exit(
                    position, date, current_price, current_vol
                )
                
                if should_close:
                    positions_to_close.append((i, pnl, reason))
                    
            # Close positions (reverse order to maintain indices)
            for i, pnl, reason in sorted(positions_to_close, reverse=True):
                position = self.active_positions.pop(i)
                self.current_capital += pnl
                
                trade_record = {
                    'entry_date': position['entry_date'],
                    'exit_date': date,
                    'days_held': (date - position['entry_date']).days,
                    'pnl': pnl,
                    'return_pct': (pnl / position['net_credit']) * 100,
                    'exit_reason': reason,
                    'entry_price': position['underlying_price'],
                    'exit_price': current_price
                }
                
                self.trades.append(trade_record)
                
                logger.info(f"Closed position: {reason}, P&L: ${pnl:.2f}")
                
            # Check for new entry
            if self.should_enter_position(date, current_vol, len(self.active_positions)):
                position = self.simulate_iron_condor_entry(date, current_price, current_vol)
                
                # Check if we have capital for the position
                required_capital = position['max_loss']
                
                if self.current_capital >= required_capital:
                    self.active_positions.append(position)
                    logger.info(f"Opened Iron Condor: Credit ${position['net_credit']:.2f}")
                    
            # Track daily portfolio value
            open_pnl = sum([
                self._calculate_position_pnl(pos, current_price, 
                                           pos['dte'] - (date - pos['entry_date']).days,
                                           current_vol)
                for pos in self.active_positions
            ])
            
            total_value = self.current_capital + open_pnl
            portfolio_value.append({
                'date': date,
                'portfolio_value': total_value,
                'spy_price': current_price,
                'volatility': current_vol,
                'positions': len(self.active_positions)
            })
            
            if len(portfolio_value) > 1:
                daily_return = (total_value - portfolio_value[-2]['portfolio_value']) / portfolio_value[-2]['portfolio_value']
                daily_returns.append(daily_return)
                
        # Calculate final metrics
        results = self._calculate_performance_metrics(portfolio_value, daily_returns)
        
        logger.info("=" * 80)
        logger.info("BACKTEST COMPLETE")
        logger.info("=" * 80)
        
        return results
        
    def _calculate_performance_metrics(self, portfolio_value: List[Dict], 
                                     daily_returns: List[float]) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        
        if not portfolio_value or not daily_returns:
            return {}
            
        df = pd.DataFrame(portfolio_value)
        
        # Basic metrics
        initial_value = self.initial_capital
        final_value = df['portfolio_value'].iloc[-1]
        total_return = (final_value - initial_value) / initial_value
        
        # Annualized return
        years = len(df) / 252
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # Sharpe ratio
        if daily_returns:
            returns_series = pd.Series(daily_returns)
            sharpe = (returns_series.mean() / returns_series.std() * np.sqrt(252)) if returns_series.std() > 0 else 0
        else:
            sharpe = 0
            
        # Max drawdown
        rolling_max = df['portfolio_value'].expanding().max()
        drawdowns = (df['portfolio_value'] - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        # Win rate
        if self.trades:
            winning_trades = [t for t in self.trades if t['pnl'] > 0]
            win_rate = len(winning_trades) / len(self.trades)
        else:
            win_rate = 0
            
        # Additional metrics
        profit_factor = 0
        if self.trades:
            gross_profits = sum([t['pnl'] for t in self.trades if t['pnl'] > 0])
            gross_losses = abs(sum([t['pnl'] for t in self.trades if t['pnl'] < 0]))
            profit_factor = gross_profits / gross_losses if gross_losses > 0 else 0
            
        results = {
            'initial_capital': initial_value,
            'final_value': final_value,
            'total_return_pct': total_return * 100,
            'annualized_return_pct': annualized_return * 100,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown * 100,
            'total_trades': len(self.trades),
            'win_rate_pct': win_rate * 100,
            'profit_factor': profit_factor,
            'avg_days_held': np.mean([t['days_held'] for t in self.trades]) if self.trades else 0,
            'best_trade': max([t['pnl'] for t in self.trades]) if self.trades else 0,
            'worst_trade': min([t['pnl'] for t in self.trades]) if self.trades else 0,
            'avg_trade_pnl': np.mean([t['pnl'] for t in self.trades]) if self.trades else 0
        }
        
        # Print results
        self._print_results(results)
        
        return results
        
    def _print_results(self, results: Dict[str, Any]):
        """Print formatted results"""
        
        print("\n" + "=" * 80)
        print("SPRINT 17: IRON CONDOR STRATEGY - 5-YEAR BACKTEST RESULTS")
        print("=" * 80)
        
        print("\nPERFORMANCE SUMMARY:")
        print(f"  Initial Capital: ${results['initial_capital']:,.2f}")
        print(f"  Final Value: ${results['final_value']:,.2f}")
        print(f"  Total Return: {results['total_return_pct']:.2f}%")
        print(f"  Annualized Return: {results['annualized_return_pct']:.2f}%")
        print(f"  Sharpe Ratio: {results['sharpe_ratio']:.3f}")
        print(f"  Max Drawdown: {results['max_drawdown_pct']:.2f}%")
        
        print("\nTRADING STATISTICS:")
        print(f"  Total Trades: {results['total_trades']}")
        print(f"  Win Rate: {results['win_rate_pct']:.1f}%")
        print(f"  Profit Factor: {results['profit_factor']:.2f}")
        print(f"  Avg Days Held: {results['avg_days_held']:.1f}")
        print(f"  Avg Trade P&L: ${results['avg_trade_pnl']:.2f}")
        print(f"  Best Trade: ${results['best_trade']:.2f}")
        print(f"  Worst Trade: ${results['worst_trade']:.2f}")
        
        print("\n" + "=" * 80)
        print("SUCCESS CRITERIA VALIDATION:")
        print("=" * 80)
        
        # Check against Sprint 17 criteria
        criteria = {
            'Post-Cost Return > 10%': results['annualized_return_pct'] > 10,
            'Sharpe Ratio > 1.2': results['sharpe_ratio'] > 1.2,
            'Max Drawdown < 15%': abs(results['max_drawdown_pct']) < 15,
            'Win Rate > 75%': results['win_rate_pct'] > 75
        }
        
        all_passed = True
        for criterion, passed in criteria.items():
            status = "PASS" if passed else "FAIL"
            print(f"  {criterion}: {status}")
            if not passed:
                all_passed = False
                
        print("\n" + "=" * 80)
        print(f"FINAL VERDICT: {'PASS - READY FOR PAPER TRADING' if all_passed else 'FAIL - STRATEGY REJECTED'}")
        print("=" * 80)
        
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save results to JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sprint17_backtest_results_{timestamp}.json"
            
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        logger.info(f"Results saved to {filename}")
        

def main():
    """
    Run Sprint 17 historical backtest
    """
    print("Starting Sprint 17: 5-Year Iron Condor Validation Backtest...")
    
    # Initialize backtester
    backtester = HistoricalIronCondorBacktest(initial_capital=100000.0)
    
    # Run 5-year backtest (2019-2023)
    start_date = '2019-01-01'
    end_date = '2023-12-31'
    
    print(f"Backtesting period: {start_date} to {end_date}")
    print("This comprehensive backtest will determine the Go/No-Go decision for the strategy.")
    
    # Run the backtest
    results = backtester.run_backtest(start_date, end_date)
    
    # Save results
    backtester.save_results(results)
    
    print("\nSprint 17 backtest completed!")
    

if __name__ == "__main__":
    main()