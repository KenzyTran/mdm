"""Phase 45: Walk-Forward Grid Search for VN30 macro filter thresholds (WF-01 / WF-02 / WF-03).

Staged three-stage grid sweep over the 6 policy fields of the Phase 44 macro filter
(DXY easing/tightening z-thresholds + DXY tightening DD threshold → 27 combos;
 EEM easing/tightening z-thresholds → 9 combos; SBV tightening stop-loss multiplier →
 3 combos; 39 total engine runs). For each combo, the engine is run ONCE on VN30
2015-2024 (D-04 single-run-and-slice), then metrics are computed per-slice on:

  - Train slice: date <= 2018-12-31 (4 calendar years, FIXED per D-05, no expanding).
  - Eval slices: per-year for y in [2019, 2020, 2021, 2022, 2023, 2024] (6 walk-forward
    evaluations per combo).

Acceptance (D-09 — ROADMAP WF-02 + sanity floor):

  combo.accepted = (median_degradation < 0.30) AND (median(eval CAGR across 6 years) > 0.0%)

  where degradation_{y} = (cagr_train - cagr_eval_{y}) / abs(cagr_train) and
  median_degradation is numpy.median(signed per-year degradations).

  Rejected combos are KEPT in output/v10_grid_results.csv with rejection_reason
  populated (ROADMAP SC-2 — no silent drops).

Windows (D-14 — reproducibility absolute, no CLI overrides):

  TRAIN_START = 2015-01-01
  TRAIN_END   = 2018-12-31
  EVAL_YEARS  = [2019, 2020, 2021, 2022, 2023, 2024]   (EVAL_END = 2024-12-31)
  OOS_FENCE   = 2025-01-01 (any data >= this date MUST NOT enter selection)

The OOS holdout 2025-2026 is excluded by data-load window AND by a runtime
assertion inside load_vn30_data (fail-loud with 'OOS leak' message; tested by
tests/test_walkforward_oos_guard.py::test_assert_fires_on_2025_data — Plan 02).

Outputs (consumed by Phase 46 VAL-01 A/B scenarios):

  output/v10_grid_results.csv   — 39 rows × ~50 columns (configs + train + 18 eval-year
                                   + 6 degradations + 3 aggregates + accept + 7 error cols)
  output/v10_grid_best.json     — 3 stages × (1 winner + 3 runners-up), schema_version=1,
                                   each entry has the FULL 10-field macro config tuple
                                   for direct dataclasses.replace(VN30_PRESET, **config) replay.

Run (~10-15 minutes serial, single tqdm bar per stage — D-17):

    uv run python analysis/walkforward_grid.py

Implementation discipline (D-16): compute_metrics is IMPORTED from analysis.validate_v9,
NOT reimplemented. Drift between Phase 41/42/45 metric formulas is a v10.0 integrity risk.
"""

import sys
import os
import json
import itertools
import traceback
import subprocess
from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET
from analysis.validate_v9 import compute_metrics


# ── Module constants (D-14 / D-05 / D-09 — reproducibility absolute) ────
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


class SummaryError(RuntimeError):
    """Raised when any of the top-3 accepted combos in a stage has NaN eval-year metrics (D-18)."""


def load_vn30_data(df_override: "pd.DataFrame | None" = None) -> pd.DataFrame:
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
    # D-14 runtime assert — STRICT < (not <=) because OOS_FENCE is the exclusion boundary for 2025
    assert df['date'].max() < pd.Timestamp(OOS_FENCE), (
        f"OOS leak: max date {df['date'].max()} crossed OOS_FENCE {OOS_FENCE}"
    )
    return df


def _load_reconciled_baseline_cagr() -> float:
    """Return cagr_pct from output/v10_reconciled_baseline.json for context print only.

    D-Claude-4: Phase 45 does NOT gate on the reconciled baseline (Phase 46 does).
    This is purely informational for the main() banner. Any read failure returns
    NaN and continues — never blocks the sweep.
    """
    try:
        with open(RECONCILED_BASELINE, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)
        return float(payload['cagr_pct'])
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return float('nan')


# ── D-03 grid values (exact per CONTEXT.md; defaults sit at the center cell) ─
DXY_EASING_Z = [-1.5, -1.0, -0.5]                        # default -1.0
DXY_TIGHTENING_Z = [0.5, 1.0, 1.5]                        # default +1.0
DXY_TIGHTENING_DD = [2, 3, 4]                             # default 3
EEM_EASING_Z = [0.5, 1.0, 1.5]                            # default +1.0
EEM_TIGHTENING_Z = [-1.5, -1.0, -0.5]                     # default -1.0
SBV_STOP_LOSS_MAX_MULT = [1.0, 1.5, 2.0]                  # default 1.5 (bounded <= stop_loss_max_multiplier=2.5)


def build_combo_grid(stage: str, locked_overrides: dict) -> list:
    """Build the list of override dicts for a given stage (D-01 staged sweep).

    Each returned override dict is passed to
    `replace(VN30_PRESET, macro_filter_enabled=True, **overrides)` — VN30_PRESET
    supplies defaults for any field NOT in the dict (notably the LOCKED windows
    dxy_window_days=20, eem_window_days=20, sbv_decay_days=90 per D-02).

    Args:
        stage: One of 'stage1_dxy', 'stage2_eem', 'stage3_all_three'.
        locked_overrides: Field overrides inherited from prior-stage winners.
            - Stage 1 (root): ignored (pass {}).
            - Stage 2: must include the 3 Stage-1 DXY winner fields.
            - Stage 3: must include Stage-1 (3 DXY) + Stage-2 (2 EEM) winner fields.

    Returns:
        List of override dicts (27 / 9 / 3 entries for stages 1 / 2 / 3).

    Raises:
        ValueError: Unknown stage name.
    """
    if stage == 'stage1_dxy':
        combos = []
        for dxy_e, dxy_t, dxy_dd in itertools.product(DXY_EASING_Z, DXY_TIGHTENING_Z, DXY_TIGHTENING_DD):
            combos.append({
                'dxy_easing_z_threshold': float(dxy_e),
                'dxy_tightening_z_threshold': float(dxy_t),
                'dxy_tightening_dd_threshold': int(dxy_dd),
            })
        assert len(combos) == 27, f"stage1 expected 27, got {len(combos)}"
        return combos

    if stage == 'stage2_eem':
        combos = []
        for eem_e, eem_t in itertools.product(EEM_EASING_Z, EEM_TIGHTENING_Z):
            overrides = dict(locked_overrides)
            overrides.update({
                'eem_easing_z_threshold': float(eem_e),
                'eem_tightening_z_threshold': float(eem_t),
            })
            combos.append(overrides)
        assert len(combos) == 9, f"stage2 expected 9, got {len(combos)}"
        return combos

    if stage == 'stage3_all_three':
        combos = []
        for sbv_mult in SBV_STOP_LOSS_MAX_MULT:
            overrides = dict(locked_overrides)
            overrides.update({
                'sbv_tightening_stop_loss_max_multiplier': float(sbv_mult),
            })
            combos.append(overrides)
        assert len(combos) == 3, f"stage3 expected 3, got {len(combos)}"
        return combos

    raise ValueError(f"Unknown stage: {stage}")


# Canonical macro config field tuple (10 fields per Phase 44 D-15) — written into
# each CSV row + JSON entry so Phase 46 can dataclasses.replace without lookups.
MACRO_CONFIG_FIELDS = [
    'dxy_easing_z_threshold',
    'dxy_tightening_z_threshold',
    'dxy_tightening_dd_threshold',
    'eem_easing_z_threshold',
    'eem_tightening_z_threshold',
    'sbv_tightening_stop_loss_max_multiplier',
    'dxy_window_days',
    'eem_window_days',
    'sbv_decay_days',
    'macro_filter_enabled',
]


def _init_row_nan_metrics(row: dict) -> None:
    """Populate all metric / degradation / aggregate columns with NaN.

    Used by the train_run_failed early-return path (D-10).
    """
    row['cagr_train_pct'] = float('nan')
    row['sharpe_rf3_train'] = float('nan')
    row['max_dd_train_pct'] = float('nan')
    for y in EVAL_YEARS:
        row[f'cagr_eval_{y}_pct'] = float('nan')
        row[f'sharpe_rf3_eval_{y}'] = float('nan')
        row[f'max_dd_eval_{y}_pct'] = float('nan')
        row[f'degradation_{y}'] = float('nan')
        row[f'error_year_{y}'] = ''
    row['median_degradation'] = float('nan')
    row['median_eval_cagr_pct'] = float('nan')
    row['eval_years_count'] = 0


def run_combo(df: pd.DataFrame, overrides: dict, stage: str, combo_id: int) -> dict:
    """Run one combo: single engine pass on 2015-2024 + train slice + 6 per-year eval slices.

    Implements D-04 (single-run-and-slice), D-08 (signed per-year degradation),
    D-09 (AND-gate accept), D-10 (NaN / insufficient-coverage handling), D-16
    (compute_metrics reused verbatim via import).

    Args:
        df: Full post-indicator VN30 DataFrame 2015-2024 (from load_vn30_data).
        overrides: dict suitable for replace(VN30_PRESET, macro_filter_enabled=True, **overrides).
        stage: 'stage1_dxy' | 'stage2_eem' | 'stage3_all_three'.
        combo_id: Sequential id within the stage (0-indexed).

    Returns:
        Row dict with D-06 schema (config + train + 18 eval-year + 6 degradation +
        3 aggregate + accept + 7 error columns).
    """
    cfg = replace(VN30_PRESET, macro_filter_enabled=True, **overrides)

    # Seed row with full 10-field macro tuple (Phase 46 replays via dataclasses.replace)
    row: dict = {
        'stage': stage,
        'combo_id': int(combo_id),
        'config_name': f"{stage}-c{int(combo_id)}",
        # Config fields lifted directly from cfg so locked + overridden fields are both present
        'dxy_easing_z_threshold': float(cfg.dxy_easing_z_threshold),
        'dxy_tightening_z_threshold': float(cfg.dxy_tightening_z_threshold),
        'dxy_tightening_dd_threshold': int(cfg.dxy_tightening_dd_threshold),
        'eem_easing_z_threshold': float(cfg.eem_easing_z_threshold),
        'eem_tightening_z_threshold': float(cfg.eem_tightening_z_threshold),
        'sbv_tightening_stop_loss_max_multiplier': float(cfg.sbv_tightening_stop_loss_max_multiplier),
        'dxy_window_days': int(cfg.dxy_window_days),
        'eem_window_days': int(cfg.eem_window_days),
        'sbv_decay_days': int(cfg.sbv_decay_days),
        'macro_filter_enabled': bool(cfg.macro_filter_enabled),
        'error_train': '',
    }

    # ── D-04 single full-period run (2015-2024) ────────────────────────
    try:
        engine = HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False))
        results = engine.run(df.copy())
    except Exception as exc:
        row['error_train'] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:200]}"
        _init_row_nan_metrics(row)
        row['accepted'] = False
        row['rejection_reason'] = 'train_run_failed'
        return row

    # ── Train slice: date <= TRAIN_END (D-04) ───────────────────────────
    train_slice = results[results['date'] <= pd.Timestamp(TRAIN_END)].copy().reset_index(drop=True)
    try:
        train_m = compute_metrics(train_slice)
        row['cagr_train_pct'] = float(train_m['cagr_pct'])
        row['sharpe_rf3_train'] = float(train_m['sharpe_rf3'])
        row['max_dd_train_pct'] = float(train_m['max_dd_pct'])
    except Exception as exc:
        row['error_train'] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:200]}"
        _init_row_nan_metrics(row)
        row['accepted'] = False
        row['rejection_reason'] = 'train_metrics_failed'
        return row

    # ── Per-year eval slices (D-04) ─────────────────────────────────────
    valid_eval_cagrs: list = []
    degradations: list = []
    for y in EVAL_YEARS:
        year_slice = results[results['date'].dt.year == y].copy().reset_index(drop=True)
        try:
            ym = compute_metrics(year_slice)
            row[f'cagr_eval_{y}_pct'] = float(ym['cagr_pct'])
            row[f'sharpe_rf3_eval_{y}'] = float(ym['sharpe_rf3'])
            row[f'max_dd_eval_{y}_pct'] = float(ym['max_dd_pct'])
            row[f'error_year_{y}'] = ''
            # D-08 signed degradation
            cagr_t = row['cagr_train_pct']
            cagr_y = row[f'cagr_eval_{y}_pct']
            if cagr_t != 0 and not np.isnan(cagr_t) and not np.isnan(cagr_y):
                deg = (cagr_t - cagr_y) / abs(cagr_t)
                row[f'degradation_{y}'] = float(deg)
                degradations.append(float(deg))
                valid_eval_cagrs.append(float(cagr_y))
            else:
                row[f'degradation_{y}'] = float('nan')
        except Exception as exc:
            row[f'error_year_{y}'] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:200]}"
            row[f'cagr_eval_{y}_pct'] = float('nan')
            row[f'sharpe_rf3_eval_{y}'] = float('nan')
            row[f'max_dd_eval_{y}_pct'] = float('nan')
            row[f'degradation_{y}'] = float('nan')

    row['eval_years_count'] = int(len(valid_eval_cagrs))
    row['median_eval_cagr_pct'] = float(np.median(valid_eval_cagrs)) if valid_eval_cagrs else float('nan')
    row['median_degradation'] = float(np.median(degradations)) if degradations else float('nan')

    # ── D-09 accept gate + D-10 coverage guard ──────────────────────────
    if row['eval_years_count'] < 5:
        row['accepted'] = False
        row['rejection_reason'] = f"insufficient_eval_coverage {row['eval_years_count']}/6"
    elif np.isnan(row['median_degradation']):
        row['accepted'] = False
        row['rejection_reason'] = 'median_degradation_nan'
    elif row['median_degradation'] >= DEGRADATION_THRESHOLD:
        row['accepted'] = False
        row['rejection_reason'] = (
            f"median_degradation {row['median_degradation']:.3f} >= {DEGRADATION_THRESHOLD:.2f}"
        )
    elif row['median_eval_cagr_pct'] <= MEDIAN_CAGR_FLOOR:
        row['accepted'] = False
        row['rejection_reason'] = (
            f"median_eval_cagr {row['median_eval_cagr_pct']:.2f}% <= {MEDIAN_CAGR_FLOOR:.1f}%"
        )
    else:
        row['accepted'] = True
        row['rejection_reason'] = ''

    return row


# ── D-12 ranking + parsimony tiebreak helpers ──────────────────────────
STAGE_FIELDS = {
    'stage1_dxy': ['dxy_easing_z_threshold', 'dxy_tightening_z_threshold', 'dxy_tightening_dd_threshold'],
    'stage2_eem': ['eem_easing_z_threshold', 'eem_tightening_z_threshold'],
    'stage3_all_three': ['sbv_tightening_stop_loss_max_multiplier'],
}

# VN30_PRESET macro defaults (duplicated here for clarity; see strategies/mdm_hybrid/config.py:97-109)
# — Phase 44 D-15 center cells. Used by parsimony_distance.
DEFAULTS = {
    'dxy_easing_z_threshold': -1.0,
    'dxy_tightening_z_threshold': 1.0,
    'dxy_tightening_dd_threshold': 3,
    'eem_easing_z_threshold': 1.0,
    'eem_tightening_z_threshold': -1.0,
    'sbv_tightening_stop_loss_max_multiplier': 1.5,
}


def parsimony_distance(row: dict, stage: str) -> int:
    """D-12 parsimony tiebreak — count of searched fields that differ from VN30_PRESET default."""
    return sum(1 for f in STAGE_FIELDS[stage] if row[f] != DEFAULTS[f])


def median_eval_sharpe(row: dict) -> float:
    """Median of per-year Sharpe_rf3 across non-NaN eval years (D-12 secondary rank key)."""
    vals = [row[f'sharpe_rf3_eval_{y}'] for y in EVAL_YEARS if not np.isnan(row[f'sharpe_rf3_eval_{y}'])]
    return float(np.median(vals)) if vals else float('-inf')


def select_winner(stage_rows: list, stage: str) -> tuple:
    """Rank accepted combos per D-12 and return (winner, top-3 runners-up).

    D-12 ranking:
      1. median_eval_cagr_pct descending (primary)
      2. median_eval_sharpe_rf3 descending (risk-adjusted tiebreak, Phase 41 D-18 precedent)
      3. parsimony_distance ascending (fewer non-default fields wins — simpler generalizes)
      4. combo_id ascending (deterministic final tiebreak)

    Args:
        stage_rows: All row dicts for this stage (accepted + rejected).
        stage: 'stage1_dxy' | 'stage2_eem' | 'stage3_all_three' (for STAGE_FIELDS lookup).

    Returns:
        (winner_row, runners_up_rows). If no accepted combos, returns (None, []).
        runners_up is at most 3 entries (ranks 2, 3, 4).
    """
    accepted = [r for r in stage_rows if r.get('accepted') is True]
    if not accepted:
        return None, []
    ranked = sorted(accepted, key=lambda r: (
        -float(r['median_eval_cagr_pct']),    # primary desc
        -median_eval_sharpe(r),                # tiebreak desc
        parsimony_distance(r, stage),          # tiebreak asc
        int(r['combo_id']),                    # deterministic last resort
    ))
    winner = ranked[0]
    runners_up = ranked[1:4]     # top-3 runners-up per D-11 (ranks 2, 3, 4)
    return winner, runners_up


def write_results_csv(all_rows: list, path: str) -> None:
    """Write output/v10_grid_results.csv with canonical column order (D-claude-1 suggestion).

    All 39 rows (accepted + rejected) — ROADMAP SC-2 no silent drops.
    """
    col_order = (
        ['stage', 'combo_id', 'config_name']
        + MACRO_CONFIG_FIELDS
        + ['cagr_train_pct', 'sharpe_rf3_train', 'max_dd_train_pct']
        + [f'cagr_eval_{y}_pct' for y in EVAL_YEARS]
        + [f'sharpe_rf3_eval_{y}' for y in EVAL_YEARS]
        + [f'max_dd_eval_{y}_pct' for y in EVAL_YEARS]
        + [f'degradation_{y}' for y in EVAL_YEARS]
        + ['median_degradation', 'median_eval_cagr_pct', 'eval_years_count']
        + ['accepted', 'rejection_reason']
        + ['error_train']
        + [f'error_year_{y}' for y in EVAL_YEARS]
    )
    df_out = pd.DataFrame(all_rows)
    # Reorder + sanity-check all expected columns are present
    missing = [c for c in col_order if c not in df_out.columns]
    if missing:
        raise RuntimeError(f"write_results_csv: missing expected columns: {missing}")
    df_out = df_out[col_order]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df_out.to_csv(path, index=False)


def _native(v):
    """Cast numpy scalars to native Python types for clean JSON output.

    Lifted verbatim from analysis/select_v9_best.py:85-89.
    """
    try:
        return v.item()
    except AttributeError:
        return v


def _get_git_head() -> str:
    """Return git HEAD short hash, or 'unknown' if git unavailable."""
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return 'unknown'


def _config_tuple(row: dict) -> dict:
    """Extract full 10-field macro config from a row for dataclasses.replace replay (D-11)."""
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


def _metrics_tuple(row: dict) -> dict:
    """Extract 5-metric summary for D-11 JSON entry."""
    maxdd_vals = [row[f'max_dd_eval_{y}_pct'] for y in EVAL_YEARS if not np.isnan(row[f'max_dd_eval_{y}_pct'])]
    return {
        'train_cagr_pct': _native(row['cagr_train_pct']),
        'median_eval_cagr_pct': _native(row['median_eval_cagr_pct']),
        'median_degradation': _native(row['median_degradation']),
        'median_eval_sharpe_rf3': _native(median_eval_sharpe(row)),
        'median_eval_max_dd_pct': _native(float(np.median(maxdd_vals))) if maxdd_vals else float('nan'),
    }


def _entry(row: dict, rank: int) -> dict:
    """One JSON entry (winner or runner-up) with config + metrics + rank."""
    return {
        'config': _config_tuple(row),
        'metrics': _metrics_tuple(row),
        'rank': int(rank),
    }


def _stage_payload(stage_block: dict, starting_rank: int = 1) -> dict:
    """Serialize a single stage's {'winner': row_or_None, 'runners_up': list} into JSON shape."""
    winner = stage_block.get('winner')
    runners_up = stage_block.get('runners_up') or []
    return {
        'winner': _entry(winner, starting_rank) if winner is not None else None,
        'runners_up': [_entry(r, starting_rank + 1 + i) for i, r in enumerate(runners_up)],
    }


def write_best_json(stages: dict, path: str) -> None:
    """Write output/v10_grid_best.json per D-11 schema (schema_version=1).

    Args:
        stages: {'stage1_dxy': {'winner': row, 'runners_up': [...]},
                 'stage2_eem': {...},
                 'stage3_all_three': {...}}.
        path: Output path (typically BEST_JSON).
    """
    payload = {
        'schema_version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'engine_git_hash': _get_git_head(),
        'train_window': f'{TRAIN_START}..{TRAIN_END}',
        'eval_years': list(EVAL_YEARS),
        'oos_holdout': f'{OOS_FENCE}..2026-12-31 (untouched)',
        'ranking_metric': 'median_eval_cagr_pct',
        'stage1_dxy': _stage_payload(stages['stage1_dxy'], starting_rank=1),
        'stage2_eem': _stage_payload(stages['stage2_eem'], starting_rank=1),
        'stage3_all_three': _stage_payload(stages['stage3_all_three'], starting_rank=1),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)


def _top3_nan_guard(stage_name: str, stage_rows: list) -> None:
    """D-18 — raise SummaryError if any top-3 accepted combo has NaN eval-year metric.

    Mirrors Phase 40 D-10 top-5 safeguard: broken configs must not silently become winners.
    Only fires when there ARE accepted combos (no-accepted stages print a warning in main()).
    """
    accepted = [r for r in stage_rows if r.get('accepted') is True]
    if not accepted:
        return
    winner, runners_up = select_winner(stage_rows, stage_name)
    top3 = [winner] + list(runners_up[:2])    # winner + 2 runners-up = top-3
    for row in top3:
        if row is None:
            continue
        for y in EVAL_YEARS:
            if np.isnan(row[f'cagr_eval_{y}_pct']):
                raise SummaryError(
                    f"Stage {stage_name} top-3 winner '{row['config_name']}' has NaN "
                    f"cagr_eval_{y}_pct — selection unsafe"
                )


def main() -> None:
    raise NotImplementedError("main() orchestrator lands in Task 5")


if __name__ == '__main__':
    main()
