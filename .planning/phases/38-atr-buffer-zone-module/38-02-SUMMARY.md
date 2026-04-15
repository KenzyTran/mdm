---
phase: 38-atr-buffer-zone-module
plan: 02
subsystem: strategy
tags: [atr, buffer-zone, position-manager, mdm-hybrid, engine-integration, feature-gate]

# Dependency graph
requires:
  - phase: 38-atr-buffer-zone-module
    plan: 01
    provides: MDMV2Config atr_buffer_* fields + Indicators.add_violation_threshold_column()
provides:
  - V2Position.atr_buf_below_count field for m-day streak counting
  - process_day() violation_threshold kwarg and branched SELL logic (enabled/disabled)
  - HybridEngine pipeline hook calling add_violation_threshold_column when enabled
  - violation_threshold_val passed to process_day() each iteration
affects:
  - 38-03-regression-test
  - 40-atr-grid-search

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Feature-gate branch in process_day: getattr(config, 'atr_buffer_enabled', False) guards new code path"
    - "m-day streak counter in position dataclass: atr_buf_below_count increments/resets daily in CASH state"
    - "Warm-up safety via None-check: violation_threshold=None during indicator warm-up prevents false SELL"

key-files:
  created: []
  modified:
    - strategies/mdm_hybrid/position_manager.py
    - strategies/mdm_hybrid/mdm_hybrid_engine.py

key-decisions:
  - "Pre-existing test_hybrid_matches_v2_on_nasdaq failure (82.68% < 95%) confirmed pre-dates Plan 02 changes (verified via git stash); logged to deferred-items, not fixed"
  - "Two atr_buffer_enabled checks in engine are correct: one guards precompute, one guards per-row read — plan acceptance criteria note of '1 hit' referred only to pipeline guard"
  - "violation_threshold=None passed when column absent (warm-up safety); process_day does not fire SELL when violation_threshold is None"

patterns-established:
  - "ATR buffer streak reset: atr_buf_below_count resets to 0 on new V2Position (enter_sell creates fresh V2Position, so counter auto-resets)"
  - "Row column check: use 'col' in row.index (not row.get()) for pd.Series from iterrows"

requirements-completed: [ATR-02, ATR-03]

# Metrics
duration: 11min
completed: 2026-04-15
---

# Phase 38 Plan 02: ATR Buffer Zone Engine Integration Summary

**HybridEngine pipeline wired with conditional add_violation_threshold_column() and V2PositionManager CASH->SELL trigger branched on atr_buffer_enabled: enabled path requires m consecutive days below violation_threshold; disabled path is byte-identical to v6.0**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-04-15T08:37:13Z
- **Completed:** 2026-04-15T08:48:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `atr_buf_below_count: int = 0` to V2Position dataclass for streak tracking
- Added `violation_threshold: float = None` kwarg to `process_day()` signature
- Branched CASH->SELL logic: when `atr_buffer_enabled=True`, uses m-day streak check; when `False`, original MA50 breakdown is byte-identical
- Inserted conditional `add_violation_threshold_column()` call in HybridEngine.run() indicator pipeline (gated on `atr_buffer_enabled`)
- Per-row `violation_threshold_val` extracted and passed to `process_day()` on every iteration
- All 14 existing `test_mdm_v2_states.py` tests pass; integration smoke tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add atr_buf_below_count to V2Position and wire streak logic in process_day** - `f80394f` (feat)
2. **Task 2: Wire add_violation_threshold_column into HybridEngine indicator pipeline** - `d322a17` (feat)

## Files Created/Modified

- `strategies/mdm_hybrid/position_manager.py` - atr_buf_below_count field + violation_threshold kwarg + branched CASH->SELL logic
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` - conditional add_violation_threshold_column() in pipeline + per-row extraction + kwarg pass to process_day()

## Decisions Made

- When `atr_buffer_enabled=False`, the disabled branch executes `if close < ma50: enter_sell(...)` which is byte-identical to original v6.0 behavior (ATR-04 protected)
- `violation_threshold=None` during ATR warm-up (first `period` rows) safely prevents any false SELL triggers — the enabled branch only fires when both `violation_threshold is not None` AND `atr_buf_below_count >= m`
- Pre-existing `test_hybrid_matches_v2_on_nasdaq` failure (82.68% vs 95% threshold) was confirmed to pre-date all Plan 02 changes via git stash; logged to deferred-items.md

## Deviations from Plan

None - plan executed exactly as written. The pre-existing test failure is out-of-scope per deviation rules (not caused by current task's changes).

### Deferred Issues

**Pre-existing test failure: test_hybrid_matches_v2_on_nasdaq**
- Test asserts Hybrid BUY state matches V2 BUY state >95% of time; currently 82.68%
- Pre-dates Phase 38 Plan 02 entirely (confirmed via git stash before applying changes)
- Logged to deferred-items.md; not in scope of Phase 38

## Issues Encountered

None — plan executed cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 (regression test) can proceed: HybridEngine now fully wired with ATR buffer, feature gate operational
- Key contract verified: `atr_buffer_enabled=False` produces no `violation_threshold` column; `=True` produces column and passes it to position manager
- `atr_buf_below_count` resets automatically on state transitions (new V2Position created on enter_sell/exit_to_cash/cover_short)

---
*Phase: 38-atr-buffer-zone-module*
*Completed: 2026-04-15*
