# Codebase Concerns

**Analysis Date:** 2026-03-27

## Tech Debt

**Duplicate Code Across Two Strategy Implementations:**
- Issue: Nearly identical position management, configuration, and performance calculation logic exists in both MDM and VN30 VSA strategies
- Files:
  - MDM: `models/position_manager.py`, `models/config.py`, `models/performance.py`
  - VSA: `vn30_vsa/position_manager.py`, `vn30_vsa/config.py`, `vn30_vsa/performance.py`
- Impact: Changes to one strategy must be replicated to the other, increasing bug risk and maintenance burden. Future strategies would require another copy
- Fix approach: Extract common trading logic into a shared base module (e.g., `common/position_manager.py`, `common/config.py`) and have both strategies inherit or compose from it

**Inconsistent Data Column Naming Conventions:**
- Issue: CSV data loaders use different column names inconsistently
- Files:
  - `models/data_loader.py` uses: `open`, `close`, `high`, `low`, `volume`, `symbol`, `date`
  - `vn30_vsa/data_loader.py` uses: `openprice`, `closeprice`, `highestprice`, `lowestprice`, `totalvol`, `stockcode`, `tradingdate`
  - vnindex_price.csv has raw columns with ISO format dates: `openindex`, `closeindex`, `lowestindex`, `highestindex`, `totalvol`, `tradingdate` with quotes wrapped in quotes
- Impact: New strategies face ambiguity about which naming convention to use. Hard to write generic data processing code. Column mismatches cause runtime errors
- Fix approach: Standardize on a single set of canonical column names. Create unified data schema that both loaders normalize to. Add column name constants to shared config

**Magic Numbers Scattered Across Code:**
- Issue: Trading parameters (percentages, thresholds, window sizes) are hardcoded or duplicated rather than centralized
- Examples:
  - Stop loss: 2.5% in MDM `models/config.py`, 7% in VSA `vn30_vsa/config.py`
  - Kelly fraction: 0.5 (half Kelly) in `vn30_vsa/kelly.py` line 63, but also `KELLY_FRACTION = 1` in `vn30_vsa/config.py` line 17 (conflicting meanings)
  - Correction threshold: -0.10 (10%) in `models/config.py` but logic says -0.12 (12%) in comments
  - Distribution day window: 20 trading days defined in config but used inconsistently
- Impact: Hard to run parameter sweeps or A/B tests. Inconsistencies lead to unintended behavior differences
- Fix approach: Create a single `StrategyParameters` dataclass that holds all configurable values with clear documentation of units and meanings

**Hardcoded CSV File Paths:**
- Issue: File paths are hardcoded with defaults that may not exist on user systems
- Files:
  - `models/mdm_engine.py` line 54: defaults to `'vnindex_price.csv'`
  - `models/data_loader.py` line 25: same
  - `vn30_vsa/data_loader.py` line 23: defaults to `"VN30_STOCKS_PRICE.csv"`
- Impact: Backtest scripts fail silently or with cryptic file-not-found errors. Hard to run from different directories
- Fix approach: Use environment variables or config file for data paths. Provide clear error messages when files are missing. Support multiple search paths

## Known Bugs

**CSV Date Parsing Inconsistency:**
- Issue: vnindex_price.csv has dates wrapped in quotes with ISO format `"2024-08-09T00:00:00.000Z"` while other CSVs use simple dates. Data loader uses `pd.read_csv()` followed by `.str.strip('"')` which is fragile
- Files: `models/data_loader.py` lines 54-56
- Trigger: Loading vnindex_price.csv with inconsistent quote handling in the CSV
- Impact: Silent failures where dates are not parsed correctly, leading to incorrect filtering and analysis
- Workaround: Manually clean CSV files before loading. Always verify date column after load
- Fix approach: Use pandas CSV reader with proper quoting parameter, explicitly handle multiple date formats, validate date parsing results

**Distribution Day Count Window Bug (Potential):**
- Issue: `DistributionDayCounter.get_dd_count_in_window()` finds current date index using `.index(current_date)`, which is O(n) and fragile if dates are duplicated or missing
- Files: `models/distribution_day.py` lines 110-113
- Trigger: When running backtests across multiple years, if current_date doesn't exist in `all_dates` list or appears multiple times
- Impact: Incorrect DD count which affects trading signals. Hard to debug because ValueError is caught silently and returns 0
- Fix approach: Use pandas DatetimeIndex with `.get_loc()` or create a date-to-index mapping dictionary. Add assertions to verify list integrity

**Missing Value Handling in Indicator Calculations:**
- Issue: Several indicator calculations assume columns exist and are non-null without defensive checks
- Files: Multiple locations including:
  - `models/indicators.py` line 37: `(close - low) / (high - low)` doesn't check for NaN values
  - `models/mdm_engine.py` lines 167-176: Uses `.get()` with fallback to None but then checks if not None - could miss edge cases with NaN vs missing
- Impact: Inconsistent behavior when data has gaps. NaN propagates through calculations silently
- Fix approach: Add explicit NaN handling at data load time. Use `.fillna()` or `.dropna()` consistently. Add assertions at indicator calculation boundaries

**Price Location Clamping May Mask Bugs:**
- Issue: `Indicators.price_location()` clamps result to [0, 1] but this masks upstream problems where high < low or close > high
- Files: `models/indicators.py` lines 34-38
- Trigger: When using bad/corrupted price data where OHLC assumptions are violated
- Impact: Silent data quality issues. False positives in signal detection because p_loc values are forced into expected range
- Fix approach: Add validation that high >= low and open/close are within [low, high]. Log warnings for violations. Consider rejecting bad bars

**MA50 Breakout Check Potentially Fires Multiple Times (State Machine Issue):**
- Issue: In MDM engine, when price crosses above MA50 in CASH state, both `is_ftd` and `is_ma50_breakout` are set to True and buy signal fires. But if MA50 still holds price up the next day, no re-entry protection exists
- Files: `models/mdm_engine.py` lines 166-177, `models/position_manager.py` lines 322-326
- Trigger: Stock bounces off MA50 multiple times in succession, or indicator lag causes multiple "breakout" signals
- Impact: Could enter position multiple times on same signal sequence
- Fix approach: Add "signal already processed" flag that persists across days. Track last signal date to prevent re-entry within N days

## Security Considerations

**No Input Validation on Configuration Objects:**
- Issue: `MDMConfig` and strategy configs accept any values without bounds checking
- Files: `models/config.py`, `vn30_vsa/config.py`
- Current mitigation: Weak - only `__post_init__` assertions in MDMConfig for sign checking
- Recommendation:
  - Add range validation (e.g., stop_loss_pct must be between 0.01 and 0.50)
  - Add type hints and validate types at init
  - Create factory methods with safe defaults rather than accepting raw floats

**Environment Variables Not Validated:**
- Issue: `.env` file present but no code validates loaded values
- Files: Project uses `python-dotenv>=1.2.1` but no observable loading of env vars in main code
- Current mitigation: None
- Recommendation:
  - Document required environment variables
  - Add startup validation that fails fast if required vars missing
  - Use type-safe config loader (e.g., pydantic)

## Performance Bottlenecks

**O(n) DataFrame Iteration in MDM Engine Main Loop:**
- Problem: `MDMEngine.run()` iterates through each row with index access, calling `.shift()` operations repeatedly
- Files: `models/mdm_engine.py` lines 115-283
- Cause: Pandas `.iloc[idx]` access in loop rather than vectorized operations. Many `.shift(1)` calls recalculate rolling values
- Current capacity: Works fine for ~2,500 trading days (10 years of daily data). For intraday data or larger datasets, becomes slow
- Improvement path:
  - Pre-compute all shifted columns once at the start: `df['prev_close'] = df['close'].shift(1)` instead of accessing row-by-row
  - Use `.iterrows()` only for state machine logic that cannot be vectorized
  - Consider numpy-based calculations for bottleneck loops

**Expensive Distribution Day Window Lookup:**
- Problem: `get_dd_count_in_window()` iterates through entire DD history and checks membership in a set for every bar (O(n * m) where m = num DD)
- Files: `models/distribution_day.py` lines 98-121
- Current capacity: Works for typical ~50-100 DD per 2,500 bars. For high-frequency strategies, becomes bottleneck
- Improvement path:
  - Pre-compute DD counts during backtest run-through instead of calculating on-demand
  - Use cumsum() operation to track rolling counts
  - Cache window DD counts between iterations

**VSA Engine Multiple DataFrame Lookups Per Bar:**
- Problem: `VSAEngine.process_exits()` and similar methods call `get_stock_row()` which does a mask lookup for every position for every day
- Files: `vn30_vsa/vsa_engine.py` lines 110-150
- Cause: Dictionary of DataFrames with mask-based lookups instead of index-based or pre-sorted structures
- Improvement path:
  - Set tradingdate as DataFrame index for O(1) lookup
  - Pre-sort position list and data structures for sequential access
  - Cache current date's data to avoid repeated lookups

## Fragile Areas

**Rally Attempt Tracker State Machine (Fragile):**
- Files: `models/rally_attempt.py`
- Why fragile:
  - Multiple state variables (`in_correction`, `day1_info`, `peak_high`) can become out of sync
  - Reset logic is split across `reset()` and `full_reset()` with unclear semantics
  - Peak update logic resets rally count (line 59) but only if new high - could miss state transitions
  - Comment on line 44 says "Note: Keep in_correction and peak_high" but it's not obvious why
- Safe modification: Add comprehensive state validation function. Document state machine with state diagram. Write unit tests for all transition sequences before modifying
- Test coverage: No existing unit tests for state transitions. Risk of breaking with small changes

**Stop Loss Logic Spread Across Multiple Files:**
- Files:
  - `models/stop_loss.py`: Defines rules for long positions
  - `models/position_manager.py` lines 256-276: Separate logic for short positions with different thresholds
  - Inconsistent between MDM and VSA implementations
- Why fragile: Three different implementations of similar concept. Easy to miss edge case in one. Hard to update rule consistently
- Safe modification: Create abstract StopLossStrategy class. Implement MDM and VSA variants. Test all stop loss types with same test suite
- Test coverage: Only basic assertions in config, no tests for stop loss triggering with edge cases (gap downs, gaps ups, limit moves)

**52-Week Breakout with Special Stop Loss (Untested Path):**
- Files: `models/stop_loss.py` lines 73-89, `models/ftd_signal.py` lines 143-176
- Why fragile: 52-week breakout is relatively new signal type (compared to FTD). Stop loss for 52-week is 1% from buy day low (special rule), different from other signals' 2.5%. Only triggered through this specific path
- Safe modification: Test 52-week breakout entries thoroughly. Verify stop loss calculation matches user requirements. Consider whether 1% stop is intentional or a typo
- Test coverage: No tests found for 52-week signals. Untested code path

**Distribution Day Type Detection Logic:**
- Files: `models/distribution_day.py` lines 30-67
- Why fragile: Type 2 (stalling) DD has three conditions (price_stall AND volume_up AND low_close). Change to any threshold could flip classification of borderline bars
- Safe modification: Add logging to track which bars are Type 1 vs Type 2. Run analysis to understand distribution of types before changing thresholds
- Test coverage: Only check_distribution_day() public method tested implicitly. No unit tests for is_distribution_day_type1/type2()

## Scaling Limits

**Single-Strategy Limitation:**
- Current capacity: MDM strategy runs on single VNINDEX time series with ~2,500 bars
- Limit: Adding second strategy (VSA) required complete code duplication. Each new strategy adds 300+ lines of unique code
- Scaling path:
  1. Extract base strategy class with common backtest loop structure
  2. Create plugin architecture for signal detectors
  3. Support multiple securities in single backtest (currently only index-by-index)

**Memory Usage with Large Stock Universe:**
- Current capacity: VSA loads ~30 VN30 stocks fine (~50MB)
- Limit: Loading all 3,000+ stocks on HNX would require 5GB+ RAM with current data structure (dict of DataFrames)
- Scaling path:
  - Use HDF5 or parquet format for data storage
  - Implement lazy loading where only active positions' data is in memory
  - Consider time-series database (InfluxDB, TimescaleDB) for larger datasets

**Backtest Speed:**
- Current capacity: Full 10-year backtest of MDM runs in ~2-3 seconds (estimated from code complexity)
- Limit: Parameter optimization (sweeping 100 parameter combinations) would take 3+ minutes per strategy
- Scaling path:
  - Profile to identify slow loops, use numba JIT compilation for hot paths
  - Parallelize across parameter combinations
  - Cache intermediate indicator calculations across parameter runs

## Dependencies at Risk

**No Package Pinning in pyproject.toml:**
- Risk: Dependencies use loose version constraints (`pandas>=2.0.0`, `numpy>=1.24.0`)
- Impact: Breaking API changes in minor versions could break backtest without warning
- Migration plan:
  1. Test with latest versions of all dependencies
  2. Pin exact versions in pyproject.toml (e.g., `pandas==2.2.0`)
  3. Use uv.lock (already present) consistently
  4. Set up CI to test with minimum and latest dependency versions

**Jupyter Notebook Dependencies in Production Code:**
- Risk: `jupyter>=1.0.0` in dependencies but code lives in .ipynb files (mdm_backtest.ipynb, vn30_vsa_backtest.ipynb) which are not version controlled properly
- Impact: Notebooks can diverge from Python modules. Hard to reproduce results. Hard to integrate into CI/CD
- Migration plan:
  - Convert notebooks to Python scripts in `scripts/` directory
  - Keep notebooks for interactive exploration only (git-ignore them)
  - Make all reproducible analysis use Python scripts

**Pandas Low-Level API Usage:**
- Risk: Code uses `.shift()`, `.iloc[]`, `.at[]` which can have subtle breaking changes between versions
- Impact: Small pandas version bump could cause silent numerical differences in indicators
- Migration plan:
  - Use higher-level pandas API (`.reset_index()`, `assign()` instead of direct assignment)
  - Create utility functions that abstract data frame operations
  - Add integration tests that verify results are stable across pandas versions

## Missing Critical Features

**No Data Validation Pipeline:**
- Problem: Data is loaded but not validated for obvious issues (negative prices, volume = 0, gaps, etc.)
- Blocks: Can't confidently run backtest on new data source without manual inspection
- Impact: Silent failures with bad data produce misleading backtests. User doesn't know if poor results are due to strategy or bad data

**No Parameter Sensitivity Analysis:**
- Problem: No built-in way to test how sensitive results are to parameter changes
- Blocks: Can't answer "is 2.5% stop loss optimal or would 2.0% be better?"
- Impact: Published backtest results may not be robust. Parameters may be overfit to historical data

**No Walk-Forward Out-of-Sample Testing:**
- Problem: All backtests are in-sample only
- Blocks: Can't assess whether strategy will work on future unseen data
- Impact: Overfitting risk. Excellent backtest results may not translate to live trading

**No Integration with Live Market Data:**
- Problem: All data must be pre-loaded from CSV files
- Blocks: Can't run strategy in semi-live mode (backtest on history, live signals on current prices)
- Impact: Can't validate strategy performance in real-time before full deployment

## Test Coverage Gaps

**No Unit Tests Exist:**
- What's not tested:
  - Individual indicator calculations (price_location, moving averages)
  - Signal detection logic (FTD rules, MA50 breakout rules, 52-week breakout)
  - State machine transitions (all MarketState transitions)
  - Distribution day counting and windowing
  - Position manager entry/exit logic
  - Stop loss calculations with edge cases
- Files affected: All `models/*.py` files have zero unit tests
- Risk: Regressions go undetected. Small refactors could break multiple features
- Priority: HIGH - should write tests for signal detection first (most critical path)

**Integration Tests Limited to Notebooks:**
- What's tested: Only full end-to-end backtests in Jupyter notebooks (`mdm_backtest.ipynb`, `vn30_vsa_backtest.ipynb`)
- What's missing:
  - Tests with different data ranges
  - Tests with edge case data (gap ups, limit moves, low volume days)
  - Tests for state machine robustness
  - Regression tests comparing old vs new code
- Risk: Changes to core modules may produce different results without detection
- Priority: MEDIUM - set up pytest framework and migrate key tests from notebooks

**No Performance/Benchmark Tests:**
- What's not tested:
  - Backtest execution time
  - Memory usage with large stock universes
  - Numerical stability (are results bit-identical across runs?)
- Risk: Performance degradation goes unnoticed until user complains
- Priority: LOW - can be added after unit/integration test foundation exists

**No Data Quality Tests:**
- What's not tested:
  - Handling of missing data points
  - Handling of NaN values in indicators
  - Behavior with extreme price movements
  - CSV parsing with different quote styles and date formats
- Risk: Bad data silently corrupts analysis
- Priority: MEDIUM - data quality tests should run before any backtest

---

*Concerns audit: 2026-03-27*
