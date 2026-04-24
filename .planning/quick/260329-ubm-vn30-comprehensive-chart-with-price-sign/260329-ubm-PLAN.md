---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/generate_vn30_report_chart.py
  - output/vn30_report_chart.png
autonomous: true
requirements: [QUICK-01]
must_haves:
  truths:
    - "Script runs end-to-end and produces a high-res PNG chart"
    - "Panel 1 shows VN30 price line with Buy/Sell/Cash signal markers from V2 engine"
    - "Panel 2 shows 3 equity curves: V2 State Machine, Hybrid (3 filters), Buy & Hold"
    - "Chart is visually clear at Telegram resolution (300 DPI, ~16x10 inches)"
  artifacts:
    - path: "scripts/generate_vn30_report_chart.py"
      provides: "Self-contained chart generation script"
    - path: "output/vn30_report_chart.png"
      provides: "High-resolution report chart PNG"
  key_links:
    - from: "scripts/generate_vn30_report_chart.py"
      to: "strategies/mdm_v2/mdm_v2_engine.py"
      via: "MDMV2Engine import and run()"
    - from: "scripts/generate_vn30_report_chart.py"
      to: "strategies/mdm_hybrid/mdm_hybrid_engine.py"
      via: "HybridEngine import and run()"
---

<objective>
Create a comprehensive VN30 report chart for boss presentation via Telegram.

Purpose: Generate a professional 2-panel chart comparing MDM strategies on VN30 data (2015-2026), with signal markers and equity curve comparison.
Output: `scripts/generate_vn30_report_chart.py` script and `output/vn30_report_chart.png` PNG file.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@analysis/backtest_vn30.py (existing VN30 backtest with dashboard chart pattern)
@strategies/mdm_v2/mdm_v2_engine.py (V2 engine API)
@strategies/mdm_hybrid/mdm_hybrid_engine.py (Hybrid engine API)
@strategies/mdm_v2/vn30_filters.py (VN30 microstructure filters)
@strategies/mdm_v2/performance.py (V2PerformanceAnalyzer for equity curves)
@core/data_loader.py (DataLoader for VN30 data)

<interfaces>
From core/data_loader.py:
```python
class DataLoader:
    def __init__(self, market: str, data_dir: Optional[str] = None): ...
    def load(self, start_date=None, end_date=None) -> pd.DataFrame: ...
    # Returns: [date, open, high, low, close, volume]
```

From strategies/mdm_v2/mdm_v2_engine.py:
```python
class MDMV2Engine:
    def __init__(self, config: MDMV2Config = None): ...
    def run(self, df: pd.DataFrame) -> pd.DataFrame: ...
    # Results df has: date, close, state ('BUY'/'CASH'/'SELL'), action, is_ftd, etc.
    def get_trades(self) -> list: ...
```

From strategies/mdm_hybrid/mdm_hybrid_engine.py:
```python
class HybridEngine:
    def __init__(self, config: HybridConfig = None): ...
    def run(self, df: pd.DataFrame) -> pd.DataFrame: ...
    # Same result schema as V2, plus: old_state, proposed, verdict, confidence
    def get_trades(self) -> list: ...
```

From strategies/mdm_hybrid/config.py:
```python
class HybridConfig:
    v2_config: MDMV2Config
    two_phase_enabled: bool = True
    filter_enabled: bool = False  # Set True to enable 3 filters
    filter_config: FilterConfig
```

From strategies/mdm_v2/vn30_filters.py:
```python
def apply_vn30_filters(df: pd.DataFrame) -> pd.DataFrame:
    # Adds is_limit_day, is_expiry_day columns
```

From strategies/mdm_v2/performance.py:
```python
class V2PerformanceAnalyzer:
    def __init__(self, results_df: pd.DataFrame, trades: list = None): ...
    self.equity  # pd.Series, equity curve starting at 1.0
    def summary(self) -> dict: ...
    # Returns: total_return, annualized_return, max_drawdown, sharpe_ratio, win_rate
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create VN30 report chart generation script</name>
  <files>scripts/generate_vn30_report_chart.py</files>
  <action>
Create a self-contained script that:

1. **Data loading:** Use `DataLoader('vn30', data_dir=project_root)` to load VN30 data with `start_date='2012-01-01'` (warmup). Apply `apply_vn30_filters(df)` from `strategies.mdm_v2.vn30_filters`.

2. **Run V2 State Machine:** Create `MDMV2Engine()` with default config, call `engine.run(df)`. Get trades via `engine.get_trades()`.

3. **Run Hybrid (3 filters):** Create `HybridEngine(HybridConfig(filter_enabled=True))`, call `engine.run(df)`. Get trades via `engine.get_trades()`.

4. **Filter to analysis period:** Filter results to `date >= '2015-01-01'` for the chart display period (consistent with user's reported numbers 2015-2026).

5. **Build equity curves:** Use `V2PerformanceAnalyzer(results, trades).equity` for both V2 and Hybrid. Build buy-and-hold equity as `close / close.iloc[0]`.

6. **Chart layout — 2 panels, figsize=(18, 11), DPI=300:**

   **Panel 1 (top, height ratio 3): VN30 Price + Signals**
   - Plot VN30 close price as black line (linewidth=1.0)
   - From V2 results, mark signal transitions:
     - Green up-arrow ('^') markersize=10 for BUY signals (action contains 'BUY' and state becomes BUY)
     - Red down-arrow ('v') markersize=10 for SELL signals (action contains 'SELL' and state becomes SELL)
     - Orange/gold diamond ('D') markersize=7 for CASH exits (action contains 'CASH' and state becomes CASH)
   - Use `state` column transitions: iterate results, when `state` changes from previous row, that is a signal point
   - Title: "VN30 Market Direction Model - Strategy Comparison (2015-2026)"
   - Legend with signal markers
   - Grid alpha=0.3

   **Panel 2 (bottom, height ratio 2): Equity Curves**
   - Blue line: "V2 State Machine" equity (linewidth=1.5)
   - Red/orange line: "Hybrid (3 Filters)" equity (linewidth=1.5)
   - Gray dashed line: "Buy & Hold" equity (linewidth=1.0, alpha=0.7)
   - Add text annotations at the end of each line showing final return %
   - Y-axis label: "Growth of $1"
   - Legend in upper-left
   - Grid alpha=0.3

7. **Performance summary text box:** Add a text box in Panel 2 (lower-right area) with key metrics:
   ```
   V2: CAGR 20.2%, MaxDD -7.5%
   Hybrid: CAGR 12.4%, MaxDD -10.3%
   B&H: CAGR 11.9%, MaxDD -48.1%
   ```
   Compute these from the actual analyzer results, not hardcoded.

8. **Style:** Use `matplotlib.use('Agg')`. Use `plt.tight_layout()`. Font sizes: title 14, axes labels 11, legend 9, annotations 9. Save to `output/vn30_report_chart.png` at 300 DPI with `bbox_inches='tight'`.

9. **Entry point:** `if __name__ == '__main__':` block. Add sys.path setup like existing scripts. Print progress messages.

Important notes:
- Use `WARMUP_START = '2012-01-01'` and `ANALYSIS_START = '2015-01-01'` constants
- Both engines need the SAME input df (loaded once, copied for each engine run)
- The V2 engine uses `from strategies.mdm_v2.config import MDMV2Config` (NOT from hybrid config)
- The Hybrid engine uses `from strategies.mdm_hybrid.config import HybridConfig`
- Signal detection for Panel 1: use V2 results state transitions (compare state[i] vs state[i-1])
  </action>
  <verify>
    <automated>cd C:/Users/trant/projects/mdm && uv run python scripts/generate_vn30_report_chart.py</automated>
  </verify>
  <done>
    - Script runs without errors
    - output/vn30_report_chart.png exists and is > 100KB (high-res chart)
    - Chart has 2 panels: price+signals and equity curves
    - Console prints final metrics for V2, Hybrid, and Buy & Hold
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>VN30 comprehensive report chart with 2 panels: price+signals and equity curve comparison</what-built>
  <how-to-verify>
    1. Open `output/vn30_report_chart.png` in image viewer
    2. Verify Panel 1 shows VN30 price with green (Buy), red (Sell), orange (Cash) markers
    3. Verify Panel 2 shows 3 equity curves clearly distinguishable
    4. Verify metrics text box shows computed CAGR and MaxDD values
    5. Verify chart is sharp and readable (suitable for Telegram at 300 DPI)
  </how-to-verify>
  <resume-signal>Type "approved" or describe visual issues to fix</resume-signal>
</task>

</tasks>

<verification>
- `uv run python scripts/generate_vn30_report_chart.py` exits with code 0
- `output/vn30_report_chart.png` file exists and is > 100KB
- Console output shows V2, Hybrid, and Buy & Hold metrics
</verification>

<success_criteria>
- High-resolution PNG chart suitable for Telegram sharing with boss
- Panel 1: VN30 price line with Buy/Sell/Cash signal markers from V2 engine
- Panel 2: Three equity curves (V2, Hybrid, Buy & Hold) with performance annotations
- All metrics computed from actual backtest runs (not hardcoded)
</success_criteria>

<output>
After completion, create `.planning/quick/260329-ubm-vn30-comprehensive-chart-with-price-sign/260329-ubm-SUMMARY.md`
</output>
