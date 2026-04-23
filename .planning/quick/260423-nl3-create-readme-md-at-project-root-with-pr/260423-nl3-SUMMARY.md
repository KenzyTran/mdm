---
phase: 260423-nl3
plan: 01
subsystem: docs
tags: [readme, onboarding, quick-task]
requirements:
  completed: [README-01]
dependency-graph:
  requires: []
  provides: ["project-root human-readable overview"]
  affects: ["new-contributor onboarding", "repo first impression"]
tech-stack:
  added: []
  patterns: ["single-page README", "milestone verdict table"]
key-files:
  created: ["README.md"]
  modified: []
decisions:
  - "Headline uses shipped v6.0 numbers (+238.8% / CAGR 11.5% / MaxDD −28.2%) in top-of-README summary — reconciled Phase 42 numbers (11.47% / -28.17% / +238.78%) are semantically identical and acceptable either way; plan specified shipped headline preferred at top"
  - "Dashboard URL omitted from README body — plan marked it optional and the README targets a technical onboarding audience, not a stakeholder deck"
  - "Milestone table uses plain ASCII hyphen for v1.0-v5.0 span and Unicode minus for drawdown signs; mixed intentionally because drawdowns are signed numbers while version spans are not"
metrics:
  duration: "~6 min"
  completed: 2026-04-23
---

# Quick Task 260423-nl3: Create README.md at Project Root — Summary

Added a project-root `README.md` so human contributors and auditors can orient without reading `.planning/PROJECT.md`. The README covers what the project is, the current v6.0 production baseline, the v1.0-v10.0 milestone journey with explicit verdicts, the two primary backtest entry points, the repo layout, the hard constraints, and drill-down links to four canonical specs.

## Objective

Ship a single-page `README.md` at `C:/Users/trant/projects/mdm/README.md` with exactly the seven sections the plan specified, covering: title + one-paragraph intro, current production model, milestone history (v1.0 through v10.0), quick start, repo layout, constraints, and further reading. No emoji. No references to Claude / AI / LLM / GSD / get-shit-done. Exactly one h1.

## What Was Built

**Task 1 — Write README.md at project root** (commit `392775e`):

- Single `# MDM Reverse-Engineering & VN30 Market Timing` title + opening paragraph covering MDM reverse-engineering (962-signal NASDAQ history 1974-2026), VN30 adaptation, v7.0 VN100 CANSLIM+MDM portfolio composition, and the independent VSA track.
- `## Current Production Model` section stating the v6.0 HybridEngine + fail-safe baseline with the shipped headline numbers verbatim (+238.8%, CAGR 11.5%, MaxDD −28.2%) plus a v7.0 companion paragraph citing CANSLIM+MDM OOS metrics (CAGR 10.18%, Sharpe 0.813, MaxDD −16.31%).
- `## Milestone History` table with exactly the six required rows (v1.0-v5.0, v6.0, v7.0, v8.0, v9.0, v10.0) and SHIPPED / SHIPPED (production) / SHIPPED / REJECTED / REJECTED / IN PROGRESS (retain-v6.0 branch) verdicts in that order.
- `## Quick Start` block citing Python 3.10+, uv, and both entry-point scripts with the correct `scripts/` prefix (`scripts/run_backtest.py`, `scripts/run_hybrid_backtest.py`).
- `## Repo Layout` bullets covering `strategies/` (with all eight subpackages enumerated), `core/`, `analysis/`, `connectors/`, `scripts/`, `tests/`, `data/`, `output/`, `docs/`, `.planning/`, plus the Code-Docs Sync Rule footer.
- `## Constraints` bullets: research-only, US data ~1000x scaling, VN30 microstructure (T+2.5 / 7% / derivative expiry), public-signal validation lag.
- `## Further Reading` with five drill-down links: `portfolio_system_overview.md`, `strategy_v7.md`, `data_dictionary.md`, `rules_mdm_hybrid.md`, `rules_vsa.md`.
- Final `*Last updated: 2026-04-23*` stamp.

File length: **66 lines**.

## Verification

Plan's automated verify gate executed and printed `OK`:

```
python -c "import re,sys; t=open('README.md',encoding='utf-8').read(); emoji=re.findall(...); banned=[...]; required=[...]; missing=[...]; h1=len(re.findall(r'(?m)^# [^#]', t)); ..."
```

Gate checks confirmed:

- 0 emoji characters.
- 0 banned tokens (`Claude`, `GSD`, `/gsd:`, `get-shit-done`, ` AI `, ` LLM `).
- All 16 required tokens present verbatim: `docs/portfolio_system_overview.md`, `docs/strategy_v7.md`, `docs/data_dictionary.md`, `docs/rules_mdm_hybrid.md`, `scripts/run_backtest.py`, `scripts/run_hybrid_backtest.py`, `v6.0`, `v7.0`, `v8.0`, `v9.0`, `v10.0`, `238.8`, `11.5`, `0.813`, `0.645`, `0/39`.
- Exactly 1 h1 header.

Drill-down link resolution check:

```
test -f docs/portfolio_system_overview.md && test -f docs/strategy_v7.md \
  && test -f docs/data_dictionary.md && test -f docs/rules_mdm_hybrid.md && echo LINKS_OK
```

Output: `LINKS_OK`.

## Deviations from Plan

None. The plan executed exactly as written. All facts-locked numbers reproduced verbatim from the `<facts_locked_from_context>` block. All six negative constraints honored. All six must-have truths satisfied. The optional dashboard URL was intentionally omitted (plan explicitly marked it optional).

## Commits

- `392775e` — docs(260423-nl3): add project-root README.md

## Self-Check: PASSED

- Created file exists: `README.md` — FOUND.
- Commit exists: `392775e` — FOUND in `git log`.
- Verify gate: OK (exit 0).
- Drill-down links: all four resolve (LINKS_OK).
