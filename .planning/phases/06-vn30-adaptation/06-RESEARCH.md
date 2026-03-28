# Phase 6: VN30 Adaptation - Research

**Researched:** 2026-03-28
**Domain:** VN30 market microstructure adaptation + parameter recalibration for MDM v2
**Confidence:** HIGH

## Summary

Phase 6 adapts the MDM v2 engine (built in Phase 4, validated in Phase 5) to the Vietnamese VN30 market. The engine itself is market-agnostic -- it processes OHLCV DataFrames and produces BUY/CASH/SELL signals. The adaptation work is therefore NOT engine modification but rather: (1) a pre-processing filter module that annotates the DataFrame with VN30-specific columns before the engine runs, (2) a Sharpe-optimized parameter sweep replacing the match-rate sweep used for NASDAQ, and (3) a backtest reporting script following the Phase 5 `validate_v2.py` pattern but comparing against VN30 buy-and-hold instead of published signals.

The VN30 data spans 2011-03-01 to 2026-03-27 (3,762 rows). VN30 daily volatility (std 1.21%) is comparable to NASDAQ but with a distinct regime shift post-2020 (1.08% pre vs 1.39% post). The 7% price limit is per-stock on HOSE, so the VN30 index itself never hits exactly 7% (max observed: +6.90%, -6.81%). Limit-day detection on the index uses a threshold approach. Derivative expiry on the 3rd Thursday of each month is confirmed by exchange specifications.

**Primary recommendation:** Build `strategies/mdm_v2/vn30_filters.py` as a stateless DataFrame annotator, adapt `parameter_sweep.py` to accept a `scoring_fn` parameter, then create `analysis/sweep_vn30.py` and `analysis/backtest_vn30.py` following established project patterns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Flag 7% limit-up/limit-down days with a boolean column (`is_limit_day`) but do NOT filter or suppress signals on those days. Let the parameter sweep decide if they matter.
- **D-02:** FTD signals on limit-up days are valid and not suppressed -- the 7% cap doesn't invalidate buying pressure.
- **D-03:** Limit day detection logic lives in a new VN30 microstructure module at `strategies/mdm_v2/vn30_filters.py`, not in the shared data loader.
- **D-04:** T+2.5 settlement delay is ignored in the backtest. MDM is a daily-bar signal model -- settlement is a real-world execution constraint, not a signal quality factor.
- **D-05:** Distribution day counting is suppressed on derivative expiry days. Elevated volume on expiry is structural, not distribution.
- **D-06:** Derivative expiry dates (3rd Thursday of each month) are computed algorithmically in `vn30_filters.py` -- no external CSV maintenance required.
- **D-07:** Fresh grid sweep over VN30 data using Phase 4's parameter_sweep.py framework. NASDAQ params may not transfer -- VN30 has different volatility/volume characteristics.
- **D-08:** Sweep optimizes for Sharpe ratio (risk-adjusted return), not signal match rate. No published VN30 signals exist as a benchmark.
- **D-09:** Adapt existing `analysis/hypothesis/parameter_sweep.py` to accept a scoring function (match_rate OR Sharpe). New VN30 sweep script at `analysis/sweep_vn30.py`.
- **D-10:** Use full available VN30 data range (2014-2026 from `data/vn30.csv`). Maximizes training data.
- **D-11:** Train/test split at pre/post-2020. Train sweep on pre-2020 data, validate on 2020-2026. COVID regime shift tests parameter robustness.
- **D-12:** Compare against VN30 buy-and-hold baseline only. VSA strategy comparison is apples-to-oranges due to multi-stock approach.

### Claude's Discretion
- Exact parameter grid ranges and step sizes for VN30 sweep
- VN30 backtest report format and chart layout (follow Phase 5 patterns)
- Internal implementation of vn30_filters.py helper functions
- How to handle edge cases in expiry date computation (holidays, etc.)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VN30-01 | Market microstructure adjustments for 7% daily price limit, T+2.5 settlement, derivative expiry filtering | vn30_filters.py module with `is_limit_day`, `is_expiry_day` columns; T+2.5 ignored per D-04; DD suppression on expiry per D-05 |
| VN30-02 | MDM v2 parameters recalibrated for VN30 market characteristics | Sharpe-optimized grid sweep via adapted parameter_sweep.py; train pre-2020, validate post-2020 |
| VN30-03 | Full VN30 backtest with performance report and comparison vs buy-and-hold | backtest_vn30.py following validate_v2.py pattern; V2PerformanceAnalyzer reused directly |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, time series | Already in project; all data processing uses it |
| numpy | >= 1.24.0 | Numerical calculations | Already in project; performance metrics use it |
| matplotlib | >= 3.7.0 | Dashboard chart generation | Already in project; Phase 5 dashboard pattern |

### Supporting
No new libraries needed. All work uses existing project dependencies.

### Alternatives Considered
None -- this phase uses only existing project libraries. No new dependencies.

## Architecture Patterns

### Recommended Project Structure
```
strategies/mdm_v2/
    vn30_filters.py          # NEW: VN30 microstructure annotations
    config.py                # UNCHANGED: MDMV2Config (same params, different values)
    mdm_v2_engine.py         # UNCHANGED: engine is market-agnostic
    performance.py           # UNCHANGED: V2PerformanceAnalyzer reused directly
    distribution_day.py      # UNCHANGED: but DD suppression needs integration point

analysis/
    hypothesis/
        parameter_sweep.py   # MODIFIED: accept scoring_fn parameter
        hypothesis_runner.py # UNCHANGED
    sweep_vn30.py            # NEW: VN30 Sharpe-optimized parameter sweep
    backtest_vn30.py         # NEW: VN30 backtest + report generation

tests/
    test_vn30_filters.py     # NEW: unit tests for microstructure module
    test_vn30_sweep.py       # NEW: integration test for Sharpe sweep
```

### Pattern 1: DataFrame Annotation Pipeline
**What:** `vn30_filters.py` adds columns to the DataFrame without modifying existing columns. The engine reads these columns (or ignores them if absent).
**When to use:** Pre-processing market-specific adjustments before passing to the market-agnostic engine.
**Example:**
```python
# vn30_filters.py
def add_limit_day_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add is_limit_day boolean column based on intraday range vs prev_close.

    For VN30 index: flags days where high or low approaches the 7%
    theoretical maximum (threshold: >=6.5% from previous close).
    Index rarely hits exactly 7% since not all 30 stocks hit limit simultaneously.
    """
    df = df.copy()
    df['prev_close'] = df['close'].shift(1)
    df['high_pct'] = (df['high'] - df['prev_close']) / df['prev_close']
    df['low_pct'] = (df['low'] - df['prev_close']) / df['prev_close']
    df['is_limit_day'] = (df['high_pct'] >= 0.065) | (df['low_pct'] <= -0.065)
    # Clean up temp columns
    df = df.drop(columns=['high_pct', 'low_pct'], errors='ignore')
    return df

def add_expiry_day_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add is_expiry_day boolean column for 3rd Thursday of each month."""
    df = df.copy()
    # Compute 3rd Thursday for each month
    df['is_expiry_day'] = df['date'].apply(_is_third_thursday)
    return df

def _is_third_thursday(dt) -> bool:
    """Check if date is the 3rd Thursday of its month."""
    if dt.weekday() != 3:  # Thursday
        return False
    # 3rd Thursday falls on days 15-21
    return 15 <= dt.day <= 21

def apply_vn30_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all VN30 microstructure filters as a single pipeline."""
    df = add_limit_day_column(df)
    df = add_expiry_day_column(df)
    return df
```

### Pattern 2: Scoring Function Abstraction for Parameter Sweep
**What:** Modify `parameter_sweep.py` to accept an optional `scoring_fn` callable. Default remains match-rate for backward compatibility. VN30 sweep passes a Sharpe-scoring function.
**When to use:** When the sweep needs to optimize for different objectives depending on the market.
**Example:**
```python
# In parameter_sweep.py - modified run_sweep signature:
def run_sweep(
    df: pd.DataFrame,
    published_signals: pd.DataFrame = None,  # Optional for Sharpe mode
    param_grid: Dict[str, List[Any]] = None,
    top_n: int = 10,
    scoring_fn=None,  # NEW: callable(config, df) -> dict with 'score' key
) -> pd.DataFrame:
    ...

# In sweep_vn30.py - the Sharpe scoring function:
def sharpe_scoring_fn(config: MDMV2Config, df: pd.DataFrame) -> dict:
    """Score a config by Sharpe ratio on VN30 data."""
    engine = MDMV2Engine(config)
    results = engine.run(df)
    analyzer = V2PerformanceAnalyzer(results, engine.get_trades())
    return {
        'score': analyzer.sharpe_ratio(),
        'total_return': analyzer.total_return(),
        'max_drawdown': analyzer.max_drawdown(),
        'win_rate': analyzer.win_rate(),
    }
```

### Pattern 3: DD Suppression on Expiry Days
**What:** The engine's distribution day counting must skip expiry days. The cleanest approach is to zero out `volume_up` on expiry days in the pre-processed DataFrame, preventing DD detection without modifying the engine.
**When to use:** When structural volume spikes should not count as distribution.
**Example:**
```python
# In vn30_filters.py or the sweep script, BEFORE engine.run():
def suppress_dd_on_expiry(df: pd.DataFrame) -> pd.DataFrame:
    """Set volume_up to False on expiry days to suppress DD counting.

    Per D-05: elevated volume on derivative expiry is structural, not distribution.
    This prevents the DD counter from firing on these days without modifying the engine.
    """
    # Note: volume_up is computed by the engine's Indicators.add_change_columns()
    # We need to either: (a) modify the engine to check is_expiry_day, or
    # (b) post-process after indicators but before DD counting.
    # Option (b) requires engine modification. Option (a) is cleaner.
    # RECOMMENDED: Add is_expiry_day check in the engine's DD counting section.
    pass
```

**Important design choice:** DD suppression on expiry days (D-05) cannot be achieved purely through pre-processing because `volume_up` is computed inside the engine by `Indicators.add_change_columns()`. Two options:

1. **Modify the engine's main loop** (in `mdm_v2_engine.py`): Add an `is_expiry_day` check before calling `dd_counter.check_distribution_day()`. This is a 3-line change.
2. **Post-process after indicator computation**: After `Indicators.add_change_columns(df)` but before the main loop, override `volume_up = False` on expiry days.

**Recommendation:** Option 2 -- insert the override in the engine's `run()` method after indicator columns are computed but before the main loop. This keeps the DD counter logic unchanged. The engine already has an `is_expiry_day` column available from vn30_filters pre-processing, and can conditionally apply the override. This is the least-invasive approach.

### Anti-Patterns to Avoid
- **Modifying the engine's core signal logic for VN30:** The engine must remain market-agnostic. VN30 adjustments go in the filter module or the DataFrame pre-processing step.
- **Hardcoding VN30 date ranges:** Use the data's actual date range, not hardcoded years. The DataLoader already handles this.
- **Using calendar days for train/test split instead of trading dates:** The data has trading dates only; filter on dates, not row counts.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Equity curve computation | Custom P&L tracker | `V2PerformanceAnalyzer` | Already handles BUY/CASH/SELL states correctly |
| Buy-and-hold comparison | Custom baseline | `_compute_buy_and_hold_metrics()` from `validate_v2.py` | Already tested, handles edge cases |
| Parameter grid search | Custom loop | `parameter_sweep.py` (adapted) | Handles progress reporting, result formatting |
| Data loading | Raw CSV parsing | `DataLoader('vn30')` | Column mapping, date parsing, type conversion |
| Dashboard chart | Custom matplotlib | Follow `generate_dashboard()` pattern from `validate_v2.py` | Consistent output format |

**Key insight:** Phase 5 built the entire performance analysis and reporting infrastructure. Phase 6 reuses it directly for VN30, changing only the data source and optimization objective.

## Common Pitfalls

### Pitfall 1: Third Thursday Holiday Collision
**What goes wrong:** The 3rd Thursday of a month may be a Vietnamese public holiday, so the actual expiry moves to the preceding trading day.
**Why it happens:** Vietnam has ~10 public holidays per year (Tet, National Day, etc.) that occasionally fall on Thursdays.
**How to avoid:** The `_is_third_thursday()` function should check if the date exists in the VN30 data. If the computed 3rd Thursday is NOT a trading day in the DataFrame, fall back to the preceding trading day. The DataFrame itself serves as the holiday calendar.
**Warning signs:** An expiry day flagged in `is_expiry_day` that does not appear in the data's date column.

### Pitfall 2: Pre-2020 Data Sparsity in Early Years
**What goes wrong:** VN30 data from 2011-2013 has lower liquidity and the early rows (2011) show OHLC all equal (e.g., open=high=low=close=472.52), suggesting the index was newly launched.
**Why it happens:** VN30 was created in Feb 2012; early 2011 data may be synthetic or low-quality.
**How to avoid:** Per D-10, use data from 2014 onward, which avoids the low-quality early period. The data loader's `start_date` parameter handles this.
**Warning signs:** Rows where open=high=low=close (zero intraday range) in the early data period.

### Pitfall 3: Sharpe Overfitting on Training Period
**What goes wrong:** The sweep finds parameters that produce a great Sharpe on pre-2020 data but collapse post-2020 due to the volatility regime shift (1.08% to 1.39% daily std).
**Why it happens:** VN30 had a massive COVID crash and then a speculative bubble in 2021, fundamentally different from pre-2020.
**How to avoid:** The train/test split at 2020 (D-11) specifically tests for this. Report train AND test Sharpe side-by-side. A large gap indicates overfitting.
**Warning signs:** Train Sharpe > 2.0 with test Sharpe < 0.5.

### Pitfall 4: Volume Characteristics Differ Between Markets
**What goes wrong:** NASDAQ-calibrated volume thresholds for DD detection may fire too frequently or too rarely on VN30.
**Why it happens:** VN30 volume patterns differ -- derivative expiry causes structural volume spikes, and the T+2.5 settlement creates different trading dynamics.
**How to avoid:** The parameter sweep will naturally find appropriate DD thresholds for VN30. The expiry-day DD suppression (D-05) prevents false positives from structural volume.
**Warning signs:** DD count consistently at 0 (thresholds too tight) or constantly at maximum (too loose).

### Pitfall 5: Engine Modification for Expiry DD Suppression
**What goes wrong:** Modifying the engine's DD counting logic to check `is_expiry_day` works for VN30 but breaks NASDAQ runs where the column doesn't exist.
**Why it happens:** The engine is shared between markets but `is_expiry_day` only exists after VN30 filtering.
**How to avoid:** Guard with `if 'is_expiry_day' in df.columns` before checking the flag. If the column is absent, no suppression occurs (NASDAQ behavior preserved).
**Warning signs:** KeyError on `is_expiry_day` when running NASDAQ backtest after the change.

## Code Examples

### VN30 Parameter Grid (Recommended Starting Ranges)

Based on VN30 volatility analysis (avg daily move 0.86%, std 1.21%):

```python
# VN30-specific grid - wider ranges than NASDAQ due to different volatility
VN30_PARAM_GRID = {
    # Correction threshold: VN30 has bigger swings, try wider range
    'correction_threshold': [-0.06, -0.08, -0.10, -0.12, -0.15],
    # FTD minimum rally day: keep similar to NASDAQ
    'ftd_min_rally_day': [3, 4, 5],
    # FTD minimum price gain: VN30 avg daily move is 0.86%, so lower gains may be meaningful
    'ftd_min_price_gain': [0.005, 0.008, 0.01, 0.012, 0.015],
    # DD cash threshold: may need higher for VN30 due to more volatile volume
    'dd_cash_threshold': [3, 4, 5, 6],
    # Stop loss: VN30 more volatile, may need wider stops
    'stop_loss_pct': [0.02, 0.025, 0.03, 0.04],
    # DD window: standard and wider
    'dd_window_size': [15, 20, 25],
}
# Total combinations: 5 * 3 * 5 * 4 * 4 * 3 = 3,600
```

### Sharpe Scoring Function

```python
def sharpe_score(config: MDMV2Config, df: pd.DataFrame) -> dict:
    """Run engine with config and return Sharpe-based score dict."""
    engine = MDMV2Engine(config)
    results = engine.run(df)
    trades = engine.get_trades()
    analyzer = V2PerformanceAnalyzer(results, trades)

    return {
        'score': analyzer.sharpe_ratio(),
        'sharpe_ratio': analyzer.sharpe_ratio(),
        'total_return': analyzer.total_return(),
        'max_drawdown': analyzer.max_drawdown(),
        'win_rate': analyzer.win_rate(),
        'annualized_return': analyzer.annualized_return(),
        'num_trades': len([t for t in trades if t['type'] == 'CASH_EXIT']),
    }
```

### VN30 Backtest Report Script Pattern

```python
# analysis/backtest_vn30.py - follows validate_v2.py pattern
# Key differences from NASDAQ validation:
# 1. No published signals to compare -- no match_rate section
# 2. Only two strategies: MDM v2 vs buy-and-hold (no classic comparison)
# 3. Train/test split at 2020 instead of 2022
# 4. Dashboard shows VN30 price, not NASDAQ

TRAIN_END = '2019-12-31'
TEST_START = '2020-01-01'
DATA_START = '2014-01-01'
WARMUP_START = '2012-01-01'  # 2 years warm-up for MA50
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Match-rate scoring only | Sharpe-based scoring option | Phase 6 | Enables optimization without published signals |
| NASDAQ-only engine | Market-agnostic engine + market-specific filters | Phase 6 | Engine unchanged; filters handle market specifics |
| No microstructure awareness | VN30 price limit + expiry day annotations | Phase 6 | Prevents false DD signals from structural volume |

## Open Questions

1. **Limit day threshold for VN30 index**
   - What we know: The 7% limit applies per-stock, not the index. Index max observed is 6.90%. Days where high or low >= 6.5% from prev close are rare (7 total in 15 years).
   - What's unclear: Whether 6.5% is the right threshold, or whether a different threshold (e.g., 6.0%) captures more meaningful days.
   - Recommendation: Use 6.5% as the threshold since it matches within 0.5% of the theoretical 7% cap. The column is informational only (D-01: signals are NOT suppressed), so the exact threshold matters less.

2. **Holiday-adjusted expiry dates**
   - What we know: 3rd Thursday rule is confirmed by exchange specifications. Vietnam has ~10 public holidays per year.
   - What's unclear: Exact list of holidays over 2014-2026 that fell on the 3rd Thursday.
   - Recommendation: Use the DataFrame's trading dates as the holiday calendar -- if the computed 3rd Thursday is not a trading day, use the preceding trading day in the data.

3. **Warm-up period for VN30**
   - What we know: Engine needs MA50 (50 trading days) warm-up. Data starts 2011 but quality improves from 2014.
   - What's unclear: Whether starting from 2012 provides enough warm-up before the 2014 analysis start.
   - Recommendation: Load from 2012-01-01 for warm-up, analyze from 2014-01-01 onward. This gives 2 full years of MA50 warm-up.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 (via uv dev-dependencies) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_vn30_filters.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VN30-01 | Limit day detection flags correct days | unit | `uv run pytest tests/test_vn30_filters.py::test_limit_day_detection -x` | Wave 0 |
| VN30-01 | Expiry day computation matches 3rd Thursday | unit | `uv run pytest tests/test_vn30_filters.py::test_expiry_day_computation -x` | Wave 0 |
| VN30-01 | DD suppressed on expiry days | unit | `uv run pytest tests/test_vn30_filters.py::test_dd_suppression_on_expiry -x` | Wave 0 |
| VN30-02 | Sweep completes and returns ranked results with Sharpe scores | integration | `uv run pytest tests/test_vn30_sweep.py::test_sharpe_sweep_runs -x` | Wave 0 |
| VN30-02 | Parameter sweep scoring_fn abstraction works for both Sharpe and match_rate | unit | `uv run pytest tests/test_vn30_sweep.py::test_scoring_fn_abstraction -x` | Wave 0 |
| VN30-03 | Backtest produces equity curve, drawdown, Sharpe, win rate | integration | `uv run pytest tests/test_vn30_sweep.py::test_backtest_report_metrics -x` | Wave 0 |
| VN30-03 | Buy-and-hold comparison included in report | integration | `uv run pytest tests/test_vn30_sweep.py::test_buy_and_hold_comparison -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_vn30_filters.py tests/test_vn30_sweep.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_vn30_filters.py` -- covers VN30-01 (limit day, expiry day, DD suppression)
- [ ] `tests/test_vn30_sweep.py` -- covers VN30-02, VN30-03 (Sharpe sweep, backtest report)

## Sources

### Primary (HIGH confidence)
- Project codebase: `strategies/mdm_v2/mdm_v2_engine.py` -- engine is market-agnostic, takes OHLCV DataFrame
- Project codebase: `strategies/mdm_v2/performance.py` -- V2PerformanceAnalyzer with Sharpe, drawdown, equity curve
- Project codebase: `analysis/hypothesis/parameter_sweep.py` -- grid search framework, match-rate scoring
- Project codebase: `analysis/validate_v2.py` -- Phase 5 validation pattern (CSV + PNG + text output)
- Project codebase: `core/data_loader.py` -- DataLoader('vn30') loads VN30 at native scale
- VN30 data analysis: 3,762 rows, 2011-2026, daily vol 1.21%, max move +6.90%/-6.81%

### Secondary (MEDIUM confidence)
- [Pinetree Securities VN30 Futures](https://pinetree.vn/en/post/derivative_offer/futures-contracts-on-vn30-index/) -- confirms 3rd Thursday expiry rule
- [MASVN VN30 Futures](https://www.masvn.com/en/article/vn30-index-future-1553) -- confirms expiry falls back to previous trading day on holidays
- [The Vietnam Yield Stock Market Guide](https://thevietnamyield.com/the-ultimate-guide-to-investing-in-vietnam-stock-market/) -- confirms 7% HOSE daily price limit

### Tertiary (LOW confidence)
- None -- all findings verified against project code or official exchange sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, reuses existing project infrastructure entirely
- Architecture: HIGH -- patterns directly follow Phase 4/5 established code; engine is verified market-agnostic
- Pitfalls: HIGH -- VN30 data analysis confirms volatility characteristics, limit day frequency, and expiry day patterns from actual data

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable -- VN30 market microstructure rules change infrequently)
