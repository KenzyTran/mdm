"""Baseline loader for MySQL ``stocks_backend.canslim`` (CANS-12).

**Context (probed live 2026-04-09):** After plan 29-09 checkpoint 1, we switched
the baseline source from ``rank_top_stocks`` to ``canslim`` because:

* ``canslim`` is the *upstream source of truth* — rows in ``rank_top_stocks``
  are downstream copies (we cross-checked that top rows in Q4 2024 match
  ``rank_top_stocks.diem_canslim`` exactly at L18=98.722787).
* ``canslim`` has far richer coverage: ~35,218 rows across 76 quarters
  (Q4 2005 .. Q4 2025, **including 2025**), ~1,100 tickers per recent quarter.
* ``canslim`` exposes *component* percentile columns so we can do not just a
  top-10 overlap but a per-rule agreement analysis against the baseline:
  - ``sale_quy_gan_nhat`` / ``sale_trailing_12_thang``
  - ``eps_quy_gan_nhat``  / ``eps_trailing_12_thang``
  - ``roe_trailing_12_thang``
  Each accompanied by a ``*_truoc_do`` (prior-period) sibling.
* ``tong_diem`` is the composite 0..100 score (equivalent to
  ``rank_top_stocks.diem_canslim``).

**Semantics:** The baseline is QUARTERLY, keyed by ``thoigian`` (a text column
holding values like ``'Q4 2024'``). Our scorer runs on daily ``as_of_date``, so
comparison code must map a quarter label → the last trading day in that
quarter and then call ``CanslimScorer.score(last_trading_day)``. This is a
documented quarterly-vs-daily semantics caveat — see
``docs/audits/phase29-canslim-validation.md``.
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Any, List, Sequence, Tuple

import pandas as pd

# The component percentile columns on ``canslim``. Each is a 0..100 percentile
# over the broader screening universe (not just VN100). We map our boolean
# CANSLIM rules onto these via a threshold (default 70 — "top 30%").
BASELINE_COMPONENT_COLUMNS: Tuple[str, ...] = (
    "sale_quy_gan_nhat",
    "sale_trailing_12_thang",
    "eps_quy_gan_nhat",
    "eps_trailing_12_thang",
    "roe_trailing_12_thang",
)


def _quarter_sort_key(q: str) -> Tuple[int, int]:
    """Sort key for ``'Q<n> <YYYY>'`` strings → (year, qnum)."""
    parts = q.strip().split()
    qnum = int(parts[0].lstrip("Qq"))
    year = int(parts[1])
    return (year, qnum)


def available_baseline_quarters(mysql_engine: Any) -> List[str]:
    """Return the sorted list of quarters present in ``canslim``.

    Sort order is chronological (year, qnum). Kept as a live query so stale
    constants don't lie if the upstream owner backfills future quarters.
    """
    sql = """
        SELECT DISTINCT thoigian
        FROM canslim
        WHERE tong_diem IS NOT NULL
    """
    df = pd.read_sql(sql, mysql_engine)
    if df.empty:
        return []
    return sorted(df["thoigian"].astype(str).tolist(), key=_quarter_sort_key)


def load_baseline_quarter(
    mysql_engine: Any,
    quarter: str,
    vn100_tickers: Sequence[str],
) -> pd.DataFrame:
    """Return the full baseline frame for ``quarter``, restricted to VN100.

    Columns returned: ``mack`` (upper), ``tong_diem``, and every column in
    :data:`BASELINE_COMPONENT_COLUMNS`. Sorted by ``tong_diem`` descending.
    Empty DataFrame on no match.
    """
    tickers = [t.upper() for t in vn100_tickers]
    if not tickers:
        return pd.DataFrame()
    cols = ", ".join(["mack", "tong_diem", *BASELINE_COMPONENT_COLUMNS])
    sql = f"""
        SELECT {cols}
        FROM canslim
        WHERE thoigian = %(q)s
          AND mack IN %(tickers)s
          AND tong_diem IS NOT NULL
        ORDER BY tong_diem DESC
    """
    df = pd.read_sql(
        sql,
        mysql_engine,
        params={"q": quarter, "tickers": tuple(tickers)},
    )
    if df.empty:
        return df
    df["mack"] = df["mack"].astype(str).str.upper()
    return df.reset_index(drop=True)


def load_baseline_top10(
    mysql_engine: Any,
    quarter: str,
    vn100_tickers: Sequence[str],
    limit: int = 10,
) -> pd.DataFrame:
    """Return top-N VN100 tickers by ``tong_diem`` for ``quarter``."""
    df = load_baseline_quarter(mysql_engine, quarter, vn100_tickers)
    if df.empty:
        return df
    return df.head(limit).reset_index(drop=True)


# ---------------------------------------------------------------- legacy shim
def load_diem_canslim_top10(
    mysql_engine: Any,
    quarter: str,
    vn100_tickers: Sequence[str],
    limit: int = 10,
) -> List[Tuple[str, float]]:
    """Backwards-compatible tuple-list form used by earlier callers.

    Prefer :func:`load_baseline_top10` which returns a full DataFrame with
    component percentiles for richer analysis.
    """
    df = load_baseline_top10(mysql_engine, quarter, vn100_tickers, limit=limit)
    if df.empty:
        return []
    return list(zip(df["mack"].tolist(), df["tong_diem"].astype(float).tolist()))


def quarter_to_last_trading_day(pg_engine: Any, quarter: str) -> date:
    """Map a baseline quarter string to the last trading day in Postgres.

    Uses ``MAX(tradingdate)`` from ``stock_eod`` within the quarter's
    calendar window so we never pick a weekend / VN-holiday.

    Args:
        pg_engine: SQLAlchemy engine-like for Postgres.
        quarter: ``'Q<n> <YYYY>'`` label.

    Returns:
        ``datetime.date`` of the last trading day inside the quarter.
        Raises ``RuntimeError`` if no trading days exist.
    """
    year, qnum = _quarter_sort_key(quarter)
    start_month = 3 * (qnum - 1) + 1
    end_month = start_month + 2
    start = date(year, start_month, 1)
    end_day = calendar.monthrange(year, end_month)[1]
    end = date(year, end_month, end_day)
    sql = """
        SELECT MAX(tradingdate) AS last_td
        FROM stock_eod
        WHERE tradingdate BETWEEN %(s)s AND %(e)s
    """
    df = pd.read_sql(sql, pg_engine, params={"s": start, "e": end})
    if df.empty or pd.isna(df["last_td"].iloc[0]):
        raise RuntimeError(
            f"No trading days found in stock_eod for quarter {quarter!r} "
            f"({start}..{end})."
        )
    raw = df["last_td"].iloc[0]
    if isinstance(raw, pd.Timestamp):
        return raw.date()
    return raw
