# Phase 29: VN100 Universe + CANSLIM Scorer — Research

**Researched:** 2026-04-09
**Domain:** Equity factor scoring (CANSLIM) + point-in-time universe construction on VN100 daily data
**Confidence:** HIGH (all data shapes, connectors, and sector routing verified from Phase 28 live audit)

## Summary

Phase 29 is mostly a wiring problem, not a discovery problem. Phase 28 already shipped the hard parts: tested Postgres + MySQL connectors, the `adjust_ohlc` price-adjustment helper, `resolve_eps_publish_date` for the publish-date look-ahead guard, and a live audit confirming the VN100 universe resolves via `stock_list.nhomtop IN ('VN30','VN100')` (100 tickers, 16 EPS-sparse, 0 missing from `stock_foreign_eod`, which starts 2022-04-07).

The job is: stand up a new `strategies/canslim/` package that pulls adjusted OHLCV + foreign flow from Postgres, pulls quarterly/annual EPS from the 4 `is_quarter_*` MySQL tables (routed by sector), computes each CANSLIM letter (C, C+, A, A+, N, S, L, I, Liquidity) as a boolean per `(date, ticker)`, emits a tidy DataFrame, and spot-checks against MySQL `rank_top_stocks.diem_canslim`.

**Primary recommendation:** Mirror the `vn30_vsa/` package layout. Build `strategies/canslim/` with `config.py` (dataclass), `universe.py` (3 modes), `rules/` (one file per letter-family for clarity), `scorer.py` (orchestrator returning the tidy DataFrame), plus a validation script under `scripts/validate_canslim.py`. Use pandas rolling windows (already proven in `models/indicators.py`) for N/S/L; use `connectors.eps.resolve_eps_publish_date` + a point-in-time filter `publish_date <= as_of_date` for C/C+/A/A+.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Universe Construction**
- **D-01:** Default universe mode = **current-VN100** (from `stock_list.nhomtop IN ('VN30','VN100')`). Survivorship bias accepted and explicitly documented in the validation report.
- **D-02:** All three modes implemented and selectable via config: `current-vn100` | `liquidity-reconstructed` | `vn30-only`. Only `current-vn100` is validated in Phase 29; the other two are wired up but not deeply tested.
- **D-03:** Semi-annual rebalance (Jan/Jul) applies to `liquidity-reconstructed` mode only. `current-vn100` uses the live list at every `as_of_date` (no intra-phase step-changes).
- **D-04:** Delisted tickers are flagged, not included. True point-in-time reconstruction stays deferred.
- **D-05:** RS edge case — any ticker with **<252 trading days of history** at `as_of_date` is dropped for that date.

**Sector Routing**
- **D-06:** Sector comes from the `stock_list` sector/industry column (exact column name to be confirmed in research step below). Map into four buckets: `bank`, `ctck`, `insurance`, `other`.
- **D-07:** Routing:
  - `other` → `is_quarter_nonbank`, use C/A directly
  - `bank` → `is_quarter_bank`, substitute **PPOP growth** for EPS growth in C/A
  - `ctck` and `insurance` → **excluded** from scoring V1
- **D-08:** If the expected sector column is missing or has unexpected values, fail loudly during scorer initialization — no silent fallback.

**Scorer Output**
- **D-09:** Tidy DataFrame, one row per `(date, ticker)`, columns: `date`, `ticker`, `sector`, `c_pass`, `c_plus_pass`, `a_pass`, `a_plus_pass`, `n_pass`, `s_pass`, `l_pass`, `i_pass`, `liq_pass`, `rs_rating` (0–100), `score` (0–100 composite).
- **D-10:** Phase 30 consumes this shape directly. Per-letter booleans are kept specifically so Phase 30 can debug which rule killed a candidate.
- **D-11:** Scorer must respect `publish_date` guard from `connectors/eps.py`. Every EPS read filters `publish_date <= as_of_date`. Enforced in unit tests.

**CanslimConfig**
- **D-12:** `CanslimConfig` dataclass at `strategies/canslim/config.py`. Defaults: C ≥ 0.20, A ≥ 0.15, N within 15% of 252d high, S ≥ 1.5× avgvol50, L ≥ 80 percentile, I = sum(foreign_net_buy[T-20..T-1]) > 0, Liquidity = 20d median turnover ≥ 5B VND.
- **D-13:** All thresholds overridable via constructor kwargs. No YAML/JSON config in Phase 29.

**Validation**
- **D-14:** Spot-check on **5 random tradingdates in 2023–2025** drawn from dates where `rank_top_stocks.diem_canslim` has data. Compare top-10 composite-score tickers vs baseline top-10. Acceptance: **≥4/10 overlap on at least 3 of the 5 dates**.
- **D-15:** Validation report at `docs/audits/phase29-canslim-validation.md` + companion CSVs under `docs/audits/phase29/`. Markdown + CSV (no notebooks), same as Phase 28.
- **D-16:** Report must include, per sampled date: our top-10 with sub-scores, baseline top-10, overlap set, qualitative notes on discrepancies.

### Claude's Discretion

- Exact composite-score weighting formula (document in `docs/rules_canslim.md`).
- Caching strategy for expensive reads (EPS, foreign-net-buy history).
- Unit-test layout under `tests/`.
- Internal module split inside `strategies/canslim/` (one file per letter vs one scorer file).
- Whether to expose a CLI entrypoint in Phase 29 or wait for Phase 30.

### Deferred Ideas (OUT OF SCOPE)

- Real point-in-time VN100 reconstruction including delisted tickers (Phase 28 deferred list).
- YAML/JSON configuration files for `CanslimConfig`.
- Deep validation of `liquidity-reconstructed` and `vn30-only` modes.
- Special handling for sparse-EPS tickers (POW, SSB, BCM, GEE, DSE).
- CLI entrypoint for the scorer.
- Volume-adjustment revisit.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UNIV-01 | VN100 universe loader (`stock_list.nhomtop` or proxy) | Phase 28 confirmed `nhomtop IN ('VN30','VN100')` returns exactly 100 tickers; loader is a 1-query helper in `connectors/postgres.py` or new `strategies/canslim/universe.py` |
| UNIV-02 | Semi-annual (Jan/Jul) rebalance, stable between dates | Only applies to `liquidity-reconstructed` mode per D-03; pandas `date.month in (1,7)` + `as_of_date` snap is sufficient |
| UNIV-03 | Three-mode sensitivity: current-VN100 / liquidity-reconstructed / VN30-only | Mode enum in `CanslimConfig`; each mode is a pure function `(as_of_date) -> set[ticker]` |
| CANS-01 | C rule — quarterly EPS YoY ≥ 20% configurable, publish_date guard | Use `connectors.mysql.load_is_quarter(sector=...)` + `connectors.eps.resolve_eps_publish_date` + filter `publish_date <= as_of_date`; group by ticker, compute YoY on `epsbasicvnd` (confirm column name live) |
| CANS-02 | C+ — EPS acceleration vs prior 2 quarters | Same source; compare latest YoY to avg of prior 2 YoYs |
| CANS-03 | A — 3yr EPS CAGR ≥ 15% | Same source, use annual roll-up (sum of 4 trailing quarters × 3 years ago) or `is_year_*` tables if Phase 28 exposed them; fall back to TTM-3yr-ago |
| CANS-04 | A+ — annual EPS positive each of last 3 years | Sum 4 quarters for each of last 3 completed years; all > 0 |
| CANS-05 | N — close within 15% of 252-day high | `models/indicators.py` rolling-max pattern; use `adj_close` |
| CANS-06 | S — breakout volume ≥ 1.5× avgvol50 | `totalvol / rolling(50).mean() >= 1.5` |
| CANS-07 | L — IBD RS rating `0.4*ROC63+0.2*ROC126+0.2*ROC189+0.2*ROC252`, percentile ≥ 80 within active universe | Compute raw score per ticker, then `df.groupby('date')['rs_raw'].rank(pct=True)*100`; requires 252 days history (D-05 drop rule) |
| CANS-08 | I — `sum(foreign_net_buy[T-20..T-1]) > 0` | `stock_foreign_eod` (Postgres) — Phase 28 flagged **data only from 2022-04-07**, so pre-2022 `i_pass` will be NaN; document in validation report |
| CANS-09 | Liquidity — 20d median turnover ≥ 5B VND | `(adj_close * totalvol).rolling(20).median() >= 5e9` |
| CANS-10 | Sector handling — non-fin C/A direct, banks PPOP, CTCK/Insurance excluded | D-06/D-07/D-08; requires confirming `stock_list` sector column name during Wave 0 |
| CANS-11 | `CanslimConfig` dataclass + per-day score function returning pass/fail + composite | D-12/D-13; mirror `models/config.MDMConfig` post-init validation pattern |
| CANS-12 | Validation: spot-check vs `rank_top_stocks.diem_canslim` | D-14/D-15/D-16; 5 dates × top-10 overlap |
</phase_requirements>

## Standard Stack

### Core (already in `pyproject.toml`, no new installs required)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | ≥2.0 | All DataFrame ops, rolling windows, percentile rank | Project lingua-franca |
| numpy | ≥1.24 | ROC, CAGR, composite math | Paired with pandas |
| SQLAlchemy | ≥2.0 | Already used by `connectors/postgres.py` + `mysql.py` | Phase 28 standard |
| python-dotenv | ≥1.2 | `.env` credentials | Phase 28 standard |
| pytest | ≥7 | Unit + integration tests with `@pytest.mark.integration` marker | Phase 28 wave-0 already added this + markers |

**No new dependencies should be added in Phase 29.** If the planner thinks one is needed, that's a signal to reconsider.

**Version verification:** Skipped — all libraries are already pinned from Phase 28. Rerunning `uv sync` is enough.

### Don't add
- `scipy` — not needed; pandas rolling + numpy cover all math
- `scikit-learn` — percentile ranking is a one-liner in pandas
- `ta-lib` — ROC is trivial
- YAML config libs — D-13 says no

## Architecture Patterns

### Recommended Project Structure
```
strategies/
└── canslim/
    ├── __init__.py          # re-export CanslimScorer, CanslimConfig, UniverseMode
    ├── config.py            # CanslimConfig dataclass + UniverseMode enum
    ├── universe.py          # load_universe(as_of_date, mode) -> set[str]
    ├── sectors.py           # classify_ticker(stock_list_row) -> Literal['bank','ctck','insurance','other']
    ├── rules/
    │   ├── __init__.py
    │   ├── fundamental.py   # C, C+, A, A+ (reads is_quarter_*, applies publish_date guard)
    │   ├── technical.py     # N, S (price/volume rolling windows)
    │   ├── rs.py            # L rule (IBD RS rating + percentile rank)
    │   ├── flow.py          # I rule (stock_foreign_eod 20d window)
    │   └── liquidity.py     # 20d median turnover
    ├── scorer.py            # CanslimScorer — orchestrator, returns tidy DataFrame
    └── baseline.py          # load_diem_canslim_baseline(dates) from MySQL rank_top_stocks

scripts/
└── validate_canslim.py      # picks 5 random dates, runs scorer, compares top-10 vs baseline, writes docs/audits/phase29-canslim-validation.md

tests/
├── test_canslim_config.py
├── test_canslim_universe.py
├── test_canslim_rules_fundamental.py   # CRITICAL: publish_date look-ahead tests
├── test_canslim_rules_technical.py
├── test_canslim_rules_rs.py
├── test_canslim_rules_flow.py
├── test_canslim_rules_liquidity.py
├── test_canslim_scorer.py              # end-to-end fake data
└── test_canslim_baseline.py            # @pytest.mark.integration
```

This matches the existing `vn30_vsa/` package style. One file per letter-family gives ~50–100 LoC per file — small enough to test independently.

### Pattern 1: Publish-Date Guard (critical, enforces no look-ahead)
**What:** Every read from `is_quarter_*` must go through `resolve_eps_publish_date` + be filtered to `publish_date <= as_of_date`.
**When to use:** C, C+, A, A+ rules.
**Example:**
```python
# strategies/canslim/rules/fundamental.py
from connectors.mysql import load_is_quarter
from connectors.eps import resolve_eps_publish_date

def load_eps_point_in_time(tickers, sector, as_of_date):
    raw = load_is_quarter(tickers, sector=sector)
    resolved = resolve_eps_publish_date(raw)
    pit = resolved[resolved["publish_date"] <= pd.Timestamp(as_of_date)]
    return pit.sort_values(["stockcode", "yearreport", "lengthreport"])
```

### Pattern 2: Tidy DataFrame output (Phase 30 contract)
**What:** Scorer returns `(date, ticker, sector, *_pass booleans, rs_rating, score)`.
**When to use:** The public API of `CanslimScorer.score(dates: list[date]) -> pd.DataFrame`.
**Example:**
```python
# strategies/canslim/scorer.py
class CanslimScorer:
    def __init__(self, config: CanslimConfig): ...
    def score(self, dates: list[pd.Timestamp]) -> pd.DataFrame:
        frames = [self._score_one_day(d) for d in dates]
        return pd.concat(frames, ignore_index=True)
```

### Pattern 3: Percentile-rank within active universe (for L rule)
```python
# strategies/canslim/rules/rs.py
def rs_rating(price_df: pd.DataFrame, as_of_date: pd.Timestamp) -> pd.Series:
    # price_df: multi-ticker, indexed by (date, ticker) with adj_close
    # Returns: Series indexed by ticker, values 0-100
    def roc(n): return price_df["adj_close"] / price_df["adj_close"].shift(n) - 1
    raw = 0.4*roc(63) + 0.2*roc(126) + 0.2*roc(189) + 0.2*roc(252)
    today = raw.loc[as_of_date]
    return today.rank(pct=True) * 100
```

### Pattern 4: Sector routing with fail-loud
```python
# strategies/canslim/sectors.py
_EXPECTED = {"bank", "ctck", "insurance", "other"}
def classify(stock_list_df: pd.DataFrame) -> pd.Series:
    # Must be confirmed during Wave 0: does stock_list have a 'sector'/'industry'/'nhomnganh' column?
    col = _pick_sector_column(stock_list_df)  # raises if none found
    mapped = stock_list_df[col].map(_SECTOR_MAP)
    bad = stock_list_df[mapped.isna()]
    if len(bad) > 0:
        raise ValueError(f"Unmapped sectors: {bad[col].unique().tolist()}")
    return mapped
```

### Anti-Patterns to Avoid
- **Loading EPS inside a per-day loop** — costs 250× DB hits. Load once up front, then filter by `publish_date <= as_of_date` in pandas.
- **Computing RS per ticker independently** — you need cross-sectional percentile ranking, so compute raw RS for all tickers first, then rank within each date.
- **Silent NaN propagation** — `i_pass` will be NaN for dates < 2022-04-07 (no foreign-flow data). Decide the policy explicitly (treat as False? skip I rule? require all others?) and document it.
- **Mutating input DataFrames** — every rule function should `df = df.copy()` at the top, matching `adjust_ohlc`/`resolve_eps_publish_date` precedent.
- **Hardcoding sector lists** — D-08 forbids this. Fail loud.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Price adjustment | Custom split/dividend math | `connectors.adjust.adjust_ohlc` | Phase 28, tested |
| EPS publish date | String parsing of yearreport | `connectors.eps.resolve_eps_publish_date` | Phase 28, tested |
| Postgres connection | `psycopg2.connect(...)` | `connectors.postgres.query / load_stock_eod` | Handles env + pooling |
| MySQL `is_quarter_*` routing | `if sector == 'bank': ...` | `connectors.mysql.load_is_quarter(sector=...)` | Already whitelists 4 sectors |
| Rolling windows (MA50, 252d high, 20d median) | Manual loops | `df.rolling(n).{max,mean,median}` | See `models/indicators.py` |
| Percentile ranking | Sort + index math | `series.rank(pct=True)` | One-liner, handles ties |
| Grid iteration for validation dates | nested loops | `np.random.default_rng(seed).choice(dates, 5, replace=False)` | Reproducible with seed |
| Baseline `diem_canslim` loading | ad-hoc SQL | One helper `load_diem_canslim(dates)` in `strategies/canslim/baseline.py` | Keeps validation logic isolated |

**Key insight:** Phase 28 already built the DB + adjustment layer specifically so Phase 29 doesn't touch raw SQL or adjustment math. The scorer should be ~90% pandas.

## Runtime State Inventory

Not applicable — Phase 29 is a greenfield package addition. No renames, no migrations, no existing service state to update. New code only.

## Common Pitfalls

### Pitfall 1: Look-ahead via EPS publish_date
**What goes wrong:** Using `yearreport + lengthreport` directly as "when this EPS was known" — actual publishing happens 45–90 days later.
**Why it happens:** It's the obvious thing to do and `is_quarter_*` often lacks a real `publish_date` column.
**How to avoid:** Pipe every EPS read through `resolve_eps_publish_date`, then filter `publish_date <= as_of_date`. Unit test: construct a fake EPS row with `publish_date = 2024-04-15`, query with `as_of_date = 2024-04-14`, assert the row is excluded.
**Warning signs:** Composite score spikes exactly on earnings-announcement days; backtests show unrealistically high returns during reporting seasons.

### Pitfall 2: Survivorship in `current-vn100` mode
**What goes wrong:** Using today's VN100 list for 2014 backtests — ROS, FLC-era losers are excluded, inflating backtest returns.
**Why it happens:** Phase 28 confirmed point-in-time VN100 membership is unavailable.
**How to avoid:** Document explicitly in validation report (D-14). For Phase 29 scorer itself this is acceptable per D-01/D-04. Flag delisted tickers (from Phase 28's delisted_candidates.csv) visibly.
**Warning signs:** Validation overlap vs `diem_canslim` is implausibly high on old dates.

### Pitfall 3: Foreign-flow data starts 2022-04-07
**What goes wrong:** I-rule evaluates to True/False randomly (or NaN) for dates before 2022-04-07 because `stock_foreign_eod` has no rows there.
**Why it happens:** Phase 28 audit discovered this — `stock_foreign_eod` earliest row is 2022-04-07.
**How to avoid:** In `rules/flow.py`, explicitly check the 20-day window has data. If empty → mark `i_pass = False` (conservative) OR skip I-rule for that date (document decision). Either way, the validation report must state the pre-2022 handling policy.
**Warning signs:** 2021 scores have suspicious I-rule patterns.

### Pitfall 4: Percentile ranking with <252 days history
**What goes wrong:** Newly-listed tickers (e.g., DSE first listed 2022) produce NaN ROC(252), corrupting the percentile rank for every other ticker on that date.
**Why it happens:** `series.rank(pct=True)` treats NaN separately but downstream `>= 80` comparison propagates NaN.
**How to avoid:** D-05 says drop any ticker with <252 days of history for that date. Implement in `universe.py` — the active universe for each date already excludes them.
**Warning signs:** Days with fewer than ~70 tickers passing RS; NaN `l_pass` values.

### Pitfall 5: Banks and securities firms miss `is_quarter_nonbank`
**What goes wrong:** Banks (ACB, BID, CTG, VCB, …) and securities (SSI, VND, …) have zero rows in `is_quarter_nonbank` — they live in `is_quarter_bank` and `is_quarter_stock` respectively.
**Why it happens:** This exact bug hit Phase 28 (see `cbf3e0c`).
**How to avoid:** Route per ticker before querying. Banks → `load_is_quarter(..., sector='bank')`. CTCK/Insurance → excluded per D-07. Other → `nonbank`.
**Warning signs:** All bank tickers fail C/A with "no EPS data" — known Phase 28 bug, don't repeat.

### Pitfall 6: PPOP column name for banks
**What goes wrong:** For banks, C/A use **PPOP growth** (Pre-Provision Operating Profit) not EPS. The exact column name in `is_quarter_bank` must be confirmed — it's probably `ppop`, `loinhuansauchiphi`, or similar Vietnamese-named column.
**How to avoid:** First task in the fundamental-rules plan = inspect `is_quarter_bank` columns live, pick the correct PPOP column, document in `docs/rules_canslim.md`. Do NOT guess.
**Warning signs:** All bank C/A results are False because the wrong column is being read.

### Pitfall 7: Composite score weighting is undefined
**What goes wrong:** D-09 requires a `score` column but the weighting is Claude's discretion (not in CONTEXT.md). Picking a weighting after seeing validation results = overfitting.
**How to avoid:** Commit the composite weighting formula to `docs/rules_canslim.md` BEFORE running the validation spot-check. Reasonable default: equal-weighted sum of 9 booleans × 10 + RS_rating/10 (so 0–100 range). Document the choice as a design decision, not an empirical one.

## Code Examples

### Computing the IBD RS rating (L rule)
```python
# strategies/canslim/rules/rs.py
import pandas as pd

def compute_rs_rating(prices: pd.DataFrame, as_of_date: pd.Timestamp, active: list[str]) -> pd.Series:
    """
    prices: long-format DataFrame with columns [tradingdate, stockcode, adj_close]
    Returns: Series indexed by ticker, values 0-100 percentile among `active` tickers.
    """
    wide = prices.pivot(index="tradingdate", columns="stockcode", values="adj_close")
    wide = wide.loc[:as_of_date]
    if len(wide) < 253:
        raise ValueError(f"Need >=253 rows to compute RS as of {as_of_date}, got {len(wide)}")
    last = wide.iloc[-1]
    roc63  = last / wide.iloc[-64]  - 1
    roc126 = last / wide.iloc[-127] - 1
    roc189 = last / wide.iloc[-190] - 1
    roc252 = last / wide.iloc[-253] - 1
    raw = 0.4*roc63 + 0.2*roc126 + 0.2*roc189 + 0.2*roc252
    raw = raw.reindex(active).dropna()
    return raw.rank(pct=True) * 100
```

### Point-in-time quarterly EPS YoY (C rule for non-banks)
```python
# strategies/canslim/rules/fundamental.py
import pandas as pd
from connectors.mysql import load_is_quarter
from connectors.eps import resolve_eps_publish_date

EPS_COL = "epsbasicvnd"  # TODO(Wave 0): confirm live against is_quarter_nonbank schema

def c_rule(tickers: list[str], as_of_date: pd.Timestamp, threshold: float = 0.20) -> pd.Series:
    raw = load_is_quarter(tickers, sector="nonbank")
    pit = resolve_eps_publish_date(raw)
    pit = pit[pit["publish_date"] <= as_of_date]
    pit = pit.sort_values(["stockcode", "yearreport", "lengthreport"])
    latest = pit.groupby("stockcode").tail(1).set_index("stockcode")
    # Join with row from same quarter 1 year earlier
    prev_year = pit.copy()
    prev_year["match_year"] = prev_year["yearreport"] + 1
    merged = latest.merge(
        prev_year,
        left_on=["stockcode", "yearreport", "lengthreport"],
        right_on=["stockcode", "match_year", "lengthreport"],
        suffixes=("", "_prev"),
    ).set_index("stockcode")
    yoy = (merged[EPS_COL] - merged[f"{EPS_COL}_prev"]) / merged[f"{EPS_COL}_prev"].abs()
    return yoy >= threshold
```

### Liquidity filter (20d median turnover)
```python
# strategies/canslim/rules/liquidity.py
def liq_pass(prices: pd.DataFrame, min_vnd: float = 5e9) -> pd.Series:
    # prices: long-format with adj_close, totalvol, stockcode, tradingdate
    prices = prices.sort_values(["stockcode", "tradingdate"]).copy()
    prices["turnover"] = prices["adj_close"] * prices["totalvol"]
    prices["med20"] = prices.groupby("stockcode")["turnover"].transform(
        lambda s: s.rolling(20, min_periods=20).median()
    )
    return prices.set_index(["tradingdate","stockcode"])["med20"] >= min_vnd
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded VN100 ticker list in code | Pull from `stock_list.nhomtop IN ('VN30','VN100')` | Phase 28 | Single source of truth, no drift |
| Computing EPS as-of-filing-date | `publish_date + 45d/90d` imputation via `resolve_eps_publish_date` | Phase 28 | No look-ahead |
| `is_quarter_nonbank` for everything | Per-sector routing across 4 tables | Phase 28 bug fix `cbf3e0c` | Banks + CTCK now covered |
| CSV-based OHLCV loaders | Postgres `stock_eod` + `adjust_ohlc` | Phase 28 | Adjusted series for all tickers |

**Deprecated/outdated:**
- `models/data_loader.py` CSV loader — still used by MDM/VSA strategies, but Phase 29 must use `connectors/postgres.py` directly. Do not wire CANSLIM through the old CSV loader.

## Open Questions

1. **Exact column names in `is_quarter_*` and `stock_list`**
   - What we know: `is_quarter_bank/nonbank/insurance/stock` all exist and work via `load_is_quarter`. `stock_list` has `stockcode` and `nhomtop`.
   - What's unclear: Exact EPS column name (`epsbasicvnd`? `eps_basic`? `eps`?), exact PPOP column name in `is_quarter_bank`, and the exact sector column in `stock_list` (`sector`? `industry`? `nhomnganh`? `icb`?).
   - Recommendation: **First task of Wave 0 = a 10-line live SQL introspection script** (`SELECT column_name FROM information_schema.columns WHERE table_name = ...`) that prints the real schema. Lock the column names in `strategies/canslim/config.py` as module constants. Do NOT guess in the planning phase.

2. **Composite score weighting formula**
   - What we know: D-09 requires a `score` column, 0–100 range, and D-10 says Phase 30 can rank by it.
   - What's unclear: Weighting scheme (equal-weight? RS-heavy? EPS-heavy?).
   - Recommendation: Equal-weight 9 booleans × 10 points + `rs_rating × 0.1` bonus (capped at 100). Commit to `docs/rules_canslim.md` before running validation. Sweep can come in Phase 32.

3. **Pre-2022 I-rule handling**
   - What we know: `stock_foreign_eod` starts 2022-04-07.
   - What's unclear: For backtest dates 2014–2022-03, is `i_pass = False` (conservative, rejects everyone), `i_pass = True` (optimistic, ignores rule), or `i_pass = NaN` (scorer output has missing values)?
   - Recommendation: **`i_pass = True` before 2022-04-07**, document as "I-rule unavailable; not enforced". This matches the spirit of "rule passes if we can't prove it fails". Flag clearly in validation report. Alternative: `i_pass = NaN` and let Phase 30 decide.

4. **A-rule: annual rollup source**
   - What we know: We have quarterly `is_quarter_*`. Phase 28 did not confirm whether `is_year_*` tables exist.
   - What's unclear: Compute annual EPS from TTM-sum of 4 quarters, or query a separate `is_year_*` table?
   - Recommendation: **TTM-sum of 4 quarters** — simpler, same publish_date guard mechanism, one data source. Verify in Wave 0 that at least 12 quarters (3 years) of history exist for the majority of VN100 tickers (Phase 28 says 16/100 are sparse — they'll fail A-rule naturally, per D's deferred list).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All code | ✓ | 3.10+ (pyproject) | — |
| pandas ≥2.0 | Data manipulation | ✓ | Installed in Phase 28 | — |
| SQLAlchemy ≥2.0 | DB connectors | ✓ | Installed in Phase 28 | — |
| Postgres live (TA) | `stock_eod`, `stock_foreign_eod`, `stock_list` | ✓ | Phase 28 integration tests pass | — |
| MySQL live (Fundamentals) | `is_quarter_*`, `rank_top_stocks` | ✓ | Phase 28 integration tests pass | Integration tests auto-skip when IP allow-list blocks dev host — same pattern applies here |
| pytest + `integration` marker | Test suite | ✓ | Phase 28 pyproject additions | — |
| `.env` credentials | DB access | ✓ | Confirmed working Phase 28 | — |
| `stock_foreign_eod` coverage ≥ 2014 | I-rule pre-2022 | ✗ | Data starts 2022-04-07 | **Handle per Open Question 3 — not a blocker** |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- Pre-2022 foreign-flow data — fallback: `i_pass = True` (rule not enforced) with explicit documentation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥7 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (added in Phase 28 Wave 0, already has `markers = ["integration: requires live DB"]`) |
| Quick run command | `uv run pytest tests/ -m "not integration" -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UNIV-01 | Loader returns 100 tickers for current-VN100 | integration | `pytest tests/test_canslim_universe.py::test_current_vn100_live -m integration -q` | ❌ Wave 0 |
| UNIV-01 | Loader handles missing `stock_list` (fail loud) | unit | `pytest tests/test_canslim_universe.py::test_missing_table_raises -q` | ❌ Wave 0 |
| UNIV-02 | Semi-annual rebalance snap for `liquidity-reconstructed` | unit | `pytest tests/test_canslim_universe.py::test_rebalance_snap -q` | ❌ Wave 0 |
| UNIV-03 | Three modes selectable via enum | unit | `pytest tests/test_canslim_config.py::test_universe_modes -q` | ❌ Wave 0 |
| UNIV, D-05 | Tickers with <252d history dropped | unit | `pytest tests/test_canslim_universe.py::test_min_history_drop -q` | ❌ Wave 0 |
| CANS-01 | C rule YoY threshold | unit | `pytest tests/test_canslim_rules_fundamental.py::test_c_rule_threshold -q` | ❌ Wave 0 |
| CANS-01, D-11 | **C rule publish_date look-ahead guard** | unit | `pytest tests/test_canslim_rules_fundamental.py::test_publish_date_guard -q` | ❌ Wave 0 |
| CANS-02 | C+ acceleration vs prior 2 quarters | unit | `pytest tests/test_canslim_rules_fundamental.py::test_c_plus_acceleration -q` | ❌ Wave 0 |
| CANS-03 | A 3yr CAGR | unit | `pytest tests/test_canslim_rules_fundamental.py::test_a_rule_cagr -q` | ❌ Wave 0 |
| CANS-04 | A+ 3 positive years | unit | `pytest tests/test_canslim_rules_fundamental.py::test_a_plus_positive_years -q` | ❌ Wave 0 |
| CANS-05 | N within 15% 252d high | unit | `pytest tests/test_canslim_rules_technical.py::test_n_rule -q` | ❌ Wave 0 |
| CANS-06 | S 1.5× avgvol50 | unit | `pytest tests/test_canslim_rules_technical.py::test_s_rule -q` | ❌ Wave 0 |
| CANS-07 | L RS formula + percentile | unit | `pytest tests/test_canslim_rules_rs.py::test_rs_formula_and_percentile -q` | ❌ Wave 0 |
| CANS-08 | I 20-day foreign net buy | unit | `pytest tests/test_canslim_rules_flow.py::test_i_rule_window -q` | ❌ Wave 0 |
| CANS-08 | I pre-2022 fallback | unit | `pytest tests/test_canslim_rules_flow.py::test_i_rule_pre_2022 -q` | ❌ Wave 0 |
| CANS-09 | Liquidity 20d median ≥ 5B | unit | `pytest tests/test_canslim_rules_liquidity.py::test_liq_threshold -q` | ❌ Wave 0 |
| CANS-10, D-06/07/08 | Sector routing + fail-loud on unknown | unit | `pytest tests/test_canslim_rules_fundamental.py::test_sector_routing -q` | ❌ Wave 0 |
| CANS-10 | Banks use PPOP not EPS | unit | `pytest tests/test_canslim_rules_fundamental.py::test_bank_ppop -q` | ❌ Wave 0 |
| CANS-11, D-09 | Scorer returns tidy DataFrame with all 14 columns | unit | `pytest tests/test_canslim_scorer.py::test_output_schema -q` | ❌ Wave 0 |
| CANS-11 | `CanslimConfig` defaults + kwargs override | unit | `pytest tests/test_canslim_config.py::test_defaults_and_overrides -q` | ❌ Wave 0 |
| CANS-12, D-14 | Baseline spot-check on 5 random dates, ≥4/10 on ≥3 dates | script | `python scripts/validate_canslim.py --seed 42` then check exit code + `docs/audits/phase29-canslim-validation.md` | ❌ Wave 0 |
| CANS-12 | `load_diem_canslim_baseline` returns expected shape | integration | `pytest tests/test_canslim_baseline.py -m integration -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -m "not integration" -q` (<10s)
- **Per wave merge:** `uv run pytest tests/ -q` (≤30s including live DB)
- **Phase gate:** Full suite green + `docs/audits/phase29-canslim-validation.md` committed + `≥4/10 on ≥3 of 5 dates` acceptance confirmed

### Wave 0 Gaps
- [ ] `strategies/__init__.py` — empty package marker (new top-level package)
- [ ] `strategies/canslim/__init__.py` — re-export `CanslimScorer`, `CanslimConfig`, `UniverseMode`
- [ ] `strategies/canslim/config.py` — stub `CanslimConfig` dataclass + `UniverseMode` enum with defaults from D-12
- [ ] `strategies/canslim/universe.py` — stub with `load_universe(as_of_date, mode)` signature
- [ ] `strategies/canslim/sectors.py` — stub with `classify(...)` signature
- [ ] `strategies/canslim/rules/__init__.py` — empty package marker
- [ ] `strategies/canslim/rules/fundamental.py` — stubs for `c_rule`, `c_plus_rule`, `a_rule`, `a_plus_rule`
- [ ] `strategies/canslim/rules/technical.py` — stubs for `n_rule`, `s_rule`
- [ ] `strategies/canslim/rules/rs.py` — stub for `compute_rs_rating`
- [ ] `strategies/canslim/rules/flow.py` — stub for `i_rule` with pre-2022 fallback
- [ ] `strategies/canslim/rules/liquidity.py` — stub for `liq_rule`
- [ ] `strategies/canslim/scorer.py` — stub `CanslimScorer.score(dates)`
- [ ] `strategies/canslim/baseline.py` — stub `load_diem_canslim_baseline(dates)`
- [ ] `scripts/validate_canslim.py` — stub with `--seed` arg
- [ ] `tests/test_canslim_config.py` through `tests/test_canslim_baseline.py` — 9 test file stubs
- [ ] `tests/fixtures/canslim/` — fake OHLCV + fake EPS DataFrames for unit tests
- [ ] `docs/audits/phase29/` — directory created
- [ ] `docs/rules_canslim.md` — stub with section headers (must be filled in same commit as scorer per Code-Docs Sync Rule)
- [ ] **Live schema introspection script** — 10-line helper that prints columns of `is_quarter_nonbank`, `is_quarter_bank`, `stock_list` so the planner can lock EPS/PPOP/sector column names

## Project Constraints (from CLAUDE.md)

- **Code-Docs Sync Rule:** Any change to `strategies/canslim/` logic MUST update `docs/rules_canslim.md` in the same commit. Plan tasks must bundle code + docs edits.
- **GSD Workflow Enforcement:** All file edits happen inside GSD command flow — no direct edits outside it.
- **Naming:** `snake_case` for files/functions/variables, `PascalCase` for classes (`CanslimScorer`, `CanslimConfig`), dataclass post-init validation for configs (mirror `MDMConfig`).
- **State[i-1] discipline:** Called out in MEMORY for the 707% bug. Applies to NAV in Phase 31+, but the Phase 29 scorer must not use same-day close to compute same-day signals — use `<= as_of_date` strictly.
- **Python ≥3.10**, `uv` package manager, no new deps unless strictly needed.
- **Vietnamese communication preference** confirmed in CONTEXT.md specifics.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/28-data-audit-connectors/28-05-SUMMARY.md` — VN100 resolution, 16 sparse tickers, `stock_foreign_eod` starts 2022-04-07, 4-sector EPS union
- `connectors/postgres.py` (read live) — `load_stock_eod`, `query`, env handling
- `connectors/mysql.py` (read live) — `load_is_quarter(sector=...)`, sector whitelist, expanding bindparams
- `connectors/adjust.py` (read live) — `adjust_ohlc(df)` interface
- `connectors/eps.py` (read live) — `resolve_eps_publish_date(df)` interface and imputation rules
- `.planning/phases/29-vn100-universe-canslim-scorer/29-CONTEXT.md` — all locked decisions
- `.planning/REQUIREMENTS.md` — UNIV-01..03, CANS-01..12 definitions
- `.planning/ROADMAP.md` Phase 29 section — SC1–SC7 acceptance criteria
- `.planning/STATE.md` — project data source map (Postgres TA / MySQL fundamentals)
- `.planning/phases/28-data-audit-connectors/28-VALIDATION.md` — pytest infrastructure pattern

### Secondary (MEDIUM confidence)
- Phase 28 `docs/audits/phase28-data-audit.md` (excerpts grepped) — confirms VN100 count, EPS gaps, foreign_eod date range

### Tertiary (LOW confidence) — flag for Wave 0 verification
- Exact column name for EPS in `is_quarter_nonbank` (guessed `epsbasicvnd`)
- Exact column name for PPOP in `is_quarter_bank`
- Exact column name for sector in `stock_list`
- Whether `is_year_*` tables exist (probably not needed — TTM-sum works)

**All three must be verified by live `information_schema` query in the first Wave 0 task.**

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no external dependencies
- Architecture: HIGH — mirrors existing `vn30_vsa/` pattern; Phase 28 connectors are the DB layer
- Pitfalls: HIGH — survivorship, look-ahead, sector routing, pre-2022 foreign flow all already hit in Phase 28
- Column names: **LOW** — explicitly flagged; first Wave 0 task must introspect schema
- Composite score weighting: MEDIUM — discretionary, concrete recommendation provided

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 days; Phase 28 deliverables are stable)

## RESEARCH COMPLETE

**Phase:** 29 - VN100 Universe + CANSLIM Scorer
**Confidence:** HIGH

### Key Findings

- Phase 28 already shipped every DB/adjustment primitive Phase 29 needs — no new dependencies, no SQL outside `connectors/`
- `stock_list.nhomtop IN ('VN30','VN100')` is the confirmed VN100 source (100 tickers, live-verified)
- Three schema column names (EPS in `is_quarter_nonbank`, PPOP in `is_quarter_bank`, sector in `stock_list`) are NOT yet verified and must be the **first Wave 0 task** — do not let the planner hardcode guesses
- `stock_foreign_eod` data only starts 2022-04-07 → I-rule needs an explicit pre-2022 policy (recommendation: `i_pass = True`, document as "not enforced")
- Package layout mirrors `vn30_vsa/`: `strategies/canslim/{config,universe,sectors,scorer,baseline}.py` + `rules/{fundamental,technical,rs,flow,liquidity}.py`
- Composite score weighting is Claude's discretion but MUST be committed to `docs/rules_canslim.md` before running validation to avoid overfitting

### File Created
`.planning/phases/29-vn100-universe-canslim-scorer/29-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All deps already installed from Phase 28 |
| Architecture | HIGH | Mirrors `vn30_vsa/`; connectors pattern tested |
| Pitfalls | HIGH | Phase 28 already hit sector-routing + publish-date issues |
| DB column names | LOW | Must be verified in Wave 0 via `information_schema` |
| Composite weighting | MEDIUM | Discretionary; concrete default recommended |

### Open Questions
1. Exact EPS / PPOP / sector column names — schedule as Wave 0 live-schema introspection
2. Composite score weighting formula — recommend equal-weight booleans + RS bonus, lock before validation
3. Pre-2022 I-rule handling — recommend `i_pass = True`, document clearly
4. A-rule annual rollup: TTM-sum from quarterly (recommended) vs `is_year_*` tables (verify existence)

### Ready for Planning
Research complete. Planner can proceed to PLAN.md creation. Wave 0 must include: (a) new package skeleton, (b) test stubs, (c) **live schema introspection helper** to lock column names, (d) `docs/rules_canslim.md` stub.
