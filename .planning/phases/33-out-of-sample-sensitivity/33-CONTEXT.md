# Phase 33: Out-of-Sample + Sensitivity - Context

**Gathered:** 2026-04-10 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate the Phase 32 locked-parameter strategy on untouched 2019-2025 data and across universe/period sensitivities. Produce pass/fail verdict against BT-08 targets. No new strategy logic — analysis only.

</domain>

<decisions>
## Implementation Decisions

### OOS Execution (BT-03)
- **D-01:** New script `analysis/backtest_vn100_oos.py` mirroring `analysis/backtest_vn100.py` with `PERIOD = ("2019-01-01", "2025-12-31")`. Hard-coded per D-09 reproducibility convention (no CLI args).
- **D-02:** Use rank-1 locked config only: `c_yoy=0.25, a_cagr=0.20, n_prox=0.10, hard_stop=0.06, slots=5, entry=C` loaded from `docs/audits/phase32/locked_params_top3.json`.
- **D-03:** Fix CANSLIM cache bug before running OOS: `build_canslim_raw_frame()` currently caches by ticker set only (not date range). Must add date range to cache key or force rebuild when period differs — otherwise OOS scoring silently uses in-sample fundamentals (2014-2018 data for 2019-2025 run).

### Sensitivity Matrix (BT-04)
- **D-04:** New script `analysis/sensitivity_vn100.py`. Matrix: **3 universe modes × 3 locked configs** (all 3 from `locked_params_top3.json`). Total = 9 runs.
- **D-05:** Universe modes: `"current-vn100"`, `"liquidity-reconstructed"`, `"vn30-only"` — already implemented in `strategies/canslim/universe.py`.
- **D-06:** Fix cache key bug before running: `precompute_static()` hard-codes `mode="current-vn100"` and cache filenames don't include universe mode. Must include mode in parquet filename (e.g., `ohlc_{mode}_{start}_{end}.parquet`) to prevent cache collision across modes.
- **D-07:** Reuse `Pool + imap_unordered` multiprocessing pattern from `analysis/sweep_vn100.py`.

### Baseline Implementations
- **D-08:** CANSLIM-only (no MDM gate): inject constant `pd.Series` of all `"BUY"` as `precomputed["mdm_gate"]`. No engine changes needed — gate is a plain Series consumed by `PortfolioEngine`.
- **D-09:** MDM-only-on-index baseline: standalone NAV computation from `HybridEngine` state × VN30 OHLC (buy when MDM=BUY, hold cash when MDM=SELL/CASH). **Cannot** route through `PortfolioEngine` — no `fills` or `scorer_frame` exist for an index. Simple NAV array, not a portfolio simulation.

### diem_canslim Comparison (BT-04)
- **D-10:** Ranking comparison only (not a NAV backtest): Spearman ρ + top-10 overlap count per available quarter (2019 Q1 – 2025 Q4) using `strategies/canslim/baseline.py` infra already built in Phase 29.
- **D-11:** Precedent from Phase 29: median ρ=0.280, 2.43/10 overlap on 28 in-sample quarters. OOS comparison uses same method on OOS quarters.

### VN-Index B&H Benchmark (BT-08)
- **D-12:** Source: `data/vnindex.csv` (1,749 rows, covers 2019-01-02 to 2026-04-01, confirmed).
- **D-13:** B&H NAV = `close / close[first_oos_date]` over 2019-2025. Sharpe_rf3 and MaxDD computed via same `_compute_metrics()` function used for strategy NAV (rf=3%, 252-day annualization).
- **D-14:** BT-08 pass criteria: Sharpe uplift > 0.20 vs VN-Index B&H AND MaxDD reduction > 30% vs VN-Index B&H. If either target fails, write analysis identifying responsible component (CANSLIM / entry / MDM / costs).

### Claude's Discretion
- Output format for sensitivity matrix (CSV table vs markdown report)
- Whether to produce charts or only numeric metrics
- Cache implementation detail (separate dir vs filename suffix for universe mode)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 32 outputs (locked params + audit)
- `docs/audits/phase32/locked_params_top3.json` — 3 locked configs (rank-1 is D-02 for OOS)
- `docs/audits/phase32-backtest-sweep.md` — in-sample sweep results, metrics methodology
- `.planning/phases/32-vn100-backtest-in-sample-sweep/32-01-SUMMARY.md` — pipeline handoff notes (stub warnings)
- `.planning/phases/32-vn100-backtest-in-sample-sweep/32-02-SUMMARY.md` — CANSLIM scorer wiring

### Pipeline & engine
- `analysis/_vn100_pipeline.py` — main pipeline (precompute_static, run_vn100_backtest, _compute_metrics, build_canslim_raw_frame)
- `analysis/backtest_vn100.py` — single-run baseline script to mirror for OOS
- `analysis/sweep_vn100.py` — multiprocessing pattern to reuse for sensitivity

### Universe & baseline
- `strategies/canslim/universe.py` — 3 universe modes already implemented
- `strategies/canslim/baseline.py` — diem_canslim MySQL loader, Spearman comparison

### Requirements
- `.planning/REQUIREMENTS.md` §BT-03, BT-04, BT-08

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analysis/_vn100_pipeline.py::precompute_static()` — call once per (universe_mode, period) pair; must fix cache key to include mode
- `analysis/_vn100_pipeline.py::run_vn100_backtest()` — accepts `precomputed=` dict; inject constant-BUY series here for CANSLIM-only baseline
- `analysis/_vn100_pipeline.py::_compute_metrics()` — accepts any NAV array; use directly for B&H benchmark computation
- `analysis/_vn100_pipeline.py::build_canslim_raw_frame()` — cache bug must be fixed (D-03)
- `strategies/canslim/universe.py::UniverseLoader.get(mode=...)` — already supports all 3 modes
- `strategies/canslim/baseline.py` — full diem_canslim comparison harness from Phase 29
- `analysis/sweep_vn100.py::Pool + imap_unordered` — reuse for sensitivity 9-run matrix

### Established Patterns
- Hard-coded PERIOD constants (no CLI args) per D-09 reproducibility convention
- Parquet cache keyed by `(start, end)` suffix — extend to `(mode, start, end)` for sensitivity
- `precomputed=` dict injection pattern for overriding pipeline components

### Integration Points
- `data/vnindex.csv` → B&H benchmark (load via existing DataLoader or direct pandas read)
- `docs/audits/phase32/locked_params_top3.json` → config override for OOS + sensitivity scripts
- MySQL `stocks_backend.canslim.tong_diem` → diem_canslim comparison via `baseline.py`

</code_context>

<specifics>
## Specific Ideas

- OOS run: rank-1 config only (not all 3)
- Sensitivity run: all 3 locked configs × 3 universe modes = 9 total runs
- diem_canslim: ranking comparison (Spearman ρ + top-10 overlap), not NAV backtest

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-out-of-sample-sensitivity*
*Context gathered: 2026-04-10*
