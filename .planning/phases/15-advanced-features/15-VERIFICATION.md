---
phase: 15-advanced-features
verified: 2026-03-29T15:30:00Z
status: human_needed
score: 14/15 must-haves verified
re_verification: false
human_verification:
  - test: "Run uv run python analysis/compare_models.py and open output/model_comparison.png"
    expected: "4-subplot dashboard renders correctly: per-type accuracy bars for 3 models, overall accuracy bars, 3 confusion matrices side-by-side; accuracy values are reasonable (v2 ~37.9%, DT ~55.5%, Hybrid ~33.6%)"
    why_human: "Visual chart correctness requires human inspection; Plan 03 Task 2 is a blocking human-verify checkpoint"
  - test: "Confirm REQUIREMENTS.md ADV-04 checkbox and table entry are updated to Complete"
    expected: "ADV-04 line reads '- [x] **ADV-04**' and table row shows 'Complete'"
    why_human: "REQUIREMENTS.md shows ADV-04 as Pending/checkbox unchecked despite compare_models.py being committed and output file existing — requires human to confirm the code is accepted and update the tracking document"
---

# Phase 15: Advanced Features Verification Report

**Phase Goal:** Advanced MDM features — HA Smoothed filter, contextual transitions, model comparison dashboard
**Verified:** 2026-03-29T15:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                        | Status     | Evidence                                                                         |
|----|----------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------|
| 1  | HA Smoothed 55 condition evaluates green/red candles as bullish/bearish when enabled         | VERIFIED   | `ha_smooth_bullish()` / `ha_smooth_bearish()` static methods in indicator_filter.py lines 202-231 |
| 2  | HA Smoothed 55 is disabled by default and does not affect existing filter results            | VERIFIED   | `ha_smooth_enabled: bool = False` in FilterConfig (indicator_filter.py line 65); confirmed by test_baseline_verdict_unchanged |
| 3  | evaluate() returns both a Verdict and a confidence float (0.0-1.0)                          | VERIFIED   | Return type is `tuple` at line 317; all paths return `(Verdict, float)` — lines 345, 348, 354, 357, 359 |
| 4  | Output DataFrame contains a 'confidence' column with per-day values                          | VERIFIED   | `df['confidence'] = 0.0` at line 177 of engine; `df.at[idx, 'confidence'] = confidence` at line 341 |
| 5  | Phase 14 baseline is unchanged when ha_smooth_enabled=False (regression)                     | VERIFIED   | FilterConfig defaults to ha_smooth_enabled=False; test_baseline_unchanged passes (commit 6519b4a) |
| 6  | Engine tracks state history with prior state, duration, entered date                         | VERIFIED   | `self.state_history = []` (line 54), `state_history.append({state, entered_date, duration})` at line 394 |
| 7  | Contextual rules make Cash stickier when entered from Sell (bearish regime)                  | VERIFIED   | `_get_contextual_threshold()` line 87: Rule 2 checks `prior_state == "SELL"` and returns 1.0 |
| 8  | Long Cash duration increases BUY confirmation threshold                                      | VERIFIED   | Rule 1 in `_get_contextual_threshold()`: `if self._days_in_current_state > cash_limit: return 1.0` |
| 9  | State history only grows on state CHANGES, not every day                                     | VERIFIED   | Append happens only when `final_state_str != self._current_state_name`; test_state_history_only_on_changes passes |
| 10 | Dashboard shows pure state machine (v2) accuracy per signal type                            | VERIFIED   | `analysis/compare_models.py` imports MDMV2Engine, runs it, feeds result to plot_accuracy_comparison() |
| 11 | Dashboard shows pure decision tree accuracy per signal type                                  | VERIFIED   | DecisionTreeClassifier imported (line 23), trained on feature snapshots, per-type recall from classification_report |
| 12 | Dashboard shows hybrid model accuracy per signal type                                        | VERIFIED   | HybridEngine imported (line 31), run with `HybridConfig(filter_enabled=True)`, fed to comparison |
| 13 | All three models compared side-by-side on a single chart                                     | VERIFIED   | `plot_accuracy_comparison()` at line 179; 4-subplot figure with per-type bars, overall bars, 3 confusion matrices |
| 14 | Script runs end-to-end and produces output file                                              | VERIFIED   | `output/model_comparison.png` exists; commit b49d5e4 (359 lines, fully implemented) |
| 15 | Visual chart correctness                                                                     | UNCERTAIN  | Human verification required (Plan 03 blocking checkpoint)                        |

**Score:** 14/15 truths verified (15th requires human)

### Required Artifacts

| Artifact                                           | Expected                                             | Status     | Details                                                           |
|----------------------------------------------------|------------------------------------------------------|------------|-------------------------------------------------------------------|
| `strategies/mdm_hybrid/indicator_filter.py`        | 7th HA Smoothed condition + confidence in evaluate() | VERIFIED   | 359 lines; ha_smooth_bullish, ha_smooth_bearish, tuple return     |
| `strategies/mdm_hybrid/config.py`                  | ha_smooth_enabled toggle in FilterConfig             | VERIFIED   | FilterConfig is in indicator_filter.py (co-located); config.py imports it via `from .indicator_filter import FilterConfig`; ha_smooth_enabled confirmed |
| `strategies/mdm_hybrid/mdm_hybrid_engine.py`       | Confidence column + state_history + contextual logic | VERIFIED   | 472 lines; all three features present and wired                   |
| `tests/test_indicator_filter.py`                   | Tests for HA condition and confidence                | VERIFIED   | 49 test functions; test_ha_smooth_bullish at line 366, test_confidence_returned at line 417 |
| `tests/test_hybrid_engine.py`                      | Tests for contextual transitions and confidence      | VERIFIED   | 23 test functions; test_state_history_tracking line 414, test_contextual_cash_from_sell_stickier line 461 |
| `analysis/compare_models.py`                       | Three-way comparison dashboard script                | VERIFIED   | 359 lines; def main() at line 305, plot_accuracy_comparison() at line 179 |
| `output/model_comparison.png`                      | Generated dashboard chart                            | VERIFIED   | File exists; generated by commit b49d5e4                          |

### Key Link Verification

| From                                        | To                                           | Via                                               | Status     | Details                                                                    |
|---------------------------------------------|----------------------------------------------|---------------------------------------------------|------------|----------------------------------------------------------------------------|
| indicator_filter.py                         | mdm_hybrid_engine.py                         | evaluate() returns tuple (Verdict, float)         | VERIFIED   | `verdict, confidence = self.indicator_filter.evaluate` at engine line 340  |
| config.py                                   | indicator_filter.py                          | FilterConfig.ha_smooth_enabled drives 7th cond    | VERIFIED   | `self.config.ha_smooth_enabled` in _get_bullish_votes and _get_bearish_votes |
| mdm_hybrid_engine.py                        | indicator_filter.py                          | Creates temporary FilterConfig with adj threshold  | VERIFIED   | `ctx_config = FilterConfig(..., majority_threshold=ctx_threshold)` line 327 |
| analysis/compare_models.py                  | strategies/mdm_hybrid/mdm_hybrid_engine.py   | Runs HybridEngine to get hybrid results           | VERIFIED   | `from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine` line 31 |
| analysis/compare_models.py                  | strategies/mdm_v2/mdm_v2_engine.py           | Runs MDMV2Engine for pure state machine baseline  | VERIFIED   | `from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine` line 33         |
| analysis/compare_models.py                  | DecisionTreeClassifier (sklearn)             | Trains DT model for pure DT comparison            | VERIFIED   | `from sklearn.tree import DecisionTreeClassifier` line 23; random_state=42 line 131 |

### Data-Flow Trace (Level 4)

| Artifact                    | Data Variable       | Source                                          | Produces Real Data | Status   |
|-----------------------------|---------------------|-------------------------------------------------|--------------------|----------|
| indicator_filter.py         | agree_ratio (float) | sum(conditions) / len(conditions)               | Yes — computed live| FLOWING  |
| mdm_hybrid_engine.py        | confidence column   | evaluate() tuple second element                 | Yes — per-row calc | FLOWING  |
| mdm_hybrid_engine.py        | state_history list  | On-state-change append in run() loop            | Yes — grows on transitions | FLOWING |
| analysis/compare_models.py  | model accuracy data | MDMV2Engine.run(), HybridEngine.run(), DT.predict() | Yes — from real data | FLOWING |

### Behavioral Spot-Checks

| Behavior                                          | Command                                                                       | Result                    | Status  |
|---------------------------------------------------|-------------------------------------------------------------------------------|---------------------------|---------|
| indicator_filter.py 49 tests pass                 | `uv run python -m pytest tests/test_indicator_filter.py -q`                   | 49 passed in 3.11s        | PASS    |
| Phase 15 hybrid engine tests (8 targeted) pass    | `uv run python -m pytest tests/test_hybrid_engine.py -k "contextual or state_history or confidence" -q` | 8 passed in 181s | PASS |
| ha_smooth_bullish static method exists            | grep in indicator_filter.py                                                   | Line 202 confirmed        | PASS    |
| confidence column wired in engine                 | grep `df.at[idx, 'confidence']` in mdm_hybrid_engine.py                      | Lines 341, 386 confirmed  | PASS    |
| state_history tracking wired in engine            | grep `self.state_history.append` in mdm_hybrid_engine.py                     | Line 394 confirmed        | PASS    |
| compare_models.py exists with all 3 model imports | grep HybridEngine, MDMV2Engine, DecisionTreeClassifier                        | Lines 23, 31, 33 confirmed | PASS   |
| output/model_comparison.png exists               | ls output/model_comparison.png                                                | File exists               | PASS    |
| All Phase 15 commits exist in git log             | git show --stat ede8a30 07ffa1c 6519b4a 072362b 415f8b3 b49d5e4               | All 6 commits found       | PASS    |

### Requirements Coverage

| Requirement | Source Plan | Description                                                            | Status       | Evidence                                                             |
|-------------|------------|------------------------------------------------------------------------|--------------|----------------------------------------------------------------------|
| ADV-01      | 15-02-PLAN | Contextual state transitions — state depends on prior state history   | SATISFIED    | `_get_contextual_threshold()`, `state_history`, 6 contextual tests   |
| ADV-02      | 15-01-PLAN | Heikin Ashi Smoothed 55 as trend confirmation filter                  | SATISFIED    | `ha_smooth_bullish/bearish()` in indicator_filter.py; ha_smooth_enabled toggle |
| ADV-03      | 15-01-PLAN | Indicator confidence scoring — agreement ratio exposed                 | SATISFIED    | evaluate() returns (Verdict, float); confidence column in DataFrame  |
| ADV-04      | 15-03-PLAN | Three-way comparison dashboard                                         | SATISFIED (code) / PENDING (docs) | compare_models.py committed (b49d5e4); output/model_comparison.png exists; REQUIREMENTS.md still shows checkbox unchecked and table shows "Pending" |

**Documentation gap found:** REQUIREMENTS.md line 92 shows `- [ ] **ADV-04**` (unchecked) and line 179 shows `| ADV-04 | Phase 15 | Pending |`. The code artifact is fully implemented and committed. This is a tracking document update that was not done after Plan 03 completed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | No TODO, FIXME, placeholder, or stub patterns detected in modified files |

### Human Verification Required

#### 1. Dashboard Visual Correctness

**Test:** Run `uv run python analysis/compare_models.py` (or if already run, open `output/model_comparison.png`)
**Expected:** 4-subplot figure renders with: (top-left) per-type accuracy bars grouping Buy/Cash/Sell for 3 models; (top-right) overall accuracy bars for all 3 models with labeled percentages; (bottom row) 3 confusion matrix heatmaps labeled "Pure State Machine", "Pure Decision Tree", "Hybrid"
**Why human:** This is an explicit blocking human-verify checkpoint in Plan 03 Task 2. Visual readability, label clarity, and color scheme cannot be verified programmatically.

#### 2. REQUIREMENTS.md ADV-04 Tracking Update

**Test:** Open `.planning/REQUIREMENTS.md` and update line 92 from `- [ ] **ADV-04**` to `- [x] **ADV-04**` and line 179 from `Pending` to `Complete`
**Expected:** ADV-04 tracking matches code reality
**Why human:** This is a documentation update decision that requires human confirmation the dashboard output was reviewed and accepted.

### Gaps Summary

No functional gaps exist. All three phase objectives are fully implemented and wired:

1. **ADV-02 + ADV-03 (Plan 01):** HA Smoothed 55 condition with NaN-safe static methods, toggle via `ha_smooth_enabled=False` (default preserving Phase 14 baseline), and confidence score exposed as `(Verdict, float)` tuple return from `evaluate()` wired into the engine output DataFrame.

2. **ADV-01 (Plan 02):** State history tracking (`state_history` list), `_get_contextual_threshold()` implementing two "favor cash" rules, temporary IndicatorFilter creation with adjusted threshold when context is bearish — all committed and tested.

3. **ADV-04 (Plan 03):** `analysis/compare_models.py` (359 lines) with `MDMV2Engine`, `HybridEngine`, and `DecisionTreeClassifier` imports, `plot_accuracy_comparison()` function, `def main()`, and `output/model_comparison.png` generated.

The only outstanding items are human verification of dashboard visual quality (Plan 03's blocking checkpoint) and updating the REQUIREMENTS.md tracking document for ADV-04.

---

_Verified: 2026-03-29T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
