# Phase 44: Macro Filter Module - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 44-macro-filter-module
**Areas discussed:** Filter policy mechanics, Position sizing, Module placement & integration point, Config surface for grid search
**Language:** English questions initially; switched to Vietnamese from Q2 of Area 1 onward per user preference.

---

## Area 1 — Filter policy mechanics

### Q1: When DXY is in 'easing' regime AND the state machine proposes SELL, what should MacroFilter do?

| Option | Description | Selected |
|--------|-------------|----------|
| VETO the SELL | Block the SELL transition entirely; keep current state. Parallels IndicatorFilter.Verdict.VETO. | ✓ |
| DELAY: require N-day confirmation | Only fire SELL if proposed on 2+ consecutive days. Adds pending_sell counter state. | |
| DAMPEN: raise DD threshold | Increase required DD count (5 → 7) while easing active. More invasive. | |

**User's choice:** VETO the SELL
**Notes:** Mirrors existing IndicatorFilter abstraction exactly; smallest blast radius.

### Q2: When DXY is in 'tightening' regime AND no SELL proposal is active, what does 'amplify SELL' mean mechanically?

| Option | Description | Selected |
|--------|-------------|----------|
| Hạ ngưỡng DD | Lower required DD count (5 → 3) while tightening active. Keeps policy inside state machine. | ✓ |
| SELL đón đầu | Pre-emptive SELL if price below MA50 AND tightening active, no DD count needed. | |
| Rút ngắn cash_deterioration_days | Speed BUY→CASH degradation without forcing SELL. | |

**User's choice:** Hạ ngưỡng DD
**Notes:** Symmetric to Q1's VETO (active→passive direction). User follow-up: field name `dxy_tightening_dd_threshold: int = 3` (see follow-up F2).

### Q3: When SBV regime is 'tightening' AND current position is BUY/HOLD, what should MacroFilter do?

| Option | Description | Selected |
|--------|-------------|----------|
| Full CASH (binary) | Transition to CASH on SBV tightening regime transition. | |
| Nửa vị thế (sizing mới) | Reduce to 50% exposure via new Position.size scalar. | |
| Siết stop-loss multiplier | Reduce stop_loss_max_multiplier (2.5 → 1.5) so existing positions bail earlier. | ✓ |

**User's choice:** Siết stop-loss multiplier
**Notes:** User picked passive policy over aggressive CASH exit. Deviation from ROADMAP MACRO-05 — triggered follow-up F1 (decide how to reconcile the deviation).

### Q4: When DXY and SBV signals disagree, which wins?

| Option | Description | Selected |
|--------|-------------|----------|
| Most-restrictive wins | If EITHER is cautionary, act cautionary. Only BOTH-easing yields full easing policy. | ✓ |
| SBV wins | Rate policy is longer-horizon and more authoritative. | |
| DXY wins | DXY closer to real-time market liquidity. | |

**User's choice:** Most-restrictive wins
**Notes:** Conservative combiner. Reinforces D-01/D-02/D-03 by making any single cautionary signal activate tightening policies.

### Follow-up F1: How to handle Q3 deviation from MACRO-05

| Option | Description | Selected |
|--------|-------------|----------|
| Cập nhật MACRO-05 sang stop-loss | Rewrite ROADMAP / REQUIREMENTS.md to reflect stop-loss approach. | ✓ |
| Hai tầng: stop-loss + escalation | Stop-loss first; escalate to CASH if position survives N days. | |
| Giữ spec hiện tại làm target xa | Ship stop-loss now; leave CASH-exit as Phase 45/46 grid unlock. | |

**User's choice:** Cập nhật MACRO-05 sang stop-loss
**Notes:** User committed to binary engine + stop-loss tightening. ROADMAP + REQUIREMENTS.md update bundled into Phase 44 scope per D-05.

### Follow-up F2: DD threshold config exposure

| Option | Description | Selected |
|--------|-------------|----------|
| Config field mới | `dxy_tightening_dd_threshold: int = 3` on MDMV2Config. Phase 45 grid-searches. | ✓ |
| Hardcode 3 (quyước cố định) | Don't expose; simpler grid. | |
| Tỷ lệ của dd_cash_threshold | `dd_cash_threshold * 0.6` dynamically. | |

**User's choice:** Config field mới
**Notes:** Opens grid search surface for Phase 45. Evidence-backed default (3) but tunable.

---

## Area 2 — Position sizing (half vs full CASH)

**Resolved indirectly** — no questions needed.

Q3 of Area 1 rejected "Nửa vị thế (sizing mới)" and "Full CASH (binary)", picking stop-loss tightening instead. This implicitly resolves Area 2: engine remains binary CASH/BUY/SELL, no `Position.size` scalar, no half-position state. Captured as D-06 in CONTEXT.md.

**Deferred to v11+:** Fractional position sizing considered — revisit only if v10.0 passes HARD gate AND walk-forward suggests fractional sizing would improve OOS.

---

## Area 3 — Module placement & integration point

### Q1: Which file/module contains MacroFilter?

| Option | Description | Selected |
|--------|-------------|----------|
| `strategies/mdm_hybrid/macro_filter.py` (NEW) | Parallel to indicator_filter.py. New class + config dataclass. | ✓ |
| Extend existing indicator_filter.py | Fold macro into indicator_filter.py. | |
| `core/macro_filter.py` | Cross-cutting concern in core/. | |

**User's choice:** New file `strategies/mdm_hybrid/macro_filter.py`
**Notes:** Parallels IndicatorFilter precedent. Macro and indicator concerns are distinct.

### Q2: Where does MacroFilter hook into HybridEngine.run()?

| Option | Description | Selected |
|--------|-------------|----------|
| Sau IndicatorFilter, trước apply action | process_day → IndicatorFilter → MacroFilter → apply. Outer overrule layer. | ✓ |
| Trước IndicatorFilter | process_day → MacroFilter → IndicatorFilter → apply. Macro filters early. | |
| Pre-step: tweak config trước process_day | MacroFilter tweaks config, state machine runs with mutated values. | |

**User's choice:** After IndicatorFilter, before apply action
**Notes:** Macro regime overrules local indicator consensus in conflict. Reverse ordering would let majority-vote indicator logic override a clear macro signal.

### Q3: When `macro_filter_enabled=False`, what parity mechanism?

| Option | Description | Selected |
|--------|-------------|----------|
| Hard short-circuit | `if not enabled: return` first-line. No compute, no enrich. | ✓ |
| Compute-then-ignore | Compute z-scores / regime but don't apply policy. | |
| Fork engine loop | Separate `_run_macro_off()` vs `_run_macro_on()` methods. | |

**User's choice:** Hard short-circuit
**Notes:** Zero drift risk; matches Phase 38/39 feature-gate precedent.

### Q4: When are DXY_z / EEM_z / SBV_regime columns computed?

| Option | Description | Selected |
|--------|-------------|----------|
| Precompute trước engine.run() | Enrich DataFrame once. Engine reads precomputed columns. | ✓ |
| Lazy per-step in MacroFilter.apply() | Compute rolling z-score each day. Look-ahead risk. | |
| Helper module `core/macro_indicators.py` | Separate reusable module. | |

**User's choice:** Precompute before engine.run()
**Notes:** Matches `core.indicators.build_indicator_dataframe` precedent. Cheaper for Phase 45 grid search (re-use precomputed columns across config variants).

---

## Area 4 — Config surface for Phase 45 grid search

### Q1: DXY z-score threshold — symmetric or asymmetric?

| Option | Description | Selected |
|--------|-------------|----------|
| Bất đối xứng: 2 fields | `dxy_easing_z_threshold` + `dxy_tightening_z_threshold`. | ✓ |
| Đối xứng: 1 field | Single `dxy_z_threshold`; easing at `-threshold`, tightening at `+threshold`. | |

**User's choice:** Asymmetric (2 fields)
**Notes:** Allows easing bands wider than tightening in VN context.

### Q2: EEM thresholds — shared with DXY or separate?

| Option | Description | Selected |
|--------|-------------|----------|
| Threshold riêng cho EEM | `eem_easing_z_threshold` + `eem_tightening_z_threshold`. | ✓ |
| Dùng chung với DXY | Single threshold for both. | |
| Bỏ EEM, chỉ dùng DXY | Drop EEM from the filter. | |

**User's choice:** Separate EEM thresholds
**Notes:** EEM has positive correlation with VN30 (+0.19) while DXY is negative (-0.19). Separate fields allow the grid to honor the sign asymmetry.

### Q3: Window lengths (DXY / EEM / SBV decay) — what to expose?

| Option | Description | Selected |
|--------|-------------|----------|
| Expose all | `dxy_window_days`, `eem_window_days`, `sbv_decay_days` as config. | ✓ |
| Hardcode 20/20/90 | Fixed values; no grid surface. | |
| Expose SBV decay only | DXY/EEM hardcoded; SBV tunable. | |

**User's choice:** Expose all three
**Notes:** Phase 45 grid-searches all windows alongside thresholds. Defaults locked to quick-task evidence (20 / 20 / 90).

### Q4: Mandatory MDMV2Config fields — pick all that apply (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| macro_filter_enabled: bool = False | Feature gate. | ✓ |
| dxy_tightening_dd_threshold: int = 3 | From F2 of Area 1. | |
| sbv_tightening_stop_loss_max_multiplier: float = 1.5 | From F1 of Area 1 (MACRO-05 rewrite). | |
| macro_liquidity_proxy_path + macro_sbv_events_path | CSV path overrides. | |

**User's choice:** macro_filter_enabled (only)
**Notes:** Interpreted charitably — dxy_tightening_dd_threshold and sbv_tightening_stop_loss_max_multiplier are already committed by F2/F1 earlier in the discussion, so user selecting only the feature gate confirms those are in-scope but not a *new* choice here. Path fields (CSV overrides) excluded — resolved via Follow-up F3 below (hardcode).

### Follow-up F3: EEM policy role

| Option | Description | Selected |
|--------|-------------|----------|
| Đối xứng với DXY: VETO SELL khi easing, hạ DD khi tightening | EEM follows identical policy as DXY, differs only in sign convention. | ✓ |
| EEM chỉ là signal củng cố (confirmation) | EEM reinforces DXY's decision, doesn't independently VETO/amplify. | |
| Combine vào 'liquidity regime' duy nhất | Compose DXY_z and EEM_z into single score. | |

**User's choice:** Symmetric with DXY
**Notes:** Two independent code paths for DXY and EEM — shared MacroFilter.apply() body differing only in threshold field lookup. Grid-searchable independently.

### Follow-up F4: CSV paths — hardcode or config?

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcode constants in macro_filter.py | `LIQUIDITY_PROXY_PATH = Path('data/vn_liquidity_proxy.csv')`, etc. | ✓ |
| Config field on MDMV2Config | `macro_liquidity_proxy_path`, etc. | |
| Argument to add_macro_columns() | Helper accepts paths as parameters. | |

**User's choice:** Hardcode constants
**Notes:** Phase 43 froze paths; no runtime override needed outside test fixtures (which can still pass overrides via the `add_macro_columns` helper arguments).

---

## Claude's Discretion

Areas where user deferred to Claude:

- `MacroVerdict` enum design (single enum vs. combination struct) — must support combining VETO_SELL + LOWER_DD + TIGHTEN_STOP_LOSS since D-04 allows multiple simultaneous tightening policies
- `add_macro_columns()` column naming (suggestion: `dxy_z`, `eem_z`, `sbv_regime`)
- Whether to emit `sbv_days_since_event` diagnosability column
- Unit test data strategy (synthetic mini-fixtures vs. full VN30 load; parity/integration test uses full VN30 per Phase 42 D-18)
- Specific filenames: `tests/test_macro_filter.py`, `tests/test_macro_filter_v6_parity.py` (suggested)
- Commit timing for MACRO-05 REQUIREMENTS.md edit (bundle with feature-gate addition or separate doc commit; planner decides per GSD atomic-commit convention)

## Deferred Ideas

Captured in CONTEXT.md `<deferred>` — summary:

- Fractional position sizing — v11+ if v10 HARD gate passes and walk-forward suggests sizing helps
- Combined liquidity score (DXY+EEM) — revisit if Phase 45 finds them always in sync
- CSV paths as config — revisit if tests need synthetic injection
- "Forces CASH" SBV behavior — revisit if v10.0 fails HARD gate due to SBV-tightening position bleed
- Auto-append SBV events (AUTO-02) — v2 scope
- Statistical Jump Model / vol targeting / foreign flow (ALPHA-01..03) — v11+
