# Phase 1: Data Integrity - Research

**Researched:** 2026-03-27
**Domain:** CSV data loading, normalization, pandas DataFrame processing
**Confidence:** HIGH

## Summary

Phase 1 is a data plumbing phase: build a unified loader that normalizes three CSV files (NASDAQ, S&P500, VN30) into a standard OHLCV DataFrame schema, validate the normalization against known reference values, and manually create structured CSV fixtures for Dr. K's published TECL and NASDAQ signal histories.

The existing codebase has two separate data loaders with different column conventions. The new unified loader will live alongside them (not replace them -- that is Phase 2). The CSV files are clean (zero nulls across all three datasets), use consistent quoting, and parse correctly with default pandas `read_csv`. The primary data issue is the ~1000x scaling on US market OHLC prices, which is a simple static division.

**Primary recommendation:** Build a single `UnifiedDataLoader` class in `core/data_loader.py` that accepts a market type parameter, maps columns per market, applies 1000x division for US OHLC prices only, and outputs a DataFrame with columns `[date, open, high, low, close, volume]`. Add pytest as a dev dependency and write validation tests that assert normalized prices match known reference values within 0.1%.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Static divide by 1000 for US market OHLC prices (NASDAQ, S&P500). Simple and predictable -- scaling factor is known and consistent.
- **D-02:** Volume is NOT normalized -- US volume values (~6.5B for NASDAQ) are already at correct scale.
- **D-03:** Normalization applies to US markets only. VN30 data is already at native scale (~1800 for VN30 index) and does not pass through normalization.
- **D-04:** Single `DataLoader` class that accepts a market type parameter ('nasdaq', 'sp500', 'vn30'). Internally maps columns based on market type and applies normalization where needed.
- **D-05:** Standard output columns: `date`, `open`, `high`, `low`, `close`, `volume` -- matches existing MDM loader output and is standard across trading libraries.
- **D-06:** New module created alongside existing loaders (e.g., `core/data_loader.py`). Existing `models/data_loader.py` and `vn30_vsa/data_loader.py` remain untouched -- Phase 2 handles migration.
- **D-07:** Published signals need to be manually entered from virtueofselfishinvesting.com (no existing file).
- **D-08:** Stored as CSV files with columns: `date`, `signal` (Buy/Sell/Cash), `gain_loss_pct`. Easy to edit, version control friendly, readable by pandas.
- **D-09:** Create fixtures for both TECL and NASDAQ signal histories (2017-2026, 100+ signals each).
- **D-10:** Spot-checks assert and halt on failure. If normalized price is off by >0.1% from known reference value, raise an error. Bad data must block all downstream work.
- **D-11:** Reference values are hardcoded known dates -- pick 3-5 well-known dates per market with expected close prices. Simple, deterministic, easy to verify.

### Claude's Discretion
- Exact reference dates and values for spot-checks (will look up real values during implementation)
- Internal column mapping dictionaries per market type
- CSV parsing details (quote handling, date format detection)
- Signal fixture file location within `data/` directory

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Unified data loader reads NASDAQ, S&P500, VN30 CSV files into normalized OHLCV DataFrames | Column mapping patterns from existing loaders, CSV schema analysis, standard output columns defined in D-05 |
| DATA-02 | US market data prices normalized correctly (scaled ~1000x in source CSV) | Confirmed 1000x factor via empirical check (NASDAQ 2020-01-02 raw=9092190, /1000=9092.19 matches real close). Static /1000 per D-01 |
| DATA-03 | Data validation spot-checks normalized prices against known index values (within 0.1%) | pytest framework for assertions, hardcoded reference values per D-11, fail-fast behavior per D-10 |
| DATA-04 | Published signal parser converts Dr. K's TECL and NASDAQ signal history into structured test fixtures | CSV format with date/signal/gain_loss_pct columns per D-08, manual data entry per D-07 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.3.3 | DataFrame operations, CSV reading, date parsing | Already installed, project standard |
| numpy | (installed) | Numeric operations | Already installed, project standard |
| pytest | latest | Test framework for validation assertions | Python standard, not yet installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.2.1+ | Environment variable loading | Already installed, for file path configuration |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest | unittest | pytest is simpler syntax, better assertions, better output -- use pytest |
| Manual CSV fixtures | JSON fixtures | CSV is simpler for tabular signal data, matches D-08 decision |

**Installation:**
```bash
uv add --dev pytest
```

## Architecture Patterns

### Recommended Project Structure
```
core/                    # New shared infrastructure (D-06)
    __init__.py
    data_loader.py       # UnifiedDataLoader class
data/                    # Market data and signal fixtures
    NASDAQ.csv           # Existing
    s&p500.csv           # Existing
    vn30.csv             # Existing
    signals/             # New signal fixture directory
        tecl_signals.csv
        nasdaq_signals.csv
tests/                   # New test directory
    __init__.py
    test_data_loader.py  # Loader tests + spot-check validations
    test_signal_fixtures.py  # Signal fixture parsing tests
```

### Pattern 1: Market-Type Column Mapping
**What:** Dictionary-based column mapping keyed by market type, following the existing `COLUMN_MAPPING` pattern in `models/data_loader.py`.
**When to use:** When loading any of the three CSV files through the unified loader.
**Example:**
```python
# Based on existing pattern in models/data_loader.py
COLUMN_MAPS = {
    'nasdaq': {
        'stockcode': 'symbol',
        'tradingdate': 'date',
        'openprice': 'open',
        'closeprice': 'close',
        'highestprice': 'high',
        'lowestprice': 'low',
        'totalvol': 'volume',
    },
    'sp500': {
        'stockcode': 'symbol',
        'tradingdate': 'date',
        'openprice': 'open',
        'closeprice': 'close',
        'highestprice': 'high',
        'lowestprice': 'low',
        'totalvol': 'volume',
    },
    'vn30': {
        'stockcode': 'symbol',
        'tradingdate': 'date',
        'openindex': 'open',
        'closeindex': 'close',
        'highestindex': 'high',
        'lowestindex': 'low',
        'totalvol': 'volume',
    },
}

# Markets requiring 1000x normalization on OHLC columns
US_MARKETS = {'nasdaq', 'sp500'}
NORMALIZE_COLS = ['open', 'high', 'low', 'close']
NORMALIZE_FACTOR = 1000.0
```

### Pattern 2: Fail-Fast Validation
**What:** Spot-check assertions that raise errors immediately if normalized data does not match known reference values within tolerance.
**When to use:** After loading and normalizing, before returning the DataFrame.
**Example:**
```python
def validate_spot_checks(df: pd.DataFrame, market: str) -> None:
    """Raise ValueError if normalized prices don't match known values within 0.1%."""
    REFERENCE_VALUES = {
        'nasdaq': [
            ('2020-01-02', 'close', 9092.19),
            # ... more reference dates
        ],
        'sp500': [
            ('2020-01-02', 'close', 3257.85),
            # ... more reference dates
        ],
    }
    refs = REFERENCE_VALUES.get(market, [])
    for date_str, col, expected in refs:
        row = df[df['date'] == pd.Timestamp(date_str)]
        if len(row) == 0:
            continue  # Date not in loaded range
        actual = row.iloc[0][col]
        pct_diff = abs(actual - expected) / expected
        if pct_diff > 0.001:  # 0.1% tolerance
            raise ValueError(
                f"Spot-check FAILED for {market} on {date_str}: "
                f"expected {col}={expected}, got {actual} (diff={pct_diff:.4%})"
            )
```

### Pattern 3: Signal Fixture CSV Format
**What:** Simple CSV format for manually entered signal histories.
**When to use:** For TECL and NASDAQ published signal fixtures.
**Example:**
```csv
date,signal,gain_loss_pct
2020-04-02,Buy,
2020-06-24,Sell,15.3
2020-06-29,Buy,
2020-09-04,Sell,22.1
```

### Anti-Patterns to Avoid
- **Modifying existing loaders:** D-06 explicitly says existing `models/data_loader.py` and `vn30_vsa/data_loader.py` remain untouched. Phase 2 handles migration.
- **Dynamic scale detection:** Do not try to auto-detect the 1000x factor. D-01 says use static division. The factor is known and consistent.
- **Loading all markets in one call:** Keep the loader per-market. Each call loads one market's data. Simplifies error handling and validation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing | Custom file reader | `pd.read_csv()` | Handles quoting, type inference, memory efficiently |
| Date parsing | Regex-based parser | `pd.to_datetime(format='mixed')` | Already proven in existing codebase for these CSVs |
| Test assertions | Manual if/raise in scripts | `pytest` with `assert` | Better output on failure, test discovery, fixtures |
| Tolerance comparison | Manual abs/div math in tests | `pytest.approx()` | Clean syntax: `assert actual == pytest.approx(expected, rel=0.001)` |

**Key insight:** The data is clean (zero nulls, consistent formats). The main complexity is the column mapping and normalization, which is straightforward dictionary-based transformation. Do not over-engineer this.

## Common Pitfalls

### Pitfall 1: Normalizing Volume Along with Price
**What goes wrong:** Dividing volume by 1000 when it should stay as-is.
**Why it happens:** Easy to apply normalization to all numeric columns.
**How to avoid:** D-02 explicitly states volume is NOT normalized. Only normalize OHLC columns (`open`, `high`, `low`, `close`).
**Warning signs:** Volume values in the hundreds of thousands instead of billions after loading.

### Pitfall 2: S&P500 Filename Has Special Character
**What goes wrong:** File path `data/s&p500.csv` contains an ampersand. Shell quoting or path construction might fail.
**Why it happens:** `&` is a special character in shell and some path-handling code.
**How to avoid:** Always use proper string handling. In Python, `Path('data/s&p500.csv')` works fine. In shell, quote the path.
**Warning signs:** FileNotFoundError when loading S&P500.

### Pitfall 3: Date Column as String vs Datetime
**What goes wrong:** Dates remain as strings after loading, causing silent failures in date-range filtering.
**Why it happens:** `pd.read_csv` may parse dates as strings depending on format.
**How to avoid:** Explicitly call `pd.to_datetime()` on the date column and verify dtype is `datetime64[ns]`.
**Warning signs:** Date comparisons returning unexpected results, or empty DataFrames after filtering.

### Pitfall 4: Data Sorted Descending (Newest First)
**What goes wrong:** Indicators and signals computed incorrectly because data is reverse-chronological.
**Why it happens:** All three CSV files have newest dates first (confirmed by inspection).
**How to avoid:** Always sort by date ascending after loading: `df.sort_values('date').reset_index(drop=True)`.
**Warning signs:** Moving averages or shift operations producing nonsensical values.

### Pitfall 5: Signal Fixture Data Entry Errors
**What goes wrong:** Manual entry of 100+ signals introduces typos in dates or signal types.
**Why it happens:** Human error in manual data transcription.
**How to avoid:** Write a parsing test that validates all dates are valid trading days, all signal types are in the expected set (Buy/Sell/Cash), and gain/loss values are reasonable.
**Warning signs:** Duplicate dates, non-trading-day dates (weekends), unknown signal types.

### Pitfall 6: Percentage-Based Calculations on Non-Normalized Data
**What goes wrong:** FTD thresholds, stop losses, or other percentage calculations applied to raw (1000x) prices produce correct percentages but wrong absolute values if mixed with normalized data.
**Why it happens:** Percentage changes are scale-invariant, so the bug is subtle -- it only manifests when mixing raw and normalized prices.
**How to avoid:** Normalize immediately at load time, never expose raw prices. Validate with explicit spot-checks.
**Warning signs:** Absolute dollar amounts (not percentages) being 1000x too large.

## Code Examples

### Unified DataLoader Class (Core Pattern)
```python
# core/data_loader.py
import pandas as pd
from pathlib import Path
from typing import Optional

class DataLoader:
    """Unified data loader for NASDAQ, S&P500, and VN30 market data."""

    COLUMN_MAPS = {
        'nasdaq': {
            'tradingdate': 'date', 'openprice': 'open', 'closeprice': 'close',
            'highestprice': 'high', 'lowestprice': 'low', 'totalvol': 'volume',
        },
        'sp500': {
            'tradingdate': 'date', 'openprice': 'open', 'closeprice': 'close',
            'highestprice': 'high', 'lowestprice': 'low', 'totalvol': 'volume',
        },
        'vn30': {
            'tradingdate': 'date', 'openindex': 'open', 'closeindex': 'close',
            'highestindex': 'high', 'lowestindex': 'low', 'totalvol': 'volume',
        },
    }

    FILE_PATHS = {
        'nasdaq': 'data/NASDAQ.csv',
        'sp500': 'data/s&p500.csv',
        'vn30': 'data/vn30.csv',
    }

    US_MARKETS = {'nasdaq', 'sp500'}
    OHLC_COLS = ['open', 'high', 'low', 'close']
    OUTPUT_COLS = ['date', 'open', 'high', 'low', 'close', 'volume']

    def __init__(self, market: str, data_dir: Optional[str] = None):
        if market not in self.COLUMN_MAPS:
            raise ValueError(f"Unknown market: {market}. Must be one of {list(self.COLUMN_MAPS.keys())}")
        self.market = market
        self.data_dir = Path(data_dir) if data_dir else Path('.')

    def load(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        filepath = self.data_dir / self.FILE_PATHS[self.market]
        df = pd.read_csv(filepath)

        # Drop stockcode, rename columns
        col_map = self.COLUMN_MAPS[self.market]
        df = df.rename(columns=col_map)

        # Parse dates
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        df['date'] = df['date'].dt.normalize()

        # Ensure numeric
        for col in self.OHLC_COLS + ['volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Normalize US market prices (D-01, D-02, D-03)
        if self.market in self.US_MARKETS:
            for col in self.OHLC_COLS:
                df[col] = df[col] / 1000.0

        # Filter date range
        if start_date:
            df = df[df['date'] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df['date'] <= pd.Timestamp(end_date)]

        # Sort ascending, reset index
        df = df.sort_values('date').reset_index(drop=True)

        # Drop nulls and select output columns
        df = df.dropna(subset=self.OHLC_COLS + ['volume'])
        df = df[self.OUTPUT_COLS]

        return df
```

### Signal Fixture Loader
```python
# core/signal_loader.py
import pandas as pd
from pathlib import Path

def load_signal_fixture(filepath: str) -> pd.DataFrame:
    """Load a published signal history CSV into a structured DataFrame."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df['signal'] = df['signal'].str.strip()

    valid_signals = {'Buy', 'Sell', 'Cash'}
    invalid = set(df['signal'].unique()) - valid_signals
    if invalid:
        raise ValueError(f"Invalid signal types found: {invalid}")

    if 'gain_loss_pct' in df.columns:
        df['gain_loss_pct'] = pd.to_numeric(df['gain_loss_pct'], errors='coerce')

    return df.sort_values('date').reset_index(drop=True)
```

### Spot-Check Test Example
```python
# tests/test_data_loader.py
import pytest
from core.data_loader import DataLoader

def test_nasdaq_normalization_spot_check():
    loader = DataLoader('nasdaq')
    df = loader.load(start_date='2020-01-01', end_date='2020-01-10')
    row = df[df['date'] == '2020-01-02'].iloc[0]
    # NASDAQ Composite close on 2020-01-02: ~9092.19
    assert row['close'] == pytest.approx(9092.19, rel=0.001)

def test_vn30_no_normalization():
    loader = DataLoader('vn30')
    df = loader.load(start_date='2026-03-27', end_date='2026-03-27')
    row = df.iloc[0]
    # VN30 close on 2026-03-27 should be ~1821.53 (native scale)
    assert row['close'] == pytest.approx(1821.53, rel=0.001)

def test_output_columns():
    loader = DataLoader('nasdaq')
    df = loader.load(start_date='2020-01-01', end_date='2020-01-10')
    assert list(df.columns) == ['date', 'open', 'high', 'low', 'close', 'volume']
    assert df['date'].dtype == 'datetime64[ns]'
    assert df['close'].dtype == 'float64'
```

## Data Characteristics (Verified)

| Property | NASDAQ | S&P500 | VN30 |
|----------|--------|--------|------|
| Rows | 13,317 | 10,787 | 3,762 |
| Date range | 1973-06-01 to 2026-03-26 | 1983-07-08 to 2026-03-26 | 2011-03-01 to 2026-03-27 |
| Null values | 0 | 0 | 0 |
| Stock code | ^IXIC | ^SPX | VN30 |
| OHLC columns | openprice, closeprice, highestprice, lowestprice | openprice, closeprice, highestprice, lowestprice | openindex, closeindex, highestindex, lowestindex |
| Volume column | totalvol | totalvol | totalvol |
| Sort order | Newest first | Newest first | Newest first |
| OHLC scale | ~1000x (confirmed) | ~1000x (confirmed) | Native (no scaling) |
| Volume scale | Native (~6.5B) | Native (~3B) | Native (~275M) |
| Date format | YYYY-MM-DD (clean, no ISO suffix) | YYYY-MM-DD | YYYY-MM-DD |
| Quoting | Double-quoted strings | Double-quoted strings | Double-quoted strings |

**Scale verification:** NASDAQ 2020-01-02 raw close = 9,092,190.0 / 1000 = 9,092.19 (matches real-world value). S&P500 same date raw close = 3,257,850.0 / 1000 = 3,257.85 (matches real-world value).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (needs installation) |
| Config file | none -- Wave 0 must create `pyproject.toml` `[tool.pytest.ini_options]` or `pytest.ini` |
| Quick run command | `uv run pytest tests/ -x` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Unified loader produces correct OHLCV DataFrames for all 3 markets | unit | `uv run pytest tests/test_data_loader.py -x` | Wave 0 |
| DATA-02 | US prices normalized by /1000, VN30 untouched | unit | `uv run pytest tests/test_data_loader.py::test_normalization -x` | Wave 0 |
| DATA-03 | Spot-checks against known reference values within 0.1% | unit | `uv run pytest tests/test_data_loader.py::test_spot_checks -x` | Wave 0 |
| DATA-04 | Signal fixtures parse into structured DataFrames | unit | `uv run pytest tests/test_signal_fixtures.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` -- empty init for test package
- [ ] `tests/test_data_loader.py` -- covers DATA-01, DATA-02, DATA-03
- [ ] `tests/test_signal_fixtures.py` -- covers DATA-04
- [ ] pytest install: `uv add --dev pytest`
- [ ] `core/__init__.py` -- empty init for core package

## Open Questions

1. **Exact reference values for spot-checks**
   - What we know: NASDAQ 2020-01-02 close = 9092.19 (verified from CSV). Need 3-5 dates per market.
   - What's unclear: Exact close values for other well-known dates. Will need to look up during implementation.
   - Recommendation: Use dates around major events (COVID crash, 2022 bear market, etc.) where values are well-documented. Implementation agent can verify via web search at build time (per "Claude's Discretion").

2. **Signal fixture completeness**
   - What we know: Need TECL and NASDAQ signals from 2017-2026, 100+ each (D-09).
   - What's unclear: Exact number of signals available from virtueofselfishinvesting.com. Whether gain/loss percentages are consistently published.
   - Recommendation: Start with whatever signals are publicly available. Document gaps. The fixture format supports optional gain_loss_pct (can be empty).

3. **`core/` directory naming**
   - What we know: D-06 says "e.g., `core/data_loader.py`". Phase 2 plans a three-layer architecture with `core/` as shared infrastructure.
   - What's unclear: Whether Phase 2 will rename this directory.
   - Recommendation: Use `core/` now as stated in D-06. Phase 2 can reorganize if needed. The unified loader's API should be stable regardless of file location.

## Sources

### Primary (HIGH confidence)
- Direct CSV file inspection via pandas -- confirmed column names, data types, null counts, date ranges, scale factors
- Existing `models/data_loader.py` -- reference implementation for column mapping and date parsing patterns
- Existing `vn30_vsa/data_loader.py` -- reference implementation for VN30-specific handling
- `pyproject.toml` -- confirmed Python 3.10+ requirement, pandas 2.0+ dependency

### Secondary (MEDIUM confidence)
- NASDAQ 2020-01-02 close value of ~9092.19 -- verified by dividing raw CSV value by 1000, consistent with known historical NASDAQ levels

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using existing project dependencies (pandas, numpy) plus pytest which is Python standard
- Architecture: HIGH - following existing patterns from the two current data loaders, decisions are locked
- Pitfalls: HIGH - derived from direct inspection of actual CSV data and existing code patterns

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain, data files unlikely to change format)
