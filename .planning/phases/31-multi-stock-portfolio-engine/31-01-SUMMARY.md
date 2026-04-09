---
phase: 31-multi-stock-portfolio-engine
plan: 01
subsystem: strategies/portfolio
tags: [wave-0, scaffold, config, state, rs-reader]
requires: []
provides:
  - strategies.portfolio.config.PortfolioConfig
  - strategies.portfolio.state.PositionBook
  - strategies.portfolio.state.SlotState
  - strategies.portfolio.state.CooldownRegistry
  - strategies.portfolio.state.Position
  - strategies.portfolio.state.Trade
  - connectors.postgres.load_stock_rs
  - tests.strategies.portfolio.fixtures.synthetic_panel.make_panel
affects: [connectors/postgres.py]
tech_added: []
patterns: [fail-loud-dataclass, schema-spike-first, fixture-hook-lock-days]
key_files_created:
  - strategies/portfolio/__init__.py
  - strategies/portfolio/config.py
  - strategies/portfolio/state.py
  - tests/strategies/portfolio/__init__.py
  - tests/strategies/portfolio/conftest.py
  - tests/strategies/portfolio/test_config.py
  - tests/strategies/portfolio/test_rs_reader.py
  - tests/strategies/portfolio/fixtures/__init__.py
  - tests/strategies/portfolio/fixtures/synthetic_panel.py
key_files_modified:
  - connectors/postgres.py
decisions:
  - "rs_value canonicalized to stock_rs.rss (short-term RS 1..99) — rsm/rsl deferred to later plans if needed"
  - "stockcode is CHAR space-padded in stock_rs; reader applies TRIM() on both projection and filter"
  - "SlotState.open_positions typed as plain list (not list[Position]) to avoid circular import noise — runtime contents are Position instances"
metrics:
  duration_seconds: 179
  tasks_completed: 3
  files_changed: 10
  tests_passing: 9
completed: "2026-04-09"
requirements: [GATE-01, PORT-01, PORT-06, PORT-10]
---

# Phase 31 Plan 01: Wave-0 Scaffold Summary

Bootstrapped the Phase 31 portfolio package with `PortfolioConfig` (fail-loud dataclass), the state primitives (`PositionBook`, `SlotState`, `CooldownRegistry`, `Position`, `Trade`), the `load_stock_rs` postgres reader (validated against 222k+ historical rows), and the synthetic OHLCV panel fixture with VN-style ceiling/floor hooks that every downstream Wave plan depends on.

## One-liner

Wave-0 scaffold: fail-loud PortfolioConfig + state dataclasses + stock_rs reader (rss column, TRIM'd codes) + synthetic ceiling/floor panel fixture — 9 tests green.

## Tasks

| # | Task | Commit | Tests |
|---|------|--------|-------|
| 1 | PortfolioConfig dataclass + validation tests | `c002405` | 5 passing |
| 2 | State dataclasses + synthetic panel fixtures | `ac27574` | 2 passing (7 total) |
| 3 | load_stock_rs reader + historical validation | `7ef70e1` | 2 passing (9 total) |

## Key Files

**Created:**
- `strategies/portfolio/config.py` — `PortfolioConfig` with all Phase 31 defaults (max_slots=8, slot_weight=0.125, t_plus=2, cost model, ceiling/floor/adv_mult); 14 fail-loud validations in `__post_init__`.
- `strategies/portfolio/state.py` — `Position`, `Trade`, `SlotState`, `CooldownRegistry` (D-21 cooldown clock: earliest re-entry = exit + cooldown_days + 1), `PositionBook` container.
- `tests/strategies/portfolio/fixtures/synthetic_panel.py` — `make_panel()` generating deterministic 3-ticker × 60-bar long-form OHLCV with VN ceiling/floor columns (prev_close × 1.07/0.93) and `lock_days={ticker:[(bar_idx,"ceiling"|"floor")]}` hook for forcing limit-lock bars.
- `tests/strategies/portfolio/conftest.py` — `synthetic_panel` and `config` fixtures.
- `tests/strategies/portfolio/test_config.py` — 5 config validation tests + 2 state smoke tests.
- `tests/strategies/portfolio/test_rs_reader.py` — 2 integration tests against live postgres (schema + ticker filter).

**Modified:**
- `connectors/postgres.py` — appended `load_stock_rs(start, end, tickers=None)`; schema spike comment documents `stock_rs` columns; returns canonical `["date","ticker","rs_value"]`; fail-loud on empty unfiltered frame.

## Schema Spike Findings

`stock_rs` columns (live postgres, verified):

| column | type | notes |
|--------|------|-------|
| stockcode | CHAR | space-padded — TRIM required |
| tradingdate | DATE | |
| rss | NUMERIC | short-term RS, 1..99 — canonicalized as `rs_value` |
| rsm | NUMERIC | mid-term RS (unused in plan 01) |
| rsl | NUMERIC | long-term RS (unused in plan 01) |
| rs1xx | NUMERIC | unused |
| rs2xx | NUMERIC | unused |

Range check: `2023-01-01..2023-06-30` returns 222,245 rows, rss ∈ [1, 99]; VNM has 121 rows in that range. CONTEXT Open Question 1 resolved.

## Deviations from Plan

None of Rules 1-4 triggered. Plan executed as written.

One minor clarification worth noting: the plan specified fields on `PortfolioConfig` without an exhaustive type table. I chose:
- `rs_threshold: float` (not int) because the raw `rss` column is NUMERIC and can be fractional.
- `adv_mult: float` and `ma50_vol_mult: float` for the same reason (multiplier arithmetic).
- `SlotState.open_positions` typed as a plain `list` to sidestep forward-reference gymnastics; runtime contents are `Position` instances and downstream iteration code is unchanged.

## Verification

```
uv run pytest tests/strategies/portfolio/ -x -q
9 passed in 6.93s
```

Acceptance criteria per plan:
- `class PortfolioConfig` present — yes
- `entry_mode` field present — yes
- `raise ValueError` count in `config.py`: 14 (plan required ≥4)
- `class PositionBook`, `earliest_sell_bar`, `class CooldownRegistry` — all present in `state.py`
- `def make_panel`, `ceiling` — present in fixture
- `def load_stock_rs`, `stock_rs`, `rs_value` — all present
- Full suite green: 9 passed, 0 errors, 0 skipped (live postgres available)

## Self-Check: PASSED

Files verified present:
- strategies/portfolio/config.py — FOUND
- strategies/portfolio/state.py — FOUND
- connectors/postgres.py::load_stock_rs — FOUND
- tests/strategies/portfolio/test_config.py — FOUND
- tests/strategies/portfolio/test_rs_reader.py — FOUND
- tests/strategies/portfolio/fixtures/synthetic_panel.py — FOUND

Commits verified in git log:
- c002405 — FOUND
- ac27574 — FOUND
- 7ef70e1 — FOUND
