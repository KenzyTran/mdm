# Roadmap: MDM Reverse-Engineering & VN30 Market Timing

## Milestones

- [x] **v1.0 MDM Classic & VN30** - Phases 1-6 (shipped 2026-03-28)
- [ ] **v2.0 MDM Rule Discovery** - Phases 7-10 (in progress)

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
**Plans:** 2/2 plans complete

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

### v2.0 MDM Rule Discovery

**Milestone Goal:** Reverse-engineer Dr. K's MDM decision rules using 962 published signals and multi-indicator feature engineering (EMA 9/21/55, MA 200, MACD 12-26-9, Heikin Ashi Smoothed).

- [ ] **Phase 7: Data Foundation** - Full NASDAQ OHLCV from 1974+ and 962-signal history loaded as ground truth
- [ ] **Phase 8: Indicator Engine** - Multi-indicator feature engineering with feature snapshots at every signal date
- [ ] **Phase 9: Rule Discovery** - Statistical analysis and decision tree extraction of indicator-based signal rules
- [ ] **Phase 10: Discovery Validation** - Match rate scoring, train/test split, and visual comparison of discovered rules

## Phase Details

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
**Plans:** 0/2 plans executed

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
  3. Human-readable rules are extracted from the decision tree with confidence scores (e.g., "Buy when EMA9 > EMA21 AND MACD histogram > 0: 78% confidence")
  4. Era comparison shows quantifiable differences in rule patterns pre-2019 vs post-2019, confirming or refining the structural change hypothesis
**Plans:** 1/2 plans executed

Plans:
- [x] 09-01-PLAN.md -- Dependency setup, test scaffold, and era-aware statistical profiling (DISC-01, DISC-04)
- [ ] 09-02-PLAN.md -- Decision tree training, rule extraction, and full report generation (DISC-02, DISC-03, DISC-04)

### Phase 10: Discovery Validation
**Goal**: Discovered rules are validated against the full signal history and presented alongside published signals for visual confirmation
**Depends on**: Phase 9
**Requirements**: VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. Match rate report scores discovered rules against all 962 signals with per-type breakdown (Buy/Sell/Cash match rates separately)
  2. Train/test validation shows rules trained on pre-2019 data achieve acceptable match rate on post-2019 held-out period (and vice versa)
  3. Comparison dashboard overlays discovered-rule signals and published signals on NASDAQ price chart, making agreement and divergence visually apparent
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 7 -> 8 -> 9 -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Integrity | v1.0 | 2/2 | Complete | 2026-03-27 |
| 2. Codebase Organization | v1.0 | 4/4 | Complete | 2026-03-27 |
| 3. Signal Divergence Analysis | v1.0 | 2/2 | Complete | 2026-03-27 |
| 4. MDM v2 Engine | v1.0 | 2/2 | Complete | 2026-03-28 |
| 5. Validation & Performance | v1.0 | 2/2 | Complete | 2026-03-28 |
| 6. VN30 Adaptation | v1.0 | 3/3 | Complete | 2026-03-28 |
| 7. Data Foundation | v2.0 | 0/2 | Not started | - |
| 8. Indicator Engine | v2.0 | 0/2 | Planned    |  |
| 9. Rule Discovery | v2.0 | 1/2 | In Progress|  |
| 10. Discovery Validation | v2.0 | 0/? | Not started | - |
