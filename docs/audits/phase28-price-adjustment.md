# Phase 28 — Price Adjustment Convention

**Source table:** `stock_eod` (Postgres, `vpt_wong_stock_v1`)
**Adjustment column:** `totaladjustrate`
**Helper:** `connectors.adjust.adjust_ohlc`

## Convention (locked, per phase 28 D-05/D-06)

`stock_eod` price columns are **unadjusted**. To get a continuous series
suitable for backtesting:

```
adj_open   = openprice    * totaladjustrate
adj_high   = highestprice * totaladjustrate
adj_low    = lowestprice  * totaladjustrate
adj_close  = closeprice   * totaladjustrate
adj_volume = totalvol                       # NOT adjusted (D-05)
```

All downstream backtest code (Phases 29+) MUST consume `adj_*` columns.

## Spot-check protocol

Run for 2-3 known split/dividend tickers:

```bash
uv run python scripts/spot_check_adjust.py VNM 2018-01-01 2024-12-31
uv run python scripts/spot_check_adjust.py HPG 2018-01-01 2024-12-31
uv run python scripts/spot_check_adjust.py FPT 2018-01-01 2024-12-31
```

Confirm visually that `adj_close` produces a continuous curve across
rate-change boundaries (no step discontinuity).

## Volume note

`totalvol` is intentionally NOT adjusted in v1. If a future audit shows
volume discontinuities at split boundaries, revisit per D (deferred ideas).
