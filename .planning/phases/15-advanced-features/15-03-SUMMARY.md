---
phase: 15-advanced-features
plan: 03
subsystem: analysis
tags: [model-comparison, dashboard, decision-tree, state-machine, hybrid]
dependency_graph:
  requires: [mdm_hybrid_engine.py, mdm_v2_engine.py, rule_discovery.py]
  provides: [compare_models.py, model_comparison.png]
  affects: [analysis/compare_models.py]
tech_stack:
  - matplotlib
  - sklearn
  - pandas
---

## Summary

**Three-way model comparison dashboard comparing pure state machine (v2), pure decision tree, and hybrid MDM accuracy side-by-side against 962 published NASDAQ signals.**

## Tasks Completed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | Create three-way model comparison script | Done | `0782c8a` |
| 2 | Verify dashboard visual correctness | Done | Human approved |

## Key Files

### Created
- `analysis/compare_models.py` — standalone comparison script with 4-subplot dashboard

### Generated Output
- `output/model_comparison.png` — per-type recall bars, overall accuracy bars, 3 confusion matrices

## Self-Check: PASSED

- [x] Script runs end-to-end without errors
- [x] Produces `output/model_comparison.png` with 4-subplot dashboard
- [x] Prints accuracy comparison table to stdout
- [x] Shows all three models side-by-side
- [x] Human visual verification approved

## Key Decisions

- Used sklearn classification_report for per-type precision/recall/F1
- DecisionTreeClassifier with random_state=42, max_depth=5, min_samples_leaf=10 for reproducibility
- Dashboard layout: 2 bar charts top row, 3 confusion matrices bottom row

## Results

| Model | Overall Accuracy | Signals |
|-------|-----------------|---------|
| Pure State Machine (v2) | 37.9% | 952 |
| Pure Decision Tree | 55.5% | 962 |
| Hybrid | 33.6% | 952 |

## Deviations

None — implemented as planned.
