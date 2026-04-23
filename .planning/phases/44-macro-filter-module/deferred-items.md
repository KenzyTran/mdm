# Phase 44 Deferred Items

Out-of-scope issues discovered during execution. Not fixed per scope boundary rule (only auto-fix issues DIRECTLY caused by the current task's changes).

## Plan 44-02 (Wave 2)

### Pre-existing test failure (NOT caused by this plan's changes)

- **Test:** `tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq`
- **Assertion:** `hybrid_buy_in_v2_buy > 0.95`, got `0.8268` (82.68%)
- **Verified pre-existing:** `git stash` confirms the same failure at commit e95fc07 (head before this plan), so it is not a regression introduced by adding the 10 macro filter config fields.
- **Blast radius:** None for Plan 44-02 — config additions are default-off and inert (macro_filter_enabled=False); no engine behavior change.
- **Gate status:** Does NOT gate Plan 44-02 acceptance. The relevant parity gate is `tests/test_baseline_determinism.py` (3/3 PASS).
- **Recommendation:** Separate bug triage; likely related to NASDAQ preset behavior on hybrid composition, unrelated to Phase 44 scope.
