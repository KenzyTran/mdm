# Phase 38: ATR Buffer Zone Module - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Thay trigger SELL hiện tại (`close < MA50`) trong HybridEngine bằng rule có đệm: `close < SMA50 − k × ATR_N` với xác nhận m phiên liên tiếp. Toàn bộ tính năng nằm sau cờ `atr_buffer_enabled`; khi tắt phải tái lập byte-identical signal log của v6.0 baseline trên VN30 2015-2026. Sweep (k, N, m) và A/B full sẽ làm ở Phase 40-41 — Phase 38 chỉ giao module + A/B toggle + regression test.

</domain>

<decisions>
## Implementation Decisions

### Tham số ATR
- **D-01:** Thêm tham số mới `atr_buffer_period: int = 14` trong `MDMV2Config`, tách biệt hoàn toàn với `atr_period=14` hiện có (dùng cho stop-loss). Lý do: Phase 40 sweep sẽ quét `atr_buffer_period ∈ {10, 14, 20}` mà không chạm stop-loss, giữ ATR-04 (byte-identical khi tắt) dễ kiểm chứng.
- **D-02:** Thêm tham số `atr_buffer_k: float = 0.5` (multiplier) và `atr_buffer_consecutive_days: int = 2` (m). Cả ba đều "ngủ" khi `atr_buffer_enabled=False` và không tham gia tính toán nào ngoài khi cờ bật.

### Ngữ nghĩa m-day confirmation
- **D-03:** m-day rule là backward-looking, kích hoạt cùng ngày: trigger SELL fires hôm nay khi `close[t-m+1 .. t]` đều < `violation_threshold[t-m+1 .. t]` tương ứng. m=1 tương đương luật v6.0 khi `violation_threshold ≡ MA50`.
- **D-04:** Trong m ngày đầu tiên của dữ liệu (không đủ lookback), rule không fire — tương tự cách các indicator khác (MA50 warm-up) đã handle hiện tại. Không fallback sang rule v6.0 lúc warm-up khi `atr_buffer_enabled=True`.

### Giá trị mặc định (atr_buffer_enabled=False)
- **D-05:** Defaults shipped trong `MDMV2Config`: `atr_buffer_enabled=False`, `atr_buffer_k=0.5`, `atr_buffer_period=14`, `atr_buffer_consecutive_days=2`. Cả `VN30_PRESET` và `NASDAQ_PRESET` trong [strategies/mdm_hybrid/config.py](strategies/mdm_hybrid/config.py) đều giữ `atr_buffer_enabled=False` (backward-compat).
- **D-06:** Khi Phase 38 chạy A/B test nội bộ (enabled=True vs False), dùng đúng defaults trên — không sweep trong phase này. Phase 40 sẽ override qua sweep config.

### Vị trí tính `violation_threshold`
- **D-07:** Thêm static method `Indicators.add_violation_threshold_column(df, k, period)` vào [strategies/mdm_hybrid/indicators.py](strategies/mdm_hybrid/indicators.py) (cạnh `add_atr_column`). Ghi column `violation_threshold` vào DataFrame một lần trong pipeline của `HybridEngine` (trước loop), đọc trực tiếp tại position_manager.
- **D-08:** Column luôn được compute khi `atr_buffer_enabled=True` (dùng k, period từ config); khi tắt, có thể skip compute để đảm bảo không có side-effect nào lên các column/state khác (bảo vệ ATR-04).
- **D-09:** Export `violation_threshold` lên dashboard JSON là **deferred** — Phase 42 sẽ xử lý dashboard.

### Đối xứng short-side
- **D-10:** Buffer **bất đối xứng** — chỉ áp dụng cho trigger CASH→SELL entry tại [strategies/mdm_hybrid/position_manager.py:278](strategies/mdm_hybrid/position_manager.py#L278). Short cover `SELL→CASH` (close > MA50) ở [position_manager.py:320](strategies/mdm_hybrid/position_manager.py#L320) giữ nguyên. Lý do: ROADMAP và ATR-02 chỉ nói "MA50 breakdown SELL trigger"; mở rộng sang short cover là scope mới (deferred).
- **D-11:** Stop-loss `ma50_vol_breakdown_exit` ở [stop_loss.py:136-138](strategies/mdm_hybrid/stop_loss.py#L136) (exit BUY→CASH khi `close < MA50 AND volume up`) cũng **không** đổi — đó là BUY-state exit, không phải CASH→SELL entry.

### Regression baseline (ATR-04)
- **D-12:** Capture v6.0 baseline một lần: chạy HybridEngine với `atr_buffer_enabled=False` trên VN30 2015-2026, lưu signal log thành `tests/fixtures/phase38_v6_baseline_signal_log.parquet` (date, state, action cho mỗi trading day). Commit fixture vào repo.
- **D-13:** Regression test mới (pytest) load fixture + chạy HybridEngine với defaults `atr_buffer_enabled=False`, assert DataFrame equal (byte-identical trên các cột core: date, state, transition, ma50, close). Test chạy trong CI mỗi PR.

### Claude's Discretion
- Chi tiết cách tách compute block trong `HybridEngine.run()` (trước vòng loop daily).
- Format tên test file và tên regression fixture folder (theo convention `tests/fixtures/` nếu chưa tồn tại thì tạo).
- Cách log khi buffer-zone trigger fire vs MA50 plain (chỉ thêm phần tử vào action string, không đổi schema).
- Chọn tên method chính xác cho `Indicators.add_violation_threshold_column` (có thể rút gọn nếu lặp tên hiện có).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §ATR Buffer Zone (ATR-01..04) — định nghĩa chính xác formula, consecutive-day rule, flag & backward-compat
- `.planning/ROADMAP.md` §Phase 38 — goal, depends, 4 success criteria (lines 726-735)

### Strategy rules doc (sync target per CLAUDE.md Code-Docs Sync Rule)
- `docs/rules_mdm_hybrid.md` — MUST be updated in cùng commit khi bổ sung buffer-zone rule (sync với strategies/mdm_hybrid/)

### Existing code integration points
- `strategies/mdm_hybrid/config.py` — add `atr_buffer_*` fields to `MDMV2Config` (hiện có dataclass, __post_init__)
- `strategies/mdm_hybrid/indicators.py` — add `add_violation_threshold_column()` (cạnh `add_atr_column` line 193)
- `strategies/mdm_hybrid/position_manager.py:278` — trigger point cần thay rule
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — indicator pipeline hook trước daily loop
- `strategies/mdm_hybrid/stop_loss.py:136` — **không sửa** (BUY-state exit, không phải scope ATR-02)

### Prior milestone context
- v6.0 baseline metrics (memory anchor): CAGR 11.5%, MaxDD -28.2%, Return +238.8% trên VN30 2015-2026
- Milestone v9.0 target: giảm whipsaw (84% SELL đến từ MA50 breakdown)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Indicators.add_atr_column(df, period=14)` tại [strategies/mdm_hybrid/indicators.py:193](strategies/mdm_hybrid/indicators.py#L193) — tính sẵn `atr` và `true_range`. `add_violation_threshold_column` nên gọi nội bộ hàm này nếu `period` khác `atr_period` hiện có (cân nhắc column suffix để tránh overwrite).
- `MDMV2Config` đã có pattern dataclass + `__post_init__` validation — D-01..D-05 chỉ cần thêm fields + assertion (k > 0, period > 0, m >= 1).
- `ma50_sell_enabled` flag hiện có tại [config.py:43](strategies/mdm_hybrid/config.py#L43) là tiền lệ cho kiểu feature-gate A/B mà `atr_buffer_enabled` sẽ follow.
- VN30_PRESET / NASDAQ_PRESET presets (config.py:102, 128) là template để thêm defaults mới.

### Established Patterns
- Indicator pipeline precompute: engine gọi `Indicators.add_*_column(df, ...)` trước khi vào daily loop (bằng chứng: `add_ma_columns`, `add_atr_column` đã được dùng). Column được truy xuất qua `df.loc[i, 'colname']` trong loop.
- Feature-gate toggles: bool flag trong config → branch trong position_manager (pattern hiện tại: `if self.config.ma50_sell_enabled and ... and close < ma50`).
- Tests directory convention: project dùng pytest (xem pyproject.toml); fixtures tạo mới tại `tests/fixtures/` nếu chưa có.

### Integration Points
- `HybridEngine.run()` — chèn `add_violation_threshold_column()` vào block precompute indicator nếu `atr_buffer_enabled=True`.
- `V2PositionManager.update_cash_state()` — branch logic SELL entry: nếu `atr_buffer_enabled` đọc `violation_threshold` column + kiểm tra m-day streak; else giữ nguyên `close < ma50`.
- Regression fixture + test: `tests/fixtures/phase38_v6_baseline_signal_log.parquet` + `tests/test_phase38_backward_compat.py`.

</code_context>

<specifics>
## Specific Ideas

- "Phase 38 phải giữ byte-identical khi `atr_buffer_enabled=False`" — đây là invariant cứng của milestone v9.0, không thoả hiệp. Regression parquet baseline bảo vệ điều này.
- "Giữ scope tối thiểu — chỉ thay trigger SELL entry, không đụng short cover, không đụng BUY→CASH" — giữ phase nhỏ để Phase 40 sweep dễ attribute whipsaw reduction cho ATR buffer isolated.
- Reference pattern: cách Phase 23 fail-safe và Phase 26 banding filter dùng feature-gate flag trong config + default False trên code path mới.

</specifics>

<deferred>
## Deferred Ideas

- **Symmetric short-cover buffer** — `close > ma50 + k*atr` cho SELL→CASH cover. Cần sweep riêng vì tác động tới timing thoát short. Nên mở Phase mới trong roadmap v9.0+ nếu kết quả Phase 41 cho thấy short cover whipsaw đáng kể.
- **Export `violation_threshold` lên dashboard** — Phase 42 (Documentation & Dashboard) sẽ decide có render đường buffer trên equity chart không.
- **Sentinel-based config validation** (raise nếu enabled=True mà k/N/m=None) — hiện dùng defaults nên không cần, nhưng có thể bổ sung khi chuyển sang config file YAML (future).
- **Áp dụng buffer cho BUY-state MA50 exit** (stop_loss.py:136) — bất đối xứng nhưng đã được user confirm là out-of-scope Phase 38.

### Reviewed Todos (not folded)
Không có pending todo nào match Phase 38 scope (init tool report empty).

</deferred>

---

*Phase: 38-atr-buffer-zone-module*
*Context gathered: 2026-04-15*
