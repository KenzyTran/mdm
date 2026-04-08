---
phase: 28-data-audit-connectors
plan: 02
type: execute
wave: 1
depends_on: ["28-00"]
files_modified:
  - connectors/mysql.py
  - tests/test_connectors_mysql.py
autonomous: true
requirements: [DATA-02]
must_haves:
  truths:
    - "Python code can obtain a cached SQLAlchemy engine for MySQL using only .env credentials"
    - "query(sql, params) returns a pandas DataFrame from MySQL"
    - "load_ratios_stock(tickers) returns rows from stocks_backend.ratios_stock"
    - "load_is_quarter(tickers, sector='nonbank') routes to is_quarter_nonbank/bank/insurance/stock based on sector arg"
    - "Integration test against live MySQL returns >0 rows from ratios_stock"
  artifacts:
    - path: connectors/mysql.py
      provides: "get_engine, query, load_ratios_stock, load_is_quarter"
      exports: ["get_engine", "query", "load_ratios_stock", "load_is_quarter"]
      min_lines: 60
    - path: tests/test_connectors_mysql.py
      provides: "unit + integration tests for mysql connector"
  key_links:
    - from: connectors/mysql.py
      to: ".env"
      via: "os.getenv after dotenv.load_dotenv"
      pattern: "MYSQL_HOST"
    - from: connectors/mysql.py
      to: "sqlalchemy.create_engine"
      via: "URL mysql+pymysql://..."
      pattern: "create_engine"
---

<objective>
Create `connectors/mysql.py` mirroring the postgres connector for the MySQL fundamentals DB. Closes DATA-02.

Purpose: Phase 29 CANSLIM scorer needs ratios_stock + is_quarter_* tables for EPS, growth, ROE, P/E.
Output: Working connector module + passing unit tests + passing integration test against live MySQL.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/28-data-audit-connectors/28-CONTEXT.md
@.planning/phases/28-data-audit-connectors/28-RESEARCH.md
@.planning/phases/28-data-audit-connectors/28-00-SUMMARY.md
@CLAUDE.md

<interfaces>
```python
# connectors/mysql.py
from typing import Iterable, Optional, Mapping, Any, Literal
import pandas as pd
from sqlalchemy.engine import Engine

def get_engine() -> Engine: ...
def query(sql: str, params: Optional[Mapping[str, Any]] = None) -> pd.DataFrame: ...
def load_ratios_stock(tickers: Iterable[str]) -> pd.DataFrame: ...
def load_is_quarter(
    tickers: Iterable[str],
    sector: Literal["nonbank","bank","insurance","stock"] = "nonbank",
) -> pd.DataFrame: ...
```

.env keys: MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
Tables: ratios_stock, is_quarter_nonbank, is_quarter_bank, is_quarter_insurance, is_quarter_stock, rank_top_stocks
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement connectors/mysql.py</name>
  <files>connectors/mysql.py</files>
  <read_first>
    - connectors/postgres.py (mirror its structure exactly)
    - tests/conftest.py (skip_if_no_mysql fixture)
    - .env (verify MYSQL_* keys present)
  </read_first>
  <behavior>
    - get_engine() cached singleton; raises RuntimeError if any MYSQL_HOST/USER/PASSWORD/DB missing
    - URL format mysql+pymysql://user:pw@host:port/db?charset=utf8mb4
    - query(sql, params) returns DataFrame
    - load_ratios_stock(["VNM"]) returns rows where stockcode='VNM'
    - load_is_quarter(["VNM"], sector="nonbank") queries is_quarter_nonbank
    - load_is_quarter rejects unknown sector with ValueError
  </behavior>
  <action>
    Create `connectors/mysql.py` mirroring `connectors/postgres.py` structure:

    ```python
    """MySQL connector for VN fundamentals (stocks_backend schema).

    Credentials sourced from .env via python-dotenv. Per phase 28 D-01..D-04.
    """
    from __future__ import annotations

    import os
    from typing import Any, Iterable, Literal, Mapping, Optional

    import pandas as pd
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine

    load_dotenv()

    _engine: Optional[Engine] = None

    _ALLOWED_SECTORS = {"nonbank", "bank", "insurance", "stock"}


    def _build_url() -> str:
        host = os.getenv("MYSQL_HOST")
        user = os.getenv("MYSQL_USER")
        pw   = os.getenv("MYSQL_PASSWORD")
        db   = os.getenv("MYSQL_DB")
        port = os.getenv("MYSQL_PORT", "3306")
        missing = [k for k, v in {
            "MYSQL_HOST": host, "MYSQL_USER": user,
            "MYSQL_PASSWORD": pw, "MYSQL_DB": db,
        }.items() if not v]
        if missing:
            raise RuntimeError(f"Missing MySQL env vars: {missing}")
        return f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}?charset=utf8mb4"


    def get_engine() -> Engine:
        global _engine
        if _engine is None:
            _engine = create_engine(
                _build_url(),
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
                future=True,
            )
        return _engine


    def query(sql: str, params: Optional[Mapping[str, Any]] = None) -> pd.DataFrame:
        with get_engine().connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})


    def load_ratios_stock(tickers: Iterable[str]) -> pd.DataFrame:
        tickers = list(tickers)
        # MySQL doesn't support ANY(:list) — use IN with expanding bindparam
        from sqlalchemy import bindparam
        sql = text("SELECT * FROM ratios_stock WHERE stockcode IN :tickers").bindparams(
            bindparam("tickers", expanding=True)
        )
        with get_engine().connect() as conn:
            return pd.read_sql(sql, conn, params={"tickers": tickers})


    def load_is_quarter(
        tickers: Iterable[str],
        sector: Literal["nonbank", "bank", "insurance", "stock"] = "nonbank",
    ) -> pd.DataFrame:
        if sector not in _ALLOWED_SECTORS:
            raise ValueError(f"sector must be one of {_ALLOWED_SECTORS}, got {sector!r}")
        tickers = list(tickers)
        from sqlalchemy import bindparam
        sql = text(
            f"SELECT * FROM is_quarter_{sector} WHERE stockcode IN :tickers"
        ).bindparams(bindparam("tickers", expanding=True))
        with get_engine().connect() as conn:
            return pd.read_sql(sql, conn, params={"tickers": tickers})
    ```

    Per D-01, D-02, D-03.
  </action>
  <verify>
    <automated>uv run python -c "from connectors.mysql import get_engine, query, load_ratios_stock, load_is_quarter; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f connectors/mysql.py`
    - `grep -q 'def get_engine' connectors/mysql.py`
    - `grep -q 'def load_ratios_stock' connectors/mysql.py`
    - `grep -q 'def load_is_quarter' connectors/mysql.py`
    - `grep -q 'mysql+pymysql' connectors/mysql.py`
    - `grep -q '_ALLOWED_SECTORS' connectors/mysql.py`
    - `grep -q 'load_dotenv' connectors/mysql.py`
    - Module imports without error
  </acceptance_criteria>
  <done>Module exposes the four functions, imports cleanly, sector whitelist enforced, .env-only credentials.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Write unit + integration tests for connectors.mysql</name>
  <files>tests/test_connectors_mysql.py</files>
  <read_first>
    - connectors/mysql.py (just-created interface)
    - tests/conftest.py (skip_if_no_mysql)
    - tests/test_connectors_postgres.py (mirror structure)
  </read_first>
  <behavior>
    Unit tests:
    - test_get_engine_missing_creds_raises
    - test_load_is_quarter_rejects_bad_sector (ValueError)
    Integration tests:
    - test_query_select_one
    - test_load_ratios_stock_smoke (>0 rows for VNM)
    - test_load_is_quarter_nonbank_smoke (>0 rows for VNM)
  </behavior>
  <action>
    Replace stub `tests/test_connectors_mysql.py` with:

    ```python
    """Tests for connectors.mysql — DATA-02."""
    import importlib
    import pandas as pd
    import pytest

    from tests.conftest import skip_if_no_mysql


    def _reload():
        import connectors.mysql as m
        m._engine = None
        return importlib.reload(m)


    def test_get_engine_missing_creds_raises(monkeypatch):
        for k in ("MYSQL_HOST","MYSQL_USER","MYSQL_PASSWORD","MYSQL_DB"):
            monkeypatch.delenv(k, raising=False)
        m = _reload()
        with pytest.raises(RuntimeError, match="Missing MySQL env vars"):
            m.get_engine()


    def test_load_is_quarter_rejects_bad_sector():
        from connectors.mysql import load_is_quarter
        with pytest.raises(ValueError, match="sector must be one of"):
            load_is_quarter(["VNM"], sector="bogus")  # type: ignore[arg-type]


    @skip_if_no_mysql
    @pytest.mark.integration
    def test_query_select_one():
        from connectors.mysql import query
        df = query("SELECT 1 AS x")
        assert df.iloc[0]["x"] == 1


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
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/test_connectors_mysql.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q 'test_load_is_quarter_rejects_bad_sector' tests/test_connectors_mysql.py`
    - `grep -q 'pytest.mark.integration' tests/test_connectors_mysql.py`
    - `uv run pytest tests/test_connectors_mysql.py -m "not integration" -q` green
    - `uv run pytest tests/test_connectors_mysql.py -m integration -q` green when DB reachable
  </acceptance_criteria>
  <done>Unit tests pass without DB; integration tests fetch real ratios + is_quarter rows for VNM.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_connectors_mysql.py -q` green
- DATA-02 closed
</verification>

<success_criteria>
- connectors/mysql.py mirrors postgres connector with sector router
- Unit + integration tests pass
- No hardcoded credentials
</success_criteria>

<output>
Create `.planning/phases/28-data-audit-connectors/28-02-SUMMARY.md` after completion.
</output>
