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

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
else:
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

    cagr_glyph = 'PASS' if cagr_pass else 'FAIL'
    maxdd_glyph = 'PASS' if max_dd_pass else 'FAIL'
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


def lookup_walkforward_degradation(combo_name: str = None) -> dict:
    """Read walk-forward median_degradation for the +all defaults combo (VAL-03 per D-07).

    Does NOT re-run the 39-combo sweep. Reads the row of
    output/v10_grid_results.csv whose config_name matches
    WALKFORWARD_VN30_PRESET_COMBO (default 'stage3_all_three-c1' —
    matches VN30_PRESET defaults: dxy_easing=-1.0, dxy_tightening=+1.0,
    dxy_tightening_dd=3, eem_easing=+1.0, eem_tightening=-1.0,
    sbv_mult=1.5).

    VAL-03 gate rule (D-07): pass iff median_degradation < 0.30. The CSV's
    own 'accepted' column uses the Phase 45 D-09 composite gate
    (median_degradation < 0.30 AND median_eval_cagr > 0.0); for VAL-03 we
    apply only the degradation half so the gate is interpretable in
    isolation as "walk-forward stability".

    Args:
        combo_name: Override for the target row's config_name. Default
            None → uses WALKFORWARD_VN30_PRESET_COMBO.

    Returns:
        Dict with:
          combo: str                (resolved config_name)
          median_degradation: float (from CSV)
          accepted: bool            (from CSV's own composite D-09 column)
          rejection_reason: str     (from CSV; empty string if accepted)
          passed_gate: bool         (VAL-03 rule: median_degradation < 0.30)
          threshold: float          (WALKFORWARD_DEGRADATION_THRESHOLD = 0.30)
          source_csv: str           (provenance)
          total_combos: int         (row count in CSV)
          total_accepted: int       (sum of CSV's accepted column)

    Raises:
        FileNotFoundError: if WALKFORWARD_GRID_CSV missing (points to
            Phase 45 Plan 03 as owner).
        ValueError: if combo_name not found in the CSV (schema drift).
    """
    target = combo_name if combo_name is not None else WALKFORWARD_VN30_PRESET_COMBO

    if not os.path.exists(WALKFORWARD_GRID_CSV):
        raise FileNotFoundError(
            f"{WALKFORWARD_GRID_CSV} not found. "
            "Phase 45 Plan 03 owns this artifact; re-run "
            "`uv run python analysis/walkforward_grid.py` to regenerate "
            "(or git log for commit 4dd00a0 which force-added it)."
        )

    df = pd.read_csv(WALKFORWARD_GRID_CSV)
    matches = df[df['config_name'] == target]
    if len(matches) == 0:
        available = sorted(df['config_name'].unique().tolist())[:10]
        raise ValueError(
            f"config_name='{target}' not found in {WALKFORWARD_GRID_CSV}. "
            f"First 10 available: {available}. "
            "Check Phase 45 D-07 combo-naming scheme."
        )
    if len(matches) > 1:
        raise ValueError(
            f"config_name='{target}' matches {len(matches)} rows; "
            "expected exactly 1. CSV has non-unique config_name (schema drift)."
        )

    row = matches.iloc[0]
    median_deg = float(row['median_degradation'])
    # CSV's 'accepted' is a boolean column; pandas loads it as str or bool
    # depending on dtype inference. Normalise.
    raw_accepted = row['accepted']
    if isinstance(raw_accepted, str):
        accepted = raw_accepted.strip().lower() == 'true'
    elif pd.isna(raw_accepted):
        accepted = False
    else:
        accepted = bool(raw_accepted)
    rejection_reason = (
        str(row['rejection_reason']) if pd.notna(row['rejection_reason']) else ''
    )

    # Aggregate CSV counts for report context
    if df['accepted'].dtype == object:
        total_accepted = int((df['accepted'].astype(str).str.lower() == 'true').sum())
    else:
        total_accepted = int(df['accepted'].sum())

    return {
        'combo': target,
        'median_degradation': median_deg,
        'accepted': accepted,
        'rejection_reason': rejection_reason,
        'passed_gate': median_deg < WALKFORWARD_DEGRADATION_THRESHOLD,
        'threshold': WALKFORWARD_DEGRADATION_THRESHOLD,
        'source_csv': WALKFORWARD_GRID_CSV,
        'total_combos': int(len(df)),
        'total_accepted': total_accepted,
    }


def run_parity_gate(timeout_sec: int = 300) -> dict:
    """Invoke the Phase 44 parity pytest as the VAL-04 gate (D-08).

    Does NOT duplicate parity logic. Shells out to:
        uv run python -m pytest tests/test_macro_filter_v6_parity.py -v

    Exit code 0 = all 5 tests pass = VAL-04 gate PASS.
    Any non-zero = any test failure = VAL-04 gate FAIL (blocks acceptance
    per the v10.0 HARD gate contract regardless of VAL-01..03 outcome).

    Args:
        timeout_sec: Max seconds to wait. Historical runtime ~90s;
            default 300 gives 3× margin for slow CI.

    Returns:
        Dict with:
          passed: bool          (returncode == 0)
          returncode: int
          stdout_tail: str      (last ~50 lines of stdout)
          stderr_tail: str      (last ~50 lines of stderr)
          tests_passed: int     (parsed from pytest summary; -1 if unparseable)
          tests_failed: int     (parsed from pytest summary; -1 if unparseable)
          test_file: str        (PARITY_TEST_PATH)
          duration_sec: float   (wall-clock subprocess time)

    Does NOT raise — subprocess failures (pytest not installed, test file
    missing, timeout) are captured in the return dict for report inclusion.
    """
    import time
    import re as _re

    cmd = [
        'uv', 'run', 'python', '-m', 'pytest',
        PARITY_TEST_PATH, '-v', '--tb=short',
    ]
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
        )
        rc = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc = -1
        stdout = (exc.stdout or '') + f"\n[TIMEOUT after {timeout_sec}s]"
        stderr = (exc.stderr or '') + f"\n[TIMEOUT after {timeout_sec}s]"
    except FileNotFoundError as exc:
        # 'uv' not in PATH or similar — capture and fail the gate
        rc = -2
        stdout = ''
        stderr = f"[subprocess FileNotFoundError: {exc}]"
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
        # PermissionError (OSError subclass — Windows App Control denies
        # _ctypes.pyd), other OS errors, and stdout decode failures.
        rc = -3
        stdout = ''
        stderr = f"[subprocess {type(exc).__name__}: {exc}]"

    duration = time.time() - start

    # Tail helpers (last N lines)
    def _tail(text: str, n: int = 50) -> str:
        if not text:
            return ''
        lines = text.splitlines()
        return '\n'.join(lines[-n:])

    # Parse pytest summary line: anchored to the trailing "in T.Ts" timing the
    # pytest summary always prints (e.g. "===== 5 passed in 90.21s ====="). Use
    # the LAST match to skip per-test verbose lines that may contain "passed"
    # / "failed" inside test names.
    tests_passed = -1
    tests_failed = -1
    if stdout:
        summary_re = _re.compile(
            r'(?:(\d+)\s+failed)?[,\s]*(?:(\d+)\s+passed)?[^\n]*?\sin\s+[\d.]+s'
        )
        matches = list(summary_re.finditer(stdout))
        if matches:
            failed_str, passed_str = matches[-1].groups()
            if passed_str is not None:
                tests_passed = int(passed_str)
            if failed_str is not None:
                tests_failed = int(failed_str)
        # If no 'failed' token found AND 'passed' found AND rc==0, set failed=0
        if tests_passed >= 0 and tests_failed == -1 and rc == 0:
            tests_failed = 0

    return {
        'passed': rc == 0,
        'returncode': rc,
        'stdout_tail': _tail(stdout, 50),
        'stderr_tail': _tail(stderr, 50),
        'tests_passed': tests_passed,
        'tests_failed': tests_failed,
        'test_file': PARITY_TEST_PATH,
        'duration_sec': duration,
    }


# ═══════════════════════════════════════════════════════════════════════
# Report writers (Plan 03) — text report + CSV
# ═══════════════════════════════════════════════════════════════════════


def write_ab_comparison_report(
    full_metrics: dict,
    oos_metrics: dict,
    wf_lookup: dict,
    extremes_check: dict,
    bh_stats: dict,
    report_path: str = None,
) -> list:
    """Write output/v10_ab_comparison.txt with VAL-01 A/B table + diagnostics.

    Mirrors output/v9_ab_comparison.txt structure; extends from 4 to 5
    scenarios and adds VAL-03 walk-forward reference block (D-07) and
    extremes-headroom block (D-02 runtime sanity).

    Args:
        full_metrics: {scenario_name: metrics_dict} for full-period runs.
        oos_metrics: {scenario_name: metrics_dict} for OOS slice (only
            baseline + +all populated per D-04; others may be None).
        wf_lookup: Dict from lookup_walkforward_degradation().
        extremes_check: Dict from verify_extremes_never_trigger().
        bh_stats: Buy & Hold reference dict with keys
            total_return_pct, cagr_pct, max_dd_pct.
        report_path: Override output path. Default AB_COMPARISON_TXT.

    Returns:
        List of lines written (for the caller to fold into the unified
        validation_report.txt if desired).
    """
    path = report_path if report_path is not None else AB_COMPARISON_TXT
    lines = []
    def log(msg: str = '') -> None:
        lines.append(msg)

    log('=' * 70)
    log('PHASE 46: v10.0 A/B COMPARISON (VAL-01)')
    log(f'Data window: {DATA_START} → {DATA_END}')
    log('=' * 70)

    # Scenarios built
    log(f'\nScenarios built: {SCENARIO_ORDER}')
    log(f'Scenario isolation (D-02): +DXY / +EEM / +SBV-regime disable '
        f'OTHER factors via |z| >= {Z_EXTREME_POSITIVE} extremes and '
        f'SBV multiplier = {SBV_MULTIPLIER_NOOP}.')
    log(f'Isolation sanity check (verify_extremes_never_trigger):')
    log(f'  observed max |dxy_z| = {extremes_check["dxy_z_abs_max"]:.3f} '
        f'(headroom to {Z_EXTREME_POSITIVE}: '
        f'{Z_EXTREME_POSITIVE - extremes_check["dxy_z_abs_max"]:.1f})')
    log(f'  observed max |eem_z| = {extremes_check["eem_z_abs_max"]:.3f} '
        f'(headroom to {Z_EXTREME_POSITIVE}: '
        f'{Z_EXTREME_POSITIVE - extremes_check["eem_z_abs_max"]:.1f})')
    log(f'  headroom ≥ {extremes_check["headroom"]:.1f} → isolation extremes never reachable')

    # ── VAL-01 A/B table (D-01 + D-02 + D-03) ────────────────────────
    log('\n' + '─' * 70)
    log('VAL-01: A/B COMPARISON — 5 scenarios on full period')
    log('─' * 70)
    log(f'\n{"Scenario":<14s} {"TotRet":>9s} {"CAGR":>8s} {"MaxDD":>8s} {"Sharpe":>8s} '
        f'{"Trans":>6s} {"BUY%":>6s} {"CASH%":>6s} {"SELL%":>6s}')
    log('-' * 82)
    for name in SCENARIO_ORDER:
        m = full_metrics[name]
        log(f'{name:<14s} {m["total_return_pct"]:>+8.1f}% {m["cagr_pct"]:>7.2f}% '
            f'{m["max_dd_pct"]:>7.2f}% {m["sharpe_rf3"]:>8.3f} '
            f'{m["transitions"]:>6d} {m["buy_pct"]:>5.1f}% '
            f'{m["cash_pct"]:>5.1f}% {m["sell_pct"]:>5.1f}%')
    log(f'{"B&H VN30":<14s} {bh_stats["total_return_pct"]:>+8.1f}% '
        f'{bh_stats["cagr_pct"]:>7.2f}% {bh_stats["max_dd_pct"]:>7.2f}% '
        f'{"—":>8s} {"—":>6s} {"100.0":>5s}% {"0.0":>5s}% {"0.0":>5s}%')

    # ── Whipsaw diagnostic ───────────────────────────────────────────
    log('\n' + '─' * 70)
    log('WHIPSAW DIAGNOSTIC — SELL count + MA50-breakdown share')
    log(f'v6.0 shipped reference: 124 SELL signals, 83.87% MA50-breakdown share '
        '(from output/v10_reconciled_baseline.json)')
    log('─' * 70)
    baseline_sell = full_metrics['baseline']['sell_count']
    baseline_ma50_share = full_metrics['baseline']['ma50_breakdown_sell_share']
    log(f'\n{"Scenario":<14s} {"SELL#":>6s} {"MA50%":>8s} {"BUY#":>6s} '
        f'{"dSELL":>7s} {"dMA50":>8s}')
    log('-' * 57)
    for name in SCENARIO_ORDER:
        m = full_metrics[name]
        sell_delta = m['sell_count'] - baseline_sell
        if not (np.isnan(m['ma50_breakdown_sell_share']) or np.isnan(baseline_ma50_share)):
            ma50_share_pct = m['ma50_breakdown_sell_share'] * 100
            ma50_delta = (m['ma50_breakdown_sell_share'] - baseline_ma50_share) * 100
        else:
            ma50_share_pct = float('nan')
            ma50_delta = float('nan')
        log(f'{name:<14s} {m["sell_count"]:>6d} {ma50_share_pct:>7.1f}% '
            f'{m["buy_count"]:>6d} {sell_delta:>+7d} {ma50_delta:>+7.1f}%')

    # ── VAL-03 walk-forward reference block ──────────────────────────
    log('\n' + '─' * 70)
    log('VAL-03: WALK-FORWARD STABILITY (lookup from Phase 45 sweep)')
    log('─' * 70)
    log(f'Reading {wf_lookup["source_csv"]} for combo {wf_lookup["combo"]}')
    log(f'  median_degradation:   {wf_lookup["median_degradation"]:.4f}')
    log(f'  gate threshold (D-07): {wf_lookup["threshold"]:.2f}')
    log(f'  passed_gate:          {wf_lookup["passed_gate"]}')
    log(f'  accepted in Phase 45: {wf_lookup["accepted"]} '
        f'(rejection_reason: {wf_lookup["rejection_reason"]})')
    log(f'  total combos in sweep: {wf_lookup["total_combos"]} '
        f'(accepted: {wf_lookup["total_accepted"]})')

    # ── OOS slice preview (D-04 two-scenario subset) ─────────────────
    log('\n' + '─' * 70)
    log(f'OOS SLICE METRICS (D-04: {OOS_START} → {OOS_END}, baseline + +all only)')
    log('─' * 70)
    log(f'\n{"Scenario":<14s} {"CAGR_oos":>10s} {"MaxDD_oos":>11s} {"Sharpe_oos":>11s}')
    log('-' * 50)
    for name in OOS_SCENARIO_SUBSET:
        om = oos_metrics.get(name)
        if om is None:
            log(f'{name:<14s} {"n/a":>10s} {"n/a":>11s} {"n/a":>11s}')
        else:
            log(f'{name:<14s} {om["cagr_pct"]:>9.2f}% {om["max_dd_pct"]:>10.2f}% '
                f'{om["sharpe_rf3"]:>11.3f}')

    # Write report
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'A/B comparison report saved: {path} ({len(lines)} lines)')
    return lines


def write_scenarios_csv(
    full_metrics: dict,
    oos_metrics: dict,
    hard_gate_results: dict,
    bh_stats: dict,
    csv_path: str = None,
) -> int:
    """Write output/v10_ab_scenarios.csv with VAL-01 columns + OOS + HARD-gate.

    Schema extends output/v9_ab_scenarios.csv:
      scenario, sharpe_rf3, cagr_pct, max_dd_pct, total_return_pct,
      transitions, sell_count, ma50_breakdown_sell_share, buy_count,
      buy_pct, cash_pct, sell_pct, sell_count_delta, ma50_share_delta,
      cagr_oos, max_dd_oos, sharpe_oos, hard_gate_passed

    Args:
        full_metrics: {scenario: metrics_dict} full-period.
        oos_metrics: {scenario: metrics_dict or None} OOS slice.
        hard_gate_results: {scenario: evaluate_hard_gate dict or None}.
        bh_stats: Buy & Hold reference.
        csv_path: Override path.

    Returns:
        Number of rows written (5 scenarios + 1 B&H row = 6 expected).
    """
    path = csv_path if csv_path is not None else SCENARIOS_CSV
    baseline_sell = full_metrics['baseline']['sell_count']
    baseline_ma50_share = full_metrics['baseline']['ma50_breakdown_sell_share']

    rows = []
    for name in SCENARIO_ORDER:
        m = full_metrics[name]
        om = oos_metrics.get(name)
        gate = hard_gate_results.get(name)
        ma50_delta = (
            (m['ma50_breakdown_sell_share'] - baseline_ma50_share)
            if not (np.isnan(m['ma50_breakdown_sell_share']) or np.isnan(baseline_ma50_share))
            else float('nan')
        )
        rows.append({
            'scenario': name,
            'sharpe_rf3': m['sharpe_rf3'],
            'cagr_pct': m['cagr_pct'],
            'max_dd_pct': m['max_dd_pct'],
            'total_return_pct': m['total_return_pct'],
            'transitions': m['transitions'],
            'sell_count': m['sell_count'],
            'ma50_breakdown_sell_share': m['ma50_breakdown_sell_share'],
            'buy_count': m['buy_count'],
            'buy_pct': m['buy_pct'],
            'cash_pct': m['cash_pct'],
            'sell_pct': m['sell_pct'],
            'sell_count_delta': m['sell_count'] - baseline_sell,
            'ma50_share_delta': ma50_delta,
            'cagr_oos': om['cagr_pct'] if om is not None else float('nan'),
            'max_dd_oos': om['max_dd_pct'] if om is not None else float('nan'),
            'sharpe_oos': om['sharpe_rf3'] if om is not None else float('nan'),
            'hard_gate_passed': gate['passed'] if gate is not None else None,
        })
    # B&H row
    rows.append({
        'scenario': 'B&H VN30',
        'sharpe_rf3': float('nan'),
        'cagr_pct': bh_stats['cagr_pct'],
        'max_dd_pct': bh_stats['max_dd_pct'],
        'total_return_pct': bh_stats['total_return_pct'],
        'transitions': 0,
        'sell_count': 0,
        'ma50_breakdown_sell_share': float('nan'),
        'buy_count': 0,
        'buy_pct': 100.0,
        'cash_pct': 0.0,
        'sell_pct': 0.0,
        'sell_count_delta': float('nan'),
        'ma50_share_delta': float('nan'),
        'cagr_oos': float('nan'),
        'max_dd_oos': float('nan'),
        'sharpe_oos': float('nan'),
        'hard_gate_passed': None,
    })
    df = pd.DataFrame(rows)
    # Canonical column order (fixed per CONTEXT)
    df = df[[
        'scenario', 'sharpe_rf3', 'cagr_pct', 'max_dd_pct', 'total_return_pct',
        'transitions', 'sell_count', 'ma50_breakdown_sell_share', 'buy_count',
        'buy_pct', 'cash_pct', 'sell_pct', 'sell_count_delta', 'ma50_share_delta',
        'cagr_oos', 'max_dd_oos', 'sharpe_oos', 'hard_gate_passed',
    ]]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f'Scenarios CSV saved: {path} ({len(df)} rows)')
    return len(df)


def write_validation_report(gate_results: dict, report_path: str = None) -> bool:
    """Write output/v10_validation_report.txt with per-gate verdicts + D-09 verdict string.

    Contains (in order):
      1. Header (window, date, script name)
      2. Gate summary table (VAL-01..VAL-04 pass/fail)
      3. Per-gate detail blocks
      4. Overall verdict block with LITERAL string on its own line (D-09)
      5. Rejection Narrative (D-10) if any gate failed — 20-40 lines

    Args:
        gate_results: Dict with keys:
            'val_01_ab_complete': bool (A/B ran end-to-end without error)
            'val_02_hard_gate': dict[scenario_name, evaluate_hard_gate_dict]
                for each scenario in OOS_SCENARIO_SUBSET (D-04)
            'val_03_walkforward': dict from lookup_walkforward_degradation()
            'val_04_parity': dict from run_parity_gate()
            'hard_gate_scenario': str — the scenario name whose HARD gate
                result is the VAL-02 verdict (i.e., '+all' per D-04)
            'full_metrics': dict[scenario, compute_metrics_dict] for
                narrative references (full-period baseline reference)
            'baseline_cagr_floor': float — loaded from JSON
        report_path: Override; default REPORT_TXT.

    Returns:
        all_passed: True iff every gate passed → caller returns exit code 0.
    """
    path = report_path if report_path is not None else REPORT_TXT

    # Determine overall pass/fail
    val_01_pass = gate_results['val_01_ab_complete']
    hg_scenario = gate_results['hard_gate_scenario']
    hg_result = gate_results['val_02_hard_gate'].get(hg_scenario)
    val_02_pass = hg_result['passed'] if hg_result is not None else False
    val_03_pass = gate_results['val_03_walkforward']['passed_gate']
    val_04_pass = gate_results['val_04_parity']['passed']
    all_passed = val_01_pass and val_02_pass and val_03_pass and val_04_pass

    lines = []
    def log(msg: str = '') -> None:
        lines.append(msg)

    log('=' * 70)
    log('PHASE 46: v10.0 VALIDATION REPORT')
    log(f'Data window: {DATA_START} → {DATA_END}  |  OOS: {OOS_START} → {OOS_END}')
    log(f'Script: analysis/validate_v10.py')
    log('=' * 70)

    # ── Gate summary ─────────────────────────────────────────────────
    log('\n' + '─' * 70)
    log('GATE SUMMARY')
    log('─' * 70)
    log(f'{"Gate":<8s} {"Name":<40s} {"Result":>10s}')
    log('-' * 60)
    log(f'{"VAL-01":<8s} {"A/B across 5 scenarios":<40s} '
        f'{"PASS" if val_01_pass else "FAIL":>10s}')
    log(f'{"VAL-02":<8s} {"OOS HARD gate on " + hg_scenario:<40s} '
        f'{"PASS" if val_02_pass else "FAIL":>10s}')
    log(f'{"VAL-03":<8s} {"Walk-forward median_deg < 0.30":<40s} '
        f'{"PASS" if val_03_pass else "FAIL":>10s}')
    log(f'{"VAL-04":<8s} {"v6.0 parity regression (pytest)":<40s} '
        f'{"PASS" if val_04_pass else "FAIL":>10s}')
    log('-' * 60)
    log(f'{"OVERALL":<8s} {"All four gates passed":<40s} '
        f'{"PASS" if all_passed else "FAIL":>10s}')

    # ── VAL-02 detail ────────────────────────────────────────────────
    log('\n' + '─' * 70)
    log(f'VAL-02 DETAIL — OOS HARD gate ({OOS_START} → {OOS_END})')
    log(f'Thresholds (D-05): CAGR ≥ {gate_results["baseline_cagr_floor"]:.2f}% '
        f'AND MaxDD > -20.00%')
    log('─' * 70)
    for name in OOS_SCENARIO_SUBSET:
        verdict = gate_results['val_02_hard_gate'].get(name)
        if verdict is None:
            log(f'  {name}: n/a (scenario not run on OOS slice)')
            continue
        log(f'  {name}: {"PASS" if verdict["passed"] else "FAIL"}')
        log(f'    {verdict["detail"]}')

    # ── VAL-03 detail ────────────────────────────────────────────────
    wf = gate_results['val_03_walkforward']
    log('\n' + '─' * 70)
    log(f'VAL-03 DETAIL — Walk-forward stability (lookup from Phase 45)')
    log('─' * 70)
    log(f'  combo:              {wf["combo"]}')
    log(f'  median_degradation: {wf["median_degradation"]:.4f}')
    log(f'  threshold (D-07):   < {wf["threshold"]:.2f}')
    log(f'  verdict:            {"PASS" if wf["passed_gate"] else "FAIL"}')
    if not wf['passed_gate']:
        log(f'  rejection_reason:   {wf["rejection_reason"]}')
        log(f'  source:             {wf["source_csv"]} '
            f'({wf["total_combos"]} combos, {wf["total_accepted"]} accepted)')

    # ── VAL-04 detail ────────────────────────────────────────────────
    pg = gate_results['val_04_parity']
    log('\n' + '─' * 70)
    log(f'VAL-04 DETAIL — v6.0 parity regression (pytest subprocess, D-08)')
    log('─' * 70)
    log(f'  test_file:     {pg["test_file"]}')
    log(f'  returncode:    {pg["returncode"]}')
    log(f'  tests_passed:  {pg["tests_passed"]}')
    log(f'  tests_failed:  {pg["tests_failed"]}')
    log(f'  duration:      {pg["duration_sec"]:.1f} s')
    log(f'  verdict:       {"PASS" if pg["passed"] else "FAIL"}')
    if not pg['passed']:
        log(f'  stdout tail (last 50 lines):')
        for line in pg['stdout_tail'].splitlines():
            log(f'    | {line}')

    # ── Verdict block (D-09) ─────────────────────────────────────────
    log('\n' + '=' * 70)
    log('FINAL VERDICT')
    log('=' * 70)
    log('')  # blank line before verdict for grep-without-word-boundary cleanliness
    if all_passed:
        verdict_str = VERDICT_PASS
    else:
        verdict_str = VERDICT_FAIL
    log(verdict_str)  # ← THE literal string on its own line (D-09)
    log('')

    # ── Rejection Narrative (D-10) ───────────────────────────────────
    if not all_passed:
        log('─' * 70)
        log('REJECTION NARRATIVE')
        log('─' * 70)
        baseline_cagr = gate_results['baseline_cagr_floor']
        log(f'v10.0 macro filter (DXY/EEM 20d z-scores + SBV regime) was evaluated')
        log(f'against the HARD gate (MaxDD < -20% AND CAGR ≥ {baseline_cagr:.2f}% with')
        log(f'walk-forward median degradation < 30% and v6.0 parity regression green).')
        log(f'')
        failed_gates = []
        if not val_01_pass: failed_gates.append('VAL-01 (A/B infrastructure)')
        if not val_02_pass: failed_gates.append('VAL-02 (OOS HARD gate)')
        if not val_03_pass: failed_gates.append('VAL-03 (walk-forward stability)')
        if not val_04_pass: failed_gates.append('VAL-04 (v6.0 parity)')
        log(f'Failed gate(s): {", ".join(failed_gates)}')
        log(f'')
        log(f'Phase 45 evidence (analysis/walkforward_grid.py, 39-combo sweep):')
        log(f'  • Train CAGR median 9.54% vs reconciled baseline {baseline_cagr:.2f}% → ~-2pp drag')
        log(f'    even BEFORE walk-forward year degradation is applied')
        log(f'  • Eval CAGR median 4.57% across 2019-2024 → 54% train→eval degradation')
        log(f'    (vs 30% D-07 gate). Best combo by degradation (stage1_dxy-c3) still fails')
        log(f'    at 0.411 — the entire 39-combo family is OVER-FIT to 2015-2018 training.')
        log(f'  • Per-year single-year MaxDD medians (across 39 combos):')
        log(f'      2019: -8.74%   2020: -15.29%   2021: -19.68%')
        log(f'      2022: -15.33%  2023: -12.72%   2024: -12.45%')
        log(f"    Every per-year DD IS shallower than v6.0's full-period -28.17% — the")
        log(f'    filter DOES dampen drawdowns directionally. The trade-off (eroded CAGR)')
        log(f'    is what the walk-forward gate vetoed.')
        log(f'  • Degradation distribution across 39 combos: min 0.410 / median 0.538 / max 0.645')
        log(f'  • +all scenario full-period 10y return ≈ +146.8% (from sweep row')
        log(f'    stage3_all_three-c0/c1/c2, which trade identically above the SBV layer)')
        log(f'    vs v6.0 reconciled baseline +238.78% at {baseline_cagr:.2f}% CAGR.')
        log(f'')
        log(f'Pointers:')
        log(f'  • Phase 45 sweep results: output/v10_grid_results.csv (force-added past gitignore)')
        log(f'  • Phase 45 best-config JSON: INTENTIONALLY ABSENT — main() aborted when zero')
        log(f'    stages had accepted winners (fabrication refusal, not a bug)')
        log(f'  • Reconciled baseline (CAGR gate reference): output/v10_reconciled_baseline.json')
        log(f'  • Phase 45 SUMMARY (scientific outcome narrative):')
        log(f'    .planning/phases/45-walk-forward-grid-search/'
            f'45-03-execute-sweep-commit-artifacts-SUMMARY.md')
        log(f'')
        log(f'Lessons for v11.0 planning (per Phase 45 Plan 03 lessons-learned):')
        log(f'  1. Walk-forward CV INSIDE the sweep caught an overfit that post-hoc')
        log(f'     validation would have missed — the discipline worked as designed.')
        log(f'  2. The macro-filter thesis is directionally correct (DD reduction)')
        log(f'     but the binary-model price (eroded CAGR) is too high. Future work')
        log(f'     may revisit with (a) fractional sizing (deferred per Phase 44 D-05),')
        log(f'     (b) different publication-lag assumptions, or (c) additional alpha')
        log(f'     sources (ALPHA-01 foreign flow, ALPHA-02 jump model).')
        log(f'  3. "No fabricate on zero-accepted" guard (Phase 45 D-11) prevented')
        log(f'     silently poisoning this validation — preserved pattern for v11+.')
        log(f'')
        log(f'Production decision: v6.0 HybridEngine + fail-safe remains production per')
        log(f'project memory `project_best_model.md` and `.planning/STATE.md` Best VN30')
        log(f'Model entry. The v10.0 milestone publishes this rejection audit (Phase 47')
        log(f'DOC-03 only) and does NOT update `docs/rules_mdm_hybrid.md` or the dashboard.')

    # Save report
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'Validation report saved: {path} ({len(lines)} lines, verdict: {verdict_str})')

    return all_passed


# ═══════════════════════════════════════════════════════════════════════
# Orchestration (main) — Plan 03 Task 3
# ═══════════════════════════════════════════════════════════════════════


def main():
    """Phase 46 end-to-end validation (VAL-01..VAL-05).

    Executes the four gates in order WITHOUT short-circuit (D-06) and
    writes three deliverables:
      - output/v10_ab_comparison.txt (VAL-01)
      - output/v10_ab_scenarios.csv (VAL-01 machine-readable)
      - output/v10_validation_report.txt (VAL-02/03/04 + D-09 verdict)

    Exit code (D-11): 0 on full pass, 1 on any fail.
    """
    print('=' * 70)
    print('PHASE 46: v10.0 VALIDATION PIPELINE')
    print('=' * 70)

    # ── Load HARD gate thresholds early (fail-fast if JSON missing) ──
    thresholds = load_hard_gate_thresholds()
    print(f'\nHARD gate thresholds loaded from {thresholds["baseline_source"]}:')
    print(f'  CAGR floor:     {thresholds["cagr_floor"]:.2f}%')
    print(f'  MaxDD ceiling:  {thresholds["max_dd_ceiling"]:.2f}%')

    # ── Load VN30 data ───────────────────────────────────────────────
    print(f'\nLoading VN30 data: {DATA_START} → {DATA_END}')
    loader = DataLoader('vn30')
    df_full = loader.load(start_date=DATA_START, end_date=DATA_END)
    df_full = build_indicator_dataframe(df_full)
    print(f'VN30 data: {len(df_full)} rows ({df_full["date"].min().date()} → '
          f'{df_full["date"].max().date()})')
    required_max = pd.Timestamp(OOS_END)
    if df_full['date'].max() < required_max:
        raise RuntimeError(
            f"Insufficient data: max date {df_full['date'].max().date()} < "
            f"OOS_END {OOS_END}. Re-pull VN30 data."
        )

    # ── Build scenarios ──────────────────────────────────────────────
    scenarios = build_scenarios()
    print(f'\nScenarios built: {list(scenarios.keys())}')

    # ── VAL-01: A/B across 5 scenarios on full period ────────────────
    print('\n' + '─' * 70)
    print('VAL-01: Running 5 scenarios on full period')
    print('─' * 70)
    full_results: dict = {}
    full_metrics: dict = {}
    val_01_ab_complete = True
    for name in SCENARIO_ORDER:
        print(f'  Running {name}...')
        try:
            res = run_engine(df_full, scenarios[name])
            full_results[name] = res
            full_metrics[name] = compute_metrics(res)
            m = full_metrics[name]
            print(f'    CAGR={m["cagr_pct"]:.2f}%  MaxDD={m["max_dd_pct"]:.2f}%  '
                  f'Sharpe={m["sharpe_rf3"]:.3f}  SELL={m["sell_count"]}')
        except Exception as exc:
            print(f'  ERROR in {name}: {type(exc).__name__}: {exc}')
            print(traceback.format_exc())
            val_01_ab_complete = False
            full_results[name] = None
            full_metrics[name] = {
                'sharpe_rf3': float('nan'), 'cagr_pct': float('nan'),
                'max_dd_pct': float('nan'), 'total_return_pct': float('nan'),
                'transitions': 0, 'sell_count': 0,
                'ma50_breakdown_sell_share': float('nan'), 'buy_count': 0,
                'buy_pct': float('nan'), 'cash_pct': float('nan'),
                'sell_pct': float('nan'),
            }

    # ── D-02 isolation sanity check on +all macro-on results ─────────
    extremes_check = {'dxy_z_abs_max': float('nan'), 'eem_z_abs_max': float('nan'),
                      'headroom': float('nan')}
    if full_results.get('+all') is not None:
        try:
            extremes_check = verify_extremes_never_trigger(full_results['+all'])
            print(f'\nD-02 isolation sanity: |dxy_z|max={extremes_check["dxy_z_abs_max"]:.2f}  '
                  f'|eem_z|max={extremes_check["eem_z_abs_max"]:.2f}  '
                  f'headroom={extremes_check["headroom"]:.1f}')
        except AssertionError as exc:
            print(f'\nD-02 ISOLATION LEAK: {exc}')
            val_01_ab_complete = False

    # ── Buy & Hold reference ─────────────────────────────────────────
    bh_total_ret = (df_full['close'].iloc[-1] / df_full['close'].iloc[0] - 1) * 100
    bh_years = (df_full['date'].iloc[-1] - df_full['date'].iloc[0]).days / 365.25
    bh_cagr = ((1 + bh_total_ret / 100) ** (1 / bh_years) - 1) * 100 if bh_years > 0 else 0.0
    bh_eq = df_full['close'].values / df_full['close'].iloc[0]
    bh_peak = np.maximum.accumulate(bh_eq)
    bh_maxdd = ((bh_eq - bh_peak) / bh_peak).min() * 100
    bh_stats = {
        'total_return_pct': round(bh_total_ret, 2),
        'cagr_pct': round(bh_cagr, 2),
        'max_dd_pct': round(bh_maxdd, 2),
    }

    # ── VAL-02: OOS HARD gate (baseline + +all only, D-04) ───────────
    print('\n' + '─' * 70)
    print(f'VAL-02: OOS slice {OOS_START} → {OOS_END} (baseline + +all only, D-04)')
    print('─' * 70)
    oos_metrics: dict = {}
    hard_gate_per_scenario: dict = {}
    oos_start_ts = pd.Timestamp(OOS_START)
    for name in OOS_SCENARIO_SUBSET:
        res_full = full_results.get(name)
        if res_full is None:
            oos_metrics[name] = None
            hard_gate_per_scenario[name] = None
            print(f'  {name}: n/a (full-period run errored)')
            continue
        oos_slice = res_full[res_full['date'] >= oos_start_ts].copy().reset_index(drop=True)
        if len(oos_slice) < 2:
            oos_metrics[name] = None
            hard_gate_per_scenario[name] = None
            print(f'  {name}: n/a (OOS slice has {len(oos_slice)} rows)')
            continue
        om = compute_metrics(oos_slice)
        oos_metrics[name] = om
        gate = evaluate_hard_gate(om, thresholds)
        hard_gate_per_scenario[name] = gate
        print(f'  {name}: {"PASS" if gate["passed"] else "FAIL"} — {gate["detail"]}')

    # ── VAL-03: Walk-forward lookup (D-06 no short-circuit) ──────────
    print('\n' + '─' * 70)
    print('VAL-03: Walk-forward stability (lookup Phase 45)')
    print('─' * 70)
    try:
        wf_lookup = lookup_walkforward_degradation()
        print(f'  combo={wf_lookup["combo"]}  median_deg={wf_lookup["median_degradation"]:.4f}  '
              f'passed_gate={wf_lookup["passed_gate"]}')
    except Exception as exc:
        print(f'  ERROR in VAL-03 lookup: {type(exc).__name__}: {exc}')
        wf_lookup = {
            'combo': 'N/A', 'median_degradation': float('nan'), 'threshold': 0.30,
            'passed_gate': False, 'accepted': False,
            'rejection_reason': f'lookup failed: {type(exc).__name__}: {exc}',
            'source_csv': WALKFORWARD_GRID_CSV, 'total_combos': 0, 'total_accepted': 0,
        }

    # ── VAL-04: Parity pytest subprocess (D-06 no short-circuit) ─────
    print('\n' + '─' * 70)
    print('VAL-04: v6.0 parity pytest (subprocess)')
    print('─' * 70)
    parity = run_parity_gate(timeout_sec=300)
    print(f'  returncode={parity["returncode"]}  '
          f'passed={parity["tests_passed"]}  failed={parity["tests_failed"]}  '
          f'duration={parity["duration_sec"]:.1f}s  → {"PASS" if parity["passed"] else "FAIL"}')

    # ── Write artifacts (D-06: always, even on failure) ──────────────
    print('\n' + '─' * 70)
    print('Writing Phase 46 deliverables')
    print('─' * 70)
    write_ab_comparison_report(
        full_metrics=full_metrics,
        oos_metrics=oos_metrics,
        wf_lookup=wf_lookup,
        extremes_check=extremes_check,
        bh_stats=bh_stats,
    )
    write_scenarios_csv(
        full_metrics=full_metrics,
        oos_metrics=oos_metrics,
        hard_gate_results=hard_gate_per_scenario,
        bh_stats=bh_stats,
    )
    all_passed = write_validation_report({
        'val_01_ab_complete': val_01_ab_complete,
        'val_02_hard_gate': hard_gate_per_scenario,
        'val_03_walkforward': wf_lookup,
        'val_04_parity': parity,
        'hard_gate_scenario': '+all',      # D-04: +all is the "selected" scenario
        'full_metrics': full_metrics,
        'baseline_cagr_floor': thresholds['cagr_floor'],
    })

    # ── D-11: exit code reflects verdict ─────────────────────────────
    exit_code = 0 if all_passed else 1
    print(f'\nFINAL VERDICT: {"PASS" if all_passed else "FAIL"} → exit {exit_code}')
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
