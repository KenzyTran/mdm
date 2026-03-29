# Phase 12: Indicator Filter Layer - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Stateless IndicatorFilter class with boolean condition methods (5-6 conditions from Phase 9 discovered rules), majority-voting verdict logic returning CONFIRM/VETO/OVERRIDE, and TradingView parity verification. This phase does NOT wire the filter into the hybrid engine pipeline (Phase 13) or validate against 962 signals (Phase 14).

</domain>

<decisions>
## Implementation Decisions

### Filter condition rules
- **D-01:** Source conditions from Phase 9 decision tree discovered rules — evidence-backed from 962 signals, not hardcoded domain knowledge.
- **D-02:** Implement 5-6 boolean condition methods: `close_above_ema55`, `macd_histogram_positive`, `ema9_above_ema21`, `close_above_ma200`, `close_above_ema9`, `macd_above_signal`.
- **D-03:** Default active conditions: only 3 (close_above_ema55, macd_histogram_positive, ema9_above_ema21) — the top-importance features from Phase 9. Remaining conditions implemented but disabled by default, configurable via FilterConfig toggles.
- **D-04:** Max 2-3 active rules enforced to avoid overfitting on 95 post-2019 signals (per STATE.md concern).

### Verdict logic
- **D-05:** Majority voting — count active conditions that agree. >=2/3 (or configurable threshold) of active conditions must agree for CONFIRM, otherwise VETO.
- **D-06:** Verdict logic differs per proposal type: Buy proposals check bullish conditions (EMA stack up, MACD positive). Sell proposals check bearish conditions (inverted). Matches Phase 9 finding that Buy/Sell have different indicator patterns.
- **D-07:** OVERRIDE implemented in Phase 12 (not deferred to Phase 13). When all active indicators strongly contradict the state machine proposal, the filter can suggest an override signal. Verdict enum: CONFIRM, VETO, OVERRIDE.

### TradingView parity verification
- **D-08:** 10+ reference dates with EMA/MACD values exported from TradingView, saved as CSV reference file in `data/reference/` or `tests/fixtures/`.
- **D-09:** Automated unit test reads CSV reference, computes indicators via `core/indicators.py`, compares with tolerance: ±0.01% for EMA/MA values, ±0.1% for MACD values.
- **D-10:** `core/indicators.py` already uses `adjust=False` matching TradingView convention — parity check validates this assumption holds.

### Filter config design
- **D-11:** New `FilterConfig` dataclass with boolean toggles per condition (ema55_enabled=True, macd_enabled=True, ema9_21_enabled=True, ma200_enabled=False, ema9_enabled=False, macd_signal_enabled=False) plus `majority_threshold: float = 0.67`.
- **D-12:** HybridConfig composes FilterConfig via `filter_config: FilterConfig` field, same composition pattern as `v2_config: MDMV2Config`.
- **D-13:** IndicatorFilter class lives in `strategies/mdm_hybrid/indicator_filter.py` — part of hybrid package, not core/.

### Claude's Discretion
- Exact method signatures and parameter naming for condition methods
- How to pass indicator data to IndicatorFilter (DataFrame row vs individual values)
- Internal helper structure for bullish vs bearish condition evaluation
- Test file organization and pytest fixture design
- CSV reference file format and date selection strategy for TradingView parity
- Whether majority_threshold uses fraction (0.67) or count (2 of 3)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Hybrid engine (integration target)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — Two-phase commit placeholder at lines 253-261; filter_enabled flag check at line 253; _snapshot_components/_restore_components for rollback
- `strategies/mdm_hybrid/config.py` — HybridConfig with v2_config composition pattern and filter_enabled=False placeholder (D-07 from Phase 11)

### Indicator computation (input data)
- `core/indicators.py` — compute_ema(), compute_sma(), compute_macd(), build_indicator_dataframe(). Uses adjust=False for TradingView parity. All indicators Phase 12 filter needs are already computed here.
- `core/feature_snapshot.py` — 8 boolean features defined at lines 106-113 (ema9_above_ema21, close_above_ema55, macd_histogram_positive, etc.). Reference pattern for boolean condition definitions.

### Rule discovery findings (condition source)
- `analysis/rule_discovery.py` — BOOLEAN_FEATURES, train_era_tree(), extract_rules(). Feature importances: close_above_ema55=0.687 post-2019, ema9_above_ema21 and macd_histogram_positive as secondary features.

### Signal data
- `data/signals/nasdaq_signals_full.csv` — 962-signal ground truth for future validation (Phase 14)

### Requirements
- `.planning/REQUIREMENTS.md` — HYB-02 (indicator filter layer), HYB-04 (signal override logic)

### Prior phase context
- `.planning/phases/11-foundation-two-phase-commit/11-CONTEXT.md` — D-03 (snapshot/restore pattern), D-06 (composition config), D-07 (Phase 12 adds filter config)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/indicators.py` build_indicator_dataframe(): Computes all indicators (EMA 9/21/55, MA 200, MACD, HA Smoothed) on OHLCV data. IndicatorFilter will consume these computed columns.
- `core/feature_snapshot.py` boolean feature pattern: Lines 106-113 show exact boolean conditions. IndicatorFilter methods should match these definitions for consistency.
- `strategies/mdm_hybrid/config.py` HybridConfig composition pattern: Already composes MDMV2Config — add FilterConfig the same way.
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` two-phase commit: Snapshot/restore at lines 59-73, filter placeholder at 253-261 ready for Phase 13 wiring.

### Established Patterns
- Dataclass configs with `__post_init__` validation (MDMV2Config, HybridConfig)
- Static methods for stateless calculations (Indicators class in mdm_hybrid/indicators.py)
- Boolean features as DataFrame columns (feature_snapshot.py convention)
- Strategy components as separate modules within package (dd_counter, rally_tracker, ftd_detector, position_manager)

### Integration Points
- IndicatorFilter.evaluate(row, proposal, current_state) will be called in hybrid engine's two-phase commit block (line 253-261)
- FilterConfig will be added to HybridConfig alongside existing v2_config and two_phase_enabled/filter_enabled
- core/indicators.py compute functions provide the raw indicator values that IndicatorFilter's boolean methods evaluate
- Phase 13 will wire evaluate() into the propose-filter-decide pipeline

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-indicator-filter-layer*
*Context gathered: 2026-03-29*
