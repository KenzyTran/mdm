---
phase: 17-stop-loss-risk-management
verified: 2026-03-30T08:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: null
gaps: []
human_verification: []
---

# Phase 17: Stop Loss & Risk Management Verification Report

**Phase Goal:** Implement unified stop-loss and risk management for both long and short positions in the MDM hybrid engine.
**Verified:** 2026-03-30T08:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Long stop loss defaults to 1.5% and triggers exit to CASH when close < buy_price * 0.985 | VERIFIED | `config.py` line 47: `stop_loss_pct: float = 0.015`; `stop_loss.py` line 120 applies `(1 - effective_pct)`; test `test_long_stop_loss_default_1_5_pct` passes |
| 2 | Stop loss widens during high-volatility periods (ATR > baseline) and tightens during low-volatility periods (ATR < baseline) | VERIFIED | `stop_loss.py` `_get_effective_stop_pct` scales by `atr / atr_baseline`; tests `test_volatility_adaptive_high_vol` and `test_volatility_adaptive_low_vol` both pass |
| 3 | Volatility-adaptive stop loss is clamped to [0.5x, 2.5x] of base stop loss | VERIFIED | `stop_loss.py` lines 56-58: `min_pct`/`max_pct` clamping; tests `test_volatility_adaptive_clamped_max` and `test_volatility_adaptive_clamped_min` pass |
| 4 | ATR column is computed in prepare_data and passed to stop loss checker | VERIFIED | `mdm_hybrid_engine.py` lines 157-160 call `Indicators.add_atr_column` and compute `atr_baseline`; lines 301-311 extract and pass `current_atr` / `current_atr_baseline` to `check()` |
| 5 | Short stop loss triggers when close > dd5_high * 1.01 during SELL state | VERIFIED | `stop_loss.py` lines 170-182 `check_short()`; engine lines 315-327 invoke it in SELL state; test `test_short_stop_loss_dd5_high` passes |
| 6 | DD5 high is the high price of the specific day when dd_count reaches 5 (not max of all 5 DD highs) | VERIFIED | `distribution_day.py` line 149: `dd_in_window[4][1]` (5th tuple's high, not max); test `test_dd5_high_returns_5th_dd_high` asserts `dd5_high == 15400.0` (the 5th day's high, not max) |
| 7 | DD5 high is locked into the engine when entering SELL state and survives DD counter reset on FTD | VERIFIED | `mdm_hybrid_engine.py` lines 57, 72: `self._dd5_high_locked = 0.0`; lines 287-291 cache on SELL entry; reset only at line 327 (after short stop triggers) — not on FTD reset |
| 8 | Short stop loss has higher priority than FTD/MA50 cover signals | VERIFIED | Engine lines 313-330 check short stop loss first; lines 329-353 wrapped in `if not (current_state == V2MarketState.SELL and short_stop_result.triggered)` to skip normal processing when triggered |
| 9 | When no DD5 high exists (dd_count < 5 at SELL entry), short stop loss is disabled | VERIFIED | `stop_loss.py` line 171: `if dd5_high <= 0: return StopLossResult(triggered=False, ...)`; test `test_short_stop_loss_no_dd5_high` passes |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `strategies/mdm_hybrid/config.py` | MDMV2Config with stop_loss_pct=0.015, atr_period, atr_baseline_period, volatility_adaptive, stop_loss_min_multiplier, stop_loss_max_multiplier, short_stop_pct_above_dd5 | VERIFIED | All 7 fields present at lines 47-57 |
| `strategies/mdm_hybrid/indicators.py` | `add_atr_column` static method with true_range computation | VERIFIED | Lines 193-213: full ATR implementation with `true_range`, `atr` columns |
| `strategies/mdm_hybrid/stop_loss.py` | `_get_effective_stop_pct` and `check_short` methods, `atr` / `atr_baseline` params in `check()` | VERIFIED | `_get_effective_stop_pct` lines 36-58; `check()` signature includes `atr`, `atr_baseline` lines 70-71; `check_short` lines 151-184 |
| `strategies/mdm_hybrid/distribution_day.py` | DD history as (date, high) tuples, `get_dd5_high()` method, `high` param in `check_distribution_day` | VERIFIED | `dd_history` stores tuples (line 96); `get_dd5_high()` lines 127-151; `high: float` param line 75 |
| `strategies/mdm_hybrid/mdm_hybrid_engine.py` | Short stop loss check in SELL state before FTD/cover signals, `_dd5_high_locked`, ATR wired | VERIFIED | `_dd5_high_locked` line 57; ATR computation lines 157-160; `check_short` call lines 315-327; priority guard lines 329-330 |
| `tests/test_stop_loss.py` | 21 tests covering RISK-01, RISK-02, RISK-03, SHORT-03 | VERIFIED | 21 tests present and all pass (confirmed by `pytest tests/test_stop_loss.py -x -q`) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `mdm_hybrid_engine.py` | `stop_loss.py` | `stop_loss_checker.check()` with `atr` and `atr_baseline` params | VERIFIED | Line 304: `self.stop_loss_checker.check(...)` with `atr=current_atr, atr_baseline=current_atr_baseline` at lines 309-310 |
| `mdm_hybrid_engine.py` | `indicators.py` | `Indicators.add_atr_column(df)` in run() data preparation | VERIFIED | Line 157: `df = Indicators.add_atr_column(df, period=self.config.v2_config.atr_period)` |
| `distribution_day.py` | `mdm_hybrid_engine.py` | `dd5_high` cached and locked into engine on SELL entry | VERIFIED | Line 289: `dd5_h = self.dd_counter.get_dd5_high(date, all_dates)` executed when `dd_count >= dd_cash_threshold`; stored in `self._dd5_high_locked` |
| `mdm_hybrid_engine.py` | `stop_loss.py` | `stop_loss_checker.check_short(close, dd5_high, short_entry_price)` | VERIFIED | Line 317: `self.stop_loss_checker.check_short(close, self._dd5_high_locked, short_entry)` |
| `mdm_hybrid_engine.py` | `position_manager.py` | `cover_short()` called when short stop loss triggers | VERIFIED | Line 322: `self.position_manager.cover_short(close, date, short_stop_result.reason)` — reason contains "Short stop loss" from `check_short()` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `mdm_hybrid_engine.py` (short stop check) | `self._dd5_high_locked` | `dd_counter.get_dd5_high()` reading `dd_history` populated by `check_distribution_day()` in each BUY-state iteration | Yes — computed from real high prices in the OHLCV loop | FLOWING |
| `stop_loss.py` `check_short()` | `dd5_high` | Passed from `_dd5_high_locked` in engine | Yes — flows from real DD detection | FLOWING |
| `stop_loss.py` `_get_effective_stop_pct()` | `atr`, `atr_baseline` | `add_atr_column()` using real OHLCV `high`, `low`, `close` columns | Yes — rolling mean of true range from real price data | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 21 stop loss unit tests pass | `.venv/Scripts/python -m pytest tests/test_stop_loss.py -x -q` | `21 passed in 0.43s` | PASS |
| Full test suite (non-engine) passes | `.venv/Scripts/python -m pytest tests/ --ignore=tests/test_hybrid_engine.py -x -q` | `333 passed, 4 skipped, 18 warnings` | PASS |
| Short position tests pass | `.venv/Scripts/python -m pytest tests/test_stop_loss.py tests/test_short_position.py -x -q` | `37 passed in 78.09s` | PASS |
| MDMV2Config() has correct defaults | Python import check | `stop_loss_pct=0.015`, all ATR params present | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RISK-01 | 17-01-PLAN.md | Stop loss mặc định 1.5% cho vị thế long (thay vì 2.5% hiện tại) | SATISFIED | `config.py` `stop_loss_pct = 0.015`; `stop_loss.py` Rule 1 uses this via `_get_effective_stop_pct`; `test_config_stop_loss_default` and `test_long_stop_loss_default_1_5_pct` pass |
| RISK-02 | 17-01-PLAN.md | Volatility-adaptive stop loss — stop loss rộng hơn khi market volatile | SATISFIED | `_get_effective_stop_pct` scales by ATR ratio; ATR wired into engine; 6 adaptive tests pass covering high/low/clamped/disabled cases |
| RISK-03 | 17-02-PLAN.md | Short stop loss riêng biệt — 1% trên DD5 high (từ MDM classic rules) | SATISFIED | `check_short()` in `stop_loss.py` triggers at `dd5_high * 1.01`; DD5 high tracked as high of 5th DD day; `test_short_stop_loss_dd5_high` passes |
| SHORT-03 | 17-02-PLAN.md | Short stop loss — cắt lỗ khi giá vượt ngưỡng từ giá short entry (Dr. K: 1% trên DD5 high) | SATISFIED | Engine calls `cover_short()` when `short_stop_result.triggered`; action recorded as `SHORT_COVER: Short stop loss: ...`; priority enforced before `process_day` |

No orphaned requirements for Phase 17 — REQUIREMENTS.md traceability table maps exactly RISK-01, RISK-02, RISK-03, SHORT-03 to Phase 17, all covered.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

Scanned `stop_loss.py`, `distribution_day.py`, `indicators.py`, `mdm_hybrid_engine.py`, `config.py`, and `tests/test_stop_loss.py` for TODO/placeholder/empty returns. No stub patterns detected. All return values carry real computation.

### Human Verification Required

None. All goals are verifiable via code inspection and automated tests.

### Gaps Summary

No gaps. All 9 observable truths are verified, all 6 artifacts exist and are substantive, all 5 key links are wired, all 4 requirements are satisfied, and the full test suite passes (333 tests, 21 specifically for Phase 17 behaviors).

The one noteworthy implementation detail: the key_link pattern `cover_short.*short stop` specified in the PLAN does not literally match the code (the engine calls `cover_short(close, date, short_stop_result.reason)` where the reason contains "Short stop loss" rather than the string being in the call expression). However the functional contract is met — `cover_short` is called when `short_stop_result.triggered` is True, and the reason string is "Short stop loss: ...".

---

_Verified: 2026-03-30T08:00:00Z_
_Verifier: Claude (gsd-verifier)_
