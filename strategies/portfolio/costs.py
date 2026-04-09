"""Entry/exit cost primitives for Phase 31 portfolio engine.

Per CONTEXT D-22/D-23:
- Entry cost = commission (0.25%) + slippage (0.10%) = 0.35% total debit.
- Exit cost = commission (0.25%) + tax (0.10%) + slippage (0.10%) = 0.45% haircut.
- Cost basis for P&L uses fill_price * (1 + entry_commission + entry_slippage).
"""
from __future__ import annotations

from .config import PortfolioConfig


def apply_entry_cost(notional: float, cfg: PortfolioConfig) -> float:
    """Total cash debit for opening a position = notional * (1 + comm + slip)."""
    return notional * (1.0 + cfg.entry_commission + cfg.entry_slippage)


def apply_exit_cost(gross_proceeds: float, cfg: PortfolioConfig) -> float:
    """Net cash credit from closing a position = gross * (1 - comm - tax - slip)."""
    return gross_proceeds * (
        1.0 - cfg.exit_commission - cfg.exit_tax - cfg.exit_slippage
    )


def entry_cost_basis(fill_price: float, cfg: PortfolioConfig) -> float:
    """Per-share cost basis used for P&L (D-22)."""
    return fill_price * (1.0 + cfg.entry_commission + cfg.entry_slippage)
