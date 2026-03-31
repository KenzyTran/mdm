---
phase: 21-buy-selectivity
plan: 01
subsystem: trading-strategy
tags: [buy-filter, confirmation-window, ma10-ma50, ftd, distribution-day, mdm-v2]

# Dependency graph
requires:
  - phase: 20-sell-acceleration
    provides: SellAccelerationGate pattern, MDMV2Config with acceleration fields
provides:
  - BuyFilter module for MA10/MA50 FTD rejection gate
  - BuyConfirmation module for post-FTD 3-day confirmation window
  - MDMV2Config with buy_filter_enabled, buy_confirmation_enabled fields
  - Engine integration with side-effect-free DD checking for confirmation
affects: [21-buy-selectivity-02, integration-phase, dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: [stateless-filter-gate, stateful-confirmation-window, side-effect-free-dd-check]

key-files:
  created:
    - strategies/mdm_v2/buy_filter.py
    - strategies/mdm_v2/buy_confirmation.py
    - tests/test_buy_selectivity.py
  modified:
    - strategies/mdm_v2/config.py
    - strategies/mdm_v2/mdm_v2_engine.py

key-decisions:
  - "DD check during confirmation window uses is_distribution_day_type1/type2 directly (side-effect-free) instead of check_distribution_day (which appends to dd_history)"
  - "Cancellation checked BEFORE completion in confirmation window (per pitfall 4) to prevent DD on final day from being ignored"
  - "MA50/52WEEK breakouts supersede pending confirmation by resetting the confirmation state"

patterns-established:
  - "Side-effect-free DD detection: use is_distribution_day_type1/type2 when DD check must not modify state"
  - "Buy gate pattern: stateless filter -> stateful confirmation -> engine integration"

requirements-completed: [BUY-01, BUY-02]

# Metrics
duration: 23min
completed: 2026-03-31
---

# Phase 21 Plan 01: Buy Selectivity Summary

**MA10/MA50 trend filter rejects weak FTDs, 3-day confirmation window with DD cancellation gates BUY entries in V2 engine**

## Performance

- **Duration:** 23 min
- **Started:** 2026-03-31T01:57:31Z
- **Completed:** 2026-03-31T02:20:32Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- BuyFilter rejects FTD when MA10 < MA50, allows MA50/52-week breakout bypass
- BuyConfirmation requires 3 clean days post-FTD, cancels on 2+ DD, entry at day-3 close price
- Engine integrates both gates between FTD detection and process_day with side-effect-free DD checking
- 25 tests passing (18 unit + 7 integration), no regression in 66 V2 existing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BuyFilter, BuyConfirmation modules, config fields, and test scaffold** - `16fab5d` (test: RED phase) + `e5d869d` (feat: GREEN phase)
2. **Task 2: Wire BuyFilter and BuyConfirmation into MDMV2Engine** - `a88797b` (feat)

_Note: Task 1 used TDD with separate RED/GREEN commits_

## Files Created/Modified
- `strategies/mdm_v2/buy_filter.py` - Stateless MA10/MA50 FTD rejection gate (BuyFilter class)
- `strategies/mdm_v2/buy_confirmation.py` - Stateful post-FTD 3-day confirmation window tracker (BuyConfirmation class)
- `strategies/mdm_v2/config.py` - Added buy_filter_enabled, buy_confirmation_enabled, confirmation_window_days, confirmation_max_dd
- `strategies/mdm_v2/mdm_v2_engine.py` - Wired BuyFilter/BuyConfirmation into run loop with buy_rejected/buy_pending/buy_confirmed columns
- `tests/test_buy_selectivity.py` - 25 tests: TestBuyFilter (7), TestBuyConfirmation (8), TestConfigBuySelectivity (3), TestEngineIntegration (7)

## Decisions Made
- DD check during confirmation uses side-effect-free methods (is_distribution_day_type1/type2) to avoid polluting dd_history
- Cancellation checked before completion on each day (per pitfall 4) to prevent final-day DD from being ignored
- MA50/52WEEK breakouts supersede pending confirmation by resetting confirmation state
- Integration test searches multiple seeds to find classic FTD scenarios (most random data produces breakout-type signals)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Integration test for confirmation delay initially failed because random data (seed=12) produced only MA50/52WEEK breakout BUYs (no classic FTDs). Fixed by searching multiple seeds to find data with classic FTD scenarios.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all modules are fully wired with real data sources.

## Next Phase Readiness
- BuyFilter and BuyConfirmation are ready for plan 02 (backtest validation and parameter tuning)
- Both gates default ON, backward-compatible with buy_filter_enabled=False, buy_confirmation_enabled=False
- Engine output includes buy_rejected, buy_pending, buy_confirmed columns for analysis

---
*Phase: 21-buy-selectivity*
*Completed: 2026-03-31*
