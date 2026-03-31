# Phase 22: Combined Integration & Validation - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

All three v5.0 filters (QE floor, SELL acceleration, BUY selectivity) operating together without conflict. Validated end-to-end with A/B backtest comparison (baseline vs all-filters-on), walk-forward out-of-sample validation, CASH duration guard, integration test for all 8 filter combinations, and S3 dashboard update. This phase does NOT add new filters or change individual filter logic.

</domain>

<decisions>
## Implementation Decisions

### A/B Comparison
- **D-01:** Compare V2 baseline (all filters OFF) vs V2+all_filters (all ON) only. No intermediate combos in the A/B report — those are covered by the 8-combo integration test.
- **D-02:** New script `analysis/validate_combined.py` following `validate_sell_acceleration.py` pattern. Runs on both NASDAQ and VN30.
- **D-03:** Metrics: total return, CAGR, max drawdown, Sharpe ratio, trade count — side-by-side for baseline vs all-on.
- **D-04:** Walk-forward validation integrated in the same script (pre-2020 train, 2020-2026 test). Report includes out-of-sample degradation percentage with WARNING if > 10%.

### CASH Duration Guard
- **D-05:** CASH duration measured as average number of days in CASH state per period. Computed in `validate_combined.py` for both baseline and all-on.
- **D-06:** Report prints WARNING if all-on CASH duration exceeds 130% of baseline CASH duration. Not a hard failure — informational WARNING.

### 8-Combo Integration Test
- **D-07:** Parametrized pytest with `@pytest.mark.parametrize` over 8 combinations (True/False for qe_floor, sell_acceleration, buy_filter).
- **D-08:** Each combo runs backtest on NASDAQ 2008 and 2022 sub-periods. Assert max drawdown is not worse than V2 baseline for each sub-period.
- **D-09:** NASDAQ only — VN30 lacks 2008 data, and NASDAQ provides sufficient coverage for both bear market regimes.

### Dashboard Update
- **D-10:** Extend existing `scripts/export_dashboard_data.py` to include filter-on performance metrics (total return, Sharpe with all filters enabled).
- **D-11:** Add Global Liquidity overlay chart data to dashboard export — liquidity index plotted over price chart with QE floor active zones highlighted.
- **D-12:** Deploy via existing `scripts/deploy_dashboard.sh` and `scripts/update_dashboard.sh` — no new deployment scripts needed.

### Claude's Discretion
- Exact chart formatting for Global Liquidity overlay (color, opacity, annotation style)
- Test file naming and location within tests/
- validate_combined.py output format (console print, text file, or both)
- How to highlight QE floor active zones on the liquidity overlay chart
- Whether to add equity curve chart comparing baseline vs all-on in the report

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Filter modules (integration targets)
- `strategies/mdm_v2/liquidity.py` — QE floor filter, suppress_sell logic
- `strategies/mdm_v2/sell_acceleration.py` — SellAccelerationGate, acceleration_met boolean
- `strategies/mdm_v2/buy_filter.py` — BuyFilter, MA10/MA50 rejection
- `strategies/mdm_v2/buy_confirmation.py` — BuyConfirmation, N-day confirmation window
- `strategies/mdm_v2/config.py` — MDMV2Config with all enable flags and thresholds
- `strategies/mdm_v2/mdm_v2_engine.py` — MDMV2Engine.run() with filter wiring

### Validation patterns (script templates)
- `analysis/validate_sell_acceleration.py` — A/B bear market validation script pattern to follow
- `analysis/validate_buy_selectivity.py` — BUY selectivity validation with walk-forward
- `analysis/validate_v2.py` — Original V2 validation script

### Dashboard (update targets)
- `scripts/export_dashboard_data.py` — Dashboard data export to extend
- `scripts/deploy_dashboard.sh` — S3 deployment script
- `scripts/update_dashboard.sh` — S3 update script

### Rule documentation
- `docs/rules_mdm_v2.md` — V2 rule docs (reference for filter behavior descriptions)

### Requirements
- `.planning/REQUIREMENTS.md` — VAL-05 (A/B backtest), VAL-06 (dashboard update), VAL-07 (walk-forward validation)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `validate_sell_acceleration.py` — Direct template for A/B comparison script structure (bear market sub-period extraction, metrics comparison, console output)
- `validate_buy_selectivity.py` — Walk-forward validation pattern (pre-2020/2020-2026 split, degradation measurement)
- `export_dashboard_data.py` — Existing dashboard export pipeline (S3 data format, chart data structure)
- `MDMV2Config` — All three filter enable flags already exist (`qe_floor_enabled`, `sell_acceleration_enabled`, `buy_filter_enabled`, `buy_confirmation_enabled`)

### Established Patterns
- Config toggle pattern: each filter has an `_enabled` boolean flag defaulting to OFF
- Engine computes condition booleans, passes to position_manager (suppress_sell, acceleration_met, is_ftd filtering)
- Validation scripts follow consistent pattern: load data, run engine twice (baseline + variant), compare metrics
- S3 dashboard uses export script -> deploy script pipeline

### Integration Points
- `validate_combined.py` imports MDMV2Engine and runs it with different config settings
- Dashboard export extends existing JSON/CSV data format for S3
- Pytest parametrize uses MDMV2Config with toggled booleans
- Global Liquidity data from `data/global_liquidity.csv` (987 weekly observations, 2007-2026)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-combined-integration-validation*
*Context gathered: 2026-03-31*
