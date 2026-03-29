# Phase 8: Indicator Engine - Research

**Researched:** 2026-03-29
**Domain:** Technical indicator computation (EMA, SMA, MACD, Heikin Ashi Smoothed) and feature extraction
**Confidence:** HIGH

## Summary

Phase 8 builds a new indicator computation module in `core/` that computes EMA 9/21/55, MA 200, MACD (12,26,9), and Heikin Ashi Smoothed candles on the full 13,317-row NASDAQ OHLCV dataset (1973-2026). The output is a feature snapshot DataFrame extracted at each of the 962 signal dates, containing all indicator values plus derived features (crossover states, price-vs-MA relationships, MACD histogram sign).

The existing `strategies/mdm_classic/indicators.py` and `strategies/mdm_v2/indicators.py` compute MA10, MA50, price location, and volume metrics but do NOT compute EMAs, MACD, or Heikin Ashi. The new module belongs in `core/` since it serves the v2.0 rule discovery pipeline (Phase 9+), not any single strategy. All indicator math uses pandas built-in `ewm()` and `rolling()` -- no external TA libraries needed.

**Primary recommendation:** Create `core/indicators.py` with pure pandas/numpy indicator functions, then a `core/feature_snapshot.py` that joins indicators with signal dates. Use `adjust=False` for all EMA calculations to match standard charting platform behavior (TradingView, StockCharts).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IND-01 | EMA 9, EMA 21, EMA 55 computed on daily NASDAQ close prices | pandas `ewm(span=N, adjust=False).mean()` -- standard recursive EMA formula, spot-check against known values |
| IND-02 | MA 200 (simple) computed on daily NASDAQ close prices | pandas `rolling(window=200).mean()` -- use `min_periods=200` (not 1) to avoid partial-window values |
| IND-03 | MACD (12, 26, 9) with signal line and histogram | Standard: MACD = EMA12 - EMA26, Signal = EMA9(MACD), Histogram = MACD - Signal |
| IND-04 | Heikin Ashi Smoothed candles from OHLC data | Two-stage process: (1) smooth OHLC with EMA(55), (2) compute HA candles from smoothed prices, (3) optionally smooth again |
| IND-05 | Feature snapshot at each signal date with all indicators, crossover states, price-vs-MA relationships | Join indicators DataFrame with 962 signal dates; derive boolean crossover and relationship columns |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.3.3 (installed) | EMA via `ewm()`, SMA via `rolling()`, DataFrame ops | Already in project; `ewm` is the canonical EMA implementation |
| numpy | 2.4.1 (installed) | Vectorized boolean operations for crossover detection | Already in project; needed for efficient array comparisons |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 (installed) | Unit tests for indicator accuracy | Test each indicator against known values |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled indicators | `ta` (technical-analysis) library | `ta` has 130+ indicators but adds dependency for only 4 we need; pandas built-ins suffice |
| Hand-rolled indicators | `pandas-ta` | Same tradeoff; project already uses raw pandas everywhere |

**No new dependencies required.** All indicators can be computed with pandas + numpy already installed.

## Architecture Patterns

### Recommended Project Structure
```
core/
  indicators.py       # NEW: EMA, SMA, MACD, Heikin Ashi Smoothed functions
  feature_snapshot.py  # NEW: Extract feature rows at signal dates
  data_loader.py       # EXISTING
  signal_loader.py     # EXISTING
tests/
  test_indicators.py       # NEW: Unit tests for each indicator
  test_feature_snapshot.py # NEW: Integration tests for feature extraction
```

### Pattern 1: Stateless Indicator Functions
**What:** Each indicator is a pure function taking a pandas Series/DataFrame and returning a Series/DataFrame with the computed values. No class needed.
**When to use:** Always for this phase -- indicators are stateless transformations.
**Example:**
```python
def compute_ema(series: pd.Series, span: int) -> pd.Series:
    """Compute EMA using standard recursive formula (adjust=False).

    Args:
        series: Price series (typically close prices).
        span: EMA period (e.g., 9, 21, 55).

    Returns:
        EMA series. First (span-1) values will be less accurate
        due to initialization but converge quickly.
    """
    return series.ewm(span=span, adjust=False).mean()


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    """Compute SMA with strict min_periods to avoid partial windows."""
    return series.rolling(window=window, min_periods=window).mean()


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Compute MACD line, signal line, and histogram.

    Returns:
        DataFrame with columns [macd, macd_signal, macd_histogram].
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({
        'macd': macd_line,
        'macd_signal': signal_line,
        'macd_histogram': histogram,
    })
```

### Pattern 2: Heikin Ashi Smoothed (Two-Stage)
**What:** The "Heikin Ashi Smoothed Buy Sell v4" indicator referenced in Dr. K's TradingView setup uses EMA period 55. The calculation:
1. Compute standard Heikin Ashi candles from raw OHLC
2. Smooth the HA candles with EMA(55)
3. Some variants apply triple-EMA smoothing (TEMA) for extra smoothing

**Standard Heikin Ashi formulas:**
```python
def compute_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Heikin Ashi OHLC from standard OHLC.

    Args:
        df: DataFrame with columns [open, high, low, close].

    Returns:
        DataFrame with columns [ha_open, ha_high, ha_low, ha_close].
    """
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4

    ha_open = pd.Series(index=df.index, dtype='float64')
    ha_open.iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2

    ha_high = pd.concat([df['high'], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df['low'], ha_open, ha_close], axis=1).min(axis=1)

    return pd.DataFrame({
        'ha_open': ha_open,
        'ha_high': ha_high,
        'ha_low': ha_low,
        'ha_close': ha_close,
    })


def compute_heikin_ashi_smoothed(df: pd.DataFrame, period: int = 55) -> pd.DataFrame:
    """Compute Heikin Ashi Smoothed candles.

    Two-stage process:
    1. Smooth raw OHLC with EMA(period)
    2. Compute Heikin Ashi on the smoothed OHLC
    """
    smoothed = pd.DataFrame({
        'open': df['open'].ewm(span=period, adjust=False).mean(),
        'high': df['high'].ewm(span=period, adjust=False).mean(),
        'low': df['low'].ewm(span=period, adjust=False).mean(),
        'close': df['close'].ewm(span=period, adjust=False).mean(),
    })
    return compute_heikin_ashi(smoothed)
```

### Pattern 3: Feature Snapshot Extraction
**What:** Join the full indicator DataFrame with the 962 signal dates to extract feature rows.
**Example:**
```python
def extract_feature_snapshot(
    indicators_df: pd.DataFrame,
    signals_df: pd.DataFrame,
) -> pd.DataFrame:
    """Extract indicator values at each signal date.

    Args:
        indicators_df: Full OHLCV + all indicators, indexed by date.
        signals_df: Signal dates with signal type.

    Returns:
        DataFrame with one row per signal date, all indicator columns,
        plus derived features (crossover states, price relationships).
    """
    # Merge on date (inner join to get only matching dates)
    snapshot = signals_df.merge(indicators_df, on='date', how='left')

    # Add derived boolean features
    snapshot['ema9_above_ema21'] = snapshot['ema9'] > snapshot['ema21']
    snapshot['ema21_above_ema55'] = snapshot['ema21'] > snapshot['ema55']
    snapshot['close_above_ma200'] = snapshot['close'] > snapshot['ma200']
    snapshot['close_above_ema9'] = snapshot['close'] > snapshot['ema9']
    snapshot['close_above_ema21'] = snapshot['close'] > snapshot['ema21']
    snapshot['close_above_ema55'] = snapshot['close'] > snapshot['ema55']
    snapshot['macd_histogram_positive'] = snapshot['macd_histogram'] > 0
    snapshot['macd_above_signal'] = snapshot['macd'] > snapshot['macd_signal']

    return snapshot
```

### Anti-Patterns to Avoid
- **Using `min_periods=1` for SMA/MA200:** This produces misleading partial-window averages. Use `min_periods=window` so early rows are NaN, which is correct.
- **Using `adjust=True` for EMA:** Standard charting platforms (TradingView, StockCharts) use the recursive formula which corresponds to `adjust=False` in pandas. Using `adjust=True` produces different values, especially in early periods.
- **Row-by-row iteration for EMA/SMA:** pandas vectorized operations are orders of magnitude faster. Only Heikin Ashi open requires a loop (recursive dependency on prior value).
- **Computing indicators inside the strategy modules:** These indicators serve rule discovery (Phase 9), not any single strategy. They belong in `core/`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EMA calculation | Manual alpha/decay loop | `pd.Series.ewm(span=N, adjust=False).mean()` | Pandas handles edge cases, NaN propagation, performance |
| SMA calculation | Manual rolling sum/divide | `pd.Series.rolling(window=N, min_periods=N).mean()` | Same reasons |
| MACD | Custom EMA difference class | Three calls to `ewm().mean()` composed together | Simple composition of primitives |

**Key insight:** All four indicator types (EMA, SMA, MACD, HA Smoothed) are built from pandas primitives. The only custom code needed is the Heikin Ashi open recursive calculation and the feature snapshot extraction logic.

## Common Pitfalls

### Pitfall 1: EMA adjust Parameter Mismatch
**What goes wrong:** EMA values don't match TradingView/StockCharts reference values.
**Why it happens:** pandas defaults to `adjust=True`, which uses a different weighting scheme than the standard recursive EMA formula used by charting platforms.
**How to avoid:** Always use `adjust=False` for all EMA calculations in this project.
**Warning signs:** Spot-check values diverge from reference, especially in the first 50-100 bars.

### Pitfall 2: NaN Propagation in Feature Snapshot
**What goes wrong:** Feature snapshot has NaN values at signal dates.
**Why it happens:** MA200 requires 200 data points to produce a value. EMA55 needs ~55+ bars to stabilize. The first signal date (1974-07-17) is ~280 trading days into the dataset (starting 1973-06-01), so it should be fine -- but signal dates with no OHLCV match (10 weekend dates) will produce NaN on left join.
**How to avoid:** (1) Use inner join or filter out the 10 weekend signal dates. (2) Verify no NaN after ~200 trading days warm-up. (3) The success criteria says "after indicator warm-up period (~200 trading days)" so first few signals may have NaN for MA200 which is acceptable.
**Warning signs:** NaN count > 10 in the feature snapshot after warm-up.

### Pitfall 3: Heikin Ashi Open Iterative Computation Performance
**What goes wrong:** Python loop over 13,317 rows is slow.
**Why it happens:** Heikin Ashi open is defined recursively: `ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2`. Cannot be vectorized directly.
**How to avoid:** Use numba `@jit` if available, or accept the ~0.1s runtime for 13K rows (acceptable for batch computation). Alternatively, use the `pandas.DataFrame.itertuples()` which is faster than `iloc` in a loop.
**Warning signs:** Runtime > 1 second for HA computation.

### Pitfall 4: Weekend Signal Dates Cause Join Failures
**What goes wrong:** 10 of 962 signal dates fall on weekends and have no OHLCV row.
**Why it happens:** Phase 7 gap report confirmed 10 weekend signal dates.
**How to avoid:** For weekend signals, snap to the nearest prior trading day (Friday). Document this behavior. The `check_signal_date_alignment` function from Phase 7 already identifies these gaps.
**Warning signs:** Feature snapshot has exactly 10 fewer rows than expected 962.

### Pitfall 5: Heikin Ashi Smoothed Variant Ambiguity
**What goes wrong:** Multiple versions of "HA Smoothed" exist with different formulas.
**Why it happens:** TradingView has dozens of HA Smoothed indicators. Dr. K uses "Heikin Ashi Smoothed Buy Sell v4 55" -- the "55" is the EMA period.
**How to avoid:** Implement the two-stage version (smooth OHLC with EMA(55), then compute HA candles) as the primary. The triple-EMA variant (TMA = 3*EMA1 - 3*EMA2 + EMA3) can be added as an alternative if validation shows the simpler version doesn't match Dr. K's charts. Start simple.
**Warning signs:** HA smoothed candles don't show the expected smoothing behavior visually.

## Code Examples

### Complete Indicator Pipeline
```python
# Source: pandas official docs + standard TA formulas
import pandas as pd
import numpy as np

def build_indicator_dataframe(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Add all Phase 8 indicators to an OHLCV DataFrame.

    Args:
        ohlcv: DataFrame with columns [date, open, high, low, close, volume].

    Returns:
        DataFrame with original columns plus all indicator columns.
    """
    df = ohlcv.copy()

    # IND-01: EMAs
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()

    # IND-02: MA 200
    df['ma200'] = df['close'].rolling(window=200, min_periods=200).mean()

    # IND-03: MACD (12, 26, 9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']

    # IND-04: Heikin Ashi Smoothed (period=55)
    ha_smoothed = compute_heikin_ashi_smoothed(df, period=55)
    df['ha_smooth_open'] = ha_smoothed['ha_open']
    df['ha_smooth_high'] = ha_smoothed['ha_high']
    df['ha_smooth_low'] = ha_smoothed['ha_low']
    df['ha_smooth_close'] = ha_smoothed['ha_close']

    return df
```

### Spot-Check Verification Pattern
```python
# Verify EMA against a known reference value
# For NASDAQ close on 2020-01-02 = 9092.19
# After ~12000 trading days, EMA values should be stable
def verify_ema_spot_check(df: pd.DataFrame):
    """Verify EMA values are reasonable on a known date."""
    row = df[df['date'] == '2020-01-02'].iloc[0]
    close = row['close']
    ema9 = row['ema9']
    # EMA9 should be close to recent prices (within a few percent)
    assert abs(ema9 - close) / close < 0.05, f"EMA9 too far from close: {ema9} vs {close}"
    # MA200 should be below close in a bull market (2020 was near highs)
    assert row['ma200'] < close, "MA200 should be below close in bull market"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `min_periods=1` for rolling | `min_periods=window` | pandas best practice | Prevents misleading partial averages |
| `adjust=True` (pandas default) | `adjust=False` for charting EMAs | Convention clarification | Matches TradingView/StockCharts |
| External TA libraries (ta-lib, ta) | pandas built-in ewm/rolling | When pandas added ewm | No C dependency, simpler install |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_indicators.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IND-01 | EMA 9/21/55 values correct | unit | `pytest tests/test_indicators.py::test_ema_values -x` | Wave 0 |
| IND-02 | MA 200 values correct | unit | `pytest tests/test_indicators.py::test_ma200_values -x` | Wave 0 |
| IND-03 | MACD line/signal/histogram correct | unit | `pytest tests/test_indicators.py::test_macd_values -x` | Wave 0 |
| IND-04 | HA Smoothed candles computed | unit | `pytest tests/test_indicators.py::test_ha_smoothed -x` | Wave 0 |
| IND-05 | Feature snapshot complete, no NaN after warm-up | integration | `pytest tests/test_feature_snapshot.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_indicators.py tests/test_feature_snapshot.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_indicators.py` -- covers IND-01 through IND-04
- [ ] `tests/test_feature_snapshot.py` -- covers IND-05

## Open Questions

1. **Heikin Ashi Smoothed exact variant**
   - What we know: Dr. K uses "Heikin Ashi Smoothed Buy Sell v4 55" on TradingView. The "55" is the EMA period. The "v4" refers to Abdoli's Rev.4 which uses triple-EMA (TEMA) smoothing.
   - What's unclear: Whether Dr. K uses the simple two-stage smoothing or the full TEMA triple-smoothing variant. The TEMA variant is more complex: TMA = 3*EMA1 - 3*EMA2 + EMA3.
   - Recommendation: Implement both the simple two-stage and the TEMA variant. Start with the simpler two-stage version. The TEMA variant can be added if the simpler version's visual output doesn't match. For Phase 8, what matters is that smoothed HA candles are computed -- Phase 9 will determine which variant correlates better with signals.

2. **Weekend signal date handling**
   - What we know: 10 of 962 signal dates fall on weekends (Saturday/Sunday). No OHLCV row exists for these dates.
   - What's unclear: Whether to snap to prior Friday, next Monday, or exclude these signals.
   - Recommendation: Snap to the nearest prior trading day. This is the most conservative approach (the signal was likely issued based on Friday's close).

## Sources

### Primary (HIGH confidence)
- pandas 2.3.3 `ewm()` documentation -- EMA implementation with `adjust` parameter behavior
- pandas 2.3.3 `rolling()` documentation -- SMA implementation with `min_periods`
- Project codebase: `core/data_loader.py`, `core/signal_loader.py`, `strategies/mdm_classic/indicators.py`

### Secondary (MEDIUM confidence)
- [Sierra Chart Heikin-Ashi Smoothed reference](https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=314&Name=Heikin-Ashi_Smoothed) -- two-stage smoothing formula
- [Abdoli's HA Smoothed Buy Sell Rev.4 on TradingView](https://www.tradingview.com/script/2N0o6J1P-Abdoli-s-Heikin-Ashi-Smoothed-Buy-Sell-Strategy-Rev-4/) -- triple-EMA variant
- [StockCharts MACD standard](https://www.alpharithms.com/calculate-macd-python-272222/) -- MACD 12-26-9 standard calculation

### Tertiary (LOW confidence)
- Heikin Ashi Smoothed "v4 55" parameter interpretation -- inferred from TradingView screenshot naming convention; not directly confirmed from Dr. K's settings

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using pandas built-ins already in project, verified versions
- Architecture: HIGH - follows existing project patterns (core/ module, static functions)
- Indicator formulas: HIGH for EMA/SMA/MACD (standard, well-documented), MEDIUM for HA Smoothed (variant ambiguity)
- Pitfalls: HIGH - verified NaN behavior, weekend gaps, adjust parameter

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (stable domain, no fast-moving dependencies)
