"""Price adjustment helper for stock_eod.

Per phase 28 D-05/D-06: adjusted_price = raw_price * totaladjustrate.
Volume left unadjusted unless audit shows otherwise.
"""
from __future__ import annotations

import pandas as pd

_RAW_TO_ADJ = {
    "openprice":    "adj_open",
    "highestprice": "adj_high",
    "lowestprice":  "adj_low",
    "closeprice":   "adj_close",
}


def adjust_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with adj_open/high/low/close = raw * totaladjustrate.

    Input: DataFrame with columns openprice, highestprice, lowestprice,
    closeprice, totaladjustrate.
    Output: same DataFrame + columns adj_open, adj_high, adj_low, adj_close.
    Volume not adjusted (per D-05).
    Raises ValueError if totaladjustrate (or any raw OHLC) column is missing.
    """
    if "totaladjustrate" not in df.columns:
        raise ValueError("missing column 'totaladjustrate'")
    out = df.copy()
    rate = out["totaladjustrate"].astype(float)
    for raw, adj in _RAW_TO_ADJ.items():
        if raw not in out.columns:
            raise ValueError(f"missing column {raw!r}")
        out[adj] = out[raw].astype(float) * rate
    return out
