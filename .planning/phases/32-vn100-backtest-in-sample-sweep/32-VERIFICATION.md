---
phase: 32-vn100-backtest-in-sample-sweep
verified: 2026-04-10T10:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 32: VN100 Backtest + In-Sample Sweep — Verification Report

**Phase Goal:** Run a full VN100 in-sample backtest (2014-2018) with a 1,536-config parameter sweep, select the top-3 configs by Sharpe, and hand off locked parameters to Phase 33.
**Verified:** 2026-04-10
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | pytest scaffold passes (pyarrow, tqdm, multiprocessing) | VERIFIED | 21 tests pass in 0.39s across all 4 test files |
| 2 | Single VN100 backtest 2014-2018 runs end-to-end without errors (BT-01) | VERIFIED | `analysis/backtest_vn100.py` exists, PERIOD hard-coded, 3 CSVs written |
| 3 | Pipeline helper is reusable from sweep script | VERIFIED | `run_vn100_backtest` + `precompute_static` exported; `sweep_vn100.py` imports from `analysis._vn100_pipeline` |
| 4 | 1,536-config sweep runs to completion (BT-02 / SC2) | VERIFIED | `sweep_results.csv` has 1,537 lines (header + 1536 rows) |
| 5 | `sweep_results.csv` contains per-config metrics with `sanity_flag` (SC3, SC5) | VERIFIED | Header contains all 17 expected columns including `sanity_flag` and `error` |
| 6 | Multiprocessing parallelism active (D-06) | VERIFIED | `Pool(cpu_count()-1)` and `imap_unordered` present in `sweep_vn100.py` |
| 7 | Top-3 configs by Sharpe_rf3 selected (BT-02 / SC4) | VERIFIED | `locked_params_top3.json` has 3 configs, ranked by Sharpe_rf3 |
| 8 | `locked_params_top3.json` schema valid for Phase 33 handoff (D-14) | VERIFIED | JSON validated: `selection_metric=sharpe_rf3`, all required keys present in each config |
| 9 | Sanity gate enforced on top-3 (D-13) | VERIFIED | `select_top3()` raises `RuntimeError` on non-OK flag; all 1536 configs are `OK` |
| 10 | Phase 32 audit report covers methodology + single-run + sweep + top-3 (D-16) | VERIFIED | `docs/audits/phase32-backtest-sweep.md` exists with all 8 required sections |

**Score: 10/10 truths verified**

---

### Required Artifacts

| Artifact | Provided | Status | Details |
|----------|----------|--------|---------|
| `tests/phase32/__init__.py` | Wave 0 scaffold | VERIFIED | Exists, 0 bytes (package marker) |
| `tests/phase32/conftest.py` | synthetic_ohlc + synthetic_universe fixtures | VERIFIED | 1,286 bytes, fixtures present |
| `tests/phase32/test_scaffold.py` | env import check | VERIFIED | 544 bytes, 3 tests |
| `analysis/_vn100_pipeline.py` | run_vn100_backtest + precompute_static helper | VERIFIED | 698 lines (exceeds 100 min), all key wiring patterns present |
| `analysis/backtest_vn100.py` | single-run baseline script | VERIFIED | 3,095 bytes, PERIOD hard-coded to 2014-01-01..2018-12-31 |
| `docs/audits/phase32/single_run_nav.csv` | daily NAV series | VERIFIED | 68,688 bytes (1,246 daily rows) |
| `docs/audits/phase32/single_run_trades.csv` | trade log | VERIFIED | 9,018 bytes (60 trades) |
| `docs/audits/phase32/single_run_positions.csv` | position log | VERIFIED | 89,824 bytes |
| `analysis/sweep_vn100.py` | full grid sweep with multiprocessing | VERIFIED | 197 lines (exceeds 150 min), multiprocessing.Pool + tqdm + sanity_flag present |
| `docs/audits/phase32/sweep_results.csv` | 1,536 sweep rows | VERIFIED | 1,537 lines (header + 1536), all metric + sanity_flag columns |
| `analysis/select_top3_vn100.py` | top-3 selection with tie-breakers | VERIFIED | 5,079 bytes, select_top3/to_json_payload/main all present |
| `docs/audits/phase32/locked_params_top3.json` | Phase 33 handoff JSON | VERIFIED | Valid JSON, 3 configs, all D-14 keys confirmed by live Python validation |
| `docs/audits/phase32-backtest-sweep.md` | Phase 32 audit report | VERIFIED | All sections present (Methodology, BT-01, BT-02, Top-3, Sanity, Artifacts, Handoff, Notes) |
| `docs/audits/phase32/cache/*.parquet` | precomputed static data | VERIFIED | 6 parquet files present (canslim_raw, ohlc, mdm_gate, universe, fundamentals, foreign) |
| `tests/phase32/test_pipeline.py` | pipeline unit tests | VERIFIED | 5,072 bytes, 6 tests |
| `tests/phase32/test_sweep.py` | sweep unit tests | VERIFIED | 2,932 bytes, 5 tests |
| `tests/phase32/test_top3.py` | top-3 selection unit tests | VERIFIED | 6,149 bytes, 7 tests |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/phase32/test_scaffold.py` | pyarrow, tqdm, multiprocessing | import statements | VERIFIED | Pattern confirmed in file |
| `analysis/_vn100_pipeline.py` | `strategies/portfolio/engine.py` | PortfolioEngine import | VERIFIED | `from strategies.portfolio.engine import PortfolioEngine` present at line 46 |
| `analysis/_vn100_pipeline.py` | `strategies/canslim/config.py` | CanslimConfig | VERIFIED | `from strategies.canslim.config import CanslimConfig` at line 44 |
| `analysis/_vn100_pipeline.py` | `connectors/adjust.py` | adjust_ohlc | VERIFIED | `adjust_ohlc` imported and called at line 184 |
| `analysis/_vn100_pipeline.py` | `strategies/mdm_hybrid/mdm_hybrid_engine.py` | HybridEngine | VERIFIED | `HybridEngine` imported and instantiated at line 212 |
| `analysis/_vn100_pipeline.py` | look-ahead discipline | `state[i-1]` | VERIFIED | Comment at lines 29,31 enforces discipline; cited `feedback_equity_formula.md` |
| `analysis/sweep_vn100.py` | `analysis/_vn100_pipeline.py` | run_vn100_backtest + precompute_static | VERIFIED | `from analysis._vn100_pipeline` import confirmed |
| `analysis/sweep_vn100.py` | multiprocessing.Pool | Pool(cpu_count()-1).imap_unordered | VERIFIED | Pattern `multiprocessing.*Pool` confirmed in file |
| `analysis/select_top3_vn100.py` | `docs/audits/phase32/sweep_results.csv` | pandas.read_csv input | VERIFIED | `SWEEP_CSV = Path("docs/audits/phase32/sweep_results.csv")` at line 23 |
| `analysis/select_top3_vn100.py` | `docs/audits/phase32/locked_params_top3.json` | json.dump output | VERIFIED | `OUTPUT_JSON = Path("docs/audits/phase32/locked_params_top3.json")` at line 24 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_vn100_pipeline.py` | `nav`, `trades`, `positions` | PortfolioEngine.run() over real OHLC from Postgres | Yes — baseline run CAGR 4.17%, 60 trades, non-trivial NAV curve | FLOWING |
| `sweep_results.csv` | CAGR, Sharpe_rf3, MaxDD per config | `run_vn100_backtest` with real CANSLIM scoring (plan-02 fix wired real scorer replacing plan-01 stub) | Yes — 4 unique CAGRs confirmed on 4-config smoke, median CAGR 1.87% across 1536 | FLOWING |
| `locked_params_top3.json` | top-3 rows | `select_top3()` reads `sweep_results.csv` | Yes — rank 1: CAGR 3.79%, Sharpe 0.0590, verified at selection time | FLOWING |

**Known stubs documented and acceptable:**
- RS frame stub (`rs_value=80`): above `rs_threshold=70` default, effectively disables RS-streak exit. Acknowledged in audit report Notes section. RS axis not part of the sweep grid — not a gap for Phase 32 scope.
- Fundamentals / foreign flow loaders: best-effort (empty frame on schema drift). Only C/A/N axes swept. Documented in audit report.
- CANSLIM stub from plan-01 (score=100): replaced in plan-02 by real scorer with `build_canslim_raw_frame`. No longer present in production code path.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 21 phase32 tests pass | `uv run pytest tests/phase32/ -x -q` | 21 passed in 0.39s | PASS |
| build_grid() yields exactly 1536 configs | `from analysis.sweep_vn100 import build_grid; assert len(build_grid())==1536` | exit 0 | PASS |
| locked_params JSON valid with 3 configs | `json.load(); assert len(configs)==3; assert selection_metric=='sharpe_rf3'` | exit 0, "JSON OK" | PASS |
| sweep_results.csv has 1537 lines | `wc -l sweep_results.csv` | 1537 | PASS |
| sweep_results.csv header has sanity_flag | first row checked | all 17 columns including sanity_flag and error | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BT-01 | 32-00, 32-01 | Single VN100 backtest 2014-2018 runs end-to-end, outputs trade log + position log + daily NAV | SATISFIED | `backtest_vn100.py` runs; 3 CSVs written; CAGR 4.17%, 60 trades confirmed in audit report |
| BT-02 | 32-02, 32-03 | 1,536-config sweep; top-3 by Sharpe; sanity gate; locked JSON handoff | SATISFIED | `sweep_results.csv` 1536 rows; `locked_params_top3.json` valid 3 configs; all 1536 OK; report written |

---

### Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `analysis/_vn100_pipeline.py` | `rs_value=80` hardcoded stub | Info | Intentional and documented — RS axis not swept; acknowledged in audit report and plan summaries. Does not affect C/A/N sweep validity. |
| `analysis/_vn100_pipeline.py` | Foreign/fundamentals empty frames on schema drift | Info | Intentional and documented — load-bearing only for I/L CANSLIM axes which are out of scope. |

No blockers found. No warnings that affect Phase 32 goal achievement.

---

### Human Verification Required

None. All automated checks pass and human checkpoint (Task 3 of plan 03) was explicitly approved by the user prior to this verification (documented in 32-03-SUMMARY.md: "Task 3: checkpoint:human-verify (APPROVED)").

---

## Commits Verified

All commits referenced in summaries confirmed present in git log:

| Commit | Plan | Description |
|--------|------|-------------|
| `cf190d5` | 32-00 | test(32-00): add phase32 scaffold tests and env deps |
| `6c46e82` | 32-01 | feat(32-01): add VN100 backtest pipeline helper (BT-01 Task 1) |
| `4498856` | 32-01 | feat(32-01): add single-run VN100 baseline script (BT-01 Task 2) |
| `fcab772` | 32-02 | feat(32-02): sweep_vn100.py with multiprocessing + sanity flag |
| `4251ca1` | 32-02 | fix(32-02): wire real CANSLIM scorer via threshold-driven raw precompute |
| `cb25d2e` | 32-03 | feat(32-03): top-3 selector + locked_params JSON + tests |
| `ef14ec9` | 32-03 | docs(32-03): Phase 32 audit report with sweep stats + top-3 table |

---

## Gaps Summary

No gaps. All 10 observable truths verified, all 17 artifacts present and substantive, all 10 key links wired, data flows confirmed from real database through pipeline to final JSON output.

---

_Verified: 2026-04-10T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
