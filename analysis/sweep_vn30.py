"""
VN30 Sharpe-Optimized Parameter Sweep

Grid search over MDMV2Config parameter space, optimized for Sharpe ratio
on pre-2020 VN30 data. No published VN30 signals exist (D-08), so optimization
uses risk-adjusted return instead of match rate.

Per D-09: Adapts analysis/hypothesis/parameter_sweep.py with scoring_fn.
Per D-10: Uses VN30 data from 2014-2026 (avoiding low-quality 2011-2013).
Per D-11: Train/test split at 2020. Train sweep on pre-2020, validate post-2020.

Usage:
    uv run python analysis/sweep_vn30.py
    uv run python analysis/sweep_vn30.py --top-n 30
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from strategies.mdm_v2.performance import V2PerformanceAnalyzer
from strategies.mdm_v2.vn30_filters import apply_vn30_filters
from analysis.hypothesis.parameter_sweep import run_sweep, save_sweep_results, print_sweep_summary
from core.data_loader import DataLoader


# Date constants (per D-10, D-11)
WARMUP_START = '2012-01-01'   # 2 years warm-up for MA50
DATA_START = '2014-01-01'     # Analysis start (avoid low-quality 2011-2013)
TRAIN_END = '2019-12-31'      # Pre-2020 training
TEST_START = '2020-01-01'     # Post-2020 validation


# VN30-specific parameter grid (per D-07, wider ranges for VN30 volatility)
VN30_PARAM_GRID = {
    'correction_threshold': [-0.06, -0.08, -0.10, -0.12, -0.15],
    'ftd_min_rally_day': [3, 4, 5],
    'ftd_min_price_gain': [0.005, 0.008, 0.01, 0.012, 0.015],
    'dd_cash_threshold': [3, 4, 5, 6],
    'stop_loss_pct': [0.02, 0.025, 0.03, 0.04],
    'dd_window_size': [15, 20, 25],
}
# Total combinations: 5 * 3 * 5 * 4 * 4 * 3 = 3,600


def sharpe_scoring_fn(config: MDMV2Config, df: pd.DataFrame) -> dict:
    """Score a config by Sharpe ratio on provided data.

    Runs the MDMV2Engine with the given config, computes performance metrics
    via V2PerformanceAnalyzer, and returns a dict with 'score' = sharpe_ratio.

    Args:
        config: MDMV2Config instance to test.
        df: OHLCV DataFrame (with VN30 filters already applied).

    Returns:
        Dict with keys: score, sharpe_ratio, total_return, max_drawdown,
        win_rate, annualized_return, num_trades.
    """
    engine = MDMV2Engine(config)
    results = engine.run(df)
    trades = engine.get_trades()

    # Handle edge case: no trades produced
    cash_exits = [t for t in trades if t.get('type') == 'CASH_EXIT']
    if not cash_exits:
        return {
            'score': 0.0,
            'sharpe_ratio': 0.0,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'annualized_return': 0.0,
            'num_trades': 0,
        }

    analyzer = V2PerformanceAnalyzer(results, trades)

    return {
        'score': analyzer.sharpe_ratio(),
        'sharpe_ratio': analyzer.sharpe_ratio(),
        'total_return': analyzer.total_return(),
        'max_drawdown': analyzer.max_drawdown(),
        'win_rate': analyzer.win_rate(),
        'annualized_return': analyzer.annualized_return(),
        'num_trades': len(cash_exits),
    }


def _load_and_filter_vn30() -> pd.DataFrame:
    """Load VN30 data with warm-up and apply microstructure filters.

    Returns:
        Filtered DataFrame starting from WARMUP_START.
    """
    loader = DataLoader('vn30')
    df = loader.load(start_date=WARMUP_START)
    df = apply_vn30_filters(df)
    return df


def _extract_train_test(df: pd.DataFrame):
    """Split data into training (DATA_START to TRAIN_END) and test (TEST_START to end).

    Args:
        df: Full DataFrame (includes warm-up rows before DATA_START).

    Returns:
        Tuple of (train_df, test_df). train_df includes warm-up rows.
        test_df includes warm-up rows before TEST_START for MA50 computation.
    """
    dates = pd.to_datetime(df['date'])

    # Training: include warm-up for indicator computation, cut analysis at TRAIN_END
    train_mask = dates <= pd.Timestamp(TRAIN_END)
    train_df = df[train_mask].copy().reset_index(drop=True)

    # Test: include rows from WARMUP_START to end (engine needs warm-up)
    # The engine uses all rows for indicator computation; results are filtered by date
    test_df = df.copy().reset_index(drop=True)

    return train_df, test_df


def _build_config_from_row(row: pd.Series) -> MDMV2Config:
    """Build MDMV2Config from a sweep results row."""
    param_names = list(VN30_PARAM_GRID.keys())
    params = {k: row[k] for k in param_names if k in row.index}
    return MDMV2Config(**params, name='vn30_best')


def _validate_train_test(best_config: MDMV2Config, train_df: pd.DataFrame,
                         test_df: pd.DataFrame) -> dict:
    """Run best config on both train and test sets, compare Sharpe.

    Per Pitfall 3: flag if train Sharpe > 2.0 and test Sharpe < 0.5.

    Args:
        best_config: Best config from sweep.
        train_df: Training DataFrame.
        test_df: Full DataFrame (test results filtered by date).

    Returns:
        Dict with train/test metrics and overfitting flag.
    """
    train_metrics = sharpe_scoring_fn(best_config, train_df)

    # For test: run on full data, but only evaluate post-2020 equity
    engine = MDMV2Engine(best_config)
    results = engine.run(test_df)
    trades = engine.get_trades()

    # Filter results to test period only for performance computation
    test_results = results[pd.to_datetime(results['date']) >= pd.Timestamp(TEST_START)].copy()
    test_results = test_results.reset_index(drop=True)

    if len(test_results) > 0:
        test_trades = [t for t in trades
                       if pd.Timestamp(t.get('date', '2000-01-01')) >= pd.Timestamp(TEST_START)]
        test_analyzer = V2PerformanceAnalyzer(test_results, test_trades)
        test_sharpe = test_analyzer.sharpe_ratio()
        test_return = test_analyzer.total_return()
        test_drawdown = test_analyzer.max_drawdown()
    else:
        test_sharpe = 0.0
        test_return = 0.0
        test_drawdown = 0.0

    # Overfitting check (Pitfall 3)
    overfitting_flag = train_metrics['sharpe_ratio'] > 2.0 and test_sharpe < 0.5

    return {
        'train_sharpe': train_metrics['sharpe_ratio'],
        'train_return': train_metrics['total_return'],
        'train_drawdown': train_metrics['max_drawdown'],
        'test_sharpe': test_sharpe,
        'test_return': test_return,
        'test_drawdown': test_drawdown,
        'overfitting_flag': overfitting_flag,
    }


def _save_best_config(config: MDMV2Config, validation: dict, output_path: str):
    """Save best config parameters and validation metrics to text file.

    Args:
        config: Best MDMV2Config.
        validation: Dict from _validate_train_test.
        output_path: Path for output text file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    lines = []
    lines.append("=== VN30 Best Configuration ===")
    lines.append("")
    lines.append("Parameters:")
    for key in VN30_PARAM_GRID.keys():
        lines.append(f"  {key}: {getattr(config, key)}")
    lines.append("")
    lines.append("Train/Test Validation:")
    lines.append(f"  Train Sharpe: {validation['train_sharpe']:.4f}")
    lines.append(f"  Train Return: {validation['train_return']:.2%}")
    lines.append(f"  Train MaxDD:  {validation['train_drawdown']:.2%}")
    lines.append(f"  Test Sharpe:  {validation['test_sharpe']:.4f}")
    lines.append(f"  Test Return:  {validation['test_return']:.2%}")
    lines.append(f"  Test MaxDD:   {validation['test_drawdown']:.2%}")
    if validation['overfitting_flag']:
        lines.append("")
        lines.append("  WARNING: Potential overfitting detected!")
        lines.append("  Train Sharpe > 2.0 with Test Sharpe < 0.5")
    lines.append("")

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"Best config saved to: {os.path.abspath(output_path)}")


def main():
    """Run VN30 Sharpe-optimized parameter sweep."""
    parser = argparse.ArgumentParser(description='VN30 Sharpe-Optimized Parameter Sweep')
    parser.add_argument('--top-n', type=int, default=20, help='Number of top results to return')
    args = parser.parse_args()

    print("Loading VN30 data...")
    df = _load_and_filter_vn30()
    print(f"  Loaded {len(df)} rows ({df['date'].iloc[0]} to {df['date'].iloc[-1]})")

    train_df, test_df = _extract_train_test(df)
    print(f"  Training set: {len(train_df)} rows (up to {TRAIN_END})")
    print(f"  Test set: {len(test_df)} rows (full data for validation)")

    print(f"\nRunning parameter sweep (optimizing Sharpe ratio)...")
    results = run_sweep(
        df=train_df,
        param_grid=VN30_PARAM_GRID,
        top_n=args.top_n,
        scoring_fn=sharpe_scoring_fn,
    )

    # Save results
    csv_path = save_sweep_results(results, 'output/vn30_sweep_results.csv')
    print(f"\nResults saved to: {csv_path}")

    # Print summary
    print_sweep_summary(results, top_n=min(10, args.top_n))

    # Validate best config
    best_row = results.iloc[0]
    best_config = _build_config_from_row(best_row)
    print(f"\nValidating best config on train/test split...")
    validation = _validate_train_test(best_config, train_df, test_df)

    print(f"\n  Train Sharpe: {validation['train_sharpe']:.4f} | "
          f"Test Sharpe: {validation['test_sharpe']:.4f}")
    print(f"  Train Return: {validation['train_return']:.2%} | "
          f"Test Return: {validation['test_return']:.2%}")

    if validation['overfitting_flag']:
        print("\n  WARNING: Potential overfitting detected!")
        print("  Train Sharpe > 2.0 with Test Sharpe < 0.5")

    # Save best config
    _save_best_config(best_config, validation, 'output/vn30_best_config.txt')


if __name__ == '__main__':
    main()
