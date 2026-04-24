# Phase 46: A/B + OOS Validation (HARD Gate) - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate the v10.0 macro filter against the HARD gate using A/B scenarios + OOS 2025-2026 + walk-forward re-check + v6.0 parity regression, then emit a **literal verdict string** that drives Phase 47 branching. Phase 45 produced **0/39 accepted combos**; the HARD gate is expected to fail and the verdict will be `"v6.0 retained as production"`. Phase 46 produces the complete scientific audit record proving that verdict holds.

**Deliverables:**

1. `output/v10_ab_comparison.txt` — human-readable A/B report: 5 scenarios (baseline / +DXY / +EEM / +SBV-regime / +all) on full VN30 2015-2026 with canonical metrics per scenario (CAGR, Sharpe_rf3, MaxDD, total return, transitions, time-in-state, SELL count, MA50-breakdown share)
2. `output/v10_ab_scenarios.csv` — machine-readable, one row per scenario with the same metrics + train/test split columns (adapting Phase 41 pattern)
3. `output/v10_validation_report.txt` — HARD-gate verdict with literal string per VAL-05; includes rejection narrative (per D-04 below) summarizing WHY v10 failed
4. Existing `tests/test_macro_filter_v6_parity.py` run as part of the validation pipeline (VAL-04 — do NOT duplicate)

**Explicitly out of scope:**
- Rule docs updates (`docs/rules_mdm_hybrid.md`) — Phase 47 DOC-01 (conditional on pass → will be skipped)
- Dashboard data / S3 deploy — Phase 47 DOC-02 (conditional on pass → will be skipped)
- Milestone audit / `.planning/MILESTONES.md` entry — Phase 47 DOC-03
- Any change to `MacroFilter` logic, `MDMV2Config` field surface, fail-safe, position_manager, stop_loss code — Phase 44 owns these (consume read-only)
- Re-running Phase 45 sweep or regenerating `output/v10_grid_results.csv`
- Loosening D-09 acceptance gate or otherwise re-opening Phase 45's verdict
- Any change to Phase 43 liquidity CSVs or Phase 42 baseline reconciliation
- `memory` updates to `project_best_model.md` (Phase 47 DOC-04 in requirements)

</domain>

<decisions>
## Implementation Decisions

### Scenario parameter choice

- **D-01 (User choice, option 1a — "defaults"):** The four macro-on scenarios (+DXY / +EEM / +SBV-regime / +all) use **Phase 44 `VN30_PRESET` defaults** for their active factor(s). Rationale: Phase 45 did not produce a winner (0/39 accepted), so `output/v10_grid_best.json` is absent and there is no optimized config to substitute. VN30_PRESET is the "as-designed" filter — the canonical config the milestone was supposed to ship. Running A/B with defaults documents "as-designed macro filter vs v6.0 baseline", which is the scientifically cleanest question Phase 46 can answer.
- **D-02 (Isolation via threshold extremes — inherits Phase 45 D-18):** +DXY, +EEM, +SBV-regime are isolated by pushing the OTHER factors' z-thresholds to never-trigger extremes — no new per-factor boolean toggles on `MDMV2Config`. Planner chooses the exact extreme values (recommended starting point: |z| ≥ 999 for z-thresholds; `sbv_tightening_stop_loss_max_multiplier = 1.0` to neutralize SBV). Planner must verify the extreme values actually prevent the factor from ever triggering on 2015-2026 data (e.g., print the max/min observed z-scores and assert extremes exceed them).
- **D-03 (+all scenario equals Phase 44 VN30_PRESET as-shipped):** The +all scenario is `macro_filter_enabled=True` with all VN30_PRESET defaults intact. This is the "full stack" configuration Phase 44 wired up.

### OOS 2025-2026 config

- **D-04 (User choice, option 2a — "defaults"):** OOS test on 2025-2026 runs **only two configs**: `baseline` (macro off, v6.0 reference) and `+all` (VN30_PRESET defaults, as-shipped). Rationale: VAL-02 text in REQUIREMENTS says "HARD gate on the selected scenario" — with no winner from Phase 45, +all-defaults is the canonical "selected" scenario to test. Running all 5 scenarios on OOS is wasted compute given the HARD gate is already expected to fail on in-sample walk-forward (VAL-03 inherited from Phase 45). Two configs is the minimum that lets VAL-02 evaluate the HARD gate with a defensible "scenario chosen".
- **D-05 (HARD gate numeric thresholds):** `MaxDD < -20%` AND `CAGR ≥ reconciled_baseline_cagr`. `reconciled_baseline_cagr = 11.47%` per [output/v10_reconciled_baseline.json](output/v10_reconciled_baseline.json) — read the JSON at runtime, do NOT hardcode 11.47 in the Python script. Fail on any gate reachable via exit code 1.

### HARD gate evaluation behavior

- **D-06 (User choice, option 3a — "defaults", no short-circuit):** Run **all four gates** (VAL-01 A/B, VAL-02 OOS HARD, VAL-03 walk-forward stability re-check, VAL-04 parity regression) in sequence regardless of interim results. Do NOT short-circuit the moment one gate fails. Rationale: Phase 46 is the canonical record for the milestone audit — Phase 47 DOC-03 and future v11.0 work need the complete per-gate data. Compute cost is small (<30 min total).
- **D-07 (VAL-03 walk-forward re-check method):** The walk-forward stability re-check consumes [output/v10_grid_results.csv](output/v10_grid_results.csv) from Phase 45 directly — do NOT re-run the 39-combo sweep. For the +all scenario (VN30_PRESET defaults), look up its row in the CSV (this is the Phase 45 `stage3_all_three-c0` combo which holds all defaults locked) and read its `median_degradation` field. VAL-03 pass = that median_degradation < 0.30. Since Phase 45 data already shows every combo ≥ 0.41, VAL-03 is known-fail — but the re-check remains in Phase 46 for closed-form auditability.
- **D-08 (VAL-04 reuses existing Phase 44 parity test):** The v6.0 parity regression gate runs [tests/test_macro_filter_v6_parity.py](tests/test_macro_filter_v6_parity.py) via `uv run python -m pytest tests/test_macro_filter_v6_parity.py -v`. Do NOT write a new test. Do NOT duplicate parity logic inside `analysis/validate_v10.py`. The Phase 46 validation script must invoke pytest (subprocess or `pytest.main()`) and capture the exit code into the validation report.

### Verdict string & Phase 47 hand-off

- **D-09 (Verdict string format — ROADMAP SC-5 locked):** Exactly one of two literal strings appears in `output/v10_validation_report.txt`, grep-matchable by Phase 47:
  - Full pass (all 4 gates): `"v10 macro filter accepted as production"`
  - Any gate fail: `"v6.0 retained as production"`
  - No other string permitted. Case-sensitive. Planner specifies exact line format.
- **D-10 (User choice, option 4b — "defaults", rejection narrative included):** `v10_validation_report.txt` includes a **"Rejection Narrative"** section on fail path summarizing: (a) which gate(s) failed, (b) Phase 45 evidence for WHY they failed (train-period drag: train CAGR 9.54% vs baseline 11.47% before eval-year degradation; 2021 and 2024 per-year whipsaw medians −11.56% / −12.49%), (c) Phase 45 CSV + JSON (absent) pointers, (d) reconciled baseline gate reference. Length: 20-40 lines. Phase 47 DOC-03 consumes this section verbatim where relevant.
- **D-11 (Exit code discipline):** The validation script's process exit code **reflects the gate verdict** — exit 0 on full pass, exit 1 on any fail (matches REQUIREMENTS VAL-02 "exit code reflecting gate verdict"). This makes CI integration possible later without re-parsing text.

### Script location & reuse

- **D-12 (Script location):** Create `analysis/validate_v10.py` following the `analysis/validate_v9.py` skeleton (module docstring, Module Constants block, `load_locked_params` → adapted to `load_v10_config`, scenario loop, walk-forward section, verdict writer). Do NOT modify `validate_v9.py` (it is the Phase 41 canonical record and the Phase 45 pytest imports `compute_metrics` from it).
- **D-13 (Metrics function reuse):** Import `compute_metrics` from `analysis.validate_v9` (same import path Phase 45 used). Do NOT fork metrics computation — would break determinism vs Phase 45 numbers.
- **D-14 (Data window):** Full A/B runs on `DATA_START='2015-01-01' → DATA_END='2026-03-31'` (same as v9 precedent — matches reconciled baseline period). OOS window is `2025-01-01 → 2026-03-31` (the post-Phase-45-fence data).

### Claude's Discretion

- Exact numeric values for "never-trigger" z-thresholds in the +DXY / +EEM / +SBV isolation scenarios (D-02) — planner picks extreme and verifies against observed data range
- Text layout / formatting inside `v10_ab_comparison.txt` — follow `v9_ab_comparison.txt` precedent as closely as practical
- Exact CSV column ordering — follow `v9_ab_scenarios.csv` precedent with additional columns for time-in-state, transitions, SELL count, MA50-breakdown share per VAL-01
- How the rejection narrative is formatted (Markdown-like vs plain prose) — consistent with the rest of `v10_validation_report.txt`
- Whether to inline-capture pytest VAL-04 output in the report or just record exit code + pointer

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Validation skeleton & A/B pattern
- [analysis/validate_v9.py](../../../analysis/validate_v9.py) — Phase 41 canonical pattern for A/B + walk-forward + scenarios CSV + verdict string. Reuse module-constants block, scenario loop shape, `compute_metrics`, walk-forward train/test slicing. Adapt from 4 scenarios (baseline/+ATR/+DD/+both) to 5 (baseline/+DXY/+EEM/+SBV-regime/+all) and add exit-code reflective verdict per D-11.

### Macro filter config (scenario builder source)
- [strategies/mdm_hybrid/config.py](../../../strategies/mdm_hybrid/config.py) — `VN30_PRESET` holds Phase 44 as-designed macro config; 10 macro fields on `MDMV2Config`. Scenario builder reads `VN30_PRESET` and toggles factor isolation via threshold extremes per D-02.
- [strategies/mdm_hybrid/macro_filter.py](../../../strategies/mdm_hybrid/macro_filter.py) — `MacroFilter` logic + `MacroVerdict` dataclass Phase 46 consumes read-only. Do NOT modify.

### Reconciled baseline (HARD gate reference)
- [output/v10_reconciled_baseline.json](../../../output/v10_reconciled_baseline.json) — Phase 42 canonical tuple (schema_version 1). CAGR gate reference = `reconciled_cagr_pct` field = 11.47%. Read at runtime, do NOT hardcode.

### Phase 45 grid results (VAL-03 data source)
- [output/v10_grid_results.csv](../../../output/v10_grid_results.csv) — 39 rows × 52 cols, all accepted=False. `median_degradation` column is the VAL-03 input. `stage3_all_three-c0` is the row representing +all defaults (VN30_PRESET).
- Phase 45 SUMMARY at [.planning/phases/45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md](../45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md) — canonical narrative of the zero-accepted outcome; rejection narrative (D-10) draws from this.

### Parity regression (VAL-04)
- [tests/test_macro_filter_v6_parity.py](../../../tests/test_macro_filter_v6_parity.py) — Phase 44 byte-exact v6.0 parity test. Phase 46 runs it as the VAL-04 gate. Do NOT duplicate.
- [tests/test_walkforward_oos_guard.py](../../../tests/test_walkforward_oos_guard.py) — Phase 45 SC-4 test (not a Phase 46 gate, but remains in `@pytest.mark.regression` suite; full regression green is a hygiene pre-flight).

### Verdict contract (Phase 47 consumer)
- [.planning/REQUIREMENTS.md](../../REQUIREMENTS.md) — VAL-01..VAL-05 full text; verdict string format locked by VAL-05.
- [.planning/ROADMAP.md](../../ROADMAP.md) §Phase 46, §Phase 47 — branching logic on verdict string; Phase 47 reads `output/v10_validation_report.txt` and greps for either literal verdict.

### Milestone baseline memory (context for narrative)
- [.planning/MILESTONES.md](../../MILESTONES.md) v9.0 entry — prior rejection precedent (walk-forward-only-post-hoc lesson); Phase 46 narrative should NOT duplicate, just cross-link.
- [.planning/PROJECT.md](../../PROJECT.md) §"v10.0 progress" — Phase 45 already logged; Phase 46 does not touch PROJECT.md (Phase 47 does per DOC-04 equivalent).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`analysis/validate_v9.py`** (393 LOC) — fork this file's skeleton. Specifically: module-constants block (lines 50-67), scenario iteration pattern (`SCENARIO_ORDER` list-driven loop), `compute_metrics` helper, walk-forward train/test split using single engine run + slice (D-04 precedent in Phase 45), human-readable report writer, scenarios CSV writer. Adapt exit discipline: v9 is exit-0-always (D-14 note), v10 must be exit-code reflective (D-11).
- **`compute_metrics` function in `analysis/validate_v9.py`** — imported by Phase 45 [analysis/walkforward_grid.py](../../../analysis/walkforward_grid.py) already; Phase 46 imports the same. Determinism of metrics across phases depends on this reuse.
- **`strategies/mdm_hybrid.config.VN30_PRESET`** — the canonical macro-on config (D-03). Use `dataclasses.replace(VN30_PRESET, ...)` to build the 4 macro-on scenarios with threshold-extreme overrides for +DXY / +EEM / +SBV isolation.
- **`strategies/mdm_hybrid.mdm_hybrid_engine.HybridEngine`** — the engine `validate_v9` already runs against; Phase 46 uses it unchanged.
- **`tests/test_macro_filter_v6_parity.py`** — VAL-04 in one file; invoke via pytest subprocess or `pytest.main()`.

### Established Patterns

- **Output report format** — `output/v9_ab_comparison.txt` is the text-report template (header, per-scenario metrics block, walk-forward table, whipsaw diagnostic, production candidate line). Mirror this structure with 5 scenarios + rejection narrative.
- **Scenarios CSV schema** — `output/v9_ab_scenarios.csv` has one row per scenario with train/test split columns. Extend with VAL-01 required columns (transitions, time-in-state, SELL count, MA50 breakdown share per scenario).
- **Artifact naming** — `v10_*` prefix consistent with Phase 42 (`v10_reconciled_baseline.json`), Phase 45 (`v10_grid_results.csv`). No collisions with Phase 46 artifacts (`v10_ab_comparison.txt`, `v10_ab_scenarios.csv`, `v10_validation_report.txt` are all new).
- **Regression hygiene** — Phase 45 established `@pytest.mark.regression` convention; Phase 46 should run full regression suite as pre-flight (13 tests post-Phase-45) and report green before validation begins.

### Integration Points

- **Phase 47 consumer** — `output/v10_validation_report.txt` read by Phase 47 DOC-01/DOC-02/DOC-03 branching. Contract is the VAL-05 literal verdict string.
- **Phase 45 consumer** — Phase 46 reads `output/v10_grid_results.csv` for VAL-03 lookup (D-07) and `output/v10_reconciled_baseline.json` for CAGR gate (D-05).
- **CI/memory hand-off** — `project_best_model.md` in user memory currently records v6.0 (+238.8%, CAGR 11.5%, MaxDD −28.2%). Phase 46 does NOT update memory; Phase 47 does, conditional on verdict. Phase 46 only writes the verdict string.

</code_context>

<specifics>
## Specific Ideas

- **Rejection narrative should be the "last scientist" perspective** — write as if explaining to a future v11.0 planner why v10.0 didn't work, not as apology. Include: train-drag (9.54% vs 11.47%, −2pp before degradation), per-year whipsaw table (2019-2024), degradation distribution histogram reference (min 0.410 / median 0.538 / max 0.645), +all scenario full-period return (from Phase 45 sweep row `stage3_all_three-c0`: ~+146.8% 10y) vs v6.0 baseline (~+197% 10y).
- **Keep the verdict string isolated on its own line** in `v10_validation_report.txt` so a plain `grep` without word-boundary tricks finds it cleanly from Phase 47.
- User's general preference (prior session): "always record best model clearly; don't force user to dig git history" — applied here by making the rejection narrative rich enough that a cold reader gets the v6.0-retained story without opening Phase 45 artifacts.

</specifics>

<deferred>
## Deferred Ideas

- **Loosening HARD gate to "partial acceptance" (e.g., accept on MaxDD-only improvement with CAGR penalty)** — scope creep. User explicitly stated (project memory): "HARD gate: fail = reject, retain v6.0. No soft acceptance of improvement on one dimension only". This is a milestone decision locked before Phase 42.
- **Re-planning Phase 45 with a looser acceptance gate** — scope creep. Would belong to v11.0 milestone.
- **Running the full 5-scenario matrix on OOS 2025-2026** — decided against (D-04). If Phase 47 DOC-03 rejection audit wants more OOS data, it can commission a quick-task.
- **New VN11.0 milestone scoping** — belongs to `/gsd:new-milestone` after Phase 47 completes. Phase 46 just produces the evidence.
- **Dashboard rejection page** — Phase 47 DOC-02 scope (conditional skipped branch).

</deferred>

---

*Phase: 46-ab-oos-validation-hard-gate*
*Context gathered: 2026-04-23*
