---
phase: 18-short-p-l-comparative-validation
plan: 02
subsystem: docs
tags: [short-position, stop-loss, atr, dd5, transition-rules, vietnamese]

# Dependency graph
requires:
  - phase: 16-short-signal-mechanics
    provides: "Short entry/cover logic, cover_short(), enter_buy() guard"
  - phase: 17-stop-loss-risk-management
    provides: "1.5% stop loss, ATR adaptive scaling, DD5 high short stop"
provides:
  - "Updated rules_mdm_v2.md with short signal, transition, and stop loss documentation"
  - "Updated rules_mdm_hybrid.md with hybrid-specific short signal and filter interaction docs"
affects: [vn30-adaptation, future-rule-docs]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Vietnamese-language rule documentation with LaTeX formulas"]

key-files:
  created: []
  modified:
    - "docs/rules_mdm_v2.md"
    - "docs/rules_mdm_hybrid.md"

key-decisions:
  - "Appended 3 new sections (X, XI, XII) after existing Section IX in both docs"
  - "Maintained Vietnamese language consistency with existing doc style"
  - "Included hybrid-specific filter interaction table in hybrid doc"

patterns-established:
  - "Rule doc versioning: sections marked with (v4.0) for traceability"
  - "Comparison tables showing old vs new behavior for breaking changes"

requirements-completed: [TRANS-03]

# Metrics
duration: 3min
completed: 2026-03-30
---

# Phase 18 Plan 02: Rule Documentation Update Summary

**Short position rules, SELL->CASH->BUY transition enforcement, and 1.5% ATR-adaptive stop loss documented in both V2 and Hybrid rule docs in Vietnamese**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-30T08:17:10Z
- **Completed:** 2026-03-30T08:19:52Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Appended Section X (short position rules), Section XI (transition enforcement), and Section XII (stop loss updates) to rules_mdm_v2.md
- Appended matching sections to rules_mdm_hybrid.md with hybrid-specific details (filter interaction, OVERRIDE paths, indicator degradation)
- All Phase 16-17 features documented: short entry/cover, 1.5% stop loss, ATR adaptive, DD5 high, SELL->CASH->BUY enforcement

## Task Commits

Each task was committed atomically:

1. **Task 1: Append short signal and stop loss sections to rules_mdm_v2.md** - `98cbb20` (docs)
2. **Task 2: Append short signal and stop loss sections to rules_mdm_hybrid.md** - `1b51a2a` (docs)

## Files Created/Modified
- `docs/rules_mdm_v2.md` - Added Sections X (short positions), XI (transition rules), XII (stop loss v4.0)
- `docs/rules_mdm_hybrid.md` - Added Sections X (short in hybrid with filter interaction), XI (transition rules + OVERRIDE), XII (stop loss v4.0)

## Decisions Made
- Appended after Section IX as specified (D-08 pattern: keep existing structure, append only)
- Used LaTeX math notation for formulas consistent with existing doc style
- Added comparison tables (old vs v4.0) in Section XI for clarity on breaking changes
- Hybrid doc includes filter interaction table showing how CONFIRM/VETO/OVERRIDE affect short positions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Rule documentation is complete for all Phase 16-17 features
- Both V2 and Hybrid rule docs now document the full v4.0 short/stop loss mechanics
- Ready for P&L tracking implementation and comparative backtesting

---
*Phase: 18-short-p-l-comparative-validation*
*Completed: 2026-03-30*
