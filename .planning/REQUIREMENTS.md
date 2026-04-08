# Requirements: MDM Reverse-Engineering & VN30 Market Timing

**Defined:** 2026-03-31
**Core Value:** Discover the actual indicator-based rules driving Dr. K's MDM signals -- optimized for VN30

## v6.0 Requirements

### Fail-Safe Mechanism

- [x] **SAFE-01**: Khi V2 engine phat SELL signal, ghi nhan HIGH cua standby-sell day (ngay ngay truoc sell signal day) lam fail-safe threshold
- [x] **SAFE-02**: Neu VN30 close vuot standby-sell HIGH sau khi vao SELL -> auto-exit ve CASH (false signal detected)
- [x] **SAFE-03**: Backtest tren VN30 xac nhan fail-safe giam false signal loss

### Gap-Up Buy Neutralization

- [x] **GAP-01**: Invalidate buy signal neu intraday low < previous day close (gap-up bi pha)
- [x] **GAP-02**: A/B backtest so sanh V2 co/khong gap-up filter tren VN30

### Rally Attempt Threshold

- [x] **RALLY-01**: Khi VN30 giam < 6% tu dinh, FTD co the den bat cu ngay nao (khong can cho day 3+)
- [x] **RALLY-02**: Khi VN30 giam >= 6% tu dinh, yeu cau FTD classic (day 3+)
- [x] **RALLY-03**: A/B backtest tren VN30 so sanh co/khong 6% threshold logic

### MA50/200dma Review

- [x] **MAREVIEW-01**: A/B backtest V2 hien tai vs V2 loai bo MA50 breakdown khoi SELL trigger logic tren VN30
- [x] **MAREVIEW-02**: A/B backtest V2 hien tai vs V2 loai bo MA50 khoi BUY filter logic tren VN30
- [x] **MAREVIEW-03**: Report ket luan: giu/bo/thay the MA50 trong signal logic, voi evidence tu backtest VN30

### Banding/Volatility Filter

- [x] **BAND-01**: Compute ATR-based volatility regime (high/normal/low) tren VN30 daily data
- [x] **BAND-02**: Suppress signal switching khi volatility regime = low (banding qua hep cho VN30)
- [x] **BAND-03**: Backtest tren VN30 cac giai doan sideways xac nhan filter giam false signals

### Validation

- [x] **VAL-08**: Combined A/B backtest tat ca v6.0 features ON vs OFF tren VN30
- [x] **VAL-09**: Walk-forward validation (train pre-2022, test 2022-2026) cho combined v6.0 features tren VN30
- [x] **VAL-10**: Update S3 dashboard voi performance metrics moi

## v7.0 Requirements — CANSLIM + MDM on VN100

**Defined:** 2026-04-08
**Goal:** Long-only CANSLIM stock picking on VN100, MDM gates capital allocation, event-driven, max 8 positions, stock-level entry confirmation required.

### Data Layer & Audit

- [x] **DATA-01**: Postgres connector module (env-driven, connection pooling) + integration test
- [x] **DATA-02**: MySQL connector module (env-driven) + integration test
- [ ] **DATA-03**: Audit `stock_eod` for delisted ticker coverage; report distinct stockcodes whose `max(tradingdate)` is pre-2024 (decide whether to backfill)
- [ ] **DATA-04**: Verify `stock_eod` price adjustment for splits/dividends/rights; document convention; if unadjusted, build adjustment helper
- [ ] **DATA-05**: Resolve EPS publish_date — find or estimate (default `period_end + 45d` Q1-Q3, `+90d` Q4/annual); document per-table source
- [ ] **DATA-06**: Per-stock fundamental coverage report for VN100 universe back to 2014 (which stocks have full quarterly EPS history)
- [ ] **DATA-07**: Verify `stock_foreign_eod` daily VN100 coverage 2014-2026

### VN100 Universe

- [ ] **UNIV-01**: VN100 universe loader from `stock_list.nhomtop` (or proxy: top-100 by free-float mcap + 20d ADV ≥10B + listed ≥180d)
- [ ] **UNIV-02**: Semi-annual rebalance step-changes (Jan/Jul) — universe stable between rebalance dates
- [ ] **UNIV-03**: Sensitivity-run support: current-VN100, liquidity-reconstructed, VN30-only

### CANSLIM Scorer

- [ ] **CANS-01**: C rule — quarterly EPS YoY ≥20% configurable, with publish_date guard
- [ ] **CANS-02**: C+ rule — EPS acceleration vs prior 2 quarters
- [ ] **CANS-03**: A rule — 3yr EPS CAGR ≥15% configurable
- [ ] **CANS-04**: A+ rule — annual EPS positive each of last 3 years
- [ ] **CANS-05**: N rule — close within 15% of 252-day high (configurable)
- [ ] **CANS-06**: S rule — breakout volume ≥1.5× avgvol50 (configurable)
- [ ] **CANS-07**: L rule — IBD-style RS rating (`0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252`), percentile-rank within VN100, threshold ≥80
- [ ] **CANS-08**: I rule — `sum(foreign_net_buy[T-20..T-1]) > 0`, fallback 13W A/D rating
- [ ] **CANS-09**: Liquidity filter — 20d median turnover ≥5B VND
- [ ] **CANS-10**: Sector handling — non-financials use C/A directly; banks substitute PPOP growth; CTCK/Insurance excluded V1
- [ ] **CANS-11**: `CanslimConfig` dataclass with all thresholds + per-day score function returning per-stock pass/fail + composite score
- [ ] **CANS-12**: Validation: spot-check CANSLIM ranks vs MySQL `rank_top_stocks.diem_canslim` baseline

### Entry Confirmation

- [ ] **ENTRY-01**: Option A — 52-week high + volume surge + close>open + upper-half close
- [ ] **ENTRY-02**: Option C — Pocket Pivot (vol > max down-day vols last 10d, close ≥ MA50, in/near base)
- [ ] **ENTRY-03**: Entry timing window — fire only within 20 trading days after MDM BUY event; expire after
- [ ] **ENTRY-04**: Entry execution model — fill at next-day open (ATO), not signal-bar close
- [ ] **ENTRY-05**: A/B comparison Option A vs Option C on VN100 backtest

### MDM Capital Allocation Gate

- [ ] **GATE-01**: MDM signal source = HybridEngine + fail-safe on VNINDEX (existing v6.0)
- [ ] **GATE-02**: Policy A (strict) — BUY: allow new entries up to 8 slots, target 100% exposure; CASH: hold existing, no new; SELL: liquidate all next open
- [ ] **GATE-03**: Ceiling/floor lock handling — skip entry fill if `next_open == ceiling AND next_high == next_low`; defer exit if floor-locked, exit next open
- [ ] **GATE-04**: T+2 settlement enforcement — bought day D not sellable until D+3

### Portfolio Engine

- [ ] **PORT-01**: Multi-stock long-only state machine (max 8 concurrent positions)
- [ ] **PORT-02**: Equal-weight position sizing (12.5%/slot), 100-share lot rounding (round down)
- [ ] **PORT-03**: 8% hard stop loss
- [ ] **PORT-04**: MA50 trailing stop (close break confirmed by volume ≥1.25× 20d avg)
- [ ] **PORT-05**: Limit-down handling — if stop hit on limit-down day, exit next open
- [ ] **PORT-06**: Exit priority chain — MDM SELL > hard stop > MA50 break > RS deterioration (RS<70 for 5 sessions)
- [ ] **PORT-07**: Re-entry cooldown — 5 days per ticker after stop-out
- [ ] **PORT-08**: Transaction costs — 0.25% commission both sides + 0.10% sell tax + 0.10% slippage
- [ ] **PORT-09**: Liquidity gate — only enter if 20d ADV > 10× position size
- [ ] **PORT-10**: Trade log + position log + daily NAV with `state[i-1]` discipline (avoid 707% bug pattern)

### Backtest & Reporting

- [ ] **BT-01**: VN100 backtest engine wiring all layers (universe → CANSLIM → entry → portfolio → costs)
- [ ] **BT-02**: In-sample run 2014-2018 + parameter sweep (CANSLIM thresholds, entry option, stop, slots)
- [ ] **BT-03**: Out-of-sample run 2019-2025 with locked parameters
- [ ] **BT-04**: Sensitivity runs across (a) current VN100 (b) liquidity-reconstructed (c) VN30-only
- [ ] **BT-05**: Performance report — CAGR, Sharpe (risk-free = 10Y VN govt ~3%), MaxDD, hit rate, profit factor, hold time, turnover, cost drag
- [ ] **BT-06**: Benchmark comparison — VN-Index B&H, VN30 B&H, MDM-only-on-index, 12M deposit, SJC gold
- [ ] **BT-07**: Real (inflation-adjusted) CAGR alongside nominal
- [ ] **BT-08**: Validation targets — Sharpe uplift > 0.20 vs benchmark, MaxDD reduction > 30% vs B&H

### Documentation

- [ ] **DOC-01**: `docs/rules_canslim_mdm.md` describing locked rules + parameters (kept in sync with code per Code-Docs Sync Rule)
- [ ] **DOC-02**: Data dictionary for new connectors and CANSLIM scorer

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
| GAP-01 | Phase 24 | Complete |
| GAP-02 | Phase 24 | Complete |
| RALLY-01 | Phase 24 | Complete |
| RALLY-02 | Phase 24 | Complete |
| RALLY-03 | Phase 24 | Complete |
| MAREVIEW-01 | Phase 25 | Complete |
| MAREVIEW-02 | Phase 25 | Complete |
| MAREVIEW-03 | Phase 25 | Complete |
| BAND-01 | Phase 26 | Complete |
| BAND-02 | Phase 26 | Complete |
| BAND-03 | Phase 26 | Complete |
| VAL-08 | Phase 27 | Complete |
| VAL-09 | Phase 27 | Complete |
| VAL-10 | Phase 27 | Complete |

**v6.0 Coverage:**
- v6 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after v6.0 roadmap created*
