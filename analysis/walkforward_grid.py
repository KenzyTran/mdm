"""Phase 45: Walk-Forward Grid Search for VN30 macro filter thresholds (WF-01 / WF-02 / WF-03).

Staged three-stage grid sweep over the 6 policy fields of the Phase 44 macro filter
(DXY easing/tightening z-thresholds + DXY tightening DD threshold → 27 combos;
 EEM easing/tightening z-thresholds → 9 combos; SBV tightening stop-loss multiplier →
 3 combos; 39 total engine runs). For each combo, the engine is run ONCE on VN30
2015-2024 (D-04 single-run-and-slice), then metrics are computed per-slice on:

  - Train slice: date <= 2018-12-31 (4 calendar years, FIXED per D-05, no expanding).
  - Eval slices: per-year for y in [2019, 2020, 2021, 2022, 2023, 2024] (6 walk-forward
    evaluations per combo).

Acceptance (D-09 — ROADMAP WF-02 + sanity floor):

  combo.accepted = (median_degradation < 0.30) AND (median(eval CAGR across 6 years) > 0.0%)

  where degradation_{y} = (cagr_train - cagr_eval_{y}) / abs(cagr_train) and
  median_degradation is numpy.median(signed per-year degradations).

  Rejected combos are KEPT in output/v10_grid_results.csv with rejection_reason
  populated (ROADMAP SC-2 — no silent drops).

Windows (D-14 — reproducibility absolute, no CLI overrides):

  TRAIN_START = 2015-01-01
  TRAIN_END   = 2018-12-31
  EVAL_YEARS  = [2019, 2020, 2021, 2022, 2023, 2024]   (EVAL_END = 2024-12-31)
  OOS_FENCE   = 2025-01-01 (any data >= this date MUST NOT enter selection)

The OOS holdout 2025-2026 is excluded by data-load window AND by a runtime
assertion inside load_vn30_data (fail-loud with 'OOS leak' message; tested by
tests/test_walkforward_oos_guard.py::test_assert_fires_on_2025_data — Plan 02).

Outputs (consumed by Phase 46 VAL-01 A/B scenarios):

  output/v10_grid_results.csv   — 39 rows × ~50 columns (configs + train + 18 eval-year
                                   + 6 degradations + 3 aggregates + accept + 7 error cols)
  output/v10_grid_best.json     — 3 stages × (1 winner + 3 runners-up), schema_version=1,
                                   each entry has the FULL 10-field macro config tuple
                                   for direct dataclasses.replace(VN30_PRESET, **config) replay.

Run (~10-15 minutes serial, single tqdm bar per stage — D-17):

    uv run python analysis/walkforward_grid.py

Implementation discipline (D-16): compute_metrics is IMPORTED from analysis.validate_v9,
NOT reimplemented. Drift between Phase 41/42/45 metric formulas is a v10.0 integrity risk.
"""

import sys
import os
import json
import itertools
import traceback
import subprocess
from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET
from analysis.validate_v9 import compute_metrics


# ── Module constants (D-14 / D-05 / D-09 — reproducibility absolute) ────
TRAIN_START = '2015-01-01'
TRAIN_END = '2018-12-31'            # D-05 — FIXED train window, no expanding
EVAL_START = '2019-01-01'
EVAL_END = '2024-12-31'              # Inclusive — 2024 is the last walk-forward year
EVAL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
OOS_FENCE = '2025-01-01'             # Any data >= this date MUST NOT enter selection (D-14)
DEGRADATION_THRESHOLD = 0.30         # D-09 (WF-02) — median_degradation < 0.30
MEDIAN_CAGR_FLOOR = 0.0              # D-09 sanity floor — median(eval CAGR) > 0.0

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
RESULTS_CSV = os.path.join(OUTPUT_DIR, 'v10_grid_results.csv')
BEST_JSON = os.path.join(OUTPUT_DIR, 'v10_grid_best.json')
RECONCILED_BASELINE = os.path.join(OUTPUT_DIR, 'v10_reconciled_baseline.json')


class SummaryError(RuntimeError):
    """Raised when any of the top-3 accepted combos in a stage has NaN eval-year metrics (D-18)."""


def load_vn30_data(df_override: "pd.DataFrame | None" = None) -> pd.DataFrame:
    """Load VN30 2015-01-01..2024-12-31, run indicators, assert OOS fence.

    Args:
        df_override: If provided, skip DataLoader + build_indicator_dataframe
            and use this DataFrame directly. Used by the Plan 02 pytest to
            inject synthetic frames with 2025-labeled rows (D-15).

    Returns:
        Post-indicator DataFrame guaranteed to have date.max() < OOS_FENCE.

    Raises:
        AssertionError: With message containing 'OOS leak' if max(date) >=
            OOS_FENCE. Caught by the D-15 regression test.
    """
    if df_override is not None:
        df = df_override
    else:
        df = DataLoader('vn30').load(start_date=TRAIN_START, end_date=EVAL_END)
        df = build_indicator_dataframe(df)
    # D-14 runtime assert — STRICT < (not <=) because OOS_FENCE is the exclusion boundary for 2025
    assert df['date'].max() < pd.Timestamp(OOS_FENCE), (
        f"OOS leak: max date {df['date'].max()} crossed OOS_FENCE {OOS_FENCE}"
    )
    return df


def _load_reconciled_baseline_cagr() -> float:
    """Return cagr_pct from output/v10_reconciled_baseline.json for context print only.

    D-Claude-4: Phase 45 does NOT gate on the reconciled baseline (Phase 46 does).
    This is purely informational for the main() banner. Any read failure returns
    NaN and continues — never blocks the sweep.
    """
    try:
        with open(RECONCILED_BASELINE, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)
        return float(payload['cagr_pct'])
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return float('nan')


def main() -> None:
    raise NotImplementedError("main() orchestrator lands in Task 5")


if __name__ == '__main__':
    main()
