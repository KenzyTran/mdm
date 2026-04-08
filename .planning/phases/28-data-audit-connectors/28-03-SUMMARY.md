---
phase: 28-data-audit-connectors
plan: 03
subsystem: connectors/price-adjustment
tags: [data, connectors, adjustment, DATA-03]
requires: [28-01]
provides: [adjust_ohlc, spot_check_adjust, phase28-price-adjustment-doc]
affects: [connectors/, scripts/, docs/audits/, tests/]
tech-stack:
  added: []
  patterns: [pure-function-helper, vectorized-pandas]
key-files:
  created:
    - connectors/adjust.py
    - scripts/spot_check_adjust.py
    - docs/audits/phase28-price-adjustment.md
  modified:
    - tests/test_adjust.py
decisions:
  - "adjusted_price = raw_price * totaladjustrate (D-05/D-06)"
  - "totalvol left unadjusted in v1 (D-05)"
  - "Helper raises ValueError on missing columns (fail loud)"
metrics:
  duration: ~3m
  completed: 2026-04-08
  tasks: 2
  tests_passed: 4
---

# Phase 28 Plan 03: Price Adjustment Helper Summary

Pure `adjust_ohlc(df)` helper computing `adj_{open,high,low,close} = raw * totaladjustrate`, backed by 4 unit tests, a live Postgres spot-check CLI, and a locked convention doc under `docs/audits/`.

## What Was Built

- **connectors/adjust.py** — `adjust_ohlc(df)` returns copy of df with `adj_open/adj_high/adj_low/adj_close` added. Raises `ValueError` if `totaladjustrate` or any raw OHLC column missing. Volume preserved unadjusted per D-05.
- **tests/test_adjust.py** — 4 tests: rate application on mixed-rate rows, raw+volume preservation, missing-column error, empty-df handling. All pass.
- **scripts/spot_check_adjust.py** — CLI (`TICKER START END`) pulling from `connectors.postgres.load_stock_eod`, applying `adjust_ohlc`, and printing 5-row windows around every rate-change boundary.
- **docs/audits/phase28-price-adjustment.md** — Locked convention, spot-check protocol, volume note.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | adjust_ohlc + unit tests | 5ab4f11 | connectors/adjust.py, tests/test_adjust.py |
| 2 | spot-check script + audit doc | 53f59f3 | scripts/spot_check_adjust.py, docs/audits/phase28-price-adjustment.md |

## Verification

- `uv run pytest tests/test_adjust.py -q` → **4 passed**
- `uv run python -c "import scripts.spot_check_adjust"` → OK
- All acceptance criteria met (helper exists, grep tokens present, tests pass, script importable, doc contains convention + NOT adjusted note).

## Deviations from Plan

None — plan executed exactly as written. Minor non-semantic adjustment in spot-check script: added `.reset_index(drop=True)` after `adjust_ohlc` and clamped window upper bound to `len(df)-1` to guarantee integer-indexed slicing works regardless of source ordering.

## Known Stubs

None.

## DATA-03 Closure

Helper exists, tested, documented, and spot-check available against live Postgres. DATA-03 closed.

## Self-Check: PASSED

- connectors/adjust.py: FOUND
- tests/test_adjust.py: FOUND (4 passing)
- scripts/spot_check_adjust.py: FOUND
- docs/audits/phase28-price-adjustment.md: FOUND
- Commit 5ab4f11: FOUND
- Commit 53f59f3: FOUND
