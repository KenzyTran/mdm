---
phase: 04-mdm-v2-engine
plan: 01
subsystem: trading-engine
tags: [mdm, state-machine, backtesting, signal-comparator, dataclass]

# Dependency graph
requires:
  - phase: 02-codebase-organization
    provides: strategies/mdm_classic/ package structure
  - phase: 03-signal-divergence-analysis
    provides: core/signal_comparator.py with extract_model_signals and compare_signals
provides:
  - strategies/mdm_v2/ package with MDMV2Config, V2PositionManager, MDMV2Engine
  - 3-state machine (BUY/CASH/SELL) replacing classic 4-state (HOLDING/CASH/WAITING_SELL/SHORT)
  - Signal comparator compatibility via STATE_TO_SIGNAL mapping updates
affects: [04-02-hypothesis-testing, 05-performance, 06-vn30-adaptation]

# Tech tracking
tech-stack:
  added: []
  patterns: [3-state-machine, config-driven-thresholds, mdmconfig-alias-for-copied-modules]

key-files:
  created:
    - strategies/mdm_v2/__init__.py
    - strategies/mdm_v2/config.py
    - strategies/mdm_v2/position_manager.py
    - strategies/mdm_v2/mdm_v2_engine.py
    - strategies/mdm_v2/stop_loss.py
    - strategies/mdm_v2/distribution_day.py
    - strategies/mdm_v2/rally_attempt.py
    - strategies/mdm_v2/ftd_signal.py
    - strategies/mdm_v2/indicators.py
    - tests/test_mdm_v2_config.py
    - tests/test_mdm_v2_states.py
    - tests/test_mdm_v2_engine.py
  modified:
    - core/signal_comparator.py

key-decisions:
  - "Added MDMConfig alias in v2 config.py so copied modules (distribution_day, rally_attempt, ftd_signal) work without import changes"
  - "V2 stop_loss removes all SHORT-related logic and check_trigger_break method"
  - "SELL state is persistent -- stays in SELL until FTD triggers SELL->BUY transition"
  - "BUY->CASH on stop loss (not BUY->SELL) to preserve Cash as intermediate state"

patterns-established:
  - "MDMConfig alias pattern: v2 config.py exports MDMConfig = MDMV2Config for backward compat with copied modules"
  - "V2 state values use BUY/CASH/SELL strings (not HOLDING/SHORT/WAITING_SELL)"
  - "Worktree data path resolution: walk up to find .claude parent for main repo data access in tests"

requirements-completed: [MDM-01, MDM-02]

# Metrics
duration: 8min
completed: 2026-03-28
---

# Phase 04 Plan 01: MDM V2 Engine Foundation Summary

**3-state MDM v2 engine (BUY/CASH/SELL) with parameterized MDMV2Config and full signal comparator pipeline compatibility**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-28T05:18:26Z
- **Completed:** 2026-03-28T05:26:07Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- MDMV2Config dataclass with all classic parameters plus v2-specific Cash/Sell triggers (dd_cash_threshold, ma10_cash_consecutive, cash_deterioration_days) and hypothesis metadata
- V2PositionManager implements 3-state machine with BUY/CASH/SELL -- no SHORT or WAITING_SELL states
- MDMV2Engine runs on NASDAQ data and produces results compatible with extract_model_signals() and compare_signals()
- Full end-to-end pipeline verified: engine -> extract signals -> compare against published NASDAQ signals

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MDMV2Config and 3-state position manager with tests**
   - `b000fee` (test: failing tests for config and states)
   - `9f410ce` (feat: implement MDMV2Config and V2PositionManager)
2. **Task 2: Build MDMV2Engine and verify signal comparator compatibility**
   - `e774c23` (test: failing tests for engine and comparator)
   - `118b069` (feat: implement engine, copy modules, update comparator)

_TDD tasks have red/green commits (test then feat)_

## Files Created/Modified
- `strategies/mdm_v2/config.py` - MDMV2Config dataclass with v2 parameters + MDMConfig alias
- `strategies/mdm_v2/position_manager.py` - V2MarketState enum and V2PositionManager with 3-state transitions
- `strategies/mdm_v2/mdm_v2_engine.py` - Main v2 engine orchestrating daily processing
- `strategies/mdm_v2/stop_loss.py` - Long-only stop loss (no SHORT logic)
- `strategies/mdm_v2/distribution_day.py` - Copied from classic (unchanged logic)
- `strategies/mdm_v2/rally_attempt.py` - Copied from classic (unchanged logic)
- `strategies/mdm_v2/ftd_signal.py` - Copied from classic (unchanged logic)
- `strategies/mdm_v2/indicators.py` - Copied from classic (unchanged logic)
- `strategies/mdm_v2/__init__.py` - Package exports
- `core/signal_comparator.py` - Added BUY->Buy and SELL->Sell to STATE_TO_SIGNAL mapping
- `tests/test_mdm_v2_config.py` - 15 tests for config defaults, validation, custom values
- `tests/test_mdm_v2_states.py` - 14 tests for state transitions
- `tests/test_mdm_v2_engine.py` - 9 tests for engine output, comparator compat, integration

## Decisions Made
- Added `MDMConfig = MDMV2Config` alias in config.py so copied modules (distribution_day, rally_attempt, ftd_signal) can import `MDMConfig` without modification
- Removed `check_trigger_break()` method from v2 stop_loss since WAITING_SELL state no longer exists
- SELL state is persistent per research resolution -- only FTD can exit SELL to BUY
- Stop loss in BUY state transitions to CASH (not SELL) preserving Cash as the intermediate state

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added MDMConfig alias for copied module compatibility**
- **Found during:** Task 2 (copying classic modules)
- **Issue:** Copied modules import `from .config import MDMConfig` but v2 config only exports `MDMV2Config`
- **Fix:** Added `MDMConfig = MDMV2Config` alias at bottom of config.py
- **Files modified:** strategies/mdm_v2/config.py
- **Verification:** All copied modules import successfully, tests pass
- **Committed in:** 118b069

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Single alias addition to avoid modifying all copied files. No scope creep.

## Issues Encountered
None

## Known Stubs
None - all modules are fully wired with real logic.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V2 engine foundation complete, ready for hypothesis testing (Plan 02)
- MDMV2Config parameterization enables parameter sweep and A/B testing
- Signal comparator pipeline verified end-to-end

## Self-Check: PASSED

All 12 created files verified present. All 4 commit hashes verified in git log.

---
*Phase: 04-mdm-v2-engine*
*Completed: 2026-03-28*
