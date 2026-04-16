# Phase 39: Refined Distribution Day Module - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Thay DD detector hard-coded -0.2% trong HybridEngine bằng dual-threshold parameterized rule: (large_drop + vol>MA20) OR (small_drop + top-percentile volume). Toàn bộ tính năng nằm sau cờ `refined_dd_enabled`; khi tắt phải tái lập byte-identical DD sequence của v6.0 baseline trên VN30 2015-2026. Sweep parameters sẽ làm ở Phase 40 — Phase 39 chỉ giao module + A/B toggle + regression test.

</domain>

<decisions>
## Implementation Decisions

### Stalling DD (Type 2)
- **D-01:** Giữ Type 2 stalling DD song song với dual-threshold rule mới. Khi `refined_dd_enabled=True`, cả 3 nguồn DD đều count (large_drop rule, small_drop rule, Type 2 stalling). Type 2 logic (`price_change_pct < 0.1%`, `volume_up`, `p_loc <= 0.2`) không thay đổi.
- **D-02:** Khi `refined_dd_enabled=False`, fallback hoàn toàn về logic v6.0 (Type 1 dùng `-0.2%` hard-code + `volume_up`, Type 2 giữ nguyên). Đảm bảo DD-04 backward-compat.

### Volume comparison semantics
- **D-03:** Thêm precompute columns mới trong `Indicators`: `add_volume_ma_column(df, period=20)` ghi column `vol_ma20`, và `add_volume_percentile_column(df, lookback, percentile)` ghi column `vol_percentile_rank`. Compute trước loop trong HybridEngine pipeline, tương tự pattern `add_atr_column`.
- **D-04:** `volume_up` (volume > prev_volume) KHÔNG bị thay đổi — vẫn dùng cho FTD, stop-loss, và Type 2 stalling DD. Dual-threshold rule mới dùng `vol_ma20` và `vol_percentile_rank` columns riêng.
- **D-05:** Khi `refined_dd_enabled=False`, skip compute `vol_ma20` và `vol_percentile_rank` để đảm bảo không side-effect lên columns/state khác (bảo vệ DD-04).

### Parameter defaults trước sweep
- **D-06:** Defaults shipped trong `MDMConfig`: `refined_dd_enabled=False`, `large_drop=-0.007` (-0.7%), `small_drop=-0.004` (-0.4%), `large_vol_rule='vol_ma20'`, `small_vol_percentile=5` (top 5%), `small_vol_lookback=50` (50 phiên). Giữa sweep range của Phase 40 để A/B test nội bộ có ý nghĩa.
- **D-07:** Cả `VN30_PRESET` và `NASDAQ_PRESET` đều ship `refined_dd_enabled=False` (backward-compat). Phase 40 sẽ override qua sweep config.

### DD counting logic
- **D-08:** Chỉ thay đổi WHAT counts as DD (definition), không thay HOW DDs are counted. 20-day rolling window (`dd_window_size=20`), DD5 high tracking, và 5DD trigger trong position_manager giữ nguyên.
- **D-09:** DD count metrics (dd_count_20d, dd5_high) sẽ tự nhiên thay đổi khi `refined_dd_enabled=True` do definition khác — Phase 40 sweep đánh giá impact qua Sharpe/CAGR/MaxDD.

### Regression baseline (DD-04)
- **D-10:** Follow Phase 38 pattern: capture v6.0 DD baseline (chạy HybridEngine `refined_dd_enabled=False` trên VN30 2015-2026), lưu signal log thành `tests/fixtures/phase39_v6_baseline_dd_sequence.parquet`. Commit fixture vào repo.
- **D-11:** Regression test pytest: load fixture + chạy HybridEngine `refined_dd_enabled=False`, assert DD columns (is_dd, dd_type, dd_count_20d) khớp byte-identical.

### Claude's Discretion
- Exact method signatures và naming cho `add_volume_ma_column` / `add_volume_percentile_column`
- Cách tổ chức logic trong `DistributionDayCounter` (thêm methods mới vs refactor `is_distribution_day_type1`)
- Format tên test file và fixture
- Cách log khi refined DD trigger fire vs classic DD (action string annotation)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §DD (DD-01..DD-04) — parameterized dual-threshold definition, config flag, backward-compat invariant
- `.planning/ROADMAP.md` §Phase 39 (lines 742-751) — goal, depends on Phase 38, 4 success criteria

### Strategy rules doc (sync target per CLAUDE.md Code-Docs Sync Rule)
- `docs/rules_mdm_hybrid.md` — MUST be updated in cùng commit khi bổ sung refined DD rule

### Existing code integration points
- `strategies/mdm_hybrid/config.py` — add `refined_dd_*` fields to `MDMConfig` dataclass (follow `atr_buffer_*` pattern từ Phase 38)
- `strategies/mdm_hybrid/distribution_day.py` — modify `DistributionDayCounter` to support dual-threshold rule
- `strategies/mdm_hybrid/indicators.py` — add `add_volume_ma_column()` và `add_volume_percentile_column()`
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — indicator pipeline hook cho volume columns
- `strategies/mdm_hybrid/position_manager.py` — DD counting logic KHÔNG đổi

### Prior phase context
- `.planning/phases/38-atr-buffer-zone-module/38-CONTEXT.md` — feature-gate pattern, regression fixture pattern, backward-compat invariant

### Prior milestone context
- v6.0 baseline: CAGR 11.5%, MaxDD -28.2%, Return +238.8% trên VN30 2015-2026
- Phase 38 đã ship ATR buffer module behind `atr_buffer_enabled` flag
- Milestone v9.0 target: giảm whipsaw (84% SELL đến từ MA50 breakdown)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DistributionDayCounter` tại `strategies/mdm_hybrid/distribution_day.py` — đã có Type 1/Type 2 detection, DD counting, DD5 high tracking. Thêm dual-threshold logic vào class này.
- `Indicators` class tại `strategies/mdm_hybrid/indicators.py` — pattern `add_*_column(df, ...)` cho precompute. `add_atr_column` là template cho volume columns mới.
- `MDMConfig` dataclass tại `strategies/mdm_hybrid/config.py` — pattern `__post_init__` validation, `VN30_PRESET`/`NASDAQ_PRESET`. Phase 38 đã thêm `atr_buffer_*` fields — follow same pattern.
- `ma50_sell_enabled` flag pattern (config.py:43) — tiền lệ cho feature-gate A/B toggle.
- Phase 38 regression fixture pattern: `tests/fixtures/phase38_v6_baseline_signal_log.parquet` + `tests/test_phase38_backward_compat.py`

### Established Patterns
- Indicator pipeline precompute: engine gọi `Indicators.add_*_column(df, ...)` trước daily loop. Column truy xuất qua `df.loc[i, 'colname']`.
- Feature-gate toggles: bool flag trong config → branch trong distribution_day/position_manager.
- `volume_up = volume > prev_volume` tại indicators.py:110 — dùng bởi FTD, stop-loss, Type 2 DD. KHÔNG thay đổi.
- VN30 expiry filter: `vn30_filters.py` override `volume_up=False` on expiry days → cần đảm bảo refined DD cũng respect expiry filter.

### Integration Points
- `HybridEngine.run()` — thêm `add_volume_ma_column()` và `add_volume_percentile_column()` vào precompute block nếu `refined_dd_enabled=True`.
- `DistributionDayCounter.is_distribution_day_type1()` — branch logic: nếu `refined_dd_enabled` dùng dual-threshold; else giữ classic -0.2% rule.
- Regression fixture + test: `tests/fixtures/phase39_v6_baseline_dd_sequence.parquet` + `tests/test_phase39_backward_compat.py`.

</code_context>

<specifics>
## Specific Ideas

- Follow Phase 38 pattern chính xác: feature-gate flag + defaults False + regression parquet baseline + pytest backward-compat test.
- "Phase 39 phải giữ byte-identical khi `refined_dd_enabled=False`" — invariant cứng (DD-04), tương tự ATR-04.
- VN30 expiry filter phải tương thích: khi expiry day override `volume_up=False`, refined DD cũng không nên fire trên ngày đó (xem xét thêm check tương tự).
- `large_vol_rule='vol_ma20'` là string param — có thể mở rộng sang rule khác trong tương lai nhưng Phase 39 chỉ implement 'vol_ma20'.

</specifics>

<deferred>
## Deferred Ideas

- **Sweep parameters cho DD** — Phase 40 (Grid Search Sweeps) sẽ sweep `large_drop`, `small_drop`, `small_vol_percentile` trên train window 2015-2021.
- **DD count threshold tuning** — Thêm `dd_count_threshold` param (hiện hard-code 5) có thể hữu ích cho sweep nhưng out of scope Phase 39.
- **Type 2 stalling threshold tuning** — Parameterize stalling thresholds (0.1%, p_loc 0.2) cho sweep. Deferred — Phase 39 giữ hard-code.
- **Export DD metrics lên dashboard** — Phase 42 sẽ decide có render DD type breakdown trên chart không.

### Reviewed Todos (not folded)
Không có pending todo nào match Phase 39 scope.

</deferred>

---

*Phase: 39-refined-distribution-day-module*
*Context gathered: 2026-04-16*
