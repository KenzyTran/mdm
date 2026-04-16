"""ATR Buffer Zone grid search sweep for v9.0 (Phase 40, SWEEP-01 + SWEEP-04).

Stage 1 of the sequential two-stage v9.0 sweep. Runs 36 HybridEngine backtests
on VN30 train window (2015-01-01..2021-12-31) -- one per cell of the 4 x 3 x 3
(k, N, m) grid -- with `atr_buffer_enabled=True` and `refined_dd_enabled=False`
so only ATR-buffer impact is measured.

Writes `output/v9_atr_sweep.csv` with the extended metrics schema (config +
core metrics + whipsaw diagnostics + error column) defined in Phase 40 D-18.

OOS guard: train window is hard-coded; a runtime assertion fails loud if the
DataLoader ever returns a row past TRAIN_END (Phase 40 D-12, SWEEP-04).

Fail-loud: every config exception is captured in-row; if any of the top-5 rows
by `sharpe_rf3` has NaN metrics the script raises SummaryError so broken
configs cannot silently become selection winners (Phase 40 D-10).

Run: `uv run python analysis/sweep_v9_atr.py`
"""

import sys
import os
import itertools
import traceback
from dataclasses import replace
from datetime import datetime

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
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), '..', 'output', 'v9_atr_sweep.csv')


class SummaryError(RuntimeError):
    """Raised when any of the top-5 rows by sharpe_rf3 has NaN metrics."""


def compute_metrics(results: pd.DataFrame) -> dict:
    """Compute core + whipsaw metrics for a single backtest result DataFrame.

    Follows the state[i-1] discipline from `analysis/sweep_vn30_params.py`
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
    print("Loading VN30 data (train window 2015-01-01..2021-12-31)...")
    df = DataLoader('vn30').load(start_date=TRAIN_START, end_date=TRAIN_END)

    # OOS-guard assertion (D-12, SWEEP-04): fail loud if any row leaks past TRAIN_END
    assert df['date'].max() <= pd.Timestamp(TRAIN_END), \
        f"OOS leak: max date {df['date'].max()} exceeds TRAIN_END {TRAIN_END}"

    df = build_indicator_dataframe(df)

    # Build the grid (exact values from D-07: 4 x 3 x 3 = 36)
    k_values = [0.3, 0.5, 0.7, 1.0]
    period_values = [10, 14, 20]
    consecutive_days_values = [1, 2, 3]
    combos = list(itertools.product(k_values, period_values, consecutive_days_values))
    assert len(combos) == 36, f"Expected 36 combos, got {len(combos)}"

    results_list = []

    for k, N, m in tqdm(combos, desc="ATR sweep"):
        # D-04 immutable config mutation: dataclasses.replace produces a new instance
        # D-05: flip ATR on, keep refined_dd off so only ATR impact is measured
        cfg = replace(
            VN30_PRESET,
            atr_buffer_enabled=True,
            atr_buffer_k=k,
            atr_buffer_period=N,
            atr_buffer_consecutive_days=m,
            refined_dd_enabled=False,
            name=f"atr-k{k}-N{N}-m{m}",
        )

        row = {
            'atr_buffer_k': k,
            'atr_buffer_period': N,
            'atr_buffer_consecutive_days': m,
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

    # Canonical column order (D-18): config, core metrics, whipsaw, error
    col_order = [
        'atr_buffer_k', 'atr_buffer_period', 'atr_buffer_consecutive_days', 'config_name',
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
