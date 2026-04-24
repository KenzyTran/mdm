---
phase: 46-ab-oos-validation-hard-gate
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - analysis/validate_v10.py
autonomous: true
requirements: [VAL-01]

must_haves:
  truths:
    - "analysis/validate_v10.py exists as a forked skeleton of analysis/validate_v9.py"
    - "Module constants DATA_START='2015-01-01', DATA_END='2026-03-31', OOS_START='2025-01-01', OOS_END='2026-03-31' defined and importable"
    - "SCENARIO_ORDER is ['baseline', '+DXY', '+EEM', '+SBV-regime', '+all']"
    - "build_scenarios() returns 5 MDMV2Config instances; +DXY/+EEM/+SBV-regime isolate their active factor by pushing inactive factors' thresholds to |z| >= 999 extremes and neutralizing SBV via multiplier=1.0 (per D-02)"
    - "+all scenario equals VN30_PRESET with macro_filter_enabled=True and all default thresholds intact (per D-03)"
    - "A runtime self-check function verify_extremes_never_trigger(df) asserts the observed dxy_z and eem_z range on 2015-2026 is strictly within |z| < 999 so isolation extremes provably never fire"
    - "compute_metrics is imported from analysis.validate_v9 (NOT reimplemented, per D-13)"
  artifacts:
    - path: "analysis/validate_v10.py"
      provides: "Phase 46 validation skeleton with 5-scenario builder + z-extreme sanity check"
      contains: "def build_scenarios"
      min_lines: 120
  key_links:
    - from: "analysis/validate_v10.py"
      to: "strategies.mdm_hybrid.config.VN30_PRESET"
      via: "dataclasses.replace(VN30_PRESET, ...) in build_scenarios"
      pattern: "from dataclasses import replace"
    - from: "analysis/validate_v10.py"
      to: "analysis.validate_v9.compute_metrics"
      via: "module import (determinism contract vs Phase 41/45)"
      pattern: "from analysis\\.validate_v9 import compute_metrics"
---

<objective>
Fork `analysis/validate_v9.py` into a new `analysis/validate_v10.py` scaffold that defines the 5-scenario A/B surface for Phase 46. This plan produces the scenario builder and module constants ONLY — no main(), no gates, no I/O. Later plans (02, 03) add gate helpers and main() orchestration respectively.

Purpose: A forkable, testable scaffold that locks in (a) the 5-scenario identity, (b) the D-02 factor-isolation via threshold extremes, (c) the D-03 +all-equals-VN30_PRESET contract, (d) the D-13 compute_metrics-reuse discipline. The observed-z-range sanity check is a runtime guard that catches the silent bug where an "extreme" threshold (e.g., 999) turns out to be reachable on real data — without the guard, +DXY could secretly trigger EEM policy.

Output: `analysis/validate_v10.py` with imports, module constants, `SCENARIO_ORDER`, `build_scenarios(df)` → `dict[str, MDMV2Config]`, and `verify_extremes_never_trigger(df)` runtime assertion helper.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md

@analysis/validate_v9.py
@strategies/mdm_hybrid/config.py

<interfaces>
<!-- Key contracts the executor consumes. Do NOT re-explore the codebase. -->

From strategies/mdm_hybrid/config.py:
```python
@dataclass
class MDMV2Config:
    # (elided non-macro fields)
    macro_filter_enabled: bool = False
    dxy_easing_z_threshold: float = -1.0
    dxy_tightening_z_threshold: float = +1.0
    eem_easing_z_threshold: float = +1.0           # sign FLIPPED vs DXY (corr +0.19)
    eem_tightening_z_threshold: float = -1.0       # sign FLIPPED vs DXY
    dxy_window_days: int = 20
    eem_window_days: int = 20
    sbv_decay_days: int = 90
    dxy_tightening_dd_threshold: int = 3
    sbv_tightening_stop_loss_max_multiplier: float = 1.5
    name: str = "default"

# VN30_PRESET already has macro_filter_enabled=False (default). The D-03 +all
# scenario must override macro_filter_enabled=True to turn the feature ON.

# __post_init__ validation (enforced when macro_filter_enabled=True):
#   dxy_easing_z_threshold < 0       — DXY easing uses NEGATIVE extreme (z <= threshold)
#   dxy_tightening_z_threshold > 0   — DXY tightening uses POSITIVE extreme
#   eem_easing_z_threshold > 0       — EEM easing uses POSITIVE (sign flipped)
#   eem_tightening_z_threshold < 0   — EEM tightening uses NEGATIVE (sign flipped)
#   0 < sbv_tightening_stop_loss_max_multiplier <= stop_loss_max_multiplier (=2.5 in VN30_PRESET)
#
# CRITICAL consequence: isolation extremes must preserve the REQUIRED SIGNS:
#   To "disable" DXY in +EEM/+SBV scenarios: set dxy_easing_z_threshold=-999.0
#     (still negative, but unreachable) and dxy_tightening_z_threshold=+999.0
#     (still positive, but unreachable). Do NOT flip signs.
#   To "disable" EEM in +DXY/+SBV scenarios: set eem_easing_z_threshold=+999.0
#     (still positive) and eem_tightening_z_threshold=-999.0 (still negative).
#   To "disable" SBV in +DXY/+EEM scenarios: set
#     sbv_tightening_stop_loss_max_multiplier=2.5 (equal to stop_loss_max_multiplier).
#     Using 1.0 would make SBV tightening MORE restrictive than default — that
#     silently introduces SBV effect into a "disabled" scenario. Multiplier = 2.5
#     makes the SBV tightening branch a no-op since it never LOWERS the cap.
```

From analysis/validate_v9.py (lines 41-67, 102-203):
```python
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET

def run_engine(df, cfg) -> pd.DataFrame:
    engine = HybridEngine(HybridConfig(
        v2_config=cfg,
        two_phase_enabled=True,
        filter_enabled=False,
    ))
    return engine.run(df.copy())

def compute_metrics(results: pd.DataFrame) -> dict:
    # Returns: sharpe_rf3, cagr_pct, max_dd_pct, total_return_pct,
    #          transitions, sell_count, ma50_breakdown_sell_share, buy_count,
    #          buy_pct, cash_pct, sell_pct
```

From Phase 44 (engine adds these columns when macro_filter_enabled=True):
```
results DataFrame gains columns: dxy_z, eem_z, sbv_regime
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create analysis/validate_v10.py scaffold with imports, module constants, SCENARIO_ORDER</name>

  <read_first>
    - analysis/validate_v9.py (lines 1-67 for module header + constants pattern; lines 41-42 stdout-reconfigure + sys.path; line 69 compute_metrics is where Plan 45 imports from)
    - strategies/mdm_hybrid/config.py (MDMV2Config dataclass + VN30_PRESET — line 189 onwards)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (D-12, D-13, D-14 — locked decisions for this scaffold)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - Module docstring names VAL-01..VAL-05 requirements and D-12 (forked skeleton) + D-13 (compute_metrics reuse)
    - Running `uv run python -c "from analysis.validate_v10 import SCENARIO_ORDER, DATA_START, DATA_END, OOS_START, OOS_END"` exits 0
    - Running `uv run python -c "from analysis.validate_v10 import compute_metrics; print(compute_metrics)"` shows it is imported from analysis.validate_v9 (print reveals module path)
  </behavior>

  <action>
    Create `analysis/validate_v10.py` with:

    1. Module docstring (verbatim structure — mirror validate_v9.py lines 1-29):
       ```
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
       ```

    2. Imports block copied from validate_v9.py:41-48, plus `from analysis.validate_v9 import compute_metrics` (D-13 reuse):
       ```python
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
       ```

    3. Module Constants block (D-14 windows + gate thresholds):
       ```python
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
       ```

    4. Leave a placeholder comment at EOF noting Plans 02 and 03 will add gate helpers + main():
       ```python
       # Plan 02 adds: load_hard_gate_thresholds(), lookup_walkforward_degradation(),
       #               run_parity_gate()
       # Plan 03 adds: main() orchestration + report/CSV/verdict writers
       ```

    DO NOT add a `main()` function, scenario builder, or any engine-running code in this task — those land in Tasks 2 and 3 of this plan + later plans.
  </action>

  <verify>
    <automated>uv run python -c "from analysis.validate_v10 import SCENARIO_ORDER, DATA_START, DATA_END, OOS_START, OOS_END, VERDICT_PASS, VERDICT_FAIL, compute_metrics; assert SCENARIO_ORDER == ['baseline', '+DXY', '+EEM', '+SBV-regime', '+all']; assert VERDICT_PASS == 'v10 macro filter accepted as production'; assert VERDICT_FAIL == 'v6.0 retained as production'; assert compute_metrics.__module__ == 'analysis.validate_v9'; print('SCAFFOLD OK')"</automated>
  </verify>

  <acceptance_criteria>
    - File `analysis/validate_v10.py` exists
    - `grep -n "from analysis.validate_v9 import compute_metrics" analysis/validate_v10.py` returns 1 hit (D-13)
    - `grep -n "SCENARIO_ORDER = \['baseline', '\+DXY', '\+EEM', '\+SBV-regime', '\+all'\]" analysis/validate_v10.py` returns 1 hit
    - `grep -n "OOS_SCENARIO_SUBSET = \['baseline', '\+all'\]" analysis/validate_v10.py` returns 1 hit (D-04)
    - `grep -n "VERDICT_PASS = \"v10 macro filter accepted as production\"" analysis/validate_v10.py` returns 1 hit (D-09)
    - `grep -n "VERDICT_FAIL = \"v6.0 retained as production\"" analysis/validate_v10.py` returns 1 hit (D-09)
    - `grep -n "HARD_GATE_MAX_DD_CEILING = -20.0" analysis/validate_v10.py` returns 1 hit (D-05)
    - `grep -n "WALKFORWARD_DEGRADATION_THRESHOLD = 0.30" analysis/validate_v10.py` returns 1 hit (D-07)
    - `grep -n "WALKFORWARD_VN30_PRESET_COMBO = 'stage3_all_three-c1'" analysis/validate_v10.py` returns 1 hit (D-07)
    - `grep -n "Z_EXTREME_POSITIVE = 999.0" analysis/validate_v10.py` returns 1 hit
    - `grep -n "SBV_MULTIPLIER_NOOP = 2.5" analysis/validate_v10.py` returns 1 hit
    - The verify command above prints `SCAFFOLD OK` with exit code 0
    - NO `def main(` present in file yet (grep returns 0 hits)
    - NO `def build_scenarios(` present yet (Task 2 adds this)
  </acceptance_criteria>

  <done>Scaffold file exists, constants importable, compute_metrics proven to come from validate_v9, SCENARIO_ORDER matches D-01 5-scenario identity, verdict strings match D-09 exactly.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Add build_scenarios() to validate_v10.py with D-02 factor isolation</name>

  <read_first>
    - analysis/validate_v10.py (file created in Task 1 — see current state)
    - analysis/validate_v9.py (lines 206-276 `build_scenario_configs` for the dataclasses.replace pattern)
    - strategies/mdm_hybrid/config.py (VN30_PRESET lines 189-235 + __post_init__ validation lines 129-156 — enforces sign constraints even on extremes)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (D-01, D-02, D-03)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - `build_scenarios()` returns dict with keys exactly matching `SCENARIO_ORDER`
    - `build_scenarios()['baseline'].macro_filter_enabled == False`
    - `build_scenarios()['+all'].macro_filter_enabled == True` AND all macro threshold fields equal VN30_PRESET values (D-03)
    - `build_scenarios()['+DXY']`: macro_filter_enabled=True, DXY fields = VN30_PRESET defaults, EEM fields = Z_EXTREME_POSITIVE/NEGATIVE, SBV multiplier = SBV_MULTIPLIER_NOOP (2.5)
    - `build_scenarios()['+EEM']`: macro_filter_enabled=True, EEM fields = VN30_PRESET defaults, DXY fields = Z_EXTREME_NEGATIVE/POSITIVE, SBV multiplier = SBV_MULTIPLIER_NOOP
    - `build_scenarios()['+SBV-regime']`: macro_filter_enabled=True, SBV multiplier = VN30_PRESET default (1.5), DXY + EEM all 4 z-thresholds set to extremes
    - All 5 configs pass __post_init__ validation (no AssertionError raised during build)
  </behavior>

  <action>
    Append to `analysis/validate_v10.py` a `build_scenarios()` function that returns a dict of 5 MDMV2Config instances. Use `dataclasses.replace(VN30_PRESET, **overrides)` per validate_v9.py:206-276 precedent.

    Implementation:

    ```python
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
    ```

    Also add a small `run_engine()` helper (copy verbatim from validate_v9.py:102-122) so Plan 03 can call it without re-implementing:

    ```python
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
    ```
  </action>

  <verify>
    <automated>uv run python -c "
from analysis.validate_v10 import build_scenarios, SCENARIO_ORDER, Z_EXTREME_POSITIVE, Z_EXTREME_NEGATIVE, SBV_MULTIPLIER_NOOP
scens = build_scenarios()
assert list(scens.keys()) == SCENARIO_ORDER, f'keys mismatch: {list(scens.keys())}'
assert scens['baseline'].macro_filter_enabled == False
assert scens['+all'].macro_filter_enabled == True
assert scens['+all'].dxy_easing_z_threshold == -1.0, 'D-03 +all must match VN30_PRESET dxy_easing=-1.0'
assert scens['+all'].sbv_tightening_stop_loss_max_multiplier == 1.5, 'D-03 +all must match VN30_PRESET sbv_mult=1.5'
# +DXY isolation
assert scens['+DXY'].dxy_easing_z_threshold == -1.0, '+DXY keeps DXY live'
assert scens['+DXY'].eem_easing_z_threshold == Z_EXTREME_POSITIVE
assert scens['+DXY'].eem_tightening_z_threshold == Z_EXTREME_NEGATIVE
assert scens['+DXY'].sbv_tightening_stop_loss_max_multiplier == SBV_MULTIPLIER_NOOP
# +EEM isolation
assert scens['+EEM'].eem_easing_z_threshold == 1.0, '+EEM keeps EEM live'
assert scens['+EEM'].dxy_easing_z_threshold == Z_EXTREME_NEGATIVE
assert scens['+EEM'].dxy_tightening_z_threshold == Z_EXTREME_POSITIVE
# +SBV isolation
assert scens['+SBV-regime'].sbv_tightening_stop_loss_max_multiplier == 1.5
assert scens['+SBV-regime'].dxy_easing_z_threshold == Z_EXTREME_NEGATIVE
assert scens['+SBV-regime'].eem_easing_z_threshold == Z_EXTREME_POSITIVE
print('5 SCENARIOS BUILT + VALIDATED')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "def build_scenarios" analysis/validate_v10.py` returns exactly 1 hit
    - `grep -n "def run_engine" analysis/validate_v10.py` returns exactly 1 hit
    - `grep -n "two_phase_enabled=True" analysis/validate_v10.py` returns 1 hit (inside run_engine)
    - Verify command above prints `5 SCENARIOS BUILT + VALIDATED` with exit code 0
    - All 5 scenario configs pass MDMV2Config.__post_init__ (tested implicitly by dataclasses.replace succeeding in the verify command; any sign-violation would raise AssertionError)
    - +DXY scenario's eem_easing_z_threshold equals Z_EXTREME_POSITIVE (999.0) — proves isolation extreme matches planned extreme constant
    - +all scenario's dxy_easing_z_threshold equals -1.0 (VN30_PRESET default — D-03 contract)
    - +all scenario's sbv_tightening_stop_loss_max_multiplier equals 1.5 (VN30_PRESET default)
  </acceptance_criteria>

  <done>5 MDMV2Config instances buildable, __post_init__ validation all pass, factor isolation verified, D-03 +all equals VN30_PRESET defaults confirmed.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Add verify_extremes_never_trigger() runtime assertion helper</name>

  <read_first>
    - analysis/validate_v10.py (current state after Task 2)
    - strategies/mdm_hybrid/macro_filter.py (top 80 lines — see how add_macro_columns produces dxy_z and eem_z columns; this is what the helper will range-check)
    - tests/test_macro_filter_v6_parity.py (lines 144-170 — precedent pattern for proving dxy_z + eem_z non-NaN after macro-on run)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - `verify_extremes_never_trigger(df_with_macro_cols)` asserts `df.dxy_z.abs().max() < Z_EXTREME_POSITIVE` AND `df.eem_z.abs().max() < Z_EXTREME_POSITIVE`
    - Raises AssertionError with a specific message containing "observed |z|" and the numeric value of the violating max when the guard fires
    - Returns a dict with keys `dxy_z_abs_max`, `eem_z_abs_max`, `headroom` for logging in the report
    - Does NOT raise when extremes are comfortably above observed range
  </behavior>

  <action>
    Append to `analysis/validate_v10.py`:

    ```python
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
    ```

    End-to-end smoke test (do NOT commit — this is a one-time verify): after writing the helper, run in a temporary python -c invocation that (1) loads VN30 2015-2026 data via DataLoader, (2) builds indicators, (3) runs the +all scenario via run_engine, (4) calls verify_extremes_never_trigger and prints the headroom. If the helper raises, increase Z_EXTREME_POSITIVE constant accordingly. DXY/EEM 20-day z-scores on real market data rarely exceed |z|=5; 999 should have ~994 of headroom.
  </action>

  <verify>
    <automated>uv run python -c "
import pandas as pd
from analysis.validate_v10 import verify_extremes_never_trigger, Z_EXTREME_POSITIVE

# Unit test 1: guard fires on synthetic leak
df_leak = pd.DataFrame({'dxy_z': [0.5, 1.2, 1000.0, 0.1], 'eem_z': [0.0, 0.3, -0.4, 0.2]})
try:
    verify_extremes_never_trigger(df_leak)
    raise SystemExit('guard did NOT fire on 1000.0 dxy_z leak')
except AssertionError as e:
    assert 'observed |dxy_z|' in str(e), f'wrong assertion msg: {e}'

# Unit test 2: missing column raises KeyError
df_missing = pd.DataFrame({'close': [1, 2, 3]})
try:
    verify_extremes_never_trigger(df_missing)
    raise SystemExit('KeyError did NOT fire on missing dxy_z')
except KeyError:
    pass

# Unit test 3: normal range passes + returns expected dict
df_ok = pd.DataFrame({'dxy_z': [-2.3, 1.5, 0.8, -1.0], 'eem_z': [0.1, -0.9, 2.1, 0.3]})
result = verify_extremes_never_trigger(df_ok)
assert result['dxy_z_abs_max'] == 2.3
assert result['eem_z_abs_max'] == 2.1
assert result['headroom'] == Z_EXTREME_POSITIVE - 2.3
print('verify_extremes_never_trigger: 3/3 unit tests PASS')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "def verify_extremes_never_trigger" analysis/validate_v10.py` returns exactly 1 hit
    - `grep -n "observed |dxy_z|" analysis/validate_v10.py` returns 1 hit (assertion message)
    - `grep -n "observed |eem_z|" analysis/validate_v10.py` returns 1 hit (assertion message)
    - Verify command above prints `verify_extremes_never_trigger: 3/3 unit tests PASS` with exit code 0
    - Helper raises AssertionError (NOT silent pass) on synthetic dxy_z=1000 input
    - Helper raises KeyError (NOT AssertionError) when dxy_z column is missing
    - Helper returns dict with keys `dxy_z_abs_max`, `eem_z_abs_max`, `headroom` on success
  </acceptance_criteria>

  <done>Runtime assertion helper exists, fires on synthetic leak, returns diagnostic dict with headroom metric for the Plan 03 report section.</done>
</task>

</tasks>

<verification>
After all 3 tasks:

1. Module importable end-to-end:
   `uv run python -c "from analysis.validate_v10 import SCENARIO_ORDER, build_scenarios, verify_extremes_never_trigger, run_engine, compute_metrics, VERDICT_PASS, VERDICT_FAIL; print('all imports OK')"` — must print exactly `all imports OK`

2. No regression in existing tests (scaffold-only, no runtime behavior change):
   `uv run pytest -m regression tests/test_baseline_determinism.py tests/test_macro_filter_v6_parity.py -v` — all 8 tests PASS (3 baseline determinism + 5 macro-filter parity)

3. File size reasonable (Plans 02 + 03 will add ~300 more lines):
   Line count of `analysis/validate_v10.py` between 150 and 300 after this plan.
</verification>

<success_criteria>
- [ ] `analysis/validate_v10.py` exists with imports, module constants, SCENARIO_ORDER
- [ ] compute_metrics imported from analysis.validate_v9 (D-13 determinism contract)
- [ ] build_scenarios() returns 5 named MDMV2Config instances covering baseline/+DXY/+EEM/+SBV-regime/+all
- [ ] D-02 isolation extremes preserve __post_init__ sign constraints (DXY easing stays <0, tightening >0; EEM flipped)
- [ ] D-03 +all scenario equals VN30_PRESET verbatim (macro_filter_enabled=True only override)
- [ ] verify_extremes_never_trigger() helper raises on leak, returns headroom dict on pass
- [ ] Verdict string constants match D-09 locked format byte-exactly
- [ ] Pre-existing regression tests still green (no side effects from scaffold)
</success_criteria>

<output>
After completion, create `.planning/phases/46-ab-oos-validation-hard-gate/46-01-scenario-scaffold-SUMMARY.md`
</output>
