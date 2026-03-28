"""
MDM V2 Validation and Performance Analysis Script

Orchestrates the full Phase 5 pipeline:
1. Auto-load best config from parameter sweep results
2. Run V2 and classic engines on NASDAQ data
3. Compute match rates for train/held-out periods with per-type breakdown
4. Generate three-way performance comparison (V2 vs buy-and-hold vs classic)
5. Produce multi-panel dashboard chart
6. Save CSV and text summary outputs

Usage:
    uv run python analysis/validate_v2.py
    uv run python analysis/validate_v2.py --sweep-csv output/sweep_results.csv
"""

import sys
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from strategies.mdm_v2.performance import V2PerformanceAnalyzer, check_degradation
from strategies.mdm_classic.mdm_engine import MDMEngine
from strategies.mdm_classic.performance import PerformanceAnalyzer
from core.signal_comparator import extract_model_signals, compare_signals
from core.data_loader import DataLoader
from core.signal_loader import load_signal_fixture


# Period definitions
TRAIN_START = '2019-01-01'
TRAIN_END = '2022-12-31'
HELDOUT_START = '2023-01-01'
HELDOUT_END = '2026-12-31'
WARMUP_START = '2017-01-01'
ANALYSIS_START = '2019-01-01'

# Degradation threshold per D-01
DEGRADATION_THRESHOLD = 0.10


# ---------------------------------------------------------------------------
# Section 2: Load best config from sweep CSV
# ---------------------------------------------------------------------------

def load_best_config(sweep_csv_path: str) -> MDMV2Config:
    """Load the best MDMV2Config from parameter sweep results CSV.

    The CSV is sorted by match_rate descending, so the first row is the best.
    Score columns are excluded; remaining columns are config parameters.

    Args:
        sweep_csv_path: Path to the sweep results CSV file.

    Returns:
        MDMV2Config populated with the best parameters.

    Raises:
        SystemExit: If the sweep CSV file is not found.
    """
    if not os.path.exists(sweep_csv_path):
        print(f"ERROR: Sweep results not found at {sweep_csv_path}.")
        print("Run parameter sweep first: uv run python analysis/hypothesis/run_sweep.py")
        sys.exit(1)

    df = pd.read_csv(sweep_csv_path)
    if len(df) == 0:
        print(f"ERROR: Sweep results CSV is empty: {sweep_csv_path}")
        sys.exit(1)

    best_row = df.iloc[0]

    # Score columns to exclude (not config parameters)
    score_cols = {
        'hypothesis', 'match_rate', 'buy_rate', 'sell_rate',
        'cash_rate', 'total_published', 'total_matched'
    }
    param_cols = [c for c in df.columns if c not in score_cols]

    # Build config dict from parameter columns
    params = {}
    for col in param_cols:
        val = best_row[col]
        # Convert numpy types to Python native
        if isinstance(val, (np.integer,)):
            val = int(val)
        elif isinstance(val, (np.floating,)):
            val = float(val)
        elif isinstance(val, (np.bool_,)):
            val = bool(val)
        params[col] = val

    # Set name from hypothesis if available
    if 'hypothesis' in best_row.index:
        params['name'] = str(best_row['hypothesis'])

    config = MDMV2Config(**params)
    return config


# ---------------------------------------------------------------------------
# Section 3: Validate match rates
# ---------------------------------------------------------------------------

def validate_match_rates(v2_results: pd.DataFrame,
                         published_signals: pd.DataFrame) -> dict:
    """Compute train and held-out match rates with per-type breakdown.

    Args:
        v2_results: V2 engine results DataFrame with date, state columns.
        published_signals: Published signals DataFrame with date, signal columns.

    Returns:
        Dict with train_match_rate, heldout_match_rate, degradation_pct,
        degradation_pass, train_per_type, heldout_per_type, train_count,
        heldout_count.
    """
    model_signals = extract_model_signals(v2_results)

    # Split published signals into train and held-out periods
    pub_dates = pd.to_datetime(published_signals['date'])
    train_pub = published_signals[pub_dates <= pd.Timestamp(TRAIN_END)].copy()
    heldout_pub = published_signals[pub_dates >= pd.Timestamp(HELDOUT_START)].copy()

    # Score each period
    train_result = compare_signals(model_signals, train_pub)
    heldout_result = compare_signals(model_signals, heldout_pub)

    # Use check_degradation from Plan 01 (match_rate is 0-100 scale)
    degradation_pct, degradation_pass = check_degradation(
        train_result['match_rate'],
        heldout_result['match_rate'],
        threshold=DEGRADATION_THRESHOLD
    )

    return {
        'train_match_rate': train_result['match_rate'],
        'heldout_match_rate': heldout_result['match_rate'],
        'degradation_pct': degradation_pct,
        'degradation_pass': degradation_pass,
        'train_per_type': train_result['per_type'],
        'heldout_per_type': heldout_result['per_type'],
        'train_count': train_result['total_published'],
        'heldout_count': heldout_result['total_published'],
    }


# ---------------------------------------------------------------------------
# Section 4: Build comparison table
# ---------------------------------------------------------------------------

def _compute_buy_and_hold_metrics(df_period: pd.DataFrame) -> dict:
    """Compute buy-and-hold metrics for a filtered period DataFrame."""
    if len(df_period) < 2:
        return {
            'total_return': 0.0, 'annualized_return': 0.0,
            'max_drawdown': 0.0, 'sharpe_ratio': 0.0,
            'win_rate': float('nan'), 'num_trades': 0,
        }

    start_price = df_period.iloc[0]['close']
    end_price = df_period.iloc[-1]['close']
    total_return = (end_price / start_price) - 1.0

    n_days = len(df_period)
    years = n_days / 252.0
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    cummax = df_period['close'].cummax()
    drawdown = (df_period['close'] - cummax) / cummax
    max_drawdown = drawdown.min()

    # Sharpe from daily close returns
    daily_returns = df_period['close'].pct_change().dropna()
    if len(daily_returns) > 0 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe,
        'win_rate': float('nan'),
        'num_trades': 0,
    }


def _compute_classic_equity(classic_results: pd.DataFrame) -> pd.Series:
    """Build daily equity curve for classic engine (HOLDING = invested)."""
    closes = classic_results['close'].values
    states = classic_results['state'].values
    n = len(closes)
    equity = np.ones(n, dtype=float)

    for i in range(1, n):
        prev_state = states[i - 1]
        if prev_state in ('HOLDING', 'WAITING_SELL'):
            equity[i] = equity[i - 1] * (closes[i] / closes[i - 1])
        else:
            equity[i] = equity[i - 1]

    return pd.Series(equity, index=classic_results.index)


def _compute_classic_metrics(classic_period: pd.DataFrame,
                             classic_trades: list) -> dict:
    """Compute performance metrics for classic engine on a period."""
    if len(classic_period) < 2:
        return {
            'total_return': 0.0, 'annualized_return': 0.0,
            'max_drawdown': 0.0, 'sharpe_ratio': 0.0,
            'win_rate': 0.0, 'num_trades': 0,
        }

    equity = _compute_classic_equity(classic_period)
    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1.0

    n_days = len(classic_period)
    years = n_days / 252.0
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    cummax = equity.cummax()
    dd = (equity - cummax) / cummax
    max_drawdown = dd.min()

    daily_returns = equity.pct_change().dropna()
    if len(daily_returns) > 0 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Filter trades to this period
    period_start = classic_period['date'].min()
    period_end = classic_period['date'].max()
    period_trades = [
        t for t in classic_trades
        if t.get('type') == 'SELL'
        and pd.Timestamp(t.get('date', '1900-01-01')) >= period_start
        and pd.Timestamp(t.get('date', '1900-01-01')) <= period_end
    ]
    wins = sum(1 for t in period_trades if t.get('pnl', 0) > 0)
    num_trades = len(period_trades)
    win_rate = wins / num_trades if num_trades > 0 else 0.0

    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe,
        'win_rate': win_rate,
        'num_trades': num_trades,
    }


def build_comparison_table(v2_results: pd.DataFrame,
                           v2_trades: list,
                           classic_results: pd.DataFrame,
                           classic_trades: list,
                           analysis_start: str = ANALYSIS_START) -> pd.DataFrame:
    """Build three-way comparison table across three time periods.

    Compares MDM v2, buy-and-hold, and MDM classic for:
    - Training period (2019-2022)
    - Held-out period (2023-2026)
    - Full period (2019-2026)

    Args:
        v2_results: V2 engine results DataFrame.
        v2_trades: V2 engine trades list.
        classic_results: Classic engine results DataFrame.
        classic_trades: Classic engine trades list.
        analysis_start: Start date for analysis period.

    Returns:
        DataFrame with 9 rows (3 periods x 3 strategies) and columns:
        period, strategy, total_return, annualized_return, max_drawdown,
        sharpe_ratio, win_rate, num_trades.
    """
    periods = [
        ("2019-2022", TRAIN_START, TRAIN_END),
        ("2023-2026", HELDOUT_START, HELDOUT_END),
        ("2019-2026", ANALYSIS_START, HELDOUT_END),
    ]

    rows = []
    for period_name, start, end in periods:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)

        # Filter data to period
        v2_period = v2_results[
            (v2_results['date'] >= start_ts) & (v2_results['date'] <= end_ts)
        ].copy().reset_index(drop=True)

        classic_period = classic_results[
            (classic_results['date'] >= start_ts) & (classic_results['date'] <= end_ts)
        ].copy().reset_index(drop=True)

        # MDM V2 metrics
        if len(v2_period) > 1:
            v2_analyzer = V2PerformanceAnalyzer(v2_period, v2_trades)
            v2_summary = v2_analyzer.summary()
            # Filter v2 trades to period for trade count
            v2_period_trades = [
                t for t in v2_trades
                if t.get('type') == 'CASH_EXIT'
                and pd.Timestamp(t.get('date', '1900-01-01')) >= start_ts
                and pd.Timestamp(t.get('date', '1900-01-01')) <= end_ts
            ]
            v2_metrics = {
                'total_return': v2_summary['total_return'],
                'annualized_return': v2_summary['annualized_return'],
                'max_drawdown': v2_summary['max_drawdown'],
                'sharpe_ratio': v2_summary['sharpe_ratio'],
                'win_rate': v2_summary['win_rate'],
                'num_trades': len(v2_period_trades),
            }
        else:
            v2_metrics = {
                'total_return': 0.0, 'annualized_return': 0.0,
                'max_drawdown': 0.0, 'sharpe_ratio': 0.0,
                'win_rate': 0.0, 'num_trades': 0,
            }

        # Buy-and-hold metrics (use v2_period close prices)
        bh_metrics = _compute_buy_and_hold_metrics(v2_period)

        # Classic metrics
        classic_metrics = _compute_classic_metrics(classic_period, classic_trades)

        # Add rows
        rows.append({'period': period_name, 'strategy': 'MDM v2', **v2_metrics})
        rows.append({'period': period_name, 'strategy': 'Buy-and-Hold', **bh_metrics})
        rows.append({'period': period_name, 'strategy': 'MDM Classic', **classic_metrics})

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Section 5: Generate dashboard
# ---------------------------------------------------------------------------

def generate_dashboard(v2_results: pd.DataFrame,
                       classic_results: pd.DataFrame,
                       published_signals: pd.DataFrame,
                       output_path: str = 'output/v2_dashboard.png'):
    """Generate multi-panel dashboard PNG.

    Three panels:
    - Top: Three equity curves (V2, buy-and-hold, classic)
    - Middle: V2 drawdown series
    - Bottom: NASDAQ price with published and model signal markers

    Args:
        v2_results: V2 engine results (full period including warm-up).
        classic_results: Classic engine results.
        published_signals: Published signals DataFrame.
        output_path: Path for output PNG file.
    """
    # Filter to analysis period
    analysis_start_ts = pd.Timestamp(ANALYSIS_START)
    v2_analysis = v2_results[v2_results['date'] >= analysis_start_ts].copy().reset_index(drop=True)
    classic_analysis = classic_results[classic_results['date'] >= analysis_start_ts].copy().reset_index(drop=True)

    # Build equity curves
    v2_analyzer = V2PerformanceAnalyzer(v2_analysis)
    v2_equity = v2_analyzer.equity

    # Buy-and-hold equity (normalized to 1.0)
    bh_equity = v2_analysis['close'] / v2_analysis['close'].iloc[0]

    # Classic equity
    classic_equity = _compute_classic_equity(classic_analysis)

    # V2 drawdown
    v2_drawdown = v2_analyzer.drawdown_series()

    # Extract model signals for overlay
    model_signals = extract_model_signals(v2_analysis)

    # Create figure
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(16, 12), sharex=True,
        gridspec_kw={'height_ratios': [3, 1, 2]}
    )

    dates = v2_analysis['date']

    # Top panel: Equity curves
    ax1.plot(dates, v2_equity.values, label='MDM V2', color='blue', linewidth=1.5)
    ax1.plot(dates, bh_equity.values, label='Buy-and-Hold', color='gray', linewidth=1.0, alpha=0.7)
    ax1.plot(dates, classic_equity.values, label='MDM Classic', color='orange', linewidth=1.0, alpha=0.7)
    ax1.set_ylabel('Equity (normalized)')
    ax1.set_title('MDM v2 Validation: Equity Curves')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Train/held-out boundary
    boundary = pd.Timestamp(HELDOUT_START)
    for ax in [ax1, ax2, ax3]:
        ax.axvline(boundary, color='purple', linestyle='--', alpha=0.5, linewidth=1)
    ax1.text(boundary, ax1.get_ylim()[1] * 0.95, ' Train | Held-out',
             color='purple', fontsize=9, va='top')

    # Middle panel: V2 drawdown
    ax2.fill_between(dates, v2_drawdown.values, 0, color='red', alpha=0.3)
    ax2.plot(dates, v2_drawdown.values, color='red', linewidth=0.8)
    ax2.set_ylabel('Drawdown')
    ax2.grid(True, alpha=0.3)

    # Bottom panel: Price with signals
    ax3.plot(dates, v2_analysis['close'].values, color='black', linewidth=0.8, label='NASDAQ')

    # Published signal markers
    pub_dates = pd.to_datetime(published_signals['date'])
    pub_in_range = published_signals[pub_dates >= analysis_start_ts]
    for _, row in pub_in_range.iterrows():
        sig_date = pd.Timestamp(row['date'])
        price_row = v2_analysis[v2_analysis['date'] == sig_date]
        if price_row.empty:
            # Find nearest date
            date_diffs = (v2_analysis['date'] - sig_date).abs()
            nearest_idx = date_diffs.idxmin()
            price = v2_analysis.loc[nearest_idx, 'close']
        else:
            price = price_row.iloc[0]['close']

        if row['signal'] == 'Buy':
            ax3.plot(sig_date, price, '^', color='green', markersize=10, alpha=0.8, zorder=5)
        elif row['signal'] == 'Sell':
            ax3.plot(sig_date, price, 'v', color='red', markersize=10, alpha=0.8, zorder=5)
        elif row['signal'] == 'Cash':
            ax3.plot(sig_date, price, 'o', color='gray', markersize=7, alpha=0.6, zorder=5)

    # Model signal markers (smaller, different shapes)
    for _, row in model_signals.iterrows():
        sig_date = pd.Timestamp(row['date'])
        if sig_date < analysis_start_ts:
            continue
        price_row = v2_analysis[v2_analysis['date'] == sig_date]
        if price_row.empty:
            continue
        price = price_row.iloc[0]['close']

        if row['signal'] == 'Buy':
            ax3.plot(sig_date, price, 'D', color='blue', markersize=5, alpha=0.6, zorder=4)
        elif row['signal'] == 'Sell':
            ax3.plot(sig_date, price, 's', color='darkred', markersize=5, alpha=0.6, zorder=4)
        elif row['signal'] == 'Cash':
            ax3.plot(sig_date, price, 'x', color='darkgray', markersize=5, alpha=0.6, zorder=4)

    ax3.set_ylabel('NASDAQ')
    ax3.set_title('Price with Published + Model Signals')
    ax3.grid(True, alpha=0.3)

    # Add legend entries for signal markers
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='^', color='w', markerfacecolor='green', markersize=10, label='Published Buy'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='red', markersize=10, label='Published Sell'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=7, label='Published Cash'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='blue', markersize=5, label='Model Buy'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='darkred', markersize=5, label='Model Sell'),
        Line2D([0], [0], marker='x', color='darkgray', markersize=5, label='Model Cash'),
    ]
    ax3.legend(handles=legend_elements, loc='upper left', fontsize=8, ncol=2)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Dashboard saved: {output_path}")


# ---------------------------------------------------------------------------
# Section 6: Save results
# ---------------------------------------------------------------------------

def save_results(comparison_table: pd.DataFrame,
                 validation_results: dict,
                 config: MDMV2Config,
                 output_dir: str = 'output/'):
    """Save CSV and text summary outputs.

    Args:
        comparison_table: Performance comparison DataFrame.
        validation_results: Dict from validate_match_rates().
        config: The MDMV2Config used.
        output_dir: Output directory path.
    """
    os.makedirs(output_dir, exist_ok=True)

    # CSV output
    csv_path = os.path.join(output_dir, 'v2_validation_results.csv')
    comparison_table.to_csv(csv_path, index=False)
    print(f"CSV saved: {csv_path}")

    # Text summary
    txt_path = os.path.join(output_dir, 'v2_validation_summary.txt')

    train_per = validation_results['train_per_type']
    heldout_per = validation_results['heldout_per_type']

    degradation_status = "PASS" if validation_results['degradation_pass'] else "FAIL"

    # Format comparison table as text
    table_text = comparison_table.to_string(index=False, float_format='{:.4f}'.format)

    summary_text = f"""MDM V2 VALIDATION SUMMARY
=========================
Date: {date.today().isoformat()}
Config: {config.name} (auto-loaded from sweep)

SIGNAL MATCH VALIDATION (PERF-03)
----------------------------------
Training (2019-2022): {validation_results['train_match_rate']:.1f}% ({validation_results['train_count']} signals)
  Buy: {train_per['Buy']['rate']:.1f}%  Sell: {train_per['Sell']['rate']:.1f}%  Cash: {train_per['Cash']['rate']:.1f}%
Held-out (2023-2026): {validation_results['heldout_match_rate']:.1f}% ({validation_results['heldout_count']} signals)
  Buy: {heldout_per['Buy']['rate']:.1f}%  Sell: {heldout_per['Sell']['rate']:.1f}%  Cash: {heldout_per['Cash']['rate']:.1f}%
Degradation: {validation_results['degradation_pct']:.1%} (threshold: 10%) -- {degradation_status}

PERFORMANCE COMPARISON (PERF-01, PERF-02)
-------------------------------------------
{table_text}
"""

    with open(txt_path, 'w') as f:
        f.write(summary_text)
    print(f"Summary saved: {txt_path}")

    return summary_text


# ---------------------------------------------------------------------------
# Section 7: Main
# ---------------------------------------------------------------------------

def main(sweep_csv: str = None):
    """Run the full validation pipeline.

    Args:
        sweep_csv: Optional path to sweep results CSV.
            Defaults to output/sweep_results.csv.
    """
    # Resolve project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Default sweep CSV path
    if sweep_csv is None:
        sweep_csv = os.path.join(project_root, 'output', 'sweep_results.csv')

    print("=" * 60)
    print("MDM V2 VALIDATION PIPELINE")
    print("=" * 60)

    # 1. Load best config
    print("\n[1/6] Loading best config from sweep results...")
    config = load_best_config(sweep_csv)
    print(f"  Config: {config.name}")
    print(f"  Parameters: correction_threshold={config.correction_threshold}, "
          f"ftd_min_rally_day={config.ftd_min_rally_day}, "
          f"dd_cash_threshold={config.dd_cash_threshold}")

    # 2. Load data
    print("\n[2/6] Loading NASDAQ data and published signals...")
    loader = DataLoader('nasdaq', data_dir=project_root)
    df = loader.load(start_date=WARMUP_START)
    print(f"  NASDAQ data: {len(df)} rows ({df['date'].min().date()} to {df['date'].max().date()})")

    signals_path = os.path.join(project_root, 'data', 'signals', 'nasdaq_signals.csv')
    published_signals = load_signal_fixture(signals_path)
    print(f"  Published signals: {len(published_signals)} signals")

    # 3. Run engines
    print("\n[3/6] Running V2 engine...")
    v2_engine = MDMV2Engine(config)
    v2_results = v2_engine.run(df)
    v2_trades = v2_engine.get_trades()
    print(f"  V2 trades: {len(v2_trades)}")

    print("  Running Classic engine...")
    classic_engine = MDMEngine()
    classic_results = classic_engine.run(df)
    classic_trades = classic_engine.get_trades()
    print(f"  Classic trades: {len(classic_trades)}")

    # 4. Validate match rates
    print("\n[4/6] Computing signal match rates...")
    # Filter to analysis period for match rate computation
    v2_analysis = v2_results[v2_results['date'] >= pd.Timestamp(ANALYSIS_START)].copy()
    validation = validate_match_rates(v2_analysis, published_signals)
    print(f"  Training match rate: {validation['train_match_rate']:.1f}%")
    print(f"  Held-out match rate: {validation['heldout_match_rate']:.1f}%")
    print(f"  Degradation: {validation['degradation_pct']:.1%} -- "
          f"{'PASS' if validation['degradation_pass'] else 'FAIL'}")

    # 5. Build comparison table
    print("\n[5/6] Building performance comparison table...")
    comparison = build_comparison_table(
        v2_results, v2_trades, classic_results, classic_trades
    )
    print(comparison.to_string(index=False))

    # 6. Generate dashboard and save results
    print("\n[6/6] Generating dashboard and saving results...")
    output_dir = os.path.join(project_root, 'output')
    dashboard_path = os.path.join(output_dir, 'v2_dashboard.png')
    generate_dashboard(v2_results, classic_results, published_signals, dashboard_path)

    summary_text = save_results(comparison, validation, config, output_dir)

    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    print(summary_text)


# ---------------------------------------------------------------------------
# Section 8: CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='MDM V2 Validation and Performance Analysis'
    )
    parser.add_argument(
        '--sweep-csv',
        type=str,
        default=None,
        help='Path to parameter sweep results CSV (default: output/sweep_results.csv)'
    )
    args = parser.parse_args()
    main(sweep_csv=args.sweep_csv)
