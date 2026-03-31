---
phase: 21
slug: buy-selectivity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 9.0.2 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_buy_selectivity.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_buy_selectivity.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | BUY-01 | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyFilter -x` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | BUY-01 | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyFilter::test_ma50_breakout_bypasses -x` | ❌ W0 | ⬜ pending |
| 21-01-03 | 01 | 1 | BUY-01 | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyFilter::test_52week_bypasses -x` | ❌ W0 | ⬜ pending |
| 21-01-04 | 01 | 1 | BUY-02 | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyConfirmation::test_clean_window -x` | ❌ W0 | ⬜ pending |
| 21-01-05 | 01 | 1 | BUY-02 | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyConfirmation::test_dd_cancellation -x` | ❌ W0 | ⬜ pending |
| 21-01-06 | 01 | 1 | BUY-02 | unit | `uv run pytest tests/test_buy_selectivity.py::TestBuyConfirmation::test_entry_price -x` | ❌ W0 | ⬜ pending |
| 21-02-01 | 02 | 2 | BUY-01+02 | integration | `uv run pytest tests/test_buy_selectivity.py::TestEngineIntegration -x` | ❌ W0 | ⬜ pending |
| 21-02-02 | 02 | 2 | BUY-01+02 | smoke | `uv run python analysis/validate_buy_selectivity.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_buy_selectivity.py` — stubs for BUY-01, BUY-02 unit + integration tests
- [ ] `analysis/validate_buy_selectivity.py` — A/B validation script

*Existing infrastructure covers test framework (pytest already installed).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Walk-forward degradation < 10% | BUY-01+02 | Requires full backtest run with train/test split | Run validate_buy_selectivity.py, check degradation column |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
