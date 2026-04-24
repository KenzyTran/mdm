# Phase 46: A/B + OOS Validation (HARD Gate) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 46-ab-oos-validation-hard-gate
**Areas discussed:** Scenario parameter choice, OOS config, HARD gate evaluation behavior, Phase 47 rejection-audit prep
**Mode:** single-turn "defaults" — user accepted recommended option for all four gray areas

---

## Scenario parameter choice

| Option | Description | Selected |
|--------|-------------|----------|
| 1a — VN30_PRESET defaults | Use Phase 44 as-designed macro config for +DXY / +EEM / +all. Documents "as-designed filter vs baseline". | ✓ |
| 1b — Closest-to-passing per stage | Use `stage1_dxy-c3` / `stage2_eem-c5` / `stage3_all_three-c0` from Phase 45 CSV. Documents "even the best combos fail". | |
| 1c — Both (2×4 macro-on scenarios) | Run both approaches, 8 macro-on scenarios total. Complete picture, higher compute. | |

**User's choice:** 1a (defaults)
**Notes:** No winner exists from Phase 45 (0/39 accepted, `v10_grid_best.json` absent), so "optimized config" is moot. VN30_PRESET is the canonical "as-designed" filter and the cleanest comparison target. Factor isolation for +DXY / +EEM / +SBV uses threshold extremes per inherited Phase 45 D-18 — no new config toggles added.

---

## OOS 2025-2026 config

| Option | Description | Selected |
|--------|-------------|----------|
| 2a — Baseline + +all defaults only | Minimal OOS: 2 configs. Matches VAL-02 text "selected scenario". | ✓ |
| 2b — All 5 scenarios on OOS | Full picture, more compute. | |
| 2c — Best-of-39 + baseline | Use `stage1_dxy-c3`. Documents "closest candidate still fails HARD gate OOS". | |

**User's choice:** 2a (defaults)
**Notes:** HARD gate already expected to fail on in-sample walk-forward (VAL-03) per Phase 45 evidence; additional OOS scenarios are wasted compute. Two configs is the minimum for a defensible "selected scenario" interpretation of VAL-02.

---

## HARD gate evaluation behavior

| Option | Description | Selected |
|--------|-------------|----------|
| 3a — Run all 4 gates, no short-circuit | Complete audit record. VAL-01 + VAL-02 + VAL-03 + VAL-04 all execute. | ✓ |
| 3b — Short-circuit on VAL-03 known-fail | Skip VAL-02 OOS compute, derive verdict from Phase 45 evidence + VAL-01 + VAL-04. | |

**User's choice:** 3a (defaults)
**Notes:** Compute cost is small (<30 min). Phase 47 DOC-03 rejection audit and future v11.0 work benefit from the complete per-gate data. Short-circuit would create a gap in the audit record.

---

## Phase 47 rejection-audit prep

| Option | Description | Selected |
|--------|-------------|----------|
| 4a — Required artifacts only | 3 files per ROADMAP; Phase 47 derives rejection lessons itself. | |
| 4b — Include "Rejection Narrative" section | 20-40 line narrative inside `v10_validation_report.txt` summarizing WHY v10 failed. | ✓ |

**User's choice:** 4b (defaults)
**Notes:** Phase 47 DOC-03 consumes the narrative verbatim where relevant. Aligns with user's persistent preference "always record best model clearly; don't force user to dig git history" — rejection story should be legible without re-opening Phase 45 artifacts.

---

## Prior decisions carried forward (not re-discussed)

From [.planning/phases/45-walk-forward-grid-search/45-CONTEXT.md](../45-walk-forward-grid-search/45-CONTEXT.md):
- **D-18 (Phase 45):** +DXY / +EEM / +SBV isolation in Phase 46 via threshold extremes, not new toggles

From [.planning/phases/44-macro-filter-module/44-CONTEXT.md](../44-macro-filter-module/44-CONTEXT.md):
- **D-15 (Phase 44):** 10 macro config fields on `MDMV2Config`, feature-gated, `VN30_PRESET` is canonical

From [.planning/REQUIREMENTS.md](../../REQUIREMENTS.md):
- **VAL-02 HARD gate:** `MaxDD < -20%` AND `CAGR ≥ reconciled_baseline` (11.47% from [output/v10_reconciled_baseline.json](../../../output/v10_reconciled_baseline.json))
- **VAL-04 parity regression:** reuse existing [tests/test_macro_filter_v6_parity.py](../../../tests/test_macro_filter_v6_parity.py), do NOT duplicate
- **VAL-05 verdict string:** literal `"v10 macro filter accepted as production"` on pass, `"v6.0 retained as production"` on fail

From [.planning/PROJECT.md](../../PROJECT.md) "Key Decisions" table:
- **v10.0 HARD gate is uncompromised** — no soft acceptance of improvement on one dimension only

## Claude's Discretion

- Exact numeric values for "never-trigger" z-thresholds in +DXY / +EEM / +SBV isolation (D-02 of CONTEXT.md)
- Text layout inside `v10_ab_comparison.txt` (follow v9 precedent)
- CSV column ordering (follow v9 precedent + VAL-01 required additions)
- Rejection narrative formatting (Markdown-like vs plain prose, consistent with rest of report)
- Whether to inline-capture pytest VAL-04 output or record exit code + pointer

## Deferred Ideas

- Loosening HARD gate — explicitly locked-closed per PROJECT.md key decision
- Running full 5-scenario matrix on OOS — decided against in D-04
- Dashboard rejection page — Phase 47 DOC-02 skipped branch
- v11.0 milestone scoping — belongs to `/gsd:new-milestone` after Phase 47
