# Phase 2: Codebase Organization - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize existing code into a three-layer architecture: `core/` (shared infrastructure), `strategies/` (signal logic per strategy), `analysis/` (post-backtest tools). Both MDM classic and VSA strategies must produce identical backtest output after migration. This phase does NOT add new capabilities, modify trading logic, or analyze signals (Phase 3).

</domain>

<decisions>
## Implementation Decisions

### Shared vs strategy-specific code
- **D-01:** Each strategy keeps its own versions of indicators.py, performance.py, stop_loss.py, data_loader.py under `strategies/mdm_classic/` and `strategies/vsa/`. No forced abstractions or base classes.
- **D-02:** `core/` contains only truly shared infrastructure: the unified DataLoader (from Phase 1), shared types (MarketState enum, Position/Trade dataclasses), and the signal fixture loader. Strategies import from core/ but own everything else.
- **D-03:** Old `models/` and `vn30_vsa/` directories are deleted after regression tests confirm identical output. Git history preserves the originals.

### Entry point handling
- **D-04:** Backtest and optimization scripts (`run_backtest.py`, `optimize_mdm.py`) move to `scripts/` directory. Imports updated to point to `strategies/`.
- **D-05:** Analysis scripts (`analyze_drawdown.py`, `analyze_vsa_drawdown.py`, `analysis/diagnose_vn30.py`) move to `analysis/`. Notebooks stay at project root (Jupyter expects them there).
- **D-06:** `check_date.py` utility moves to `scripts/` alongside other entry points.

### Migration approach
- **D-07:** Clean break — all imports updated in one pass, old paths stop working immediately. No compatibility shims. This is a research project with no external consumers.
- **D-08:** `strategies/` is a directory of packages, not a namespace package. Each strategy (`strategies/mdm_classic/`, `strategies/vsa/`) is its own package with `__init__.py`. Import pattern: `from strategies.mdm_classic import MDMEngine`.

### Regression testing
- **D-09:** Use pytest as the test framework. Sets up test infrastructure for future phases.
- **D-10:** Regression tests compare signal sequences (date + signal type) and equity curve values. Signals must match exactly; equity values within floating-point tolerance (~1e-10).
- **D-11:** Golden baseline files stored in `tests/fixtures/`. Baselines generated once from old code before migration, then compared against migrated code.

### Claude's Discretion
- Exact file/module naming within strategy directories (follow existing conventions)
- Which types/enums are truly shared vs strategy-specific (determine by reading actual code during implementation)
- Internal organization of `core/` (flat vs sub-packages)
- pytest configuration details (conftest.py structure, marker usage)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing strategy implementations (migration sources)
- `models/__init__.py` — MDM public API exports, shows what classes are exposed
- `models/mdm_engine.py` — MDM orchestration engine, primary integration point
- `models/config.py` — MDMConfig dataclass with parameter validation
- `models/position_manager.py` — Position state machine (CASH/HOLDING/WAITING_SELL/SHORT)
- `vn30_vsa/__init__.py` — VSA public API exports
- `vn30_vsa/vsa_engine.py` — VSA orchestration engine, multi-stock portfolio
- `vn30_vsa/config.py` — VSA module-level configuration constants

### Phase 1 shared infrastructure (already in core/)
- `core/data_loader.py` — Unified DataLoader from Phase 1 (D-06 in Phase 1 context)
- `data/signals/` — Signal fixture CSVs from Phase 1

### Entry points (to be migrated)
- `run_backtest.py` — MDM backtest runner
- `optimize_mdm.py` — Parameter grid search
- `analyze_drawdown.py` — MDM drawdown analysis
- `analyze_vsa_drawdown.py` — VSA drawdown analysis
- `analysis/diagnose_vn30.py` — VN30 diagnostic analysis

### Requirements
- `.planning/REQUIREMENTS.md` — ORG-01 through ORG-04 define acceptance criteria

### Codebase analysis
- `.planning/codebase/ARCHITECTURE.md` — Current layered architecture documentation
- `.planning/codebase/STRUCTURE.md` — Current directory layout and file purposes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/data_loader.py`: Unified DataLoader already established in Phase 1 — anchor point for core/ directory
- `models/__init__.py`: Shows import pattern for MDM public API — replicate in `strategies/mdm_classic/__init__.py`
- `vn30_vsa/__init__.py`: Shows import pattern for VSA public API — replicate in `strategies/vsa/__init__.py`

### Established Patterns
- Both strategies follow identical module structure: data_loader, indicators, signals/ftd_signal, position_manager, stop_loss, engine, performance, config
- Relative imports within packages (`from .data_loader import DataLoader`) — maintain this pattern in new locations
- MDMConfig uses dataclass with `__post_init__` validation; VSA uses module-level constants — both patterns kept as-is

### Integration Points
- `run_backtest.py` imports from `models` — must update to `strategies.mdm_classic`
- `optimize_mdm.py` imports `MDMConfig` and `MDMEngine` from `models` — must update
- Notebooks import from `models` and `vn30_vsa` — must update import cells
- `analysis/diagnose_vn30.py` imports from `vn30_vsa` — must update to `strategies.vsa`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-codebase-organization*
*Context gathered: 2026-03-27*
