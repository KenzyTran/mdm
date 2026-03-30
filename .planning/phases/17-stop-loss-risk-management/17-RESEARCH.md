# Phase 17: Stop Loss & Risk Management - Research

**Researched:** 2026-03-30
**Domain:** Trading system stop loss mechanics, volatility-adaptive risk management, short position risk controls
**Confidence:** HIGH

## Summary

Phase 17 modifies the existing `StopLossChecker` in `strategies/mdm_hybrid/stop_loss.py` to implement three distinct changes: (1) reduce the default long stop loss from 2.5% to 1.5%, (2) add volatility-adaptive scaling using ATR (Average True Range), and (3) add a completely new short stop loss that triggers at 1% above the DD5 high. The changes are well-scoped because the existing stop loss module already has a clean interface (`StopLossResult` dataclass, `.check()` method) and the engine calls it at a single point in the daily processing loop.

The most technically challenging part is DD5 high tracking for short stop loss. Currently, `DistributionDayCounter.dd_history` only stores dates (not prices). The engine must either extend DD history to include high prices, or look up the high from the DataFrame at the DD5 date. ATR computation does not exist in the codebase yet -- it needs to be added to either `core/indicators.py` or the hybrid indicators module.

**Primary recommendation:** Implement in 2 plans: (1) Long stop loss changes (1.5% default + ATR-based volatility scaling + config params), (2) Short stop loss (DD5 high tracking + 1% above DD5 high trigger + engine integration for SELL state).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RISK-01 | Stop loss default 1.5% for long positions (down from 2.5%) | Config change: `stop_loss_pct: float = 0.015` in MDMV2Config. Also in mdm_hybrid/config.py and mdm_v2/config.py |
| RISK-02 | Volatility-adaptive stop loss -- wider during high-vol, tighter during low-vol | ATR computation needed (not in codebase). StopLossChecker.check() accepts ATR, scales stop_loss_pct. Multiplier config params needed |
| RISK-03 | Short stop loss -- 1% above DD5 high (from MDM classic rules) | DD5 high tracking in DistributionDayCounter or engine. New check_short() method in StopLossChecker. Engine calls during SELL state |
| SHORT-03 | Short stop loss triggers at 1% above DD5 high | Same as RISK-03 -- covers short position when `close > dd5_high * 1.01` |
</phase_requirements>

## Architecture Patterns

### Current Stop Loss Flow (pre-Phase 17)
```
Engine.run() daily loop:
  -> StopLossChecker.check(close, buy_price, buy_day_low, ...)
     -> Returns StopLossResult(triggered, reason, loss_pct)
  -> position_manager.process_day(stop_loss_triggered=..., stop_loss_reason=...)
     -> if BUY and stop_loss_triggered: exit_to_cash()
     -> if SELL: NO stop loss check at all
```

### Target Stop Loss Flow (post-Phase 17)
```
Engine.run() daily loop:
  -> Compute ATR (new column in DataFrame, done in prepare_data)
  -> If BUY state:
     -> StopLossChecker.check(close, buy_price, buy_day_low, ..., atr=atr)
        -> base_pct = 0.015 (was 0.025)
        -> effective_pct = volatility_adjust(base_pct, atr, atr_baseline)
        -> Same 3 rules but with effective_pct instead of fixed pct
  -> If SELL state:
     -> StopLossChecker.check_short(close, dd5_high)
        -> triggered if close > dd5_high * 1.01
        -> Returns StopLossResult
  -> position_manager.process_day(stop_loss_triggered=..., stop_loss_reason=...)
     -> if BUY and stop_loss_triggered: exit_to_cash()
     -> if SELL and short_stop_triggered: cover_short()
```

### Key Data Flow: DD5 High Tracking
```
DistributionDayCounter tracks DD dates
  -> When dd_count reaches 5 (the 5th DD), record the HIGH of that day
  -> Store as dd5_high on the counter (or pass through engine)
  -> Used by short stop loss: close > dd5_high * 1.01

Two approaches:
  A) Extend DistributionDayCounter to store (date, high) tuples
     + Clean encapsulation
     + DD counter already knows when DD occurs
     - Requires passing high price to check_distribution_day()

  B) Engine looks up high from DataFrame when dd_count == 5
     + No change to DD counter interface
     - Logic scattered across engine
```

**Recommendation:** Approach A -- extend DD counter to store `(date, high)` tuples. Add `get_dd5_high()` method that returns the high of the most recent 5th distribution day in the window.

### Files to Modify

| File | Change | Scope |
|------|--------|-------|
| `strategies/mdm_hybrid/config.py` | `stop_loss_pct: 0.025 -> 0.015`, add `atr_period`, `atr_multiplier_low`, `atr_multiplier_high`, `atr_baseline` | Config only |
| `strategies/mdm_v2/config.py` | Same config changes | Config only |
| `strategies/mdm_hybrid/stop_loss.py` | New `check_short()` method, ATR-based scaling in `check()` | Core logic |
| `strategies/mdm_v2/stop_loss.py` | Same changes (mirror) | Core logic |
| `strategies/mdm_hybrid/indicators.py` | Add `add_atr_column()` static method | New indicator |
| `strategies/mdm_hybrid/distribution_day.py` | Store `(date, high)` in dd_history, add `get_dd5_high()` | Data tracking |
| `strategies/mdm_hybrid/mdm_hybrid_engine.py` | Call ATR in prepare_data, pass ATR to stop loss, add short stop loss check in SELL state | Integration |
| `strategies/mdm_hybrid/position_manager.py` | Accept short_stop_loss params in process_day for SELL state | Integration |

### Anti-Patterns to Avoid
- **Separate stop loss modules for long vs short:** Keep in one StopLossChecker with `check()` for long and `check_short()` for short. Don't create a new ShortStopLossChecker class.
- **Hardcoded ATR baseline:** Make it configurable. NASDAQ and VN30 have very different ATR ranges.
- **Modifying DD counter signature silently:** When extending dd_history to store highs, ensure backward compatibility (check_distribution_day already takes `date`, adding `high` is a new required param -- update all callers).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | ATR computation via rolling operations | Already in project, standard for time series |
| numpy | >= 1.24.0 | Max/abs calculations for True Range | Already in project |

No new dependencies needed. ATR is a simple rolling calculation on existing OHLCV data.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ATR computation | Custom loop over rows | `pandas.DataFrame.rolling().mean()` on True Range column | Vectorized, fast, standard formula |
| DD5 high lookup | Scanning DD history list manually in engine | `DistributionDayCounter.get_dd5_high()` method | Encapsulation, single responsibility |

## Common Pitfalls

### Pitfall 1: ATR Scale Difference Between Markets
**What goes wrong:** ATR on NASDAQ (absolute values 50-200) vs VN30 (absolute values 5-30) means a fixed ATR threshold is meaningless across markets.
**Why it happens:** ATR is in absolute price units, not percentages.
**How to avoid:** Use ATR as a ratio: `atr / close` (ATR as percentage of price) or normalize against a rolling ATR baseline (e.g., 50-day average ATR). The config should have `atr_baseline_period` to compute the rolling average ATR for comparison.
**Warning signs:** Stop loss never adapts on one market while over-adapting on another.

### Pitfall 2: DD5 High Resets on FTD
**What goes wrong:** DD counter resets on FTD (`dd_counter.reset()` clears `dd_history`). If short is entered, then an FTD fires (covering the short), the DD5 high is lost.
**Why it happens:** Reset is correct for the BUY cycle, but DD5 high may still be needed for short stop loss.
**How to avoid:** Store `dd5_high` separately on the position or engine when entering SELL state. Once the short position is opened, the DD5 high is "locked in" and doesn't change even if DD counter resets.
**Warning signs:** `dd5_high = 0` or `None` during SELL state.

### Pitfall 3: Volatility Scaling Direction
**What goes wrong:** Wider stop loss during low volatility, tighter during high volatility (inverted).
**Why it happens:** Confusing the scaling formula direction.
**How to avoid:** Clear formula: `effective_pct = base_pct * (current_atr / baseline_atr)`. When current ATR > baseline (high vol), stop widens. When current ATR < baseline (low vol), stop tightens. This is the correct and intuitive direction.
**Warning signs:** More stop-outs during calm markets, fewer during volatile markets.

### Pitfall 4: Short Stop Loss vs Short Cover Signals
**What goes wrong:** Short stop loss fires on the same day as FTD/MA50 cover signal, causing double-cover or conflicting actions.
**Why it happens:** Both are checked in the same daily loop.
**How to avoid:** Check short stop loss BEFORE checking FTD/MA50 cover in the SELL state processing. If stop loss fires, cover immediately -- don't also check FTD. Or: check both, but short stop loss has higher priority (it's a risk control).
**Warning signs:** Duplicate SHORT_COVER entries in trade log for the same date.

### Pitfall 5: DD5 High Definition Ambiguity
**What goes wrong:** Using the wrong "DD5 high" -- is it the high of the day when DD count reached 5, or the highest high among all 5 distribution days?
**Why it happens:** The rules doc says "Gia cao nhat ngay DD5" which means "highest price of DD5 day" (the day when the 5th DD occurs), not the max high of all 5 DD days.
**How to avoid:** Per rules_mdm_classic.md line 94: "Ghi nhan Gia cao nhat ngay DD5 (H_DD5)" -- this is the HIGH of the specific day when dd_count == 5. Use this single day's high, not a max across all DD days.
**Warning signs:** DD5 high is much higher than expected (if accidentally taking max of all 5 DD highs).

## Code Examples

### ATR Computation (to add to indicators.py)
```python
# Source: Standard ATR formula (Wilder, 1978)
@staticmethod
def add_atr_column(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add Average True Range column.

    True Range = max(H-L, |H-prev_C|, |L-prev_C|)
    ATR = rolling mean of True Range over period.

    Args:
        df: DataFrame with 'high', 'low', 'close' columns.
        period: ATR lookback period (default 14).

    Returns:
        DataFrame with 'atr' column added.
    """
    df = df.copy()
    prev_close = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev_close).abs()
    tr3 = (df['low'] - prev_close).abs()
    df['true_range'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = df['true_range'].rolling(window=period, min_periods=1).mean()
    return df
```

### Volatility-Adaptive Stop Loss
```python
def _get_effective_stop_pct(self, atr: float, atr_baseline: float) -> float:
    """Scale stop loss percentage by current vs baseline ATR.

    When ATR > baseline: widen stop (high volatility).
    When ATR < baseline: tighten stop (low volatility).
    Clamped to [min_pct, max_pct] range.
    """
    if atr_baseline <= 0 or atr is None:
        return self.config.stop_loss_pct

    ratio = atr / atr_baseline
    effective = self.config.stop_loss_pct * ratio

    # Clamp to reasonable range
    min_pct = self.config.stop_loss_pct * 0.5   # e.g., 0.75%
    max_pct = self.config.stop_loss_pct * 2.5   # e.g., 3.75%
    return max(min_pct, min(max_pct, effective))
```

### Short Stop Loss Check
```python
def check_short(
    self,
    current_close: float,
    dd5_high: float,
    short_entry_price: float = 0.0,
) -> StopLossResult:
    """Check short position stop loss.

    Rule: Cover short if close > DD5 high * 1.01 (1% above DD5 high).
    Per MDM classic rules section IV.4.

    Args:
        current_close: Current close price.
        dd5_high: High price of the day when DD count reached 5.
        short_entry_price: Entry price for P&L calculation.
    """
    if dd5_high <= 0:
        return StopLossResult(triggered=False, reason="No DD5 high", loss_pct=0.0)

    stop_price = dd5_high * 1.01
    loss_pct = (current_close - short_entry_price) / short_entry_price if short_entry_price > 0 else 0.0

    if current_close > stop_price:
        return StopLossResult(
            triggered=True,
            reason=f"Short stop loss: close {current_close:.2f} > DD5 high {dd5_high:.2f} * 1.01 = {stop_price:.2f}",
            loss_pct=loss_pct,
        )

    return StopLossResult(triggered=False, reason="OK", loss_pct=loss_pct)
```

### DD5 High Tracking (extend DistributionDayCounter)
```python
# In distribution_day.py -- change dd_history from list of dates to list of (date, high) tuples

def __init__(self, config: MDMConfig = None):
    self.config = config if config else MDMConfig()
    self.dd_history = []  # List of (date, high) tuples
    self.dd5_high = 0.0   # Cached DD5 high for short stop loss

def check_distribution_day(self, date, high, price_change_pct, volume_up, p_loc):
    """Now requires `high` parameter for DD5 high tracking."""
    is_type1 = self.is_distribution_day_type1(price_change_pct, volume_up)
    is_type2 = self.is_distribution_day_type2(price_change_pct, volume_up, p_loc)

    if is_type1 or is_type2:
        self.dd_history.append((date, high))
        dd_type = 1 if is_type1 else 2
        return True, dd_type

    return False, 0

def get_dd5_high(self, current_date, all_dates: list) -> float:
    """Get the high of the day when DD count reached 5 in window.

    Returns 0.0 if fewer than 5 DDs in window.
    """
    # Count DDs in window to find the 5th one
    current_idx = all_dates.index(current_date) if current_date in all_dates else -1
    if current_idx < 0:
        return 0.0
    window_start_idx = max(0, current_idx - self.config.dd_window_size + 1)
    window_dates = set(all_dates[window_start_idx:current_idx + 1])

    dd_in_window = [(d, h) for d, h in self.dd_history if d in window_dates]
    if len(dd_in_window) >= 5:
        return dd_in_window[4][1]  # High of the 5th DD
    return 0.0
```

## Config Parameters Summary

| Parameter | Default | Purpose | Location |
|-----------|---------|---------|----------|
| `stop_loss_pct` | 0.015 (was 0.025) | Base long stop loss percentage | MDMV2Config |
| `atr_period` | 14 | ATR lookback period | MDMV2Config (new) |
| `atr_baseline_period` | 50 | Rolling average ATR for normalization | MDMV2Config (new) |
| `volatility_adaptive` | True | Enable/disable ATR scaling | MDMV2Config (new) |
| `stop_loss_min_multiplier` | 0.5 | Minimum scaling factor for stop loss | MDMV2Config (new) |
| `stop_loss_max_multiplier` | 2.5 | Maximum scaling factor for stop loss | MDMV2Config (new) |
| `short_stop_pct_above_dd5` | 0.01 | Short stop: percentage above DD5 high | MDMV2Config (new) |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none -- Wave 0 must create |
| Quick run command | `.venv/Scripts/python -m pytest tests/ -x -q` |
| Full suite command | `.venv/Scripts/python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RISK-01 | Long stop loss defaults to 1.5% | unit | `.venv/Scripts/python -m pytest tests/test_stop_loss.py::test_long_stop_loss_default_1_5_pct -x` | Wave 0 |
| RISK-02 | Volatility-adaptive: wider during high-vol, tighter during low-vol | unit | `.venv/Scripts/python -m pytest tests/test_stop_loss.py::test_volatility_adaptive_scaling -x` | Wave 0 |
| RISK-03 | Short stop loss at 1% above DD5 high | unit | `.venv/Scripts/python -m pytest tests/test_stop_loss.py::test_short_stop_loss_dd5_high -x` | Wave 0 |
| SHORT-03 | Same as RISK-03 -- triggers short cover | unit | `.venv/Scripts/python -m pytest tests/test_stop_loss.py::test_short_stop_triggers_cover -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/Scripts/python -m pytest tests/test_stop_loss.py -x -q`
- **Per wave merge:** `.venv/Scripts/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_stop_loss.py` -- covers RISK-01, RISK-02, RISK-03, SHORT-03
- [ ] `tests/conftest.py` -- shared fixtures (sample OHLCV data, config objects)
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest]` -- test config

## Open Questions

1. **ATR Baseline Period for VN30 vs NASDAQ**
   - What we know: ATR(14) is standard. Baseline period (50-day rolling average of ATR) is reasonable.
   - What's unclear: Whether VN30's 7% daily price limit affects ATR meaningfully (capped true range on limit days).
   - Recommendation: Use same ATR formula for both. VN30 limit days will naturally show smaller ATR, which is correct behavior (the market literally cannot move more than 7%).

2. **DD5 High When No DD5 Exists in SELL State**
   - What we know: SELL state can be entered via MA50 breakdown or cash deterioration (not only via DD5).
   - What's unclear: What should short stop loss be when there is no DD5 high (dd_count < 5)?
   - Recommendation: If no DD5 high is available, short stop loss should be disabled (return `triggered=False`). The other cover mechanisms (FTD, MA50 breakout) still apply. Log a warning.

3. **Interaction With Two-Phase Commit**
   - What we know: Stop loss fires in the V2 processing step before the filter evaluation.
   - What's unclear: Should the indicator filter be able to VETO a stop loss exit?
   - Recommendation: No. Stop loss is a hard risk control -- it should not be vetoed by the indicator filter. Current code already handles this correctly: stop loss check happens before process_day, and process_day checks stop_loss_triggered with highest priority (line 263-265 of position_manager.py).

## Project Constraints (from CLAUDE.md)

- Python 3.10+, pandas >= 2.0.0, numpy >= 1.24.0
- 4-space indentation, snake_case naming, Google-style docstrings
- Dataclass for config (MDMV2Config), StopLossResult
- No external dependencies beyond what's already installed
- File-based storage, no database
- Must work for both NASDAQ and VN30 data
- GSD workflow enforcement: changes through GSD commands

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_hybrid/stop_loss.py` -- current StopLossChecker implementation (long only, 3 rules)
- `strategies/mdm_hybrid/config.py` -- current `stop_loss_pct: 0.025` default
- `strategies/mdm_hybrid/position_manager.py` -- V2PositionManager with SELL state, cover_short() method
- `strategies/mdm_hybrid/distribution_day.py` -- DistributionDayCounter with dd_history (dates only)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` -- daily loop integration point for stop loss
- `docs/rules_mdm_classic.md` -- Dr. K's rules: 1.5% long stop loss (section III.1), short stop loss 1% above DD5 high (section IV.4)

### Secondary (MEDIUM confidence)
- ATR formula is standard Wilder (1978) -- well-established, no variation concerns
- Volatility-adaptive scaling via ATR ratio is a common professional approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure Python + pandas/numpy
- Architecture: HIGH -- existing StopLossChecker interface is clean, extension path is clear
- Pitfalls: HIGH -- identified from reading actual codebase (DD reset, ATR scale, priority conflicts)
- DD5 high tracking: HIGH -- rules_mdm_classic.md is explicit about the definition

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no external API changes)
