# Project Research Summary

**Project:** MDM Hybrid Engine (v3.0) — State Machine + Indicator Filter
**Domain:** Hybrid trading model reverse-engineering (rule-based FSM + ML-discovered indicator filters)
**Researched:** 2026-03-29
**Confidence:** HIGH

## Executive Summary

The Hybrid MDM Engine (v3.0) is a layered trading model that combines the existing v2 state machine (DD counting, FTD detection, rally attempts) with an indicator filter layer (EMA 9/21/55, MA 200, MACD 12-26-9) to improve signal accuracy beyond the Phase 9/10 baseline of 56.7%. The project has substantial existing infrastructure that must be reused rather than rebuilt: all indicator computation is in `core/indicators.py`, the v2 state machine is stable in `strategies/mdm_v2/`, the validation pipeline against 962 published signals exists in `analysis/validate_discovery.py`, and the 8 boolean features from Phase 9/10 rule discovery are in `core/feature_snapshot.py`. No new library dependencies are needed — the entire hybrid engine builds on what is already installed (Python 3.10+, pandas, numpy, scikit-learn, matplotlib, pytest).

The recommended approach is a strict Propose-Filter-Decide pipeline: the classic state machine proposes a signal transition, the indicator filter layer confirms or vetoes (but never originates signals independently), and the position manager commits the state change only when confirmed. This architecture preserves the interpretability and debuggability of the v2 system while adding the indicator-gated behavior that Phase 9/10 confirmed characterizes Dr. K's post-2019 model. The hybrid engine is built as a new `strategies/mdm_hybrid/` package that imports v2 components without modifying them — clean separation with no code duplication. Four new components are required: `HybridConfig`, `IndicatorFilter`, `HybridPositionManager`, and `HybridEngine`.

The single most dangerous risk is overfitting indicator filter thresholds to the 95 post-2019 signals (roughly 30 per class with 8 boolean features). A match rate jump from 58.9% to more than 80% after adding filters is a red flag, not a success. The project must hold out at least 19 post-2019 signals before any filter tuning begins, limit total filter rules to 2-3, and require each rule to cover at least 10 historical signals. The second critical risk is state machine corruption: the v2 DD counter resets eagerly inside the FTD detection call chain — if the FTD transition is then vetoed by the indicator filter, the counter is already wiped and the model is stuck in CASH with no exit path. A two-phase commit pattern (propose without mutating state, confirm, then commit mutation) must be implemented before any filter code is written.

## Key Findings

### Recommended Stack

No new dependencies required. The existing stack covers all needs for the hybrid engine. The critical insight from stack research is that external FSM libraries (`transitions`, `python-statemachine`) and ML frameworks (PyBroker, LSTM, XGBoost) are explicitly not recommended — all add integration complexity without value for a 3-state deterministic model with 962 training samples. The decision tree from Phase 9 (`analysis/rule_discovery.py`) is the right ML approach; its discovered rules are the starting point for indicator filter conditions, translated into explicit conditional methods rather than loaded as a pickle at runtime.

**Core technologies:**
- Python 3.10+ / pandas / numpy: Already in use — no change needed
- scikit-learn >= 1.5.0: Already in use in `rule_discovery.py` and `validate_discovery.py` — reuse for validation scoring
- pytest >= 9.0.2: Already installed — essential for unit testing the two-phase commit refactor and filter layer
- matplotlib >= 3.7.0: Already installed — needed for three-way comparison chart (classic vs v2 vs hybrid)

**What not to use:** `transitions`, `python-statemachine`, PyBroker, TensorFlow/LSTM, XGBoost, networkx.

### Expected Features

**Must have (table stakes — hybrid MVP):**
- State machine layer (DD/FTD/Rally): Reuse v2 components unchanged, import cross-package
- Indicator filter layer (EMA/MACD confirmation): Core new code — `IndicatorFilter` class with boolean condition methods
- Signal confirmation logic (Propose-Filter-Decide): The central integration pattern; three explicit steps per day
- Signal override/veto logic: Force early exit when EMA bearish before DD count reaches threshold
- Indicator-driven cash state insertion: EMA crossover bearish = CASH trigger beyond DD counting
- Parameterized `HybridConfig` dataclass: All filter rules must be configuration, not hardcoded in engine
- Validation scoring against 962 signals: Reuse `validate_discovery.py`; target > 56.7% post-2019 accuracy

**Should have (add when MVP validates above 56.7%):**
- Indicator confidence scoring: Weighted confirmation (3/4 indicators agree = HIGH confidence)
- Contextual state transitions: Track state duration for context-dependent filter rules
- Transition cooldown (N-day persistence): Prevent whipsaw in fast-switching periods
- Parameter sweep for filter thresholds: Grid search over boolean filter combinations
- Three-way comparison dashboard: Classic vs v2 vs hybrid side-by-side accuracy chart

**Defer to v2+:**
- Adaptive indicator weights by market regime: Requires regime detection infrastructure and out-of-sample validation
- Heikin Ashi Smoothed as primary filter: Less well-understood than EMA/MACD; add only after base hybrid is validated
- VN30 adaptation of hybrid model: Must first prove hybrid works on NASDAQ

### Architecture Approach

The hybrid engine lives in a new `strategies/mdm_hybrid/` package, structured identically to the existing `mdm_classic`, `mdm_v2`, and `vsa` packages. Four new components are required; everything else is imported from existing modules unchanged. The core data flow is: DataLoader loads OHLCV → `build_indicator_dataframe()` adds EMA/MACD/HA columns → v2 `Indicators.add_*()` adds classic columns (MA50/MA10/p_loc) → `HybridEngine.run()` iterates daily bars via the Propose-Filter-Decide pipeline → `extract_model_signals()` and `compare_signals()` score against 962 published signals. The validation interface already works because it maps BUY/CASH/SELL state strings — the hybrid engine outputs the same format as v2.

**Major components:**
1. `HybridConfig` (`strategies/mdm_hybrid/config.py`) — Composes `MDMV2Config` by containment plus indicator filter boolean flags; all filter rules are config, never hardcoded in engine logic
2. `IndicatorFilter` (`strategies/mdm_hybrid/indicator_filter.py`) — Stateless evaluator per row: individual condition methods (`is_bullish_ema_stack`, `is_macd_bullish`, `is_above_ma200`) plus `evaluate(row, proposal, state) -> Verdict`; no internal state
3. `HybridPositionManager` (`strategies/mdm_hybrid/position_manager.py`) — 3-state machine (BUY/CASH/SELL) with two-phase commit; `process_day()` accepts filter verdict and only commits state mutation after CONFIRM; separates proposal from commitment
4. `HybridEngine` (`strategies/mdm_hybrid/hybrid_engine.py`) — Orchestrator: data preparation, daily loop via `_compute_classic_proposal` → `indicator_filter.evaluate` → `_resolve_action` → `position_manager.process_day`, results DataFrame output matching v2 format

**Build order by dependency:** HybridConfig (no deps) → IndicatorFilter (config only) → HybridPositionManager (config only) → HybridEngine (all above + v2 imports + core) → validation entry script.

### Critical Pitfalls

1. **Signal authority ambiguity (design time)** — Without a strict hierarchy, indicator-originated signals and state machine signals create untestable spaghetti logic. Prevention: indicators can only CONFIRM or VETO; they never propose new signals. Encode this as an assertion in `_resolve_action()`. Define the authority chain before writing any code — this is a design decision, not an implementation detail.

2. **State machine corruption from indicator vetos (implementation time)** — The v2 DD counter resets eagerly inside the FTD detection call chain. If the FTD transition is then vetoed, the counter is already wiped and the model is stuck in CASH with no exit path. Prevention: refactor to two-phase commit before adding any filter logic. This is the hardest integration task and cannot be deferred.

3. **Overfitting indicator filter thresholds to 95 post-2019 signals (filter tuning time)** — 95 signals with 8 boolean features is near the statistical floor for rule discovery. Prevention: hold out 19+ signals before tuning begins; use LOOCV; require each rule to cover 10+ historical signals; pre-register rules before examining data. A match rate jump to >80% is a red flag.

4. **Era-dependent filter fragility** — Phase 9/10 confirmed a structural feature shift at Feb 2019 (EMA9-dominant pre-2019 vs EMA55-dominant post-2019 with zero overlap in top-2 features). Prevention: scope the hybrid model explicitly to post-2019; make filter rules configurable for future swapping; track quarterly match rate as a leading indicator of model drift.

5. **Indicator calculation divergence from TradingView** — Dr. K uses TradingView; subtle EMA initialization differences or MACD formula variations mean the model's boolean decisions may disagree with what Dr. K actually sees. Prevention: spot-check 5+ dates against TradingView screenshots before building any filters; use boolean features (MACD > 0, not MACD > 0.37) to absorb small numerical differences.

## Implications for Roadmap

Based on the combined research, the hybrid engine requires five phases following strict dependency order. No phase can be safely started before its predecessor is validated against the regression baseline.

### Phase 1: Architecture Foundation and Two-Phase Commit Refactor
**Rationale:** The state machine corruption pitfall requires refactoring `process_day()` to separate proposal from commitment before any filter code is added. This is a precondition, not an optional improvement. Without two-phase commit, adding any indicator veto will corrupt the DD counter and create stuck states. Also establishes the `HybridConfig` dataclass and package structure.
**Delivers:** `strategies/mdm_hybrid/` package skeleton; `HybridConfig` dataclass with v2 composition; `HybridPositionManager` with two-phase commit; unit tests proving vetoed FTD does not reset DD counter.
**Addresses:** Parameterized config (table stakes), state machine foundation
**Avoids:** P1 (signal authority ambiguity — defined in design doc), P4 (state machine corruption — fixed before filter code exists), P5 (Cash semantics — defined explicitly as DD-accumulation and stop-loss paths only)

### Phase 2: Indicator Filter Layer
**Rationale:** `IndicatorFilter` depends only on `HybridConfig` and has no state machine dependency. Building and unit-testing it in isolation before wiring into the engine catches filter logic bugs with synthetic data rather than in a live engine loop. The TradingView spot-check belongs here — before any thresholds are calibrated.
**Delivers:** `IndicatorFilter` class with all boolean condition methods; `evaluate()` returning CONFIRM/VETO/OVERRIDE verdicts; unit tests covering each condition with synthetic row data; TradingView spot-check validation of EMA/MACD boolean values at 5+ dates.
**Uses:** `core/indicators.py` (existing, no changes)
**Avoids:** P2 (look-ahead bias — verify causal computation in each method), P7 (indicator divergence — TradingView spot-check before any filter tuning)

### Phase 3: HybridEngine Integration
**Rationale:** Wire the three components (classic state machine, indicator filter, hybrid position manager) into the Propose-Filter-Decide pipeline. Must verify that when the filter is set to "always confirm," the hybrid engine produces identical output to the v2 engine — this is the regression baseline. Without this baseline, it is impossible to isolate whether accuracy changes come from filter rules or integration bugs.
**Delivers:** `HybridEngine` with full daily processing loop; output DataFrame matching v2 format; regression test confirming identity with v2 when filter is disabled; `scripts/run_hybrid_backtest.py` entry point outputting three-way comparison.
**Implements:** Full Propose-Filter-Decide pipeline; full data flow from DataLoader through validation scoring
**Avoids:** P1 (authority chain enforced as assertion in `_resolve_action()`), P4 (two-phase commit already in place)

### Phase 4: Filter Tuning and Validation
**Rationale:** Only after a working integration exists can filter rules be tested against published signals. Must hold out 19+ post-2019 signals before tuning begins — this partition must be selected and locked before any filter analysis runs. Target: hybrid accuracy > 56.7% on the post-2019 held-out set.
**Delivers:** 2-3 indicator filter rules (maximum) validated with LOOCV; confusion matrix and per-type accuracy vs pure state machine and pure decision tree; cross-era regression check (pre-2019 accuracy must not catastrophically degrade); signal log recording "proposed X, filter said Y, final Z" for every day.
**Addresses:** Validation scoring (table stakes), era-aware evaluation
**Avoids:** P3 (overfitting — LOOCV required; 10+ signal rule threshold enforced), P6 (era fragility — post-2019 explicit scope; held-out 2024-2026 accuracy reported separately)

### Phase 5: Enhancements (Post-Validation, Conditional)
**Rationale:** Only warranted if Phase 4 validates the hybrid approach by exceeding 56.7% on the held-out set. Enhancements add accuracy and usability but do not change the core architecture.
**Delivers:** Indicator confidence scoring (weighted majority confirmation); transition cooldown (N-day persistence); grid search over filter boolean combinations; three-way visual comparison dashboard.
**Addresses:** Differentiator features — confidence scoring, contextual transitions, cooldown, parameter sweep
**Condition:** Phase 4 must demonstrate > 56.7% post-2019 accuracy before this phase is authorized.

### Phase Ordering Rationale

- **Phase 1 before all others:** Two-phase commit is a structural precondition. Adding filter logic to eagerly-mutating state machine code creates the DD counter corruption bug. Retrofitting two-phase commit after filter code exists would require rewriting all integration points simultaneously — high risk.
- **Phase 2 before Phase 3:** `IndicatorFilter` is stateless and independently testable. Building it in isolation with synthetic unit tests (known indicator values, expected verdicts) is far safer than debugging filter logic inside a live engine loop where the source of errors is ambiguous.
- **Phase 3 establishes regression baseline before Phase 4 begins:** The baseline (hybrid-with-filter-disabled = v2 output) must be locked in git before filter rules are added. Without it, there is no way to isolate accuracy changes.
- **Phase 4 test set must be selected at end of Phase 3:** The 19+ held-out post-2019 signals must be selected and locked immediately after Phase 3 completes — before any filter analysis begins. Selecting them after seeing partial results would introduce data leakage.
- **Phase 5 is conditional on Phase 4 success:** If hybrid accuracy does not exceed 56.7%, Phase 5 enhancements are premature. The correct response to Phase 4 failure is to revisit Phase 4 with a different filter hypothesis, not to add more features.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Two-phase commit refactor):** The exact mutation points in `DistributionDayCounter`, `RallyAttemptTracker`, and `FTDSignalDetector` need a code-level audit before the design is finalized. Specifically: where does `dd_counter.reset()` get called in the FTD detection call chain? This must be mapped before writing `HybridPositionManager`.
- **Phase 4 (Pre-registration of filter rules):** The specific 2-3 filter rules to pre-register before examining the data require a hypothesis-first design session informed by Phase 9 feature importances (close_above_ema55 dominant post-2019, importance=0.687). Consider a brief research-phase to select and document candidate rules before Phase 4 execution begins.

Phases with standard patterns (skip research-phase):
- **Phase 2 (IndicatorFilter):** Straightforward class with boolean condition methods. Pattern already established in `core/feature_snapshot.py`. No research needed.
- **Phase 3 (Engine integration):** The `strategies/mdm_v2/mdm_v2_engine.py` wiring pattern is the exact template. Propose-Filter-Decide is a standard pipeline. No research needed.
- **Phase 5 (Enhancements):** All enhancements extend established project patterns. Confidence scoring and parameter sweeps follow existing conventions in `analysis/`.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies needed; all alternatives evaluated and rejected with clear rationale grounded in project specifics (962 samples, 3-state machine, existing infrastructure) |
| Features | HIGH | Grounded in existing codebase analysis, Dr. K's known TradingView setup, and Phase 9/10 validated findings; differentiator features are clearly flagged as post-validation |
| Architecture | HIGH | Fully specified with existing module interfaces documented; proposed structure follows established project conventions; build order follows strict dependency chain |
| Pitfalls | HIGH | Pitfalls derived from project-specific Phase 9/10 findings — P3 (95-signal overfitting) and P4 (DD counter reset) are precisely located in existing code, not generic advice |

**Overall confidence:** HIGH

### Gaps to Address

- **Exact mutation points in v2 components:** Phase 1 requires auditing where `dd_counter.reset()`, `rally_tracker` state updates, and `ftd_detector` internal state mutations occur in the call chain. This is a code-reading task (run `grep -n "reset\|self\." strategies/mdm_v2/*.py`) that must complete before Phase 1 design is finalized.
- **TradingView indicator parity:** `core/indicators.py` uses `adjust=False` for EMA alignment with TradingView. MACD and HA Smoothed parity have not been formally verified. Must spot-check in Phase 2 before any filter thresholds are established.
- **Held-out test set selection:** The specific 19+ post-2019 signals to hold out for Phase 4 final evaluation must be selected before Phase 3 completes — selecting them after seeing engine output would introduce data leakage. Select at start of Phase 4, lock in config, never touch until final evaluation.
- **Pre-registered filter rule candidates:** The 2-3 filter rules to test in Phase 4 must be decided based on domain logic and Phase 9 feature importances, not by scanning data. This design decision belongs at the start of Phase 4 planning.

## Sources

### Primary (HIGH confidence)
- Existing codebase (`core/indicators.py`, `core/feature_snapshot.py`, `strategies/mdm_v2/`, `analysis/rule_discovery.py`, `analysis/validate_discovery.py`) — interfaces, integration patterns, confirmed working
- Phase 9 findings: 962 signals, pre-2019 CV=53.9%, post-2019 CV=58.9%, feature importances, structural shift confirmed at Feb 2019 (EMA9 dominant pre vs EMA55 dominant post, zero overlap in top-2 features)
- Phase 10 findings: 21.3% cross-era degradation, era-specific trees required, confusion matrices per signal type

### Secondary (MEDIUM confidence)
- [Hybrid AI-Driven Trading System (ComSIA 2026)](https://arxiv.org/html/2601.19504v1) — regime-adaptive hybrid combining technical indicators with ML
- [Heuristic Based Trading System on Forex Data](https://www.sciencedirect.com/science/article/abs/pii/S1568494616300369) — signal conflict resolution via weighted majority voting
- [Understanding Look-Ahead Bias in Trading Strategies](https://www.marketcalls.in/machine-learning/understanding-look-ahead-bias-and-how-to-avoid-it-in-trading-strategies.html)
- Dr. K's known TradingView indicator setup (EMA 9/21/55, MA 200, MACD 12-26-9, HA Smoothed 55) — from PROJECT.md context

### Tertiary (LOW confidence)
- `transitions` library (v0.9.2) and `python-statemachine` (v3.0.0) — evaluated and rejected; documentation reviewed to confirm rationale for rejection
- IBD distribution day analysis resources — corroborating signal definitions, not primary sources for hybrid design

---
*Research completed: 2026-03-29*
*Ready for roadmap: yes*
