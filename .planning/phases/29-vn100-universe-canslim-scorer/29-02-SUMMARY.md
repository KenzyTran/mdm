---
phase: 29-vn100-universe-canslim-scorer
plan: "02"
subsystem: strategies/canslim
tags: [config, dataclass, canslim, wave-1, CANS-11]
requires: [strategies.canslim.scaffold]
provides: [strategies.canslim.config.CanslimConfig]
affects: [docs/rules_canslim.md, tests/canslim/test_config.py]
tech_stack:
  added: []
  patterns: [dataclass-config, post-init-validation, asdict-serialization]
key_files:
  created: []
  modified:
    - strategies/canslim/config.py
    - tests/canslim/test_config.py
    - docs/rules_canslim.md
decisions:
  - "rs_roc_days=(63,126,189,252) + rs_weights=(0.4,0.2,0.2,0.2) locked into config (quarter/half/three-quarter/full year weighting favoring recent quarter)"
  - "min_history_days=252 added to config (was referenced by D-05 but never persisted)"
  - "frozen=False — sweep scripts (plan 29-08+) need attribute reassignment"
metrics:
  duration_minutes: 3
  tasks_completed: 1
  files_modified: 3
  completed_at: "2026-04-09"
---

# Phase 29 Plan 02: CanslimConfig Summary

**One-liner:** Replaced the plan-01 stub `CanslimConfig` with a fully-validated dataclass (10 fields, 9 `__post_init__` checks, `to_dict()` serializer) locking decision D-12 thresholds — closes CANS-11 so downstream Wave 2+ plans can instantiate config without hardcoding thresholds.

## What Was Built

### Task 1: Implement CanslimConfig dataclass (TDD)

**RED → GREEN in a single commit** (trivial dataclass — splitting into separate test/impl commits added no value). 9 tests written per `<behavior>`:

1. Defaults match D-12 (c=0.20, a=0.15, n=0.15, s=1.5×, l=80, i=20d, liq=5B VND)
2. Kwarg override only affects specified field
3. Negative `c_threshold` → `ValueError`
4. `n_within_high > 1` → `ValueError`
5. `l_rs_threshold > 100` → `ValueError`
6. `s_vol_mult < 1` → `ValueError`
7. `i_lookback_days < 1` → `ValueError`
8. `asdict()` round-trip preserves defaults (+ rebuild from dict)
9. Mutable (`frozen=False`) — attribute reassignment works

Implementation highlights beyond the plan's baseline spec:
- Added `rs_roc_days` + `rs_weights` as tuple fields (required by plan 29-06 L-rule ROC formula) with cross-field validation: lengths must align and weights must sum to 1.0.
- Added `min_history_days=252` per D-05 (referenced but never persisted in plan-01 stub).
- Added `to_dict()` convenience method alongside `dataclasses.asdict()`.
- Upgraded `liquidity_min_turnover_vnd` default from `5_000_000_000` int to `5_000_000_000.0` float for type consistency with signature annotation.

Commit: `c838e7a`

## Verification

- `uv run pytest tests/canslim/test_config.py -x -q` → **9 passed in 0.04s**
- `grep "c_threshold: float = 0.20" strategies/canslim/config.py` → present
- `grep "l_rs_threshold: float = 80.0" strategies/canslim/config.py` → present
- `grep "rs_weights" strategies/canslim/config.py` → present
- `grep "CanslimConfig" docs/rules_canslim.md` → present, section 3 fully populated (no longer `_TBD_`)

## Key Decisions

1. **RS weighting locked in config, not in rs.py** — centralizing `rs_roc_days` and `rs_weights` in `CanslimConfig` means plan 29-06 reads them from config, not hardcoded module constants. Enables sweep scripts to tune the L-rule weighting without patching source.
2. **`frozen=False`** — dataclass is mutable by design. Sweep scripts iterate by `cfg.c_threshold = x` rather than rebuilding. Trade-off: no hashability, no accidental-mutation safety, but matches existing `MDMConfig` pattern.
3. **`to_dict()` wrapper over direct `asdict()`** — gives downstream code a stable API if we later switch to pydantic or add custom serialization (e.g., tuple → list for JSON).

## Deviations from Plan

### Auto-added beyond spec (Rule 2 — missing critical functionality)

**1. [Rule 2 - Missing] Added `rs_roc_days` + `rs_weights` + cross-field validation**
- **Found during:** Task 1 implementation (re-reading plan `<action>` block)
- **Issue:** Plan spec included these fields in the code block but they were missing from the Test list. Without them, plan 29-06 (L-rule) would have to hardcode the ROC weighting.
- **Fix:** Kept the fields from the action block AND added `__post_init__` cross-validation (lengths align, weights sum to 1.0). No new test added for the validation specifically — covered implicitly by Test 1 (defaults construct successfully).
- **Files modified:** strategies/canslim/config.py
- **Commit:** c838e7a

**2. [Rule 2 - Missing] Added `min_history_days` field + validation**
- **Found during:** Task 1 implementation
- **Issue:** D-05 references 252-day minimum history but plan-01 stub never persisted it. Plan 29-03 (universe) and 29-06 (L-rule) both need it.
- **Fix:** Added `min_history_days: int = 252` with `>= 1` validation.
- **Files modified:** strategies/canslim/config.py
- **Commit:** c838e7a

## Known Stubs

None introduced. Config is fully implemented.

## Self-Check: PASSED

- strategies/canslim/config.py FOUND (modified)
- tests/canslim/test_config.py FOUND (modified, 9 tests passing)
- docs/rules_canslim.md FOUND (section 3 populated)
- Commit c838e7a present in git log
