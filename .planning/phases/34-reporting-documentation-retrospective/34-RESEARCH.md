# Phase 34: Reporting + Documentation + Retrospective - Research

**Researched:** 2026-04-10
**Domain:** Performance reporting, benchmark comparison, documentation, project milestone closure
**Confidence:** HIGH

## Summary

Phase 34 is a reporting and documentation phase that ships v7.0 as a milestone. The core work involves: (1) extending the existing metrics pipeline (`analysis/_vn100_pipeline.py`) to compute missing metrics (profit factor, Sharpe with rf=10Y VN govt ~3%), (2) building a benchmark comparison table including VN30 B&H, 12M deposit, and SJC gold, (3) computing real (CPI-adjusted) CAGR, (4) updating `docs/rules_canslim_mdm.md` to reflect final locked parameters, (5) creating a data dictionary for connectors and CANSLIM scorer, (6) writing a v7.0 retrospective entry, and (7) updating project management docs.

Most of the existing infrastructure is already in place. The `_vn100_pipeline.py` computes CAGR, Sharpe_rf3, MaxDD, hit_rate, turnover, cost_drag, num_trades, and avg_hold_days. Phase 33 produced OOS metrics JSON and baselines JSON with strategy, CANSLIM-only, MDM-only-on-index, and VN-Index B&H benchmarks. The gaps are: profit factor (not computed), VN30 B&H benchmark (not in Phase 33 baselines), 12M deposit benchmark, SJC gold benchmark, and real CAGR (CPI adjustment).

**Primary recommendation:** Build a standalone `analysis/generate_v7_report.py` script that reads existing Phase 33 outputs, computes missing metrics, fetches/hardcodes benchmark data, and produces a comprehensive JSON report + markdown summary for dashboard integration.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BT-05 | Performance report: CAGR, Sharpe (rf=10Y VN govt ~3%), MaxDD + duration, hit rate, profit factor, hold time, turnover, cost drag | Existing pipeline computes all except profit factor. Sharpe already uses rf=3%. Add profit_factor to metrics dict. |
| BT-06 | Benchmark comparison: VN-Index B&H, VN30 B&H, MDM-only-on-index, 12M deposit, SJC gold | VN-Index B&H and MDM-only already in baselines.json. Need VN30 B&H (data in data/vn30_price.csv), 12M deposit (~5-6% avg), SJC gold (hardcode or fetch). |
| BT-07 | Real (inflation-adjusted) CAGR alongside nominal | CPI data needed. Vietnam avg CPI ~3-4% over 2019-2025. Can hardcode annual CPI or source from GSO. |
| DOC-01 | `docs/rules_canslim_mdm.md` documenting locked CANSLIM rules, entry options, portfolio policies, MDM gate, costs | File exists with Phase 31 content. Needs update with locked Phase 32 sweep params (rank-1 config) and Phase 33 OOS results. |
| DOC-02 | Data dictionary for connectors and CANSLIM scorer | New file needed. Document `connectors/postgres.py`, `connectors/mysql.py`, `connectors/adjust.py`, `connectors/eps.py`, `strategies/canslim/scorer.py` schemas. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | Metrics computation, NAV series processing | Already in project stack |
| numpy | >= 1.24.0 | Statistical calculations (Sharpe, drawdown) | Already in project stack |
| matplotlib | >= 3.7.0 | Performance charts if dashboard updated | Already in project stack |
| json (stdlib) | - | Report output format | Consistent with existing metrics.json pattern |

### Supporting
No new dependencies needed. All reporting uses existing project libraries.

## Architecture Patterns

### Report Generation Pattern
```
analysis/generate_v7_report.py
  ├── Reads: docs/audits/phase33/oos_metrics.json
  ├── Reads: docs/audits/phase33/baselines.json
  ├── Reads: docs/audits/phase33/oos_trades.csv
  ├── Reads: docs/audits/phase33/oos_nav.csv
  ├── Computes: missing metrics (profit_factor)
  ├── Computes: additional benchmarks (VN30 B&H, deposit, gold)
  ├── Computes: real CAGR (CPI-adjusted)
  ├── Writes: docs/audits/phase34/v7_report.json
  └── Writes: docs/audits/phase34/v7_report.md
```

### Existing Metrics Pipeline
The `analysis/_vn100_pipeline.py` (lines 630-710) computes metrics from `PortfolioResult`. Key current metrics:
- `CAGR` - annualized compound growth
- `Sharpe_rf3` - Sharpe with rf=3% (already matches BT-05 requirement)
- `MaxDD` - maximum drawdown ratio
- `MaxDD_duration_days` - longest underwater period
- `hit_rate` - wins / total trades
- `turnover` - total buy notional / mean NAV
- `total_cost_drag_pct` - total costs / initial NAV
- `num_trades` - count
- `avg_hold_days` - mean holding period

### Missing Metric: Profit Factor
```python
# profit_factor = sum(winning PnL) / abs(sum(losing PnL))
# Source: trades list from PortfolioResult
gross_profits = sum(t.pnl_pct for t in trades if t.pnl_pct > 0)
gross_losses = abs(sum(t.pnl_pct for t in trades if t.pnl_pct < 0))
profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')
```

### Benchmark Data Sources

| Benchmark | Data Source | Method |
|-----------|------------|--------|
| VN-Index B&H | Already in `baselines.json` | CAGR=10.42%, Sharpe=0.383, MaxDD=-40.34% |
| VN30 B&H | `data/vn30_price.csv` or Postgres `index_eod` | Compute from OHLCV same period 2019-2025 |
| MDM-only-on-index | Already in `baselines.json` | CAGR=8.01%, Sharpe=0.508, MaxDD=-15.60% |
| 12M deposit | Hardcode annual rates | ~5-6% avg nominal; Vietnam SBV rates 2019-2025 |
| SJC gold | Hardcode or manual lookup | SJC gold VND price 2019 vs 2025 for CAGR |

### Real CAGR Computation
```python
# real_cagr = (1 + nominal_cagr) / (1 + avg_inflation) - 1
# Vietnam CPI 2019-2025 approximate annual rates:
# 2019: 2.79%, 2020: 3.23%, 2021: 1.84%, 2022: 3.15%, 2023: 3.25%, 2024: ~3.6%, 2025: ~3.5%
# Geometric mean ~3.0%
avg_cpi = 0.03  # approximate
real_cagr = (1 + nominal_cagr) / (1 + avg_cpi) - 1
```

### Anti-Patterns to Avoid
- **Re-running backtests:** Phase 33 already ran OOS. Use existing output files, do not re-run the pipeline.
- **Fetching live data for benchmarks:** Gold/deposit rates don't need API calls. Hardcode well-documented values with source citations.
- **Modifying `_vn100_pipeline.py`:** Compute profit_factor in the report script, not by modifying the shared pipeline (avoids breaking Phase 32/33 contracts).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sharpe ratio | Custom formula | Already computed as `Sharpe_rf3` in pipeline | Already uses rf=3% as required |
| Drawdown analysis | New drawdown module | Read existing `oos_nav.csv` | Phase 33 already produced this |
| Dashboard data export | New export pipeline | Extend `scripts/export_dashboard_data.py` | Existing pattern handles JSON + HTML |

## Common Pitfalls

### Pitfall 1: Inconsistent Benchmark Periods
**What goes wrong:** Computing VN30 B&H over a different date range than the strategy OOS period.
**Why it happens:** VN30 data might have different start/end dates than the 2019-2025 OOS period.
**How to avoid:** Filter VN30 data to exactly match `PERIOD = ("2019-01-01", "2025-12-31")` from Phase 33.
**Warning signs:** Benchmark CAGR dramatically different from expected range.

### Pitfall 2: Stale docs/rules_canslim_mdm.md
**What goes wrong:** The file references "Phase 31" and says "no production VN100 backtest yet". Phase 32/33 have since run backtests and locked parameters.
**Why it happens:** Code-Docs Sync Rule only triggers on code changes. Phase 32/33 changed parameters but the engine code didn't change.
**How to avoid:** Update the file to reflect rank-1 locked params: `c_yoy=0.25, a_cagr=0.20, n_prox=0.10, hard_stop=0.06, slots=5, entry=C`.

### Pitfall 3: CPI Data Sourcing
**What goes wrong:** Spending excessive time finding exact annual CPI figures for Vietnam.
**Why it happens:** Vietnam GSO publishes CPI but not always in machine-readable format.
**How to avoid:** Hardcode well-known approximate values with source citation (GSO.gov.vn). The real CAGR is a secondary metric; +/- 0.5% CPI precision is acceptable.

### Pitfall 4: Gold Price in VND
**What goes wrong:** Using international gold (USD/oz) instead of SJC gold (VND/tael).
**Why it happens:** International gold data is easier to find programmatically.
**How to avoid:** The requirement says "SJC gold" specifically. Use VND-denominated SJC prices. Hardcode start/end values for 2019 and 2025.

### Pitfall 5: Dashboard Update Scope Creep
**What goes wrong:** Attempting to rebuild the dashboard for CANSLIM+MDM when the existing dashboard is MDM-on-VN30.
**Why it happens:** The UI hint says "yes" but the dashboard currently shows MDM models, not the CANSLIM portfolio.
**How to avoid:** Add a new tab or section to existing dashboard rather than rebuilding. Alternatively, generate a standalone HTML report.

## Code Examples

### Reading Existing Phase 33 Outputs
```python
import json
import pandas as pd

# Metrics already computed
with open("docs/audits/phase33/oos_metrics.json") as f:
    metrics = json.load(f)

# Baselines already computed
with open("docs/audits/phase33/baselines.json") as f:
    baselines = json.load(f)

# Trade-level data for profit factor
trades_df = pd.read_csv("docs/audits/phase33/oos_trades.csv")
```

### Computing Profit Factor from Trade CSV
```python
# oos_trades.csv has pnl_pct column from Phase 31 ab_report
wins = trades_df.loc[trades_df["pnl_pct"] > 0, "pnl_pct"].sum()
losses = abs(trades_df.loc[trades_df["pnl_pct"] < 0, "pnl_pct"].sum())
profit_factor = wins / losses if losses > 0 else float("inf")
```

### VN30 Buy-and-Hold from Data File
```python
# data/vn30_price.csv or Postgres index_eod
vn30 = pd.read_csv("data/vn30_price.csv")
vn30["tradingdate"] = pd.to_datetime(vn30["tradingdate"])
mask = (vn30["tradingdate"] >= "2019-01-01") & (vn30["tradingdate"] <= "2025-12-31")
vn30_period = vn30[mask].sort_values("tradingdate")
start_price = vn30_period.iloc[0]["closeindex"]
end_price = vn30_period.iloc[-1]["closeindex"]
years = (vn30_period.iloc[-1]["tradingdate"] - vn30_period.iloc[0]["tradingdate"]).days / 365.25
vn30_cagr = (end_price / start_price) ** (1 / years) - 1
```

### Retrospective Entry Format
```markdown
## Milestone: v7.0 -- CANSLIM + MDM on VN100

**Shipped:** 2026-04-10
**Phases:** X | **Plans:** Y | **Timeline:** Z days

### What Was Built
- [summary of v7.0 deliverables]

### What Worked
- [process/technical wins]

### What Was Inefficient
- [lessons from failures]

### Key Lessons
1. [lesson]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-model dashboard (MDM V2/Hybrid) | Multi-strategy dashboard (MDM + CANSLIM) | Phase 34 | Dashboard now covers portfolio strategy |
| Manual metric computation | Pipeline-generated metrics JSON | Phase 32 | Reproducible, auditable |
| No CPI adjustment | Real CAGR alongside nominal | Phase 34 | More honest performance comparison |

## Open Questions

1. **VN30 B&H data availability**
   - What we know: `data/vn30_price.csv` exists; also available via Postgres `index_eod`
   - What's unclear: Whether the CSV covers 2019-2025 fully, or if Postgres query is needed
   - Recommendation: Try CSV first, fall back to Postgres

2. **SJC Gold Price Data**
   - What we know: SJC gold is Vietnam-specific (VND per tael)
   - What's unclear: No automated data source in project
   - Recommendation: Hardcode approximate values: ~36.5M VND/tael (Jan 2019) to ~92M VND/tael (Dec 2025), source: SJC.com.vn historical. CAGR ~14-15%.

3. **12M Deposit Rate**
   - What we know: Vietnam SBV sets base rates; commercial banks vary
   - What's unclear: Exact annual 12M deposit rates 2019-2025
   - Recommendation: Hardcode approximate values: 2019: 6.5%, 2020: 5.0%, 2021: 5.0%, 2022: 6.0%, 2023: 5.5%, 2024: 4.5%, 2025: 4.5%. Compute compound return.

4. **Dashboard update scope**
   - What we know: Current dashboard shows MDM-on-VN30 models. Phase 34 has `UI hint: yes`.
   - What's unclear: Whether to add CANSLIM results to existing dashboard or create new dashboard
   - Recommendation: Add a CANSLIM tab/section to existing dashboard, or generate standalone HTML report in `docs/audits/phase34/`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/phase34/ -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BT-05 | Performance report with all required metrics | unit | `uv run pytest tests/phase34/test_report.py::test_metrics_complete -x` | Wave 0 |
| BT-06 | Benchmark table has all 5 comparisons | unit | `uv run pytest tests/phase34/test_report.py::test_benchmarks -x` | Wave 0 |
| BT-07 | Real CAGR computed correctly | unit | `uv run pytest tests/phase34/test_report.py::test_real_cagr -x` | Wave 0 |
| DOC-01 | rules_canslim_mdm.md has locked params | smoke | `uv run pytest tests/phase34/test_docs.py::test_rules_doc_current -x` | Wave 0 |
| DOC-02 | Data dictionary exists and covers connectors | smoke | `uv run pytest tests/phase34/test_docs.py::test_data_dict_exists -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/phase34/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/phase34/__init__.py` -- package init
- [ ] `tests/phase34/test_report.py` -- covers BT-05, BT-06, BT-07
- [ ] `tests/phase34/test_docs.py` -- covers DOC-01, DOC-02

## Sources

### Primary (HIGH confidence)
- Project codebase: `analysis/_vn100_pipeline.py` lines 630-710 -- existing metrics computation
- Project codebase: `docs/audits/phase33/oos_metrics.json` -- OOS performance data
- Project codebase: `docs/audits/phase33/baselines.json` -- existing benchmark data
- Project codebase: `docs/rules_canslim_mdm.md` -- current doc state (Phase 31, needs update)
- Project codebase: `docs/audits/phase33/verdict.md` -- locked config and OOS results

### Secondary (MEDIUM confidence)
- Vietnam CPI data: GSO.gov.vn annual reports (approximate values used)
- SJC gold prices: SJC.com.vn historical (approximate start/end values)
- Vietnam deposit rates: SBV published base rates (approximate commercial rates)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing libraries
- Architecture: HIGH -- extends existing pipeline pattern, reads existing outputs
- Pitfalls: HIGH -- based on direct inspection of existing code and data files

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable -- reporting phase, no fast-moving dependencies)
