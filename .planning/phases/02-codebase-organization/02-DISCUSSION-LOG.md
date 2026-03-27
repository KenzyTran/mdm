# Phase 2: Codebase Organization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 02-codebase-organization
**Areas discussed:** Shared vs strategy code, Entry point handling, Migration approach, Regression testing

---

## Shared vs strategy code

### How should duplicated modules be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep separate | Each strategy keeps its own versions. Only truly shared infra goes to core/. Avoids forced abstractions. | ✓ |
| Extract common base | Create base classes in core/ that each strategy extends. More DRY but adds abstraction. | |
| Merge where possible | Combine into single core/ modules with strategy-specific parameters. Maximum sharing, tighter coupling. | |

**User's choice:** Keep separate
**Notes:** None

### What belongs in core/?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: loader + types only | core/ contains unified DataLoader, shared types (MarketState, Position/Trade), signal fixture loader. | ✓ |
| Loader + types + config base | Also add BaseConfig dataclass to core/. | |
| You decide | Claude determines during implementation. | |

**User's choice:** Minimal: loader + types only
**Notes:** None

### What happens to old directories?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete after verified | Remove old directories once regression tests pass. Git history preserves originals. | ✓ |
| Keep as archive | Rename to _archive_* directories. | |
| Git handles it | Delete — git history is the archive. | |

**User's choice:** Delete after verified
**Notes:** None

---

## Entry point handling

### Where should backtest/optimization scripts live?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep at root | Entry points stay at project root, update imports. | |
| Move to scripts/ | Create scripts/ directory for all entry points. | ✓ |
| Move into strategies | Each strategy gets its own runner. | |

**User's choice:** Move to scripts/
**Notes:** None

### What about analysis scripts and notebooks?

| Option | Description | Selected |
|--------|-------------|----------|
| All to analysis/ | Move analyze_*.py and diagnose_vn30.py to analysis/. Notebooks stay at root. | ✓ |
| Scripts + notebooks to analysis/ | Move everything including notebooks. | |
| You decide | Claude places them where appropriate. | |

**User's choice:** All to analysis/
**Notes:** None

---

## Migration approach

### How should import paths be migrated?

| Option | Description | Selected |
|--------|-------------|----------|
| Clean break | Update all imports in one pass. Old paths stop working. No shims. | ✓ |
| Compatibility shims | Old directories re-export from new locations. Gradual migration. | |
| Incremental per-strategy | Migrate MDM first, verify, then VSA. Two passes. | |

**User's choice:** Clean break
**Notes:** None

### Should strategies/ be a package or directory of packages?

| Option | Description | Selected |
|--------|-------------|----------|
| Directory of packages | strategies/ is a folder. Each strategy is its own package. Import: from strategies.mdm_classic import MDMEngine | ✓ |
| Namespace package | strategies/ is a package with __init__.py that exports from sub-packages. | |

**User's choice:** Directory of packages
**Notes:** None

---

## Regression testing

### What test framework?

| Option | Description | Selected |
|--------|-------------|----------|
| pytest | Standard Python test framework. Sets up infrastructure for future phases. | ✓ |
| Simple script | Standalone comparison script. No framework dependency. | |
| You decide | Claude picks during implementation. | |

**User's choice:** pytest
**Notes:** None

### What should regression tests compare?

| Option | Description | Selected |
|--------|-------------|----------|
| Signals + equity curve | Full signal sequence and equity values. Exact signal match, floating-point tolerance for equity. | ✓ |
| Full DataFrame match | Entire output DataFrames column by column. | |
| Trade list only | Final trade list (entry/exit, P&L). | |

**User's choice:** Signals + equity curve
**Notes:** None

### Where should golden baselines be stored?

| Option | Description | Selected |
|--------|-------------|----------|
| tests/fixtures/ | Golden output CSVs generated from old code before migration. | ✓ |
| Generate on the fly | Run old and new code in same test, compare live. | |
| You decide | Claude determines during implementation. | |

**User's choice:** tests/fixtures/
**Notes:** None

---

## Claude's Discretion

- Exact file/module naming within strategy directories
- Which types/enums are truly shared vs strategy-specific
- Internal organization of core/
- pytest configuration details

## Deferred Ideas

None — discussion stayed within phase scope
