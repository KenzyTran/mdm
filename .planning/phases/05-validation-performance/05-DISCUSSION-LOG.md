# Phase 5: Validation & Performance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 05-validation-performance
**Areas discussed:** Validation criteria, Performance metrics, Report & visualization, Buy-and-hold comparison

---

## Validation criteria

### Match rate degradation threshold

| Option | Description | Selected |
|--------|-------------|----------|
| 10% relative drop | If training match rate is 60%, held-out must be >=54%. Reasonable tolerance for overfitting detection. | ✓ |
| 5% absolute drop | Held-out must be within 5 percentage points of training. Stricter. | |
| No threshold -- report only | Just report both rates side by side. Manual judgment. | |

**User's choice:** 10% relative drop
**Notes:** None

### Per-signal-type validation

| Option | Description | Selected |
|--------|-------------|----------|
| Overall + per-type breakdown | Report overall match rate plus Buy/Sell/Cash rates separately. | ✓ |
| Overall only | Single match rate number. Simpler. | |

**User's choice:** Overall + per-type breakdown
**Notes:** None

### Config source for validation

| Option | Description | Selected |
|--------|-------------|----------|
| Load best from sweep CSV | Read top-ranked config from Phase 4's sweep results. Fully automated. | ✓ |
| Manual config file | User specifies config by name or file path. | |

**User's choice:** Load best from sweep CSV
**Notes:** None

---

## Performance metrics

### Analyzer approach

| Option | Description | Selected |
|--------|-------------|----------|
| New v2 PerformanceAnalyzer | Build in analysis/ or strategies/mdm_v2/. Includes Sharpe. Classic stays untouched. | ✓ |
| Extend classic analyzer | Add Sharpe to existing class. Less code but modifies classic. | |
| Shared core analyzer | Move to core/performance.py. Strategy-agnostic. Bigger refactor. | |

**User's choice:** New v2 PerformanceAnalyzer
**Notes:** None

### Trade simulation

| Option | Description | Selected |
|--------|-------------|----------|
| Hypothetical returns | 100% allocation on Buy, 0% on Cash/Sell. Simple equity curve from signal timing. | ✓ |
| Position-based simulation | Actual buy/sell execution with stop losses and trade records. | |

**User's choice:** Hypothetical returns
**Notes:** None

### Risk-free rate for Sharpe

| Option | Description | Selected |
|--------|-------------|----------|
| 0% risk-free rate | Standard for backtesting comparisons. No external data dependency. | ✓ |
| US Treasury rate | Approximate average yield per period. More academically correct. | |

**User's choice:** 0% risk-free rate
**Notes:** None

---

## Report & visualization

### Output formats

| Option | Description | Selected |
|--------|-------------|----------|
| Script + notebook | Analysis script generates CSV + text + PNG. Jupyter for interactive. Phase 3 pattern. | ✓ |
| Script only | Standalone script. No notebook. | |
| Notebook only | All analysis in Jupyter. Not scriptable. | |

**User's choice:** Script + notebook
**Notes:** None

### Equity curve detail

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-panel dashboard | Top: equity curve (v2 vs B&H). Middle: drawdown. Bottom: signal markers. One PNG. | ✓ |
| Simple equity curve | Single chart with buy-and-hold overlay. | |
| Separate charts | Individual PNGs per metric. | |

**User's choice:** Multi-panel dashboard
**Notes:** None

### Script location

| Option | Description | Selected |
|--------|-------------|----------|
| analysis/validate_v2.py | Follows existing pattern alongside analyze_drawdown.py. | ✓ |
| scripts/validate_v2.py | Entry-point script alongside run_backtest.py. | |

**User's choice:** analysis/validate_v2.py
**Notes:** None

---

## Buy-and-hold comparison

### Comparison structure

| Option | Description | Selected |
|--------|-------------|----------|
| Full period + train/test split | Three rows: 2019-2022, 2023-2026, 2019-2026. Aligned with validation split. | ✓ |
| Full period only | Single comparison over 2019-2026. | |
| Annual breakdown | Year-by-year table. Most granular but noisy. | |

**User's choice:** Full period + train/test split
**Notes:** None

### Baselines

| Option | Description | Selected |
|--------|-------------|----------|
| v2 + buy-and-hold + classic | Three-way comparison showing v2 improvement over both baselines. | ✓ |
| v2 + buy-and-hold only | Two-way comparison per PERF-02. | |

**User's choice:** v2 + buy-and-hold + classic
**Notes:** None

---

## Claude's Discretion

- Exact matplotlib styling (colors, fonts, figure dimensions)
- Notebook cell structure and organization
- CSV column ordering and text summary formatting
- Internal data structures for performance results
- Edge case handling (insufficient held-out signals, missing dates)

## Deferred Ideas

None -- discussion stayed within phase scope
