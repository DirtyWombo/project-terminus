"""
Transaction Cost Analysis (TCA) - Tier 1 Implementation
======================================================

Expert guidance: "You cannot know if your strategy is truly profitable if you don't 
know what you're paying in slippage. This is the single most overlooked cost for new quants."

Day 1 Implementation: Basic slippage tracking after every trade
Upgrade Path: Full TCA engine with comprehensive cost breakdown
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from sqlalchemy import text

from .models import db, Trade, Price

logging.basicConfig(level=logging.INFO)

@dataclass
class TradeCostAnalysis:
    """Container for trade cost analysis results"""
    trade_id: int
    symbol: str
    side: str
    quantity: float
    decision_price: float
    execution_price: float
    decision_time: datetime
    execution_time: datetime
    
    # Basic cost metrics (Day 1 implementation)
    slippage_dollars: float
    slippage_bps: float
    execution_delay_seconds: float
    
    # Extended cost metrics (upgrade path)
    commission_dollars: float = 0.0
    commission_bps: float = 0.0
    market_impact_dollars: float = 0.0
    market_impact_bps: float = 0.0
    
    # Quality metrics
    execution_quality_score: float = 0.0
    cost_category: str = "UNKNOWN"

class BasicTransactionCostAnalyzer:
    """
    Day 1 Implementation of Transaction Cost Analysis
    
    Simple but effective - tracks the single most important cost metric:
    slippage_cost = average_fill_price - price_at_decision_time
    """
    
    def __init__(self):
        self.cost_thresholds = {
            'excellent': 5,    # < 5 bps
            'good': 15,        # < 15 bps  
            'acceptable': 30,  # < 30 bps
            'poor': 50,        # < 50 bps
            'terrible': 100    # >= 100 bps
        }
    
    def analyze_trade_cost(self, trade: Trade, decision_price: float, decision_time: datetime) -> TradeCostAnalysis:
        """
        Analyze transaction costs for a single trade
        
        Args:
            trade: Trade object from database
            decision_price: Price when trade decision was made
            decision_time: Time when trade decision was made
            
        Returns:
            TradeCostAnalysis object with cost breakdown
        """
        # Basic slippage calculation (Day 1 implementation)
        execution_price = float(trade.price)
        quantity = float(trade.amount)
        
        # Calculate slippage based on trade direction
        if trade.type == 'BUY':
            slippage_dollars = (execution_price - decision_price) * quantity
        else:  # SELL
            slippage_dollars = (decision_price - execution_price) * quantity
        
        # Calculate slippage in basis points
        slippage_bps = (slippage_dollars / (decision_price * quantity)) * 10000
        
        # Calculate execution delay
        execution_delay = (trade.timestamp - decision_time).total_seconds()
        
        # Create analysis object
        analysis = TradeCostAnalysis(
            trade_id=trade.id,
            symbol=trade.symbol,
            side=trade.type,
            quantity=quantity,
            decision_price=decision_price,
            execution_price=execution_price,
            decision_time=decision_time,
            execution_time=trade.timestamp,
            slippage_dollars=slippage_dollars,
            slippage_bps=slippage_bps,
            execution_delay_seconds=execution_delay,
            execution_quality_score=self._calculate_execution_quality_score(slippage_bps),
            cost_category=self._categorize_execution_cost(slippage_bps)
        )
        
        # Log the analysis (Day 1 implementation)
        self._log_trade_cost_analysis(analysis)
        
        return analysis
    
    def _calculate_execution_quality_score(self, slippage_bps: float) -> float:
        """Calculate execution quality score from 0-100"""
        if slippage_bps < 0:
            return 100  # Positive slippage is perfect
        elif slippage_bps < 5:
            return 90
        elif slippage_bps < 15:
            return 75
        elif slippage_bps < 30:
            return 60
        elif slippage_bps < 50:
            return 40
        elif slippage_bps < 100:
            return 20
        else:
            return 0
    
    def _categorize_execution_cost(self, slippage_bps: float) -> str:
        """Categorize execution cost quality"""
        if slippage_bps < 0:
            return "EXCELLENT"
        elif slippage_bps < self.cost_thresholds['excellent']:
            return "EXCELLENT"
        elif slippage_bps < self.cost_thresholds['good']:
            return "GOOD"
        elif slippage_bps < self.cost_thresholds['acceptable']:
            return "ACCEPTABLE"
        elif slippage_bps < self.cost_thresholds['poor']:
            return "POOR"
        else:
            return "TERRIBLE"
    
    def _log_trade_cost_analysis(self, analysis: TradeCostAnalysis):
        """Log trade cost analysis for immediate visibility"""
        log_message = (
            f"TCA | {analysis.symbol} {analysis.side} | "
            f"Slippage: {analysis.slippage_bps:.1f}bps "
            f"(${analysis.slippage_dollars:.2f}) | "
            f"Quality: {analysis.cost_category} | "
            f"Delay: {analysis.execution_delay_seconds:.1f}s"
        )
        
        if analysis.slippage_bps > self.cost_thresholds['poor']:
            logging.warning(f"HIGH SLIPPAGE: {log_message}")
        elif analysis.slippage_bps > self.cost_thresholds['acceptable']:
            logging.info(f"MODERATE SLIPPAGE: {log_message}")
        else:
            logging.info(f"GOOD EXECUTION: {log_message}")
    
    def get_recent_cost_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of recent trading costs"""
        try:
            # Get recent trades
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_trades = Trade.query.filter(Trade.timestamp >= cutoff_date).all()
            
            if not recent_trades:
                return {
                    'error': f'No trades found in last {days} days',
                    'total_trades': 0
                }
            
            # For Day 1 implementation, we'll estimate slippage using available data
            cost_analyses = []
            
            for trade in recent_trades:
                # Estimate decision price using closest price data
                decision_price = self._estimate_decision_price(trade)
                if decision_price:
                    analysis = self.analyze_trade_cost(trade, decision_price, trade.timestamp)
                    cost_analyses.append(analysis)
            
            if not cost_analyses:
                return {
                    'error': 'Could not analyze any trades',
                    'total_trades': len(recent_trades)
                }
            
            # Calculate summary statistics
            total_slippage_dollars = sum(a.slippage_dollars for a in cost_analyses)
            total_notional = sum(a.quantity * a.decision_price for a in cost_analyses)
            avg_slippage_bps = np.mean([a.slippage_bps for a in cost_analyses])
            avg_execution_quality = np.mean([a.execution_quality_score for a in cost_analyses])
            
            # Cost breakdown by category
            cost_breakdown = {}
            for analysis in cost_analyses:
                category = analysis.cost_category
                if category not in cost_breakdown:
                    cost_breakdown[category] = {'count': 0, 'total_slippage': 0}
                cost_breakdown[category]['count'] += 1
                cost_breakdown[category]['total_slippage'] += analysis.slippage_dollars
            
            return {
                'period': f'Last {days} days',
                'total_trades': len(cost_analyses),
                'total_slippage_dollars': total_slippage_dollars,
                'total_notional': total_notional,
                'slippage_percentage': (total_slippage_dollars / total_notional) * 100 if total_notional > 0 else 0,
                'average_slippage_bps': avg_slippage_bps,
                'average_execution_quality': avg_execution_quality,
                'cost_breakdown': cost_breakdown,
                'worst_execution': max(cost_analyses, key=lambda x: x.slippage_bps, default=None),
                'best_execution': min(cost_analyses, key=lambda x: x.slippage_bps, default=None)
            }
            
        except Exception as e:
            logging.error(f"Error generating cost summary: {e}")
            return {'error': str(e)}
    
    def _estimate_decision_price(self, trade: Trade) -> Optional[float]:
        """Estimate decision price using closest price data"""
        try:
            # Get price data around trade time
            price_data = Price.query.filter(
                Price.symbol == trade.symbol,
                Price.timestamp <= trade.timestamp,
                Price.timestamp >= trade.timestamp - timedelta(minutes=5)
            ).order_by(Price.timestamp.desc()).first()
            
            if price_data:
                return float(price_data.close)
            else:
                # Fallback to execution price (no slippage calculation possible)
                return float(trade.price)
                
        except Exception as e:
            logging.error(f"Error estimating decision price for trade {trade.id}: {e}")
            return None
    
    def create_cost_alert(self, analysis: TradeCostAnalysis) -> Optional[str]:
        """Create cost alert for high slippage trades"""
        if analysis.slippage_bps > self.cost_thresholds['poor']:
            return (
                f"🚨 HIGH SLIPPAGE ALERT\n"
                f"Trade: {analysis.symbol} {analysis.side}\n"
                f"Slippage: {analysis.slippage_bps:.1f}bps (${analysis.slippage_dollars:.2f})\n"
                f"Quality: {analysis.cost_category}\n"
                f"Execution delay: {analysis.execution_delay_seconds:.1f}s"
            )
        return None


class TCAReportGenerator:
    """Generate TCA reports for Slack integration"""
    
    def __init__(self, analyzer: BasicTransactionCostAnalyzer):
        self.analyzer = analyzer
    
    def generate_daily_tca_report(self) -> str:
        """Generate daily TCA report for Slack"""
        cost_summary = self.analyzer.get_recent_cost_summary(days=1)
        
        if 'error' in cost_summary:
            return f"📊 Daily TCA Report\n❌ {cost_summary['error']}"
        
        report = f"""📊 Daily Transaction Cost Analysis
        
🔍 **Execution Summary:**
• Total Trades: {cost_summary['total_trades']}
• Average Slippage: {cost_summary['average_slippage_bps']:.1f}bps
• Total Slippage Cost: ${cost_summary['total_slippage_dollars']:.2f}
• Execution Quality: {cost_summary['average_execution_quality']:.1f}/100

💰 **Cost Breakdown:**"""
        
        for category, data in cost_summary['cost_breakdown'].items():
            report += f"\n• {category}: {data['count']} trades (${data['total_slippage']:.2f})"
        
        if cost_summary['worst_execution']:
            worst = cost_summary['worst_execution']
            report += f"\n\n⚠️ **Worst Execution:**\n{worst.symbol} {worst.side}: {worst.slippage_bps:.1f}bps"
        
        if cost_summary['best_execution']:
            best = cost_summary['best_execution']
            report += f"\n\n✅ **Best Execution:**\n{best.symbol} {best.side}: {best.slippage_bps:.1f}bps"
        
        return report
    
    def generate_weekly_tca_report(self) -> str:
        """Generate weekly TCA report for performance review"""
        cost_summary = self.analyzer.get_recent_cost_summary(days=7)
        
        if 'error' in cost_summary:
            return f"📊 Weekly TCA Report\n❌ {cost_summary['error']}"
        
        report = f"""📊 Weekly Transaction Cost Analysis
        
🔍 **7-Day Performance:**
• Total Trades: {cost_summary['total_trades']}
• Average Slippage: {cost_summary['average_slippage_bps']:.1f}bps
• Total Slippage Cost: ${cost_summary['total_slippage_dollars']:.2f}
• Slippage % of Notional: {cost_summary['slippage_percentage']:.3f}%
• Average Quality Score: {cost_summary['average_execution_quality']:.1f}/100

💰 **Cost Distribution:**"""
        
        for category, data in cost_summary['cost_breakdown'].items():
            percentage = (data['count'] / cost_summary['total_trades']) * 100
            report += f"\n• {category}: {data['count']} trades ({percentage:.1f}%)"
        
        # Add recommendations
        if cost_summary['average_slippage_bps'] > 30:
            report += "\n\n💡 **Recommendations:**\n• Consider implementing adaptive execution algorithms\n• Review order sizes and timing"
        elif cost_summary['average_slippage_bps'] > 15:
            report += "\n\n💡 **Recommendations:**\n• Monitor execution timing during high volatility\n• Consider order size optimization"
        else:
            report += "\n\n✅ **Status:** Execution quality is good - continue monitoring"
        
        return report


# Factory function for easy integration
def create_tca_analyzer() -> BasicTransactionCostAnalyzer:
    """Create configured TCA analyzer instance"""
    return BasicTransactionCostAnalyzer()


# Example usage for integration
if __name__ == "__main__":
    # Create analyzer
    tca_analyzer = create_tca_analyzer()
    
    # Generate sample report
    report_generator = TCAReportGenerator(tca_analyzer)
    print(report_generator.generate_daily_tca_report())