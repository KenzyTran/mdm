---
phase: 46-ab-oos-validation-hard-gate
plan: 04
type: execute
wave: 4
depends_on: ["46-01-scenario-scaffold-PLAN", "46-02-gate-helpers-PLAN", "46-03-pipeline-wiring-PLAN"]
files_modified:
  - output/v10_ab_comparison.txt
  - output/v10_ab_scenarios.csv
  - output/v10_validation_report.txt
autonomous: false
requirements: [VAL-01, VAL-02, VAL-03, VAL-04, VAL-05]

must_haves:
  truths:
    - "output/v10_ab_comparison.txt exists with 5-scenario A/B table covering VAL-01 columns"
    - "output/v10_ab_scenarios.csv exists with 6 rows (5 scenarios + B&H reference) matching SCENARIO_ORDER order"
    - "output/v10_validation_report.txt contains the literal verdict string on its own line per D-09"
    - "Expected retain-v6.0 branch: verdict string is 'v6.0 retained as production' AND script exited with code 1 AND rejection narrative present (per Phase 45 zero-accepted outcome)"
    - "Alternate pass branch: verdict string is 'v10 macro filter accepted as production' AND script exited with code 0 — only possible if somehow VAL-02 OOS +all hits CAGR >= 11.47% AND MaxDD > -20% AND VAL-03 passes AND VAL-04 passes (not expected given Phase 45 evidence; handled to preserve scientific honesty)"
    - "Full regression suite green pre-flight and post-commit (Phase 45 established 13 @pytest.mark.regression tests)"
    - "The three output artifacts are committed under output/ force-add past gitignore (Phase 42-05 / 45-03 precedent)"
  artifacts:
    - path: "output/v10_ab_comparison.txt"
      provides: "Human-readable 5-scenario A/B report (VAL-01)"
      min_lines: 50
    - path: "output/v10_ab_scenarios.csv"
      provides: "Machine-readable scenarios table (VAL-01 + OOS + HARD gate)"
      contains: "scenario,sharpe_rf3,cagr_pct"
    - path: "output/v10_validation_report.txt"
      provides: "HARD gate verdict report with literal D-09 verdict + D-10 narrative"
      contains: "FINAL VERDICT"
      min_lines: 60
  key_links:
    - from: "output/v10_validation_report.txt"
      to: "Phase 47 DOC-01/DOC-02/DOC-03 branching"
      via: "grep for literal verdict string (VERDICT_PASS or VERDICT_FAIL)"
      pattern: "v10 macro filter accepted as production|v6\\.0 retained as production"
---

<objective>
Execute `analysis/validate_v10.py` end-to-end on real VN30 2015-2026 data, human-verify the produced verdict, then commit the three output artifacts. This plan is the "GO/NO-GO" checkpoint for the v10.0 milestone — the committed `v10_validation_report.txt` is what Phase 47 reads to branch between full ship vs rejection audit.

Purpose: Separate execution from code changes so the engine run (and its ~2-5 minute cost for 5 full-period + 2 OOS-slice engine invocations + pytest subprocess) happens against a code-frozen `analysis/validate_v10.py`. Human verification at the checkpoint ensures we don't commit an artifact that the D-02 isolation sanity check silently bypassed or that has a parity failure masking a real regression.

Output: 3 committed artifacts + 1 commit message explicitly naming the retain-v6.0 verdict OR a ship-v10 verdict. Phase 47 enters the conditional branch indicated by the committed report.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-01-scenario-scaffold-SUMMARY.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-02-gate-helpers-SUMMARY.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-03-pipeline-wiring-SUMMARY.md
@.planning/phases/45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md

@analysis/validate_v10.py
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Pre-flight regression suite green + fresh artifact state</name>

  <read_first>
    - analysis/validate_v10.py (confirm all functions present from Plans 01-03)
    - .gitignore (confirm output/ is gitignored — force-add is required per Phase 42-05 / 45-03)
  </read_first>

  <files>
    (no files modified in this task — it is a gate check)
  </files>

  <behavior>
    - Full `@pytest.mark.regression` suite passes (13 tests as of end of Phase 45: 3 baseline_determinism + 5 macro_filter_v6_parity + 2 walkforward_oos_guard + other phase regressions)
    - No existing `output/v10_ab_comparison.txt`, `output/v10_ab_scenarios.csv`, `output/v10_validation_report.txt` files (if they exist from a prior aborted run, remove them so this plan produces fresh artifacts)
    - `uv run python -c "from analysis.validate_v10 import main"` succeeds (script importable)
  </behavior>

  <action>
    1. Run the full regression suite:
       ```
       uv run pytest -m regression -v
       ```
       All tests must pass. Record the count in the Task summary (e.g., "13/13 PASS"). If any fail, STOP and open a debug plan — do NOT run validate_v10.py until the suite is green.

    2. Clean any stale Phase 46 artifacts (force fresh output from this plan):
       ```
       rm -f output/v10_ab_comparison.txt output/v10_ab_scenarios.csv output/v10_validation_report.txt
       ```
       (Windows bash: `rm` works because this environment uses bash. If missing, `rm -f` is a no-op.)

    3. Confirm validate_v10.py is importable and main() exists:
       ```
       uv run python -c "from analysis.validate_v10 import main, SCENARIO_ORDER; print(f'main importable, {len(SCENARIO_ORDER)} scenarios')"
       ```
       Must print `main importable, 5 scenarios`.

    4. Confirm input artifacts are present:
       ```
       test -f output/v10_reconciled_baseline.json && echo "JSON present"
       test -f output/v10_grid_results.csv && echo "CSV present"
       test -f tests/test_macro_filter_v6_parity.py && echo "parity test present"
       ```
       All three must print the "present" string.
  </action>

  <verify>
    <automated>uv run pytest -m regression -v 2>&1 | tail -20</automated>
  </verify>

  <acceptance_criteria>
    - `uv run pytest -m regression -v` exits 0 with at least 12 tests passed (baseline 13 as of Phase 45)
    - `test -f output/v10_ab_comparison.txt || echo stale-absent` prints `stale-absent` (artifact not present before run)
    - `test -f output/v10_ab_scenarios.csv || echo stale-absent` prints `stale-absent`
    - `test -f output/v10_validation_report.txt || echo stale-absent` prints `stale-absent`
    - `test -f output/v10_reconciled_baseline.json && echo JSON-present` prints `JSON-present`
    - `test -f output/v10_grid_results.csv && echo GRID-present` prints `GRID-present`
    - `uv run python -c "from analysis.validate_v10 import main, SCENARIO_ORDER; print(len(SCENARIO_ORDER))"` prints `5`
  </acceptance_criteria>

  <done>Regression suite is green, Phase 46 input artifacts are in place, stale output artifacts removed, validate_v10.py is importable. Ready for Task 2 execution.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Execute validate_v10.py end-to-end + capture exit code + stdout tail</name>

  <read_first>
    - analysis/validate_v10.py (the script being executed — confirm main() is the entry)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (D-06 no short-circuit means exit 1 does NOT imply failure of this task — it may be the expected retain-v6.0 outcome)
    - .planning/phases/45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md (context: Phase 45 0/39 accepted → expected retain-v6.0 path)
  </read_first>

  <files>
    - output/v10_ab_comparison.txt (produced by script)
    - output/v10_ab_scenarios.csv (produced by script)
    - output/v10_validation_report.txt (produced by script)
  </files>

  <behavior>
    - Run `uv run python analysis/validate_v10.py`, tee stdout to a temp log file, capture exit code
    - Script runs 5 scenarios full-period + 2 OOS slices + walk-forward CSV read + pytest subprocess + 3 file writers
    - Expected runtime: ~3-6 minutes (5 full engine runs × 30-60s each + pytest subprocess ~90s + writers)
    - Exit code semantics (D-11): 0 = full pass = unexpected, 1 = any fail = expected retain-v6.0 — BOTH are "script ran successfully" for this task
    - The three output artifacts must be written regardless of exit code (D-06 no short-circuit)
  </behavior>

  <action>
    Execute the validation script:

    ```
    uv run python analysis/validate_v10.py
    ```

    NOTE: Exit code 1 is EXPECTED under the retain-v6.0 branch (per Phase 45 evidence). The script is designed to produce all three artifacts AND exit with code-reflective-of-verdict (D-11). Treat exit code 1 as "script completed successfully with verdict = retain v6.0" — NOT as a failure of this task.

    After the run, verify the three artifacts exist:
    ```
    test -f output/v10_ab_comparison.txt && echo "AB report: $(wc -l < output/v10_ab_comparison.txt) lines"
    test -f output/v10_ab_scenarios.csv && echo "CSV: $(wc -l < output/v10_ab_scenarios.csv) lines"
    test -f output/v10_validation_report.txt && echo "Validation: $(wc -l < output/v10_validation_report.txt) lines"
    ```

    Then extract the verdict string via grep (exactly one of the two literal strings from D-09 must appear):
    ```
    grep -F "v10 macro filter accepted as production" output/v10_validation_report.txt || echo "NOT v10-accepted"
    grep -F "v6.0 retained as production" output/v10_validation_report.txt || echo "NOT v6.0-retained"
    ```

    Expected (retain-v6.0 branch): first grep returns NOT-FOUND, second grep returns the match.
    Unexpected (v10-accepted branch): first grep returns the match, second returns NOT-FOUND.

    Record in the Task summary:
    - Script exit code
    - Verdict string found
    - 5-scenario CAGR table from output/v10_ab_comparison.txt
    - HARD gate +all OOS result
    - Walk-forward lookup result
    - Parity pytest pass/fail count
  </action>

  <verify>
    <automated>uv run python analysis/validate_v10.py; echo "EXIT=$?"; test -f output/v10_ab_comparison.txt && test -f output/v10_ab_scenarios.csv && test -f output/v10_validation_report.txt && echo "ALL THREE ARTIFACTS PRESENT" || echo "MISSING ARTIFACT"</automated>
  </verify>

  <acceptance_criteria>
    - Script completes within 10 minutes (likely ~3-6 min)
    - Exit code is 0 OR 1 (either is valid per D-11; other codes indicate uncaught error)
    - `output/v10_ab_comparison.txt` exists AND has at least 40 lines
    - `output/v10_ab_scenarios.csv` exists AND has exactly 7 lines (1 header + 5 scenarios + 1 B&H row)
    - `output/v10_validation_report.txt` exists AND has at least 50 lines
    - `grep -c "^v6\\.0 retained as production$\\|^v10 macro filter accepted as production$" output/v10_validation_report.txt` returns exactly 1 (exactly ONE of the two literal verdict strings, on its own line)
    - `grep -F "VAL-01: A/B COMPARISON" output/v10_ab_comparison.txt` returns 1 hit
    - `grep -F "FINAL VERDICT" output/v10_validation_report.txt` returns 1 hit
    - CSV header line starts with `scenario,sharpe_rf3,cagr_pct,max_dd_pct,total_return_pct`
    - Under retain-v6.0 branch (EXPECTED): `grep -F "REJECTION NARRATIVE" output/v10_validation_report.txt` returns 1 hit AND `grep -F "9.54" output/v10_validation_report.txt` returns at least 1 hit (narrative references Phase 45 train CAGR)
    - Under v10-accepted branch (UNEXPECTED but handled): NO `REJECTION NARRATIVE` section; verify +all OOS CAGR ≥ 11.47% AND MaxDD > -20% in the report to sanity-check
  </acceptance_criteria>

  <done>Script ran end-to-end, three artifacts produced, verdict string captured, per-gate verdicts recorded in Task summary. Ready for human-verify checkpoint.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Human-verify retain-v6.0 vs ship-v10 branch + approve commit</name>

  <read_first>
    - output/v10_validation_report.txt (the verdict source)
    - output/v10_ab_comparison.txt (the 5-scenario metrics)
    - output/v10_ab_scenarios.csv (the machine-readable row data)
    - .planning/phases/45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md (expected-branch context)
  </read_first>

  <files>
    (no files modified — verification-only checkpoint; no disk state changes in this task)
  </files>

  <what-built>
    Task 2 executed `analysis/validate_v10.py` against real VN30 2015-2026 data and produced:
      - output/v10_ab_comparison.txt (5-scenario A/B + whipsaw + OOS slice + walk-forward reference)
      - output/v10_ab_scenarios.csv (6 rows: 5 scenarios + B&H)
      - output/v10_validation_report.txt (gate summary + per-gate detail + literal verdict + optional rejection narrative)
    Exit code reflects verdict (D-11): 0 = full pass = v10 accepted; 1 = any fail = v6.0 retained.
  </what-built>

  <how-to-verify>
    1. **Read the validation report end-to-end:**
       ```
       cat output/v10_validation_report.txt
       ```
       Confirm:
       - GATE SUMMARY block shows PASS/FAIL for all 4 gates (VAL-01..VAL-04)
       - VAL-02 DETAIL block shows HARD gate verdict for +all scenario (the D-04 selected OOS scenario)
       - VAL-03 DETAIL block shows median_degradation ≈ 0.537 and passed_gate=False (retain-v6.0 expected)
       - VAL-04 DETAIL block shows tests_passed ≥ 5 with returncode=0 (parity gate green; failure here would be a hard stop regardless of other gates)
       - FINAL VERDICT block contains EXACTLY ONE of the two literal D-09 strings on its own line

    2. **Read the A/B comparison report:**
       ```
       cat output/v10_ab_comparison.txt
       ```
       Confirm:
       - All 5 scenarios appear in order (baseline, +DXY, +EEM, +SBV-regime, +all)
       - baseline CAGR ≈ 11.47% and baseline MaxDD ≈ -28.17% (matches reconciled baseline from Phase 42)
       - D-02 extremes headroom block shows `headroom ≥ 990` (observed |z| << 999 → isolation extremes never reached)
       - Whipsaw diagnostic shows baseline SELL count ≈ 124 (matches v10_reconciled_baseline.json sell_count=124)
       - +all SELL count, CAGR, MaxDD differ from baseline (proves macro filter has an effect — otherwise VAL-04's "changes at least one signal" test would already have failed)

    3. **Spot-check the CSV:**
       ```
       cat output/v10_ab_scenarios.csv | column -t -s,
       ```
       Confirm 7 lines (header + 5 scenarios + B&H), all 5 scenarios listed in SCENARIO_ORDER, `hard_gate_passed` column populated for baseline and +all rows (non-null), null for +DXY/+EEM/+SBV-regime (D-04 OOS-subset only runs 2).

    4. **Decision gate:**
       - Retain-v6.0 branch (EXPECTED): verdict line is `v6.0 retained as production`, exit code was 1, rejection narrative present. This is consistent with Phase 45 evidence (0/39 accepted, median_deg ~0.54 >> 0.30 gate). APPROVE commit.
       - Ship-v10 branch (UNEXPECTED): verdict line is `v10 macro filter accepted as production`, exit code was 0, no rejection narrative. This means OOS +all somehow beat reconciled baseline on both CAGR and MaxDD AND walk-forward CSV lookup passes AND parity is green. This contradicts Phase 45 evidence — before approving, MANUALLY inspect:
         - VAL-02 DETAIL block: is the reported CAGR plausibly >= 11.47%?
         - VAL-03 DETAIL block: is median_degradation really < 0.30? (Phase 45 recorded 0.537 for stage3_all_three-c1)
         - If VAL-03 passed unexpectedly, check whether `analysis/validate_v10.py` is reading the correct CSV row (stage3_all_three-c1 per D-07)
         - Only approve commit if the numbers are defensible

    5. **Parity failure branch (RARE):** If VAL-04 shows failed tests, the v6.0 parity regression is broken — this is a HARD STOP. Do NOT commit. Open a debug workflow to investigate whether something in Phase 44 broke under the current HEAD.
  </how-to-verify>

  <action>
    PAUSE for human verification. Do NOT proceed to Task 4 (commit) until the user explicitly approves the verdict branch. The user inspects the three artifacts using the commands in how-to-verify above, decides which branch is correct, and responds with the resume-signal phrase.

    Executor behavior on resume:
    - On "approved — retain v6.0": proceed to Task 4 with commit-message verdict = "v6.0 retained as production"
    - On "approved — ship v10": proceed to Task 4 with commit-message verdict = "v10 macro filter accepted as production"
    - On "hold — issue: ...": halt the plan, record the user's issue in the Task summary, and open a debug workflow if needed — do NOT commit artifacts that the user flagged as problematic
  </action>

  <verify>
    <automated>grep -E "^(v10 macro filter accepted as production|v6\.0 retained as production)$" output/v10_validation_report.txt</automated>
  </verify>

  <acceptance_criteria>
    - `grep -E "^(v10 macro filter accepted as production|v6\\.0 retained as production)$" output/v10_validation_report.txt` returns exactly 1 line (the verdict string on its own line, grep-matchable)
    - User responds with one of: `approved — retain v6.0`, `approved — ship v10`, or `hold — issue: {description}`
    - On hold: Task 4 does NOT run; plan is halted and user issue is recorded
    - On approved: Task 4 proceeds with the verdict string captured from the grep above
  </acceptance_criteria>

  <done>Human reviewer has read all three artifacts, the verdict is consistent with Phase 45 evidence (or, on unexpected ship-v10 branch, manually audited for plausibility), and the decision to commit or halt is recorded. Task 4 gates on this approval.</done>

  <resume-signal>Type "approved — retain v6.0" OR "approved — ship v10" OR "hold — issue: {description}"</resume-signal>
</task>

<task type="auto" tdd="false">
  <name>Task 4: Commit three Phase 46 output artifacts with verdict-naming commit message</name>

  <read_first>
    - output/v10_ab_comparison.txt (the artifact being committed)
    - output/v10_ab_scenarios.csv (the artifact being committed)
    - output/v10_validation_report.txt (the artifact being committed — source of the verdict string to echo in commit message)
    - .planning/phases/45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md (lines 131-149 — the precedent commit-strategy pattern for retain-v6.0 verdict)
  </read_first>

  <files>
    - output/v10_ab_comparison.txt
    - output/v10_ab_scenarios.csv
    - output/v10_validation_report.txt
  </files>

  <behavior>
    - Force-add the three artifacts past the `output/` gitignore (Phase 42-05 / 45-03 precedent)
    - Commit message body names the verdict explicitly so `git log` is machine-grep-able for Phase 47 branching
    - Post-commit regression suite still green (sanity check — artifact addition has no code impact but run to catch any toolchain regression)
  </behavior>

  <action>
    1. Force-add the three artifacts (output/ is gitignored):
       ```
       git add -f output/v10_ab_comparison.txt output/v10_ab_scenarios.csv output/v10_validation_report.txt
       ```

    2. Verify staged state:
       ```
       git status
       git diff --stat --cached
       ```

    3. Extract the literal verdict from the report for the commit message:
       ```
       VERDICT=$(grep -E '^(v10 macro filter accepted as production|v6\.0 retained as production)$' output/v10_validation_report.txt)
       echo "Verdict: $VERDICT"
       ```

    4. Commit with a message that explicitly names the verdict so Phase 47 can grep git log (Plan 45-03 pattern):

       ```
       git commit -m "$(cat <<'EOF'
       data(46): commit v10 A/B + OOS validation artifacts — verdict: {PASTE VERDICT HERE}

       Phase 46 end-to-end validation completed. analysis/validate_v10.py
       executed 5-scenario A/B on VN30 2015-2026 + OOS (2025-2026, baseline +
       all per D-04) + walk-forward CSV lookup (D-07) + v6.0 parity pytest
       (D-08). Exit code 1 (any gate fail) — D-11 exit-reflective-of-verdict.

       Gate verdicts:
         VAL-01 A/B:          {PASS|FAIL}   (5 scenarios complete, extremes headroom > 990)
         VAL-02 HARD (+all):  {PASS|FAIL}   (OOS CAGR vs 11.47% floor, MaxDD vs -20% ceiling)
         VAL-03 walk-forward: {PASS|FAIL}   (median_degradation vs 0.30 gate, from v10_grid_results.csv)
         VAL-04 parity:       {PASS|FAIL}   (tests/test_macro_filter_v6_parity.py pytest)

       Verdict string (D-09, literal, own line in v10_validation_report.txt):
         "{PASTE VERDICT}"

       Phase 47 branching: on 'v6.0 retained as production', DOC-01 + DOC-02
       are skipped; DOC-03 (rejection audit appended to .planning/MILESTONES.md)
       runs. project_best_model.md memory stays pinned (no update).

       Artifacts (force-added past output/ gitignore per Phase 42-05 / 45-03):
         output/v10_ab_comparison.txt    — 5-scenario A/B + whipsaw + OOS + walk-forward reference
         output/v10_ab_scenarios.csv     — machine-readable, 6 rows (5 scenarios + B&H)
         output/v10_validation_report.txt — per-gate detail + literal verdict + (if fail) rejection narrative

       Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
       EOF
       )"
       ```

       Fill in the `{PASTE VERDICT HERE}`, `{PASS|FAIL}` placeholders from the actual report contents.

    5. Post-commit verification:
       ```
       git log -1 --format="%H %s"
       git log -1 | grep -E "v10 macro filter accepted as production|v6\.0 retained as production"
       uv run pytest -m regression -v 2>&1 | tail -5
       ```
  </action>

  <verify>
    <automated>git log -1 --format="%H %s" && git log -1 | grep -E "v10 macro filter accepted as production|v6\.0 retained as production" | head -3</automated>
  </verify>

  <acceptance_criteria>
    - `git log -1 --name-only | grep "output/v10_ab_comparison.txt"` returns 1 hit
    - `git log -1 --name-only | grep "output/v10_ab_scenarios.csv"` returns 1 hit
    - `git log -1 --name-only | grep "output/v10_validation_report.txt"` returns 1 hit
    - `git log -1 --format=%s | grep -E "data\\(46\\)"` returns 1 hit (commit message subject prefix)
    - `git log -1 | grep -E "v10 macro filter accepted as production|v6\\.0 retained as production"` returns at least 1 hit (verdict string in commit message body — machine-grep-able per Phase 45-03 pattern)
    - `test -f output/v10_ab_comparison.txt && test -f output/v10_ab_scenarios.csv && test -f output/v10_validation_report.txt` all exit 0 (artifacts present post-commit)
    - `uv run pytest -m regression -v` exits 0 with same count as Task 1 pre-flight (toolchain unchanged)
    - `git status` shows clean working tree (no uncommitted changes from this plan)
  </acceptance_criteria>

  <done>Three Phase 46 artifacts committed with verdict explicitly named in commit message subject + body. Phase 47 planner can grep git log for verdict without opening the report file. Regression suite still green.</done>
</task>

</tasks>

<verification>
After all 4 tasks:

1. Artifacts exist and are committed:
   ```
   git log -1 --name-only | grep -E "output/v10_(ab_comparison|ab_scenarios|validation_report)"
   ```
   Must show 3 hits.

2. Verdict string is grep-able from the committed report AND commit message:
   ```
   grep -E "^(v10 macro filter accepted as production|v6\\.0 retained as production)$" output/v10_validation_report.txt
   git log -1 | grep -E "v10 macro filter accepted as production|v6\\.0 retained as production"
   ```
   Both must return at least 1 hit (exactly the same string).

3. VAL-01..VAL-05 requirements covered:
   - VAL-01: output/v10_ab_comparison.txt exists with 5-scenario table + output/v10_ab_scenarios.csv exists with 6 rows
   - VAL-02: output/v10_validation_report.txt contains "VAL-02 DETAIL" block with +all scenario HARD gate result
   - VAL-03: report contains "VAL-03 DETAIL" block with median_degradation lookup from Phase 45 CSV
   - VAL-04: report contains "VAL-04 DETAIL" block with pytest returncode + tests passed/failed
   - VAL-05: report contains literal verdict string on its own line (grep-matchable)

4. Regression suite green post-commit:
   `uv run pytest -m regression -v` → all pass (count unchanged from Task 1).
</verification>

<success_criteria>
- [ ] Pre-flight regression suite green (Task 1)
- [ ] Script ran end-to-end without uncaught error (Task 2)
- [ ] Three artifacts written: v10_ab_comparison.txt, v10_ab_scenarios.csv, v10_validation_report.txt
- [ ] Human verified verdict branch (retain-v6.0 or ship-v10) at Task 3 checkpoint
- [ ] Three artifacts committed with verdict-naming commit message (Task 4)
- [ ] Post-commit regression suite still green
- [ ] Phase 47 can grep either the report or git log to determine branch
</success_criteria>

<output>
After completion, create `.planning/phases/46-ab-oos-validation-hard-gate/46-04-execute-and-commit-SUMMARY.md`

Summary should record:
- Exit code from Task 2
- Verdict string found
- Per-gate PASS/FAIL counts (VAL-01..VAL-04)
- Key metrics table (5 scenarios × CAGR/MaxDD/Sharpe/SELL count)
- +all OOS metrics (CAGR, MaxDD, Sharpe)
- VAL-03 median_degradation
- VAL-04 parity returncode + tests passed/failed
- Commit hash for the 3-artifact commit
- Phase 47 next-branch indication (DOC-03 only if retain-v6.0, full DOC-01/02/03 if ship-v10)
</output>
