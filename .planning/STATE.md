---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Signal Quality & Macro Filter
status: defining
stopped_at: null
last_updated: "2026-03-30T12:00:00.000Z"
last_activity: 2026-03-30
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Discover the actual indicator-based rules driving Dr. K's MDM signals
**Current focus:** Defining requirements for v5.0

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-30 — Milestone v5.0 started

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v4.0)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend (from v3.0):**

- Last 5 plans: 5min, 4min, 20min, 22min, 48min
- Trend: Variable (simple plans fast, complex plans longer)

*Updated after each plan completion*
| Phase 16 P01 | 33min | 2 tasks | 4 files |
| Phase 16 P02 | 68min | 2 tasks | 4 files |
| Phase 17 P01 | 48min | 2 tasks | 7 files |
| Phase 17 P02 | 29min | 2 tasks | 6 files |
| Phase 18 P01 | 6min | 2 tasks | 5 files |
| Phase 18 P02 | 3min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v4.0 Roadmap]: 3-phase structure: Short Mechanics -> Stop Loss -> P&L & Validation
- [v4.0 Roadmap]: SHORT-01 + SHORT-04 + TRANS-01 grouped together (short entry/cover/transition are tightly coupled)
- [v4.0 Roadmap]: All stop loss requirements (RISK-01/02/03 + SHORT-03) in one phase for unified risk management
- [v4.0 Roadmap]: P&L tracking (SHORT-02) deferred to Phase 18 since it needs working short positions from Phase 16
- [Phase 16]: Short P&L formula: (entry - cover) / entry, positive on market drop
- [Phase 16]: enter_buy() raises ValueError from SELL state to enforce cover_short() first
- [Phase 16]: MA50 breakout from SELL covers to CASH only (no direct buy per Pitfall 4)
- [Phase 16]: All SELL->CASH transitions use cover_short() with P&L (replaces degrade_to_cash)
- [Phase 17]: Long stop loss reduced from 2.5% to 1.5% per Dr. K documented rules
- [Phase 17]: Volatility-adaptive stop loss uses ATR/baseline ratio clamped to [0.5x, 2.5x]
- [Phase 17]: DD5 high is high of specific 5th DD day, locked into engine on SELL entry
- [Phase 17]: Short stop loss at 1% above DD5 high, checked before FTD/cover signals
- [Phase 18]: Inverse return formula: equity * (closes[i-1] / closes[i]) for short P&L
- [Phase 18]: Rule docs updated with short position, transition enforcement, and ATR-adaptive stop loss (v4.0)

### Pending Todos

None yet.

### Blockers/Concerns

- Existing position_manager in mdm_v2/mdm_hybrid supports long-only -- needs extension for short positions
- VN30 short mechanics differ from NASDAQ (direct index short vs inverse ETF) -- may need market-specific adapters
- DD5 high tracking for short stop loss requires access to distribution day history from state machine

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260330-9b5 | Organize root directory and create strategy rule docs | 2026-03-30 | pending | [260330-9b5-organize-root-directory-and-create-strat](./quick/260330-9b5-organize-root-directory-and-create-strat/) |

## Session Continuity

Last session: 2026-03-30T08:23:12.578Z
Stopped at: Completed 18-02-PLAN.md
Resume file: None
