---
phase: 41-ab-walk-forward-validation
plan: 01
subsystem: validation
tags: [python, pandas, numpy, hybrid-engine, validation, scaffolding, vn30]

# Dependency graph
requires:
  - phase: 40-grid-search-sweeps
    provides: v9_atr_best.json + v9_dd_best.json locked params, compute_metrics schema (Sharpe_rf3 + whipsaw columns), validate_combined_v6.py skeleton template
provides:
  - analysis/validate_v9.py scaffold with 5 functions (load_locked_params, run_engine, compute_metrics, build_scenario_configs, main)
  - 4-scenario MDMV2Config builder (baseline / +ATR / +DD / +both) via dataclasses.replace(VN30_PRESET, ...)
  - 11-key metrics schema (Phase 40 parity + total_return_pct extension for A/B readability)
  - Module constants for walk-forward boundaries (TRAIN_END=2021-12-31, TEST_START=2022-01-01, DEGRADATION_THRESHOLD=0.50)
  - Stub main() producing output/v9_ab_comparison.txt with locked-params echo + scenario list
affects: [41-02, 42-documentation-and-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dataclass replace-for-scenario-mutation (Phase 40 D-04 pattern reused)"
    - "Fail-loud JSON loader with remediation message (Phase 40 D-13 handoff continuity)"
    - "Log-to-list report capture (v6 precedent)"

key-files:
  created:
    - analysis/validate_v9.py (scaffold; 324 lines with compute_metrics + scenario builder + main stub)
    - output/v9_ab_comparison.txt (stub report with locked-params echo + scenarios built line; Plan 41-02 fills remainder)
  modified: []

key-decisions:
  - "compute_metrics extends Phase 40 sweep_v9_atr schema with total_return_pct key for A/B table readability (D-03 rationale)"
  - "load_locked_params returns two separate dicts rather than merged — scenario builder must drive +ATR scenario from atr_params, not from dd_params['atr_buffer_*'] provenance echo"
  - "Runtime assert df_full['date'].max() >= '2025-12-01' allows any 2025-2026 data cutoff without failing while catching truncated-data regressions"
  - "refined_dd_large_vol_rule and refined_dd_small_vol_lookback stay at VN30_PRESET defaults ('vol_ma20', 50) per D-06 — never overridden in any dataclasses.replace call"

patterns-established:
  - "Scaffolding-then-fill split for large validation scripts: Plan 01 ships parseable skeleton + helpers; Plan 02 focuses on report-shaping + CSV writing + run/verify (context budget hygiene)"
  - "Main() stub produces a partial-but-valid artifact so Plan 02 starting point is a running end-to-end pipeline, not an import-error recovery job"

requirements-completed: [VAL-01, VAL-04]

# Metrics
duration: ~8min
completed: 2026-04-21
---

# Phase 41 Plan 01: Validate v9.0 Scaffold Summary

**analysis/validate_v9.py scaffold with 5 functions (load_locked_params, run_engine, compute_metrics, build_scenario_configs, main stub) producing stub output/v9_ab_comparison.txt — Plan 41-02 fills VAL-01..04 report sections**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-21T03:44Z
- **Completed:** 2026-04-21T03:52:11Z
- **Tasks:** 2
- **Files created:** 2 (validate_v9.py + stub v9_ab_comparison.txt)

## Accomplishments
- Scaffolding script `analysis/validate_v9.py` (324 lines) parses cleanly and runs end-to-end with exit code 0
- Loaded Phase 40 locked params from `output/v9_atr_best.json` (k=1.0, N=20, m=2) and `output/v9_dd_best.json` (large_drop=-0.007, small_drop=-0.003, percentile=3)
- Built all 4 D-05 scenarios via `dataclasses.replace(VN30_PRESET, ...)`: `baseline`, `+ATR`, `+DD`, `+both`
- Loaded full VN30 data (2803 rows, 2015-01-05 -> 2026-03-31) confirming VAL-01 full-period coverage precondition met
- 11-key metrics schema ready (sharpe_rf3, cagr_pct, max_dd_pct, total_return_pct, transitions, sell_count, ma50_breakdown_sell_share, buy_count, buy_pct, cash_pct, sell_pct)
- Stub report saved to `output/v9_ab_comparison.txt`; Plan 41-02 appends A/B table, walk-forward, whipsaw diagnostic, production candidate

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold with imports, constants, load_locked_params, run_engine** — `7648e71` (feat)
2. **Task 2: Add compute_metrics, build_scenario_configs, main() stub** — `481d587` (feat)

## Files Created/Modified
- `analysis/validate_v9.py` — Phase 41 validation script scaffold; 5 functions, 7 module constants, 4-scenario builder, stub main()
- `output/v9_ab_comparison.txt` — Stub report (Plan 41-02 fills VAL-01..04 sections + production candidate)

## Decisions Made

- **D-02 remediation strings preserved verbatim** — FileNotFoundError messages point to exact Phase 40 remediation commands (`analysis/sweep_v9_atr.py` + `analysis/select_v9_best.py --stage atr/dd`), ensuring downstream failures self-document the fix path
- **Dual-JSON loader returns tuple not merged dict** — atr_params and dd_params are separate so `build_scenario_configs` must pull ATR overrides from atr_params even when dd_best.json echoes ATR provenance. Prevents accidental single-source-of-truth collapse
- **Metrics schema adds `total_return_pct`** vs Phase 40 sweep_v9_atr.py — A/B report readability requirement; sweep files optimize for grid-CSV compactness while validation report optimizes for human-readable pairwise deltas
- **Runtime data-coverage assert uses `>= 2025-12-01`** — lets loader return 2026-03-31 or beyond without failing, but fails loud if loader truncates before 2026 arrives in VAL-01 full-period coverage
- **Plan-split rationale** — Task 1 (skeleton) and Task 2 (fill-in) are atomic units so Plan 41-02 starts from a known-good running stub, not from import-error recovery. Plan 41-02 context budget freed for CSV writing + production candidate decision logic

## Deviations from Plan

None — plan executed exactly as written. Both tasks followed the embedded action blocks verbatim; every acceptance-criteria grep pattern returned the expected count (including 4 `replace(VN30_PRESET` calls verified via multiline-aware grep after the default single-line pass returned 1 due to the `\s*` pattern spanning lines in the source).

## Issues Encountered

- **Windows line-ending LF->CRLF auto-conversion warning** on both commits — benign git noise, no actual content mutation. File parses and runs correctly under `uv run python`.

## Next Phase Readiness

- **Ready for Plan 41-02:** Skeleton is a running end-to-end pipeline. Plan 41-02 inherits:
  - 4 scenarios in scenarios dict, keyed `['baseline', '+ATR', '+DD', '+both']`
  - `run_engine(df, cfg)` helper with HybridConfig(two_phase_enabled=True, filter_enabled=False) pre-wired
  - `compute_metrics(results)` with full 11-key schema including Phase 40 whipsaw columns
  - `log()` closure and `lines` list pattern — Plan 41-02 appends report sections then replaces the final write
  - `SCENARIOS_CSV` constant pre-declared — Plan 41-02 writes the per-scenario CSV
  - Runtime data-coverage assert already in place — Plan 41-02 doesn't need to re-validate
- **No blockers.** All Phase 40 JSON artifacts present, VN30 data loads 2015→2026, dataclasses.replace successfully constructs all 4 MDMV2Config instances.

## Self-Check: PASSED

Verified existence of all claimed artifacts:
- `analysis/validate_v9.py`: FOUND
- `output/v9_ab_comparison.txt`: FOUND (stub, 10 lines)
- Task commit `7648e71`: FOUND in git log
- Task commit `481d587`: FOUND in git log
- Functions `load_locked_params, run_engine, compute_metrics, build_scenario_configs, main`: all parseable via ast
- Script runs end-to-end with exit code 0 under `uv run python analysis/validate_v9.py`
- Plan-level CONTEXT.md decision fidelity: D-01 (single file), D-02 (2 FileNotFoundError raises), D-05 (4 scenarios), D-06 (large_vol_rule + lookback not overridden), D-14 (sys.exit(0) unconditional) — all verified

---
*Phase: 41-ab-walk-forward-validation*
*Completed: 2026-04-21*
