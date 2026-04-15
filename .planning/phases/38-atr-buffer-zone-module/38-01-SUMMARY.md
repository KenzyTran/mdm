---
phase: 38-atr-buffer-zone-module
plan: 01
subsystem: strategy
tags: [atr, buffer-zone, config, indicators, mdm-hybrid, whipsaw-reduction]

# Dependency graph
requires:
  - phase: 27-combined-validation
    provides: HybridEngine + fail-safe v6.0 baseline (CAGR 11.5%, MaxDD -28.2%)
provides:
  - MDMV2Config with atr_buffer_* fields (feature gate + 3 numeric params)
  - Indicators.add_violation_threshold_column() static method
  - docs/rules_mdm_hybrid.md section XVI ATR Buffer Zone
affects:
  - 38-02-engine-integration
  - 38-03-regression-test
  - 40-atr-grid-search

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Feature-gate boolean in dataclass config (atr_buffer_enabled=False default)
    - Separate ATR column names (atr_buf/true_range_buf) to avoid stop-loss column collision

key-files:
  created: []
  modified:
    - strategies/mdm_hybrid/config.py
    - strategies/mdm_hybrid/indicators.py
    - docs/rules_mdm_hybrid.md

key-decisions:
  - "atr_buffer_period is separate from atr_period (stop-loss ATR) to allow independent sweep in Phase 40"
  - "add_violation_threshold_column uses atr_buf/true_range_buf column names (not atr/true_range) to prevent clobbering stop-loss ATR"
  - "atr_buffer_enabled=False default in both MDMV2Config and presets ensures byte-identical v6.0 behavior by default"
  - "All 3 numeric assertions are unconditional (not gated on enabled) so any config with invalid values fails fast"

patterns-established:
  - "ATR buffer feature gate: atr_buffer_enabled bool flag in MDMV2Config, presets explicitly carry enabled=False"
  - "Separate ATR column suffix pattern: use 'atr_buf'/'true_range_buf' when computing additional ATR variants"

requirements-completed: [ATR-01, ATR-03]

# Metrics
duration: 10min
completed: 2026-04-15
---

# Phase 38 Plan 01: ATR Buffer Zone Config & Indicator Summary

**MDMV2Config extended with 4 atr_buffer_* fields (feature-gated, defaults off) and Indicators.add_violation_threshold_column() implemented using separate atr_buf column to prevent stop-loss ATR collision**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-15T08:25:00Z
- **Completed:** 2026-04-15T08:35:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added 4 new fields to MDMV2Config: atr_buffer_enabled=False, atr_buffer_k=0.5, atr_buffer_period=14, atr_buffer_consecutive_days=2
- Added 3 validation assertions in __post_init__: k>0, period>0, consecutive_days>=1
- VN30_PRESET and NASDAQ_PRESET both explicitly carry atr_buffer_enabled=False (backward-compat)
- Implemented Indicators.add_violation_threshold_column(df, k, period) using atr_buf/true_range_buf column names
- Updated docs/rules_mdm_hybrid.md with section XVI ATR Buffer Zone (Code-Docs Sync Rule)
- All 34 existing tests pass (no regression)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add atr_buffer_* fields to MDMV2Config and update presets** - `a147db7` (feat)
2. **Task 2: Add Indicators.add_violation_threshold_column static method** - `0a37727` (feat)

## Files Created/Modified

- `strategies/mdm_hybrid/config.py` - 4 new atr_buffer_* fields + 3 validation assertions + preset updates
- `strategies/mdm_hybrid/indicators.py` - add_violation_threshold_column() static method after add_atr_column
- `docs/rules_mdm_hybrid.md` - section XVI ATR Buffer Zone (Code-Docs Sync per CLAUDE.md)

## Decisions Made

- Used unconditional assertions for k/period/consecutive_days validation (not gated on enabled=True) so invalid configs fail fast regardless of flag state
- `atr_buffer_period=14` default matches `atr_period=14` stop-loss default numerically, but they are independent parameters swept separately in Phase 40
- docs/rules_mdm_hybrid.md updated in same commit batch per CLAUDE.md Code-Docs Sync Rule

## Deviations from Plan

None - plan executed exactly as written. The Code-Docs Sync Rule addition to docs/rules_mdm_hybrid.md was required by CLAUDE.md and was bundled into Task 1's commit.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (engine integration) can proceed: MDMV2Config has the fields, Indicators has the method
- Plan 03 (regression test) can proceed: config backward-compat fields in place
- Key contract: engine reads `config.atr_buffer_enabled`, calls `Indicators.add_violation_threshold_column(df, k=config.atr_buffer_k, period=config.atr_buffer_period)` in precompute block, position manager reads `violation_threshold` column + checks `atr_buffer_consecutive_days`-day streak

---
*Phase: 38-atr-buffer-zone-module*
*Completed: 2026-04-15*
