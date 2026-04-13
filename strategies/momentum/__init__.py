"""Momentum strategy package (Phase 35-36).
Owning requirements: MOM-01, MOM-02, MOM-03, MSCO-01, MSCO-02, MSCO-03, MSCO-04.
"""
from .scorer import apply_momentum_thresholds
from .scorer_config import MomentumScorerConfig
from .rs import compute_rs_panel, get_rs_rankings
from .config import RSConfig

__all__ = [
    "apply_momentum_thresholds",
    "MomentumScorerConfig",
    "compute_rs_panel",
    "get_rs_rankings",
    "RSConfig",
]
