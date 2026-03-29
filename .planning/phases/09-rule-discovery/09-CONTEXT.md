# Phase 9: Rule Discovery - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Discover indicator-based rules that drive Buy/Sell/Cash signal transitions through statistical analysis and decision tree extraction on the 962-signal feature snapshot. This phase produces statistical profiles and human-readable rules — it does NOT validate match rates or build comparison dashboards (Phase 10).

</domain>

<decisions>
## Implementation Decisions

### Signal framing
- **D-01:** Classify each signal date as Buy, Sell, or Cash based on indicator conditions at that moment. This is a 3-class classification on 962 samples — not transition-based.

### Era splitting strategy
- **D-02:** Binary split at Feb 9, 2019. Train separate decision trees for pre-2019 and post-2019 eras. This directly tests the confirmed structural change hypothesis from v1.0 analysis.

### Decision tree configuration
- **D-03:** Max tree depth capped at 4-5 levels to keep extracted rules human-readable and avoid overfitting on 962 samples.

### Output format
- **D-04:** Human-readable rule strings printed to console and saved to a text/markdown report file. Format matches DISC-03 requirement: "Buy when EMA9 > EMA21 AND MACD histogram > 0: 78% confidence".

### Code location
- **D-05:** Rule discovery code lives in `analysis/rule_discovery.py` as a standalone analysis script, consistent with existing `analysis/` directory pattern.

### Claude's Discretion
- Statistical profiling depth (DISC-01): whether to include continuous indicator distributions alongside boolean feature frequency tables, based on what best reveals separation between signal types
- Feature selection for decision tree: boolean-only vs boolean+continuous features, based on what the statistical profiling reveals about discriminability
- Class imbalance handling strategy (Buy/Sell/Cash distribution may be uneven)
- scikit-learn DecisionTreeClassifier hyperparameters beyond max_depth
- Statistical profiling visualization approach (tables, bar charts, etc.)
- Report file format and structure details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Feature snapshot (input data)
- `core/feature_snapshot.py` -- extract_feature_snapshot() produces the 962-row DataFrame with all indicator values + 8 boolean features. This is the direct input to rule discovery.
- `core/indicators.py` -- Indicator computation functions (EMA, SMA, MACD, Heikin Ashi). Defines what features are available.

### Signal data
- `data/signals/nasdaq_signals_full.csv` -- Full 962-signal ground truth (1974-2026) with date, signal, gain_loss_pct, dollar_becomes

### Data infrastructure
- `core/data_loader.py` -- DataLoader for NASDAQ OHLCV data with /1000 normalization
- `core/signal_loader.py` -- Signal fixture loader (extended in Phase 7 for dollar_becomes)

### Existing analysis patterns
- `analysis/validate_v2.py` -- Full validation pipeline; reference for analysis script structure
- `analysis/hypothesis/` -- Hypothesis testing framework from v1.0; reference for parameter sweep patterns

### Requirements
- `.planning/REQUIREMENTS.md` -- DISC-01 (statistical profile), DISC-02 (decision tree), DISC-03 (human-readable rules), DISC-04 (era-aware analysis)

### Prior phase context
- `.planning/phases/07-data-foundation/07-CONTEXT.md` -- Data loading decisions (D-03: pass through all data, D-05: warn-not-fail on gaps)
- `.planning/phases/08-indicator-engine/08-RESEARCH.md` -- Indicator engine research and implementation decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/feature_snapshot.py` extract_feature_snapshot(): Produces ready-to-use DataFrame with 962 rows, all indicator values, and 8 boolean features. Direct input to decision tree.
- `core/indicators.py` build_indicator_dataframe(): Computes all indicators on NASDAQ OHLCV. Called upstream of feature snapshot.
- `core/data_loader.py` DataLoader: Loads and normalizes NASDAQ data. Already proven across Phases 1-8.
- `core/signal_loader.py` load_signal_fixture(): Loads 962 signals with date/signal/gain_loss_pct/dollar_becomes.

### Established Patterns
- Module-level pure functions (no classes) for computation — established in Phase 8 indicators
- Analysis scripts in `analysis/` follow standalone pattern: load data, compute, print report, optionally save output
- `analysis/validate_v2.py` uses three-way comparison and dashboard output — reference for report structure

### Integration Points
- Feature snapshot output (962-row DataFrame) is the sole input to rule discovery
- Discovered rules will feed into Phase 10 validation (match rate scoring, visual comparison)
- scikit-learn is not currently in pyproject.toml — will need to be added as dependency

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

*Phase: 09-rule-discovery*
*Context gathered: 2026-03-29*
