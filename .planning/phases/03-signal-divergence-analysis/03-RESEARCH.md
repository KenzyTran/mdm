# Phase 3: Signal Divergence Analysis - Research

**Researched:** 2026-03-28
**Domain:** Signal comparison, divergence classification, matplotlib visualization
**Confidence:** HIGH

## Summary

Phase 3 builds a comparison engine, divergence report, and visual overlay that measures where MDM classic rules diverge from Dr. K's published NASDAQ signals. The core challenge is: (1) running MDM classic on NASDAQ data (it was built for VN30), (2) mapping engine states to Buy/Sell/Cash signals that match the published format, and (3) classifying divergences by type.

The existing codebase provides all building blocks: `core/data_loader.py` loads normalized NASDAQ OHLCV, `core/signal_loader.py` loads published signals, and `strategies/mdm_classic/MDMEngine` produces daily state columns. The main integration gap is that MDMEngine uses its own internal `DataLoader` (expects VN-style CSV columns), but decision D-13 says to load NASDAQ via `core/data_loader.py`. The `core/data_loader.py` output (columns: date, open, high, low, close, volume) is already compatible with MDMEngine.run() which expects exactly those columns -- the engine's load_data() is just a convenience wrapper. The engine's run() method accepts any DataFrame with OHLCV columns directly.

**Primary recommendation:** Build `core/signal_comparator.py` as a pure-function module operating on two DataFrames (model signals, published signals), with auto-classification heuristics. Wire it with a thin adapter that runs MDMEngine on NASDAQ data and extracts state transitions as signals.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** State-to-signal mapping: HOLDING->Buy, SHORT->Sell, CASH+WAITING_SELL->Cash. Compare state transitions against published signal changes.
- **D-02:** Exact date match only -- a model signal on date X only matches a published signal on date X. No tolerance window.
- **D-03:** Match metrics: overall match rate (% of published signals matched) plus separate match rates per signal type (Buy, Sell, Cash).
- **D-04:** Comparison engine built as reusable module `core/signal_comparator.py`. Takes two signal DataFrames, returns structured results. Phase 4's hypothesis testing reuses this directly.
- **D-05:** Four-type taxonomy: THRESHOLD (model nearly triggered), TIMING (right signal within +/-5 days), STRUCTURAL (signal type model can't produce, e.g., Cash), IRREPRODUCIBLE (no discernible pattern).
- **D-06:** Auto-classification via heuristics: model signal within +/-5 days -> TIMING, published Cash and model has no Cash state -> STRUCTURAL, model indicator within 10% of threshold -> THRESHOLD, else -> IRREPRODUCIBLE.
- **D-07:** Output as CSV (detailed per-divergence rows: date, published signal, model signal, type, context) plus text summary (counts per type, worst periods, overall match rate). CSV feeds Phase 4; summary is human-readable.
- **D-08:** Chart layout: main panel with NASDAQ price line, below it two horizontal color-coded tracks -- top track for published signals, bottom track for model signals (green=Buy, red=Sell, gray=Cash).
- **D-09:** Shaded divergence zones: light red/pink vertical bands behind price chart wherever model and published signals disagree.
- **D-10:** Both a script in `analysis/` generating high-res PNG and a Jupyter notebook for interactive exploration.
- **D-11:** Primary comparison target: NASDAQ published signals (`data/signals/nasdaq_signals.csv`). TECL is not used for primary comparison.
- **D-12:** Full comparison period: 2019-2026 (entire published signal range). No pre/post splits.
- **D-13:** Classic model runs on NASDAQ data loaded via unified `core/data_loader.py` with market='nasdaq'. Does not use the classic engine's own data_loader for NASDAQ data.

### Claude's Discretion
- Exact heuristic thresholds for auto-classification (the 10% threshold proximity, +/-5 day window)
- Internal data structures for comparison results
- Chart styling details (exact colors, font sizes, figure dimensions)
- Notebook structure and cell organization
- Text summary formatting and section ordering

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SIG-01 | Signal comparison engine scores model-generated signals against published signal history | D-01 through D-04 define the comparison engine spec; `core/signal_comparator.py` module with match rate + per-type scoring |
| SIG-02 | MDM classic rules run on NASDAQ data and produce Buy/Sell/Cash signal list | MDMEngine.run() accepts any OHLCV DataFrame; core/data_loader.py provides NASDAQ data; state-to-signal mapping from D-01 |
| SIG-03 | Divergence report identifies dates, signal types, and durations where classic rules differ from published post-2019 signals | D-05 through D-07 define divergence classification taxonomy and output format |
| SIG-04 | Visual signal overlay shows price chart with model signals and published signals side by side | D-08 through D-10 define chart layout, shading, and delivery format (PNG + notebook) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.3.3 | DataFrame operations for signal comparison, merging, date alignment | Already installed; project-standard for all data work |
| numpy | 2.4.1 | Numeric operations for threshold proximity calculations | Already installed; used throughout codebase |
| matplotlib | 3.10.8 | Multi-panel chart with price line, signal tracks, divergence shading | Already installed; established pattern in analysis/ scripts |
| pytest | 9.0.2 | Test infrastructure for comparison engine validation | Already installed; established test pattern in tests/ |

### Supporting
No additional libraries needed. All requirements are met by the existing stack.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| matplotlib | plotly | Interactive but adds dependency; D-10 specifies notebook for interactive exploration anyway |

**Installation:**
No new packages required. All libraries already installed.

## Architecture Patterns

### Recommended Project Structure
```
core/
  signal_comparator.py    # NEW: Reusable comparison engine (SIG-01)
analysis/
  signal_divergence.py    # NEW: Script generating PNG + CSV + summary (SIG-03, SIG-04)
notebooks/
  signal_overlay.ipynb    # NEW: Interactive Jupyter notebook (SIG-04)
data/
  signals/
    nasdaq_signals.csv    # EXISTING: Published signals (input)
output/
  divergence_report.csv   # NEW: Per-divergence detail rows (output)
  divergence_summary.txt  # NEW: Human-readable summary (output)
  signal_overlay.png      # NEW: High-res chart (output)
```

### Pattern 1: State-to-Signal Extraction
**What:** Run MDMEngine on NASDAQ data and extract signal transitions from the daily state column.
**When to use:** Every time the comparison needs model-generated signals.
**Key insight:** MDMEngine.run() returns a DataFrame with a `state` column containing MarketState values (CASH, HOLDING, WAITING_SELL, SHORT). Signal transitions are detected by finding rows where the mapped signal changes from the previous day.

```python
# State-to-signal mapping (from D-01)
STATE_TO_SIGNAL = {
    'HOLDING': 'Buy',
    'SHORT': 'Sell',
    'CASH': 'Cash',
    'WAITING_SELL': 'Cash',
}

def extract_model_signals(results_df: pd.DataFrame) -> pd.DataFrame:
    """Extract signal change points from MDM engine results.

    Maps engine states to Buy/Sell/Cash and returns only the rows
    where the signal changes (transitions).
    """
    df = results_df[['date', 'state']].copy()
    df['signal'] = df['state'].map(STATE_TO_SIGNAL)
    # Detect transitions: where signal differs from previous day
    df['prev_signal'] = df['signal'].shift(1)
    transitions = df[df['signal'] != df['prev_signal']].copy()
    return transitions[['date', 'signal']].reset_index(drop=True)
```

### Pattern 2: Published Signal Alignment
**What:** Published signals are sparse (67 rows covering 2019-2026) -- they represent change points, not daily states. Model signals are also extracted as change points. Comparison aligns on dates.
**When to use:** When building the comparison DataFrame.

```python
def align_signals(model_signals: pd.DataFrame, published_signals: pd.DataFrame) -> pd.DataFrame:
    """Outer-merge model and published signal change points on date."""
    merged = pd.merge(
        published_signals.rename(columns={'signal': 'published'}),
        model_signals.rename(columns={'signal': 'model'}),
        on='date',
        how='outer'
    ).sort_values('date')
    return merged
```

### Pattern 3: Daily Signal State for Visual Overlay
**What:** For the chart, both model and published signals need to be expanded to daily states (forward-fill from change points).
**When to use:** Building the visual overlay chart.

```python
def expand_to_daily(signals_df: pd.DataFrame, date_range: pd.DatetimeIndex) -> pd.Series:
    """Forward-fill sparse signal changes to daily states."""
    daily = pd.DataFrame({'date': date_range})
    daily = daily.merge(signals_df, on='date', how='left')
    daily['signal'] = daily['signal'].ffill()
    return daily.set_index('date')['signal']
```

### Pattern 4: NASDAQ Data Adapter for MDM Classic
**What:** MDMEngine.run() accepts a DataFrame with columns [date, open, high, low, close, volume]. The core/data_loader.py DataLoader('nasdaq').load() returns exactly these columns. No adapter needed -- just pass directly.
**Key detail:** MDMEngine's __init__ creates its own DataLoader, but run() ignores it. The engine's run(df) method takes any DataFrame with the right columns. The engine's load_data() method is a separate convenience that is NOT used in this flow.

```python
from core.data_loader import DataLoader
from strategies.mdm_classic import MDMEngine

# Load NASDAQ via unified loader
loader = DataLoader('nasdaq')
nasdaq_df = loader.load(start_date='2017-01-01', end_date='2026-12-31')

# Run classic engine directly on NASDAQ data
engine = MDMEngine()
results = engine.run(nasdaq_df)
```

**IMPORTANT:** The engine starts processing from index 1 (skips first row). The data must start well before 2019 to allow indicators (MA50 needs ~50 days warmup) to stabilize. Loading from 2017 gives 2 full years of warmup before the 2019-2026 comparison window.

### Anti-Patterns to Avoid
- **Comparing daily states instead of transitions:** Published signals are change points. Comparing daily states would inflate match counts. Compare transition dates.
- **Using MDMEngine's load_data():** This uses the classic DataLoader which expects VN-style CSV. Use core/data_loader.py per D-13.
- **Modifying MDMEngine for this phase:** Phase 3 is analysis-only. The classic engine must run unmodified. Phase 4 will modify rules.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date alignment | Custom date matching loop | `pd.merge(on='date', how='outer')` | Handles missing dates, duplicates, timezone edge cases |
| Forward-fill for daily states | Manual loop through dates | `pd.Series.ffill()` after merge with date range | Vectorized, handles gaps correctly |
| Multi-panel charts | Manual subplot positioning | `matplotlib.gridspec.GridSpec` or `fig.add_subplot()` | Standard approach for complex layouts |
| Color-coded horizontal bands | Drawing rectangles manually | `ax.axvspan()` for divergence zones + `ax.fill_between()` for signal tracks | Built-in matplotlib, handles date axes |

## Common Pitfalls

### Pitfall 1: MDM Classic Produces No Cash Transitions
**What goes wrong:** The MDM classic state machine transitions HOLDING -> WAITING_SELL -> SHORT or back to HOLDING. It goes to CASH via stop loss or sell. But there is no explicit "Cash" signal -- it's a state after selling. Published signals frequently have Cash as an intermediate step between Buy and Sell.
**Why it happens:** The classic MDM was designed for VN30 where Cash wasn't a published concept. Dr. K's post-2019 NASDAQ model uses Cash as a distinct signal (reduce exposure but not short).
**How to avoid:** D-01 correctly maps CASH and WAITING_SELL to "Cash" signal. But many divergences will be STRUCTURAL type because the classic model goes HOLDING->SHORT where published goes Buy->Cash->Sell.
**Warning signs:** If STRUCTURAL divergences dominate (>40% of total), this is expected -- it's what Phase 4 needs to fix.

### Pitfall 2: Indicator Warmup Period
**What goes wrong:** Running MDMEngine on NASDAQ data starting from 2019 produces garbage signals for the first ~50 days because MA50, rolling highs, etc. need history.
**Why it happens:** Indicators like MA50, 52-week high, and rolling highs need substantial prior data.
**How to avoid:** Load NASDAQ data from 2017 (or earlier) to give 2+ years of warmup. Only compare signals within the 2019-2026 window.
**Warning signs:** First model signal appearing unrealistically early (e.g., day 2).

### Pitfall 3: Multiple Model Signals on Same Day
**What goes wrong:** The MDM engine can produce multiple state transitions in edge cases (e.g., buy then immediately hit stop loss). The published signals have exactly one signal per date.
**Why it happens:** The engine processes state sequentially within a day.
**How to avoid:** When extracting model signals, take the LAST state of each day as the definitive signal. The engine's results DataFrame already does this -- each row has the final state for that date.
**Warning signs:** More model signals than published signals in a given week.

### Pitfall 4: NASDAQ Data Period Coverage
**What goes wrong:** The published signals span 2019-01-04 to 2024-11-06 (67 rows, with the last signal being "Buy" with no closing signal). The NASDAQ CSV must cover this full range.
**Why it happens:** Data file may not extend to most recent dates.
**How to avoid:** Verify NASDAQ CSV date range before running. The comparison window should be clipped to the overlap between available data and published signals.
**Warning signs:** Published signals outside the NASDAQ data range.

### Pitfall 5: Signal-to-Signal Timing for Divergence Windows
**What goes wrong:** The +/-5 day TIMING heuristic (D-06) could match a model signal to the WRONG published signal if signals are close together.
**Why it happens:** Published signals can be as close as 2 days apart (e.g., 2020-03-02 Buy, 2020-03-04 Cash).
**How to avoid:** For TIMING classification, match each published signal to the nearest model signal of the SAME TYPE within +/-5 days. Don't match a Buy to a nearby Sell.
**Warning signs:** TIMING classifications between signals of different types.

## Code Examples

### Running MDM Classic on NASDAQ Data
```python
# Verified pattern from existing codebase
from core.data_loader import DataLoader
from strategies.mdm_classic import MDMEngine

loader = DataLoader('nasdaq')
nasdaq_df = loader.load(start_date='2017-01-01', end_date='2026-12-31')

engine = MDMEngine()
results = engine.run(nasdaq_df)

# Extract state transitions as signals
results['mapped_signal'] = results['state'].map({
    'HOLDING': 'Buy',
    'SHORT': 'Sell',
    'CASH': 'Cash',
    'WAITING_SELL': 'Cash',
})
results['prev_mapped'] = results['mapped_signal'].shift(1)
transitions = results[results['mapped_signal'] != results['prev_mapped']].copy()
model_signals = transitions[['date', 'mapped_signal']].rename(columns={'mapped_signal': 'signal'})
```

### Multi-Panel Matplotlib Chart (D-08, D-09)
```python
# Based on existing analysis/analyze_drawdown.py pattern
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec

fig = plt.figure(figsize=(20, 10))
gs = GridSpec(3, 1, height_ratios=[4, 1, 1], hspace=0.05)

# Main price panel
ax_price = fig.add_subplot(gs[0])
ax_price.plot(daily_df['date'], daily_df['close'], color='black', linewidth=0.8)

# Divergence shading (D-09)
for start, end in divergence_periods:
    ax_price.axvspan(start, end, alpha=0.15, color='red')

# Published signals track (top)
ax_pub = fig.add_subplot(gs[1], sharex=ax_price)
signal_colors = {'Buy': '#2ca02c', 'Sell': '#d62728', 'Cash': '#7f7f7f'}
# Use fill_between with step for color-coded bands

# Model signals track (bottom)
ax_model = fig.add_subplot(gs[2], sharex=ax_price)

plt.savefig('output/signal_overlay.png', dpi=150, bbox_inches='tight')
```

### Divergence Auto-Classification (D-05, D-06)
```python
def classify_divergence(
    pub_date, pub_signal, model_signal,
    model_signals_df, engine_results_df, config
) -> str:
    """Classify a single divergence point.

    Returns one of: TIMING, STRUCTURAL, THRESHOLD, IRREPRODUCIBLE
    """
    # STRUCTURAL: Published Cash but model can't produce equivalent
    if pub_signal == 'Cash':
        # Check if model was in a state that never transitions to Cash-like
        # Classic model's Cash comes from stop-loss/sell, not a deliberate Cash signal
        return 'STRUCTURAL'

    # TIMING: Model has same signal type within +/-5 days
    window = model_signals_df[
        (model_signals_df['date'] >= pub_date - pd.Timedelta(days=5)) &
        (model_signals_df['date'] <= pub_date + pd.Timedelta(days=5)) &
        (model_signals_df['signal'] == pub_signal)
    ]
    if len(window) > 0:
        return 'TIMING'

    # THRESHOLD: Model indicator was within 10% of trigger threshold
    # Requires checking engine internals (dd_count near 5, price near FTD threshold, etc.)
    # Implementation depends on what indicators are available in results_df

    return 'IRREPRODUCIBLE'
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| matplotlib pyplot interface | Object-oriented matplotlib API | Long established | Use fig/ax pattern, not plt.plot() directly |
| Manual date formatting | `mdates.AutoDateLocator` + `ConciseDateFormatter` | matplotlib 3.1+ | Cleaner date axes on time series charts |

**Deprecated/outdated:**
- `matplotlib.pyplot` global state: Use OO API (fig, ax) for multi-panel charts

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | tests/conftest.py (sys.path setup + FIXTURES path) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIG-01 | Signal comparator produces match rate and per-type breakdown | unit | `uv run pytest tests/test_signal_comparator.py -x` | Wave 0 |
| SIG-01 | Comparator handles edge cases (empty signals, single signal, perfect match) | unit | `uv run pytest tests/test_signal_comparator.py -x` | Wave 0 |
| SIG-02 | MDM classic runs on NASDAQ data without errors | integration | `uv run pytest tests/test_nasdaq_mdm.py::test_engine_runs -x` | Wave 0 |
| SIG-02 | Extracted model signals contain only Buy/Sell/Cash types | unit | `uv run pytest tests/test_nasdaq_mdm.py::test_signal_types -x` | Wave 0 |
| SIG-03 | Divergence report CSV has required columns | unit | `uv run pytest tests/test_signal_comparator.py::test_divergence_csv_format -x` | Wave 0 |
| SIG-03 | Auto-classification assigns valid types | unit | `uv run pytest tests/test_signal_comparator.py::test_classification -x` | Wave 0 |
| SIG-04 | Overlay chart script runs without errors and produces PNG | smoke | `uv run pytest tests/test_signal_overlay.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_signal_comparator.py tests/test_nasdaq_mdm.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_signal_comparator.py` -- covers SIG-01, SIG-03
- [ ] `tests/test_nasdaq_mdm.py` -- covers SIG-02
- [ ] `tests/test_signal_overlay.py` -- covers SIG-04 (smoke test: script runs, PNG produced)

## Open Questions

1. **NASDAQ CSV date range coverage**
   - What we know: Published signals span 2019-01-04 to 2024-11-06. NASDAQ CSV exists at data/NASDAQ.csv.
   - What's unclear: Whether NASDAQ CSV covers the full 2017-2026 range needed (2017 for warmup, 2024+ for latest signals).
   - Recommendation: First task should verify data range. If data stops before 2024-11-06, the comparison window must be clipped.

2. **THRESHOLD classification requires engine internals**
   - What we know: D-06 says "model indicator within 10% of threshold." MDMEngine results include dd_count, drawdown_pct, rally_day, etc.
   - What's unclear: Exactly which indicators to check for proximity (DD count near 5? FTD gain near 1%? Price near MA50?).
   - Recommendation: Check dd_count (4 when threshold is 5), price_change_pct proximity to ftd_min_price_gain, and drawdown proximity to correction_threshold. These are the three main trigger conditions in MDMConfig.

3. **Last published signal has no close**
   - What we know: The last signal in nasdaq_signals.csv is "2024-11-06,Buy," with no gain_loss_pct -- it's still open.
   - What's unclear: Whether to include this as a matchable signal or treat it as incomplete.
   - Recommendation: Include it -- it's a valid Buy signal. Just note that gain/loss is N/A.

## Sources

### Primary (HIGH confidence)
- `core/signal_loader.py` -- signal fixture loading API, validated columns: date, signal, gain_loss_pct
- `core/data_loader.py` -- DataLoader('nasdaq') produces [date, open, high, low, close, volume], US market normalization
- `strategies/mdm_classic/mdm_engine.py` -- MDMEngine.run(df) accepts OHLCV DataFrame, returns DataFrame with 'state' column
- `strategies/mdm_classic/position_manager.py` -- MarketState enum: CASH, HOLDING, WAITING_SELL, SHORT
- `strategies/mdm_classic/config.py` -- MDMConfig with thresholds for THRESHOLD classification
- `data/signals/nasdaq_signals.csv` -- 67 published signals, 2019-01-04 to 2024-11-06
- `analysis/analyze_drawdown.py` -- Established matplotlib charting pattern
- `tests/test_mdm_regression.py` -- Reference for running MDM engine in tests

### Secondary (MEDIUM confidence)
- matplotlib 3.10 documentation -- GridSpec, axvspan, fill_between APIs (verified by installed version)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in codebase
- Architecture: HIGH -- patterns derived directly from existing code; MDMEngine.run() API verified
- Pitfalls: HIGH -- identified from code review of engine state machine and published signal structure
- Visualization: MEDIUM -- matplotlib patterns are standard but exact D-08/D-09 implementation needs iteration

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain, no external API dependencies)
