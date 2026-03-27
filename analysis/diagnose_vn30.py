import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from strategies.mdm_classic.data_loader import DataLoader

def analyze_vn30():
    print("🔍 DIAGNOSING VN30 MARKET BEHAVIOR")
    print("=" * 50)
    
    # Load data
    try:
        loader = DataLoader('vn30_price.csv')
        df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
        print(f"✅ Data loaded: {len(df)} rows")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # Calculate indicators if not present (Data Loader effectively does some of this but let's be sure)
    df['prev_close'] = df['close'].shift(1)
    df['prev_volume'] = df['volume'].shift(1)
    df['price_change'] = df['close'] - df['prev_close']
    df['price_change_pct'] = df['price_change'] / df['prev_close']
    df['volume_up'] = df['volume'] > df['prev_volume']
    
    # Define Thresholds
    FTD_THRESHOLDS = [0.005, 0.008, 0.01, 0.012, 0.015] # 0.5%, 0.8%, 1.0%, 1.2%, 1.5%
    DD_THRESHOLDS = [-0.001, -0.002, -0.003, -0.005] # -0.1%, -0.2%, -0.3%, -0.5%
    
    total_days = len(df)
    
    print("\n📊 1. FTD TRIGGER POTENTIAL (Price Up + Vol Up)")
    print("-" * 50)
    print(f"{'Min Gain':<10} | {'Days':<10} | {'% of Total':<10}")
    print("-" * 50)
    
    for thresh in FTD_THRESHOLDS:
        # Condition: Price Gain >= Threshold AND Volume > Prev
        count = len(df[(df['price_change_pct'] >= thresh) & (df['volume_up'])])
        pct = (count / total_days) * 100
        print(f"{thresh*100:>4.1f}%      | {count:<10} | {pct:>8.2f}%")
        
    print("\n📊 2. DISTRIBUTION DAY FREQUENCY (Price Drop + Vol Up)")
    print("-" * 50)
    print(f"{'Max Drop':<10} | {'Days':<10} | {'% of Total':<10}")
    print("-" * 50)
    
    for thresh in DD_THRESHOLDS:
        # Condition: Price Drop <= Threshold (more negative) AND Volume > Prev
        count = len(df[(df['price_change_pct'] <= thresh) & (df['volume_up'])])
        pct = (count / total_days) * 100
        print(f"{thresh*100:>4.1f}%      | {count:<10} | {pct:>8.2f}%")

    # Analyze Volatility
    print("\n📊 3. VOLATILITY STATS")
    print("-" * 50)
    avg_daily_move = df['price_change_pct'].abs().mean()
    print(f"Average Daily Move (Abs): {avg_daily_move*100:.2f}%")
    std_dev = df['price_change_pct'].std()
    print(f"Standard Deviation:       {std_dev*100:.2f}%")
    
    # Check sequences of DDs
    # If 5 DDs occur in 20 days, we exit. How often does this happen?
    df['is_dd_02'] = (df['price_change_pct'] <= -0.002) & (df['volume_up'])
    df['dd_rolling_20'] = df['is_dd_02'].rolling(window=20).sum()
    
    days_with_5_dds = len(df[df['dd_rolling_20'] >= 5])
    print(f"\nDays with >= 5 Distribution Days (0.2% thresh) in last 20 days: {days_with_5_dds}")
    print(f"Percentage of time in 'Warning/Sell' zone: {(days_with_5_dds/total_days)*100:.2f}%")

    # Check gaps between FTDs (using 1% rule)
    df['potential_ftd_10'] = (df['price_change_pct'] >= 0.01) & (df['volume_up'])
    ftd_dates = df[df['potential_ftd_10']]['date'].tolist()
    
    if len(ftd_dates) > 1:
        gaps = []
        for i in range(1, len(ftd_dates)):
            gap = (ftd_dates[i] - ftd_dates[i-1]).days
            gaps.append(gap)
        
        avg_gap = np.mean(gaps)
        max_gap = np.max(gaps)
        print(f"\nTime between Potential FTDs (1.0% rule):")
        print(f"  Average Gap: {avg_gap:.1f} days")
        print(f"  Max Gap:     {max_gap} days")
    else:
        print("\nNot enough FTDs to calculate gaps.")

if __name__ == "__main__":
    analyze_vn30()
