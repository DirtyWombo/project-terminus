#!/usr/bin/env python3
"""
Debug script to examine fundamental data structure and identify QVM calculation issues
"""

import pandas as pd
import json

def debug_fundamental_data():
    """Examine the structure of our fundamental data"""
    
    print("=" * 80)
    print("FUNDAMENTAL DATA DIAGNOSTIC")
    print("=" * 80)
    
    # Load the fundamental data
    try:
        data = pd.read_pickle('data/sprint_8/fundamental_data.pkl')
        print(f"Successfully loaded fundamental data for {len(data)} tickers")
        print(f"Tickers: {list(data.keys())}")
    except Exception as e:
        print(f"Error loading fundamental data: {e}")
        return
    
    # Examine each ticker's data structure
    for ticker in list(data.keys())[:3]:  # Look at first 3 tickers
        print(f"\n{'-'*60}")
        print(f"EXAMINING {ticker}")
        print(f"{'-'*60}")
        
        ticker_data = data[ticker]
        print(f"Available keys: {list(ticker_data.keys())}")
        
        # Check info data
        if 'info' in ticker_data:
            info = ticker_data['info']
            print(f"\nINFO data type: {type(info)}")
            if isinstance(info, dict):
                key_count = len(info.keys())
                print(f"Info keys count: {key_count}")
                sample_keys = list(info.keys())[:10]
                print(f"Sample info keys: {sample_keys}")
                
                # Check for enterprise value
                ev = info.get('enterpriseValue')
                print(f"Enterprise Value: {ev} (type: {type(ev)})")
            else:
                print("Info data is not a dictionary!")
        
        # Check financials data
        if 'financials' in ticker_data:
            financials = ticker_data['financials']
            print(f"\nFINANCIALS data type: {type(financials)}")
            if hasattr(financials, 'shape'):
                print(f"Financials shape: {financials.shape}")
                if not financials.empty:
                    print(f"Financials columns: {list(financials.columns)}")
                    print(f"Financials index: {list(financials.index)}")
                    
                    # Look for Net Income
                    if 'Net Income' in financials.index:
                        net_income = financials.loc['Net Income']
                        print(f"Net Income found: {net_income.iloc[0] if len(net_income) > 0 else 'No data'}")
                    else:
                        print("Net Income not found in financials index")
                        print("Available financial metrics:")
                        for idx in financials.index[:10]:
                            print(f"  - {idx}")
                else:
                    print("Financials DataFrame is empty")
        
        # Check balance sheet data
        if 'balance_sheet' in ticker_data:
            balance_sheet = ticker_data['balance_sheet']
            print(f"\nBALANCE SHEET data type: {type(balance_sheet)}")
            if hasattr(balance_sheet, 'shape'):
                print(f"Balance sheet shape: {balance_sheet.shape}")
                if not balance_sheet.empty:
                    print(f"Balance sheet columns: {list(balance_sheet.columns)}")
                    print(f"Balance sheet index: {list(balance_sheet.index)}")
                    
                    # Look for Total Stockholder Equity
                    equity_keys = [idx for idx in balance_sheet.index if 'equity' in idx.lower() or 'stockholder' in idx.lower()]
                    print(f"Equity-related keys: {equity_keys}")
                else:
                    print("Balance sheet DataFrame is empty")

def test_qvm_calculations():
    """Test QVM factor calculations with actual data"""
    
    print(f"\n{'='*80}")
    print("TESTING QVM FACTOR CALCULATIONS")
    print("=" * 80)
    
    # Load data
    data = pd.read_pickle('data/sprint_8/fundamental_data.pkl')
    
    # Import QVM functions
    from features.qvm_factors import calculate_quality_factor, calculate_value_factor
    
    for ticker in list(data.keys())[:5]:  # Test first 5
        print(f"\nTesting {ticker}:")
        
        try:
            quality = calculate_quality_factor(data[ticker])
            print(f"  Quality (ROE): {quality}")
        except Exception as e:
            print(f"  Quality calculation error: {e}")
        
        try:
            value = calculate_value_factor(data[ticker])
            print(f"  Value (EBIT/EV): {value}")
        except Exception as e:
            print(f"  Value calculation error: {e}")

def suggest_fixes():
    """Suggest potential fixes based on data structure"""
    
    print(f"\n{'='*80}")
    print("SUGGESTED FIXES")
    print("=" * 80)
    
    data = pd.read_pickle('data/sprint_8/fundamental_data.pkl')
    
    if data:
        sample_ticker = list(data.keys())[0]
        sample_data = data[sample_ticker]
        
        # Check financials structure
        if 'financials' in sample_data and not sample_data['financials'].empty:
            financials = sample_data['financials']
            
            print("Available financial statement line items:")
            for i, item in enumerate(financials.index):
                print(f"  {i+1:2d}. {item}")
                if i >= 20:  # Limit output
                    print(f"     ... and {len(financials.index) - 21} more")
                    break
        
        # Check balance sheet structure  
        if 'balance_sheet' in sample_data and not sample_data['balance_sheet'].empty:
            balance_sheet = sample_data['balance_sheet']
            
            print(f"\nAvailable balance sheet line items:")
            for i, item in enumerate(balance_sheet.index):
                print(f"  {i+1:2d}. {item}")
                if i >= 20:  # Limit output
                    print(f"     ... and {len(balance_sheet.index) - 21} more")
                    break
        
        print(f"\nRecommendations:")
        print("1. Check exact spelling of 'Net Income' and 'Total Stockholder Equity'")
        print("2. Consider alternative field names (e.g., 'Net Income Common Stockholders')")
        print("3. Implement fallback calculations if primary fields unavailable")
        print("4. Add data validation before calculations")

if __name__ == "__main__":
    debug_fundamental_data()
    test_qvm_calculations()
    suggest_fixes()