"""Postgres connector for VN market data (TA schema).

Credentials sourced from .env via python-dotenv. Per phase 28 D-01..D-04.
Exposes: get_engine, query, load_stock_eod, load_ratios.
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Mapping, Optional

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

_engine: Optional[Engine] = None


def _build_url() -> str:
    host = os.getenv("POSTGRES_HOST")
    user = os.getenv("POSTGRES_USER")
    pw = os.getenv("POSTGRES_PASSWORD")
    # Accept both POSTGRES_DB (plan spec) and POSTGRES_DATABASE (legacy .env key)
    db = os.getenv("POSTGRES_DB") or os.getenv("POSTGRES_DATABASE")
    port = os.getenv("POSTGRES_PORT", "5432")
    missing = [
        k for k, v in {
            "POSTGRES_HOST": host,
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": pw,
            "POSTGRES_DB": db,
        }.items() if not v
    ]
    if missing:
        raise RuntimeError(f"Missing Postgres env vars: {missing}")
    return f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"


def get_engine() -> Engine:
    """Return cached SQLAlchemy engine for Postgres."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            _build_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            future=True,
        )
    return _engine


def query(sql: str, params: Optional[Mapping[str, Any]] = None) -> pd.DataFrame:
    """Execute parameterized SQL and return a pandas DataFrame."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def load_stock_eod(
    tickers: Iterable[str],
    start: str,
    end: str,
) -> pd.DataFrame:
    """Load OHLCV+adjustrate from stock_eod for given tickers/date range.

    Returns columns: stockcode, tradingdate (datetime64), openprice,
    highestprice, lowestprice, closeprice, totalvol, totaladjustrate.
    """
    tickers = list(tickers)
    sql = """
        SELECT stockcode, tradingdate,
               openprice, highestprice, lowestprice, closeprice,
               totalvol, totaladjustrate
        FROM stock_eod
        WHERE stockcode = ANY(:tickers)
          AND tradingdate BETWEEN :start AND :end
        ORDER BY stockcode, tradingdate
    """
    df = query(sql, {"tickers": tickers, "start": start, "end": end})
    if not df.empty:
        df["tradingdate"] = pd.to_datetime(df["tradingdate"])
    return df


def load_ratios(tickers: Iterable[str]) -> pd.DataFrame:
    """Load all rows from ratios_stock for the given tickers."""
    tickers = list(tickers)
    sql = "SELECT * FROM ratios_stock WHERE stockcode = ANY(:tickers)"
    return query(sql, {"tickers": tickers})
