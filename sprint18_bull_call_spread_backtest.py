#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 18: Full-Scale Historical Bull Call Spread Backtest
5-year validation test for SPY Bull Call Spread strategy

This script performs the definitive backtest required for Sprint 18,
testing the Bull Call Spread strategy across multiple market regimes from 2019-2023.

Key Features:
- 5-year historical backtest (2019-2023)
- Realistic Bull Call Spread simulation based on historical data
- Transaction costs and slippage modeling
- Technical indicator-based entry signals
- Complete performance analytics with Sprint 18 success criteria
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
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BullCallSpreadTrade:
    """Individual Bull Call Spread trade record"""
    entry_date: datetime
    exit_date: datetime
    underlying_price_entry: float
    underlying_price_exit: float
    long_call_strike: float
    short_call_strike: float
    net_debit_paid: float
    pnl: float
    exit_reason: str
    days_held: int
    dte_at_entry: int
    dte_at_exit: int

class HistoricalBullCallSpreadBacktest:
    """
    Comprehensive Bull Call Spread backtesting with realistic historical simulation
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Strategy parameters (from Sprint 18)
        self.target_dte = 45
        self.long_call_delta = 0.50    # ATM call
        self.short_call_delta = 0.30   # OTM call
        self.profit_target = 1.00      # 100% of debit paid
        self.stop_loss = 0.50          # 50% of debit paid
        self.min_dte_close = 7
        
        # Technical indicators
        self.regime_filter_period = 200  # 200-day MA
        self.pullback_ema_period = 20    # 20-day EMA
        
        # Transaction costs
        self.commission_per_contract = 0.65  # Per contract commission
        self.slippage_per_contract = 0.05   # Slippage estimate
        
        # Position sizing
        self.contracts_per_trade = 10  # Trade 10 contracts per spread
        self.max_positions = 3         # Maximum concurrent positions
        
        # Tracking
        self.trades: List[BullCallSpreadTrade] = []
        self.daily_pnl = []
        self.active_positions = []
        self.equity_curve = []
        
        # Technical indicator storage
        self.price_history = []
        self.ema_history = []
        self.ma_200_history = []
        
        logger.info(f"Historical Bull Call Spread Backtest initialized")
        logger.info(f"Initial capital: ${initial_capital:,.2f}")
        logger.info(f"Strategy: {self.contracts_per_trade} contracts per trade, max {self.max_positions} positions")
        
    def download_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Download historical SPY data for the backtest period"""
        logger.info(f"Downloading {symbol} data from {start_date} to {end_date}")
        
        # Download SPY historical data
        spy = yf.download(symbol, start=start_date, end=end_date)
        
        # If multi-level columns, flatten them
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.droplevel(1)
        
        # Calculate technical indicators
        spy['returns'] = spy['Close'].pct_change()
        spy['volatility'] = spy['returns'].rolling(window=30).std() * np.sqrt(252)
        spy['ma_200'] = spy['Close'].rolling(window=self.regime_filter_period).mean()
        spy['ema_20'] = spy['Close'].ewm(span=self.pullback_ema_period).mean()
        
        # Calculate signals - handle NaN values
        spy['in_bull_regime'] = (spy['Close'] > spy['ma_200']).fillna(False)
        spy['pullback_signal'] = (
            (spy['Close'].shift(1) > spy['ema_20'].shift(1) * 1.001) & 
            (spy['Close'] <= spy['ema_20'] * 1.005)
        ).fillna(False)
        
        logger.info(f"Downloaded {len(spy)} days of data")
        return spy
        
    def simulate_bull_call_spread_entry(self, date: datetime, underlying_price: float, 
                                      volatility: float) -> Dict[str, Any]:
        """
        Simulate Bull Call Spread entry based on market conditions
        
        Returns position details including expected debit and strikes
        """
        # Calculate approximate strikes based on delta
        # Using simplified Black-Scholes approximation
        iv = volatility
        tte = self.target_dte / 365.0
        
        # ATM long call (delta ~0.50)
        long_call_strike = round(underlying_price)
        
        # OTM short call (delta ~0.30) - approximately 5-7% OTM
        otm_distance = underlying_price * 0.06  # 6% OTM approximation
        short_call_strike = round(underlying_price + otm_distance)
        
        # Estimate option prices using simplified but improved pricing
        # ATM long call - base price with volatility and time adjustments
        intrinsic_long = max(0, underlying_price - long_call_strike)
        time_value_long = underlying_price * 0.03 * (iv / 0.20) * np.sqrt(tte)
        long_call_price = intrinsic_long + time_value_long
        
        # OTM short call - lower time value for OTM options
        intrinsic_short = max(0, underlying_price - short_call_strike)
        time_value_short = underlying_price * 0.015 * (iv / 0.20) * np.sqrt(tte)
        short_call_price = intrinsic_short + time_value_short
        
        # Ensure minimum reasonable prices
        long_call_price = max(long_call_price, 0.50)
        short_call_price = max(short_call_price, 0.20)
        
        # Net debit
        net_debit = long_call_price - short_call_price
        
        # Ensure reasonable debit range
        min_debit = 0.50
        max_debit = 3.00
        net_debit = max(min_debit, min(max_debit, net_debit))
        
        # Strike width
        strike_width = short_call_strike - long_call_strike
        
        # Calculate max profit/loss
        max_profit = strike_width - net_debit
        max_loss = net_debit
        breakeven = long_call_strike + net_debit
        
        return {
            'long_call_strike': long_call_strike,
            'short_call_strike': short_call_strike,
            'net_debit': net_debit,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'breakeven': breakeven,
            'strike_width': strike_width,
            'dte': self.target_dte
        }
    
    def simulate_bull_call_spread_exit(self, position: Dict[str, Any], 
                                     current_price: float, current_date: datetime,
                                     days_held: int, volatility: float) -> Tuple[float, str]:
        """
        Simulate Bull Call Spread exit and calculate P&L
        
        Returns (pnl, exit_reason)
        """
        entry_debit = position['net_debit']
        long_strike = position['long_call_strike']
        short_strike = position['short_call_strike']
        dte_remaining = position['dte'] - days_held
        
        # Calculate intrinsic values
        long_intrinsic = max(0, current_price - long_strike)
        short_intrinsic = max(0, current_price - short_strike)
        
        # Estimate time values (simplified)
        if dte_remaining > 0:
            tte = dte_remaining / 365.0
            iv = volatility
            
            # Time value approximation (decreases with time)
            time_decay_factor = np.sqrt(tte) if tte > 0 else 0
            
            long_time_value = current_price * 0.02 * (iv / 0.20) * time_decay_factor
            short_time_value = current_price * 0.01 * (iv / 0.20) * time_decay_factor
        else:
            long_time_value = 0
            short_time_value = 0
        
        # Total option values
        long_call_value = long_intrinsic + long_time_value
        short_call_value = short_intrinsic + short_time_value
        
        # Net value of spread (what we can sell it for)
        spread_value = long_call_value - short_call_value
        
        # P&L = spread_value - entry_debit (per share)
        pnl_per_share = spread_value - entry_debit
        
        # Account for transaction costs
        total_commission = 4 * self.commission_per_contract  # 2 legs × 2 transactions
        total_slippage = 2 * self.slippage_per_contract     # Entry and exit slippage
        transaction_costs_per_contract = (total_commission + total_slippage) / 100  # Per share
        
        pnl_per_contract = (pnl_per_share - transaction_costs_per_contract) * 100
        total_pnl = pnl_per_contract * self.contracts_per_trade
        
        # Determine exit reason
        if dte_remaining <= self.min_dte_close:
            exit_reason = "DTE_EXPIRY"
        elif pnl_per_share >= entry_debit * self.profit_target:
            exit_reason = "PROFIT_TARGET"
        elif pnl_per_share <= -entry_debit * self.stop_loss:
            exit_reason = "STOP_LOSS"
        else:
            exit_reason = "MANUAL"
        
        return total_pnl, exit_reason
    
    def should_enter_trade(self, data_row: pd.Series, current_date: datetime) -> bool:
        """Check if conditions are met for new Bull Call Spread entry"""
        
        # Need sufficient data history
        if pd.isna(data_row['ma_200']) or pd.isna(data_row['ema_20']):
            return False
        
        # Must be in bull regime (above 200-day MA)
        if not data_row['in_bull_regime']:
            return False
        
        # Must have pullback signal
        if not data_row['pullback_signal']:
            return False
        
        # Don't exceed max positions
        if len(self.active_positions) >= self.max_positions:
            return False
        
        # Don't enter on consecutive days (avoid clustering)
        if self.active_positions:
            last_entry = max([pos['entry_date'] for pos in self.active_positions])
            if (current_date - last_entry).days < 10:  # Increased to 10 days
                return False
        
        # Additional volatility filter - don't enter during extreme volatility
        volatility = data_row['volatility'] if not pd.isna(data_row['volatility']) else 0.20
        if volatility > 0.40:  # Don't enter if volatility > 40%
            return False
        
        return True
    
    def should_exit_position(self, position: Dict[str, Any], current_data: pd.Series, 
                           current_date: datetime, days_held: int) -> bool:
        """Check if position should be exited"""
        
        current_price = current_data['Close']
        entry_debit = position['net_debit']
        
        # Don't exit on entry day unless absolutely necessary
        if days_held == 0:
            return False
        
        # Always exit at minimum DTE
        dte_remaining = position['dte'] - days_held
        if dte_remaining <= self.min_dte_close:
            return True
        
        # Estimate current P&L for profit target / stop loss
        long_intrinsic = max(0, current_price - position['long_call_strike'])
        short_intrinsic = max(0, current_price - position['short_call_strike'])
        
        # Add time value component for more realistic valuation
        if dte_remaining > 0:
            tte = dte_remaining / 365.0
            volatility = current_data['volatility'] if not pd.isna(current_data['volatility']) else 0.20
            
            # Rough time value estimation
            long_time_value = current_price * 0.02 * (volatility / 0.20) * np.sqrt(tte)
            short_time_value = current_price * 0.01 * (volatility / 0.20) * np.sqrt(tte)
        else:
            long_time_value = 0
            short_time_value = 0
        
        current_spread_value = (long_intrinsic + long_time_value) - (short_intrinsic + short_time_value)
        pnl_per_share = current_spread_value - entry_debit
        
        # More conservative profit target and stop loss
        profit_threshold = entry_debit * self.profit_target * 0.8  # 80% of target
        stop_threshold = -entry_debit * self.stop_loss * 1.2      # 120% of stop
        
        # Check profit target
        if pnl_per_share >= profit_threshold:
            return True
        
        # Check stop loss
        if pnl_per_share <= stop_threshold:
            return True
        
        return False
    
    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Run the complete historical backtest
        """
        logger.info(f"Starting Bull Call Spread backtest: {start_date} to {end_date}")
        
        # Download data
        spy_data = self.download_historical_data('SPY', start_date, end_date)
        
        # Reset tracking variables
        self.trades = []
        self.active_positions = []
        self.current_capital = self.initial_capital
        self.equity_curve = []
        
        total_days = len(spy_data)
        
        for i, (date, row) in enumerate(spy_data.iterrows()):
            if i % 60 == 0:  # Progress update every 60 days
                logger.info(f"Processing {date.strftime('%Y-%m-%d')} - Day {i+1}/{total_days}")
            
            current_date = date
            current_price = row['Close']
            volatility = row['volatility'] if not pd.isna(row['volatility']) else 0.20
            
            # Check for new entries
            if self.should_enter_trade(row, current_date):
                position = self.simulate_bull_call_spread_entry(
                    current_date, current_price, volatility
                )
                
                # Add position tracking
                position['entry_date'] = current_date
                position['entry_price'] = current_price
                position['days_held'] = 0
                
                self.active_positions.append(position)
                
                logger.info(f"ENTRY: {current_date.strftime('%Y-%m-%d')} - "
                           f"${position['long_call_strike']:.0f}/${position['short_call_strike']:.0f} "
                           f"spread for ${position['net_debit']:.2f} debit")
            
            # Check exits for active positions
            positions_to_close = []
            for pos_idx, position in enumerate(self.active_positions):
                position['days_held'] = (current_date - position['entry_date']).days
                
                if self.should_exit_position(position, row, current_date, position['days_held']):
                    positions_to_close.append(pos_idx)
            
            # Close positions (reverse order to maintain indices)
            for pos_idx in reversed(positions_to_close):
                position = self.active_positions[pos_idx]
                
                pnl, exit_reason = self.simulate_bull_call_spread_exit(
                    position, current_price, current_date, position['days_held'], volatility
                )
                
                # Create trade record
                trade = BullCallSpreadTrade(
                    entry_date=position['entry_date'],
                    exit_date=current_date,
                    underlying_price_entry=position['entry_price'],
                    underlying_price_exit=current_price,
                    long_call_strike=position['long_call_strike'],
                    short_call_strike=position['short_call_strike'],
                    net_debit_paid=position['net_debit'],
                    pnl=pnl,
                    exit_reason=exit_reason,
                    days_held=position['days_held'],
                    dte_at_entry=position['dte'],
                    dte_at_exit=position['dte'] - position['days_held']
                )
                
                self.trades.append(trade)
                self.current_capital += pnl
                
                logger.info(f"EXIT: {current_date.strftime('%Y-%m-%d')} - "
                           f"P&L: ${pnl:.2f}, Reason: {exit_reason}, "
                           f"Days held: {position['days_held']}")
                
                # Remove from active positions
                del self.active_positions[pos_idx]
            
            # Track equity curve
            self.equity_curve.append({
                'date': current_date,
                'equity': self.current_capital,
                'active_positions': len(self.active_positions)
            })
        
        # Close any remaining positions at the end
        if self.active_positions:
            final_row = spy_data.iloc[-1]
            final_date = spy_data.index[-1]
            final_price = final_row['Close']
            final_volatility = final_row['volatility'] if not pd.isna(final_row['volatility']) else 0.20
            
            for position in self.active_positions:
                position['days_held'] = (final_date - position['entry_date']).days
                pnl, exit_reason = self.simulate_bull_call_spread_exit(
                    position, final_price, final_date, position['days_held'], final_volatility
                )
                
                trade = BullCallSpreadTrade(
                    entry_date=position['entry_date'],
                    exit_date=final_date,
                    underlying_price_entry=position['entry_price'],
                    underlying_price_exit=final_price,
                    long_call_strike=position['long_call_strike'],
                    short_call_strike=position['short_call_strike'],
                    net_debit_paid=position['net_debit'],
                    pnl=pnl,
                    exit_reason="BACKTEST_END",
                    days_held=position['days_held'],
                    dte_at_entry=position['dte'],
                    dte_at_exit=position['dte'] - position['days_held']
                )
                
                self.trades.append(trade)
                self.current_capital += pnl
        
        # Calculate performance metrics
        return self.calculate_performance_metrics(start_date, end_date)
    
    def calculate_performance_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        
        if not self.trades:
            return {"error": "No trades executed during backtest period"}
        
        # Basic trade statistics
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L statistics
        trade_pnls = [t.pnl for t in self.trades]
        total_pnl = sum(trade_pnls)
        avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        gross_profit = sum([pnl for pnl in trade_pnls if pnl > 0])
        gross_loss = abs(sum([pnl for pnl in trade_pnls if pnl < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        best_trade = max(trade_pnls) if trade_pnls else 0
        worst_trade = min(trade_pnls) if trade_pnls else 0
        
        # Return calculations
        total_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        
        # Calculate annualized return
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        years = (end_dt - start_dt).days / 365.25
        
        # Handle negative capital case
        if self.current_capital <= 0 or years <= 0:
            annualized_return = -100.0  # Total loss
        else:
            try:
                annualized_return = ((self.current_capital / self.initial_capital) ** (1/years) - 1) * 100
            except (OverflowError, ValueError):
                annualized_return = -100.0
        
        # Calculate Sharpe ratio (simplified)
        if self.equity_curve:
            equity_df = pd.DataFrame(self.equity_curve)
            equity_df.set_index('date', inplace=True)
            daily_returns = equity_df['equity'].pct_change().dropna()
            
            if len(daily_returns) > 1:
                excess_return = daily_returns.mean() * 252  # Annualized
                volatility = daily_returns.std() * np.sqrt(252)  # Annualized
                sharpe_ratio = excess_return / volatility if volatility > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Calculate max drawdown
            running_max = equity_df['equity'].expanding().max()
            drawdown = (equity_df['equity'] - running_max) / running_max
            max_drawdown = drawdown.min() * 100  # Convert to percentage
        else:
            sharpe_ratio = 0
            max_drawdown = 0
        
        # Trade timing statistics
        hold_periods = [t.days_held for t in self.trades]
        avg_hold_period = np.mean(hold_periods) if hold_periods else 0
        
        # Exit reason breakdown
        exit_reasons = {}
        for trade in self.trades:
            reason = trade.exit_reason
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        # Sprint 18 Success Criteria Check
        success_criteria = {
            'post_cost_annualized_return_target': 12.0,
            'post_cost_sharpe_ratio_target': 0.8,
            'max_drawdown_target': 20.0,
            'win_rate_target': 45.0
        }
        
        criteria_met = {
            'annualized_return_met': annualized_return >= success_criteria['post_cost_annualized_return_target'],
            'sharpe_ratio_met': sharpe_ratio >= success_criteria['post_cost_sharpe_ratio_target'],
            'max_drawdown_met': abs(max_drawdown) <= success_criteria['max_drawdown_target'],
            'win_rate_met': win_rate >= success_criteria['win_rate_target']
        }
        
        all_criteria_met = all(criteria_met.values())
        
        return {
            # Basic metrics
            'backtest_period': f"{start_date} to {end_date}",
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            
            # P&L metrics
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_pnl': total_pnl,
            'total_return_pct': total_return,
            'annualized_return_pct': annualized_return,
            'avg_trade_pnl': avg_trade_pnl,
            
            # Risk metrics
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            
            # Trade statistics
            'avg_hold_period_days': avg_hold_period,
            'exit_reason_breakdown': exit_reasons,
            
            # Sprint 18 Success Criteria
            'success_criteria': success_criteria,
            'criteria_met': criteria_met,
            'all_criteria_met': all_criteria_met,
            
            # Additional info
            'contracts_per_trade': self.contracts_per_trade,
            'max_concurrent_positions': self.max_positions,
            'commission_per_contract': self.commission_per_contract
        }


def main():
    """
    Run the Sprint 18 Bull Call Spread backtest
    """
    print("=" * 80)
    print("SPRINT 18: BULL CALL SPREAD HISTORICAL BACKTEST")
    print("=" * 80)
    
    # Initialize backtest
    backtest = HistoricalBullCallSpreadBacktest(initial_capital=100000.0)
    
    # Run backtest for the specified period
    start_date = "2019-01-01"
    end_date = "2023-12-31"
    
    logger.info("Starting 5-year Bull Call Spread backtest...")
    results = backtest.run_backtest(start_date, end_date)
    
    # Print results
    print(f"\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    
    print(f"Period: {results['backtest_period']}")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.1f}%")
    print(f"Total Return: {results['total_return_pct']:.1f}%")
    print(f"Annualized Return: {results['annualized_return_pct']:.1f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.1f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Average Trade P&L: ${results['avg_trade_pnl']:.2f}")
    print(f"Best Trade: ${results['best_trade']:.2f}")
    print(f"Worst Trade: ${results['worst_trade']:.2f}")
    
    print(f"\n" + "="*60)
    print("SPRINT 18 SUCCESS CRITERIA EVALUATION")
    print("="*60)
    
    criteria = results['success_criteria']
    met = results['criteria_met']
    
    print(f"[X] Annualized Return > {criteria['post_cost_annualized_return_target']:.1f}%: "
          f"{results['annualized_return_pct']:.1f}% {'PASS' if met['annualized_return_met'] else 'FAIL'}")
    
    print(f"[X] Sharpe Ratio > {criteria['post_cost_sharpe_ratio_target']:.1f}: "
          f"{results['sharpe_ratio']:.2f} {'PASS' if met['sharpe_ratio_met'] else 'FAIL'}")
    
    print(f"[X] Max Drawdown < {criteria['max_drawdown_target']:.1f}%: "
          f"{abs(results['max_drawdown_pct']):.1f}% {'PASS' if met['max_drawdown_met'] else 'FAIL'}")
    
    print(f"[X] Win Rate > {criteria['win_rate_target']:.1f}%: "
          f"{results['win_rate']:.1f}% {'PASS' if met['win_rate_met'] else 'FAIL'}")
    
    print(f"\n>>> OVERALL VERDICT: {'SUCCESS - All criteria met!' if results['all_criteria_met'] else 'FAILURE - Criteria not met'}")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sprint18_bull_call_spread_results_{timestamp}.json"
    
    # Convert datetime objects to strings for JSON serialization
    json_results = results.copy()
    
    with open(filename, 'w') as f:
        json.dump(json_results, f, indent=2, default=str)
    
    logger.info(f"Results saved to {filename}")
    
    print(f"\nBacktest completed! Results saved to {filename}")
    print("="*80)


if __name__ == "__main__":
    main()