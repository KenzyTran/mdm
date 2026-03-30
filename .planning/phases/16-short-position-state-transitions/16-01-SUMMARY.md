---
phase: 16-short-position-state-transitions
plan: 01
subsystem: trading
tags: [short-position, position-manager, state-machine, pnl]

requires:
  - phase: 13-hybrid-engine-integration
    provides: V2PositionManager with 3-state machine (BUY/CASH/SELL)
provides:
  - V2Position with short_entry_price and short_entry_date fields
  - cover_short() method with P&L calculation (entry - cover) / entry
  - enter_buy() guard preventing direct SELL->BUY transition
  - HybridConfig.short_mode configuration flag
affects: [16-02-PLAN, short-stop-loss, pnl-tracking]

tech-stack:
  added: []
  patterns: [SELL->CASH->BUY two-step transition, short P&L as (entry - cover) / entry]

key-files:
  created:
    - tests/test_short_position.py
  modified:
    - strategies/mdm_hybrid/position_manager.py
    - strategies/mdm_hybrid/config.py
    - tests/test_hybrid_engine.py

key-decisions:
  - "Short P&L formula: (entry - cover) / entry, positive on market drop"
  - "enter_buy() raises ValueError from SELL state to enforce cover_short() first"
  - "process_day SELL+FTD does cover_short then enter_buy in one step"

patterns-established:
  - "SELL->CASH->BUY: Always cover short before buying (no direct SELL->BUY)"
  - "Short fields reset to defaults on cover_short (clean state)"

requirements-completed: [SHORT-01, SHORT-04, TRANS-01]

duration: 33min
completed: 2026-03-30
---

# Phase 16 Plan 01: Short Position Mechanics Summary

**V2Position extended with short entry tracking, cover_short() P&L method, and enter_buy() SELL-state guard in position manager**

## Performance

- **Duration:** 33 min
- **Started:** 2026-03-30T02:32:08Z
- **Completed:** 2026-03-30T03:05:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- V2Position dataclass extended with short_entry_price and short_entry_date fields
- cover_short() method computes short P&L as (entry - cover) / entry and appends SHORT_COVER trade
- enter_buy() guard raises ValueError when called from SELL state, enforcing cover_short() first
- process_day() SELL+FTD path does cover_short then enter_buy (SELL->CASH->BUY)
- HybridConfig.short_mode defaults to 'direct' for VN30 market

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test file for short position mechanics** - `951d0c3` (test) - TDD RED phase
2. **Task 2: Implement V2Position extension, cover_short(), enter_buy() guard, and config flag** - `6fcd818` (feat) - TDD GREEN phase

_TDD cycle: 11 failing tests written first, then all 11 pass after implementation._

## Files Created/Modified
- `tests/test_short_position.py` - 11 tests covering short entry, cover P&L, buy guard, config
- `strategies/mdm_hybrid/position_manager.py` - V2Position short fields, cover_short(), enter_buy() guard, process_day SELL block
- `strategies/mdm_hybrid/config.py` - short_mode field on HybridConfig
- `tests/test_hybrid_engine.py` - Updated regression test for new SELL->BUY action string format

## Decisions Made
- Short P&L formula: (entry - cover) / entry -- positive when market drops (gain for short)
- enter_buy() raises ValueError from SELL to enforce proper cover_short() transition
- process_day SELL+FTD covers and buys in same step (transient CASH per D-09)
- enter_sell() price parameter defaults to 0.0 for backward compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated hybrid regression test for new action string format**
- **Found during:** Task 2 (implementation)
- **Issue:** test_hybrid_matches_v2_on_nasdaq expected bit-for-bit action match, but hybrid now produces "SHORT_COVER + BUY" instead of "BUY ... from SELL"
- **Fix:** Updated test to verify state sequence match exactly, and allow action string differences only at SELL->BUY transitions
- **Files modified:** tests/test_hybrid_engine.py
- **Verification:** All 34 tests pass (11 new + 23 existing)
- **Committed in:** 6fcd818 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Expected regression from changing SELL->BUY behavior. Test updated to validate states match while allowing new action strings.

## Issues Encountered
None

## Known Stubs
None - all methods are fully implemented with real logic.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Position manager short mechanics complete, ready for Plan 02 (engine integration)
- Plan 02 will wire enter_sell with close price, add MA50 breakout cover, and update engine SELL state handling

## Self-Check: PASSED

All files exist. All commits verified (951d0c3, 6fcd818).

---
*Phase: 16-short-position-state-transitions*
*Completed: 2026-03-30*
