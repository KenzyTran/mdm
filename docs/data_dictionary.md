# Data Dictionary -- CANSLIM + MDM v7.0

**Scope:** Connectors, adjustment helpers, and CANSLIM scorer introduced in Phases 28-31.

## Connectors

### connectors/postgres.py

Postgres connector for TA data (vpt_wong_stock_v1 database).

Env vars: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` (or `POSTGRES_DATABASE`), `POSTGRES_USER`, `POSTGRES_PASSWORD`

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| get_engine | `get_engine() -> Engine` | SQLAlchemy Engine | Return cached SQLAlchemy engine for Postgres |
| query | `query(sql: str, params: Optional[Mapping[str, Any]]) -> pd.DataFrame` | DataFrame | Execute parameterized SQL, return as DataFrame |
| load_stock_eod | `load_stock_eod(tickers: Iterable[str], start: str, end: str) -> pd.DataFrame` | DataFrame with columns: stockcode, tradingdate, openprice, highestprice, lowestprice, closeprice, totalvol, totaladjustrate | Load daily OHLCV+adjustrate for given tickers and date range |
| load_ratios | `load_ratios(tickers: Iterable[str]) -> pd.DataFrame` | DataFrame (all columns from ratios_stock) | Load all rows from ratios_stock for the given tickers |
| load_stock_rs | `load_stock_rs(start: str, end: str, tickers: Optional[Iterable[str]]) -> pd.DataFrame` | DataFrame with columns: date, ticker, rs_value | Load short-term RS ratings (rss column) from stock_rs for a date range |

### connectors/mysql.py

MySQL connector for fundamentals (stocks_backend database).

Env vars: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB` (or `MYSQL_DATABASE`), `MYSQL_USER`, `MYSQL_PASSWORD`

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| get_engine | `get_engine() -> Engine` | SQLAlchemy Engine | Return cached SQLAlchemy engine for MySQL |
| query | `query(sql: str, params: Optional[Mapping[str, Any]]) -> pd.DataFrame` | DataFrame | Execute parameterized SQL, return as DataFrame |
| load_ratios_stock | `load_ratios_stock(tickers: Iterable[str]) -> pd.DataFrame` | DataFrame (all columns from ratios_stock) | Load all rows from ratios_stock for the given tickers |
| load_is_quarter | `load_is_quarter(tickers: Iterable[str], sector: Literal["nonbank", "bank", "insurance", "stock"]) -> pd.DataFrame` | DataFrame (all columns from is_quarter_<sector>) | Load quarterly income-statement rows from is_quarter_<sector> |

### connectors/adjust.py

Price adjustment for splits/dividends/rights. Per Phase 28 D-05/D-06.

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| adjust_ohlc | `adjust_ohlc(df: pd.DataFrame) -> pd.DataFrame` | DataFrame with original columns + adj_open, adj_high, adj_low, adj_close | Apply corporate-action adjustments: adjusted_price = raw_price * totaladjustrate. Input must have openprice, highestprice, lowestprice, closeprice, totaladjustrate columns. Volume is not adjusted (per D-05). |

### connectors/eps.py

EPS publish-date resolution. Per Phase 28 D-08/D-09/D-10. Pure function -- no DB access.

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| resolve_eps_publish_date | `resolve_eps_publish_date(df: pd.DataFrame) -> pd.DataFrame` | DataFrame with publish_date column added | Resolve/impute publish dates. Resolution order: (1) use existing publish_date / announce_date / updated_at if non-null; (2) impute from (yearreport, lengthreport): Q1-Q3 (lengthreport in {3,6,9}) -> period_end + 45d, Q4/annual (lengthreport in {12, NaN}) -> period_end + 90d |

## CANSLIM Scorer

### strategies/canslim/scorer.py

| Class/Function | Signature | Returns | Description |
|----------------|-----------|---------|-------------|
| CanslimScorer | `CanslimScorer(config: CanslimConfig, universe_loader: UniverseLoader, sector_router: SectorRouter, pg_engine: Any, mysql_engine: Any)` | instance | Main scorer class. Orchestrates all CANSLIM rules into a single tidy output frame. |
| CanslimScorer.score | `score(self, as_of_date: date) -> pd.DataFrame` | DataFrame with columns: date, ticker, sector, c_pass, c_plus_pass, a_pass, a_plus_pass, n_pass, s_pass, l_pass, i_pass, liq_pass, rs_rating, score | Score all eligible VN100 stocks on a given date. Composite formula: 0.70 * boolean_component + 0.30 * rs_rating. |

Composite formula (LOCKED -- see docs/rules_canslim.md §7):
- `score = 0.70 * (100 * sum(passes) / 9) + 0.30 * rs_rating`
- Boolean rules (9): c, c+, a, a+, n, s, l, i, liq
- RS component: rs_rating (0-100), NaN treated as 0

### strategies/canslim/config.py (CanslimConfig)

| Parameter | Default | Locked (rank-1) | Description |
|-----------|---------|-----------------|-------------|
| c_threshold | 0.20 | 0.25 | Quarterly EPS YoY growth minimum (maps to c_yoy in sweep) |
| a_threshold | 0.15 | 0.20 | 3-year EPS CAGR minimum (maps to a_cagr in sweep) |
| n_within_high | 0.15 | 0.10 | Max distance from 252-day high (maps to n_prox in sweep) |
| s_vol_mult | 1.50 | 1.50 | Breakout volume multiplier over avgvol50 |
| l_rs_threshold | 80.0 | 80.0 | RS percentile rank minimum (0-100) |
| i_lookback_days | 20 | 20 | Foreign net buy lookback days |
| liquidity_min_turnover_vnd | 5_000_000_000 | 5_000_000_000 | Minimum 20d median turnover in VND |
| min_history_days | 252 | 252 | Minimum history required to score a ticker |

## Data Sources

| Source | Database | Key Tables | Coverage |
|--------|----------|-----------|----------|
| Postgres (TA) | vpt_wong_stock_v1 | stock_eod (5.9M rows, 2936 stocks), stock_rs, nganh_rs, nhnl_indicator, index_eod, stock_list, stock_signals | Through 2026-04-08 |
| MySQL (Fundamentals) | stocks_backend | ratios_stock (EPS, growth, P/E, ROE, market cap), is_quarter_nonbank, is_quarter_bank, is_quarter_insurance, is_quarter_stock, rank_top_stocks (has existing diem_canslim baseline) | Varies by stock |

## Column Schemas

### stock_eod (Postgres)

| Column | Type | Description |
|--------|------|-------------|
| stockcode | VARCHAR | Ticker symbol |
| tradingdate | DATE | Trading date |
| openprice | NUMERIC | Open price (raw, 1000 VND) |
| highestprice | NUMERIC | High price (raw) |
| lowestprice | NUMERIC | Low price (raw) |
| closeprice | NUMERIC | Close price (raw) |
| totalvol | NUMERIC | Total volume (shares) |
| totaladjustrate | NUMERIC | Cumulative adjustment rate for OHLC |

### ratios_stock (MySQL)

| Column | Type | Description |
|--------|------|-------------|
| stockcode | VARCHAR | Ticker symbol |
| yearreport | INT | Report year |
| lengthreport | INT | Report length in months (3/6/9/12) |
| eps | NUMERIC | Earnings per share |
| roe | NUMERIC | Return on equity |
| pe | NUMERIC | Price-to-earnings ratio |
| (other columns) | NUMERIC | Additional fundamental metrics |
