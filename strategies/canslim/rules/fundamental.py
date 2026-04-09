"""Fundamental rules C, C+, A, A+ (CANS-01..04, D-07, D-11).

Implements per plan 29-05:

* **C**  — current-quarter value YoY vs 4 quarters ago >= ``config.c_threshold``.
* **C+** — current-quarter YoY growth exceeds mean of the prior two quarters'
  YoY growths (acceleration).
* **A**  — 3-year TTM-sum CAGR of the value column >= ``config.a_threshold``.
* **A+** — last 3 rolling-TTM annual values all strictly positive.

**Sector branching (D-06):**

* ``bank``   → ``is_quarter_bank`` table, PPOP column
* ``other``  → ``is_quarter_nonbank`` table, EPS (net-profit proxy) column
* ``ctck`` / ``insurance`` → EXCLUDED, returns ``(False, False, False, False)``

**Look-ahead guard (D-11):** every row loaded from MySQL is run through
``connectors.eps.resolve_eps_publish_date`` which either uses an existing
publish/announce date column or imputes one from ``yearreport`` +
``lengthreport`` (period_end + 45d for quarters, +90d for annuals). Rows with
``publish_date > as_of_date`` are filtered BEFORE any rule is evaluated.

**Schema lock fallback:** ``schema_lock.json`` may legitimately have
``is_quarter_bank_ppop_column`` or ``publish_date_column`` as ``null`` when
the introspector can't find a clean match. In that case we fall back to the
non-bank EPS column name for the PPOP proxy, and rely entirely on imputation
for the publish date. These fallbacks are documented in
``docs/rules_canslim.md`` §4.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from connectors.eps import resolve_eps_publish_date
from strategies.canslim.config import CanslimConfig
from strategies.canslim.sectors import SectorRouter

_SCHEMA_LOCK: Optional[dict] = None
_SCHEMA_PATH = Path(
    ".planning/phases/29-vn100-universe-canslim-scorer/schema_lock.json"
)


def _schema() -> dict:
    """Return the ``locked`` section of schema_lock.json (cached)."""
    global _SCHEMA_LOCK
    if _SCHEMA_LOCK is None:
        _SCHEMA_LOCK = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _SCHEMA_LOCK["locked"]


def _load_quarters(
    mysql_engine,
    table: str,
    value_col: str,
    ticker: str,
    as_of_date: date,
) -> pd.DataFrame:
    """Load up to 16 most recent published quarterly rows for ``ticker``.

    Always selects ``yearreport`` and ``lengthreport`` so that
    :func:`resolve_eps_publish_date` can impute a ``publish_date`` when the
    source table has no publish/announce column. Rows with
    ``publish_date > as_of_date`` are filtered out (D-11 look-ahead guard).
    """
    sql = f"""
        SELECT stockcode, yearreport, lengthreport, {value_col} AS value
        FROM {table}
        WHERE stockcode = %(t)s
        ORDER BY yearreport DESC, lengthreport DESC
        LIMIT 32
    """
    df = pd.read_sql(sql, mysql_engine, params={"t": ticker})
    if df.empty:
        return df
    df = resolve_eps_publish_date(df)
    cutoff = pd.Timestamp(as_of_date)
    df = df[df["publish_date"] <= cutoff].copy()
    # Sort strictly by publish_date desc so index 0 is the most-recently
    # published row that is still visible at as_of_date.
    df = df.sort_values("publish_date", ascending=False).reset_index(drop=True)
    return df.head(16)


# --------------------------------------------------------------------------- #
# Pure rule helpers (no DB, no schema) — easy to unit-test in isolation.
# --------------------------------------------------------------------------- #


def compute_c(values: List[float], threshold: float) -> bool:
    """C: current quarter YoY vs 4 quarters ago >= ``threshold``.

    ``values`` is ordered newest-first. Returns ``False`` if fewer than 5
    observations are available.
    """
    if len(values) < 5:
        return False
    prior = values[4]
    if prior == 0:
        return False
    yoy = (values[0] - prior) / abs(prior)
    return yoy >= threshold


def compute_c_plus(values: List[float]) -> bool:
    """C+: current YoY growth > mean of prior two quarters' YoY growths.

    Needs at least 7 quarters (current + 2 prior + their respective
    4-quarter-lag rows).
    """
    if len(values) < 7:
        return False

    def yoy(i: int) -> float:
        prior = values[i + 4]
        if prior == 0:
            return 0.0
        return (values[i] - prior) / abs(prior)

    return yoy(0) > (yoy(1) + yoy(2)) / 2.0


def compute_a(values: List[float], threshold: float) -> bool:
    """A: 3-year TTM-sum CAGR >= ``threshold``.

    Uses the sum of the four most-recent quarters (current TTM) and the sum
    of the four quarters ending two years earlier (TTM from 2 years ago), so
    at least 12 quarters of history are required. Returns ``False`` on
    insufficient data or non-positive denominators.
    """
    if len(values) < 12:
        return False
    ttm_now = sum(values[0:4])
    ttm_2y_ago = sum(values[8:12])
    if ttm_2y_ago <= 0 or ttm_now <= 0:
        return False
    cagr = (ttm_now / ttm_2y_ago) ** (1.0 / 2.0) - 1.0
    return cagr >= threshold


def compute_a_plus(annual_values: List[float]) -> bool:
    """A+: last 3 rolling-TTM annual values all strictly positive."""
    if len(annual_values) < 3:
        return False
    return all(v > 0 for v in annual_values[:3])


# --------------------------------------------------------------------------- #
# Orchestrator — the only function the scorer calls.
# --------------------------------------------------------------------------- #


def compute_fundamentals(
    ticker: str,
    as_of_date: date,
    config: CanslimConfig,
    sector_router: SectorRouter,
    mysql_engine,
) -> Tuple[bool, bool, bool, bool]:
    """Evaluate (C, C+, A, A+) for ``ticker`` at ``as_of_date``.

    Args:
        ticker: Upper-case ticker symbol.
        as_of_date: Evaluation date — any row with ``publish_date`` strictly
            after this is invisible (D-11 look-ahead guard).
        config: :class:`CanslimConfig` providing ``c_threshold`` / ``a_threshold``.
        sector_router: Router built from ``stock_list`` (plan 29-04).
        mysql_engine: SQLAlchemy-like engine accepted by ``pd.read_sql``.

    Returns:
        Tuple of four booleans ``(c_pass, c_plus_pass, a_pass, a_plus_pass)``.
        Excluded sectors (ctck / insurance) and tickers with no published
        history return ``(False, False, False, False)``.
    """
    sector = sector_router.route(ticker)
    if sector in ("ctck", "insurance"):
        return (False, False, False, False)

    locked = _schema()
    if sector == "bank":
        table = "is_quarter_bank"
        # Fallback: schema_lock bank PPOP column may legitimately be null.
        value_col = (
            locked.get("is_quarter_bank_ppop_column")
            or locked["is_quarter_nonbank_eps_column"]
        )
    else:
        table = "is_quarter_nonbank"
        value_col = locked["is_quarter_nonbank_eps_column"]

    df = _load_quarters(mysql_engine, table, value_col, ticker, as_of_date)
    if df.empty:
        return (False, False, False, False)

    values: List[float] = df["value"].astype(float).tolist()

    # Rolling-TTM "annual" values for A+: sum of 4q at offsets 0, 4, 8.
    annuals: List[float] = []
    for offset in (0, 4, 8):
        if len(values) >= offset + 4:
            annuals.append(sum(values[offset : offset + 4]))

    return (
        compute_c(values, config.c_threshold),
        compute_c_plus(values),
        compute_a(values, config.a_threshold),
        compute_a_plus(annuals),
    )


# --------------------------------------------------------------------------- #
# Legacy stub shims — kept so plan 29-05 doesn't break imports from the
# scaffold created in plan 29-02. Scorer code should call
# :func:`compute_fundamentals` directly.
# --------------------------------------------------------------------------- #


def check_c_quarterly_eps_yoy(ticker, as_of_date, config, sector_router, mysql_engine):
    """Thin shim returning only the C component (CANS-01)."""
    return compute_fundamentals(ticker, as_of_date, config, sector_router, mysql_engine)[0]


def check_c_plus_eps_acceleration(ticker, as_of_date, config, sector_router, mysql_engine):
    """Thin shim returning only the C+ component (CANS-02)."""
    return compute_fundamentals(ticker, as_of_date, config, sector_router, mysql_engine)[1]


def check_a_annual_eps_growth(ticker, as_of_date, config, sector_router, mysql_engine):
    """Thin shim returning only the A component (CANS-03)."""
    return compute_fundamentals(ticker, as_of_date, config, sector_router, mysql_engine)[2]


def check_a_plus_roe(ticker, as_of_date, config, sector_router, mysql_engine):
    """Thin shim returning only the A+ component (CANS-04).

    Name kept for backward compat with the plan-29-02 stub even though the
    final rule is "positive annual EPS 3 years" rather than an ROE screen
    (see 29-CONTEXT.md D-12).
    """
    return compute_fundamentals(ticker, as_of_date, config, sector_router, mysql_engine)[3]
