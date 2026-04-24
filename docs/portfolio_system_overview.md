# Tổng quan hệ thống danh mục MDM+VN100

> Mô tả toàn bộ logic, tham số, và cơ chế của hệ thống từ tín hiệu MDM đến quản lý danh mục.  
> Áp dụng cho: **v7.0 (CANSLIM+MDM)** và **v8.0 (RS Momentum+MDM)**  
> Cập nhật: 2026-04-13

---

## Sơ đồ luồng tổng quan

```
VN-Index OHLCV
      │
      ▼
[1. MDM HybridEngine]
  → State: BUY / CASH / SELL (per ngày)
      │
      ├─ SELL → Thanh lý một phần (giữ top 50% RS)
      │
      └─ BUY  → Mở cửa sổ 20 ngày nhận tín hiệu entry
                    │
VN100 OHLCV panel ─┤
Fundamental / RS   │
                   ▼
         [2. Stock Scorer]
           CANSLIM (v7.0) hoặc RS Momentum (v8.0)
           → score = 100 nếu pass, NaN nếu fail
                   │
                   ▼
         [3. Entry Engine]
           Option A: 52-week high breakout
           Option C: Pocket Pivot
           → Danh sách Fill objects (ticker, fill_date, fill_price)
                   │
                   ▼
         [4. Portfolio Engine]
           Quản lý tối đa 8 slot, 12.5% NAV mỗi slot
           Stop loss, cooldown, T+2, thanh khoản, giá trần/sàn
                   │
                   ▼
         [5. Kết quả]
           trades, NAV daily, positions daily, metrics
```

---

## Phần 1 — MDM HybridEngine (Tín hiệu thị trường)

### Mục đích

Phân loại trạng thái thị trường VN-Index thành 3 trạng thái:
- **BUY** — thị trường tăng, mở entry
- **CASH** — thị trường không rõ ràng, không mở mới, giữ cũ
- **SELL** — thị trường giảm, thanh lý một phần danh mục

### Config: `MDMV2Config` (VN30 preset)

**Correction / FTD parameters:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `correction_threshold` | -6% | Điều chỉnh ≥ 6% kích hoạt theo dõi rally attempt |
| `ftd_min_rally_day` | ngày 3+ | FTD chỉ hợp lệ từ ngày thứ 3 trở đi |
| `ftd_max_rally_day` | ngày 12 | FTD hết hạn sau ngày 12 |
| `ftd_min_price_gain` | +1% | Gain tối thiểu cho FTD |

**Distribution Day (DD) parameters:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `dd_window_size` | 20 ngày | Cửa sổ đếm DD |
| `dd_price_drop_threshold` | -0.2% | Close giảm ≥ 0.2% so với hôm trước = DD |
| `dd_price_stall_threshold` | +0.1% | Close tăng < 0.1% và ở vùng thấp = stall DD |
| `dd_stall_p_loc_threshold` | 20% | Price location < 20% = vùng thấp trong ngày |

**Chuyển trạng thái:**

| Transition | Điều kiện |
|-----------|-----------|
| BUY → CASH | 5 DD trong 20 ngày **hoặc** close < MA10 liên tiếp 3 ngày |
| CASH → SELL | Tự động sau 20 ngày trong CASH (cash_deterioration) |
| CASH → BUY | FTD signal, MA50 breakout, hoặc 52-week high |
| SELL → BUY | FTD signal (phục hồi) |

> **Fail-safe:** Khi đang SELL, nếu VN-Index đóng cửa vượt đỉnh của thanh SELL cũ (standby-sell HIGH) → tự động chuyển về CASH. Giảm tín hiệu giả.

**MDM stop loss (cho VN-Index signal engine, không phải stock level):**

| Tham số | Giá trị |
|---------|---------|
| `stop_loss_pct` | 1.5% |
| `atr_period` | 14 ngày |
| `fail_safe_enabled` | True |

---

## Phần 2 — Entry Detection (Tín hiệu vào lệnh cổ phiếu)

### Cửa sổ MDM BUY Window

```
Bắt đầu: Bar đầu tiên sau khi chuyển sang BUY (inclusive)
Kết thúc: Bar thứ 20 (window_days = 20)

Nếu series bắt đầu đã ở trạng thái BUY (không có chuyển đổi prior) → KHÔNG mở cửa sổ (fail-closed).
Tín hiệu nằm ngoài cửa sổ bị loại bỏ.
```

### Option A — 52-Week High Breakout

**Điều kiện (ALL phải đúng):**

```
1. close[t] > max(close[t-252 .. t-1])     — vượt đỉnh 52 tuần
2. volume[t] >= 1.5 × mean(volume[t-50..t-1])  — khối lượng đột biến ≥ 1.5× TB 50 ngày
3. close[t] > open[t]                       — nến tăng
4. close[t] >= (high[t] + low[t]) / 2      — đóng ở nửa trên của nến
```

**Entry fill:** `open[t+1]` (sáng hôm sau)

### Option C — Pocket Pivot

**Điều kiện (ALL phải đúng):**

```
1. close[t] > open[t]                       — nến tăng
2. close[t] >= MA50[t]                      — đóng trên MA50
3. volume[t] > max(down_day_vol[t-10..t-1]) — vượt khối lượng ngày giảm cao nhất trong 10 ngày
   (Nếu không có ngày giảm nào trong 10 ngày → TÍN HIỆU BỊ LOẠI, fail-closed)
4. close[t] >= (1 - 0.15) × max(high[t-50..t-1])  — trong vòng 15% đỉnh 50 ngày (near-base)
```

**Entry fill:** `open[t+1]`

### Deduplication

```
Cùng (ticker, window_id, detector):
  → Giữ tín hiệu sớm nhất (fill_date nhỏ nhất)

A và C là hai luồng độc lập:
  → Cùng ticker có thể có cả A và C trong một cửa sổ

Union mode: dùng cả A và C, sau đó dedup theo quy tắc trên
```

---

## Phần 3 — Stock Scoring (Lọc cổ phiếu)

### A. CANSLIM Scorer (v7.0)

Config: `CanslimConfig`

| Rule | Tham số | Ngưỡng | Dữ liệu |
|------|---------|--------|---------|
| **C** — Current EPS | `c_threshold` | EPS YoY ≥ 20% | MySQL fundamentals |
| **A** — Annual EPS | `a_threshold` | CAGR 3 năm ≥ 15% | MySQL fundamentals |
| **N** — Near high | `n_within_high` | Trong vòng 15% đỉnh 252 ngày | Giá |
| **S** — Volume | `s_vol_mult` | Volume ≥ 1.5× TB 50 ngày | Khối lượng |
| **L** — RS Rating | `l_rs_threshold` | RS ≥ 80 (top 20%) | Giá (cross-sectional) |

**RS Formula (CANSLIM):**
```
rs_raw = 0.4 × ROC(63) + 0.2 × ROC(126) + 0.2 × ROC(189) + 0.2 × ROC(252)
rs_rating = cross-sectional percentile rank trong VN100 [0, 100]
```

**Scoring:**
```
score = 100.0  nếu C AND A AND N AND S đều pass
score = NaN    nếu bất kỳ rule nào fail → cổ phiếu bị loại
```

> Lưu ý: Rule **L** (RS ≥ 80) hiện không áp dụng ở scorer level — được kiểm tra ở portfolio level qua `rs_streak_days`.

### B. RS Momentum Scorer (v8.0)

Config: `MomentumScorerConfig`

| Rule | Tham số | Ngưỡng | Dữ liệu |
|------|---------|--------|---------|
| **RS** | `rs_threshold` | RS ≥ 70 (top 30%) | Giá (cross-sectional) |
| **N** — Near high | `n_within_high` | Trong vòng 15% đỉnh 252 ngày | Giá |

**RS Formula options:**

| Formula | Công thức | Kết quả in-sample |
|---------|-----------|-----------------|
| `weighted_roc` | 0.4×ROC63 + 0.2×ROC126 + 0.2×ROC189 + 0.2×ROC252 | Sharpe=0.576 |
| `roc126` ✓ | ROC(126) = close/close.shift(126) - 1 | **Sharpe=0.702** (winner) |

**Scoring:**
```
score = 100.0  nếu rs_rating >= 70 AND n_prox <= 0.15
score = NaN    nếu bất kỳ rule nào fail
```

> v8.0 không cần MySQL, không cần dữ liệu fundamental. Hoàn toàn từ giá.

---

## Phần 4 — Portfolio Engine (Quản lý danh mục)

### Config: `PortfolioConfig`

#### Slot Management

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `max_slots` | 8 | Số vị thế tối đa đồng thời |
| `slot_weight` | 0.125 (12.5%) | Tỷ trọng mỗi vị thế = 1/8 NAV hôm trước |
| `lot_size` | 100 | Làm tròn xuống bội số 100 cổ phiếu |
| `max_buys_per_ticker` | 2 | Tối đa 2 lần mua cùng một mã |
| `max_ticker_weight` | 30% | Tổng tỷ trọng 1 mã ≤ 30% NAV |

#### Sizing Formula

```
target_notional = NAV[t-1] × 0.125

raw_shares = target_notional / fill_price
shares = floor(raw_shares / 100) × 100   ← làm tròn lot 100

NAV[t-1] là NAV đóng cửa ngày hôm trước — KHÔNG dùng giá hôm nay (tránh lookahead)
```

#### Cost Model

| Loại phí | Tham số | Giá trị | Tổng |
|---------|---------|---------|------|
| **Mua** — Commission | `entry_commission` | 0.25% | |
| **Mua** — Slippage | `entry_slippage` | 0.10% | **0.35%** |
| **Bán** — Commission | `exit_commission` | 0.25% | |
| **Bán** — Thuế | `exit_tax` | 0.10% | |
| **Bán** — Slippage | `exit_slippage` | 0.10% | **0.45%** |

```
cash_debit  = notional × (1 + 0.0025 + 0.0010)
net_proceeds = gross   × (1 - 0.0025 - 0.0010 - 0.0010)
```

#### Thanh khoản (ADV20 Gate)

```
adv20[t] = mean(close × volume, t-20..t-1)   ← shift(1), không dùng bar hiện tại

Điều kiện qua gate: adv20 >= 10.0 × target_notional

Nếu fail → từ chối lệnh (không ghi nhận unfilled, lặng lẽ bỏ qua)
```

#### Vietnam Microstructure

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `ceiling_pct` | 7% | Giá trần = prev_close × 1.07 |
| `floor_pct` | 7% | Giá sàn = prev_close × 0.93 |
| `t_plus` | 2 | T+2.5 settlement |
| earliest_sell | buy_bar + 3 | Sớm nhất có thể bán = T+3 |

**Ceiling-lock:** Nếu `open == high == low == ceiling` → thanh bị kẹp trần → hoãn entry sang bar tiếp theo.

**Floor-lock:** Nếu `open == high == low == floor` → thanh bị kẹp sàn → hoãn exit, tái kiểm tra bar tiếp theo.

#### Cooldown

```
Sau khi thoát lệnh (hard_stop / ma50_break / rs_deterioration):
  earliest_re_entry = exit_bar + cooldown_days + 1
                    = exit_bar + 6 (với cooldown_days=5)

Lệnh thoát do mdm_sell: KHÔNG đăng ký cooldown (có thể vào lại ngay)
```

---

## Phần 5 — Exit Logic (Thoát lệnh)

### Thứ tự ưu tiên (first-match-wins)

```
1. T+2 Block          → bar_idx < buy_bar + 3 → KHÔNG thoát (silent pass)
2. Hard Stop          → low[t] <= buy_price × (1 - 0.08)
3. MA50 Breakdown     → close[t] < MA50[t] AND volume[t] >= 1.25 × vol20_avg[t]
4. RS Deterioration   → rs_rating < threshold liên tiếp 5 ngày (rs_streak_days=5)
                        NaN → reset streak về 0 (fail-closed)
5. MDM SELL gate      → xem phần dưới
```

**Fill thoát lệnh:** `open[bar_idx + 1]` (sáng ngày hôm sau)

### MDM SELL — Partial Liquidation

```
Khi MDM chuyển sang SELL:
  1. Lấy danh sách tất cả vị thế mở (có thể bán được, đã qua T+2)
  2. Xếp hạng theo RS (giảm dần)
  3. Giữ lại top 50%: N_keep = ceil(n_eligible × 0.5)
  4. Thanh lý phần còn lại: exit_reason = "mdm_sell"
  5. Không đăng ký cooldown cho các lệnh này
  6. Các bar SELL tiếp theo: không thanh lý lại (prevent re-liquidation)

Ví dụ: 6 vị thế → giữ 3 (top RS), thanh lý 3
```

---

## Phần 6 — Invariants & Design Principles

### SC8: NAV Lookback Invariant (chống lookahead bias)

```
NAV[t] được tính TRƯỚC khi thực hiện quyết định tại bar t.
Tất cả sizing dùng NAV[t-1].
Không có giá tương lai nào được dùng cho quyết định hiện tại.
```

### Fail-Closed Defaults (mặc định từ chối khi không đủ dữ liệu)

| Tình huống | Hành vi |
|-----------|---------|
| Option C: không có ngày giảm trong 10 ngày | Reject tín hiệu |
| RS streak: giá trị NaN | Reset streak về 0 |
| CANSLIM/Momentum: NaN trong bất kỳ rule | score = NaN → loại cổ phiếu |
| ADV20: lịch sử < 20 ngày | NaN → fail liquidity gate |
| Entry: nằm ngoài BUY window | Reject |

---

## Phần 7 — Kết quả Backtest (OOS 2019-2025)

### So sánh v7.0 vs v8.0

| Metric | v7.0 CANSLIM+MDM | v8.0 RS+MDM (roc126) | VN-Index B&H |
|--------|:----------------:|:--------------------:|:------------:|
| CAGR | **10.18%** | 10.03% | 10.42% |
| **Sharpe_rf3** | **0.813** | 0.645 | 0.383 |
| MaxDD | **-16.3%** | -24.9% | -40.3% |
| Win Rate | 30.5% | 40.2% | — |
| Số lệnh | 59 | 92 | — |
| Avg Hold | 41 ngày | 44 ngày | — |
| Cost Drag | ~3-5% | **18.96%** | — |

### In-sample config (Phase 32/37, 2016-2018)

**v7.0 sweep winner:**

| Tham số | Giá trị |
|---------|---------|
| `c_yoy_threshold` | 0.25 |
| `slots` | 5 |
| `entry_option` | C (Pocket Pivot) |
| `sell_retain_pct` | 0.5 |

**v8.0 sweep winner:**

| Tham số | Giá trị |
|---------|---------|
| `rs_formula` | roc126 |
| `rs_threshold` | 70.0 |
| `n_within_high` | 0.10 |
| `hard_stop` | 0.08 |
| `slots` | 5 |
| `entry_option` | A (52-week breakout) |

---

## Phần 8 — File Reference

### Config files

| File | Class | Dùng cho |
|------|-------|---------|
| `strategies/portfolio/config.py` | `PortfolioConfig` | Toàn bộ portfolio engine |
| `strategies/entry/config.py` | `EntryConfig` | Option A / Option C |
| `strategies/canslim/config.py` | `CanslimConfig` | CANSLIM scorer (v7.0) |
| `strategies/momentum/scorer_config.py` | `MomentumScorerConfig` | RS scorer (v8.0) |
| `strategies/mdm_hybrid/config.py` | `HybridConfig`, `MDMV2Config` | MDM engine |

### Engine files

| File | Class | Vai trò |
|------|-------|---------|
| `strategies/portfolio/engine.py` | `PortfolioEngine` | Orchestrator chính |
| `strategies/entry/engine.py` | `EntryEngine` | Sinh tín hiệu entry |
| `strategies/mdm_hybrid/mdm_hybrid_engine.py` | `HybridEngine` | MDM state machine |

### Portfolio modules

| File | Nội dung |
|------|---------|
| `strategies/portfolio/state.py` | `Position`, `Trade`, `PositionBook` |
| `strategies/portfolio/exits.py` | Exit priority chain |
| `strategies/portfolio/sizing.py` | `target_notional`, lot rounding, ADV20 gate |
| `strategies/portfolio/costs.py` | `apply_entry_cost`, `apply_exit_cost` |
| `strategies/portfolio/microstructure.py` | Ceiling/floor lock, T+2 math |

### Entry modules

| File | Nội dung |
|------|---------|
| `strategies/entry/option_a.py` | 52-week breakout detector |
| `strategies/entry/option_c.py` | Pocket pivot detector |
| `strategies/entry/window.py` | BUY window logic |

### Pipeline

| File | Function | Dùng cho |
|------|----------|---------|
| `analysis/_vn100_pipeline.py` | `run_vn100_backtest()` | v7.0 CANSLIM backtest |
| `analysis/_vn100_pipeline.py` | `run_v8_backtest()` | v8.0 Momentum backtest |
| `analysis/sweep_vn100_v8.py` | `main()` | In-sample sweep v8.0 |
| `analysis/backtest_vn100_v8_oos.py` | `main()` | OOS validation v8.0 |

---

## Bảng tổng hợp tất cả tham số

| Tham số | Giá trị | Module |
|---------|---------|--------|
| **MDM Engine** | | |
| `correction_threshold` | -6% (VN30) | HybridEngine |
| `dd_cash_threshold` | 5 DD | HybridEngine |
| `ma10_cash_consecutive` | 3 ngày (VN30) | HybridEngine |
| `cash_deterioration_days` | 20 ngày (VN30) | HybridEngine |
| `stop_loss_pct` | 1.5% | HybridEngine |
| `fail_safe_enabled` | True | HybridEngine |
| **Entry** | | |
| Option A: `high_lookback` | 252 ngày | EntryEngine |
| Option A: `vol_mult` | 1.5× | EntryEngine |
| Option C: `ma_length` | 50 ngày | EntryEngine |
| Option C: `pocket_lookback` | 10 ngày | EntryEngine |
| Option C: `base_tolerance` | 15% | EntryEngine |
| `window_days` | 20 ngày | EntryEngine |
| **CANSLIM (v7.0)** | | |
| `c_threshold` (EPS YoY) | 20% | CanslimConfig |
| `a_threshold` (EPS CAGR) | 15% | CanslimConfig |
| `n_within_high` | 15% | CanslimConfig |
| `s_vol_mult` | 1.5× | CanslimConfig |
| `l_rs_threshold` | 80 | CanslimConfig |
| **RS Momentum (v8.0)** | | |
| `rs_threshold` | 70 | MomentumScorerConfig |
| `n_within_high` | 15% | MomentumScorerConfig |
| `rs_formula` | roc126 | `run_v8_backtest()` |
| **Portfolio** | | |
| `max_slots` | 8 | PortfolioConfig |
| `slot_weight` | 12.5% | PortfolioConfig |
| `lot_size` | 100 cổ phiếu | PortfolioConfig |
| `max_buys_per_ticker` | 2 | PortfolioConfig |
| `max_ticker_weight` | 30% | PortfolioConfig |
| `hard_stop_pct` | 8% | PortfolioConfig |
| `rs_streak_days` | 5 ngày | PortfolioConfig |
| `ma50_vol_mult` | 1.25× | PortfolioConfig |
| `cooldown_days` | 5 ngày | PortfolioConfig |
| `t_plus` | 2 (T+2.5) | PortfolioConfig |
| `sell_retain_pct` | 50% | PortfolioConfig |
| `adv_mult` | 10× | PortfolioConfig |
| `ceiling_pct` | 7% | PortfolioConfig |
| `floor_pct` | 7% | PortfolioConfig |
| **Costs** | | |
| Entry total | 0.35% | PortfolioConfig |
| Exit total | 0.45% | PortfolioConfig |
