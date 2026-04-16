---
phase: 39-refined-distribution-day-module
plan: 02
subsystem: distribution-day-engine
tags: [mdm-hybrid, distribution-day, engine-pipeline, feature-gate, pytest, tdd]

# Dependency graph
requires:
  - phase: 39-01
    provides: MDMV2Config.refined_dd_* fields, Indicators.add_volume_ma_column, Indicators.add_volume_percentile_column
  - phase: 38-atr-buffer-zone-module
    provides: feature-gate pattern (enabled=False byte-identical), precompute block insertion convention
provides:
  - DistributionDayCounter.is_distribution_day_type1 branches on refined_dd_enabled (DD-02, DD-03)
  - DistributionDayCounter.check_distribution_day forwards vol_above_ma20 and vol_top_pct kwargs (Pitfall 4)
  - HybridEngine precomputes vol_ma20 + vol_top_pct columns when refined_dd_enabled=True (D-05)
  - HybridEngine daily loop passes per-row vol inputs to DD counter in BUY state
  - Expiry-day suppression of vol_top_pct column + per-row vol_above_ma20 override (Pitfall 1)
  - 11-test pytest suite covering classic fallback, large/small drop paths, Type 2 invariance, kwarg forwarding
affects: [39-03, phase-40-grid-search]

# Tech tracking
tech-stack:
  added: []  # Pure pandas/numpy/pytest; no new libraries
  patterns:
    - "Feature-gate precompute: `if self.config.v2_config.refined_dd_enabled: df = Indicators.add_volume_*_column(df, ...)` (same shape as Phase 38 atr_buffer block)"
    - "Per-row kwarg synthesis in daily loop: default False, overridden only when feature enabled and not expiry day"
    - "Column-level + row-level expiry suppression: `df.loc[..., 'vol_top_pct'] = False` during precompute AND `is_expiry` guard in row loop (belt-and-braces per Pitfall 1)"
    - "Backward-compatible method signature growth: new kwargs default to False so existing positional callers unaffected (Pitfall 4)"

key-files:
  created: []
  modified:
    - strategies/mdm_hybrid/distribution_day.py
    - strategies/mdm_hybrid/mdm_hybrid_engine.py
    - tests/test_phase39_dd_logic.py

key-decisions:
  - "Belt-and-braces expiry suppression: mask vol_top_pct column during precompute AND skip vol input synthesis in daily loop when is_expiry. Column mask alone would let vol_above_ma20 fire on expiry days (computed from raw volume vs vol_ma20); row-level guard catches that without needing a second precompute column."
  - "Default False for all new kwargs (vol_above_ma20, vol_top_pct) at both is_distribution_day_type1 and check_distribution_day boundaries. Existing regression fixtures + Plan 03 backward-compat test work unchanged (Pitfall 4)."
  - "Type 2 stalling DD left untouched per D-01/D-04. Only Type 1 branches on refined_dd_enabled; Type 2 always uses classic price_stall + volume_up + p_loc rule regardless of flag state."
  - "Disabled path skips vol column precompute entirely (D-05). Engine smoke test confirmed vol_ma20 and vol_top_pct are NOT present in result when refined_dd_enabled=False, preserving DD-04 byte-identical invariant for Plan 03 fixture generation."

patterns-established:
  - "Phase 39 precompute block lives between ATR buffer block and filter_enabled block, inserted in the same location convention as Phase 38"
  - "Expiry-day suppression runs AFTER the existing volume_up expiry filter so both classic and refined paths see the same expiry-day treatment"

requirements-completed: [DD-02, DD-03]

# Metrics
duration: ~4 min (Task 1 already committed in prior session; this session completed Task 2 engine wiring + verification + SUMMARY)
completed: 2026-04-16
---

# Phase 39 Plan 02: Dual-Threshold DD Logic + Engine Wiring Summary

**Wired the refined dual-threshold Distribution Day rule (large_drop + vol>MA20) OR (small_drop + top-percentile volume) through DistributionDayCounter and HybridEngine, gated entirely behind `refined_dd_enabled`; disabled path stays byte-identical to v6.0 while enabled path precomputes vol_ma20/vol_top_pct and passes them to the DD counter with expiry-day suppression.**

## Performance

- **Duration:** ~4 min this session (Task 1 had already shipped in a prior session; this session committed Task 2 engine wiring + verification + SUMMARY)
- **Completed:** 2026-04-16
- **Tasks:** 2 (Task 1 resumed / verified complete, Task 2 completed + committed this session)
- **Files modified:** 2 (1 test file created, 2 source files modified)

## Accomplishments

- `DistributionDayCounter.is_distribution_day_type1` branches cleanly on `refined_dd_enabled`: classic v6.0 rule (drop ≤ dd_price_drop_threshold AND volume_up) when disabled, dual-threshold rule (large_drop + vol_above_ma20) OR (small_drop + vol_top_pct) when enabled. Type 2 stalling left untouched.
- `check_distribution_day` signature extended with `vol_above_ma20: bool = False, vol_top_pct: bool = False` so every existing positional caller (Plan 03 regression fixture, downstream code, unit tests) keeps working unchanged.
- `HybridEngine.run` precomputes `vol_ma20` and `vol_top_pct` columns only when `refined_dd_enabled=True` (D-05). Disabled path adds ZERO columns — engine smoke test confirmed `'vol_ma20' not in result.columns` and `'vol_top_pct' not in result.columns` for disabled config.
- Expiry-day suppression implemented belt-and-braces: column-level `df.loc[is_expiry_day, 'vol_top_pct'] = False` during precompute + row-level `if not is_expiry:` guard in the daily BUY-state block. This ensures refined DD does not fire on derivative expiry days (Pitfall 1) for BOTH vol inputs, since `vol_above_ma20` is computed per-row and cannot be masked via column.
- 11 unit tests pass via `uv run pytest tests/test_phase39_dd_logic.py -x -v` covering: 3 classic fallback cases, 2 refined large-drop path cases, 3 refined small-drop path cases, 1 Type 2 invariance test, 2 `check_distribution_day` backward-compat tests.
- Phase 38 regression test (`tests/test_phase38_backward_compat.py`) still passes — no side effects from Phase 39 wiring.
- Engine smoke test (both disabled and enabled) runs cleanly on VN30 2020-01-01 to 2020-06-30 data.

## Task Commits

Each task was committed atomically (Task 1 as TDD RED + GREEN commits, Task 2 as single feat commit):

1. **Task 1 RED: Add failing tests for dual-threshold DD logic** — `fcb6461` (test)
2. **Task 1 GREEN: Add dual-threshold branch to DistributionDayCounter** — `198bc42` (feat)
3. **Task 2: Wire refined DD vol precompute + daily loop into HybridEngine** — `d5fe0f7` (feat)

_Task 2 did not require a separate test commit — existing Plan 01 indicator tests and the engine smoke test from the plan's `<verify>` block cover the wiring contract._

## Files Created/Modified

- `strategies/mdm_hybrid/distribution_day.py` — `is_distribution_day_type1` accepts `vol_above_ma20` and `vol_top_pct` kwargs (default False) and branches on `self.config.refined_dd_enabled`; `check_distribution_day` forwards both kwargs into the type1 check; Type 2 logic body unchanged.
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — added `refined_dd_enabled` precompute block (calls `Indicators.add_volume_ma_column(df, period=20)` + `Indicators.add_volume_percentile_column(df, lookback, percentile)`), added expiry-day column mask for `vol_top_pct`, extended BUY-state DD block to synthesize `vol_above_ma20` and `vol_top_pct_val` (with expiry guard) and pass them as kwargs to `self.dd_counter.check_distribution_day`.
- `tests/test_phase39_dd_logic.py` — new 11-test pytest suite for DD-02/DD-03 branch logic, Type 2 invariance, and backward-compat signature.

## Decisions Made

- **Belt-and-braces expiry suppression.** The plan specified column-level masking of `vol_top_pct` on expiry days. Implemented that, but also added a row-level `if not is_expiry:` guard before computing `vol_above_ma20 = bool(row['volume'] > vol_ma20_val)`. Rationale: `vol_above_ma20` is computed per-row from raw `volume` and `vol_ma20` — the column mask only protects `vol_top_pct`. Without the row-level guard, `vol_above_ma20` could still fire on an expiry-day large drop and trigger refined DD. Both guards together preserve the spirit of the existing `volume_up` expiry filter across both vol inputs.
- **No REFACTOR commit for Task 2.** The engine wiring landed cleanly on first implementation and matched the plan's `<action>` block nearly verbatim. No structural cleanup needed.
- **Comment blocks preserved as rule references.** Inline comments cite the governing decisions (D-05, DD-04, Pitfall 1, Pitfall 4) so future contributors can cross-reference without rereading the full plan.

## Deviations from Plan

- **Expiry-day row-level guard added in daily loop** (tracked as auto-enhancement, Rule 2 — missing critical functionality): The plan's `<action>` block only specified column-level masking of `vol_top_pct` on expiry days. Discovered during implementation that `vol_above_ma20` is computed per-row from raw volume and cannot be masked via column. Added the row-level `if not is_expiry:` guard so both vol inputs are suppressed on expiry days. This is the intent of the plan (Pitfall 1: "suppress refined DD on expiry days") faithfully extended to both inputs. Files modified: `strategies/mdm_hybrid/mdm_hybrid_engine.py` (daily loop BUY-state block). Commit: `d5fe0f7`.

## Issues Encountered

None.

## User Setup Required

None — pure code change, no external service configuration.

## Next Phase Readiness

- **Plan 03 ready:** `refined_dd_enabled=False` path is byte-identical to v6.0 (no vol columns added, classic rule unchanged). Plan 03 can generate the regression fixture (`tests/fixtures/phase39_v6_baseline_dd_sequence.parquet`) by running `HybridEngine` with `refined_dd_enabled=False` on VN30 2015-2026 and capturing `date`, `is_dd`, `dd_type`, `dd_count_20d` columns. The fixture will then be asserted against the same run in `test_phase39_backward_compat.py` with byte-exact equality.
- **Phase 40 ready:** Full parameter surface exposed — both enabled/disabled modes run without error; grid search can vary `refined_dd_large_drop`, `refined_dd_small_drop`, `refined_dd_small_vol_percentile` with confidence that the engine wiring handles all combinations.
- **No blockers.** All Plan 02 acceptance criteria met:
  - Dual-threshold branch in `is_distribution_day_type1` ✓
  - `check_distribution_day` forwards new kwargs ✓
  - Engine precompute gated on `refined_dd_enabled` ✓
  - Engine daily loop synthesizes vol inputs and passes them through ✓
  - Expiry day suppression (column + row level) ✓
  - 11 tests green via `uv run pytest tests/test_phase39_dd_logic.py -x -v` ✓
  - Engine smoke test (disabled + enabled) passes ✓
  - Phase 38 regression still green ✓

## Self-Check: PASSED

- File `strategies/mdm_hybrid/distribution_day.py`: FOUND
- File `strategies/mdm_hybrid/mdm_hybrid_engine.py`: FOUND
- File `tests/test_phase39_dd_logic.py`: FOUND
- Commit `fcb6461` (test RED): FOUND
- Commit `198bc42` (feat GREEN, Task 1): FOUND
- Commit `d5fe0f7` (feat, Task 2 engine wiring): FOUND
- `uv run pytest tests/test_phase39_dd_logic.py -x -v`: 11 passed
- `uv run pytest tests/test_phase39_indicators.py -x -v`: 14 passed (no regression)
- `uv run pytest tests/test_phase38_backward_compat.py -x`: 2 passed (no regression)
- Engine smoke test (both refined_dd_enabled=False and True): PASSED

---
*Phase: 39-refined-distribution-day-module*
*Completed: 2026-04-16*
