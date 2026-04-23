---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: VN Macro Filter + Baseline Reconciliation
status: executing
stopped_at: Completed 45-01-walkforward-grid-script-PLAN.md (analysis/walkforward_grid.py 685 lines, 5 commits 6ccb5cb..9180905)
last_updated: "2026-04-23T08:37:10.133Z"
last_activity: 2026-04-23
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 9
  completed_plans: 9
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** Discover MDM rules + apply on Vietnamese market — current focus: reduce v6.0 HybridEngine MaxDD from -28.6% to < -20% via VN-native macro filter (DXY/EEM/SBV regime), after reconciling baseline drift (shipped 11.5% → measured 10.70%).
**Current focus:** Phase 45 — walk-forward-grid-search

## Current Position

Phase: 45 (walk-forward-grid-search) — EXECUTING
Plan: 2 of 3
Status: Ready to execute
Last activity: 2026-04-23

Progress: [░░░░░░░░░░] 0% (v10.0: 0/6 phases complete)

## v10.0 Phase Plan

| # | Phase | Requirements | Gate |
|---|-------|--------------|------|
| 42 | Baseline Reconciliation | BASE-01, BASE-02, BASE-03 | Drift explained + reconciled baseline locked |
| 43 | Canonical Liquidity Data Pipeline | LIQ-01, LIQ-02, LIQ-03 | Regenerable CSVs + publication-lag spec |
| 44 | Macro Filter Module | MACRO-01..05 | v6.0 parity when off (VAL-04 alignment) |
| 45 | Walk-Forward Grid Search | WF-01, WF-02, WF-03 | Median degradation < 30% inside the sweep |
| 46 | A/B + OOS Validation (HARD Gate) | VAL-01..05 | MaxDD < -20% AND CAGR ≥ reconciled baseline |
| 47 | Docs & Dashboard | DOC-01, DOC-02, DOC-03 | Conditional branch on Phase 46 verdict |

## Accumulated Context

### Dependency ordering (explicit user guidance)

- BASE (Phase 42) must come first — "not fix baseline thì tối ưu trên cái drift"
- LIQ (Phase 43) after BASE, before MACRO
- MACRO (Phase 44) before WF (grid-search the module's thresholds)
- WF (Phase 45) before VAL (validation needs grid-searched params)
- DOC (Phase 47) conditional on VAL-02 HARD gate: pass → ship v10 docs + dashboard; fail → retain v6.0, publish rejection audit only

### HARD gate (milestone acceptance)

All three must hold simultaneously for v10.0 acceptance:

1. OOS (2025-2026) MaxDD < -20%
2. OOS CAGR ≥ reconciled baseline from Phase 42
3. Walk-forward median degradation < 30% across rolling windows

v6.0 parity regression (VAL-04) must stay green throughout. Any fail → retain v6.0.

### Key learnings carried forward

- **Phase 41 lesson:** Grid search must rolling-validate INSIDE the sweep, not post-hoc. v9.0 Phase 40 winners overfit 2015-2021 and degraded +67% to +96% on 2022-2026. Phase 45 implements walk-forward CV as acceptance criterion inside the grid.
- **Engine drift:** Measured baseline CAGR 10.70% vs shipped v6.0 memory 11.5% — Phase 42 must reconcile before any optimization runs.
- **Quick task 260421-lb4 GO verdict:** DXY 20d z corr = -0.1909, EEM 20d z corr = +0.1911, SBV regime spread 55.76pp CAGR. USD/VND + US10Y near-zero → excluded from feature set. Evidence base for Phase 44 MacroFilter.

### Canonical artifacts from prior work

- `output/v9_ab_comparison.txt` — measured baseline 10.70% (input to Phase 42 drift analysis)
- `output/v9_ab_scenarios.csv` — Phase 41 walk-forward degradation table (reference for "do not repeat")
- `docs/research/liquidity_proxy_correlation.md` — quick task 260421-lb4 GO verdict (input to Phase 44)
- `data/vn_liquidity_proxy.csv` + `data/sbv_policy_events.csv` — existing proxy data (Phase 43 productionizes these)
- `strategies/mdm_hybrid/` — engine to modify for MACRO-04 integration
- `analysis/validate_v9.py` — A/B + walk-forward + verdict-string pattern to adapt for Phase 46

### Decisions

See PROJECT.md Key Decisions table. Recent decisions affecting v10.0:

- [Milestone v10.0 start]: VN-native macro proxies (DXY/EEM/SBV), not US/Fed — evidence-based from quick task 260421-lb4
- [Milestone v10.0 start]: Walk-forward CV INSIDE grid search (Phase 41 lesson)
- [Milestone v10.0 start]: HARD gate MaxDD < -20% AND CAGR ≥ baseline — fail = reject, retain v6.0
- [Roadmap creation 2026-04-21]: Dependency order BASE → LIQ → MACRO → WF → VAL → DOC locked (baseline-first principle)
- [Phase 42]: Plan 42-02: Pinned v6.0 ship commit 37cfdc248f8fc1d2aaaf0ec484147b9fa16b4e5a and HEAD 3601679cdba9c3ea674904e6f8a9aa24273cb6ad as bisect anchors; 256 commits in range, 8 engine-touching
- [Phase 42]: Plan 42-01: CAGR-only bisect gate at 11.4 (tight) chosen over composite SELL+MaxDD gate; design-note inline block documents rationale vs D-09 parity band 11.2-11.8 (HEAD acceptance tolerance, wider)
- [Phase 42]: Plan 42-01: sys.stdout.reconfigure() replaces io.TextIOWrapper(sys.stdout.buffer) wrapping in bisect script (Windows I/O-closed-file bug auto-fixed per Rule 1); future Phase 42 plans should adopt this pattern when copying from validate_v9.py
- [Phase 42]: Plan 42-03: git bisect converged on f80394f68b98925c47f0c66b9df1099576878ca0 (Phase 38-02 feat) as single-commit source of CAGR 11.47->10.70 drift; position_manager.py elif-chain reparent made cash_deterioration SELL elif unreachable when close >= ma50
- [Phase 42]: Plan 42-03: D-11 (no fail-safe changes) ruled INAPPLICABLE to offending commit — f80394f modifies CASH->SELL branches not fail-safe; plan 42-04 eligible for D-07 step-1 selective revert
- [Phase 42]: Plan 42-03: /tmp-resident self-contained bisect gate pattern — inline compute_metrics + use os.getcwd() for sys.path — enables bisect across commits predating the gate's originating analysis module. Future BASE-class phases reuse this pattern.
- [Phase 42]: Plan 42-04: STEP 1 selective revert attempted but produced non-self-contained diff (pure git revert removes violation_threshold kwarg that d322a17 wired into mdm_hybrid_engine.py:412 caller); rolled back and escalated to STEP 2 per plan's exit rule
- [Phase 42]: Plan 42-04: STEP 2 landing — added v60_strict_mode: bool = False to MDMV2Config with branch-guard in V2PositionManager.process_day() CASH-state block that restores the flat v6.0 elif chain when True. Parity verified: CAGR 11.4700 / SELL 124 / MaxDD -28.1700 on VN30 2015-2026 (all three D-09 bands PASS). Label: fixed_by_preset.
- [Phase 42]: Plan 42-04: D-11 fail-safe-logic no-fly zone honored — only kwarg pass-throughs (fail_safe_threshold=prev_high) appear in the diff, no decision-logic changes. DECISION-LOGIC grep (fail_safe_exit|fail_safe_enabled|fail_safe_threshold > 0|close > self.position.fail_safe) returns empty on git diff 3601679c..HEAD.
- [Phase 42]: Plan 42-05: Published reconciled v10.0 baseline (BASE-02 closer) — output/v10_reconciled_baseline.json with schema_version=1 and 18 D-12 fields (cagr_pct=11.47, sharpe_rf3=0.502414, sell_count=124, total_return_pct=238.78, max_dd_pct=-28.17, outcome=fixed_by_preset). Force-added past output/ gitignore so Phases 43-47 load without re-running publisher (D-14). Single formatter json.dumps used for both JSON and audit-doc cells ensures byte-identical floats (M1); 8 float fields verified inline + externally. B2 parser with three ValueError paths enforces strict Label-line contract.
- [Phase 42]: Plan 42-05: schema_version is a TABLE-EXCLUDED field in audit doc's ## Reconciled Baseline (present in prose as 'Schema version: **1** (D-15)'). Intentional split: the table is the canonical 18-field tuple, schema_version is metadata about the tuple. Implemented via AUDIT_FIELD_ORDER constant omitting schema_version while build_tuple dict includes it.
- [Phase 42]: Plan 42-06: Closed BASE-03 with tests/test_baseline_determinism.py (274 lines, 3 tests under @pytest.mark.regression class TestBaselineDeterminism). M5 byte-exact primary assertions (len(set(cagrs))==1 etc.) with D-17 thresholds as informative fallback messages only. Byte-exact results DataFrame equality via results_1.equals(results_2) across 2 fresh engines. Co-wave-4-tolerant downstream-JSON guard with pytest.skip fallback. Stdout-safe lazy import of analysis.validate_v9.compute_metrics via orphan-wrapper parking. All 3 tests PASSED on reconciled-HEAD commit 8c6722b in 38.67s.
- [Phase 43]: Plan 43-02: D-06 schema applied to data/sbv_policy_events.csv (5 cols: date, rate_change_pct, new_refinance_rate_pct, direction, source). 12 rows preserved byte-exact; source cites Reuters on 12/12, SBV press on 10/12, Vietnam News on 3/12. No neutral rows (derived downstream). LIQ-02 closed.
- [Phase 43]: Plan 43-02: D-07 conservatism honored. Candidate 2014 refinance cuts (2014-03-18, 2014-10-29) investigated but not appended — no clean Reuters/Vietnam News/SBV citation located in this short pass; omit-rather-than-invert rule applies. Canonical row count stays 12 until a future backfill plan sources these cleanly.
- [Phase 43]: Plan 43-01: Empty-DataFrame treated as transient ValueError (silent yfinance rate-limit surrogate) and retried; missing-'Close'-column is NON-transient and raises RuntimeError immediately per D-05 — two distinct error classes so schema drift surfaces loudly and rate-limits auto-recover
- [Phase 43]: Plan 43-01: HTTPError retry is CODE-filtered — only 401/403/429 retry, all other HTTP statuses re-raise. Prevents retry storms on real backend outages (500s) masquerading as rate-limits
- [Phase 43]: Plan 43-01: data/vn_liquidity_proxy.csv regeneration was byte-identical to HEAD (zero git diff) — confirms D-01 productionize-not-recreate held; yfinance deterministic over identical date range + ticker set at this point in time
- [Phase 43]: Plan 43-03: Spec placed at repo-root docs/ (NOT docs/research/) per plan fence — docs/research is research evidence, docs/ is production contract. Any change to inputs/merge contract requires Phase 44 VAL-04 re-run.
- [Phase 43]: Plan 43-03: Enumerated 5 look-ahead traps vs D-09 minimum of 3. Added (4) rolling-z-score-on-raw-CSV trap and (5) SBV direction='nearest' trap — both greppable failure modes Phase 44 reviewers can key off.
- [Phase 43]: Plan 43-03: Code-Docs Sync pointer added to spec footer — future strategies/mdm_hybrid/macro_filter*.py changes MUST update docs/liquidity_proxy_spec.md in the same commit per CLAUDE.md Code-Docs Sync Rule.
- [Phase 44]: Plan 44-01: doc-only rewrite of MACRO-05 per D-05 landed as two atomic commits (ee0b80d ROADMAP, 46067c4 REQUIREMENTS) BEFORE Wave-2 code work; 6 canonical threshold field names (dxy_easing_z_threshold, dxy_tightening_z_threshold, eem_easing_z_threshold, eem_tightening_z_threshold, dxy_tightening_dd_threshold, sbv_tightening_stop_loss_max_multiplier) now frozen in both ROADMAP.md:852 and REQUIREMENTS.md:26 — Phase 45 planner cannot race on stale dxy_z_threshold/sbv_tightening_position_frac text
- [Phase 44]: Plan 44-02: Wave 2 foundation lands 10 D-15 macro config fields on MDMV2Config + both presets, strategies/mdm_hybrid/macro_filter.py with MacroVerdict frozen dataclass (D-04 stacking requires orthogonal fields, not enum) + add_macro_columns no-look-ahead helper (merge_asof backward + z-score after merge + +1 BusinessDay SBV shift per spec §5/§6), and tests/test_macro_filter.py (18 tests, 11 immediate pass, 7 skip until Plan 03 MacroFilter class) + tests/test_macro_filter_v6_parity.py (2 regression stubs with v60_strict_mode=True Pitfall 8 guard); MacroFilter class deliberately deferred to Plan 03 alongside engine wiring to avoid dead code; empty-SBV-CSV Rule 2 defensive fix bundled with Task 3 commit (pd.read_csv on empty returns object dtypes, BusinessDay shift collapses to float64 breaking merge_asof dtype alignment); baseline determinism remains green (3/3 PASS) so MACRO-04 parity target still achievable
- [Phase 44]: Plan 44-03: MacroFilter class lands + HybridEngine wired via 6 insertion points (import, __init__ conditional instantiation, precompute gate around add_macro_columns, per-row macro_verdict computation, effective_dd_threshold passed to process_day, VETO_SELL handling AFTER IndicatorFilter with restore-from-snapshot + MACRO_VETO_SELL diagnostic). Dual-layer D-09 short-circuit live (engine gate + class first-line guard). BUY-branch DD elif restructured to resolve dd_threshold once via override-or-default pattern (byte-identical when None). Override params (effective_dd_threshold, effective_max_multiplier) default None so pre-Phase-44 byte-exact parity is automatic (Pattern 5 invariant). snapshot = None safeguard at engine line 252 preserved + INSERTION 6 guard no-ops VETO_SELL when two_phase_enabled=False (crash-proof verified). All 18 MacroFilter unit tests + 2 parity regressions + 3 baseline_determinism + 22 hybrid_engine (1 deselected pre-existing) + 3 mdm_regression all PASS.
- [Phase 44]: Plan 44-04: Parity regression sign-off lands — 5/5 tests in tests/test_macro_filter_v6_parity.py PASS under @pytest.mark.regression (macro-off byte-exact parity via df.equals + macro-on determinism + macro-on D-09 column presence + macro-on vs off observable effect defense). Phase 44 VALIDATION.md flipped to status=approved + nyquist_compliant=true + wave_0_complete=true; Per-Task Verification Map renumbered wholesale from planner placeholders (44-01-* → 44-02-*, 44-02-* → 44-03-*, 44-03-* → 44-04-*) to match actual executed plan/wave structure (closes plan-checker WARNING 2). No deviations; no engine changes needed (Plan 03 wiring was correct end-to-end). Baseline determinism 3/3, macro_filter unit 18/18, hybrid_engine 22/22 (1 deselected pre-existing NASDAQ failure). All 5 Phase 44 ROADMAP success criteria objectively met; all 5 MACRO-XX requirements regression-proven complete.
- [Phase 45]: Plan 45-01: D-14 OOS fence enforced at runtime via strict < assertion with 'OOS leak' substring match for Plan 02 pytest grep; EVAL_END=2024-12-31 inclusive; no CLI overrides (reproducibility absolute)
- [Phase 45]: Plan 45-01: D-16 discipline honored — compute_metrics IMPORTED from analysis.validate_v9, zero reimplementation; drift risk across Phase 41/42/45 metric formulas eliminated by construction
- [Phase 45]: Plan 45-01: MACRO_CONFIG_FIELDS module-level 10-tuple is single source of truth for CSV COL_ORDER + JSON _config_tuple + run_combo row seeding; prevents the 10-field list from drifting across three call sites (Claude discretion refinement beyond planner suggestion)
- [Phase 45]: Plan 45-01: JSON payload uses Python float('nan') in median_eval_max_dd_pct for all-NaN year edge case (json.dump emits literal NaN — acceptable since D-11 consumer is Phase 46 pandas/numpy, not strict JSON parser); chose signal-preserving NaN over None cast
- [Phase 45]: Plan 45-01: df_override injection hook on load_vn30_data enables Plan 02 pytest to raise AssertionError on synthetic 2025 frames without network-bound DataLoader call; reusable pattern for future OOS-guard tests

### Pending Todos

None. See `.planning/todos/pending/` (empty).

### Blockers/Concerns

None blocking Phase 42. Downstream concerns tracked in phase-specific plans.

## Session Continuity

Last session: 2026-04-23T08:37:10.127Z
Stopped at: Completed 45-01-walkforward-grid-script-PLAN.md (analysis/walkforward_grid.py 685 lines, 5 commits 6ccb5cb..9180905)
Resume file: None
Next command: `/gsd:plan-phase 42` to plan Baseline Reconciliation (BASE-01, BASE-02, BASE-03)
