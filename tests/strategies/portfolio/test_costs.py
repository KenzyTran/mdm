"""Tests for strategies.portfolio.costs (D-22, D-23)."""
import pytest

from strategies.portfolio.config import PortfolioConfig
from strategies.portfolio.costs import (
    apply_entry_cost,
    apply_exit_cost,
    entry_cost_basis,
)


def test_entry_cost_default():
    cfg = PortfolioConfig()
    assert apply_entry_cost(100_000_000, cfg) == pytest.approx(100_350_000)


def test_exit_cost_default():
    cfg = PortfolioConfig()
    assert apply_exit_cost(100_000_000, cfg) == pytest.approx(99_550_000)


def test_entry_cost_basis():
    cfg = PortfolioConfig()
    assert entry_cost_basis(25000, cfg) == pytest.approx(25087.5)


def test_cost_override():
    cfg = PortfolioConfig(entry_commission=0.001, entry_slippage=0.001)
    assert apply_entry_cost(100_000_000, cfg) == pytest.approx(100_200_000)
