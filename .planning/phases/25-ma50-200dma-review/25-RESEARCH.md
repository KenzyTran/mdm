# Phase 25: MA50/200dma Review - Research

**Researched:** 2026-04-01
**Domain:** A/B backtesting, MA50 role analysis, 200dma indicator addition
**Confidence:** HIGH

## Summary

Phase 25 is a research/A/B testing phase that evaluates whether MA50 should remain in V2's signal logic. The phase runs 5 structured scenarios on VN30 data, progressively removing MA50 from SELL trigger, BUY filter, and breakout buy signal, plus a 200dma replacement scenario. The deliverable is a quantitative report (MAREVIEW-03) recommending keep/remove/replace.

The existing codebase already has config flags for 2 of the 3 MA50 uses (`ma50_sell_enabled`, `buy_filter_enabled`), so scenarios 2 and 3 are pure flag toggles. The main implementation work is: (1) adding a `ma50_breakout_enabled` config flag to gate scenario 4, (2) adding `sma200` indicator computation for scenario 5, (3) wiring 200dma as replacement buy/sell trigger, and (4) building the validation script following Phase 24's pattern.

**Primary recommendation:** Follow the Phase 24 `validate_buy_entry.py` pattern exactly -- 5 config variants, shared `run_backtest()` + `compute_metrics()`, comparison table output.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 5 scenarios: Baseline (all MA50 on), -SELL only, -BUY filter only, -All MA50, +200dma replacement
- **D-02:** In scenarios 2 and 3, MA50 breakout buy stays active (isolate one role at a time)
- **D-03:** 200dma requires: add sma200 indicator, add `ma200_enabled: bool = False` config flag, replace MA50 breakout with `close > sma200` crossover, replace MA50 SELL with `close < sma200`
- **D-04:** When `ma50_sell_enabled=False`, SELL falls back to `cash_deterioration_days` only
- **D-05:** Single script `analysis/validate_ma50_review.py` following Phase 24 pattern
- **D-06:** Report concludes with one of: keep MA50 / remove MA50 / replace MA50 with 200dma

### Claude's Discretion
- Exact sma200 implementation (rolling 200-day close mean, same pattern as ma50)
- Config parameter naming for 200dma threshold and enable flags
- How to handle 200dma not being available for first 200 bars
- Validation script output formatting and per-scenario table layout
- Whether to add per-scenario result columns to trades DataFrame

### Deferred Ideas (OUT OF SCOPE)
- ATR-based or DD-count-based replacement SELL trigger
- Optimizing `cash_deterioration_days` threshold when MA50 SELL is removed
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAREVIEW-01 | A/B backtest V2 current vs V2 without MA50 breakdown in SELL trigger on VN30 | Scenario 2 (-SELL only): toggle `ma50_sell_enabled=False`, SELL falls back to `cash_deterioration_days` only |
| MAREVIEW-02 | A/B backtest V2 current vs V2 without MA50 in BUY filter on VN30 | Scenario 3 (-BUY filter only): toggle `buy_filter_enabled=False`, FTD signals no longer gated by MA10/MA50 trend |
| MAREVIEW-03 | Report concluding keep/remove/replace MA50, with VN30 backtest evidence | Validation script outputs per-scenario metrics table + recommendation section comparing all 5 scenarios |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations for backtest results | Already in project |
| numpy | >= 1.24.0 | Rolling mean computation for sma200 | Already in project |
| matplotlib | >= 3.7.0 | Optional equity curve charts per scenario | Already in project |

### Supporting
No new libraries needed. This phase uses only existing project dependencies.

**Installation:** None required -- all dependencies already installed.

## Architecture Patterns

### Existing Indicator Pattern (copy for sma200)

The `Indicators` class uses static methods that take a DataFrame and return a modified copy:

```python
# Source: strategies/mdm_v2/indicators.py line 116-128
@staticmethod
def add_ma50_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['ma50'] = df['close'].rolling(window=50, min_periods=1).mean()
    return df
```

For sma200, follow the identical pattern:
```python
@staticmethod
def add_sma200_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['sma200'] = df['close'].rolling(window=200, min_periods=1).mean()
    return df
```

**Note on `min_periods=1`:** The existing MA50 uses `min_periods=1`, which means the first 49 bars use a partial window. The same approach for sma200 means the first 199 bars will have a partial-window average. This is consistent with the existing pattern and avoids NaN handling complexity. The warmup period (`WARMUP_DAYS = 300`) in the validation script already loads ~450 calendar days of pre-period data, which exceeds 200 trading days.

### Config Flag Convention (v5.0 rule)

New features default OFF for backward compatibility:
```python
# In MDMV2Config:
ma50_breakout_enabled: bool = True   # NEW: gate existing MA50 breakout buy (default ON = no behavior change)
ma200_enabled: bool = False          # NEW: 200dma replacement (default OFF per v5.0)
```

`ma50_breakout_enabled` defaults True because the MA50 breakout signal is currently always active -- setting True preserves existing behavior. Only scenario 4 sets it False.

### A/B Validation Script Pattern (from Phase 24)

The established pattern from `validate_buy_entry.py`:

1. Define `PERIODS` dict with VN30 full range
2. Create per-scenario config factory functions (`make_baseline_config()`, etc.)
3. Shared `run_backtest(config, period)` loads data via `DataLoader`, runs `MDMV2Engine`
4. Shared `compute_metrics(engine)` extracts total_return, max_drawdown, trade_count, win_rate via `V2PerformanceAnalyzer`
5. `print_comparison(results_dict)` outputs aligned table
6. Main block iterates configs, collects results, prints comparison

For Phase 25, extend with:
- 5 config factories instead of 4
- Add `sharpe_ratio` to metrics (CONTEXT.md requires it in success criteria)
- Add recommendation section logic comparing scenarios

### MA50 Use-Site Map (CRITICAL -- 5 sites, not 3)

CONTEXT.md identifies 3 MA50 use sites. Research reveals **2 additional sites** that are NOT in scope for A/B toggle but must be understood:

| # | Module | Function | MA50 Role | In A/B Scope? |
|---|--------|----------|-----------|---------------|
| 1 | `position_manager.py` L201 | `process_day()` CASH->SELL | SELL trigger: `close < ma50` | YES (D-01 Scenario 2) |
| 2 | `buy_filter.py` L46 | `BuyFilter.check()` | BUY gate: reject FTD when `ma10 < ma50` | YES (D-01 Scenario 3) |
| 3 | `ftd_signal.py` L89-141 | `check_ma50_breakout()` | BUY signal: MA50 crossover after correction | YES (D-01 Scenario 4) |
| 4 | `stop_loss.py` L106-113 | `StopLossChecker.check()` Rule 3 | Stop loss: break below MA50 with volume | NO -- stop loss stays unchanged |
| 5 | `sell_acceleration.py` L85-93 | `_check_volume_ma50_breakdown()` | Acceleration gate: MA50 breakdown as one of 3 OR conditions | NO -- acceleration gate stays unchanged |

**Important:** When MA50 SELL trigger is disabled (scenario 2), the sell acceleration gate's MA50 breakdown check (#5) remains active. This is correct per CONTEXT.md D-04 -- the acceleration gate is a separate concern. Similarly, stop loss Rule 3 (#4) continues to use MA50 regardless of scenario. The planner should NOT touch these.

### 200dma Replacement Wiring (Scenario 5)

Scenario 5 replaces MA50 with 200dma in two specific paths:

1. **BUY signal:** Replace `check_ma50_breakout()` with a 200dma crossover:
   - Condition: `prev_close <= prev_sma200 and close > sma200` (cross above)
   - Plus volume confirmation and correction depth check (same as current MA50 breakout)

2. **SELL trigger:** Replace `close < ma50` in position_manager CASH->SELL with `close < sma200`

This means the engine needs to pass `sma200` and `prev_sma200` values when `ma200_enabled=True`. The cleanest approach: compute sma200 in the engine's `run()` method (alongside ma50), pass to position_manager and ftd_detector.

### Engine Integration Points

In `mdm_v2_engine.py`:
- Line 96-101: Add `Indicators.add_sma200_column(df)` call when `ma200_enabled=True`
- Line 101: Add `df['prev_sma200'] = df['sma200'].shift(1)` 
- Line 192-204: Gate `check_ma50_breakout()` on `ma50_breakout_enabled` flag; add alternative 200dma breakout check when `ma200_enabled=True`
- Line 201-208 (via position_manager): Pass sma200 to `process_day()` for 200dma SELL trigger

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Performance metrics | Custom return/drawdown/Sharpe | `V2PerformanceAnalyzer` | Already handles state[i-1] rule, avoids look-ahead bias |
| Data loading | Manual CSV parsing | `DataLoader` + warmup period | Handles column mapping, date filtering |
| Rolling mean | Manual loop computation | `pd.Series.rolling().mean()` | Vectorized, handles edge cases |

## Common Pitfalls

### Pitfall 1: State[i-1] Look-Ahead Bias
**What goes wrong:** Using current-day state instead of previous-day state for equity calculation gives wildly inflated returns (707% vs 93% was a real bug).
**Why it happens:** Temptation to compute return based on today's state rather than yesterday's.
**How to avoid:** Always use `V2PerformanceAnalyzer` which enforces the `state[i-1]` rule internally.
**Warning signs:** Returns that seem too good to be true.

### Pitfall 2: MA50 Breakout Has No Config Gate
**What goes wrong:** Currently `check_ma50_breakout()` fires whenever MA50 data exists -- there's no `ma50_breakout_enabled` flag to disable it for scenario 4.
**Why it happens:** The MA50 breakout was added in v3.0 before the flag convention was established.
**How to avoid:** Add `ma50_breakout_enabled: bool = True` to MDMV2Config before implementing scenarios. Gate the breakout check in the engine.
**Warning signs:** Scenario 4 (-All MA50) still shows MA50 breakout buy signals.

### Pitfall 3: Scenario 5 Must Replace, Not Add
**What goes wrong:** Adding 200dma as an additional buy signal alongside MA50 breakout instead of replacing it.
**Why it happens:** Misreading D-03 as "add 200dma" rather than "replace MA50 with 200dma."
**How to avoid:** Scenario 5 config: `ma50_sell_enabled=False, buy_filter_enabled=False, ma50_breakout_enabled=False, ma200_enabled=True`. All MA50 uses OFF, 200dma ON.
**Warning signs:** Scenario 5 shows both MA50 and 200dma signals in trade log.

### Pitfall 4: Sell Acceleration Still Uses MA50
**What goes wrong:** When MA50 SELL is disabled (scenarios 2, 4, 5), the sell acceleration gate's `_check_volume_ma50_breakdown()` still uses MA50. This could cause subtle behavior where the acceleration gate fires on MA50 breakdown but the SELL trigger itself is disabled.
**Why it happens:** The acceleration gate checks MA50 breakdown independently.
**How to avoid:** This is actually correct behavior per CONTEXT.md (D-04 says SELL falls back to deterioration days only). The acceleration gate's MA50 check simply becomes one path for triggering acceleration -- but since MA50 SELL trigger is off, the acceleration result for MA50 path is moot. However, the acceleration gate also has ROC and DD-cluster paths that still function.
**Warning signs:** None -- this is expected. Document in the report.

### Pitfall 5: Warmup Period for 200dma
**What goes wrong:** sma200 has NaN or unreliable values for first 200 bars.
**Why it happens:** 200-day rolling window needs 200 data points for a true average.
**How to avoid:** Using `min_periods=1` (matching existing MA50 pattern) and existing `WARMUP_DAYS = 300` already loads sufficient pre-period data. The validation script loads ~450 calendar days of warmup, which exceeds 200 trading days.
**Warning signs:** sma200 values very close to close price in early bars.

### Pitfall 6: Sharpe Ratio in Metrics
**What goes wrong:** Phase success criteria require Sharpe ratio comparison, but Phase 24's `compute_metrics()` only returns total_return, max_drawdown, trade_count, win_rate.
**Why it happens:** Phase 24 didn't need Sharpe.
**How to avoid:** Add `sharpe_ratio` to `compute_metrics()` output using `V2PerformanceAnalyzer.sharpe_ratio()`.
**Warning signs:** Missing Sharpe column in comparison table.

## Code Examples

### Config for Each Scenario

```python
# Scenario 1: Baseline (all MA50 uses on)
def make_baseline_config():
    return MDMV2Config(
        ma50_sell_enabled=True,
        buy_filter_enabled=True,
        ma50_breakout_enabled=True,   # NEW flag, default True
        ma200_enabled=False,
        name="baseline",
    )

# Scenario 2: -SELL only
def make_no_sell_config():
    return MDMV2Config(
        ma50_sell_enabled=False,      # DISABLED
        buy_filter_enabled=True,
        ma50_breakout_enabled=True,
        ma200_enabled=False,
        name="no_ma50_sell",
    )

# Scenario 3: -BUY filter only
def make_no_filter_config():
    return MDMV2Config(
        ma50_sell_enabled=True,
        buy_filter_enabled=False,     # DISABLED
        ma50_breakout_enabled=True,
        ma200_enabled=False,
        name="no_buy_filter",
    )

# Scenario 4: -All MA50
def make_no_ma50_config():
    return MDMV2Config(
        ma50_sell_enabled=False,      # DISABLED
        buy_filter_enabled=False,     # DISABLED
        ma50_breakout_enabled=False,  # DISABLED (NEW)
        ma200_enabled=False,
        name="no_ma50_all",
    )

# Scenario 5: +200dma replacement
def make_200dma_config():
    return MDMV2Config(
        ma50_sell_enabled=False,      # Replaced by 200dma
        buy_filter_enabled=False,     # MA50 filter off (no MA200 filter equivalent)
        ma50_breakout_enabled=False,  # Replaced by 200dma crossover
        ma200_enabled=True,           # NEW: 200dma replacement active
        name="200dma_replace",
    )
```

### sma200 Indicator (following existing pattern)

```python
# Source pattern: strategies/mdm_v2/indicators.py add_ma50_column
@staticmethod
def add_sma200_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add 200-day Simple Moving Average column."""
    df = df.copy()
    df['sma200'] = df['close'].rolling(window=200, min_periods=1).mean()
    return df
```

### 200dma Crossover Buy Signal

```python
# Adaptation of check_ma50_breakout for 200dma
def check_200dma_breakout(
    self, close, prev_close, sma200, prev_sma200,
    volume_up, drawdown_pct, date
):
    """Check if price breaks above 200dma after correction."""
    if drawdown_pct > self.config.ma50_breakout_correction:
        return False, None
    if not (prev_close <= prev_sma200 and close > sma200):
        return False, None
    if not volume_up:
        return False, None
    signal = FTDSignal(date=date, price=close, rally_day=0, signal_type="200DMA")
    self.last_signal = signal
    return True, signal
```

### Validation Metrics with Sharpe

```python
def compute_metrics(engine):
    results_df = engine.results
    trades = engine.get_trades()
    analyzer = V2PerformanceAnalyzer(results_df, trades)
    exit_trades = [t for t in trades if t.get('type') in ('CASH_EXIT', 'SHORT_COVER', 'FAIL_SAFE_EXIT')]
    wins = sum(1 for t in exit_trades if t.get('pnl', 0) > 0)
    win_rate = (wins / len(exit_trades) * 100) if exit_trades else 0.0
    return {
        'total_return': analyzer.total_return() * 100,
        'max_drawdown': analyzer.max_drawdown() * 100,
        'sharpe_ratio': analyzer.sharpe_ratio(),
        'trade_count': len(exit_trades),
        'win_rate': win_rate,
    }
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `tests/conftest.py` (path setup only) |
| Quick run command | `uv run pytest tests/test_mdm_v2_engine.py -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAREVIEW-01 | MA50 SELL toggle produces different results when disabled | unit | `uv run pytest tests/test_ma50_review.py::test_no_sell_differs_from_baseline -x` | Wave 0 |
| MAREVIEW-02 | BUY filter toggle produces different results when disabled | unit | `uv run pytest tests/test_ma50_review.py::test_no_filter_differs_from_baseline -x` | Wave 0 |
| MAREVIEW-03 | Validation script runs all 5 scenarios without error | smoke | `uv run python analysis/validate_ma50_review.py` | Wave 0 |
| - | sma200 indicator computed correctly | unit | `uv run pytest tests/test_ma50_review.py::test_sma200_indicator -x` | Wave 0 |
| - | ma50_breakout_enabled=False prevents MA50 breakout signals | unit | `uv run pytest tests/test_ma50_review.py::test_breakout_gated -x` | Wave 0 |
| - | 200dma replacement produces valid buy/sell signals | unit | `uv run pytest tests/test_ma50_review.py::test_200dma_replacement -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_ma50_review.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green + validation script runs successfully

### Wave 0 Gaps
- [ ] `tests/test_ma50_review.py` -- covers MAREVIEW-01, MAREVIEW-02, sma200, breakout gate, 200dma replacement
- Framework install: None needed (pytest 9.0.2 already available)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MA50 breakout always active | Should be gated by config flag | Phase 25 (now) | Enables scenario 4 (remove all MA50) |
| No 200dma indicator | Add sma200 column | Phase 25 (now) | Enables scenario 5 (200dma replacement) |
| 4 metrics (return, DD, trades, win rate) | 5 metrics (+Sharpe) | Phase 25 (now) | Better risk-adjusted comparison |

## Open Questions

1. **Should BuyFilter have a 200dma equivalent in scenario 5?**
   - What we know: Current BuyFilter checks MA10 >= MA50. Scenario 5 disables this entirely.
   - What's unclear: Should scenario 5 replace with MA10 >= sma200 check?
   - Recommendation: Per D-03 and CONTEXT.md, scenario 5 only replaces breakout buy and SELL trigger. BuyFilter is simply disabled. This is correct -- if 200dma replacement performs well, a future phase could add a 200dma-based filter.

2. **Stop loss Rule 3 still uses MA50 even when all MA50 is disabled**
   - What we know: `StopLossChecker.check()` Rule 3 fires on MA50 breakdown with volume.
   - What's unclear: Should this be disabled in scenario 4/5?
   - Recommendation: Per CONTEXT.md scope ("This phase does NOT change... stop loss behavior"), keep stop loss unchanged. Document in report that stop loss still uses MA50.

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_v2/config.py` -- existing config flags verified
- `strategies/mdm_v2/indicators.py` -- MA50 pattern verified for sma200 copy
- `strategies/mdm_v2/position_manager.py` -- SELL trigger logic at L201-208
- `strategies/mdm_v2/buy_filter.py` -- BuyFilter.check() MA10/MA50 gate
- `strategies/mdm_v2/ftd_signal.py` -- check_ma50_breakout() at L89-141
- `strategies/mdm_v2/stop_loss.py` -- Rule 3 MA50 dependency at L106-113
- `strategies/mdm_v2/sell_acceleration.py` -- MA50 breakdown check at L85-93
- `strategies/mdm_v2/mdm_v2_engine.py` -- full engine flow verified
- `analysis/validate_buy_entry.py` -- Phase 24 A/B pattern (primary reference)
- `strategies/mdm_v2/performance.py` -- V2PerformanceAnalyzer with sharpe_ratio()

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all existing
- Architecture: HIGH -- follows established Phase 24 A/B pattern exactly
- Pitfalls: HIGH -- all MA50 use sites verified by reading actual code
- 200dma implementation: HIGH -- direct copy of existing MA50 pattern

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable -- no external dependency changes expected)
