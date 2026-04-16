---
phase: 40-grid-search-sweeps
plan: 03
subsystem: analysis
tags: [grid-search, refined-dd, atr-buffer, vn30, sweep, backtest, whipsaw, pipeline]

# Dependency graph
requires:
  - phase: 40-01
    provides: analysis/sweep_v9_atr.py + output/v9_atr_sweep.csv (36-row ATR grid with extended-schema metrics) -- skeleton mirrored here and consumed end-to-end
  - phase: 40-02
    provides: analysis/select_v9_best.py with --stage {atr,dd} dispatch + D-21 JSON handoff schema ({params, metrics, selected_at, train_window})
  - phase: 38-atr-buffer-zone-module
    provides: MDMV2Config atr_buffer_* fields + HybridEngine ATR precompute gate (pinned True with locked k=1.0, N=20, m=2 from stage 1)
  - phase: 39-refined-distribution-day-module
    provides: MDMV2Config refined_dd_* fields + DistributionDayCounter dual-threshold branch (flipped True with swept large_drop, small_drop, small_vol_percentile)
provides:
  - analysis/sweep_v9_dd.py -- serial 54-run refined-DD grid-search script (6 large_drop x 3 small_drop x 3 percentile) with stage-1 JSON handoff
  - output/v9_dd_sweep.csv -- 54 rows with DD params + locked ATR metadata + extended metrics + error column (D-18)
  - output/v9_atr_best.{txt,json} -- stage-1 selected winner (atr-k1.0-N20-m2)
  - output/v9_dd_best.{txt,json} -- stage-2 selected winner (dd-L-0.007-S-0.003-P3)
  - Phase 40 pipeline closure: full four-step execution (ATR sweep -> select atr -> DD sweep -> select dd) verified
affects: [phase-41-ab-walk-forward-validation, phase-42-documentation-dashboard]

# Tech tracking
tech-stack:
  added: []  # Pure reuse: stdlib + pandas + tqdm, HybridEngine + DataLoader + build_indicator_dataframe -- no new deps
  patterns:
    - "Sequential stage-handoff via JSON artifact: stage 2 reads output/v9_atr_best.json at startup, raises FileNotFoundError with exact next-command hint if absent (enforces ordered execution)"
    - "D-02 self-contained stage scripts: compute_metrics is a sibling copy across sweep_v9_atr.py and sweep_v9_dd.py (no cross-import), so a stage-2 re-run does not implicitly trigger stage-1 re-execution"
    - "Locked-param metadata columns in downstream sweep CSV (atr_buffer_k/period/m duplicated across all 54 rows) for traceability without requiring join to stage-1 JSON"

key-files:
  created:
    - analysis/sweep_v9_dd.py
  modified: []

key-decisions:
  - "Top-9 DD configs tied on Sharpe_rf3=0.7160 / CAGR=13.55% / MaxDD=-16.69% -- selector correctly picked dd-L-0.007-S-0.003-P3 as the first lexicographic row after D-17's 3-tier sort (stable sort preserves itertools.product order from -0.005..-0.010 x -0.003..-0.005 x {3,5,10}). DD parameters provide minimal separation inside the 'moderate' neighborhood on VN30 train, which is a meaningful finding for Phase 41."
  - "DD sweep performance uniformly UNDER the locked ATR-only baseline (Sharpe_rf3=0.7160 vs 0.7596; CAGR=13.55 vs 14.14) -- refined_dd_enabled adds ZERO Sharpe over the ATR-only config on VN30 train window. Phase 41 A/B should test (i) baseline, (ii) ATR-only, (iii) ATR+DD; current evidence suggests the ATR-only config may be the production candidate."
  - "ma50_breakdown_sell_share = 1.0 uniformly across all 54 DD rows -- every SELL in the sweep flowed through the ma50_sell_enabled branch (same pattern as plan 40-01). The buffered-label and classic-label are treated as the same whipsaw-path hit (D-20); refined DD did not introduce a new SELL-trigger path."
  - "Gitignored runtime artifacts: output/v9_*_{sweep,best}.* are reproducible from the scripts + input CSV data; repo is committed for scripts (two sweep + one selector) and one chore marker commit for the pipeline run (--allow-empty). Artifacts live on disk for Phase 41 consumption but are not versioned."

patterns-established:
  - "Stage-N handoff protocol: next-stage script reads stage-(N-1)'s JSON at startup, missing JSON raises FileNotFoundError with exact remediation command -- pattern scales to Phase 42+ joint sweeps"
  - "DD sweep CSV preserves BOTH swept (DD) and locked (ATR) params as columns so a Phase 41 reader doesn't need to join v9_atr_best.json to reconstruct full config context"

requirements-completed: [SWEEP-02, SWEEP-04]

# Metrics
duration: ~7 min
completed: 2026-04-16
---

# Phase 40 Plan 03: Refined-DD Grid-Search Sweep + Pipeline Closure Summary

**54-run serial refined-DD grid search on locked ATR config (k=1.0, N=20, m=2) producing `output/v9_dd_sweep.csv`; stage-2 winner `dd-L-0.007-S-0.003-P3` ties 8 other configs at Sharpe_rf3=0.7160 and UNDERPERFORMS the ATR-only baseline (0.7596), revealing that refined_dd adds no alpha on VN30 train window.**

## Performance

- **Duration:** ~7 min (script authored + full pipeline run + verification + summary)
- **Started:** 2026-04-16T07:40:00Z
- **Completed:** 2026-04-16T07:47:00Z
- **Tasks:** 2 (1 script creation + 1 end-to-end pipeline execution)
- **Files modified:** 1 created (`analysis/sweep_v9_dd.py`, 286 lines); 6 runtime artifacts in `output/` (gitignored by design)
- **Sweep runtimes:** ATR 108s (36 runs, ~3.0s/config), DD 107s (54 runs, ~2.0s/config)

## Accomplishments

- **SWEEP-02 satisfied.** `analysis/sweep_v9_dd.py` exercises the full 6x3x3 refined-DD grid (`large_drop ∈ {-0.005..-0.010}`, `small_drop ∈ {-0.003, -0.004, -0.005}`, `small_vol_percentile ∈ {3, 5, 10}`) per D-08 with `atr_buffer_enabled=True` (locked from stage 1) and `refined_dd_enabled=True` (swept), so only the combined ATR+DD impact over ATR-only is measured.
- **SWEEP-04 satisfied** (reinforced). Both sweep scripts assert `df['date'].max() <= pd.Timestamp('2021-12-31')` at load time; no CLI override exists to accidentally leak 2022+ data.
- **Stage-1 JSON handoff (D-13) operational.** `load_locked_atr()` reads `output/v9_atr_best.json`, validates required keys (`atr_buffer_k/period/consecutive_days`), and casts to float/int. Missing JSON raises FileNotFoundError with the exact remediation command: *"Run `uv run python analysis/select_v9_best.py --stage atr` first"*. Verified by invoking before the JSON existed.
- **Full Phase 40 pipeline executed end-to-end.** All four commands ran in sequence with exit code 0:
  1. `sweep_v9_atr.py` → 36 rows in `output/v9_atr_sweep.csv` (108s)
  2. `select_v9_best.py --stage atr` → `output/v9_atr_best.{txt,json}` picking `atr-k1.0-N20-m2`
  3. `sweep_v9_dd.py` → 54 rows in `output/v9_dd_sweep.csv` (107s)
  4. `select_v9_best.py --stage dd` → `output/v9_dd_best.{txt,json}` picking `dd-L-0.007-S-0.003-P3`
- **All six artifacts schema-verified:** row counts (36 / 54), grid-uniques coverage (4/3/3 for ATR, 6/3/3 for DD), locked ATR constant across all 54 DD rows (`.nunique() == 1` on each of the three ATR columns), JSON top-level keys `{params, metrics, selected_at, train_window}`, `train_window == '2015-01-01..2021-12-31'`, `max_dd_pct >= -30` both stages, finite `sharpe_rf3` both stages, DD best params includes locked ATR metadata for Phase 41 traceability.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create analysis/sweep_v9_dd.py with 54-run DD grid search and stage-1 JSON handoff** — `23807f8` (feat)
2. **Task 2: Execute full Phase 40 pipeline end-to-end (runtime artifacts)** — `abd900b` (chore, `--allow-empty` since `output/` is gitignored)

**Plan metadata:** will be appended with this SUMMARY.md, STATE.md, and ROADMAP.md updates.

## Files Created/Modified

- `analysis/sweep_v9_dd.py` (286 lines, new file):
  - Module docstring references SWEEP-02/SWEEP-04 and the stage-1 prerequisite
  - Imports: stdlib (sys/os/json/itertools/traceback) + numpy + pandas + tqdm + HybridEngine/VN30_PRESET
  - Constants: `TRAIN_START='2015-01-01'`, `TRAIN_END='2021-12-31'`, `OUTPUT_CSV`, `ATR_BEST_JSON`
  - `SummaryError(RuntimeError)`: top-5 NaN guard exception
  - `load_locked_atr()`: stage-1 handoff with FileNotFoundError + KeyError guards (D-13)
  - `compute_metrics()`: D-02 sibling copy of `sweep_v9_atr.compute_metrics` (same extended schema per D-18)
  - `main()`: load JSON → load VN30 → OOS assert → indicators → itertools.product(54) → replace(VN30_PRESET, ...) → HybridEngine.run() → write CSV with canonical col_order → top-5 NaN guard

**Runtime artifacts produced (all gitignored per project convention):**
- `output/v9_atr_sweep.csv` — 36 rows (regenerated by step 1 of pipeline)
- `output/v9_atr_best.{txt,json}` — stage-1 winner (produced by step 2)
- `output/v9_dd_sweep.csv` — 54 rows (produced by step 3)
- `output/v9_dd_best.{txt,json}` — stage-2 winner (produced by step 4)

## Verification Line Numbers

From `analysis/sweep_v9_dd.py`:

| What | Line | Snippet |
| :--- | :---: | :--- |
| Stage-1 handoff constant | 55 | `ATR_BEST_JSON = os.path.join(...'v9_atr_best.json')` |
| `SummaryError` class | 58 | `class SummaryError(RuntimeError):` |
| `load_locked_atr` function | 62 | `def load_locked_atr() -> dict:` |
| FileNotFoundError msg (D-13) | 79 | `f"{ATR_BEST_JSON} not found. ... Run \`uv run python analysis/select_v9_best.py --stage atr\` first"` |
| `compute_metrics` function | 93 | `def compute_metrics(results: pd.DataFrame) -> dict:` |
| `main` function | 175 | `def main():` |
| **OOS-guard assertion (D-12)** | **185** | `assert df['date'].max() <= pd.Timestamp(TRAIN_END), ...` |
| large_drop grid (D-08) | 191 | `large_drop_values = [-0.005, -0.006, -0.007, -0.008, -0.009, -0.010]` |
| small_drop grid (D-08) | 192 | `small_drop_values = [-0.003, -0.004, -0.005]` |
| percentile grid (D-08) | 193 | `percentile_values = [3, 5, 10]` |
| ATR locked ON (D-06) | 208 | `atr_buffer_enabled=True,` |
| DD swept ON (D-06) | 213 | `refined_dd_enabled=True,` |
| large_vol_rule fixed (D-08) | 216 | `refined_dd_large_vol_rule='vol_ma20'` |
| small_vol_lookback fixed (D-08) | 218 | `refined_dd_small_vol_lookback=50` |
| Top-5 NaN guard (D-10) | 268 | `if top5['sharpe_rf3'].isna().any():` |

## Stage-1 Winner (ATR)

```
Config: atr-k1.0-N20-m2
Params:
  atr_buffer_k              = 1.0
  atr_buffer_period         = 20
  atr_buffer_consecutive_days = 2
Metrics:
  sharpe_rf3                = 0.7596
  cagr_pct                  = 14.14
  max_dd_pct                = -16.69
  transitions               = 125
  sell_count                = 32
  ma50_breakdown_sell_share = 1.00
  buy_count                 = 24
  buy_pct                   = 34.42
  cash_pct                  = 42.25
  sell_pct                  = 23.33
```

## Stage-2 Winner (DD on locked ATR)

```
Config: dd-L-0.007-S-0.003-P3
Params:
  refined_dd_large_drop             = -0.007
  refined_dd_small_drop             = -0.003
  refined_dd_small_vol_percentile   = 3
  atr_buffer_k                      = 1.0        (locked from stage 1)
  atr_buffer_period                 = 20         (locked from stage 1)
  atr_buffer_consecutive_days       = 2          (locked from stage 1)
Metrics:
  sharpe_rf3                = 0.7160
  cagr_pct                  = 13.55
  max_dd_pct                = -16.69
  transitions               = 121
  sell_count                = 31
  ma50_breakdown_sell_share = 1.00
  buy_count                 = 23
  buy_pct                   = 35.16
  cash_pct                  = 41.28
  sell_pct                  = 23.56
```

## DD Sweep Distribution (54 rows, 0 errors, 0 NaN)

| Metric | Min | Max | Median | Note |
| :--- | :---: | :---: | :---: | :--- |
| `sharpe_rf3` | 0.6543 | 0.7160 | 0.6794 | best stage-2 < 0.7596 best stage-1 |
| `cagr_pct` | 12.61 | 13.55 | — | best stage-2 < 14.14 best stage-1 |
| `max_dd_pct` | -17.97 | -16.69 | — | all pass MaxDD >= -30 constraint |
| `transitions` | 121 | 125 | — | fewer than ATR-only top (125) |
| `sell_count` | 31 | 31 | 31 | uniform — DD knobs barely move SELL count |
| `ma50_breakdown_sell_share` | 1.0 | 1.0 | 1.0 | all SELLs flow through MA50 path |

**Top 9 DD configs are a nine-way tie** (Sharpe_rf3=0.7160, CAGR=13.55%, MaxDD=-16.69%, transitions=121, sell_count=31):

| Rank | config_name | large_drop | small_drop | percentile |
| :---: | :--- | :---: | :---: | :---: |
| 1 | dd-L-0.007-S-0.003-P3 | -0.007 | -0.003 | 3 |
| 2 | dd-L-0.007-S-0.004-P3 | -0.007 | -0.004 | 3 |
| 3 | dd-L-0.007-S-0.005-P3 | -0.007 | -0.005 | 3 |
| 4 | dd-L-0.008-S-0.003-P3 | -0.008 | -0.003 | 3 |
| 5 | dd-L-0.008-S-0.003-P5 | -0.008 | -0.003 | 5 |
| 6 | dd-L-0.008-S-0.004-P3 | -0.008 | -0.004 | 3 |
| 7 | dd-L-0.008-S-0.004-P5 | -0.008 | -0.004 | 5 |
| 8 | dd-L-0.008-S-0.005-P3 | -0.008 | -0.005 | 3 |
| 9 | dd-L-0.008-S-0.005-P5 | -0.008 | -0.005 | 5 |

The tie tells us the refined-DD dual-threshold rule is NOT differentiating runs inside this neighborhood — on VN30 train window 2015-2021 the ATR buffer alone already suppresses the same false-breakdown whipsaw events that DD would otherwise catch, so DD becomes redundant. Stage-2 winner `dd-L-0.007-S-0.003-P3` is selected by pandas' stable sort order of `itertools.product` (large=-0.007 first in the tied neighborhood) rather than by a metric advantage.

## Skeleton Differences vs Plan 40-01

`sweep_v9_dd.py` vs `sweep_v9_atr.py`:

| Area | 40-01 (ATR) | 40-03 (DD) |
| :--- | :--- | :--- |
| Grid size | 36 (4x3x3) | **54 (6x3x3)** |
| Swept fields | `atr_buffer_k`, `atr_buffer_period`, `atr_buffer_consecutive_days` | `refined_dd_large_drop`, `refined_dd_small_drop`, `refined_dd_small_vol_percentile` |
| Locked fields | — (none) | `atr_buffer_k/period/consecutive_days` from stage-1 JSON |
| Stage-1 handoff | — | `load_locked_atr()` reads `output/v9_atr_best.json` (D-13) |
| Config flags | `atr_buffer_enabled=True`, `refined_dd_enabled=False` | **both True** |
| CSV col_order | config (4) + metrics (10) + error = 15 cols | DD params (3) + locked ATR metadata (3) + config_name + metrics (10) + error = **18 cols** |
| Extra imports | — | `json` (for `load_locked_atr`) |
| Everything else | — | **identical structure** (OOS assert, `compute_metrics`, tqdm loop, fail-loud per config, top-5 NaN `SummaryError`) |

## Decisions Made

1. **D-02 sibling copy of `compute_metrics`, no cross-import.** `sweep_v9_dd.py` re-defines `compute_metrics` verbatim (same 10-key schema) rather than importing from `sweep_v9_atr.py`. Rationale: keeps each stage script self-contained so a stage-2 re-run does not implicitly trigger import-side-effect re-execution of stage-1 code paths. Copy-paste cost is offset by the independence guarantee.
2. **Locked ATR as both JSON input AND CSV output metadata.** Stage-2 CSV preserves the locked k/N/m values as columns duplicated across all 54 rows (not just in the companion JSON). Rationale: Phase 41 readers get full config context from a single `pd.read_csv` without needing to join/merge the stage-1 artifact.
3. **Gitignore keeps runtime artifacts out of the repo; chore marker commit for Task 2.** `output/` is listed in `.gitignore` (line 18). Phase 40 artifacts are deterministic reproductions from the scripts + input data, so the repo records only the scripts. Task 2's completion is captured by a `--allow-empty` chore commit with the full pipeline log embedded in the message — provides git-log provenance without versioning 100KB of CSV.
4. **Top-9 tie reported truthfully in SUMMARY.** Per PROJECT.md core value ("accurately reverse-engineer"), reporting the tie — including that `dd-L-0.007-S-0.003-P3` won by stable-sort order rather than metric advantage — is more useful to the Phase 41 validator than hiding the uniformity. Phase 41 A/B should test whether the ATR-only config (`refined_dd_enabled=False`) matches the ATR+DD config on OOS 2022-2026, since stage-2 evidence suggests DD adds nothing.

## Deviations from Plan

None - plan executed exactly as written.

All acceptance criteria from Task 1 and Task 2 `<acceptance_criteria>` blocks passed on first run:
- Task 1: script parses, defines all four symbols (`main`, `compute_metrics`, `load_locked_atr`, `SummaryError`), contains all literal grid/config/OOS strings, no multiprocessing import, both MA50 labels present, FileNotFoundError fires with correct remediation message when `v9_atr_best.json` is absent.
- Task 2: all four pipeline commands exited 0; all six artifacts exist with correct row counts, grid coverage, locked-ATR constancy, D-21 JSON schema, train_window literal, MaxDD constraint, finite sharpe_rf3, and traceability fields in the DD-best JSON.

No Rule 1/2/3 auto-fixes triggered. No architectural questions surfaced. No `strategies/` or `docs/` edits were required or made (Phase 40 is tooling-only per CONTEXT.md).

## Issues Encountered

- **Cosmetic: shell-quoting in the nested `python -c` verification block.** The plan's Task 2 `<automated>` block uses double-quotes inside a python `-c` inside a bash heredoc, which tripped on the outer `"params"` key access. The critical assertions all executed and printed "Pipeline complete. All 6 artifacts valid." before the print statement errored. Re-ran the same assertions via a clean heredoc (`uv run python <<'PYEOF' ... PYEOF`) to get a clean output with `ALL CHECKS PASSED` + the full winner params/metrics dicts. Not a code issue, just verification-driver tooling friction.

## User Setup Required

None — no external service configuration required. All outputs are local CSV/JSON/TXT files in `output/`.

## Next Phase Readiness

- **Phase 41 (A/B + walk-forward validation) unblocked.** All four best-artifact files exist on disk in `output/`:
  - `v9_atr_best.json` → `params` has `atr_buffer_{k=1.0, period=20, consecutive_days=2}`
  - `v9_dd_best.json` → `params` has `refined_dd_{large_drop=-0.007, small_drop=-0.003, small_vol_percentile=3}` + locked ATR metadata
  - Both JSONs conform to the D-21 schema, so Phase 41 can code against `{params, metrics, selected_at, train_window}` with confidence.
- **Phase 41 A/B scenarios:** four configurations to test on walk-forward Train 2015-2021 / Test 2022-2026:
  - **Baseline:** `refined_dd_enabled=False, atr_buffer_enabled=False` (v6.0 reference)
  - **+ATR only:** `atr_buffer_enabled=True` with locked (k=1.0, N=20, m=2); `refined_dd_enabled=False` (the stage-1 winner, Sharpe_rf3=0.7596 in-sample)
  - **+DD only:** `refined_dd_enabled=True` with locked DD winner; `atr_buffer_enabled=False` (not part of current selection but valuable diagnostic)
  - **+both:** `atr_buffer_enabled=True` + `refined_dd_enabled=True` (the stage-2 winner, Sharpe_rf3=0.7160 in-sample)
- **Phase 41 hypothesis to test:** Based on the nine-way stage-2 tie and the fact that `+both` in-sample (0.7160) underperforms `+ATR only` (0.7596), the ATR-only config may be the production winner. If OOS 2022-2026 validation confirms ATR-only >= ATR+DD, the Phase 42 docs should ship ATR-only as v9.0.
- **Phase 41 OOS window:** `TRAIN_END='2021-12-31'` assert guarantees 2022-2026 data is untouched by the sweep. Phase 41 can safely reuse the same `DataLoader('vn30').load(...)` pattern with `start_date='2022-01-01'`.
- **Zero blockers.** Scripts are dependency-free at runtime (stdlib + pandas + tqdm + numpy, all already in project). All six artifacts are schema-checked.

## Self-Check: PASSED

**File existence check:**
- FOUND: `analysis/sweep_v9_dd.py`
- FOUND: `output/v9_atr_sweep.csv`
- FOUND: `output/v9_atr_best.txt`
- FOUND: `output/v9_atr_best.json`
- FOUND: `output/v9_dd_sweep.csv`
- FOUND: `output/v9_dd_best.txt`
- FOUND: `output/v9_dd_best.json`

**Commit existence check:**
- FOUND: `23807f8` (feat(40-03): add refined-DD grid-search sweep script)
- FOUND: `abd900b` (chore(40-03): execute Phase 40 pipeline end-to-end)

---
*Phase: 40-grid-search-sweeps*
*Plan: 03*
*Completed: 2026-04-16*
