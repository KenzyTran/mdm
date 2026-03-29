# Stack Research

**Domain:** Hybrid state machine + indicator filter MDM engine
**Researched:** 2026-03-29
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.10+ | Runtime | Already in use, no change needed |
| pandas | >= 2.0.0 | DataFrame operations, time series | Already in use for all OHLCV and signal processing |
| numpy | >= 1.24.0 | Numerical computation | Already in use for indicator math |
| scikit-learn | >= 1.5.0 | Decision tree classifiers, scoring | Already in use for rule_discovery.py and validate_discovery.py |

### Supporting Libraries (NEW for Hybrid Engine)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **None required** | -- | -- | See rationale below |

### Why No New Libraries

The hybrid engine does NOT need external state machine or ML libraries beyond what is already installed. Here is the reasoning:

**State Machine Libraries (NOT recommended):**

The two leading Python FSM libraries are `transitions` (v0.9.2) and `python-statemachine` (v3.0.0). Both are well-maintained. However, they solve problems this project does not have:

1. **The existing state machine is simple.** V2PositionManager already implements a clean 3-state machine (BUY/CASH/SELL) with 6 transitions. The hybrid engine adds indicator-based guards to these same transitions -- this is adding `if` conditions to existing code, not restructuring the state machine topology.

2. **External FSM libraries add indirection without value.** The state machine processes one row at a time in a pandas iteration loop. The "state" is a single enum value. Libraries like `transitions` shine for complex event-driven systems with dozens of states and async callbacks -- not for a deterministic daily-bar loop with 3 states.

3. **Integration friction.** Both libraries want to own the state object lifecycle. Integrating with the existing dataclass-based `V2Position` and pandas-centric `run()` loop would require adapter code that adds complexity without improving clarity.

4. **Debugging advantage of hand-rolled FSM.** When a signal mismatch occurs (the core validation task), stepping through explicit `if/elif` state transitions in `process_day()` is far easier than tracing through a library's event dispatch chain.

**Sequence Modeling / Deep Learning (NOT recommended):**

1. **962 samples is far too few** for LSTM, transformer, or any deep sequence model. Decision trees with 8 boolean features are the correct tool for this data volume.

2. **The problem is classification, not sequence prediction.** Each signal date is independently classifiable by its indicator snapshot. The decision tree in rule_discovery.py already handles this. The hybrid engine's job is to use these rules as filters on state machine transitions, not to predict sequences.

**Hybrid Framework Libraries (NOT recommended):**

Libraries like PyBroker combine ML with backtesting but impose their own data pipeline and execution model. This project already has a working backtest loop, data loaders, and performance analyzers. Adopting a framework would mean rewriting infrastructure for no gain.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | >= 9.0.2 | Already installed as dev dependency, essential for hybrid engine validation |
| matplotlib | >= 3.7.0 | Already installed, needed for comparison charts (hybrid vs classic vs tree) |

## Installation

```bash
# No new packages needed. Existing stack covers all requirements:
# pandas, numpy, scikit-learn, matplotlib, pytest
#
# Verify current environment:
uv run python -c "import pandas, numpy, sklearn; print('Stack OK')"
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Hand-rolled FSM (enum + if/elif) | `transitions` library (v0.9.2) | If state machine grows beyond ~10 states or needs visual diagram export for documentation |
| Hand-rolled FSM | `python-statemachine` (v3.0.0) | If you need hierarchical/compound states (e.g., BUY state with sub-states like BUY_AGGRESSIVE, BUY_DEFENSIVE) |
| scikit-learn DecisionTreeClassifier | XGBoost / LightGBM | If you expand to hundreds of continuous features and need gradient boosting; current 8 boolean features do not warrant this |
| scikit-learn DecisionTreeClassifier | Rule engine (e.g., `business-rules`, `durable-rules`) | If rules need to be user-editable at runtime; current rules are researcher-tuned code |
| pandas iteration loop | Vectorized numpy state machine | If backtest speed becomes a bottleneck (unlikely with ~13K daily bars) |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `transitions` / `python-statemachine` | Adds indirection to a 3-state machine; harder to debug signal mismatches | Enum + explicit if/elif in process_day() |
| PyBroker / Zipline / Backtrader | Replaces existing working infrastructure; migration cost with no research value | Existing backtest loop in engine.run() |
| TensorFlow / PyTorch / LSTM | 962 samples is insufficient for deep learning; overfitting guaranteed | scikit-learn DecisionTreeClassifier (already working) |
| XGBoost / LightGBM | 8 boolean features with 962 samples -- gradient boosting provides no advantage over a depth-3 decision tree | scikit-learn DecisionTreeClassifier |
| `networkx` for state graphs | Sometimes suggested for FSM visualization; massive dependency for a trivial 3-node graph | Simple ASCII diagram in docstring or matplotlib for one-off visualization |

## Stack Patterns by Variant

**If the hybrid engine stays at 3 states (BUY/CASH/SELL):**
- Keep the existing hand-rolled enum + if/elif pattern from V2PositionManager
- Add indicator filter guard conditions inline
- Because: simplest, most debuggable, already proven in v2

**If state machine expands to 6+ states (e.g., adding AGGRESSIVE_BUY, CAUTIOUS_SELL, TRANSITION sub-states):**
- Consider adopting `python-statemachine` v3.0.0 for compound state support
- Because: compound/hierarchical states are genuinely hard to hand-roll correctly

**If decision tree rules evolve to 20+ continuous features:**
- Consider adding `xgboost` or `lightgbm` alongside scikit-learn
- Because: gradient boosting handles feature interactions better at higher dimensionality
- Current 8 boolean features do NOT warrant this

## Integration Points with Existing Stack

The hybrid engine plugs into existing infrastructure at these boundaries:

| Existing Component | How Hybrid Uses It | Integration Pattern |
|---|---|---|
| `core/indicators.py` | Computes EMA 9/21/55, MA 200, MACD for each bar | Call `add_all_indicators(df)` before engine loop |
| `core/feature_snapshot.py` | Extracts boolean features at each date | Reuse boolean feature derivation logic inline in engine |
| `analysis/rule_discovery.py` | Trained decision tree provides filter rules | Export tree rules as hardcoded conditions or call `clf.predict()` per bar |
| `strategies/mdm_v2/position_manager.py` | Base state machine (BUY/CASH/SELL) | Extend or wrap with indicator guard conditions |
| `strategies/mdm_v2/config.py` | MDMV2Config dataclass | Extend with hybrid-specific params (filter weights, override thresholds) |
| `analysis/validate_discovery.py` | Scoring pipeline (confusion matrix, match rates) | Reuse for hybrid model validation against 962 signals |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| scikit-learn >= 1.5.0 | Python 3.10+, pandas >= 2.0.0 | Already validated in rule_discovery.py |
| pandas >= 2.0.0 | numpy >= 1.24.0 | Copy-on-write default in pandas 3.0; current code is compatible |
| matplotlib >= 3.7.0 | All above | No compatibility concerns |

## What Already Exists (DO NOT Re-implement)

These capabilities are validated and should be reused, not rebuilt:

- **EMA/MACD/MA computation**: `core/indicators.py`
- **Boolean feature derivation** (8 features): `core/feature_snapshot.py`
- **Decision tree training**: `analysis/rule_discovery.py` (era-aware, cross-validated)
- **Validation scoring**: `analysis/validate_discovery.py` (confusion matrix, match rates, degradation deltas)
- **State machine base**: `strategies/mdm_v2/position_manager.py` (BUY/CASH/SELL)
- **Performance analysis**: `strategies/mdm_v2/performance.py`
- **Data loading**: `core/data_loader.py`, `core/signal_loader.py`

## Sources

- [transitions on GitHub](https://github.com/pytransitions/transitions) -- v0.9.2, lightweight FSM, evaluated and rejected for this use case
- [python-statemachine on PyPI](https://pypi.org/project/python-statemachine/) -- v3.0.0 (Feb 2026), full statecharts, evaluated and rejected for 3-state simplicity
- [PyBroker](https://www.pybroker.com/) -- ML+backtesting framework, evaluated and rejected (existing infrastructure sufficient)
- [scikit-learn documentation](https://scikit-learn.org/stable/) -- DecisionTreeClassifier already in use, confirmed sufficient for 8-feature classification

---
*Stack research for: Hybrid MDM Engine (v3.0)*
*Researched: 2026-03-29*
