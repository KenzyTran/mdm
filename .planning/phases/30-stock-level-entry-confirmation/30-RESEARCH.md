# Phase 30: Stock-Level Entry Confirmation — Research

**Researched:** 2026-04-09
**Domain:** Stock-level entry signal detection (52wk high breakout + Pocket Pivot) on VN100, gated by VN30 MDM BUY window
**Confidence:** HIGH (semantics fully locked in CONTEXT.md; all integration points exist in repo)

## Summary

Phase 30 is a thin, well-scoped signal-detection + reporting phase. CONTEXT.md (D-01..D-21) has already locked every formula, threshold, window rule, and output contract — the planner's job is to decompose these into small vertical tasks, not to make design choices. All upstream assets (adjusted OHLCV reader, CANSLIM scorer output shape, HybridEngine state series, Markdown+CSV audit convention) are in place from Phases 28/29. The only real research questions are (a) the exact call shape of `HybridEngine` so Phase 30 can consume its state series without re-running it, and (b) the test-fixture strategy for detectors that need 252 trading days of history.

**Primary recommendation:** Build `strategies/entry/` as five pure-Python modules (`config.py`, `option_a.py`, `option_c.py`, `window.py`, `engine.py`) plus an `ab_report.py` script. Keep detectors vectorized over a per-ticker adjusted OHLCV frame; keep the window tracker as a stateless function over the MDM state series. Tests under `tests/entry/` mirroring `tests/canslim/` style.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Package Layout**
- **D-01:** New package `strategies/entry/` parallel to `strategies/canslim/`. Files: `config.py` (EntryConfig dataclass), `option_a.py`, `option_c.py`, `window.py` (MDM-BUY window tracker), `ab_report.py`.
- **D-02:** All price/volume reads go through `connectors/adjust.py::adjust_ohlc()`. No raw unadjusted reads.

**Option A Detector (ENTRY-01)**
- **D-03:** Fire on bar `t` when ALL hold (adjusted OHLCV):
  - `close[t] > max(close[t-252..t-1])` (new 52-week high on close)
  - `vol[t] >= 1.5 * mean(vol[t-50..t-1])`
  - `close[t] > open[t]` (up bar)
  - `close[t] >= (high[t] + low[t]) / 2` (upper-half-of-range close)
- **D-04:** 252, 50, 1.5 are EntryConfig-tunable; formulas above are locked semantics.

**Option C Detector (ENTRY-02, Pocket Pivot)**
- **D-05:** Fire on bar `t` when ALL hold:
  - `close[t] > open[t]`
  - `close[t] >= MA50[t]`
  - `vol[t] > max(down_day_vols[t-10..t-1])` where down day = `close < prior close`. If zero down days in last 10 sessions → **fail-closed, no fire**.
  - `close[t] >= 0.85 * max(high[t-50..t-1])` (within 15% of 50-day high)
- **D-06:** MA50 = simple MA on adjusted close. Config exposes `ma_length=50`, `pocket_lookback=10`, `base_tolerance=0.15`.

**Entry Window (ENTRY-03)**
- **D-07:** Window = 20 trading days from most recent **CASH/SELL → BUY transition** of MDM state series. Signal bar itself counts as day 1.
- **D-08:** Each new CASH/SELL→BUY transition **resets** window to 20. Continuous BUY does not extend — original clock keeps running.
- **D-09:** Hard expiry: confirmations on day 21+ rejected even if MDM still BUY.
- **D-10:** MDM state series = existing `HybridEngine` VN30 state (v6 best). Passed in at construction. Phase 30 does **NOT** re-run MDM.

**Fill Model (ENTRY-04)**
- **D-11:** Fill = `open[t+1]` (ATO) on adjusted OHLC. Signal bar `t`, fill bar `t+1`.
- **D-12:** If `t` is last bar in dataset → drop fill, record "unfilled: no next bar".
- **D-13:** T+2 / ceiling / floor lock handling **deferred to Phase 31**. Phase 30 assumes next-day open always tradable. Documented in A/B report.

**Duplicate Handling**
- **D-14:** Option A and Option C are **two independent streams**. One ticker can contribute one fill to each stream in the same window.
- **D-15:** Within a single stream, per (ticker, window, detector): only the **first** fire is recorded; subsequent fires in the same window suppressed.

**A/B Comparison Universe (ENTRY-05, SC5)**
- **D-16:** Report produced **twice** — raw VN100 universe (no CANSLIM filter) AND CANSLIM-qualified subset (all Phase 29 per-letter booleans TRUE on signal bar: `c_pass & a_pass & n_pass & s_pass & l_pass & i_pass & liq_pass`). Side-by-side in report.
- **D-17:** Universe source = Phase 29 default `current-vn100` mode. Survivorship bias accepted.
- **D-18:** Window 2014-01-01 → 2025-12-31, driven by VN30 MDM state series. Report header states actual first/last date after load.
- **D-19:** Report metrics (per detector × per universe):
  - Total fills
  - Unique tickers filled
  - Number of BUY windows that produced ≥1 fill
  - Mean fills per BUY window
  - Distribution of "days since BUY" at fire time (1–20)
  - Overlap set: tickers filled by both A and C within same window

**EntryConfig**
- **D-20:** Dataclass at `strategies/entry/config.py`. All numeric thresholds from D-03..D-06 and 20-day window overridable kwargs. No YAML — Python-native.

**Output Location**
- **D-21:** Report at `docs/audits/phase30-entry-ab.md` + companion CSVs under `docs/audits/phase30/`. No notebooks.

### Claude's Discretion
- Exact unit-test layout under `tests/entry/` (repo uses `tests/canslim/`, not `tests/strategies/canslim/` — plan should match)
- `window.py` generator vs materialized list
- Vectorized vs row-by-row detectors (correctness first, optimize if slow)
- Internal helper for "down-day volumes last 10 sessions" rolling max
- Whether A/B report includes small matplotlib plot or stays pure tabular

### Deferred Ideas (OUT OF SCOPE)
- T+2 settlement, 7% ceiling/floor lock → Phase 31 (GATE/PORT)
- Position sizing / Kelly / equal-weight → Phase 31
- Exit logic (MDM SELL, 8% stop, MA50 trailing, RS<70) → Phase 31
- Re-entry cooldown → Phase 31
- Costs (commission, tax, slippage) → Phase 31
- Liquidity gate (20d ADV ≥ 10× position size) → Phase 31
- In-sample sweep over EntryConfig thresholds → Phase 32
- Entry-density UI dashboards → future
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENTRY-01 | Option A: 52-wk high + vol surge + close>open + upper-half close | D-03/D-04 fully specify formula; implementable as pure-pandas rolling ops on adjusted frame. Test fixtures: synthetic 260-bar ticker series. |
| ENTRY-02 | Option C (Pocket Pivot): vol > max down-day vols last 10d, close≥MA50, in/near base | D-05/D-06 fully specify; "fail-closed on zero down days" is the subtle rule the planner must add as explicit branch + test. |
| ENTRY-03 | 20-day window from MDM BUY event; expire after | D-07..D-10 specify transition semantics. Consume `HybridEngine(...).run(df)['state']` column (V2MarketState string values). No re-run of MDM — pass series in via constructor. |
| ENTRY-04 | Fill at next-day open (ATO), not signal close | D-11..D-13. Last-bar edge case (D-12) and T+2/lock deferral (D-13) must appear as explicit test + report note. |
| ENTRY-05 | A/B comparison on VN100 2014-2025 | D-16..D-19 fully specify metrics. Run EntryEngine twice (canslim_scores=None and =scorer_df). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.10+**, pandas ≥2.0, numpy ≥1.24, matplotlib ≥3.7. uv for package management.
- **snake_case** modules/functions, **PascalCase** classes/dataclasses, `MA50`-style short names for domain concepts.
- **Dataclass config with `__post_init__` validation** — fail-loud, no silent fallback (matches Phase 29 D-08).
- **Layered architecture**: data_loader → indicators → signal_detection → engine. Phase 30 follows this.
- **Google-style docstrings** on all public classes/methods.
- **Code-Docs Sync Rule**: `docs/rules_entry.md` must be created in the same commit as `strategies/entry/` code.
- **`state[i-1]` discipline**: no look-ahead. The 20-day window check and fill model already encode this (signal at `t`, fill at `t+1`). Unit test must assert.
- **GSD workflow**: all file edits occur within `/gsd:execute-phase`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | ≥2.0 | Rolling windows, per-ticker groupby, output frames | Already the project standard; all sibling packages use it |
| numpy | ≥1.24 | Vectorized comparisons | Sibling of pandas, already in stack |
| pytest | ≥9.0 | Unit tests with fixtures (see `tests/canslim/conftest.py` for pattern) | Already project test runner |

### Supporting
| Module | Path | Purpose | Reuse Pattern |
|--------|------|---------|---------------|
| `adjust_ohlc` | `connectors/adjust.py` | Produces `adj_open/high/low/close` from raw stock_eod + `totaladjustrate`. Volume NOT adjusted (documented). | Call on every raw frame before detector — matches Phase 28 D-05/D-06. |
| `CanslimConfig` / `CanslimScorer` | `strategies/canslim/` | Phase 29 scorer output with columns `date, ticker, c_pass, c_plus_pass, a_pass, a_plus_pass, n_pass, s_pass, l_pass, i_pass, liq_pass, rs_rating, score` | For D-16 filter: left-join scorer output on `(date,ticker)`, keep rows where `c_pass & a_pass & n_pass & s_pass & l_pass & i_pass & liq_pass`. |
| `HybridEngine` (V2 base) | `strategies/mdm_hybrid/mdm_hybrid_engine.py` | `run(df)` returns a DataFrame with a `state` column of `V2MarketState` string values (`"BUY"`, `"CASH"`, `"SELL"`) | Phase 30 accepts the resulting `state` series as input (see D-10). Do not instantiate HybridEngine inside EntryEngine. |
| `V2MarketState` | `strategies/mdm_hybrid/position_manager.py` | Enum with values `BUY`/`CASH`/`SELL` (string-valued) | Window tracker compares string values; no import coupling needed (use string literals) OR re-export the enum for type safety. Planner decides. |

**Installation:** Nothing new. All deps already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
strategies/entry/
├── __init__.py          # re-export EntryEngine, EntryConfig, Fill
├── config.py            # EntryConfig dataclass + __post_init__ validation
├── option_a.py          # detect_option_a(df: pd.DataFrame, cfg) -> pd.Series[bool]
├── option_c.py          # detect_option_c(df: pd.DataFrame, cfg) -> pd.Series[bool]
├── window.py            # buy_windows(state: pd.Series, window_days=20) -> list[(start, end)]
│                        # is_in_window(date, windows) -> (bool, days_since_buy)
├── engine.py            # EntryEngine orchestrator (takes mdm_state, universe, scores, price_loader, cfg)
└── ab_report.py         # script entry for docs/audits/phase30-entry-ab.md generation

tests/entry/
├── conftest.py          # synthetic OHLCV fixture builders (260+ bars)
├── test_config.py       # threshold validation
├── test_option_a.py     # 4-clause AND: positive, each single-clause fail, edge cases
├── test_option_c.py     # pocket-pivot positive, zero-down-days fail-closed, base tolerance edge
├── test_window.py       # reset semantics, day-1 inclusive, day-21 reject, continuous BUY no-extend
├── test_engine.py       # dedup per stream, A/C independence, last-bar unfilled, state[i-1] look-ahead guard
└── test_ab_report.py    # tiny end-to-end with 2 tickers and a synthetic MDM state
```

Note: repo convention is `tests/canslim/`, not `tests/strategies/canslim/`. Phase 30 should use `tests/entry/` (flat, not nested under `strategies/`).

### Pattern 1: Per-Ticker Vectorized Detector
**What:** Each detector takes an adjusted single-ticker OHLCV frame (sorted by date) and returns a boolean Series aligned to the frame's index.
**Why:** Matches Phase 29's rule modules (`strategies/canslim/rules/technical.py::compute_n/compute_s`) which operate per-stock via groupby.
**Example skeleton:**
```python
# strategies/entry/option_a.py
def detect_option_a(df: pd.DataFrame, cfg: EntryConfig) -> pd.Series:
    """Return bool Series: True on bars where Option A fires.

    df must have columns: adj_open, adj_high, adj_low, adj_close, totalvol.
    Sorted ascending by date, single ticker.
    """
    c = df["adj_close"]
    o = df["adj_open"]
    h = df["adj_high"]
    lo = df["adj_low"]
    v = df["totalvol"]

    hi_252 = c.shift(1).rolling(cfg.high_lookback).max()    # exclude today
    avg_vol_50 = v.shift(1).rolling(cfg.vol_lookback).mean()

    cond_new_high = c > hi_252
    cond_vol_surge = v >= cfg.vol_mult * avg_vol_50
    cond_up_bar = c > o
    cond_upper_half = c >= (h + lo) / 2.0

    return (cond_new_high & cond_vol_surge & cond_up_bar & cond_upper_half).fillna(False)
```

### Pattern 2: Stateless Window Tracker
**What:** Window tracker takes the full MDM state series (indexed by date) and returns a list of `(window_start_date, window_end_date)` tuples — one per CASH/SELL→BUY transition.
**Why:** Pure function, trivially testable. Engine just asks `is_in_any_window(signal_date)` per fire.
**Edge cases the planner MUST cover as tests:**
- First bar of the state series is already BUY (no prior CASH → does it count as a transition? CONTEXT silent. **Open question #1** — default recommendation: treat "series starts in BUY" as an initial transition at index 0, but surface for user confirmation before coding).
- Single-bar BUY flip (CASH→BUY→CASH in 2 days): one window of 2 days.
- BUY→SELL→BUY (no CASH in between): SELL→BUY is a valid transition per D-07 ("CASH/SELL → BUY"). Two windows.
- Continuous BUY > 20 days: D-08 says clock does NOT extend; only day 1–20 after the original transition produce fills.

### Pattern 3: Detector → Window → Fill Pipeline
```
for ticker in universe:
    df_adj = adjust_ohlc(raw_prices[ticker])
    df_adj = add_ma50(df_adj)                       # simple MA on adj_close
    fires_a = detect_option_a(df_adj, cfg)
    fires_c = detect_option_c(df_adj, cfg)
    for detector_name, fires in [("A", fires_a), ("C", fires_c)]:
        for signal_date in df_adj.index[fires]:
            window_id = find_window(signal_date, mdm_windows)
            if window_id is None: continue
            if already_fired(ticker, window_id, detector_name): continue
            fill_bar = next_bar(df_adj, signal_date)
            if fill_bar is None:
                record_unfilled(...); continue
            fills.append(Fill(signal_date, fill_bar, ticker, detector_name,
                              fill_price=df_adj.loc[fill_bar, "adj_open"], ...))
```

### Anti-Patterns to Avoid
- **Re-running `HybridEngine` inside `EntryEngine`** — D-10 explicitly forbids. State series is an input.
- **Using unadjusted prices** — D-02. Every frame goes through `adjust_ohlc` first.
- **`close[t-252:t+1]` window including today** — Option A new-high test must EXCLUDE today (`shift(1).rolling(252).max()`). Easy off-by-one.
- **Computing MA50 on raw close** — D-06 says adjusted close.
- **Filling on signal-bar close** — D-11 says next-day open. Unit test required.
- **Extending window on continuous BUY** — D-08 locks this. The window is anchored to the transition bar, not "while state == BUY".
- **Nested `tests/strategies/entry/`** — repo convention is flat `tests/canslim/`; match it (`tests/entry/`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Price adjustment from raw stock_eod | Custom split/dividend logic | `connectors/adjust.py::adjust_ohlc` | Already audited in Phase 28; multiplies by `totaladjustrate`. |
| CANSLIM qualification on signal bar | Re-implementing C/A/N/S/L/I/liq tests | `strategies/canslim/CanslimScorer` output | Phase 29 locked semantics; D-16 says use per-letter booleans. |
| MDM state series | Re-implementing HybridEngine | Consume `HybridEngine.run(vn30_df)["state"]` as input | D-10 explicit. |
| MA50 | Custom rolling mean | `pd.Series.rolling(50).mean()` on `adj_close` | Trivial; no helper needed but check `strategies/mdm_hybrid/indicators.py` for an existing one before duplicating. |
| Rolling max over variable-filter window (down-day vols) | Loop | `vol.where(is_down_day).shift(1).rolling(10, min_periods=1).max()` then compare | Standard pandas idiom. Fail-closed when no down days: rolling max over all-NaN window returns NaN → comparison returns False naturally. |

**Key insight:** Phase 30 is glue + two formulas + one windowing function. Zero novel algorithms. Every non-trivial primitive (adjustment, CANSLIM pass, MDM state) already exists in the codebase.

## Runtime State Inventory

Not applicable — Phase 30 is greenfield code addition (new package + new report). No rename, no refactor, no migration. No stored state, no live services, no OS registrations, no secrets, no build artifacts to update.

## Common Pitfalls

### Pitfall 1: Off-by-one in "new 52-week high"
**What goes wrong:** Using `rolling(252).max()` without `.shift(1)` includes today's close in the reference max, so `close[t] > max(...)` can never fire.
**How to avoid:** Use `c.shift(1).rolling(252).max()`.
**Warning sign:** Option A detector returns all-False on a known breakout fixture.

### Pitfall 2: Pocket Pivot zero-down-days silent-pass
**What goes wrong:** If the last 10 sessions have no down days, naive `max(down_vols)` returns NaN/−inf and `vol > NaN` evaluates to False in pandas — BUT if implemented with Python `max()` on empty list it raises. Or if using `fillna(0)` it becomes a free pass (any positive volume > 0).
**How to avoid:** Leave NaN in place, use pandas comparison (False propagation). D-05 says **fail-closed** when fewer than 1 down day. Unit test for this exact scenario.

### Pitfall 3: Window day-1 vs day-0 counting
**What goes wrong:** D-07 says "signal bar counts as day 1". Easy to implement as day 0 and get 21-day windows.
**How to avoid:** If transition bar is `T`, valid signal bars are `T, T+1, ..., T+19` (20 bars total, inclusive). Test both endpoints.

### Pitfall 4: Look-ahead via MDM state alignment
**What goes wrong:** MDM state at `T` might be computed using `close[T]` (it is — HybridEngine processes today's close to decide today's state). That's fine for window eligibility because the state is known at end-of-day `T` and the fill is `open[T+1]`. But if the planner reads `state[T+1]` to validate the fill bar, that's look-ahead.
**How to avoid:** Window eligibility checked ONLY at signal bar `t`. Fill executes at `t+1` unconditionally (or drops per D-12). Unit test: shuffle future state to garbage and assert no fills change.

### Pitfall 5: Same ticker fires A and C on same bar
**What goes wrong:** D-14 says independent streams — so a single bar can emit one A fill AND one C fill for the same ticker. Easy to accidentally dedup across streams.
**How to avoid:** Dedup key = `(ticker, window_id, detector_name)` not `(ticker, window_id)`.

### Pitfall 6: Last-bar fill silently dropped without record
**What goes wrong:** D-12 says unfilled-last-bar must be **recorded** as "unfilled: no next bar", not silently dropped. Easy to just skip.
**How to avoid:** Return two lists or tag fills with a status column. Report includes unfilled count.

### Pitfall 7: CANSLIM join on date key
**What goes wrong:** CanslimScorer output is keyed by `(date, ticker)`. If prices are daily and scorer runs daily, join is clean. But if scorer is sparse (only on rebalance days), join produces NaNs and naive `&` treats NaN as False — correct behavior, but silently drops all signals between rebalances. Verify scorer cadence in Phase 29 output before implementing.
**How to avoid:** Check `strategies/canslim/scorer.py` output cadence. If sparse, forward-fill pass booleans before joining. **Open question #2.**

## Code Examples

### Option C "down-day vol max" idiom
```python
# strategies/entry/option_c.py
def detect_option_c(df: pd.DataFrame, cfg: EntryConfig) -> pd.Series:
    c = df["adj_close"]
    o = df["adj_open"]
    h = df["adj_high"]
    v = df["totalvol"]

    prev_close = c.shift(1)
    is_down_day = c < prev_close
    down_vols = v.where(is_down_day)                            # NaN on up days
    # max over last 10 sessions, EXCLUDING today
    max_down_vol_10 = down_vols.shift(1).rolling(
        cfg.pocket_lookback, min_periods=1
    ).max()                                                      # NaN if zero down days -> fail-closed

    ma50 = c.rolling(cfg.ma_length).mean()
    hi_50 = h.shift(1).rolling(cfg.ma_length).max()

    cond_up_bar = c > o
    cond_above_ma = c >= ma50
    cond_vol_pocket = v > max_down_vol_10                        # NaN -> False
    cond_near_base = c >= (1.0 - cfg.base_tolerance) * hi_50

    return (cond_up_bar & cond_above_ma & cond_vol_pocket & cond_near_base).fillna(False)
```

### Window tracker
```python
# strategies/entry/window.py
def compute_buy_windows(state: pd.Series, window_days: int = 20) -> list[tuple]:
    """Return list of (start_idx, end_idx_inclusive) for each CASH/SELL->BUY transition.

    state: pd.Series indexed by date, values in {"BUY","CASH","SELL"}.
    """
    prev = state.shift(1)
    is_transition = (state == "BUY") & (prev.isin(["CASH", "SELL"]))
    # Also handle series-starts-in-BUY edge (see Open Question #1)
    transitions = state.index[is_transition]
    out = []
    idx = list(state.index)
    for t in transitions:
        i = idx.index(t)
        j = min(i + window_days - 1, len(idx) - 1)
        out.append((idx[i], idx[j]))
    return out
```

### EntryConfig skeleton (mirrors `CanslimConfig`)
```python
# strategies/entry/config.py
from dataclasses import dataclass

@dataclass
class EntryConfig:
    # Option A
    high_lookback: int = 252
    vol_lookback: int = 50
    vol_mult: float = 1.5
    # Option C
    ma_length: int = 50
    pocket_lookback: int = 10
    base_tolerance: float = 0.15
    # Window
    window_days: int = 20

    def __post_init__(self) -> None:
        if self.high_lookback < 2:
            raise ValueError("high_lookback must be >= 2")
        if self.vol_lookback < 1:
            raise ValueError("vol_lookback must be >= 1")
        if self.vol_mult < 1.0:
            raise ValueError("vol_mult must be >= 1.0")
        if self.ma_length < 2:
            raise ValueError("ma_length must be >= 2")
        if self.pocket_lookback < 1:
            raise ValueError("pocket_lookback must be >= 1")
        if not (0 < self.base_tolerance < 1):
            raise ValueError("base_tolerance must be in (0, 1)")
        if self.window_days < 1:
            raise ValueError("window_days must be >= 1")
```

## State of the Art

Not applicable — Option A (52-week high + volume surge) and Option C (Pocket Pivot, Gil Morales / Dr. K) are fixed published methodologies. CONTEXT.md locks all thresholds. No library version drift concerns.

## Open Questions

1. **Series-starts-in-BUY edge case.** If the VN30 MDM state series begins on a bar where state is already BUY (no prior CASH/SELL bar visible), does that count as a transition to anchor a window? CONTEXT.md is silent.
   - What we know: D-07 says "most recent CASH/SELL → BUY transition". No prior bar = no transition observable.
   - Recommendation: Treat as "no window" until an actual transition is observed. Test fixture should cover it. Surface during planning for user confirmation — one-line decision.

2. **CanslimScorer output cadence.** Is Phase 29's scorer output dense (per trading day) or sparse (per rebalance)? Affects join semantics for D-16 CANSLIM-qualified filter.
   - What we know: Phase 29 output columns include `date` and per-letter booleans. `UNIV-02` says "semi-annual rebalance step-changes, universe stable between rebalance dates" — universe is stepped, but CANSLIM *rules* (N, S, liquidity, RS) are technical and daily-computable. Unclear whether the scorer is actually run daily or materialized at rebalance dates only.
   - Recommendation: Task 1 of Phase 30 should open `strategies/canslim/scorer.py` and confirm cadence. If sparse, use forward-fill on per-letter booleans before left-joining onto price bars.

3. **Where does raw VN100 OHLCV come from for the A/B report?** Phase 28 built `connectors/postgres.py` helpers. The A/B script needs a price loader that (a) reads `stock_eod` for each ticker in the VN100 universe, (b) applies `adjust_ohlc`, (c) feeds the detector. Need to confirm there's already a batch loader or whether Phase 30 writes a thin wrapper.
   - Recommendation: Task 1 of Phase 30 also audits `connectors/postgres.py` for a `load_prices(tickers, start, end)` helper. If missing, Phase 30 adds a minimal one under `connectors/` (not under `strategies/entry/` — keeps data-access layer clean).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.10+ | — |
| pandas | detectors, report | ✓ | ≥2.0 | — |
| numpy | vectorized ops | ✓ | ≥1.24 | — |
| pytest | tests | ✓ | ≥9.0.2 | — |
| Postgres (stock_eod) | VN100 price data | ✓ (Phase 28 verified) | — | — |
| `strategies/canslim` (Phase 29 scorer) | D-16 qualified-universe filter | ✓ | — | — |
| `strategies/mdm_hybrid` (HybridEngine) | D-10 MDM state series | ✓ | — | — |
| matplotlib | optional plot in A/B report | ✓ | ≥3.7 | Pure tabular |

**No blocking gaps.**

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths=["tests"]) |
| Quick run command | `uv run pytest tests/entry/ -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENTRY-01 | Option A fires on 52wk high + vol surge + up bar + upper-half close; fails when any clause fails | unit | `uv run pytest tests/entry/test_option_a.py -x` | ❌ Wave 0 |
| ENTRY-02 | Option C fires on pocket pivot; fails-closed when zero down days in last 10 | unit | `uv run pytest tests/entry/test_option_c.py -x` | ❌ Wave 0 |
| ENTRY-03 | Window 20 days from CASH/SELL→BUY; day 1 inclusive; day 21 rejected; no extension on continuous BUY; reset on new transition | unit | `uv run pytest tests/entry/test_window.py -x` | ❌ Wave 0 |
| ENTRY-04 | Fill = next-day open; last-bar drops to "unfilled: no next bar"; no look-ahead (state[i-1] discipline) | unit | `uv run pytest tests/entry/test_engine.py::test_fill_next_open tests/entry/test_engine.py::test_last_bar_unfilled tests/entry/test_engine.py::test_no_lookahead -x` | ❌ Wave 0 |
| ENTRY-05 | A/B engine runs twice (raw VN100 + CANSLIM-qualified) and produces required metric columns | unit + integration | `uv run pytest tests/entry/test_ab_report.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/entry/ -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/entry/conftest.py` — synthetic OHLCV fixture builders (260+ bars, configurable volume/close patterns)
- [ ] `tests/entry/test_config.py` — EntryConfig validation
- [ ] `tests/entry/test_option_a.py` — ENTRY-01 (positive + each clause fails)
- [ ] `tests/entry/test_option_c.py` — ENTRY-02 (positive, zero-down-days fail-closed, base tolerance edge)
- [ ] `tests/entry/test_window.py` — ENTRY-03 (reset, day-1 inclusive, day-21 reject, continuous BUY, SELL→BUY transition, series-starts-in-BUY edge)
- [ ] `tests/entry/test_engine.py` — ENTRY-04 (next-day open fill, last-bar unfilled, no look-ahead, A/C stream independence, within-stream dedup)
- [ ] `tests/entry/test_ab_report.py` — ENTRY-05 (tiny 2-ticker run producing both tables)
- [ ] Framework install: none needed (pytest already installed)

## Sources

### Primary (HIGH confidence)
- `.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md` — All formulas, thresholds, semantics locked (D-01..D-21)
- `.planning/REQUIREMENTS.md` §v7.0 ENTRY-01..ENTRY-05
- `.planning/ROADMAP.md` §Phase 30 — Goal + SC1..SC5
- `strategies/canslim/config.py`, `strategies/canslim/scorer.py` — Phase 29 dataclass + scorer output shape
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` (L130-181) — `run(df)` returns DataFrame with `state` column of V2MarketState string values
- `strategies/mdm_hybrid/position_manager.py` (L18-20) — `V2MarketState` enum: `BUY`, `CASH`, `SELL` (string-valued)
- `connectors/adjust.py` — `adjust_ohlc()` signature and semantics
- `pyproject.toml` — pytest config, dependency versions
- `CLAUDE.md` — project conventions (naming, layered architecture, Code-Docs Sync Rule)
- `tests/canslim/` directory listing — confirms flat `tests/<pkg>/` layout convention

### Secondary (MEDIUM confidence)
- None — all findings sourced directly from repo files.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Locked decisions (from CONTEXT.md): HIGH — verbatim copy, nothing to interpret
- Integration points (adjust_ohlc, HybridEngine, CanslimScorer): HIGH — verified by reading source files
- Test layout convention (`tests/entry/` vs `tests/strategies/entry/`): HIGH — repo uses flat `tests/canslim/`
- Pitfalls: HIGH — derived from locked semantics + `state[i-1]` memory rule
- Open Questions (3): MEDIUM — flagged for planner to resolve in Task 1 (code audit) or by user ack

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 days — stack stable, CONTEXT.md locked)
