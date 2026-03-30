# Requirements: MDM Reverse-Engineering & VN30 Market Timing

**Defined:** 2026-03-27 (v1-v3), 2026-03-30 (v4)
**Core Value:** Discover the actual indicator-based rules driving Dr. K's MDM signals

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
- [x] **VN30-02**: MDM v2 parameters recalibrated for VN30 market characteristics
- [x] **VN30-03**: Full VN30 backtest with performance report and comparison vs buy-and-hold

## v2.0 Requirements

### Data Infrastructure (Extended)

- [x] **DATA-05**: Full NASDAQ OHLCV data available from 1974+ for indicator computation across entire signal history
- [x] **DATA-06**: Full signal history loader parses 962 signals (1974-2026) from nasdaq_signals_full.csv with date, signal type, gain/loss, dollar-becomes columns

### Indicator Engine

- [x] **IND-01**: EMA 9, EMA 21, EMA 55 computed on daily NASDAQ close prices
- [x] **IND-02**: MA 200 (simple) computed on daily NASDAQ close prices
- [x] **IND-03**: MACD (12, 26, 9) with signal line and histogram computed on daily close
- [x] **IND-04**: Heikin Ashi Smoothed candles computed from OHLC data
- [x] **IND-05**: Feature snapshot extracted at each signal date: all indicator values, crossover states, price-vs-MA relationships

### Rule Discovery

- [x] **DISC-01**: Statistical profile of indicator conditions at each signal type (Buy/Sell/Cash) showing frequency distributions
- [x] **DISC-02**: Decision tree model trained on indicator features to classify signal transitions
- [x] **DISC-03**: Extracted human-readable rules from decision tree with confidence scores
- [x] **DISC-04**: Era-aware analysis comparing pre-2019 vs post-2019 rule patterns to identify structural changes

### Validation (Extended)

- [x] **VAL-01**: Match rate scoring of discovered rules against full 962-signal history with per-type breakdown
- [x] **VAL-02**: Train/test validation with configurable split point (default: pre-2019 train, post-2019 test)
- [x] **VAL-03**: Comparison dashboard showing discovered rules' signals vs published signals on price chart

## v3.0 Requirements

### Hybrid Engine

- [x] **HYB-01**: State machine layer tái sử dụng v2 logic (DD counting, FTD detection, Rally Attempts) làm tầng đề xuất signal
- [x] **HYB-02**: Indicator filter layer dùng EMA 9/21/55, MACD, MA 200 để xác nhận hoặc veto signal từ state machine
- [x] **HYB-03**: Signal confirmation logic — state machine đề xuất, indicator filter xác nhận/chặn dựa trên điều kiện boolean
- [x] **HYB-04**: Signal override logic — indicators có thể ghi đè signal khi điều kiện đủ mạnh
- [x] **HYB-05**: Cash state insertion dựa trên indicator degradation (post-2019 logic)
- [x] **HYB-06**: Two-phase commit cho state machine — không mutate state trước khi filter xác nhận

### Advanced Features

- [x] **ADV-01**: Contextual state transitions — chuyển trạng thái phụ thuộc lịch sử trạng thái trước đó
- [x] **ADV-02**: Heikin Ashi Smoothed 55 làm bộ lọc trend confirmation bổ sung
- [x] **ADV-03**: Indicator confidence scoring — đếm số indicators đồng thuận, tạo điểm tự tin
- [ ] **ADV-04**: Three-way comparison dashboard — pure state machine vs pure decision tree vs hybrid

### Validation

- [x] **VAL-04**: Validate hybrid model trên toàn bộ 962 published signals với confusion matrix và per-type accuracy

## v4.0 Requirements

### Short Signal

- [x] **SHORT-01**: SELL signal mở vị thế short trên chỉ số (VN30: short trực tiếp, NASDAQ: inverse ETF concept)
- [ ] **SHORT-02**: P&L tracking cho vị thế short — gain khi market giảm, loss khi market tăng
- [ ] **SHORT-03**: Short stop loss — cắt lỗ khi giá vượt ngưỡng từ giá short entry (Dr. K: 1% trên DD5 high)
- [x] **SHORT-04**: Short cover — đóng vị thế short khi có FTD hoặc MA50 breakout (chuyển về CASH)

### Stop Loss & Risk

- [x] **RISK-01**: Stop loss mặc định 1.5% cho vị thế long (thay vì 2.5% hiện tại)
- [x] **RISK-02**: Volatility-adaptive stop loss — stop loss rộng hơn khi market volatile
- [ ] **RISK-03**: Short stop loss riêng biệt — 1% trên DD5 high (từ MDM classic rules)

### Transition & Validation

- [x] **TRANS-01**: Enforce SELL→CASH→BUY — không cho phép chuyển trực tiếp SELL→BUY
- [ ] **TRANS-02**: Backtest comparison long-only vs long/short trên NASDAQ và VN30
- [ ] **TRANS-03**: Cập nhật rule docs (rules_mdm_v2.md, rules_mdm_hybrid.md) với quy tắc short mới

## Future Requirements

### Deferred from v3.0

- **FUT-01**: Era-aware evaluation riêng pre/post 2019
- **FUT-02**: Configurable/parameterized rules cho parameter sweep
- **FUT-03**: Cooldown/anti-whipsaw logic

### Extended Markets

- **EXT-01**: Rolling window validation with expanding train window
- **EXT-02**: Interactive analysis Jupyter notebooks for rule exploration
- **EXT-03**: Breadth indicator filter for VN30 (advance/decline check)
- **EXT-04**: Apply discovered NASDAQ rules to VN30 with recalibration

## Out of Scope

| Feature | Reason |
|---------|--------|
| ML ensemble (XGBoost, Random Forest) | 95 post-2019 signals quá ít, sẽ overfit |
| Continuous indicator values | Boolean features tổng quát hóa tốt hơn qua các era |
| Sentiment/macro indicators | Không nằm trong indicator set đã biết của Dr. K |
| Per-stock signals | MDM là market-level model |
| Neural network / deep learning models | MDM is rule-based; interpretability required |
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
| VN30-02 | Phase 6 | Complete |
| VN30-03 | Phase 6 | Complete |
| DATA-05 | Phase 7 | Complete |
| DATA-06 | Phase 7 | Complete |
| IND-01 | Phase 8 | Complete |
| IND-02 | Phase 8 | Complete |
| IND-03 | Phase 8 | Complete |
| IND-04 | Phase 8 | Complete |
| IND-05 | Phase 8 | Complete |
| DISC-01 | Phase 9 | Complete |
| DISC-02 | Phase 9 | Complete |
| DISC-03 | Phase 9 | Complete |
| DISC-04 | Phase 9 | Complete |
| VAL-01 | Phase 10 | Complete |
| VAL-02 | Phase 10 | Complete |
| VAL-03 | Phase 10 | Complete |
| HYB-01 | Phase 11 | Complete |
| HYB-06 | Phase 11 | Complete |
| HYB-02 | Phase 12 | Complete |
| HYB-03 | Phase 13 | Complete |
| HYB-04 | Phase 13 | Complete |
| HYB-05 | Phase 13 | Complete |
| VAL-04 | Phase 14 | Complete |
| ADV-01 | Phase 15 | Complete |
| ADV-02 | Phase 15 | Complete |
| ADV-03 | Phase 15 | Complete |
| ADV-04 | Phase 15 | Pending |
| SHORT-01 | Phase 16 | Complete |
| SHORT-04 | Phase 16 | Complete |
| TRANS-01 | Phase 16 | Complete |
| RISK-01 | Phase 17 | Complete |
| RISK-02 | Phase 17 | Complete |
| RISK-03 | Phase 17 | Pending |
| SHORT-03 | Phase 17 | Pending |
| SHORT-02 | Phase 18 | Pending |
| TRANS-02 | Phase 18 | Pending |
| TRANS-03 | Phase 18 | Pending |

**v1.0 Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

**v2.0 Coverage:**
- v2 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

**v3.0 Coverage:**
- v3 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

**v4.0 Coverage:**
- v4 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-30 after v4.0 roadmap creation*
