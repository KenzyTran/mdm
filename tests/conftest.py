"""
Shared test configuration and fixtures for MDM project tests.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

# Ensure project root is on sys.path so imports work from tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Path to test fixture files
FIXTURES = Path(__file__).parent / 'fixtures'

# Load .env for DB credential fixtures (phase 28 connectors)
load_dotenv()


@pytest.fixture
def fake_ohlc_df():
    """Synthetic stock_eod-shaped DataFrame for unit tests."""
    return pd.DataFrame({
        "stockcode": ["AAA"] * 5,
        "tradingdate": pd.date_range("2024-01-02", periods=5, freq="B"),
        "openprice":   [10.0, 11.0, 12.0, 13.0, 14.0],
        "highestprice": [10.5, 11.5, 12.5, 13.5, 14.5],
        "lowestprice": [9.5, 10.5, 11.5, 12.5, 13.5],
        "closeprice":  [10.2, 11.2, 12.2, 13.2, 14.2],
        "totalvol":    [1000, 1100, 1200, 1300, 1400],
        "totaladjustrate": [2.0, 2.0, 2.0, 1.0, 1.0],  # split on row 4
    })


def _has_pg_creds() -> bool:
    base = all(os.getenv(k) for k in ("POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD"))
    db = os.getenv("POSTGRES_DB") or os.getenv("POSTGRES_DATABASE")
    return bool(base and db)


def _has_mysql_creds() -> bool:
    base = all(os.getenv(k) for k in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD"))
    db = os.getenv("MYSQL_DB") or os.getenv("MYSQL_DATABASE")
    return bool(base and db)


skip_if_no_pg = pytest.mark.skipif(not _has_pg_creds(), reason="Postgres creds not in .env")
skip_if_no_mysql = pytest.mark.skipif(not _has_mysql_creds(), reason="MySQL creds not in .env")
