"""Phase 46: v10.0 A/B + OOS Validation (HARD Gate) — VAL-01..VAL-05.

Forked from analysis/validate_v9.py skeleton per CONTEXT D-12. Imports
compute_metrics from analysis.validate_v9 per D-13 (determinism across
Phase 41/45/46). Produces:
- output/v10_ab_comparison.txt — 5-scenario A/B report on VN30 2015-2026
- output/v10_ab_scenarios.csv — machine-readable per-scenario metrics
- output/v10_validation_report.txt — HARD gate verdict + rejection narrative

Scenarios (D-01 "defaults" + D-02 isolation via threshold extremes):
  1. baseline:       macro_filter_enabled=False (v6.0 reference)
  2. +DXY:           macro_filter_enabled=True, EEM + SBV disabled via extremes
  3. +EEM:           macro_filter_enabled=True, DXY + SBV disabled via extremes
  4. +SBV-regime:    macro_filter_enabled=True, DXY + EEM disabled via extremes
  5. +all:           VN30_PRESET verbatim + macro_filter_enabled=True (D-03)

Exit discipline (D-11): exit 0 on full pass, exit 1 on any gate fail.
Verdict string (D-09): literal "v10 macro filter accepted as production"
on full pass, "v6.0 retained as production" on any fail.

Usage:  uv run python analysis/validate_v10.py
"""

import sys
import os
import io
import json
import subprocess
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
from analysis.validate_v9 import compute_metrics


# ── Module constants ────────────────────────────────────────────────
DATA_START = '2015-01-01'
DATA_END = '2026-03-31'              # Full A/B period (matches v9 precedent + reconciled baseline window)
OOS_START = '2025-01-01'             # OOS HARD gate window (D-14)
OOS_END = '2026-03-31'

# HARD gate thresholds (D-05)
HARD_GATE_MAX_DD_CEILING = -20.0     # OOS MaxDD must be strictly > this (less negative)
# HARD_GATE_CAGR_FLOOR read at runtime from output/v10_reconciled_baseline.json (D-05)

# VAL-03 walk-forward re-check (D-07)
WALKFORWARD_DEGRADATION_THRESHOLD = 0.30
WALKFORWARD_GRID_CSV = os.path.join(
    os.path.dirname(__file__), '..', 'output', 'v10_grid_results.csv'
)
WALKFORWARD_VN30_PRESET_COMBO = 'stage3_all_three-c1'
# D-07 note: stage3_all_three-c1 matches VN30_PRESET defaults exactly
# (dxy_easing=-1.0, dxy_tightening=+1.0, dxy_tightening_dd=3,
#  eem_easing=+1.0, eem_tightening=-1.0, sbv_mult=1.5).
# All three stage3_all_three rows have identical median_degradation
# (0.5374873...) because the macro filter policy saturates before
# the SBV multiplier variation matters.

# Reconciled baseline (D-05)
RECONCILED_BASELINE_JSON = os.path.join(
    os.path.dirname(__file__), '..', 'output', 'v10_reconciled_baseline.json'
)

# VAL-04 parity test (D-08)
PARITY_TEST_PATH = 'tests/test_macro_filter_v6_parity.py'

# Output paths
REPORT_TXT = os.path.join(os.path.dirname(__file__), '..', 'output', 'v10_validation_report.txt')
AB_COMPARISON_TXT = os.path.join(os.path.dirname(__file__), '..', 'output', 'v10_ab_comparison.txt')
SCENARIOS_CSV = os.path.join(os.path.dirname(__file__), '..', 'output', 'v10_ab_scenarios.csv')

# Verdict strings (D-09 — exact, case-sensitive, locked by ROADMAP SC-5)
VERDICT_PASS = "v10 macro filter accepted as production"
VERDICT_FAIL = "v6.0 retained as production"

# Scenario iteration order — single source of truth for A/B loop + CSV writer + OOS subset
SCENARIO_ORDER = ['baseline', '+DXY', '+EEM', '+SBV-regime', '+all']
OOS_SCENARIO_SUBSET = ['baseline', '+all']  # D-04: OOS runs only these two

# Isolation extremes (D-02). Sized to never trigger on 2015-2026 dxy_z/eem_z ranges.
# verify_extremes_never_trigger() asserts observed |z| < this bound at runtime.
Z_EXTREME_POSITIVE = 999.0
Z_EXTREME_NEGATIVE = -999.0
SBV_MULTIPLIER_NOOP = 2.5   # equals stop_loss_max_multiplier; makes SBV tightening branch a no-op

# Isolation rationale: __post_init__ validation in MDMV2Config requires
# dxy_easing_z < 0, dxy_tightening_z > 0, eem_easing_z > 0, eem_tightening_z < 0.
# We preserve those required signs while pushing magnitudes to 999 so the
# policy branch is never entered on real data.


def build_scenarios() -> dict:
    """Build the 5 scenario MDMV2Config instances per D-01/D-02/D-03.

    D-01 (defaults): all macro-on scenarios use VN30_PRESET defaults for
        their active factor(s). No Phase-45 grid-search winner exists
        because 0/39 combos were accepted.
    D-02 (isolation via extremes): +DXY/+EEM/+SBV-regime disable the
        other factors by pushing z-thresholds to unreachable extremes
        (preserving required signs per MDMV2Config.__post_init__) and
        neutralizing SBV by setting the multiplier equal to
        stop_loss_max_multiplier (2.5), so the SBV tightening branch
        never LOWERS the effective cap.
    D-03 (+all = VN30_PRESET verbatim): the full-stack scenario flips
        only the feature gate; all thresholds stay at VN30_PRESET values.

    Returns:
        Dict with keys matching SCENARIO_ORDER; each value is an
        MDMV2Config suitable for HybridEngine(HybridConfig(v2_config=...)).
    """
    # --- baseline: macro off, v6.0 reference ---------------------------
    baseline = replace(
        VN30_PRESET,
        macro_filter_enabled=False,
        name='baseline',
    )

    # --- +DXY: DXY live, EEM + SBV disabled via extremes ---------------
    plus_dxy = replace(
        VN30_PRESET,
        macro_filter_enabled=True,
        # DXY: VN30_PRESET defaults (live) — no override
        # EEM: unreachable extremes (signs preserved per __post_init__)
        eem_easing_z_threshold=Z_EXTREME_POSITIVE,     # still > 0
        eem_tightening_z_threshold=Z_EXTREME_NEGATIVE, # still < 0
        # SBV: multiplier equals stop_loss_max_multiplier (no tightening effect)
        sbv_tightening_stop_loss_max_multiplier=SBV_MULTIPLIER_NOOP,
        name='+DXY',
    )

    # --- +EEM: EEM live, DXY + SBV disabled via extremes ---------------
    plus_eem = replace(
        VN30_PRESET,
        macro_filter_enabled=True,
        # DXY: unreachable extremes (signs preserved)
        dxy_easing_z_threshold=Z_EXTREME_NEGATIVE,     # still < 0
        dxy_tightening_z_threshold=Z_EXTREME_POSITIVE, # still > 0
        # EEM: VN30_PRESET defaults (live) — no override
        # SBV: no-op multiplier
        sbv_tightening_stop_loss_max_multiplier=SBV_MULTIPLIER_NOOP,
        name='+EEM',
    )

    # --- +SBV-regime: SBV live, DXY + EEM disabled via extremes --------
    plus_sbv = replace(
        VN30_PRESET,
        macro_filter_enabled=True,
        # DXY: unreachable extremes
        dxy_easing_z_threshold=Z_EXTREME_NEGATIVE,
        dxy_tightening_z_threshold=Z_EXTREME_POSITIVE,
        # EEM: unreachable extremes
        eem_easing_z_threshold=Z_EXTREME_POSITIVE,
        eem_tightening_z_threshold=Z_EXTREME_NEGATIVE,
        # SBV: VN30_PRESET default multiplier (1.5) — live
        name='+SBV-regime',
    )

    # --- +all: VN30_PRESET as-shipped (D-03) ---------------------------
    plus_all = replace(
        VN30_PRESET,
        macro_filter_enabled=True,
        name='+all',
    )

    return {
        'baseline': baseline,
        '+DXY': plus_dxy,
        '+EEM': plus_eem,
        '+SBV-regime': plus_sbv,
        '+all': plus_all,
    }


def run_engine(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Run HybridEngine on df with the given MDMV2Config.

    Mirrors analysis/validate_v9.py::run_engine — two_phase_enabled=True,
    filter_enabled=False. df is defensively copied inside engine.run()
    already but we copy here too so callers can re-run scenarios on
    shared data without side effects.
    """
    engine = HybridEngine(HybridConfig(
        v2_config=cfg,
        two_phase_enabled=True,
        filter_enabled=False,
    ))
    return engine.run(df.copy())


def verify_extremes_never_trigger(df_with_macro_cols: pd.DataFrame) -> dict:
    """D-02 sanity check: prove isolation extremes are unreachable on 2015-2026 data.

    The +DXY/+EEM/+SBV-regime scenarios rely on |z| >= 999 thresholds to
    disable the OTHER factors. If observed dxy_z or eem_z ever reach 999
    in the data window, those scenarios silently leak factor effects.

    This helper runs on a DataFrame produced by a macro-on engine run
    (which gains dxy_z + eem_z columns via add_macro_columns). Any
    macro-on scenario will do — simplest is to call it on the +all run
    once, since VN30_PRESET emits the same underlying z-columns as
    +DXY/+EEM.

    Args:
        df_with_macro_cols: DataFrame with 'dxy_z' and 'eem_z' columns.

    Returns:
        Dict with:
          dxy_z_abs_max: max(|dxy_z|) observed in the window
          eem_z_abs_max: max(|eem_z|) observed in the window
          headroom: smallest gap between observed max and Z_EXTREME_POSITIVE
                    across both factors (positive means safe)

    Raises:
        AssertionError: if either observed |z| >= Z_EXTREME_POSITIVE.
        KeyError: if required columns are missing (hard fail — scenario
            builder was run against the wrong engine results).
    """
    if 'dxy_z' not in df_with_macro_cols.columns:
        raise KeyError(
            "dxy_z column absent — verify_extremes_never_trigger must be "
            "called on a macro-on engine results DataFrame (run +all scenario first)."
        )
    if 'eem_z' not in df_with_macro_cols.columns:
        raise KeyError("eem_z column absent — see dxy_z KeyError above.")

    dxy_abs_max = float(df_with_macro_cols['dxy_z'].abs().max())
    eem_abs_max = float(df_with_macro_cols['eem_z'].abs().max())

    assert dxy_abs_max < Z_EXTREME_POSITIVE, (
        f"observed |dxy_z| max = {dxy_abs_max:.3f} >= Z_EXTREME_POSITIVE "
        f"({Z_EXTREME_POSITIVE}); isolation extremes LEAK in +EEM/+SBV "
        f"scenarios — increase Z_EXTREME_POSITIVE to > {dxy_abs_max:.3f}."
    )
    assert eem_abs_max < Z_EXTREME_POSITIVE, (
        f"observed |eem_z| max = {eem_abs_max:.3f} >= Z_EXTREME_POSITIVE "
        f"({Z_EXTREME_POSITIVE}); isolation extremes LEAK in +DXY/+SBV "
        f"scenarios — increase Z_EXTREME_POSITIVE to > {eem_abs_max:.3f}."
    )

    headroom = min(
        Z_EXTREME_POSITIVE - dxy_abs_max,
        Z_EXTREME_POSITIVE - eem_abs_max,
    )
    return {
        'dxy_z_abs_max': dxy_abs_max,
        'eem_z_abs_max': eem_abs_max,
        'headroom': headroom,
    }


# ═══════════════════════════════════════════════════════════════════════
# Gate helpers (Plan 02) — pure functions consumed by Plan 03 main()
# ═══════════════════════════════════════════════════════════════════════


def load_hard_gate_thresholds() -> dict:
    """Load VAL-02 HARD gate thresholds per D-05.

    CAGR floor comes from output/v10_reconciled_baseline.json (Phase 42
    BASE-02 canonical tuple) so we never hardcode the floor value in this
    script — any future reconciliation re-run updates the gate automatically.
    MaxDD ceiling is the module constant HARD_GATE_MAX_DD_CEILING = -20.0
    (milestone decision, not subject to baseline drift).

    Returns:
        Dict with:
          cagr_floor: float (from reconciled baseline cagr_pct field)
          max_dd_ceiling: float (HARD_GATE_MAX_DD_CEILING, always -20.0)
          baseline_source: str (the JSON path, for report provenance)
          schema_version: int (from JSON, for compatibility tracking)

    Raises:
        FileNotFoundError: if RECONCILED_BASELINE_JSON missing (message
            points to Phase 42 Plan 42-05 as the owner).
        KeyError: if JSON lacks 'cagr_pct' key (schema drift — fail loud).
    """
    if not os.path.exists(RECONCILED_BASELINE_JSON):
        raise FileNotFoundError(
            f"{RECONCILED_BASELINE_JSON} not found. "
            "Phase 42 Plan 42-05 owns this artifact; verify "
            "output/v10_reconciled_baseline.json exists (force-added past "
            "output/ gitignore) before running Phase 46 validation."
        )
    with open(RECONCILED_BASELINE_JSON, 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    if 'cagr_pct' not in baseline:
        raise KeyError(
            f"'cagr_pct' missing from {RECONCILED_BASELINE_JSON}. "
            f"Found keys: {sorted(baseline.keys())}. Schema drift — "
            "check Phase 42 BASE-02 contract."
        )
    return {
        'cagr_floor': float(baseline['cagr_pct']),
        'max_dd_ceiling': HARD_GATE_MAX_DD_CEILING,
        'baseline_source': RECONCILED_BASELINE_JSON,
        'schema_version': baseline.get('schema_version', None),
    }


def evaluate_hard_gate(metrics: dict, thresholds: dict) -> dict:
    """Evaluate VAL-02 HARD gate against a single scenario's metrics.

    D-05 rule: pass iff
      (cagr_pct >= cagr_floor) AND (max_dd_pct > max_dd_ceiling)
    where max_dd_pct and max_dd_ceiling are both negative; "strictly
    less negative" means "observed drawdown shallower than the -20% cap".

    Args:
        metrics: Dict from compute_metrics() — must have 'cagr_pct' and
            'max_dd_pct' keys (float percent values; e.g. reconciled baseline
            cagr and its max drawdown).
        thresholds: Dict from load_hard_gate_thresholds() — must have
            'cagr_floor' and 'max_dd_ceiling'.

    Returns:
        Dict with:
          passed: bool — True iff both sub-gates pass
          cagr_pass: bool
          max_dd_pass: bool
          cagr_observed: float
          max_dd_observed: float
          cagr_required: float (>=)
          max_dd_required: float (strictly > i.e. shallower-than)
          detail: str — one-line human summary for the report
    """
    cagr_obs = float(metrics['cagr_pct'])
    max_dd_obs = float(metrics['max_dd_pct'])
    cagr_req = float(thresholds['cagr_floor'])
    max_dd_req = float(thresholds['max_dd_ceiling'])

    cagr_pass = cagr_obs >= cagr_req
    # max_dd_obs and max_dd_req both negative. 'shallower' = less negative = greater.
    max_dd_pass = max_dd_obs > max_dd_req
    passed = cagr_pass and max_dd_pass

    cagr_glyph = '✓' if cagr_pass else '✗'
    maxdd_glyph = '✓' if max_dd_pass else '✗'
    detail = (
        f"CAGR {cagr_glyph} {cagr_obs:.2f}% vs floor {cagr_req:.2f}% | "
        f"MaxDD {maxdd_glyph} {max_dd_obs:.2f}% vs ceiling {max_dd_req:.2f}%"
    )

    return {
        'passed': passed,
        'cagr_pass': cagr_pass,
        'max_dd_pass': max_dd_pass,
        'cagr_observed': cagr_obs,
        'max_dd_observed': max_dd_obs,
        'cagr_required': cagr_req,
        'max_dd_required': max_dd_req,
        'detail': detail,
    }


# Plan 02 still-to-add: lookup_walkforward_degradation(), run_parity_gate()
# Plan 03 adds: main() orchestration + report/CSV/verdict writers
