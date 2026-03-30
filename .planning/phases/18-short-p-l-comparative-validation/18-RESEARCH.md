# Phase 18: Short P&L & Comparative Validation - Research

**Researched:** 2026-03-30
**Domain:** Performance analytics, equity curve computation, backtest comparison
**Confidence:** HIGH

## Summary

Phase 18 is a measurement and documentation phase -- it does NOT add new trading logic. The work centers on three deliverables: (1) modifying the existing equity curve builder to capture short position returns (inverse price movement when prev_state=SELL), (2) creating a comparison script that runs long-only vs long/short backtests side-by-side for both NASDAQ and VN30, and (3) updating rule documentation files with short signal rules from Phases 16-17.

The codebase is well-structured for this work. The `V2PerformanceAnalyzer._build_daily_equity()` method at line 91 of `strategies/mdm_hybrid/performance.py` already has the exact branch point where the change goes -- currently `equity[i] = equity[i-1]` for non-BUY states, which needs an `elif prev_state == 'SELL'` branch for inverse returns. The `analysis/validate_v2.py` script provides a proven pattern for comparison reports with matplotlib charts and metrics tables.

**Primary recommendation:** Modify `_build_daily_equity()` to add inverse return for SELL state, create a single comparison script with market parameter, and append short-related sections to both rule doc files. Use the existing `validate_v2.py` pattern for the comparison script structure.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Equity curve uses inverse return when prev_state=SELL: `equity[i] = equity[i-1] * (close[i-1] / close[i])`. Gain when market drops, loss when market rises.
- D-02: Single blended equity curve (not separate long/short curves). All metrics computed from blended curve.
- D-03: Modify existing `V2PerformanceAnalyzer._build_daily_equity()` in `strategies/mdm_hybrid/performance.py` -- add `elif prev_state == 'SELL'` branch.
- D-04: Python script (not notebook) for comparison report. Consistent with Phase 5 approach (`analysis/validate_v2.py` pattern).
- D-05: Chart shows 2 equity curves on same plot: long-only vs long/short. Metrics table shows side-by-side: total return, annualized return, max drawdown, Sharpe ratio, win rate.
- D-06: Single script handles both NASDAQ and VN30 via market parameter. Outputs 2 charts + 2 metrics tables.
- D-07: Add sections to both `docs/rules_mdm_v2.md` and `docs/rules_mdm_hybrid.md` covering: short entry/cover rules, stop loss 1.5% + adaptive scaling, short stop loss (DD5 high), SELL->CASH->BUY transition enforcement.
- D-08: Keep existing doc structure -- append sections, don't rewrite.
- D-09: NASDAQ and VN30 use identical short logic. Differences handled by existing config.

### Claude's Discretion
- Long-only backtest mode implementation: config flag to disable short returns (treat SELL as CASH for comparison), or run engine twice with different configs
- Chart styling, colors, layout details
- Exact structure of new rule doc sections (headings, formatting)
- Whether to include per-trade short P&L breakdown in the comparison report
- Script file naming and location in `scripts/` or `analysis/`

### Deferred Ideas (OUT OF SCOPE)
- Separate short-only equity curve analysis
- Inverse ETF decay modeling for NASDAQ
- Interactive notebook for comparison exploration
- Anti-whipsaw / cooldown logic for short transitions (FUT-03)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHORT-02 | P&L tracking cho vi the short -- gain khi market giam, loss khi market tang | Equity curve modification in `_build_daily_equity()` with inverse return formula. Manual verification via `cover_short()` P&L in trade list. |
| TRANS-02 | Backtest comparison long-only vs long/short tren NASDAQ va VN30 | Comparison script pattern from `analysis/validate_v2.py`. Two-run approach: one with short returns, one treating SELL as CASH. |
| TRANS-03 | Cap nhat rule docs (rules_mdm_v2.md, rules_mdm_hybrid.md) voi quy tac short moi | Append sections to existing Vietnamese-language rule docs covering Phase 16-17 features. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame operations for equity curve, metrics | Already in use throughout project |
| numpy | >= 1.24.0 | Array operations for equity computation | Already in use for performance math |
| matplotlib | >= 3.7.0 | Comparison chart generation | Already in use for dashboards |

### Supporting
No new libraries needed. This phase uses only existing project dependencies.

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Approach for Long-Only Mode

**Recommendation (Claude's discretion area):** Use a config flag approach rather than running the engine twice.

**Rationale:** Running the engine twice would produce different state transitions (since long-only mode would not enter SELL state at all, changing the entire signal sequence). The correct comparison is: same signals, same state transitions, but SELL days treated as flat (no inverse return) in the equity curve only.

**Implementation:** Add a `long_only_equity` parameter to `V2PerformanceAnalyzer.__init__()` that, when True, treats SELL the same as CASH in `_build_daily_equity()`. This way:
- Both long-only and long/short use the SAME engine run, SAME trades
- Only the equity curve computation differs
- This isolates the pure effect of short position returns

```python
class V2PerformanceAnalyzer:
    def __init__(self, results_df, trades=None, long_only_equity=False):
        self.long_only_equity = long_only_equity
        # ... existing init ...

    def _build_daily_equity(self):
        for i in range(1, n):
            prev_state = states[i - 1]
            if prev_state == "BUY":
                equity[i] = equity[i - 1] * (closes[i] / closes[i - 1])
            elif prev_state == "SELL" and not self.long_only_equity:
                # Inverse return: gain when market drops
                equity[i] = equity[i - 1] * (closes[i - 1] / closes[i])
            else:
                # CASH or SELL in long-only mode
                equity[i] = equity[i - 1]
```

### Comparison Script Structure

Follow `analysis/validate_v2.py` pattern:

```
analysis/compare_long_short.py
├── Section 1: Constants (periods, output paths)
├── Section 2: Run engine for a given market
├── Section 3: Build comparison metrics (long-only vs long/short)
├── Section 4: Generate comparison chart (2 equity curves)
├── Section 5: Save results (CSV + text summary)
├── Section 6: Main (iterate NASDAQ, VN30)
└── Section 7: CLI entry point (argparse)
```

### Win Rate Computation for Short Trades

The current `win_rate()` only counts CASH_EXIT trades. For the blended long/short comparison, win rate should include SHORT_COVER trades as well. The comparison script should compute:
- Long win rate: profitable CASH_EXIT trades / total CASH_EXIT trades (existing)
- Short win rate: profitable SHORT_COVER trades / total SHORT_COVER trades (new)
- Combined win rate: all profitable exits / all exits (new)

### Anti-Patterns to Avoid
- **Running engine twice for comparison:** Would produce different signal sequences. Use single run with equity-level switching instead.
- **Separate long/short equity curves:** Contradicts D-02. Single blended curve is required.
- **Modifying position_manager for long-only:** The long-only difference is equity-only, not signal-level.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Equity curve math | Custom return loop | Extend existing `_build_daily_equity()` | Avoids off-by-one errors, uses proven pattern |
| Metrics computation | New metrics functions | Existing `V2PerformanceAnalyzer.summary()` | Already computes all required metrics |
| Chart generation | Custom plotting code | Follow `generate_dashboard()` pattern from `validate_v2.py` | Proven matplotlib layout |
| Data loading | New loader code | Existing `DataLoader('nasdaq')` and `DataLoader('vn30')` | Already handles both markets |

## Common Pitfalls

### Pitfall 1: Off-by-one in inverse return formula
**What goes wrong:** Using `close[i] / close[i-1]` instead of `close[i-1] / close[i]` for short returns, which would give long returns instead of inverse.
**Why it happens:** Easy to confuse numerator/denominator since short profits are the mirror of long profits.
**How to avoid:** The formula `equity[i] = equity[i-1] * (close[i-1] / close[i])` means: if close drops 5%, equity gains ~5.26%. If close rises 5%, equity loses ~4.76%. Verify with manual calculation on known trades.
**Warning signs:** Short equity goes up when market goes up.

### Pitfall 2: Win rate including wrong trade types
**What goes wrong:** Including SHORT_COVER trades in long win rate or vice versa.
**Why it happens:** The existing `win_rate()` filters for `type == 'CASH_EXIT'` only. SHORT_COVER trades have a separate type.
**How to avoid:** For combined win rate, filter for both CASH_EXIT and SHORT_COVER. For separate rates, filter each type independently.
**Warning signs:** Win rate changes unexpectedly when short positions are added.

### Pitfall 3: VN30 data loader differences
**What goes wrong:** Assuming VN30 data loads identically to NASDAQ.
**Why it happens:** VN30 uses different column names in source CSV (openprice vs openindex).
**How to avoid:** Use `DataLoader('vn30')` which handles column mapping automatically. The HybridEngine works with normalized columns.
**Warning signs:** KeyError on column names when running VN30 comparison.

### Pitfall 4: Rule docs language inconsistency
**What goes wrong:** Writing new sections in English when existing docs are in Vietnamese.
**Why it happens:** Existing `rules_mdm_v2.md` and `rules_mdm_hybrid.md` are entirely in Vietnamese.
**How to avoid:** Write new sections in Vietnamese to match existing style (per CONTEXT specifics section).
**Warning signs:** Mixed language in the same document.

### Pitfall 5: Forgetting to update mdm_v2/performance.py
**What goes wrong:** Only updating `strategies/mdm_hybrid/performance.py` but not the copy at `strategies/mdm_v2/performance.py`.
**Why it happens:** Both files contain the same `V2PerformanceAnalyzer` class.
**How to avoid:** Check if mdm_v2 performance.py is used by the comparison script. If the script only uses HybridEngine, then only the hybrid copy needs updating. The CONTEXT canonical refs mention `strategies/mdm_v2/performance.py` as "same class, may need same update."
**Warning signs:** Inconsistent behavior depending on which import path is used.

### Pitfall 6: Short P&L sign convention mismatch
**What goes wrong:** Equity curve shows positive return but trade P&L shows negative, or vice versa.
**Why it happens:** `cover_short()` computes `pnl = (entry - cover) / entry` which is positive when market drops. The equity curve formula `close[i-1] / close[i]` also produces >1 when market drops. These should be consistent.
**How to avoid:** Verify 3+ trades manually: check that trade-level P&L matches the cumulative equity change during that SELL period.
**Warning signs:** Aggregate equity return doesn't match sum of trade P&L values.

## Code Examples

### Inverse return in equity curve (D-01)
```python
# Source: D-01 from CONTEXT.md, verified against position_manager.cover_short()
# In _build_daily_equity():
elif prev_state == "SELL" and not self.long_only_equity:
    # Short position: gain when market drops
    equity[i] = equity[i - 1] * (closes[i - 1] / closes[i])
```

### Manual verification pattern for 3+ trades (Success Criteria 1)
```python
# After running engine, extract SHORT_COVER trades
short_trades = [t for t in trades if t['type'] == 'SHORT_COVER']
for t in short_trades[:3]:
    entry = t['entry_price']
    cover = t['price']
    expected_pnl = (entry - cover) / entry
    actual_pnl = t['pnl']
    assert abs(expected_pnl - actual_pnl) < 1e-10, f"P&L mismatch: {expected_pnl} vs {actual_pnl}"
    print(f"Trade {t['date']}: entry={entry:.2f}, cover={cover:.2f}, "
          f"pnl={actual_pnl:.4f} ({'gain' if actual_pnl > 0 else 'loss'})")
```

### Comparison metrics side-by-side (D-05)
```python
# Run single engine, create two analyzers
results = engine.run(df)
trades = engine.get_trades()

long_short = V2PerformanceAnalyzer(results, trades, long_only_equity=False)
long_only = V2PerformanceAnalyzer(results, trades, long_only_equity=True)

metrics = {
    'Strategy': ['Long/Short', 'Long-Only'],
    'Total Return': [long_short.total_return(), long_only.total_return()],
    'Annualized Return': [long_short.annualized_return(), long_only.annualized_return()],
    'Max Drawdown': [long_short.max_drawdown(), long_only.max_drawdown()],
    'Sharpe Ratio': [long_short.sharpe_ratio(), long_only.sharpe_ratio()],
}
comparison_df = pd.DataFrame(metrics)
```

### Chart with 2 equity curves (D-05)
```python
fig, ax = plt.subplots(figsize=(14, 7))
ax.plot(dates, long_short_equity, label='Long/Short', color='blue', linewidth=1.5)
ax.plot(dates, long_only_equity, label='Long-Only', color='orange', linewidth=1.5)
ax.set_ylabel('Equity (normalized to 1.0)')
ax.set_title(f'{market} - Long-Only vs Long/Short Performance')
ax.legend()
ax.grid(True, alpha=0.3)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via uv run) |
| Config file | No pytest.ini -- default discovery |
| Quick run command | `uv run python -m pytest tests/test_v2_performance.py tests/test_short_position.py -x -q` |
| Full suite command | `uv run python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHORT-02 | Short P&L in equity curve -- inverse return when SELL | unit | `uv run python -m pytest tests/test_short_equity.py -x` | Wave 0 |
| SHORT-02 | Manual verification on 3+ trades | integration | `uv run python -m pytest tests/test_short_equity.py::test_manual_verification -x` | Wave 0 |
| TRANS-02 | Comparison script runs for NASDAQ | smoke | `uv run python analysis/compare_long_short.py --market nasdaq` | Wave 0 |
| TRANS-02 | Comparison script runs for VN30 | smoke | `uv run python analysis/compare_long_short.py --market vn30` | Wave 0 |
| TRANS-03 | Rule docs updated | manual-only | Visual inspection of docs/rules_mdm_v2.md and docs/rules_mdm_hybrid.md | N/A |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_v2_performance.py tests/test_short_position.py -x -q`
- **Per wave merge:** `uv run python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_short_equity.py` -- covers SHORT-02 (inverse return in equity curve, manual 3-trade verification)
- [ ] Extend `tests/test_v2_performance.py` with SELL state equity cases

## Sources

### Primary (HIGH confidence)
- `strategies/mdm_hybrid/performance.py` -- current equity curve implementation, line 70-94
- `strategies/mdm_hybrid/position_manager.py` -- cover_short() P&L formula, line 148-174
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` -- engine run() producing state column
- `strategies/mdm_hybrid/config.py` -- HybridConfig with short_mode field
- `analysis/validate_v2.py` -- comparison script pattern (630 lines)
- `docs/rules_mdm_hybrid.md` -- existing rule doc structure (Vietnamese)
- `docs/rules_mdm_v2.md` -- existing rule doc structure (Vietnamese)
- `18-CONTEXT.md` -- all locked decisions D-01 through D-09

### Secondary (MEDIUM confidence)
- `tests/test_short_position.py` -- existing short position tests from Phase 16
- `tests/test_v2_performance.py` -- existing performance analyzer tests

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all existing project dependencies
- Architecture: HIGH - clear modification targets identified, proven patterns to follow
- Pitfalls: HIGH - derived from direct code inspection of equity curve and P&L formulas

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable -- this is internal project code, not external dependencies)
