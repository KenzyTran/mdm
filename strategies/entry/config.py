"""EntryConfig — thresholds for the Phase 30 stock-level entry detectors.

Field defaults and validation rules follow
``.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md`` decisions
D-03..D-06 (Option A and Option C detector semantics) and D-20 (dataclass
location + overridable kwargs). All validation is fail-loud per
``__post_init__`` — matches the Phase 29 ``CanslimConfig`` pattern.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EntryConfig:
    """Strategy parameters for the Phase 30 entry detectors.

    Defaults are the locked values from Phase 30 CONTEXT.md (D-03..D-06,
    D-20). All thresholds are kwargs-overridable so that the Phase 32
    in-sample sweep can perturb them without code changes.

    Attributes:
        high_lookback: Trailing trading-day window for the Option A 52-week
            high check (D-03/D-04). Default 252.
        vol_lookback: Trailing window for the Option A volume-surge average
            (D-03/D-04). Default 50.
        vol_mult: Option A volume-surge multiplier — signal requires
            ``vol[t] >= vol_mult * mean(vol[t - vol_lookback .. t - 1])``
            (D-03/D-04). Default 1.5.
        ma_length: Option C moving-average length on adjusted close; also
            the lookback for the "near-base" 50-day high check (D-05/D-06).
            Default 50.
        pocket_lookback: Option C down-day-volume lookback (D-05/D-06).
            Default 10. Fail-closed when there are zero down days in this
            window — see 30-RESEARCH.md Pitfall #2.
        base_tolerance: Option C "within X% of 50-day high" tolerance as a
            fraction (D-05/D-06). Default 0.15 (== 15%).
        window_days: MDM BUY window length in trading days from the most
            recent CASH/SELL -> BUY transition (D-07, D-20). Default 20.
            The signal bar itself counts as day 1.
    """

    # Option A (D-03/D-04)
    high_lookback: int = 252
    vol_lookback: int = 50
    vol_mult: float = 1.5
    # Option C (D-05/D-06)
    ma_length: int = 50
    pocket_lookback: int = 10
    base_tolerance: float = 0.15
    # Window (D-07..D-09, D-20)
    window_days: int = 20

    def __post_init__(self) -> None:
        """Fail-loud validation of all threshold fields.

        Raises:
            ValueError: If any field is outside its documented valid range.
        """
        if self.high_lookback < 2:
            raise ValueError("high_lookback must be >= 2")
        if self.vol_lookback < 1:
            raise ValueError("vol_lookback must be >= 1")
        if self.vol_mult < 1.0:
            raise ValueError("vol_mult must be >= 1.0")
        if self.ma_length < 2:
            raise ValueError("ma_length must be >= 2")
        if self.pocket_lookback < 1:
            raise ValueError("pocket_lookback must be >= 1")
        if not (0 < self.base_tolerance < 1):
            raise ValueError("base_tolerance must be in (0, 1)")
        if self.window_days < 1:
            raise ValueError("window_days must be >= 1")
