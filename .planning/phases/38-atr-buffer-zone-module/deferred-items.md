# Deferred Items - Phase 38 ATR Buffer Zone Module

## Pre-existing Test Failure (out of scope)

**Discovered during:** Plan 02, Task 2 verification
**Test:** `tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq`
**Failure:** Asserts `hybrid_buy_in_v2_buy > 0.95` (Hybrid BUY state matches V2 BUY ≥95% of time), but actual is 82.68%
**Status:** Confirmed pre-existing — failure reproduced identically via `git stash` before any Plan 02 changes applied
**Not fixed:** Out-of-scope per deviation rules (not caused by current task's changes)
**Suggested action:** Investigate in a separate debug session after Phase 38 completes
