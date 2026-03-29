"""
Rule Discovery: Era-Aware Statistical Profiling of MDM Signals

Analyzes the relationship between indicator conditions (boolean features
and continuous values) and published signal types (Buy/Sell/Cash) across
pre-2019 and post-2019 eras. This statistical profiling reveals which
indicator features most strongly separate signal types, guiding the
decision tree rule extraction in Plan 02.

Usage:
    uv run python analysis/rule_discovery.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text, _tree
from sklearn.model_selection import cross_val_score


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ERA_SPLIT_DATE = '2019-02-09'

SIGNAL_CSV = 'data/signals/nasdaq_signals_full.csv'

BOOLEAN_FEATURES = [
    'ema9_above_ema21',
    'ema21_above_ema55',
    'close_above_ma200',
    'close_above_ema9',
    'close_above_ema21',
    'close_above_ema55',
    'macd_histogram_positive',
    'macd_above_signal',
]

CONTINUOUS_FEATURES = [
    'macd',
    'macd_signal',
    'macd_histogram',
    'ema9',
    'ema21',
    'ema55',
    'ma200',
]

CLASS_NAMES = ['Buy', 'Cash', 'Sell']


# ---------------------------------------------------------------------------
# Core profiling functions
# ---------------------------------------------------------------------------

def split_by_era(
    snapshot: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split snapshot into pre-2019 and post-2019 eras.

    The era boundary is Feb 9, 2019 -- the date Dr. K's MDM underwent
    a structural change from the classic model to the post-2019 model.

    Args:
        snapshot: DataFrame with a 'date' column.

    Returns:
        Tuple of (pre_2019, post_2019) DataFrames as copies.
    """
    cutoff = pd.Timestamp(ERA_SPLIT_DATE)
    mask = snapshot['date'] < cutoff
    return snapshot[mask].copy(), snapshot[~mask].copy()


def profile_boolean_features(
    snapshot: pd.DataFrame,
    bool_cols: list,
) -> pd.DataFrame:
    """Compute boolean feature frequency tables per signal type.

    For each boolean feature, calculates the proportion of True values
    within each signal type (Buy/Cash/Sell). This reveals which indicator
    conditions are most associated with each signal.

    Args:
        snapshot: Feature snapshot DataFrame with signal and boolean columns.
        bool_cols: List of boolean column names to profile.

    Returns:
        DataFrame with boolean features as rows (index) and signal types
        as columns, values are proportions (0.0 to 1.0).
    """
    return snapshot.groupby('signal')[bool_cols].mean().T


def profile_continuous_features(
    snapshot: pd.DataFrame,
    cont_cols: list,
) -> pd.DataFrame:
    """Compute descriptive statistics for continuous features per signal type.

    For each continuous feature, calculates count, mean, std, min, 25%, 50%,
    75%, max within each signal type.

    Args:
        snapshot: Feature snapshot DataFrame with signal and continuous columns.
        cont_cols: List of continuous column names to profile.

    Returns:
        Multi-index DataFrame with signal type as first level index,
        containing descriptive statistics from pandas describe().
    """
    return snapshot.groupby('signal')[cont_cols].describe()


def generate_statistical_report(
    snapshot: pd.DataFrame,
    era_name: str,
) -> str:
    """Generate a markdown-formatted statistical report for a snapshot era.

    Args:
        snapshot: Feature snapshot DataFrame for a single era.
        era_name: Human-readable era label (e.g., 'Pre-2019', 'Post-2019').

    Returns:
        Markdown string containing dataset summary, boolean frequency table,
        and continuous feature statistics.
    """
    lines = []
    lines.append(f"## {era_name} Statistical Profile")
    lines.append("")

    # Dataset summary
    total = len(snapshot)
    class_counts = snapshot['signal'].value_counts()
    lines.append(f"**Total signals:** {total}")
    lines.append("")
    lines.append("**Class distribution:**")
    for cls in CLASS_NAMES:
        count = class_counts.get(cls, 0)
        pct = count / total * 100 if total > 0 else 0
        lines.append(f"- {cls}: {count} ({pct:.1f}%)")
    lines.append("")

    # Boolean frequency table
    bool_profile = profile_boolean_features(snapshot, BOOLEAN_FEATURES)
    lines.append("### Boolean Feature Frequencies (% True)")
    lines.append("")
    header = "| Feature | " + " | ".join(CLASS_NAMES) + " |"
    separator = "| --- | " + " | ".join(["---"] * len(CLASS_NAMES)) + " |"
    lines.append(header)
    lines.append(separator)
    for feat in bool_profile.index:
        vals = " | ".join(f"{bool_profile.loc[feat, cls]:.1%}" for cls in CLASS_NAMES)
        lines.append(f"| {feat} | {vals} |")
    lines.append("")

    # Continuous feature summary (mean +/- std per signal type)
    cont_profile = profile_continuous_features(snapshot, CONTINUOUS_FEATURES)
    lines.append("### Continuous Feature Summary (mean +/- std)")
    lines.append("")
    header = "| Feature | " + " | ".join(CLASS_NAMES) + " |"
    lines.append(header)
    lines.append(separator)
    for feat in CONTINUOUS_FEATURES:
        parts = []
        for cls in CLASS_NAMES:
            if cls in cont_profile.index:
                mean_val = cont_profile.loc[cls, (feat, 'mean')]
                std_val = cont_profile.loc[cls, (feat, 'std')]
            else:
                mean_val, std_val = 0, 0
            parts.append(f"{mean_val:.2f} +/- {std_val:.2f}")
        lines.append(f"| {feat} | " + " | ".join(parts) + " |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Decision tree training and rule extraction (Plan 02)
# ---------------------------------------------------------------------------

def train_era_tree(snapshot, feature_cols, max_depth=4):
    """Train a decision tree classifier on features to predict signal type.

    Uses class_weight='balanced' to handle imbalanced classes (e.g., Sell=15
    in post-2019 era). Cross-validation folds are capped at the minimum
    class count to avoid folds with missing classes.

    Args:
        snapshot: Feature snapshot DataFrame with 'signal' column and feature columns.
        feature_cols: List of column names to use as features.
        max_depth: Maximum tree depth (capped at 4-5 for human readability).

    Returns:
        Tuple of (clf, cv_accuracy, feature_names) where clf is the fitted
        DecisionTreeClassifier, cv_accuracy is mean cross-validated accuracy,
        and feature_names is the list of feature column names used.
    """
    X = snapshot[feature_cols].values
    y = snapshot['signal'].values
    feature_names = list(feature_cols)

    clf = DecisionTreeClassifier(
        max_depth=max_depth,
        class_weight='balanced',
        random_state=42,
        min_samples_leaf=5,
    )
    clf.fit(X, y)

    # Cross-validated accuracy with fold count capped at minimum class size
    min_class_count = int(pd.Series(y).value_counts().min())
    if min_class_count < 2:
        # Too few samples for cross-validation; use training accuracy
        cv_accuracy = clf.score(X, y)
    else:
        cv = min(5, min_class_count)
        cv_scores = cross_val_score(clf, X, y, cv=cv, scoring='accuracy')
        cv_accuracy = cv_scores.mean()

    return (clf, cv_accuracy, feature_names)


def extract_rules(tree, feature_names, class_names):
    """Extract human-readable rules from a trained decision tree.

    Walks the tree structure recursively to produce rules of the form:
    "Buy when ema9_above_ema21 AND NOT macd_above_signal: 78% confidence (N=45)"

    Boolean features (threshold ~0.5) are simplified to "feature" / "NOT feature"
    instead of the raw "feature > 0.5000" representation.

    Args:
        tree: Fitted DecisionTreeClassifier.
        feature_names: List of feature names matching training columns.
        class_names: List of class labels (e.g., ['Buy', 'Cash', 'Sell']).

    Returns:
        List of rule strings, one per leaf node.
    """
    tree_ = tree.tree_
    rules = []

    def _walk(node, conditions):
        # Leaf node
        if tree_.feature[node] == _tree.TREE_UNDEFINED:
            weighted_counts = tree_.value[node][0]
            weighted_total = weighted_counts.sum()
            predicted_idx = int(np.argmax(weighted_counts))
            confidence = weighted_counts[predicted_idx] / weighted_total if weighted_total > 0 else 0
            class_name = class_names[predicted_idx]
            # Use actual sample count (not weighted) for N
            n_samples = int(tree_.n_node_samples[node])
            cond_str = " AND ".join(conditions) if conditions else "always"
            rules.append(
                f"{class_name} when {cond_str}: {confidence:.0%} confidence (N={n_samples})"
            )
            return

        feat_name = feature_names[tree_.feature[node]]
        threshold = tree_.threshold[node]

        # Boolean simplification: threshold near 0.5 means boolean split
        is_boolean = 0.4 <= threshold <= 0.6

        if is_boolean:
            left_cond = f"NOT {feat_name}"
            right_cond = feat_name
        else:
            left_cond = f"{feat_name} <= {threshold:.4f}"
            right_cond = f"{feat_name} > {threshold:.4f}"

        _walk(tree_.children_left[node], conditions + [left_cond])
        _walk(tree_.children_right[node], conditions + [right_cond])

    _walk(0, [])
    return rules


# ---------------------------------------------------------------------------
# Full report generation (Plan 02)
# ---------------------------------------------------------------------------

def generate_full_report(snapshot: pd.DataFrame) -> str:
    """Generate a complete rule discovery report with statistical profiles,
    decision trees, extracted rules, and era comparison.

    Args:
        snapshot: Full feature snapshot DataFrame with 'date', 'signal',
                  and all boolean/continuous feature columns.

    Returns:
        Markdown-formatted report string.
    """
    from datetime import date as _date

    pre, post = split_by_era(snapshot)
    feature_cols = BOOLEAN_FEATURES

    lines = []
    lines.append("# Rule Discovery Report")
    lines.append(f"Generated: {_date.today().isoformat()}")
    lines.append("")

    # --- Dataset Summary ---
    lines.append("## Dataset Summary")
    lines.append(f"- Total signals: {len(snapshot)}")
    pre_counts = pre['signal'].value_counts()
    post_counts = post['signal'].value_counts()
    pre_summary = ", ".join(f"{c}={pre_counts.get(c, 0)}" for c in CLASS_NAMES)
    post_summary = ", ".join(f"{c}={post_counts.get(c, 0)}" for c in CLASS_NAMES)
    lines.append(f"- Pre-2019 (before {ERA_SPLIT_DATE}): {len(pre)} signals ({pre_summary})")
    lines.append(f"- Post-2019 (from {ERA_SPLIT_DATE}): {len(post)} signals ({post_summary})")
    lines.append("")

    # --- Statistical Profiles ---
    lines.append(generate_statistical_report(pre, "Pre-2019"))
    lines.append("")
    lines.append(generate_statistical_report(post, "Post-2019"))
    lines.append("")

    # --- Decision Tree: Pre-2019 ---
    pre_clf, pre_cv, pre_feat = train_era_tree(pre, feature_cols, max_depth=4)
    pre_train_acc = pre_clf.score(pre[feature_cols].values, pre['signal'].values)
    pre_tree_text = export_text(pre_clf, feature_names=pre_feat, class_names=CLASS_NAMES, show_weights=True)
    pre_rules = extract_rules(pre_clf, pre_feat, CLASS_NAMES)

    lines.append("## Decision Tree: Pre-2019")
    lines.append(f"Feature set: {', '.join(feature_cols)}")
    lines.append(f"Train accuracy: {pre_train_acc:.1%}")
    lines.append(f"Cross-validated accuracy: {pre_cv:.1%}")
    lines.append("")
    lines.append("```")
    lines.append(pre_tree_text.rstrip())
    lines.append("```")
    lines.append("")
    lines.append("### Extracted Rules (Pre-2019)")
    lines.append("")
    for i, rule in enumerate(pre_rules, 1):
        lines.append(f"{i}. {rule}")
    lines.append("")

    # --- Decision Tree: Post-2019 ---
    post_clf, post_cv, post_feat = train_era_tree(post, feature_cols, max_depth=4)
    post_train_acc = post_clf.score(post[feature_cols].values, post['signal'].values)
    post_tree_text = export_text(post_clf, feature_names=post_feat, class_names=CLASS_NAMES, show_weights=True)
    post_rules = extract_rules(post_clf, post_feat, CLASS_NAMES)

    sell_count = post_counts.get('Sell', 0)
    lines.append("## Decision Tree: Post-2019")
    lines.append(f"Feature set: {', '.join(feature_cols)}")
    lines.append(f"Train accuracy: {post_train_acc:.1%}")
    lines.append(f"Cross-validated accuracy: {post_cv:.1%}")
    lines.append(f"**NOTE:** Post-2019 has only {len(post)} samples (Sell={sell_count}). Rules are tentative.")
    lines.append("")
    lines.append("```")
    lines.append(post_tree_text.rstrip())
    lines.append("```")
    lines.append("")
    lines.append("### Extracted Rules (Post-2019)")
    lines.append("")
    for i, rule in enumerate(post_rules, 1):
        lines.append(f"{i}. {rule}")
    lines.append("")

    # --- Era Comparison (DISC-04) ---
    lines.append("## Era Comparison (DISC-04)")
    lines.append("")

    # Feature importance table
    lines.append("### Feature Importance Changes")
    lines.append("")
    lines.append("| Feature | Pre-2019 Importance | Post-2019 Importance | Change |")
    lines.append("| --- | --- | --- | --- |")
    pre_imp = dict(zip(pre_feat, pre_clf.feature_importances_))
    post_imp = dict(zip(post_feat, post_clf.feature_importances_))
    for feat in feature_cols:
        p = pre_imp.get(feat, 0)
        q = post_imp.get(feat, 0)
        change = q - p
        sign = "+" if change >= 0 else ""
        lines.append(f"| {feat} | {p:.3f} | {q:.3f} | {sign}{change:.3f} |")
    lines.append("")

    # Rule pattern differences narrative
    lines.append("### Rule Pattern Differences")
    lines.append("")

    # Determine top features per era
    pre_sorted = sorted(pre_imp.items(), key=lambda x: x[1], reverse=True)
    post_sorted = sorted(post_imp.items(), key=lambda x: x[1], reverse=True)
    pre_top = [f for f, v in pre_sorted if v > 0.05][:3]
    post_top = [f for f, v in post_sorted if v > 0.05][:3]

    lines.append(f"**Pre-2019 top features:** {', '.join(pre_top) if pre_top else 'none above 5%'}")
    lines.append(f"**Post-2019 top features:** {', '.join(post_top) if post_top else 'none above 5%'}")
    lines.append("")

    overlap = set(pre_top) & set(post_top)
    if overlap:
        lines.append(f"Shared dominant features: {', '.join(overlap)}")
    else:
        lines.append("No overlap in top features between eras -- suggests structural rule change.")
    lines.append("")

    # Confidence comparison
    def avg_confidence(rules_list):
        confs = []
        for r in rules_list:
            try:
                pct = r.split(": ")[1].split(" confidence")[0]
                confs.append(int(pct.replace("%", "")) / 100)
            except (IndexError, ValueError):
                pass
        return np.mean(confs) if confs else 0

    pre_avg = avg_confidence(pre_rules)
    post_avg = avg_confidence(post_rules)
    lines.append(f"Average rule confidence: Pre-2019={pre_avg:.0%}, Post-2019={post_avg:.0%}")
    lines.append("")
    lines.append(f"**Warning:** Post-2019 era has only {len(post)} samples with "
                 f"Sell={sell_count}. Rules from this era should be treated as tentative "
                 f"hypotheses requiring out-of-sample validation, not definitive trading rules.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main script
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from core.data_loader import DataLoader
    from core.indicators import build_indicator_dataframe
    from core.signal_loader import load_signal_fixture
    from core.feature_snapshot import extract_feature_snapshot

    print("=" * 70)
    print("MDM Rule Discovery: Full Report Generation")
    print("=" * 70)
    print()

    # Step 1: Load NASDAQ OHLCV data
    print("Loading NASDAQ OHLCV data...")
    ohlcv = DataLoader('nasdaq').load()
    print(f"  Loaded {len(ohlcv)} trading days ({ohlcv['date'].min().date()} to {ohlcv['date'].max().date()})")

    # Step 2: Build indicators
    print("Building indicator dataframe...")
    indicators = build_indicator_dataframe(ohlcv)
    print(f"  Indicators computed: {len(indicators)} rows")

    # Step 3: Load signals
    print(f"Loading signals from {SIGNAL_CSV}...")
    signals = load_signal_fixture(SIGNAL_CSV)
    print(f"  Loaded {len(signals)} published signals")

    # Step 4: Extract feature snapshot
    print("Extracting feature snapshot...")
    snapshot = extract_feature_snapshot(indicators, signals)
    print(f"  Snapshot: {len(snapshot)} signal-date rows")

    # Step 5: Generate full report
    print("Generating full rule discovery report...")
    report = generate_full_report(snapshot)

    # Print to console
    print()
    print(report)

    # Save to file
    os.makedirs('output', exist_ok=True)
    output_path = 'output/rule_discovery_report.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print()
    print(f"Report saved to {output_path}")
