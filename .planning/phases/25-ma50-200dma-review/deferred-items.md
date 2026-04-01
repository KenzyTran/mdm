# Deferred Items - Phase 25

## Pre-existing Issues Found (Out of Scope)

### test_data_foundation.py::TestSignalDateAlignment::test_gap_report_returns_dataframe

**Found during:** Task 2 (full suite run)
**Issue:** `FileNotFoundError: data/NASDAQ.csv` - missing data file required by this test
**Status:** Pre-existing before Phase 25 changes
**Action needed:** Add `data/NASDAQ.csv` or mock the file in the test fixture
**Out of scope:** This is not caused by Phase 25 changes

### test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq

**Found during:** Phase 25 Plan 02 - Task 1/2 full suite verification
**Issue:** `AssertionError: Hybrid should be BUY when v2 is BUY at least 95% of the time, got 88.49%`
**Status:** Pre-existing before Phase 25 Plan 02 changes (confirmed by stash + re-run)
**Action needed:** Investigate hybrid engine vs v2 BUY state divergence (likely from Phase 23 fail-safe changes)
**Out of scope:** Not caused by Plan 02 changes (200dma wiring only adds new optional paths, defaults unchanged)
