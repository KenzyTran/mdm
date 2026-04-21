# Milestones

## v9.0 VN30 MDM Whipsaw Reduction (Shipped: 2026-04-21)

**Phases completed:** 4 phases (38-41), 11 plans, 22 tasks
**Timeline:** 2026-04-15 → 2026-04-21 (7 days)

**Summary:** Attempted to reduce whipsaw in v6.0 HybridEngine + fail-safe on VN30 via ATR Buffer Zone (for MA50 breakdown suppression) and Refined Distribution Day (dual-threshold vol-aware). Grid search selected `atr-k1.0-N20-m2` and `dd-L-0.007-S-0.003-P3` on 2015-2021 train. A/B + walk-forward validation on full 2015-2026 REJECTED all 3 v9 scenarios. v6.0 retained as production.

**Result: v9.0 extensions REJECTED on evidence.**

| Scenario | CAGR | MaxDD | Sharpe | Walk-fwd Degradation | Verdict |
|---|---|---|---|---|---|
| Baseline v6.0 | 10.70% | -28.63% | 0.461 | +35.4% | reference |
| +ATR | 8.78% | -33.40% | 0.369 | +96.4% | FAIL |
| +DD | 10.03% | -29.03% | 0.417 | +67.2% | FAIL |
| +both | 8.93% | -33.40% | 0.376 | +87.2% | FAIL |

**Key accomplishments:**
- ATR Buffer module (`strategies/mdm_hybrid/atr_buffer.py`) feature-gated with v6.0 parity — Phase 38
- Refined DD module (`strategies/mdm_hybrid/refined_dd.py`) dual-threshold vol-aware, feature-gated — Phase 39
- Sequential grid search pipeline (36 ATR + 54 DD runs, locked params JSON) — Phase 40
- Unified A/B + walk-forward + whipsaw diagnostic validation script (`analysis/validate_v9.py`, 651 lines) — Phase 41
- Production Candidate recommendation: `v6.0 HybridEngine + fail-safe remains production` (literal string in `output/v9_ab_comparison.txt`) — Phase 41

**Key learning (flagged for v10.0):**
- Grid search ONLY on train window → 67-96% degradation on OOS. Walk-forward CV must be INSIDE grid search, not post-hoc.
- Engine baseline drift: measured CAGR 10.70% vs shipped v6.0 memory 11.5%. Must reconcile before declaring any new production candidate.

---

## v7.0 CANSLIM + MDM on VN100 (Shipped: 2026-04-10)

**Phases completed:** 8 phases (28-34 + 999.1), 34 plans, 62 tasks
**Timeline:** 2026-04-08 → 2026-04-10 (2 days)
**Files changed:** 250 files, 53,598 insertions

**Summary:** Long-only CANSLIM stock picking on VN100 with MDM as capital allocation gate. Full end-to-end pipeline from data connectors through portfolio engine, backtested in-sample (2014-2018) and out-of-sample (2019-2025). Phase 999.1 added RS-ranked partial liquidation on MDM SELL.

**OOS Result (2019-2025, post-999.1):** CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31%

**Key accomplishments:**
- Postgres + MySQL connectors; VN100 data audit: 2936 stockcodes, 852 delisted, 16 EPS-sparse tickers
- CANSLIM scorer (C/A/N/S/L/I/M + liquidity), validated vs diem_canslim baseline (OOS rho=0.365)
- Entry confirmation: Option A (52w breakout) + Option C (Pocket Pivot), next-day ATO fills
- Multi-stock portfolio engine: max 8 positions, 8% hard stop, MA50 trailing stop, T+2 settlement, 0.35% costs
- OOS 2019-2025: CAGR=6.23%, Sharpe=0.448, MaxDD=-10.22% (pre-999.1); CAGR=10.18%, Sharpe=0.813, MaxDD=-16.31% (post-999.1)
- Key finding: CANSLIM alone Sharpe=1.047; MDM gate reduces to Sharpe=0.448 but cuts MaxDD from -40% to -10%
- RS-ranked partial liquidation (Phase 999.1): keep top 50% positions by RS on MDM SELL event

---

## v6.0 MDM Fail-Safe & Signal Refinement (Shipped: 2026-04-02)

**Phases completed:** 4 phases, 9 plans, 16 tasks

**Key accomplishments:**

- A/B backtest on VN30 shows fail-safe improves total return from 7.4% to 58.1% with max DD improving from -51.4% to -46.3%, but triggers during 2022 bear market
- MDMV2Config gains ma50_breakout_enabled + ma200_enabled flags, Indicators gains add_sma200_column, and 6 Wave-0 tests establish MAREVIEW coverage
- 200dma BUY crossover and SELL breakdown wired into V2 engine with MA50 breakout config-gated; all scenarios 4 and 5 now functional
- 5-scenario A/B test on VN30 2018-2026 showing REMOVE MA50 SELL trigger improves Sharpe 0.34->0.50 and return +38.4%
- ATR-14 volatility regime classifier with VN30 P25/P75 thresholds and VolatilityFilter suppression module
- ATR-based volatility filter wired into V2 engine/position manager with A/B validation showing 50-79% transition reduction in low-vol periods

---

## v5.0 Signal Quality & Macro Filter (Shipped: 2026-03-31)

**Phases completed:** 4 phases, 8 plans, 17 tasks

**Key accomplishments:**

- CASH->SELL transitions gated by suppress_sell parameter in position manager, wired to LiquidityLoader in V2 engine, with 4 integration tests and Vietnamese documentation
- SellAccelerationGate module with ROC/DD-clustering/volume-MA50 conditions gating CASH->SELL transitions in V2 engine
- Bear market A/B validation proving SELL acceleration gate does not delay critical signals (0-day delay in 2008) or degrade drawdown (improved in both 2022 periods), with rule documentation synced to code
- MA10/MA50 trend filter rejects weak FTDs, 3-day confirmation window with DD cancellation gates BUY entries in V2 engine
- A/B validation proves buy selectivity reduces NASDAQ trades by 13.2% and VN30 trades by 19.6%, with rule documentation updated in Vietnamese

---
