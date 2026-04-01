---
phase: 25-ma50-200dma-review
plan: 02
subsystem: strategy
tags: [mdm_v2, 200dma, ma50, ftd_signal, position_manager, engine, indicators]

# Dependency graph
requires:
  - phase: 25-01
    provides: "ma50_breakout_enabled and ma200_enabled config flags, add_sma200_column indicator method"
provides:
  - "check_200dma_breakout method in FTDSignalDetector (signal_type=200DMA)"
  - "MA50 breakout gated on ma50_breakout_enabled config flag in engine"
  - "200dma BUY crossover path in engine when ma200_enabled=True"
  - "200dma SELL breakdown path in V2PositionManager when ma200_enabled=True"
  - "sma200 parameter threaded through engine -> process_day"
  - "is_200dma_breakout result column in engine output DataFrame"
affects: [25-03, mdm_v2_engine, position_manager, ftd_signal]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Config-gated signal paths: new signal types wrapped in if config.flag check before calling detector"
    - "sma200 passed as None default to process_day - backward compatible optional parameter"

key-files:
  created: []
  modified:
    - strategies/mdm_v2/ftd_signal.py
    - strategies/mdm_v2/mdm_v2_engine.py
    - strategies/mdm_v2/position_manager.py
    - tests/test_ma50_review.py
    - docs/rules_mdm_v2.md

key-decisions:
  - "200dma breakout uses same correction threshold as MA50 breakout (ma50_breakout_correction=-0.06) for consistency"
  - "sma200 passed as None default to process_day - backward compat, no behavior change for existing callers"
  - "200dma SELL uses elif chain after MA50 SELL - only one SELL path fires per day"
  - "test_hybrid_matches_v2_on_nasdaq pre-existing failure (88.49% < 95%) logged as deferred, not caused by Plan 02"

patterns-established:
  - "Config-gated signal: wrap check in `if not is_ftd and self.config.flag_enabled:` pattern"
  - "New optional engine data columns: add result column init to False, set True inside detection block"

requirements-completed: [MAREVIEW-01, MAREVIEW-02]

# Metrics
duration: 13min
completed: 2026-04-01
---

# Phase 25 Plan 02: MA50/200dma Review — Engine Wiring Summary

**200dma BUY crossover and SELL breakdown wired into V2 engine with MA50 breakout config-gated; all scenarios 4 and 5 now functional**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-01T05:49:19Z
- **Completed:** 2026-04-01T06:02:19Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- MA50 breakout buy signal gated on `ma50_breakout_enabled` flag — setting False disables it without regression
- `check_200dma_breakout` method added to FTDSignalDetector with `signal_type="200DMA"`
- 200dma BUY path wired in engine: computes sma200/prev_sma200, checks crossover when `ma200_enabled=True`
- 200dma SELL breakdown path added to V2PositionManager as elif after MA50 SELL block
- `sma200` parameter threaded from engine row to `process_day()` with None default for backward compat
- 2 new tests added: `test_engine_gates_ma50_breakout`, `test_200dma_replacement_signals`
- Full test suite: 8/8 MA50 review tests pass; pre-existing hybrid test failure documented as deferred

## Task Commits

1. **Task 1: Add 200dma breakout method and gate MA50 breakout in engine** - `110b602` (feat)
2. **Task 2: Add 200dma SELL trigger path and enhance tests** - included in `110b602` (single commit - tasks share verification)

**Plan metadata (docs):** `15325b2` (docs: rules_mdm_v2 sync + deferred items)

## Files Created/Modified
- `strategies/mdm_v2/ftd_signal.py` - Added `check_200dma_breakout` method after `check_ma50_breakout`
- `strategies/mdm_v2/mdm_v2_engine.py` - MA50 breakout gate, sma200 indicator wiring, 200dma BUY path, sma200 arg to process_day
- `strategies/mdm_v2/position_manager.py` - Added `sma200` param to `process_day`, added 200dma SELL elif block
- `tests/test_ma50_review.py` - Added MDMV2Engine import, `test_engine_gates_ma50_breakout`, `test_200dma_replacement_signals`
- `docs/rules_mdm_v2.md` - Added ma50_breakout_enabled/ma200_enabled to params table, Plan 02 wiring docs (Section updated)

## Decisions Made
- 200dma breakout reuses `ma50_breakout_correction` threshold (-6%) — same depth requirement for both MA50 and 200dma crossovers, consistent and no new config needed
- `sma200=None` default in `process_day` — backward compatible, no callers need updating unless they want 200dma SELL
- 200dma SELL uses elif (not separate if) after MA50 SELL — guarantees only one SELL path fires per day; when MA50 SELL disabled and 200dma enabled, the elif chain correctly routes to 200dma SELL

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pre-existing test failure (out of scope):**
`tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq` fails with 88.49% < 95% BUY state overlap.
Confirmed pre-existing by running with git stash (same failure before Plan 02 changes).
Likely introduced by Phase 23 fail-safe changes. Logged in `deferred-items.md`.

## Next Phase Readiness
- Plan 03 (A/B validation script) can now run all 5 scenarios: baseline, no-MA50-sell, no-MA50-breakout, no-MA50-all, 200dma-replace
- All config flags, indicators, BUY paths, and SELL paths are functional
- Default config produces identical output to pre-change baseline (no regression confirmed by full suite)

## Self-Check: PASSED

All expected files found. Commits 110b602 and 15325b2 verified in git log. 8/8 MA50 review tests pass, 46/46 related V2 engine tests pass.

---
*Phase: 25-ma50-200dma-review*
*Completed: 2026-04-01*
