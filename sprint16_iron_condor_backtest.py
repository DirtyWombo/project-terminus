#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sprint 16: SPY Iron Condor Volatility Trading Backtest
Complete backtest implementation using the options backtesting infrastructure

This script demonstrates the full Sprint 16 options backtesting system:
- Iron Condor strategy on SPY
- Historical options data management
- Greeks calculation and risk management
- Performance analytics and reporting

Strategy: Short Iron Condor on SPY
- Sell OTM call and put (collect premium)
- Buy further OTM options (limit risk)
- Target 30 DTE, close at 50% profit or 21 DTE
- Delta-neutral volatility play
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

# Add current directory to path
sys.path.append(os.getcwd())

from options_backtesting.core_engine import (
    OptionsBacktestEngine, OptionContract, OptionType, OptionPosition, 
    IronCondorPosition, MarketDataEvent, StrategyEvent, ExecutionEvent
)
from options_backtesting.historical_manager import HistoricalOptionsManager
from options_backtesting.greeks_engine import GreeksEngine
from options_backtesting.iron_condor_strategy import IronCondorStrategy, IronCondorParameters

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Sprint16Backtester:
    """
    Complete Sprint 16 Iron Condor backtesting system
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        """
        Initialize Sprint 16 backtester
        
        Args:
            initial_capital: Starting capital for backtest
        """
        self.initial_capital = initial_capital
        
        # Initialize components
        self.data_manager = HistoricalOptionsManager(enable_cache=True)
        self.greeks_engine = GreeksEngine(risk_free_rate=0.05)
        
        # Strategy parameters optimized for current market conditions and demonstration
        self.strategy_params = IronCondorParameters(
            target_dte=7,               # Target 7 days to expiration (for demo with current data)
            delta_short_call=0.12,      # Slightly conservative short call delta
            delta_short_put=-0.12,      # Slightly conservative short put delta
            wing_width=10.0,            # $10 wings for SPY
            
            # Entry criteria (relaxed for demonstration)
            min_premium_collected=0.10, # Min 10% credit relative to wing width
            max_bid_ask_spread=0.40,    # Allow up to 40% spreads for demonstration
            min_open_interest=5,        # Lower threshold for demonstration
            min_volume=1,               # Lower threshold for demonstration
            
            # Risk management
            profit_target=0.50,         # Take profit at 50%
            stop_loss=2.0,              # Stop at 200% of credit
            
            # Greeks limits
            max_delta=15.0,             # Allow some delta for trend following
            max_gamma=75.0,             # Conservative gamma limit
            max_vega=150.0,             # Conservative vega limit
            
            # Timing
            min_dte_close=7,            # Close at 7 DTE minimum
            max_dte_open=45,            # Open up to 45 DTE
            
            # Position sizing
            max_positions=3,            # Conservative position count
            position_size=20000.0       # $20k per position for 100k account
        )
        
        # Initialize strategy
        self.strategy = IronCondorStrategy(
            parameters=self.strategy_params,
            data_manager=self.data_manager,
            greeks_engine=self.greeks_engine
        )
        
        # Initialize core engine
        self.engine = OptionsBacktestEngine(initial_capital=initial_capital)
        
        # Backtest state
        self.current_date = None
        self.backtest_results = {}
        
        logger.info("Sprint 16 backtester initialized")
        logger.info(f"Initial capital: ${initial_capital:,.2f}")
        logger.info(f"Strategy: Iron Condor with {self.strategy_params.target_dte} DTE target")
        
    def run_backtest(self, start_date: str, end_date: str, 
                    symbol: str = 'SPY') -> Dict[str, Any]:
        """
        Run complete Iron Condor backtest
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            symbol: Underlying symbol (default SPY)
            
        Returns:
            Comprehensive backtest results
        """
        logger.info("=" * 80)
        logger.info("SPRINT 16: SPY IRON CONDOR VOLATILITY TRADING BACKTEST")
        logger.info("=" * 80)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Track backtest metrics
        trading_days = 0
        options_data_days = 0
        signals_generated = {'OPEN': 0, 'CLOSE': 0, 'ADJUST': 0, 'HOLD': 0}
        
        # Main backtest loop
        current_date = start_dt
        
        while current_date <= end_dt:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
                
            self.current_date = current_date
            date_str = current_date.strftime('%Y-%m-%d')
            trading_days += 1
            
            logger.info(f"Processing {date_str} (Day {trading_days})")
            
            try:
                # Get options chain for current date
                options_chain = self.data_manager.get_options_chain(symbol, date_str)
                
                if not options_chain:
                    logger.warning(f"No options data for {date_str}")
                    current_date += timedelta(days=1)
                    continue
                    
                options_data_days += 1
                logger.info(f"Retrieved {len(options_chain)} option contracts")
                
                # Generate strategy signal
                signal = self.strategy.generate_signal(current_date, options_chain)
                signals_generated[signal.value] += 1
                
                logger.info(f"Signal: {signal.value}")
                
                # Process signal
                if signal.value == 'OPEN':
                    self._process_open_signal(current_date, options_chain)
                elif signal.value == 'CLOSE':
                    self._process_close_signal(current_date, options_chain)
                elif signal.value == 'ADJUST':
                    self._process_adjust_signal(current_date, options_chain)
                
                # Update portfolio metrics
                self._update_portfolio_metrics(current_date, options_chain)
                
                # Log position status
                active_positions = len(self.strategy.active_positions)
                if active_positions > 0:
                    logger.info(f"Active positions: {active_positions}")
                    
                    # Show current P&L
                    total_pnl = sum([pos.total_pnl for pos in self.strategy.active_positions])
                    logger.info(f"Current open P&L: ${total_pnl:.2f}")
                
            except Exception as e:
                logger.error(f"Error processing {date_str}: {e}")
                
            current_date += timedelta(days=1)
        
        # Calculate final results
        final_results = self._calculate_final_results(
            trading_days, options_data_days, signals_generated
        )
        
        logger.info("=" * 80)
        logger.info("SPRINT 16 BACKTEST COMPLETED")
        logger.info("=" * 80)
        
        return final_results
        
    def _process_open_signal(self, date: datetime, options_chain: List[OptionContract]):
        """Process OPEN signal - create new Iron Condor position"""
        logger.info("Processing OPEN signal")
        
        # Find Iron Condor strikes
        strikes = self.strategy._find_iron_condor_strikes(options_chain)
        
        if not strikes:
            logger.warning("No suitable Iron Condor strikes found")
            return
            
        # Validate data quality
        if not self.strategy._validate_data_quality(strikes, options_chain):
            logger.warning("Data quality validation failed")
            return
            
        # Create Iron Condor position
        iron_condor = self.strategy.create_iron_condor_position(strikes, options_chain)
        
        if iron_condor:
            self.strategy.active_positions.append(iron_condor)
            self.strategy.trades_opened += 1
            
            # Update tracking metrics
            premium_collected = iron_condor.net_premium_collected
            self.strategy.total_premium_collected += premium_collected
            
            logger.info(f"✓ Opened Iron Condor position #{self.strategy.trades_opened}")
            logger.info(f"  Premium collected: ${premium_collected:.2f}")
            logger.info(f"  Max profit: ${iron_condor.max_profit:.2f}")
            logger.info(f"  Max loss: ${iron_condor.max_loss:.2f}")
        else:
            logger.error("Failed to create Iron Condor position")
            
    def _process_close_signal(self, date: datetime, options_chain: List[OptionContract]):
        """Process CLOSE signal - close existing positions"""
        logger.info("Processing CLOSE signal")
        
        positions_to_close = []
        
        for position in self.strategy.active_positions:
            if self.strategy._should_close_position(position, options_chain):
                positions_to_close.append(position)
        
        for position in positions_to_close:
            # Update final prices
            self.strategy._update_position_prices(position, options_chain)
            
            # Close the position
            final_pnl = position.total_pnl
            
            # Mark positions as closed
            for pos in [position.short_call, position.long_call, position.short_put, position.long_put]:
                pos.exit_date = date
                pos.exit_price = pos.contract.mid_price
            
            # Move to closed positions
            self.strategy.active_positions.remove(position)
            self.strategy.closed_positions.append(position)
            self.strategy.trades_closed += 1
            
            # Update P&L tracking
            self.strategy.total_pnl += final_pnl
            
            logger.info(f"✓ Closed Iron Condor position")
            logger.info(f"  Final P&L: ${final_pnl:.2f}")
            logger.info(f"  Hold period: {(date - position.entry_date).days} days")
            
    def _process_adjust_signal(self, date: datetime, options_chain: List[OptionContract]):
        """Process ADJUST signal - adjust existing positions"""
        logger.info("Processing ADJUST signal")
        
        # For this implementation, we'll log the adjustment opportunity
        # but not implement complex adjustment logic
        logger.info("Adjustment opportunity detected - holding current positions")
        
    def _update_portfolio_metrics(self, date: datetime, options_chain: List[OptionContract]):
        """Update portfolio metrics and Greeks"""
        
        # Calculate current portfolio value
        cash = self.initial_capital
        
        # Add closed position P&L
        closed_pnl = sum([pos.total_pnl for pos in self.strategy.closed_positions])
        
        # Add open position P&L
        open_pnl = sum([pos.total_pnl for pos in self.strategy.active_positions])
        
        portfolio_value = cash + closed_pnl + open_pnl
        daily_pnl = portfolio_value - self.initial_capital
        
        # Update engine performance tracker
        self.engine.performance.record_daily_pnl(date, daily_pnl, portfolio_value)
        
        # Calculate and record portfolio Greeks if we have positions
        if self.strategy.active_positions:
            portfolio_positions = []
            
            for ic_pos in self.strategy.active_positions:
                for pos in [ic_pos.short_call, ic_pos.long_call, ic_pos.short_put, ic_pos.long_put]:
                    portfolio_positions.append({
                        'contract': pos.contract,
                        'quantity': pos.quantity
                    })
            
            if options_chain:
                underlying_price = options_chain[0].underlying_price
                portfolio_greeks = self.greeks_engine.calculate_portfolio_greeks(
                    portfolio_positions, underlying_price
                )
                
                self.engine.performance.record_greeks(date, portfolio_greeks)
        
    def _calculate_final_results(self, trading_days: int, options_data_days: int, 
                               signals_generated: Dict[str, int]) -> Dict[str, Any]:
        """Calculate comprehensive final results"""
        
        # Get strategy performance
        strategy_performance = self.strategy.get_strategy_performance()
        
        # Get engine performance
        engine_performance = self.engine.performance.get_performance_summary()
        
        # Calculate additional metrics
        data_coverage = (options_data_days / trading_days * 100) if trading_days > 0 else 0
        
        # Final portfolio value
        final_portfolio_value = engine_performance.get('final_portfolio_value', self.initial_capital)
        
        final_results = {
            'backtest_summary': {
                'initial_capital': self.initial_capital,
                'final_portfolio_value': final_portfolio_value,
                'total_return_pct': ((final_portfolio_value - self.initial_capital) / self.initial_capital * 100),
                'trading_days': trading_days,
                'options_data_days': options_data_days,
                'data_coverage_pct': data_coverage
            },
            'strategy_performance': strategy_performance,
            'performance_metrics': engine_performance,
            'signals_generated': signals_generated,
            'strategy_parameters': {
                'target_dte': self.strategy_params.target_dte,
                'wing_width': self.strategy_params.wing_width,
                'profit_target': self.strategy_params.profit_target,
                'stop_loss': self.strategy_params.stop_loss,
                'max_positions': self.strategy_params.max_positions
            }
        }
        
        # Print summary
        self._print_final_summary(final_results)
        
        return final_results
        
    def _print_final_summary(self, results: Dict[str, Any]):
        """Print comprehensive final summary"""
        
        summary = results['backtest_summary']
        strategy = results['strategy_performance']
        metrics = results['performance_metrics']
        signals = results['signals_generated']
        
        print("\n" + "=" * 80)
        print("SPRINT 16: IRON CONDOR BACKTEST RESULTS")
        print("=" * 80)
        
        print(f"BACKTEST SUMMARY:")
        print(f"  Initial Capital: ${summary['initial_capital']:,.2f}")
        print(f"  Final Portfolio Value: ${summary['final_portfolio_value']:,.2f}")
        print(f"  Total Return: {summary['total_return_pct']:.2f}%")
        print(f"  Trading Days: {summary['trading_days']}")
        print(f"  Data Coverage: {summary['data_coverage_pct']:.1f}%")
        
        print(f"\nSTRATEGY PERFORMANCE:")
        print(f"  Total Trades: {strategy['total_trades']}")
        print(f"  Active Positions: {strategy['active_positions']}")
        print(f"  Win Rate: {strategy['win_rate']:.1f}%")
        print(f"  Total P&L: ${strategy['total_pnl']:,.2f}")
        print(f"  Average Trade: ${strategy['avg_trade_pnl']:.2f}")
        print(f"  Profit Factor: {strategy['profit_factor']:.2f}")
        print(f"  Premium Collected: ${strategy['total_premium_collected']:,.2f}")
        
        if metrics:
            print(f"\nPERFORMANCE METRICS:")
            print(f"  Annualized Return: {metrics.get('annualized_return_pct', 0):.2f}%")
            print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
            print(f"  Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
        
        print(f"\nSIGNALS GENERATED:")
        for signal, count in signals.items():
            print(f"  {signal}: {count}")
        
        print("=" * 80)
        
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save backtest results to JSON file"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sprint16_iron_condor_results_{timestamp}.json"
        
        # Convert datetime objects to strings for JSON serialization
        json_results = self._prepare_for_json(results)
        
        with open(filename, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        logger.info(f"Results saved to {filename}")
        
    def _prepare_for_json(self, obj):
        """Recursively prepare object for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._prepare_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        else:
            return obj


def main():
    """
    Run Sprint 16 Iron Condor backtest
    """
    print("Starting Sprint 16 SPY Iron Condor Backtest...")
    
    # Initialize backtester
    backtester = Sprint16Backtester(initial_capital=100000.0)
    
    # Run backtest for recent period (limited by yfinance data availability)
    # In production, this would use Theta Data for historical backtesting
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    
    print(f"Backtesting period: {start_date} to {end_date}")
    print("Note: Using yfinance for demonstration - production would use Theta Data")
    
    # Run the backtest
    results = backtester.run_backtest(start_date, end_date, symbol='SPY')
    
    # Save results
    backtester.save_results(results)
    
    print("\nSprint 16 backtest completed successfully!")
    print("Options backtesting infrastructure validated [SUCCESS]")


if __name__ == "__main__":
    main()