# Stack Research

**Domain:** Global Liquidity macro filter + SELL acceleration + BUY selectivity for MDM V2
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

No new dependencies required. The existing pandas + numpy stack handles everything needed for this milestone: weekly-to-daily time series alignment, momentum/acceleration calculations, and signal quality scoring. Adding external TA libraries (pandas-ta, ta-lib) would be over-engineering -- the calculations are simple enough to implement in 5-10 lines of pure pandas each, consistent with the project's existing approach in `core/indicators.py`.

## Recommended Stack

### Core Technologies (NO CHANGES)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| pandas | >= 2.0.0 | All data manipulation, resampling, merging | Already installed |
| numpy | >= 1.24.0 | Numerical computations | Already installed |
| Python | >= 3.10 | Runtime | Already installed |

These three handle 100% of the new feature requirements. No version upgrades needed.

### Supporting Libraries (NO CHANGES)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| matplotlib | >= 3.7.0 | Before/after comparison charts | Already installed |
| scikit-learn | >= 1.5.0 | Parameter optimization if needed | Already installed |

### New Code Modules (NOT libraries -- custom code within project)

| Module | Purpose | Key pandas/numpy APIs Used |
|--------|---------|---------------------------|
| `core/liquidity.py` | Load and align Global Liquidity weekly data to daily | `pd.merge_asof()`, `ffill()`, `pct_change()` |
| Additions to `strategies/mdm_v2/config.py` | New config params for QE floor, SELL acceleration, BUY scoring | dataclass fields |
| Additions to `strategies/mdm_v2/position_manager.py` | Modified state transition logic | Pure Python conditionals |

## Key Technical Decisions

### 1. Weekly-to-Daily Alignment: Use `pd.merge_asof()` not `resample().ffill()`

**Why:** The global liquidity CSV has weekly dates (Wednesdays) that don't align with trading days. `merge_asof` does left-join by nearest prior date, which is exactly the semantics needed: "for each trading day, use the most recent weekly liquidity value."

```python
# Correct approach
daily_with_liquidity = pd.merge_asof(
    daily_df.sort_values('date'),
    liquidity_df[['date', 'global_liquidity', 'liquidity_roc_20w', 'qe_floor']].sort_values('date'),
    on='date',
    direction='backward'  # use most recent prior value
)
```

**Why not `resample().ffill()`:** Requires setting date as index, resampling to daily (creates non-trading days like weekends), then filtering back to trading days. More steps, more error-prone, same result.

**Confidence:** HIGH -- `merge_asof` is standard pandas for this exact use case.

### 2. Momentum/Acceleration: Pure pandas, no external TA library

**Why:** The SELL acceleration condition needs Rate of Change (ROC) and its derivative (acceleration = ROC of ROC). These are trivially computed:

```python
# Rate of change (momentum) over N periods
roc_n = series.pct_change(periods=n)

# Acceleration = change in momentum
acceleration = roc_n.diff()

# Or: ROC of ROC for percentage acceleration
roc_of_roc = roc_n.pct_change(periods=m)
```

MACD histogram slope (already computed in `core/indicators.py`) is another acceleration proxy -- just `macd_hist.diff()`.

**Why not pandas-ta or ta-lib:**
- pandas-ta: 130+ indicators, but we need exactly 2-3 trivial calculations. Adds a dependency for `series.pct_change()`.
- ta-lib: C library with installation complexity on Windows. Overkill.
- The project already implements all its indicators in pure pandas (see `core/indicators.py`). Adding an external library breaks this clean pattern.

**Confidence:** HIGH -- these are fundamental pandas operations.

### 3. BUY Quality Scoring: Weighted scoring in pure Python/numpy

**Why:** BUY selectivity needs a multi-factor score (e.g., liquidity trend + price relative to MA200 + MACD momentum + rally day strength). This is a simple weighted sum:

```python
score = (
    w1 * (liquidity_roc > 0) +      # QE tailwind
    w2 * (close > ma200) +            # Long-term trend
    w3 * (macd_hist > 0) +            # Momentum positive
    w4 * (rally_day >= ftd_min) +     # Rally strength
    w5 * volume_confirmation           # Volume quality
)
buy_quality = score >= threshold
```

No ML needed. No new libraries. Weights tunable via config dataclass, optimizable with existing parameter sweep infrastructure in `analysis/hypothesis/`.

**Confidence:** HIGH.

### 4. Global Liquidity Data: Already Downloaded, No API Needed

The CSV at `data/global_liquidity.csv` already contains:
- `global_liquidity`: Fed + ECB + BOJ combined balance sheet (USD millions)
- `liquidity_roc_20w`: 20-week rate of change (pre-computed)
- `qe_floor`: Binary flag (pre-computed)

987 rows, 2007-2026. Weekly frequency. No FRED API calls needed for backtesting. For future updates, `fredapi` could be added but is out of scope for this milestone.

**Confidence:** HIGH -- data file verified.

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `pd.merge_asof()` for alignment | `resample('D').ffill()` | Creates non-trading day rows, requires extra filtering step |
| Pure pandas ROC/acceleration | `pandas-ta` library | Unnecessary dependency for trivial calculations |
| Pure pandas ROC/acceleration | `ta-lib` (C wrapper) | Windows installation issues, massive overkill |
| Weighted score in Python | scikit-learn classifier | Overfitting risk on small signal dataset, black box vs interpretable |
| Config dataclass params | YAML/JSON config files | Project already uses dataclass pattern everywhere, stay consistent |
| Pre-computed `qe_floor` column | Real-time FRED API | Backtesting only, data already downloaded |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pandas-ta` | Adds dependency for 2 lines of code; project convention is pure pandas indicators | `series.pct_change(n)` and `.diff()` |
| `ta-lib` / `TA-Lib` | C dependency, Windows install pain, 150+ indicators when you need 2 | Pure pandas |
| `fredapi` | Not needed for backtesting; data already in CSV | Direct CSV load |
| `statsmodels` | Tempting for regime detection, but the QE floor is a simple threshold on ROC, not a hidden Markov model | Simple threshold logic |
| ML classifiers for BUY scoring | 962 signals is too few for train/test split; interpretable rules match project philosophy | Weighted scoring with tunable params |

## Integration Points with Existing Code

### Where new code plugs in:

1. **`core/liquidity.py` (new)** -- Loads `data/global_liquidity.csv`, provides `merge_liquidity(daily_df)` function
2. **`strategies/mdm_v2/config.py`** -- Add params: `qe_floor_enabled`, `sell_acceleration_threshold`, `buy_quality_threshold`, `buy_quality_weights`
3. **`strategies/mdm_v2/mdm_v2_engine.py`** -- In `run()`:
   - After indicator computation, call `merge_liquidity(df)` to add liquidity columns
   - Pass `qe_floor` to `position_manager.process_day()` to suppress SELL
   - Compute acceleration indicators (MACD hist slope, price ROC acceleration)
   - Compute BUY quality score before entering BUY state
4. **`strategies/mdm_v2/position_manager.py`** -- Modify `process_day()` signature to accept `qe_floor`, `sell_acceleration`, `buy_quality_score`

### What stays unchanged:

- `core/indicators.py` -- Existing MACD, EMA, MA calculations are sufficient
- Data loaders -- No schema changes needed
- Performance analyzer -- Works on any engine output with `state` column
- Dashboard -- Just needs updated backtest results

## Installation

```bash
# No new packages needed. Verify existing:
uv pip list | grep -E "pandas|numpy"

# If starting fresh:
uv sync
```

## Version Compatibility

| Package | Current Minimum | Needed For This Milestone | Notes |
|---------|-----------------|---------------------------|-------|
| pandas >= 2.0.0 | `merge_asof`, `pct_change` | Both available since pandas 0.19+ | No issues |
| numpy >= 1.24.0 | Basic array ops | Available in all numpy versions | No issues |
| Python >= 3.10 | Dataclass updates, match/case if needed | Already required | No issues |

No version bumps needed.

## Sources

- [pandas merge_asof documentation](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html) -- weekly-to-daily alignment (HIGH confidence)
- [pandas resample documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.resample.html) -- alternative approach considered
- [pandas-ta momentum indicators](https://www.pandas-ta.dev/api/momentum/) -- evaluated and rejected (unnecessary dependency)
- Project files: `core/indicators.py`, `strategies/mdm_v2/config.py`, `strategies/mdm_v2/mdm_v2_engine.py`, `data/global_liquidity.csv` -- verified existing capabilities

---
*Stack research for: MDM V2 Signal Quality & Macro Filter milestone*
*Researched: 2026-03-30*
