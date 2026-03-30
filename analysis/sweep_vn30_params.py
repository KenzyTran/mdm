"""Parameter sweep for VN30-optimized MDM config.

Sweeps key parameters that affect BUY time % and exit sensitivity,
targeting total return >= buy & hold (~204%).

Usage:
    uv run python analysis/sweep_vn30_params.py
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
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config


def compute_metrics(results):
    closes = results['close'].values
    states = results['state'].values
    n = len(closes)

    # Long + Short equity
    eq = np.ones(n)
    for i in range(1, n):
        if states[i - 1] == 'BUY':
            eq[i] = eq[i - 1] * (closes[i] / closes[i - 1])
        elif states[i - 1] == 'SELL':
            eq[i] = eq[i - 1] * (closes[i - 1] / closes[i])
        else:
            eq[i] = eq[i - 1]

    total_ret = (eq[-1] - 1) * 100
    peak = np.maximum.accumulate(eq)
    max_dd = ((eq - peak) / peak).min() * 100
    transitions = sum(1 for i in range(1, n) if states[i] != states[i - 1])
    buy_pct = sum(1 for s in states if s == 'BUY') / n * 100

    years = (results['date'].iloc[-1] - results['date'].iloc[0]).days / 365.25
    cagr = (eq[-1] ** (1 / years) - 1) * 100

    return {
        'total_return': round(total_ret, 1),
        'cagr': round(cagr, 1),
        'max_dd': round(max_dd, 1),
        'transitions': transitions,
        'buy_pct': round(buy_pct, 1),
    }


def main():
    print("Loading VN30 data...")
    loader = DataLoader('vn30')
    df = loader.load(start_date='2015-01-01', end_date='2026-03-27')
    df = build_indicator_dataframe(df)

    bh_ret = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    print(f"Buy & Hold: +{bh_ret:.0f}%")
    print()

    # Parameters to sweep (focus on exit sensitivity + SELL behavior)
    param_grid = {
        'dd_cash_threshold': [5, 6, 7, 8],
        'ma10_cash_consecutive': [2, 3, 4, 5],
        'cash_deterioration_days': [10, 15, 20, 30, 999],  # 999 = effectively disable SELL
        'correction_threshold': [-0.06, -0.08, -0.10],
        'stop_loss_pct': [0.015, 0.02, 0.025, 0.03],
    }

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combos = list(itertools.product(*values))
    print(f"Sweeping {len(combos)} combinations...")
    print()

    results_list = []

    for i, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        config = MDMV2Config(**params, name=f"sweep-{i}")

        engine = HybridEngine(HybridConfig(
            v2_config=config,
            two_phase_enabled=True,
            filter_enabled=False,
        ))
        res = engine.run(df.copy())
        metrics = compute_metrics(res)
        metrics.update(params)
        results_list.append(metrics)

        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(combos)} done...")

    # Sort by total return
    results_df = pd.DataFrame(results_list)
    results_df = results_df.sort_values('total_return', ascending=False)

    # Top 20
    print("\n" + "=" * 90)
    print("TOP 20 CONFIGS (by total return)")
    print("=" * 90)
    print(f"{'Return':>8} {'CAGR':>6} {'MaxDD':>7} {'Trans':>6} {'BUY%':>6} | "
          f"{'DD_th':>5} {'MA10d':>5} {'Cash_d':>6} {'Corr':>6} {'SL%':>5}")
    print("-" * 90)

    for _, row in results_df.head(20).iterrows():
        print(f"{row['total_return']:>+7.0f}% {row['cagr']:>5.1f}% {row['max_dd']:>6.1f}% "
              f"{row['transitions']:>5.0f} {row['buy_pct']:>5.1f}% | "
              f"{row['dd_cash_threshold']:>5.0f} {row['ma10_cash_consecutive']:>5.0f} "
              f"{row['cash_deterioration_days']:>6.0f} {row['correction_threshold']:>6.2f} "
              f"{row['stop_loss_pct']:>5.3f}")

    # Beat buy & hold?
    beats_bh = results_df[results_df['total_return'] >= bh_ret]
    print(f"\n{len(beats_bh)} configs beat Buy & Hold (+{bh_ret:.0f}%)")

    if len(beats_bh) > 0:
        print("\nBest config beating B&H:")
        best = beats_bh.iloc[0]
        print(f"  Return: +{best['total_return']:.0f}%  CAGR: {best['cagr']:.1f}%  MaxDD: {best['max_dd']:.1f}%")
        print(f"  dd_cash_threshold={int(best['dd_cash_threshold'])}")
        print(f"  ma10_cash_consecutive={int(best['ma10_cash_consecutive'])}")
        print(f"  cash_deterioration_days={int(best['cash_deterioration_days'])}")
        print(f"  correction_threshold={best['correction_threshold']}")
        print(f"  stop_loss_pct={best['stop_loss_pct']}")

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'vn30_sweep_results.csv')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    results_df.to_csv(out_path, index=False)
    print(f"\nFull results saved to: {out_path}")


if __name__ == '__main__':
    main()
