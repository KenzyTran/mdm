# Phase 7: Data Foundation - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Full 52-year NASDAQ price history (1974+) and complete 962-signal ground truth are loaded and ready for indicator computation. This phase extends the existing data infrastructure — it does NOT compute indicators (Phase 8) or discover rules (Phase 9).

</domain>

<decisions>
## Implementation Decisions

### Signal loader scope
- **D-01:** Extend existing `load_signal_fixture()` in `core/signal_loader.py` to optionally parse the `dollar_becomes` column. If the column is present in the CSV, include it in the output DataFrame; if absent, skip gracefully. This keeps backward compatibility with existing 3-column signal CSVs (TECL, partial NASDAQ).
- **D-02:** The full 962-signal CSV (`data/signals/nasdaq_signals_full.csv`) has 4 columns: `date`, `signal`, `gain_loss_pct`, `dollar_becomes`. All four are parsed by the extended loader.

### Early data quality
- **D-03:** Pass through all NASDAQ data as-is from 1973+. No filtering, trimming, or flagging of early rows with 0 volume or identical OHLC values. Phase 8 indicators (EMA, MA, MACD) only need close prices, which are valid even in the earliest data.
- **D-04:** The `dropna()` on OHLCV columns in the existing DataLoader is sufficient quality control — no additional quality gates needed for early data.

### Date alignment strategy
- **D-05:** When a signal date has no matching OHLCV row, warn and report but do not fail. Generate a gap report listing all mismatched signal dates so they are visible for investigation.
- **D-06:** Phase 8 (Indicator Engine) will decide how to handle gaps during feature snapshot extraction. Phase 7 only ensures the data is loaded and gaps are documented.

### Validation depth
- **D-07:** Add 2-3 spot-check reference values from distinct eras (~1974 early history, ~2000 dot-com peak, ~2008 financial crisis) to the existing SPOT_CHECKS dictionary in `core/data_loader.py`. Combined with existing 2020-2021 checks, this validates normalization across 4+ decades.
- **D-08:** Keep existing 0.1% tolerance threshold. Same assert-and-halt behavior as Phase 1.

### Claude's Discretion
- Exact reference dates and close prices for 1974/2000/2008 spot-checks (will look up real values)
- Gap report format (print to console, save to file, or return as DataFrame)
- Whether to add a convenience function for loading the full signal history specifically
- Test structure and assertion details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing data infrastructure
- `core/data_loader.py` -- Unified DataLoader with /1000 normalization, spot-checks, column mapping
- `core/signal_loader.py` -- Signal fixture loader (currently 3-column: date, signal, gain_loss_pct)

### Signal data
- `data/signals/nasdaq_signals_full.csv` -- Full 962-signal history (1974-2026) with dollar_becomes column
- `data/signals/nasdaq_signals.csv` -- Partial NASDAQ signals (2017-2026, 3-column format)
- `data/signals/tecl_signals.csv` -- TECL signals (2017-2026, 3-column format)

### Price data
- `data/NASDAQ.csv` -- NASDAQ Composite OHLCV (1973-2026, 13,318 rows, ~1000x scaled prices)

### Requirements
- `.planning/REQUIREMENTS.md` -- DATA-05 (full NASDAQ OHLCV from 1974+), DATA-06 (962-signal loader)

### Prior phase context
- `.planning/phases/01-data-integrity/01-CONTEXT.md` -- Phase 1 data decisions (normalization, loader design, signal format)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/data_loader.py` DataLoader class: Already handles NASDAQ loading with /1000 normalization, date parsing, and spot-checks. Only needs spot-check dictionary extended for earlier eras.
- `core/signal_loader.py` load_signal_fixture(): Parses date/signal/gain_loss_pct with validation. Needs minor extension for optional dollar_becomes column.
- `core/signal_comparator.py`: Signal comparison engine from Phase 3 — not modified in Phase 7 but consumes signal loader output.

### Established Patterns
- Column mapping via dictionary in DataLoader (COLUMN_MAPS)
- Spot-check validation with 0.1% tolerance and assert-on-failure behavior
- Signal type validation against VALID_SIGNALS set {"Buy", "Sell", "Cash"}
- pd.to_numeric(errors='coerce') for safe numeric conversion

### Integration Points
- Extended signal loader will be consumed by Phase 8's feature snapshot extraction (IND-05)
- Extended DataLoader spot-checks validate the full 1974+ price history
- Gap report output will inform Phase 8's alignment strategy

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 07-data-foundation*
*Context gathered: 2026-03-29*
