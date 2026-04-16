---
phase: 39-refined-distribution-day-module
verified: 2026-04-16T11:30:00Z
status: passed
score: 4/4 success criteria verified
re_verification:
  previous_status: none
  note: Initial verification (no prior VERIFICATION.md)
requirements_verified:
  - DD-01
  - DD-02
  - DD-03
  - DD-04
---

# Phase 39: Refined Distribution Day Module Verification Report

**Phase Goal:** Distribution Day detector replaces the hard-coded -0.2% rule with a parameterized dual-threshold definition that captures both obvious drops and subtle-but-heavy-volume drops.
**Verified:** 2026-04-16T11:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
|---|---------------------------|--------|----------|
| 1 | DD detector accepts 5 new parameters and stops using any hard-coded -0.2% threshold when refined is enabled | VERIFIED | `strategies/mdm_hybrid/config.py` lines 68-74 define all 6 refined_dd_* fields; `strategies/mdm_hybrid/distribution_day.py` lines 65-78 branch — refined path NEVER reads `dd_price_drop_threshold` (-0.002) |
| 2 | DD fires when (drop >= large_drop AND vol > vol_ma20) OR (drop >= small_drop AND vol in top percentile) | VERIFIED | `distribution_day.py` lines 69-78: `large_drop_dd` uses `refined_dd_large_drop` + `vol_above_ma20`; `small_drop_dd` uses `refined_dd_small_drop` + `vol_top_pct`; returns OR. Proven by 5 refined-path tests in `test_phase39_dd_logic.py` |
| 3 | Config flag `refined_dd_enabled` toggles new rule, falling back to classic -0.2% | VERIFIED | `config.py` line 69: default `False`; `distribution_day.py` line 65 `if not self.config.refined_dd_enabled:` branches to classic rule. Both presets (VN30, NASDAQ) ship `refined_dd_enabled=False` (config.py lines 156, 192) |
| 4 | HybridEngine with refined_dd_enabled=False produces DD count sequence identical to v6.0 baseline on VN30 2015-2026 | VERIFIED | `tests/fixtures/phase39_v6_baseline_dd_sequence.parquet` (2808 rows, 110 DDs: 109 Type 1 + 1 Type 2) locked by `test_refined_dd_disabled_matches_baseline` with byte-exact equality on `is_dd`, `dd_type`, `dd_count`. Test passed in live run. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `strategies/mdm_hybrid/config.py` | 6 refined_dd_* fields + gated validation + propagated to both presets | VERIFIED | Lines 68-74 define fields; lines 88-96 gate validation on `refined_dd_enabled`; VN30_PRESET (156-161) + NASDAQ_PRESET (192-197) both ship disabled |
| `strategies/mdm_hybrid/indicators.py` | add_volume_ma_column + add_volume_percentile_column | VERIFIED | Lines 247-263 add `vol_ma20` via rolling(period).mean(); lines 265-294 add `vol_top_pct` boolean via rolling.quantile. Both use `min_periods=1` matching module convention |
| `strategies/mdm_hybrid/distribution_day.py` | Dual-threshold is_distribution_day_type1 with branched logic | VERIFIED | Lines 32-78: new signature with `vol_above_ma20`/`vol_top_pct` kwargs (default False, Pitfall 4); line 65 branches on flag; Type 2 (lines 80-100) unchanged |
| `strategies/mdm_hybrid/mdm_hybrid_engine.py` | Precompute + DD call wiring | VERIFIED | Lines 171-179 gated precompute; lines 196-201 expiry suppression of vol_top_pct; lines 313-333 BUY-state daily loop synthesizes vol inputs with expiry guard and passes kwargs to `check_distribution_day` |
| `tests/test_phase39_indicators.py` | Unit tests for config + indicators | VERIFIED | 14 test functions covering defaults, validation gating, MA + percentile semantics, min_periods edge, non-mutation |
| `tests/test_phase39_dd_logic.py` | Unit tests for branched DD logic | VERIFIED | 11 test functions covering classic fallback (3), refined large-drop path (2), refined small-drop path (3), Type 2 invariance (1), check_distribution_day signature compat (2) |
| `tests/test_phase39_backward_compat.py` | Regression test for DD-04 | VERIFIED | 2 test functions: byte-exact equality against fixture + fixture schema check. Uses `pytest.fail` (not skip) on missing asset per D-10/D-11 |
| `tests/fixtures/phase39_v6_baseline_dd_sequence.parquet` | v6.0 baseline | VERIFIED | 28,515 bytes, 2808 rows × 4 cols (`date`, `is_dd`, `dd_type`, `dd_count`), 110 DDs (109 Type 1 + 1 Type 2), range 2015-01-05 to 2026-04-07 |
| `scripts/generate_phase39_fixture.py` | Fixture generator | VERIFIED | Runnable script uses DataLoader('vn30'), `MDMV2Config(refined_dd_enabled=False)`, writes parquet with `[date, is_dd, dd_type, dd_count]` |
| `docs/rules_mdm_hybrid.md` | Section XVII for refined DD | VERIFIED | Section XVII starts at line 555; covers feature gate, dual-threshold rule, Type 2 invariance, params table, indicator gating, expiry suppression (2-layer), backward-compat fixture reference |

### Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| `config.py` | `distribution_day.py` | `self.config.refined_dd_enabled` read by DD counter | WIRED (distribution_day.py line 65) |
| `mdm_hybrid_engine.py` | `indicators.py` | `Indicators.add_volume_ma_column` + `add_volume_percentile_column` in precompute | WIRED (engine lines 174, 175 — confirmed via grep) |
| `mdm_hybrid_engine.py` | `distribution_day.py` | `check_distribution_day(..., vol_above_ma20=..., vol_top_pct=...)` | WIRED (engine lines 329-333) |
| `test_phase39_backward_compat.py` | `phase39_v6_baseline_dd_sequence.parquet` | `pd.read_parquet(FIXTURE_PATH)` | WIRED (test line 52) |
| `test_phase39_backward_compat.py` | `mdm_hybrid_engine.py` | `HybridEngine(MDMV2Config(refined_dd_enabled=False)).run(...)` | WIRED (test lines 58-60) |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Produces Real Data | Status |
|----------|------|--------|--------------------|--------|
| Engine precompute (vol_ma20) | `df['vol_ma20']` | `Indicators.add_volume_ma_column(df, period=20)` → real `df['volume'].rolling(20).mean()` | Yes | FLOWING |
| Engine precompute (vol_top_pct) | `df['vol_top_pct']` | `add_volume_percentile_column` → rolling(50).quantile(0.95) comparison | Yes | FLOWING |
| Daily loop vol inputs | `vol_above_ma20`, `vol_top_pct_val` | Read from row via `row['volume'] > row.get('vol_ma20', 0.0)` and `row.get('vol_top_pct', False)` | Yes | FLOWING |
| DD counter refined branch | `large_drop_dd`, `small_drop_dd` | Combines kwargs + config thresholds | Yes | FLOWING |
| Fixture baseline | `is_dd`, `dd_type`, `dd_count` | Generated by `HybridEngine(refined_dd_enabled=False).run(VN30 2015-2026)` via `scripts/generate_phase39_fixture.py` | Yes (110 real DDs from 2808 real trading days) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All Phase 39 tests pass | `uv run pytest tests/test_phase39_indicators.py tests/test_phase39_dd_logic.py tests/test_phase39_backward_compat.py -x -q` | 27 passed in 3.28s | PASS |
| Feature gate in refined=True direction: classic -0.2% rule does NOT fire | Inline Python: `MDMV2Config(refined_dd_enabled=True)` + drop=-0.003 + volume_up=True + vol kwargs=False → `is_dd=False` | Assertion passed ("classic path NOT fired when refined=True") | PASS |
| Feature gate in refined=False direction: refined vol kwargs ignored | Inline Python: `MDMV2Config(refined_dd_enabled=False)` + drop=-0.008 + volume_up=False + vol_above_ma20=True → `is_dd=False` | Assertion passed ("refined path NOT fired when refined=False") | PASS |
| Engine does NOT add vol columns when disabled | `HybridEngine(refined_dd_enabled=False).run(vn30)` | `vol_ma20` and `vol_top_pct` absent from result | PASS |
| Engine DOES add vol columns when enabled | `HybridEngine(refined_dd_enabled=True).run(vn30)` | Both columns present in result | PASS |
| Fixture integrity | `pd.read_parquet` + schema checks | 2808 rows × 4 cols, 110 DDs, dates 2015-01-05 → 2026-04-07 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DD-01 | 39-01 | DD detector accepts params (large_drop, small_drop, large_vol_rule, small_vol_percentile, small_vol_lookback) | SATISFIED | All 5 config fields (+ flag) in `MDMV2Config` lines 68-74; engine passes them through to `Indicators.add_volume_percentile_column` (engine lines 175-178). Hard-coded -0.2% replaced in refined path. |
| DD-02 | 39-02 | Dual-threshold rule: (drop >= large_drop AND vol > vol_ma20) OR (drop >= small_drop AND vol in top N%) | SATISFIED | `distribution_day.py` lines 69-78 implement OR of `large_drop_dd` and `small_drop_dd` branches. Tested by `test_refined_large_drop_hit`, `test_refined_small_drop_hit`, and 3 miss cases. |
| DD-03 | 39-01 + 39-02 | Config flag `refined_dd_enabled` toggles, falling back cleanly to classic -0.2% | SATISFIED | Flag defaults `False` (config.py 69); `distribution_day.py` line 65 branches; both presets ship disabled (156, 192). Bidirectional gate verified in spot-checks. |
| DD-04 | 39-03 | HybridEngine with refined_dd_enabled=False produces DD count sequence identical to v6.0 baseline on VN30 2015-2026 | SATISFIED | `test_refined_dd_disabled_matches_baseline` asserts byte-exact equality on 2808-row fixture (110 DDs). Fixture exists and test passed in live pytest run. Uses `pytest.fail` on missing asset (hard regression, no silent skip). |

No orphaned requirements — REQUIREMENTS.md maps exactly DD-01..DD-04 to Phase 39, and all 4 appear across plan frontmatter (39-01: DD-01, DD-03; 39-02: DD-02, DD-03; 39-03: DD-04).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | No TODO/FIXME/placeholder/stub patterns detected in `strategies/mdm_hybrid/*.py`. All new code is substantive. |

### Human Verification Required

None — all success criteria are programmatically testable and were exercised by the test suite plus live spot-checks.

### Gaps Summary

No gaps. Phase 39 achieved its goal: the hard-coded -0.2% Type 1 Distribution Day rule is replaced by a parameterized dual-threshold definition (large drop + MA20 volume OR small drop + top-percentile volume) that is exposed on `MDMV2Config` through 6 fields, gated behind `refined_dd_enabled` (default False, both presets disabled), and byte-identical to the v6.0 baseline on VN30 2015-2026 when the gate is off. All 27 Phase 39 tests pass. Feature gate is bidirectional: classic path cannot fire when refined is on, refined path cannot fire when refined is off. Documentation sync (`docs/rules_mdm_hybrid.md` Section XVII) is in place per the Code-Docs Sync Rule. Phase 40 (grid search) can consume this interface directly.

---

_Verified: 2026-04-16T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
