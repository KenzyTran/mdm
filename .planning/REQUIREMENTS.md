# Requirements: MDM Reverse-Engineering & VN30 Market Timing

**Defined:** 2026-03-31
**Core Value:** Discover the actual indicator-based rules driving Dr. K's MDM signals -- optimized for VN30

## v6.0 Requirements

### Fail-Safe Mechanism

- [x] **SAFE-01**: Khi V2 engine phat SELL signal, ghi nhan HIGH cua standby-sell day (ngay ngay truoc sell signal day) lam fail-safe threshold
- [x] **SAFE-02**: Neu VN30 close vuot standby-sell HIGH sau khi vao SELL -> auto-exit ve CASH (false signal detected)
- [x] **SAFE-03**: Backtest tren VN30 xac nhan fail-safe giam false signal loss

### Gap-Up Buy Neutralization

- [ ] **GAP-01**: Invalidate buy signal neu intraday low < previous day close (gap-up bi pha)
- [ ] **GAP-02**: A/B backtest so sanh V2 co/khong gap-up filter tren VN30

### Rally Attempt Threshold

- [ ] **RALLY-01**: Khi VN30 giam < 6% tu dinh, FTD co the den bat cu ngay nao (khong can cho day 3+)
- [ ] **RALLY-02**: Khi VN30 giam >= 6% tu dinh, yeu cau FTD classic (day 3+)
- [ ] **RALLY-03**: A/B backtest tren VN30 so sanh co/khong 6% threshold logic

### MA50/200dma Review

- [ ] **MAREVIEW-01**: A/B backtest V2 hien tai vs V2 loai bo MA50 breakdown khoi SELL trigger logic tren VN30
- [ ] **MAREVIEW-02**: A/B backtest V2 hien tai vs V2 loai bo MA50 khoi BUY filter logic tren VN30
- [ ] **MAREVIEW-03**: Report ket luan: giu/bo/thay the MA50 trong signal logic, voi evidence tu backtest VN30

### Banding/Volatility Filter

- [ ] **BAND-01**: Compute ATR-based volatility regime (high/normal/low) tren VN30 daily data
- [ ] **BAND-02**: Suppress signal switching khi volatility regime = low (banding qua hep cho VN30)
- [ ] **BAND-03**: Backtest tren VN30 cac giai doan sideways xac nhan filter giam false signals

### Validation

- [ ] **VAL-08**: Combined A/B backtest tat ca v6.0 features ON vs OFF tren VN30
- [ ] **VAL-09**: Walk-forward validation (train pre-2022, test 2022-2026) cho combined v6.0 features tren VN30
- [ ] **VAL-10**: Update S3 dashboard voi performance metrics moi

## Future Requirements

### Deferred from v3.0

- **FUT-01**: Era-aware evaluation rieng pre/post 2019
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
| NASDAQ-specific optimization | v6.0 focuses on VN30 only -- Dr. K rules adapted for Vietnamese market |
| Leading stocks confirmation | Requires VN30 breadth data not currently available |
| ML ensemble (XGBoost, Random Forest) | Too few signals, will overfit |
| Real-time trading or live signals | Research/backtesting only |
| Intraday tick data analysis | MDM operates on daily bars |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SAFE-01 | Phase 23 | Complete |
| SAFE-02 | Phase 23 | Complete |
| SAFE-03 | Phase 23 | Complete |
| GAP-01 | Phase 24 | Pending |
| GAP-02 | Phase 24 | Pending |
| RALLY-01 | Phase 24 | Pending |
| RALLY-02 | Phase 24 | Pending |
| RALLY-03 | Phase 24 | Pending |
| MAREVIEW-01 | Phase 25 | Pending |
| MAREVIEW-02 | Phase 25 | Pending |
| MAREVIEW-03 | Phase 25 | Pending |
| BAND-01 | Phase 26 | Pending |
| BAND-02 | Phase 26 | Pending |
| BAND-03 | Phase 26 | Pending |
| VAL-08 | Phase 27 | Pending |
| VAL-09 | Phase 27 | Pending |
| VAL-10 | Phase 27 | Pending |

**v6.0 Coverage:**
- v6 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after v6.0 roadmap created*
