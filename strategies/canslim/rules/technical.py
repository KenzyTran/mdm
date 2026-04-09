"""Technical rule: N (New high / pivot) — owning requirements CANS-05, CANS-06.

Stub: filled in by plan 29-06.
"""
from __future__ import annotations


def check_n_new_high(ticker: str, as_of_date, config) -> bool:
    """N: Price within n_within_high of 52-week high (CANS-05)."""
    raise NotImplementedError("Filled in by plan 29-06")


def check_n_pivot_breakout(ticker: str, as_of_date, config) -> bool:
    """N: Pivot/base breakout confirmation (CANS-06)."""
    raise NotImplementedError("Filled in by plan 29-06")
