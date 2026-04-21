# Phase 42: Baseline Reconciliation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in [42-CONTEXT.md](42-CONTEXT.md) — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 42-baseline-reconciliation
**Areas discussed:** Audit methodology, Reconciliation strategy, Reconciled baseline scope & publication, Determinism test scope

---

## Audit Methodology

### Search strategy

| Option | Description | Selected |
|--------|-------------|----------|
| git bisect (automated) | Scripted CAGR-check bisect over 253 commits (~8 engine runs) | ✓ |
| Milestone-boundary checkpoints | Manual checkout at Phase 27/34/37/41 heads, run backtest, drill | |
| File-level targeted archaeology | git log likely-suspect files, hand-inspect touching commits | |

**User's choice:** git bisect (automated)
**Notes:** Fastest convergence, deterministic, tolerates the 253-commit haystack. Script must tolerate refactors (Phase 02 `models/` → `strategies/mdm_classic/`; Phase 11 introduced `strategies/mdm_hybrid/`).

### "Good" v6.0 reference source

| Option | Description | Selected |
|--------|-------------|----------|
| output/v6_combined_validation.txt numbers | Trust the shipped artifact (Return +238.8%, CAGR 11.5%, MaxDD -28.2%) | ✓ |
| Re-run v6.0 ship commit + capture fresh | Checkout Phase 27 ship, re-run validate_combined_v6.py today | |
| Both — cross-check | Re-run and compare to .txt; divergence itself is a finding | |

**User's choice:** output/v6_combined_validation.txt numbers
**Notes:** The shipped artifact is truth-of-record. Re-running introduces a second source and ambiguity. Cross-check path deferred as out-of-scope.

### Bisect threshold

| Option | Description | Selected |
|--------|-------------|----------|
| CAGR only (≥ 11.4%) | Single-metric gate, fast convergence, evidence columns for others | ✓ |
| CAGR + SELL count tuple | Both CAGR ≥ 11.4% AND SELL ≥ 120; more rigorous but can split drift | |
| Byte-exact signal log match | Strictest; likely overkill for bisect (reserve for BASE-03 regression) | |

**User's choice:** CAGR only (≥ 11.4%)
**Notes:** Multi-metric gates can split a single drift across commits. SELL count and MaxDD captured as evidence, not gate.

### Audit report location & shape

| Option | Description | Selected |
|--------|-------------|----------|
| docs/audits/v10_baseline_drift.md — per-commit table | Single markdown file, narrative + bisect log + decision | ✓ |
| Structured folder docs/audits/phase42/ | Multi-file: bisect log, per-commit, decision, publish — precedent exists | |
| Audit doc + machine-readable JSON | .md narrative + sidecar JSON for programmatic diff | |

**User's choice:** Single file docs/audits/v10_baseline_drift.md
**Notes:** One-file audit precedent matches Phase 28-31 pattern. Folder pattern reserved for multi-artifact audits (deferred unless bisect finds >3 distinct drifting commits).

---

## Reconciliation Strategy (BASE-02)

**Mode:** User requested Claude to decide remaining areas ("Bạn quyết đinh hết luôn nhé"). Decisions below were picked by Claude with rationale.

### Fix-forward path

| Option | Description | Selected |
|--------|-------------|----------|
| Selective revert | `git revert` offending commit if self-contained | ✓ (step 1 of waterfall) |
| v6.0-strict preset flag | Add `v60_strict_mode` field to MDMV2Config for reversible v6.0 semantics | ✓ (step 2 fallback) |
| Accept-and-document | Document explicit justification if revert/preset infeasible | ✓ (step 3 last resort) |

**Decision:** Three-step fallback waterfall, stop at first step that restores parity.
**Rationale:** Fix-forward is spec-preferred. Selective revert is simplest if safe; preset flag preserves v7/v8 compatibility; accept-and-document triggers a flagged section in the audit doc ("Reconciliation Outcome: Accepted drift, not fixed"). Downstream phases must read the outcome field.

### Parity thresholds (extended beyond spec's CAGR-only)

- CAGR within ±0.3pp of 11.5% (spec)
- SELL count within ±5 of 124 (added)
- MaxDD within ±1.0pp of -28.2% (added)
- Parity-suspect outcome (CAGR matches, SELL diverges >5) treated as accept-and-document unless root cause understood

**Rationale:** If CAGR lands but SELL is off, engine behavior differs materially even if aggregate return coincides. A multi-metric parity check catches compensating drifts (e.g., a rule retuning that preserves CAGR by chance).

### Reconciliation window

- Fixed at v6.0 shipped window: 2015-01-05 → 2026-03-31
- Data growth post-ship is its own dimension — out of scope

### Fail-safe logic

- Explicitly out-of-scope (REQUIREMENTS.md). Any fail-safe-touching drift → accept-and-document.

---

## Reconciled Baseline — Scope & Publication

### Canonical tuple

**Decision:** Expand beyond spec's (CAGR, MaxDD, Sharpe_rf3, SELL count). Full schema:

```
cagr_pct, max_dd_pct, sharpe_rf3, sell_count,
total_return_pct, transitions, buy_pct, cash_pct, sell_pct,
ma50_breakdown_sell_share, buy_count,
run_start, run_end,
engine_git_hash, python_version, pandas_version, numpy_version,
reconciliation_outcome  # "fixed_by_revert" | "fixed_by_preset" | "accepted_drift"
schema_version: 1
```

**Rationale:**
- Phase 46 HARD gate needs MaxDD AND CAGR — tuple must carry both to avoid re-measurement divergence
- Time-in-state + MA50 share are cited by downstream phases (Phase 44 MACRO-04 parity, Phase 46 VAL-04)
- Environment version fields guard against silent pandas/numpy drift in later phases
- `reconciliation_outcome` makes the fix-forward path visible to every consumer
- `schema_version` is forward-compat hedge — not overengineering, as Phases 43-47 will touch this file

### Publication

**Decision:** Both `docs/audits/v10_baseline_drift.md` (human-readable "Reconciled Baseline" section with table) AND `output/v10_reconciled_baseline.json` (machine-readable).

**Rationale:**
- Audit doc wraps the tuple in narrative for human readers (Phase 47 DOC-03, MILESTONES.md)
- JSON is the programmatic source; Phase 46 VAL-02 gate code loads it at run time
- Hardcoded constants in downstream phases rejected — invites silent divergence

### Consumption rule

**Decision:** Downstream Phases 43-47 MUST read `output/v10_reconciled_baseline.json`. No hardcoding of baseline numbers in plan text or code.

---

## Determinism Test Scope (BASE-03)

### Test structure

**Decision:** Two test functions in `tests/test_baseline_determinism.py`:

1. **`test_numeric_variance_across_3_runs`** — 3 fresh `HybridEngine` runs, asserts:
   - `max(CAGRs) - min(CAGRs) ≤ 0.1` pp
   - `max(MaxDDs) - min(MaxDDs) ≤ 0.1` pp
   - `max(Sharpes) - min(Sharpes) ≤ 0.005`
   - `len(set(SELL_counts)) == 1` (exact)
   - `len(set(transitions)) == 1` (exact)

2. **`test_signal_log_byte_exact`** — 2 fresh engines, asserts `df1.equals(df2)` on signal_log DataFrames (pandas byte-exact: index, columns, dtypes, values).

**Rationale:** Numeric variance covers "did the math stay close"; byte-exact covers "did anything reorder or perturb silently". Both together = strongest determinism proof for v10.0 gate integrity.

### Data slice

**Decision:** Full VN30 2015-01-05 → 2026-03-31 real data, loaded via `DataLoader('vn30').load(...)`.

**Rationale:** Shorter fixtures mask warmup-dependent non-determinism (MA200, etc.). ~15s total pytest runtime acceptable. Planner may switch to a pre-indicator-computed fixture if runtime blows past 30s.

### Test marker & bar

- `@pytest.mark.regression` marker (matches [tests/test_mdm_regression.py](tests/test_mdm_regression.py), [tests/test_vsa_regression.py](tests/test_vsa_regression.py) precedent)
- No CI exists (no `.github/workflows/`) — bar is **"pytest passes locally on the reconciled-HEAD commit"**
- Test docstring records the bar explicitly
- Preset: VN30_PRESET (v6.0 default) OR v60_strict_mode preset if D-07 step 2 path taken — determinism must hold for whichever preset is canonical

---

## Claude's Discretion

- Exact v6.0 ship commit hash resolution (from `.planning/MILESTONES.md` v6.0 entry or git log)
- Bisect script output verbosity, TTY formatting
- Audit doc narrative tone (follow Phase 28 precedent)
- Markdown table column widths
- Test file import patterns (match existing hybrid-engine pytest conventions)
- Per-bisect-step intermediate signal-log archival (nice-to-have)
- JSON field ordering (alphabetical vs semantic)

---

## Deferred Ideas

- v7.0 CANSLIM baseline reconciliation — v11+ scope
- Environment-drift forensics (pandas/numpy version pinning) — repo-wide hygiene, not v10.0
- Multi-file audit folder `docs/audits/phase42/` — revisit if >3 distinct drifting commits
- CI integration for determinism test — no CI infrastructure exists
- Fresh re-run of v6.0 ship commit for cross-check — explicitly rejected in D-02
- Backport of v60_strict_mode to Phase 23-27 tests — not needed
- Expanding reconciliation window past 2026-03-31 — confounds drift analysis

## Workflow Note

**Init tool bug encountered:** `node gsd-tools.cjs init phase-op 42` returned `phase_found: false` despite Phase 42 being present in ROADMAP.md (lines 805-815). Root cause: `extractCurrentMilestone()` in `.claude/get-shit-done/bin/lib/core.cjs` uses `^#{1,${headingLevel}}\s+(?:.*v\d+\.\d+|✅|📋|🚧)` as its "next milestone" regex, and this matches `### Phase 27: Combined v6.0 Validation & Dashboard` because the title contains "v6.0". Result: v10.0 milestone scope is truncated at Phase 27. Worked around by reading ROADMAP.md directly. Flag for maintenance.

---
*Discussion log recorded: 2026-04-21*
