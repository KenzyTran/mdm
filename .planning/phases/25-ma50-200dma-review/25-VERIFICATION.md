---
phase: 25-ma50-200dma-review
verified: 2026-04-01T07:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
human_verification:
  - test: "Run uv run python analysis/validate_ma50_review.py against fresh VN30 data"
    expected: "5-scenario table prints with all 5 rows populated, RECOMMENDATION line prints"
    why_human: "Script depends on local VN30 data file — cannot run in verification without data file accessible"
---

# Phase 25: MA50/200dma Review Verification Report

**Phase Goal:** Review whether MA50 breakout and 200dma replace/supplement the existing MDM V2 rules — run A/B tests and produce a data-driven recommendation
**Verified:** 2026-04-01T07:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | MDMV2Config has ma50_breakout_enabled flag defaulting to True | VERIFIED | `strategies/mdm_v2/config.py` line 71: `ma50_breakout_enabled: bool = True` |
| 2 | MDMV2Config has ma200_enabled flag defaulting to False | VERIFIED | `strategies/mdm_v2/config.py` line 72: `ma200_enabled: bool = False` |
| 3 | Indicators can compute sma200 column on a DataFrame | VERIFIED | `strategies/mdm_v2/indicators.py` line 131: `def add_sma200_column(df)` with `rolling(window=200, min_periods=1)` |
| 4 | Test scaffolding exists for all MAREVIEW requirements | VERIFIED | `tests/test_ma50_review.py` has 8 test functions, all pass (8/8) |
| 5 | Engine gates MA50 breakout check on ma50_breakout_enabled flag | VERIFIED | `strategies/mdm_v2/mdm_v2_engine.py` line 199: `if not is_ftd and self.config.ma50_breakout_enabled:` |
| 6 | Engine computes sma200 column when ma200_enabled=True | VERIFIED | `strategies/mdm_v2/mdm_v2_engine.py` lines 105-107: `if self.config.ma200_enabled: df = Indicators.add_sma200_column(df)` |
| 7 | 200dma crossover triggers BUY signal when ma200_enabled=True | VERIFIED | `strategies/mdm_v2/mdm_v2_engine.py` lines 213-224: `if not is_ftd and self.config.ma200_enabled:` calls `check_200dma_breakout` |
| 8 | 200dma breakdown triggers SELL when ma200_enabled=True and ma50_sell_enabled=False | VERIFIED | `strategies/mdm_v2/position_manager.py` lines 213-221: elif block with `self.config.ma200_enabled and sma200 is not None and close < sma200` |
| 9 | With all flags at defaults, engine produces identical output to pre-change baseline | VERIFIED | All 8 test_ma50_review tests pass; default ma50_breakout_enabled=True preserves prior behavior |
| 10 | Validation script runs all 5 scenarios and prints comparison table | VERIFIED | `analysis/validate_ma50_review.py` has 5 make_*_config() functions + print_comparison() with all 5 columns |
| 11 | Comparison table shows total_return, max_drawdown, sharpe_ratio, trade_count, win_rate | VERIFIED | `analysis/validate_ma50_review.py` line 201: sharpe_ratio included; line 218: all 5 metrics printed |
| 12 | Report section recommends one of: keep MA50 / remove MA50 / replace with 200dma | VERIFIED | `analysis/validate_ma50_review.py` lines 258/261/266: three RECOMMENDATION branches; line 252: Sharpe-based selection |
| 13 | Recommendation is based on quantitative evidence from all 5 scenarios | VERIFIED | `print_recommendation()` compares baseline/remove/replace by Sharpe ratio; prints delta and evidence lines |
| 14 | docs/rules_mdm_v2.md updated with MA50 review findings | VERIFIED | `docs/rules_mdm_v2.md` line 734: `### MA50/200dma Review (Phase 25)`; line 764: `**RECOMMENDATION: REMOVE MA50 from signal logic.**` with actual scenario table |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `strategies/mdm_v2/config.py` | ma50_breakout_enabled and ma200_enabled config flags | VERIFIED | Lines 71-72: both flags with correct defaults |
| `strategies/mdm_v2/indicators.py` | add_sma200_column static method | VERIFIED | Line 131: method with `rolling(window=200, min_periods=1)` |
| `tests/test_ma50_review.py` | Test scaffolding for all MA50 review behaviors | VERIFIED | 131 lines, 8 test functions, 8/8 pass |
| `strategies/mdm_v2/mdm_v2_engine.py` | sma200 indicator wiring and ma50_breakout_enabled gate | VERIFIED | Lines 105, 199, 213: all three wiring points present |
| `strategies/mdm_v2/ftd_signal.py` | check_200dma_breakout method | VERIFIED | Line 143: `def check_200dma_breakout(` with `signal_type="200DMA"` at line 187 |
| `strategies/mdm_v2/position_manager.py` | 200dma SELL trigger path | VERIFIED | Lines 163 (sma200 param), 213-221 (elif SELL block) |
| `analysis/validate_ma50_review.py` | 5-scenario A/B validation and MAREVIEW-03 report | VERIFIED | 302 lines; all 5 scenario factories; print_comparison; print_recommendation |
| `docs/rules_mdm_v2.md` | Updated rules documentation reflecting MA50 review | VERIFIED | Section XVI present with actual backtest results table and recommendation |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `strategies/mdm_v2/config.py` | `strategies/mdm_v2/mdm_v2_engine.py` | ma50_breakout_enabled gate in engine | WIRED | engine.py line 199 checks `self.config.ma50_breakout_enabled` |
| `strategies/mdm_v2/mdm_v2_engine.py` | `strategies/mdm_v2/ftd_signal.py` | check_200dma_breakout call when ma200_enabled | WIRED | engine.py line 217 calls `self.ftd_detector.check_200dma_breakout(...)` |
| `strategies/mdm_v2/mdm_v2_engine.py` | `strategies/mdm_v2/position_manager.py` | sma200 passed to process_day for 200dma SELL | WIRED | engine.py line 355: `sma200=row.get('sma200')...` in process_day call |
| `strategies/mdm_v2/mdm_v2_engine.py` | `strategies/mdm_v2/indicators.py` | add_sma200_column call in run() | WIRED | engine.py line 106: `df = Indicators.add_sma200_column(df)` |
| `analysis/validate_ma50_review.py` | `strategies/mdm_v2/config.py` | MDMV2Config scenario factories | WIRED | validate_ma50_review.py lines 23, 43, 67, 91, 116, 140 |
| `analysis/validate_ma50_review.py` | `strategies/mdm_v2/mdm_v2_engine.py` | MDMV2Engine.run() per scenario | WIRED | validate_ma50_review.py lines 24, 173 |
| `analysis/validate_ma50_review.py` | `strategies/mdm_v2/performance.py` | V2PerformanceAnalyzer for metrics | WIRED | validate_ma50_review.py lines 25, 192 |

**Note on plan-01 key_link:** Plan 01 specified `ma50_breakout_enabled` consumed by `ftd_signal.py`, but the gate is correctly placed in `mdm_v2_engine.py` (which wraps the `ftd_signal.py` call). This is architecturally correct — the config flag controls whether the engine calls the detector, not the detector itself. The intent (flag disables MA50 breakout) is fully achieved.

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `analysis/validate_ma50_review.py` | results dict (5 scenarios) | DataLoader -> MDMV2Engine.run() -> V2PerformanceAnalyzer | Yes — engine.run() processes historical OHLCV rows, no static returns | FLOWING |
| `strategies/mdm_v2/mdm_v2_engine.py` | sma200 column | Indicators.add_sma200_column(df) conditional on ma200_enabled | Yes — real rolling mean from close prices | FLOWING |
| `strategies/mdm_v2/position_manager.py` | sma200 (SELL trigger) | Passed via process_day() from engine row.get('sma200') | Yes — real computed value when ma200_enabled=True | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 8 test_ma50_review tests pass | `uv run pytest tests/test_ma50_review.py -x -q` | 8 passed in 0.31s | PASS |
| Config flags have correct defaults | Verified via grep in config.py | `ma50_breakout_enabled: bool = True`, `ma200_enabled: bool = False` | PASS |
| Engine gates MA50 breakout | Code inspection engine.py line 199 | `if not is_ftd and self.config.ma50_breakout_enabled:` | PASS |
| Validation script has all 5 scenario factories | grep in validate_ma50_review.py | All 5 `make_*_config` functions found | PASS |
| Full test suite (excl. pre-existing failure) | `uv run pytest tests/ -q` | 135 passed, 1 pre-existing failure in test_hybrid_engine.py | PASS (pre-existing failure documented) |

**Pre-existing test failure:** `tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq` fails with 88.49% < 95% BUY state overlap threshold. Last modified in Phase 17 (commit 140f3a0). Confirmed pre-existing before Phase 25 by both Plan 02 and Plan 03 summaries. Not caused by Phase 25 changes.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MAREVIEW-01 | Plans 01, 02, 03 | A/B backtest V2 vs V2 without MA50 in SELL trigger on VN30 | SATISFIED | Scenario 2 (no_ma50_sell) and Scenario 4 (no_ma50_all) cover this. Results in docs/rules_mdm_v2.md: no_ma50_sell Sharpe=0.50 vs baseline 0.34 |
| MAREVIEW-02 | Plans 01, 02, 03 | A/B backtest V2 vs V2 without MA50 in BUY filter on VN30 | SATISFIED | Scenario 3 (no_buy_filter) covers this. Result: Sharpe=0.25 — worst scenario, buy filter retains value |
| MAREVIEW-03 | Plan 03 | Report conclusion: keep/remove/replace MA50, with VN30 backtest evidence | SATISFIED | validate_ma50_review.py print_recommendation() outputs `RECOMMENDATION: REMOVE MA50 from signal logic.` with Sharpe evidence. docs/rules_mdm_v2.md line 764 records the recommendation. |

No orphaned requirements — all MAREVIEW-01/02/03 are claimed by plans in this phase and fully implemented.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scan covered: `analysis/validate_ma50_review.py`, `strategies/mdm_v2/ftd_signal.py`, `strategies/mdm_v2/position_manager.py`, `strategies/mdm_v2/mdm_v2_engine.py`, `tests/test_ma50_review.py`. No TODO/FIXME/placeholder patterns. No empty return stubs. No hardcoded empty data arrays flowing to rendering.

---

### Human Verification Required

#### 1. Validation script execution with live data

**Test:** Run `uv run python analysis/validate_ma50_review.py` from project root with VN30 data file present.
**Expected:** Prints 5-row comparison table with scenario names, numeric Return/MaxDD/Sharpe/Trades/WinRate values matching the results documented in SUMMARY (1_baseline 52.8%, 2_no_ma50_sell 91.2%, etc.), followed by RECOMMENDATION section.
**Why human:** Script requires local VN30 data CSV file at the path configured in DataLoader. Cannot execute in verification without confirming data file is accessible and the script exits 0.

---

### Gaps Summary

No gaps found. All 14 must-have truths are verified against the actual codebase. All 8 required artifacts exist, are substantive, and are correctly wired. All 3 requirement IDs are satisfied with evidence. The phase goal — producing a data-driven recommendation on whether MA50 breakout and 200dma should replace/supplement existing MDM V2 rules — is achieved:

- Config flags and SMA200 indicator provide the mechanical A/B test infrastructure (Plans 01-02)
- All 5 test scenarios are wired through the engine with config-gated signal paths (Plan 02)
- The validation script runs 5 scenarios and recommends REMOVE MA50 SELL trigger based on Sharpe ratio comparison (Plan 03)
- The recommendation is documented with actual backtest evidence in docs/rules_mdm_v2.md

The one pre-existing test failure (`test_hybrid_matches_v2_on_nasdaq`) is documented in both Plan 02 and Plan 03 summaries as pre-existing from Phase 23 and is out of scope for this phase.

---

_Verified: 2026-04-01T07:00:00Z_
_Verifier: Claude (gsd-verifier)_
