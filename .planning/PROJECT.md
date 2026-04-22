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

## Completed: v9.0 VN30 MDM Whipsaw Reduction (shipped 2026-04-21)

**Kết quả: v9.0 extensions REJECTED on evidence. v6.0 retained as production.**

Tất cả 3 scenario v9 (+ATR, +DD, +both) fail gate CAGR ≥ 11.5% trên full 2015-2026. Walk-forward degradation +67% → +96% (breaches 50% threshold) → Phase 40 grid search overfit train window 2015-2021.

**Phases shipped:**
- [x] Phase 38 — ATR Buffer Zone module (feature-gated, v6.0 parity when off)
- [x] Phase 39 — Refined Distribution Day module (dual-threshold, feature-gated, v6.0 parity when off)
- [x] Phase 40 — Grid-search sweeps (ATR 36 runs + DD 54 runs, train 2015-2021). Stage-1 winner `atr-k1.0-N20-m2`. Stage-2: refined DD shows zero in-sample alpha over ATR-only
- [x] Phase 41 — A/B + walk-forward validation. All 3 v9 scenarios FAIL VAL-03. Committed recommendation: **v6.0 HybridEngine + fail-safe retained as production** (D-21 fallback)

**Production baseline (as measured Phase 41):** CAGR 10.70%, MaxDD -28.63%, Sharpe_rf3 0.461 (vs v6.0 shipped memory: CAGR 11.5%, MaxDD -28.2% — drift to reconcile in v10.0).

**Artifacts:** `output/v9_ab_comparison.txt`, `output/v9_ab_scenarios.csv`, `analysis/validate_v9.py`

## Current Milestone: v10.0 VN Macro Filter + Baseline Reconciliation

**Goal:** Giảm MaxDD của v6.0 HybridEngine từ -28.6% xuống **dưới -20%** trên VN30 2015-2026 bằng cách tích hợp VN macro filter (DXY/EEM 20d z-scores + SBV regime), **sau khi** reconcile baseline drift (shipped 11.5% → measured 10.70%).

**Target features:**
- Baseline drift forensics: tìm commit nào gây drift CAGR 11.5% → 10.70% và SELL count 124 → 105, fix forward để có baseline sạch trước khi tối ưu
- Liquidity proxy data pipeline: cố định `data/vn_liquidity_proxy.csv` + `data/sbv_policy_events.csv` làm canonical input, regenerable
- Macro filter module: DXY 20d z-score, EEM 20d z-score, SBV regime (easing/neutral/tightening, 90-day decay), feature-gated với v6.0 parity khi off
- Walk-forward-native grid search: rolling windows trong chính grid search (không phải post-hoc), chỉ accept params có median degradation < 30%
- A/B + OOS validation với HARD gate
- Docs + dashboard update (chỉ khi gate pass)

**Success criteria (HARD gate — nếu fail = reject, giữ v6.0):**
- MaxDD < -20% AND CAGR ≥ reconciled baseline
- Walk-forward degradation < 30% qua tất cả rolling windows
- v6.0 parity duy trì khi filter off (regression test)

**Evidence driving this milestone (from quick task 260421-lb4, GO verdict):**
- DXY 20d z-score corr = -0.1909 với 20d forward VN30 returns (inverse, expected)
- EEM 20d z-score corr = +0.1911 với 20d forward VN30 returns
- SBV regime split: easing +31.84% CAGR (465 days) vs tightening -23.92% CAGR (84 days) — spread 55.76pp
- USD/VND + US10Y: near-zero correlation, exclude from feature set
- MANDATORY: walk-forward CV trong grid search (Phase 41 lesson, do not repeat)

## Completed: v8.0 Momentum Stock Selection (shipped 2026-04-13)

**Result: v8.0 TRAILS v7.0.** RS momentum (roc126) as stock selector does not outperform CANSLIM fundamentals.

**Target features (v8.0):**
- RS tự tính từ giá: IBD Weighted ROC (0.4×ROC63 + 0.2×ROC126/189/252) vs ROC 6 tháng đơn giản
- Stock filter: RS ≥ 70 (top 30% trong VN100) + N rule + Volume surge
- Entry confirmation: Option A/C giữ nguyên
- MDM gate: giữ nguyên
- Backtest đầy đủ 2016-2025, so sánh với v7.0 baseline

### Validated (v8.0) — shipped 2026-04-13

**Result: v8.0 TRAILS v7.0.** RS momentum (roc126) as stock selector does not outperform CANSLIM fundamentals.

- ✓ RS computation module: `compute_rs_panel` (IBD Weighted ROC + ROC-126, vectorized, cross-sectional percentile ranking) — Phase 35
- ✓ Parquet caching layer: `get_rs_rankings` wraps compute_rs_panel with disk cache keyed by formula/mode/date range — Phase 35
- ✓ MomentumScorer: `apply_momentum_thresholds` (RS≥70 + N rule, replaces CANSLIM C/A fundamentals, zero MySQL) — Phase 36
- ✓ v8 pipeline: `run_v8_backtest` + `build_momentum_raw_frame` in `_vn100_pipeline.py`, formula kwarg wired — Phase 36-37
- ✓ In-sample sweep 2016-2018 (216 configs): roc126 wins Sharpe_rf3=0.702, locked config written — Phase 37
- ✓ OOS validation 2019-2025: CAGR=10.0%, Sharpe=0.645, MaxDD=-24.9% — Phase 37
- ✓ Three-way comparison: v8.0 vs v7.0 (Sharpe=0.813) vs VN-Index B&H — Phase 37

**v8.0 OOS:** CAGR=10.0%, Sharpe_rf3=0.645, MaxDD=-24.9% (trails v7.0 Sharpe=0.813)
**Best model remains v7.0:** CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31%

### Active (v10.0)

- [ ] Baseline drift forensics — find commit(s) causing CAGR drift 11.5% → 10.70% and SELL count 124 → 105; fix forward
- [ ] Canonical liquidity proxy data pipeline — regenerable `data/vn_liquidity_proxy.csv` + `data/sbv_policy_events.csv` with publication-lag handling
- [ ] VN macro filter module — DXY 20d z-score + EEM 20d z-score + SBV regime (90-day decay), feature-gated with v6.0 parity when off
- [ ] Walk-forward-native grid search — rolling windows inside grid search, accept params only if median degradation < 30%
- [ ] A/B validation (baseline / +DXY / +EEM / +SBV-regime / +all) + OOS with HARD gate (MaxDD < -20% AND CAGR ≥ baseline)
- [ ] Docs + dashboard update — only if HARD gate passes

### Validated (v9.0) — shipped 2026-04-21 (results REJECTED, v6.0 retained)

- ✓ ATR Buffer Zone module (VT = SMA50 − k×ATR_N, m-day consecutive close) — Phase 38
- ✓ Refined Distribution Day module (dual-threshold: large_drop + vol-MA, small_drop + top-percentile) — Phase 39
- ✓ ATR parameter grid search (36 combos) in-sample 2015-2021 — Phase 40 (winner `atr-k1.0-N20-m2`)
- ✓ DD parameter grid search (54 combos) on locked ATR config — Phase 40 (winner `dd-L-0.007-S-0.003-P3`, 9-way tie, zero alpha over ATR-only)
- ✓ Selection pipeline: max Sharpe with MaxDD ≤ -30% constraint — Phase 40 (`analysis/select_v9_best.py`)
- ✓ A/B validation (baseline / +ATR / +DD / +both) — Phase 41 (all v9 scenarios FAIL milestone criterion)
- ✓ Walk-forward validation (Train 2015-2021 / Test 2022-2026) — Phase 41 (degradation +67% to +96%, breaches 50% threshold)
- ✓ Production Candidate recommendation committed: **v6.0 HybridEngine + fail-safe retained** — Phase 41 (D-21 fallback)

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
| v9.0 extensions rejected; v6.0 retained | Phase 41: all 3 v9 scenarios (+ATR, +DD, +both) fail CAGR ≥ 11.5% gate on 2015-2026; walk-forward degradation exceeds 50%. Phase 40 sweep winners were overfit to 2015-2021 train window | ✓ Good (evidence-based rejection) |
| v10.0 uses VN-native macro proxies (DXY/EEM/SBV regime), not US/Fed | Quick task 260421-lb4 GO verdict: DXY/EEM 20d z-scores show ±0.19 corr with 20d fwd VN30 returns; SBV regime spread 55.76pp CAGR. USD/VND + US10Y near-zero and excluded. SBV OMO raw data not publicly available → proxies are the pragmatic path | — Pending |
| v10.0 walk-forward CV in grid search (not post-hoc) | Phase 41 showed +67-96% degradation when tuning only on train window 2015-2021. Must rolling-validate inside grid search to avoid repeating overfit | — Pending |
| v10.0 HARD gate: MaxDD < -20% AND CAGR ≥ baseline | User explicit: fail the gate = reject, retain v6.0. No soft acceptance of "improvement on one dimension only" | — Pending |

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

**v10.0 progress (as of Phase 42 complete):**
- ✓ Phase 42 Baseline Reconciliation — bisect identified `f80394f` (Phase 38-02) as single drift commit; reconciled via `v60_strict_mode` preset flag (D-07 step 2). At reconciled HEAD: CAGR 11.47%, SELL 124, MaxDD -28.17% — all three D-09 parity bands pass. Canonical tuple published at `output/v10_reconciled_baseline.json` (schema_version: 1); 3/3 determinism tests green.

---
*Last updated: 2026-04-22 after Phase 42 Baseline Reconciliation complete (BASE-01/02/03)*
