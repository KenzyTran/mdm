---
phase: 29-vn100-universe-canslim-scorer
plan: "04"
subsystem: strategies/canslim
tags: [canslim, sectors, wave-1]
requires: [strategies.canslim, schema_lock.json]
provides: [strategies.canslim.sectors.SectorRouter]
affects: [docs/rules_canslim.md, tests/canslim/test_sectors.py]
tech_stack:
  added: []
  patterns: [dataclass-router, substring-classification, fail-loud-validation]
key_files:
  created: []
  modified:
    - strategies/canslim/sectors.py
    - tests/canslim/test_sectors.py
    - docs/rules_canslim.md
decisions:
  - "Bank detected via substring match on 'ngân hàng'/'bank' against stock_list.nhom"
  - "ctck + insurance EXCLUDED from CANSLIM scoring (D-07) — bespoke IS schemas unsupported"
  - "from_postgres fails LOUD if sector column NULL for >50% of tickers (D-08)"
  - "Unknown ticker warns + defaults to 'other' (soft); stale schema fails hard"
metrics:
  duration_minutes: 3
  tasks_completed: 1
  files_modified: 3
  completed_at: "2026-04-09"
---

# Phase 29 Plan 04: Sector Routing Summary

**One-liner:** Implemented `SectorRouter` dataclass with bank/ctck/insurance/other classification via Vietnamese substring matching over `stock_list.nhom`, plus `from_postgres` classmethod that fails loud when the locked schema column goes stale — closes CANS-10 so plan 29-05 can branch C/A rules between `is_quarter_nonbank` (EPS) and `is_quarter_bank` (PPOP).

## What Was Built

### Task 1: SectorRouter (TDD)

**RED → GREEN → docs:**

- `strategies/canslim/sectors.py` — `SectorRouter` dataclass with:
  - `route(ticker) -> 'bank'|'ctck'|'insurance'|'other'` via case-insensitive substring match on `BANK_TOKENS` / `CTCK_TOKENS` / `INSURANCE_TOKENS`
  - `is_excluded(ticker)` returns True for ctck + insurance (D-07)
  - `from_postgres(pg_engine, sector_column)` classmethod — loads stock_list, raises `RuntimeError` if empty or if >50% of sector values are NULL (D-08 fail-loud)
  - Module-level constants `SECTOR_BANK` and `SECTOR_EXCLUDED` exported for downstream use
- `tests/canslim/test_sectors.py` — 9 tests:
  - smoke import, bank/ctck/insurance/other routing, unknown-ticker warn + default, `is_excluded` matrix, `from_postgres` happy path (monkeypatched `pd.read_sql`), `from_postgres` fail-loud on >50% NULLs
- `docs/rules_canslim.md` §2 — bucket table (label → downstream IS table → score branch), exclusion policy (D-07), fail-loud rule (D-08)
- Commit: `9f2939f`

## Verification

- `uv run pytest tests/canslim/test_sectors.py -x -q` → **9 passed in 0.05s**
- `grep -q "BANK_TOKENS" strategies/canslim/sectors.py` → found
- `grep -q "RuntimeError" strategies/canslim/sectors.py` → found (2 raises)
- `docs/rules_canslim.md` §2 no longer `_TBD_` — contains bucket table and D-06/07/08 references

## Key Decisions

1. **Substring matching over exact equality** — Vietnamese labels in `stock_list.nhom` are free text ("Ngân hàng TMCP", "CTCK", etc.); tokens match case-insensitive contains so subtle label variations don't break classification.
2. **Tiered failure model** — individual unknown tickers warn + default to `other` (soft, keeps backtests running on partial data); a stale schema column (>50% NULL) hard-fails so a corrupted universe can't silently reach the scorer.
3. **50% NULL threshold** — chosen to distinguish "a few missing labels" (tolerable) from "wrong column locked" (catastrophic). Matches D-08 intent without being too twitchy.
4. **`ctck` bucket name kept short** — matches the VN industry shorthand and keeps downstream branch code readable (`if bucket == 'ctck': skip`).

## Deviations from Plan

None — plan executed exactly as written. The plan's reference implementation shipped verbatim; the only additions were module-level `SECTOR_BANK` / `SECTOR_EXCLUDED` constants (listed in the plan's `must_haves.artifacts` requirement).

## Known Stubs

None introduced by this plan. The `SectorRouter` is fully functional; plan 29-05 will consume it via `SectorRouter.from_postgres(...)` in the fundamental rules module.

## Self-Check: PASSED

- strategies/canslim/sectors.py FOUND (SectorRouter, BANK_TOKENS, RuntimeError all present)
- tests/canslim/test_sectors.py FOUND (9 tests, all pass)
- docs/rules_canslim.md §2 FOUND (no longer _TBD_)
- Commit 9f2939f present in git log
