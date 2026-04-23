---
phase: 44
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
autonomous: true
requirements: [MACRO-05]
must_haves:
  truths:
    - "ROADMAP.md §Phase 44 success criterion 5 reflects the D-05 rewrite (stop-loss tightening, NOT half-position/full CASH)"
    - "REQUIREMENTS.md MACRO-05 reflects the D-05 rewrite with the new 6 threshold field names"
    - "Old text 'sbv_tightening_position_frac' no longer appears in either doc"
    - "Phase 45 planner reading REQUIREMENTS.md gets the correct (rewritten) MACRO-05 text"
  artifacts:
    - path: ".planning/ROADMAP.md"
      provides: "Updated Phase 44 success criterion 5"
      contains: "dxy_easing_z_threshold"
    - path: ".planning/REQUIREMENTS.md"
      provides: "Rewritten MACRO-05 line"
      contains: "sbv_tightening_stop_loss_max_multiplier"
  key_links:
    - from: ".planning/ROADMAP.md"
      to: ".planning/REQUIREMENTS.md"
      via: "Both docs carry the same 6 threshold field names per D-05"
      pattern: "dxy_easing_z_threshold.*dxy_tightening_z_threshold.*eem_easing_z_threshold.*eem_tightening_z_threshold.*dxy_tightening_dd_threshold.*sbv_tightening_stop_loss_max_multiplier"
---

<objective>
Atomic doc-only rewrite of the MACRO-05 specification per CONTEXT.md D-05. ROADMAP.md §Phase 44 success criterion 5 AND REQUIREMENTS.md MACRO-05 are updated in this single plan, in a separate doc-only commit landed BEFORE any code work.

Purpose: Engine binary model is preserved (no fractional sizing); MACRO-05 is rewritten to describe the actual implementation (DXY easing VETOes SELL, DXY tightening lowers DD threshold, SBV tightening shrinks stop_loss_max_multiplier). This plan lands first so Phase 45 planning (which reads REQUIREMENTS.md) cannot race on stale text. Per RESEARCH.md Open Question 4 (recommendation: SEPARATE doc-only commit, landed FIRST).

Output: 2 doc files updated with grep-verifiable text.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/44-macro-filter-module/44-CONTEXT.md
@.planning/phases/44-macro-filter-module/44-RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite ROADMAP.md Phase 44 success criterion 5 per D-05</name>
  <files>.planning/ROADMAP.md</files>
  <read_first>
    - .planning/ROADMAP.md (read lines 843-854 — current Phase 44 entry to know exact line of SC-5)
    - .planning/phases/44-macro-filter-module/44-CONTEXT.md §D-05 (the verbatim before/after text)
  </read_first>
  <action>
    Open `.planning/ROADMAP.md` and locate Phase 44 success criterion 5 (currently line 852). Replace the EXACT current text:

    BEFORE (current line 852):
    ```
      5. Filter policy is implemented: DXY easing suppresses SELL, DXY tightening amplifies SELL, SBV tightening regime forces half-position or full CASH; exact thresholds (`dxy_z_threshold`, `sbv_tightening_position_frac`) are exposed as config fields ready for the Phase 45 grid search
    ```

    AFTER (new line 852):
    ```
      5. Filter policy is implemented: DXY easing VETOes SELL, DXY tightening lowers the effective DD threshold, SBV tightening shrinks `stop_loss_max_multiplier`; exact thresholds (`dxy_easing_z_threshold`, `dxy_tightening_z_threshold`, `eem_easing_z_threshold`, `eem_tightening_z_threshold`, `dxy_tightening_dd_threshold`, `sbv_tightening_stop_loss_max_multiplier`) are exposed as config fields ready for the Phase 45 grid search (per Phase 44 D-05 — engine binary model preserved, fractional sizing deferred to v11+)
    ```

    Do NOT modify any other line in the Phase 44 entry (Goal line 844, Depends on line 845, Requirements line 846, criteria 1-4 lines 848-851, Plans line 853, Canonical refs line 854 all stay intact). Do NOT modify Phase 45/46/47 entries.
  </action>
  <verify>
    <automated>grep -c "dxy_easing_z_threshold" .planning/ROADMAP.md | grep -q "^[1-9]" && grep -c "sbv_tightening_position_frac" .planning/ROADMAP.md | grep -q "^0$" && grep -c "sbv_tightening_stop_loss_max_multiplier" .planning/ROADMAP.md | grep -q "^[1-9]" && echo PASS</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "dxy_easing_z_threshold" .planning/ROADMAP.md` returns at least 1
    - `grep -c "sbv_tightening_stop_loss_max_multiplier" .planning/ROADMAP.md` returns at least 1
    - `grep -c "sbv_tightening_position_frac" .planning/ROADMAP.md` returns 0 (old text removed)
    - `grep -c "forces half-position or full CASH" .planning/ROADMAP.md` returns 0 (old text removed)
    - `grep -c "VETOes SELL" .planning/ROADMAP.md` returns at least 1
    - `grep -n "### Phase 44: Macro Filter Module" .planning/ROADMAP.md` returns line 843 (header position unchanged)
    - `grep -n "### Phase 45: Walk-Forward Grid Search" .planning/ROADMAP.md` returns line 856 (downstream phase header unchanged — confirms no line shifts beyond the in-place rewrite)
    - All 6 threshold names present: `grep -c -E "(dxy_easing_z_threshold|dxy_tightening_z_threshold|eem_easing_z_threshold|eem_tightening_z_threshold|dxy_tightening_dd_threshold|sbv_tightening_stop_loss_max_multiplier)" .planning/ROADMAP.md` returns at least 6
  </acceptance_criteria>
  <done>ROADMAP.md SC-5 reflects the D-05 rewrite; old text strings removed; all 6 threshold field names present.</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite REQUIREMENTS.md MACRO-05 per D-05</name>
  <files>.planning/REQUIREMENTS.md</files>
  <read_first>
    - .planning/REQUIREMENTS.md (read lines 22-26 to confirm exact MACRO-05 line)
    - .planning/phases/44-macro-filter-module/44-CONTEXT.md §D-05 (the verbatim before/after text)
  </read_first>
  <action>
    Open `.planning/REQUIREMENTS.md` and locate the MACRO-05 line (currently line 26). Replace the EXACT current text:

    BEFORE (current line 26):
    ```
    - [ ] **MACRO-05**: Filter policy — DXY easing suppresses SELL, DXY tightening amplifies SELL, SBV tightening regime forces half-position or full CASH (exact thresholds `dxy_z_threshold`, `sbv_tightening_position_frac` grid-searched in WF-01)
    ```

    AFTER (new line 26):
    ```
    - [ ] **MACRO-05**: Filter policy — DXY easing VETOes SELL, DXY tightening lowers the effective DD threshold, SBV tightening shrinks `stop_loss_max_multiplier` (exact thresholds `dxy_easing_z_threshold`, `dxy_tightening_z_threshold`, `eem_easing_z_threshold`, `eem_tightening_z_threshold`, `dxy_tightening_dd_threshold`, `sbv_tightening_stop_loss_max_multiplier` grid-searched in WF-01; engine binary model preserved per Phase 44 D-05/D-06, fractional sizing deferred to v11+)
    ```

    Do NOT modify MACRO-01..04 (lines 22-25), do NOT touch the Traceability table (lines 76-99), do NOT touch Coverage section (lines 101-112). Do NOT update line 116 ("Last updated") — Phase 44 commits will update this naturally via git when the phase completes (separate concern).

    Per CONTEXT.md D-05 the rewrite "piggy-backs on the phase completion (not a separate phase)" — this Plan 01 is the doc-only piggy-back, landing FIRST in the wave order so Phase 45 planning reads the correct text. Per RESEARCH.md Open Question 4 recommendation, this is a SEPARATE commit from the code changes (Plan 02-04 commit code).
  </action>
  <verify>
    <automated>grep -c "dxy_easing_z_threshold" .planning/REQUIREMENTS.md | grep -q "^[1-9]" && grep -c "sbv_tightening_position_frac" .planning/REQUIREMENTS.md | grep -q "^0$" && grep -c "sbv_tightening_stop_loss_max_multiplier" .planning/REQUIREMENTS.md | grep -q "^[1-9]" && echo PASS</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "dxy_easing_z_threshold" .planning/REQUIREMENTS.md` returns at least 1
    - `grep -c "sbv_tightening_stop_loss_max_multiplier" .planning/REQUIREMENTS.md` returns at least 1
    - `grep -c "sbv_tightening_position_frac" .planning/REQUIREMENTS.md` returns 0 (old text removed)
    - `grep -c "forces half-position or full CASH" .planning/REQUIREMENTS.md` returns 0 (old text removed)
    - `grep -c "VETOes SELL" .planning/REQUIREMENTS.md` returns at least 1
    - `grep -n "MACRO-04" .planning/REQUIREMENTS.md` returns line 25 (preceding requirement intact)
    - `grep -n "WF-01" .planning/REQUIREMENTS.md | head -1` returns line 30 (Walk-Forward section header intact, no line shifts beyond in-place rewrite)
    - All 6 threshold names present in MACRO-05: `grep -c -E "(dxy_easing_z_threshold|dxy_tightening_z_threshold|eem_easing_z_threshold|eem_tightening_z_threshold|dxy_tightening_dd_threshold|sbv_tightening_stop_loss_max_multiplier)" .planning/REQUIREMENTS.md` returns at least 6
  </acceptance_criteria>
  <done>REQUIREMENTS.md MACRO-05 reflects the D-05 rewrite; old text strings removed; all 6 threshold field names present; surrounding requirements (MACRO-01..04, WF-01..03) intact.</done>
</task>

</tasks>

<verification>
After both tasks:

1. Both docs updated atomically — old text strings absent in both files (`grep -c "sbv_tightening_position_frac" .planning/ROADMAP.md .planning/REQUIREMENTS.md` returns total 0)
2. Both docs carry the new 6 threshold names (run the all-6-names grep on each)
3. Surrounding text intact — Phase 44 header at ROADMAP.md:843, Phase 45 header at ROADMAP.md:856, REQUIREMENTS.md MACRO-04 at line 25, REQUIREMENTS.md WF-01 at line 30
4. Single doc-only commit committed to git BEFORE Plan 02 starts (per RESEARCH Open Q4 recommendation)

Commit message convention (executor will use):
```
docs(44-01): rewrite MACRO-05 spec per D-05 — engine binary model preserved

ROADMAP.md SC-5 and REQUIREMENTS.md MACRO-05 updated to describe the
implemented policy: DXY easing VETOes SELL, DXY tightening lowers the
effective DD threshold, SBV tightening shrinks stop_loss_max_multiplier.

Replaces the original "forces half-position or full CASH" wording
which would have required a Position.size scalar refactor (deferred
to v11+ per Phase 44 D-05/D-06). Six threshold field names exposed as
Phase 45 grid-search inputs.

This is a doc-only commit landed BEFORE any code work so Phase 45
planning reads the correct text. Code follow-up in Plans 44-02..04.
```
</verification>

<success_criteria>
- ROADMAP.md SC-5 reflects D-05 rewrite (grep checks pass)
- REQUIREMENTS.md MACRO-05 reflects D-05 rewrite (grep checks pass)
- Both old text strings ("forces half-position or full CASH", "sbv_tightening_position_frac") absent from both files
- All 6 new threshold field names present in both files
- No code files touched (only `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` in `git diff --stat`)
- Atomic doc-only commit on top of HEAD before Plan 02 begins
</success_criteria>

<output>
After completion, create `.planning/phases/44-macro-filter-module/44-01-SUMMARY.md` documenting:
- Exact lines edited in each file (with line numbers from the live diff, e.g., "ROADMAP.md:852" and "REQUIREMENTS.md:26")
- Verification grep results (paste the command outputs)
- Commit hash of the doc-only commit
- Confirmation that no code files were touched
- Note for Plan 02: the 10 D-15 config field names + the rewritten policy semantics are now the canonical reference — Plan 02 implements them
</output>
