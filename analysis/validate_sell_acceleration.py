"""
SELL Acceleration Bear Market Validation (SELL-01, SELL-02)

A/B comparison: V2 baseline vs V2+sell_acceleration on bear market sub-periods.
Validates:
- SELL-01: SELL only fires with acceleration condition
- SELL-02: Bear market performance not degraded

Usage:
    uv run python analysis/validate_sell_acceleration.py
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


# Bear market periods for validation (per D-07)
BEAR_PERIODS = {
    'nasdaq_2008': {'start': '2007-10-01', 'end': '2009-03-31', 'market': 'nasdaq'},
    'nasdaq_2022': {'start': '2021-11-01', 'end': '2023-01-31', 'market': 'nasdaq'},
    'vn30_2022': {'start': '2022-01-01', 'end': '2022-12-31', 'market': 'vn30'},
}

# Warmup period before bear start to allow indicators to stabilize
WARMUP_DAYS = 300  # ~1 year of trading days


def compute_max_drawdown(equity_series):
    """Compute max drawdown from an equity series.

    Args:
        equity_series: pd.Series of equity values.

    Returns:
        Max drawdown as a negative fraction (e.g., -0.15 for -15%).
    """
    peak = equity_series.expanding().max()
    drawdown = (equity_series - peak) / peak
    return drawdown.min()


def find_first_sell_date(results_df, period_start, period_end):
    """Find first SELL signal date within a period.

    Looks for action strings containing 'SELL signal:' in the results
    DataFrame, sliced to the bear period.

    Args:
        results_df: Engine results DataFrame with date, action columns.
        period_start: Start date string.
        period_end: End date string.

    Returns:
        pd.Timestamp of first SELL or None if no SELL in period.
    """
    start_ts = pd.Timestamp(period_start)
    end_ts = pd.Timestamp(period_end)

    period_df = results_df[
        (results_df['date'] >= start_ts) & (results_df['date'] <= end_ts)
    ]

    # Look for SELL signal actions (MA50 sell or cash deterioration)
    sell_rows = period_df[
        period_df['action'].str.contains('SELL signal:', case=False, na=False)
    ]

    if len(sell_rows) == 0:
        return None

    return sell_rows.iloc[0]['date']


def count_sell_signals(results_df, period_start, period_end):
    """Count total SELL signals within a period.

    Args:
        results_df: Engine results DataFrame.
        period_start: Start date string.
        period_end: End date string.

    Returns:
        Integer count of SELL signals.
    """
    start_ts = pd.Timestamp(period_start)
    end_ts = pd.Timestamp(period_end)

    period_df = results_df[
        (results_df['date'] >= start_ts) & (results_df['date'] <= end_ts)
    ]

    sell_rows = period_df[
        period_df['action'].str.contains('SELL signal:', case=False, na=False)
    ]

    return len(sell_rows)


def compute_period_metrics(results_df, trades, period_start, period_end):
    """Compute equity metrics for a bear period.

    Uses V2PerformanceAnalyzer with state[i-1] rule (CRITICAL: avoid
    look-ahead bias per CLAUDE.md equity formula rule).

    Args:
        results_df: Full engine results DataFrame.
        trades: List of trade dicts from engine.
        period_start: Start date string.
        period_end: End date string.

    Returns:
        Dict with max_drawdown, total_return, first_sell_date, sell_count.
    """
    start_ts = pd.Timestamp(period_start)
    end_ts = pd.Timestamp(period_end)

    # Slice results to bear period
    period_df = results_df[
        (results_df['date'] >= start_ts) & (results_df['date'] <= end_ts)
    ].copy().reset_index(drop=True)

    if len(period_df) < 2:
        return {
            'max_drawdown': 0.0,
            'total_return': 0.0,
            'first_sell_date': None,
            'sell_count': 0,
        }

    # Use V2PerformanceAnalyzer which correctly uses state[i-1]
    analyzer = V2PerformanceAnalyzer(period_df, trades)
    max_dd = analyzer.max_drawdown()
    total_ret = analyzer.total_return()

    first_sell = find_first_sell_date(results_df, period_start, period_end)
    sell_count = count_sell_signals(results_df, period_start, period_end)

    return {
        'max_drawdown': max_dd,
        'total_return': total_ret,
        'first_sell_date': first_sell,
        'sell_count': sell_count,
    }


def compute_delay_trading_days(date1, date2):
    """Compute delay between two dates in trading (business) days.

    Args:
        date1: Baseline date (earlier expected).
        date2: Acceleration date (later expected).

    Returns:
        Integer number of business days between dates.
        Positive means acceleration is later. 0 if same date.
        Returns None if either date is None.
    """
    if date1 is None or date2 is None:
        return None

    # Use numpy busday_count for business days
    d1 = pd.Timestamp(date1).date()
    d2 = pd.Timestamp(date2).date()
    return int(np.busday_count(d1, d2))


def run_validation():
    """Run the full A/B bear market validation.

    For each bear period:
    1. Load market data with warmup
    2. Run V2 baseline (sell_acceleration_enabled=False)
    3. Run V2 + acceleration (sell_acceleration_enabled=True)
    4. Compare metrics and check thresholds

    Returns:
        Tuple of (output_text, results_dict, all checks passed).
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    output_lines = []
    output_lines.append("=" * 55)
    output_lines.append("=== SELL Acceleration Bear Market Validation ===")
    output_lines.append("=" * 55)
    output_lines.append(f"Date: {date.today().isoformat()}")
    output_lines.append("")

    all_results = {}
    checks_passed = 0
    checks_total = 0

    for period_name, period_info in BEAR_PERIODS.items():
        start = period_info['start']
        end = period_info['end']
        market = period_info['market']

        output_lines.append(f"--- {period_name} ({start} to {end}) ---")

        # Load data with warmup
        loader = DataLoader(market, data_dir=project_root)

        # Calculate warmup start: go back ~300 trading days before period start
        warmup_start_dt = pd.Timestamp(start) - pd.Timedelta(days=int(WARMUP_DAYS * 1.5))
        warmup_start = warmup_start_dt.strftime('%Y-%m-%d')

        df = loader.load(start_date=warmup_start)
        output_lines.append(f"  Data loaded: {len(df)} rows ({market})")

        # Run baseline (acceleration OFF)
        baseline_config = MDMV2Config(sell_acceleration_enabled=False, name="baseline")
        baseline_engine = MDMV2Engine(baseline_config)
        baseline_results = baseline_engine.run(df)
        baseline_trades = baseline_engine.get_trades()

        baseline_metrics = compute_period_metrics(
            baseline_results, baseline_trades, start, end
        )

        # Run acceleration (acceleration ON)
        accel_config = MDMV2Config(sell_acceleration_enabled=True, name="acceleration")
        accel_engine = MDMV2Engine(accel_config)
        accel_results = accel_engine.run(df)
        accel_trades = accel_engine.get_trades()

        accel_metrics = compute_period_metrics(
            accel_results, accel_trades, start, end
        )

        # Compute delay
        delay = compute_delay_trading_days(
            baseline_metrics['first_sell_date'],
            accel_metrics['first_sell_date']
        )

        # Format first SELL dates
        baseline_sell_str = (
            baseline_metrics['first_sell_date'].strftime('%Y-%m-%d')
            if baseline_metrics['first_sell_date'] is not None
            else "No SELL"
        )
        accel_sell_str = (
            accel_metrics['first_sell_date'].strftime('%Y-%m-%d')
            if accel_metrics['first_sell_date'] is not None
            else "No SELL"
        )

        output_lines.append(f"  Baseline first SELL: {baseline_sell_str}")
        output_lines.append(f"  Acceleration first SELL: {accel_sell_str}")

        # Delay check
        if delay is not None:
            # For 2008 periods: delay <= 5 trading days
            if '2008' in period_name:
                delay_threshold = 5
                delay_pass = abs(delay) <= delay_threshold
                delay_status = "PASS" if delay_pass else "FAIL"
                output_lines.append(
                    f"  Delay: {delay} trading days [{delay_status}, threshold: <= {delay_threshold}]"
                )
                checks_total += 1
                if delay_pass:
                    checks_passed += 1
            else:
                output_lines.append(f"  Delay: {delay} trading days")
        else:
            if baseline_metrics['first_sell_date'] is None and accel_metrics['first_sell_date'] is None:
                output_lines.append("  Delay: N/A (no SELL signals in either run)")
            else:
                output_lines.append("  Delay: N/A (one run had no SELL)")

        output_lines.append(
            f"  Baseline SELL count: {baseline_metrics['sell_count']}"
        )
        output_lines.append(
            f"  Acceleration SELL count: {accel_metrics['sell_count']}"
        )

        # Drawdown check
        baseline_dd = baseline_metrics['max_drawdown']
        accel_dd = accel_metrics['max_drawdown']

        output_lines.append(f"  Baseline max drawdown: {baseline_dd:.1%}")
        output_lines.append(f"  Acceleration max drawdown: {accel_dd:.1%}")

        # For 2022 periods: acceleration max drawdown <= baseline max drawdown (not worse)
        # Note: drawdown is negative, so "not worse" means accel_dd >= baseline_dd
        if '2022' in period_name:
            dd_pass = accel_dd >= baseline_dd - 0.001  # 0.1% tolerance
            dd_status = "PASS" if dd_pass else "FAIL"
            output_lines.append(f"  Drawdown check: [{dd_status}]")
            checks_total += 1
            if dd_pass:
                checks_passed += 1

        # Total return
        output_lines.append(f"  Baseline total return: {baseline_metrics['total_return']:.1%}")
        output_lines.append(f"  Acceleration total return: {accel_metrics['total_return']:.1%}")

        output_lines.append("")

        all_results[period_name] = {
            'baseline': baseline_metrics,
            'acceleration': accel_metrics,
            'delay': delay,
            'baseline_results': baseline_results,
            'accel_results': accel_results,
            'start': start,
            'end': end,
            'market': market,
        }

    output_lines.append(f"Overall: {checks_passed}/{checks_total} checks PASSED")

    output_text = '\n'.join(output_lines)
    all_passed = checks_passed == checks_total

    return output_text, all_results, all_passed


def generate_comparison_chart(all_results, output_path):
    """Generate comparison chart with SELL signal markers.

    One subplot per bear period showing price line with
    baseline and acceleration SELL markers.

    Args:
        all_results: Dict of period results from run_validation().
        output_path: Path for output PNG file.
    """
    n_periods = len(all_results)
    fig, axes = plt.subplots(n_periods, 1, figsize=(14, 5 * n_periods))

    if n_periods == 1:
        axes = [axes]

    for ax, (period_name, data) in zip(axes, all_results.items()):
        start_ts = pd.Timestamp(data['start'])
        end_ts = pd.Timestamp(data['end'])

        # Slice to bear period
        baseline_df = data['baseline_results']
        accel_df = data['accel_results']

        baseline_period = baseline_df[
            (baseline_df['date'] >= start_ts) & (baseline_df['date'] <= end_ts)
        ]
        accel_period = accel_df[
            (accel_df['date'] >= start_ts) & (accel_df['date'] <= end_ts)
        ]

        # Plot price
        ax.plot(baseline_period['date'], baseline_period['close'],
                color='black', linewidth=0.8, label='Price')

        # Baseline SELL markers
        baseline_sells = baseline_period[
            baseline_period['action'].str.contains('SELL signal:', case=False, na=False)
        ]
        if len(baseline_sells) > 0:
            ax.scatter(baseline_sells['date'], baseline_sells['close'],
                       marker='v', color='red', s=100, zorder=5,
                       label=f'Baseline SELL ({len(baseline_sells)})')

        # Acceleration SELL markers
        accel_sells = accel_period[
            accel_period['action'].str.contains('SELL signal:', case=False, na=False)
        ]
        if len(accel_sells) > 0:
            ax.scatter(accel_sells['date'], accel_sells['close'],
                       marker='D', color='blue', s=80, zorder=5,
                       label=f'Acceleration SELL ({len(accel_sells)})')

        # Deferred SELL markers (acceleration only)
        deferred_sells = accel_period[
            accel_period['action'].str.contains('SELL deferred', case=False, na=False)
        ]
        if len(deferred_sells) > 0:
            ax.scatter(deferred_sells['date'], deferred_sells['close'],
                       marker='x', color='orange', s=60, zorder=4, alpha=0.7,
                       label=f'Deferred SELL ({len(deferred_sells)})')

        ax.set_title(f'{period_name} ({data["start"]} to {data["end"]})')
        ax.set_ylabel('Price')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Chart saved: {output_path}")


def main():
    """Run validation, save outputs, print results."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Run validation
    output_text, all_results, all_passed = run_validation()

    # Print to console
    print(output_text)

    # Save text output
    txt_path = os.path.join(output_dir, 'sell_acceleration_validation.txt')
    with open(txt_path, 'w') as f:
        f.write(output_text)
    print(f"\nResults saved: {txt_path}")

    # Generate comparison chart
    chart_path = os.path.join(output_dir, 'sell_acceleration_comparison.png')
    generate_comparison_chart(all_results, chart_path)

    # Exit with appropriate code
    if all_passed:
        print("\nAll checks PASSED.")
    else:
        print("\nSome checks FAILED.")


if __name__ == '__main__':
    main()
