---
phase: 45-walk-forward-grid-search
plan: 01
subsystem: testing
tags: [walk-forward, grid-search, macro-filter, vn30, hybrid-engine, tqdm, dataclasses, oos-guard]

# Dependency graph
requires:
  - phase: 44-macro-filter-module
    provides: 10-field MDMV2Config macro tuple + MacroFilter class + HybridEngine wiring
  - phase: 43-canonical-liquidity-data-pipeline
    provides: data/vn_liquidity_proxy.csv + data/sbv_policy_events.csv (consumed transitively via MacroFilter)
  - phase: 42-baseline-reconciliation
    provides: output/v10_reconciled_baseline.json (context-only anchor, not a gate)
  - phase: 41-ab-walk-forward-validation
    provides: analysis/validate_v9.py::compute_metrics (reused verbatim via import per D-16)
provides:
  - analysis/walkforward_grid.py — staged-sweep orchestrator (Stage 1 DXY → Stage 2 EEM → Stage 3 SBV)
  - 7 importable functions (load_vn30_data, build_combo_grid, run_combo, select_winner, write_results_csv, write_best_json, main) + SummaryError class + _top3_nan_guard
  - Runtime D-14 OOS fence assertion at data-load boundary (fail-loud 'OOS leak' message)
  - D-15 df_override injection hook (consumed by Plan 02 pytest)
  - Hard-coded train/eval/OOS windows (no CLI overrides — reproducibility absolute per D-14)
affects: [45-02-oos-guard-pytest, 45-03-execute-sweep-commit-artifacts, 46-ab-oos-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-14 strict-less-than OOS fence — assert df['date'].max() < pd.Timestamp(OOS_FENCE)"
    - "D-04 single-run-and-slice — engine.run once on full period, slice 7 ways (train + 6 years) via pandas date masks"
    - "D-18 top-3 NaN guard — SummaryError if any of top-3 ranked accepted combos has NaN eval-year metric (Phase 40 D-10 precedent extended)"
    - "D-12 4-level ranking key — (-median_eval_cagr, -median_eval_sharpe, parsimony_distance, combo_id) deterministic"
    - "df_override-style test injection — function accepts pre-built DataFrame to bypass network-dependent data loaders during pytest"
    - "MACRO_CONFIG_FIELDS 10-tuple constant — single source of truth for full macro config serialization (CSV columns + JSON config entry + dataclasses.replace keys)"

key-files:
  created:
    - analysis/walkforward_grid.py (685 lines — orchestrator script)
  modified: []

key-decisions:
  - "Used strict < (not <=) for OOS_FENCE assertion so 2025-01-01-labeled rows fail loud; EVAL_END='2024-12-31' as inclusive top boundary keeps all 2024 walk-forward data in-scope"
  - "Factored a _load_reconciled_baseline_cagr helper returning NaN on any read failure (FileNotFoundError / KeyError / ValueError / JSONDecodeError) — baseline print is strictly informational per D-Claude-4, never gates the sweep"
  - "Populated MACRO_CONFIG_FIELDS module-level constant as single source of truth — used by write_results_csv COL_ORDER, _config_tuple JSON serialization, and implicitly by run_combo when seeding rows from cfg"
  - "Parsimony distance implemented as integer count of searched fields differing from VN30_PRESET defaults (simplest D-12 option), not scaled Euclidean — matches planner's explicit 'fewest non-default fields among ties at this depth' option"
  - "Kept NaN-aware median calculations throughout: median_eval_sharpe filters NaN per-year Sharpe, median_eval_max_dd_pct only medians over non-NaN years; JSON emits Python float('nan') which json.dump serializes as NaN (acceptable since D-11 payload is for Phase 46 consumption with pandas/numpy, not strict JSON)"
  - "Task 5 main() uses plain ASCII dashes in banners/logs (not Unicode box-drawing) to match project precedent in validate_v9.py/sweep_v9_atr.py and avoid Windows cp1252 stdout issues"

patterns-established:
  - "Staged sweep orchestrator single-file layout — module constants + SummaryError + load_vn30_data + build_combo_grid + run_combo + select_winner + write_results_csv + write_best_json + _top3_nan_guard + main (mirrors sweep_v9_atr.py / sweep_v9_dd.py structure, generalized to N-stage)"
  - "df_override hook for pytest — any phase that runs a data pipeline + assertion should expose an injection kwarg so pytest can validate assertion semantics on synthetic frames in < 1s"
  - "Signed degradation + median — per-year degradation_{y} = (cagr_train - cagr_y) / abs(cagr_train), then np.median preserves sign (positive = degraded, negative = improved); gate uses raw value not absolute"

requirements-completed: [WF-01, WF-02, WF-03]

# Metrics
duration: 6min 14s
completed: 2026-04-23
---

# Phase 45 Plan 01: Walk-Forward Grid Script Summary

**Single-file 685-line orchestrator `analysis/walkforward_grid.py` implementing 3-stage macro-filter grid sweep (27 DXY → 9 EEM → 3 SBV = 39 combos) with walk-forward CV INSIDE the sweep, D-14 OOS fence enforcement, and D-11 schema-versioned JSON output consumable by Phase 46.**

## Performance

- **Duration:** 6 min 14 s
- **Started:** 2026-04-23T08:28:55Z
- **Completed:** 2026-04-23T08:35:09Z
- **Tasks:** 5
- **Files modified:** 1 (created)

## Accomplishments

- Landed `analysis/walkforward_grid.py` (685 lines, all 7 required helpers callable) implementing every decision in 45-CONTEXT.md D-01..D-18 without touching engine / config / validate_v9 / docs / dashboard code.
- D-14 OOS fence is enforced at the runtime boundary (`assert df['date'].max() < pd.Timestamp(OOS_FENCE)` fails with the literal substring `"OOS leak"` that Plan 02's pytest greps for).
- D-16 metric-formula discipline honored: `compute_metrics` is imported verbatim from `analysis.validate_v9`, zero reimplementation — drift risk across Phase 41/42/45 eliminated by construction.
- D-18 top-3 NaN guard fires loud via `SummaryError` if any top-3 accepted combo has a NaN per-year CAGR — unsafe selections cannot silently win.
- D-15 test-injection hook (`load_vn30_data(df_override=...)`) is present and verified to raise `AssertionError('... OOS leak ...')` when handed a synthetic 2025-labeled DataFrame.
- Script is correct-by-construction (syntax-checked, all grids import to the exact 27 / 9 / 3 shapes) but intentionally does NOT execute the sweep — Plan 03 runs it to produce the actual `output/v10_grid_results.csv` + `output/v10_grid_best.json` artifacts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Module skeleton + OOS constants + SummaryError + compute_metrics import** — `6ccb5cb` (feat)
2. **Task 2: load_vn30_data helper (OOS-guarded, injectable for tests)** — `8ce8079` (feat)
3. **Task 3: build_combo_grid (3 stages × D-03 values) + run_combo (train + 6 eval slices)** — `097a7d5` (feat)
4. **Task 4: select_winner (D-12 ranking) + write_results_csv + write_best_json (D-11 schema)** — `9400fb7` (feat)
5. **Task 5: main() orchestrator — load data, run 3 stages serial, write outputs** — `9180905` (feat)

## Files Created/Modified

- `analysis/walkforward_grid.py` — NEW, 685 lines. Module docstring covers WF-01/02/03 scope. Constants: `TRAIN_START=2015-01-01`, `TRAIN_END=2018-12-31`, `EVAL_END=2024-12-31`, `OOS_FENCE=2025-01-01`, `EVAL_YEARS=[2019..2024]`, `DEGRADATION_THRESHOLD=0.30`, `MEDIAN_CAGR_FLOOR=0.0`. 7 top-level callables (main, load_vn30_data, build_combo_grid, run_combo, select_winner, write_results_csv, write_best_json) + SummaryError class + internal helpers (_init_row_nan_metrics, parsimony_distance, median_eval_sharpe, _native, _get_git_head, _config_tuple, _metrics_tuple, _entry, _stage_payload, _top3_nan_guard, _load_reconciled_baseline_cagr).

## Decisions Made

- **NaN-median semantics in JSON metrics tuple** — `median_eval_max_dd_pct` returns Python `float('nan')` when every eval year errored (all NaN); `json.dump` emits `NaN` literal which is acceptable for Phase 46's pandas/numpy consumer but NOT strict JSON. Judged acceptable because the D-11 consumer is Phase 46 Python code (NOT an external parser); strict-JSON compliance would force a `None` cast that loses the NaN signal.
- **ASCII dashes in banners** — Task 5 uses plain `-` characters in section banners (e.g., `"─ STAGE 1 ─"` → `"- STAGE 1 -"`) to avoid Windows cp1252 stdout emit issues observed in Phase 42 plans. Planner's example used unicode box-drawing; this is a safe deviation (visual only).
- **Git HEAD capture via subprocess** — `_get_git_head()` uses `subprocess.check_output(['git', 'rev-parse', 'HEAD'])` rather than reading .git/HEAD directly; covers detached HEAD + worktrees + missing git (returns `'unknown'` on any exception). Stderr silenced with `subprocess.DEVNULL` so a missing git binary doesn't pollute the sweep's stdout.

## Deviations from Plan

None — plan executed exactly as written. All 5 tasks implemented per their `<action>` blocks, all acceptance criteria passed on first attempt, no bugs / missing-critical / blocking / architectural issues encountered.

Light stylistic additions beyond the planner's minimums (all within Claude's discretion per D-Claude-1):

- Added a module-level `MACRO_CONFIG_FIELDS` constant (the 10-field tuple) to single-source the CSV column layout, JSON config serialization, and CSV row seeding in `run_combo`. Planner suggested the list inline in multiple places; consolidating eliminated copy-paste drift.
- Added `_init_row_nan_metrics` helper for the train_run_failed / train_metrics_failed early-return paths (D-10). Prevents the 7-line NaN-assignment block from duplicating.
- Added `_stage_payload` helper inside `write_best_json` so the 3 stage entries share serialization logic rather than triplicating it.

## Issues Encountered

None. Inline verifications in each task's `<verify>` block passed on first attempt. `python -m py_compile` clean. Grid counts (27/9/3/39) correct on first build. `select_winner` ranking (higher median_eval_cagr wins) verified with synthetic 2-row input. `_top3_nan_guard` fires correctly on synthetic NaN-winner input. `write_results_csv` + `write_best_json` round-trip verified end-to-end in tempdir with a 3-row synthetic payload.

## User Setup Required

None — no external services, credentials, or environment variables required. The sweep runs locally against already-checked-in VN30 CSV data + Phase 43 macro CSVs.

## Next Phase Readiness

- **Plan 02 (45-02-oos-guard-pytest)** — Ready to execute. Can import `analysis.walkforward_grid.load_vn30_data` and pass `df_override=` with 2025-labeled synthetic data; expects `AssertionError` with `"OOS leak"` substring. Can also import `select_winner` for the second pytest (selection-excludes-2025 semantics — likely requires small refactor of the row-level data to also flag 2025-containing rows, but Plan 02 owns that design).
- **Plan 03 (45-03-execute-sweep-commit-artifacts)** — Ready. Runs `uv run python analysis/walkforward_grid.py`, expects ~10-15 min serial execution, produces `output/v10_grid_results.csv` (39 rows) + `output/v10_grid_best.json` (schema_version=1 payload). Will need to decide whether the full CSV is git-committed (Phase 40 precedent: yes) — Plan 03's `<action>` block owns that call.
- **Phase 46** — Blocked on Plan 03 execution (needs the JSON). Once unblocked, Phase 46 consumes `output/v10_grid_best.json` to construct its 5 A/B scenarios via `dataclasses.replace(VN30_PRESET, **winner['config'])`. The 10-field config tuple shape is exactly what Phase 46's planner expects.

## Self-Check: PASSED

Files verified to exist:
- `analysis/walkforward_grid.py` — FOUND (685 lines)

Commits verified (git log):
- `6ccb5cb` feat(45-01): scaffold walkforward_grid module with OOS fence constants — FOUND
- `8ce8079` feat(45-01): add OOS-guarded load_vn30_data helper + baseline-CAGR read — FOUND
- `097a7d5` feat(45-01): add build_combo_grid + run_combo with D-09 accept gate — FOUND
- `9400fb7` feat(45-01): add select_winner + write_results_csv + write_best_json — FOUND
- `9180905` feat(45-01): add main() staged-sweep orchestrator — FOUND

Required module surface (all callables):
- `main`, `load_vn30_data`, `build_combo_grid`, `run_combo`, `select_winner`, `write_results_csv`, `write_best_json` — ALL CALLABLE
- `SummaryError` — subclass of RuntimeError, present and importable

Plan-level verification block (from plan frontmatter):
- OOS_FENCE='2025-01-01' — verified
- DEGRADATION_THRESHOLD=0.30 — verified
- TRAIN_END='2018-12-31' — verified
- EVAL_END='2024-12-31' — verified
- `compute_metrics` imported from `analysis.validate_v9` (D-16) — verified
- Grid counts 27 + 9 + 3 = 39 — verified via inline python
- `python -m py_compile analysis/walkforward_grid.py` — clean

Out-of-scope self-check (MUST all be NO):
- Did this plan touch `strategies/mdm_hybrid/*.py`? — NO ✓
- Did this plan add new MDMV2Config fields? — NO ✓
- Did this plan modify `analysis/validate_v9.py`? — NO ✓
- Did this plan touch `docs/`, `dashboard/`, or Phase 43 CSVs? — NO ✓

---

*Phase: 45-walk-forward-grid-search*
*Completed: 2026-04-23*
