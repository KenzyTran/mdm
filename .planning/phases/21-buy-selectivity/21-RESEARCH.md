# Phase 21: BUY Selectivity - Research

**Researched:** 2026-03-31
**Domain:** FTD entry filtering, confirmation window, walk-forward validation
**Confidence:** HIGH

## Summary

Phase 21 adds two BUY-side filters to the MDM V2 engine: (1) an MA10 < MA50 rejection filter that blocks classic FTD signals when the trend is not confirmed, and (2) a post-FTD confirmation window that requires 3 clean days (max 1 DD) before committing to BUY. Both filters apply only to classic FTD signals -- MA50 breakout and 52-week breakout bypass both filters.

The implementation follows the established gate pattern from Phase 20 (SellAccelerationGate). Two new modules (`buy_filter.py`, `buy_confirmation.py`) will be created in `strategies/mdm_v2/`. The engine wires these gates before passing `is_ftd` to `position_manager.process_day()`, exactly like `suppress_sell` and `acceleration_met`. The confirmation window introduces statefulness across multiple days, which is the primary technical challenge.

**Primary recommendation:** Follow the SellAccelerationGate module pattern exactly. The buy filter is stateless (single-day check). The confirmation window is stateful (tracks pending FTD across days). Engine integration point is between FTD detection (line ~156) and the `process_day()` call (line ~238).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** MA10 < MA50 rejection filter applies ONLY to classic FTD signals. MA50 breakout and 52-week breakout bypass this filter.
- **D-02:** No additional rejection conditions beyond MA10 < MA50.
- **D-03:** Post-FTD confirmation window is 3 trading days. During this window, state remains CASH.
- **D-04:** FTD is canceled when 2 or more Distribution Days occur within the 3-day window. A single DD is tolerated.
- **D-05:** If window passes cleanly (0-1 DD), BUY entry is confirmed at the close price of the confirmation day (day 3), NOT the original FTD price.
- **D-06:** Confirmation window applies only to classic FTD signals (same scope as D-01).
- **D-07:** Two separate modules: `buy_filter.py` for MA10/MA50 rejection, `buy_confirmation.py` for N-day window tracking.
- **D-08:** Engine-side filtering: engine calls filter/confirmation checks BEFORE passing `is_ftd` to `position_manager.process_day()`. If rejected or pending, `is_ftd=False`.
- **D-09:** Walk-forward validation with pre-2020 train / 2020-2026 test split. Degradation < 10%.
- **D-10:** Primary metrics: trade count reduction (target 15-40%) and win rate improvement.
- **D-11:** A/B validation script on both NASDAQ and VN30, following Phase 20's pattern.
- **D-12:** New config fields: `buy_filter_enabled` (True), `buy_confirmation_enabled` (True), `confirmation_window_days` (3), `confirmation_max_dd` (1).
- **D-13:** Same defaults for NASDAQ and VN30 initially.

### Claude's Discretion
- Exact class/method naming for buy_filter.py and buy_confirmation.py
- Internal state tracking for confirmation window (counter, DD accumulator)
- Validation script output format and report structure
- Whether to log filter/confirmation decisions in results DataFrame columns
- How engine tracks confirmation window state across days

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BUY-01 | Reject FTD signal when MA10 < MA50 (trend not confirmed), reducing whipsaw entries | Stateless filter in `buy_filter.py`; MA10 and MA50 already computed in engine DataFrame (`ma10`, `ma50` columns). Check at FTD detection time. |
| BUY-02 | Post-FTD confirmation window -- require N days without distribution day after FTD before committing to BUY | Stateful tracker in `buy_confirmation.py`; must track pending FTD, day counter, DD accumulator across engine loop iterations. Entry price changes to day-3 close. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Code-Docs Sync Rule:** When modifying strategy logic, MUST update `docs/rules_mdm_v2.md` in the same commit.
- **Equity formula rule:** Must use `state[i-1]` not `state[i]` to avoid look-ahead bias.
- **GSD Workflow Enforcement:** All changes through GSD commands.
- **Naming conventions:** snake_case files, PascalCase classes, methods prefixed with `check_`, `get_`, etc.
- **Module design:** Single-responsibility modules, config-driven parameters.

## Architecture Patterns

### Recommended Module Structure
```
strategies/mdm_v2/
    buy_filter.py          # NEW: MA10 < MA50 rejection (stateless)
    buy_confirmation.py    # NEW: N-day confirmation window (stateful)
    sell_acceleration.py   # EXISTING: template pattern
    config.py              # MODIFIED: new config fields
    mdm_v2_engine.py       # MODIFIED: wire new gates
docs/
    rules_mdm_v2.md        # MODIFIED: document buy selectivity rules
analysis/
    validate_buy_selectivity.py  # NEW: A/B validation script
```

### Pattern 1: Stateless Gate (BuyFilter)
**What:** Single-check rejection filter, mirrors SellAccelerationGate structure.
**When to use:** MA10 < MA50 check -- no state needed between days.
**Example:**
```python
# Source: Derived from sell_acceleration.py pattern
class BuyFilter:
    """Gates FTD signals on trend confirmation (MA10 >= MA50)."""

    def __init__(self, config: MDMV2Config):
        self.config = config

    def check(self, signal_type: str, ma10: float, ma50: float) -> bool:
        """Return True if FTD should be ALLOWED (not rejected).

        MA50 breakout and 52-week breakout always allowed (per D-01).
        When buy_filter_enabled=False, returns True (allow all).

        Args:
            signal_type: "FTD", "MA50", or "52WEEK"
            ma10: Current 10-day MA value
            ma50: Current 50-day MA value

        Returns:
            True if signal passes filter, False if rejected.
        """
        if not self.config.buy_filter_enabled:
            return True  # Disabled = allow all

        # Non-FTD signals bypass filter (D-01, D-06)
        if signal_type in ("MA50", "52WEEK"):
            return True

        # Reject FTD when MA10 < MA50
        if ma10 is not None and ma50 is not None:
            return ma10 >= ma50

        return True  # Allow if MAs unavailable
```

### Pattern 2: Stateful Gate (BuyConfirmation)
**What:** Tracks a pending FTD across multiple days with DD counting.
**When to use:** Confirmation window -- must persist state across engine loop iterations.
**Critical design notes:**
- Instance variable tracks pending state (not DataFrame column -- avoids look-ahead)
- Must be reset when a new FTD fires while one is pending
- Must be reset when confirmation succeeds or fails
- Entry price changes to day-3 close (D-05)

**Example:**
```python
# Source: Derived from sell_acceleration.py + stateful tracking
class BuyConfirmation:
    """Manages post-FTD confirmation window before BUY entry."""

    def __init__(self, config: MDMV2Config):
        self.config = config
        self._pending = False
        self._days_elapsed = 0
        self._dd_count = 0
        self._original_ftd_date = None

    def submit_ftd(self, date):
        """Register a new FTD signal for confirmation.

        Called when FTD passes the BuyFilter but needs confirmation.
        Resets any existing pending window.
        """
        if not self.config.buy_confirmation_enabled:
            return  # No-op when disabled
        self._pending = True
        self._days_elapsed = 0
        self._dd_count = 0
        self._original_ftd_date = date

    def process_day(self, is_dd: bool, close: float) -> tuple:
        """Advance confirmation window by one day.

        Args:
            is_dd: Whether today is a distribution day
            close: Today's closing price (used for confirmed entry)

        Returns:
            (confirmed: bool, rejected: bool, entry_price: float)
            - confirmed=True on day N if DD count <= max
            - rejected=True if DD count > max during window
            - entry_price is the close on confirmation day
        """
        if not self.config.buy_confirmation_enabled:
            return False, False, 0.0

        if not self._pending:
            return False, False, 0.0

        self._days_elapsed += 1
        if is_dd:
            self._dd_count += 1

        # Check cancellation (D-04): too many DDs
        if self._dd_count > self.config.confirmation_max_dd:
            self.reset()
            return False, True, 0.0

        # Check completion (D-05): window passed
        if self._days_elapsed >= self.config.confirmation_window_days:
            self.reset()
            return True, False, close  # Entry at day-3 close

        return False, False, 0.0  # Still pending

    def is_pending(self) -> bool:
        return self._pending

    def reset(self):
        self._pending = False
        self._days_elapsed = 0
        self._dd_count = 0
        self._original_ftd_date = None
```

### Pattern 3: Engine Integration
**What:** Wire buy gates between FTD detection and position_manager call.
**Integration point:** After line ~187 (FTD detection block), before line ~238 (process_day call).

```python
# In engine __init__:
self.buy_filter = None
if self.config.buy_filter_enabled:
    self.buy_filter = BuyFilter(self.config)

self.buy_confirmation = None
if self.config.buy_confirmation_enabled:
    self.buy_confirmation = BuyConfirmation(self.config)

# In engine run loop, after FTD detection block:
# Step 2b: Apply BUY selectivity gates
if is_ftd and self.buy_filter is not None:
    if not self.buy_filter.check(signal_type, ma10, ma50):
        is_ftd = False
        action_note = "FTD rejected: MA10 < MA50"

# Step 2c: Confirmation window
if is_ftd and signal_type == "FTD" and self.buy_confirmation is not None:
    self.buy_confirmation.submit_ftd(date)
    is_ftd = False  # Don't enter BUY yet, wait for confirmation

# Process confirmation window (runs every day, even non-FTD days)
if self.buy_confirmation is not None and self.buy_confirmation.is_pending():
    confirmed, rejected, entry_price = self.buy_confirmation.process_day(
        is_dd=is_dd_for_confirmation, close=close
    )
    if confirmed:
        is_ftd = True
        ftd_price = entry_price  # Day-3 close (D-05)
        signal_type = "FTD"
    elif rejected:
        action_note = "FTD canceled: DD threshold in confirmation window"
```

### Anti-Patterns to Avoid
- **Look-ahead bias in confirmation window:** Do NOT check DD using data from the full DataFrame. Must use the DD counter's real-time state as the engine processes each day sequentially.
- **State[i] instead of state[i-1]:** The equity formula bug. Confirmation window state must be based on previous day's state, not current.
- **Mutating is_ftd after position_manager call:** The filter must happen BEFORE process_day, not after. This is the established pattern (suppress_sell happens before process_day).
- **DD counting during confirmation vs BUY state:** DD is currently only counted in BUY state (line 194). During confirmation window, the engine is in CASH state. Need to decide: either count DDs specifically for confirmation window (even in CASH), or use a simpler heuristic. The confirmation window DD check should use the same DistributionDayCounter logic but applied during CASH state for the window period only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MA comparison | Custom MA calculation | Existing `ma10`, `ma50` columns from Indicators | Already computed in engine DataFrame |
| DD detection during confirmation | New DD detection logic | Existing `DistributionDayCounter.check_distribution_day()` | Same logic, just call it during CASH state for confirmation window |
| A/B validation framework | Custom comparison | Follow `validate_sell_acceleration.py` pattern | Proven pattern, consistent output |
| Walk-forward split | Manual date slicing | pandas date filtering (same as existing scripts) | Standard approach |

## Common Pitfalls

### Pitfall 1: DD Not Counted During CASH State
**What goes wrong:** The engine only counts DDs when `current_state == V2MarketState.BUY` (line 194). During the confirmation window, the state is CASH. If DDs are not detected during CASH, the confirmation window can never be canceled by DDs.
**Why it happens:** The original design only needed DD counting for BUY exit logic.
**How to avoid:** During confirmation window, call `check_distribution_day()` even when in CASH state. This is a temporary extension -- only active while confirmation is pending. The DD count from this check feeds into `buy_confirmation.process_day()`, not the main DD counter.
**Warning signs:** Confirmation window never gets canceled despite heavy selling days.

### Pitfall 2: Confirmation Window Interaction with MA50/52-Week Breakout
**What goes wrong:** A new MA50 breakout or 52-week breakout fires while a classic FTD is pending confirmation. The pending FTD should be superseded by the immediate entry.
**Why it happens:** Two buy signals compete.
**How to avoid:** If MA50 breakout or 52-week breakout fires, reset the confirmation window and enter BUY immediately. These signals bypass both filters (D-01, D-06).
**Warning signs:** Delayed entry despite strong breakout signal.

### Pitfall 3: Entry Price Change on Confirmation
**What goes wrong:** Using the original FTD price instead of day-3 close for the entry.
**Why it happens:** The existing `ftd_price` is set during FTD detection. If not overridden on confirmation day, the wrong price is used.
**How to avoid:** When confirmation succeeds, explicitly set `ftd_price = close` (day-3 close per D-05). The stop loss is then calculated from this new entry price.
**Warning signs:** Backtest P&L does not match expected entry prices.

### Pitfall 4: Confirmation Day DD Check Timing
**What goes wrong:** The DD check on the confirmation day itself (day 3) might be checked before or after the confirmation decision.
**Why it happens:** Order of operations within the day loop matters.
**How to avoid:** Process DD check first, then check confirmation window. If day 3 is itself a DD and that pushes count > max, the FTD should be canceled (not confirmed).
**Warning signs:** Edge case where day 3 is a DD but confirmation still passes.

### Pitfall 5: Walk-Forward Overfitting Assessment
**What goes wrong:** Parameters tuned on pre-2020 data show > 10% degradation on 2020-2026 test data.
**Why it happens:** The confirmation_window_days=3 and confirmation_max_dd=1 are fixed by decision (D-03, D-04). The MA10 < MA50 filter is parameter-free. Overfitting risk is LOW because there are no free parameters to tune.
**How to avoid:** The walk-forward test is a sanity check, not parameter optimization. Run with fixed parameters on both periods and compare.
**Warning signs:** If degradation > 10%, the fixed parameters may not generalize. But since parameters are not tuned, this is unlikely.

## Code Examples

### Engine Integration Point (exact location)
```python
# strategies/mdm_v2/mdm_v2_engine.py, line ~188
# AFTER: 52-week breakout check (line ~187)
# BEFORE: DD counting (line ~189)

# NEW: BUY selectivity gates
buy_rejected = False
buy_pending = False

if is_ftd and signal_type == "FTD":
    # Gate 1: MA10/MA50 trend filter (BUY-01)
    if self.buy_filter is not None:
        ma10_val = row['ma10'] if 'ma10' in row else None
        ma50_check = row['ma50'] if 'ma50' in row else None
        if not self.buy_filter.check("FTD", ma10_val, ma50_check):
            is_ftd = False
            buy_rejected = True

    # Gate 2: Confirmation window (BUY-02)
    if is_ftd and self.buy_confirmation is not None:
        self.buy_confirmation.submit_ftd(date)
        is_ftd = False  # Suppress immediate entry
        buy_pending = True

# Process pending confirmation (every day)
confirmation_dd = False
if self.buy_confirmation is not None and self.buy_confirmation.is_pending():
    # Must detect DD even in CASH state for confirmation window
    confirmation_dd, _ = self.dd_counter.check_distribution_day(
        date, price_change_pct, volume_up, p_loc
    )
    confirmed, rejected, entry_price = self.buy_confirmation.process_day(
        confirmation_dd, close
    )
    if confirmed:
        is_ftd = True
        ftd_price = entry_price
        signal_type = "FTD"
    elif rejected:
        pass  # FTD canceled, action logged
```

### Config Addition
```python
# strategies/mdm_v2/config.py, in MDMV2Config
# BUY Selectivity (v5.0, BUY-01, BUY-02)
buy_filter_enabled: bool = True           # MA10 < MA50 rejection (D-12)
buy_confirmation_enabled: bool = True     # Post-FTD confirmation (D-12)
confirmation_window_days: int = 3         # Days to confirm (D-03, D-12)
confirmation_max_dd: int = 1              # Max DD allowed in window (D-04, D-12)
```

### Validation Script Pattern
```python
# analysis/validate_buy_selectivity.py
# Follow validate_sell_acceleration.py pattern:
# 1. Define test periods (full NASDAQ, full VN30)
# 2. Run baseline (buy_filter_enabled=False, buy_confirmation_enabled=False)
# 3. Run filtered (buy_filter_enabled=True, buy_confirmation_enabled=True)
# 4. Compare: trade count reduction, win rate, total return
# 5. Walk-forward: train pre-2020, test 2020-2026
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_buy_selectivity.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUY-01 | FTD rejected when MA10 < MA50 | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyFilter -x` | Wave 0 |
| BUY-01 | MA50 breakout bypasses filter | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyFilter::test_ma50_breakout_bypasses -x` | Wave 0 |
| BUY-01 | 52-week breakout bypasses filter | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyFilter::test_52week_bypasses -x` | Wave 0 |
| BUY-02 | Confirmation window passes after 3 clean days | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyConfirmation::test_clean_window -x` | Wave 0 |
| BUY-02 | Confirmation canceled on 2+ DDs | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyConfirmation::test_dd_cancellation -x` | Wave 0 |
| BUY-02 | Entry price is day-3 close, not FTD price | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyConfirmation::test_entry_price -x` | Wave 0 |
| BUY-01+02 | Engine integration: filter + confirmation wired correctly | integration | `uv run pytest tests/test_buy_selectivity.py::TestEngineIntegration -x` | Wave 0 |
| BUY-01+02 | Trade count reduction 15-40% on NASDAQ | smoke | `uv run python analysis/validate_buy_selectivity.py` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_buy_selectivity.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green + validation script passes

### Wave 0 Gaps
- [ ] `tests/test_buy_selectivity.py` -- covers BUY-01, BUY-02 unit + integration tests
- [ ] `analysis/validate_buy_selectivity.py` -- A/B validation script

## Open Questions

1. **DD counting during CASH state for confirmation window**
   - What we know: DD counter only runs in BUY state currently. Confirmation window needs DD detection in CASH state.
   - What's unclear: Should we call `dd_counter.check_distribution_day()` (which may add to dd_history) or create a separate lightweight check?
   - Recommendation: Call `check_distribution_day()` but track the result separately for the confirmation window. Do NOT add to `dd_history` during CASH state -- that would pollute the main DD counter. Create a local boolean from the same conditions (price_change_pct and volume_up checks) without side effects.

2. **Interaction with suppress_sell during confirmation**
   - What we know: During confirmation window, state is CASH. CASH->SELL transitions can still fire.
   - What's unclear: If a SELL transition fires during confirmation window, should the pending FTD be canceled?
   - Recommendation: Yes -- if the market deteriorates enough to trigger SELL during confirmation, the pending FTD is clearly invalid. Reset confirmation window on SELL transition.

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_v2/sell_acceleration.py` -- template gate pattern (read directly)
- `strategies/mdm_v2/config.py` -- MDMV2Config structure and validation patterns (read directly)
- `strategies/mdm_v2/mdm_v2_engine.py` -- engine run loop, integration points (read directly)
- `strategies/mdm_v2/ftd_signal.py` -- FTD detection with signal_type differentiation (read directly)
- `strategies/mdm_v2/position_manager.py` -- CASH->BUY transition logic (read directly)
- `analysis/validate_sell_acceleration.py` -- A/B validation pattern (read directly)
- `docs/rules_mdm_v2.md` -- current rule documentation (read directly)

### Secondary (MEDIUM confidence)
- `.planning/phases/21-buy-selectivity/21-CONTEXT.md` -- locked decisions and canonical refs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all code patterns verified from existing codebase
- Architecture: HIGH -- directly follows Phase 20 gate pattern, all integration points verified
- Pitfalls: HIGH -- identified from reading actual engine code, DD counting scope verified

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable -- internal project patterns)
