---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: VN30 MDM Whipsaw Reduction
status: defining_requirements
stopped_at: Milestone v9.0 started
last_updated: "2026-04-15"
last_activity: 2026-04-15
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Discover MDM rules + apply on Vietnamese market — current focus: reduce whipsaw on VN30 index timing.
**Current focus:** Milestone v9.0 — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-15 — Milestone v9.0 started

## Accumulated Context

### Baseline (HybridEngine + fail-safe, v6.0)

- Full period 2015-2026: Return +238.8%, CAGR 11.5%, MaxDD -28.2%
- B&H VN30: +205%, MaxDD -48.1%
- Walk-forward Train (2015-2021): CAGR 13.6%, MaxDD -15.3%
- Walk-forward Test (2022-2026): CAGR 8.1%, MaxDD -28.2%
- Signal breakdown: 60 BUY (43% FTD, 40% 52w-breakout, 17% MA50-breakout), 124 SELL (84% MA50-breakdown, 16% cash-deterioration)
- Exit breakdown: 59 BUY-exits (49% MA10-3day, 24% stop-loss, 14% DD-threshold), 133 SELL-exits (46% MA50-cover, 26% fail-safe, 25% FTD-cover)
- Time in state: BUY 30.5%, SELL 32.1%, CASH 37.4%

### Diagnostic driving v9.0

- **Whipsaw source #1:** 84% of SELL signals come from MA50 breakdown — target for ATR Buffer Zone
- **Whipsaw source #2:** 22 BUY-exits from stop-loss + DD threshold — target for Refined DD definition
- **Hypothesis:** Large-cap "kéo xả" (VIC, VCB) to liquidate retail F1 derivatives creates false breakdowns that ATR buffer will absorb

### Grid search budget

- ATR sweep: 36 combos (4 multiplier × 3 period × 3 consecutive_days)
- DD sweep: 54 combos (6 large_drop × 3 small_drop × 3 vol_percentile)
- Sequential (ATR first, lock best, then DD): 90 total runs
- Selection: max Sharpe with MaxDD ≤ -30% constraint, tie-break by CAGR

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-04-15
Stopped at: Milestone v9.0 started
Resume file: None
