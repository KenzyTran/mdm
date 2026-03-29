# Phase 10: Discovery Validation - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate discovered rules against the full 962-signal history with match rate scoring, train/test era-based validation, and visual comparison dashboards. Does NOT modify discovered rules, add new indicators, or extend to VN30 (future work).

</domain>

<decisions>
## Implementation Decisions

### Match rate scoring
- **D-01:** Per-signal-date prediction — for each of the 962 signal dates, predict Buy/Sell/Cash from indicator features using the trained decision tree. Compare predicted vs actual published signal.
- **D-02:** Report all predictions, but also show a filtered view for high-confidence rules (e.g., predict_proba >= 70%). Gives both full-picture and high-confidence subset metrics.
- **D-03:** Full confusion matrix (predicted vs actual) plus precision/recall per signal type (Buy/Sell/Cash). Shows not just overall accuracy but where errors concentrate.

### Train/test split design
- **D-04:** Era-based cross-validation: train on pre-2019 -> test on post-2019, AND train on post-2019 -> test on pre-2019. Tests whether rules generalize across the confirmed structural change.
- **D-05:** Frame cross-era results by quantifying degradation: report cross-era match rate alongside same-era rate. The delta measures structural change magnitude (e.g., "Pre-2019 rules on post-2019 data: 45% vs 72% same-era — confirms structural shift").

### Comparison dashboard
- **D-06:** NASDAQ price chart with published signals on top row and discovered-rule signals on bottom row. Color-coded: green=Buy, red=Sell, gray=Cash. Divergence points highlighted.
- **D-07:** Two era panels (pre-2019 and post-2019) stacked or side-by-side. Each era shows its own tree's predictions. Full 52-year single chart would be too dense for readable signal markers.

### Rule application method
- **D-08:** Use sklearn `tree.predict()` and `tree.predict_proba()` directly on feature snapshots. No re-implementation of rules as Python code. Avoids translation errors.
- **D-09:** Retrain trees in the validation pipeline (self-contained). No saved model files — validation script loads data, trains trees with same parameters as Phase 9, then scores. Matches Phase 9's functional approach.

### Claude's Discretion
- Exact matplotlib styling (colors, markers, figure dimensions, DPI)
- Script organization within `analysis/` (single file vs multiple)
- Confidence threshold value (70% suggested but adjustable)
- How to handle warm-up period signals (pre-200 trading days where MA200 is NaN)
- Report text formatting and section ordering
- Jupyter notebook cell structure and organization
- Whether to include a summary statistics panel on the dashboard chart

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rule discovery (Phase 9 outputs — direct input)
- `analysis/rule_discovery.py` — `train_era_tree()`, `extract_rules()`, `generate_full_report()`. Contains tree training logic, era splitting, and the feature/class constants (BOOLEAN_FEATURES, CLASS_NAMES, ERA_SPLIT_DATE) to reuse.

### Feature data pipeline
- `core/feature_snapshot.py` — `extract_feature_snapshot()` produces the 962-row DataFrame with all indicator values and 8 boolean features. Direct input to validation scoring.
- `core/indicators.py` — `build_indicator_dataframe()` computes all indicators on NASDAQ OHLCV.
- `core/data_loader.py` — `DataLoader('nasdaq').load()` for NASDAQ OHLCV with /1000 normalization.
- `core/signal_loader.py` — `load_signal_fixture()` for 962 published signals.

### Signal data
- `data/signals/nasdaq_signals_full.csv` — Full 962-signal ground truth (1974-2026)

### Validation pattern reference (Phase 5)
- `analysis/validate_v2.py` — Full validation pipeline with match rates, three-way comparison, dashboard charts. Reference for script structure, output patterns, and matplotlib multi-panel layout.

### Requirements
- `.planning/REQUIREMENTS.md` — VAL-01 (match rate scoring), VAL-02 (train/test validation), VAL-03 (comparison dashboard)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analysis/rule_discovery.py` `train_era_tree()`: Trains decision tree with class_weight='balanced', returns (clf, cv_accuracy, feature_names). Reuse directly for validation pipeline.
- `analysis/rule_discovery.py` `split_by_era()`: Splits DataFrame at ERA_SPLIT_DATE. Reuse for train/test era splitting.
- `analysis/rule_discovery.py` constants: BOOLEAN_FEATURES, CONTINUOUS_FEATURES, CLASS_NAMES, ERA_SPLIT_DATE — import rather than redefine.
- `core/feature_snapshot.py` `extract_feature_snapshot()`: Produces ready-to-use 962-row DataFrame.
- `analysis/validate_v2.py`: Reference for matplotlib dashboard layout, CSV/text/PNG output pattern.
- `analysis/validate_v2.py` `generate_dashboard()`: Multi-panel chart generation pattern with NASDAQ price overlay.

### Established Patterns
- Analysis scripts in `analysis/` follow: load data -> compute -> print report -> save to `output/`
- Module-level pure functions (no classes) for computation (Phase 8 convention)
- scikit-learn already in dependencies (added Phase 9)
- Output files go to `output/` directory (gitignored)

### Integration Points
- Imports `train_era_tree`, `split_by_era`, feature constants from `analysis/rule_discovery.py`
- Imports data pipeline from `core/` (DataLoader, indicators, feature_snapshot, signal_loader)
- Outputs: match rate CSV, confusion matrix text, dashboard PNG, markdown report to `output/`
- Optional: Jupyter notebook for interactive exploration (following Phase 5 pattern)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-discovery-validation*
*Context gathered: 2026-03-29*
