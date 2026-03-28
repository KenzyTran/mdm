# Phase 5: Validation & Performance - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate MDM v2 rules on held-out 2023-2026 data, produce full performance analysis (equity curve, max drawdown, Sharpe ratio, win rate), and compare MDM v2 against buy-and-hold and MDM classic baselines. Does NOT modify v2 rules or adapt for VN30 (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Validation criteria
- **D-01:** Held-out validation uses 2023-2026 published signals. Training was 2019-2022 (Phase 4 D-12). Match rate on held-out must not drop more than 10% relative to training match rate (e.g., if training is 60%, held-out must be >=54%).
- **D-02:** Report both overall match rate and per-signal-type breakdown (Buy/Sell/Cash separately) for both training and held-out periods. Reveals if one signal type degrades more than others.
- **D-03:** Best config loaded automatically from Phase 4's parameter sweep results CSV (top-ranked row). No manual config selection required — fully automated pipeline from sweep to validation.

### Performance metrics
- **D-04:** New v2-specific PerformanceAnalyzer (not extending classic). Includes all PERF-01 metrics: equity curve, max drawdown, Sharpe ratio, win rate, total return, annualized return. Classic analyzer stays untouched.
- **D-05:** Hypothetical returns model — assume 100% allocation on Buy signal, 0% on Cash/Sell. Simple equity curve from signal timing. This is about validating signal quality, not portfolio management.
- **D-06:** Sharpe ratio uses 0% risk-free rate. Standard for backtesting comparisons, no external data dependency.

### Report & visualization
- **D-07:** Analysis script (`analysis/validate_v2.py`) generates CSV results + text summary + PNG charts. Jupyter notebook for interactive exploration. Follows Phase 3 pattern (D-10).
- **D-08:** Multi-panel dashboard chart: top panel equity curve (v2 vs buy-and-hold vs classic), middle panel drawdown, bottom panel signal markers on NASDAQ price. One high-res PNG output.
- **D-09:** Script lives at `analysis/validate_v2.py` following established pattern (alongside `analyze_drawdown.py`, `diagnose_vn30.py`).

### Buy-and-hold comparison
- **D-10:** Three-row comparison table: 2019-2022 (train), 2023-2026 (held-out), 2019-2026 (full). Shows performance in both periods separately, aligned with validation split.
- **D-11:** Three-way comparison: MDM v2 vs buy-and-hold NASDAQ vs MDM classic. Demonstrates both absolute performance and improvement from reverse-engineering v2 rules.

### Claude's Discretion
- Exact matplotlib styling (colors, fonts, figure dimensions)
- Notebook cell structure and organization
- CSV column ordering and text summary formatting
- Internal data structures for performance results
- How to handle edge cases (insufficient held-out signals, missing dates)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### MDM v2 engine (Phase 4 outputs)
- `strategies/mdm_v2/mdm_v2_engine.py` -- MDM v2 engine with 3-state machine (BUY/CASH/SELL)
- `strategies/mdm_v2/config.py` -- MDMV2Config dataclass with parameterized thresholds
- `analysis/hypothesis/parameter_sweep.py` -- Sweep results CSV with top-ranked configs
- `analysis/hypothesis/hypothesis_runner.py` -- Hypothesis runner that scores configs against published signals

### Signal comparison infrastructure (Phase 3 outputs)
- `core/signal_comparator.py` -- Match rate scoring, divergence classification, signal alignment
- `core/signal_loader.py` -- Published signal fixture loader
- `core/data_loader.py` -- Unified DataLoader with NASDAQ normalization (market='nasdaq')

### Published signal data
- `data/signals/nasdaq_signals.csv` -- Published NASDAQ signals 2019-2026

### Existing performance analyzer (reference)
- `strategies/mdm_classic/performance.py` -- Classic PerformanceAnalyzer with return, drawdown, win rate (no Sharpe). Reference for v2 analyzer.
- `strategies/mdm_classic/mdm_engine.py` -- Classic engine for three-way comparison baseline

### Existing analysis patterns
- `analysis/analyze_drawdown.py` -- Reference for matplotlib multi-panel chart layout
- `analysis/diagnose_vn30.py` -- Reference for analysis script structure

### Requirements
- `.planning/REQUIREMENTS.md` -- PERF-01 through PERF-03 define acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/signal_comparator.py`: compare_signals() returns match_rate and per_type breakdown -- direct scoring for validation
- `core/signal_comparator.py`: extract_model_signals() converts engine state column to Buy/Sell/Cash transitions
- `core/data_loader.py`: Unified DataLoader with market='nasdaq' loads normalized NASDAQ data
- `core/signal_loader.py`: Load published signals into validated DataFrame
- `analysis/hypothesis/parameter_sweep.py`: Sweep results CSV -- source for best config auto-loading
- `analysis/hypothesis/hypothesis_runner.py`: run_hypothesis() runs a config and scores it -- reusable for validation run
- `strategies/mdm_classic/performance.py`: PerformanceAnalyzer pattern -- reference for building v2 analyzer
- `analysis/analyze_drawdown.py`: matplotlib charting pattern with multi-panel layout -- template for dashboard

### Established Patterns
- DataFrame-centric workflow: engine.run(df) returns DataFrame with signals and states
- CSV I/O: load from CSV, process in pandas, export results as CSV
- Analysis scripts in `analysis/` that import from core/ and strategies/
- Output files go to `output/` directory (gitignored, per Phase 3 convention)
- Jupyter notebooks for interactive exploration alongside scripts

### Integration Points
- Validation script imports `run_hypothesis()` from `analysis/hypothesis/` for running v2 with a config
- Validation script imports `compare_signals()` from `core/signal_comparator.py` for match rate on held-out set
- Validation script imports MDMEngine from `strategies/mdm_classic/` for classic baseline comparison
- New v2 PerformanceAnalyzer takes engine results DataFrame and computes metrics
- Output PNG/CSV/text goes to `output/` directory

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 05-validation-performance*
*Context gathered: 2026-03-28*
