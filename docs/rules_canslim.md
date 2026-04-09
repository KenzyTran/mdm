# CANSLIM Rules (Phase 29)

> Status: STUB — filled in by plans 29-02..29-09.
> Code-Docs Sync Rule: any edit to strategies/canslim/ MUST update this file in the same commit (CLAUDE.md).

## 1. Universe

Implemented by `strategies/canslim/universe.py::UniverseLoader` (plan 29-03).

**Three modes** (select at construction time):

1. **`current-vn100`** — reads `stock_list` where `nhomtop IN ('VN30','VN100')`. Simple and fast, but survivorship-biased (uses today's membership for historical dates).
2. **`liquidity-reconstructed`** — top-100 tickers by 60-day average dollar turnover (`AVG(closeindex * totalvol)`) ending at the most recent **Jan 1 / Jul 1 rebalance date** `<= as_of_date`. Between two rebalance dates the set is **frozen** (no intra-period churn). Approximates point-in-time VN100 without index-committee data.
3. **`vn30-only`** — `stock_list.nhomtop = 'VN30'` only. Narrow sanity baseline.

**Rebalance policy (liquidity-reconstructed):** semi-annual, `_last_rebalance_date(d)` returns `date(y, 7, 1)` if `d >= Jul 1`, else `date(y, 1, 1)` if `d >= Jan 1`, else `date(y-1, 7, 1)`.

**D-05 history-length filter:** after mode selection, every candidate must have at least `min_history_days` (default **252**) rows in `stock_eod` at or before `as_of_date`. Shorter histories are dropped so downstream indicators (200d MA, 52w RS, etc.) have enough data.

**Usage:**

```python
loader = UniverseLoader(mode="current-vn100", pg_engine=pg)
tickers = loader.get(as_of_date=date(2025, 6, 1))  # → Set[str]
```

Closes requirements UNIV-01, UNIV-02, UNIV-03.

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

Implemented by `strategies/canslim/rules/fundamental.py::compute_fundamentals` (plan 29-05). Closes CANS-01..CANS-04.

**Entry point:**

```python
compute_fundamentals(ticker, as_of_date, config, sector_router, mysql_engine)
# -> (c_pass, c_plus_pass, a_pass, a_plus_pass)
```

**Sector branching (D-06):**

| Sector bucket        | Table                | Value column (from schema_lock.json)         |
| -------------------- | -------------------- | -------------------------------------------- |
| `bank`               | `is_quarter_bank`    | `is_quarter_bank_ppop_column` (PPOP)         |
| `other`              | `is_quarter_nonbank` | `is_quarter_nonbank_eps_column` (net profit) |
| `ctck` / `insurance` | — (excluded)         | returns `(False, False, False, False)` (D-07) |

**Schema-lock fallback:** if `schema_lock.json.locked.is_quarter_bank_ppop_column` is `null` (introspector could not find an unambiguous PPOP column in `is_quarter_bank`), the bank branch falls back to the non-bank EPS column name. This is a documented approximation — re-run `scripts/introspect_canslim_schema.py` once a bank PPOP column is identified.

**Formulas (all newest-first):**

| Rule | Formula                                                                     |
| ---- | --------------------------------------------------------------------------- |
| C    | `(values[0] - values[4]) / abs(values[4]) >= config.c_threshold`            |
| C+   | `yoy(0) > (yoy(1) + yoy(2)) / 2` where `yoy(i)=(v[i]-v[i+4])/abs(v[i+4])`   |
| A    | `(sum(values[0:4]) / sum(values[8:12])) ** (1/2) - 1 >= config.a_threshold` |
| A+   | `all(annuals[:3] > 0)` where `annuals[k] = sum(values[4k : 4k+4])`          |

Insufficient history returns `False` (not an exception): C needs 5 quarters, C+ needs 7, A needs 12, A+ needs 3 rolling-TTM windows (i.e. 12 quarters).

**Look-ahead guard (D-11):** every row loaded from MySQL is passed through `connectors/eps.py::resolve_eps_publish_date`, which either reuses an existing `publish_date` / `announce_date` / `updated_at` column or imputes one from `yearreport` + `lengthreport` (period_end + 45 days for quarters, +90 days for annuals). Rows with `publish_date > as_of_date` are dropped BEFORE any rule is evaluated, so the scorer can never peek at a quarter before it was filed. This is the only acceptable lookahead discipline because `schema_lock.publish_date_column` is legitimately `null` — no real publish-date column exists in the MySQL fundamentals tables today.

**Tests:** `tests/canslim/test_rules_fundamental.py` covers pure helpers (C / C+ / A / A+), the look-ahead guard, bank-table routing, ctck exclusion, and insufficient-history fall-through.

## 5. Technical Rule (N) + RS (L)

Implemented by `strategies/canslim/rules/technical.py` (N + S helper) and
`strategies/canslim/rules/rs.py` (L). Closes CANS-05 and CANS-07.

### N rule — close near 252-day high (CANS-05)

`compute_n(ohlcv, as_of_date, config)` returns True iff

    close >= (1 - config.n_within_high) * rolling_max(high, 252)

using the ``config.min_history_days`` (default 252) bars at or before
``as_of_date``. Tickers with insufficient history return False. Default
``n_within_high = 0.15`` → close must be within 15% of the 52-week high.

### S helper — breakout volume (CANS-06 helper)

`compute_s(ohlcv, as_of_date, config)` returns True iff

    today_volume >= config.s_vol_mult * avgvol50

where ``avgvol50`` is the mean of the 50 bars preceding ``as_of_date``.
Default ``s_vol_mult = 1.5``. Returns False if fewer than 51 bars are
available. The full S rule (breakout price action) lives alongside the flow
rules in plan 29-07; this helper is the volume gate.

### L rule — RS rating (CANS-07)

`compute_rs_ratings(panel, as_of_date, universe, config)` computes the
**locked RS formula**:

    raw_rs = 0.4*ROC(63) + 0.2*ROC(126) + 0.2*ROC(189) + 0.2*ROC(252)

then **percentile-ranks within the active universe** at ``as_of_date``
(higher = stronger, 100 = universe leader). Lookbacks and weights come
from `config.rs_roc_days` and `config.rs_weights` so sweep scripts can
tune them without editing source. Tickers with fewer than
`config.min_history_days` bars get `rs_rating = NaN` and fail the L rule.

**L pass:** `rs_rating >= config.l_rs_threshold` (default 80).

Returns a `pd.Series` indexed by ticker in `[0, 100]` ∪ {NaN}.

**Tests:** `tests/canslim/test_rules_technical.py` (7 tests — N true/false/insufficient, S true/false/insufficient, module imports) and `tests/canslim/test_rules_rs.py` (7 tests — single-ticker percentile 100, two-ticker ranking, insufficient history NaN, l_pass threshold, panel filtering, formula numeric check, module imports).

## 6. Flow (I) + Liquidity (Liq)

Implemented by `strategies/canslim/rules/flow.py` and `strategies/canslim/rules/liquidity.py` (plan 29-07). Closes CANS-06, CANS-08, CANS-09.

### 6.1 I — Foreign net-buy flow (CANS-08)

`compute_i(ticker, as_of_date, config, pg_engine) -> bool`

Sums `fbvalue - fsvalue` from Postgres `stock_foreign_eod` over the last `config.i_lookback_days` trading rows (default **20**) strictly **before** `as_of_date`. Rule passes iff the sum is strictly greater than zero.

```sql
SELECT (fbvalue - fsvalue) AS net_buy
FROM stock_foreign_eod
WHERE stockcode = :t AND tradingdate < :d
ORDER BY tradingdate DESC
LIMIT :n
```

**Pre-2022 fallback (critical):** `stock_foreign_eod` has no rows before **2022-04-07** (locked by research in 29-RESEARCH.md). Any `as_of_date < 2022-04-07` returns `i_pass=True` automatically, without querying. This prevents starving historical backtests of signal while keeping the fallback explicit and grep-able via the `FOREIGN_DATA_START` constant in `flow.py`.

| Case                         | Behavior             |
| ---------------------------- | -------------------- |
| `as_of_date < 2022-04-07`    | **True** (fallback)  |
| Post-2022, sum > 0           | True                 |
| Post-2022, sum == 0          | False (strict `> 0`) |
| Post-2022, sum < 0           | False                |
| Post-2022, no rows in table  | False                |

### 6.2 S — Volume surge wrapper (CANS-06)

`flow.compute_s(ohlcv, as_of_date, config)` is a thin wrapper delegating to `strategies.canslim.rules.technical.compute_s` (implemented in plan 29-06). The wrapper exists so the scorer imports all "per-signal" rules from a single surface (`flow.compute_i`, `flow.compute_s`) while the numeric logic stays in `technical.py`.

### 6.3 Liq — Liquidity gate (CANS-09)

`compute_liq(ohlcv, as_of_date, config) -> bool`

20-day rolling **median** of turnover (`closeindex * totalvol`) must meet or exceed `config.liquidity_min_turnover_vnd` (default **5_000_000_000** VND = 5B VND).

**Why median, not mean:** a single fat-finger print or crossing trade can drag an otherwise illiquid name above the threshold if averaged. Median is robust to that tail. Fewer than 20 bars of history → False (insufficient data, no silent pass).

## 7. Composite Score
_TBD — plan 29-08_

## 8. Validation vs rank_top_stocks.diem_canslim
_TBD — plan 29-09_
