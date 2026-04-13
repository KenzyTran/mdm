---
phase: 37-backtest-validation
plan: "03"
subsystem: backtest-validation
tags: [v8.0, oos, momentum, comparison, roc126]
dependency_graph:
  requires: ["37-02"]
  provides: ["oos_metrics_v8", "comparison_table_v8", "v8_oos_backtest"]
  affects: ["PROJECT.md", "MEMORY best model"]
tech_stack:
  added: []
  patterns: ["locked-params-json-load", "three-way-comparison-table"]
key_files:
  created:
    - analysis/backtest_vn100_v8_oos.py
    - docs/audits/phase37/oos_metrics_v8.json
    - docs/audits/phase37/oos_nav_v8.csv
    - docs/audits/phase37/oos_trades_v8.csv
    - docs/audits/phase37/comparison_table.json
  modified: []
decisions:
  - "v8.0 TRAILS v7.0 on Sharpe_rf3 (0.645 vs 0.813, delta=-0.168); CAGR near-parity (10.0% vs 10.2%) but MaxDD worse (-24.9% vs -16.3%)"
  - "roc126 formula confirmed as sweep winner — simpler ROC-126 outperformed IBD Weighted ROC in-sample"
  - "v8.0 does NOT beat v7.0 — RS momentum is not superior to CANSLIM+MDM on VN100 OOS 2019-2025"
metrics:
  duration: "1min 37sec"
  completed_date: "2026-04-13"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
---

# Phase 37 Plan 03: v8.0 OOS Validation & Comparison Summary

One-liner: OOS backtest (2019-2025) with locked roc126 formula — v8.0 CAGR=10.0%, Sharpe=0.645, MaxDD=-24.9%, trailing v7.0 on risk-adjusted returns (Sharpe delta=-0.168).

## What Was Done

Created `analysis/backtest_vn100_v8_oos.py` modeled on the v7.0 OOS script pattern. The script:
1. Loads `locked_params_v8.json` written by Plan 02's in-sample sweep
2. Constructs `MomentumScorerConfig` + `PortfolioConfig` from sweep winner params
3. Calls `run_v8_backtest(..., formula=best["rs_formula"])` — no hardcoded formula
4. Writes all OOS artifacts to `docs/audits/phase37/`
5. Builds `comparison_table.json` (3 rows: v8.0, v7.0, VN-Index B&H)
6. Prints human-readable comparison with direction vs v7.0

## Results

### v8.0 OOS Performance (2019-2025)

| Metric | v8.0 (RS+N+MDM, roc126) | v7.0 (CANSLIM+MDM) | VN-Index B&H |
|--------|------------------------|---------------------|--------------|
| CAGR | 10.0% | 10.2% | 10.4% |
| Sharpe_rf3 | 0.645 | 0.813 | 0.383 |
| MaxDD | -24.9% | -16.3% | -40.3% |
| Trades | 92 | 59 | — |
| AvgHold | 44.0d | 41.2d | — |

**Verdict: v8.0 TRAILS v7.0 by Sharpe_rf3 delta=-0.168**

- CAGR is essentially identical (10.0% vs 10.2%)
- Risk-adjusted return (Sharpe) is meaningfully lower (0.645 vs 0.813)
- MaxDD is worse (-24.9% vs -16.3%) — RS momentum takes bigger drawdowns
- More trades (92 vs 59) with similar avg hold — higher turnover, no alpha gain
- v8.0 beats VN-Index B&H on Sharpe (0.645 vs 0.383) — still value over passive

### Interpretation

RS momentum (roc126) as a stock selector does NOT outperform CANSLIM fundamentals on this dataset. Key reasons likely include:
1. CANSLIM uses fundamental quality filters (EPS growth) which may correlate with better risk-adjusted returns on VN100
2. roc126 RS ranking may have higher noise in Vietnamese market microstructure (T+2.5, 7% limits)
3. The in-sample sweep period (2014-2018) may have different regime characteristics vs OOS (2019-2025 with COVID)

## Artifacts

| File | Description |
|------|-------------|
| `analysis/backtest_vn100_v8_oos.py` | OOS script loading locked params, producing all artifacts |
| `docs/audits/phase37/oos_metrics_v8.json` | Full OOS metrics: CAGR, Sharpe_rf3, MaxDD, hit_rate, num_trades, avg_hold_days |
| `docs/audits/phase37/oos_nav_v8.csv` | Daily NAV series (1749 rows) |
| `docs/audits/phase37/oos_trades_v8.csv` | Complete trade log (92 trades) |
| `docs/audits/phase37/comparison_table.json` | 3-row comparison: v8.0 / v7.0 / VN-Index B&H |

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create backtest_vn100_v8_oos.py | efb94bd | analysis/backtest_vn100_v8_oos.py |
| 2 | Run OOS backtest & comparison table | d536e9b | 4 artifact files in docs/audits/phase37/ |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data is wired and computed from live DB/cache.

## Self-Check: PASSED

All files exist and both commits verified.
