# Requirements: VN30 MDM Whipsaw Reduction (v9.0)

**Defined:** 2026-04-15
**Core Value:** Giảm whipsaw trong HybridEngine + fail-safe trên VN30 bằng ATR Buffer Zone + Refined Distribution Day, beat baseline v6.0 (Return +238.8%, CAGR 11.5%, MaxDD -28.2%).

## v9.0 Requirements

### ATR Buffer Zone

- [x] **ATR-01**: Compute `violation_threshold` column = SMA50 − k × ATR_N, parameterized by (k, N); integrate into existing indicator pipeline
- [ ] **ATR-02**: MA50 breakdown SELL trigger requires close < violation_threshold trên m phiên liên tiếp (configurable m)
- [x] **ATR-03**: Config flag `atr_buffer_enabled` trong MDMV2Config / HybridEngine để A/B baseline vs +ATR
- [ ] **ATR-04**: Backward-compat — khi `atr_buffer_enabled=False`, trigger behavior khớp hoàn toàn v6.0 baseline (byte-identical signal log)

### Refined Distribution Day

- [ ] **DD-01**: DD detector accepts params (`large_drop`, `small_drop`, `large_vol_rule`, `small_vol_percentile`, `small_vol_lookback`) thay cho hard-coded -0.2%
- [ ] **DD-02**: Implement dual-threshold rule — DD=True nếu (drop ≥ large_drop AND volume > vol_ma20) HOẶC (drop ≥ small_drop AND volume ∈ top small_vol_percentile% của small_vol_lookback phiên gần nhất)
- [ ] **DD-03**: Config flag `refined_dd_enabled` để fallback về classic -0.2% rule khi off
- [ ] **DD-04**: Backward-compat — khi `refined_dd_enabled=False`, DD count khớp v6.0 baseline

### Grid Search & Selection

- [ ] **SWEEP-01**: ATR grid search over `atr_multiplier` [0.3, 0.5, 0.7, 1.0] × `atr_period` [10, 14, 20] × `consecutive_days` [1, 2, 3] → 36 runs, output `output/v9_atr_sweep.csv` (config + Sharpe + CAGR + MaxDD + transitions)
- [ ] **SWEEP-02**: DD grid search on locked best ATR config over `large_drop` [-0.5, -0.6, -0.7, -0.8, -0.9, -1.0]% × `small_drop` [-0.3, -0.4, -0.5]% × `small_vol_percentile` [3, 5, 10]% → 54 runs, output `output/v9_dd_sweep.csv`
- [ ] **SWEEP-03**: Selection script picks max Sharpe subject to MaxDD ≤ -30% (tie-break CAGR) from each sweep; writes `output/v9_atr_best.txt` và `output/v9_dd_best.txt`
- [ ] **SWEEP-04**: All sweeps run on train window 2015-2021 only (no OOS leakage)

### A/B + Walk-Forward Validation

- [ ] **VAL-01**: A/B report with 4 scenarios (baseline / +ATR only / +DD only / +both) on full period 2015-2026, output `output/v9_ab_comparison.txt` với CAGR, Sharpe, MaxDD, transitions, time-in-state
- [ ] **VAL-02**: Walk-forward validation — Train 2015-2021, Test 2022-2026, CAGR degradation < 50% threshold
- [ ] **VAL-03**: Combined model beats baseline v6.0 on CAGR (≥ 11.5%) AND (Sharpe > baseline OR MaxDD < -25%); document if fails
- [ ] **VAL-04**: Transition count report — measure whipsaw reduction (target: SELL signals reduce from 124 baseline, MA50-breakdown share drops from 84%)

### Documentation & Dashboard

- [ ] **DOC-01**: Rule documentation updated — `docs/rules_mdm_hybrid.md` reflects new ATR buffer + DD definition
- [ ] **DOC-02**: Dashboard `dashboard/data/` updated với v9 model JSON (equity curve + signal log) cho comparison view
- [ ] **DOC-03**: v9 report markdown `docs/audits/v9_0_report.md` — baseline vs v9, sweep winners, diagnostic (whipsaw metrics), conclusion

## Future Requirements (v10.0+)

- SBV open market operations data (liquidity signal for VN market) — chưa thu thập được
- MA10 "3-phiên exit" buffer — 49% BUY exits từ MA10 có thể cải thiện thêm
- FTD BUY signal refinement — 60 BUY signals hiện tại chưa phải bottleneck nhưng có thể tối ưu
- Instrument simulation: VN30F1 futures (short-able, có leverage) vs ETF E1VFVN30 (long-only) vs cash index

## Out of Scope

| Feature | Reason |
|---------|--------|
| MA10 buffer | Diagnostic cho thấy 49% BUY exits từ MA10 — có value nhưng defer để scope gọn |
| BUY signal changes (FTD, 52w, MA50 breakout) | 60 BUY signals không phải bottleneck — SELL whipsaw là target chính |
| Joint grid search (ATR × DD simultaneously) | 1944 combos tốn compute — sequential 90-run đủ cho first pass |
| F1 futures / ETF simulation | Scope instrument sẽ mở rộng sau — milestone này giữ VN30 cash index giả định |
| SBV data | Chưa thu thập được — defer |
| Change in fail-safe mechanism | Fail-safe đã validated trong v6.0 — không touch |
| Live trading / paper trading | Research/backtest only — per project OOS rule |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ATR-01 | Phase 38 | Complete |
| ATR-02 | Phase 38 | Pending |
| ATR-03 | Phase 38 | Complete |
| ATR-04 | Phase 38 | Pending |
| DD-01 | Phase 39 | Pending |
| DD-02 | Phase 39 | Pending |
| DD-03 | Phase 39 | Pending |
| DD-04 | Phase 39 | Pending |
| SWEEP-01 | Phase 40 | Pending |
| SWEEP-02 | Phase 40 | Pending |
| SWEEP-03 | Phase 40 | Pending |
| SWEEP-04 | Phase 40 | Pending |
| VAL-01 | Phase 41 | Pending |
| VAL-02 | Phase 41 | Pending |
| VAL-03 | Phase 41 | Pending |
| VAL-04 | Phase 41 | Pending |
| DOC-01 | Phase 42 | Pending |
| DOC-02 | Phase 42 | Pending |
| DOC-03 | Phase 42 | Pending |

**Coverage:**
- v9.0 requirements: 19 total
- Mapped to phases: 19 ✓
- Unmapped: 0

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after roadmap creation (Phases 38-42)*
