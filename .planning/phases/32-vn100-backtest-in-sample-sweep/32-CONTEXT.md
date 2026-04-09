# Phase 32: VN100 Backtest + In-Sample Sweep - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Ráp pipeline end-to-end: universe (Phase 29) → CANSLIM scorer (Phase 29) → entry detectors (Phase 30) → portfolio engine (Phase 31) → costs, chạy single-run backtest trên VN100 giai đoạn **2014-2018**, rồi chạy parameter sweep 1,536 configs và chọn top-3 theo Sharpe làm locked params cho Phase 33. Không có OOS, không có sensitivity 3-universe (Phase 33), không có dashboard (Phase 34).

</domain>

<decisions>
## Implementation Decisions

### Universe Mode (in-sample)
- **D-01:** Lock universe = **current-VN100** (Phase 29 mode `current`). User chọn đơn giản, chấp nhận survivorship bias cho in-sample. Sensitivity qua liquidity-reconstructed và VN30-only là scope Phase 33 (UNIV-03, BT-04).
- **D-02:** Semi-annual rebalance Jan/Jul theo Phase 29 UNIV-02 — giữ nguyên, không override.

### Sweep Grid (theo ROADMAP §Phase 32 SC2)
- **D-03:** Grid chính xác theo roadmap, không thêm chiều mới:
  - `c_yoy ∈ {0.10, 0.15, 0.20, 0.25}`
  - `a_cagr ∈ {0.10, 0.15, 0.20, 0.25}`
  - `n_proximity ∈ {0.05, 0.10, 0.15, 0.20}`
  - `hard_stop ∈ {0.06, 0.07, 0.08, 0.10}`
  - `slots ∈ {5, 8, 10}`
  - `entry_option ∈ {A, C}` — bám đúng roadmap, KHÔNG sweep `union` mặc dù Phase 31 D-05 hỗ trợ.
  - **Total = 4×4×4×4×3×2 = 1,536 configs**
- **D-04:** Các tham số KHÔNG sweep (lock theo Phase 31 defaults):
  - MDM gate = HybridEngine v6 (Phase 31 D-07)
  - Costs = 0.25% commission + 0.10% tax + 0.10% slippage (Phase 31 D-22)
  - Cooldown = 5 trading days (Phase 31 D-20/D-21)
  - Liquidity gate = ADV20 > 10× target (Phase 31 D-24)
  - Exit priority chain (Phase 31 D-13) — không sweep thứ tự
  - RS threshold = 70, 5 consecutive sessions (Phase 31 D-16)
  - MA50 trailing volume multiplier = 1.25× (Phase 31 D-13 item 3)

### Sweep Runtime Strategy
- **D-05:** **Partial precompute + multiprocessing**:
  1. Precompute 1 lần (cache vào memory hoặc parquet dưới `docs/audits/phase32/cache/`):
     - VN100 universe membership theo ngày (rebalance Jan/Jul)
     - Raw EPS/price/volume/foreign data cho toàn bộ universe 2014-2018
     - MDM gate state series (HybridEngine v6) trên VN-Index 2014-2018
     - Adjusted OHLC cho toàn bộ universe (qua `connectors/adjust.py`)
  2. Re-compute mỗi config:
     - CANSLIM score mask (vì c_yoy/a_cagr/n_proximity thay đổi)
     - Entry fills (vì entry_option thay đổi)
     - Portfolio engine run (vì slots/hard_stop thay đổi)
- **D-06:** Song song hoá bằng `multiprocessing.Pool` với `cpu_count() - 1` workers. Mỗi worker nhận 1 config, trả về metrics dict. Kết quả aggregate vào 1 DataFrame duy nhất.
- **D-07:** Progress bar bằng `tqdm` hoặc print mỗi 50 configs. Fail-loud: nếu 1 config crash, log ticker + config, tiếp tục các config khác (không abort toàn sweep). Tổng số config crash được report ở cuối.

### Single-Run vs Sweep Scripts
- **D-08:** Hai script riêng, mirror pattern `analysis/sweep_vn30_params.py`:
  - `analysis/backtest_vn100.py` — chạy 1 config duy nhất, default = Phase 31 defaults. Dùng để debug, in trade log dễ đọc, verify pipeline đúng trước khi sweep. Đây là SC1 của roadmap.
  - `analysis/sweep_vn100.py` — chạy full 1,536-config grid, output CSV + top-3 selection.
- **D-09:** Cả 2 script đặt period 2014-01-01 → 2018-12-31 hard-coded. Không cho override qua CLI args trong phase này (giữ reproducibility). Phase 33 sẽ tạo script riêng cho 2019-2025.

### Sharpe Definition & Top-3 Selection
- **D-10:** Sharpe dùng **rf = 3%** (annualized, VN 10Y govt) nhất quán với Phase 34 BT-05. Sharpe = `(annualized_return - 0.03) / annualized_vol`. Annualized vol dùng daily returns × √252.
- **D-11:** Top-3 selection: sort sweep results theo Sharpe giảm dần, lấy 3 rows đầu. Không loại theo tiêu chí phụ (CAGR floor, MaxDD ceiling) — chỉ dùng Sharpe thuần để tránh chọn vòng vo.
- **D-12:** Tie-breaker nếu Sharpe bằng nhau: CAGR cao hơn thắng; nếu vẫn tie, MaxDD thấp hơn thắng.

### Sanity Gate (SC5)
- **D-13:** "Không config nào >300% CAGR" xử lý như **soft-flag**: ghi column `sanity_flag` trong sweep CSV (giá trị `OK` / `CAGR_TOO_HIGH`), vẫn chạy tiếp toàn sweep. Sau khi sweep xong, nếu có config nào flagged, print warning và yêu cầu user confirm trước khi chọn top-3. Nếu config trong top-3 bị flag → abort, require manual review (có thể là bug look-ahead chứ không phải hiệu quả thật).

### Locked Params Handoff (→ Phase 33)
- **D-14:** Output locked params dưới dạng **JSON** tại `docs/audits/phase32/locked_params_top3.json`:
  ```json
  {
    "selected_at": "2026-04-XX",
    "selection_metric": "sharpe_rf3",
    "period": "2014-01-01..2018-12-31",
    "universe": "current-VN100",
    "configs": [
      {"rank": 1, "c_yoy": 0.15, "a_cagr": 0.10, ...metrics: {...}},
      {"rank": 2, ...},
      {"rank": 3, ...}
    ]
  }
  ```
- **D-15:** Phase 33 sẽ có 1 helper nhỏ load JSON này và rebuild PortfolioConfig + CanslimConfig — helper đó thuộc scope Phase 33, không Phase 32.

### Output Artifacts
- **D-16:** Tất cả output dưới `docs/audits/phase32/`, theo convention Phase 28/29/30/31:
  - `docs/audits/phase32-backtest-sweep.md` — report chính: methodology, single-run summary, sweep summary, top-3 table, sanity check results, notes
  - `docs/audits/phase32/single_run_nav.csv` — daily NAV của single-run baseline (SC1)
  - `docs/audits/phase32/single_run_trades.csv` — trade log single-run
  - `docs/audits/phase32/single_run_positions.csv` — position log single-run
  - `docs/audits/phase32/sweep_results.csv` — toàn bộ 1,536 rows với tất cả metrics + sanity_flag
  - `docs/audits/phase32/locked_params_top3.json` — D-14
  - `docs/audits/phase32/cache/` — parquet cache cho precompute (gitignore nếu dung lượng lớn)
- **D-17:** Metrics per config trong sweep_results.csv: `CAGR, Sharpe_rf3, MaxDD, MaxDD_duration_days, hit_rate, turnover, total_cost_drag_pct, num_trades, avg_hold_days, sanity_flag`

### Claude's Discretion
- Cache format (parquet vs pickle vs hdf5) và cache invalidation strategy
- Chunksize cho multiprocessing Pool
- Exact logging format cho crashed configs
- Có dùng `joblib.Memory` cho precompute hay tự viết
- Layout của report markdown (charts vs tables)
- Whether to include equity curve PNG cho top-3 trong report
- Progress bar thư viện (tqdm vs manual print)

### Folded Todos
None — không có todo nào match Phase 32 scope lúc gather context.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- `.planning/ROADMAP.md` §Phase 32 — Goal, SC1–SC5, sweep grid chính xác
- `.planning/REQUIREMENTS.md` BT-01, BT-02 — Backtest engine wiring + in-sample sweep

### Upstream Phase 31 (engine đã lock, tiêu thụ trực tiếp)
- `.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md` — Toàn bộ decisions D-01..D-28 đã khoá, Phase 32 KHÔNG sửa
- `strategies/portfolio/engine.py` — PortfolioEngine entry point
- `strategies/portfolio/config.py` — PortfolioConfig dataclass (sweep chỉ đổi hard_stop + slots + entry_mode)
- `strategies/portfolio/ab_report.py` — CSV writers cho trade/position/NAV

### Upstream Phase 30 (entry detectors)
- `.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md` — Entry window + fill model
- `strategies/entry/` — EntryEngine; sweep đổi `entry_option ∈ {A, C}`
- `docs/rules_entry.md` — Công thức Option A / Option C

### Upstream Phase 29 (CANSLIM scorer + universe)
- `.planning/phases/29-vn100-universe-canslim-scorer/29-CONTEXT.md` — Scorer + universe loader semantics
- `strategies/canslim/` — Scorer package; sweep đổi `c_yoy`, `a_cagr`, `n_proximity` qua `CanslimConfig`
- `strategies/canslim/config.py` — `CanslimConfig` dataclass

### Upstream Phase 28 (data + connectors)
- `connectors/adjust.py::adjust_ohlc()` — Bắt buộc cho mọi price/volume read
- `connectors/postgres.py` — Load stock_eod, stock_foreign_eod, stock_rs (Phase 31 extension)
- `docs/audits/phase28-data-audit.md` — Known data gaps trên VN100 2014-2018

### MDM Gate Source
- `strategies/mdm_hybrid/mdm_hybrid_engine.py::HybridEngine` — VN30 MDM state series, v6 config (Phase 31 D-07)
- `docs/rules_mdm_hybrid.md` — BUY/CASH/SELL transition rules

### Prior sweep patterns (tham khảo)
- `analysis/sweep_vn30_params.py` — Pattern cho parameter sweep + metrics compute (tham khảo structure, không copy nguyên vì grid khác)

### Memory discipline
- **Equity formula rule** (`feedback_equity_formula.md`) — `state[i-1]` discipline đã enforce trong Phase 31 D-26; Phase 32 kế thừa
- **Best VN30 model** (`project_best_model.md`) — HybridEngine + best sweep config là MDM gate source đúng

### Rules docs to update per Code-Docs Sync Rule
- `docs/rules_canslim_mdm.md` — Phase 34 sẽ finalize. Phase 32 KHÔNG cần update (chỉ wire + sweep, không thay đổi logic).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `strategies/portfolio/` — đã có đầy đủ engine.py, config.py, exits.py, sizing.py, state.py, costs.py, microstructure.py, ab_report.py từ Phase 31. Phase 32 CHỈ wire và gọi, không sửa.
- `strategies/entry/` — EntryEngine produces Fill records, Phase 31 đã consume, Phase 32 tái sử dụng y nguyên
- `strategies/canslim/` — Scorer + `CanslimConfig` dataclass; sweep tạo config mới mỗi lần, call scorer.
- `strategies/mdm_hybrid/` — HybridEngine cho MDM gate, chạy 1 lần trên VN-Index.
- `connectors/postgres.py` + `connectors/adjust.py` — readers đã tồn tại.
- `analysis/sweep_vn30_params.py` — pattern cho grid sweep + metrics compute, có thể copy skeleton.

### Established Patterns
- **Markdown + CSV audit artifacts** dưới `docs/audits/phaseXX/` — Phase 28/29/30/31 precedent
- **Dataclass config, fail-loud validation** — Phase 29/30/31 precedent
- **Adjusted OHLC only** via `adjust_ohlc()` — zero raw price reads
- **`state[i-1]` discipline** — enforced ở Phase 31 engine, Phase 32 không đụng vào
- **Period hard-coded trong analysis scripts** — reproducibility, không dùng CLI args cho dates
- **Multiprocessing sweep** — chưa có precedent rõ trong repo, nhưng `sweep_vn30_params.py` là serial; Phase 32 sẽ là script đầu tiên dùng `multiprocessing.Pool`

### Integration Points
- **Inputs:**
  - VN100 universe membership → Phase 29 loader
  - EPS/fundamentals → postgres via Phase 28 connectors
  - Adjusted OHLC → `connectors/adjust.py`
  - MDM gate state → HybridEngine.run() trên VN-Index 2014-2018
- **Outputs:**
  - `docs/audits/phase32/` CSV + JSON + markdown report
  - `locked_params_top3.json` → Phase 33 consume

</code_context>

<specifics>
## Specific Ideas

- User chọn **current-VN100** cho in-sample "cho đơn giản", chấp nhận survivorship bias. Phase 33 sẽ bù bằng sensitivity qua liquidity-reconstructed + VN30-only.
- User không quan tâm các detail orchestration (runtime, format, script layout) — Claude tự quyết theo default. Chỉ cần deliverables chạy được.
- Sweep 1,536 configs là lớn — phải dùng multiprocessing, không serial.

</specifics>

<deferred>
## Deferred Ideas

- **OOS 2019-2025 + sensitivity 3-universe** — Phase 33 (BT-03, BT-04)
- **Liquidity-reconstructed universe cho in-sample** — cân nhắc rerun Phase 32 nếu Phase 33 sensitivity cho thấy survivorship bias làm méo top-3 nghiêm trọng. Hiện không in scope.
- **Sweep `entry_mode=union`** — Phase 31 D-05 hỗ trợ nhưng roadmap grid không có. Có thể thử post-hoc nếu top-3 yếu.
- **Cost sensitivity sweep** — Phase 33 scope (costs overridable per Phase 31 D-23)
- **Benchmark comparison + real (CPI-adjusted) CAGR** — Phase 34 (BT-06, BT-07)
- **Dashboard + `docs/rules_canslim_mdm.md`** — Phase 34

</deferred>

---

*Phase: 32-vn100-backtest-in-sample-sweep*
*Context gathered: 2026-04-09*
