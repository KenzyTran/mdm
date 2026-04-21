---
phase: 41-ab-walk-forward-validation
plan: 02
subsystem: validation
tags: [python, pandas, numpy, hybrid-engine, validation, walk-forward, ab-testing, vn30, whipsaw]

# Dependency graph
requires:
  - phase: 41-ab-walk-forward-validation
    provides: validate_v9.py scaffold (load_locked_params, run_engine, compute_metrics, build_scenario_configs, main-stub) + SCENARIOS_CSV constant + stub output/v9_ab_comparison.txt
  - phase: 40-grid-search-sweeps
    provides: locked ATR/DD params (output/v9_{atr,dd}_best.json), whipsaw metrics schema
provides:
  - Complete VAL-01..VAL-04 validation script analysis/validate_v9.py (569 lines)
  - output/v9_ab_comparison.txt human-readable unified report with 4 VAL sections + DD-only bias caveat + Production Candidate recommendation
  - output/v9_ab_scenarios.csv machine-readable per-scenario table (4 v9 scenarios + B&H VN30 reference row, 17 canonical columns including walk-forward train/test CAGR + degradation + whipsaw deltas)
  - Committed Phase 41 production-candidate recommendation: **v6.0 HybridEngine + fail-safe remains production** (all 3 v9 scenarios FAIL VAL-03 on full 2015-2026)
affects: [42-documentation-and-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Full-period run-once, slice-by-date for Test metrics (D-08 indicator warmup continuity)"
    - "Pairwise baseline Sharpe comparison for VAL-03 (not absolute threshold) — baseline excluded from verdict loop"
    - "Parsimony tiebreak for production candidate (ATR-only vs ATR+DD at 5% relative Sharpe margin)"
    - "Committed recommendation + fallback literal (D-21 v6.0 retention) — not data-only reports"
    - "Canonical CSV column order via explicit csv_df[[...]] slicing (not dict-iteration dependent)"

key-files:
  created:
    - output/v9_ab_comparison.txt (110 lines, 7368 bytes — full VAL-01..04 + DD caveat + Production Candidate)
    - output/v9_ab_scenarios.csv (6 lines: header + 4 v9 + B&H, 17 columns)
  modified:
    - analysis/validate_v9.py (+330 lines: module-level SCENARIO_ORDER, VAL-01 A/B table, VAL-04 whipsaw diagnostic, VAL-02 walk-forward, DD-only bias caveat, VAL-03 success criterion, failure-mode writeup, CSV writer, Production Candidate section)

key-decisions:
  - "Baseline excluded from VAL-03 verdict loop (D-15): baseline is the reference, not a candidate — only +ATR, +DD, +both get pass/fail verdicts"
  - "MaxDD pass condition uses `> SUCCESS_MAXDD` (-25.0) because MaxDD is stored as negative number — greater-than means less drawdown"
  - "Full-period results cached once per scenario in full_results dict then sliced for Test metrics via date >= TEST_START, preserving indicator warmup continuity (MA50/MA200/ATR warmup)"
  - "Train run is SEPARATE engine run on df<=TRAIN_END (D-09) so Train CAGR reflects engine that never saw post-2021 data"
  - "upper-bound estimate phrase (lowercase) used in DD-only bias caveat to match D-07 spec text verbatim — not 'UPPER-BOUND' as first-draft used"
  - "Parsimony tiebreak: if +both is top and +ATR within 5% relative Sharpe margin, prefer +ATR (not executed in this run since no v9 passed)"
  - "All 3 v9 scenarios fail VAL-03 on full 2015-2026: CAGR gaps +1.47pp (+DD) to +2.72pp (+ATR), Sharpe 0.369-0.417 vs baseline 0.461, MaxDD -29% to -33% vs -25% gate — Phase 41 recommends v6.0 retention (D-21)"
  - "Closest-to-criterion scenario in failure-mode: +DD at CAGR 10.03% (1.47pp below gate) — not +ATR (CAGR 8.78%). This inverts Phase 40 grid-search expectation that ATR-only would be the top candidate. Hypothesis: 2022-2026 OOS regime hostile to ATR buffer widening"

patterns-established:
  - "Unified Phase 41-style validation script: 4 VAL sections embedded in single report, committed production-candidate recommendation as final section, machine-readable CSV sibling for downstream parsing"
  - "Fail-loud per scenario (Phase 40 D-10): traceback captured in report but execution continues with NaN metrics — final verdict and CSV row still emitted; prevents one broken scenario from killing the entire validation run"
  - "D-21 committed fallback literal ('v6.0 HybridEngine + fail-safe remains production') — Phase 42 reads a single string from report rather than interpreting metric tables"

requirements-completed: [VAL-01, VAL-02, VAL-03, VAL-04]

# Metrics
duration: ~6min
completed: 2026-04-21
---

# Phase 41 Plan 02: A/B + Walk-Forward + Whipsaw + Production Candidate Summary

**Complete VAL-01..VAL-04 validation of v9.0 (ATR Buffer + Refined DD) vs v6.0 baseline on VN30 2015-2026 — all 3 v9 scenarios FAIL VAL-03 on full-period, Phase 41 recommends v6.0 retention (D-21)**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-21T03:55:33Z
- **Completed:** 2026-04-21T04:01:43Z
- **Tasks:** 2
- **Files modified:** 1 (analysis/validate_v9.py)
- **Files created:** 2 (output/v9_ab_comparison.txt, output/v9_ab_scenarios.csv)

## Accomplishments

1. **4-scenario A/B comparison on full 2015-2026** (VAL-01) with B&H VN30 reference row (D-17):

   | Scenario  | TotRet  | CAGR   | MaxDD   | Sharpe_rf3 | Trans | BUY%  | CASH% | SELL% |
   | --------- | ------- | ------ | ------- | ---------- | ----- | ----- | ----- | ----- |
   | baseline  | +213.4% | 10.70% | -28.63% | 0.461      | 296   | 29.8% | 38.8% | 31.4% |
   | +ATR      | +157.5% | 8.78%  | -33.40% | 0.369      | 220   | 30.0% | 46.5% | 23.5% |
   | +DD       | +192.7% | 10.03% | -29.03% | 0.417      | 297   | 30.8% | 38.0% | 31.2% |
   | +both     | +161.4% | 8.93%  | -33.40% | 0.376      | 214   | 30.7% | 45.6% | 23.7% |
   | B&H VN30  | +205.1% | 10.44% | -48.14% | —          | —     | 100%  | 0%    | 0%    |

2. **Walk-forward validation** (VAL-02) Train 2015-2021 / Test 2022-2026:

   | Scenario | CAGR_tr | CAGR_te | Degradation | Verdict                                    |
   | -------- | ------- | ------- | ----------- | ------------------------------------------ |
   | baseline | 12.39%  | 8.01%   | +35.4%      | PASS (within 50% threshold)                |
   | +ATR     | 14.14%  | 0.51%   | +96.4%      | FAIL (exceeds threshold by nearly 2x)      |
   | +DD      | 13.58%  | 4.45%   | +67.2%      | FAIL                                       |
   | +both    | 13.55%  | 1.74%   | +87.2%      | FAIL                                       |

   All 3 v9 scenarios FAIL walk-forward — massive train-test CAGR degradation indicates in-sample overfitting.

3. **Whipsaw diagnostic** (VAL-04) vs baseline 105 SELL signals:

   | Scenario | SELL# | MA50% | BUY# | Δ SELL | Δ MA50% | Whipsaw reduction                |
   | -------- | ----- | ----- | ---- | ------ | ------- | -------------------------------- |
   | baseline | 105   | 100%  | 27   | 0      | 0%      | —                                |
   | +ATR     | 59    | 100%  | 41   | -46    | 0%      | -43.8% SELL count (whipsaw down) |
   | +DD      | 106   | 100%  | 27   | +1     | 0%      | +1.0% (no reduction)             |
   | +both    | 57    | 100%  | 40   | -48    | 0%      | -45.7% SELL count                |

   ATR Buffer reduces SELL count by ~44-46%, but metrics degrade — whipsaw reduction came at the cost of ~22-24% absolute CAGR.

4. **VAL-03 success criterion (CAGR ≥ 11.5% AND (Sharpe > 0.461 OR MaxDD > -25%)):** ALL FAIL

   | Scenario | CAGR gap | Sharpe gap   | MaxDD gap     | Verdict                          |
   | -------- | -------- | ------------ | ------------- | -------------------------------- |
   | +ATR     | -2.72pp  | -0.092       | -8.40pp       | FAIL (CAGR ✗, Sharpe ✗, MaxDD ✗) |
   | +DD      | -1.47pp  | -0.044       | -4.03pp       | FAIL (CAGR ✗, Sharpe ✗, MaxDD ✗) |
   | +both    | -2.57pp  | -0.085       | -8.40pp       | FAIL (CAGR ✗, Sharpe ✗, MaxDD ✗) |

5. **DD-only bias caveat (D-07)** present as 8-line Methodological Note paragraph with verbatim phrases "DD-only bias caveat", "atr_buffer_enabled=True", "upper-bound estimate".

6. **Production Candidate** (D-19 FINAL section, D-20 committed recommendation): **"v6.0 HybridEngine + fail-safe remains production"** per D-21 fallback trigger. Phase 42 (docs + dashboard + audit) consumes this literal string.

7. **Script runs end-to-end with exit code 0** (D-14) regardless of VAL-03 verdict.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add VAL-01 A/B table + VAL-04 whipsaw diagnostic** — `e2eaafa` (feat)
2. **Task 2: Add VAL-02 walk-forward + VAL-03 verdict + DD-only bias caveat + Production Candidate section + CSV writer** — `92afd4f` (feat)

## Files Created/Modified

- `analysis/validate_v9.py` — Complete Phase 41 validation script (Plan 41-01 scaffold + Plan 41-02 fill-in). Module-level `SCENARIO_ORDER = ['baseline', '+ATR', '+DD', '+both']`, 4 VAL sections, DD-only caveat, Production Candidate section as final, CSV writer with 17 canonical columns, single `sys.exit(0)` at end.
- `output/v9_ab_comparison.txt` — 110-line unified VAL-01..04 report + Methodological Note + Production Candidate (7368 bytes). Gitignored; regenerated by script.
- `output/v9_ab_scenarios.csv` — 6-line (5 data + header) per-scenario table with 17 columns: scenario, sharpe_rf3, cagr_pct, max_dd_pct, total_return_pct, transitions, sell_count, ma50_breakdown_sell_share, buy_count, buy_pct, cash_pct, sell_pct, sell_count_delta, ma50_share_delta, cagr_train, cagr_test, cagr_degradation. B&H VN30 row included per D-17. Gitignored.

## Decisions Made

- **Baseline excluded from VAL-03 verdict loop** (D-15 fidelity): The baseline is the pairwise reference for Sharpe comparison; it cannot simultaneously be evaluated as a candidate against itself. VAL-03 verdicts reported for +ATR, +DD, +both only.
- **MaxDD comparison `> SUCCESS_MAXDD` (-25.0)** not `<`: MaxDD is stored as negative number (e.g., -28.63%), so "better than -25%" means "MaxDD value > -25" (closer to zero).
- **Train run is independent engine execution**, not a slice of full results: `train_df = df_full[df_full['date'] <= TRAIN_END].copy()` then `run_engine(train_df, cfg)`. Matches D-09 precedent and ensures Train metrics reflect an engine that never saw post-2021 data.
- **Test metrics slice from cached full-period results**: preserves indicator warmup continuity (MA50 needs 50 days, MA200 needs 200 days, ATR needs N days). Slicing `r_full[r_full['date'] >= TEST_START]` gives clean Test-window state without re-warming indicators.
- **Upper-bound caveat phrasing** — Plan's action block had "UPPER-BOUND" (caps) but D-07 CONTEXT.md spec + acceptance criterion grep are lowercase "upper-bound estimate". Fixed during Task 2 to match spec verbatim.
- **Parsimony tiebreak (D-18)** implemented but not triggered in this run (no v9 scenario passed VAL-03 so the fallback branch executed instead).
- **D-21 fallback recommendation** — literal string `'v6.0 HybridEngine + fail-safe remains production'` emitted as the committed recommendation since `any_pass=False`. Phase 42 docs and dashboard will reflect v6.0 retention.
- **Closest-to-criterion scenario is +DD, not +ATR** — this inverts Phase 40 Stage-2 finding that DD added zero alpha over ATR-only. In full-period 2015-2026 (vs Phase 40 train-only 2015-2021), DD beat ATR-only by +1.25pp CAGR and +0.048 Sharpe. Hypothesis: the 2022-2026 OOS window is hostile to ATR buffer widening (which increased CASH% from 38.8% to 46.5%, starving the book of exposure during Vietnam's 2023-2024 recovery).

## Deviations from Plan

**One minor deviation:** The plan's embedded action code used `log('they represent an UPPER-BOUND estimate...')` (capitalized), but the plan's own acceptance criterion grep (`grep "upper-bound estimate" analysis/validate_v9.py`) and D-07 CONTEXT.md spec both use lowercase. Adjusted to lowercase during Task 2 to satisfy spec + acceptance criteria. This is **Rule 1 (bug fix)** — the capitalization mismatch would have caused the acceptance-criteria grep to return 0 matches. No new functionality added; purely a spec-compliance fix.

**Committed in:** `92afd4f` (Task 2 commit).

**Total deviations:** 1 auto-fixed (1 spec-compliance bug).

**Impact on plan:** Zero scope creep; fix was exactly what the acceptance criterion demanded.

## Issues Encountered

- **Windows LF→CRLF git warning** on both commits — benign git noise, no content mutation. File parses and runs correctly under `uv run python`.
- **No functional issues.** First end-to-end run after Task 2 produced all 4 VAL sections + caveat + Production Candidate in the expected order.

## Next Phase Readiness

**Ready for Phase 42 (Documentation + Dashboard + Audit):**
- Production-candidate recommendation is committed as literal string in `output/v9_ab_comparison.txt` — Phase 42 DOC-03 audit report can quote verbatim
- `output/v9_ab_scenarios.csv` provides machine-readable per-scenario metrics for Phase 42 dashboard data build (if needed; Phase 42 may re-run engine for signal-log emission per CONTEXT.md scope)
- `docs/rules_mdm_hybrid.md` untouched (Phase 42 DOC-01 scope)
- `dashboard/data/` untouched (Phase 42 DOC-02 scope)
- Phase 42 decision tree is unambiguous: v6.0 retention path means docs/dashboard describe v6.0 as production, v9 modules stay as feature-flagged-off research code with Phase 40 in-sample provenance documented

**Concerns (feed into v10.0 planning, NOT Phase 42):**
- Walk-forward degradation +67% to +96% on all v9 scenarios suggests the ATR Buffer + Refined DD tuning overfit Phase 40's 2015-2021 train window badly. Future work should widen train window or use walk-forward cross-validation in the grid search itself, not post-hoc.
- VAL-03 uses BASELINE Sharpe (0.461) as the bar, but baseline is much weaker than the memory-recorded v6.0 (STATE.md lists 0.461 derived here on current engine vs project_best_model.md v6.0 reference CAGR 11.5%/MaxDD -28.2%). The engine may have drifted; diagnostic: current baseline CAGR 10.70% vs recorded 11.5% (0.8pp gap). v10.0 should reconcile before declaring a new production candidate.

## Self-Check: PASSED

Verified existence of all claimed artifacts:
- `analysis/validate_v9.py`: FOUND (parses via `python -c "import ast; ast.parse(open('analysis/validate_v9.py').read())"`)
- `output/v9_ab_comparison.txt`: FOUND (110 lines, 7368 bytes, all 4 VAL headers + DD caveat + Production Candidate)
- `output/v9_ab_scenarios.csv`: FOUND (5 data rows, 17 canonical columns, B&H VN30 row present)
- Task commit `e2eaafa`: FOUND in git log
- Task commit `92afd4f`: FOUND in git log
- Script exits 0 end-to-end under `uv run python analysis/validate_v9.py`
- `grep -c "sys.exit(0)" analysis/validate_v9.py` returns 1 (only exit, end of main)
- `grep -c "v6.0 HybridEngine + fail-safe remains production" analysis/validate_v9.py` returns 2 (D-21 fallback literal appears in both the top-level branch and the fallback-within-pass branch)
- `grep -c "v9.0 production candidate" analysis/validate_v9.py` returns 1 (D-20 positive-path string)
- `docs/rules_mdm_hybrid.md` untouched: `git diff --name-only` returns empty
- `dashboard/` untouched: `git diff --name-only dashboard/` returns empty
- Plan-level CONTEXT.md decision fidelity: D-03 (2 artifacts), D-05 (4 scenarios + monotone order), D-07 (DD-only bias caveat with all required phrases), D-08/D-09 (train-separate / test-sliced), D-10 (degradation formula), D-14 (sys.exit 0 always), D-15 (VAL-03 sole gate, baseline excluded), D-17 (B&H row in table AND CSV), D-19 (Production Candidate final section), D-20 (committed recommendation), D-21 (v6.0 retention fallback triggered and literal string emitted) — all verified

---
*Phase: 41-ab-walk-forward-validation*
*Completed: 2026-04-21*
