---
gsd_state_version: 1.0
milestone: v8.0
milestone_name: Momentum Stock Selection
status: verifying
stopped_at: Completed 35-02-PLAN.md
last_updated: "2026-04-10T09:36:30.953Z"
last_activity: 2026-04-10
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 9
  completed_plans: 9
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-10)

**Core value:** Discover MDM rules + apply as capital allocation gate for pure momentum stock picking on VN100.
**Current focus:** Phase 35 — rs-module

## Current Position

Phase: 35 (rs-module) — EXECUTING
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-04-10

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 35 P01 | 3min | 2 tasks | 6 files |
| Phase 35 P02 | 2min | 1 tasks | 2 files |

## Data Sources (verified 2026-04-08)

**Postgres (vpt_wong_stock_v1, TA):**

- stock_eod: 5.9M rows, 2936 stocks, through 2026-04-08
- stock_rs (rss/rsm/rsl): coverage from 2022-03-14 only
- nganh_rs, nhnl_indicator, index_eod, stock_list, stock_signals

**MySQL (stocks_backend, Fundamentals):**

- NOT needed for v8.0 — replaced by price-computed RS

## Accumulated Context

### Decisions (v7.0 -> v8.0 pivot)

- CANSLIM fundamental (C/A rules: EPS YoY, EPS CAGR) replaced by RS momentum — removes MySQL dependency
- RS computed cross-sectionally within VN100 from OHLC price data
- Two RS formulas to compare: IBD Weighted ROC vs ROC 6-month
- N rule (near 52-week high) + Volume surge at entry retained as TA filters
- stock_rs DB data only from 2022 — not usable as primary RS source for backtest from 2016
- MDM gate unchanged: HybridEngine + fail-safe on VNINDEX
- Pyramiding: max 2 buys per ticker, 30% NAV cap per ticker
- Hard stop: 8%, no window limit (buy for full MDM BUY period)
- [P35-01] Used fill_method=None in pct_change to avoid pandas FutureWarning deprecation
- [P35-01] Excluded NaN rows (insufficient history) from RS output rather than returning NaN ranks
- [P35-02] Lazy imports for DB connectors inside get_rs_rankings to avoid import-time DB dependency
- [P35-02] 400 calendar day pre-start warm-up to cover 252 trading day lookback for RS computation

### v7.0 Baseline (for comparison)

- OOS 2019-2025: CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31%
- VN-Index B&H: CAGR=10.42%, Sharpe=0.383, MaxDD=-40.34%
- CANSLIM-only (no MDM gate): Sharpe=1.047, CAGR=16.4%

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-04-10T09:36:30.945Z
Stopped at: Completed 35-02-PLAN.md
Resume file: None
