---
phase: 45-walk-forward-grid-search
plan: 03
type: execute
wave: 3
depends_on: [01, 02]
files_modified:
  - output/v10_grid_results.csv
  - output/v10_grid_best.json
autonomous: false
requirements: [WF-01, WF-02, WF-03]

must_haves:
  truths:
    - "analysis/walkforward_grid.py runs end-to-end on VN30 2015-2024 and exits 0"
    - "output/v10_grid_results.csv contains exactly 39 data rows (27 DXY + 9 EEM + 3 SBV) with both accepted=True and accepted=False present"
    - "output/v10_grid_best.json exists with schema_version=1, keys stage1_dxy/stage2_eem/stage3_all_three each with winner + runners_up"
    - "Each JSON winner config has all 10 macro fields populated (ready for Phase 46 dataclasses.replace)"
    - "Human reviewer inspects the Stage 3 winner config and median_degradation value; confirms the sweep produced sensible results before Phase 46 consumes them"
    - "Full pytest regression suite (baseline_determinism + macro_filter_v6_parity + walkforward_oos_guard) stays green after the sweep run"
  artifacts:
    - path: "output/v10_grid_results.csv"
      provides: "One row per combo across 3 stages (39 total) with config + per-year metrics + accept decision"
      min_lines: 40
    - path: "output/v10_grid_best.json"
      provides: "3 stage winners + 3 runners-up per stage, single-file consumable by Phase 46 VAL-01 scenario builder"
      contains: "schema_version, stage1_dxy, stage2_eem, stage3_all_three"
  key_links:
    - from: "output/v10_grid_results.csv"
      to: "output/v10_grid_best.json"
      via: "select_winner on accepted combos from CSV → JSON payload"
      pattern: "stage1_dxy|stage2_eem|stage3_all_three"
    - from: "output/v10_grid_best.json"
      to: "Phase 46 A/B scenario builder (downstream)"
      via: "Phase 46 reads this JSON to build 5 scenarios via threshold-extreme neutralization (D-13)"
      pattern: "ranking_metric.*median_eval_cagr_pct"
---

<objective>
Execute `analysis/walkforward_grid.py` on real VN30 data to produce `output/v10_grid_results.csv` and `output/v10_grid_best.json` — the two artifacts Phase 46 depends on. Then verify the artifacts programmatically + surface the key numbers to the human for sanity review before Phase 46 starts.

Purpose: Plans 01 and 02 land correct-by-construction code. This plan runs it once end-to-end, commits the artifacts, and gives the human a checkpoint to confirm results look sane (per CONTEXT D-Claude-6 "commit CSV? Phase 40 precedent: yes").

Output: Committed CSV + JSON under `output/`, a printed summary of winners, and a human-verified go-ahead for Phase 46.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/45-walk-forward-grid-search/45-CONTEXT.md
@analysis/walkforward_grid.py
@tests/test_walkforward_oos_guard.py
@output/v10_reconciled_baseline.json

<interfaces>
From Plan 01:
  `uv run python analysis/walkforward_grid.py` → writes output/v10_grid_results.csv + output/v10_grid_best.json
  Expected runtime ~10-15 min (39 combos × ~15-20s/combo on Phase 42 BASE-03 benchmark of ~3s per year × 10 years per run)
  Expected CSV size: 39 rows × ~45 columns
  Expected JSON size: 3 stages × (1 winner + 3 runners-up) ≈ 12 entries total

From Plan 02:
  `uv run pytest -m regression tests/test_walkforward_oos_guard.py -v` must be green (pre-run sanity)

Phase 42 reconciled baseline (output/v10_reconciled_baseline.json):
  cagr_pct = 11.47 (v6.0 reference; NOT a gate — just context print)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pre-flight checks — tests green + no existing artifacts</name>
  <files>(no file changes)</files>
  <read_first>
    - analysis/walkforward_grid.py (confirm RESULTS_CSV/BEST_JSON paths point to output/v10_grid_results.csv and output/v10_grid_best.json)
  </read_first>
  <action>
    Run the full regression suite as a pre-flight check. All of these must pass before proceeding:

    1. `uv run pytest -m regression tests/test_walkforward_oos_guard.py -v` — must show "2 passed"
    2. `uv run pytest -m regression tests/test_baseline_determinism.py -v` — must show "3 passed" (Phase 42 invariant)
    3. `uv run pytest -m regression tests/test_macro_filter_v6_parity.py -v` — must show "5 passed" (Phase 44 invariant)
    4. `python -m py_compile analysis/walkforward_grid.py` — must exit 0

    Then confirm no stale artifacts will pollute this run:
    5. `ls output/v10_grid_results.csv output/v10_grid_best.json 2>&1` — if either exists, note its mtime for comparison post-sweep; do NOT delete (the script overwrites deterministically).

    If any pre-flight fails, STOP and report the failure. Do not proceed to Task 2.
  </action>
  <verify>
    <automated>uv run pytest -m regression tests/test_walkforward_oos_guard.py tests/test_baseline_determinism.py tests/test_macro_filter_v6_parity.py -v --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest -m regression tests/test_walkforward_oos_guard.py tests/test_baseline_determinism.py tests/test_macro_filter_v6_parity.py -v` exits 0 and reports "10 passed" (2 + 3 + 5) with no failures, errors, or xfailed
    - `python -m py_compile analysis/walkforward_grid.py` exits 0
    - Executor has noted whether output/v10_grid_results.csv and output/v10_grid_best.json exist pre-run (informational, not a gate)
  </acceptance_criteria>
  <done>
    All regression tests green (10 passed). Script compiles cleanly. Pre-existing artifact state noted. Ready to run the sweep.
  </done>
</task>

<task type="auto">
  <name>Task 2: Execute the sweep end-to-end</name>
  <files>output/v10_grid_results.csv, output/v10_grid_best.json</files>
  <read_first>
    - analysis/walkforward_grid.py (confirm main() entry path and expected stdout structure)
    - .planning/phases/45-walk-forward-grid-search/45-CONTEXT.md D-17 — serial execution ~10-15 min expected
  </read_first>
  <action>
    Execute the sweep. Expected runtime: 10-15 minutes.

    ```
    uv run python analysis/walkforward_grid.py 2>&1 | tee output/v10_grid_run.log
    ```

    (Tee captures stdout to a runlog for post-run inspection. The runlog is ephemeral — not committed to git.)

    During execution, the script prints:
    - Header (TRAIN/EVAL/OOS windows, accept gate)
    - Reconciled baseline CAGR (context only)
    - tqdm progress for Stage 1 (27 combos), Stage 2 (9 combos), Stage 3 (3 combos)
    - Per-stage winner line: "Stage N winner: {config_name} | median_eval_cagr={X.XX}% | median_degradation={Y.YYY}"
    - Final summary: "{accepted}/39 combos accepted"

    Post-run, confirm exit code 0. If the script raised SummaryError (D-18 guard tripped), treat as a BLOCKER — do NOT commit artifacts. Report the top-3 NaN details and stop.

    Do NOT delete output/v10_grid_run.log — it's useful runtime evidence for SUMMARY.md but is NOT committed (add to .gitignore check if not already).
  </action>
  <verify>
    <automated>test -f output/v10_grid_results.csv && test -f output/v10_grid_best.json && python -c "import pandas as pd; df = pd.read_csv('output/v10_grid_results.csv'); assert len(df) == 39, f'Expected 39 rows, got {len(df)}'; assert df['stage'].value_counts().to_dict() == {'stage1_dxy': 27, 'stage2_eem': 9, 'stage3_all_three': 3}; print(f'CSV OK: 39 rows, {df[chr(34)+chr(97)+chr(99)+chr(99)+chr(101)+chr(112)+chr(116)+chr(101)+chr(100)+chr(34)].sum()}/39 accepted')"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f output/v10_grid_results.csv` exits 0
    - `test -f output/v10_grid_best.json` exits 0
    - `python -c "import pandas as pd; df=pd.read_csv('output/v10_grid_results.csv'); assert len(df)==39"` exits 0
    - `python -c "import pandas as pd; df=pd.read_csv('output/v10_grid_results.csv'); counts=df['stage'].value_counts().to_dict(); assert counts=={'stage1_dxy':27,'stage2_eem':9,'stage3_all_three':3}, counts"` exits 0
    - `python -c "import pandas as pd; df=pd.read_csv('output/v10_grid_results.csv'); cols=set(df.columns); needed={'median_degradation','median_eval_cagr_pct','accepted','rejection_reason','cagr_train_pct'}; assert needed.issubset(cols), f'Missing: {needed-cols}'"` exits 0
    - `python -c "import json; j=json.load(open('output/v10_grid_best.json')); assert j['schema_version']==1; assert set(j.keys())>={'stage1_dxy','stage2_eem','stage3_all_three','schema_version','generated_at','engine_git_hash','train_window','eval_years','oos_holdout','ranking_metric'}"` exits 0
    - `python -c "import json; j=json.load(open('output/v10_grid_best.json'));\nfor s in ('stage1_dxy','stage2_eem','stage3_all_three'):\n    assert 'winner' in j[s] and 'runners_up' in j[s]"` exits 0
    - `python -c "import json; j=json.load(open('output/v10_grid_best.json')); w=j['stage3_all_three']['winner']; cfg=w['config']; needed={'dxy_easing_z_threshold','dxy_tightening_z_threshold','dxy_tightening_dd_threshold','eem_easing_z_threshold','eem_tightening_z_threshold','sbv_tightening_stop_loss_max_multiplier','dxy_window_days','eem_window_days','sbv_decay_days','macro_filter_enabled'}; assert needed.issubset(cfg.keys()), f'Missing config fields: {needed-set(cfg.keys())}'; assert cfg['macro_filter_enabled'] is True"` exits 0
    - Script exit code 0 (no SummaryError, no uncaught exception)
    - At least ONE row in CSV has `accepted=True` AND at least ONE row has `accepted=False` (both cases represented per ROADMAP SC-2 "not silently dropped")
  </acceptance_criteria>
  <done>
    Script ran to completion (exit 0), produced a 39-row CSV with correct stage split and all required columns, produced a valid JSON with schema_version=1 and 3-stage structure. Both accepted and rejected combos present in CSV. Stage 3 winner has all 10 macro config fields populated.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Human-verify sweep results before committing artifacts</name>
  <files>output/v10_grid_results.csv, output/v10_grid_best.json</files>
  <read_first>
    - output/v10_grid_results.csv (produced by Task 2 — inspect head + tail)
    - output/v10_grid_best.json (produced by Task 2 — inspect full contents)
    - output/v10_grid_run.log (stdout capture from Task 2 — scan for warnings/tracebacks)
  </read_first>
  <what-built>
    Analysis artifacts from running `analysis/walkforward_grid.py` in Task 2:
    - `output/v10_grid_results.csv` — 39 rows × ~45 columns, one per combo
    - `output/v10_grid_best.json` — 3 stage winners + 3 runners-up per stage
  </what-built>
  <action>
    This is a human-verify checkpoint. No code is changed. The executor presents the artifacts to the user, runs a summary inspection script, and waits for the "approved" signal before Task 4 commits anything to git.

    Save this inspection script to `/tmp/inspect_phase45.py` and run it, printing output to the user for review:

    ```python
    import pandas as pd
    import json

    df = pd.read_csv('output/v10_grid_results.csv')
    print(f'Total combos: {len(df)}')
    print(f'Stage split: {df["stage"].value_counts().to_dict()}')
    print(f'Accepted: {df["accepted"].sum()}/{len(df)}')
    print('Rejection reasons:')
    rejected = df[~df['accepted']]
    print(rejected['rejection_reason'].value_counts().to_dict())

    print()
    j = json.load(open('output/v10_grid_best.json'))
    print(f'Schema version: {j["schema_version"]}')
    print(f'Ranking metric: {j["ranking_metric"]}')
    print(f'OOS holdout: {j["oos_holdout"]}')
    print(f'Engine git hash: {j["engine_git_hash"]}')

    for s in ['stage1_dxy', 'stage2_eem', 'stage3_all_three']:
        w = j[s]['winner']
        ru_count = len(j[s]['runners_up'])
        print(f'\n{s} winner:')
        print(f'  config: {w["config"]}')
        print(f'  metrics: {w["metrics"]}')
        print(f'  runners_up count: {ru_count}')
    ```

    Then instruct the user to verify:
    1. At least 1 combo accepted in each stage, OR document why all were rejected in Stage N as a legitimate outcome (e.g., train CAGR extremely low across the board).
    2. Stage 3 winner's `median_eval_cagr_pct` is in the 5-15% ballpark (reasonable given v6.0 baseline 11.47%). If < 0% or > 30%, pause and inspect.
    3. Stage 3 winner's `median_degradation` is within (-0.5, 0.30) — per D-09 it MUST be < 0.30 to be accepted.
    4. First 3 rows of CSV are stage1_dxy with all 10 macro fields populated: `head -4 output/v10_grid_results.csv` (including header).
    5. `config` field of each winner in JSON has all 10 keys and `macro_filter_enabled: true`.
    6. JSON metadata: `schema_version: 1`, `ranking_metric: "median_eval_cagr_pct"`, `oos_holdout: "2025-01-01..2026-12-31 (untouched)"`.
    7. (Optional) Scan `output/v10_grid_run.log` for unexpected WARNING or traceback lines.

    Expected-outcome reference (NOT a gate — Phase 46 evaluates the real gate):
    - If the macro filter is valuable, 5-20 out of 39 combos should be accepted.
    - If ZERO combos are accepted across all stages, that's a legitimate scientific result (v10.0 macro filter does not pass walk-forward discipline) — Phase 46 would enter the retain-v6.0 branch. Document this if it happens.

    Wait for the user's "approved" signal before proceeding to Task 4. If the user reports an issue (0 accepted everywhere, bizarre winner config, NaN in winner metrics, runtime > 30 min, SummaryError raised mid-run, JSON missing a stage), DO NOT proceed to Task 4. Diagnose and fix upstream before retrying.
  </action>
  <how-to-verify>
    Open a fresh terminal and run the inspection script above. Read through the printed output and the CSV + JSON artifacts. Apply the 7 checks listed in `<action>`.
  </how-to-verify>
  <verify>
    <automated>python -c "import pandas as pd; df=pd.read_csv('output/v10_grid_results.csv'); print(f'summary: {len(df)} rows | accepted {df[chr(34)+chr(97)+chr(99)+chr(99)+chr(101)+chr(112)+chr(116)+chr(101)+chr(100)+chr(34)].sum()}/{len(df)} | stages {df[chr(34)+chr(115)+chr(116)+chr(97)+chr(103)+chr(101)+chr(34)].value_counts().to_dict()}')"</automated>
  </verify>
  <acceptance_criteria>
    - User inspected the printed summary (stage counts + accepted/rejected split + stage winners) and responded "approved"
    - If user reported an issue, Task 4 is NOT executed — plan halts awaiting upstream fix
    - Automated summary-print above runs cleanly (confirms CSV is readable even if user wants to re-inspect later)
  </acceptance_criteria>
  <resume-signal>
    Type "approved" if the artifacts look sane. If anything looks off (e.g., 0 accepted, bizarre winner config, NaN in winner metrics, runtime > 30 min, SummaryError raised mid-run, JSON missing a stage), describe the issue and do NOT proceed.

    If SummaryError was raised mid-run: the script halted correctly per D-18 (top-3 accepted combo had NaN eval metric). Do NOT commit the partial CSV. Investigate which combo NaN'd (via the `error_train` / `error_year_{y}` columns or the runlog traceback) and either fix upstream (rare — likely a data issue) or document the NaN as a legitimate engine failure and decide whether to loosen the D-18 guard for this iteration.

    If the sweep is in a "bizarre" state (e.g., all Stage 1 combos rejected with "insufficient_eval_coverage 0/6"): the engine is failing systematically. Abort. Check the reconciled baseline + MacroFilter integration — likely a Phase 44 contract issue surfacing only under grid search conditions.
  </resume-signal>
  <done>
    User has reviewed artifacts and explicitly approved them ("approved" or describing all 7 checks as passing). Phase 45 artifacts are verified sensible and ready to commit.
  </done>
</task>

<task type="auto">
  <name>Task 4: Commit artifacts to git</name>
  <files>output/v10_grid_results.csv, output/v10_grid_best.json</files>
  <read_first>
    - .gitignore (confirm output/ is whitelisted for these specific files — Phase 42 Plan 42-05 precedent force-added output/v10_reconciled_baseline.json past gitignore)
    - CLAUDE.md (Code-Docs Sync rule — NOT applicable per phase planner note; Phase 45 does NOT modify strategies/ or docs/rules_*.md)
  </read_first>
  <action>
    Stage and commit the two artifacts:

    ```bash
    git add -f output/v10_grid_results.csv output/v10_grid_best.json
    ```

    (The `-f` flag handles the case where output/ is gitignored — Phase 42-05 precedent explicitly force-adds artifacts that downstream phases consume.)

    Then commit with a message referencing WF-01/WF-02/WF-03:

    ```bash
    git commit -m "$(cat <<'EOF'
    feat(45): execute walk-forward grid sweep, commit CSV + JSON artifacts

    Ran analysis/walkforward_grid.py end-to-end on VN30 2015-2024 per Phase 45 D-01
    staged sweep (27 DXY + 9 EEM + 3 SBV = 39 combos). Acceptance gate:
    median_degradation < 0.30 AND median(eval CAGR) > 0 enforced INSIDE the sweep
    per WF-02 (Phase 41 lesson: walk-forward CV must be inside grid search, not post-hoc).

    Artifacts (WF-03):
    - output/v10_grid_results.csv: 39 rows with full D-06 schema (config + per-year
      metrics + accept decision + rejection_reason) — both accepted and rejected
      combos present per ROADMAP SC-2.
    - output/v10_grid_best.json: D-11 schema, 3 stage winners + 3 runners-up each,
      full 10-field macro config tuple per entry (Phase 46 consumable via
      dataclasses.replace(VN30_PRESET, **config)).

    OOS fence (D-14): 2025-2026 data never entered the sweep (runtime assert + Plan
    02 pytest verifies). Phase 46 OOS test will be the first time 2025+ data touches
    any v10.0 candidate.

    Pre-run regression suite (10 tests) green; compute_metrics reused from
    analysis/validate_v9.py per D-16 (no drift).

    Closes: WF-01, WF-02, WF-03
    EOF
    )"
    ```

    After commit, verify:
    - `git log -1 --stat` shows only `output/v10_grid_results.csv` + `output/v10_grid_best.json` modified (no accidental strategy file changes)
    - `git status` is clean (no uncommitted changes in strategies/ or tests/)
  </action>
  <verify>
    <automated>git log -1 --name-only --format="" | grep -E "output/v10_grid_(results\.csv|best\.json)" | sort -u | wc -l</automated>
  </verify>
  <acceptance_criteria>
    - `git log -1 --name-only --format=""` lists exactly `output/v10_grid_results.csv` and `output/v10_grid_best.json` (no other files)
    - `git log -1 --format="%s"` contains "45" and one of "grid", "sweep", or "walk-forward"
    - `git status --short` produces empty output (no uncommitted changes)
    - `git show HEAD --stat` shows 2 files changed with reasonable line counts (CSV ~40 rows, JSON ~150 lines)
    - No file under `strategies/`, `docs/`, or `tests/` appears in `git show HEAD --stat`
    - Post-commit regression suite still green: `uv run pytest -m regression tests/test_walkforward_oos_guard.py tests/test_baseline_determinism.py tests/test_macro_filter_v6_parity.py -v` exits 0 with 10 passed
  </acceptance_criteria>
  <done>
    Both artifacts committed in a single commit referencing WF-01/WF-02/WF-03. Commit touches ONLY the two output files — no strategy/docs/test changes. git status is clean. Full regression suite still green. Phase 46 can now read the JSON to start A/B scenario construction.
  </done>
</task>

</tasks>

<verification>
Phase-level verification (after all 4 tasks):

- `uv run pytest -m regression tests/ -v` reports all regression tests passing (baseline_determinism + macro_filter_v6_parity + walkforward_oos_guard = 10 tests green)
- `python -c "import json; j=json.load(open('output/v10_grid_best.json')); print('Schema v' + str(j['schema_version']) + ', stages:', list(j.keys()))"` prints the schema + stages list for human confirmation
- `git log -1 --stat` shows the Phase 45 execution commit with exactly 2 files changed

**Out-of-scope self-check (MUST all be NO):**
- Did this plan modify `strategies/` files? → NO
- Did this plan modify `analysis/walkforward_grid.py`? → NO (Plan 01 owns it)
- Did this plan add new tests? → NO (Plan 02 owns tests)
- Did this plan change `docs/` or `dashboard/`? → NO (Phase 47 territory)
- Did this plan touch `output/v10_reconciled_baseline.json`? → NO (read-only context)
</verification>

<success_criteria>
- Sweep runs end-to-end, exit 0
- Committed CSV has 39 rows split 27/9/3 across stages
- Committed JSON has schema_version=1, 3 stages × (1 winner + 3 runners-up)
- Both accepted and rejected combos present in CSV
- Stage 3 winner has all 10 macro config fields populated (ready for Phase 46 dataclasses.replace)
- Human checkpoint passed — results are sensible (or documented as a legitimate all-rejected outcome)
- All 10 regression tests still green post-commit
- git HEAD contains only output/ changes — no strategies/, docs/, or tests/ modifications
</success_criteria>

<output>
After completion, executor creates `.planning/phases/45-walk-forward-grid-search/45-03-SUMMARY.md` summarizing:
- Sweep runtime (actual wall-clock)
- Accepted/rejected counts per stage
- Stage 3 winner config (the candidate Phase 46 will likely evaluate first)
- Any rows where run_combo raised (with error_year_{y} content)
- Baseline CAGR from reconciled JSON (context only) vs Stage 3 winner's train CAGR (rough sanity)
- Confirmation that OOS fence held (max date in CSV eval years = 2024)
- Confirmation that all regression tests stayed green
</output>
