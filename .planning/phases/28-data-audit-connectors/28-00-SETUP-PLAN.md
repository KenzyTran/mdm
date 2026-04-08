---
phase: 28-data-audit-connectors
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - pyproject.toml
  - connectors/__init__.py
  - tests/__init__.py
  - tests/conftest.py
  - tests/test_connectors_postgres.py
  - tests/test_connectors_mysql.py
  - tests/test_adjust.py
  - tests/test_eps_publish.py
  - docs/audits/.gitkeep
autonomous: true
requirements: []
must_haves:
  truths:
    - "uv sync installs sqlalchemy, psycopg2-binary, pymysql, pytest"
    - "pytest collects 4 stub test files without import errors"
    - "connectors/ package importable"
    - "docs/audits/ directory exists"
  artifacts:
    - path: pyproject.toml
      provides: "deps + [tool.pytest.ini_options] integration marker"
      contains: "sqlalchemy"
    - path: connectors/__init__.py
      provides: "package marker"
    - path: tests/conftest.py
      provides: "shared fixtures: fake_ohlc_df, env_loader, skip_if_no_db"
  key_links:
    - from: tests/conftest.py
      to: ".env"
      via: "python-dotenv load_dotenv() in fixture"
      pattern: "load_dotenv"
---

<objective>
Wave 0 scaffolding: install DB deps, create connectors package, create test stubs and shared fixtures, create docs/audits dir.

Purpose: Wave 1+ tasks have a working test harness from the first commit (Nyquist compliance — every later task can run `pytest`).
Output: All deps installed, all stub test files exist and collect, integration marker registered.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/28-data-audit-connectors/28-CONTEXT.md
@.planning/phases/28-data-audit-connectors/28-VALIDATION.md
@pyproject.toml
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add deps + pytest config to pyproject.toml</name>
  <files>pyproject.toml</files>
  <read_first>
    - pyproject.toml (current deps + existing [tool.pytest.ini_options])
  </read_first>
  <action>
    Edit pyproject.toml:
    1. Add to `[project].dependencies` (preserve existing entries):
       - "sqlalchemy>=2.0"
       - "psycopg2-binary>=2.9"
       - "pymysql>=1.1"
    2. In existing `[tool.pytest.ini_options]` block, extend `markers` list to include:
       - "integration: requires live DB credentials (deselect with -m 'not integration')"
       Final markers list MUST contain BOTH the existing "regression" marker AND the new "integration" marker.
    3. Run `uv sync` to install.
    Per D-01, D-03 (SQLAlchemy + .env creds).
  </action>
  <verify>
    <automated>uv sync && uv run python -c "import sqlalchemy, psycopg2, pymysql; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q 'sqlalchemy>=2.0' pyproject.toml`
    - `grep -q 'psycopg2-binary' pyproject.toml`
    - `grep -q 'pymysql' pyproject.toml`
    - `grep -q 'integration: requires live DB' pyproject.toml`
    - `grep -q 'regression:' pyproject.toml` (existing marker still present)
    - `uv sync` exits 0
  </acceptance_criteria>
  <done>uv sync succeeds, all three libraries importable, integration marker registered alongside existing regression marker.</done>
</task>

<task type="auto">
  <name>Task 2: Create connectors package + tests scaffolding + docs/audits dir</name>
  <files>
    connectors/__init__.py,
    tests/__init__.py,
    tests/conftest.py,
    tests/test_connectors_postgres.py,
    tests/test_connectors_mysql.py,
    tests/test_adjust.py,
    tests/test_eps_publish.py,
    docs/audits/.gitkeep
  </files>
  <read_first>
    - .env (verify POSTGRES_*, MYSQL_* keys exist — do NOT print values)
    - strategies/mdm_classic/data_loader.py (column-mapping pattern to mirror in future connectors)
    - .planning/phases/28-data-audit-connectors/28-VALIDATION.md (Wave 0 Requirements section)
  </read_first>
  <action>
    1. `connectors/__init__.py` — empty file with single docstring `"""Database connectors package (Postgres, MySQL)."""`.

    2. `tests/__init__.py` — empty file.

    3. `tests/conftest.py` — shared fixtures:
       ```python
       """Shared pytest fixtures for phase 28 connectors."""
       import os
       import pandas as pd
       import pytest
       from dotenv import load_dotenv

       load_dotenv()

       @pytest.fixture
       def fake_ohlc_df():
           """Synthetic stock_eod-shaped DataFrame for unit tests."""
           return pd.DataFrame({
               "stockcode": ["AAA"] * 5,
               "tradingdate": pd.date_range("2024-01-02", periods=5, freq="B"),
               "openprice":   [10.0, 11.0, 12.0, 13.0, 14.0],
               "highestprice":[10.5, 11.5, 12.5, 13.5, 14.5],
               "lowestprice": [ 9.5, 10.5, 11.5, 12.5, 13.5],
               "closeprice":  [10.2, 11.2, 12.2, 13.2, 14.2],
               "totalvol":    [1000, 1100, 1200, 1300, 1400],
               "totaladjustrate": [2.0, 2.0, 2.0, 1.0, 1.0],  # split on row 4
           })

       def _has_pg_creds() -> bool:
           return all(os.getenv(k) for k in ("POSTGRES_HOST","POSTGRES_USER","POSTGRES_PASSWORD","POSTGRES_DB"))

       def _has_mysql_creds() -> bool:
           return all(os.getenv(k) for k in ("MYSQL_HOST","MYSQL_USER","MYSQL_PASSWORD","MYSQL_DB"))

       skip_if_no_pg = pytest.mark.skipif(not _has_pg_creds(), reason="Postgres creds not in .env")
       skip_if_no_mysql = pytest.mark.skipif(not _has_mysql_creds(), reason="MySQL creds not in .env")
       ```

    4. `tests/test_connectors_postgres.py` — stub:
       ```python
       """Tests for connectors.postgres — DATA-01."""
       import pytest

       def test_module_importable():
           import connectors  # noqa
           # Real tests added in plan 01.
           pytest.skip("scaffold — implemented in 28-01")
       ```

    5. `tests/test_connectors_mysql.py` — analogous stub, skip with message "scaffold — implemented in 28-02".

    6. `tests/test_adjust.py` — stub, skip "scaffold — implemented in 28-03".

    7. `tests/test_eps_publish.py` — stub, skip "scaffold — implemented in 28-04".

    8. `docs/audits/.gitkeep` — empty file so dir is committed.
  </action>
  <verify>
    <automated>uv run pytest tests/ --collect-only -q && test -d docs/audits && uv run python -c "import connectors"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f connectors/__init__.py`
    - `test -f tests/conftest.py`
    - `test -f tests/test_connectors_postgres.py`
    - `test -f tests/test_connectors_mysql.py`
    - `test -f tests/test_adjust.py`
    - `test -f tests/test_eps_publish.py`
    - `test -f docs/audits/.gitkeep`
    - `grep -q 'fake_ohlc_df' tests/conftest.py`
    - `grep -q 'skip_if_no_pg' tests/conftest.py`
    - `grep -q 'load_dotenv' tests/conftest.py`
    - `uv run pytest tests/ --collect-only -q` exits 0 and reports >=4 collected items
  </acceptance_criteria>
  <done>Package importable, all 4 stub test files collect cleanly, conftest exposes fake_ohlc_df + skip markers, docs/audits exists.</done>
</task>

</tasks>

<verification>
- `uv sync` clean
- `uv run pytest tests/ -q` exits 0 (skipped stubs are fine)
- `uv run python -c "import connectors; import sqlalchemy; import psycopg2; import pymysql"` exits 0
</verification>

<success_criteria>
Wave 0 done: deps installed, connectors package + tests scaffold + docs/audits exist, pytest can collect, integration marker registered.
</success_criteria>

<output>
Create `.planning/phases/28-data-audit-connectors/28-00-SUMMARY.md` after completion.
</output>
