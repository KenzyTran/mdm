# Milestones

## v7.0 CANSLIM + MDM on VN100 (Shipped: 2026-04-10)

**Phases completed:** 7 phases (28-34), ~18 plans

**Summary:** CANSLIM + MDM on VN100 -- 7 phases (28-34), portfolio engine with 5-way benchmark comparison. OOS result: CAGR=6.23%, Sharpe_rf3=0.448, MaxDD=-10.22%.

**Key accomplishments:**

- Database connectors: Postgres (TA), MySQL (fundamentals) with sqlalchemy
- VN100 universe loader with 3 modes: current-vn100, liquidity-reconstructed, vn30-only
- CANSLIM scorer: C/A/N/S/L/I/liq boolean rules + composite score (0.70 bool + 0.30 RS)
- Entry confirmation: Option A (pivot breakout) and Option C (pocket pivot) union feed
- Multi-stock long-only portfolio engine: max 8 slots, event-driven, T+2.5, 7% limit
- MDM capital allocation gate from HybridEngine + fail-safe (best v6.0 model)
- In-sample sweep (Phase 32): rank-1 params selected (c_yoy=0.25, slots=5, entry=C)
- OOS validation (Phase 33): BT-08 FAIL on Sharpe uplift, PASS on MaxDD reduction
- Key finding: CANSLIM is alpha source (Sharpe 1.047), MDM reduces Sharpe but cuts MaxDD 74.7%
- Documentation: rules_canslim_mdm.md, data_dictionary.md, retrospective entry

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
