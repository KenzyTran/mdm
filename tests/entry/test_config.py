"""EntryConfig validation tests (ENTRY Wave 0 scaffold).

Covers the seven fail-loud branches in
``strategies/entry/config.py::EntryConfig.__post_init__`` plus the
defaults-construct-cleanly case. These are the only ``tests/entry/`` tests
that are GREEN on day 1 of Phase 30 — every other test file uses
``pytest.importorskip`` to RED-stub against modules not yet built.
"""
from __future__ import annotations

import pytest

from strategies.entry import EntryConfig


def test_defaults_construct_with_locked_values():
    cfg = EntryConfig()
    assert cfg.high_lookback == 252
    assert cfg.vol_lookback == 50
    assert cfg.vol_mult == 1.5
    assert cfg.ma_length == 50
    assert cfg.pocket_lookback == 10
    assert cfg.base_tolerance == 0.15
    assert cfg.window_days == 20


def test_rejects_high_lookback_too_small():
    with pytest.raises(ValueError, match="high_lookback must be >= 2"):
        EntryConfig(high_lookback=1)


def test_rejects_vol_lookback_zero():
    with pytest.raises(ValueError, match="vol_lookback must be >= 1"):
        EntryConfig(vol_lookback=0)


def test_rejects_vol_mult_below_one():
    with pytest.raises(ValueError, match="vol_mult must be >= 1.0"):
        EntryConfig(vol_mult=0.9)


def test_rejects_ma_length_too_small():
    with pytest.raises(ValueError, match="ma_length must be >= 2"):
        EntryConfig(ma_length=1)


def test_rejects_pocket_lookback_zero():
    with pytest.raises(ValueError, match="pocket_lookback must be >= 1"):
        EntryConfig(pocket_lookback=0)


def test_rejects_base_tolerance_zero():
    with pytest.raises(ValueError, match=r"base_tolerance must be in \(0, 1\)"):
        EntryConfig(base_tolerance=0.0)


def test_rejects_base_tolerance_one():
    with pytest.raises(ValueError, match=r"base_tolerance must be in \(0, 1\)"):
        EntryConfig(base_tolerance=1.0)


def test_rejects_window_days_zero():
    with pytest.raises(ValueError, match="window_days must be >= 1"):
        EntryConfig(window_days=0)
