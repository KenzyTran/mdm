---
phase: 30-stock-level-entry-confirmation
verified: 2026-04-09T00:00:00Z
status: passed
score: 5/5 must-haves verified
---

# Phase 30: Stock-Level Entry Confirmation Verification Report

**Phase Goal:** A candidate stock is bought only after a stock-level confirmation signal fires within 20 trading days of an MDM BUY event
**Verified:** 2026-04-09
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP success criteria)

| #   | Truth | Status     | Evidence |
| --- | ----- | ---------- | -------- |
| 1   | Option A detector implements 4-clause D-03 formula | VERIFIED | `strategies/entry/option_a.py:48-49` uses `c.shift(1).rolling(cfg.high_lookback).max()` with all four clauses ANDed; off-by-one guard test green |
| 2   | Option C (Pocket Pivot) detector with fail-closed | VERIFIED | `strategies/entry/option_c.py:57-59` uses `v.where(is_down_day).shift(1).rolling(...).max()` — NaN propagation, no `fillna(0)` |
| 3   | 20-day window from CASH/SELL→BUY transition | VERIFIED | `strategies/entry/window.py:54` `(state == "BUY") & prev.isin(["CASH","SELL"])`; series-starts-in-BUY locked to no initial window |
| 4   | Fill = next-day adj_open (ATO), not signal-bar close | VERIFIED | `engine.py` next-bar lookup with last-bar unfilled handling; no-lookahead test green |
| 5   | A/B helper produces side-by-side counts on VN100 2014-2025 | VERIFIED | `docs/audits/phase30-entry-ab.md` exists with real run: Raw A=468, C=1733; CANSLIM A=4, C=3 |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `strategies/entry/config.py` | VERIFIED | 73 lines, EntryConfig with __post_init__ validation |
| `strategies/entry/option_a.py` | VERIFIED | 57 lines, shift(1).rolling pattern present |
| `strategies/entry/option_c.py` | VERIFIED | 71 lines, fail-closed via `.where(is_down_day)` + shift(1).rolling |
| `strategies/entry/window.py` | VERIFIED | 108 lines, transition detection via `isin(["CASH","SELL"])` |
| `strategies/entry/engine.py` | VERIFIED | 228 lines, EntryEngine class wires detectors + windows + canslim gate |
| `strategies/entry/ab_report.py` | VERIFIED | 457 lines, runs engine twice (raw + canslim) |
| `docs/rules_entry.md` | VERIFIED | exists, contains Option A and Option C |
| `docs/audits/phase30-entry-ab.md` | VERIFIED | real VN100 run, source commit 9a878bb, 2014-2025 |
| `docs/audits/phase30/entry_ab_raw_vn100.csv` | VERIFIED | 113KB |
| `docs/audits/phase30/entry_ab_canslim.csv` | VERIFIED | 446 bytes |
| `tests/entry/` (7 files) | VERIFIED | 33 tests pass |

### Key Link Verification

| From | To | Status |
| ---- | -- | ------ |
| option_a.py → close.shift(1).rolling(252).max() | adj_close shift+rolling | WIRED |
| option_c.py → fail-closed NaN propagation | `.where().shift(1).rolling().max()` | WIRED (no fillna(0)) |
| window.py → transition detector | `isin(["CASH","SELL"])` | WIRED |
| engine.py → detect_option_a / option_c | imported and called per ticker | WIRED |
| engine.py → compute_buy_windows | called once in __init__ (no-lookahead) | WIRED |
| engine.py → canslim gate (c_pass..liq_pass) | CANSLIM_GATE_COLS in engine.py:98 | WIRED |
| ab_report.py → EntryEngine twice | raw (None) + canslim_scores | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data Source | Status |
| -------- | ----------- | ------ |
| ab_report.py output md | Real VN100 prices via UniverseLoader, HybridEngine state, CanslimScorer | FLOWING (468/1733 raw fills, 4/3 canslim fills documented) |
| entry_ab_raw_vn100.csv | EntryEngine.run() over 100 tickers | FLOWING (113KB of fill records) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase 30 test suite | `uv run pytest tests/entry/ -q` | 33 passed | PASS |
| Imports work | `from strategies.entry import EntryEngine, ...` | available via __init__.py (47 lines) | PASS |
| Live A/B artifacts exist | ls docs/audits/phase30* | md + 2 CSVs present | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| ENTRY-01 | 30-01, 30-02 | Option A 52-week high + vol surge + up bar + upper-half | SATISFIED | option_a.py + test_option_a.py green |
| ENTRY-02 | 30-01, 30-02 | Option C Pocket Pivot fail-closed | SATISFIED | option_c.py + test_option_c.py green |
| ENTRY-03 | 30-01, 30-02 | 20-day MDM BUY window | SATISFIED | window.py + test_window.py green (incl. series-starts-in-BUY case) |
| ENTRY-04 | 30-01, 30-03 | Next-day open fill | SATISFIED | engine.py + test_engine.py green (no-lookahead, last-bar unfilled, A/C streams independent, dedup) |
| ENTRY-05 | 30-01, 30-03 | A/B comparison VN100 | SATISFIED | phase30-entry-ab.md + 2 CSVs with real 2014-2025 numbers |

All five requirement IDs from REQUIREMENTS.md (lines 81-85) are accounted for and marked `[x]`. No orphaned requirements.

### Anti-Patterns Found

None. Specifically verified absences:
- `fillna(0)` NOT present in option_c.py (would be free-pass bug per pitfall #2)
- `shift(1).rolling` IS present in option_a.py (off-by-one guard per pitfall #1)
- engine.py calls `compute_buy_windows` once in `__init__` (no-lookahead via state[i-1] discipline)

### Human Verification Required

None. All success criteria are programmatically verifiable and verified.

### Gaps Summary

No gaps. Phase 30 goal fully achieved: detectors, window, engine, A/B report all implemented with real VN100 2014-2025 fills documented. All 33 tests green. Code-Docs Sync rule satisfied (docs/rules_entry.md present alongside code).

---

_Verified: 2026-04-09_
_Verifier: Claude (gsd-verifier)_
