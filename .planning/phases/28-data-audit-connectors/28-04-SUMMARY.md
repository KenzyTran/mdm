---
phase: 28-data-audit-connectors
plan: 04
subsystem: connectors
tags: [eps, fundamentals, data-audit, canslim]
requirements: [DATA-04]
requires: []
provides: ["connectors.eps.resolve_eps_publish_date"]
affects: ["phase-29 CANSLIM C/A rules (look-ahead-bias gate)"]
tech-stack:
  added: []
  patterns: ["pure-function", "priority-fallback-imputation"]
key-files:
  created:
    - connectors/eps.py
  modified:
    - tests/test_eps_publish.py
decisions:
  - "Q1-Q3 imputation offset: period_end + 45 days"
  - "Q4/annual imputation offset: period_end + 90 days"
  - "Real-column priority: publish_date > announce_date > updated_at"
  - "Missing yearreport raises ValueError (hard fail, not silent)"
metrics:
  duration: "~5 min"
  completed: "2026-04-08"
  tasks: 1
  tests: 10
---

# Phase 28 Plan 04: EPS Publish Date Resolution Summary

Pure `resolve_eps_publish_date(df)` helper that guarantees every fundamentals row has a `publish_date` column — either taken from a real source column or imputed from `yearreport`/`lengthreport` per D-08/D-09/D-10. This is the canonical look-ahead-bias gate for Phase 29 CANSLIM C/A rules.

## What Was Built

- `connectors/eps.py` — `resolve_eps_publish_date` pure function + `_period_end` / `_impute_one` helpers, no DB or env access.
- Resolution order per row:
  1. Use existing `publish_date` if non-null.
  2. Else fall back to `announce_date`, then `updated_at`.
  3. Else impute from `(yearreport, lengthreport)`: period_end + 45d for Q1-Q3, + 90d for Q4/annual/NaN.
- `tests/test_eps_publish.py` — 10 unit tests covering Q1-Q4 imputation, annual-NaN path, all three real-column shortcuts, mixed real+imputed rows, and the missing-yearreport error path.

## Verification

- `uv run pytest tests/test_eps_publish.py -q` → **10 passed**.
- Acceptance criteria from plan all satisfied (file exists, function signature present, priority constant present, all named tests present).

## Deviations from Plan

None — plan executed exactly as written.

## Commits

- `e410efc` feat(28-04): implement resolve_eps_publish_date + 10 unit tests

## Self-Check: PASSED

- FOUND: connectors/eps.py
- FOUND: tests/test_eps_publish.py
- FOUND: commit e410efc
