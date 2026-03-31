# Milestones

## v5.0 Signal Quality & Macro Filter (Shipped: 2026-03-31)

**Phases completed:** 4 phases, 8 plans, 17 tasks

**Key accomplishments:**

- CASH->SELL transitions gated by suppress_sell parameter in position manager, wired to LiquidityLoader in V2 engine, with 4 integration tests and Vietnamese documentation
- SellAccelerationGate module with ROC/DD-clustering/volume-MA50 conditions gating CASH->SELL transitions in V2 engine
- Bear market A/B validation proving SELL acceleration gate does not delay critical signals (0-day delay in 2008) or degrade drawdown (improved in both 2022 periods), with rule documentation synced to code
- MA10/MA50 trend filter rejects weak FTDs, 3-day confirmation window with DD cancellation gates BUY entries in V2 engine
- A/B validation proves buy selectivity reduces NASDAQ trades by 13.2% and VN30 trades by 19.6%, with rule documentation updated in Vietnamese

---
