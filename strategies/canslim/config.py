"""CanslimConfig dataclass — owning requirement CANS-12 (parameter defaults).

Field defaults follow 29-CONTEXT.md decision D-12. Validation logic is added
by plan 29-02 (post_init checks).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CanslimConfig:
    """Strategy parameters for the CANSLIM scorer.

    Defaults per 29-CONTEXT.md D-12. All thresholds expressed as fractions
    (e.g. 0.20 == 20%).
    """

    c_threshold: float = 0.20
    a_threshold: float = 0.15
    n_within_high: float = 0.15
    s_vol_mult: float = 1.5
    l_rs_threshold: float = 80.0
    liquidity_min_turnover_vnd: float = 5_000_000_000
    i_lookback_days: int = 20
