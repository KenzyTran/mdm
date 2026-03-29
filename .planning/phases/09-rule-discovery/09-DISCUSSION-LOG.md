# Phase 9: Rule Discovery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 09-rule-discovery
**Areas discussed:** Signal framing, Era splitting, Decision tree scope, Output format

---

## Signal Framing

| Option | Description | Selected |
|--------|-------------|----------|
| Signal type (Recommended) | Classify each signal date as Buy, Sell, or Cash. 962 samples, 3 classes. | ✓ |
| Signal transitions | Classify transitions (Buy→Cash, etc.). Captures sequence context but reduces samples per class. | |
| Both approaches | Signal type first, transition analysis as secondary view. | |

**User's choice:** Signal type (Recommended)
**Notes:** Directly matches DISC-02 requirement. Simpler framing with full 962 sample count.

---

## Statistical Profiling Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Both continuous and boolean (Recommended) | Show distributions of raw indicator values AND frequency tables of boolean features per signal type. | |
| Boolean features only | Focus on the 8 boolean crossover/position features only. | |
| You decide | Claude picks based on feature discriminability. | ✓ |

**User's choice:** You decide
**Notes:** Claude's discretion on profiling depth.

---

## Era Splitting

| Option | Description | Selected |
|--------|-------------|----------|
| Binary split at Feb 2019 (Recommended) | Train separate trees for pre-2019 and post-2019. Clean split at known change date. | ✓ |
| Post-2019 focus with pre-2019 comparison | Primary tree on post-2019 only, pre-2019 as secondary comparison. | |
| Full history + era as feature | Single tree with era boolean feature. Risk: may blur structural change. | |

**User's choice:** Binary split at Feb 2019 (Recommended)
**Notes:** Directly tests the structural change hypothesis confirmed in v1.0 analysis.

---

## Decision Tree Features

| Option | Description | Selected |
|--------|-------------|----------|
| Boolean features only (Recommended) | 8 boolean features. Produces directly human-readable rules. | |
| Boolean + continuous | Add continuous features. More expressive but harder to interpret. | |
| You decide | Claude picks based on statistical profiling results. | ✓ |

**User's choice:** You decide
**Notes:** Claude's discretion based on what profiling reveals.

---

## Tree Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Cap at depth 4-5 (Recommended) | Human-readable rules, avoids overfitting on 962 samples. | ✓ |
| No limit, prune after | Full growth then prune via cross-validation. | |
| You decide | Claude picks based on cross-validation. | |

**User's choice:** Cap at depth 4-5 (Recommended)
**Notes:** Standard for interpretable decision trees.

---

## Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| Text rules + console report (Recommended) | Human-readable rule strings saved to markdown file. | ✓ |
| Jupyter notebook | Interactive notebook with visualizations. | |
| Both script and notebook | Script for rules + notebook for visualization. | |

**User's choice:** Text rules + console report (Recommended)
**Notes:** Matches DISC-03 requirement format.

---

## Code Location

| Option | Description | Selected |
|--------|-------------|----------|
| analysis/rule_discovery.py (Recommended) | Standalone analysis script, consistent with analysis/ directory. | ✓ |
| core/rule_discovery.py | Core infrastructure, importable by Phase 10. | |
| You decide | Claude picks based on Phase 10 consumption pattern. | |

**User's choice:** analysis/rule_discovery.py (Recommended)
**Notes:** Follows established analysis script pattern.

---

## Claude's Discretion

- Statistical profiling depth (continuous vs boolean-only)
- Feature selection for decision tree (boolean-only vs mixed)
- Class imbalance handling
- scikit-learn hyperparameters beyond max_depth
- Report file format details
