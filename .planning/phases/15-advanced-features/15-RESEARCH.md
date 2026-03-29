# Phase 15: Advanced Features - Research

**Researched:** 2026-03-29
**Domain:** Hybrid MDM engine enhancement -- contextual transitions, HA filter, confidence scoring, comparison dashboard
**Confidence:** HIGH

## Summary

Phase 15 enhances the existing hybrid MDM engine with four independent capabilities: (1) contextual state transitions that consider state duration and prior state sequence, (2) Heikin Ashi Smoothed 55 as a 7th toggleable filter condition, (3) exposing indicator confidence scores in the output DataFrame, and (4) a three-way model comparison dashboard. All four features build on well-established codebase patterns and require no new external dependencies.

The codebase is well-structured for these additions. IndicatorFilter already has 6 boolean conditions with majority-vote logic -- adding HA Smoothed 55 as condition 7 follows the exact same pattern. The confidence score (agree_count / total_active) is already computed inside `evaluate()` but not exposed. State history tracking requires adding a lightweight history list to HybridEngine. The comparison dashboard follows the analysis/validate_hybrid.py pattern with matplotlib output.

**Primary recommendation:** Implement as four independent feature groups. ADV-03 (confidence) is trivial (expose existing computation). ADV-02 (HA filter) follows established patterns exactly. ADV-01 (contextual transitions) needs the most design care. ADV-04 (dashboard) is a new analysis script.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Add HA Smoothed 55 as 7th boolean condition inside existing `IndicatorFilter`, alongside the 6 EMA/MACD conditions. Toggleable via `FilterConfig.ha_smooth_enabled`. Consistent with majority-vote logic.
- **D-02:** Bullish condition: `ha_smooth_close > ha_smooth_open` (green HA candle). Bearish: `ha_smooth_close < ha_smooth_open` (red HA candle). HA Smoothed 55 columns already computed in `core/indicators.py`.
- **D-03:** Simple ratio: `agree_count / total_active_conditions`. Already computed inside `IndicatorFilter.evaluate()` -- expose as return value or DataFrame column. Range 0.0-1.0.
- **D-04:** Add `confidence` column to the output DataFrame so it's available for downstream analysis and the comparison dashboard.

### Claude's Discretion
- **Contextual transition logic (ADV-01):** Duration + sequence approach. Implementation location (IndicatorFilter vs HybridEngine), specific context rules, reuse of `cash_deterioration_days`.
- **Dashboard scope & format (ADV-04):** Static matplotlib script, Jupyter notebook, or both. Metrics to include.

### Deferred Ideas (OUT OF SCOPE)
- Parameter sweep/tuning of filter thresholds
- Leading stocks confirmation as filter input
- Anti-whipsaw / cooldown logic (FUT-03)
- Era-aware evaluation (FUT-01)
- VN30 adaptation with recalibrated rules (EXT-04)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ADV-01 | Contextual state transitions -- state history awareness | State history tracking via list in HybridEngine; V2Position already has `days_in_cash`; context rules derive from Dr. K's "favor cash" philosophy |
| ADV-02 | Heikin Ashi Smoothed 55 as toggle filter | HA Smoothed columns already in `build_indicator_dataframe()`; add 7th condition to IndicatorFilter following D-01/D-02 |
| ADV-03 | Indicator confidence scoring per day | `agree_count / len(conditions)` already computed in `evaluate()` line 311-312; expose as return value + DataFrame column |
| ADV-04 | Three-way comparison dashboard | Pure state machine = v2 engine, pure DT = rule_discovery.py model, hybrid = current engine; validate_hybrid.py provides confusion matrix pattern |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, time series | Already in use, all data flows through DataFrames |
| numpy | >= 1.24.0 | Numerical computations | Already in use for indicator math |
| matplotlib | >= 3.7.0 | Dashboard chart generation | Already in use for analysis scripts |
| scikit-learn | >= 1.5.0 | Confusion matrix, classification report, DecisionTreeClassifier | Already in use in validate_hybrid.py and rule_discovery.py |

### Supporting
No new libraries required. All features build on existing stack.

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Modifications

```
strategies/mdm_hybrid/
  indicator_filter.py    # ADD: ha_smooth condition (7th), expose confidence score
  config.py              # ADD: ha_smooth_enabled to FilterConfig
  mdm_hybrid_engine.py   # ADD: state_history tracking, confidence column in output
analysis/
  compare_models.py      # NEW: three-way comparison dashboard script
```

### Pattern 1: Adding a Filter Condition (ADV-02)

**What:** Follow the exact same pattern as existing 6 conditions.
**When to use:** Adding HA Smoothed 55 as 7th condition.

Three files change:
1. `FilterConfig` -- add `ha_smooth_enabled: bool = False` toggle
2. `FilterConfig.active_count()` -- include `self.ha_smooth_enabled` in sum
3. `IndicatorFilter` -- add static methods + append to `_get_bullish_votes` / `_get_bearish_votes`

**Example:**
```python
# In IndicatorFilter class
@staticmethod
def ha_smooth_bullish(row) -> bool:
    """Check if HA Smoothed 55 candle is green (bullish)."""
    return bool(
        pd.notna(row['ha_smooth_close'])
        and pd.notna(row['ha_smooth_open'])
        and row['ha_smooth_close'] > row['ha_smooth_open']
    )

@staticmethod
def ha_smooth_bearish(row) -> bool:
    """Check if HA Smoothed 55 candle is red (bearish)."""
    return bool(
        pd.notna(row['ha_smooth_close'])
        and pd.notna(row['ha_smooth_open'])
        and row['ha_smooth_close'] < row['ha_smooth_open']
    )

# In _get_bullish_votes:
if self.config.ha_smooth_enabled:
    votes.append(self.ha_smooth_bullish(row))

# In _get_bearish_votes:
if self.config.ha_smooth_enabled:
    votes.append(self.ha_smooth_bearish(row))
```

### Pattern 2: Exposing Confidence Score (ADV-03)

**What:** Change `evaluate()` to return both Verdict and confidence float.
**Design choice:** Return a named tuple or dataclass instead of bare Verdict, OR add a separate method. Recommended: return a `FilterResult` dataclass containing `verdict` and `confidence` to maintain backward compatibility via properties.

**Example:**
```python
from dataclasses import dataclass

@dataclass
class FilterResult:
    verdict: Verdict
    confidence: float  # 0.0-1.0, agree_count / total_active

    # Backward compatibility: FilterResult can be compared to Verdict
    def __eq__(self, other):
        if isinstance(other, Verdict):
            return self.verdict == other
        return super().__eq__(other)
```

**Alternative (simpler):** Have `evaluate()` return `Tuple[Verdict, float]`. The engine already destructures the return. This requires updating all call sites but there are only 1-2.

**Recommendation:** Use the Tuple approach -- simpler, fewer new abstractions. The HybridEngine is the only caller of `evaluate()`, so the change surface is small.

### Pattern 3: State History Tracking (ADV-01)

**What:** Track state transitions in HybridEngine for contextual rules.
**Where:** In HybridEngine, NOT in IndicatorFilter (filter should remain stateless per Phase 12 design).

**Recommended data structure:**
```python
@dataclass
class StateHistoryEntry:
    state: str          # "BUY", "CASH", "SELL"
    entered_date: str   # date string
    duration: int       # days in this state (updated incrementally)

# In HybridEngine.__init__:
self.state_history: list[StateHistoryEntry] = []
self.current_state_entry: StateHistoryEntry = StateHistoryEntry("CASH", "", 0)
```

**Contextual rules to implement (Claude's discretion):**

1. **Cash duration awareness:** If in Cash > N days (reuse `cash_deterioration_days` concept), increase threshold for BUY confirmation. Rationale: Dr. K's "favor cash positions" in whipsaw environments.

2. **Prior state sequence:** Buy->Cash->Buy within short period = potential whipsaw. Could increase veto sensitivity for the second Buy.

3. **Sell->Cash transition vs Buy->Cash:** Coming from Sell means bearish regime -- Cash entry from Sell should be stickier (harder to transition out) than Cash entry from Buy exit.

**Implementation location:** Add context evaluation in HybridEngine._process_day() BEFORE calling indicator_filter.evaluate(). Pass context info as additional parameter to evaluate(), or apply as a post-filter adjustment to the verdict.

**Recommendation:** Implement context as a modifier to the majority_threshold. When context is bearish (long Cash, prior Sell), temporarily increase the threshold for BUY confirmation (e.g., require 100% agreement instead of 2/3). This avoids changing the IndicatorFilter API -- just create a temporary FilterConfig with adjusted threshold.

### Pattern 4: Three-Way Comparison Dashboard (ADV-04)

**What:** Standalone analysis script comparing pure state machine, pure decision tree, hybrid.
**Format:** Static matplotlib script in `analysis/compare_models.py` (consistent with existing analysis scripts).

**Three models to run:**
1. Pure state machine: `MDMV2Engine(MDMV2Config())` -- already in validate_hybrid.py as v2 baseline
2. Pure decision tree: Load trained model from `analysis/rule_discovery.py` and predict on signal dates
3. Hybrid: `HybridEngine(HybridConfig(filter_enabled=True))`

**Dashboard layout recommendation:**
- Figure with 3-4 subplots:
  1. Accuracy bar chart (per-type: Buy/Cash/Sell) for each model
  2. Confusion matrix heatmaps side-by-side (3 matrices)
  3. Overall accuracy comparison table
  4. Optional: equity curve overlay or signal timeline

**Reusable functions from validate_hybrid.py:**
- `build_confusion_matrices()` -- adapts easily for any model output
- `format_confusion_matrix()` -- markdown table formatting
- `_format_classification_report()` -- per-type metrics

### Anti-Patterns to Avoid
- **Making IndicatorFilter stateful:** Filter must remain stateless (Phase 12 design). State history lives in HybridEngine.
- **Breaking evaluate() return type without updating callers:** HybridEngine compares `verdict == Verdict.VETO` etc. If returning tuple, must update ALL comparison sites.
- **Enabling ha_smooth by default:** D-01 says toggleable. Default should be False to avoid changing Phase 14 validation baseline.
- **Adding more than 3 active conditions by default:** D-04 from Phase 12 warns against overfitting with >3 conditions. HA Smoothed should be OFF by default.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confusion matrix | Custom counting logic | `sklearn.metrics.confusion_matrix` | Already used in validate_hybrid.py |
| Classification report | Manual precision/recall | `sklearn.metrics.classification_report` | Already used, handles edge cases |
| Decision tree model | Custom rule matcher | `sklearn.tree.DecisionTreeClassifier` | Already trained in rule_discovery.py |
| HA Smoothed computation | New indicator code | `core/indicators.compute_heikin_ashi_smoothed()` | Already implemented and tested |

## Common Pitfalls

### Pitfall 1: Breaking the Phase 14 Validation Baseline
**What goes wrong:** Adding HA Smoothed condition enabled-by-default changes all accuracy numbers from Phase 14.
**Why it happens:** FilterConfig defaults affect all instantiations.
**How to avoid:** `ha_smooth_enabled: bool = False` as default. Phase 14 validation should produce identical results with this change.
**Warning signs:** Any change in confusion matrix numbers when running validate_hybrid.py without explicitly enabling HA.

### Pitfall 2: evaluate() Return Type Breaking Callers
**What goes wrong:** Changing evaluate() to return (Verdict, float) breaks `verdict == Verdict.VETO` comparisons.
**Why it happens:** HybridEngine compares the return value against Verdict enum values on lines 281, 285, 298, 302.
**How to avoid:** Update ALL comparison sites in mdm_hybrid_engine.py when changing the return type. Test that filter_enabled=True still works identically.
**Warning signs:** TypeError or always-False comparisons.

### Pitfall 3: State History Memory Leak
**What goes wrong:** Accumulating state history entries for every day (13,000+ rows) wastes memory.
**Why it happens:** Tracking every state transition without bounds.
**How to avoid:** Only append to history on state CHANGES, not every day. Duration is incremented in-place on the current entry.
**Warning signs:** state_history list growing to 13K+ entries.

### Pitfall 4: Decision Tree Model Not Reproducible
**What goes wrong:** Three-way dashboard gives different decision tree results each run.
**Why it happens:** DecisionTreeClassifier has random_state parameter affecting splits.
**How to avoid:** Set `random_state=42` (or match rule_discovery.py's setting) for reproducibility.
**Warning signs:** Different accuracy numbers across runs.

### Pitfall 5: HA Smoothed NaN at Start of Series
**What goes wrong:** First ~55 rows have warming-up HA Smoothed values that may not be meaningful.
**Why it happens:** EMA(55) needs warm-up period; HA recursive formula starts from row 0.
**How to avoid:** NaN-safe checks in ha_smooth_bullish/bearish (using `pd.notna()` like all other conditions). Already handled by the existing pattern.
**Warning signs:** False results for early rows.

### Pitfall 6: Contextual Rules Overfitting
**What goes wrong:** Adding complex context rules tuned to post-2019 data overfits on 95 signals.
**Why it happens:** Small sample size for post-2019 validation.
**How to avoid:** Keep context rules simple and grounded in Dr. K's stated philosophy ("favor cash"). No more than 2-3 context parameters. Validate on held-out set.
**Warning signs:** Dramatic accuracy improvement on tune set but degradation on held-out set.

## Code Examples

### Adding confidence to evaluate() (ADV-03)

```python
# In IndicatorFilter.evaluate() -- modified return
def evaluate(self, row, proposal: str, current_state=None) -> tuple:
    """Returns (Verdict, confidence_float)."""
    if proposal == "BUY":
        conditions = self._get_bullish_votes(row)
    elif proposal in ("SELL", "CASH"):
        conditions = self._get_bearish_votes(row)
    else:
        return Verdict.CONFIRM, 1.0

    if len(conditions) == 0:
        return Verdict.CONFIRM, 1.0

    agree_count = sum(conditions)
    agree_ratio = agree_count / len(conditions)

    if agree_ratio == 0.0 and len(conditions) >= 3:
        return Verdict.OVERRIDE, 0.0

    if agree_ratio >= self.config.majority_threshold:
        return Verdict.CONFIRM, agree_ratio

    return Verdict.VETO, agree_ratio
```

### HybridEngine caller update pattern

```python
# In HybridEngine._process_day (line ~276 area):
# Before: verdict = self.indicator_filter.evaluate(row, proposal, old_state)
# After:
verdict, confidence = self.indicator_filter.evaluate(row, proposal, old_state)
df.at[idx, 'confidence'] = confidence

# All subsequent comparisons remain: verdict == Verdict.VETO, etc.
```

### State history tracking in HybridEngine

```python
# In __init__:
self.state_history = []  # List of (state_str, entered_date, duration)
self._current_state_start = None
self._current_state_name = "CASH"
self._days_in_current_state = 0

# In run() loop, after determining final new_state:
if new_state.value != self._current_state_name:
    # State changed -- record previous state
    if self._current_state_start is not None:
        self.state_history.append({
            'state': self._current_state_name,
            'entered': self._current_state_start,
            'duration': self._days_in_current_state,
        })
    self._current_state_name = new_state.value
    self._current_state_start = date
    self._days_in_current_state = 1
else:
    self._days_in_current_state += 1
```

### Three-way comparison chart

```python
# In analysis/compare_models.py
import matplotlib.pyplot as plt
import numpy as np

def plot_accuracy_comparison(v2_acc, dt_acc, hybrid_acc, class_names):
    """Bar chart comparing per-type accuracy across 3 models."""
    x = np.arange(len(class_names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width, v2_acc, width, label='Pure State Machine (v2)')
    ax.bar(x, dt_acc, width, label='Pure Decision Tree')
    ax.bar(x + width, hybrid_acc, width, label='Hybrid')

    ax.set_xlabel('Signal Type')
    ax.set_ylabel('Accuracy')
    ax.set_title('MDM Model Comparison: Per-Type Accuracy')
    ax.set_xticks(x)
    ax.set_xticklabels(class_names)
    ax.legend()
    ax.set_ylim(0, 1.0)

    return fig
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_indicator_filter.py tests/test_hybrid_engine.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADV-01 | State transitions consider history | unit | `uv run pytest tests/test_hybrid_engine.py::test_contextual_transitions -x` | Wave 0 |
| ADV-02 | HA Smoothed 55 filter toggle | unit | `uv run pytest tests/test_indicator_filter.py::test_ha_smooth_condition -x` | Wave 0 |
| ADV-03 | Confidence score in output | unit | `uv run pytest tests/test_indicator_filter.py::test_confidence_score -x` | Wave 0 |
| ADV-04 | Three-way dashboard runs | smoke | `uv run python analysis/compare_models.py` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_indicator_filter.py tests/test_hybrid_engine.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_indicator_filter.py::test_ha_smooth_bullish` -- HA condition True when green candle
- [ ] `tests/test_indicator_filter.py::test_ha_smooth_bearish` -- HA condition True when red candle
- [ ] `tests/test_indicator_filter.py::test_ha_smooth_nan_safe` -- NaN returns False
- [ ] `tests/test_indicator_filter.py::test_confidence_returned` -- evaluate() returns confidence float
- [ ] `tests/test_indicator_filter.py::test_ha_smooth_toggle_off` -- disabled by default, no effect
- [ ] `tests/test_hybrid_engine.py::test_confidence_column_exists` -- output DataFrame has confidence col
- [ ] `tests/test_hybrid_engine.py::test_state_history_tracking` -- state history populated on transitions
- [ ] `tests/test_hybrid_engine.py::test_contextual_cash_stickiness` -- context rules affect verdicts
- [ ] `tests/test_hybrid_engine.py::test_baseline_unchanged` -- filter_enabled=True without HA still matches Phase 14

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_hybrid/indicator_filter.py` -- current 6-condition filter with evaluate() logic
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` -- HybridEngine with two-phase commit pipeline
- `strategies/mdm_hybrid/config.py` -- HybridConfig and FilterConfig dataclasses
- `strategies/mdm_hybrid/position_manager.py` -- V2PositionManager with days_in_cash tracking
- `core/indicators.py` -- build_indicator_dataframe() including HA Smoothed 55 columns
- `analysis/validate_hybrid.py` -- Phase 14 validation pipeline (dashboard pattern reference)
- `analysis/rule_discovery.py` -- DecisionTreeClassifier for pure DT model

### Secondary (MEDIUM confidence)
- `.planning/phases/15-advanced-features/15-CONTEXT.md` -- user decisions and canonical refs
- `.planning/phases/12-indicator-filter-layer/12-CONTEXT.md` (referenced) -- D-02, D-04, D-07 design decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns already established
- Architecture: HIGH -- modifications follow existing patterns exactly, all target files read and understood
- Pitfalls: HIGH -- derived from direct code reading of call sites and data flow

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable codebase, no external dependency changes expected)
