# Phase 1: Data Integrity - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

All market data (NASDAQ, S&P500, VN30) loads correctly through a unified loader with normalized prices, and Dr. K's published signal history (TECL + NASDAQ) is available as structured CSV test fixtures. This phase does NOT reorganize the codebase (Phase 2) or analyze signals (Phase 3).

</domain>

<decisions>
## Implementation Decisions

### Normalization approach
- **D-01:** Static divide by 1000 for US market OHLC prices (NASDAQ, S&P500). Simple and predictable — scaling factor is known and consistent.
- **D-02:** Volume is NOT normalized — US volume values (~6.5B for NASDAQ) are already at correct scale.
- **D-03:** Normalization applies to US markets only. VN30 data is already at native scale (~1800 for VN30 index) and does not pass through normalization.

### Unified loader design
- **D-04:** Single `DataLoader` class that accepts a market type parameter ('nasdaq', 'sp500', 'vn30'). Internally maps columns based on market type and applies normalization where needed.
- **D-05:** Standard output columns: `date`, `open`, `high`, `low`, `close`, `volume` — matches existing MDM loader output and is standard across trading libraries.
- **D-06:** New module created alongside existing loaders (e.g., `core/data_loader.py`). Existing `models/data_loader.py` and `vn30_vsa/data_loader.py` remain untouched — Phase 2 handles migration.

### Signal fixture format
- **D-07:** Published signals need to be manually entered from virtueofselfishinvesting.com (no existing file).
- **D-08:** Stored as CSV files with columns: `date`, `signal` (Buy/Sell/Cash), `gain_loss_pct`. Easy to edit, version control friendly, readable by pandas.
- **D-09:** Create fixtures for both TECL and NASDAQ signal histories (2017-2026, 100+ signals each).

### Validation spot-checks
- **D-10:** Spot-checks assert and halt on failure. If normalized price is off by >0.1% from known reference value, raise an error. Bad data must block all downstream work.
- **D-11:** Reference values are hardcoded known dates — pick 3-5 well-known dates per market with expected close prices. Simple, deterministic, easy to verify.

### Claude's Discretion
- Exact reference dates and values for spot-checks (will look up real values during implementation)
- Internal column mapping dictionaries per market type
- CSV parsing details (quote handling, date format detection)
- Signal fixture file location within `data/` directory

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing data loaders (reference implementations)
- `models/data_loader.py` — Current MDM loader with `openindex`→`open` column mapping, date parsing, and numeric conversion
- `vn30_vsa/data_loader.py` — Current VSA loader with `openprice` column names, multi-stock grouping

### Data files
- `data/NASDAQ.csv` — NASDAQ Composite OHLCV with ~1000x scaled prices, `openprice`/`closeprice` columns
- `data/s&p500.csv` — S&P 500 OHLCV with ~1000x scaled prices, same column format as NASDAQ
- `data/vn30.csv` — VN30 index OHLCV at native scale, `openindex`/`closeindex` columns

### Requirements
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-04 define acceptance criteria for this phase

### Known issues
- `.planning/codebase/CONCERNS.md` — Documents CSV date parsing inconsistency, inconsistent column naming, hardcoded file paths

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models/data_loader.py` DataLoader class: Column mapping pattern, date parsing with `format='mixed'`, numeric coercion — can be used as template for unified loader
- `vn30_vsa/data_loader.py` load_vn30_data(): Multi-stock grouping pattern — may be useful for future phases but not directly needed here

### Established Patterns
- Column mapping via dictionary: `COLUMN_MAPPING = {'stockcode': 'symbol', 'tradingdate': 'date', ...}` — unified loader should follow same pattern
- Date handling: Strip quotes, `pd.to_datetime(format='mixed')`, normalize — proven approach for the CSV formats in this project
- Numeric coercion: `pd.to_numeric(errors='coerce')` followed by `dropna()` — defensive pattern already used

### Integration Points
- New unified loader will be imported by `run_backtest.py` and future analysis scripts
- Must produce DataFrames compatible with `models/indicators.py` (expects `close`, `high`, `low`, `volume` columns)
- Signal fixture CSVs will be consumed by Phase 3's signal comparison engine

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-integrity*
*Context gathered: 2026-03-27*
