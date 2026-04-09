"""Shared pytest fixtures for the Phase 31 portfolio test suite."""
from __future__ import annotations

import pytest

from strategies.portfolio.config import PortfolioConfig
from tests.strategies.portfolio.fixtures.synthetic_panel import make_panel


@pytest.fixture
def synthetic_panel():
    return make_panel()


@pytest.fixture
def config():
    return PortfolioConfig()
