# Architecture Research: Multi-Strategy Trading System

## Current State Problem

Both `models/` (MDM) and `vn30_vsa/` (VSA) duplicate 6 infrastructure modules with no shared code:
- data_loader.py (duplicated)
- indicators.py (duplicated)
- position_manager.py (duplicated)
- stop_loss.py (duplicated)
- performance.py (duplicated)
- config.py (duplicated)

Adding MDM v2 as a third copy is unsustainable.

## Recommended Architecture: Three-Layer Design

```
project/
├── core/                    # Shared infrastructure (Layer 1)
│   ├── types.py             # Common types: Signal, Position, TradeResult, OHLCV
│   ├── data/
│   │   ├── loader.py        # Unified data loader (NASDAQ, S&P500, VN30)
│   │   ├── normalizer.py    # Price normalization (US data scaling)
│   │   └── signals.py       # Published signal parser (Dr. K's signal history)
│   ├── indicators/
│   │   ├── moving_avg.py    # MA calculations (SMA, EMA)
│   │   ├── volume.py        # Volume analysis utilities
│   │   └── technical.py     # Other technical indicators
│   ├── backtesting/
│   │   ├── engine.py        # Generic backtest loop (calls strategy.detect_signal())
│   │   ├── comparison.py    # Signal comparison engine (model vs published)
│   │   └── metrics.py       # Performance metrics (Sharpe, drawdown, win rate)
│   └── performance/
│       ├── report.py        # Performance reporting
│       └── visualization.py # Charts, signal overlays, equity curves
│
├── strategies/              # Signal logic only (Layer 2)
│   ├── base.py              # Strategy Protocol interface
│   ├── mdm_classic/         # Original pre-2019 MDM rules
│   │   ├── __init__.py
│   │   ├── engine.py        # State machine: Cash→Buy→Hold→Warning→Short
│   │   ├── ftd.py           # Follow-Through Day detection
│   │   ├── distribution.py  # Distribution Day counting
│   │   ├── rally.py         # Rally Attempt tracking
│   │   └── config.py        # Classic rule parameters
│   ├── mdm_v2/              # Post-2019 reverse-engineered rules
│   │   ├── __init__.py
│   │   ├── engine.py        # Modified state machine (with Cash intermediate state)
│   │   ├── signals.py       # New signal detection logic
│   │   └── config.py        # Parameterized thresholds for experimentation
│   └── vsa/                 # Volume Spread Analysis (independent)
│       ├── __init__.py
│       ├── engine.py        # VSA-specific engine
│       ├── signals.py       # VSA signal detection
│       ├── kelly.py         # Kelly Criterion position sizing
│       └── config.py        # VSA parameters
│
├── analysis/                # Research & exploration (Layer 3)
│   ├── divergence.py        # Compare classic vs published signals
│   ├── hypothesis.py        # Test rule modifications systematically
│   ├── parameter_sweep.py   # Grid search over rule parameters
│   └── notebooks/           # Jupyter notebooks for exploration
│
├── scripts/                 # Entry points
│   ├── run_backtest.py      # Run any strategy backtest
│   ├── compare_signals.py   # Compare model output vs published signals
│   └── analyze.py           # Run analysis tools
│
├── data/                    # Market data (CSV)
│   ├── NASDAQ.csv
│   ├── s&p500.csv
│   └── vn30.csv
│
├── tests/                   # Test suite
│   ├── test_data_loader.py
│   ├── test_mdm_classic.py
│   ├── test_signal_comparison.py
│   └── fixtures/
│       └── published_signals.json  # Dr. K's signal history as test data
│
└── rules.md                 # Original MDM rules documentation
```

## Strategy Interface (Protocol Pattern)

```python
from typing import Protocol, Literal

Signal = Literal["buy", "sell", "cash"]

class Strategy(Protocol):
    def detect_signal(self, data: pd.DataFrame, idx: int, state: dict) -> Signal:
        """Given market data up to index idx and current state, return signal."""
        ...

    def get_initial_state(self) -> dict:
        """Return strategy's initial state (e.g., dd_count=0, position=cash)."""
        ...
```

**Key design decision:** MDM v2 should NOT inherit from MDM classic. Use composition over inheritance — both use `core/` but have independent signal rules. This makes divergences explicit, which is essential for reverse-engineering.

## Data Flow

```
CSV Files → core/data/loader.py → Normalized DataFrame (OHLCV + date index)
                                        │
                                        ▼
                              core/backtesting/engine.py
                                        │
                              ┌─────────┼─────────┐
                              ▼         ▼         ▼
                         mdm_classic  mdm_v2     vsa
                        .detect_signal()  per bar
                              │         │         │
                              ▼         ▼         ▼
                         Signal lists (Buy/Sell/Cash + dates)
                              │         │
                              ▼         ▼
                    core/backtesting/comparison.py
                              │
                              ▼
                    Divergence report + match score
                              │
                              ▼
                    core/performance/report.py → Charts, metrics
```

## Component Boundaries

| Component | Depends On | Never Depends On |
|-----------|-----------|-----------------|
| `core/types` | Nothing | — |
| `core/data` | `core/types` | Any strategy |
| `core/indicators` | `core/types`, numpy/pandas | Any strategy |
| `core/backtesting` | `core/types`, `core/indicators` | Any strategy |
| `strategies/*` | `core/*` | Other strategies |
| `analysis/*` | `core/*`, `strategies/*` | — |
| `scripts/*` | Everything | — |

**Strict rule:** Strategies depend on core, never the reverse, never on each other.

## Build Order (Dependency-Driven)

1. **Foundation:** `core/types.py` + `core/data/` — no dependencies, everything else needs these
2. **Infrastructure:** `core/indicators/` + `core/backtesting/` — needs types + data
3. **Migration:** Migrate existing `models/` → `strategies/mdm_classic/`, `vn30_vsa/` → `strategies/vsa/` — verify identical backtest output at each step
4. **Signal Tools:** `core/backtesting/comparison.py` + published signal parser — needs migrated strategies
5. **New Strategy:** `strategies/mdm_v2/` + analysis tools — needs signal comparison as validation
6. **VN30 Adaptation:** Parameter tuning for VN30 market — needs validated v2 rules

**Critical:** Migration must verify identical backtest results at each step. Any regression = bug introduced.

## Open Questions

- VSA engine loop abstraction — multi-stock portfolio iteration is structurally different from single-index MDM
- Whether MDM classic sub-components (rally attempt tracking) should be shared in core vs duplicated in v2 — defer until v2 rules are understood

---
*Researched: 2026-03-27*
*Confidence: HIGH for component boundaries and data flow, MEDIUM for VSA abstraction*
