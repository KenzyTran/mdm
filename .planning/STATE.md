---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: VN30 MDM Whipsaw Reduction
status: ready_to_execute
stopped_at: Roadmap created, Phase 38 ready to plan
last_updated: "2026-04-15"
last_activity: 2026-04-15
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Discover MDM rules + apply on Vietnamese market — current focus: reduce whipsaw on VN30 index timing via ATR Buffer Zone + Refined Distribution Day.
**Current focus:** Milestone v9.0 — roadmap complete, ready to plan Phase 38

## Current Position

Phase: 38 — ATR Buffer Zone Module (not started)
Plan: —
Status: Ready to plan — roadmap locked
Last activity: 2026-04-15 — Roadmap created for v9.0 (Phases 38-42)

Progress: [..........] 0% (0/5 phases)

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

- **Whipsaw source #1:** 84% of SELL signals come from MA50 breakdown — target for ATR Buffer Zone (Phase 38)
- **Whipsaw source #2:** 22 BUY-exits from stop-loss + DD threshold — target for Refined DD definition (Phase 39)
- **Hypothesis:** Large-cap "kéo xả" (VIC, VCB) to liquidate retail F1 derivatives creates false breakdowns that ATR buffer will absorb

### v9.0 phase plan

- Phase 38: ATR Buffer Zone module (ATR-01..04) — indicator + trigger + config flag + regression
- Phase 39: Refined Distribution Day module (DD-01..04) — dual-threshold + config flag + regression
- Phase 40: Grid search (SWEEP-01..04) — ATR sweep (36 runs) → lock best → DD sweep (54 runs) → select max Sharpe with MaxDD ≤ -30%
- Phase 41: A/B + walk-forward validation (VAL-01..04) — 4 scenarios, Train 2015-2021 / Test 2022-2026, whipsaw diagnostic
- Phase 42: Documentation + dashboard (DOC-01..03) — rules_mdm_hybrid.md, v9 dashboard JSON, audit report

### Grid search budget

- ATR sweep: 36 combos (4 multiplier × 3 period × 3 consecutive_days) on train 2015-2021
- DD sweep: 54 combos (6 large_drop × 3 small_drop × 3 vol_percentile) on train 2015-2021, locked ATR
- Sequential (ATR first, lock best, then DD): 90 total runs
- Selection: max Sharpe with MaxDD ≤ -30% constraint, tie-break by CAGR

### Success criterion

CAGR ≥ 11.5% AND (Sharpe > baseline OR MaxDD < -25%) on full 2015-2026 period.

### Pending Todos

None — awaiting `/gsd:plan-phase 38`.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-15
Stopped at: Roadmap created for v9.0; Phase 38 ready to plan
Resume file: None
Next command: `/gsd:plan-phase 38`
