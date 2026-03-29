# Phase 10: Discovery Validation - Research

**Researched:** 2026-03-29
**Domain:** scikit-learn model validation, matplotlib visualization, classification metrics
**Confidence:** HIGH

## Summary

Phase 10 validates the decision trees trained in Phase 9 against the full 962-signal history. The work involves three distinct deliverables: (1) match rate scoring with confusion matrices and per-type precision/recall, (2) era-based cross-validation quantifying structural change, and (3) a multi-panel matplotlib dashboard comparing discovered vs published signals on NASDAQ price charts.

All required libraries (scikit-learn 1.8.0, matplotlib 3.10.8, pandas 2.3.3, numpy 2.4.1) are already installed and verified. The Phase 9 `analysis/rule_discovery.py` module provides `train_era_tree()`, `split_by_era()`, and all feature/class constants that this phase reuses directly. The Phase 5 `analysis/validate_v2.py` provides a proven template for multi-panel dashboard generation and output file patterns.

**Primary recommendation:** Build a single `analysis/validate_discovery.py` script that retrains era trees (self-contained per D-09), scores all 962 signals with `predict()` and `predict_proba()`, generates confusion matrices via `sklearn.metrics`, and produces a two-era stacked dashboard using matplotlib. Output goes to `output/` directory following established project patterns.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Per-signal-date prediction -- for each of the 962 signal dates, predict Buy/Sell/Cash from indicator features using the trained decision tree. Compare predicted vs actual published signal.
- **D-02:** Report all predictions, but also show a filtered view for high-confidence rules (e.g., predict_proba >= 70%). Gives both full-picture and high-confidence subset metrics.
- **D-03:** Full confusion matrix (predicted vs actual) plus precision/recall per signal type (Buy/Sell/Cash). Shows not just overall accuracy but where errors concentrate.
- **D-04:** Era-based cross-validation: train on pre-2019 -> test on post-2019, AND train on post-2019 -> test on pre-2019. Tests whether rules generalize across the confirmed structural change.
- **D-05:** Frame cross-era results by quantifying degradation: report cross-era match rate alongside same-era rate. The delta measures structural change magnitude.
- **D-06:** NASDAQ price chart with published signals on top row and discovered-rule signals on bottom row. Color-coded: green=Buy, red=Sell, gray=Cash. Divergence points highlighted.
- **D-07:** Two era panels (pre-2019 and post-2019) stacked or side-by-side. Each era shows its own tree's predictions. Full 52-year single chart would be too dense for readable signal markers.
- **D-08:** Use sklearn `tree.predict()` and `tree.predict_proba()` directly on feature snapshots. No re-implementation of rules as Python code. Avoids translation errors.
- **D-09:** Retrain trees in the validation pipeline (self-contained). No saved model files -- validation script loads data, trains trees with same parameters as Phase 9, then scores. Matches Phase 9's functional approach.

### Claude's Discretion
- Exact matplotlib styling (colors, markers, figure dimensions, DPI)
- Script organization within `analysis/` (single file vs multiple)
- Confidence threshold value (70% suggested but adjustable)
- How to handle warm-up period signals (pre-200 trading days where MA200 is NaN)
- Report text formatting and section ordering
- Jupyter notebook cell structure and organization
- Whether to include a summary statistics panel on the dashboard chart

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAL-01 | Match rate scoring of discovered rules against full 962-signal history with per-type breakdown | `sklearn.metrics.classification_report` and `confusion_matrix` provide precision/recall/f1 per class. `predict_proba()` enables confidence filtering (D-02). Reuse `train_era_tree()` from Phase 9. |
| VAL-02 | Train/test validation with configurable split point (default: pre-2019 train, post-2019 test) | `split_by_era()` from Phase 9 handles era splitting. Cross-era scoring (D-04, D-05) requires training on one era and predicting on the other, then comparing same-era vs cross-era accuracy deltas. |
| VAL-03 | Comparison dashboard showing discovered rules' signals vs published signals on price chart | Phase 5 `generate_dashboard()` provides proven multi-panel matplotlib pattern. D-06/D-07 specify two-era stacked layout with published/discovered signal rows per era panel. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.8.0 | Decision tree predict/predict_proba, classification_report, confusion_matrix | Already installed from Phase 9; provides all needed classification metrics |
| matplotlib | 3.10.8 | Multi-panel dashboard chart generation | Already installed; project standard for all visualization |
| pandas | 2.3.3 | DataFrame operations, groupby for per-type metrics | Already installed; project standard for all data manipulation |
| numpy | 2.4.1 | Array operations for confidence thresholding | Already installed; project standard for numerical ops |

### Supporting
No additional libraries needed. All dependencies are already in place from Phases 8-9.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sklearn confusion_matrix | Manual pandas crosstab | sklearn provides standardized format + labels; no reason to hand-roll |
| matplotlib subplots | plotly | Project uses matplotlib exclusively; no need to introduce new dep |

## Architecture Patterns

### Recommended Project Structure
```
analysis/
  validate_discovery.py    # Main validation script (VAL-01, VAL-02, VAL-03)
  rule_discovery.py        # Phase 9 (imports: train_era_tree, split_by_era, constants)
output/
  discovery_validation_report.md   # Full text report
  discovery_match_rates.csv        # Per-signal predictions + actuals
  discovery_confusion_matrix.txt   # Confusion matrices
  discovery_dashboard.png          # Multi-panel comparison chart
```

### Pattern 1: Self-Contained Retrain-and-Score Pipeline
**What:** Validation script loads raw data, builds indicators, extracts features, trains trees with identical parameters to Phase 9, then scores -- no model serialization.
**When to use:** Per D-09, trees are retrained in the validation pipeline itself.
**Example:**
```python
# Source: Phase 9 rule_discovery.py pattern + D-09
from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from core.signal_loader import load_signal_fixture
from core.feature_snapshot import extract_feature_snapshot
from analysis.rule_discovery import (
    train_era_tree, split_by_era, BOOLEAN_FEATURES, CLASS_NAMES, ERA_SPLIT_DATE
)

# Load and prepare
ohlcv = DataLoader('nasdaq').load()
indicators = build_indicator_dataframe(ohlcv)
signals = load_signal_fixture('data/signals/nasdaq_signals_full.csv')
snapshot = extract_feature_snapshot(indicators, signals)
pre, post = split_by_era(snapshot)

# Train era-specific trees (same params as Phase 9)
pre_clf, pre_cv, pre_feat = train_era_tree(pre, BOOLEAN_FEATURES, max_depth=4)
post_clf, post_cv, post_feat = train_era_tree(post, BOOLEAN_FEATURES, max_depth=4)
```

### Pattern 2: Dual-View Scoring (Full + High-Confidence)
**What:** Score all predictions, then filter to high-confidence subset using predict_proba.
**When to use:** Per D-02, provides both full-picture and high-confidence metrics.
**Example:**
```python
from sklearn.metrics import classification_report, confusion_matrix

# Full scoring
preds = clf.predict(X)
proba = clf.predict_proba(X)

# Full metrics
full_report = classification_report(y_true, preds, labels=CLASS_NAMES, output_dict=True)
full_cm = confusion_matrix(y_true, preds, labels=CLASS_NAMES)

# High-confidence subset (D-02)
max_proba = proba.max(axis=1)
high_conf_mask = max_proba >= 0.70
if high_conf_mask.sum() > 0:
    hc_report = classification_report(
        y_true[high_conf_mask], preds[high_conf_mask],
        labels=CLASS_NAMES, output_dict=True
    )
```

### Pattern 3: Era Cross-Validation with Degradation Quantification
**What:** Train on era A, test on era B, and vice versa. Report both same-era and cross-era accuracy.
**When to use:** Per D-04 and D-05.
**Example:**
```python
# Same-era scoring (baseline)
pre_same = pre_clf.score(X_pre, y_pre)
post_same = post_clf.score(X_post, y_post)

# Cross-era scoring
pre_on_post = pre_clf.score(X_post, y_post)  # Pre-2019 rules on post-2019 data
post_on_pre = post_clf.score(X_pre, y_pre)   # Post-2019 rules on pre-2019 data

# Degradation delta (D-05)
pre_degradation = pre_same - pre_on_post
post_degradation = post_same - post_on_pre
```

### Pattern 4: Two-Era Stacked Dashboard
**What:** Two vertically stacked panels (pre-2019, post-2019), each showing NASDAQ price with published signals on top row and discovered signals on bottom row.
**When to use:** Per D-06 and D-07.
**Example:**
```python
# Source: validate_v2.py generate_dashboard() pattern adapted for era panels
matplotlib.use('Agg')
fig, axes = plt.subplots(2, 1, figsize=(18, 14), sharex=False)

for ax, era_df, era_name, clf in [(axes[0], pre, "Pre-2019", pre_clf),
                                    (axes[1], post, "Post-2019", post_clf)]:
    # Plot NASDAQ price
    ax.plot(era_df['date'], era_df['close'], color='black', linewidth=0.8)

    # Published signals (top markers)
    # Discovered signals (bottom markers with offset)
    # Divergence highlighting
```

### Anti-Patterns to Avoid
- **Serializing models to disk:** D-09 explicitly says no saved model files. Retrain in the script.
- **Re-implementing tree rules as Python code:** D-08 says use `predict()`/`predict_proba()` directly. No manual if/else chains.
- **Single 52-year chart:** D-07 says too dense. Use two era panels.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confusion matrix | Manual counting loop | `sklearn.metrics.confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)` | Handles missing classes, label ordering, edge cases |
| Per-class precision/recall | Manual TP/FP/FN counting | `sklearn.metrics.classification_report(output_dict=True)` | Returns dict with precision, recall, f1, support per class |
| Prediction confidence | Manual probability calculation | `clf.predict_proba(X).max(axis=1)` | Correct leaf probability from fitted tree |
| Era splitting | Date comparison logic | `split_by_era()` from Phase 9 | Already tested, handles the cutoff correctly |

## Common Pitfalls

### Pitfall 1: predict_proba Class Order Mismatch
**What goes wrong:** `predict_proba()` returns probabilities in `clf.classes_` order, which may not match CLASS_NAMES order.
**Why it happens:** scikit-learn sorts class labels alphabetically, so `clf.classes_` = ['Buy', 'Cash', 'Sell'] -- which happens to match CLASS_NAMES. But relying on this implicitly is fragile.
**How to avoid:** Always use `clf.classes_` to map probability columns, not hardcoded indices.
**Warning signs:** Confidence scores that seem inverted (high confidence for wrong class).

### Pitfall 2: Warm-Up Period NaN Features
**What goes wrong:** Signals before ~200 trading days from data start have NaN for MA200 and derived booleans.
**Why it happens:** MA200 requires 200 data points; early 1974 signals lack this history.
**How to avoid:** Either drop signals with NaN features before scoring (with a note in the report), or fill NaN booleans with False (matching extract_feature_snapshot behavior). Document how many signals were affected.
**Warning signs:** NaN in predictions, sklearn warnings about NaN input.

### Pitfall 3: Class Imbalance in Post-2019 Era
**What goes wrong:** Post-2019 era has very few Sell signals (~15), causing unstable per-class metrics.
**Why it happens:** Dr. K's post-2019 MDM uses Cash as intermediate state, reducing Sell count.
**How to avoid:** Already handled by `class_weight='balanced'` in `train_era_tree()`. Report sample counts alongside metrics. Use `zero_division=0` in classification_report.
**Warning signs:** 0% or 100% precision/recall for Sell in post-2019.

### Pitfall 4: Cross-Era Accuracy Misinterpretation
**What goes wrong:** Low cross-era accuracy interpreted as "bad model" rather than "confirmed structural change."
**Why it happens:** D-05 explicitly says the delta measures structural change magnitude -- it's informational, not a pass/fail gate.
**How to avoid:** Frame cross-era degradation as evidence quantifying the pre/post-2019 structural shift. The report narrative matters.
**Warning signs:** N/A -- this is a framing issue, not a code bug.

### Pitfall 5: Matplotlib Backend on Headless Windows
**What goes wrong:** `plt.show()` blocks or errors without a display.
**Why it happens:** Script runs from CLI without GUI.
**How to avoid:** Use `matplotlib.use('Agg')` before importing pyplot (already done in validate_v2.py pattern). Save to PNG only.
**Warning signs:** "Tcl_AsyncDelete" errors or hanging script.

## Code Examples

### Confusion Matrix with Labels
```python
# Source: sklearn.metrics documentation, verified with sklearn 1.8.0
from sklearn.metrics import confusion_matrix, classification_report

CLASS_NAMES = ['Buy', 'Cash', 'Sell']

cm = confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)
# cm[i][j] = count of true=CLASS_NAMES[i] predicted as CLASS_NAMES[j]

report = classification_report(
    y_true, y_pred,
    labels=CLASS_NAMES,
    output_dict=True,
    zero_division=0,
)
# report['Buy']['precision'], report['Buy']['recall'], etc.
# report['accuracy'] for overall
# report['macro avg'] for unweighted average
```

### predict_proba Confidence Filtering
```python
# Source: sklearn DecisionTreeClassifier docs
proba = clf.predict_proba(X_test)  # shape (n_samples, n_classes)
max_proba = proba.max(axis=1)       # highest class probability per sample
preds = clf.predict(X_test)

# Map class indices to names
class_map = {i: name for i, name in enumerate(clf.classes_)}

# High-confidence subset
threshold = 0.70
mask = max_proba >= threshold
print(f"High-confidence: {mask.sum()}/{len(mask)} ({mask.mean():.0%})")
```

### Multi-Panel Era Dashboard
```python
# Source: validate_v2.py generate_dashboard() pattern, adapted for D-06/D-07
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

fig, (ax_pre, ax_post) = plt.subplots(
    2, 1, figsize=(18, 14), sharex=False
)

# Color scheme per D-06
colors = {'Buy': 'green', 'Sell': 'red', 'Cash': 'gray'}

for ax, era_data, era_name in [(ax_pre, pre_data, 'Pre-2019'),
                                 (ax_post, post_data, 'Post-2019')]:
    ax.plot(era_data['date'], era_data['close'], 'k-', linewidth=0.8)
    ax.set_title(f'{era_name} Era')

    # Published signals (triangles above price)
    for sig_type, marker in [('Buy', '^'), ('Sell', 'v'), ('Cash', 'o')]:
        mask = era_data['signal'] == sig_type
        ax.scatter(era_data.loc[mask, 'date'],
                   era_data.loc[mask, 'close'] * 1.02,
                   marker=marker, c=colors[sig_type], s=60,
                   alpha=0.8, zorder=5, label=f'Published {sig_type}')

    # Discovered signals (diamonds below price)
    for sig_type, marker in [('Buy', 'D'), ('Sell', 's'), ('Cash', 'x')]:
        mask = era_data['predicted'] == sig_type
        ax.scatter(era_data.loc[mask, 'date'],
                   era_data.loc[mask, 'close'] * 0.98,
                   marker=marker, c=colors[sig_type], s=40,
                   alpha=0.6, zorder=4, label=f'Discovered {sig_type}')

plt.tight_layout()
fig.savefig('output/discovery_dashboard.png', dpi=150, bbox_inches='tight')
plt.close(fig)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_discovery_validation.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAL-01 | Match rate scoring produces per-type breakdown with confusion matrix | unit | `uv run pytest tests/test_discovery_validation.py::test_match_rate_scoring -x` | Wave 0 |
| VAL-01 | High-confidence filtering returns subset metrics | unit | `uv run pytest tests/test_discovery_validation.py::test_high_confidence_filtering -x` | Wave 0 |
| VAL-02 | Cross-era validation trains on one era and scores on other | unit | `uv run pytest tests/test_discovery_validation.py::test_cross_era_validation -x` | Wave 0 |
| VAL-02 | Degradation quantification reports same-era vs cross-era delta | unit | `uv run pytest tests/test_discovery_validation.py::test_degradation_quantification -x` | Wave 0 |
| VAL-03 | Dashboard generates PNG file with two era panels | smoke | `uv run pytest tests/test_discovery_validation.py::test_dashboard_generates_png -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_discovery_validation.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_discovery_validation.py` -- covers VAL-01, VAL-02, VAL-03
- Mock snapshot fixture can reuse `_make_mock_snapshot()` pattern from `tests/test_rule_discovery.py`

## Sources

### Primary (HIGH confidence)
- `analysis/rule_discovery.py` -- Phase 9 implementation with train_era_tree, split_by_era, extract_rules, constants (BOOLEAN_FEATURES, CLASS_NAMES, ERA_SPLIT_DATE)
- `analysis/validate_v2.py` -- Phase 5 validation pipeline with generate_dashboard multi-panel pattern
- `core/feature_snapshot.py` -- extract_feature_snapshot producing 962-row DataFrame
- scikit-learn 1.8.0 verified: classification_report, confusion_matrix, predict_proba all confirmed working
- matplotlib 3.10.8 verified: Agg backend, subplots, savefig confirmed

### Secondary (MEDIUM confidence)
- sklearn.metrics API behavior verified via local execution (predict_proba shape, class ordering)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and verified
- Architecture: HIGH - follows established Phase 5 and Phase 9 patterns exactly
- Pitfalls: HIGH - based on direct code inspection and local testing

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable domain, no fast-moving dependencies)
