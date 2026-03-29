# Phase 7: Data Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 07-data-foundation
**Areas discussed:** Signal loader scope, Early data quality, Date alignment strategy, Validation depth

---

## Signal Loader Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing loader | Add dollar_becomes as optional column in load_signal_fixture(). Backward-compatible. | ✓ |
| New dedicated function | Create load_full_signal_history() specifically for 962-signal CSV. | |
| Ignore dollar_becomes | Don't parse it now. Phase 10 can add when needed. | |

**User's choice:** Extend existing loader (Recommended)
**Notes:** Keeps backward compatibility with existing 3-column CSVs while supporting the full 4-column format.

---

## Early Data Quality

| Option | Description | Selected |
|--------|-------------|----------|
| Pass through as-is | Load all data from 1973+, don't filter or flag. Indicators use close price which is valid. | ✓ |
| Trim to first signal date | Start from 1974-07-17. Earlier data has no ground truth. | |
| Flag quality in metadata | Add data_quality column marking rows with 0 volume or identical OHLC. | |

**User's choice:** Pass through as-is (Recommended)
**Notes:** Phase 8 indicators (EMA, MA, MACD) only need close prices, which are valid even in earliest data.

---

## Date Alignment Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and report gaps | Log mismatched dates, output gap report. Phase 8 decides how to handle. | ✓ |
| Snap to nearest trading day | Auto-align signals to closest OHLCV date. Risk: off-by-one errors. | |
| Fail hard on any mismatch | Raise error if any signal date missing. May block on 50-year gaps. | |

**User's choice:** Warn and report gaps (Recommended)
**Notes:** Don't block progress. Let Phase 8 decide alignment during feature snapshot extraction.

---

## Validation Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Add a few era checks | Add 2-3 spot-checks from ~1974, ~2000, ~2008. Covers 4+ decades total. | ✓ |
| Keep existing only | 2020-2021 checks confirm normalization works. Same scaling for all data. | |
| Full era coverage | 5+ checks per decade. Maximum confidence but hard to find references. | |

**User's choice:** Add a few era checks (Recommended)
**Notes:** Combined with existing 2020-2021 checks, validates normalization across 4+ decades.

---

## Claude's Discretion

- Exact reference dates/values for historical spot-checks
- Gap report format
- Convenience function for full signal history loading
- Test structure

## Deferred Ideas

None -- discussion stayed within phase scope
