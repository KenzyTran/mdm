"""Refined Distribution Day grid search sweep for v9.0 (Phase 40, SWEEP-02 + SWEEP-04).

Stage 2 of the sequential two-stage v9.0 sweep. Runs 54 HybridEngine backtests
on VN30 train window (2015-01-01..2021-12-31) -- one per cell of the 6 x 3 x 3
(large_drop, small_drop, small_vol_percentile) grid -- with BOTH
`atr_buffer_enabled=True` (locked from stage-1 winner) and
`refined_dd_enabled=True` (swept) so refined-DD impact is measured on top of
the stage-1 ATR config.

Writes `output/v9_dd_sweep.csv` with the extended metrics schema (config +
locked ATR metadata + core metrics + whipsaw diagnostics + error column)
defined in Phase 40 D-18.

Stage-1 handoff (D-13): reads the locked (k, N, m) ATR params from
`output/v9_atr_best.json` at startup. Raises FileNotFoundError with
"Run `uv run python analysis/select_v9_best.py --stage atr` first" if
the JSON is missing -- this enforces ordered execution of the Phase 40
pipeline (sweep_v9_atr.py -> select_v9_best.py --stage atr -> this script).

OOS guard: train window is hard-coded; a runtime assertion fails loud if the
DataLoader ever returns a row past TRAIN_END (Phase 40 D-12, SWEEP-04).

Fail-loud: every config exception is captured in-row; if any of the top-5 rows
by `sharpe_rf3` has NaN metrics the script raises SummaryError so broken
configs cannot silently become selection winners (Phase 40 D-10).

Run: `uv run python analysis/sweep_v9_dd.py` (requires `output/v9_atr_best.json`
from `select_v9_best.py --stage atr` first).
"""

import sys
import os
import json
import itertools
import traceback
from dataclasses import replace

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET


# OOS-guard constants (D-12): no CLI override allowed. The train window is
# hard-coded so that nobody accidentally leaks 2022+ data into a sweep meant
# to feed selection.
TRAIN_START = '2015-01-01'
TRAIN_END = '2021-12-31'
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), '..', 'output', 'v9_dd_sweep.csv')
ATR_BEST_JSON = os.path.join(os.path.dirname(__file__), '..', 'output', 'v9_atr_best.json')


class SummaryError(RuntimeError):
    """Raised when any of the top-5 rows by sharpe_rf3 has NaN metrics."""


def load_locked_atr() -> dict:
    """Read stage-1 winner from v9_atr_best.json. Enforces ordered execution (D-13).

    Returns:
        Dict with keys `atr_buffer_k` (float), `atr_buffer_period` (int),
        `atr_buffer_consecutive_days` (int). These are the locked values
        every cell of the DD sweep will pin.

    Raises:
        FileNotFoundError: if the JSON artifact is missing -- tells the user
            exactly which command to run next.
        KeyError: if the JSON is present but missing required param fields.
    """
    if not os.path.exists(ATR_BEST_JSON):
        raise FileNotFoundError(
            f"{ATR_BEST_JSON} not found. "
            "Run `uv run python analysis/select_v9_best.py --stage atr` first "
            "(which requires `analysis/sweep_v9_atr.py` to have produced output/v9_atr_sweep.csv)."
        )
    with open(ATR_BEST_JSON) as fh:
        payload = json.load(fh)
    params = payload['params']
    required = ['atr_buffer_k', 'atr_buffer_period', 'atr_buffer_consecutive_days']
    missing = [k for k in required if k not in params]
    if missing:
        raise KeyError(f"v9_atr_best.json missing required params: {missing}")
    return {
        'atr_buffer_k': float(params['atr_buffer_k']),
        'atr_buffer_period': int(params['atr_buffer_period']),
        'atr_buffer_consecutive_days': int(params['atr_buffer_consecutive_days']),
    }


def compute_metrics(results: pd.DataFrame) -> dict:
    """Compute core + whipsaw metrics for a single backtest result DataFrame.

    Sibling copy of `sweep_v9_atr.compute_metrics` (D-02: each stage script is
    self-contained so a stage-2 re-run does not re-execute stage 1). Follows
    the state[i-1] discipline from `analysis/sweep_vn30_params.py`
    (feedback_equity_formula.md) to avoid look-ahead bias. Extends the
    Phase 32 schema with whipsaw diagnostics (sell_count,
    ma50_breakdown_sell_share, buy_count, *_pct) required by Phase 40 D-18.

    Args:
        results: DataFrame from HybridEngine.run() with columns
            `date`, `close`, `state`, `action`.

    Returns:
        Dict with keys: sharpe_rf3, cagr_pct, max_dd_pct, transitions,
        sell_count, ma50_breakdown_sell_share, buy_count, buy_pct,
        cash_pct, sell_pct. Values are float/int.
    """
    closes = results['close'].values
    states = results['state'].values
    actions = results['action']
    n = len(closes)

    # Long + Short equity using state[i-1] (no look-ahead, feedback_equity_formula.md)
    eq = np.ones(n)
    for i in range(1, n):
        if states[i - 1] == 'BUY':
            eq[i] = eq[i - 1] * (closes[i] / closes[i - 1])
        elif states[i - 1] == 'SELL':
            eq[i] = eq[i - 1] * (closes[i - 1] / closes[i])
        else:
            eq[i] = eq[i - 1]

    # CAGR
    years = (results['date'].iloc[-1] - results['date'].iloc[0]).days / 365.25
    cagr = (eq[-1] ** (1 / years) - 1) * 100

    # MaxDD (signed, negative)
    peak = np.maximum.accumulate(eq)
    max_dd = ((eq - peak) / peak).min() * 100

    # Transitions
    transitions = sum(1 for i in range(1, n) if states[i] != states[i - 1])

    # Sharpe_rf3 per D-19: (ann_return - 0.03) / ann_vol, rf = 3%
    daily_returns = pd.Series(eq).pct_change().dropna()
    ann_vol = daily_returns.std() * np.sqrt(252)
    total_return_pct = (eq[-1] - 1) * 100
    ann_return = (1 + total_return_pct / 100) ** (1 / years) - 1
    if ann_vol == 0 or np.isnan(ann_vol):
        sharpe_rf3 = float('nan')
    else:
        sharpe_rf3 = (ann_return - 0.03) / ann_vol

    # Whipsaw diagnostics (D-18, D-20)
    sell_count = int((actions.str.startswith('SELL signal:')).sum())
    # MA50-breakdown path: classic label when atr_buffer disabled, buffered label when enabled
    ma50_mask = (
        actions.str.startswith('SELL signal: MA50 breakdown') |
        actions.str.startswith('SELL signal: ATR buffer zone')
    )
    if sell_count > 0:
        ma50_breakdown_sell_share = ma50_mask.sum() / sell_count
    else:
        ma50_breakdown_sell_share = float('nan')

    buy_count = int((actions.str.startswith('BUY at')).sum())
    buy_pct = (states == 'BUY').mean() * 100
    cash_pct = (states == 'CASH').mean() * 100
    sell_pct = (states == 'SELL').mean() * 100

    return {
        'sharpe_rf3': sharpe_rf3,
        'cagr_pct': round(cagr, 2),
        'max_dd_pct': round(max_dd, 2),
        'transitions': int(transitions),
        'sell_count': sell_count,
        'ma50_breakdown_sell_share': ma50_breakdown_sell_share,
        'buy_count': buy_count,
        'buy_pct': round(buy_pct, 2),
        'cash_pct': round(cash_pct, 2),
        'sell_pct': round(sell_pct, 2),
    }


def main():
    print("Loading stage-1 ATR winner...")
    locked = load_locked_atr()
    print(f"  Locked ATR: k={locked['atr_buffer_k']}, period={locked['atr_buffer_period']}, "
          f"consecutive_days={locked['atr_buffer_consecutive_days']}")

    print("Loading VN30 data (train window 2015-01-01..2021-12-31)...")
    df = DataLoader('vn30').load(start_date=TRAIN_START, end_date=TRAIN_END)

    # OOS-guard assertion (D-12, SWEEP-04): fail loud if any row leaks past TRAIN_END
    assert df['date'].max() <= pd.Timestamp(TRAIN_END), \
        f"OOS leak: max date {df['date'].max()} exceeds TRAIN_END {TRAIN_END}"

    df = build_indicator_dataframe(df)

    # Build the grid (exact values from D-08: 6 x 3 x 3 = 54)
    large_drop_values = [-0.005, -0.006, -0.007, -0.008, -0.009, -0.010]
    small_drop_values = [-0.003, -0.004, -0.005]
    percentile_values = [3, 5, 10]
    combos = list(itertools.product(large_drop_values, small_drop_values, percentile_values))
    assert len(combos) == 54, f"Expected 54 combos, got {len(combos)}"

    results_list = []

    for large_drop, small_drop, pct in tqdm(combos, desc="DD sweep"):
        # D-04 immutable config mutation: dataclasses.replace produces a new instance
        # D-06: pin locked ATR from stage 1, sweep refined_dd params
        # D-08: large_vol_rule='vol_ma20' and small_vol_lookback=50 are FIXED (out of grid)
        cfg = replace(
            VN30_PRESET,
            # Locked ATR from stage 1 (D-06)
            atr_buffer_enabled=True,
            atr_buffer_k=locked['atr_buffer_k'],
            atr_buffer_period=locked['atr_buffer_period'],
            atr_buffer_consecutive_days=locked['atr_buffer_consecutive_days'],
            # Swept DD params (D-06, D-08)
            refined_dd_enabled=True,
            refined_dd_large_drop=large_drop,
            refined_dd_small_drop=small_drop,
            refined_dd_large_vol_rule='vol_ma20',   # fixed per D-08
            refined_dd_small_vol_percentile=pct,
            refined_dd_small_vol_lookback=50,       # fixed per D-08
            name=f"dd-L{large_drop}-S{small_drop}-P{pct}",
        )

        row = {
            'refined_dd_large_drop': large_drop,
            'refined_dd_small_drop': small_drop,
            'refined_dd_small_vol_percentile': pct,
            # Locked ATR metadata (D-18 -- included as columns so downstream reports have full config context)
            'atr_buffer_k': locked['atr_buffer_k'],
            'atr_buffer_period': locked['atr_buffer_period'],
            'atr_buffer_consecutive_days': locked['atr_buffer_consecutive_days'],
            'config_name': cfg.name,
            'error': '',
        }

        # D-10 fail-loud-per-config: trap exceptions, record NaN metrics + traceback
        try:
            engine = HybridEngine(HybridConfig(
                v2_config=cfg,
                two_phase_enabled=True,
                filter_enabled=False,
            ))
            res = engine.run(df.copy())
            metrics = compute_metrics(res)
            row.update(metrics)
        except Exception as exc:
            row['error'] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            for col in ['sharpe_rf3', 'cagr_pct', 'max_dd_pct', 'transitions',
                        'sell_count', 'ma50_breakdown_sell_share', 'buy_count',
                        'buy_pct', 'cash_pct', 'sell_pct']:
                row[col] = float('nan')
        results_list.append(row)

    df_out = pd.DataFrame(results_list)

    # Canonical column order (D-18): DD params -> locked ATR metadata -> core metrics -> whipsaw -> error
    col_order = [
        'refined_dd_large_drop', 'refined_dd_small_drop', 'refined_dd_small_vol_percentile',
        'atr_buffer_k', 'atr_buffer_period', 'atr_buffer_consecutive_days',
        'config_name',
        'sharpe_rf3', 'cagr_pct', 'max_dd_pct', 'transitions',
        'sell_count', 'ma50_breakdown_sell_share', 'buy_count',
        'buy_pct', 'cash_pct', 'sell_pct', 'error',
    ]
    df_out = df_out[col_order]

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df_out.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {len(df_out)} rows to {OUTPUT_CSV}")

    # D-10 top-5 NaN guard: broken configs cannot silently become selection winners
    top5 = df_out.sort_values('sharpe_rf3', ascending=False, na_position='last').head(5)
    if top5['sharpe_rf3'].isna().any():
        raise SummaryError(
            f"NaN sharpe_rf3 in top-5 rows -- broken configs would win selection:\n{top5}"
        )

    print("\nTop 5 by sharpe_rf3:")
    print(top5[['config_name', 'sharpe_rf3', 'cagr_pct', 'max_dd_pct']].to_string(index=False))


if __name__ == '__main__':
    main()
