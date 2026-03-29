# Phase 15: Advanced Features - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance the hybrid MDM engine with four capabilities: (1) contextual state transitions that consider state history, (2) Heikin Ashi Smoothed 55 as additional trend filter, (3) indicator confidence scoring per day, and (4) three-way comparison dashboard. This phase does NOT re-tune filter thresholds or re-validate against 962 signals (that was Phase 14).

</domain>

<decisions>
## Implementation Decisions

### Heikin Ashi filter integration (ADV-02)
- **D-01:** Add HA Smoothed 55 as 7th boolean condition inside existing `IndicatorFilter`, alongside the 6 EMA/MACD conditions. Toggleable via `FilterConfig.ha_smooth_enabled`. Consistent with majority-vote logic.
- **D-02:** Bullish condition: `ha_smooth_close > ha_smooth_open` (green HA candle). Bearish: `ha_smooth_close < ha_smooth_open` (red HA candle). HA Smoothed 55 columns already computed in `core/indicators.py`.

### Confidence score design (ADV-03)
- **D-03:** Simple ratio: `agree_count / total_active_conditions`. Already computed inside `IndicatorFilter.evaluate()` — expose as return value or DataFrame column. Range 0.0-1.0.
- **D-04:** Add `confidence` column to the output DataFrame so it's available for downstream analysis and the comparison dashboard.

### Claude's Discretion

**Contextual transition logic (ADV-01):**
- Duration + sequence approach recommended: track both days-in-state AND prior state sequence
- Where to implement: inside `IndicatorFilter.evaluate()` with added `state_history` parameter, or in `HybridEngine` before filter call — Claude decides based on cleanest integration
- Specific context rules (e.g., Cash > N days triggers, Buy→Cash vs Sell→Cash differentiation) — Claude determines from codebase patterns and Dr. K's webinar insights
- `cash_deterioration_days` already exists in v2 config — reuse or extend as needed

**Dashboard scope & format (ADV-04):**
- Claude decides: static matplotlib script, Jupyter notebook, or both
- Must show pure state machine vs pure decision tree vs hybrid accuracy side-by-side
- Consistent with existing `analysis/` script conventions
- Metrics to include: accuracy, confusion matrices, equity curves, or other relevant comparisons

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Hybrid engine (modification targets)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — HybridEngine with Propose-Filter-Decide pipeline; state snapshots at lines 59-73
- `strategies/mdm_hybrid/indicator_filter.py` — IndicatorFilter.evaluate(row, proposal, current_state) -> Verdict; FilterConfig; 6 existing boolean conditions
- `strategies/mdm_hybrid/config.py` — HybridConfig with MDMV2Config composition, `filter_enabled`, `filter_config: FilterConfig`
- `strategies/mdm_hybrid/position_manager.py` — V2PositionManager with state transitions

### Indicator computation
- `core/indicators.py` — build_indicator_dataframe() computes EMA 9/21/55, MA 200, MACD, AND Heikin Ashi Smoothed 55 (columns: ha_smooth_open/high/low/close)

### Existing analysis scripts (pattern reference)
- `analysis/validate_hybrid.py` — Phase 14 validation script with confusion matrices (pattern for dashboard)
- `analysis/validate_v2.py` — V2 validation pipeline (three-way comparison reference)
- `analysis/validate_discovery.py` — Discovery validation with cross-era comparison
- `analysis/rule_discovery.py` — Decision tree training (pure decision tree model reference for ADV-04)

### Prior phase context
- `.planning/phases/12-indicator-filter-layer/12-CONTEXT.md` — D-02 (stateless conditions), D-04 (max 2-3 conditions), D-07 (Verdict enum)
- `.planning/phases/13-hybrid-engine-integration/13-CONTEXT.md` — D-04 (OVERRIDE=Cash), D-06/D-07 (cash insertion logic)

### Requirements
- `.planning/REQUIREMENTS.md` — ADV-01 through ADV-04

### Webinar findings (design rationale)
- `.planning/PROJECT.md` — "Key observations from 2012 VMAP webinar": Cash state pre-2019, "favor cash positions", banding concept, contextual transitions

### Data
- `data/signals/nasdaq_signals_full.csv` — 962-signal ground truth for comparison dashboard

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IndicatorFilter` with 6 boolean conditions + majority-vote evaluate() — extend with 7th HA condition
- `core/indicators.py` compute_heikin_ashi_smoothed() — HA Smoothed 55 already computed and wired into build_indicator_dataframe()
- `analysis/validate_hybrid.py` — Phase 14 confusion matrix and report generation (reuse for dashboard)
- `analysis/rule_discovery.py` — Decision tree model training (pure DT reference for three-way comparison)
- `MDMV2Config.cash_deterioration_days` — existing duration-based parameter, extendable for contextual transitions

### Established Patterns
- DataFrame-centric: engine.run(df) returns DataFrame with signal columns
- FilterConfig dataclass: per-condition boolean toggles (e.g., `ema9_enabled`, `macd_enabled`)
- Verdict enum: CONFIRM/VETO/OVERRIDE majority-vote logic
- Analysis scripts: standalone Python scripts in `analysis/` producing reports + CSV output

### Integration Points
- `IndicatorFilter.evaluate()` — add HA condition, expose confidence ratio
- `FilterConfig` — add `ha_smooth_enabled: bool = False` toggle
- `HybridEngine._process_day()` — wire state history tracking
- Output DataFrame — add `confidence` column
- New `analysis/compare_models.py` or similar for three-way dashboard

</code_context>

<specifics>
## Specific Ideas

- Dr. K 2012 webinar: "In this whipsaw environment, it's very important to favor cash positions" — contextual transitions should inherit this philosophy
- Cash existed pre-2019 as a state — contextual logic applies across all eras
- Phase 14 showed hybrid post-2019 accuracy 44.4% vs v2 7.1% — contextual awareness may improve this further
- "Banding width" concept from webinar — volatility-aware filtering could be implemented as part of contextual transitions

</specifics>

<deferred>
## Deferred Ideas

- Parameter sweep/tuning of filter thresholds — separate optimization phase
- Leading stocks confirmation as filter input — no breadth data available
- Anti-whipsaw / cooldown logic (FUT-03) — future requirement
- Era-aware evaluation (FUT-01) — future requirement
- VN30 adaptation with recalibrated rules — EXT-04

</deferred>

---

*Phase: 15-advanced-features*
*Context gathered: 2026-03-29*
