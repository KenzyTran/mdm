---
phase: 33-out-of-sample-sensitivity
plan: 01
subsystem: backtest
tags: [canslim, portfolio, vn100, oos, cache, pipeline]

# Dependency graph
requires:
  - phase: 32-vn100-backtest-in-sample-sweep
    provides: locked_params_top3.json with rank-1 config for OOS use

provides:
  - Fixed _vn100_pipeline.py with mode-aware and date-range-aware cache keys
  - analysis/backtest_vn100_oos.py OOS script (2019-2025, rank-1 locked params)
  - docs/audits/phase33/oos_nav.csv (1749 rows daily NAV)
  - docs/audits/phase33/oos_trades.csv (62 trades)
  - docs/audits/phase33/oos_positions.csv
  - docs/audits/phase33/oos_metrics.json (CAGR, Sharpe_rf3, MaxDD, etc.)

affects:
  - 33-02-sensitivity (will use fixed precompute_static with mode param)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cache key = (mode, start, end) for precompute_static parquet files"
    - "Cache key = (min_date, max_date) derived from panel for canslim_raw parquet"
    - "Hard-coded PERIOD constants (no CLI args) per D-09 reproducibility convention"

key-files:
  created:
    - analysis/backtest_vn100_oos.py
    - docs/audits/phase33/oos_nav.csv
    - docs/audits/phase33/oos_trades.csv
    - docs/audits/phase33/oos_positions.csv
    - docs/audits/phase33/oos_metrics.json
  modified:
    - analysis/_vn100_pipeline.py

key-decisions:
  - "D-03 fixed: build_canslim_raw_frame cache path now derived from panel min/max date to prevent OOS from reusing in-sample fundamentals"
  - "D-06 fixed: precompute_static gains mode param (default current-vn100) so sensitivity runs across universe modes don't collide in cache"
  - "OOS results: CAGR=6.23%, Sharpe_rf3=0.448, MaxDD=-10.22%, 62 trades over 2019-2025"

patterns-established:
  - "precompute_static(period, mode='current-vn100') — mode is explicit, not hard-coded"
  - "canslim_raw_{min_d}_{max_d}.parquet — date-range-keyed cache prevents data contamination"

requirements-completed: [BT-03]

# Metrics
duration: 10min
completed: 2026-04-10
---

# Phase 33 Plan 01: OOS Backtest + Cache Fix Summary

**Fixed two cache contamination bugs (D-03, D-06) then ran OOS VN100 backtest 2019-2025 with rank-1 locked params producing CAGR=6.23%, Sharpe_rf3=0.448, MaxDD=-10.22%**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-10T03:05:00Z
- **Completed:** 2026-04-10T03:15:00Z
- **Tasks:** 2
- **Files modified:** 2 (pipeline fix + new OOS script + 4 audit CSV/JSON outputs)

## Accomplishments

- Fixed D-03: `build_canslim_raw_frame` now derives cache path from panel date range (`canslim_raw_{min_d}_{max_d}.parquet`) — OOS run will never silently reuse in-sample fundamentals
- Fixed D-06: `precompute_static` gains `mode` parameter (default `"current-vn100"`); all 5 cache filenames include `{mode}` segment to prevent collisions across universe modes in sensitivity runs
- OOS backtest 2019-2025 ran end-to-end with rank-1 locked config; produced 1749-row NAV series and 62-trade log with full metrics JSON

## OOS Results (BT-03)

| Metric | OOS (2019-2025) | In-Sample (2014-2018) |
|--------|-----------------|----------------------|
| CAGR | 6.23% | 3.79% |
| Sharpe_rf3 | 0.448 | 0.059 |
| MaxDD | -10.22% | -17.66% |
| MaxDD duration | 1007 days | 293 days |
| Hit rate | 45.16% | 50.00% |
| Num trades | 62 | 34 |
| Avg hold days | 33.0 | 36.8 |

OOS Sharpe (0.448) is substantially better than in-sample (0.059) — likely reflects favorable regime post-2019 and/or the locked params generalize well.

## Task Commits

1. **Task 1: Fix cache key bugs D-03 and D-06** - `75b53da` (fix)
2. **Task 2: Create OOS script and run backtest** - `db4cff5` (feat)

## Files Created/Modified

- `analysis/_vn100_pipeline.py` — Fixed D-03 (date-range cache) and D-06 (mode-aware cache) bugs
- `analysis/backtest_vn100_oos.py` — OOS script for 2019-2025 with rank-1 locked params
- `docs/audits/phase33/oos_nav.csv` — 1749-row daily NAV series
- `docs/audits/phase33/oos_trades.csv` — 62-trade log with buy/sell dates and P&L
- `docs/audits/phase33/oos_positions.csv` — Daily position snapshot
- `docs/audits/phase33/oos_metrics.json` — All required metrics (CAGR, Sharpe_rf3, MaxDD, etc.)

## Decisions Made

- Cache keys for `precompute_static` now include `{mode}` segment between the existing `{start}_{end}` parts; existing callers get `"current-vn100"` default and experience a one-time cache rebuild (desired to purge stale caches)
- `build_canslim_raw_frame` computes cache_path locally from `panel["date"].min/max()` — module-level `CANSLIM_RAW_CACHE` constant is kept for backward reference but is no longer used in the cache lookup/write path

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — both cache fixes applied cleanly, OOS backtest ran to completion on first attempt.

## Known Stubs

None — all metrics keys populated with real values from live DB query + 7-year backtest run.

## Next Phase Readiness

- Plan 33-02 (sensitivity matrix): `precompute_static(period, mode=...)` is now safe to call per universe mode; 3x3 sensitivity run can proceed without cache collision risk
- `oos_metrics.json` is available for BT-08 benchmark comparison in plan 33-02 or 33-03

---
*Phase: 33-out-of-sample-sensitivity*
*Completed: 2026-04-10*
