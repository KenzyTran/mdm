"""Tests for flow rules (I, S) — CANS-06, CANS-08."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from strategies.canslim.config import CanslimConfig
from strategies.canslim.rules import flow


def test_flow_module_imports():
    assert hasattr(flow, "compute_i")
    assert hasattr(flow, "compute_s")
    assert flow.FOREIGN_DATA_START == date(2022, 4, 7)


# ---------------- compute_i — CANS-08 ----------------


def test_compute_i_pre_2022_fallback_returns_true():
    """Pre-2022-04-07 → always True regardless of DB."""
    cfg = CanslimConfig()
    with patch("strategies.canslim.rules.flow.pd.read_sql") as m:
        m.return_value = pd.DataFrame({"net_buy": []})
        assert flow.compute_i("HPG", date(2020, 6, 15), cfg, pg_engine=None) is True
    m.assert_not_called()


def test_compute_i_positive_net_buy_passes():
    cfg = CanslimConfig()
    fake = pd.DataFrame({"net_buy": [1_000_000] * 20})
    with patch("strategies.canslim.rules.flow.pd.read_sql", return_value=fake):
        assert flow.compute_i("HPG", date(2024, 1, 15), cfg, pg_engine=object()) is True


def test_compute_i_negative_net_buy_fails():
    cfg = CanslimConfig()
    fake = pd.DataFrame({"net_buy": [-50_000] * 20})
    with patch("strategies.canslim.rules.flow.pd.read_sql", return_value=fake):
        assert flow.compute_i("HPG", date(2024, 1, 15), cfg, pg_engine=object()) is False


def test_compute_i_zero_net_buy_fails_strict():
    """Strictly > 0, so exactly zero must return False."""
    cfg = CanslimConfig()
    fake = pd.DataFrame({"net_buy": [0] * 20})
    with patch("strategies.canslim.rules.flow.pd.read_sql", return_value=fake):
        assert flow.compute_i("HPG", date(2024, 1, 15), cfg, pg_engine=object()) is False


def test_compute_i_empty_result_fails():
    """Post-2022 ticker with no rows → False (no silent pass)."""
    cfg = CanslimConfig()
    fake = pd.DataFrame({"net_buy": []})
    with patch("strategies.canslim.rules.flow.pd.read_sql", return_value=fake):
        assert flow.compute_i("ZZZ", date(2024, 1, 15), cfg, pg_engine=object()) is False


def test_compute_i_uses_i_lookback_days_param():
    """LIMIT must be bound from ``config.i_lookback_days`` (trading rows, not calendar)."""
    cfg = CanslimConfig(i_lookback_days=15)
    fake = pd.DataFrame({"net_buy": [1] * 15})
    captured = {}

    def fake_read_sql(sql, engine, params):
        captured["params"] = params
        captured["sql"] = sql
        return fake

    with patch("strategies.canslim.rules.flow.pd.read_sql", side_effect=fake_read_sql):
        flow.compute_i("HPG", date(2024, 1, 15), cfg, pg_engine=object())

    assert captured["params"]["n"] == 15
    assert captured["params"]["t"] == "HPG"
    assert captured["params"]["d"] == date(2024, 1, 15)
    assert "LIMIT" in captured["sql"]


# ---------------- compute_s wrapper — CANS-06 ----------------


def test_compute_s_delegates_to_technical():
    """flow.compute_s must delegate to technical.compute_s for consistency."""
    cfg = CanslimConfig()
    df = pd.DataFrame()
    with patch("strategies.canslim.rules.flow.technical.compute_s", return_value=True) as m:
        assert flow.compute_s(df, date(2024, 1, 15), cfg) is True
    m.assert_called_once()
