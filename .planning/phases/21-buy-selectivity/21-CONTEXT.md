# Phase 21: BUY Selectivity - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

FTD entries are filtered to reject low-quality setups, reducing whipsaw without missing major rallies. Two mechanisms: (1) MA10/MA50 trend filter rejects FTD when trend not confirmed, (2) post-FTD confirmation window requires clean period before committing to BUY. This phase does NOT change SELL logic, stop loss, QE floor, or sell acceleration behavior.

</domain>

<decisions>
## Implementation Decisions

### FTD Rejection Criteria
- **D-01:** MA10 < MA50 rejection filter applies ONLY to classic FTD signals. MA50 breakout and 52-week breakout bypass this filter (they inherently confirm strong trend).
- **D-02:** No additional rejection conditions beyond MA10 < MA50. Combined with confirmation window (D-03 to D-06), this is sufficient to filter whipsaw.

### Confirmation Window
- **D-03:** Post-FTD confirmation window is 3 trading days. During this window, state remains CASH (no position taken).
- **D-04:** FTD is canceled when 2 or more Distribution Days occur within the 3-day window. A single DD is tolerated.
- **D-05:** If window passes cleanly (0-1 DD), BUY entry is confirmed at the close price of the confirmation day (day 3), NOT the original FTD price.
- **D-06:** Confirmation window applies only to classic FTD signals (same scope as D-01). MA50 breakout and 52-week breakout enter BUY immediately.

### Gate Architecture
- **D-07:** Two separate modules in `strategies/mdm_v2/`: `buy_filter.py` for MA10/MA50 rejection logic, `buy_confirmation.py` for N-day window tracking.
- **D-08:** Engine-side filtering: engine calls filter/confirmation checks BEFORE passing `is_ftd` to `position_manager.process_day()`. If rejected or pending confirmation, `is_ftd=False`. Follows the same pattern as `suppress_sell` / `acceleration_met`.

### Validation Approach
- **D-09:** Walk-forward validation with pre-2020 train / 2020-2026 test split. Degradation must be < 10% out-of-sample vs in-sample (per roadmap success criteria).
- **D-10:** Primary metrics: trade count reduction (target 15-40%) and win rate improvement. Whipsaw reduction measured by fewer trades + higher win rate.
- **D-11:** A/B validation script runs on both NASDAQ and VN30, following Phase 20's `validate_sell_acceleration.py` pattern.

### Config & Parameters
- **D-12:** New config fields in MDMV2Config: `buy_filter_enabled` (default True), `buy_confirmation_enabled` (default True), `confirmation_window_days` (default 3), `confirmation_max_dd` (default 1 — cancel if DD count > this value).
- **D-13:** Same defaults for NASDAQ and VN30 initially. Per-market tuning deferred to Phase 22 integration.

### Claude's Discretion
- Exact class/method naming for buy_filter.py and buy_confirmation.py
- Internal state tracking for confirmation window (counter, DD accumulator)
- Validation script output format and report structure
- Whether to log filter/confirmation decisions in results DataFrame columns
- How engine tracks confirmation window state across days (internal instance variable vs DataFrame column)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### BUY entry logic (modification targets)
- `strategies/mdm_v2/ftd_signal.py` — FTDSignalDetector with check_ftd(), check_ma50_breakout(), check_52week_breakout() — the 3 buy signal types
- `strategies/mdm_v2/mdm_v2_engine.py` — MDMV2Engine.run() lines 143-187, FTD detection and is_ftd flag logic
- `strategies/mdm_v2/position_manager.py` — V2PositionManager.process_day() lines 175-182, CASH->BUY transition on is_ftd
- `strategies/mdm_v2/config.py` — MDMV2Config dataclass, existing enable flags and threshold patterns

### Phase 20 pattern to follow
- `strategies/mdm_v2/sell_acceleration.py` — SellAccelerationGate module pattern (separate class, engine-wired)
- `.planning/phases/20-sell-acceleration/20-CONTEXT.md` — Architecture decisions for gate pattern

### Rule documentation (update targets)
- `docs/rules_mdm_v2.md` — Section III "CASH -> BUY" needs buy selectivity filter documentation

### Validation patterns
- `analysis/validate_v2.py` — Existing A/B comparison script pattern
- `analysis/validate_sell_acceleration.py` — Phase 20 bear market validation script pattern

### Requirements
- `.planning/REQUIREMENTS.md` — BUY-01 (MA10 < MA50 rejection), BUY-02 (post-FTD confirmation window)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SellAccelerationGate` in `sell_acceleration.py` — direct template for module structure, config wiring, and engine integration
- `suppress_sell` / `acceleration_met` parameter pattern in `position_manager.process_day()` — proven pattern for gate booleans
- `FTDSignalDetector` — already separates FTD, MA50 breakout, and 52-week breakout into distinct methods (easy to filter selectively)
- `DistributionDayCounter` — already tracks DD counts, can be queried during confirmation window

### Established Patterns
- Config dataclass with enable flags (`sell_acceleration_enabled`, `ma50_sell_enabled`) and numeric thresholds
- Engine computes condition, passes boolean to position_manager (suppress_sell pattern)
- Separate modules per concern (`sell_acceleration.py`, `liquidity.py`, `stop_loss.py`)
- MA10 and MA50 already computed in indicators and available in engine's DataFrame (`ma10`, `ma50` columns)

### Integration Points
- Engine run loop: buy filter check goes after FTD detection (line ~156) but before passing is_ftd to position_manager
- Confirmation window requires engine to track state across multiple days (new stateful component)
- Config: new fields in MDMV2Config dataclass with enable flags
- Validation script follows existing `analysis/validate_*.py` pattern

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

*Phase: 21-buy-selectivity*
*Context gathered: 2026-03-31*
