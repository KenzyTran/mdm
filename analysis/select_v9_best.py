"""Select best v9 config from a sweep CSV.

Usage:
    uv run python analysis/select_v9_best.py --stage atr   # reads v9_atr_sweep.csv -> writes v9_atr_best.{txt,json}
    uv run python analysis/select_v9_best.py --stage dd    # reads v9_dd_sweep.csv  -> writes v9_dd_best.{txt,json}

SWEEP-03 implementation:
  1. Load sweep CSV.
  2. Filter rows where max_dd_pct >= -30 (constraint: drawdown not worse than -30%).
  3. If no candidates pass -> raise RuntimeError + exit code 1 (D-16, no unconstrained fallback).
  4. Sort by sharpe_rf3 desc, cagr_pct desc, max_dd_pct desc (less-negative MaxDD wins per D-17).
  5. Top row -> write TXT (human table) + JSON (machine schema per D-21).
"""

import sys
import os
import argparse
import json
from datetime import datetime, timezone
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
TRAIN_WINDOW = '2015-01-01..2021-12-31'
MAX_DD_FLOOR = -30.0        # keep rows where max_dd_pct >= MAX_DD_FLOOR (D-15 interpretation)

STAGE_CONFIG = {
    'atr': {
        'sweep_csv': 'v9_atr_sweep.csv',
        'best_txt': 'v9_atr_best.txt',
        'best_json': 'v9_atr_best.json',
        'param_fields': ['atr_buffer_k', 'atr_buffer_period', 'atr_buffer_consecutive_days'],
    },
    'dd': {
        'sweep_csv': 'v9_dd_sweep.csv',
        'best_txt': 'v9_dd_best.txt',
        'best_json': 'v9_dd_best.json',
        'param_fields': [
            'refined_dd_large_drop', 'refined_dd_small_drop', 'refined_dd_small_vol_percentile',
            'atr_buffer_k', 'atr_buffer_period', 'atr_buffer_consecutive_days',
        ],
    },
}

METRIC_FIELDS = [
    'sharpe_rf3', 'cagr_pct', 'max_dd_pct', 'transitions',
    'sell_count', 'ma50_breakdown_sell_share', 'buy_count',
    'buy_pct', 'cash_pct', 'sell_pct',
]


def select_best(df: pd.DataFrame) -> pd.Series:
    """Apply MaxDD >= -30 filter, sort by (sharpe_rf3, cagr_pct, max_dd_pct) desc, return top row.

    Raises:
        RuntimeError: if no rows pass the MaxDD constraint (D-16 strict -- no fallback).
    """
    # Drop rows that errored during sweep (NaN sharpe_rf3 means the config raised).
    clean = df[df['sharpe_rf3'].notna()].copy()
    # D-15 step 2: MaxDD constraint. "MaxDD <= -30%" = "drawdown not worse than -30".
    # Values are negative, so keep rows where max_dd_pct >= -30.
    candidates = clean[clean['max_dd_pct'] >= MAX_DD_FLOOR]
    if candidates.empty:
        raise RuntimeError(
            f"No configs pass MaxDD >= {MAX_DD_FLOOR}% constraint. "
            f"{len(clean)} non-error rows; best (shallowest) max_dd_pct was "
            f"{clean['max_dd_pct'].max() if not clean.empty else 'N/A'}. "
            f"Per D-16 no unconstrained fallback -- inspect the sweep CSV and revise the grid."
        )
    # D-17 tiebreak: sharpe_rf3 desc -> cagr_pct desc -> max_dd_pct desc (less negative wins).
    ranked = candidates.sort_values(
        by=['sharpe_rf3', 'cagr_pct', 'max_dd_pct'],
        ascending=[False, False, False],
    )
    return ranked.iloc[0]


def write_outputs(row: pd.Series, stage: str) -> None:
    """Write `output/v9_{stage}_best.txt` (human-readable) + `.json` (machine-readable per D-21)."""
    cfg = STAGE_CONFIG[stage]

    # Cast numpy numeric types to native Python for clean JSON.
    def _native(v):
        try:
            return v.item()
        except AttributeError:
            return v

    params = {f: _native(row[f]) for f in cfg['param_fields']}
    metrics = {f: _native(row[f]) for f in METRIC_FIELDS}

    payload = {
        'params': params,
        'metrics': metrics,
        'selected_at': datetime.now(timezone.utc).isoformat(),
        'train_window': TRAIN_WINDOW,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    json_path = os.path.join(OUTPUT_DIR, cfg['best_json'])
    with open(json_path, 'w') as fh:
        json.dump(payload, fh, indent=2)

    # Human-readable TXT: key-value layout (D-22 allows either ASCII table or key-value; pick key-value for simplicity).
    txt_lines = []
    txt_lines.append(f"v9 best config -- stage={stage}")
    txt_lines.append(f"selected_at: {payload['selected_at']}")
    txt_lines.append(f"train_window: {payload['train_window']}")
    txt_lines.append("")
    txt_lines.append("-- params --")
    for k, v in params.items():
        txt_lines.append(f"  {k}: {v}")
    txt_lines.append("")
    txt_lines.append("-- metrics --")
    for k, v in metrics.items():
        txt_lines.append(f"  {k}: {v}")

    txt_path = os.path.join(OUTPUT_DIR, cfg['best_txt'])
    with open(txt_path, 'w') as fh:
        fh.write('\n'.join(txt_lines) + '\n')

    print(f"Wrote {txt_path}")
    print(f"Wrote {json_path}")


def main():
    parser = argparse.ArgumentParser(description='Select best v9 sweep config (SWEEP-03).')
    parser.add_argument('--stage', choices=['atr', 'dd'], required=True,
                        help='Which sweep stage to select from.')
    args = parser.parse_args()

    stage = args.stage
    cfg = STAGE_CONFIG[stage]
    sweep_csv = os.path.join(OUTPUT_DIR, cfg['sweep_csv'])

    if not os.path.exists(sweep_csv):
        raise FileNotFoundError(
            f"Sweep CSV not found: {sweep_csv}. "
            f"Run `uv run python analysis/sweep_v9_{stage}.py` first."
        )

    df = pd.read_csv(sweep_csv)
    best = select_best(df)
    print(f"Best {stage} config: {best.get('config_name', '<no-name>')}")
    write_outputs(best, stage)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
