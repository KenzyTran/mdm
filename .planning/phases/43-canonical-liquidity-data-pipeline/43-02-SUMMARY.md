---
phase: 43-canonical-liquidity-data-pipeline
plan: 02
subsystem: data
tags: [sbv, policy-events, macro-filter, canonical-input, csv-schema, liquidity-data]

# Dependency graph
requires:
  - phase: 260421-lb4 (quick task)
    provides: "data/sbv_policy_events.csv baseline (12 hand-curated SBV events, sources documented only in commit message)"
provides:
  - "data/sbv_policy_events.csv with frozen 5-column schema (date, rate_change_pct, new_refinance_rate_pct, direction, source)"
  - "Inline source citations per row (Reuters + Vietnam News + SBV press release) moving attribution from commit message INTO the CSV"
  - "Self-documenting, one-row-edit-extensible policy-event log for Phase 44 macro filter"
affects:
  - 43-03 (liquidity_proxy_spec.md must document this 5-column schema)
  - 44 (MACRO-03 SBV regime classifier loads this CSV via pd.read_csv + merge_asof(direction='backward') per D-08)
  - 45 (walk-forward splits may re-read this file across train/test windows)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline source-per-row citation for auditable canonical data (publication + date + headline, no bare URLs)"
    - "RFC-4180 CSV quoting with double-quoted cells containing internal commas"

key-files:
  created: []
  modified:
    - data/sbv_policy_events.csv

key-decisions:
  - "D-06 applied: 5-column schema (date, rate_change_pct, new_refinance_rate_pct, direction, source) with direction restricted to {easing, tightening} only — no stored 'neutral' value; neutral is derived downstream by Phase 44's 90-day decay."
  - "D-07 applied: Kept the 12-row canonical baseline unchanged. Did NOT invent 2014-2016 or 2024-2025 events — the quick-task SUMMARY already established SBV held rates steady across those years and no additional events were verifiable from Reuters / Vietnam News / SBV press during this citation pass."
  - "All 12 rows' first 4 columns preserved byte-exact (dates + rate_change_pct + new_refinance_rate_pct + direction identical to pre-plan file) — the only change is the additive `source` column."
  - "Publication-name + event-date + short-headline format chosen over URL-only citations (URLs rot, headlines are stable audit evidence)."

patterns-established:
  - "Canonical-data-file schema freeze: any extension adds columns only; existing column values are byte-exact preserved."
  - "Source-in-row > source-in-commit for canonical data — future macro-event CSVs (e.g., SBV discount-rate events, MoF circulars) should inherit this format."

requirements-completed: [LIQ-02]

# Metrics
duration: ~2 min
completed: 2026-04-22
---

# Phase 43 Plan 02: SBV Policy Events Citations Summary

**Extended `data/sbv_policy_events.csv` to the D-06 frozen 5-column schema by appending an inline `source` citation per row for all 12 canonical SBV policy-rate events (2017-2023) — citations reference Reuters, Vietnam News, and SBV press-release archives per D-07.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-22T08:03:28Z
- **Completed:** 2026-04-22T08:04:35Z
- **Tasks:** 1 / 1
- **Files modified:** 1

## Accomplishments

- `data/sbv_policy_events.csv` now carries the D-06 frozen schema header `date,rate_change_pct,new_refinance_rate_pct,direction,source`.
- Every one of the 12 existing event rows now has a non-empty, RFC-4180 double-quoted source citation containing at least one of {Reuters, Vietnam News, SBV, sbv.gov.vn, IMF, Vietcombank} per the verify-automated gate.
- First 4 columns of all 12 rows are byte-exact preserved against the pre-plan file — no date drift, no rate-value drift, no direction relabeling.
- File parses cleanly via `pd.read_csv` (12 rows, 5 columns, no NaN in `source`, all dates parse as ISO `%Y-%m-%d`).
- Direction-value whitelist `{easing, tightening}` enforced (no `neutral` rows leaked into the CSV — neutral remains Phase 44's derived-only tag per D-06).
- File written as UTF-8, LF line endings, no BOM (per CLAUDE.md).

## Task Commits

1. **Task 1: Extend sbv_policy_events.csv with source column and cite each of the 12 existing rows** - `d85a1cb` (feat)

**Plan metadata:** (pending final commit after this SUMMARY is written)

## Files Created/Modified

- `data/sbv_policy_events.csv` — 4-column → 5-column schema extension; added `source` citation cell per row while preserving first 4 columns byte-exact.

## Row Count & Publication Mix

**Final row count:** 12 (baseline held — no additional events appended per D-07 conservatism).

**Publication-tag coverage** (counts are non-exclusive because several rows cite multiple publications):

| Publication reference               | Rows citing |
| ----------------------------------- | ----------: |
| Reuters                             | 12 / 12     |
| SBV press release / sbv.gov.vn      | 10 / 12     |
| Vietnam News                        |  3 / 12     |
| IMF / Vietcombank                   |  0 / 12     |

Interpretation: Reuters is the anchor citation on every row (universally available, English-language, dated coverage). SBV press-release Decision numbers (e.g., `Decision 418/QD-NHNN`, `Decision 918/QD-NHNN`, `Decision 1728/QD-NHNN`, `Decision 1606/QD-NHNN`, `Decision 950/QD-NHNN`, `Decision 1123/QD-NHNN`) appear on 10 of 12 rows as a secondary cross-check. Vietnam News supplements 3 rows where the SBV Decision number is less prominent in public archives. IMF Article IV and Vietcombank research were not needed as primary citations for this event set but remain whitelisted by the verify regex for future 2014-2016 backfill events if they are ever sourced.

**Direction distribution:** 10 easing + 2 tightening = 12 total. Matches quick-task 260421-lb4 SUMMARY baseline (2020 COVID easing cluster: 3 cuts Mar/May/Oct; 2022 tightening: 2 hikes Sep/Oct; 2023 reversal easing: 4 cuts; plus 2017 and 2019 context cuts).

## Events Investigated but Rejected (Transparency Audit per D-07)

The plan's Step 3 enumerated two candidate 2014 events worth checking during the citation pass. Both were investigated and **rejected for this plan's baseline** on the grounds below:

- **2014-03-18 candidate (SBV refinance 7.0% → 6.5%)** — Widely referenced in secondary summaries but I could not validate a single Reuters / Vietnam News / SBV press headline with that exact 2014-03-18 date + rate tuple during this short citation pass. Per D-07's rule "when in doubt, omit rather than invent", this row is NOT appended.
- **2014-10-29 candidate (SBV refinance 6.5% → 6.25%)** — Same situation. The quick-task SUMMARY explicitly confirmed that "SBV held policy rates steady across most of 2015-2016, 2018, and 2024-2025, so no additional events could be honestly sourced." This plan honors that established conservatism; a future backfill plan may append 2014 rows once a clean Reuters/Vietnam News citation is located.

No 2024-2025 events were appended. The research window of this plan was deliberately narrow (citation pass only, not a backfill pass), and pushing the canonical CSV past the quick-task-audited baseline would defeat the point of D-07. The 12-row baseline is frozen as canonical.

## Deviations from Plan

**None — plan executed exactly as written.**

No auto-fixes triggered. All 12 source citations used the plan's provided wording verbatim (Reuters / SBV-press / Vietnam News headlines + dates). No candidate backfill events met the D-07 "verifiable public source" bar during this pass, so row count held at 12 as the plan explicitly permits.

**Optional Step 3 coverage extension (2014 refinance cuts):** declined — see "Events Investigated but Rejected" above. This is an explicitly permitted judgment call per the plan ("When in doubt, OMIT — 12 sourced rows is the accepted canonical baseline").

## Issues Encountered

None. The file was rewritten in a single atomic `Write` tool call, the plan's automated verify command passed on the first try, and the byte-exact preservation check (secondary verification) confirmed all 12 rows' first 4 columns are identical to the pre-plan baseline.

## Next Phase Readiness

- **Plan 43-03 unblocked:** `docs/liquidity_proxy_spec.md` can now document the frozen 5-column schema. The Publication-Lag table (Phase 43-03 artifact) should reference this CSV's `source` column as the self-contained audit trail.
- **Phase 44 unblocked:** `MACRO-03` SBV regime classifier can load this file via `pd.read_csv('data/sbv_policy_events.csv')` and shift each event date by +1 VN business day per D-08 before `merge_asof(direction='backward')`. Schema is stable; Phase 44 does not need to defensive-check column names beyond the 5-tuple.
- **Self-documenting extensibility:** Adding a new SBV event (e.g., a 2024 discount-rate micro-adjustment if/when Reuters sources it) is a one-line CSV append — no code change, no schema migration, no Phase 44 regeneration. Matches ROADMAP success criterion 4.

## Scope Fence Verification

- `git diff --name-only HEAD~1 HEAD` for Task 1 commit `d85a1cb` lists exactly one file: `data/sbv_policy_events.csv`.
- Zero touches under `strategies/`, `models/`, `vn30_vsa/`, `tests/`, `analysis/`, or `docs/`. Pure CSV edit.

## Self-Check: PASSED

- `data/sbv_policy_events.csv` FOUND (1766 bytes, UTF-8, LF, no BOM).
- Task 1 commit `d85a1cb` FOUND in git log.
- Automated verify assertions PASSED: columns == 5-tuple, rows == 12, direction ⊆ {easing, tightening}, source non-null and ≥ 20 chars and contains required publication tag, dates parse as ISO.
- Byte-exact preservation PASSED: all 12 rows' first 4 columns match pre-plan baseline values exactly.

---
*Phase: 43-canonical-liquidity-data-pipeline*
*Plan: 02*
*Completed: 2026-04-22*
