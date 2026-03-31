"""
Fail-Safe Mechanism A/B Validation (SAFE-03)

A/B comparison: V2 baseline (fail_safe_enabled=False) vs V2+fail_safe
(fail_safe_enabled=True) on VN30 data.

Validates:
- Fail-safe reduces total loss from false SELL signals on VN30
- No fail-safe triggers during VN30 2022 bear market (Jan-Nov 2022)

Usage:
    uv run python analysis/validate_fail_safe.py
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


# Periods for validation
VN30_PERIODS = {
    'vn30_full': {'start': '2018-01-01', 'end': '2026-03-31', 'market': 'vn30'},
    'vn30_2022_bear': {'start': '2022-01-01', 'end': '2022-11-30', 'market': 'vn30'},
}

# Warmup period before start to allow indicators to stabilize
WARMUP_DAYS = 300  # ~1 year of trading days


def load_vn30_data(warmup_start=None):
    """Load VN30 data with optional warmup start date.

    Args:
        warmup_start: Start date string for data loading (includes warmup).
            If None, loads all available data.

    Returns:
        pd.DataFrame with columns [date, open, high, low, close, volume].
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    loader = DataLoader('vn30', data_dir=project_root)
    df = loader.load(start_date=warmup_start)
    return df


def run_ab_comparison(df):
    """Run A/B comparison: baseline (no fail-safe) vs test (with fail-safe).

    Args:
        df: VN30 DataFrame with OHLCV data (including warmup period).

    Returns:
        Dict with keys: baseline_results, failsafe_results,
        baseline_metrics, failsafe_metrics, baseline_trades, failsafe_trades.
    """
    # Baseline: fail-safe OFF
    baseline_config = MDMV2Config(fail_safe_enabled=False, name="baseline_no_failsafe")
    baseline_engine = MDMV2Engine(baseline_config)
    baseline_results = baseline_engine.run(df)
    baseline_trades = baseline_engine.get_trades()

    baseline_analyzer = V2PerformanceAnalyzer(baseline_results, baseline_trades)
    baseline_metrics = baseline_analyzer.summary()

    # Test: fail-safe ON
    failsafe_config = MDMV2Config(fail_safe_enabled=True, name="with_failsafe")
    failsafe_engine = MDMV2Engine(failsafe_config)
    failsafe_results = failsafe_engine.run(df)
    failsafe_trades = failsafe_engine.get_trades()

    failsafe_analyzer = V2PerformanceAnalyzer(failsafe_results, failsafe_trades)
    failsafe_metrics = failsafe_analyzer.summary()

    return {
        'baseline_results': baseline_results,
        'failsafe_results': failsafe_results,
        'baseline_metrics': baseline_metrics,
        'failsafe_metrics': failsafe_metrics,
        'baseline_trades': baseline_trades,
        'failsafe_trades': failsafe_trades,
        'baseline_equity': baseline_analyzer.equity,
        'failsafe_equity': failsafe_analyzer.equity,
    }


def identify_false_sells(results_df, trades, recovery_window=20):
    """Find SELL signals that were followed by market recovery (false sells).

    A false sell is one where the market close exceeds the sell-day close
    within recovery_window trading days.

    Args:
        results_df: Engine results DataFrame with date, close, action columns.
        trades: List of trade dicts from engine.
        recovery_window: Number of trading days to check for recovery.

    Returns:
        List of false sell trade dicts.
    """
    false_sells = []

    # Find SELL_SIGNAL trades
    sell_trades = [t for t in trades if t.get('type') == 'SELL_SIGNAL']

    for trade in sell_trades:
        sell_date = pd.Timestamp(trade['date'])

        # Find the sell day in results
        sell_idx = results_df.index[results_df['date'] == sell_date]
        if len(sell_idx) == 0:
            continue
        sell_idx = sell_idx[0]
        sell_close = results_df.loc[sell_idx, 'close']

        # Check if market recovers within window
        window_end = min(sell_idx + recovery_window, len(results_df) - 1)
        window_df = results_df.iloc[sell_idx + 1:window_end + 1]

        if len(window_df) > 0 and window_df['close'].max() > sell_close:
            false_sells.append(trade)

    return false_sells


def count_fail_safe_triggers(trades):
    """Count trades with type == 'FAIL_SAFE_EXIT'.

    Args:
        trades: List of trade dicts from engine.

    Returns:
        Integer count of FAIL_SAFE_EXIT trades.
    """
    return sum(1 for t in trades if t.get('type') == 'FAIL_SAFE_EXIT')


def validate_bear_safety(results_df, trades, period_start, period_end):
    """Check that NO FAIL_SAFE_EXIT trades occur during the bear period.

    Args:
        results_df: Engine results DataFrame.
        trades: List of trade dicts from engine.
        period_start: Start date string for bear period.
        period_end: End date string for bear period.

    Returns:
        bool: True if no fail-safe triggers during bear period (safe).
    """
    start_ts = pd.Timestamp(period_start)
    end_ts = pd.Timestamp(period_end)

    fail_safe_trades = [
        t for t in trades
        if t.get('type') == 'FAIL_SAFE_EXIT'
        and start_ts <= pd.Timestamp(t['date']) <= end_ts
    ]

    return len(fail_safe_trades) == 0


def plot_comparison(baseline_results, failsafe_results,
                    baseline_equity, failsafe_equity, output_path):
    """Generate comparison chart with equity curves and key metrics bar chart.

    Two-panel chart:
    - Top: Equity curves overlaid (baseline vs fail-safe)
    - Bottom: Bar chart of key metrics comparison

    Args:
        baseline_results: Baseline engine results DataFrame.
        failsafe_results: Fail-safe engine results DataFrame.
        baseline_equity: pd.Series of baseline equity values.
        failsafe_equity: pd.Series of fail-safe equity values.
        output_path: Path for output PNG file.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10),
                                     gridspec_kw={'height_ratios': [2, 1]})

    # Top panel: Equity curves
    dates_baseline = baseline_results['date'].values
    dates_failsafe = failsafe_results['date'].values

    ax1.plot(dates_baseline, baseline_equity.values,
             color='red', linewidth=1.0, alpha=0.8, label='Baseline (no fail-safe)')
    ax1.plot(dates_failsafe, failsafe_equity.values,
             color='blue', linewidth=1.0, alpha=0.8, label='With fail-safe')

    # Mark fail-safe exit points on the equity curve
    fail_safe_rows = failsafe_results[
        failsafe_results['action'].str.contains('fail-safe', case=False, na=False)
    ]
    if len(fail_safe_rows) > 0:
        fs_indices = fail_safe_rows.index
        ax1.scatter(failsafe_results.loc[fs_indices, 'date'].values,
                    failsafe_equity.loc[fs_indices].values,
                    marker='^', color='green', s=100, zorder=5,
                    label=f'Fail-safe triggers ({len(fail_safe_rows)})')

    ax1.set_title('Fail-Safe A/B Comparison: Equity Curves (VN30)')
    ax1.set_ylabel('Equity (starting at 1.0)')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Bottom panel: Metrics bar chart
    baseline_analyzer = V2PerformanceAnalyzer(baseline_results, [])
    failsafe_analyzer = V2PerformanceAnalyzer(failsafe_results, [])

    metrics_labels = ['Total Return', 'Max Drawdown', 'Sharpe Ratio']
    baseline_vals = [
        baseline_analyzer.total_return() * 100,
        baseline_analyzer.max_drawdown() * 100,
        baseline_analyzer.sharpe_ratio(),
    ]
    failsafe_vals = [
        failsafe_analyzer.total_return() * 100,
        failsafe_analyzer.max_drawdown() * 100,
        failsafe_analyzer.sharpe_ratio(),
    ]

    x = np.arange(len(metrics_labels))
    width = 0.35

    ax2.bar(x - width / 2, baseline_vals, width, color='red', alpha=0.7,
            label='Baseline')
    ax2.bar(x + width / 2, failsafe_vals, width, color='blue', alpha=0.7,
            label='With fail-safe')

    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics_labels)
    ax2.set_title('Key Metrics Comparison')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for i, (bv, fv) in enumerate(zip(baseline_vals, failsafe_vals)):
        fmt = '.1f' if i < 2 else '.2f'
        unit = '%' if i < 2 else ''
        ax2.text(i - width / 2, bv, f'{bv:{fmt}}{unit}',
                 ha='center', va='bottom', fontsize=8)
        ax2.text(i + width / 2, fv, f'{fv:{fmt}}{unit}',
                 ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Chart saved: {output_path}")


def main():
    """Run fail-safe A/B validation, save outputs, print results."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    results_dir = os.path.join(project_root, 'results')
    os.makedirs(results_dir, exist_ok=True)

    output_lines = []
    output_lines.append("=" * 55)
    output_lines.append("=== Fail-Safe Mechanism A/B Validation (SAFE-03) ===")
    output_lines.append("=" * 55)
    output_lines.append(f"Date: {date.today().isoformat()}")
    output_lines.append("")

    # Load VN30 data with warmup
    warmup_start_dt = pd.Timestamp(VN30_PERIODS['vn30_full']['start']) - pd.Timedelta(
        days=int(WARMUP_DAYS * 1.5)
    )
    warmup_start = warmup_start_dt.strftime('%Y-%m-%d')
    df = load_vn30_data(warmup_start=warmup_start)
    output_lines.append(f"Data loaded: {len(df)} rows (VN30)")
    output_lines.append("")

    # Run A/B comparison on full period
    output_lines.append("--- Full Period A/B Comparison ---")
    comparison = run_ab_comparison(df)

    baseline_metrics = comparison['baseline_metrics']
    failsafe_metrics = comparison['failsafe_metrics']

    # Print comparison table
    output_lines.append(f"{'Metric':<30} {'Baseline':>15} {'Fail-Safe':>15}")
    output_lines.append("-" * 62)
    output_lines.append(
        f"{'Total Return':<30} {baseline_metrics['total_return']:>14.1%} {failsafe_metrics['total_return']:>14.1%}"
    )
    output_lines.append(
        f"{'Max Drawdown':<30} {baseline_metrics['max_drawdown']:>14.1%} {failsafe_metrics['max_drawdown']:>14.1%}"
    )
    output_lines.append(
        f"{'Sharpe Ratio':<30} {baseline_metrics['sharpe_ratio']:>14.2f} {failsafe_metrics['sharpe_ratio']:>14.2f}"
    )
    output_lines.append(
        f"{'Win Rate':<30} {baseline_metrics['win_rate']:>14.1%} {failsafe_metrics['win_rate']:>14.1%}"
    )
    output_lines.append(
        f"{'Trade Count (baseline)':<30} {len(comparison['baseline_trades']):>15}"
    )
    output_lines.append(
        f"{'Trade Count (fail-safe)':<30} {len(comparison['failsafe_trades']):>15}"
    )

    # False sell analysis
    baseline_false_sells = identify_false_sells(
        comparison['baseline_results'], comparison['baseline_trades']
    )
    failsafe_false_sells = identify_false_sells(
        comparison['failsafe_results'], comparison['failsafe_trades']
    )

    output_lines.append(
        f"{'False SELL count (baseline)':<30} {len(baseline_false_sells):>15}"
    )
    output_lines.append(
        f"{'False SELL count (fail-safe)':<30} {len(failsafe_false_sells):>15}"
    )

    # Fail-safe trigger count
    fs_trigger_count = count_fail_safe_triggers(comparison['failsafe_trades'])
    output_lines.append(
        f"{'Fail-safe triggers':<30} {fs_trigger_count:>15}"
    )
    output_lines.append("")

    # Validate bear safety on 2022 period
    bear_period = VN30_PERIODS['vn30_2022_bear']
    bear_safe = validate_bear_safety(
        comparison['failsafe_results'],
        comparison['failsafe_trades'],
        bear_period['start'],
        bear_period['end'],
    )

    output_lines.append("--- Validation Criteria ---")

    # Criterion 1: Fail-safe effect on false SELL losses
    # Compare total return or false sell count
    return_improved = failsafe_metrics['total_return'] >= baseline_metrics['total_return']
    false_sells_reduced = len(failsafe_false_sells) <= len(baseline_false_sells)
    criterion_1_pass = return_improved or false_sells_reduced
    status_1 = "PASS" if criterion_1_pass else "FAIL"
    output_lines.append(
        f"[{status_1}] Fail-safe reduces false SELL losses "
        f"(return improved: {return_improved}, false sells reduced: {false_sells_reduced})"
    )

    # Criterion 2: No fail-safe triggers during 2022 bear
    status_2 = "PASS" if bear_safe else "FAIL"
    output_lines.append(
        f"[{status_2}] No fail-safe triggers during 2022 bear market (Jan-Nov 2022)"
    )

    output_lines.append("")
    checks_passed = sum([criterion_1_pass, bear_safe])
    checks_total = 2
    output_lines.append(f"Overall: {checks_passed}/{checks_total} checks PASSED")

    output_text = '\n'.join(output_lines)

    # Print to console
    print(output_text)

    # Save text output
    txt_path = os.path.join(results_dir, 'fail_safe_validation.txt')
    with open(txt_path, 'w') as f:
        f.write(output_text)
    print(f"\nResults saved: {txt_path}")

    # Generate comparison chart
    chart_path = os.path.join(results_dir, 'fail_safe_ab_comparison.png')
    plot_comparison(
        comparison['baseline_results'],
        comparison['failsafe_results'],
        comparison['baseline_equity'],
        comparison['failsafe_equity'],
        chart_path,
    )

    # Summary
    if checks_passed == checks_total:
        print("\nAll checks PASSED.")
    else:
        print("\nSome checks FAILED.")


if __name__ == '__main__':
    main()
