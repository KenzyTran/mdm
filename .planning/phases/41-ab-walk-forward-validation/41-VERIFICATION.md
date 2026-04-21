---
phase: 41-ab-walk-forward-validation
verified: 2026-04-21T05:30:00Z
status: passed
score: 4/4 success criteria verified
---

# Phase 41: A/B + Walk-Forward Validation Verification Report

**Phase Goal:** Combined v9.0 model is validated against baseline with A/B comparison and walk-forward testing, and whipsaw reduction is quantified
**Verified:** 2026-04-21T05:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

This is a READ-ONLY VALIDATION phase. The phase goal is to produce evidence (pass or fail) and a committed production-candidate recommendation. A negative VAL-03 verdict (all v9 scenarios fail the CAGR ≥ 11.5% gate) combined with D-21 v6.0-retention fallback is a successful phase outcome, as long as all 4 success criteria are satisfied.

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A/B report covers 4 scenarios on 2015-2026 with CAGR/Sharpe/MaxDD/transitions/time-in-state per scenario | VERIFIED | `output/v9_ab_comparison.txt` lines 20-26 contain all 4 scenarios (baseline/+ATR/+DD/+both) + B&H, each with TotRet/CAGR/MaxDD/Sharpe/Trans/BUY%/CASH%/SELL%. `output/v9_ab_scenarios.csv` has 5 data rows and 17 canonical columns |
| 2 | Walk-forward validates 2015-2021 Train vs 2022-2026 Test with CAGR degradation documented when > 50% | VERIFIED | Report lines 46-61: all 4 scenarios show CAGR_tr + CAGR_te + Degrad + pass/fail verdict. 3 v9 scenarios exceed threshold and each has an explicit FAIL verdict with the degradation percentage documented (e.g. `+ATR: FAIL (degradation +96.4% exceeds threshold)`). Breach is documented per VAL-02 "documented if breached" requirement |
| 3 | Combined model meets CAGR ≥ 11.5% AND (Sharpe > baseline OR MaxDD < -25%), or a failure-mode writeup explains the gap | VERIFIED | Report lines 76-96: VAL-03 section with baseline-pairwise Sharpe comparison; all 3 v9 scenarios FAIL with per-scenario verdict breakdown (CAGR ✗, Sharpe ✗, MaxDD ✗). Failure-mode analysis block explicitly lists gap vs 11.5% for each scenario (+2.72pp, +1.47pp, +2.57pp), Sharpe deltas, MaxDD breaches, hypothesized reasons (regime change, DD-only bias, ATR overfitting), and closest-to-criterion scenario (+DD at CAGR 10.03%) |
| 4 | Transition-count diagnostic quantifies whipsaw reduction (SELL signals drop from 124, MA50-share drops from 84%) | VERIFIED | Report lines 29-43: VAL-04 section prints literal `Baseline v6.0 reference: 124 SELL signals, 84% MA50-breakdown share` then per-scenario SELL count + MA50% + buy count + Δ SELL + Δ MA50%. Whipsaw reduction evidence loop shows `+ATR: -43.8%`, `+DD: -1.0%`, `+both: -45.7%` SELL count change. Note: actual baseline SELL count (105) differs from ROADMAP reference (124) because the current HybridEngine differs from the memory reference; the report correctly uses actual measured baseline (105) for Δ computations while still echoing the 124/84% historical anchor as required by the success criterion |

**Score:** 4/4 success criteria verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `analysis/validate_v9.py` | Phase 41 validation script with 5 functions + 4 VAL sections + CSV writer + Production Candidate | VERIFIED | 651 lines; parses cleanly (`ast.parse` OK); all 5 functions present via AST walk (`load_locked_params, run_engine, compute_metrics, build_scenario_configs, main`); grep confirms all 4 VAL section headers, DD-only caveat, Production Candidate section; 1 `sys.exit(0)` at line 647 |
| `output/v9_ab_comparison.txt` | Human-readable unified report with 4 VAL sections + DD caveat + Production Candidate recommendation | VERIFIED | 110 lines, 7368 bytes. Contains all 4 VAL section headers (VAL-01, VAL-02, VAL-03, VAL-04), Methodological Note: DD-only bias caveat, Production Candidate section as the final section with committed recommendation `v6.0 HybridEngine + fail-safe remains production` (line 107) |
| `output/v9_ab_scenarios.csv` | Machine-readable per-scenario metrics table (4 scenarios + B&H) with 17 canonical columns | VERIFIED | 5 data rows (4 v9 scenarios + B&H VN30); all 17 required columns present (scenario, sharpe_rf3, cagr_pct, max_dd_pct, total_return_pct, transitions, sell_count, ma50_breakdown_sell_share, buy_count, buy_pct, cash_pct, sell_pct, sell_count_delta, ma50_share_delta, cagr_train, cagr_test, cagr_degradation); B&H VN30 scenario row present |
| `output/v9_atr_best.json` | Phase 40 locked ATR params (dependency input) | VERIFIED | Loaded successfully: k=1.0, N=20, m=2 (confirmed in report line 5) |
| `output/v9_dd_best.json` | Phase 40 locked DD params (dependency input) | VERIFIED | Loaded successfully: large_drop=-0.007, small_drop=-0.003, percentile=3 (confirmed in report line 6) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `analysis/validate_v9.py` | `output/v9_atr_best.json` | `json.load in load_locked_params()` | WIRED | `ATR_BEST_JSON` path constant at line 59; `FileNotFoundError` raise at lines 83-88; `json.load` at line 96. Confirmed end-to-end: params echoed in report line 5 |
| `analysis/validate_v9.py` | `output/v9_dd_best.json` | `json.load in load_locked_params()` | WIRED | `DD_BEST_JSON` path constant at line 60; `FileNotFoundError` raise at lines 89-94; `json.load` at line 98. Confirmed end-to-end: params echoed in report line 6 |
| `analysis/validate_v9.py` | `VN30_PRESET` | `dataclasses.replace` | WIRED | 4 `replace(VN30_PRESET, ...)` calls in `build_scenario_configs` (lines 233, 239, 248, 259); each produces one of the 4 scenarios with correct overrides. `refined_dd_large_vol_rule` and `refined_dd_small_vol_lookback` correctly NOT overridden (D-06 fidelity) |
| `analysis/validate_v9.py` | `output/v9_ab_comparison.txt` | `open().write` in `main()` | WIRED | `REPORT_TXT` constant at line 61; write at lines 641-643 at end of `main()`. Artifact exists on disk with expected content |
| `analysis/validate_v9.py` | `output/v9_ab_scenarios.csv` | `pd.DataFrame.to_csv` in `main()` | WIRED | `SCENARIOS_CSV` constant at line 62; `csv_df.to_csv(SCENARIOS_CSV, index=False)` at line 580. Canonical column order via explicit `csv_df[[...]]` slicing at lines 573-578 (not dict-iteration dependent) |
| `analysis/validate_v9.py` | Train/Test compute_metrics calls | Walk-forward slice by date (D-08, D-09) | WIRED | Train slice: `df_full[df_full['date'] <= TRAIN_END]` at line 403 → separate engine run. Test slice: `r_full[r_full['date'] >= TEST_START]` at line 425 from cached full-period results (preserves indicator warmup). Degradation formula `(ct - cte) / abs(ct)` at line 435 matches D-10 exactly |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `output/v9_ab_comparison.txt` | `full_metrics[name]` | `compute_metrics(run_engine(df_full, cfg))` — real HybridEngine run on 2803-row VN30 DataFrame 2015-2026 | Yes — report shows distinct numeric metrics per scenario (baseline CAGR 10.70%, +ATR 8.78%, +DD 10.03%, +both 8.93%) with differentiated SELL counts, MA%, transitions | FLOWING |
| `output/v9_ab_comparison.txt` | `train_metrics[name]`, `test_metrics[name]`, `degradations[name]` | Independent engine run on Train slice + cached full-period slice on Test; degradation computed per scenario | Yes — report shows distinct train CAGR (12.39/14.14/13.58/13.55%) and test CAGR (8.01/0.51/4.45/1.74%) with non-trivial degradation values | FLOWING |
| `output/v9_ab_scenarios.csv` | CSV row data | Same `full_metrics`, `train_metrics`, `test_metrics`, `degradations` dicts + B&H computed from df_full close series | Yes — CSV contains real float/int values matching report table; B&H row has CAGR 10.44%, MaxDD -48.14% derived from actual price series | FLOWING |
| Production Candidate recommendation | `recommendation` variable | Derived from `any_pass` boolean (from `verdicts` dict built from `full_metrics`) via D-21 fallback branch | Yes — `any_pass=False` triggers D-21 v6.0 retention path; literal string emitted to report | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Script parses as valid Python | `python -c "import ast; ast.parse(open('analysis/validate_v9.py').read())"` | Parses OK | PASS |
| All 5 required functions defined | AST walk for function names | `{build_scenario_configs, compute_metrics, load_locked_params, main, run_engine}` all present | PASS |
| CSV has exactly 5 data rows + 17 columns | `pd.read_csv('output/v9_ab_scenarios.csv')` | 5 rows; 17 columns matching canonical set; scenarios = [baseline, +ATR, +DD, +both, B&H VN30] | PASS |
| Report contains all 4 VAL section headers + DD caveat + Production Candidate | grep lines 12-111 of report | All 6 required anchors present | PASS |
| Script committed with 4 atomic commits (Task × 2 + Summary × 2) | `git log --oneline -10` | `7648e71, 481d587, e7d79b6, e2eaafa, 92afd4f, dadbdb5` all present in recent history | PASS |
| Phase 42 scope files untouched | `git diff --name-only HEAD~6 HEAD -- docs/rules_mdm_hybrid.md dashboard/` | Empty output (nothing touched) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| VAL-01 | 41-01, 41-02 | A/B report with 4 scenarios on 2015-2026 with CAGR, Sharpe, MaxDD, transitions, time-in-state | SATISFIED | `output/v9_ab_comparison.txt` VAL-01 section (lines 12-26) has all 4 scenarios + B&H reference row; all required columns present; CSV mirror at `output/v9_ab_scenarios.csv` |
| VAL-02 | 41-02 | Walk-forward — Train 2015-2021, Test 2022-2026, CAGR degradation < 50% threshold | SATISFIED | Report VAL-02 section (lines 46-61) with train/test CAGR per scenario, degradation percentage, explicit PASS/FAIL verdict vs 50% threshold. Breaches (+96.4%, +67.2%, +87.2%) are explicitly documented in text form |
| VAL-03 | 41-02 | Combined model beats baseline on CAGR ≥ 11.5% AND (Sharpe > baseline OR MaxDD < -25%); document if fails | SATISFIED | Report VAL-03 section (lines 76-96) with baseline-pairwise Sharpe (0.461), per-scenario verdict breakdown, and explicit Failure-mode analysis block with gap vs 11.5%, hypothesized reasons, closest-to-criterion scenario. Per phase guidance: failure verdict WITH D-21 fallback recommendation is the phase success condition |
| VAL-04 | 41-01 | Transition count report — whipsaw reduction (SELL signals from 124 baseline, MA50-share from 84%) | SATISFIED | Report VAL-04 section (lines 29-43) with literal baseline reference `124 SELL signals, 84% MA50-breakdown share`, per-scenario SELL count + MA50% + delta columns, and explicit whipsaw-reduction evidence loop (+ATR: -43.8%, +DD: -1.0%, +both: -45.7%) |

All 4 phase requirements from PLAN frontmatter are cross-referenced against REQUIREMENTS.md (lines 31-34) and all appear in Phase 41 traceability table (lines 77-80). No orphaned requirements. No ID missing from plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `analysis/validate_v9.py` | - | TODO/FIXME/PLACEHOLDER/NotImplementedError | - | None found |
| `analysis/validate_v9.py` | - | Stub returns / empty handlers / console.log-only implementations | - | None found |
| `analysis/validate_v9.py` | - | Hardcoded empty data feeding rendering | - | None found; NaN fallback for failed engine runs is a legitimate error-handling pattern (fail-loud per Phase 40 D-10) |

Clean file — no anti-pattern smells. The fail-loud NaN assignment in the except blocks (lines 333-338, 420-421, 427-429) is legitimate per Phase 40 D-10 pattern and is explicitly documented in summary.

### Human Verification Required

None. All 4 success criteria are verifiable programmatically against concrete artifacts. The phase delivers evidence-based outputs (text report + CSV + committed recommendation string) rather than UI behavior, visual rendering, or external service integration.

### Gaps Summary

No gaps found. Phase 41 delivered a complete, evidence-based validation of v9.0 against v6.0 baseline. All 4 success criteria are satisfied:

1. **VAL-01 (A/B):** 4 scenarios + B&H on 2015-2026 with all required metrics columns in both human-readable report and machine-readable CSV.
2. **VAL-02 (Walk-forward):** Train/Test split implemented exactly per D-08/D-09, degradation computed per D-10, all 3 v9 scenarios correctly flagged as breaching the 50% threshold in the report text.
3. **VAL-03 (Success criterion):** All 3 v9 scenarios fail the full-period criterion; failure-mode writeup present with per-scenario gap, hypothesized reasons, and closest-to-criterion identification.
4. **VAL-04 (Whipsaw):** Historical baseline reference (124 / 84%) echoed verbatim; measured baseline (105) and per-scenario deltas quantify actual whipsaw reduction (+ATR: -46 SELL, -44%; +both: -48 SELL, -46%).

**Production Candidate:** D-21 fallback triggered correctly — committed recommendation is `v6.0 HybridEngine + fail-safe remains production` (literal string present in script at lines 593 and 608, and in report line 107). This is the expected and correct outcome given that no v9 scenario passed VAL-03.

**Phase 42 readiness:** All scope boundary files (`docs/rules_mdm_hybrid.md`, `dashboard/`) are untouched per git diff. Phase 42 can consume the committed recommendation verbatim from the report.

**Note on baseline SELL-count drift (informational, NOT a gap):** Baseline SELL count in current measurement is 105 vs the ROADMAP historical anchor of 124. This is documented in summary line 170 ("The engine may have drifted; diagnostic: current baseline CAGR 10.70% vs recorded 11.5% (0.8pp gap)"). The Phase 41 report correctly uses the actual measured baseline (105) for delta computations while still echoing the 124/84% anchor to satisfy the success criterion text. This drift is a v10.0 concern and explicitly deferred per summary.

---

*Verified: 2026-04-21T05:30:00Z*
*Verifier: Claude (gsd-verifier)*
