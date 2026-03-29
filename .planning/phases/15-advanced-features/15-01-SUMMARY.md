---
phase: 15-advanced-features
plan: 01
subsystem: mdm-hybrid
tags: [indicator-filter, ha-smoothed, confidence-score, tdd]
dependency_graph:
  requires: [indicator_filter.py, mdm_hybrid_engine.py, config.py]
  provides: [ha_smooth_condition, confidence_return, confidence_column]
  affects: [indicator_filter.py, mdm_hybrid_engine.py, config.py, test_indicator_filter.py, test_hybrid_engine.py]
tech_stack:
  added: []
  patterns: [tuple-return, toggleable-condition, NaN-safe-static-method]
key_files:
  created: []
  modified:
    - strategies/mdm_hybrid/indicator_filter.py
    - strategies/mdm_hybrid/mdm_hybrid_engine.py
    - tests/test_indicator_filter.py
    - tests/test_hybrid_engine.py
decisions:
  - "ha_smooth_enabled defaults to False, preserving Phase 14 baseline"
  - "evaluate() returns tuple(Verdict, float) instead of bare Verdict"
  - "confidence = agree_count / total_active (0.0-1.0 range)"
  - "filter-disabled path defaults confidence to 1.0"
metrics:
  duration: 22min
  completed: "2026-03-29T12:56:32Z"
---

# Phase 15 Plan 01: HA Smoothed 55 Condition + Confidence Score Summary

Added Heikin Ashi Smoothed 55 as 7th toggleable filter condition with NaN-safe static methods, and changed evaluate() to return (Verdict, float) tuple exposing agreement ratio as confidence score wired into engine output DataFrame.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| ede8a30 | test | Add failing tests for HA Smooth condition and confidence return (TDD RED) |
| 07ffa1c | feat | Add HA Smoothed 55 condition and confidence return to IndicatorFilter (TDD GREEN) |
| 6519b4a | feat | Wire confidence column into HybridEngine output and update callers |

## Changes Made

### Task 1: IndicatorFilter HA Smooth + Confidence (TDD)

**FilterConfig** (indicator_filter.py):
- Added `ha_smooth_enabled: bool = False` field
- Updated `active_count()` to include `ha_smooth_enabled` in sum

**IndicatorFilter** (indicator_filter.py):
- Added `ha_smooth_bullish(row)` static method: checks `ha_smooth_close > ha_smooth_open` with NaN safety via `row.get()` and `pd.notna()`
- Added `ha_smooth_bearish(row)` static method: checks `ha_smooth_close < ha_smooth_open` with NaN safety
- `_get_bullish_votes()`: appends HA vote when `ha_smooth_enabled=True`
- `_get_bearish_votes()`: appends HA vote when `ha_smooth_enabled=True`
- `evaluate()` return type changed from `Verdict` to `tuple[Verdict, float]`
- All return paths updated: `CONFIRM, 1.0` (unknown/empty), `OVERRIDE, 0.0`, `CONFIRM, agree_ratio`, `VETO, agree_ratio`

**Tests** (test_indicator_filter.py):
- Updated `_make_row` and `_make_bearish_row` defaults with `ha_smooth_close`/`ha_smooth_open`
- Updated all 12 existing `evaluate()` calls to destructure tuple
- Added TestHASmoothCondition (6 tests): bullish, bearish, NaN safety, toggle off/on, active_count
- Added TestConfidence (5 tests): tuple return, all/none/partial agree, baseline unchanged

### Task 2: Confidence Column in HybridEngine

**mdm_hybrid_engine.py**:
- Added `df['confidence'] = 0.0` column initialization
- Changed evaluate call: `verdict, confidence = self.indicator_filter.evaluate(...)`
- Added `df.at[idx, 'confidence'] = confidence` after evaluate
- Added else branch: `df.at[idx, 'confidence'] = 1.0` when filter disabled

**test_hybrid_engine.py**:
- `test_confidence_column_exists`: verifies float values 0.0-1.0 with filter enabled
- `test_confidence_column_filter_disabled`: verifies all 1.0 without filter
- `test_baseline_unchanged`: verifies both paths produce same row count with confidence column

## Verification Results

- `uv run pytest tests/test_indicator_filter.py -k "not TradingViewParity"`: 48 passed
- `uv run pytest tests/test_hybrid_engine.py -k "confidence or baseline"`: 3 passed
- `uv run pytest tests/test_hybrid_engine.py -k "snapshot or config_defaults or vetoed_ftd"`: 3 passed (regression)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all functionality is fully wired.

## Self-Check: PASSED

- All 4 modified files exist in worktree
- All 3 commits (ede8a30, 07ffa1c, 6519b4a) found in git log
- Acceptance criteria keywords verified in source files
