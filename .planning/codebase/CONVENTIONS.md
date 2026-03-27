# Coding Conventions

**Analysis Date:** 2026-03-27

## Naming Patterns

**Files:**
- Lowercase with underscores: `data_loader.py`, `ftd_signal.py`, `position_manager.py`
- Module purpose reflected in name (e.g., `mdm_engine.py` for main engine, `indicators.py` for calculations)
- Configuration files: `config.py`

**Functions:**
- snake_case: `check_distribution_day()`, `add_price_location_column()`, `calculate_rolling_kelly()`
- Methods prefixed with `get_`, `set_`, `check_`, `calculate_` to indicate action
- Private methods prefixed with `_` (rarely used)

**Variables:**
- snake_case for all local and module-level variables: `rally_day`, `price_change_pct`, `dd_count`
- Short abbreviations used for domain concepts: `ma50` (50-day moving average), `p_loc` (price location), `dd` (distribution day), `ftd` (follow-through day)
- Boolean flags prefixed with `is_`, `has_`, `should_`: `is_ftd`, `is_dd`, `volume_up`, `stop_loss_triggered`
- Dataframe columns use consistent naming: `date`, `close`, `high`, `low`, `volume`, `open`, `symbol`

**Types:**
- PascalCase for classes: `DataLoader`, `Indicators`, `MDMEngine`, `PositionManager`, `FTDSignalDetector`
- Enum values in UPPERCASE: `MarketState.CASH`, `MarketState.HOLDING`
- Dataclass names in PascalCase: `Position`, `Trade`, `FTDSignal`, `MDMConfig`

## Code Style

**Formatting:**
- No explicit formatter configured (no `.prettierrc` or `black.toml`)
- 4-space indentation (standard Python)
- Line lengths appear to follow 120-char limit based on observed code
- Single blank line between methods, double blank line between classes

**Linting:**
- No linting configuration found (no `.pylintrc` or `.flake8`)
- Standard Python style conventions observed

**Imports:**
- Grouped in order: standard library, third-party, local imports
- Example from `mdm_engine.py`:
  ```python
  import pandas as pd
  from typing import Optional

  from .data_loader import DataLoader
  from .indicators import Indicators
  from .config import MDMConfig
  ```
- No type checking configuration (no `mypy.ini`)

## Import Organization

**Order:**
1. Standard library imports (`pandas`, `numpy`, `dataclasses`, `typing`, `pathlib`)
2. Third-party imports (`pandas`, `numpy`, `requests`)
3. Local imports (relative imports using `.module_name`)

**Path Aliases:**
- None detected - uses relative imports within packages
- Example: `from .data_loader import DataLoader` in same package

## Error Handling

**Patterns:**
- Minimal error handling observed - focus on domain logic
- Limited use of try/except: only found in `distribution_day.py` for date parsing
- Assertions used for parameter validation in `__post_init__` methods:
  ```python
  def __post_init__(self):
      """Validate parameters."""
      assert self.correction_threshold < 0, "Correction threshold must be negative"
      assert self.stop_loss_pct > 0, "Stop loss percentage must be positive"
  ```
- DataFrame operations use `.get()` and `.isna()` to handle missing values safely

## Logging

**Framework:** No logging framework configured

**Patterns:**
- Console output via `print()` statements
- Results written to files with `open()` and manual string formatting
- Example from `run_backtest.py`:
  ```python
  with open('report.txt', 'w', encoding='utf-8') as f:
      sys.stdout = f
      analyzer.print_report()
      sys.stdout = sys.__stdout__
  ```

## Comments

**When to Comment:**
- Multi-line docstrings for all public methods and classes
- Inline comments explain domain-specific logic (e.g., indicator calculations, state transitions)
- Comments reference trading rules: "Rules:", "Conditions:", "Check if..."

**JSDoc/TSDoc:**
- Python docstrings follow Google style with `Args:`, `Returns:` sections
- Example from `data_loader.py`:
  ```python
  def load(self, start_date: str = '2016-01-16', end_date: str = '2026-01-16') -> pd.DataFrame:
      """
      Load and preprocess data from CSV.

      Args:
          start_date: Start date in 'YYYY-MM-DD' format
          end_date: End date in 'YYYY-MM-DD' format

      Returns:
          Preprocessed DataFrame with OHLCV data
      """
  ```
- Module-level docstrings at top of each file describe purpose

## Function Design

**Size:** Functions are small to medium (20-50 lines), focused on single responsibility
- `check_ftd()`: 20 lines - checks single condition
- `process_day()`: ~100 lines - state machine processing (larger but contains all transitions)
- Static methods used for stateless calculations: `Indicators.price_location()`, `Indicators.add_price_location_column()`

**Parameters:**
- Keep to 5-7 positional parameters max
- Use default values for optional params: `def __init__(self, config: MDMConfig = None)`
- Long parameter lists passed as structured objects (dataclasses) for complex methods

**Return Values:**
- Single return value per function (tuples for multiple related values)
- Example: `Tuple[bool, Optional[FTDSignal]]` for signal detection
- None returned when data unavailable
- Empty DataFrames or dicts for "no results" case

## Module Design

**Exports:**
- No explicit `__all__` declarations observed
- Classes are the primary exports (e.g., `MDMEngine`, `DataLoader`)
- Functions module-level in utility files: `detect_volume_spike()`, `detect_buy_signal()` in `signals.py`

**Barrel Files:**
- `models/__init__.py` imports key classes for convenient access:
  - Used for importing multiple components from same package

---

*Convention analysis: 2026-03-27*
