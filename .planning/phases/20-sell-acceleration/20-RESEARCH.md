# Phase 20: SELL Acceleration - Research

**Researched:** 2026-03-31
**Domain:** Trading signal gating / momentum confirmation for SELL transitions
**Confidence:** HIGH

## Summary

Phase 20 adds an acceleration gate to the CASH->SELL transition in the MDM V2 engine. Currently, SELL triggers on MA50 breakdown or cash deterioration alone. This phase gates those triggers so SELL only fires when at least one downside momentum condition is confirmed: price ROC below threshold, DD clustering above threshold, or volume-confirmed MA50 breakdown.

The implementation follows the exact same architectural pattern as Phase 19's QE floor `suppress_sell` -- a separate module computes a boolean condition, the engine passes it to `position_manager.process_day()`. The key difference: QE floor suppresses SELL when ON; acceleration gate suppresses SELL when acceleration is NOT met. Both are AND conditions on the SELL transition.

**Primary recommendation:** Create `sell_acceleration.py` with `SellAccelerationGate` class, add `acceleration_met` parameter to `process_day()`, wire through engine identical to `suppress_sell` pattern. Bear market validation script follows `analysis/validate_v2.py` pattern but compares V2 baseline vs V2+sell_acceleration on 2008 and 2022 sub-periods.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Acceleration gate on existing triggers -- MA50 breakdown and cash deterioration remain the primary SELL triggers, but only fire when at least 1 acceleration condition is met (OR logic between acceleration conditions).
- **D-02:** Three acceleration conditions (any 1 sufficient): Price ROC below threshold, DD clustering, Volume-confirmed MA50 breakdown.
- **D-03:** Gate applies to BOTH MA50 breakdown AND cash deterioration triggers.
- **D-04:** Separate module `sell_acceleration.py` in `strategies/mdm_v2/` containing `SellAccelerationGate` class.
- **D-05:** Engine calls `SellAccelerationGate.check()` each session, receives boolean `acceleration_met`. Passes as parameter to `position_manager.process_day()` (same pattern as QE floor `suppress_sell`).
- **D-06:** A/B comparison script: V2 baseline vs V2+sell_acceleration on bear market sub-periods (2008, 2022). Following existing `analysis/validate_v2.py` pattern.
- **D-07:** Script runs on both NASDAQ (2008 + 2022 data) and VN30 (2022 data). Outputs signal dates, delay measurement, drawdown, and total return comparison.
- **D-08:** Success criteria thresholds: SELL delay <= 5 trading days (2008), max drawdown not worse than baseline (2022).
- **D-09:** New config fields in MDMV2Config: `sell_acceleration_enabled` (default True), `roc_threshold`, `roc_window`, `dd_cluster_count`, `dd_cluster_window`. Easy A/B toggle via enable flag.
- **D-10:** Same defaults for NASDAQ and VN30 initially.

### Claude's Discretion
- Exact default values for ROC threshold, ROC window, DD cluster count/window (informed by backtest results)
- Volume confirmation logic details (e.g., volume > prev_volume vs volume > MA50_volume)
- Script file naming and output format details
- Whether to log acceleration gate decisions in results DataFrame columns

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SELL-01 | SELL transition requires downside acceleration condition (price ROC or DD clustering), not just MA50 breakdown or cash deterioration alone | Architecture pattern (suppress_sell), SellAccelerationGate module design, config fields, integration points in engine and position_manager |
| SELL-02 | Mandatory bear-market sub-period validation (2008, 2022) -- SELL changes must not degrade performance during confirmed bear markets | Validation script pattern (validate_v2.py), data availability (NASDAQ.csv covers 2008+2022, vn30.csv covers 2022), delay measurement approach |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | ROC computation, DD clustering window, data slicing for bear market periods | Already used throughout project |
| numpy | >= 1.24.0 | Numerical comparisons for acceleration conditions | Already used throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| matplotlib | >= 3.7.0 | A/B comparison charts in validation script | Bear market validation output |

**No new dependencies required.** All computation uses pandas/numpy already in the project.

## Architecture Patterns

### Recommended Project Structure
```
strategies/mdm_v2/
    sell_acceleration.py       # NEW: SellAccelerationGate class
    config.py                  # MODIFY: add acceleration config fields
    position_manager.py        # MODIFY: add acceleration_met parameter
    mdm_v2_engine.py           # MODIFY: instantiate gate, compute, pass to PM
analysis/
    validate_sell_acceleration.py  # NEW: A/B bear market validation script
docs/
    rules_mdm_v2.md            # MODIFY: Section III.5 and VII state diagram
```

### Pattern 1: Boolean Gate (Same as suppress_sell)
**What:** A separate module computes a boolean, engine passes it to position_manager
**When to use:** Any time a transition needs conditional gating
**Example:**
```python
# In sell_acceleration.py
class SellAccelerationGate:
    def __init__(self, config: MDMV2Config):
        self.config = config

    def check(
        self,
        close: float,
        closes_history: list,  # or pd.Series for ROC
        dd_dates: list,        # recent DD dates for clustering
        date: pd.Timestamp,
        volume: float,
        prev_volume: float,
        ma50: float,
        prev_close: float,
        prev_ma50: float,
    ) -> bool:
        """Return True if at least one acceleration condition is met."""
        if not self.config.sell_acceleration_enabled:
            return True  # When disabled, always allow SELL (backward compat)

        # Condition 1: Price ROC below threshold
        roc_met = self._check_price_roc(close, closes_history)

        # Condition 2: DD clustering
        dd_cluster_met = self._check_dd_clustering(dd_dates, date)

        # Condition 3: Volume-confirmed MA50 breakdown
        vol_ma50_met = self._check_volume_ma50_breakdown(
            close, ma50, prev_close, prev_ma50, volume, prev_volume
        )

        return roc_met or dd_cluster_met or vol_ma50_met
```

```python
# In mdm_v2_engine.py run loop (after QE floor, before process_day)
# 4c. Compute sell acceleration gate
acceleration_met = True  # default: allow SELL
if self.config.sell_acceleration_enabled:
    acceleration_met = self.sell_acceleration_gate.check(
        close=close,
        closes_history=df['close'].iloc[max(0, idx - self.config.roc_window):idx + 1],
        dd_dates=self.dd_counter.dd_history,
        date=date,
        volume=row['volume'],
        prev_volume=row['prev_volume'],
        ma50=ma50_val,
        prev_close=prev_close,
        prev_ma50=prev_ma50_val,
    )

# 5. Update position (pass both suppress_sell AND acceleration_met)
new_state, action = self.position_manager.process_day(
    ...,
    suppress_sell=suppress_sell,
    acceleration_met=acceleration_met,
)
```

```python
# In position_manager.py process_day(), CASH state block
# SELL only fires when: trigger condition met AND acceleration_met AND NOT suppress_sell
elif self.config.ma50_sell_enabled and ma50 is not None and close < ma50:
    if suppress_sell:
        action = "SELL suppressed: QE floor (MA50 breakdown)"
    elif not acceleration_met:
        action = "SELL deferred: no acceleration (MA50 breakdown)"
    else:
        self.enter_sell(date, f"MA50 breakdown (close {close:.2f} < MA50 {ma50:.2f})")
        action = "SELL signal: MA50 breakdown"
```

### Pattern 2: Acceleration Condition Implementation Details
**What:** The three specific conditions and their data requirements

**Price ROC:**
```python
def _check_price_roc(self, close: float, closes_history) -> bool:
    """Check if price rate-of-change is below threshold (bearish momentum)."""
    if len(closes_history) < self.config.roc_window + 1:
        return False
    past_close = closes_history.iloc[-(self.config.roc_window + 1)]
    roc = (close - past_close) / past_close
    return roc < self.config.roc_threshold
```

**DD Clustering:**
```python
def _check_dd_clustering(self, dd_dates: list, current_date: pd.Timestamp) -> bool:
    """Check if enough DDs occurred within recent window."""
    if not dd_dates:
        return False
    window_start = current_date - pd.Timedelta(days=self.config.dd_cluster_window * 1.5)
    # Use trading days from dd_history
    recent_dds = [d for d in dd_dates if d >= window_start]
    return len(recent_dds) >= self.config.dd_cluster_count
```

**Volume-Confirmed MA50 Breakdown:**
```python
def _check_volume_ma50_breakdown(
    self, close, ma50, prev_close, prev_ma50, volume, prev_volume
) -> bool:
    """MA50 breakdown with volume confirmation."""
    if ma50 is None or prev_ma50 is None:
        return False
    breakdown = close < ma50 and prev_close >= prev_ma50
    volume_confirmed = volume > prev_volume
    return breakdown and volume_confirmed
```

### Pattern 3: Config Integration
**What:** New fields follow existing pattern (enable flag + numeric thresholds)
```python
# In MDMV2Config dataclass, add after qe_floor fields:

# SELL Acceleration (v5.0, SELL-01)
sell_acceleration_enabled: bool = True     # Master switch
roc_threshold: float = -0.04              # ROC must be below -4%
roc_window: int = 10                      # 10-day lookback for ROC
dd_cluster_count: int = 3                 # 3 DDs required
dd_cluster_window: int = 5               # within 5 sessions
```

### Recommended Default Values (Claude's Discretion)
**Confidence: MEDIUM** -- These are starting points based on domain reasoning, to be validated by backtest.

| Parameter | Recommended Default | Rationale |
|-----------|-------------------|-----------|
| `roc_threshold` | -0.04 (-4%) | ~2 standard deviations of 10-day NASDAQ returns. Below this = significant bearish momentum. |
| `roc_window` | 10 | Two trading weeks. Short enough to be responsive, long enough to filter noise. |
| `dd_cluster_count` | 3 | 3 DDs in a short window signals institutional distribution. Lower than the 5-DD BUY->CASH threshold. |
| `dd_cluster_window` | 5 | 5 trading sessions (1 week). Tight clustering = aggressive selling. |

**Volume confirmation:** Use `volume > prev_volume` (simple comparison). This matches the existing volume_up pattern used throughout the codebase. Using MA50_volume would require passing additional data and adds complexity without proven benefit.

### Anti-Patterns to Avoid
- **Look-ahead in ROC:** ROC must use `closes_history[:idx+1]` (inclusive of current day, not future). The closes_history slice in engine must be `df['close'].iloc[max(0, idx - roc_window):idx + 1]`.
- **DD clustering counting BUY-state DDs when in CASH:** The dd_counter only counts DDs during BUY state. When checking clustering in CASH state, use the dd_history from the PREVIOUS BUY period. This is already the behavior since `dd_counter.dd_history` persists across state changes (only reset on FTD).
- **Modifying suppress_sell semantics:** The `acceleration_met` parameter must be SEPARATE from `suppress_sell`. They serve different purposes: QE floor prevents SELL entirely; acceleration gate defers SELL until momentum is confirmed. Do NOT merge them into one boolean.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ROC computation | Custom loop over prices | `(close - closes_history.iloc[-N-1]) / closes_history.iloc[-N-1]` | One-liner with pandas, no loop needed |
| Date windowing for DD clustering | Manual date arithmetic | `pd.Timedelta` + list comprehension | Handles weekends/holidays via actual DD dates |
| Bear market sub-period slicing | Manual index slicing | `df[(df['date'] >= start) & (df['date'] <= end)]` | Standard pandas pattern used in validate_v2.py |

## Common Pitfalls

### Pitfall 1: Acceleration Gate Disabled Means SELL Always Allowed
**What goes wrong:** If `sell_acceleration_enabled=False` and `check()` returns False, all SELLs are blocked.
**Why it happens:** Forgetting to handle the disabled case.
**How to avoid:** When disabled, `check()` MUST return True (allow all SELLs), preserving V2 baseline behavior.
**Warning signs:** Setting `sell_acceleration_enabled=False` produces zero SELL signals.

### Pitfall 2: DD History is Shared Between States
**What goes wrong:** DD clustering check finds no DDs because counter was reset on FTD.
**Why it happens:** `dd_counter.reset()` clears `dd_history` when FTD triggers BUY. If the market then exits BUY quickly to CASH, dd_history is empty.
**How to avoid:** The DD clustering condition is most useful as a confirmation of MA50 breakdown. DDs from the preceding BUY period should still be in dd_history since reset only happens on FTD (which triggers BUY, not CASH). When transitioning BUY->CASH->checking SELL: the DD history from the BUY period is still available. This is correct behavior.
**Warning signs:** DD clustering never triggers. Verify dd_history is not prematurely cleared.

### Pitfall 3: Volume-Confirmed MA50 Breakdown Overlaps with Primary Trigger
**What goes wrong:** The MA50 breakdown trigger (close < ma50) AND the volume-confirmed MA50 breakdown acceleration condition fire simultaneously, making the acceleration gate always pass when MA50 breakdown triggers.
**Why it happens:** Volume-confirmed MA50 breakdown IS a subset of MA50 breakdown (it adds volume requirement). So when a volume-confirmed breakdown occurs, the MA50 trigger fires AND the acceleration gate passes.
**How to avoid:** This is actually CORRECT behavior -- a volume-confirmed breakdown is a genuine acceleration signal. The gate adds value when MA50 breakdown happens WITHOUT volume (gate blocks) or when cash deterioration triggers (gate requires separate confirmation).
**Warning signs:** None -- this is expected behavior. Document it clearly.

### Pitfall 4: SELL Delay Measurement in 2008 Validation
**What goes wrong:** Measuring delay from V2 baseline's first SELL date but V2+acceleration's first SELL is a different signal entirely.
**Why it happens:** The gate may defer one SELL but then a different trigger fires the actual SELL.
**How to avoid:** Compare the first CASH->SELL transition date in both runs. The delay is simply: `acceleration_sell_date - baseline_sell_date` in trading days. If acceleration fires BEFORE baseline (due to different DD clustering path), delay is negative (acceptable).
**Warning signs:** Delay > 5 trading days in 2008 sub-period.

### Pitfall 5: Hybrid Engine Not Updated
**What goes wrong:** V2 engine works with acceleration gate but hybrid engine has no `suppress_sell` OR `acceleration_met` parameter.
**Why it happens:** Hybrid position_manager.process_day() has a DIFFERENT signature -- it lacks `suppress_sell` entirely (Phase 19 QE floor was not integrated into hybrid).
**How to avoid:** For this phase, focus on V2 engine only (per CONTEXT.md D-04: module in `strategies/mdm_v2/`). Hybrid integration is deferred -- document as open question. The validation script uses V2 engine only.
**Warning signs:** Hybrid backtest shows different behavior from V2.

### Pitfall 6: State[i-1] Bug in Validation Script Equity Calculation
**What goes wrong:** Equity calculation uses state[i] instead of state[i-1], creating look-ahead bias.
**Why it happens:** Known project pitfall (documented in CLAUDE.md and STATE.md -- 707% vs 93% bug).
**How to avoid:** Always use `state[i-1]` for equity calculation. Copy equity computation from existing `V2PerformanceAnalyzer`, do NOT hand-roll.
**Warning signs:** Unrealistically high returns in validation results.

## Code Examples

### Engine Integration (following QE floor pattern exactly)
```python
# In MDMV2Engine.__init__, after liquidity_loader:
self.sell_acceleration_gate = None
if self.config.sell_acceleration_enabled:
    from .sell_acceleration import SellAccelerationGate
    self.sell_acceleration_gate = SellAccelerationGate(self.config)

# In MDMV2Engine.run() loop, after step 4b (QE floor), before step 5:
# 4c. Compute sell acceleration gate (SELL-01)
acceleration_met = True  # default: always allow
if self.config.sell_acceleration_enabled and self.sell_acceleration_gate is not None:
    acceleration_met = self.sell_acceleration_gate.check(...)
```

### Validation Script Structure (following validate_v2.py pattern)
```python
"""
SELL Acceleration Bear Market Validation

A/B comparison: V2 baseline vs V2+sell_acceleration on bear market sub-periods.
Validates SELL-01 and SELL-02 requirements.

Usage:
    uv run python analysis/validate_sell_acceleration.py
"""

# Bear market sub-periods
BEAR_PERIODS = {
    'nasdaq_2008': ('2007-10-01', '2009-03-31'),
    'nasdaq_2022': ('2021-11-01', '2023-01-31'),
    'vn30_2022': ('2022-01-01', '2022-12-31'),
}

# For each period:
# 1. Run V2 baseline (sell_acceleration_enabled=False)
# 2. Run V2 + acceleration (sell_acceleration_enabled=True)
# 3. Compare: first SELL date, total SELL count, max drawdown, total return
# 4. Output delay measurement and pass/fail against thresholds
```

### Position Manager Update Pattern
```python
# Add acceleration_met parameter with default True for backward compatibility
def process_day(
    self,
    ...,
    suppress_sell: bool = False,
    acceleration_met: bool = True,   # NEW: default True = allow SELL
) -> Tuple[V2MarketState, str]:
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SELL on MA50 breakdown alone | SELL requires acceleration confirmation | Phase 20 (this phase) | Prevents premature SELL during normal pullbacks |
| Single suppress_sell gate | Two independent gates (suppress_sell + acceleration_met) | Phase 20 | Gates compose via AND logic: both must allow SELL |

## Open Questions

1. **Hybrid engine integration**
   - What we know: Hybrid position_manager lacks `suppress_sell` parameter (Phase 19 was V2-only for QE floor). It also lacks `acceleration_met`.
   - What's unclear: Whether hybrid should get both gates in this phase or later.
   - Recommendation: V2-only for this phase (per CONTEXT.md D-04). Hybrid integration in Phase 22 (integration phase).

2. **Optimal default parameter values**
   - What we know: ROC -4%/10-day and DD 3/5-session are reasonable starting points.
   - What's unclear: Whether these work well on both NASDAQ and VN30.
   - Recommendation: Run backtest with these defaults, tune if needed. D-10 says same defaults initially.

3. **DD history availability when entering CASH**
   - What we know: `dd_counter.dd_history` persists across BUY->CASH transition (only reset on FTD).
   - What's unclear: Edge case where very quick BUY->CASH transition leaves minimal DD history.
   - Recommendation: This is fine -- if there are few DDs, the clustering condition simply won't trigger, and ROC or volume-confirmed breakdown would need to confirm instead.

4. **Logging acceleration gate decisions**
   - What we know: CONTEXT.md lists this as Claude's discretion.
   - Recommendation: YES -- add `acceleration_met` column to results DataFrame. Costs nothing, invaluable for debugging. Also log which specific condition(s) were met in the action string.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual backtest validation (no pytest in project) |
| Config file | None -- project uses script-based validation |
| Quick run command | `uv run python analysis/validate_sell_acceleration.py` |
| Full suite command | Same as quick run |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SELL-01 | SELL only fires with acceleration condition met | integration | `uv run python analysis/validate_sell_acceleration.py` | Wave 0 |
| SELL-02 | Bear market validation (2008 delay <= 5 days, 2022 drawdown not worse) | integration | Same script, checks thresholds | Wave 0 |

### Sampling Rate
- **Per task commit:** Manual smoke test: run engine with acceleration enabled, verify SELL signals change
- **Per wave merge:** `uv run python analysis/validate_sell_acceleration.py`
- **Phase gate:** Full validation script green (delay and drawdown thresholds pass)

### Wave 0 Gaps
- [ ] `analysis/validate_sell_acceleration.py` -- covers SELL-01, SELL-02
- [ ] `strategies/mdm_v2/sell_acceleration.py` -- the module itself (tested implicitly by validation script)

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_v2/position_manager.py` -- current SELL transition logic (lines 182-194), suppress_sell pattern
- `strategies/mdm_v2/mdm_v2_engine.py` -- QE floor integration pattern (lines 208-232)
- `strategies/mdm_v2/config.py` -- MDMV2Config dataclass structure
- `strategies/mdm_v2/liquidity.py` -- Phase 19 module pattern to follow
- `analysis/validate_v2.py` -- A/B comparison script pattern
- `docs/rules_mdm_v2.md` -- Current SELL rules (Section III.5, VII)

### Secondary (MEDIUM confidence)
- Default parameter recommendations (ROC -4%/10-day, DD 3/5) -- domain reasoning, not empirically validated yet

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, purely internal project code
- Architecture: HIGH - follows exact existing pattern (suppress_sell from Phase 19)
- Pitfalls: HIGH - identified from direct code reading and project history
- Default parameters: MEDIUM - reasonable starting points but need backtest validation

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable -- internal project, no external dependencies changing)
