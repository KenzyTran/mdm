# Phase 45: Walk-Forward Grid Search - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a walk-forward grid search over the **6 policy fields** of the Phase 44 macro filter (4 z-thresholds + 2 policy knobs) on VN30 with train window 2015-2018, annual walk-forward evaluations 2019/2020/2021/2022/2023/2024, OOS holdout 2025-2026 untouched. Acceptance rule (`median CAGR degradation < 30%` AND `median eval-year CAGR > 0%`) is enforced **inside the sweep**, not post-hoc. Output single CSV of all combos (accepted + rejected) plus single JSON of stage winners + runners-up consumable by Phase 46.

Deliverables:

1. `analysis/walkforward_grid.py` — staged sweep orchestrator (Stage 1 DXY → Stage 2 EEM → Stage 3 SBV)
2. `output/v10_grid_results.csv` — one row per combo across all stages (config + per-year metrics + accept/reject + reason)
3. `output/v10_grid_best.json` — 3 stage winners + 3 runners-up per stage, single-file consumable by Phase 46
4. OOS leakage runtime assert + pytest test asserting selection cannot see 2025-labeled data

**Explicitly out of scope:**
- A/B comparison across 5 scenarios (Phase 46 VAL-01)
- OOS test on 2025-2026 holdout (Phase 46 VAL-02)
- HARD gate evaluation (Phase 46 VAL-02)
- v6.0 parity regression test (Phase 46 VAL-04)
- Production candidate verdict string (Phase 46 VAL-05)
- Rule docs / dashboard updates (Phase 47)
- Any change to MacroFilter logic, MDMV2Config field surface, fail-safe, position_manager, or stop_loss code (Phase 44 owns all of these — Phase 45 consumes them read-only)
- Adding new MDMV2Config fields (no per-signal `dxy_enabled / eem_enabled / sbv_enabled` toggles — Phase 46 will decompose +DXY / +EEM / +SBV scenarios via threshold extremes per Phase 46 design)
- Engine changes of any kind
- Regenerating Phase 43 canonical CSVs

</domain>

<decisions>
## Implementation Decisions

### Search space sizing & strategy

- **D-01 (Staged sweep — Phase 40 D-01 precedent):** Three sequential stages, Stage N+1 begins after Stage N selects its winner:
  - **Stage 1 — DXY:** Sweep `dxy_easing_z_threshold`, `dxy_tightening_z_threshold`, `dxy_tightening_dd_threshold` over a 3×3×3 = 27-combo grid. Hold `eem_*`, `sbv_*` at Phase 44 VN30_PRESET defaults. Select winner per D-09 ranking.
  - **Stage 2 — EEM:** Lock Stage 1 DXY winner. Sweep `eem_easing_z_threshold`, `eem_tightening_z_threshold` over 3×3 = 9-combo grid. Hold `sbv_*` at default. Select winner.
  - **Stage 3 — SBV (all-three):** Lock Stage 1 DXY + Stage 2 EEM winners. Sweep `sbv_tightening_stop_loss_max_multiplier` over 3 values. Total 3 combos.
  - **Total combos across stages: 27 + 9 + 3 = 39.** With 6 walk-forward eval years per combo + 1 train run (single full-period run + slice per D-04), each combo fires `engine.run()` exactly once → 39 engine runs total.
  - Acknowledged: same conditional-optimization bias as Phase 41 D-07 (Stage 2 winner is conditional on Stage 1 lock, Stage 3 conditional on Stage 1+2). Bias is documented in CSV + flagged in handoff JSON. Phase 46 reviewer can re-run any stage independently if needed.

- **D-02 (Search 6 policy fields, lock 3 windows):** The 6 grid-searched fields are:
  - `dxy_easing_z_threshold` (Stage 1)
  - `dxy_tightening_z_threshold` (Stage 1)
  - `dxy_tightening_dd_threshold` (Stage 1)
  - `eem_easing_z_threshold` (Stage 2)
  - `eem_tightening_z_threshold` (Stage 2)
  - `sbv_tightening_stop_loss_max_multiplier` (Stage 3)
  Locked at Phase 44 VN30_PRESET defaults: `dxy_window_days=20`, `eem_window_days=20`, `sbv_decay_days=90`. Quick-task 260421-lb4 already validated 20d windows for DXY/EEM correlation and 90d for SBV transmission — re-searching them spends compute on the wrong question. Locking is documented in CSV header comments + reproducible by reading VN30_PRESET.

- **D-03 (3 values per searched field — default ± 1 step):** Step sizes:
  - z-thresholds: ±0.5 around default (e.g., `dxy_easing_z ∈ {-1.5, -1.0, -0.5}`, `dxy_tightening_z ∈ {0.5, 1.0, 1.5}`, `eem_easing_z ∈ {0.5, 1.0, 1.5}`, `eem_tightening_z ∈ {-1.5, -1.0, -0.5}`)
  - `dxy_tightening_dd_threshold` (int): `{2, 3, 4}` (default 3 ± 1)
  - `sbv_tightening_stop_loss_max_multiplier`: `{1.0, 1.5, 2.0}` (default 1.5 ± 0.5; max bounded by `stop_loss_max_multiplier=2.5` per `__post_init__` assert)
  - Planner may justify per-field deviations (e.g., wider grid for the most-sensitive field) but default values must remain at the center cell of the grid.

### Walk-forward run methodology

- **D-04 (Single full-period run + per-year slice — Phase 41 D-08 precedent):** For each combo, run engine ONCE on `DataLoader('vn30').load('2015-01-01', '2024-12-31')` with `build_indicator_dataframe`. The OOS hold-out 2025-2026 is excluded by data window AND by runtime assert per D-13. From the resulting signal log:
  - **Train metrics (used by D-08 numerator):** slice rows where `date <= 2018-12-31` (4 calendar years), compute CAGR via `analysis/validate_v9.py::compute_metrics()`.
  - **Eval-year metrics (used by D-08 denominator across 6 entries):** slice rows where `date.year == y` for each `y ∈ {2019, 2020, 2021, 2022, 2023, 2024}`, compute CAGR / Sharpe_rf3 / MaxDD per year.
  - This mirrors how the engine runs in production (continuous state, no annual restart) and matches the Phase 42 reconciled-baseline methodology. The Phase 41 mistake was tuning grid params on train-only metrics, NOT the run pattern itself — Phase 45 fixes by enforcing per-year acceptance INSIDE the sweep.

- **D-05 (Train window FIXED at 2015-2018 per ROADMAP — no expanding):** Train metric is computed ONCE per combo from the 2015-2018 slice and reused as the degradation reference for all 6 eval years. Do NOT expand train per year (e.g., 2015-2018 for 2019 eval, 2015-2019 for 2020 eval) — ROADMAP locks fixed window and that's the v9.0-lesson-honoring choice (no peek-ahead training).

- **D-06 (Per-year metrics columns in CSV):** For each combo and each eval year `y`:
  - `cagr_eval_{y}_pct` (float)
  - `sharpe_rf3_eval_{y}` (float)
  - `max_dd_eval_{y}_pct` (float, signed negative)
  - 18 eval-year-specific columns total (3 metrics × 6 years).
  - Plus 3 train-window columns: `cagr_train_pct`, `sharpe_rf3_train`, `max_dd_train_pct`.
  - Plus 6 derived columns: `degradation_2019`, ..., `degradation_2024` (per-year ratio per D-08).
  - Plus aggregate: `median_degradation`, `median_eval_cagr_pct`, `eval_years_count` (= 6 normally, less if NaN-skipped per D-10).
  - Reuse `analysis/validate_v9.py::compute_metrics()` for the per-slice computation — DO NOT reimplement.

- **D-07 (Diagnostic whipsaw columns deferred):** Per-year `transitions / sell_count / ma50_breakdown_share` are NOT included in v10_grid_results.csv (despite Phase 40 D-18 schema). Reason: per-year whipsaw is a Phase 46 VAL-04 concern (full-period whipsaw vs reconciled baseline). Including 30+ extra columns inflates CSV without serving Phase 45's acceptance gate. Planner discretion: include if it costs < 10% additional runtime and fits a single-screen CSV header.

### Acceptance rule details

- **D-08 (Degradation formula — Phase 41 D-10 applied per-year, then median):**
  - For each eval year `y`: `degradation_{y} = (cagr_train_pct - cagr_eval_{y}_pct) / abs(cagr_train_pct)`
  - Median across 6 years: `median_degradation = numpy.median([degradation_{y} for y in 2019..2024])`
  - Default is `numpy.median` semantics (linear interpolation for even count — average of 3rd and 4th smallest after sorting). Document in CSV header comment.
  - Per-year value is signed: positive = eval CAGR < train CAGR (degradation), negative = eval CAGR > train CAGR (improvement). Median of signed values; gate uses raw value, not absolute.

- **D-09 (Acceptance gate — ROADMAP + sanity floor):**
  - Combo `accepted=True` if AND ONLY if BOTH:
    - `median_degradation < 0.30` (ROADMAP WF-02, dimensionless, signed; values like 0.12 = 12% degradation pass; values like 0.45 fail)
    - `median(cagr_eval_{y} for y in 2019..2024) > 0.0` (sanity floor — combo must beat cash on median; rejects combos that pass degradation gate via low-but-positive train CAGR yet have median eval CAGR like -2%)
  - All other combos `accepted=False` with a `rejection_reason` string column populated (e.g., `"median_degradation 0.42 >= 0.30"`, `"median_eval_cagr -1.30% <= 0%"`, `"engine_error_year_2020"`, `"insufficient_eval_coverage 4/6"`).
  - **Both accepted and rejected combos appear in v10_grid_results.csv** per ROADMAP SC-2 ("not silently dropped"). The `accepted` boolean column drives Phase 46 / runner downstream consumption.

- **D-10 (NaN handling — skip year, cap minimum coverage):**
  - If a single eval year errors (engine raises) or returns NaN metrics: drop that year from the median calc, increment `eval_years_count` accordingly. Continue evaluating remaining years.
  - If `eval_years_count < 5` (i.e., `≥ 2` years failed): mark combo `accepted=False` with `rejection_reason="insufficient_eval_coverage {N}/6"`. Median over fewer than 5 years is too thin a sample for a 30% gate.
  - Engine errors per year are caught with try/except; full traceback written to a `error_year_{y}` text column (kept short — first 200 chars). Combo continues to next year. Phase 40 D-10 fail-loud precedent applied per-year, not per-combo.
  - Train run failure (rare): combo immediately marked `accepted=False` with `rejection_reason="train_run_failed"` and traceback in `error_train` column. No eval years attempted.

### Top-N selection & Phase 46 handoff

- **D-11 (Stage winners + runners-up — single JSON):** `output/v10_grid_best.json` schema:
  ```json
  {
    "schema_version": 1,
    "generated_at": "<iso8601>",
    "engine_git_hash": "<HEAD>",
    "train_window": "2015-01-01..2018-12-31",
    "eval_years": [2019, 2020, 2021, 2022, 2023, 2024],
    "oos_holdout": "2025-01-01..2026-12-31 (untouched)",
    "ranking_metric": "median_eval_cagr_pct",
    "stage1_dxy": {
      "winner": { "config": {...}, "metrics": {...}, "rank": 1 },
      "runners_up": [
        { "config": {...}, "metrics": {...}, "rank": 2 },
        { "config": {...}, "metrics": {...}, "rank": 3 },
        { "config": {...}, "metrics": {...}, "rank": 4 }
      ]
    },
    "stage2_eem": { "winner": {...}, "runners_up": [...] },
    "stage3_all_three": { "winner": {...}, "runners_up": [...] }
  }
  ```
  - `config` field of each entry is the FULL 10-field MDMV2Config macro tuple (D-15 from Phase 44) — including locked windows + non-stage-active fields at default. Phase 46 can pass directly to `dataclasses.replace(VN30_PRESET, **config)` without lookup.
  - `metrics` field includes `train_cagr_pct`, `median_eval_cagr_pct`, `median_degradation`, `median_eval_sharpe_rf3`, `median_eval_max_dd_pct` — enough for Phase 46 to rank scenarios without re-running.
  - Runners-up are top-3 from the SAME stage's accepted-combo pool (i.e., for Stage 1, top-3 accepted combos sweeping DXY).

- **D-12 (Ranking metric — median eval CAGR with parsimony tiebreak):** Within each stage's accepted-combo pool, rank by:
  1. `median_eval_cagr_pct` descending (primary)
  2. Tiebreak: `median_eval_sharpe_rf3` descending (Phase 41 D-18 precedent — risk-adjusted)
  3. Tiebreak: parsimony — config closer to Phase 44 VN30_PRESET defaults wins (sum of absolute distances from default values across the searched fields, scaled per field's range; planner may simplify to "fewest non-default fields among ties at this depth"). Justification: simpler params generalize better, mirrors Phase 41 D-18 parsimony principle.
  4. Tiebreak (very rare): row order in the CSV (first-seen wins, deterministic).

- **D-13 (Phase 46 handoff — stage winners only, Phase 46 builds 5 scenarios):** Phase 45 outputs ONLY the 3 stage winners + runners-up. Phase 46 is responsible for constructing the 5 A/B scenarios (`baseline / +DXY / +EEM / +SBV / +all`) by mutating VN30_PRESET via `dataclasses.replace` and selectively neutralizing non-target signals (e.g., for `+DXY only`: take Stage 1 DXY winner's DXY thresholds, set EEM thresholds to extreme values like `eem_easing_z=999` and `eem_tightening_z=-999` so EEM never triggers, set `sbv_tightening_stop_loss_max_multiplier=stop_loss_max_multiplier` so SBV override is no-op). This separation keeps Phase 45 narrowly focused on parameter selection; Phase 46 owns scenario design. **Phase 46 design note (out of Phase 45 scope, but anchored here):** scenario decomposition via threshold extremes is acceptable because no per-signal `enable` flag exists in MDMV2Config — adding such a flag is Phase 44 territory and is not retrofitted in v10.0.

### OOS leakage guard (SC-1 + SC-4)

- **D-14 (Runtime assert — top-of-script):** Top of `analysis/walkforward_grid.py`:
  ```python
  TRAIN_START = '2015-01-01'
  EVAL_END = '2024-12-31'    # Inclusive — 2024 is the last walk-forward year
  OOS_FENCE = '2025-01-01'   # Any data >= this date MUST NOT enter selection
  ```
  Right after each `DataLoader.load()` call (whether at module import or inside per-combo loop): `assert df['date'].max() < pd.Timestamp(OOS_FENCE), f"OOS leak: max date {df['date'].max()} crossed {OOS_FENCE}"`. Phase 40 D-12 precedent extended to a stricter boundary.
  Script does NOT accept CLI overrides for `TRAIN_START` / `EVAL_END` / `OOS_FENCE` — reproducibility absolute.

- **D-15 (Synthetic-data leakage test — pytest, SC-4):** New test file `tests/test_walkforward_oos_guard.py` with `@pytest.mark.regression` marker. Two test functions:
  - `test_assert_fires_on_2025_data`: construct a synthetic mini-DataFrame with `date` column containing `pd.Timestamp('2025-06-15')`, call the script's data-load helper (factored into an importable function per planner discretion) with this DataFrame injected, assert AssertionError with message containing `"OOS leak"`.
  - `test_selection_excludes_2025_when_present`: construct synthetic combo result rows with one row containing `date = 2025-XX` in its eval slice, call the selection function on the rows, assert that 2025-XX-row is NOT in the accepted set AND is flagged via `rejection_reason` mentioning OOS.
  - Tests run in < 1 second (synthetic data only, no real engine call).

### Implementation discipline

- **D-16 (Reuse `compute_metrics`, do NOT reimplement):** `analysis/walkforward_grid.py` imports `from analysis.validate_v9 import compute_metrics`. Any deviation requires explicit Plan-time justification — drift between Phase 41/42/45 metric formulas is a v10.0 integrity risk (reconciled-baseline tuple lives in `output/v10_reconciled_baseline.json` and is consumed across Phase 45/46/47 — formulas must agree). If `compute_metrics` lacks a per-year mode, planner adds it via a `slice_dates: Optional[Tuple[date, date]]` kwarg in `analysis/validate_v9.py` rather than copy-paste in the new script.

- **D-17 (Serial execution + tqdm — no multiprocessing):** 39 combos × 1 engine run each ≈ 10-15 minutes serial (Phase 42 BASE-03 measured ~3s per engine on full 2015-2026; Phase 45 runs 2015-2024 = ~10 years, slightly faster per run). Single tqdm progress bar covers all 3 stages. No multiprocessing — Phase 40 precedent (90 runs serial), Phase 45 has fewer runs. Avoids the Phase 32 multi-process complexity.

- **D-18 (Fail-loud per-cell, fail-summary on top winners):** Per-combo errors captured per-year per D-10 (graceful degradation). After each stage's CSV write but BEFORE selection: scan top-3 by ranking metric — if ANY top-3 row has `accepted=True` AND any per-year metric column is NaN, raise `SummaryError("Stage {N} winner has NaN in eval year metrics — selection unsafe")`. Mirrors Phase 40 D-10 sweep summary safeguard.

### Claude's Discretion

- Exact CSV column ORDER (suggest: stage_id, combo_id, [10 config fields], [4 train cols], [3 eval cols × 6 years = 18], [6 degradation cols], [3 aggregate cols], accepted, rejection_reason, error_train, error_year_{y}). Planner may rearrange.
- Helper function decomposition inside `walkforward_grid.py` (suggest: `load_vn30_data()`, `build_combo_grid(stage)`, `run_combo(cfg, df) -> dict`, `select_winner(stage_results) -> tuple[winner, runners_up]`, `write_results_csv(rows)`, `write_best_json(stages)`).
- tqdm description string format / verbosity per combo.
- Whether to also write per-stage human-readable `output/v10_grid_stage{N}.txt` siblings (Phase 40 D-21 precedent had .txt + .json siblings — Phase 45 ROADMAP only mandates JSON; .txt is bonus).
- Specific numpy / pandas version assertions in the script (suggest: read from `output/v10_reconciled_baseline.json` engine_git_hash and assert HEAD matches at sweep start; if mismatch warn, do not abort — Phase 45 is parameter selection, not parity regression).
- Whether to bundle a small `analysis/inspect_grid_results.py` helper for reviewers (nice-to-have).
- Whether to commit a snapshot of `output/v10_grid_results.csv` (full 39+ rows) to git or only the JSON winners. Phase 40 commits its sweep CSVs — Phase 45 likely follows.

### Folded Todos

None — `gsd-tools todo match-phase 45` reports `{ todo_count: 0, matches: [] }`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements (current phase scope)
- [.planning/ROADMAP.md §Phase 45](.planning/ROADMAP.md) (lines 862-872) — Goal, 4 success criteria, train/eval/OOS windows, output paths
- [.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md) §Walk-Forward Discipline (WF-01, WF-02, WF-03) — grid infrastructure, median degradation metric, dashboard requirement
- [.planning/PROJECT.md](.planning/PROJECT.md) §Current Milestone v10.0 (lines 65-87) — milestone goal, HARD gate, evidence base

### Phase 44 outputs (MUST READ — frozen upstream contracts)
- [.planning/phases/44-macro-filter-module/44-CONTEXT.md](.planning/phases/44-macro-filter-module/44-CONTEXT.md) §D-15 — full 10-field MDMV2Config macro tuple (search space inputs); §D-04 most-restrictive combiner; §D-09 hard short-circuit parity invariant
- [strategies/mdm_hybrid/macro_filter.py](strategies/mdm_hybrid/macro_filter.py) — MacroFilter class + add_macro_columns helper + LIQUIDITY_PROXY_PATH / SBV_EVENTS_PATH constants
- [strategies/mdm_hybrid/config.py](strategies/mdm_hybrid/config.py) — MDMV2Config dataclass with 10 macro fields (lines 91-109), `__post_init__` validation (lines 130-156), VN30_PRESET (line 189)

### Phase 43 outputs (data inputs — read-only via MacroFilter)
- [docs/liquidity_proxy_spec.md](docs/liquidity_proxy_spec.md) — merge contract + publication-lag policy (Phase 45 does NOT modify; consumes through MacroFilter)
- [data/vn_liquidity_proxy.csv](data/vn_liquidity_proxy.csv) — 6-col daily panel 2015-2025
- [data/sbv_policy_events.csv](data/sbv_policy_events.csv) — 5-col event log, 12 rows

### Phase 42 outputs (canonical baseline — read-only)
- [output/v10_reconciled_baseline.json](output/v10_reconciled_baseline.json) — schema_version=1, CAGR=11.47, sell_count=124. Phase 45 does NOT gate on this directly (Phase 46 does), but uses it as a sanity reference if planner wants to print "baseline CAGR for context" in the report.
- [docs/audits/v10_baseline_drift.md](docs/audits/v10_baseline_drift.md) — reconciliation narrative (read for context)
- [.planning/phases/42-baseline-reconciliation/42-CONTEXT.md](.planning/phases/42-baseline-reconciliation/42-CONTEXT.md) §D-12/D-14/D-15 — canonical-tuple consumer contract (Phase 45 follows the "read JSON, never hardcode" discipline)

### Phase 41 patterns (mirror for run methodology)
- [analysis/validate_v9.py](analysis/validate_v9.py) — `compute_metrics()` (lines 125-203) MUST be reused per D-16; `run_engine()` (lines 102-122) HybridConfig construction pattern; D-08/D-09/D-10 train/test split discipline
- [.planning/phases/41-ab-walk-forward-validation/41-CONTEXT.md](.planning/phases/41-ab-walk-forward-validation/41-CONTEXT.md) §D-08/D-10/D-18 — run pattern, degradation formula, parsimony ranking precedent. **Phase 45 D-04/D-08/D-12 inherit these.**

### Phase 40 patterns (mirror for sweep orchestration)
- [analysis/sweep_v9_atr.py](analysis/sweep_v9_atr.py) — staged sweep template (D-01/D-04/D-12 patterns: serial loop with tqdm, OOS hard-coded boundary, per-cell try/except, SummaryError if top-N has NaN)
- [analysis/sweep_v9_dd.py](analysis/sweep_v9_dd.py) — Stage 2 reads Stage 1 winner JSON (D-13 handoff pattern Phase 45 mirrors across its 3 stages)
- [analysis/select_v9_best.py](analysis/select_v9_best.py) — selection algorithm + JSON+TXT output pair (Phase 45 unifies into single JSON per D-11)
- [.planning/phases/40-grid-search-sweeps/40-CONTEXT.md](.planning/phases/40-grid-search-sweeps/40-CONTEXT.md) §D-01/D-09/D-10/D-12/D-15/D-18/D-19/D-22 — staged-sweep + fail-loud + tiebreak + extended-CSV-schema patterns

### Engine entry points (read-only consumption)
- [strategies/mdm_hybrid/mdm_hybrid_engine.py](strategies/mdm_hybrid/mdm_hybrid_engine.py) — HybridEngine class. Phase 45 invokes `engine.run(df.copy())` per combo. NO modifications.
- [core/data_loader.py](core/data_loader.py) — `DataLoader('vn30').load(start, end)`. Phase 45 invokes once per combo with start='2015-01-01', end='2024-12-31'.
- [core/indicators.py](core/indicators.py) — `build_indicator_dataframe(df)`. Phase 45 invokes once per combo before engine.run.

### Pytest precedent (regression test pattern for D-15)
- [tests/test_baseline_determinism.py](tests/test_baseline_determinism.py) — `@pytest.mark.regression` marker, class-scoped pattern (Phase 45 D-15 test inherits)
- [tests/test_macro_filter_v6_parity.py](tests/test_macro_filter_v6_parity.py) — Phase 44 parity regression test structure

### Memory anchors
- v10.0 HARD gate (gate Phase 45 must enable, not enforce): MaxDD < -20% AND CAGR ≥ reconciled baseline AND walk-forward median degradation < 30% — memory: `project_v9_whipsaw.md`. Phase 45 produces the walk-forward leg evidence; Phase 46 evaluates the gate.
- Equity formula `state[i-1]` discipline — memory: `feedback_equity_formula.md`. Inherited via `compute_metrics` reuse (D-16) — Phase 45 MUST NOT compute per-year equity with `state[i]`.
- v9.0 Phase 41 lesson — walk-forward CV INSIDE grid search (memory: `project_v9_whipsaw.md`). Phase 45 D-08 + D-09 IS the implementation of this lesson.
- VN liquidity proxy evidence (DXY/EEM ±0.19 corr; SBV 55.76pp spread) — memory: `project_liquidity_proxy.md`. Underwrites D-02 lock of windows at 20d/90d.
- Best-model doc discipline — memory: `feedback_best_model_docs.md`. Phase 45 outputs (winners JSON) feed Phase 46/47 — they must clearly identify which combo would supersede v6.0 IF Phase 46 HARD gate passes.

### Prior phase contexts (carry-forward decisions, read for inheritance)
- [.planning/phases/40-grid-search-sweeps/40-CONTEXT.md](.planning/phases/40-grid-search-sweeps/40-CONTEXT.md) — D-01 staged sweep, D-09 serial-tqdm, D-10 fail-loud, D-12 OOS-guard, D-18 extended schema
- [.planning/phases/41-ab-walk-forward-validation/41-CONTEXT.md](.planning/phases/41-ab-walk-forward-validation/41-CONTEXT.md) — D-08 single-run-slice, D-10 degradation formula, D-18 parsimony ranking
- [.planning/phases/42-baseline-reconciliation/42-CONTEXT.md](.planning/phases/42-baseline-reconciliation/42-CONTEXT.md) — D-14 read-JSON-never-hardcode discipline; D-12 canonical-tuple consumer contract
- [.planning/phases/44-macro-filter-module/44-CONTEXT.md](.planning/phases/44-macro-filter-module/44-CONTEXT.md) — D-15 macro config field surface (search space); D-04 most-restrictive combiner (acceptance behavior unaffected, sanity check)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- [analysis/validate_v9.py::compute_metrics()](analysis/validate_v9.py) — canonical per-slice metrics function (CAGR, Sharpe_rf3, MaxDD, transitions, sell_count, ma50_breakdown_share, buy_count, *_pct). Phase 45 reuses verbatim per D-16. May add `slice_dates` kwarg if per-year slicing needs different signature.
- [analysis/sweep_v9_atr.py](analysis/sweep_v9_atr.py) — sweep loop skeleton (data load → tqdm grid loop → per-cell try/except → CSV write → SummaryError check). Phase 45 mirrors structure across 3 stages.
- [analysis/select_v9_best.py](analysis/select_v9_best.py) — JSON+TXT output writer. Phase 45 unifies into single JSON per D-11; can lift the JSON-writing portion.
- `dataclasses.replace(VN30_PRESET, **overrides)` — Phase 40 D-04 / Phase 41 D-05 / Phase 42 D-22 precedent. Phase 45 uses this per stage to construct each combo's config from VN30_PRESET + grid cell overrides.
- `HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False))` — engine construction pattern.
- `tqdm` import + serial loop pattern from sweep_v9_atr.py.
- [tests/test_macro_filter_v6_parity.py](tests/test_macro_filter_v6_parity.py) — `@pytest.mark.regression` test structure to model D-15 OOS guard test after.

### Established Patterns

- **Single-file analysis script per phase** — Phase 27, 40, 41, 42 precedent. Phase 45 emits ONE orchestrator: `analysis/walkforward_grid.py`. Three stages live inside this single file (functions per stage, not separate scripts) because handoff is in-memory rather than via JSON files between stages.
- **Output to `output/`** — Phase 45 writes to `output/v10_grid_results.csv` and `output/v10_grid_best.json` per ROADMAP SC-3.
- **Hard-coded train/eval/OOS boundaries + runtime asserts** — Phase 40 D-12 precedent extended per D-14. Phase 45's `OOS_FENCE='2025-01-01'` is the hard guard.
- **Fail-loud per-cell, fail-summary on top-N** — Phase 40 D-10 precedent. Phase 45 D-18 inherits.
- **Sharpe_rf3 formula** — `(ann_return - 0.03) / (daily_returns.std() × √252)`. Phase 40 D-19, Phase 41 D-11, Phase 42 D-15. Phase 45 inherits via `compute_metrics` reuse.
- **Pytest `@pytest.mark.regression`** — Phase 42 BASE-03, Phase 44 MACRO-04. Phase 45 D-15 OOS guard test inherits.
- **dataclasses.replace for clean config mutation** — Phase 40+ standard. Phase 45 builds 39 combo configs this way.
- **Read JSON, never hardcode** — Phase 42 D-14. Phase 45 reads VN30_PRESET defaults from the dataclass directly (no JSON), but Phase 46 reads `output/v10_grid_best.json` from Phase 45 (D-11 schema).

### Integration Points

**Inputs:**
- VN30 OHLCV via `DataLoader('vn30').load('2015-01-01', '2024-12-31')` — Phase 45-specific window (excludes OOS hold-out at the data-load layer in addition to runtime assert)
- VN30_PRESET from [strategies/mdm_hybrid/config.py:189](strategies/mdm_hybrid/config.py) — base for `dataclasses.replace` per combo
- MacroFilter / add_macro_columns via [strategies/mdm_hybrid/macro_filter.py](strategies/mdm_hybrid/macro_filter.py) — invoked through HybridEngine when `macro_filter_enabled=True` (set TRUE for all 39 sweep combos by definition)
- Phase 43 canonical CSVs (`data/vn_liquidity_proxy.csv`, `data/sbv_policy_events.csv`) — consumed by add_macro_columns; Phase 45 does NOT touch these directly
- `analysis/validate_v9.py::compute_metrics()` — per-slice metrics

**Outputs Phase 45 creates:**
- `analysis/walkforward_grid.py` — NEW staged-sweep orchestrator script
- `output/v10_grid_results.csv` — 39+ rows × ~30+ columns (configs + per-year metrics + accept/reject + reasons)
- `output/v10_grid_best.json` — 3 stage winners + 3 runners-up per stage, schema_version=1
- `tests/test_walkforward_oos_guard.py` — NEW pytest with 2 OOS guard tests (D-15)
- Possibly: `analysis/inspect_grid_results.py` (Claude's discretion D-claude-1)
- Possibly: `analysis/validate_v9.py` modification — add `slice_dates` kwarg to `compute_metrics` if needed (D-16)
- NO other engine / config / docs / dashboard changes

**Downstream consumers (Phases 46-47):**
- Phase 46 VAL-01 A/B comparison — reads `output/v10_grid_best.json` to construct 5 scenarios via threshold extremes per D-13 handoff design
- Phase 46 VAL-02 OOS HARD gate — Phase 45's accepted-combo pool is the candidate set; Phase 46 picks Stage 3 winner (or runner-up) and runs on 2025-2026 OOS holdout
- Phase 46 VAL-03 walk-forward stability gate — re-checks median_degradation for the chosen scenario across Phase 45's eval years
- Phase 47 DOC-01 rules doc — documents the production-candidate threshold values (from Phase 45 winner JSON if Phase 46 HARD gate passes)
- Phase 47 DOC-03 milestone audit — quotes Phase 45 results in v10.0 milestone retrospective ("walk-forward CV INSIDE grid found N accepted combos out of 39 candidates, top-3 had median degradation X%")

</code_context>

<specifics>
## Specific Ideas

- **"Staged sweep mirroring Phase 40"** — user explicit: prefer staged D-01 over joint or coarse-then-fine. Smaller per-stage grid, easier to debug, conditional bias acknowledged but acceptable given DXY+EEM+SBV decompose naturally into 3 signal-source layers.
- **"Lock the 3 window fields at quick-task evidence defaults"** — windows came from quick-task 260421-lb4 GO verdict (20d for ±0.19 correlation finding). Re-searching them spends compute on a question already answered. Locking is documented in CSV header.
- **"Single full-period run + slice"** — user explicit: Phase 41 D-08 pattern is correct; Phase 41's mistake was the absence of per-year acceptance INSIDE grid sweep, not the run pattern itself.
- **"Pure ROADMAP gate + sanity floor"** — degradation < 30% AND median(eval CAGR) > 0%. Sanity floor catches the "pass via low-but-positive train CAGR" failure mode. Reconciled-baseline 11.47% is NOT used as per-year floor (unrealistic on annual basis).
- **"Single JSON with stage winners + runners-up"** — single file consumable by Phase 46. Each entry carries the FULL 10-field config tuple so Phase 46 can `dataclasses.replace` directly.
- **"Phase 45 produces stage winners; Phase 46 builds 5 scenarios"** — separation of concerns. Phase 46 will use threshold extremes (e.g., `eem_easing_z=999`) to neutralize signals not under test in a given scenario. No new MDMV2Config fields.
- **"Reuse compute_metrics, don't reimplement"** — D-16 hard rule. Drift between Phase 41/42/45 metric formulas is a v10.0 integrity risk. Add per-year `slice_dates` kwarg in validate_v9.py if needed; do not copy-paste.
- **"OOS holdout untouched — runtime assert + pytest test"** — D-14 + D-15. The Phase 41 lesson (walk-forward-only-post-hoc) is enforced two ways: data-load window stops at 2024-12-31 AND runtime assert catches accidental boundary slip AND pytest test asserts selection rejects 2025-labeled data.

</specifics>

<deferred>
## Deferred Ideas

- **Joint full grid (3^6 = 729 combos × 6 evals = 4400 runs)** — rejected per D-01 (staged preferred for debuggability). Revisit only if Phase 46 evidence shows DXY/EEM/SBV interactions are non-additive and staged sweep missed a sweet spot.
- **Coarse-then-fine grid** — rejected per D-01 (added implementation complexity for marginal information gain at this combo count). Revisit if v11.0 macro work expands the search space substantially.
- **Search the 3 window fields (dxy_window, eem_window, sbv_decay)** — rejected per D-02 (quick-task evidence already validated 20d/90d). Revisit if v11.0 expands the macro feature set or finds window-length sensitivity in Phase 46 OOS.
- **5 values per searched field** — rejected per D-03 (3 vals/field gives sufficient resolution at default ±1 step; 5 vals adds compute without proportional information).
- **Whipsaw diagnostic columns per year (transitions, sell_count, ma50_breakdown_share × 6 years)** — rejected per D-07 (Phase 46 VAL-04 owns whipsaw on full-period; per-year inflates CSV without serving acceptance gate). Optional planner discretion.
- **Composite ranking score (CAGR × (1 - degradation))** — rejected per D-12 (no project precedent; median_eval_cagr + parsimony tiebreak is the simpler, Phase 41 D-18-aligned choice).
- **Phase 46 scenario configs pre-baked into Phase 45 JSON** — rejected per D-13 (separation of concerns; Phase 46 owns scenario design, can change scenario count without touching Phase 45 output).
- **Multiprocessing for per-combo runs** — rejected per D-17 (39 combos × ~15s each = ~10 min serial; multiprocessing overhead exceeds benefit at this scale). Revisit if v11.0 sweeps grow > 200 combos.
- **Per-stage human-readable .txt output siblings** — Phase 40 D-21 had .txt + .json. Phase 45 ROADMAP only mandates JSON; .txt is bonus per Claude's discretion.
- **Selection considering 2025-2026 if Phase 46 HARD gate fails** — explicitly out of scope. OOS hold-out is sacred; if the v10.0 candidate fails Phase 46 gate, retain v6.0 (per `project_v9_whipsaw.md` + ROADMAP §Phase 46 SC-5). No "tune until OOS passes" loop.
- **Adding per-signal `dxy_enabled / eem_enabled / sbv_enabled` flags to MDMV2Config** — rejected per D-13 (Phase 44 territory, retroactive flag-add is anti-pattern). Phase 46 uses threshold extremes instead.
- **Joint 3-stage cross-validation** — i.e., sweep DXY+EEM jointly, sweep SBV separately. Considered and rejected: 3-way cross requires bigger compute and Stage 3 (SBV alone) carries minimal sensitivity (1 field, 3 values). Linear staging is sufficient.
- **Reading `output/v10_reconciled_baseline.json` to gate combo acceptance** — rejected per D-09 (sanity floor uses median eval CAGR > 0%, not reconciled baseline). Reconciled baseline informs Phase 46 HARD gate, not Phase 45 acceptance.
- **`analysis/inspect_grid_results.py` reviewer helper** — Claude's discretion (D-claude-6). Nice-to-have if planner judges it pays off; otherwise reviewers use pandas in a notebook.

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 45` reports `{ todo_count: 0, matches: [] }`. No standing backlog items competed for Phase 45 scope.

</deferred>

---

*Phase: 45-walk-forward-grid-search*
*Context gathered: 2026-04-23*
