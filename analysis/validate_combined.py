"""
Combined Integration Validation (VAL-05, VAL-07)

A/B comparison: V2 baseline (all filters OFF) vs V2 all-filters (all filters ON)
on NASDAQ and VN30. Walk-forward validation: train pre-2020, test 2020-2026.
CASH duration guard: warns if all-on exceeds 130% of baseline.

Usage:
    uv run python analysis/validate_combined.py
"""

import sys
import os
from pathlib import Path
from datetime import date

# Resolve project root, handling worktree paths for data access
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
MAIN_REPO = PROJECT_ROOT
if '.claude' in str(PROJECT_ROOT) and 'worktrees' in str(PROJECT_ROOT):
    parts = PROJECT_ROOT.parts
    for i, part in enumerate(parts):
        if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
            MAIN_REPO = Path(*parts[:i])
            break

sys.path.insert(0, str(PROJECT_ROOT))

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
    """Create baseline config with ALL filters explicitly OFF.

    Per D-01, Pitfall 1: baseline must have ALL v5.0 filters disabled
    to measure the true impact of enabling everything together.

    Returns:
        MDMV2Config with all filters disabled.
    """
    return MDMV2Config(
        qe_floor_enabled=False,
        sell_acceleration_enabled=False,
        buy_filter_enabled=False,
        buy_confirmation_enabled=False,
        name="baseline",
    )


def make_allon_config():
    """Create config with ALL v5.0 filters enabled.

    Returns:
        MDMV2Config with all filters enabled.
    """
    return MDMV2Config(
        qe_floor_enabled=True,
        sell_acceleration_enabled=True,
        buy_filter_enabled=True,
        buy_confirmation_enabled=True,
        confirmation_window_days=3,
        confirmation_max_dd=1,
        liquidity_csv_path=str(MAIN_REPO / "data" / "global_liquidity.csv"),
        name="all_filters",
    )


def compute_metrics(results_df, trades):
    """Compute performance metrics from engine results.

    Uses V2PerformanceAnalyzer with state[i-1] rule (CRITICAL: avoid
    look-ahead bias per CLAUDE.md equity formula rule).

    Args:
        results_df: Full engine results DataFrame.
        trades: List of trade dicts from engine.

    Returns:
        Dict with total_return, cagr, max_drawdown, sharpe, trade_count, equity.
    """
    analyzer = V2PerformanceAnalyzer(results_df, trades)

    exit_trades = [t for t in trades if t.get('type') in ('CASH_EXIT', 'SHORT_COVER')]

    return {
        'total_return': analyzer.total_return(),
        'cagr': analyzer.annualized_return(),
        'max_drawdown': analyzer.max_drawdown(),
        'sharpe': analyzer.sharpe_ratio(),
        'trade_count': len(exit_trades),
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
            'cagr': 0.0,
            'max_drawdown': 0.0,
            'sharpe': 0.0,
            'trade_count': 0,
            'equity': pd.Series([1.0]),
        }

    # Filter trades to period
    period_trades = [
        t for t in trades
        if start_ts <= pd.Timestamp(t.get('date', t.get('exit_date', '1900-01-01'))) <= end_ts
    ]

    return compute_metrics(period_df, period_trades)


def compute_avg_cash_duration(results_df):
    """Average consecutive days in CASH state per CASH episode."""
    states = results_df['state'].values
    durations = []
    run = 0
    for s in states:
        if s == 'CASH':
            run += 1
        else:
            if run > 0:
                durations.append(run)
            run = 0
    if run > 0:
        durations.append(run)
    return np.mean(durations) if durations else 0.0


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
    """Run the full A/B validation with walk-forward and CASH duration analysis.

    For each period:
    1. Load market data with warmup
    2. Run V2 baseline (all filters OFF)
    3. Run V2 all-filters (all filters ON)
    4. Compare metrics side-by-side

    Then perform walk-forward validation on NASDAQ and CASH duration guard.

    Returns:
        Tuple of (output_text, all_results).
    """
    data_root = str(MAIN_REPO)

    output_lines = []
    output_lines.append("=" * 70)
    output_lines.append("=== COMBINED INTEGRATION VALIDATION (A/B + Walk-Forward + CASH) ===")
    output_lines.append("=" * 70)
    output_lines.append(f"Date: {date.today().isoformat()}")
    output_lines.append("")

    all_results = {}

    for period_name, period_info in PERIODS.items():
        start = period_info['start']
        end = period_info['end']
        market = period_info['market']

        output_lines.append(f"--- {period_name} ({start} to {end}) ---")

        # Load data with warmup
        loader = DataLoader(market, data_dir=data_root)
        warmup_start_dt = pd.Timestamp(start) - pd.Timedelta(days=int(WARMUP_DAYS * 1.5))
        warmup_start = warmup_start_dt.strftime('%Y-%m-%d')
        df = loader.load(start_date=warmup_start, end_date=end)
        output_lines.append(f"  Data loaded: {len(df)} rows ({market})")

        # Run baseline (all filters OFF)
        baseline_config = make_baseline_config()
        baseline_engine = MDMV2Engine(baseline_config)
        baseline_results = baseline_engine.run(df)
        baseline_trades = baseline_engine.get_trades()
        baseline_metrics = compute_metrics(baseline_results, baseline_trades)

        # Run all-filters (all filters ON)
        allon_config = make_allon_config()
        allon_engine = MDMV2Engine(allon_config)
        allon_results = allon_engine.run(df)
        allon_trades = allon_engine.get_trades()
        allon_metrics = compute_metrics(allon_results, allon_trades)

        # Print comparison table
        output_lines.append("")
        headers = ["Metric", "Baseline", "All-Filters", "Delta"]
        rows = [
            ("Total Return",
             f"{baseline_metrics['total_return']:.1%}",
             f"{allon_metrics['total_return']:.1%}",
             f"{allon_metrics['total_return'] - baseline_metrics['total_return']:+.1%}"),
            ("CAGR",
             f"{baseline_metrics['cagr']:.1%}",
             f"{allon_metrics['cagr']:.1%}",
             f"{allon_metrics['cagr'] - baseline_metrics['cagr']:+.1%}"),
            ("Max Drawdown",
             f"{baseline_metrics['max_drawdown']:.1%}",
             f"{allon_metrics['max_drawdown']:.1%}",
             f"{allon_metrics['max_drawdown'] - baseline_metrics['max_drawdown']:+.1%}"),
            ("Sharpe",
             f"{baseline_metrics['sharpe']:.2f}",
             f"{allon_metrics['sharpe']:.2f}",
             f"{allon_metrics['sharpe'] - baseline_metrics['sharpe']:+.2f}"),
            ("Trade Count",
             f"{baseline_metrics['trade_count']}",
             f"{allon_metrics['trade_count']}",
             f"{allon_metrics['trade_count'] - baseline_metrics['trade_count']:+d}"),
        ]
        output_lines.append(format_table(headers, rows, col_widths=[18, 14, 14, 14]))
        output_lines.append("")

        all_results[period_name] = {
            'baseline_metrics': baseline_metrics,
            'allon_metrics': allon_metrics,
            'baseline_results': baseline_results,
            'allon_results': allon_results,
            'start': start,
            'end': end,
            'market': market,
        }

    # CASH Duration Guard
    output_lines.append("=" * 70)
    output_lines.append("=== CASH Duration Guard ===")
    output_lines.append("=" * 70)
    output_lines.append("")

    for period_name, data in all_results.items():
        baseline_cash_avg = compute_avg_cash_duration(data['baseline_results'])
        allon_cash_avg = compute_avg_cash_duration(data['allon_results'])
        ratio = allon_cash_avg / baseline_cash_avg if baseline_cash_avg > 0 else 0.0

        output_lines.append(f"  {period_name}:")
        output_lines.append(f"    Baseline avg CASH duration: {baseline_cash_avg:.1f} days")
        output_lines.append(f"    All-Filters avg CASH duration: {allon_cash_avg:.1f} days")
        output_lines.append(f"    Ratio: {ratio:.2f}")

        if ratio > 1.3:
            output_lines.append(f"    WARNING: CASH duration exceeds 130% of baseline (ratio={ratio:.2f})")
        else:
            output_lines.append(f"    PASS: CASH duration within 130% of baseline")
        output_lines.append("")

    # Walk-forward validation on NASDAQ
    output_lines.append("=" * 70)
    output_lines.append("=== Walk-Forward Validation (NASDAQ) ===")
    output_lines.append("=" * 70)
    output_lines.append("")

    # Use already-computed NASDAQ all-filters results
    nasdaq_data = all_results.get('nasdaq_full')
    if nasdaq_data:
        allon_results_full = nasdaq_data['allon_results']
        # Re-run engine to get trades for period filtering
        loader = DataLoader('nasdaq', data_dir=data_root)
        warmup_start_dt = pd.Timestamp('2004-01-01') - pd.Timedelta(days=int(WARMUP_DAYS * 1.5))
        warmup_start = warmup_start_dt.strftime('%Y-%m-%d')
        df_full = loader.load(start_date=warmup_start)

        allon_config = make_allon_config()
        allon_engine = MDMV2Engine(allon_config)
        allon_results_wf = allon_engine.run(df_full)
        allon_trades_wf = allon_engine.get_trades()

        # In-sample: pre-2020
        is_metrics = compute_period_metrics(
            allon_results_wf, allon_trades_wf,
            '2004-01-01', '2019-12-31'
        )

        # Out-of-sample: 2020-2026
        oos_metrics = compute_period_metrics(
            allon_results_wf, allon_trades_wf,
            WALK_FORWARD_SPLIT, '2026-12-31'
        )

        # Compute degradation with zero-division guard
        is_tr = is_metrics['total_return']
        oos_tr = oos_metrics['total_return']
        if abs(is_tr) > 0:
            degradation = (is_tr - oos_tr) / abs(is_tr)
        else:
            degradation = 0.0

        wf_headers = ["Metric", "In-Sample", "Out-of-Sample", "Degradation"]
        wf_rows = [
            ("Total Return",
             f"{is_metrics['total_return']:.1%}",
             f"{oos_metrics['total_return']:.1%}",
             f"{degradation:.1%}"),
            ("CAGR",
             f"{is_metrics['cagr']:.1%}",
             f"{oos_metrics['cagr']:.1%}",
             f"-"),
            ("Max Drawdown",
             f"{is_metrics['max_drawdown']:.1%}",
             f"{oos_metrics['max_drawdown']:.1%}",
             f"-"),
            ("Sharpe",
             f"{is_metrics['sharpe']:.2f}",
             f"{oos_metrics['sharpe']:.2f}",
             f"-"),
            ("Trade Count",
             f"{is_metrics['trade_count']}",
             f"{oos_metrics['trade_count']}",
             f"-"),
        ]
        output_lines.append(format_table(wf_headers, wf_rows, col_widths=[18, 16, 18, 14]))
        output_lines.append("")

        # Walk-forward degradation warning
        if abs(degradation) > 0.10:
            output_lines.append(f"  WARNING: Walk-forward degradation {degradation:.1%} exceeds 10% threshold")
        else:
            output_lines.append(f"  PASS: Walk-forward degradation {degradation:.1%} within 10% threshold")

        output_lines.append("")

    output_text = '\n'.join(output_lines)
    return output_text, all_results


def generate_equity_chart(all_results, project_root):
    """Generate combined equity comparison chart.

    Shows baseline vs all-filters equity curves for each market.

    Args:
        all_results: Dict of period results from run_validation().
        project_root: Project root directory for output paths.
    """
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)

    n_periods = len(all_results)
    fig, axes = plt.subplots(n_periods, 1, figsize=(14, 6 * n_periods))

    if n_periods == 1:
        axes = [axes]

    for ax, (period_name, data) in zip(axes, all_results.items()):
        baseline_results = data['baseline_results']
        allon_results = data['allon_results']
        baseline_equity = data['baseline_metrics']['equity']
        allon_equity = data['allon_metrics']['equity']

        baseline_dates = baseline_results['date'].values
        allon_dates = allon_results['date'].values

        ax.plot(baseline_dates[:len(baseline_equity)], baseline_equity.values,
                color='blue', linewidth=1.0, alpha=0.8,
                label=f'Baseline (return={data["baseline_metrics"]["total_return"]:.1%})')
        ax.plot(allon_dates[:len(allon_equity)], allon_equity.values,
                color='green', linewidth=1.0, alpha=0.8,
                label=f'All-Filters (return={data["allon_metrics"]["total_return"]:.1%})')

        ax.set_title(f'{period_name}: Equity Curves (Baseline vs All-Filters)')
        ax.set_ylabel('Equity (starting at 1.0)')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    chart_path = os.path.join(output_dir, 'combined_equity_comparison.png')
    fig.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Chart saved: {chart_path}")


def run_validation_main():
    """Entry point: run validation, save outputs, print results."""
    output_dir = str(MAIN_REPO / 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Run validation
    output_text, all_results = run_validation()

    # Print to console
    print(output_text)

    # Save text output
    txt_path = os.path.join(output_dir, 'combined_validation.txt')
    with open(txt_path, 'w') as f:
        f.write(output_text)
    print(f"\nResults saved: {txt_path}")

    # Generate equity comparison chart
    generate_equity_chart(all_results, str(MAIN_REPO))

    print("\nValidation complete.")


if __name__ == '__main__':
    run_validation_main()
