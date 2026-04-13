---
phase: 37-backtest-validation
verified: 2026-04-13T07:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 37: Backtest Validation — Verification Report

**Phase Goal:** Validate v8.0 — run in-sample sweep to select best formula+config, then run OOS backtest 2019-2025 and produce three-way comparison (v8.0 vs v7.0 vs VN-Index B&H).
**Verified:** 2026-04-13T07:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `build_momentum_raw_frame` accepts `formula` kwarg and produces different `rs_rating` for each formula | VERIFIED | Lines 790-866 in `_vn100_pipeline.py`; `roc126` branch uses `close/close.shift(126)-1`; `weighted_roc` uses 4-lookback weighted sum; test 3 confirms divergent output |
| 2 | `run_v8_backtest` accepts `formula` kwarg and passes it through to `build_momentum_raw_frame` | VERIFIED | Line 447 adds `formula: str = "weighted_roc"`; line 519: `build_momentum_raw_frame(panel, formula=formula)` |
| 3 | Cache filename encodes formula — separate parquet files per formula | VERIFIED | Line 816: `f"momentum_raw_{formula}_{min_d}_{max_d}.parquet"`; test 5 confirms roc126 cache contains "roc126" in name |
| 4 | Sweep runs 216 configs (2 formulas x 108 combos) over 2016-2018; output contains both formula values | VERIFIED | `sweep_v8_results.csv` has 216 data rows (217 lines incl. header); `grep -c weighted_roc` = 108, `grep -c roc126` = 108 |
| 5 | `locked_params_v8.json` contains winning config selected by highest Sharpe_rf3 with sanity gates | VERIFIED | `rs_formula=roc126`, `rs_threshold=70.0`, `Sharpe_rf3=0.7019`, `CAGR=0.1135`, `MaxDD=-0.0845`; all required keys present |
| 6 | OOS run uses `locked_params_v8.json` — formula and all params from in-sample sweep, not hardcoded | VERIFIED | `backtest_vn100_v8_oos.py` line 24 loads `locked_params_v8.json`; line 84: `formula=best["rs_formula"]` |
| 7 | `oos_metrics_v8.json` contains CAGR, Sharpe_rf3, MaxDD and all `_compute_metrics` fields | VERIFIED | File contains: CAGR=0.1003, Sharpe_rf3=0.6450, MaxDD=-0.2489, MaxDD_duration_days=1027, hit_rate, turnover, total_cost_drag_pct, num_trades, avg_hold_days |
| 8 | `comparison_table.json` has exactly 3 rows: v8.0, v7.0, VN-Index B&H | VERIFIED | 3 rows confirmed: "v8.0 (RS+N+MDM, roc126)", "v7.0 (CANSLIM+MDM)", "VN-Index B&H" |
| 9 | `oos_nav_v8.csv` and `oos_trades_v8.csv` are non-empty with real data | VERIFIED | `oos_nav_v8.csv`: 1749 data rows (2019-01-02 to end); `oos_trades_v8.csv`: 92 trades with buy/sell prices and PnL |
| 10 | All 7 unit tests in `tests/phase37/test_formula_param.py` pass | VERIFIED | `uv run pytest tests/phase37/test_formula_param.py -v` → 7 passed in 0.40s |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `analysis/_vn100_pipeline.py` | VERIFIED | `formula` kwarg added to both `build_momentum_raw_frame` (line 790) and `run_v8_backtest` (line 447); pass-through at line 519 |
| `analysis/sweep_vn100_v8.py` | VERIFIED | 229 lines; exports `build_grid` and `main`; calls `run_v8_backtest(formula=config["rs_formula"])` |
| `analysis/backtest_vn100_v8_oos.py` | VERIFIED | 134 lines; exports `main`; loads locked params; calls `run_v8_backtest(..., formula=best["rs_formula"])` |
| `docs/audits/phase37/locked_params_v8.json` | VERIFIED | Contains `rs_formula`, `rs_threshold`, `Sharpe_rf3`, `CAGR`, `MaxDD` and 6 additional metric fields |
| `docs/audits/phase37/sweep_v8_results.csv` | VERIFIED | 216 data rows; both `weighted_roc` (108 rows) and `roc126` (108 rows) present |
| `docs/audits/phase37/oos_metrics_v8.json` | VERIFIED | All required fields including `Sharpe_rf3` |
| `docs/audits/phase37/oos_nav_v8.csv` | VERIFIED | 1749 rows; columns: date, nav, cash, deployed_pct, open_slots |
| `docs/audits/phase37/oos_trades_v8.csv` | VERIFIED | 92 rows; columns: ticker, buy_date, buy_price, sell_date, sell_price, pnl_pct, exit_reason |
| `docs/audits/phase37/comparison_table.json` | VERIFIED | 3 entries with v8.0, v7.0, VN-Index B&H |
| `tests/phase37/__init__.py` | VERIFIED | Exists |
| `tests/phase37/test_formula_param.py` | VERIFIED | 325 lines; 7 tests |
| `37-01-SUMMARY.md` | VERIFIED | Documents Plan 01 completion with commits |
| `37-02-SUMMARY.md` | VERIFIED | Documents Plan 02 completion with commits |
| `37-03-SUMMARY.md` | VERIFIED | Documents Plan 03 completion with commits |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_vn100_pipeline.py (run_v8_backtest)` | `_vn100_pipeline.py (build_momentum_raw_frame)` | `formula` kwarg pass-through | WIRED | Line 519: `build_momentum_raw_frame(panel, formula=formula)` |
| `_vn100_pipeline.py (build_momentum_raw_frame)` | RS rating computation block | formula branch: weighted_roc vs roc126 | WIRED | Lines 856-866 implement both branches correctly |
| `analysis/sweep_vn100_v8.py` | `_vn100_pipeline.py (run_v8_backtest)` | worker calls with `formula=config["rs_formula"]` | WIRED | Line 129: `formula=config["rs_formula"]` |
| `analysis/sweep_vn100_v8.py` | `docs/audits/phase37/locked_params_v8.json` | best row written after sweep | WIRED | Line 63 defines `LOCKED_PARAMS` path; winner written via JSON dump |
| `analysis/backtest_vn100_v8_oos.py` | `docs/audits/phase37/locked_params_v8.json` | `json.load` at script start | WIRED | Line 24: `LOCKED_PARAMS = Path("docs/audits/phase37/locked_params_v8.json")` |
| `analysis/backtest_vn100_v8_oos.py` | `_vn100_pipeline.py (run_v8_backtest)` | `run_v8_backtest(..., formula=best["rs_formula"])` | WIRED | Line 84: `formula=best["rs_formula"]` |
| `docs/audits/phase37/oos_metrics_v8.json` | `docs/audits/phase37/comparison_table.json` | v8 metrics merged with V7 + VNINDEX constants | WIRED | v8.0 row in comparison_table uses CAGR=0.1003 and Sharpe_rf3=0.645 matching oos_metrics exactly |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 7 unit tests pass | `uv run pytest tests/phase37/test_formula_param.py -v` | 7 passed in 0.40s | PASS |
| `locked_params_v8.json` has all required keys | Python json.load + key check | All 5 required keys present | PASS |
| `comparison_table.json` has 3 rows with correct labels | Python json.load + count | 3 rows: v8.0, v7.0, VN-Index B&H | PASS |
| `sweep_v8_results.csv` has both formula values (108 rows each) | grep -c | 108 weighted_roc + 108 roc126 = 216 | PASS |
| OOS NAV and trades are non-empty real data | wc -l | 1749 NAV rows, 92 trade rows | PASS |
| All 6 documented commits exist in git history | git log | 1ab1af4, d2604f9, 1a4faef, 50c698d, efb94bd, d536e9b all present | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BT-01 | Plan 02 | In-sample sweep 2016-2018 so sanh 2 RS formula, chon formula tot hon | SATISFIED | `sweep_vn100_v8.py` runs 216 configs; `locked_params_v8.json` selects roc126 by Sharpe_rf3=0.702 |
| BT-02 | Plan 03 | OOS 2019-2025 voi formula duoc chon tu in-sample | SATISFIED | `backtest_vn100_v8_oos.py` loads locked params; OOS metrics written: CAGR=10.0%, Sharpe=0.645 |
| BT-03 | Plan 03 | So sanh vs v7.0 baseline va VN-Index B&H | SATISFIED | `comparison_table.json` has all 3 rows with full metrics for three-way comparison |

---

### Anti-Patterns Found

None detected. Scanned `sweep_vn100_v8.py`, `backtest_vn100_v8_oos.py`, and `test_formula_param.py` for TODO/FIXME/placeholder/stub patterns — clean.

---

### Human Verification Required

#### 1. Comparison table console output

**Test:** Run `uv run python analysis/backtest_vn100_v8_oos.py` and confirm the comparison table prints in human-readable form.
**Expected:** Tabular output showing v8.0, v7.0, VN-Index B&H with CAGR/Sharpe/MaxDD side by side.
**Why human:** Cannot run full backtest script in verification (requires DB connection and 1–2 minute execution time). The artifact exists and wiring is verified; console output format is a UX check.

#### 2. v8.0 verdict interpretation

**Test:** Review `comparison_table.json` values against the phase goal of "validating v8.0."
**Expected:** Report should clearly state whether v8.0 beats, matches, or trails v7.0 — confirmed by SUMMARY (v8.0 trails: Sharpe 0.645 vs 0.813, CAGR near-parity 10.0% vs 10.2%, MaxDD worse -24.9% vs -16.3%).
**Why human:** Business interpretation of whether this verdict is acceptable and what action follows (archive v8, continue development, etc.).

---

## Gaps Summary

No gaps. All 10 observable truths verified, all 13 artifacts confirmed to exist with substantive content, all 7 key links wired, all 3 requirements satisfied, 6 commits verified in git history, 7 unit tests pass at runtime.

The phase goal is fully achieved: in-sample formula selection (roc126 wins 2016-2018), OOS validation (2019-2025), and three-way comparison table all exist with real computed data.

---

_Verified: 2026-04-13T07:00:00Z_
_Verifier: Claude (gsd-verifier)_
