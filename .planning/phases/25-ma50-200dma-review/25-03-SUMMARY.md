---
phase: 25-ma50-200dma-review
plan: 03
subsystem: analysis
tags: [ma50, 200dma, backtesting, ab-test, validation, vn30, sharpe]

# Dependency graph
requires:
  - phase: 25-02
    provides: 200dma wiring in mdm_v2_engine.py, config flags ma50_breakout_enabled and ma200_enabled

provides:
  - analysis/validate_ma50_review.py: 5-scenario A/B validation script with quantitative recommendation
  - MAREVIEW-03 recommendation: REMOVE MA50 SELL trigger (Sharpe 0.34->0.50, return +38.4%)
  - docs/rules_mdm_v2.md: Updated with actual backtest results and evidence-based recommendation

affects: [phase-27-integration, combined-validation, default-config-update]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "5-scenario A/B validation pattern: each scenario varies exactly one MA50 flag"
    - "Sharpe ratio as primary recommendation metric (risk-adjusted, per Research Pitfall 6)"

key-files:
  created:
    - analysis/validate_ma50_review.py
  modified:
    - docs/rules_mdm_v2.md

key-decisions:
  - "MAREVIEW-03: REMOVE MA50 SELL trigger (4_no_ma50_all Sharpe=0.35 > baseline 0.34, MaxDD -34.2% vs -47.9%)"
  - "2_no_ma50_sell (Sharpe=0.50) shows MA50 SELL trigger is primary drag on VN30 performance"
  - "Buy filter (MA10<MA50) retains value -- 3_no_buy_filter Sharpe=0.25 is worst scenario"
  - "Change not applied to default config -- will integrate in Phase 27 combined validation"
  - "Pre-existing test failure in test_hybrid_engine.py (not caused by this plan's changes)"

patterns-established:
  - "Validation scripts follow validate_buy_entry.py pattern: same imports, PERIODS, WARMUP_DAYS, run_backtest, compute_metrics"
  - "print_recommendation() compares keep/remove/replace by Sharpe, prints evidence-based output"

requirements-completed: [MAREVIEW-01, MAREVIEW-02, MAREVIEW-03]

# Metrics
duration: 16min
completed: 2026-04-01
---

# Phase 25 Plan 03: MA50/200dma Review Validation Summary

**5-scenario A/B test on VN30 2018-2026 showing REMOVE MA50 SELL trigger improves Sharpe 0.34->0.50 and return +38.4%**

## Performance

- **Duration:** 16 min
- **Started:** 2026-04-01T06:29:03Z
- **Completed:** 2026-04-01T06:45:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `analysis/validate_ma50_review.py` with 5-scenario A/B validation following Phase 24 pattern
- Script runs all 5 scenarios on VN30 and prints comparison table with return, MaxDD, Sharpe, trades, win rate
- MAREVIEW-03 recommendation section identifies best scenario by Sharpe and outputs evidence-based verdict
- Updated `docs/rules_mdm_v2.md` Section XVI with actual backtest results and recommendation

## Task Commits

1. **Task 1: Create validation script with 5 scenarios and report** - `3237a2e` (feat)
2. **Task 2: Update rules documentation with MA50 review findings** - `9363b8d` (docs)

## Files Created/Modified

- `analysis/validate_ma50_review.py` - 5-scenario A/B validation: baseline, no_ma50_sell, no_buy_filter, no_ma50_all, 200dma_replace
- `docs/rules_mdm_v2.md` - Section XVI updated with actual results and MAREVIEW-03 recommendation

## Decisions Made

- MAREVIEW-03 recommendation: REMOVE MA50 SELL trigger. Evidence: `2_no_ma50_sell` Sharpe=0.50 vs baseline 0.34; `4_no_ma50_all` also beats baseline on both Sharpe and MaxDD
- Buy filter (MA10<MA50) retains value -- `3_no_buy_filter` is worst scenario (Sharpe=0.25). When integrating in Phase 27, should keep `buy_filter_enabled=True`
- Change not applied to default config yet -- Phase 27 will handle combined integration decision

## Scenario Results (VN30 2018-2026)

```
Scenario                   Return      MaxDD   Sharpe   Trades    WinRate
-------------------------------------------------------------------------
1_baseline                  52.8%     -47.9%    0.34       75      28.0%
2_no_ma50_sell              91.2%     -40.5%    0.50       67      31.3%
3_no_buy_filter             29.6%     -46.7%    0.25       88      33.0%
4_no_ma50_all               47.8%     -34.2%    0.35       74      29.7%
5_200dma_replace            37.7%     -34.8%    0.29       76      30.3%
```

**RECOMMENDATION: REMOVE MA50 from signal logic.** (best Sharpe in keep/remove/replace comparison)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-existing test failure: `tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq` fails with 88.49% < 95% threshold. Verified this failure exists before any changes from this plan. Out of scope per deviation rules -- logged to deferred items.

## Next Phase Readiness

- Phase 25 is complete: all 3 plans done (CONTEXT, ENGINE, VALIDATION)
- Key finding for Phase 27 integration: set `ma50_sell_enabled=False` but keep `buy_filter_enabled=True`
- MAREVIEW-01/02/03 all verified

---
*Phase: 25-ma50-200dma-review*
*Completed: 2026-04-01*

## Self-Check: PASSED

- FOUND: analysis/validate_ma50_review.py
- FOUND: docs/rules_mdm_v2.md
- FOUND: .planning/phases/25-ma50-200dma-review/25-03-SUMMARY.md
- FOUND commit: 3237a2e (feat: create MA50/200dma review validation script)
- FOUND commit: 9363b8d (docs: update rules_mdm_v2 with MA50 review findings)
