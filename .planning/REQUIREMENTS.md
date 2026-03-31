# Requirements: MDM Reverse-Engineering & VN30 Market Timing

**Defined:** 2026-03-31
**Core Value:** Discover the actual indicator-based rules driving Dr. K's MDM signals — optimized for VN30

## v6.0 Requirements

### Fail-Safe Mechanism

- [ ] **SAFE-01**: Khi V2 engine phát SELL signal, ghi nhận HIGH của standby-sell day (ngày ngay trước sell signal day) làm fail-safe threshold
- [ ] **SAFE-02**: Nếu VN30 close vượt standby-sell HIGH sau khi vào SELL → auto-exit về CASH (false signal detected)
- [ ] **SAFE-03**: Backtest trên VN30 xác nhận fail-safe giảm false signal loss

### Gap-Up Buy Neutralization

- [ ] **GAP-01**: Invalidate buy signal nếu intraday low < previous day close (gap-up bị phá)
- [ ] **GAP-02**: A/B backtest so sánh V2 có/không gap-up filter trên VN30

### Rally Attempt Threshold

- [ ] **RALLY-01**: Khi VN30 giảm < 6% từ đỉnh, FTD có thể đến bất cứ ngày nào (không cần chờ day 3+)
- [ ] **RALLY-02**: Khi VN30 giảm ≥ 6% từ đỉnh, yêu cầu FTD classic (day 3+)
- [ ] **RALLY-03**: A/B backtest trên VN30 so sánh có/không 6% threshold logic

### MA50/200dma Review

- [ ] **MAREVIEW-01**: A/B backtest V2 hiện tại vs V2 loại bỏ MA50 breakdown khỏi SELL trigger logic trên VN30
- [ ] **MAREVIEW-02**: A/B backtest V2 hiện tại vs V2 loại bỏ MA50 khỏi BUY filter logic trên VN30
- [ ] **MAREVIEW-03**: Report kết luận: giữ/bỏ/thay thế MA50 trong signal logic, với evidence từ backtest VN30

### Banding/Volatility Filter

- [ ] **BAND-01**: Compute ATR-based volatility regime (high/normal/low) trên VN30 daily data
- [ ] **BAND-02**: Suppress signal switching khi volatility regime = low (banding quá hẹp cho VN30)
- [ ] **BAND-03**: Backtest trên VN30 các giai đoạn sideways xác nhận filter giảm false signals

### Validation

- [ ] **VAL-08**: Combined A/B backtest tất cả v6.0 features ON vs OFF trên VN30
- [ ] **VAL-09**: Walk-forward validation (train pre-2022, test 2022-2026) cho combined v6.0 features trên VN30
- [ ] **VAL-10**: Update S3 dashboard với performance metrics mới

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
| NASDAQ-specific optimization | v6.0 focuses on VN30 only — Dr. K rules adapted for Vietnamese market |
| Leading stocks confirmation | Requires VN30 breadth data not currently available |
| ML ensemble (XGBoost, Random Forest) | Too few signals, will overfit |
| Real-time trading or live signals | Research/backtesting only |
| Intraday tick data analysis | MDM operates on daily bars |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SAFE-01 | - | Pending |
| SAFE-02 | - | Pending |
| SAFE-03 | - | Pending |
| GAP-01 | - | Pending |
| GAP-02 | - | Pending |
| RALLY-01 | - | Pending |
| RALLY-02 | - | Pending |
| RALLY-03 | - | Pending |
| MAREVIEW-01 | - | Pending |
| MAREVIEW-02 | - | Pending |
| MAREVIEW-03 | - | Pending |
| BAND-01 | - | Pending |
| BAND-02 | - | Pending |
| BAND-03 | - | Pending |
| VAL-08 | - | Pending |
| VAL-09 | - | Pending |
| VAL-10 | - | Pending |

**v6.0 Coverage:**
- v6 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17 ⚠️

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after v6.0 milestone started*
