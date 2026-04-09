"""Sector router (CANS-10, D-06..D-08).

Classifies each VN100 ticker into one of four buckets — ``bank``, ``ctck``
(securities firms), ``insurance``, or ``other`` — using the locked
``stock_list.sector`` column recorded in schema_lock.json by plan 29-01.

Design rules:

* D-06: bank tickers route to the PPOP growth branch (``is_quarter_bank``);
  non-bank, non-excluded tickers route to the EPS branch (``is_quarter_nonbank``).
* D-07: ``ctck`` and ``insurance`` tickers are EXCLUDED from scoring — their
  income statements use bespoke schemas (``is_quarter_stock`` /
  ``is_quarter_insurance``) that CANSLIM fundamental rules don't support.
* D-08: missing / unknown sector column must fail LOUD — silent fallback to
  "other" across the whole universe would corrupt the scorer.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, Literal

import pandas as pd

SectorBucket = Literal["bank", "ctck", "insurance", "other"]

# Substring rules over Vietnamese labels. Case-insensitive contains.
BANK_TOKENS = ("ngân hàng", "ngan hang", "bank")
CTCK_TOKENS = ("chứng khoán", "chung khoan", "securities")
INSURANCE_TOKENS = ("bảo hiểm", "bao hiem", "insurance")

SECTOR_BANK: SectorBucket = "bank"
SECTOR_EXCLUDED = ("ctck", "insurance")


@dataclass
class SectorRouter:
    """Route VN100 tickers into CANSLIM sector buckets.

    Attributes:
        ticker_to_sector: Mapping from UPPER-case ticker to raw sector label
            as loaded from stock_list (Vietnamese).
    """

    ticker_to_sector: Dict[str, str]

    def route(self, ticker: str) -> SectorBucket:
        """Return the sector bucket for ``ticker``.

        Unknown tickers emit a warning and default to ``'other'`` — the
        fail-loud check lives in :meth:`from_postgres` where we can reason
        over the whole universe at once.
        """
        raw = (self.ticker_to_sector.get(ticker.upper()) or "").strip().lower()
        if not raw:
            warnings.warn(
                f"Ticker {ticker} has no sector label; defaulting to 'other'"
            )
            return "other"
        if any(tok in raw for tok in BANK_TOKENS):
            return "bank"
        if any(tok in raw for tok in CTCK_TOKENS):
            return "ctck"
        if any(tok in raw for tok in INSURANCE_TOKENS):
            return "insurance"
        return "other"

    def is_excluded(self, ticker: str) -> bool:
        """True if ticker is in a CANSLIM-excluded bucket (ctck / insurance)."""
        return self.route(ticker) in SECTOR_EXCLUDED

    @classmethod
    def from_postgres(cls, pg_engine, sector_column: str) -> "SectorRouter":
        """Build a router from Postgres ``stock_list``.

        Args:
            pg_engine: SQLAlchemy engine-like object accepted by ``pd.read_sql``.
            sector_column: Column name locked in schema_lock.json
                (``locked.stock_list_sector_column``).

        Raises:
            RuntimeError: If ``stock_list`` is empty, or if the sector column
                is NULL for more than 50% of tickers (D-08 fail-loud).
        """
        sql = f"SELECT stockcode, {sector_column} AS sector FROM stock_list"
        df = pd.read_sql(sql, pg_engine)
        if df.empty:
            raise RuntimeError("stock_list is empty")
        missing = df["sector"].isna().mean()
        if missing > 0.5:
            raise RuntimeError(
                f"Sector column {sector_column!r} missing for {missing:.0%} of "
                "tickers — schema_lock.json is stale. Re-run "
                "scripts/introspect_canslim_schema.py."
            )
        mapping = dict(zip(df["stockcode"].str.upper(), df["sector"].fillna("")))
        return cls(ticker_to_sector=mapping)
