# Phase 28: Data Audit & Connectors - Research

**Researched:** 2026-04-08
**Domain:** Python DB connectivity (SQLAlchemy + pandas) + Vietnamese equities data audit
**Confidence:** HIGH on stack/patterns, MEDIUM on VN-specific schema details (to be verified live in Wave 0)

## Summary

Phase 28 introduces the first database layer in the repo. Locked decisions constrain the design tightly: SQLAlchemy engine + `pandas.read_sql`, one module per DB under `connectors/`, creds from `.env`, `adjusted = raw * totaladjustrate`, EPS publish_date imputed as `period_end + 45d / +90d`, and a Markdown+CSV audit deliverable. Research therefore focuses on idiomatic driver/URL choices, mirroring the existing `core/data_loader.py` column-normalization pattern, audit query shapes, and how to test DB code without a live DB in CI.

**Primary recommendation:** Use `sqlalchemy>=2.0` + `psycopg2-binary` (Postgres) + `pymysql` (MySQL). Cache a module-level engine per DB via `functools.lru_cache`, enable `pool_pre_ping=True`, load creds once with `python-dotenv`. Mirror the `COLUMN_MAPS` pattern from `core/data_loader.py` so engines remain source-agnostic. Unit tests use fixture DataFrames and monkeypatched `query()`; a single integration test guarded by `pytest.mark.skipif(no creds)` runs `SELECT ... LIMIT 5` against real DBs.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** SQLAlchemy engine + `pandas.read_sql` for both Postgres and MySQL.
- **D-02:** One module per DB: `connectors/postgres.py` and `connectors/mysql.py`. Each exposes `get_engine()`, `query(sql, params=None) -> pd.DataFrame`, plus domain helpers (`load_stock_eod`, `load_ratios`, ...).
- **D-03:** Credentials ONLY from `.env` via `python-dotenv`. Never hardcoded.
- **D-04:** Integration test `tests/test_connectors.py` runs `SELECT ... LIMIT 5` against `stock_eod` and `ratios_stock` and must pass before phase verify.
- **D-05:** `stock_eod` is UNADJUSTED. `adjusted = raw_col * totaladjustrate` applied to `openprice`, `closeprice`, `highestprice`, `lowestprice`. Volume left as-is unless audit shows otherwise.
- **D-06:** Helper `adjust_ohlc(df)` in `connectors/` (or `data/adjust.py`). All downstream backtests use adjusted prices.
- **D-07:** Spot-check adjustment on 2–3 tickers with known large splits/dividends.
- **D-08:** Inspect `ratios_stock` schema; prefer a real `publish_date` / `updated_at` / `announce_date` column if one exists, otherwise impute.
- **D-09:** Imputation rule: `publish_date = period_end + 45d` for Q1–Q3, `+90d` for Q4/annual. Documented as the backtest assumption.
- **D-10:** Helper `resolve_eps_publish_date(df)` adds `publish_date`. Downstream CANSLIM must filter by `publish_date <= as_of_date`.
- **D-11:** Deliverable = `docs/audits/phase28-data-audit.md` + `docs/audits/phase28/*.csv`. No notebook.
- **D-12:** Audit must cover: distinct stockcode count, delisted candidates (`max(tradingdate) < 2024-01-01`), spot-check known delistings (FLC, ROS, HVN, ...), confirm `totaladjustrate` usage, EPS coverage per current VN100 ticker back to 2014, `stock_foreign_eod` VN100 daily coverage 2014–2026.
- **D-13:** Delisted tickers are FLAGGED only in Phase 28. Universe inclusion deferred to Phase 29.

### Claude's Discretion
- SQLAlchemy URL format, pool size, connection timeout.
- `connectors/__init__.py` re-export layout.
- CSV schemas for audit companion files.
- Choice of 2–3 tickers for the adjustment spot-check.

### Deferred Ideas (OUT OF SCOPE)
- Active survivorship-bias handling (include delisted in backtest universe) — Phase 29.
- Scraping HOSE disclosures for real EPS publish_date.
- Async connectors / pool tuning for live use.
- Adjustment of `totalvol` unless audit proves it necessary.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Postgres connector + integration test | SQLAlchemy+psycopg2 pattern in "Standard Stack" + "Code Examples" below |
| DATA-02 | MySQL connector + integration test | SQLAlchemy+pymysql pattern, same shape as Postgres |
| DATA-03 | Audit `stock_eod` for delisted ticker coverage | Audit query patterns section (max-date-per-ticker SQL) |
| DATA-04 | Verify `stock_eod` price adjustment; build helper if unadjusted | `adjust_ohlc` formula locked; spot-check protocol in "Code Examples" |
| DATA-05 | Resolve EPS publish_date (real column or impute) | Schema inspection + imputation rule in helper |
| DATA-06 | VN100 fundamental coverage back to 2014 | EPS coverage pivot pattern in audit queries |
| DATA-07 | `stock_foreign_eod` VN100 daily coverage 2014-2026 | Coverage gap query pattern |

## Project Constraints (from CLAUDE.md)

- **Naming:** snake_case modules/functions, PascalCase classes, typed helpers. `connectors/postgres.py`, `connectors/mysql.py` fit.
- **Module layout:** sibling of `models/`, `strategies/`, `core/`, `vn30_vsa/`.
- **Column normalization:** existing `core/data_loader.py` uses per-source `COLUMN_MAPS` to emit canonical `[date, open, high, low, close, volume]`. Connector helpers should emit the SAME canonical schema (plus `symbol` for multi-ticker loads) so downstream engines are source-agnostic.
- **Error handling philosophy:** minimal try/except; validate inputs via assertions / dataclass post_init; rely on pandas `.dropna()` / `.get()` for missing data.
- **Code-docs sync rule:** since this phase creates the first DB layer, `docs/` must get a data-dictionary entry (satisfies DOC-02). Audit deliverable itself lives in `docs/audits/`.
- **GSD workflow:** file edits go through the GSD phase execution pipeline.
- **state[i-1] discipline:** relevant downstream; for this phase, `publish_date <= as_of_date` is the equivalent look-ahead guard.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0,<3.0 | DB engine + connection pool | De-facto Python ORM/core; pandas.read_sql natively accepts SQLAlchemy Engine/Connection (raw DBAPI connections are deprecated in pandas 2.x for non-SQLite) |
| psycopg2-binary | >=2.9.9 | Postgres driver | Mature, synchronous, well-known. `psycopg[binary]` (psycopg3) is newer but SQLAlchemy 2.0 still defaults to psycopg2 unless URL says otherwise. For an offline audit tool, psycopg2-binary is the lower-risk choice. |
| PyMySQL | >=1.1.0 | MySQL driver | Pure-Python, zero build dependency on Windows (user is on Win11). `mysql-connector-python` is Oracle-maintained but has licensing quirks and a larger footprint. `mysqlclient` is faster but requires MySQL C client headers at install time — painful on Windows. PyMySQL "just works". |
| python-dotenv | >=1.2.1 (already installed) | Load `.env` creds | Already a project dep. |
| pandas | >=2.0.0 (already installed) | `read_sql` result handling | Already a project dep. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0.2 (already dev dep) | Integration test runner | Use `pytest.mark.skipif` for live-DB-required tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psycopg2-binary | psycopg[binary] (v3) | v3 has native async + better COPY support. Not needed for offline audit; v2 is the more common pattern in training/SO answers. |
| PyMySQL | mysqlclient | ~3–5x faster, but needs MySQL C headers at install time; painful on Windows. |
| PyMySQL | mysql-connector-python | Official Oracle driver; slower than PyMySQL; GPL+FOSS-exception license is awkward. |
| SQLAlchemy engine | raw DBAPI cursor | pandas 2.x deprecates raw-connection path for non-SQLite; SQLAlchemy also gives pool_pre_ping, URL parsing, and dialect abstraction for free. |

**Installation:**
```bash
uv add sqlalchemy psycopg2-binary pymysql
# (or the equivalent edit to pyproject.toml [project].dependencies)
```

**Version verification:** Plan must run `pip index versions <pkg>` or equivalent during Wave 0 and record the exact resolved versions in the commit. Do not trust training-data version numbers.

### URL formats (locked patterns)

- Postgres: `postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}`
- MySQL: `mysql+pymysql://{user}:{pw}@{host}:{port}/{db}?charset=utf8mb4`

Use `sqlalchemy.engine.URL.create(...)` rather than f-string interpolation — it handles password URL-encoding (passwords containing `@`, `:`, `/` break naive f-strings).

## Architecture Patterns

### Recommended Project Structure
```
connectors/
├── __init__.py          # re-export get_pg_engine, get_mysql_engine, load_stock_eod, load_ratios, adjust_ohlc, resolve_eps_publish_date
├── postgres.py          # get_engine(), query(), load_stock_eod(), load_index_eod(), load_stock_foreign_eod()
├── mysql.py             # get_engine(), query(), load_ratios(), load_is_quarter(), load_rank_top_stocks()
├── adjust.py            # adjust_ohlc(df), resolve_eps_publish_date(df)
└── schema.py            # canonical column maps + expected-column assertions
docs/
└── audits/
    ├── phase28-data-audit.md
    └── phase28/
        ├── delisted_candidates.csv
        ├── vn100_eps_coverage.csv
        ├── vn100_foreign_coverage.csv
        └── adjustment_spotcheck.csv
scripts/
└── run_phase28_audit.py  # generates the docs/audits/phase28/* outputs
tests/
├── test_connectors_unit.py       # no live DB; monkeypatch query(); exercises adjust_ohlc + resolve_eps_publish_date on fixtures
└── test_connectors_integration.py  # skip if no creds; SELECT LIMIT 5 against stock_eod + ratios_stock
```

### Pattern 1: Cached Engine + Thin Query Helper
**What:** Module-level cached engine so every call reuses the same pool.
**When to use:** Always, for offline batch workloads.
**Example:**
```python
# connectors/postgres.py
import os
from functools import lru_cache
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

load_dotenv()  # idempotent; safe at import

@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DATABASE"],
    )
    return create_engine(
        url,
        pool_pre_ping=True,   # transparently reconnect on stale connections
        pool_recycle=1800,    # recycle conns every 30 min
        future=True,
    )

def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})
```

`lru_cache` gives us a cheap "module singleton" pattern that is trivially resettable in tests via `get_engine.cache_clear()`.

### Pattern 2: Domain Helpers Emit Canonical Columns
**What:** Wrap `query()` in typed helpers that rename source columns to the project canonical schema — mirror `core/data_loader.py` `COLUMN_MAPS`.
**Why:** Downstream engines (Phase 29+) should not know whether data came from CSV or Postgres.
**Example:**
```python
# connectors/postgres.py (cont)
STOCK_EOD_COL_MAP = {
    "stockcode": "symbol",
    "tradingdate": "date",
    "openprice": "open_raw",
    "highestprice": "high_raw",
    "lowestprice": "low_raw",
    "closeprice": "close_raw",
    "totalvol": "volume",
    "totaladjustrate": "adj",
}

def load_stock_eod(
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    adjusted: bool = True,
) -> pd.DataFrame:
    sql = """
        SELECT stockcode, tradingdate, openprice, highestprice,
               lowestprice, closeprice, totalvol, totaladjustrate
        FROM stock_eod
        WHERE (:start IS NULL OR tradingdate >= :start)
          AND (:end   IS NULL OR tradingdate <= :end)
          AND (:tickers IS NULL OR stockcode = ANY(:tickers))
        ORDER BY stockcode, tradingdate
    """
    df = query(sql, {"start": start, "end": end, "tickers": tickers})
    df = df.rename(columns=STOCK_EOD_COL_MAP)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    if adjusted:
        df = adjust_ohlc(df)
    return df
```

### Pattern 3: Pure-Function Adjustment Helper
**What:** `adjust_ohlc(df)` is a pure pandas function over a DataFrame that has `open_raw/high_raw/low_raw/close_raw/adj` columns. No DB access.
**Why:** Trivial to unit-test on a fixture DataFrame — no live DB needed.
```python
# connectors/adjust.py
OHLC_RAW = ["open_raw", "high_raw", "low_raw", "close_raw"]

def adjust_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "adj" not in out.columns:
        raise KeyError("adjust_ohlc requires 'adj' column (from totaladjustrate)")
    # NULL adjust rate -> treat as 1.0 and FLAG (do not silently drop)
    null_mask = out["adj"].isna()
    if null_mask.any():
        out.loc[null_mask, "adj"] = 1.0
    for raw, clean in zip(OHLC_RAW, ["open", "high", "low", "close"]):
        out[clean] = out[raw] * out["adj"]
    return out
```

### Pattern 4: publish_date resolver
```python
# connectors/adjust.py (cont)
def resolve_eps_publish_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add a publish_date column.
    - If a real column (publish_date / announce_date / updated_at) is present, use it.
    - Otherwise impute: Q1-Q3 -> period_end + 45d, Q4/annual -> + 90d.
    """
    out = df.copy()
    for candidate in ("publish_date", "announce_date", "updated_at"):
        if candidate in out.columns and out[candidate].notna().any():
            out["publish_date"] = pd.to_datetime(out[candidate])
            return out
    # Impute path — requires 'period_end' and 'quarter' (1..4) columns
    out["period_end"] = pd.to_datetime(out["period_end"])
    delta = out["quarter"].map(lambda q: 45 if q in (1, 2, 3) else 90)
    out["publish_date"] = out["period_end"] + pd.to_timedelta(delta, unit="D")
    return out
```

### Anti-Patterns to Avoid
- **Opening a new Engine per call:** defeats pooling; can exhaust server connection slots.
- **f-string SQL interpolation of user/ticker values:** SQL injection vector; use bind params via `text(":name")`.
- **Hardcoding creds in module constants:** blocked by D-03.
- **Writing a notebook for the audit:** blocked by D-11 (bad git diffs).
- **Dropping rows with NULL `totaladjustrate` silently:** mask and flag instead.
- **Using `period_end` as EPS publish_date directly:** look-ahead bias — this is the exact bug D-10 protects against.
- **Forgetting `pool_pre_ping`:** connections get killed by the DB's idle timeout; next query throws `OperationalError` mid-audit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection pooling / reconnect | Manual connection caching with try/except reconnect | SQLAlchemy engine + `pool_pre_ping=True` | Handles stale connections, timeouts, and thread-safety for free |
| Password URL-escaping | f-string URL | `sqlalchemy.engine.URL.create(...)` | Auto-handles special chars (`@`, `:`, `/`) in passwords |
| SQL→DataFrame conversion | Manual cursor loop + dict-building | `pandas.read_sql(text(sql), conn, params=...)` | Handles type inference, chunking, and is the canonical path |
| `.env` parsing | Custom reader | `python-dotenv` (already a dep) | Already used elsewhere |
| Date diff / quarter offset math | Manual month arithmetic | `pd.to_timedelta` + pandas offsets | Avoids DST/leap issues; vectorized |

**Key insight:** The whole connector layer should be ~150 lines of glue. Everything meaningful (engine, pooling, query, type coercion) already exists in SQLAlchemy + pandas.

## Runtime State Inventory

Not a rename/refactor phase — section omitted.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Everything | ✓ (per pyproject.toml) | >=3.10 | — |
| `sqlalchemy` | Connectors | ✗ (not in pyproject) | — | Install via `uv add` |
| `psycopg2-binary` | Postgres connector | ✗ | — | Install via `uv add` |
| `pymysql` | MySQL connector | ✗ | — | Install via `uv add` |
| Postgres server reachable | Integration test, audit script | Assumed ✓ (STATE.md says 5.9M rows verified 2026-04-08) | — | Integration test skips if creds missing |
| MySQL server reachable | Integration test, audit script | Assumed ✓ (STATE.md lists ratios_stock) | — | Same |
| `.env` with POSTGRES_* / MYSQL_* keys | All connector code | ✓ (confirmed keys present, values redacted) | — | — |

**Missing dependencies with no fallback:** sqlalchemy, psycopg2-binary, pymysql — must be installed in Wave 0 / pre-task.

**Missing dependencies with fallback:** Live DB reachability for integration test — skip marker so CI without creds still passes, but phase verify requires the marker to pass locally.

## Common Pitfalls

### Pitfall 1: Look-ahead bias on EPS publish_date
**What goes wrong:** Backtest uses `period_end` (e.g., 2024-03-31 for Q1 2024) as the date EPS becomes known, but disclosure actually happens 30–90 days later. Signals fire on information not yet public.
**Why it happens:** DB schema has `period_end` (the quarter the numbers describe), not the disclosure date.
**How to avoid:** `resolve_eps_publish_date` helper + contract that downstream CANSLIM ALWAYS filters `publish_date <= as_of_date`. Document the 45/90 rule in `docs/audits/phase28-data-audit.md` + `docs/rules_canslim_mdm.md` (DOC-01 dependency).
**Warning signs:** Backtest Sharpe looks too good; entries cluster right on `period_end` dates.

### Pitfall 2: NULL `totaladjustrate` rows
**What goes wrong:** `adjust_ohlc` produces NaN prices; downstream indicator calc silently propagates NaN.
**Why it happens:** Some rows may have missing adjust rate (data vendor gaps, recently-listed tickers).
**How to avoid:** Detect NULL, substitute 1.0 with a FLAG column `adj_imputed=True`, and emit a row count into the audit report.
**Warning signs:** Audit CSV shows nonzero `adj_imputed` count.

### Pitfall 3: `tradingdate` returned as object/string instead of timestamp
**What goes wrong:** Date filter comparisons fail silently; downstream date arithmetic throws.
**Why it happens:** Postgres `date` type can come back as `datetime.date` (not `datetime64[ns]`); MySQL DATETIME may come back with timezone quirks.
**How to avoid:** Always `pd.to_datetime(df["date"]).dt.normalize()` inside every domain helper — matches existing `core/data_loader.py` contract.

### Pitfall 4: Volume adjustment question
**What goes wrong:** After a split, raw `totalvol` is on a pre-split per-share basis, so volume-based indicators (avgvol50, volume spike detection) show a fake discontinuity on ex-split day.
**Why it happens:** CONTEXT.md locks "volume left as-is unless audit shows otherwise."
**How to avoid:** The audit MUST include a volume-continuity spot check on the same 2–3 tickers used for the price spot-check. Flag — don't fix — for Phase 29 to decide.
**Warning signs:** Volume drops/spikes by a factor matching `totaladjustrate` on the split day.

### Pitfall 5: Password with special characters
**What goes wrong:** `create_engine("postgresql+psycopg2://user:pa@ss@host/db")` parses wrong.
**How to avoid:** Always `URL.create(...)`.

### Pitfall 6: Integration test leaves connections open
**What goes wrong:** Repeated pytest runs eventually hit server `max_connections`.
**How to avoid:** Use `with get_engine().connect() as conn:` (context manager) everywhere. Call `get_engine.cache_clear(); engine.dispose()` in a session-scoped fixture teardown.

### Pitfall 7: Timezone on `tradingdate`
**What goes wrong:** Postgres TIMESTAMP WITH TIME ZONE columns come back as tz-aware; comparisons against tz-naive `pd.Timestamp("2024-01-01")` raise or silently miscompare.
**How to avoid:** `.dt.tz_localize(None).dt.normalize()` on read. `tradingdate` should be DATE, not TIMESTAMP — verify in Wave 0 schema introspection.

### Pitfall 8: Using `pandas.read_sql` with raw DBAPI connection
**What goes wrong:** pandas 2.x emits a deprecation warning and may break in 3.x.
**How to avoid:** Pass the SQLAlchemy `Engine` or a `Connection` from `with engine.connect()`, not `psycopg2.connect(...)` directly.

## Code Examples

### Audit query: distinct stockcode count + max date per ticker
```sql
-- Postgres
SELECT stockcode,
       MAX(tradingdate) AS last_seen,
       MIN(tradingdate) AS first_seen,
       COUNT(*)         AS bar_count
FROM stock_eod
GROUP BY stockcode
ORDER BY last_seen;
```
Python side flags delisted:
```python
df = pg.query("... above ...")
delisted = df[df["last_seen"] < "2024-01-01"]
delisted.to_csv("docs/audits/phase28/delisted_candidates.csv", index=False)
```

### Audit query: VN100 EPS coverage pivot
```python
vn100 = [...]  # from scripts / existing VN100 list
sql = """
    SELECT stockcode, year, quarter, period_end, eps
    FROM ratios_stock
    WHERE stockcode IN %(tickers)s
      AND year >= 2014
"""
df = mysql.query(sql, {"tickers": tuple(vn100)})
pivot = (df.assign(yq=lambda d: d["year"].astype(str) + "Q" + d["quarter"].astype(str))
           .pivot_table(index="stockcode", columns="yq", values="eps", aggfunc="first"))
coverage = pivot.notna().sum(axis=1) / pivot.shape[1]
coverage.sort_values().to_csv("docs/audits/phase28/vn100_eps_coverage.csv")
```

### Adjustment spot-check
Pick 2–3 tickers where a large split/bonus is publicly known (candidates to verify in Wave 0: **VNM** (consistent large cash + stock dividends), **FPT** (regular stock dividends), **HPG** (multiple bonus issues)). For each:
1. Load raw OHLC + totaladjustrate for ±10 days around the ex-date.
2. Assert `close_adjusted` on ex-date is within ~1% of `close_adjusted` on the day before (no discontinuity).
3. Assert `close_raw` DOES show the discontinuity (sanity that we're adjusting a real gap).

### Known VN delisted tickers to spot-check (as of 2026-04-08)
| Ticker | Status | Event |
|--------|--------|-------|
| FLC | Delisted HOSE | 2023 — accounting/disclosure violations |
| ROS | Delisted HOSE | 2022 — FLC group |
| HVN | Delisted HOSE→UPCoM | 2022 — negative equity (Vietnam Airlines) — may have since relisted; verify |
| HNG | Delisted HOSE | 2023 — HAGL Agrico |
| HAG | Delisted once, relisted — verify state |

Confidence: MEDIUM. The exact statuses have shifted across 2022–2025 and should be confirmed against `stock_eod.max(tradingdate)` during audit execution rather than taken as ground truth from this doc.

### Integration test skeleton
```python
# tests/test_connectors_integration.py
import os
import pytest
pytestmark = pytest.mark.skipif(
    not os.getenv("POSTGRES_HOST") or not os.getenv("MYSQL_HOST"),
    reason="DB credentials not set; integration test skipped",
)

def test_postgres_select_five():
    from connectors import postgres
    df = postgres.query("SELECT * FROM stock_eod LIMIT 5")
    assert len(df) == 5
    for col in ("stockcode", "tradingdate", "closeprice", "totaladjustrate"):
        assert col in df.columns

def test_mysql_select_five():
    from connectors import mysql
    df = mysql.query("SELECT * FROM ratios_stock LIMIT 5")
    assert len(df) == 5
```

### Unit test for adjust_ohlc (no DB)
```python
# tests/test_connectors_unit.py
import pandas as pd
from connectors.adjust import adjust_ohlc, resolve_eps_publish_date

def test_adjust_ohlc_applies_rate():
    raw = pd.DataFrame({
        "symbol": ["VNM", "VNM"],
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "open_raw":  [100.0, 50.0],
        "high_raw":  [110.0, 55.0],
        "low_raw":   [ 99.0, 49.0],
        "close_raw": [105.0, 52.0],
        "adj":       [  2.0,  2.0],  # post-split, pre-split raw was /2
    })
    out = adjust_ohlc(raw)
    assert out["close"].tolist() == [210.0, 104.0]

def test_resolve_publish_date_imputes_q4_plus_90():
    df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-12-31"]),
        "quarter": [4],
    })
    out = resolve_eps_publish_date(df)
    assert out["publish_date"].iloc[0] == pd.Timestamp("2024-03-30")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pandas.read_sql(sql, psycopg2_conn)` | `pandas.read_sql(text(sql), sqlalchemy_engine_conn, params=...)` | pandas 2.0 (2023) | Raw-DBAPI path deprecated for non-SQLite; use SQLAlchemy |
| `create_engine(f"...{pw}...")` | `URL.create(...)` | SQLAlchemy 1.4+ | Avoids URL-encoding bugs |
| psycopg2 | psycopg (v3) | 2022+ | v3 adds async + COPY; v2 still ubiquitous and fine for sync workloads |
| `mysqlclient` / `mysql-connector-python` | `pymysql` on Windows | — | Pure Python, no C build toolchain required |

## Open Questions

1. **Does `ratios_stock` have a real publish/announce/updated date column?**
   - What we know: STATE.md lists `ratios_stock` with EPS/growth/P/E/ROE/marketcap columns; no schema dump in repo.
   - What's unclear: Presence of `publish_date`/`announce_date`/`updated_at`.
   - Recommendation: Wave 0 task = `information_schema.columns` query; `resolve_eps_publish_date` prefers real column with imputation as fallback. This is the exact shape locked by D-08/D-09.

2. **Is `totaladjustrate` always populated?**
   - Recommendation: Audit counts NULLs per ticker and flags in the audit report.

3. **Does `stock_eod.tradingdate` arrive as DATE or TIMESTAMP?**
   - Recommendation: Wave 0 schema introspection; helper normalizes via `pd.to_datetime(...).dt.tz_localize(None).dt.normalize()` either way.

4. **`stockcode IN (...)` bind-param style differs between Postgres (`ANY(:array)`) and MySQL (`IN :tuple` with `expanding=True`).**
   - Recommendation: Each connector module owns its own ticker-filter idiom; don't try to abstract.

5. **Known VN delistings list currency** — the FLC/ROS/HVN/HNG list above is from training data and should be treated as MEDIUM confidence and cross-checked against `stock_eod` during audit.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 (already configured in `pyproject.toml [tool.uv] dev-dependencies`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, markers include `regression` |
| Quick run command | `uv run pytest tests/test_connectors_unit.py -x` |
| Full suite command | `uv run pytest tests/test_connectors_unit.py tests/test_connectors_integration.py -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Postgres engine builds + `SELECT LIMIT 5` on `stock_eod` succeeds | integration | `pytest tests/test_connectors_integration.py::test_postgres_select_five -x` | ❌ Wave 0 |
| DATA-02 | MySQL engine builds + `SELECT LIMIT 5` on `ratios_stock` succeeds | integration | `pytest tests/test_connectors_integration.py::test_mysql_select_five -x` | ❌ Wave 0 |
| DATA-03 | Delisted-candidate detection produces expected CSV shape on fixture | unit | `pytest tests/test_connectors_unit.py::test_delisted_detection -x` | ❌ Wave 0 |
| DATA-04 | `adjust_ohlc` applies `raw * adj` correctly incl. NULL handling | unit | `pytest tests/test_connectors_unit.py::test_adjust_ohlc_applies_rate -x` | ❌ Wave 0 |
| DATA-04 | Spot-check on real tickers (VNM/FPT/HPG) — continuous adjusted series | integration | `pytest tests/test_connectors_integration.py::test_adjustment_spotcheck -x` | ❌ Wave 0 |
| DATA-05 | `resolve_eps_publish_date` imputes Q1–Q3 + 45d, Q4 + 90d | unit | `pytest tests/test_connectors_unit.py::test_resolve_publish_date_imputes_q4_plus_90 -x` | ❌ Wave 0 |
| DATA-05 | Resolver prefers real column when present | unit | `pytest tests/test_connectors_unit.py::test_resolve_publish_date_uses_real_column -x` | ❌ Wave 0 |
| DATA-06 | VN100 EPS coverage pivot produces non-empty CSV | integration + script smoke | `pytest tests/test_connectors_integration.py::test_vn100_eps_coverage_script -x` | ❌ Wave 0 |
| DATA-07 | `stock_foreign_eod` VN100 coverage query returns rows across 2014–2026 | integration | `pytest tests/test_connectors_integration.py::test_foreign_eod_coverage -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_connectors_unit.py -x` (fast, no DB)
- **Per wave merge:** `uv run pytest tests/test_connectors_unit.py tests/test_connectors_integration.py -v`
- **Phase gate:** Full suite green + audit deliverable (`docs/audits/phase28-data-audit.md` + CSVs) committed before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_connectors_unit.py` — fixture-only tests for `adjust_ohlc` and `resolve_eps_publish_date`, plus a delisted-detection pure-pandas test
- [ ] `tests/test_connectors_integration.py` — live-DB tests, gated with `pytest.mark.skipif(no creds)`, exercising the specific SELECTs required by DATA-01/02/04/06/07
- [ ] `connectors/__init__.py`, `connectors/postgres.py`, `connectors/mysql.py`, `connectors/adjust.py` — modules must exist before tests run
- [ ] `scripts/run_phase28_audit.py` — entry point that writes CSVs under `docs/audits/phase28/` and refreshes the Markdown table counts
- [ ] Dependency install: `uv add sqlalchemy psycopg2-binary pymysql`
- [ ] VN100 ticker list source — either query `stock_list.nhomtop` (Phase 29 will formalize) or hand-list for the audit only

No existing test file in `tests/` covers DB code; this is a clean slate build.

## Sources

### Primary (HIGH confidence)
- `core/data_loader.py` — existing canonical column-map pattern to mirror
- `tests/conftest.py` — existing test harness layout (sys.path + FIXTURES dir)
- `pyproject.toml` — confirms Python 3.10+, pytest 9.0.2, python-dotenv already deps
- `.env` (keys only) — confirms POSTGRES_* and MYSQL_* env var names
- `.planning/phases/28-data-audit-connectors/28-CONTEXT.md` — locked decisions
- `.planning/REQUIREMENTS.md` — DATA-01..DATA-07 exact language
- `.planning/STATE.md` — verified row counts for Postgres/MySQL tables as of 2026-04-08
- SQLAlchemy 2.0 docs + pandas 2.x `read_sql` docs (training data, cross-referenced)

### Secondary (MEDIUM confidence)
- Driver recommendations (psycopg2-binary vs psycopg3, PyMySQL vs mysqlclient on Windows) — from training-data ecosystem consensus
- EPS imputation rule (45/90 days) — standard Vietnam disclosure timing heuristic; locked by CONTEXT.md regardless

### Tertiary (LOW confidence — validate in Wave 0)
- Specific known-delisted VN ticker list (FLC/ROS/HVN/HNG) — must cross-check against `stock_eod` during audit, do not treat as authoritative
- Exact VNM/FPT/HPG split/dividend history — use as spot-check candidates but verify ex-dates against actual data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — SQLAlchemy+psycopg2+PyMySQL is the textbook Python DB stack; well-verified
- Architecture: HIGH — mirrors existing `core/data_loader.py` pattern
- Pitfalls: HIGH on generic DB/pandas pitfalls; MEDIUM on VN-specific (volume adjustment, delisted list)
- VN-specific audit content: MEDIUM — relies on live Wave 0 schema introspection to confirm
- EPS imputation rule: HIGH — locked by user decision regardless of accuracy

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (30 days; Python DB stack is slow-moving)

## RESEARCH COMPLETE

**Phase:** 28 - Data Audit & Connectors
**Confidence:** HIGH (stack/patterns), MEDIUM (VN schema specifics pending Wave 0)

### Key Findings
- Locked decisions leave very little architectural ambiguity: SQLAlchemy + psycopg2-binary + PyMySQL is the right stack, and the connector layer should be ~150 lines mirroring `core/data_loader.py`'s column-map idiom.
- Engine caching via `functools.lru_cache` + `pool_pre_ping=True` + `URL.create(...)` is the minimal correct baseline.
- `adjust_ohlc` and `resolve_eps_publish_date` are pure pandas functions — fully unit-testable on fixture DataFrames with zero live-DB dependency. Live DB only required for the thin integration tests + audit script execution.
- Validation strategy splits cleanly: fast unit layer for every task commit (no DB), gated integration layer for wave merge (skip-if-no-creds).
- Highest-risk pitfalls: look-ahead bias on EPS publish_date (guarded by D-10), NULL `totaladjustrate` handling, tz-aware `tradingdate` coming back from Postgres, and volume-adjustment discontinuity (flagged but not fixed per CONTEXT.md).
- Known-delisted ticker list (FLC/ROS/HVN/HNG) is MEDIUM confidence — must be cross-checked against `stock_eod.max(tradingdate)` during audit execution, not taken from research doc.

### File Created
`.planning/phases/28-data-audit-connectors/28-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | SQLAlchemy/psycopg2/PyMySQL is the canonical Python sync DB stack |
| Architecture | HIGH | Mirrors existing `core/data_loader.py` pattern; locked decisions constrain everything else |
| Pitfalls | HIGH (generic) / MEDIUM (VN-specific) | Well-known DB+pandas pitfalls; VN specifics need live verification |
| Validation | HIGH | Pytest already configured; unit/integration split is standard |

### Open Questions
- Does `ratios_stock` expose a real `publish_date`/`announce_date`/`updated_at` column? (Wave 0 `information_schema` query)
- Is `totaladjustrate` always populated? (Wave 0 audit counts)
- `tradingdate` DATE vs TIMESTAMP WITH TIME ZONE? (Wave 0 schema introspection)
- Current delisting status of FLC/ROS/HVN/HNG/HAG — confirm against live `stock_eod`

### Ready for Planning
Research complete. Planner can now create PLAN.md files with confidence on stack, module layout, test strategy, and audit deliverable shape.
