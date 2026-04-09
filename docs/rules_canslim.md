# CANSLIM Rules (Phase 29)

> Status: STUB — filled in by plans 29-02..29-09.
> Code-Docs Sync Rule: any edit to strategies/canslim/ MUST update this file in the same commit (CLAUDE.md).

## 1. Universe
_TBD — plan 29-03_

## 2. Sector Routing
_TBD — plan 29-04_

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
