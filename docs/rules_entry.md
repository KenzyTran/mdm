# Phase 30 — Stock-Level Entry Confirmation Rules (LOCKED)

Authoritative rules for the `strategies/entry/` package. Per the CLAUDE.md
**Code-Docs Sync Rule**, any change to `strategies/entry/*.py` that alters
detector formulas, window semantics, fill pricing, or dedup keys MUST land
in the same commit as an update to this file.

## 1. Purpose

Generate stock-level buy signals, gated by the MDM BUY window and filled at
the next-day open, for downstream consumption by the Phase 31 portfolio
engine. Two independent detector streams (**Option A** and **Option C**)
provide complementary breakout and pocket-pivot confirmation.

Covers requirements **ENTRY-01..ENTRY-05** from
`.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md`.

## 2. Option A — 52-Week High Breakout (ENTRY-01, D-03/D-04)

Implementation: `strategies/entry/option_a.py::detect_option_a`

Fires on bar `t` iff ALL four clauses hold:

1. `adj_close[t] > max(adj_close[t-252 .. t-1])` — strict new 52-week high
   (exclude today via `.shift(1).rolling(...)`)
2. `totalvol[t]  >= 1.5 * mean(totalvol[t-50 .. t-1])` — volume surge
3. `adj_close[t] > adj_open[t]` — up bar
4. `adj_close[t] >= (adj_high[t] + adj_low[t]) / 2` — upper-half close

Tunables (`EntryConfig`): `high_lookback=252`, `vol_lookback=50`,
`vol_mult=1.5`.

**Pitfall #1 (off-by-one):** Both the high reference and the volume baseline
MUST use `.shift(1)` BEFORE `.rolling(...)` — otherwise today's close/volume
contaminates the reference window and the strict `>` check can never fire.

## 3. Option C — Pocket Pivot (ENTRY-02, D-05/D-06)

Implementation: `strategies/entry/option_c.py::detect_option_c`

Fires on bar `t` iff ALL four clauses hold:

1. `adj_close[t] > adj_open[t]` — up bar
2. `adj_close[t] >= MA50(adj_close)[t]` — above 50-day simple moving average
3. `totalvol[t]  > max(down_day_vols[t-10 .. t-1])` — pocket-pivot volume,
   where a down day is `adj_close < prior adj_close`
4. `adj_close[t] >= 0.85 * max(adj_high[t-50 .. t-1])` — within 15% of the
   50-day high (near-base)

Tunables (`EntryConfig`): `ma_length=50`, `pocket_lookback=10`,
`base_tolerance=0.15`.

**Pitfall #2 (fail-closed on zero down days):** If the last `pocket_lookback`
sessions contain NO down days, `down_day_vols` is all-NaN, rolling-max is
NaN, and `totalvol > NaN` evaluates False — the detector correctly does
NOT fire. **Do not `.fillna(0)`** here; that converts a missing reference
into a free pass and lets any positive volume satisfy the clause.

## 4. Entry Timing Window (ENTRY-03, D-07..D-10)

Implementation: `strategies/entry/window.py::compute_buy_windows`,
`is_in_any_window` (alias: `find_window`).

- **Length:** 20 trading days from the most recent `CASH/SELL → BUY`
  transition of the MDM state series.
- **Day-1 inclusive:** The transition bar itself is day 1; the terminal bar
  is day 20. Window = `[t, t + 19]`.
- **No extension on continuous BUY:** The clock keeps running from the
  original transition bar. Continuous BUY beyond day 20 does NOT extend
  the window.
- **Reset on new transition:** Each new `CASH/SELL → BUY` opens a fresh
  window — overlapping or mid-window new transitions are kept independent.
- **Series-starts-in-BUY:** NO initial window. If the series begins already
  in BUY with no prior observable CASH/SELL bar, that is NOT a transition.
  Fail-closed per `30-01-NOTES.md §3` (LOCKED). Implemented naturally via
  `state.shift(1).isin([...])` — the NaN at index 0 evaluates False.
- **MDM state source:** `strategies/mdm_hybrid/HybridEngine` with the v6
  best config. Phase 30 CONSUMES the state series — it does NOT re-run the
  hybrid engine internally (D-10).

## 5. Fill Model (ENTRY-04, D-11..D-13)

Implementation: `strategies/entry/engine.py::EntryEngine.run`

- **Fill price:** `adj_open[t+1]` — next-day open (ATO).
- **Last-bar signals:** If the signal fires on the final bar in the frame,
  the record is written as `Unfilled(reason="unfilled: no next bar")` and
  stored on `FillList.unfilled`. No synthetic fill is fabricated.
- **Deferred to Phase 31:** T+2 settlement, 7% ceiling/floor lock handling,
  partial fills, slippage. Phase 30 assumes every next-day open is tradable.

## 6. Duplicate Handling (D-14/D-15)

- **A and C are independent streams:** Same ticker on same bar can produce
  one fill to each stream within the same window.
- **Within-stream dedup key:** `(ticker, window_id, detector_name)`. First
  fire wins; subsequent fires for the same key inside the same window are
  silently dropped.
- **Window boundary:** On a new `CASH/SELL → BUY` transition the window_id
  advances, so the same (ticker, detector) can legitimately fire once per
  window.

## 7. CANSLIM Gate (D-16)

When `EntryEngine(canslim_scores=...)` is supplied, a signal only passes the
gate if ALL seven per-letter booleans are True on the **signal bar** for
that ticker:

```
c_pass & a_pass & n_pass & s_pass & l_pass & i_pass & liq_pass
```

Missing (ticker, date) keys in the scoreboard fail-closed (signal dropped).
Per `30-01-NOTES.md §1`, `CanslimScorer.score(d)` returns a dense
per-ticker frame — no forward-fill needed.

## 8. Output Location (D-21)

Per-run artefacts produced by `strategies/entry/ab_report.py::run_ab_report`:

- **Markdown report:** `docs/audits/phase30-entry-ab.md`
- **Raw VN100 fills CSV:** `docs/audits/phase30/entry_ab_raw_vn100.csv`
- **CANSLIM-qualified fills CSV:** `docs/audits/phase30/entry_ab_canslim.csv`

D-19 metrics per detector stream (raw & canslim):
`total_fills, unique_tickers, windows_with_fills, mean_fills_per_window,
days_since_buy_histogram, ab_overlap_count`.

## 9. References

Code:
- `strategies/entry/config.py` — `EntryConfig` dataclass (Wave 0, plan 30-01)
- `strategies/entry/option_a.py` — `detect_option_a` (plan 30-02)
- `strategies/entry/option_c.py` — `detect_option_c` (plan 30-02)
- `strategies/entry/window.py` — `compute_buy_windows`, `is_in_any_window` (plan 30-02)
- `strategies/entry/engine.py` — `EntryEngine`, `Fill`, `Unfilled` (plan 30-03)
- `strategies/entry/ab_report.py` — A/B runner (plan 30-03)

Tests:
- `tests/entry/test_config.py` (Wave 0)
- `tests/entry/test_option_a.py`, `test_option_c.py`, `test_window.py` (plan 30-02)
- `tests/entry/test_engine.py`, `test_ab_report.py` (plan 30-03)

Context:
- `.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md`
- `.planning/phases/30-stock-level-entry-confirmation/30-RESEARCH.md`
- `.planning/phases/30-stock-level-entry-confirmation/30-01-NOTES.md`
