# Phase 25: MA50/200dma Review - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Evidence-based A/B testing to determine whether MA50 should remain in V2's SELL trigger and BUY filter logic, based on Dr. K's statement that MA50/200dma have "little value." Phase runs 5 structured scenarios comparing MA50-on baseline against variants that progressively remove MA50 uses, plus a 200dma replacement scenario. Delivers a quantitative report (MAREVIEW-03) recommending keep/remove/replace with VN30 backtest evidence.

This phase does NOT change QE floor, fail-safe, sell acceleration, buy selectivity, or stop loss behavior.

</domain>

<decisions>
## Implementation Decisions

### A/B Test Scenarios (5 total)
- **D-01:** 5 scenarios to run:
  1. **Baseline** — all MA50 uses on (`ma50_sell_enabled=True`, `buy_filter_enabled=True`, MA50 breakout buy on)
  2. **-SELL only** — `ma50_sell_enabled=False`; BUY filter and MA50 breakout buy remain active
  3. **-BUY filter only** — `buy_filter_enabled=False`; SELL trigger and MA50 breakout buy remain active
  4. **-All MA50** — all 3 MA50 uses disabled: `ma50_sell_enabled=False`, `buy_filter_enabled=False`, MA50 breakout buy off
  5. **+200dma replacement** — MA50 breakout buy replaced with 200dma crossover buy signal; MA50 SELL trigger replaced with `close < 200dma`

- **D-02:** In scenarios 2 and 3 (single-use removal), MA50 breakout buy signal stays active — each test isolates one MA50 role at a time.

### 200dma Implementation
- **D-03:** 200dma is not in the current codebase. Scenario 5 requires:
  - Add `sma200` indicator computation to `Indicators`
  - Add a config flag: `ma200_enabled: bool = False` (default OFF per v5.0 convention)
  - Replace `check_ma50_breakout()` logic with `close > sma200` crossover for buy signal
  - Replace `ma50_sell_enabled` trigger with `close < sma200` for SELL trigger in Scenario 5

### SELL Trigger When MA50 Removed
- **D-04:** When `ma50_sell_enabled=False`, the SELL trigger falls back to `cash_deterioration_days` only — no new trigger added. A/B measures the delta of MA50-less + deterioration-only approach.

### Validation Script
- **D-05:** Single script `analysis/validate_ma50_review.py` following Phase 24's `validate_buy_entry.py` pattern — runs all 5 scenarios, prints per-scenario metrics (total return, max DD, Sharpe, win rate), and outputs MAREVIEW-03 recommendation section comparing all results.

### Report Structure (MAREVIEW-03)
- **D-06:** Report concludes with one of three actions: keep MA50 as-is / remove MA50 / replace MA50 with 200dma — with quantitative evidence from all 5 scenarios.

### Claude's Discretion
- Exact implementation of `sma200` (rolling 200-day close mean, same pattern as `ma50`)
- Config parameter naming for 200dma threshold and enable flags
- How to handle 200dma not being available for first 200 bars
- Validation script output formatting and per-scenario table layout
- Whether to add per-scenario result columns to trades DataFrame

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### MA50 implementation targets (all 3 use sites)
- `strategies/mdm_v2/position_manager.py` §"CASH→SELL: MA50 breakdown" (~line 200-208) — MA50 SELL trigger logic
- `strategies/mdm_v2/buy_filter.py` — BuyFilter.check() MA10/MA50 trend filter for FTD gate
- `strategies/mdm_v2/ftd_signal.py` — check_ma50_breakout() MA50 crossover buy signal
- `strategies/mdm_v2/config.py` — MDMV2Config: `ma50_sell_enabled`, `buy_filter_enabled`, `ma50_breakout_correction` flags

### Engine orchestration
- `strategies/mdm_v2/mdm_v2_engine.py` — MA50 indicator setup (line ~96-101), BUY gate at line ~237-241, MA50 breakout detection at line ~192-200

### Indicator layer (200dma needs to be added here)
- `strategies/mdm_v2/indicators.py` — `add_ma50_column()` pattern to follow for `add_sma200_column()`

### Validation patterns to follow
- `analysis/validate_buy_entry.py` — Phase 24 multi-scenario A/B structure (primary reference)
- `analysis/validate_sell_acceleration.py` — Phase 20 A/B pattern (secondary reference)

### Documentation (update target)
- `docs/rules_mdm_v2.md` — Must be updated to reflect MA50 review findings and any logic changes

### Requirements
- `.planning/REQUIREMENTS.md` — MAREVIEW-01, MAREVIEW-02, MAREVIEW-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MDMV2Config.ma50_sell_enabled` and `buy_filter_enabled` flags already exist — scenarios 2 and 3 are flag toggles, no new code needed for those
- `Indicators.add_ma50_column()` — exact pattern to copy for `add_sma200_column()`
- `analysis/validate_buy_entry.py` — complete multi-scenario A/B framework: config per scenario, run engine, collect metrics, compare

### Established Patterns
- New config flags default OFF for backward compatibility (v5.0 decision, applies to `ma200_enabled`)
- A/B validation: create MDMV2Config variants, run `MDMV2Engine.run()` per scenario, use `V2PerformanceAnalyzer` for metrics
- MA50 breakout buy flag needs to be added to config (currently no `ma50_breakout_enabled` flag — the signal is always active if MA50 data exists)

### Integration Points
- `strategies/mdm_v2/indicators.py` — add `add_sma200_column()` here
- `strategies/mdm_v2/config.py` — add `ma50_breakout_enabled: bool = True` (to gate Scenario 4) and `ma200_enabled: bool = False` (for Scenario 5)
- `strategies/mdm_v2/ftd_signal.py` — gate `check_ma50_breakout()` on `ma50_breakout_enabled` config flag
- `strategies/mdm_v2/position_manager.py` — add 200dma SELL path for Scenario 5
- `analysis/validate_ma50_review.py` — new file, script entry point for all 5 scenarios

</code_context>

<specifics>
## Specific Ideas

- Dr. K's quote: "MA50/200dma have little value" in signal model — this is the direct motivation for Phase 25
- 200dma scenario is a full replacement (both buy and sell) — not just adding it alongside MA50
- In scenarios 2 and 3 (partial removal), MA50 breakout buy stays on to isolate the individual impact

</specifics>

<deferred>
## Deferred Ideas

- ATR-based or DD-count-based replacement SELL trigger — if MAREVIEW-03 shows MA50 removal is bad AND 200dma doesn't improve it, this could be Phase 26 scope (currently Phase 26 = Banding/Volatility Filter)
- Optimizing `cash_deterioration_days` threshold when MA50 SELL is removed — out of scope, would be a parameter sweep

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 25-ma50-200dma-review*
*Context gathered: 2026-04-01*
