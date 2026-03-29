# Phase 11: Foundation & Two-Phase Commit - Research

**Researched:** 2026-03-29
**Domain:** Python state machine architecture, snapshot/restore pattern, package forking
**Confidence:** HIGH

## Summary

Phase 11 creates the `strategies/mdm_hybrid/` package by forking `strategies/mdm_v2/` and adding a two-phase commit mechanism using `copy.deepcopy()` snapshot/restore. The v2 engine has 4 mutable components (DD counter, rally tracker, FTD detector, position manager) that mutate state during daily processing. The two-phase commit wraps each day's processing: snapshot all 4 components before processing, let them mutate normally, then either keep the mutations (confirm) or restore from snapshot (veto).

Empirical testing confirms `copy.deepcopy()` works correctly on all 4 v2 components with full isolation -- mutating a copy does not affect the original. Performance overhead is ~0.04ms per cycle (4 deepcopies), adding ~0.5 seconds to a full 13,000-day NASDAQ backtest. This is negligible.

**Primary recommendation:** Fork v2 as-is, add snapshot/restore wrapping in the engine's daily loop, and verify bit-for-bit regression with `assert_series_equal` on state/action columns across the full NASDAQ dataset.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Fork entire `strategies/mdm_v2/` into `strategies/mdm_hybrid/`. Full copy, independent package. No imports back to v2. Follows the same fork pattern used in Phase 4 (classic -> v2).
- **D-02:** Engine file named `mdm_hybrid_engine.py`, class `HybridEngine`. Consistent with `mdm_v2_engine.py` naming pattern.
- **D-03:** Snapshot/restore pattern using `copy.deepcopy()`. Before processing each day, snapshot all 4 components. If filter vetos the proposal, restore snapshot. If confirm (or no filter active), keep mutated state.
- **D-04:** All 4 mutable components protected by two-phase commit: DD counter (reset on FTD), position manager (enter_buy/exit_to_cash/enter_sell), rally tracker (full_reset after FTD), FTD detector (internal state).
- **D-05:** `two_phase_enabled` defaults to `True` in HybridConfig. Hybrid engine always uses snapshot/restore. Must be explicitly disabled for bypass.
- **D-06:** Composition pattern -- HybridConfig contains a `v2_config: MDMV2Config` field plus hybrid-specific flags. Clear separation between v2 state machine params and hybrid control flags.
- **D-07:** Phase 11 adds only `two_phase_enabled: bool = True` and `filter_enabled: bool = False` as hybrid-specific flags. Phase 12 will add indicator filter configuration.
- **D-08:** Integration test compares hybrid (no filter) vs v2 on full NASDAQ data (1974-2026). Bit-for-bit match on 'state' and 'action' columns using `assert_series_equal`.
- **D-09:** Signal sequence comparison -- run both engines on identical data, verify identical state transitions every day. This is the primary regression baseline for Phase 11.

### Claude's Discretion
- Snapshot helper function location (inline in engine vs separate module)
- Exact deepcopy implementation details and performance optimization if needed
- Which v2 modules to copy as-is vs which need modification for two-phase commit integration
- Test file organization and pytest fixtures
- How to structure the proposal object that will later be passed to indicator filter (Phase 12)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HYB-01 | State machine layer reuses v2 logic (DD counting, FTD detection, Rally Attempts) as signal proposal layer | Fork v2 package as-is; all 4 components (DD counter, rally tracker, FTD detector, position manager) carry over unchanged. Engine wraps them with snapshot/restore. |
| HYB-06 | Two-phase commit for state machine -- do not mutate state before filter confirms | `copy.deepcopy()` verified to provide full isolation on all 4 components. 0.04ms/cycle overhead is negligible. Snapshot before day, restore on veto, keep on confirm. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| copy (stdlib) | Python 3.12 | `deepcopy()` for snapshot/restore | Built-in, no dependencies. Verified working on all 4 component types. |
| dataclasses (stdlib) | Python 3.12 | `HybridConfig` dataclass with composition | Matches existing `MDMV2Config` pattern |
| pandas | 2.2.x (installed) | DataFrame operations, `assert_series_equal` in tests | Already in stack, used for regression testing |
| pytest | 9.0.2 (installed) | Unit and integration tests | Already configured in pyproject.toml |

### Supporting
No additional libraries needed. This phase uses only stdlib + existing dependencies.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `copy.deepcopy()` | Manual `__copy__`/`__getstate__` | More code, same result. deepcopy works correctly already. |
| `copy.deepcopy()` | Memento pattern with explicit state dicts | More structured but unnecessary complexity for 4 simple objects |

## Architecture Patterns

### Recommended Project Structure
```
strategies/mdm_hybrid/
    __init__.py              # Export HybridConfig, HybridEngine
    config.py                # HybridConfig (composition of MDMV2Config + hybrid flags)
    mdm_hybrid_engine.py     # HybridEngine with two-phase commit loop
    distribution_day.py      # Copied as-is from v2
    rally_attempt.py         # Copied as-is from v2
    ftd_signal.py            # Copied as-is from v2
    stop_loss.py             # Copied as-is from v2
    position_manager.py      # Copied as-is from v2
    indicators.py            # Copied as-is from v2
    performance.py           # Copied as-is from v2
    vn30_filters.py          # Copied as-is from v2
```

### Pattern 1: Snapshot/Restore Two-Phase Commit
**What:** Before processing each day, deepcopy the 4 mutable components. After processing, either keep mutations (confirm) or restore snapshots (rollback).
**When to use:** Every day in the engine loop when `two_phase_enabled=True`.
**Example:**
```python
import copy

# In HybridEngine.run() daily loop:
if self.config.two_phase_enabled:
    # Phase 1: SNAPSHOT
    snapshot = {
        'dd_counter': copy.deepcopy(self.dd_counter),
        'rally_tracker': copy.deepcopy(self.rally_tracker),
        'ftd_detector': copy.deepcopy(self.ftd_detector),
        'position_manager': copy.deepcopy(self.position_manager),
    }

# ... existing v2 daily processing (mutates components) ...

if self.config.two_phase_enabled and self.config.filter_enabled:
    # Phase 2: DECIDE (filter logic comes in Phase 12)
    vetoed = False  # placeholder
    if vetoed:
        # ROLLBACK
        self.dd_counter = snapshot['dd_counter']
        self.rally_tracker = snapshot['rally_tracker']
        self.ftd_detector = snapshot['ftd_detector']
        self.position_manager = snapshot['position_manager']
```

### Pattern 2: HybridConfig Composition
**What:** HybridConfig wraps MDMV2Config rather than inheriting from it.
**When to use:** For clear separation of v2 params vs hybrid control flags.
**Example:**
```python
from dataclasses import dataclass, field
from strategies.mdm_v2.config import MDMV2Config  # NO -- this is in hybrid package

@dataclass
class HybridConfig:
    """Configuration for hybrid MDM engine.

    Composes v2 config (state machine params) with hybrid-specific flags.
    """
    v2_config: MDMV2Config = field(default_factory=MDMV2Config)
    two_phase_enabled: bool = True
    filter_enabled: bool = False

    def __post_init__(self):
        if isinstance(self.v2_config, dict):
            self.v2_config = MDMV2Config(**self.v2_config)
```

**IMPORTANT:** Since the hybrid package is a full fork, it will have its own copy of `MDMV2Config` (aliased as `MDMConfig`). The `HybridConfig.v2_config` field uses the LOCAL copy, not an import from `strategies/mdm_v2/`.

### Pattern 3: Compatibility Alias
**What:** The v2 package uses `MDMConfig = MDMV2Config` alias so copied modules (distribution_day, rally_attempt, etc.) that `from .config import MDMConfig` continue working.
**When to use:** In the hybrid package's `config.py`.
**Example:**
```python
# In strategies/mdm_hybrid/config.py
# Keep the MDMV2Config class as-is (copied from v2)
# Keep the MDMConfig alias so forked modules work unchanged
MDMConfig = MDMV2Config

# Add HybridConfig alongside
@dataclass
class HybridConfig:
    v2_config: MDMV2Config = field(default_factory=MDMV2Config)
    two_phase_enabled: bool = True
    filter_enabled: bool = False
```

### Anti-Patterns to Avoid
- **Importing from v2:** Hybrid package MUST be fully independent. No `from strategies.mdm_v2 import ...`. This is locked decision D-01.
- **Selective deepcopy:** Deepcopying only some components creates inconsistent state. All 4 must be snapshotted together.
- **Mutating config during snapshot/restore:** Config is immutable params -- never include it in the snapshot cycle.
- **Conditional processing logic:** The v2 daily processing code should run identically whether two-phase is enabled or not. Two-phase commit wraps the processing, it does not change processing logic.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Object cloning | Custom `clone()` methods on each component | `copy.deepcopy()` | Verified working on all 4 types, handles nested objects automatically |
| Series comparison | Manual loop comparing states | `pd.testing.assert_series_equal()` | Handles NaN, dtype differences, provides clear error messages |
| Config composition | Flat config with all params | Dataclass composition (`v2_config` field) | Clean separation, Phase 12 adds fields without touching v2 params |

## Common Pitfalls

### Pitfall 1: StopLossChecker Config Reference
**What goes wrong:** When forked modules import `from .config import MDMConfig`, the hybrid config.py must still export `MDMConfig` as alias.
**Why it happens:** All 4 component modules (distribution_day, rally_attempt, ftd_signal, stop_loss) use `from .config import MDMConfig`.
**How to avoid:** Keep the `MDMConfig = MDMV2Config` alias in the hybrid config.py alongside the new `HybridConfig`.
**Warning signs:** ImportError on first test run.

### Pitfall 2: Position Manager Trades List Grows Through Snapshots
**What goes wrong:** If snapshot is taken after a trade is recorded, and then restored, the trade is lost from the trades list.
**Why it happens:** `position_manager.trades` is a list that accumulates. Deepcopy captures its state at snapshot time.
**How to avoid:** This is actually correct behavior for two-phase commit -- a vetoed signal should not record a trade. But understand that the trades list is part of the rollback. For Phase 11 with `filter_enabled=False`, no rollback ever happens so this is not an issue yet.
**Warning signs:** Missing trades in hybrid vs v2 comparison (would only appear in Phase 12+).

### Pitfall 3: DD Counter Reset on FTD Happens Inside Processing
**What goes wrong:** In v2 engine lines 147/161/173, `self.dd_counter.reset()` is called inside the FTD detection block. If a filter later vetoes this FTD, the DD counter has been incorrectly reset.
**Why it happens:** V2 assumed signals are always accepted.
**How to avoid:** The snapshot/restore pattern handles this automatically -- DD counter state is snapshotted before the reset can happen, and restored if vetoed.
**Warning signs:** DD counter at 0 after a vetoed FTD (the exact bug two-phase commit prevents).

### Pitfall 4: Rally Tracker full_reset After FTD (Line 221)
**What goes wrong:** Similar to Pitfall 3. `self.rally_tracker.full_reset()` at line 221 runs after FTD detection. A vetoed FTD should not reset the rally tracker.
**Why it happens:** V2 unconditionally resets rally tracker when FTD fires.
**How to avoid:** Snapshot/restore covers this. The rally tracker is one of the 4 snapshotted components.
**Warning signs:** Rally day count at 0 after vetoed FTD.

### Pitfall 5: Regression Test Must Use Same Config
**What goes wrong:** Hybrid engine with default HybridConfig may not produce identical results to v2 engine with default MDMV2Config if the config composition introduces subtle differences.
**Why it happens:** HybridConfig wraps MDMV2Config -- need to ensure the inner config defaults match v2 defaults exactly.
**How to avoid:** In regression test, explicitly create `HybridConfig(v2_config=MDMV2Config())` and `MDMV2Config()` with same default parameters. Verify `HybridConfig().v2_config` equals `MDMV2Config()`.
**Warning signs:** State mismatches starting from day 1.

### Pitfall 6: Worktree Data Path Resolution
**What goes wrong:** Tests fail when run from git worktree because data files live in main repo.
**Why it happens:** Existing test infrastructure uses `WORKTREE_ROOT` / `MAIN_REPO` path resolution pattern (see test_mdm_v2_engine.py lines 10-20).
**How to avoid:** Copy the same worktree path resolution pattern into hybrid tests.
**Warning signs:** FileNotFoundError when loading NASDAQ data in integration tests.

## Code Examples

### Complete HybridConfig (recommended)
```python
from dataclasses import dataclass, field

# MDMV2Config is copied into this package, not imported from v2
from .config_base import MDMV2Config  # or just inline in same file

@dataclass
class HybridConfig:
    """Hybrid MDM engine configuration.

    Composes v2 state machine config with hybrid control flags.
    Phase 11: two_phase_enabled + filter_enabled only.
    Phase 12 will add indicator filter configuration fields.
    """
    v2_config: MDMV2Config = field(default_factory=MDMV2Config)
    two_phase_enabled: bool = True
    filter_enabled: bool = False
```

### Snapshot/Restore Helper (recommended: inline in engine)
```python
def _snapshot_components(self) -> dict:
    """Snapshot all mutable state machine components."""
    return {
        'dd_counter': copy.deepcopy(self.dd_counter),
        'rally_tracker': copy.deepcopy(self.rally_tracker),
        'ftd_detector': copy.deepcopy(self.ftd_detector),
        'position_manager': copy.deepcopy(self.position_manager),
    }

def _restore_components(self, snapshot: dict):
    """Restore all mutable state machine components from snapshot."""
    self.dd_counter = snapshot['dd_counter']
    self.rally_tracker = snapshot['rally_tracker']
    self.ftd_detector = snapshot['ftd_detector']
    self.position_manager = snapshot['position_manager']
```

### Proposal Dataclass (for Phase 12 forward compatibility)
```python
@dataclass
class SignalProposal:
    """A proposed signal transition from the state machine.

    Created after state machine processes a day.
    Passed to indicator filter for confirm/veto decision.
    Phase 11: always confirmed (filter_enabled=False).
    Phase 12: filter inspects and may veto.
    """
    date: pd.Timestamp
    proposed_state: str      # The state after processing (BUY/CASH/SELL)
    previous_state: str      # The state before processing
    action: str              # Action description
    is_transition: bool      # Whether state actually changed
    signal_type: str = ""    # FTD, MA50, 52WEEK, DD, stop_loss, etc.
```

### Regression Test Pattern
```python
def test_hybrid_matches_v2_on_nasdaq(nasdaq_data):
    """Hybrid engine (no filter) must produce identical output to v2."""
    from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
    from strategies.mdm_v2.config import MDMV2Config as V2Config
    from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
    from strategies.mdm_hybrid.config import HybridConfig

    v2_config = V2Config()
    v2_engine = MDMV2Engine(v2_config)
    v2_result = v2_engine.run(nasdaq_data)

    hybrid_config = HybridConfig(v2_config=V2Config(), filter_enabled=False)
    hybrid_engine = HybridEngine(hybrid_config)
    hybrid_result = hybrid_engine.run(nasdaq_data)

    pd.testing.assert_series_equal(
        v2_result['state'], hybrid_result['state'],
        check_names=False, obj="state column"
    )
    pd.testing.assert_series_equal(
        v2_result['action'], hybrid_result['action'],
        check_names=False, obj="action column"
    )
```

### Vetoed FTD Unit Test (the core correctness test)
```python
def test_vetoed_ftd_does_not_reset_dd_counter():
    """A vetoed FTD must not reset the DD counter.

    Scenario: DD counter has 3 DDs. FTD fires. Filter vetos.
    Expected: DD counter still has 3 DDs.
    """
    # This test verifies the snapshot/restore mechanism
    # by manually simulating what the filter would do.
    engine = HybridEngine(HybridConfig(two_phase_enabled=True))

    # Setup: manually set dd_counter to have some history
    engine.dd_counter.dd_history = [date1, date2, date3]

    # Snapshot
    snapshot = engine._snapshot_components()

    # Simulate FTD processing (which calls dd_counter.reset())
    engine.dd_counter.reset()
    assert len(engine.dd_counter.dd_history) == 0  # mutated

    # Restore (simulating veto)
    engine._restore_components(snapshot)
    assert len(engine.dd_counter.dd_history) == 3  # restored
```

## Mutation Point Audit

Complete inventory of state mutations in the v2 engine daily loop that two-phase commit must protect:

| Line | Component | Mutation | Trigger |
|------|-----------|----------|---------|
| 125-127 | rally_tracker | `process_day()` updates peak, correction state, day1, rally count | Every day in CASH/SELL |
| 142-143 | ftd_detector | `check_ftd()` sets `last_signal` | Rally day >= 4 in CASH/SELL |
| 147 | dd_counter | `reset()` clears dd_history | FTD detected |
| 154-155 | ftd_detector | `check_ma50_breakout()` sets `last_signal` | Not FTD, in CASH/SELL |
| 161 | dd_counter | `reset()` clears dd_history | MA50 breakout |
| 166-167 | ftd_detector | `check_52week_breakout()` sets `last_signal` | Not FTD/MA50, in CASH/SELL |
| 173 | dd_counter | `reset()` clears dd_history | 52-week breakout |
| 181-182 | dd_counter | `check_distribution_day()` appends to dd_history | In BUY state |
| 203-217 | position_manager | `process_day()` calls enter_buy/exit_to_cash/enter_sell, appends trades | Every day |
| 221 | rally_tracker | `full_reset()` clears all state | FTD detected |

**Key insight:** All mutations happen through method calls on the 4 components. No direct attribute mutation from the engine loop. This means snapshot/restore at the component level captures everything.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_hybrid_engine.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HYB-01 | v2 logic reused in hybrid (fork produces identical results) | integration | `uv run pytest tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq -x` | Wave 0 |
| HYB-06 | Two-phase commit prevents DD counter corruption on vetoed FTD | unit | `uv run pytest tests/test_hybrid_engine.py::test_vetoed_ftd_does_not_reset_dd_counter -x` | Wave 0 |
| HYB-06 | Two-phase commit prevents rally tracker corruption on vetoed FTD | unit | `uv run pytest tests/test_hybrid_engine.py::test_vetoed_ftd_does_not_reset_rally_tracker -x` | Wave 0 |
| HYB-06 | Two-phase commit snapshot/restore isolation | unit | `uv run pytest tests/test_hybrid_engine.py::test_snapshot_restore_isolation -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_hybrid_engine.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_hybrid_engine.py` -- covers HYB-01 (regression) and HYB-06 (snapshot/restore, veto protection)
- [ ] `strategies/mdm_hybrid/__init__.py` -- package must exist before tests can import

## Modules to Copy vs Modify

| Module | Action | Reason |
|--------|--------|--------|
| `distribution_day.py` | Copy as-is | No changes needed; imports `MDMConfig` from local `.config` |
| `rally_attempt.py` | Copy as-is | No changes needed; imports `MDMConfig` from local `.config` |
| `ftd_signal.py` | Copy as-is | No changes needed; imports `MDMConfig` from local `.config` |
| `stop_loss.py` | Copy as-is | No changes needed; imports `MDMV2Config` from local `.config` |
| `position_manager.py` | Copy as-is | No changes needed; imports `MDMV2Config` from local `.config` |
| `indicators.py` | Copy as-is | Static methods, no state |
| `performance.py` | Copy as-is | Analysis utility |
| `vn30_filters.py` | Copy as-is | VN30-specific, may be used later |
| `config.py` | **Modify** | Add `HybridConfig` dataclass alongside existing `MDMV2Config`/`MDMConfig` |
| `mdm_v2_engine.py` | **Modify** -> `mdm_hybrid_engine.py` | Rename class to `HybridEngine`, add snapshot/restore, accept `HybridConfig` |
| `__init__.py` | **New** | Export `HybridConfig`, `HybridEngine` |

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_v2/mdm_v2_engine.py` -- Full source code audit of daily processing loop and all mutation points
- `strategies/mdm_v2/position_manager.py` -- V2PositionManager state machine with enter_buy/exit_to_cash/enter_sell
- `strategies/mdm_v2/distribution_day.py` -- DistributionDayCounter with dd_history list and reset()
- `strategies/mdm_v2/rally_attempt.py` -- RallyAttemptTracker with full_reset() and process_day() mutations
- `strategies/mdm_v2/ftd_signal.py` -- FTDSignalDetector with last_signal state
- `strategies/mdm_v2/config.py` -- MDMV2Config dataclass and MDMConfig alias pattern
- Empirical `copy.deepcopy()` testing -- All 4 components verified for isolation and performance (0.04ms/cycle)

### Secondary (MEDIUM confidence)
- `tests/test_mdm_v2_engine.py` -- Existing test patterns, worktree path resolution, synthetic data generation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib copy + existing deps only, verified empirically
- Architecture: HIGH - fork pattern established in Phase 4, deepcopy verified on all component types
- Pitfalls: HIGH - identified through direct code audit of all mutation points in v2 engine

**Research date:** 2026-03-29
**Valid until:** indefinite (architecture patterns, no external dependency drift)
