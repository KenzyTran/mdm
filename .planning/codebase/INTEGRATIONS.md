# External Integrations

**Analysis Date:** 2026-03-27

## APIs & External Services

**Current Status:**
- No active external API integrations in use
- `requests` library installed but not imported in any strategy files
- All data sourced from local CSV files

**Potential Integration Points:**
- Market data APIs (not yet implemented)
- Trading execution APIs (not yet implemented)
- Real-time quote services (not yet implemented)

## Data Storage

**Databases:**
- None - File-based storage only

**File Storage:**
- Local filesystem CSV files
- Location: Project root and `data/` directory
- Files:
  - `vnindex_price.csv` - VNINDEX historical data for MDM strategy
  - `vn30_price.csv` - VN30 stock data for VSA strategy
  - `VN30_STOCKS_PRICE.csv` - Alternative VN30 stocks format
  - `data/vn30.csv` - Preprocessed data
  - `data/s&p500.csv` - Comparative market data

**Data Format:**
- CSV format with OHLCV columns
- CSV readers: `pandas.read_csv()` via `DataLoader` classes
  - `models/data_loader.py` - MDM data loading with column mapping
  - `vn30_vsa/data_loader.py` - VSA data loading with column mapping

**Caching:**
- None - Data loaded fresh from CSV on each run
- No in-memory caching beyond DataFrames during execution

## Configuration Management

**Environment Variables:**
- `.env` file present at project root
- Managed by: `python-dotenv` package
- Currently used for: File paths, data source configuration

**Required Environment Setup:**
- Data file paths should be configurable via `.env` if needed
- No API keys or secrets currently required

## Authentication & Identity

**Auth Provider:**
- Not applicable - No external services requiring authentication

**Current Implementation:**
- Standalone local execution
- No user authentication or account management needed
- No API key/token management required

## Monitoring & Observability

**Error Tracking:**
- None configured

**Logging:**
- Console output to stdout
- Report export to text file: `report.txt`
- Analysis output to: `optimization_results.csv`

**Patterns:**
- Print-based logging in analysis scripts (`analysis/diagnose_vn30.py`)
- Example: `print()` statements for progress and results

## CI/CD & Deployment

**Hosting:**
- No cloud deployment
- Local command-line execution only
- Environment: Windows 11 (as per codebase environment)

**CI Pipeline:**
- None configured
- No GitHub Actions, GitLab CI, or other pipeline present

**Execution:**
- Manual script invocation via Python
- Entry points:
  - `run_backtest.py` - MDM strategy backtest
  - `optimize_mdm.py` - Parameter optimization
  - `vn30_vsa/vsa_engine.py` - VSA strategy execution
  - Analysis scripts in `analysis/` directory

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Output & Reporting

**Report Generation:**
- Text reports: `report.txt` (via `PerformanceAnalyzer`)
- CSV exports: `optimization_results.csv`

**Performance Analysis:**
- `models/performance.py` - MDM performance metrics
- `vn30_vsa/performance.py` - VSA performance metrics

## Data Pipeline

**Input:**
- CSV files (OHLCV format)
- File locations specified in:
  - `DataLoader` constructor defaults
  - Engine `load_data()` method parameters

**Processing:**
- Data loading via `DataLoader` classes
- Column mapping and validation
- Date filtering
- Numeric conversion
- Missing value handling

**Output:**
- `PerformanceAnalyzer` class generates:
  - Performance metrics (returns, Sharpe ratio, drawdown, etc.)
  - Trade statistics
  - Backtest reports

## System Dependencies

**External Package Dependencies:**
- pandas - Data manipulation (via pip/uv)
- numpy - Numerical computing (via pip/uv)
- matplotlib - Visualization (via pip/uv)
- jupyter - Interactive notebooks (via pip/uv)
- requests - HTTP client (via pip/uv) [not currently used]
- python-dotenv - Environment config (via pip/uv)

**No system-level dependencies** (no C extensions, no compiled binaries required)

## Scaling & Limitations

**Current Scalability:**
- In-memory processing limited by available RAM
- No distributed computing or parallel processing implemented
- Suitable for: Historical backtesting, parameter optimization
- Not suitable for: Real-time trading, high-frequency analysis

**Performance Constraints:**
- Data loading from CSV: O(n) where n = number of rows
- Strategy execution: O(n) per security
- Memory usage: Proportional to data size (all data in memory via pandas)

## Future Integration Considerations

**Potential Enhancements:**
- Real-time data feed from financial APIs (Alpha Vantage, IB, etc.)
- Database storage (PostgreSQL, SQLite) for larger datasets
- Trading API integration for order execution
- WebSocket support for live market data
- Cloud deployment (AWS, GCP, Azure)

---

*Integration audit: 2026-03-27*
