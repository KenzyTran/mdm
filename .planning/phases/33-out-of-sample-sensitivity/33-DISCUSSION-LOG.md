# Phase 33: Out-of-Sample + Sensitivity - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-10
**Phase:** 33-out-of-sample-sensitivity
**Mode:** assumptions
**Areas analyzed:** OOS Execution, Sensitivity Matrix, Baseline Implementations, diem_canslim Comparison, VN-Index B&H Benchmark

## Assumptions Presented

### OOS Execution Strategy
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New script mirroring backtest_vn100.py, rank-1 config, PERIOD 2019-2025 | Confident | analysis/backtest_vn100.py hard-coded PERIOD convention; locked_params_top3.json schema |
| CANSLIM cache bug (build_canslim_raw_frame keys by ticker set only, not date range) | Confident | _vn100_pipeline.py line 411 — CANSLIM_RAW_CACHE checks ticker subset, not date range |

### Sensitivity Matrix Design
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 3 universe modes × configs; reuse Pool+imap_unordered from sweep_vn100.py | Likely | universe.py VALID_MODES; sweep_vn100.py multiprocessing pattern |
| Cache key collision bug (precompute_static hard-codes mode="current-vn100") | Likely | _vn100_pipeline.py line 151 — UniverseLoader called with hardcoded mode |

### Baseline Implementations
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| CANSLIM-only: inject constant-BUY Series as precomputed["mdm_gate"] | Likely | _vn100_pipeline.py lines 321-323 gate is plain pd.Series |
| MDM-only: standalone NAV, cannot route through PortfolioEngine | Likely | PortfolioEngine requires fills + scorer_frame; index has neither |

### diem_canslim Comparison
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Ranking comparison (Spearman ρ + top-10 overlap) using baseline.py, not NAV backtest | Confident | strategies/canslim/baseline.py lines 55-171; Phase 29 precedent (ρ=0.280) |

### VN-Index B&H Benchmark
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| data/vnindex.csv covers 2019-2026; B&H NAV = close/close[0]; _compute_metrics() | Confident | data/vnindex.csv confirmed 1749 rows; _vn100_pipeline.py _compute_metrics() self-contained |

## Corrections Made

### OOS Config Selection
- **Original assumption:** Planner would decide which config rank to use
- **User decision:** OOS → rank-1 only

### Sensitivity Config Selection
- **Original assumption:** Sensitivity uses rank-1 only
- **User decision:** Sensitivity → all 3 locked configs × 3 universe modes = 9 runs

## External Research

None performed — codebase provided sufficient evidence for all assumptions.
