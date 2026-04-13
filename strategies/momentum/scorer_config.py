"""MomentumScorerConfig — v8.0 momentum scorer thresholds (MSCO-01, MSCO-02).

Replaces CANSLIM C/A rules (EPS YoY, EPS CAGR) with RS momentum + N rule.
Pure price-based computation — no DB connectors required.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MomentumScorerConfig:
    """v8.0 momentum scorer thresholds (MSCO-01, MSCO-02).

    Replaces CANSLIM C/A rules with RS momentum + N rule.
    Pure price-based computation — all computed from OHLC price data.

    Attributes:
        rs_threshold: Minimum RS percentile rank to pass (MSCO-01).
            Default 70.0 = top 30% of VN100 universe.
        n_within_high: Maximum proximity to 52-week high (MSCO-02).
            Expressed as fraction: 0.15 means within 15% of 52w high.
            Passed when (high_52w - close) / high_52w <= n_within_high.
        min_history_days: Minimum trading days of history required to compute
            RS and N rule. Default 252 = 1 trading year.
    """

    rs_threshold: float = 70.0       # MSCO-01: RS percentile >= 70
    n_within_high: float = 0.15      # MSCO-02: within 15% of 52-week high
    min_history_days: int = 252      # Need 252 days for RS + N computation

    def __post_init__(self) -> None:
        if not (0 <= self.rs_threshold <= 100):
            raise ValueError(
                f"rs_threshold must be in [0, 100], got {self.rs_threshold}"
            )
        if not (0 < self.n_within_high <= 1):
            raise ValueError(
                f"n_within_high must be in (0, 1], got {self.n_within_high}"
            )
        if self.min_history_days < 1:
            raise ValueError(
                f"min_history_days must be >= 1, got {self.min_history_days}"
            )
