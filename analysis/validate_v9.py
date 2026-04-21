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


# ── compute_metrics + build_scenario_configs + main(): added in Task 2 ──

if __name__ == '__main__':
    raise NotImplementedError('main() is implemented in Task 2 of Plan 41-01')
