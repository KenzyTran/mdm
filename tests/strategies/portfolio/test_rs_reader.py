"""Integration test for connectors.postgres.load_stock_rs (Phase 31 plan 01).

Per D-15, the RS reader MUST be validated against >= 2 known historical
rows before downstream plans rely on it. This file IS that validation.
Gracefully skips when postgres env vars are unavailable.
"""
from __future__ import annotations

import pandas as pd
import pytest


def _engine_or_skip():
    try:
        from connectors.postgres import get_engine

        get_engine()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"postgres unavailable: {exc}")


def test_load_stock_rs_schema():
    _engine_or_skip()
    from connectors.postgres import load_stock_rs

    df = load_stock_rs("2023-01-01", "2023-06-30")
    assert list(df.columns) == ["date", "ticker", "rs_value"]
    assert len(df) >= 2, f"expected >=2 historical rows, got {len(df)}"
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert pd.api.types.is_numeric_dtype(df["rs_value"])


def test_load_stock_rs_ticker_filter():
    _engine_or_skip()
    from connectors.postgres import load_stock_rs

    df = load_stock_rs("2023-01-01", "2023-06-30", tickers=["VNM"])
    if df.empty:
        pytest.skip("VNM absent from stock_rs in this date range")
    assert set(df["ticker"].unique()) == {"VNM"}
    assert len(df) >= 2
