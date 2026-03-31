# Phase 20: SELL Acceleration - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

SELL transitions require confirmed downside momentum/acceleration before firing. Currently CASH->SELL triggers on MA50 breakdown or cash deterioration alone -- this phase adds an acceleration gate so SELL only fires when genuine bearish momentum is present. Validated on 2008 and 2022 bear market sub-periods. This phase does NOT change BUY logic, stop loss, or QE floor behavior.

</domain>

<decisions>
## Implementation Decisions

### Acceleration Conditions
- **D-01:** Acceleration gate on existing triggers -- MA50 breakdown and cash deterioration remain the primary SELL triggers, but only fire when at least 1 acceleration condition is met (OR logic between acceleration conditions).
- **D-02:** Three acceleration conditions (any 1 sufficient):
  - Price ROC below threshold (e.g., ROC over N days < -X%)
  - DD clustering (e.g., 3 DDs within 5 sessions)
  - Volume-confirmed MA50 breakdown (MA50 breakdown + volume increase)
- **D-03:** Gate applies to BOTH MA50 breakdown AND cash deterioration triggers. No SELL without confirmed momentum regardless of trigger type.

### Gate Architecture
- **D-04:** Separate module `sell_acceleration.py` in `strategies/mdm_v2/` containing `SellAccelerationGate` class.
- **D-05:** Engine calls `SellAccelerationGate.check()` each session, receives boolean `acceleration_met`. Passes as parameter to `position_manager.process_day()` (same pattern as QE floor `suppress_sell`).

### Bear Market Validation
- **D-06:** A/B comparison script: V2 baseline vs V2+sell_acceleration on bear market sub-periods (2008, 2022). Following existing `analysis/validate_v2.py` pattern.
- **D-07:** Script runs on both NASDAQ (2008 + 2022 data) and VN30 (2022 data). Outputs signal dates, delay measurement, drawdown, and total return comparison.
- **D-08:** Success criteria thresholds: SELL delay <= 5 trading days (2008), max drawdown not worse than baseline (2022).

### Config & Parameters
- **D-09:** New config fields in MDMV2Config: `sell_acceleration_enabled` (default True), `roc_threshold`, `roc_window`, `dd_cluster_count`, `dd_cluster_window`. Easy A/B toggle via enable flag.
- **D-10:** Same defaults for NASDAQ and VN30 initially. Tune per-market presets after backtest results if needed.

### Claude's Discretion
- Exact default values for ROC threshold, ROC window, DD cluster count/window (informed by backtest results)
- Volume confirmation logic details (e.g., volume > prev_volume vs volume > MA50_volume)
- Script file naming and output format details
- Whether to log acceleration gate decisions in results DataFrame columns

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### SELL transition logic (modification targets)
- `strategies/mdm_v2/position_manager.py` -- V2PositionManager.process_day() lines 182-194, current CASH->SELL logic with MA50 breakdown and cash deterioration
- `strategies/mdm_v2/mdm_v2_engine.py` -- MDMV2Engine.run() lines 208-232, QE floor suppress_sell pattern to follow for acceleration gate
- `strategies/mdm_v2/config.py` -- MDMV2Config dataclass, ma50_sell_enabled and cash_deterioration_days fields

### Rule documentation (update targets)
- `docs/rules_mdm_v2.md` -- Section III.5 "CASH -> SELL" and Section VII state diagram need acceleration gate documentation

### Validation patterns
- `analysis/validate_v2.py` -- Existing A/B comparison script pattern to follow

### Requirements
- `.planning/REQUIREMENTS.md` -- SELL-01 (acceleration condition), SELL-02 (bear market validation)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `suppress_sell` parameter pattern in position_manager.process_day() -- same approach for `acceleration_met` parameter
- QE floor integration in engine (lines 208-213) -- template for how acceleration gate wires in
- `analysis/validate_v2.py` -- existing A/B comparison script, reuse pattern for bear market validation

### Established Patterns
- Config dataclass with enable flags and numeric thresholds (MDMV2Config)
- Engine computes condition, passes boolean to position_manager (suppress_sell pattern)
- Separate modules for distinct concerns (liquidity.py, stop_loss.py)

### Integration Points
- Engine run loop: acceleration check goes between indicator computation and position_manager.process_day()
- Position manager: new `acceleration_met` parameter alongside existing `suppress_sell`
- Config: new fields in MDMV2Config dataclass
- Hybrid engine may need same integration (strategies/mdm_hybrid/)

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 20-sell-acceleration*
*Context gathered: 2026-03-31*
