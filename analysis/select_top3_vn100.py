"""Select top-3 parameter configs from VN100 in-sample sweep results.

Implements BT-02 SC4 + D-10..D-14 from Phase 32 context:
- Reads sweep_results.csv produced by analysis/sweep_vn100.py (BT-02).
- Sorts by Sharpe_rf3 descending; tie-breakers: CAGR desc, MaxDD desc (D-12).
  (MaxDD stored as negative; descending = closer to 0 = less severe = correct.)
- Enforces D-13 sanity gate: raises RuntimeError if any top-3 row has
  sanity_flag != "OK" (aborts Phase 33 handoff until manual review).
- Writes locked_params_top3.json per D-14 schema.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SWEEP_CSV = Path("docs/audits/phase32/sweep_results.csv")
OUTPUT_JSON = Path("docs/audits/phase32/locked_params_top3.json")
PERIOD = "2014-01-01..2018-12-31"
UNIVERSE = "current-VN100"
SELECTION_METRIC = "sharpe_rf3"

GRID_COLS = ["c_yoy", "a_cagr", "n_proximity", "hard_stop", "slots", "entry_option"]
METRIC_COLS = [
    "CAGR",
    "Sharpe_rf3",
    "MaxDD",
    "MaxDD_duration_days",
    "hit_rate",
    "turnover",
    "total_cost_drag_pct",
    "num_trades",
    "avg_hold_days",
]


# ---------------------------------------------------------------------------
# Core selection logic
# ---------------------------------------------------------------------------

def select_top3(df: pd.DataFrame) -> pd.DataFrame:
    """Return top-3 rows by Sharpe_rf3 with D-12 tie-breakers and D-13 gate.

    Args:
        df: Full sweep results DataFrame with columns including Sharpe_rf3,
            CAGR, MaxDD, and sanity_flag.

    Returns:
        3-row DataFrame sorted by Sharpe_rf3 desc, CAGR desc, MaxDD desc.

    Raises:
        RuntimeError: If any of the top-3 rows has sanity_flag != "OK" (D-13).
    """
    # Filter out hard-ERROR rows (failed runs from D-07) before selection
    clean = df[df["sanity_flag"] != "ERROR"].copy()

    # Sort: Sharpe_rf3 desc, CAGR desc, MaxDD desc (D-12)
    # MaxDD is negative; descending puts -0.10 before -0.20 = less severe first = correct
    sorted_df = clean.sort_values(
        by=["Sharpe_rf3", "CAGR", "MaxDD"],
        ascending=[False, False, False],
    )

    top3 = sorted_df.head(3).reset_index(drop=True)

    # D-13 sanity gate: abort if any top-3 row is not "OK"
    flagged = top3[top3["sanity_flag"] != "OK"]
    if not flagged.empty:
        details = flagged[["c_yoy", "a_cagr", "n_proximity", "hard_stop", "slots",
                            "entry_option", "sanity_flag"]].to_dict(orient="records")
        raise RuntimeError(
            f"Top-3 contains sanity-flagged config: {details}. "
            "Manual review required before Phase 33 handoff."
        )

    return top3


# ---------------------------------------------------------------------------
# JSON payload builder
# ---------------------------------------------------------------------------

def to_json_payload(top3: pd.DataFrame) -> dict:
    """Build D-14 schema payload dict from top-3 DataFrame.

    Args:
        top3: 3-row DataFrame from select_top3().

    Returns:
        Dict matching D-14 JSON schema (selected_at, selection_metric, period,
        universe, configs[3]).
    """
    configs = []
    for i, row in enumerate(top3.itertuples()):
        configs.append({
            "rank": i + 1,
            "c_yoy": row.c_yoy,
            "a_cagr": row.a_cagr,
            "n_proximity": row.n_proximity,
            "hard_stop": row.hard_stop,
            "slots": int(row.slots),
            "entry_option": row.entry_option,
            "metrics": {col: getattr(row, col) for col in METRIC_COLS},
        })

    return {
        "selected_at": date.today().isoformat(),
        "selection_metric": SELECTION_METRIC,
        "period": PERIOD,
        "universe": UNIVERSE,
        "configs": configs,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Read sweep CSV, select top-3, write JSON, print summary."""
    df = pd.read_csv(SWEEP_CSV)

    total = len(df)
    ok_count = (df["sanity_flag"] == "OK").sum()
    flagged_count = (df["sanity_flag"] == "CAGR_TOO_HIGH").sum()
    error_count = (df["sanity_flag"] == "ERROR").sum()
    print(f"Sweep summary: total={total} OK={ok_count} CAGR_TOO_HIGH={flagged_count} ERROR={error_count}")

    top3 = select_top3(df)

    payload = to_json_payload(top3)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"Written: {OUTPUT_JSON}")

    print("\nTop-3 configs:")
    display_cols = GRID_COLS + ["CAGR", "Sharpe_rf3", "MaxDD", "num_trades", "sanity_flag"]
    print(top3[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
