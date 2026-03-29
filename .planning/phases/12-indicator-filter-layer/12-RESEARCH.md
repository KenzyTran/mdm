# Phase 12: Indicator Filter Layer - Research

**Researched:** 2026-03-29
**Domain:** Python dataclass design, boolean indicator evaluation, enum-based verdict pattern
**Confidence:** HIGH

## Summary

Phase 12 creates a stateless `IndicatorFilter` class with boolean condition methods derived from Phase 9 rule discovery, a `FilterConfig` dataclass with per-condition toggles, and a `Verdict` enum (CONFIRM/VETO/OVERRIDE). The class evaluates a DataFrame row against configured conditions using majority voting to produce a typed verdict. This phase does NOT wire the filter into the hybrid engine pipeline (Phase 13 scope).

The implementation is straightforward: all indicator computation already exists in `core/indicators.py`, all boolean feature definitions already exist in `core/feature_snapshot.py` (lines 106-113), and the config composition pattern is established in `strategies/mdm_hybrid/config.py`. The primary technical risk is TradingView parity verification -- confirming that `adjust=False` EMA and standard MACD (12,26,9) match TradingView outputs at known dates.

**Primary recommendation:** Follow the established dataclass + static method patterns from the hybrid package. Reuse boolean condition definitions verbatim from `feature_snapshot.py`. Create the TradingView reference CSV as a test fixture, not a runtime dependency.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Source conditions from Phase 9 decision tree discovered rules -- evidence-backed from 962 signals, not hardcoded domain knowledge.
- **D-02:** Implement 5-6 boolean condition methods: `close_above_ema55`, `macd_histogram_positive`, `ema9_above_ema21`, `close_above_ma200`, `close_above_ema9`, `macd_above_signal`.
- **D-03:** Default active conditions: only 3 (close_above_ema55, macd_histogram_positive, ema9_above_ema21) -- the top-importance features from Phase 9. Remaining conditions implemented but disabled by default, configurable via FilterConfig toggles.
- **D-04:** Max 2-3 active rules enforced to avoid overfitting on 95 post-2019 signals (per STATE.md concern).
- **D-05:** Majority voting -- count active conditions that agree. >=2/3 (or configurable threshold) of active conditions must agree for CONFIRM, otherwise VETO.
- **D-06:** Verdict logic differs per proposal type: Buy proposals check bullish conditions (EMA stack up, MACD positive). Sell proposals check bearish conditions (inverted). Matches Phase 9 finding that Buy/Sell have different indicator patterns.
- **D-07:** OVERRIDE implemented in Phase 12 (not deferred to Phase 13). When all active indicators strongly contradict the state machine proposal, the filter can suggest an override signal. Verdict enum: CONFIRM, VETO, OVERRIDE.
- **D-08:** 10+ reference dates with EMA/MACD values exported from TradingView, saved as CSV reference file in `data/reference/` or `tests/fixtures/`.
- **D-09:** Automated unit test reads CSV reference, computes indicators via `core/indicators.py`, compares with tolerance: +/-0.01% for EMA/MA values, +/-0.1% for MACD values.
- **D-10:** `core/indicators.py` already uses `adjust=False` matching TradingView convention -- parity check validates this assumption holds.
- **D-11:** New `FilterConfig` dataclass with boolean toggles per condition (ema55_enabled=True, macd_enabled=True, ema9_21_enabled=True, ma200_enabled=False, ema9_enabled=False, macd_signal_enabled=False) plus `majority_threshold: float = 0.67`.
- **D-12:** HybridConfig composes FilterConfig via `filter_config: FilterConfig` field, same composition pattern as `v2_config: MDMV2Config`.
- **D-13:** IndicatorFilter class lives in `strategies/mdm_hybrid/indicator_filter.py` -- part of hybrid package, not core/.

### Claude's Discretion
- Exact method signatures and parameter naming for condition methods
- How to pass indicator data to IndicatorFilter (DataFrame row vs individual values)
- Internal helper structure for bullish vs bearish condition evaluation
- Test file organization and pytest fixture design
- CSV reference file format and date selection strategy for TradingView parity
- Whether majority_threshold uses fraction (0.67) or count (2 of 3)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HYB-02 | Indicator filter layer using EMA 9/21/55, MACD, MA 200 to confirm or veto signals from state machine | All 6 boolean conditions defined in D-02 map directly to existing `feature_snapshot.py` patterns. FilterConfig (D-11) + IndicatorFilter.evaluate() (D-05/D-06/D-07) + TradingView parity (D-08/D-09/D-10) fully cover this requirement. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >=2.0.0 | DataFrame row access for indicator values | Already in project dependencies |
| numpy | >=1.24.0 | NaN handling in indicator comparisons | Already in project dependencies |
| pytest | 9.0.2 | Unit testing for conditions and verdicts | Already configured as dev dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| enum (stdlib) | builtin | Verdict enum (CONFIRM/VETO/OVERRIDE) | Verdict type definition |
| dataclasses (stdlib) | builtin | FilterConfig dataclass | Config with toggles and threshold |

No new dependencies required. Everything uses existing project stack.

## Architecture Patterns

### Recommended File Structure
```
strategies/mdm_hybrid/
    indicator_filter.py    # NEW: FilterConfig, Verdict, IndicatorFilter
    config.py              # MODIFIED: add filter_config field to HybridConfig
tests/
    test_indicator_filter.py   # NEW: unit tests for filter
    fixtures/
        tradingview_reference.csv  # NEW: TradingView parity data
```

### Pattern 1: Verdict Enum
**What:** Simple string enum for typed verdict returns.
**When to use:** Every call to `IndicatorFilter.evaluate()`.
**Example:**
```python
# Source: established V2MarketState pattern in position_manager.py
from enum import Enum

class Verdict(Enum):
    CONFIRM = "CONFIRM"
    VETO = "VETO"
    OVERRIDE = "OVERRIDE"
```

### Pattern 2: FilterConfig Dataclass with Toggles
**What:** Dataclass with boolean toggle per condition and a majority threshold.
**When to use:** Configuring which conditions are active and how many must agree.
**Example:**
```python
# Source: HybridConfig/MDMV2Config composition pattern in config.py
from dataclasses import dataclass

@dataclass
class FilterConfig:
    # Active by default (top-3 from Phase 9 importance)
    ema55_enabled: bool = True
    macd_enabled: bool = True
    ema9_21_enabled: bool = True
    # Implemented but disabled by default
    ma200_enabled: bool = False
    ema9_enabled: bool = False
    macd_signal_enabled: bool = False
    # Voting threshold
    majority_threshold: float = 0.67

    def __post_init__(self):
        assert 0.0 < self.majority_threshold <= 1.0
        active = sum([self.ema55_enabled, self.macd_enabled,
                      self.ema9_21_enabled, self.ma200_enabled,
                      self.ema9_enabled, self.macd_signal_enabled])
        # D-04: warn or enforce max 2-3 active
```

### Pattern 3: Stateless Boolean Condition Methods
**What:** Each condition is a standalone method taking a DataFrame row, returning bool.
**When to use:** Individual condition evaluation, unit testing each condition independently.
**Example:**
```python
# Source: feature_snapshot.py lines 106-113
class IndicatorFilter:
    def __init__(self, config: FilterConfig = None):
        self.config = config or FilterConfig()

    @staticmethod
    def close_above_ema55(row) -> bool:
        """Close price above EMA 55."""
        return bool(row['close'] > row['ema55'])

    @staticmethod
    def macd_histogram_positive(row) -> bool:
        """MACD histogram is positive."""
        return bool(row['macd_histogram'] > 0)

    @staticmethod
    def ema9_above_ema21(row) -> bool:
        """EMA 9 above EMA 21 (bullish stack)."""
        return bool(row['ema9'] > row['ema21'])
```

### Pattern 4: Proposal-Aware Verdict Evaluation
**What:** evaluate() checks bullish conditions for Buy proposals, bearish (inverted) for Sell proposals.
**When to use:** The main entry point called by the hybrid engine (Phase 13 wiring).
**Example:**
```python
def evaluate(self, row, proposal: str, current_state) -> Verdict:
    """Evaluate indicator conditions against a proposed signal.

    Args:
        row: DataFrame row with indicator columns (ema9, ema21, ema55, etc.)
        proposal: Proposed signal type ("BUY", "SELL", "CASH")
        current_state: Current V2MarketState

    Returns:
        Verdict: CONFIRM, VETO, or OVERRIDE
    """
    if proposal == "BUY":
        conditions = self._get_bullish_votes(row)
    elif proposal in ("SELL", "CASH"):
        conditions = self._get_bearish_votes(row)
    else:
        return Verdict.CONFIRM  # no opinion on unknown proposals

    active_count = len(conditions)
    if active_count == 0:
        return Verdict.CONFIRM

    agree_count = sum(conditions)
    agree_ratio = agree_count / active_count

    # All active conditions strongly disagree -> OVERRIDE
    if agree_ratio == 0.0:
        return Verdict.OVERRIDE

    if agree_ratio >= self.config.majority_threshold:
        return Verdict.CONFIRM
    else:
        return Verdict.VETO
```

### Pattern 5: Row-Based Input (Recommended Discretion Choice)
**What:** Pass a pandas Series (DataFrame row) to evaluate(), not individual values.
**Why:** Matches existing engine pattern where `row = df.iloc[idx]` is already available at line 135 of `mdm_hybrid_engine.py`. Avoids parameter explosion. The row must contain indicator columns (ema9, ema21, ema55, ma200, macd, macd_signal, macd_histogram) which are added by `build_indicator_dataframe()`.
**Implication for Phase 13:** The hybrid engine must call `build_indicator_dataframe()` on the OHLCV data (or add those columns) before the daily loop. Currently it only adds v2-style indicators (MA10, MA50, etc.) but not EMA/MACD.

### Anti-Patterns to Avoid
- **Stateful filter:** IndicatorFilter must NOT store any state between calls. Each `evaluate()` call is independent -- this is explicitly stated in the phase boundary.
- **Hardcoded thresholds in condition methods:** Conditions are simple comparisons (>, <). Thresholds belong in FilterConfig, not in methods.
- **Coupling to engine internals:** IndicatorFilter should not import HybridEngine or know about snapshots. It receives a row + proposal string, returns a Verdict.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EMA/SMA/MACD computation | Custom indicator math | `core/indicators.py` compute_ema/compute_sma/compute_macd | Already validated, uses adjust=False for TradingView parity |
| Boolean feature definitions | New condition logic | Mirror `core/feature_snapshot.py` lines 106-113 | Exact same conditions, already tested against 962 signals |
| Config composition | Ad-hoc parameter passing | Dataclass composition pattern from HybridConfig | Established project pattern with __post_init__ validation |

**Key insight:** Phase 12 is a thin layer over existing indicator infrastructure. The boolean conditions are literally one-line comparisons that already exist in `feature_snapshot.py`. The new value is: (1) packaging them into a configurable class with toggles, (2) adding majority-vote verdict logic, and (3) formal TradingView parity verification.

## Common Pitfalls

### Pitfall 1: NaN Indicator Values in Early Rows
**What goes wrong:** MA 200 requires 200 days of data. Early rows have NaN for ma200, ema55 (warmup period). Comparing NaN > anything returns False, silently breaking conditions.
**Why it happens:** `build_indicator_dataframe()` returns NaN for warmup period. Row-based boolean comparison with NaN produces False without error.
**How to avoid:** Each condition method must handle NaN explicitly. Use `pd.notna(row['ma200'])` guard before comparison. Return False (condition not met) when indicator data is unavailable. Document this behavior.
**Warning signs:** Filter always returns VETO during first ~200 days of backtest.

### Pitfall 2: Inverted Conditions for Sell Proposals
**What goes wrong:** Using bullish conditions (close > ema55) to evaluate Sell proposals, resulting in always-VETO for sells.
**Why it happens:** D-06 requires different condition sets for Buy vs Sell. Easy to forget the inversion.
**How to avoid:** Separate `_get_bullish_votes()` and `_get_bearish_votes()` helper methods. Bearish checks the opposite: close < ema55, macd_histogram < 0, ema9 < ema21.
**Warning signs:** Filter confirms all Buy proposals but vetoes all Sell proposals (or vice versa).

### Pitfall 3: OVERRIDE Trigger Too Aggressive
**What goes wrong:** OVERRIDE fires too frequently, undermining the state machine's primary role.
**Why it happens:** OVERRIDE is defined as "all active indicators strongly contradict the proposal." If only 2-3 conditions are active, all-disagree happens often by chance.
**How to avoid:** OVERRIDE requires ALL active conditions to disagree (agree_ratio == 0.0). With 3 active conditions, this means all 3 must disagree. Consider whether OVERRIDE should also require a minimum number of active conditions (e.g., at least 3).
**Warning signs:** More OVERRIDE verdicts than CONFIRM verdicts in backtesting.

### Pitfall 4: TradingView Parity Tolerance Too Tight
**What goes wrong:** Parity tests fail due to floating-point differences between pandas EMA and TradingView's implementation.
**Why it happens:** TradingView may use different precision, rounding, or seed value handling for EMAs. Both use adjust=False, but initialization differences (first value handling) compound over hundreds of periods.
**How to avoid:** Use relative tolerance (+/-0.01% for EMA/MA, +/-0.1% for MACD as specified in D-09). Select reference dates well after warmup period (>200 trading days from data start) to minimize initialization divergence.
**Warning signs:** Parity passes for EMA9 but fails for EMA55 or MA200 (longer periods amplify seed differences).

### Pitfall 5: FilterConfig Max Active Rules Not Enforced
**What goes wrong:** User enables all 6 conditions, overfitting on 95 post-2019 signals.
**Why it happens:** D-04 says "max 2-3 active rules" but no enforcement mechanism.
**How to avoid:** Add `__post_init__` validation that counts active toggles and raises warning (or assertion) if more than 3 are enabled. Decide: hard error vs. warning. Recommendation: warning, not error -- allow experimentation but log the risk.
**Warning signs:** Users silently enable all 6 conditions and report "great" post-2019 results that don't generalize.

## Code Examples

### Complete FilterConfig with Validation
```python
# Source: established pattern from MDMV2Config in strategies/mdm_hybrid/config.py
from dataclasses import dataclass
import warnings

@dataclass
class FilterConfig:
    """Configuration for indicator filter conditions.

    Controls which boolean conditions are active and the voting threshold.
    Default active conditions are the top-3 from Phase 9 feature importance:
    close_above_ema55 (0.687), ema9_above_ema21, macd_histogram_positive.
    """
    ema55_enabled: bool = True
    macd_enabled: bool = True
    ema9_21_enabled: bool = True
    ma200_enabled: bool = False
    ema9_enabled: bool = False
    macd_signal_enabled: bool = False
    majority_threshold: float = 0.67

    def __post_init__(self):
        assert 0.0 < self.majority_threshold <= 1.0, \
            "majority_threshold must be in (0, 1]"
        active = self.active_count()
        if active > 3:
            warnings.warn(
                f"FilterConfig has {active} active conditions. "
                f"Max 2-3 recommended to avoid overfitting (D-04)."
            )

    def active_count(self) -> int:
        """Count number of enabled conditions."""
        return sum([
            self.ema55_enabled, self.macd_enabled, self.ema9_21_enabled,
            self.ma200_enabled, self.ema9_enabled, self.macd_signal_enabled,
        ])
```

### HybridConfig Composition Update
```python
# Source: existing HybridConfig in strategies/mdm_hybrid/config.py
@dataclass
class HybridConfig:
    v2_config: MDMV2Config = field(default_factory=MDMV2Config)
    filter_config: FilterConfig = field(default_factory=FilterConfig)  # NEW
    two_phase_enabled: bool = True
    filter_enabled: bool = False  # Phase 13 enables this

    def __post_init__(self):
        if isinstance(self.v2_config, dict):
            self.v2_config = MDMV2Config(**self.v2_config)
        if isinstance(self.filter_config, dict):
            self.filter_config = FilterConfig(**self.filter_config)
```

### TradingView Reference CSV Format
```csv
date,close,ema9,ema21,ema55,ma200,macd,macd_signal,macd_histogram
2023-01-03,10386.98,10423.45,10612.33,11234.56,12045.67,-189.22,-156.78,-32.44
2023-06-15,13573.32,13498.21,13345.67,12890.12,12234.56,156.78,134.22,22.56
...
```
Reference dates should span different market regimes (bull, bear, sideways) and be well past the 200-day warmup period to ensure stable indicator values.

### Unit Test Pattern for Boolean Conditions
```python
# Source: test_indicators.py pattern with synthetic data
import pandas as pd
import pytest
from strategies.mdm_hybrid.indicator_filter import IndicatorFilter, Verdict, FilterConfig

def _make_row(**overrides):
    """Create a synthetic row with indicator values."""
    defaults = {
        'close': 100.0, 'ema9': 99.0, 'ema21': 98.0, 'ema55': 95.0,
        'ma200': 90.0, 'macd': 1.5, 'macd_signal': 1.0, 'macd_histogram': 0.5,
    }
    defaults.update(overrides)
    return pd.Series(defaults)

class TestBooleanConditions:
    def test_close_above_ema55_true(self):
        row = _make_row(close=100.0, ema55=95.0)
        assert IndicatorFilter.close_above_ema55(row) is True

    def test_close_above_ema55_false(self):
        row = _make_row(close=90.0, ema55=95.0)
        assert IndicatorFilter.close_above_ema55(row) is False

    def test_close_above_ema55_nan(self):
        row = _make_row(close=100.0, ema55=float('nan'))
        assert IndicatorFilter.close_above_ema55(row) is False

class TestVerdict:
    def test_all_bullish_confirms_buy(self):
        row = _make_row(close=100.0, ema55=95.0, ema9=99.0, ema21=98.0,
                        macd_histogram=0.5)
        filt = IndicatorFilter()
        assert filt.evaluate(row, "BUY", None) == Verdict.CONFIRM

    def test_all_bearish_vetoes_buy(self):
        row = _make_row(close=80.0, ema55=95.0, ema9=90.0, ema21=92.0,
                        macd_histogram=-0.5)
        filt = IndicatorFilter()
        assert filt.evaluate(row, "BUY", None) == Verdict.OVERRIDE
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_indicator_filter.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HYB-02a | 6 boolean condition methods return correct bool | unit | `uv run pytest tests/test_indicator_filter.py::TestBooleanConditions -x` | Wave 0 |
| HYB-02b | evaluate() returns CONFIRM/VETO/OVERRIDE | unit | `uv run pytest tests/test_indicator_filter.py::TestVerdict -x` | Wave 0 |
| HYB-02c | FilterConfig toggles control active conditions | unit | `uv run pytest tests/test_indicator_filter.py::TestFilterConfig -x` | Wave 0 |
| HYB-02d | NaN handling in early rows | unit | `uv run pytest tests/test_indicator_filter.py::TestNaNHandling -x` | Wave 0 |
| HYB-02e | TradingView parity at 10+ dates | integration | `uv run pytest tests/test_indicator_filter.py::TestTradingViewParity -x` | Wave 0 |
| HYB-02f | Buy vs Sell proposal uses different conditions | unit | `uv run pytest tests/test_indicator_filter.py::TestProposalDirection -x` | Wave 0 |
| HYB-02g | OVERRIDE triggers when all conditions contradict | unit | `uv run pytest tests/test_indicator_filter.py::TestOverride -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_indicator_filter.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_indicator_filter.py` -- covers all HYB-02 sub-requirements
- [ ] `tests/fixtures/tradingview_reference.csv` -- TradingView parity data (10+ dates)

## Open Questions

1. **TradingView Reference Data Source**
   - What we know: Need 10+ reference dates with EMA/MACD values from TradingView for NASDAQ composite.
   - What's unclear: How to efficiently export these values. TradingView does not have a bulk export for indicator values -- must manually read from chart or use Pine Script data window.
   - Recommendation: Select 10-15 dates across market regimes (2020 crash, 2021 bull, 2022 bear, 2023-2024 recovery). Record values from TradingView's data window feature (hover over indicator, read tooltip). Format as CSV fixture. This is a one-time manual effort.

2. **Majority Threshold: Fraction vs Count**
   - What we know: D-11 specifies `majority_threshold: float = 0.67` and D-05 says ">=2/3 or configurable."
   - Recommendation: Use fraction (0.67). With 3 active conditions, 0.67 means 2/3 must agree. This generalizes naturally if user enables more conditions. The formula: `agree_count / active_count >= majority_threshold`.

3. **OVERRIDE Minimum Active Conditions**
   - What we know: OVERRIDE fires when all active conditions contradict. With only 2 active conditions, both disagreeing could be coincidental.
   - Recommendation: Require at least 3 active conditions for OVERRIDE to be possible. With fewer, downgrade to VETO. This prevents spurious overrides when user disables conditions.

## Project Constraints (from CLAUDE.md)

- Python 3.10+ with uv package manager
- 4-space indentation, ~120 char line limit
- snake_case for functions/variables, PascalCase for classes
- Google-style docstrings with Args/Returns
- Dataclass configs with `__post_init__` validation
- No linting/formatting tools configured -- follow observed style
- Tests in `tests/` directory using pytest
- GSD workflow enforcement for all changes

## Sources

### Primary (HIGH confidence)
- `core/indicators.py` -- verified compute_ema uses `adjust=False`, compute_macd uses standard (12,26,9)
- `core/feature_snapshot.py` lines 106-113 -- exact boolean condition definitions
- `strategies/mdm_hybrid/config.py` -- HybridConfig composition pattern with MDMV2Config
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` lines 253-261 -- two-phase commit placeholder for filter
- `analysis/rule_discovery.py` -- BOOLEAN_FEATURES list, feature importance values

### Secondary (MEDIUM confidence)
- TradingView EMA uses `adjust=False` equivalent (recursive EMA formula) -- widely documented but not formally verified against this project's pandas implementation yet. Phase 12 D-08/D-09 parity tests will confirm.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing project tools
- Architecture: HIGH -- established patterns (dataclass, enum, static methods) from existing codebase
- Pitfalls: HIGH -- NaN handling and TradingView parity are concrete, well-understood risks
- Verdict logic: MEDIUM -- OVERRIDE threshold and bearish inversion logic need careful unit testing

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable domain, no external dependency changes expected)
