---
phase: 17-stop-loss-risk-management
plan: 01
subsystem: trading-strategy
tags: [stop-loss, atr, volatility, risk-management, tdd]

# Dependency graph
requires:
  - phase: 16-short-position-state-transitions
    provides: StopLossChecker and 3-state position manager
provides:
  - 1.5% default long stop loss (was 2.5%)
  - ATR indicator computation (Indicators.add_atr_column)
  - Volatility-adaptive stop loss scaling with clamping
  - ATR wired into hybrid engine data pipeline
affects: [17-02, backtesting, optimization]

# Tech tracking
tech-stack:
  added: []
  patterns: [volatility-adaptive-risk, atr-based-scaling]

key-files:
  created:
    - tests/test_stop_loss.py
  modified:
    - strategies/mdm_hybrid/config.py
    - strategies/mdm_hybrid/indicators.py
    - strategies/mdm_hybrid/stop_loss.py
    - strategies/mdm_hybrid/mdm_hybrid_engine.py
    - strategies/mdm_v2/config.py
    - tests/test_mdm_v2_config.py

key-decisions:
  - "ATR uses rolling mean (not EMA) for simplicity and consistency with existing MA indicators"
  - "Volatility-adaptive scaling clamped to [0.5x, 2.5x] of base stop loss to prevent extreme values"
  - "Updated mdm_v2 config stop_loss_pct to 0.015 to stay in sync with hybrid config (prevent config drift)"

patterns-established:
  - "Volatility-adaptive pattern: base_value * (current_atr / baseline_atr) with min/max clamping"
  - "ATR computation uses min_periods=1 for rolling window to avoid NaN at start of series"

requirements-completed: [RISK-01, RISK-02]

# Metrics
duration: 48min
completed: 2026-03-30
---

# Phase 17 Plan 01: Stop Loss & ATR Volatility-Adaptive Scaling Summary

**Reduced long stop loss from 2.5% to 1.5% per Dr. K rules and added ATR-based volatility-adaptive scaling with [0.5x, 2.5x] clamping**

## Performance

- **Duration:** 48 min
- **Started:** 2026-03-30T05:43:31Z
- **Completed:** 2026-03-30T06:31:36Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Changed default stop_loss_pct from 0.025 (2.5%) to 0.015 (1.5%) aligning with Dr. K's documented rules
- Added ATR indicator computation (true range + rolling mean) to Indicators class
- Implemented volatility-adaptive stop loss: scales by ATR/baseline ratio, clamped to [0.5x, 2.5x]
- Wired ATR computation and baseline into hybrid engine data pipeline
- 11 unit tests covering all stop loss scenarios (TDD red-green flow)

## Task Commits

Each task was committed atomically:

1. **Task 1: Config, ATR indicator, and volatility-adaptive stop loss with tests**
   - `7b9746b` (test) - failing tests for 1.5% stop loss and ATR scaling
   - `e791b11` (feat) - implement 1.5% stop loss with volatility-adaptive ATR scaling
2. **Task 2: Wire ATR into engine and validate existing tests pass** - `6aef8a7` (feat)

## Files Created/Modified
- `tests/test_stop_loss.py` - 11 tests for stop loss config, ATR, and volatility-adaptive scaling
- `strategies/mdm_hybrid/config.py` - MDMV2Config with stop_loss_pct=0.015, ATR params, volatility flags
- `strategies/mdm_hybrid/indicators.py` - Indicators.add_atr_column() static method
- `strategies/mdm_hybrid/stop_loss.py` - StopLossChecker._get_effective_stop_pct() and updated check()
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` - ATR computation in run() and ATR pass-through to check()
- `strategies/mdm_v2/config.py` - stop_loss_pct synced to 0.015
- `tests/test_mdm_v2_config.py` - Updated expected default to 0.015

## Decisions Made
- ATR uses simple rolling mean (not EMA) for consistency with existing indicator patterns
- Volatility-adaptive scaling clamped to [0.5x, 2.5x] to prevent extreme stops
- Updated mdm_v2 config to match hybrid config (0.015) to prevent config drift test failure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Synced mdm_v2 config stop_loss_pct to 0.015**
- **Found during:** Task 2 (engine wiring and test validation)
- **Issue:** `test_hybrid_config_v2_defaults_match` failed because `strategies/mdm_v2/config.py` still had 0.025 while hybrid had 0.015
- **Fix:** Updated `strategies/mdm_v2/config.py` stop_loss_pct to 0.015 and updated `tests/test_mdm_v2_config.py` expected value
- **Files modified:** strategies/mdm_v2/config.py, tests/test_mdm_v2_config.py
- **Verification:** Config drift test passes
- **Committed in:** 6aef8a7 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Config sync was necessary to prevent test regression. No scope creep.

## Issues Encountered
- Worktree was behind main (on commit b9910a6), required git merge to get strategies/ directory
- Engine tests are very slow (~20 min for full suite) due to processing large datasets; ran targeted tests to verify

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Stop loss infrastructure ready for Phase 17 Plan 02 (short stop loss and DD5 high tracking)
- ATR column available in engine output DataFrame for any future volatility-based features

---
*Phase: 17-stop-loss-risk-management*
*Completed: 2026-03-30*
