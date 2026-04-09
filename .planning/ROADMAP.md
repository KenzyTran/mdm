# Roadmap: MDM Reverse-Engineering & VN30 Market Timing

## Milestones

- ✅ **v1.0 MDM Classic & VN30** - Phases 1-6 (shipped 2026-03-28)
- ✅ **v2.0 MDM Rule Discovery** - Phases 7-10 (shipped 2026-03-29)
- ✅ **v3.0 Hybrid MDM Engine** - Phases 11-15 (shipped 2026-03-29)
- ✅ **v4.0 MDM Short Signal & Dr. K Alignment** - Phases 16-18 (shipped 2026-03-30)
- ✅ **v5.0 Signal Quality & Macro Filter** - Phases 19-22 (shipped 2026-03-31)
- ✅ **v6.0 MDM Fail-Safe & Signal Refinement** - Phases 23-27 (shipped 2026-04-02)
- 📋 **v7.0 CANSLIM + MDM on VN100** - Phases 28-34

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MDM Classic & VN30 (Phases 1-6) - SHIPPED 2026-03-28</summary>

- [x] **Phase 1: Data Integrity** - Unified data loading with proven normalization and published signal fixtures
- [x] **Phase 2: Codebase Organization** - Three-layer architecture with migrated strategies and verified identical output
- [x] **Phase 3: Signal Divergence Analysis** - Comparison engine and divergence report identifying where classic rules fail post-2019
- [x] **Phase 4: MDM v2 Engine** - Cash state machine, parameterized rules, and systematic hypothesis testing
- [x] **Phase 5: Validation & Performance** - Held-out validation, performance metrics, and visual analysis tools
- [x] **Phase 6: VN30 Adaptation** - MDM v2 recalibrated for Vietnamese market microstructure

### Phase 1: Data Integrity
**Goal**: All market data loads correctly and published signal history is available as structured test fixtures
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria** (what must be TRUE):
  1. Running the unified loader on NASDAQ, S&P500, and VN30 CSVs produces normalized OHLCV DataFrames with correct dtypes and no NaN gaps
  2. Spot-checking normalized US prices against known real-world index values on specific dates confirms values within 0.1% tolerance
  3. Published TECL and NASDAQ signal histories parse into structured fixtures with date, signal type, and gain/loss fields that match the source data
  4. All percentage-based calculations (FTD thresholds, stop losses) produce correct results on the normalized data
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md -- Unified DataLoader with normalization and spot-check validation (DATA-01, DATA-02, DATA-03)
- [x] 01-02-PLAN.md -- Signal fixture loader and TECL/NASDAQ published signal CSV files (DATA-04)

### Phase 2: Codebase Organization
**Goal**: Existing code is reorganized into a clean three-layer architecture with zero regression in backtest output
**Depends on**: Phase 1
**Requirements**: ORG-01, ORG-02, ORG-03, ORG-04
**Success Criteria** (what must be TRUE):
  1. Project follows core/ (shared infrastructure), strategies/ (signal logic), analysis/ (tools) architecture with no cross-strategy imports
  2. MDM classic strategy runs from strategies/mdm_classic/ and produces identical backtest output to the original models/ implementation
  3. VSA strategy runs from strategies/vsa/ and produces identical backtest output to the original vn30_vsa/ implementation
  4. A regression test suite confirms bit-for-bit identical signal sequences and equity curves before and after migration
**Plans:** 4 plans

Plans:
- [x] 02-01-PLAN.md -- Golden baselines and regression test scaffolds (ORG-04)
- [x] 02-02-PLAN.md -- Migrate MDM and VSA strategies to strategies/ (ORG-01, ORG-02, ORG-03)
- [x] 02-03-PLAN.md -- Move scripts/analysis, update notebooks, delete old dirs, run regression (ORG-01, ORG-04)
- [x] 02-04-PLAN.md -- Fix trade regression test signal_type NaN mismatch (ORG-04, gap closure)

### Phase 3: Signal Divergence Analysis
**Goal**: The project can measure exactly where and how classic MDM rules diverge from Dr. K's published post-2019 signals
**Depends on**: Phase 2
**Requirements**: SIG-01, SIG-02, SIG-03, SIG-04
**Success Criteria** (what must be TRUE):
  1. Signal comparison engine scores model-generated signals against published signals with match rate, timing offset, and per-signal type breakdown
  2. MDM classic rules running on NASDAQ data produce a complete Buy/Sell/Cash signal list for the full 2017-2026 period
  3. Divergence report lists every date where classic output differs from published post-2019 signals, classified by type (threshold, timing, structural, irreproducible)
  4. Visual overlay chart shows NASDAQ price with both model signals and published signals plotted, making divergence patterns visually apparent
**Plans:** 2 plans
**UI hint**: yes

Plans:
- [x] 03-01-PLAN.md -- Signal comparison engine and model signal extraction (SIG-01, SIG-02)
- [x] 03-02-PLAN.md -- Divergence report, visual overlay chart, and interactive notebook (SIG-03, SIG-04)

### Phase 4: MDM v2 Engine
**Goal**: A parameterized MDM v2 engine with Cash state can be systematically tuned to maximize match rate against published signals
**Depends on**: Phase 3
**Requirements**: MDM-01, MDM-02, MDM-03, MDM-04
**Success Criteria** (what must be TRUE):
  1. MDM v2 state machine implements Cash as an intermediate state between Buy and Sell, matching observed post-2019 signal behavior
  2. All rule thresholds (FTD %, DD %, MA periods, DD count trigger, etc.) are configurable via a named configuration file
  3. Hypothesis testing framework takes a rule modification, runs it against train-set signals (2017-2022), and reports match rate delta
  4. Parameter sweep searches a defined parameter space and reports the top-N configurations ranked by signal match rate
  5. Best configuration achieves measurably higher match rate than classic rules on the training signal set
**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md -- MDM v2 engine with 3-state machine and parameterized config (MDM-01, MDM-02)
- [x] 04-02-PLAN.md -- Hypothesis testing framework and parameter sweep (MDM-03, MDM-04)

### Phase 5: Validation & Performance
**Goal**: MDM v2 rules are validated on held-out data and backed by full performance analysis
**Depends on**: Phase 4
**Requirements**: PERF-01, PERF-02, PERF-03
**Success Criteria** (what must be TRUE):
  1. Backtest report shows equity curve, max drawdown, Sharpe ratio, and win rate for MDM v2 on NASDAQ
  2. Performance comparison table shows MDM v2 vs buy-and-hold NASDAQ over the same period
  3. Held-out validation (2023-2026 signals) confirms match rate does not degrade significantly compared to training set (2017-2022)
**Plans:** 2 plans

Plans:
- [x] 05-01-PLAN.md -- V2PerformanceAnalyzer with daily equity, drawdown, Sharpe, win rate and unit tests (PERF-01)
- [x] 05-02-PLAN.md -- Validation script, three-way comparison, dashboard chart, and notebook (PERF-02, PERF-03)

### Phase 6: VN30 Adaptation
**Goal**: MDM v2 is recalibrated for VN30 market characteristics and produces actionable backtest results
**Depends on**: Phase 5
**Requirements**: VN30-01, VN30-02, VN30-03
**Success Criteria** (what must be TRUE):
  1. Market microstructure filters handle VN30 7% daily price limit days, T+2.5 settlement constraints, and derivative expiry effects
  2. MDM v2 parameters are recalibrated for VN30 (different volatility, volume characteristics, index composition)
  3. Full VN30 backtest report with equity curve, drawdown, Sharpe, and win rate is generated and compared against VN30 buy-and-hold
**Plans:** 3 plans

Plans:
- [x] 06-01-PLAN.md -- VN30 microstructure filters and engine DD suppression integration (VN30-01)
- [x] 06-02-PLAN.md -- Parameter sweep Sharpe adaptation and VN30 grid search (VN30-02)
- [x] 06-03-PLAN.md -- VN30 backtest report with performance metrics and buy-and-hold comparison (VN30-03)

</details>

<details>
<summary>v2.0 MDM Rule Discovery (Phases 7-10) - SHIPPED 2026-03-29</summary>

- [x] **Phase 7: Data Foundation** - Full NASDAQ OHLCV from 1974+ and 962-signal history loaded as ground truth
- [x] **Phase 8: Indicator Engine** - Multi-indicator feature engineering with feature snapshots at every signal date
- [x] **Phase 9: Rule Discovery** - Statistical analysis and decision tree extraction of indicator-based signal rules
- [x] **Phase 10: Discovery Validation** - Match rate scoring, train/test split, and visual comparison of discovered rules

### Phase 7: Data Foundation
**Goal**: Full 52-year NASDAQ price history and complete 962-signal ground truth are loaded and ready for indicator computation
**Depends on**: Phase 6 (v1.0 complete)
**Requirements**: DATA-05, DATA-06
**Success Criteria** (what must be TRUE):
  1. NASDAQ OHLCV data loads from 1974 onward with no gaps in trading days, correct dtypes, and prices matching known historical values
  2. Full signal history loader parses all 962 signals from nasdaq_signals_full.csv with date, signal type (Buy/Sell/Cash), gain/loss, and dollar-becomes columns
  3. Signal dates align with available OHLCV dates (every signal date has a corresponding price row)
**Plans:** 2 plans

Plans:
- [x] 07-01-PLAN.md -- Extend DataLoader spot-checks and signal loader for dollar_becomes (DATA-05, DATA-06)
- [x] 07-02-PLAN.md -- Date alignment gap report and integration tests (DATA-05, DATA-06)

### Phase 8: Indicator Engine
**Goal**: All known Dr. K indicators are computed across the full NASDAQ history and feature snapshots are extracted at every signal date
**Depends on**: Phase 7
**Requirements**: IND-01, IND-02, IND-03, IND-04, IND-05
**Success Criteria** (what must be TRUE):
  1. EMA 9, EMA 21, EMA 55, and MA 200 are computed on daily NASDAQ close prices and spot-checked against known values
  2. MACD (12, 26, 9) with signal line and histogram produces values consistent with standard implementations
  3. Heikin Ashi Smoothed candles are computed from OHLC data with visually verifiable smoothing behavior
  4. Feature snapshot at each of the 962 signal dates contains all indicator values, EMA crossover states (9/21, 21/55), price-vs-MA relationships, and MACD histogram sign
  5. Feature snapshot DataFrame has no NaN values for signal dates after indicator warm-up period (~200 trading days)
**Plans:** 2 plans

Plans:
- [x] 08-01-PLAN.md -- Indicator computation module: EMA, SMA, MACD, Heikin Ashi Smoothed (IND-01, IND-02, IND-03, IND-04)
- [x] 08-02-PLAN.md -- Feature snapshot extraction at 962 signal dates (IND-05)

### Phase 9: Rule Discovery
**Goal**: Indicator-based rules that drive Buy/Sell/Cash signal transitions are discovered through statistical analysis and machine learning
**Depends on**: Phase 8
**Requirements**: DISC-01, DISC-02, DISC-03, DISC-04
**Success Criteria** (what must be TRUE):
  1. Statistical profile shows frequency distributions of indicator conditions (EMA crossover states, MACD sign, price-vs-MA position) at each signal type, revealing clear separation between Buy/Sell/Cash
  2. Decision tree classifier achieves meaningfully above-chance accuracy on classifying signal transitions from indicator features
  3. Human-readable rules are extracted from the decision tree with confidence scores
  4. Era comparison shows quantifiable differences in rule patterns pre-2019 vs post-2019, confirming or refining the structural change hypothesis
**Plans:** 2 plans

Plans:
- [x] 09-01-PLAN.md -- Dependency setup, test scaffold, and era-aware statistical profiling (DISC-01, DISC-04)
- [x] 09-02-PLAN.md -- Decision tree training, rule extraction, and full report generation (DISC-02, DISC-03, DISC-04)

### Phase 10: Discovery Validation
**Goal**: Discovered rules are validated against the full signal history and presented alongside published signals for visual confirmation
**Depends on**: Phase 9
**Requirements**: VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. Match rate report scores discovered rules against all 962 signals with per-type breakdown (Buy/Sell/Cash match rates separately)
  2. Train/test validation shows rules trained on pre-2019 data achieve acceptable match rate on post-2019 held-out period (and vice versa)
  3. Comparison dashboard overlays discovered-rule signals and published signals on NASDAQ price chart, making agreement and divergence visually apparent
**Plans:** 2 plans

Plans:
- [x] 10-01-PLAN.md -- Match rate scoring, confusion matrices, and cross-era validation (VAL-01, VAL-02)
- [x] 10-02-PLAN.md -- Two-era comparison dashboard and end-to-end pipeline (VAL-03)
**UI hint**: yes

</details>

<details>
<summary>v3.0 Hybrid MDM Engine (Phases 11-15) - SHIPPED 2026-03-29</summary>

- [x] **Phase 11: Foundation & Two-Phase Commit** - Package skeleton, HybridConfig, and state machine refactor to prevent corruption from indicator vetos (completed 2026-03-29)
- [x] **Phase 12: Indicator Filter Layer** - Stateless IndicatorFilter with boolean condition methods and TradingView parity check (completed 2026-03-29)
- [x] **Phase 13: Hybrid Engine Integration** - Wire Propose-Filter-Decide pipeline with confirmation, override, and cash insertion logic (completed 2026-03-29)
- [x] **Phase 14: Hybrid Validation** - Validate hybrid model against 962 signals with confusion matrix and per-type accuracy (completed 2026-03-29)
- [x] **Phase 15: Advanced Features** - Contextual transitions, HA Smoothed filter, confidence scoring, three-way dashboard (completed 2026-03-29)

### Phase 11: Foundation & Two-Phase Commit
**Goal**: Hybrid engine has a safe architectural foundation where indicator vetos cannot corrupt state machine internals
**Depends on**: Phase 10
**Requirements**: HYB-01, HYB-06
**Success Criteria** (what must be TRUE):
  1. `strategies/mdm_hybrid/` package exists with `HybridConfig` dataclass that composes v2 config plus indicator filter flags
  2. State machine proposes signal transitions without mutating internal state (DD counter, rally tracker) until explicit commit is called
  3. A vetoed FTD proposal does not reset the DD counter -- verified by unit test with known scenario
  4. With two-phase commit enabled and no filter active, hybrid position manager produces identical state transitions to v2 position manager
**Plans:** 1/1 plans complete

Plans:
- [x] 11-01-PLAN.md -- Fork v2 package, HybridConfig, HybridEngine with two-phase commit, regression tests (HYB-01, HYB-06)

### Phase 12: Indicator Filter Layer
**Goal**: Indicator conditions can evaluate any market day and return a CONFIRM/VETO/OVERRIDE verdict independently of the state machine
**Depends on**: Phase 11
**Requirements**: HYB-02
**Success Criteria** (what must be TRUE):
  1. `IndicatorFilter` class exposes boolean condition methods for EMA stack (9/21/55), MACD bullish/bearish, and price vs MA 200
  2. `evaluate(row, proposal, current_state)` returns a typed verdict (CONFIRM, VETO, or OVERRIDE) based on configured indicator conditions
  3. Each condition method is unit-tested with synthetic row data producing expected boolean outputs
  4. EMA and MACD boolean values spot-checked against TradingView at 5+ known dates and confirmed matching
**Plans:** 1/1 plans complete

Plans:
- [x] 12-01-PLAN.md -- FilterConfig, Verdict enum, IndicatorFilter with 6 boolean conditions, evaluate() verdict logic, unit tests, TradingView parity (HYB-02)

### Phase 13: Hybrid Engine Integration
**Goal**: The full Propose-Filter-Decide pipeline runs on NASDAQ data, producing signal output in the same format as v2
**Depends on**: Phase 12
**Requirements**: HYB-03, HYB-04, HYB-05
**Success Criteria** (what must be TRUE):
  1. `HybridEngine.run()` processes daily bars through the complete pipeline: classic proposal, indicator filter evaluation, resolved action, position manager commit
  2. When indicator filter is set to "always confirm" mode, hybrid engine output is identical to v2 engine output (regression baseline locked in tests)
  3. Signal override logic forces state transitions when indicator conditions are sufficiently strong, even without a state machine proposal
  4. Cash state is inserted when indicator degradation is detected (EMA crossover bearish) independent of DD count threshold
  5. `scripts/run_hybrid_backtest.py` entry point runs end-to-end and produces output file with signal log
**Plans:** 2/2 plans complete

Plans:
- [x] 13-01-PLAN.md -- Wire Propose-Filter-Decide pipeline into engine with degrade_to_cash and indicator columns (HYB-03, HYB-04, HYB-05)
- [x] 13-02-PLAN.md -- Integration tests for filter pipeline and hybrid backtest entry point script (HYB-03, HYB-04, HYB-05)

### Phase 14: Hybrid Validation
**Goal**: Hybrid model accuracy is measured against all 962 published signals and compared to the v2 baseline of 56.7%
**Depends on**: Phase 13
**Requirements**: VAL-04
**Success Criteria** (what must be TRUE):
  1. Confusion matrix shows per-type accuracy (Buy/Cash/Sell) for hybrid model on the full 962-signal history
  2. Post-2019 accuracy is reported separately and compared against 56.7% v2 baseline with clear delta
  3. Signal log records "proposed X, filter said Y, final Z" for every trading day, enabling diagnosis of where filter helps or hurts
  4. Held-out test set (19+ post-2019 signals) selected and locked before any filter tuning begins -- tuning results reported on held-out set separately
**Plans:** 1/1 plans complete

Plans:
- [x] 14-01-PLAN.md -- Hybrid validation with confusion matrix, v2 baseline comparison, signal diagnosis, held-out split (VAL-04)

### Phase 15: Advanced Features
**Goal**: Hybrid model enhanced with contextual awareness, additional filters, and comparative analysis tools
**Depends on**: Phase 14
**Requirements**: ADV-01, ADV-02, ADV-03, ADV-04
**Success Criteria** (what must be TRUE):
  1. State transitions consider previous state history (duration in current state, prior state sequence) when applying filter rules
  2. Heikin Ashi Smoothed 55 operates as an additional trend confirmation filter that can be toggled on/off via config
  3. Indicator confidence score (count of agreeing indicators out of total) is computed per day and available in the output DataFrame
  4. Three-way comparison dashboard shows pure state machine vs pure decision tree vs hybrid accuracy side-by-side on a single chart
**Plans:** 3/3 plans complete

Plans:
- [x] 15-01-PLAN.md -- HA Smoothed 55 filter condition + confidence score exposure (ADV-02, ADV-03)
- [x] 15-02-PLAN.md -- Contextual state transitions with state history tracking (ADV-01)
- [x] 15-03-PLAN.md -- Three-way model comparison dashboard (ADV-04)
**UI hint**: yes

</details>

<details>
<summary>v4.0 MDM Short Signal & Dr. K Alignment (Phases 16-18) - SHIPPED 2026-03-30</summary>

- [x] **Phase 16: Short Position & State Transitions** - Short entry on SELL, short cover mechanics, and enforced SELL->CASH->BUY transition (completed 2026-03-30)
- [x] **Phase 17: Stop Loss & Risk Management** - Long stop loss 1.5%, volatility-adaptive adjustment, and short-specific stop loss rules (completed 2026-03-30)
- [x] **Phase 18: Short P&L & Comparative Validation** - Short P&L tracking, long-only vs long/short backtest comparison, and rule docs update (completed 2026-03-30)

### Phase 16: Short Position & State Transitions
**Goal**: SELL signal opens a real short position and the state machine enforces correct SELL->CASH->BUY transition sequence
**Depends on**: Phase 15
**Requirements**: SHORT-01, SHORT-04, TRANS-01
**Success Criteria** (what must be TRUE):
  1. When hybrid engine emits SELL signal, position manager opens a short position on the index (VN30: direct short, NASDAQ: inverse ETF concept) with entry price recorded
  2. Short position is covered (closed) when FTD is detected or price breaks above MA50, transitioning to CASH state
  3. State machine rejects any direct SELL->BUY transition -- a CASH state must always intervene between SELL and BUY
  4. Running the engine on historical NASDAQ data produces a signal log where every BUY signal is preceded by a CASH signal (never directly by SELL)
**Plans**: 2 plans

Plans:
- [x] 16-01-PLAN.md -- V2Position short fields, cover_short(), enter_buy() guard, config short_mode (SHORT-01, SHORT-04, TRANS-01)
- [x] 16-02-PLAN.md -- Engine cover triggers, degrade_to_cash replacement, NASDAQ validation (SHORT-04, TRANS-01)

### Phase 17: Stop Loss & Risk Management
**Goal**: Stop loss rules align with Dr. K's model -- 1.5% default for long, volatility-adaptive scaling, and separate short stop loss logic
**Depends on**: Phase 16
**Requirements**: RISK-01, RISK-02, RISK-03, SHORT-03
**Success Criteria** (what must be TRUE):
  1. Long position stop loss defaults to 1.5% (down from 2.5%) and triggers position exit to CASH when breached
  2. Volatility-adaptive mechanism widens stop loss during high-volatility periods (measured by ATR or similar) and tightens during low-volatility periods
  3. Short stop loss triggers at 1% above DD5 high (the highest high of the last 5 distribution days), matching MDM classic rules
  4. Backtest on NASDAQ shows stop loss triggers at expected points -- spot-checking 5+ known volatile periods confirms adaptive behavior
**Plans**: 2 plans

Plans:
- [x] 17-01-PLAN.md -- Long stop loss 1.5%, ATR indicator, volatility-adaptive scaling (RISK-01, RISK-02)
- [x] 17-02-PLAN.md -- DD5 high tracking, short stop loss check_short(), engine SELL state integration (RISK-03, SHORT-03)

### Phase 18: Short P&L & Comparative Validation
**Goal**: Short position P&L is tracked correctly and backtest proves whether long/short outperforms long-only
**Depends on**: Phase 17
**Requirements**: SHORT-02, TRANS-02, TRANS-03
**Success Criteria** (what must be TRUE):
  1. Short position P&L computes correctly -- gain when market drops from entry, loss when market rises from entry -- verified with manual calculation on 3+ trades
  2. Backtest comparison report shows long-only vs long/short performance side-by-side on NASDAQ with equity curve, max drawdown, Sharpe ratio, and total return
  3. Same comparison report generated for VN30, showing long-only vs long/short performance with VN30-specific parameters
  4. Rule documentation files (rules_mdm_v2.md, rules_mdm_hybrid.md) updated with short signal rules, stop loss changes, and SELL->CASH->BUY transition requirement
**Plans**: 2 plans

Plans:
- [x] 18-01-PLAN.md -- Short P&L in equity curve, long_only_equity flag, comparison script with charts (SHORT-02, TRANS-02)
- [x] 18-02-PLAN.md -- Update rule docs with short signal, stop loss, and transition rules (TRANS-03)
**UI hint**: yes

</details>

<details>
<summary>v5.0 Signal Quality & Macro Filter (Phases 19-22) - SHIPPED 2026-03-31</summary>

- [x] **Phase 19: Global Liquidity Integration** - Load liquidity data, implement QE floor filter suppressing SELL during liquidity expansion (completed 2026-03-30)
- [x] **Phase 20: SELL Acceleration** - Require downside momentum/acceleration before SELL transition, validated on bear markets (completed 2026-03-31)
- [x] **Phase 21: BUY Selectivity** - Reject weak FTD entries and add post-FTD confirmation window to reduce whipsaw (completed 2026-03-31)
- [x] **Phase 22: Combined Integration & Validation** - A/B comparison, walk-forward validation, dashboard update with all filters combined (completed 2026-03-31)

### Phase 19: Global Liquidity Integration
**Goal**: V2 engine can suppress SELL signals during central bank liquidity expansion, implementing Dr. K's confirmed QE floor behavior
**Depends on**: Phase 18
**Requirements**: LIQ-01, LIQ-02, LIQ-03
**Success Criteria** (what must be TRUE):
  1. Global liquidity CSV loads into a daily-aligned DataFrame with forward-filled values and a publication lag offset (minimum 7 days) that prevents look-ahead bias -- verified by unit test confirming no daily row uses liquidity data published after that date
  2. With qe_floor_enabled=True and liquidity expanding, CASH->SELL transitions are suppressed while all other transitions (BUY->CASH stop loss, SELL->CASH cover, etc.) remain unaffected
  3. With qe_floor_enabled=False (default), V2 engine produces identical equity curve to the current baseline (190.8% VN30 total return +/- 0.1%) -- regression test locks this invariant
  4. Pre-2007 dates (before liquidity data exists) handle gracefully with NaN/neutral regime -- no crashes or incorrect signals in the 1974-2007 period
**Plans**: 2 plans

Plans:
- [x] 19-01-PLAN.md -- LiquidityLoader data pipeline and MDMV2Config QE floor fields (LIQ-01, LIQ-03)
- [x] 19-02-PLAN.md -- Engine wiring, SELL suppression gate, and regression tests (LIQ-02, LIQ-03)

### Phase 20: SELL Acceleration
**Goal**: SELL transitions require confirmed downside momentum, preventing premature exits during normal pullbacks
**Depends on**: Phase 19
**Requirements**: SELL-01, SELL-02
**Success Criteria** (what must be TRUE):
  1. SELL transition fires only when at least one acceleration condition is met (price ROC below threshold, DD clustering above threshold, or volume-confirmed MA50 breakdown) -- not on MA50 breakdown or cash deterioration alone
  2. Backtest on 2008 bear market sub-period shows SELL acceleration does not delay the first correct SELL signal by more than 5 trading days vs V2 baseline
  3. Backtest on 2022 bear market sub-period shows max drawdown is not worse than V2 baseline
  4. A/B comparison of V2 vs V2+sell_acceleration in isolation shows performance delta on both NASDAQ and VN30
**Plans**: 2 plans

Plans:
- [x] 20-01-PLAN.md -- SellAccelerationGate module, config fields, engine and position manager wiring (SELL-01)
- [x] 20-02-PLAN.md -- Bear market A/B validation script and rule docs update (SELL-01, SELL-02)

### Phase 21: BUY Selectivity
**Goal**: FTD entries are filtered to reject low-quality setups, reducing whipsaw without missing major rallies
**Depends on**: Phase 20
**Requirements**: BUY-01, BUY-02
**Success Criteria** (what must be TRUE):
  1. FTD signal is rejected when MA10 < MA50 (trend not confirmed) -- verified by checking that rejected FTDs correspond to entries that would have been stopped out within 5 days in the V2 baseline
  2. Post-FTD confirmation window requires N days without a distribution day after FTD before committing to BUY -- early DD triggers immediate exit to CASH
  3. Walk-forward validation (train pre-2020, test 2020-2026) shows BUY selectivity filters degrade less than 10% out-of-sample vs in-sample performance
  4. Trade count reduction from BUY filtering is between 15-40% -- too few rejections means the filter is not working, too many means it is over-fitted
**Plans**: 2 plans

Plans:
- [x] 21-01-PLAN.md -- BuyFilter + BuyConfirmation modules, config fields, engine wiring, unit + integration tests (BUY-01, BUY-02)
- [x] 21-02-PLAN.md -- A/B validation script with walk-forward analysis and rule docs update (BUY-01, BUY-02)

### Phase 22: Combined Integration & Validation
**Goal**: All three filters operate together without conflicting, validated end-to-end with A/B comparison and dashboard update
**Depends on**: Phase 21
**Requirements**: VAL-05, VAL-06, VAL-07
**Success Criteria** (what must be TRUE):
  1. A/B backtest report comparing V2 baseline vs V2+all_filters shows side-by-side metrics (total return, CAGR, max drawdown, Sharpe, trade count) on both NASDAQ and VN30
  2. Walk-forward out-of-sample validation (train pre-2020, test 2020-2026) shows combined filter performance degrades less than 10% from in-sample -- confirming no overfitting
  3. S3 dashboard is updated with new performance metrics, Global Liquidity overlay chart, and signal quality annotations
  4. Average CASH duration with all filters enabled stays below 130% of V2 baseline CASH duration -- filters are not trapping capital
  5. Integration test covers all 8 filter combinations (liquidity x sell_accel x buy_quality on/off) and confirms no combination produces worse max drawdown than V2 baseline on 2008 or 2022 sub-periods
**Plans**: 2 plans

Plans:
- [x] 22-01-PLAN.md -- A/B validation script + walk-forward + CASH duration + 8-combo integration test (VAL-05, VAL-07)
- [x] 22-02-PLAN.md -- Dashboard export extension with V2 filtered model and liquidity overlay + S3 deploy (VAL-06)
**UI hint**: yes

</details>

#### v6.0 MDM Fail-Safe & Signal Refinement (Phases 23-27)

**Milestone Goal:** Implement Dr. K's specific signal rules (fail-safe, gap-up neutralization, 6% threshold) and review MA50/volatility filter role to reduce whipsaw on VN30.

- [x] **Phase 23: Fail-Safe Mechanism** - Auto-exit SELL to CASH when VN30 reclaims standby-sell HIGH, with A/B validation
 (completed 2026-03-31)
- [x] **Phase 24: Buy Entry Refinement** - Gap-up neutralization and 6% rally attempt threshold for FTD timing on VN30
 (completed 2026-03-31)
- [x] **Phase 25: MA50/200dma Review** - A/B research testing whether MA50 should be removed from SELL trigger and BUY filter logic (completed 2026-04-01)
- [x] **Phase 26: Banding/Volatility Filter** - ATR-based volatility regime detection to suppress signals during low-volatility sideways periods (completed 2026-04-01)
- [x] **Phase 27: Combined v6.0 Validation & Dashboard** - End-to-end A/B, walk-forward validation, and S3 dashboard update with all v6.0 features (completed 2026-04-02)

#### v7.0 CANSLIM + MDM on VN100 (Phases 28-34)

**Milestone Goal:** Long-only CANSLIM stock picking on VN100 with MDM as capital allocation gate, max 8 positions, event-driven, stock-level entry confirmation, validated in-sample (2014-2018) and out-of-sample (2019-2025).

- [x] **Phase 28: Data Audit & Connectors** — Postgres/MySQL connectors, audit delisted/adjusted/EPS publish_date, fundamental coverage report
 (completed 2026-04-09)
- [ ] **Phase 29: VN100 Universe + CANSLIM Scorer** — universe loader with semi-annual rebalance, C/A/N/S/L/I rules, sector handling, baseline cross-check
- [ ] **Phase 30: Entry Confirmation** — Option A (52wk high + vol) + Option C (Pocket Pivot), 20-day window from MDM BUY, A/B comparison
- [ ] **Phase 31: Multi-Stock Portfolio Engine** — 8-slot equal-weight engine, stops, exits, cooldowns, costs, T+2 + ceiling/floor lock handling, `state[i-1]` discipline
- [ ] **Phase 32: VN100 Backtest + In-Sample Sweep** — wire engine to data, run 2014-2018 sweep across CANSLIM/entry/stop params
- [ ] **Phase 33: Out-of-Sample + Sensitivity** — locked-param 2019-2025 run, sensitivity across (current VN100, liquidity-reconstructed, VN30-only), comparison vs `diem_canslim` baseline
- [ ] **Phase 34: Reporting + Documentation** — performance dashboard (CAGR/Sharpe/MaxDD/cost drag/benchmarks/real CAGR), `docs/rules_canslim_mdm.md`, milestone retrospective

## Phase Details

### Phase 23: Fail-Safe Mechanism
**Goal**: False SELL signals are automatically detected and exited when VN30 reclaims the standby-sell day HIGH
**Depends on**: Phase 22
**Requirements**: SAFE-01, SAFE-02, SAFE-03
**Success Criteria** (what must be TRUE):
  1. When V2 engine transitions to SELL, the HIGH of the day immediately before the sell signal day is recorded as the fail-safe threshold in engine state
  2. While in SELL state, if VN30 close exceeds the fail-safe threshold, engine auto-transitions to CASH with a "fail-safe triggered" annotation in the signal log
  3. A/B backtest on VN30 shows fail-safe reduces average loss on false SELL trades (trades where SELL was followed by market recovery) compared to V2 baseline
  4. Fail-safe does not trigger during genuine bear markets (2022 VN30 drawdown) -- verified by checking that no fail-safe exit occurs within 10 days of a SELL that precedes a 10%+ decline
**Plans:** 2/2 plans complete

Plans:
- [x] 23-01-PLAN.md -- Fail-safe core logic: config, position state, SELL->CASH transition, unit tests (SAFE-01, SAFE-02)
- [x] 23-02-PLAN.md -- A/B validation script comparing V2 baseline vs V2+fail-safe on VN30 (SAFE-03)

### Phase 24: Buy Entry Refinement
**Goal**: BUY entries on VN30 are refined with gap-up invalidation and decline-severity-aware FTD timing rules from Dr. K's webinar
**Depends on**: Phase 23
**Requirements**: GAP-01, GAP-02, RALLY-01, RALLY-02, RALLY-03
**Success Criteria** (what must be TRUE):
  1. A buy signal is invalidated when the signal day's intraday low is below the previous day's close (gap-up broken) -- verified by identifying 3+ historical VN30 instances where this filter would have prevented a losing trade
  2. When VN30 has declined less than 6% from its recent peak, FTD can trigger on any day (no day-3+ requirement) -- verified by checking that shallow pullback recoveries are captured faster
  3. When VN30 has declined 6% or more from its recent peak, FTD requires classic day-3+ timing -- verified by checking that deep correction entries still wait for proper follow-through
  4. A/B backtest on VN30 comparing V2 baseline vs V2+gap_filter shows gap filter reduces false entry count without significantly reducing total return
  5. A/B backtest on VN30 comparing V2 baseline vs V2+rally_threshold shows the 6% logic improves entry timing (fewer whipsaw trades in shallow pullbacks)
**Plans:** 2/2 plans complete

Plans:
- [x] 24-01-PLAN.md -- BuyEntryFilter module, config, engine integration, unit tests (GAP-01, RALLY-01, RALLY-02)
- [x] 24-02-PLAN.md -- A/B validation script and rules documentation update (GAP-02, RALLY-03)

### Phase 25: MA50/200dma Review
**Goal**: Evidence-based decision on whether MA50 should remain in V2 signal logic, based on Dr. K's statement that MA50/200dma have "little value"
**Depends on**: Phase 24
**Requirements**: MAREVIEW-01, MAREVIEW-02, MAREVIEW-03
**Success Criteria** (what must be TRUE):
  1. A/B backtest on VN30 shows performance delta (total return, max drawdown, Sharpe) between V2 with MA50 breakdown as SELL trigger vs V2 without it
  2. A/B backtest on VN30 shows performance delta between V2 with MA50 in BUY filter logic vs V2 without it
  3. A written report recommends one of three actions (keep MA50, remove MA50, replace MA50 with alternative) with quantitative evidence from the backtests
  4. If MA50 is recommended for removal, the report identifies what (if anything) replaces its role in the signal logic
**Plans:** 3/3 plans complete

Plans:
- [x] 25-01-PLAN.md -- Config flags (ma50_breakout_enabled, ma200_enabled), sma200 indicator, test scaffolding (MAREVIEW-01, MAREVIEW-02)
- [x] 25-02-PLAN.md -- Engine wiring: gate MA50 breakout, 200dma crossover buy, 200dma SELL trigger (MAREVIEW-01, MAREVIEW-02)
- [x] 25-03-PLAN.md -- 5-scenario A/B validation script and rules documentation update (MAREVIEW-01, MAREVIEW-02, MAREVIEW-03)

### Phase 26: Banding/Volatility Filter
**Goal**: V2 engine suppresses signal switching during low-volatility sideways periods on VN30, implementing Dr. K's "banding width" concept
**Depends on**: Phase 25
**Requirements**: BAND-01, BAND-02, BAND-03
**Success Criteria** (what must be TRUE):
  1. ATR-based volatility regime classifier labels each VN30 trading day as high/normal/low volatility, with regime boundaries calibrated to VN30's historical ATR distribution
  2. When volatility regime is "low", signal transitions (both BUY and SELL) are suppressed -- engine stays in current state until volatility returns to normal/high
  3. A/B backtest on VN30 sideways periods (identified by ATR regime) shows the volatility filter reduces false signal count by at least 20% during those periods
  4. The filter does not delay entries or exits during high-volatility trending periods -- verified by checking that 2020 crash exit and 2021 rally entry timing are unchanged
**Plans:** 2/2 plans complete

Plans:
- [x] 26-01-PLAN.md -- Config, ATR indicator, VolatilityFilter module with unit tests (BAND-01, BAND-02)
- [x] 26-02-PLAN.md -- Engine/position manager integration, A/B validation, docs update (BAND-02, BAND-03)

### Phase 27: Combined v6.0 Validation & Dashboard
**Goal**: All v6.0 features validated together with walk-forward testing and dashboard updated with new performance metrics
**Depends on**: Phase 26
**Requirements**: VAL-08, VAL-09, VAL-10
**Success Criteria** (what must be TRUE):
  1. A/B backtest report comparing V2 baseline vs V2+all_v6_features shows side-by-side metrics (total return, CAGR, max drawdown, Sharpe, trade count, false signal rate) on VN30
  2. Walk-forward validation (train pre-2022, test 2022-2026) shows combined v6.0 features degrade less than 10% out-of-sample vs in-sample on VN30
  3. S3 dashboard is updated with v6.0 performance metrics, fail-safe annotations, volatility regime overlay, and updated equity curve
**Plans**: TBD
**UI hint**: yes

### Phase 28: Data Audit & Connectors
**Goal**: Postgres + MySQL connectors are usable from Python; data quality risks for VN100 backtest are quantified
**Depends on**: Phase 27
**Requirements**: DATA-01..DATA-07
**Success Criteria:**
  1. `connectors/postgres.py` and `connectors/mysql.py` modules load credentials from `.env`, expose typed query helpers, integration test queries `stock_eod` and `ratios_stock` successfully
  2. Audit report enumerates: count of distinct stockcodes in `stock_eod`, count whose `max(tradingdate) < 2024-01-01` (delisted candidates), confirmed list of known delistings (FLC, ROS, HVN, …) present or absent
  3. Price-adjustment convention documented (whether `closeprice` reflects splits/divs/rights); if unadjusted, helper produces adjusted series
  4. EPS publish_date sourced or imputed (`+45d` Q1-Q3, `+90d` Q4/annual) with documented assumption
  5. Per-stock fundamental coverage report for current VN100 back to 2014: which tickers have full quarterly EPS history vs gaps
  6. `stock_foreign_eod` daily VN100 coverage 2014-2026 confirmed
**Plans:** 6/6 plans complete

Plans:
- [x] 28-00-SETUP-PLAN.md -- Wave 0 scaffolding: deps, connectors package, tests, docs/audits dir
- [x] 28-01-POSTGRES-CONNECTOR-PLAN.md -- connectors/postgres.py with get_engine/query/load_stock_eod/load_ratios + tests (DATA-01)
- [x] 28-02-MYSQL-CONNECTOR-PLAN.md -- connectors/mysql.py mirror + sector router + tests (DATA-02)
- [x] 28-03-PRICE-ADJUSTMENT-PLAN.md -- adjust_ohlc helper + spot-check script + convention doc (DATA-03)
- [x] 28-04-EPS-PUBLISH-DATE-PLAN.md -- resolve_eps_publish_date helper + 10 unit tests (DATA-04)
- [x] 28-05-DATA-AUDIT-REPORT-PLAN.md -- run_phase28_audit.py + Markdown report + 4 CSVs (DATA-05/06/07)
**UI hint**: no

### Phase 29: VN100 Universe + CANSLIM Scorer
**Goal**: Daily CANSLIM rank for the VN100 universe is computable, configurable, and validated against project's existing baseline
**Depends on**: Phase 28
**Requirements**: UNIV-01..UNIV-03, CANS-01..CANS-12
**Success Criteria:**
  1. VN100 universe loader returns ticker set per date with semi-annual rebalance (Jan/Jul); proxy fallback documented if HOSE membership unavailable
  2. Three universe modes selectable: current-VN100, liquidity-reconstructed (top-100 by 60d ADV), VN30-only
  3. CANSLIM scorer computes C/C+/A/A+/N/S/L/I/Liquidity per stock per day; respects EPS publish_date guard (no look-ahead)
  4. Sector handling — non-financials use C/A directly; banks substitute PPOP growth; CTCK/Insurance excluded
  5. `CanslimConfig` dataclass with all thresholds (defaults: C≥0.20, A≥0.15, N within 15%, S≥1.5×, L≥80, I 20d>0)
  6. Spot-check: top-10 CANSLIM stocks on N recent dates qualitatively overlap with `rank_top_stocks.diem_canslim` top-10 (≥4/10 overlap acceptable; document discrepancies)
  7. RS rating uses formula `0.4*ROC(63)+0.2*ROC(126)+0.2*ROC(189)+0.2*ROC(252)`, percentile-ranked within active universe
**Plans:** 7/9 plans executed

Plans:
- [x] 29-01-PLAN.md -- Wave 0 scaffold: package skeleton, test stubs, live-schema introspection, docs stub
- [x] 29-02-PLAN.md -- CanslimConfig dataclass with defaults + validation (CANS-11)
- [x] 29-03-PLAN.md -- UniverseLoader: 3 modes + Jan/Jul rebalance (UNIV-01..03)
- [x] 29-04-PLAN.md -- SectorRouter: bank/ctck/insurance/other fail-loud (CANS-10)
- [x] 29-05-PLAN.md -- Fundamental rules C/C+/A/A+ with sector branching + publish_date guard (CANS-01..04)
- [x] 29-06-PLAN.md -- Technical N rule + RS rating with universe percentile (CANS-05, CANS-07)
- [x] 29-07-PLAN.md -- Flow I (pre-2022 fallback) + Liquidity 20d median turnover (CANS-06, CANS-08, CANS-09)
- [ ] 29-08-PLAN.md -- CanslimScorer end-to-end wiring with locked composite formula (CANS-11)
- [ ] 29-09-PLAN.md -- Baseline comparison vs rank_top_stocks.diem_canslim + validation report (CANS-12)
**UI hint**: no

### Phase 30: Stock-Level Entry Confirmation
**Goal**: A candidate stock is bought only after a stock-level confirmation signal fires within 20 trading days of an MDM BUY event
**Depends on**: Phase 29
**Requirements**: ENTRY-01..ENTRY-05
**Success Criteria:**
  1. Option A detector — `close > max(close,252) AND vol ≥1.5*avgvol50 AND close>open AND close in upper half of day's range`
  2. Option C (Pocket Pivot) detector — `close>open AND close≥MA50 AND vol > max(down-day vols last 10d) AND within 15% of 50d high`
  3. Entry timing window — confirmation only counts if MDM is in BUY state AND it's been ≤20 trading days since most recent CASH/SELL→BUY transition
  4. Entry execution model — fill price = next-day open (ATO), not signal-bar close
  5. A/B helper produces side-by-side fill counts for Option A vs Option C on VN100 over 2014-2025
**Plans**: TBD
**UI hint**: no

### Phase 31: Multi-Stock Portfolio Engine
**Goal**: A long-only multi-stock state machine with stops, exits, costs, and Vietnam microstructure correctly processes a daily bar sequence without look-ahead
**Depends on**: Phase 30
**Requirements**: GATE-01..GATE-04, PORT-01..PORT-10
**Success Criteria:**
  1. Engine holds up to 8 concurrent positions; equal-weight (12.5%/slot); 100-share lot rounding (down)
  2. MDM gate Policy A enforced: BUY allows new entries up to 8; CASH holds existing, no new; SELL liquidates all next open
  3. Exit priority chain firing in order: MDM SELL > 8% hard stop > MA50 trailing break (vol confirm 1.25×) > RS<70 for 5 sessions
  4. Vietnam microstructure handled: T+2 settlement (no sell <2d after buy), 7% ceiling lock blocks new fills, 7% floor lock defers exit to next open
  5. Re-entry cooldown 5 days per ticker after stop
  6. Costs applied both sides: 0.25% commission + 0.10% sell tax + 0.10% slippage
  7. Liquidity gate: refuse entry if 20d ADV < 10× position size
  8. Equity curve uses `state[i-1]` discipline; unit test asserts no `state[i]` look-ahead in NAV computation
**Plans**: TBD
**UI hint**: no

### Phase 32: VN100 Backtest + In-Sample Sweep
**Goal**: A wired pipeline (universe→CANSLIM→entry→portfolio→costs) runs end-to-end on VN100 2014-2018 and an in-sample sweep selects parameters
**Depends on**: Phase 31
**Requirements**: BT-01, BT-02
**Success Criteria:**
  1. Single-run backtest over VN100 2014-2018 produces trade log, position log, daily NAV without errors
  2. Sweep grid run over: c_yoy ∈ {0.10,0.15,0.20,0.25}, a_cagr ∈ {0.10,0.15,0.20,0.25}, n_proximity ∈ {0.05,0.10,0.15,0.20}, hard_stop ∈ {0.06,0.07,0.08,0.10}, slots ∈ {5,8,10}, entry_option ∈ {A,C}
  3. Sweep results CSV with per-config (CAGR, Sharpe, MaxDD, hit rate, turnover, total cost drag)
  4. Top-3 configs identified by Sharpe and locked for OOS
  5. Sanity: no config produces >300% CAGR (sign of look-ahead); equity curves visually plausible
**Plans**: TBD
**UI hint**: no

### Phase 33: Out-of-Sample + Sensitivity
**Goal**: Locked-parameter strategy is validated on untouched 2019-2025 data and across universe/period sensitivities
**Depends on**: Phase 32
**Requirements**: BT-03, BT-04, BT-08
**Success Criteria:**
  1. OOS run 2019-2025 with locked parameters from Phase 32; performance metrics computed
  2. Sensitivity matrix: 3 universes × 1 locked config + 1 baseline (CANSLIM-only no MDM gate) + 1 baseline (MDM-only-on-index)
  3. Comparison vs `rank_top_stocks.diem_canslim` baseline ranking strategy on same period
  4. Pass/fail vs targets: Sharpe uplift > 0.20 vs VN-Index B&H, MaxDD reduction > 30% vs VN-Index B&H
  5. If targets fail, written analysis identifies which component (CANSLIM/entry/MDM/costs) is responsible
**Plans**: TBD
**UI hint**: yes

### Phase 34: Reporting + Documentation + Retrospective
**Goal**: v7.0 milestone is shippable: dashboard updated, rules documented, retrospective filed
**Depends on**: Phase 33
**Requirements**: BT-05, BT-06, BT-07, DOC-01, DOC-02
**Success Criteria:**
  1. Performance report: nominal CAGR, Sharpe (rf=10Y VN govt 3%), MaxDD + duration, hit rate, profit factor, hold time, turnover, cost drag
  2. Benchmark table: vs VN-Index B&H, VN30 B&H, MDM-only-on-index, 12M deposit, SJC gold
  3. Real (CPI-adjusted) CAGR alongside nominal
  4. `docs/rules_canslim_mdm.md` documents locked CANSLIM rules, entry options, portfolio policies, MDM gate, costs — kept in sync with code
  5. Data dictionary for connectors and CANSLIM scorer
  6. Retrospective entry added in `.planning/RETROSPECTIVE.md`
  7. PROJECT.md, MILESTONES.md, STATE.md updated for v7.0 ship
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 23 -> 24 -> 25 -> 26 -> 27

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Integrity | v1.0 | 2/2 | Complete | 2026-03-27 |
| 2. Codebase Organization | v1.0 | 4/4 | Complete | 2026-03-27 |
| 3. Signal Divergence Analysis | v1.0 | 2/2 | Complete | 2026-03-27 |
| 4. MDM v2 Engine | v1.0 | 2/2 | Complete | 2026-03-28 |
| 5. Validation & Performance | v1.0 | 2/2 | Complete | 2026-03-28 |
| 6. VN30 Adaptation | v1.0 | 3/3 | Complete | 2026-03-28 |
| 7. Data Foundation | v2.0 | 2/2 | Complete | 2026-03-29 |
| 8. Indicator Engine | v2.0 | 2/2 | Complete | 2026-03-29 |
| 9. Rule Discovery | v2.0 | 2/2 | Complete | 2026-03-29 |
| 10. Discovery Validation | v2.0 | 2/2 | Complete | 2026-03-29 |
| 11. Foundation & Two-Phase Commit | v3.0 | 1/1 | Complete | 2026-03-29 |
| 12. Indicator Filter Layer | v3.0 | 1/1 | Complete | 2026-03-29 |
| 13. Hybrid Engine Integration | v3.0 | 2/2 | Complete | 2026-03-29 |
| 14. Hybrid Validation | v3.0 | 1/1 | Complete | 2026-03-29 |
| 15. Advanced Features | v3.0 | 3/3 | Complete | 2026-03-29 |
| 16. Short Position & State Transitions | v4.0 | 2/2 | Complete | 2026-03-30 |
| 17. Stop Loss & Risk Management | v4.0 | 2/2 | Complete | 2026-03-30 |
| 18. Short P&L & Comparative Validation | v4.0 | 2/2 | Complete | 2026-03-30 |
| 19. Global Liquidity Integration | v5.0 | 2/2 | Complete | 2026-03-30 |
| 20. SELL Acceleration | v5.0 | 2/2 | Complete | 2026-03-31 |
| 21. BUY Selectivity | v5.0 | 2/2 | Complete | 2026-03-31 |
| 22. Combined Integration & Validation | v5.0 | 2/2 | Complete | 2026-03-31 |
| 23. Fail-Safe Mechanism | v6.0 | 2/2 | Complete    | 2026-03-31 |
| 24. Buy Entry Refinement | v6.0 | 2/2 | Complete    | 2026-03-31 |
| 25. MA50/200dma Review | v6.0 | 3/3 | Complete    | 2026-04-01 |
| 26. Banding/Volatility Filter | v6.0 | 2/2 | Complete    | 2026-04-01 |
| 27. Combined v6.0 Validation & Dashboard | v6.0 | 0/0 | Complete    | 2026-04-02 |
| 28. Data Audit & Connectors | v7.0 | 6/6 | Complete    | 2026-04-09 |
| 29. VN100 Universe + CANSLIM Scorer | v7.0 | 7/9 | In Progress|  |
| 30. Stock-Level Entry Confirmation | v7.0 | 0/0 | Pending | — |
| 31. Multi-Stock Portfolio Engine | v7.0 | 0/0 | Pending | — |
| 32. VN100 Backtest + In-Sample Sweep | v7.0 | 0/0 | Pending | — |
| 33. Out-of-Sample + Sensitivity | v7.0 | 0/0 | Pending | — |
| 34. Reporting + Documentation | v7.0 | 0/0 | Pending | — |
