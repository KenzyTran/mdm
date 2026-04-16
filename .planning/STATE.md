---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: VN30 MDM Whipsaw Reduction
status: verifying
stopped_at: Completed 39-03-PLAN.md (backward-compat fixture + DD-04 regression + rules_mdm_hybrid.md Section XVII) — Phase 39 ready for verification
last_updated: "2026-04-16T06:07:43.581Z"
last_activity: 2026-04-16
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 9
  completed_plans: 9
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Discover MDM rules + apply on Vietnamese market — current focus: reduce whipsaw on VN30 index timing via ATR Buffer Zone + Refined Distribution Day.
**Current focus:** Phase 39 — refined-distribution-day-module

## Current Position

Phase: 39 (refined-distribution-day-module) — READY FOR VERIFICATION
Plan: 3 of 3 (last)
Status: Phase complete — ready for verification
Last activity: 2026-04-16 — Plan 03 shipped (backward-compat fixture + DD-04 regression + docs sync)

Progress: [██████████] 100% (3/3 plans in Phase 39)

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

### Phase 39 Plan 03 Decisions (shipped 2026-04-16)

- Fixture COLS use engine column name `dd_count` (not `dd_count_20d` from decision-language). Engine has always exposed the column without the `_20d` suffix; renaming would have meant a chained refactor across `position_manager`, signal log code, and downstream notebooks — out of Plan 03 scope. Doc Section XVII clarifies the naming explicitly.
- Regression test uses boolean/integer exact equality (no float tolerance) for `is_dd`, `dd_type`, `dd_count`. Discrete columns demand byte-identical match to catch 5DD-threshold regressions (e.g., `dd_count` 4→5 is the difference between "stay BUY" and "trigger SELL").
- Code-docs sync deferred to terminal plan (03) rather than touching docs in every plan. `docs/rules_mdm_hybrid.md` Section XVII covers the completed feature surface atomically — avoids merge conflicts and keeps the doc update coherent with shipped behavior (CLAUDE.md Code-Docs Sync Rule honored at phase level).
- Phase 39 shipped: 2 backward-compat tests + 11 DD-logic tests + 14 indicator tests = 27 Phase 39 tests, all green. Phase 38 regression (2 tests) still green. Total 29 passed in 13.78s.

### Plan 03 Metrics

| Plan | Duration | Tasks | Files | Commits |
| :--- | :---: | :---: | :---: | :--- |
| 39-03 | ~14 min | 2 | 4 (3 created, 1 modified) | `e713624`, `ba1ac02` |

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-16T06:07:43.577Z
Stopped at: Completed 39-03-PLAN.md (backward-compat fixture + DD-04 regression + rules_mdm_hybrid.md Section XVII) — Phase 39 ready for verification
Resume file: None
Next command: `/gsd:verify-phase 39` (Phase 39 ready for verification — all 3 plans shipped, 27 tests green, DD-04 invariant locked)
