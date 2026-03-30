# Architecture Research

**Domain:** Global Liquidity macro filter + SELL acceleration + BUY quality scoring integration into MDM V2 engine
**Researched:** 2026-03-30
**Confidence:** HIGH

## System Overview

### Current Architecture (Before)

```
┌─────────────────────────────────────────────────────────────┐
│                     MDMV2Engine.run()                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │Indicators│  │RallyTrack│  │FTDDetect │  │DistribDD    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬───────┘ │
│       │             │             │               │         │
│       ├─────────────┴─────────────┴───────────────┘         │
│       ↓                                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            V2PositionManager (BUY/CASH/SELL)          │   │
│  │  process_day(is_ftd, dd_count, stop_loss, ma10, ma50) │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐                                 │
│  │StopLoss  │  │VN30Filter│                                 │
│  └──────────┘  └──────────┘                                 │
├─────────────────────────────────────────────────────────────┤
│                  DataLoader -> Daily OHLCV                    │
└─────────────────────────────────────────────────────────────┘
```

### Target Architecture (After)

```
┌─────────────────────────────────────────────────────────────┐
│                     MDMV2Engine.run()                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │Indicators│  │RallyTrack│  │FTDDetect │  │DistribDD    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬───────┘ │
│       │             │             │               │         │
│       ├─────────────┴─────────────┴───────────────┘         │
│       ↓                                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ┌──────────────┐  NEW                                │   │
│  │  │LiquidityFilt │  Suppress SELL when QE expanding    │   │
│  │  └──────┬───────┘                                     │   │
│  │         ↓                                             │   │
│  │  ┌──────────────┐  NEW                                │   │
│  │  │SellAccelerat │  Require momentum confirmation      │   │
│  │  └──────┬───────┘                                     │   │
│  │         ↓                                             │   │
│  │  ┌──────────────┐  NEW                                │   │
│  │  │BuyQualScore  │  Filter/score BUY entries           │   │
│  │  └──────┬───────┘                                     │   │
│  │         ↓                                             │   │
│  │  ┌──────────────────────────────────────────────────┐ │   │
│  │  │     V2PositionManager (BUY/CASH/SELL)            │ │   │
│  │  │ process_day(..., liquidity_regime, sell_accel,    │ │   │
│  │  │             buy_quality_score)                    │ │   │
│  │  └──────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐              │
│  │StopLoss  │  │VN30Filter│  │LiquidityLoad │ NEW          │
│  └──────────┘  └──────────┘  └──────────────┘              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │DataLoader (OHLCV)│  │GlobalLiquidCSV   │ NEW data source │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | New/Modified | Location |
|-----------|----------------|--------------|----------|
| `LiquidityLoader` | Load weekly CSV, forward-fill to daily, expose regime flag | NEW | `strategies/mdm_v2/liquidity.py` |
| `SellAccelerator` | Check momentum conditions before allowing SELL transition | NEW | `strategies/mdm_v2/sell_accelerator.py` |
| `BuyQualityScorer` | Score FTD/breakout quality, suppress low-quality entries | NEW | `strategies/mdm_v2/buy_quality.py` |
| `MDMV2Config` | Add new parameters for all 3 features | MODIFIED | `strategies/mdm_v2/config.py` |
| `V2PositionManager` | Accept new filter signals in process_day() | MODIFIED | `strategies/mdm_v2/position_manager.py` |
| `MDMV2Engine` | Orchestrate new components in daily loop | MODIFIED | `strategies/mdm_v2/mdm_v2_engine.py` |
| `V2PerformanceAnalyzer` | Add liquidity regime breakdown to reports | MODIFIED | `strategies/mdm_v2/performance.py` |
| `export_dashboard_data.py` | Export liquidity overlay data | MODIFIED | `scripts/export_dashboard_data.py` |

## Recommended Project Structure

After integration, the `strategies/mdm_v2/` directory:

```
strategies/mdm_v2/
├── __init__.py
├── config.py               # MODIFIED: new params for liquidity, sell_accel, buy_quality
├── mdm_v2_engine.py        # MODIFIED: load liquidity, wire new components into loop
├── position_manager.py     # MODIFIED: accept liquidity_regime, sell_accel, buy_quality
├── liquidity.py            # NEW: LiquidityLoader + LiquidityRegime enum
├── sell_accelerator.py     # NEW: SellAccelerator (momentum checks)
├── buy_quality.py          # NEW: BuyQualityScorer (FTD quality scoring)
├── indicators.py           # EXISTING (may add momentum columns)
├── distribution_day.py     # EXISTING (no changes)
├── rally_attempt.py        # EXISTING (no changes)
├── ftd_signal.py           # EXISTING (no changes)
├── stop_loss.py            # EXISTING (no changes)
├── vn30_filters.py         # EXISTING (no changes)
└── performance.py          # MODIFIED: liquidity regime performance breakdown
```

### Structure Rationale

- **New files are peers of existing components** because they follow the same pattern: stateless checkers that receive data and return a result. No new subdirectories needed -- the module is already flat with clear naming.
- **Config changes are additive** because MDMV2Config uses a dataclass with defaults. New params get defaults that preserve current behavior (backward compatible).
- **Engine is the sole orchestrator** because all wiring happens in `mdm_v2_engine.py`. New components are instantiated in `__init__` and called in `run()`. This matches the existing pattern exactly.

## Architectural Patterns

### Pattern 1: Weekly-to-Daily Data Merge via Forward Fill

**What:** Global Liquidity data is WEEKLY (987 rows, every Wednesday). Trading data is DAILY. Merge by forward-filling the weekly value to each trading day until the next weekly observation arrives.

**When to use:** Always -- this is the only correct approach for lower-frequency macro data. The alternative (interpolation) would create look-ahead bias.

**Trade-offs:** Simple and correct. The liquidity reading on Monday-Tuesday reflects the previous week's value (1-2 day lag), which is acceptable for a weekly macro indicator. No look-ahead bias.

**Implementation:**

```python
# strategies/mdm_v2/liquidity.py

import pandas as pd
from enum import Enum
from dataclasses import dataclass


class LiquidityRegime(Enum):
    """Global liquidity regime classification."""
    QE_EXPANDING = "QE_EXPANDING"   # Liquidity growing -> suppress SELL
    QE_NEUTRAL = "QE_NEUTRAL"       # Liquidity flat -> no effect
    QE_CONTRACTING = "QE_CONTRACTING"  # Liquidity shrinking -> normal rules


@dataclass
class LiquidityState:
    """Daily liquidity state after forward-fill merge."""
    regime: LiquidityRegime
    liquidity_roc_20w: float  # 20-week rate of change (%)
    qe_floor: bool            # Original qe_floor flag from CSV
    global_liquidity: float   # Absolute level


class LiquidityLoader:
    """Load and merge weekly global liquidity data with daily trading data.

    Data source: data/global_liquidity.csv
    Columns: date, WALCL, fed_net, ECB_USD, BOJ_USD,
             global_liquidity, liquidity_roc_20w, qe_floor
    """

    def __init__(self, csv_path: str = "data/global_liquidity.csv",
                 roc_expand_threshold: float = 0.0,
                 roc_contract_threshold: float = -2.0):
        self.csv_path = csv_path
        self.roc_expand_threshold = roc_expand_threshold
        self.roc_contract_threshold = roc_contract_threshold

    def load_and_merge(self, daily_df: pd.DataFrame) -> pd.DataFrame:
        """Merge weekly liquidity into daily DataFrame via forward-fill.

        Steps:
        1. Load weekly CSV
        2. Set date as index
        3. Reindex to daily trading dates with ffill
        4. Classify regime from ROC
        5. Join columns to daily_df

        Args:
            daily_df: DataFrame with 'date' column (daily OHLCV).

        Returns:
            daily_df with added columns: global_liquidity,
            liquidity_roc_20w, qe_floor, liquidity_regime.
        """
        liq = pd.read_csv(self.csv_path, parse_dates=['date'])
        liq = liq[['date', 'global_liquidity', 'liquidity_roc_20w', 'qe_floor']]
        liq = liq.set_index('date').sort_index()

        # Reindex to daily trading dates, forward-fill
        trading_dates = pd.DatetimeIndex(daily_df['date'])
        liq_daily = liq.reindex(trading_dates, method='ffill')
        liq_daily = liq_daily.reset_index().rename(columns={'index': 'date'})

        # Classify regime
        liq_daily['liquidity_regime'] = liq_daily['liquidity_roc_20w'].apply(
            self._classify_regime
        )

        # Merge into daily_df
        df = daily_df.copy()
        for col in ['global_liquidity', 'liquidity_roc_20w', 'qe_floor',
                     'liquidity_regime']:
            df[col] = liq_daily[col].values

        return df

    def _classify_regime(self, roc: float) -> str:
        if pd.isna(roc):
            return LiquidityRegime.QE_NEUTRAL.value
        if roc > self.roc_expand_threshold:
            return LiquidityRegime.QE_EXPANDING.value
        if roc < self.roc_contract_threshold:
            return LiquidityRegime.QE_CONTRACTING.value
        return LiquidityRegime.QE_NEUTRAL.value
```

**Key design decisions:**
- `method='ffill'` ensures no look-ahead. Monday uses last Wednesday's value.
- Early daily dates before first liquidity observation (pre-2007) get NaN, classified as NEUTRAL (safe default).
- Regime thresholds are configurable via `MDMV2Config` for parameter sweep.

### Pattern 2: Filter-Gate Architecture (not Propose-Filter-Decide)

**What:** Each new feature acts as a gate that can suppress or modify a state transition proposed by the existing logic. Gates run AFTER the existing logic determines a transition but BEFORE it executes in the position manager.

**When to use:** For all 3 new features. This is simpler than the Hybrid engine's two-phase snapshot/restore because we are modifying V2 directly (not wrapping it).

**Trade-offs:**
- PRO: Minimal changes to existing `process_day()`. Each gate is a simple boolean check.
- PRO: Each gate can be independently enabled/disabled via config flag.
- CON: Order of gates matters (liquidity gate should run before sell acceleration).

**How it works in the engine loop:**

```python
# Inside MDMV2Engine.run(), step 5 becomes:

# 5a. Compute filter gate signals
liquidity_regime = row.get('liquidity_regime', 'QE_NEUTRAL')
sell_accelerated = self.sell_accelerator.check(
    close, prev_close, ma50, price_change_pct, volume_up, dd_count
)
buy_quality = self.buy_scorer.score(
    is_ftd, signal_type, rally_day, price_change_pct,
    volume_up, p_loc, close, ma50, drawdown_pct
)

# 5b. Pass gate signals to position manager
new_state, action = self.position_manager.process_day(
    ...,  # existing args unchanged
    liquidity_regime=liquidity_regime,
    sell_accelerated=sell_accelerated,
    buy_quality=buy_quality,
)
```

### Pattern 3: Additive Config with Backward-Compatible Defaults

**What:** All new parameters added to `MDMV2Config` with defaults that reproduce current behavior exactly. Enables toggling features on/off.

**When to use:** Always for config changes in an existing backtesting system.

**Trade-offs:**
- PRO: Existing backtests produce identical results with no config changes.
- PRO: Each feature can be A/B tested independently.
- CON: Config grows larger (mitigated by clear grouping with comments).

**Config additions:**

```python
@dataclass
class MDMV2Config:
    # ... existing params unchanged ...

    # === Global Liquidity Filter (NEW) ===
    liquidity_enabled: bool = False           # OFF by default = backward compat
    liquidity_csv_path: str = "data/global_liquidity.csv"
    liquidity_roc_expand: float = 0.0         # ROC > 0 = expanding
    liquidity_roc_contract: float = -2.0      # ROC < -2 = contracting
    liquidity_suppress_sell: bool = True       # Suppress SELL when QE_EXPANDING

    # === SELL Acceleration (NEW) ===
    sell_accel_enabled: bool = False           # OFF by default
    sell_accel_min_dd_count: int = 3           # Min DD count before SELL allowed
    sell_accel_price_below_ma50_days: int = 3  # Days below MA50 before SELL
    sell_accel_momentum_threshold: float = -0.02  # Negative momentum required

    # === BUY Quality Scoring (NEW) ===
    buy_quality_enabled: bool = False          # OFF by default
    buy_quality_min_score: float = 0.5         # Min score to accept BUY
    buy_quality_volume_weight: float = 0.3     # Weight for volume confirmation
    buy_quality_ploc_weight: float = 0.2       # Weight for price location
    buy_quality_trend_weight: float = 0.3      # Weight for trend alignment
    buy_quality_drawdown_weight: float = 0.2   # Weight for drawdown depth
```

## Data Flow

### Daily Processing Flow (Modified)

```
DataLoader.load()                    LiquidityLoader.load_and_merge()
      |                                         |
      v                                         v
  daily_df [date, OHLCV]    ---- merge ---->  daily_df + [liquidity cols]
      |
      v
  Indicators (add columns: p_loc, ma10, ma50, etc.)
      |
      v
  VN30 Filters (is_expiry_day, is_limit_day) -- if VN30
      |
      v
  +--- FOR EACH DAY -------------------------------------------+
  |                                                             |
  |  1. RallyAttemptTracker.process_day()  -> rally_day, is_day1|
  |  2. FTDSignalDetector.check_ftd()      -> is_ftd, ftd_price|
  |  3. DistributionDayCounter             -> dd_count, is_dd   |
  |  4. StopLossChecker.check()            -> stop_loss_result  |
  |                                                             |
  |  5. NEW GATES:                                              |
  |     a. Read liquidity_regime from row                       |
  |     b. SellAccelerator.check() -> sell_accelerated: bool    |
  |     c. BuyQualityScorer.score() -> buy_quality: float       |
  |                                                             |
  |  6. V2PositionManager.process_day(                          |
  |         ...existing args...,                                |
  |         liquidity_regime=regime,                            |
  |         sell_accelerated=sell_accel,                         |
  |         buy_quality=quality_score,                           |
  |     )                                                       |
  |                                                             |
  |  7. Update DataFrame row with results + new columns         |
  +-------------------------------------------------------------+
      |
      v
  V2PerformanceAnalyzer.analyze() -> equity, metrics, regime breakdown
```

### Liquidity Data Flow (NEW)

```
data/global_liquidity.csv (WEEKLY: 987 rows, 2007-2026)
    |
    v  pd.read_csv()
Weekly DataFrame [date, global_liquidity, liquidity_roc_20w, qe_floor]
    |
    v  reindex(trading_dates, method='ffill')
Daily-aligned DataFrame (forward-filled, no look-ahead)
    |
    v  _classify_regime(roc)
Daily DataFrame + liquidity_regime column
    |
    v  merge with daily_df
Engine DataFrame with all liquidity columns available per row
```

### State Transition Modifications

Current transitions in `V2PositionManager.process_day()`:

```
CASH -> BUY:   is_ftd == True
BUY  -> CASH:  dd_count >= threshold | stop_loss | MA10 below
CASH -> SELL:  close < MA50 | days_in_cash >= deterioration
SELL -> BUY:   is_ftd == True
```

Modified transitions with gates:

```
CASH -> BUY:   is_ftd == True
               AND (NOT buy_quality_enabled OR buy_quality >= min_score)

BUY  -> CASH:  dd_count >= threshold | stop_loss | MA10 below
               (UNCHANGED -- protective exits never gated)

CASH -> SELL:  (close < MA50 | days_in_cash >= deterioration)
               AND (NOT liquidity_suppress_sell OR regime != QE_EXPANDING)
               AND (NOT sell_accel_enabled OR sell_accelerated == True)

SELL -> BUY:   is_ftd == True
               AND (NOT buy_quality_enabled OR buy_quality >= min_score)
```

**Critical rule: BUY -> CASH is NOT gated by liquidity.** If you are in a position and stop loss / DD threshold triggers, you must exit regardless of liquidity regime. The QE floor only suppresses entering SELL (bearish regime signal), not protective exits. This matches Dr. K's 2013 webinar: QE floor affects the MDM signal direction, not individual position risk management.

### Key Data Flows

1. **Liquidity merge:** Runs ONCE before the daily loop starts (not per-day). The `load_and_merge()` adds columns to the full DataFrame, then the loop reads them per-row. Efficient and clean.

2. **Gate evaluation:** Runs per-day INSIDE the loop. Each gate is a simple function call returning a bool or float. No state mutation in the gates -- they are pure functions of row data.

3. **Dashboard export:** After backtest, the liquidity columns are available in results DataFrame. Export adds `liquidity_regime` to chart data so dashboard can shade QE periods.

## SellAccelerator Design

The SELL accelerator requires momentum confirmation before allowing CASH -> SELL transition. This prevents premature SELL signals during mild corrections.

```python
# strategies/mdm_v2/sell_accelerator.py

from dataclasses import dataclass


@dataclass
class SellAccelResult:
    """Result of sell acceleration check."""
    accelerated: bool
    reason: str


class SellAccelerator:
    """Check momentum conditions before allowing SELL transition.

    Conditions checked (all must be true for sell_accelerated=True):
    1. DD count >= sell_accel_min_dd_count (distribution building)
    2. Close below MA50 for >= sell_accel_price_below_ma50_days
    3. Recent price momentum < sell_accel_momentum_threshold

    The accelerator tracks days_below_ma50 as internal state (reset
    when close crosses back above MA50).
    """

    def __init__(self, config):
        self.config = config
        self.days_below_ma50 = 0

    def reset(self):
        self.days_below_ma50 = 0

    def check(self, close, ma50, dd_count, price_change_5d) -> SellAccelResult:
        """Check if SELL transition should be allowed.

        Args:
            close: Current close price.
            ma50: Current 50-day MA.
            dd_count: Current distribution day count.
            price_change_5d: 5-day price change percentage.

        Returns:
            SellAccelResult with accelerated flag and reason.
        """
        if not self.config.sell_accel_enabled:
            return SellAccelResult(accelerated=True, reason="disabled")

        # Track days below MA50
        if ma50 is not None and close < ma50:
            self.days_below_ma50 += 1
        else:
            self.days_below_ma50 = 0

        # Check conditions
        dd_ok = dd_count >= self.config.sell_accel_min_dd_count
        ma50_ok = self.days_below_ma50 >= self.config.sell_accel_price_below_ma50_days
        momentum_ok = price_change_5d < self.config.sell_accel_momentum_threshold

        accelerated = dd_ok and ma50_ok and momentum_ok

        if not accelerated:
            reasons = []
            if not dd_ok:
                reasons.append(f"DD {dd_count} < {self.config.sell_accel_min_dd_count}")
            if not ma50_ok:
                reasons.append(f"below MA50 {self.days_below_ma50}d < {self.config.sell_accel_price_below_ma50_days}d")
            if not momentum_ok:
                reasons.append(f"momentum {price_change_5d:.3f} > {self.config.sell_accel_momentum_threshold}")
            return SellAccelResult(accelerated=False, reason="; ".join(reasons))

        return SellAccelResult(accelerated=True, reason="momentum confirmed")
```

**Note:** SellAccelerator has minimal state (`days_below_ma50` counter). This is acceptable because it tracks a running count that resets on MA50 crossover, similar to how `V2Position.ma10_below_count` works in the existing position manager.

## BuyQualityScorer Design

The BUY quality scorer assigns a 0.0-1.0 score to FTD/breakout signals. Low-scoring signals are suppressed to reduce whipsaw.

```python
# strategies/mdm_v2/buy_quality.py

class BuyQualityScorer:
    """Score FTD/breakout signal quality.

    Scoring factors:
    - Volume confirmation (FTD volume vs average)
    - Price location (close in upper half of range = stronger)
    - Trend alignment (close above MA50 = stronger)
    - Drawdown depth (deeper correction before FTD = more meaningful)

    Each factor returns 0.0-1.0, combined as weighted average.
    """

    def __init__(self, config):
        self.config = config

    def score(self, is_ftd, signal_type, rally_day,
              price_change_pct, volume_ratio, p_loc,
              close, ma50, drawdown_pct) -> float:
        """Score a potential BUY signal quality.

        Returns 1.0 if buy_quality_enabled is False (pass-through).
        """
        if not self.config.buy_quality_enabled or not is_ftd:
            return 1.0  # No filtering

        scores = {}

        # Volume factor: higher volume ratio = better
        scores['volume'] = min(1.0, volume_ratio / 1.5) if volume_ratio else 0.5

        # Price location factor: close in upper range = stronger
        scores['ploc'] = p_loc if p_loc is not None else 0.5

        # Trend factor: above MA50 = 1.0, below = 0.0-0.5
        if ma50 is not None and ma50 > 0:
            ma50_ratio = close / ma50
            scores['trend'] = min(1.0, max(0.0, ma50_ratio - 0.9) / 0.2)
        else:
            scores['trend'] = 0.5

        # Drawdown factor: deeper correction = more meaningful FTD
        # -10% drawdown -> score 1.0, -3% -> score 0.3
        abs_dd = abs(drawdown_pct) if drawdown_pct else 0
        scores['drawdown'] = min(1.0, abs_dd / 0.10)

        # Weighted combination
        total = (
            scores['volume'] * self.config.buy_quality_volume_weight +
            scores['ploc'] * self.config.buy_quality_ploc_weight +
            scores['trend'] * self.config.buy_quality_trend_weight +
            scores['drawdown'] * self.config.buy_quality_drawdown_weight
        )

        return total
```

**Design choice: Start simple.** The scorer uses 4 factors with linear scaling. If this does not improve held-out performance, simplify to 2-3 binary conditions instead. Avoid adding more factors -- overfitting risk increases with every knob.

## Integration into V2PositionManager

The position manager changes are minimal. Three new optional kwargs to `process_day()`:

```python
def process_day(
    self,
    # ... existing params unchanged ...
    liquidity_regime: str = None,      # NEW
    sell_accelerated: bool = True,      # NEW (default=True = no gating)
    buy_quality: float = 1.0,           # NEW (default=1.0 = no gating)
) -> Tuple[V2MarketState, str]:

    # In CASH state, before CASH -> BUY:
    if is_ftd:
        if self.config.buy_quality_enabled and buy_quality < self.config.buy_quality_min_score:
            action = f"BUY suppressed (quality {buy_quality:.2f} < {self.config.buy_quality_min_score})"
            # Do NOT enter_buy -- signal rejected
        else:
            self.enter_buy(ftd_price, date, low, signal_type)

    # In CASH state, before CASH -> SELL:
    elif self.config.ma50_sell_enabled and ma50 is not None and close < ma50:
        sell_allowed = True
        if self.config.liquidity_enabled and liquidity_regime == "QE_EXPANDING":
            sell_allowed = False
            action = f"SELL suppressed (QE expanding)"
        if sell_allowed and self.config.sell_accel_enabled and not sell_accelerated:
            sell_allowed = False
            action = f"SELL deferred (momentum not confirmed)"
        if sell_allowed:
            self.enter_sell(date, f"MA50 breakdown")

    # In SELL state, before SELL -> BUY:
    if is_ftd:
        if self.config.buy_quality_enabled and buy_quality < self.config.buy_quality_min_score:
            action = f"BUY suppressed from SELL (quality {buy_quality:.2f})"
        else:
            self.enter_buy(ftd_price, date, low, signal_type)

    # BUY -> CASH: UNCHANGED. No liquidity gating on protective exits.
```

## Scaling Considerations

Not relevant for this backtesting project. The global liquidity CSV is 987 rows. Forward-fill merge is O(n) where n = trading days. Gate checks are O(1) per day. No performance concerns.

| Operation | Current Cost | After Integration | Notes |
|-----------|-------------|-------------------|-------|
| Data load | ~100ms | +5ms (liquidity CSV) | Negligible |
| Indicator calc | ~200ms | +0ms | Liquidity pre-computed in CSV |
| Daily loop (VN30, ~2800 days) | ~500ms | +10ms (3 gate checks/day) | Pure arithmetic |
| Parameter sweep | O(n * combos) | O(n * combos * 1.02x) | Marginal overhead |

## Anti-Patterns

### Anti-Pattern 1: Interpolating Weekly Data to Daily

**What people do:** Linear interpolation or spline fitting to create "smooth" daily liquidity values from weekly data.
**Why it's wrong:** Creates look-ahead bias. Wednesday's liquidity value would influence Monday's interpolated value. Fatal in backtesting.
**Do this instead:** Forward-fill only. Monday-Tuesday use last week's value. Simple, correct, no look-ahead.

### Anti-Pattern 2: Gating BUY-to-CASH Exits with Liquidity

**What people do:** "If QE is expanding, don't exit to CASH even on stop loss" -- thinking the QE floor protects against all losses.
**Why it's wrong:** QE floor suppresses SELL (bearish regime signal), not protective exits. A position hitting stop loss is risk management, not a regime call. Dr. K's 2013 webinar says QE floor affects the MDM signal (suppress SELL), not position management.
**Do this instead:** Only gate CASH-to-SELL transition with liquidity. BUY-to-CASH transitions (stop loss, DD threshold, MA10) remain unaffected.

### Anti-Pattern 3: Complex Weighted Scoring Without Baseline

**What people do:** Build a 10-factor BUY quality score with tuned weights, test it, declare improvement.
**Why it's wrong:** Without clear baseline comparison and holdout validation, complex scoring overfits to training data. More knobs = more overfitting risk.
**Do this instead:** Start with 4 factors (volume, p_loc, trend, drawdown). Only add complexity if simple gates do not improve held-out performance. Always compare to `buy_quality_enabled=False` baseline.

### Anti-Pattern 4: Mutating Engine State Inside Filter Gates

**What people do:** Put state-changing logic (resetting DD counter, modifying position) inside the liquidity or sell-acceleration checker.
**Why it's wrong:** Breaks separation of concerns. Gates should be pure functions (or near-pure with minimal tracking state). State mutation belongs in `V2PositionManager.process_day()` only.
**Do this instead:** Gates return a verdict (bool/float). The position manager reads the verdict and decides whether to execute.

### Anti-Pattern 5: Liquidity Filter on Pre-2007 Data

**What people do:** Enable liquidity filter on NASDAQ backtests starting from 1974, where no liquidity data exists.
**Why it's wrong:** Pre-2007 dates have no liquidity observations. Forward-fill from nothing = NaN = QE_NEUTRAL, which is correct behavior. But reporting "liquidity improved results" when 60% of the backtest period had no liquidity data is misleading.
**Do this instead:** Report liquidity regime coverage. If backtest starts before 2007-05-02, warn that liquidity data only covers a subset. Separate performance reporting for liquidity-covered vs uncovered periods.

## Integration Points

### New Component Interfaces

| Component | Input | Output | Called By |
|-----------|-------|--------|-----------|
| `LiquidityLoader.load_and_merge(daily_df)` | Daily OHLCV DataFrame | DataFrame + 4 liquidity cols | `MDMV2Engine.run()` (once, before loop) |
| `SellAccelerator.check(close, ma50, dd_count, price_5d)` | Daily row values | `SellAccelResult` | `MDMV2Engine.run()` (per day) |
| `BuyQualityScorer.score(is_ftd, signal_type, ...)` | FTD info + row values | `float` (0.0-1.0) | `MDMV2Engine.run()` (per day) |
| `V2PositionManager.process_day(...+3 kwargs)` | Existing + gate results | `(state, action)` | `MDMV2Engine.run()` (per day) |

### Modified Interfaces (All Backward Compatible)

| Component | Change | Default Behavior |
|-----------|--------|-----------------|
| `MDMV2Config.__init__` | +15 new params, all with defaults | All features OFF = identical to current |
| `V2PositionManager.process_day()` | +3 optional kwargs | `None`/`True`/`1.0` = no gating |
| `MDMV2Engine.__init__` | Instantiate 3 new components | Gated by config flags |
| `MDMV2Engine.run()` | Liquidity merge + gate calls | Gated by config flags |

### Dashboard Integration

| Data Point | Source | Dashboard Use |
|------------|--------|---------------|
| `liquidity_regime` per day | Engine results DataFrame | Background shading on price chart |
| `liquidity_roc_20w` per day | Engine results DataFrame | Secondary axis or tooltip |
| `buy_quality` per signal | Engine results DataFrame | Signal marker color/size |
| Before/after metrics | V2PerformanceAnalyzer | Comparison table |

## Suggested Build Order

Build order follows dependency chain. Each step produces a testable unit.

### Step 1: LiquidityLoader + Config Additions (foundation)

**Files:** `liquidity.py` (NEW), `config.py` (MODIFY)
**Depends on:** Nothing (reads CSV independently)
**Testable:** Load CSV, forward-fill, verify no look-ahead, verify regime classification, verify backward compatibility (all new params defaulted OFF).
**Why first:** Foundation for all other features. Novel weekly-to-daily merge needs careful testing.

### Step 2: Wire Liquidity into Engine (data flow)

**Files:** `mdm_v2_engine.py` (MODIFY)
**Depends on:** Step 1
**Testable:** Run backtest with `liquidity_enabled=False`, verify IDENTICAL results to baseline. Then `True`, verify liquidity columns in results DataFrame.
**Why second:** Proves data merge works end-to-end without changing trading logic.

### Step 3: Liquidity SELL Suppression Gate (first trading logic change)

**Files:** `position_manager.py` (MODIFY)
**Depends on:** Steps 1-2
**Testable:** Backtest with liquidity gate ON. Count SELL signals in QE_EXPANDING periods -- should be zero. Compare overall return.
**Why third:** Highest-value feature (Dr. K explicitly uses QE floor). Simple boolean gate.

### Step 4: SellAccelerator (second feature)

**Files:** `sell_accelerator.py` (NEW), `position_manager.py` (MODIFY), `mdm_v2_engine.py` (MODIFY to add 5-day momentum column)
**Depends on:** Step 3 (gates stack)
**Testable:** Backtest with sell acceleration ON. SELL should require momentum confirmation. Count deferred SELLs.
**Why fourth:** Modifies same transition as liquidity (CASH -> SELL), so tests both gates together.

### Step 5: BuyQualityScorer (third feature)

**Files:** `buy_quality.py` (NEW), `position_manager.py` (MODIFY)
**Depends on:** Steps 1-2 (may use liquidity regime as input)
**Testable:** Backtest with buy quality ON. Count suppressed BUY signals. Compare whipsaw rate.
**Why fifth:** Independent of SELL-side changes. Can be developed in parallel with Step 4.

### Step 6: Performance + Dashboard (output)

**Files:** `performance.py` (MODIFY), `export_dashboard_data.py` (MODIFY)
**Depends on:** Steps 1-5
**Testable:** Verify regime-breakdown metrics. Dashboard shows liquidity shading.
**Why last:** Pure output -- no impact on trading logic.

### Step 7: Parameter Sweep + Validation

**Files:** New script or notebook
**Depends on:** All above
**Testable:** Sweep thresholds on VN30 and NASDAQ. Compare to baseline. Holdout validation.

## Sources

- Existing codebase: `strategies/mdm_v2/` (all 12 files read and analyzed)
- `data/global_liquidity.csv` structure: 987 weeks, 2007-2026, pre-computed `liquidity_roc_20w` and `qe_floor` columns
- Dr. K's 2013 webinar transcript (referenced in PROJECT.md): QE floor concept -- suppress SELL when QE expanding
- Existing pattern: `vn30_filters.py` as model for stateless DataFrame transformers
- Existing pattern: `V2Position.ma10_below_count` for stateful counting in position manager
- Existing pattern: `HybridEngine` two-phase commit (noted but NOT used -- too complex for V2 direct integration)
- Existing `V2PositionManager.process_day()` interface (kwargs-extensible design)

---
*Architecture research for: Global Liquidity + SELL Acceleration + BUY Quality integration into MDM V2*
*Researched: 2026-03-30*
