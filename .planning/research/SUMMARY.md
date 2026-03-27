# Project Research Summary

**Project:** MDM Reverse-Engineering System
**Domain:** Quantitative trading strategy analysis / rule-based model reverse-engineering
**Researched:** 2026-03-27
**Confidence:** HIGH (stack, architecture, pitfalls) / MEDIUM (differentiator features)

## Executive Summary

This project is a rule-based reverse-engineering effort aimed at reconstructing the post-2019 logic of Dr. K's Market Direction Model (MDM) from published signal history. Unlike typical ML projects, the goal is human-interpretable rule discovery — the model must remain explainable. With only ~100 published signals and a ~7-year dataset (~13K NASDAQ rows, ~3.7K VN30 rows), machine learning is explicitly excluded: the sample is too small and overfitting risk is extreme. The correct approach is systematic hypothesis testing — propose a rule modification, measure signal match rate, iterate.

The recommended approach is a three-layer Python architecture (core infrastructure → strategy implementations → analysis tools), preserving the existing pandas + custom state-machine pattern but refactoring the duplicated code into a shared `core/` package. The current codebase has three copies of the same infrastructure (MDM, VSA, and a nascent v2). Consolidation is not just a cleanliness concern — it is necessary for reliable divergence analysis, because the signal comparison engine must be shared to produce consistent results across strategy variants.

The two highest risks are (1) lookahead bias in the backtester — the engine must be strictly point-in-time — and (2) data normalization, because US market CSVs have prices scaled ~1000x and any miscorrection silently corrupts every percentage-based rule (FTD thresholds, distribution day counts, stop losses). These two issues must be resolved in Phase 1 before any rule discovery work begins. A third risk, overfitting to the training signal set, must be controlled by holding out 2023-2026 signals for final validation.

## Key Findings

### Recommended Stack

The existing pandas + numpy + custom state-machine engine is the correct core. No framework replacement is warranted at this dataset scale. TA-Lib should be added for standard indicators (RSI, MA families), but the MDM-specific indicators (Follow-Through Days, Distribution Days, Rally Attempts) must remain hand-coded — no library implements them. The custom backtesting engine (`mdm_engine.py`) is superior to backtrader/zipline for this use case because MDM is a state machine, not an event-driven portfolio; generic frameworks impose unnecessary complexity.

**Core technologies:**
- **pandas >= 2.2**: Primary data structure for all OHLCV operations — existing codebase, migration cost outweighs polars gains at this scale
- **numpy >= 1.26**: Vectorized math for indicator calculations
- **ta-lib / pandas-ta**: Standard technical indicators (MA, RSI); pandas-ta as fallback if TA-Lib C lib fails
- **Custom state-machine engine**: MDM Cash→Buy→Hold→Warning→Short logic; generic frameworks cannot represent this cleanly
- **matplotlib + mplfinance**: Signal overlay charts and candlestick visualization — essential for visual divergence analysis
- **scipy.stats**: Statistical tests for signal pattern analysis during hypothesis testing
- **pytest**: Rule validation — each rule modification must produce a verifiable expected signal set
- **pyproject.toml**: Dependency management — currently missing from the repo

**Do not add:** scikit-learn, XGBoost, LSTM, backtrader, zipline, real-time data feeds, or web dashboards.

### Expected Features

**Must have (table stakes) — these enable the core mission:**
- Data normalization layer — US prices are ~1000x scaled; all percentage rules fail without this
- Published signal parser — Dr. K's NASDAQ/TECL signal history as structured test fixtures
- Signal comparison engine — match scoring between model-generated and published signals; biggest current gap
- MDM classic on NASDAQ data — baseline before attempting to reverse-engineer changes
- Divergence analysis report — where and how classic rules fail post-2019
- Cash state modeling — the single most significant post-2019 behavioral change (intermediate Cash state between Buy and Sell)
- Parameterized rule engine — thresholds configurable for systematic experimentation
- Backtesting with standard metrics — equity curve, Sharpe, drawdown, win rate vs. buy-and-hold

**Should have (enable systematic research):**
- Hypothesis testing framework — propose/score rule modifications systematically; highest ROI feature
- Visual signal overlay charts — price chart with model signals and published signals overlaid; visual inspection often reveals what statistics miss
- Parameter sweep / grid search — automated threshold exploration
- Rolling window validation — train pre-2022, validate 2022-2026
- Trade-by-trade attribution — which rule triggered each signal

**Defer to later:**
- VN30 market adaptation — only after NASDAQ rules are validated
- Multi-timeframe analysis — after core rules are stable
- Regime detection — nice-to-have for understanding MDM's operating conditions
- Signal confidence scoring — post-validation refinement

### Architecture Approach

The three-layer design eliminates the current duplication problem. All shared logic moves to `core/` (data loading, normalization, indicator math, backtesting engine, comparison engine, metrics, visualization). Strategy-specific signal logic lives in `strategies/` (mdm_classic, mdm_v2, vsa) and implements a Protocol interface. Analysis tools (divergence, hypothesis, parameter sweep) live in `analysis/`. The strict dependency rule — strategies depend on core, never on each other, core never depends on strategies — is non-negotiable for the comparison engine to work correctly.

**Major components:**
1. `core/data/` — unified OHLCV loader, US price normalizer, published signal parser
2. `core/backtesting/` — generic backtest loop, signal comparison engine, performance metrics
3. `strategies/mdm_classic/` — pre-2019 state machine (FTD, Distribution Days, Rally Attempt)
4. `strategies/mdm_v2/` — post-2019 reverse-engineered rules (parameterized, Cash state)
5. `strategies/vsa/` — Volume Spread Analysis (independent, preserved from current codebase)
6. `analysis/` — divergence report, hypothesis tester, parameter sweep

Migration of existing code to this structure must verify identical backtest output at each step. Any regression is a bug.

### Critical Pitfalls

1. **Lookahead bias in engine** — each bar can only see data up to that bar; MA calculations must use only prior data; run sequentially not vectorized. Enforce at engine architecture level before any rule work begins.

2. **US data price normalization** — NASDAQ/S&P500 CSVs have prices ~1000x scaled; unit test against known real-world index values on specific dates; catches silent corruption of all percentage-based rules.

3. **Overfitting to published signals** — split signals into train (2017-2022) and held-out test (2023-2026); prefer fewer, logically motivated rules over parameter curve-fitting; a 95%+ match rate with many special-case rules is a red flag, not a success.

4. **Post-2019 change may be structural, not parametric** — the Cash state and rapid signal switching suggest an architectural change (new state, possibly new inputs like VIX or breadth), not just threshold tweaks; start with parameter tuning but be prepared to hypothesize new rule structures.

5. **Premature VN30 adaptation** — applying NASDAQ rules to VN30 before NASDAQ validation wastes effort; VN30's 7% price limits, T+2.5 settlement, and 30-stock index composition require separate calibration; treat VN30 as its own phase gated on NASDAQ success.

## Implications for Roadmap

### Phase 1: Foundation and Data Integrity
**Rationale:** All subsequent work depends on correct data and a valid comparison baseline. Normalization errors silently corrupt everything downstream. This phase has no dependencies and must be done first.
**Delivers:** Unified data loader with proven normalization; published signal history as structured fixtures; baseline MDM classic run on NASDAQ data
**Addresses features:** Data normalization layer, published signal parser, MDM classic on NASDAQ (features 1, 8, 3)
**Avoids pitfall:** Data normalization errors (Pitfall 3), TECL vs. NASDAQ signal confusion (Pitfall 4)
**Architecture work:** `core/types.py`, `core/data/loader.py`, `core/data/normalizer.py`, `core/data/signals.py`

### Phase 2: Signal Comparison Infrastructure + Code Consolidation
**Rationale:** The comparison engine is the measurement instrument for all reverse-engineering. Building it before divergence analysis ensures every subsequent finding is reliably scored. Code consolidation must happen here to avoid building the comparison engine on duplicated infrastructure.
**Delivers:** `core/backtesting/comparison.py` with match scoring; consolidated `core/` package; existing mdm_classic and vsa migrated to `strategies/` with verified identical output
**Addresses features:** Signal comparison engine (feature 2)
**Architecture work:** Full three-layer refactor; Strategy Protocol interface; migration verification tests
**Research flag:** Migration verification is straightforward but tedious — standard pattern, no additional research needed

### Phase 3: Divergence Analysis
**Rationale:** Can only be done once comparison infrastructure exists and MDM classic is running on NASDAQ. Output directly informs Phase 4 hypothesis work.
**Delivers:** Report identifying every date/type divergence between classic MDM output and published post-2019 signals; classification of divergences (threshold, timing, structural, irreproducible)
**Addresses features:** Divergence analysis report (feature 4)
**Avoids pitfall:** Assuming post-2019 change is parametric before evidence (Pitfall 10); survivorship bias (Pitfall 6)

### Phase 4: Cash State and Parameterized Engine (MDM v2 Core)
**Rationale:** Divergence analysis output tells us where and how the classic rules fail; this phase builds the v2 engine to fix them systematically. Cash state is the single most significant structural change confirmed by divergence analysis.
**Delivers:** `strategies/mdm_v2/` engine with Cash intermediate state; parameterized threshold configuration; hypothesis testing framework; parameter sweep capability
**Addresses features:** Cash state modeling, parameterized rule engine, hypothesis testing framework, parameter sweep (features 5, 6, 9, 11)
**Avoids pitfall:** Overfitting (train/test split enforced here), lookahead bias (engine architecture established in Phase 1)
**Research flag:** May need deeper research if divergence analysis reveals structural changes (new indicators, new state machine branches) not addressable via parameterization alone

### Phase 5: Validation and Analysis Tools
**Rationale:** Before claiming v2 rules are discovered, validate on held-out 2023-2026 signals and build the visual/attribution tools that either confirm or challenge the rules.
**Delivers:** Rolling window validation results; visual signal overlay charts; trade-by-trade attribution; full performance metrics vs. buy-and-hold
**Addresses features:** Rolling window validation, visual signal overlay, trade-by-trade attribution, backtesting metrics (features 12, 10, 16, 7)
**Avoids pitfall:** Overfitting to training signals (Pitfall 1)

### Phase 6: VN30 Adaptation
**Rationale:** Only possible after NASDAQ rules are validated. VN30's microstructure differences (7% price limits, T+2.5, 30-stock index) require deliberate threshold recalibration, not blind parameter copy.
**Delivers:** VN30-tuned MDM v2 parameters; filters for price-limit days and derivative expiry; volume threshold adjustments; VN30 backtest vs. buy-and-hold
**Addresses features:** VN30 market adaptation module (feature 13)
**Avoids pitfall:** Different market microstructure (Pitfall 7), volume interpretation differences (Pitfall 8), index composition effects (Pitfall 9), premature VN30 application (Pitfall 11)
**Research flag:** May need research on VN30-specific parameter ranges; Vietnamese market microstructure is sparsely documented

### Phase Ordering Rationale

- Data integrity (Phase 1) must precede everything — a normalization bug silently corrupts all rule-discovery work
- Signal comparison (Phase 2) must precede divergence analysis (Phase 3) — you cannot measure divergences without a measurement tool
- Divergence analysis (Phase 3) must precede v2 hypothesis work (Phase 4) — without knowing where the rules fail you are guessing
- NASDAQ validation (Phases 1-5) must precede VN30 adaptation (Phase 6) — different market, separate calibration problem
- Version-control every rule hypothesis as a named configuration file — this prevents the process pitfall of losing track of what was tried

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4:** If divergence analysis reveals structural changes (e.g., new indicator inputs like VIX, breadth, or relative strength), the v2 architecture may need redesign — flag for research-phase before implementation
- **Phase 6:** VN30-specific parameter ranges and market microstructure (price limit behavior, T+2.5 sequencing) may require dedicated research before calibration

Phases with standard patterns (skip research-phase):
- **Phase 1:** Data loading, normalization, and CSV parsing are well-understood; unit test coverage is sufficient
- **Phase 2:** Code consolidation and Strategy Protocol are standard refactoring patterns
- **Phase 5:** Backtesting metrics, rolling window validation, and matplotlib charting are all well-documented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing codebase validates pandas+numpy; custom engine rationale is well-established; only optional additions (polars, vectorbt) are MEDIUM |
| Features | HIGH (table stakes) / MEDIUM (differentiators) | Table stakes are directly derivable from project goals; differentiator ROI rankings are research-based estimates |
| Architecture | HIGH | Component boundaries and data flow are clear; VSA multi-stock abstraction is the one open question |
| Pitfalls | HIGH (data/implementation) / MEDIUM-HIGH (VN30) | Data and lookahead pitfalls are empirically validated concerns; VN30 microstructure risks are well-reasoned but less tested |

**Overall confidence:** HIGH for execution approach; MEDIUM for how long post-2019 rule discovery will take

### Gaps to Address

- **2019 rule change nature:** Whether the "material change" is parametric or structural cannot be determined until divergence analysis is complete. Phase 4 scope may expand significantly if the change is structural.
- **Same-day signal events:** Some published signals show same-day state switching (e.g., Buy→Cash same day) that may be irreproducible with daily OHLCV bars. Establish an acceptable match-rate floor (e.g., 85% within 2 days) rather than targeting 100%.
- **FTD threshold ambiguity:** Whether the 2% FTD threshold applies pre- or post-2019 is unresolved. Document and test both variants in Phase 4.
- **VSA abstraction:** Multi-stock portfolio iteration in VSA is structurally different from single-index MDM; the generic backtesting engine loop may need a separate code path. Resolve during Phase 2 migration.

## Sources

### Primary (HIGH confidence)
- Existing codebase (`models/`, `vn30_vsa/`) — confirmed duplicated infrastructure, confirmed existing state-machine engine
- Dr. K's published MDM rules documentation (`rules.md`) — confirmed signal definitions, state machine states, FTD/DD criteria
- Published signal history (implied by PROJECT.md) — signal dates and types used as ground truth

### Secondary (MEDIUM confidence)
- O'Neil methodology literature — FTD and Distribution Day definitions; behavioral basis for rule spirit vs. curve-fitting constraint
- TA-Lib documentation — indicator availability and calculation correctness
- pandas 2.2 release notes — DataFrame API stability

### Tertiary (LOW confidence / needs validation)
- VN30 microstructure specifics (T+2.5 effects on re-entry, price limit frequency) — needs empirical validation against actual VN30 data
- Post-2019 structural change hypotheses — unverified until divergence analysis runs

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*
