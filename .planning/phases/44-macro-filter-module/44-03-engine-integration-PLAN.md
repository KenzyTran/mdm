---
phase: 44
plan: 03
type: execute
wave: 3
depends_on: ["44-02"]
files_modified:
  - strategies/mdm_hybrid/macro_filter.py
  - strategies/mdm_hybrid/position_manager.py
  - strategies/mdm_hybrid/stop_loss.py
  - strategies/mdm_hybrid/mdm_hybrid_engine.py
autonomous: true
requirements: [MACRO-04, MACRO-05]
must_haves:
  truths:
    - "MacroFilter class exists in strategies/mdm_hybrid/macro_filter.py with apply() method that returns MacroVerdict"
    - "MacroFilter.apply() first line is the D-09 hard short-circuit when macro_filter_enabled=False"
    - "V2PositionManager.process_day() accepts effective_dd_threshold param (default None = use config); BUY-state DD branch reads the override"
    - "StopLossChecker.check() accepts effective_max_multiplier param (default None = use config); _get_effective_stop_pct uses the override"
    - "HybridEngine.run() conditionally calls add_macro_columns ONLY when macro_filter_enabled=True (D-09 dual-layer gate)"
    - "HybridEngine.__init__ instantiates MacroFilter ONLY when macro_filter_enabled=True"
    - "HybridEngine per-row loop computes macro_verdict ONCE before stop_loss check, passes effective_max_multiplier to stop_loss + effective_dd_threshold to position_manager"
    - "HybridEngine VETO_SELL handling restores from snapshot when macro_verdict.veto_sell AND state machine proposed SELL"
    - "All MacroFilter-class-dependent unit tests in tests/test_macro_filter.py PASS (no longer skipped)"
    - "Existing tests still green: tests/test_baseline_determinism.py, tests/test_hybrid_engine.py, tests/test_mdm_regression.py"
  artifacts:
    - path: "strategies/mdm_hybrid/macro_filter.py"
      provides: "MacroFilter class with apply() method (added to existing module from Plan 02)"
      contains: "class MacroFilter"
    - path: "strategies/mdm_hybrid/position_manager.py"
      provides: "process_day with effective_dd_threshold override param"
      contains: "effective_dd_threshold"
    - path: "strategies/mdm_hybrid/stop_loss.py"
      provides: "check + _get_effective_stop_pct with effective_max_multiplier override"
      contains: "effective_max_multiplier"
    - path: "strategies/mdm_hybrid/mdm_hybrid_engine.py"
      provides: "MacroFilter instantiation + precompute gate + per-row hook + VETO_SELL handling"
      contains: "macro_filter_enabled"
  key_links:
    - from: "HybridEngine.run() per-row loop"
      to: "MacroFilter.apply() - MacroVerdict - V2PositionManager.process_day + StopLossChecker.check + VETO_SELL snapshot restore"
      via: "macro_verdict variable computed once per row, fields flow to 3 different consumers"
      pattern: "macro_verdict\\s*=.*macro_filter"
    - from: "HybridEngine.__init__ + HybridEngine.run() precompute block"
      to: "macro_filter_enabled config flag"
      via: "Dual-layer D-09 gate: __init__ sets self.macro_filter=None when disabled; run() skips add_macro_columns when disabled"
      pattern: "if self\\.config\\.v2_config\\.macro_filter_enabled"
---

<objective>
Wire MacroFilter into the HybridEngine via the 6 insertion points specified in RESEARCH §"Common Operation 4". This plan unifies engine, position_manager, and stop_loss changes into a single plan because they are tightly coupled — the engine call site MUST pass effective_dd_threshold to a process_day that accepts it, and effective_max_multiplier to a check() that accepts it. Splitting risks one half landing without the other and breaking everything in between.

Per CONTEXT.md D-09, the gate is DUAL-LAYER:
1. `MacroFilter.apply()` first line: `if not self.config.v2_config.macro_filter_enabled: return MacroVerdict.pass_through()`
2. Engine: `if self.config.v2_config.macro_filter_enabled: df = add_macro_columns(df)` — gate around the helper call

Both gates MUST exist. Missing either breaks parity (Pitfall 1 — adding NaN-filled columns when disabled changes df.equals semantics).

Per CONTEXT.md D-04, MacroVerdict is a STACKING dataclass (not enum). MacroFilter.apply() reads pre-computed columns, applies the most-restrictive combiner, returns a MacroVerdict whose three fields flow to three different consumers. Per RESEARCH §Pattern 5, consumers (process_day + check) accept None-defaulting override parameters that fall back to config defaults — so when MacroVerdict.pass_through() is returned (disabled or no signal), the call sites are byte-identical to the pre-change code path.

Purpose: Land engine integration so MacroFilter actually runs end-to-end. After this plan all unit tests in test_macro_filter.py pass (no skips) and the parity test in test_macro_filter_v6_parity.py becomes meaningful (engine actually invokes MacroFilter when enabled, skips it when disabled). Plan 04 wraps the formal regression sign-off.

Output: 4 files modified (1 module extended, 3 engine-stack files patched).
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/44-macro-filter-module/44-CONTEXT.md
@.planning/phases/44-macro-filter-module/44-RESEARCH.md
@.planning/phases/44-macro-filter-module/44-02-foundation-config-helper-stubs-PLAN.md

@strategies/mdm_hybrid/macro_filter.py
@strategies/mdm_hybrid/position_manager.py
@strategies/mdm_hybrid/stop_loss.py
@strategies/mdm_hybrid/mdm_hybrid_engine.py
@strategies/mdm_hybrid/indicator_filter.py

@tests/test_macro_filter.py
@tests/test_macro_filter_v6_parity.py

<interfaces>
<!-- Key contracts grounded against live code 2026-04-23. -->

From strategies/mdm_hybrid/macro_filter.py (Plan 02 Task 2 output — extends with MacroFilter class):
```python
@dataclass(frozen=True)
class MacroVerdict:
    veto_sell: bool = False
    effective_dd_threshold: Optional[int] = None
    effective_stop_loss_max_multiplier: Optional[float] = None
    @classmethod
    def pass_through(cls) -> "MacroVerdict": ...
    def is_pass(self) -> bool: ...

def add_macro_columns(df, liquidity_proxy_path=..., sbv_events_path=...,
    dxy_window_days=20, eem_window_days=20, sbv_decay_days=90) -> pd.DataFrame:
    """Returns df + dxy_z, eem_z, sbv_regime, sbv_days_since_event columns."""
```

From strategies/mdm_hybrid/position_manager.py (current signature — line 228 onwards):
```python
def process_day(
    self, date, high, low, close, is_ftd, ftd_price, dd_count, is_dd,
    stop_loss_triggered, stop_loss_reason, signal_type="FTD",
    ma10=None, ma50=None, prev_high=0.0, violation_threshold=None,
) -> Tuple[V2MarketState, str]:
    # BUY branch line 351: elif dd_count >= self.config.dd_cash_threshold and is_dd:
    #   exit_to_cash(close, date, f"DD count {dd_count} >= threshold {self.config.dd_cash_threshold}")
```

From strategies/mdm_hybrid/stop_loss.py (current signature — line 36 + line 60):
```python
def _get_effective_stop_pct(self, atr=None, atr_baseline=None) -> float:
    # Line 57: max_pct = self.config.stop_loss_pct * self.config.stop_loss_max_multiplier
    # Line 58: return max(min_pct, min(max_pct, effective))

def check(self, current_close, buy_price, buy_day_low, ma50=None, prev_close=None,
    prev_ma50=None, current_volume=None, prev_volume=None, signal_type="FTD",
    atr=None, atr_baseline=None) -> StopLossResult:
    # Line 119: effective_pct = self._get_effective_stop_pct(atr, atr_baseline)
```

From strategies/mdm_hybrid/mdm_hybrid_engine.py (LIVE LINE NUMBERS verified 2026-04-23):
```python
# Line 26: from .indicator_filter import IndicatorFilter, Verdict
# Line 42: def __init__(self, config: HybridConfig = None):
# Line 50: self.stop_loss_checker = StopLossChecker(v2)
# Line 51: self.position_manager = V2PositionManager(v2)
# Line 53: self.results: Optional[pd.DataFrame] = None
# Line 54: self.indicator_filter = IndicatorFilter(self.config.filter_config) if self.config.filter_enabled else None
# Line 130: def run(self, df: pd.DataFrame) -> pd.DataFrame:
# Line 164: if self.config.v2_config.atr_buffer_enabled:    # ATR buffer precompute gate (precedent)
# Line 173: if self.config.v2_config.refined_dd_enabled:    # refined_dd precompute gate (precedent)
# Line 182: if self.config.filter_enabled:                  # filter indicators precompute
# Line 235: if self.config.two_phase_enabled: snapshot = self._snapshot_components()
# Line 247: current_state = self.position_manager.get_state()
# Line 343-360: stop_loss_checker.check(...) call (line 353 is the actual call; 360 closes args)
# Line 397-413: position_manager.process_day(...) call
# Line 419: # Two-phase commit: Propose-Filter-Decide pipeline (Phase 13)
# Line 420: if self.config.two_phase_enabled and self.config.filter_enabled:
# Line 454-457: Verdict.VETO branch — _restore_components(snapshot); new_state = ...; action = ''
# Line 489: end of two-phase block; line 490 onwards: signal log columns
```

From tests/test_macro_filter.py (Plan 02 Task 3 — currently SKIPPED tests this plan must activate):
- test_short_circuit_when_disabled — needs MacroFilter class
- test_dxy_easing_vetoes_sell — needs MacroFilter.apply
- test_dxy_tightening_lowers_dd — needs MacroFilter.apply
- test_sbv_tightening_shrinks_stop_loss — needs MacroFilter.apply
- test_most_restrictive_combiner — needs MacroFilter.apply
- test_d04_cautionary_wins — needs MacroFilter.apply
- test_eem_easing_vetoes_sell — needs MacroFilter.apply (D-13 symmetry)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Append MacroFilter class to strategies/mdm_hybrid/macro_filter.py</name>
  <files>strategies/mdm_hybrid/macro_filter.py</files>
  <read_first>
    - strategies/mdm_hybrid/macro_filter.py (Plan 02 Task 2 output — MacroVerdict + add_macro_columns + path constants exist; this task APPENDS the MacroFilter class to the same file)
    - strategies/mdm_hybrid/indicator_filter.py (full file — class structure, NaN-safe pattern at line 317, dataclass + class composition style)
    - .planning/phases/44-macro-filter-module/44-CONTEXT.md §D-01..D-04, D-09, D-13 (policy semantics, combiner, EEM symmetry, hard short-circuit)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Code Examples §Common Operation 2" (full MacroFilter.apply reference, lines 611-691)
    - tests/test_macro_filter.py (the 7 currently-skipped tests; their assertions are the contract)
  </read_first>
  <behavior>
    - Test 1 (test_short_circuit_when_disabled): MacroFilter(cfg with macro_filter_enabled=False).apply(empty Series, current_state=None) returns pass_through verdict — DOES NOT raise even on empty row, because first-line guard short-circuits before any column read
    - Test 2 (test_dxy_easing_vetoes_sell): row with dxy_z=-1.5, eem_z=0, sbv_regime='neutral' + current_state=BUY → verdict.veto_sell == True
    - Test 3 (test_dxy_tightening_lowers_dd): row with dxy_z=+1.5, eem_z=0, sbv_regime='neutral' + current_state=BUY → verdict.effective_dd_threshold == cfg.dxy_tightening_dd_threshold (default 3)
    - Test 4 (test_sbv_tightening_shrinks_stop_loss): row with dxy_z=0, eem_z=0, sbv_regime='tightening' → verdict.effective_stop_loss_max_multiplier == cfg.sbv_tightening_stop_loss_max_multiplier (default 1.5)
    - Test 5 (test_most_restrictive_combiner): row with dxy_z=+1.5 AND sbv_regime='tightening' → BOTH effective_dd_threshold AND effective_stop_loss_max_multiplier set; veto_sell == False
    - Test 6 (test_d04_cautionary_wins): row with dxy_z=-1.5 (DXY easing) AND sbv_regime='tightening' (SBV cautionary) → veto_sell == False (D-04 cautionary blocks bullish), effective_stop_loss_max_multiplier set
    - Test 7 (test_eem_easing_vetoes_sell): row with eem_z=+1.5 (D-12 sign flip — POSITIVE z is EEM easing) → verdict.veto_sell == True (D-13 symmetry to DXY)
    - Test 8 (NaN safety, implicit in tests above): row with dxy_z=NaN must not crash; treated as not-easing-not-tightening (per IndicatorFilter D-13 NaN-safe precedent — `pd.notna(x) and ...`)
  </behavior>
  <action>
    APPEND the following class to the END of `strategies/mdm_hybrid/macro_filter.py` (after the existing MacroVerdict dataclass and add_macro_columns function from Plan 02 Task 2). Do NOT modify the existing MacroVerdict or add_macro_columns. Do NOT add any new module-level imports beyond `pd` (already present from Plan 02).

    ```python
    # ── MacroFilter class (Plan 03) ─────────────────────────────────────────

    class MacroFilter:
        """Stateless macro-policy filter for the hybrid engine.

        Reads precomputed dxy_z, eem_z, sbv_regime columns and combines them
        via the most-restrictive rule (D-04) to produce a MacroVerdict.

        The filter never originates new state — it only modulates state-machine
        decisions via three orthogonal policy levers:
          - veto_sell (D-01, D-13): DXY OR EEM easing blocks SELL transition
          - effective_dd_threshold (D-02, D-13): DXY OR EEM tightening lowers
            V2PositionManager.dd_cash_threshold via override parameter
          - effective_stop_loss_max_multiplier (D-03): SBV tightening shrinks
            stop_loss_max_multiplier via StopLossChecker override parameter

        D-04 conflict resolution (most-restrictive wins):
          - If ANY tightening signal active → apply tightening policies (lower
            DD threshold, tighten stop-loss); veto_sell stays False
          - veto_sell requires (any easing) AND (no tightening) — a single
            cautionary signal blocks the bullish veto

        Per CONTEXT.md D-09, when macro_filter_enabled=False the apply()
        method's first line returns pass_through() before reading any column.
        Combined with the engine's gate around add_macro_columns, this is the
        DUAL-LAYER short-circuit that protects v6.0 parity (MACRO-04 / VAL-04).
        """

        def __init__(self, config):
            """Initialize with a HybridConfig.

            Args:
                config: HybridConfig instance — exposes config.v2_config with
                    the 10 D-15 fields landed in Plan 02 Task 1.
            """
            self.config = config

        def apply(self, row, current_state) -> MacroVerdict:
            """Evaluate macro policy for one trading day.

            Args:
                row: pandas Series with dxy_z, eem_z, sbv_regime columns.
                    When macro_filter_enabled=False the row is not even
                    read (D-09 hard short-circuit).
                current_state: V2MarketState (BUY / CASH / SELL). Used by
                    D-01: veto_sell suppresses transitions INTO SELL, not
                    transitions away from SELL.

            Returns:
                MacroVerdict — pass_through if filter disabled, no signal
                active, or NaN columns. Stacking allowed per D-04.
            """
            # Lazy import inside the function to avoid circular deps with
            # position_manager (defensive — position_manager doesn't import
            # this module today, but a future refactor might).
            from .position_manager import V2MarketState

            # ── D-09 HARD SHORT-CIRCUIT — first-line guard guarantees parity ──
            # Do NOT compute votes, read columns, or call helpers when disabled.
            if not self.config.v2_config.macro_filter_enabled:
                return MacroVerdict.pass_through()

            v2 = self.config.v2_config

            # ── Read precomputed columns (NaN-safe per IndicatorFilter D-13) ─
            dxy_z = row.get('dxy_z')
            eem_z = row.get('eem_z')
            sbv_regime = row.get('sbv_regime', 'neutral')

            dxy_easing = pd.notna(dxy_z) and dxy_z < v2.dxy_easing_z_threshold
            dxy_tightening = pd.notna(dxy_z) and dxy_z > v2.dxy_tightening_z_threshold
            # D-12: EEM signs FLIPPED vs DXY (EEM corr +0.19 vs DXY -0.19)
            eem_easing = pd.notna(eem_z) and eem_z > v2.eem_easing_z_threshold
            eem_tightening = pd.notna(eem_z) and eem_z < v2.eem_tightening_z_threshold
            sbv_easing = sbv_regime == 'easing'
            sbv_tightening = sbv_regime == 'tightening'

            # ── D-04 most-restrictive combiner ──────────────────────────────
            any_tightening = dxy_tightening or eem_tightening or sbv_tightening
            any_easing = dxy_easing or eem_easing or sbv_easing

            veto_sell = False
            effective_dd_threshold = None
            effective_stop_loss_max_multiplier = None

            # D-01 / D-13: easing VETOes SELL — but ONLY if no tightening
            # signal active (D-04 cautionary blocks bullish). Veto only
            # meaningful for transitions INTO SELL — D-01 says "block SELL
            # transition, keep current state HOLD/BUY unchanged".
            if any_easing and not any_tightening and current_state != V2MarketState.SELL:
                veto_sell = True

            # D-02 / D-13: DXY OR EEM tightening lowers DD threshold (stacks
            # with D-03 — independent policy lever per D-04, NOT elif).
            if dxy_tightening or eem_tightening:
                effective_dd_threshold = v2.dxy_tightening_dd_threshold

            # D-03: SBV tightening shrinks stop-loss max multiplier
            # (independent of D-02 — stacks per D-04, NOT elif).
            if sbv_tightening:
                effective_stop_loss_max_multiplier = v2.sbv_tightening_stop_loss_max_multiplier

            return MacroVerdict(
                veto_sell=veto_sell,
                effective_dd_threshold=effective_dd_threshold,
                effective_stop_loss_max_multiplier=effective_stop_loss_max_multiplier,
            )
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/test_macro_filter.py::test_short_circuit_when_disabled tests/test_macro_filter.py::test_dxy_easing_vetoes_sell tests/test_macro_filter.py::test_dxy_tightening_lowers_dd tests/test_macro_filter.py::test_sbv_tightening_shrinks_stop_loss tests/test_macro_filter.py::test_most_restrictive_combiner tests/test_macro_filter.py::test_d04_cautionary_wins tests/test_macro_filter.py::test_eem_easing_vetoes_sell -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "class MacroFilter" strategies/mdm_hybrid/macro_filter.py` returns 1
    - `grep -c "def apply" strategies/mdm_hybrid/macro_filter.py` returns 1
    - `grep -c "if not self.config.v2_config.macro_filter_enabled:" strategies/mdm_hybrid/macro_filter.py` returns 1 (first-line guard exists per D-09)
    - `grep -n "return MacroVerdict.pass_through()" strategies/mdm_hybrid/macro_filter.py | wc -l` returns at least 1 (the short-circuit return)
    - `grep -c "any_tightening = dxy_tightening or eem_tightening or sbv_tightening" strategies/mdm_hybrid/macro_filter.py` returns 1 (D-04 most-restrictive combiner)
    - `grep -c "elif" strategies/mdm_hybrid/macro_filter.py` returns 0 inside MacroFilter.apply (Pitfall 5 — no elif between policy applications; verify by reading the file)
    - All 7 previously-skipped tests now PASS: `uv run pytest tests/test_macro_filter.py -v 2>&1 | grep -c "PASSED"` returns at least 14 (Plan 02 Task 3 produced 14+ tests; this plan unblocks the 7 previously-skipped ones)
    - Zero skipped tests in test_macro_filter.py: `uv run pytest tests/test_macro_filter.py -v 2>&1 | grep -c "SKIPPED"` returns 0
    - `uv run pytest tests/test_baseline_determinism.py -x -m regression` exits 0 (no behavioral drift — engine integration not yet wired)
  </acceptance_criteria>
  <done>MacroFilter class appended; all 7 previously-skipped MacroFilter tests pass; zero skipped tests in test_macro_filter.py; baseline determinism still green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add effective_dd_threshold override to V2PositionManager.process_day + effective_max_multiplier override to StopLossChecker</name>
  <files>strategies/mdm_hybrid/position_manager.py, strategies/mdm_hybrid/stop_loss.py</files>
  <read_first>
    - strategies/mdm_hybrid/position_manager.py (full file — process_day signature line 228, BUY branch elif at line 351, v60_strict_mode branch at line 280-303 which we MUST NOT touch)
    - strategies/mdm_hybrid/stop_loss.py (full file — _get_effective_stop_pct at line 36, check at line 60, line 119 effective_pct call)
    - .planning/phases/44-macro-filter-module/44-CONTEXT.md §D-02 (DD threshold override semantics) and §D-03 (stop-loss multiplier override)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Architecture Patterns §Pattern 5" (Effective-Override Parameters Down the Call Stack, lines 326-371) — INCLUDES THE PARITY INVARIANT WARNING ("the new branch's else arm reads the EXACT same field that the original code read")
  </read_first>
  <behavior>
    - Test 1 (parity invariant — implicit): When effective_dd_threshold=None is passed, process_day's BUY-branch DD elif fires at the same dd_count as before (uses self.config.dd_cash_threshold)
    - Test 2 (parity invariant — implicit): When effective_max_multiplier=None is passed, _get_effective_stop_pct uses self.config.stop_loss_max_multiplier (byte-identical to pre-change behavior)
    - Test 3 (override active): When effective_dd_threshold=3 is passed (override below default 5), the DD exit fires at dd_count=3 instead of dd_count=5
    - Test 4 (override active): When effective_max_multiplier=1.5 is passed (override below default 2.5), max_pct in _get_effective_stop_pct is computed using 1.5 instead of 2.5
    - Test 5 (existing tests still pass): tests/test_baseline_determinism.py + tests/test_hybrid_engine.py + tests/test_mdm_regression.py all exit 0 (existing engine still calls these without the new param, default None preserves all behavior)
  </behavior>
  <action>
    **EDIT 1 — strategies/mdm_hybrid/position_manager.py:**

    Find the process_day signature starting at line 228. Append a new keyword parameter at the END of the signature (after `violation_threshold: float = None,` at line 244), BEFORE the closing `) -> Tuple[V2MarketState, str]:` at line 245:

    BEFORE (lines 228-245):
    ```python
        def process_day(
            self,
            date: pd.Timestamp,
            high: float,
            low: float,
            close: float,
            is_ftd: bool,
            ftd_price: float,
            dd_count: int,
            is_dd: bool,
            stop_loss_triggered: bool,
            stop_loss_reason: str,
            signal_type: str = "FTD",
            ma10: float = None,
            ma50: float = None,
            prev_high: float = 0.0,
            violation_threshold: float = None,
        ) -> Tuple[V2MarketState, str]:
    ```

    AFTER:
    ```python
        def process_day(
            self,
            date: pd.Timestamp,
            high: float,
            low: float,
            close: float,
            is_ftd: bool,
            ftd_price: float,
            dd_count: int,
            is_dd: bool,
            stop_loss_triggered: bool,
            stop_loss_reason: str,
            signal_type: str = "FTD",
            ma10: float = None,
            ma50: float = None,
            prev_high: float = 0.0,
            violation_threshold: float = None,
            effective_dd_threshold: int = None,   # Phase 44 D-02 — MacroFilter override; None = use config default
        ) -> Tuple[V2MarketState, str]:
    ```

    Update the docstring (around line 263, the existing `violation_threshold:` line) to include:
    ```python
                effective_dd_threshold: Phase 44 D-02 — MacroFilter override
                    for self.config.dd_cash_threshold; None = use config default.
                    DXY/EEM tightening lowers this from 5 to 3 (default).
    ```

    Find the BUY-branch DD elif at the CURRENT line 351:

    BEFORE (line 351-353):
    ```python
                # Check DD threshold (on a DD day)
                elif dd_count >= self.config.dd_cash_threshold and is_dd:
                    self.exit_to_cash(close, date, f"DD count {dd_count} >= threshold {self.config.dd_cash_threshold}")
                    action = f"CASH exit: DD count {dd_count}"
    ```

    AFTER (resolves dd_threshold once, then uses it; preserves byte-identical behavior when override is None):
    ```python
                # Check DD threshold (on a DD day) — Phase 44 D-02 override
                # When effective_dd_threshold is None (default, or MacroFilter
                # disabled / no DXY-EEM tightening), this reads self.config.dd_cash_threshold
                # and the comparison is byte-identical to the pre-Phase-44 code path.
                else:
                    dd_threshold = (
                        effective_dd_threshold
                        if effective_dd_threshold is not None
                        else self.config.dd_cash_threshold
                    )
                    if dd_count >= dd_threshold and is_dd:
                        self.exit_to_cash(close, date, f"DD count {dd_count} >= threshold {dd_threshold}")
                        action = f"CASH exit: DD count {dd_count}"
                    # Check MA10 consecutive below — keep existing logic
                    elif (self.config.ma10_cash_enabled
                          and self.position.ma10_below_count >= self.config.ma10_cash_consecutive):
                        self.exit_to_cash(close, date, f"Close below MA10 for {self.position.ma10_below_count} days")
                        action = f"CASH exit: MA10 below count {self.position.ma10_below_count}"
    ```

    CRITICAL: After this edit, the original elif at line 354-358 (MA10 consecutive below) MUST be REMOVED because it's now nested inside the `else:` block. Verify by re-reading the file — the BUY branch should have:
    - `if stop_loss_triggered: ...` (existing line 347)
    - `else:` (NEW — replaces the old `elif dd_count >= ...` and `elif (self.config.ma10_cash_enabled...)`
        - resolve dd_threshold
        - `if dd_count >= dd_threshold and is_dd:` (CASH exit DD)
        - `elif (self.config.ma10_cash_enabled and ...):` (CASH exit MA10)

    Why the restructure: the original code chained `elif dd_count >= self.config.dd_cash_threshold and is_dd:` directly off the stop_loss elif. To swap in the variable threshold cleanly, restructure as `else: ... if dd_count >= dd_threshold ... elif ma10 ...`. The control flow is logically identical (when stop_loss not triggered, check DD then MA10 — same order as before).

    DO NOT touch the v60_strict_mode CASH-state branch (lines 280-303) — that branch is Phase 42 BASE-02 territory.
    DO NOT touch the SELL-state branch (lines 360-376) — fail-safe and short-cover logic untouched per Phase 23 / Phase 42 D-11 fail-safe no-fly zone.
    DO NOT change any condition logic, only add the override parameter and the dd_threshold resolution.

    **EDIT 2 — strategies/mdm_hybrid/stop_loss.py:**

    Find `_get_effective_stop_pct` at line 36-58. Append a new parameter:

    BEFORE (line 36):
    ```python
        def _get_effective_stop_pct(self, atr: float = None, atr_baseline: float = None) -> float:
    ```

    AFTER:
    ```python
        def _get_effective_stop_pct(
            self,
            atr: float = None,
            atr_baseline: float = None,
            effective_max_multiplier: float = None,   # Phase 44 D-03 — MacroFilter override
        ) -> float:
    ```

    Find line 57 inside `_get_effective_stop_pct`:

    BEFORE:
    ```python
            max_pct = self.config.stop_loss_pct * self.config.stop_loss_max_multiplier
    ```

    AFTER:
    ```python
            # Phase 44 D-03: when effective_max_multiplier is None (default, or
            # MacroFilter disabled / no SBV tightening), this reads
            # self.config.stop_loss_max_multiplier — byte-identical to pre-change.
            max_multiplier = (
                effective_max_multiplier
                if effective_max_multiplier is not None
                else self.config.stop_loss_max_multiplier
            )
            max_pct = self.config.stop_loss_pct * max_multiplier
    ```

    Find `check` at line 60-73. Append a new parameter to the signature:

    BEFORE (line 60-73):
    ```python
        def check(
            self,
            current_close: float,
            buy_price: float,
            buy_day_low: float,
            ma50: float = None,
            prev_close: float = None,
            prev_ma50: float = None,
            current_volume: float = None,
            prev_volume: float = None,
            signal_type: str = "FTD",
            atr: float = None,
            atr_baseline: float = None,
        ) -> StopLossResult:
    ```

    AFTER:
    ```python
        def check(
            self,
            current_close: float,
            buy_price: float,
            buy_day_low: float,
            ma50: float = None,
            prev_close: float = None,
            prev_ma50: float = None,
            current_volume: float = None,
            prev_volume: float = None,
            signal_type: str = "FTD",
            atr: float = None,
            atr_baseline: float = None,
            effective_max_multiplier: float = None,   # Phase 44 D-03 — MacroFilter override
        ) -> StopLossResult:
    ```

    Find line 119 inside `check`:

    BEFORE:
    ```python
            # Rule 1: Stop loss from buy price (volatility-adaptive)
            effective_pct = self._get_effective_stop_pct(atr, atr_baseline)
    ```

    AFTER:
    ```python
            # Rule 1: Stop loss from buy price (volatility-adaptive)
            # Phase 44 D-03: pass effective_max_multiplier through to _get_effective_stop_pct
            effective_pct = self._get_effective_stop_pct(atr, atr_baseline, effective_max_multiplier)
    ```

    DO NOT touch `check_short` (line 151+) — short stop loss is unchanged per CONTEXT.md scope.
    DO NOT touch the 52WEEK special rule (line 104-116) — signal-type-specific logic untouched.
  </action>
  <verify>
    <automated>uv run pytest tests/test_baseline_determinism.py -x -m regression && uv run pytest tests/test_hybrid_engine.py -x && uv run pytest tests/test_mdm_regression.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "effective_dd_threshold: int = None" strategies/mdm_hybrid/position_manager.py` returns 1 line (signature)
    - `grep -n "effective_max_multiplier: float = None" strategies/mdm_hybrid/stop_loss.py` returns at least 2 lines (one in _get_effective_stop_pct, one in check)
    - `grep -c "if effective_dd_threshold is not None" strategies/mdm_hybrid/position_manager.py` returns 1 (override resolution)
    - `grep -c "if effective_max_multiplier is not None" strategies/mdm_hybrid/stop_loss.py` returns 1 (override resolution)
    - Existing baseline determinism test passes: `uv run pytest tests/test_baseline_determinism.py -x -m regression` exits 0 (parity invariant — None default preserves byte-identical behavior; MUST hold even before engine wires the new params)
    - Existing hybrid engine tests pass: `uv run pytest tests/test_hybrid_engine.py -x` exits 0
    - Existing MDM regression tests pass: `uv run pytest tests/test_mdm_regression.py -x` exits 0
    - Manual sanity (override active path): `uv run python -c "from strategies.mdm_hybrid.config import MDMV2Config; from strategies.mdm_hybrid.stop_loss import StopLossChecker; cfg = MDMV2Config(); chk = StopLossChecker(cfg); pct_default = chk._get_effective_stop_pct(atr=1.0, atr_baseline=1.0); pct_override = chk._get_effective_stop_pct(atr=1.0, atr_baseline=1.0, effective_max_multiplier=1.5); print('default_max:', pct_default, 'override_max:', pct_override); assert pct_override < pct_default; print('PASS')"` exits 0 with PASS
  </acceptance_criteria>
  <done>process_day + check + _get_effective_stop_pct accept None-defaulting override params; existing test suite still green (parity preserved when params=None); override path verified to actually shrink the threshold/multiplier when set.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire MacroFilter into HybridEngine via 6 insertion points (gate + init + per-row hook + VETO_SELL handling)</name>
  <files>strategies/mdm_hybrid/mdm_hybrid_engine.py</files>
  <read_first>
    - strategies/mdm_hybrid/mdm_hybrid_engine.py (full file — verified line numbers in interfaces section above; 6 insertion points spread across __init__, run() precompute block, per-row loop)
    - .planning/phases/44-macro-filter-module/44-CONTEXT.md §D-08 (hook AFTER IndicatorFilter), §D-09 (dual-layer short-circuit), §D-10 (precompute helper signature)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Code Examples §Common Operation 4" (engine hook insertion — exact 6-insertion-point map, lines 765-836)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Architecture Patterns §Pattern 4" (hook insertion mechanics, lines 282-324)
    - tests/test_macro_filter_v6_parity.py (the 2 stubs that activate after this task — they currently mechanically pass via the unmodified-engine path; after this task they EXERCISE the engine-with-MacroFilter path with the gate disabled)
  </read_first>
  <behavior>
    - Test 1 (parity preserved when disabled, MUST be byte-exact): With macro_filter_enabled=False, two fresh engine runs produce df.equals(df)=True (test_signal_log_byte_exact_with_macro_off in tests/test_macro_filter_v6_parity.py)
    - Test 2 (no columns added when disabled): With macro_filter_enabled=False, results DataFrame does NOT contain dxy_z, eem_z, sbv_regime columns (test_macro_columns_absent_when_disabled — D-09 trap detection)
    - Test 3 (existing baseline determinism still passes): tests/test_baseline_determinism.py exits 0 (the engine adds new init/run/loop code but is gated entirely off when macro_filter_enabled=False, so byte-exact parity preserved)
    - Test 4 (engine instantiates MacroFilter when enabled): Manually verify by `MDMV2Config(macro_filter_enabled=True)` + HybridEngine + check that engine.macro_filter is not None
    - Test 5 (engine path with macro on does NOT crash on full VN30 2015-2026 data — smoke test): With macro_filter_enabled=True + v60_strict_mode=True (so we're in same parity territory but with macro on), engine.run(prepared_df) returns a non-empty DataFrame without raising
  </behavior>
  <action>
    Six edits in `strategies/mdm_hybrid/mdm_hybrid_engine.py`. Apply in numbered order; each edit references the LIVE line number in the file BEFORE this task's edits.

    **INSERTION 1 — Module-level import (after line 26):**

    Find line 26: `from .indicator_filter import IndicatorFilter, Verdict`

    Add immediately AFTER (becomes new line 27):
    ```python
    from .macro_filter import MacroFilter, MacroVerdict, add_macro_columns
    ```

    Rationale: top-level import is OK because macro_filter.py has zero side effects at import time (Plan 02 Task 2 verified). Mirror line 26 IndicatorFilter pattern. (Note: RESEARCH §Anti-Patterns warns against importing add_macro_columns at module top — but the warning is about MAKING THE GATE TEXTUALLY OBVIOUS, not about correctness. Plan 03 imports it once at module top so engine.py:27 reads "this module uses MacroFilter"; the precompute gate at INSERTION 2 below remains explicit.)

    **INSERTION 2 — __init__ (after line 54, the existing self.indicator_filter line):**

    Find line 54: `self.indicator_filter = IndicatorFilter(self.config.filter_config) if self.config.filter_enabled else None`

    Add immediately AFTER (becomes new line 55):
    ```python
            # Phase 44 D-09 — instantiate MacroFilter only when feature enabled
            self.macro_filter = (
                MacroFilter(self.config)
                if self.config.v2_config.macro_filter_enabled
                else None
            )
    ```

    Rationale: mirrors line 54 IndicatorFilter conditional instantiation. When disabled, self.macro_filter is None → per-row hook skips evaluation entirely (INSERTION 4).

    **INSERTION 3 — Precompute gate (after line 179, the end of the refined_dd block):**

    Find the refined_dd precompute block at lines 173-179:
    ```python
            # Refined DD volume columns (Phase 39, DD-01/DD-02)
            # Only when enabled -- D-05: no side effects when disabled (protects DD-04)
            if self.config.v2_config.refined_dd_enabled:
                df = Indicators.add_volume_ma_column(df, period=20)
                df = Indicators.add_volume_percentile_column(
                    df,
                    lookback=self.config.v2_config.refined_dd_small_vol_lookback,
                    percentile=self.config.v2_config.refined_dd_small_vol_percentile,
                )
    ```

    Add immediately AFTER (becomes new lines 180-188):
    ```python

            # Macro Filter columns (Phase 44, MACRO-01/02/03)
            # Only when enabled -- D-09: no side effects when disabled (protects MACRO-04 / VAL-04)
            if self.config.v2_config.macro_filter_enabled:
                df = add_macro_columns(
                    df,
                    dxy_window_days=self.config.v2_config.dxy_window_days,
                    eem_window_days=self.config.v2_config.eem_window_days,
                    sbv_decay_days=self.config.v2_config.sbv_decay_days,
                )
    ```

    Rationale: mirrors line 164 (atr_buffer) and line 173 (refined_dd) precompute gates. The gate is the engine half of the dual-layer D-09 short-circuit. Without it, even default-disabled config would add NaN-filled columns (Pitfall 1) and break parity.

    **INSERTION 3.5 — PRESERVE the existing `snapshot = None` safeguard at line 234 (CRITICAL — do NOT remove during refactor):**

    Re-read `strategies/mdm_hybrid/mdm_hybrid_engine.py` lines 233-236 to confirm the LIVE state of the snapshot initialization (verified 2026-04-23):
    ```python
                # Two-phase commit: snapshot before processing
                snapshot = None                                    # ← line 234 — LOAD-BEARING; KEEP
                if self.config.two_phase_enabled:                  # ← line 235
                    snapshot = self._snapshot_components()         # ← line 236
    ```

    The `snapshot = None` initialization at line 234 is LOAD-BEARING for INSERTION 6 below — when `two_phase_enabled=False`, line 234 still runs, binding `snapshot` to `None` for the rest of the per-row loop body. INSERTION 6's guard (`and snapshot is not None`) then correctly evaluates without raising NameError.

    If your edits anywhere in run() accidentally remove or move line 234 (e.g., during a refactor that consolidates the two-phase block), the engine will raise `NameError: name 'snapshot' is not defined` at INSERTION 6 whenever `macro_filter_enabled=True AND two_phase_enabled=False`. This is the crash scenario that the new acceptance criterion below explicitly tests.

    **DO NOT** modify lines 233-236 in any way. **DO NOT** wrap them in an additional `if`. **DO NOT** indent them inside any other block. Verify line 234 is still `            snapshot = None` (12 leading spaces, no prefix `if`) AFTER all 6 INSERTIONs land.

    If for any reason the live file no longer has `snapshot = None` on its own line BEFORE the `if self.config.two_phase_enabled:` check, ADD it back at the top of the per-row loop body with the same indentation, immediately before the `if self.config.two_phase_enabled:` line. The contract is: `snapshot` MUST always be bound to either `None` or the snapshot dict before any code below INSERTION 4 runs.

    **INSERTION 4 — Per-row macro_verdict computation (BEFORE the existing stop_loss check at the current line 353):**

    Find the existing stop_loss check call (currently lines 349-360, with the actual call at line 353):
    ```python
                # Get ATR values for volatility-adaptive stop loss (Phase 17, RISK-02)
                current_atr = row['atr'] if 'atr' in row and pd.notna(row['atr']) else None
                current_atr_baseline = row['atr_baseline'] if 'atr_baseline' in row and pd.notna(row['atr_baseline']) else None

                stop_loss_result = self.stop_loss_checker.check(
                    close, buy_price, buy_day_low,
                    ma50=ma50, prev_close=prev_close, prev_ma50=prev_ma50_val,
                    current_volume=current_volume, prev_volume=prev_volume,
                    signal_type=signal_type_held,
                    atr=current_atr,
                    atr_baseline=current_atr_baseline,
                )
    ```

    Insert NEW code BETWEEN the current_atr_baseline line and the `stop_loss_result = ...` call:
    ```python
                # Phase 44 D-02/D-03/D-08: compute MacroVerdict ONCE per row.
                # Verdict.effective_max_multiplier flows to stop_loss check below.
                # Verdict.effective_dd_threshold flows to position_manager.process_day below.
                # Verdict.veto_sell handled at INSERTION 6 (after IndicatorFilter block).
                macro_verdict = (
                    self.macro_filter.apply(row, current_state)
                    if self.macro_filter is not None
                    else MacroVerdict.pass_through()
                )
    ```

    AND modify the stop_loss_check call by ADDING `effective_max_multiplier=macro_verdict.effective_stop_loss_max_multiplier,` as the LAST kwarg (after `atr_baseline=current_atr_baseline,`):

    AFTER:
    ```python
                stop_loss_result = self.stop_loss_checker.check(
                    close, buy_price, buy_day_low,
                    ma50=ma50, prev_close=prev_close, prev_ma50=prev_ma50_val,
                    current_volume=current_volume, prev_volume=prev_volume,
                    signal_type=signal_type_held,
                    atr=current_atr,
                    atr_baseline=current_atr_baseline,
                    effective_max_multiplier=macro_verdict.effective_stop_loss_max_multiplier,
                )
    ```

    **INSERTION 5 — position_manager.process_day call (modify lines 397-413):**

    Find the existing process_day call:
    ```python
                    new_state, action = self.position_manager.process_day(
                        date=date,
                        high=high,
                        low=low,
                        close=close,
                        is_ftd=is_ftd,
                        ftd_price=ftd_price,
                        dd_count=dd_count,
                        is_dd=is_dd,
                        stop_loss_triggered=stop_loss_result.triggered,
                        stop_loss_reason=stop_loss_result.reason,
                        signal_type=signal_type,
                        ma10=ma10,
                        ma50=ma50_val,
                        prev_high=prev_high,
                        violation_threshold=violation_threshold_val,   # NEW: ATR-02
                    )
    ```

    Add `effective_dd_threshold=macro_verdict.effective_dd_threshold,` as the LAST kwarg (after `violation_threshold=violation_threshold_val,`):

    AFTER:
    ```python
                    new_state, action = self.position_manager.process_day(
                        date=date,
                        high=high,
                        low=low,
                        close=close,
                        is_ftd=is_ftd,
                        ftd_price=ftd_price,
                        dd_count=dd_count,
                        is_dd=is_dd,
                        stop_loss_triggered=stop_loss_result.triggered,
                        stop_loss_reason=stop_loss_result.reason,
                        signal_type=signal_type,
                        ma10=ma10,
                        ma50=ma50_val,
                        prev_high=prev_high,
                        violation_threshold=violation_threshold_val,   # ATR-02
                        effective_dd_threshold=macro_verdict.effective_dd_threshold,   # Phase 44 D-02
                    )
    ```

    **INSERTION 6 — VETO_SELL handling (NEW block AFTER the two-phase IndicatorFilter block at line 489, BEFORE the signal log columns at line 490):**

    Find the end of the two-phase block. The `if self.config.two_phase_enabled and self.config.filter_enabled:` block starts at line 420 and ends at line 488 (the `# old_state == CASH: skip` comment at line 488). Lines 490-493 record signal log columns:

    ```python
                    # Record signal log columns for every trading day (D-09, D-10)
                    df.at[idx, 'old_state'] = old_state.value
                    df.at[idx, 'proposed'] = proposal
                    df.at[idx, 'verdict'] = verdict.value
    ```

    The two-phase block ends at line 493 (closing the inner `if`); then line 494 is `else:` (filter disabled fallback), ending at 496. Line 498 begins state history tracking.

    Insert NEW MacroFilter VETO_SELL handling AFTER the two-phase `else:` block ends (after line 496), BEFORE the `# State history tracking` comment at line 498:

    ```python

                # Phase 44 D-01 / INSERTION 6: MacroFilter VETO_SELL handling
                # Applies AFTER IndicatorFilter (D-08 hook order: macro overrules
                # local indicator consensus). Only fires when state machine
                # actually proposed a transition INTO SELL — D-01 explicitly says
                # "block the SELL transition, keep current state HOLD/BUY unchanged".
                # Snapshot may be None when two_phase_enabled=False; in that case
                # the veto is a no-op (RESEARCH Open Q1 — current research recommends
                # documenting this constraint; for now, silently no-op when snapshot
                # is unavailable since macro_filter_enabled=True with two_phase=False
                # is not a supported configuration in v10.0).
                if (
                    macro_verdict.veto_sell
                    and new_state == V2MarketState.SELL
                    and current_state != V2MarketState.SELL
                    and snapshot is not None
                ):
                    self._restore_components(snapshot)
                    new_state = self.position_manager.get_state()
                    action = ''
                    # Diagnostic — overwrites verdict column when present (D-09 signal log)
                    if self.config.two_phase_enabled and self.config.filter_enabled:
                        df.at[idx, 'verdict'] = 'MACRO_VETO_SELL'
    ```

    Rationale: per RESEARCH §Pattern 4, "macro_verdict.veto_sell handled AFTER IndicatorFilter". The VETO_SELL is the OUTERMOST layer — even if IndicatorFilter CONFIRMs a SELL, MacroFilter can rollback. The restore-from-snapshot pattern mirrors lines 454-457 (existing IndicatorFilter VETO branch). The `snapshot is not None` guard handles the edge case flagged in RESEARCH Open Q1 — silently no-op rather than crash if a future config combines macro on + two_phase off.

    **CRITICAL non-modification:**
    DO NOT touch lines 56-57 (`self._dd5_high_locked = 0.0`).
    DO NOT touch the existing `if self.config.two_phase_enabled and self.config.filter_enabled:` block (lines 420-488 — IndicatorFilter logic untouched).
    DO NOT touch the SELL-state branch logic in position_manager (line 360+) — fail-safe untouched.
    DO NOT touch the VETO/OVERRIDE branches at lines 451-487 — IndicatorFilter pipeline untouched per D-08 (MacroFilter is the OUTER layer, not a replacement).
  </action>
  <verify>
    <automated>uv run pytest tests/test_baseline_determinism.py -x -m regression && uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression && uv run pytest tests/test_macro_filter.py -x && uv run pytest tests/test_hybrid_engine.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "from .macro_filter import" strategies/mdm_hybrid/mdm_hybrid_engine.py` returns 1 line (INSERTION 1)
    - `grep -c "self.macro_filter = " strategies/mdm_hybrid/mdm_hybrid_engine.py` returns 1 (INSERTION 2 — __init__ instantiation)
    - `grep -c "if self.config.v2_config.macro_filter_enabled:" strategies/mdm_hybrid/mdm_hybrid_engine.py` returns at least 1 (INSERTION 3 — precompute gate; matches the dual-layer D-09 pattern)
    - `grep -c "macro_verdict = " strategies/mdm_hybrid/mdm_hybrid_engine.py` returns 1 (INSERTION 4 — per-row computation)
    - `grep -c "effective_max_multiplier=macro_verdict.effective_stop_loss_max_multiplier" strategies/mdm_hybrid/mdm_hybrid_engine.py` returns 1 (INSERTION 4 — passed to stop_loss)
    - `grep -c "effective_dd_threshold=macro_verdict.effective_dd_threshold" strategies/mdm_hybrid/mdm_hybrid_engine.py` returns 1 (INSERTION 5 — passed to position_manager)
    - `grep -c "macro_verdict.veto_sell" strategies/mdm_hybrid/mdm_hybrid_engine.py` returns at least 1 (INSERTION 6 — VETO_SELL handling)
    - `grep -c "MACRO_VETO_SELL" strategies/mdm_hybrid/mdm_hybrid_engine.py` returns 1 (diagnostic in signal log)
    - Existing baseline determinism passes: `uv run pytest tests/test_baseline_determinism.py -x -m regression` exits 0 (parity preserved — engine code added but gated entirely off when macro_filter_enabled=False, which is the test config)
    - New parity stub now actually exercises the engine path: `uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression` exits 0 (both `test_signal_log_byte_exact_with_macro_off` and `test_macro_columns_absent_when_disabled` PASS)
    - All MacroFilter unit tests still pass: `uv run pytest tests/test_macro_filter.py -v 2>&1 | grep -c "PASSED"` returns at least 14
    - Existing hybrid engine tests pass: `uv run pytest tests/test_hybrid_engine.py -x` exits 0
    - Smoke test for enabled path doesn't crash: `uv run python -c "from dataclasses import replace; from core.data_loader import DataLoader; from core.indicators import build_indicator_dataframe; from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine; from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET; cfg = replace(VN30_PRESET, macro_filter_enabled=True, v60_strict_mode=True); df = DataLoader('vn30').load('2020-01-01', '2020-06-30'); df = build_indicator_dataframe(df); engine = HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False)); result = engine.run(df); print('rows:', len(result), 'has_dxy_z:', 'dxy_z' in result.columns); assert 'dxy_z' in result.columns; print('PASS')"` exits 0 with PASS (engine doesn't crash with macro on; columns present)
    - **CRASH-PROOF (INSERTION 3.5 / BLOCKER fix):** The `snapshot = None` safeguard at engine line 234 is preserved AFTER all edits — verify with `grep -nP "^            snapshot = None\s*$" strategies/mdm_hybrid/mdm_hybrid_engine.py` returns at least 1 line (the bare `snapshot = None` on its own line, BEFORE the `if self.config.two_phase_enabled:` check)
    - **CRASH-PROOF acceptance test (macro-on + two_phase-off must not raise NameError):** `uv run python -c "from strategies.mdm_hybrid.config import VN30_PRESET, HybridConfig; from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine; from dataclasses import replace; from models.data_loader import DataLoader; v2 = replace(VN30_PRESET, macro_filter_enabled=True, v60_strict_mode=True); cfg = HybridConfig(v2_config=v2, two_phase_enabled=False, filter_enabled=False); df = DataLoader('vn30').load('2024-01-02', '2024-03-31'); eng = HybridEngine(cfg); eng.run(df); print('OK')" 2>&1 | grep -q "OK"` — proves the engine does NOT raise NameError at INSERTION 6 when `two_phase_enabled=False AND macro_filter_enabled=True` (the configuration that would have crashed if line 234's `snapshot = None` had been removed; INSERTION 6's `and snapshot is not None` guard correctly no-ops the veto)
  </acceptance_criteria>
  <done>HybridEngine wired with all 6 insertion points; dual-layer D-09 short-circuit verified (parity test passes); MacroFilter unit tests pass; smoke test confirms macro-on path runs end-to-end without crashing.</done>
</task>

</tasks>

<verification>
After all 3 tasks:

1. macro_filter.py contains MacroVerdict + add_macro_columns + path constants (Plan 02) + MacroFilter class (Plan 03 Task 1)
2. position_manager.process_day accepts effective_dd_threshold; stop_loss.check accepts effective_max_multiplier (Task 2)
3. HybridEngine wired with 6 insertion points (Task 3)
4. Dual-layer D-09 gate works: with macro_filter_enabled=False, no columns added + byte-exact parity (test_macro_filter_v6_parity.py PASS)
5. With macro_filter_enabled=True, engine runs end-to-end without crashing on real VN30 data (smoke test PASS)
6. All existing test suites still green:
   - tests/test_baseline_determinism.py
   - tests/test_hybrid_engine.py
   - tests/test_mdm_regression.py
7. All MacroFilter tests now PASS (zero SKIPPED): tests/test_macro_filter.py
</verification>

<success_criteria>
- MacroFilter class exists with apply() method satisfying all 7 unit-test contracts (no skipped tests in test_macro_filter.py)
- Override parameters added to position_manager.process_day and stop_loss.check + _get_effective_stop_pct
- HybridEngine wired with all 6 insertion points; macro_filter_enabled gates everything
- Parity test (test_macro_filter_v6_parity.py) passes — byte-exact equality + no leaked columns when disabled
- Existing test suites all pass: baseline_determinism, hybrid_engine, mdm_regression
- Smoke test confirms macro-on path runs successfully on real VN30 data
- All grep + pytest acceptance criteria pass
</success_criteria>

<output>
After completion, create `.planning/phases/44-macro-filter-module/44-03-SUMMARY.md` documenting:
- Final symbol list of macro_filter.py: `grep -nE "^(def|class|    def)" strategies/mdm_hybrid/macro_filter.py`
- Diff summary of position_manager.py + stop_loss.py + mdm_hybrid_engine.py (lines added/removed)
- Pytest output for: test_macro_filter.py (full suite), test_macro_filter_v6_parity.py, test_baseline_determinism.py, test_hybrid_engine.py
- Smoke test output (engine running with macro_filter_enabled=True on 2020 H1 data)
- Confirmation that the 3 RESEARCH.md Open Questions are resolved:
  - Q1 (VETO_SELL safe when two_phase=False?): handled via `snapshot is not None` guard in INSERTION 6 — silent no-op for unsupported config
  - Q2 (SBV decay calendar vs business days?): calendar (per spec §4.4 verbatim — already in Plan 02 Task 2 helper)
  - Q3 (sbv_days_since_event column?): YES, included in helper (Plan 02 Task 2)
- Note for Plan 04: parity test now meaningfully exercises the engine path; Plan 04 wraps the formal regression sign-off and adds smoke-test coverage for the enabled path
</output>
