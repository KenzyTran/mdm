"""Flow rule: I (Institutional sponsorship) — owning requirements CANS-09, CANS-10.

Stub: filled in by plan 29-07. Reads stock_foreign_eod over i_lookback_days.
"""
from __future__ import annotations


def check_i_foreign_net_buy(ticker: str, as_of_date, config) -> bool:
    """I: Net foreign buying over i_lookback_days (CANS-09)."""
    raise NotImplementedError("Filled in by plan 29-07")


def check_s_volume_surge(ticker: str, as_of_date, config) -> bool:
    """S: Supply/demand — volume surge >= s_vol_mult (CANS-10)."""
    raise NotImplementedError("Filled in by plan 29-07")
