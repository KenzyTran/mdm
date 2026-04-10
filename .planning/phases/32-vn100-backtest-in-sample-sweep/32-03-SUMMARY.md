---
phase: 32-vn100-backtest-in-sample-sweep
plan: 03
subsystem: backtest-pipeline
tags: [vn100, canslim, top3-selection, audit-report, BT-02, D-13, D-14, D-16]
requires:
  - docs/audits/phase32/sweep_results.csv
  - analysis/select_top3_vn100.py::select_top3
provides:
  - docs/audits/phase32/locked_params_top3.json
  - docs/audits/phase32-backtest-sweep.md
  - analysis/select_top3_vn100.py
  - tests/phase32/test_top3.py
affects:
  - .planning/phases/33-vn100-oos-sensitivity/  # Phase 33 consumes locked_params_top3.json
tech-stack:
  added: []
  patterns: [tdd-red-green, d14-json-schema, d13-sanity-gate]
key-files:
  created:
    - analysis/select_top3_vn100.py
    - tests/phase32/test_top3.py
    - docs/audits/phase32/locked_params_top3.json
    - docs/audits/phase32-backtest-sweep.md
  modified: []
decisions:
  - "Top-3 selected by Sharpe_rf3 desc (D-12 tie-breakers: CAGR desc, MaxDD desc). All 3 share c_yoy=0.25 / n_prox=0.10 / hard_stop=0.06 / entry=C — tight fundamentals + tight stop + next-day-open fill dominates 2014-2018 in-sample."
  - "D-13 sanity gate passed: 1536/1536 configs are sanity_flag=OK, 0 CAGR_TOO_HIGH, 0 ERROR."
  - "Audit report documents survivorship bias caveat, RS stub, and low-Sharpe environment explanation for Phase 33 consumer."
metrics:
  duration: "~25 min"
  tasks: 3
  files: 4
  completed: "2026-04-10"
requirements: [BT-02]
---

# Phase 32 Plan 03: Top-3 Selection + Audit Report Summary

BT-02 SC4 + SC5 complete. Reads 1,536-row `sweep_results.csv` from plan 02, selects top-3 configs by Sharpe_rf3 with D-12 tie-breakers and D-13 sanity gate, writes `locked_params_top3.json` for Phase 33, and produces the Phase 32 audit report.

## Tasks

### Task 1: select_top3_vn100.py + locked_params JSON (TDD) (commit `cb25d2e`)

**TDD RED:** `tests/phase32/test_top3.py` written first — 7 failing tests covering:
- `test_select_top3_returns_three_rows`
- `test_select_top3_sorted_by_sharpe_desc`
- `test_tie_breaker_cagr` (D-12)
- `test_tie_breaker_maxdd` (D-12)
- `test_sanity_gate_aborts` (D-13)
- `test_sanity_gate_ok_passes`
- `test_json_schema` (D-14)

**TDD GREEN:** `analysis/select_top3_vn100.py` implemented with:
- `select_top3(df)`: filters ERRORs, sorts [Sharpe_rf3 desc, CAGR desc, MaxDD desc], takes top 3, raises `RuntimeError` if any has `sanity_flag != "OK"`.
- `to_json_payload(top3)`: builds D-14 dict with `selected_at`, `selection_metric`, `period`, `universe`, `configs[3]`.
- `main()`: reads SWEEP_CSV, prints summary, calls select_top3, writes JSON, prints top-3 table.

**Results from real data:**

| Rank | c_yoy | a_cagr | n_prox | hard_stop | slots | entry | CAGR | Sharpe_rf3 | MaxDD |
|------|-------|--------|--------|-----------|-------|-------|------|------------|-------|
| 1 | 0.25 | 0.20 | 0.10 | 0.06 | 5 | C | 3.79% | 0.0590 | -17.66% |
| 2 | 0.25 | 0.25 | 0.10 | 0.06 | 8 | C | 3.76% | 0.0566 | -17.67% |
| 3 | 0.25 | 0.25 | 0.10 | 0.06 | 10 | C | 3.76% | 0.0566 | -17.67% |

All `sanity_flag = OK`. JSON written to `docs/audits/phase32/locked_params_top3.json`.

### Task 2: Phase 32 audit report (commit `ef14ec9`)

`docs/audits/phase32-backtest-sweep.md` written with all D-16 sections:
1. Methodology (pipeline, period, universe, MDM gate, costs, Sharpe definition)
2. Single-Run Baseline: CAGR 4.17%, Sharpe 0.0671, MaxDD -20.63%, 60 trades, 50% hit rate
3. Sweep Results: 1536 OK, Sharpe min -0.2583 / median -0.0904 / max +0.0590, CAGR median 1.87%
4. Top-3 Configs table
5. Sanity Gate: 0 flagged, gate passed
6. Artifacts list
7. Phase 33 handoff
8. Notes & Caveats (survivorship bias, RS stub, fundamentals stub)

### Task 3: checkpoint:human-verify (APPROVED)

User reviewed top-3 JSON and audit report. Checkpoint approved — plan 32-03 complete.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None introduced in this plan. Pre-existing stubs (RS stub, fundamentals stub) documented
in audit report Notes & Caveats section. These stubs were present from plan 02 and are
out of scope for plan 03 to resolve.

## Verification

- `uv run pytest tests/phase32/test_top3.py -x -q` → 7 passed in 0.14s
- `docs/audits/phase32/locked_params_top3.json` → valid JSON, 3 configs, selection_metric=sharpe_rf3
- All config keys present: rank, c_yoy, a_cagr, n_proximity, hard_stop, slots, entry_option, metrics
- `docs/audits/phase32-backtest-sweep.md` → all sections present, verified with grep

## Self-Check: PASSED

- `analysis/select_top3_vn100.py` exists ✓
- `tests/phase32/test_top3.py` exists ✓  
- `docs/audits/phase32/locked_params_top3.json` exists ✓
- `docs/audits/phase32-backtest-sweep.md` exists ✓
- Commit `cb25d2e` exists ✓
- Commit `ef14ec9` exists ✓
