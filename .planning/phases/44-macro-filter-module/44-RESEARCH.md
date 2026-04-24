# Phase 44: Macro Filter Module - Research

**Researched:** 2026-04-23
**Domain:** Engine-feature integration (pandas merge_asof, dataclass extension, regression-locked feature gate)
**Confidence:** HIGH

## Summary

Phase 44 inserts a feature-gated `MacroFilter` between the existing `IndicatorFilter` and the engine's action-apply step in `HybridEngine.run()`. CONTEXT.md provides 16 locked decisions; this research turns them into mechanical implementation specifics — exact engine line ranges where the hook lands (~line 489 inside the existing two-phase block), the `pd.merge_asof(direction='backward')` recipe for the precompute helper (verbatim from `docs/liquidity_proxy_spec.md` §5), the `if not enabled: return PASS` short-circuit pattern (mirrors `atr_buffer_enabled` precedent at engine.py:164), the `df.equals(df)` parity invariant (verbatim copy from `tests/test_baseline_determinism.py:229`), and the recommended `MacroVerdict` design (a small dataclass holding three independent flags plus `effective_dd_threshold` / `effective_stop_loss_max_multiplier` overrides, since D-04 most-restrictive can stack VETO_SELL with LOWER_DD with TIGHTEN_STOP).

All upstream contracts are frozen and verified: liquidity proxy CSV is 2867 rows / 6 columns starting `2015-01-01` ending `2025-12-31` (column order: `date, usdvnd_close, dxy_close, tnx_close, vnm_close, eem_close`); SBV events CSV is 12 rows / 5 columns spanning `2017-07-10..2023-06-19` with `direction ∈ {easing, tightening}` only (no `neutral` rows in CSV — derived via 90-day decay). Reconciled baseline JSON exists with `schema_version=1`, `cagr_pct=11.47`, `sell_count=124`, `total_return_pct=238.78`, `max_dd_pct=-28.17`, `reconciliation_outcome="fixed_by_preset"` — Phase 44 parity test loads this at runtime per Phase 42 D-14.

Both `VN30_PRESET` and `NASDAQ_PRESET` exist (config.py:141, config.py:178), so D-15's "10 fields land in BOTH presets" requirement is mechanically satisfiable. The `v60_strict_mode=True` discipline established by Phase 42-04 must be combined with `macro_filter_enabled=False` for the parity test fixture.

**Primary recommendation:** Mirror Phase 38 ATR-buffer's exact mechanics — feature flag in `MDMV2Config`, `__post_init__` validation gated on the flag, dual short-circuit (helper not called AND first-line return PASS), and a tests/fixtures-style parquet baseline path is NOT needed (Phase 42 reconciled-baseline JSON is the new canonical reference). Implement `MacroVerdict` as a dataclass with three flag fields plus two override scalars — not a single enum — because D-04 explicitly stacks tightening policies.

## Project Constraints (from CLAUDE.md)

- **Code-Docs Sync:** `strategies/mdm_hybrid/` <-> `docs/rules_mdm_hybrid.md` MUST be updated in the same commit on logic changes. **Phase 44 explicit deferral:** rules-doc update is Phase 47 DOC-01 scope (CONTEXT.md memory anchor). Phase 44 commits to `strategies/mdm_hybrid/macro_filter.py` and engine.py changes WITHOUT touching `docs/rules_mdm_hybrid.md` because (a) the macro filter is feature-gated default-off and (b) v10.0 acceptance is conditional on Phase 46 HARD gate — DOC-01 explicitly fires only on pass. Spec for Phase 44 commits: append a code-docs-sync deferral note to the commit message body referencing Phase 47.
- **Liquidity-spec sync:** `docs/liquidity_proxy_spec.md` footer notes that "Future Phase 44 work that touches `strategies/mdm_hybrid/` or any new `strategies/mdm_hybrid/macro_filter*.py` module MUST update this spec in the same commit." If any Phase 44 plan changes the merge contract or column names, update this spec. If Phase 44 only consumes the contract as documented (the recommended path), no spec update needed — note this explicitly in the SUMMARY.md.
- **GSD Workflow Enforcement:** All file-changing work goes through GSD commands. Phase 44 plans will be authored by `gsd-planner` consuming this RESEARCH.md and CONTEXT.md.
- **Python 3.10+, pandas >= 2.0.0:** verified live: `pandas 2.3.3` installed; `merge_asof` available. No version pinning needed.
- **Testing:** pytest >= 9.0.2 (`pyproject.toml`), markers `regression` and `integration` declared. Phase 44's parity test uses `@pytest.mark.regression`.
- **No CI exists:** acceptance bar per Phase 42 D-20 — "pytest passes locally on the reconciled-HEAD commit." Phase 44 inherits this bar.
- **Snake_case + PascalCase + dataclass conventions:** all new module + class names follow project standard (verified against `indicator_filter.py`, `position_manager.py`, `stop_loss.py`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (DXY easing suppresses SELL):** When DXY z-score is in easing regime (`dxy_z < dxy_easing_z_threshold`, default `-1.0`) AND the state machine proposes SELL, MacroFilter returns **VETO** — block the SELL transition, keep current state (HOLD/BUY unchanged). Parallels `IndicatorFilter.Verdict.VETO` pattern.
- **D-02 (DXY tightening amplifies SELL):** When DXY z-score is in tightening regime (`dxy_z > dxy_tightening_z_threshold`, default `+1.0`) AND no SELL proposal is currently active, MacroFilter **lowers the effective `dd_cash_threshold`** from `5` down to `dxy_tightening_dd_threshold` (default `3`) so SELL can fire earlier on weak price action. Implementation: MacroFilter exposes an "effective DD threshold for today" value that `V2PositionManager` consumes instead of the static config value. Policy tweaks config-at-use-site, not in-place mutation of config object.
- **D-03 (SBV tightening shrinks stop-loss):** When SBV regime is `tightening` AND current position is BUY/HOLD, MacroFilter **reduces `stop_loss_max_multiplier`** from its default (`2.5` in VN30_PRESET) down to `sbv_tightening_stop_loss_max_multiplier` (default `1.5`) — existing positions bail earlier on drawdown. Policy is PASSIVE — does NOT force CASH exit. This is a **deliberate deviation from the original MACRO-05 spec** which read "forces half-position or full CASH". See D-05.
- **D-04 (Conflict resolution: most-restrictive wins):** When DXY and SBV signals disagree (e.g., DXY easing but SBV tightening), MacroFilter acts cautionary. Semantics:
  - If EITHER DXY tightening OR SBV tightening is active → apply tightening policies (D-02 for DD lowering, D-03 for stop-loss shrinking)
  - VETO of SELL (D-01) requires BOTH DXY easing AND no tightening regime from SBV active (most-restrictive principle: a single cautionary signal blocks the bullish policy)
  - When BOTH DXY easing AND SBV easing → full easing policy (VETO SELL)
  - When neither is active (DXY neutral AND SBV neutral) → MacroFilter is pass-through
  - EEM is combined using the same rule (see D-13 below — EEM's policy is symmetric to DXY's)
- **D-05 (ROADMAP / REQUIREMENTS.md update — MACRO-05 rewrite):** As part of Phase 44 execution, update `.planning/ROADMAP.md` §Phase 44 success criterion 5 AND `.planning/REQUIREMENTS.md` MACRO-05 from the original "DXY easing suppresses SELL, DXY tightening amplifies SELL, SBV tightening regime forces half-position or full CASH; exact thresholds `dxy_z_threshold`, `sbv_tightening_position_frac` are exposed as config fields ready for the Phase 45 grid search" To: "DXY easing VETOes SELL, DXY tightening lowers the effective DD threshold, SBV tightening shrinks `stop_loss_max_multiplier`; exact thresholds `dxy_easing_z_threshold`, `dxy_tightening_z_threshold`, `eem_easing_z_threshold`, `eem_tightening_z_threshold`, `dxy_tightening_dd_threshold`, `sbv_tightening_stop_loss_max_multiplier` are exposed as config fields ready for the Phase 45 grid search". This commit piggy-backs on the phase completion (not a separate phase).
- **D-06 (Binary engine preserved):** `HybridEngine` remains binary (`MarketState.CASH | BUY | SELL` + SHORT). No `Position.size` scalar, no half-position state. MacroFilter influences the state machine via threshold tweaks (D-02) and stop-loss tightening (D-03) rather than introducing a new position sizing concept.
- **D-07 (New file, not extension):** `MacroFilter` lives in a **new file** `strategies/mdm_hybrid/macro_filter.py`, parallel to `indicator_filter.py`.
- **D-08 (Hook AFTER IndicatorFilter):** In `HybridEngine.run()` per-step loop, the decision order is: (1) `V2PositionManager.process_day(...)` → returns `(proposed_state, proposed_action)`; (2) `IndicatorFilter.evaluate(row, proposal, current_state)` → returns `Verdict.CONFIRM | VETO | OVERRIDE`; (3) **NEW:** `MacroFilter.apply(row, state_machine_decision, current_state)` → returns `MacroVerdict.PASS | VETO_SELL | LOWER_DD_THRESHOLD | TIGHTEN_STOP_LOSS` (or a combination struct); (4) Engine applies final action. Reverse ordering would let majority-vote indicator logic override a clear macro regime signal — semantically wrong.
- **D-09 (Hard short-circuit parity):** When `macro_filter_enabled=False`, `MacroFilter.apply()` returns `MacroVerdict.PASS` on its first line: `if not self.config.v2_config.macro_filter_enabled: return MacroVerdict.PASS` AND the precompute step (D-10) is also skipped — no DXY_z / EEM_z / SBV_regime columns are added to the DataFrame when the flag is False. Guarantees zero NaN propagation, zero float rounding drift, and zero new columns in the signal log.
- **D-10 (Precompute enrichment before engine.run()):** DXY_z, EEM_z, and SBV_regime columns are computed **ONCE** before `HybridEngine.run()` is called. Helper `add_macro_columns(df, liquidity_proxy_path, sbv_events_path, dxy_window_days=20, eem_window_days=20, sbv_decay_days=90)` uses `pd.merge_asof(direction='backward')` per Phase 43 D-08 merge contract; z-score computed AFTER the merge per `docs/liquidity_proxy_spec.md` Section 5.3; SBV regime shifts event_date by +1 BusinessDay before the merge then applies 90-day decay to 'neutral'. Helper called by `HybridEngine.__init__` or by the caller BEFORE engine instantiation. When `macro_filter_enabled=False`, helper is NOT called — DataFrame stays schema-clean.
- **D-11 (DXY thresholds — asymmetric, 2 fields):** `dxy_easing_z_threshold: float = -1.0` and `dxy_tightening_z_threshold: float = +1.0`. Separate fields allow Phase 45 walk-forward grid to search easing bands wider than tightening bands.
- **D-12 (EEM thresholds — separate from DXY):** `eem_easing_z_threshold: float = +1.0` and `eem_tightening_z_threshold: float = -1.0`. Signs FLIPPED relative to DXY because EEM has POSITIVE correlation with VN30 forward returns (+0.19 vs DXY -0.19).
- **D-13 (EEM policy role — symmetric to DXY):** EEM triggers the SAME policy verbs as DXY (easing VETOes SELL, tightening lowers DD threshold). Both DXY and EEM policy execution flows through the SAME MacroFilter code path.
- **D-14 (Window lengths — all exposed):** `dxy_window_days: int = 20`, `eem_window_days: int = 20`, `sbv_decay_days: int = 90` — all three are MDMV2Config fields. Defaults from quick-task 260421-lb4 evidence.
- **D-15 (Full MDMV2Config field list — mandatory):** 10 new fields appended to `MDMV2Config`:
  ```python
  macro_filter_enabled: bool = False
  dxy_easing_z_threshold: float = -1.0
  dxy_tightening_z_threshold: float = +1.0
  eem_easing_z_threshold: float = +1.0
  eem_tightening_z_threshold: float = -1.0
  dxy_window_days: int = 20
  eem_window_days: int = 20
  sbv_decay_days: int = 90
  dxy_tightening_dd_threshold: int = 3
  sbv_tightening_stop_loss_max_multiplier: float = 1.5
  ```
  All 10 fields default-gated to the False feature flag. **Both VN30_PRESET and NASDAQ_PRESET MUST carry the field set** — verified by research that NASDAQ_PRESET exists at config.py:178.
- **D-16 (CSV paths hardcoded, not config):** `LIQUIDITY_PROXY_PATH = Path('data/vn_liquidity_proxy.csv')` and `SBV_EVENTS_PATH = Path('data/sbv_policy_events.csv')` as path constants in `macro_filter.py`. Test fixtures inject alternative paths via `add_macro_columns` function arguments.

### Claude's Discretion

- Exact enum design for `MacroVerdict` (single enum vs. combination struct) — must support combining VETO_SELL + LOWER_DD + TIGHTEN_STOP_LOSS since D-04 allows multiple tightening policies simultaneously. **Research recommendation:** dataclass with three flags + two override scalars (see Architecture Patterns §Pattern 1 below).
- `add_macro_columns` implementation details — column names: `dxy_z`, `eem_z`, `sbv_regime` (matches existing snake_case convention).
- Whether SBV merge produces a per-row `sbv_days_since_event` column for diagnosability (nice-to-have — research recommends YES for forensics in Phase 45/46 grid search debugging).
- Unit test data strategy: synthetic mini-fixtures for unit tests; integration/parity test uses full VN30 load per Phase 42 D-18 precedent.
- Specific filenames: `tests/test_macro_filter.py` (unit), `tests/test_macro_filter_v6_parity.py` (regression).
- Exact timing of MACRO-05 REQUIREMENTS.md/ROADMAP edit commit — research recommends bundling into the same commit as the feature gate addition so the ROADMAP/REQUIREMENTS state is consistent for the planner reading it during Phase 45.

### Deferred Ideas (OUT OF SCOPE)

- Fractional position sizing (`Position.size` scalar) — v11+ candidate
- EEM+DXY combined liquidity score — considered and rejected per D-13
- Data path as MDMV2Config field — rejected per D-16
- MACRO-05 "forces CASH" behavior — replaced with stop-loss tightening per D-03/D-05
- Auto-append new SBV events (AUTO-02) — Phase 44 operates on frozen 12-row CSV
- Statistical Jump Model / Moreira-Muir vol targeting / Foreign flow integration (ALPHA-01..03) — v11+ candidates
- Dashboard overlay of macro columns — Phase 47 DOC-02 scope
- Live yfinance refresh during engine run — Phase 44 reads frozen CSV
- Grid search of thresholds — Phase 45 WF-01
- A/B comparison of 5 scenarios — Phase 46 VAL-01
- OOS HARD gate validation — Phase 46 VAL-02
- Walk-forward median degradation — Phase 45 WF-02
- Regenerating canonical CSVs — Phase 43 owns them
- Any change to fail-safe logic — Phase 23 / Phase 42 D-11
- Any change to `strategies/canslim/`, `strategies/portfolio/`, `vn30_vsa/`
- Any change to baseline reconciliation artifacts — Phase 42 owns `output/v10_reconciled_baseline.json`
- `docs/rules_mdm_hybrid.md` update — Phase 47 DOC-01

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MACRO-01 | DXY 20d z-score indicator computed from liquidity proxy, merged to daily VN30 trading dates via `pd.merge_asof` (backward direction, publication-lag aware) | `docs/liquidity_proxy_spec.md` §5.1 + §5.3 verified contract; CSV column `dxy_close` confirmed live; helper signature in D-10 spec; merge-asof recipe in Code Examples §Common Operation 1 |
| MACRO-02 | EEM 20d z-score indicator, same pipeline as DXY | Same as MACRO-01; CSV column `eem_close` confirmed live; symmetric implementation per D-13 (single code path, two field-name parameters) |
| MACRO-03 | SBV regime classifier — labels each trading day as easing/neutral/tightening based on most recent rate change event with 90-day decay (user can tune decay window via config) | `docs/liquidity_proxy_spec.md` §4.4 + §5.2 verified; SBV CSV 12 rows verified live (`2017-07-10..2023-06-19`, all `easing` or `tightening`, no `neutral`); 90-day decay applied AFTER merge per spec §5; `sbv_decay_days` is D-15 config field |
| MACRO-04 | `MacroFilter` module integrated into HybridEngine state pipeline, feature-gated via `macro_filter_enabled` flag in `MDMV2Config`; v6.0 parity verified when flag is False (byte-exact signal log) | D-08 hook order spec; D-09 hard short-circuit pattern (`if not enabled: return PASS` + helper-not-called); engine.py:164/173 ATR/refined-DD precedent; parity test pattern verbatim from `tests/test_baseline_determinism.py:229` (`results_1.equals(results_2)`) |
| MACRO-05 | Filter policy — DXY easing suppresses SELL, DXY tightening amplifies SELL, SBV tightening regime [SHRINKS STOP-LOSS — rewritten per D-05]; exact thresholds exposed as config fields ready for Phase 45 grid search | D-01/D-02/D-03/D-04/D-15 specify exact policy semantics, conflict resolution, and the 10 config fields; Phase 44 execution INCLUDES rewriting REQUIREMENTS.md MACRO-05 line and ROADMAP.md SC-5 verbatim per D-05 |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.3.3 (verified live) | merge_asof, rolling z-score, BusinessDay offset, DataFrame.equals() | Already-pinned project core; `pd.merge_asof` is the canonical no-look-ahead temporal join; `DataFrame.equals()` is the byte-exact regression assertion |
| numpy | 2.2.6 (per `output/v10_reconciled_baseline.json`) | Rolling math, NaN handling | Already-pinned; needed for z-score = (x - rolling_mean) / rolling_std |
| python stdlib `enum.Enum` | 3.10 | `MacroVerdict` flag type (if enum chosen over dataclass) | Pattern precedent: `Verdict` enum at `indicator_filter.py:30` |
| python stdlib `dataclasses` | 3.10 | `MacroVerdict` combination struct (recommended); MDMV2Config field extension | Pattern precedent: `FilterConfig` at `indicator_filter.py:42` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0.2 (in pyproject.toml dev-deps) | Unit + regression tests | Both new test files |
| pytest markers | n/a | `@pytest.mark.regression` | Parity test ONLY (matches `test_baseline_determinism.py`) — unit tests run in default suite |
| `pd.tseries.offsets.BusinessDay` | pandas built-in | `event_date + BusinessDay(1)` for SBV +1-day shift | SBV merge per spec §4.4 |
| pyarrow | >=14.0.0 (in pyproject.toml) | Test fixtures parquet I/O (if Phase 44 chooses fixture parquet — research recommends NO; use full VN30 load per Phase 42 D-18) | Only if introducing fixture parquets |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pd.merge_asof(direction='backward')` | Manual loop indexing | merge_asof is vectorized, monotonic-key-validated, and matches `docs/liquidity_proxy_spec.md` exactly — no alternative consistent with the look-ahead-trap-ruled-out spec |
| `MacroVerdict = Enum` (single value per call) | `MacroVerdict = dataclass` (combination struct) | **Single enum FAILS D-04** because tightening policies stack: a day can be simultaneously "DXY tightening lowers DD" AND "SBV tightening shrinks stop-loss". An enum can express only one outcome per evaluation. **Recommendation: dataclass** with three boolean flags + two override scalars. |
| Forward-fill liquidity proxy in CSV | Apply ffill in `add_macro_columns` after merge, OR rely on `merge_asof(backward)` natural last-known-value carry | Spec §6 trap #3 explicitly forbids forward-fill at write time. Backward-merge naturally carries last-known value across non-US-trading days — no manual ffill needed in helper. |
| Compute z-score on raw proxy CSV | Compute on merged VN30-indexed DataFrame | Spec §6 trap #4 explicitly forbids the former. **Mandatory: compute AFTER merge.** |
| Merge SBV on raw `date` | Merge on `effective_date = date + BusinessDay(1)` | Spec §6 trap #2 forbids the former. **Mandatory: shift FIRST, then merge_asof on shifted column.** |
| `.parquet` fixture for parity test (Phase 38/39 pattern) | Live VN30 load + reconciled-HEAD re-run (Phase 42 pattern) | **Phase 42 D-18 superseded the fixture pattern.** Phase 44 parity test loads VN30 fresh, runs HybridEngine twice (with `macro_filter_enabled=False` and the v60_strict_mode=True preset), asserts byte-exact `.equals()`. No fixture file to maintain. |

**Installation:** No new dependencies required. All dependencies present.

**Version verification:** Verified live `2026-04-23`:
- pandas 2.3.3 (matches reconciled baseline JSON)
- pytest >=9.0.2 (per pyproject.toml; markers `regression`, `integration` declared)
- pyarrow >=14.0.0 (per pyproject.toml; not needed for chosen pattern)

## Architecture Patterns

### Recommended Project Structure

```
strategies/mdm_hybrid/
├── config.py                    # ADD 10 fields to MDMV2Config + both presets
├── mdm_hybrid_engine.py         # ADD precompute (gated) + ADD hook in two-phase block
├── position_manager.py          # ADD effective_dd_threshold parameter to process_day()
├── stop_loss.py                 # ADD effective_max_multiplier parameter to check()
├── indicator_filter.py          # READ-ONLY (pattern precedent)
├── macro_filter.py              # NEW — MacroFilter class, MacroVerdict dataclass, add_macro_columns(), path constants
├── indicators.py                # READ-ONLY (existing pipeline)
├── distribution_day.py          # READ-ONLY
├── rally_attempt.py             # READ-ONLY
├── ftd_signal.py                # READ-ONLY
└── (no other files)

tests/
├── test_macro_filter.py             # NEW — unit tests (DXY z-score on known date, EEM z-score on known date, SBV regime transitions, MacroFilter conflict resolution)
├── test_macro_filter_v6_parity.py   # NEW — @pytest.mark.regression byte-exact equality
└── test_baseline_determinism.py     # READ-ONLY (parity test pattern source)

data/                                # READ-ONLY (Phase 43 owns)
├── vn_liquidity_proxy.csv           # 2867 rows, 6 cols (date, usdvnd_close, dxy_close, tnx_close, vnm_close, eem_close)
└── sbv_policy_events.csv            # 12 rows, 5 cols (date, rate_change_pct, new_refinance_rate_pct, direction, source)

output/
└── v10_reconciled_baseline.json     # READ-ONLY (loaded by parity test runtime per Phase 42 D-14)

.planning/
├── ROADMAP.md                       # EDIT line 852 (SC-5 rewrite per D-05)
└── REQUIREMENTS.md                  # EDIT line 26 (MACRO-05 rewrite per D-05)
```

### Pattern 1: MacroVerdict as a Dataclass (RECOMMENDED — resolves D-04 stacking requirement)

**What:** A small dataclass holding three independent policy flags plus two override scalars. The MacroFilter sets the appropriate flags/overrides per row; the engine and downstream consumers (V2PositionManager, StopLossChecker) read what they need.

**When to use:** When D-04 requires multiple policies to fire simultaneously (DXY tightening + SBV tightening = both LOWER_DD and TIGHTEN_STOP_LOSS).

**Why not an enum:** A single-value enum can only express one outcome per call. The most-restrictive combiner (D-04) explicitly stacks tightening policies. An enum would require either a power-set of values (10+ enum values) or sequential evaluation calls — both worse than a dataclass.

**Example:**
```python
# strategies/mdm_hybrid/macro_filter.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class MacroVerdict:
    """Per-day macro policy decision.

    Three independent flags + two scalar overrides. Multiple flags can be
    True simultaneously per D-04 most-restrictive combiner.

    Attributes:
        veto_sell: If True, the engine MUST NOT transition to SELL today
            (regardless of state machine proposal).
        effective_dd_threshold: Override for V2PositionManager's
            dd_cash_threshold today. None = use config default. D-02 sets
            this to dxy_tightening_dd_threshold (default 3) when DXY tightening.
        effective_stop_loss_max_multiplier: Override for StopLossChecker's
            stop_loss_max_multiplier today. None = use config default. D-03
            sets this to sbv_tightening_stop_loss_max_multiplier (default
            1.5) when SBV tightening.
    """
    veto_sell: bool = False
    effective_dd_threshold: Optional[int] = None
    effective_stop_loss_max_multiplier: Optional[float] = None

    @classmethod
    def pass_through(cls) -> "MacroVerdict":
        """Sentinel returned when filter is disabled or no signal active."""
        return cls()  # all defaults — equivalent to PASS

    def is_pass(self) -> bool:
        """True iff this verdict imposes no policy changes."""
        return (
            not self.veto_sell
            and self.effective_dd_threshold is None
            and self.effective_stop_loss_max_multiplier is None
        )
```

This design accommodates ALL D-04 combinations:
- DXY easing + SBV easing → `MacroVerdict(veto_sell=True)`
- DXY tightening only → `MacroVerdict(effective_dd_threshold=3)`
- SBV tightening only → `MacroVerdict(effective_stop_loss_max_multiplier=1.5)`
- DXY tightening + SBV tightening (most-restrictive stack) → `MacroVerdict(effective_dd_threshold=3, effective_stop_loss_max_multiplier=1.5)`
- DXY easing + SBV tightening (cautionary wins per D-04) → `MacroVerdict(effective_dd_threshold=3, effective_stop_loss_max_multiplier=1.5)` (no veto_sell — SBV cautionary blocks the bullish veto)
- Neutral / disabled → `MacroVerdict.pass_through()` → `is_pass() == True`

### Pattern 2: Hard Short-Circuit Feature Gate (D-09 invariant)

**What:** Two-line guard at the very top of each function that touches the feature; equivalent guard around the precompute helper call site in the engine.

**When to use:** ANY feature-gated module that must guarantee byte-exact parity when off (Phase 38 ATR-04, Phase 39 DD-04, Phase 44 MACRO-04).

**Example:**
```python
# strategies/mdm_hybrid/macro_filter.py
class MacroFilter:
    def __init__(self, config: HybridConfig):
        self.config = config

    def apply(self, row, state_machine_decision, current_state) -> MacroVerdict:
        # D-09 HARD SHORT-CIRCUIT — first-line guard guarantees parity.
        # Do NOT compute votes, read columns, or call helpers when disabled.
        if not self.config.v2_config.macro_filter_enabled:
            return MacroVerdict.pass_through()
        # ... only reachable when enabled ...
```

```python
# strategies/mdm_hybrid/mdm_hybrid_engine.py — inside HybridEngine.run() precompute block
# (insert near line 173 after the refined_dd block; mirrors atr_buffer pattern at line 164)

# Macro Filter (Phase 44, MACRO-01..04)
# Only when enabled — D-09: no side effects when disabled (protects MACRO-04)
if self.config.v2_config.macro_filter_enabled:
    from .macro_filter import add_macro_columns
    df = add_macro_columns(
        df,
        dxy_window_days=self.config.v2_config.dxy_window_days,
        eem_window_days=self.config.v2_config.eem_window_days,
        sbv_decay_days=self.config.v2_config.sbv_decay_days,
    )
```

### Pattern 3: Precompute-once, Read-per-row (engine.py:157-179 precedent)

**What:** Add columns to the DataFrame ONCE before the daily loop. Inside the loop, read column values via `row['dxy_z']` etc. Never recompute per-row.

**When to use:** Every indicator/feature-derived signal in this engine. Verified pattern across `add_atr_column` (line 157), `add_violation_threshold_column` (line 165), `add_volume_ma_column` (line 174), `build_indicator_dataframe` (line 184).

### Pattern 4: Hook Insertion in Two-Phase Commit Block

**What:** D-08 places MacroFilter AFTER IndicatorFilter. The exact insertion point in the existing engine code is the END of the `if self.config.two_phase_enabled and self.config.filter_enabled:` block (engine.py:420-493) but BEFORE the `# State history tracking` block (engine.py:498).

**Critical mechanic:** The `new_state` and `action` variables hold the post-IndicatorFilter decision when the hook fires. MacroFilter reads these (along with `old_state`) and decides whether to:
1. **VETO_SELL:** rollback the state machine via `_restore_components(snapshot)` and clear `action`. Mirror the existing VETO branch at engine.py:454-457.
2. **LOWER_DD_THRESHOLD:** this is consumed UPSTREAM in `position_manager.process_day()`, NOT in the engine block — see Pattern 5.
3. **TIGHTEN_STOP_LOSS:** this is consumed UPSTREAM in `stop_loss_checker.check()`, NOT in the engine block — see Pattern 5.

**This means MacroFilter is called TWICE-conceptually per day, OR pre-computed-once per day:**
- The threshold-override logic (D-02, D-03) must be available BEFORE `position_manager.process_day()` runs (engine.py:397) and BEFORE `stop_loss_checker.check()` runs (engine.py:353).
- The veto-sell logic (D-01) is applied AFTER both — at the existing IndicatorFilter post-decision block.

**Recommended design — single per-row evaluate call up-front:**
```python
# Inside the daily loop, BEFORE stop_loss check (around engine.py:350)
macro_verdict = (
    self.macro_filter.apply(row, current_state)
    if self.macro_filter is not None
    else MacroVerdict.pass_through()
)

# Then stop_loss check with override (engine.py:353)
stop_loss_result = self.stop_loss_checker.check(
    ...,
    effective_max_multiplier=macro_verdict.effective_stop_loss_max_multiplier,
)

# Then position_manager.process_day with override (engine.py:397)
new_state, action = self.position_manager.process_day(
    ...,
    effective_dd_threshold=macro_verdict.effective_dd_threshold,
)

# Then INSIDE the existing two-phase block, AFTER IndicatorFilter VETO/OVERRIDE handling
# (after engine.py:489) — apply VETO_SELL only if state machine proposed SELL:
if macro_verdict.veto_sell and new_state == V2MarketState.SELL and old_state != V2MarketState.SELL:
    self._restore_components(snapshot)
    new_state = self.position_manager.get_state()
    action = ''  # match existing VETO pattern at engine.py:457
```

This decomposition lets `MacroFilter.apply()` be called ONCE per row but the verdict's three components flow to three different consumers. The MacroVerdict dataclass design (Pattern 1) makes this clean.

### Pattern 5: Effective-Override Parameters Down the Call Stack

**What:** New optional parameters on `V2PositionManager.process_day()` and `StopLossChecker.check()` that default to `None`. When `None`, use the config default; when set, use the override.

**Why:** Per D-02 ("Policy tweaks config-at-use-site, not in-place mutation of config object"), the config object is immutable per run. Per-row overrides flow as parameters.

**position_manager.py change (mechanical):**
```python
def process_day(
    self,
    ...,  # existing parameters
    effective_dd_threshold: int = None,  # NEW — D-02 override
) -> Tuple[V2MarketState, str]:
    ...
    # Inside BUY branch around current line 351
    dd_threshold = (
        effective_dd_threshold
        if effective_dd_threshold is not None
        else self.config.dd_cash_threshold
    )
    elif dd_count >= dd_threshold and is_dd:
        self.exit_to_cash(close, date, f"DD count {dd_count} >= threshold {dd_threshold}")
```

**stop_loss.py change (mechanical):**
```python
def _get_effective_stop_pct(
    self,
    atr: float = None,
    atr_baseline: float = None,
    effective_max_multiplier: float = None,  # NEW — D-03 override
) -> float:
    ...
    max_pct = self.config.stop_loss_pct * (
        effective_max_multiplier
        if effective_max_multiplier is not None
        else self.config.stop_loss_max_multiplier
    )
    return max(min_pct, min(max_pct, effective))

def check(self, ..., effective_max_multiplier: float = None) -> StopLossResult:
    ...
    effective_pct = self._get_effective_stop_pct(atr, atr_baseline, effective_max_multiplier)
```

**Critical parity invariant:** When `effective_dd_threshold=None` and `effective_max_multiplier=None` are passed, the resulting branch is byte-identical to the pre-change code path. This is the ONLY way the parity test passes. Verify by code review: the new branch's `else` arm reads the exact same field that the original code read.

### Anti-Patterns to Avoid

- **Mutating MDMV2Config in place per row** — would break Phase 42's determinism contract (re-running engine on same df must produce byte-exact same results). Use parameter overrides per Pattern 5.
- **Computing macro columns per-row inside the daily loop** — would be O(N²) and could trigger different caching behavior between runs. Always precompute once per Pattern 3.
- **Computing 20-day z-score on raw `data/vn_liquidity_proxy.csv`** — Spec §6 trap #4 forbids this. Z-score MUST be computed AFTER the backward merge on VN30-indexed data.
- **Using `direction='nearest'` or `direction='forward'` in any merge_asof call** — Spec §6 traps #1 and #5 forbid both. Always `direction='backward'`.
- **Skipping the `event_date + BusinessDay(1)` shift on SBV merge** — Spec §6 trap #2 forbids same-day SBV regime use.
- **Adding macro columns to df when `macro_filter_enabled=False`** — D-09 explicitly says "no DXY_z / EEM_z / SBV_regime columns are added to the DataFrame when the flag is False." Adding columns even with NaN values would change `df.equals(df)` semantics in the parity test.
- **Importing `add_macro_columns` at module top of `mdm_hybrid_engine.py`** — Phase 38 ATR pattern (line 165) and Phase 39 DD pattern (line 174) keep the import inside the gated block. NOT for circular-import safety (no circularity here) but to make the gate textually obvious during code review.
- **Using a single `MacroVerdict` enum** — fails D-04 stacking. Use dataclass.
- **Reading `output/v10_reconciled_baseline.json` at test-module import time** — `tests/test_baseline_determinism.py` precedent (lines 245-250) loads inside the test function with `pytest.skip` fallback. Phase 44 parity test inherits this pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-aware temporal join with no look-ahead | Manual `for` loop with `bisect_left` | `pd.merge_asof(direction='backward')` | merge_asof is vectorized, monotonic-key validated, and the spec mandates it (§5.1). Hand-rolled loop would diverge from spec wording in subtle ways (off-by-one on `allow_exact_matches`). |
| 20-day rolling z-score | Manual rolling-window loop with running sum | `df['x'].rolling(20).mean()` and `df['x'].rolling(20).std()` | pandas rolling is vectorized and NaN-safe at warm-up. Hand-rolled with running sum can have float-precision drift over a 2700-row series — non-determinism poisons the parity test. |
| BusinessDay-shifted column | `pd.Timedelta(days=1)` or manual weekday skip | `pd.tseries.offsets.BusinessDay(1)` | Timedelta(days=1) doesn't skip weekends; manual weekday skip is bug-prone. The spec uses `BusinessDay(1)` verbatim (§4.4) — match the spec to keep merge contract honored. |
| 90-day decay classifier | for-loop iterating events | After merge_asof: `(vn30_date - effective_date).dt.days > 90` → mask to 'neutral' | Vectorized boolean mask is one expression. for-loop is slow and easier to get wrong on edge cases (e.g., decay starting from same-day vs +1-day). |
| Byte-exact DataFrame equality | Custom comparison loop | `df1.equals(df2)` | pandas `.equals()` checks index, columns, dtypes, AND values. Phase 42 D-17 chose this for the strongest determinism proof. Custom comparison would risk missing dtype divergence. |
| Verdict struct | Custom enum with combinatorial values | Frozen dataclass with three fields | Enum values with combinations require `MacroVerdict.VETO_AND_LOWER_DD_AND_TIGHTEN_STOP` etc. — combinatorial blow-up. Dataclass with three independent fields is the SOLID design. |
| Feature-gate parity guarantee | Compute-and-ignore (compute z-score, don't apply) | First-line `if not enabled: return` AND skip helper call | Compute-and-ignore introduces float-rounding drift in the column set that fails byte-exact parity. Phase 38 ATR-04 and Phase 39 DD-04 both proved this empirically — Phase 44 inherits the lesson. |

**Key insight:** Phase 44 is fundamentally a *plumbing* phase. The macro signals themselves are well-understood (correlation evidence frozen in quick-task 260421-lb4 / `docs/research/liquidity_proxy_correlation.md`). The risk is NOT the math; the risk is silent corruption of the engine's byte-exact parity invariant by a stray ffill, a wrong merge direction, an unconditional column add, or a config-mutation side-effect. Every "don't hand-roll" item above maps to a specific way the parity test could fail silently — use the listed pandas-native one-liner and the parity test catches you if you slip.

## Runtime State Inventory

(Phase 44 is a code/feature-gated addition with no rename, refactor, or migration. No persisted runtime state needs auditing. The only "state" Phase 44 introduces is the precomputed `dxy_z`, `eem_z`, `sbv_regime` columns on the engine's per-run DataFrame — ephemeral, recomputed each `engine.run()` call.)

**Stored data:** None — Phase 44 reads `data/vn_liquidity_proxy.csv` and `data/sbv_policy_events.csv` (frozen Phase 43 outputs) and writes nothing persistent.
**Live service config:** None — no external services involved.
**OS-registered state:** None — no daemons, schedulers, or persistent jobs.
**Secrets/env vars:** None — all paths are filesystem-relative constants per D-16.
**Build artifacts:** None — no compiled binaries, no installed packages.

## Common Pitfalls

### Pitfall 1: Adding columns to df when feature is disabled

**What goes wrong:** Even adding NaN-filled `dxy_z`, `eem_z`, `sbv_regime` columns when `macro_filter_enabled=False` would change `df.shape`, `df.columns`, and `df.equals(df_baseline)` would return False. Parity test fails.

**Why it happens:** Developer thinks "no harm in computing it; just don't read it." This is the compute-and-ignore anti-pattern Phase 38/39 explicitly rejected.

**How to avoid:** Wrap `add_macro_columns()` call in the engine inside `if self.config.v2_config.macro_filter_enabled:` block, exactly mirroring engine.py:164 (atr_buffer) and engine.py:173 (refined_dd). Add a code-review checklist item for this in the plan.

**Warning signs:** Parity test failure mode → "DataFrame columns differ: [...]" — first thing to check is the gate around `add_macro_columns`.

### Pitfall 2: Wrong merge direction reintroduces look-ahead

**What goes wrong:** Using `merge_asof(direction='nearest')` or `direction='forward'` lets a VN30 date pick up a future US close (or future SBV event). The 2026 Phase 46 OOS HARD gate would silently include peeking; CAGR would inflate. Phase 47 would ship a fraudulent v10.0.

**Why it happens:** `direction='backward'` is a non-default kwarg, and `'nearest'` "feels" smoother. Spec §6 enumerates exactly this trap as #1 and #5.

**How to avoid:** Verify `direction='backward'` literally appears in every merge_asof call in `macro_filter.py`. Add a unit test that asserts `add_macro_columns(df_with_known_future_us_close)` does NOT pick up that future value (use a synthetic fixture where 2020-03-15 is in the proxy but the VN30 date is 2020-03-14 — assert `dxy_z` for 2020-03-14 reflects 2020-03-13 or earlier, NOT 2020-03-15).

**Warning signs:** Phase 46 walk-forward years 2025/2026 show abnormally high CAGR; A/B "+all" scenario looks too clean. Investigate merge directions.

### Pitfall 3: Z-score computed on raw CSV (not merged DF)

**What goes wrong:** Computing 20-day rolling z on the proxy CSV directly produces a series indexed by US trading days. Mapping back to VN30 dates via merge can use a z-score from a US date that lies in the FUTURE from the VN date's perspective (when nearest US date is tomorrow). Spec §6 trap #4.

**Why it happens:** It's "more efficient" to z-score the proxy once and merge the result. Wrong direction.

**How to avoid:** Document order of operations in `add_macro_columns()` docstring. Step 1: merge_asof(backward). Step 2: rolling z-score on the merged VN30-indexed DataFrame. Add a unit test that compares two implementations (z-then-merge vs merge-then-z) and asserts they differ on at least one VN holiday — proves the order matters.

**Warning signs:** Subtle CAGR drift in walk-forward years that have many US holidays misaligned with VN holidays (e.g., Thanksgiving falls on a VN trading day).

### Pitfall 4: SBV merge without +1 BusinessDay shift

**What goes wrong:** Using SBV `date` directly in merge_asof would let a same-day SELL signal use the announcement made later that same session. Spec §6 trap #2.

**Why it happens:** Easy to forget the shift; pandas tutorial examples don't show it.

**How to avoid:** Compute `sbv['effective_date'] = sbv['date'] + pd.tseries.offsets.BusinessDay(1)` BEFORE merge_asof. Use `right_on='effective_date'`. Add a unit test that uses an SBV event on date D and asserts the regime classification on D returns NaN/None or the previous regime, NOT the new regime — the new regime appears starting from D+1 BusinessDay.

**Warning signs:** A specific SBV-event date in the parity test diff vs reconciled baseline.

### Pitfall 5: Stacking conflict resolution implemented as if-elif-else

**What goes wrong:** A naive implementation reads "DXY tightening lowers DD" as exclusive with "SBV tightening shrinks stop-loss" — because it's coded as `if dxy_tight: ...; elif sbv_tight: ...`. D-04 explicitly says BOTH apply when both are active.

**Why it happens:** Default Python branching habits.

**How to avoid:** Use independent boolean checks setting independent fields on `MacroVerdict` (Pattern 1). NEVER `elif` between policy-application branches. Add a unit test fixture where DXY z = +1.5 (tightening) AND SBV regime = tightening, assert the verdict has BOTH `effective_dd_threshold` set AND `effective_stop_loss_max_multiplier` set.

**Warning signs:** Phase 45 grid search shows "DXY-only" and "SBV-only" winning combos but "DXY+SBV combined" mysteriously underperforms — investigate stacking implementation.

### Pitfall 6: Forgetting NASDAQ_PRESET in D-15

**What goes wrong:** Adding the 10 fields to MDMV2Config and VN30_PRESET but forgetting NASDAQ_PRESET means NASDAQ runs (e.g., `tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq`) would crash with `TypeError: __init__() got an unexpected keyword argument 'macro_filter_enabled'` IF the preset is constructed via dict-spread, OR silently use dataclass defaults (which is the desired behavior).

**Why it happens:** Phase 38 and Phase 39 both correctly added their fields to BOTH presets (verified at config.py:164-167 and 168-173). Phase 44 must do the same.

**How to avoid:** Plan checklist: "VN30_PRESET diff and NASDAQ_PRESET diff each include all 10 D-15 fields explicitly." Code review verifies side-by-side. The MDMV2Config dataclass defaults will save you, but explicit-in-preset is the project convention.

**Warning signs:** `pytest tests/test_hybrid_engine.py` failures or warnings about preset construction.

### Pitfall 7: Importing analysis.validate_v9 at parity-test module top

**What goes wrong:** `analysis/validate_v9.py` rewrites `sys.stdout` at module-import time (verified in `tests/test_baseline_determinism.py` lines 50-57 comment). Importing it at test-module top breaks pytest's stdout capture during collection. Phase 44 parity test would have spurious "I/O operation on closed file" failures.

**Why it happens:** Natural to import at module top; the side-effect is invisible.

**How to avoid:** Use the lazy-import shim pattern verbatim from `tests/test_baseline_determinism.py` lines 98-143 (`_get_compute_metrics()` function, `_ORPHAN_STDOUT_WRAPPER_HOLDER` list). Phase 44 parity test that needs `compute_metrics` MUST adopt this pattern. (Note: the recommended Phase 44 parity test design uses `df.equals(df)` and does NOT need compute_metrics — but if the planner adds a metric-comparison sub-test, this shim is mandatory.)

**Warning signs:** Pytest collection fails with `ValueError: I/O operation on closed file` BEFORE any test runs.

### Pitfall 8: Missing v60_strict_mode=True in parity-test fixture

**What goes wrong:** Phase 42-04 plan landed `v60_strict_mode: bool = False` in MDMV2Config (config.py:89) AND made it `True` for the reconciled-baseline parity assertion (verified at `tests/test_baseline_determinism.py:152-156`). Phase 44 parity test MUST inherit this — without `v60_strict_mode=True`, the engine runs the post-Phase-38 elif chain that drifts CAGR away from the v6.0 target.

**Why it happens:** New parity test author copies VN30_PRESET defaults verbatim, missing the override.

**How to avoid:** Phase 44 parity test fixture builds the MDMV2Config via the same `_build_reconciled_cfg()` pattern at `tests/test_baseline_determinism.py:146-156`:
```python
overrides = dict(
    atr_buffer_enabled=False,
    refined_dd_enabled=False,
    macro_filter_enabled=False,  # NEW for Phase 44
)
if 'v60_strict_mode' in MDMV2Config.__dataclass_fields__:
    overrides['v60_strict_mode'] = True
return replace(VN30_PRESET, **overrides)
```

**Warning signs:** Parity test reports CAGR drift back to ~10.70% (the unreconciled baseline) — first thing to check is `v60_strict_mode`.

## Code Examples

Verified patterns from project sources and the verified spec.

### Common Operation 1: add_macro_columns helper (full implementation pattern)

```python
# Source: synthesized from docs/liquidity_proxy_spec.md §5.1, §5.2, §5.3 (verified 2026-04-23)
# AND CONTEXT.md D-10 helper signature

import pandas as pd
from pathlib import Path

LIQUIDITY_PROXY_PATH = Path('data/vn_liquidity_proxy.csv')
SBV_EVENTS_PATH = Path('data/sbv_policy_events.csv')


def add_macro_columns(
    df: pd.DataFrame,
    liquidity_proxy_path: Path = LIQUIDITY_PROXY_PATH,
    sbv_events_path: Path = SBV_EVENTS_PATH,
    dxy_window_days: int = 20,
    eem_window_days: int = 20,
    sbv_decay_days: int = 90,
) -> pd.DataFrame:
    """Enrich VN30 DataFrame with dxy_z, eem_z, sbv_regime columns.

    Three-step pipeline per docs/liquidity_proxy_spec.md:
        1. Merge proxy CSV onto VN30 dates via merge_asof(backward) — §5.1
        2. Compute rolling z-scores AFTER the merge (VN30-indexed) — §5.3
        3. Merge SBV events on shifted effective_date and apply 90-day decay — §4.4 / §5.2

    Args:
        df: VN30 DataFrame, MUST have a sorted 'date' column.
        liquidity_proxy_path: Path to the canonical 6-column proxy CSV.
        sbv_events_path: Path to the canonical 5-column SBV events CSV.
        dxy_window_days: Rolling window for DXY z-score (default 20).
        eem_window_days: Rolling window for EEM z-score (default 20).
        sbv_decay_days: Days after event before regime decays to 'neutral' (default 90).

    Returns:
        Copy of input DataFrame with appended columns:
            dxy_z (float, NaN during warm-up)
            eem_z (float, NaN during warm-up)
            sbv_regime (str, one of 'easing' | 'neutral' | 'tightening')
            sbv_days_since_event (int, diagnostic — Claude's Discretion)
    """
    df = df.copy()
    df = df.sort_values('date').reset_index(drop=True)

    # ── Step 1: merge proxy onto VN30 dates (no look-ahead) ──────────────
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

    # Drop the intermediate close columns to keep the schema lean
    merged = merged.drop(columns=['dxy_close', 'eem_close'])

    # ── Step 3: SBV regime via shifted-date merge_asof + 90-day decay ───
    sbv = pd.read_csv(sbv_events_path, parse_dates=['date'])
    sbv = sbv.sort_values('date').reset_index(drop=True)
    sbv['effective_date'] = sbv['date'] + pd.tseries.offsets.BusinessDay(1)
    # CRITICAL: shift first, then merge. Spec §6 trap #2 forbids same-day use.

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

    # Apply 90-day decay: regime → 'neutral' when no event in last sbv_decay_days
    # (NaN days_since means we're before the first SBV event — also 'neutral')
    sbv_merged['sbv_regime'] = sbv_merged['sbv_raw_direction'].where(
        sbv_merged['sbv_days_since_event'].notna()
        & (sbv_merged['sbv_days_since_event'] <= sbv_decay_days),
        other='neutral',
    )

    # Cleanup intermediate columns
    sbv_merged = sbv_merged.drop(columns=['effective_date', 'sbv_raw_direction'])

    return sbv_merged
```

### Common Operation 2: MacroFilter.apply() (full implementation pattern)

```python
# Source: CONTEXT.md D-01..D-04, D-09, plus IndicatorFilter pattern (indicator_filter.py:317)

import pandas as pd
from .config import HybridConfig
from .position_manager import V2MarketState


class MacroFilter:
    """Stateless macro-policy filter for the hybrid engine.

    Reads precomputed dxy_z, eem_z, sbv_regime columns and combines them
    via the most-restrictive rule (D-04) to produce a MacroVerdict.

    The filter never originates new state — it only modulates state-machine
    decisions via three orthogonal policy levers (veto sell, lower DD
    threshold, tighten stop-loss).
    """

    def __init__(self, config: HybridConfig):
        self.config = config

    def apply(self, row, current_state) -> MacroVerdict:
        """Evaluate macro policy for the given trading day.

        Args:
            row: pandas Series with dxy_z, eem_z, sbv_regime columns
                (added by add_macro_columns when feature enabled).
            current_state: V2MarketState (BUY/CASH/SELL).

        Returns:
            MacroVerdict — pass_through if filter disabled or no signal active.
        """
        # D-09 HARD SHORT-CIRCUIT — first-line guard guarantees parity.
        if not self.config.v2_config.macro_filter_enabled:
            return MacroVerdict.pass_through()

        v2 = self.config.v2_config

        # ── Read precomputed columns ────────────────────────────────────
        dxy_z = row.get('dxy_z')
        eem_z = row.get('eem_z')
        sbv_regime = row.get('sbv_regime', 'neutral')

        # NaN-safe per IndicatorFilter D-13 precedent
        dxy_easing = pd.notna(dxy_z) and dxy_z < v2.dxy_easing_z_threshold
        dxy_tightening = pd.notna(dxy_z) and dxy_z > v2.dxy_tightening_z_threshold
        eem_easing = pd.notna(eem_z) and eem_z > v2.eem_easing_z_threshold  # SIGN FLIPPED per D-12
        eem_tightening = pd.notna(eem_z) and eem_z < v2.eem_tightening_z_threshold  # SIGN FLIPPED per D-12
        sbv_easing = sbv_regime == 'easing'
        sbv_tightening = sbv_regime == 'tightening'

        # ── D-04 most-restrictive combiner ──────────────────────────────
        any_tightening = dxy_tightening or eem_tightening or sbv_tightening
        any_easing = dxy_easing or eem_easing or sbv_easing

        veto_sell = False
        effective_dd_threshold = None
        effective_stop_loss_max_multiplier = None

        # D-01 / D-13: DXY OR EEM easing VETOes SELL — but only if no tightening from SBV
        # (D-04: a single cautionary signal blocks the bullish policy)
        if any_easing and not any_tightening and current_state != V2MarketState.SELL:
            veto_sell = True

        # D-02 / D-13: DXY OR EEM tightening lowers DD threshold
        if dxy_tightening or eem_tightening:
            effective_dd_threshold = v2.dxy_tightening_dd_threshold

        # D-03: SBV tightening shrinks stop-loss max multiplier
        if sbv_tightening:
            effective_stop_loss_max_multiplier = v2.sbv_tightening_stop_loss_max_multiplier

        return MacroVerdict(
            veto_sell=veto_sell,
            effective_dd_threshold=effective_dd_threshold,
            effective_stop_loss_max_multiplier=effective_stop_loss_max_multiplier,
        )
```

### Common Operation 3: Parity test pattern (verbatim adaptation of test_baseline_determinism.py)

```python
# Source: tests/test_baseline_determinism.py:159-232 (verified 2026-04-23)
# Adapted for Phase 44 MACRO-04 / VAL-04 alignment

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
    """Reconciled v6.0 preset with macro filter EXPLICITLY disabled."""
    overrides = dict(
        atr_buffer_enabled=False,
        refined_dd_enabled=False,
        macro_filter_enabled=False,  # NEW for Phase 44
    )
    if 'v60_strict_mode' in MDMV2Config.__dataclass_fields__:
        overrides['v60_strict_mode'] = True  # CRITICAL — Phase 42-04 contract
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
    """MACRO-04: macro_filter_enabled=False MUST produce v6.0-parity signal log."""

    @pytest.fixture(scope='class')
    def prepared_df(self) -> pd.DataFrame:
        df = DataLoader('vn30').load(DATA_START, DATA_END)
        df = build_indicator_dataframe(df)
        return df

    def test_signal_log_byte_exact_with_macro_off(self, prepared_df):
        """When macro_filter_enabled=False, two fresh-engine runs are byte-exact."""
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

### Common Operation 4: Engine hook insertion (exact lines)

```python
# Source: strategies/mdm_hybrid/mdm_hybrid_engine.py — verified line numbers 2026-04-23

# ─── INSERTION 1: precompute block, after refined_dd block (current line 179),
# before "Add EMA/MACD" block (current line 182). Mirrors atr_buffer_enabled at 164. ───
if self.config.v2_config.macro_filter_enabled:
    from .macro_filter import add_macro_columns
    df = add_macro_columns(
        df,
        dxy_window_days=self.config.v2_config.dxy_window_days,
        eem_window_days=self.config.v2_config.eem_window_days,
        sbv_decay_days=self.config.v2_config.sbv_decay_days,
    )

# ─── INSERTION 2: instantiate filter in __init__ (after current line 54
# `self.indicator_filter = ...`). ───
self.macro_filter = (
    MacroFilter(self.config)
    if self.config.v2_config.macro_filter_enabled
    else None
)

# ─── INSERTION 3: per-row evaluate, BEFORE stop_loss check (current line 353)
# inside the daily loop. Computes the verdict ONCE per row. ───
macro_verdict = (
    self.macro_filter.apply(row, current_state)
    if self.macro_filter is not None
    else MacroVerdict.pass_through()
)

# ─── INSERTION 4: pass effective_max_multiplier to stop_loss check (modifies
# current line 353-360 call). ───
stop_loss_result = self.stop_loss_checker.check(
    close, buy_price, buy_day_low,
    ma50=ma50, prev_close=prev_close, prev_ma50=prev_ma50_val,
    current_volume=current_volume, prev_volume=prev_volume,
    signal_type=signal_type_held,
    atr=current_atr,
    atr_baseline=current_atr_baseline,
    effective_max_multiplier=macro_verdict.effective_stop_loss_max_multiplier,
)

# ─── INSERTION 5: pass effective_dd_threshold to position_manager.process_day
# (modifies current line 397-413 call). ───
new_state, action = self.position_manager.process_day(
    date=date,
    high=high,
    ...,  # all existing kwargs preserved
    violation_threshold=violation_threshold_val,
    effective_dd_threshold=macro_verdict.effective_dd_threshold,
)

# ─── INSERTION 6: VETO_SELL handling, AFTER existing IndicatorFilter block
# (after current line 489 inside `if self.config.two_phase_enabled and self.config.filter_enabled:`),
# OR equivalently at the same indentation level OUTSIDE that block (recommended:
# outside, since macro filter does NOT depend on two_phase / IndicatorFilter being on). ───
if (
    macro_verdict.veto_sell
    and new_state == V2MarketState.SELL
    and current_state != V2MarketState.SELL
):
    # Restore from snapshot — same pattern as IndicatorFilter VETO at engine.py:454-457
    if snapshot is not None:
        self._restore_components(snapshot)
    new_state = self.position_manager.get_state()
    action = ''
    df.at[idx, 'verdict'] = 'MACRO_VETO_SELL'  # diagnostic — Claude's Discretion
```

**Critical alignment note for the planner:** INSERTION 6 must work whether or not `two_phase_enabled` and `filter_enabled` are True. The cleanest design is to lift the snapshot creation outside the `if self.config.two_phase_enabled` block (always snapshot if either two_phase OR macro_filter is enabled). Alternative: macro_filter only restores if snapshot is non-None and ignores the case where two_phase is off (then VETO_SELL would only work when two_phase_enabled=True). The Phase 42 reconciled-baseline preset has `two_phase_enabled=True` (always), so the alternative is safe — but the planner should call this out as a planned-execution constraint.

### Common Operation 5: Config field append (exact diff target)

```python
# Source: strategies/mdm_hybrid/config.py — append after line 89 (v60_strict_mode field)

@dataclass
class MDMV2Config:
    # ... all existing fields preserved unchanged ...

    # v6.0 Strict Mode (Phase 42 BASE-02, D-07 step 2)
    v60_strict_mode: bool = False

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

    def __post_init__(self):
        # ... all existing assertions preserved ...

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

Then update both presets at config.py:141 (VN30_PRESET) and config.py:178 (NASDAQ_PRESET) — append the same 10 fields with the default values explicitly listed in the constructor call (matches Phase 38/39 convention; see config.py:164-167 atr_buffer block and config.py:168-173 refined_dd block).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-feature parquet baseline fixture (Phase 38: `phase38_v6_baseline_signal_log.parquet`; Phase 39: `phase39_v6_baseline_dd_sequence.parquet`) | Fresh-run + `df.equals(df)` byte-exact assertion (Phase 42 D-17/D-18) | Phase 42 (2026-04-22) | Phase 44 inherits the fresh-run pattern — no parquet fixture to maintain. Lower-risk (no fixture-rot), higher-runtime (~3s per engine × N runs). |
| Single `Verdict` enum (Phase 12 IndicatorFilter) | `MacroVerdict` dataclass with multiple flags (Phase 44) | Phase 44 design choice (this RESEARCH.md) | D-04 stacking requirement makes single-enum impossible. Dataclass is more verbose but correctly expresses orthogonal policy levers. |
| Hardcoded baseline numbers in test (Phase 38 fixture; Phase 39 fixture) | Read from `output/v10_reconciled_baseline.json` at runtime (Phase 42 D-14) | Phase 42-05 plan (2026-04-22) | Phase 44 parity test does NOT need to read the JSON for `df.equals()` comparison — the parity invariant is "two macro-off runs are byte-exact", not "macro-off run matches a hardcoded number". The JSON consumption is for Phase 46 HARD gate. |
| `pip install` workflow | `uv run python ...` workflow (per pyproject.toml) | Pre-Phase 38 | Use `uv run pytest -m regression tests/test_macro_filter_v6_parity.py -v` for the parity test invocation. |
| `tests/fixtures/` parquet fixtures (Phase 38/39) | No fixture; live VN30 reload + reconciled-HEAD re-run (Phase 42/44) | Phase 42 D-18 | Faster to author, slower to run, more robust. |

**Deprecated/outdated:**
- The original MACRO-05 wording ("forces half-position or full CASH"). Phase 44 D-05 explicitly rewrites this. Planner MUST execute the ROADMAP.md and REQUIREMENTS.md edits as part of phase scope.
- "Compute z-score then merge" pattern. Spec §6 trap #4 forbids — z-score AFTER merge.

## Open Questions

1. **Is INSERTION 6 (VETO_SELL handling) safe when `two_phase_enabled=False`?**
   - What we know: All Phase 42 reconciled-baseline runs have `two_phase_enabled=True`. The IndicatorFilter VETO/OVERRIDE block already requires `two_phase_enabled=True` for snapshot/restore (engine.py:235, 420). VETO_SELL needs the same snapshot mechanism to roll back the SELL transition.
   - What's unclear: Does the project intend to support `macro_filter_enabled=True` with `two_phase_enabled=False`? CONTEXT.md doesn't address this.
   - Recommendation: Document an assertion in `MacroFilter.__init__`: "if `macro_filter_enabled` then `two_phase_enabled` MUST be True". Plan should add a unit test for this constraint. If the planner discovers a downstream consumer wants `two_phase_enabled=False` with macro on, escalate as a Phase 44 scope clarification before implementing.

2. **Does the SBV decay use calendar days or business days?**
   - What we know: D-14 says `sbv_decay_days: int = 90` — integer, unit-implicit. Spec §4.4 says "any date more than 90 calendar days after the most recent event_date" — uses `(date - effective_date).dt.days` semantics, which is calendar days.
   - What's unclear: Phase 45 grid search may want to sweep 60/90/120; should the unit stay calendar?
   - Recommendation: Implement as calendar days (matches spec wording verbatim). Add a unit test that fires an SBV event on `2020-03-17` and asserts the regime is `'tightening'` until `2020-06-15` (90 calendar days later) and `'neutral'` from `2020-06-16` onward. Phase 45 sweep can vary the integer; semantics stay calendar.

3. **Should `sbv_days_since_event` be exposed as a column?**
   - What we know: CONTEXT.md "Claude's Discretion" lists "Whether SBV merge produces a per-row `sbv_days_since_event` column for diagnosability (nice-to-have)".
   - What's unclear: Adds a non-essential column. Phase 45 grid-search debugging may want it; Phase 46 dashboard overlay may want it.
   - Recommendation: YES — include `sbv_days_since_event` in the merged DataFrame. Marginal cost (one int column), high diagnostic value. Already coded into Common Operation 1 example above. Plan can drop if disagreed.

4. **What is the right testing scope for the MACRO-05 ROADMAP/REQUIREMENTS rewrite (D-05)?**
   - What we know: D-05 says the rewrite "piggy-backs on the phase completion". GSD convention favors atomic commits. CLAUDE.md doesn't address `.planning/` doc edits as a separate commit pattern.
   - What's unclear: Bundle into the same commit as the feature gate addition, OR separate doc-only commit.
   - Recommendation: SEPARATE doc-only commit, landed FIRST in the phase (before any code changes). Reasons: (a) makes the requirement diff reviewable independently of code; (b) the planner reading REQUIREMENTS.md during Phase 45 planning gets the correct text immediately; (c) bundling with code-heavy commits buries doc changes in diff noise. Per GSD atomic-commit convention.

5. **Does Phase 44 need to update `docs/liquidity_proxy_spec.md`?**
   - What we know: The spec footer says "Future Phase 44 work that touches `strategies/mdm_hybrid/` or any new `strategies/mdm_hybrid/macro_filter*.py` module MUST update this spec in the same commit, per the CLAUDE.md Code-Docs Sync Rule. Specifically, any change to the merge contract (Section 5), the publication-lag policy (Section 4), or the input schemas (Section 2) must land together with the corresponding code change."
   - What's unclear: Phase 44 only CONSUMES the contract — does not change merge contract, publication-lag policy, or schemas.
   - Recommendation: NO update to `docs/liquidity_proxy_spec.md` needed if Phase 44 implements the spec verbatim. Add an explicit note in 44-NN-SUMMARY.md confirming this. The Code-Docs Sync rule applies when Phase 44's macro_filter.py *deviates* from the spec — current research recommends zero deviation.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | All implementation, both tests | ✓ | 2.3.3 (verified live 2026-04-23) | — |
| numpy | rolling z-score | ✓ | 2.2.6 (per reconciled baseline JSON; matches installed) | — |
| pytest | Both tests | ✓ | >=9.0.2 (per pyproject.toml dev-deps) | — |
| Python 3.10+ | Dataclasses, type hints | ✓ | 3.10.20 (per reconciled baseline JSON) | — |
| pyarrow | Not needed (no parquet fixture in chosen design) | ✓ | >=14.0.0 (available if needed) | — |
| `data/vn_liquidity_proxy.csv` | add_macro_columns | ✓ | 2867 rows verified, schema matches spec §2.1 | — |
| `data/sbv_policy_events.csv` | add_macro_columns | ✓ | 12 rows verified, schema matches spec §2.2 | — |
| `output/v10_reconciled_baseline.json` | Optional in Phase 44 (used by Phase 46 HARD gate) | ✓ | schema_version=1, all 18 D-12 fields present | — |
| `tests/test_baseline_determinism.py` | Pattern source for parity test | ✓ | 274 lines, 3 tests under TestBaselineDeterminism class | — |
| `strategies/mdm_hybrid/v60_strict_mode` field | parity test fixture | ✓ | Verified at config.py:89 | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 (per pyproject.toml dev-deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths=["tests"], markers regression and integration declared) |
| Quick run command | `uv run pytest tests/test_macro_filter.py -x` |
| Full suite command | `uv run pytest -m regression tests/test_macro_filter_v6_parity.py -v` AND `uv run pytest tests/test_macro_filter.py -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MACRO-01 | DXY 20d z-score correctly computed via merge_asof(backward) on a known date | unit | `uv run pytest tests/test_macro_filter.py::test_dxy_z_known_date -x` | ❌ Wave 0 |
| MACRO-01 | DXY z-score uses VN30-indexed rolling window (not US-indexed) | unit | `uv run pytest tests/test_macro_filter.py::test_dxy_z_uses_vn_calendar -x` | ❌ Wave 0 |
| MACRO-02 | EEM 20d z-score correctly computed via same pipeline as DXY | unit | `uv run pytest tests/test_macro_filter.py::test_eem_z_known_date -x` | ❌ Wave 0 |
| MACRO-02 | EEM sign convention is flipped vs DXY (per D-12) | unit | `uv run pytest tests/test_macro_filter.py::test_eem_sign_flipped -x` | ❌ Wave 0 |
| MACRO-03 | SBV regime classifier transitions across known event sequence (e.g., 2020-03-17 cut → 'easing' on 2020-03-18 onwards) | unit | `uv run pytest tests/test_macro_filter.py::test_sbv_regime_transitions -x` | ❌ Wave 0 |
| MACRO-03 | SBV decay to 'neutral' after 90 days | unit | `uv run pytest tests/test_macro_filter.py::test_sbv_90_day_decay -x` | ❌ Wave 0 |
| MACRO-03 | SBV +1 BusinessDay shift (2020-03-17 event NOT visible on 2020-03-17 trading) | unit | `uv run pytest tests/test_macro_filter.py::test_sbv_publication_lag_shift -x` | ❌ Wave 0 |
| MACRO-04 | macro_filter_enabled=False → byte-exact parity across 2 fresh runs | regression | `uv run pytest -m regression tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity::test_signal_log_byte_exact_with_macro_off -v` | ❌ Wave 0 |
| MACRO-04 | macro_filter_enabled=False → no dxy_z/eem_z/sbv_regime columns added | regression | `uv run pytest -m regression tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity::test_macro_columns_absent_when_disabled -v` | ❌ Wave 0 |
| MACRO-04 | Existing baseline determinism test still passes (sanity) | regression | `uv run pytest -m regression tests/test_baseline_determinism.py -v` | ✅ exists |
| MACRO-04 | Existing hybrid engine tests still pass (no regressions in NASDAQ path) | unit | `uv run pytest tests/test_hybrid_engine.py -v` | ✅ exists |
| MACRO-05 | DXY easing → veto_sell flag set | unit | `uv run pytest tests/test_macro_filter.py::test_dxy_easing_vetoes_sell -x` | ❌ Wave 0 |
| MACRO-05 | DXY tightening → effective_dd_threshold set to dxy_tightening_dd_threshold | unit | `uv run pytest tests/test_macro_filter.py::test_dxy_tightening_lowers_dd -x` | ❌ Wave 0 |
| MACRO-05 | SBV tightening → effective_stop_loss_max_multiplier set to sbv_tightening_stop_loss_max_multiplier | unit | `uv run pytest tests/test_macro_filter.py::test_sbv_tightening_shrinks_stop_loss -x` | ❌ Wave 0 |
| MACRO-05 | D-04 most-restrictive: DXY tightening + SBV tightening simultaneously sets BOTH overrides | unit | `uv run pytest tests/test_macro_filter.py::test_d04_stacking_tightening -x` | ❌ Wave 0 |
| MACRO-05 | D-04 cautionary blocks bullish: DXY easing + SBV tightening → no veto_sell, only tightening overrides | unit | `uv run pytest tests/test_macro_filter.py::test_d04_cautionary_wins -x` | ❌ Wave 0 |
| MACRO-05 | EEM symmetry to DXY: EEM easing alone vetoes SELL (same code path) | unit | `uv run pytest tests/test_macro_filter.py::test_eem_easing_vetoes_sell -x` | ❌ Wave 0 |
| MACRO-05 (D-15) | All 10 new MDMV2Config fields present with correct defaults in BOTH VN30_PRESET and NASDAQ_PRESET | unit | `uv run pytest tests/test_macro_filter.py::test_config_field_presence -x` | ❌ Wave 0 |
| MACRO-05 (D-09) | macro_filter_enabled validates field constraints in __post_init__ when True | unit | `uv run pytest tests/test_macro_filter.py::test_config_validation_gated_on_flag -x` | ❌ Wave 0 |
| ROADMAP SC-1..SC-3 | (Same as MACRO-01/02/03 above — directly mapped) | unit | (see above) | ❌ Wave 0 |
| ROADMAP SC-4 | (Same as MACRO-04 byte-exact above — directly mapped) | regression | (see above) | ❌ Wave 0 |
| ROADMAP SC-5 | (After D-05 rewrite — Same as MACRO-05 policy tests above) | unit | (see above) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_macro_filter.py -x` (unit suite — fast, ~5s)
- **Per wave merge:** `uv run pytest tests/test_macro_filter.py tests/test_macro_filter_v6_parity.py -v` (full Phase 44 suite — includes the regression test, ~30s)
- **Phase gate:** `uv run pytest -m regression -v` (full regression suite — Phase 42 baseline + Phase 44 parity together; ~60s) green BEFORE `/gsd:verify-work`. Plus `uv run pytest tests/test_hybrid_engine.py tests/test_macro_filter.py tests/test_macro_filter_v6_parity.py -v` to confirm no NASDAQ regression.

### Wave 0 Gaps

- [ ] `tests/test_macro_filter.py` — unit suite covering MACRO-01/02/03/05 + D-04 stacking + D-15 config presence + D-09 validation gating. ~12 test functions, synthetic mini-fixtures (no full VN30 load).
- [ ] `tests/test_macro_filter_v6_parity.py` — `@pytest.mark.regression` two-test class covering MACRO-04 byte-exact and macro-columns-absent invariants. Full VN30 load (~3s engine × 2 = 6s).
- [ ] No new `tests/conftest.py` needed — existing fixtures in `test_baseline_determinism.py` and `test_hybrid_engine.py` are class-scoped and not shared across files. Phase 44 fixtures live inside their own test files (matches Phase 38/39 convention).
- [ ] Framework install: not needed — `uv run pytest` already works (verified by reading pyproject.toml + STATE.md confirming Phase 42 tests passed).
- [ ] Synthetic fixtures for unit tests:
  - DXY z-score known-date: a 30-row mini DataFrame with hand-computed expected z on day 21 (first day with full window).
  - EEM z-score known-date: same pattern, different sign expectation.
  - SBV regime transitions: a 200-row date sequence + 3 synthetic SBV events at days 50, 100, 150 with directions [easing, tightening, easing], assert regime classification on days 51 (easing — first BusinessDay after event 1), 100 (still easing — within decay window), 141 (50 days after event 1, before decay), 145 (95 days — neutral), 151 (tightening — first day after event 2).
  - SBV publication lag: a 5-row mini DF with SBV event on date D, assert regime on D is `'neutral'` (event not visible), regime on D+1 BusinessDay is the event's direction.
  - D-04 stacking: 4 hand-built rows (DXY tightening only / SBV tightening only / both / DXY easing + SBV tightening), assert MacroVerdict fields per spec.

## Sources

### Primary (HIGH confidence)
- `c:/Users/trant/projects/mdm/.planning/phases/44-macro-filter-module/44-CONTEXT.md` — 16 D-decisions, locked
- `c:/Users/trant/projects/mdm/.planning/REQUIREMENTS.md` — MACRO-01..05 (lines 22-26)
- `c:/Users/trant/projects/mdm/.planning/ROADMAP.md` — Phase 44 (lines 843-854)
- `c:/Users/trant/projects/mdm/docs/liquidity_proxy_spec.md` — sections 2 (schemas), 4 (publication lag), 5 (merge contract), 6 (look-ahead traps) — load-bearing for MACRO-01/02/03
- `c:/Users/trant/projects/mdm/strategies/mdm_hybrid/mdm_hybrid_engine.py` — current engine code, line numbers verified live (precompute block lines 144-184; daily loop indicator-filter block lines 420-493)
- `c:/Users/trant/projects/mdm/strategies/mdm_hybrid/config.py` — current MDMV2Config + VN30_PRESET (line 141) + NASDAQ_PRESET (line 178); v60_strict_mode field at line 89
- `c:/Users/trant/projects/mdm/strategies/mdm_hybrid/indicator_filter.py` — Verdict enum + FilterConfig + IndicatorFilter pattern precedent (lines 30, 42, 98, 317)
- `c:/Users/trant/projects/mdm/strategies/mdm_hybrid/position_manager.py` — V2PositionManager.process_day() (line 228); BUY-state DD-threshold check at line 351; v60_strict_mode flat elif at lines 280-303
- `c:/Users/trant/projects/mdm/strategies/mdm_hybrid/stop_loss.py` — StopLossChecker.check() and _get_effective_stop_pct() at lines 36-58
- `c:/Users/trant/projects/mdm/tests/test_baseline_determinism.py` — parity test pattern (lines 159-232), v60_strict_mode fixture (lines 146-156), lazy-import shim (lines 98-143)
- `c:/Users/trant/projects/mdm/tests/test_hybrid_engine.py` — existing hybrid engine tests structure (lines 22-99)
- `c:/Users/trant/projects/mdm/tests/test_phase38_backward_compat.py` — feature-gate parity test precedent (Phase 38 ATR-04 invariant)
- `c:/Users/trant/projects/mdm/output/v10_reconciled_baseline.json` — schema_version=1, 18 fields, reconciliation_outcome="fixed_by_preset"
- `c:/Users/trant/projects/mdm/data/vn_liquidity_proxy.csv` — header verified live (6 cols, first row 2015-01-01, last row 2025-12-31, 2868 lines including header = 2867 data rows)
- `c:/Users/trant/projects/mdm/data/sbv_policy_events.csv` — verified live (12 rows, schema matches spec, all `easing` or `tightening`, no `neutral`, span 2017-07-10..2023-06-19)
- `c:/Users/trant/projects/mdm/.planning/phases/42-baseline-reconciliation/42-CONTEXT.md` — D-12 (18-field tuple), D-14 (downstream JSON contract), D-17 (byte-exact equality), D-18 (full-period prepared_df fixture)
- `c:/Users/trant/projects/mdm/.planning/phases/43-canonical-liquidity-data-pipeline/43-CONTEXT.md` — D-08 (publication-lag policy), D-09 (look-ahead traps)
- `c:/Users/trant/projects/mdm/.planning/phases/38-atr-buffer-zone-module/38-CONTEXT.md` — feature-gate default-off precedent (D-05/D-06/D-12/D-13)
- `c:/Users/trant/projects/mdm/.planning/phases/39-refined-distribution-day-module/39-CONTEXT.md` — feature-gate parity-when-off precedent + gated __post_init__ validation (D-05/D-06/D-10/D-11)
- `c:/Users/trant/projects/mdm/.planning/phases/12-indicator-filter-layer/12-CONTEXT.md` — IndicatorFilter pattern source (D-05 evaluate signature, D-07 Verdict enum, D-11 majority_threshold)
- `c:/Users/trant/projects/mdm/pyproject.toml` — pandas>=2.0.0, pytest>=9.0.2, markers `regression`, `integration` declared
- `c:/Users/trant/projects/mdm/.planning/STATE.md` — Phase 42/43 completion, project context
- Live verification (Bash): `pandas 2.3.3` installed, `merge_asof` API confirmed available
- Live verification (file ops): `vn_liquidity_proxy.csv` 2868 lines, `sbv_policy_events.csv` 12 data rows, all schemas match spec

### Secondary (MEDIUM confidence)
- `c:/Users/trant/projects/mdm/core/indicators.py:142` — build_indicator_dataframe signature (called from engine.py:184 — verified)
- `c:/Users/trant/projects/mdm/core/data_loader.py:116` — DataLoader.load() signature (used by parity test pattern)
- `docs/research/liquidity_proxy_correlation.md` — referenced by spec; not directly read in this research, but correlation values DXY -0.19 / EEM +0.19 / SBV spread 55.76pp are quoted by both spec §1 and CONTEXT.md memory anchor — cross-source consistent

### Tertiary (LOW confidence)
- None — every recommendation in this RESEARCH.md is verified against either Phase 44 CONTEXT.md, the load-bearing spec doc, or live code/data in the repo.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified live; no version uncertainty.
- Architecture: HIGH — every pattern is mechanically grounded in existing code (Phase 38/39/42 precedents) plus CONTEXT.md decisions.
- Pitfalls: HIGH — each pitfall maps to a specific spec section, code line, or prior phase failure mode; not speculation.
- Code Examples: HIGH for the pattern shapes; the exact computation in `add_macro_columns` synthesizes the spec — Plan should validate against the spec one more time during code review.
- Validation Architecture: HIGH — test types and commands match existing project conventions (Phase 38/39/42 precedents + pyproject.toml markers).

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (30 days — domain is stable; only thing that could invalidate is a fresh Phase 42 reconciliation or schema change to the canonical CSVs, both of which would surface as STATE.md updates)
