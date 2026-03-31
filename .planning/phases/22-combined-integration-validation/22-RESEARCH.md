# Phase 22: Combined Integration & Validation - Research

**Researched:** 2026-03-31
**Domain:** Integration testing, A/B backtesting, walk-forward validation, S3 dashboard update
**Confidence:** HIGH

## Summary

Phase 22 integrates the three v5.0 filters (QE floor, SELL acceleration, BUY selectivity) and validates them operating together. The codebase already has all three filters implemented with independent enable flags in `MDMV2Config`. The validation scripts from Phases 20 and 21 (`validate_sell_acceleration.py`, `validate_buy_selectivity.py`) provide direct templates for the combined validation script. The S3 dashboard export pipeline (`export_dashboard_data.py`) needs extension to include filter-on metrics and Global Liquidity overlay data.

Key insight: This phase produces no new strategy logic. It is purely validation + reporting + dashboard. All filter code and config flags already exist. The work is (1) a new `validate_combined.py` script combining A/B comparison with walk-forward analysis, (2) a parametrized pytest for the 8 filter combinations, and (3) extending the dashboard export with new data.

**Primary recommendation:** Follow the established validation script pattern exactly (DataLoader + MDMV2Engine with toggled configs + V2PerformanceAnalyzer). The 8-combo pytest should use `@pytest.mark.parametrize` with the three boolean flags. Dashboard export extends `export_dashboard_data.py` with a new model entry and liquidity overlay data.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Compare V2 baseline (all filters OFF) vs V2+all_filters (all ON) only. No intermediate combos in the A/B report -- those are covered by the 8-combo integration test.
- **D-02:** New script `analysis/validate_combined.py` following `validate_sell_acceleration.py` pattern. Runs on both NASDAQ and VN30.
- **D-03:** Metrics: total return, CAGR, max drawdown, Sharpe ratio, trade count -- side-by-side for baseline vs all-on.
- **D-04:** Walk-forward validation integrated in the same script (pre-2020 train, 2020-2026 test). Report includes out-of-sample degradation percentage with WARNING if > 10%.
- **D-05:** CASH duration measured as average number of days in CASH state per period. Computed in `validate_combined.py` for both baseline and all-on.
- **D-06:** Report prints WARNING if all-on CASH duration exceeds 130% of baseline CASH duration. Not a hard failure -- informational WARNING.
- **D-07:** Parametrized pytest with `@pytest.mark.parametrize` over 8 combinations (True/False for qe_floor, sell_acceleration, buy_filter).
- **D-08:** Each combo runs backtest on NASDAQ 2008 and 2022 sub-periods. Assert max drawdown is not worse than V2 baseline for each sub-period.
- **D-09:** NASDAQ only -- VN30 lacks 2008 data, and NASDAQ provides sufficient coverage for both bear market regimes.
- **D-10:** Extend existing `scripts/export_dashboard_data.py` to include filter-on performance metrics (total return, Sharpe with all filters enabled).
- **D-11:** Add Global Liquidity overlay chart data to dashboard export -- liquidity index plotted over price chart with QE floor active zones highlighted.
- **D-12:** Deploy via existing `scripts/deploy_dashboard.sh` and `scripts/update_dashboard.sh` -- no new deployment scripts needed.

### Claude's Discretion
- Exact chart formatting for Global Liquidity overlay (color, opacity, annotation style)
- Test file naming and location within tests/
- validate_combined.py output format (console print, text file, or both)
- How to highlight QE floor active zones on the liquidity overlay chart
- Whether to add equity curve chart comparing baseline vs all-on in the report

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAL-05 | A/B backtest comparing V2 baseline vs V2+filters on both VN30 and NASDAQ with identical metrics | `validate_combined.py` using MDMV2Engine with toggled config flags + V2PerformanceAnalyzer for metrics (total return, CAGR, max drawdown, Sharpe, trade count) |
| VAL-06 | Update S3 dashboard with new performance metrics and Global Liquidity overlay chart | Extend `export_dashboard_data.py` with new MDMV2Engine model entry (all filters ON) + liquidity overlay data from `data/global_liquidity.csv` |
| VAL-07 | Walk-forward out-of-sample validation (train pre-2020, test 2020-2026) to detect overfitting | Same script computes in-sample vs out-of-sample degradation using `compute_period_metrics()` pattern from `validate_buy_selectivity.py` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Equity formula rule:** Must use `state[i-1]` not `state[i]` to avoid look-ahead bias. V2PerformanceAnalyzer already handles this correctly.
- **Code-Docs Sync Rule:** If strategy logic changes, update corresponding `docs/rules_*.md`. This phase adds no new strategy logic, but dashboard data changes may warrant a note in `docs/rules_mdm_v2.md`.
- **GSD Workflow Enforcement:** All changes go through GSD workflow.
- **Data scaling:** US market data prices scaled ~1000x -- DataLoader already handles normalization.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, date slicing, merge_asof | Already used throughout project |
| numpy | >= 1.24.0 | Equity calculations, busday_count | Already used throughout project |
| matplotlib | >= 3.7.0 | Comparison charts, equity curves | Already used in validation scripts |
| pytest | >= 9.0.2 | Parametrized integration test | Already configured in pyproject.toml |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | - | Dashboard data export to JSON | Already used in export_dashboard_data.py |
| aws-cli | 2.34.9 | S3 deployment | Already installed, used by deploy scripts |

### Existing Project Modules (no new dependencies)
| Module | Purpose |
|--------|---------|
| `core.data_loader.DataLoader` | Load NASDAQ and VN30 data |
| `strategies.mdm_v2.config.MDMV2Config` | Toggle all 3 filter enable flags |
| `strategies.mdm_v2.mdm_v2_engine.MDMV2Engine` | Run backtest with config |
| `strategies.mdm_v2.performance.V2PerformanceAnalyzer` | Compute metrics (total_return, max_drawdown, sharpe_ratio, annualized_return, win_rate) |

## Architecture Patterns

### Recommended Structure (new files only)
```
analysis/
  validate_combined.py          # A/B comparison + walk-forward (VAL-05, VAL-07)
tests/
  test_combined_integration.py  # 8-combo parametrized pytest (success criteria 5)
scripts/
  export_dashboard_data.py      # MODIFIED: add filter-on model + liquidity overlay (VAL-06)
output/
  combined_validation.txt       # Generated report
  combined_equity_comparison.png # Generated chart
```

### Pattern 1: A/B Validation Script (from validate_sell_acceleration.py + validate_buy_selectivity.py)
**What:** Load data, run engine twice (baseline OFF, all-filters ON), compare metrics side-by-side.
**When to use:** For `validate_combined.py`.
**Example:**
```python
# Baseline: ALL filters OFF
baseline_config = MDMV2Config(
    qe_floor_enabled=False,
    sell_acceleration_enabled=False,
    buy_filter_enabled=False,
    buy_confirmation_enabled=False,
    name="baseline",
)

# All-on: ALL filters ON
allon_config = MDMV2Config(
    qe_floor_enabled=True,
    sell_acceleration_enabled=True,
    buy_filter_enabled=True,
    buy_confirmation_enabled=True,
    confirmation_window_days=3,
    confirmation_max_dd=1,
    name="all_filters",
)

# Run both engines on same data
baseline_engine = MDMV2Engine(baseline_config)
baseline_results = baseline_engine.run(df)
allon_engine = MDMV2Engine(allon_config)
allon_results = allon_engine.run(df)

# Compare via V2PerformanceAnalyzer
baseline_analyzer = V2PerformanceAnalyzer(baseline_results, baseline_engine.get_trades())
allon_analyzer = V2PerformanceAnalyzer(allon_results, allon_engine.get_trades())
```

### Pattern 2: Walk-Forward Degradation (from validate_buy_selectivity.py)
**What:** Split results into in-sample (pre-2020) and out-of-sample (2020-2026), compute metrics for each period, measure degradation.
**When to use:** For overfitting detection in `validate_combined.py`.
**Example:**
```python
WALK_FORWARD_SPLIT = '2020-01-01'

# Compute metrics for each period
is_metrics = compute_period_metrics(results, trades, '2004-01-01', '2019-12-31')
oos_metrics = compute_period_metrics(results, trades, WALK_FORWARD_SPLIT, '2026-12-31')

# Degradation = (in_sample - out_of_sample) / abs(in_sample)
degradation = (is_metrics['total_return'] - oos_metrics['total_return']) / abs(is_metrics['total_return'])

if abs(degradation) > 0.10:
    print("WARNING: Degradation exceeds 10% threshold")
```

### Pattern 3: CASH Duration Computation (new for this phase)
**What:** Count average consecutive days in CASH state per entry into CASH.
**When to use:** For CASH duration guard check (D-05, D-06).
**Example:**
```python
def compute_avg_cash_duration(results_df):
    """Compute average number of consecutive days in CASH state."""
    states = results_df['state'].values
    cash_durations = []
    current_run = 0
    for s in states:
        if s == 'CASH':
            current_run += 1
        else:
            if current_run > 0:
                cash_durations.append(current_run)
            current_run = 0
    if current_run > 0:
        cash_durations.append(current_run)
    return np.mean(cash_durations) if cash_durations else 0.0
```

### Pattern 4: Parametrized Pytest for 8 Combinations (D-07, D-08)
**What:** Test all 8 on/off combinations of 3 boolean filter flags on bear market sub-periods.
**When to use:** For `test_combined_integration.py`.
**Example:**
```python
import pytest
from itertools import product

COMBOS = list(product([True, False], repeat=3))

@pytest.mark.parametrize("qe,sell_accel,buy_filt", COMBOS)
def test_filter_combo_2008(nasdaq_data, baseline_dd_2008, qe, sell_accel, buy_filt):
    config = MDMV2Config(
        qe_floor_enabled=qe,
        sell_acceleration_enabled=sell_accel,
        buy_filter_enabled=buy_filt,
        buy_confirmation_enabled=buy_filt,  # buy_confirmation follows buy_filter
    )
    engine = MDMV2Engine(config)
    results = engine.run(nasdaq_data)
    # Slice to 2008 bear period and check drawdown
    analyzer = V2PerformanceAnalyzer(period_results, engine.get_trades())
    assert analyzer.max_drawdown() >= baseline_dd_2008 - 0.001
```

### Pattern 5: Dashboard Export Extension (D-10, D-11)
**What:** Add a new model entry to `export_dashboard_data.py` for MDMV2Engine with all filters ON, plus liquidity overlay data.
**When to use:** For VAL-06 dashboard update.
**Key considerations:**
- Current dashboard runs HybridEngine on VN30 only. New entry uses MDMV2Engine directly.
- Liquidity overlay: export `data/global_liquidity.csv` columns (date, global_liquidity, qe_floor) as JSON array for chart overlay.
- QE floor active zones: periods where `qe_floor == 1` become shaded regions on the chart (start_date, end_date pairs).

### Anti-Patterns to Avoid
- **Running engine with state[i] instead of state[i-1]:** V2PerformanceAnalyzer already handles this. Never compute equity manually.
- **Testing VN30 on 2008 sub-period:** VN30 data starts 2018. Only NASDAQ has 2008 data (per D-09).
- **Hardcoding filter defaults in validation script:** Use MDMV2Config defaults. Currently `sell_acceleration_enabled` and `buy_filter_enabled` default to True -- baseline config must explicitly set all to False.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Equity curve computation | Custom equity loop | `V2PerformanceAnalyzer` | Handles state[i-1] rule, short positions, edge cases |
| Performance metrics | Custom Sharpe/drawdown | `V2PerformanceAnalyzer.summary()` | Already validated, uses correct annualization |
| Data loading + normalization | Custom CSV reader | `DataLoader('nasdaq')` / `DataLoader('vn30')` | Handles 1000x scaling, column mapping |
| Walk-forward split | Custom date logic | `compute_period_metrics()` pattern | Tested in validate_buy_selectivity.py |
| Liquidity merge to daily | Custom join logic | `LiquidityLoader.load_and_merge()` | Handles publication lag, merge_asof |

## Common Pitfalls

### Pitfall 1: Config Defaults Changed Since Phase 19
**What goes wrong:** `MDMV2Config()` now defaults `sell_acceleration_enabled=True`, `buy_filter_enabled=True`, `buy_confirmation_enabled=True`. A "baseline" config that omits these gets filters ON, not OFF.
**Why it happens:** Defaults evolved as phases completed (Phase 20 turned on sell_acceleration, Phase 21 turned on buy filters).
**How to avoid:** Baseline config MUST explicitly set ALL filter flags to False.
**Warning signs:** Baseline producing different results than expected V2 behavior.

### Pitfall 2: buy_confirmation_enabled Must Track buy_filter_enabled
**What goes wrong:** Setting `buy_filter_enabled=True` but forgetting `buy_confirmation_enabled=True` (or vice versa) creates inconsistent filter behavior.
**Why it happens:** They are separate flags but were designed to work together (Phase 21).
**How to avoid:** Always toggle both together in test combinations. For the 8-combo test, treat them as one flag.
**Warning signs:** Buy confirmation never triggers because filter is off.

### Pitfall 3: QE Floor Requires CSV File Access
**What goes wrong:** Tests with `qe_floor_enabled=True` fail because `data/global_liquidity.csv` is not found (path relative to working directory).
**Why it happens:** LiquidityLoader uses relative path by default. Tests may run from different directory.
**How to avoid:** Use the WORKTREE_ROOT pattern from `test_qe_floor.py` to resolve data directory. Set `liquidity_csv_path` explicitly in config for tests.
**Warning signs:** FileNotFoundError on liquidity CSV.

### Pitfall 4: Walk-Forward Degradation Metric Interpretation
**What goes wrong:** Degradation formula gives misleading results when in-sample return is negative or near zero.
**Why it happens:** Division by near-zero in-sample value amplifies noise.
**How to avoid:** Use `safe_degradation()` pattern from validate_buy_selectivity.py with guard for zero division.
**Warning signs:** Degradation > 100% or negative when both periods have positive returns.

### Pitfall 5: CAGR Computation Not in V2PerformanceAnalyzer
**What goes wrong:** D-03 requires CAGR in the report, but `V2PerformanceAnalyzer` only has `annualized_return()`, not CAGR specifically.
**Why it happens:** `annualized_return()` IS the CAGR (compound annual growth rate). It uses `(1 + total_return) ** (1/years) - 1`.
**How to avoid:** Use `analyzer.annualized_return()` and label it CAGR in the report.
**Warning signs:** None -- just a naming difference.

### Pitfall 6: Dashboard Export Uses HybridEngine, Not MDMV2Engine
**What goes wrong:** Trying to add MDMV2Engine model to a pipeline that assumes HybridEngine interface.
**Why it happens:** `export_dashboard_data.py` currently imports and uses `HybridEngine` with `HybridConfig`.
**How to avoid:** Add a separate export function for MDMV2Engine models. The compute_equity and compute_metrics functions in the export script can work with any engine that produces results with 'date', 'close', 'state' columns. MDMV2Engine produces the same column format.
**Warning signs:** Import errors or missing config parameters.

## Code Examples

### CASH Duration Computation
```python
# Source: Novel for this phase, based on state column analysis
def compute_avg_cash_duration(results_df):
    """Average consecutive days in CASH state per CASH episode."""
    states = results_df['state'].values
    durations = []
    run = 0
    for s in states:
        if s == 'CASH':
            run += 1
        else:
            if run > 0:
                durations.append(run)
            run = 0
    if run > 0:
        durations.append(run)
    return np.mean(durations) if durations else 0.0
```

### QE Floor Zone Extraction for Dashboard
```python
# Source: Based on global_liquidity.csv qe_floor column
def extract_qe_zones(liquidity_df):
    """Extract QE floor active date ranges for chart overlay."""
    zones = []
    in_zone = False
    start = None
    for _, row in liquidity_df.iterrows():
        if row['qe_floor'] == 1 and not in_zone:
            start = row['date']
            in_zone = True
        elif row['qe_floor'] == 0 and in_zone:
            zones.append({'start': start, 'end': row['date']})
            in_zone = False
    if in_zone:
        zones.append({'start': start, 'end': liquidity_df['date'].iloc[-1]})
    return zones
```

### Full Metrics Table Row Generation
```python
# Source: Combined from validate_sell_acceleration.py + validate_buy_selectivity.py patterns
def compute_full_metrics(results_df, trades):
    """Compute all D-03 required metrics."""
    analyzer = V2PerformanceAnalyzer(results_df, trades)
    exit_trades = [t for t in trades if t.get('type') in ('CASH_EXIT', 'SHORT_COVER')]
    return {
        'total_return': analyzer.total_return(),
        'cagr': analyzer.annualized_return(),  # CAGR = annualized_return
        'max_drawdown': analyzer.max_drawdown(),
        'sharpe': analyzer.sharpe_ratio(),
        'trade_count': len(exit_trades),
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Individual filter validation | Combined A/B + walk-forward | Phase 22 | Proves filters don't conflict |
| Dashboard with HybridEngine only | Dashboard with V2+filters model | Phase 22 | Shows latest strategy performance |
| No CASH duration tracking | CASH duration guard | Phase 22 | Detects capital trapping from excessive filtering |

## Open Questions

1. **Dashboard model naming for V2+filters**
   - What we know: Current dashboard has mdm_v2, mdm_hybrid, mdm_p15 model keys
   - What's unclear: Whether to add a new model key (e.g., 'mdm_v2_filtered') or replace 'mdm_v2'
   - Recommendation: Add new key 'mdm_v2_filtered' to show both baseline and filtered side-by-side

2. **VN30 QE floor applicability**
   - What we know: STATE.md notes "Global liquidity filter applicability to VN30 is unproven"
   - What's unclear: Whether A/B on VN30 with qe_floor ON is meaningful
   - Recommendation: Run both NASDAQ and VN30 per D-02, but note VN30 QE floor results as informational. The walk-forward validation will reveal if it helps or hurts VN30.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All scripts | Yes | 3.10+ | -- |
| pytest | 8-combo integration test | Yes | 9.0.2 | -- |
| pandas | All data processing | Yes | >= 2.0.0 | -- |
| numpy | Metric calculations | Yes | >= 1.24.0 | -- |
| matplotlib | Comparison charts | Yes | >= 3.7.0 | -- |
| AWS CLI | S3 dashboard deploy | Yes | 2.34.9 | -- |
| uv | Package runner | Yes | Configured | -- |
| data/global_liquidity.csv | QE floor overlay | Yes | 987 rows (2007-2026) | -- |

**Missing dependencies:** None. All tools available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_combined_integration.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAL-05 | A/B backtest baseline vs filters, NASDAQ + VN30 | integration (script) | `uv run python analysis/validate_combined.py` | Wave 0 |
| VAL-05 | 8 filter combos max drawdown not worse than baseline | unit (pytest) | `uv run pytest tests/test_combined_integration.py -x` | Wave 0 |
| VAL-05 | CASH duration under 130% of baseline | integration (script) | `uv run python analysis/validate_combined.py` | Wave 0 |
| VAL-06 | Dashboard export includes filter metrics + liquidity overlay | smoke | `uv run python scripts/export_dashboard_data.py` | Existing (modified) |
| VAL-07 | Walk-forward degradation < 10% | integration (script) | `uv run python analysis/validate_combined.py` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_combined_integration.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green + `uv run python analysis/validate_combined.py` passes all checks

### Wave 0 Gaps
- [ ] `tests/test_combined_integration.py` -- 8-combo parametrized test covering VAL-05 success criterion 5
- [ ] `analysis/validate_combined.py` -- A/B + walk-forward validation script covering VAL-05, VAL-07, success criteria 1-4

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_v2/config.py` -- MDMV2Config with all filter enable flags (qe_floor_enabled, sell_acceleration_enabled, buy_filter_enabled, buy_confirmation_enabled)
- `strategies/mdm_v2/mdm_v2_engine.py` -- Engine wiring for all filters, conditional initialization based on config flags
- `strategies/mdm_v2/performance.py` -- V2PerformanceAnalyzer with total_return, max_drawdown, sharpe_ratio, annualized_return, win_rate
- `analysis/validate_sell_acceleration.py` -- A/B bear market validation script template (228 lines)
- `analysis/validate_buy_selectivity.py` -- Walk-forward validation script template (467 lines)
- `scripts/export_dashboard_data.py` -- Dashboard export pipeline (315 lines)
- `data/global_liquidity.csv` -- 987 weekly observations (2007-2026) with qe_floor column

### Secondary (MEDIUM confidence)
- `tests/test_qe_floor.py` -- WORKTREE_ROOT pattern for resolving data directory in tests
- `tests/test_buy_selectivity.py` -- Parametrized test patterns for filter assertions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, versions verified in pyproject.toml
- Architecture: HIGH -- directly follows two existing validation script patterns
- Pitfalls: HIGH -- identified from actual codebase analysis (config defaults, engine interfaces, path resolution)

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable -- no external dependency changes expected)
