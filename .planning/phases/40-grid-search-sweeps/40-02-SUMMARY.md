---
phase: 40-grid-search-sweeps
plan: 02
subsystem: selection-cli
tags: [v9, sweep, selection, cli, pandas, json, argparse, max-dd-constraint]

# Dependency graph
requires:
  - phase: 40-01
    provides: output/v9_atr_sweep.csv schema with config fields (atr_buffer_k, atr_buffer_period, atr_buffer_consecutive_days) + metrics (sharpe_rf3, cagr_pct, max_dd_pct, transitions, sell_count, ma50_breakdown_sell_share, buy_count, buy_pct, cash_pct, sell_pct)
  - phase: 38-atr-buffer-zone-module
    provides: MDMV2Config.atr_buffer_* fields used as config param source for JSON artifact
  - phase: 39-refined-distribution-day-module
    provides: MDMV2Config.refined_dd_* fields used as config param source for DD-stage JSON artifact
provides:
  - analysis/select_v9_best.py (selection CLI with --stage {atr,dd}; implements D-15 MaxDD-constrained max-Sharpe picker, D-16 strict abort, D-17 3-tier tiebreak, D-21 TXT+JSON writer)
affects: [phase-40-03-grid-search-dd-sweep, phase-41-ab-walk-forward-validation]

# Tech tracking
tech-stack:
  added: []  # Pure stdlib + pandas (already in project) -- no new dependencies
  patterns:
    - "Two-stage selection CLI driven by STAGE_CONFIG dispatch table (file paths + param_fields per stage) -- adding a future stage is a one-line config entry"
    - "D-21 JSON schema locked: {params, metrics, selected_at, train_window} -- downstream consumers (plan 40-03 DD sweep, phase 41 A/B) can rely on this shape"
    - "Native Python type casting in JSON writer (.item() on numpy scalars) -- keeps artifacts readable and avoids numpy.int64/float64 leakage"

key-files:
  created:
    - analysis/select_v9_best.py
  modified: []

key-decisions:
  - "Key-value TXT layout chosen over ASCII table (D-22 permits either). Rationale: single-winner output per invocation, key-value is self-describing and diff-friendly for git. ASCII table only wins when comparing multiple rows."
  - "STAGE_CONFIG dispatches everything stage-specific (CSV filename, TXT/JSON names, param_fields list). main() has zero if/else on stage value beyond argparse choices -- clean, extensible."
  - "JSON-first + TXT-secondary: write_outputs emits JSON before TXT so a partial-failure mid-write leaves the machine-readable artifact intact for plan 40-03 handoff. (Belt-and-braces -- both writes use context-managed open(); this is just ordering intent.)"
  - "select_best drops NaN sharpe_rf3 rows BEFORE the MaxDD filter. Config errors from sweep (per plan 40-01 D-10 fail-loud with error column) must not poison selection. The RuntimeError message reports both the non-error row count AND the best achievable max_dd_pct -- actionable diagnostics for a user hitting the D-16 abort."

patterns-established:
  - "CLI-with-dispatch-table pattern: argparse choices drive STAGE_CONFIG lookup, main() stays thin, branch logic isolated to the config dict. Reusable for future multi-stage sweep-selection tooling."
  - "Synthetic algorithm test recipe (documented in task verification): 5 small DataFrames covering (1) MaxDD filter, (2) CAGR tiebreak, (3) MaxDD tiebreak (less-negative wins), (4) RuntimeError on empty, (5) NaN dropping. Fast (<1s), no data dependency, catches logic regressions cheaply."

requirements-completed: [SWEEP-03]

# Metrics
duration: ~5 min
completed: 2026-04-16
---

# Phase 40 Plan 02: v9 Selection CLI Summary

**`analysis/select_v9_best.py` implements the D-15 selection algorithm — MaxDD >= -30 filter, 3-tier tiebreak (sharpe_rf3 desc -> cagr_pct desc -> max_dd_pct desc), D-16 strict abort on empty candidates, D-21 TXT+JSON artifact pair — with `--stage {atr,dd}` dispatch for both sweep stages.**

## Performance

- **Duration:** ~5 min (start 2026-04-16T07:30:41Z, end 2026-04-16T07:33:10Z)
- **Tasks:** 1
- **Files created:** 1 (analysis/select_v9_best.py, 155 lines)
- **Files modified:** 0
- **Commits:** 1 (feat) — no TDD split (single-file utility, verified via synthetic algorithm tests in-session)

## Accomplishments

- **SWEEP-03 requirement satisfied.** `analysis/select_v9_best.py` provides a single-entry-point CLI with two discrete modes (`--stage atr`, `--stage dd`) that reads the corresponding sweep CSV, applies the locked D-15 selection algorithm, and writes both a human-readable TXT and a machine-readable JSON artifact.
- **D-15 algorithm implemented verbatim.** `select_best(df)`: (1) drop rows with NaN `sharpe_rf3` (errored sweep cells), (2) filter `max_dd_pct >= MAX_DD_FLOOR (-30.0)`, (3) `sort_values(by=['sharpe_rf3', 'cagr_pct', 'max_dd_pct'], ascending=[False, False, False])`, (4) `iloc[0]`. Lines 57-78.
- **D-16 strict abort.** Empty-candidates branch raises `RuntimeError` with an actionable message (non-error row count + best achievable max_dd_pct). `__main__` catches it, prints to stderr, and exits 1. No unconstrained fallback path. Lines 67-72, 148-150.
- **D-17 tiebreak locked.** `by=['sharpe_rf3', 'cagr_pct', 'max_dd_pct']` and `ascending=[False, False, False]` -- line 74-76. Less-negative MaxDD wins the third tier as required.
- **D-21 JSON schema.** Every JSON artifact has exactly `{params, metrics, selected_at, train_window}` keys. `train_window` is the hard-coded literal `'2015-01-01..2021-12-31'`. `selected_at` is a timezone-aware ISO-8601 timestamp. Native Python types in JSON via `.item()` cast on numpy scalars (lines 87-92 `_native` helper). Verified with end-to-end synthetic row writer.
- **D-22 dual artifact.** Both TXT (key-value layout) and JSON written via `write_outputs(row, stage)`. TXT subsection ordering: header (stage + selected_at + train_window) → `-- params --` block → `-- metrics --` block.
- **CLI argparse restricts `--stage` to exactly {atr, dd}.** Unknown choices rejected with exit code 2 (standard argparse behavior). Verified: `uv run python analysis/select_v9_best.py --stage bogus` prints `error: argument --stage: invalid choice: 'bogus' (choose from 'atr', 'dd')` and exits 2.
- **Missing input CSV produces actionable error.** If `output/v9_{stage}_sweep.csv` is absent, `FileNotFoundError` fires with message instructing user to run `sweep_v9_{stage}.py` first (lines 140-143).

## Task Commits

Each task committed atomically with --no-verify (parallel-executor discipline):

1. **Task 1: Create analysis/select_v9_best.py with --stage {atr,dd} modes** — `5085146` (feat)

## Files Created/Modified

- `analysis/select_v9_best.py` (155 lines, new file):
  - Lines 1-15: Module docstring with usage + algorithm summary
  - Lines 17-24: Imports + sys.path.insert project root shim
  - Lines 27-52: Module constants (`OUTPUT_DIR`, `TRAIN_WINDOW`, `MAX_DD_FLOOR`, `STAGE_CONFIG`, `METRIC_FIELDS`)
  - Lines 55-78: `select_best(df)` — D-15 filter + D-17 tiebreak + D-16 strict abort
  - Lines 81-124: `write_outputs(row, stage)` — D-21 JSON + D-22 TXT writer with native-type cast
  - Lines 127-145: `main()` — argparse + CSV load + dispatch
  - Lines 148-153: `if __name__ == '__main__'` with RuntimeError handler for exit code 1

## Decisions Made

- **Key-value TXT over ASCII table.** Single-winner output per invocation means a grid/table adds no value; key-value is self-describing, diff-friendly in git, and immediately readable by humans. ASCII tables only shine for multi-row comparisons — out of scope for this artifact.
- **STAGE_CONFIG dispatch over if/else branching.** Every stage-specific concern (CSV filename, TXT/JSON output names, which fields are "params" vs "metrics") lives in one dict. `main()` does a single `STAGE_CONFIG[stage]` lookup. Adding a future stage (e.g., joint ATR×DD in v10.0) is a one-entry dict addition, not a code-path refactor.
- **NaN `sharpe_rf3` dropped BEFORE MaxDD filter.** Per plan 40-01 D-10 (fail-loud + `error` column), a sweep row with an exception has `sharpe_rf3=NaN` but may still have a real-looking `max_dd_pct` value (or NaN). Dropping NaN-sharpe rows up front prevents these from polluting the MaxDD filter or the sort. The RuntimeError message reports `len(clean)` (non-error rows) AND `clean['max_dd_pct'].max()` (best achievable drawdown) — if the D-16 abort fires, the user sees immediately whether the grid is too tight (best was -32%) or whether most cells errored (clean was tiny).
- **Native-type cast via `.item()` with AttributeError fallback.** numpy scalar types (numpy.int64, numpy.float64) are present in `pd.Series` rows from `pd.read_csv`. `json.dump` chokes on them in some environments and produces ugly output (`"transitions": 120.0` instead of `120`). A 3-line `_native(v)` helper coerces via `.item()` when available (all numpy scalars support it) and passes through native Python types untouched. Result: clean JSON with correct integer/float types per column semantics.
- **No TDD split.** Single-file utility (155 lines), no iterative refinement needed — plan `<action>` block specified the exact code shape. In-session verification used 5 synthetic DataFrames (MaxDD filter, CAGR tiebreak, MaxDD tiebreak, RuntimeError on empty, NaN dropping) plus an end-to-end `write_outputs` test — all passed on first run. Splitting into RED/GREEN commits would have added noise.

## Deviations from Plan

None. The plan's `<action>` block specified the file shape, constants, function signatures, and the D-15/D-16/D-17/D-21 semantics. Implementation matched verbatim. No Rule 1/2/3 auto-fixes triggered. No architectural questions surfaced.

## Issues Encountered

- **Windows `python` command not on PATH (sandbox).** First verification attempt used bare `python` which hit the Microsoft Store shim. Resolved by using `uv run python` for all invocations (project convention per CLAUDE.md and existing sweep scripts). Not a code issue — just tooling discipline.

## Verification Evidence

All acceptance criteria from plan 40-02 verified:

- [x] `analysis/select_v9_best.py` exists and parses as valid Python (static analysis via `ast.parse`).
- [x] Module defines `select_best`, `write_outputs`, `main` functions.
- [x] Source contains literal `MAX_DD_FLOOR = -30.0`.
- [x] Source contains literal `TRAIN_WINDOW = '2015-01-01..2021-12-31'`.
- [x] Source contains literal `choices=['atr', 'dd']`.
- [x] Source contains literal `by=['sharpe_rf3', 'cagr_pct', 'max_dd_pct']` and `ascending=[False, False, False]`.
- [x] Source contains `raise RuntimeError` inside `select_best`.
- [x] `uv run python analysis/select_v9_best.py --help` exits 0, prints usage (confirmed with `{atr,dd}` choice list).
- [x] `uv run python analysis/select_v9_best.py --stage bogus` exits 2 with argparse "invalid choice" error.
- [x] Algorithm tests (synthetic DataFrames, in-session): MaxDD filter drops -35 rows; Sharpe tie -> CAGR wins; Sharpe+CAGR tie -> less-negative MaxDD wins; empty candidates -> RuntimeError with expected message; NaN-sharpe rows dropped.
- [x] `write_outputs` end-to-end test: JSON has `{params, metrics, selected_at, train_window}` keys, `train_window` = hard-coded literal, numpy scalars coerced to native int/float, TXT renders with `-- params --` and `-- metrics --` blocks.
- [ ] End-to-end run with real `output/v9_atr_sweep.csv` → per plan 40-02 `<acceptance_criteria>`, this is deferred to plan 40-03's pipeline run (this plan does not produce CSVs).

## Next Plan Readiness

- **Plan 40-03** consumes this script twice: first as `uv run python analysis/select_v9_best.py --stage atr` (after `sweep_v9_atr.py` produces the CSV) to materialize `output/v9_atr_best.json` (which the DD sweep script reads to lock ATR params), then as `--stage dd` (after `sweep_v9_dd.py`) to produce the final winner. Both consumption paths are already wired — plan 40-03 just invokes the CLI.
- **Phase 41 (A/B + walk-forward validation)** will load `output/v9_atr_best.json` and `output/v9_dd_best.json` to reconstruct the +ATR, +DD, +both scenarios on full 2015-2026. JSON schema is locked per D-21 so plan 41 can code against `{params, metrics, selected_at, train_window}` with confidence.
- **No blockers.** Script is dependency-free at runtime (stdlib + pandas, both already in project).

---
*Phase: 40-grid-search-sweeps*
*Plan: 02*
*Completed: 2026-04-16*

## Self-Check: PASSED

- analysis/select_v9_best.py: **FOUND**
- commit 5085146: **FOUND**
