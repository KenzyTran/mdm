# Phase 14: Hybrid Validation - Research

**Researched:** 2026-03-29
**Domain:** Signal validation, confusion matrix analysis, held-out test methodology
**Confidence:** HIGH

## Summary

Phase 14 validates the hybrid MDM engine (built in Phases 11-13) against all 962 published signals. The core challenge is adapting the existing `signal_comparator.py` infrastructure to work with the hybrid engine's output, computing confusion matrices with per-type accuracy, and establishing a held-out discipline for post-2019 signals before any filter tuning occurs.

The project already has all the building blocks: `extract_model_signals()` maps BUY/SELL/CASH states to Buy/Sell/Cash signals, `compare_signals()` computes match rates with per-type breakdown, and `validate_discovery.py` demonstrates confusion matrix generation with `sklearn.metrics`. The hybrid engine already produces signal log columns (old_state, proposed, verdict) on every trading day. The main work is: (1) a validation script that runs the hybrid engine on full NASDAQ data, compares against 962 signals, and reports confusion matrices; (2) a held-out split of post-2019 signals locked before tuning; (3) a diagnostic signal log linking proposed/verdict/final for every day.

**Primary recommendation:** Build a single `analysis/validate_hybrid.py` script that reuses `core/signal_comparator` for match rates and `sklearn.metrics` for confusion matrices, following the established pattern from `analysis/validate_discovery.py` and `analysis/validate_v2.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAL-04 | Validate hybrid model on full 962 published signals with confusion matrix and per-type accuracy | Reuse `extract_model_signals()` + `compare_signals()` from `core/signal_comparator.py`; `sklearn.metrics.confusion_matrix` and `classification_report` for per-type metrics; 962 signals available in `data/signals/nasdaq_signals_full.csv` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, signal alignment | Already used throughout project |
| numpy | >= 1.24.0 | Numerical array operations | Already used throughout project |
| scikit-learn | (already installed) | confusion_matrix, classification_report | Already used in Phase 10 validate_discovery.py |
| matplotlib | >= 3.7.0 | Confusion matrix heatmap, dashboard charts | Already used throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| core/signal_comparator | project module | extract_model_signals, compare_signals | Match rate computation |
| core/signal_loader | project module | load_signal_fixture | Load 962-signal ground truth |
| core/data_loader | project module | DataLoader('nasdaq') | Load NASDAQ OHLCV data |

**Installation:** No new packages needed. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
analysis/
  validate_hybrid.py         # Main validation script (NEW)
output/
  hybrid_validation_report.md    # Markdown report (generated)
  hybrid_confusion_matrix.txt    # Confusion matrices (generated)
  hybrid_match_rates.csv         # Per-signal predictions (generated)
  hybrid_signal_log.csv          # Full signal log (generated)
  hybrid_dashboard.png           # Visual dashboard (generated)
tests/
  test_hybrid_validation.py      # Validation tests (NEW)
```

### Pattern 1: Signal Extraction from Hybrid Engine
**What:** The hybrid engine's `state` column uses BUY/CASH/SELL values. `extract_model_signals()` already maps these via STATE_TO_SIGNAL dict (BUY->Buy, SELL->Sell, CASH->Cash). This produces signal transitions compatible with `compare_signals()`.
**When to use:** Whenever comparing hybrid output against published signals.
**Example:**
```python
# From core/signal_comparator.py - already handles hybrid states
STATE_TO_SIGNAL = {
    "BUY": "Buy",
    "SELL": "Sell",
    "CASH": "Cash",
}
model_signals = extract_model_signals(hybrid_results)
comparison = compare_signals(model_signals, published_signals)
```

### Pattern 2: Confusion Matrix with sklearn
**What:** Use sklearn confusion_matrix with explicit labels=['Buy', 'Cash', 'Sell'] for consistent ordering.
**When to use:** Per-type accuracy reporting.
**Example:**
```python
# Pattern from analysis/validate_discovery.py
from sklearn.metrics import confusion_matrix, classification_report
CLASS_NAMES = ['Buy', 'Cash', 'Sell']
cm = confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)
report = classification_report(y_true, y_pred, labels=CLASS_NAMES, output_dict=True, zero_division=0)
```

### Pattern 3: Held-Out Split for Post-2019 Signals
**What:** Post-2019 has 99 signals. The phase requires 19+ held-out signals locked before tuning. A 80/20 split gives ~79 tune / ~20 held-out. Selection must be deterministic and chronological (not random) to prevent look-ahead bias.
**When to use:** Before any filter parameter tuning.
**Example:**
```python
# Chronological split: last 20 post-2019 signals are held out
post_2019 = full_signals[full_signals['date'] >= '2019-01-01']
n_heldout = max(19, len(post_2019) // 5)  # At least 19, ~20%
tune_signals = post_2019.iloc[:-n_heldout]
heldout_signals = post_2019.iloc[-n_heldout:]
# Lock held-out set: save to file or define as constant dates
```

### Pattern 4: Diagnostic Signal Log
**What:** The hybrid engine already populates `old_state`, `proposed`, `verdict` columns on every trading day (Phase 13 D-09, D-10). Phase 14 needs to match these to published signal dates to show "proposed X, filter said Y, final Z".
**When to use:** Diagnosing where filter helps vs hurts.
**Example:**
```python
# Merge hybrid results with published signals on date
signal_dates = published_signals['date'].values
log_at_signals = hybrid_results[hybrid_results['date'].isin(signal_dates)]
diagnosis = log_at_signals[['date', 'old_state', 'proposed', 'verdict', 'state', 'action']].copy()
diagnosis = diagnosis.rename(columns={'state': 'final_state'})
```

### Anti-Patterns to Avoid
- **Random held-out selection:** Must be chronological to avoid leaking future information into tuning set.
- **Tuning before locking held-out:** The held-out set must be defined and saved BEFORE any filter parameter changes.
- **Comparing only post-2019:** The full 962-signal history must be scored for overall accuracy.
- **Ignoring indicator warm-up period:** The first ~200 trading days lack EMA/MACD values. Signals before the warm-up period should be handled (NaN indicators -> default verdict).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Signal extraction | Custom state-to-signal mapping | `extract_model_signals()` from `core/signal_comparator.py` | Already handles BUY/SELL/CASH mapping |
| Match rate computation | Manual date matching and counting | `compare_signals()` from `core/signal_comparator.py` | Handles alignment, per-type breakdown |
| Confusion matrix | Manual counting loop | `sklearn.metrics.confusion_matrix` | Handles edge cases, standardized labels |
| Classification report | Manual precision/recall calc | `sklearn.metrics.classification_report` | F1, support, macro/weighted averages |
| Signal loading | CSV parsing code | `load_signal_fixture()` from `core/signal_loader.py` | Validated date parsing, signal type checking |

**Key insight:** Phase 10's `validate_discovery.py` already built the full confusion matrix + cross-era validation pipeline. Phase 14 follows the same pattern but swaps the decision tree classifier for the hybrid engine.

## Common Pitfalls

### Pitfall 1: Indicator Warm-Up NaN Period
**What goes wrong:** Early signals (pre-1975) have no EMA/MACD values due to warm-up period. The hybrid engine with filter enabled might behave differently on these rows.
**Why it happens:** EMA 55 needs ~55 days, MA 200 needs ~200 days of data. NASDAQ data starts 1971 but filter indicators are NaN until warm-up completes.
**How to avoid:** Run hybrid engine on full NASDAQ data from 1971+. The indicator filter already handles NaN (returns CONFIRM when indicators are NaN per IndicatorFilter design). Report accuracy separately for warm-up vs post-warm-up periods, or simply note warm-up coverage.
**Warning signs:** Unexpectedly high match rate on early signals (engine defaulting to CONFIRM on NaN indicators).

### Pitfall 2: Signal Date Alignment
**What goes wrong:** Published signal dates may not exactly align with OHLCV trading days (weekends, holidays). `compare_signals()` uses exact date matching.
**Why it happens:** Some signal dates in the CSV may be recorded on non-trading days.
**How to avoid:** Use `check_signal_date_alignment()` from `core/signal_loader.py` first. Already validated in Phase 7 but worth a sanity check.
**Warning signs:** Unexpectedly low match count.

### Pitfall 3: V2 Baseline Measurement Inconsistency
**What goes wrong:** The 56.7% baseline from v2 may have been measured on a different signal subset or with different alignment rules.
**Why it happens:** V2 validation in Phase 5 used `nasdaq_signals.csv` (post-2019 only, fewer signals), not `nasdaq_signals_full.csv` (962 signals).
**How to avoid:** Re-run v2 baseline measurement on exactly the same signal set (962 signals from `nasdaq_signals_full.csv`) and same period filter to ensure apples-to-apples comparison. Report both: v2 on post-2019 (original baseline) and v2 on full 962.
**Warning signs:** Different baseline number than expected 56.7%.

### Pitfall 4: Confusion Matrix Label Ordering
**What goes wrong:** Confusion matrix rows/columns get scrambled if labels parameter is not explicit.
**Why it happens:** sklearn infers labels from data, which may not include all 3 types if one type has no predictions.
**How to avoid:** Always pass `labels=['Buy', 'Cash', 'Sell']` to `confusion_matrix()` and `classification_report()`.
**Warning signs:** Matrix has fewer than 3x3 cells.

### Pitfall 5: Held-Out Contamination Through Full-Data Training
**What goes wrong:** If the v2 state machine parameters were already optimized on post-2019 data (Phase 4 parameter sweep), the held-out set is partially contaminated.
**Why it happens:** Parameter sweep in Phase 4 used train/held-out split but covered 2019-2022 train.
**How to avoid:** Acknowledge this limitation. The held-out set for Phase 14 validates the FILTER tuning (not state machine parameters). Use the latest 20 post-2019 signals as held-out since those were not in the Phase 4 training window.
**Warning signs:** Over-optimistic held-out accuracy.

## Code Examples

### Running Hybrid Engine on Full NASDAQ Data
```python
from core.data_loader import DataLoader
from strategies.mdm_hybrid.config import HybridConfig
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine

loader = DataLoader('nasdaq')
df = loader.load()

config = HybridConfig(filter_enabled=True)
engine = HybridEngine(config)
results = engine.run(df)
```

### Computing Match Rates Against 962 Signals
```python
from core.signal_comparator import extract_model_signals, compare_signals
from core.signal_loader import load_signal_fixture

published = load_signal_fixture('data/signals/nasdaq_signals_full.csv')
model_signals = extract_model_signals(results)
comparison = compare_signals(model_signals, published)

print(f"Overall: {comparison['match_rate']:.1f}%")
for sig_type, data in comparison['per_type'].items():
    print(f"  {sig_type}: {data['rate']:.1f}% ({data['matched']}/{data['published']})")
```

### Building Confusion Matrix at Signal Dates
```python
import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report

CLASS_NAMES = ['Buy', 'Cash', 'Sell']

# For each published signal date, find the hybrid engine's state on that date
merged = pd.merge(
    published[['date', 'signal']],
    results[['date', 'state']],
    on='date',
    how='inner'
)
# Map engine state to signal type
STATE_TO_SIGNAL = {"BUY": "Buy", "SELL": "Sell", "CASH": "Cash"}
merged['predicted'] = merged['state'].map(STATE_TO_SIGNAL)

y_true = merged['signal'].values
y_pred = merged['predicted'].values

cm = confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)
report = classification_report(y_true, y_pred, labels=CLASS_NAMES, output_dict=True, zero_division=0)
```

### Held-Out Split (Chronological)
```python
post_2019 = published[published['date'] >= pd.Timestamp('2019-01-01')]
# Last 20 signals are held out (chronological, no randomness)
HELDOUT_COUNT = 20
tune_set = post_2019.iloc[:-HELDOUT_COUNT]
heldout_set = post_2019.iloc[-HELDOUT_COUNT:]
# Lock held-out dates before any tuning
HELDOUT_DATES = heldout_set['date'].tolist()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure state machine (v2) | Hybrid: state machine + indicator filter | Phase 11-13 (v3.0) | Filter can confirm, veto, or override signals |
| Decision tree classifier (Phase 10) | Hybrid rule-based engine | Phase 11-13 (v3.0) | Interpretable rules instead of ML model |
| Match rate only (Phase 5) | Confusion matrix + per-type accuracy | Phase 10+ | Much richer diagnosis of where model fails |

## Open Questions

1. **Exact v2 baseline on 962 signals**
   - What we know: v2 achieved 56.7% on post-2019 signals (Phase 5, using `nasdaq_signals.csv`)
   - What's unclear: What is v2's accuracy on the full 962-signal set? The 56.7% was post-2019 only.
   - Recommendation: Re-run v2 engine on full NASDAQ data and score against all 962 signals as part of validation script to establish exact comparable baseline.

2. **Filter behavior on pre-2019 signals**
   - What we know: Filter conditions (especially close_above_ema55) are post-2019 dominant. Pre-2019 signals have different indicator patterns.
   - What's unclear: Will the filter help or hurt on pre-2019 signals?
   - Recommendation: Report pre-2019 vs post-2019 accuracy separately. The filter is expected to help post-2019 and be neutral/slightly negative pre-2019.

3. **Signal type at published signal dates vs transition detection**
   - What we know: `extract_model_signals()` detects state TRANSITIONS. Published signals are also transitions. But the hybrid engine's current state at a published signal date may differ from whether a transition happened on that exact date.
   - What's unclear: Should we compare transitions (model signal on date X matches published signal on date X) or states (model is in BUY state on the date published says Buy)?
   - Recommendation: Use BOTH approaches -- transition-based via `compare_signals()` for consistency with prior phases, and state-based (engine state on signal date) for the confusion matrix. Report both.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none -- pytest discovered via pyproject.toml |
| Quick run command | `uv run pytest tests/test_hybrid_validation.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAL-04 | Confusion matrix with per-type accuracy on 962 signals | integration | `uv run pytest tests/test_hybrid_validation.py::test_confusion_matrix_per_type -x` | Wave 0 |
| VAL-04 | Post-2019 accuracy vs 56.7% baseline | integration | `uv run pytest tests/test_hybrid_validation.py::test_post2019_vs_baseline -x` | Wave 0 |
| VAL-04 | Signal log with proposed/verdict/final | integration | `uv run pytest tests/test_hybrid_validation.py::test_signal_log_diagnosis -x` | Wave 0 |
| VAL-04 | Held-out set locked before tuning | unit | `uv run pytest tests/test_hybrid_validation.py::test_heldout_set_locked -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_hybrid_validation.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_hybrid_validation.py` -- covers VAL-04 (confusion matrix, baseline comparison, signal log, held-out)
- [ ] No new framework install needed (pytest + sklearn already available)

## Data Inventory

| Data | Location | Format | Records | Notes |
|------|----------|--------|---------|-------|
| Full signal history | `data/signals/nasdaq_signals_full.csv` | CSV: date, signal, gain_loss_pct, dollar_becomes | 962 signals | 863 pre-2019, 99 post-2019 |
| Post-2019 signals | subset of above | same | 99 signals | 38 Buy, 44 Cash, 17 Sell |
| NASDAQ OHLCV | loaded via `DataLoader('nasdaq')` | CSV | ~13K+ trading days | 1971+ to present |
| Post-2019 only signals | `data/signals/nasdaq_signals.csv` | CSV | ~95 signals | Used in Phase 5 for 56.7% baseline |

## Sources

### Primary (HIGH confidence)
- `core/signal_comparator.py` -- extract_model_signals, compare_signals (project code, verified)
- `analysis/validate_discovery.py` -- confusion matrix pattern, classification_report usage (project code, verified)
- `analysis/validate_v2.py` -- validation pipeline pattern, held-out split, dashboard generation (project code, verified)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` -- hybrid engine with signal log columns (project code, verified)
- `strategies/mdm_hybrid/indicator_filter.py` -- IndicatorFilter.evaluate(), Verdict enum (project code, verified)
- `data/signals/nasdaq_signals_full.csv` -- 962 signals confirmed (962 lines + header)

### Secondary (MEDIUM confidence)
- sklearn confusion_matrix and classification_report -- standard API, well-documented
- 56.7% v2 baseline -- from Phase 5 validation, measured on post-2019 `nasdaq_signals.csv` (may differ slightly from full 962 set)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and used in prior phases
- Architecture: HIGH - follows exact same pattern as Phase 10 validate_discovery.py
- Pitfalls: HIGH - identified from code review of existing comparator and signal alignment logic

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable domain, no external dependencies changing)
