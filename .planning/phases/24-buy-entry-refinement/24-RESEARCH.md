# Phase 24: Buy Entry Refinement - Research

**Researched:** 2026-03-31
**Domain:** FTD buy signal filtering (gap-up invalidation + decline-severity-aware FTD timing)
**Confidence:** HIGH

## Summary

Phase 24 adds two buy-entry refinements to the MDM V2 engine: (1) gap-up invalidation that rejects FTD signals when the signal day's intraday low breaks below the previous day's close, and (2) a 6% decline-severity threshold that relaxes FTD timing requirements for shallow pullbacks while maintaining classic day-3+ rules for deep corrections.

Both features are well-scoped with clear decisions from CONTEXT.md. The existing codebase already provides all necessary data points (`prev_close`, `low`, `drawdown_pct`, `signal_type`, `rally_day`) in the engine loop, and the module/config pattern from Phase 21 (BuyFilter, BuyConfirmation) serves as a direct template. No new libraries, external dependencies, or architectural changes are needed.

**Primary recommendation:** Follow the BuyFilter module pattern exactly -- single `BuyEntryFilter` class in `strategies/mdm_v2/buy_entry.py`, config flags in MDMV2Config, engine integration after FTD detection alongside existing buy selectivity gates.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Gap-up filter applies ONLY to classic FTD signals. MA50 breakout and 52-week breakout bypass this filter (consistent with Phase 21 buy_filter scope).
- **D-02:** Gap-up "broken" defined as: signal day's intraday low < previous day's close. No additional conditions (no bearish candle check, no margin/buffer).
- **D-03:** Keep existing correction_threshold = -10% unchanged. The 6% rule is implemented as SEPARATE logic, not by modifying correction_threshold. User confirmed: lowering correction_threshold to -6% previously caused excessive noise.
- **D-04:** Use existing drawdown_pct (computed from rolling_high) for decline measurement. No new calculation needed.
- **D-05:** Rally tracker still requires correction phase (in_correction=True) to be active. The 6% rule does NOT bypass correction detection.
- **D-06:** When drawdown is between -6% and -10% (shallow pullback): engine bypasses rally_tracker's day count requirement and allows FTD check directly (no rally_day >= 4 requirement). When drawdown >= -10% (deep correction): use rally_tracker normally with day 3+ requirement.
- **D-07:** Single new module: `strategies/mdm_v2/buy_entry.py` containing a BuyEntryFilter class that handles both gap-up filter and rally threshold logic. Both are buy-entry refinements with simple logic -- separate modules would be overkill.
- **D-08:** New config fields in MDMV2Config: `gap_filter_enabled: bool = True`, `rally_threshold_enabled: bool = True`, `rally_threshold_pct: float = -0.06`
- **D-09:** Single validation script: `analysis/validate_buy_entry.py` running 3 A/B scenarios: baseline vs +gap_filter vs +rally_threshold vs +both.
- **D-10:** Gap filter success: must identify 3+ historical VN30 instances where filter would have prevented a losing trade, PLUS overall return comparison.
- **D-11:** Rally threshold success: verify shallow pullback recoveries captured faster (fewer whipsaw trades) AND deep correction entries still wait for proper follow-through.

### Claude's Discretion
- BuyEntryFilter class internal design (method signatures, state tracking)
- Exact integration point in engine run loop (after existing buy selectivity gates or before)
- Validation script output format and report structure
- Whether to log gap-filter/rally-threshold decisions in results DataFrame columns
- How to identify and report the 3+ historical gap-up instances in validation output

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GAP-01 | Invalidate buy signal when intraday low < previous day close (gap-up broken) | Engine has `low` and `prev_close` at line 138-139. BuyEntryFilter.check_gap() compares these values. Scope: FTD only (D-01). |
| GAP-02 | A/B backtest comparing V2 baseline vs V2+gap_filter on VN30 | Validation script pattern from `validate_buy_selectivity.py`. Config toggle: `gap_filter_enabled`. Must show 3+ prevented losing trades (D-10). |
| RALLY-01 | When VN30 declined < 6% from peak, FTD can trigger on any day (no day-3+ requirement) | Engine line 170 checks `rally_day >= 4`. Rally threshold logic bypasses this when `drawdown_pct > rally_threshold_pct` (D-06). Uses existing `drawdown_pct` from line 166. |
| RALLY-02 | When VN30 declined >= 6% from peak, FTD requires classic day-3+ timing | Default behavior preserved -- the `rally_day >= 4` check at line 170 stays for deep corrections (D-06). |
| RALLY-03 | A/B backtest comparing V2 baseline vs V2+rally_threshold on VN30 | Same validation script, separate scenario. Must show fewer whipsaw trades in shallow pullbacks and preserved deep-correction timing (D-11). |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations, results tracking | Already in use throughout engine |
| numpy | >= 1.24.0 | Numeric comparisons | Already in use for indicators |
| matplotlib | >= 3.7.0 | Equity curve charts in validation | Already used by validation scripts |
| pytest | >= 9.0.2 | Unit testing | Already configured in pyproject.toml |

No new libraries needed. All computation is simple float comparisons.

## Architecture Patterns

### Recommended Module Structure
```
strategies/mdm_v2/
  buy_entry.py          # NEW: BuyEntryFilter class (gap + rally threshold)
  config.py             # MODIFY: add 3 new config fields
  mdm_v2_engine.py      # MODIFY: integrate BuyEntryFilter in run loop
analysis/
  validate_buy_entry.py  # NEW: A/B validation script
docs/
  rules_mdm_v2.md       # MODIFY: update Section III with new rules
tests/
  test_buy_entry.py      # NEW: unit tests for BuyEntryFilter
```

### Pattern 1: BuyEntryFilter Module (per D-07)

**What:** Single class handling both gap-up invalidation and rally threshold logic.
**When to use:** Applied in the engine's run loop for every FTD signal candidate.

```python
# Source: Derived from existing buy_filter.py pattern
from .config import MDMV2Config


class BuyEntryFilter:
    """Buy entry refinement: gap-up invalidation and rally threshold."""

    def __init__(self, config: MDMV2Config):
        self.config = config

    def check_gap(self, signal_type: str, low: float, prev_close: float) -> bool:
        """Check if buy signal passes gap-up filter.

        Args:
            signal_type: "FTD", "MA50", or "52WEEK"
            low: Signal day's intraday low
            prev_close: Previous day's close

        Returns:
            True if signal is allowed, False if gap-up is broken (reject).
        """
        if not self.config.gap_filter_enabled:
            return True
        # MA50/52WEEK bypass gap filter (per D-01)
        if signal_type in ("MA50", "52WEEK"):
            return True
        # Gap-up broken: intraday low < previous close (per D-02)
        return low >= prev_close

    def should_allow_early_ftd(self, drawdown_pct: float) -> bool:
        """Check if FTD can trigger without day-3+ requirement.

        Args:
            drawdown_pct: Current drawdown from peak (negative value)

        Returns:
            True if shallow pullback (< 6%), allowing early FTD.
        """
        if not self.config.rally_threshold_enabled:
            return False
        # Shallow pullback: drawdown between 0% and -6%
        return drawdown_pct > self.config.rally_threshold_pct
```

### Pattern 2: Engine Integration Point

**What:** Insert gap-up check as a new gate after FTD detection; modify rally_day check to consult rally threshold.
**Key insight:** The gap filter fits naturally alongside existing buy gates (lines 204-249). The rally threshold modifies the FTD trigger condition at line 170.

```python
# In mdm_v2_engine.py run loop:

# MODIFIED: FTD detection with rally threshold (RALLY-01, RALLY-02)
if current_state in [V2MarketState.CASH, V2MarketState.SELL]:
    # Check if early FTD is allowed (shallow pullback)
    allow_early = (self.buy_entry_filter is not None
                   and self.buy_entry_filter.should_allow_early_ftd(drawdown_pct))

    if rally_day >= 4 or allow_early:
        is_ftd, signal = self.ftd_detector.check_ftd(
            rally_day, price_change_pct, volume_up, date, close
        )
        # ... existing signal handling

# NEW GATE: Gap-up filter (GAP-01, after FTD detection)
if is_ftd and self.buy_entry_filter is not None:
    if not self.buy_entry_filter.check_gap(signal_type, low, prev_close):
        is_ftd = False
        buy_rejected = True  # Reuse existing column
```

### Pattern 3: Config Integration (per D-08)

```python
# In config.py MDMV2Config:
# Buy Entry Refinement (v6.0, GAP-01, RALLY-01)
gap_filter_enabled: bool = True
rally_threshold_enabled: bool = True
rally_threshold_pct: float = -0.06
```

### Anti-Patterns to Avoid
- **Modifying correction_threshold:** User explicitly confirmed this caused excessive noise. The 6% logic must be a SEPARATE bypass, not a threshold change (D-03).
- **Applying gap filter to MA50/52WEEK breakouts:** These signals bypass ALL FTD-specific gates per established convention (D-01, consistent with Phase 21).
- **Bypassing correction detection for shallow pullbacks:** The rally tracker's `in_correction=True` is still required (D-05). Only the day-count requirement is relaxed.
- **Using state[i] instead of state[i-1]:** Critical bug pattern from project history -- equity formula must use previous state to avoid look-ahead bias.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drawdown calculation | Custom peak-to-trough logic | `Indicators.drawdown_from_peak()` + existing `drawdown_pct` column (line 166) | Already computed, tested, available in engine loop |
| A/B backtest framework | Custom comparison logic | Existing `validate_buy_selectivity.py` pattern with `compute_metrics()` | Proven pattern, handles equity calculation correctly |
| Config toggle pattern | Ad-hoc enable/disable | MDMV2Config dataclass with `_enabled: bool` fields | Consistent with 6+ existing feature toggles |

## Common Pitfalls

### Pitfall 1: Rally Threshold Bypassing Correction Detection
**What goes wrong:** Allowing FTD on any day regardless of whether the market is in correction, creating false buy signals during uptrends.
**Why it happens:** Misinterpreting D-06 as "allow FTD anytime when drawdown < 6%" without checking in_correction.
**How to avoid:** The `should_allow_early_ftd()` only affects the `rally_day >= 4` check. The engine still requires `current_state in [CASH, SELL]` and `in_correction == True` from rally_tracker.
**Warning signs:** Excessive buy signals during trending markets (more signals than baseline).

### Pitfall 2: FTD Min Rally Day Config Conflict
**What goes wrong:** The FTDSignalDetector.check_ftd() internally checks `ftd_min_rally_day <= rally_day_count <= ftd_max_rally_day` (line 59 of ftd_signal.py). Default `ftd_min_rally_day=3`. If rally_day is 1 or 2, check_ftd() will reject the signal even though the engine allowed it.
**Why it happens:** Two layers of day-count validation: engine (line 170) and detector (line 59).
**How to avoid:** When `allow_early` is True and rally_day < ftd_min_rally_day, either: (a) pass a modified rally_day to check_ftd, or (b) temporarily override the min check. Recommended: pass `max(rally_day, config.ftd_min_rally_day)` to satisfy the detector's range check, OR call check_ftd with the actual rally_day and ensure ftd_min_rally_day allows it. The simplest approach: check price/volume conditions directly when early FTD is allowed, bypassing the day-count guard in both engine AND detector.
**Warning signs:** Rally threshold is enabled but no early FTD signals ever trigger.

### Pitfall 3: Gap Filter on Confirmed FTD
**What goes wrong:** Gap filter runs on the confirmation day (Day N of BuyConfirmation window) instead of the original FTD signal day.
**Why it happens:** The FTD passes through BuyConfirmation before BUY is committed. By confirmation day, prev_close/low are different values.
**How to avoid:** Apply gap filter at the same point as other FTD gates -- on the FTD signal day itself, before the signal enters BuyConfirmation. The gate order should be: FTD detected -> Gap filter -> MA10/MA50 filter -> Confirmation window.
**Warning signs:** Gap filter never fires because it checks the wrong day's price data.

### Pitfall 4: Drawdown Measurement Scope
**What goes wrong:** Using `drawdown_pct` from rolling_high which includes the current bar's high, leading to an inconsistency where a new high resets drawdown to 0% mid-correction.
**Why it happens:** The rally_tracker.update_peak() is called at the start of process_day(), which can reset `in_correction` when a new high is made.
**How to avoid:** This is actually the correct behavior -- a new high means correction is over. But verify that `drawdown_pct` from `Indicators.drawdown_from_peak(close, rolling_high)` is consistent with rally_tracker's own correction detection. Both should agree on whether we're in a correction.
**Warning signs:** Drawdown shows -5% but rally tracker says not in correction, or vice versa.

### Pitfall 5: Validation Script Not Isolating Features
**What goes wrong:** Running all features ON vs all OFF doesn't show individual feature impact.
**Why it happens:** Gap filter and rally threshold may interact (e.g., rally threshold creates more FTD signals, gap filter removes some of them).
**How to avoid:** Run 4 configs as specified in D-09: baseline (both OFF), +gap_filter only, +rally_threshold only, +both. Compare each pair independently.
**Warning signs:** Combined result is worse than individual features, suggesting negative interaction.

## Code Examples

### Engine Init Wiring
```python
# In __init__:
self.buy_entry_filter = None
if self.config.gap_filter_enabled or self.config.rally_threshold_enabled:
    self.buy_entry_filter = BuyEntryFilter(self.config)

# In reset():
# BuyEntryFilter is stateless, no reset needed
```

### Validation Script Config Patterns
```python
# Source: Derived from analysis/validate_buy_selectivity.py pattern

def make_baseline_config():
    """V2 with buy entry refinements OFF."""
    return MDMV2Config(
        gap_filter_enabled=False,
        rally_threshold_enabled=False,
        sell_acceleration_enabled=True,
        buy_filter_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        name="baseline",
    )

def make_gap_only_config():
    """V2 + gap filter, no rally threshold."""
    return MDMV2Config(
        gap_filter_enabled=True,
        rally_threshold_enabled=False,
        sell_acceleration_enabled=True,
        buy_filter_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        name="gap_filter",
    )

def make_rally_only_config():
    """V2 + rally threshold, no gap filter."""
    return MDMV2Config(
        gap_filter_enabled=False,
        rally_threshold_enabled=True,
        rally_threshold_pct=-0.06,
        sell_acceleration_enabled=True,
        buy_filter_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        name="rally_threshold",
    )

def make_combined_config():
    """V2 + both refinements."""
    return MDMV2Config(
        gap_filter_enabled=True,
        rally_threshold_enabled=True,
        rally_threshold_pct=-0.06,
        sell_acceleration_enabled=True,
        buy_filter_enabled=True,
        buy_confirmation_enabled=True,
        fail_safe_enabled=True,
        name="combined",
    )
```

### Gap-Up Instance Identification
```python
# In validation script: find specific instances where gap filter prevented loss
def find_gap_filtered_instances(baseline_results, filtered_results, trades_baseline, trades_filtered):
    """Identify trades that baseline took but gap filter rejected.

    Compare FTD dates: find dates where baseline has is_ftd=True
    but filtered has buy_rejected=True (or is_ftd=False).
    Cross-reference with trade P&L to identify prevented losses.
    """
    baseline_ftds = baseline_results[baseline_results['is_ftd'] == True]
    filtered_rejected = filtered_results[filtered_results['buy_rejected'] == True]

    # Find matching dates where gap filter changed outcome
    gap_filtered_dates = set(filtered_rejected['date']) - set(
        filtered_results[filtered_results['is_ftd'] == True]['date']
    )
    # ... match with losing trades in baseline
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_buy_entry.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GAP-01 | Gap-up broken invalidates FTD | unit | `uv run pytest tests/test_buy_entry.py::TestGapFilter -x` | Wave 0 |
| GAP-01 | Gap-up filter bypassed for MA50/52WEEK | unit | `uv run pytest tests/test_buy_entry.py::TestGapFilter::test_bypass_ma50 -x` | Wave 0 |
| GAP-02 | A/B backtest gap filter vs baseline | smoke (script) | `uv run python analysis/validate_buy_entry.py` | Wave 0 |
| RALLY-01 | Shallow pullback allows early FTD | unit | `uv run pytest tests/test_buy_entry.py::TestRallyThreshold -x` | Wave 0 |
| RALLY-02 | Deep correction requires day-3+ | unit | `uv run pytest tests/test_buy_entry.py::TestRallyThreshold::test_deep_correction -x` | Wave 0 |
| RALLY-03 | A/B backtest rally threshold vs baseline | smoke (script) | `uv run python analysis/validate_buy_entry.py` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_buy_entry.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green + validation script passes before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_buy_entry.py` -- covers GAP-01, RALLY-01, RALLY-02
- [ ] `analysis/validate_buy_entry.py` -- covers GAP-02, RALLY-03

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FTD always requires day 4+ | Dr. K webinar: day-3+ only for >= 6% corrections | Post-2019 MDM update | Captures shallow pullback recoveries faster |
| No gap-up validation | Gap-up broken = false signal | Dr. K webinar | Reduces false entries after gap-up reversals |

## Open Questions

1. **FTD Detector Day-Count Double Check (Pitfall 2)**
   - What we know: Both engine (line 170) and FTDSignalDetector.check_ftd() (line 59) validate rally day range. `ftd_min_rally_day=3` in config.
   - What's unclear: When early FTD is allowed (rally_day could be 1 or 2), the detector will reject it.
   - Recommendation: Simplest fix -- when `allow_early` is True, call check_ftd with `rally_day_count=max(rally_day, config.ftd_min_rally_day)` to satisfy the detector's internal range check. This preserves the detector's max_rally_day upper bound while bypassing only the minimum. Alternative: duplicate the price/volume check inline (but this violates DRY).

2. **Interaction Between Gap Filter and BuyConfirmation**
   - What we know: Gate order matters. Currently: FTD -> BuyFilter (MA10/MA50) -> BuyConfirmation.
   - What's unclear: Should gap filter go before or after BuyFilter?
   - Recommendation: Place gap filter BEFORE BuyFilter (as the earliest gate), since gap-up broken is a fundamental invalidation. No point checking MA trend for a signal that's already invalidated by price action.

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_v2/mdm_v2_engine.py` -- engine run loop, FTD detection (lines 148-249)
- `strategies/mdm_v2/config.py` -- MDMV2Config with existing toggle patterns
- `strategies/mdm_v2/buy_filter.py` -- BuyFilter module pattern (direct template)
- `strategies/mdm_v2/buy_confirmation.py` -- BuyConfirmation stateful gate pattern
- `strategies/mdm_v2/rally_attempt.py` -- RallyAttemptTracker with correction detection
- `strategies/mdm_v2/ftd_signal.py` -- FTDSignalDetector with internal day-count validation
- `analysis/validate_buy_selectivity.py` -- A/B validation script pattern
- `tests/test_fail_safe.py` -- Unit test pattern for engine features
- `.planning/phases/24-buy-entry-refinement/24-CONTEXT.md` -- All locked decisions

### Secondary (MEDIUM confidence)
- Dr. K webinar rules on 6% threshold and gap-up invalidation (documented in CONTEXT.md specifics)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all existing
- Architecture: HIGH -- follows established BuyFilter/BuyConfirmation patterns exactly
- Pitfalls: HIGH -- identified from direct code inspection (double day-count check, gate ordering, confirmation interaction)
- Integration points: HIGH -- exact line numbers verified in engine source

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable -- internal project code, not external dependencies)
