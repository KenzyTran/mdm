---
phase: 08-indicator-engine
verified: 2026-03-29T04:30:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
gaps: []
---

# Phase 8: Indicator Engine Verification Report

**Phase Goal:** Build the indicator computation engine that calculates EMA 9/21/55, MA 200, MACD (12,26,9), and Heikin Ashi Smoothed candles on NASDAQ data, then extract feature snapshots at each of the 962 signal dates for downstream rule discovery.
**Verified:** 2026-03-29T04:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | EMA 9/21/55 values computed on NASDAQ close prices match standard recursive EMA formula | VERIFIED | `compute_ema` uses `series.ewm(span=span, adjust=False).mean()`; test_compute_ema_basic validates exact values [1.0, 1.5, 2.25, 3.125, 4.0625]; integration test confirms EMA9 within 5% of close on real data |
| 2 | MA 200 uses min_periods=200 producing NaN for first 199 rows | VERIFIED | `series.rolling(window=window, min_periods=window).mean()` at line 46; test_ma200_nan_count and test_ma200_nan_first_199_rows both pass |
| 3 | MACD line equals EMA12 minus EMA26, signal line is EMA9 of MACD, histogram is MACD minus signal | VERIFIED | Lines 72-81 of indicators.py implement exact formula; test_compute_macd_histogram_identity verifies histogram identity with rtol=1e-10 |
| 4 | Heikin Ashi Smoothed candles use two-stage process: EMA(55) smoothing then HA computation | VERIFIED | `compute_heikin_ashi_smoothed` smooths OHLC with EMA(period=55) then calls `compute_heikin_ashi`; test_compute_heikin_ashi_smoothed_returns_4_columns passes |
| 5 | Feature snapshot contains one row per signal date with all indicator values | VERIFIED | test_full_snapshot_row_count PASSED: exactly 962 rows; test_full_snapshot_columns confirms all required columns present |
| 6 | Weekend signal dates snap to nearest prior trading day (Friday) | VERIFIED | snap_to_trading_day backward search implemented; test_snap_weekend_to_friday, test_snap_searches_backward, test_weekend_signals_snapped (10 weekend rows confirmed) all PASS |
| 7 | No NaN values in feature snapshot after indicator warm-up period (~200 trading days) | VERIFIED | test_full_snapshot_no_nan_after_warmup PASSED for all 11 indicator columns after 1975-06-01; test_no_nan_after_warmup (row 250) PASSED |
| 8 | Derived boolean features capture EMA crossover states and price-vs-MA relationships | VERIFIED | 8 boolean features in feature_snapshot.py (lines 106-113); test_boolean_features_are_bool_dtype confirms dtype=bool; test_full_snapshot_boolean_columns_complete PASSED |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `core/indicators.py` | compute_ema, compute_sma, compute_macd, compute_heikin_ashi, compute_heikin_ashi_smoothed, build_indicator_dataframe | VERIFIED | 179 lines, all 6 functions implemented as module-level pure functions (no class), substantive computation logic throughout |
| `tests/test_indicators.py` | Unit tests for all indicator functions | VERIFIED | 282 lines, 19 test functions across 5 test classes + integration class; imports from core.indicators |
| `core/feature_snapshot.py` | snap_to_trading_day, extract_feature_snapshot | VERIFIED | 119 lines, both functions implemented with full computation logic, 8 boolean features, fillna(False).astype(bool) pattern |
| `tests/test_feature_snapshot.py` | Unit and integration tests for feature extraction | VERIFIED | 350 lines, 17 test functions across 3 test classes including full integration class with scope="module" fixture |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `core/indicators.py` | `pandas ewm/rolling` | `adjust=False` for all EMA calls | VERIFIED | 12 occurrences of `adjust=False` in indicators.py; confirmed in compute_ema, compute_macd (3x), compute_heikin_ashi_smoothed (4x) |
| `tests/test_indicators.py` | `core/indicators.py` | import and verify indicator outputs | VERIFIED | Lines 16-23: `from core.indicators import build_indicator_dataframe, compute_ema, ...` (all 6 functions imported and exercised) |
| `core/feature_snapshot.py` | `core/indicators.py` | receives indicators_df from build_indicator_dataframe | VERIFIED | Design: feature_snapshot.py takes pre-built indicators DataFrame as parameter (no direct import needed); call site in tests/test_feature_snapshot.py line 16: `from core.indicators import build_indicator_dataframe` and used at line 260 to build the snapshot fixture |
| `core/feature_snapshot.py` | `core/signal_loader.py` | uses signal DataFrame structure (date, signal columns) | VERIFIED | Pattern `signals.*date` confirmed: sig["date"] accessed at lines 76, 82; "signal" column used at line 87; signal_loader used in integration fixture at test_feature_snapshot.py line 258 |
| `tests/test_feature_snapshot.py` | `core/feature_snapshot.py` | import and verify snapshot extraction | VERIFIED | Line 15: `from core.feature_snapshot import extract_feature_snapshot, snap_to_trading_day` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `core/indicators.py` | ema9/ema21/ema55/ma200/macd/ha_smooth_* | `series.ewm()` / `series.rolling()` on ohlcv["close"] and ohlcv OHLC columns | Yes — pandas vectorized computations on real OHLCV price data | FLOWING |
| `core/feature_snapshot.py` | indicator columns at signal dates | merge of indicators_df (real computations) with signals_df (962 signal dates) | Yes — left join populates all indicator columns from real computation; 962 rows confirmed by integration test | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 36 tests pass (19 indicators + 17 snapshot) | `uv run python -m pytest tests/test_indicators.py tests/test_feature_snapshot.py -v` | 36 passed, 13 warnings in 16.97s | PASS |
| 962-row snapshot with 10 weekend snaps | `test_full_snapshot_row_count`, `test_weekend_signals_snapped` | PASSED | PASS |
| No NaN after warmup (all 11 indicator columns) | `test_full_snapshot_no_nan_after_warmup` | PASSED after 1975-06-01 | PASS |
| All 6 commits exist in git history | `git log --oneline` grep | 720d5aa, 703ff1e, f5e5426, edfb983, bee0c4c, daa6308 all found | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| IND-01 | 08-01-PLAN.md | EMA 9, EMA 21, EMA 55 computed on daily NASDAQ close prices | SATISFIED | `compute_ema` with span=9/21/55; `build_indicator_dataframe` adds ema9/ema21/ema55 columns; integration test confirms correct values on 52-year NASDAQ data |
| IND-02 | 08-01-PLAN.md | MA 200 (simple) computed on daily NASDAQ close prices | SATISFIED | `compute_sma` with window=200, min_periods=200; `build_indicator_dataframe` adds ma200 column; test_ma200_nan_count confirms correct NaN behavior |
| IND-03 | 08-01-PLAN.md | MACD (12, 26, 9) with signal line and histogram computed on daily close | SATISFIED | `compute_macd(fast=12, slow=26, signal=9)` produces macd/macd_signal/macd_histogram columns; histogram identity test passes with rtol=1e-10 |
| IND-04 | 08-01-PLAN.md | Heikin Ashi Smoothed candles computed from OHLC data | SATISFIED | `compute_heikin_ashi_smoothed(period=55)` two-stage EMA+HA; returns ha_smooth_open/high/low/close; smoothing test confirms lower std than raw close |
| IND-05 | 08-02-PLAN.md | Feature snapshot extracted at each signal date: all indicator values, crossover states, price-vs-MA relationships | SATISFIED | `extract_feature_snapshot` produces 962-row DataFrame with all indicator columns + 8 boolean crossover/relationship features; 10 weekend dates snapped; NaN-free after warmup |

No orphaned requirements — all 5 IND requirements mapped to Phase 8 in REQUIREMENTS.md are claimed by plans 08-01 and 08-02 and verified above.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_indicators.py` | 213, 223, 232, 242, 249, 259, 274 | `@pytest.mark.integration` not registered in pytest config | Info | Tests run correctly but emit PytestUnknownMarkWarning; no functional impact |
| `tests/test_feature_snapshot.py` | 267, 274, 291, 309, 327, 335 | `@pytest.mark.integration` not registered in pytest config | Info | Same warning as above; no functional impact |

No blockers or warnings found. The unregistered mark is cosmetic — all 36 tests pass and integration tests correctly load real data. There are no TODO/FIXME/placeholder patterns, no empty returns, no hardcoded empty data structures in any phase 08 file.

### Human Verification Required

None. All critical behaviors were verified programmatically:
- Exact EMA formula matches verified with known test vectors
- 962-row count confirmed by integration test on real signal fixture
- Weekend date snapping verified with real data (10 known weekend signals)
- No NaN after warmup confirmed on 52-year NASDAQ dataset

### Gaps Summary

No gaps found. All 8 observable truths verified, all 4 artifacts exist and are substantive (non-trivial implementations, no stubs), all key links are wired, data flows from real OHLCV price computations through to the 962-row snapshot output, and all 36 tests pass including integration tests on real NASDAQ data. Requirements IND-01 through IND-05 are fully satisfied.

---

_Verified: 2026-03-29T04:30:00Z_
_Verifier: Claude (gsd-verifier)_
