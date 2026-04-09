"""State dataclasses for the Phase 31 multi-stock portfolio engine.

Contains Position, Trade, SlotState, CooldownRegistry, PositionBook.
Cooldown math: per Phase 31 CONTEXT D-21, earliest re-entry bar after an
exit = exit_bar + cooldown_days + 1 (D+6 when cooldown_days=5).
Earliest-sell math: per D-17, with t_plus=2 (T+2.5 settlement) a position
opened on buy_bar may first be sold on buy_bar + 3.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class Position:
    ticker: str
    buy_bar: int
    buy_date: pd.Timestamp
    buy_price: float
    shares: int
    cost_basis: float
    earliest_sell_bar: int  # = buy_bar + 3 per D-17


@dataclass
class Trade:
    ticker: str
    buy_date: pd.Timestamp
    buy_price: float
    buy_cost_vnd: float
    sell_date: pd.Timestamp
    sell_price: float
    sell_cost_vnd: float
    pnl_vnd: float
    pnl_pct: float
    exit_reason: str


@dataclass
class SlotState:
    max_slots: int
    open_positions: list = field(default_factory=list)

    def free_slots(self) -> int:
        return self.max_slots - len(self.open_positions)

    def has_open(self, ticker: str) -> bool:
        for p in self.open_positions:
            if p.ticker == ticker:
                return True
        return False


@dataclass
class CooldownRegistry:
    _exit_bars: dict = field(default_factory=dict)

    def register(self, ticker: str, exit_bar_idx: int) -> None:
        self._exit_bars[ticker] = exit_bar_idx

    def is_cooling(self, ticker: str, current_bar_idx: int, cooldown_days: int) -> bool:
        """True if ticker still in cooldown window (D-21).

        Earliest re-entry bar = exit_bar + cooldown_days + 1. So ticker is
        cooling iff current_bar_idx < exit_bar + cooldown_days + 1.
        """
        if ticker not in self._exit_bars:
            return False
        return current_bar_idx < self._exit_bars[ticker] + cooldown_days + 1


@dataclass
class PositionBook:
    """Container holding slots, cooldowns, completed trades, and unfilled log."""

    slots: SlotState
    cooldowns: CooldownRegistry = field(default_factory=CooldownRegistry)
    completed_trades: list = field(default_factory=list)
    unfilled: list = field(default_factory=list)

    def __init__(self, max_slots: int):
        self.slots = SlotState(max_slots=max_slots, open_positions=[])
        self.cooldowns = CooldownRegistry()
        self.completed_trades = []
        self.unfilled = []
