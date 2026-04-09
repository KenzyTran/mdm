---
phase: 30-stock-level-entry-confirmation
plan: 01
subsystem: testing
tags: [pytest, dataclass, pandas, entry-signals, canslim, mdm]

requires:
  - phase: 28-vn100-data-layer
    provides: connectors/adjust.py adjust_ohlc, connectors/postgres.py load_stock_eod
  - phase: 29-canslim-scorer
    provides: strategies/canslim/scorer.py CanslimScorer.score(as_of_date) dense per-date output
provides:
  - strategies/entry/ package skeleton with EntryConfig dataclass (D-03..D-06, D-20)
  - tests/entry/ scaffold with conftest fixtures and RED stubs for ENTRY-01..ENTRY-05
  - Resolution of 3 Phase 30 open questions (NOTES.md)
  - Locked decision: series-starts-in-BUY = no initial window
affects: [30-02, 30-03, 32 (in-sample sweep)]

tech-stack:
  added: []
  patterns:
    - "EntryConfig dataclass with fail-loud __post_init__ validation (mirrors CanslimConfig)"
    - "Test scaffold uses pytest.importorskip for RED-stub pattern across Wave 0"
    - "Synthetic deterministic OHLCV fixture builder (260-bar business-day frames)"

key-files:
  created:
    - strategies/entry/__init__.py
    - strategies/entry/config.py
    - tests/entry/__init__.py
    - tests/entry/conftest.py
    - tests/entry/test_config.py
    - tests/entry/test_option_a.py
    - tests/entry/test_option_c.py
    - tests/entry/test_window.py
    - tests/entry/test_engine.py
    - tests/entry/test_ab_report.py
    - .planning/phases/30-stock-level-entry-confirmation/30-01-NOTES.md
  modified: []

key-decisions:
  - "CanslimScorer is per-date dense (one row per ticker per as_of_date) - no forward-fill needed in 30-03"
  - "VN100 batch price loader already exists: connectors/postgres.py::load_stock_eod(tickers, start, end)"
  - "Series-starts-in-BUY = no initial window (fail-closed) - locked for 30-02 window.py"
  - "tests/entry/ layout matches flat tests/canslim/ convention (not nested under strategies/)"
  - "RED-stub pattern via pytest.importorskip so Wave 0 commit has zero collection errors"

patterns-established:
  - "Wave 0 scaffold pattern: create config + tests now, detectors/engine later, stubs skip via importorskip"
  - "Deterministic OHLCV fixture with make_buy_breakout_bar mutator for forcing detector clauses"
  - "MDM state fixture via (date, new_state) transition list with forward-fill"

requirements-completed: []

duration: 8min
completed: 2026-04-09
---

# Phase 30 Plan 01: Wave 0 Scaffold Summary

**strategies/entry/ package skeleton with validated EntryConfig and full tests/entry/ RED-stub scaffold for ENTRY-01..ENTRY-05**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-09T05:26Z
- **Completed:** 2026-04-09T05:34Z
- **Tasks:** 3
- **Files created:** 11
- **Files modified:** 0

## Accomplishments

- Created `strategies/entry/` package with `EntryConfig` dataclass (7 fields, fail-loud validation on 7 branches)
- Built `tests/entry/` scaffold: conftest fixtures (OHLCV, breakout-bar mutator, MDM state) + 6 test files
- Resolved all 3 open questions from 30-RESEARCH.md via code audit (30-01-NOTES.md)
- Locked the series-starts-in-BUY edge case to "no initial window" so 30-02 window.py implementer has no ambiguity
- Established RED-stub pattern via `pytest.importorskip` — 9 config tests PASS, 5 downstream test modules SKIP cleanly, zero collection errors

## Task Commits

1. **Task 1: Resolve open questions via code audit** — `5577133` (docs)
2. **Task 2: Create strategies/entry package + EntryConfig** — `41c4005` (feat, includes test_config.py)
3. **Task 3: Test scaffold with RED stubs** — `ba14033` (test)

## EntryConfig Signature

```python
@dataclass
class EntryConfig:
    # Option A (D-03/D-04)
    high_lookback: int = 252
    vol_lookback: int = 50
    vol_mult: float = 1.5
    # Option C (D-05/D-06)
    ma_length: int = 50
    pocket_lookback: int = 10
    base_tolerance: float = 0.15
    # Window (D-07..D-09, D-20)
    window_days: int = 20
```

Validation rules (raise `ValueError`):
- `high_lookback >= 2`
- `vol_lookback >= 1`
- `vol_mult >= 1.0`
- `ma_length >= 2`
- `pocket_lookback >= 1`
- `0 < base_tolerance < 1` (exclusive)
- `window_days >= 1`

## Fixture Helpers (tests/entry/conftest.py)

Available to 30-02 and 30-03 test authors:

| Fixture | Signature | Purpose |
|---------|-----------|---------|
| `make_ohlcv` | `(n_bars=260, start_date="2020-01-01", seed=42) -> DataFrame` | Deterministic business-day OHLCV frame with `adj_open/adj_high/adj_low/adj_close/totalvol` |
| `make_buy_breakout_bar` | `(df, idx) -> DataFrame` | Mutates bar at positional `idx` to satisfy all four Option A clauses |
| `make_mdm_state` | `(dates, transitions, initial="CASH") -> Series[str]` | Materializes MDM state series from `(date, new_state)` tuples |

All use fixed seeds and pure numpy — no external data dependencies.

## Resolved Open Questions (inline from 30-01-NOTES.md)

### 1. CanslimScorer output cadence

**Dense per-date.** `CanslimScorer.score(as_of_date: date)` returns one row per (as_of_date, ticker) for every eligible ticker on that single day. All per-letter booleans (`c_pass`, `c_plus_pass`, `a_pass`, `a_plus_pass`, `n_pass`, `s_pass`, `l_pass`, `i_pass`, `liq_pass`) plus `rs_rating` and `score` are computed fresh from daily technicals + quarterly fundamentals. **No forward-fill needed** in 30-03. For performance, 30-03 may cache per-date frames keyed by signal-bar date.

### 2. VN100 batch price loader

**Exists — use `connectors/postgres.py::load_stock_eod(tickers, start, end)`.** Returns raw OHLCV+adjustrate panel from `stock_eod`. 30-03 should call this, group by `stockcode`, pass each per-ticker frame through `connectors/adjust.py::adjust_ohlc()`, then feed into `EntryEngine`. No new wrapper under `strategies/entry/` needed.

### 3. Series-starts-in-BUY edge case — LOCKED

**No initial window.** If the VN30 MDM state series begins on a bar where state is already BUY with no prior CASH/SELL, that is NOT treated as a transition. The first window only opens on an actually-observed CASH/SELL → BUY transition. Implementation: `prev = state.shift(1); (state == "BUY") & prev.isin(["CASH", "SELL"])` — the `shift(1)` NaN at index 0 naturally evaluates to False in `isin`. A dedicated unit test `test_window_series_starts_in_buy_no_initial_window` pins this behavior.

## Test Files and RED-Stub Pattern

All files at `tests/entry/`:

| File | Status | Pattern |
|------|--------|---------|
| `conftest.py` | green fixtures | Shared `make_ohlcv`, `make_buy_breakout_bar`, `make_mdm_state` |
| `test_config.py` | **9 tests PASS** | EntryConfig default + 8 validation cases |
| `test_option_a.py` | SKIP | `pytest.importorskip("strategies.entry.option_a", reason="30-02 Task 1 not yet implemented")` |
| `test_option_c.py` | SKIP | `pytest.importorskip("strategies.entry.option_c", ...)` |
| `test_window.py` | SKIP | `pytest.importorskip("strategies.entry.window", ...)` |
| `test_engine.py` | SKIP | `pytest.importorskip("strategies.entry.engine", ...)` |
| `test_ab_report.py` | SKIP | `pytest.importorskip("strategies.entry.ab_report", ...)` |

`uv run pytest tests/entry/ -q` result: **9 passed, 5 skipped, 0 errors in 0.05s**.

When 30-02 creates `strategies/entry/option_a.py`, the `importorskip` converts to a live import and all 6 Option A tests become real RED/GREEN gates. Same pattern for option_c, window, engine, ab_report.

## Decisions Made

- Used `pytest.importorskip` module-level RED-stub (not xfail or marker-based skip) — cleanest conversion path, no test code churn when downstream modules land.
- `test_window_no_extension_on_continuous_buy` leverages the "series starts in BUY -> no window" locked decision for its assertion, avoiding a contradiction between the two tests.
- Did NOT create `docs/rules_entry.md` in this plan — it is Code-Docs Sync relevant only when detector formulas land in 30-02. Plan 30-02 will create it alongside `option_a.py`/`option_c.py`.

## Deviations from Plan

None — plan executed exactly as written. All verification commands passed on first run.

## Issues Encountered

None.

## Next Phase Readiness

- **30-02** can start immediately: every test file it needs to light up already exists, `EntryConfig` is importable with locked defaults, and fixture helpers (`make_ohlcv`, `make_buy_breakout_bar`, `make_mdm_state`) cover every test scenario the research called out.
- **30-03** can consume `connectors.postgres.load_stock_eod` directly per NOTES §2 and iterate `CanslimScorer.score(d)` per signal-bar date per NOTES §1.
- No blockers.

## Self-Check: PASSED

- FOUND: strategies/entry/__init__.py
- FOUND: strategies/entry/config.py
- FOUND: tests/entry/conftest.py
- FOUND: tests/entry/test_config.py
- FOUND: tests/entry/test_option_a.py
- FOUND: tests/entry/test_option_c.py
- FOUND: tests/entry/test_window.py
- FOUND: tests/entry/test_engine.py
- FOUND: tests/entry/test_ab_report.py
- FOUND: .planning/phases/30-stock-level-entry-confirmation/30-01-NOTES.md
- FOUND commit: 5577133 (Task 1 — NOTES.md)
- FOUND commit: 41c4005 (Task 2 — EntryConfig + test_config)
- FOUND commit: ba14033 (Task 3 — RED-stub test scaffold)

---
*Phase: 30-stock-level-entry-confirmation*
*Completed: 2026-04-09*
