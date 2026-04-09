"""Fundamental rules: C, C+, A, A+ — owning requirements CANS-01..CANS-04.

Stub: filled in by plan 29-05. Reads is_quarter_<sector> columns locked in
schema_lock.json (plan 29-01 Task 2).
"""
from __future__ import annotations


def check_c_quarterly_eps_yoy(ticker: str, as_of_date, config) -> bool:
    """C: Quarterly EPS YoY growth >= c_threshold (CANS-01)."""
    raise NotImplementedError("Filled in by plan 29-05")


def check_c_plus_eps_acceleration(ticker: str, as_of_date, config) -> bool:
    """C+: EPS growth acceleration vs prior quarter (CANS-02)."""
    raise NotImplementedError("Filled in by plan 29-05")


def check_a_annual_eps_growth(ticker: str, as_of_date, config) -> bool:
    """A: Annual EPS growth >= a_threshold (CANS-03)."""
    raise NotImplementedError("Filled in by plan 29-05")


def check_a_plus_roe(ticker: str, as_of_date, config) -> bool:
    """A+: ROE quality screen (CANS-04)."""
    raise NotImplementedError("Filled in by plan 29-05")
