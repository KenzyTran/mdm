# Phase 30-01 — Open Question Resolutions

Resolved via code audit during 30-01 execution (2026-04-09). These answers are
locked and consumed by 30-02 and 30-03 executors.

## 1. CanslimScorer output cadence (OQ #2 / Pitfall #7)

**Answer:** Per-date, per-ticker (sparse-by-call, not sparse-by-design).

`strategies/canslim/scorer.py::CanslimScorer.score(as_of_date: date) -> pd.DataFrame`
takes **a single as-of-date** and returns one row per (as_of_date, ticker) for
every ticker in the universe on that date. All per-letter booleans
(`c_pass, c_plus_pass, a_pass, a_plus_pass, n_pass, s_pass, l_pass, i_pass,
liq_pass`) plus `rs_rating` and `score` are computed fresh on that bar from
daily technical inputs (N, S, RS, liquidity) and quarterly fundamentals
(C/A). There is no rebalance gating inside the scorer — the universe loader
handles universe membership stepping; the rules themselves are daily-computable.

**Implementation note for 30-03:** To build the CANSLIM-qualified stream for
D-16, iterate over the trading dates in the signal-bar set and call
`scorer.score(d)` for each `d`, then left-join on `(date, ticker)`. No
forward-fill needed — every trading day has a complete snapshot. For
performance, 30-03 may optionally batch by calling `score` once per unique
signal-bar date (not once per fire) and caching. If the per-date cost is
prohibitive, 30-03 can cache daily frames in a dict keyed by date; that is a
perf optimization, not a correctness concern.

## 2. VN100 batch price loader (OQ #3)

**Answer:** Exists. Use `connectors/postgres.py::load_stock_eod(tickers, start, end)`.

Audit of `connectors/postgres.py` shows `load_stock_eod` at line 61 with the
signature `load_stock_eod(tickers, start, end)` returning an OHLCV+adjustrate
panel from `stock_eod`. This is the batch loader Phase 30-03 needs.

**Implementation note for 30-03:** The `ab_report.py` script should:
1. Resolve VN100 tickers via `strategies/canslim/universe.py::UniverseLoader`
   (same source Phase 29 used — `current-vn100` mode per D-17).
2. Call `connectors.postgres.load_stock_eod(tickers, "2014-01-01", "2025-12-31")`.
3. Group by `stockcode`, pass each per-ticker frame through
   `connectors.adjust.adjust_ohlc()` to materialize `adj_open/high/low/close`.
4. Feed adjusted frames into `EntryEngine`.

No new connector wrapper is required. Do NOT add loader code under
`strategies/entry/` — keeps data-access layer clean.

## 3. Series-starts-in-BUY edge case (OQ #1)

**Answer (LOCKED):** No initial window.

If the VN30 MDM state series begins on a bar where state is already BUY with
no observable prior CASH/SELL bar, that is **NOT** treated as a transition and
does **NOT** open a window. The first window only opens on an actually-observed
CASH/SELL→BUY transition later in the series.

**Rationale:** D-07 defines a window as anchored to a "CASH/SELL → BUY
transition". Without a visible prior bar in the opposing state, no transition
can be observed. Treating the first bar as a synthetic transition would
fabricate signal eligibility that Dr. K's rules do not grant. Fail-closed is
consistent with the rest of the phase (Pocket Pivot zero-down-days, unfilled
last bar, etc.).

**Implementation note for 30-02 (window.py):** In `compute_buy_windows`,
derive transitions via `prev = state.shift(1); (state == "BUY") & prev.isin(["CASH", "SELL"])`.
The shift(1) naturally produces NaN on index 0, which `isin([...])` evaluates
to False, so index-0 BUY is silently excluded from transitions. No special
case needed — just do not add a "first bar BUY counts as transition" branch.
A dedicated unit test (`test_window_series_starts_in_buy_no_initial_window`)
pins this behavior.
