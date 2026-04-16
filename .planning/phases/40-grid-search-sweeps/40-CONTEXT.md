# Phase 40: Grid Search Sweeps - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Chạy sequential in-sample grid search trên VN30 train window 2015-01-01..2021-12-31: (1) ATR sweep 36 runs over (k, N, m) với `atr_buffer_enabled=True` và `refined_dd_enabled=False`; (2) DD sweep 54 runs trên config ATR đã lock, với `refined_dd_enabled=True`; (3) selection script chọn max-Sharpe_rf3 subject to MaxDD ≤ -30%, tie-break CAGR → MaxDD. OOS window 2022-2026 hoàn toàn không đụng tới (runtime assert). A/B + walk-forward validation, dashboard, rules doc là scope Phase 41/42 — Phase 40 chỉ sản xuất 4 artifacts: `output/v9_atr_sweep.csv`, `output/v9_dd_sweep.csv`, `output/v9_atr_best.{txt,json}`, `output/v9_dd_best.{txt,json}`.

</domain>

<decisions>
## Implementation Decisions

### Script layout
- **D-01:** 3 scripts riêng dưới `analysis/`:
  - `analysis/sweep_v9_atr.py` — 36 runs ATR sweep → `output/v9_atr_sweep.csv`
  - `analysis/sweep_v9_dd.py` — đọc `output/v9_atr_best.json`, chạy 54 runs DD sweep trên locked ATR config → `output/v9_dd_sweep.csv`
  - `analysis/select_v9_best.py` — đọc cả 2 CSV, áp dụng constraint + tie-break, ghi `v9_atr_best.{txt,json}` + `v9_dd_best.{txt,json}`
- **D-02:** Mirror Phase 32 pattern (single-run + sweep separate), không gộp vào 1 script sequential. Lý do: debug dễ, re-run từng giai đoạn, fail trong giai đoạn 2 không phải re-run ATR.

### Baseline config cho sweep
- **D-03:** Sweep override trên `VN30_PRESET` (strategies/mdm_hybrid/config.py:129). Giữ nguyên fail_safe_enabled=True, ma50_sell_enabled=True, correction_threshold=-0.06, cash_deterioration_days=20, ma10_cash_consecutive=3, stop_loss_pct=0.015, volatility_adaptive=True. Chỉ flip ATR/DD params per stage.
- **D-04:** Dùng `dataclasses.replace(VN30_PRESET, atr_buffer_enabled=True, atr_buffer_k=k, atr_buffer_period=N, atr_buffer_consecutive_days=m, name=f"atr-k{k}-N{N}-m{m}")` cho mỗi config ATR. Tương tự cho DD stage với `refined_dd_*` fields.
- **D-05:** Trong ATR sweep (stage 1), `refined_dd_enabled=False` — dùng classic v6.0 DD rule (-0.2%). Cô lập 1 dimension biến tại thời điểm để attribute impact ATR buffer thuần túy.
- **D-06:** Trong DD sweep (stage 2), `atr_buffer_enabled=True` với (k, N, m) đã lock từ stage 1 + `refined_dd_enabled=True` với (large_drop, small_drop, small_vol_percentile) từ sweep grid.

### ATR sweep grid (Stage 1, SWEEP-01)
- **D-07:** Grid theo ROADMAP line 763 chính xác:
  - `atr_buffer_k ∈ {0.3, 0.5, 0.7, 1.0}` (4 values)
  - `atr_buffer_period ∈ {10, 14, 20}` (3 values)
  - `atr_buffer_consecutive_days ∈ {1, 2, 3}` (3 values)
  - **Total = 4 × 3 × 3 = 36 runs**

### DD sweep grid (Stage 2, SWEEP-02)
- **D-08:** Grid theo ROADMAP line 764 chính xác:
  - `refined_dd_large_drop ∈ {-0.005, -0.006, -0.007, -0.008, -0.009, -0.010}` (6 values, −0.5% đến −1.0%)
  - `refined_dd_small_drop ∈ {-0.003, -0.004, -0.005}` (3 values, −0.3% đến −0.5%)
  - `refined_dd_small_vol_percentile ∈ {3, 5, 10}` (3 values, top 3/5/10%)
  - Các field khác: `refined_dd_large_vol_rule='vol_ma20'` (fixed, MDMV2Config `__post_init__` hiện chỉ support value này), `refined_dd_small_vol_lookback=50` (fixed per Phase 39 D-06)
  - **Total = 6 × 3 × 3 = 54 runs**
  - **Validation guard:** `MDMV2Config.__post_init__` assert `large_drop ≤ small_drop` — grid đã thiết kế luôn thỏa (mọi large ≤ mọi small). Nhưng khi construct Config per cell, assertion có thể fire — Plan wiring phải ensure đúng thứ tự.

### Orchestration
- **D-09:** Serial với `tqdm` progress bar (Phase 32 precedent dùng multiprocessing cho 1,536 configs; Phase 40 chỉ 90 runs ~2-5 phút). Mỗi script: load data + build_indicator_dataframe 1 lần precompute, sau đó loop qua grid gọi `engine.run(df.copy())`.
- **D-10:** Fail-loud: nếu 1 config raise, log config name + traceback, record row với metrics=NaN + `error` column, tiếp tục. Cuối sweep raise SummaryError nếu có rows NaN trong top-5 (để tránh ghi best từ broken config).
- **D-11:** Per-script data load: `DataLoader('vn30').load(start_date='2015-01-01', end_date='2021-12-31')` → `build_indicator_dataframe(df)` → pass `df.copy()` vào engine.run. Indicator compute cho ATR/DD (add_violation_threshold_column, add_volume_ma_column, add_volume_percentile_column) vẫn xảy ra bên trong HybridEngine pipeline per Phase 38 D-07 / Phase 39 D-03 (precompute hook gated bởi feature flag).

### OOS leakage guard (SWEEP-04)
- **D-12:** Hard-code `TRAIN_START = '2015-01-01'`, `TRAIN_END = '2021-12-31'` ở top-level mỗi sweep script. Ngay sau DataLoader.load(), runtime assertion: `assert df['date'].max() <= pd.Timestamp(TRAIN_END), f"OOS leak: max date {df['date'].max()}"`. Không nhận CLI args override window (giữ reproducibility tuyệt đối).

### Handoff ATR → DD stage
- **D-13:** `sweep_v9_dd.py` đọc `output/v9_atr_best.json` (machine-readable sibling từ select_v9_best). Nếu file missing: raise FileNotFoundError với message "Run select_v9_best.py stage=atr trước" — ép user chạy đúng thứ tự. Load JSON → dict of (atr_buffer_k, atr_buffer_period, atr_buffer_consecutive_days) → gán vào config template cho DD sweep.
- **D-14:** `select_v9_best.py` có 2 mode `--stage atr` và `--stage dd` — chạy sau khi mỗi sweep CSV được tạo. Stage atr đọc v9_atr_sweep.csv → ghi v9_atr_best.{txt,json}. Stage dd đọc v9_dd_sweep.csv → ghi v9_dd_best.{txt,json}.

### Selection logic (SWEEP-03)
- **D-15:** Selection algorithm:
  1. Load sweep CSV
  2. Filter `MaxDD > -30%` (tức MaxDD ≥ -30%, vì MaxDD là số âm, "≤ -30%" trong spec có nghĩa drawdown nặng hơn -30%, ví dụ -35% BỊ LOẠI; -28% OK). **Interpret:** constraint = keep rows where `MaxDD >= -30` (less negative than -30).
  3. Nếu candidates rỗng → abort + RuntimeError + exit code 1 (per D-16).
  4. Sort by Sharpe_rf3 desc, tie CAGR desc, tie MaxDD desc (ít âm hơn thắng).
  5. Top row → ghi best files.
- **D-16:** Constraint fallback: **Abort + exit code 1 nếu empty**. Script không fallback về max-Sharpe unconstrained. Lý do: v6.0 baseline MaxDD -28.2% → realistic có config pass; nếu không, có thể grid sai hoặc data issue — user phải intervene thủ công, không block pipeline tự động.
- **D-17:** Tiebreak 3-tier: Sharpe_rf3 → CAGR → MaxDD (ít âm hơn thắng). Nếu cả 3 bằng nhau (cực hiếm) → config đầu tiên trong CSV (stable).

### CSV metrics schema (extended cho Phase 41)
- **D-18:** Mỗi row `v9_atr_sweep.csv` / `v9_dd_sweep.csv` chứa:
  - **Config fields**: tương ứng stage (atr: k/N/m; dd: large_drop/small_drop/small_vol_percentile + atr params đã lock làm metadata)
  - **Core metrics** (required by SWEEP-01/02): `sharpe_rf3`, `cagr_pct`, `max_dd_pct`, `transitions`
  - **Whipsaw diagnostic cho Phase 41 VAL-04**: `sell_count`, `ma50_breakdown_sell_share` (fraction of SELL signals from ma50_breakdown path), `buy_count`, `buy_pct` (time in BUY state), `cash_pct`, `sell_pct`
  - **Error tracking**: `error` column (empty nếu run thành công; traceback/message nếu fail per D-10)
- **D-19:** Sharpe_rf3 tính theo convention Phase 32 D-10: `(annualized_return - 0.03) / annualized_vol`, annualized_vol = daily_returns.std() × √252. Dùng cùng formula với `compute_metrics` trong `analysis/sweep_vn30_params.py`, extend thêm whipsaw columns.
- **D-20:** `ma50_breakdown_sell_share` cần read `signal_log` output từ HybridEngine.run() — kiểm tra xem `action` column có chứa chuỗi 'ma50_breakdown' (hoặc tương đương) cho mỗi CASH→SELL transition. Implementation detail thuộc Plan, nhưng signal log phải expose đủ info.

### Output format best files (SWEEP-03)
- **D-21:** Mỗi stage ghi CẢ 2 files:
  - `output/v9_atr_best.txt` — human-readable table (params + metrics, ascii formatted)
  - `output/v9_atr_best.json` — machine-readable dict `{params: {...}, metrics: {...}, selected_at: iso8601, train_window: "2015-01-01..2021-12-31"}`
  - Tương tự `v9_dd_best.{txt,json}`
- **D-22:** TXT đủ "chính danh" theo REQUIREMENTS SWEEP-03; JSON là convenience bonus cho Phase 41 load params dễ. Cost: duplicate info, minor.

### Claude's Discretion
- Exact column order trong CSV (config fields trước hay sau metrics)
- Tên chính xác các metric columns (snake_case giữ consistent với Phase 32)
- Cách parse `ma50_breakdown` từ action log của HybridEngine (có thể cần thêm label/action string khi Phase 38 trigger fire — scope Plan sẽ xác nhận)
- Format chi tiết TXT layout (ASCII table vs key-value)
- Whether to include equity curve PNG cho top-3 configs (Phase 32 D-style extra) — optional
- Log level (tqdm only vs per-config print vs silent)

### Folded Todos
None — init report empty matches cho Phase 40.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- `.planning/ROADMAP.md` §Phase 40 (lines 758-767) — Goal, 4 success criteria, exact grid cardinalities, output file paths
- `.planning/REQUIREMENTS.md` §Grid Search & Selection (SWEEP-01..04) — Params, file paths, OOS boundary

### Upstream Phase 38 (ATR Buffer module shipped)
- `.planning/phases/38-atr-buffer-zone-module/38-CONTEXT.md` — Toàn bộ D-01..D-13 đã khoá. Phase 40 KHÔNG sửa module, chỉ set flag + params.
- `strategies/mdm_hybrid/config.py` — `atr_buffer_enabled/_k/_period/_consecutive_days` fields (line 62-66) + VN30_PRESET (line 129)
- `strategies/mdm_hybrid/indicators.py` — `add_violation_threshold_column()` (precompute entry)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — pipeline hook
- `strategies/mdm_hybrid/position_manager.py:278` — trigger point (đã thay theo Phase 38)

### Upstream Phase 39 (Refined DD module shipped)
- `.planning/phases/39-refined-distribution-day-module/39-CONTEXT.md` — D-01..D-11 đã khoá
- `strategies/mdm_hybrid/config.py` — `refined_dd_*` fields (line 69-74), post_init assert (line 88-96)
- `strategies/mdm_hybrid/distribution_day.py` — `DistributionDayCounter` với dual-threshold branch
- `strategies/mdm_hybrid/indicators.py` — `add_volume_ma_column`, `add_volume_percentile_column`

### Upstream Phase 32 (sweep precedent pattern)
- `.planning/phases/32-vn100-backtest-in-sample-sweep/32-CONTEXT.md` — Sharpe_rf3 convention (D-10), tie-break pattern (D-12), CSV/JSON output layout (D-14, D-16, D-17), fail-loud precedent (D-07, D-13)
- `analysis/sweep_vn30_params.py` — Template cho serial sweep với HybridEngine + compute_metrics; Phase 40 scripts có thể mô phỏng skeleton (dataclasses.replace, loop, to_csv)
- `analysis/sweep_vn100.py` — Multi-processing reference (không dùng Phase 40 nhưng tham khảo metrics)

### Engine entry points (consume read-only)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py::HybridEngine` — main engine, gọi `engine.run(df.copy())` per config
- `core/data_loader.py::DataLoader('vn30').load(start, end)` — data source
- `core/indicators.py::build_indicator_dataframe(df)` — precompute non-ATR/non-DD indicators

### Strategy rules doc (sync target per CLAUDE.md Code-Docs Sync Rule)
- `docs/rules_mdm_hybrid.md` — KHÔNG đổi trong Phase 40 (sweep tools không sửa rule logic). Phase 42 DOC-01 sẽ update với sweep winners.

### Memory anchors
- v6.0 baseline VN30 2015-2026: CAGR 11.5%, MaxDD -28.2%, Return +238.8%, 124 SELL signals (84% MA50-breakdown)
- Success criterion v9.0: CAGR ≥ 11.5% AND (Sharpe > baseline OR MaxDD < -25%) — VAL-03 kiểm tra sau, Phase 40 chỉ chọn candidates
- Equity formula rule (`feedback_equity_formula.md`) — `compute_metrics` dùng `state[i-1]` pattern (đã đúng trong sweep_vn30_params.py mẫu)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analysis/sweep_vn30_params.py::compute_metrics()` — pattern tính equity curve + CAGR + MaxDD + transitions (long + short equity, `state[i-1]` discipline). Phase 40 extend hàm này thêm whipsaw columns.
- `dataclasses.replace(VN30_PRESET, **overrides)` — clean immutable config mutation, đã dùng trong Phase 32 sweep.
- `HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False))` pattern — nguyên gốc từ sweep_vn30_params.py.
- `DataLoader('vn30').load(start, end)` + `build_indicator_dataframe(df)` — data pipeline precompute, 1 lần cho toàn sweep.
- `tqdm` likely available (Phase 32 sweep_vn100.py dùng) — nếu không thì fallback print mỗi N configs.
- Output convention: `output/` directory ở root (có sẵn: vn30_backtest_results.csv, compare_vn30.txt) — Phase 40 dùng cùng thư mục.

### Established Patterns
- **Period hard-code trong analysis scripts**: Phase 32 D-09 precedent, Phase 40 mở rộng (D-12 OOS assert).
- **Dataclass + `dataclasses.replace`** cho config mutation trong sweep loop — Phase 32 precedent.
- **Audit CSV schema**: config fields + core metrics + diagnostic — Phase 32 D-17 precedent.
- **Feature flag false → byte-identical baseline**: Phase 38 ATR-04, Phase 39 DD-04. Phase 40 bật flag lên qua override, kế thừa invariant module đã lock.
- **Sequential 2-stage sweep**: chưa có precedent trong repo — Phase 40 là precedent đầu tiên cho v10.0+ future sweeps.
- **Output paths lowercase với underscore + CSV/TXT/JSON trio**: Phase 32 locked_params_top3.json precedent.

### Integration Points
- **Inputs:**
  - VN30 OHLCV data → `DataLoader` (2015-2021 train window only)
  - VN30_PRESET config template → `strategies/mdm_hybrid/config.py`
  - HybridEngine pipeline → Phase 38/39 modules đã wired
  - Action log schema → `HybridEngine.run()` output DataFrame (cần verify có `action` column với 'ma50_breakdown' label cho whipsaw metric)
- **Outputs:**
  - `output/v9_atr_sweep.csv` (36 rows, extended schema)
  - `output/v9_dd_sweep.csv` (54 rows, extended schema)
  - `output/v9_atr_best.txt` + `output/v9_atr_best.json`
  - `output/v9_dd_best.txt` + `output/v9_dd_best.json`
- **Downstream consumers:**
  - Phase 41 A/B report sẽ load v9_atr_best.json + v9_dd_best.json → reconstruct +ATR, +DD, +both configs cho 4 scenarios trên full 2015-2026
  - Phase 41 walk-forward test dùng cùng locked params trên Train 2015-2021 / Test 2022-2026

</code_context>

<specifics>
## Specific Ideas

- **"Provably untouched" OOS** — D-12 runtime assert là bắt buộc, không chỉ documentation. Sweep phải fail ngay nếu ai đó pass end_date > 2021 vào script sau này.
- **Constraint interpretation** — "MaxDD ≤ -30%" trong REQUIREMENTS nghĩa là "drawdown không nặng hơn -30%" (i.e. MaxDD value `>= -30` when values are negative). Keep rows where `max_dd_pct >= -30`. Decision D-15 làm rõ điểm này để tránh bug sign-flip.
- **Follow Phase 32 sweep-vn30 skeleton**: `sweep_vn30_params.py` là template gần nhất (cùng engine, cùng data source). Phase 40 mirror structure này cho ATR stage.
- **No multiprocessing cho Phase 40** — 90 runs ~2-5 phút serial là chấp nhận được. Giữ scripts đơn giản, debuggability trên hết.

</specifics>

<deferred>
## Deferred Ideas

- **Joint grid search (ATR × DD đồng thời, 1,944 combos)** — out of scope v9.0 per REQUIREMENTS "Out of Scope" mục. Sequential 90 runs đủ cho first pass.
- **Sensitivity sweep trên NASDAQ preset** — Phase 40 chỉ VN30. Nếu Phase 41 whipsaw diagnostic show pattern, có thể mở phase mới cho NASDAQ.
- **Equity curve PNG render cho top configs** — nice-to-have, scope Phase 41 hoặc Phase 42 dashboard.
- **Cost sensitivity** (commission/tax/slippage variations) — VN30 cash index không cần; CANSLIM sweeping Phase 33 đã có precedent nhưng off-scope v9.0.
- **MA50-breakdown action label guarantee** — Phase 40 giả định HybridEngine action log đã có label 'ma50_breakdown'. Nếu Plan phát hiện chưa có, cần add label (minor engine tweak) hoặc infer từ signal_log structure. Nếu chi phí cao → defer whipsaw column sang Phase 41.
- **Relaxed MaxDD tier fallback (-35%, -40%)** — D-16 chốt abort strict. Nếu run thực tế empty, user mở phase nhỏ hoặc chỉnh sửa grid thay vì tự động relax.
- **Parameterize `refined_dd_large_vol_rule`** (ngoài `vol_ma20`) — Phase 39 ship 1 rule duy nhất; sweep thêm rule là scope module mới.
- **Parameterize `refined_dd_small_vol_lookback`** (ngoài 50) — out of grid per ROADMAP; giữ fixed.

### Reviewed Todos (not folded)
Không có pending todo nào match Phase 40 scope (init tool báo empty).

</deferred>

---

*Phase: 40-grid-search-sweeps*
*Context gathered: 2026-04-16*
