---
phase: 02-codebase-organization
plan: 01
subsystem: testing
tags: [pytest, regression, baselines, golden-files, csv]

# Dependency graph
requires:
  - phase: 01-data-foundation
    provides: validated data loaders and CSV data files
provides:
  - golden baseline CSVs for MDM signals, trades, VSA NAV, and VSA trades
  - regression test scaffolds importing from new strategy paths
  - pytest configuration with regression marker
affects: [02-codebase-organization, testing]

# Tech tracking
tech-stack:
  added: [pytest]
  patterns: [golden-file regression testing, fixture-based test data]

key-files:
  created:
    - tests/conftest.py
    - tests/fixtures/mdm_signals_baseline.csv
    - tests/fixtures/mdm_trades_baseline.csv
    - tests/fixtures/vsa_nav_baseline.csv
    - tests/fixtures/vsa_trades_baseline.csv
    - tests/test_mdm_regression.py
    - tests/test_vsa_regression.py
  modified:
    - pyproject.toml

key-decisions:
  - "Used pre-migration import paths to capture baselines before any file moves"
  - "VSA tests include skipif decorator for environments without VN30_STOCKS_PRICE.csv"

patterns-established:
  - "Golden-file regression: capture baseline output, compare post-migration output within tolerance"
  - "Test fixtures stored in tests/fixtures/ as CSV files"

requirements-completed: [ORG-04]

# Metrics
duration: 4min
completed: 2026-03-27
---

# Phase 02 Plan 01: Regression Baselines Summary

**Golden baseline CSVs captured from pre-migration MDM (109 signals, 79 trades) and VSA (2763 NAV rows, 195 trades) with regression test scaffolds importing from new strategy paths**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T13:33:03Z
- **Completed:** 2026-03-27T13:36:32Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Captured MDM golden baselines: 109 signal rows and 79 trade records from pre-migration code
- Captured VSA golden baselines: 2763 NAV history rows and 195 trade records from pre-migration code
- Created regression test scaffolds that import from new strategy paths (strategies.mdm_classic, strategies.vsa)
- Configured pytest with testpaths and regression marker in pyproject.toml

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate golden baselines and configure pytest** - `2ca133d` (feat)
2. **Task 2: Create regression test files for MDM and VSA** - `501fd9f` (feat)

## Files Created/Modified
- `pyproject.toml` - Added [tool.pytest.ini_options] with testpaths and regression marker
- `tests/conftest.py` - Shared test config with FIXTURES path constant and sys.path setup
- `tests/__init__.py` - Package marker for tests directory
- `tests/fixtures/mdm_signals_baseline.csv` - 109 MDM signal rows (date, close, state, action)
- `tests/fixtures/mdm_trades_baseline.csv` - 79 MDM trade records (type, date, price, signal_type, reason, pnl)
- `tests/fixtures/vsa_nav_baseline.csv` - 2763 VSA NAV history rows
- `tests/fixtures/vsa_trades_baseline.csv` - 195 VSA trade records (stock_code, buy/sell info, pnl, exit_reason)
- `tests/test_mdm_regression.py` - TestMDMRegression class with 3 tests (signal sequence, trade P&L, trade count)
- `tests/test_vsa_regression.py` - TestVSARegression class with 4 tests (NAV history, trade count, P&L, exit reasons)

## Decisions Made
- Used pre-migration import paths (models.*, vn30_vsa.*) to capture baselines before any file moves happen
- VSA regression tests include @pytest.mark.skipif for environments where VN30_STOCKS_PRICE.csv is absent
- Tests import from new paths (strategies.mdm_classic, strategies.vsa) so they will fail until Plan 02 migration completes

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all baselines contain real data from actual backtest runs.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Golden baselines locked in before any file moves
- Regression tests ready to validate post-migration output identity
- Plan 02 (directory restructure) and Plan 03 (import migration) can proceed

---
*Phase: 02-codebase-organization*
*Completed: 2026-03-27*
