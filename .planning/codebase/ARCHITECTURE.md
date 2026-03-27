# Architecture

**Analysis Date:** 2026-03-27

## Pattern Overview

**Overall:** Multi-strategy backtesting platform with pluggable signal detection engines

**Key Characteristics:**
- **Two independent trading strategies** (MDM and VSA) with separate but structurally similar modules
- **Layered architecture** separating data loading, indicator calculation, signal detection, and position management
- **State machine pattern** for position tracking (CASH, HOLDING, WAITING_SELL, SHORT states)
- **Component-based design** with single-responsibility modules that compose into engines
- **Configuration-driven parameters** allowing parameter optimization via config objects

## Layers

**Data Layer:**
- Purpose: Load, validate, and preprocess market data (OHLCV) from CSV sources
- Location: `models/data_loader.py`, `vn30_vsa/data_loader.py`
- Contains: CSV file reading, date range filtering, column mapping, numeric type conversion
- Depends on: pandas for data manipulation
- Used by: Engines (MDMEngine, VSAEngine) to load price data

**Indicator Calculation Layer:**
- Purpose: Calculate technical indicators (moving averages, price location, volume ratios, rolling highs)
- Location: `models/indicators.py`, `vn30_vsa/indicators.py`
- Contains: Static methods for MA10, MA50, price location (P_loc), volume ratios, drawdown calculations
- Depends on: pandas, numpy for vectorized calculations
- Used by: Engines to prepare features before signal detection

**Signal Detection Layer:**
- Purpose: Identify buy/sell signals based on strategy-specific rules
- Location: `models/ftd_signal.py`, `models/distribution_day.py`, `models/rally_attempt.py` (MDM) and `vn30_vsa/signals.py` (VSA)
- Contains: FTD detector, distribution day counter, rally attempt tracker (MDM), volume spike and breakout detection (VSA)
- Depends on: Config objects, indicators from layer above
- Used by: Engines to determine trading actions

**Position Management Layer:**
- Purpose: Track positions, manage state transitions, execute trades, calculate P&L
- Location: `models/position_manager.py`, `vn30_vsa/position_manager.py`
- Contains: Position state machine, trade execution logic, NAV calculation
- Depends on: MarketState enum, Trade/Position dataclasses
- Used by: Engines to update portfolio state based on signals

**Risk Management Layer:**
- Purpose: Enforce stop loss rules and trailing stop loss mechanics
- Location: `models/stop_loss.py`, `vn30_vsa/stop_loss.py`, `vn30_vsa/trailing_stop.py`, `vn30_vsa/kelly.py`
- Contains: Stop loss validation, position sizing via Kelly Criterion
- Depends on: Position data, configuration
- Used by: Engines during daily processing

**Engine Layer:**
- Purpose: Orchestrate all layers - coordinate data loading, calculation, signal detection, and position updates
- Location: `models/mdm_engine.py`, `vn30_vsa/vsa_engine.py`
- Contains: Main loop processing daily bars, state machine updates, trade recording
- Depends on: All layers below
- Used by: Scripts (run_backtest.py, optimize_mdm.py) and Jupyter notebooks

**Performance Analysis Layer:**
- Purpose: Calculate backtest statistics, win rates, P&L metrics
- Location: `models/performance.py`, `vn30_vsa/performance.py`
- Contains: Trade analysis, performance metrics, reporting
- Depends on: Engine results and trade history
- Used by: Backtesting scripts for reporting

## Data Flow

**Backtest Execution Flow:**

1. Load CSV data → DataLoader reads OHLCV, filters date range, validates numeric columns
2. Engine receives DataFrame with clean OHLCV data
3. For each trading day (left to right through time):
   - Add indicators: Indicators layer calculates MA10, MA50, P_loc, rolling highs
   - Detect signals: Signal detection layer checks FTD, distribution days, volume spikes
   - Check risk: Stop loss layer validates position protection
   - Update state: Position manager processes signal and updates state machine
   - Record trade: If state changed, trade is logged with entry/exit prices and P&L
4. Engine returns complete results DataFrame with signals, states, and positions per day
5. Performance analyzer calculates trade statistics and backtest metrics

**State Machine Data Flow (Position Manager):**

```
CASH
  ├─→ [FTD Signal Detected] → enter_holding() → HOLDING
  └─→ [MA50 Breakout] → enter_holding() → HOLDING

HOLDING
  ├─→ [Stop Loss Triggered] → exit_position() → CASH + Trade closed
  ├─→ [Distribution Days == 5] → WAITING_SELL
  ├─→ [Rally Day 4+ with FTD] → (Reset counter, keep HOLDING)
  └─→ [Trigger Break] → trigger_break() → WAITING_SELL

WAITING_SELL
  ├─→ [Price < Trigger] → open_short() → SHORT + Trade closed
  ├─→ [Price > DD5 High] → back_to_holding() → HOLDING
  └─→ [New FTD] → (Reset, keep state)

SHORT
  ├─→ [FTD/MA50 Breakout] → cover_short() → CASH + Trade closed
  └─→ [Stop Loss 1%] → exit_short() → CASH + Trade closed
```

**State Management:**
- Current position stored in `PositionManager.position` (Position dataclass)
- Position includes buy_price, buy_date, buy_day_low, trigger_price, dd5_high
- State transitions triggered by signal detection results passed to `process_day()`
- Trades recorded immediately when exits occur (sell, cover, stop loss)

## Key Abstractions

**Configuration Objects:**
- Purpose: Centralize strategy parameters for easy modification and optimization
- Examples: `models/config.py` (MDMConfig), `vn30_vsa/config.py` (module-level constants)
- Pattern: Dataclass with parameters + post-init validation (MDM), or module constants (VSA)
- Usage: Passed to component constructors, used during signal detection logic

**Signal Classes:**
- Purpose: Encapsulate signal information (date, price, type, confidence)
- Examples: `FTDSignal`, distribution day records, volume spike data
- Pattern: Dataclass with typed fields (signal_type, price, rally_day, date)
- Usage: Returned from detector methods, passed to position manager for action

**Position/Trade Dataclasses:**
- Purpose: Type-safe position tracking and trade record keeping
- Examples: `Position` (current position state), `Trade` (completed trade record)
- Pattern: Mutable dataclass for Position, immutable for Trade records
- Usage: Position updated in-place during backtest, Trade created on position close

## Entry Points

**Run Backtest (MDM):**
- Location: `run_backtest.py`
- Triggers: User executes `python run_backtest.py`
- Responsibilities: Load data, instantiate engine, run backtest, output report to file
- Flow: DataLoader.load() → MDMEngine.run() → PerformanceAnalyzer.print_report()

**Parameter Optimization:**
- Location: `optimize_mdm.py`
- Triggers: User executes `python optimize_mdm.py`
- Responsibilities: Grid search parameter space, run backtest for each combo, compare results
- Flow: Iterate combinations → Create MDMConfig with params → MDMEngine.run() → Compare metrics

**Jupyter Notebooks:**
- Location: `mdm_backtest.ipynb`, `vn30_vsa_backtest.ipynb`, `sp500_backtest.ipynb`
- Triggers: User opens notebook in Jupyter/IPython
- Responsibilities: Interactive backtesting, parameter tuning, chart visualization
- Flow: Import engines → Run experiments → Plot results in-notebook

**Analysis Scripts:**
- Location: `analysis/diagnose_vn30.py`, `analyze_drawdown.py`, `analyze_vsa_drawdown.py`
- Triggers: User executes scripts for post-backtest analysis
- Responsibilities: Detailed analysis of specific aspects (drawdowns, distribution days, etc.)

## Error Handling

**Strategy:** Configuration validation + graceful data handling

**Patterns:**
- **Data validation**: DataLoader validates numeric columns, drops rows with NaN, filters dates
- **Type safety**: Use type hints throughout (Optional, Tuple return types for error indication)
- **Graceful degradation**:
  - Stop loss checkers return "not triggered" when data missing (e.g., NA for MA values)
  - Signal detectors return (False, None) when conditions not met
  - Position manager initializes with safe defaults (CASH state, 0.0 prices)
- **Config validation**: MDMConfig post_init validates parameter ranges (e.g., correction_threshold < 0)

**No exceptions raised in hot loop**: Core daily processing loop catches no exceptions - assumes clean data from DataLoader

## Cross-Cutting Concerns

**Logging:** No structured logging - uses print statements during backtest (redirected to file in run_backtest.py)

**Validation:**
- Data validation in DataLoader (date ranges, numeric types, null handling)
- Config validation in MDMConfig post_init
- Signal validity checks before recording (return False if conditions not met)

**Authentication:** Not applicable - batch processing, file-based data

**State Reset:** Engines provide reset() method to clear internal state (position manager, counters) before each backtest run

---

*Architecture analysis: 2026-03-27*
