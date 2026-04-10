# MDM Reverse-Engineering & VN30 Market Timing

## What This Is

A research and trading system project to reverse-engineer Dr. K's Market Direction Model (MDM) using 52 years of published signal history (962 signals, 1974-2026) and multi-indicator feature engineering. The project discovers which technical indicator conditions (EMA crossovers, MACD, MA relationships) trigger Buy/Sell/Cash transitions, then applies discovered rules to both NASDAQ and VN30. Also maintains a separate VSA (Volume Spread Analysis) strategy.

## Core Value

Discover the actual indicator-based rules driving Dr. K's MDM signals by analyzing 962 published signals against computed technical indicators — achieving high match rate across both historical and recent periods.

## Current Milestone: v7.0 CANSLIM Stock Picking + MDM Capital Allocation on VN100 (Shipped 2026-04-10)

**Goal:** Long-only CANSLIM stock picking trên rổ VN100, dùng MDM (HybridEngine + fail-safe) làm gate phân bổ tỷ lệ tiền/hàng, event-driven, max 8 vị thế, backtest qua nhiều năm.

**Target features:**
- Research papers học thuật về CANSLIM (rules C/A/N/S/L/I/M, biến thể định lượng, entry confirmation)
- Data layer: Postgres connector (TA), MySQL connector (fundamentals), Redis connector (live, phase sau)
- VN100 universe loader (static)
- CANSLIM scorer module (per-stock score 0-100, daily)
- Event-driven signal engine (FTD, base breakout, RS new high, EPS surprise)
- Stock-level entry confirmation (MDM BUY là cần, không đủ — phải chờ pivot buy point per stock)
- MDM-driven capital allocation policy (BUY/CASH/SELL → exposure %)
- Multi-stock long-only portfolio engine (max 8 vị thế, O'Neil stop 7-8%, T+2.5, 7% limit)
- Backtest + performance reporting (CAGR, Sharpe, MaxDD, win rate vs benchmark)
- Validation vs `rank_top_stocks.diem_canslim` baseline

**Key context:**
- Universe VN100 static (không có point-in-time data)
- Data sources: Postgres `stock_eod` (5.9M rows, 2936 mã, đến 2026-04-08), Postgres `stock_rs`/`nganh_rs`/`nhnl_indicator`, MySQL `ratios_stock`/`is_quarter_*`/`rank_top_stocks`
- Long-only, max 8 vị thế, event-driven
- MDM signal source: HybridEngine + fail-safe (best v6.0)

## Completed: v6.0 MDM Fail-Safe & Signal Refinement (shipped 2026-04-02)

**Kết quả:**
- [x] Fail-safe mechanism — auto-CASH khi close vượt standby-sell HIGH → +47% return (Phase 23)
- [x] Gap-up buy neutralization — invalidate buy nếu low < prev_close (Phase 24)
- [x] 6% rally attempt threshold — FTD sớm hơn khi giảm nông (Phase 24)
- [x] MA50/200dma review — A/B test: loại MA50 SELL tăng Sharpe 0.34→0.50 (Phase 25)
- [x] Banding/volatility filter — ATR-based suppress trong low-vol, giảm 50-79% transitions (Phase 26)
- [x] Combined validation — A/B + walk-forward ALL PASS (Phase 27)

**Best model:** HybridEngine + fail-safe = **+239%** return, CAGR 11.5%, MaxDD -28.2% (beat Buy & Hold +205%)
**Dashboard:** http://mdm-trading-dashboard.s3-website-ap-southeast-1.amazonaws.com

## Requirements

### Validated

- ✓ MDM original rules (pre-2019) implemented — existing `models/` package
- ✓ VSA strategy implemented — existing `vn30_vsa/` package
- ✓ Backtesting infrastructure — `run_backtest.py`, performance tracking
- ✓ Data loaders for VN30, NASDAQ, S&P500 — CSV format with OHLCV
- ✓ Kelly Criterion position management — existing implementation

### Active (v7.0)

- [ ] Research CANSLIM academic literature (rules, quantitative variants, Vietnam adaptation, entry confirmation)
- [ ] Database connectors (Postgres TA, MySQL fundamentals, Redis live)
- [ ] VN100 universe loader (static)
- [ ] CANSLIM scorer (C/A/N/S/L/I/M components)
- [ ] Event-driven signal engine + stock-level entry confirmation
- [ ] MDM capital allocation policy
- [x] Multi-stock long-only portfolio engine (max 8 positions) — Phase 31
- [x] Backtest + performance reporting on VN100 — Phase 34 (profit_factor=3.74, real_CAGR, 5 benchmarks)
- [ ] Validation vs `rank_top_stocks.diem_canslim` baseline

### Validated (v1.0-v5.0)

- ✓ Reorganize codebase into clearly separated strategies — v1.0
- ✓ Normalize US market data — v1.0
- ✓ Run MDM classic rules on NASDAQ and compare with published signals — v1.0
- ✓ Identify divergence points between classic rules and post-2019 signals — v1.0
- ✓ Implement MDM v2 candidate rules with 3-state machine — v1.0
- ✓ Validate MDM v2 against published signal history — v1.0
- ✓ Use decision trees to discover indicator conditions per era — v2.0
- ✓ Score discovered rules with match rates and cross-era validation — v2.0
- ✓ Hybrid engine with Propose-Filter-Decide pipeline — v3.0
- ✓ Short signal with stop loss and cover mechanics — v4.0
- ✓ QE Floor filter (suppress SELL during liquidity expansion) — v5.0
- ✓ SELL Acceleration Gate (downside momentum required) — v5.0
- ✓ BUY Selectivity (trend filter + confirmation window) — v5.0
- ✓ Combined A/B + walk-forward validation — v5.0

### Out of Scope

- Real-time trading or live signal generation — this is research/backtesting only
- Recreating the exact proprietary model — we're approximating based on public data
- Web scraping or automated data collection from Dr. K's website
- Options or derivatives strategies beyond basic long/short/cash
- Mobile app or web UI — command-line/notebook analysis only

## Context

**Dr. K's MDM history:**
- Original model dates back to ~2000, based on IBD/O'Neil methodology (Follow-Through Days, Distribution Days, Rally Attempts)
- Material change made Feb 9, 2019 that significantly improved performance
- Model trades NASDAQ Composite and leveraged ETF TECL
- Three signals: Buy (long), Sell (short), Cash (flat)
- Published signal history available from 2017-2026 on virtueofselfishinvesting.com

**Key observations about post-2019 behavior:**
1. Cash state switching is much faster (sometimes same-day Buy→Cash)
2. Sell signals appear to trigger without full 5-DD accumulation
3. Model appears more responsive to short-term price action

**Key observations from 2012 VMAP webinar (Dr. K transcript):**
1. Cash state existed pre-2019 — MDM issued "neutral signal" on Oct 15, 2012 (bác bỏ giả thuyết Cash chỉ post-2019)
2. 6% rally attempt threshold: NASDAQ must fall >= 6% before requiring classic FTD (day 4+); below 6% FTD can come anytime
3. FTD requires "confirming action in leading stocks" — not just index price/volume
4. "Banding width" concept: model performance depends on price oscillation amplitude — too narrow = whipsaw, implies volatility-aware filtering
5. Cash→Sell triggered by "continued deterioration and selling pressure in leading stocks AND major indices"
6. Dr. K: "the key is to not change the inherent logic in the model" — core rules are stable, only minor adjustments
7. Worst drawdowns: 15.7% (Q2-Q3 1999), 18.1% (2012) on 1x ETF

**Existing codebase:**
- `strategies/mdm_classic/` — MDM classic implementation (migrated from `models/`)
- `strategies/vsa/` — Independent VSA strategy (migrated from `vn30_vsa/`)
- `scripts/` — Entry-point scripts (`run_backtest.py`, `optimize_mdm.py`, `check_date.py`)
- `strategies/mdm_v2/` — MDM v2 engine with 3-state machine (BUY/CASH/SELL) and parameterized config
- `analysis/hypothesis/` — Hypothesis testing framework and parameter sweep for v2 tuning
- `strategies/mdm_v2/performance.py` — V2PerformanceAnalyzer (equity curve, drawdown, Sharpe, win rate)
- `analysis/validate_v2.py` — Full validation pipeline (match rates, three-way comparison, dashboard)
- `notebooks/v2_validation.ipynb` — Interactive Jupyter validation notebook
- `core/indicators.py` — Indicator engine: EMA 9/21/55, MA 200, MACD (12,26,9), Heikin Ashi Smoothed
- `core/feature_snapshot.py` — Feature snapshot extraction: joins indicators with 962 signal dates + 8 boolean features
- `analysis/rule_discovery.py` — Rule discovery pipeline: era splitting, statistical profiling, decision tree training, human-readable rule extraction
- `analysis/validate_discovery.py` — Discovery validation: match rate scoring, confusion matrices, cross-era validation, degradation deltas, two-era dashboard
- `strategies/mdm_hybrid/indicator_filter.py` — IndicatorFilter: 6-condition filter with CONFIRM/VETO/OVERRIDE verdicts for hybrid signal validation
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — HybridEngine with Propose-Filter-Decide pipeline: state machine proposes, indicators confirm/veto/override
- `scripts/run_hybrid_backtest.py` — Hybrid backtest entry point with signal log CSV output
- `analysis/validate_hybrid.py` — Hybrid validation pipeline: confusion matrices, per-type accuracy, v2 baseline comparison, held-out discipline
- `tests/test_hybrid_validation.py` — Integration tests for hybrid validation pipeline
- `analysis/` — Analysis tools (`analyze_drawdown.py`, `diagnose_vn30.py`)
- `data/` — NASDAQ, S&P500, VN30 OHLCV data
- Data format: US data normalized (Phase 1), VN30 data is native scale

**Published signal data (embedded in project):**
- Full NASDAQ signal history: 1974-07-17 to 2026-02-27 (962 signals) — `data/signals/nasdaq_signals_full.csv`
- TECL signals: 2017-01-30 to 2026-02-26 (100+ signals)
- NASDAQ Composite signals (partial): same period — `data/signals/nasdaq_signals.csv`
- All include Buy/Sell/Cash with % gain/loss per trade and $1 growth tracking

**Dr. K's known indicators (from TradingView chart):**
- EMA 9, EMA 21, EMA 55 (multiple exponential moving averages)
- MA 200 (simple moving average, long-term trend)
- MACD Strategy 12 26 9 (momentum)
- Heikin Ashi Smoothed Buy Sell v4 55 (trend confirmation)
- Global Liquidity Index (macro)
- Volume Profile (VRVP)

## Constraints

- **Data**: US market data prices appear to be scaled by ~1000x — must normalize before analysis
- **Validation**: Can only validate against publicly delayed signals (up to 2 months delay for non-members)
- **VN30 adaptation**: Vietnamese market has different microstructure (T+2.5 settlement, 7% price limit, derivative expiry effects)
- **Scope**: The reverse-engineered model will be an approximation — exact replication is unlikely without proprietary knowledge

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep VSA as separate strategy | User preference — independent trading system, not a filter for MDM | ✓ Good |
| Combined approach for reverse-engineering | Run classic rules + analyze patterns simultaneously for best coverage | ✓ Good |
| NASDAQ as primary validation index | Dr. K's model trades NASDAQ Composite; TECL is just leveraged exposure | ✓ Good |
| Organize strategies into separate packages | Clean separation enables independent development and testing | ✓ Good |
| QE Floor disabled by default on VN30 | Fed liquidity has low correlation with VN30 — degrades performance (93.7% vs 190.8%) | ✓ Good |
| Dashboard simplified to single V2 model | Hybrid/P15/Filtered models all underperform V2 on VN30 — less clutter | ✓ Good |
| Walk-forward split at 2020-01-01 | Pre-COVID train, post-COVID test — validates filters across regime change | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-10 — v7.0 shipped + Phase 999.1 fix: MDM SELL nay đóng chỉ 50% vị thế yếu nhất theo RS (partial liquidation); vị thế giữ lại vẫn đóng qua stop/signal cá nhân. OOS post-fix: CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31%.*
