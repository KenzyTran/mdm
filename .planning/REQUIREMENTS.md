# Requirements: MDM + Momentum Stock Selection (v8.0)

**Defined:** 2026-04-10
**Core Value:** RS momentum thuần TA thay thế CANSLIM fundamental, giữ MDM làm timing gate

## v8.0 Requirements

### RS Module

- [x] **MOM-01**: RS Weighted ROC (IBD style) tính được cho toàn VN100 — 0.4×ROC63 + 0.2×ROC126 + 0.2×ROC189 + 0.2×ROC252 — rank cross-sectional percentile [0,100] theo từng ngày
- [x] **MOM-02**: RS ROC 6 tháng đơn giản (ROC126) tính song song để so sánh in-sample
- [x] **MOM-03**: RS cache vào parquet theo period/formula, không tính lại mỗi lần chạy

### Momentum Scorer

- [x] **MSCO-01**: Stock filter RS ≥ 70 (top 30% VN100) là điều kiện đủ điều kiện mua
- [x] **MSCO-02**: N rule giữ lại — cổ phiếu phải trong vòng 15% đỉnh 52 tuần
- [x] **MSCO-03**: Volume surge tại ngày entry giữ lại (Option A/C đã có sẵn trong detector)
- [x] **MSCO-04**: Bỏ hoàn toàn C/A rule (EPS YoY, EPS CAGR) — không cần MySQL fundamentals

### Backtest

- [ ] **BT-01**: In-sample sweep 2016-2018 so sánh 2 RS formula (Weighted ROC vs ROC126), chọn formula tốt hơn
- [ ] **BT-02**: OOS 2019-2025 với formula được chọn từ in-sample
- [ ] **BT-03**: So sánh kết quả vs v7.0 baseline (CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31%) và VN-Index B&H

## Future Requirements (v9.0+)

- Integrate DB RS (rss/rsm/rsl) khi có đủ lịch sử từ 2016
- Thử rank RS trong toàn sàn (~2000 cổ phiếu) thay vì chỉ VN100
- Live signal generation từ RS rankings

## Out of Scope

| Feature | Reason |
|---------|--------|
| MySQL fundamentals (EPS, earnings) | Replaced by price-based RS — v8.0 goal |
| CANSLIM C/A rules | Fundamental rules replaced by momentum |
| RS từ stock_rs DB | Chỉ có từ 2022, không đủ cho backtest 2016 |
| Rebalance định kỳ | Giữ event-driven (entry signal) cho nhất quán với v7.0 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MOM-01 | Phase 35 | Complete |
| MOM-02 | Phase 35 | Complete |
| MOM-03 | Phase 35 | Complete |
| MSCO-01 | Phase 36 | Complete |
| MSCO-02 | Phase 36 | Complete |
| MSCO-03 | Phase 36 | Complete |
| MSCO-04 | Phase 36 | Complete |
| BT-01 | Phase 37 | Pending |
| BT-02 | Phase 37 | Pending |
| BT-03 | Phase 37 | Pending |

**Coverage:**
- v8.0 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after initial definition*
