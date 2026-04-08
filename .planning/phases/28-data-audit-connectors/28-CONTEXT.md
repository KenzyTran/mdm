# Phase 28: Data Audit & Connectors - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver Python connectors for the Postgres and MySQL databases that hold Vietnamese market data, plus an audit report that quantifies data-quality risks for the VN100 CANSLIM + MDM backtest (v7.0 milestone). Scope is limited to connectors, schema inspection, data audit, and adjustment/EPS helpers. Universe construction, scoring, and backtest logic belong to Phases 29+.

</domain>

<decisions>
## Implementation Decisions

### Connector Design
- **D-01:** Use **SQLAlchemy engine + `pandas.read_sql`** as the query pattern for both Postgres and MySQL. Rationale: backtest code is pandas-heavy, engine pool handles reconnects, no async needed for offline work.
- **D-02:** One module per DB: `connectors/postgres.py` and `connectors/mysql.py`. Each exposes:
  - `get_engine()` — returns cached SQLAlchemy engine, creds loaded from `.env` via `python-dotenv`
  - `query(sql, params=None) -> pd.DataFrame` — typed helper
  - A handful of domain helpers (e.g., `load_stock_eod(tickers, start, end)`, `load_ratios(tickers)`) built on top
- **D-03:** Credentials come **only** from `.env` (already contains `POSTGRES_HOST/PORT/USER/PASSWORD/DB`, `MYSQL_HOST/PORT/USER/PASSWORD/DB`). Never hardcode.
- **D-04:** Integration test: a small `tests/test_connectors.py` (or script under `scripts/`) that runs a `SELECT ... LIMIT 5` against `stock_eod` and `ratios_stock`. Must pass before phase is verified.

### Price Adjustment
- **D-05:** `stock_eod` **is unadjusted**. Adjusted price = raw price column × `totaladjustrate` column from the same row. Apply to `openprice`, `closeprice`, `highestprice`, `lowestprice` (volume left as-is unless audit shows otherwise).
- **D-06:** Provide a helper `adjust_ohlc(df)` in `connectors/` (or a new `data/adjust.py`) that takes a raw `stock_eod` DataFrame and returns adjusted OHLC columns. All downstream backtest code must use adjusted prices.
- **D-07:** Spot-check the helper on 2–3 tickers with known large splits/dividends to confirm the continuous series looks right.

### EPS publish_date
- **D-08:** Assume the DB does **not** expose a real publish_date. Phase 28 will still briefly inspect `ratios_stock` schema; if a usable column (publish_date / updated_at / announce_date) exists, prefer it — otherwise impute.
- **D-09:** Default imputation rule: `publish_date = period_end + 45 days` for Q1–Q3, `period_end + 90 days` for Q4 / annual. Document this as the assumption backtests rely on.
- **D-10:** Expose a helper `resolve_eps_publish_date(df)` that adds a `publish_date` column using the imputation rule (or the real column if found). Downstream CANSLIM phases must filter EPS by `publish_date <= as_of_date` — no look-ahead.

### Audit Report + Delisted Handling
- **D-11:** Deliverable is a **Markdown report + companion CSVs** under `docs/audits/phase28-data-audit.md` and `docs/audits/phase28/*.csv`. No Jupyter notebook (bad git diff).
- **D-12:** Report must contain, at minimum:
  - Distinct stockcode count in `stock_eod`
  - Count and list of stockcodes with `max(tradingdate) < 2024-01-01` (delisted candidates)
  - Explicit check for known delistings (FLC, ROS, HVN, …) — present or absent
  - Price-adjustment convention confirmation (`totaladjustrate` usage)
  - EPS coverage per current VN100 ticker back to 2014 (quarterly rows present vs gaps)
  - `stock_foreign_eod` daily VN100 coverage 2014-2026 (gaps, missing tickers)
- **D-13:** Delisted tickers are **flagged only** in Phase 28. Actual survivorship-bias handling (including delisted stocks in the backtest universe) is deferred to Phase 29 (VN100 Universe).

### Claude's Discretion
- Exact SQLAlchemy URL format, pool size, connection timeout.
- File layout inside `connectors/` (whether to add `__init__.py` re-exports).
- CSV schemas for the audit companion files.
- Choice of which 2–3 tickers to use for the adjustment spot-check.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- `.planning/ROADMAP.md` §Phase 28 — Goal, success criteria, dependency on Phase 27
- `.planning/REQUIREMENTS.md` DATA-01..DATA-07 — Specific requirements this phase must close

### Project conventions
- `CLAUDE.md` — Project conventions, naming, module layout, code-docs sync rule
- `pyproject.toml` — Dependencies; add `sqlalchemy`, `psycopg2-binary`, `pymysql` (or `mysql-connector-python`) here
- `.env` — Credential keys already defined (POSTGRES_*, MYSQL_*)

No external ADRs — this is a greenfield connector layer.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `python-dotenv` already a project dep and used elsewhere — reuse for `.env` loading.
- `models/data_loader.py` and `vn30_vsa/data_loader.py` already load CSVs with column normalization — the new connectors can follow the same column-mapping style so downstream engines don't care whether data came from CSV or DB.

### Established Patterns
- snake_case modules, PascalCase classes, typed helpers.
- DataFrames are the lingua franca between layers.
- No existing DB code — this phase introduces the first DB dependency.

### Integration Points
- New `connectors/` package at repo root (sibling of `models/`, `vn30_vsa/`).
- Phase 29+ will import `from connectors.postgres import load_stock_eod` etc.
- `.env` loading is the only cross-cutting concern.

</code_context>

<specifics>
## Specific Ideas

- User confirmed the concrete adjustment formula: `adjusted_price = price_col * totaladjustrate` directly from `stock_eod`. This is the canonical rule — no corporate-actions table lookup needed.
- User was new to the EPS publish_date concept; imputation is acceptable provided the rule is clearly documented so Phase 29 CANSLIM rules can rely on it.

</specifics>

<deferred>
## Deferred Ideas

- Active survivorship-bias handling (actually including delisted tickers in the backtest universe) — Phase 29.
- Scraping HOSE disclosures for real EPS publish_date — out of scope, only consider if imputation proves materially wrong later.
- Async connectors / connection pooling tuning for live use — not needed for offline backtests.
- Adjustment of `totalvol` — only revisit if audit shows volume discontinuities.

</deferred>

---

*Phase: 28-data-audit-connectors*
*Context gathered: 2026-04-08*
