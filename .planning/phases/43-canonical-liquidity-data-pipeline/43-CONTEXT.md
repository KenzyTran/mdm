---
phase: 43-canonical-liquidity-data-pipeline
milestone: v10.0
created: 2026-04-22
---

# Phase 43 Context & Decisions

Phase 43 productionizes two canonical inputs built in quick task `260421-lb4`:
- `data/vn_liquidity_proxy.csv` (5 yfinance proxies, 2867 rows, 2015-2025)
- `data/sbv_policy_events.csv` (12 hand-curated SBV events, 2017-2023)

Upstream research verdict: **GO** (DXY 20d z corr = -0.19, EEM 20d z corr = +0.19, SBV regime CAGR spread 55.76pp). See `docs/research/liquidity_proxy_correlation.md`.

Phase 44 (Macro Filter Module) is the downstream consumer — it will use `pd.merge_asof(direction='backward')` to merge these CSVs onto VN30 trading dates with no look-ahead. Phase 43 MUST document the merge contract and publication-lag policy so Phase 44 doesn't have to guess.

---

## Key Decisions (locked for this phase)

### D-01: Productionize, do not recreate
**Decision:** Harden the existing `analysis/build_liquidity_proxy.py` in place — do NOT rewrite from scratch. Preserve the yfinance ticker map, the outer-join pattern, and the existing output schema.

**Why:** The quick task's evidence base (`docs/research/liquidity_proxy_correlation.md`) was computed against this specific CSV. Rewriting would invalidate the GO verdict and force re-running the correlation analysis. Additive hardening only.

### D-02: Date range stays 2015-01-01 → 2026-01-01
**Decision:** Default `--start` = `2015-01-01`, default `--end` = `2026-01-01`. Keep existing constants as module-level defaults consumed by the CLI parser.

**Why:** Matches the Phase 42 reconciled baseline window (VN30 2015-2026) and the quick-task correlation evidence. ROADMAP line 827 says "2014-2026" for SBV events but the VN30 trading data starts 2015-01-05 and the macro filter will be applied on VN30 dates only — 2015 is the load-bearing floor.

### D-03: CLI arg names (locked)
- `--start YYYY-MM-DD` (default `2015-01-01`)
- `--end YYYY-MM-DD` (default `2026-01-01`)
- `--output PATH` (default `data/vn_liquidity_proxy.csv`)
- `--max-retries N` (default `3`, yfinance 401/429/transient retry cap)
- `--retry-backoff-sec S` (default `5`, base sleep between retries; exponential `S * 2**attempt`)

**Why locked:** Phase 44/45 walkforward scripts will shell out to this builder; flag names MUST be stable.

### D-04: yfinance retry policy
**Decision:** Wrap `yf.download` in a retry loop that catches:
- `requests.exceptions.HTTPError` with status 401, 403, 429
- `requests.exceptions.ConnectionError`
- `requests.exceptions.Timeout`
- Empty DataFrame returned (yfinance sometimes silently returns empty on rate limit)

Exponential backoff: `sleep(retry_backoff_sec * 2**attempt)`. After `max_retries` exhausted, raise the final exception with ticker + date range context.

**NOT caught:** KeyError on missing `Close` column, TypeError, ValueError — these indicate a real schema change in yfinance and MUST surface.

**Why:** ROADMAP success criterion 1 says "yfinance 401 retries and missing-column errors are handled, not silenced." Retry transient failures; fail loud on schema errors.

### D-05: Missing-column error contract
**Decision:** If `fetch_ticker()` returns a DataFrame without a `'Close'` column (or a MultiIndex without a `'Close'` level), raise `RuntimeError(f"ticker {symbol}: 'Close' column missing — yfinance schema changed")`. Do NOT return empty Series, do NOT forward-fill to hide the gap.

**Why:** Silent missing-column errors would produce all-NaN columns in the CSV, which Phase 44 would silently inherit as a "no signal" day — hiding a real outage behind a successful-looking CSV.

### D-06: SBV CSV schema freeze
**Schema:** `date, rate_change_pct, new_refinance_rate_pct, direction, source`

The existing 4-column schema (`date, rate_change_pct, new_refinance_rate_pct, direction`) is extended by a 5th `source` column containing a short citation string per row (e.g., `"Reuters 2022-09-22 SBV hikes refinance rate"` or `"SBV press release sbv.gov.vn/webcenter/ShowProperty?nodeId=..."`). One primary source per row is sufficient; multiple sources separated by `; ` when cross-checked.

**Direction values:** `easing | tightening` only. `neutral` is DERIVED downstream (Phase 44) via 90-day decay, NOT stored in the CSV.

**Why:** ROADMAP success criterion 2 says "documented sources per row." Inline `source` column keeps the CSV self-contained and one-row-edit extensible (criterion 4).

### D-07: SBV event coverage target
**Decision:** Keep the existing 12 rows as canonical (Reuters + SBV press + Vietnam News sources already verified by quick task). Add source citations per row. Do NOT invent additional events for 2014-2016 or 2024-2025 just to hit a higher count — the quick-task SUMMARY confirmed SBV held rates steady across most of those years and no additional events could be honestly sourced.

If the planner-executor finds 2-3 additional well-sourced events during the source-citation pass (e.g., a 2024 discount-rate micro-adjustment with a Reuters link), they may be appended. Otherwise 12 rows stands.

**Why:** D-06 requires source-per-row. Any event without a verifiable source violates the curation contract.

### D-08: Publication-lag policy (documents Phase 44 merge contract)
**DXY / EEM / VNM (US-market yfinance tickers):**
- US cash session closes ~22:00 ICT (Indochina Time) when DST active, ~23:00 ICT in US winter.
- First VN trading session that can use the US close is THE NEXT VN trading day (T+1 in VN calendar).
- Merge contract: `pd.merge_asof(vn30_df, proxy_df, on='date', direction='backward')` — this assigns each VN30 date the most recent proxy close strictly `<=` that date. With US close on date D (22:00 ICT) and VN session opening 09:00 ICT on D+1, `merge_asof(direction='backward')` on raw CSV dates naturally lags by 1 VN trading day. NO manual shift needed.

**USD/VND (yfinance `VND=X`):**
- 24h FX, quoted throughout VN session. Same-day merge is technically available but USD/VND near-zero correlation in quick-task => exclude from active feature set, keep in CSV for transparency.

**SBV events:**
- Announcements are typically intra-session VN press releases (morning/afternoon).
- Policy signal available AT-OR-AFTER event close: merge on `event_date + 1 VN_trading_day` to guarantee the announcement was public before the session opened.
- In practice: Phase 44's SBV regime lookup uses `merge_asof(direction='backward')` on `event_date + 1 business day` as the effective date.

### D-09: Look-ahead traps documented (spec-level)
The spec MUST enumerate at least:
1. Same-day DXY/EEM merge: FORBIDDEN. Only `direction='backward'` with natural 1-day lag.
2. Weekend/holiday bridging: Last-known-value carry is the correct behavior for `merge_asof(backward)` — do not forward-fill inside the CSV itself (keeps raw data raw).
3. SBV event-day signal: If a SELL signal fires on the same date as an SBV rate hike announced at 14:00, Phase 44 MUST NOT use that regime tag for that day's decision — it is available only from T+1 session open.

### D-10: Not in scope for Phase 43
- Building the actual z-score / regime signals — Phase 44 work (MACRO-01..03)
- Automating SBV event scraping — deferred to v2 requirements (AUTO-02)
- Re-running correlation analysis — already done in quick task 260421-lb4

### D-11: SUMMARY.md convention
Each plan produces `43-NN-SUMMARY.md` on completion per GSD convention. Summary must document any yfinance API changes encountered during hardening (Phase 44 regression signal).

---

## File Ownership (no conflicts)

| Plan | Modifies |
|------|----------|
| 43-01 | `analysis/build_liquidity_proxy.py`, `data/vn_liquidity_proxy.csv` (regenerated), `43-01-SUMMARY.md` |
| 43-02 | `data/sbv_policy_events.csv`, `43-02-SUMMARY.md` |
| 43-03 | `docs/liquidity_proxy_spec.md`, `43-03-SUMMARY.md` |

Plans 43-01 and 43-02 touch disjoint files → Wave 1 parallel.
Plan 43-03 needs final schemas from both → Wave 2 sequential.

---

## Downstream Consumer Contract (Phase 44)

Phase 44 will:
1. Load `data/vn_liquidity_proxy.csv` into a DataFrame, forward-fill within-column gaps, compute 20-day rolling z-scores for `dxy_close` and `eem_close`.
2. Load `data/sbv_policy_events.csv`, shift each event date by +1 business day to build an "effective date" column, then classify VN30 dates via `pd.merge_asof(direction='backward')` with 90-day decay to `neutral`.
3. Regression-test byte-exact v6.0 parity when `macro_filter_enabled=False`.

Phase 43's job: freeze the input contracts so Phase 44 never has to revisit them.
