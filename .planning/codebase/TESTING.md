# Testing Patterns

**Analysis Date:** 2026-03-27

## Test Framework

**Runner:**
- No test framework detected in project
- No pytest, unittest, or vitest configuration found
- `pyproject.toml` lists no dev dependencies for testing

**Assertion Library:**
- None configured - Python assert statements used in limited cases for validation

**Run Commands:**
- No testing infrastructure configured
- Manual testing appears to be done via Jupyter notebooks: `mdm_backtest.ipynb`, `vn30_vsa_backtest.ipynb`
- Backtest scripts: `run_backtest.py` executes end-to-end validation

## Test File Organization

**Location:**
- No dedicated test directory exists (`tests/`, `test/`)
- Testing done through Jupyter notebooks co-located with code

**Naming:**
- Notebooks named with `_backtest` suffix: `mdm_backtest.ipynb`, `sp500_backtest.ipynb`, `vn30_vsa_backtest.ipynb`
- Analysis/diagnostic scripts: `analyze_drawdown.py`, `analyze_vsa_drawdown.py`, `check_date.py`, `diagnose_vn30.py`

**Structure:**
- Backtest notebooks contain:
  - Data loading
  - Strategy engine execution
  - Performance metrics calculation
  - Result visualization
  - Trade analysis

## Test Structure

**Manual Testing Approach:**
- End-to-end backtests validate entire strategy pipeline
- Example backtest flow from notebooks:
  1. Load historical data via `DataLoader`
  2. Initialize engine (`MDMEngine`, `VSAEngine`)
  3. Run strategy with `engine.run(df)`
  4. Analyze trades via `PerformanceAnalyzer`
  5. Generate reports and visualizations

**Patterns:**
- Data preparation: Load CSV, filter dates, ensure numeric columns
- Engine execution: Reset state, process data row-by-row, track state changes
- Results validation: Check trade counts, P&L, win rates
- Performance comparison: Compare strategy P&L vs buy-and-hold baseline

## Mocking

**Framework:** None - minimal external dependencies

**Patterns:**
- No mocking framework detected (no unittest.mock usage)
- Direct DataFrame manipulation for test data
- CSV files used as test data source

**What to Mock:**
- File I/O would be mock candidates if unit tests existed
- External API calls would require mocking (currently using static CSV files)

**What NOT to Mock:**
- DataFrame operations - test with real pandas operations
- Indicator calculations - verify with actual mathematical operations
- State transitions - test actual state machine behavior

## Fixtures and Factories

**Test Data:**
- Historical CSV files serve as fixtures:
  - `vnindex_price.csv`: VNINDEX historical data
  - `vn30_price.csv`: VN30 component prices
- Configuration objects used across tests:
  ```python
  from models.config import MDMConfig
  config = MDMConfig()  # Uses defaults
  ```

**Location:**
- Test data files: `/c/Users/trant/projects/mdm/data/` directory and root directory
- Configuration: `models/config.py`, `vn30_vsa/config.py` provide preset configurations

## Coverage

**Requirements:** No coverage requirements enforced

**View Coverage:**
- No coverage tooling configured
- Manual inspection of trade results provides implicit coverage
- Notebooks show all executed code paths

## Test Types

**Unit Tests:**
- Not formally implemented
- Implicit unit testing via individual method validation in notebooks
- State machine transitions tested through backtest execution

**Integration Tests:**
- Backtests function as integration tests
- Complete pipeline tested: data load → indicators → signals → position management → performance
- `run_backtest.py` provides scripted integration test:
  ```python
  loader = DataLoader('vnindex_price.csv')
  df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
  engine = MDMEngine()
  results = engine.run(df)
  analyzer = PerformanceAnalyzer(results, trades)
  analyzer.print_report()
  ```

**E2E Tests:**
- Jupyter notebooks serve as E2E test and development environment
- Full backtest pipeline validation in `mdm_backtest.ipynb`, `vn30_vsa_backtest.ipynb`
- Alternative VSA strategy tested separately in `analyze_vsa_drawdown.py`

## Common Patterns

**Data Validation:**
- Check for NaN values after loading: `df.dropna(subset=numeric_cols)`
- Ensure numeric types: `pd.to_numeric(df[col], errors='coerce')`
- Date parsing with error handling:
  ```python
  df['date'] = pd.to_datetime(df['date'], format='mixed')
  df['date'] = df['date'].dt.normalize()
  ```

**State Assertion:**
- Implicit assertions through expected state transitions:
  ```python
  current_state = self.position_manager.get_state()
  if current_state == MarketState.CASH:
      # Process cash state logic
  ```

**Result Validation:**
- Trade results checked via summary statistics:
  ```python
  summary = engine.summary()
  # Checks: total_wins, win_rate, total_pnl, etc.
  ```

## Testing Gaps

**Untested Areas:**
- Unit tests for individual indicator calculations (implicit testing via backtest)
- Edge cases in date/numeric handling (no parametrized test cases)
- Error conditions (minimal error handling means few edge cases tested)
- Configuration parameter variations (manual testing of config values)

## Custom Test Helpers

**Analysis Scripts:**
- `analyze_drawdown.py`: Analyzes maximum drawdown scenarios
- `analyze_vsa_drawdown.py`: VSA-specific drawdown analysis
- `check_date.py`: Date range validation
- `diagnose_vn30.py`: VN30 data diagnostics

**Performance Analyzer:**
- `models/performance.py` and `vn30_vsa/performance.py` provide performance metrics
- Methods calculate key metrics: return, Sharpe ratio, max drawdown, win rate
- Used to validate strategy performance in notebooks

---

*Testing analysis: 2026-03-27*
