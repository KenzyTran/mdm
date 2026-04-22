# Phase 44: Macro Filter Module - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a feature-gated `MacroFilter` to `HybridEngine` that consumes the two canonical inputs frozen in Phase 43 (`data/vn_liquidity_proxy.csv`, `data/sbv_policy_events.csv`) and overlays three macro signals on the v6.0 state-machine decisions:

1. **DXY 20d z-score** (US Dollar Index) — liquidity proxy, negative correlation with VN30 forward returns
2. **EEM 20d z-score** (iShares EM ETF) — EM flow proxy, positive correlation with VN30 forward returns
3. **SBV regime classifier** — labels each trading day `easing | neutral | tightening` based on most recent SBV rate action with 90-day decay

Deliverables:

1. `strategies/mdm_hybrid/macro_filter.py` — NEW file with `MacroFilter` class, `MacroConfig`-style dataclass, precompute helper
2. Config fields on `MDMV2Config` gating filter behavior (feature-gated via `macro_filter_enabled: bool = False`)
3. Hook into `HybridEngine.run()` loop AFTER `IndicatorFilter.evaluate()` and BEFORE action apply
4. Byte-exact v6.0 parity regression test (signal-log equality vs reconciled-HEAD baseline from Phase 42) when `macro_filter_enabled=False`
5. Unit tests: DXY z-score on a known date, EEM z-score on a known date, SBV regime transitions across a known event sequence

**Explicitly out of scope:**
- Grid search of thresholds / windows (Phase 45 WF-01)
- A/B comparison across 5 scenarios (Phase 46 VAL-01)
- OOS validation / HARD gate (Phase 46 VAL-02)
- Walk-forward median degradation (Phase 45 WF-02)
- Regenerating the two canonical CSVs (Phase 43 owns them)
- Any change to fail-safe logic (REQUIREMENTS.md Out of Scope, Phase 42 D-11)
- Any change to `strategies/canslim/`, `strategies/portfolio/`, `vn30_vsa/`
- Any change to baseline reconciliation artifacts (Phase 42 owns `output/v10_reconciled_baseline.json`)

</domain>

<decisions>
## Implementation Decisions

### Filter policy mechanics

- **D-01 (DXY easing suppresses SELL):** When DXY z-score is in easing regime (`dxy_z < dxy_easing_z_threshold`, default `-1.0`) AND the state machine proposes SELL, MacroFilter returns **VETO** — block the SELL transition, keep current state (HOLD/BUY unchanged). Parallels `IndicatorFilter.Verdict.VETO` pattern.

- **D-02 (DXY tightening amplifies SELL):** When DXY z-score is in tightening regime (`dxy_z > dxy_tightening_z_threshold`, default `+1.0`) AND no SELL proposal is currently active, MacroFilter **lowers the effective `dd_cash_threshold`** from `5` down to `dxy_tightening_dd_threshold` (default `3`) so SELL can fire earlier on weak price action. Implementation: MacroFilter exposes an "effective DD threshold for today" value that `V2PositionManager` consumes instead of the static config value. Policy tweaks config-at-use-site, not in-place mutation of config object.

- **D-03 (SBV tightening shrinks stop-loss):** When SBV regime is `tightening` AND current position is BUY/HOLD, MacroFilter **reduces `stop_loss_max_multiplier`** from its default (`2.5` in VN30_PRESET) down to `sbv_tightening_stop_loss_max_multiplier` (default `1.5`) — existing positions bail earlier on drawdown. Policy is PASSIVE — does NOT force CASH exit. This is a **deliberate deviation from the original MACRO-05 spec** which read "forces half-position or full CASH". See D-05.

- **D-04 (Conflict resolution: most-restrictive wins):** When DXY and SBV signals disagree (e.g., DXY easing but SBV tightening), MacroFilter acts cautionary. Semantics:
  - If EITHER DXY tightening OR SBV tightening is active → apply tightening policies (D-02 for DD lowering, D-03 for stop-loss shrinking)
  - VETO of SELL (D-01) requires BOTH DXY easing AND no tightening regime from SBV active (most-restrictive principle: a single cautionary signal blocks the bullish policy)
  - When BOTH DXY easing AND SBV easing → full easing policy (VETO SELL)
  - When neither is active (DXY neutral AND SBV neutral) → MacroFilter is pass-through
  - EEM is combined using the same rule (see D-13 below — EEM's policy is symmetric to DXY's)

- **D-05 (ROADMAP / REQUIREMENTS.md update — MACRO-05 rewrite):** As part of Phase 44 execution, update `.planning/ROADMAP.md` §Phase 44 success criterion 5 AND `.planning/REQUIREMENTS.md` MACRO-05 from:
  > "DXY easing suppresses SELL, DXY tightening amplifies SELL, SBV tightening regime forces half-position or full CASH; exact thresholds `dxy_z_threshold`, `sbv_tightening_position_frac` are exposed as config fields ready for the Phase 45 grid search"

  To:
  > "DXY easing VETOes SELL, DXY tightening lowers the effective DD threshold, SBV tightening shrinks `stop_loss_max_multiplier`; exact thresholds `dxy_easing_z_threshold`, `dxy_tightening_z_threshold`, `eem_easing_z_threshold`, `eem_tightening_z_threshold`, `dxy_tightening_dd_threshold`, `sbv_tightening_stop_loss_max_multiplier` are exposed as config fields ready for the Phase 45 grid search"

  This commit piggy-backs on the phase completion (not a separate phase). Rationale for deviation: engine binary model preserved, smaller blast radius, stop-loss is already a first-class config — fractional sizing would be a much larger refactor touching PositionManager, NAV calc, and every metric. Deferred-idea scalar sizing is noted below.

### Position sizing

- **D-06 (Binary engine preserved):** `HybridEngine` remains binary (`MarketState.CASH | BUY | SELL` + SHORT). No `Position.size` scalar, no half-position state. MacroFilter influences the state machine via threshold tweaks (D-02) and stop-loss tightening (D-03) rather than introducing a new position sizing concept.

### Module placement & integration point

- **D-07 (New file, not extension):** `MacroFilter` lives in a **new file** `strategies/mdm_hybrid/macro_filter.py`, parallel to `indicator_filter.py`. Not folded into `indicator_filter.py` — macro concerns (market-wide liquidity, monetary regime) are distinct from indicator concerns (local price action) and mixing them dilutes both.

- **D-08 (Hook AFTER IndicatorFilter):** In `HybridEngine.run()` per-step loop, the decision order is:
  1. `V2PositionManager.process_day(...)` → returns `(proposed_state, proposed_action)`
  2. `IndicatorFilter.evaluate(row, proposal, current_state)` → returns `Verdict.CONFIRM | VETO | OVERRIDE`
  3. **NEW:** `MacroFilter.apply(row, state_machine_decision, current_state)` → returns `MacroVerdict.PASS | VETO_SELL | LOWER_DD_THRESHOLD | TIGHTEN_STOP_LOSS` (or a combination struct)
  4. Engine applies final action (`exit_to_cash`, `cover_short`, `degrade_to_cash`, etc.)

  Rationale: MacroFilter is the outer policy layer — macro regime overrules local indicator consensus in conflict. Reverse ordering (MacroFilter before IndicatorFilter) would let the majority-vote indicator logic override a clear macro regime signal, which is semantically wrong.

- **D-09 (Hard short-circuit parity):** When `macro_filter_enabled=False`, `MacroFilter.apply()` returns `MacroVerdict.PASS` on its first line:
  ```python
  if not self.config.v2_config.macro_filter_enabled:
      return MacroVerdict.PASS
  ```
  AND the precompute step (D-10) is also skipped — no DXY_z / EEM_z / SBV_regime columns are added to the DataFrame when the flag is False. This guarantees zero NaN propagation, zero float rounding drift, and zero new columns in the signal log — pure byte-exact parity with reconciled-HEAD (Phase 42 D-12/D-14).

- **D-10 (Precompute enrichment before engine.run()):** DXY_z, EEM_z, and SBV_regime columns are computed **ONCE** before `HybridEngine.run()` is called. Helper signature:
  ```python
  def add_macro_columns(
      df: pd.DataFrame,
      liquidity_proxy_path: Path = LIQUIDITY_PROXY_PATH,
      sbv_events_path: Path = SBV_EVENTS_PATH,
      dxy_window_days: int = 20,
      eem_window_days: int = 20,
      sbv_decay_days: int = 90,
  ) -> pd.DataFrame:
      """Enrich VN30 DataFrame with DXY_z, EEM_z, SBV_regime columns.

      Uses pd.merge_asof(direction='backward') per Phase 43 D-08 merge contract.
      Z-score computed AFTER the merge (on VN30-indexed DataFrame) per
      docs/liquidity_proxy_spec.md Section 5.3 — rolling window respects VN30
      trading days, not US calendar days.
      SBV regime shifts event_date by +1 BusinessDay (Phase 43 D-08) before the
      merge, then applies 90-day decay to 'neutral'.
      """
  ```
  Called by `HybridEngine.__init__` or by the caller BEFORE engine instantiation. When `macro_filter_enabled=False`, helper is NOT called — DataFrame stays schema-clean.

### Config surface (Phase 45 grid search inputs)

- **D-11 (DXY thresholds — asymmetric, 2 fields):** `dxy_easing_z_threshold: float = -1.0` and `dxy_tightening_z_threshold: float = +1.0`. Separate fields allow Phase 45 walk-forward grid to search easing bands wider than tightening bands (DXY skewed right in VN context per quick-task 260421-lb4 evidence).

- **D-12 (EEM thresholds — separate from DXY):** `eem_easing_z_threshold: float = +1.0` and `eem_tightening_z_threshold: float = -1.0`. Signs FLIPPED relative to DXY fields because EEM has POSITIVE correlation with VN30 forward returns (+0.19 vs DXY -0.19 per Phase 43 D-08 evidence). EEM easing = EEM z > +threshold (EM flow positive); EEM tightening = EEM z < -threshold (EM flow negative).

- **D-13 (EEM policy role — symmetric to DXY):** EEM triggers the SAME policy verbs as DXY: EEM easing VETOes SELL (reinforces DXY easing under D-04 most-restrictive rule), EEM tightening lowers DD threshold (reinforces DXY tightening under D-04). Both DXY and EEM policy execution flows through the SAME MacroFilter code path, differing only in which field's threshold is checked and which direction of z is "easing" for that series. Implementation reuses code.

- **D-14 (Window lengths — all exposed):** `dxy_window_days: int = 20`, `eem_window_days: int = 20`, `sbv_decay_days: int = 90` — all three are MDMV2Config fields. Phase 45 grid-searches these alongside the z-score thresholds and DD / stop-loss multipliers. Default values come from quick-task 260421-lb4 evidence (20d DXY z-score corr = -0.19, 20d EEM z-score corr = +0.19, 90-day decay matches SBV rate-action transmission lag).

- **D-15 (Full MDMV2Config field list — mandatory for Phase 44):**
  ```python
  # Macro Filter (Phase 44, MACRO-01..05)
  macro_filter_enabled: bool = False              # Feature gate: off = reconciled-HEAD parity
  dxy_easing_z_threshold: float = -1.0            # DXY z < this → easing regime → VETO SELL
  dxy_tightening_z_threshold: float = +1.0        # DXY z > this → tightening → lower DD threshold
  eem_easing_z_threshold: float = +1.0            # EEM z > this → easing (sign flipped vs DXY)
  eem_tightening_z_threshold: float = -1.0        # EEM z < this → tightening
  dxy_window_days: int = 20                       # Rolling window for DXY z-score (computed on merged DF)
  eem_window_days: int = 20                       # Rolling window for EEM z-score
  sbv_decay_days: int = 90                        # Days after event_date before regime → neutral
  dxy_tightening_dd_threshold: int = 3            # Effective dd_cash_threshold when DXY tightening active
  sbv_tightening_stop_loss_max_multiplier: float = 1.5  # stop_loss_max_multiplier when SBV tightening active
  ```
  All 10 fields default-gated to the False feature flag — when disabled, none of these values affect behavior.

- **D-16 (CSV paths hardcoded, not config):** Path constants in `macro_filter.py`:
  ```python
  LIQUIDITY_PROXY_PATH = Path('data/vn_liquidity_proxy.csv')
  SBV_EVENTS_PATH = Path('data/sbv_policy_events.csv')
  ```
  Phase 43 froze these paths; no need to expose as MDMV2Config fields. Test fixtures can inject alternative paths via the `add_macro_columns` function arguments (the constants are only the defaults).

### Claude's Discretion

- Exact enum design for `MacroVerdict` (single enum vs. combination struct) — planner decides, must support combining VETO_SELL + LOWER_DD + TIGHTEN_STOP_LOSS since D-04 allows multiple tightening policies simultaneously
- `add_macro_columns` implementation details (which column names land on the DataFrame — suggestion: `dxy_z`, `eem_z`, `sbv_regime`, matching existing snake_case convention)
- Whether SBV merge produces a per-row `sbv_days_since_event` column for diagnosability (nice-to-have)
- Unit test data strategy — synthetic fixtures vs. full VN30 load (prefer synthetic mini-fixtures for unit tests; integration/parity test uses full VN30 data per Phase 42 D-18 precedent)
- Specific filenames for test files (follow `tests/test_*.py` conventions; suggested: `tests/test_macro_filter.py`, `tests/test_macro_filter_v6_parity.py`)
- Exact timing of the MACRO-05 REQUIREMENTS.md edit commit (can be bundled with the feature gate addition, or separate doc commit — planner decides per GSD atomic-commit convention)

### Folded Todos

None — no todos matched this phase at discussion time (gsd-tools todo match-phase was not invoked; standing backlog has no macro-filter-specific items per memory review).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements (current phase scope)
- [.planning/ROADMAP.md §Phase 44](.planning/ROADMAP.md) (lines 844-858) — Goal, 5 success criteria, MACRO-01..05 mapping. **Note**: MACRO-05 success criterion 5 MUST be updated per D-05 during Phase 44 execution.
- [.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md) §Macro Filter Module (MACRO-01..05) — **MACRO-05 needs rewrite per D-05**.
- [.planning/PROJECT.md](.planning/PROJECT.md) §Current Milestone v10.0 (lines 65-87) — milestone goal, HARD gate, evidence base.

### Phase 43 outputs (MUST READ — frozen upstream contracts)
- [docs/liquidity_proxy_spec.md](docs/liquidity_proxy_spec.md) — **LOAD-BEARING.** Merge contract (§5), publication-lag policy (§4), look-ahead traps ruled out (§6). Phase 44 MUST follow this spec or Phase 42 parity breaks.
- [data/vn_liquidity_proxy.csv](data/vn_liquidity_proxy.csv) — 6-column daily panel 2015-2025, 2867 rows (columns: `date, usdvnd_close, dxy_close, tnx_close, vnm_close, eem_close`). Only `dxy_close` and `eem_close` consumed by MacroFilter per D-10/D-13.
- [data/sbv_policy_events.csv](data/sbv_policy_events.csv) — 5-column event log, 12 rows, schema `date, rate_change_pct, new_refinance_rate_pct, direction, source`. `direction ∈ {easing, tightening}`; `neutral` DERIVED downstream via 90-day decay.
- [.planning/phases/43-canonical-liquidity-data-pipeline/43-CONTEXT.md](.planning/phases/43-canonical-liquidity-data-pipeline/43-CONTEXT.md) §D-08 / D-09 — publication-lag decisions + look-ahead traps that Phase 44 MUST honor.

### Phase 42 outputs (parity target)
- [output/v10_reconciled_baseline.json](output/v10_reconciled_baseline.json) — **Canonical baseline** Phase 44 VAL-04 parity regression asserts against. Schema v1 per Phase 42 D-15.
- [docs/audits/v10_baseline_drift.md](docs/audits/v10_baseline_drift.md) — reconciled baseline narrative + tuple (human-readable).
- [tests/test_baseline_determinism.py](tests/test_baseline_determinism.py) — pytest regression precedent (determinism test pattern Phase 44 parity test adapts).
- [.planning/phases/42-baseline-reconciliation/42-CONTEXT.md](.planning/phases/42-baseline-reconciliation/42-CONTEXT.md) §D-12/D-14/D-17/D-18 — reconciled baseline tuple, downstream consumer contract, determinism test patterns.

### Engine under modification
- [strategies/mdm_hybrid/mdm_hybrid_engine.py](strategies/mdm_hybrid/mdm_hybrid_engine.py) — HybridEngine main loop. Lines ~100-200 are the per-step decision cascade where D-08 hook inserts.
- [strategies/mdm_hybrid/config.py](strategies/mdm_hybrid/config.py) — MDMV2Config dataclass (lines 10-108), VN30_PRESET (line 141), HybridConfig (line 116). D-15 config fields append here.
- [strategies/mdm_hybrid/indicator_filter.py](strategies/mdm_hybrid/indicator_filter.py) — **Pattern precedent** for MacroFilter (class structure, Verdict enum, FilterConfig dataclass, NaN-safe evaluation per D-06/D-13 of Phase 12).
- [strategies/mdm_hybrid/position_manager.py](strategies/mdm_hybrid/position_manager.py) — `V2PositionManager.process_day()`. D-02 `dxy_tightening_dd_threshold` plumbing lands here (effective DD threshold consumption).
- [strategies/mdm_hybrid/stop_loss.py](strategies/mdm_hybrid/stop_loss.py) — stop-loss multiplier math. D-03 `sbv_tightening_stop_loss_max_multiplier` plumbing passes through.

### New files created by Phase 44
- `strategies/mdm_hybrid/macro_filter.py` — NEW. Contains `MacroFilter` class, `MacroVerdict` enum, `add_macro_columns()` helper, `LIQUIDITY_PROXY_PATH` / `SBV_EVENTS_PATH` path constants.
- `tests/test_macro_filter.py` — NEW. Unit tests per ROADMAP SC-1/2/3 (DXY z on known date, EEM z on known date, SBV regime transitions).
- `tests/test_macro_filter_v6_parity.py` — NEW. Integration test asserting byte-exact signal-log equality vs reconciled-HEAD baseline when `macro_filter_enabled=False` (MACRO-04 / VAL-04).

### Pytest precedent (regression pattern)
- [tests/test_baseline_determinism.py](tests/test_baseline_determinism.py) — `@pytest.mark.regression` marker, class-scoped fixtures, `df1.equals(df2)` signal-log byte-exact equality (Phase 42 D-17). Phase 44 parity test adapts this pattern.
- [tests/test_hybrid_engine.py](tests/test_hybrid_engine.py), [tests/test_mdm_regression.py](tests/test_mdm_regression.py) — existing hybrid-engine test structure to model imports after.

### Quick-task research (evidence base — DO NOT re-run)
- [docs/research/liquidity_proxy_correlation.md](docs/research/liquidity_proxy_correlation.md) — GO verdict evidence (DXY 20d z corr = -0.1909, EEM 20d z corr = +0.1911, SBV easing +31.84% CAGR vs tightening -23.92% CAGR). Phase 44 defaults (20d windows, +/-1.0 z thresholds, 90d decay) come from here.
- [.planning/quick/260421-lb4-build-vn30-liquidity-proxy-dataset-and-t/260421-lb4-SUMMARY.md](.planning/quick/260421-lb4-build-vn30-liquidity-proxy-dataset-and-t/260421-lb4-SUMMARY.md) — quick-task summary (source of row counts, tickers, SBV event cluster descriptions).

### Prior phase contexts (carry-forward decisions)
- [.planning/phases/11-foundation-two-phase-commit/11-CONTEXT.md](.planning/phases/11-foundation-two-phase-commit/11-CONTEXT.md) — HybridConfig composition pattern.
- [.planning/phases/12-indicator-filter-layer/](.planning/phases/12-indicator-filter-layer/) — IndicatorFilter pattern (D-05 evaluate signature, D-07 Verdict enum, D-11 majority_threshold, D-13 NaN-safe evaluation). Phase 44 MacroFilter follows this structure.
- [.planning/phases/38-atr-buffer-zone-module/38-CONTEXT.md](.planning/phases/38-atr-buffer-zone-module/38-CONTEXT.md) — Feature-gate pattern (`atr_buffer_enabled: bool = False` default-off, backward-compat invariant). Phase 44 `macro_filter_enabled` inherits this.
- [.planning/phases/39-refined-distribution-day-module/39-CONTEXT.md](.planning/phases/39-refined-distribution-day-module/39-CONTEXT.md) — Feature-gate + v6.0-parity-when-off invariant pattern.
- [.planning/phases/23-fail-safe-mechanism/](.planning/phases/23-fail-safe-mechanism/) — fail-safe canonical semantics (Phase 44 MUST NOT modify).

### Memory anchors
- v6.0 baseline VN30 2015-2026 target: CAGR 11.5%, MaxDD -28.2%, 124 SELL — memory: `project_best_model.md`. Phase 44 parity target is the RECONCILED-HEAD version of these numbers per Phase 42 D-14 (reads JSON, not hardcoded).
- Equity formula `state[i-1]` discipline — memory: `feedback_equity_formula.md`. Parity test MUST uphold this; MacroFilter MUST NOT introduce a `state[i]` reference anywhere.
- v10.0 HARD gate: MaxDD < -20% AND CAGR ≥ reconciled baseline — memory: `project_v9_whipsaw.md`. Phase 44 does NOT evaluate the gate (that's Phase 46); but MacroFilter's policy must aim at the gate so Phase 45 grid search has a usable search space.
- VN liquidity proxy research verdict: DXY/EEM z-score correlation ±0.19 with 20d fwd VN30; SBV easing +31.84% CAGR vs tightening -23.92% — memory: `project_liquidity_proxy.md`. These ARE the defaults in D-11/D-12/D-14.
- Best-model doc discipline — memory: `feedback_best_model_docs.md`. Updates to rules doc (`docs/rules_mdm_hybrid.md`) happen at Phase 47 DOC-01, NOT Phase 44.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- [strategies/mdm_hybrid/indicator_filter.py:IndicatorFilter](strategies/mdm_hybrid/indicator_filter.py) — class structure, Verdict enum, NaN-safe row-evaluation pattern. MacroFilter's `apply()` method mirrors `evaluate()` shape.
- `@dataclass FilterConfig` (same file, lines 42-79) — per-condition toggle pattern with `__post_init__` validation. MacroConfig (if separate dataclass — discretionary per D-07) follows same shape.
- [strategies/mdm_hybrid/config.py::dataclass MDMV2Config](strategies/mdm_hybrid/config.py) — append D-15 fields to the existing dataclass; `__post_init__` asserts field-range invariants when `macro_filter_enabled=True` (follows Phase 39 D-06 "gate validation per feature flag" precedent).
- `dataclasses.replace(VN30_PRESET, **overrides)` — preset-mutation pattern. Test fixtures for MacroFilter enabled/disabled will create preset variants this way.
- [tests/test_baseline_determinism.py::test_signal_log_byte_exact](tests/test_baseline_determinism.py) — `df1.equals(df2)` byte-exact equality for signal-log parity (VAL-04 pattern).
- [analysis/validate_v9.py::compute_metrics()](analysis/validate_v9.py) — canonical metrics function; Phase 44 unit tests that compare CAGR across feature-gate states reuse this.

### Established Patterns

- **Feature-gate default-off** — Phase 38/39/42 precedent. `macro_filter_enabled: bool = False` in MDMV2Config, VN30_PRESET, NASDAQ_PRESET. All three presets MUST carry the field.
- **Verdict enum pattern** — Phase 12 (IndicatorFilter.Verdict). MacroFilter's `MacroVerdict` is a new enum OR a combination struct (D-07 Claude's Discretion).
- **Hook order: position_manager → IndicatorFilter → MacroFilter** — D-08 insert point is the OUTER decision layer, consistent with "macro overrides local" semantics.
- **Precompute columns on the input DataFrame** — `core.indicators.build_indicator_dataframe()` precedent. MacroFilter's `add_macro_columns()` is a parallel entry point that runs AFTER `build_indicator_dataframe`.
- **Backward-compat test suite per feature gate** — Phase 38 `test_phase38_backward_compat.py`, Phase 39 `test_phase39_backward_compat.py`. Phase 44 produces `test_macro_filter_v6_parity.py`.
- **Hard short-circuit for parity** — NOT compute-and-ignore. Phase 38/39 gates short-circuit; Phase 44 follows per D-09.
- **Pytest `@pytest.mark.regression`** — gates determinism-sensitive tests. Phase 44 parity test inherits.

### Integration Points

**Inputs:**
- VN30 OHLCV via `DataLoader('vn30').load('2015-01-05', '2026-03-31')` — Phase 42 D-10 canonical window.
- `data/vn_liquidity_proxy.csv` (6 columns, 2867 rows) — Phase 43 LIQ-01 output. MacroFilter reads `dxy_close`, `eem_close`.
- `data/sbv_policy_events.csv` (5 columns, 12 rows) — Phase 43 LIQ-02 output. MacroFilter reads `date`, `direction`.
- `VN30_PRESET` from [strategies/mdm_hybrid/config.py:141](strategies/mdm_hybrid/config.py#L141) — base config. Extended with D-15 fields; default-off feature gate preserves Phase 42 parity.
- `output/v10_reconciled_baseline.json` — parity target. Phase 44 parity test loads this file at test runtime per Phase 42 D-14 (NOT hardcoded).

**Outputs Phase 44 creates:**
- `strategies/mdm_hybrid/macro_filter.py` — NEW (MacroFilter class, MacroVerdict enum, add_macro_columns helper, path constants).
- Edit `strategies/mdm_hybrid/config.py` — append D-15 fields + update presets.
- Edit `strategies/mdm_hybrid/mdm_hybrid_engine.py` — inject MacroFilter call per D-08.
- Edit `strategies/mdm_hybrid/position_manager.py` — consume effective `dd_cash_threshold` from MacroFilter per D-02 (design via discretion — could be a callback, could be a config override struct).
- Edit `strategies/mdm_hybrid/stop_loss.py` — consume effective `stop_loss_max_multiplier` from MacroFilter per D-03 (same plumbing choice).
- `tests/test_macro_filter.py` — NEW (ROADMAP SC-1/2/3 unit tests).
- `tests/test_macro_filter_v6_parity.py` — NEW (MACRO-04 / VAL-04 regression).
- Edit `.planning/ROADMAP.md` — update Phase 44 SC-5 per D-05.
- Edit `.planning/REQUIREMENTS.md` — update MACRO-05 per D-05.

**Downstream consumers (Phases 45-47):**
- Phase 45 WF-01 grid search — reads D-15 config field names to build the parameter grid. Grid dimensions: 6 thresholds × 3 windows × 2 policy-knobs (DD threshold + stop-loss mult) = ~10-parameter space (Phase 45 sizes it down).
- Phase 46 VAL-01 A/B — 5 scenarios (baseline / +DXY / +EEM / +SBV / +all) toggle by zeroing out individual MacroFilter fields via preset mutation. MacroFilter's design MUST let "EEM only" (thresholds wide enough to never trigger DXY/SBV) yield the expected scenario behavior.
- Phase 46 VAL-02 OOS HARD gate — reads `output/v10_reconciled_baseline.json` for CAGR floor; Phase 44's VAL-04 parity test is a PRE-REQUISITE (green-parity required before gate meaningful).
- Phase 47 DOC-01 rules doc update — documents MacroFilter policy in `docs/rules_mdm_hybrid.md` per CLAUDE.md code-docs sync rule. Phase 44 does NOT write the rules doc (that's Phase 47).

</code_context>

<specifics>
## Specific Ideas

- **"Update MACRO-05 rather than force half-position"** — user explicit: Phase 44 deviates from the original ROADMAP wording because introducing fractional sizing is a larger refactor than v10.0 should accept. The ROADMAP / REQUIREMENTS.md edit is bundled into this phase's scope (not deferred to a later phase).
- **"Most-restrictive wins" in DXY/SBV conflict** — user picked the conservative combiner. When ANY cautionary signal fires, tightening policies (D-02, D-03) activate. VETO of SELL (D-01) only fires when both DXY and SBV agree on easing (or SBV neutral + DXY easing).
- **"EEM symmetric to DXY"** — user picked the parallel policy design over "EEM as confirmation signal only" or "combine into single liquidity score". Rationale: two independent signals with separate code paths are easier to diagnose and grid-search than a combined scalar.
- **"Hardcode CSV paths"** — user preferred hardcoded path constants over MDMV2Config fields. Phase 43 froze the paths; zero need for runtime override outside test fixtures.
- **"Precompute before engine.run"** — user preferred 1-shot DataFrame enrichment over per-step computation. Aligns with `core.indicators.build_indicator_dataframe` precedent and makes Phase 45 grid search cheaper (re-use precomputed columns across config variants).
- **"Hard short-circuit parity"** — user preferred `if not macro_filter_enabled: return` first-line guard over compute-and-ignore. Zero drift risk. Same decision as Phase 38/39 feature-gate parity.

</specifics>

<deferred>
## Deferred Ideas

- **Fractional position sizing (`Position.size` scalar)** — v11+ candidate. Original MACRO-05 spec called for "half-position or full CASH"; Phase 44 replaces this with stop-loss tightening per D-03/D-05. If v10.0 passes HARD gate but walk-forward suggests fractional sizing would improve OOS, revisit for v11.0.
- **EEM+DXY combined liquidity score** — considered and rejected per D-13. If Phase 45 grid search shows EEM and DXY always move in sync (correlation > 0.8 on the thresholds grid), revisit — a combined score would shrink the grid.
- **Data path as MDMV2Config field** — rejected per D-16 (hardcoded in macro_filter.py). Revisit only if Phase 45/46 needs synthetic CSV injection at runtime (current test path: `add_macro_columns` function arguments).
- **MACRO-05 "forces CASH" behavior** — original spec demanded it; Phase 44 replaces with stop-loss tightening per D-03/D-05. If v10.0 fails HARD gate and forensics suggest SBV tightening lingers too long before causing exits, revisit forced CASH exit in v11.0.
- **Auto-append new SBV events (AUTO-02)** — v2 requirement per REQUIREMENTS.md "Out of scope for v10.0". Phase 44 operates on the frozen 12-row CSV from Phase 43.
- **Statistical Jump Model / Moreira-Muir vol targeting / Foreign flow integration (ALPHA-01..03)** — v11+ candidates per REQUIREMENTS.md. Phase 44 does NOT integrate any of these.
- **Dashboard overlay of DXY_z / EEM_z / SBV_regime columns** — Phase 47 DOC-02 scope, NOT Phase 44.
- **Live yfinance refresh during engine run** — out of scope; Phase 44 reads the frozen CSV. Live refresh is AUTO-01 deferred.

### Reviewed Todos (not folded)
None — no phase 44 todo matches identified at discussion time.

</deferred>

---

*Phase: 44-macro-filter-module*
*Context gathered: 2026-04-22*
