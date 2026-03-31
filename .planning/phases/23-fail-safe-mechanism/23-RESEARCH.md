# Phase 23: Fail-Safe Mechanism - Research

**Researched:** 2026-03-31
**Domain:** Trading strategy state machine extension (SELL->CASH fail-safe transition)
**Confidence:** HIGH

## Summary

The fail-safe mechanism is a specific Dr. K rule documented in VOSI FAQ findings: when the model issues a SELL signal that turns out to be false, it auto-exits to CASH when the index reclaims the HIGH of the "standby-sell day" (the day immediately before the sell signal day). This is a well-defined, narrow state machine extension that adds one new transition path (SELL->CASH via fail-safe) and one new piece of engine state (fail-safe threshold price).

The implementation touches three areas: (1) recording the standby-sell day HIGH when entering SELL state, (2) checking the fail-safe condition each day while in SELL state, and (3) A/B backtesting to validate the mechanism reduces false signal losses on VN30 without triggering during genuine bear markets. The existing codebase has clear patterns for all three from prior phases (sell acceleration, QE floor, buy selectivity).

**Primary recommendation:** Add `fail_safe_enabled` config flag (default True), store `fail_safe_threshold` in V2Position, check threshold in SELL state processing block of `process_day()`, and validate with A/B backtest using the established `validate_*.py` pattern.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAFE-01 | Record HIGH of standby-sell day as fail-safe threshold when V2 transitions to SELL | V2Position dataclass gets `fail_safe_threshold` field; `enter_sell()` accepts threshold param; engine passes `prev_high` from DataFrame |
| SAFE-02 | Auto-exit SELL to CASH when VN30 close exceeds fail-safe threshold | New SELL state processing block in `process_day()` checks `close > fail_safe_threshold`; creates trade record with "fail-safe triggered" annotation |
| SAFE-03 | A/B backtest confirms fail-safe reduces false signal loss on VN30 | Follow `validate_sell_acceleration.py` pattern: run V2 baseline vs V2+fail_safe, compare false SELL trade losses |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.10+, pandas >= 2.0, numpy >= 1.24, matplotlib >= 3.7
- snake_case for functions/variables, PascalCase for classes
- Config via dataclass with `__post_init__` validation
- New features default OFF for backward compatibility (v5.0 decision) -- but fail-safe is a v6.0 feature, should default True per this phase's purpose
- Code-Docs Sync Rule: update `docs/rules_mdm_v2.md` when modifying strategy logic
- State[i-1] not state[i] bug pattern: use previous day's state for return capture, never current day
- All work through GSD workflow

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, time series | Already in use throughout engine |
| numpy | >= 1.24.0 | Numerical calculations | Already in use for indicators |
| matplotlib | >= 3.7.0 | A/B comparison charts | Already used in validate_*.py scripts |
| pytest | >= 9.0.2 | Unit tests for fail-safe logic | Already configured in pyproject.toml |

### Supporting
No new libraries needed. This is a pure logic extension of existing engine code.

## Architecture Patterns

### Where Changes Go

```
strategies/mdm_v2/
  config.py              # Add fail_safe_enabled flag
  position_manager.py    # Add fail_safe_threshold to V2Position, SELL->CASH transition
  mdm_v2_engine.py       # Pass prev_high to position_manager on SELL entry
analysis/
  validate_fail_safe.py  # A/B backtest script (new file)
tests/
  test_fail_safe.py      # Unit tests (new file)
docs/
  rules_mdm_v2.md        # Update with fail-safe rules section
```

### Pattern 1: Config Flag with Default

**What:** Add config parameter following exact pattern of existing features
**When to use:** All new feature additions
**Example:**
```python
# In config.py - MDMV2Config dataclass
fail_safe_enabled: bool = True    # Auto-exit SELL when close > standby-sell HIGH (SAFE-01)
```

Note: Unlike v5.0 features which default OFF, fail-safe defaults ON because it is a protective mechanism that reduces risk. The user can still disable it via config.

### Pattern 2: V2Position State Extension

**What:** Add threshold field to V2Position dataclass
**Example:**
```python
@dataclass
class V2Position:
    state: V2MarketState = V2MarketState.CASH
    buy_price: float = 0.0
    buy_date: Optional[pd.Timestamp] = None
    buy_day_low: float = 0.0
    signal_type: str = "FTD"
    days_in_cash: int = 0
    ma10_below_count: int = 0
    fail_safe_threshold: float = 0.0  # HIGH of standby-sell day (SAFE-01)
```

### Pattern 3: SELL State Processing Block

**What:** Add fail-safe check in the SELL state branch of `process_day()`
**Current code** (position_manager.py line 223-227):
```python
elif current_state == V2MarketState.SELL:
    # SELL is persistent -- only FTD can transition to BUY
    if is_ftd:
        self.enter_buy(ftd_price, date, low, signal_type)
        action = f"BUY at {ftd_price:.2f} ({signal_type}) from SELL"
```
**After fail-safe** -- check fail-safe BEFORE FTD (fail-safe exits to CASH, not directly to BUY):
```python
elif current_state == V2MarketState.SELL:
    # Check fail-safe first: close > standby-sell HIGH -> exit to CASH
    if (self.config.fail_safe_enabled
        and self.position.fail_safe_threshold > 0
        and close > self.position.fail_safe_threshold):
        self._fail_safe_exit(date, close)
        action = f"CASH: fail-safe triggered (close {close:.2f} > threshold {self.position.fail_safe_threshold:.2f})"
    # FTD -> BUY (from SELL)
    elif is_ftd:
        self.enter_buy(ftd_price, date, low, signal_type)
        action = f"BUY at {ftd_price:.2f} ({signal_type}) from SELL"
```

### Pattern 4: Standby-Sell Day HIGH Capture

**What:** The engine must pass the HIGH of the day BEFORE the sell signal day to `enter_sell()`
**Key insight:** The "standby-sell day" = the day immediately before the sell signal day. Its HIGH is the threshold.

In `mdm_v2_engine.py`, when CASH->SELL transitions fire, the engine has access to the full DataFrame. The previous day's HIGH is `df.iloc[idx-1]['high']` (or `row['prev_high']` if a prev_high column is added).

**Implementation approach:** Add `prev_high` column via `Indicators.add_prev_columns()` (which already adds `prev_close`, `prev_volume`), then pass it to `enter_sell()`.

### Pattern 5: Fail-Safe Exit Method

**What:** New method on V2PositionManager for fail-safe exit
```python
def fail_safe_exit(self, date: pd.Timestamp, close: float):
    """Exit SELL state to CASH via fail-safe (SAFE-02)."""
    self.trades.append({
        'type': 'FAIL_SAFE_EXIT',
        'date': date,
        'price': close,
        'reason': f"Fail-safe: close {close:.2f} > standby-sell HIGH {self.position.fail_safe_threshold:.2f}",
    })
    self.position = V2Position(
        state=V2MarketState.CASH,
        days_in_cash=0,
        ma10_below_count=0,
    )
```

### Anti-Patterns to Avoid

- **Checking fail-safe AFTER FTD:** If FTD fires on the same day fail-safe would trigger, fail-safe should take priority (exit to CASH first, then FTD can trigger BUY on next day if conditions still hold). This prevents skipping the CASH state.
- **Using current day's HIGH instead of previous day's HIGH:** The standby-sell day is the day BEFORE the sell signal day. Dr. K's definition is explicit about this.
- **Look-ahead bias with prev_high:** Must use `shift(1)` or `iloc[idx-1]` -- never access future data. The existing `Indicators.add_prev_columns()` already does this correctly for `prev_close`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| A/B backtest comparison | Custom comparison logic | Follow `validate_sell_acceleration.py` pattern | Already has bear period validation, equity comparison, metric extraction |
| Equity curve calculation | Manual P&L tracking | `V2PerformanceAnalyzer` | Handles state[i-1] bias correctly |
| Previous day column | Manual indexing in loop | `Indicators.add_prev_columns()` + extend it | Vectorized, handles edge cases |

## Common Pitfalls

### Pitfall 1: State[i] vs State[i-1] Bug
**What goes wrong:** Using current day's state instead of previous day's state for return capture creates massive look-ahead bias (707% vs 93% equity difference documented in project history).
**Why it happens:** Natural to check current state for today's return.
**How to avoid:** All equity/return calculations use `V2PerformanceAnalyzer` which already handles this correctly. Never compute equity manually.
**Warning signs:** Equity curves that look "too good" -- suspiciously high returns.

### Pitfall 2: Fail-Safe Triggering in Genuine Bear Markets
**What goes wrong:** If fail-safe threshold is too easily reclaimed (e.g., during a dead-cat bounce in 2022), it prematurely exits SELL, causing the engine to miss the full bear decline.
**Why it happens:** Even in genuine bear markets, there are short-term bounces that can temporarily exceed the standby-sell HIGH.
**How to avoid:** Success criterion 4 explicitly requires validation: "no fail-safe exit occurs within 10 days of a SELL that precedes a 10%+ decline." Test against VN30 2022 bear market (Jan-Nov 2022, ~40% decline). The threshold being the standby-sell day HIGH (not a lower threshold) is Dr. K's design choice specifically to avoid this -- the HIGH is a strong resistance level.
**Warning signs:** Fail-safe triggers during 2022 VN30 crash period.

### Pitfall 3: Fail-Safe Creates Whipsaw with FTD
**What goes wrong:** Fail-safe exits to CASH, then FTD immediately fires, then another SELL, creating rapid state cycling.
**Why it happens:** After fail-safe exits to CASH, the engine enters rally tracking mode. If market is choppy, FTD/SELL can cycle quickly.
**How to avoid:** This is actually correct behavior -- the fail-safe IS designed to detect false SELLs and exit. If the market then genuinely deteriorates, it should re-enter SELL via normal CASH->SELL path. Monitor trade count in A/B test -- if fail-safe significantly increases trade count, it may need a cooldown.
**Warning signs:** Trade count increases by >50% vs baseline.

### Pitfall 4: prev_high Not Available on First Day
**What goes wrong:** `df.iloc[idx-1]['high']` when idx=0 causes index error or wrong value.
**How to avoid:** The engine already skips idx=0 (`if idx == 0: continue`). Additionally, CASH->SELL transitions never fire on the first day (need indicator warmup). No special handling needed, but `add_prev_columns` should include `prev_high` to be safe.

### Pitfall 5: Fail-Safe on NASDAQ vs VN30
**What goes wrong:** Dr. K's fail-safe is defined for NASDAQ. VN30 has different market microstructure (7% daily price limit, T+2.5 settlement) which may affect how the standby-sell HIGH behaves.
**How to avoid:** The A/B backtest (SAFE-03) runs on VN30 data specifically. If fail-safe triggers too often or too rarely on VN30, the threshold concept may need VN30-specific calibration. But start with the exact Dr. K rule and measure first.

## Code Examples

### Example 1: How enter_sell() Changes

```python
# Current signature:
def enter_sell(self, date: pd.Timestamp, reason: str):

# New signature with fail-safe threshold:
def enter_sell(self, date: pd.Timestamp, reason: str, fail_safe_threshold: float = 0.0):
    """Enter SELL state from CASH."""
    self.trades.append({
        'type': 'SELL_SIGNAL',
        'date': date,
        'reason': reason,
    })
    self.position = V2Position(
        state=V2MarketState.SELL,
        days_in_cash=0,
        ma10_below_count=0,
        fail_safe_threshold=fail_safe_threshold,  # SAFE-01
    )
```

### Example 2: Engine Passes prev_high

```python
# In mdm_v2_engine.py, where CASH->SELL transitions fire:
# The prev_high is the HIGH of the day before the sell signal day
prev_high = df.iloc[idx - 1]['high'] if idx > 0 else 0.0

# MA50 breakdown path:
self.enter_sell(
    date,
    f"MA50 breakdown (close {close:.2f} < MA50 {ma50:.2f})",
    fail_safe_threshold=prev_high,
)

# Cash deterioration path:
self.enter_sell(
    date,
    f"Cash deterioration ({self.position.days_in_cash} days)",
    fail_safe_threshold=prev_high,
)
```

### Example 3: A/B Validation Script Pattern

```python
# Follow validate_sell_acceleration.py pattern:
# 1. Create baseline config (fail_safe_enabled=False)
# 2. Create test config (fail_safe_enabled=True)
# 3. Run both on VN30 full period
# 4. Compare: false SELL trade losses, total return, max drawdown
# 5. Validate bear market safety (2022 VN30)

baseline_config = MDMV2Config(fail_safe_enabled=False, name="baseline")
failsafe_config = MDMV2Config(fail_safe_enabled=True, name="fail_safe")

# Run engines
baseline_engine = MDMV2Engine(baseline_config)
failsafe_engine = MDMV2Engine(failsafe_config)

baseline_results = baseline_engine.run(vn30_data)
failsafe_results = failsafe_engine.run(vn30_data)

# Compare false SELL trades (SELLs followed by market recovery)
# A false SELL = SELL signal followed by market closing above sell-day price within N days
```

### Example 4: Identifying False SELL Trades for SAFE-03

```python
def identify_false_sells(results_df, trades, recovery_window=20):
    """Identify SELL signals that were followed by market recovery.

    A false SELL = SELL signal where the market close exceeds the
    standby-sell HIGH within recovery_window days.
    """
    sell_trades = [t for t in trades if t['type'] == 'SELL_SIGNAL']
    false_sells = []
    for sell in sell_trades:
        sell_date = sell['date']
        sell_idx = results_df[results_df['date'] == sell_date].index[0]
        # Look at next N days
        future = results_df.iloc[sell_idx:sell_idx + recovery_window]
        # If market recovers above sell-day close, it was false
        sell_close = results_df.loc[sell_idx, 'close']
        if (future['close'] > sell_close).any():
            false_sells.append(sell)
    return false_sells
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SELL is permanent until FTD | SELL can exit to CASH via fail-safe | v6.0 (this phase) | Reduces false SELL losses from -1% to -2.5% range |
| No standby-sell concept | Track standby-sell day HIGH as threshold | v6.0 (this phase) | Gives engine ability to detect false signals |

**Dr. K's stated loss range for false signals:** -1% to -1.5% normal, -1.5% to -2.5% high volatility. This gives us a benchmark to compare against.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_fail_safe.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAFE-01 | SELL entry records standby-sell HIGH in position state | unit | `uv run pytest tests/test_fail_safe.py::test_sell_records_threshold -x` | Wave 0 |
| SAFE-01 | fail_safe_threshold == prev day HIGH (not current day) | unit | `uv run pytest tests/test_fail_safe.py::test_threshold_is_prev_day_high -x` | Wave 0 |
| SAFE-02 | Close > threshold triggers SELL->CASH transition | unit | `uv run pytest tests/test_fail_safe.py::test_fail_safe_triggers_cash -x` | Wave 0 |
| SAFE-02 | Close <= threshold keeps SELL state | unit | `uv run pytest tests/test_fail_safe.py::test_no_trigger_below_threshold -x` | Wave 0 |
| SAFE-02 | Trade record has "fail-safe triggered" annotation | unit | `uv run pytest tests/test_fail_safe.py::test_fail_safe_trade_annotation -x` | Wave 0 |
| SAFE-02 | fail_safe_enabled=False disables mechanism | unit | `uv run pytest tests/test_fail_safe.py::test_disabled_no_trigger -x` | Wave 0 |
| SAFE-03 | A/B backtest on VN30 shows reduced false signal loss | integration | `uv run python analysis/validate_fail_safe.py` | Wave 0 |
| SC-4 | No fail-safe trigger during 2022 VN30 bear market | integration | `uv run python analysis/validate_fail_safe.py` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_fail_safe.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_fail_safe.py` -- covers SAFE-01, SAFE-02
- [ ] `analysis/validate_fail_safe.py` -- covers SAFE-03, SC-4

## Sources

### Primary (HIGH confidence)
- VOSI FAQ Findings (project memory `project_mdm_findings.md` lines 135-140) -- Dr. K's exact fail-safe definition: "NASDAQ moves above the HIGH of the standby-sell signal day"
- Source code: `strategies/mdm_v2/position_manager.py` -- current SELL state handling
- Source code: `strategies/mdm_v2/mdm_v2_engine.py` -- current engine loop
- Source code: `strategies/mdm_v2/config.py` -- config pattern
- Source code: `analysis/validate_sell_acceleration.py` -- A/B validation pattern

### Secondary (MEDIUM confidence)
- Project PITFALLS.md -- SELL suppression bias warnings apply to fail-safe (must validate on bear markets)
- Dr. K webinar 2013 -- SELL acceleration requirement (fail-safe is the inverse: exit from SELL when signal was false)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, pure extension of existing code
- Architecture: HIGH - follows exact patterns from sell_acceleration, QE floor, buy_selectivity phases
- Pitfalls: HIGH - well-documented in project research and Dr. K's own loss range data
- Dr. K rule definition: HIGH - directly from VOSI FAQ scrape with specific threshold definition

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable domain, no external dependencies)
