---
phase: 28-data-audit-connectors
plan: 01
type: execute
wave: 1
depends_on: ["28-00"]
files_modified:
  - connectors/postgres.py
  - tests/test_connectors_postgres.py
autonomous: true
requirements: [DATA-01]
must_haves:
  truths:
    - "Python code can obtain a cached SQLAlchemy engine for Postgres using only .env credentials"
    - "query(sql, params) returns a pandas DataFrame"
    - "load_stock_eod(tickers, start, end) returns OHLCV rows from stock_eod for the requested window"
    - "load_ratios(tickers) returns rows from ratios_stock for the requested tickers"
    - "Integration test against live Postgres returns >0 rows from stock_eod LIMIT 5"
  artifacts:
    - path: connectors/postgres.py
      provides: "get_engine, query, load_stock_eod, load_ratios"
      exports: ["get_engine", "query", "load_stock_eod", "load_ratios"]
      min_lines: 60
    - path: tests/test_connectors_postgres.py
      provides: "unit + integration tests for postgres connector"
  key_links:
    - from: connectors/postgres.py
      to: ".env"
      via: "os.getenv after dotenv.load_dotenv"
      pattern: "POSTGRES_HOST"
    - from: connectors/postgres.py
      to: "sqlalchemy.create_engine"
      via: "URL postgresql+psycopg2://..."
      pattern: "create_engine"
---

<objective>
Create `connectors/postgres.py` with engine factory, generic query helper, and two domain helpers (`load_stock_eod`, `load_ratios`). Closes DATA-01.

Purpose: Phase 29+ (CANSLIM scorer) needs a single import line to pull VN100 OHLCV and fundamentals from Postgres.
Output: Working connector module + passing unit tests + passing integration test against live Postgres.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/28-data-audit-connectors/28-CONTEXT.md
@.planning/phases/28-data-audit-connectors/28-RESEARCH.md
@.planning/phases/28-data-audit-connectors/28-00-SUMMARY.md
@strategies/mdm_classic/data_loader.py
@CLAUDE.md

<interfaces>
<!-- Contracts this plan defines (consumed by plans 02, 03, 04, 05) -->

```python
# connectors/postgres.py
from typing import Iterable, Optional, Mapping, Any
import pandas as pd
from sqlalchemy.engine import Engine

def get_engine() -> Engine: ...
def query(sql: str, params: Optional[Mapping[str, Any]] = None) -> pd.DataFrame: ...
def load_stock_eod(
    tickers: Iterable[str],
    start: str,           # 'YYYY-MM-DD'
    end: str,             # 'YYYY-MM-DD'
) -> pd.DataFrame:
    """Returns columns: stockcode, tradingdate (datetime64), openprice,
    highestprice, lowestprice, closeprice, totalvol, totaladjustrate."""

def load_ratios(tickers: Iterable[str]) -> pd.DataFrame:
    """Returns all rows from ratios_stock for the given tickers."""
```

stock_eod schema (relevant columns): stockcode, tradingdate, openprice, highestprice, lowestprice, closeprice, totalvol, totaladjustrate
ratios_stock schema (relevant columns): stockcode, period (or yearreport/lengthreport), eps, roe, pe, marketcap (verify column names at runtime via `SELECT column_name FROM information_schema.columns WHERE table_name='ratios_stock'`)

.env keys: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement connectors/postgres.py</name>
  <files>connectors/postgres.py</files>
  <read_first>
    - connectors/__init__.py (created in 28-00)
    - tests/conftest.py (fixtures available)
    - .env (verify POSTGRES_* keys present, do not log values)
    - strategies/mdm_classic/data_loader.py (column-mapping convention)
  </read_first>
  <behavior>
    - get_engine() returns a sqlalchemy.Engine; calling twice returns the SAME object (cached via module-level singleton).
    - get_engine() raises RuntimeError if any of POSTGRES_HOST/USER/PASSWORD/DB missing.
    - query("SELECT 1 AS x") returns DataFrame with column 'x' and one row value 1 (integration only).
    - load_stock_eod(["VNM"], "2024-01-01", "2024-01-31") returns DataFrame with required columns and tradingdate dtype is datetime64.
    - load_stock_eod accepts a list/tuple/set of tickers and parameterizes safely (no SQL injection — use bound params).
    - load_ratios(["VNM"]) returns DataFrame with stockcode column, all rows have stockcode=='VNM'.
  </behavior>
  <action>
    Create `connectors/postgres.py`:

    ```python
    """Postgres connector for VN market data (TA schema).

    Credentials sourced from .env via python-dotenv. Per phase 28 D-01..D-04.
    """
    from __future__ import annotations

    import os
    from typing import Any, Iterable, Mapping, Optional

    import pandas as pd
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine

    load_dotenv()

    _engine: Optional[Engine] = None


    def _build_url() -> str:
        host = os.getenv("POSTGRES_HOST")
        user = os.getenv("POSTGRES_USER")
        pw   = os.getenv("POSTGRES_PASSWORD")
        db   = os.getenv("POSTGRES_DB")
        port = os.getenv("POSTGRES_PORT", "5432")
        missing = [k for k, v in {
            "POSTGRES_HOST": host, "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": pw, "POSTGRES_DB": db,
        }.items() if not v]
        if missing:
            raise RuntimeError(f"Missing Postgres env vars: {missing}")
        return f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"


    def get_engine() -> Engine:
        """Return cached SQLAlchemy engine for Postgres."""
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
        """Execute parameterized SQL and return DataFrame."""
        with get_engine().connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})


    def load_stock_eod(
        tickers: Iterable[str],
        start: str,
        end: str,
    ) -> pd.DataFrame:
        """Load OHLCV+adjustrate from stock_eod for given tickers/date range."""
        tickers = list(tickers)
        sql = """
            SELECT stockcode, tradingdate,
                   openprice, highestprice, lowestprice, closeprice,
                   totalvol, totaladjustrate
            FROM stock_eod
            WHERE stockcode = ANY(:tickers)
              AND tradingdate BETWEEN :start AND :end
            ORDER BY stockcode, tradingdate
        """
        df = query(sql, {"tickers": tickers, "start": start, "end": end})
        if not df.empty:
            df["tradingdate"] = pd.to_datetime(df["tradingdate"])
        return df


    def load_ratios(tickers: Iterable[str]) -> pd.DataFrame:
        """Load all rows from ratios_stock for the given tickers."""
        tickers = list(tickers)
        sql = "SELECT * FROM ratios_stock WHERE stockcode = ANY(:tickers)"
        return query(sql, {"tickers": tickers})
    ```

    Per D-01 (SQLAlchemy + read_sql), D-02 (module layout), D-03 (.env only).
  </action>
  <verify>
    <automated>uv run python -c "from connectors.postgres import get_engine, query, load_stock_eod, load_ratios; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f connectors/postgres.py`
    - `grep -q 'def get_engine' connectors/postgres.py`
    - `grep -q 'def query' connectors/postgres.py`
    - `grep -q 'def load_stock_eod' connectors/postgres.py`
    - `grep -q 'def load_ratios' connectors/postgres.py`
    - `grep -q 'load_dotenv' connectors/postgres.py`
    - `grep -q 'create_engine' connectors/postgres.py`
    - `grep -q 'pool_pre_ping' connectors/postgres.py`
    - No hardcoded password (`grep -v POSTGRES_PASSWORD connectors/postgres.py | grep -i 'password.*=.*[a-zA-Z0-9]' || true` — manual review)
    - Module imports without error
  </acceptance_criteria>
  <done>Module exposes the four functions, imports cleanly, uses .env exclusively for credentials.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Write unit + integration tests for connectors.postgres</name>
  <files>tests/test_connectors_postgres.py</files>
  <read_first>
    - connectors/postgres.py (just-created interface)
    - tests/conftest.py (skip_if_no_pg, fake_ohlc_df fixtures)
    - .planning/phases/28-data-audit-connectors/28-VALIDATION.md (rows 28-01-01, 28-01-02)
  </read_first>
  <behavior>
    Unit tests (no DB):
    - test_get_engine_missing_creds_raises: monkeypatch env to clear POSTGRES_HOST -> RuntimeError
    - test_get_engine_cached: with creds set, two calls return same object
    - test_build_url_format: url starts with "postgresql+psycopg2://"
    Integration tests (require live DB, marked):
    - test_query_select_one: query("SELECT 1 AS x") returns DataFrame with one row, x==1
    - test_load_stock_eod_smoke: load_stock_eod(["VNM"], "2024-01-02", "2024-01-31") returns >0 rows; columns include tradingdate, closeprice, totaladjustrate
    - test_load_ratios_smoke: load_ratios(["VNM"]) returns DataFrame with stockcode column, all values == "VNM"
  </behavior>
  <action>
    Replace stub `tests/test_connectors_postgres.py` with:

    ```python
    """Tests for connectors.postgres — DATA-01."""
    import importlib
    import os
    import pandas as pd
    import pytest

    from tests.conftest import skip_if_no_pg


    def _reload():
        import connectors.postgres as m
        m._engine = None
        return importlib.reload(m)


    def test_get_engine_missing_creds_raises(monkeypatch):
        for k in ("POSTGRES_HOST","POSTGRES_USER","POSTGRES_PASSWORD","POSTGRES_DB"):
            monkeypatch.delenv(k, raising=False)
        m = _reload()
        with pytest.raises(RuntimeError, match="Missing Postgres env vars"):
            m.get_engine()


    @skip_if_no_pg
    def test_get_engine_cached():
        m = _reload()
        e1 = m.get_engine()
        e2 = m.get_engine()
        assert e1 is e2


    @skip_if_no_pg
    @pytest.mark.integration
    def test_query_select_one():
        from connectors.postgres import query
        df = query("SELECT 1 AS x")
        assert isinstance(df, pd.DataFrame)
        assert df.iloc[0]["x"] == 1


    @skip_if_no_pg
    @pytest.mark.integration
    def test_load_stock_eod_smoke():
        from connectors.postgres import load_stock_eod
        df = load_stock_eod(["VNM"], "2024-01-02", "2024-01-31")
        assert len(df) > 0
        for col in ("stockcode","tradingdate","openprice","closeprice","totalvol","totaladjustrate"):
            assert col in df.columns
        assert df["tradingdate"].dtype.kind == "M"
        assert (df["stockcode"] == "VNM").all()


    @skip_if_no_pg
    @pytest.mark.integration
    def test_load_ratios_smoke():
        from connectors.postgres import load_ratios
        df = load_ratios(["VNM"])
        assert len(df) > 0
        assert "stockcode" in df.columns
        assert (df["stockcode"] == "VNM").all()
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/test_connectors_postgres.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q 'test_get_engine_missing_creds_raises' tests/test_connectors_postgres.py`
    - `grep -q 'test_load_stock_eod_smoke' tests/test_connectors_postgres.py`
    - `grep -q 'pytest.mark.integration' tests/test_connectors_postgres.py`
    - `uv run pytest tests/test_connectors_postgres.py -m "not integration" -q` passes (unit tests green)
    - `uv run pytest tests/test_connectors_postgres.py -m integration -q` passes when DB reachable (or all skipped if creds missing)
  </acceptance_criteria>
  <done>Unit tests pass without DB, integration tests pass against live Postgres returning real rows from stock_eod and ratios_stock.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_connectors_postgres.py -q` green
- DATA-01 closed: connector module exists, integration test queries stock_eod successfully
</verification>

<success_criteria>
- connectors/postgres.py exposes get_engine/query/load_stock_eod/load_ratios
- Unit tests pass with no DB; integration tests pass with live DB
- No hardcoded credentials anywhere
</success_criteria>

<output>
Create `.planning/phases/28-data-audit-connectors/28-01-SUMMARY.md` after completion.
</output>
