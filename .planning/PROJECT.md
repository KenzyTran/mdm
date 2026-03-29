# MDM Reverse-Engineering & VN30 Market Timing

## What This Is

A research and trading system project to reverse-engineer Dr. K's Market Direction Model (MDM) using 52 years of published signal history (962 signals, 1974-2026) and multi-indicator feature engineering. The project discovers which technical indicator conditions (EMA crossovers, MACD, MA relationships) trigger Buy/Sell/Cash transitions, then applies discovered rules to both NASDAQ and VN30. Also maintains a separate VSA (Volume Spread Analysis) strategy.

## Core Value

Discover the actual indicator-based rules driving Dr. K's MDM signals by analyzing 962 published signals against computed technical indicators — achieving high match rate across both historical and recent periods.

## Current Milestone: v3.0 Hybrid MDM Engine

**Goal:** Kết hợp state machine cổ điển (Distribution Days, Follow-Through Days, Rally Attempts) với indicator filters (EMA/MACD) thành hybrid model — state machine đề xuất signal, indicators xác nhận/ghi đè.

**Target features:**
- State machine MDM classic (DD counting, FTD detection, Rally Attempts) làm tầng quyết định chính
- EMA 9/21/55, MACD, MA 200 làm bộ lọc xác nhận/ghi đè signal
- Cash state logic mới (không có trong classic, thêm vào post-2019)
- Chuỗi chuyển trạng thái có ngữ cảnh (Buy→Cash→Sell phụ thuộc trạng thái trước)
- Validation trên 962 signals với hybrid model (target: accuracy cao hơn 56.7%)
- So sánh hybrid vs pure decision tree vs pure state machine

## Requirements

### Validated

- ✓ MDM original rules (pre-2019) implemented — existing `models/` package
- ✓ VSA strategy implemented — existing `vn30_vsa/` package
- ✓ Backtesting infrastructure — `run_backtest.py`, performance tracking
- ✓ Data loaders for VN30, NASDAQ, S&P500 — CSV format with OHLCV
- ✓ Kelly Criterion position management — existing implementation

### Active

- [x] Reorganize codebase into clearly separated strategies (MDM classic, MDM v2, VSA) — Validated in Phase 2: Codebase Organization
- [x] Normalize US market data (NASDAQ/S&P500 prices appear scaled by ~1000x) — Validated in Phase 1: Data Integrity
- [x] Run MDM classic rules on NASDAQ data and compare with published signals — Validated in Phase 3: Signal Divergence Analysis
- [x] Identify divergence points between classic rules output and actual post-2019 signals — Validated in Phase 3: Signal Divergence Analysis
- [x] Analyze signal patterns to hypothesize new MDM v2 rules (Cash state behavior, faster signal switching, modified DD counting) — Validated in Phase 4: MDM V2 Engine
- [x] Implement MDM v2 candidate rules — Validated in Phase 4: MDM V2 Engine
- [x] Validate MDM v2 against published signal history (target: high match rate) — Validated in Phase 5: Validation & Performance
- [x] Use decision trees to discover indicator conditions that predict signal types per era — Validated in Phase 9: Rule Discovery
- [x] Score discovered rules against published signals with match rates, confusion matrices, and cross-era validation — Validated in Phase 10: Discovery Validation
- [ ] Adapt MDM v2 parameters for VN30 market characteristics
- [ ] Backtest MDM v2 on VN30 with performance reporting

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
| Keep VSA as separate strategy | User preference — independent trading system, not a filter for MDM | — Pending |
| Combined approach for reverse-engineering | Run classic rules + analyze patterns simultaneously for best coverage | — Pending |
| NASDAQ as primary validation index | Dr. K's model trades NASDAQ Composite; TECL is just leveraged exposure | — Pending |
| Organize strategies into separate packages | Clean separation enables independent development and testing | — Pending |

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
*Last updated: 2026-03-29 after Phase 13: Hybrid Engine Integration complete*
