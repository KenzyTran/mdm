# Stack Research: Market Timing Model Reverse-Engineering

## Current Stack Assessment

The existing codebase uses pure Python with minimal dependencies. Based on `.planning/codebase/STACK.md`, the project uses:
- Python 3.x (no version pinned)
- pandas for data manipulation
- numpy for numerical computation
- No formal dependency management (no requirements.txt, pyproject.toml)

## Recommended Stack

### Core Data & Computation

| Library | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| **pandas** | >=2.2 | DataFrame operations, time series, CSV I/O | High |
| **numpy** | >=1.26 | Numerical arrays, vectorized math | High |
| **polars** | >=1.0 (optional) | Fast alternative for large dataset operations | Medium |

**Why pandas over polars as primary:** The existing codebase is pandas-based. Migration cost outweighs performance gains for datasets of this size (~13K rows NASDAQ, ~3.7K VN30).

### Technical Analysis & Indicators

| Library | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| **ta-lib** (python wrapper) | >=0.4.28 | Industry-standard technical indicators (MA, RSI, etc.) | High |
| **pandas-ta** | >=0.3.14 | Pure-Python fallback if TA-Lib C library install fails | Medium |

**Why TA-Lib:** Gold standard for financial technical analysis. Pre-computed indicators are battle-tested. However, Dr. K's MDM uses custom logic (FTD, Distribution Days) that won't be in any library — these must be hand-coded.

**Why NOT** generic ML libraries (scikit-learn, tensorflow) for signal discovery: The goal is rule-based reverse-engineering, not ML prediction. Overfitting risk is extreme with small signal datasets (~100 signals over 7 years).

### Backtesting

| Library | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| **Custom engine** (existing) | — | State-machine backtester matching MDM logic | High |
| **vectorbt** | >=0.26 (optional) | Vectorized backtesting for rapid parameter sweeps | Medium |

**Why keep custom engine:** MDM is a state machine (Cash→Buy→Hold→Warning→Short). Generic backtesting frameworks (backtrader, zipline) add complexity without value for state-machine models. The existing `mdm_engine.py` is the right approach.

**Why NOT backtrader/zipline:** Overkill for this use case. Both impose their own event-loop architecture. MDM logic maps better to a simple state machine iterated over a DataFrame.

### Visualization & Analysis

| Library | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| **matplotlib** | >=3.8 | Charts, signal overlays, equity curves | High |
| **plotly** | >=5.18 (optional) | Interactive charts for signal exploration | Medium |
| **mplfinance** | >=0.12 | Candlestick charts with volume | High |

### Signal Analysis (Reverse-Engineering Specific)

| Library | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| **scipy.stats** | >=1.12 | Statistical tests for signal pattern analysis | High |
| **dtw-python** | >=1.3 | Dynamic Time Warping for signal sequence matching | Medium |

**Why DTW:** Useful for comparing the timing alignment between model-generated signals and published signals, accounting for slight date offsets.

### Project Infrastructure

| Tool | Purpose | Confidence |
|------|---------|------------|
| **pyproject.toml** | Dependency management, project metadata | High |
| **pytest** | Testing framework (validate rules produce expected signals) | High |
| **ruff** | Fast Python linter/formatter | Medium |

## What NOT to Use

| Library | Why Not |
|---------|---------|
| **scikit-learn / XGBoost** | ML approaches will overfit on ~100 signal data points. This is a rule-discovery problem, not prediction. |
| **backtrader / zipline** | Imposes event-loop architecture; MDM state machine is simpler and more transparent as custom code. |
| **Jupyter notebooks as primary** | Analysis notebooks are fine, but core logic must live in .py files for testability and version control. |
| **Real-time data feeds (yfinance, alpaca)** | Out of scope — using static CSV data for reproducibility. |
| **Deep learning (LSTM, transformers)** | Same overfitting concern as ML. The model has explicit rules, not learned patterns. |

## Data Normalization Note

US market data (NASDAQ, S&P500) appears to have prices multiplied by ~1000x (e.g., S&P500 showing 6555860 instead of 6555.86). Data loader must normalize this. VN30 data appears to be at native scale.

---
*Researched: 2026-03-27*
*Confidence: High for core stack, Medium for optional additions*
