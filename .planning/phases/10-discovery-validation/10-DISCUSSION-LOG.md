# Phase 10: Discovery Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 10-discovery-validation
**Areas discussed:** Match rate scoring, Train/test split design, Comparison dashboard, Rule application method

---

## Match Rate Scoring

| Option | Description | Selected |
|--------|-------------|----------|
| Per-signal-date prediction | For each of 962 signal dates, predict from features using trained tree. Compare predicted vs actual. | ✓ |
| Continuous signal generation | Apply rules to every trading day to generate timeline, compare transitions against published dates. | |
| Both approaches | Per-signal-date first (primary), then continuous generation as secondary analysis. | |

**User's choice:** Per-signal-date prediction
**Notes:** Simple, direct, matches how rules were discovered.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Report all, highlight confident | Score all predictions, also show filtered view for rules above confidence threshold. | ✓ |
| Score all predictions equally | Every prediction counts the same regardless of confidence. | |
| Only score confident rules | Exclude low-confidence predictions from match rate. | |

**User's choice:** Report all, highlight confident
**Notes:** Gives both full picture and high-confidence subset metric.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Confusion matrix + per-type rates | Full confusion matrix plus precision/recall per signal type. | ✓ |
| Per-type match rate only | Buy accuracy, Sell accuracy, Cash accuracy as separate percentages. | |

**User's choice:** Confusion matrix + per-type rates
**Notes:** Shows where errors happen, not just overall accuracy.

---

## Train/Test Split Design

| Option | Description | Selected |
|--------|-------------|----------|
| Era-based cross-validation | Train pre-2019 -> test post-2019, AND vice versa. Tests cross-era generalization. | ✓ |
| Within-era holdout | Split each era 80/20. Tests within-era generalization only. | |
| Both cross-era + within-era | Run both strategies. Most thorough but complex output. | |

**User's choice:** Era-based cross-validation
**Notes:** Aligns with VAL-02's configurable split point and tests structural change hypothesis.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Expect degradation, quantify it | Report cross-era rate alongside same-era rate. Frame delta as structural change measure. | ✓ |
| Pass/fail threshold | Set minimum acceptable cross-era match rate (e.g., above chance ~33%). | |

**User's choice:** Expect degradation, quantify it
**Notes:** Quantifies structural change magnitude rather than binary pass/fail.

---

## Comparison Dashboard

| Option | Description | Selected |
|--------|-------------|----------|
| Price + dual signal markers | NASDAQ price with published signals top row, discovered-rule signals bottom row. Color-coded. | ✓ |
| Side-by-side signal timelines | Two horizontal timelines with color-coded Buy/Sell/Cash periods. | |
| Combined price + confusion summary | Price chart with signal markers plus confusion matrix heatmap panel. | |

**User's choice:** Price + dual signal markers
**Notes:** Similar to Phase 3's visual overlay pattern.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Era panels | Two panels: pre-2019 and post-2019. Each shows its own tree's predictions. | ✓ |
| Post-2019 only | Focus on structural change period only. | |
| Full history, single chart | All 52 years on one chart. Signal markers may be too dense. | |

**User's choice:** Era panels
**Notes:** Full history too dense for readable signal markers.

---

## Rule Application Method

| Option | Description | Selected |
|--------|-------------|----------|
| Use sklearn tree.predict() | Call predict() and predict_proba() directly. No translation errors. | ✓ |
| Re-implement rules as Python | Code extracted rules as if/else. Useful for outside-sklearn use. | |
| Both: tree primary, rules cross-check | Compare tree predictions vs re-implemented rules for extraction accuracy. | |

**User's choice:** Use sklearn tree.predict()
**Notes:** No risk of translation errors, provides confidence scores via predict_proba().

---

| Option | Description | Selected |
|--------|-------------|----------|
| Retrain in validation pipeline | Self-contained: loads data, trains trees, scores. No saved model dependency. | ✓ |
| Save/load trained models | Phase 9 saves to pickle/joblib, validation loads. Adds serialization coupling. | |

**User's choice:** Retrain in validation pipeline
**Notes:** Matches Phase 9's functional approach, no model file management needed.

---

## Claude's Discretion

- Matplotlib styling, script organization, confidence threshold value, warm-up handling, report formatting, notebook structure

## Deferred Ideas

None — discussion stayed within phase scope
