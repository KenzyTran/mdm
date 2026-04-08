# v7.0 Research Synthesis — CANSLIM + MDM on VN100

**Date:** 2026-04-08
**Inputs:** 01-canslim-rules.md, 02-entry-confirmation.md, 03-portfolio-construction.md, 04-vietnam-pitfalls.md

---

## Top-Level Strategy (locked)

Long-only, max 8 positions, event-driven, on a static-with-rebalance VN100 universe. Two-stage signal:

1. **MDM gate** (existing HybridEngine + fail-safe) provides regime: BUY / CASH / SELL.
2. **Per-stock signal** fires only when MDM=BUY:
   - **CANSLIM rank** (top-N candidate set, recomputed daily)
   - **Entry confirmation** (pivot/breakout) on a candidate ticker triggers actual buy
3. Exit priority: MDM SELL → 8% hard stop → MA50 trailing → RS deterioration. **No fixed profit targets.**

This separates *what to buy* (CANSLIM) from *when to buy it* (entry confirmation) from *whether to be in market* (MDM) — three independent failure modes, each testable in isolation.

---

## Data Sources Reconciled

| Field | Source | Notes |
|---|---|---|
| Daily OHLCV (VN universe) | Postgres `stock_eod` (5.9M rows, 2936 stocks) | **Verify:** prices adjusted for splits/divs? include delisted? |
| Pre-computed RS (rss/rsm/rsl) | Postgres `stock_rs` | Optional baseline; we will compute IBD-style ourselves |
| Sector RS | Postgres `nganh_rs` | Optional |
| Foreign net buy daily | Postgres `stock_foreign_eod` | Primary I-rule input |
| New high / new low | Postgres `nhnl_indicator` | Optional cross-check |
| Index OHLC | Postgres `index_eod` | For benchmark + MDM input |
| Stock master + sector + group | Postgres `stock_list` (`nhom`, `nhomtop`, `nganh`) | VN100 proxy filter |
| Quarterly financials | MySQL `is_quarter_nonbank` / `_bank` / `_insurance` / `_stock` | **Need publish_date column or estimate +45d** |
| Annual financials | MySQL `is_year_*` | |
| Ratios (EPS, ROE, P/E, mcap) | MySQL `ratios_stock` | 4580 rows — may be sparse, verify per-stock coverage |
| Existing CANSLIM baseline | MySQL `rank_top_stocks.diem_canslim` | Validation reference |
| Live ticks/quotes | Redis (25k keys) | **Deferred** to live-signal phase |

---

## CANSLIM Rules — Locked Defaults (with sweep)

| Letter | Rule | Default | Sweep |
|---|---|---|---|
| C | Latest Q EPS YoY | ≥20% | {.10, .15, .20, .25} |
| C+ | EPS acceleration | latest > mean(prior 2Q) | — |
| A | 3yr EPS CAGR | ≥15% | {.10, .15, .20, .25} |
| A+ | EPS positive last 3yr | required | — |
| N | Within 15% of 252d high | ≤15% | {.05, .10, .15, .20} |
| S | Vol vs 50d avg on entry day | ≥1.5× | {1.25, 1.5, 2.0} |
| L | IBD RS rating (VN100 universe) | ≥80 | {70, 80, 90} |
| I | Foreign net-buy 20d sum | >0 | window {10, 20, 40} |
| M | MDM state | == BUY | — |
| Liquidity | 20d median turnover | ≥5B VND | — |

**RS formula:** `0.4*ROC(63) + 0.2*ROC(126) + 0.2*ROC(189) + 0.2*ROC(252)`, percentile-rank within VN100 only.

**Sector exclusions for C/A:** Banks (use PPOP growth substitute), Securities firms / CTCK (exclude — EPS too volatile), Insurance (exclude V1).

---

## Entry Confirmation — Locked

**MDM BUY is necessary but not sufficient.** Wait for stock-level confirmation, max 20 trading days from MDM BUY event, then opportunity expires.

| Option | Rule | v7.0 priority |
|---|---|---|
| **A — 52wk high + volume** | `close > max(close,252) AND vol ≥1.5*avgvol50 AND close>open AND upper-half close` | **MVP, ship first** |
| **C — Pocket Pivot** | `close>open AND close≥MA50 AND vol > max(down-day vols last 10d) AND within 15% of 50d high` | **A/B vs A** |
| B — Flat-base breakout | Geometric pivot detection + buy-zone | Defer to v7.1 |

Entry executes at **next-day open** (ATO), not signal-bar close.

---

## Portfolio Engine — Locked

```yaml
exposure_policy: strict     # Policy A
mdm_gate:
  BUY:  { max_positions: 8, target_exposure: 1.00, allow_new_entries: true }
  CASH: { max_positions: 8, target_exposure: hold, allow_new_entries: false }
  SELL: { max_positions: 0, liquidate: next_open }

position_sizing: equal_weight  # 12.5% per slot, 8 slots
lot_rounding: 100              # HOSE board lot
liquidity_filter: adv_20d > 10 * position_size

stop_loss:
  hard_stop_pct: 0.08
  limit_down_handling: exit_next_open_if_limit_down
  trailing_stop: ma50_close_break_on_volume (1.25x)

exit_priority:
  1: mdm_regime_sell
  2: hard_stop_8pct
  3: ma50_trailing_break
  4: rs_deterioration  # RS<70 for 5 sessions

reentry_cooldown: 5 days per ticker after stop

transaction_costs:
  commission: 0.0025  # both sides
  sell_tax:   0.0010
  slippage:   0.0010
  round_trip_floor: 0.0060
```

**Sweep:** hard_stop_pct {.06, .07, .08, .10}, slots {5, 8, 10}, fill_window_days {1, 3, 5, 10}.

---

## Vietnam-Specific Hard Constraints (must implement)

1. **T+2 settlement** (since 2022-08-29) — buy D, sellable D+3
2. **7% HOSE daily limit** — ceiling lock blocks fills, floor lock blocks exits → exit next open
3. **VN100 rebalance Jan/Jul** — universe step-changes, not daily
4. **EPS publish_date** — `WHERE publish_date <= bar_date` to avoid restatement look-ahead
5. **Adjusted prices** required for RS, N, base detection
6. **Delisted history** must be in `stock_eod` or backfilled before backtest
7. **`state[t-1]` rule** for equity curve (project's known 707% vs 93% bug)
8. **Tet calendar** — use HOSE trading-day calendar
9. **Sector schemas** — use `is_quarter_nonbank` for general stocks, separate handling for banks
10. **Re-entry cooldown** 5d/ticker after stop

---

## Top Risks (ranked)

1. Survivorship — `stock_eod` may exclude delisted (FLC, ROS, HVN…) → **Phase 1 audit**
2. EPS look-ahead via restated audited numbers → publish_date column
3. No peer-reviewed CANSLIM-on-Vietnam evidence → in-sample sweep + OOS validation required
4. Vietnam momentum unstable (~85% retail, mean-reverting) → expect lower Sharpe than US, may need shorter RS lookbacks
5. CANSLIM IC on VN100 unknown → equal-weight only until validated
6. Capacity at 100B+ VND with 8 positions on small-cap end of VN100
7. MDM whipsaw (false SELL) under Policy A → may need Policy B/C in v7.1

---

## Validation Plan

| Stage | Period | What |
|---|---|---|
| In-sample | 2014-2018 | Sweep CANSLIM thresholds + entry option A vs C |
| Out-of-sample | 2019-2025 | Lock thresholds, run untouched |
| Sensitivity | both | (a) current VN100 (b) liquidity-reconstructed (c) VN30-only |
| Baseline | both | vs `rank_top_stocks.diem_canslim` ranking, vs VN-Index, vs MDM-only-on-index |
| Honesty | OOS | Sharpe with risk-free = 10Y VN govt ~3.0%, real CAGR (CPI 3-4%), vs deposit ~5-6%, vs gold |

**Targets (from research):** Sharpe uplift > 0.20 vs benchmark, MaxDD reduction > 30%.

---

## Open Questions for Phase 1 (data audit)

These MUST be answered before any strategy code:

1. Does `stock_eod.closeprice` adjust for corporate actions?
2. Does `stock_eod` include delisted tickers (audit: count distinct stockcodes with `max(tradingdate) < 2024`)?
3. Is `stock_list.nhomtop` static-current or has effective dates? Can we derive VN100 membership from it?
4. Does MySQL `is_quarter_*` have a publish_date? If not, we add `publish_date = period_end + 45d` default.
5. What's the per-stock fundamental coverage in `ratios_stock`/`is_quarter_*` for VN100 names back to 2014?
6. Does `stock_foreign_eod` cover all VN100 with daily values back to 2014?
