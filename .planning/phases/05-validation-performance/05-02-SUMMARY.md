---
phase: 05-validation-performance
plan: 02
subsystem: analysis
tags: [validation, performance, matplotlib, jupyter, signal-matching, equity-curve]

# Dependency graph
requires:
  - phase: 05-01
    provides: V2PerformanceAnalyzer, check_degradation, equity curve and drawdown metrics
  - phase: 04-02
    provides: MDMV2Engine, MDMV2Config, parameter sweep infrastructure
  - phase: 03-02
    provides: signal_comparator module with extract_model_signals, compare_signals
provides:
  - Full validation script with train/held-out match rate analysis
  - Three-way performance comparison (V2 vs buy-and-hold vs classic)
  - Multi-panel dashboard PNG generation
  - Interactive Jupyter notebook for validation exploration
  - CSV and text summary output generation
affects: [06-vn30-adaptation]

# Tech tracking
tech-stack:
  added: []
  patterns: [multi-panel matplotlib dashboard, period-filtered performance comparison, automated sweep config loading]

key-files:
  created:
    - analysis/validate_v2.py
    - notebooks/v2_validation.ipynb
  modified: []

key-decisions:
  - "Classic engine equity uses HOLDING/WAITING_SELL states as invested, CASH/SHORT as flat"
  - "Buy-and-hold Sharpe computed from daily close returns with sqrt(252) annualization"
  - "Published signal markers use large triangles/circles, model signals use smaller diamonds/squares for visual separation"

patterns-established:
  - "Period-filtered analysis: warm-up from 2017, metrics computed only on 2019+ analysis period"
  - "Three-period comparison pattern: train (2019-2022), held-out (2023-2026), full (2019-2026)"

requirements-completed: [PERF-02, PERF-03]

# Metrics
duration: 4min
completed: 2026-03-28
---

# Phase 5 Plan 2: Validation Script & Dashboard Summary

**Full validation pipeline with train/held-out match rates, three-way performance comparison, multi-panel dashboard, and interactive Jupyter notebook**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T08:49:54Z
- **Completed:** 2026-03-28T08:54:21Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created 645-line validation script that auto-loads best sweep config, runs both engines, and produces all outputs
- Built three-way comparison table across three time periods with V2 vs buy-and-hold vs MDM classic metrics
- Generated multi-panel dashboard with equity curves, drawdown, and signal overlay on price chart
- Created 14-cell Jupyter notebook for interactive exploration of all validation outputs

## Task Commits

Each task was committed atomically:

1. **Task 1: Create validation script with all analysis logic** - `48f74f8` (feat)
2. **Task 2: Create interactive Jupyter notebook** - `b93e28e` (feat)

## Files Created/Modified
- `analysis/validate_v2.py` - Full validation pipeline: config loading, match rates, comparison table, dashboard chart, CSV/text output
- `notebooks/v2_validation.ipynb` - Interactive 14-cell notebook with all validation steps and held-out exploration example

## Decisions Made
- Classic engine equity curve maps HOLDING and WAITING_SELL states to invested (capturing returns), CASH and SHORT to flat
- Buy-and-hold Sharpe ratio uses same formula as V2 (mean/std * sqrt(252)) for fair comparison
- Signal markers in dashboard use different shapes/sizes for published vs model signals to avoid visual confusion

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Validation script ready to run once parameter sweep results exist at output/sweep_results.csv
- All Phase 5 analysis infrastructure complete, ready for Phase 6 VN30 adaptation
- Dashboard PNG, CSV, and text summary auto-generated in output/ directory

---
*Phase: 05-validation-performance*
*Completed: 2026-03-28*
