---
phase: 37-backtest-validation
plan: "02"
subsystem: analysis
tags: [sweep, momentum, rs, formula-selection, backtest, vn100]

# Dependency graph
requires:
  - phase: 37-01
    provides: run_v8_backtest with formula kwarg in _vn100_pipeline.py
provides:
  - 216-config in-sample sweep (2016-2018) comparing IBD Weighted ROC vs ROC-126
  - locked_params_v8.json — winning formula + config selected by highest Sharpe_rf3
  - sweep_v8_results.csv — full 216-row comparison table
affects:
  - 37-03 (OOS validation consumes locked_params_v8.json)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase 32 sweep pattern: sys.path injection + top-level worker + Pool(cpu_count()-1) + tqdm fallback"
    - "Single precompute_static call in main process before Pool.map to prime parquet cache (avoids N-way DB race)"

key-files:
  created:
    - analysis/sweep_vn100_v8.py
    - docs/audits/phase37/sweep_v8_results.csv
    - docs/audits/phase37/locked_params_v8.json
  modified: []

key-decisions:
  - "roc126 wins in-sample (2016-2018): Sharpe_rf3=0.702, CAGR=11.3%, MaxDD=-8.5% vs weighted_roc Sharpe=0.576"
  - "Winner config: rs_formula=roc126, rs_threshold=70.0, n_within_high=0.10, hard_stop=0.08, slots=5, entry_option=A"
  - "Sanity gates: CAGR>=5% and MaxDD>=-30% applied before selecting winner — no fallback needed (215/216 configs passed)"
  - "1 ERROR row (first worker parquet race condition on cache prime) — acceptable, 215/216 valid results"

patterns-established:
  - "sweep_vn100_v8.py mirrors sweep_vn100.py structure exactly — same pattern for v8.0 formula sweep"

requirements-completed: [BT-01]

# Metrics
duration: 2min
completed: 2026-04-13
---

# Phase 37 Plan 02: In-Sample Formula Sweep Summary

**roc126 wins in-sample 2016-2018 with Sharpe_rf3=0.702 vs weighted_roc 0.576 — locked_params_v8.json written for OOS validation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-13T03:13:01Z
- **Completed:** 2026-04-13T03:15:12Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `analysis/sweep_vn100_v8.py` — 216-config in-sample sweep mirroring Phase 32 sweep_vn100.py pattern
- Executed sweep over 2016-2018: 215/216 configs completed successfully (1 first-worker parquet race error)
- roc126 formula dominates: best Sharpe_rf3=0.702, CAGR=11.3%, MaxDD=-8.5% vs weighted_roc best Sharpe=0.576
- Wrote `locked_params_v8.json`: rs_formula=roc126, rs_threshold=70.0, n_within_high=0.10, hard_stop=0.08, slots=5, entry_option=A

## Task Commits

Each task was committed atomically:

1. **Task 1: Create sweep_vn100_v8.py** - `1a4faef` (feat)
2. **Task 2: Run sweep and write locked_params_v8.json** - `50c698d` (feat)

**Plan metadata:** (docs commit — below)

## Files Created/Modified

- `analysis/sweep_vn100_v8.py` — 216-config in-sample sweep script for v8.0 formula selection (BT-01)
- `docs/audits/phase37/sweep_v8_results.csv` — 216 rows, all METRIC_COLS, both formula values
- `docs/audits/phase37/locked_params_v8.json` — winning config: roc126, rs_threshold=70, n_within_high=0.10, hard_stop=0.08, slots=5, entry=A

## Decisions Made

- **roc126 selected as winning formula** over IBD Weighted ROC. In-sample Sharpe gap is substantial (+0.13 Sharpe units). roc126 (single 6-month lookback) achieves cleaner signals than the multi-period weighted version on 2016-2018 VN100 data.
- **Winner config**: rs_threshold=70.0 (top 30%), n_within_high=0.10 (tight near-high filter), hard_stop=0.08 (standard), slots=5, entry_option=A (52w breakout).
- **Sanity gate outcome**: 215/216 configs passed CAGR>=5% + MaxDD>=-30% — market conditions 2016-2018 were favorable, no fallback needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- 1 ERROR row in sweep output: first worker encountered corrupted/incomplete parquet during initial parallel start (race condition between cache prime completion and first worker spawn). All 215 remaining configs completed normally. This is acceptable per plan ("failed configs logged and skipped, not abort").

## Next Phase Readiness

- `locked_params_v8.json` is ready — Plan 37-03 (OOS validation) can run immediately
- OOS period: 2019-2025 using roc126 formula with locked config
- Key comparison: v8.0 OOS Sharpe vs v7.0 baseline Sharpe=0.813 (CAGR=10.18%)

---
*Phase: 37-backtest-validation*
*Completed: 2026-04-13*
