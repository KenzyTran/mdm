# Phase 4: MDM v2 Engine - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a parameterized MDM v2 engine with Cash as an intermediate state between Buy and Sell, a hypothesis testing framework for systematic rule modification, and a parameter sweep that maximizes signal match rate against published post-2019 signals. Does NOT perform held-out validation (Phase 5) or adapt for VN30 (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Cash state behavior
- **D-01:** Cash triggers from Buy (HOLDING) via combined conditions: EITHER distribution day count hitting a configurable threshold OR price-action heuristics (e.g., close below MA10, failed rally). Both conditions are parameterizable for the sweep.
- **D-02:** Cash exits: FTD or MA50 breakout triggers Cash->Buy (reuses existing signal types). MA10/MA50 breakdown condition triggers Cash->Sell. Consistent with classic signal detection patterns.
- **D-03:** SHORT state is removed from v2. Sell signals transition to Cash (go flat), not to a short position. Simplifies the state machine to three states: Buy (HOLDING), Cash, Sell (triggers exit to Cash).
- **D-04:** Cash is scored as a distinct third signal type in match rate calculations. Cash is NOT a partial Sell. The signal comparator already supports Buy/Sell/Cash per Phase 3 D-01.

### v2 engine architecture
- **D-05:** Fork MDM classic into a new `strategies/mdm_v2/` package. Classic code stays untouched as reference. Follows Phase 2 pattern of independent strategy packages under `strategies/`.
- **D-06:** New `MDMV2Config` dataclass in `strategies/mdm_v2/config.py` with v2-specific parameters (Cash trigger thresholds, no SHORT-related params). Can reference classic defaults as starting point but owns its own schema.
- **D-07:** Hypothesis testing and parameter sweep code lives in `analysis/hypothesis/` directory. Follows existing pattern of `analysis/` for post-backtest research tools.

### Hypothesis testing framework
- **D-08:** Hypotheses are defined as named `MDMV2Config` variations with different parameter values. No code changes per hypothesis — purely config-driven. E.g., `aggressive_cash`: dd_threshold=3, `conservative_cash`: dd_threshold=5.
- **D-09:** Results reported as CSV (columns: hypothesis_name, match_rate, per_type_rates, param_values) plus text summary with top-N ranking. Consistent with Phase 3 output patterns.
- **D-10:** Framework supports parameter variations only for Phase 4. Structural changes (new signal types, different state transitions) are tested manually by modifying v2 engine code. Keep the framework simple.

### Parameter sweep design
- **D-11:** Grid search over defined parameter space. Exhaustive, reproducible, follows existing `optimize_mdm.py` pattern. Suitable for ~5-8 parameters with 3-5 values each.
- **D-12:** Training period: 2019-2022 published signals only (post-2019 change). Held-out 2023-2026 reserved for Phase 5 validation. Clean separation since we're targeting post-2019 behavior specifically.
- **D-13:** Sweep results ranked by overall signal match rate only. Per-type breakdown (Buy/Sell/Cash rates) shown in output but not used for ranking. Simple and directly aligned with core value.

### Claude's Discretion
- Exact parameter ranges and grid values for the sweep
- Internal state machine implementation details for Cash transitions
- Which classic engine modules to copy vs rewrite for v2
- CSV output formatting and text summary structure
- Hypothesis naming conventions and organization

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### MDM classic strategy (fork source)
- `strategies/mdm_classic/mdm_engine.py` -- MDM classic engine with daily processing loop, state machine orchestration (~350 lines)
- `strategies/mdm_classic/config.py` -- MDMConfig dataclass with existing parameter definitions and validation
- `strategies/mdm_classic/position_manager.py` -- State machine (CASH/HOLDING/WAITING_SELL/SHORT), Position dataclass, state transition logic
- `strategies/mdm_classic/ftd_signal.py` -- FTD detection logic, MA50 breakout, 52-week breakout signals
- `strategies/mdm_classic/distribution_day.py` -- Distribution day counting with windowed approach
- `strategies/mdm_classic/rally_attempt.py` -- Correction and rally day tracking
- `strategies/mdm_classic/stop_loss.py` -- Stop loss validation rules
- `strategies/mdm_classic/indicators.py` -- Technical indicator calculations (MA10, MA50, P_loc, volume ratios)

### Signal comparison infrastructure (Phase 3 outputs)
- `core/signal_comparator.py` -- Match rate scoring, divergence classification, signal alignment. Reuse directly for hypothesis testing (Phase 3 D-04).
- `core/signal_loader.py` -- Published signal fixture loader
- `core/data_loader.py` -- Unified DataLoader with NASDAQ normalization

### Published signal data
- `data/signals/nasdaq_signals.csv` -- Published NASDAQ signals 2019-2026 (primary comparison target)

### Existing parameter optimization (reference pattern)
- `scripts/optimize_mdm.py` -- Grid search pattern for parameter optimization. Reference for sweep implementation.

### Requirements
- `.planning/REQUIREMENTS.md` -- MDM-01 through MDM-04 define acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/signal_comparator.py`: compare_signals() returns match_rate and per_type breakdown -- direct scoring function for hypothesis testing
- `core/signal_comparator.py`: extract_model_signals() converts engine state column to Buy/Sell/Cash transitions -- works with v2 engine output
- `core/data_loader.py`: Unified DataLoader with market='nasdaq' -- loads normalized NASDAQ data for v2 engine
- `scripts/optimize_mdm.py`: Grid search pattern with nested loops and result collection -- template for parameter sweep
- `strategies/mdm_classic/config.py`: MDMConfig dataclass pattern with __post_init__ validation -- template for MDMV2Config

### Established Patterns
- Strategy packages under `strategies/` with `__init__.py`, own config, own engine (Phase 2 D-08)
- DataFrame-centric workflow: engine.run(df) returns DataFrame with signals and states
- CSV I/O for results: load from CSV, process in pandas, export results as CSV
- Analysis scripts in `analysis/` that import from core/ and strategies/

### Integration Points
- v2 engine must produce results DataFrame with 'state' column compatible with `extract_model_signals()` (maps state to Buy/Sell/Cash)
- Hypothesis testing imports `compare_signals()` from `core/signal_comparator.py` for match rate scoring
- Parameter sweep loads NASDAQ data via `core/data_loader.py` and published signals via `core/signal_loader.py`
- Sweep results CSV goes to `output/` directory (gitignored, per Phase 3 convention)

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

*Phase: 04-mdm-v2-engine*
*Context gathered: 2026-03-28*
