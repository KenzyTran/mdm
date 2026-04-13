---
phase: 37-backtest-validation
plan: "01"
subsystem: analysis-pipeline
tags: [formula-kwarg, momentum, rs-rating, tdd, cache]
dependency_graph:
  requires: []
  provides: [formula-kwarg-in-build-momentum-raw-frame, formula-kwarg-in-run-v8-backtest]
  affects: [analysis/_vn100_pipeline.py]
tech_stack:
  added: []
  patterns: [formula-branch-in-rs-computation, formula-encoded-cache-filename]
key_files:
  created:
    - tests/phase37/__init__.py
    - tests/phase37/test_formula_param.py
  modified:
    - analysis/_vn100_pipeline.py
decisions:
  - "formula kwarg defaults to weighted_roc so all existing callers (Phase 36 tests, sweep scripts) require zero changes"
  - "Cache filename encodes formula (momentum_raw_{formula}_{min_d}_{max_d}.parquet) to prevent cross-formula cache collisions"
  - "Test for roc126 divergence from weighted_roc uses crafted price series (recent pump vs long-term recovery) where cross-sectional ranking order definitively differs between formulas — random walk panels with same seed produce identical ordinal ranking regardless of formula"
  - "formula pass-through test uses mock + try/except pattern to verify call args without requiring full backtest data"
metrics:
  duration: "4 minutes"
  completed_date: "2026-04-13"
  tasks_completed: 2
  files_changed: 3
---

# Phase 37 Plan 01: Formula Kwarg Wiring Summary

`build_momentum_raw_frame` and `run_v8_backtest` now accept `formula` kwarg (`"weighted_roc"` | `"roc126"`) with separate cache files per formula, enabling Plan 02's in-sample sweep to compare RS formula variants without silent identical results.

## What Was Built

### Change 1 — `build_momentum_raw_frame` in `analysis/_vn100_pipeline.py`

- Added `formula: str = "weighted_roc"` parameter
- Added `ValueError` guard for unknown formula strings
- Updated cache path: `momentum_raw_{formula}_{min_d}_{max_d}.parquet`
- RS computation block replaced with formula branch:
  - `roc126`: `close / close.shift(126) - 1.0` (single lookback, cross-sectional ranked)
  - `weighted_roc`: `0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252` (unchanged from prior behavior)

### Change 2 — `run_v8_backtest` in `analysis/_vn100_pipeline.py`

- Added `formula: str = "weighted_roc"` parameter (after `entry_cfg`)
- Added docstring entry: `formula: RS formula for build_momentum_raw_frame ('weighted_roc' | 'roc126'). Default 'weighted_roc'.`
- Changed `build_momentum_raw_frame(panel)` call to `build_momentum_raw_frame(panel, formula=formula)`
- `precomputed["momentum_raw"]` injection path unchanged (formula irrelevant when caller pre-injects raw)

### Task 1 — Test Scaffold (TDD RED then GREEN)

Created `tests/phase37/test_formula_param.py` with 7 tests:
1. `test_build_momentum_raw_frame_default_formula` — default call produces non-NaN rs_rating
2. `test_build_momentum_raw_frame_weighted_roc` — explicit weighted_roc matches default output
3. `test_build_momentum_raw_frame_roc126` — roc126 produces DIFFERENT rs_rating from weighted_roc (uses crafted diverging panel)
4. `test_invalid_formula_raises` — ValueError with message referencing valid options
5. `test_cache_filename_includes_formula` — roc126 cache file contains "roc126" in name
6. `test_run_v8_backtest_formula_kwarg_accepted` — signature introspection confirms `formula` param with default `"weighted_roc"`
7. `test_formula_passthrough` — mock confirms `run_v8_backtest(formula="roc126")` calls `build_momentum_raw_frame` with `formula="roc126"`

## Verification Results

```
tests/phase37/test_formula_param.py::test_build_momentum_raw_frame_default_formula PASSED
tests/phase37/test_formula_param.py::test_build_momentum_raw_frame_weighted_roc PASSED
tests/phase37/test_formula_param.py::test_build_momentum_raw_frame_roc126 PASSED
tests/phase37/test_formula_param.py::test_invalid_formula_raises PASSED
tests/phase37/test_formula_param.py::test_cache_filename_includes_formula PASSED
tests/phase37/test_formula_param.py::test_run_v8_backtest_formula_kwarg_accepted PASSED
tests/phase37/test_formula_param.py::test_formula_passthrough PASSED
7 passed in 0.47s

tests/strategies/momentum/ — 29 passed (no regression)
```

## Commits

- `1ab1af4`: `test(37-01): add failing tests for formula kwarg wiring` (TDD RED)
- `d2604f9`: `feat(37-01): add formula kwarg to build_momentum_raw_frame and run_v8_backtest` (GREEN)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 3 roc126 divergence check used random panel — cross-sectional ranks identical**
- **Found during:** Task 2, GREEN phase
- **Issue:** With a random-walk 3-ticker panel, weighted_roc and roc126 happen to produce the same cross-sectional rank ordering, so `rs_rating` was identical despite different formula branches. The test correctly failed during implementation.
- **Fix:** Replaced random panel helper with `_make_panel_diverging_formulas()` that crafts 3 tickers with specifically designed momentum profiles (TA: recent pump, TB: long-term recovery, TC: neutral). This guarantees the two formulas produce different ordinal rankings.
- **Files modified:** `tests/phase37/test_formula_param.py`
- **Commit:** included in `d2604f9`

## Known Stubs

None.

## Self-Check: PASSED

- `analysis/_vn100_pipeline.py` — modified with formula kwarg
- `tests/phase37/__init__.py` — created
- `tests/phase37/test_formula_param.py` — created (7 tests)
- Commits `1ab1af4` and `d2604f9` verified in git log
