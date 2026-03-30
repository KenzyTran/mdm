---
phase: 18-short-p-l-comparative-validation
verified: 2026-03-30T09:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 18: Short P&L Comparative Validation — Verification Report

**Phase Goal:** Short P&L in equity curve with long-only comparison, plus rule documentation updates
**Verified:** 2026-03-30T09:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Short position equity goes UP when market goes DOWN during SELL state | VERIFIED | `performance.py` line 100: `equity[i] = equity[i-1] * (closes[i-1] / closes[i])` when `prev_state == "SELL"`. `test_sell_state_market_drop_equity_increases` passes. |
| 2 | Short position equity goes DOWN when market goes UP during SELL state | VERIFIED | Same inverse return formula. `test_sell_state_market_rise_equity_decreases` passes. |
| 3 | Long-only mode treats SELL same as CASH (flat equity) | VERIFIED | `long_only_equity` param in `__init__`, branch `elif prev_state == "SELL" and not self.long_only_equity` falls to flat `else` when `True`. `test_long_only_equity_sell_treated_as_cash` passes. |
| 4 | Comparison script outputs side-by-side metrics for NASDAQ | VERIFIED | `analysis/compare_long_short.py` 258 lines, `print_metrics_table()` outputs Total Return, Annualized Return, Max Drawdown, Sharpe Ratio, Win Rate. Spot-check passed. |
| 5 | Comparison script outputs side-by-side metrics for VN30 | VERIFIED | Same `run_comparison()` function handles both `nasdaq` and `vn30` markets. `argparse` `--market` flag with `choices=['nasdaq', 'vn30']`. |
| 6 | Chart shows 2 equity curves (long-only vs long/short) per market | VERIFIED | `generate_chart()` plots blue `Long/Short` and orange `Long-Only` equity curves, saves to `output/compare_{market}.png`. figsize=(14,7), grid alpha=0.3, legend upper left. |
| 7 | Rule docs describe short entry on SELL signal | VERIFIED | Both docs Section X contain explicit short entry rules, `pnl = (gia_entry - gia_cover) / gia_entry` formula. |
| 8 | Rule docs describe short cover on FTD or MA50 breakout | VERIFIED | Both docs Section X list FTD and MA50 breakout as cover triggers. Hybrid doc adds OVERRIDE path. |
| 9 | Rule docs describe stop loss 1.5% for long and DD5 high for short | VERIFIED | Both docs Section XII: `stop_loss_pct = 0.015`, short stop loss `DD5_high * 1.01`. |
| 10 | Rule docs describe SELL->CASH->BUY transition enforcement | VERIFIED | Both docs Section XI contain `SELL -> CASH -> BUY: KHONG CHO PHEP` and `enter_buy()` ValueError guard. |
| 11 | Rule docs describe volatility-adaptive stop loss mechanism | VERIFIED | Both docs Section XII describe ATR adaptive scaling, formula, clamp range [0.5x, 2.5x], config fields `atr_period = 14`. |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `strategies/mdm_hybrid/performance.py` | V2PerformanceAnalyzer with `long_only_equity` flag and SELL inverse return | VERIFIED | 194 lines, substantive, contains all required patterns |
| `strategies/mdm_v2/performance.py` | Identical copy kept in sync | VERIFIED | 194 lines, `diff` returns no output — files are byte-for-byte identical |
| `tests/test_short_equity.py` | Unit tests for SHORT-02 inverse return, min 50 lines | VERIFIED | 173 lines, 6 test functions in `TestShortEquityCurve` class |
| `analysis/compare_long_short.py` | Comparison script for long-only vs long/short, min 100 lines | VERIFIED | 258 lines, full implementation |
| `docs/rules_mdm_v2.md` | Updated V2 rule doc with Sections X, XI, XII containing "SHORT" | VERIFIED | 357 lines (was 244), 3 new sections appended, contains all required patterns |
| `docs/rules_mdm_hybrid.md` | Updated Hybrid rule doc with Sections X, XI, XII | VERIFIED | 376 lines (was 247), 3 new sections appended, contains all required patterns |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `strategies/mdm_hybrid/performance.py` | `_build_daily_equity()` | `elif prev_state == "SELL" and not self.long_only_equity:` branch | WIRED | Line 98: `elif prev_state == "SELL" and not self.long_only_equity:` |
| `strategies/mdm_hybrid/performance.py` | `_build_daily_equity()` | `closes[i - 1] / closes[i]` inverse return | WIRED | Line 100: `equity[i] = equity[i - 1] * (closes[i - 1] / closes[i])` |
| `analysis/compare_long_short.py` | `V2PerformanceAnalyzer` | `long_only_equity=True` vs `long_only_equity=False` | WIRED | Lines 67-68: two analyzers created from same results with opposing flags |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `analysis/compare_long_short.py` | `long_short.equity`, `long_only.equity` | `HybridEngine.run(df)` results + `V2PerformanceAnalyzer._build_daily_equity()` | Yes — calls `DataLoader(market).load()`, runs full engine loop | FLOWING |
| `tests/test_short_equity.py` | `analyzer.equity` | Synthetic `make_results_df()` with explicit price sequences | Yes — deterministic test data by design | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Unit tests pass (22 total: 6 new + 16 existing) | `uv run python -m pytest tests/test_short_equity.py tests/test_v2_performance.py -x -q` | `22 passed in 0.30s` | PASS |
| Comparison script metrics table renders | Python import of `print_metrics_table` with synthetic data | Formatted side-by-side table with all 5 metrics | PASS |
| `mdm_v2/performance.py` stays in sync | `diff strategies/mdm_v2/performance.py strategies/mdm_hybrid/performance.py` | No output (files identical) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SHORT-02 | 18-01-PLAN.md | P&L tracking for short — gain when market drops, loss when market rises | SATISFIED | `_build_daily_equity()` inverse return formula; all 6 `TestShortEquityCurve` tests pass |
| TRANS-02 | 18-01-PLAN.md | Backtest comparison long-only vs long/short on NASDAQ and VN30 | SATISFIED | `analysis/compare_long_short.py` with dual `V2PerformanceAnalyzer` pattern, metrics table, chart output |
| TRANS-03 | 18-02-PLAN.md | Update rule docs with short rules | SATISFIED | Both docs have Sections X (short), XI (transitions), XII (stop loss) in Vietnamese |

No orphaned requirements: REQUIREMENTS.md maps SHORT-02, TRANS-02, TRANS-03 all to Phase 18, and all three are claimed in plans.

---

### Anti-Patterns Found

None found. Scanned for TODO/FIXME, empty returns, hardcoded empty state, and placeholder comments across all 4 modified/created files. No issues.

---

### Human Verification Required

#### 1. Comparison Script End-to-End with Real Data

**Test:** Run `uv run python analysis/compare_long_short.py --market nasdaq` (requires NASDAQ data file in `data/` directory)
**Expected:** Produces `output/compare_nasdaq.png` and `output/compare_nasdaq.txt` with metrics table and two-line equity chart. Long/Short return should be materially higher than Long-Only (per SUMMARY: +7440% vs +2187%).
**Why human:** Requires actual data file present on the machine and visual inspection of the PNG chart.

#### 2. Comparison Script End-to-End for VN30

**Test:** Run `uv run python analysis/compare_long_short.py --market vn30`
**Expected:** Produces `output/compare_vn30.png` and metrics table. Long/Short +155% vs Long-Only +89% per SUMMARY.
**Why human:** Requires VN30 data file and visual chart inspection.

---

### Gaps Summary

No gaps. All 11 observable truths are verified with code evidence. All 6 required artifacts exist, are substantive (correct implementations, not stubs), and are properly wired. Both plan 01 and plan 02 artifacts verified independently. Commits f435a44, 03ff012, e391614, 98cbb20, 1b51a2a all exist in git history.

---

_Verified: 2026-03-30T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
