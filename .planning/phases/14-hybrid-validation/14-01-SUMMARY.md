---
phase: 14-hybrid-validation
plan: 01
subsystem: validation
tags: [confusion-matrix, sklearn, signal-comparison, hybrid-engine, held-out-set]

# Dependency graph
requires:
  - phase: 13-hybrid-engine-integration
    provides: HybridEngine with Propose-Filter-Decide pipeline and signal log columns
provides:
  - Hybrid validation pipeline with confusion matrices and v2 baseline comparison
  - Signal diagnosis CSV with filter_effect classification (helped/hurt/neutral)
  - Held-out set discipline (20 chronologically last post-2019 signals)
  - Integration tests for hybrid validation (4 tests)
affects: [14-02 if exists, vn30-adaptation, parameter-tuning]

# Tech tracking
tech-stack:
  added: [scikit-learn confusion_matrix, classification_report]
  patterns: [worktree-aware path resolution, module-scoped fixtures for engine runs]

key-files:
  created:
    - analysis/validate_hybrid.py
    - tests/test_hybrid_validation.py
  modified: []

key-decisions:
  - "Confusion matrix uses inner-join merge on date (952 of 962 signals matched)"
  - "filter_effect classification: helped=filter corrected wrong proposal, hurt=filter overrode correct proposal, neutral=no filter change"
  - "Post-2019 accuracy measured as classification accuracy (true labels vs predicted), not signal-comparator match rate"

patterns-established:
  - "Validation pipeline pattern: load data -> run engines -> build confusion matrices -> build diagnosis -> generate report"
  - "Held-out split: chronological last N post-2019 signals, no randomness"

requirements-completed: [VAL-04]

# Metrics
duration: 8min
completed: 2026-03-29
---

# Phase 14 Plan 01: Hybrid Validation Summary

**Confusion matrix validation of hybrid engine on 952 signals with per-type Buy/Cash/Sell accuracy, v2 baseline delta (+37.4% post-2019), filter effect diagnosis, and 20-signal held-out set**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-29T11:26:45Z
- **Completed:** 2026-03-29T11:35:02Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created 4 integration tests: confusion matrix 3x3, post-2019 vs v2 baseline, signal log diagnosis (952 matched), held-out set discipline (20 signals)
- Built full validation pipeline producing confusion matrices for full/pre2019/post2019 signal subsets
- Generated signal diagnosis CSV with filter_effect classification (38 helped, 91 hurt, 823 neutral)
- Measured: hybrid 44.4% vs v2 7.1% post-2019 accuracy (delta +37.4%)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffold for hybrid validation** - `841a34d` (test)
2. **Task 2: Create hybrid validation script with report generation** - `d378d11` (feat)

## Files Created/Modified
- `tests/test_hybrid_validation.py` - 4 integration tests with module-scoped fixtures for efficient engine execution
- `analysis/validate_hybrid.py` - Full validation pipeline: confusion matrices, v2 baseline, signal diagnosis, held-out split, report generation

## Output Files Generated
- `output/hybrid_validation_report.md` - Markdown report with confusion matrices, v2 baseline comparison, per-type accuracy, held-out results
- `output/hybrid_signal_diagnosis.csv` - Per-signal diagnosis with date, signal, predicted, match, filter_effect columns
- `output/hybrid_confusion_matrix.txt` - Formatted confusion matrices (full and post-2019)

## Decisions Made
- Confusion matrix uses classification accuracy (sklearn) rather than signal-comparator match rate, providing per-type precision/recall/f1
- Filter effect classification distinguishes helped (filter corrected wrong proposal) from hurt (filter overrode correct proposal) from neutral
- Post-2019 accuracy definition: all signals on or after 2019-01-01, not limited to signal-comparator transition matching

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree branch behind main**
- **Found during:** Task 1 (test file creation)
- **Issue:** Worktree branch only had 2 commits, missing core/, strategies/, data/ directories needed for imports
- **Fix:** Merged main into worktree branch to get all required code
- **Files modified:** (merge commit, no manual file changes)
- **Verification:** All imports resolve, tests pass

**2. [Rule 3 - Blocking] Added worktree-aware path resolution to validate_hybrid.py**
- **Found during:** Task 2 (validation script)
- **Issue:** DataLoader resolved data_dir to worktree root where data/NASDAQ.csv doesn't exist
- **Fix:** Added worktree detection pattern (same as run_hybrid_backtest.py) to resolve to main repo root
- **Files modified:** analysis/validate_hybrid.py
- **Verification:** Script runs successfully, loads all data files

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes required for script execution in worktree environment. No scope creep.

## Issues Encountered
None beyond the blocking issues resolved above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Validation pipeline complete, ready for parameter tuning or advanced analysis
- Filter effect analysis shows 91 hurt vs 38 helped -- filter needs tuning
- Held-out set of 20 signals ready for unbiased accuracy measurement after tuning

---
*Phase: 14-hybrid-validation*
*Completed: 2026-03-29*
