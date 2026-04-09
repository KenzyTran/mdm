---
phase: 32-vn100-backtest-in-sample-sweep
plan: 00
subsystem: tests/phase32
tags: [scaffold, tests, env]
requires: []
provides: [tests/phase32 fixtures, pyarrow, tqdm]
affects: [pyproject.toml]
tech_stack:
  added: [pyarrow>=14.0.0, tqdm>=4.66.0]
  patterns: [pytest fixtures, top-level mp helper for Windows spawn]
key_files:
  created:
    - tests/phase32/__init__.py
    - tests/phase32/conftest.py
    - tests/phase32/test_scaffold.py
  modified:
    - pyproject.toml
decisions:
  - Use top-level `_double` helper (not lambda) for multiprocessing Pool to work on Windows spawn
  - Synthetic OHLC = 3 tickers (AAA/BBB/CCC) x 30 business days, monotonic uptrend per ticker
metrics:
  tasks: 1
  duration: ~2m
  completed: 2026-04-09
---

# Phase 32 Plan 00: Wave 0 Scaffold Summary

One-liner: Bootstrap `tests/phase32/` with env-check tests, shared synthetic OHLC + universe fixtures, and add `pyarrow` / `tqdm` deps so Wave 1 plans can run.

## What Was Built

- `tests/phase32/__init__.py` — package marker.
- `tests/phase32/conftest.py` — two fixtures:
  - `synthetic_ohlc` returns a pandas DataFrame (90 rows = 3 tickers x 30 bdays) with columns `stockcode, tradingdate, openprice, highprice, lowprice, closeprice, volume`.
  - `synthetic_universe` returns `{date: [AAA, BBB, CCC]}` for the same 30-day span.
- `tests/phase32/test_scaffold.py` — three env tests:
  - `test_imports_pyarrow` / `test_imports_tqdm` assert versions.
  - `test_multiprocessing_pool` spins `Pool(2)` and maps top-level `_double` over `[1,2,3]`.
- `pyproject.toml` — added `pyarrow>=14.0.0` and `tqdm>=4.66.0` to `[project] dependencies`.

## Verification

- `uv run pytest tests/phase32/test_scaffold.py -x -q` → `3 passed in 0.12s`.
- `pyarrow` installed by uv (26.3 MiB).
- `tqdm` already resolvable from transitive deps.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

- `cf190d5` test(32-00): add phase32 scaffold tests and env deps

## Self-Check: PASSED

- FOUND: tests/phase32/__init__.py
- FOUND: tests/phase32/conftest.py
- FOUND: tests/phase32/test_scaffold.py
- FOUND: pyproject.toml (pyarrow + tqdm lines present)
- FOUND commit: cf190d5
