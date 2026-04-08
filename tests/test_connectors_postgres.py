"""Tests for connectors.postgres — DATA-01."""
import importlib
import os

import pandas as pd
import pytest
from dotenv import load_dotenv

# Load .env before evaluating skip markers so integration tests run when
# credentials are present locally.
load_dotenv()

# Resolve skip_if_no_pg from conftest if available (added by 28-00); otherwise
# fall back to a local skip marker based on env credentials.
try:  # pragma: no cover - import shim
    from tests.conftest import skip_if_no_pg  # type: ignore
except Exception:  # pragma: no cover
    _have_db = os.getenv("POSTGRES_DB") or os.getenv("POSTGRES_DATABASE")
    skip_if_no_pg = pytest.mark.skipif(
        not (
            os.getenv("POSTGRES_HOST")
            and os.getenv("POSTGRES_USER")
            and os.getenv("POSTGRES_PASSWORD")
            and _have_db
        ),
        reason="Postgres credentials not available",
    )


def _reload():
    import connectors.postgres as m
    m._engine = None
    return importlib.reload(m)


def test_get_engine_missing_creds_raises(monkeypatch):
    for k in ("POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        monkeypatch.delenv(k, raising=False)
    # Prevent dotenv from reloading real values on reload
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    m = _reload()
    with pytest.raises(RuntimeError, match="Missing Postgres env vars"):
        m.get_engine()


def test_build_url_format(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "h")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    monkeypatch.setenv("POSTGRES_DB", "d")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    m = _reload()
    url = m._build_url()
    assert url.startswith("postgresql+psycopg2://")
    assert "@h:5432/d" in url


@skip_if_no_pg
def test_get_engine_cached():
    m = _reload()
    e1 = m.get_engine()
    e2 = m.get_engine()
    assert e1 is e2


@skip_if_no_pg
@pytest.mark.integration
def test_query_select_one():
    _reload()
    from connectors.postgres import query
    df = query("SELECT 1 AS x")
    assert isinstance(df, pd.DataFrame)
    assert int(df.iloc[0]["x"]) == 1


@skip_if_no_pg
@pytest.mark.integration
def test_load_stock_eod_smoke():
    _reload()
    from connectors.postgres import load_stock_eod
    df = load_stock_eod(["VNM"], "2024-01-02", "2024-01-31")
    assert len(df) > 0
    for col in (
        "stockcode", "tradingdate", "openprice", "closeprice",
        "totalvol", "totaladjustrate",
    ):
        assert col in df.columns
    assert df["tradingdate"].dtype.kind == "M"
    assert (df["stockcode"] == "VNM").all()


@skip_if_no_pg
@pytest.mark.integration
def test_load_ratios_smoke():
    _reload()
    from connectors.postgres import load_ratios
    df = load_ratios(["VNM"])
    assert len(df) > 0
    assert "stockcode" in df.columns
    assert (df["stockcode"] == "VNM").all()
