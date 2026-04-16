---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: VN30 MDM Whipsaw Reduction
status: executing
stopped_at: Completed 39-02-PLAN.md (dual-threshold DD branch + engine wiring)
last_updated: "2026-04-16T04:12:40.108Z"
last_activity: 2026-04-16
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 9
  completed_plans: 9
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Discover MDM rules + apply on Vietnamese market — current focus: reduce whipsaw on VN30 index timing via ATR Buffer Zone + Refined Distribution Day.
**Current focus:** Phase 39 — refined-distribution-day-module

## Current Position

Phase: 39 (refined-distribution-day-module) — EXECUTING
Plan: 3 of 3
Status: Plan 02 complete — ready to execute Plan 03 (regression fixture + DD-04 backward-compat pytest)
Last activity: 2026-04-16 — Plan 02 shipped (dual-threshold DD branch + HybridEngine wiring)

Progress: [██████....] 67% (2/3 plans in Phase 39)

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

### Phase 39 Plan 01 Decisions (shipped 2026-04-16)

- Refined DD validation in `MDMV2Config.__post_init__` is gated behind `refined_dd_enabled=True` (Pitfall 5) so disabled configs accept arbitrary placeholder params — prevents Phase 40 sweep wiring from accidentally tripping on placeholder values
- Volume indicators (`vol_ma20`, `vol_top_pct`) use `min_periods=1` matching existing `add_*_column` convention — no NaN handling needed in Plan 02 DD counter loop
- `vol_top_pct` cast to bool dtype via `.astype(bool)` for cheap downstream branch logic and self-describing parquet fixtures
- Both VN30_PRESET and NASDAQ_PRESET ship `refined_dd_enabled=False` (D-07) preserving v6.0 byte-identical behavior — DD-04 backward-compat invariant intact

### Phase 39 Plan 02 Decisions (shipped 2026-04-16)

- `DistributionDayCounter.is_distribution_day_type1` branches on `refined_dd_enabled`: classic v6.0 rule (drop ≤ dd_price_drop_threshold AND volume_up) when disabled, dual-threshold rule (large_drop + vol_above_ma20) OR (small_drop + vol_top_pct) when enabled. Type 2 stalling untouched per D-01/D-04.
- `check_distribution_day` grew `vol_above_ma20` and `vol_top_pct` kwargs (default False) — existing positional callers including Plan 03 regression fixture and other downstream code work unchanged (Pitfall 4).
- HybridEngine precompute block gated on `refined_dd_enabled=True` (D-05): disabled path adds zero new columns, preserving DD-04 byte-identical invariant. Smoke test confirmed `'vol_ma20' not in result.columns` when disabled.
- Belt-and-braces expiry suppression for refined DD: column-level `df.loc[is_expiry_day, 'vol_top_pct'] = False` during precompute AND row-level `if not is_expiry:` guard in daily BUY-state block. Needed because `vol_above_ma20` is computed per-row from raw `volume` vs `vol_ma20` and cannot be masked at column level (Pitfall 1 extended).
- 11 unit tests green covering: 3 classic fallback, 2 refined large-drop, 3 refined small-drop, 1 Type 2 invariance, 2 check_distribution_day kwarg forwarding / backward-compat. Phase 38 regression still green — no side effects.

### Pending Todos

- Plan 03: regression fixture generation (`tests/fixtures/phase39_v6_baseline_dd_sequence.parquet`) + DD-04 backward-compat pytest (`tests/test_phase39_backward_compat.py`)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-16T04:12:40.103Z
Stopped at: Completed 39-02-PLAN.md (dual-threshold DD branch + engine wiring)
Resume file: None
Next command: `/gsd:execute-phase 39` (Plan 03 — regression fixture + backward-compat test)
