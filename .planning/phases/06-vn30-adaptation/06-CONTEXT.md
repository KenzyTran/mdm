# Phase 6: VN30 Adaptation - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Recalibrate MDM v2 for Vietnamese market microstructure (7% price limits, T+2.5 settlement, derivative expiry) and produce a full VN30 backtest with performance reporting. Does NOT modify the core MDM v2 engine logic or add new signal types.

</domain>

<decisions>
## Implementation Decisions

### Price limit day handling
- **D-01:** Flag 7% limit-up/limit-down days with a boolean column (`is_limit_day`) but do NOT filter or suppress signals on those days. Let the parameter sweep decide if they matter.
- **D-02:** FTD signals on limit-up days are valid and not suppressed -- the 7% cap doesn't invalidate buying pressure.
- **D-03:** Limit day detection logic lives in a new VN30 microstructure module at `strategies/mdm_v2/vn30_filters.py`, not in the shared data loader.

### Settlement & derivative expiry
- **D-04:** T+2.5 settlement delay is ignored in the backtest. MDM is a daily-bar signal model -- settlement is a real-world execution constraint, not a signal quality factor.
- **D-05:** Distribution day counting is suppressed on derivative expiry days. Elevated volume on expiry is structural, not distribution.
- **D-06:** Derivative expiry dates (3rd Thursday of each month) are computed algorithmically in `vn30_filters.py` -- no external CSV maintenance required.

### Parameter recalibration
- **D-07:** Fresh grid sweep over VN30 data using Phase 4's parameter_sweep.py framework. NASDAQ params may not transfer -- VN30 has different volatility/volume characteristics.
- **D-08:** Sweep optimizes for Sharpe ratio (risk-adjusted return), not signal match rate. No published VN30 signals exist as a benchmark.
- **D-09:** Adapt existing `analysis/hypothesis/parameter_sweep.py` to accept a scoring function (match_rate OR Sharpe). New VN30 sweep script at `analysis/sweep_vn30.py`.

### Backtest scope
- **D-10:** Use full available VN30 data range (2014-2026 from `data/vn30.csv`). Maximizes training data.
- **D-11:** Train/test split at pre/post-2020. Train sweep on pre-2020 data, validate on 2020-2026. COVID regime shift tests parameter robustness.
- **D-12:** Compare against VN30 buy-and-hold baseline only. VSA strategy comparison is apples-to-oranges due to multi-stock approach.

### Claude's Discretion
- Exact parameter grid ranges and step sizes for VN30 sweep
- VN30 backtest report format and chart layout (follow Phase 5 patterns)
- Internal implementation of vn30_filters.py helper functions
- How to handle edge cases in expiry date computation (holidays, etc.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### MDM v2 engine (Phase 4 outputs)
- `strategies/mdm_v2/mdm_v2_engine.py` -- MDM v2 engine with 3-state machine (BUY/CASH/SELL)
- `strategies/mdm_v2/config.py` -- MDMV2Config dataclass with parameterized thresholds
- `strategies/mdm_v2/performance.py` -- V2PerformanceAnalyzer (equity curve, drawdown, Sharpe, win rate)

### Parameter sweep framework (Phase 4 outputs)
- `analysis/hypothesis/parameter_sweep.py` -- Grid sweep framework to be adapted for Sharpe-based scoring
- `analysis/hypothesis/hypothesis_runner.py` -- Hypothesis runner that scores configs

### Validation pipeline (Phase 5 outputs)
- `analysis/validate_v2.py` -- Validation script pattern (CSV + text + PNG output)
- `notebooks/v2_validation.ipynb` -- Jupyter validation notebook pattern

### Data infrastructure
- `core/data_loader.py` -- Unified DataLoader with market='vn30' support (native scale, no normalization)
- `data/vn30.csv` -- VN30 OHLCV data (2014-2026)

### VN30 analysis (existing)
- `analysis/diagnose_vn30.py` -- VN30 threshold analysis (FTD/DD frequency at various thresholds)

### Requirements
- `.planning/REQUIREMENTS.md` -- VN30-01, VN30-02, VN30-03 define acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/data_loader.py`: DataLoader(market='vn30') loads VN30 data with correct column mapping and native scale
- `strategies/mdm_v2/mdm_v2_engine.py`: V2 engine runs on any OHLCV DataFrame -- market-agnostic
- `strategies/mdm_v2/performance.py`: V2PerformanceAnalyzer computes equity curve, Sharpe, drawdown, win rate
- `analysis/hypothesis/parameter_sweep.py`: Grid search framework -- needs scoring function abstraction for Sharpe
- `analysis/hypothesis/hypothesis_runner.py`: Runs a config and scores it -- reusable with new objective
- `analysis/diagnose_vn30.py`: VN30 threshold analysis -- informs parameter grid range selection

### Established Patterns
- Strategy packages under `strategies/` with own config, engine, performance modules
- DataFrame-centric workflow: engine.run(df) returns DataFrame with signals and states
- Analysis scripts in `analysis/` that import from core/ and strategies/
- Output files go to `output/` directory (gitignored)
- Jupyter notebooks for interactive exploration alongside scripts

### Integration Points
- VN30 filters module adds columns to DataFrame before passing to v2 engine
- Adapted parameter_sweep.py accepts scoring_fn parameter (Sharpe or match_rate)
- VN30 sweep script loads data via core/data_loader.py, applies vn30_filters, runs sweep
- VN30 backtest report follows Phase 5 validate_v2.py output pattern (CSV + PNG + text)

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

*Phase: 06-vn30-adaptation*
*Context gathered: 2026-03-28*
