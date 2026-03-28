# Phase 4: MDM v2 Engine - Research

**Researched:** 2026-03-28
**Domain:** Trading state machine engine, parameter optimization, hypothesis testing
**Confidence:** HIGH

## Summary

Phase 4 builds a parameterized MDM v2 engine that introduces Cash as a deliberate intermediate state between Buy and Sell, removes the SHORT state, and provides a hypothesis testing framework with grid-search parameter sweep to maximize signal match rate against published post-2019 signals.

The existing codebase provides strong foundations: the classic MDM engine (350 lines, well-structured), the signal comparator from Phase 3, the optimize_mdm.py grid search pattern, and 42 published training signals (2019-2022) with 19 Buy, 12 Sell, and 11 Cash signals. A single engine run on the training data (1008 rows) takes ~0.25s, meaning a 3000-combination sweep completes in ~13 minutes -- well within practical limits.

The primary architectural challenge is designing the Cash state transitions correctly: Cash must be triggered from HOLDING via configurable conditions (DD count threshold AND/OR price-action heuristics like MA10 breakdown), and must exit to Buy (via FTD/MA50 breakout) or to Sell (via further deterioration). The three-state machine (Buy/Cash/Sell) is simpler than classic's four-state (CASH/HOLDING/WAITING_SELL/SHORT), which means the v2 position manager can be a clean rewrite rather than a modification.

**Primary recommendation:** Fork mdm_classic into strategies/mdm_v2/ as a clean copy, simplify the state machine to three states, make all thresholds configurable via MDMV2Config dataclass, then build the hypothesis testing framework as a thin wrapper around engine.run() + compare_signals() scoring.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Cash triggers from Buy (HOLDING) via combined conditions: EITHER distribution day count hitting a configurable threshold OR price-action heuristics (e.g., close below MA10, failed rally). Both conditions are parameterizable for the sweep.
- **D-02:** Cash exits: FTD or MA50 breakout triggers Cash->Buy (reuses existing signal types). MA10/MA50 breakdown condition triggers Cash->Sell. Consistent with classic signal detection patterns.
- **D-03:** SHORT state is removed from v2. Sell signals transition to Cash (go flat), not to a short position. Simplifies the state machine to three states: Buy (HOLDING), Cash, Sell (triggers exit to Cash).
- **D-04:** Cash is scored as a distinct third signal type in match rate calculations. Cash is NOT a partial Sell. The signal comparator already supports Buy/Sell/Cash per Phase 3 D-01.
- **D-05:** Fork MDM classic into a new `strategies/mdm_v2/` package. Classic code stays untouched as reference. Follows Phase 2 pattern of independent strategy packages under `strategies/`.
- **D-06:** New `MDMV2Config` dataclass in `strategies/mdm_v2/config.py` with v2-specific parameters (Cash trigger thresholds, no SHORT-related params). Can reference classic defaults as starting point but owns its own schema.
- **D-07:** Hypothesis testing and parameter sweep code lives in `analysis/hypothesis/` directory. Follows existing pattern of `analysis/` for post-backtest research tools.
- **D-08:** Hypotheses are defined as named `MDMV2Config` variations with different parameter values. No code changes per hypothesis -- purely config-driven.
- **D-09:** Results reported as CSV (columns: hypothesis_name, match_rate, per_type_rates, param_values) plus text summary with top-N ranking.
- **D-10:** Framework supports parameter variations only for Phase 4. Structural changes tested manually.
- **D-11:** Grid search over defined parameter space. Exhaustive, reproducible, follows existing optimize_mdm.py pattern.
- **D-12:** Training period: 2019-2022 published signals only. Held-out 2023-2026 reserved for Phase 5.
- **D-13:** Sweep results ranked by overall signal match rate only. Per-type breakdown shown but not used for ranking.

### Claude's Discretion
- Exact parameter ranges and grid values for the sweep
- Internal state machine implementation details for Cash transitions
- Which classic engine modules to copy vs rewrite for v2
- CSV output formatting and text summary structure
- Hypothesis naming conventions and organization

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MDM-01 | Cash implemented as intermediate state between Buy and Sell in state machine | v2 position manager with 3-state machine (Buy/Cash/Sell); D-01/D-02/D-03 define transitions; classic position_manager.py provides fork base |
| MDM-02 | Parameterized rule engine with configurable thresholds | MDMV2Config dataclass extending classic MDMConfig pattern; all rule thresholds as fields with defaults and validation |
| MDM-03 | Hypothesis testing framework allows systematic rule modification and match-rate scoring | analysis/hypothesis/ module wrapping engine.run() + compare_signals(); config-driven per D-08/D-10 |
| MDM-04 | Parameter sweep searches over rule parameter space to maximize signal match rate | Grid search following optimize_mdm.py pattern; 42 training signals; ~0.25s/run enables 3000+ combos in <15min |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >=2.0.0 | DataFrame engine for OHLCV processing and results | Already in project; engine produces DataFrame output |
| numpy | >=1.24.0 | Numeric computations for indicators | Already in project |
| itertools | stdlib | Grid search parameter combinations | Standard library; used in existing optimize_mdm.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses | stdlib | MDMV2Config and signal dataclasses | All config and data structures |
| csv | stdlib | Results output | Hypothesis and sweep result CSV export |
| time | stdlib | Sweep timing and progress reporting | Parameter sweep progress tracking |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| itertools grid search | scikit-optimize / optuna | Overkill for ~3000 combos; adds dependency; grid search is deterministic and reproducible per D-11 |
| Manual CSV output | pandas to_csv | Either works; pandas to_csv is simpler for DataFrame results |

**Installation:** No new packages required. All dependencies already in pyproject.toml.

## Architecture Patterns

### Recommended Project Structure
```
strategies/mdm_v2/
    __init__.py              # Package exports
    config.py                # MDMV2Config dataclass
    position_manager.py      # 3-state machine (Buy/Cash/Sell)
    mdm_v2_engine.py         # Main engine (forked from classic)
    distribution_day.py      # Copied from classic (unchanged)
    rally_attempt.py         # Copied from classic (unchanged)
    ftd_signal.py            # Copied from classic (unchanged)
    stop_loss.py             # Simplified (no SHORT logic)
    indicators.py            # Copied from classic (unchanged)

analysis/hypothesis/
    __init__.py
    hypothesis_runner.py     # Run single hypothesis config, return match rate
    parameter_sweep.py       # Grid search over MDMV2Config space
```

### Pattern 1: Three-State Machine
**What:** Replace classic's 4-state (CASH/HOLDING/WAITING_SELL/SHORT) with 3 states: Buy (HOLDING), Cash, Sell. Sell is a transient signal that immediately transitions to Cash.
**When to use:** All v2 engine position management.
**Implementation detail:**

State transitions:
```
Cash -> Buy:    FTD signal OR MA50 breakout OR 52-week breakout
Buy -> Cash:    DD count >= threshold OR close < MA10 (price-action heuristic) OR stop loss
Buy -> Sell:    NOT used as a persistent state. "Sell" is the signal TYPE emitted when exiting Buy.
Cash -> Sell:   MA10/MA50 breakdown condition (further deterioration while in Cash)
```

The key insight: in v2, "Sell" is a signal label for the comparator, not a position state. The engine only has two persistent states (Buy and Cash). When a Sell signal is emitted, the position transitions to Cash. The `extract_model_signals()` function in `core/signal_comparator.py` already maps states to signals -- v2 needs its state column to produce values that map correctly.

**Recommended state values for the 'state' column:**
- `"BUY"` -> maps to signal "Buy"
- `"CASH"` -> maps to signal "Cash"
- When a Sell-type exit occurs, the state goes to `"CASH"` but the action/signal column records the Sell transition

Wait -- this creates a problem. The `extract_model_signals()` function detects transitions by mapping state values. If we go Buy->Cash on both Cash signals AND Sell signals, the comparator cannot distinguish them.

**Resolution:** Use a dedicated state value `"SELL"` that is transient (lasts 0-1 rows before becoming CASH), OR modify the v2 engine to emit an explicit signal column that the comparator reads instead of deriving from state. The simpler approach: keep the STATE_TO_SIGNAL mapping but add a `"SELL"` state that the engine sets on the row where the Sell signal fires, then transitions to CASH on the next row. This matches how classic works with SHORT.

Actually, reviewing the signal data more carefully: looking at the published signals, Sell and Cash appear as distinct signal types. For example:
- 2019-10-01: Cash (exit from Buy)
- 2019-12-02: Sell (exit from Buy)

The difference between Cash and Sell in published signals appears to be: Cash = caution/partial exit (may re-enter), Sell = definitive exit (market in trouble). In v2:
- **Cash signal** = Buy->Cash transition triggered by early warning (DD threshold, MA10 loss)
- **Sell signal** = Cash->Sell transition triggered by further deterioration while in Cash (MA50 breakdown, continued decline)

This means the v2 engine needs these actual states to produce correct signal mapping:
```python
class V2MarketState(Enum):
    BUY = "BUY"      # Holding positions (maps to "Buy" signal on entry)
    CASH = "CASH"    # Flat, cautious (maps to "Cash" signal on entry from BUY)
    SELL = "SELL"     # Flat, bearish (maps to "Sell" signal on entry from CASH)
```

Where SELL and CASH are both "flat" (no position), but they represent different signal types for comparison purposes. SELL transitions back to CASH or directly to BUY on the next FTD.

```python
# Updated STATE_TO_SIGNAL for v2
V2_STATE_TO_SIGNAL = {
    "BUY": "Buy",
    "CASH": "Cash",
    "SELL": "Sell",
}
```

### Pattern 2: Config-Driven Hypothesis
**What:** Each hypothesis is a named MDMV2Config instance. Runner takes config + data, returns match rate dict.
**When to use:** All hypothesis testing and parameter sweep.
**Example:**
```python
from dataclasses import dataclass, field

@dataclass
class MDMV2Config:
    """Configuration for MDM v2 engine."""
    # --- Rally / FTD parameters (from classic) ---
    correction_threshold: float = -0.10
    ftd_min_rally_day: int = 3
    ftd_max_rally_day: int = 12
    ftd_min_price_gain: float = 0.01
    ma50_breakout_correction: float = -0.06

    # --- Distribution Day parameters ---
    dd_window_size: int = 20
    dd_price_drop_threshold: float = -0.002
    dd_price_stall_threshold: float = 0.001
    dd_stall_p_loc_threshold: float = 0.2

    # --- Cash trigger parameters (NEW in v2) ---
    dd_cash_threshold: int = 5          # DD count that triggers Buy->Cash
    ma10_cash_enabled: bool = True      # Enable close<MA10 as Cash trigger
    ma10_cash_consecutive: int = 2      # Consecutive days below MA10 to trigger Cash

    # --- Sell trigger parameters (NEW in v2) ---
    ma50_sell_enabled: bool = True      # Enable MA50 breakdown as Cash->Sell
    cash_deterioration_days: int = 10   # Days in Cash before auto-Sell

    # --- Stop Loss parameters ---
    stop_loss_pct: float = 0.025

    # --- Hypothesis metadata ---
    name: str = "default"
```

### Pattern 3: Grid Search with Signal Scoring
**What:** Wrap itertools.product over config parameter ranges, run engine + comparator for each, collect results.
**When to use:** Parameter sweep (MDM-04).
**Example:**
```python
def run_sweep(df, published_signals, param_grid, top_n=10):
    """Grid search over parameter space, scored by signal match rate."""
    keys = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))

    results = []
    for combo in combos:
        params = dict(zip(keys, combo))
        config = MDMV2Config(**params)
        engine = MDMV2Engine(config)
        result_df = engine.run(df)

        model_signals = extract_model_signals(result_df)
        score = compare_signals(model_signals, published_signals)

        results.append({
            'name': f"sweep_{hash(combo)}",
            'match_rate': score['match_rate'],
            'buy_rate': score['per_type']['Buy']['rate'],
            'sell_rate': score['per_type']['Sell']['rate'],
            'cash_rate': score['per_type']['Cash']['rate'],
            **params
        })

    results_df = pd.DataFrame(results)
    return results_df.sort_values('match_rate', ascending=False).head(top_n)
```

### Anti-Patterns to Avoid
- **Modifying classic engine in-place:** Fork to strategies/mdm_v2/, never touch mdm_classic. Classic is the reference baseline.
- **Optimizing for per-type rates:** D-13 says rank by overall match rate only. Per-type shown for analysis but not ranking.
- **Encoding hypotheses as code changes:** D-10 says config-driven only. If a hypothesis needs code changes, it is manual/structural, not part of the automated framework.
- **Using held-out data (2023+):** D-12 strictly reserves 2023-2026 for Phase 5. Training on 2019-2022 only.
- **Over-fitting with too many parameters:** 42 training signals is a small dataset. Keep the parameter space focused on 5-8 meaningful parameters with 3-5 values each.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Signal match rate scoring | Custom comparison logic | `core/signal_comparator.compare_signals()` | Already tested in Phase 3; handles Buy/Sell/Cash types, per-type breakdown |
| Signal extraction from engine output | Manual state parsing | `core/signal_comparator.extract_model_signals()` | Handles state-to-signal mapping, transition detection |
| NASDAQ data loading | Custom CSV reader | `core/data_loader.DataLoader('nasdaq')` | Handles 1000x normalization, date parsing, spot-checks |
| Published signal loading | Custom parser | `core/signal_loader.load_signal_fixture()` | Validates signal types, parses dates |
| Grid search combinations | Custom nested loops | `itertools.product()` | Standard library, already used in optimize_mdm.py |

**Key insight:** Phase 3 built the signal comparison infrastructure specifically for this use case. The hypothesis testing framework is essentially a thin orchestration layer around existing components: DataLoader + Engine.run() + extract_model_signals() + compare_signals().

## Common Pitfalls

### Pitfall 1: State-Signal Mapping Mismatch
**What goes wrong:** v2 engine state column values don't map correctly through `extract_model_signals()`, producing wrong signal types for comparison.
**Why it happens:** Classic uses STATE_TO_SIGNAL mapping {"HOLDING": "Buy", "SHORT": "Sell", "CASH": "Cash", "WAITING_SELL": "Cash"}. V2 needs different mapping since it has no HOLDING/SHORT/WAITING_SELL.
**How to avoid:** Define V2_STATE_TO_SIGNAL explicitly. Either (a) update extract_model_signals to accept a custom mapping dict, or (b) use state names that work with the existing mapping, or (c) create a v2-specific extract function.
**Warning signs:** Match rate is 0% or near-0% -- signals not being extracted correctly.

### Pitfall 2: Sell Signal as Persistent State
**What goes wrong:** If Sell is just an alias for Cash (both = flat/no position), the comparator cannot distinguish Cash and Sell signal types.
**Why it happens:** The temptation to treat Sell and Cash as the same position state (both are "not holding").
**How to avoid:** Keep SELL as a distinct state enum value. When Cash->Sell transition fires, set state to SELL. When SELL->Buy transition fires (via FTD), set state to BUY. The SELL state persists until a Buy signal, just like CASH persists until a Buy signal. The difference is only in the signal label.
**Warning signs:** All published Sell signals show as Cash in model output.

### Pitfall 3: Overfitting on 42 Signals
**What goes wrong:** Grid search finds parameters that perfectly match 42 training signals but fail on held-out data.
**Why it happens:** Small sample size (42 signals) with many free parameters creates high risk of overfitting.
**How to avoid:** (1) Keep parameter space small (5-8 params, 3-5 values). (2) Prefer configs with good overall match rate AND reasonable per-type rates. (3) Phase 5 validation will catch overfitting -- this is by design. (4) Report top-N (not just top-1) so Phase 5 can validate multiple candidates.
**Warning signs:** Top config has 90%+ match rate with extreme parameter values.

### Pitfall 4: DD Count Reset Timing
**What goes wrong:** Distribution day counter not reset at correct state transitions, causing stale DD counts to trigger premature Cash signals.
**Why it happens:** Classic resets DD count on FTD signal. V2 must also reset on Buy->Cash transition (or not -- this is a design choice that affects signal quality).
**How to avoid:** Explicitly decide DD count behavior at each state transition. Document when dd_counter.reset() is called. Test with known signal dates.
**Warning signs:** Cash signals fire too frequently shortly after Buy signals.

### Pitfall 5: Training Data Date Range Off-by-One
**What goes wrong:** Including 2023 signals in training, or excluding late 2022 signals.
**Why it happens:** Ambiguous date filtering (strict vs inclusive boundaries).
**How to avoid:** Training data: 2019-01-01 through 2022-12-31 inclusive. Published signals in this range: 42 signals. Load NASDAQ price data starting from 2017 or 2018 to warm up indicators (MA50 needs 50 days of prior data, rolling high needs 252 days).
**Warning signs:** Signal count doesn't match expected 42 for training set.

## Code Examples

### Creating and Running v2 Engine
```python
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from core.data_loader import DataLoader
from core.signal_loader import load_signal_fixture
from core.signal_comparator import extract_model_signals, compare_signals

# Load data with warm-up period for indicators
loader = DataLoader('nasdaq')
df = loader.load(start_date='2017-01-01', end_date='2022-12-31')

# Load published signals (training set)
published = load_signal_fixture('data/signals/nasdaq_signals.csv')
published_train = published[
    (published['date'] >= '2019-01-01') &
    (published['date'] <= '2022-12-31')
]

# Run v2 engine
config = MDMV2Config(dd_cash_threshold=4, ma10_cash_consecutive=3)
engine = MDMV2Engine(config)
results = engine.run(df)

# Score against published signals
model_signals = extract_model_signals(results)
score = compare_signals(model_signals, published_train)
print(f"Match rate: {score['match_rate']:.1f}%")
```

### Hypothesis Runner Pattern
```python
def run_hypothesis(name, config, df, published_signals):
    """Run a single hypothesis and return scored result."""
    engine = MDMV2Engine(config)
    results = engine.run(df)
    model_signals = extract_model_signals(results)
    score = compare_signals(model_signals, published_signals)
    return {
        'hypothesis': name,
        'match_rate': score['match_rate'],
        'total_published': score['total_published'],
        'total_matched': score['total_matched'],
        'buy_rate': score['per_type']['Buy']['rate'],
        'sell_rate': score['per_type']['Sell']['rate'],
        'cash_rate': score['per_type']['Cash']['rate'],
        'config': config,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 4-state machine (CASH/HOLDING/WAITING_SELL/SHORT) | 3-state (BUY/CASH/SELL) | Phase 4 (this phase) | Simplifies logic, removes SHORT trading |
| Performance-optimized parameters (optimize_mdm.py) | Signal-match-optimized parameters | Phase 4 (this phase) | Optimize for fidelity to published signals, not P&L |
| Single config per engine run | Named config hypotheses | Phase 4 (this phase) | Enables systematic exploration |

## Open Questions

1. **Signal comparator coupling to classic config**
   - What we know: `classify_divergences()` in signal_comparator.py imports `MDMConfig` from strategies/mdm_classic. The v2 engine uses `MDMV2Config`.
   - What's unclear: Does the hypothesis framework need divergence classification (Phase 3 feature), or just match rate scoring?
   - Recommendation: Hypothesis runner only needs `compare_signals()` which does NOT depend on MDMConfig. Divergence classification is optional/separate. No coupling issue for the core scoring path.

2. **Warm-up period for indicators**
   - What we know: MA50 needs 50 trading days, rolling high (52-week) needs 252 trading days. Training signals start 2019-01-01.
   - What's unclear: Exact start date for price data to ensure indicators are valid by 2019-01-01.
   - Recommendation: Load price data from 2017-01-01 (2 full years of warm-up). This provides ample data for all indicators. Only compare signals from 2019-01-01 onwards.

3. **Sell state persistence vs transient**
   - What we know: Published signals show Sell followed by Buy (e.g., 2019-12-02 Sell, 2020-01-06 Buy). The Sell state persists until the next Buy.
   - What's unclear: Should SELL be a persistent state (like CASH), or should it quickly transition back to CASH?
   - Recommendation: SELL should be persistent. It represents a bearish flat position that only exits via a new Buy signal (FTD/MA50 breakout). This matches the published signal pattern where Sell persists until the next Buy or Cash.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ (dev dependency in pyproject.toml) |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x --timeout=30` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MDM-01 | Cash as intermediate state in 3-state machine | unit | `uv run pytest tests/test_mdm_v2_states.py -x` | No - Wave 0 |
| MDM-01 | State transitions: Buy->Cash, Cash->Sell, Cash->Buy, Sell->Buy | unit | `uv run pytest tests/test_mdm_v2_states.py::test_state_transitions -x` | No - Wave 0 |
| MDM-02 | All thresholds configurable via MDMV2Config | unit | `uv run pytest tests/test_mdm_v2_config.py -x` | No - Wave 0 |
| MDM-02 | Engine produces valid results with non-default config | integration | `uv run pytest tests/test_mdm_v2_engine.py::test_custom_config -x` | No - Wave 0 |
| MDM-03 | Hypothesis runner scores config against published signals | integration | `uv run pytest tests/test_hypothesis.py::test_hypothesis_runner -x` | No - Wave 0 |
| MDM-03 | Multiple hypotheses compared in batch | integration | `uv run pytest tests/test_hypothesis.py::test_batch_hypotheses -x` | No - Wave 0 |
| MDM-04 | Parameter sweep runs grid search and returns ranked results | integration | `uv run pytest tests/test_hypothesis.py::test_parameter_sweep -x` | No - Wave 0 |
| MDM-04 | Sweep results CSV contains required columns | unit | `uv run pytest tests/test_hypothesis.py::test_sweep_output_format -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_mdm_v2_states.py tests/test_mdm_v2_config.py tests/test_mdm_v2_engine.py tests/test_hypothesis.py -x --timeout=60`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mdm_v2_states.py` -- covers MDM-01 (state machine transitions)
- [ ] `tests/test_mdm_v2_config.py` -- covers MDM-02 (config validation, parameter ranges)
- [ ] `tests/test_mdm_v2_engine.py` -- covers MDM-01/MDM-02 integration (engine produces correct state column)
- [ ] `tests/test_hypothesis.py` -- covers MDM-03/MDM-04 (hypothesis runner, sweep, output format)

## Data Characteristics

### Training Dataset (2019-2022)
| Metric | Value |
|--------|-------|
| Published signals | 42 |
| Buy signals | 19 |
| Sell signals | 12 |
| Cash signals | 11 |
| NASDAQ trading days | 1008 |
| Time per engine run | ~0.25s |

### Parameter Space Estimates
| Params | Values/param | Total combos | Est. runtime |
|--------|-------------|--------------|--------------|
| 5 | 3 | 243 | ~1 min |
| 6 | 3 | 729 | ~3 min |
| 7 | 3 | 2,187 | ~9 min |
| 8 | 3 | 6,561 | ~27 min |
| 6 | 4 | 4,096 | ~17 min |

**Recommendation:** Start with 6-7 key parameters, 3 values each (729-2187 combos, 3-9 min). This is the sweet spot for exhaustive search with 42 training signals.

### Recommended Parameter Grid
```python
param_grid = {
    'correction_threshold': [-0.08, -0.10, -0.12],     # When correction phase starts
    'ftd_min_rally_day': [3, 4, 5],                     # Earliest FTD day
    'ftd_min_price_gain': [0.008, 0.01, 0.015],         # FTD price gain threshold
    'dd_cash_threshold': [3, 4, 5],                     # DD count for Buy->Cash
    'stop_loss_pct': [0.02, 0.025, 0.03],               # Stop loss percentage
    'dd_window_size': [15, 20, 25],                     # DD rolling window
}
# = 729 combinations, ~3 min runtime
```

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_classic/mdm_engine.py` - Full engine source, 350 lines, daily processing loop
- `strategies/mdm_classic/position_manager.py` - 4-state machine with all transitions
- `strategies/mdm_classic/config.py` - MDMConfig dataclass with 11 parameters
- `core/signal_comparator.py` - compare_signals(), extract_model_signals() implementations
- `core/signal_loader.py` - Published signal loader with validation
- `core/data_loader.py` - Unified DataLoader with NASDAQ normalization
- `scripts/optimize_mdm.py` - Grid search reference pattern
- `data/signals/nasdaq_signals.csv` - 67 published signals (42 in training set)

### Secondary (MEDIUM confidence)
- Performance benchmarks: ~0.25s per engine run measured on actual training data
- Signal type distribution: 19 Buy, 12 Sell, 11 Cash in 2019-2022 training set

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - uses only existing project dependencies, no new packages
- Architecture: HIGH - well-understood fork pattern, clear state machine design, existing grid search reference
- Pitfalls: HIGH - identified from direct code review of classic engine and signal comparator

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain, no external dependency changes)
