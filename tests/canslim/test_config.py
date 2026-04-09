"""Tests for CanslimConfig — CANS-12."""
import pytest

from strategies.canslim.config import CanslimConfig


def test_canslim_config_imports():
    """Smoke: CanslimConfig is importable and instantiable."""
    cfg = CanslimConfig()
    assert cfg.c_threshold == 0.20
    assert cfg.l_rs_threshold == 80.0


@pytest.mark.skip(reason="implemented in plan 29-02")
def test_cans12_config_validation_rejects_negative_thresholds():
    """CANS-12: post_init validation."""
    pass
