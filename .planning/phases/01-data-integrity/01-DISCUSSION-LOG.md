# Phase 1: Data Integrity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 01-data-integrity
**Areas discussed:** Normalization approach, Unified loader design, Signal fixture format, Validation spot-checks

---

## Normalization approach

| Option | Description | Selected |
|--------|-------------|----------|
| Static divide by 1000 | Simple and predictable. Known consistent scaling factor. | ✓ |
| Dynamic detection | Auto-detect scaling by comparing magnitude to expected ranges. More robust but adds complexity. | |
| Per-market config | Define scaling factor per market in config dict. Middle ground. | |

**User's choice:** Static divide by 1000
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Prices only | Volume values (~6.5B) look reasonable. Only OHLC needs 1000x correction. | ✓ |
| Prices and volume | Normalize both, even if volume looks correct. | |

**User's choice:** Prices only
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| US markets only | VN30 already at native scale. Normalization is a US data fix. | ✓ |
| All markets, no-op for VN30 | Uniform code path with scale=1 for VN30. | |

**User's choice:** US markets only
**Notes:** None

---

## Unified loader design

| Option | Description | Selected |
|--------|-------------|----------|
| Single class, market param | One DataLoader class accepting market type. Consistent interface. | ✓ |
| Factory function per market | Separate load_nasdaq(), load_sp500(), load_vn30() functions. Simpler. | |
| Config-driven loader | Generic function + config dict per market. Extensible. | |

**User's choice:** Single class, market param
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| date, open, high, low, close, volume | Matches existing MDM loader. Standard in trading libraries. | ✓ |
| date, open, high, low, close, volume, symbol | Same but always includes symbol column. | |

**User's choice:** date, open, high, low, close, volume
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| New module, keep old loaders | Create new unified loader. Old loaders untouched for Phase 2 migration. | ✓ |
| Replace existing loaders now | Update models/data_loader.py to be unified. Risk of breaking existing scripts. | |

**User's choice:** New module, keep old loaders
**Notes:** None

---

## Signal fixture format

| Option | Description | Selected |
|--------|-------------|----------|
| Already have it in a file | Signal data exists somewhere in the project | |
| Need to manually enter it | Signal history typed in from website | ✓ |
| You decide | Claude figures out best approach | |

**User's choice:** Need to manually enter it
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| CSV files | Simple CSV with date, signal, gain_loss_pct. Easy to edit and version control. | ✓ |
| Python dict/list in .py file | Embedded in Python module. Type-safe but harder to bulk edit. | |
| JSON file | Machine-readable, supports nesting, less convenient for manual entry. | |

**User's choice:** CSV files
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Both TECL and NASDAQ | Both mentioned in PROJECT.md. Enables richer analysis. | ✓ |
| NASDAQ only | Primary MDM target. TECL is leveraged exposure of same signals. | |

**User's choice:** Both TECL and NASDAQ
**Notes:** None

---

## Validation spot-checks

| Option | Description | Selected |
|--------|-------------|----------|
| Assert and halt | Raise error if spot-check fails (>0.1% off). Bad data blocks downstream work. | ✓ |
| Warn and continue | Log warning but don't stop. Allows partial investigation. | |
| Report only | Generate pass/fail report for user review. No blocking. | |

**User's choice:** Assert and halt
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded known dates | Pick 3-5 well-known dates per market with expected close prices. Deterministic. | ✓ |
| External API cross-reference | Fetch from free API at validation time. More thorough but adds dependency. | |
| You decide | Claude picks appropriate dates and values. | |

**User's choice:** Hardcoded known dates
**Notes:** None

---

## Claude's Discretion

- Exact reference dates and values for spot-checks
- Internal column mapping dictionaries per market type
- CSV parsing details
- Signal fixture file location within data/ directory

## Deferred Ideas

None — discussion stayed within phase scope
