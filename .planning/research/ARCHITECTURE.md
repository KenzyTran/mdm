# Architecture Research

**Domain:** Hybrid MDM Engine (State Machine + Indicator Filter)
**Researched:** 2026-03-29
**Confidence:** HIGH

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Entry Points                                   │
│  scripts/run_hybrid_backtest.py    notebooks/hybrid_validation.ipynb  │
├─────────────────────────────────────────────────────────────────────┤
│                    strategies/mdm_hybrid/                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │  HybridEngine    │  │  IndicatorFilter │  │  HybridConfig     │  │
│  │  (orchestrator)  │──│  (confirm/veto)  │  │  (all params)     │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────────────────┘  │
│           │                     │                                    │
│  ┌────────┴─────────────────────┴─────────────────────────────────┐  │
│  │               HybridPositionManager                            │  │
│  │  BUY/CASH/SELL + indicator-gated transitions                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                    Reused from existing code                         │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │ core/      │  │ strategies/  │  │ core/        │                 │
│  │ indicators │  │ mdm_v2/      │  │ feature_     │                 │
│  │ .py        │  │ components   │  │ snapshot.py  │                 │
│  └────────────┘  └──────────────┘  └──────────────┘                 │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │ core/      │  │ core/signal_ │  │ analysis/    │                 │
│  │ data_      │  │ comparator   │  │ validate_    │                 │
│  │ loader.py  │  │ .py          │  │ discovery.py │                 │
│  └────────────┘  └──────────────┘  └──────────────┘                 │
├─────────────────────────────────────────────────────────────────────┤
│                         Data Layer                                   │
│  data/nasdaq/    data/signals/    data/vn30/                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | New vs Reused |
|-----------|----------------|---------------|
| `HybridEngine` | Orchestrate daily loop: compute classic signals, apply indicator filters, feed to position manager | **NEW** |
| `IndicatorFilter` | Evaluate indicator conditions (EMA crossovers, MACD state, MA200 trend) and return confirm/veto/override verdict | **NEW** |
| `HybridConfig` | Hold all parameters: classic DD/FTD params + indicator filter thresholds + filter mode weights | **NEW** |
| `HybridPositionManager` | 3-state machine (BUY/CASH/SELL) with indicator-gated transitions | **NEW** (extends V2 logic) |
| `core/indicators.py` | `build_indicator_dataframe()` -- EMA 9/21/55, MA200, MACD, HA Smoothed | Reused as-is |
| `strategies/mdm_v2/` components | DD counter, rally tracker, FTD detector, stop loss checker | Reused (imported, not copied) |
| `core/signal_comparator.py` | `extract_model_signals()`, `compare_signals()`, divergence classification | Reused as-is |
| `core/feature_snapshot.py` | `extract_feature_snapshot()` for validation against 962 signals | Reused as-is |
| `core/data_loader.py` | `DataLoader('nasdaq').load()` for OHLCV data | Reused as-is |
| `analysis/validate_discovery.py` | Scoring, confusion matrices, cross-era validation | Reused as-is |

## Recommended Project Structure

```
strategies/
├── mdm_classic/          # Existing -- no changes
├── mdm_v2/               # Existing -- no changes, components imported by hybrid
│   ├── distribution_day.py
│   ├── rally_attempt.py
│   ├── ftd_signal.py
│   ├── stop_loss.py
│   ├── indicators.py     # Classic indicators (MA50, MA10, p_loc etc.)
│   └── ...
├── mdm_hybrid/           # NEW strategy package
│   ├── __init__.py
│   ├── config.py         # HybridConfig dataclass
│   ├── indicator_filter.py   # IndicatorFilter class
│   ├── position_manager.py   # HybridPositionManager
│   ├── hybrid_engine.py      # HybridEngine orchestrator
│   └── performance.py        # Reuse/extend V2PerformanceAnalyzer
├── vsa/                  # Existing -- no changes
```

### Structure Rationale

- **`strategies/mdm_hybrid/`:** Separate package follows existing convention (mdm_classic, mdm_v2, vsa are all separate packages). No code copied from v2 -- components are imported across packages.
- **Import v2 components, don't copy:** DD counter, rally tracker, FTD detector, and stop loss checker from `strategies/mdm_v2/` are mature and tested. The hybrid engine imports them directly rather than duplicating code. This avoids drift between v2 and hybrid implementations.
- **`core/indicators.py` stays untouched:** The `build_indicator_dataframe()` function already computes all needed indicators (EMA 9/21/55, MA200, MACD, HA Smoothed). The hybrid engine calls it in its data preparation step.

## Architectural Patterns

### Pattern 1: Propose-Filter-Decide Pipeline

**What:** The classic state machine (DD counting, FTD detection, rally attempts) proposes a signal transition. The indicator filter evaluates current indicator state and returns a verdict (CONFIRM, VETO, OVERRIDE). The position manager makes the final state transition based on both inputs.

**When to use:** This is the core pattern for every trading day processed by the hybrid engine.

**Trade-offs:** Adds one layer of indirection vs. v2's direct signal-to-action flow. But this is exactly the architectural need -- separating "what the classic rules say" from "what the indicators say" enables independent tuning of each layer.

**Example:**
```python
# In HybridEngine.run(), inside the daily loop:

# Step 1: Classic state machine proposes action
classic_proposal = self._compute_classic_proposal(row, current_state)
# Returns: Proposal(action="BUY", reason="FTD on rally day 5", confidence=1.0)
#      or: Proposal(action="HOLD", reason="no signal", confidence=1.0)

# Step 2: Indicator filter evaluates
filter_verdict = self.indicator_filter.evaluate(
    row,                    # current day's data with all indicators
    classic_proposal,       # what the classic rules want to do
    current_state,          # current position state
)
# Returns: Verdict(decision="CONFIRM"|"VETO"|"OVERRIDE", reason="...", override_action="...")

# Step 3: Position manager applies final decision
final_action = self._resolve_action(classic_proposal, filter_verdict)
new_state, action_str = self.position_manager.process_day(...)
```

### Pattern 2: Indicator Filter as Rule Evaluator

**What:** The `IndicatorFilter` class encapsulates the discovered decision tree rules as explicit conditional logic. Each rule is a method that returns a boolean. The `evaluate()` method combines rules based on the current state and proposed transition.

**When to use:** When the indicator filter needs to confirm or veto a classic signal.

**Trade-offs:** Hardcoded rules are less flexible than a trained decision tree, but more debuggable, more testable, and easier to tune per-parameter. The discovered rules (from Phase 9/10) serve as the starting point; human judgment refines them.

**Example:**
```python
class IndicatorFilter:
    """Evaluate indicator conditions to confirm/veto/override classic signals."""

    def __init__(self, config: HybridConfig):
        self.config = config

    def is_bullish_ema_stack(self, row: pd.Series) -> bool:
        """EMA 9 > EMA 21 > EMA 55 (full bullish alignment)."""
        return row['ema9'] > row['ema21'] > row['ema55']

    def is_macd_bullish(self, row: pd.Series) -> bool:
        """MACD line above signal line."""
        return row['macd'] > row['macd_signal']

    def is_above_ma200(self, row: pd.Series) -> bool:
        """Close above MA 200 (long-term uptrend)."""
        if pd.isna(row.get('ma200')):
            return True  # Not enough data yet, don't block
        return row['close'] > row['ma200']

    def evaluate(self, row, proposal, current_state) -> Verdict:
        """Combine rules based on state and proposed action."""
        ...
```

### Pattern 3: Config Inheritance with Override

**What:** `HybridConfig` extends `MDMV2Config` by composition (contains a v2 config) plus adds indicator filter parameters. This allows the hybrid engine to pass the v2 config subset to imported v2 components unchanged.

**When to use:** Constructing the hybrid engine and its sub-components.

**Trade-offs:** Composition over inheritance avoids diamond problem if config hierarchies grow. Slightly more verbose than subclassing, but clearer ownership.

**Example:**
```python
@dataclass
class HybridConfig:
    """Configuration for the hybrid MDM engine."""

    # Classic state machine parameters (delegated to v2 components)
    v2: MDMV2Config = field(default_factory=MDMV2Config)

    # Indicator filter parameters
    require_bullish_ema_for_buy: bool = True     # EMA9 > EMA21 for FTD confirmation
    require_macd_confirm_for_buy: bool = False   # MACD above signal for buy
    require_above_ma200_for_buy: bool = True     # Close > MA200 for buy
    ema_veto_sell: bool = True                   # Bullish EMA stack vetoes sell signal
    macd_override_to_cash: bool = True           # MACD cross-down overrides to Cash

    # Filter behavior
    filter_mode: str = "confirm"  # "confirm" (filter only confirms/vetoes)
                                   # "override" (filter can also generate signals)
                                   # "hybrid" (weighted combination)

    name: str = "hybrid_default"
```

## Data Flow

### Daily Processing Flow (Single Day)

```
OHLCV Row (with all indicators pre-computed)
    |
    v
[Classic Components]
    |-- RallyAttemptTracker.process_day() --> rally_day, is_day1
    |-- FTDSignalDetector.check_ftd()     --> is_ftd, ftd_price
    |-- DistributionDayCounter.check_dd() --> dd_count, is_dd
    |-- StopLossChecker.check()           --> stop_loss_triggered
    |
    v
[Classic Proposal]
    action: BUY|SELL|CASH|HOLD
    reason: "FTD on day 5" | "DD count 5" | "stop loss" | ...
    |
    v
[IndicatorFilter.evaluate()]
    |-- Check EMA stack alignment
    |-- Check MACD state
    |-- Check MA200 trend
    |-- Check HA Smoothed color
    |
    v
[Filter Verdict]
    decision: CONFIRM|VETO|OVERRIDE
    reason: "bullish EMA confirms buy" | "bearish MACD vetoes buy" | ...
    override_action: (only if OVERRIDE) "CASH" | "SELL"
    |
    v
[Resolve Action]
    Combine proposal + verdict --> final_action
    |
    v
[HybridPositionManager.process_day()]
    Apply state transition: BUY/CASH/SELL
    Record trade if position changes
    |
    v
[Update DataFrame row with state, action, indicators]
```

### Full Pipeline Data Flow

```
DataLoader('nasdaq').load()
    |
    v
build_indicator_dataframe(ohlcv)     # core/indicators.py
    |-- Adds: ema9, ema21, ema55, ma200, macd, macd_signal,
    |         macd_histogram, ha_smooth_*
    |
    v
Indicators.add_*() from mdm_v2      # Classic indicators: MA50, MA10, p_loc, etc.
    |
    v
DataFrame with ALL columns (OHLCV + classic indicators + core indicators)
    |
    v
HybridEngine.run(df)                 # Day-by-day processing loop
    |
    v
results_df with state/action columns
    |
    v
[Validation Path]                     [Performance Path]
extract_model_signals()               get_trades() -> trade_df
compare_signals(model, published)     equity_curve, Sharpe, drawdown
confusion_matrix, match_rate          win_rate, total_return
```

### Key Data Flows

1. **Indicator merge:** `build_indicator_dataframe()` from `core/indicators.py` adds EMA/MACD/HA columns. Then `Indicators.add_*()` from `strategies/mdm_v2/indicators.py` adds classic columns (MA50, MA10, p_loc, prev_columns, change_columns). Both run before the daily loop, producing a single wide DataFrame.

2. **Cross-package import:** The hybrid engine imports DD counter, rally tracker, FTD detector, and stop loss from `strategies.mdm_v2`. These components accept `MDMV2Config` (aliased as `MDMConfig` in v2's config.py). The hybrid engine passes `self.config.v2` to these constructors.

3. **Validation reuse:** After `HybridEngine.run()` produces results, `core/signal_comparator.extract_model_signals()` works unchanged because it maps "BUY"/"CASH"/"SELL" states to signals (already in `STATE_TO_SIGNAL` dict). `compare_signals()` and `classify_divergences()` work without modification.

## Integration Points

### Existing Modules Consumed (No Changes Needed)

| Module | What Hybrid Uses | Interface |
|--------|------------------|-----------|
| `core/data_loader.py` | `DataLoader('nasdaq').load()` | Returns DataFrame `[date, open, high, low, close, volume]` |
| `core/indicators.py` | `build_indicator_dataframe(ohlcv)` | Returns DataFrame with 11 added indicator columns |
| `core/signal_loader.py` | `load_signal_fixture(path)` | Returns DataFrame `[date, signal, gain_loss_pct]` |
| `core/signal_comparator.py` | `extract_model_signals()`, `compare_signals()` | Works with any engine outputting `state` column with BUY/CASH/SELL values |
| `core/feature_snapshot.py` | `extract_feature_snapshot()` | For side-by-side comparison with discovered rules |
| `analysis/validate_discovery.py` | `score_predictions()`, confusion matrices | For comparing hybrid accuracy vs pure decision tree |
| `strategies/mdm_v2/distribution_day.py` | `DistributionDayCounter(config)` | Accepts MDMV2Config, call `.check_distribution_day()` per day |
| `strategies/mdm_v2/rally_attempt.py` | `RallyAttemptTracker(config)` | Accepts MDMV2Config, call `.process_day()` per day |
| `strategies/mdm_v2/ftd_signal.py` | `FTDSignalDetector(config)` | Accepts MDMV2Config, call `.check_ftd()`, `.check_ma50_breakout()` |
| `strategies/mdm_v2/stop_loss.py` | `StopLossChecker(config)` | Accepts MDMV2Config, call `.check()` per day |
| `strategies/mdm_v2/indicators.py` | `Indicators.add_*()` static methods | Add classic indicator columns to DataFrame |

### New Components to Build

| Component | File | Dependencies | Purpose |
|-----------|------|--------------|---------|
| `HybridConfig` | `strategies/mdm_hybrid/config.py` | `strategies.mdm_v2.config.MDMV2Config` | Compose v2 config + indicator filter params |
| `IndicatorFilter` | `strategies/mdm_hybrid/indicator_filter.py` | `HybridConfig`, pandas | Evaluate indicator conditions, return verdicts |
| `HybridPositionManager` | `strategies/mdm_hybrid/position_manager.py` | `HybridConfig`, pandas | 3-state machine with indicator-gated transitions |
| `HybridEngine` | `strategies/mdm_hybrid/hybrid_engine.py` | All above + v2 components + core/indicators | Orchestrate daily loop |
| Entry script | `scripts/run_hybrid_backtest.py` | `HybridEngine`, core loaders, signal comparator | Run backtest and print comparison report |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| HybridEngine <-> v2 components | Direct method calls via imported instances | Pass `config.v2` to v2 component constructors |
| HybridEngine <-> IndicatorFilter | `evaluate(row, proposal, state)` -> `Verdict` | Stateless evaluation per row -- no internal state in filter |
| HybridEngine <-> core/indicators | `build_indicator_dataframe(df)` before loop | One-time call during data preparation |
| HybridEngine <-> signal_comparator | Post-run: `extract_model_signals(results)` | Same interface as v2 engine output |
| Classic indicators <-> Core indicators | Both add columns to same DataFrame | Column names don't overlap (MA50/MA10 vs ema9/ema21/ema55/ma200) |

## Anti-Patterns

### Anti-Pattern 1: Copying v2 Component Code into Hybrid Package

**What people do:** Copy `distribution_day.py`, `rally_attempt.py`, etc. into `strategies/mdm_hybrid/` to avoid cross-package imports.
**Why it's wrong:** Creates code drift. Bug fixes in v2 components won't propagate. Already happened once during the classic->v2 migration.
**Do this instead:** Import directly: `from strategies.mdm_v2.distribution_day import DistributionDayCounter`. Python's import system handles cross-package imports fine since both are under `strategies/`.

### Anti-Pattern 2: Embedding Decision Tree Model Object in Engine

**What people do:** Pickle the trained `DecisionTreeClassifier` from Phase 9 and load it at runtime to make predictions.
**Why it's wrong:** Black box -- can't tune individual rules, can't debug why a specific signal was vetoed, can't adjust for edge cases. The decision tree had only 56.7% accuracy on post-2019 data; the extracted rules need human refinement, not blind replay.
**Do this instead:** Translate discovered rules into explicit conditional methods in `IndicatorFilter`. Each method is independently testable, tunable, and debuggable.

### Anti-Pattern 3: Indicator Filter with Internal State

**What people do:** Give the indicator filter memory of previous days (e.g., tracking consecutive bullish/bearish days inside the filter).
**Why it's wrong:** Blurs responsibility. The state machine (position manager) owns state tracking. The indicator filter should be a pure function of the current row's data.
**Do this instead:** If multi-day indicator patterns matter (e.g., "MACD crossed down 2 days ago"), precompute them as DataFrame columns during data preparation, then the filter reads them as row values.

### Anti-Pattern 4: Single Monolithic process_day() Method

**What people do:** Put classic signal detection + indicator evaluation + state transition all in one giant method (like the v2 engine's 140-line `run()` loop body).
**Why it's wrong:** Hard to test individual pieces. Hard to swap indicator rules. The whole point of the hybrid is separable layers.
**Do this instead:** Three explicit steps per day: `_compute_classic_proposal()`, `indicator_filter.evaluate()`, `_resolve_action()`. Each is independently testable.

## Suggested Build Order

Build order follows dependency chains. Each step produces a testable artifact.

### Step 1: HybridConfig (no dependencies)

Create `strategies/mdm_hybrid/config.py` with `HybridConfig` dataclass. Contains `v2: MDMV2Config` plus indicator filter boolean flags and thresholds.

**Test:** Instantiate config, verify `config.v2` produces valid `MDMV2Config`, verify post_init validation.

### Step 2: IndicatorFilter (depends on config only)

Create `strategies/mdm_hybrid/indicator_filter.py` with `IndicatorFilter` class. Implement individual condition methods (`is_bullish_ema_stack`, `is_macd_bullish`, `is_above_ma200`) and the `evaluate()` orchestrator.

**Test:** Unit test each condition method with synthetic row data. Test evaluate() returns correct CONFIRM/VETO/OVERRIDE for known indicator states.

### Step 3: HybridPositionManager (depends on config)

Create `strategies/mdm_hybrid/position_manager.py`. Start from `V2PositionManager` logic but add `filter_verdict` parameter to `process_day()`. The position manager respects VETO (blocks transition) and OVERRIDE (forces transition).

**Test:** Unit test state transitions with mocked proposals and verdicts. Verify VETO prevents BUY->CASH when classic says sell but indicators say hold.

### Step 4: HybridEngine (depends on all above + v2 components + core)

Create `strategies/mdm_hybrid/hybrid_engine.py`. Wire together:
1. Data preparation (core indicators + classic indicators)
2. Daily loop with propose-filter-decide pipeline
3. Results DataFrame output matching v2 format

**Test:** Run on NASDAQ data, verify output DataFrame has expected columns. Compare against v2 engine output to confirm classic signal detection is identical when filter is set to "always confirm."

### Step 5: Validation Integration

Create `scripts/run_hybrid_backtest.py`. Wire `HybridEngine` -> `extract_model_signals()` -> `compare_signals()` against 962 published signals. Print three-way comparison: classic vs v2 vs hybrid match rates.

**Test:** Run on full NASDAQ dataset. Target: hybrid accuracy > 56.7% (v2 baseline). Generate confusion matrix and per-era breakdown.

### Step 6: Parameter Tuning

Use existing `analysis/` patterns to sweep indicator filter parameters. Which combination of EMA/MACD/MA200 filters produces highest match rate on post-2019 signals?

**Test:** Grid search over filter boolean flags. Track match rate, per-type accuracy (Buy/Cash/Sell), and cross-era degradation.

## Scaling Considerations

Not applicable -- this is a research/backtesting system processing ~13,000 trading days (52 years of NASDAQ data). All computation is in-memory pandas operations completing in under 5 seconds. No scaling concerns.

The only performance consideration: `build_indicator_dataframe()` computes HA Smoothed candles with a Python loop (O(n) for recursive HA open). For 13K rows this takes ~50ms. Not a bottleneck.

## Sources

- Existing codebase: `strategies/mdm_v2/mdm_v2_engine.py` (v2 engine pattern)
- Existing codebase: `core/indicators.py` (indicator computation interface)
- Existing codebase: `core/signal_comparator.py` (validation interface)
- Existing codebase: `analysis/rule_discovery.py` (discovered decision tree rules)
- Existing codebase: `analysis/validate_discovery.py` (validation methodology)
- `.planning/PROJECT.md` (project context and milestone goals)

---
*Architecture research for: Hybrid MDM Engine*
*Researched: 2026-03-29*
