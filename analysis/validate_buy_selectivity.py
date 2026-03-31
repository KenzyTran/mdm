"""
BUY Selectivity A/B Validation (BUY-01, BUY-02)

A/B comparison: V2 baseline vs V2+buy_selectivity on NASDAQ and VN30.
Walk-forward validation: train pre-2020, test 2020-2026.

Usage:
    uv run python analysis/validate_buy_selectivity.py
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


# Test periods
PERIODS = {
    'nasdaq_full': {'start': '2004-01-01', 'end': '2026-12-31', 'market': 'nasdaq'},
    'vn30_full': {'start': '2018-01-01', 'end': '2026-12-31', 'market': 'vn30'},
}
WARMUP_DAYS = 300

# Walk-forward split
WALK_FORWARD_SPLIT = '2020-01-01'


def make_baseline_config():
    """Create baseline config with buy selectivity OFF.

    Keeps sell_acceleration ON (other v5.0 features stay active).

    Returns:
        MDMV2Config with buy filters disabled.
    """
    return MDMV2Config(
        buy_filter_enabled=False,
        buy_confirmation_enabled=False,
        sell_acceleration_enabled=True,
        name="baseline",
    )


def make_filtered_config():
    """Create filtered config with buy selectivity ON.

    Returns:
        MDMV2Config with buy filters enabled (default values).
    """
    return MDMV2Config(
        buy_filter_enabled=True,
        buy_confirmation_enabled=True,
        confirmation_window_days=3,
        confirmation_max_dd=1,
        sell_acceleration_enabled=True,
        name="filtered",
    )


def compute_metrics(results_df, trades):
    """Compute performance metrics from engine results.

    Uses V2PerformanceAnalyzer with state[i-1] rule (CRITICAL: avoid
    look-ahead bias per CLAUDE.md equity formula rule).

    Args:
        results_df: Full engine results DataFrame.
        trades: List of trade dicts from engine.

    Returns:
        Dict with total_return, max_drawdown, trade_count, win_rate,
        avg_trade_pnl, buy_rejections, buy_confirmations.
    """
    analyzer = V2PerformanceAnalyzer(results_df, trades)

    exit_trades = [t for t in trades if t.get('type') in ('CASH_EXIT', 'SHORT_COVER')]
    wins = sum(1 for t in exit_trades if t.get('pnl', 0) > 0)
    win_rate = wins / len(exit_trades) if exit_trades else 0.0
    avg_pnl = (
        sum(t.get('pnl', 0) for t in exit_trades) / len(exit_trades)
        if exit_trades
        else 0.0
    )

    buy_rejections = int(results_df['buy_rejected'].sum()) if 'buy_rejected' in results_df.columns else 0
    buy_confirmations = int(results_df['buy_confirmed'].sum()) if 'buy_confirmed' in results_df.columns else 0

    return {
        'total_return': analyzer.total_return(),
        'max_drawdown': analyzer.max_drawdown(),
        'trade_count': len(exit_trades),
        'win_rate': win_rate,
        'avg_trade_pnl': avg_pnl,
        'buy_rejections': buy_rejections,
        'buy_confirmations': buy_confirmations,
        'equity': analyzer.equity,
    }


def compute_period_metrics(results_df, trades, start, end):
    """Compute metrics for a specific date range.

    Slices results to the given period and computes metrics.

    Args:
        results_df: Full engine results DataFrame.
        trades: List of trade dicts from engine.
        start: Start date string.
        end: End date string.

    Returns:
        Dict with performance metrics for the period.
    """
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    period_df = results_df[
        (results_df['date'] >= start_ts) & (results_df['date'] <= end_ts)
    ].copy().reset_index(drop=True)

    if len(period_df) < 2:
        return {
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'trade_count': 0,
            'win_rate': 0.0,
            'avg_trade_pnl': 0.0,
            'buy_rejections': 0,
            'buy_confirmations': 0,
            'equity': pd.Series([1.0]),
        }

    # Filter trades to period
    period_trades = [
        t for t in trades
        if start_ts <= pd.Timestamp(t.get('date', t.get('exit_date', '1900-01-01'))) <= end_ts
    ]

    return compute_metrics(period_df, period_trades)


def format_table(headers, rows, col_widths=None):
    """Format a simple text table.

    Args:
        headers: List of header strings.
        rows: List of row tuples/lists.
        col_widths: Optional list of column widths.

    Returns:
        Formatted table string.
    """
    if col_widths is None:
        col_widths = [max(len(str(h)), max(len(str(r[i])) for r in rows))
                      for i, h in enumerate(headers)]

    lines = []
    header_line = " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    lines.append(f"| {header_line} |")
    sep_line = " | ".join("-" * w for w in col_widths)
    lines.append(f"| {sep_line} |")
    for row in rows:
        row_line = " | ".join(str(v).ljust(w) for v, w in zip(row, col_widths))
        lines.append(f"| {row_line} |")

    return "\n".join(lines)


def run_validation():
    """Run the full A/B validation with walk-forward analysis.

    For each period:
    1. Load market data with warmup
    2. Run V2 baseline (buy selectivity OFF)
    3. Run V2 + filtered (buy selectivity ON)
    4. Compare metrics

    Then perform walk-forward validation on NASDAQ.

    Returns:
        Tuple of (output_text, all_results, trade_reduction_pct).
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    output_lines = []
    output_lines.append("=" * 60)
    output_lines.append("=== BUY SELECTIVITY A/B VALIDATION ===")
    output_lines.append("=" * 60)
    output_lines.append(f"Date: {date.today().isoformat()}")
    output_lines.append("")

    all_results = {}
    trade_reduction_nasdaq = 0.0

    for period_name, period_info in PERIODS.items():
        start = period_info['start']
        end = period_info['end']
        market = period_info['market']

        output_lines.append(f"--- {period_name} ({start} to {end}) ---")

        # Load data with warmup
        loader = DataLoader(market, data_dir=project_root)
        warmup_start_dt = pd.Timestamp(start) - pd.Timedelta(days=int(WARMUP_DAYS * 1.5))
        warmup_start = warmup_start_dt.strftime('%Y-%m-%d')
        df = loader.load(start_date=warmup_start, end_date=end)
        output_lines.append(f"  Data loaded: {len(df)} rows ({market})")

        # Run baseline (buy selectivity OFF)
        baseline_config = make_baseline_config()
        baseline_engine = MDMV2Engine(baseline_config)
        baseline_results = baseline_engine.run(df)
        baseline_trades = baseline_engine.get_trades()
        baseline_metrics = compute_metrics(baseline_results, baseline_trades)

        # Run filtered (buy selectivity ON)
        filtered_config = make_filtered_config()
        filtered_engine = MDMV2Engine(filtered_config)
        filtered_results = filtered_engine.run(df)
        filtered_trades = filtered_engine.get_trades()
        filtered_metrics = compute_metrics(filtered_results, filtered_trades)

        # Compute trade reduction
        base_tc = baseline_metrics['trade_count']
        filt_tc = filtered_metrics['trade_count']
        trade_reduction = (base_tc - filt_tc) / base_tc * 100 if base_tc > 0 else 0.0

        if 'nasdaq' in period_name:
            trade_reduction_nasdaq = trade_reduction

        # Print comparison table
        output_lines.append("")
        headers = ["Metric", "Baseline", "Filtered", "Delta"]
        rows = [
            ("Total Return",
             f"{baseline_metrics['total_return']:.1%}",
             f"{filtered_metrics['total_return']:.1%}",
             f"{filtered_metrics['total_return'] - baseline_metrics['total_return']:+.1%}"),
            ("Max Drawdown",
             f"{baseline_metrics['max_drawdown']:.1%}",
             f"{filtered_metrics['max_drawdown']:.1%}",
             f"{filtered_metrics['max_drawdown'] - baseline_metrics['max_drawdown']:+.1%}"),
            ("Trade Count",
             f"{base_tc}",
             f"{filt_tc}",
             f"{filt_tc - base_tc:+d}"),
            ("Win Rate",
             f"{baseline_metrics['win_rate']:.1%}",
             f"{filtered_metrics['win_rate']:.1%}",
             f"{filtered_metrics['win_rate'] - baseline_metrics['win_rate']:+.1%}"),
            ("Avg Trade PnL",
             f"{baseline_metrics['avg_trade_pnl']:.4f}",
             f"{filtered_metrics['avg_trade_pnl']:.4f}",
             f"{filtered_metrics['avg_trade_pnl'] - baseline_metrics['avg_trade_pnl']:+.4f}"),
            ("Buy Rejections",
             f"{baseline_metrics['buy_rejections']}",
             f"{filtered_metrics['buy_rejections']}",
             f"-"),
            ("Buy Confirmations",
             f"{baseline_metrics['buy_confirmations']}",
             f"{filtered_metrics['buy_confirmations']}",
             f"-"),
            ("Trade Reduction",
             f"-",
             f"-",
             f"{trade_reduction:.1f}%"),
        ]
        output_lines.append(format_table(headers, rows, col_widths=[18, 12, 12, 12]))
        output_lines.append("")

        all_results[period_name] = {
            'baseline_metrics': baseline_metrics,
            'filtered_metrics': filtered_metrics,
            'baseline_results': baseline_results,
            'filtered_results': filtered_results,
            'trade_reduction': trade_reduction,
            'start': start,
            'end': end,
            'market': market,
        }

    # Walk-forward validation on NASDAQ
    output_lines.append("=" * 60)
    output_lines.append("=== Walk-Forward Validation (NASDAQ) ===")
    output_lines.append("=" * 60)
    output_lines.append("")

    # Load full NASDAQ data
    loader = DataLoader('nasdaq', data_dir=project_root)
    warmup_start_dt = pd.Timestamp('2004-01-01') - pd.Timedelta(days=int(WARMUP_DAYS * 1.5))
    warmup_start = warmup_start_dt.strftime('%Y-%m-%d')
    df_full = loader.load(start_date=warmup_start)

    # Run filtered config on full data
    filtered_config = make_filtered_config()
    filtered_engine = MDMV2Engine(filtered_config)
    filtered_results = filtered_engine.run(df_full)
    filtered_trades = filtered_engine.get_trades()

    # In-sample: pre-2020
    is_metrics = compute_period_metrics(
        filtered_results, filtered_trades,
        '2004-01-01', '2019-12-31'
    )

    # Out-of-sample: 2020-2026
    oos_metrics = compute_period_metrics(
        filtered_results, filtered_trades,
        WALK_FORWARD_SPLIT, '2026-12-31'
    )

    # Compute degradation
    def safe_degradation(is_val, oos_val):
        """Compute relative degradation, handling edge cases."""
        if is_val == 0:
            return 0.0
        return (is_val - oos_val) / abs(is_val)

    tr_degradation = safe_degradation(is_metrics['total_return'], oos_metrics['total_return'])
    wr_degradation = safe_degradation(is_metrics['win_rate'], oos_metrics['win_rate'])

    wf_headers = ["Metric", "In-Sample", "Out-of-Sample", "Degradation"]
    wf_rows = [
        ("Total Return",
         f"{is_metrics['total_return']:.1%}",
         f"{oos_metrics['total_return']:.1%}",
         f"{tr_degradation:.1%}"),
        ("Win Rate",
         f"{is_metrics['win_rate']:.1%}",
         f"{oos_metrics['win_rate']:.1%}",
         f"{wr_degradation:.1%}"),
        ("Trade Count",
         f"{is_metrics['trade_count']}",
         f"{oos_metrics['trade_count']}",
         f"-"),
        ("Max Drawdown",
         f"{is_metrics['max_drawdown']:.1%}",
         f"{oos_metrics['max_drawdown']:.1%}",
         f"-"),
    ]
    output_lines.append(format_table(wf_headers, wf_rows, col_widths=[18, 14, 16, 14]))
    output_lines.append("")

    # Degradation warnings
    if abs(tr_degradation) > 0.10:
        output_lines.append(f"  WARNING: Total return degradation {tr_degradation:.1%} exceeds 10% threshold")
    else:
        output_lines.append(f"  PASS: Total return degradation {tr_degradation:.1%} within 10% threshold")

    if abs(wr_degradation) > 0.10:
        output_lines.append(f"  WARNING: Win rate degradation {wr_degradation:.1%} exceeds 10% threshold")
    else:
        output_lines.append(f"  PASS: Win rate degradation {wr_degradation:.1%} within 10% threshold")

    output_lines.append("")

    # Trade reduction assertion
    output_lines.append("=" * 60)
    output_lines.append("=== Validation Checks ===")
    output_lines.append("=" * 60)

    if 15 <= trade_reduction_nasdaq <= 40:
        output_lines.append(f"  PASS: NASDAQ trade reduction {trade_reduction_nasdaq:.1f}% is within 15-40% range")
    else:
        output_lines.append(f"  INFO: NASDAQ trade reduction {trade_reduction_nasdaq:.1f}% outside 15-40% target range")

    output_lines.append("")

    output_text = '\n'.join(output_lines)

    return output_text, all_results, trade_reduction_nasdaq


def generate_equity_charts(all_results, project_root):
    """Generate equity curve comparison charts.

    Chart 1: NASDAQ equity curves (baseline vs filtered)
    Chart 2: VN30 equity curves (baseline vs filtered)

    Args:
        all_results: Dict of period results from run_validation().
        project_root: Project root directory for output paths.
    """
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)

    for period_name, data in all_results.items():
        market = data['market']
        baseline_results = data['baseline_results']
        filtered_results = data['filtered_results']
        baseline_metrics = data['baseline_metrics']
        filtered_metrics = data['filtered_metrics']

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Top: Price with buy signals
        ax1.plot(baseline_results['date'], baseline_results['close'],
                 color='black', linewidth=0.8, label='Price')
        ax1.set_title(f'{period_name}: Price')
        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # Bottom: Equity curves comparison
        baseline_equity = baseline_metrics['equity']
        filtered_equity = filtered_metrics['equity']

        # Align equity with dates
        baseline_dates = baseline_results['date'].values
        filtered_dates = filtered_results['date'].values

        ax2.plot(baseline_dates[:len(baseline_equity)], baseline_equity.values,
                 color='blue', linewidth=1.0, alpha=0.8,
                 label=f'Baseline (return={baseline_metrics["total_return"]:.1%})')
        ax2.plot(filtered_dates[:len(filtered_equity)], filtered_equity.values,
                 color='green', linewidth=1.0, alpha=0.8,
                 label=f'Filtered (return={filtered_metrics["total_return"]:.1%})')
        ax2.set_title(f'{period_name}: Equity Curves (Baseline vs Buy Selectivity)')
        ax2.set_ylabel('Equity (starting at 1.0)')
        ax2.legend(loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        chart_path = os.path.join(output_dir, f'buy_selectivity_{market}.png')
        fig.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"Chart saved: {chart_path}")


def main():
    """Run validation, save outputs, print results."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Run validation
    output_text, all_results, trade_reduction_nasdaq = run_validation()

    # Print to console
    print(output_text)

    # Save text output
    txt_path = os.path.join(output_dir, 'buy_selectivity_validation.txt')
    with open(txt_path, 'w') as f:
        f.write(output_text)
    print(f"\nResults saved: {txt_path}")

    # Generate comparison charts
    generate_equity_charts(all_results, project_root)

    print("\nValidation complete.")


if __name__ == '__main__':
    main()
