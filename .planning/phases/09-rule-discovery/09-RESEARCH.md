# Phase 9: Rule Discovery - Research

**Researched:** 2026-03-29
**Domain:** Statistical profiling, decision tree classification, rule extraction from indicator features
**Confidence:** HIGH

## Summary

Phase 9 takes the 962-row feature snapshot (produced by Phase 8) containing 8 boolean features and continuous indicator values at each signal date, and discovers the indicator-based rules that drive Buy/Sell/Cash signal transitions. The work involves three layers: (1) statistical profiling of indicator conditions per signal type, (2) training scikit-learn DecisionTreeClassifier models to classify signals, and (3) extracting human-readable rules from the trained trees. All analysis must be era-aware, splitting at Feb 9, 2019.

The dataset is clean -- zero NaNs in all indicator columns, 962 samples total with reasonable class balance overall (Buy=333, Cash=339, Sell=290). The post-2019 era has only 95 samples with significant class imbalance (Sell=15, Buy=37, Cash=43), which constrains what the decision tree can reliably learn for that era.

**Primary recommendation:** Use scikit-learn 1.8.0 DecisionTreeClassifier with max_depth=4-5, class_weight='balanced' for the imbalanced post-2019 era, and export_text() for rule extraction. Statistical profiling via pandas crosstab/groupby on the 8 boolean features plus continuous indicator distributions per signal type.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Classify each signal date as Buy, Sell, or Cash based on indicator conditions at that moment. This is a 3-class classification on 962 samples -- not transition-based.
- **D-02:** Binary split at Feb 9, 2019. Train separate decision trees for pre-2019 and post-2019 eras. This directly tests the confirmed structural change hypothesis from v1.0 analysis.
- **D-03:** Max tree depth capped at 4-5 levels to keep extracted rules human-readable and avoid overfitting on 962 samples.
- **D-04:** Human-readable rule strings printed to console and saved to a text/markdown report file. Format matches DISC-03 requirement: "Buy when EMA9 > EMA21 AND MACD histogram > 0: 78% confidence".
- **D-05:** Rule discovery code lives in `analysis/rule_discovery.py` as a standalone analysis script, consistent with existing `analysis/` directory pattern.

### Claude's Discretion
- Statistical profiling depth (DISC-01): whether to include continuous indicator distributions alongside boolean feature frequency tables
- Feature selection for decision tree: boolean-only vs boolean+continuous features
- Class imbalance handling strategy
- scikit-learn DecisionTreeClassifier hyperparameters beyond max_depth
- Statistical profiling visualization approach
- Report file format and structure details

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISC-01 | Statistical profile of indicator conditions at each signal type showing frequency distributions | pandas crosstab on 8 boolean features + groupby describe on continuous indicators; separation visible in frequency tables |
| DISC-02 | Decision tree model trained on indicator features to classify signal transitions | scikit-learn 1.8.0 DecisionTreeClassifier, max_depth=4-5, class_weight='balanced', trained separately for pre/post-2019 |
| DISC-03 | Extracted human-readable rules from decision tree with confidence scores | sklearn.tree.export_text() + custom traversal to produce "Buy when X AND Y: N% confidence" format |
| DISC-04 | Era-aware analysis comparing pre-2019 vs post-2019 rule patterns | Binary split at 2019-02-09; separate trees trained per era; rule comparison in output report |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.8.0 | Decision tree classifier + rule export | Industry standard for interpretable ML; export_text() built-in |
| pandas | >=2.0.0 | Statistical profiling via crosstab, groupby, describe | Already in project |
| numpy | >=1.24.0 | Array operations for feature matrices | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| matplotlib | >=3.7.0 | Optional: tree visualization, bar charts for frequency distributions | If visual profiling desired |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DecisionTreeClassifier | Random Forest | Loses interpretability -- rules not extractable as single paths |
| export_text | graphviz export_graphviz | Requires graphviz system install; text output matches D-04 better |

**Installation:**
```bash
cd C:/Users/trant/projects/mdm
# Add to pyproject.toml dependencies, then:
uv sync
```

scikit-learn 1.8.0 will pull in: joblib 1.5.3, scipy 1.17.1, threadpoolctl 3.6.0.

## Architecture Patterns

### Recommended Project Structure
```
analysis/
    rule_discovery.py    # Main analysis script (D-05)
output/
    rule_discovery_report.md   # Generated report with rules + stats
```

### Pattern 1: Standalone Analysis Script
**What:** Single-file script following existing `analysis/` pattern (like `validate_v2.py`).
**When to use:** This phase -- produces report output, not reusable library code.
**Structure:**
```python
"""Rule Discovery Analysis Script

Discovers indicator-based rules driving Buy/Sell/Cash signal transitions
through statistical profiling and decision tree extraction.

Usage:
    uv run python analysis/rule_discovery.py
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from core.signal_loader import load_signal_fixture
from core.feature_snapshot import extract_feature_snapshot


# Constants
ERA_SPLIT_DATE = '2019-02-09'
SIGNAL_CSV = 'data/signals/nasdaq_signals_full.csv'
BOOLEAN_FEATURES = [
    'ema9_above_ema21', 'ema21_above_ema55', 'close_above_ma200',
    'close_above_ema9', 'close_above_ema21', 'close_above_ema55',
    'macd_histogram_positive', 'macd_above_signal',
]
CONTINUOUS_FEATURES = [
    'macd', 'macd_signal', 'macd_histogram',
    'ema9', 'ema21', 'ema55', 'ma200',
]
```

### Pattern 2: Era-Aware Analysis
**What:** Split dataset at Feb 9, 2019 and run identical analysis pipeline on each era separately.
**When to use:** All DISC requirements -- statistical profiling and tree training both era-aware.
```python
def split_by_era(snapshot: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split snapshot into pre-2019 and post-2019 eras."""
    mask = snapshot['date'] < pd.Timestamp(ERA_SPLIT_DATE)
    return snapshot[mask].copy(), snapshot[~mask].copy()
```

### Pattern 3: Rule Extraction from Decision Tree
**What:** Walk the trained tree to produce human-readable rule strings with confidence scores.
**When to use:** After tree training -- converts sklearn internals to D-04 output format.
```python
from sklearn.tree import _tree

def extract_rules(tree: DecisionTreeClassifier, feature_names: list, class_names: list) -> list[str]:
    """Extract human-readable rules from a trained decision tree.

    Returns list of rule strings like:
    "Buy when ema9_above_ema21 AND macd_histogram_positive: 78% confidence (N=45)"
    """
    tree_ = tree.tree_
    rules = []

    def recurse(node, conditions):
        if tree_.feature[node] == _tree.TREE_UNDEFINED:
            # Leaf node
            counts = tree_.value[node][0]
            total = counts.sum()
            predicted_class_idx = counts.argmax()
            confidence = counts[predicted_class_idx] / total
            class_name = class_names[predicted_class_idx]
            condition_str = " AND ".join(conditions) if conditions else "always"
            rules.append(
                f"{class_name} when {condition_str}: "
                f"{confidence:.0%} confidence (N={int(total)})"
            )
            return

        feature = feature_names[tree_.feature[node]]
        threshold = tree_.threshold[node]

        # Left branch: feature <= threshold
        left_cond = f"{feature} <= {threshold:.4f}"
        recurse(tree_.children_left[node], conditions + [left_cond])

        # Right branch: feature > threshold
        right_cond = f"{feature} > {threshold:.4f}"
        recurse(tree_.children_right[node], conditions + [right_cond])

    recurse(0, [])
    return rules
```

### Pattern 4: Statistical Profiling
**What:** Frequency tables for boolean features + descriptive stats for continuous features, grouped by signal type.
```python
def profile_boolean_features(snapshot: pd.DataFrame, bool_cols: list) -> pd.DataFrame:
    """Produce frequency table: % True for each boolean feature, per signal type."""
    return snapshot.groupby('signal')[bool_cols].mean().T

def profile_continuous_features(snapshot: pd.DataFrame, cont_cols: list) -> pd.DataFrame:
    """Produce descriptive stats for continuous features, per signal type."""
    return snapshot.groupby('signal')[cont_cols].describe()
```

### Anti-Patterns to Avoid
- **Overfitting on small post-2019 set:** With only 95 samples (Sell=15), deep trees will memorize. Stick to max_depth=4-5 per D-03.
- **Ignoring class imbalance in post-2019:** Sell has only 15 samples vs Cash=43. Must use class_weight='balanced'.
- **Mixing eras before profiling:** Each era must be profiled independently to surface structural changes per DISC-04.
- **Using boolean-only features when continuous add value:** The profiling step should reveal whether continuous features (MACD value, distance from MA) add discriminability beyond boolean crossover states. Decision on feature set should follow evidence.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decision tree training | Custom tree implementation | sklearn.tree.DecisionTreeClassifier | Handles splits, pruning, class weights |
| Rule text export | Manual tree traversal for basic text | sklearn.tree.export_text() | Built-in, handles formatting |
| Custom rule format | - | Custom traversal of tree_.tree_ internals | export_text gives tree structure; custom traversal needed for "X when Y: Z% confidence" format per D-04 |
| Cross-validation | Manual train/test splitting | sklearn.model_selection.cross_val_score | Proper stratified k-fold on small datasets |
| Frequency tables | Manual counting loops | pandas.crosstab() or groupby().mean() | Vectorized, handles edge cases |

**Key insight:** scikit-learn's export_text() gives a readable tree structure, but the specific D-04 format ("Buy when X AND Y: Z% confidence") requires walking the tree internals via tree_.tree_ attributes. Both approaches should be used -- export_text for the full tree view, custom traversal for the condensed rule list.

## Common Pitfalls

### Pitfall 1: Post-2019 Overfitting
**What goes wrong:** Decision tree achieves 95%+ accuracy on 95 samples by memorizing individual cases, producing rules that don't generalize.
**Why it happens:** Small sample size (95), class imbalance (Sell=15), max_depth=4 creates up to 16 leaf nodes for 95 samples.
**How to avoid:** Use stratified cross-validation (5-fold) to report honest accuracy. Report both train accuracy and cross-validated accuracy. If CV accuracy is much lower than train accuracy, note overfitting risk.
**Warning signs:** Train accuracy above 85% with CV accuracy below 60%.

### Pitfall 2: Boolean Features Masking Signal
**What goes wrong:** Using only 8 boolean features loses granularity. Two signals with ema9_above_ema21=True might have very different EMA gap sizes (barely crossing vs strongly above).
**Why it happens:** Boolean encoding discards magnitude information.
**How to avoid:** Statistical profiling (DISC-01) should examine both boolean frequencies AND continuous distributions. If continuous features show clear separation that booleans miss, include them in the tree.
**Warning signs:** Boolean-only tree has low accuracy but continuous feature distributions show clear separation between signal types.

### Pitfall 3: Ignoring Class Priors in Confidence Scores
**What goes wrong:** A rule says "Buy: 45% confidence" but the base rate for Buy is 35% -- this rule is actually informative, not weak.
**Why it happens:** Confidence = leaf class proportion, which is affected by overall class distribution.
**How to avoid:** Report both raw confidence and lift over base rate in rule output. A rule with 45% confidence when base rate is 35% has 1.3x lift.
**Warning signs:** All rules show confidence near base rates.

### Pitfall 4: Feature Leakage from Price Columns
**What goes wrong:** Including raw price (close, open, high, low) as features. The tree splits on absolute price levels which are non-stationary (NASDAQ at 100 in 1974 vs 15000 in 2024).
**Why it happens:** The snapshot has raw OHLCV columns alongside indicator columns.
**How to avoid:** Feature set must be limited to indicators and derived booleans -- NOT raw OHLCV prices. Indicators (EMA ratios, MACD) are scale-invariant by construction.
**Warning signs:** Tree splits on close > 5000 or similar absolute thresholds.

### Pitfall 5: HA Smoothed Features Highly Correlated
**What goes wrong:** Including all 4 HA Smoothed columns (ha_smooth_open/high/low/close) alongside EMA features adds multicollinearity without new information for tree splitting.
**Why it happens:** HA Smoothed is derived from EMA(55) of OHLC, which overlaps heavily with EMA55 and general price trend.
**How to avoid:** Either use HA Smoothed candle color (ha_smooth_close > ha_smooth_open as boolean) as a single derived feature, or exclude HA Smoothed columns if they don't improve tree accuracy.
**Warning signs:** Tree never splits on HA features, or splits are redundant with EMA splits.

## Code Examples

### Loading the Feature Snapshot
```python
# Source: core/feature_snapshot.py (verified in project)
from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from core.signal_loader import load_signal_fixture
from core.feature_snapshot import extract_feature_snapshot

dl = DataLoader('nasdaq')
ohlcv = dl.load()
indicators = build_indicator_dataframe(ohlcv)
signals = load_signal_fixture('data/signals/nasdaq_signals_full.csv')
snapshot = extract_feature_snapshot(indicators, signals)
# Shape: (962, 27) -- 8 bool features, continuous indicators, signal column
```

### Training Era-Aware Decision Tree
```python
# Source: scikit-learn 1.8.0 official docs
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import cross_val_score

feature_cols = BOOLEAN_FEATURES  # Start with boolean; add continuous if profiling warrants
class_names = ['Buy', 'Cash', 'Sell']

X = era_df[feature_cols].values
y = era_df['signal'].values

clf = DecisionTreeClassifier(
    max_depth=4,                  # D-03: cap at 4-5
    class_weight='balanced',      # Handle imbalance
    random_state=42,              # Reproducibility
    min_samples_leaf=5,           # Prevent single-sample leaves
)
clf.fit(X, y)

# Cross-validated accuracy
cv_scores = cross_val_score(clf, X, y, cv=5, scoring='accuracy')
print(f"CV Accuracy: {cv_scores.mean():.1%} +/- {cv_scores.std():.1%}")

# Full tree text
print(export_text(clf, feature_names=feature_cols, class_names=class_names, show_weights=True))
```

### Producing D-04 Format Rules
```python
# Source: sklearn tree_ internals (scikit-learn docs)
# After training clf:
rules = extract_rules(clf, feature_names=feature_cols, class_names=class_names)
for rule in rules:
    print(rule)
# Output: "Buy when ema9_above_ema21 > 0.5000 AND macd_histogram_positive > 0.5000: 78% confidence (N=45)"
```

Note: For boolean features encoded as True/False, sklearn will split at threshold 0.5. The rule extraction should detect this and simplify "ema9_above_ema21 > 0.5000" to "ema9_above_ema21" and "<= 0.5000" to "NOT ema9_above_ema21" for readability.

### Report Output Structure
```markdown
# Rule Discovery Report
Generated: {date}

## Dataset Summary
- Total signals: 962
- Pre-2019 (before 2019-02-09): 867 signals
- Post-2019 (from 2019-02-09): 95 signals

## Statistical Profile: Pre-2019

### Boolean Feature Frequencies by Signal Type
| Feature | Buy (N=296) | Cash (N=296) | Sell (N=275) |
|---------|-------------|--------------|--------------|
| ema9_above_ema21 | 72% | 51% | 28% |
...

## Decision Tree: Pre-2019
Accuracy: {train}% (CV: {cv}%)
{export_text output}

### Extracted Rules (Pre-2019)
1. Buy when ema9_above_ema21 AND macd_histogram_positive: 78% confidence (N=45)
...

## Decision Tree: Post-2019
...

## Era Comparison
| Rule Pattern | Pre-2019 | Post-2019 | Change |
...
```

## Data Profile (Verified)

Actual data from running the feature snapshot pipeline:

| Property | Value |
|----------|-------|
| Total signals | 962 |
| Columns | 27 (8 boolean, continuous indicators, OHLCV, signal, date, gain_loss_pct) |
| NaN count (indicators) | 0 across all 7 numeric indicator columns |
| Class distribution | Buy=333, Cash=339, Sell=290 |
| Pre-2019 signals | 867 (Buy=296, Cash=296, Sell=275) -- well balanced |
| Post-2019 signals | 95 (Buy=37, Cash=43, Sell=15) -- imbalanced |
| Boolean features | ema9_above_ema21, ema21_above_ema55, close_above_ma200, close_above_ema9, close_above_ema21, close_above_ema55, macd_histogram_positive, macd_above_signal |
| Continuous indicators | ema9, ema21, ema55, ma200, macd, macd_signal, macd_histogram |
| HA Smoothed cols | ha_smooth_open, ha_smooth_high, ha_smooth_low, ha_smooth_close |
| OHLCV cols (exclude from features) | open, high, low, close, volume |

**Key implication for planning:** Pre-2019 tree will have plenty of data for reliable rules. Post-2019 tree (95 samples, Sell=15) will produce tentative rules at best -- confidence scores and CV accuracy must be prominently reported.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sklearn export_graphviz (requires graphviz install) | export_text (no external deps) | sklearn 0.21 (2019) | Text output works everywhere |
| Manual feature importance | tree.feature_importances_ + permutation_importance | sklearn 0.22+ | Built-in importance ranking |
| class_weight='auto' | class_weight='balanced' | sklearn 0.17 | Clearer API for imbalanced classes |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ (via uv dev-dependencies) |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_rule_discovery.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISC-01 | Statistical profile produces frequency tables for all 8 boolean features per signal type | unit | `uv run pytest tests/test_rule_discovery.py::test_boolean_frequency_profile -x` | No -- Wave 0 |
| DISC-01 | Statistical profile produces continuous feature stats per signal type | unit | `uv run pytest tests/test_rule_discovery.py::test_continuous_stats_profile -x` | No -- Wave 0 |
| DISC-02 | Decision tree trained on feature snapshot achieves above-chance accuracy | unit | `uv run pytest tests/test_rule_discovery.py::test_decision_tree_above_chance -x` | No -- Wave 0 |
| DISC-03 | Extracted rules match expected format with confidence scores | unit | `uv run pytest tests/test_rule_discovery.py::test_rule_extraction_format -x` | No -- Wave 0 |
| DISC-04 | Era split produces separate results for pre/post-2019 | unit | `uv run pytest tests/test_rule_discovery.py::test_era_split_produces_separate_results -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_rule_discovery.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_rule_discovery.py` -- covers DISC-01 through DISC-04
- [ ] scikit-learn dependency added to pyproject.toml -- required for imports in test

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | Yes | 3.10+ | -- |
| pandas | Statistical profiling | Yes | >=2.0.0 | -- |
| numpy | Feature arrays | Yes | >=1.24.0 | -- |
| scikit-learn | Decision tree (DISC-02, DISC-03) | No (not in pyproject.toml) | 1.8.0 (via uv) | -- |
| matplotlib | Optional visualization | Yes | >=3.7.0 | Text-only output |
| pytest | Testing | Yes | >=9.0.2 (dev) | -- |

**Missing dependencies with no fallback:**
- scikit-learn 1.8.0 -- must be added to pyproject.toml dependencies before implementation

**Missing dependencies with fallback:**
- None

## Open Questions

1. **Boolean-only vs boolean+continuous features for decision tree**
   - What we know: 8 boolean features capture crossover states; continuous features (MACD value, EMA gaps) capture magnitude
   - What's unclear: Whether continuous features improve classification enough to justify more complex tree splits
   - Recommendation: Statistical profiling (DISC-01) answers this -- implement profiling first, then decide feature set based on observed separation. Start with boolean-only tree, try boolean+continuous, compare CV accuracy.

2. **HA Smoothed feature utility**
   - What we know: 4 HA Smoothed columns exist but are highly correlated with EMA features
   - What's unclear: Whether candle color (close > open) adds unique signal
   - Recommendation: Derive a single `ha_smooth_bullish` boolean (ha_smooth_close > ha_smooth_open) and test if it improves tree accuracy. Drop raw HA columns from feature set.

3. **Post-2019 tree reliability with Sell=15**
   - What we know: 15 samples of one class is very low for tree learning
   - What's unclear: Whether the tree can learn meaningful Sell rules for post-2019
   - Recommendation: Report the limitation prominently. Use class_weight='balanced' and min_samples_leaf=3-5. If CV accuracy for Sell is near zero, note that Sell rules for post-2019 are unreliable.

## Sources

### Primary (HIGH confidence)
- [scikit-learn 1.8.0 DecisionTreeClassifier docs](https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeClassifier.html) - verified API: max_depth, class_weight, min_samples_leaf parameters
- [scikit-learn 1.8.0 export_text docs](https://scikit-learn.org/stable/modules/generated/sklearn.tree.export_text.html) - verified: feature_names, class_names, show_weights parameters
- [scikit-learn 1.8.0 Decision Trees guide](https://scikit-learn.org/stable/modules/tree.html) - tree internals, feature importance, rule extraction patterns
- Project code: `core/feature_snapshot.py`, `core/indicators.py` -- verified by running pipeline, confirmed 962 rows, 27 columns, zero NaNs

### Secondary (MEDIUM confidence)
- scikit-learn version 1.8.0 confirmed via `uv pip install --dry-run` (pulls scipy 1.17.1, joblib 1.5.3, threadpoolctl 3.6.0)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - scikit-learn is the undisputed standard for interpretable ML in Python; API verified against 1.8.0 docs
- Architecture: HIGH - follows established analysis/ script pattern in project; feature snapshot verified with actual data run
- Pitfalls: HIGH - data profile verified empirically (962 samples, class distributions, NaN counts); post-2019 imbalance confirmed
- Data profile: HIGH - verified by running actual pipeline and inspecting output

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable domain, scikit-learn tree API unchanged for years)
