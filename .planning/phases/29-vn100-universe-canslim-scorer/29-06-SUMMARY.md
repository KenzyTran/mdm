---
phase: 29-vn100-universe-canslim-scorer
plan: "06"
subsystem: strategies/canslim
tags: [rules, technical, rs, canslim, wave-2, CANS-05, CANS-07]
requires: [strategies.canslim.config.CanslimConfig]
provides:
  - strategies.canslim.rules.technical.compute_n
  - strategies.canslim.rules.technical.compute_s
  - strategies.canslim.rules.rs.compute_rs_ratings
affects: [docs/rules_canslim.md]
tech_stack:
  added: []
  patterns: [pure-pandas-rule, percentile-rank, config-driven-weights]
key_files:
  created: []
  modified:
    - strategies/canslim/rules/technical.py
    - strategies/canslim/rules/rs.py
    - tests/canslim/test_rules_technical.py
    - tests/canslim/test_rules_rs.py
    - docs/rules_canslim.md
decisions:
  - "N rule reads min_history_days from config (252 default) instead of hardcoded 252 — one source of truth with D-05"
  - "compute_rs_ratings returns NaN (not False) for insufficient history so scorer can distinguish missing from failing"
  - "Extra tickers in the panel (outside the passed universe) are filtered out before ranking — rank is always universe-relative"
metrics:
  duration_minutes: 6
  tasks_completed: 2
  files_modified: 5
  completed_at: "2026-04-09"
---

# Phase 29 Plan 06: N Rule + RS Rating Summary

**One-liner:** Implemented CANSLIM N (close within 15% of 252d high), S helper (volume >= 1.5x avgvol50), and the locked L RS rating `0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252` percentile-ranked within the active universe — closes CANS-05 and CANS-07 with 14 passing tests.

## What Was Built

### Task 1: compute_n + compute_s (technical.py)

Replaced `check_n_new_high` / `check_n_pivot_breakout` stubs with two vectorised pandas helpers operating on a single-ticker long-format OHLCV frame (`tradingdate`, `closeindex`, `highestindex`, `totalvol`):

- `compute_n(ohlcv, as_of_date, config)` — True iff `close >= (1 - config.n_within_high) * max(highestindex over 252d)`. Returns False on insufficient history.
- `compute_s(ohlcv, as_of_date, config)` — True iff today's volume `>= config.s_vol_mult * mean(prior 50 volumes)`. Returns False if fewer than 51 bars.

Legacy stub names retained as `NotImplementedError` shims so any caller that still imports them fails loud instead of silently picking a stale module.

Tests (`tests/canslim/test_rules_technical.py`): 7 passing
1. Module imports smoke
2. N true: close 180 vs 252d high 200 (≥170)
3. N false: close 160 (<170)
4. N false: insufficient history (100 bars)
5. S true: today 200 vs avg50 100 (≥150)
6. S false: today 120 (<150)
7. S false: insufficient history (20 bars)

Commit: `bf6d9e2`

### Task 2: compute_rs_ratings (rs.py) + docs §5

Implemented the locked L rule formula consuming `CanslimConfig.rs_roc_days` and `CanslimConfig.rs_weights` so sweep scripts can tune weights without patching source. Process:

1. Filter panel to bars `<= as_of_date` AND `stockcode.upper() in universe`.
2. Group by ticker, compute `raw_rs = sum(w_i * ROC(lookback_i))`, returning NaN if any window is missing or history `< config.min_history_days`.
3. `raw.rank(pct=True, na_option="keep") * 100` — NaNs stay NaN, non-NaNs get a universe-relative percentile in `[0, 100]`.

`l_pass` is simply `rs_rating >= config.l_rs_threshold` (80 by default), applied by the scorer in a later plan.

Tests (`tests/canslim/test_rules_rs.py`): 7 passing
1. Module imports smoke
2. Single-ticker doubling → rank 100
3. Two-ticker ranking (AAA +50% → 100, BBB +10% → 50)
4. Insufficient history (100 bars) → NaN
5. l_pass threshold (80): HI pass, LO fail
6. Extra tickers in panel are filtered out — returned Series is universe-only
7. Numeric RS formula check (253-bar series with known ROC points)

Docs: `docs/rules_canslim.md` §5 replaced TBD stub with formulas, defaults, and test pointers. Code-Docs Sync rule satisfied — the commit touches both code and docs.

Commit: `7826ee2`

## Verification

- `uv run pytest tests/canslim/test_rules_technical.py tests/canslim/test_rules_rs.py -q` → **14 passed in 0.10s**
- `grep -q "n_within_high" strategies/canslim/rules/technical.py` → present
- `grep -q "s_vol_mult" strategies/canslim/rules/technical.py` → present
- `grep -q "0.4" strategies/canslim/rules/rs.py` → present
- `grep -q "rank(pct=True" strategies/canslim/rules/rs.py` → present
- `grep -q "0.4\*ROC(63) + 0.2\*ROC(126) + 0.2\*ROC(189) + 0.2\*ROC(252)" docs/rules_canslim.md` → present

## Key Decisions

1. **`min_history_days` read from config, not hardcoded.** N and RS both use `config.min_history_days` — keeps D-05 as the single source of truth and lets sweeps shorten the requirement for smoke runs without touching the rule code.
2. **NaN (not False) for insufficient RS history.** The scorer needs to distinguish "couldn't compute" from "computed and failed threshold" — NaN propagates through `rank(na_option="keep")` cleanly, and `l_pass = rs_rating >= threshold` evaluates False on NaN naturally.
3. **Panel filter before ranking.** `compute_rs_ratings` drops any ticker not in the passed `universe` before computing ranks, so the percentile is strictly universe-relative even if the caller passes a larger panel (typical — loaders may return the full VN100 panel).
4. **Legacy stub shims kept.** The plan-01 stubs (`check_n_new_high`, `check_l_rs_rank`, etc.) are retained as raising shims so old imports fail loud rather than silently resolving to nothing.

## Deviations from Plan

None that affected behavior. Two small-but-notable implementation choices:

- Kept legacy stub function names as raising shims (plan's action block showed a clean-room rewrite; retaining the shims costs nothing and protects any stale import).
- Added 1 extra test (module imports smoke) per rule module to match the sibling test files' convention — brings totals to 7/7 rather than the plan's 6/6. Still passes all acceptance criteria.

No Rule 1/2/3 auto-fixes were needed — the config, docs scaffolding, and test dir already existed from plans 29-01 and 29-02.

## Known Stubs

None introduced. `check_n_pivot_breakout` and `check_l_industry_leader` remain deferred to later plans (CANS-06 pivot price-action, CANS-08 industry leadership); they still raise `NotImplementedError` with clear messages.

## Self-Check: PASSED

- strategies/canslim/rules/technical.py FOUND (modified)
- strategies/canslim/rules/rs.py FOUND (modified)
- tests/canslim/test_rules_technical.py FOUND (modified, 7 tests passing)
- tests/canslim/test_rules_rs.py FOUND (modified, 7 tests passing)
- docs/rules_canslim.md FOUND (§5 populated)
- Commit bf6d9e2 present in git log
- Commit 7826ee2 present in git log
