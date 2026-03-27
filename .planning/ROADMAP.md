# Roadmap: MDM Reverse-Engineering & VN30 Market Timing

## Overview

This roadmap takes the project from its current state (working but duplicated MDM classic and VSA implementations) to a validated reverse-engineered MDM v2 model adapted for VN30. The journey follows a strict dependency chain: correct data first, then organized code, then measurement infrastructure, then rule discovery, then validation, and finally VN30 adaptation. Each phase delivers a complete, verifiable capability that the next phase depends on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Integrity** - Unified data loading with proven normalization and published signal fixtures
- [ ] **Phase 2: Codebase Organization** - Three-layer architecture with migrated strategies and verified identical output
- [ ] **Phase 3: Signal Divergence Analysis** - Comparison engine and divergence report identifying where classic rules fail post-2019
- [ ] **Phase 4: MDM v2 Engine** - Cash state machine, parameterized rules, and systematic hypothesis testing
- [ ] **Phase 5: Validation & Performance** - Held-out validation, performance metrics, and visual analysis tools
- [ ] **Phase 6: VN30 Adaptation** - MDM v2 recalibrated for Vietnamese market microstructure

## Phase Details

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
- [ ] 01-01-PLAN.md -- Unified DataLoader with normalization and spot-check validation (DATA-01, DATA-02, DATA-03)
- [ ] 01-02-PLAN.md -- Signal fixture loader and TECL/NASDAQ published signal CSV files (DATA-04)

### Phase 2: Codebase Organization
**Goal**: Existing code is reorganized into a clean three-layer architecture with zero regression in backtest output
**Depends on**: Phase 1
**Requirements**: ORG-01, ORG-02, ORG-03, ORG-04
**Success Criteria** (what must be TRUE):
  1. Project follows core/ (shared infrastructure), strategies/ (signal logic), analysis/ (tools) architecture with no cross-strategy imports
  2. MDM classic strategy runs from strategies/mdm_classic/ and produces identical backtest output to the original models/ implementation
  3. VSA strategy runs from strategies/vsa/ and produces identical backtest output to the original vn30_vsa/ implementation
  4. A regression test suite confirms bit-for-bit identical signal sequences and equity curves before and after migration
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

### Phase 3: Signal Divergence Analysis
**Goal**: The project can measure exactly where and how classic MDM rules diverge from Dr. K's published post-2019 signals
**Depends on**: Phase 2
**Requirements**: SIG-01, SIG-02, SIG-03, SIG-04
**Success Criteria** (what must be TRUE):
  1. Signal comparison engine scores model-generated signals against published signals with match rate, timing offset, and per-signal type breakdown
  2. MDM classic rules running on NASDAQ data produce a complete Buy/Sell/Cash signal list for the full 2017-2026 period
  3. Divergence report lists every date where classic output differs from published post-2019 signals, classified by type (threshold, timing, structural, irreproducible)
  4. Visual overlay chart shows NASDAQ price with both model signals and published signals plotted, making divergence patterns visually apparent
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD
- [ ] 03-03: TBD

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
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Validation & Performance
**Goal**: MDM v2 rules are validated on held-out data and backed by full performance analysis
**Depends on**: Phase 4
**Requirements**: PERF-01, PERF-02, PERF-03
**Success Criteria** (what must be TRUE):
  1. Backtest report shows equity curve, max drawdown, Sharpe ratio, and win rate for MDM v2 on NASDAQ
  2. Performance comparison table shows MDM v2 vs buy-and-hold NASDAQ over the same period
  3. Held-out validation (2023-2026 signals) confirms match rate does not degrade significantly compared to training set (2017-2022)
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

### Phase 6: VN30 Adaptation
**Goal**: MDM v2 is recalibrated for VN30 market characteristics and produces actionable backtest results
**Depends on**: Phase 5
**Requirements**: VN30-01, VN30-02, VN30-03
**Success Criteria** (what must be TRUE):
  1. Market microstructure filters handle VN30 7% daily price limit days, T+2.5 settlement constraints, and derivative expiry effects
  2. MDM v2 parameters are recalibrated for VN30 (different volatility, volume characteristics, index composition)
  3. Full VN30 backtest report with equity curve, drawdown, Sharpe, and win rate is generated and compared against VN30 buy-and-hold
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Integrity | 0/2 | Planning complete | - |
| 2. Codebase Organization | 0/3 | Not started | - |
| 3. Signal Divergence Analysis | 0/3 | Not started | - |
| 4. MDM v2 Engine | 0/3 | Not started | - |
| 5. Validation & Performance | 0/3 | Not started | - |
| 6. VN30 Adaptation | 0/3 | Not started | - |
