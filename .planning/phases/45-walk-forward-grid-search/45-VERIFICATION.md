---
phase: 45-walk-forward-grid-search
verified: 2026-04-23T10:45:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Inspect output/v10_grid_results.csv visually and confirm the retain-v6.0 verdict makes scientific sense"
    expected: "All 39 combos show median degradation 0.41-0.65, confirming the macro filter over-fits 2015-2018 training conditions"
    why_human: "Scientific interpretation of the sweep result (all-rejected outcome) requires domain judgment, not just code inspection"
---

# Phase 45: Walk-Forward Grid Search Verification Report

**Phase Goal:** Macro filter thresholds are selected by a rolling-window grid search whose acceptance rule is `median degradation < 30%` across walk-forward years — overfitting is ruled out INSIDE the sweep, not after

**Verified:** 2026-04-23T10:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Context: Zero-Accepted Outcome is Not a Gap

The sweep executed cleanly and produced 0/39 accepted combos. Per Plan 03 line 211, this is a documented legitimate outcome ("If ZERO combos are accepted across all stages, that's a legitimate scientific result"). The goal is about the discipline of the search method — whether overfitting is ruled out INSIDE the sweep — not whether any combo passed. The grid search correctly applied the gate and correctly refused to emit `v10_grid_best.json` when no stage had a winner. This is verified behavior.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Script runs train 2015-2018 + annual walk-forward 2019-2024 + refuses 2025+ data (date-range guard) | VERIFIED | `OOS_FENCE = '2025-01-01'`, strict `<` assert in `load_vn30_data`, EVAL_YEARS = [2019..2024] only |
| 2 | Per-combo `median_degradation` computed; combos with `>= 30%` marked rejected (not silently dropped) | VERIFIED | D-09 gate at line 338 uses `>=`, CSV has 39 rows all with `rejection_reason` populated |
| 3 | `output/v10_grid_results.csv` contains per-combo config + per-window metrics + accept/reject; JSON guard correctly absent when 0 accepted | VERIFIED (with documented exception on JSON) | CSV: 39 rows x 52 cols, all required columns present; JSON absent per `main()` guard at line 669-673 |
| 4 | Selection never considers 2025-2026 data — verified by test asserting synthetic 2025-labeled data is excluded | VERIFIED | 2 regression tests in `tests/test_walkforward_oos_guard.py`, both PASS |
| 5 | Full regression suite (10 tests) stays green post-sweep | VERIFIED | `python -m pytest -m regression` → 10 passed in 70.98s |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `analysis/walkforward_grid.py` | Staged walk-forward sweep orchestrator | VERIFIED | 685 lines, importable, all 7 required functions present: `load_vn30_data`, `build_combo_grid`, `run_combo`, `select_winner`, `write_results_csv`, `write_best_json`, `main` |
| `tests/test_walkforward_oos_guard.py` | 2 @pytest.mark.regression OOS guard tests | VERIFIED | 211 lines, both tests pass, imports from `analysis.walkforward_grid` |
| `output/v10_grid_results.csv` | 39 rows x ~45 cols, per-combo config + metrics + accept decision | VERIFIED | 39 rows x 52 cols (19,851 bytes), stage split 27/9/3, all 52 columns present |
| `output/v10_grid_best.json` | Intentionally absent (0 combos accepted, main() guard) | VERIFIED (documented exception) | main() guard at line 669: `if all(s['winner'] is not None ...)` — correctly skips JSON write when any stage has no winner |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `walkforward_grid.py` | `analysis/validate_v9.py::compute_metrics` | `from analysis.validate_v9 import compute_metrics` | WIRED | Line 69 — D-16 reuse rule honored, not reimplemented |
| `walkforward_grid.py` | `strategies/mdm_hybrid/config.py::VN30_PRESET` | `from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET` | WIRED | Line 68, used in `run_combo` via `replace(VN30_PRESET, ...)` |
| `walkforward_grid.py` | `strategies/mdm_hybrid/mdm_hybrid_engine.py::HybridEngine` | `HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False))` | WIRED | Line 276, exactly matching D-04 single-run pattern |
| `walkforward_grid.py` | `output/v10_grid_results.csv` | `write_results_csv(all_rows, RESULTS_CSV)` after all 3 stages | WIRED | Line 667, confirmed CSV exists on disk (39 rows) |
| `test_walkforward_oos_guard.py` | `walkforward_grid.py::load_vn30_data` | lazy import pattern (stdout-safe), calls `load_vn30_data(df_override=df_leaky)` | WIRED | Lines 69-95 in test file |
| `test_walkforward_oos_guard.py` | `walkforward_grid.py::select_winner` | lazy import, `select_winner([legit_row, poisoned_row], 'stage1_dxy')` | WIRED | Lines 149-160 in test file |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `output/v10_grid_results.csv` | `all_rows` (39 dicts) | `run_combo()` calls `HybridEngine.run(df.copy())` on live VN30 data from `DataLoader('vn30')` | Yes — engine run on real 2015-2024 VN30 data; 39 combos each with 6 per-year metrics | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CSV has exactly 39 rows split 27/9/3 | `python -c "import pandas as pd; df=pd.read_csv('output/v10_grid_results.csv'); print(df['stage'].value_counts().to_dict())"` | `{'stage1_dxy': 27, 'stage2_eem': 9, 'stage3_all_three': 3}` | PASS |
| All required columns present | `python -c "..."` checking required_cols subset | Required cols present: True, Missing: set() | PASS |
| All rejections are via `median_degradation >= 0.30` | CSV rejection_reason column | 26 unique degradation values all >= 0.410, format `median_degradation X.XXX >= 0.30` | PASS |
| `cagr_train_pct`, `sharpe_rf3_train`, `max_dd_train_pct` present | Column check | All 3 present in 52-column CSV | PASS |
| Per-year columns for 2019-2024 (18 metric + 6 degradation) | Column check | `cagr_eval_2019_pct` through `max_dd_eval_2024_pct`, `degradation_2019` through `degradation_2024` all present | PASS |
| No 2025 years in eval columns | Column listing | Max eval year is `degradation_2024` — no 2025 columns exist | PASS |
| OOS guard raises AssertionError on 2025 data | `test_assert_fires_on_2025_data` | PASSED (2 tests, 70.98s total) | PASS |
| Full 10 regression tests green | `python -m pytest -m regression` | 10 passed in 70.98s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WF-01 | Plans 01, 02, 03 | Rolling-window grid search infrastructure — train 2015-2018, annual walk-forward 2019/2020/2021/2022/2023/2024, held-out test 2025-2026; implementation in `analysis/walkforward_grid.py` | SATISFIED | `analysis/walkforward_grid.py` (685 lines), TRAIN_START/TRAIN_END/EVAL_YEARS/OOS_FENCE constants verified, commit `9400fb7`+`097a7d5`+`9180905` |
| WF-02 | Plans 01, 03 | Median degradation metric per combo; accepted only if median degradation < 30% | SATISFIED | `median_degradation = np.median(degradations)` at line 329; D-09 gate `>= DEGRADATION_THRESHOLD` at line 338; all 39 CSV rows have populated `rejection_reason` |
| WF-03 | Plans 01, 03 | Grid search dashboard — `output/v10_grid_results.csv` with per-scenario median CAGR/Sharpe/MaxDD/degradation, sortable, reproducible from locked params | SATISFIED | CSV committed in `4dd00a0` (only file changed); `v10_grid_best.json` correctly absent per main() guard (0 accepted); CSV alone is sufficient to reproduce any future winner if gate reopened |

All 3 requirements in REQUIREMENTS.md are marked `[x]` complete and map to Phase 45. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `analysis/walkforward_grid.py` | 92 | `"pd.DataFrame | None"` as string annotation (Python 3.10 union type workaround) | Info | Not a stub — intentional forward-reference for Python 3.10 compatibility |

No stubs, no placeholder returns, no hardcoded empty data arrays that flow to user-visible output. The `return None, []` in `select_winner` at line 403-404 is correct behavior when no combos are accepted (not a stub — it is the documented zero-accepted path).

### SC-3 Documented Exception: v10_grid_best.json Intentionally Absent

The plan's Task 2 acceptance criteria included `test -f output/v10_grid_best.json` — which technically fails. However:

1. The `main()` guard at line 669 (`if all(s['winner'] is not None for s in stages_result.values())`) correctly refuses to write the JSON when any stage has no winner
2. The guard prints `"WARNING: at least one stage has no accepted winner - {BEST_JSON} NOT written"` — this is the exact message documented in SUMMARY.md
3. Plan 03's `<resume-signal>` (line 211) explicitly documents the zero-accepted outcome as a legitimate scientific result requiring no repair
4. The human checkpoint (Task 3) was completed and the retain-v6.0 verdict was approved
5. The commit message `4dd00a0` explicitly states "output/v10_grid_best.json is INTENTIONALLY NOT written"

**Classification: Passed with documented exception.** The guard is the correct defensive behavior. Fabricating a JSON with null winners would silently poison Phase 46.

### Human Verification Required

1. **Retain-v6.0 Scientific Verdict**

   **Test:** Open `output/v10_grid_results.csv` and review the per-stage degradation distributions. Confirm the interpretation that DXY/EEM/SBV signals reduce per-year MaxDD vs v6.0's -28.17% full-period DD, but the CAGR cost is prohibitive (median 54% degradation vs 30% threshold).
   
   **Expected:** Stage 1 best combo: `stage1_dxy-c3`, median_eval_cagr_pct=5.58%, median_degradation=0.411. Every combo in every stage fails with degradation > 0.40. All 39 rejection_reasons follow the pattern `median_degradation X.XXX >= 0.30`.
   
   **Why human:** Scientific interpretation of an all-rejected sweep outcome requires domain judgment about whether the methodology correctly identified macro filter over-fitting vs whether there is a data or implementation issue that should be investigated before closing the phase.

---

## Gaps Summary

No gaps. All 5 observable truths verified, all required artifacts substantive and wired, all 3 requirements satisfied, regression suite fully green (10/10). The only non-standard outcome is the intentional absence of `v10_grid_best.json`, which is correctly classified as a documented exception (the `main()` guard implementing the D-11 "no-fabricate-on-zero-accepted" rule).

Phase 45 goal is achieved: the grid search correctly implements the overfitting-rule-inside-the-sweep methodology AND honors the OOS fence, as demonstrated by:
- The 30% degradation threshold being enforced per-combo (not post-hoc)
- The OOS fence preventing 2025+ data entry at both runtime-assert and pytest-regression levels
- The all-rejected outcome being a valid scientific result, not an implementation failure

---

_Verified: 2026-04-23T10:45:00Z_
_Verifier: Claude (gsd-verifier)_
