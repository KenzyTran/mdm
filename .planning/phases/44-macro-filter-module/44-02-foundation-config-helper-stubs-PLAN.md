---
phase: 44
plan: 02
type: execute
wave: 2
depends_on: ["44-01"]
files_modified:
  - strategies/mdm_hybrid/config.py
  - strategies/mdm_hybrid/macro_filter.py
  - tests/test_macro_filter.py
  - tests/test_macro_filter_v6_parity.py
autonomous: true
requirements: [MACRO-01, MACRO-02, MACRO-03]
must_haves:
  truths:
    - "MDMV2Config exposes all 10 D-15 fields with the documented defaults"
    - "Both VN30_PRESET and NASDAQ_PRESET carry all 10 fields explicitly"
    - "add_macro_columns() correctly enriches a VN30 DataFrame with dxy_z, eem_z, sbv_regime columns via merge_asof(backward) (no look-ahead)"
    - "DXY 20d z-score on a known date matches manually computed value (MACRO-01 unit test)"
    - "EEM 20d z-score on a known date matches manually computed value, sign convention flipped vs DXY (MACRO-02 unit test)"
    - "SBV regime classifier transitions across known event sequence with +1 BusinessDay shift (MACRO-03 unit test)"
    - "SBV regime decays to 'neutral' after sbv_decay_days (MACRO-03 unit test)"
    - "Test scaffolding files (tests/test_macro_filter.py, tests/test_macro_filter_v6_parity.py) exist with stubs covering all 12 validation-contract test IDs"
  artifacts:
    - path: "strategies/mdm_hybrid/config.py"
      provides: "MDMV2Config with 10 D-15 fields + VN30_PRESET + NASDAQ_PRESET extended"
      contains: "macro_filter_enabled"
    - path: "strategies/mdm_hybrid/macro_filter.py"
      provides: "MacroVerdict dataclass + add_macro_columns helper + path constants"
      exports: ["MacroVerdict", "add_macro_columns", "LIQUIDITY_PROXY_PATH", "SBV_EVENTS_PATH"]
    - path: "tests/test_macro_filter.py"
      provides: "Wave 0 test stubs covering all MACRO-01..05 unit assertions"
      contains: "def test_dxy_zscore_known_date"
    - path: "tests/test_macro_filter_v6_parity.py"
      provides: "Wave 0 parity test stubs (skipped pending MacroFilter class in Plan 03)"
      contains: "@pytest.mark.regression"
  key_links:
    - from: "strategies/mdm_hybrid/macro_filter.py::add_macro_columns"
      to: "data/vn_liquidity_proxy.csv + data/sbv_policy_events.csv"
      via: "pd.read_csv + pd.merge_asof(direction='backward')"
      pattern: "pd\\.merge_asof\\([^)]*direction\\s*=\\s*['\"]backward['\"]"
    - from: "tests/test_macro_filter.py"
      to: "strategies/mdm_hybrid/macro_filter.py::add_macro_columns"
      via: "import + synthetic mini-fixture call"
      pattern: "from strategies\\.mdm_hybrid\\.macro_filter import add_macro_columns"
---

<objective>
Foundation work — three parallelizable concerns that share Wave 2 because none depends on the others, but they collectively unblock Wave 3 (integration). Per RESEARCH.md Architecture Patterns §1, the MacroVerdict is a frozen dataclass (not enum) since D-04 stacks tightening policies. Per CONTEXT.md D-10 + RESEARCH.md Code Examples §1, add_macro_columns uses pd.merge_asof(direction='backward') with z-score AFTER the merge. Per CONTEXT.md D-15, both presets carry all 10 fields explicitly.

This plan deliberately bundles config + helper + test stubs because all three are mechanical, share zero implementation surface (different files), and together provide a complete foundation Plan 03 can build the engine integration on without any further file creation.

Purpose: Land the data plumbing (DataFrame enrichment) and config surface so Plan 03 can focus purely on engine wiring. Test stubs go in this plan (not a separate Wave 0) because Phase 42 D-18 precedent uses inline synthetic mini-fixtures; the unit tests for MACRO-01..03 only need add_macro_columns to exist (which lands here), not the MacroFilter class (Plan 03).

Output: 4 files (1 config edit, 1 new module, 2 new test files).
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
@.planning/phases/44-macro-filter-module/44-VALIDATION.md
@docs/liquidity_proxy_spec.md
@strategies/mdm_hybrid/config.py
@strategies/mdm_hybrid/indicator_filter.py
@data/vn_liquidity_proxy.csv
@data/sbv_policy_events.csv

<interfaces>
<!-- Key types/contracts the executor needs. Extracted from codebase 2026-04-23. -->

From strategies/mdm_hybrid/config.py (current state — 10 fields will be appended):
```python
@dataclass
class MDMV2Config:
    # ... 30+ existing fields including:
    dd_cash_threshold: int = 5                 # D-02 override target
    stop_loss_max_multiplier: float = 2.5      # D-03 override target (VN30 preset value)
    atr_buffer_enabled: bool = False           # Phase 38 feature-gate precedent
    refined_dd_enabled: bool = False           # Phase 39 feature-gate precedent
    v60_strict_mode: bool = False              # Phase 42 BASE-02 — line 89
    name: str = "default"
    # __post_init__ does conditional validation gated on feature flags

VN30_PRESET = MDMV2Config(...)               # config.py:141 — explicit constructor with named args
NASDAQ_PRESET = MDMV2Config(...)             # config.py:178 — explicit constructor with named args
```

From data/vn_liquidity_proxy.csv (Phase 43 LIQ-01 frozen schema):
```
6 columns, 2867 rows, dates 2015-01-01..2025-12-31:
  date, usdvnd_close, dxy_close, tnx_close, vnm_close, eem_close
```
Only `dxy_close` and `eem_close` consumed by add_macro_columns per D-10.

From data/sbv_policy_events.csv (Phase 43 LIQ-02 frozen schema):
```
5 columns, 12 rows, dates 2017-07-10..2023-06-19:
  date, rate_change_pct, new_refinance_rate_pct, direction, source
direction ∈ {easing, tightening} only — 'neutral' is DERIVED via 90-day decay.
```

From docs/liquidity_proxy_spec.md §5 (merge contract — MUST follow verbatim):
- Step 1: pd.merge_asof(direction='backward') VN30 dates LEFT, proxy RIGHT, on='date'
- Step 2: rolling z-score AFTER merge on VN30-indexed DataFrame (NOT on raw proxy CSV — trap #4)
- Step 3: SBV merge requires `sbv['effective_date'] = sbv['date'] + pd.tseries.offsets.BusinessDay(1)` BEFORE merge_asof (trap #2)

From RESEARCH §"Common Operation 1" (full add_macro_columns reference implementation, 90 lines, copy-adapt verbatim).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Append D-15 field block to MDMV2Config + extend BOTH presets</name>
  <files>strategies/mdm_hybrid/config.py</files>
  <read_first>
    - strategies/mdm_hybrid/config.py (full file — to see current MDMV2Config field list, both presets at lines 141 and 178, and __post_init__ structure)
    - .planning/phases/44-macro-filter-module/44-CONTEXT.md §D-11..D-15 (the 10-field spec + validation rules)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Code Examples §Common Operation 5" (verbatim diff target with __post_init__ assertions, lines 838-901)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Common Pitfalls §Pitfall 6" (forgetting NASDAQ_PRESET — explicit warning)
  </read_first>
  <behavior>
    - Test 1 (test_config_field_presence): MDMV2Config().macro_filter_enabled == False; all 10 D-15 fields present with documented defaults
    - Test 2 (test_config_field_presence): VN30_PRESET.macro_filter_enabled == False AND VN30_PRESET.dxy_easing_z_threshold == -1.0 AND VN30_PRESET.sbv_tightening_stop_loss_max_multiplier == 1.5 (all 10 fields explicitly set in preset constructor — not relying on dataclass defaults)
    - Test 3 (test_config_field_presence): NASDAQ_PRESET.macro_filter_enabled == False AND same field-presence checks (Pitfall 6 guard — both presets carry the block)
    - Test 4 (test_config_validation_gated_on_flag): MDMV2Config(macro_filter_enabled=True, dxy_easing_z_threshold=+1.0) raises AssertionError ("dxy_easing_z_threshold should be negative")
    - Test 5 (test_config_validation_gated_on_flag): MDMV2Config(macro_filter_enabled=False, dxy_easing_z_threshold=+1.0) does NOT raise — validation only fires when feature enabled (Phase 39 D-06 precedent)
    - Test 6 (test_config_validation_gated_on_flag): MDMV2Config(macro_filter_enabled=True, sbv_tightening_stop_loss_max_multiplier=3.0, stop_loss_max_multiplier=2.5) raises AssertionError (sbv override must be ≤ stop_loss_max_multiplier)
  </behavior>
  <action>
    Append the following block to MDMV2Config DIRECTLY AFTER the v60_strict_mode field (currently config.py:89), BEFORE __post_init__ (currently config.py:91):

    ```python
        # ── Macro Filter (Phase 44, MACRO-01..05) ───────────────────────────
        # Feature-gated default-off; when False, helper not called and
        # MacroFilter.apply() returns pass_through on first line (D-09).
        macro_filter_enabled: bool = False

        # Threshold fields (Phase 45 grid-search inputs)
        dxy_easing_z_threshold: float = -1.0           # D-11 — DXY z < this → easing → VETO SELL
        dxy_tightening_z_threshold: float = +1.0       # D-11 — DXY z > this → tightening → lower DD
        eem_easing_z_threshold: float = +1.0           # D-12 — sign FLIPPED vs DXY (EEM corr +0.19)
        eem_tightening_z_threshold: float = -1.0       # D-12 — sign FLIPPED vs DXY

        # Window fields
        dxy_window_days: int = 20                      # D-14 — z-score lookback
        eem_window_days: int = 20                      # D-14 — z-score lookback
        sbv_decay_days: int = 90                       # D-14 — regime decay to neutral

        # Policy override fields (consumed at use-site, not in-place mutation)
        dxy_tightening_dd_threshold: int = 3           # D-02 — V2PositionManager override
        sbv_tightening_stop_loss_max_multiplier: float = 1.5  # D-03 — StopLossChecker override
    ```

    Append to __post_init__ (after the existing refined_dd_enabled validation block at config.py:100-108):

    ```python
            # Macro Filter validation only fires when feature is enabled (Phase 39 D-06 precedent)
            if self.macro_filter_enabled:
                assert self.dxy_easing_z_threshold < 0, (
                    f"dxy_easing_z_threshold should be negative (e.g., -1.0); "
                    f"got {self.dxy_easing_z_threshold}"
                )
                assert self.dxy_tightening_z_threshold > 0, (
                    f"dxy_tightening_z_threshold should be positive (e.g., +1.0); "
                    f"got {self.dxy_tightening_z_threshold}"
                )
                assert self.eem_easing_z_threshold > 0, (
                    f"eem_easing_z_threshold should be positive (sign flipped vs DXY); "
                    f"got {self.eem_easing_z_threshold}"
                )
                assert self.eem_tightening_z_threshold < 0, (
                    f"eem_tightening_z_threshold should be negative (sign flipped vs DXY); "
                    f"got {self.eem_tightening_z_threshold}"
                )
                assert self.dxy_window_days > 0, "dxy_window_days must be positive"
                assert self.eem_window_days > 0, "eem_window_days must be positive"
                assert self.sbv_decay_days > 0, "sbv_decay_days must be positive"
                assert self.dxy_tightening_dd_threshold > 0, (
                    "dxy_tightening_dd_threshold must be positive"
                )
                assert 0 < self.sbv_tightening_stop_loss_max_multiplier <= self.stop_loss_max_multiplier, (
                    f"sbv_tightening_stop_loss_max_multiplier ({self.sbv_tightening_stop_loss_max_multiplier}) "
                    f"must be in (0, stop_loss_max_multiplier={self.stop_loss_max_multiplier}]"
                )
    ```

    Extend VN30_PRESET (config.py:141-176) — append the following 10 named-arg lines at the end of the constructor, AFTER `v60_strict_mode=False,` (currently line 174), BEFORE `name="vn30",` (currently line 175):

    ```python
        # Macro Filter (Phase 44 D-15) — defaults match MDMV2Config defaults; explicit per project convention
        macro_filter_enabled=False,
        dxy_easing_z_threshold=-1.0,
        dxy_tightening_z_threshold=+1.0,
        eem_easing_z_threshold=+1.0,
        eem_tightening_z_threshold=-1.0,
        dxy_window_days=20,
        eem_window_days=20,
        sbv_decay_days=90,
        dxy_tightening_dd_threshold=3,
        sbv_tightening_stop_loss_max_multiplier=1.5,
    ```

    Extend NASDAQ_PRESET (config.py:178-213) — append the SAME 10 named-arg lines at the end of the constructor, AFTER `v60_strict_mode=False,` (currently line 211), BEFORE `name="nasdaq",` (currently line 212).

    DO NOT modify any existing field, default, or preset value. DO NOT modify HybridConfig (config.py:117-136). DO NOT modify the MDMConfig alias (config.py:113).

    Per CONTEXT.md D-09: defaults MUST keep the feature off (macro_filter_enabled=False) so existing tests pass and v6.0 parity is preserved when this plan lands.
  </action>
  <verify>
    <automated>uv run python -c "from strategies.mdm_hybrid.config import MDMV2Config, VN30_PRESET, NASDAQ_PRESET; assert MDMV2Config().macro_filter_enabled is False; assert VN30_PRESET.macro_filter_enabled is False; assert NASDAQ_PRESET.macro_filter_enabled is False; assert VN30_PRESET.dxy_easing_z_threshold == -1.0; assert NASDAQ_PRESET.sbv_tightening_stop_loss_max_multiplier == 1.5; print('PASS')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "macro_filter_enabled" strategies/mdm_hybrid/config.py` returns at least 3 (MDMV2Config field + VN30_PRESET + NASDAQ_PRESET)
    - `grep -c "dxy_easing_z_threshold" strategies/mdm_hybrid/config.py` returns at least 3 (field + 2 presets)
    - `grep -c "sbv_tightening_stop_loss_max_multiplier" strategies/mdm_hybrid/config.py` returns at least 3 (field + 2 presets)
    - `grep -c "dxy_tightening_dd_threshold" strategies/mdm_hybrid/config.py` returns at least 3
    - `uv run python -c "from strategies.mdm_hybrid.config import MDMV2Config; assert all(f in MDMV2Config.__dataclass_fields__ for f in ['macro_filter_enabled','dxy_easing_z_threshold','dxy_tightening_z_threshold','eem_easing_z_threshold','eem_tightening_z_threshold','dxy_window_days','eem_window_days','sbv_decay_days','dxy_tightening_dd_threshold','sbv_tightening_stop_loss_max_multiplier']); print('PASS')"` exits 0 with PASS in output
    - `uv run python -c "from strategies.mdm_hybrid.config import MDMV2Config; MDMV2Config(macro_filter_enabled=True, dxy_easing_z_threshold=+1.0)" 2>&1 | grep -q "should be negative"` (validation fires when enabled)
    - `uv run python -c "from strategies.mdm_hybrid.config import MDMV2Config; MDMV2Config(macro_filter_enabled=False, dxy_easing_z_threshold=+1.0); print('OK')" 2>&1 | grep -q "OK"` (validation gated on flag — does NOT fire when disabled)
    - `uv run pytest tests/test_baseline_determinism.py -x -m regression` exits 0 (existing parity invariant still holds — config additions are default-off and inert)
    - `uv run pytest tests/test_hybrid_engine.py -x` exits 0 (existing hybrid engine tests still pass)
  </acceptance_criteria>
  <done>MDMV2Config has all 10 D-15 fields; both presets carry the block explicitly; gated validation works; existing test suite still green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create strategies/mdm_hybrid/macro_filter.py with MacroVerdict + add_macro_columns + path constants</name>
  <files>strategies/mdm_hybrid/macro_filter.py</files>
  <read_first>
    - strategies/mdm_hybrid/indicator_filter.py (full file — class structure, dataclass pattern, NaN-safe evaluation, module docstring style)
    - .planning/phases/44-macro-filter-module/44-CONTEXT.md §D-07..D-10, D-16 (file placement, helper signature, path constants)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Architecture Patterns §Pattern 1" (MacroVerdict dataclass design, lines 181-237)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Code Examples §Common Operation 1" (add_macro_columns full reference implementation, lines 505-609)
    - docs/liquidity_proxy_spec.md (full file — §5 merge contract, §6 look-ahead traps; this is the LOAD-BEARING contract per CONTEXT.md canonical_refs)
    - data/vn_liquidity_proxy.csv (first 5 lines via `head -5` to confirm column order)
    - data/sbv_policy_events.csv (full file — only 12 rows; needed for fixture construction)
  </read_first>
  <behavior>
    - Test 1 (test_dxy_zscore_known_date): On a synthetic 30-row VN30 DataFrame + matching synthetic proxy DataFrame where all dxy_close == 100.0 except day 30 = 110.0, calling add_macro_columns yields dxy_z[29] == (110 - mean(100..110)) / std(100..110) within 1e-9 (deterministic computed value)
    - Test 2 (test_eem_zscore_known_date): Same setup with eem_close varying yields eem_z[N] matching manual computation within 1e-9
    - Test 3 (test_eem_sign_flipped): Verify EEM sign-flipped policy by constructing a synthetic case where eem_z[N] = +1.5 — verify add_macro_columns returns the value (sign convention enforcement is in MacroFilter.apply, not in add_macro_columns; this test asserts that the column IS produced with the natural z-score sign so MacroFilter.apply can apply the flip)
    - Test 4 (test_sbv_regime_transitions): Synthetic SBV CSV with one easing event on 2020-03-17 + VN30 dates [2020-03-16, 2020-03-17, 2020-03-18, 2020-03-19] yields sbv_regime values [neutral, neutral, easing, easing] (BusinessDay(1) shift means 2020-03-17 event becomes effective on 2020-03-18, so 2020-03-17 trading sees the PREVIOUS regime which is 'neutral' since no prior event)
    - Test 5 (test_sbv_decay_to_neutral): SBV easing event on 2020-03-17 + VN30 dates spanning 2020-03-18 (easing) and 2020-06-16 (90 days after effective_date 2020-03-18 = 2020-06-16) — assert regime is 'easing' on 2020-06-15 (89 days) and 'neutral' on 2020-06-17 (91 days). Test uses sbv_decay_days=90.
    - Test 6 (test_sbv_publication_lag_shift): SBV event on 2020-03-17 — assert regime on the SAME DAY (2020-03-17 trading) is NOT the new regime (per spec §6 trap #2). Validates +1 BusinessDay shift.
    - Test 7 (test_no_lookahead_in_dxy): Synthetic case where proxy has dxy_close on 2020-03-15 = 200 (extreme value) — assert that for VN30 date 2020-03-14, the dxy_z does NOT incorporate the 2020-03-15 value (validates direction='backward')
    - Test 8 (test_z_after_merge_not_before): Construct two synthetic cases — one where US has more trading days than VN30 in a window — assert that z-score reflects the VN30-indexed window (i.e., uses values at VN30 dates only after backward-merge, not values at US dates)
  </behavior>
  <action>
    Create NEW file `strategies/mdm_hybrid/macro_filter.py` with the following structure. Module docstring style mirrors `indicator_filter.py:1-21`. The MacroVerdict dataclass is verbatim from RESEARCH §Pattern 1. The add_macro_columns is verbatim from RESEARCH §Common Operation 1.

    ```python
    """
    MacroFilter Module for MDM Hybrid Engine

    Stateless macro-policy filter that overlays DXY/EEM z-score signals and
    SBV regime classification on the v6.0 state-machine decisions. Per
    Phase 44 CONTEXT.md D-04, the filter combines signals via the
    most-restrictive rule and produces a MacroVerdict with three orthogonal
    policy levers (veto sell, lower DD threshold, tighten stop-loss).

    Phase 44: MacroVerdict dataclass + add_macro_columns precompute helper +
    path constants. The MacroFilter class lives in this module too but is
    instantiated/wired in Plan 03 (this plan provides the dataclass + helper
    foundation; Plan 03 adds the .apply() integration).

    Design decisions referenced (44-CONTEXT.md):
      D-04: Most-restrictive combiner — multiple tightening policies stack
      D-07: New file, parallel to indicator_filter.py
      D-08: Hook AFTER IndicatorFilter in HybridEngine.run() (Plan 03 wires)
      D-09: Hard short-circuit when macro_filter_enabled=False
      D-10: Precompute enrichment via add_macro_columns(df, ...)
      D-11..D-15: 10 config fields on MDMV2Config (Plan 02 Task 1 lands them)
      D-16: CSV paths hardcoded (LIQUIDITY_PROXY_PATH, SBV_EVENTS_PATH)

    Code-Docs Sync (CLAUDE.md):
      docs/rules_mdm_hybrid.md update is Phase 47 DOC-01 scope per CONTEXT.md
      memory anchors. Phase 44 commits without touching the rules doc.

      docs/liquidity_proxy_spec.md is the LOAD-BEARING contract for
      add_macro_columns (§5 merge_asof recipe, §6 look-ahead traps). This
      module implements the spec verbatim — no spec deviation, no spec edit
      needed (per RESEARCH.md Open Q5 recommendation).
    """

    from dataclasses import dataclass
    from pathlib import Path
    from typing import Optional

    import pandas as pd


    # ── Path constants (D-16 — hardcoded per Phase 43 frozen contract) ──────
    LIQUIDITY_PROXY_PATH = Path('data/vn_liquidity_proxy.csv')
    SBV_EVENTS_PATH = Path('data/sbv_policy_events.csv')


    @dataclass(frozen=True)
    class MacroVerdict:
        """Per-day macro policy decision.

        Three independent flags + two scalar overrides. Multiple flags can be
        True simultaneously per D-04 most-restrictive combiner — e.g., DXY
        tightening + SBV tightening sets BOTH effective_dd_threshold AND
        effective_stop_loss_max_multiplier in the same verdict.

        Why dataclass not enum: a single-value enum cannot express stacking.
        Per RESEARCH.md Pattern 1, stacking requires orthogonal fields.

        Attributes:
            veto_sell: If True, the engine MUST NOT transition to SELL today
                (regardless of state machine proposal). D-01.
            effective_dd_threshold: Override for V2PositionManager's
                dd_cash_threshold today. None = use config default. D-02 sets
                this to dxy_tightening_dd_threshold (default 3) when DXY or
                EEM tightening active.
            effective_stop_loss_max_multiplier: Override for StopLossChecker's
                stop_loss_max_multiplier today. None = use config default.
                D-03 sets this to sbv_tightening_stop_loss_max_multiplier
                (default 1.5) when SBV tightening active.
        """
        veto_sell: bool = False
        effective_dd_threshold: Optional[int] = None
        effective_stop_loss_max_multiplier: Optional[float] = None

        @classmethod
        def pass_through(cls) -> "MacroVerdict":
            """Sentinel returned when filter is disabled or no signal active.

            All defaults — equivalent to PASS in the original D-08 enum
            phrasing. Use this in MacroFilter.apply()'s D-09 short-circuit.
            """
            return cls()

        def is_pass(self) -> bool:
            """True iff this verdict imposes no policy changes."""
            return (
                not self.veto_sell
                and self.effective_dd_threshold is None
                and self.effective_stop_loss_max_multiplier is None
            )


    def add_macro_columns(
        df: pd.DataFrame,
        liquidity_proxy_path: Path = LIQUIDITY_PROXY_PATH,
        sbv_events_path: Path = SBV_EVENTS_PATH,
        dxy_window_days: int = 20,
        eem_window_days: int = 20,
        sbv_decay_days: int = 90,
    ) -> pd.DataFrame:
        """Enrich VN30 DataFrame with dxy_z, eem_z, sbv_regime columns.

        Three-step pipeline per docs/liquidity_proxy_spec.md (frozen contract):
            1. Merge proxy CSV onto VN30 dates via merge_asof(backward) — §5.1
            2. Compute rolling z-scores AFTER the merge (VN30-indexed) — §5.3
            3. Merge SBV events on shifted effective_date and apply N-day decay
               — §4.4 / §5.2

        Order of operations is LOAD-BEARING. Computing z-score before merge
        leaks future US closes into VN dates (spec §6 trap #4). Using SBV date
        directly without +1 BusinessDay shift uses same-session info (trap #2).
        Using direction='nearest' or 'forward' reintroduces look-ahead (traps
        #1 and #5).

        Args:
            df: VN30 DataFrame, MUST have a sorted 'date' column (datetime64).
            liquidity_proxy_path: Path to canonical 6-column proxy CSV
                (Phase 43 LIQ-01 output).
            sbv_events_path: Path to canonical 5-column SBV events CSV
                (Phase 43 LIQ-02 output).
            dxy_window_days: Rolling window for DXY z-score (default 20 from
                quick-task 260421-lb4 evidence; corr -0.19 with VN30 forward).
            eem_window_days: Rolling window for EEM z-score (default 20).
            sbv_decay_days: Days after event before regime decays to 'neutral'
                (default 90 = SBV rate-action transmission lag estimate).

        Returns:
            Copy of input DataFrame with appended columns:
                dxy_z (float, NaN during warm-up)
                eem_z (float, NaN during warm-up)
                sbv_regime (str, one of 'easing' | 'neutral' | 'tightening')
                sbv_days_since_event (int/NaN, diagnostic — Claude's Discretion
                                       per RESEARCH.md Open Q3 YES recommendation)
        """
        df = df.copy()
        df = df.sort_values('date').reset_index(drop=True)

        # ── Step 1: merge proxy onto VN30 dates (no look-ahead) ─────────────
        proxy = pd.read_csv(liquidity_proxy_path, parse_dates=['date'])
        proxy = proxy.sort_values('date').reset_index(drop=True)

        merged = pd.merge_asof(
            df,
            proxy[['date', 'dxy_close', 'eem_close']],
            on='date',
            direction='backward',
            allow_exact_matches=True,
        )

        # ── Step 2: rolling z-scores on the merged (VN30-indexed) DataFrame ─
        # CRITICAL: z-score AFTER merge per spec §5.3. Computing on raw proxy
        # would leak future US closes into VN dates (spec §6 trap #4).
        dxy_mean = merged['dxy_close'].rolling(dxy_window_days, min_periods=dxy_window_days).mean()
        dxy_std = merged['dxy_close'].rolling(dxy_window_days, min_periods=dxy_window_days).std()
        merged['dxy_z'] = (merged['dxy_close'] - dxy_mean) / dxy_std

        eem_mean = merged['eem_close'].rolling(eem_window_days, min_periods=eem_window_days).mean()
        eem_std = merged['eem_close'].rolling(eem_window_days, min_periods=eem_window_days).std()
        merged['eem_z'] = (merged['eem_close'] - eem_mean) / eem_std

        # Drop intermediate close columns to keep the schema lean
        merged = merged.drop(columns=['dxy_close', 'eem_close'])

        # ── Step 3: SBV regime via shifted-date merge_asof + N-day decay ────
        sbv = pd.read_csv(sbv_events_path, parse_dates=['date'])
        sbv = sbv.sort_values('date').reset_index(drop=True)
        # CRITICAL: shift first, then merge. Spec §6 trap #2 forbids same-day use.
        sbv['effective_date'] = sbv['date'] + pd.tseries.offsets.BusinessDay(1)

        sbv_merged = pd.merge_asof(
            merged,
            sbv[['effective_date', 'direction']].rename(columns={'direction': 'sbv_raw_direction'}),
            left_on='date',
            right_on='effective_date',
            direction='backward',
            allow_exact_matches=True,
        )

        # Compute decay: days since most-recent SBV effective_date
        sbv_merged['sbv_days_since_event'] = (
            sbv_merged['date'] - sbv_merged['effective_date']
        ).dt.days

        # Apply N-day decay: regime → 'neutral' when no event within sbv_decay_days
        # NaN days_since means we're before the first SBV event — also 'neutral'.
        sbv_merged['sbv_regime'] = sbv_merged['sbv_raw_direction'].where(
            sbv_merged['sbv_days_since_event'].notna()
            & (sbv_merged['sbv_days_since_event'] <= sbv_decay_days),
            other='neutral',
        )

        # Cleanup intermediate columns
        sbv_merged = sbv_merged.drop(columns=['effective_date', 'sbv_raw_direction'])

        return sbv_merged
    ```

    DO NOT add the MacroFilter class in this task — Plan 03 Task 1 lands it. This task ONLY provides MacroVerdict, add_macro_columns, and path constants. (Reason: Plan 03 needs the engine + position_manager + stop_loss changes simultaneously to make MacroFilter.apply meaningful; landing MacroFilter without those wirings would be dead code.)
  </action>
  <verify>
    <automated>uv run python -c "from strategies.mdm_hybrid.macro_filter import MacroVerdict, add_macro_columns, LIQUIDITY_PROXY_PATH, SBV_EVENTS_PATH; v = MacroVerdict.pass_through(); assert v.is_pass(); v2 = MacroVerdict(veto_sell=True, effective_dd_threshold=3, effective_stop_loss_max_multiplier=1.5); assert not v2.is_pass(); assert str(LIQUIDITY_PROXY_PATH).replace(chr(92),'/') == 'data/vn_liquidity_proxy.csv'; print('PASS')"</automated>
  </verify>
  <acceptance_criteria>
    - File `strategies/mdm_hybrid/macro_filter.py` exists
    - `grep -c "class MacroVerdict" strategies/mdm_hybrid/macro_filter.py` returns 1
    - `grep -c "@dataclass(frozen=True)" strategies/mdm_hybrid/macro_filter.py` returns at least 1
    - `grep -c "def add_macro_columns" strategies/mdm_hybrid/macro_filter.py` returns 1
    - `grep -c "direction='backward'" strategies/mdm_hybrid/macro_filter.py` returns exactly 2 (one for proxy merge, one for SBV merge — spec §6 traps #1/#5 both forbid 'nearest'/'forward')
    - `grep -c "BusinessDay(1)" strategies/mdm_hybrid/macro_filter.py` returns 1 (SBV +1 day shift — trap #2)
    - `grep -c "LIQUIDITY_PROXY_PATH" strategies/mdm_hybrid/macro_filter.py` returns at least 2 (constant definition + helper default)
    - `grep -c "SBV_EVENTS_PATH" strategies/mdm_hybrid/macro_filter.py` returns at least 2
    - `grep -c "rolling(dxy_window_days" strategies/mdm_hybrid/macro_filter.py` returns 2 (mean + std — z-score AFTER merge per spec §5.3, trap #4)
    - `grep -c "class MacroFilter" strategies/mdm_hybrid/macro_filter.py` returns 0 (Plan 03 Task 1 adds the class — this task ONLY adds dataclass + helper)
    - Import works: `uv run python -c "from strategies.mdm_hybrid.macro_filter import MacroVerdict, add_macro_columns, LIQUIDITY_PROXY_PATH, SBV_EVENTS_PATH; print('OK')"` exits 0
    - `uv run pytest tests/test_baseline_determinism.py -x -m regression` exits 0 (helper module addition does NOT affect existing engine behavior — verifies no accidental import-time side effects on engine path)
  </acceptance_criteria>
  <done>macro_filter.py exists with MacroVerdict dataclass + add_macro_columns helper + path constants; spec contract honored (backward merge, +1 BusinessDay shift, z-score after merge); MacroFilter class deferred to Plan 03; baseline determinism still green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create tests/test_macro_filter.py + tests/test_macro_filter_v6_parity.py with all stubs from VALIDATION.md</name>
  <files>tests/test_macro_filter.py, tests/test_macro_filter_v6_parity.py</files>
  <read_first>
    - .planning/phases/44-macro-filter-module/44-VALIDATION.md (the 12 test mappings — this is the source of truth for which tests must exist)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Code Examples §Common Operation 3" (verbatim parity test pattern, lines 693-763)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Validation Architecture §Phase Requirements → Test Map" (lines 977-999 — the full per-test specification)
    - tests/test_baseline_determinism.py (full file — class-scoped fixture pattern, _build_reconciled_cfg, _run_once, @pytest.mark.regression usage, lazy-import shim warning at lines 50-57)
    - data/sbv_policy_events.csv (full 12 rows — needed to construct realistic SBV fixture dates)
  </read_first>
  <behavior>
    All stubs follow this pattern: write the test function with the synthetic fixture inline, call the function-under-test, assert the expected behavior. For tests that depend on classes Plan 03 will create (MacroFilter), use `pytest.importorskip` or skip-when-attribute-missing pattern so this task's tests don't break the suite before Plan 03 lands.

    Tests asserting Task 1 (config) MUST pass at end of this task.
    Tests asserting Task 2 (add_macro_columns + MacroVerdict) MUST pass at end of this task.
    Tests asserting Plan 03's MacroFilter class MAY skip until Plan 03 lands.
    The parity test in test_macro_filter_v6_parity.py MAY skip until Plan 03 lands (engine integration required for the parity invariant to be meaningful).

    Per CONTEXT.md "Claude's Discretion" for test data strategy: synthetic mini-fixtures inline in test functions (Phase 42 D-18 precedent — same pattern as test_baseline_determinism.py).
  </behavior>
  <action>
    Create NEW file `tests/test_macro_filter.py` with all 10 unit-test stubs from VALIDATION.md §Per-Task Verification Map (rows 44-01-* and 44-02-*, mapped to MACRO-01..05). Use this exact structure:

    ```python
    """Unit tests for strategies/mdm_hybrid/macro_filter.py (Phase 44, MACRO-01..05).

    Tests cover:
      - MACRO-01: DXY 20d z-score on a known date (test_dxy_zscore_known_date,
                  test_dxy_z_uses_vn_calendar)
      - MACRO-02: EEM 20d z-score on a known date (test_eem_zscore_known_date,
                  test_eem_sign_flipped)
      - MACRO-03: SBV regime classifier transitions + decay + +1-day shift
                  (test_sbv_regime_transitions, test_sbv_decay_to_neutral,
                  test_sbv_publication_lag_shift)
      - MACRO-04: MacroVerdict.pass_through, hard short-circuit when disabled
                  (test_macro_verdict_pass_through, test_short_circuit_when_disabled)
                  [test_short_circuit_when_disabled requires Plan 03 MacroFilter class]
      - MACRO-05: Policy verbs + most-restrictive combiner + EEM symmetry +
                  config validation gating (test_dxy_easing_vetoes_sell,
                  test_dxy_tightening_lowers_dd, test_sbv_tightening_shrinks_stop_loss,
                  test_most_restrictive_combiner, test_d04_cautionary_wins,
                  test_eem_easing_vetoes_sell, test_config_field_presence,
                  test_config_validation_gated_on_flag)
                  [policy/combiner tests require Plan 03 MacroFilter class]

    Synthetic mini-fixtures inline per Phase 42 D-18 precedent — see
    tests/test_baseline_determinism.py for the established pattern.
    """

    from dataclasses import replace
    from pathlib import Path

    import pytest
    import pandas as pd
    import numpy as np

    from strategies.mdm_hybrid.config import MDMV2Config, VN30_PRESET, NASDAQ_PRESET
    from strategies.mdm_hybrid.macro_filter import (
        MacroVerdict,
        add_macro_columns,
        LIQUIDITY_PROXY_PATH,
        SBV_EVENTS_PATH,
    )


    # ── Helpers ─────────────────────────────────────────────────────────────

    def _write_synthetic_proxy(tmp_path: Path, dates, dxy_values, eem_values) -> Path:
        """Write a synthetic 6-column liquidity proxy CSV matching Phase 43 schema."""
        df = pd.DataFrame({
            'date': pd.to_datetime(dates),
            'usdvnd_close': [25000.0] * len(dates),  # placeholder — not consumed
            'dxy_close': dxy_values,
            'tnx_close': [4.0] * len(dates),         # placeholder — not consumed
            'vnm_close': [15.0] * len(dates),        # placeholder — not consumed
            'eem_close': eem_values,
        })
        path = tmp_path / 'proxy.csv'
        df.to_csv(path, index=False)
        return path


    def _write_synthetic_sbv(tmp_path: Path, events) -> Path:
        """Write a synthetic SBV events CSV.

        events: list of (date_str, direction) tuples.
        """
        df = pd.DataFrame({
            'date': pd.to_datetime([e[0] for e in events]),
            'rate_change_pct': [-0.5 if e[1] == 'easing' else +0.5 for e in events],
            'new_refinance_rate_pct': [4.0] * len(events),
            'direction': [e[1] for e in events],
            'source': ['synthetic'] * len(events),
        })
        path = tmp_path / 'sbv.csv'
        df.to_csv(path, index=False)
        return path


    # ── MACRO-01 / MACRO-02 / MACRO-03 (add_macro_columns) ──────────────────

    def test_dxy_zscore_known_date(tmp_path):
        """MACRO-01: DXY 20d z-score on a known date matches manual computation.

        Synthetic case: 30 VN30 dates, dxy_close = [100, 101, ..., 129]. On day
        30 (idx 29), z = (129 - mean(110..129)) / std(110..129).
        """
        dates = pd.date_range('2020-01-01', periods=30, freq='B')
        dxy_values = [100.0 + i for i in range(30)]
        eem_values = [50.0] * 30  # constant — std=0, z will be NaN — separate test
        proxy_path = _write_synthetic_proxy(tmp_path, dates, dxy_values, eem_values)
        sbv_path = _write_synthetic_sbv(tmp_path, [])  # empty SBV — all 'neutral'

        df = pd.DataFrame({'date': dates})
        result = add_macro_columns(df, proxy_path, sbv_path, dxy_window_days=20)

        # Expected dxy_z[29] uses values at indices 10..29 (20-day window ending at 29)
        window = dxy_values[10:30]
        expected_z = (dxy_values[29] - np.mean(window)) / np.std(window, ddof=1)
        assert abs(result['dxy_z'].iloc[29] - expected_z) < 1e-9, (
            f"DXY z-score mismatch: got {result['dxy_z'].iloc[29]}, expected {expected_z}"
        )

    def test_dxy_z_uses_vn_calendar(tmp_path):
        """MACRO-01: rolling z-score window respects VN30 trading days, not US calendar.

        Spec §5.3 + §6 trap #4: z-score MUST be computed AFTER merge so the
        20-day window counts VN30 dates.
        """
        # VN30 has only 10 days in window; US has 20 (more US holidays missed)
        # If z is computed pre-merge: uses 20 US days → different value
        # If z is computed post-merge: uses last 20 VN30 dates (= all 30 US dates with
        #   backward-fill for missing VN30 dates in proxy). Test verifies post-merge.
        # Synthetic: 30 VN30 dates spanning 60 calendar days, proxy has 60 daily values.
        vn_dates = pd.date_range('2020-01-01', periods=30, freq='2B')  # every other business day
        proxy_dates = pd.date_range('2020-01-01', periods=60, freq='B')
        proxy_dxy = list(range(100, 160))
        proxy_eem = [50.0] * 60
        proxy_path = _write_synthetic_proxy(tmp_path, proxy_dates, proxy_dxy, proxy_eem)
        sbv_path = _write_synthetic_sbv(tmp_path, [])

        df = pd.DataFrame({'date': vn_dates})
        result = add_macro_columns(df, proxy_path, sbv_path, dxy_window_days=20)

        # Post-merge z uses VN-indexed values: result['dxy_z'].iloc[29] uses
        # the dxy_close values backward-merged onto vn_dates[10:30].
        # If z were computed pre-merge on the proxy (US calendar), the rolling
        # would average proxy[40:60] = 140..159, mean=149.5; merged to VN it'd be
        # different from the post-merge z. We assert the post-merge value matches
        # the rolling-after-merge expectation.
        merged_dxy = result['dxy_close'].tolist() if 'dxy_close' in result.columns else None
        # dxy_close is dropped after z computation; reconstruct expected from proxy lookup
        expected_window = []
        for d in vn_dates[10:30]:
            mask = pd.to_datetime(proxy_dates) <= d
            expected_window.append(proxy_dxy[mask.sum() - 1])
        expected_z = (expected_window[-1] - np.mean(expected_window)) / np.std(expected_window, ddof=1)
        assert abs(result['dxy_z'].iloc[29] - expected_z) < 1e-9, (
            f"DXY z computed on US calendar (pre-merge) instead of VN calendar (post-merge). "
            f"Spec §6 trap #4 violated. Got {result['dxy_z'].iloc[29]}, expected {expected_z}"
        )

    def test_eem_zscore_known_date(tmp_path):
        """MACRO-02: EEM 20d z-score matches manual computation, same pipeline as DXY."""
        dates = pd.date_range('2020-01-01', periods=30, freq='B')
        dxy_values = [100.0] * 30
        eem_values = [40.0 + i * 0.5 for i in range(30)]
        proxy_path = _write_synthetic_proxy(tmp_path, dates, dxy_values, eem_values)
        sbv_path = _write_synthetic_sbv(tmp_path, [])

        df = pd.DataFrame({'date': dates})
        result = add_macro_columns(df, proxy_path, sbv_path, eem_window_days=20)

        window = eem_values[10:30]
        expected_z = (eem_values[29] - np.mean(window)) / np.std(window, ddof=1)
        assert abs(result['eem_z'].iloc[29] - expected_z) < 1e-9

    def test_eem_sign_flipped(tmp_path):
        """MACRO-02 / D-12: EEM column is produced with natural z-score sign;
        sign-flip semantics live in MacroFilter.apply (Plan 03), not in helper.

        This test ensures add_macro_columns does NOT prematurely apply the EEM
        sign convention — it produces a standard z-score, and the consumer
        applies the (z > +threshold = easing) convention per D-12.
        """
        dates = pd.date_range('2020-01-01', periods=30, freq='B')
        dxy_values = [100.0] * 30
        eem_values = [40.0 - i * 0.5 for i in range(30)]  # DECREASING
        proxy_path = _write_synthetic_proxy(tmp_path, dates, dxy_values, eem_values)
        sbv_path = _write_synthetic_sbv(tmp_path, [])

        df = pd.DataFrame({'date': dates})
        result = add_macro_columns(df, proxy_path, sbv_path, eem_window_days=20)

        # Decreasing series → final z is NEGATIVE (standard z-score)
        # Sign convention flip happens in MacroFilter, not here
        assert result['eem_z'].iloc[29] < 0, (
            f"EEM z-score for decreasing series should be negative (raw z), "
            f"sign convention flip is consumer-side per D-12. Got {result['eem_z'].iloc[29]}"
        )

    def test_sbv_regime_transitions(tmp_path):
        """MACRO-03: SBV regime classifier transitions across known event sequence.

        Synthetic: easing event on 2020-03-17 + tightening on 2020-06-17.
        BusinessDay(1) shift: regime visible from 2020-03-18 (Wed) onward.
        """
        # Use existing SBV CSV format dates; pick weekday to avoid weekend complications
        dates = pd.date_range('2020-03-13', '2020-06-25', freq='B')
        proxy_path = _write_synthetic_proxy(
            tmp_path, dates, [100.0] * len(dates), [50.0] * len(dates)
        )
        sbv_path = _write_synthetic_sbv(tmp_path, [
            ('2020-03-17', 'easing'),
            ('2020-06-17', 'tightening'),
        ])

        df = pd.DataFrame({'date': dates})
        result = add_macro_columns(df, proxy_path, sbv_path, sbv_decay_days=90)

        # 2020-03-17 (Tue) — same-day, regime should be 'neutral' (no prior event,
        # current event not effective until +1 BusinessDay)
        row_0317 = result[result['date'] == pd.Timestamp('2020-03-17')].iloc[0]
        assert row_0317['sbv_regime'] == 'neutral', (
            f"Same-day SBV regime should be 'neutral' (no prior event); got {row_0317['sbv_regime']}"
        )
        # 2020-03-18 (Wed) — effective_date of the easing event, regime = 'easing'
        row_0318 = result[result['date'] == pd.Timestamp('2020-03-18')].iloc[0]
        assert row_0318['sbv_regime'] == 'easing', (
            f"+1-BusinessDay regime should be 'easing'; got {row_0318['sbv_regime']}"
        )
        # 2020-06-18 (Thu) — effective_date of tightening event, regime = 'tightening'
        row_0618 = result[result['date'] == pd.Timestamp('2020-06-18')].iloc[0]
        assert row_0618['sbv_regime'] == 'tightening', (
            f"After tightening event, regime should be 'tightening'; got {row_0618['sbv_regime']}"
        )

    def test_sbv_decay_to_neutral(tmp_path):
        """MACRO-03: SBV regime decays to 'neutral' after sbv_decay_days."""
        dates = pd.date_range('2020-03-13', '2020-08-01', freq='B')
        proxy_path = _write_synthetic_proxy(
            tmp_path, dates, [100.0] * len(dates), [50.0] * len(dates)
        )
        sbv_path = _write_synthetic_sbv(tmp_path, [('2020-03-17', 'easing')])

        df = pd.DataFrame({'date': dates})
        result = add_macro_columns(df, proxy_path, sbv_path, sbv_decay_days=90)

        # effective_date = 2020-03-18; +89 days = 2020-06-15 (within decay)
        # +90 days = 2020-06-16 (exactly at threshold, INCLUSIVE per spec §5.2)
        # +91 days = 2020-06-17 (outside, decayed to neutral)
        row_within = result[result['date'] == pd.Timestamp('2020-06-15')].iloc[0]
        assert row_within['sbv_regime'] == 'easing', (
            f"Within decay window (89 days), regime should still be 'easing'; "
            f"got {row_within['sbv_regime']}"
        )
        row_at_threshold = result[result['date'] == pd.Timestamp('2020-06-16')].iloc[0]
        assert row_at_threshold['sbv_regime'] == 'easing', (
            f"At decay threshold (90 days, INCLUSIVE), regime should still be 'easing'; "
            f"got {row_at_threshold['sbv_regime']}"
        )
        row_decayed = result[result['date'] == pd.Timestamp('2020-06-17')].iloc[0]
        assert row_decayed['sbv_regime'] == 'neutral', (
            f"After decay window (91 days), regime should decay to 'neutral'; "
            f"got {row_decayed['sbv_regime']}"
        )

    def test_sbv_publication_lag_shift(tmp_path):
        """MACRO-03: +1 BusinessDay shift — same-day event NOT visible (spec §6 trap #2)."""
        dates = pd.date_range('2020-03-13', '2020-03-25', freq='B')
        proxy_path = _write_synthetic_proxy(
            tmp_path, dates, [100.0] * len(dates), [50.0] * len(dates)
        )
        sbv_path = _write_synthetic_sbv(tmp_path, [('2020-03-17', 'tightening')])

        df = pd.DataFrame({'date': dates})
        result = add_macro_columns(df, proxy_path, sbv_path, sbv_decay_days=90)

        row_0317 = result[result['date'] == pd.Timestamp('2020-03-17')].iloc[0]
        assert row_0317['sbv_regime'] != 'tightening', (
            f"Same-day SBV regime MUST NOT be 'tightening' — spec §6 trap #2. "
            f"Got '{row_0317['sbv_regime']}' on 2020-03-17 with event on same day."
        )

    # ── MACRO-04 (MacroVerdict + short-circuit) ─────────────────────────────

    def test_macro_verdict_pass_through():
        """MACRO-04: MacroVerdict.pass_through() returns a verdict with is_pass()=True."""
        v = MacroVerdict.pass_through()
        assert v.is_pass(), "pass_through verdict must satisfy is_pass()"
        assert v.veto_sell is False
        assert v.effective_dd_threshold is None
        assert v.effective_stop_loss_max_multiplier is None

    def test_macro_verdict_stacking():
        """MACRO-04 / D-04: MacroVerdict supports stacking — multiple non-None fields."""
        v = MacroVerdict(
            veto_sell=False,
            effective_dd_threshold=3,
            effective_stop_loss_max_multiplier=1.5,
        )
        assert not v.is_pass()
        assert v.effective_dd_threshold == 3
        assert v.effective_stop_loss_max_multiplier == 1.5

    @pytest.mark.skipif(
        not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
        reason='MacroFilter class lands in Plan 03; this test is a stub for that plan'
    )
    def test_short_circuit_when_disabled():
        """MACRO-04 / D-09: macro_filter_enabled=False → first-line return pass_through.

        Plan 03 implements MacroFilter.apply(); this stub passes when the class
        lands and exercises the disabled-path short-circuit.
        """
        from strategies.mdm_hybrid.macro_filter import MacroFilter
        from strategies.mdm_hybrid.config import HybridConfig
        cfg = HybridConfig(v2_config=replace(VN30_PRESET, macro_filter_enabled=False))
        mf = MacroFilter(cfg)
        # Empty row — should not even read columns due to short-circuit
        verdict = mf.apply(pd.Series(dtype=object), current_state=None)
        assert verdict.is_pass(), 'Short-circuit broken — pass_through expected'

    # ── MACRO-05 policy verbs (require MacroFilter class — Plan 03) ─────────

    @pytest.mark.skipif(
        not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
        reason='MacroFilter class lands in Plan 03'
    )
    def test_dxy_easing_vetoes_sell():
        """MACRO-05 / D-01: DXY z < dxy_easing_z_threshold → veto_sell=True."""
        from strategies.mdm_hybrid.macro_filter import MacroFilter
        from strategies.mdm_hybrid.config import HybridConfig
        from strategies.mdm_hybrid.position_manager import V2MarketState
        cfg = HybridConfig(v2_config=replace(VN30_PRESET,
            macro_filter_enabled=True, dxy_easing_z_threshold=-1.0))
        mf = MacroFilter(cfg)
        row = pd.Series({'dxy_z': -1.5, 'eem_z': 0.0, 'sbv_regime': 'neutral'})
        verdict = mf.apply(row, current_state=V2MarketState.BUY)
        assert verdict.veto_sell is True

    @pytest.mark.skipif(
        not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
        reason='MacroFilter class lands in Plan 03'
    )
    def test_dxy_tightening_lowers_dd():
        """MACRO-05 / D-02: DXY z > dxy_tightening_z_threshold → effective_dd_threshold set."""
        from strategies.mdm_hybrid.macro_filter import MacroFilter
        from strategies.mdm_hybrid.config import HybridConfig
        from strategies.mdm_hybrid.position_manager import V2MarketState
        cfg = HybridConfig(v2_config=replace(VN30_PRESET,
            macro_filter_enabled=True, dxy_tightening_z_threshold=+1.0,
            dxy_tightening_dd_threshold=3))
        mf = MacroFilter(cfg)
        row = pd.Series({'dxy_z': +1.5, 'eem_z': 0.0, 'sbv_regime': 'neutral'})
        verdict = mf.apply(row, current_state=V2MarketState.BUY)
        assert verdict.effective_dd_threshold == 3

    @pytest.mark.skipif(
        not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
        reason='MacroFilter class lands in Plan 03'
    )
    def test_sbv_tightening_shrinks_stop_loss():
        """MACRO-05 / D-03: SBV regime=tightening → effective_stop_loss_max_multiplier set."""
        from strategies.mdm_hybrid.macro_filter import MacroFilter
        from strategies.mdm_hybrid.config import HybridConfig
        from strategies.mdm_hybrid.position_manager import V2MarketState
        cfg = HybridConfig(v2_config=replace(VN30_PRESET,
            macro_filter_enabled=True, sbv_tightening_stop_loss_max_multiplier=1.5))
        mf = MacroFilter(cfg)
        row = pd.Series({'dxy_z': 0.0, 'eem_z': 0.0, 'sbv_regime': 'tightening'})
        verdict = mf.apply(row, current_state=V2MarketState.BUY)
        assert verdict.effective_stop_loss_max_multiplier == 1.5

    @pytest.mark.skipif(
        not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
        reason='MacroFilter class lands in Plan 03'
    )
    def test_most_restrictive_combiner():
        """MACRO-05 / D-04: DXY tightening + SBV tightening → BOTH overrides set (stacking)."""
        from strategies.mdm_hybrid.macro_filter import MacroFilter
        from strategies.mdm_hybrid.config import HybridConfig
        from strategies.mdm_hybrid.position_manager import V2MarketState
        cfg = HybridConfig(v2_config=replace(VN30_PRESET, macro_filter_enabled=True))
        mf = MacroFilter(cfg)
        row = pd.Series({'dxy_z': +1.5, 'eem_z': 0.0, 'sbv_regime': 'tightening'})
        verdict = mf.apply(row, current_state=V2MarketState.BUY)
        # BOTH overrides must be set per D-04 stacking
        assert verdict.effective_dd_threshold is not None, 'D-04 stacking broken: dd_threshold not set'
        assert verdict.effective_stop_loss_max_multiplier is not None, 'D-04 stacking broken: stop_loss not set'
        # AND no veto_sell (cautionary tightening blocks bullish veto)
        assert verdict.veto_sell is False, 'D-04 cautionary-wins broken: veto_sell set despite tightening'

    @pytest.mark.skipif(
        not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
        reason='MacroFilter class lands in Plan 03'
    )
    def test_d04_cautionary_wins():
        """MACRO-05 / D-04: DXY easing + SBV tightening → no veto_sell (cautionary blocks bullish)."""
        from strategies.mdm_hybrid.macro_filter import MacroFilter
        from strategies.mdm_hybrid.config import HybridConfig
        from strategies.mdm_hybrid.position_manager import V2MarketState
        cfg = HybridConfig(v2_config=replace(VN30_PRESET, macro_filter_enabled=True))
        mf = MacroFilter(cfg)
        row = pd.Series({'dxy_z': -1.5, 'eem_z': 0.0, 'sbv_regime': 'tightening'})
        verdict = mf.apply(row, current_state=V2MarketState.BUY)
        assert verdict.veto_sell is False, 'D-04 cautionary-wins broken'
        assert verdict.effective_stop_loss_max_multiplier is not None, 'SBV tightening should still tighten stop-loss'

    @pytest.mark.skipif(
        not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
        reason='MacroFilter class lands in Plan 03'
    )
    def test_eem_easing_vetoes_sell():
        """MACRO-05 / D-13: EEM easing alone (z > +threshold) → veto_sell=True (symmetric to DXY)."""
        from strategies.mdm_hybrid.macro_filter import MacroFilter
        from strategies.mdm_hybrid.config import HybridConfig
        from strategies.mdm_hybrid.position_manager import V2MarketState
        cfg = HybridConfig(v2_config=replace(VN30_PRESET,
            macro_filter_enabled=True, eem_easing_z_threshold=+1.0))
        mf = MacroFilter(cfg)
        # Note D-12 sign flip: EEM easing = z > +threshold (positive)
        row = pd.Series({'dxy_z': 0.0, 'eem_z': +1.5, 'sbv_regime': 'neutral'})
        verdict = mf.apply(row, current_state=V2MarketState.BUY)
        assert verdict.veto_sell is True, 'D-13 EEM symmetry broken: EEM easing did not veto SELL'

    # ── Config presence + validation gating (lands with Task 1, runs now) ──

    def test_config_field_presence():
        """MACRO-05 / D-15: All 10 fields present in MDMV2Config + both presets."""
        expected_fields = [
            'macro_filter_enabled',
            'dxy_easing_z_threshold', 'dxy_tightening_z_threshold',
            'eem_easing_z_threshold', 'eem_tightening_z_threshold',
            'dxy_window_days', 'eem_window_days', 'sbv_decay_days',
            'dxy_tightening_dd_threshold', 'sbv_tightening_stop_loss_max_multiplier',
        ]
        for f in expected_fields:
            assert f in MDMV2Config.__dataclass_fields__, f'MDMV2Config missing field: {f}'
            assert hasattr(VN30_PRESET, f), f'VN30_PRESET missing field: {f}'
            assert hasattr(NASDAQ_PRESET, f), f'NASDAQ_PRESET missing field: {f}'
        # Defaults
        assert VN30_PRESET.macro_filter_enabled is False, 'VN30_PRESET must default macro filter OFF (D-09 parity)'
        assert NASDAQ_PRESET.macro_filter_enabled is False, 'NASDAQ_PRESET must default macro filter OFF'
        assert VN30_PRESET.dxy_easing_z_threshold == -1.0
        assert VN30_PRESET.dxy_tightening_z_threshold == +1.0
        assert VN30_PRESET.eem_easing_z_threshold == +1.0
        assert VN30_PRESET.eem_tightening_z_threshold == -1.0
        assert VN30_PRESET.dxy_window_days == 20
        assert VN30_PRESET.eem_window_days == 20
        assert VN30_PRESET.sbv_decay_days == 90
        assert VN30_PRESET.dxy_tightening_dd_threshold == 3
        assert VN30_PRESET.sbv_tightening_stop_loss_max_multiplier == 1.5

    def test_config_validation_gated_on_flag():
        """MACRO-05 / D-09: Validation only fires when macro_filter_enabled=True (Phase 39 D-06 precedent)."""
        # OFF + invalid value → no error (validation gated)
        MDMV2Config(macro_filter_enabled=False, dxy_easing_z_threshold=+1.0)  # Should not raise
        # ON + invalid value → AssertionError
        with pytest.raises(AssertionError, match='should be negative'):
            MDMV2Config(macro_filter_enabled=True, dxy_easing_z_threshold=+1.0)
        with pytest.raises(AssertionError, match='should be positive'):
            MDMV2Config(macro_filter_enabled=True, dxy_tightening_z_threshold=-1.0)
        with pytest.raises(AssertionError, match='must be in'):
            MDMV2Config(macro_filter_enabled=True,
                       sbv_tightening_stop_loss_max_multiplier=3.0,
                       stop_loss_max_multiplier=2.5)
    ```

    Create NEW file `tests/test_macro_filter_v6_parity.py` with the parity test stub from RESEARCH §Common Operation 3 — `pytest.skip` until Plan 03 lands the engine integration:

    ```python
    """v6.0 parity regression test for Phase 44 MacroFilter (MACRO-04 / VAL-04).

    When macro_filter_enabled=False:
      1. Two fresh HybridEngine runs produce byte-exact equal results DataFrames
      2. No dxy_z / eem_z / sbv_regime columns appear in the results

    Pattern verbatim from tests/test_baseline_determinism.py:159-232 with
    macro_filter_enabled=False added to the preset overrides per RESEARCH.md
    Pitfall 8 + Common Operation 3.

    Plan 03 lands the engine integration; this stub will activate then.
    Until then, the test is skipped — `add_macro_columns` (Plan 02 Task 2)
    alone does not exercise the parity invariant.

    Run:  uv run pytest -m regression tests/test_macro_filter_v6_parity.py -v
    """

    from dataclasses import replace

    import pytest
    import pandas as pd

    from core.data_loader import DataLoader
    from core.indicators import build_indicator_dataframe
    from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
    from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config, VN30_PRESET


    DATA_START = '2015-01-05'
    DATA_END = '2026-03-31'


    def _build_macro_off_cfg() -> MDMV2Config:
        """Reconciled v6.0 preset with macro filter EXPLICITLY disabled.

        Mirrors tests/test_baseline_determinism.py:_build_reconciled_cfg with
        an additional macro_filter_enabled=False override per Phase 44 D-09.
        """
        overrides = dict(
            atr_buffer_enabled=False,
            refined_dd_enabled=False,
            macro_filter_enabled=False,  # Phase 44 D-09 — hard short-circuit
        )
        if 'v60_strict_mode' in MDMV2Config.__dataclass_fields__:
            overrides['v60_strict_mode'] = True  # Phase 42-04 contract — RESEARCH.md Pitfall 8
        return replace(VN30_PRESET, **overrides)


    def _run_once(df: pd.DataFrame) -> pd.DataFrame:
        """Fresh HybridEngine -> .run(df.copy()) -> results DataFrame."""
        engine = HybridEngine(HybridConfig(
            v2_config=_build_macro_off_cfg(),
            two_phase_enabled=True,
            filter_enabled=False,
        ))
        return engine.run(df.copy())


    @pytest.mark.regression
    class TestMacroFilterV6Parity:
        """MACRO-04 / VAL-04: macro_filter_enabled=False → byte-exact v6.0 parity.

        These tests REQUIRE Plan 03's engine integration (the precompute gate
        + MacroFilter wiring). Until Plan 03 lands the engine changes, these
        tests would still pass mechanically (engine ignores the new config
        fields when no integration exists yet) — but the TRUE parity invariant
        is meaningless without the integration. Plan 03 makes them meaningful.
        """

        @pytest.fixture(scope='class')
        def prepared_df(self) -> pd.DataFrame:
            df = DataLoader('vn30').load(DATA_START, DATA_END)
            df = build_indicator_dataframe(df)
            return df

        def test_signal_log_byte_exact_with_macro_off(self, prepared_df):
            """Two fresh-engine macro-off runs → byte-exact equal results."""
            results_1 = _run_once(prepared_df)
            results_2 = _run_once(prepared_df)
            assert results_1.equals(results_2), (
                "Signal log DataFrames differ between two macro-off runs. "
                "MacroFilter is leaking state when disabled — D-09 hard short-circuit "
                "is broken."
            )

        def test_macro_columns_absent_when_disabled(self, prepared_df):
            """D-09: no dxy_z / eem_z / sbv_regime columns appear when feature off."""
            results = _run_once(prepared_df)
            for col in ('dxy_z', 'eem_z', 'sbv_regime'):
                assert col not in results.columns, (
                    f"Column '{col}' present when macro_filter_enabled=False. "
                    f"D-09 short-circuit violated — add_macro_columns() was called."
                )
    ```

    DO NOT add a conftest.py — VALIDATION.md §Wave 0 explicitly says no new shared fixtures needed (synthetic mini-fixtures inline per Phase 42 D-18).

    DO NOT include `from analysis.validate_v9 import compute_metrics` at module top — RESEARCH §Pitfall 7 + tests/test_baseline_determinism.py:50-57 explicitly warns. The current parity test design uses df.equals() which doesn't need compute_metrics.
  </action>
  <verify>
    <automated>uv run pytest tests/test_macro_filter.py::test_macro_verdict_pass_through tests/test_macro_filter.py::test_macro_verdict_stacking tests/test_macro_filter.py::test_dxy_zscore_known_date tests/test_macro_filter.py::test_eem_zscore_known_date tests/test_macro_filter.py::test_sbv_regime_transitions tests/test_macro_filter.py::test_sbv_decay_to_neutral tests/test_macro_filter.py::test_sbv_publication_lag_shift tests/test_macro_filter.py::test_config_field_presence tests/test_macro_filter.py::test_config_validation_gated_on_flag -x</automated>
  </verify>
  <acceptance_criteria>
    - File `tests/test_macro_filter.py` exists
    - File `tests/test_macro_filter_v6_parity.py` exists
    - `grep -c "def test_" tests/test_macro_filter.py` returns at least 14 (all VALIDATION.md row-44-01-* and 44-02-* tests + extras)
    - `grep -c "def test_" tests/test_macro_filter_v6_parity.py` returns at least 2
    - `grep -c "@pytest.mark.regression" tests/test_macro_filter_v6_parity.py` returns at least 1 (class-level marker)
    - `grep -c "from analysis.validate_v9" tests/test_macro_filter_v6_parity.py` returns 0 (Pitfall 7 — no module-top import)
    - `grep -c "from analysis.validate_v9" tests/test_macro_filter.py` returns 0
    - All Task 1+2 tests pass: `uv run pytest tests/test_macro_filter.py::test_macro_verdict_pass_through tests/test_macro_filter.py::test_dxy_zscore_known_date tests/test_macro_filter.py::test_eem_zscore_known_date tests/test_macro_filter.py::test_sbv_regime_transitions tests/test_macro_filter.py::test_sbv_decay_to_neutral tests/test_macro_filter.py::test_sbv_publication_lag_shift tests/test_macro_filter.py::test_config_field_presence tests/test_macro_filter.py::test_config_validation_gated_on_flag -x` exits 0
    - Plan-03-dependent tests skip cleanly: `uv run pytest tests/test_macro_filter.py -v 2>&1 | grep -c "SKIPPED"` returns at least 6 (the MacroFilter-class-dependent tests skip until Plan 03)
    - **Pitfall 8 guard (RESEARCH §Common Pitfalls):** parity-test fixture explicitly sets `v60_strict_mode=True` — verify with `grep -c "'v60_strict_mode'" tests/test_macro_filter_v6_parity.py` returns at least 1 (without this, the parity test exercises the wrong config and passes spuriously)
    - `uv run pytest tests/test_baseline_determinism.py -x -m regression` STILL exits 0 (test additions don't break existing parity)
  </acceptance_criteria>
  <done>Test files exist with all 12 VALIDATION.md test stubs (8 plus 4 extras for symmetry coverage); Task 1+2 tests pass; Plan 03-dependent tests skip cleanly; no import-time side effects.</done>
</task>

</tasks>

<verification>
After all 3 tasks:

1. Config: `uv run python -c "from strategies.mdm_hybrid.config import MDMV2Config, VN30_PRESET, NASDAQ_PRESET; m = MDMV2Config(); print(m.macro_filter_enabled, m.dxy_easing_z_threshold, m.sbv_decay_days)"` outputs `False -1.0 90`
2. Helper: `uv run python -c "import pandas as pd; from strategies.mdm_hybrid.macro_filter import add_macro_columns; df = pd.DataFrame({'date': pd.date_range('2020-01-01', periods=30, freq='B')}); result = add_macro_columns(df); print(list(result.columns))"` outputs columns including `dxy_z`, `eem_z`, `sbv_regime`, `sbv_days_since_event`
3. Tests: `uv run pytest tests/test_macro_filter.py -v` shows all Task-1+2 tests PASS + Plan-03-dependent tests SKIPPED
4. Baseline: `uv run pytest tests/test_baseline_determinism.py -x -m regression` exits 0 (no regression)
5. Hybrid engine: `uv run pytest tests/test_hybrid_engine.py -x` exits 0
</verification>

<success_criteria>
- All 10 D-15 fields present in MDMV2Config + both presets explicitly
- macro_filter.py exists with MacroVerdict + add_macro_columns + path constants (no MacroFilter class — Plan 03)
- tests/test_macro_filter.py + tests/test_macro_filter_v6_parity.py exist with all 12+ stubs from VALIDATION.md
- Task 1+2 tests pass; Plan 03-dependent tests skip cleanly via pytest.mark.skipif
- Baseline determinism regression still green (no behavioral drift from config-field additions)
- No `from analysis.validate_v9` at any test module top (Pitfall 7)
- All 3 task acceptance criteria pass via grep + pytest commands
</success_criteria>

<output>
After completion, create `.planning/phases/44-macro-filter-module/44-02-SUMMARY.md` documenting:
- Lines added to config.py (with byte counts and exact line ranges in HEAD)
- macro_filter.py file size + symbol list (`grep -nE "^(def|class) " strategies/mdm_hybrid/macro_filter.py`)
- Test file counts (test functions + skip-conditioned ones)
- Pytest output of all 9 immediately-passing tests in test_macro_filter.py
- Confirmation that test_baseline_determinism.py still passes
- Note for Plan 03: contracts available — `MacroVerdict`, `add_macro_columns`, the 10 config fields. Plan 03 implements `MacroFilter` class + engine wiring + position_manager/stop_loss override params.
</output>
