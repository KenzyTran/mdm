# Phase 3: Signal Divergence Analysis - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a comparison engine and divergence report that measures exactly where and how MDM classic rules diverge from Dr. K's published post-2019 signals on NASDAQ. Includes visual overlay chart. Does NOT modify trading rules (Phase 4) or build new signal logic.

</domain>

<decisions>
## Implementation Decisions

### Signal matching logic
- **D-01:** State-to-signal mapping: HOLDING->Buy, SHORT->Sell, CASH+WAITING_SELL->Cash. Compare state transitions against published signal changes.
- **D-02:** Exact date match only — a model signal on date X only matches a published signal on date X. No tolerance window.
- **D-03:** Match metrics: overall match rate (% of published signals matched) plus separate match rates per signal type (Buy, Sell, Cash).
- **D-04:** Comparison engine built as reusable module `core/signal_comparator.py`. Takes two signal DataFrames, returns structured results. Phase 4's hypothesis testing reuses this directly.

### Divergence classification
- **D-05:** Four-type taxonomy: THRESHOLD (model nearly triggered), TIMING (right signal within +/-5 days), STRUCTURAL (signal type model can't produce, e.g., Cash), IRREPRODUCIBLE (no discernible pattern).
- **D-06:** Auto-classification via heuristics: model signal within +/-5 days -> TIMING, published Cash and model has no Cash state -> STRUCTURAL, model indicator within 10% of threshold -> THRESHOLD, else -> IRREPRODUCIBLE.
- **D-07:** Output as CSV (detailed per-divergence rows: date, published signal, model signal, type, context) plus text summary (counts per type, worst periods, overall match rate). CSV feeds Phase 4; summary is human-readable.

### Visual overlay design
- **D-08:** Chart layout: main panel with NASDAQ price line, below it two horizontal color-coded tracks — top track for published signals, bottom track for model signals (green=Buy, red=Sell, gray=Cash).
- **D-09:** Shaded divergence zones: light red/pink vertical bands behind price chart wherever model and published signals disagree.
- **D-10:** Both a script in `analysis/` generating high-res PNG and a Jupyter notebook for interactive exploration.

### Comparison scope
- **D-11:** Primary comparison target: NASDAQ published signals (`data/signals/nasdaq_signals.csv`). TECL is not used for primary comparison.
- **D-12:** Full comparison period: 2019-2026 (entire published signal range). No pre/post splits.
- **D-13:** Classic model runs on NASDAQ data loaded via unified `core/data_loader.py` with market='nasdaq'. Does not use the classic engine's own data_loader for NASDAQ data.

### Claude's Discretion
- Exact heuristic thresholds for auto-classification (the 10% threshold proximity, +/-5 day window)
- Internal data structures for comparison results
- Chart styling details (exact colors, font sizes, figure dimensions)
- Notebook structure and cell organization
- Text summary formatting and section ordering

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Signal infrastructure (Phase 1 outputs)
- `core/signal_loader.py` — Published signal fixture loader, validates Buy/Sell/Cash types, returns sorted DataFrame
- `core/data_loader.py` — Unified DataLoader with NASDAQ normalization (market='nasdaq')
- `data/signals/nasdaq_signals.csv` — Published NASDAQ signals 2019-2026 (date, signal, gain_loss_pct)
- `data/signals/tecl_signals.csv` — Published TECL signals (reference, not primary comparison)

### MDM classic strategy (Phase 2 outputs)
- `strategies/mdm_classic/mdm_engine.py` — MDM orchestration engine, runs backtest and produces signal sequence
- `strategies/mdm_classic/position_manager.py` — State machine with CASH/HOLDING/WAITING_SELL/SHORT states and Position dataclass
- `strategies/mdm_classic/config.py` — MDMConfig dataclass with all rule parameters

### Existing analysis patterns
- `analysis/analyze_drawdown.py` — Reference for analysis script structure and matplotlib usage
- `tests/test_mdm_regression.py` — Reference for how to run MDM classic and extract signals programmatically

### Requirements
- `.planning/REQUIREMENTS.md` — SIG-01 through SIG-04 define acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/signal_loader.py`: Load published signals into validated DataFrame — direct input to comparison engine
- `core/data_loader.py`: Load NASDAQ OHLCV with normalization — feed to MDM classic engine
- `strategies/mdm_classic/MDMEngine`: Run classic rules on any OHLCV data — produces signal sequence to compare
- `strategies/mdm_classic/position_manager.py` MarketState enum: CASH, HOLDING, WAITING_SELL, SHORT — defines the state-to-signal mapping source
- `analysis/analyze_drawdown.py`: matplotlib charting pattern with multi-panel layout — template for visual overlay

### Established Patterns
- DataFrame-centric workflow: all components accept and return pandas DataFrames
- CSV I/O: load from CSV, process in pandas, export results as CSV
- Analysis scripts: standalone Python files in analysis/ that import from core/strategies and produce output files
- pytest in tests/: established test infrastructure for regression and fixture validation

### Integration Points
- New `core/signal_comparator.py` imports `core/signal_loader.py` for published signals
- MDMEngine needs NASDAQ data via `core/data_loader.py` (may need adapter to bridge loader output format to engine input)
- Phase 4 will import `core/signal_comparator.py` for match-rate scoring during hypothesis testing
- Divergence CSV output goes to `data/` directory alongside other generated files

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-signal-divergence-analysis*
*Context gathered: 2026-03-28*
