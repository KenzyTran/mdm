---
phase: 08-indicator-engine
plan: 01
subsystem: indicators
tags: [ema, sma, macd, heikin-ashi, pandas-ewm, technical-analysis]

# Dependency graph
requires:
  - phase: 07-data-foundation
    provides: "DataLoader with full 1974+ NASDAQ OHLCV data"
provides:
  - "compute_ema, compute_sma, compute_macd, compute_heikin_ashi, compute_heikin_ashi_smoothed, build_indicator_dataframe"
  - "Unit tests (12) and integration tests (7) for all indicator functions"
affects: [08-02-feature-snapshot, 09-rule-discovery]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Module-level pure functions for indicators (no class)", "adjust=False for all EMA computations", "min_periods=window for SMA to avoid partial averages"]

key-files:
  created: [core/indicators.py, tests/test_indicators.py]
  modified: []

key-decisions:
  - "Used module-level functions instead of class (per research recommendation) for stateless indicator transformations"
  - "Two-stage Heikin Ashi Smoothed: EMA(55) smooth then HA compute (simpler variant, Phase 9 can evaluate)"
  - "Smart data_dir finder in tests to handle worktree environments where gitignored CSV data lives in main repo"

patterns-established:
  - "adjust=False on all ewm() calls to match TradingView/StockCharts EMA behavior"
  - "min_periods=window on all rolling() calls to prevent misleading partial-window averages"
  - "Recursive loop for Heikin Ashi open (cannot be vectorized)"

requirements-completed: [IND-01, IND-02, IND-03, IND-04]

# Metrics
duration: 5min
completed: 2026-03-29
---

# Phase 8 Plan 01: Indicator Engine Summary

**Core indicator module with EMA 9/21/55, MA 200, MACD 12-26-9, and Heikin Ashi Smoothed candles using pandas ewm/rolling with adjust=False**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-29T02:45:26Z
- **Completed:** 2026-03-29T02:50:12Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Six pure indicator functions in core/indicators.py: compute_ema, compute_sma, compute_macd, compute_heikin_ashi, compute_heikin_ashi_smoothed, build_indicator_dataframe
- All EMA computations use adjust=False matching TradingView/StockCharts standard
- 12 unit tests on synthetic data + 7 integration tests on real 52-year NASDAQ data all passing
- Integration tests confirm: no NaN after warmup, EMA/MA relationships hold, smoothing reduces volatility

## Task Commits

Each task was committed atomically:

1. **Task 1: Create core/indicators.py with all indicator functions (TDD)**
   - `720d5aa` (test: add failing tests for indicator functions)
   - `703ff1e` (feat: implement core indicator functions)
2. **Task 2: Spot-check indicators against real NASDAQ data** - `f5e5426` (test)

## Files Created/Modified
- `core/indicators.py` - Six pure indicator functions: EMA, SMA, MACD, Heikin Ashi, HA Smoothed, build_indicator_dataframe orchestrator
- `tests/test_indicators.py` - 12 unit tests + 7 integration tests covering all indicator functions

## Decisions Made
- Used module-level functions instead of class for indicators (stateless transformations, per research recommendation)
- Implemented simpler two-stage Heikin Ashi Smoothed (EMA smooth then HA compute) rather than triple-EMA variant; Phase 9 rule discovery will determine which correlates better with signals
- Added smart data directory finder in integration tests to resolve gitignored CSV data across worktree environments

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Integration tests data directory resolution for worktrees**
- **Found during:** Task 2 (integration tests)
- **Issue:** DataLoader uses relative path `data/NASDAQ.csv` but gitignored data files are only in the main repo, not in git worktrees
- **Fix:** Added `_find_data_dir()` static method that checks project root first, then traverses .git file to find main repo for worktree environments
- **Files modified:** tests/test_indicators.py
- **Verification:** All 19 tests pass including integration tests loading real NASDAQ data
- **Committed in:** f5e5426 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix necessary to run integration tests in worktree environment. No scope creep.

## Issues Encountered
None beyond the data directory resolution documented above.

## Known Stubs
None - all indicator functions fully implemented with real computation logic.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- core/indicators.py ready for Plan 02 (feature snapshot extraction at signal dates)
- build_indicator_dataframe provides the full enriched DataFrame that Plan 02 will join with 962 signal dates
- All indicator columns confirmed NaN-free after row 250 (past 200-day warmup)

## Self-Check: PASSED

- core/indicators.py: FOUND
- tests/test_indicators.py: FOUND
- 08-01-SUMMARY.md: FOUND
- Commit 720d5aa: FOUND
- Commit 703ff1e: FOUND
- Commit f5e5426: FOUND

---
*Phase: 08-indicator-engine*
*Completed: 2026-03-29*
