# Phase 29: VN100 Universe + CANSLIM Scorer - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a configurable VN100 universe loader and a daily CANSLIM scorer that, together, produce a per-day pass/fail + composite score for every active VN100 ticker, respecting EPS publish_date (no look-ahead) and validated against MySQL's `rank_top_stocks.diem_canslim` baseline. Entry confirmation, portfolio construction, and multi-stock backtesting are out of scope — they belong to Phases 30+.

</domain>

<decisions>
## Implementation Decisions

### Universe Construction
- **D-01:** Default universe mode = **current-VN100** (from `stock_list.nhomtop IN ('VN30','VN100')`, Phase 28 confirmed 100 tickers). Accept survivorship bias explicitly in the report.
- **D-02:** All three modes still implemented and selectable via config: `current-vn100` | `liquidity-reconstructed` | `vn30-only`. Only the first is validated in Phase 29 success criteria; the other two are wired up but not deeply tested.
- **D-03:** Semi-annual rebalance (Jan/Jul) applies to `liquidity-reconstructed` mode; `current-vn100` uses the live list at every as_of_date (no intra-phase step-changes).
- **D-04:** Delisted tickers are **flagged, not included**. Survivorship bias is documented in the Phase 29 audit/validation report; true point-in-time reconstruction stays deferred (Phase 28's deferred list keeps ownership).
- **D-05:** RS rating edge case — any ticker with **<252 trading days of history** at `as_of_date` is dropped from the universe *for that date*. Matches UNIV-01 "listed ≥180d" spirit and the L rule's 252d ROC requirement.

### Sector Routing
- **D-06:** Sector classification comes from the **`stock_list` sector/industry column** (Phase 29 research step must confirm exact column name and value vocabulary). Map into four buckets: `bank`, `ctck` (securities), `insurance`, `other`.
- **D-07:** Routing rules:
  - `other` → non-financial EPS table (`is_quarter_nonbank`), use C/A directly
  - `bank` → bank EPS table (`is_quarter_bank`), substitute **PPOP growth** for EPS growth in C/A
  - `ctck` and `insurance` → **excluded** from scoring V1 (CANS-10)
- **D-08:** If the expected sector column does not exist or has unexpected values, fail loudly during scorer initialization — no silent fallback to hardcoded lists.

### CANSLIM Scorer Output
- **D-09:** Scorer returns a tidy DataFrame with one row per `(date, ticker)` and columns:
  - `date`, `ticker`, `sector`
  - `c_pass`, `c_plus_pass`, `a_pass`, `a_plus_pass`, `n_pass`, `s_pass`, `l_pass`, `i_pass`, `liq_pass` (booleans)
  - `rs_rating` (0–100 percentile, raw L-rule value pre-threshold)
  - `score` (0–100 composite — weighting method decided during planning, documented in `docs/rules_canslim.md`)
- **D-10:** Phase 30 consumes this shape directly: filter by `c_pass & a_pass & n_pass & s_pass & l_pass & i_pass & liq_pass` for "qualifies as CANSLIM candidate", or use `score` for ranked candidate lists. Per-letter booleans are kept specifically so Phase 30 can debug which rule killed a candidate.
- **D-11:** Scorer must respect `publish_date` guard from `connectors/eps.py` — every EPS read filters `publish_date <= as_of_date`. No look-ahead, enforced in unit tests.

### CanslimConfig
- **D-12:** `CanslimConfig` dataclass lives at `strategies/canslim/config.py` (new `strategies/canslim/` package). Threshold defaults as per ROADMAP SC5:
  - C ≥ 0.20 (quarterly EPS YoY), A ≥ 0.15 (3yr EPS CAGR)
  - N within 15% of 252d high, S ≥ 1.5× avgvol50
  - L ≥ 80 (RS percentile), I: sum(foreign_net_buy[T-20..T-1]) > 0
  - Liquidity: 20d median turnover ≥ 5B VND
- **D-13:** All thresholds overridable via constructor kwargs (Python-native). No YAML/JSON config file in Phase 29 — sweep scripts can build `CanslimConfig(...)` directly. YAML can come later if needed.

### Validation Methodology
- **D-14:** Spot-check runs on **5 random tradingdates in 2023–2025** drawn from dates where `rank_top_stocks.diem_canslim` has data. Compare our top-10 composite-score tickers vs baseline top-10. Acceptance: **≥4/10 overlap** on at least 3 of the 5 dates (ROADMAP SC6 softened per-date, tightened per-sample).
- **D-15:** Validation report lives at `docs/audits/phase29-canslim-validation.md` + companion CSVs under `docs/audits/phase29/`. Same Markdown-plus-CSV convention as Phase 28 (no notebooks).
- **D-16:** Report must include, per sampled date: our top-10 with sub-scores, baseline top-10, overlap set, qualitative notes on discrepancies (which rule differs? Is it RS, EPS timing, sector routing?).

### Claude's Discretion
- Exact composite-score weighting formula (SC5 doesn't fix it — document whatever is chosen in `docs/rules_canslim.md`).
- Caching strategy for expensive reads (EPS, foreign-net-buy history).
- Unit-test layout under `tests/` for the scorer.
- Internal module split inside `strategies/canslim/` (e.g., one file per letter vs one scorer file).
- Whether to expose a CLI entrypoint in Phase 29 or wait for Phase 30.

### Folded Todos
None — no pending todos matched Phase 29 scope at context-gather time.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- `.planning/ROADMAP.md` §Phase 29 — Goal, success criteria SC1–SC7, dependency on Phase 28
- `.planning/REQUIREMENTS.md` UNIV-01..UNIV-03, CANS-01..CANS-12 — All specific requirements this phase must close

### Upstream Phase 28 Artifacts (mandatory reads)
- `.planning/phases/28-data-audit-connectors/28-CONTEXT.md` — Decisions on connectors, adjustment formula, EPS publish_date imputation
- `docs/audits/phase28-data-audit.md` — VN100 source confirmation, EPS coverage per ticker, delisted list, sector-table split
- `connectors/postgres.py`, `connectors/mysql.py` — Engines + domain helpers to reuse
- `connectors/adjust.py` — `adjust_ohlc()` (all price reads must go through this)
- `connectors/eps.py` — `resolve_eps_publish_date()` (all EPS reads must go through this)

### Project conventions
- `CLAUDE.md` — Naming, module layout, code-docs sync rule (any change to scorer logic must update `docs/rules_canslim.md` in the same commit)
- `pyproject.toml` — Python version + deps

### Existing strategy docs for style reference
- `docs/rules_mdm_classic.md`, `docs/rules_mdm_v2.md`, `docs/rules_vsa.md` — Format/tone to follow when writing `docs/rules_canslim.md`

No external ADRs — CANSLIM is specified directly in ROADMAP + REQUIREMENTS.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `connectors/postgres.py` — already exposes `get_engine()` + `query()`; add VN100-specific helpers here or in a thin `connectors/universe.py` wrapper.
- `connectors/mysql.py` — used for `is_quarter_nonbank`, `is_quarter_bank`, `rank_top_stocks` reads.
- `connectors/adjust.py` + `connectors/eps.py` — Phase 28 deliverables, already tested; Phase 29 is the first real consumer.
- `models/indicators.py` — existing rolling-window helpers (MA50, price_location, rolling highs) that map cleanly to N and S rules.

### Established Patterns
- Dataclass-per-strategy config (see `MDMConfig` in `models/config.py`) — mirror this for `CanslimConfig`.
- DataFrame-as-lingua-franca between layers — scorer takes/returns DataFrames, no custom row classes.
- Validation deliverables are Markdown + companion CSVs under `docs/audits/` (Phase 28 precedent).
- Strategy packages live as siblings of `models/`: new `strategies/canslim/` follows `vn30_vsa/` layout.

### Integration Points
- `strategies/canslim/` (new package) is the sole new top-level entry.
- Phase 30 will `from strategies.canslim import CanslimScorer, CanslimConfig`.
- Phase 28 connectors are imported but not modified.
- No changes to `models/` or `vn30_vsa/` — Phase 29 is additive.

</code_context>

<specifics>
## Specific Ideas

- User confirmed Vietnamese communication preference during this discussion.
- Per-letter boolean output was chosen specifically so Phase 30 can answer "why did this candidate fail?" without re-running the scorer.
- "Fail loud on missing sector column" reflects the Phase 28 pattern of preferring explicit errors over silent fallbacks.

</specifics>

<deferred>
## Deferred Ideas

- Real point-in-time VN100 reconstruction including delisted tickers — stays on Phase 28's deferred list; revisit only if Phase 29 validation shows survivorship bias materially distorts results.
- YAML/JSON configuration files for `CanslimConfig` — Python constructor kwargs are enough for Phase 29. Revisit when sweep/optimize scripts outgrow it.
- Deep validation of `liquidity-reconstructed` and `vn30-only` universe modes — wired up but only `current-vn100` is validated in this phase.
- Handling tickers with sparse EPS history (POW, SSB, BCM, GEE, DSE per Phase 28 audit) — default behavior: they fail C/A naturally; revisit only if they show up as false negatives in validation.
- CLI entrypoint for the scorer — wait until Phase 30 knows what it needs.
- Volume-adjustment revisit — still inherits Phase 28's "only if audit shows discontinuities" stance.

</deferred>

---

*Phase: 29-vn100-universe-canslim-scorer*
*Context gathered: 2026-04-09*
