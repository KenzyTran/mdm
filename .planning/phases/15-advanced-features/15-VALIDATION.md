---
phase: 15
slug: advanced-features
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 9.0.2 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_indicator_filter.py tests/test_hybrid_engine.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_indicator_filter.py tests/test_hybrid_engine.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | ADV-02 | unit | `uv run pytest tests/test_indicator_filter.py::test_ha_smooth_condition -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | ADV-03 | unit | `uv run pytest tests/test_indicator_filter.py::test_confidence_score -x` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | ADV-01 | unit | `uv run pytest tests/test_hybrid_engine.py::test_contextual_transitions -x` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | ADV-04 | smoke | `uv run python analysis/compare_models.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_indicator_filter.py::test_ha_smooth_bullish` — HA condition True when green candle
- [ ] `tests/test_indicator_filter.py::test_ha_smooth_bearish` — HA condition True when red candle
- [ ] `tests/test_indicator_filter.py::test_ha_smooth_nan_safe` — NaN returns False
- [ ] `tests/test_indicator_filter.py::test_confidence_returned` — evaluate() returns confidence float
- [ ] `tests/test_indicator_filter.py::test_ha_smooth_toggle_off` — disabled by default, no effect
- [ ] `tests/test_hybrid_engine.py::test_confidence_column_exists` — output DataFrame has confidence col
- [ ] `tests/test_hybrid_engine.py::test_state_history_tracking` — state history populated on transitions
- [ ] `tests/test_hybrid_engine.py::test_contextual_cash_stickiness` — context rules affect verdicts
- [ ] `tests/test_hybrid_engine.py::test_baseline_unchanged` — filter_enabled=True without HA still matches Phase 14

*Existing infrastructure covers framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Three-way dashboard visual correctness | ADV-04 | Chart layout and readability require visual inspection | Run `uv run python analysis/compare_models.py`, inspect output chart for side-by-side accuracy display |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
