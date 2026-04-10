"""RSConfig — parameters for momentum RS computation (Phase 35, MOM-01/MOM-02).

Field defaults mirror the IBD Weighted ROC formula used in CanslimConfig.
__post_init__ validates weight alignment and sum.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class RSConfig:
    """Configuration for Relative Strength computation.

    Defaults follow IBD Weighted ROC: 0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252.
    """

    roc_days: Tuple[int, ...] = (63, 126, 189, 252)
    roc_weights: Tuple[float, ...] = (0.4, 0.2, 0.2, 0.2)
    min_history_days: int = 252

    def __post_init__(self) -> None:
        if len(self.roc_days) != len(self.roc_weights):
            raise ValueError("roc_days and roc_weights must align")
        if abs(sum(self.roc_weights) - 1.0) > 1e-9:
            raise ValueError("roc_weights must sum to 1.0")
        if self.min_history_days < 1:
            raise ValueError("min_history_days must be >= 1")
