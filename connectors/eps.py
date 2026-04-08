"""EPS publish-date resolution.

Per phase 28 D-08/D-09/D-10. Pure function — no DB access.
"""
from __future__ import annotations

import pandas as pd

_QUARTER_END_MONTH_DAY = {
    3:  (3, 31),
    6:  (6, 30),
    9:  (9, 30),
    12: (12, 31),
}

_REAL_COL_PRIORITY = ("publish_date", "announce_date", "updated_at")


def _period_end(year: int, length) -> pd.Timestamp:
    L = 12 if (length is None or pd.isna(length)) else int(length)
    if L not in _QUARTER_END_MONTH_DAY:
        L = 12
    m, d = _QUARTER_END_MONTH_DAY[L]
    return pd.Timestamp(year=int(year), month=m, day=d)


def _impute_one(year: int, length) -> pd.Timestamp:
    pe = _period_end(year, length)
    L = 12 if (length is None or pd.isna(length)) else int(length)
    offset_days = 90 if L == 12 else 45
    return pe + pd.Timedelta(days=offset_days)


def resolve_eps_publish_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add publish_date column per D-08/D-09/D-10.

    Resolution order:
      1. Use existing publish_date / announce_date / updated_at if non-null.
      2. Otherwise impute from (yearreport, lengthreport):
         - lengthreport in {3, 6, 9}   -> period_end + 45 days
         - lengthreport in {12, NaN}   -> period_end + 90 days

    Pure function: no DB / env access.
    """
    out = df.copy()

    if "publish_date" not in out.columns:
        out["publish_date"] = pd.NaT
    out["publish_date"] = pd.to_datetime(out["publish_date"], errors="coerce")

    for col in _REAL_COL_PRIORITY[1:]:  # announce_date, updated_at
        if col in out.columns:
            fallback = pd.to_datetime(out[col], errors="coerce")
            out["publish_date"] = out["publish_date"].fillna(fallback)

    if "yearreport" not in out.columns:
        raise ValueError("missing column 'yearreport' — cannot impute publish_date")

    length_col = (
        out["lengthreport"]
        if "lengthreport" in out.columns
        else pd.Series([None] * len(out), index=out.index)
    )

    mask = out["publish_date"].isna()
    if mask.any():
        imputed = [
            _impute_one(y, L)
            for y, L in zip(out.loc[mask, "yearreport"], length_col[mask])
        ]
        out.loc[mask, "publish_date"] = pd.to_datetime(imputed)

    return out
