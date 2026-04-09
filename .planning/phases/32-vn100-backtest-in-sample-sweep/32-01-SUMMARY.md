---
phase: 32-vn100-backtest-in-sample-sweep
plan: 01
subsystem: backtest-pipeline
tags: [vn100, canslim, portfolio, backtest, pipeline, BT-01]
requires:
  - strategies/portfolio/engine.py
  - strategies/portfolio/config.py
  - strategies/canslim/config.py
  - strategies/entry/engine.py
  - strategies/mdm_hybrid/mdm_hybrid_engine.py
  - connectors/postgres.py
  - connectors/adjust.py
provides:
  - analysis/_vn100_pipeline.py::run_vn100_backtest
  - analysis/_vn100_pipeline.py::precompute_static
  - analysis/backtest_vn100.py (BT-01 / SC1 single-run baseline)
affects:
  - docs/audits/phase32/single_run_nav.csv
  - docs/audits/phase32/single_run_trades.csv
  - docs/audits/phase32/single_run_positions.csv
tech-stack:
  added: []
  patterns: [parquet-cache, fail-loud-validation, state-i-1-discipline]
key-files:
  created:
    - analysis/_vn100_pipeline.py
    - analysis/backtest_vn100.py
    - tests/phase32/test_pipeline.py
    - docs/audits/phase32/single_run_nav.csv
    - docs/audits/phase32/single_run_trades.csv
    - docs/audits/phase32/single_run_positions.csv
  modified: []
decisions:
  - "CANSLIM scorer stubbed to score=100 for plan 01; real DB-bound scorer wired in plan 02 via precomputed injection"
  - "Foreign-flow + fundamentals loads are best-effort (empty frame on schema drift) — not used by stub scorer"
  - "Fill adapter `_PortfolioFill` bridges Phase 30 Fill.detector -> Phase 31 engine's expected detector_tag attribute without mutating upstream dataclasses"
  - "Parquet cache keyed on (start,end) under docs/audits/phase32/cache/ for sweep reuse"
metrics:
  duration: "~5 min"
  tasks: 2
  files: 6
  completed: "2026-04-09"
requirements: [BT-01]
---

# Phase 32 Plan 01: VN100 Backtest Pipeline + Single-Run Baseline

BT-01 wired end-to-end: `analysis/_vn100_pipeline.py` composes universe → CANSLIM (stubbed) → entry detectors → portfolio engine → costs; `analysis/backtest_vn100.py` runs the 2014-2018 single-run baseline with Phase 31 defaults and writes three audit CSVs.

## Tasks

### Task 1: `_vn100_pipeline.py` helper + precompute cache (commit `6c46e82`)

- `precompute_static(period)` returns `{universe, ohlc, fundamentals, foreign, mdm_gate}`; parquet-cached under `docs/audits/phase32/cache/`.
- Live-load path: `UniverseLoader(mode=current-vn100)` → `load_stock_eod` → `adjust_ohlc` → `HybridEngine(VN30_PRESET)` on VN-Index for MDM gate series.
- `run_vn100_backtest(canslim_cfg, portfolio_cfg, entry_option, period, precomputed=None)` reshapes adjusted OHLC into the Phase 31 `PortfolioEngine` schema, wraps fills in `_PortfolioFill` (detector_tag adapter), runs the engine, and emits `{metrics, nav, trades, positions}`.
- Metrics per D-10: CAGR, Sharpe_rf3 (rf=3%), MaxDD, MaxDD_duration_days, hit_rate, turnover, total_cost_drag_pct, num_trades, avg_hold_days.
- 6 unit tests in `tests/phase32/test_pipeline.py` (all green, 0.11s) inject a synthetic `precomputed` dict to bypass the DB and assert: dict-key shape, function signature, metric-key shape, `state[i-1]` discipline (flat NAV with no positions), A/C acceptance, invalid-option rejection.

### Task 2: `backtest_vn100.py` single-run baseline (commit `4498856`)

- Hard-coded `PERIOD = ("2014-01-01", "2018-12-31")` per D-09.
- Phase 31 defaults: `max_slots=8, hard_stop_pct=0.08, entry_mode=A, cooldown=5, commission=0.25%, tax=0.10%, slippage=0.10%`.
- Phase 29 defaults: `c_threshold=0.20, a_threshold=0.15, n_within_high=0.15`.
- Ran end-to-end against live Postgres + VN30 HybridEngine → wrote all three CSVs.
- **Baseline results:** CAGR 4.16%, Sharpe_rf3 0.067, MaxDD -20.63%, MaxDD duration 389 days, hit rate 50%, 60 trades, avg hold 36.4 days.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Fill.detector vs engine's detector_tag**
- **Found during:** Task 1 wiring.
- **Issue:** Phase 31 `PortfolioEngine._dedupe_union` reads `f.detector_tag` but Phase 30 `strategies/entry/engine.Fill` exposes `detector`. Calling unadapted would `AttributeError` inside the engine loop.
- **Fix:** Added a tiny `_PortfolioFill` dataclass adapter in `_vn100_pipeline.py` that exposes `detector_tag` alongside the other Fill fields. Upstream dataclasses untouched — Phase 30/31 code paths unchanged.
- **Files modified:** `analysis/_vn100_pipeline.py`.
- **Commit:** `6c46e82`.

**2. [Rule 3 — Blocking] `sys.path` missing for script execution**
- **Found during:** Task 2 run.
- **Issue:** `python analysis/backtest_vn100.py` raised `ModuleNotFoundError: No module named 'analysis'` under `uv run`.
- **Fix:** Prepended repo root to `sys.path` at the top of the script, matching `analysis/sweep_vn30_params.py`.
- **Commit:** `4498856`.

**3. [Rule 3 — Blocking] `stock_foreign_eod` schema drift**
- **Found during:** Task 2 run against live Postgres.
- **Issue:** Hand-written SQL referenced `foreignbuyvol`/`foreignsellvol` columns that do not exist in the current schema (`psycopg2.errors.UndefinedColumn`).
- **Fix:** Downgraded the foreign-flow + fundamentals loads to best-effort (return empty DataFrame on error). Plan 01 uses a stub scorer (score=100 for all), so these frames are not consumed. Plan 02 will wire the real CANSLIM scorer and at that point the loaders need to reference the actual schema — this is **deferred to plan 02** since that's when the loads become load-bearing.
- **Commit:** `4498856`.

## Known Stubs

- **CANSLIM scorer stub (score=100 for all)** — `analysis/_vn100_pipeline.py` builds `scorer_frame` with `canslim_score=100.0` for every (date,ticker). Plan 02 (the 1,536-config sweep) MUST replace this with a real scorer invocation that consumes `canslim_cfg` — otherwise the sweep's `c_yoy/a_cagr/n_proximity` dimensions become no-ops. Documented in the module docstring and in the Task 1 commit message.
- **RS frame stub (rs_value=80 for all)** — Above the Phase 31 `rs_threshold=70` default; effectively disables the RS-streak exit in plan 01. Plan 02 should plumb `connectors/postgres.load_stock_rs` results through `precomputed["rs"]`.
- **Foreign flow + fundamentals = empty frames** — Load-bearing only once the real scorer is wired in plan 02.

These stubs are intentional and scoped to plan 01's responsibility (pipeline wiring + single-run smoke). Plan 02 will replace them; the `precomputed=` injection hook is already in place.

## Verification

- `uv run pytest tests/phase32/test_pipeline.py -x -q` → 6 passed in 0.11s.
- `uv run python analysis/backtest_vn100.py` → exit 0, 3 CSVs written under `docs/audits/phase32/`, summary printed.
- Look-ahead discipline markers present: `grep` hits for `i - 1`, `state[i-1]`, `adjust_ohlc`, `HybridEngine`, `Sharpe_rf3` in `analysis/_vn100_pipeline.py`.

## Self-Check: PASSED

- `analysis/_vn100_pipeline.py` exists ✓
- `analysis/backtest_vn100.py` exists ✓
- `tests/phase32/test_pipeline.py` exists ✓
- `docs/audits/phase32/single_run_nav.csv` exists ✓
- `docs/audits/phase32/single_run_trades.csv` exists ✓
- `docs/audits/phase32/single_run_positions.csv` exists ✓
- Commit `6c46e82` exists ✓
- Commit `4498856` exists ✓
