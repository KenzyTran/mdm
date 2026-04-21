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

_To be populated by plan 42-03._

Table will have columns: `commit_hash | date | author | subject | cagr_pct | sell_count | max_dd_pct | verdict`.
Rows are one per commit tested by `git bisect`, plus a final row with the identified offending commit(s).

## Root-Cause Narrative

_To be populated by plan 42-03._

Will describe: what the offending commit(s) changed, why the change caused CAGR drift, whether the drift is
an intentional improvement, a bug, or an untested side effect.

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
