"""Universe loader (UNIV-01..03). Reads stock_list + stock_eod from Postgres.

Three modes:
- current-vn100: stock_list.nhomtop IN ('VN30','VN100') — survivorship-biased but simple.
- liquidity-reconstructed: top-100 by 60d ADV at Jan 1 / Jul 1 rebalance dates
  (no intra-period churn between rebalances).
- vn30-only: stock_list.nhomtop = 'VN30'.

All modes apply D-05 history-length filter: tickers with fewer than
`min_history_days` rows in stock_eod at/before `as_of_date` are dropped.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Set

import pandas as pd

VALID_MODES = ("current-vn100", "liquidity-reconstructed", "vn30-only")


@dataclass
class UniverseLoader:
    mode: str
    pg_engine: object
    min_history_days: int = 252
    adv_window_days: int = 60

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"mode must be one of {VALID_MODES}, got {self.mode!r}"
            )

    def get(self, as_of_date: date) -> Set[str]:
        """Return the eligible ticker set for `as_of_date`."""
        if self.mode == "current-vn100":
            tickers = self._current_vn100()
        elif self.mode == "vn30-only":
            tickers = self._vn30_only()
        else:
            tickers = self._liquidity_reconstructed(as_of_date)
        return self._filter_by_history(tickers, as_of_date)

    # ------------------------------------------------------------------ modes

    def _current_vn100(self) -> Set[str]:
        sql = (
            "SELECT stockcode FROM stock_list "
            "WHERE nhomtop IN ('VN30','VN100')"
        )
        df = pd.read_sql(sql, self.pg_engine)
        if df.empty:
            return set()
        return set(df["stockcode"].str.upper())

    def _vn30_only(self) -> Set[str]:
        sql = "SELECT stockcode FROM stock_list WHERE nhomtop = 'VN30'"
        df = pd.read_sql(sql, self.pg_engine)
        if df.empty:
            return set()
        return set(df["stockcode"].str.upper())

    def _last_rebalance_date(self, as_of_date: date) -> date:
        """Return the most recent Jan 1 or Jul 1 <= as_of_date."""
        year = as_of_date.year
        if as_of_date >= date(year, 7, 1):
            return date(year, 7, 1)
        if as_of_date >= date(year, 1, 1):
            return date(year, 1, 1)
        return date(year - 1, 7, 1)

    def _liquidity_reconstructed(self, as_of_date: date) -> Set[str]:
        rebalance = self._last_rebalance_date(as_of_date)
        sql = """
            SELECT stockcode,
                   AVG(closeprice * totalvol) AS adv
            FROM stock_eod
            WHERE tradingdate BETWEEN %(start)s AND %(end)s
            GROUP BY stockcode
            ORDER BY adv DESC
            LIMIT 100
        """
        params = {
            "start": rebalance - pd.Timedelta(days=self.adv_window_days * 2),
            "end": rebalance,
        }
        df = pd.read_sql(sql, self.pg_engine, params=params)
        if df.empty:
            return set()
        return set(df["stockcode"].str.upper())

    # ----------------------------------------------------------------- filter

    def _filter_by_history(
        self, tickers: Set[str], as_of_date: date
    ) -> Set[str]:
        if not tickers:
            return set()
        sql = """
            SELECT stockcode, COUNT(*) AS n
            FROM stock_eod
            WHERE stockcode = ANY(%(tickers)s)
              AND tradingdate <= %(d)s
            GROUP BY stockcode
        """
        df = pd.read_sql(
            sql,
            self.pg_engine,
            params={"tickers": list(tickers), "d": as_of_date},
        )
        if df.empty:
            return set()
        eligible = df.loc[df["n"] >= self.min_history_days, "stockcode"]
        return set(eligible.str.upper())


# Back-compat shim for plan 29-01 stub callers.
def load_vn100_universe(as_of_date=None):  # pragma: no cover - legacy
    """Deprecated: use UniverseLoader(mode='current-vn100').get(as_of_date)."""
    raise NotImplementedError(
        "Use UniverseLoader(mode='current-vn100', pg_engine=...).get(as_of_date)"
    )
