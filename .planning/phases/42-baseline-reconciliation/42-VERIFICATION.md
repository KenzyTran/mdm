---
phase: 42-baseline-reconciliation
verified: 2026-04-22T14:20:00Z
status: passed
score: 4/4 success criteria verified (BASE-01, BASE-02, BASE-03 all satisfied)
---

# Phase 42: Baseline Reconciliation Verification Report

**Phase Goal:** Close the v10.0 baseline drift loop — identify the commit(s) that caused CAGR drift from v6.0 (11.5%) to measured HEAD (10.70%), fix-forward so the HybridEngine reconciled HEAD reproduces v6.0 baseline within D-09 tolerance, and publish the canonical reconciled baseline tuple as machine + human SSoT for Phases 43-47.

**Verified:** 2026-04-22T14:20:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
|---|---------------------------|--------|----------|
| 1 | `docs/audits/v10_baseline_drift.md` exists with exact commit hash(es) that changed CAGR 11.5%→10.70% and SELL count 124→105, plus per-commit diff and root-cause narrative | VERIFIED | Audit doc at `docs/audits/v10_baseline_drift.md` (265 lines); Bisect Log table with 8 tested commits; offending commit `f80394f68b98925c47f0c66b9df1099576878ca0` identified with full hash, date, author, diff summary (33 insertions, 4 deletions in `strategies/mdm_hybrid/position_manager.py`); Root-Cause Narrative explains semantic change (outer elif + nested if makes cash-deterioration branch unreachable), quantifies drift (SELL 124→105, CAGR 11.47→10.70, MaxDD +0.46pp), classifies as inadvertent parity break |
| 2 | Running `HybridEngine + fail-safe` on VN30 2015-2026 reproduces shipped v6.0 CAGR within ±0.3pp (fix-forward preferred) | VERIFIED | Reconciled-HEAD parity (all three D-09 bands PASS): CAGR 11.47 ∈ [11.2, 11.8], SELL 124 ∈ [119, 129], MaxDD -28.17 ∈ [-29.2, -27.2]. Fix-forward via `v60_strict_mode` preset flag (D-07 STEP 2). Pytest regression confirms byte-exact determinism (3 fresh engines → len(set(cagrs))==1, len(set(maxdds))==1, etc.). |
| 3 | `tests/test_baseline_determinism.py` runs engine 3× on identical inputs asserting CAGR varies by ≤0.1pp (test committed and passes) | VERIFIED | Test file at `tests/test_baseline_determinism.py` (274 lines). `uv run pytest -m regression tests/test_baseline_determinism.py -v` exits 0, 3/3 PASSED in 26.89s. M5 tightening: primary assertions use byte-exact equality (`len(set(...)) == 1`), D-17's 0.1pp threshold retained as fallback message only. |
| 4 | A single "reconciled baseline" tuple (CAGR, MaxDD, Sharpe_rf3, SELL count) is published in audit doc and quoted by every downstream phase as gate reference | VERIFIED | `output/v10_reconciled_baseline.json` (19 keys, schema_version=1, all 18 D-12 fields, reconciliation_outcome=fixed_by_preset). Audit doc `## Reconciled Baseline` section has matching 18-row table. M1 byte-identical invariant verified externally — all 8 float fields' audit-cell strings equal `json.dumps(json_value)`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---------|---------|--------|---------|
| `analysis/bisect_v10_baseline.py` | CAGR gate script (BASE-01) | VERIFIED | 185 lines. Contains: CAGR_GATE=11.4, DATA_START='2015-01-05', DATA_END='2026-03-31', EXIT_SKIP=125, BISECT_RESULT emit (including NA path), inline design-note citing 11.2–11.8 parity band, `from analysis.validate_v9 import compute_metrics`, atr_buffer_enabled=False, refined_dd_enabled=False, two_phase_enabled=True, filter_enabled=False, v60_strict_mode=True (reconciliation-check preset). |
| `docs/audits/v10_baseline_drift.md` | Single-file audit with 9 sections populated | VERIFIED | 265 lines. All 9 required `##` sections present: Executive Summary, Bisect Endpoints, Reference Numbers, Bisect Log, Root-Cause Narrative, Reconciliation Outcome, Reconciled Baseline, Invariants, References. No `_To be populated_` placeholders remain. |
| `strategies/mdm_hybrid/config.py` | `v60_strict_mode` flag (BASE-02) | VERIFIED | `v60_strict_mode: bool = False` at line 89 of MDMV2Config. `v60_strict_mode=False` explicit in VN30_PRESET (line 174) and NASDAQ_PRESET (line 211). |
| `strategies/mdm_hybrid/position_manager.py` | Branch-guarded elif arm (BASE-02) | VERIFIED | Line 280: `elif getattr(self.config, 'v60_strict_mode', False):` — re-flattens CASH→SELL elif chain when strict mode active. No changes to fail-safe decision logic (D-11 invariant). |
| `docs/rules_mdm_hybrid.md` | Documented v60_strict_mode (Code-Docs Sync) | VERIFIED | Section XVIII with 7 subsections: 10 matches for `v60_strict_mode`. Covers background/drift, config params, affected code, strict-vs-default table, backward compat (Phase 38/39 fixtures), Phase 44/45/46 interactions, Phase 42 BASE-03 determinism usage. |
| `analysis/publish_v10_baseline.py` | Publisher script (BASE-02) | VERIFIED | 413 lines. SCHEMA_VERSION=1, FLOAT_DECIMALS=6, VALID_OUTCOMES tuple, CHOICE_LEAK_STR, STRICT_LABEL_RE, _round_floats, _render_cell, verify_byte_identical, parse_reconciliation_outcome (B2 hardened with 3 ValueError paths — choice-expression leak, multiple label-literals, zero/multi strict Label lines). Reuses `analysis.validate_v9.compute_metrics`. |
| `output/v10_reconciled_baseline.json` | 18-field tuple + schema_version=1 | VERIFIED | 19 keys total (schema_version + 18 D-12 fields). schema_version=1, cagr_pct=11.47, max_dd_pct=-28.17, sharpe_rf3=0.502414, sell_count=124, total_return_pct=238.78, transitions=334, buy_pct=30.36, cash_pct=37.5, sell_pct=32.14, ma50_breakdown_sell_share=0.83871, buy_count=27, run_start='2015-01-05', run_end='2026-03-31', engine_git_hash=a4248183…, python_version=3.10.20, pandas_version=2.3.3, numpy_version=2.2.6, reconciliation_outcome=fixed_by_preset. |
| `tests/test_baseline_determinism.py` | Pytest regression (BASE-03) | VERIFIED | 274 lines. @pytest.mark.regression class TestBaselineDeterminism with 3 tests: test_numeric_variance_across_3_runs (M5 byte-exact CAGR/MaxDD/Sharpe/SELL/transitions via `len(set(...))==1`), test_signal_log_byte_exact (results_1.equals(results_2)), test_reconciled_baseline_json_loadable (m4 D-14 guard, co-wave-4 tolerant via pytest.skip). All 3 pass in 26.89s. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `analysis/bisect_v10_baseline.py` | `core.data_loader.DataLoader` | `DataLoader('vn30').load(DATA_START, DATA_END)` | WIRED | loader.load() call at line 153 |
| `analysis/bisect_v10_baseline.py` | `HybridEngine` | `HybridEngine(HybridConfig(...))` | WIRED | engine construction at lines 159-161 |
| `analysis/bisect_v10_baseline.py` | `compute_metrics` | `from analysis.validate_v9 import compute_metrics` | WIRED | import at line 124, call at line 166 |
| `docs/audits/v10_baseline_drift.md` | `output/v6_combined_validation.txt` | cited as v6.0 truth-of-record | WIRED | referenced in Executive Summary + Reference Numbers section |
| `docs/audits/v10_baseline_drift.md` | `output/v9_ab_comparison.txt` | cited as measured-today drift | WIRED | referenced in Executive Summary + Reference Numbers section |
| `docs/audits/v10_baseline_drift.md` | `analysis/bisect_v10_baseline.py` | cited as gate script | WIRED | referenced in Bisect Log + References section |
| `docs/audits/v10_baseline_drift.md` | `strategies/mdm_hybrid/config.py` | cites v60_strict_mode field and default | WIRED | Reconciliation Outcome → Artifacts Produced lists config.py change |
| `analysis/publish_v10_baseline.py` | `output/v10_reconciled_baseline.json` | `json.dump` with schema_version=1 + 18 fields | WIRED | write_json() at publisher; JSON on disk has schema_version=1 + all 18 D-12 fields |
| `docs/audits/v10_baseline_drift.md` | `output/v10_reconciled_baseline.json` | numbers in Reconciled Baseline table match JSON byte-identical | WIRED | M1 verified externally: all 8 float fields byte-equal |
| `tests/test_baseline_determinism.py` | `HybridEngine` | 3 fresh engines, byte-exact equality | WIRED | _run_once() helper constructs HybridEngine(HybridConfig(...)); fixture feeds 3 runs |
| `tests/test_baseline_determinism.py` | `compute_metrics` | reuses canonical metrics | WIRED | stdout-safe lazy import _get_compute_metrics() (satisfies acceptance grep) |
| `tests/test_baseline_determinism.py` | `output/v10_reconciled_baseline.json` | schema+type regression guard | WIRED | test_reconciled_baseline_json_loadable reads JSON, asserts schema_version=1 + 18 fields + types |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `output/v10_reconciled_baseline.json` | all 18 metric/meta fields | `compute_metrics(results)` ← `HybridEngine.run(df)` ← `DataLoader('vn30').load(...)` + `build_indicator_dataframe(df)` | Yes — real VN30 OHLCV data flows through DataLoader → indicators → engine → metrics; schema_version + env pins are from `sys.version`, `pd.__version__`, `np.__version__`, `git rev-parse HEAD` | FLOWING |
| Audit doc `## Reconciled Baseline` table | 18 field values | `_render_cell(tup[field])` ← `_round_floats(tup)` ← `compute_metrics(results)` (same pipeline as JSON) | Yes — same in-memory tuple feeds both JSON and audit doc via the same `json.dumps`-based formatter (M1 invariant guarantees byte-identical) | FLOWING |
| Bisect Log table | CAGR/SELL/MaxDD per commit | `BISECT_RESULT` stdout lines from `analysis/bisect_v10_baseline.py` at each tested commit | Yes — `compute_metrics(engine.run(df))` at each bisect-tested commit; 8 real rows in table, trajectory monotone | FLOWING |
| `tests/test_baseline_determinism.py` test assertions | CAGR/MaxDD/Sharpe/SELL/trans across 3 runs + DataFrame equality across 2 runs | `HybridEngine(...).run(df.copy())` × 3 fresh instances; `compute_metrics(results)` per run | Yes — 3 live engine runs on VN30 2015-2026 full window; all 5 `len(set(...)) == 1` primary gates pass; signal log `.equals()` passes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Determinism tests pass | `uv run pytest -m regression tests/test_baseline_determinism.py -v` | 3 passed in 26.89s, exit 0 | PASS |
| JSON schema validity | `python -c "import json; d=json.load(open('output/v10_reconciled_baseline.json')); assert d['schema_version']==1; …"` | JSON OK: 19 keys, outcome=fixed_by_preset, cagr=11.47, sell=124, maxdd=-28.17 | PASS |
| M1 byte-identical invariant (external re-check) | `python -c "…json.dumps(v) vs audit-doc cell…"` for all float fields | M1 byte-identical check: PASSED for all float fields | PASS |
| B2 strict Label line (exactly 1) | `grep -cE "^Label: \`(fixed_by_revert\|fixed_by_preset\|accepted_drift)\`$" docs/audits/v10_baseline_drift.md` | 1 | PASS |
| B2 no choice-expression leak | `grep -c "fixed_by_revert \| fixed_by_preset" docs/audits/v10_baseline_drift.md` | 0 | PASS |
| 9 required audit sections present | `grep -cE "^## (Executive Summary\|Bisect Endpoints\|Reference Numbers\|Bisect Log\|Root-Cause Narrative\|Reconciliation Outcome\|Reconciled Baseline\|Invariants\|References)$" docs/audits/v10_baseline_drift.md` | 9 | PASS |
| D-11 invariant (no fail-safe decision-logic changes) | `git diff 3601679c..HEAD -- strategies/mdm_hybrid/position_manager.py \| grep -iE "fail_safe_exit\|fail_safe_enabled\|fail_safe_threshold > 0\|close > self.position.fail_safe\|_check_fail_safe"` | empty (0 matches) | PASS |
| All 6 phase commits exist | `git log --oneline --all \| grep -E "784c8b8\|3ec448f\|a424818\|8c6722b\|cbff877\|5f8c4af"` | 6 commits found | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BASE-01 | 42-01, 42-02, 42-03 | Forensic audit — identify commit(s) causing CAGR drift 11.5%→10.70% + SELL drift 124→105; produce `docs/audits/v10_baseline_drift.md` with commit hashes, diffs, root cause | SATISFIED | Offending commit `f80394f` identified. Bisect log has 8 rows. Root-Cause Narrative explains semantic change (CASH→SELL elif refactor making cash_deterioration branch unreachable). REQUIREMENTS.md line 10: `[x] BASE-01`. |
| BASE-02 | 42-04, 42-05 | Reconciled baseline — fix forward so HybridEngine+fail-safe matches v6.0 shipped CAGR within ±0.3pp | SATISFIED | `v60_strict_mode` preset flag lands in MDMV2Config + V2PositionManager branch-guard. Reconciled-HEAD: CAGR 11.47, SELL 124, MaxDD -28.17 — all 3 D-09 bands pass. Published tuple in `output/v10_reconciled_baseline.json`. REQUIREMENTS.md line 11: `[x] BASE-02`. |
| BASE-03 | 42-06 | Regression test — engine run determinism (same inputs → CAGR ±0.1pp across 3 runs); test committed under `tests/test_baseline_determinism.py` | SATISFIED | `tests/test_baseline_determinism.py` (274 lines). M5 tightening: byte-exact (len(set(...))==1) primary assertions stronger than D-17's 0.1pp threshold. Tests pass in 26.89s, 3/3 green. REQUIREMENTS.md line 12: `[x] BASE-03`. |

No orphaned requirements found — all 3 BASE IDs accounted for across the 6 plans; all 3 marked `[x]` in REQUIREMENTS.md.

### Anti-Patterns Found

None detected. Scan results:

- No `TODO`/`FIXME`/`XXX`/`PLACEHOLDER` anti-patterns found in modified files
- No `_To be populated by plan_` placeholders remaining in audit doc (all 4 initial placeholders replaced by subsequent plans)
- Stubs/stub patterns only in audit doc + summaries (not executable code) — no runtime impact
- `BISECT_RESULT: cagr=NA sell=NA max_dd=NA` appears intentionally as the NA-emitting skip path (documented in plan 42-01 as the M3 invariant)
- Commented-out `# from analysis.validate_v9 import compute_metrics` in test file is intentional (documentation hint for the stdout-safe lazy-import pattern — still satisfies acceptance grep)

### D-09 Parity Band Verification (explicit numeric check)

| Metric | Reference (v6.0) | Reconciled-HEAD | Band (D-09) | Pass? |
|--------|------------------|-----------------|-------------|-------|
| CAGR (%) | 11.5 | 11.47 | [11.2, 11.8] | PASS (delta -0.03pp) |
| SELL count | 124 | 124 | [119, 129] | PASS (delta 0) |
| MaxDD (%) | -28.2 | -28.17 | [-29.2, -27.2] | PASS (delta +0.03pp) |

All three D-09 bands satisfied simultaneously at reconciled-HEAD commit `a4248183b63674aef2cb707355a6fc9b4eaeb3b4`.

### D-11 Invariant Verification (no fail-safe decision-logic changes)

```
git diff 3601679cdba9c3ea674904e6f8a9aa24273cb6ad..HEAD -- strategies/mdm_hybrid/position_manager.py | grep -iE "fail_safe_exit|fail_safe_enabled|fail_safe_threshold > 0|close > self.position.fail_safe|_check_fail_safe"
→ (empty output — 0 matches)
```

The only `fail_safe` mentions in the diff are `fail_safe_threshold=prev_high` kwarg pass-throughs to `enter_sell(...)` inside the new strict-mode branch — these mirror the existing non-strict branches and do NOT modify fail-safe decision logic. D-11 VERIFIED.

### M1 Byte-Identical Invariant Verification (audit doc ↔ JSON)

External re-check performed (not relying on publisher's own verify_byte_identical):

```python
python -c "
import json, re
d = json.load(open('output/v10_reconciled_baseline.json'))
t = open('docs/audits/v10_baseline_drift.md').read()
fails = []
for k, v in d.items():
    if isinstance(v, float):
        m = re.search(rf'^\| {re.escape(k)} \| (.*) \|$', t, re.MULTILINE)
        if m and m.group(1).strip() != json.dumps(v):
            fails.append((k, json.dumps(v), m.group(1).strip()))
assert not fails, f'M1 mismatches: {fails}'
"
→ "M1 byte-identical check: PASSED for all float fields"
```

All 8 float fields (cagr_pct, max_dd_pct, sharpe_rf3, total_return_pct, buy_pct, cash_pct, sell_pct, ma50_breakdown_sell_share) render byte-identical in audit doc cells vs JSON values. M1 VERIFIED.

### Human Verification Required

None. All acceptance criteria verified programmatically:
- Determinism tests pass (pytest green)
- D-09 parity bands (all 3) verified by explicit numeric check against JSON values
- D-11 (no fail-safe changes) verified by git diff + targeted grep
- M1 (byte-identical) verified externally via Python script
- B2 (strict Label line) verified by regex grep (exactly 1 match, 0 choice-expression leaks)
- Requirements coverage verified by cross-reference against REQUIREMENTS.md

### Gaps Summary

None. Phase 42 goal achieved in full:

1. **BASE-01 forensic audit:** Offending commit `f80394f68b98925c47f0c66b9df1099576878ca0` identified via git bisect, documented in single-file audit `docs/audits/v10_baseline_drift.md` with 8-row bisect log, root-cause narrative, and file-level diff summary.
2. **BASE-02 fix-forward reconciliation:** `v60_strict_mode` preset flag (default False) landed in MDMV2Config with branch-guarded re-flattening of CASH→SELL elif chain in V2PositionManager.process_day(). Reconciled-HEAD satisfies all 3 D-09 parity bands (CAGR 11.47, SELL 124, MaxDD -28.17). Canonical tuple published to `output/v10_reconciled_baseline.json` (schema_version=1, 18 fields, outcome=fixed_by_preset). Audit doc `## Reconciled Baseline` section is byte-identical to JSON (M1 verified).
3. **BASE-03 determinism regression:** `tests/test_baseline_determinism.py` with 3 pytest.mark.regression tests (byte-exact numeric variance across 3 runs, byte-exact signal log across 2 runs, D-14 downstream-JSON guard with co-wave-tolerant skip). All 3 tests pass in 26.89s on reconciled-HEAD. M5 tightening: primary assertions are `len(set(...)) == 1` (stronger than D-17's 0.1pp threshold, which is retained as informative fallback).

The phase is a clean close — no gaps, no regressions, no human verification needed. Downstream Phases 43-47 have the canonical reconciled-baseline tuple to consume per D-14.

---

_Verified: 2026-04-22T14:20:00Z_
_Verifier: Claude (gsd-verifier)_
