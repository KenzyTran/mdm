---
phase: 08-indicator-engine
plan: 02
subsystem: indicators
tags: [feature-snapshot, date-snapping, boolean-features, signal-join, pandas-merge]

# Dependency graph
requires:
  - phase: 08-indicator-engine
    provides: "build_indicator_dataframe with EMA, SMA, MACD, HA Smoothed columns"
  - phase: 07-data-foundation
    provides: "DataLoader with full 1974+ NASDAQ OHLCV, signal_loader with 962 signals"
provides:
  - "snap_to_trading_day function for weekend/holiday signal date resolution"
  - "extract_feature_snapshot function producing 962-row DataFrame with all indicators + 8 boolean features"
affects: [09-rule-discovery]

# Tech tracking
tech-stack:
  added: []
  patterns: ["snap_to_trading_day with backward search for weekend/holiday dates", ".fillna(False).astype(bool) for NaN-safe boolean feature derivation"]

key-files:
  created: [core/feature_snapshot.py, tests/test_feature_snapshot.py]
  modified: []

key-decisions:
  - "Used backward day-by-day search (max_lookback=5) for date snapping rather than pandas merge_asof -- simpler and more explicit"
  - "Preserved original signal dates in output (not snapped dates) so rule discovery sees the published dates"
  - "Used data/signals/nasdaq_signals_full.csv path (actual location) instead of tests/fixtures path referenced in plan"

patterns-established:
  - ".fillna(False).astype(bool) pattern for boolean features derived from columns that may have NaN during warmup"
  - "_find_data_dir() helper reused from test_indicators.py for worktree data resolution"

requirements-completed: [IND-05]

# Metrics
duration: 4min
completed: 2026-03-29
---

# Phase 8 Plan 02: Feature Snapshot Extraction Summary

**Feature snapshot joining 962 signal dates with indicator-enriched NASDAQ data, producing 8 derived boolean features for EMA crossovers, price-vs-MA, and MACD states**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-29T02:54:21Z
- **Completed:** 2026-03-29T02:58:13Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Feature snapshot extraction module with snap_to_trading_day and extract_feature_snapshot functions
- All 962 signal rows represented including 10 weekend dates snapped to prior Friday
- 8 boolean features: ema9_above_ema21, ema21_above_ema55, close_above_ma200, close_above_ema9, close_above_ema21, close_above_ema55, macd_histogram_positive, macd_above_signal
- 17 tests passing: 11 unit tests on synthetic data + 6 integration tests on real 52-year NASDAQ data

## Task Commits

Each task was committed atomically:

1. **Task 1: Create core/feature_snapshot.py with weekend snap and derived features (TDD)**
   - `edfb983` (test: add failing tests for feature snapshot extraction)
   - `bee0c4c` (feat: implement feature snapshot extraction)
2. **Task 2: Integration test with real 962-signal NASDAQ data** - `daa6308` (test)

## Files Created/Modified
- `core/feature_snapshot.py` - snap_to_trading_day and extract_feature_snapshot functions with 8 boolean features
- `tests/test_feature_snapshot.py` - 11 unit tests + 6 integration tests covering all functionality

## Decisions Made
- Used backward day-by-day search for date snapping (max_lookback=5) rather than pandas merge_asof -- more explicit about what happens with weekend dates
- Preserved original signal dates in output DataFrame, not snapped dates, so Phase 9 rule discovery sees the same dates as Dr. K's published history
- Fixed signal fixture path to data/signals/nasdaq_signals_full.csv (actual location) instead of tests/fixtures/ path mentioned in plan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected signal fixture file path**
- **Found during:** Task 2 (integration tests)
- **Issue:** Plan referenced `tests/fixtures/nasdaq_signals_full.csv` but actual file is at `data/signals/nasdaq_signals_full.csv`
- **Fix:** Used correct path in integration test fixture
- **Files modified:** tests/test_feature_snapshot.py
- **Verification:** All 17 tests pass
- **Committed in:** daa6308 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor path correction. No scope creep.

## Issues Encountered
None.

## Known Stubs
None - all functions fully implemented with real computation logic.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- core/feature_snapshot.py ready for Phase 9 rule discovery
- extract_feature_snapshot produces the exact DataFrame needed: 962 rows x (all indicators + 8 boolean features)
- All indicator columns confirmed NaN-free after 1975-06-01 warmup
- Phase 08 indicator engine fully complete (Plans 01 + 02)

## Self-Check: PASSED

- core/feature_snapshot.py: FOUND
- tests/test_feature_snapshot.py: FOUND
- 08-02-SUMMARY.md: FOUND
- Commit edfb983: FOUND
- Commit bee0c4c: FOUND
- Commit daa6308: FOUND

---
*Phase: 08-indicator-engine*
*Completed: 2026-03-29*
