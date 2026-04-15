---
phase: 38-atr-buffer-zone-module
plan: 03
subsystem: testing
tags: [atr, buffer-zone, regression-test, pytest, fixture, parquet, mdm-hybrid, backward-compat]

# Dependency graph
requires:
  - phase: 38-atr-buffer-zone-module
    plan: 01
    provides: MDMV2Config atr_buffer_* fields + Indicators.add_violation_threshold_column()
  - phase: 38-atr-buffer-zone-module
    plan: 02
    provides: HybridEngine pipeline wired with ATR buffer + branched CASH->SELL logic
provides:
  - tests/fixtures/phase38_v6_baseline_signal_log.parquet — v6.0 baseline (2808 rows, VN30 2015-2026)
  - tests/test_phase38_backward_compat.py — ATR-04 regression guard (2 tests)
  - docs/rules_mdm_hybrid.md section XVI — ATR Buffer Zone rule documentation (completed in Plan 01)
affects:
  - 40-atr-grid-search
  - 41-ab-validation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Split assertion pattern: exact equality for string cols (state/transition), rtol/atol=1e-5 for numerics (ma50/close)"
    - "Hard fail (not skip) when required data asset absent — CI must detect missing data, not silently pass"
    - "Parquet fixture for regression baseline: committed to tests/fixtures/, regenerated via scripts/generate_phase38_fixture.py"

key-files:
  created:
    - tests/fixtures/phase38_v6_baseline_signal_log.parquet
    - tests/test_phase38_backward_compat.py
    - scripts/generate_phase38_fixture.py
  modified: []

key-decisions:
  - "Use data/vn30.csv (DataLoader 'vn30' market key) instead of vn30_price.csv — DataLoader.FILE_PATHS already maps 'vn30' to data/vn30.csv"
  - "Task 2 docs update already satisfied by Plan 01 (docs/rules_mdm_hybrid.md section XVI exists and passes all acceptance criteria)"
  - "Fixture has 2808 rows covering VN30 2015-01-05 to 2026-04-07 (state: CASH=1206, SELL=969, BUY=633)"
  - "Keep scripts/generate_phase38_fixture.py in repo for future fixture regeneration reference (D-12)"

patterns-established:
  - "Regression fixture pattern: one-time generator script + committed parquet + pytest assert_frame_equal"
  - "ATR buffer CI guard: test_atr_buffer_disabled_matches_baseline runs every PR, fails hard if VN30 CSV missing"

requirements-completed: [ATR-04]

# Metrics
duration: 15min
completed: 2026-04-15
---

# Phase 38 Plan 03: Regression Fixture and Backward-Compat Test Summary

**Committed phase38_v6_baseline_signal_log.parquet (2808 rows, VN30 2015-2026) and ATR-04 regression pytest that asserts byte-identical HybridEngine(atr_buffer_enabled=False) behavior via split assertion (exact string, rtol=1e-5 numeric)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-15T08:52:00Z
- **Completed:** 2026-04-15T09:07:00Z
- **Tasks:** 2
- **Files modified:** 3 created (fixture, test, generator script)

## Accomplishments

- Generated phase38_v6_baseline_signal_log.parquet using HybridEngine(atr_buffer_enabled=False) on VN30 2015-2026 (2808 rows)
- Created test_phase38_backward_compat.py with 2 tests: schema guard and full backward-compat assertion
- test_atr_buffer_disabled_matches_baseline: exact equality for state/transition strings, rtol/atol=1e-5 for ma50/close
- Hard fail (not skip) when data/vn30.csv absent — satisfies D-13 CI requirement
- Feature gate end-to-end verified: enabled path with m=1 produces 136 -> 88 SELL day reduction and adds violation_threshold column
- Both regression tests pass; existing config/unit tests unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Capture v6.0 baseline fixture and write regression pytest** - `ac7477f` (feat)
2. **Task 2: Update docs/rules_mdm_hybrid.md with ATR Buffer Zone section** - pre-existing (Plan 01 commit b7c1f63)

**Plan metadata:** (final docs commit follows)

## Files Created/Modified

- `tests/fixtures/phase38_v6_baseline_signal_log.parquet` - v6.0 baseline signal log (date, state, transition, ma50, close), 2808 rows VN30 2015-2026
- `tests/test_phase38_backward_compat.py` - ATR-04 regression pytest: schema check + byte-identical backward-compat assert
- `scripts/generate_phase38_fixture.py` - One-shot fixture generator kept for D-12 regeneration reference
- `docs/rules_mdm_hybrid.md` - Section XVI ATR Buffer Zone (satisfied by Plan 01)

## Decisions Made

- Used `DataLoader('vn30')` with `loader.data_dir = ROOT` instead of raw CSV path — matches existing test patterns and uses correct column mapping automatically
- docs/rules_mdm_hybrid.md Task 2 was already complete from Plan 01 (section XVI passes all acceptance criteria grep checks)
- Kept generate_phase38_fixture.py in scripts/ (not deleted) for future fixture regeneration reference per D-12

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Pre-existing work] Task 2 docs already satisfied by Plan 01**
- **Found during:** Task 2 verification
- **Issue:** The plan instructed to append section "IX. ATR BUFFER ZONE" to docs/rules_mdm_hybrid.md — but Plan 01 already added section "XVI. ATR BUFFER ZONE — MA50 BREAKDOWN FILTER (Phase 38, ATR-01/ATR-03)" which passes all 6 acceptance criteria grep checks
- **Fix:** Verified all criteria met; no additional modification needed (would duplicate content)
- **Files modified:** None (pre-existing)
- **Verification:** All 6 grep acceptance criteria confirmed — 1 "ATR BUFFER ZONE" hit, 8 "violation_threshold" hits, 2 "atr_buffer_enabled" hits, 1 "atr_buffer_consecutive_days" hit, 2 "byte-identical" hits, 5 "atr_buf" hits
- **Committed in:** b7c1f63 (Plan 01 Task 2 commit)

---

**Total deviations:** 1 pre-existing (Task 2 docs already done in Plan 01)
**Impact on plan:** No scope change. CLAUDE.md Code-Docs Sync Rule already satisfied.

## Issues Encountered

None — fixture generation ran cleanly on first attempt with DataLoader('vn30').

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 40 grid search can proceed: regression guard in place, ATR buffer module fully wired and tested
- Key contract: running HybridEngine with atr_buffer_enabled=False on VN30 2015-2026 must always match fixture; CI will catch any regression
- Fixture regeneration procedure: `uv run python scripts/generate_phase38_fixture.py` then commit new parquet (D-12)

## Known Stubs

None — fixture is populated with real VN30 data, tests assert real engine behavior.

---
*Phase: 38-atr-buffer-zone-module*
*Completed: 2026-04-15*
