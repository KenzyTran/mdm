# Phase 19: Global Liquidity Integration - Research

**Researched:** 2026-03-30
**Domain:** Weekly-to-daily liquidity data merge, QE floor filter for SELL suppression in MDM V2 engine
**Confidence:** HIGH

## Summary

Phase 19 integrates the pre-existing `data/global_liquidity.csv` (987 weekly rows, 2007-05-02 to 2026-03-25, all Wednesdays, no gaps) into the V2 engine to implement Dr. K's confirmed QE floor behavior: suppress CASH->SELL transitions when global liquidity is expanding. The data pipeline is straightforward -- forward-fill weekly values to daily trading dates with a publication lag offset to prevent look-ahead bias. The engine modification is surgical: a single boolean gate before the two existing CASH->SELL transitions in `V2PositionManager.process_day()`.

The highest-risk correctness issue is the publication lag offset. The CSV combines Fed WALCL (released Thursday for prior Wednesday, ~1 day lag), ECB total assets (~1-2 week lag), and BOJ total assets (~2 week lag). A 7-day minimum offset shifts each weekly observation forward by 7 days before the merge, ensuring no daily row uses data that was not yet publicly available. A configurable `publication_lag_days` parameter allows testing 7, 10, 14-day offsets.

The second critical correctness requirement is backward compatibility: with `qe_floor_enabled=False` (default), the engine must produce the exact same equity curve as the current baseline (190.8% VN30 total return +/- 0.1%). This is tested via regression test. Pre-2007 dates (NASDAQ data starts 1974) must handle NaN liquidity gracefully -- classify as NEUTRAL regime, no SELL suppression.

**Primary recommendation:** Create `strategies/mdm_v2/liquidity.py` with `LiquidityLoader` class using `pd.merge_asof(direction='backward')` with a shifted date column for publication lag. Add `qe_floor_enabled` boolean to `MDMV2Config` defaulting to `False`. Gate CASH->SELL transitions in `V2PositionManager.process_day()` when regime is EXPANDING and config flag is ON.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIQ-01 | Load global_liquidity.csv, forward-fill to daily trading dates, add qe_floor column to engine DataFrame with publication lag offset | `LiquidityLoader` class with `pd.merge_asof(direction='backward')` on lag-shifted dates; data verified: 987 weekly rows, all Wednesdays, no gaps, columns include pre-computed `qe_floor` and `liquidity_roc_20w` |
| LIQ-02 | Suppress CASH->SELL transition when QE floor ON, keep all other transitions intact | Filter-gate pattern: single boolean check before the two CASH->SELL branches in `V2PositionManager.process_day()` (line 181: MA50 breakdown, line 185: cash deterioration); all other transitions (BUY->CASH stop loss, SELL->BUY via FTD) are untouched |
| LIQ-03 | `qe_floor_enabled` flag in MDMV2Config, defaults OFF for backward compatibility | Additive dataclass field `qe_floor_enabled: bool = False` plus `publication_lag_days: int = 7` and `liquidity_csv_path: str = "data/global_liquidity.csv"` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 (installed) | `merge_asof` for weekly-to-daily alignment, DataFrame operations | Already in project; `merge_asof` is the canonical time-series forward-fill merge |
| numpy | >= 1.24.0 (installed) | NaN handling for pre-2007 dates | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 (installed via uv) | Unit tests for publication lag, regression tests | All test files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `merge_asof` | `reindex(method='ffill')` | `reindex` is simpler but creates rows for non-trading days; `merge_asof` only fills to existing daily dates -- either works since we control the target index |
| Simple `qe_floor` column from CSV | Recomputing ROC in code | CSV already has pre-computed `qe_floor` and `liquidity_roc_20w`; recomputing adds no value but adds a bug surface |

**Installation:** None required -- all dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
strategies/mdm_v2/
  liquidity.py          # NEW: LiquidityLoader + LiquidityRegime enum
  config.py             # MODIFIED: add qe_floor_enabled, publication_lag_days, liquidity_csv_path
  position_manager.py   # MODIFIED: accept liquidity_suppress_sell param in process_day()
  mdm_v2_engine.py      # MODIFIED: instantiate LiquidityLoader, merge pre-loop, pass regime to process_day()
tests/
  test_liquidity.py     # NEW: unit tests for loader, publication lag, regime classification, NaN handling
  test_qe_floor.py      # NEW: integration tests for SELL suppression, regression test for baseline
```

### Pattern 1: Publication Lag via Date Shift Before Merge
**What:** Shift the liquidity CSV dates forward by `publication_lag_days` before merging, so `merge_asof(direction='backward')` naturally picks the most recent observation that was actually published by the daily date.
**When to use:** Always -- this is the correct way to prevent look-ahead bias with lagged data.
**Example:**
```python
# Source: project research ARCHITECTURE.md + pandas merge_asof docs
def load_and_merge(self, daily_df: pd.DataFrame, publication_lag_days: int = 7) -> pd.DataFrame:
    liq = pd.read_csv(self.csv_path, parse_dates=['date'])
    liq = liq[['date', 'global_liquidity', 'liquidity_roc_20w', 'qe_floor']]

    # Shift dates forward by publication lag to prevent look-ahead
    # A Wednesday observation with 7-day lag is only "available" the following Wednesday
    liq['date'] = liq['date'] + pd.Timedelta(days=publication_lag_days)

    # merge_asof: for each daily date, find the most recent liquidity row <= that date
    daily_sorted = daily_df.sort_values('date').copy()
    merged = pd.merge_asof(
        daily_sorted,
        liq.sort_values('date'),
        on='date',
        direction='backward'
    )
    return merged
```

### Pattern 2: Filter-Gate for SELL Suppression
**What:** A boolean parameter passed to `process_day()` that prevents CASH->SELL transitions. The gate runs AFTER the existing logic determines a transition should happen but BEFORE it executes.
**When to use:** For the QE floor SELL suppression -- and later for SELL acceleration (Phase 20).
**Example:**
```python
# In V2PositionManager.process_day():
if current_state == V2MarketState.CASH:
    self.position.days_in_cash += 1

    if is_ftd:
        # BUY transition -- NOT gated by liquidity
        self.enter_buy(ftd_price, date, low, signal_type)
        action = f"BUY at {ftd_price:.2f} ({signal_type})"
    elif self.config.ma50_sell_enabled and ma50 is not None and close < ma50:
        # CASH->SELL: MA50 breakdown -- GATED by liquidity
        if not suppress_sell:
            self.enter_sell(date, f"MA50 breakdown ...")
            action = f"SELL signal: MA50 breakdown"
        else:
            action = "SELL suppressed: QE floor"
    elif self.position.days_in_cash >= self.config.cash_deterioration_days:
        # CASH->SELL: deterioration -- GATED by liquidity
        if not suppress_sell:
            self.enter_sell(date, f"Cash deterioration ...")
            action = f"SELL signal: cash deterioration"
        else:
            action = "SELL suppressed: QE floor"
```

### Pattern 3: NaN/Pre-2007 Graceful Handling
**What:** Before 2007-05-02 (first liquidity row), `merge_asof` produces NaN for liquidity columns. Classify NaN regime as NEUTRAL (no suppression).
**When to use:** Always -- NASDAQ data starts 1974, liquidity data starts 2007.
**Example:**
```python
# After merge, fill NaN regime with neutral
def compute_suppress_sell(self, row, config):
    if not config.qe_floor_enabled:
        return False
    qe_floor = row.get('qe_floor', None)
    if pd.isna(qe_floor) or qe_floor is None:
        return False  # Pre-2007: no suppression
    return bool(qe_floor == 1)
```

### Anti-Patterns to Avoid
- **Interpolating between weekly points:** Creates synthetic data that never existed and introduces look-ahead bias.
- **Using `reindex` without controlling the target dates:** Can create rows for weekends/holidays if using `pd.date_range` instead of actual trading dates.
- **Modifying the CSV's pre-computed `qe_floor` column:** The column already encodes `liquidity_roc_20w > 0`. Use it directly rather than re-implementing the threshold logic in the engine.
- **Checking `state[i]` instead of `state[i-1]` for equity calculation:** This exact bug caused 707% vs 93% equity difference in a prior milestone. The liquidity regime at day `i` affects the state transition on day `i`, and equity uses the state AFTER transition. This is correct as long as the publication lag ensures the regime value was available before day `i`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Weekly-to-daily time alignment | Custom date loop with manual ffill | `pd.merge_asof(direction='backward')` | Handles edge cases (first/last dates, unequal lengths, non-trading days) correctly |
| Publication lag offset | Custom logic to skip recent N rows | Date shift + `merge_asof` | Cleaner, testable, matches pandas idiom |
| Regime classification | Multi-threshold state machine | Pre-computed `qe_floor` column from CSV | Already computed in download script; fewer moving parts |

**Key insight:** The download script (`scripts/download_global_liquidity.py`) already computes `liquidity_roc_20w` and `qe_floor`. The engine only needs to load, lag-shift, merge, and use the pre-computed flag. Building a second regime classifier in the engine is unnecessary duplication.

## Common Pitfalls

### Pitfall 1: Look-Ahead Bias from Missing Publication Lag
**What goes wrong:** Weekly liquidity data merged without lag offset means Tuesday's trading uses Wednesday's observation that hasn't been published yet.
**Why it happens:** `merge_asof(direction='backward')` correctly picks the most recent observation <= the daily date, but if the observation date in the CSV is the measurement date (Wednesday) rather than the publication date (Thursday+), the merge is 1+ days early.
**How to avoid:** Shift all liquidity dates forward by `publication_lag_days` (default 7) before merging. Unit test: for every daily row, assert the matched liquidity date (before shift) is at least `publication_lag_days` before the daily date.
**Warning signs:** Backtests that look unrealistically good with QE floor enabled.

### Pitfall 2: Backward Compatibility Regression
**What goes wrong:** Adding liquidity columns or changing `process_day()` signature accidentally changes behavior even when `qe_floor_enabled=False`.
**Why it happens:** Python default parameter values, NaN propagation, or an if-branch that doesn't short-circuit correctly.
**How to avoid:** Regression test: run V2 engine with `qe_floor_enabled=False` on VN30 full dataset, assert total return equals 190.8% +/- 0.1%. Run this test FIRST before enabling QE floor.
**Warning signs:** Any change in trade count, signal dates, or equity curve when flag is OFF.

### Pitfall 3: NaN Crash on Pre-2007 NASDAQ Data
**What goes wrong:** Pre-2007 rows have NaN in liquidity columns. If `suppress_sell` logic doesn't handle NaN, it crashes or incorrectly suppresses/allows transitions.
**Why it happens:** `merge_asof` returns NaN when no match exists (daily date is before all liquidity dates).
**How to avoid:** Treat NaN as `qe_floor=0` (no suppression). Test with NASDAQ data from 1974 to confirm no crashes in the 1974-2007 period.
**Warning signs:** `TypeError: unsupported operand type(s)` or `ValueError` on NaN comparison.

### Pitfall 4: State[i] vs State[i-1] in Equity Calculation
**What goes wrong:** Equity curve uses the wrong day's state for P&L calculation, creating an off-by-one error that dramatically inflates or deflates returns.
**Why it happens:** This project already experienced this exact bug (707% vs 93% equity difference). When adding a new gate (SELL suppression), it's easy to miscalculate which day the suppression takes effect on.
**How to avoid:** The suppression affects the state transition decision on day `i`. Equity for day `i` uses the state AFTER the transition. This is correct. The regression test catches any error.
**Warning signs:** Equity curve deviating from baseline by more than 0.1% when QE floor is OFF.

### Pitfall 5: Excessive QE Floor Regime Changes Creating Whipsaw
**What goes wrong:** The `qe_floor` column flips frequently (66 regime changes over 19 years), potentially causing rapid SELL suppression on/off cycling.
**Why it happens:** `liquidity_roc_20w > 0` is a noisy signal near the zero crossing.
**How to avoid:** For Phase 19, accept the pre-computed `qe_floor` as-is. Document the 66 regime changes (average ~3.5/year). In Phase 22 integration, consider adding hysteresis if needed (e.g., require 2+ consecutive weeks above/below threshold).
**Warning signs:** Many "SELL suppressed" followed by "SELL signal" within a few days.

## Code Examples

### LiquidityLoader Complete Implementation
```python
# strategies/mdm_v2/liquidity.py
import pandas as pd
from enum import Enum

class LiquidityRegime(Enum):
    EXPANDING = "EXPANDING"    # QE floor ON, suppress SELL
    NEUTRAL = "NEUTRAL"        # No data or flat, no effect
    CONTRACTING = "CONTRACTING"  # Normal rules apply

class LiquidityLoader:
    """Load weekly global liquidity CSV and merge to daily trading dates."""

    def __init__(self, csv_path: str = "data/global_liquidity.csv"):
        self.csv_path = csv_path

    def load_and_merge(self, daily_df: pd.DataFrame,
                       publication_lag_days: int = 7) -> pd.DataFrame:
        """Merge weekly liquidity into daily DataFrame.

        Args:
            daily_df: DataFrame with 'date' column (daily OHLCV).
            publication_lag_days: Days to shift liquidity dates forward
                to prevent look-ahead bias. Default 7.

        Returns:
            daily_df with added columns: global_liquidity,
            liquidity_roc_20w, qe_floor.
        """
        liq = pd.read_csv(self.csv_path, parse_dates=['date'])
        liq = liq[['date', 'global_liquidity', 'liquidity_roc_20w', 'qe_floor']]

        # Apply publication lag: shift dates forward
        liq['date'] = liq['date'] + pd.Timedelta(days=publication_lag_days)
        liq = liq.sort_values('date')

        # merge_asof: for each daily date, pick most recent liquidity <= date
        merged = pd.merge_asof(
            daily_df.sort_values('date'),
            liq,
            on='date',
            direction='backward'
        )

        # NaN handling: pre-2007 dates get neutral values
        merged['qe_floor'] = merged['qe_floor'].fillna(0).astype(int)

        return merged
```

### Config Additions
```python
# In MDMV2Config dataclass -- additive fields
# Global Liquidity / QE Floor (v5.0)
qe_floor_enabled: bool = False              # Master switch, default OFF
publication_lag_days: int = 7                # Days to offset liquidity data
liquidity_csv_path: str = "data/global_liquidity.csv"
```

### Engine Wiring
```python
# In MDMV2Engine.__init__():
from .liquidity import LiquidityLoader
self.liquidity_loader = LiquidityLoader(self.config.liquidity_csv_path)

# In MDMV2Engine.run(), before the daily loop:
if self.config.qe_floor_enabled:
    df = self.liquidity_loader.load_and_merge(df, self.config.publication_lag_days)

# Inside the daily loop, before process_day():
suppress_sell = False
if self.config.qe_floor_enabled:
    qe_floor_val = row.get('qe_floor', 0)
    suppress_sell = bool(qe_floor_val == 1) if not pd.isna(qe_floor_val) else False
```

### Publication Lag Unit Test
```python
def test_publication_lag_prevents_look_ahead():
    """No daily row should use liquidity data published after that date."""
    loader = LiquidityLoader("data/global_liquidity.csv")
    daily_df = pd.DataFrame({'date': pd.date_range('2010-01-01', '2010-12-31', freq='B')})
    merged = loader.load_and_merge(daily_df, publication_lag_days=7)

    # Load raw liquidity dates (before lag shift)
    raw_liq = pd.read_csv("data/global_liquidity.csv", parse_dates=['date'])

    for _, row in merged.dropna(subset=['global_liquidity']).iterrows():
        daily_date = row['date']
        matched_liq_value = row['global_liquidity']
        # Find original date for this liquidity value
        original_row = raw_liq[raw_liq['global_liquidity'] == matched_liq_value].iloc[-1]
        original_date = original_row['date']
        # Original observation must be at least lag_days before the daily date
        assert (daily_date - original_date).days >= 7, \
            f"Look-ahead: daily {daily_date.date()} uses liquidity from {original_date.date()}"
```

### Regression Test
```python
def test_qe_floor_off_preserves_baseline():
    """With qe_floor_enabled=False, V2 equity must match 190.8% baseline."""
    from strategies.mdm_v2.config import MDMV2Config
    from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
    from core.data_loader import DataLoader

    config = MDMV2Config(qe_floor_enabled=False)
    engine = MDMV2Engine(config)
    loader = DataLoader('vn30')
    df = loader.load()
    results = engine.run(df)

    # Calculate total return from equity curve
    # ... (use existing V2PerformanceAnalyzer)
    total_return = ...  # Should be ~190.8%
    assert abs(total_return - 190.8) < 0.1, \
        f"Regression: expected 190.8% +/- 0.1%, got {total_return:.1f}%"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FRED API live download | Pre-downloaded CSV (`scripts/download_global_liquidity.py`) | Already done | No network dependency during backtesting |
| Complex regime HMM | Simple `liquidity_roc_20w > 0` threshold | Research decision | Only 3 QE cycles in 18 years -- HMM would overfit |
| Hybrid two-phase snapshot | Direct filter-gate in V2 | v5.0 design | Simpler than v3.0 Hybrid approach; V2 is modified directly |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None (default discovery) |
| Quick run command | `uv run pytest tests/test_liquidity.py tests/test_qe_floor.py -x -v` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIQ-01 | Weekly CSV loads, forward-fills to daily, publication lag prevents look-ahead | unit | `uv run pytest tests/test_liquidity.py -x` | Wave 0 |
| LIQ-01 | NaN/neutral regime for pre-2007 dates | unit | `uv run pytest tests/test_liquidity.py::test_pre2007_nan_handling -x` | Wave 0 |
| LIQ-02 | CASH->SELL suppressed when QE floor ON | integration | `uv run pytest tests/test_qe_floor.py::test_sell_suppressed_during_qe -x` | Wave 0 |
| LIQ-02 | Other transitions (BUY->CASH, SELL->BUY) unaffected | integration | `uv run pytest tests/test_qe_floor.py::test_other_transitions_unaffected -x` | Wave 0 |
| LIQ-03 | qe_floor_enabled=False produces identical baseline | regression | `uv run pytest tests/test_qe_floor.py::test_baseline_regression -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_liquidity.py tests/test_qe_floor.py -x -v`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_liquidity.py` -- covers LIQ-01 (loader, merge, lag, NaN)
- [ ] `tests/test_qe_floor.py` -- covers LIQ-02 (SELL suppression), LIQ-03 (regression baseline)

## Open Questions

1. **Optimal publication lag days**
   - What we know: Fed WALCL releases Thursday for prior Wednesday (1-day lag). ECB/BOJ have 1-2 week lag. Combined figure uses `merge_asof(direction='backward')` which already picks the most recent available, so the lag in the CSV reflects the slowest component.
   - What's unclear: Whether 7 days is sufficient or 14 days is more realistic for the combined global figure.
   - Recommendation: Default to 7 days (minimum requirement from success criteria). Test with 7, 10, 14 and compare -- if results are insensitive to lag choice, 7 is fine.

2. **QE floor regime change frequency**
   - What we know: 66 regime changes in 19 years (~3.5/year). Some periods have rapid on/off cycling (e.g., 2009-2010 had 7 changes in 15 months).
   - What's unclear: Whether rapid cycling causes SELL suppression whipsaw that traps capital.
   - Recommendation: Implement as-is for Phase 19. Track CASH duration with QE floor ON vs OFF. Address in Phase 22 integration if needed (hysteresis filter).

## Data Inventory

| Data Source | File | Rows | Date Range | Frequency | Status |
|-------------|------|------|------------|-----------|--------|
| Global Liquidity | `data/global_liquidity.csv` | 987 | 2007-05-02 to 2026-03-25 | Weekly (Wednesdays) | Ready |
| NASDAQ OHLCV | `data/NASDAQ.csv` | 13,317 | 1973-06-01 to 2026-03-26 | Daily | Ready |
| VN30 OHLCV | `data/vn30.csv` | 3,762 | 2011-03-01 to 2026-03-27 | Daily | Ready |

**Key data facts:**
- Liquidity CSV has no gaps (all 987 rows are exactly 7 days apart, all Wednesdays)
- Pre-computed columns: `global_liquidity`, `liquidity_roc_20w`, `qe_floor` (1 = expanding, 0 = not)
- First 20 rows have NaN in `liquidity_roc_20w` (warm-up period for 20-week ROC), but `qe_floor` is already 0 for those
- QE floor distribution: 654 weeks ON (66%), 333 weeks OFF (34%)
- NASDAQ has 34 years of data before first liquidity point (1973-2007) -- requires NaN handling

## Sources

### Primary (HIGH confidence)
- Project codebase: `strategies/mdm_v2/position_manager.py` -- CASH->SELL transitions at lines 181, 185
- Project codebase: `strategies/mdm_v2/config.py` -- MDMV2Config dataclass pattern
- Project codebase: `scripts/download_global_liquidity.py` -- data source, column definitions
- `data/global_liquidity.csv` -- verified 987 rows, weekly Wednesdays, columns confirmed
- `.planning/research/ARCHITECTURE.md` -- filter-gate pattern, LiquidityLoader code sample
- `.planning/research/SUMMARY.md` -- pitfall analysis, state[i] bug history
- pandas `merge_asof` documentation -- canonical forward-fill merge pattern

### Secondary (MEDIUM confidence)
- [FRED WALCL series page](https://fred.stlouisfed.org/series/WALCL) -- H.4.1 release schedule (Thursday for prior Wednesday)
- Project `.planning/research/PITFALLS.md` -- publication lag analysis, state contamination risks

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns verified in codebase
- Architecture: HIGH -- filter-gate pattern fully specified in project research, code samples available
- Pitfalls: HIGH -- two pitfalls based on documented project bugs (state[i] error, hybrid engine failure)
- Data: HIGH -- CSV verified with exact row counts, date ranges, column contents

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable -- no fast-moving dependencies)
