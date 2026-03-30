# Phase 16: Short Position & State Transitions - Research

**Researched:** 2026-03-30
**Domain:** State machine extension (short positions), trading system position management
**Confidence:** HIGH

## Summary

Phase 16 extends the existing 3-state machine (BUY/CASH/SELL) so that SELL is no longer a passive label but an actual short position with entry price, cover mechanics, and P&L tracking on cover. The changes are concentrated in two files: `position_manager.py` (data model + state transitions) and `mdm_hybrid_engine.py` (cover trigger logic + SELL->CASH->BUY enforcement at engine level). A config flag `short_mode` is added for future VN30/NASDAQ differentiation.

The critical correctness requirement is TRANS-01: no direct SELL->BUY transition. Currently line 232-236 of position_manager.py allows exactly this. The fix requires defense-in-depth: a guard in `enter_buy()` that raises on SELL state, plus engine-level logic that covers the short to CASH before buying.

**Primary recommendation:** Implement in 3 focused tasks: (1) V2Position data model + enter_sell/cover_short methods, (2) engine-level cover triggers and SELL->CASH->BUY enforcement, (3) validation script verifying no SELL->BUY in NASDAQ signal log.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Extend V2Position with `short_entry_price: float = 0.0` and `short_entry_date: Optional[pd.Timestamp] = None`. Shared dataclass, unused fields = 0/None.
- D-02: `enter_sell()` takes `price` param, stores in `short_entry_price` and `short_entry_date`. Entry price = close on SELL signal day.
- D-03: On short cover, compute P&L immediately: `(short_entry_price - cover_price) / short_entry_price`. Gain when market falls, loss when market rises.
- D-04: Cover short on FTD detected -> CASH (record short P&L).
- D-05: Cover short on close > MA50 (MA50 breakout) -> CASH. Symmetric with CASH->SELL (close < MA50).
- D-06: Indicator filter OVERRIDE/VETO when in SELL also covers short to CASH. Consistent with Phase 13 D-04/D-07.
- D-07: Defense in depth -- enforce at both engine level AND position manager level.
- D-08: Position manager `enter_buy()` has guard -- if currently SELL, raise error (catch bug, don't auto-cover).
- D-09: Engine: before calling `enter_buy()`, check if in SELL -> cover short first, then BUY.
- D-10: Config flag `short_mode: str = 'direct'` in config. Values: 'direct' (VN30) or 'inverse_etf' (NASDAQ). Both share same logic for now.

### Claude's Discretion
- SELL->CASH->BUY timing: whether CASH is transient (cover + buy same day) or persistent (CASH at least 1 day). Based on MDM behavior and Dr. K's signal history.
- Method naming for cover short (e.g., `cover_short()` vs `exit_short_to_cash()`)
- Trade record format for short trades (type field values)
- Priority ordering between cover triggers (FTD vs MA50 vs filter)
- Integration with two-phase commit snapshot/restore pattern

### Deferred Ideas (OUT OF SCOPE)
- Short stop loss (1% above DD5 high) -- Phase 17 (SHORT-03, RISK-03)
- Inverse ETF decay modeling for NASDAQ -- future enhancement
- Short P&L reporting and comparison dashboard -- Phase 18 (SHORT-02, TRANS-02)
- Anti-whipsaw / cooldown logic for short transitions -- FUT-03
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHORT-01 | SELL signal opens short position on index (VN30: direct, NASDAQ: inverse ETF concept) | V2Position extension (D-01/D-02), enter_sell() modification, short_mode config flag (D-10) |
| SHORT-04 | Short cover on FTD or MA50 breakout -> CASH | New cover_short() method (D-04/D-05), engine cover trigger logic, degrade_to_cash pattern reference |
| TRANS-01 | Enforce SELL->CASH->BUY (no direct SELL->BUY) | enter_buy() guard (D-08), engine pre-check (D-09), NASDAQ signal log validation |
</phase_requirements>

## Architecture Patterns

### Current State Machine (pre-Phase 16)
```
CASH --[FTD/MA50 breakout]--> BUY
BUY --[DD count/stop loss/MA10]--> CASH
CASH --[MA50 breakdown/deterioration]--> SELL
SELL --[FTD/MA50 breakout]--> BUY  (BUG: direct SELL->BUY, violates TRANS-01)
```

### Target State Machine (post-Phase 16)
```
CASH --[FTD/MA50 breakout]--> BUY
BUY --[DD count/stop loss/MA10]--> CASH
CASH --[MA50 breakdown/deterioration]--> SELL (opens short, records entry price)
SELL --[FTD detected]--> CASH (covers short, records P&L)
SELL --[close > MA50]--> CASH (covers short, records P&L)
SELL --[indicator OVERRIDE/VETO]--> CASH (covers short, records P&L)
CASH --[FTD/MA50 breakout]--> BUY
```

### Key Transition: SELL->CASH->BUY (same-day)
When FTD fires while in SELL state, the engine must:
1. Cover short to CASH (with P&L)
2. Then enter BUY (in the same daily processing step)

This is a **transient CASH** -- it appears in the trade log but may not persist as a full-day state. Dr. K's published signals show SELL followed directly by BUY on the same date in some cases, meaning the intermediate CASH is implicit. The engine should allow same-day cover+buy (transient CASH) to match this behavior.

### Recommended Project Structure (no new files)
```
strategies/mdm_hybrid/
  position_manager.py   # MODIFY: V2Position fields, enter_sell(price), cover_short(), enter_buy() guard
  mdm_hybrid_engine.py  # MODIFY: cover triggers in SELL processing, SELL->CASH->BUY at engine level
  config.py             # MODIFY: add short_mode to HybridConfig
  stop_loss.py          # NO CHANGE (Phase 17)
  performance.py        # NO CHANGE (Phase 18)
```

### Pattern: Cover Short Method
Follow `exit_to_cash()` pattern but with reversed P&L calculation:

```python
def cover_short(self, cover_price: float, cover_date: pd.Timestamp, reason: str):
    """Cover short position and return to CASH state."""
    entry = self.position.short_entry_price
    pnl = (entry - cover_price) / entry if entry > 0 else 0

    self.trades.append({
        'type': 'SHORT_COVER',
        'date': cover_date,
        'price': cover_price,
        'reason': reason,
        'pnl': pnl,
        'entry_price': entry,
    })

    self.position = V2Position(
        state=V2MarketState.CASH,
        days_in_cash=0,
        ma10_below_count=0,
    )
```

### Pattern: enter_buy() Guard (D-08)
```python
def enter_buy(self, buy_price, buy_date, buy_day_low, signal_type="FTD"):
    """Enter BUY state. Raises if currently in SELL (must cover first)."""
    if self.position.state == V2MarketState.SELL:
        raise ValueError(
            f"Cannot enter BUY directly from SELL state. "
            f"Must cover_short() first. Date: {buy_date}"
        )
    # ... existing logic
```

### Pattern: Engine SELL->CASH->BUY (D-09)
In the engine's SELL state processing block:

```python
elif current_state == V2MarketState.SELL:
    if is_ftd:
        # Cover short first, then buy
        self.position_manager.cover_short(close, date, "FTD detected")
        self.position_manager.enter_buy(ftd_price, date, low, signal_type)
        action = f"SHORT_COVER + BUY at {ftd_price:.2f} ({signal_type})"
    elif ma50_val is not None and close > ma50_val:
        # MA50 breakout covers short to CASH (no buy)
        self.position_manager.cover_short(close, date, f"MA50 breakout (close {close:.2f} > MA50 {ma50_val:.2f})")
        action = f"SHORT_COVER: MA50 breakout"
```

### Anti-Pattern: degrade_to_cash for Short Cover
Do NOT use `degrade_to_cash()` for short cover -- it skips P&L calculation. Always use the new `cover_short()` method which computes short P&L. Reserve `degrade_to_cash()` for non-position state changes only.

### Integration with Two-Phase Commit
The indicator filter OVERRIDE/VETO handling in the engine (lines 343-378) already handles SELL degradation. Currently it calls `degrade_to_cash()`. After Phase 16, these paths must call `cover_short()` instead to capture short P&L:

```python
# Before (Phase 13):
elif old_state == V2MarketState.SELL:
    self.position_manager.degrade_to_cash(date, "indicator degradation from SELL")

# After (Phase 16):
elif old_state == V2MarketState.SELL:
    self.position_manager.cover_short(close, date, "indicator degradation from SELL")
```

This applies to both the "state change + OVERRIDE" path (line 358-361) and the "no state change + VETO/OVERRIDE" path (line 373-377).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Short P&L calculation | Custom gain/loss formula | Standard `(entry - exit) / entry` | Matches D-03, consistent with long P&L pattern |
| State transition guard | Complex if-else chains | Single ValueError in enter_buy() + engine pre-check | Defense in depth per D-07 |
| Trade type tracking | Separate short trade list | Extend existing trades list with 'SHORT_COVER' type | Keep single trade log for Phase 18 reporting |

## Common Pitfalls

### Pitfall 1: Forgetting to Update degrade_to_cash Calls
**What goes wrong:** Existing `degrade_to_cash()` calls for SELL state (indicator override paths) don't record short P&L after Phase 16.
**Why it happens:** There are 2 separate code paths in the engine that degrade SELL to CASH (lines 358-361 and 373-377). Easy to miss one.
**How to avoid:** Search for ALL `degrade_to_cash` calls. Any that can fire when state is SELL must become `cover_short()`.
**Warning signs:** Short trades with no P&L recorded in trade log.

### Pitfall 2: Snapshot/Restore Breaking Short State
**What goes wrong:** After two-phase commit restore, short_entry_price and short_entry_date are lost because deepcopy of V2Position doesn't include new fields.
**Why it happens:** `copy.deepcopy()` on dataclass should work automatically for new fields. But if V2Position uses `__slots__` or custom `__copy__`, it could break.
**How to avoid:** V2Position is a standard `@dataclass` -- deepcopy works correctly. But verify with a test that snapshot/restore preserves short fields.
**Warning signs:** Short P&L = 0 after veto+restore cycles.

### Pitfall 3: SELL->CASH->BUY Double Trade Recording
**What goes wrong:** cover_short() appends a trade, then enter_buy() appends another. If not careful, the state might be inconsistent between the two calls.
**Why it happens:** cover_short() sets state to CASH, enter_buy() expects CASH state. This is correct flow, but if any intermediate check runs between them, it could see inconsistent state.
**How to avoid:** Call cover_short() and enter_buy() sequentially in the same engine block with no intervening state checks. The trade log will correctly show SHORT_COVER then BUY.
**Warning signs:** Assertion errors or state mismatch logs.

### Pitfall 4: MA50 Breakout as Both Short Cover AND Buy Trigger
**What goes wrong:** When in SELL and close > MA50, the MA50 breakout covers the short AND could trigger a buy signal (since MA50 breakout is a buy signal type). This could cause same-day cover+buy via MA50.
**Why it happens:** The FTD detection code at line 238-249 checks MA50 breakout when in CASH or SELL state.
**How to avoid:** Decide whether MA50 breakout from SELL should only cover (to CASH) or also buy. Recommendation: MA50 breakout from SELL covers to CASH only. FTD from SELL covers+buys. This avoids whipsaw.
**Warning signs:** Frequent same-day SHORT_COVER + BUY via MA50 breakout.

### Pitfall 5: enter_sell() Callers Need price Parameter
**What goes wrong:** All existing callers of `enter_sell()` don't pass a price. After adding the price param, they break.
**Why it happens:** enter_sell() is called in position_manager.process_day() (line 204, 208) and needs the close price passed through.
**How to avoid:** Add `close` parameter to process_day's enter_sell calls. The close price is already available in process_day's parameters.
**Warning signs:** TypeError on missing positional argument.

### Pitfall 6: Existing Test Regression
**What goes wrong:** Existing tests in test_hybrid_engine.py and test_mdm_v2_states.py may assert on trade log format or state transitions that change.
**Why it happens:** SELL->BUY direct transition was the old behavior. Tests may explicitly test for it.
**How to avoid:** Run existing test suite before and after changes. Update tests that expected direct SELL->BUY to expect SELL->CASH->BUY.
**Warning signs:** Test failures in unmodified test files.

## Code Examples

### V2Position Extension (D-01)
```python
# Source: position_manager.py, current V2Position at line 24
@dataclass
class V2Position:
    """Current position information for v2 engine."""
    state: V2MarketState = V2MarketState.CASH
    buy_price: float = 0.0
    buy_date: Optional[pd.Timestamp] = None
    buy_day_low: float = 0.0
    signal_type: str = "FTD"
    days_in_cash: int = 0
    ma10_below_count: int = 0
    # Phase 16: short position fields (D-01)
    short_entry_price: float = 0.0
    short_entry_date: Optional[pd.Timestamp] = None
```

### enter_sell() with Price (D-02)
```python
# Source: position_manager.py, current enter_sell at line 119
def enter_sell(self, date: pd.Timestamp, reason: str, price: float = 0.0):
    """Enter SELL state and open short position."""
    self.trades.append({
        'type': 'SELL_SIGNAL',
        'date': date,
        'price': price,
        'reason': reason,
    })
    self.position = V2Position(
        state=V2MarketState.SELL,
        days_in_cash=0,
        ma10_below_count=0,
        short_entry_price=price,
        short_entry_date=date,
    )
```

### HybridConfig Extension (D-10)
```python
# Source: config.py, add to HybridConfig
@dataclass
class HybridConfig:
    v2_config: MDMV2Config = field(default_factory=MDMV2Config)
    two_phase_enabled: bool = True
    filter_enabled: bool = False
    filter_config: FilterConfig = field(default_factory=FilterConfig)
    short_mode: str = 'direct'  # 'direct' or 'inverse_etf' (D-10)
```

### NASDAQ Validation Script (TRANS-01)
```python
# Validate no SELL->BUY in signal log
def validate_no_sell_to_buy(results_df):
    """Verify every BUY is preceded by CASH, never by SELL."""
    states = results_df[results_df['action'] != '']['state'].tolist()
    for i in range(1, len(states)):
        if states[i] == 'BUY':
            assert states[i-1] != 'SELL', (
                f"SELL->BUY violation at index {i}: "
                f"state[{i-1}]={states[i-1]}, state[{i}]={states[i]}"
            )
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_hybrid_engine.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHORT-01 | SELL signal records short_entry_price and short_entry_date | unit | `uv run pytest tests/test_short_position.py::test_enter_sell_records_short_fields -x` | Wave 0 |
| SHORT-01 | short_mode config flag exists with default 'direct' | unit | `uv run pytest tests/test_short_position.py::test_short_mode_config -x` | Wave 0 |
| SHORT-04 | FTD covers short to CASH with P&L | unit | `uv run pytest tests/test_short_position.py::test_ftd_covers_short -x` | Wave 0 |
| SHORT-04 | MA50 breakout covers short to CASH | unit | `uv run pytest tests/test_short_position.py::test_ma50_covers_short -x` | Wave 0 |
| SHORT-04 | Indicator OVERRIDE covers short to CASH | unit | `uv run pytest tests/test_short_position.py::test_indicator_override_covers_short -x` | Wave 0 |
| SHORT-04 | Short P&L calculated correctly (gain on market drop) | unit | `uv run pytest tests/test_short_position.py::test_short_pnl_calculation -x` | Wave 0 |
| TRANS-01 | enter_buy() raises ValueError when in SELL | unit | `uv run pytest tests/test_short_position.py::test_enter_buy_guard -x` | Wave 0 |
| TRANS-01 | Engine SELL->CASH->BUY on FTD (same day) | integration | `uv run pytest tests/test_short_position.py::test_sell_cash_buy_transition -x` | Wave 0 |
| TRANS-01 | NASDAQ full run: every BUY preceded by CASH | integration | `uv run pytest tests/test_short_position.py::test_nasdaq_no_sell_to_buy -x` | Wave 0 |
| - | Existing hybrid engine tests still pass | regression | `uv run pytest tests/test_hybrid_engine.py -x` | Existing |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_short_position.py -x`
- **Per wave merge:** `uv run pytest tests/test_hybrid_engine.py tests/test_short_position.py -x`
- **Phase gate:** `uv run pytest tests/ -x` full suite green before verify

### Wave 0 Gaps
- [ ] `tests/test_short_position.py` -- covers SHORT-01, SHORT-04, TRANS-01
- [ ] No new conftest.py fixtures needed (existing `_make_ohlcv` helper in test_hybrid_engine.py can be imported or duplicated)

## Project Constraints (from CLAUDE.md)

- Python 3.10+, pandas >= 2.0, numpy >= 1.24
- snake_case for functions/variables, PascalCase for classes
- 4-space indentation, 120-char line limit
- Dataclass pattern for data objects (V2Position)
- Trade recording: append dict to self.trades list
- All work through GSD workflow
- No linting/formatting enforcement (no black/flake8 config)
- uv as package manager (`uv run pytest` for tests)

## Open Questions

1. **Transient CASH timing for FTD from SELL**
   - What we know: Dr. K's signals sometimes show SELL on day N and BUY on day N+1 (or even same day). The intermediate CASH is implicit.
   - What's unclear: Whether the validation script should check consecutive calendar days or just consecutive signal entries.
   - Recommendation: Check consecutive signal entries in the trade log. A SHORT_COVER + BUY on the same date is valid (transient CASH). The constraint is that the trade log sequence must show SHORT_COVER before BUY, never SELL_SIGNAL immediately followed by BUY.

2. **MA50 breakout from SELL: cover only or cover+buy?**
   - What we know: MA50 breakout is both a short cover trigger (D-05) and a buy signal (existing logic).
   - What's unclear: Whether to allow same-day cover+buy via MA50 breakout, or restrict MA50 breakout from SELL to cover-only.
   - Recommendation: MA50 breakout from SELL should only cover to CASH. The next day's processing can detect MA50 breakout again from CASH and trigger a buy. This avoids Pitfall 4 and matches the "favor cash" philosophy.

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_hybrid/position_manager.py` -- current V2Position, enter_sell(), enter_buy(), degrade_to_cash(), process_day() implementation
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` -- current engine loop, two-phase commit, filter handling, SELL state processing
- `strategies/mdm_hybrid/config.py` -- HybridConfig, MDMV2Config dataclasses
- `strategies/mdm_hybrid/indicator_filter.py` -- Verdict enum, OVERRIDE/VETO mechanics
- `.planning/phases/16-short-position-state-transitions/16-CONTEXT.md` -- all D-01 through D-10 decisions

### Secondary (MEDIUM confidence)
- `tests/test_hybrid_engine.py` -- existing test patterns, _make_ohlcv helper
- `.planning/REQUIREMENTS.md` -- SHORT-01, SHORT-04, TRANS-01 requirement definitions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pure Python dataclass/enum extension, no new libraries
- Architecture: HIGH - all modification targets read and understood, patterns clear from existing code
- Pitfalls: HIGH - identified from direct code reading, all 6 pitfalls have specific line references

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable -- internal code, no external dependency changes)
