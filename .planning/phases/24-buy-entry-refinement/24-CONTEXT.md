# Phase 24: Buy Entry Refinement - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

BUY entries on VN30 are refined with two mechanisms: (1) gap-up buy neutralization invalidates FTD when intraday gap is broken, (2) decline-severity-aware FTD timing allows earlier FTD in shallow pullbacks (< 6%) while requiring classic day-3+ timing for deep corrections (>= 6%). This phase does NOT change SELL logic, stop loss, fail-safe, QE floor, sell acceleration, or buy selectivity behavior.

</domain>

<decisions>
## Implementation Decisions

### Gap-Up Invalidation Scope
- **D-01:** Gap-up filter applies ONLY to classic FTD signals. MA50 breakout and 52-week breakout bypass this filter (consistent with Phase 21 buy_filter scope).
- **D-02:** Gap-up "broken" defined as: signal day's intraday low < previous day's close. No additional conditions (no bearish candle check, no margin/buffer).

### 6% Rally Threshold Logic
- **D-03:** Keep existing correction_threshold = -10% unchanged. The 6% rule is implemented as SEPARATE logic, not by modifying correction_threshold. User confirmed: lowering correction_threshold to -6% previously caused excessive noise.
- **D-04:** Use existing drawdown_pct (computed from rolling_high) for decline measurement. No new calculation needed.
- **D-05:** Rally tracker still requires correction phase (in_correction=True) to be active. The 6% rule does NOT bypass correction detection.
- **D-06:** When drawdown is between -6% and -10% (shallow pullback): engine bypasses rally_tracker's day count requirement and allows FTD check directly (no rally_day >= 4 requirement). When drawdown >= -10% (deep correction): use rally_tracker normally with day 3+ requirement.

### Module Architecture
- **D-07:** Single new module: `strategies/mdm_v2/buy_entry.py` containing a BuyEntryFilter class that handles both gap-up filter and rally threshold logic. Both are buy-entry refinements with simple logic — separate modules would be overkill.

### Config Parameters
- **D-08:** New config fields in MDMV2Config:
  - `gap_filter_enabled: bool = True` — master switch for gap-up invalidation
  - `rally_threshold_enabled: bool = True` — master switch for 6% rally threshold
  - `rally_threshold_pct: float = -0.06` — decline threshold for shallow vs deep pullback FTD timing

### Validation Approach
- **D-09:** Single validation script: `analysis/validate_buy_entry.py` running 3 A/B scenarios: baseline vs +gap_filter vs +rally_threshold vs +both.
- **D-10:** Gap filter success: must identify 3+ historical VN30 instances where filter would have prevented a losing trade, PLUS overall return comparison (ensure no significant return degradation).
- **D-11:** Rally threshold success: verify shallow pullback recoveries captured faster (fewer whipsaw trades) AND deep correction entries still wait for proper follow-through.

### Claude's Discretion
- BuyEntryFilter class internal design (method signatures, state tracking)
- Exact integration point in engine run loop (after existing buy selectivity gates or before)
- Validation script output format and report structure
- Whether to log gap-filter/rally-threshold decisions in results DataFrame columns
- How to identify and report the 3+ historical gap-up instances in validation output

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Buy entry logic (modification targets)
- `strategies/mdm_v2/ftd_signal.py` — FTDSignalDetector with check_ftd(), check_ma50_breakout(), check_52week_breakout()
- `strategies/mdm_v2/mdm_v2_engine.py` — MDMV2Engine.run() lines 148-230, FTD detection, rally tracking, and buy selectivity gates
- `strategies/mdm_v2/rally_attempt.py` — RallyAttemptTracker with correction_threshold and rally day counting
- `strategies/mdm_v2/config.py` — MDMV2Config dataclass with existing enable flags and threshold patterns

### Phase 21 pattern to follow (buy gates)
- `strategies/mdm_v2/buy_filter.py` — BuyFilter module pattern (MA10/MA50 rejection)
- `strategies/mdm_v2/buy_confirmation.py` — BuyConfirmation module pattern (N-day window)
- `.planning/phases/21-buy-selectivity/21-CONTEXT.md` — Architecture decisions for buy gate pattern (D-07, D-08)

### Rule documentation (update targets)
- `docs/rules_mdm_v2.md` — Section III "CASH -> BUY" needs gap-up and rally threshold documentation

### Validation patterns
- `analysis/validate_buy_selectivity.py` — Phase 21 validation script pattern
- `analysis/validate_sell_acceleration.py` — Phase 20 A/B validation pattern

### Requirements
- `.planning/REQUIREMENTS.md` — GAP-01, GAP-02, RALLY-01, RALLY-02, RALLY-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BuyFilter` in `buy_filter.py` — direct template for module structure, config wiring, engine integration
- `BuyConfirmation` in `buy_confirmation.py` — stateful buy gate pattern
- `drawdown_pct` already computed in engine loop (line 166) via `Indicators.drawdown_from_peak()` — reuse for 6% check
- `prev_close` already available in engine loop — reuse for gap-up check
- Engine already has `signal_type` variable distinguishing "FTD" vs "MA50" vs "52WEEK" — use for scope filtering

### Established Patterns
- Config dataclass with enable flags (`buy_filter_enabled`, `sell_acceleration_enabled`) and numeric thresholds
- Engine computes condition, sets `is_ftd=False` if rejected (buy_filter pattern at line 218-222)
- Separate modules per concern, single class per module
- `low` value available in engine loop via `row['low']`

### Integration Points
- Engine run loop: gap-up check goes after FTD detection but before/alongside existing buy selectivity gates
- Rally threshold: modifies the `rally_day >= 4` check at line 170 based on drawdown severity
- Config: new fields in MDMV2Config following existing enable flag pattern
- Validation: new script in `analysis/` following existing validate_*.py pattern

</code_context>

<specifics>
## Specific Ideas

- User previously tried lowering correction_threshold to -6% and experienced excessive signal noise — the 6% rule must be implemented as a SEPARATE bypass mechanism, not by changing the correction threshold
- Dr. K webinar: "NASDAQ must fall >= 6% before requiring classic FTD (day 4+); below 6% FTD can come anytime"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-buy-entry-refinement*
*Context gathered: 2026-03-31*
