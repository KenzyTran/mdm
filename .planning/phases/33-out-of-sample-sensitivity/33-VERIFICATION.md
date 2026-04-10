---
phase: 33-out-of-sample-sensitivity
verified: 2026-04-10T05:00:00Z
status: human_needed
score: 11/11 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 9/11
  gaps_closed:
    - "Sensitivity matrix covers 3 universes x 3 locked configs = 9 runs (liquidity-reconstructed SQL bug fixed; all 9 cells now non-NaN)"
    - "CANSLIM-only baseline (no MDM gate) metrics are computed (periodic CASH->BUY tiling fix; 109 trades, Sharpe=1.047)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Confirm that the failure attribution conclusion in verdict.md Section 7 is actionable for next-phase planning"
    expected: "MDM gate identified as primary bottleneck (Strategy 0.448 < CANSLIM-only 1.047) is a valid, data-backed conclusion and not an artifact of the periodic-CASH tiling methodology"
    why_human: "The periodic-CASH tiling approach (CASH every 19 bars) creates a specific pattern of buy windows. Domain judgment is needed to confirm this approximates 'no MDM gate' semantics faithfully enough to support the attribution conclusion"
---

# Phase 33: Out-of-Sample Sensitivity Verification Report

**Phase Goal:** Validate that the VN100 CANSLIM+MDM strategy generalizes out-of-sample (2019-2025) and is robust to universe/parameter changes — so that Phase 32's in-sample rank-1 result is not a data-mining artifact.
**Verified:** 2026-04-10T05:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (Plan 03 fixed two gaps from initial verification)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | OOS backtest 2019-2025 runs to completion with rank-1 locked params | VERIFIED | oos_nav.csv 1749 rows; oos_metrics.json CAGR=6.23%, Sharpe=0.448, MaxDD=-10.22% |
| 2 | CANSLIM cache is date-range-aware so OOS does not silently reuse in-sample fundamentals | VERIFIED | `build_canslim_raw_frame` computes `canslim_raw_{min_d}_{max_d}.parquet`; confirmed via import inspect check |
| 3 | precompute_static cache is universe-mode-aware so sensitivity runs will not collide | VERIFIED | `precompute_static(period, mode="current-vn100")` signature confirmed; `mode` in parameters |
| 4 | OOS metrics (CAGR, Sharpe_rf3, MaxDD) are computed and printed | VERIFIED | oos_metrics.json contains all 9 required keys with non-zero values |
| 5 | Sensitivity matrix covers 3 universes x 3 locked configs = 9 runs | VERIFIED | sensitivity_matrix.csv: 9 rows, 0 NaN — liquidity-reconstructed SQL bug (closeindex->closeprice) fixed in commit 96084c9; all 3 universe modes produce valid Sharpe values |
| 6 | CANSLIM-only baseline (no MDM gate) metrics are computed | VERIFIED | baselines.json canslim_only: 109 trades, Sharpe_rf3=1.047, CAGR=16.4% — fixed via periodic CASH->BUY tiling (every 19 bars) in sensitivity_vn100.py |
| 7 | MDM-only-on-index baseline NAV + metrics are computed | VERIFIED | baselines.json mdm_only_index: Sharpe_rf3=0.508, MaxDD=-15.60% |
| 8 | VN-Index B&H benchmark Sharpe and MaxDD are computed | VERIFIED | baselines.json vnindex_bh: Sharpe_rf3=0.383, MaxDD=-40.34% |
| 9 | diem_canslim ranking comparison (Spearman rho + top-10 overlap) runs on OOS quarters | VERIFIED | diem_canslim_oos.json: 24 quarters, median_rho=0.365, mean_overlap=2.83/10 |
| 10 | Pass/fail verdict against BT-08 targets is written with component attribution if fail | VERIFIED | verdict.md 3077 chars; BT-08 table present (Sharpe uplift FAIL +0.064, MaxDD reduction PASS 74.7%); Section 7 Failure Attribution identifies MDM gate as primary bottleneck |
| 11 | All output files are auto-generated from data (not hardcoded) | VERIFIED | write_verdict() in sensitivity_vn100.py reads oos_metrics.json, baselines.json, sensitivity_matrix.csv, diem_canslim_oos.json at runtime |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `analysis/_vn100_pipeline.py` | Fixed cache keys for build_canslim_raw_frame and precompute_static | VERIFIED | Date-range cache key confirmed via inspect; mode-aware cache confirmed via signature check |
| `analysis/backtest_vn100_oos.py` | Single-run OOS script with rank-1 locked config | VERIFIED | 3414 bytes; PERIOD=("2019-01-01","2025-12-31"); loads locked_params_top3.json rank-1 |
| `docs/audits/phase33/oos_nav.csv` | OOS daily NAV | VERIFIED | 102058 bytes (1749 rows) |
| `docs/audits/phase33/oos_trades.csv` | OOS trade log | VERIFIED | 8981 bytes (62 trades) |
| `docs/audits/phase33/oos_metrics.json` | OOS metrics with CAGR, Sharpe_rf3, MaxDD | VERIFIED | All required keys; CAGR=0.0623, Sharpe=0.448, MaxDD=-0.102 |
| `analysis/sensitivity_vn100.py` | 9-run sensitivity matrix + baselines | VERIFIED | 36250 bytes; periodic CASH tiling at line 239; precompute_static(mode=) wiring present |
| `docs/audits/phase33/sensitivity_matrix.csv` | 3x3 matrix results | VERIFIED | 9 rows, 0 NaN; liquidity-reconstructed Sharpe values: 0.064, 0.052, 0.052 |
| `docs/audits/phase33/baselines.json` | CANSLIM-only, MDM-only, VN-Index B&H metrics | VERIFIED | canslim_only: 109 trades, Sharpe=1.047; mdm_only_index: Sharpe=0.508; vnindex_bh: Sharpe=0.383 |
| `docs/audits/phase33/diem_canslim_oos.json` | Spearman rho + top-10 overlap for OOS quarters | VERIFIED | median_rho=0.365, mean_overlap=2.83/10, 24 quarters |
| `docs/audits/phase33/verdict.md` | Pass/fail against BT-08 + failure attribution | VERIFIED | 3077 chars; all required sections present; CANSLIM-only row shows non-zero Sharpe (1.047) |
| `strategies/canslim/universe.py` | SQL uses closeprice (not closeindex) | VERIFIED | Line 78: `AVG(closeprice * totalvol) AS adv`; no occurrence of closeindex |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| analysis/backtest_vn100_oos.py | analysis/_vn100_pipeline.py | run_vn100_backtest() | WIRED | Import and call confirmed |
| analysis/backtest_vn100_oos.py | docs/audits/phase32/locked_params_top3.json | json.load for rank-1 config | WIRED | LOCKED_PARAMS path + cfg1["rank"]==1 assert |
| analysis/sensitivity_vn100.py | analysis/_vn100_pipeline.py | precompute_static(mode=) + run_vn100_backtest() | WIRED | precompute_static(period, mode=mode) at line ~152 |
| analysis/sensitivity_vn100.py | docs/audits/phase32/locked_params_top3.json | json.load for all 3 configs | WIRED | All 3 configs loaded |
| docs/audits/phase33/verdict.md | docs/audits/phase33/oos_metrics.json | strategy metrics for pass/fail | WIRED | write_verdict() reads oos_metrics.json; Sharpe_rf3=0.448 in verdict table |
| strategies/canslim/universe.py | stock_eod table | SQL AVG(closeprice * totalvol) | WIRED | closeprice column confirmed; closeindex removed |
| analysis/sensitivity_vn100.py | strategies/entry/window.py | CASH->BUY transition triggers compute_buy_windows | WIRED | Periodic CASH insert at iloc[i] every 19 bars (line 239) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| oos_nav.csv | nav_df from run_vn100_backtest() | DB queries via _vn100_pipeline.py | Yes — 1749 rows, CAGR=6.23% | FLOWING |
| oos_metrics.json | metrics dict | _compute_metrics() on nav_df | Yes — all 9 keys non-zero | FLOWING |
| sensitivity_matrix.csv | 9-row DataFrame | Pool workers calling run_vn100_backtest() | Yes — 9/9 rows non-NaN after SQL fix | FLOWING |
| baselines.json canslim_only | Sharpe_rf3=1.047 | run_vn100_backtest() with periodic-CASH gate override | Yes — 109 trades after tiling fix | FLOWING |
| baselines.json mdm_only_index | nav Series | VN-Index + MDM gate state machine | Yes — CAGR=8.01%, Sharpe=0.508 | FLOWING |
| baselines.json vnindex_bh | nav Series | data/vnindex.csv normalized close | Yes — CAGR=10.42%, Sharpe=0.383 | FLOWING |
| diem_canslim_oos.json | rho + overlap per quarter | MySQL canslim table + Spearman scipy | Yes — 24 quarters | FLOWING |
| verdict.md | All BT-08 numbers | json.load from oos_metrics.json + baselines.json | Yes — auto-generated; canslim_only row shows 1.047, not 0.000 | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| oos_metrics.json has required keys with non-zero values | uv run python assert CAGR>0 and Sharpe_rf3>0 | CAGR=0.0623, Sharpe_rf3=0.448 | PASS |
| sensitivity_matrix.csv has 9 non-NaN rows | uv run python — has NaN check | 9 rows, Has NaN: False | PASS |
| baselines.json canslim_only has >0 trades and non-zero Sharpe | uv run python assert num_trades>0 and Sharpe!=0 | 109 trades, Sharpe=1.047 | PASS |
| universe.py contains closeprice not closeindex | grep on file | Line 78: AVG(closeprice * totalvol) AS adv | PASS |
| sensitivity_vn100.py has periodic CASH tiling | grep for iloc.*CASH | Line 239: all_buy.iloc[i] = "CASH" | PASS |
| verdict.md is >1000 chars with FAIL verdict and Failure Attribution | wc + content check | 3077 chars; FAIL verdict; Section 7 present; canslim_only Sharpe=1.047 in table | PASS |
| _vn100_pipeline.py cache fixes intact | import inspect check | mode param present; canslim_raw_{min_d}_{max_d} pattern present | PASS |
| Gap closure commit exists | git log | 96084c9 fix(33-03): fix SQL column bug + canslim_only baseline transition | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BT-03 | 33-01-PLAN.md | Out-of-sample run 2019-2025 with locked parameters | SATISFIED | analysis/backtest_vn100_oos.py PERIOD=("2019-01-01","2025-12-31") with rank-1 locked params; oos_metrics.json populated with all required keys |
| BT-04 | 33-02-PLAN.md, 33-03-PLAN.md | Sensitivity runs across (a) current VN100 (b) liquidity-reconstructed (c) VN30-only | SATISFIED | All 9 cells in sensitivity_matrix.csv are non-NaN after SQL fix; 3 universe modes produce valid Sharpe values (0.448, 0.064, 0.268 for rank-1) |
| BT-08 | 33-02-PLAN.md, 33-03-PLAN.md | Validation targets — Sharpe uplift > 0.20 vs benchmark, MaxDD reduction > 30% vs B&H | SATISFIED | verdict.md: Sharpe uplift FAIL (+0.064 vs threshold 0.20); MaxDD reduction PASS (74.7% vs threshold 30%); Failure Attribution section identifies MDM gate as primary bottleneck using valid canslim_only Sharpe=1.047 data |

**Orphaned requirements check:** BT-03, BT-04, BT-08 all claimed by plan frontmatter and verified against REQUIREMENTS.md. All are marked [x] in REQUIREMENTS.md. No orphaned requirements for Phase 33.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| analysis/sensitivity_vn100.py | ~239 | Periodic CASH tiling (every 19 bars) to approximate "no MDM gate" baseline | Info | Methodology works (produces 109 trades, Sharpe=1.047) but differs from Plan 03 spec (which said `iloc[0] = "CASH"`). The tiling is a deliberate improvement, documented in SUMMARY. No blocking issue. |
| docs/audits/phase33/verdict.md | - | cost drag ratio reported as 9.5521 (ratio, not %) in the OOS metrics table | Info | Cosmetic: "Cost drag (ratio): 9.5521" is ambiguous unit. Not a data or logic issue. |

---

### Re-verification Summary

**Previous status:** gaps_found (score: 9/11)
**Current status:** human_needed (score: 11/11)

Both gaps are confirmed closed:

**Gap 1 closed — liquidity-reconstructed universe now produces valid data:**
- `strategies/canslim/universe.py` line 78: `AVG(closeprice * totalvol) AS adv` (closeindex removed)
- `docs/audits/phase33/sensitivity_matrix.csv`: 9 rows, 0 NaN — liquidity-reconstructed Sharpe values are 0.064, 0.052, 0.052 (low but valid)
- Commit: 96084c9

**Gap 2 closed — CANSLIM-only baseline now produces real trades:**
- `analysis/sensitivity_vn100.py` line 239: periodic CASH insert every 19 bars creates 92 overlapping buy windows
- `docs/audits/phase33/baselines.json` canslim_only: 109 trades, Sharpe_rf3=1.047, CAGR=16.4%
- `docs/audits/phase33/verdict.md` Section 5 Baseline Comparison shows CANSLIM-only Sharpe=1.047 (not 0.000)
- Failure Attribution in Section 7 now correctly identifies MDM gate as primary bottleneck

**No regressions detected.** All 7 behavioral spot-checks pass. All previously-verified truths remain intact.

### Human Verification Required

**1. Confirm canslim_only baseline methodology is valid for failure attribution**

- **Test:** Review the periodic CASH->BUY tiling approach (every 19 bars = ~1 month) in `analysis/sensitivity_vn100.py` lines 228-239. Determine whether injecting CASH every 19 bars faithfully represents "always available to enter" semantics, or whether the 19-bar window structure introduces systematic selection bias (only stocks eligible in 20-trading-day windows, repeating monthly)
- **Expected:** The periodic tiling is a valid approximation — CANSLIM stock selection drives the Sharpe=1.047 result, confirming that MDM gate (Sharpe reduced from 1.047 to 0.448) is the genuine bottleneck, not a measurement artifact of the tiling method
- **Why human:** Requires domain judgment on whether 20-day buy windows repeating monthly are equivalent to "no gate" for the purposes of isolating the MDM gate contribution. Cannot determine programmatically whether the tiling pattern itself introduces favorable/unfavorable selection timing.

---

_Verified: 2026-04-10T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — after Plan 03 gap closure_
