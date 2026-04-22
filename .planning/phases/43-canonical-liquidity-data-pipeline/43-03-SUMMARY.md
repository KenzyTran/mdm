---
phase: 43-canonical-liquidity-data-pipeline
plan: 03
subsystem: docs
tags: [liquidity-proxy, sbv-events, macro-filter, merge-asof, publication-lag, canonical-spec]

# Dependency graph
requires:
  - phase: 43-01
    provides: "Hardened analysis/build_liquidity_proxy.py with 5-flag argparse CLI + retry + schema guard; final CSV schema (6 columns, 2867 rows, 2015-01-01 -> 2025-12-31)"
  - phase: 43-02
    provides: "data/sbv_policy_events.csv with frozen 5-column schema (12 rows, Reuters/SBV-press/Vietnam-News citations, easing|tightening only)"
provides:
  - "docs/liquidity_proxy_spec.md — production spec Phase 44 MacroFilter reads as the canonical contract for inputs + merge + publication-lag policy"
  - "Explicit pd.merge_asof(direction='backward') contract for BOTH proxy and SBV, with verbatim code blocks Phase 44 can copy"
  - "5 enumerated look-ahead traps per D-09 (2 over the 3-minimum requirement)"
affects:
  - 44 (MACRO-01..05 — reads this spec as source-of-truth for merge signatures, publication-lag handling, z-score computation order)
  - 45 (WF-01..03 — walk-forward grid-search scripts re-read the CSVs across train/test windows)
  - 46 (VAL-04 parity regression — any change to inputs or merge contract requires re-running this test)
  - 47 (DOC-01 — spec is the upstream for any v10.0 public-facing docs about the macro filter)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Production-spec-vs-research-doc separation: docs/liquidity_proxy_spec.md (contract, load-bearing) is distinct from docs/research/liquidity_proxy_correlation.md (evidence base, frozen)"
    - "Merge contract documented with verbatim Python code blocks so Phase 44 can copy-paste, not re-derive"
    - "Publication-lag policy split by data source: US-market tickers (natural 1-day lag via backward merge), SBV events (explicit +1 BusinessDay shift then backward merge)"

key-files:
  created:
    - docs/liquidity_proxy_spec.md
  modified: []

key-decisions:
  - "Spec placed at repo-root docs/ (NOT docs/research/) per the plan's explicit fence — docs/research is the research evidence base, docs/ is the production contract; this is load-bearing for Phase 44's VAL-04 parity"
  - "5 look-ahead traps enumerated vs the 3-minimum D-09 baseline — added (4) rolling-z-score-on-raw-CSV trap and (5) SBV direction='nearest' trap as belt-and-braces coverage for Phase 44's implementation review"
  - "Code-Docs Sync pointer added at the bottom of the spec: future Phase 44 work on strategies/mdm_hybrid/macro_filter*.py MUST update this spec in the same commit per CLAUDE.md Code-Docs Sync Rule — extends the existing strategies/<engine>/ <-> docs/rules_*.md pattern to cover the new macro-filter subsystem"
  - "Cross-reference to docs/research/liquidity_proxy_correlation.md kept as a final > See also footer — the research doc is the motivation/evidence, the spec is the contract; both remain valid and neither replaces the other"
  - "Merge contract documented with allow_exact_matches=True (not False) — same-date match allowed when both US and VN markets have a session that day; this is correct because US close still posts AFTER VN close on any given calendar date, so the exact-match only fires across identical local-date labels, not across overlapping trading hours"

patterns-established:
  - "Canonical-spec layout for data-contract docs: 7-section skeleton (Title, Canonical Inputs, Regeneration, Publication-Lag Policy, Merge Contract, Look-Ahead Traps Ruled Out, Extension Path) — reusable template for future data pipelines (e.g., foreign-flow data, MoF circulars)"
  - "Look-ahead trap enumeration as a first-class section — each trap numbered + bolded + explained + referenced back to the merge contract; makes the failure modes reviewable by a non-author"
  - "One-row-edit extension path documented explicitly so downstream analysts don't need to read builder code to append events"

requirements-completed: [LIQ-03]

# Metrics
duration: 2m
completed: 2026-04-22
---

# Phase 43 Plan 03: Canonical Liquidity Proxy Specification Summary

**Shipped `docs/liquidity_proxy_spec.md` — the production contract that freezes both canonical inputs (data/vn_liquidity_proxy.csv and data/sbv_policy_events.csv), documents the `pd.merge_asof(direction='backward')` merge Phase 44 MacroFilter MUST implement, specifies per-source publication-lag policy per D-08, and enumerates 5 look-ahead traps per D-09 — closes LIQ-03 and unblocks Phase 44 MACRO-01..05 from having to re-derive these contracts from quick-task artifacts.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-22T08:09:50Z
- **Completed:** 2026-04-22T08:12:05Z
- **Tasks:** 1 / 1
- **Files created:** 1 (`docs/liquidity_proxy_spec.md`)
- **Files modified:** 0

## Spec Metrics

- **Total line count:** 199 lines (plan target: >= 80, ~100-150 indicative range; exceeded for completeness without padding)
- **Section count:** 1 H1 + 6 H2 + 12 H3 = 7 top-level required sections in specified order:
  1. `# VN30 Liquidity Proxy + SBV Events — Canonical Spec` (H1 title + opening 3-paragraph motivation)
  2. `## Canonical Inputs` (with H3 subsections for each CSV)
  3. `## Regeneration` (CLI, defaults, retry/schema-guard policy)
  4. `## Publication-Lag Policy` (H3 subsections per data source)
  5. `## Merge Contract (for Phase 44 MacroFilter)` (H3 subsections for proxy, SBV, z-score)
  6. `## Look-Ahead Traps Ruled Out` (5 numbered traps)
  7. `## Extension Path` (H3 subsections for SBV events, proxy regeneration, ticker-set changes)
- **`merge_asof` mentions:** 10 (plan required >= 2 — well over)
- **`direction='backward'` mentions:** 11 (plan required >= 2)
- **H2 section count (`^## `):** 6 (matches the 6 non-title required sections)
- **Numbered look-ahead trap items:** 5 (plan required >= 3; added 2 extras — see Decisions Made)

## Cross-Check Against Upstream Plans

### CLI flag names (cross-check with 43-01-SUMMARY)

All 5 flags from 43-01 documented verbatim and matching source code `analysis/build_liquidity_proxy.py` lines 194-230:

| Flag | Default | Documented in spec | Matches 43-01 / source |
|---|---|---|---|
| `--start` | `2015-01-01` | Section 3 | Yes |
| `--end` | `2026-01-01` | Section 3 | Yes |
| `--output` | `data/vn_liquidity_proxy.csv` | Section 3 | Yes |
| `--max-retries` | `3` | Section 3 | Yes |
| `--retry-backoff-sec` | `5.0` | Section 3 | Yes |

No drift detected. Phase 44 / 45 walk-forward shell-outs can use these flag names with the stability guarantee that 43-01 locked them under D-03.

### Proxy CSV schema (cross-check with 43-01-SUMMARY and live CSV)

6-column schema documented in Section 2.1 matches both the 43-01 SUMMARY header line (`date,usdvnd_close,dxy_close,tnx_close,vnm_close,eem_close`) and the live CSV headers verified via `pd.read_csv` during plan execution:

- rows: 2867
- date range: 2015-01-01 to 2025-12-31
- column order: date, usdvnd_close, dxy_close, tnx_close, vnm_close, eem_close
- tickers: VND=X, DX-Y.NYB, ^TNX, VNM, EEM (all documented in Section 2.1 table)

### SBV CSV schema (cross-check with 43-02-SUMMARY)

5-column schema documented in Section 2.2 matches 43-02-SUMMARY exactly:

- columns: date, rate_change_pct, new_refinance_rate_pct, direction, source
- direction whitelist: {easing, tightening} only — neutral explicitly called out as DERIVED downstream, not stored
- row count: 12 baseline (10 easing + 2 tightening), extensibility path documented
- source citation format: "publication + date + short headline" with Reuters/Vietnam News/SBV/IMF/Vietcombank whitelist

No drift detected.

## Look-Ahead Traps Added Beyond D-09 Minimum

D-09 requires at least 3 traps. The spec documents 5:

- (1-3) — the three D-09-mandated traps: same-day DXY/EEM forbidden, SBV intra-session lag, weekend/holiday bridging correctness. Documented verbatim in Section 6.
- (4) **Added: rolling z-score on raw proxy DataFrame is WRONG.** Rationale: Phase 44's z-score computation is the most subtle place a look-ahead can creep in — the z-score must be computed ON the merged VN30-indexed DataFrame AFTER the backward merge, never on the raw proxy CSV. Without this trap written down, a well-meaning Phase 44 implementer might precompute the z-score in the builder to "save time" and silently reintroduce a future-peek via nearest-US-date mapping.
- (5) **Added: SBV `direction='nearest'` is FORBIDDEN.** Rationale: backward-merge guarantees no look-ahead; `nearest` would match a VN date to a FUTURE SBV event when calendar distance favors the forward side. Documented explicitly so Phase 44 reviewers can grep for this failure mode.

These two extras are belt-and-braces coverage — each addresses a specific failure class that a reviewer should key off during Phase 44 code review.

## Cross-Reference to Research Doc

Footer line at the bottom of the spec:

> See also: `docs/research/liquidity_proxy_correlation.md` for the quick-task research (GO verdict) that motivated this spec.

The research doc itself was NOT modified — it's the research evidence base (GO verdict, correlation table, regime split metrics) and remains frozen. The spec references the research doc as motivation; the research doc does not reference the spec (it predates the spec — acyclic).

## Code-Docs Sync Rule Pointer

Added a standalone line at the bottom of the spec (just above the footer cross-reference):

> Code-Docs Sync: Future Phase 44 work that touches `strategies/mdm_hybrid/` or any new `strategies/mdm_hybrid/macro_filter*.py` module MUST update this spec in the same commit, per the CLAUDE.md Code-Docs Sync Rule.

This extends the existing CLAUDE.md sync pattern (`strategies/mdm_hybrid/` <-> `docs/rules_mdm_hybrid.md`) to the new macro-filter subsystem. Any Phase 44 plan that adds `strategies/mdm_hybrid/macro_filter.py` (or similar) is now on notice that this spec is the docs side of that sync.

## Task Commits

1. **Task 1: Write docs/liquidity_proxy_spec.md with 7 mandatory sections** — `7db0d31` (docs)

Single atomic commit for the single plan task. Commit message: `docs(43-03): write canonical liquidity proxy spec with merge contract and publication-lag policy`.

## Files Created / Modified

- **Created:** `docs/liquidity_proxy_spec.md` (199 lines, UTF-8, LF line endings, no BOM, no emojis, markdown with fenced code blocks tagged `python` / `bash`).
- **Modified:** none.

## Decisions Made

See `key-decisions` frontmatter. Summary of the two non-obvious judgment calls:

- **Spec placement at docs/ (not docs/research/):** The plan's scope fence explicitly forbids placing the spec under `docs/research/` — that directory is for research evidence (correlation reports, GO/NO-GO verdicts, exploratory outputs). This document is a production contract: Phase 44's macro filter reads it as its merge-signature source-of-truth, and any change requires re-running VAL-04 parity. Treating it as a production contract (not a research output) means it lives at `docs/liquidity_proxy_spec.md` alongside `docs/rules_*.md` and `docs/strategy_v7.md`.
- **5 traps rather than the D-09 minimum of 3:** The two extras (rolling-z-score-on-raw-CSV and SBV `direction='nearest'`) were added because both are failure modes that would be easy to miss in a Phase 44 code review if not explicitly enumerated. The `direction='nearest'` trap in particular is pernicious — it would silently match VN dates to future SBV events under certain calendar configurations, and the bug wouldn't show up in simple unit tests that use only past events. Enumerating it explicitly makes it greppable.

## Deviations from Plan

**None — plan executed exactly as written.**

No auto-fixes triggered. All 7 sections written in the specified order with the plan-provided content (section bodies, tables, code blocks) kept verbatim where mandated. Numeric values (DXY corr -0.1909, EEM corr +0.1911, CAGR spread 55.76pp, 2867 proxy rows, 12 SBV rows, publication-lag 22:00/23:00 ICT, 90-day decay) all preserved as specified in the plan.

No emojis used. LF line endings. UTF-8 no-BOM. Markdown code blocks tagged with language (`python` / `bash`).

**Total deviations:** 0
**Impact on plan:** None.

## Issues Encountered

None. Single-pass Write tool call succeeded; automated verify assertions all passed on first run (199 lines >= 80, 20 required tokens present, 5 CLI flags present, 5 numbered look-ahead traps >= 3 minimum).

## Scope Fence Verification

- Commit `7db0d31` touches exactly one file: `docs/liquidity_proxy_spec.md`.
- Zero modifications to tracked files (verified via `git status --short` filtering for non-`??` lines — empty).
- `docs/research/liquidity_proxy_correlation.md` unchanged (`git diff HEAD -- docs/research/liquidity_proxy_correlation.md` returns empty).
- `data/vn_liquidity_proxy.csv` unchanged (not in commit; not modified).
- `data/sbv_policy_events.csv` unchanged (not in commit; not modified).
- Zero touches under `strategies/`, `models/`, `vn30_vsa/`, `tests/`, `analysis/` — pure doc addition.

## Next Phase Readiness

Phase 43 is now complete (LIQ-01 + LIQ-02 + LIQ-03 all closed). Phase 44 MacroFilter (MACRO-01..05) is unblocked and can:

1. Read `docs/liquidity_proxy_spec.md` Section 5 (Merge Contract) and copy the two Python code blocks verbatim into its MACRO-01 and MACRO-03 merge steps.
2. Read Section 4 (Publication-Lag Policy) to justify every merge choice in code review.
3. Read Section 6 (Look-Ahead Traps Ruled Out) as its own pre-implementation review checklist — each trap is a falsifiable invariant Phase 44's tests should assert.
4. Trust that both CSV schemas are frozen — column names, dtypes, row counts, and direction whitelists will not drift under Phase 43; any future change requires a new Phase 43-Nth plan that updates this spec in the same commit.

## Known Stubs

None. The spec is complete prose with no TODO / placeholder markers. All numeric values, code blocks, and cross-references are concrete.

## Self-Check

Artifacts:
- `docs/liquidity_proxy_spec.md` — FOUND (199 lines, UTF-8, all 7 required sections present, 10 merge_asof mentions, 11 direction='backward' mentions, 5 numbered look-ahead traps, all 5 CLI flags documented)
- `docs/research/liquidity_proxy_correlation.md` — UNCHANGED (no diff, no status flag)
- `data/vn_liquidity_proxy.csv` — UNCHANGED (not in commit)
- `data/sbv_policy_events.csv` — UNCHANGED (not in commit)

Commits:
- `7db0d31` (Task 1) — FOUND in git log

**Self-Check: PASSED**

---
*Phase: 43-canonical-liquidity-data-pipeline*
*Plan: 03*
*Completed: 2026-04-22*
