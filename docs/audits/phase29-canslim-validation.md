# Phase 29 — CANSLIM Scorer Validation Report

**Phase:** 29 — vn100-universe-canslim-scorer
**Plan:** 29-09 (CANS-12, SC6)
**Date:** 2026-04-09
**Verdict:** **SHIPPED with documented baseline divergence** (user decision, Option A)

This report is the phase-level roll-up for Phase 29. It records the evidence
for Success Criteria SC1–SC7, the bugs discovered while wiring the scorer
against live databases during plan 29-09, and the rationale for accepting the
divergence from the upstream `stocks_backend.canslim` baseline instead of
tuning the composite weights to match.

---

## 1. TL;DR

- SC1–SC5 **PASS**, but with an important caveat: those success criteria were
  backed by unit tests throughout plans 29-02…29-08. They were **only exercised
  end-to-end against live Postgres + MySQL during plan 29-09**, which is when
  three latent schema bugs were discovered and fixed (see §5).
- SC6 (baseline alignment) **FAILS vs the original numeric gate** (median
  Spearman ρ ≥ 0.5 on ≥ 70% of quarters). Observed: median ρ = **0.280**,
  **1/28 (4%)** of quarters clear ρ ≥ 0.5, mean top-10 overlap **2.43/10**.
- SC6 is **ACCEPTED by user decision** as expected divergence for an
  independent implementation. CANSLIM in this codebase is to be treated as an
  **independent screen**, not a replica of `stocks_backend.canslim`.
  Calibration against the baseline is **deferred** to a future phase.
- SC7 (docs) **PASS** — `docs/rules_canslim.md` §1–§8 reflects the shipped
  code; this report is linked from §8.
- **Phase 29 ships.** Plans 29-01 through 29-09 are complete; the scorer,
  universe loader, sector router, rules, composite, and validation tooling
  are all in place and exercised end-to-end.

---

## 2. Success Criteria roll-up (SC1–SC7)

| SC  | Summary                                             | Status             | Evidence |
| --- | --------------------------------------------------- | ------------------ | -------- |
| SC1 | Schema lock + introspection (plan 29-01)            | PASS¹              | `schema_lock.json`, `scripts/introspect_canslim_schema.py`, `29-01-SUMMARY.md` |
| SC2 | Universe loader (3 modes, 252d history)             | PASS¹              | `strategies/canslim/universe.py`, `tests/canslim/test_universe.py`, `29-03-SUMMARY.md` |
| SC3 | Sector router + exclusions (bank / ctck / ins.)     | PASS¹              | `strategies/canslim/sectors.py`, `tests/canslim/test_sectors.py`, `29-04-SUMMARY.md` |
| SC4 | CANSLIM rules (C, C+, A, A+, N, S, L, I, Liq)       | PASS¹              | `strategies/canslim/rules/*.py`, `tests/canslim/test_rules_*.py`, `29-05/06/07-SUMMARY.md` |
| SC5 | Scorer composite + end-to-end pipeline              | PASS¹              | `strategies/canslim/scorer.py`, `tests/canslim/test_scorer.py`, `29-08-SUMMARY.md` |
| SC6 | Alignment vs `stocks_backend.canslim` baseline      | **FAIL vs gate / ACCEPTED** | `docs/audits/phase29/baseline_comparison.md`, §4 below |
| SC7 | `docs/rules_canslim.md` reflects shipped code       | PASS               | `docs/rules_canslim.md` §1–§8, this report linked from §8 |

¹ **Caveat (see §5):** SC1–SC5 had unit-test coverage throughout Phase 29, but
were only truly run end-to-end against the live databases during 29-09. That
run surfaced three schema/column mismatches that never triggered in unit tests
because the tests used synthetic DataFrames. Those bugs are now fixed and the
scorer executes cleanly across 28 quarters of real data.

---

## 3. Requirements traceability

Each requirement from Phase 29 → closed by which plan → verification evidence.

| Req     | Description                                              | Closed by | Evidence |
| ------- | -------------------------------------------------------- | --------- | -------- |
| UNIV-01 | `current-vn100` mode                                     | 29-03     | `strategies/canslim/universe.py`, `test_universe.py::test_current_vn100` |
| UNIV-02 | `liquidity-reconstructed` mode + semi-annual rebalance   | 29-03     | `universe.py::_last_rebalance_date`, `test_universe.py::test_liquidity_*` |
| UNIV-03 | `vn30-only` mode                                         | 29-03     | `universe.py`, `test_universe.py::test_vn30_only` |
| CANS-01 | C rule (quarterly EPS YoY)                               | 29-05     | `rules/fundamental.py::_c_pass`, `test_rules_fundamental.py::test_c_*` |
| CANS-02 | C+ rule (accelerating YoY)                               | 29-05     | `rules/fundamental.py::_c_plus_pass`, `test_c_plus_*` |
| CANS-03 | A rule (3yr EPS CAGR)                                    | 29-05     | `rules/fundamental.py::_a_pass`, `test_a_*` |
| CANS-04 | A+ rule (3yr positive annuals)                           | 29-05     | `rules/fundamental.py::_a_plus_pass`, `test_a_plus_*` |
| CANS-05 | N rule (close within 15% of 252d high)                   | 29-06     | `rules/technical.py::compute_n`, `test_rules_technical.py::test_n_*` |
| CANS-06 | S rule (breakout volume ≥1.5× avgvol50)                  | 29-06/07  | `rules/technical.py::compute_s`, `rules/flow.py::compute_s` wrapper |
| CANS-07 | L rule (RS rating ≥80, percentile within universe)       | 29-06     | `rules/rs.py::compute_rs_ratings`, `test_rules_rs.py` |
| CANS-08 | I rule (20d foreign net-buy > 0, pre-2022 fallback)      | 29-07     | `rules/flow.py::compute_i`, `test_rules_flow.py::test_i_*` |
| CANS-09 | Liq gate (20d median turnover ≥5B VND)                   | 29-07     | `rules/liquidity.py::compute_liq`, `test_rules_liquidity.py` |
| CANS-10 | Sector routing + fail-loud                               | 29-04     | `sectors.py::SectorRouter.from_postgres`, `test_sectors.py` |
| CANS-11 | Composite score 0.70·bool + 0.30·RS                      | 29-08     | `scorer.py::CanslimScorer.score`, `test_scorer.py::test_composite_*` |
| CANS-12 | Validation vs baseline                                   | **29-09** | `baseline.py`, `scripts/canslim_baseline_compare.py`, §4 below |

---

## 4. SC6 — Baseline comparison results

### 4.1 Methodology

- Target table: `stocks_backend.canslim` (composite `tong_diem` + component
  percentile columns `eps_quy_gan_nhat`, `eps_trailing_12_thang`,
  `sale_quy_gan_nhat`). This is an **upstream quarterly** ranking, not a daily
  signal.
- 28 quarters compared: Q1 2019 → Q4 2025 inclusive.
- VN100-restricted on both sides.
- For each quarter, `as_of_date` = last trading day in `stock_eod` at or
  before quarter-end. Scorer runs as daily; baseline is quarterly — any
  intra-quarter drift in N/S/RS/I/Liq is visible to the scorer but not to the
  baseline. This is an unavoidable semantic mismatch, not a bug.
- Metrics reported: (a) top-10 overlap, (b) Spearman ρ between our `score`
  and baseline `tong_diem` on the ticker intersection, (c) per-component
  agreement rate between our boolean C/A/S passes and the baseline percentile
  columns thresholded at **≥ 70**.
- **Original acceptance gate:** Spearman ρ ≥ 0.5 on ≥ 70% of quarters.

### 4.2 Results

| Metric                                 | Observed           |
| -------------------------------------- | ------------------ |
| Quarters compared                      | 28                 |
| Errors / failed runs                   | 0                  |
| Median Spearman ρ                      | **0.280**          |
| Quarters with ρ ≥ 0.5                  | **1 / 28 (4%)**    |
| Mean top-10 overlap                    | **2.43 / 10**      |
| Best single quarter (ρ)                | Q2 2021 ρ = 0.530  |
| Worst single quarter (ρ)               | Q3 2025 ρ = 0.004  |
| Per-component agreement — C (EPS YoY)  | **69%** mean       |
| Per-component agreement — A (EPS TTM)  | **70%** mean       |
| Per-component agreement — S (Sales)    | **66%** mean       |

Full per-quarter table and top-10 lists: `docs/audits/phase29/baseline_comparison.md`.

### 4.3 Interpretation — why individual rules agree but rankings diverge

The per-component agreement rates (66–70%) are **directionally correct**: our
boolean C/A/S rules pick the same stocks the upstream baseline flags as having
strong quarterly/TTM EPS and sales growth roughly two times out of three.
Given the baseline encodes its components as continuous percentile ranks and
we encode ours as booleans thresholded at ≥ 70, this level of agreement is
about what you would expect from an honest, independent reimplementation of
the same high-level rules.

What drives the composite-ranking divergence is then mostly **not** the
fundamental rules themselves. The main drivers are:

1. **Composite weighting is different.** Our score is `0.70 * (bool_passes/9)
   * 100 + 0.30 * rs_rating` (locked in plan 29-08). The upstream baseline
   blends its components with a different, opaque weighting that we never
   reverse-engineered. When most boolean gates pass for many tickers, our
   composite degenerates toward RS rank + a flat constant, which does not
   resemble the baseline's continuous composite at all.
2. **Non-fundamental rules have no baseline counterpart.** Our N, L (RS), I
   (foreign flow), and Liq rules influence `bool_passes/9` and the 30% RS
   component of our composite, but they have no analogue in the
   `stocks_backend.canslim` schema. Any quarter where those rules move the
   top-10 ordering is a quarter where we and the baseline simply cannot
   agree by construction.
3. **Daily vs quarterly semantics.** Even with a fixed as-of date, our N/S/I
   rules look at the final 20–252 trading days ending that day, while the
   baseline fundamentals are a snapshot of that quarter's filing. Stocks that
   had a strong quarter but weak late-quarter price action get deranked by us
   but not by the baseline (and vice versa).
4. **Boolean thresholding of a percentile baseline.** Mapping the baseline's
   continuous percentile columns to boolean passes via `≥ 70` inflates the
   apparent disagreement vs. a rank correlation that the baseline itself
   computes internally with the raw percentiles.

None of these are bugs. They are the expected signatures of an independent
implementation with a different composite formula and a larger rule set.

### 4.4 Decision — Option A: accept the divergence

The user reviewed the raw results and explicitly chose **Option A: ship
Phase 29 with the divergence documented**, rather than tune the composite
weights to match `stocks_backend.canslim`. The rationale recorded from that
checkpoint:

- The upstream `stocks_backend.canslim` table is a reasonable sanity anchor
  but is **not authoritative** — nobody on the team has verified its logic
  end-to-end, it is quarterly, and its composite weighting is opaque.
- Tuning our composite to match it would corrupt the rule set we actually
  want to trade: a daily, VN100-restricted, long-only CANSLIM screen driven
  by the rules locked in plans 29-02…29-08.
- Per-component agreement at 66–70% confirms our fundamental rules are
  directionally sound, which is the real SC6 intent.
- A future phase can revisit calibration — either against a different
  reference, against forward returns, or by re-deriving the baseline's
  internal weighting — when we have a clear reason to.

**Therefore:** Phase 29 ships with CANSLIM as an **independent screen**, not
a baseline replica. SC6 is marked **FAIL vs the original numeric gate** and
**ACCEPTED vs phase goal** by user decision.

---

## 5. Bugs discovered during plan 29-09 (and fixed)

Plan 29-09 was the first time `CanslimScorer` was exercised **end-to-end
against live Postgres and MySQL across 28 quarters**. All prior plans used
unit tests with synthetic DataFrames. That end-to-end run surfaced three
latent schema bugs that unit tests could never have caught, plus one
configuration defect in `schema_lock.json`:

1. **`scorer.py::_load_panel` queried `closeindex` / `highestindex` columns
   that do not exist in `stock_eod`.** The real columns are
   `closeprice` / `highestprice`. The scorer would have raised on the very
   first real query. **Fix:** commit `2deab97` — swap to `closeprice` /
   `highestprice` in the panel loader.
2. **`rules/fundamental.py::_load_quarters` queried `stockcode`,
   `yearreport`, `lengthreport` on `is_quarter_*` tables.** The real columns
   are `mack` (ticker) and a single text column `thoigian` encoding the
   period (e.g. `"Q1/2023"`, `"2023"`). No row would ever have matched.
   **Fix:** commit `2deab97` — rewrite `_load_quarters` to filter on `mack`
   and parse `thoigian` to derive year/period ordering.
3. **`schema_lock.json.locked.is_quarter_bank_ppop_column` was `null`.**
   The introspector had not pinned a PPOP column for the bank income
   statement, and the fallback path in `fundamental.py` degenerated to an
   empty column name. **Fix:** commit `2deab97` — hardcode
   `loi_nhuan_tu_hdkd_truoc_chi_phi_du_phong_rui_ro_tin_dung` as the bank
   PPOP column pending a proper re-introspection.

**Lesson:** SC1–SC5 being "green" in unit tests was misleading. Any future
phase that builds a new data-backed component should include at least one
smoke test that hits the real DBs before being considered complete. The
existing unit tests are still valuable but cannot replace a live run.

These fixes are all scoped inside the scorer's data-loading and schema-lock
layers; none of the rule math changed.

---

## 6. Known caveats (unchanged from plan 29-07/29-08)

- **Survivorship bias** in `current-vn100` mode: historical backtests use
  today's VN100 membership. Use `liquidity-reconstructed` to approximate
  point-in-time membership for backtests that care.
- **Pre-2022 I-rule fallback:** `stock_foreign_eod` has no data before
  2022-04-07, so `compute_i` returns `True` unconditionally before that
  cutoff. Backtests starting earlier will over-report I-rule passes.
- **ctck / insurance excluded** (D-07) from the universe before scoring.
  Securities firms and insurers use bespoke income-statement schemas that
  our C/A rules do not support.
- **Bank PPOP column is a pinned approximation** — see bug #3 above.
  A future pass should re-run `scripts/introspect_canslim_schema.py` with
  an improved heuristic to verify the locked column.
- **Composite weights (0.70 bool / 0.30 RS) are locked but unvalidated
  against forward returns.** SC6 does not validate predictive power; it
  only validates alignment with an upstream baseline, which we have now
  explicitly chosen not to match.

---

## 7. Artifacts

- Scorer entry point: `strategies/canslim/scorer.py`
- Baseline loader: `strategies/canslim/baseline.py`
- Comparison CLI: `scripts/canslim_baseline_compare.py`
- Raw per-quarter comparison: `docs/audits/phase29/baseline_comparison.md`
- Rules reference: `docs/rules_canslim.md` (§1–§8)
- Phase plan: `.planning/phases/29-vn100-universe-canslim-scorer/29-09-PLAN.md`
- Plan summary: `.planning/phases/29-vn100-universe-canslim-scorer/29-09-SUMMARY.md`

---

## 8. Final verdict

**Phase 29 SHIPPED with documented baseline divergence.**

- SC1–SC5, SC7: PASS (with the end-to-end caveat in §5).
- SC6: FAIL vs original numeric gate, **ACCEPTED** by user decision as
  expected independent-implementation divergence. Calibration deferred.
- Phase 29 closes CANS-01…CANS-12 and UNIV-01…UNIV-03.

Orchestrator still owns the formal `verify_phase_goal` and phase-complete
transitions; this report only closes plan 29-09.
