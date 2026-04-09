---
phase: 29-vn100-universe-canslim-scorer
plan: "01"
subsystem: strategies/canslim
tags: [scaffold, schema-lock, canslim, wave-0]
requires: [connectors.postgres, connectors.mysql]
provides: [strategies.canslim, schema_lock.json]
affects: [docs/rules_canslim.md, tests/canslim]
tech_stack:
  added: []
  patterns: [dataclass-config, stub-then-fill, schema-introspection]
key_files:
  created:
    - strategies/canslim/__init__.py
    - strategies/canslim/config.py
    - strategies/canslim/universe.py
    - strategies/canslim/sectors.py
    - strategies/canslim/scorer.py
    - strategies/canslim/baseline.py
    - strategies/canslim/rules/__init__.py
    - strategies/canslim/rules/fundamental.py
    - strategies/canslim/rules/technical.py
    - strategies/canslim/rules/rs.py
    - strategies/canslim/rules/flow.py
    - strategies/canslim/rules/liquidity.py
    - tests/canslim/__init__.py
    - tests/canslim/conftest.py
    - tests/canslim/test_config.py
    - tests/canslim/test_universe.py
    - tests/canslim/test_sectors.py
    - tests/canslim/test_rules_fundamental.py
    - tests/canslim/test_rules_technical.py
    - tests/canslim/test_rules_rs.py
    - tests/canslim/test_rules_flow.py
    - tests/canslim/test_rules_liquidity.py
    - tests/canslim/test_scorer.py
    - scripts/introspect_canslim_schema.py
    - .planning/phases/29-vn100-universe-canslim-scorer/schema_lock.json
    - docs/rules_canslim.md
    - docs/audits/phase29/.gitkeep
  modified: []
decisions:
  - "stock_list.nhom is the locked sector column (3 candidates found, 'nhom' chosen)"
  - "is_quarter_bank PPOP and publish_date columns flagged AMBIGUOUS — plans 29-04/05 must resolve before implementing fundamental rules"
metrics:
  duration_minutes: 8
  tasks_completed: 3
  files_created: 27
  completed_at: "2026-04-09"
---

# Phase 29 Plan 01: Wave 0 Scaffold Summary

**One-liner:** Created complete strategies/canslim package skeleton (12 stub modules + 11 test files = 25 collected tests), live-DB schema introspection script that locks Postgres+MySQL column names into schema_lock.json, and docs/rules_canslim.md stub — unblocks plans 29-02..29-09.

## What Was Built

### Task 1: strategies/canslim package + tests
- `CanslimConfig` dataclass with D-12 defaults (c_threshold=0.20, l_rs_threshold=80.0, etc.)
- `CanslimScorer` class with constructor accepting config + pg/mysql engines; `score()` raises NotImplementedError
- 5 rule modules (fundamental, technical, rs, flow, liquidity) with one stub function per requirement (CANS-01..CANS-11)
- universe.py, sectors.py, baseline.py stubs for plans 29-03, 29-04, 29-09
- tests/canslim/conftest.py with fake_ohlcv, fake_eps, fake_stock_list, canslim_config fixtures
- 25 collected tests (11 smoke + 14 skipped placeholders) — all pass collection
- Commit: `d00534f`

### Task 2: schema introspection script
- `scripts/introspect_canslim_schema.py` CLI using `connectors.postgres.get_engine` and `connectors.mysql.get_engine`
- Probes Postgres tables: stock_list, stock_eod, stock_foreign_eod, index_eod, stock_rs
- Probes MySQL tables: is_quarter_nonbank/bank/insurance/stock, ratios_stock, rank_top_stocks
- Pattern-matches sector / EPS / PPOP / publish_date columns; emits structured JSON
- Ran live → wrote `.planning/phases/29-vn100-universe-canslim-scorer/schema_lock.json` (1660+ lines of column metadata)
- **Locked:**
  - `stock_list_sector_column = "nhom"` (3 candidates, picked first)
  - `is_quarter_nonbank_eps_column = "loi_nhuan_gop"` (8 candidates flagged in notes)
- **Ambiguous (flagged for plans 29-04/05):**
  - `is_quarter_bank_ppop_column` — no PPOP-like column found
  - `publish_date_column` — no publish/period/ngay column found
- Commit: `e3ad77c`

### Task 3: docs stub
- `docs/rules_canslim.md` — 8-section stub with Code-Docs Sync rule banner
- `docs/audits/phase29/.gitkeep` — empty dir for plan 29-09's validation report
- Commit: `99b2009`

## Verification

- `uv run python -c "import strategies.canslim"` → exit 0
- `uv run pytest tests/canslim --collect-only -q` → 25 tests collected across 11 files
- `CanslimConfig().c_threshold == 0.20` → True
- `schema_lock.json` exists with keys postgres, mysql, locked, notes
- `docs/rules_canslim.md` contains 8 `## ` headings and "Code-Docs Sync Rule" string

## Key Decisions

1. **stock_list.nhom over stock_list.nganh** — both columns exist; picked `nhom` as first match. Plan 29-04 should verify this is the correct one for sector routing or switch to `nganh`.
2. **EPS column = `loi_nhuan_gop`** — first pattern match. This is "gross profit" in Vietnamese, not net EPS — plan 29-05 likely needs to switch to `loi_nhuan_sau_thue_cua_co_dong_cua_cong_ty_me` (net profit attributable to parent shareholders). Listed in notes for resolution.
3. **No PPOP column in is_quarter_bank** — plan 29-05 will need either to use `loi_nhuan_truoc_thue` proxy or extend introspection.
4. **Stubs raise NotImplementedError** — keeps imports clean while making "not implemented yet" obvious at runtime.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added sys.path insertion to introspection script**
- **Found during:** Task 2 verification
- **Issue:** Running `uv run python scripts/introspect_canslim_schema.py` failed with `ModuleNotFoundError: connectors` because scripts/ is not auto-added to sys.path
- **Fix:** Added `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))` matching pattern from `scripts/export_dashboard_data.py`
- **Files modified:** scripts/introspect_canslim_schema.py
- **Commit:** included in `e3ad77c`

## Known Stubs

All strategies/canslim/ modules contain `NotImplementedError` stubs by design — this is a Wave 0 scaffold. Each stub references its filling plan (29-02..29-09). No stubs flow to UI or block runtime usage outside of test collection.

## Self-Check: PASSED

- strategies/canslim/__init__.py FOUND
- scripts/introspect_canslim_schema.py FOUND
- .planning/phases/29-vn100-universe-canslim-scorer/schema_lock.json FOUND
- docs/rules_canslim.md FOUND
- docs/audits/phase29/.gitkeep FOUND
- Commits d00534f, e3ad77c, 99b2009 all present in git log
