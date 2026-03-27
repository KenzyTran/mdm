<!-- GSD:project-start source:PROJECT.md -->
## Project

**MDM Reverse-Engineering & VN30 Market Timing**

A research and trading system project to reverse-engineer Dr. K's post-2019 Market Direction Model (MDM) by analyzing public signal history against NASDAQ/S&P500 price data, then adapt and apply the discovered rules to Vietnam's VN30 index. The project also maintains a separate VSA (Volume Spread Analysis) strategy as an independent trading system.

**Core Value:** Accurately reverse-engineer the post-2019 MDM logic so that backtested signals match Dr. K's published signal history — this is the foundation everything else depends on.

### Constraints

- **Data**: US market data prices appear to be scaled by ~1000x — must normalize before analysis
- **Validation**: Can only validate against publicly delayed signals (up to 2 months delay for non-members)
- **VN30 adaptation**: Vietnamese market has different microstructure (T+2.5 settlement, 7% price limit, derivative expiry effects)
- **Scope**: The reverse-engineered model will be an approximation — exact replication is unlikely without proprietary knowledge
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.10+ - Core trading strategy implementation, data processing, backtesting
## Runtime
- Python 3.10 or higher (specified in `pyproject.toml`)
- uv - Modern Python package manager (configured in `pyproject.toml`)
- Lockfile: Not present (configured via `pyproject.toml`)
## Frameworks & Libraries
- pandas >= 2.0.0 - Time series data manipulation, OHLCV processing
- numpy >= 1.24.0 - Numerical computations for indicators and backtesting calculations
- matplotlib >= 3.7.0 - Chart generation for performance analysis and market visualization
- jupyter >= 1.0.0 - Interactive analysis and experimentation environment
- requests >= 2.32.5 - For potential API integrations (currently not actively used for live data)
- python-dotenv >= 1.2.1 - Environment variable loading from `.env` file
## Core System Architecture
- Modular engine-based architecture
- Two distinct trading strategy implementations:
- `MDMEngine` (`models/mdm_engine.py`) - Orchestrates MDM strategy execution
- `VSAEngine` (`vn30_vsa/vsa_engine.py`) - Orchestrates VSA strategy execution
## Key Dependencies by Purpose
- pandas - Required for all data handling and time series operations
- numpy - Required for mathematical calculations on trading signals
- python-dotenv - Environment configuration for file paths and parameters
- matplotlib - Backtesting analysis and result visualization
- jupyter - Research and analysis notebooks
- requests - Available for future API integration (installed but not currently imported in strategy code)
## Configuration
- `.env` file present (location: `/c/Users/trant/projects/mdm/.env`)
- No secrets visible in configuration
- File paths and parameters managed via:
- Configuration file: `pyproject.toml`
- Tool: `[tool.uv]` section for package manager configuration
- Dev dependencies: None explicitly configured
## Data Sources
- CSV files (OHLCV format)
- Files used:
- MDM loader maps: `stockcode`, `tradingdate`, `openindex`, `closeindex`, `lowestindex`, `highestindex`, `totalvol`
- VSA loader expects: `stockcode`, `tradingdate`, `openprice`, `closeprice`, `highestprice`, `lowestprice`, `totalvol`
## Database & Storage
- File-based storage only (no database)
- Data source: Local CSV files
- Output: CSV files and text reports
- Results exported to:
## Platform Requirements
- OS: Windows (environment shows Windows 11)
- Python 3.10+
- No compiled dependencies required (pure Python)
- Deployment target: Command-line execution environment
- Data files must be available locally (relative paths configured in loaders)
- No server/API deployment required currently
## Performance & Computational Requirements
- All calculations done in-memory via pandas DataFrames
- No streaming or distributed processing
- Suitable for historical backtesting (not real-time)
- Scales with data file size
- Typical usage: ~100K to 1M+ rows of OHLCV data
## Versioning & Compatibility
- Minimum: Python 3.10 (due to `requires-python = ">=3.10"`)
- Type hints and modern Python syntax assumed
- pandas >= 2.0.0 (requires Python 3.9+)
- numpy >= 1.24.0 (requires Python 3.10+)
- matplotlib >= 3.7.0 (compatible with Python 3.10+)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Lowercase with underscores: `data_loader.py`, `ftd_signal.py`, `position_manager.py`
- Module purpose reflected in name (e.g., `mdm_engine.py` for main engine, `indicators.py` for calculations)
- Configuration files: `config.py`
- snake_case: `check_distribution_day()`, `add_price_location_column()`, `calculate_rolling_kelly()`
- Methods prefixed with `get_`, `set_`, `check_`, `calculate_` to indicate action
- Private methods prefixed with `_` (rarely used)
- snake_case for all local and module-level variables: `rally_day`, `price_change_pct`, `dd_count`
- Short abbreviations used for domain concepts: `ma50` (50-day moving average), `p_loc` (price location), `dd` (distribution day), `ftd` (follow-through day)
- Boolean flags prefixed with `is_`, `has_`, `should_`: `is_ftd`, `is_dd`, `volume_up`, `stop_loss_triggered`
- Dataframe columns use consistent naming: `date`, `close`, `high`, `low`, `volume`, `open`, `symbol`
- PascalCase for classes: `DataLoader`, `Indicators`, `MDMEngine`, `PositionManager`, `FTDSignalDetector`
- Enum values in UPPERCASE: `MarketState.CASH`, `MarketState.HOLDING`
- Dataclass names in PascalCase: `Position`, `Trade`, `FTDSignal`, `MDMConfig`
## Code Style
- No explicit formatter configured (no `.prettierrc` or `black.toml`)
- 4-space indentation (standard Python)
- Line lengths appear to follow 120-char limit based on observed code
- Single blank line between methods, double blank line between classes
- No linting configuration found (no `.pylintrc` or `.flake8`)
- Standard Python style conventions observed
- Grouped in order: standard library, third-party, local imports
- Example from `mdm_engine.py`:
- No type checking configuration (no `mypy.ini`)
## Import Organization
- None detected - uses relative imports within packages
- Example: `from .data_loader import DataLoader` in same package
## Error Handling
- Minimal error handling observed - focus on domain logic
- Limited use of try/except: only found in `distribution_day.py` for date parsing
- Assertions used for parameter validation in `__post_init__` methods:
- DataFrame operations use `.get()` and `.isna()` to handle missing values safely
## Logging
- Console output via `print()` statements
- Results written to files with `open()` and manual string formatting
- Example from `run_backtest.py`:
## Comments
- Multi-line docstrings for all public methods and classes
- Inline comments explain domain-specific logic (e.g., indicator calculations, state transitions)
- Comments reference trading rules: "Rules:", "Conditions:", "Check if..."
- Python docstrings follow Google style with `Args:`, `Returns:` sections
- Example from `data_loader.py`:
- Module-level docstrings at top of each file describe purpose
## Function Design
- `check_ftd()`: 20 lines - checks single condition
- `process_day()`: ~100 lines - state machine processing (larger but contains all transitions)
- Static methods used for stateless calculations: `Indicators.price_location()`, `Indicators.add_price_location_column()`
- Keep to 5-7 positional parameters max
- Use default values for optional params: `def __init__(self, config: MDMConfig = None)`
- Long parameter lists passed as structured objects (dataclasses) for complex methods
- Single return value per function (tuples for multiple related values)
- Example: `Tuple[bool, Optional[FTDSignal]]` for signal detection
- None returned when data unavailable
- Empty DataFrames or dicts for "no results" case
## Module Design
- No explicit `__all__` declarations observed
- Classes are the primary exports (e.g., `MDMEngine`, `DataLoader`)
- Functions module-level in utility files: `detect_volume_spike()`, `detect_buy_signal()` in `signals.py`
- `models/__init__.py` imports key classes for convenient access:
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- **Two independent trading strategies** (MDM and VSA) with separate but structurally similar modules
- **Layered architecture** separating data loading, indicator calculation, signal detection, and position management
- **State machine pattern** for position tracking (CASH, HOLDING, WAITING_SELL, SHORT states)
- **Component-based design** with single-responsibility modules that compose into engines
- **Configuration-driven parameters** allowing parameter optimization via config objects
## Layers
- Purpose: Load, validate, and preprocess market data (OHLCV) from CSV sources
- Location: `models/data_loader.py`, `vn30_vsa/data_loader.py`
- Contains: CSV file reading, date range filtering, column mapping, numeric type conversion
- Depends on: pandas for data manipulation
- Used by: Engines (MDMEngine, VSAEngine) to load price data
- Purpose: Calculate technical indicators (moving averages, price location, volume ratios, rolling highs)
- Location: `models/indicators.py`, `vn30_vsa/indicators.py`
- Contains: Static methods for MA10, MA50, price location (P_loc), volume ratios, drawdown calculations
- Depends on: pandas, numpy for vectorized calculations
- Used by: Engines to prepare features before signal detection
- Purpose: Identify buy/sell signals based on strategy-specific rules
- Location: `models/ftd_signal.py`, `models/distribution_day.py`, `models/rally_attempt.py` (MDM) and `vn30_vsa/signals.py` (VSA)
- Contains: FTD detector, distribution day counter, rally attempt tracker (MDM), volume spike and breakout detection (VSA)
- Depends on: Config objects, indicators from layer above
- Used by: Engines to determine trading actions
- Purpose: Track positions, manage state transitions, execute trades, calculate P&L
- Location: `models/position_manager.py`, `vn30_vsa/position_manager.py`
- Contains: Position state machine, trade execution logic, NAV calculation
- Depends on: MarketState enum, Trade/Position dataclasses
- Used by: Engines to update portfolio state based on signals
- Purpose: Enforce stop loss rules and trailing stop loss mechanics
- Location: `models/stop_loss.py`, `vn30_vsa/stop_loss.py`, `vn30_vsa/trailing_stop.py`, `vn30_vsa/kelly.py`
- Contains: Stop loss validation, position sizing via Kelly Criterion
- Depends on: Position data, configuration
- Used by: Engines during daily processing
- Purpose: Orchestrate all layers - coordinate data loading, calculation, signal detection, and position updates
- Location: `models/mdm_engine.py`, `vn30_vsa/vsa_engine.py`
- Contains: Main loop processing daily bars, state machine updates, trade recording
- Depends on: All layers below
- Used by: Scripts (run_backtest.py, optimize_mdm.py) and Jupyter notebooks
- Purpose: Calculate backtest statistics, win rates, P&L metrics
- Location: `models/performance.py`, `vn30_vsa/performance.py`
- Contains: Trade analysis, performance metrics, reporting
- Depends on: Engine results and trade history
- Used by: Backtesting scripts for reporting
## Data Flow
```
```
- Current position stored in `PositionManager.position` (Position dataclass)
- Position includes buy_price, buy_date, buy_day_low, trigger_price, dd5_high
- State transitions triggered by signal detection results passed to `process_day()`
- Trades recorded immediately when exits occur (sell, cover, stop loss)
## Key Abstractions
- Purpose: Centralize strategy parameters for easy modification and optimization
- Examples: `models/config.py` (MDMConfig), `vn30_vsa/config.py` (module-level constants)
- Pattern: Dataclass with parameters + post-init validation (MDM), or module constants (VSA)
- Usage: Passed to component constructors, used during signal detection logic
- Purpose: Encapsulate signal information (date, price, type, confidence)
- Examples: `FTDSignal`, distribution day records, volume spike data
- Pattern: Dataclass with typed fields (signal_type, price, rally_day, date)
- Usage: Returned from detector methods, passed to position manager for action
- Purpose: Type-safe position tracking and trade record keeping
- Examples: `Position` (current position state), `Trade` (completed trade record)
- Pattern: Mutable dataclass for Position, immutable for Trade records
- Usage: Position updated in-place during backtest, Trade created on position close
## Entry Points
- Location: `run_backtest.py`
- Triggers: User executes `python run_backtest.py`
- Responsibilities: Load data, instantiate engine, run backtest, output report to file
- Flow: DataLoader.load() → MDMEngine.run() → PerformanceAnalyzer.print_report()
- Location: `optimize_mdm.py`
- Triggers: User executes `python optimize_mdm.py`
- Responsibilities: Grid search parameter space, run backtest for each combo, compare results
- Flow: Iterate combinations → Create MDMConfig with params → MDMEngine.run() → Compare metrics
- Location: `mdm_backtest.ipynb`, `vn30_vsa_backtest.ipynb`, `sp500_backtest.ipynb`
- Triggers: User opens notebook in Jupyter/IPython
- Responsibilities: Interactive backtesting, parameter tuning, chart visualization
- Flow: Import engines → Run experiments → Plot results in-notebook
- Location: `analysis/diagnose_vn30.py`, `analyze_drawdown.py`, `analyze_vsa_drawdown.py`
- Triggers: User executes scripts for post-backtest analysis
- Responsibilities: Detailed analysis of specific aspects (drawdowns, distribution days, etc.)
## Error Handling
- **Data validation**: DataLoader validates numeric columns, drops rows with NaN, filters dates
- **Type safety**: Use type hints throughout (Optional, Tuple return types for error indication)
- **Graceful degradation**:
- **Config validation**: MDMConfig post_init validates parameter ranges (e.g., correction_threshold < 0)
## Cross-Cutting Concerns
- Data validation in DataLoader (date ranges, numeric types, null handling)
- Config validation in MDMConfig post_init
- Signal validity checks before recording (return False if conditions not met)
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
