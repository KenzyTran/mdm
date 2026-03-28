"""
VN30 MDM v2 Backtest Report Script

Runs MDM v2 with the best sweep config on full VN30 data, generates
performance metrics, buy-and-hold comparison, and a multi-panel dashboard
chart.

Outputs:
    - output/vn30_backtest_results.csv   (metric comparison table)
    - output/vn30_backtest_summary.txt   (text summary)
    - output/vn30_dashboard.png          (3-panel dashboard chart)

Usage:
    uv run python analysis/backtest_vn30.py
    uv run python analysis/backtest_vn30.py --config-file output/vn30_best_config.txt
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
from strategies.mdm_v2.performance import V2PerformanceAnalyzer
from strategies.mdm_v2.vn30_filters import apply_vn30_filters
from core.data_loader import DataLoader


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WARMUP_START = '2012-01-01'
DATA_START = '2014-01-01'
TRAIN_END = '2019-12-31'
TEST_START = '2020-01-01'


# ---------------------------------------------------------------------------
# Section 1: Load best config
# ---------------------------------------------------------------------------

def load_best_config(config_path: str) -> MDMV2Config:
    """Load MDMV2Config from a key=value config file.

    The config file is written by sweep_vn30.py with one parameter per line
    in ``key=value`` format.  Numeric values are converted to int or float
    as appropriate; boolean strings ('True'/'False') are converted to bool.

    If the config file does not exist, returns MDMV2Config() with defaults
    and prints a warning.

    Args:
        config_path: Path to the config text file.

    Returns:
        MDMV2Config populated from the file, or defaults if missing.
    """
    if not os.path.exists(config_path):
        print(f"WARNING: Config file not found at {config_path}. Using default config.")
        return MDMV2Config()

    params = {}
    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip()

            # Convert value types
            if val.lower() in ('true', 'false'):
                params[key] = val.lower() == 'true'
            else:
                try:
                    # Try int first, then float
                    if '.' in val:
                        params[key] = float(val)
                    else:
                        params[key] = int(val)
                except ValueError:
                    params[key] = val

    # Filter to only valid MDMV2Config fields
    valid_fields = {f.name for f in MDMV2Config.__dataclass_fields__.values()}
    filtered = {k: v for k, v in params.items() if k in valid_fields}

    config = MDMV2Config(**filtered)
    return config


# ---------------------------------------------------------------------------
# Section 2: Buy-and-hold metrics
# ---------------------------------------------------------------------------

def compute_buy_and_hold(df: pd.DataFrame) -> dict:
    """Compute buy-and-hold performance metrics from close prices.

    Args:
        df: DataFrame with 'close' column (at least 2 rows).

    Returns:
        Dict with keys: total_return, annualized_return, max_drawdown,
        sharpe_ratio.
    """
    if len(df) < 2:
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
        }

    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    total_return = (end_price / start_price) - 1.0

    n_days = len(df)
    years = n_days / 252.0
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    cummax = df['close'].cummax()
    drawdown = (df['close'] - cummax) / cummax
    max_drawdown = drawdown.min()

    daily_returns = df['close'].pct_change().dropna()
    if len(daily_returns) > 0 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe,
    }


# ---------------------------------------------------------------------------
# Section 3: Dashboard chart
# ---------------------------------------------------------------------------

def generate_vn30_dashboard(v2_results: pd.DataFrame,
                            analyzer: V2PerformanceAnalyzer,
                            bh_metrics: dict,
                            output_path: str = 'output/vn30_dashboard.png'):
    """Generate 3-panel VN30 dashboard PNG.

    Panels:
        1. VN30 price with BUY/CASH/SELL signal markers
        2. Equity curve (MDM v2 vs buy-and-hold, both starting at 1.0)
        3. Drawdown chart from analyzer.drawdown_series()

    Args:
        v2_results: Engine results DataFrame (filtered to analysis period).
        analyzer: V2PerformanceAnalyzer for the analysis period.
        bh_metrics: Buy-and-hold metrics dict (for reference only).
        output_path: Path for output PNG file.
    """
    from matplotlib.lines import Line2D

    dates = v2_results['date']

    # Equity curves
    v2_equity = analyzer.equity
    bh_equity = v2_results['close'] / v2_results['close'].iloc[0]

    # Drawdown
    v2_drawdown = analyzer.drawdown_series()

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(16, 12), sharex=True,
        gridspec_kw={'height_ratios': [3, 2, 1]}
    )

    # --- Panel 1: VN30 price with signal markers ---
    ax1.plot(dates, v2_results['close'].values, color='black', linewidth=0.8, label='VN30')

    # Signal markers from state transitions
    for idx in range(1, len(v2_results)):
        action = v2_results.iloc[idx].get('action', '')
        if not action:
            continue
        sig_date = v2_results.iloc[idx]['date']
        price = v2_results.iloc[idx]['close']
        if 'BUY' in str(action).upper():
            ax1.plot(sig_date, price, '^', color='green', markersize=8, alpha=0.8, zorder=5)
        elif 'SELL' in str(action).upper():
            ax1.plot(sig_date, price, 'v', color='red', markersize=8, alpha=0.8, zorder=5)
        elif 'CASH' in str(action).upper():
            ax1.plot(sig_date, price, 'o', color='gray', markersize=6, alpha=0.6, zorder=5)

    legend_elements = [
        Line2D([0], [0], color='black', linewidth=0.8, label='VN30'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='green', markersize=8, label='BUY'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='red', markersize=8, label='SELL'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=6, label='CASH'),
    ]
    ax1.legend(handles=legend_elements, loc='upper left', fontsize=8)
    ax1.set_ylabel('VN30 Index')
    ax1.set_title('VN30 MDM v2 Backtest Dashboard')
    ax1.grid(True, alpha=0.3)

    # Train / Test boundary
    boundary = pd.Timestamp(TEST_START)
    for ax in [ax1, ax2, ax3]:
        ax.axvline(boundary, color='purple', linestyle='--', alpha=0.5, linewidth=1)
    ax1.text(boundary, ax1.get_ylim()[1] * 0.95, ' Train | Test',
             color='purple', fontsize=9, va='top')

    # --- Panel 2: Equity curve ---
    ax2.plot(dates, v2_equity.values, label='MDM v2', color='blue', linewidth=1.5)
    ax2.plot(dates, bh_equity.values, label='Buy-and-Hold', color='gray', linewidth=1.0, alpha=0.7)
    ax2.set_ylabel('Equity (normalized)')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)

    # --- Panel 3: Drawdown ---
    ax3.fill_between(dates, v2_drawdown.values, 0, color='red', alpha=0.3)
    ax3.plot(dates, v2_drawdown.values, color='red', linewidth=0.8)
    ax3.set_ylabel('Drawdown')
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Dashboard saved: {output_path}")


# ---------------------------------------------------------------------------
# Section 4: Text summary
# ---------------------------------------------------------------------------

def generate_text_summary(analyzer: V2PerformanceAnalyzer,
                          bh_metrics: dict,
                          config: MDMV2Config,
                          train_analyzer: V2PerformanceAnalyzer = None,
                          test_analyzer: V2PerformanceAnalyzer = None) -> str:
    """Generate formatted text summary of backtest results.

    Args:
        analyzer: V2PerformanceAnalyzer for the full period.
        bh_metrics: Buy-and-hold metrics dict for the full period.
        config: MDMV2Config used for the backtest.
        train_analyzer: Optional analyzer for the training period.
        test_analyzer: Optional analyzer for the test period.

    Returns:
        Formatted text string with backtest summary.
    """
    summary = analyzer.summary()

    lines = []
    lines.append("=" * 50)
    lines.append("VN30 MDM v2 Backtest Summary")
    lines.append("=" * 50)
    lines.append(f"Date: {date.today().isoformat()}")
    lines.append(f"Config: {config.name}")
    lines.append(f"  correction_threshold={config.correction_threshold}, "
                 f"ftd_min_rally_day={config.ftd_min_rally_day}, "
                 f"dd_cash_threshold={config.dd_cash_threshold}")
    lines.append("")

    lines.append(f"Full Period ({DATA_START[:4]}-present):")
    lines.append(f"  MDM v2:       Sharpe={summary['sharpe_ratio']:.3f}, "
                 f"Return={summary['total_return'] * 100:.1f}%, "
                 f"MaxDD={summary['max_drawdown'] * 100:.1f}%, "
                 f"WinRate={summary['win_rate'] * 100:.1f}%")
    lines.append(f"  Buy-and-Hold: Sharpe={bh_metrics['sharpe_ratio']:.3f}, "
                 f"Return={bh_metrics['total_return'] * 100:.1f}%, "
                 f"MaxDD={bh_metrics['max_drawdown'] * 100:.1f}%")
    lines.append("")

    if train_analyzer is not None:
        train_sharpe = train_analyzer.sharpe_ratio()
        lines.append(f"Train Period ({DATA_START[:4]}-{TRAIN_END[:4]}):")
        lines.append(f"  MDM v2 Sharpe: {train_sharpe:.3f}")
        lines.append("")

    if test_analyzer is not None:
        test_sharpe = test_analyzer.sharpe_ratio()
        lines.append(f"Test Period ({TEST_START[:4]}-present):")
        lines.append(f"  MDM v2 Sharpe: {test_sharpe:.3f}")
        lines.append("")

    if train_analyzer is not None and test_analyzer is not None:
        train_sharpe = train_analyzer.sharpe_ratio()
        test_sharpe = test_analyzer.sharpe_ratio()
        gap = abs(train_sharpe - test_sharpe)
        status = "PASS" if gap <= 1.5 else "WARNING"
        lines.append(f"Train/Test Gap: {gap:.3f} ({status} -- threshold 1.5)")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section 5: Main
# ---------------------------------------------------------------------------

def main():
    """Run VN30 backtest pipeline."""
    parser = argparse.ArgumentParser(
        description='VN30 MDM v2 Backtest and Report'
    )
    parser.add_argument(
        '--config-file',
        type=str,
        default=None,
        help='Path to best config file (default: output/vn30_best_config.txt)'
    )
    parser.add_argument(
        '--sweep-csv',
        type=str,
        default=None,
        help='Path to sweep results CSV (default: output/vn30_sweep_results.csv)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory (default: output/)'
    )
    args = parser.parse_args()

    # Resolve project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_dir = args.output_dir or os.path.join(project_root, 'output')
    config_file = args.config_file or os.path.join(project_root, 'output', 'vn30_best_config.txt')

    print("=" * 60)
    print("VN30 MDM v2 BACKTEST PIPELINE")
    print("=" * 60)

    # 1. Load config
    print("\n[1/5] Loading config...")
    config = load_best_config(config_file)
    print(f"  Config: {config.name}")
    print(f"  Parameters: correction_threshold={config.correction_threshold}, "
          f"ftd_min_rally_day={config.ftd_min_rally_day}, "
          f"dd_cash_threshold={config.dd_cash_threshold}")

    # 2. Load VN30 data
    print("\n[2/5] Loading VN30 data...")
    loader = DataLoader('vn30', data_dir=project_root)
    df = loader.load(start_date=WARMUP_START)
    print(f"  VN30 data: {len(df)} rows ({df['date'].min().date()} to {df['date'].max().date()})")

    # Apply VN30 microstructure filters
    df = apply_vn30_filters(df)
    print(f"  Applied VN30 filters (is_limit_day, is_expiry_day columns)")

    # 3. Run engine on full period
    print("\n[3/5] Running MDM v2 engine...")
    engine = MDMV2Engine(config)
    full_results = engine.run(df)
    full_trades = engine.get_trades()

    # Filter to analysis period (DATA_START onward)
    analysis_results = full_results[
        full_results['date'] >= pd.Timestamp(DATA_START)
    ].copy().reset_index(drop=True)
    print(f"  Analysis period: {len(analysis_results)} rows, {len(full_trades)} trades")

    # Full period analyzer
    full_analyzer = V2PerformanceAnalyzer(analysis_results, full_trades)

    # Full period buy-and-hold
    bh_metrics = compute_buy_and_hold(analysis_results)

    # Train period
    train_results = analysis_results[
        analysis_results['date'] <= pd.Timestamp(TRAIN_END)
    ].copy().reset_index(drop=True)
    train_analyzer = V2PerformanceAnalyzer(train_results) if len(train_results) > 1 else None

    # Test period
    test_results = analysis_results[
        analysis_results['date'] >= pd.Timestamp(TEST_START)
    ].copy().reset_index(drop=True)
    test_analyzer = V2PerformanceAnalyzer(test_results) if len(test_results) > 1 else None

    # 4. Generate outputs
    print("\n[4/5] Generating outputs...")

    # Dashboard PNG
    dashboard_path = os.path.join(output_dir, 'vn30_dashboard.png')
    generate_vn30_dashboard(analysis_results, full_analyzer, bh_metrics, dashboard_path)

    # Text summary
    summary_text = generate_text_summary(
        full_analyzer, bh_metrics, config, train_analyzer, test_analyzer
    )
    txt_path = os.path.join(output_dir, 'vn30_backtest_summary.txt')
    os.makedirs(output_dir, exist_ok=True)
    with open(txt_path, 'w') as f:
        f.write(summary_text)
    print(f"  Summary saved: {txt_path}")

    # CSV metrics
    full_summary = full_analyzer.summary()
    metrics_rows = [
        {'metric': 'total_return', 'mdm_v2': full_summary['total_return'], 'buy_and_hold': bh_metrics['total_return']},
        {'metric': 'annualized_return', 'mdm_v2': full_summary['annualized_return'], 'buy_and_hold': bh_metrics['annualized_return']},
        {'metric': 'max_drawdown', 'mdm_v2': full_summary['max_drawdown'], 'buy_and_hold': bh_metrics['max_drawdown']},
        {'metric': 'sharpe_ratio', 'mdm_v2': full_summary['sharpe_ratio'], 'buy_and_hold': bh_metrics['sharpe_ratio']},
        {'metric': 'win_rate', 'mdm_v2': full_summary['win_rate'], 'buy_and_hold': float('nan')},
    ]
    metrics_df = pd.DataFrame(metrics_rows)
    csv_path = os.path.join(output_dir, 'vn30_backtest_results.csv')
    metrics_df.to_csv(csv_path, index=False)
    print(f"  CSV saved: {csv_path}")

    # 5. Print summary
    print("\n[5/5] Results:")
    print(summary_text)

    print("\n" + "=" * 60)
    print("VN30 BACKTEST COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
