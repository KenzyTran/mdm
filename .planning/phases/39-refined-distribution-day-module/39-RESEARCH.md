# Phase 39: Refined Distribution Day Module - Research

**Researched:** 2026-04-16
**Domain:** Distribution Day detection logic refactoring, feature-gated dual-threshold rule
**Confidence:** HIGH

## Summary

Phase 39 replaces the hard-coded `-0.2%` Type 1 Distribution Day threshold in `DistributionDayCounter` with a parameterized dual-threshold rule: (large_drop + volume > vol_ma20) OR (small_drop + top-percentile volume). The change is gated behind `refined_dd_enabled` (default False) in `MDMV2Config`, following the exact pattern established by Phase 38's `atr_buffer_enabled` flag. Two new indicator columns (`vol_ma20`, `vol_percentile_rank`) are precomputed in the engine pipeline when the feature is enabled.

The codebase is well-structured for this change. `DistributionDayCounter` already separates Type 1 and Type 2 detection into distinct methods. The engine's precompute block has a clear insertion point (after ATR buffer, before expiry filter). Phase 38's regression test pattern provides a direct template for the DD-04 backward-compatibility test.

**Primary recommendation:** Follow Phase 38 pattern exactly -- config fields + indicator precompute + branched detection logic + parquet fixture + pytest regression test.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Type 2 stalling DD runs in parallel with new dual-threshold rule. When refined_dd_enabled=True, all 3 DD sources count (large_drop rule, small_drop rule, Type 2 stalling). Type 2 logic unchanged.
- D-02: When refined_dd_enabled=False, fallback entirely to v6.0 logic (Type 1 uses -0.2% hard-code + volume_up, Type 2 unchanged). Ensures DD-04 backward-compat.
- D-03: Add precompute columns in Indicators: add_volume_ma_column(df, period=20) writes col vol_ma20, add_volume_percentile_column(df, lookback, percentile) writes col vol_percentile_rank. Compute before loop in engine pipeline, same pattern as add_atr_column.
- D-04: volume_up (volume > prev_volume) NOT changed -- still used for FTD, stop-loss, and Type 2 stalling DD. Dual-threshold rule uses vol_ma20 and vol_percentile_rank columns separately.
- D-05: When refined_dd_enabled=False, skip computing vol_ma20 and vol_percentile_rank to ensure no side-effects on other columns/state (protects DD-04).
- D-06: Defaults in MDMConfig: refined_dd_enabled=False, large_drop=-0.007 (-0.7%), small_drop=-0.004 (-0.4%), large_vol_rule='vol_ma20', small_vol_percentile=5 (top 5%), small_vol_lookback=50 (50 sessions).
- D-07: Both VN30_PRESET and NASDAQ_PRESET ship refined_dd_enabled=False (backward-compat).
- D-08: Only change WHAT counts as DD (definition), not HOW DDs are counted. 20-day rolling window, DD5 high tracking, and 5DD trigger in position_manager unchanged.
- D-09: DD count metrics naturally change when refined_dd_enabled=True -- Phase 40 sweep evaluates impact.
- D-10: Follow Phase 38 pattern: capture v6.0 DD baseline, save as tests/fixtures/phase39_v6_baseline_dd_sequence.parquet. Commit fixture to repo.
- D-11: Regression test pytest: load fixture + run HybridEngine with refined_dd_enabled=False, assert DD columns (is_dd, dd_type, dd_count_20d) match byte-identical.

### Claude's Discretion
- Exact method signatures and naming for add_volume_ma_column / add_volume_percentile_column
- How to organize logic in DistributionDayCounter (add new methods vs refactor is_distribution_day_type1)
- Test file and fixture format naming
- How to log when refined DD trigger fires vs classic DD (action string annotation)

### Deferred Ideas (OUT OF SCOPE)
- Sweep parameters for DD -- Phase 40
- DD count threshold tuning (dd_count_threshold param, currently hard-coded 5) -- out of scope
- Type 2 stalling threshold tuning (parameterize 0.1%, p_loc 0.2) -- deferred
- Export DD metrics to dashboard -- Phase 42
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DD-01 | DD detector accepts params (large_drop, small_drop, large_vol_rule, small_vol_percentile, small_vol_lookback) replacing hard-coded -0.2% | Config fields in MDMV2Config + branched logic in DistributionDayCounter.is_distribution_day_type1 |
| DD-02 | Dual-threshold rule: DD=True if (drop >= large_drop AND volume > vol_ma20) OR (drop >= small_drop AND volume in top small_vol_percentile% of small_vol_lookback recent days) | Two new Indicators columns (vol_ma20, vol_percentile_rank) + dual-branch check in DD counter |
| DD-03 | Config flag refined_dd_enabled to fallback to classic -0.2% rule when off | Boolean field in MDMV2Config, conditional precompute in engine, conditional branch in DD counter |
| DD-04 | Backward-compat: when refined_dd_enabled=False, DD count matches v6.0 baseline | Parquet fixture + pytest regression test following Phase 38 pattern exactly |
</phase_requirements>

## Architecture Patterns

### Integration Points Map

```
strategies/mdm_hybrid/
  config.py              # ADD: 6 new fields to MDMV2Config + update presets
  indicators.py          # ADD: add_volume_ma_column(), add_volume_percentile_column()
  distribution_day.py    # MODIFY: is_distribution_day_type1() dual-branch logic
  mdm_hybrid_engine.py   # ADD: precompute block for vol columns (gated)
docs/
  rules_mdm_hybrid.md    # UPDATE: DD definition section (Code-Docs Sync Rule)
tests/
  fixtures/phase39_v6_baseline_dd_sequence.parquet  # NEW: regression fixture
  test_phase39_backward_compat.py                    # NEW: regression test
```

### Pattern 1: Feature-Gate Toggle (from Phase 38)

**What:** Boolean config field gates new behavior; False = byte-identical to baseline.
**When to use:** Every A/B testable feature change.
**Existing example in codebase:**
```python
# config.py (Phase 38 pattern)
atr_buffer_enabled: bool = False          # Feature gate: off = v6.0 behavior

# engine.py (Phase 38 pattern)
if self.config.v2_config.atr_buffer_enabled:
    df = Indicators.add_violation_threshold_column(df, k=..., period=...)
```

### Pattern 2: Indicator Precompute Column (established pattern)

**What:** Static method on Indicators class adds column(s) to DataFrame before daily loop.
**Existing examples:** `add_atr_column`, `add_ma50_column`, `add_violation_threshold_column`
**Key convention:** Method returns df copy with new column(s). Called in engine's precompute block.

### Pattern 3: Regression Fixture (from Phase 38)

**What:** Parquet file capturing baseline signal/DD sequence. Pytest loads fixture, runs engine with feature disabled, asserts equality.
**Existing example:** `tests/fixtures/phase38_v6_baseline_signal_log.parquet` + `tests/test_phase38_backward_compat.py`
**Key details:**
- Fixture generated from VN30 2015-2026 data
- Test FAILS (not skips) if data file missing
- String columns use exact equality; floats use rtol=1e-5

### Anti-Patterns to Avoid
- **Modifying volume_up column:** This column is used by FTD, stop-loss, and Type 2 stalling DD. The new dual-threshold rule must use separate vol_ma20 and vol_percentile_rank columns.
- **Computing columns when feature disabled:** Per D-05, skip vol_ma20 and vol_percentile_rank computation entirely when refined_dd_enabled=False to avoid any side-effects.
- **Changing DD counting logic:** Per D-08, only the DD definition changes. Rolling window, DD5 high tracking, 5DD threshold are untouched.

## Code Examples

### 1. Config Fields to Add (MDMV2Config)

```python
# After atr_buffer_consecutive_days field, following Phase 38 pattern:

# Refined Distribution Day (Phase 39, DD-01/DD-03)
refined_dd_enabled: bool = False              # Feature gate: off = v6.0 behavior (DD-04)
refined_dd_large_drop: float = -0.007         # Large drop threshold (-0.7%)
refined_dd_small_drop: float = -0.004         # Small drop threshold (-0.4%)
refined_dd_large_vol_rule: str = 'vol_ma20'   # Volume comparison for large drops
refined_dd_small_vol_percentile: int = 5      # Top N% volume percentile
refined_dd_small_vol_lookback: int = 50       # Lookback window for percentile calc
```

Validation in `__post_init__`:
```python
if self.refined_dd_enabled:
    assert self.refined_dd_large_drop < 0, "large_drop must be negative"
    assert self.refined_dd_small_drop < 0, "small_drop must be negative"
    assert self.refined_dd_large_drop <= self.refined_dd_small_drop, "large_drop must be <= small_drop"
    assert 0 < self.refined_dd_small_vol_percentile <= 100, "percentile must be 1-100"
    assert self.refined_dd_small_vol_lookback > 0, "lookback must be positive"
```

### 2. Indicator Columns (indicators.py)

```python
@staticmethod
def add_volume_ma_column(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Add volume moving average column.

    Args:
        df: DataFrame with 'volume' column.
        period: MA lookback period (default 20).

    Returns:
        DataFrame with 'vol_ma20' column added.
    """
    df = df.copy()
    df['vol_ma20'] = df['volume'].rolling(window=period, min_periods=1).mean()
    return df

@staticmethod
def add_volume_percentile_column(
    df: pd.DataFrame, lookback: int = 50, percentile: int = 5
) -> pd.DataFrame:
    """Add volume percentile rank column.

    For each row, computes whether the volume is in the top `percentile`%
    of the last `lookback` trading days. Result is boolean.

    Args:
        df: DataFrame with 'volume' column.
        lookback: Rolling window size (default 50).
        percentile: Top N percent threshold (default 5 = top 5%).

    Returns:
        DataFrame with 'vol_top_pct' boolean column added.
    """
    df = df.copy()
    threshold_quantile = 1.0 - (percentile / 100.0)  # top 5% = 95th percentile
    rolling_threshold = df['volume'].rolling(window=lookback, min_periods=1).quantile(threshold_quantile)
    df['vol_top_pct'] = df['volume'] >= rolling_threshold
    return df
```

### 3. Dual-Threshold Branch in DistributionDayCounter

```python
def is_distribution_day_type1(
    self,
    price_change_pct: float,
    volume_up: bool,
    vol_above_ma20: bool = False,
    vol_top_pct: bool = False,
) -> bool:
    """Check Type 1 DD with optional dual-threshold rule.

    When refined_dd_enabled=False (default): classic rule (drop <= -0.2% AND volume_up).
    When refined_dd_enabled=True: dual-threshold rule:
      - Large drop path: drop <= large_drop AND volume > vol_ma20
      - Small drop path: drop <= small_drop AND volume in top percentile
    """
    if not self.config.refined_dd_enabled:
        # Classic v6.0 rule (DD-04 backward-compat)
        return (price_change_pct <= self.config.dd_price_drop_threshold) and volume_up

    # Refined dual-threshold rule (DD-02)
    large_drop_dd = (
        price_change_pct <= self.config.refined_dd_large_drop
        and vol_above_ma20
    )
    small_drop_dd = (
        price_change_pct <= self.config.refined_dd_small_drop
        and vol_top_pct
    )
    return large_drop_dd or small_drop_dd
```

### 4. Engine Precompute Block

```python
# In HybridEngine.run(), after ATR buffer block, before expiry filter:

# Refined DD volume columns (Phase 39, DD-01/DD-02)
# Only when enabled -- D-05: no side effects when disabled (protects DD-04)
if self.config.v2_config.refined_dd_enabled:
    df = Indicators.add_volume_ma_column(df, period=20)
    df = Indicators.add_volume_percentile_column(
        df,
        lookback=self.config.v2_config.refined_dd_small_vol_lookback,
        percentile=self.config.v2_config.refined_dd_small_vol_percentile,
    )
```

### 5. Engine Daily Loop DD Check (modified call)

```python
# In the daily loop, when checking DD in BUY state:
if current_state == V2MarketState.BUY:
    # Prepare refined DD inputs (only meaningful when enabled)
    vol_above_ma20 = False
    vol_top_pct = False
    if self.config.v2_config.refined_dd_enabled:
        vol_above_ma20 = row['volume'] > row.get('vol_ma20', 0)
        vol_top_pct = bool(row.get('vol_top_pct', False))

    is_dd, dd_type = self.dd_counter.check_distribution_day(
        date, high, price_change_pct, volume_up, p_loc,
        vol_above_ma20=vol_above_ma20,
        vol_top_pct=vol_top_pct,
    )
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rolling percentile | Manual loop computing percentile over window | `pd.Series.rolling().quantile()` | Vectorized, handles edge cases (min_periods), battle-tested |
| Volume MA | Manual accumulator in daily loop | `pd.Series.rolling().mean()` | Same pattern as existing `add_ma50_column`, consistent |
| Parquet fixture I/O | CSV or pickle | `pd.read_parquet` / `df.to_parquet` | Already used by Phase 38 fixture, preserves dtypes exactly |

## Common Pitfalls

### Pitfall 1: Expiry Day Interaction with Refined DD
**What goes wrong:** VN30 expiry days have volume_up overridden to False (line 179 of engine). But the refined DD rule uses vol_ma20 and vol_top_pct, not volume_up. So refined DD could fire on expiry days even though classic DD is suppressed.
**Why it happens:** The expiry filter targets volume_up specifically, but the new rule bypasses that column.
**How to avoid:** When refined_dd_enabled=True AND is_expiry_day=True, suppress vol_above_ma20 and vol_top_pct to False (same spirit as existing expiry filter). Add this in the daily loop, not in the precompute.
**Warning signs:** DD count spikes on third Thursdays of each month.

### Pitfall 2: Rolling Quantile NaN on Early Rows
**What goes wrong:** `pd.Series.rolling(window=50).quantile(0.95)` returns NaN for the first 49 rows (when min_periods=50).
**Why it happens:** Not enough data in the lookback window.
**How to avoid:** Use `min_periods=1` (consistent with all other rolling indicators in the codebase -- see add_ma50_column, add_atr_column). This means early rows use whatever data is available.
**Warning signs:** vol_top_pct is NaN or always False in early period.

### Pitfall 3: Fixture Column Mismatch
**What goes wrong:** Phase 38 fixture stores state/transition/ma50/close. Phase 39 fixture needs DD-specific columns (is_dd, dd_type, dd_count_20d). Using the wrong columns breaks the regression test.
**Why it happens:** Copy-paste from Phase 38 test without adjusting columns.
**How to avoid:** Explicitly define COLS = ['date', 'is_dd', 'dd_type', 'dd_count_20d'] for the Phase 39 fixture. The regression test asserts these DD columns specifically.

### Pitfall 4: check_distribution_day Signature Change Breaking Type 2
**What goes wrong:** Adding vol_above_ma20 and vol_top_pct params to check_distribution_day could break callers.
**Why it happens:** check_distribution_day calls both is_distribution_day_type1 and is_distribution_day_type2.
**How to avoid:** Add new params with defaults (vol_above_ma20=False, vol_top_pct=False) to maintain backward-compatible signature. Type 2 does not use these params.

### Pitfall 5: Validation Assertions When Feature Disabled
**What goes wrong:** If __post_init__ always validates refined_dd params, creating a config with refined_dd_enabled=False but default values would fail if defaults don't pass validation.
**Why it happens:** Over-eager validation.
**How to avoid:** Only validate refined_dd params when refined_dd_enabled=True (as shown in code example above).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_phase39_backward_compat.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DD-01 | Config accepts refined DD params | unit | `uv run pytest tests/test_phase39_backward_compat.py::test_config_refined_dd_params -x` | Wave 0 |
| DD-02 | Dual-threshold rule fires correctly | unit | `uv run pytest tests/test_phase39_backward_compat.py::test_refined_dd_dual_threshold -x` | Wave 0 |
| DD-03 | refined_dd_enabled toggle works | unit | `uv run pytest tests/test_phase39_backward_compat.py::test_refined_dd_toggle -x` | Wave 0 |
| DD-04 | Backward-compat: disabled matches v6.0 | regression | `uv run pytest tests/test_phase39_backward_compat.py::test_refined_dd_disabled_matches_baseline -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_phase39_backward_compat.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `tests/test_phase39_backward_compat.py` -- regression test + unit tests for DD-01..DD-04
- [ ] `tests/fixtures/phase39_v6_baseline_dd_sequence.parquet` -- baseline fixture generation script/one-shot
- [ ] No new framework install needed (pytest already configured)

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_hybrid/distribution_day.py` -- existing DD counter, Type 1/Type 2 separation, check_distribution_day interface
- `strategies/mdm_hybrid/config.py` -- MDMV2Config dataclass, VN30_PRESET/NASDAQ_PRESET, Phase 38 atr_buffer_* fields as template
- `strategies/mdm_hybrid/indicators.py` -- all add_*_column patterns, especially add_atr_column and add_violation_threshold_column
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` -- precompute block (lines 143-179), DD check in daily loop (lines 286-301), expiry filter (lines 176-179)
- `tests/test_phase38_backward_compat.py` -- regression test template (fixture loading, exact equality, COLS pattern)
- `.planning/phases/39-refined-distribution-day-module/39-CONTEXT.md` -- all locked decisions D-01 through D-11

### Secondary (MEDIUM confidence)
- `docs/rules_mdm_hybrid.md` -- current DD documentation that needs updating (Code-Docs Sync Rule)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pure Python/pandas, no new dependencies
- Architecture: HIGH -- follows established Phase 38 pattern exactly, all integration points identified in code
- Pitfalls: HIGH -- expiry day interaction and rolling quantile edge cases verified against actual codebase

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable -- internal codebase patterns, no external dependencies)
