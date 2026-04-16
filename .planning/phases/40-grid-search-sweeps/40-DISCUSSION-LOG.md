# Phase 40: Grid Search Sweeps - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 40-grid-search-sweeps
**Areas discussed:** Constraint fallback, Baseline config cơ sở, Script layout + orchestration, Metrics + output format, OOS guard + Handoff

---

## Constraint Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Abort + exit code 1 (Recommended) | Fail-loud RuntimeError nếu không config nào pass MaxDD ≤ -30%. User can thiệp thủ công. | ✓ |
| Fallback max-Sharpe + warning | Chọn max-Sharpe unconstrained, ghi warning. Pragmatic, không block pipeline. | |
| Two-tier: relax MaxDD dần | Thử -30% → -35% → -40%. Tự động hóa nhưng phức tạp. | |

**User's choice:** Abort + exit code 1
**Notes:** v6.0 baseline MaxDD -28.2% cho thấy kịch bản abort hiếm xảy ra; nếu fire, nên intervene manually (grid sai hoặc data issue).

---

## Tiebreak (nested under Constraint Fallback)

| Option | Description | Selected |
|--------|-------------|----------|
| Tiebreak 3-tier: Sharpe → CAGR → MaxDD (Recommended) | Phase 32 D-12 pattern. MaxDD ít âm hơn thắng ở tier 3. | ✓ |
| Tiebreak transitions thấp hơn | Align với whipsaw reduction goal. | |
| Tiebreak simpler params | Ưu tiên config không "extreme" để chống overfitting. | |

**User's choice:** Tiebreak 3-tier
**Notes:** Giữ consistent với Phase 32 precedent.

---

## Baseline Config

| Option | Description | Selected |
|--------|-------------|----------|
| Copy VN30_PRESET, override ATR/DD only (Recommended) | Start từ VN30_PRESET, flip 1 feature flag + override params stage-specific. | ✓ |
| Start fresh MDMV2Config defaults | Không dùng preset. Không match v6.0 baseline. | |
| VN30_PRESET + ma50_sell=False | Tắt MA50 path gốc, ATR là replacement duy nhất. Risky. | |

**User's choice:** Copy VN30_PRESET, override ATR/DD only
**Notes:** Giữ fail_safe, correction -0.06, cash_deter=20, ma10_cash_cons=3 — baseline khớp v6.0.

---

## ATR Stage DD Handling

| Option | Description | Selected |
|--------|-------------|----------|
| refined_dd_enabled=False — classic v6.0 DD (Recommended) | Isolate ATR impact. | ✓ |
| refined_dd_enabled=True, DD defaults | Compound 2 features sớm. | |
| Tùy user qua CLI flag | Linh hoạt, overkill. | |

**User's choice:** refined_dd_enabled=False
**Notes:** ATR sweep cô lập 1 dimension biến.

---

## Script Layout

| Option | Description | Selected |
|--------|-------------|----------|
| 3 scripts riêng (Recommended) | sweep_v9_atr.py + sweep_v9_dd.py + select_v9_best.py | ✓ |
| 1 script sequential | sweep_v9.py end-to-end | |
| 2 scripts + inline selection | Duplicated selection logic | |

**User's choice:** 3 scripts riêng
**Notes:** Debug dễ, re-run stage riêng, mirror Phase 32 pattern.

---

## Orchestration

| Option | Description | Selected |
|--------|-------------|----------|
| Serial với tqdm progress bar (Recommended) | 90 runs, ~2-5 phút. | ✓ |
| multiprocessing.Pool | Nhanh hơn ~30%, phức tạp hơn. | |
| Serial + precompute cache baseline df | Cache 1 lần build_indicator_dataframe. | |

**User's choice:** Serial với tqdm
**Notes:** Load data + build_indicator_dataframe 1 lần, sau đó loop pass df.copy() vào engine.

---

## CSV Metrics

| Option | Description | Selected |
|--------|-------------|----------|
| Extended: + whipsaw diagnostic cho Phase 41 (Recommended) | Core + sell_count + ma50_breakdown_share + time_in_state | ✓ |
| Tối thiểu spec | Core 4 columns chỉ. | |
| Extended + sanity_flag | Thêm CAGR sanity flag. | |

**User's choice:** Extended
**Notes:** Phase 41 VAL-04 cần whipsaw metrics — ghi luôn để tiết kiệm re-run.

---

## Best File Format

| Option | Description | Selected |
|--------|-------------|----------|
| TXT human + JSON sibling (Recommended) | v9_atr_best.txt + v9_atr_best.json | ✓ |
| TXT duy nhất | Strict theo REQUIREMENTS, parse thủ công. | |
| JSON duy nhất | Vi phạm REQUIREMENTS (spec nói .txt). | |

**User's choice:** TXT + JSON sibling
**Notes:** Phase 41 load JSON dễ, TXT đọc mắt được.

---

## OOS Guard

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-code + runtime assert (Recommended) | TRAIN_START/END constants + assert max date ≤ 2021-12-31 | ✓ |
| CLI args + assert | Override window qua CLI, linh hoạt. | |
| Hard-code + audit log | Ghi window + data hash vào output. | |

**User's choice:** Hard-code + runtime assert
**Notes:** Không nhận CLI window override — reproducibility tuyệt đối.

---

## Handoff ATR → DD

| Option | Description | Selected |
|--------|-------------|----------|
| sweep_v9_dd.py đọc output/v9_atr_best.json (Recommended) | JSON sibling từ select stage 1. | ✓ |
| CLI arg --atr-best path | Linh hoạt, thêm 1 step nhớ. | |
| Hard-code path | No CLI override. | |

**User's choice:** Đọc output/v9_atr_best.json
**Notes:** Nếu file missing, raise với hướng dẫn chạy select stage=atr trước.

---

## Claude's Discretion

- Exact column order trong CSV
- Chi tiết tên metric columns (snake_case)
- Parse logic cho ma50_breakdown label từ action log
- Format chi tiết TXT layout
- Equity curve PNG cho top configs (optional)
- Log verbosity

## Deferred Ideas

- Joint grid search (ATR × DD, 1,944 combos)
- NASDAQ sensitivity sweep
- Equity curve rendering
- Cost sensitivity
- Relaxed MaxDD tier fallback
- Parameterize refined_dd_large_vol_rule / small_vol_lookback
- MA50-breakdown action label fallback nếu engine chưa có
