---
phase: 20-sell-acceleration
plan: 01
subsystem: trading-engine
tags: [sell-signal, acceleration-gate, momentum, distribution-days, roc]

# Dependency graph
requires:
  - phase: 19-liquidity-filter
    provides: QE floor suppress_sell pattern in V2 engine and position manager
provides:
  - SellAccelerationGate module with 3 acceleration conditions
  - MDMV2Config with sell acceleration fields
  - Engine wiring for acceleration gate between QE floor and process_day
  - Position manager deferred SELL action strings
affects: [20-sell-acceleration plan 02, integration-phase]

# Tech tracking
tech-stack:
  added: []
  patterns: [gate-pattern-for-sell-transitions, or-logic-acceleration-conditions]

key-files:
  created:
    - strategies/mdm_v2/sell_acceleration.py
  modified:
    - strategies/mdm_v2/config.py
    - strategies/mdm_v2/mdm_v2_engine.py
    - strategies/mdm_v2/position_manager.py

key-decisions:
  - "Acceleration gate uses OR logic across 3 conditions (ROC, DD cluster, volume-confirmed MA50)"
  - "Gate defaults to enabled=True with backward-compat: disabled returns True (allow all SELLs)"
  - "suppress_sell (QE floor) takes priority over acceleration_met check"
  - "DD clustering approximates trading days via calendar days * 1.5"

patterns-established:
  - "Gate pattern: separate module with check() returning bool, wired between QE floor and process_day"
  - "Deferred action strings: 'SELL deferred: no acceleration (reason)' for debugging"

requirements-completed: [SELL-01]

# Metrics
duration: 2min
completed: 2026-03-31
---

# Phase 20 Plan 01: SELL Acceleration Gate Summary

**SellAccelerationGate module with ROC/DD-clustering/volume-MA50 conditions gating CASH->SELL transitions in V2 engine**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-31T00:30:46Z
- **Completed:** 2026-03-31T00:32:53Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created SellAccelerationGate class with 3 OR-logic acceleration conditions (price ROC below -4%, DD clustering 3-in-5, volume-confirmed MA50 breakdown)
- Added 5 new config fields to MDMV2Config with validation assertions
- Wired acceleration gate into V2 engine run loop between QE floor and process_day call
- Updated position manager to defer SELL when acceleration not met (separate from QE floor suppression)
- Added acceleration_met column to results DataFrame for debugging

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SellAccelerationGate module and update MDMV2Config** - `2314d64` (feat)
2. **Task 2: Wire acceleration gate into V2 engine and position manager** - `3f3da7c` (feat)

## Files Created/Modified
- `strategies/mdm_v2/sell_acceleration.py` - SellAccelerationGate class with check() and 3 private condition methods
- `strategies/mdm_v2/config.py` - 5 new fields (sell_acceleration_enabled, roc_threshold, roc_window, dd_cluster_count, dd_cluster_window) with validation
- `strategies/mdm_v2/mdm_v2_engine.py` - Import, instantiate, compute acceleration_met, pass to process_day, add DataFrame column
- `strategies/mdm_v2/position_manager.py` - New acceleration_met parameter, deferred SELL action strings for both triggers

## Decisions Made
- Acceleration gate uses OR logic: any single condition (ROC, DD cluster, volume-MA50) is sufficient to allow SELL
- Gate disabled returns True for backward compatibility (all SELLs pass through)
- suppress_sell (QE floor) takes priority over acceleration check in position manager
- DD clustering uses calendar days * 1.5 to approximate trading day windows (handles weekends)
- ROC uses closes_history.iloc[-(roc_window+1)] to avoid look-ahead bias

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SellAccelerationGate module ready for plan 02 (validation and backtest comparison)
- acceleration_met column in results DataFrame enables analysis of deferred vs fired SELLs
- Default enabled=True means new runs will use the gate; set sell_acceleration_enabled=False for baseline comparison

---
*Phase: 20-sell-acceleration*
*Completed: 2026-03-31*
