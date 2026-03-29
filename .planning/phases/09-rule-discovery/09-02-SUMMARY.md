---
phase: 09-rule-discovery
plan: 02
subsystem: analysis
tags: [scikit-learn, decision-tree, rule-extraction, era-comparison, machine-learning]

# Dependency graph
requires:
  - phase: 09-rule-discovery/01
    provides: Era-aware statistical profiling functions and feature constants
provides:
  - Decision tree training with balanced class weights and cross-validation
  - Human-readable rule extraction from trained trees
  - Full rule discovery report with era comparison
  - Generated output/rule_discovery_report.md
affects: [validation, backtesting, mdm-engine]

# Tech tracking
tech-stack:
  added: [scikit-learn DecisionTreeClassifier, cross_val_score, export_text]
  patterns: [era-aware ML training, boolean feature simplification in rule extraction, weighted vs actual sample count handling]

key-files:
  created: [output/rule_discovery_report.md]
  modified: [analysis/rule_discovery.py]

key-decisions:
  - "Used n_node_samples for actual counts in rules instead of weighted counts from class_weight='balanced'"
  - "Boolean threshold detection (0.4-0.6 range) for simplified rule output"
  - "CV folds capped at min class count to prevent missing-class fold errors"

patterns-established:
  - "Era-aware ML: train separate trees per era, compare feature importances"
  - "Rule format: '{Signal} when {conditions}: {confidence}% confidence (N={count})'"

requirements-completed: [DISC-02, DISC-03, DISC-04]

# Metrics
duration: 4min
completed: 2026-03-29
---

# Phase 9 Plan 02: Rule Discovery Report Summary

**Decision tree rule extraction with era comparison revealing structural shift from close_above_ema9 (pre-2019) to close_above_ema55 (post-2019) as dominant feature**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-29T04:44:38Z
- **Completed:** 2026-03-29T04:48:43Z
- **Tasks:** 2
- **Files modified:** 2 (+ 1 generated report)

## Accomplishments
- Implemented train_era_tree with balanced class weights and adaptive cross-validation (pre-2019: 53.9% CV, post-2019: 58.9% CV, both above 34% chance)
- Implemented extract_rules with recursive tree walk, boolean simplification, and proper actual-sample-count reporting
- Generated full rule discovery report with statistical profiles, decision trees, extracted rules, and era comparison
- Era comparison reveals structural shift: close_above_ema9 (70.2% importance pre-2019) replaced by close_above_ema55 (68.7% importance post-2019)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement decision tree training and rule extraction** - `a5cf3a4` (feat)
2. **Task 2: Generate full rule discovery report with era comparison** - `880dc4e` (feat)

## Files Created/Modified
- `analysis/rule_discovery.py` - Added train_era_tree, extract_rules, generate_full_report functions
- `output/rule_discovery_report.md` - Generated markdown report with full analysis
- `tests/test_rule_discovery.py` - All 5 tests passing (imported from wave 1)

## Decisions Made
- Used `tree_.n_node_samples[node]` for actual sample counts in rules instead of weighted counts from `class_weight='balanced'` (weighted counts gave misleading N=0/N=1 values)
- Boolean threshold detection range 0.4-0.6 for simplified "feature" / "NOT feature" output
- CV folds capped at minimum class count to prevent folds with missing classes (critical for post-2019 Sell=15)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed weighted vs actual sample counts in extract_rules**
- **Found during:** Task 2 (report generation)
- **Issue:** class_weight='balanced' causes tree_.value to contain weighted counts, not actual sample counts. Rules showed N=0 and N=1 for leaves with hundreds of actual samples.
- **Fix:** Used tree_.n_node_samples[node] for the N count while keeping weighted values for confidence calculation
- **Files modified:** analysis/rule_discovery.py
- **Verification:** Report now shows correct N values (e.g., N=24 instead of N=1)
- **Committed in:** 880dc4e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Bug fix essential for meaningful rule output. No scope creep.

## Issues Encountered
- Data files (NASDAQ.csv, signals CSV) not present in worktree - copied from main repo to enable script execution

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions fully implemented.

## Next Phase Readiness
- Rule discovery report complete with pre-2019 and post-2019 decision trees
- Key finding: structural shift from EMA9-based to EMA55-based rules between eras
- Post-2019 rules marked as tentative due to small sample size (95 signals, Sell=15)
- Ready for validation phase to test discovered rules against out-of-sample data

---
*Phase: 09-rule-discovery*
*Completed: 2026-03-29*
