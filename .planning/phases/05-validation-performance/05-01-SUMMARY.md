---
phase: 05-validation-performance
plan: 01
subsystem: testing
tags: [performance-metrics, equity-curve, sharpe-ratio, drawdown, tdd]

# Dependency graph
requires:
  - phase: 04-mdm-v2-strategy
    provides: MDMV2Engine with state column (BUY/CASH/SELL) and trade dicts
provides:
  - V2PerformanceAnalyzer class computing equity curve, drawdown, Sharpe, win rate, returns
  - check_degradation() function for train/held-out match rate validation
affects: [05-02-validation-script, 06-vn30-adaptation]

# Tech tracking
tech-stack:
  added: []
  patterns: [previous-day-state-equity-capture, relative-degradation-threshold]

key-files:
  created:
    - strategies/mdm_v2/performance.py
    - tests/test_v2_performance.py
  modified: []

key-decisions:
  - "Previous-day state determines today's return capture (BUY day entry does not capture that day's return)"
  - "Sharpe uses 0% risk-free rate with sqrt(252) annualization per D-06"
  - "Win rate counts only CASH_EXIT trades (v2 trade type), not SELL_SIGNAL"
  - "check_degradation is standalone function (not method) for easy import by Plan 02"

patterns-established:
  - "Equity curve: prev-day BUY state captures today's close/prev_close return"
  - "Degradation formula: (train - heldout) / train, pass if <= threshold"

requirements-completed: [PERF-01, PERF-03]

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 05 Plan 01: V2 Performance Analyzer Summary

**V2PerformanceAnalyzer with daily equity curve (prev-day state capture), max drawdown, Sharpe ratio, win rate, and check_degradation for train/held-out validation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-28T08:42:48Z
- **Completed:** 2026-03-28T08:46:05Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- V2PerformanceAnalyzer class with all PERF-01 metrics: equity curve, max drawdown, Sharpe ratio, win rate, total return, annualized return, drawdown series
- check_degradation() standalone function for PERF-03 train/held-out match rate validation
- 16 unit tests covering all metrics plus edge cases (constant equity, empty trades, SELL state, zero train rate)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `9d4e57e` (test)
2. **Task 1 GREEN: Implementation** - `21a9296` (feat)

_TDD task with separate RED and GREEN commits._

## Files Created/Modified
- `strategies/mdm_v2/performance.py` - V2PerformanceAnalyzer class with all PERF-01 metrics and check_degradation function
- `tests/test_v2_performance.py` - 16 unit tests covering equity curve, drawdown, Sharpe, win rate, returns, and PERF-03 degradation logic

## Decisions Made
- Previous-day state determines return capture: when state[i-1] is BUY, equity[i] captures close[i]/close[i-1]; otherwise equity is flat
- Sharpe ratio returns 0.0 when daily returns have zero standard deviation (constant equity)
- Win rate only considers CASH_EXIT trade type, ignoring BUY entries and SELL_SIGNAL events
- check_degradation handles zero train_rate edge case by returning (0.0, True)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V2PerformanceAnalyzer ready for consumption by validation script (Plan 02)
- check_degradation function importable for PERF-03 train/held-out degradation checking
- All tests passing, no stubs or placeholders

## Self-Check: PASSED

- All created files exist on disk
- All commit hashes found in git log
- 16/16 tests pass

---
*Phase: 05-validation-performance*
*Completed: 2026-03-28*
