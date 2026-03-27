# Phase 2: Codebase Organization - Research

**Researched:** 2026-03-27
**Domain:** Python package restructuring, regression testing
**Confidence:** HIGH

## Summary

This phase reorganizes existing code into a three-layer architecture (`core/`, `strategies/`, `analysis/`) with zero regression in backtest output. The codebase is well-suited for this: the two strategies (`models/` for MDM, `vn30_vsa/` for VSA) are fully independent with zero cross-imports, both use internal relative imports exclusively, and `core/` already exists from Phase 1 with the unified DataLoader.

The primary risk is subtle behavioral divergence during migration. Both strategies produce deterministic numerical output (signal sequences, equity curves, trade lists) that can be captured as golden baselines before migration and compared after. pytest 9.0.2 is already installed and has existing tests in `tests/`.

**Primary recommendation:** Generate golden baseline CSVs from the old code first, then move files, update imports, and verify baselines match exactly. No code logic should change -- this is purely a file reorganization with import path updates.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Each strategy keeps its own versions of indicators.py, performance.py, stop_loss.py, data_loader.py under `strategies/mdm_classic/` and `strategies/vsa/`. No forced abstractions or base classes.
- **D-02:** `core/` contains only truly shared infrastructure: the unified DataLoader (from Phase 1), shared types (MarketState enum, Position/Trade dataclasses), and the signal fixture loader. Strategies import from core/ but own everything else.
- **D-03:** Old `models/` and `vn30_vsa/` directories are deleted after regression tests confirm identical output. Git history preserves the originals.
- **D-04:** Backtest and optimization scripts (`run_backtest.py`, `optimize_mdm.py`) move to `scripts/` directory. Imports updated to point to `strategies/`.
- **D-05:** Analysis scripts (`analyze_drawdown.py`, `analyze_vsa_drawdown.py`, `analysis/diagnose_vn30.py`) move to `analysis/`. Notebooks stay at project root (Jupyter expects them there).
- **D-06:** `check_date.py` utility moves to `scripts/` alongside other entry points.
- **D-07:** Clean break -- all imports updated in one pass, old paths stop working immediately. No compatibility shims. This is a research project with no external consumers.
- **D-08:** `strategies/` is a directory of packages, not a namespace package. Each strategy (`strategies/mdm_classic/`, `strategies/vsa/`) is its own package with `__init__.py`. Import pattern: `from strategies.mdm_classic import MDMEngine`.
- **D-09:** Use pytest as the test framework. Sets up test infrastructure for future phases.
- **D-10:** Regression tests compare signal sequences (date + signal type) and equity curve values. Signals must match exactly; equity values within floating-point tolerance (~1e-10).
- **D-11:** Golden baseline files stored in `tests/fixtures/`. Baselines generated once from old code before migration, then compared against migrated code.

### Claude's Discretion
- Exact file/module naming within strategy directories (follow existing conventions)
- Which types/enums are truly shared vs strategy-specific (determine by reading actual code during implementation)
- Internal organization of `core/` (flat vs sub-packages)
- pytest configuration details (conftest.py structure, marker usage)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORG-01 | Three-layer architecture implemented (core/ shared infrastructure, strategies/ signal logic, analysis/ tools) | Directory structure pattern documented; file inventory complete; import patterns verified |
| ORG-02 | Existing MDM classic migrated from models/ to strategies/mdm_classic/ | MDM has 11 files, all use relative imports (`from .module import X`); MDMEngine is the orchestrator; no external dependencies beyond pandas/numpy |
| ORG-03 | Existing VSA migrated from vn30_vsa/ to strategies/vsa/ | VSA has 11 files, all use relative imports; VSAEngine is the orchestrator; fully independent from MDM (zero cross-imports) |
| ORG-04 | Backtest output identical before and after migration (regression test) | Golden baseline approach documented; MDM output is a DataFrame with signal columns + trade list; VSA output is NAV DataFrame + trade list; pytest fixtures pattern established |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test framework | Already installed as dev dependency; D-09 locked decision |
| pandas | >= 2.0.0 | DataFrame comparison for regression tests | Already in project; `pd.testing.assert_frame_equal` for exact comparison |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | >= 1.24.0 | Floating-point tolerance in comparisons | `np.testing.assert_allclose` for equity values within ~1e-10 tolerance |

No new packages needed. This phase uses only what is already installed.

## Architecture Patterns

### Target Project Structure
```
mdm/
├── core/                          # Shared infrastructure (Phase 1 + new shared types)
│   ├── __init__.py                # Export shared types
│   ├── data_loader.py             # Unified DataLoader (from Phase 1)
│   └── signal_loader.py           # Signal fixture loader (from Phase 1)
├── strategies/                    # Strategy packages
│   ├── __init__.py                # Empty or minimal
│   ├── mdm_classic/               # MDM strategy (from models/)
│   │   ├── __init__.py            # Public API exports (mirrors current models/__init__.py)
│   │   ├── config.py
│   │   ├── data_loader.py         # MDM's own DataLoader (kept per D-01)
│   │   ├── distribution_day.py
│   │   ├── ftd_signal.py
│   │   ├── indicators.py
│   │   ├── mdm_engine.py
│   │   ├── performance.py
│   │   ├── position_manager.py    # Contains MarketState, Position, PositionManager
│   │   ├── rally_attempt.py
│   │   └── stop_loss.py
│   └── vsa/                       # VSA strategy (from vn30_vsa/)
│       ├── __init__.py            # Public API exports (mirrors current vn30_vsa/__init__.py)
│       ├── config.py
│       ├── data_loader.py         # VSA's own data_loader (kept per D-01)
│       ├── indicators.py
│       ├── kelly.py
│       ├── performance.py
│       ├── position_manager.py    # VSA's own Position class (completely different from MDM's)
│       ├── signals.py
│       ├── stop_loss.py
│       ├── trailing_stop.py
│       └── vsa_engine.py
├── analysis/                      # Analysis tools
│   ├── __init__.py
│   ├── analyze_drawdown.py        # From root analyze_drawdown.py
│   ├── analyze_vsa_drawdown.py    # From root analyze_vsa_drawdown.py
│   └── diagnose_vn30.py           # From analysis/diagnose_vn30.py (already here)
├── scripts/                       # Entry point scripts
│   ├── run_backtest.py            # From root run_backtest.py
│   ├── optimize_mdm.py            # From root optimize_mdm.py
│   └── check_date.py              # From root check_date.py
├── tests/                         # Test suite
│   ├── __init__.py                # Already exists
│   ├── fixtures/                  # Golden baseline files (D-11)
│   │   ├── mdm_signals_baseline.csv
│   │   ├── mdm_trades_baseline.csv
│   │   ├── vsa_nav_baseline.csv
│   │   └── vsa_trades_baseline.csv
│   ├── test_data_loader.py        # Already exists (Phase 1)
│   ├── test_signal_fixtures.py    # Already exists (Phase 1)
│   ├── test_mdm_regression.py     # New: MDM regression test
│   └── test_vsa_regression.py     # New: VSA regression test
├── data/                          # Data files (unchanged)
├── *.ipynb                        # Notebooks stay at root (D-05)
└── pyproject.toml
```

### Pattern 1: Golden Baseline Regression Testing
**What:** Generate deterministic output from old code, save as CSV fixtures, then verify migrated code produces identical output.
**When to use:** Any code reorganization where behavior must not change.
**Example:**
```python
# Generate baseline (run ONCE before migration, from old code):
from models import MDMEngine, DataLoader
loader = DataLoader('vnindex_price.csv')
df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
engine = MDMEngine()
results = engine.run(df)

# Save signal sequence
signals = results[results['action'] != ''][['date', 'close', 'state', 'action']].copy()
signals.to_csv('tests/fixtures/mdm_signals_baseline.csv', index=False)

# Save trade list
trades_df = engine.get_trade_df()
trades_df.to_csv('tests/fixtures/mdm_trades_baseline.csv', index=False)
```

```python
# Regression test (run AFTER migration):
import pandas as pd
import numpy as np
from strategies.mdm_classic import MDMEngine
from strategies.mdm_classic.data_loader import DataLoader

def test_mdm_signals_match_baseline():
    loader = DataLoader('vnindex_price.csv')
    df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
    engine = MDMEngine()
    results = engine.run(df)

    signals = results[results['action'] != ''][['date', 'close', 'state', 'action']].copy()
    baseline = pd.read_csv('tests/fixtures/mdm_signals_baseline.csv', parse_dates=['date'])

    pd.testing.assert_frame_equal(signals.reset_index(drop=True), baseline)

def test_mdm_trades_match_baseline():
    # Similar pattern with trade list comparison
    # Use np.testing.assert_allclose for float columns (pnl) with atol=1e-10
    pass
```

### Pattern 2: File Move with Import Update
**What:** Copy files to new location, update all relative imports (which stay the same since package structure is preserved), update absolute imports in entry points and notebooks.
**When to use:** All strategy files -- they already use `from .module import X` relative imports which work unchanged after moving.

### Key Insight: Relative Imports Need No Changes
Both `models/` and `vn30_vsa/` use relative imports internally (e.g., `from .data_loader import DataLoader`, `from .config import MDMConfig`). When these files move to `strategies/mdm_classic/` and `strategies/vsa/`, the relative imports remain valid because the internal package structure is preserved. Only the external consumers (scripts, notebooks, analysis tools) need import path updates.

### Anti-Patterns to Avoid
- **Shared abstractions too early:** D-01 explicitly forbids forced abstractions. Do NOT create base classes for Position, PositionManager, etc. MDM's `Position` (6 fields, enum-based state) is fundamentally different from VSA's `Position` (stock-specific, tracks MA10 violations). They should NOT share a base class.
- **Namespace packages:** D-08 explicitly requires regular packages with `__init__.py`, not PEP 420 namespace packages.
- **Partial migration:** D-07 requires a clean break. Do NOT leave compatibility shims like `models/__init__.py` that re-exports from `strategies/`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DataFrame comparison | Custom column-by-column checks | `pd.testing.assert_frame_equal` | Handles dtypes, NaN, index alignment |
| Float comparison | Manual epsilon checks | `np.testing.assert_allclose(atol=1e-10)` | Proper relative/absolute tolerance |
| CSV baseline storage | Pickle or JSON | CSV with `pd.read_csv(parse_dates=[...])` | Human-readable, diff-friendly in git |

## Common Pitfalls

### Pitfall 1: MDMEngine Uses Its Own DataLoader
**What goes wrong:** Assuming MDMEngine should use `core.data_loader.DataLoader` after migration.
**Why it happens:** `core/data_loader.py` is the Phase 1 unified loader. But `models/data_loader.py` is the MDM-specific loader with different column mappings and a different API (`DataLoader(filepath)` vs `DataLoader('market_name')`). MDMEngine internally creates `self.data_loader = DataLoader()` from its own module.
**How to avoid:** Per D-01, each strategy keeps its own data_loader. `strategies/mdm_classic/data_loader.py` stays separate from `core/data_loader.py`.
**Warning signs:** Import errors when MDMEngine tries to instantiate DataLoader.

### Pitfall 2: VSA Engine Loads Data Differently
**What goes wrong:** Assuming VSA and MDM have the same data loading pattern.
**Why it happens:** MDM's `engine.run(df)` takes a pre-loaded DataFrame. VSA's `engine.load_data(filepath)` then `engine.run()` loads internally. The regression test must follow each strategy's native pattern.
**How to avoid:** Study each engine's API before writing tests. MDM: `DataLoader -> df -> engine.run(df)`. VSA: `engine.load_data(filepath) -> engine.run()`.

### Pitfall 3: VSA Data File Not in data/ Directory
**What goes wrong:** VSA references `VN30_STOCKS_PRICE.csv` which is NOT in `data/` -- it was at the project root and has been deleted (git status shows `D VN30_STOCKS_PRICE.csv`).
**Why it happens:** The VSA data file was a large CSV at the root that was gitignored or removed.
**How to avoid:** VSA regression tests need the data file to exist. Check if `vn30_price.csv` (which does exist at root) is usable, or if VSA specifically needs the multi-stock `VN30_STOCKS_PRICE.csv`. If the latter is unavailable, VSA regression may need to be marked as skip-if-no-data.
**Warning signs:** `FileNotFoundError` when running VSA backtest.

### Pitfall 4: Notebook Import Updates Are JSON Edits
**What goes wrong:** Trying to update notebook imports with text find-replace.
**Why it happens:** `.ipynb` files are JSON. Import statements are inside string arrays in code cells.
**How to avoid:** Use Python's `json` module to load, modify import strings, and save notebooks. Or use careful string replacement knowing the JSON structure.
**Warning signs:** Broken JSON in notebooks, or imports not actually updated.

### Pitfall 5: sys.path Manipulation in analysis/diagnose_vn30.py
**What goes wrong:** `analysis/diagnose_vn30.py` currently uses `sys.path.append` to access `models`. After migration it needs to access `strategies.mdm_classic` instead, AND the sys.path hack needs to reference the correct parent directory since the file moves.
**Why it happens:** Script was written before proper package structure existed.
**How to avoid:** After moving to `analysis/diagnose_vn30.py` (already there), update to use `from strategies.mdm_classic.data_loader import DataLoader` and ensure the project root is on sys.path. Better: run from project root with `python -m analysis.diagnose_vn30`.

### Pitfall 6: core/__init__.py Is Currently Empty
**What goes wrong:** D-02 says core/ should export shared types (MarketState, Position, Trade). But currently `core/__init__.py` is empty (1 line, effectively blank).
**Why it happens:** Phase 1 only created the data_loader and signal_loader.
**How to avoid:** Evaluate whether MarketState/Position truly need to be in core/. The two strategies have completely different Position classes (MDM: 9 fields; VSA: stock_code, spike tracking, MA10 violation, etc.) and VSA doesn't even use MarketState. Per "Claude's Discretion" on shared types: the answer is likely that NOTHING is truly shared between strategies. Keep core/ minimal with just Phase 1 artifacts.

## Code Examples

### MDM Regression Test Pattern
```python
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'

class TestMDMRegression:
    """Verify MDM strategy output is identical after migration."""

    @pytest.fixture(scope='class')
    def mdm_results(self):
        from strategies.mdm_classic.data_loader import DataLoader
        from strategies.mdm_classic import MDMEngine
        loader = DataLoader('vnindex_price.csv')
        df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
        engine = MDMEngine()
        results = engine.run(df)
        return results, engine

    def test_signal_sequence_matches(self, mdm_results):
        results, _ = mdm_results
        signals = results[results['action'] != ''][['date', 'close', 'state', 'action']].copy()
        signals = signals.reset_index(drop=True)
        baseline = pd.read_csv(FIXTURES / 'mdm_signals_baseline.csv', parse_dates=['date'])
        pd.testing.assert_frame_equal(signals, baseline)

    def test_trade_pnl_matches(self, mdm_results):
        _, engine = mdm_results
        trades = engine.get_trade_df()
        baseline = pd.read_csv(FIXTURES / 'mdm_trades_baseline.csv', parse_dates=['date'])
        # Exact match on string columns, close match on float columns
        for col in ['type', 'date']:
            pd.testing.assert_series_equal(trades[col], baseline[col])
        if 'pnl' in trades.columns:
            np.testing.assert_allclose(
                trades['pnl'].fillna(0).values,
                baseline['pnl'].fillna(0).values,
                atol=1e-10
            )
```

### Import Update Map
```python
# Scripts that need import updates:
IMPORT_CHANGES = {
    # Old import -> New import
    'from models import MDMEngine, DataLoader': 'from strategies.mdm_classic import MDMEngine\nfrom strategies.mdm_classic.data_loader import DataLoader',
    'from models.config import MDMConfig': 'from strategies.mdm_classic.config import MDMConfig',
    'from models.mdm_engine import MDMEngine': 'from strategies.mdm_classic.mdm_engine import MDMEngine',
    'from models.performance import PerformanceAnalyzer': 'from strategies.mdm_classic.performance import PerformanceAnalyzer',
    'from vn30_vsa.vsa_engine import VSAEngine': 'from strategies.vsa.vsa_engine import VSAEngine',
    'from vn30_vsa.performance import': 'from strategies.vsa.performance import',
    'from models.data_loader import DataLoader': 'from strategies.mdm_classic.data_loader import DataLoader',
}
```

### Files That Need Import Updates
| File | Current Import | New Import |
|------|---------------|------------|
| `scripts/run_backtest.py` | `from models import MDMEngine, DataLoader` | `from strategies.mdm_classic import MDMEngine, DataLoader` |
| `scripts/optimize_mdm.py` | `from models.config import MDMConfig` etc. | `from strategies.mdm_classic.config import MDMConfig` etc. |
| `scripts/check_date.py` | `from models import MDMEngine, DataLoader` | `from strategies.mdm_classic import MDMEngine, DataLoader` |
| `analysis/analyze_drawdown.py` | `from models import MDMEngine, DataLoader` | `from strategies.mdm_classic import MDMEngine, DataLoader` |
| `analysis/analyze_vsa_drawdown.py` | `from vn30_vsa.vsa_engine import VSAEngine` | `from strategies.vsa.vsa_engine import VSAEngine` |
| `analysis/diagnose_vn30.py` | `from models.data_loader import DataLoader` + sys.path hack | `from strategies.mdm_classic.data_loader import DataLoader` (remove sys.path hack) |
| `mdm_backtest.ipynb` | `from models import (...)` | `from strategies.mdm_classic import (...)` |
| `sp500_backtest.ipynb` | `from models.mdm_engine import MDMEngine` | `from strategies.mdm_classic.mdm_engine import MDMEngine` |
| `vn30_vsa_backtest.ipynb` | `from vn30_vsa.vsa_engine import VSAEngine` etc. | `from strategies.vsa.vsa_engine import VSAEngine` etc. |
| `tests/test_data_loader.py` | `from core.data_loader import DataLoader` | No change (core/ stays) |

## Shared Types Analysis

Per "Claude's Discretion" on which types are truly shared:

| Type | MDM Version | VSA Version | Truly Shared? |
|------|------------|-------------|---------------|
| `MarketState` enum | CASH, HOLDING, WAITING_SELL, SHORT | Not used (VSA uses dict-based position tracking) | **NO** |
| `Position` dataclass | 9 fields: state, buy_price, buy_date, etc. | 10+ fields: stock_code, spike_high, spike_low, violated_ma10, etc. | **NO** |
| `Trade` record | Dict with type/date/price/pnl | DataFrame rows with stock_code/pnl_pct/exit_reason | **NO** |

**Recommendation:** Do NOT extract shared types to `core/`. The strategies have completely different domain models. `core/` should remain minimal: just `data_loader.py` and `signal_loader.py` from Phase 1. This aligns with D-01's explicit "no forced abstractions" and is the honest result of reading the actual code.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `models/` flat package | `strategies/mdm_classic/` nested | This phase | All MDM imports change |
| `vn30_vsa/` flat package | `strategies/vsa/` nested | This phase | All VSA imports change |
| Scripts at root | `scripts/` directory | This phase | Cleaner root, scripts run from root with `python scripts/X.py` |
| Analysis scripts scattered | `analysis/` directory | This phase | Unified analysis location |

## Open Questions

1. **VN30_STOCKS_PRICE.csv availability**
   - What we know: Git status shows `D VN30_STOCKS_PRICE.csv` (deleted). VSAEngine.load_data() expects this file.
   - What's unclear: Whether this file is available locally (gitignored) or completely gone. `vn30_price.csv` exists but is for index data, not individual stocks.
   - Recommendation: During baseline generation, check if the file exists. If not, VSA regression tests should be `@pytest.mark.skipif` when data is unavailable. The structural migration (file moves + imports) can still be verified without the data.

2. **Notebook import update approach**
   - What we know: 3 notebooks have imports that need updating. They are JSON files.
   - What's unclear: Whether to use `json` module programmatically or manual search-replace.
   - Recommendation: Use Python script or careful string replacement. The import patterns are simple and well-defined (see Import Update Map above).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None -- needs `[tool.pytest.ini_options]` in pyproject.toml (Wave 0) |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/ -x -q` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ORG-01 | Three-layer architecture exists | smoke | `python -c "from strategies.mdm_classic import MDMEngine; from strategies.vsa import VSAEngine; from core.data_loader import DataLoader"` | No -- Wave 0 |
| ORG-02 | MDM migrated, runs correctly | integration | `.venv/Scripts/python.exe -m pytest tests/test_mdm_regression.py -x` | No -- Wave 0 |
| ORG-03 | VSA migrated, runs correctly | integration | `.venv/Scripts/python.exe -m pytest tests/test_vsa_regression.py -x` | No -- Wave 0 |
| ORG-04 | Output identical to baseline | integration | `.venv/Scripts/python.exe -m pytest tests/test_mdm_regression.py tests/test_vsa_regression.py -v` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/ -x -q`
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mdm_regression.py` -- covers ORG-02, ORG-04
- [ ] `tests/test_vsa_regression.py` -- covers ORG-03, ORG-04
- [ ] `tests/fixtures/` directory with baseline CSV files
- [ ] `[tool.pytest.ini_options]` in `pyproject.toml` -- configure testpaths, markers
- [ ] Baseline generation script to capture old code output before migration

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all 22 `.py` files in `models/` and `vn30_vsa/`
- Verified zero cross-imports between `models/` and `vn30_vsa/` via grep
- Verified all internal imports are relative (`from .module import X`)
- Verified existing pytest infrastructure (9.0.2, `tests/` with 2 test files)
- Verified `core/` contents from Phase 1 (data_loader.py, signal_loader.py, empty __init__.py)

### Secondary (MEDIUM confidence)
- Import patterns in notebooks verified via grep of `.ipynb` files
- VSA data file status inferred from git status (`D VN30_STOCKS_PRICE.csv`)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new packages needed, all verified installed
- Architecture: HIGH - file inventory complete, import patterns mapped, zero cross-imports confirmed
- Pitfalls: HIGH - discovered through actual code inspection (MDM vs VSA Position differences, data loader divergence, missing VSA data file)

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable -- no external dependency changes expected)
