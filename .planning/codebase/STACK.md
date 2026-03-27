# Technology Stack

**Analysis Date:** 2026-03-27

## Languages

**Primary:**
- Python 3.10+ - Core trading strategy implementation, data processing, backtesting

## Runtime

**Environment:**
- Python 3.10 or higher (specified in `pyproject.toml`)

**Package Manager:**
- uv - Modern Python package manager (configured in `pyproject.toml`)
- Lockfile: Not present (configured via `pyproject.toml`)

## Frameworks & Libraries

**Data Processing & Analysis:**
- pandas >= 2.0.0 - Time series data manipulation, OHLCV processing
- numpy >= 1.24.0 - Numerical computations for indicators and backtesting calculations

**Visualization:**
- matplotlib >= 3.7.0 - Chart generation for performance analysis and market visualization

**Development & Notebooks:**
- jupyter >= 1.0.0 - Interactive analysis and experimentation environment

**HTTP & External Communication:**
- requests >= 2.32.5 - For potential API integrations (currently not actively used for live data)

**Configuration Management:**
- python-dotenv >= 1.2.1 - Environment variable loading from `.env` file

## Core System Architecture

**Framework Pattern:**
- Modular engine-based architecture
- Two distinct trading strategy implementations:
  1. **MDM (Market Direction Model)** - `models/` package
  2. **VSA (Volume Spike Analysis)** - `vn30_vsa/` package

**Engine Classes:**
- `MDMEngine` (`models/mdm_engine.py`) - Orchestrates MDM strategy execution
- `VSAEngine` (`vn30_vsa/vsa_engine.py`) - Orchestrates VSA strategy execution

## Key Dependencies by Purpose

**Critical (Strategy Core):**
- pandas - Required for all data handling and time series operations
- numpy - Required for mathematical calculations on trading signals
- python-dotenv - Environment configuration for file paths and parameters

**Infrastructure:**
- matplotlib - Backtesting analysis and result visualization
- jupyter - Research and analysis notebooks

**Potential (Not Currently Used):**
- requests - Available for future API integration (installed but not currently imported in strategy code)

## Configuration

**Environment:**
- `.env` file present (location: `/c/Users/trant/projects/mdm/.env`)
- No secrets visible in configuration
- File paths and parameters managed via:
  - `models/config.py` - MDM strategy configuration (dataclass: `MDMConfig`)
  - `vn30_vsa/config.py` - VSA strategy configuration (module-level constants)

**Build & Dependency Management:**
- Configuration file: `pyproject.toml`
- Tool: `[tool.uv]` section for package manager configuration
- Dev dependencies: None explicitly configured

## Data Sources

**Current Data Format:**
- CSV files (OHLCV format)
- Files used:
  - `vnindex_price.csv` - VNINDEX market data
  - `vn30_price.csv` - VN30 individual stock data
  - `VN30_STOCKS_PRICE.csv` - Alternative VN30 stocks format
  - `data/vn30.csv` - Preprocessed stock data
  - `data/s&p500.csv` - External market data (for comparison/analysis)

**Column Mappings:**
- MDM loader maps: `stockcode`, `tradingdate`, `openindex`, `closeindex`, `lowestindex`, `highestindex`, `totalvol`
- VSA loader expects: `stockcode`, `tradingdate`, `openprice`, `closeprice`, `highestprice`, `lowestprice`, `totalvol`

## Database & Storage

**Current Implementation:**
- File-based storage only (no database)
- Data source: Local CSV files
- Output: CSV files and text reports

**Persistence:**
- Results exported to:
  - `report.txt` - Backtest performance report
  - `optimization_results.csv` - Parameter optimization results

## Platform Requirements

**Development:**
- OS: Windows (environment shows Windows 11)
- Python 3.10+
- No compiled dependencies required (pure Python)

**Production:**
- Deployment target: Command-line execution environment
- Data files must be available locally (relative paths configured in loaders)
- No server/API deployment required currently

## Performance & Computational Requirements

**Processing:**
- All calculations done in-memory via pandas DataFrames
- No streaming or distributed processing
- Suitable for historical backtesting (not real-time)

**Memory:**
- Scales with data file size
- Typical usage: ~100K to 1M+ rows of OHLCV data

## Versioning & Compatibility

**Python Version Constraint:**
- Minimum: Python 3.10 (due to `requires-python = ">=3.10"`)
- Type hints and modern Python syntax assumed

**Library Compatibility:**
- pandas >= 2.0.0 (requires Python 3.9+)
- numpy >= 1.24.0 (requires Python 3.10+)
- matplotlib >= 3.7.0 (compatible with Python 3.10+)

---

*Stack analysis: 2026-03-27*
