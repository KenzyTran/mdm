---
phase: 24-buy-entry-refinement
plan: 02
subsystem: trading-strategy
tags: [gap-filter, rally-threshold, buy-entry, validation, vn30, a-b-test]

# Dependency graph
requires:
  - phase: 24-buy-entry-refinement-01
    provides: BuyEntryFilter module, gap_filter_enabled/rally_threshold_enabled config fields, engine integration
provides:
  - A/B validation script comparing 4 buy entry configs on VN30
  - Gap filter analysis showing signal type breakdown (classic FTD vs breakout)
  - Rally threshold analysis showing 31 early entry instances in shallow pullbacks
  - Updated rules_mdm_v2.md with Section XV documenting both features
affects: [phase-25-ma-review, phase-27-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [retroactive-signal-scan-pattern, signal-type-aware-analysis]

key-files:
  created:
    - analysis/validate_buy_entry.py
  modified:
    - docs/rules_mdm_v2.md

key-decisions:
  - "Gap filter has zero impact on VN30 classic FTDs -- all 19 gap-broken signals are MA50/52WEEK breakouts (correctly bypassed per D-01)"
  - "Rally threshold adds 31 early FTD entries on VN30 but reduces total return (40.2% vs 58.1%) and increases trades (87 vs 69)"
  - "Combined config (53.5% return) underperforms baseline (58.1%) on VN30 -- buy entry refinements calibrated for US market patterns"

patterns-established:
  - "Retroactive signal scan: analyze historical signals by type (classic FTD vs breakout) to understand filter behavior"
  - "VN30 market structure finding: 7% daily limit means gap-up broken is rare for classic FTDs"

requirements-completed: [GAP-02, RALLY-03]

# Metrics
duration: 7min
completed: 2026-03-31
---

# Phase 24 Plan 02: Buy Entry Validation Summary

**A/B validation of gap filter and rally threshold on VN30: gap filter has no classic FTD impact (all gap-broken signals are breakouts), rally threshold adds 31 early entries but reduces return**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-31T10:21:28Z
- **Completed:** 2026-03-31T10:28:42Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created 4-scenario A/B validation script (baseline, gap_filter, rally_threshold, combined) on VN30
- Gap filter analysis reveals VN30 classic FTDs never exhibit gap-up broken pattern; all 19 gap-broken instances are MA50/52WEEK breakouts correctly bypassed per D-01
- Rally threshold analysis shows 31 early FTD entries in shallow pullbacks (drawdown < 6%), all with rally_day=0
- Updated docs/rules_mdm_v2.md with Section XV documenting gap-up invalidation and rally threshold rules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create A/B validation script** - `bae5876` (feat)
2. **Task 2: Update rules documentation** - `8858877` (docs)

## Files Created/Modified
- `analysis/validate_buy_entry.py` - A/B validation with 4 configs, gap filter analysis, rally timing analysis
- `docs/rules_mdm_v2.md` - Section XV: BUY ENTRY REFINEMENT (v6.0) with gap-up invalidation and rally threshold rules

## Decisions Made
- Gap filter has zero impact on VN30 classic FTDs because VN30's 7% daily price limit prevents the gap-up broken pattern from occurring on classic FTD signals. All 19 gap-broken signals are MA50/52WEEK breakouts which correctly bypass the filter per D-01.
- Rally threshold adds many early entries (31 new FTDs) but these extra signals reduce overall performance (40.2% vs 58.1% return, 87 vs 69 trades) -- the shallow pullback signals on VN30 tend to be noisy.
- Combined config (53.5%) still underperforms baseline (58.1%) -- buy entry refinements are calibrated for US market patterns where gap-up broken FTDs are more common.

## Deviations from Plan

None - plan executed exactly as written. The gap filter analysis approach was adapted from direct A/B comparison to retroactive signal-type scan when direct comparison showed identical results (0 filtered), providing more informative output about why the filter has no impact on VN30.

## Issues Encountered
- Data files (vn30.csv) not present in worktree due to .gitignore -- copied from main repo
- Worktree was behind main branch -- required fast-forward merge to get Plan 01 commits

## Known Stubs

None -- all functionality is fully wired with no placeholder data.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Validation results show gap filter is a safety net (no VN30 impact) and rally threshold needs parameter tuning
- Both features are correctly implemented but their value on VN30 is limited compared to US markets
- Ready for Phase 25 (MA Review) which may provide more significant performance improvements

## Self-Check: PASSED

- analysis/validate_buy_entry.py exists on disk
- docs/rules_mdm_v2.md exists on disk and contains Section XV
- Commit bae5876 verified in git log
- Commit 8858877 verified in git log

---
*Phase: 24-buy-entry-refinement*
*Completed: 2026-03-31*
