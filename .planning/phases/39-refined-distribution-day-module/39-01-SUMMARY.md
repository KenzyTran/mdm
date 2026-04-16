---
phase: 39-refined-distribution-day-module
plan: 01
subsystem: strategy-config
tags: [mdm-hybrid, distribution-day, indicators, pandas, pytest, feature-gate]

# Dependency graph
requires:
  - phase: 38-atr-buffer-zone-module
    provides: feature-gate pattern (atr_buffer_enabled), MDMV2Config dataclass extension pattern, regression fixture/test pattern
provides:
  - 6 refined_dd_* fields on MDMV2Config (DD-01, DD-03)
  - Indicators.add_volume_ma_column producing vol_ma20 (DD-02 data layer)
  - Indicators.add_volume_percentile_column producing vol_top_pct boolean (DD-02 data layer)
  - Gated __post_init__ validation (only fires when refined_dd_enabled=True)
  - Both VN30_PRESET and NASDAQ_PRESET ship refined_dd_enabled=False (D-07, DD-04 backward-compat)
  - 14-test pytest suite covering config defaults, validation gating, and indicator semantics
affects: [39-02, 39-03, phase-40-grid-search]

# Tech tracking
tech-stack:
  added: []  # No new libraries — pure pandas/numpy/pytest
  patterns:
    - "Feature-gated __post_init__ validation: assertions only run when feature flag is True (Pitfall 5)"
    - "Volume percentile via pd.Series.rolling().quantile() with min_periods=1 (no NaN on early rows)"
    - "Indicator column methods follow add_atr_column template: @staticmethod, df.copy(), descriptive column name"

key-files:
  created:
    - tests/test_phase39_indicators.py
  modified:
    - strategies/mdm_hybrid/config.py
    - strategies/mdm_hybrid/indicators.py

key-decisions:
  - "Gated validation: refined_dd_* assertions only fire when refined_dd_enabled=True so default-disabled configs with permissive params still construct"
  - "vol_top_pct stored as boolean (cast via .astype(bool)) to make downstream branch logic in DD counter trivially `if row['vol_top_pct']:`"
  - "min_periods=1 on both rolling indicators matches existing add_ma50_column / add_atr_column / add_violation_threshold_column convention — no NaN gymnastics in DD counter loop"

patterns-established:
  - "Indicator method naming: add_<feature>_column(df, ...) returning df.copy() with new column(s)"
  - "Test file naming: test_phase{NN}_<subsystem>.py colocated under tests/ root"
  - "TDD RED→GREEN commit cadence: separate test commit (failing) from feat commit (implementation)"

requirements-completed: [DD-01, DD-03]

# Metrics
duration: 3min
completed: 2026-04-16
---

# Phase 39 Plan 01: Refined DD Config + Volume Indicator Columns Summary

**Added 6 refined_dd_* config fields to MDMV2Config (defaults D-06, presets disabled) plus two volume indicator columns (vol_ma20, vol_top_pct) ready for the dual-threshold DD rule in Plan 02.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-16T03:47:40Z
- **Completed:** 2026-04-16T03:50:46Z
- **Tasks:** 2
- **Files modified:** 2 (+1 created)

## Accomplishments

- MDMV2Config carries 6 new refined_dd_* fields with D-06 defaults; both VN30_PRESET and NASDAQ_PRESET ship `refined_dd_enabled=False` to preserve v6.0 byte-identical behavior (DD-04, D-07)
- Validation only fires when feature is enabled (Pitfall 5 protection) — disabled configs with arbitrary refined_dd_* values still construct cleanly
- Indicators class exposes `add_volume_ma_column` (vol_ma20) and `add_volume_percentile_column` (vol_top_pct boolean) following the existing `add_atr_column` / `add_ma50_column` template
- Both rolling computations use `min_periods=1` so no NaN appears on early rows — Plan 02 DD counter can read columns without null guards
- 14 unit tests pass covering: defaults, validation gating (enabled vs disabled), order constraint (large_drop ≤ small_drop), percentile range (1-100), lookback positivity, MA computation (basic + min_periods edge), percentile semantics (top hit, mid miss, short data edge), and input non-mutation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add refined DD config fields to MDMV2Config and presets** — `a546633` (feat)
2. **Task 2 RED: Add failing tests for indicators + config** — `005d50c` (test)
3. **Task 2 GREEN: Add volume MA + percentile indicator columns** — `41b94f2` (feat)

_Task 2 was TDD: RED commit (failing tests) → GREEN commit (implementation). No REFACTOR commit — implementation matched style on first pass._

## Files Created/Modified

- `strategies/mdm_hybrid/config.py` — added 6 `refined_dd_*` fields to `MDMV2Config`, gated validation block in `__post_init__`, propagated all 6 fields to `VN30_PRESET` and `NASDAQ_PRESET`
- `strategies/mdm_hybrid/indicators.py` — added `add_volume_ma_column(df, period=20)` and `add_volume_percentile_column(df, lookback=50, percentile=5)` static methods
- `tests/test_phase39_indicators.py` — new 14-test pytest suite covering config defaults/validation and indicator semantics

## Decisions Made

- **Gated validation in `__post_init__`**: Per Pitfall 5 / D-06, the refined_dd_* asserts run only when `refined_dd_enabled=True`. This means `MDMV2Config(refined_dd_enabled=False, refined_dd_large_drop=0.99)` constructs without error — important so disabled-feature configs do not accidentally trip on placeholder values that Phase 40 sweep code may stage temporarily.
- **`vol_top_pct` cast to bool dtype**: Using `(df['volume'] >= rolling_threshold).astype(bool)` returns a true bool Series rather than `object`/`uint8`. Lets downstream DD counter use `bool(row['vol_top_pct'])` cheaply and keeps the column self-describing in parquet fixtures.
- **`min_periods=1` on both rolling computations**: Consistent with every existing `add_*_column` in the same module. Matches Pitfall 2 guidance — early-period rows use whatever data is available rather than producing NaN that would force null-handling in the DD counter loop.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes triggered. No architectural questions surfaced.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 02 ready:** `MDMV2Config.refined_dd_enabled` flag, all 6 parameters, and both volume columns are in place. Plan 02 (`DistributionDayCounter` dual-threshold logic + engine precompute hook) can wire `vol_above_ma20 = row['volume'] > row['vol_ma20']` and `vol_top_pct = bool(row['vol_top_pct'])` directly into the DD branch.
- **Plan 03 ready:** Regression fixture generation can call `HybridEngine` with `refined_dd_enabled=False` and rely on Task 1's preset wiring to ensure DD-04 backward-compat baseline is captured.
- **No blockers.** All Plan 01 acceptance criteria met:
  - 6 config fields present with D-06 defaults ✓
  - Both presets ship `refined_dd_enabled=False` ✓
  - Validation gated on enabled=True ✓
  - Two indicator methods produce expected columns with min_periods=1 ✓
  - 14 unit tests green via `uv run pytest tests/test_phase39_indicators.py -x -v` ✓

## Self-Check: PASSED

- File `strategies/mdm_hybrid/config.py`: FOUND
- File `strategies/mdm_hybrid/indicators.py`: FOUND
- File `tests/test_phase39_indicators.py`: FOUND
- Commit `a546633`: FOUND
- Commit `005d50c`: FOUND
- Commit `41b94f2`: FOUND
- Verification command `uv run pytest tests/test_phase39_indicators.py -x -v`: 14 passed

---
*Phase: 39-refined-distribution-day-module*
*Completed: 2026-04-16*
