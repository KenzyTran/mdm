# Requirements: MDM Reverse-Engineering & VN30 Market Timing

**Defined:** 2026-03-27
**Core Value:** Accurately reverse-engineer the post-2019 MDM logic so that backtested signals match Dr. K's published signal history

## v1 Requirements

### Data Infrastructure

- [x] **DATA-01**: Unified data loader reads NASDAQ, S&P500, VN30 CSV files into normalized OHLCV DataFrames
- [x] **DATA-02**: US market data prices normalized correctly (scaled ~1000x in source CSV)
- [x] **DATA-03**: Data validation spot-checks normalized prices against known index values (within 0.1%)
- [x] **DATA-04**: Published signal parser converts Dr. K's TECL and NASDAQ signal history into structured test fixtures

### Codebase Organization

- [x] **ORG-01**: Three-layer architecture implemented (core/ shared infrastructure, strategies/ signal logic, analysis/ tools)
- [x] **ORG-02**: Existing MDM classic migrated from models/ to strategies/mdm_classic/
- [x] **ORG-03**: Existing VSA migrated from vn30_vsa/ to strategies/vsa/
- [x] **ORG-04**: Backtest output identical before and after migration (regression test)

### Signal Analysis

- [x] **SIG-01**: Signal comparison engine scores model-generated signals against published signal history
- [x] **SIG-02**: MDM classic rules run on NASDAQ data and produce Buy/Sell/Cash signal list
- [x] **SIG-03**: Divergence report identifies dates, signal types, and durations where classic rules differ from published post-2019 signals
- [x] **SIG-04**: Visual signal overlay shows price chart with model signals and published signals side by side

### MDM v2 Engine

- [x] **MDM-01**: Cash implemented as intermediate state between Buy and Sell in state machine
- [x] **MDM-02**: Parameterized rule engine with configurable thresholds (FTD %, DD %, MA periods, DD count, etc.)
- [x] **MDM-03**: Hypothesis testing framework allows systematic rule modification and match-rate scoring
- [x] **MDM-04**: Parameter sweep searches over rule parameter space to maximize signal match rate

### Backtesting & Performance

- [x] **PERF-01**: Backtest produces equity curve, max drawdown, Sharpe ratio, win rate
- [x] **PERF-02**: Performance compared against buy-and-hold baseline
- [x] **PERF-03**: Train/test split validation (train on pre-2022, validate on 2022-2026)

### VN30 Adaptation

- [x] **VN30-01**: Market microstructure adjustments for 7% daily price limit, T+2.5 settlement, derivative expiry filtering
- [ ] **VN30-02**: MDM v2 parameters recalibrated for VN30 market characteristics
- [ ] **VN30-03**: Full VN30 backtest with performance report and comparison vs buy-and-hold

## v2 Requirements

### Advanced Analysis

- **ADV-01**: Trade-by-trade attribution explaining which rules triggered each signal
- **ADV-02**: Regime detection classifying market periods (trending, ranging, volatile)
- **ADV-03**: Multi-timeframe analysis cross-referencing daily signals with weekly trend
- **ADV-04**: Signal confidence scoring based on condition strength

### Extended Markets

- **EXT-01**: Rolling window validation with expanding train window
- **EXT-02**: Interactive analysis Jupyter notebooks
- **EXT-03**: Breadth indicator filter for VN30 (advance/decline check)

## Out of Scope

| Feature | Reason |
|---------|--------|
| ML/genetic programming for rule discovery | Model is rule-based; ~100 signals guarantees overfitting |
| Real-time trading or live signals | Research/backtesting only |
| Web dashboard or mobile app | CLI/notebook analysis sufficient |
| Automated data scraping | Explicit project boundary |
| Options/derivatives strategies | Beyond basic long/short/cash |
| Intraday tick data analysis | MDM operates on daily bars |
| Exact model replication | Approximation from public data; proprietary knowledge unavailable |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| ORG-01 | Phase 2 | Complete |
| ORG-02 | Phase 2 | Complete |
| ORG-03 | Phase 2 | Complete |
| ORG-04 | Phase 2 | Complete |
| SIG-01 | Phase 3 | Complete |
| SIG-02 | Phase 3 | Complete |
| SIG-03 | Phase 3 | Complete |
| SIG-04 | Phase 3 | Complete |
| MDM-01 | Phase 4 | Complete |
| MDM-02 | Phase 4 | Complete |
| MDM-03 | Phase 4 | Complete |
| MDM-04 | Phase 4 | Complete |
| PERF-01 | Phase 5 | Complete |
| PERF-02 | Phase 5 | Complete |
| PERF-03 | Phase 5 | Complete |
| VN30-01 | Phase 6 | Complete |
| VN30-02 | Phase 6 | Pending |
| VN30-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-27 after initial definition*
