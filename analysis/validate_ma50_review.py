"""
MA50/200dma Review A/B Validation (MAREVIEW-01, MAREVIEW-02, MAREVIEW-03)

5-scenario comparison on VN30: baseline vs partial MA50 removal vs full
removal vs 200dma replacement. Produces quantitative recommendation.

Usage:
    uv run python analysis/validate_ma50_review.py
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')

from core.data_loader import DataLoader
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from strategies.mdm_v2.performance import V2PerformanceAnalyzer


# Test periods -- VN30 only per plan
PERIODS = {
    'vn30_full': {'start': '2018-01-01', 'end': '2026-12-31', 'market': 'vn30'},
}
WARMUP_DAYS = 300


def make_baseline_config():
    """Create baseline config with all MA50 uses ON, 200dma OFF.

    Scenario 1: Represents current V2 behavior with all MA50 signals active.

    Returns:
        MDMV2Config with all MA50 enabled.
    """
    return MDMV2Config(
        ma50_sell_enabled=True,
        buy_filter_enabled=True,
        ma50_breakout_enabled=True,
        ma200_enabled=False,
        sell_acceleration_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        gap_filter_enabled=True,
        rally_threshold_enabled=True,
        rally_threshold_pct=-0.06,
        name="1_baseline",
    )


def make_no_sell_config():
    """Create config with MA50 SELL trigger disabled.

    Scenario 2: Removes MA50 breakdown as SELL trigger only.
    Cash->Sell transition still possible via cash_deterioration_days.

    Returns:
        MDMV2Config with ma50_sell_enabled=False.
    """
    return MDMV2Config(
        ma50_sell_enabled=False,
        buy_filter_enabled=True,
        ma50_breakout_enabled=True,
        ma200_enabled=False,
        sell_acceleration_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        gap_filter_enabled=True,
        rally_threshold_enabled=True,
        rally_threshold_pct=-0.06,
        name="2_no_ma50_sell",
    )


def make_no_filter_config():
    """Create config with MA50 BUY filter disabled.

    Scenario 3: Removes MA10 < MA50 rejection for buy entries only.
    MA50 SELL trigger and breakout signal remain active.

    Returns:
        MDMV2Config with buy_filter_enabled=False.
    """
    return MDMV2Config(
        ma50_sell_enabled=True,
        buy_filter_enabled=False,
        ma50_breakout_enabled=True,
        ma200_enabled=False,
        sell_acceleration_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        gap_filter_enabled=True,
        rally_threshold_enabled=True,
        rally_threshold_pct=-0.06,
        name="3_no_buy_filter",
    )


def make_no_ma50_config():
    """Create config with all MA50 uses disabled.

    Scenario 4: Removes all MA50 roles: SELL trigger, BUY filter,
    and MA50 breakout buy signal. 200dma also off.
    SELL falls back to cash_deterioration_days only.

    Returns:
        MDMV2Config with all MA50 flags off.
    """
    return MDMV2Config(
        ma50_sell_enabled=False,
        buy_filter_enabled=False,
        ma50_breakout_enabled=False,
        ma200_enabled=False,
        sell_acceleration_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        gap_filter_enabled=True,
        rally_threshold_enabled=True,
        rally_threshold_pct=-0.06,
        name="4_no_ma50_all",
    )


def make_200dma_config():
    """Create config with all MA50 off and 200dma replacement on.

    Scenario 5: Replaces all MA50 roles with 200dma equivalent.
    ma200_enabled=True activates 200dma SELL trigger and breakout signal.

    Returns:
        MDMV2Config with MA50 off and 200dma enabled.
    """
    return MDMV2Config(
        ma50_sell_enabled=False,
        buy_filter_enabled=False,
        ma50_breakout_enabled=False,
        ma200_enabled=True,
        sell_acceleration_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        gap_filter_enabled=True,
        rally_threshold_enabled=True,
        rally_threshold_pct=-0.06,
        name="5_200dma_replace",
    )


def run_backtest(config, period):
    """Run V2 engine with given config on a market period.

    Loads data via DataLoader, creates MDMV2Engine, runs backtest.

    Args:
        config: MDMV2Config instance.
        period: Dict with 'start', 'end', 'market' keys.

    Returns:
        Tuple of (results_df, engine).
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    loader = DataLoader(period['market'], data_dir=project_root)
    warmup_start_dt = pd.Timestamp(period['start']) - pd.Timedelta(days=int(WARMUP_DAYS * 1.5))
    warmup_start = warmup_start_dt.strftime('%Y-%m-%d')
    df = loader.load(start_date=warmup_start, end_date=period['end'])

    engine = MDMV2Engine(config)
    results = engine.run(df)
    return results, engine


def compute_metrics(engine):
    """Extract performance metrics from engine run.

    Uses V2PerformanceAnalyzer with state[i-1] rule to avoid look-ahead bias.
    Includes Sharpe ratio for risk-adjusted comparison.

    Args:
        engine: MDMV2Engine after run().

    Returns:
        Dict with total_return, max_drawdown, sharpe_ratio, trade_count, win_rate.
    """
    results_df = engine.results if hasattr(engine, 'results') else engine.run_results
    trades = engine.get_trades()
    analyzer = V2PerformanceAnalyzer(results_df, trades)

    exit_trades = [t for t in trades if t.get('type') in ('CASH_EXIT', 'SHORT_COVER', 'FAIL_SAFE_EXIT')]
    wins = sum(1 for t in exit_trades if t.get('pnl', 0) > 0)
    win_rate = (wins / len(exit_trades) * 100) if exit_trades else 0.0

    return {
        'total_return': analyzer.total_return() * 100,   # as percentage
        'max_drawdown': analyzer.max_drawdown() * 100,    # as percentage
        'sharpe_ratio': analyzer.sharpe_ratio(),
        'trade_count': len(exit_trades),
        'win_rate': win_rate,
    }


def print_comparison(results_dict):
    """Print comparison table of all 5 scenarios.

    Args:
        results_dict: Dict mapping scenario name -> {results, engine, metrics}.
    """
    header = f"{'Scenario':<22} {'Return':>10} {'MaxDD':>10} {'Sharpe':>8} {'Trades':>8} {'WinRate':>10}"
    print(header)
    print("-" * len(header))
    for name, data in results_dict.items():
        m = data['metrics']
        print(f"{name:<22} {m['total_return']:>9.1f}% {m['max_drawdown']:>9.1f}% {m['sharpe_ratio']:>7.2f} {m['trade_count']:>8d} {m['win_rate']:>9.1f}%")


def print_recommendation(results_dict):
    """Print MAREVIEW-03 recommendation based on scenario comparison.

    Compares baseline vs no_ma50_all vs 200dma_replace by Sharpe ratio
    (risk-adjusted metric). Also reports deltas vs baseline for context.

    Args:
        results_dict: Dict mapping scenario name -> {results, engine, metrics}.
    """
    print("\n" + "=" * 70)
    print("MAREVIEW-03: MA50 Review Recommendation")
    print("=" * 70)

    baseline = results_dict['1_baseline']['metrics']
    no_sell = results_dict['2_no_ma50_sell']['metrics']
    no_filter = results_dict['3_no_buy_filter']['metrics']
    no_ma50 = results_dict['4_no_ma50_all']['metrics']
    dma200 = results_dict['5_200dma_replace']['metrics']

    print(f"\nBaseline total return: {baseline['total_return']:.1f}%")
    print(f"No MA50 SELL:         {no_sell['total_return']:.1f}% (delta: {no_sell['total_return'] - baseline['total_return']:+.1f}%)")
    print(f"No BUY filter:        {no_filter['total_return']:.1f}% (delta: {no_filter['total_return'] - baseline['total_return']:+.1f}%)")
    print(f"No MA50 (all):        {no_ma50['total_return']:.1f}% (delta: {no_ma50['total_return'] - baseline['total_return']:+.1f}%)")
    print(f"200dma replace:       {dma200['total_return']:.1f}% (delta: {dma200['total_return'] - baseline['total_return']:+.1f}%)")

    # Determine recommendation by Sharpe ratio (risk-adjusted)
    scenarios = {
        'keep': baseline,
        'remove': no_ma50,
        'replace_200dma': dma200,
    }
    best_name = max(scenarios, key=lambda k: scenarios[k]['sharpe_ratio'])
    best = scenarios[best_name]

    print(f"\nBest risk-adjusted (Sharpe): {best_name} (Sharpe={best['sharpe_ratio']:.2f})")

    if best_name == 'keep':
        print("\nRECOMMENDATION: KEEP MA50 in signal logic.")
        print("Evidence: Baseline MA50 configuration produces the best risk-adjusted returns on VN30.")
    elif best_name == 'remove':
        print("\nRECOMMENDATION: REMOVE MA50 from signal logic.")
        print("Evidence: Removing all MA50 uses improves risk-adjusted returns on VN30.")
        print(f"SELL falls back to cash_deterioration_days only (per D-04).")
        print(f"Note: Stop loss Rule 3 and sell acceleration still use MA50 (out of scope).")
    elif best_name == 'replace_200dma':
        print("\nRECOMMENDATION: REPLACE MA50 with 200dma in signal logic.")
        print("Evidence: 200dma replacement produces better risk-adjusted returns on VN30.")

    # Additional context
    print(f"\nMaxDD comparison: baseline={baseline['max_drawdown']:.1f}%, best={best['max_drawdown']:.1f}%")
    print(f"Trade count: baseline={baseline['trade_count']}, best={best['trade_count']}")
    print(f"\nNote: Sell acceleration gate and stop loss Rule 3 still use MA50 regardless of scenario.")
    print(f"This is correct per phase scope -- those are separate concerns.")


if __name__ == '__main__':
    print("=" * 70)
    print("=== MA50/200dma REVIEW A/B VALIDATION (MAREVIEW-01/02/03) ===")
    print("=" * 70)
    print(f"Date: {date.today().isoformat()}")
    print()

    configs = {
        '1_baseline': make_baseline_config(),
        '2_no_ma50_sell': make_no_sell_config(),
        '3_no_buy_filter': make_no_filter_config(),
        '4_no_ma50_all': make_no_ma50_config(),
        '5_200dma_replace': make_200dma_config(),
    }
    period = PERIODS['vn30_full']
    results = {}
    for name, config in configs.items():
        print(f"Running scenario: {name}...")
        result_df, engine = run_backtest(config, period)
        metrics = compute_metrics(engine)
        results[name] = {'results': result_df, 'engine': engine, 'metrics': metrics}

    print("\n" + "=" * 70)
    print("MA50/200dma Review A/B Comparison (VN30)")
    print("=" * 70 + "\n")
    print_comparison(results)
    print_recommendation(results)
