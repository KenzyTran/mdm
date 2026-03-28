"""
Parameter Sweep for MDM v2

Grid search over MDMV2Config parameter space, scored by signal match rate
against published 2019-2022 signals. Results ranked by overall match rate (D-13).
"""
import itertools
import time
import os
import pandas as pd
from typing import Dict, List, Any

from strategies.mdm_v2.config import MDMV2Config
from .hypothesis_runner import run_hypothesis


def run_sweep(
    df: pd.DataFrame,
    published_signals: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    top_n: int = 10
) -> pd.DataFrame:
    """Grid search over parameter space, scored by signal match rate.

    Args:
        df: NASDAQ OHLCV DataFrame (include warm-up from 2017+)
        published_signals: Published signals for 2019-2022 training period
        param_grid: Dict mapping MDMV2Config field names to lists of values
            Example: {'dd_cash_threshold': [3, 4, 5], 'stop_loss_pct': [0.02, 0.025, 0.03]}
        top_n: Return only top N results

    Returns:
        DataFrame with columns: hypothesis, match_rate, buy_rate, sell_rate, cash_rate,
        plus one column per parameter. Sorted by match_rate descending.
    """
    keys = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))
    total = len(combos)

    print(f"Parameter sweep: {total} combinations across {len(keys)} parameters")
    start_time = time.time()

    results = []
    for i, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        name = f"sweep_{i:04d}"
        config = MDMV2Config(**params, name=name)

        result = run_hypothesis(name, config, df, published_signals)
        result.update(params)  # Add parameter values to result
        results.append(result)

        # Progress every 100 combos
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (total - i - 1) / rate
            print(f"  {i+1}/{total} ({rate:.1f}/s, ~{remaining:.0f}s remaining)")

    elapsed = time.time() - start_time
    print(f"Sweep complete: {total} combinations in {elapsed:.1f}s")

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('match_rate', ascending=False).reset_index(drop=True)

    return results_df.head(top_n) if top_n else results_df


def save_sweep_results(results_df: pd.DataFrame, output_path: str) -> str:
    """Save sweep results to CSV.

    Args:
        results_df: Results DataFrame from run_sweep
        output_path: Path for output CSV (e.g., 'output/sweep_results.csv')

    Returns:
        Absolute path of saved file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Columns order: name first, then scores, then parameters (per D-09)
    score_cols = ['hypothesis', 'match_rate', 'buy_rate', 'sell_rate', 'cash_rate',
                  'total_published', 'total_matched']
    param_cols = [c for c in results_df.columns if c not in score_cols]
    ordered_cols = [c for c in score_cols if c in results_df.columns] + param_cols
    results_df[ordered_cols].to_csv(output_path, index=False)
    return os.path.abspath(output_path)


def print_sweep_summary(results_df: pd.DataFrame, top_n: int = 10) -> str:
    """Print text summary of top-N sweep results (per D-09).

    Args:
        results_df: Results DataFrame from run_sweep (already sorted)
        top_n: Number of top configs to display

    Returns:
        Summary text string
    """
    top = results_df.head(top_n)
    lines = []
    lines.append(f"=== Parameter Sweep Results (Top {min(top_n, len(top))}) ===")
    lines.append("")

    score_cols = {'hypothesis', 'match_rate', 'buy_rate', 'sell_rate', 'cash_rate',
                  'total_published', 'total_matched', 'name'}
    param_cols = [c for c in results_df.columns if c not in score_cols]

    for idx, row in top.iterrows():
        rank = idx + 1
        lines.append(f"#{rank}: {row.get('hypothesis', row.get('name', 'unknown'))} "
                     f"| match_rate: {row['match_rate']:.1f}%")
        lines.append(f"     Buy: {row['buy_rate']:.1f}% | "
                     f"Sell: {row['sell_rate']:.1f}% | "
                     f"Cash: {row['cash_rate']:.1f}%")
        params_str = ", ".join(f"{c}={row[c]}" for c in param_cols if c in row.index)
        lines.append(f"     Params: {params_str}")
        lines.append("")

    summary = "\n".join(lines)
    print(summary)
    return summary


# Default parameter grid (recommended starting grid per research)
DEFAULT_PARAM_GRID = {
    'correction_threshold': [-0.08, -0.10, -0.12],
    'ftd_min_rally_day': [3, 4, 5],
    'ftd_min_price_gain': [0.008, 0.01, 0.015],
    'dd_cash_threshold': [3, 4, 5],
    'stop_loss_pct': [0.02, 0.025, 0.03],
    'dd_window_size': [15, 20, 25],
}
