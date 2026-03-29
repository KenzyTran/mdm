# Phase 11: Foundation & Two-Phase Commit - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `strategies/mdm_hybrid/` package skeleton with HybridConfig and refactor the v2 state machine to use a two-phase commit pattern — indicator vetos cannot corrupt DD counter, rally tracker, position manager, or FTD detector internals. This phase does NOT implement indicator filters (Phase 12) or wire the full pipeline (Phase 13).

</domain>

<decisions>
## Implementation Decisions

### Package architecture
- **D-01:** Fork entire `strategies/mdm_v2/` into `strategies/mdm_hybrid/`. Full copy, independent package. No imports back to v2. Follows the same fork pattern used in Phase 4 (classic → v2).
- **D-02:** Engine file named `mdm_hybrid_engine.py`, class `HybridEngine`. Consistent with `mdm_v2_engine.py` naming pattern.

### Two-phase commit mechanism
- **D-03:** Snapshot/restore pattern using `copy.deepcopy()`. Before processing each day, snapshot all 4 components. If filter vetos the proposal, restore snapshot. If confirm (or no filter active), keep mutated state.
- **D-04:** All 4 mutable components protected by two-phase commit: DD counter (reset on FTD), position manager (enter_buy/exit_to_cash/enter_sell), rally tracker (full_reset after FTD), FTD detector (internal state).
- **D-05:** `two_phase_enabled` defaults to `True` in HybridConfig. Hybrid engine always uses snapshot/restore. Must be explicitly disabled for bypass.

### HybridConfig design
- **D-06:** Composition pattern — HybridConfig contains a `v2_config: MDMV2Config` field plus hybrid-specific flags. Clear separation between v2 state machine params and hybrid control flags.
- **D-07:** Phase 11 adds only `two_phase_enabled: bool = True` and `filter_enabled: bool = False` as hybrid-specific flags. Phase 12 will add indicator filter configuration.

### Regression testing
- **D-08:** Integration test compares hybrid (no filter) vs v2 on full NASDAQ data (1974-2026). Bit-for-bit match on 'state' and 'action' columns using `assert_series_equal`.
- **D-09:** Signal sequence comparison — run both engines on identical data, verify identical state transitions every day. This is the primary regression baseline for Phase 11.

### Claude's Discretion
- Snapshot helper function location (inline in engine vs separate module)
- Exact deepcopy implementation details and performance optimization if needed
- Which v2 modules to copy as-is vs which need modification for two-phase commit integration
- Test file organization and pytest fixtures
- How to structure the proposal object that will later be passed to indicator filter (Phase 12)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### V2 engine (fork source)
- `strategies/mdm_v2/mdm_v2_engine.py` — V2 engine daily processing loop with mutation points at lines 147 (DD reset on FTD), 161 (DD reset on MA50 breakout), 173 (DD reset on 52w breakout), 221 (rally tracker reset)
- `strategies/mdm_v2/position_manager.py` — V2PositionManager with 3-state machine (BUY/CASH/SELL), V2Position dataclass, immediate state mutation in enter_buy/exit_to_cash/enter_sell
- `strategies/mdm_v2/config.py` — MDMV2Config dataclass with v2-specific parameters and MDMConfig compatibility alias
- `strategies/mdm_v2/distribution_day.py` — DistributionDayCounter with windowed DD counting and reset()
- `strategies/mdm_v2/rally_attempt.py` — RallyAttemptTracker with correction tracking and full_reset()
- `strategies/mdm_v2/ftd_signal.py` — FTDSignalDetector with FTD, MA50 breakout, 52-week breakout detection
- `strategies/mdm_v2/stop_loss.py` — StopLossChecker
- `strategies/mdm_v2/indicators.py` — Indicators class with static methods for MA, price location, volume ratios

### Core infrastructure
- `core/data_loader.py` — DataLoader for NASDAQ OHLCV with /1000 normalization
- `core/signal_comparator.py` — Signal comparison for match rate scoring (Phase 14 will use)
- `core/indicators.py` — Multi-indicator engine (EMA, MACD, MA200) — Phase 12 will connect this

### Data
- `data/signals/nasdaq_signals_full.csv` — Full 962-signal ground truth for validation
- NASDAQ OHLCV data (1974-2026) via DataLoader

### Requirements
- `.planning/REQUIREMENTS.md` — HYB-01 (state machine reuse), HYB-06 (two-phase commit)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `strategies/mdm_v2/` entire package: Fork source. All modules are self-contained with clean interfaces.
- `core/data_loader.py` DataLoader: Loads NASDAQ data for integration tests.
- Phase 4 fork pattern: `strategies/mdm_classic/` → `strategies/mdm_v2/` established the fork workflow.

### Established Patterns
- Strategy packages under `strategies/` with `__init__.py`, own config, own engine
- DataFrame-centric workflow: engine.run(df) returns DataFrame with signals and states
- Dataclass configs with `__post_init__` validation
- `MDMConfig = MDMV2Config` alias pattern in v2 config for backward compatibility with copied modules

### Integration Points
- Hybrid engine must produce results DataFrame with same columns as v2 ('state', 'action', etc.) for downstream compatibility
- `core/signal_comparator.py` extract_model_signals() expects 'state' column with BUY/CASH/SELL values
- Phase 12 will add IndicatorFilter that reads from `core/indicators.py` and integrates with the two-phase commit propose/confirm flow
- Phase 13 will wire the full Propose-Filter-Decide pipeline using the snapshot/restore mechanism built here

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-foundation-two-phase-commit*
*Context gathered: 2026-03-29*
