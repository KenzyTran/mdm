# Phase 13: Hybrid Engine Integration - Research

**Researched:** 2026-03-29
**Domain:** Trading engine pipeline wiring (Python, pandas, state machine + indicator filter)
**Confidence:** HIGH

## Summary

Phase 13 wires the Propose-Filter-Decide pipeline into `HybridEngine`: the v2 state machine mutates as normal, then the engine compares old vs new state to form a proposal, runs `IndicatorFilter.evaluate()` on the proposal, and acts on the verdict (CONFIRM keeps mutations, VETO restores snapshot, OVERRIDE forces Cash). A backtest entry point script produces a detailed signal log CSV.

All building blocks exist and are tested: snapshot/restore (Phase 11), IndicatorFilter with evaluate() returning Verdict enum (Phase 12), build_indicator_dataframe() for EMA/MACD columns (Phase 8), and the two-phase commit placeholder block at lines 252-261 of `mdm_hybrid_engine.py`. The implementation is primarily wiring -- no new algorithms or data structures needed.

**Primary recommendation:** Implement the pipeline in the existing placeholder block (lines 252-261), add indicator columns via `build_indicator_dataframe()` in the data prep section, and create `scripts/run_hybrid_backtest.py` following the pattern of `scripts/run_backtest.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Diff-based approach. State machine mutates as normal, then engine compares old_state (from snapshot) vs new_state. If state changed, that's the proposal. Filter evaluates the proposal; if VETO, restore snapshot to rollback.
- **D-02:** On days with no state change, still run filter to check for cash insertion (see D-05). Proposal = "confirm current state".
- **D-03:** Wire into existing two-phase commit block at lines 252-261 of `mdm_hybrid_engine.py`. Minimal refactoring of the mutation flow.
- **D-04:** OVERRIDE = force Cash. Regardless of what state machine proposed, if filter returns OVERRIDE, engine forces transition to Cash state. No direct Buy->Sell or Sell->Buy overrides.
- **D-05:** Aligns with Dr. K's philosophy from 2012 webinar: "favor cash positions" in uncertain environments. Phase 15 can upgrade override logic if needed.
- **D-06:** Use IndicatorFilter itself for degradation detection. Every day the state machine does NOT propose a state change, run filter with proposal = "confirm current state". If filter returns VETO or OVERRIDE, degrade to Cash.
- **D-07:** Cash insertion applies when in BUY state. If in SELL state and filter says VETO/OVERRIDE on "confirm SELL", also degrade to Cash (symmetric).
- **D-08:** No separate degradation logic or threshold -- reuse existing majority-vote evaluation from Phase 12.
- **D-09:** `scripts/run_hybrid_backtest.py` produces both: (1) detailed CSV signal log with columns `date, old_state, proposed, verdict, final_state, action`, and (2) console summary with performance metrics (win rate, drawdown, trade count).
- **D-10:** Signal log CSV enables Phase 14 diagnosis: "proposed X, filter said Y, final Z" for every trading day.

### Claude's Discretion
- Exact proposal representation passed to IndicatorFilter (string label vs enum)
- How to extract old_state from snapshot vs storing it before mutation
- Console summary format and which metrics to show
- Signal log CSV filename and location convention
- Whether to add verdict/proposal columns to the main results DataFrame or keep them only in the signal log
- How to handle the "always confirm" regression mode (filter_enabled=False should bypass all new logic)

### Deferred Ideas (OUT OF SCOPE)
- Contextual transitions (Buy->Cash->Sell depending on prior state) -- Phase 15
- Parameter tuning of filter thresholds -- Phase 14 after validation baseline
- Leading stocks confirmation as additional filter input -- out of scope (no breadth data available)
- "Banding width" / volatility-aware filter activation -- Phase 15 advanced features
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HYB-03 | Signal confirmation logic -- state machine proposes, indicator filter confirms/blocks based on boolean conditions | IndicatorFilter.evaluate() exists with CONFIRM/VETO verdicts; wiring into placeholder block at lines 252-261; diff-based proposal extraction from snapshot comparison |
| HYB-04 | Signal override logic -- indicators can override signal when conditions are sufficiently strong | Verdict.OVERRIDE exists (3+ active, 0 agreement); D-04 locks OVERRIDE = force Cash; position_manager has exit_to_cash() and enter_sell()->Cash path |
| HYB-05 | Cash state insertion based on indicator degradation (post-2019 logic) | D-06/D-07: run filter on "confirm current state" proposal every day; VETO/OVERRIDE on confirm -> degrade to Cash; symmetric for BUY and SELL states |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, row iteration | Already in use throughout project |
| numpy | >= 1.24.0 | Numeric operations | Already in use throughout project |
| copy | stdlib | deepcopy for snapshot/restore | Already used in mdm_hybrid_engine.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test framework | All test files |

No new dependencies required. This phase uses only existing project libraries.

## Architecture Patterns

### Recommended Modification Structure
```
strategies/mdm_hybrid/
    mdm_hybrid_engine.py    # MODIFY: wire filter into placeholder block
    indicator_filter.py     # READ ONLY: evaluate() already complete
    position_manager.py     # READ ONLY: enter_buy/exit_to_cash/enter_sell exist
    config.py               # MINOR: possibly no changes needed (filter_enabled toggle exists)

core/
    indicators.py           # READ ONLY: build_indicator_dataframe() exists

scripts/
    run_hybrid_backtest.py  # NEW: backtest entry point

tests/
    test_hybrid_engine.py   # MODIFY: add integration tests for filter pipeline
```

### Pattern 1: Diff-Based Proposal Extraction (D-01)
**What:** Capture old_state before mutation, let state machine mutate, compare old vs new to derive proposal.
**When to use:** Every daily iteration in the main loop.
**Example:**
```python
# Before mutation (line ~131, after snapshot)
old_state = self.position_manager.get_state()

# ... existing mutation code runs (steps 1-5) ...

new_state = self.position_manager.get_state()

# Derive proposal
if new_state != old_state:
    # State changed: proposal is the new state
    proposal = new_state.value  # "BUY", "CASH", or "SELL"
else:
    # No change: proposal is "confirm current state"
    proposal = f"CONFIRM_{old_state.value}"  # or just old_state.value
```

### Pattern 2: Filter Decision Block (D-03, lines 252-261)
**What:** Replace placeholder with actual filter evaluation and response logic.
**When to use:** After state machine mutation, before DataFrame update.
**Example:**
```python
if self.config.two_phase_enabled and self.config.filter_enabled:
    indicator_filter = IndicatorFilter(self.config.filter_config)

    if new_state != old_state:
        proposal = new_state.value
    else:
        proposal = old_state.value  # "confirm current state"

    verdict = indicator_filter.evaluate(row, proposal, old_state)

    if new_state != old_state:
        # State machine proposed a change
        if verdict == Verdict.VETO:
            self._restore_components(snapshot)
            new_state = self.position_manager.get_state()
            action = ''
        elif verdict == Verdict.OVERRIDE:
            # Force to Cash regardless of proposal
            if new_state != V2MarketState.CASH:
                self._restore_components(snapshot)
                self.position_manager.exit_to_cash(close, date, "OVERRIDE: indicator disagreement")
                new_state = V2MarketState.CASH
                action = f"CASH exit: filter override"
    else:
        # No state change proposed -- check for cash insertion (D-06)
        if verdict in (Verdict.VETO, Verdict.OVERRIDE):
            if old_state == V2MarketState.BUY:
                self.position_manager.exit_to_cash(close, date, "indicator degradation")
                new_state = V2MarketState.CASH
                action = f"CASH exit: indicator degradation"
            elif old_state == V2MarketState.SELL:
                # Symmetric: SELL degrades to CASH too (D-07)
                self.position_manager.exit_to_cash(close, date, "indicator degradation from SELL")
                new_state = V2MarketState.CASH
                action = f"CASH: indicator degradation from SELL"
```

### Pattern 3: Regression Bypass (filter_enabled=False)
**What:** When filter_enabled is False, the entire filter block is skipped, producing identical output to v2.
**When to use:** Default config, backward compatibility, regression testing.
**Example:**
```python
# The existing condition at line 253 already handles this:
if self.config.two_phase_enabled and self.config.filter_enabled:
    # ... filter logic ...
# When filter_enabled=False, this block never executes.
# State machine mutations are kept as-is. Identical to v2.
```

### Pattern 4: Indicator Column Integration
**What:** Add EMA/MACD columns to the DataFrame before the daily loop so rows have indicator data for the filter.
**When to use:** In the data preparation section of `run()`, after existing indicator computations.
**Example:**
```python
# In HybridEngine.run(), after existing Indicators.add_* calls:
from core.indicators import build_indicator_dataframe
if self.config.filter_enabled:
    df = build_indicator_dataframe(df)
    # This adds: ema9, ema21, ema55, ma200, macd, macd_signal, macd_histogram
```

### Anti-Patterns to Avoid
- **Instantiating IndicatorFilter per row:** Create once before the loop, not inside it. The filter is stateless, so one instance suffices.
- **Modifying IndicatorFilter.evaluate():** The filter is Phase 12's deliverable and is read-only for this phase. All new logic goes in the engine.
- **Using exit_to_cash from SELL state:** V2PositionManager.exit_to_cash() records a CASH_EXIT trade with P&L. But SELL state has no position. For SELL->CASH, need to set state directly or use a new method. This is a critical integration point.
- **Calling build_indicator_dataframe() unconditionally:** Only call when filter_enabled=True to avoid unnecessary computation in regression mode.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EMA/MACD computation | Custom indicator code | `core.indicators.build_indicator_dataframe()` | Already tested, TradingView-parity verified |
| Snapshot/restore | Manual state tracking | `_snapshot_components()` / `_restore_components()` | Deep copy of all 4 components, Phase 11 tested |
| Majority vote logic | Custom voting | `IndicatorFilter.evaluate()` | Already handles bullish/bearish conditions, NaN, threshold |
| Performance metrics | Custom P&L calcs | `HybridEngine.summary()` + existing PerformanceAnalyzer | Already implemented |

## Common Pitfalls

### Pitfall 1: SELL State Has No Position to "Exit"
**What goes wrong:** Calling `exit_to_cash(close, date, reason)` from SELL state triggers P&L calculation with buy_price=0, producing garbage trade records.
**Why it happens:** `exit_to_cash()` assumes a position exists (BUY->CASH). SELL state has no position.
**How to avoid:** For SELL->CASH transition on indicator degradation, set `position.state = V2MarketState.CASH` directly or create a `degrade_to_cash()` method that only changes state without P&L recording. Or record a special trade type like `SELL_TO_CASH`.
**Warning signs:** Trades with pnl=0.0 or buy_price=0.0 in the trade log.

### Pitfall 2: Proposal Direction for "Confirm Current State"
**What goes wrong:** Passing "BUY" as proposal for "confirm BUY state" triggers bullish condition checks. If bullish conditions fail (VETO), the engine degrades to Cash even though nothing was changing. This is actually the INTENDED behavior per D-06.
**Why it matters:** Must be clear that "confirm BUY" means "are conditions still bullish enough to stay in BUY?" and "confirm SELL" means "are conditions still bearish enough to stay in SELL?"
**How to avoid:** Use the current state's value as the proposal string (e.g., "BUY" for confirm-BUY). The filter naturally checks the right direction.
**Warning signs:** Test that confirm-CASH does NOT trigger degradation (already in CASH, nothing to degrade to).

### Pitfall 3: Indicator Columns Missing in DataFrame
**What goes wrong:** `IndicatorFilter.evaluate()` accesses `row['ema55']`, `row['macd_histogram']`, etc. If `build_indicator_dataframe()` was not called, KeyError crashes the loop.
**Why it happens:** The existing HybridEngine.run() uses `strategies/mdm_hybrid/indicators.py` for MA10/MA50 but does NOT call `core/indicators.py` for EMA/MACD.
**How to avoid:** Call `build_indicator_dataframe(df)` in the data prep section when filter_enabled=True. Guard with a check for required columns.
**Warning signs:** KeyError on 'ema55', 'ema9', 'ema21', 'macd_histogram'.

### Pitfall 4: Double State Mutation on Override
**What goes wrong:** State machine already mutated (e.g., BUY->CASH via DD count). Filter returns OVERRIDE. Restoring snapshot then forcing Cash produces the same result, but the trade record is different (DD count reason vs override reason).
**Why it happens:** OVERRIDE always forces Cash (D-04). If the state machine already proposed Cash, OVERRIDE is redundant but produces a different trade log entry.
**How to avoid:** When state machine proposed Cash and filter says OVERRIDE, keep the state machine's transition (it's already going to Cash). Only override when the proposal differs from Cash.
**Warning signs:** Duplicate CASH_EXIT trade records for the same date.

### Pitfall 5: CASH State Confirmation Should Not Degrade
**What goes wrong:** When current state is CASH and filter evaluates "confirm CASH" with bearish conditions, it might return CONFIRM (bearish conditions agree with CASH). But if it returns VETO/OVERRIDE, there's nowhere to degrade to -- already in CASH.
**Why it happens:** D-06/D-07 only apply to BUY and SELL states.
**How to avoid:** Skip degradation check when old_state is CASH. Only run cash insertion for BUY and SELL states.
**Warning signs:** Infinite loops or meaningless "CASH exit from CASH" actions.

### Pitfall 6: Signal Log CSV Must Include ALL Days
**What goes wrong:** Only logging days where state changes, missing the majority of trading days.
**Why it happens:** D-10 says signal log enables Phase 14 diagnosis for "every trading day".
**How to avoid:** Record proposal/verdict/final_state for every row in the DataFrame, not just transition days.
**Warning signs:** Signal log CSV with far fewer rows than trading days.

## Code Examples

### Backtest Entry Point Pattern (from existing `scripts/run_backtest.py`)
```python
# Source: scripts/run_backtest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.config import HybridConfig
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine

loader = DataLoader('nasdaq')
df = loader.load()
# Indicators added inside engine when filter_enabled=True

config = HybridConfig(filter_enabled=True)
engine = HybridEngine(config)
results = engine.run(df)

# Signal log CSV
signal_cols = ['date', 'old_state', 'proposed', 'verdict', 'final_state', 'action']
results[signal_cols].to_csv('hybrid_signal_log.csv', index=False)

# Console summary
summary = engine.summary()
print(f"Total trades: {summary['total_completed']}")
print(f"Win rate: {summary['win_rate']:.1%}")
```

### Position Manager State Transitions Available
```python
# Source: strategies/mdm_hybrid/position_manager.py
# BUY -> CASH: exit_to_cash(sell_price, sell_date, reason) -- records P&L
# CASH -> SELL: enter_sell(date, reason) -- no position
# SELL -> BUY: enter_buy(buy_price, buy_date, buy_day_low, signal_type)
# CASH -> BUY: enter_buy(...)

# CRITICAL: No SELL->CASH method exists.
# For SELL degradation to CASH (D-07), need to handle state change
# without P&L calculation. Options:
# 1. Direct: self.position_manager.position.state = V2MarketState.CASH
# 2. New method: add degrade_sell_to_cash(date, reason) to V2PositionManager
```

### IndicatorFilter.evaluate() Signature
```python
# Source: strategies/mdm_hybrid/indicator_filter.py
def evaluate(self, row, proposal: str, current_state=None) -> Verdict:
    # proposal: "BUY" -> checks bullish conditions
    # proposal: "SELL" or "CASH" -> checks bearish conditions
    # Returns: Verdict.CONFIRM, Verdict.VETO, or Verdict.OVERRIDE
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v2 state machine only | Hybrid: state machine + indicator filter | Phase 11-13 (v3.0) | Two-phase commit prevents DD counter corruption |
| Binary BUY/SELL | 3-state BUY/CASH/SELL | Phase 4 (v1.0) | Cash as intermediate state for uncertain markets |
| Placeholder filter block | Full Propose-Filter-Decide pipeline | Phase 13 (this phase) | Filter can veto, override, or insert Cash |

## Open Questions

1. **SELL->CASH transition method**
   - What we know: `exit_to_cash()` assumes a BUY position exists and calculates P&L. SELL state has no position.
   - What's unclear: Best way to transition SELL->CASH without corrupting trade records.
   - Recommendation: Add a small `degrade_to_cash(date, reason)` method to V2PositionManager that changes state and records a trade of type `STATE_DEGRADE` without P&L. This is the cleanest approach. Alternatively, set `position.state` directly and record a manual trade entry.

2. **Proposal string for "confirm current state"**
   - What we know: IndicatorFilter.evaluate() expects "BUY", "SELL", or "CASH" as proposal string.
   - What's unclear: For "confirm BUY", should proposal be "BUY" (which checks bullish conditions)?
   - Recommendation: Use the current state's `.value` as proposal. "BUY" checks bullish (correct: are conditions still bullish?). "SELL" checks bearish (correct: are conditions still bearish?). "CASH" would need special handling -- per D-06/D-07, only BUY and SELL states trigger degradation checks.

3. **Where to add indicator columns**
   - What we know: `build_indicator_dataframe()` adds ema9/21/55, ma200, macd columns. HybridEngine.run() has a data prep section (lines 89-99).
   - What's unclear: Whether to merge with existing indicator calls or call separately.
   - Recommendation: Call `build_indicator_dataframe()` as the FIRST indicator step (it works on raw OHLCV), then let existing `Indicators.add_*` calls overlay their columns. Or call it after existing calls -- the EMA/MACD columns won't conflict with MA10/MA50.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (conftest.py in tests/) |
| Quick run command | `uv run python -m pytest tests/test_hybrid_engine.py -x -q` |
| Full suite command | `uv run python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HYB-03 | Filter confirms BUY proposal when bullish conditions met | unit | `uv run python -m pytest tests/test_hybrid_engine.py::test_filter_confirms_buy -x` | Wave 0 |
| HYB-03 | Filter vetoes BUY proposal, snapshot restored | unit | `uv run python -m pytest tests/test_hybrid_engine.py::test_filter_vetoes_buy_restores_snapshot -x` | Wave 0 |
| HYB-03 | Regression: filter_enabled=False matches v2 | integration | `uv run python -m pytest tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq -x` | Exists |
| HYB-04 | Override forces Cash from BUY state | unit | `uv run python -m pytest tests/test_hybrid_engine.py::test_override_forces_cash_from_buy -x` | Wave 0 |
| HYB-04 | Override forces Cash from SELL state | unit | `uv run python -m pytest tests/test_hybrid_engine.py::test_override_forces_cash_from_sell -x` | Wave 0 |
| HYB-05 | Cash insertion on BUY with bearish indicators | unit | `uv run python -m pytest tests/test_hybrid_engine.py::test_cash_insertion_from_buy -x` | Wave 0 |
| HYB-05 | Cash insertion on SELL with non-bearish indicators | unit | `uv run python -m pytest tests/test_hybrid_engine.py::test_cash_insertion_from_sell -x` | Wave 0 |
| HYB-05 | No cash insertion when already in CASH | unit | `uv run python -m pytest tests/test_hybrid_engine.py::test_no_degradation_from_cash -x` | Wave 0 |
| D-09 | Backtest script runs end-to-end, produces CSV | smoke | `uv run python scripts/run_hybrid_backtest.py` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_hybrid_engine.py -x -q`
- **Per wave merge:** `uv run python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_hybrid_engine.py` -- add filter pipeline integration tests (HYB-03, HYB-04, HYB-05)
- [ ] `scripts/run_hybrid_backtest.py` -- new file for smoke test
- [ ] Test helper: synthetic DataFrame WITH indicator columns (ema9, ema21, ema55, macd_histogram) for filter testing

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` -- current engine code, placeholder block at lines 252-261
- `strategies/mdm_hybrid/indicator_filter.py` -- IndicatorFilter.evaluate() signature and verdict logic
- `strategies/mdm_hybrid/position_manager.py` -- V2PositionManager state transitions and trade recording
- `strategies/mdm_hybrid/config.py` -- HybridConfig with filter_enabled flag
- `core/indicators.py` -- build_indicator_dataframe() for EMA/MACD column computation
- `tests/test_hybrid_engine.py` -- existing regression and snapshot tests
- `tests/test_indicator_filter.py` -- existing filter verdict tests

### Secondary (MEDIUM confidence)
- `.planning/phases/13-hybrid-engine-integration/13-CONTEXT.md` -- locked decisions D-01 through D-10

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing project libraries
- Architecture: HIGH -- all building blocks exist and are tested, wiring pattern is clear from code inspection
- Pitfalls: HIGH -- identified from direct code reading (SELL->CASH gap, missing indicator columns, double mutation)

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable, no external dependency changes expected)
