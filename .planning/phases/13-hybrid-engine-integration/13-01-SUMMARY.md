---
phase: 13-hybrid-engine-integration
plan: 01
subsystem: trading-engine
tags: [hybrid-engine, indicator-filter, two-phase-commit, state-machine, ema, macd]

# Dependency graph
requires:
  - phase: 11-foundation-two-phase-commit
    provides: snapshot/restore infrastructure, HybridEngine shell
  - phase: 12-indicator-filter-layer
    provides: IndicatorFilter with CONFIRM/VETO/OVERRIDE verdicts
provides:
  - Full Propose-Filter-Decide pipeline wired into HybridEngine daily loop
  - degrade_to_cash() method for SELL->CASH without P&L calculation
  - Signal log columns (old_state, proposed, verdict) for diagnosis
  - Indicator column integration via build_indicator_dataframe when filter enabled
affects: [14-validation, 15-advanced-features, run_hybrid_backtest]

# Tech tracking
tech-stack:
  added: []
  patterns: [propose-filter-decide pipeline, diff-based proposal extraction, cash insertion via degradation]

key-files:
  created: []
  modified:
    - strategies/mdm_hybrid/mdm_hybrid_engine.py
    - strategies/mdm_hybrid/position_manager.py

key-decisions:
  - "OVERRIDE always forces Cash regardless of state machine proposal (D-04)"
  - "Cash insertion reuses existing majority-vote from IndicatorFilter (D-08)"
  - "SELL->CASH degradation uses degrade_to_cash() without P&L (D-07)"

patterns-established:
  - "Diff-based proposal: compare snapshot old_state vs post-mutation new_state"
  - "Cash insertion on no-change days: filter evaluates 'confirm current state'"
  - "Signal log columns populated every trading day for Phase 14 diagnosis"

requirements-completed: [HYB-03, HYB-04, HYB-05]

# Metrics
duration: 4min
completed: 2026-03-29
---

# Phase 13 Plan 01: Propose-Filter-Decide Pipeline Summary

**Full Propose-Filter-Decide pipeline wired into HybridEngine two-phase commit block with VETO rollback, OVERRIDE force-Cash, and cash insertion degradation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-29T09:00:54Z
- **Completed:** 2026-03-29T09:05:16Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Wired complete filter pipeline: state machine proposes via mutation, IndicatorFilter evaluates, engine decides (confirm/veto/override/degrade)
- Added degrade_to_cash() to V2PositionManager for SELL->CASH transitions without corrupting P&L records
- Regression preserved: all 6 existing tests pass, filter_enabled=False produces identical output to v2

## Task Commits

Each task was committed atomically:

1. **Task 1: Add degrade_to_cash() method and indicator column integration** - `2b5baec` (feat)
2. **Task 2: Wire Propose-Filter-Decide pipeline into two-phase commit block** - `f4057e8` (feat)

## Files Created/Modified
- `strategies/mdm_hybrid/position_manager.py` - Added degrade_to_cash() method for state degradation without P&L
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` - Full Propose-Filter-Decide pipeline, IndicatorFilter import/init, indicator columns, signal log columns

## Decisions Made
- OVERRIDE forces Cash from any state: uses exit_to_cash for BUY (preserves P&L) and degrade_to_cash for SELL (no P&L)
- Cash insertion runs on every no-change day via filter evaluation of "confirm current state"
- Signal log columns added to main DataFrame (not separate CSV) for simpler Phase 14 access

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all pipeline logic is fully wired with real IndicatorFilter evaluation.

## Next Phase Readiness
- HybridEngine ready for filter-enabled backtesting (Phase 13 Plan 02: backtest script)
- Signal log columns (old_state, proposed, verdict) ready for Phase 14 diagnosis
- filter_enabled=True activates full pipeline; filter_enabled=False preserves v2 regression

---
*Phase: 13-hybrid-engine-integration*
*Completed: 2026-03-29*
