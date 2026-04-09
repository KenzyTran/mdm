"""PortfolioConfig — Phase 31 multi-stock portfolio engine parameters.

Fail-loud validation per Phase 31 CONTEXT D-03/D-05/D-08/D-09/D-17..D-24.
No YAML, no silent fallback — mirrors Phase 30 EntryConfig pattern.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortfolioConfig:
    """Strategy parameters for the Phase 31 portfolio engine.

    Fields and defaults are locked by Phase 31 CONTEXT.md decisions
    D-03 (fail-loud), D-05 (no YAML), D-08 (max 8 slots equal-weight),
    D-09 (lot size), D-17 (T+2.5 earliest-sell = buy_bar+3),
    D-18..D-20 (cost model), D-21 (cooldown math), D-22..D-24
    (RS threshold / ceiling-floor limits / ADV liquidity guard).
    """

    # Slot / sizing
    max_slots: int = 8
    slot_weight: float = 0.125
    lot_size: int = 100

    # Entry
    entry_mode: str = "union"  # "A" | "C" | "union"
    rs_threshold: float = 70.0
    rs_streak_days: int = 5
    ma50_vol_mult: float = 1.25

    # Exit / risk
    hard_stop_pct: float = 0.08
    cooldown_days: int = 5
    t_plus: int = 2  # settlement offset; earliest_sell_bar = buy_bar + 3

    # Cost model
    entry_commission: float = 0.0025
    entry_slippage: float = 0.0010
    exit_commission: float = 0.0025
    exit_tax: float = 0.0010
    exit_slippage: float = 0.0010

    # Liquidity / VN microstructure
    adv_mult: float = 10.0
    ceiling_pct: float = 0.07
    floor_pct: float = 0.07

    def __post_init__(self) -> None:
        if self.max_slots < 1 or self.max_slots > 20:
            raise ValueError(f"max_slots must be in [1,20], got {self.max_slots}")
        if not (0 < self.slot_weight <= 1):
            raise ValueError(f"slot_weight must be in (0,1], got {self.slot_weight}")
        if self.lot_size < 1:
            raise ValueError(f"lot_size must be >= 1, got {self.lot_size}")
        if self.entry_mode not in {"A", "C", "union"}:
            raise ValueError(
                f"entry_mode must be one of {{'A','C','union'}}, got {self.entry_mode!r}"
            )
        if not (0 < self.hard_stop_pct < 1):
            raise ValueError(
                f"hard_stop_pct must be in (0,1), got {self.hard_stop_pct}"
            )
        if self.rs_threshold < 0 or self.rs_threshold > 100:
            raise ValueError(
                f"rs_threshold must be in [0,100], got {self.rs_threshold}"
            )
        for name, val in (
            ("entry_commission", self.entry_commission),
            ("entry_slippage", self.entry_slippage),
            ("exit_commission", self.exit_commission),
            ("exit_tax", self.exit_tax),
            ("exit_slippage", self.exit_slippage),
        ):
            if val < 0 or val > 0.05:
                raise ValueError(f"{name} must be in [0, 0.05], got {val}")
        if self.adv_mult < 1:
            raise ValueError(f"adv_mult must be >= 1, got {self.adv_mult}")
        if self.rs_streak_days < 1:
            raise ValueError(f"rs_streak_days must be >= 1, got {self.rs_streak_days}")
        if self.cooldown_days < 0:
            raise ValueError(f"cooldown_days must be >= 0, got {self.cooldown_days}")
        if not (0 < self.ceiling_pct < 1):
            raise ValueError(f"ceiling_pct must be in (0,1), got {self.ceiling_pct}")
        if not (0 < self.floor_pct < 1):
            raise ValueError(f"floor_pct must be in (0,1), got {self.floor_pct}")
        if self.ma50_vol_mult < 0:
            raise ValueError(f"ma50_vol_mult must be >= 0, got {self.ma50_vol_mult}")
        if self.t_plus < 0:
            raise ValueError(f"t_plus must be >= 0, got {self.t_plus}")
