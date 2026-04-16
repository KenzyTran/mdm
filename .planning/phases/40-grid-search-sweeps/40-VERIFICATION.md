---
phase: 40-grid-search-sweeps
verified: 2026-04-16T08:30:00Z
status: passed
score: 4/4 must-haves verified
gaps: []
human_verification: []
---

# Phase 40: Grid Search Sweeps Verification Report

**Phase Goal:** Best ATR and DD configurations are selected via a sequential, in-sample grid search that respects the OOS boundary and the max-drawdown constraint
**Verified:** 2026-04-16T08:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ATR sweep executes 36 runs over 4×3×3 grid on train window 2015-2021, writing `output/v9_atr_sweep.csv` with config + Sharpe + CAGR + MaxDD + transitions | VERIFIED | CSV confirmed: 36 rows, cols match, k={0.3,0.5,0.7,1.0}, period={10,14,20}, consec={1,2,3} |
| 2 | DD sweep executes 54 runs on locked best ATR config, writing `output/v9_dd_sweep.csv` with full D-08 grid coverage | VERIFIED | CSV confirmed: 54 rows, large_drop×small_drop×percentile full grid, locked ATR nunique=1 on all 3 columns |
| 3 | Selection script picks max-Sharpe subject to MaxDD ≤ -30% and writes `output/v9_atr_best.txt`, `output/v9_atr_best.json`, `output/v9_dd_best.txt`, `output/v9_dd_best.json` | VERIFIED | All 4 artifacts exist; ATR best max_dd_pct=-16.69 (≥-30 ✓), DD best max_dd_pct=-16.69 (≥-30 ✓); JSON schema={params,metrics,selected_at,train_window} |
| 4 | No sweep touches data after 2021 — OOS window 2022-2026 is provably untouched | VERIFIED | Both sweep scripts contain hard-coded `TRAIN_END='2021-12-31'` with runtime assertion `df['date'].max() <= pd.Timestamp(TRAIN_END)` and no CLI override surface |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `analysis/sweep_v9_atr.py` | 36-run ATR grid search, OOS guard, extended CSV schema | VERIFIED | 222 lines; `SummaryError`, `compute_metrics`, `main` defined; all grid literals present; no multiprocessing |
| `analysis/select_v9_best.py` | Selection CLI with `--stage {atr,dd}`, MaxDD constraint, D-17 tiebreak, D-21 JSON | VERIFIED | 155 lines; `select_best`, `write_outputs`, `main` defined; `MAX_DD_FLOOR=-30.0`, `choices=['atr','dd']`, sort descending on all 3 tiers |
| `analysis/sweep_v9_dd.py` | 54-run DD grid search, stage-1 JSON handoff, locked ATR params | VERIFIED | 287 lines; `load_locked_atr`, `compute_metrics`, `SummaryError`, `main` defined; all grid literals and fixed params present |
| `output/v9_atr_sweep.csv` | 36 rows, 15 columns, full 4×3×3 grid, no NaN in top-5 | VERIFIED | 36 rows, columns=['atr_buffer_k','atr_buffer_period','atr_buffer_consecutive_days','config_name','sharpe_rf3','cagr_pct','max_dd_pct','transitions','sell_count','ma50_breakdown_sell_share','buy_count','buy_pct','cash_pct','sell_pct','error'], top-5 NaN=False |
| `output/v9_atr_best.txt` | Human-readable stage-1 winner with params and metrics | VERIFIED | File exists with key-value format |
| `output/v9_atr_best.json` | Machine-readable JSON with {params,metrics,selected_at,train_window} | VERIFIED | keys={'params','metrics','selected_at','train_window'}; params={'atr_buffer_k':1.0,'atr_buffer_period':20,'atr_buffer_consecutive_days':2}; max_dd_pct=-16.69 |
| `output/v9_dd_sweep.csv` | 54 rows, 18 columns, full 6×3×3 DD grid, locked ATR constant | VERIFIED | 54 rows, locked ATR nunique=1 on all 3 columns, full DD grid coverage |
| `output/v9_dd_best.txt` | Human-readable stage-2 winner with params and metrics | VERIFIED | File exists with key-value format |
| `output/v9_dd_best.json` | Machine-readable JSON with DD params + locked ATR metadata | VERIFIED | keys={'params','metrics','selected_at','train_window'}; params includes refined_dd_* AND locked atr_buffer_* for traceability; max_dd_pct=-16.69 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sweep_v9_atr.py` | `strategies/mdm_hybrid/config.py::VN30_PRESET` | `dataclasses.replace(VN30_PRESET, atr_buffer_enabled=True, ...)` | WIRED | Line 37 imports VN30_PRESET; line 159 uses `replace(VN30_PRESET, ...)` |
| `sweep_v9_atr.py` | `core.data_loader.DataLoader('vn30').load` | DataLoader call + max-date assertion | WIRED | Line 138 loads data; line 141-142 asserts max date |
| `sweep_v9_atr.py` | `strategies.mdm_hybrid.mdm_hybrid_engine.HybridEngine` | `engine.run(df.copy())` | WIRED | Line 183 calls `engine.run(df.copy())` |
| `select_v9_best.py` | `output/v9_atr_sweep.csv` | `pd.read_csv` when `--stage atr` | WIRED | Line 144 reads CSV via STAGE_CONFIG dispatch |
| `select_v9_best.py` | `output/v9_dd_sweep.csv` | `pd.read_csv` when `--stage dd` | WIRED | Same line 144 via STAGE_CONFIG dispatch for dd stage |
| `select_v9_best.py` | `output/v9_atr_best.json` | `json.dump` with D-21 schema | WIRED | Lines 102-104 write JSON |
| `select_v9_best.py` | `output/v9_dd_best.json` | `json.dump` with D-21 schema | WIRED | Same write_outputs function dispatches for dd stage |
| `sweep_v9_dd.py` | `output/v9_atr_best.json` | `json.load` to extract locked ATR params | WIRED | Lines 56, 82-83 define ATR_BEST_JSON path and load it |
| `sweep_v9_dd.py` | `strategies/mdm_hybrid/config.py::VN30_PRESET` | `dataclasses.replace(VN30_PRESET, atr_buffer_enabled=True, ..., refined_dd_enabled=True, ...)` | WIRED | Line 218 sets `refined_dd_enabled=True`, locked ATR wired from loaded JSON |
| `sweep_v9_dd.py` | `strategies.mdm_hybrid.mdm_hybrid_engine.HybridEngine` | `engine.run(df.copy())` | WIRED | Line 246 calls `engine.run(df.copy())` |

---

## Data-Flow Trace (Level 4)

These are analysis scripts (not rendering components), but the data flows are verified below since they produce output files that feed downstream phases.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `sweep_v9_atr.py` | `df_out` (36-row DataFrame) | `HybridEngine.run()` × 36 configs via `DataLoader('vn30').load()` | Yes — real backtest results; 0 error rows confirmed in SUMMARY | FLOWING |
| `select_v9_best.py` | `best` (pd.Series winner row) | `pd.read_csv(sweep_csv)` → `select_best(df)` applying MaxDD≥-30 filter | Yes — reads real sweep CSV; all 36 rows passed constraint | FLOWING |
| `sweep_v9_dd.py` | `df_out` (54-row DataFrame) | Locked ATR from `json.load(v9_atr_best.json)` + `HybridEngine.run()` × 54 configs | Yes — 0 error rows confirmed in SUMMARY; locked k=1.0,N=20,m=2 verified constant | FLOWING |
| `output/v9_atr_best.json` / `v9_dd_best.json` | JSON payloads | `write_outputs(best, stage)` from select_best | Yes — max_dd_pct verified ≥-30 both stages; sharpe_rf3 finite both stages | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ATR sweep produces 36-row CSV with full grid coverage | `uv run python -c "import pandas as pd; atr=pd.read_csv('output/v9_atr_sweep.csv'); assert len(atr)==36"` | 36 rows, k={0.3,0.5,0.7,1.0}, period={10,14,20}, consec={1,2,3} | PASS |
| DD sweep produces 54-row CSV with locked ATR | `uv run python -c "import pandas as pd; dd=pd.read_csv('output/v9_dd_sweep.csv'); assert len(dd)==54; assert dd['atr_buffer_k'].nunique()==1"` | 54 rows, locked ATR k nunique=1 | PASS |
| ATR best JSON passes MaxDD constraint | `uv run python -c "import json; d=json.load(open('output/v9_atr_best.json')); assert d['metrics']['max_dd_pct'] >= -30"` | max_dd_pct=-16.69 (≥-30) | PASS |
| DD best JSON passes MaxDD constraint + has locked ATR params | `uv run python -c "import json; d=json.load(open('output/v9_dd_best.json')); assert 'atr_buffer_k' in d['params']"` | params includes atr_buffer_k=1.0 | PASS |
| select_v9_best.py --help exits 0 | `uv run python analysis/select_v9_best.py --help` | Usage printed with {atr,dd} choice list | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SWEEP-01 | 40-01-PLAN.md | ATR grid search 36 runs, `output/v9_atr_sweep.csv` with config+Sharpe+CAGR+MaxDD+transitions | SATISFIED | CSV verified: 36 rows, full 4×3×3 grid, all required columns present including whipsaw diagnostics |
| SWEEP-02 | 40-03-PLAN.md | DD grid search 54 runs on locked ATR, `output/v9_dd_sweep.csv` | SATISFIED | CSV verified: 54 rows, full 6×3×3 grid, locked ATR constant across all rows |
| SWEEP-03 | 40-02-PLAN.md | Selection script max-Sharpe subject to MaxDD≤-30%, writes `v9_atr_best.txt` and `v9_dd_best.txt` | SATISFIED | Both .txt and .json artifacts exist; MaxDD≥-30 verified in both; tiebreak logic (sharpe/cagr/max_dd desc) implemented |
| SWEEP-04 | 40-01-PLAN.md, 40-03-PLAN.md | All sweeps on 2015-2021 train window only, no OOS leakage | SATISFIED | Both sweep scripts hard-code TRAIN_END='2021-12-31' with runtime assertion `df['date'].max() <= pd.Timestamp(TRAIN_END)`, no CLI override allowed |

**All 4 requirements SATISFIED. No orphaned requirements.**

REQUIREMENTS.md status table confirms all four SWEEP-01..SWEEP-04 marked `Complete | Phase 40`.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none found) | — | — | — | — |

No TODO/FIXME/placeholder comments found in any of the three new scripts. No empty implementations. No hardcoded empty return values that flow to outputs. No multiprocessing imports (verified by grep).

---

## Production Code Isolation (Additive-Only Check)

Phase 40 is tooling-only. Verified by inspecting commits:
- `19bd6ad` — only `analysis/sweep_v9_atr.py` created
- `5085146` — only `analysis/select_v9_best.py` created
- `23807f8` — only `analysis/sweep_v9_dd.py` created
- `abd900b` — empty chore commit (runtime artifacts in gitignored `output/`)

No `strategies/`, `models/`, `vn30_vsa/`, or `docs/rules_*.md` files were modified. The CLAUDE.md Code-Docs Sync Rule is not triggered because no strategy logic changed.

---

## Human Verification Required

None. All success criteria are verifiable programmatically:
- CSV row counts and column schemas are machine-checkable.
- JSON artifact schemas and constraint compliance are machine-checkable.
- OOS guard is a code-level assertion, not a visual/UX concern.
- No UI, real-time behavior, or external service integration involved.

---

## Notable Findings

1. **ATR-only dominates ATR+DD in-sample.** The stage-2 winner `dd-L-0.007-S-0.003-P3` achieves Sharpe=0.7160 vs the ATR-only stage-1 winner at 0.7596. Nine DD configs tied at the same Sharpe, meaning the refined_dd module adds no measurable alpha over ATR buffer alone on the 2015-2021 VN30 train window. Phase 41 should test ATR-only as the primary production candidate.

2. **All 36 ATR configs and all 54 DD configs pass the MaxDD≤-30% constraint** (best max_dd=-15.29 for ATR, best=-16.69 for DD). The D-16 RuntimeError path was never triggered; selection was never at risk of an empty-candidates abort.

3. **ma50_breakdown_sell_share = 1.0 uniformly** across all 90 sweep rows. Every SELL in both sweeps flowed through the MA50 path (either classic `SELL signal: MA50 breakdown` or buffered `SELL signal: ATR buffer zone`). Phase 41's VAL-04 whipsaw diagnostic should focus on whether the ATR buffer reduces SELL frequency rather than changing the SELL trigger path.

4. **Stage-1 JSON handoff protocol operational.** `sweep_v9_dd.py` correctly raises FileNotFoundError with exact remediation command if invoked before `select_v9_best.py --stage atr` has run. Verified during plan execution.

---

## Gaps Summary

No gaps. All 4 observable truths verified, all 9 required artifacts exist and pass all verification levels, all 4 key requirements satisfied, no anti-patterns, no production code modified.

---

_Verified: 2026-04-16T08:30:00Z_
_Verifier: Claude (gsd-verifier)_
