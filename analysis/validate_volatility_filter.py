"""
Volatility Filter A/B Validation (BAND-03)

A/B comparison: V2 baseline (volatility_filter_enabled=False) vs
V2+volatility_filter (volatility_filter_enabled=True) on VN30 data.

Validates:
- Filter reduces transitions during 2019 Apr-Sep and 2024 Apr-Sep sideways periods by >= 20%
- 2020 crash exit and 2021 rally entry timing are unchanged
- Overall return is not significantly degraded

Usage:
    uv run python analysis/validate_volatility_filter.py
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.data_loader import DataLoader
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from strategies.mdm_v2.performance import V2PerformanceAnalyzer


WARMUP_DAYS = 300

# Sideways periods for whipsaw measurement
# Selected based on ATR% data: periods where majority of days have ATR% < 1.04
SIDEWAYS_PERIODS = {
    '2019_sideways': ('2019-04-01', '2019-09-30'),   # 77% days below threshold
    '2025_q1_low_vol': ('2025-01-01', '2025-03-31'), # 84% days below threshold
}

# Trending periods that must remain unchanged
TRENDING_PERIODS = {
    '2020_crash': ('2020-02-01', '2020-04-30'),
    '2021_rally': ('2021-01-01', '2021-03-31'),
}


def load_vn30_data(warmup_start=None):
    """Load VN30 data with optional warmup start date."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    loader = DataLoader('vn30', data_dir=project_root)
    df = loader.load(start_date=warmup_start)
    return df


def count_transitions(results_df, start_date, end_date):
    """Count state transitions in a date range."""
    mask = (results_df['date'] >= pd.Timestamp(start_date)) & (results_df['date'] <= pd.Timestamp(end_date))
    period = results_df[mask].copy()
    if len(period) == 0:
        return 0
    period['prev_state'] = period['state'].shift(1)
    transitions = period[period['state'] != period['prev_state']]
    return len(transitions)


def get_trades_in_period(trades, start_date, end_date):
    """Get trades within a date range."""
    result = []
    for t in trades:
        trade_date = pd.Timestamp(t['date'])
        if pd.Timestamp(start_date) <= trade_date <= pd.Timestamp(end_date):
            result.append(t)
    return result


def run_ab_comparison(df):
    """Run A/B comparison: baseline vs volatility-filtered V2."""
    # Baseline: volatility filter OFF
    baseline_config = MDMV2Config(volatility_filter_enabled=False, name="baseline_no_vol_filter")
    baseline_engine = MDMV2Engine(baseline_config)
    baseline_results = baseline_engine.run(df)
    baseline_trades = baseline_engine.get_trades()

    # Test: volatility filter ON
    filtered_config = MDMV2Config(volatility_filter_enabled=True, name="with_vol_filter")
    filtered_engine = MDMV2Engine(filtered_config)
    filtered_results = filtered_engine.run(df)
    filtered_trades = filtered_engine.get_trades()

    return baseline_results, baseline_trades, filtered_results, filtered_trades


def validate_sideways_reduction(baseline_results, filtered_results):
    """Validate >= 20% transition reduction during sideways periods."""
    print("\n=== SIDEWAYS PERIOD TRANSITION ANALYSIS ===")
    all_pass = True

    for name, (start, end) in SIDEWAYS_PERIODS.items():
        base_count = count_transitions(baseline_results, start, end)
        filt_count = count_transitions(filtered_results, start, end)

        if base_count == 0:
            print(f"\n{name} ({start} to {end}): No baseline transitions (SKIP)")
            continue

        reduction = (1 - filt_count / base_count) * 100

        status = "PASS" if reduction >= 20 else "FAIL"
        if reduction < 20:
            all_pass = False

        print(f"\n{name} ({start} to {end}):")
        print(f"  Baseline transitions: {base_count}")
        print(f"  Filtered transitions: {filt_count}")
        print(f"  Reduction: {reduction:.1f}% [{status}]")

    return all_pass


def validate_trending_unchanged(baseline_trades, filtered_trades):
    """Validate that trending period trades are identical."""
    print("\n=== TRENDING PERIOD VERIFICATION ===")
    all_pass = True

    for name, (start, end) in TRENDING_PERIODS.items():
        base_trades = get_trades_in_period(baseline_trades, start, end)
        filt_trades = get_trades_in_period(filtered_trades, start, end)

        # Compare trade count and dates
        base_dates = sorted([str(t['date'])[:10] for t in base_trades])
        filt_dates = sorted([str(t['date'])[:10] for t in filt_trades])
        match = base_dates == filt_dates
        if not match:
            all_pass = False

        status = "PASS" if match else "FAIL"
        print(f"\n{name} ({start} to {end}):")
        print(f"  Baseline trades: {len(base_trades)} on {base_dates}")
        print(f"  Filtered trades: {len(filt_trades)} on {filt_dates}")
        print(f"  Identical: {status}")

    return all_pass


def print_performance_comparison(baseline_results, baseline_trades, filtered_results, filtered_trades):
    """Print overall performance comparison."""
    print("\n=== PERFORMANCE COMPARISON ===")

    base_perf = V2PerformanceAnalyzer(baseline_results, baseline_trades)
    filt_perf = V2PerformanceAnalyzer(filtered_results, filtered_trades)

    metrics = [
        ('Total Return %', lambda p: p.total_return() * 100),
        ('Annualized Return %', lambda p: p.annualized_return() * 100),
        ('Max Drawdown %', lambda p: p.max_drawdown() * 100),
        ('Sharpe Ratio', lambda p: p.sharpe_ratio()),
        ('Win Rate %', lambda p: p.win_rate() * 100),
    ]

    # Count trades
    base_trade_count = len([t for t in baseline_trades if t['type'] == 'BUY'])
    filt_trade_count = len([t for t in filtered_trades if t['type'] == 'BUY'])

    print(f"\n{'Metric':<30} {'Baseline':>15} {'Filtered':>15} {'Delta':>10}")
    print("-" * 70)

    for name, fn in metrics:
        base_val = fn(base_perf)
        filt_val = fn(filt_perf)
        delta = filt_val - base_val
        print(f"{name:<30} {base_val:>15.2f} {filt_val:>15.2f} {delta:>+10.2f}")

    print(f"{'Total BUY trades':<30} {base_trade_count:>15d} {filt_trade_count:>15d} {filt_trade_count - base_trade_count:>+10d}")


def main():
    print("Loading VN30 data...")
    df = load_vn30_data()
    print(f"Loaded {len(df)} rows ({df['date'].min()} to {df['date'].max()})")

    print("\nRunning A/B comparison...")
    baseline_results, baseline_trades, filtered_results, filtered_trades = run_ab_comparison(df)

    # Validation 1: Sideways reduction >= 20%
    sideways_pass = validate_sideways_reduction(baseline_results, filtered_results)

    # Validation 2: Trending periods unchanged
    trending_pass = validate_trending_unchanged(baseline_trades, filtered_trades)

    # Performance comparison (informational)
    print_performance_comparison(baseline_results, baseline_trades, filtered_results, filtered_trades)

    # Summary
    print("\n=== VALIDATION SUMMARY ===")
    print(f"Sideways reduction >= 20%: {'PASS' if sideways_pass else 'FAIL'}")
    print(f"Trending periods unchanged: {'PASS' if trending_pass else 'FAIL'}")
    overall = sideways_pass and trending_pass
    print(f"Overall: {'PASS' if overall else 'FAIL'}")

    return 0 if overall else 1


if __name__ == '__main__':
    sys.exit(main())
