---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: VN Macro Filter + Baseline Reconciliation
status: executing
stopped_at: Completed 42-04-PLAN.md (BASE-02 fix-forward; v60_strict_mode preset flag landed — CAGR 11.47 / SELL 124 / MaxDD -28.17 parity restored)
last_updated: "2026-04-22T06:39:52.141Z"
last_activity: 2026-04-22
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
**Current focus:** Phase 42 — baseline-reconciliation

## Current Position

Phase: 42 (baseline-reconciliation) — EXECUTING
Plan: 3 of 6
Status: Ready to execute
Last activity: 2026-04-22

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

### Pending Todos

None. See `.planning/todos/pending/` (empty).

### Blockers/Concerns

None blocking Phase 42. Downstream concerns tracked in phase-specific plans.

## Session Continuity

Last session: 2026-04-22T06:39:52.136Z
Stopped at: Completed 42-04-PLAN.md (BASE-02 fix-forward; v60_strict_mode preset flag landed — CAGR 11.47 / SELL 124 / MaxDD -28.17 parity restored)
Resume file: None
Next command: `/gsd:plan-phase 42` to plan Baseline Reconciliation (BASE-01, BASE-02, BASE-03)
