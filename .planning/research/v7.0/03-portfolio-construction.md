# Portfolio Construction & Capital Allocation — Research (v7.0)

**Scope:** Long-only multi-stock VN30/VN100 backtest, top-down MDM gate + bottom-up CANSLIM.
**Overall confidence:** MEDIUM.

---

## 1. Capital Allocation via Market-Timing Gate

### 1.1 Binary (100/0) — Faber
Faber (2007, updated 2013) *A Quantitative Approach to Tactical Asset Allocation* — 10-month SMA rule.
- Buy & Hold: CAGR ~9.9%, MaxDD ~46%, Sharpe ~0.46
- Timing: CAGR ~10.5%, MaxDD ~9.5%, Sharpe ~0.76
- Post-2013 OOS weaker; alpha decayed, DD reduction persists.

**Takeaway:** Binary reliably halves MaxDD, modestly improves CAGR.

### 1.2 Three-state (100/50/0)
Widely used by AQR/Newfound/ReSolve. Neutral as half-position to reduce whipsaw. Newfound 2019 shows binary has severe specification risk; ensemble/graduated approaches cut result variance 30-50%.

### 1.3 Graduated
~Same CAGR, 20-30% lower turnover, +0.05-0.10 Sharpe.

### 1.4 Antonacci Dual Momentum / GEM
*Dual Momentum Investing* (2014).
- **GEM: CAGR 17.4%, Sharpe 0.87, MaxDD 22.7%** (1974-2013)
- Post-2013 OOS weaker (~5% whipsaw drag)

**Relevance:** Structurally identical to MDM CASH/SELL gate. Regime filter adds ~4-7% CAGR, halves MaxDD.

### 1.5 Summary

| Policy | CAGR uplift | MaxDD reduction | Turnover | Whipsaw |
|---|---|---|---|---|
| Binary 100/0 | +0.5-2% | 50-70% | Low | HIGH |
| Three-state | +0.5-2% | 40-60% | Med | Med |
| Graduated | +0-1.5% | 40-60% | Med-High | LOW |
| Dual Momentum | +4-8% | 50-65% | Low | Med |

---

## 2. Position Sizing with ≤8 Positions

### 2.1 Equal weight (1/N)
**DeMiguel, Garlappi & Uppal (2009, RFS)** — 1/N beats 14 optimization-based sizers OOS. Parameter-estimation error dominates at small N. **Academic default for N≤10.**

### 2.2 Score-weighted
Adds 50-150 bps/yr when rank IC > 0.05, zero when noisy. CANSLIM IC typically 0.02-0.05. **Not recommended until IC validated.**

### 2.3 Fractional Kelly
`f* = (pb−q)/b`. Trend p~0.40 b~2.5 → f* ≈ 0.16. Full Kelly rejected (Thorp, Ziemba). Half-Kelly × 8 ≈ 64% exposure. p and b drift 30-50% across regimes — unstable.

### 2.4 Risk parity
Weaker single-market small-N. Typical +30-50 bps Sharpe.

### 2.5 O'Neil pyramid
**No academic evidence.** Trader folklore. +1-2% CAGR but 2× whipsaw.

### 2.6 Recommendation
**Equal-weight, 12.5%/slot × 8 slots.** Add Kelly/vol-scaling only after baseline validated.

---

## 3. O'Neil 7-8% Stop Loss

- **No peer-reviewed study directly validates 7-8%.** Heuristic.
- **Kaminski & Lo (2014, JFM)** — stops add value in momentum regimes, subtract in mean-reversion. 10-15% monthly stop on US equities +50-100 bps/yr.
- AAII CAN SLIM: 19.2% annualized since 1998 vs SP500 5.7% (whole screen).

**Verdict:** Defensible for breakouts but interacts badly with Vietnam 7% limit. **Recommend 7-8% hard stop, exit next open if limit-down.**

### Trailing variants
- MA50 break on volume — O'Neil/Minervini classic, empirically robust
- MA10 — tighter, whipsaws more
- Percent-trailing (15-20%) — Covel/Clenow standard
- ATR-trailing (Chandelier)

**Recommendation:** MA50 trailing (core trend) + 8% hard (broken thesis).

---

## 4. Exit Rules Beyond Stop Loss

1. **Regime exit (MDM=SELL):** Full liquidation. Highest priority.
2. **Stock-specific deterioration:** RS<70, MA50 break on volume, DD cluster
3. **Profit-taking:**
   - Climax run: 20-25% gain in 1-3 weeks
   - 8-week hold rule (counterbalance)
   - Fixed 20-25% target: cuts CAGR 2-3% (caps winners), reduces MaxDD ~20%
4. **Hold forever if uptrend intact** — Hurst/Ooi/Pedersen (2017) *"Century of Evidence on Trend Following"*

**Recommended exit priority:** MDM SELL > 8% hard stop > MA50 break > RS deterioration. **No fixed profit targets.**

---

## 5. MDM Gate Integration — Three Policies

### Policy A — Strict (RECOMMENDED BASELINE)
- **BUY:** 100% deployed, 8 slots, fill over next 5 days
- **CASH:** Hold existing, no new entries; stops/trail still active
- **SELL:** Liquidate all on next open

**Pros:** Simple, clean attribution, matches Faber/Antonacci.
**Cons:** Whipsaw on regime flips.

### Policy B — Moderate
- BUY: 100%/8 | CASH: Hold, trim oversized | SELL: 50% then 0% if persists 5d
**Pros:** Reduces false-SELL whipsaw. **Cons:** More params, muddier attribution.

### Policy C — Graduated
- BUY: 25→50→75→100% over 10d | CASH: hold | SELL: 75→50→25→0% over 6d
**Pros:** Smoothest equity curve. **Cons:** Complex; gives up alpha in strong bulls.

**Recommendation:** **Policy A for v7.0.** Cleanest attribution. Evaluate B/C in v7.1+.

---

## 6. Vietnam Microstructure & Costs

- **Commission:** 0.10-0.35% each side; retail ~0.20-0.25%
- **Sell tax:** 0.10% of gross (statutory)
- **Round-trip:** ~0.45-0.55% of notional
- **Lot size:** HOSE 100 shares. Round down.
- **T+2.5:** Bought T, sellable T+2.5. Not binding for week-to-month holds but blocks MDM=SELL exits <2d old.
- **7% daily limit (HOSE):** Critical. If limit-down gap, cannot exit at 8% stop — backtest must model `if low == limit_down → exit next open`.
- **Foreign ownership limits:** Banks ~30%. Ignore for domestic VND backtest.
- **Liquidity floor:** Only trade stocks with 20-day ADV > 10× position size.

---

## 7. Survivorship Bias Mitigation (Static VN100)

1. **Delisted-stock inclusion** — manually add historical members (~5-10 cases 2015-2025)
2. **Historical-intersection universe** — union across years; over-inclusive
3. **Liquidity-threshold reconstruction** *(RECOMMENDED)* — top 100 by 60-day turnover at each rebalance. Bias-free by construction.
4. **Sensitivity analysis** — current VN100 vs reconstructed vs VN30-only
5. **Document explicitly**

---

## 8. RECOMMENDED PORTFOLIO CONSTRUCTION SPEC

```yaml
exposure_policy: strict     # Policy A
mdm_gate:
  BUY:  { max_positions: 8, target_exposure: 1.00, allow_new_entries: true }
  CASH: { max_positions: 8, target_exposure: hold, allow_new_entries: false }
  SELL: { max_positions: 0, target_exposure: 0.00, liquidate: next_open }

position_sizing:
  method: equal_weight
  slots: 8
  per_slot_pct: 0.125
  lot_rounding: 100
  liquidity_filter:
    min_adv_20d_multiple: 10
  max_position_concentration: 0.15

entry_rules:
  trigger: (mdm_state == BUY) AND canslim_rank_top_8 AND entry_confirmation_fired
  fill_window_days: 5
  entry_price: next_day_open

stop_loss:
  hard_stop_pct: 0.08
  limit_down_handling: exit_next_open_if_limit_down
  trailing_stop: ma50_close_break_on_volume
  ma50_volume_confirm_multiple: 1.25

exit_priority:
  1: mdm_regime_sell
  2: hard_stop_8pct
  3: ma50_trailing_break
  4: stock_rs_deterioration   # RS<70 for 5 sessions
  # NO fixed profit targets

transaction_costs:
  commission_pct: 0.0025
  sell_tax_pct:   0.0010
  slippage_pct:   0.0010
  round_trip_budget: 0.0060

market_constraints:
  settlement: T+2.5
  daily_price_limit_pct: 0.07
  board_lot: 100
  short_selling: disabled

universe:
  base: vn100_liquidity_reconstructed
  rebalance_frequency: quarterly
  sensitivity_runs: [vn100_current, vn30_only]

validation_targets:
  benchmark: vnindex_buy_hold
  required_sharpe_uplift: "> 0.20 vs benchmark"
  required_maxdd_reduction: "> 30% vs benchmark"
```

### Sweeps
- hard_stop_pct: {0.06, 0.07, 0.08, 0.10}
- slots: {5, 8, 10}
- fill_window_days: {1, 3, 5, 10}
- ma50_volume_confirm_multiple: {1.0, 1.25, 1.5}

### Excluded from v7.0 baseline
- Fractional Kelly (unstable)
- Score-weighted sizing (IC unvalidated)
- Pyramid add-ons (no evidence)
- Fixed profit targets
- Three-state/graduated exposure (muddies attribution)

---

## Open Questions

1. CANSLIM rank IC on VN100 historically
2. VN100 limit-down frequency blocking 8% stop
3. Capacity at 100B VND AUM
4. MDM false-SELL frequency justifying Policy B/C

---

## Sources

- Faber — Quantitative Approach to Tactical Asset Allocation (SSRN)
- Antonacci — Dual Momentum Investing
- Newfound — Fragility Case Study: Dual Momentum GEM (2019)
- DeMiguel, Garlappi, Uppal (2009, RFS) — Optimal Versus Naive Diversification
- Kaminski & Lo (2014, JFM) — When Do Stop-Loss Rules Stop Losses?
- Hurst, Ooi, Pedersen (2017) — A Century of Evidence on Trend Following
- AAII — Revisiting CAN SLIM
- Papertoprofit — 87 Stop Loss Strategies Tested
- PLOS One — Vietnam tick size, trade execution costs
- QuantifiedStrategies — Survivorship Bias
