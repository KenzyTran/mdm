---
phase: 42-baseline-reconciliation
plan: 04
subsystem: engine
tags: [v60-strict-mode, mdm-hybrid, position-manager, baseline-reconciliation, preset-flag, cash-deterioration, elif-chain, feature-gate, d-07]

# Dependency graph
requires:
  - phase: 42-baseline-reconciliation (plan 42-03)
    provides: offending commit f80394f identified + D-11 ruled inapplicable, clearing the path for D-07 STEP 1 (revert) or STEP 2 (preset flag)
  - phase: 42-baseline-reconciliation (plan 42-01)
    provides: analysis/bisect_v10_baseline.py with BISECT_RESULT stdout contract and tight CAGR gate at 11.4, used as the step-by-step parity verifier in the waterfall
  - phase: 42-baseline-reconciliation (plan 42-02)
    provides: pinned phase-start ("bad") anchor 3601679cdba9c3ea674904e6f8a9aa24273cb6ad in docs/audits/v10_baseline_drift.md ## Bisect Endpoints — used as PHASE_START_HASH for the D-11 compliance diff
provides:
  - MDMV2Config.v60_strict_mode feature flag (bool = False) with explicit preset defaults in VN30_PRESET and NASDAQ_PRESET
  - Branch-guarded v6.0 flat-elif-chain restoration in V2PositionManager.process_day() (CASH→SELL block) — active only when v60_strict_mode=True
  - Reconciled-HEAD state where HybridEngine produces CAGR 11.4700 / SELL 124 / MaxDD -28.1700 on VN30 2015-2026, satisfying all three D-09 parity bands simultaneously
  - Reconciliation Outcome section of docs/audits/v10_baseline_drift.md populated with label `fixed_by_preset`, parity-check table, artifacts, and D-11 compliance statement (phase-start hash literal resolved)
  - docs/rules_mdm_hybrid.md Section XVIII documenting v60_strict_mode semantics, preset defaults, affected code shape, and Phase 44/45/46 downstream interactions (Code-Docs Sync Rule honored in same commit)
  - analysis/bisect_v10_baseline.py updated to set v60_strict_mode=True on the reconciliation-check preset via dataclasses.replace()
affects: [42-05 (baseline publisher — reads reconciled-HEAD CAGR 11.47/SELL 124/MaxDD -28.17 as the canonical tuple), 42-06 (determinism regression test — must run with v60_strict_mode=True per D-22), 44 (MACRO-04 parity regression uses reconciled-HEAD signal log as target — reconciled-HEAD runs strict mode), 45 (WF grid search baseline uses v60_strict_mode=True), 46 (VAL-02 HARD gate + VAL-04 byte-exact signal log regression — both gated on strict-mode reconciled baseline)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fix-forward waterfall STEP 1→STEP 2 fallback on non-self-contained revert: pure `git revert` that cleanly applies but breaks downstream callers (via kwarg removal) is recognized as non-self-contained per plan's STEP 1 exit rule and escalated to STEP 2 (preset flag) rather than committed as-is"
    - "Branch-guarded feature flag with `getattr(self.config, 'v60_strict_mode', False)` defensive access — resilient against old cached config objects without the field, relevant for Phase 44+ cross-preset compatibility"
    - "Parity check triad: all three D-09 bands verified simultaneously on one bisect-gate run (exit 0 + BISECT_RESULT parse) — no separate run needed per metric since compute_metrics computes all three at once"
    - "Code-Docs Sync Rule honored by staging config.py + rules_mdm_hybrid.md + impl file + caller + audit doc in ONE atomic commit — satisfies the 'same-commit' acceptance criterion for preset-flag additions that touch rule-documented behavior"

key-files:
  created: []
  modified:
    - "strategies/mdm_hybrid/config.py (added v60_strict_mode field to MDMV2Config + explicit =False in VN30_PRESET and NASDAQ_PRESET)"
    - "strategies/mdm_hybrid/position_manager.py (added branch-guarded elif arm in V2PositionManager.process_day() CASH-state block that restores the flat v6.0 elif chain when v60_strict_mode=True — no changes to fail-safe decision logic, D-11 verified)"
    - "analysis/bisect_v10_baseline.py (extended dataclasses.replace(VN30_PRESET, ...) to include v60_strict_mode=True on the reconciliation-check preset with inline Phase 42-04 annotation)"
    - "docs/rules_mdm_hybrid.md (added Section XVIII 'V60_STRICT_MODE (Phase 42 BASE-02, D-07 step 2)' with 7 subsections: background, config params, affected code, strict-vs-default table, backward compatibility, Phase 44/45/46 interactions, Phase 42 BASE-03 determinism)"
    - "docs/audits/v10_baseline_drift.md (populated Reconciliation Outcome section: bolded outcome header, strict Label line 'Label: \\`fixed_by_preset\\`', Path Taken narrative with STEP 1 attempt + escalation rationale, Parity Check table with all three bands PASS, Artifacts Produced, D-11 Compliance Statement with resolved phase-start hash 3601679cdba9c3ea674904e6f8a9aa24273cb6ad literal)"

key-decisions:
  - "Escalated from D-07 STEP 1 (selective git revert) to STEP 2 (v60_strict_mode preset flag) after discovering pure `git revert f80394f` would remove the `violation_threshold` kwarg from `process_day()` — which a later commit (d322a17) wired into the caller at mdm_hybrid_engine.py:412 via `process_day(..., violation_threshold=violation_threshold_val)`. Pure revert produces no merge conflict but would raise TypeError at runtime when ATR-buffer-enabled consumers invoke the engine. Per the plan's STEP 1 exit rule 'Revert is not self-contained → proceed to STEP 2', escalated without committing the revert."
  - "v60_strict_mode field defaults to False in MDMV2Config so that v7/v8/v9 test fixtures (phase38_backward_compat, phase39_backward_compat) remain green — the strict-mode path is opt-in for v10.0 macro baseline, determinism test, and bisect reconciliation check. Both VN30_PRESET and NASDAQ_PRESET set the field explicitly to False for self-documentation (rather than relying on the dataclass default), making the preset row grep-visible to plan 42-06 determinism test."
  - "Branch-guard placed as the FIRST sibling elif after the FTD arm in the CASH-state block (before the post-drift `elif self.config.ma50_sell_enabled and ma50 is not None:` arm). Ordering matters: v60_strict_mode=True must shortcut past the atr_buffer nested-if entirely. The two paths are mutually exclusive by design — strict mode intentionally ignores the ATR buffer feature to achieve v6.0 byte-parity in control flow. Documented in the strict-vs-default comparison table in rules_mdm_hybrid.md §XVIII.4."
  - "Used `getattr(self.config, 'v60_strict_mode', False)` instead of `self.config.v60_strict_mode` for defensive access — resilient against older config objects passed in from cached test fixtures or cross-preset conversions during Phase 44+. The `getattr` pattern mirrors the existing `getattr(self.config, 'atr_buffer_enabled', False)` in the same function (line 282 pre-fix), keeping the code style consistent."
  - "Audit-doc Label line written strictly per B2 contract: `Label: \\`fixed_by_preset\\`` on a single line, never the choice-expression `fixed_by_revert | fixed_by_preset | accepted_drift`. Plan 42-05 JSON schema enum binds to the three canonical literals; leaking the template choice-expression would trigger a ValueError downstream."

patterns-established:
  - "Preset-flag escalation from selective revert: when a `git revert` diff would break callers through kwarg-signature changes — even without merge conflicts — classify as non-self-contained and escalate to STEP 2 with a new MDMVxConfig field. Do NOT apply a mixed revert+fixup path (would split the drift story across two commits and complicate downstream bisect re-runs)."
  - "Same-commit Code-Docs Sync for feature-flag additions: `strategies/mdm_hybrid/config.py` + rule file + implementation file + caller (if any) + audit doc all staged atomically. The plan's acceptance-criteria grep `git log -n1 --format=%H -- config.py; git show --stat | grep rules_mdm_hybrid.md` enforces this and was passed."
  - "Reconciliation parity verification via the existing bisect gate (not a separate probe script): `uv run python analysis/bisect_v10_baseline.py` serves BOTH as the git-bisect runner (per-commit gate) AND as the post-fix parity verifier (HEAD probe). The BISECT_RESULT stdout contract carries all three D-09 metrics (cagr/sell/max_dd) in one line — parse once, verify all three bands. No need for a dedicated 'parity check' script."
  - "B2 strict Label line contract: canonical label literal appears EXACTLY ONCE in the audit doc inside backticks on a standalone `Label: \\`<label>\\`` line. Never the choice-expression. The regex `^Label: \\`(fixed_by_revert|fixed_by_preset|accepted_drift)\\`$` is the downstream parse target for plan 42-05's JSON schema writer."

requirements-completed: [BASE-02]

# Metrics
duration: 15min
completed: 2026-04-22
---

# Phase 42 Plan 04: Fix-Forward Waterfall (D-07) Summary

**v60_strict_mode feature flag (MDMV2Config) + branch-guarded flat-elif-chain in V2PositionManager.process_day() restore v6.0 CASH→SELL semantics, yielding CAGR 11.4700 / SELL 124 / MaxDD -28.1700 on VN30 2015-2026 — all three D-09 parity bands pass simultaneously.**

## Performance

- **Duration:** ~15 min (including 1 STEP 1 attempt + rollback before STEP 2 landing)
- **Started:** 2026-04-22T06:18:50Z
- **Completed:** 2026-04-22T06:33:13Z
- **Tasks:** 1 / 1
- **Files modified:** 5 (1 config, 1 engine code, 1 bisect script, 1 rule doc, 1 audit doc)

## Accomplishments

- **STEP 1 attempted (selective `git revert f80394f`):** Applied cleanly with no merge conflicts (`git revert --no-edit --no-commit` succeeded, `git diff --cached` showed `1 file changed, 4 insertions(+), 33 deletions(-)` — the expected mirror of the offending commit's `33 insertions(+), 4 deletions(-)`). However, inspection revealed the revert removes the `violation_threshold` kwarg from `process_day()`, which a later commit `d322a17` wired into the caller at `strategies/mdm_hybrid/mdm_hybrid_engine.py:412` via `process_day(..., violation_threshold=violation_threshold_val, ...)`. Pure revert would TypeError at runtime. Rolled back via `git reset HEAD` + `git checkout`; escalated to STEP 2 per the plan's STEP 1 exit rule.
- **STEP 2 landed (v60_strict_mode preset flag):** Added `v60_strict_mode: bool = False` to `MDMV2Config` (with a 10-line inline docstring citing f80394f, Phase 42 D-07, and the branch-guard semantics). Both `VN30_PRESET` (line 129 area) and `NASDAQ_PRESET` set the field to False explicitly. Added a single branch-guarded `elif getattr(self.config, 'v60_strict_mode', False):` arm as the FIRST sibling after the FTD arm in the CASH-state block of `V2PositionManager.process_day()` — the strict-mode block re-flattens the CASH→SELL elif chain to `if MA50 breakdown ... elif days_in_cash >= cash_deterioration_days ...`, restoring reachability of the cash_deterioration branch. `analysis/bisect_v10_baseline.py` updated to pass `v60_strict_mode=True` on the reconciliation-check preset via `dataclasses.replace`.
- **Parity verified at reconciled-HEAD (commit `784c8b8`):** `uv run python analysis/bisect_v10_baseline.py` returned exit 0 with `BISECT_RESULT: cagr=11.4700 sell=124 max_dd=-28.1700`. Deltas vs v6.0 reference: CAGR -0.03pp (inside ±0.3pp → [11.2, 11.8]), SELL 0 (inside ±5 → [119, 129]), MaxDD +0.03pp (inside ±1.0pp → [-29.2, -27.2]). All three D-09 bands pass simultaneously.
- **Code-Docs Sync Rule honored:** Single commit (`784c8b8`) contains `strategies/mdm_hybrid/config.py`, `strategies/mdm_hybrid/position_manager.py`, `analysis/bisect_v10_baseline.py`, `docs/rules_mdm_hybrid.md` (Section XVIII added with 7 subsections covering background, config, affected code, strict-vs-default table, backward compat, Phase 44/45/46 interactions, and Phase 42 BASE-03 determinism usage), and `docs/audits/v10_baseline_drift.md` (Reconciliation Outcome populated). Acceptance-criterion grep `git show --stat $PRESET_COMMIT | grep rules_mdm_hybrid.md` passed alongside the config.py grep.
- **D-11 compliance verified:** `git diff 3601679c..HEAD -- strategies/mdm_hybrid/position_manager.py | grep -iE "fail_safe_exit|fail_safe_enabled|fail_safe_threshold > 0|close > self.position.fail_safe"` returns empty. The only `fail_safe`-matching lines in the diff are two `fail_safe_threshold=prev_high` kwarg pass-throughs inside the new strict-mode branch's two `self.enter_sell(...)` calls — mirroring the existing non-strict branches and NOT modifying fail-safe decision logic. The audit doc's D-11 Compliance Statement embeds the literal phase-start hash `3601679cdba9c3ea674904e6f8a9aa24273cb6ad` (40-char hex, resolved from the plan's PRE-CHECK 0 via the audit doc's `## Bisect Endpoints` bad-anchor row).

## Task Commits

Each task was committed atomically:

1. **Task 1: Execute fix-forward waterfall (STEP 1 attempted + rolled back → STEP 2 landed) and populate Reconciliation Outcome** — `784c8b8` (feat)

_Note: Single-task plan with one atomic commit containing the full preset-flag fix (MDMV2Config field, branch-guard in position_manager.py, bisect script update, rules doc §XVIII, audit doc Reconciliation Outcome). STEP 1 revert was staged and rolled back pre-commit; only the STEP 2 landing is in the git log._

## Files Created/Modified

- `strategies/mdm_hybrid/config.py` (modified, +14 / -0) — added `v60_strict_mode: bool = False` field to `MDMV2Config` with 10-line inline docstring; added `v60_strict_mode=False` to `VN30_PRESET` and `NASDAQ_PRESET` for self-documentation.
- `strategies/mdm_hybrid/position_manager.py` (modified, +24 / -0) — added a branch-guarded `elif getattr(self.config, 'v60_strict_mode', False):` arm immediately after the `if is_ftd:` arm in the CASH-state block. The new arm holds a flat `if MA50 breakdown elif cash_deterioration` chain matching v6.0 control flow. No changes to fail-safe decision logic (SELL-state branch lines 336-352 byte-identical pre vs post).
- `analysis/bisect_v10_baseline.py` (modified, +4 / -0) — extended the `dataclasses.replace(VN30_PRESET, atr_buffer_enabled=False, refined_dd_enabled=False)` call to include `v60_strict_mode=True`, with an inline Phase 42-04 comment explaining the reconciliation-check semantics.
- `docs/rules_mdm_hybrid.md` (modified, +68 / -0) — added Section XVIII "V60_STRICT_MODE (Phase 42 BASE-02, D-07 step 2)" with 7 subsections covering: background/drift story, config parameter + preset defaults, affected code with branch-guard shape, strict-vs-default comparison table, backward compatibility with Phase 38/39 regression fixtures, Phase 44/45/46 downstream interactions, Phase 42 BASE-03 determinism usage.
- `docs/audits/v10_baseline_drift.md` (modified, +43 / -6) — replaced the `_To be populated by plan 42-04._` placeholder with a fully populated Reconciliation Outcome section: bold outcome header "**Reconciliation Outcome: Fixed by preset**", strict Label line `` `Label: \`fixed_by_preset\` `` (regex-compliant, single occurrence, no choice-expression leak), Path Taken narrative describing STEP 1 attempt + escalation rationale + STEP 2 landing, Parity Check table with live-measured values (CAGR 11.47 / SELL 124 / MaxDD -28.17) and per-band PASS verdicts, Artifacts Produced listing all 4 changed files + bisect verification line, D-11 Compliance Statement with literal 40-char phase-start hash `3601679cdba9c3ea674904e6f8a9aa24273cb6ad` embedded in the `git diff ... -- strategies/mdm_hybrid/position_manager.py` verification command.

## Decisions Made

- **Escalated STEP 1 → STEP 2 on non-self-contained revert.** See deviation #1 below. `git revert f80394f` applied cleanly (no merge conflicts, expected diff shape), but the revert removes kwargs that a later commit wired into the caller, producing a runtime TypeError instead of compile-time merge conflict. Plan's STEP 1 exit rule explicitly covers this case ("Revert is not self-contained → proceed to STEP 2") — escalated without committing the revert, preserving a clean single-commit fix story.
- **v60_strict_mode default=False (not True).** Preserving v7/v8/v9 default behavior means the existing `tests/test_phase38_backward_compat.py` and `tests/test_phase39_backward_compat.py` fixtures remain green without modification. v10.0 baseline consumers (Phase 42 determinism test per D-22, Phase 44 MACRO-04 parity regression, Phase 45 WF grid search baseline, Phase 46 VAL-02 HARD gate + VAL-04 byte-exact regression) opt in via `v60_strict_mode=True`. Both `VN30_PRESET` and `NASDAQ_PRESET` set the field to False explicitly for self-documentation, so the preset row grep-matches the acceptance-criterion check.
- **Branch-guard as FIRST elif after FTD, before the post-drift arm.** When `v60_strict_mode=True`, control must shortcut past the atr_buffer nested-if entirely. The two paths are mutually exclusive by design — strict mode intentionally ignores the ATR buffer feature to achieve v6.0 byte-parity in control flow. This is documented in §XVIII.4 strict-vs-default comparison table in `docs/rules_mdm_hybrid.md`.
- **Defensive `getattr(self.config, 'v60_strict_mode', False)` access.** Mirrors the existing `getattr(self.config, 'atr_buffer_enabled', False)` pattern in the same function — resilient against older config objects from cached test fixtures or cross-preset conversions in Phase 44+.
- **Single atomic commit for all 5 files.** Code-Docs Sync Rule enforces same-commit update of `config.py` + `rules_mdm_hybrid.md`. Staging the audit doc in the same commit keeps the single-commit fix story coherent for plan 42-05 (baseline publisher) which reads the audit doc's Reconciliation Outcome section.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] STEP 1 selective revert produced a non-self-contained diff; escalated to STEP 2**
- **Found during:** Task 1 (STEP 1 verification step — post-revert inspection)
- **Issue:** `git revert --no-edit --no-commit f80394f68b98925c47f0c66b9df1099576878ca0` applied cleanly (no merge conflicts, diff shape matches expected mirror of offending commit: 4 insertions / 33 deletions). However, the revert removes the `violation_threshold: float = None` kwarg from `V2PositionManager.process_day()`'s signature. A later commit (`d322a17`, per the Bisect Log in `docs/audits/v10_baseline_drift.md ## Bisect Log`) wired this kwarg into the caller at `strategies/mdm_hybrid/mdm_hybrid_engine.py:412` via `process_day(..., violation_threshold=violation_threshold_val, ...)`. A pure revert therefore produces a runtime `TypeError: process_day() got an unexpected keyword argument 'violation_threshold'` when the ATR-buffer feature surface is exercised by any caller holding the d322a17-wired engine binary.
- **Fix:** Per the plan's STEP 1 exit rule at line 160 ("If `git revert` produces merge conflicts, abort: `git revert --abort`. Revert is not self-contained → proceed to STEP 2"), rolled back the staged revert (`git reset HEAD strategies/mdm_hybrid/position_manager.py` + `git checkout strategies/mdm_hybrid/position_manager.py`) and escalated to STEP 2 (v60_strict_mode preset flag). Verified working tree clean via `git diff strategies/mdm_hybrid/position_manager.py | head -5` returning empty before editing. The escalation preserves ATR-buffer caller compatibility (default False = no-op for existing consumers) while restoring v6.0 parity when strict-mode is opted in.
- **Files modified:** None (the STEP 1 attempt was staged only and rolled back before any commit; see `git log --oneline $PHASE_START_HASH..HEAD -- strategies/mdm_hybrid/position_manager.py` — only `784c8b8` appears, the STEP 2 commit).
- **Verification:** Parity re-verification post-STEP-2 landing: `uv run python analysis/bisect_v10_baseline.py` returned exit 0 with `BISECT_RESULT: cagr=11.4700 sell=124 max_dd=-28.1700`. All three D-09 parity bands pass simultaneously.
- **Committed in:** Not separately committed — the STEP 1 attempt is an ephemeral working-tree state that was rolled back. The plan's STEP 2 landing is committed atomically in `784c8b8`. The STEP 1 rationale is captured in the audit doc's Path Taken narrative so downstream reviewers can reconstruct the escalation reasoning without needing access to git reflog.

---

**Total deviations:** 1 auto-fixed (1 blocking via STEP 1→STEP 2 escalation)
**Impact on plan:** The plan explicitly anticipated this escalation path ("Revert is not self-contained → proceed to STEP 2"). No scope creep — all work landed in the planned waterfall branches, just at STEP 2 instead of STEP 1. The single-commit preset-flag fix is cleaner than a two-commit revert+fixup alternative would have been, and preserves the ATR-buffer feature surface for v7/v8/v9 consumers (default False is a no-op). The STEP 1 attempt itself was informative: it confirmed f80394f is structurally self-contained at the VCS diff level but non-self-contained at the caller-contract level — a useful distinction for future BASE-class phases considering pure-revert fixes.

## Issues Encountered

- **Plan's PRE-CHECK 1 D-11 grep yielded 6 false-positive matches on context lines** (`fail_safe_threshold: float = 0.0`, `prev_high: High of previous day (for fail-safe threshold)`, kwargs named `fail_safe_threshold=prev_high`). Plan 42-03 already adjudicated D-11 inapplicable for f80394f (commit touches CASH→SELL branches, NOT the fail-safe decision logic). Re-verified with a more specific grep on DECISION-LOGIC patterns (`fail_safe_exit|fail_safe_enabled|fail_safe_threshold > 0|close > self.position.fail_safe`) which returned 0 matches — D-11 clear. Documented the distinction in the audit doc's D-11 Compliance Statement narrative so future BASE-class audits can reuse the pattern without needing to redo the false-positive filtering.

## User Setup Required

None — pure engine refactor + config flag + docs update. No external service, credential, or environment changes required. `uv run python analysis/bisect_v10_baseline.py` is the verification command (no user setup to run it).

## Next Phase Readiness

**Ready for plan 42-05 (Publish Reconciled Baseline):**
- Reconciled-HEAD committed at `784c8b8`. Canonical tuple inputs (CAGR 11.4700, SELL 124, MaxDD -28.1700) already captured in the audit doc's Parity Check table — plan 42-05 can read the literal numbers directly without re-running the engine if desired, or re-run `uv run python analysis/bisect_v10_baseline.py` for freshness.
- Reconciliation Outcome section populated with the strict Label line `Label: \`fixed_by_preset\`` — plan 42-05's JSON schema writer can grep this line unambiguously and emit `reconciliation_outcome: "fixed_by_preset"` in `output/v10_reconciled_baseline.json` per D-12/D-13.
- Full canonical tuple (18 fields per D-12) still needs to be computed by plan 42-05 — the bisect gate only emits CAGR/SELL/MaxDD. Plan 42-05 will invoke `analysis.validate_v9.compute_metrics()` on a fresh HybridEngine run with `v60_strict_mode=True` to fill in sharpe_rf3, transitions, buy_pct/cash_pct/sell_pct, ma50_breakdown_sell_share, buy_count, and env version fields.

**Ready for plan 42-06 (Determinism Regression Test):**
- `v60_strict_mode=True` is the canonical preset for the determinism test per D-22. Plan 42-06 can import `VN30_PRESET` and apply `dataclasses.replace(VN30_PRESET, v60_strict_mode=True)` (same pattern the bisect script uses) to configure the test fixture.
- Both determinism test functions (`test_numeric_variance_across_3_runs` and `test_signal_log_byte_exact`) will operate on the strict-mode engine — the deterministic-by-construction nature of the strict-mode branch-guard (no randomness, no dict iteration order, no pandas reorder-prone ops) means both tests should pass by design. If they don't, the non-determinism is pre-existing in the HybridEngine machinery (dd_counter, rally_tracker, ftd_detector, or the indicator pipeline) and is a separate bug unrelated to the strict-mode fix.

**Concerns passed forward:**
- Phase 44 MACRO-04 parity regression will compare `macro_filter_enabled=False` signal log to the reconciled-HEAD signal log (both with `v60_strict_mode=True`). Plan 44 planner should read §XVIII.6 of `docs/rules_mdm_hybrid.md` to understand the strict-mode semantics before wiring the test.
- The fail-safe logic remains untouched (D-11). Future phases considering any modification to `V2PositionManager.fail_safe_exit()`, `_check_fail_safe`-equivalent code in the SELL-state branch, or the `hasattr(self.config, 'fail_safe_enabled') and ... and close > self.position.fail_safe_threshold` check must do so via a NEW phase-context proposal — not as a drift-fix.
- ATR-buffer and v60_strict_mode are mutually exclusive by design (strict mode ignores atr_buffer). If a future phase needs both simultaneously (unusual — ATR buffer is the post-drift replacement for MA50 breakdown), a third config flag would be needed; the current dichotomy is intentional for clarity.

## Self-Check: PASSED

Artifact and commit existence verified:
- FOUND: `strategies/mdm_hybrid/config.py` (modified)
- FOUND: `strategies/mdm_hybrid/position_manager.py` (modified)
- FOUND: `analysis/bisect_v10_baseline.py` (modified)
- FOUND: `docs/rules_mdm_hybrid.md` (modified)
- FOUND: `docs/audits/v10_baseline_drift.md` (modified)
- FOUND: commit `784c8b8` in `git log --oneline --all` (feat(42-04) preset flag)

Acceptance-criteria block from plan (all 13 checks):
- CK1 `## Reconciliation Outcome` header: PASS (1 match)
- CK2 `**Reconciliation Outcome:` bold outcome header: PASS (1 match)
- CK3 `_To be populated by plan 42-04._` placeholder removed: PASS (0 matches)
- CK4 (B2 strict) `^Label: \`...\`$` exactly 1: PASS (1 match)
- CK5 (B2 no-choice-leak) `fixed_by_revert | fixed_by_preset` absent: PASS (0 matches)
- CK6 `### Parity Check (D-09 thresholds)` header: PASS (1 match)
- CK7 `### D-11 Compliance Statement` header: PASS (1 match)
- CK8 `<phase-start-hash>` placeholder removed: PASS (0 matches)
- CK9 40-char-hex D-11 grep command: PASS (1 match)
- CK10 `v60_strict_mode: bool = False` in config.py: PASS (1 match)
- CK11 `v60_strict_mode=False` preset explicit values: PASS (2 matches — both VN30_PRESET and NASDAQ_PRESET)
- CK12 `v60_strict_mode=True` in bisect script: PASS (2 matches — param + docstring)
- CK13 (m1 Code-Docs Sync) `v60_strict_mode` in rules doc: PASS (10 matches)
- CK14 (m1 Same-commit) config.py + rules_mdm_hybrid.md in one commit: PASS (commit `784c8b8` contains both)
- CK15 (M4 D-11 runtime) `git diff PSH..HEAD -- position_manager.py | grep -iE "fail_safe_exit|fail_safe_enabled|..." ` empty: PASS (empty output)

Parity verification at committed HEAD `784c8b8`: `BISECT_RESULT: cagr=11.4700 sell=124 max_dd=-28.1700` (exit 0). All three D-09 bands pass.

---
*Phase: 42-baseline-reconciliation*
*Completed: 2026-04-22*
