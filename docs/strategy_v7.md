# Chiến lược v7.0 — CANSLIM + MDM Gate + RS Partial Liquidation

**Trạng thái:** Best model hiện tại (2026-04-15). Shipped 2026-04-10 sau Phase 999.1.
**Phạm vi:** Long-only, đa cổ phiếu, VN100, timeframe daily.
**Kết quả OOS (2019-01-02 → 2025-12-31):** NAV 1.0B → 1.971B (+97.1%), CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31%.

> Tài liệu này là **mô tả tổng thể** cho người đọc mới. Spec chi tiết từng module vẫn ở [rules_canslim_mdm.md](rules_canslim_mdm.md) (cần cập nhật Phase 999.1) và [rules_mdm_hybrid.md](rules_mdm_hybrid.md) Section XV.

---

## 1. Ý tưởng cốt lõi

v7.0 tách bạch **2 quyết định độc lập**:

1. **Chọn cổ phiếu gì** → CANSLIM scorer (fundamental-driven, chọn công ty tăng trưởng mạnh gần đỉnh 52w)
2. **Lúc nào được mua / cắt bớt** → MDM gate (market-timing, BUY/CASH/SELL cho cả thị trường)

Hai lớp này combine qua một **portfolio engine** quản lý tối đa 5 vị thế song song với risk management chặt (6% hard stop + MA50 trailing + T+2).

---

## 2. Universe — VN100

- 100 mã thanh khoản cao nhất HOSE theo rebalance bán niên.
- Loader: [connectors/postgres.py](../connectors/postgres.py) (OHLCV TA) + MySQL (fundamentals).
- Mode production: `current-vn100` (static 100 mã snapshot cuối kỳ, tránh survivorship bias bằng cách kiểm tra ADV20 thanh khoản từng bar).

---

## 3. Chọn cổ phiếu — CANSLIM Scorer

Module: [strategies/canslim/](../strategies/canslim/)

Tính 7 thành phần C-A-N-S-L-I-M, chuẩn hoá thành điểm 0-100. Phase 29 validated OOS rho=0.365 vs baseline `diem_canslim` của team bên ngoài.

**Locked thresholds (rank-1 từ Phase 32 sweep 2014-2018):**

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `c_yoy` | 0.25 | EPS quý YoY ≥ 25% |
| `a_cagr` | 0.20 | EPS 3-năm CAGR ≥ 20% |
| `n_prox` | 0.10 | Giá trong vòng 10% đỉnh 252-day |
| `slots` | 5 | Tối đa 5 vị thế đồng thời |
| `slot_weight` | 0.20 | Mỗi vị thế = 20% NAV |

Ứng viên vào rổ = mã pass cả 3 ngưỡng C/A/N. Điểm tổng CANSLIM dùng để **tie-break** khi số ứng viên > free slots.

---

## 4. Xác nhận vào lệnh — Entry Primitives

Module: [strategies/entry/](../strategies/entry/)

Cần **BOTH** điều kiện kỹ thuật thoả mãn mới emit fill:

- **Option A — Pivot breakout:** giá phá base/đỉnh pivot với volume surge.
- **Option C — Pocket Pivot:** up-day với volume > max down-volume trong 10 ngày trước.

Entry feed = **A ∪ C union** (dedupe per `(ticker, window_id)`, ưu tiên A nếu trùng fill_date). Locked config dùng `entry=C` (Pocket Pivot) cho rank-1.

---

## 5. MDM Gate — Capital Allocation Policy A

Module: [strategies/mdm_hybrid/](../strategies/mdm_hybrid/) (HybridEngine + fail-safe v6.0)

MDM phát tín hiệu thị trường `{BUY, CASH, SELL}` cho từng bar dựa trên FTD/DD + QE floor + banding + fail-safe standby-sell HIGH:

| MDM state | Hành vi portfolio |
|---|---|
| **BUY** | Được mở vị thế mới (nếu free_slots > 0). Vị thế cũ giữ nguyên, chạy exit chains bình thường. |
| **CASH** | **Không** mở vị thế mới (ứng viên log vào unfilled.csv `reason=gate_cash`). Vị thế cũ giữ nguyên. |
| **SELL** | **Partial liquidation** — xem Mục 6. |

**Quan trọng:** MDM gate KHÔNG override các exit signal cá nhân (hard stop, MA50 break). Nó chỉ điều phối capital allocation ở cấp thị trường.

---

## 6. Partial Liquidation trên MDM SELL (Phase 999.1 — the game-changer)

**Đây là thay đổi cốt lõi đưa Sharpe từ 0.448 → 0.813.**

Trước 999.1: MDM SELL = liquidate toàn bộ → cắt cả winner khoẻ khi noise SELL ngắn ngày.

Sau 999.1: Khi gate chuyển SELL, rank các vị thế hiện có theo **RS (Relative Strength)** → đóng 50% yếu nhất, **giữ lại 50% mạnh nhất**.

**Pseudo-code** ([strategies/portfolio/engine.py:446-483](../strategies/portfolio/engine.py#L446-L483)):

```python
eligible = open_positions_not_scheduled_for_exit()
ranked = sorted(eligible, key=rs_at(ticker, date), reverse=True)  # NaN = -inf
n_keep = math.ceil(len(eligible) * cfg.sell_retain_pct)  # default 0.5
to_close = ranked[n_keep:]   # bottom 50% → exit next open với reason=mdm_sell
retained = ranked[:n_keep]   # top 50% → tiếp tục chạy exit chains cá nhân
```

**Tham số:** `sell_retain_pct = 0.5` (configurable, validated `0 < x ≤ 1`).

**MDM SELL là exit reason DUY NHẤT không register cooldown** → cho phép tái entry ngay khi gate trở lại BUY.

---

## 7. Exit Chain — First-Match-Wins

Module: [strategies/portfolio/exits.py](../strategies/portfolio/exits.py)

Thứ tự ưu tiên trên mỗi bar (sau T+2):

1. **T+2 block:** `bar_idx < buy_bar + 3` → không exit nào fire được.
2. **MDM SELL** (partial, section 3 của engine — KHÔNG ở exits.py để tránh duplicate dispatch bug, fix commit `d218ce3`).
3. **Hard stop 6%:** `close ≤ cost_basis × 0.94`. Nếu bar floor-locked (`open=high=low=floor`) → defer sang bar kế.
4. **MA50 break:** close xuyên MA50 (có optional volume confirmation).
5. **RS streak:** N bar liên tiếp RS < ngưỡng; **fail-closed on NaN** (bất kỳ NaN nào reset streak = 0).

Exit execution: next-bar open, trừ trường hợp floor-locked.

---

## 8. Cost Model

[strategies/portfolio/costs.py](../strategies/portfolio/costs.py)

| Loại | Rate | Áp dụng |
|---|---|---|
| Entry commission + slippage | 0.35% | `notional × (1 + 0.0035)` |
| Exit haircut | 0.45% | `gross × (1 - 0.0045)` |
| Cost basis | fill × 1.0035 | Dùng cho hard-stop reference |

**Total cost drag OOS:** 9.64% trong 7 năm (turnover 7.39x).

---

## 9. Cơ chế đặc thù Việt Nam

- **T+2.5 settlement** (D-17): `earliest_sell_bar = buy_bar + 3`.
- **Biên độ ±7% HOSE** (D-18): ceiling = `prev_close × 1.07`, floor = `× 0.93`.
  - Ceiling-locked bar: chặn entry (log `reason=ceiling_lock`).
  - Floor-locked bar: defer hard-stop exit.
- **Lot 100**: `shares = floor(target_notional / fill_price / 100) × 100`.
- **Liquidity gate ADV20** (D-24): `target_notional ≤ adv_mult × ADV20` (20-bar mean `close × volume` strict trước bar, NaN fail-closed).

---

## 10. NAV Discipline — SC8 `state[i-1]` Rule

**Non-negotiable invariant** (ref: [memory/feedback_equity_formula.md](../../../.claude/projects/c--Users-trant-projects-mdm/memory/feedback_equity_formula.md)):

Mọi quyết định sizing ở bar `t` CHỈ dùng NAV + ADV20 tính từ bars **strict trước t**. Engine compute `nav_prev = _compute_nav(bar_idx - 1)` TRƯỚC khi materialize entry bar-t; ADV20 series shift bằng 1.

Đây là class bug đã từng sinh ra divergence 707% vs 93% — guard bởi `test_nav_lookback.py::test_no_bar_t_lookahead`.

---

## 11. Hiệu suất OOS 2019-2025

Audit artifacts: [docs/audits/phase33/](audits/phase33/)

| Chỉ số | v7.0 (sau 999.1) | CANSLIM-only baseline | VN-Index B&H |
|---|---|---|---|
| **Total return** | **+97.1%** | cao hơn nhưng volatile | ~+60% |
| **CAGR** | 10.18% | ~12% | ~7% |
| **Sharpe (rf=3%)** | 0.813 | 1.047 | ~0.3 |
| **MaxDD** | **-16.31%** | ~-40% | ~-35% |
| **MaxDD duration** | 938 ngày | longer | ~900d |
| **Hit rate** | 30.5% | higher | n/a |
| **Profit factor** | 3.74 | — | — |
| **Trades** | 59 | ~80 | 1 |
| **Avg hold** | 41.3 ngày | — | — |
| **Turnover** | 7.39x | higher | 0 |

**Đánh giá:**
- ✓ MaxDD giảm **~2.5x** so với B&H và baseline — MDM gate là **drawdown controller** tuyệt vời.
- ✗ Sharpe 0.813 < CANSLIM-only 1.047 → MDM gate vẫn **cắn alpha** (nhưng không nhiều như trước 999.1).
- ✗ CAGR 10% khá thấp cho active strategy trên cận biên.
- ✗ MaxDD duration 938 ngày (~2.5 năm) là điểm yếu tâm lý lớn.
- ✗ Hit rate 30.5% + 59 trades → fragile, dựa vào vài big winners.

---

## 12. Known limitations

1. **MDM gate là bottleneck risk-adjusted.** Phase 33 đã chứng minh CANSLIM-only Sharpe cao hơn → câu hỏi: liệu có thể thay MDM bằng regime filter nhẹ hơn?
2. **v8.0 RS-momentum thử thay CANSLIM → thất bại** (Sharpe 0.645). Kết luận: alpha của v7.0 đến từ **fundamentals**, không phải TA-only.
3. **Survivorship bias tiềm ẩn** do dùng VN100 snapshot cuối kỳ, mitigate bằng ADV20 liquidity gate nhưng chưa hoàn toàn loại bỏ.
4. **Sample nhỏ** (59 trades / 7 năm) → p-value yếu. Cần validate thêm bằng Monte Carlo bootstrap.

---

## 13. Artifacts & Entry Points

- **Config locked:** [strategies/portfolio/config.py](../strategies/portfolio/config.py) (rank-1: `slots=5, c_yoy=0.25, a_cagr=0.20, n_prox=0.10, hard_stop=0.06, entry=C, sell_retain_pct=0.5`)
- **Engine:** [strategies/portfolio/engine.py](../strategies/portfolio/engine.py)
- **OOS runner:** [scripts/export_dashboard_data.py](../scripts/export_dashboard_data.py), `analysis/generate_v7_report.py`
- **Audit OOS:** [docs/audits/phase33/oos_metrics.json](audits/phase33/oos_metrics.json), [oos_nav.csv](audits/phase33/oos_nav.csv), [oos_trades.csv](audits/phase33/oos_trades.csv)
- **Phase verification:** [.planning/phases/999.1-fix-mdm-sell-reduce-slots/999.1-VERIFICATION.md](../.planning/phases/999.1-fix-mdm-sell-reduce-slots/999.1-VERIFICATION.md) (8/8 truths passed)

---

*Last updated: 2026-04-15 — post Phase 999.1, v8.0 RS-momentum ablation shipped and trailing.*
