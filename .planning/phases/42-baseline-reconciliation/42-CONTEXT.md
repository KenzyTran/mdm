# Phase 42: Baseline Reconciliation - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Forensic audit + fix-forward of the engine drift between shipped v6.0 (CAGR 11.5%, Return +238.8%, MaxDD -28.2%, 124 SELL — [output/v6_combined_validation.txt](output/v6_combined_validation.txt)) and currently-measured baseline (CAGR 10.70%, Return +213.4%, MaxDD -28.63%, 105 SELL — [output/v9_ab_comparison.txt](output/v9_ab_comparison.txt)), plus a committed determinism regression test, so that v10.0 macro work (Phases 43-47) tunes against a clean, reproducible reference.

Deliverables:

1. `docs/audits/v10_baseline_drift.md` — bisect log + offending commit(s) + diffs + root-cause narrative (BASE-01)
2. `HybridEngine + fail-safe` on VN30 2015-2026 reproduces v6.0 CAGR within ±0.3pp via fix-forward (selective revert → v6.0-strict preset fallback → accept-and-document) (BASE-02)
3. `tests/test_baseline_determinism.py` — 3-run numeric variance + byte-exact signal log equality (BASE-03)
4. `output/v10_reconciled_baseline.json` + the same tuple quoted in audit doc — single source of truth consumed by Phases 43-47 HARD gate checks

**Explicitly out of scope:**
- Macro filter implementation (Phase 44)
- Liquidity proxy / SBV data regeneration (Phase 43)
- Walk-forward grid search (Phase 45)
- A/B + OOS validation (Phase 46)
- Rule-doc / dashboard updates (Phase 47)
- Any change to `strategies/canslim/`, `strategies/portfolio/`, `vn30_vsa/` — v10.0 out-of-scope per REQUIREMENTS.md
- Any change to fail-safe logic — v6.0 parity must hold

</domain>

<decisions>
## Implementation Decisions

### Audit methodology (BASE-01)

- **D-01:** Use `git bisect` (automated) between the v6.0 ship commit (Phase 27 ship, commit before v7.0 work began — resolve exact hash during planning) and `HEAD`. Bisect script runs `HybridEngine + fail-safe` on VN30 2015-2026 with `atr_buffer_enabled=False, refined_dd_enabled=False`, prints CAGR to stdout, exits 0 if CAGR ≥ 11.4% else exits 1. ~253 commits → ~8 engine runs. Reason: milestone-boundary checkpoints only narrow to a window and then still need bisect inside; file-level archaeology risks missing data/preset drift. Bisect is deterministic and fastest.
- **D-02:** The "good" reference is the numbers in `output/v6_combined_validation.txt` as committed: **Return +238.8%, CAGR 11.5%, MaxDD -28.2%** (Fail-Safe row). This is the shipped artifact and is already the truth-of-record for the project. Do NOT re-run the v6.0 ship commit to regenerate a fresh baseline — if a re-run diverges from the .txt, that divergence would itself be ambiguity ("which is truth?") and adds cost.
- **D-03:** Bisect gate = **CAGR only (≥ 11.4%)**. Spec requires fix to within ±0.3pp of 11.5% → threshold 11.2% (strict) or 11.4% (tight). Use 11.4% so a commit that drifts CAGR by just 0.1pp still flags as "bad" and the bisect converges on the EARLIEST drift. SELL count and MaxDD are captured as bisect-evidence columns but are not the gate — they often co-move with CAGR and including them can split a single drift across two commits.
- **D-04:** Bisect "test" script lives at `analysis/bisect_v10_baseline.py`. It loads VN30 via `DataLoader('vn30').load('2015-01-05', '2026-03-31')`, precomputes indicators, instantiates `HybridEngine(HybridConfig(v2_config=VN30_PRESET_v60, two_phase_enabled=True, filter_enabled=False))` with macro and v9 feature flags forced OFF, runs, computes CAGR via [analysis/validate_v9.py::compute_metrics()](analysis/validate_v9.py#L125). Handles import-path breakage across history (if `strategies/mdm_hybrid/` didn't exist at an older commit, script falls back to old `models/` path or exits 125 = skip). **Must tolerate refactors** — Phase 02 migrated `models/` → `strategies/mdm_classic/` and Phase 11 introduced `strategies/mdm_hybrid/`.
- **D-05:** Bisect log (each tested commit: hash, date, author, subject, CAGR, SELL count, MaxDD, verdict) saved to `docs/audits/v10_baseline_drift.md` as a markdown table. If bisect identifies multiple drifting commits (e.g., non-monotone drift), each is listed with per-commit impact measured by re-running bisect segments.
- **D-06:** Audit doc target path: **single file `docs/audits/v10_baseline_drift.md`** (not a folder like `docs/audits/phase42/`). One-file pattern matches Phase 28-31 audit precedent for narrative-heavy audits; folder pattern is reserved for multi-artifact audits (Phase 32, 37). Future reviewers open one file.

### Reconciliation strategy (BASE-02)

- **D-07:** Fix-forward path is a **three-step fallback waterfall**, attempted in order; stop at first step that restores parity:
  1. **Selective revert** — if offending commit is self-contained and unrelated to v7+ work, `git revert` it directly. Verify CAGR within ±0.3pp, keep move on.
  2. **v6.0-strict preset flag** — if revert would break v7/v8 (e.g., the drifting commit is wired into CANSLIM pipeline or portfolio engine), add a `v60_strict_mode: bool = False` field to `MDMV2Config` (or equivalent, decided at plan time) that, when True, restores v6.0 semantics via targeted branch-guards in the offending code paths. Default False keeps current behavior for v7/v8 consumers; v10.0 macro work sets True for its baseline runs.
  3. **Accept-and-document** — if both above fail or are unsafe, document explicit justification in audit doc: what changed, why reverting/preset is infeasible, what metric gap remains, and why the drifted baseline is the correct reference going forward. This path downgrades v10.0's HARD gate from "CAGR ≥ 11.5%" to "CAGR ≥ reconciled-measured baseline" — which the spec already anticipates.
- **D-08:** Selective revert is PREFERRED; preset-flag is acceptable; accept-and-document triggers an explicit alert in the audit doc (flagged section: "**Reconciliation Outcome: Accepted drift, not fixed**"). Downstream phases must read this section.
- **D-09:** If fix-forward succeeds (step 1 or 2), the reconciled CAGR must be within **±0.3pp of 11.5%** AND SELL count within **±5 of 124** AND MaxDD within **±1.0pp of -28.2%**. If numeric CAGR matches but SELL count is off by >5, that is a "parity-suspect" outcome: treat as accept-and-document unless root cause is understood (e.g., a single filter threshold commit).
- **D-10:** Parity-verification run reproduces the exact VN30 2015-2026 window used by v6.0 shipped (`2015-01-05` → `2026-03-31` per `output/v9_ab_comparison.txt` line 8). Do NOT expand the window — data growth after ship is its own drift dimension and out of scope for BASE-02.
- **D-11:** No changes to fail-safe logic are allowed during reconciliation (REQUIREMENTS.md Out of Scope). If bisect identifies a fail-safe drift, that is an accept-and-document finding, not a fix candidate.

### Reconciled baseline — scope & publication

- **D-12:** Canonical tuple **expands beyond the ROADMAP.md spec** (CAGR, MaxDD, Sharpe_rf3, SELL count). Full fields:
  ```
  cagr_pct, max_dd_pct, sharpe_rf3, sell_count,
  total_return_pct, transitions, buy_pct, cash_pct, sell_pct,
  ma50_breakdown_sell_share, buy_count,
  run_start, run_end,
  engine_git_hash, python_version, pandas_version, numpy_version,
  reconciliation_outcome  # "fixed_by_revert" | "fixed_by_preset" | "accepted_drift"
  ```
  Reason: downstream Phases 43-47 will gate on more than CAGR (Phase 46 HARD gate includes MaxDD < -20%, time-in-state, MA50 share). If the canonical tuple omits those, each downstream phase re-measures and risks diverging. Env version fields guard against silent pandas/numpy drift.
- **D-13:** Publication: **both** `docs/audits/v10_baseline_drift.md` (human-readable table in "Reconciled Baseline" section) AND `output/v10_reconciled_baseline.json` (machine-readable). Audit doc wraps the tuple in narrative; JSON is the programmatic single source.
- **D-14:** Downstream phases (43-47) **MUST read from `output/v10_reconciled_baseline.json`** and NOT hardcode the baseline numbers in their plan/code. Hardcoding invites silent divergence if Phase 42's reconciled values shift during Phase 42 itself (e.g., preset-flag tuning). Spec-call: Phase 46 VAL-02 gate code loads the JSON at run time.
- **D-15:** JSON schema locked at v1 with `schema_version: 1` key. Any future rework of the tuple shape (e.g., Phase 46 adds a metric) must bump schema_version and migrate consumers. This is a forward-compat hedge, not overengineering — Phases 43-47 will touch this file semantically and a schema key prevents silent breakage.
- **D-16:** The audit doc's "Reconciled Baseline" table is the **human quote source** for Phase 47 DOC-01/DOC-03 and `.planning/MILESTONES.md` v10.0 entry. Planner for Phase 42 writes it with literal numbers so grep/reading works without running any script.

### Determinism regression test (BASE-03)

- **D-17:** Test file: `tests/test_baseline_determinism.py`. Two test functions in a single pytest class:
  1. **`test_numeric_variance_across_3_runs`** — instantiates 3 fresh `HybridEngine` objects, runs each on VN30 2015-2026, computes metrics tuple, asserts:
     - `max(CAGRs) - min(CAGRs) ≤ 0.1` (pp)
     - `max(MaxDDs) - min(MaxDDs) ≤ 0.1` (pp)
     - `max(Sharpes) - min(Sharpes) ≤ 0.005`
     - `len(set(SELL_counts)) == 1` (integer count must be exact)
     - `len(set(transitions)) == 1`
  2. **`test_signal_log_byte_exact`** — instantiates 2 fresh engines, extracts `signal_log` DataFrame from each, asserts `df1.equals(df2)` (pandas byte-exact equality on index, columns, dtypes, values). Strongest determinism guarantee — catches even floating-point column reordering.
- **D-18:** Data slice: **full 2015-2026 VN30** (real data via `DataLoader('vn30').load('2015-01-05', '2026-03-31')`). Rationale: shorter synthetic fixtures can mask warmup-dependent non-determinism (e.g., MA200 initialization). Full-period run is ~3s per engine × 5 runs total = ~15s — acceptable for a pytest `@pytest.mark.regression` test. If runtime exceeds 30s on the dev machine, planner may switch to a cached input DataFrame (precomputed indicators) to skip the indicator pipeline on each test run.
- **D-19:** Test marker: `@pytest.mark.regression` (matches `test_mdm_regression.py` and `test_vsa_regression.py` precedent). Run via `pytest -m regression tests/test_baseline_determinism.py`.
- **D-20:** No CI exists in the repo (verified: no `.github/workflows/`, no `.gitlab-ci.yml`). Bar for BASE-03 is: **"pytest passes locally on the reconciled-HEAD commit"**. Test docstring records this explicitly so future reviewers understand the bar wasn't "green-CI" but "green-on-HEAD when committed".
- **D-21:** If either test fails on the reconciled-HEAD commit, Phase 42 is incomplete — Planner must not close the phase. Non-determinism in the engine is a bug, not a feature, and blocks v10.0 gate integrity.
- **D-22:** Test uses VN30_PRESET (the v6.0-default preset — or v6.0-strict preset if D-07 step 2 path taken). Determinism must hold for whichever preset is declared canonical by the reconciliation outcome.

### Claude's Discretion

- Exact commit identification pattern for v6.0 ship (e.g., `git log --grep="v6.0"` vs STATE.md vs manual) — resolved during planning via `.planning/MILESTONES.md` v6.0 entry
- Bisect script output verbosity and TTY pretty-printing (follow Phase 40 fail-loud conventions)
- Audit doc section headers / narrative tone (follow `docs/audits/phase28-*.md` precedent)
- Exact column order and width in the markdown bisect-log table
- Test-file imports and helper functions (follow existing pytest `tests/` conventions)
- Whether to save per-bisect-step intermediate signal logs for forensics (nice-to-have)
- JSON field ordering (alphabetical vs semantic grouping)

### Folded Todos

None — `gsd-tools todo match-phase 42` reports `todo_count: 0`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- [.planning/ROADMAP.md §Phase 42](.planning/ROADMAP.md) (lines 805-815) — Goal, 4 success criteria (BASE-01/02/03 mapped), reconciled-baseline tuple spec
- [.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md) §Baseline Reconciliation (BASE-01..03) — forensic audit, fix-forward, determinism test requirements
- [.planning/PROJECT.md](.planning/PROJECT.md) Key Decisions table — v6.0 production retention rationale, v9.0 rejection evidence, v10.0 HARD gate policy

### Shipped v6.0 artifact (the "good" reference)
- [output/v6_combined_validation.txt](output/v6_combined_validation.txt) — Fail-Safe row: Return +238.8%, CAGR 11.5%, MaxDD -28.2%, 313→334 transitions. **Truth-of-record for bisect.**
- [.planning/MILESTONES.md](.planning/MILESTONES.md) v6.0 entry — shipped metrics memory

### Measured-today drift evidence (the "bad" current state)
- [output/v9_ab_comparison.txt](output/v9_ab_comparison.txt) (lines 22-26) — baseline row: Return +213.4%, CAGR 10.70%, MaxDD -28.63%, 296 transitions, 105 SELL
- [output/v9_ab_scenarios.csv](output/v9_ab_scenarios.csv) — machine-readable baseline metrics

### Engine under audit (read-only investigation; changes only if reconciliation requires)
- [strategies/mdm_hybrid/mdm_hybrid_engine.py](strategies/mdm_hybrid/mdm_hybrid_engine.py) — HybridEngine class, state pipeline
- [strategies/mdm_hybrid/config.py](strategies/mdm_hybrid/config.py) — VN30_PRESET (line 129), MDMV2Config dataclass
- [strategies/mdm_hybrid/indicator_filter.py](strategies/mdm_hybrid/indicator_filter.py) — IndicatorFilter logic
- [strategies/mdm_hybrid/position_manager.py](strategies/mdm_hybrid/position_manager.py) — Position state, fail-safe trigger
- [core/indicators.py](core/indicators.py) — `build_indicator_dataframe()`; Phase 38-01 added `add_violation_threshold_column`, Phase 39-01 added vol MA/percentile columns (both are feature-gated but precompute-path changes are suspects)
- [core/data_loader.py](core/data_loader.py) — `DataLoader('vn30').load()` entry point

### Metrics schema precedent (reuse, don't reinvent)
- [analysis/validate_v9.py::compute_metrics()](analysis/validate_v9.py) (lines 125-193) — `sharpe_rf3`, `cagr_pct`, `max_dd_pct`, `total_return_pct`, `transitions`, `sell_count`, `ma50_breakdown_sell_share`, `buy_pct/cash_pct/sell_pct`
- [analysis/validate_combined_v6.py](analysis/validate_combined_v6.py) — Phase 27 precedent: report structure (header → sections → save), log-to-list pattern

### Test precedent (pytest regression pattern)
- [tests/test_mdm_regression.py](tests/test_mdm_regression.py) — `@pytest.mark.regression` pattern, fixtures, engine-run-via-fixture
- [tests/test_hybrid_engine.py](tests/test_hybrid_engine.py), [tests/test_fail_safe.py](tests/test_fail_safe.py), [tests/test_phase38_backward_compat.py](tests/test_phase38_backward_compat.py), [tests/test_phase39_backward_compat.py](tests/test_phase39_backward_compat.py) — existing hybrid-engine tests to model imports/setup after

### Audit doc precedent
- [docs/audits/phase28-data-audit.md](docs/audits/phase28-data-audit.md), [docs/audits/phase29-canslim-validation.md](docs/audits/phase29-canslim-validation.md) — narrative-heavy single-file audit pattern Phase 42 follows
- [docs/audits/phase32/](docs/audits/phase32/), [docs/audits/phase34/](docs/audits/phase34/) — multi-file audit folder pattern (NOT chosen for Phase 42)

### Prior phase contexts (upstream decisions to respect)
- [.planning/phases/23-fail-safe-mechanism/](.planning/phases/23-fail-safe-mechanism/) — fail-safe canonical semantics
- [.planning/phases/27-combined-v6-validation/](.planning/phases/27-combined-v6-validation/) — v6.0 validation precedent that produced the reference numbers
- [.planning/phases/38-atr-buffer-zone-module/38-CONTEXT.md](.planning/phases/38-atr-buffer-zone-module/38-CONTEXT.md) — ATR-04 backward-compat invariant (feature-gate parity claim under audit)
- [.planning/phases/39-refined-distribution-day-module/39-CONTEXT.md](.planning/phases/39-refined-distribution-day-module/39-CONTEXT.md) — DD-04 backward-compat invariant (feature-gate parity claim under audit)
- [.planning/phases/41-ab-walk-forward-validation/41-CONTEXT.md](.planning/phases/41-ab-walk-forward-validation/41-CONTEXT.md) — measured-today baseline numbers + metrics schema conventions

### Memory anchors
- v6.0 baseline VN30 2015-2026: Return +238.8%, CAGR 11.5%, MaxDD -28.2%, 124 SELL (84% MA50-breakdown) — memory: `project_best_model.md`
- Equity formula `state[i-1]` discipline — memory: `feedback_equity_formula.md` (regression test must uphold this)
- v10.0 HARD gate: MaxDD < -20% AND CAGR ≥ reconciled baseline — memory: `project_v9_whipsaw.md`
- Best-model doc discipline — memory: `feedback_best_model_docs.md` (audit doc must state the final reconciled baseline clearly)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- [analysis/validate_v9.py::compute_metrics()](analysis/validate_v9.py#L125-L193) — canonical metrics function; Phase 42 bisect script and reconciled-baseline writer both reuse this. Do NOT reimplement.
- [analysis/validate_combined_v6.py](analysis/validate_combined_v6.py) — report layout pattern (log-to-list, `print()` + `lines.append()`, save-to-file) for the human-readable audit doc
- `dataclasses.replace(VN30_PRESET, **overrides)` — Phase 40 D-04 preset-mutation pattern, reused for the v6.0-strict preset if D-07 step 2 path taken
- `HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False))` — engine construction pattern from v6/Phase 40/41
- [tests/test_mdm_regression.py](tests/test_mdm_regression.py) class-scoped `@pytest.fixture` for engine-run — BASE-03 test file models its fixtures after this

### Established Patterns
- **Single-file validation/analysis script per phase** — Phase 27, 40, 41 precedent. Phase 42 emits `analysis/bisect_v10_baseline.py` (bisect runner) + `analysis/publish_v10_baseline.py` (writes JSON + audit-doc reconciled-baseline section) — split because bisect runs across history while publish runs once at HEAD.
- **Output to `output/`** — reconciled-baseline JSON lives at `output/v10_reconciled_baseline.json` alongside `v9_ab_comparison.txt`, `v6_combined_validation.txt`.
- **Audit doc to `docs/audits/`** — matches Phase 28-34 convention. Markdown narrative + tables.
- **Fail-loud on broken runs** — Phase 40 D-10 traceback-to-report. Bisect script: exit 125 (git bisect's "untestable, skip") if import or data-load raises; exit 1 if CAGR < 11.4%; exit 0 if CAGR ≥ 11.4%.
- **Sharpe_rf3 formula**: `(ann_return − 0.03) / (daily_returns.std() × √252)` — Phase 40 D-19, Phase 41 D-11. Reconciled-baseline tuple inherits this convention.
- **Pytest `@pytest.mark.regression`** marker — gates deterministic/expensive tests. BASE-03 test inherits.

### Integration Points
- **Inputs:**
  - VN30 OHLCV via `DataLoader('vn30').load('2015-01-05', '2026-03-31')` — data window MUST match v6.0-shipped window
  - `VN30_PRESET` from [strategies/mdm_hybrid/config.py:129](strategies/mdm_hybrid/config.py#L129) — base for reconciliation
  - v6.0 reference numbers from [output/v6_combined_validation.txt](output/v6_combined_validation.txt) — truth-of-record
  - Git history (253 commits since v6.0 ship) — bisect surface
- **Outputs Phase 42 creates:**
  - `docs/audits/v10_baseline_drift.md` — audit narrative + bisect log + reconciled baseline table (BASE-01, BASE-02)
  - `output/v10_reconciled_baseline.json` — machine-readable canonical tuple with schema_version=1 (BASE-02)
  - `tests/test_baseline_determinism.py` — pytest regression test (BASE-03)
  - `analysis/bisect_v10_baseline.py` — bisect runner script (BASE-01 evidence producer)
  - `analysis/publish_v10_baseline.py` — writes the JSON + audit-doc reconciled-baseline section after fix-forward (BASE-02 closer)
  - Possibly: revert commit(s) and/or `v60_strict_mode` flag addition to `MDMV2Config` (fix-forward artifacts)
- **Downstream consumers (Phases 43-47):**
  - Phase 43 LIQ pipeline — no dependency on reconciled baseline (data work)
  - Phase 44 MACRO-04 v6.0 parity regression — compares new `macro_filter_enabled=False` signal log to reconciled-HEAD signal log (NOT v6.0 shipped signal log — parity target is the reconciled-HEAD state)
  - Phase 45 WF grid search — reconciled baseline is `train_cagr` reference; walk-forward degradation computed against it
  - Phase 46 VAL-02 HARD gate — reads `output/v10_reconciled_baseline.json` and asserts OOS CAGR ≥ reconciled_baseline.cagr_pct AND MaxDD < -20%
  - Phase 46 VAL-04 regression test — byte-exact signal log match against reconciled-HEAD (same target as Phase 44 MACRO-04)
  - Phase 47 DOC-03 milestone audit — quotes reconciled-baseline tuple directly from audit doc

</code_context>

<specifics>
## Specific Ideas

- **"Fix-forward preferred, selective revert first"** — user explicit earlier, reiterated in spec. Preset-flag is the second chair; accept-and-document is flagged as the last-resort exit with alert banner.
- **"Trust the shipped .txt as v6.0 reference"** — do not re-run the ship commit to regenerate fresh numbers. The `output/v6_combined_validation.txt` committed numbers are the truth-of-record; re-running risks creating a new source of truth that diverges from what the project already published.
- **"CAGR is the single bisect gate"** — multi-metric gates (CAGR + SELL + MaxDD) can split a single drift across commits. Simpler is correct here.
- **"Machine + human publication"** — every downstream phase reads the JSON; no phase hardcodes. Audit doc carries the human narrative + redundant human-readable tuple for non-programmatic review.
- **"Full 2015-2026 in the determinism test, no fixtures"** — shorter slices mask warmup non-determinism. 15s total pytest runtime is acceptable.
- **"Byte-exact signal log equality"** — strongest determinism proof. If the engine can't produce two byte-identical signal logs on identical inputs, that's a bug that blocks v10.0 gate integrity.
- **"No changes to fail-safe"** — explicit REQUIREMENTS.md Out of Scope. If bisect lands on a fail-safe-touching commit, that is an accept-and-document finding, not a fix target.

</specifics>

<deferred>
## Deferred Ideas

- **v7.0 CANSLIM baseline reconciliation** — CANSLIM pipeline may also have drifted. v10.0 scope is MDM engine only; CANSLIM audit is a candidate for v11+ if portfolio work resumes.
- **Environment-drift forensics** — if bisect identifies that pandas/numpy version bump is the cause (not a repo commit), document but don't pin. Pinning dependencies is a repo-wide hygiene task, not a v10.0 scope.
- **Multi-file audit folder structure** (`docs/audits/phase42/`) — rejected for Phase 42 in favor of single-file; revisit if bisect finds >3 distinct drifting commits and the single-file grows unwieldy.
- **CI integration for determinism test** — no CI exists; standing up one is out of scope. BASE-03 bar is local-pytest-passes-on-HEAD.
- **Fresh re-run of v6.0 ship commit for cross-check** — explicitly rejected in D-02. If a future milestone needs environment-drift evidence, this belongs there.
- **v60_strict_mode preset applied retroactively to Phase 23-27 tests** — if preset-flag path is taken, those older tests continue running on current preset (they already pass there). No backport.
- **Expanding the reconciliation window** — beyond 2015-01-05 → 2026-03-31 would pull in data that post-dates v6.0 ship and confound drift analysis. Data-growth audit is separate.

### Reviewed Todos (not folded)
None — `gsd-tools todo match-phase 42` reports `matches: []`.

</deferred>

---

*Phase: 42-baseline-reconciliation*
*Context gathered: 2026-04-21*
