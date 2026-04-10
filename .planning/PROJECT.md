# MDM Reverse-Engineering & VN30 Market Timing

## What This Is

A research and trading system project to reverse-engineer Dr. K's Market Direction Model (MDM) using 52 years of published signal history (962 signals, 1974-2026), then apply it as a capital allocation gate for long-only CANSLIM stock picking on the VN100 universe. The project discovers indicator-based MDM rules (EMA crossovers, MACD, MA relationships) and combines them with a quantitative CANSLIM scorer to build a multi-stock portfolio engine for the Vietnamese market.

## Core Value

Discover the actual indicator-based rules driving Dr. K's MDM signals — and combine them with quantitative CANSLIM stock selection on VN100 to build a backtested, rule-based trading system for the Vietnamese market.

## Completed: v7.0 CANSLIM + MDM on VN100 (shipped 2026-04-10)

**Kết quả:**
- [x] Postgres + MySQL connectors, VN100 universe loader (100 tickers, 2936 stockcodes audited) — Phase 28
- [x] CANSLIM scorer (C/A/N/S/L/I/M) validated vs diem_canslim baseline (OOS rho=0.365) — Phase 29
- [x] Stock entry confirmation: Option A (52w breakout) + Option C (Pocket Pivot), MDM BUY window — Phase 30
- [x] Multi-stock portfolio engine: max 8 positions, 8% hard stop, MA50 trailing stop, T+2.5, 0.35% costs — Phase 31
- [x] In-sample sweep 2014-2018, locked parameters selected — Phase 32
- [x] OOS validation 2019-2025: CAGR=6.23%, Sharpe=0.448, MaxDD=-10.22% — Phase 33
- [x] CANSLIM-only baseline Sharpe=1.047 >> MDM+CANSLIM Sharpe=0.448; MDM gate is bottleneck — Phase 33
- [x] Performance report: profit_factor=3.74, real_CAGR, 5 benchmarks — Phase 34
- [x] RS-ranked partial liquidation on MDM SELL (keep top 50%): OOS CAGR=10.18%, Sharpe=0.813, MaxDD=-16.31% — Phase 999.1

**Best model with 999.1 fix:** CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31% (OOS 2019-2025)

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

## Current Milestone: v8.0 Momentum Stock Selection

**Goal:** Thay thế CANSLIM fundamental bằng RS momentum thuần TA để chọn cổ phiếu, giữ MDM làm timing gate.

**Target features:**
- RS tự tính từ giá: so sánh IBD Weighted ROC (0.4×ROC63 + 0.2×ROC126/189/252) vs ROC 6 tháng đơn giản
- Stock filter: RS ≥ 70 (top 30% trong VN100) + N rule (gần đỉnh 52 tuần) + Volume surge tại entry
- Entry confirmation: Option A/C giữ nguyên
- MDM gate: giữ nguyên (BUY/CASH/SELL + partial liquidation)
- Backtest đầy đủ 2016-2025, so sánh với v7.0 baseline

### Active

### Validated (v7.0)

- ✓ Database connectors (Postgres TA, MySQL fundamentals) — v7.0
- ✓ VN100 universe loader (100-ticker static, semi-annual rebalance) — v7.0
- ✓ CANSLIM scorer (C/A/N/S/L/I/M, validated vs diem_canslim OOS rho=0.365) — v7.0
- ✓ Stock entry confirmation (Option A breakout + Option C Pocket Pivot) — v7.0
- ✓ MDM capital allocation gate (BUY=new entries, CASH=hold, SELL=partial liquidation by RS) — v7.0
- ✓ Multi-stock long-only portfolio engine (max 8 positions, 8% stop, MA50 trailing) — v7.0
- ✓ Backtest + performance reporting (profit_factor=3.74, real_CAGR, 5 benchmarks) — v7.0
- ✓ RS-ranked partial liquidation on MDM SELL (keep top 50%) — v7.0
- ✓ OOS validation 2019-2025: CAGR=10.18%, Sharpe=0.813, MaxDD=-16.31% — v7.0

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
| MDM BUY is necessary but not sufficient for stock entry | Stock-level confirmation (pivot buy point) required per stock — avoids buying on index signal alone | ✓ Good |
| CANSLIM is primary alpha source, not MDM timing | CANSLIM-only Sharpe=1.047 >> MDM+CANSLIM Sharpe=0.448; MDM gate reduces exposure during corrections | ✓ Good |
| RS-ranked partial liquidation on MDM SELL | Keep top 50% positions by RS instead of full liquidation; weaker positions closed, strongest held with individual stops | ✓ Good |
| current-vn100 preferred over liquidity-reconstructed | Liquidity-reconstructed Sharpe=0.052 vs current-vn100 Sharpe=0.448; survivorship bias is acknowledged tradeoff | ✓ Good |
| equal-weight 12.5%/slot sizing | 8 slots × 12.5% = 100% exposure; simpler and avoids Kelly overfitting on small sample | ✓ Good |

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

## Context

**Current codebase state (v7.0):**
- ~250 files, 53,598 insertions since v6.0
- New packages: `strategies/canslim/`, `strategies/entry/`, `strategies/portfolio/`, `connectors/`
- Data connectors: Postgres (`stock_eod`, `stock_rs`, `nganh_rs`, `nhnl_indicator`) + MySQL (`ratios_stock`, `is_quarter_*`, `rank_top_stocks`)
- VN100 universe: 100-ticker static, semi-annual rebalance Jan/Jul
- CANSLIM scorer: 8 rules (C/A/N/S/L/I/M + liquidity), schema-locked
- Entry confirmation: Option A (52w-high breakout) + Option C (Pocket Pivot), next-day ATO fill
- Portfolio engine: max 8 positions, 8% hard stop, MA50 trailing stop, T+2 settlement, 0.35% total cost
- MDM signal source: HybridEngine + fail-safe on VNINDEX (v6.0 best model)
- OOS performance (2019-2025, 999.1 fix): CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31%

**Key finding from v7.0:**
CANSLIM stock selection alone (without MDM gate) achieves Sharpe=1.047, CAGR=16.4%, 109 trades. MDM gate reduces this to Sharpe=0.448 but also reduces MaxDD from ~40% to ~10%. MDM is a risk management tool, not an alpha generator for stock selection. This reframes the purpose of the MDM component — next milestone should investigate CASH policy (hold vs liquidate) to recover lost alpha.

---
*Last updated: 2026-04-10 after v7.0 milestone*
