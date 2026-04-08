"""MySQL connector for VN fundamentals (stocks_backend schema).

Credentials sourced from .env via python-dotenv. Per phase 28 D-01..D-04.
Exposes: get_engine, query, load_ratios_stock, load_is_quarter.
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Literal, Mapping, Optional
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

_engine: Optional[Engine] = None

_ALLOWED_SECTORS = {"nonbank", "bank", "insurance", "stock"}


def _build_url() -> str:
    host = os.getenv("MYSQL_HOST")
    user = os.getenv("MYSQL_USER")
    pw = os.getenv("MYSQL_PASSWORD")
    # Accept either MYSQL_DB or MYSQL_DATABASE (project .env uses the latter).
    db = os.getenv("MYSQL_DB") or os.getenv("MYSQL_DATABASE")
    port = os.getenv("MYSQL_PORT", "3306")
    missing = [
        k for k, v in {
            "MYSQL_HOST": host,
            "MYSQL_USER": user,
            "MYSQL_PASSWORD": pw,
            "MYSQL_DB": db,
        }.items() if not v
    ]
    if missing:
        raise RuntimeError(f"Missing MySQL env vars: {missing}")
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(pw)}"
        f"@{host}:{port}/{db}?charset=utf8mb4"
    )


def get_engine() -> Engine:
    """Return cached SQLAlchemy engine for MySQL."""
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


def load_ratios_stock(tickers: Iterable[str]) -> pd.DataFrame:
    """Load all rows from ratios_stock for the given tickers."""
    tickers = list(tickers)
    sql = text(
        "SELECT * FROM ratios_stock WHERE stockcode IN :tickers"
    ).bindparams(bindparam("tickers", expanding=True))
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn, params={"tickers": tickers})


def load_is_quarter(
    tickers: Iterable[str],
    sector: Literal["nonbank", "bank", "insurance", "stock"] = "nonbank",
) -> pd.DataFrame:
    """Load quarterly income-statement rows from is_quarter_<sector>."""
    if sector not in _ALLOWED_SECTORS:
        raise ValueError(
            f"sector must be one of {_ALLOWED_SECTORS}, got {sector!r}"
        )
    tickers = list(tickers)
    sql = text(
        f"SELECT * FROM is_quarter_{sector} WHERE stockcode IN :tickers"
    ).bindparams(bindparam("tickers", expanding=True))
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn, params={"tickers": tickers})
