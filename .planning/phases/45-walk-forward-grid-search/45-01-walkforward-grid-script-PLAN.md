---
phase: 45-walk-forward-grid-search
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - analysis/walkforward_grid.py
autonomous: true
requirements: [WF-01, WF-02, WF-03]

must_haves:
  truths:
    - "Script refuses 2025+ data during search (runtime assert fires before any engine run on leaked data)"
    - "Script runs 39 engine combos across 3 stages (27 DXY + 9 EEM + 3 SBV) on VN30 2015-2024"
    - "For each combo, script computes train CAGR on 2015-2018 slice + per-year CAGR on 2019..2024 slices + median degradation"
    - "Accept gate enforces median_degradation < 0.30 AND median(eval CAGR) > 0 — rejected combos stay in CSV with rejection_reason"
    - "Stage 2 sweep locks Stage 1 winner's DXY config; Stage 3 sweep locks Stage 1 + Stage 2 winners"
    - "JSON output has 3 stages × (1 winner + 3 runners-up) with full 10-field macro config tuple for Phase 46 dataclasses.replace"
    - "SummaryError raised if top-3 ranked accepted combos in any stage have NaN eval-year metrics"
    - "Data-load helper factored into an importable function so the Plan 02 pytest can inject synthetic DataFrames"
  artifacts:
    - path: "analysis/walkforward_grid.py"
      provides: "Staged walk-forward grid sweep orchestrator (Stage 1 DXY → Stage 2 EEM → Stage 3 SBV)"
      contains: "TRAIN_START, EVAL_END, OOS_FENCE, SummaryError, load_vn30_data, build_combo_grid, run_combo, select_winner, write_results_csv, write_best_json, main"
      min_lines: 400
  key_links:
    - from: "analysis/walkforward_grid.py"
      to: "analysis/validate_v9.py::compute_metrics"
      via: "from analysis.validate_v9 import compute_metrics"
      pattern: "from analysis.validate_v9 import compute_metrics"
    - from: "analysis/walkforward_grid.py"
      to: "strategies/mdm_hybrid/config.py::VN30_PRESET"
      via: "from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET"
      pattern: "from strategies.mdm_hybrid.config import .*VN30_PRESET"
    - from: "analysis/walkforward_grid.py"
      to: "strategies/mdm_hybrid/mdm_hybrid_engine.py::HybridEngine"
      via: "engine = HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False)); engine.run(df.copy())"
      pattern: "HybridEngine\\(HybridConfig"
    - from: "analysis/walkforward_grid.py"
      to: "output/v10_grid_results.csv"
      via: "df_out.to_csv(OUTPUT_CSV, index=False) after all stages complete"
      pattern: "to_csv.*v10_grid_results\\.csv"
    - from: "analysis/walkforward_grid.py"
      to: "output/v10_grid_best.json"
      via: "json.dump(payload, fh, indent=2) at end of main after Stage 3 selection"
      pattern: "v10_grid_best\\.json"
---

<objective>
Build `analysis/walkforward_grid.py` — the single-file staged-sweep orchestrator that implements Phase 45's full acceptance-gate-inside-the-sweep methodology.

Purpose: Produce the grid-searched macro filter threshold candidates (3 stage winners + 3 runners-up per stage) that Phase 46 consumes to build its 5 A/B scenarios. Enforce WF-01 (infra), WF-02 (degradation metric), WF-03 (sortable CSV + locked-params JSON) without any OOS leak.

Output: `analysis/walkforward_grid.py` that when run produces `output/v10_grid_results.csv` + `output/v10_grid_best.json` in ~10-15 minutes serial.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/45-walk-forward-grid-search/45-CONTEXT.md

# Canonical reference files (MUST READ — source-of-truth contracts)
@analysis/validate_v9.py
@analysis/sweep_v9_atr.py
@analysis/select_v9_best.py
@strategies/mdm_hybrid/config.py
@strategies/mdm_hybrid/mdm_hybrid_engine.py
@strategies/mdm_hybrid/macro_filter.py
@output/v10_reconciled_baseline.json

<interfaces>
<!-- Key types and contracts extracted from canonical refs. Executor uses these directly. -->

From analysis/validate_v9.py (REUSE VERBATIM — D-16 hard rule, no reimplementation):

```python
def compute_metrics(results: pd.DataFrame) -> dict:
    """Returns dict with keys:
      sharpe_rf3 (float), cagr_pct (float rounded 2dp), max_dd_pct (float rounded 2dp),
      total_return_pct (float), transitions (int), sell_count (int),
      ma50_breakdown_sell_share (float), buy_count (int),
      buy_pct (float), cash_pct (float), sell_pct (float)
    Computes CAGR via state[i-1] discipline; years = (last_date - first_date).days / 365.25.
    IMPORTANT: works on pre-sliced DataFrames — caller slices by date before passing.
    """
```

CRITICAL: No `slice_dates` kwarg needed on compute_metrics. Phase 41 precedent (validate_v9.py:425) slices upstream:
    `r_year = r_full[r_full['date'].dt.year == y].copy().reset_index(drop=True)`
    `metrics_year = compute_metrics(r_year)`

From strategies/mdm_hybrid/config.py:
  VN30_PRESET (line 189) — MDMV2Config instance. Defaults for all 10 macro fields set per Phase 44 D-15.
  Macro defaults (the grid centers per D-03):
    dxy_easing_z_threshold=-1.0, dxy_tightening_z_threshold=+1.0,
    eem_easing_z_threshold=+1.0, eem_tightening_z_threshold=-1.0,
    dxy_window_days=20 (LOCKED — not searched), eem_window_days=20 (LOCKED),
    sbv_decay_days=90 (LOCKED),
    dxy_tightening_dd_threshold=3, sbv_tightening_stop_loss_max_multiplier=1.5,
    macro_filter_enabled=False (MUST override to True for all combos).

  MDMV2Config.__post_init__ assertions (line 111-156) that fire when macro_filter_enabled=True:
    dxy_easing_z_threshold < 0                     (so {-1.5, -1.0, -0.5} all satisfy)
    dxy_tightening_z_threshold > 0                 (so {0.5, 1.0, 1.5} all satisfy)
    eem_easing_z_threshold > 0                     (so {0.5, 1.0, 1.5} all satisfy)
    eem_tightening_z_threshold < 0                 (so {-1.5, -1.0, -0.5} all satisfy)
    dxy_tightening_dd_threshold > 0                (so {2, 3, 4} all satisfy)
    0 < sbv_tightening_stop_loss_max_multiplier <= stop_loss_max_multiplier (= 2.5)
        (so {1.0, 1.5, 2.0} all satisfy — 2.0 <= 2.5)

From strategies/mdm_hybrid/mdm_hybrid_engine.py:
  HybridEngine(config: HybridConfig).run(df: pd.DataFrame) -> pd.DataFrame
  Result columns include: date, close, state, action (+ dxy_z, eem_z, sbv_regime when macro_filter_enabled=True).

From strategies/mdm_hybrid/config.py:
  HybridConfig(v2_config: MDMV2Config, two_phase_enabled: bool = True, filter_enabled: bool = False)
  Engine construction pattern used by validate_v9.py:117-122 — reuse verbatim.

From core/data_loader.py + core/indicators.py:
  DataLoader('vn30').load(start_date: str, end_date: str) -> pd.DataFrame
  build_indicator_dataframe(df: pd.DataFrame) -> pd.DataFrame
  Invoke pattern (validate_v9.py:301-303):
    df = DataLoader('vn30').load(start_date=TRAIN_START, end_date=EVAL_END)
    df = build_indicator_dataframe(df)

From analysis/sweep_v9_atr.py:
  class SummaryError(RuntimeError) — pattern at line 48-49; reuse.
  tqdm serial loop pattern — lines 155-192; reuse structure.
  Per-combo try/except capturing `type(exc).__name__: {exc}\n{traceback.format_exc()}` into error column.

From output/v10_reconciled_baseline.json (schema_version=1, 18 D-12 fields):
  Load for context print-only — do NOT gate on this. schema_version==1 and cagr_pct==11.47 are the reconciled anchors.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Module skeleton + OOS constants + SummaryError + compute_metrics import</name>
  <files>analysis/walkforward_grid.py</files>
  <read_first>
    - analysis/sweep_v9_atr.py (lines 1-50 module docstring + imports + TRAIN_START/TRAIN_END/OUTPUT_CSV constants + SummaryError class — copy this header structure)
    - analysis/validate_v9.py (lines 31-67 imports + DATA_START/DATA_END/TRAIN_END/TEST_START constants — mirror style)
    - analysis/validate_v9.py (lines 125-203 compute_metrics — confirm the function signature and import path `from analysis.validate_v9 import compute_metrics`)
    - .planning/phases/45-walk-forward-grid-search/45-CONTEXT.md (D-14 OOS fence + D-16 reuse rule + D-17 serial + D-18 SummaryError)
  </read_first>
  <action>
    Create `analysis/walkforward_grid.py` with this exact header structure (all values concrete, not referenced):

    1. Module docstring describing Phase 45 (WF-01/02/03), the 3 stages (27 DXY + 9 EEM + 3 SBV = 39 combos), train/eval/OOS windows, and acceptance rule (median_degradation < 0.30 AND median(eval CAGR) > 0).
    2. Imports (Python stdlib: sys, os, json, itertools, traceback; from dataclasses import replace; from datetime import datetime, timezone; third-party: numpy as np, pandas as pd, tqdm.tqdm). Add `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))` per sweep_v9_atr.py:32 pattern.
    3. Project imports: `from core.data_loader import DataLoader`, `from core.indicators import build_indicator_dataframe`, `from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine`, `from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET`, `from analysis.validate_v9 import compute_metrics` (D-16 — MUST be this single import line; do NOT reimplement).
    4. Module constants (exact values — copy verbatim):
       ```
       TRAIN_START = '2015-01-01'
       TRAIN_END = '2018-12-31'            # D-05 — FIXED train window, no expanding
       EVAL_START = '2019-01-01'
       EVAL_END = '2024-12-31'              # Inclusive — 2024 is the last walk-forward year
       EVAL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
       OOS_FENCE = '2025-01-01'             # Any data >= this date MUST NOT enter selection (D-14)
       DEGRADATION_THRESHOLD = 0.30         # D-09 (WF-02) — median_degradation < 0.30
       MEDIAN_CAGR_FLOOR = 0.0              # D-09 sanity floor — median(eval CAGR) > 0.0

       OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
       RESULTS_CSV = os.path.join(OUTPUT_DIR, 'v10_grid_results.csv')
       BEST_JSON = os.path.join(OUTPUT_DIR, 'v10_grid_best.json')
       RECONCILED_BASELINE = os.path.join(OUTPUT_DIR, 'v10_reconciled_baseline.json')
       ```
    5. `class SummaryError(RuntimeError): """Raised when any of the top-3 accepted combos in a stage has NaN eval-year metrics (D-18)."""` — copy pattern from sweep_v9_atr.py:48-49.

    Do NOT implement grid builders / runners / writers in this task — those land in Tasks 2-5. Leave a `def main(): raise NotImplementedError` placeholder so `python -c "import analysis.walkforward_grid"` works.

    Reference decision traceability: each block above carries a D-NN comment per D-14/D-16/D-17 from CONTEXT.md.
  </action>
  <verify>
    <automated>python -c "import sys; sys.path.insert(0, '.'); import analysis.walkforward_grid as m; assert m.TRAIN_START == '2015-01-01'; assert m.TRAIN_END == '2018-12-31'; assert m.EVAL_END == '2024-12-31'; assert m.OOS_FENCE == '2025-01-01'; assert m.EVAL_YEARS == [2019, 2020, 2021, 2022, 2023, 2024]; assert m.DEGRADATION_THRESHOLD == 0.30; assert m.MEDIAN_CAGR_FLOOR == 0.0; assert issubclass(m.SummaryError, RuntimeError); from analysis.walkforward_grid import compute_metrics; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^OOS_FENCE = '2025-01-01'" analysis/walkforward_grid.py` returns 1
    - `grep -c "^DEGRADATION_THRESHOLD = 0.30" analysis/walkforward_grid.py` returns 1
    - `grep -c "^TRAIN_END = '2018-12-31'" analysis/walkforward_grid.py` returns 1
    - `grep -c "^EVAL_END = '2024-12-31'" analysis/walkforward_grid.py` returns 1
    - `grep -c "from analysis.validate_v9 import compute_metrics" analysis/walkforward_grid.py` returns exactly 1 (D-16)
    - `grep -c "class SummaryError" analysis/walkforward_grid.py` returns 1
    - `python -c "import analysis.walkforward_grid"` exits 0
  </acceptance_criteria>
  <done>
    Module importable, all 8 constants defined with exact D-14/D-05 values, SummaryError class present, compute_metrics imported (not reimplemented per D-16), main() is NotImplementedError placeholder awaiting subsequent tasks.
  </done>
</task>

<task type="auto">
  <name>Task 2: load_vn30_data helper (OOS-guarded, injectable for tests)</name>
  <files>analysis/walkforward_grid.py</files>
  <read_first>
    - analysis/validate_v9.py (lines 300-310 — DataLoader('vn30').load + build_indicator_dataframe + post-load assert pattern)
    - analysis/sweep_v9_atr.py (lines 137-142 — OOS-guard assert pattern: `assert df['date'].max() <= pd.Timestamp(TRAIN_END)` — Phase 45 extends to `< pd.Timestamp(OOS_FENCE)` per D-14)
    - .planning/phases/45-walk-forward-grid-search/45-CONTEXT.md (D-14 assert wording + D-15 "factored into an importable function per planner discretion" + script does NOT accept CLI overrides for TRAIN_START/EVAL_END/OOS_FENCE)
  </read_first>
  <action>
    Add this data-load helper function to `analysis/walkforward_grid.py` (must be importable by the Plan 02 pytest):

    ```python
    def load_vn30_data(df_override: pd.DataFrame | None = None) -> pd.DataFrame:
        """Load VN30 2015-01-01..2024-12-31, run indicators, assert OOS fence.

        Args:
            df_override: If provided, skip DataLoader + build_indicator_dataframe
                and use this DataFrame directly. Used by the Plan 02 pytest to
                inject synthetic frames with 2025-labeled rows (D-15).

        Returns:
            Post-indicator DataFrame guaranteed to have date.max() < OOS_FENCE.

        Raises:
            AssertionError: With message containing 'OOS leak' if max(date) >=
                OOS_FENCE. Caught by the D-15 regression test.
        """
        if df_override is not None:
            df = df_override
        else:
            df = DataLoader('vn30').load(start_date=TRAIN_START, end_date=EVAL_END)
            df = build_indicator_dataframe(df)
        # D-14 runtime assert — STRICT < (not <=) because OOS_FENCE is inclusive exclusion of 2025
        assert df['date'].max() < pd.Timestamp(OOS_FENCE), (
            f"OOS leak: max date {df['date'].max()} crossed OOS_FENCE {OOS_FENCE}"
        )
        return df
    ```

    Critical constraints (copy verbatim):
    - The assert message MUST contain the literal substring "OOS leak" (D-15 test greps for this).
    - The assert MUST use `<` (strict less-than), not `<=`, because OOS_FENCE='2025-01-01' is the exclusion boundary.
    - The df_override kwarg exists SOLELY for D-15 test injection; production call passes no args.
    - No CLI argparse — the constants TRAIN_START/EVAL_END/OOS_FENCE are hardcoded per D-14 "reproducibility absolute".

    Also add a `def _load_reconciled_baseline_cagr() -> float:` helper that reads `RECONCILED_BASELINE` JSON and returns `payload['cagr_pct']` (= 11.47 at HEAD) — used only for main() context print per D-Claude-4. On FileNotFoundError or KeyError, return `float('nan')` and continue (not a gate).
  </action>
  <verify>
    <automated>python -c "import pandas as pd; from analysis.walkforward_grid import load_vn30_data, OOS_FENCE; df_bad = pd.DataFrame({'date': [pd.Timestamp('2024-06-01'), pd.Timestamp('2025-06-15')]}); raised = False
try:
    load_vn30_data(df_override=df_bad)
except AssertionError as e:
    assert 'OOS leak' in str(e), f'wrong msg: {e}'
    raised = True
assert raised, 'AssertionError not raised on 2025 data'; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def load_vn30_data" analysis/walkforward_grid.py` returns 1
    - `grep -c "OOS leak" analysis/walkforward_grid.py` returns at least 1 (assert message contains literal)
    - `grep "assert df\[.date.\]\.max() < pd\.Timestamp(OOS_FENCE)" analysis/walkforward_grid.py` matches at least once
    - `grep -c "df_override" analysis/walkforward_grid.py` returns at least 2 (parameter + body)
    - Inline python verify above prints OK (injected 2025 frame raises AssertionError with 'OOS leak')
  </acceptance_criteria>
  <done>
    load_vn30_data helper present, accepts df_override kwarg (enables D-15 test injection), fires AssertionError with message containing literal "OOS leak" when max(date) >= OOS_FENCE. No CLI overrides. _load_reconciled_baseline_cagr helper present for main() context print.
  </done>
</task>

<task type="auto">
  <name>Task 3: build_combo_grid (3 stages × exact grid values from D-03) + run_combo (per-combo train + 6 eval slices)</name>
  <files>analysis/walkforward_grid.py</files>
  <read_first>
    - .planning/phases/45-walk-forward-grid-search/45-CONTEXT.md (D-01 staged sweep, D-02 locked windows, D-03 EXACT grid values, D-04 single-run + slice, D-06 per-year metrics columns, D-10 NaN handling, D-16 reuse compute_metrics)
    - strategies/mdm_hybrid/config.py (lines 91-109 — 10 macro fields on MDMV2Config; line 189 VN30_PRESET — the dataclasses.replace base)
    - strategies/mdm_hybrid/config.py (lines 130-156 — __post_init__ asserts that fire when macro_filter_enabled=True — all D-03 grid values satisfy these)
    - analysis/validate_v9.py (lines 102-122 run_engine — engine construction pattern; lines 411-430 train/test two-slice call + metrics pattern)
    - analysis/sweep_v9_atr.py (lines 155-192 — per-combo try/except + tqdm + row dict assembly pattern)
  </read_first>
  <action>
    Add TWO functions to `analysis/walkforward_grid.py`:

    **A) `build_combo_grid(stage: str, locked_overrides: dict) -> list[dict]`**

    Returns a list of dict overrides (to pass to `dataclasses.replace(VN30_PRESET, **overrides, macro_filter_enabled=True)`). Enumerate grid values VERBATIM from D-03 (these are the exact sets — do NOT deviate):

    ```python
    # D-03 grid values (default at center cell per CONTEXT.md D-03)
    DXY_EASING_Z = [-1.5, -1.0, -0.5]                        # default -1.0
    DXY_TIGHTENING_Z = [0.5, 1.0, 1.5]                        # default +1.0
    DXY_TIGHTENING_DD = [2, 3, 4]                             # default 3
    EEM_EASING_Z = [0.5, 1.0, 1.5]                            # default +1.0
    EEM_TIGHTENING_Z = [-1.5, -1.0, -0.5]                     # default -1.0
    SBV_STOP_LOSS_MAX_MULT = [1.0, 1.5, 2.0]                  # default 1.5
    ```

    Stage behavior:
    - `stage == 'stage1_dxy'`: itertools.product(DXY_EASING_Z, DXY_TIGHTENING_Z, DXY_TIGHTENING_DD) → 27 combos. Each combo sets `dxy_easing_z_threshold`, `dxy_tightening_z_threshold`, `dxy_tightening_dd_threshold`. `eem_*` and `sbv_*` fields REMAIN AT VN30_PRESET DEFAULTS (not in override dict). `locked_overrides` arg is ignored (Stage 1 is the root). assert len == 27.
    - `stage == 'stage2_eem'`: itertools.product(EEM_EASING_Z, EEM_TIGHTENING_Z) → 9 combos. Each combo sets `eem_easing_z_threshold`, `eem_tightening_z_threshold`. `locked_overrides` MUST include the 3 DXY winner fields from Stage 1 — merge them into each combo dict. `sbv_*` remains default. assert len == 9.
    - `stage == 'stage3_all_three'`: iterate SBV_STOP_LOSS_MAX_MULT → 3 combos. Each combo sets `sbv_tightening_stop_loss_max_multiplier`. `locked_overrides` MUST include Stage 1 DXY winner (3 fields) + Stage 2 EEM winner (2 fields) = 5 locked fields. assert len == 3.

    Return list[dict]: each dict has only the fields this stage searches + any locked_overrides from prior stages. The caller does `replace(VN30_PRESET, macro_filter_enabled=True, **combo_overrides)` — VN30_PRESET defaults fill unspecified fields (including the LOCKED windows `dxy_window_days=20, eem_window_days=20, sbv_decay_days=90` per D-02).

    **B) `run_combo(df: pd.DataFrame, overrides: dict, stage: str, combo_id: int) -> dict`**

    Runs the engine ONCE on the full df (2015-2024) per D-04 single-run-and-slice, then computes metrics for train slice + each of 6 eval years.

    Returns a row dict with these exact keys (D-06 CSV schema — copy verbatim):
    - Config fields (10 total — full MDMV2Config macro tuple so Phase 46 can replay): `dxy_easing_z_threshold, dxy_tightening_z_threshold, dxy_tightening_dd_threshold, eem_easing_z_threshold, eem_tightening_z_threshold, sbv_tightening_stop_loss_max_multiplier, dxy_window_days, eem_window_days, sbv_decay_days, macro_filter_enabled`
    - Stage / combo metadata: `stage` (= stage arg), `combo_id` (= combo_id arg), `config_name` (= f"{stage}-c{combo_id}")
    - Train metrics (3 cols): `cagr_train_pct, sharpe_rf3_train, max_dd_train_pct`
    - Per-year eval metrics (3 cols × 6 years = 18 cols): `cagr_eval_2019_pct, sharpe_rf3_eval_2019, max_dd_eval_2019_pct, cagr_eval_2020_pct, ...` through 2024
    - Per-year degradation (6 cols): `degradation_2019, degradation_2020, ..., degradation_2024` (D-08: `(cagr_train - cagr_eval_y) / abs(cagr_train)`, signed)
    - Aggregate (3 cols): `median_degradation, median_eval_cagr_pct, eval_years_count`
    - Accept gate (2 cols): `accepted` (bool), `rejection_reason` (str — empty when accepted)
    - Error cols: `error_train` (str, empty when OK), `error_year_2019, ..., error_year_2024` (7 error cols total)

    Per-combo logic (D-10 NaN handling + D-04 run pattern):
    ```python
    row = {the 10 config fields + stage + combo_id + config_name, initialized from overrides}
    cfg = replace(VN30_PRESET, macro_filter_enabled=True, **overrides)
    # D-04 single-run on full data
    try:
        engine = HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False))
        results = engine.run(df.copy())
    except Exception as exc:
        row['error_train'] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:200]}"
        # Populate all metric cols with NaN + accepted=False + rejection_reason='train_run_failed'
        for col in <17 metric cols + 6 degradation cols + 3 aggregate cols>: row[col] = float('nan')
        row['accepted'] = False
        row['rejection_reason'] = 'train_run_failed'
        row['eval_years_count'] = 0
        return row

    # Train slice: date <= 2018-12-31 (D-04)
    train_slice = results[results['date'] <= pd.Timestamp(TRAIN_END)].copy().reset_index(drop=True)
    try:
        train_m = compute_metrics(train_slice)
        row['cagr_train_pct'] = train_m['cagr_pct']
        row['sharpe_rf3_train'] = train_m['sharpe_rf3']
        row['max_dd_train_pct'] = train_m['max_dd_pct']
    except Exception as exc:
        row['error_train'] = ...; row['cagr_train_pct'] = float('nan'); ...; row['accepted'] = False; row['rejection_reason'] = 'train_metrics_failed'; return row

    # Per-year eval slices (D-04)
    valid_evals = []   # list of (year, cagr) for median calc
    degradations = []  # list of signed degradation per year
    for y in EVAL_YEARS:
        year_slice = results[results['date'].dt.year == y].copy().reset_index(drop=True)
        try:
            ym = compute_metrics(year_slice)
            row[f'cagr_eval_{y}_pct'] = ym['cagr_pct']
            row[f'sharpe_rf3_eval_{y}'] = ym['sharpe_rf3']
            row[f'max_dd_eval_{y}_pct'] = ym['max_dd_pct']
            row[f'error_year_{y}'] = ''
            # D-08 degradation — signed
            if row['cagr_train_pct'] != 0 and not np.isnan(row['cagr_train_pct']) and not np.isnan(ym['cagr_pct']):
                deg = (row['cagr_train_pct'] - ym['cagr_pct']) / abs(row['cagr_train_pct'])
                row[f'degradation_{y}'] = deg
                degradations.append(deg)
                valid_evals.append(ym['cagr_pct'])
            else:
                row[f'degradation_{y}'] = float('nan')
        except Exception as exc:
            row[f'error_year_{y}'] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:200]}"
            row[f'cagr_eval_{y}_pct'] = float('nan')
            row[f'sharpe_rf3_eval_{y}'] = float('nan')
            row[f'max_dd_eval_{y}_pct'] = float('nan')
            row[f'degradation_{y}'] = float('nan')

    row['eval_years_count'] = len(valid_evals)
    row['median_eval_cagr_pct'] = float(np.median(valid_evals)) if valid_evals else float('nan')
    row['median_degradation'] = float(np.median(degradations)) if degradations else float('nan')

    # D-09 accept gate (D-10 insufficient-coverage check)
    if row['eval_years_count'] < 5:
        row['accepted'] = False
        row['rejection_reason'] = f"insufficient_eval_coverage {row['eval_years_count']}/6"
    elif np.isnan(row['median_degradation']):
        row['accepted'] = False
        row['rejection_reason'] = 'median_degradation_nan'
    elif row['median_degradation'] >= DEGRADATION_THRESHOLD:
        row['accepted'] = False
        row['rejection_reason'] = f"median_degradation {row['median_degradation']:.3f} >= {DEGRADATION_THRESHOLD:.2f}"
    elif row['median_eval_cagr_pct'] <= MEDIAN_CAGR_FLOOR:
        row['accepted'] = False
        row['rejection_reason'] = f"median_eval_cagr {row['median_eval_cagr_pct']:.2f}% <= {MEDIAN_CAGR_FLOOR:.1f}%"
    else:
        row['accepted'] = True
        row['rejection_reason'] = ''

    return row
    ```

    CRITICAL: `results['date'].dt.year == y` is the D-04 per-year slice predicate. Each slice calls `compute_metrics` — Phase 41 pattern (validate_v9.py:425 precedent).
  </action>
  <verify>
    <automated>python -c "from analysis.walkforward_grid import build_combo_grid; g1 = build_combo_grid('stage1_dxy', {}); assert len(g1) == 27; g2 = build_combo_grid('stage2_eem', {'dxy_easing_z_threshold': -1.0, 'dxy_tightening_z_threshold': 1.0, 'dxy_tightening_dd_threshold': 3}); assert len(g2) == 9; g3 = build_combo_grid('stage3_all_three', {'dxy_easing_z_threshold': -1.0, 'dxy_tightening_z_threshold': 1.0, 'dxy_tightening_dd_threshold': 3, 'eem_easing_z_threshold': 1.0, 'eem_tightening_z_threshold': -1.0}); assert len(g3) == 3; assert all(-1.5 <= c['dxy_easing_z_threshold'] <= -0.5 for c in g1); print('grid OK'); from analysis.walkforward_grid import run_combo; print('run_combo importable')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def build_combo_grid" analysis/walkforward_grid.py` returns 1
    - `grep -c "def run_combo" analysis/walkforward_grid.py` returns 1
    - `grep -c "DXY_EASING_Z = \[-1.5, -1.0, -0.5\]" analysis/walkforward_grid.py` returns 1
    - `grep -c "DXY_TIGHTENING_DD = \[2, 3, 4\]" analysis/walkforward_grid.py` returns 1
    - `grep -c "SBV_STOP_LOSS_MAX_MULT = \[1.0, 1.5, 2.0\]" analysis/walkforward_grid.py` returns 1
    - `grep -c "median_degradation" analysis/walkforward_grid.py` returns at least 3
    - `grep -c "insufficient_eval_coverage" analysis/walkforward_grid.py` returns at least 1
    - `grep -c "train_run_failed" analysis/walkforward_grid.py` returns at least 1
    - Inline python verify above prints "grid OK" then "run_combo importable"
  </acceptance_criteria>
  <done>
    build_combo_grid yields 27/9/3 combos for the 3 stages with exact D-03 values; run_combo performs a single engine run, slices 2015-2018 train + 6 per-year eval, computes median degradation with signed values, applies the D-09 AND-gate (< 0.30 AND > 0.0%) with D-10 NaN/insufficient-coverage handling, and returns a row dict covering all D-06 columns.
  </done>
</task>

<task type="auto">
  <name>Task 4: select_winner (D-12 ranking) + write_results_csv + write_best_json (D-11 schema)</name>
  <files>analysis/walkforward_grid.py</files>
  <read_first>
    - .planning/phases/45-walk-forward-grid-search/45-CONTEXT.md (D-11 JSON schema VERBATIM + D-12 ranking formula + D-18 top-3 NaN guard + D-claude-1 CSV column order)
    - analysis/select_v9_best.py (lines 80-125 — JSON payload write pattern; lift the `_native` numpy-to-python cast helper)
    - analysis/sweep_v9_atr.py (lines 196-214 — canonical col_order + to_csv + top-N NaN SummaryError — mirror this tail)
  </read_first>
  <action>
    Add THREE functions to `analysis/walkforward_grid.py`:

    **A) `select_winner(stage_rows: list[dict], stage: str) -> tuple[dict, list[dict]]`**

    Returns `(winner_row, runners_up_rows)`. Only accepted rows compete (filter `[r for r in stage_rows if r['accepted']]`). If pool is empty, return `(None, [])`.

    D-12 ranking (copy this sort key exactly):
    ```python
    accepted = [r for r in stage_rows if r['accepted']]
    # Parsimony tiebreak helper — count fields different from VN30_PRESET default
    # Fields searched per stage:
    STAGE_FIELDS = {
        'stage1_dxy': ['dxy_easing_z_threshold', 'dxy_tightening_z_threshold', 'dxy_tightening_dd_threshold'],
        'stage2_eem': ['eem_easing_z_threshold', 'eem_tightening_z_threshold'],
        'stage3_all_three': ['sbv_tightening_stop_loss_max_multiplier'],
    }
    DEFAULTS = {
        'dxy_easing_z_threshold': -1.0, 'dxy_tightening_z_threshold': 1.0,
        'dxy_tightening_dd_threshold': 3, 'eem_easing_z_threshold': 1.0,
        'eem_tightening_z_threshold': -1.0, 'sbv_tightening_stop_loss_max_multiplier': 1.5,
    }
    def parsimony_distance(row, stage):
        return sum(1 for f in STAGE_FIELDS[stage] if row[f] != DEFAULTS[f])
    # D-12 sort: median_eval_cagr_pct desc, median_eval_sharpe_rf3 (computed below) desc, parsimony asc, combo_id asc
    # Note: median_eval_sharpe_rf3 is not in row schema — compute inline from sharpe_rf3_eval_{y} cols
    def median_eval_sharpe(row):
        vals = [row[f'sharpe_rf3_eval_{y}'] for y in EVAL_YEARS if not np.isnan(row[f'sharpe_rf3_eval_{y}'])]
        return float(np.median(vals)) if vals else float('-inf')
    ranked = sorted(accepted, key=lambda r: (
        -r['median_eval_cagr_pct'],               # primary desc
        -median_eval_sharpe(r),                    # tiebreak desc
        parsimony_distance(r, stage),              # tiebreak asc (fewer non-default wins)
        r['combo_id'],                             # deterministic last resort
    ))
    winner = ranked[0] if ranked else None
    runners_up = ranked[1:4]    # top-3 runners-up per D-11 (ranks 2, 3, 4 = 3 entries)
    return winner, runners_up
    ```

    **B) `write_results_csv(all_rows: list[dict], path: str) -> None`**

    Writes CSV with canonical column order (D-claude-1 suggestion — planner may adjust but keep exact column names from Task 3 schema):
    ```python
    COL_ORDER = (
        ['stage', 'combo_id', 'config_name']
        + ['dxy_easing_z_threshold', 'dxy_tightening_z_threshold', 'dxy_tightening_dd_threshold',
           'eem_easing_z_threshold', 'eem_tightening_z_threshold',
           'sbv_tightening_stop_loss_max_multiplier',
           'dxy_window_days', 'eem_window_days', 'sbv_decay_days', 'macro_filter_enabled']
        + ['cagr_train_pct', 'sharpe_rf3_train', 'max_dd_train_pct']
        + [f'cagr_eval_{y}_pct' for y in EVAL_YEARS]
        + [f'sharpe_rf3_eval_{y}' for y in EVAL_YEARS]
        + [f'max_dd_eval_{y}_pct' for y in EVAL_YEARS]
        + [f'degradation_{y}' for y in EVAL_YEARS]
        + ['median_degradation', 'median_eval_cagr_pct', 'eval_years_count']
        + ['accepted', 'rejection_reason']
        + ['error_train'] + [f'error_year_{y}' for y in EVAL_YEARS]
    )
    df = pd.DataFrame(all_rows)
    df = df[COL_ORDER]   # reorder + sanity check all cols present
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    ```

    **C) `write_best_json(stages: dict, path: str) -> None`**

    D-11 schema VERBATIM — write this exact structure:
    ```python
    def _config_tuple(row):
        """Extract full 10-field macro config from a row for dataclasses.replace replay."""
        return {
            'dxy_easing_z_threshold': _native(row['dxy_easing_z_threshold']),
            'dxy_tightening_z_threshold': _native(row['dxy_tightening_z_threshold']),
            'dxy_tightening_dd_threshold': _native(row['dxy_tightening_dd_threshold']),
            'eem_easing_z_threshold': _native(row['eem_easing_z_threshold']),
            'eem_tightening_z_threshold': _native(row['eem_tightening_z_threshold']),
            'sbv_tightening_stop_loss_max_multiplier': _native(row['sbv_tightening_stop_loss_max_multiplier']),
            'dxy_window_days': _native(row['dxy_window_days']),
            'eem_window_days': _native(row['eem_window_days']),
            'sbv_decay_days': _native(row['sbv_decay_days']),
            'macro_filter_enabled': True,
        }
    def _metrics_tuple(row):
        return {
            'train_cagr_pct': _native(row['cagr_train_pct']),
            'median_eval_cagr_pct': _native(row['median_eval_cagr_pct']),
            'median_degradation': _native(row['median_degradation']),
            'median_eval_sharpe_rf3': _native(median_eval_sharpe(row)),   # from select_winner helper
            'median_eval_max_dd_pct': _native(float(np.median([row[f'max_dd_eval_{y}_pct'] for y in EVAL_YEARS if not np.isnan(row[f'max_dd_eval_{y}_pct'])] or [float('nan')]))),
        }
    def _entry(row, rank):
        return {'config': _config_tuple(row), 'metrics': _metrics_tuple(row), 'rank': rank}
    payload = {
        'schema_version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'engine_git_hash': _get_git_head(),   # subprocess.run(['git', 'rev-parse', 'HEAD'], ...) — strip
        'train_window': f'{TRAIN_START}..{TRAIN_END}',
        'eval_years': list(EVAL_YEARS),
        'oos_holdout': f'{OOS_FENCE}..2026-12-31 (untouched)',
        'ranking_metric': 'median_eval_cagr_pct',
        'stage1_dxy': {'winner': _entry(stages['stage1_dxy']['winner'], 1),
                       'runners_up': [_entry(r, i+2) for i, r in enumerate(stages['stage1_dxy']['runners_up'])]},
        'stage2_eem': {...same for stage2...},
        'stage3_all_three': {...same for stage3...},
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    ```

    Also add `_native(v)` helper (lift from select_v9_best.py:85-89 — `try: return v.item()` pattern) and `_get_git_head()` helper:
    ```python
    def _get_git_head() -> str:
        import subprocess
        try:
            return subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        except Exception:
            return 'unknown'
    ```

    Also add `_top3_nan_guard(stage_name, stage_rows)` — D-18 enforcement:
    ```python
    def _top3_nan_guard(stage_name: str, stage_rows: list[dict]) -> None:
        """Raise SummaryError if any of the top-3 accepted combos (by D-12 ranking) has NaN eval-year metric (D-18)."""
        accepted = [r for r in stage_rows if r['accepted']]
        if not accepted:
            return  # no accepted — nothing to guard
        # Use same ranking as select_winner
        winner, runners_up = select_winner(stage_rows, stage_name)
        top3 = [winner] + runners_up[:2]   # top-3 = winner + 2 runners-up
        for row in top3:
            if row is None:
                continue
            for y in EVAL_YEARS:
                if np.isnan(row[f'cagr_eval_{y}_pct']):
                    raise SummaryError(
                        f"Stage {stage_name} top-3 winner '{row['config_name']}' has NaN cagr_eval_{y}_pct — selection unsafe"
                    )
    ```
  </action>
  <verify>
    <automated>python -c "from analysis.walkforward_grid import select_winner, write_results_csv, write_best_json, _top3_nan_guard, _native, _get_git_head; import numpy as np; fake_rows = [{'stage':'stage1_dxy','combo_id':0,'config_name':'c0','dxy_easing_z_threshold':-1.0,'dxy_tightening_z_threshold':1.0,'dxy_tightening_dd_threshold':3,'median_eval_cagr_pct':10.0,'accepted':True, **{f'sharpe_rf3_eval_{y}':1.0 for y in [2019,2020,2021,2022,2023,2024]}, **{f'cagr_eval_{y}_pct':10.0 for y in [2019,2020,2021,2022,2023,2024]}, **{f'max_dd_eval_{y}_pct':-15.0 for y in [2019,2020,2021,2022,2023,2024]}},{'stage':'stage1_dxy','combo_id':1,'config_name':'c1','dxy_easing_z_threshold':-0.5,'dxy_tightening_z_threshold':1.5,'dxy_tightening_dd_threshold':2,'median_eval_cagr_pct':12.0,'accepted':True, **{f'sharpe_rf3_eval_{y}':1.2 for y in [2019,2020,2021,2022,2023,2024]}, **{f'cagr_eval_{y}_pct':12.0 for y in [2019,2020,2021,2022,2023,2024]}, **{f'max_dd_eval_{y}_pct':-18.0 for y in [2019,2020,2021,2022,2023,2024]}}]; w, ru = select_winner(fake_rows, 'stage1_dxy'); assert w['combo_id'] == 1, f'wrong winner {w}'; assert isinstance(_get_git_head(), str); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def select_winner" analysis/walkforward_grid.py` returns 1
    - `grep -c "def write_results_csv" analysis/walkforward_grid.py` returns 1
    - `grep -c "def write_best_json" analysis/walkforward_grid.py` returns 1
    - `grep -c "'schema_version': 1" analysis/walkforward_grid.py` returns 1
    - `grep -c "'ranking_metric': 'median_eval_cagr_pct'" analysis/walkforward_grid.py` returns 1
    - `grep -c "'stage1_dxy'" analysis/walkforward_grid.py` returns at least 2
    - `grep -c "'stage2_eem'" analysis/walkforward_grid.py` returns at least 2
    - `grep -c "'stage3_all_three'" analysis/walkforward_grid.py` returns at least 2
    - `grep -c "SummaryError" analysis/walkforward_grid.py` returns at least 3 (class def + raise + import)
    - `grep -c "parsimony_distance" analysis/walkforward_grid.py` returns at least 1 (D-12 tiebreak)
    - Inline python verify above prints OK (higher median_eval_cagr wins)
  </acceptance_criteria>
  <done>
    select_winner ranks by median_eval_cagr_pct → median_eval_sharpe → parsimony → combo_id; write_results_csv writes all D-06 columns with COL_ORDER; write_best_json writes D-11 schema verbatim (schema_version=1, stage1_dxy/stage2_eem/stage3_all_three, winner + runners_up with full 10-field config + 5-metric tuple); _top3_nan_guard raises SummaryError per D-18.
  </done>
</task>

<task type="auto">
  <name>Task 5: main() orchestrator — load data, run 3 stages serial, write outputs, print summary</name>
  <files>analysis/walkforward_grid.py</files>
  <read_first>
    - analysis/validate_v9.py (lines 279-340 — main() entry pattern; lines 291-312 load data + build + assert; top-level log-to-file pattern)
    - analysis/sweep_v9_atr.py (lines 136-217 — main orchestrator: load, grid loop with tqdm, CSV write, top-N NaN SummaryError, print top-5)
    - .planning/phases/45-walk-forward-grid-search/45-CONTEXT.md (D-17 serial+tqdm, D-18 fail-summary, D-claude-3 tqdm description)
  </read_first>
  <action>
    Replace the Task-1 placeholder `def main(): raise NotImplementedError` with the full orchestrator. Structure VERBATIM:

    ```python
    def main() -> None:
        print("=" * 70)
        print("PHASE 45: WALK-FORWARD GRID SEARCH (WF-01 / WF-02 / WF-03)")
        print(f"  Train: {TRAIN_START}..{TRAIN_END}")
        print(f"  Eval years: {EVAL_YEARS}")
        print(f"  OOS holdout (UNTOUCHED): {OOS_FENCE}..2026-12-31")
        print(f"  Accept gate: median_degradation < {DEGRADATION_THRESHOLD:.2f} AND median(eval CAGR) > {MEDIAN_CAGR_FLOOR:.1f}%")
        print("=" * 70)

        # Load baseline for context (D-Claude-4)
        baseline_cagr = _load_reconciled_baseline_cagr()
        if not np.isnan(baseline_cagr):
            print(f"Reconciled v6.0 baseline CAGR (context only, not a gate): {baseline_cagr:.2f}%")

        # D-14 OOS-guarded data load
        print("\nLoading VN30 data (2015-01-01..2024-12-31)...")
        df = load_vn30_data()
        print(f"  {len(df)} rows ({df['date'].min().date()} -> {df['date'].max().date()})")

        # Accumulate all 39 rows across stages for single CSV write
        all_rows: list[dict] = []
        stages_result: dict = {}

        # ── STAGE 1: DXY (27 combos) ────────────────────────────────────
        print(f"\n{'─' * 70}\nSTAGE 1 — DXY sweep (27 combos)\n{'─' * 70}")
        stage1_grid = build_combo_grid('stage1_dxy', {})
        assert len(stage1_grid) == 27, f"stage1 expected 27, got {len(stage1_grid)}"
        stage1_rows = []
        for i, overrides in enumerate(tqdm(stage1_grid, desc='Stage1 DXY')):
            row = run_combo(df, overrides, 'stage1_dxy', i)
            stage1_rows.append(row)
            all_rows.append(row)
        _top3_nan_guard('stage1_dxy', stage1_rows)
        winner1, runners_up1 = select_winner(stage1_rows, 'stage1_dxy')
        stages_result['stage1_dxy'] = {'winner': winner1, 'runners_up': runners_up1}
        if winner1 is None:
            print("  WARNING: Stage 1 has NO accepted combos. Stages 2/3 will sweep against VN30_PRESET DXY defaults.")
            stage1_locked = {}    # fallback — use VN30_PRESET defaults (planner discretion: alternative is abort)
        else:
            stage1_locked = {f: winner1[f] for f in ['dxy_easing_z_threshold', 'dxy_tightening_z_threshold', 'dxy_tightening_dd_threshold']}
            print(f"  Stage 1 winner: {winner1['config_name']} | median_eval_cagr={winner1['median_eval_cagr_pct']:.2f}% | median_degradation={winner1['median_degradation']:.3f}")

        # ── STAGE 2: EEM (9 combos, DXY locked) ─────────────────────────
        print(f"\n{'─' * 70}\nSTAGE 2 — EEM sweep (9 combos, DXY locked)\n{'─' * 70}")
        stage2_grid = build_combo_grid('stage2_eem', stage1_locked)
        assert len(stage2_grid) == 9, f"stage2 expected 9, got {len(stage2_grid)}"
        stage2_rows = []
        for i, overrides in enumerate(tqdm(stage2_grid, desc='Stage2 EEM')):
            row = run_combo(df, overrides, 'stage2_eem', i)
            stage2_rows.append(row)
            all_rows.append(row)
        _top3_nan_guard('stage2_eem', stage2_rows)
        winner2, runners_up2 = select_winner(stage2_rows, 'stage2_eem')
        stages_result['stage2_eem'] = {'winner': winner2, 'runners_up': runners_up2}
        if winner2 is None:
            print("  WARNING: Stage 2 has NO accepted combos.")
            stage2_locked = dict(stage1_locked)   # only DXY locked downstream
        else:
            stage2_locked = dict(stage1_locked)
            stage2_locked.update({f: winner2[f] for f in ['eem_easing_z_threshold', 'eem_tightening_z_threshold']})
            print(f"  Stage 2 winner: {winner2['config_name']} | median_eval_cagr={winner2['median_eval_cagr_pct']:.2f}% | median_degradation={winner2['median_degradation']:.3f}")

        # ── STAGE 3: SBV (3 combos, DXY+EEM locked) ─────────────────────
        print(f"\n{'─' * 70}\nSTAGE 3 — SBV sweep (3 combos, DXY+EEM locked)\n{'─' * 70}")
        stage3_grid = build_combo_grid('stage3_all_three', stage2_locked)
        assert len(stage3_grid) == 3, f"stage3 expected 3, got {len(stage3_grid)}"
        stage3_rows = []
        for i, overrides in enumerate(tqdm(stage3_grid, desc='Stage3 SBV')):
            row = run_combo(df, overrides, 'stage3_all_three', i)
            stage3_rows.append(row)
            all_rows.append(row)
        _top3_nan_guard('stage3_all_three', stage3_rows)
        winner3, runners_up3 = select_winner(stage3_rows, 'stage3_all_three')
        stages_result['stage3_all_three'] = {'winner': winner3, 'runners_up': runners_up3}
        if winner3 is not None:
            print(f"  Stage 3 winner: {winner3['config_name']} | median_eval_cagr={winner3['median_eval_cagr_pct']:.2f}% | median_degradation={winner3['median_degradation']:.3f}")

        # ── Outputs ─────────────────────────────────────────────────────
        assert len(all_rows) == 39, f"expected 39 total combos, got {len(all_rows)}"
        write_results_csv(all_rows, RESULTS_CSV)
        print(f"\nWrote {RESULTS_CSV} ({len(all_rows)} rows)")
        if all(s['winner'] is not None for s in stages_result.values()):
            write_best_json(stages_result, BEST_JSON)
            print(f"Wrote {BEST_JSON} (3 stages × 1 winner + 3 runners-up)")
        else:
            print(f"WARNING: at least one stage has no accepted winner — {BEST_JSON} NOT written")

        # Accept/reject summary
        accepted = sum(1 for r in all_rows if r['accepted'])
        print(f"\nSummary: {accepted}/{len(all_rows)} combos accepted (D-09 gate: < {DEGRADATION_THRESHOLD*100:.0f}% degradation AND > {MEDIAN_CAGR_FLOOR:.0f}% median eval CAGR)")

    if __name__ == '__main__':
        main()
    ```

    Do NOT wrap in try/except at top level — per-combo errors are already captured in row dicts; SummaryError from _top3_nan_guard is intended to halt the script (D-18 fail-loud).
  </action>
  <verify>
    <automated>python -c "import analysis.walkforward_grid as m; import inspect; src = inspect.getsource(m.main); assert 'stage1_dxy' in src and 'stage2_eem' in src and 'stage3_all_three' in src; assert 'tqdm' in src; assert '_top3_nan_guard' in src; assert 'write_results_csv' in src; assert 'write_best_json' in src; assert 'len(all_rows) == 39' in src; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def main()" analysis/walkforward_grid.py` returns 1
    - `grep -c "STAGE 1" analysis/walkforward_grid.py` returns at least 1
    - `grep -c "STAGE 2" analysis/walkforward_grid.py` returns at least 1
    - `grep -c "STAGE 3" analysis/walkforward_grid.py` returns at least 1
    - `grep -c "assert len(all_rows) == 39" analysis/walkforward_grid.py` returns 1
    - `grep -c "assert len(stage1_grid) == 27" analysis/walkforward_grid.py` returns 1
    - `grep -c "assert len(stage2_grid) == 9" analysis/walkforward_grid.py` returns 1
    - `grep -c "assert len(stage3_grid) == 3" analysis/walkforward_grid.py` returns 1
    - `grep -c "write_results_csv(all_rows, RESULTS_CSV)" analysis/walkforward_grid.py` returns 1
    - `grep -c "write_best_json(stages_result, BEST_JSON)" analysis/walkforward_grid.py` returns 1
    - `grep -c "if __name__ == '__main__':" analysis/walkforward_grid.py` returns 1
    - Inline python verify above prints OK
  </acceptance_criteria>
  <done>
    main() orchestrates: OOS-guarded data load → 3 sequential stages (27+9+3 combos) with tqdm → per-stage winner lock propagation → top-3 NaN guard per stage → single CSV write of all 39 rows → JSON write of 3 stage winners + runners-up. Plan 03 executes this to produce the actual artifacts.
  </done>
</task>

</tasks>

<verification>
After all 5 tasks complete, verify the module is a coherent whole (not just syntactically correct):

- `python -c "import analysis.walkforward_grid as m; assert callable(m.main) and callable(m.load_vn30_data) and callable(m.build_combo_grid) and callable(m.run_combo) and callable(m.select_winner) and callable(m.write_results_csv) and callable(m.write_best_json); print('all 7 functions present')"` exits 0.
- `python -c "from analysis.walkforward_grid import build_combo_grid; assert len(build_combo_grid('stage1_dxy', {})) + len(build_combo_grid('stage2_eem', {'dxy_easing_z_threshold':-1.0, 'dxy_tightening_z_threshold':1.0, 'dxy_tightening_dd_threshold':3})) + len(build_combo_grid('stage3_all_three', {'dxy_easing_z_threshold':-1.0,'dxy_tightening_z_threshold':1.0,'dxy_tightening_dd_threshold':3,'eem_easing_z_threshold':1.0,'eem_tightening_z_threshold':-1.0})) == 39; print('39 combos')"` exits 0.
- Script syntax check: `python -m py_compile analysis/walkforward_grid.py` exits 0.
- Executor does NOT run the full sweep in this plan — Plan 03 executes. Plan 01 lands a correct-by-construction script.

**Out-of-scope self-check (MUST all be NO):**
- Did this plan touch `strategies/mdm_hybrid/*.py`? → must be NO
- Did this plan add new MDMV2Config fields? → must be NO
- Did this plan modify `analysis/validate_v9.py`? → must be NO (compute_metrics reused via import per D-16; per-year slicing done by caller in run_combo)
- Did this plan touch `docs/`, `dashboard/`, or Phase 43 CSVs? → must be NO
</verification>

<success_criteria>
- `analysis/walkforward_grid.py` exists, is importable, is a ~400-600 line single-file orchestrator
- All constants match D-14 (OOS_FENCE='2025-01-01'), D-05 (TRAIN_END='2018-12-31'), D-09 (DEGRADATION_THRESHOLD=0.30)
- `compute_metrics` is IMPORTED from `analysis.validate_v9`, not reimplemented (D-16)
- Grid values are verbatim D-03: 3×3×3=27 DXY, 3×3=9 EEM, 3=SBV SBV → 39 total
- CSV schema contains all D-06 columns (config + train + 18 per-year eval + 6 degradation + 3 aggregate + accept + error)
- JSON schema is D-11 verbatim (schema_version=1, stage1_dxy/stage2_eem/stage3_all_three with winner + runners_up, full 10-field config tuple per entry)
- D-15 test hook: `load_vn30_data(df_override=...)` kwarg present for synthetic injection
- D-18 top-3 NaN SummaryError guard present
- Script runs successfully in Plan 03 and produces CSV + JSON artifacts
</success_criteria>

<output>
After completion, executor creates `.planning/phases/45-walk-forward-grid-search/45-01-SUMMARY.md` summarizing: key helper functions, CSV/JSON schemas, constants, any deviations from CONTEXT.md decisions (D-01..D-18), and verification command outputs.
</output>
