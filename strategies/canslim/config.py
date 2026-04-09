"""CanslimConfig — thresholds for the Phase 29 CANSLIM scorer (CANS-11).

Field defaults follow 29-CONTEXT.md decision D-12. __post_init__ validates
threshold ranges. Not frozen — sweep scripts need attribute reassignment.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Tuple


@dataclass
class CanslimConfig:
    """Strategy parameters for the CANSLIM scorer.

    Defaults per 29-CONTEXT.md D-12. All thresholds expressed as fractions
    (e.g. 0.20 == 20%).
    """

    # C: quarterly EPS YoY threshold (D-12)
    c_threshold: float = 0.20
    # A: 3yr EPS CAGR threshold (D-12)
    a_threshold: float = 0.15
    # N: close must be within this fraction of the 252d high (D-12)
    n_within_high: float = 0.15
    # S: breakout volume multiplier over avgvol50 (D-12)
    s_vol_mult: float = 1.5
    # L: minimum RS percentile rank (0-100)
    l_rs_threshold: float = 80.0
    # I: foreign net-buy lookback window in trading days
    i_lookback_days: int = 20
    # Liquidity: minimum 20d median turnover in VND
    liquidity_min_turnover_vnd: float = 5_000_000_000.0
    # L rule ROC lookback days — locked per research formula
    rs_roc_days: Tuple[int, ...] = (63, 126, 189, 252)
    # RS weights aligned with rs_roc_days
    rs_weights: Tuple[float, ...] = (0.4, 0.2, 0.2, 0.2)
    # Minimum history required to score a ticker (matches D-05)
    min_history_days: int = 252

    def __post_init__(self) -> None:
        if self.c_threshold < 0:
            raise ValueError("c_threshold must be >= 0")
        if self.a_threshold < 0:
            raise ValueError("a_threshold must be >= 0")
        if not (0 < self.n_within_high <= 1):
            raise ValueError("n_within_high must be in (0, 1]")
        if self.s_vol_mult < 1:
            raise ValueError("s_vol_mult must be >= 1")
        if not (0 <= self.l_rs_threshold <= 100):
            raise ValueError("l_rs_threshold must be in [0, 100]")
        if self.i_lookback_days < 1:
            raise ValueError("i_lookback_days must be >= 1")
        if self.liquidity_min_turnover_vnd < 0:
            raise ValueError("liquidity_min_turnover_vnd must be >= 0")
        if len(self.rs_roc_days) != len(self.rs_weights):
            raise ValueError("rs_roc_days and rs_weights must align")
        if abs(sum(self.rs_weights) - 1.0) > 1e-9:
            raise ValueError("rs_weights must sum to 1.0")
        if self.min_history_days < 1:
            raise ValueError("min_history_days must be >= 1")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict (round-trips via dataclasses.asdict)."""
        return asdict(self)
