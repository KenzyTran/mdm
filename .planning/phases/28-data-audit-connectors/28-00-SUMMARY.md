---
phase: 28-data-audit-connectors
plan: "00"
subsystem: data-layer
tags: [scaffold, deps, pytest, connectors]
requires: []
provides:
  - connectors package (importable)
  - pytest integration marker
  - shared test fixtures (fake_ohlc_df, skip_if_no_pg, skip_if_no_mysql)
  - docs/audits/ directory
affects:
  - pyproject.toml
  - tests/conftest.py
tech_stack:
  added: [sqlalchemy>=2.0, psycopg2-binary>=2.9, pymysql>=1.1]
  patterns: [env-driven credentials via python-dotenv, pytest skipif markers]
key_files:
  created:
    - docs/audits/.gitkeep
    - tests/test_adjust.py
    - tests/test_eps_publish.py
  modified:
    - pyproject.toml
    - tests/conftest.py
decisions:
  - SQLAlchemy 2.0 as unified DB layer (D-01)
  - .env-driven creds via python-dotenv (D-03)
  - integration marker for live-DB tests (deselect with -m 'not integration')
metrics:
  duration: ~3m
  completed_date: 2026-04-08
  tasks: 2
  commits: 2
---

# Phase 28 Plan 00: Setup Summary

Wave 0 scaffolding for data-audit-connectors: DB deps installed, connectors package confirmed importable, pytest harness extended with shared fixtures and integration marker, docs/audits directory created.

## What Was Done

### Task 1 — Deps + pytest config (commit 45ba312)

- Added `sqlalchemy>=2.0`, `psycopg2-binary>=2.9`, `pymysql>=1.1` to `[project].dependencies`.
- Extended `[tool.pytest.ini_options].markers` with `integration` marker (preserved existing `regression` marker).
- `uv sync` succeeded; `import sqlalchemy, psycopg2, pymysql` succeeds.

### Task 2 — Package + tests scaffold + docs/audits (commit ef3675e)

- `connectors/__init__.py` already present from parallel wave-1 work (importable, verified).
- `tests/__init__.py` already present.
- `tests/conftest.py` extended with:
  - `load_dotenv()` at import time
  - `fake_ohlc_df` fixture (synthetic stock_eod-shaped DataFrame with split on row 4)
  - `_has_pg_creds` / `_has_mysql_creds` helpers
  - `skip_if_no_pg` / `skip_if_no_mysql` skipif markers
- `tests/test_connectors_postgres.py` and `tests/test_connectors_mysql.py` already created by parallel executors with richer content (Wave 1 already in flight) — not touched here.
- `tests/test_adjust.py` and `tests/test_eps_publish.py` created as skipping stubs (to be implemented in 28-03 / 28-04).
- `docs/audits/.gitkeep` created.

## Verification

- `uv sync` clean
- `uv run python -c "import connectors"` → ok
- `uv run python -c "import sqlalchemy, psycopg2, pymysql"` → ok
- `uv run pytest tests/ --collect-only -q` → 467 tests collected (scaffold stubs collect cleanly alongside existing suite)

## Deviations from Plan

**Scope-respectful parallel-coordination adjustments:**

1. **[Rule 3 - Blocking] connectors/__init__.py and tests/__init__.py already existed.** Other parallel executors (plans 28-01/02) had already created `connectors/__init__.py` with docstring `"""Data connectors package (Postgres/MySQL/Redis)."""` and an empty `tests/__init__.py`. Left both as-is — they satisfy the plan's acceptance criteria. No action needed.

2. **[Rule 3 - Blocking] tests/test_connectors_postgres.py and test_connectors_mysql.py already existed with real tests.** Parallel Wave 1 executors already populated these with full unit + integration tests. Left untouched; they are far richer than the scaffold stubs the plan requested, and rewriting them would destroy Wave 1 work. Acceptance criteria (file exists) still met.

3. **[Rule 3 - Blocking] tests/conftest.py already existed** with sys.path setup + FIXTURES path. Extended it in place rather than overwriting, preserving existing functionality and adding the required fake_ohlc_df fixture, skip markers, and load_dotenv call.

No architectural changes, no bugs fixed, no auth gates.

## Known Stubs

- `tests/test_adjust.py` — placeholder, implemented in 28-03
- `tests/test_eps_publish.py` — placeholder, implemented in 28-04

Both intentionally skip. Not blocking: they exist to ensure the test harness is ready from Wave 0 per Nyquist compliance.

## Self-Check: PASSED

- pyproject.toml contains sqlalchemy>=2.0, psycopg2-binary, pymysql, integration marker, regression marker: verified via grep in commit
- connectors/__init__.py exists: FOUND
- tests/conftest.py contains fake_ohlc_df, skip_if_no_pg, load_dotenv: FOUND
- tests/test_adjust.py exists: FOUND
- tests/test_eps_publish.py exists: FOUND
- docs/audits/.gitkeep exists: FOUND
- Commits 45ba312 and ef3675e present in git log: FOUND
- `uv run pytest tests/ --collect-only` exits 0: PASSED (467 collected)
