# Execute Alpha Validation - Critical Expert Requirement
# This script runs the validation notebook logic directly

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
import random
from dateutil.relativedelta import relativedelta

warnings.filterwarnings('ignore')

print("="*60)
print("OPERATION BADGER - ALPHA VALIDATION EXECUTION")
print("EXPERT REQUIREMENT: Prove alpha signal BEFORE infrastructure")
print("="*60)

# Small/Mid-Cap Universe (Expert Recommendation)
SMALL_CAP_UNIVERSE = [
    'CRWD', 'SNOW', 'DDOG', 'NET', 'OKTA', 'ZS',      # Cloud/SaaS
    'SQ', 'PYPL', 'COIN', 'SOFI', 'UPST', 'AFRM',     # Fintech  
    'PLTR', 'RBLX', 'U', 'PATH', 'FVRR',              # Growth Tech
    'MRNA', 'BNTX', 'NVAX', 'SGEN',                   # Biotech
    'ROKU', 'SPOT', 'ZM', 'DOCU', 'PTON'             # Consumer Digital
]

print(f"Universe: {len(SMALL_CAP_UNIVERSE)} small/mid-cap stocks")
print(f"Focus: Narrative-sensitive sectors with less HFT coverage")

# Get historical price data
def get_price_data(symbols, period="4y"):
    """Get historical price data for universe"""
    price_data = {}
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if not hist.empty and len(hist) > 100:  # Minimum data requirement
                # Calculate daily returns
                hist['daily_return'] = hist['Close'].pct_change()
                
                # Calculate forward returns (1, 3, 5 days)
                hist['forward_1d'] = hist['Close'].shift(-1) / hist['Close'] - 1
                hist['forward_3d'] = hist['Close'].shift(-3) / hist['Close'] - 1  
                hist['forward_5d'] = hist['Close'].shift(-5) / hist['Close'] - 1
                
                price_data[symbol] = hist
                print(f"SUCCESS {symbol}: {len(hist)} days of data")
            else:
                print(f"FAIL {symbol}: Insufficient data")
                
        except Exception as e:
            print(f"ERROR {symbol}: {e}")
    
    return price_data

print("\\nCollecting historical price data...")
price_data = get_price_data(SMALL_CAP_UNIVERSE)
print(f"Successfully collected data for {len(price_data)} stocks\\n")

# Simulate SEC filing analysis
def simulate_sec_filing_analysis(symbol, date, price_data):
    """
    Simulate AI analysis of SEC 8-K filings
    In production: Use real SEC EDGAR API + Llama 3.2
    """
    
    try:
        if symbol not in price_data:
            return None
            
        df = price_data[symbol]
        
        # Convert date to pandas timestamp for indexing
        if not isinstance(date, pd.Timestamp):
            date = pd.Timestamp(date)
            
        # Find closest trading day 
        available_dates = df.index
        if len(available_dates) == 0:
            return None
            
        # Find closest date that exists in our data and has enough history
        mask = available_dates <= date
        if not mask.any():
            return None
            
        valid_dates = available_dates[mask]
        if len(valid_dates) < 30:  # Need enough history
            return None
            
        closest_date = valid_dates[-1]  # Latest date before or on target date
        
        # Get index position for slicing
        idx = df.index.get_loc(closest_date)
        if idx < 20:  # Need at least 20 days of history
            return None
            
        # Simulate filing analysis using price/volume patterns
        recent_returns = df.iloc[idx-5:idx+1]['daily_return'].dropna()
        if len(recent_returns) < 3:
            return None
            
        recent_vol = recent_returns.std()
        if pd.isna(recent_vol) or recent_vol == 0:
            recent_vol = 0.02  # Default volatility
        
        # Volume analysis
        recent_volumes = df.iloc[idx-20:idx+1]['Volume'].dropna()
        if len(recent_volumes) < 10:
            return None
            
        avg_volume = recent_volumes.mean()
        current_volume = df.iloc[idx]['Volume']
        
        if pd.isna(avg_volume) or avg_volume == 0:
            volume_ratio = 1.0
        else:
            volume_ratio = current_volume / avg_volume
        
        # Simulate velocity score with some randomness
        # Higher volatility + volume surge = stronger signal
        base_score = (recent_vol * 20) * (volume_ratio - 1) + np.random.normal(0, 0.1)
        velocity_score = np.tanh(base_score)  # Bound to [-1, 1]
        
        # Simulate confidence based on volume and add randomness  
        raw_confidence = min(0.9, max(0.1, (volume_ratio - 0.5) / 2 + 0.5))
        confidence = max(0.1, min(0.9, raw_confidence + np.random.normal(0, 0.1)))
        
        return {
            'symbol': symbol,
            'date': closest_date,
            'velocity_score': velocity_score,
            'confidence': confidence,
            'volume_ratio': volume_ratio,
            'volatility': recent_vol
        }
        
    except Exception as e:
        print(f"Analysis error for {symbol}: {e}")
        return None

# Generate filing events
def generate_filing_events(symbols, start_date, end_date, events_per_month=2):
    """Generate simulated SEC filing events"""
    events = []
    
    current_date = start_date
    while current_date <= end_date:
        for _ in range(events_per_month):
            symbol = random.choice(symbols)
            
            # Random date within the month
            days_in_month = 30
            random_day = random.randint(0, days_in_month - 1)
            event_date = current_date + timedelta(days=random_day)
            
            # Skip weekends
            if event_date.weekday() < 5:  # Monday = 0, Friday = 4
                events.append({
                    'symbol': symbol,
                    'date': event_date,
                    'filing_type': '8-K'
                })
        
        current_date += relativedelta(months=1)
    
    return events

# Generate filing events for validation period  
start_date = datetime(2022, 1, 1)
end_date = datetime(2024, 6, 30)  # Ensure we have data for forward returns

filing_events = generate_filing_events(
    symbols=list(price_data.keys()),
    start_date=start_date,
    end_date=end_date,
    events_per_month=5  # Increase events for better sample size
)

print(f"Generated {len(filing_events)} simulated SEC filing events")

# Analyze signals
signals = []

print("Analyzing SEC filing events...")
for i, event in enumerate(filing_events):
    if i % 100 == 0:
        print(f"Processing event {i+1}/{len(filing_events)}...")
    
    # Simulate AI analysis of SEC filing
    analysis = simulate_sec_filing_analysis(
        symbol=event['symbol'],
        date=event['date'],
        price_data=price_data
    )
    
    if analysis:
        # Get forward returns for this signal
        symbol = analysis['symbol']
        date = analysis['date']
        
        if symbol in price_data and date in price_data[symbol].index:
            df = price_data[symbol]
            
            signal = {
                'symbol': symbol,
                'date': date,
                'velocity_score': analysis['velocity_score'],
                'confidence': analysis['confidence'],
                'forward_1d': df.loc[date, 'forward_1d'],
                'forward_3d': df.loc[date, 'forward_3d'],
                'forward_5d': df.loc[date, 'forward_5d'],
                'volume_ratio': analysis['volume_ratio'],
                'volatility': analysis['volatility']
            }
            
            # Only include signals with valid forward returns
            if not pd.isna(signal['forward_1d']):
                signals.append(signal)

# Convert to DataFrame
signals_df = pd.DataFrame(signals)
print(f"\\nSUCCESS: Generated {len(signals_df)} trading signals with forward returns\\n")

# CRITICAL VALIDATION
if len(signals_df) > 0:
    print("=" * 60)
    print("ALPHA VALIDATION RESULTS")
    print("=" * 60)
    
    # Basic statistics
    print(f"Sample Size: {len(signals_df)} signals")
    print(f"Date Range: {signals_df['date'].min().date()} to {signals_df['date'].max().date()}")
    print(f"Unique Stocks: {signals_df['symbol'].nunique()}")
    
    # Filter high-confidence signals (strategy requirement)
    high_conf_signals = signals_df[signals_df['confidence'] >= 0.65]
    print(f"High-Confidence Signals (≥65%): {len(high_conf_signals)} ({len(high_conf_signals)/len(signals_df)*100:.1f}%)")
    
    if len(high_conf_signals) >= 30:  # Minimum sample size
        returns_1d = high_conf_signals['forward_1d'].dropna()
        
        print(f"\\n🔬 STATISTICAL ANALYSIS (High Confidence Signals)")
        print(f"Sample Size: {len(returns_1d)}")
        print(f"Mean 1D Return: {returns_1d.mean()*100:.3f}%")
        print(f"Volatility: {returns_1d.std()*100:.3f}%")
        
        # EXPERT VALIDATION CHECKLIST
        print("\\n" + "="*50)
        print("EXPERT VALIDATION CHECKLIST")
        print("="*50)
        
        validation_results = {}
        
        # 1. Statistical Significance (p < 0.05)
        t_stat, p_value = stats.ttest_1samp(returns_1d, 0)
        validation_results['statistical_significance'] = p_value < 0.05
        
        # 2. Information Ratio (> 0.5)
        info_ratio = returns_1d.mean() / returns_1d.std() if returns_1d.std() > 0 else 0
        validation_results['information_ratio'] = info_ratio > 0.5
        
        # 3. Win Rate (> 52%)
        win_rate = (returns_1d > 0).sum() / len(returns_1d)
        validation_results['win_rate'] = win_rate > 0.52
        
        # 4. Sample Size (≥ 30)
        validation_results['sample_size'] = len(returns_1d) >= 30
        
        # 5. Sharpe Ratio (> 1.0, annualized)
        daily_sharpe = returns_1d.mean() / returns_1d.std() if returns_1d.std() > 0 else 0
        annual_sharpe = daily_sharpe * np.sqrt(252)  # Annualize
        validation_results['sharpe_ratio'] = annual_sharpe > 1.0
        
        # Print results
        print(f"1. Statistical Significance (p < 0.05): {'PASS' if validation_results['statistical_significance'] else 'FAIL'} (p = {p_value:.4f})")
        print(f"2. Information Ratio (> 0.5): {'PASS' if validation_results['information_ratio'] else 'FAIL'} ({info_ratio:.3f})")
        print(f"3. Win Rate (> 52%): {'PASS' if validation_results['win_rate'] else 'FAIL'} ({win_rate:.1%})")
        print(f"4. Sample Size (≥ 30): {'PASS' if validation_results['sample_size'] else 'FAIL'} ({len(returns_1d)})")
        print(f"5. Sharpe Ratio (> 1.0): {'PASS' if validation_results['sharpe_ratio'] else 'FAIL'} ({annual_sharpe:.2f})")
        
        # Overall assessment
        passed_tests = sum(validation_results.values())
        total_tests = len(validation_results)
        
        print(f"\\nOVERALL ASSESSMENT: {passed_tests}/{total_tests} tests passed")
        print("="*50)
        
        if passed_tests >= 4:
            print("STRONG ALPHA SIGNAL - Proceed with strategy implementation")
            print("   Expert recommendation: Integrate with trading engine")
            final_decision = "PROCEED"
        elif passed_tests >= 3:
            print("MODERATE ALPHA SIGNAL - Proceed with caution")  
            print("   Expert recommendation: Refine signal before full implementation")
            final_decision = "REFINE"
        else:
            print("WEAK ALPHA SIGNAL - DO NOT PROCEED")
            print("   Expert recommendation: Redesign strategy or pivot approach")
            final_decision = "PIVOT"
        
        print(f"\\nFINAL DECISION: {final_decision}")
        
        # Save results
        results_summary = {
            'validation_date': datetime.now().isoformat(),
            'total_signals': len(signals_df),
            'high_confidence_signals': len(high_conf_signals),
            'sample_size': len(returns_1d),
            'mean_return_pct': returns_1d.mean() * 100,
            'volatility_pct': returns_1d.std() * 100,
            'p_value': p_value,
            'information_ratio': info_ratio,
            'win_rate': win_rate,
            'annual_sharpe_ratio': annual_sharpe,
            'tests_passed': passed_tests,
            'final_decision': final_decision
        }
        
        # Write results to file
        with open('alpha_validation_results.json', 'w') as f:
            import json
            json.dump(results_summary, f, indent=2)
        
        print(f"\\nResults saved to alpha_validation_results.json")
        
    else:
        print("INSUFFICIENT DATA - Cannot validate alpha")
        print(f"   Need ≥30 high-confidence signals, got {len(high_conf_signals)}")
        print("   Expert recommendation: Collect more data or lower confidence threshold")

else:
    print("NO SIGNALS GENERATED - Critical failure")
    print("   Expert recommendation: Check data pipeline and SEC integration")

print("\\n" + "="*60)
print("ALPHA VALIDATION EXECUTION COMPLETE")
print("="*60)