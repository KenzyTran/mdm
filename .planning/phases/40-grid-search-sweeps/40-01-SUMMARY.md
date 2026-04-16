---
phase: 40-grid-search-sweeps
plan: 01
subsystem: analysis
tags: [grid-search, atr-buffer, vn30, sweep, backtest, whipsaw]

requires:
  - phase: 38-atr-buffer-zone-module
    provides: ATR buffer zone feature flag + m-day consecutive-day trigger in HybridEngine
  - phase: 39-refined-distribution-day-module
    provides: refined_dd_enabled feature flag (pinned False so stage-1 isolates ATR)
provides:
  - analysis/sweep_v9_atr.py -- serial 36-run ATR grid-search script (4 k x 3 periods x 3 consecutive_days)
  - output/v9_atr_sweep.csv -- 36 rows with config + core metrics + whipsaw diagnostics + error schema (D-18)
  - OOS-guard runtime assertion pattern (df['date'].max() <= TRAIN_END) for in-sample sweeps
  - SummaryError exception class guarding top-5 NaN winners in selection
affects: [phase-40-02-selection, phase-40-03-dd-sweep, phase-41-validation]

tech-stack:
  added: []
  patterns:
    - "Extended Phase 32 compute_metrics() with Sharpe_rf3 (rf=3%) + whipsaw columns"
    - "dataclasses.replace(VN30_PRESET, ...) per-cell immutable config mutation"
    - "Serial tqdm loop with fail-loud-per-config try/except (D-10)"
    - "Hard-coded train window + runtime OOS assertion (D-12, SWEEP-04)"

key-files:
  created:
    - analysis/sweep_v9_atr.py
  modified: []

key-decisions:
  - "Extended core metrics with Sharpe_rf3 formula (ann_return - 0.03) / ann_vol per Phase 32 D-19 convention, matching sweep_vn30_params.py lineage"
  - "ma50_breakdown_sell_share treats both 'SELL signal: MA50 breakdown' (classic) and 'SELL signal: ATR buffer zone' (buffered) as MA50-breakdown-path hits -- both flow from the same ma50_sell_enabled branch in position_manager.py:280-309"
  - "Top-5 NaN guard fires via SummaryError after CSV is written -- CSV inspection remains possible post-failure for debugging"
  - "Error column defaults to empty string so pandas writes an explicit empty field; CSV round-trip yields NaN which is semantically equivalent (no error)"

patterns-established:
  - "Sequential-sweep script skeleton: load once -> OOS assert -> build_indicator_dataframe -> dataclasses.replace loop -> compute_metrics -> CSV with canonical col_order + NaN top-5 guard"
  - "Whipsaw diagnostic columns (sell_count, ma50_breakdown_sell_share, *_pct) travel with every sweep CSV so Phase 41 VAL-04 can plot whipsaw reduction without a second run"

requirements-completed: [SWEEP-01, SWEEP-04]

duration: 4min
completed: 2026-04-16
---

# Phase 40 Plan 01: ATR Buffer Grid-Search Sweep Summary

**36-run serial ATR grid search on VN30 train window 2015-2021 producing `output/v9_atr_sweep.csv` with extended whipsaw-diagnostic schema; top config `atr-k1.0-N20-m2` beats baseline at Sharpe_rf3=0.76, CAGR=14.14%, MaxDD=-16.69%.**

## Performance

- **Duration:** 4 min (script execution + commit)
- **Started:** 2026-04-16T07:30:43Z
- **Completed:** 2026-04-16T07:35:07Z
- **Tasks:** 1
- **Files modified:** 1 created (`analysis/sweep_v9_atr.py`, 221 lines)
- **Sweep runtime:** 128s wall clock for 36 runs (~3.6s/config)

## Accomplishments

- `analysis/sweep_v9_atr.py` exercises the full 4x3x3 ATR grid (`k ∈ {0.3, 0.5, 0.7, 1.0}`, `N ∈ {10, 14, 20}`, `m ∈ {1, 2, 3}`) per D-07, with `atr_buffer_enabled=True` and `refined_dd_enabled=False` per D-05 so only ATR buffer impact is measured.
- `output/v9_atr_sweep.csv` written with 36 rows and exact 15-column canonical order from D-18 (config fields -> core metrics -> whipsaw diagnostics -> error).
- Runtime OOS guard (line 141): `assert df['date'].max() <= pd.Timestamp(TRAIN_END)` satisfies SWEEP-04 with zero CLI-override surface.
- Top-5 NaN guard (line 211): `SummaryError` prevents broken configs from silently becoming selection winners in Plan 40-02.
- All 36 configs completed without error (0 NaN rows, 0 traceback rows).

## Task Commits

Single task was committed atomically:

1. **Task 1: Create analysis/sweep_v9_atr.py with 36-run ATR grid search and extended-schema CSV output** - `19bd6ad` (feat)

**Plan metadata commit:** will be appended with this SUMMARY.md, STATE.md, and ROADMAP.md updates.

## Files Created/Modified

- `analysis/sweep_v9_atr.py` (new, 221 lines) -- serial 36-run ATR grid-search script producing `output/v9_atr_sweep.csv`

## Verification Line Numbers

From `analysis/sweep_v9_atr.py`:

| What | Line | Snippet |
| :--- | :---: | :--- |
| SummaryError class | 48 | `class SummaryError(RuntimeError):` |
| compute_metrics() | 52 | `def compute_metrics(results: pd.DataFrame) -> dict:` |
| main() | 136 | `def main():` |
| **OOS-guard assertion (D-12)** | **141** | `assert df['date'].max() <= pd.Timestamp(TRAIN_END), \` |
| k grid (D-07) | 147 | `k_values = [0.3, 0.5, 0.7, 1.0]` |
| period grid (D-07) | 148 | `period_values = [10, 14, 20]` |
| consecutive_days grid (D-07) | 149 | `consecutive_days_values = [1, 2, 3]` |
| ATR flip ON (D-05) | 160 | `atr_buffer_enabled=True,` |
| refined_dd pinned OFF (D-05) | 164 | `refined_dd_enabled=False,` |
| Top-5 NaN guard (D-10) | 211 | `if top5['sharpe_rf3'].isna().any():` |

## First Run Results

**Row count:** 36 (100% grid coverage, 0 errors, 0 NaN)

**Top 10 by sharpe_rf3:**

| config_name       |   k | N  | m |  sharpe_rf3 | cagr_pct | max_dd_pct | trans | sell_ct | ma50_share |
| :---------------- | --: | -: | -: | ----------: | -------: | ---------: | ----: | ------: | ---------: |
| atr-k1.0-N20-m2   | 1.0 | 20 | 2 |      0.7596 |    14.14 |     -16.69 |   125 |      32 |        1.0 |
| atr-k0.5-N14-m2   | 0.5 | 14 | 2 |      0.7513 |    14.04 |     -20.88 |   140 |      39 |        1.0 |
| atr-k0.3-N20-m1   | 0.3 | 20 | 1 |      0.7308 |    14.34 |     -15.31 |   154 |      48 |        1.0 |
| atr-k0.5-N10-m2   | 0.5 | 10 | 2 |      0.7270 |    13.69 |     -20.88 |   141 |      40 |        1.0 |
| atr-k0.3-N14-m1   | 0.3 | 14 | 1 |      0.7131 |    14.06 |     -15.31 |   156 |      49 |        1.0 |
| atr-k0.3-N10-m1   | 0.3 | 10 | 1 |      0.7131 |    14.06 |     -15.31 |   156 |      49 |        1.0 |
| atr-k0.5-N20-m1   | 0.5 | 20 | 1 |      0.7084 |    13.93 |     -15.31 |   148 |      45 |        1.0 |
| atr-k0.5-N10-m1   | 0.5 | 10 | 1 |      0.6936 |    13.69 |     -16.36 |   146 |      44 |        1.0 |
| atr-k0.5-N10-m3   | 0.5 | 10 | 3 |      0.6933 |    13.29 |     -15.29 |   132 |      34 |        1.0 |
| atr-k0.5-N14-m3   | 0.5 | 14 | 3 |      0.6933 |    13.29 |     -15.29 |   132 |      34 |        1.0 |

**Summary distribution (36 rows):**
- `sharpe_rf3`: min 0.4463, max 0.7596, median 0.655
- `cagr_pct`: min 9.26, max 14.34
- `max_dd_pct`: min -24.25, max -15.29 (all passing v9.0 MaxDD ≤ -30% constraint)
- `ma50_breakdown_sell_share`: 1.0 uniformly (every SELL in the sweep flowed through the ma50_sell_enabled branch, as expected when fail_safe_enabled=True and deterioration days stay at 20)

**Observation for downstream (Plan 40-02 selection):**
- Every config in the sweep passes the MaxDD ≤ -30% hard constraint, so the selection algorithm in plan 40-02 will definitely have a non-empty candidate set.
- Top configs cluster around moderate k with longer period (N=20) — k=1.0/N=20/m=2 edges out k=0.5/N=14/m=2 primarily on MaxDD (-16.69 vs -20.88), consistent with the "wider buffer + slower trigger = fewer false SELL" hypothesis driving v9.0.

## Decisions Made

None beyond the scope already framed in Phase 40 D-01..D-22. Plan executed exactly as specified:
- dataclasses.replace on VN30_PRESET (D-04)
- Sharpe_rf3 per Phase 32 D-19 convention (rf=3%, daily_returns.pct_change().dropna().std() x sqrt(252))
- Canonical column order from D-18
- tqdm progress bar, no multiprocessing (D-09)
- Error column left empty (not NaN) in source dict; pandas CSV round-trip converts to NaN, which is semantically equivalent

## Deviations from Plan

None - plan executed exactly as written.

All acceptance criteria from the plan's `<acceptance_criteria>` block passed on first run:
- Script parses as valid Python.
- Literal strings (`TRAIN_START`, `TRAIN_END`, `atr_buffer_enabled=True`, `refined_dd_enabled=False`, OOS assertion) all present.
- Grid literals present.
- No `multiprocessing` imports.
- Both `SELL signal: MA50 breakdown` and `SELL signal: ATR buffer zone` literals present.
- `main`, `compute_metrics`, `SummaryError` all defined.
- `uv run python analysis/sweep_v9_atr.py` completed in 128s, produced `output/v9_atr_sweep.csv`.
- CSV row count = 36; column order matches expected list exactly.
- All three grid uniques match (k, period, consecutive_days).
- Top-5 by sharpe_rf3 has zero NaN (SummaryError not raised).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `output/v9_atr_sweep.csv` is the input for Plan 40-02 (`analysis/select_v9_best.py --stage atr`).
- `ma50_breakdown_sell_share` column pre-computed for Phase 41 VAL-04 whipsaw diagnostic.
- All configs pass the MaxDD ≤ -30% hard constraint -- selection will produce a non-empty candidate set.
- Zero blockers; Plan 40-02 can proceed immediately.

## Self-Check: PASSED

**File existence check:**
- FOUND: `analysis/sweep_v9_atr.py`
- FOUND: `output/v9_atr_sweep.csv`

**Commit existence check:**
- FOUND: `19bd6ad` (feat(40-01): add ATR buffer grid-search sweep script)

---
*Phase: 40-grid-search-sweeps*
*Plan: 01*
*Completed: 2026-04-16*
