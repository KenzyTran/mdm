"""Tests for VN100 universe loader — UNIV-01, UNIV-02."""
import pytest

from strategies.canslim import universe  # noqa: F401


def test_universe_module_imports():
    """Smoke: universe module is importable."""
    assert hasattr(universe, "load_vn100_universe")


@pytest.mark.skip(reason="implemented in plan 29-03")
def test_univ01_load_vn100_returns_100_tickers():
    """UNIV-01: VN100 list contains 100 tickers."""
    pass


@pytest.mark.skip(reason="implemented in plan 29-03")
def test_univ02_universe_is_static():
    """UNIV-02: universe does not vary by as_of_date."""
    pass
