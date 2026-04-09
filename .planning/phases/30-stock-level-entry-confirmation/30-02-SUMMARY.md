---
phase: 30-stock-level-entry-confirmation
plan: 02
subsystem: entry-detectors
tags: [pandas, entry-signals, canslim, option-a, pocket-pivot, window]

requires:
  - phase: 30-stock-level-entry-confirmation
    provides: strategies/entry/config.py EntryConfig + tests/entry/ scaffold
provides:
  - strategies/entry/option_a.py detect_option_a (ENTRY-01)
  - strategies/entry/option_c.py detect_option_c (ENTRY-02)
  - strategies/entry/window.py compute_buy_windows + is_in_any_window / find_window (ENTRY-03)
affects: [30-03]

tech-stack:
  added: []
  patterns:
    - "Vectorized shift(1).rolling() idiom for off-by-one-safe trailing references"
    - "NaN propagation as fail-closed primitive (down-day-vol max)"
    - "Transition detection via state.shift(1).isin([...]) — NaN naturally False"

key-files:
  created:
    - strategies/entry/option_a.py
    - strategies/entry/option_c.py
    - strategies/entry/window.py
  modified:
    - strategies/entry/__init__.py
    - tests/entry/test_option_a.py
    - tests/entry/test_option_c.py
    - tests/entry/test_window.py

key-decisions:
  - "is_in_any_window uses pd.bdate_range fallback to count 1-indexed days_since_buy when trading_days_index not passed (matches test fixtures that use pd.bdate_range)"
  - "find_window kept as alias for is_in_any_window per plan interface section"
  - "Materialized list windows (not generator) — tens of windows per backtest, simpler iteration"

requirements-completed: [ENTRY-01, ENTRY-02, ENTRY-03]

duration: 6min
completed: 2026-04-09
---

# Phase 30 Plan 02: Entry Detector & Window Tracker Summary

**Three pure-function building blocks — Option A breakout, Option C pocket pivot, MDM BUY window — all GREEN against 18 RED tests from 30-01.**

## Performance

- **Duration:** ~6 min
- **Tasks:** 3
- **Files created:** 3
- **Files modified:** 4
- **Tests:** 18 new GREEN (6 Option A + 5 Option C + 7 window); `tests/entry/` totals 27 passed, 2 skipped (engine + ab_report pending 30-03)

## Task Commits

1. **Task 1 — Option A detector (ENTRY-01)** — `1369805`
2. **Task 2 — Option C detector (ENTRY-02)** — `33f30f5`
3. **Task 3 — Window tracker (ENTRY-03)** — `3029e38`

## Function Signatures

```python
# strategies/entry/option_a.py
def detect_option_a(df: pd.DataFrame, cfg: EntryConfig) -> pd.Series[bool]:
    """Fires on bar t iff:
       1. adj_close[t] > max(adj_close[t-252..t-1])   (strict new 52wk high, shift(1))
       2. totalvol[t]  >= 1.5 * mean(vol[t-50..t-1])  (shift(1))
       3. adj_close[t] > adj_open[t]                  (up bar)
       4. adj_close[t] >= (adj_high[t]+adj_low[t])/2  (upper-half close)
    NaN warmup -> False."""

# strategies/entry/option_c.py
def detect_option_c(df: pd.DataFrame, cfg: EntryConfig) -> pd.Series[bool]:
    """Fires on bar t iff:
       1. adj_close[t] > adj_open[t]
       2. adj_close[t] >= MA50(adj_close)[t]
       3. totalvol[t]  >  max(down_day_vols[t-10..t-1])  (NaN = fail-closed)
       4. adj_close[t] >= 0.85 * max(adj_high[t-50..t-1])
    """

# strategies/entry/window.py
def compute_buy_windows(state: pd.Series, window_days: int = 20) -> list[tuple[Timestamp, Timestamp]]:
    """One (start, end_inclusive) per CASH/SELL->BUY transition.
    Day-1 inclusive; no extension on continuous BUY;
    series-starts-in-BUY -> NO initial window (30-01-NOTES §3)."""

def is_in_any_window(signal_date, windows, trading_days_index=None) -> tuple[bool, int | None]:
    """1-indexed days_since_buy (1=transition bar, window_days=terminal)."""

find_window = is_in_any_window  # alias per plan interfaces
```

## Input DataFrame Contract (detectors)

Both `detect_option_a` and `detect_option_c` expect a **single-ticker** adjusted OHLCV frame, sorted ascending by date, with columns:

| Column       | Dtype   | Notes                                      |
| ------------ | ------- | ------------------------------------------ |
| `adj_open`   | float64 | Adjusted open                              |
| `adj_high`   | float64 | Adjusted high                              |
| `adj_low`    | float64 | Adjusted low                               |
| `adj_close`  | float64 | Adjusted close                             |
| `totalvol`   | float64 | Raw total volume (unadjusted OK for ratio) |

Returns `pd.Series[bool]` aligned to `df.index`. Warmup bars where rolling references are undefined come back as `False` (not `NaN`) via `.fillna(False).astype(bool)`.

## Pitfall Guards (explicit)

| Pitfall                          | Guard                                                                           | Location                           |
| -------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------- |
| **#1** Off-by-one on 52wk max    | `c.shift(1).rolling(252).max()` — exclude today's close from reference          | `option_a.py:hi_ref`               |
| **#1** Off-by-one on vol avg     | `v.shift(1).rolling(50).mean()` — exclude today's volume                        | `option_a.py:avg_vol`              |
| **#2** Free-pass on zero down days | `down_vols = v.where(is_down_day)` → NaN propagates through `v > NaN` = False | `option_c.py:max_down_vol` (NO `fillna(0)`) |
| **#3** Day-1 off-by-one          | Window is `[t, t+window_days-1]`, start = transition bar, 1-indexed counting    | `window.py:compute_buy_windows`    |
| **Locked** series-starts-in-BUY  | `state.shift(1).isin([...])` — NaN at idx 0 evaluates False naturally           | `window.py:is_transition`          |

`grep -n "fillna(0)" strategies/entry/option_c.py` returns nothing — free-pass bug absent by construction.

## Integration Note for 30-03

The `EntryEngine` in 30-03 should thread these pieces together as follows:

```python
# Precompute once per backtest
windows = compute_buy_windows(mdm_state_series, cfg.window_days)

# Per-ticker, precompute signal series
for ticker, df in adjusted_panel.groupby("ticker"):
    a_fires = detect_option_a(df, cfg)
    c_fires = detect_option_c(df, cfg)
    for signal_date in df.index[a_fires | c_fires]:
        in_window, days_since = is_in_any_window(
            signal_date, windows, trading_days_index=mdm_state_series.index
        )
        if not in_window:
            continue
        # CANSLIM gate (D-16) + dedup key
        win_id = next(i for i, (s, e) in enumerate(windows) if s <= signal_date <= e)
        detector_name = "option_a" if a_fires.loc[signal_date] else "option_c"
        dedup_key = (ticker, win_id, detector_name)
        # emit candidate
```

- **Pass `trading_days_index=mdm_state_series.index`** to `is_in_any_window` so `days_since_buy` uses the engine's actual trading calendar (HOSE holidays etc.), not the `bdate_range` fallback.
- **Dedup key** `(ticker, window_id, detector_name)` prevents re-firing within the same window per D-08/D-09.
- Per 30-01-NOTES §1, iterate `CanslimScorer.score(d)` on each unique signal-bar date and cache.

## Verification

- `uv run pytest tests/entry/test_option_a.py tests/entry/test_option_c.py tests/entry/test_window.py -q` → **18 passed**
- `uv run pytest tests/entry/ -q` → **27 passed, 2 skipped** (engine + ab_report deferred to 30-03)
- `python -c "from strategies.entry import EntryConfig, detect_option_a, detect_option_c, compute_buy_windows, find_window, is_in_any_window"` → succeeds
- `grep -n "shift(1).rolling" strategies/entry/option_a.py` → 2 hits (hi_ref, avg_vol)
- `grep -n "fillna(0)" strategies/entry/option_c.py` → 0 hits (free-pass bug absent)

## Deviations from Plan

**1. [Rule 3 — Blocking] `is_in_any_window` days_since_buy fallback counting**

- **Found during:** Task 3 verification run
- **Issue:** First draft computed `days_since_buy` via `(signal_ts - start).days + 1`. Test `test_window_day_20_inclusive` expected `day == 20` for `dates[5+19]` but got `28` — calendar days vs trading days mismatch (weekends inflate the offset).
- **Fix:** Switched fallback to `len(pd.bdate_range(start, signal_ts))` which counts business days inclusive. Also kept the `trading_days_index` kwarg so 30-03 engine can pass its exact HOSE-aware calendar for correctness on real data.
- **Files modified:** `strategies/entry/window.py`
- **Commit:** `3029e38`

No other deviations. Plan executed as written.

## Known Stubs

None. All three modules are complete implementations; no hardcoded empty values or placeholder data. The 2 skipped tests (`test_engine.py`, `test_ab_report.py`) are scoped to plan 30-03 and use the 30-01 RED-stub `importorskip` pattern intentionally.

## Next Phase Readiness

- **30-03** can import `detect_option_a`, `detect_option_c`, `compute_buy_windows`, `is_in_any_window` directly from `strategies.entry`. Integration recipe provided above.
- No blockers.

## Self-Check: PASSED

- FOUND: strategies/entry/option_a.py
- FOUND: strategies/entry/option_c.py
- FOUND: strategies/entry/window.py
- FOUND commit: 1369805 (Task 1 Option A)
- FOUND commit: 33f30f5 (Task 2 Option C)
- FOUND commit: 3029e38 (Task 3 Window)

---
*Phase: 30-stock-level-entry-confirmation*
*Completed: 2026-04-09*
