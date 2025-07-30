#!/usr/bin/env python
"""
Test Iron Condor strike selection with current SPY options data
"""
import sys
import os
sys.path.append(os.getcwd())

from options_data.yfinance_options_client import YFinanceOptionsClient
import pandas as pd

def test_iron_condor_strikes():
    """Test Iron Condor strategy strike selection"""
    print("=" * 80)
    print("TESTING IRON CONDOR STRIKE SELECTION")
    print("=" * 80)
    
    # Initialize client
    client = YFinanceOptionsClient()
    
    # Get current options data
    options_df = client.get_current_spy_options_chain(save_to_disk=False)
    
    if options_df.empty:
        print("No options data available")
        return
    
    print(f"Total contracts: {len(options_df)}")
    print(f"Current SPY price: ${options_df['underlying_price'].iloc[0]:.2f}")
    
    # Show available expirations
    expirations = sorted(options_df['expiration'].unique())
    dte_info = []
    for exp in expirations:
        exp_df = options_df[options_df['expiration'] == exp]
        dte = exp_df['days_to_expiration'].iloc[0]
        dte_info.append((exp, dte))
    
    print(f"\nAvailable expirations with DTE:")
    for exp, dte in dte_info[:10]:  # Show first 10
        print(f"  {exp}: {dte} days")
    
    # Test with different DTE targets
    test_dtes = [7, 14, 21, 30, 45]
    
    for target_dte in test_dtes:
        print(f"\n{'='*50}")
        print(f"TESTING TARGET DTE: {target_dte} days")
        print(f"{'='*50}")
        
        iron_condor = client.get_iron_condor_strikes(options_df, target_dte=target_dte)
        
        if iron_condor:
            print(f"SUCCESS: Iron Condor found for ~{target_dte} DTE:")
            print(f"  Expiration: {iron_condor['expiration']}")
            print(f"  Actual DTE: {iron_condor['days_to_expiration']} days")
            print(f"  Underlying: ${iron_condor['underlying_price']:.2f}")
            print(f"  Short Put:  ${iron_condor['short_put_strike']:.2f}")
            print(f"  Long Put:   ${iron_condor['long_put_strike']:.2f}")
            print(f"  Short Call: ${iron_condor['short_call_strike']:.2f}")
            print(f"  Long Call:  ${iron_condor['long_call_strike']:.2f}")
            print(f"  Wing Width: ${iron_condor['wing_width']:.2f}")
            
            # Calculate strategy width and max profit potential
            call_spread_width = iron_condor['long_call_strike'] - iron_condor['short_call_strike']
            put_spread_width = iron_condor['short_put_strike'] - iron_condor['long_put_strike']
            max_loss = max(call_spread_width, put_spread_width) * 100  # Per contract
            
            print(f"  Max Loss per contract: ${max_loss:.2f}")
            
            # Show the actual option prices for this strategy
            exp_df = options_df[options_df['expiration'] == iron_condor['expiration']]
            
            short_call_data = exp_df[(exp_df['strike'] == iron_condor['short_call_strike']) & 
                                   (exp_df['option_type'] == 'C')]
            short_put_data = exp_df[(exp_df['strike'] == iron_condor['short_put_strike']) & 
                                  (exp_df['option_type'] == 'P')]
            
            if not short_call_data.empty and not short_put_data.empty:
                short_call_bid = short_call_data['bid'].iloc[0]
                short_put_bid = short_put_data['bid'].iloc[0]
                net_credit = (short_call_bid + short_put_bid) * 100
                
                print(f"  Short Call Bid: ${short_call_bid:.2f}")
                print(f"  Short Put Bid:  ${short_put_bid:.2f}")
                print(f"  Estimated Credit: ${net_credit:.2f} per contract")
                
                if net_credit > 0:
                    max_profit_pct = (net_credit / max_loss) * 100 if max_loss > 0 else 0
                    print(f"  Max Profit %: {max_profit_pct:.1f}%")
        else:
            print(f"FAILED: No suitable Iron Condor found for {target_dte} DTE")

if __name__ == "__main__":
    test_iron_condor_strikes()