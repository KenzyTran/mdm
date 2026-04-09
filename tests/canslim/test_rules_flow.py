"""Tests for flow rule (I, S) — CANS-09, CANS-10."""
import pytest

from strategies.canslim.rules import flow  # noqa: F401


def test_flow_module_imports():
    """Smoke."""
    assert hasattr(flow, "check_i_foreign_net_buy")


@pytest.mark.skip(reason="implemented in plan 29-07")
def test_cans09_i_foreign_net_buy():
    """CANS-09."""
    pass


@pytest.mark.skip(reason="implemented in plan 29-07")
def test_cans10_s_volume_surge():
    """CANS-10."""
    pass
