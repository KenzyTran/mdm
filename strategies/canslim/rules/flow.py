"""I rule — foreign net-buy flow (CANS-08) + S wrapper (CANS-06).

Pre-2022 fallback: `stock_foreign_eod` coverage starts 2022-04-07 per
29-RESEARCH.md. Any `as_of_date` strictly earlier than that returns
`i_pass=True` by default so historical backtests are not starved of signal.

S rule delegates to `technical.compute_s` (CANS-06) for consistency.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from strategies.canslim.config import CanslimConfig
from strategies.canslim.rules import technical

# stock_foreign_eod has no rows before this date (locked by plan 29-01 research).
FOREIGN_DATA_START = date(2022, 4, 7)


def compute_i(
    ticker: str,
    as_of_date: date,
    config: CanslimConfig,
    pg_engine: Any,
) -> bool:
    """I rule: foreign net-buy flow over ``config.i_lookback_days`` trading days.

    Strict ``> 0`` check. Returns ``True`` automatically for ``as_of_date`` before
    2022-04-07 (`FOREIGN_DATA_START`) because the upstream table has no coverage
    in that range — documented fallback rather than a NaN crash.

    Args:
        ticker: Stock code (upper-cased before query).
        as_of_date: Signal date — only rows strictly before this date are summed.
        config: CanslimConfig; ``i_lookback_days`` controls window.
        pg_engine: SQLAlchemy engine / DBAPI connection accepted by pandas.read_sql.

    Returns:
        True iff net foreign buy value (fbvalue - fsvalue) summed over the last
        ``config.i_lookback_days`` trading rows is strictly greater than zero.
    """
    if as_of_date < FOREIGN_DATA_START:
        # Pre-2022-04-07 fallback — documented in 29-RESEARCH.md + docs/rules_canslim.md §6.
        return True

    sql = """
        SELECT net_buy FROM (
            SELECT (fbvalue - fsvalue) AS net_buy
            FROM stock_foreign_eod
            WHERE stockcode = %(t)s AND tradingdate < %(d)s
            ORDER BY tradingdate DESC
            LIMIT %(n)s
        ) q
    """
    df = pd.read_sql(
        sql,
        pg_engine,
        params={
            "t": ticker.upper(),
            "d": as_of_date,
            "n": config.i_lookback_days,
        },
    )
    if df.empty:
        return False
    return float(df["net_buy"].sum()) > 0


def compute_s(ohlcv: pd.DataFrame, as_of_date, config: CanslimConfig) -> bool:
    """S rule wrapper (CANS-06).

    Delegates to :func:`strategies.canslim.rules.technical.compute_s` so the
    scorer has a single import surface (``from .rules import flow``) without
    duplicating the volume-surge logic.
    """
    return technical.compute_s(ohlcv, as_of_date, config)


# Legacy stubs kept for backwards compatibility with earlier scaffold callers.
def check_i_foreign_net_buy(ticker: str, as_of_date, config) -> bool:
    """Deprecated: use :func:`compute_i`."""
    raise NotImplementedError("Use compute_i(ticker, as_of_date, config, pg_engine)")


def check_s_volume_surge(ticker: str, as_of_date, config) -> bool:
    """Deprecated: use :func:`compute_s`."""
    raise NotImplementedError("Use compute_s(ohlcv, as_of_date, config)")
