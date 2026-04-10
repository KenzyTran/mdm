# Deferred Items - Phase 35

## Pre-existing Test Failures

1. **tests/canslim/test_config.py::test_s_vol_mult_below_one_raises** - Test expects `s_vol_mult >= 1` but CanslimConfig validates `>= 0`. Mismatch from Phase 29. Not related to Phase 35 changes.
