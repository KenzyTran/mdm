# Phase 30: Stock-Level Entry Confirmation - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect stock-level entry confirmation signals (Option A = 52-week high + volume surge; Option C = Pocket Pivot) that fire within a 20-trading-day window after an MDM BUY event, with fills modeled at next-day open (ATO), and produce an A/B comparison of fill counts on VN100 2014–2025. Portfolio construction, position sizing, stops, T+2 / ceiling-floor lock handling, and the MDM capital-allocation gate belong to Phase 31 and are out of scope here.

</domain>

<decisions>
## Implementation Decisions

### Package Layout
- **D-01:** New package `strategies/entry/` parallel to `strategies/canslim/`. Proposed files: `config.py` (EntryConfig dataclass), `option_a.py`, `option_c.py`, `window.py` (MDM-BUY window tracker), `ab_report.py`.
- **D-02:** All price/volume reads go through `connectors/adjust.py::adjust_ohlc()` — same discipline as Phase 28/29. No raw unadjusted reads.

### Option A Detector (ENTRY-01)
- **D-03:** Fire condition on bar `t` (all values from adjusted OHLCV):
  - `close[t] > max(close[t-252..t-1])` — new 52-week high on close
  - `vol[t] >= 1.5 * mean(vol[t-50..t-1])` — volume surge vs 50-day avg
  - `close[t] > open[t]` — up bar
  - `close[t] >= (high[t] + low[t]) / 2` — upper-half-of-range close
- **D-04:** "252" and "50" and "1.5" are EntryConfig-tunable defaults; the formulas above are the locked semantics.

### Option C Detector (ENTRY-02, Pocket Pivot)
- **D-05:** Fire condition on bar `t`:
  - `close[t] > open[t]`
  - `close[t] >= MA50[t]`
  - `vol[t] > max(down_day_vols[t-10..t-1])` where a down day = `close < prior close`. If fewer than 1 down day in the last 10 sessions, the pocket-pivot volume test fails-closed (no fire).
  - `close[t] >= 0.85 * max(high[t-50..t-1])` — "in/near base", within 15% of 50-day high
- **D-06:** MA50 is simple moving average on adjusted close. EntryConfig exposes `ma_length=50`, `pocket_lookback=10`, `base_tolerance=0.15`.

### Entry Window (ENTRY-03)
- **D-07:** The window is 20 trading days, measured from the bar of the most recent **CASH/SELL → BUY transition** of the MDM state series. The signal bar itself counts as day 1.
- **D-08:** Each new `CASH/SELL → BUY` transition **resets** the window to 20 days. If MDM stays continuously BUY (no transition), the original clock keeps running — no extension.
- **D-09:** Window expiry is hard: confirmations on day 21+ are rejected, even if MDM is still BUY.
- **D-10:** MDM state series used by Phase 30 is the existing `HybridEngine` VN30 state (the v6 configuration currently recorded as the best model). The state series is passed in at engine construction — Phase 30 does **not** re-run MDM.

### Fill Model (ENTRY-04)
- **D-11:** Fill price = `open[t+1]` (next-day open, ATO) on adjusted OHLC. Signal bar = `t`, fill bar = `t+1`.
- **D-12:** If `t` is the last available bar in the dataset, the fill is dropped (recorded as "unfilled: no next bar") — not carried forward.
- **D-13:** T+2 / ceiling / floor lock handling is **deferred to Phase 31**. Phase 30 assumes every next-day open is tradable. This simplification is documented in the A/B report.

### Same-Window Duplicate Handling
- **D-14:** Option A and Option C are tracked as **two independent signal streams** for the A/B report. A single ticker can contribute one fill to each stream within the same window.
- **D-15:** Within a single stream, if the same ticker fires multiple times inside one window, only the **first** fire per (ticker, window, detector) is recorded — subsequent fires in the same window are suppressed.

### A/B Comparison Universe (ENTRY-05, SC5)
- **D-16:** Produce the A/B report **twice** — once on the raw VN100 universe (no CANSLIM filter) and once on the CANSLIM-qualified subset (all per-letter booleans from Phase 29 scorer true on the signal bar). Both tables live side-by-side in the report.
- **D-17:** Universe source = Phase 29 default `current-vn100` mode. Survivorship bias accepted (same as Phase 29).
- **D-18:** Window = 2014-01-01 → 2025-12-31, driven by VN30 MDM state series availability. The A/B report header states the actual first/last date used after data loading.
- **D-19:** Report metrics (per detector × per universe):
  - Total fills
  - Unique tickers filled
  - Number of BUY windows that produced ≥1 fill
  - Mean fills per BUY window
  - Distribution of "days since BUY" at fire time (1–20)
  - Overlap set: tickers filled by both A and C within the same window

### EntryConfig
- **D-20:** Dataclass at `strategies/entry/config.py`. All numeric thresholds from D-03..D-06 and the 20-day window are overridable kwargs. No YAML — Python-native, consistent with Phase 29.

### Output Location
- **D-21:** Report at `docs/audits/phase30-entry-ab.md` + companion CSVs under `docs/audits/phase30/` — same Markdown+CSV convention as Phase 28/29. No notebooks.

### Claude's Discretion
- Exact unit-test layout under `tests/strategies/entry/`
- Whether `window.py` exposes a generator or materializes a list of windows
- Vectorized vs row-by-row implementation of detectors (correctness first, optimize if slow)
- Internal helper for the "down-day volumes in last 10 sessions" rolling max
- Whether A/B report includes a small plot (matplotlib) or stays pure tabular

### Folded Todos
None — no pending todos matched Phase 30 scope at context-gather time.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- `.planning/ROADMAP.md` §Phase 30 — Goal, success criteria SC1–SC5, dependency on Phase 29
- `.planning/REQUIREMENTS.md` ENTRY-01..ENTRY-05 — Entry confirmation requirements

### Upstream Phase 29 Artifacts (mandatory reads)
- `.planning/phases/29-vn100-universe-canslim-scorer/29-CONTEXT.md` — Universe mode, scorer output shape (per-letter booleans), publish_date guard
- `strategies/canslim/` — Scorer package used to produce the CANSLIM-qualified universe for the second A/B table
- `docs/audits/phase29-canslim-validation.md` — Baseline spot-check methodology to mirror for Phase 30 reporting style

### Upstream Phase 28 Artifacts (mandatory reads)
- `connectors/postgres.py`, `connectors/mysql.py` — Engines/helpers for price + VN100 list reads
- `connectors/adjust.py` — `adjust_ohlc()` — ALL price/volume reads must go through this
- `docs/audits/phase28-data-audit.md` — VN100 coverage, delisted handling

### MDM State Source
- `models/mdm_engine.py` / HybridEngine entry point (see memory: HybridEngine + best sweep config = 190.8% is the current best VN30 model) — source of the MDM state series passed into Phase 30
- `docs/rules_mdm_hybrid.md` — Rules governing when CASH/SELL→BUY transitions happen (important for understanding what the 20-day window is counting from)

### Rules docs to update per Code-Docs Sync Rule
- `docs/rules_entry.md` (new) — Document Option A and Option C formulas, window semantics, and fill model. Must be created in the same commit as the code.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `connectors/adjust.py::adjust_ohlc()` — Adjusted OHLCV reader; mandatory for all price/volume reads (Phase 28 decision carried forward).
- `strategies/canslim/` — Phase 29 scorer package; Phase 30 imports it to produce the CANSLIM-qualified universe. Output shape is `(date, ticker, c_pass, ..., liq_pass, score)` — Phase 30 filters on `c_pass & a_pass & n_pass & s_pass & l_pass & i_pass & liq_pass`.
- `models/indicators.py` — Existing moving-average and rolling helpers for VN30/MDM; consider reusing the MA50 helper if it matches adjusted-close semantics.
- `models/mdm_engine.py` (HybridEngine) — Current best VN30 model; provides the market-timing state series that Phase 30 consumes but does not run.

### Established Patterns
- **`state[i-1]` discipline** (memory: equity formula rule) — Phase 30 must never let "today's state decides today's fill". Concretely: the 20-day window check uses the MDM state at bar `t` (signal bar) which was already observable; the fill happens at `open[t+1]`. Unit test should assert no look-ahead.
- **Fail-loud config validation** (Phase 29 D-08) — If EntryConfig thresholds are out of sane ranges, raise at construction, no silent fallback.
- **Markdown + CSV audits, no notebooks** (Phase 28/29) — `docs/audits/phaseNN-*.md` + sibling CSV directory.
- **Dataclass config in `<pkg>/config.py`** — Phase 29 set the precedent; Phase 30 follows.

### Integration Points
- Phase 30 engine signature (expected): `EntryEngine(mdm_state: pd.Series, universe_tickers: list[str], canslim_scores: pd.DataFrame | None, price_loader, config: EntryConfig)`.
- Phase 31 consumes Phase 30's `(date, ticker, detector, fill_price, signal_bar, window_start)` fills table as the entry stream into the portfolio engine.
- A/B report script lives under `scripts/` or `analysis/` (final location decided during planning) and invokes `EntryEngine` twice — once with `canslim_scores=None`, once with the Phase 29 scorer output.

</code_context>

<specifics>
## Specific Ideas

- "Pipeline-realistic vs raw detector performance are both interesting — report side-by-side so we can see how much CANSLIM tightens the funnel." (user, this session)
- Follow the "best model docs rule" from memory: if Phase 30's A/B report surfaces a variant that beats the current best, update `.planning` memory + docs in the same commit — don't force a future session to dig git history.

</specifics>

<deferred>
## Deferred Ideas

- T+2 settlement enforcement, 7% ceiling/floor lock handling → Phase 31 (GATE/PORT requirements)
- Position sizing / Kelly / equal-weight slot allocation → Phase 31
- Exit logic (MDM SELL, 8% stop, MA50 trailing, RS<70) → Phase 31
- Re-entry cooldown after stop → Phase 31
- Costs (commission, tax, slippage) → Phase 31
- Liquidity gate (20d ADV ≥ 10× position size) → Phase 31
- In-sample parameter sweep over EntryConfig thresholds → Phase 32
- Plot dashboards for entry signal density → future UI phase (not yet scheduled)

### Reviewed Todos (not folded)
None — no todos cross-referenced into Phase 30 scope.

</deferred>

---

*Phase: 30-stock-level-entry-confirmation*
*Context gathered: 2026-04-09*
