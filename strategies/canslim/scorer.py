"""CanslimScorer — end-to-end per-(date,ticker) scoring (CANS-11, D-09..D-11).

Wires universe + sectors + all rules into a single
``CanslimScorer.score(as_of_date)`` that returns a tidy DataFrame with one
row per eligible (date, ticker). Composite formula is LOCKED — see
``docs/rules_canslim.md`` §7.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, List

import numpy as np
import pandas as pd

from strategies.canslim.config import CanslimConfig
from strategies.canslim.rules.flow import compute_i
from strategies.canslim.rules.fundamental import compute_fundamentals
from strategies.canslim.rules.liquidity import compute_liq
from strategies.canslim.rules.rs import compute_rs_ratings
from strategies.canslim.rules.technical import compute_n, compute_s
from strategies.canslim.sectors import SectorRouter
from strategies.canslim.universe import UniverseLoader

# Number of boolean CANSLIM rules that feed the composite — c, c+, a, a+,
# n, s, l, i, liq. Locked with the composite formula in docs §7.
NUM_BOOLEAN_RULES = 9

# Composite weights (LOCKED — see docs/rules_canslim.md §7).
BOOL_WEIGHT = 0.70
RS_WEIGHT = 0.30

OUTPUT_COLUMNS = [
    "date",
    "ticker",
    "sector",
    "c_pass",
    "c_plus_pass",
    "a_pass",
    "a_plus_pass",
    "n_pass",
    "s_pass",
    "l_pass",
    "i_pass",
    "liq_pass",
    "rs_rating",
    "score",
]


@dataclass
class CanslimScorer:
    """Orchestrate CANSLIM rules into a single tidy output frame.

    Attributes:
        config: :class:`CanslimConfig` with all thresholds/lookbacks.
        universe_loader: :class:`UniverseLoader` — supplies eligible tickers.
        sector_router: :class:`SectorRouter` — sector buckets + exclusions.
        pg_engine: Postgres engine for TA + flow reads.
        mysql_engine: MySQL engine for fundamentals.
    """

    config: CanslimConfig
    universe_loader: UniverseLoader
    sector_router: SectorRouter
    pg_engine: Any
    mysql_engine: Any

    def score(self, as_of_date: date) -> pd.DataFrame:
        """Return the tidy per-(date,ticker) CANSLIM DataFrame for ``as_of_date``.

        Steps:
            1. Resolve the universe from ``universe_loader``.
            2. Drop tickers whose sector is excluded (D-07: ctck / insurance).
            3. Load the full OHLCV panel once for the remaining tickers.
            4. Compute RS ratings universe-wide (percentile ranked).
            5. For each ticker evaluate the 9 boolean rules + composite score.
        """
        tickers = sorted(self.universe_loader.get(as_of_date))
        tickers = [t for t in tickers if not self.sector_router.is_excluded(t)]
        if not tickers:
            return self._empty_frame()

        panel = self._load_panel(tickers, as_of_date)
        rs_series = compute_rs_ratings(panel, as_of_date, tickers, self.config)

        rows = []
        for ticker in tickers:
            ohlcv = (
                panel[panel["stockcode"].str.upper() == ticker]
                .sort_values("tradingdate")
                .reset_index(drop=True)
            )
            c, cp, a, ap = compute_fundamentals(
                ticker,
                as_of_date,
                self.config,
                self.sector_router,
                self.mysql_engine,
            )
            n = compute_n(ohlcv, as_of_date, self.config)
            s = compute_s(ohlcv, as_of_date, self.config)
            i_flag = compute_i(ticker, as_of_date, self.config, self.pg_engine)
            liq = compute_liq(ohlcv, as_of_date, self.config)

            rs_val = float(rs_series.get(ticker, np.nan))
            l_flag = (not np.isnan(rs_val)) and (rs_val >= self.config.l_rs_threshold)

            passes: List[bool] = [c, cp, a, ap, n, s, l_flag, i_flag, liq]
            composite = self._composite(passes, rs_val)

            rows.append(
                {
                    "date": as_of_date,
                    "ticker": ticker,
                    "sector": self.sector_router.route(ticker),
                    "c_pass": bool(c),
                    "c_plus_pass": bool(cp),
                    "a_pass": bool(a),
                    "a_plus_pass": bool(ap),
                    "n_pass": bool(n),
                    "s_pass": bool(s),
                    "l_pass": bool(l_flag),
                    "i_pass": bool(i_flag),
                    "liq_pass": bool(liq),
                    "rs_rating": rs_val,
                    "score": composite,
                }
            )

        df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
        # Enforce bool dtypes on the *_pass columns; floats on rs/score.
        for col in (
            "c_pass",
            "c_plus_pass",
            "a_pass",
            "a_plus_pass",
            "n_pass",
            "s_pass",
            "l_pass",
            "i_pass",
            "liq_pass",
        ):
            df[col] = df[col].astype(bool)
        df["rs_rating"] = df["rs_rating"].astype(float)
        df["score"] = df["score"].astype(float)
        return df

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _composite(passes: List[bool], rs_val: float) -> float:
        """LOCKED composite: 0.70 * boolean_component + 0.30 * rs_component.

        See ``docs/rules_canslim.md`` §7. Boolean component is the pass ratio
        scaled to 0..100. RS component is ``rs_rating`` directly (already
        0..100); NaN RS is treated as 0 so the booleans still contribute.
        """
        bool_component = 100.0 * sum(1 for p in passes if p) / NUM_BOOLEAN_RULES
        rs_component = 0.0 if np.isnan(rs_val) else rs_val
        return BOOL_WEIGHT * bool_component + RS_WEIGHT * rs_component

    def _load_panel(self, tickers: List[str], as_of_date: date) -> pd.DataFrame:
        """Load the OHLCV panel (close/high/volume) for ``tickers`` up to ``as_of_date``."""
        sql = """
            SELECT stockcode, tradingdate,
                   closeprice AS closeindex,
                   highestprice AS highestindex,
                   totalvol
            FROM stock_eod
            WHERE stockcode = ANY(%(t)s) AND tradingdate <= %(d)s
            ORDER BY stockcode, tradingdate
        """
        return pd.read_sql(
            sql,
            self.pg_engine,
            params={"t": tickers, "d": as_of_date},
        )

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        """Return an empty DataFrame with the locked output schema."""
        return pd.DataFrame({c: pd.Series(dtype="object") for c in OUTPUT_COLUMNS})
