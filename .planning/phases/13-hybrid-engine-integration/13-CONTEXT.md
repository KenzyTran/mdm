# Phase 13: Hybrid Engine Integration - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the full Propose-Filter-Decide pipeline into HybridEngine: state machine proposes via mutation, IndicatorFilter evaluates the diff, engine decides (confirm/veto/override/cash insertion). Output same format as v2. Includes `scripts/run_hybrid_backtest.py` entry point. This phase does NOT tune parameters or validate against 962 signals (Phase 14).

</domain>

<decisions>
## Implementation Decisions

### Propose-Filter-Decide wiring
- **D-01:** Diff-based approach. State machine mutates as normal, then engine compares old_state (from snapshot) vs new_state. If state changed, that's the proposal. Filter evaluates the proposal; if VETO, restore snapshot to rollback.
- **D-02:** On days with no state change, still run filter to check for cash insertion (see D-05). Proposal = "confirm current state".
- **D-03:** Wire into existing two-phase commit block at lines 252-261 of `mdm_hybrid_engine.py`. Minimal refactoring of the mutation flow.

### Override behavior
- **D-04:** OVERRIDE = force Cash. Regardless of what state machine proposed, if filter returns OVERRIDE, engine forces transition to Cash state. No direct Buy->Sell or Sell->Buy overrides.
- **D-05:** Aligns with Dr. K's philosophy from 2012 webinar: "favor cash positions" in uncertain environments. Phase 15 can upgrade override logic if needed.

### Cash insertion logic (HYB-05)
- **D-06:** Use IndicatorFilter itself for degradation detection. Every day the state machine does NOT propose a state change, run filter with proposal = "confirm current state". If filter returns VETO or OVERRIDE, degrade to Cash.
- **D-07:** Cash insertion applies when in BUY state. If in SELL state and filter says VETO/OVERRIDE on "confirm SELL", also degrade to Cash (symmetric).
- **D-08:** No separate degradation logic or threshold — reuse existing majority-vote evaluation from Phase 12.

### Backtest script output
- **D-09:** `scripts/run_hybrid_backtest.py` produces both: (1) detailed CSV signal log with columns `date, old_state, proposed, verdict, final_state, action`, and (2) console summary with performance metrics (win rate, drawdown, trade count).
- **D-10:** Signal log CSV enables Phase 14 diagnosis: "proposed X, filter said Y, final Z" for every trading day.

### Claude's Discretion
- Exact proposal representation passed to IndicatorFilter (string label vs enum)
- How to extract old_state from snapshot vs storing it before mutation
- Console summary format and which metrics to show
- Signal log CSV filename and location convention
- Whether to add verdict/proposal columns to the main results DataFrame or keep them only in the signal log
- How to handle the "always confirm" regression mode (filter_enabled=False should bypass all new logic)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Hybrid engine (modification target)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — Two-phase commit block at lines 252-261 (placeholder for filter wiring); snapshot/restore at lines 59-73, 130-133
- `strategies/mdm_hybrid/config.py` — HybridConfig with `filter_enabled=False` flag and `filter_config: FilterConfig` composition
- `strategies/mdm_hybrid/indicator_filter.py` — IndicatorFilter.evaluate(row, proposal, current_state) -> Verdict; FilterConfig; Verdict enum (CONFIRM/VETO/OVERRIDE)
- `strategies/mdm_hybrid/position_manager.py` — V2PositionManager with enter_buy/exit_to_cash/enter_sell state transitions

### Indicator computation
- `core/indicators.py` — build_indicator_dataframe() computes EMA 9/21/55, MA 200, MACD columns needed by IndicatorFilter

### Prior phase context
- `.planning/phases/11-foundation-two-phase-commit/11-CONTEXT.md` — D-03 (snapshot/restore pattern), D-06 (config composition), D-08/D-09 (regression baseline)
- `.planning/phases/12-indicator-filter-layer/12-CONTEXT.md` — D-05 (evaluate signature), D-06 (bullish vs bearish), D-07 (OVERRIDE verdict)

### V2 reference (regression baseline)
- `strategies/mdm_v2/mdm_v2_engine.py` — Original v2 engine for comparison
- `scripts/run_backtest.py` — Existing v2 backtest script (pattern reference for hybrid backtest)

### Requirements
- `.planning/REQUIREMENTS.md` — HYB-03 (signal confirmation), HYB-04 (signal override), HYB-05 (cash insertion)

### Data
- `data/signals/nasdaq_signals_full.csv` — 962-signal ground truth (Phase 14 will use, but signal log format must be compatible)

### Webinar findings (design rationale)
- `.planning/PROJECT.md` — "Key observations from 2012 VMAP webinar" section: Cash state pre-2019, "favor cash positions", banding concept

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IndicatorFilter.evaluate(row, proposal, current_state)` — Ready to call, returns Verdict enum. Handles bullish vs bearish conditions internally.
- `HybridEngine._snapshot_components()` / `_restore_components()` — Snapshot/restore for all 4 mutable components already working.
- `core/indicators.py` build_indicator_dataframe() — Computes all indicator columns IndicatorFilter needs.
- `scripts/run_backtest.py` — Pattern for backtest entry point (DataLoader, engine.run(), performance output).

### Established Patterns
- DataFrame-centric: engine.run(df) returns DataFrame with signal columns
- Two-phase commit: snapshot before daily processing, decide after
- Strategy packages: self-contained under `strategies/` with own config, engine, tests
- Regression test: hybrid (no filter) vs v2 bit-for-bit match on state/action columns

### Integration Points
- Lines 252-261: placeholder block where filter wiring goes
- `config.filter_enabled`: toggle that activates the filter pipeline
- `core/indicators.py` columns must be present in DataFrame before filter evaluation
- Results DataFrame must keep same columns as v2 for downstream compatibility (signal_comparator, performance analyzer)

</code_context>

<specifics>
## Specific Ideas

- Dr. K 2012 webinar: "In this whipsaw environment, it's very important to favor cash positions. The model takes that into account." — Cash insertion logic (D-06) directly implements this philosophy.
- Cash existed pre-2019 as a state — not a post-2019 invention. The hybrid model should treat Cash as a first-class intermediate state throughout all eras.

</specifics>

<deferred>
## Deferred Ideas

- Contextual transitions (Buy->Cash->Sell depending on prior state) — Phase 15
- Parameter tuning of filter thresholds — Phase 14 after validation baseline
- Leading stocks confirmation as additional filter input — out of scope (no breadth data available)
- "Banding width" / volatility-aware filter activation — Phase 15 advanced features

</deferred>

---

*Phase: 13-hybrid-engine-integration*
*Context gathered: 2026-03-29*
