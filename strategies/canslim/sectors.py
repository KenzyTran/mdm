"""Sector routing — owning requirement UNIV-03 (route ticker -> is_quarter_*).

Stub: filled in by plan 29-04. Reads stock_list.sector (column name locked
in schema_lock.json by plan 29-01 Task 2).
"""
from __future__ import annotations


def route_ticker_to_sector_table(ticker: str) -> str:
    """Map a ticker to its is_quarter_<sector> table name.

    Args:
        ticker: VN stock symbol.

    Returns:
        str: One of "nonbank", "bank", "insurance", "stock".

    Raises:
        NotImplementedError: Filled in by plan 29-04.
    """
    raise NotImplementedError("Filled in by plan 29-04")
