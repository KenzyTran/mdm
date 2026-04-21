# v10.0 Baseline Drift Audit — Phase 42

**Status:** In Progress (plan 42-02 seed; bisect pending in 42-03)
**Opened:** 2026-04-21
**Closes:** BASE-01 (forensic audit), BASE-02 (fix-forward), BASE-03 (determinism regression test)

## Executive Summary

Between v6.0 ship (CAGR 11.5%, MaxDD -28.2%, 124 SELL per `output/v6_combined_validation.txt`) and HEAD
(CAGR 10.70%, MaxDD -28.63%, 105 SELL per `output/v9_ab_comparison.txt`), the VN30 2015-2026 backtest drifted.
This audit identifies the offending commit(s) via `git bisect` with CAGR-only gate (CAGR 11.4% per D-03),
applies a fix-forward waterfall (selective revert → v60_strict_mode preset → accept-and-document per D-07),
and publishes the reconciled baseline tuple that downstream Phases 43-47 consume as the HARD gate reference.

## Bisect Endpoints

| Anchor | Commit Hash | Subject | Reference |
|--------|-------------|---------|-----------|
| good (v6.0 ship) | 37cfdc248f8fc1d2aaaf0ec484147b9fa16b4e5a | chore: complete v6.0 milestone — MDM Fail-Safe & Signal Refinement | truth-of-record = `output/v6_combined_validation.txt` |
| bad  (HEAD)      | 3601679cdba9c3ea674904e6f8a9aa24273cb6ad | docs(42): create phase plan — 6 plans across 4 waves for BASE-01/02/03 reconciliation | drift = `output/v9_ab_comparison.txt` |

Bisect surface area: 8 commits between anchors touching `strategies/mdm_hybrid/`, `core/indicators.py`, or `core/data_loader.py`.
Full commit range: 256 commits (checked via `git log --oneline 37cfdc2..HEAD | wc -l`).
Expected bisect iterations: ~log2(N_total) engine runs (per D-01, ~8 for 256 commits).

## Reference Numbers

### v6.0 Truth-of-Record (from `output/v6_combined_validation.txt`, Fail-Safe column)

| Metric | Value |
|--------|-------|
| Total Return | +238.8% |
| CAGR | 11.5% |
| Max Drawdown | -28.2% |
| Transitions | 334 |
| BUY time | 30.4% |
| SELL signal count | 124 |
| MA50-breakdown SELL share | 84% |

### Measured-Today Drift (from `output/v9_ab_comparison.txt`, baseline row)

| Metric | Value | Delta vs v6.0 |
|--------|-------|---------------|
| Total Return | +213.4% | -25.4pp |
| CAGR | 10.70% | -0.80pp |
| Max Drawdown | -28.63% | -0.43pp |
| Sharpe_rf3 | 0.461 | — (not in v6.0 report) |
| Transitions | 296 | -38 |
| BUY% / CASH% / SELL% | 29.8% / 38.8% / 31.4% | — |
| SELL signal count | 105 | -19 |
| MA50-breakdown SELL share | 100.0% | +16pp |

## Bisect Log

`git bisect` was driven by `analysis/bisect_v10_baseline.py` (wrapper copied to `/tmp/bisect_v10_gate.py` with
`analysis.validate_v9.compute_metrics` inlined so the gate works on commits that predate Phase 41) as the
per-commit CAGR gate. Anchors: good = `37cfdc2` (v6.0 ship), bad = `3601679` (phase 42 plan creation).
Bisect converged in 8 iterations; every tested commit is listed below with the gate's recorded metrics tuple.

| commit_hash | date | author | subject | cagr_pct | sell_count | max_dd_pct | verdict |
|-------------|------|--------|---------|----------|------------|------------|---------|
| 427064a | 2026-04-10 | KenzyTran | docs: add backlog item 999.1 — fix MDM SELL reduce slots | 11.47 | 124 | -28.17 | good |
| 5ecdcc8 | 2026-04-15 | KenzyTran | docs(38): capture phase context (ATR Buffer Zone Module) | 11.47 | 124 | -28.17 | good |
| b7c1f63 | 2026-04-15 | KenzyTran | docs(38-01): complete ATR Buffer Zone config and indicator plan | 11.47 | 124 | -28.17 | good |
| a147db7 | 2026-04-15 | KenzyTran | feat(38-01): add atr_buffer_* fields to MDMV2Config and update presets | 11.47 | 124 | -28.17 | good |
| f80394f | 2026-04-15 | KenzyTran | feat(38-02): add atr_buf_below_count to V2Position and wire m-day streak in process_day | 10.70 | 105 | -28.63 | bad |
| d322a17 | 2026-04-15 | KenzyTran | feat(38-02): wire add_violation_threshold_column into HybridEngine indicator pipeline | 10.70 | 105 | -28.63 | bad |
| 66ef4c4 | 2026-04-16 | KenzyTran | docs(39): research phase domain | 10.70 | 105 | -28.63 | bad |
| 9788da9 | 2026-04-16 | KenzyTran | docs(40): capture phase context | 10.70 | 105 | -28.63 | bad |

CAGR trajectory between good anchor and offending commit is monotone; no segment re-runs required per D-05.

**Offending commit identified by bisect:**

`f80394f` — `feat(38-02): add atr_buf_below_count to V2Position and wire m-day streak in process_day`

Full hash: `f80394f68b98925c47f0c66b9df1099576878ca0`
Date: `2026-04-15`
Author: `KenzyTran`

This is the commit where `uv run python analysis/bisect_v10_baseline.py` first returns exit 1 (CAGR < 11.4%).
Its immediate parent (`b7c1f63`) returned exit 0 (CAGR = 11.47% ≥ 11.4%).

CAGR delta at this commit: `11.47 - 10.70 = 0.77pp`
SELL count delta: `124 - 105 = 19`
MaxDD delta: `-28.17 - (-28.63) = 0.46pp`

**Diff summary:** `git show --stat f80394f68b98925c47f0c66b9df1099576878ca0` output:

```
 strategies/mdm_hybrid/position_manager.py | 37 +++++++++++++++++++++++++++----
 1 file changed, 33 insertions(+), 4 deletions(-)
```

Single-file change, entirely within `strategies/mdm_hybrid/position_manager.py`. Adds `atr_buf_below_count`
field to `V2Position`, adds `violation_threshold` kwarg to `process_day()`, and restructures the
CASH→SELL branch into an outer elif gating on `ma50_sell_enabled and ma50 is not None` with a nested
if/else on `atr_buffer_enabled`. Commit message claims the disabled-path branch is "byte-identical to
original v6.0 MA50 breakdown check (ATR-04 protected)" — bisect evidence contradicts this claim.

**If bisect identified multiple non-monotone drift commits (per D-05):** none found. Trajectory was
strictly monotone (all goods chronologically precede all bads across the 8 tested commits); the drift
is attributable to a SINGLE commit, `f80394f`.

## Root-Cause Narrative

**Files changed by offending commit:** `strategies/mdm_hybrid/position_manager.py` (37 lines changed, 33
insertions / 4 deletions). No other files touched. No `core/`, no indicator-pipeline, no fail-safe
(`_check_fail_safe`) code modified. Per D-11, fail-safe logic is explicitly out of scope for
reconciliation — **this finding does NOT touch fail-safe**.

**Semantic change.** The commit refactored the CASH→SELL branch of `V2PositionManager.process_day()`. The
v6.0 pre-refactor structure was a flat elif chain:

```python
if is_ftd: ...                                    # CASH → BUY
elif ma50_sell_enabled and ma50 is not None and close < ma50:
    ...                                           # CASH → SELL via MA50 breakdown
elif days_in_cash >= cash_deterioration_days:
    ...                                           # CASH → SELL via deterioration
```

Post-refactor (feature-gated on `atr_buffer_enabled`):

```python
if is_ftd: ...
elif ma50_sell_enabled and ma50 is not None:     # outer elif — matches on ANY day with ma50
    if atr_buffer_enabled:                        # new ATR buffer branch
        ... m-day streak logic ...
    else:                                         # disabled path — claimed byte-identical
        if close < ma50:                          # nested if (no else!)
            ... MA50 breakdown SELL ...
elif days_in_cash >= cash_deterioration_days:    # UNREACHABLE when ma50 is not None
    ...                                           # the cash-deterioration elif is dead
```

**Why CAGR drifted.** When `close >= ma50` on a CASH day (engine has data for `ma50`), the OLD code fell
through the first elif (its condition `close < ma50` was false) and **could still fire a cash-deterioration
SELL via the next elif**. The NEW code captures the `elif` gate on `ma50_sell_enabled and ma50 is not None`
unconditionally, enters the nested if, finds `close < ma50` is false, does nothing, and **silently skips
the cash_deterioration elif entirely**. The cash_deterioration SELL branch becomes dead code on every day
the engine has a valid MA50 and `close >= ma50` — which is most days across the 2015-2026 run.

Quantitatively: SELL count dropped 124 → 105 (-19 SELLs eliminated). Those 19 missed SELLs were
cash-deterioration triggers that the old elif chain fired on CASH days with `close >= ma50` and
`days_in_cash >= cash_deterioration_days`. Without them, the engine holds CASH longer in deteriorating
conditions, misses stop-loss opportunities that cash-deterioration-SELL would have provided, and
accumulates more drawdown during prolonged sideways/drop regimes — hence CAGR 11.47 → 10.70 (-0.77pp) and
MaxDD -28.17 → -28.63 (-0.46pp).

**Intent assessment.** The commit message asserts parity ("byte-identical to original v6.0 MA50 breakdown
check (ATR-04 protected)") and explicitly intends to preserve disabled-path behavior. The refactor is an
**inadvertent** parity break — a feature-gate refactor with an uncovered side effect. The author's intent
was clearly to preserve v6.0 semantics when `atr_buffer_enabled=False`; the ATR-04 backward-compat
invariant from Phase 38-CONTEXT.md was a load-bearing claim that no regression test validated at the
commit's merge time. This is the class of bug the Phase 42 BASE-03 determinism regression test is
designed to catch going forward (though BASE-03 tests determinism, not parity — a related but distinct
regression-test category belongs in a future phase).

**D-11 applicability.** The change touches `strategies/mdm_hybrid/position_manager.py` but the modified
code is the CASH→SELL MA50-breakdown / cash-deterioration branches, NOT the fail-safe logic
(`_check_fail_safe` or its threshold-setting callers). Therefore D-11's "no changes to fail-safe →
accept-and-document" rule does NOT apply. This finding is eligible for the D-07 selective-revert path
(step 1) in plan 42-04, since the offending commit is self-contained (single file, 33-line diff) and the
ATR buffer feature can be re-implemented as a true byte-identical gate after revert. If selective revert
is chosen, plan 42-04 must also add a regression test that fails before the revert and passes after, so
the parity claim is enforceable going forward.

**Downstream propagation.** Commits `d322a17`, `66ef4c4`, and `9788da9` in the bisect table all inherit
`f80394f`'s CAGR 10.70 (they are chronologically later and do not restore parity). No subsequent commit
in the 37cfdc2..3601679 range independently affects CAGR — the drift is a single-commit event followed
by unchanged baseline through HEAD. This is consistent with the measured-today numbers in
`output/v9_ab_comparison.txt` (CAGR 10.70, MaxDD -28.63, SELL count 105) matching the first bad commit's
metrics tuple exactly.

## Reconciliation Outcome

_To be populated by plan 42-04._

One of: **fixed_by_revert** (selective `git revert` of offending commit), **fixed_by_preset** (added
`v60_strict_mode: bool = False` to MDMV2Config per D-07 step 2), or **accepted_drift** (drift documented as
intentional/unsafe-to-revert per D-07 step 3 — if chosen, this section will start with the exact string
`**Reconciliation Outcome: Accepted drift, not fixed**` so downstream phases grep-detect the exception).

Parity thresholds (D-09): CAGR within ±0.3pp of 11.5% AND SELL count within ±5 of 124 AND MaxDD within ±1.0pp of -28.2%.

## Reconciled Baseline

_To be populated by plan 42-05 (literal numbers, not dynamic references, per D-16)._

Will contain the full 18-field canonical tuple (D-12) as a human-readable markdown table,
numerically identical to `output/v10_reconciled_baseline.json`.

## Invariants

- **D-10:** Data window locked at `2015-01-05` → `2026-03-31` for every run in this audit.
- **D-11:** No fail-safe logic changes allowed. If bisect lands on a fail-safe-touching commit, that finding
  becomes **accept-and-document** — it is NOT a fix candidate.
- **D-14:** Downstream Phases 43-47 read from `output/v10_reconciled_baseline.json`, not from literals in this doc.
- **D-15:** JSON `schema_version: 1` locks the tuple shape.

## References

- `output/v6_combined_validation.txt` — v6.0 truth-of-record
- `output/v9_ab_comparison.txt` — measured-today drift
- `.planning/MILESTONES.md` — v6.0 entry, v9.0 entry
- `.planning/phases/42-baseline-reconciliation/42-CONTEXT.md` — 22 locked decisions (D-01..D-22)
- `analysis/bisect_v10_baseline.py` — bisect runner (plan 42-01)
- `analysis/publish_v10_baseline.py` — reconciled-baseline publisher (plan 42-05)
- `tests/test_baseline_determinism.py` — determinism regression (plan 42-06)
