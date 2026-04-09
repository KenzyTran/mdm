"""CANSLIM strategy package (Phase 29).

Owning requirements: UNIV-01..UNIV-03, CANS-01..CANS-12.
Wave 0 scaffold — business logic stubbed; filled in by plans 29-02..29-09.
"""
from strategies.canslim.config import CanslimConfig  # noqa: F401
from strategies.canslim.scorer import CanslimScorer  # noqa: F401

__all__ = ["CanslimConfig", "CanslimScorer"]
