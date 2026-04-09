---
phase: 29-vn100-universe-canslim-scorer
verified: 2026-04-09T00:00:00Z
status: passed
score: 15/15 requirements satisfied; 7/7 success criteria accounted for (SC6 ACCEPTED per Option A); test-suite gap resolved in commit 47a286e
re_verification: 2026-04-09
gaps:
  - truth: "Unit test suite for strategies/canslim runs green"
    status: resolved
    resolution: "Commit 47a286e updated _quarterly_frame and _fake_quarters to use mack/thoigian schema; uv run pytest tests/canslim/ now reports 73/73 passed."
    reason: >
      8 tests fail in tests/canslim/test_rules_fundamental.py and
      tests/canslim/test_scorer.py with KeyError: 'thoigian'. Plan 29-09 fixed
      a production schema bug (is_quarter_* tables use `mack`/`thoigian` not
      `stockcode`/`yearreport`/`lengthreport`) in strategies/canslim/rules/fundamental.py,
      but the synthetic DataFrame fixtures in the test files were not updated
      to the new schema. The audit (§5) acknowledges the fixtures are stale
      and recommends live-DB smoke tests as follow-up, but does not call out
      that these specific unit tests now FAIL rather than merely being weak.
      CI / `uv run pytest tests/canslim/` is red.
    artifacts:
      - path: tests/canslim/test_rules_fundamental.py
        issue: "Fixture rows use old schema (stockcode/yearreport/lengthreport); compute_fundamentals now reads `thoigian` — KeyError"
      - path: tests/canslim/test_scorer.py
        issue: "Scorer integration tests fall through to fundamental.py and crash on the same KeyError"
    missing:
      - "Update test fixtures in test_rules_fundamental.py to use the mack/thoigian schema so compute_fundamentals can parse them"
      - "Update test_scorer.py fixtures the same way (or stub compute_fundamentals for scorer tests)"
      - "Re-run uv run pytest tests/canslim/ and confirm 73/73 pass"
---

# Phase 29: VN100 Universe + CANSLIM Scorer — Verification Report

**Phase Goal (ROADMAP):** Daily CANSLIM rank for the VN100 universe is computable, configurable, and validated against project's existing baseline.

**Verified:** 2026-04-09
**Status:** gaps_found (1 gap — stale unit-test fixtures from 29-09 schema bug fix)
**Re-verification:** No — initial verification.

**Important context honored:** Per task brief, SC6 (baseline alignment) is treated as ACCEPTED with documented caveat per Option A decision and is NOT used to fail the phase. Verification focuses on whether every other SC and requirement is genuinely met, plus a regression scan for anti-patterns and test rot.

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
| - | ------------------------- | ------ | -------- |
| SC1 | VN100 universe loader returns ticker set per date with semi-annual rebalance; proxy fallback documented | VERIFIED | `strategies/canslim/universe.py` implements `_last_rebalance_date` (Jan/Jul), three modes, and a `_filter_by_history` D-05 guard. Proxy fallback documented in module docstring and 29-03-SUMMARY.md. |
| SC2 | Three universe modes selectable: current-VN100, liquidity-reconstructed, VN30-only | VERIFIED | `universe.py` VALID_MODES = ("current-vn100", "liquidity-reconstructed", "vn30-only"); `__post_init__` rejects anything else; each mode has its own private method. |
| SC3 | Scorer computes C/C+/A/A+/N/S/L/I/Liquidity per stock/day; respects EPS publish_date guard (no look-ahead) | VERIFIED | `scorer.py::CanslimScorer.score` wires all nine rules and produces the 14-column OUTPUT_COLUMNS frame. `rules/fundamental.py::_load_quarters` routes every row through `resolve_eps_publish_date` and filters `publish_date > as_of_date`. |
| SC4 | Sector handling — non-financials use C/A directly; banks substitute PPOP growth; CTCK/Insurance excluded | VERIFIED | `sectors.py::SectorRouter.route` + `is_excluded`; `fundamental.py::compute_fundamentals` branches on sector, uses `is_quarter_bank` + PPOP column for banks and returns `(False,)*4` for ctck/insurance. `SectorRouter.from_postgres` fails loud (>50% missing sectors). |
| SC5 | `CanslimConfig` dataclass with all thresholds (defaults per spec) | VERIFIED | `config.py` defaults match spec exactly: c_threshold=0.20, a_threshold=0.15, n_within_high=0.15, s_vol_mult=1.5, l_rs_threshold=80, i_lookback_days=20, liquidity_min_turnover_vnd=5B. `__post_init__` validates ranges. RS weights sum to 1.0 enforced. |
| SC6 | Spot-check vs rank_top_stocks.diem_canslim (≥4/10 overlap acceptable) | ACCEPTED (documented divergence, per Option A) | `docs/audits/phase29-canslim-validation.md` records median Spearman ρ = 0.280, 2.43/10 top-10 overlap across 28 quarters. User accepted as independent screen, not replica. `scripts/canslim_baseline_compare.py` + `strategies/canslim/baseline.py` exercise the harness. Per task brief: NOT a phase-level fail. |
| SC7 | RS rating uses `0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252`, percentile-ranked within active universe | VERIFIED | `rules/rs.py::compute_rs_ratings` — weights/lookbacks come from `CanslimConfig.rs_roc_days/rs_weights` (defaults (63,126,189,252) and (0.4,0.2,0.2,0.2)); `raw.rank(pct=True) * 100` percentile within `uset`. `CanslimConfig.__post_init__` locks weight sum = 1.0. |

**Score:** 7/7 SCs accounted for (6 VERIFIED + 1 ACCEPTED per user decision).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `strategies/canslim/config.py` | CanslimConfig dataclass + validation | VERIFIED | 65 lines; dataclass + `__post_init__` + `to_dict`. |
| `strategies/canslim/universe.py` | 3-mode loader + Jan/Jul rebalance + history filter | VERIFIED | 124 lines; all three modes + D-05 filter + fail-loud on invalid mode. |
| `strategies/canslim/sectors.py` | Sector router with fail-loud | VERIFIED | 97 lines; `from_postgres` raises on >50% missing; `is_excluded` used by scorer. |
| `strategies/canslim/rules/fundamental.py` | C/C+/A/A+ + sector branch + publish-date guard | VERIFIED | 270 lines; pure helpers `compute_c/_plus/a/a_plus` + orchestrator `compute_fundamentals`; `resolve_eps_publish_date` invoked before rule math. |
| `strategies/canslim/rules/technical.py` | N + S helpers | VERIFIED | 59 lines; 252d-high N rule and avgvol50 S rule. |
| `strategies/canslim/rules/rs.py` | Percentile-ranked RS rating | VERIFIED | 97 lines; weighted ROC + universe-wide `rank(pct=True)*100`. |
| `strategies/canslim/rules/flow.py` | I rule with pre-2022 fallback | VERIFIED | 90 lines; `FOREIGN_DATA_START = 2022-04-07` short-circuit; net-buy sum > 0 check. |
| `strategies/canslim/rules/liquidity.py` | 20d median turnover gate | VERIFIED | 36 lines; median (not mean), rationale documented in docstring. |
| `strategies/canslim/scorer.py` | End-to-end CanslimScorer | VERIFIED | 184 lines; imports all rules, sector router, universe loader; locked composite `0.70*bool + 0.30*RS`. |
| `strategies/canslim/baseline.py` | Baseline comparison loader | VERIFIED | 171 lines; `stocks_backend.canslim` loader for 29-09. |
| `scripts/canslim_baseline_compare.py` | 28-quarter comparison CLI | VERIFIED | Exists; referenced by audit report. |
| `scripts/introspect_canslim_schema.py` | Live-schema introspection | VERIFIED | Exists; feeds schema_lock.json. |
| `schema_lock.json` | Pinned live schema | VERIFIED | Present in phase dir with timestamped introspection of stock_list, is_quarter_*, stock_eod, stock_foreign_eod. |
| `docs/rules_canslim.md` | Rules doc reflecting shipped code | VERIFIED | 296 lines including §8 baseline validation section (per 29-09 audit ref). |
| `docs/audits/phase29-canslim-validation.md` | Phase-level SC1–SC7 roll-up + bug writeups | VERIFIED | 260 lines; SC table, bug post-mortems, Option A rationale. |

### Key Link Verification (Wiring)

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| `scorer.py::CanslimScorer.score` | `UniverseLoader.get` | `self.universe_loader.get(as_of_date)` | WIRED |
| `scorer.py` | `SectorRouter.is_excluded` | filter comprehension on tickers | WIRED |
| `scorer.py` | `compute_fundamentals` | per-ticker loop | WIRED |
| `scorer.py` | `compute_n` / `compute_s` / `compute_liq` | per-ticker loop on ohlcv slice | WIRED |
| `scorer.py` | `compute_rs_ratings` | called once with full panel + tickers | WIRED |
| `scorer.py` | `compute_i` | per-ticker loop with pg_engine | WIRED |
| `fundamental.py::_load_quarters` | `connectors.eps.resolve_eps_publish_date` | direct import + invocation before filter | WIRED |
| `fundamental.py::compute_fundamentals` | `SectorRouter.route` + schema_lock | sector branch + column lookup | WIRED |
| `baseline.py` + `canslim_baseline_compare.py` | `CanslimScorer` | harness runs scorer vs upstream table across 28 quarters | WIRED (evidence: audit report §4) |

No orphaned modules. Every rule module is imported and exercised by `scorer.py`.

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `CanslimScorer.score` | `panel` (OHLCV) | `_load_panel` → `stock_eod` Postgres | Yes (exercised live in 29-09) | FLOWING |
| `CanslimScorer.score` | `rs_series` | `compute_rs_ratings(panel, ...)` | Yes | FLOWING |
| `compute_fundamentals` | `df` (quarters) | `_load_quarters` → MySQL `is_quarter_*` via mack/thoigian | Yes (fixed in 29-09 commit 2deab97) | FLOWING |
| `compute_i` | `df` (net_buy) | Postgres `stock_foreign_eod` | Yes (with pre-2022 fallback) | FLOWING |
| `SectorRouter.from_postgres` | `mapping` | Postgres `stock_list.sector_column` | Yes | FLOWING |

All dynamic-data artifacts have traceable upstream sources that produce real data in the 28-quarter 29-09 run. Baseline comparison report in `docs/audits/phase29/baseline_comparison.md` is the evidence that data actually flows end-to-end.

### Requirements Coverage

Every requirement ID from the phase manifest is accounted for in both PLAN frontmatter and production code.

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| UNIV-01 | 29-03 | VN100 loader from stock_list.nhomtop (or proxy) | SATISFIED | `universe.py::_current_vn100` SELECT on `nhomtop IN ('VN30','VN100')` |
| UNIV-02 | 29-03 | Semi-annual rebalance (Jan/Jul) | SATISFIED | `universe.py::_last_rebalance_date` |
| UNIV-03 | 29-03 | Three modes selectable | SATISFIED | `VALID_MODES` + dispatch in `get()` |
| CANS-01 | 29-05 | C rule — quarterly EPS YoY ≥20% with publish_date guard | SATISFIED | `fundamental.py::compute_c` + `_load_quarters` publish-date filter |
| CANS-02 | 29-05 | C+ rule — acceleration vs prior 2 quarters | SATISFIED | `fundamental.py::compute_c_plus` |
| CANS-03 | 29-05 | A rule — 3yr EPS CAGR ≥15% | SATISFIED | `fundamental.py::compute_a` (TTM/TTM-2y) |
| CANS-04 | 29-05 | A+ — annual EPS positive 3 years | SATISFIED | `fundamental.py::compute_a_plus` over rolling-TTM annuals |
| CANS-05 | 29-06 | N — close within 15% of 252d high | SATISFIED | `technical.py::compute_n` |
| CANS-06 | 29-07 (and 29-06) | S — breakout vol ≥1.5× avgvol50 | SATISFIED | `technical.py::compute_s`; re-exported via `flow.py::compute_s` |
| CANS-07 | 29-06 | L — IBD-style RS, percentile-rank within VN100, ≥80 | SATISFIED | `rs.py::compute_rs_ratings` + `scorer.py` threshold |
| CANS-08 | 29-07 | I — 20d foreign net buy > 0, pre-2022 fallback | SATISFIED | `flow.py::compute_i` + `FOREIGN_DATA_START` short-circuit |
| CANS-09 | 29-07 | Liquidity — 20d median turnover ≥5B VND | SATISFIED | `liquidity.py::compute_liq` |
| CANS-10 | 29-04 | Sector handling + bank PPOP sub + ctck/insurance excluded | SATISFIED | `sectors.py::SectorRouter` + `fundamental.py` branch |
| CANS-11 | 29-02 + 29-08 | CanslimConfig + end-to-end scorer | SATISFIED | `config.py` + `scorer.py` (LOCKED composite 0.70/0.30) |
| CANS-12 | 29-09 | Validation vs baseline | SATISFIED (documented divergence) | `baseline.py` + `canslim_baseline_compare.py` + `docs/audits/phase29-canslim-validation.md` |

No orphaned requirements — every ID in REQUIREMENTS.md (UNIV-01..03, CANS-01..12) is claimed by a plan in this phase and implemented in code.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `strategies/canslim/rules/technical.py` | 52-59 | Legacy stub functions `check_n_new_high`, `check_n_pivot_breakout` raise NotImplementedError | Info | Dead compatibility shims from 29-01 scaffold. Not called by scorer. |
| `strategies/canslim/rules/rs.py` | 90-97 | Legacy stub functions `check_l_rs_rank`, `check_l_industry_leader` | Info | Same as above. |
| `strategies/canslim/rules/flow.py` | 83-90 | Legacy stub `check_i_foreign_net_buy`, `check_s_volume_surge` | Info | Same. |
| `strategies/canslim/rules/liquidity.py` | 34-36 | Legacy `check_liquidity_turnover` stub | Info | Same. |
| `strategies/canslim/rules/fundamental.py` | 248-270 | Four `check_*` shim wrappers | Info | Harmless — they forward to `compute_fundamentals`. |
| `strategies/canslim/universe.py` | 120-124 | `load_vn100_universe` raises NotImplementedError | Info | Deprecation guard for old callers. |
| `strategies/canslim/rules/fundamental.py` | 213-216 | Hardcoded bank PPOP column fallback | Warning | Documented in audit §5 bug #3 as "pinned approximation pending re-introspection". Acceptable per Option A but tracked. |
| `strategies/canslim/scorer.py` | 168-170 | SQL SELECT uses `closeprice AS closeindex`/`highestprice AS highestindex` — name drift between `stock_eod` real schema and downstream alias | Info | Fixed in 29-09 (commit 2deab97). No impact. |

No Blocker anti-patterns. All NotImplementedError stubs are compatibility shims with clear deprecation messages and are not on the scorer hot path.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| canslim package imports cleanly | `uv run pytest tests/canslim/ -q` | 65 passed, 8 FAILED | FAIL |
| Failing tests all have same root cause | pytest output | All 8 failures are `KeyError: 'thoigian'` in fundamental/scorer tests | FAIL (single root cause) |
| Commit history contains 29-09 bug-fix commit | `git log --oneline -- strategies/canslim/` | `2deab97 feat(29-09): baseline comparison script + fix scorer schema bugs` present | PASS |
| Audit report exists and documents Option A | `docs/audits/phase29-canslim-validation.md` | 260 lines, §1 TL;DR explicitly says "SHIPPED with documented baseline divergence" | PASS |
| Baseline comparison raw results recorded | `docs/audits/phase29/baseline_comparison.md` | Exists | PASS |
| schema_lock.json present with live schema | phase-dir file | Present, introspected 2026-04-09 | PASS |

**Spot-check summary:** 4/6 pass. The two failures both stem from the same root cause: 29-09 fixed production code to read the real `mack`/`thoigian` columns but the synthetic DataFrame fixtures in `tests/canslim/test_rules_fundamental.py` and `tests/canslim/test_scorer.py` were left on the old fake `stockcode`/`yearreport`/`lengthreport` schema, so `_load_quarters` now crashes with `KeyError: 'thoigian'` on the stale fixtures.

### Human Verification Required

None. All automated verification is conclusive:

- Production wiring is verified via code inspection and matches the audit report's end-to-end 28-quarter run.
- SC6 divergence is a documented user-accepted outcome, not an open question.
- The one gap (stale test fixtures) is mechanically obvious and unambiguously fixable.

### Gaps Summary

Phase 29 meets its goal: the CANSLIM scorer is computable (`CanslimScorer.score` wires all nine rules end-to-end), configurable (`CanslimConfig` with validated thresholds), and validated against the `stocks_backend.canslim` baseline (28-quarter harness with documented Option-A acceptance of the numeric divergence). All 15 requirement IDs are implemented and wired in production code, the composite formula is locked, and the end-to-end run in 29-09 exercised the full stack against live Postgres + MySQL.

**One gap remains:** Plan 29-09 fixed three schema bugs in production but left the synthetic unit-test fixtures in `tests/canslim/test_rules_fundamental.py` and `tests/canslim/test_scorer.py` on the pre-fix schema. `uv run pytest tests/canslim/` now reports 65 passed / 8 FAILED, all failures sharing a single `KeyError: 'thoigian'` root cause. The audit (§5) acknowledges synthetic-fixture weakness as a lesson learned but does not explicitly call out that existing tests are now red. This is a Warning-level regression — production code is correct and exercised against real data, but the red test suite will block CI and mislead future contributors.

**Recommended follow-up (small plan, ~1 hour):** Update the two test files to use the mack/thoigian schema that `_load_quarters` now expects, re-run `uv run pytest tests/canslim/`, confirm 73/73 pass. No rule-math changes needed.

---

*Verified: 2026-04-09 — Claude (gsd-verifier). Honored task-brief instruction to accept SC6 divergence per Option A rather than fail the phase on the baseline alignment gate.*
