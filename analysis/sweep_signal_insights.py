"""Sweep based on signal sequence analysis insights.

Tests 3 hypotheses derived from Dr. K's 962-signal dataset:
  H1: Increase cash_deterioration_days (reduce false SELL)
  H2: Long-only mode (SELL→flat instead of short)
  H3: Filter threshold (tighter BUY entry to reduce whipsaw)

Compares against current VN30_PRESET baseline.

Usage:
    uv run python analysis/sweep_signal_insights.py
"""

import sys
import os
import itertools

import numpy as np
import pandas as pd
from dataclasses import replace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config, VN30_PRESET
from strategies.mdm_hybrid.indicator_filter import FilterConfig


def compute_metrics(results, long_only=False):
    """Compute equity curve metrics with optional long-only mode."""
    closes = results['close'].values
    states = results['state'].values
    n = len(closes)

    eq = np.ones(n)
    for i in range(1, n):
        if states[i - 1] == 'BUY':
            eq[i] = eq[i - 1] * (closes[i] / closes[i - 1])
        elif states[i - 1] == 'SELL' and not long_only:
            eq[i] = eq[i - 1] * (closes[i - 1] / closes[i])
        else:
            eq[i] = eq[i - 1]

    total_ret = (eq[-1] - 1) * 100
    peak = np.maximum.accumulate(eq)
    max_dd = ((eq - peak) / peak).min() * 100
    transitions = sum(1 for i in range(1, n) if states[i] != states[i - 1])
    buy_pct = sum(1 for s in states if s == 'BUY') / n * 100
    sell_pct = sum(1 for s in states if s == 'SELL') / n * 100

    years = (results['date'].iloc[-1] - results['date'].iloc[0]).days / 365.25
    cagr = (eq[-1] ** (1 / years) - 1) * 100 if eq[-1] > 0 else -100

    return {
        'total_return': round(total_ret, 1),
        'cagr': round(cagr, 1),
        'max_dd': round(max_dd, 1),
        'transitions': transitions,
        'buy_pct': round(buy_pct, 1),
        'sell_pct': round(sell_pct, 1),
    }


def run_config(df, v2_config, filter_enabled=False, filter_config=None, long_only=False):
    """Run a single backtest config and return metrics."""
    hc = HybridConfig(
        v2_config=v2_config,
        two_phase_enabled=True,
        filter_enabled=filter_enabled,
        filter_config=filter_config or FilterConfig(),
    )
    engine = HybridEngine(hc)
    res = engine.run(df.copy())
    metrics = compute_metrics(res, long_only=long_only)
    return metrics


def main():
    print("=" * 80)
    print("Signal Sequence Insight Sweep — VN30")
    print("=" * 80)

    print("\nLoading VN30 data...")
    loader = DataLoader('vn30')
    df = loader.load(start_date='2015-01-01', end_date='2026-03-27')
    df = build_indicator_dataframe(df)

    bh_ret = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    print(f"Buy & Hold: +{bh_ret:.0f}%")

    # --- Baseline: current VN30_PRESET ---
    print("\n" + "-" * 80)
    print("BASELINE: VN30_PRESET (current best)")
    print("-" * 80)
    baseline = run_config(df, VN30_PRESET)
    baseline_lo = run_config(df, VN30_PRESET, long_only=True)
    print(f"  Long+Short: {baseline['total_return']:+.0f}%  CAGR={baseline['cagr']:.1f}%  "
          f"MaxDD={baseline['max_dd']:.1f}%  Trans={baseline['transitions']}  "
          f"BUY%={baseline['buy_pct']}%  SELL%={baseline['sell_pct']}%")
    print(f"  Long-only:  {baseline_lo['total_return']:+.0f}%  CAGR={baseline_lo['cagr']:.1f}%  "
          f"MaxDD={baseline_lo['max_dd']:.1f}%  Trans={baseline_lo['transitions']}  "
          f"BUY%={baseline_lo['buy_pct']}%")

    # --- H1: cash_deterioration_days sweep ---
    print("\n" + "-" * 80)
    print("H1: cash_deterioration_days (reduce false SELL)")
    print("  Post-2019 Dr. K: Cash->Sell only 26%. Auto-SELL may be too aggressive.")
    print("-" * 80)
    print(f"{'cash_det':>10} {'mode':>10} {'Return':>8} {'CAGR':>6} {'MaxDD':>7} "
          f"{'Trans':>6} {'BUY%':>6} {'SELL%':>6} {'vs base':>8}")
    print("-" * 72)

    h1_results = []
    for cd_days in [10, 15, 20, 30, 40, 60, 120, 999]:
        v2 = replace(VN30_PRESET, cash_deterioration_days=cd_days)
        for long_only, mode_name in [(False, 'L+S'), (True, 'L-only')]:
            m = run_config(df, v2, long_only=long_only)
            base_ref = baseline if not long_only else baseline_lo
            delta = m['total_return'] - base_ref['total_return']
            print(f"{cd_days:>10} {mode_name:>10} {m['total_return']:>+7.0f}% {m['cagr']:>5.1f}% "
                  f"{m['max_dd']:>6.1f}% {m['transitions']:>5} {m['buy_pct']:>5.1f}% "
                  f"{m['sell_pct']:>5.1f}% {delta:>+7.1f}%")
            h1_results.append({**m, 'cash_det': cd_days, 'long_only': long_only, 'delta': delta})

    # --- H2: Long-only with best cash_det from H1 ---
    print("\n" + "-" * 80)
    print("H2: Long-only comparison (SELL expectancy near zero)")
    print("-" * 80)

    # Find best cash_det for each mode
    h1_df = pd.DataFrame(h1_results)
    for lo in [False, True]:
        mode = 'Long-only' if lo else 'Long+Short'
        best = h1_df[h1_df['long_only'] == lo].sort_values('total_return', ascending=False).iloc[0]
        print(f"  Best {mode}: cash_det={int(best['cash_det'])} -> {best['total_return']:+.0f}% "
              f"(CAGR={best['cagr']:.1f}%, MaxDD={best['max_dd']:.1f}%)")

    # --- H3: Filter threshold sweep (tighter BUY entry) ---
    print("\n" + "-" * 80)
    print("H3: Indicator filter (reduce whipsaw BUY)")
    print("  Post-2019 BUY <7d = 0% win rate. Tighter filter may help.")
    print("-" * 80)

    # Use best cash_det from H1 long+short
    best_cd = int(h1_df[h1_df['long_only'] == False].sort_values('total_return', ascending=False).iloc[0]['cash_det'])
    print(f"  Using cash_det={best_cd} (best from H1)")
    print()

    print(f"{'filter':>8} {'thresh':>8} {'mode':>10} {'Return':>8} {'CAGR':>6} "
          f"{'MaxDD':>7} {'Trans':>6} {'vs base':>8}")
    print("-" * 72)

    filter_configs = [
        ('off', False, FilterConfig()),
        ('3-dflt', True, FilterConfig(majority_threshold=2/3)),
        ('3-0.5', True, FilterConfig(majority_threshold=0.5)),
        ('3-1.0', True, FilterConfig(majority_threshold=1.0)),
        ('2-dflt', True, FilterConfig(ema55_enabled=True, macd_enabled=True,
                                       ema9_21_enabled=False, majority_threshold=0.5)),
        ('2-1.0', True, FilterConfig(ema55_enabled=True, macd_enabled=True,
                                      ema9_21_enabled=False, majority_threshold=1.0)),
    ]

    for fc_name, f_enabled, fc in filter_configs:
        v2 = replace(VN30_PRESET, cash_deterioration_days=best_cd)
        for long_only, mode_name in [(False, 'L+S'), (True, 'L-only')]:
            m = run_config(df, v2, filter_enabled=f_enabled, filter_config=fc, long_only=long_only)
            delta = m['total_return'] - baseline['total_return']
            print(f"{fc_name:>8} {fc.majority_threshold:>7.2f} {mode_name:>10} "
                  f"{m['total_return']:>+7.0f}% {m['cagr']:>5.1f}% {m['max_dd']:>6.1f}% "
                  f"{m['transitions']:>5} {delta:>+7.1f}%")

    # --- Summary ---
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Baseline VN30_PRESET (L+S):  {baseline['total_return']:+.0f}%")
    print(f"  Baseline VN30_PRESET (L-only): {baseline_lo['total_return']:+.0f}%")
    print(f"  Buy & Hold:                  +{bh_ret:.0f}%")


if __name__ == '__main__':
    main()
