---
phase: 42-baseline-reconciliation
plan: 03
subsystem: audit
tags: [git-bisect, drift-forensics, cagr, position-manager, atr-buffer, phase-38, baseline-reconciliation]

# Dependency graph
requires:
  - phase: 42-baseline-reconciliation (plan 42-01)
    provides: analysis/bisect_v10_baseline.py (the CAGR gate script + BISECT_RESULT stdout contract + D-04 skip-untestable semantics)
  - phase: 42-baseline-reconciliation (plan 42-02)
    provides: docs/audits/v10_baseline_drift.md pinned bisect endpoints (good=37cfdc2, bad=3601679) + placeholder scaffolding for Bisect Log and Root-Cause Narrative
  - phase: 41-ab-walk-forward-validation
    provides: analysis/validate_v9.py::compute_metrics (inlined into /tmp wrapper so gate works on commits predating Phase 41)
provides:
  - Identified offending commit f80394f (Phase 38-02) as the single-commit source of CAGR 11.47→10.70 drift
  - Full bisect log with 8 tested commits + verdicts in docs/audits/v10_baseline_drift.md
  - Root-cause narrative (3.8k non-whitespace chars) explaining the inadvertent elif-chain reparent that broke disabled-path parity
  - D-11 applicability ruling: offending commit does NOT touch fail-safe, so eligible for D-07 step-1 selective revert in plan 42-04
  - Self-contained /tmp/bisect_v10_gate.py pattern — inline compute_metrics enables bisect across commits that predate its originating analysis module
affects: [42-04 (reconciliation decision — selective revert is the top candidate), 42-05 (reconciled baseline consumer), 43-47 (downstream v10.0 phases reading output/v10_reconciled_baseline.json)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Self-contained /tmp-resident bisect gate: copy script to /tmp, inline downstream-introduced dependencies (compute_metrics), use os.getcwd() for sys.path — survives git checkouts of old commits where the script itself does not yet exist"
    - "Stash-before-bisect ritual: stash tracked modifications before `git bisect start` to avoid mid-bisect checkout conflicts on uv.lock / plan files; pop after `git bisect reset`"
    - "Monotone-trajectory assertion in Bisect Log: explicit statement in narrative (not just table implication) so reviewers don't need to reason about segment re-run semantics"

key-files:
  created: []
  modified:
    - docs/audits/v10_baseline_drift.md (populated Bisect Log table + Root-Cause Narrative; 116 insertions, 7 deletions replacing the two _To be populated_ placeholders)

key-decisions:
  - "Inlined compute_metrics into the /tmp wrapper script rather than gating on Phase 41 commits: without this, bisect skips all Phase 28-40 commits (where validate_v9.py does not yet exist) and cannot converge. This is a Rule 3 auto-fix to the bisect gate's dependency surface, not a deviation from the plan's investigative intent."
  - "Used stash-before-bisect pattern: phase 42 plan edits + config.json were uncommitted and would have blocked mid-bisect checkouts; stashed tracked-only (kept untracked files in place) before `git bisect start`, popped after `git bisect reset`. HEAD verified restored to c708ff0 before commit."
  - "Applied D-05 monotone-trajectory exit: all 4 goods in the bisect log chronologically precede all 4 bads (trajectory is strictly monotone along the 8-commit tested surface), so no segment re-runs required. Stated this explicitly in the narrative to satisfy the m2 acceptance criterion."
  - "Applied D-11 ruling: f80394f modifies strategies/mdm_hybrid/position_manager.py in the CASH→SELL MA50-breakdown / cash-deterioration branches, NOT the fail-safe (_check_fail_safe) branch. Therefore fail-safe-restriction does NOT apply; plan 42-04 can use D-07 step-1 (selective revert) without violating D-11."

patterns-established:
  - "Bisect Log table schema: `commit_hash | date | author | subject | cagr_pct | sell_count | max_dd_pct | verdict` with verdict ∈ {good, bad, skip (untestable), bad (segment-N)} — downstream audits reproducing this pattern should match column order"
  - "Offending-commit callout block: short_hash header, full_hash, date, author, parent-comparison context, CAGR/SELL/MaxDD deltas with arithmetic, diff stat verbatim. Enables grep-greppable forensics"
  - "Root-Cause Narrative structure: Files Changed → Semantic Change (before/after code snippets) → Why CAGR drifted (quantitative explanation) → Intent Assessment (inadvertent vs deliberate) → D-11 applicability → Downstream Propagation. This structure will be reused by other BASE-01-class phase audits"

requirements-completed: [BASE-01]

# Metrics
duration: ~25min
completed: 2026-04-21
---

# Phase 42 Plan 03: Run Bisect + Populate Audit Log Summary

**`git bisect` converged in 8 iterations on commit `f80394f` (Phase 38-02) as the single source of the CAGR 11.47→10.70 drift — a position_manager.py refactor that inadvertently reparented the `close < ma50` test from an elif condition into a nested if, silently making the subsequent cash-deterioration SELL elif unreachable whenever the engine had a valid MA50.**

## Performance

- **Duration:** ~25 min (including 2 bisect restarts to iterate on the gate script's cwd/module-path + inlined-compute_metrics auto-fixes)
- **Started:** 2026-04-21T10:25:00Z
- **Completed:** 2026-04-21T10:50:00Z
- **Tasks:** 1 / 1
- **Files modified:** 1 (`docs/audits/v10_baseline_drift.md`)

## Accomplishments

- **Identified offending commit `f80394f68b98925c47f0c66b9df1099576878ca0`** — `feat(38-02): add atr_buf_below_count to V2Position and wire m-day streak in process_day`. Per-commit CAGR impact: 11.47 → 10.70 (-0.77pp); SELL count 124 → 105 (-19); MaxDD -28.17 → -28.63 (-0.46pp). All three deltas match the measured-today drift in `output/v9_ab_comparison.txt` exactly (CAGR 10.70, SELL 105, MaxDD -28.63), confirming the drift is a single-commit event with no subsequent restoration across the 250 commits between f80394f and HEAD.
- **Populated the Bisect Log table** with 8 tested commits (4 good, 4 bad — trajectory monotone, no segment re-runs required per D-05). Each row carries `commit_hash | date | author | subject | cagr_pct | sell_count | max_dd_pct | verdict` so plan 42-04 can reason about the bisect surface without re-reading `/tmp/bisect_run.log`.
- **Wrote a 3829-char Root-Cause Narrative** explaining the semantic change: the commit's refactor replaced a flat elif chain (`elif ma50_sell_enabled and ma50 is not None and close < ma50`) with an outer-elif/nested-if pattern (`elif ma50_sell_enabled and ma50 is not None:` → `if close < ma50: ...`). The outer elif takes ownership of the elif chain on every day MA50 is not None, so the subsequent `elif days_in_cash >= cash_deterioration_days` becomes unreachable when `close >= ma50` — eliminating 19 cash-deterioration SELLs that the v6.0 baseline fired. Commit message's "byte-identical to original v6.0" parity claim is thus incorrect.
- **Ruled D-11 inapplicable:** f80394f touches the CASH→SELL MA50-breakdown / cash-deterioration branches, NOT the fail-safe logic. Plan 42-04 can use D-07 step-1 (selective revert) without violating the "no fail-safe changes" invariant.
- **Verified clean branch restore:** HEAD at plan end is `c708ff0`, identical to pre-bisect saved hash. `git bisect log` shows `not bisecting any more` — no dangling bisect state.

## Task Commits

Each task was committed atomically:

1. **Task 1: Execute git bisect with CAGR gate, append every tested commit to Bisect Log table** — `a7e21e8` (docs)

_Note: Single-task plan; atomic doc-only commit. No engine code modified (only forensic updates to the audit doc)._

## Files Created/Modified

- `docs/audits/v10_baseline_drift.md` (modified, +116 / -7) — replaced both `_To be populated by plan 42-03._` placeholders. `## Bisect Log` section now contains the 8-row table + offending-commit callout + monotone-trajectory statement. `## Root-Cause Narrative` section now contains the 6-subsection root-cause analysis (Files Changed / Semantic Change / Why CAGR drifted / Intent Assessment / D-11 applicability / Downstream Propagation).

## Decisions Made

- **Inlined `compute_metrics` into the /tmp-resident gate wrapper.** See deviation #1 below. Plan's original script (`analysis/bisect_v10_baseline.py`) imports `analysis.validate_v9.compute_metrics`, but `validate_v9.py` was only introduced in Phase 41 (commit 481d5873). Without inlining, every Phase 28-40 commit skipped with `ModuleNotFoundError: No module named 'analysis.validate_v9'`, preventing bisect convergence on a pre-Phase-41 drift. The inlined version is byte-equivalent in the metric fields bisect depends on (cagr_pct, sell_count, max_dd_pct).
- **Used the pinned bad anchor `3601679` rather than current HEAD `c708ff0` as the bisect bad.** Commits between 3601679 and c708ff0 are pure infrastructure (added bisect script + seeded audit doc) and cannot affect engine CAGR. Using the pinned anchor matches plan 42-02's invariant and gives downstream readers a stable reference.
- **Stashed tracked modifications before `git bisect start`.** Phase 42 plan edits in the working tree would have blocked mid-bisect checkouts. Stashed tracked files (keeping untracked files in place), then popped after `git bisect reset`. Alternative of committing first was rejected because the plan edits were work-in-progress for plans 42-04/05/06, not finalized.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed `os.path.dirname(__file__)` sys.path bug in /tmp-resident gate wrapper**
- **Found during:** Task 1 (first bisect attempt) — all 5 commits tested skipped with `ModuleNotFoundError: No module named 'core'` despite `core/` existing at those commits.
- **Issue:** `analysis/bisect_v10_baseline.py` uses `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))` to locate the repo root. When the script is copied to `/tmp/bisect_v10_gate.py` (necessary to survive `git bisect`'s checkouts of commits where the script itself doesn't exist), `__file__` resolves to `/tmp/bisect_v10_gate.py` and the parent is `/tmp/` — not the repo. Every import of `core.*` then fails. Bisect marked all 5 initial commits as `skip` before running out of untestable history and aborting.
- **Fix:** Replaced the `os.path.dirname(__file__)`-based parent-computation with `os.getcwd()`. During `git bisect run`, cwd is always the repo root (bisect runs commands from the repo), so `sys.path.insert(0, os.getcwd())` correctly points at the checked-out tree.
- **Files modified:** `/tmp/bisect_v10_gate.py` (local wrapper only — the repo copy `analysis/bisect_v10_baseline.py` retains the `__file__`-based path since it's always invoked in-place where that pattern works)
- **Verification:** Re-invoked `uv run python /tmp/bisect_v10_gate.py` after a `git bisect` checkout of 427064a → `BISECT_RESULT: cagr=11.4700 sell=124 max_dd=-28.1700` (exit 0). Import now succeeds.
- **Committed in:** Not separately committed — the /tmp wrapper is a bisect-session ephemeral. The pattern is documented in this SUMMARY's key-decisions for future BASE-class phases to adopt.

**2. [Rule 3 - Blocking] Inlined `compute_metrics` into /tmp wrapper to unblock pre-Phase-41 commits**
- **Found during:** Task 1 (second bisect attempt) — after fix #1, bisect still skipped ~239/256 commits with `ModuleNotFoundError: No module named 'analysis.validate_v9'`.
- **Issue:** `analysis/validate_v9.py` was introduced in Phase 41-01 (commit 481d5873). Every commit in the bisect range that predates Phase 41 — which is the majority of the range since v6.0 ship was in Phase 27 — lacks this module. The gate's `from analysis.validate_v9 import compute_metrics` line therefore ImportErrors on every Phase 28-40 commit, sending them to the skip path and making convergence impossible if the drift is pre-Phase-41.
- **Fix:** Copied `compute_metrics()` body (lines 125-203 of `analysis/validate_v9.py`) into the /tmp wrapper as `_compute_metrics_inline()`. Only the three fields bisect actually consumes (`cagr_pct`, `max_dd_pct`, `sell_count`) are computed — the other 8 fields from the full compute_metrics (sharpe_rf3, transitions, ma50_breakdown_sell_share, etc.) are omitted since the bisect gate doesn't read them. Same state[i-1] equity formula, same rounding, same SELL-count pattern match.
- **Files modified:** `/tmp/bisect_v10_gate.py` (local wrapper)
- **Verification:** Post-fix bisect converged in 8 iterations (no skips inside the converging range — the 4 good + 4 bad commits all have strategies/mdm_hybrid present by Phase 38). Final `git bisect` output: `f80394f68b98925c47f0c66b9df1099576878ca0 is the first bad commit`. All acceptance-criteria grep patterns returned PASS.
- **Committed in:** Not separately committed — same reason as fix #1 (ephemeral /tmp wrapper).

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes were essential for bisect convergence — without them, the gate would have skipped the majority of commits and bisect would have aborted with "We cannot bisect more" (which is exactly what happened in the first attempt). The auto-fixes preserve the plan's investigative intent (find the earliest CAGR drift via bisect) by making the gate script work across the full historical commit surface instead of only post-Phase-41 commits. No change to the repo copy `analysis/bisect_v10_baseline.py` — the fixes live in the ephemeral /tmp wrapper; the repo script is correct for in-place invocation. The root-cause finding (f80394f as the offending commit) is unaffected by how the gate was run — bisect's correctness depends only on good/bad verdicts at each step, not on the implementation path of compute_metrics.

## Issues Encountered

- **Bisect's first run aborted mid-convergence on a `uv.lock` checkout conflict.** The gate script invokes `uv run` during some test paths (original version); `uv` modifies `uv.lock` as a side effect of its first invocation on an old commit, leaving the working tree dirty. Bisect then failed to check out the next commit. Switched to direct `.venv/Scripts/python.exe` invocation (bypassing `uv run`) to avoid the lock mutation. Documented in decisions — other Phase 42 plans running across history should use the direct venv python path for the same reason.
- **Stashing tracked modifications before bisect:** The plan didn't explicitly call out the stash-before-bisect ritual. Applied it proactively because the working tree had 5 tracked-but-modified plan files that would have blocked bisect. Pattern added to key-decisions for the benefit of future BASE-class phases.

## User Setup Required

None — pure forensic audit. No external service or credential changes required.

## Next Phase Readiness

**Ready for plan 42-04 (Reconciliation Decision):**
- Offending commit identified: `f80394f`. Single-file, 33-line-diff refactor of `strategies/mdm_hybrid/position_manager.py`.
- D-11 explicitly ruled **inapplicable** (no fail-safe touched). D-07 step-1 **selective revert** is the top candidate path.
- Parent commit `b7c1f63` recorded as the "desired post-revert state" with CAGR 11.47 / SELL 124 / MaxDD -28.17 — well within the D-09 parity band of 11.2–11.8 CAGR, ±5 SELL count of 124, ±1.0pp MaxDD of -28.2.
- If plan 42-04 chooses selective revert: must add a regression test that fails pre-revert and passes post-revert, so the ATR-04 parity claim becomes enforceable. The absence of such a test at the original f80394f merge time is the class of bug Phase 42 BASE-03 is designed to catch going forward (though BASE-03 tests determinism, not parity — a parity-regression test is a distinct artifact).
- If plan 42-04 chooses the preset-flag path (D-07 step 2): add `v60_strict_mode: bool = False` to `MDMV2Config` that branch-guards the nested-if back to a flat elif.
- If plan 42-04 chooses accept-and-document (D-07 step 3): the audit doc's `## Reconciliation Outcome` section must open with the literal string `**Reconciliation Outcome: Accepted drift, not fixed**` (already scaffolded in plan 42-02 seed).

**Concerns passed forward:**
- ATR-04 backward-compat invariant (Phase 38-CONTEXT.md) was a load-bearing claim that no regression test validated. Plan 42-04 should emit a regression test regardless of which D-07 path it takes, to re-enforce ATR-04 going forward.
- Phase 39 `refined_dd_enabled` may have the same class of bug (untested feature-gate parity claim). Out of scope for plan 42-04 but candidate for quick follow-up — the /tmp wrapper pattern in this summary is directly reusable for a second bisect on that feature gate if plan 42-04's reviewers want comfort.

## Self-Check: PASSED

Artifact and commit existence verified:
- FOUND: `docs/audits/v10_baseline_drift.md` (modified, 116+ / 7- vs parent)
- FOUND: commit `a7e21e8` in `git log --oneline --all`

Acceptance-criteria block from plan (all 9 checks):
- CK1 offending-commit header: PASS
- CK2 table header: PASS
- CK3 table-rows (8 >= 3): PASS
- CK4 placeholders removed (0 occurrences of `_To be populated by plan 42-03._`): PASS
- CK5 bisect reset verified (`not bisecting any more` in `git bisect log`): PASS
- CK6 monotone/segment (matches `trajectory.*monotone.*no segment re-runs`): PASS
- CK7 cagr-delta line present: PASS
- CK8 diff-summary section present: PASS
- CK9 root-cause narrative header present: PASS

Root-Cause Narrative length: 3829 non-whitespace characters (>> 200 minimum).
HEAD restoration: `c708ff00f55bd58428f5658ffe95c6621c278903` — identical to pre-bisect saved hash.

---
*Phase: 42-baseline-reconciliation*
*Completed: 2026-04-21*
