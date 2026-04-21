"""Phase 41: v9.0 A/B + Walk-Forward Validation (VAL-01..VAL-04).

Validates the v9.0 HybridEngine extensions (ATR Buffer Zone + Refined Distribution Day)
against the v6.0 baseline on VN30 2015-2026. Produces:
- output/v9_ab_comparison.txt — human-readable report with 4 scenarios (baseline/+ATR/+DD/+both),
  walk-forward (Train 2015-2021 / Test 2022-2026), whipsaw diagnostic, production candidate.
- output/v9_ab_scenarios.csv — one row per scenario with full metrics + train/test split columns.

Inputs:
- Phase 40 locked params: output/v9_atr_best.json + output/v9_dd_best.json (FileNotFoundError
  with remediation if missing — per D-02).

Scenarios (D-05):
  1. baseline:  atr_buffer_enabled=False, refined_dd_enabled=False (v6.0 shipped VN30_PRESET)
  2. +ATR:      atr_buffer_enabled=True with locked (k, N, m); refined_dd_enabled=False
  3. +DD:       atr_buffer_enabled=False; refined_dd_enabled=True with locked (large/small/percentile)
                — see D-07 methodological note (DD params optimized under ATR=True, so +DD is upper bound)
  4. +both:     ATR + DD both enabled with all locked params (canonical v9.0 full stack)

Walk-forward (D-08, D-09):
- Test metrics: run engine once on full 2015-2026 for indicator warmup, slice date >= 2022-01-01
- Train metrics: separate engine run on df[df['date'] <= '2021-12-31']
- Degradation: (cagr_train - cagr_test) / abs(cagr_train); threshold 50% (VAL-02)

Exit 0 always (D-14): VAL-03 verdict is text-only, not a process exit gate.

Usage:
    uv run python analysis/validate_v9.py
"""

import sys
import os
import io
import json
import traceback
from dataclasses import replace

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET


# ── Module constants ────────────────────────────────────────────────────
DATA_START = '2015-01-01'
DATA_END = '2026-03-31'        # Full period for VAL-01 (matches v6 precedent line 95)
TRAIN_END = '2021-12-31'       # Walk-forward train upper bound (D-09, VAL-02)
TEST_START = '2022-01-01'      # Walk-forward test lower bound (D-08, VAL-02)
DEGRADATION_THRESHOLD = 0.50   # VAL-02: CAGR degradation < 50%
SUCCESS_CAGR = 11.5            # VAL-03: CAGR >= 11.5% (baseline v6.0 CAGR)
SUCCESS_MAXDD = -25.0          # VAL-03: MaxDD < -25% (alternative to Sharpe > baseline)

ATR_BEST_JSON = os.path.join(os.path.dirname(__file__), '..', 'output', 'v9_atr_best.json')
DD_BEST_JSON = os.path.join(os.path.dirname(__file__), '..', 'output', 'v9_dd_best.json')
REPORT_TXT = os.path.join(os.path.dirname(__file__), '..', 'output', 'v9_ab_comparison.txt')
SCENARIOS_CSV = os.path.join(os.path.dirname(__file__), '..', 'output', 'v9_ab_scenarios.csv')

# Scenario iteration order: monotone complexity (D-05). Reused by A/B table,
# walk-forward loop, whipsaw diagnostic, VAL-03 verdict, CSV writer.
SCENARIO_ORDER = ['baseline', '+ATR', '+DD', '+both']


def load_locked_params() -> tuple[dict, dict]:
    """Read Phase 40 locked winners from JSON artifacts.

    Returns:
        (atr_params, dd_params) as two dicts. atr_params has keys
        `atr_buffer_k`, `atr_buffer_period`, `atr_buffer_consecutive_days`.
        dd_params has keys `refined_dd_large_drop`, `refined_dd_small_drop`,
        `refined_dd_small_vol_percentile` (plus atr_* keys we ignore for the
        scenario builder — ATR params come from atr_params).

    Raises:
        FileNotFoundError: if either JSON is missing. Message includes the
            exact Phase 40 remediation command (D-02).
    """
    if not os.path.exists(ATR_BEST_JSON):
        raise FileNotFoundError(
            f"{ATR_BEST_JSON} not found. "
            "Run `uv run python analysis/sweep_v9_atr.py` then "
            "`uv run python analysis/select_v9_best.py --stage atr` (Phase 40)."
        )
    if not os.path.exists(DD_BEST_JSON):
        raise FileNotFoundError(
            f"{DD_BEST_JSON} not found. "
            "Run `uv run python analysis/sweep_v9_dd.py` then "
            "`uv run python analysis/select_v9_best.py --stage dd` (Phase 40)."
        )
    with open(ATR_BEST_JSON, 'r', encoding='utf-8') as f:
        atr_best = json.load(f)
    with open(DD_BEST_JSON, 'r', encoding='utf-8') as f:
        dd_best = json.load(f)
    return atr_best['params'], dd_best['params']


def run_engine(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Run HybridEngine on df with the given MDMV2Config.

    Mirrors `analysis/validate_combined_v6.py::run_engine` (lines 71-79) —
    two_phase_enabled=True, filter_enabled=False. df is defensively copied
    inside engine.run() already but we copy here too so callers can re-run
    scenarios on shared data without side effects.

    Args:
        df: Post-indicator VN30 DataFrame (from build_indicator_dataframe).
        cfg: MDMV2Config instance built via dataclasses.replace(VN30_PRESET, ...).

    Returns:
        Results DataFrame with columns date, close, state, action (and others).
    """
    engine = HybridEngine(HybridConfig(
        v2_config=cfg,
        two_phase_enabled=True,
        filter_enabled=False,
    ))
    return engine.run(df.copy())


def compute_metrics(results: pd.DataFrame) -> dict:
    """Compute equity + whipsaw metrics for a single backtest result DataFrame.

    Follows the state[i-1] discipline (feedback_equity_formula.md) to avoid
    look-ahead bias. Schema matches Phase 40 `analysis/sweep_v9_atr.py::compute_metrics`
    extended with `total_return_pct` for A/B report readability.

    Args:
        results: DataFrame from HybridEngine.run() with columns date, close, state, action.

    Returns:
        Dict with keys: sharpe_rf3, cagr_pct, max_dd_pct, total_return_pct,
        transitions, sell_count, ma50_breakdown_sell_share, buy_count,
        buy_pct, cash_pct, sell_pct.
    """
    closes = results['close'].values
    states = results['state'].values
    actions = results['action']
    n = len(closes)

    # Long + Short equity using state[i-1] (no look-ahead)
    eq = np.ones(n)
    for i in range(1, n):
        if states[i - 1] == 'BUY':
            eq[i] = eq[i - 1] * (closes[i] / closes[i - 1])
        elif states[i - 1] == 'SELL':
            eq[i] = eq[i - 1] * (closes[i - 1] / closes[i])
        else:
            eq[i] = eq[i - 1]

    years = (results['date'].iloc[-1] - results['date'].iloc[0]).days / 365.25
    cagr = (eq[-1] ** (1 / years) - 1) * 100 if years > 0 else 0.0

    peak = np.maximum.accumulate(eq)
    max_dd = ((eq - peak) / peak).min() * 100

    transitions = sum(1 for i in range(1, n) if states[i] != states[i - 1])

    daily_returns = pd.Series(eq).pct_change().dropna()
    ann_vol = daily_returns.std() * np.sqrt(252)
    total_return_pct = (eq[-1] - 1) * 100
    if years > 0:
        ann_return = (1 + total_return_pct / 100) ** (1 / years) - 1
    else:
        ann_return = 0.0
    if ann_vol == 0 or np.isnan(ann_vol):
        sharpe_rf3 = float('nan')
    else:
        sharpe_rf3 = (ann_return - 0.03) / ann_vol

    # Whipsaw diagnostics (D-11; labels verified from sweep_v9_atr.py:106-111)
    sell_count = int((actions.str.startswith('SELL signal:')).sum())
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
        'total_return_pct': round(total_return_pct, 2),
        'transitions': int(transitions),
        'sell_count': sell_count,
        'ma50_breakdown_sell_share': ma50_breakdown_sell_share,
        'buy_count': buy_count,
        'buy_pct': round(buy_pct, 2),
        'cash_pct': round(cash_pct, 2),
        'sell_pct': round(sell_pct, 2),
    }


def build_scenario_configs(atr_params: dict, dd_params: dict) -> dict:
    """Build the 4 scenario MDMV2Config instances per D-05.

    Uses dataclasses.replace(VN30_PRESET, **overrides) to produce immutable
    mutations. The +DD scenario uses the DD params verbatim from v9_dd_best.json
    despite Phase 40 D-07 noting these were optimized conditional on ATR=True
    (the report emits a methodological caveat paragraph in Plan 41-02).

    Args:
        atr_params: Dict from v9_atr_best.json['params'] with keys
            atr_buffer_k (float), atr_buffer_period (int),
            atr_buffer_consecutive_days (int).
        dd_params: Dict from v9_dd_best.json['params'] with keys
            refined_dd_large_drop (float), refined_dd_small_drop (float),
            refined_dd_small_vol_percentile (int). (The dd JSON also echoes
            atr_buffer_* keys for provenance; we ignore those here.)

    Returns:
        Dict with keys 'baseline', '+ATR', '+DD', '+both', each an MDMV2Config.
    """
    atr_k = atr_params['atr_buffer_k']
    atr_N = atr_params['atr_buffer_period']
    atr_m = atr_params['atr_buffer_consecutive_days']
    dd_large = dd_params['refined_dd_large_drop']
    dd_small = dd_params['refined_dd_small_drop']
    dd_pct = dd_params['refined_dd_small_vol_percentile']

    baseline = replace(
        VN30_PRESET,
        atr_buffer_enabled=False,
        refined_dd_enabled=False,
        name='baseline',
    )
    plus_atr = replace(
        VN30_PRESET,
        atr_buffer_enabled=True,
        atr_buffer_k=atr_k,
        atr_buffer_period=atr_N,
        atr_buffer_consecutive_days=atr_m,
        refined_dd_enabled=False,
        name='+ATR',
    )
    plus_dd = replace(
        VN30_PRESET,
        atr_buffer_enabled=False,
        refined_dd_enabled=True,
        refined_dd_large_drop=dd_large,
        refined_dd_small_drop=dd_small,
        refined_dd_small_vol_percentile=dd_pct,
        # refined_dd_large_vol_rule='vol_ma20' and refined_dd_small_vol_lookback=50
        # are VN30_PRESET defaults per D-06 — no override needed.
        name='+DD',
    )
    plus_both = replace(
        VN30_PRESET,
        atr_buffer_enabled=True,
        atr_buffer_k=atr_k,
        atr_buffer_period=atr_N,
        atr_buffer_consecutive_days=atr_m,
        refined_dd_enabled=True,
        refined_dd_large_drop=dd_large,
        refined_dd_small_drop=dd_small,
        refined_dd_small_vol_percentile=dd_pct,
        name='+both',
    )
    return {
        'baseline': baseline,
        '+ATR': plus_atr,
        '+DD': plus_dd,
        '+both': plus_both,
    }


def main():
    """Phase 41 validation entry point. Plan 41-02 fills in the VAL-01..04 sections."""
    lines = []

    def log(msg: str = '') -> None:
        print(msg)
        lines.append(msg)

    log('=' * 70)
    log('PHASE 41: v9.0 A/B + WALK-FORWARD VALIDATION')
    log('=' * 70)

    # Load inputs
    atr_params, dd_params = load_locked_params()
    log(f'\nLocked ATR params: k={atr_params["atr_buffer_k"]}, '
        f'N={atr_params["atr_buffer_period"]}, '
        f'm={atr_params["atr_buffer_consecutive_days"]}')
    log(f'Locked DD params: large_drop={dd_params["refined_dd_large_drop"]}, '
        f'small_drop={dd_params["refined_dd_small_drop"]}, '
        f'small_vol_percentile={dd_params["refined_dd_small_vol_percentile"]}')

    # Load data (full period + train slice)
    loader = DataLoader('vn30')
    df_full = loader.load(start_date=DATA_START, end_date=DATA_END)
    df_full = build_indicator_dataframe(df_full)
    log(f'\nVN30 data: {len(df_full)} rows ({df_full["date"].min().date()} -> '
        f'{df_full["date"].max().date()})')

    # Runtime assert: full-period coverage required (D-08 precondition)
    assert df_full['date'].max() >= pd.Timestamp('2025-12-01'), \
        f"Insufficient data: max date {df_full['date'].max()} — need through 2025+ for VAL-01"

    scenarios = build_scenario_configs(atr_params, dd_params)
    log(f'\nScenarios built: {list(scenarios.keys())}')

    # ── VAL-01: A/B COMPARISON (full period 2015-2026) ──────────────────
    log('\n' + '─' * 70)
    log('VAL-01: A/B COMPARISON — 4 scenarios on full period 2015-2026')
    log('─' * 70)

    # Run engine once per scenario on FULL data; cache results for walk-forward reuse
    full_results: dict[str, pd.DataFrame] = {}
    full_metrics: dict[str, dict] = {}
    for name in SCENARIO_ORDER:
        log(f'  Running {name}...')
        cfg = scenarios[name]
        try:
            res = run_engine(df_full, cfg)
            full_results[name] = res
            full_metrics[name] = compute_metrics(res)
        except Exception as exc:
            # Fail-loud per Phase 40 D-10: capture traceback in report but keep going
            log(f'  ERROR in {name}: {type(exc).__name__}: {exc}')
            log(traceback.format_exc())
            full_results[name] = None
            full_metrics[name] = {k: float('nan') for k in [
                'sharpe_rf3', 'cagr_pct', 'max_dd_pct', 'total_return_pct',
                'transitions', 'sell_count', 'ma50_breakdown_sell_share',
                'buy_count', 'buy_pct', 'cash_pct', 'sell_pct',
            ]}

    # Buy & Hold VN30 reference (D-17)
    bh_total_ret = (df_full['close'].iloc[-1] / df_full['close'].iloc[0] - 1) * 100
    bh_years = (df_full['date'].iloc[-1] - df_full['date'].iloc[0]).days / 365.25
    bh_cagr = ((1 + bh_total_ret / 100) ** (1 / bh_years) - 1) * 100 if bh_years > 0 else 0.0
    # B&H MaxDD on close series
    bh_eq = df_full['close'].values / df_full['close'].iloc[0]
    bh_peak = np.maximum.accumulate(bh_eq)
    bh_maxdd = ((bh_eq - bh_peak) / bh_peak).min() * 100

    # A/B table (D-17: B&H row included)
    log(f'\n{"Scenario":<12s} {"TotRet":>9s} {"CAGR":>8s} {"MaxDD":>8s} {"Sharpe":>8s} '
        f'{"Trans":>6s} {"BUY%":>6s} {"CASH%":>6s} {"SELL%":>6s}')
    log('-' * 80)
    for name in SCENARIO_ORDER:
        m = full_metrics[name]
        log(f'{name:<12s} {m["total_return_pct"]:>+8.1f}% {m["cagr_pct"]:>7.2f}% '
            f'{m["max_dd_pct"]:>7.2f}% {m["sharpe_rf3"]:>8.3f} '
            f'{m["transitions"]:>6d} {m["buy_pct"]:>5.1f}% '
            f'{m["cash_pct"]:>5.1f}% {m["sell_pct"]:>5.1f}%')
    log(f'{"B&H VN30":<12s} {bh_total_ret:>+8.1f}% {bh_cagr:>7.2f}% {bh_maxdd:>7.2f}% '
        f'{"—":>8s} {"—":>6s} {"100.0":>5s}% {"0.0":>5s}% {"0.0":>5s}%')

    # ── VAL-04: WHIPSAW DIAGNOSTIC ──────────────────────────────────────
    log('\n' + '─' * 70)
    log('VAL-04: WHIPSAW DIAGNOSTIC — SELL count + MA50-breakdown share')
    log(f'Baseline v6.0 reference: 124 SELL signals, 84% MA50-breakdown share')
    log('─' * 70)

    baseline_sell = full_metrics['baseline']['sell_count']
    baseline_ma50_share = full_metrics['baseline']['ma50_breakdown_sell_share']

    log(f'\n{"Scenario":<12s} {"SELL#":>6s} {"MA50%":>8s} {"BUY#":>6s} '
        f'{"dSELL":>7s} {"dMA50":>8s}')
    log('-' * 55)
    for name in SCENARIO_ORDER:
        m = full_metrics[name]
        sell_delta = m['sell_count'] - baseline_sell
        ma50_share_pct = (m['ma50_breakdown_sell_share'] * 100
                         if not np.isnan(m['ma50_breakdown_sell_share']) else float('nan'))
        baseline_ma50_share_pct = (baseline_ma50_share * 100
                                   if not np.isnan(baseline_ma50_share) else float('nan'))
        ma50_delta = (ma50_share_pct - baseline_ma50_share_pct
                     if not (np.isnan(ma50_share_pct) or np.isnan(baseline_ma50_share_pct))
                     else float('nan'))
        log(f'{name:<12s} {m["sell_count"]:>6d} {ma50_share_pct:>7.1f}% '
            f'{m["buy_count"]:>6d} {sell_delta:>+7d} {ma50_delta:>+7.1f}%')

    log('\nWhipsaw reduction evidence:')
    for name in ['+ATR', '+DD', '+both']:
        m = full_metrics[name]
        sell_drop = baseline_sell - m['sell_count']
        if baseline_sell > 0:
            sell_drop_pct = sell_drop / baseline_sell * 100
            log(f'  {name}: SELL count {m["sell_count"]} vs baseline {baseline_sell} '
                f'({sell_drop:+d}, {sell_drop_pct:+.1f}%)')

    # Save report (partial until Plan 41-02 completes it)
    os.makedirs(os.path.dirname(REPORT_TXT), exist_ok=True)
    with open(REPORT_TXT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    log(f'\nReport saved: {REPORT_TXT}')

    # D-14: exit 0 always
    sys.exit(0)


if __name__ == '__main__':
    main()
