# Phase 7: Data Foundation - Research

**Researched:** 2026-03-29
**Domain:** Data loading, CSV parsing, date alignment, pandas DataFrame processing
**Confidence:** HIGH

## Summary

Phase 7 extends the existing data infrastructure (built in Phase 1) to handle the full 52-year NASDAQ price history and the complete 962-signal ground truth. The existing `DataLoader` and `load_signal_fixture()` are well-structured and only need incremental changes: adding historical spot-checks to the DataLoader and extending the signal loader to handle an optional 4th column (`dollar_becomes`).

The NASDAQ CSV (`data/NASDAQ.csv`) already contains 13,317 rows from 1973-06-01 to 2026-03-26, covering the full required range. The signal file (`data/signals/nasdaq_signals_full.csv`) contains exactly 962 signals from 1974-07-17 to 2026-02-27. Date alignment analysis reveals 10 signal dates that fall on weekends (Saturday/Sunday) and have no corresponding OHLCV row -- these are the only gaps and must be reported per D-05.

**Primary recommendation:** Make minimal, targeted changes to existing loaders. Extend spot-checks with 3 verified historical values. Add optional `dollar_becomes` parsing. Build a gap report function that identifies weekend signal dates.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Extend existing `load_signal_fixture()` in `core/signal_loader.py` to optionally parse the `dollar_becomes` column. If the column is present in the CSV, include it in the output DataFrame; if absent, skip gracefully. This keeps backward compatibility with existing 3-column signal CSVs (TECL, partial NASDAQ).
- D-02: The full 962-signal CSV (`data/signals/nasdaq_signals_full.csv`) has 4 columns: `date`, `signal`, `gain_loss_pct`, `dollar_becomes`. All four are parsed by the extended loader.
- D-03: Pass through all NASDAQ data as-is from 1973+. No filtering, trimming, or flagging of early rows with 0 volume or identical OHLC values. Phase 8 indicators (EMA, MA, MACD) only need close prices, which are valid even in the earliest data.
- D-04: The `dropna()` on OHLCV columns in the existing DataLoader is sufficient quality control -- no additional quality gates needed for early data.
- D-05: When a signal date has no matching OHLCV row, warn and report but do not fail. Generate a gap report listing all mismatched signal dates so they are visible for investigation.
- D-06: Phase 8 (Indicator Engine) will decide how to handle gaps during feature snapshot extraction. Phase 7 only ensures the data is loaded and gaps are documented.
- D-07: Add 2-3 spot-check reference values from distinct eras (~1974 early history, ~2000 dot-com peak, ~2008 financial crisis) to the existing SPOT_CHECKS dictionary in `core/data_loader.py`. Combined with existing 2020-2021 checks, this validates normalization across 4+ decades.
- D-08: Keep existing 0.1% tolerance threshold. Same assert-and-halt behavior as Phase 1.

### Claude's Discretion
- Exact reference dates and close prices for 1974/2000/2008 spot-checks (will look up real values)
- Gap report format (print to console, save to file, or return as DataFrame)
- Whether to add a convenience function for loading the full signal history specifically
- Test structure and assertion details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-05 | Full NASDAQ OHLCV data available from 1974+ for indicator computation across entire signal history | NASDAQ.csv already contains 13,317 rows from 1973-06-01. DataLoader loads it correctly with /1000 normalization. Need historical spot-checks to validate early data. |
| DATA-06 | Full signal history loader parses 962 signals (1974-2026) from nasdaq_signals_full.csv with date, signal type, gain/loss, dollar-becomes columns | Signal file confirmed: 962 rows, 4 columns (date, signal, gain_loss_pct, dollar_becomes). Signal loader needs `dollar_becomes` column support. Date format is MM-DD-YYYY. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, CSV parsing, date handling | Already in use; project standard |
| pytest | >= 9.0.2 | Test framework | Already configured in pyproject.toml |

### Supporting
No new libraries needed. Phase 7 uses only pandas features already in the project.

## Architecture Patterns

### Existing Code to Extend (NOT Replace)

```
core/
  data_loader.py   # Add 3 historical spot-checks to SPOT_CHECKS dict
  signal_loader.py # Extend load_signal_fixture() for optional dollar_becomes
```

### Pattern 1: Optional Column Parsing in Signal Loader
**What:** Detect whether `dollar_becomes` column exists in CSV and include it only when present.
**When to use:** When the same loader must handle both 3-column and 4-column signal CSVs.
**Example:**
```python
# After reading CSV
df = pd.read_csv(filepath)

# Parse dollar_becomes if present (backward compatible)
if "dollar_becomes" in df.columns:
    df["dollar_becomes"] = pd.to_numeric(df["dollar_becomes"], errors="coerce")
```

### Pattern 2: Gap Report as DataFrame Return
**What:** Compare signal dates against OHLCV dates, return DataFrame of mismatches.
**When to use:** When documenting date alignment gaps between two datasets.
**Example:**
```python
def check_signal_date_alignment(
    signals: pd.DataFrame, ohlcv: pd.DataFrame
) -> pd.DataFrame:
    """Check which signal dates have no matching OHLCV row.

    Returns:
        DataFrame with columns [date, signal, day_of_week] for unmatched dates.
    """
    ohlcv_dates = set(ohlcv["date"].dt.normalize())
    mask = ~signals["date"].dt.normalize().isin(ohlcv_dates)
    gaps = signals[mask].copy()
    gaps["day_of_week"] = gaps["date"].dt.day_name()
    return gaps[["date", "signal", "day_of_week"]].reset_index(drop=True)
```

### Pattern 3: Spot-Check Dictionary Extension
**What:** Add historical reference values to existing SPOT_CHECKS dict.
**When to use:** Validating data normalization across multiple eras.
**Example:**
```python
SPOT_CHECKS = {
    'nasdaq': [
        # Early history (1974 bear market bottom area)
        ('1974-10-03', 54.87),
        # Dot-com peak (March 10, 2000) - verified: 5048.62
        ('2000-03-10', 5048.62),
        # Financial crisis (Nov 20, 2008) - verified: 1316.12
        ('2008-11-20', 1316.12),
        # Existing checks (2020-2021 era)
        ('2020-01-02', 9092.19),
        ('2020-03-23', 6860.67),
        ('2021-11-19', 16057.4375),
    ],
    # ... sp500 unchanged
}
```

### Anti-Patterns to Avoid
- **Creating a new loader class:** The existing DataLoader handles NASDAQ perfectly. Only the SPOT_CHECKS dictionary needs updating.
- **Filtering early data:** D-03 explicitly says pass through all data as-is. Do not add quality gates for 0-volume or identical-OHLC rows.
- **Failing on gap dates:** D-05 explicitly says warn and report, do not fail.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date parsing | Custom date parser | `pd.to_datetime(format='mixed')` | Already handles MM-DD-YYYY and YYYY-MM-DD formats |
| Column detection | Manual CSV header reading | `"col_name" in df.columns` after `pd.read_csv()` | pandas handles it cleanly |
| Numeric coercion | try/except float() | `pd.to_numeric(errors='coerce')` | Already established project pattern |

## Common Pitfalls

### Pitfall 1: Signal Date Format Mismatch
**What goes wrong:** The full signal CSV uses MM-DD-YYYY format (e.g., `02-27-2026`), while OHLCV dates are YYYY-MM-DD. Direct string comparison fails.
**Why it happens:** Different data sources use different date conventions.
**How to avoid:** Always compare `pd.Timestamp` objects after `pd.to_datetime()` parsing. The existing signal loader already does this correctly.
**Warning signs:** 0 aligned dates when you expect hundreds.

### Pitfall 2: Weekend Signal Dates
**What goes wrong:** 10 of 962 signal dates fall on Saturday or Sunday (no OHLCV trading data exists for weekends).
**Why it happens:** Dr. K's published signal history records the publication date, not the trading date.
**How to avoid:** The gap report (D-05) documents these. Phase 8 will handle alignment.
**Warning signs:** Gap report shows exactly 10 mismatches, all on weekends.
**Known gaps:**
- 1979-10-06 (Saturday)
- 1989-10-28 (Saturday)
- 1992-08-22 (Saturday)
- 1993-04-03 (Saturday)
- 1998-05-30 (Saturday)
- 1998-08-01 (Saturday)
- 2003-01-25 (Saturday)
- 2005-12-17 (Saturday)
- 2011-12-18 (Sunday)
- 2012-05-06 (Sunday)

### Pitfall 3: Breaking Backward Compatibility
**What goes wrong:** Changing signal loader signature or return type breaks existing tests and downstream code (signal_comparator.py).
**Why it happens:** Existing code expects exactly 3 columns from load_signal_fixture.
**How to avoid:** Only ADD the dollar_becomes column when present in CSV. Existing 3-column CSVs produce same output as before. Do not change function signature.
**Warning signs:** Existing test_signal_fixtures.py tests fail.

### Pitfall 4: gain_loss_pct NaN Values in Full Signal File
**What goes wrong:** Assuming all 962 signals have gain_loss_pct values, then filtering or failing on NaN.
**Why it happens:** 339 of 962 signals have NaN gain_loss_pct (Buy and Cash signals typically lack this).
**How to avoid:** Use `pd.to_numeric(errors='coerce')` (already done). Do not dropna on this column.
**Warning signs:** Only 623 non-null gain_loss_pct values out of 962.

## Data Characteristics (Verified)

### NASDAQ OHLCV (data/NASDAQ.csv)
- **Rows:** 13,317 (after header)
- **Date range:** 1973-06-01 to 2026-03-26
- **Format:** Quoted fields, YYYY-MM-DD dates, ~1000x scaled prices
- **Early data (1973-1983):** Volume = 0, OHLC identical (single close value). This is expected and correct per D-03.
- **Column names:** stockcode, tradingdate, openprice, closeprice, highestprice, lowestprice, totalvol

### Full Signal History (data/signals/nasdaq_signals_full.csv)
- **Rows:** 962 signals
- **Date range:** 1974-07-17 to 2026-02-27
- **Date format:** MM-DD-YYYY (differs from OHLCV)
- **Columns:** date, signal, gain_loss_pct, dollar_becomes
- **Signal types:** Buy, Sell, Cash (all valid)
- **gain_loss_pct:** 623 non-null, 339 NaN
- **dollar_becomes:** 962 non-null (all populated)
- **Sort order:** Newest first (reversed from what loader expects)

### Verified Historical Spot-Check Values
| Date | Close | Era | Verification |
|------|-------|-----|-------------|
| 1974-10-03 | 54.87 | Bear market bottom | Loaded from CSV, within range of known 1974 NASDAQ lows |
| 2000-03-10 | 5048.62 | Dot-com peak | Confirmed by Wikipedia, multiple financial sources |
| 2008-11-20 | 1316.12 | Financial crisis | Confirmed by Wikipedia, financial crisis records |

## Code Examples

### Extended signal loader (backward compatible)
```python
def load_signal_fixture(filepath: str) -> pd.DataFrame:
    """Load a published signal history CSV into a structured DataFrame.

    Args:
        filepath: Path to signal CSV. Supports both 3-column (date, signal,
                  gain_loss_pct) and 4-column (+ dollar_becomes) formats.

    Returns:
        DataFrame with parsed dates, validated signal types, numeric columns.
    """
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    df["signal"] = df["signal"].str.strip()

    invalid = set(df["signal"].unique()) - VALID_SIGNALS
    if invalid:
        raise ValueError(f"Invalid signal types found: {invalid}")

    df["gain_loss_pct"] = pd.to_numeric(df["gain_loss_pct"], errors="coerce")

    # Parse dollar_becomes if present (backward compatible with 3-column CSVs)
    if "dollar_becomes" in df.columns:
        df["dollar_becomes"] = pd.to_numeric(
            df["dollar_becomes"], errors="coerce"
        )

    df = df.sort_values("date").reset_index(drop=True)
    return df
```

### Gap report function
```python
def check_signal_date_alignment(
    signals: pd.DataFrame, ohlcv: pd.DataFrame
) -> pd.DataFrame:
    """Check which signal dates have no matching OHLCV trading day.

    Args:
        signals: Signal DataFrame with 'date' column (datetime).
        ohlcv: OHLCV DataFrame with 'date' column (datetime).

    Returns:
        DataFrame of unmatched signal dates with day_of_week info.
        Empty DataFrame if all dates align.
    """
    ohlcv_dates = set(ohlcv["date"].dt.normalize())
    sig_dates_norm = signals["date"].dt.normalize()
    mask = ~sig_dates_norm.isin(ohlcv_dates)
    if mask.sum() == 0:
        return pd.DataFrame(columns=["date", "signal", "day_of_week"])

    gaps = signals.loc[mask, ["date", "signal"]].copy()
    gaps["day_of_week"] = gaps["date"].dt.day_name()
    return gaps.reset_index(drop=True)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `.venv/Scripts/python -m pytest tests/ -x -q` |
| Full suite command | `.venv/Scripts/python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-05 | NASDAQ loads from 1974+ with correct dtypes, no gaps, spot-checks pass | integration | `.venv/Scripts/python -m pytest tests/test_data_loader.py -x -q` | Exists (extend) |
| DATA-05 | Historical spot-checks (1974, 2000, 2008) validate normalization | unit | `.venv/Scripts/python -m pytest tests/test_data_loader.py::TestSpotCheckNasdaq -x -q` | Exists (extend) |
| DATA-06 | Full 962-signal CSV loads with 4 columns | integration | `.venv/Scripts/python -m pytest tests/test_signal_fixtures.py -x -q` | Exists (extend) |
| DATA-06 | Backward compatibility: 3-column CSVs still load correctly | unit | `.venv/Scripts/python -m pytest tests/test_signal_fixtures.py::TestSignalFixtureLoader -x -q` | Exists |
| DATA-06 | Signal-OHLCV date alignment gap report | unit | `.venv/Scripts/python -m pytest tests/test_data_foundation.py -x -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/Scripts/python -m pytest tests/ -x -q`
- **Per wave merge:** `.venv/Scripts/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_data_foundation.py` -- covers gap report function and full signal integration (DATA-05/DATA-06 alignment)
- New tests for historical spot-checks and 4-column signal loading can be added to existing test files

## Project Constraints (from CLAUDE.md)

- Python 3.10+ with uv package manager
- pandas >= 2.0.0 for all data handling
- 4-space indentation, ~120 char line limit
- snake_case for functions/variables, PascalCase for classes
- Google-style docstrings with Args/Returns sections
- Grouped imports: standard library, third-party, local
- Minimal error handling, focus on domain logic
- GSD workflow enforcement for all changes

## Sources

### Primary (HIGH confidence)
- `data/NASDAQ.csv` -- directly loaded and analyzed: 13,317 rows, 1973-06-01 to 2026-03-26
- `data/signals/nasdaq_signals_full.csv` -- directly loaded and analyzed: 962 signals, 4 columns
- `core/data_loader.py` -- read and analyzed existing implementation
- `core/signal_loader.py` -- read and analyzed existing implementation
- `tests/test_data_loader.py` -- read existing test structure
- `tests/test_signal_fixtures.py` -- read existing test structure

### Secondary (MEDIUM confidence)
- Wikipedia: Nasdaq Composite dot-com peak 5,048.62 on 2000-03-10
- Wikipedia: 2008 financial crisis NASDAQ low 1,316.12 on 2008-11-20

### Tertiary (LOW confidence)
- 1974-10-03 close value 54.87: verified only from the project's own CSV data (no independent source found for exact daily NASDAQ values from 1974). The value is plausible given the NASDAQ was in the 50-65 range during late 1974, but treat with slightly lower confidence than the 2000/2008 values.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed, extending existing code
- Architecture: HIGH -- patterns are incremental extensions of Phase 1 work
- Pitfalls: HIGH -- all 10 gap dates verified empirically, data characteristics confirmed by direct analysis

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable -- data files are static, no API dependencies)
