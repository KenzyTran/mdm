---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: mdm-rule-discovery
status: defining
stopped_at: Defining requirements for v2.0
last_updated: "2026-03-29T00:00:00.000Z"
last_activity: 2026-03-29
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-27)

**Core value:** Discover the actual indicator-based rules driving Dr. K's MDM signals by analyzing 962 published signals against computed technical indicators
**Current focus:** v2.0 milestone — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-29 — Milestone v2.0 started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P01 | 5min | 1 tasks | 7 files |
| Phase 01 P02 | 4min | 2 tasks | 5 files |
| Phase 02 P01 | 4min | 2 tasks | 8 files |
| Phase 02 P02 | 2min | 2 tasks | 23 files |
| Phase 02 P03 | 6min | 2 tasks | 55 files |
| Phase 02 P04 | 1min | 1 tasks | 1 files |
| Phase 03 P01 | 8min | 2 tasks | 3 files |
| Phase 03 P02 | 5min | 2 tasks | 5 files |
| Phase 04 P02 | 3min | 2 tasks | 4 files |
| Phase 05 P02 | 4min | 2 tasks | 2 files |
| Phase 06 P01 | 3min | 2 tasks | 3 files |
| Phase 06 P02 | 4min | 2 tasks | 3 files |
| Phase 06 P03 | 14min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: 6-phase structure derived from requirement categories (DATA -> ORG -> SIG -> MDM -> PERF -> VN30)
- Roadmap: NASDAQ validation must complete before VN30 adaptation begins (Phase 5 gates Phase 6)
- [Phase 01]: Used actual CSV values for spot-check references instead of plan-specified values when they differed
- [Phase 01]: Volume dtype forced to float64 via explicit cast for consistency across all markets
- [Phase 01]: Signal fixtures are skeleton approximations needing manual verification against published source
- [Phase 01]: Added .gitignore exception for data/signals/ - fixtures are curated test artifacts
- [Phase 02]: Golden baselines captured from pre-migration code before any file moves
- [Phase 02]: Regression tests import from new strategy paths - will fail until migration completes
- [Phase 02]: Pure copy migration - no import modifications needed since all internal imports are relative
- [Phase 02]: Used sys.path.insert pattern for scripts/ and analysis/ subdirectory imports
- [Phase 02]: Pre-existing test_trade_pnl_matches failure confirmed as baseline CSV format issue, not migration regression
- [Phase 02]: Normalize both sides with fillna rather than modifying baseline CSV
- [Phase 03]: TIMING window uses calendar-day approximation (5 trading days ~ 7.5 calendar days)
- [Phase 03]: Integration tests auto-detect git worktree and resolve data paths to main repo for gitignored CSVs
- [Phase 03]: Divergence classification cascade: TIMING -> STRUCTURAL -> THRESHOLD -> IRREPRODUCIBLE (D-06 order)
- [Phase 03]: Added output/ to .gitignore for generated analysis artifacts
- [Phase 03]: Used git worktree data path resolution in analysis script for gitignored CSVs
- [Phase 04]: Hypothesis runner uses synthetic self-matching for baseline validation
- [Phase 04]: Parameter sweep uses itertools.product for exhaustive grid search, same pattern as scripts/optimize_mdm.py
- [Phase 05]: Classic engine equity maps HOLDING/WAITING_SELL to invested, CASH/SHORT to flat for fair comparison
- [Phase 05]: Published vs model signal markers use different shapes/sizes in dashboard for visual separation
- [Phase 06]: Expiry day holiday fallback uses DataFrame trading dates as calendar
- [Phase 06]: Engine DD suppression via volume_up override - no vn30_filters import in engine
- [Phase 06]: Config loaded from key=value text file with fallback to MDMV2Config defaults
- [Phase 06]: scoring_fn parameter makes run_sweep market-agnostic (Sharpe for VN30, match-rate for NASDAQ)
- [Phase 06]: Train/test split at 2020 with overfitting detection (Sharpe > 2.0 train + < 0.5 test)

### Pending Todos

None yet.

### Blockers/Concerns

- US market data prices scaled ~1000x -- must be resolved in Phase 1 before any rule work
- Post-2019 MDM change may be structural (not just parametric) -- Phase 4 scope could expand

## Session Continuity

Last session: 2026-03-28T11:30:00.000Z
Stopped at: Completed 06-02-PLAN.md and 06-03-PLAN.md (Wave 2)
Resume file: None
