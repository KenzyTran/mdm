"""Tests for connectors.mysql — DATA-02."""
from __future__ import annotations

import importlib

import pytest


def _mysql_reachable() -> bool:
    try:
        from connectors.mysql import get_engine
        eng = get_engine()
        with eng.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


skip_if_no_mysql = pytest.mark.skipif(
    not _mysql_reachable(), reason="MySQL not reachable / creds missing"
)


def _reload():
    import connectors.mysql as m
    m._engine = None
    return importlib.reload(m)


# ---------------- unit tests ----------------


def test_get_engine_missing_creds_raises(monkeypatch):
    for k in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD",
              "MYSQL_DB", "MYSQL_DATABASE"):
        monkeypatch.delenv(k, raising=False)
    # Prevent dotenv from re-populating during reload.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: False)
    m = _reload()
    m._engine = None
    with pytest.raises(RuntimeError, match="Missing MySQL env vars"):
        m.get_engine()
    # Restore clean module state for other tests.
    _reload()


def test_load_is_quarter_rejects_bad_sector():
    from connectors.mysql import load_is_quarter
    with pytest.raises(ValueError, match="sector must be one of"):
        load_is_quarter(["VNM"], sector="bogus")  # type: ignore[arg-type]


# ---------------- integration tests ----------------


@skip_if_no_mysql
@pytest.mark.integration
def test_query_select_one():
    from connectors.mysql import query
    df = query("SELECT 1 AS x")
    assert int(df.iloc[0]["x"]) == 1


@skip_if_no_mysql
@pytest.mark.integration
def test_load_ratios_stock_smoke():
    from connectors.mysql import load_ratios_stock
    df = load_ratios_stock(["VNM"])
    assert len(df) > 0
    assert "stockcode" in df.columns
    assert (df["stockcode"] == "VNM").all()


@skip_if_no_mysql
@pytest.mark.integration
def test_load_is_quarter_nonbank_smoke():
    from connectors.mysql import load_is_quarter
    df = load_is_quarter(["VNM"], sector="nonbank")
    assert len(df) > 0
    assert "stockcode" in df.columns
