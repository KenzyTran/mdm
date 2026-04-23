---
phase: 45-walk-forward-grid-search
plan: 03
subsystem: validation
tags: [walk-forward, grid-search, macro-filter, vn30, retain-v6.0, oos-discipline, legitimate-rejection]

# Dependency graph
requires:
  - phase: 45-walk-forward-grid-search
    plan: 01
    provides: analysis/walkforward_grid.py orchestrator
  - phase: 45-walk-forward-grid-search
    plan: 02
    provides: tests/test_walkforward_oos_guard.py (OOS fence regression)
  - phase: 42-baseline-reconciliation
    provides: output/v10_reconciled_baseline.json (context anchor — not a gate)
  - phase: 44-macro-filter-module
    provides: MDMV2Config 10 macro fields + MacroFilter + HybridEngine wiring (sweep's search target)
provides:
  - output/v10_grid_results.csv (39 rows, force-added past gitignore) — full D-06 schema
  - retain-v6.0 verdict for Phase 46 branching (all 39 combos rejected by D-09 gate)
  - runtime evidence that v10.0 macro filter does NOT pass walk-forward discipline
affects: [46-ab-oos-validation, 47-docs-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase-42-05 force-add past gitignore — output/ is gitignored but downstream-consumable artifacts are checked in via git add -f"
    - "main() zero-accepted guard — D-11 JSON is intentionally NOT written when no stage has a winner (fabrication refusal, not a bug)"
    - "Legitimate-rejection commit-message pattern — commit explicitly names the retain-v6.0 branch so git log reads as a scientific result, not a half-finished task"

key-files:
  created:
    - output/v10_grid_results.csv (39 rows × 52 cols, 19 851 bytes — force-added)
  modified: []

key-decisions:
  - "Commit CSV alone (not CSV + JSON) — main() correctly refused to write output/v10_grid_best.json because zero stages had accepted winners; fabricating a JSON with null winners would be worse than omitting it"
  - "Commit-message body names the retain-v6.0 verdict explicitly — Phase 46 planner and future-you reading git log immediately sees this was a legitimate scientific outcome, not a skipped artifact"
  - "Keep run.log ephemeral (not committed) — D-02/planner intent honored, key numbers copied into SUMMARY.md instead"
  - "No code changes, no test changes, no strategy changes — this plan is pure execution + documentation, scope-pure per plan out-of-scope self-check"

patterns-established:
  - "Walk-forward sweep result publication under retain-v6.0 branch — commit the rejection artifact with explicit verdict in the message body so downstream branching (Phase 46 HARD gate → Phase 47 conditional DOC-01/02) has machine-grep-able evidence without needing to re-run the sweep"

requirements-completed: [WF-01, WF-02, WF-03]

# Metrics
duration: ~15min (sweep 2m37s + inspection + commits)
completed: 2026-04-23
---

# Phase 45 Plan 03: Execute Sweep + Commit Artifacts Summary

**`analysis/walkforward_grid.py` executed end-to-end on VN30 2015-2024: 39 combos swept in 2m37s, zero accepted. All combos failed the D-09 gate `median_degradation < 0.30` — train→eval degradation median 53.8% is nearly twice the threshold. Per Plan 03 line 211, this is a LEGITIMATE scientific result: v10.0 VN-native macro filter (DXY/EEM/SBV) does not pass walk-forward discipline. Phase 46 enters the retain-v6.0 branch. Human verified and approved the retain-v6.0 interpretation at the Task 3 checkpoint.**

## Performance

- **Duration:** ~15 min total (sweep 2m37s, inspection + checkpoint + commit)
- **Sweep runtime:** 2 min 37 s (Stage 1 = 1m47s, Stage 2 = 35s, Stage 3 = 11s)
- **Exit code:** 0 (clean — no SummaryError, no uncaught exception, D-18 top-3 NaN guard did not fire)
- **Tasks:** 4 (3 executed pre-checkpoint, Task 4 completed post-approval by continuation agent)
- **Files modified:** 1 (output/v10_grid_results.csv — force-added past gitignore)

## Accomplishments

- Executed the Phase 45 walk-forward sweep to completion with no runtime failures or data issues.
- All 39 combos produced complete per-year metrics (`eval_years_count=6` for every row, zero NaN in `error_*` columns).
- D-14 OOS fence held: max date in loaded VN30 data = 2024-12-31 < 2025-01-01 OOS_FENCE. Plan 02's pytest regression suite (10/10 PASS pre-run and post-run) validates the assertion semantics.
- D-09 acceptance gate applied correctly: 0 combos accepted, 39 rejected via `median_degradation >= 0.30`. Zero rejections via the `median_eval_cagr_pct > 0%` floor (every combo earned a positive median eval CAGR — the failure is degradation-shape, not CAGR-sign).
- D-11 JSON payload intentionally NOT written: `main()` checks "at least one stage has no accepted winner" and aborts the JSON step with the literal log line `"WARNING: at least one stage has no accepted winner - ... v10_grid_best.json NOT written"`. This is the planner's defensive behavior — fabricating a winner when none passed would silently poison Phase 46.
- Committed CSV (force-add past `output/` gitignore per Phase 42-05 precedent). Commit message body names the retain-v6.0 verdict explicitly so `git log` reads as a scientific outcome rather than a half-finished sweep.
- Human reviewed the artifact at Task 3 checkpoint and explicitly approved the retain-v6.0 interpretation.

## Task Commits

Per GSD task-commit protocol. Tasks 1-3 in the prior executor session (pre-checkpoint); Task 4 in the continuation session (post-approval):

1. **Task 1: Pre-flight checks (regression 10/10, py_compile, artifact state noted)** — no commit (no file changes, as planned)
2. **Task 2: Execute the sweep end-to-end** — no separate commit (sweep output is data, committed under Task 4)
3. **Task 3: Human-verify sweep results** — checkpoint task, no code changes
4. **Task 4: Commit artifact (CSV alone, JSON intentionally absent per main() guard)** — `4dd00a0` (data)

## Files Created/Modified

- `output/v10_grid_results.csv` — NEW, 39 data rows × 52 columns, force-added past `output/` gitignore. Schema per D-06: stage + combo_id + config_name + 10 macro config fields + train metrics (CAGR/Sharpe/MaxDD) + 6×3 per-year metrics + 6 per-year degradation + aggregate (median_degradation, median_eval_cagr_pct, eval_years_count) + accept decision (accepted, rejection_reason) + 7 error columns (error_train, error_year_2019..2024 — all NaN / empty, confirming clean runs).
- `output/v10_grid_best.json` — **NOT created** per design. `main()` aborted JSON write when zero stages had winners. Commit message body documents this explicitly.
- `output/v10_grid_run.log` — NOT committed (ephemeral per planner intent). 36-line stdout capture with tqdm progress bars, stage banners, and the final "0/39 combos accepted" summary.

## Sweep Results (Key Numbers)

**Headline:** 0/39 combos accepted. All rejected by the D-09 gate `median_degradation >= 0.30`. Full-period 10y total return across combos: median +146.84%, best +163.39%. v6.0 reconciled baseline reference (not a gate): +238.78% total return at 11.47% CAGR.

### Per-stage summary

| Stage | Combos | train CAGR (median) | eval CAGR (median) | degradation (median) | degradation (min) | Accepted |
| ----- | ------ | ------------------- | ------------------ | -------------------- | ----------------- | -------- |
| stage1_dxy | 27 | 9.29% | 4.57% | 0.509 | 0.410 | 0 |
| stage2_eem | 9 | 9.60% | 3.72% | 0.617 | 0.508 | 0 |
| stage3_all_three | 3 | 9.87% | 4.57% | 0.537 | 0.537 | 0 |
| **Total** | **39** | **9.54%** | **4.57%** | **0.5375** | **0.410** | **0** |

**Reading**: every combo suffered ~41%-64% train→eval CAGR degradation (median 54%) — more than 1.3× to 2.1× the D-09 threshold of 30%. Even the best combo by degradation (`stage1_dxy-c3` at 0.411) cleared only by a hair and still failed. Adding EEM on top of DXY (Stage 2) or SBV on top (Stage 3) tightened degradation rather than widening it, indicating the macro filter is over-fitting to 2015-2018 training conditions and delivering less robust out-of-sample behavior than the v6.0 baseline.

### Best combo by eval CAGR (still rejected)

- **Config:** `stage1_dxy-c3` (stage1_dxy)
- **train_cagr_pct:** 9.46%
- **median_eval_cagr_pct:** 5.58%
- **median_degradation:** 0.411 (fails D-09 `< 0.30`)
- **rejection_reason:** `median_degradation 0.411 >= 0.30`

### Worst-year drawdown distribution

Across 39 combos × 6 eval years = 234 single-year DD observations:

- **Deepest single-year DD:** -19.68% (2021, across every combo that reached Stage 3 / locked configuration). Better than v6.0's full-period MaxDD of -28.17%.
- **Median single-year DD:** -14.98%
- **By year (median across combos):** 2019 -8.74%, 2020 -15.29%, 2021 -19.68%, 2022 -15.33%, 2023 -12.72%, 2024 -12.45%

**Interpretation:** the macro filter DOES reduce per-year MaxDD vs the v6.0 baseline's -28.17% full-period DD (every year's median DD is shallower than the v6.0 peak), but the cost — eroded CAGR on a year-by-year basis — is too high. The D-09 gate correctly vetoed the trade-off at the discovery stage.

### Error columns

- `error_train`: 0 non-null rows (zero train failures)
- `error_year_{2019..2024}`: 0 non-null rows each (zero per-year failures)
- D-18 top-3 NaN guard did not fire (no SummaryError raised).

## Decisions Made

- **Commit CSV alone, not CSV + JSON (deviation from plan Task 4 `<action>`).** Plan Task 4 assumes both artifacts are committed. Under the approved retain-v6.0 interpretation, JSON intentionally does not exist — fabricating a winner payload would silently poison Phase 46. Adapted the commit strategy to CSV-only with a commit-message body that names the retain-v6.0 branch explicitly, so downstream phases (46 branching, 47 conditional docs) have a machine-grep-able anchor without needing to re-run the sweep. **Filed as Rule 3 deviation (auto-adapted blocking condition) — documented below.**
- **Commit-message body is long-form on purpose.** Git log is the canonical audit trail for Phase 46 planner deciding which branch to enter. An 800-byte commit message with per-stage numbers + verdict + rationale costs nothing and prevents "why is there no JSON" spelunking three weeks from now.
- **run.log not committed.** Plan 02's `<read_first>` says "runlog is ephemeral — not committed to git (add to .gitignore check if not already)." The `output/` directory is already gitignored, so the log is implicitly untracked. Key numbers extracted to this SUMMARY.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adapted Task 4 commit from "stage CSV + JSON" to "stage CSV alone"**

- **Found during:** Task 4 artifact verification
- **Issue:** Plan Task 4 `<action>` block runs `git add -f output/v10_grid_results.csv output/v10_grid_best.json`. Under the approved retain-v6.0 interpretation, `output/v10_grid_best.json` does not exist on disk (main() correctly aborted the write). `git add` on a non-existent file would fail and halt the commit.
- **Fix:** Staged and committed CSV alone. Adapted commit-message subject from `feat(45): execute walk-forward grid sweep, commit CSV + JSON artifacts` to `data(45-03): commit v10 walkforward sweep results -- 0/39 accepted, retain v6.0`. The commit-message body documents the JSON's intentional absence with the exact main() guard logic.
- **Files modified:** `output/v10_grid_results.csv` (the sole artifact; staged with `git add -f` past `output/` gitignore).
- **Commit:** `4dd00a0`

This is a forced adaptation — the plan's `<action>` block assumes the happy path where at least one combo is accepted. Plan's `<resume-signal>` line 211 explicitly documents the zero-accepted case as legitimate, so the deviation is pre-sanctioned by the plan's own language. No user permission needed (Rule 3).

### Authentication Gates

None — pure local execution against checked-in VN30 CSV + Phase 43 macro CSVs.

## Issues Encountered

None. Pre-flight regression 10/10 PASS, sweep ran clean to exit 0, D-18 NaN guard did not fire, artifacts verified, post-commit regression 10/10 PASS. The retain-v6.0 verdict is the scientific outcome of the sweep, not an execution issue.

## User Setup Required

None — the sweep is deterministic and reproducible from HEAD. Future runs:

```
uv run python analysis/walkforward_grid.py
```

Will regenerate `output/v10_grid_results.csv` byte-equivalently (modulo engine RNG non-determinism, which Phase 42 BASE-03 proves is zero per `tests/test_baseline_determinism.py`).

## Next Phase Readiness

- **Phase 46 (A/B + OOS Validation) — enters retain-v6.0 branch.** With no D-09-accepted macro filter configuration to promote, Phase 46's 5-scenario A/B report and OOS HARD gate will mechanically evaluate against the VN30_PRESET macro configuration. VAL-02's HARD gate (OOS MaxDD < -20% AND CAGR ≥ reconciled baseline) will either:
  1. **Reject v10.0** on the same grounds as Phase 45 (sub-baseline CAGR, which the grid search already proved) → VAL-05 writes the literal string `"v6.0 retained as production"` to `output/v10_validation_report.txt`, exit code 1 → Phase 47 DOC-03 runs (rejection audit only, DOC-01/02 skipped).
  2. **Or surface a narrower-than-grid-searched macro config** that passes — but the grid search swept the entire D-03 space, so this is not expected.
  Either way, Phase 46's planner should read this SUMMARY.md + the CSV before designing the A/B scenarios.
- **Phase 47 (Docs & Dashboard) — conditional execution.** On the expected retain-v6.0 outcome, Phase 47 runs DOC-03 (milestone audit capturing lessons learned) and skips DOC-01 (rules doc update) + DOC-02 (dashboard re-deploy). `project_best_model.md` memory stays pinned to v7.0 (CANSLIM+MDM) until a future milestone beats it.
- **Phase 45 is COMPLETE.** All 3 plans finished, all 3 WF-* requirements met (script exists + OOS-guarded + artifact published + decision gate provably inside the sweep).

## Lessons Learned

1. **Walk-forward CV inside the sweep caught an over-fit that post-hoc validation would have missed.** Phase 41's v9.0 lesson ("grid search must rolling-validate INSIDE the sweep, not after") played out textbook-perfectly: a macro filter that looks promising on 2015-2018 training CAGR (median 9.54%) degrades sharply on 2019-2024 eval years (median 4.57%), with median 54% degradation — far above the 30% gate. Had we only run a final OOS check, the 2025-2026 holdout might have passed by luck, and we'd have shipped a fragile model. The rolling-window discipline rejected the family at discovery.
2. **Macro-filter reduced per-year DD vs v6.0 baseline, but the CAGR cost was prohibitive.** Every single-year DD across 39 combos × 6 years was shallower than v6.0's -28.17% full-period DD. This confirms the MACRO thesis directionally (DXY/EEM/SBV signals DO dampen drawdowns) but the filter-induced CAGR erosion pushed every combo below the walk-forward acceptance bar. A future v11+ exploration might revisit with: (a) fractional sizing (deferred per Phase 44 D-05 — binary model preserved in v10), (b) different publication-lag assumptions, or (c) additional alpha sources (ALPHA-01 foreign flow, ALPHA-02 jump model from backlog).
3. **D-11 JSON's "no-fabricate-on-zero-accepted" guard proved its value.** The defensive `main()` logic that aborts JSON write when no stage has a winner prevented silently poisoning Phase 46. Without that guard, a naive consumer in Phase 46 would have loaded an empty/null winner config, run `dataclasses.replace(VN30_PRESET, **null_config)`, and produced nonsense A/B scenarios. Pattern worth preserving in future grid-search phases.

## Self-Check: PASSED

Files verified to exist:
- `output/v10_grid_results.csv` — FOUND (39 data rows, 19 851 bytes, force-added past gitignore)
- `output/v10_grid_best.json` — CORRECTLY ABSENT (main() guard fired as designed)
- `output/v10_grid_run.log` — FOUND locally (not committed, per planner intent)

Commits verified (git log):
- `4dd00a0` data(45-03): commit v10 walkforward sweep results -- 0/39 accepted, retain v6.0 — FOUND

Acceptance criteria (per plan):
- `test -f output/v10_grid_results.csv` exits 0 — PASS
- `test -f output/v10_grid_best.json` exits 0 — **intentionally FAIL** per approved retain-v6.0 interpretation (plan line 211 permits this outcome)
- CSV has 39 rows split 27/9/3 across stages — PASS (stage1_dxy=27, stage2_eem=9, stage3_all_three=3)
- CSV has all required columns (median_degradation, median_eval_cagr_pct, accepted, rejection_reason, cagr_train_pct) — PASS
- At least one accepted=True AND at least one accepted=False — **NOT MET** (0 True, 39 False). Documented as legitimate per plan line 211; acceptance criterion relaxed by approved retain-v6.0 checkpoint outcome.
- Script exit code 0 — PASS
- Post-commit regression suite 10/10 PASS — PASS (87s runtime)

Out-of-scope self-check (MUST all be NO):
- Did this plan modify `strategies/`? — NO
- Did this plan modify `analysis/walkforward_grid.py`? — NO (Plan 01 owns it)
- Did this plan add new tests? — NO (Plan 02 owns tests)
- Did this plan change `docs/` or `dashboard/`? — NO (Phase 47 territory)
- Did this plan touch `output/v10_reconciled_baseline.json`? — NO (read-only context)

---

*Phase: 45-walk-forward-grid-search*
*Completed: 2026-04-23*
