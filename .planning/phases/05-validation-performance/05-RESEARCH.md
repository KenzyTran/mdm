# Phase 5: Validation & Performance - Research

**Researched:** 2026-03-28
**Domain:** Backtesting performance analysis, train/test validation, financial metrics
**Confidence:** HIGH

## Summary

Phase 5 builds a validation and performance analysis pipeline for MDM v2. The codebase already has all the building blocks: the v2 engine (`MDMV2Engine`), signal comparison infrastructure (`compare_signals`, `extract_model_signals`), a data loader with NASDAQ normalization, hypothesis runner for automated config loading, and a classic engine for baseline comparison. The classic `PerformanceAnalyzer` provides a structural reference but lacks Sharpe ratio and daily equity tracking -- the v2 analyzer must compute daily equity from signal states rather than from trade-by-trade compounding.

The key technical challenge is building a daily equity curve from signal states (100% invested on BUY, 0% on CASH/SELL) rather than from the trade list. The trade list only records entry/exit points, but a proper equity curve, max drawdown, and Sharpe ratio require daily portfolio values. The signal-based approach (D-05) is straightforward: iterate through the engine results DataFrame, tracking daily portfolio value based on state.

Published signals span 2019-01 to 2024-11 (67 signals). The train/test split is 2019-2022 (training, Phase 4) vs 2023-2026 (held-out). The held-out period has limited signals (roughly the last ~20 of 67), so degradation thresholds must be evaluated with small-sample awareness.

**Primary recommendation:** Build a standalone `V2PerformanceAnalyzer` class in `strategies/mdm_v2/performance.py` that takes engine results DataFrame and computes all PERF-01 metrics. Validation script at `analysis/validate_v2.py` orchestrates: load best config from sweep CSV, run v2 engine, run classic engine, compute metrics for both periods, generate comparison table and multi-panel PNG.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Held-out validation uses 2023-2026 published signals. Training was 2019-2022 (Phase 4 D-12). Match rate on held-out must not drop more than 10% relative to training match rate (e.g., if training is 60%, held-out must be >=54%).
- **D-02:** Report both overall match rate and per-signal-type breakdown (Buy/Sell/Cash separately) for both training and held-out periods.
- **D-03:** Best config loaded automatically from Phase 4's parameter sweep results CSV (top-ranked row). No manual config selection required.
- **D-04:** New v2-specific PerformanceAnalyzer (not extending classic). Includes all PERF-01 metrics: equity curve, max drawdown, Sharpe ratio, win rate, total return, annualized return.
- **D-05:** Hypothetical returns model -- assume 100% allocation on Buy signal, 0% on Cash/Sell. Simple equity curve from signal timing.
- **D-06:** Sharpe ratio uses 0% risk-free rate.
- **D-07:** Analysis script generates CSV results + text summary + PNG charts. Jupyter notebook for interactive exploration.
- **D-08:** Multi-panel dashboard chart: top panel equity curve (v2 vs buy-and-hold vs classic), middle panel drawdown, bottom panel signal markers on NASDAQ price.
- **D-09:** Script lives at `analysis/validate_v2.py`.
- **D-10:** Three-row comparison table: 2019-2022 (train), 2023-2026 (held-out), 2019-2026 (full).
- **D-11:** Three-way comparison: MDM v2 vs buy-and-hold NASDAQ vs MDM classic.

### Claude's Discretion
- Exact matplotlib styling (colors, fonts, figure dimensions)
- Notebook cell structure and organization
- CSV column ordering and text summary formatting
- Internal data structures for performance results
- How to handle edge cases (insufficient held-out signals, missing dates)

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERF-01 | Backtest produces equity curve, max drawdown, Sharpe ratio, win rate | V2PerformanceAnalyzer with daily equity tracking from engine results state column; Sharpe from daily returns with 0% risk-free rate |
| PERF-02 | Performance compared against buy-and-hold baseline | Three-way comparison (v2 vs buy-and-hold vs classic) using same DataLoader and date ranges |
| PERF-03 | Train/test split validation (train on pre-2022, validate on 2022-2026) | Signal comparator's compare_signals() applied separately to 2019-2022 and 2023-2026 published signals; 10% relative degradation threshold per D-01 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.3.3 | DataFrame operations for equity curves, metrics | Already installed, project standard |
| numpy | 2.4.1 | Daily returns, Sharpe ratio calculation | Already installed, project standard |
| matplotlib | 3.10.8 | Multi-panel dashboard chart (PNG output) | Already installed, project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2+ | Unit tests for analyzer and validation | Dev dependency, already configured |

No new libraries required. All dependencies are already installed.

**Version verification:** Verified via `uv run python -c "import X; print(X.__version__)"` on 2026-03-28. All versions current in the project venv.

## Architecture Patterns

### Recommended Project Structure
```
strategies/mdm_v2/
    performance.py          # NEW: V2PerformanceAnalyzer class
analysis/
    validate_v2.py          # NEW: Main validation script
notebooks/
    v2_validation.ipynb     # NEW: Interactive exploration notebook (optional)
output/
    v2_validation_results.csv   # Generated output
    v2_validation_summary.txt   # Generated output
    v2_dashboard.png            # Generated output
tests/
    test_v2_performance.py  # NEW: Unit tests for analyzer
```

### Pattern 1: Daily Equity Curve from State Column
**What:** Build daily portfolio value by iterating engine results DataFrame. When state is BUY, portfolio tracks index returns. When state is CASH or SELL, portfolio holds flat.
**When to use:** For all equity curve, drawdown, and Sharpe calculations.
**Example:**
```python
def build_daily_equity(results_df: pd.DataFrame, initial_value: float = 1.0) -> pd.Series:
    """Build daily equity curve from engine state column.

    100% invested when state=BUY, 0% when state=CASH or SELL (per D-05).
    """
    equity = [initial_value]
    for i in range(1, len(results_df)):
        prev_close = results_df.iloc[i - 1]['close']
        curr_close = results_df.iloc[i]['close']
        state = results_df.iloc[i]['state']

        daily_return = (curr_close - prev_close) / prev_close

        if state == 'BUY':
            equity.append(equity[-1] * (1 + daily_return))
        else:
            equity.append(equity[-1])  # Flat in cash

    return pd.Series(equity, index=results_df.index)
```

### Pattern 2: Sharpe Ratio Calculation
**What:** Annualized Sharpe ratio from daily equity curve with 0% risk-free rate (D-06).
**When to use:** PERF-01 metric.
**Example:**
```python
def calculate_sharpe(equity_series: pd.Series, trading_days: int = 252) -> float:
    """Annualized Sharpe ratio with 0% risk-free rate."""
    daily_returns = equity_series.pct_change().dropna()
    if daily_returns.std() == 0:
        return 0.0
    return (daily_returns.mean() / daily_returns.std()) * np.sqrt(trading_days)
```

### Pattern 3: Auto-loading Best Config from Sweep CSV
**What:** Read sweep results CSV (top row = best config), reconstruct MDMV2Config from parameter columns.
**When to use:** D-03 automated pipeline.
**Example:**
```python
def load_best_config(sweep_csv_path: str) -> MDMV2Config:
    """Load top-ranked config from parameter sweep results."""
    df = pd.read_csv(sweep_csv_path)
    top_row = df.iloc[0]

    # Extract parameter columns (exclude score columns)
    score_cols = {'hypothesis', 'match_rate', 'buy_rate', 'sell_rate',
                  'cash_rate', 'total_published', 'total_matched'}
    param_cols = {c: top_row[c] for c in df.columns if c not in score_cols}

    return MDMV2Config(**param_cols)
```

### Pattern 4: Period-Filtered Validation
**What:** Run engine on full date range (with warm-up from 2017+), then filter published signals and engine results by period for scoring.
**When to use:** D-10 three-row comparison table.
**Example:**
```python
# Run engine once on full range
results = engine.run(full_df)
model_signals = extract_model_signals(results)

# Score per period
for label, start, end in [("Train", "2019-01-01", "2022-12-31"),
                           ("Held-out", "2023-01-01", "2026-12-31")]:
    period_published = published[
        (published['date'] >= start) & (published['date'] <= end)
    ]
    score = compare_signals(model_signals, period_published)
```

### Pattern 5: Multi-Panel Dashboard (matplotlib)
**What:** Three vertically stacked subplots sharing x-axis. Follows `analyze_drawdown.py` pattern.
**When to use:** D-08 dashboard output.
**Example:**
```python
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12),
                                      sharex=True, gridspec_kw={'height_ratios': [3, 1, 2]})
# Top: equity curves
ax1.plot(dates, v2_equity, label='MDM v2')
ax1.plot(dates, bh_equity, label='Buy & Hold')
ax1.plot(dates, classic_equity, label='MDM Classic')

# Middle: drawdown
ax2.fill_between(dates, v2_drawdown, 0, alpha=0.3)

# Bottom: price with signal markers
ax3.plot(dates, prices)
# Add buy/sell/cash markers
```

### Anti-Patterns to Avoid
- **Trade-by-trade equity only:** The classic analyzer compounds trade P&L. This misses intra-trade drawdowns and cannot compute daily Sharpe. Use daily equity from state column instead.
- **Running engine multiple times per period:** Run engine once on full data with warm-up, then slice results by date for per-period analysis.
- **Hardcoding sweep results path:** The sweep output path should be configurable, defaulting to `output/sweep_results.csv`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Signal match scoring | Custom alignment logic | `core.signal_comparator.compare_signals()` | Already handles exact-date matching, per-type breakdown |
| Model signal extraction | Manual state parsing | `core.signal_comparator.extract_model_signals()` | Maps both v1 and v2 states to Buy/Sell/Cash |
| NASDAQ data loading | Custom CSV parsing | `core.data_loader.DataLoader('nasdaq')` | Handles 1000x normalization, spot-check validation |
| Published signal loading | Custom CSV parsing | `core.signal_loader.load_signal_fixture()` | Validates signal types, parses dates |
| Running v2 with a config | Manual engine setup | `analysis.hypothesis.hypothesis_runner.run_hypothesis()` | Handles engine creation, running, signal extraction, scoring in one call |

**Key insight:** Phase 3 and 4 built substantial reusable infrastructure. The validation script should be a thin orchestration layer importing from core/ and analysis/hypothesis/.

## Common Pitfalls

### Pitfall 1: State Transition Timing for Equity
**What goes wrong:** The equity curve applies today's return based on today's state, but the state change happens during today's processing. If a BUY signal fires today, the equity should NOT include today's return (position entered at close).
**Why it happens:** Off-by-one in state vs return alignment.
**How to avoid:** Use previous day's state to determine if today's return is captured. Or use today's state but recognize that BUY entry happens at close price -- the return starts from the next day.
**Warning signs:** Equity curve shows unrealistic jumps on signal days.

### Pitfall 2: Warm-Up Period in Metrics
**What goes wrong:** Including the 2017-2019 warm-up period in performance metrics inflates the number of trading days and dilutes returns.
**Why it happens:** Engine needs warm-up data for MA50/rolling calculations, but metrics should only cover the analysis period.
**How to avoid:** Run engine on full data (start_date='2017-01-01'), but filter results to analysis period (2019+) before computing metrics.
**Warning signs:** Annualized returns seem too low, total days count is too high.

### Pitfall 3: Small Sample Held-Out Signals
**What goes wrong:** With ~20 signals in held-out period, match rate variance is high. A single signal mismatch changes rate by ~5%.
**Why it happens:** Published signals only go to 2024-11 (67 total, roughly split ~47 train / ~20 held-out).
**How to avoid:** Report absolute counts alongside percentages. Note confidence interval or sample size in the summary text.
**Warning signs:** Held-out match rate appears much worse but difference is just 1-2 signals.

### Pitfall 4: Classic Engine Uses Different Data Loader
**What goes wrong:** Classic `MDMEngine` has its own `DataLoader` in `strategies/mdm_classic/data_loader.py` which expects different CSV format.
**Why it happens:** Classic engine was migrated from old codebase with VN30 column names.
**How to avoid:** For three-way comparison, feed classic engine the same DataFrame from `core.data_loader.DataLoader('nasdaq')`. The classic `engine.run(df)` accepts a DataFrame directly.
**Warning signs:** Classic engine crashes or produces wrong prices.

### Pitfall 5: Sweep Results CSV May Not Exist
**What goes wrong:** Validation script fails on first run if Phase 4 sweep was never executed or output was cleared.
**Why it happens:** `output/` is gitignored; sweep results only exist after running the sweep.
**How to avoid:** Add clear error message if sweep CSV not found, with instructions to run the sweep first. Consider a fallback default config.
**Warning signs:** FileNotFoundError on script startup.

## Code Examples

### V2PerformanceAnalyzer Structure
```python
class V2PerformanceAnalyzer:
    """Performance analyzer for MDM v2 strategy.

    Computes equity curve, max drawdown, Sharpe ratio, win rate,
    total return, and annualized return from engine results.
    """

    TRADING_DAYS_PER_YEAR = 252

    def __init__(self, results_df: pd.DataFrame):
        self.results = results_df
        self.equity = self._build_daily_equity()

    def _build_daily_equity(self) -> pd.Series:
        """Daily equity from state column (100% BUY, 0% CASH/SELL)."""
        ...

    def total_return(self) -> float: ...
    def annualized_return(self) -> float: ...
    def max_drawdown(self) -> float: ...
    def sharpe_ratio(self) -> float: ...
    def win_rate(self, trades: list) -> float: ...
    def drawdown_series(self) -> pd.Series: ...

    def summary(self) -> dict:
        """All metrics as dict."""
        ...
```

### Validation Script Main Flow
```python
# analysis/validate_v2.py
def main():
    # 1. Load best config from sweep results
    config = load_best_config('output/sweep_results.csv')

    # 2. Load NASDAQ data (with warm-up)
    loader = DataLoader('nasdaq', data_dir=project_root)
    df = loader.load(start_date='2017-01-01')

    # 3. Load published signals
    published = load_signal_fixture(signal_path)

    # 4. Run engines
    v2_engine = MDMV2Engine(config)
    v2_results = v2_engine.run(df)

    classic_engine = MDMEngine()
    classic_results = classic_engine.run(df)

    # 5. Signal match validation (PERF-03)
    train_published = published[published['date'] <= '2022-12-31']
    heldout_published = published[published['date'] >= '2023-01-01']
    v2_signals = extract_model_signals(v2_results)

    train_score = compare_signals(v2_signals, train_published)
    heldout_score = compare_signals(v2_signals, heldout_published)

    # 6. Performance metrics (PERF-01)
    analysis_results = v2_results[v2_results['date'] >= '2019-01-01']
    v2_perf = V2PerformanceAnalyzer(analysis_results)

    # 7. Comparison table (PERF-02, D-10, D-11)
    # Three periods x three strategies

    # 8. Generate outputs
    # CSV, text summary, PNG dashboard
```

### Win Rate from V2 Trades
```python
def win_rate(trades: list) -> float:
    """Win rate from v2 trade list.

    V2 trades use 'CASH_EXIT' type (not 'SELL' like classic).
    """
    exits = [t for t in trades if t['type'] == 'CASH_EXIT']
    if not exits:
        return 0.0
    wins = sum(1 for t in exits if t.get('pnl', 0) > 0)
    return wins / len(exits)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Classic 4-state (HOLDING/CASH/WAITING_SELL/SHORT) | V2 3-state (BUY/CASH/SELL) | Phase 4 | Trade types are BUY/CASH_EXIT/SELL_SIGNAL, not BUY/SELL/SHORT/COVER |
| Trade-by-trade equity (classic analyzer) | Daily equity from state column | Phase 5 (new) | Enables proper daily Sharpe and intra-trade drawdown tracking |
| Manual config selection | Auto-load from sweep CSV top row | Phase 5 (new) | D-03 fully automated pipeline |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_v2_performance.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | Equity curve, max drawdown, Sharpe, win rate computed correctly | unit | `uv run pytest tests/test_v2_performance.py::TestV2PerformanceAnalyzer -x` | Wave 0 |
| PERF-01 | Sharpe ratio uses 0% risk-free rate | unit | `uv run pytest tests/test_v2_performance.py::test_sharpe_zero_rfr -x` | Wave 0 |
| PERF-02 | Three-way comparison table (v2 vs buy-and-hold vs classic) | unit | `uv run pytest tests/test_v2_performance.py::test_comparison_table -x` | Wave 0 |
| PERF-03 | Train/held-out match rate validation with 10% degradation check | unit | `uv run pytest tests/test_v2_performance.py::test_train_heldout_validation -x` | Wave 0 |
| PERF-03 | Per-signal-type breakdown for both periods | unit | `uv run pytest tests/test_v2_performance.py::test_per_type_breakdown -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_v2_performance.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_v2_performance.py` -- covers PERF-01, PERF-02, PERF-03
- [ ] Synthetic data fixtures for deterministic equity/drawdown/Sharpe testing

## Open Questions

1. **Sweep results CSV path**
   - What we know: Sweep outputs to `output/` directory (gitignored). D-03 says auto-load from sweep results.
   - What's unclear: Exact filename of sweep results CSV from Phase 4 execution. Code uses `save_sweep_results()` with a configurable path.
   - Recommendation: Default to `output/sweep_results.csv`, allow override via command-line arg or constant.

2. **Classic engine compatibility with core DataLoader output**
   - What we know: Classic `MDMEngine.run(df)` accepts a DataFrame. Core DataLoader outputs `[date, open, high, low, close, volume]`.
   - What's unclear: Whether classic engine expects a `symbol` column or other columns not in core DataLoader output.
   - Recommendation: Test with core DataLoader output early; add missing columns if needed.

3. **Published signals date coverage**
   - What we know: `nasdaq_signals.csv` has 67 signals from 2019-01-04 to 2024-11-06. Context says "2023-2026" for held-out.
   - What's unclear: Whether more signals will be added. Current data only goes to late 2024, not 2026.
   - Recommendation: Use "2023-2024" as the practical held-out range. Document actual date range in outputs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | Yes | 3.12.13 | -- |
| pandas | Data processing | Yes | 2.3.3 | -- |
| numpy | Metrics calculation | Yes | 2.4.1 | -- |
| matplotlib | Chart generation | Yes | 3.10.8 | -- |
| pytest | Testing | Yes | via uv dev deps | -- |
| uv | Package management | Yes | configured | -- |

No missing dependencies. All tools available.

## Sources

### Primary (HIGH confidence)
- Project codebase: `strategies/mdm_v2/` -- engine, config, position manager examined directly
- Project codebase: `core/signal_comparator.py` -- compare_signals API verified
- Project codebase: `strategies/mdm_classic/performance.py` -- reference analyzer pattern
- Project codebase: `analysis/hypothesis/parameter_sweep.py` -- sweep results format verified
- Project codebase: `analysis/analyze_drawdown.py` -- matplotlib multi-panel pattern verified
- Project codebase: `data/signals/nasdaq_signals.csv` -- 67 signals, 2019-01 to 2024-11

### Secondary (MEDIUM confidence)
- Phase 5 CONTEXT.md decisions D-01 through D-11 -- user-locked requirements

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed, versions verified
- Architecture: HIGH - patterns derived from existing codebase, clear reuse path
- Pitfalls: HIGH - identified from direct code inspection (trade types, data loader differences, warm-up periods)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain, no external dependency changes expected)
