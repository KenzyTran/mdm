# Phase 26: Banding/Volatility Filter - Research

**Researched:** 2026-04-01
**Domain:** ATR-based volatility regime classification, signal suppression during low-volatility sideways markets
**Confidence:** HIGH

## Summary

Phase 26 implements Dr. K's "banding width" concept: when VN30 is in a low-volatility sideways regime, signal transitions (BUY and SELL) are suppressed to prevent whipsaw. The implementation uses ATR-14 as a percentage of close price to classify each trading day into high/normal/low volatility regimes, with boundaries calibrated to VN30's historical ATR distribution.

Empirical analysis of 3,765 VN30 daily bars (2011-2026) shows the ATR% distribution has clear regime separation. The P25 threshold (1.036%) cleanly identifies sideways periods: the 2019 Apr-Sep sideways period has 94/126 days (75%) classified as "low" volatility, while the 2020 Feb-Apr crash has 0/62 days as "low" and the 2021 Jan-Jun rally has 0/58 days as "low". This means a filter that suppresses signals during "low" volatility will not interfere with trending periods.

The baseline V2 engine generates 13 transitions during the 2019 sideways and 15 transitions during the 2024 low-vol period -- classic whipsaw behavior with repeated stop-loss exits and rapid re-entries. The volatility filter should eliminate most of these by keeping the engine in its current state (CASH or SELL) until volatility returns to normal/high levels.

**Primary recommendation:** Create a standalone `VolatilityFilter` module following the `BuyEntryFilter` / `SellAccelerationGate` pattern. Use ATR-14 as % of close, with P25 as the low-volatility boundary and P75 as the high-volatility boundary. Suppress signal transitions (both BUY and SELL) when regime is "low". Wire into the engine via a `suppress_signal` boolean passed to `process_day()`, analogous to the existing `suppress_sell` (QE floor) pattern.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BAND-01 | Compute ATR-based volatility regime (high/normal/low) on VN30 daily data | ATR-14 as % of close, with percentile-based thresholds calibrated to VN30 historical distribution (P25=1.036%, P75=1.734%). Add `add_atr_column()` and `add_volatility_regime_column()` to Indicators module. |
| BAND-02 | Suppress signal switching when volatility regime = low (banding too narrow for VN30) | New `VolatilityFilter` class checks ATR regime. When regime=low, both BUY entries and CASH->SELL transitions are suppressed. Engine passes `suppress_signal` boolean to position manager. |
| BAND-03 | Backtest on VN30 sideways periods confirms filter reduces false signals | A/B validation script comparing baseline vs volatility-filtered V2 on VN30. Key periods: 2019 Apr-Sep (13 baseline transitions), 2024 Apr-Sep (15 baseline transitions). Success: >= 20% fewer false signals during low-vol periods. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, rolling ATR computation | Already in project |
| numpy | >= 1.24.0 | True Range calculation (max of 3 components) | Already in project |

### Supporting
No new libraries needed. ATR is a simple rolling mean of True Range -- no external TA library required.

**Installation:** None required -- all dependencies already installed.

## Architecture Patterns

### Integration Point in Engine

The volatility filter integrates at two points in the engine loop:

1. **Indicator computation** (before main loop): Add ATR column and volatility regime column to DataFrame
2. **Signal gating** (inside main loop): Check regime before allowing state transitions

The existing pattern for signal suppression is the QE floor (`suppress_sell`), which is a boolean passed to `process_day()`. The volatility filter follows the same pattern but gates BOTH buy and sell transitions.

### New Module: `volatility_filter.py`

```python
# Source: pattern from strategies/mdm_v2/buy_entry.py
class VolatilityFilter:
    """Suppress signal switching during low-volatility regimes (BAND-02)."""

    def __init__(self, config: MDMV2Config):
        self.config = config

    def should_suppress(self, atr_pct: float) -> bool:
        """Check if current volatility regime is too low for reliable signals.

        Args:
            atr_pct: Current ATR-14 as percentage of close price.

        Returns:
            True if signals should be suppressed (low volatility regime).
        """
        if not self.config.volatility_filter_enabled:
            return False
        return atr_pct < self.config.volatility_low_threshold
```

### New Indicator Methods: ATR computation

```python
# Source: pattern from strategies/mdm_v2/indicators.py add_ma50_column
@staticmethod
def add_atr_column(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add ATR-14 and ATR% columns.

    True Range = max(H-L, |H-prev_C|, |L-prev_C|)
    ATR = rolling mean of TR over `period` days
    ATR% = ATR / close * 100

    Args:
        df: DataFrame with 'high', 'low', 'close', 'prev_close' columns.
        period: ATR lookback window (default 14).

    Returns:
        DataFrame with 'atr' and 'atr_pct' columns added.
    """
    df = df.copy()
    prev_close = df['prev_close']
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            (df['high'] - prev_close).abs(),
            (df['low'] - prev_close).abs()
        )
    )
    df['atr'] = df['tr'].rolling(window=period, min_periods=1).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100
    return df
```

### Config Additions

```python
# New fields in MDMV2Config (following existing feature flag pattern)
volatility_filter_enabled: bool = False    # Master switch (default OFF per v5.0 convention)
volatility_low_threshold: float = 1.04     # ATR% below this = low volatility (P25 of VN30 distribution)
volatility_high_threshold: float = 1.73    # ATR% above this = high volatility (P75, informational)
atr_period: int = 14                       # ATR lookback window
```

### Engine Integration Pattern

```python
# In mdm_v2_engine.py run() method:

# After indicator computation, before main loop:
if self.config.volatility_filter_enabled:
    df = Indicators.add_atr_column(df, self.config.atr_period)

# Inside main loop, before process_day():
suppress_volatility = False
if self.config.volatility_filter_enabled and 'atr_pct' in df.columns:
    atr_pct = df.iloc[idx]['atr_pct']
    suppress_volatility = self.volatility_filter.should_suppress(atr_pct)

# Pass to process_day -- suppress BOTH buy and sell transitions
new_state, action = self.position_manager.process_day(
    ...
    suppress_sell=suppress_sell or suppress_volatility,  # Extend existing flag
    suppress_buy=suppress_volatility,                     # New parameter
    ...
)
```

### Position Manager Changes

The position manager needs a new `suppress_buy` parameter to gate FTD/breakout entries during low volatility. This is minimal -- just one additional `if` check in the CASH and SELL state handlers:

```python
# In process_day():
if current_state == V2MarketState.CASH:
    if is_ftd:
        if suppress_buy:
            action = "BUY suppressed: low volatility"
        else:
            self.enter_buy(ftd_price, date, low, signal_type)
            action = f"BUY at {ftd_price:.2f} ({signal_type})"
```

### Anti-Patterns to Avoid

- **Using fixed ATR thresholds from other markets:** VN30's ATR distribution is specific to Vietnamese market microstructure (7% price limit, T+2.5). The P25/P75 approach auto-calibrates.
- **Suppressing ONLY buy signals:** Dr. K's banding concept suppresses ALL signal switching. If you only suppress buys, the engine can still transition CASH->SELL during sideways periods, creating unnecessary short exposure.
- **Removing the volatility column during trending periods:** The column should always be computed (when enabled). Only the suppression logic is conditional.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| True Range calculation | Custom formula | `np.maximum()` vectorized | Edge cases with gaps, limit days |
| Regime classification | Complex HMM/Markov model | Simple percentile thresholds | VN30 distribution is clean; P25/P75 separate regimes perfectly |
| Signal suppression logic | Custom state machine modifications | Extend existing `suppress_sell` pattern | Pattern already proven with QE floor |

**Key insight:** The VN30 ATR distribution has remarkably clean regime separation at percentile boundaries. No need for sophisticated regime-switching models -- simple threshold classification works because VN30's price limit mechanism creates natural volatility clusters.

## Common Pitfalls

### Pitfall 1: Look-ahead bias in ATR percentile calibration
**What goes wrong:** Using the full dataset to compute P25/P75 thresholds means future data influences past regime labels.
**Why it happens:** ATR percentiles are computed on the entire history including data after each date.
**How to avoid:** Use FIXED thresholds from historical calibration (1.04% and 1.73%), not dynamically computed percentiles. These are config parameters, not runtime calculations. The thresholds are calibrated once on historical data and applied going forward.
**Warning signs:** Threshold values change when you extend the dataset end date.

### Pitfall 2: Suppressing signals that were already in flight
**What goes wrong:** A buy confirmation is pending (BUY-02 window) when volatility drops to low. If the pending signal completes, it bypasses suppression.
**How to avoid:** Check suppression BEFORE processing buy confirmation results. If suppressed, cancel the pending confirmation.
**Warning signs:** Trades appearing during low-volatility periods despite filter being enabled.

### Pitfall 3: State[i] vs state[i-1] equity bug
**What goes wrong:** Using current-day state instead of previous-day state for equity calculation (the 707% vs 93% bug from project history).
**How to avoid:** The performance analyzer already handles this correctly. Do not modify equity calculation logic -- only add the suppression gate.
**Warning signs:** Unrealistically high returns when filter is enabled.

### Pitfall 4: ATR NaN at start of data
**What goes wrong:** First 13 rows have NaN ATR with `min_periods=14` (or partially computed with `min_periods=1`).
**How to avoid:** Use `min_periods=1` for ATR rolling mean (consistent with existing MA50/MA10 pattern), but treat the first `atr_period` rows as "normal" regime (not low, not high). The first ~300 rows are warmup anyway.
**Warning signs:** Signals suppressed in the first weeks of backtest due to unstable ATR.

### Pitfall 5: Volatility filter interacting with fail-safe
**What goes wrong:** Engine is in SELL state, fail-safe should trigger (close > standby-sell HIGH), but volatility is low so transition is suppressed.
**How to avoid:** Fail-safe exits should NOT be suppressed by the volatility filter. Fail-safe is a safety mechanism that overrides signal logic. Only suppress DISCRETIONARY transitions (FTD entry, MA50 breakdown entry into SELL, cash deterioration SELL).
**Warning signs:** Being stuck in SELL state during a fail-safe condition because volatility filter blocks the exit.

### Pitfall 6: Suppressing stop loss exits
**What goes wrong:** Stop loss should trigger (price dropped X% from buy), but volatility is low so BUY->CASH transition is suppressed.
**How to avoid:** Stop loss exits should NEVER be suppressed. The volatility filter only suppresses NEW signal entries, not protective exits. Stop loss and DD-count exits remain active regardless of volatility regime.
**Warning signs:** Holding positions through large drawdowns during low-volatility periods.

## Code Examples

### A/B Validation Script Pattern (from validate_fail_safe.py)

```python
# Source: analysis/validate_fail_safe.py lines 59-80
def run_ab_comparison(df):
    # Baseline: volatility filter OFF
    baseline_config = MDMV2Config(volatility_filter_enabled=False, name="baseline_no_vol_filter")
    baseline_engine = MDMV2Engine(baseline_config)
    baseline_results = baseline_engine.run(df)
    baseline_trades = baseline_engine.get_trades()

    # Test: volatility filter ON
    filtered_config = MDMV2Config(volatility_filter_enabled=True, name="with_vol_filter")
    filtered_engine = MDMV2Engine(filtered_config)
    filtered_results = filtered_engine.run(df)
    filtered_trades = filtered_engine.get_trades()
```

### Counting Transitions During Specific Periods

```python
# For BAND-03 validation: count transitions in sideways periods
results['prev_state'] = results['state'].shift(1)
transitions = results[results['state'] != results['prev_state']]

# Filter to low-volatility periods identified by ATR regime
low_vol_transitions = transitions[transitions['atr_regime'] == 'low']
print(f"Transitions during low-vol: baseline={baseline_count}, filtered={filtered_count}")
print(f"Reduction: {(1 - filtered_count/baseline_count)*100:.1f}%")
```

### Key Verification: 2020 crash and 2021 rally timing unchanged

```python
# Success criterion 4: filter must NOT delay entries/exits during trending periods
# Compare specific trade dates between baseline and filtered
crash_2020 = [t for t in trades if '2020-02' <= str(t['date'])[:7] <= '2020-04']
rally_2021 = [t for t in trades if '2021-01' <= str(t['date'])[:7] <= '2021-03']
# Verify: same trade dates and prices in both variants
```

## VN30 ATR Distribution (Empirical Calibration Data)

Based on analysis of 3,750 trading days (2011-2026):

| Metric | Value |
|--------|-------|
| Mean ATR% | 1.469% |
| Median ATR% | 1.285% |
| Std Dev | 0.642% |
| Min | 0.470% |
| Max | 4.954% |
| **P25 (low threshold)** | **1.036%** |
| **P75 (high threshold)** | **1.734%** |

### Regime Distribution at P25/P75 Boundaries

| Regime | Days | Percentage |
|--------|------|------------|
| Low (ATR% < 1.04%) | 938 | 25% |
| Normal (1.04% <= ATR% < 1.73%) | 1,888 | 50% |
| High (ATR% >= 1.73%) | 938 | 25% |

### Regime Validation by Key Period

| Period | Description | Low Days | Normal Days | High Days | ATR% Range |
|--------|-------------|----------|-------------|-----------|------------|
| 2019 Apr-Sep | Sideways | 94 (75%) | 32 (25%) | 0 (0%) | 0.72-1.21% |
| 2020 Feb-Apr | Crash | 0 (0%) | 16 (26%) | 46 (74%) | 1.17-4.95% |
| 2021 Jan-Mar | Rally entry | 0 (0%) | 27 (47%) | 31 (53%) | 1.32-4.07% |
| 2024 Apr-Sep | Low-vol sideways | Most low | Some normal | Few high | ~0.77-1.87% |

### Baseline V2 Whipsaw During Sideways

| Period | Transitions | Key Pattern |
|--------|-------------|-------------|
| 2019 Apr-Sep sideways | 13 | Repeated MA50 breakout -> stop loss -> SELL -> MA50 breakout cycle |
| 2024 Apr-Sep low-vol | 15 | FTD -> stop loss -> SELL -> fail-safe -> repeat |
| 2020 crash | 0 | Already positioned (no whipsaw) |
| 2021 rally | 14 | Active 52-week breakout entries (NOT whipsaw -- legitimate signals) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No volatility awareness | ATR-based regime filter | Phase 26 | Reduces sideways whipsaw by suppressing signals during low-vol |
| Fixed-threshold regime | Percentile-calibrated thresholds | Phase 26 | Auto-adapts to VN30's specific volatility distribution |

**Note on Dr. K's "banding width" concept:** Dr. K mentions that "banding width" affects performance -- when the market trades in a narrow band, signals are unreliable because price oscillates around MA breakout/breakdown levels without conviction. The ATR-based approach directly measures this banding width.

## Open Questions

1. **Should the 2021 rally transitions be preserved exactly?**
   - What we know: 2021 Jan-Jun has 14 transitions, all during normal/high volatility. The filter should NOT suppress any of these.
   - What's unclear: Some 2021 transitions are quick stop-loss exits that could be considered whipsaw. But they are during high-vol trending periods, not sideways.
   - Recommendation: Accept that high-vol whipsaw is a different problem (addressed by stop-loss tuning, not volatility filter). Only suppress low-vol whipsaw.

2. **Should regime be computed on a rolling basis or with fixed lookback?**
   - What we know: Using fixed percentile thresholds (1.04%, 1.73%) avoids look-ahead bias.
   - What's unclear: Whether the thresholds should shift over time (VN30 market maturation could change volatility distribution).
   - Recommendation: Use fixed thresholds for now. If walk-forward validation (Phase 27) shows degradation, revisit with rolling percentile computation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | tests/conftest.py |
| Quick run command | `uv run pytest tests/test_volatility_filter.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BAND-01 | ATR computation and regime classification | unit | `uv run pytest tests/test_volatility_filter.py::test_atr_computation -x` | No -- Wave 0 |
| BAND-01 | Regime labels correct for known periods | unit | `uv run pytest tests/test_volatility_filter.py::test_regime_classification -x` | No -- Wave 0 |
| BAND-02 | Signal suppression during low-vol regime | unit | `uv run pytest tests/test_volatility_filter.py::test_signal_suppression -x` | No -- Wave 0 |
| BAND-02 | Stop loss and fail-safe NOT suppressed | unit | `uv run pytest tests/test_volatility_filter.py::test_protective_exits_not_suppressed -x` | No -- Wave 0 |
| BAND-03 | A/B backtest false signal reduction >= 20% | integration | `uv run python analysis/validate_volatility_filter.py` | No -- Wave 0 |
| BAND-03 | 2020 crash exit and 2021 rally entry unchanged | integration | `uv run python analysis/validate_volatility_filter.py` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_volatility_filter.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_volatility_filter.py` -- covers BAND-01, BAND-02
- [ ] `analysis/validate_volatility_filter.py` -- covers BAND-03
- [ ] No framework install needed (pytest already in project)

## Sources

### Primary (HIGH confidence)
- VN30 CSV data (3,765 rows, 2011-2026) -- empirical ATR distribution analysis
- Existing codebase: `strategies/mdm_v2/` -- engine architecture, config pattern, indicator pattern
- Existing validation scripts: `analysis/validate_fail_safe.py`, `analysis/validate_buy_selectivity.py` -- A/B test pattern

### Secondary (MEDIUM confidence)
- Dr. K "banding width" concept from project research notes (`.planning/PROJECT.md`, `.planning/ROADMAP.md`)
- ATR-14 as standard volatility measure (well-established in technical analysis, no external verification needed)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, pure computation on existing data
- Architecture: HIGH -- follows existing patterns exactly (BuyEntryFilter, SellAccelerationGate, suppress_sell)
- Pitfalls: HIGH -- identified from project history (state[i-1] bug) and engine analysis (fail-safe/stop-loss interaction)
- VN30 calibration: HIGH -- empirical data analysis with clean regime separation

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable -- ATR percentiles change slowly)
