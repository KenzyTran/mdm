# CANSLIM Rules (Phase 29)

> Status: STUB — filled in by plans 29-02..29-09.
> Code-Docs Sync Rule: any edit to strategies/canslim/ MUST update this file in the same commit (CLAUDE.md).

## 1. Universe
_TBD — plan 29-03_

## 2. Sector Routing

Owned by `strategies/canslim/sectors.py` (`SectorRouter`). Closes CANS-10.

Each VN100 ticker is classified into one of four buckets using the
`stock_list.sector` column (locked as `nhom` in `schema_lock.json`, plan 29-01):

| Bucket      | Trigger (case-insensitive substring) | Downstream table       | Score branch          |
| ----------- | ------------------------------------ | ---------------------- | --------------------- |
| `bank`      | `ngân hàng` / `ngan hang` / `bank`   | `is_quarter_bank`      | PPOP growth (D-06)    |
| `ctck`      | `chứng khoán` / `securities`         | `is_quarter_stock`     | **EXCLUDED** (D-07)   |
| `insurance` | `bảo hiểm` / `insurance`             | `is_quarter_insurance` | **EXCLUDED** (D-07)   |
| `other`     | anything else                        | `is_quarter_nonbank`   | EPS growth (default)  |

**Exclusion policy (D-07):** Securities firms and insurance companies use
bespoke income-statement schemas that CANSLIM's C/A rules don't support. They
are filtered out of the universe before scoring via
`SectorRouter.is_excluded(ticker)`.

**Fail-loud rule (D-08):** `SectorRouter.from_postgres` raises `RuntimeError`
if the locked sector column is NULL for >50% of tickers — this means
`schema_lock.json` is stale and `scripts/introspect_canslim_schema.py` must
be re-run. Silent fallback to "other" across the whole universe would corrupt
the scorer. Individual unknown tickers emit a warning and default to `other`.

**Tests:** `tests/canslim/test_sectors.py` (9 tests — bank / ctck / insurance / other routing, unknown-ticker warn, `is_excluded`, `from_postgres` happy path, fail-loud on >50% missing).

## 3. CanslimConfig

Dataclass `strategies.canslim.config.CanslimConfig` centralizes every threshold the scorer consumes. Defaults lock decision **D-12** from `29-CONTEXT.md`. All fields are kwarg-overridable (used by sweep scripts); `__post_init__` rejects invalid ranges with actionable `ValueError`s; `to_dict()` / `dataclasses.asdict()` serialize round-trip.

| Field | Default | Meaning | Valid range |
|-------|---------|---------|-------------|
| `c_threshold` | `0.20` | C: quarterly EPS YoY growth minimum | `>= 0` |
| `a_threshold` | `0.15` | A: 3yr EPS CAGR minimum | `>= 0` |
| `n_within_high` | `0.15` | N: close must be within this fraction of 252d high | `(0, 1]` |
| `s_vol_mult` | `1.5` | S: breakout volume multiplier over avgvol50 | `>= 1` |
| `l_rs_threshold` | `80.0` | L: minimum RS percentile rank | `[0, 100]` |
| `i_lookback_days` | `20` | I: foreign net-buy lookback window (trading days) | `>= 1` |
| `liquidity_min_turnover_vnd` | `5_000_000_000.0` | Liquidity: minimum 20d median turnover (VND) | `>= 0` |
| `rs_roc_days` | `(63, 126, 189, 252)` | L: ROC lookback windows (trading days) | aligns with `rs_weights` |
| `rs_weights` | `(0.4, 0.2, 0.2, 0.2)` | L: weights applied to each ROC window | sums to `1.0` |
| `min_history_days` | `252` | Minimum OHLCV history required to score a ticker | `>= 1` |

**Tests:** `tests/canslim/test_config.py` (9 tests — defaults, overrides, validation, asdict round-trip, mutability).


## 4. Fundamental Rules (C, C+, A, A+)
_TBD — plan 29-05_

## 5. Technical Rule (N) + RS (L)
_TBD — plan 29-06_

## 6. Flow (I) + Liquidity (Liq)
_TBD — plan 29-07_

## 7. Composite Score
_TBD — plan 29-08_

## 8. Validation vs rank_top_stocks.diem_canslim
_TBD — plan 29-09_
