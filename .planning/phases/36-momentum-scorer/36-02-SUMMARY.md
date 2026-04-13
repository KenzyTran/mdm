---
phase: 36-momentum-scorer
plan: 02
subsystem: strategy
tags: [momentum, pipeline, v8-backtest, run_v8_backtest, canslim-replacement, no-mysql]

# Dependency graph
requires:
  - phase: 36-01
    provides: apply_momentum_thresholds, MomentumScorerConfig
  - phase: 35-rs-computation
    provides: RS computation patterns (IBD Weighted ROC, n_prox)
  - phase: 31-portfolio-engine
    provides: PortfolioEngine (scorer_frame wire compat, REQUIRED_SCORER_COLS)
provides:
  - run_v8_backtest callable with MomentumScorerConfig + PortfolioConfig for Phase 37 sweep
  - build_momentum_raw_frame producing [date, ticker, n_prox, rs_rating] without DB
  - strategies/momentum package with full public exports
affects: [phase-37-sweep, v8-backtest-comparison]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "run_v8_backtest lazy-imports scorer to avoid circular deps and keep v7.0 path clean"
    - "momentum_raw_* cache prefix separates v8.0 from v7.0 canslim_raw_* cache (no stale schema)"
    - "build_momentum_raw_frame reuses same IBD Weighted ROC formula as build_canslim_raw_frame"
    - "precomputed dict accepted by both run_vn100_backtest and run_v8_backtest — fundamentals key optional in v8"

key-files:
  created: []
  modified:
    - analysis/_vn100_pipeline.py
    - strategies/momentum/__init__.py

key-decisions:
  - "Lazy import of momentum scorer inside run_v8_backtest (not top-level) — avoids circular deps, keeps v7.0 import path unchanged"
  - "build_momentum_raw_frame takes only panel (no precomputed) — no fundamentals needed, self-contained pure-price function"
  - "momentum_raw_* cache prefix avoids schema collision with canslim_raw_* (different columns: no eps_yoy_q0/eps_cagr_3y)"
  - "precomputed['fundamentals'] key NOT required by run_v8_backtest — fails only on universe/ohlc/mdm_gate missing"

requirements-completed: [MSCO-01, MSCO-02, MSCO-03, MSCO-04]

# Metrics
duration: 4min
completed: 2026-04-13
---

# Phase 36 Plan 02: Momentum Pipeline Wiring Summary

**run_v8_backtest + build_momentum_raw_frame added to _vn100_pipeline.py — RS+N scorer wired to PortfolioEngine, no MySQL, v7.0 intact**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-13
- **Completed:** 2026-04-13
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- `run_v8_backtest` added to `analysis/_vn100_pipeline.py` — accepts MomentumScorerConfig, reuses unchanged EntryEngine + PortfolioEngine (MSCO-03)
- `build_momentum_raw_frame` added — pure price-based, computes n_prox + rs_rating (IBD Weighted ROC), no DB/EPS (MSCO-04)
- Cache uses `momentum_raw_*` prefix to avoid stale schema collision with v7.0 `canslim_raw_*` files
- `strategies/momentum/__init__.py` updated with full public exports: `apply_momentum_thresholds`, `MomentumScorerConfig`, `compute_rs_panel`, `get_rs_rankings`, `RSConfig`
- v7.0 functions `run_vn100_backtest`, `build_canslim_raw_frame`, `_apply_canslim_thresholds`, `precompute_static` untouched — Phase 37 can import both for A/B comparison
- All 13 scorer unit tests pass; import verification checks pass

## Task Commits

1. **Task 1: Add build_momentum_raw_frame and run_v8_backtest to pipeline** - `65114da` (feat)

## Files Created/Modified

- `analysis/_vn100_pipeline.py` — Added `run_v8_backtest` (v8.0 entry point, ~120 lines) + `build_momentum_raw_frame` (~80 lines) + updated `__all__`
- `strategies/momentum/__init__.py` — Added public exports for all momentum package modules

## Decisions Made

- Lazy import of momentum scorer inside `run_v8_backtest` avoids circular deps and keeps the v7.0 top-level import path clean
- `build_momentum_raw_frame` signature takes only `panel` (no `precomputed`) — pure price, self-contained, no fundamentals argument needed
- `momentum_raw_*` cache prefix: different columns from `canslim_raw_*` (no `eps_yoy_q0`, `eps_cagr_3y`) — separate prefix avoids stale parquet schema errors
- `precomputed["fundamentals"]` NOT required — v8.0 only validates `universe`, `ohlc`, `mdm_gate` keys

## Deviations from Plan

None — plan executed exactly as written. All v8.0 code added without touching v7.0 functions.

## Issues Encountered

None — verification checks passed on first run.

## User Setup Required

None — pure price-based computation, no external DB required.

## Next Phase Readiness

- Phase 37 sweep can call `run_v8_backtest(momentum_cfg, portfolio_cfg, entry_option, period)` directly
- Both `run_vn100_backtest` (v7.0) and `run_v8_backtest` (v8.0) importable from `analysis._vn100_pipeline` for A/B comparison
- `precompute_static` shared between both — compute once, pass as `precomputed=` to both entry points

## Known Stubs

None — all logic fully implemented. `build_momentum_raw_frame` computes real n_prox + rs_rating from panel data.

## Self-Check: PASSED

- FOUND: analysis/_vn100_pipeline.py
- FOUND: strategies/momentum/__init__.py
- FOUND: .planning/phases/36-momentum-scorer/36-02-SUMMARY.md
- FOUND commit: 65114da

---
*Phase: 36-momentum-scorer*
*Completed: 2026-04-13*
