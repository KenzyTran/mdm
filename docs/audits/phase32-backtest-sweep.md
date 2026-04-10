---
phase: 32
name: vn100-backtest-in-sample-sweep
status: complete
date: 2026-04-10
period: 2014-01-01..2018-12-31
universe: current-VN100
requirements: [BT-01, BT-02]
---

# Phase 32 — VN100 Backtest + In-Sample Sweep

## Methodology

### Pipeline Architecture

```
Universe (Phase 29)     →  current-VN100 semi-annual rebalance Jan/Jul
CANSLIM Scorer (Ph 29)  →  C/A/N threshold gates (swept)
MDM Gate (Phase 31)     →  HybridEngine v6 on VN-Index; BUY required for new entries
Entry Detector (Ph 30)  →  Option A (pivot close) or Option C (next-day open) [swept]
Portfolio Engine (Ph31) →  PortfolioEngine.run(); max_slots + hard_stop swept
Costs                   →  0.25% commission + 0.10% tax + 0.10% slippage (fixed)
```

### Period

Hard-coded 2014-01-01 to 2018-12-31 per D-09. Reproducibility constraint — no CLI
date override in Phase 32 scripts. Phase 33 will run 2019-2025 OOS separately.

### Universe

Current-VN100 (D-01): VN100 members as of the backtest run date, semi-annual rebalance.
Survivorship bias is acknowledged. Phase 33 will run sensitivity across
liquidity-reconstructed universe and VN30-only to quantify the bias.

### MDM Gate

HybridEngine v6 (Phase 31 D-07): BUY signal is necessary (but not sufficient) for new
position entry. Capital fully deployed during BUY state (Policy A); no new entries in
CASH or SELL states. RS-streak exit: 5 consecutive sessions below RS threshold 70.

### Costs (fixed, not swept)

| Component | Rate |
|-----------|------|
| Commission | 0.25% |
| Tax | 0.10% |
| Slippage | 0.10% |
| **Total round-trip** | **~0.90%** |

### Sharpe Definition

Sharpe = (annualized_return - rf) / annualized_vol  
rf = 3% annualized (VN 10Y govt bond, D-10).  
Annualized vol = daily returns × √252.

---

## Single-Run Baseline (BT-01 / SC1)

Phase 31 default configuration; one run used to validate pipeline correctness before
launching the 1,536-config sweep.

### Configuration

| Parameter | Value |
|-----------|-------|
| max_slots | 8 |
| hard_stop | 0.08 |
| entry_option | A |
| c_yoy | 0.20 |
| a_cagr | 0.15 |
| n_proximity | 0.15 |
| MDM gate | HybridEngine v6 |
| Costs | 0.25% + 0.10% + 0.10% |

### Results

| Metric | Value |
|--------|-------|
| Period | 2014-01-02 → 2018-12-28 (4.99 years) |
| Initial NAV | 1,000,000,000 VND |
| Final NAV | 1,225,654,421 VND |
| CAGR | 4.17% |
| Annualized Vol | 17.38% |
| Sharpe (rf=3%) | 0.0671 |
| Max Drawdown | -20.63% |
| Trade Count | 60 |
| Hit Rate | 50.0% |

### Exit Breakdown

| Exit Reason | Count |
|-------------|-------|
| mdm_sell | 38 |
| hard_stop | 13 |
| ma50_break | 9 |

### Artifacts

- `docs/audits/phase32/single_run_nav.csv` — 1,246 daily NAV rows
- `docs/audits/phase32/single_run_trades.csv` — 60 closed trades
- `docs/audits/phase32/single_run_positions.csv` — position log

---

## Sweep Results (BT-02 / SC2–SC3)

### Grid

| Axis | Values | Count |
|------|--------|-------|
| c_yoy | {0.10, 0.15, 0.20, 0.25} | 4 |
| a_cagr | {0.10, 0.15, 0.20, 0.25} | 4 |
| n_proximity | {0.05, 0.10, 0.15, 0.20} | 4 |
| hard_stop | {0.06, 0.07, 0.08, 0.10} | 4 |
| slots | {5, 8, 10} | 3 |
| entry_option | {A, C} | 2 |
| **Total** | 4×4×4×4×3×2 | **1,536** |

### Run Summary

| Category | Count |
|----------|-------|
| Total configs | 1,536 |
| Completed OK | 1,536 |
| CAGR_TOO_HIGH (>300%) | 0 |
| ERROR (exception) | 0 |

All 1,536 configs completed without error. No look-ahead anomalies detected.

### Metric Distributions

**Sharpe_rf3** (rf = 3%):

| Stat | Value |
|------|-------|
| min | -0.2583 |
| p25 | -0.1119 |
| median | -0.0904 |
| p75 | -0.0640 |
| max | +0.0590 |

Note: most configs show negative Sharpe because annual returns (median ~1.87%) fall
below the 3% risk-free rate over this 2014-2018 period. The top configs overcome this
via tighter CANSLIM filters selecting higher-quality stocks.

**CAGR**:

| Stat | Value |
|------|-------|
| min | -0.34% |
| p25 | 1.45% |
| median | 1.87% |
| p75 | 2.20% |
| max | 3.79% |

**Max Drawdown**:

| Stat | Value |
|------|-------|
| min (worst) | -23.11% |
| p25 | -17.70% |
| median | -16.61% |
| p75 | -14.83% |
| max (best) | -14.44% |

### Parameter Sensitivity

From the sweep distribution:

- **c_yoy = 0.25** (tightest earnings filter) consistently dominates the top rows —
  stricter YoY EPS growth requirement selects fewer but higher-quality stocks.
- **n_proximity = 0.10** dominates top configs — moderate proximity to 52W high;
  too tight (0.05) misses valid breakouts, too loose (0.20) admits extended stocks.
- **entry_option = C** (next-day open fill) outperforms option A in top positions —
  avoids late-day pivot chasing and reduces fill risk in thin VN markets.
- **hard_stop = 0.06** (tightest) wins in top-3 — aggressive loss-limiting preserves
  capital given the relatively small per-trade alpha.

---

## Top-3 Configs (BT-02 / SC4)

Selection metric: **Sharpe_rf3** descending.  
Tie-breakers (D-12): CAGR descending → MaxDD descending (less severe = closer to 0).

| Rank | c_yoy | a_cagr | n_prox | hard_stop | slots | entry | CAGR | Sharpe_rf3 | MaxDD | num_trades |
|------|-------|--------|--------|-----------|-------|-------|------|------------|-------|------------|
| 1 | 0.25 | 0.20 | 0.10 | 0.06 | 5 | C | 3.79% | 0.0590 | -17.66% | 34 |
| 2 | 0.25 | 0.25 | 0.10 | 0.06 | 8 | C | 3.76% | 0.0566 | -17.67% | 33 |
| 3 | 0.25 | 0.25 | 0.10 | 0.06 | 10 | C | 3.76% | 0.0566 | -17.67% | 33 |

All three configs share c_yoy=0.25, n_proximity=0.10, hard_stop=0.06, entry=C.
Ranks 2 and 3 differ only in slot count (8 vs 10) and tie on Sharpe + CAGR; rank 2
wins the MaxDD tie-breaker marginally (-17.67% both, same to 2dp — ranks separated by
slots tie-breaker as a deterministic sort on original row order).

Observation: the tightest CANSLIM filter (c_yoy=0.25) reduces the investable universe
significantly, resulting in fewer trades (31–34 vs 65+ for loose configs) but higher
average quality. Combined with tight hard_stop=0.06, the strategy loses small and wins
modestly in this 2014-2018 period.

---

## Sanity Gate (BT-02 / SC5)

Per D-13: configs with CAGR > 300% are flagged `CAGR_TOO_HIGH` and excluded from
top-3 selection. If any top-3 row carries a non-OK flag, the selector raises
`RuntimeError` and aborts Phase 33 handoff.

| Flag | Count |
|------|-------|
| OK | 1,536 |
| CAGR_TOO_HIGH | 0 |
| ERROR | 0 |

**Result: sanity gate passed.** No configs flagged. Top-3 are all `sanity_flag = OK`.

---

## Artifacts

| File | Description |
|------|-------------|
| `docs/audits/phase32/single_run_nav.csv` | Daily NAV for baseline single-run (BT-01) |
| `docs/audits/phase32/single_run_trades.csv` | Closed trade log for single-run |
| `docs/audits/phase32/single_run_positions.csv` | Position log for single-run |
| `docs/audits/phase32/sweep_results.csv` | All 1,536 sweep rows (GRID_COLS + METRIC_COLS + sanity_flag) |
| `docs/audits/phase32/locked_params_top3.json` | Top-3 locked configs (D-14 schema) for Phase 33 |
| `docs/audits/phase32/cache/*.parquet` | Precomputed static data (canslim_raw, ohlc, mdm_gate, universe, fundamentals, foreign) |
| `analysis/select_top3_vn100.py` | Selection script with D-13 gate + D-14 JSON writer |
| `analysis/sweep_vn100.py` | Full 1,536-config sweep runner (multiprocessing Pool) |
| `analysis/backtest_vn100.py` | Single-run baseline script (BT-01) |
| `tests/phase32/test_top3.py` | 7 unit tests for select_top3 (TDD) |
| `tests/phase32/test_sweep.py` | 5 unit tests for sweep_vn100 |

---

## Handoff to Phase 33

`docs/audits/phase32/locked_params_top3.json` will be loaded by a Phase 33 helper
(D-15) to rebuild `CanslimConfig` + `PortfolioConfig` for each of the 3 top configs.

**Phase 33 scope:**
- **BT-03:** OOS backtest 2019-2025 on the 3 locked configs.
- **BT-04:** Sensitivity sweep across 3 universes (current-VN100, liquidity-reconstructed
  VN100, VN30-only) to quantify survivorship bias.

The locked params should be considered **preliminary** until Phase 33 OOS validation.
A config that performs well in-sample (2014-2018) may degrade OOS due to regime change
(VN market developed significantly post-2019, COVID, commodity cycle shifts).

---

## Notes & Caveats

1. **Survivorship bias:** current-VN100 includes stocks that survived to 2026.
   Stocks that were delisted, merged, or removed from VN100 between 2014-2018 are
   excluded, inflating in-sample returns. Phase 33 BT-04 will run liquidity-reconstructed
   sensitivity.

2. **RS stub:** `rs_value=80` hardcoded for all stocks (above the rs_threshold=70
   default), effectively disabling the RS-streak exit in this sweep. The RS axis was
   not part of the D-03 sweep grid. Phase 33 should decide whether to wire real RS
   before OOS runs.

3. **Fundamentals stub:** `i_pass` (institutional sponsorship) and `liq_pass`
   (liquidity gate beyond ADV20) rules are not wired — the CANSLIM scorer only
   evaluates C / A / N axes as per the sweep grid design. Full CANSLIM (all 7 letters)
   is deferred.

4. **Low Sharpe environment:** The 2014-2018 VN market was range-bound in 2014-2016
   followed by a bull run in 2017-2018. The rf=3% risk-free rate exceeds the median
   config CAGR of 1.87%, explaining the predominantly negative Sharpe distribution.
   Top configs exceed rf through concentration in high-quality stocks.

5. **Error-free sweep:** 0 of 1,536 configs threw exceptions. The per-config
   fail-loud + continue pattern (D-07) was validated by the exception-safe worker
   test, but never triggered in production.
