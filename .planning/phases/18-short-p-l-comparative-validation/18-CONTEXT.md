# Phase 18: Short P&L & Comparative Validation - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Short position P&L is tracked correctly in the equity curve (inverse return when SELL), backtest comparison report shows long-only vs long/short performance on both NASDAQ and VN30, and rule documentation files are updated with short signal rules and stop loss changes from Phases 16-17. This phase does NOT add new trading logic — it measures and documents what Phases 16-17 built.

</domain>

<decisions>
## Implementation Decisions

### Short P&L in equity curve
- **D-01:** Equity curve uses inverse return when prev_state=SELL: `equity[i] = equity[i-1] * (close[i-1] / close[i])`. Gain when market drops, loss when market rises.
- **D-02:** Single blended equity curve (not separate long/short curves). All metrics (Sharpe, drawdown, win rate, total return) computed from the blended curve.
- **D-03:** Modify existing `V2PerformanceAnalyzer._build_daily_equity()` in `strategies/mdm_hybrid/performance.py` — add `elif prev_state == 'SELL'` branch.

### Comparison report format
- **D-04:** Python script (not notebook) that outputs metrics table + matplotlib chart. Consistent with Phase 5 approach (`analysis/validate_v2.py` pattern).
- **D-05:** Chart shows 2 equity curves on same plot: long-only vs long/short. Metrics table shows side-by-side: total return, annualized return, max drawdown, Sharpe ratio, win rate.
- **D-06:** Single script handles both NASDAQ and VN30 via market parameter. Outputs 2 charts + 2 metrics tables (one per market). Reuses code, no duplication.

### Rule docs update scope
- **D-07:** Add new sections to both `docs/rules_mdm_v2.md` and `docs/rules_mdm_hybrid.md` covering: short entry/cover rules, stop loss 1.5% + adaptive scaling, short stop loss (DD5 high), SELL->CASH->BUY transition enforcement.
- **D-08:** Keep existing doc structure — append sections, don't rewrite. Minimal disruption to existing content.

### VN30 short parameters
- **D-09:** NASDAQ and VN30 use identical short logic (inverse return in equity curve). Differences handled by existing config (stop loss thresholds, MA periods). No VN30-specific short code needed.

### Claude's Discretion
- Long-only backtest mode implementation: config flag to disable short returns (treat SELL as CASH for comparison), or run engine twice with different configs
- Chart styling, colors, layout details
- Exact structure of new rule doc sections (headings, formatting)
- Whether to include per-trade short P&L breakdown in the comparison report
- Script file naming and location in `scripts/` or `analysis/`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Performance analyzer (modification target)
- `strategies/mdm_hybrid/performance.py` — V2PerformanceAnalyzer with _build_daily_equity() at line 70, currently treats SELL as 0% invested at line 91
- `strategies/mdm_hybrid/position_manager.py` — V2PositionManager with cover_short() and short P&L calculation
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — HybridEngine producing results DataFrame with state column

### Rule docs (update targets)
- `docs/rules_mdm_v2.md` — V2 engine rule documentation, needs short signal sections
- `docs/rules_mdm_hybrid.md` — Hybrid engine rule documentation, needs short signal sections

### Existing comparison patterns
- `analysis/validate_v2.py` — Three-way comparison script pattern (reuse for long-only vs long/short)
- `strategies/mdm_v2/performance.py` — V2 performance analyzer (same class, may need same update)

### Prior phase context
- `.planning/phases/16-short-position-state-transitions/16-CONTEXT.md` — D-03 (short P&L formula), D-04-D-06 (cover triggers), D-10 (short_mode config)
- `.planning/phases/17-stop-loss-risk-management/` — Stop loss 1.5%, ATR adaptive, DD5 high short stop loss

### Requirements
- `.planning/REQUIREMENTS.md` — SHORT-02 (short P&L tracking), TRANS-02 (long-only vs long/short comparison), TRANS-03 (rule docs update)

### Data
- `data/signals/nasdaq_signals_full.csv` — 962-signal ground truth
- NASDAQ and VN30 OHLCV data via DataLoader

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `V2PerformanceAnalyzer` — extend `_build_daily_equity()` for short returns (D-01)
- `analysis/validate_v2.py` — comparison script pattern with matplotlib charts
- `HybridEngine.run()` — produces DataFrame with `state` column (BUY/CASH/SELL)
- `scripts/run_hybrid_backtest.py` — entry point pattern for NASDAQ backtest
- Existing VN30 config and data loading from Phase 6

### Established Patterns
- DataFrame-centric: engine.run(df) returns DataFrame with signal columns
- Performance analyzer: takes results_df + trades list, computes all metrics via summary()
- Script pattern: load data, run engine, analyze, output report + chart
- Config-driven: HybridConfig with market-specific parameter sets

### Integration Points
- `performance.py` line 91: `equity[i] = equity[i-1]` for SELL — change to inverse return
- `position_manager.py` cover_short(): already computes per-trade P&L
- Config: may need `long_only_mode` flag or similar to run comparison
- Rule docs: append new sections after existing content

</code_context>

<specifics>
## Specific Ideas

- Phase 5 validation script pattern is the reference for comparison report format
- Blended single equity curve keeps things simple — no separate short tracking needed
- Rule docs should document in Vietnamese (consistent with existing docs/rules_mdm_hybrid.md format)

</specifics>

<deferred>
## Deferred Ideas

- Separate short-only equity curve analysis — future enhancement if needed to isolate short contribution
- Inverse ETF decay modeling for NASDAQ — future enhancement
- Interactive notebook for comparison exploration — could add later if script isn't enough
- Anti-whipsaw / cooldown logic for short transitions — FUT-03

</deferred>

---

*Phase: 18-short-p-l-comparative-validation*
*Context gathered: 2026-03-30*
