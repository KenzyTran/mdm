---
phase: 33-out-of-sample-sensitivity
plan: 03
subsystem: backtest
tags: [canslim, sensitivity, universe, sql, baseline, verdict]

requires:
  - phase: 33-01
    provides: "OOS backtest results (oos_metrics.json, oos_nav.csv)"
  - phase: 33-02
    provides: "Sensitivity matrix framework, baselines, verdict template"
provides:
  - "Fixed liquidity-reconstructed universe mode (closeprice SQL fix)"
  - "Fixed canslim_only baseline with periodic CASH->BUY transitions"
  - "Complete 9-row sensitivity matrix with all non-NaN values"
  - "Valid verdict.md failure attribution using real baseline data"
affects: [phase-34, canslim-scoring, mdm-gate-policy]

tech-stack:
  added: []
  patterns: ["Periodic CASH->BUY gate tiling for always-open entry windows"]

key-files:
  created: []
  modified:
    - strategies/canslim/universe.py
    - analysis/sensitivity_vn100.py
    - docs/audits/phase33/sensitivity_matrix.csv
    - docs/audits/phase33/baselines.json
    - docs/audits/phase33/verdict.md

key-decisions:
  - "CANSLIM-only baseline Sharpe=1.047 (109 trades) proves stock selection generates strong alpha without MDM gate"
  - "MDM gate identified as primary Sharpe bottleneck: Strategy 0.448 < CANSLIM-only 1.047"
  - "Liquidity-reconstructed universe has much worse Sharpe (0.052-0.064) vs current-vn100 (0.381-0.448)"
  - "Periodic CASH->BUY tiling (every 19 bars) creates 99.9% period coverage for always-open baseline"

patterns-established:
  - "Gate override for baselines: periodic CASH insert every (window_days-1) bars to tile buy windows"

requirements-completed: [BT-03, BT-04, BT-08]

duration: 7min
completed: 2026-04-10
---

# Phase 33 Plan 03: Gap Closure Summary

**Fixed SQL column bug (closeindex->closeprice) and canslim_only baseline (periodic CASH->BUY tiling), proving CANSLIM stock selection generates Sharpe 1.047 without MDM gate**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-10T03:53:46Z
- **Completed:** 2026-04-10T04:00:17Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Fixed SQL column bug in `_liquidity_reconstructed()`: `closeindex` (index_eod column) replaced with `closeprice` (stock_eod column), enabling valid liquidity-reconstructed universe mode
- Fixed canslim_only baseline: periodic CASH->BUY transitions every 19 bars create 92 overlapping buy windows covering 99.9% of OOS period (was producing 0 trades due to single all-BUY series with no transitions)
- Regenerated all artifacts: sensitivity_matrix.csv (9 rows, all non-NaN), baselines.json (canslim_only: 109 trades, Sharpe=1.047, CAGR=16.4%), verdict.md (correct failure attribution)
- Key insight: CANSLIM stock selection alone (Sharpe 1.047) far exceeds VN-Index B&H (0.383), but MDM gate reduces it to 0.448 -- MDM gate is the primary bottleneck, not CANSLIM scoring

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix SQL column bug + canslim_only baseline transition, re-run sensitivity** - `96084c9` (fix)
2. **Task 2: Validate regenerated verdict.md failure attribution** - validation only, no code changes needed

## Files Created/Modified
- `strategies/canslim/universe.py` - Fixed closeindex -> closeprice in _liquidity_reconstructed SQL
- `analysis/sensitivity_vn100.py` - Added periodic CASH->BUY gate tiling in run_canslim_only_baseline
- `docs/audits/phase33/sensitivity_matrix.csv` - Full 9-row matrix, liquidity-reconstructed rows now have real Sharpe values
- `docs/audits/phase33/baselines.json` - canslim_only: 109 trades, Sharpe=1.047, CAGR=16.4%, MaxDD=-32.2%
- `docs/audits/phase33/verdict.md` - Updated failure attribution: MDM gate is primary bottleneck

## Decisions Made
- CANSLIM-only baseline Sharpe=1.047 proves stock selection generates strong alpha without MDM gate
- MDM gate identified as primary Sharpe bottleneck (Strategy 0.448 < CANSLIM-only 1.047)
- Liquidity-reconstructed universe has much worse risk-adjusted returns (Sharpe 0.052-0.064) vs current-vn100 (0.381-0.448) -- current-vn100 remains preferred universe mode
- Used periodic CASH tiling (every 19 bars) instead of single CASH at bar 0, because a single transition only opens one 20-bar window out of 1749 bars

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Periodic CASH->BUY tiling instead of single CASH at iloc[0]**
- **Found during:** Task 1 (canslim_only baseline fix)
- **Issue:** Plan specified `all_buy.iloc[0] = "CASH"` but this creates only ONE 20-bar buy window out of 1749 bars. EntryEngine only accepts entries within buy windows, so 99% of the period had no entry eligibility, producing 0 trades.
- **Fix:** Insert CASH every 19 bars (`for i in range(0, len(all_buy), 19): all_buy.iloc[i] = "CASH"`) creating 92 overlapping windows with 99.9% coverage.
- **Files modified:** analysis/sensitivity_vn100.py
- **Verification:** 109 trades, Sharpe=1.047, CAGR=16.4%
- **Committed in:** 96084c9

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for canslim_only baseline to produce meaningful results. Without this, the baseline would still show 0 trades.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 33 is complete: all 3 plans executed, OOS backtest + sensitivity + gap closure done
- Key finding: MDM gate is the primary bottleneck for Sharpe uplift (reduces CANSLIM-only 1.047 to 0.448)
- Next phase should focus on MDM gate policy adaptation for VN market (reduce CASH periods that miss VN bull runs)
- BT-08 overall verdict remains FAIL (Sharpe uplift +0.064 < target +0.20)

---
*Phase: 33-out-of-sample-sensitivity*
*Completed: 2026-04-10*

## Self-Check: PASSED

- All 5 key files verified present on disk
- Commit 96084c9 verified in git log
