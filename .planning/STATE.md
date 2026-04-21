---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: VN Macro Filter + Baseline Reconciliation
status: planning
stopped_at: Phase 42 context gathered
last_updated: "2026-04-21T09:38:43.785Z"
last_activity: 2026-04-21 — ROADMAP.md created, all 22 requirements mapped to phases 42-47
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
**Current focus:** Phase 42 — Baseline Reconciliation

## Current Position

Phase: 42 of 47 (Baseline Reconciliation) — first v10.0 phase
Plan: — (ready to plan)
Status: Ready to plan
Last activity: 2026-04-21 — ROADMAP.md created, all 22 requirements mapped to phases 42-47

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

### Pending Todos

None. See `.planning/todos/pending/` (empty).

### Blockers/Concerns

None blocking Phase 42. Downstream concerns tracked in phase-specific plans.

## Session Continuity

Last session: 2026-04-21T09:38:43.780Z
Stopped at: Phase 42 context gathered
Resume file: .planning/phases/42-baseline-reconciliation/42-CONTEXT.md
Next command: `/gsd:plan-phase 42` to plan Baseline Reconciliation (BASE-01, BASE-02, BASE-03)
