"""Liquidity gate — owning requirements CANS-11, CANS-12 (Liq filter D-11).

Stub: filled in by plan 29-07.
"""
from __future__ import annotations


def check_liquidity_turnover(ticker: str, as_of_date, config) -> bool:
    """Liq: Average daily turnover >= liquidity_min_turnover_vnd (CANS-11)."""
    raise NotImplementedError("Filled in by plan 29-07")
