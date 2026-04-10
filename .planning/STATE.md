---
gsd_state_version: 1.0
milestone: v6.0
milestone_name: MDM Fail-Safe & Signal Refinement
status: verifying
stopped_at: Completed 33-02-PLAN.md
last_updated: "2026-04-10T03:18:14.486Z"
last_activity: 2026-04-10
progress:
  total_phases: 12
  completed_phases: 11
  total_plans: 39
  completed_plans: 39
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-08)

**Core value:** Long-only CANSLIM stock picking trên VN100, dùng MDM làm capital allocation gate.
**Current focus:** Phase 33 — out-of-sample-sensitivity

## Current Position

Phase: 33 (out-of-sample-sensitivity) — EXECUTING
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-04-10

## Data Sources (verified 2026-04-08)

**Postgres (vpt_wong_stock_v1, TA):**

- stock_eod: 5.9M rows, 2936 stocks, through 2026-04-08
- stock_rs, nganh_rs, nhnl_indicator, index_eod, stock_list, stock_signals

**MySQL (stocks_backend, Fundamentals):**

- ratios_stock (EPS, growth, P/E, ROE, market cap)
- is_quarter_nonbank/bank/insurance/stock (income statement quarterly)
- tm_quarter_* (balance sheet)
- rank_top_stocks (has existing diem_canslim — baseline for comparison)

**Redis (live/recent cache):** for live signal phase only, not historical backtest.

## Accumulated Context

### Decisions (v7.0)

- Universe: VN100 static (no point-in-time data available)
- Long-only, max 8 concurrent positions
- Event-driven (not periodic rebalance)
- MDM signal source: HybridEngine + fail-safe (best v6.0 model = +239%)
- MDM BUY is necessary but NOT sufficient — must wait for stock-level entry confirmation (pivot buy point)
- MDM determines capital allocation ratio (exact policy: TBD in planning)
- Postgres primary for TA, MySQL for fundamentals, Redis deferred to live-signal phase

### Decisions (Phase 33, Plan 01)

- D-03 fixed: canslim_raw cache path derived from panel min/max date to prevent OOS from reusing in-sample fundamentals
- D-06 fixed: precompute_static gains mode param (default current-vn100) so sensitivity runs across universe modes don't collide in cache
- OOS results (rank-1, 2019-2025): CAGR=6.23%, Sharpe_rf3=0.448, MaxDD=-10.22%, 62 trades

### Decisions (Phase 33, Plan 02)

- BT-08 FAIL: Sharpe uplift +0.064 (target >0.20 FAIL); MaxDD reduction 74.7% (target >30% PASS); Overall FAIL
- CANSLIM scoring is primary bottleneck: CANSLIM-only baseline shows 0 trades, stock selection alone does not generate alpha
- MDM timing is sound: MDM-only-on-index achieves Sharpe=0.508 (+0.125 uplift vs B&H), exceeding the BT-08 target
- VN-Index B&H benchmark: CAGR=10.42%, Sharpe=0.383, MaxDD=-40.34% for 2019-2025
- diem_canslim OOS: 24 quarters, median rho=0.365 (better than in-sample 0.280) — scorer generalizes well OOS
- liquidity-reconstructed mode failed (SQL schema bug: closeindex column) — deferred to future fix

### Open Questions

- Exact MDM capital allocation policy (BUY=100%, CASH=?%, SELL=0%?)
- Stock-level entry confirmation mechanism (FTD-per-stock? base breakout? pivot + volume?)
- Backtest start date (data coverage on fundamentals — verify in phase 1)
- Position sizing method (equal-weight vs Kelly vs CANSLIM-score-weighted)

### Blockers/Concerns

- No point-in-time VN100 membership → survivorship bias risk (acknowledged)
- Fundamentals row counts small (ratios_stock: 4580) — need to verify per-stock coverage
- `is_quarter_stock` is securities-firms-only; general stocks use `is_quarter_nonbank`

## Session Continuity

Last session: 2026-04-10T03:18:14.479Z
Stopped at: Completed 33-02-PLAN.md
Resume: Continue with plan 32-04 or move to Phase 33
