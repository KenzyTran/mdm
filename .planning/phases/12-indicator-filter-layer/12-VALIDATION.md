---
phase: 12
slug: indicator-filter-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_indicator_filter.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_indicator_filter.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | HYB-02a | unit | `uv run pytest tests/test_indicator_filter.py::TestBooleanConditions -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | HYB-02b | unit | `uv run pytest tests/test_indicator_filter.py::TestVerdict -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | HYB-02c | unit | `uv run pytest tests/test_indicator_filter.py::TestFilterConfig -x` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | HYB-02d | unit | `uv run pytest tests/test_indicator_filter.py::TestNaNHandling -x` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 1 | HYB-02e | integration | `uv run pytest tests/test_indicator_filter.py::TestTradingViewParity -x` | ❌ W0 | ⬜ pending |
| 12-01-06 | 01 | 1 | HYB-02f | unit | `uv run pytest tests/test_indicator_filter.py::TestProposalDirection -x` | ❌ W0 | ⬜ pending |
| 12-01-07 | 01 | 1 | HYB-02g | unit | `uv run pytest tests/test_indicator_filter.py::TestOverride -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_indicator_filter.py` — stubs for all HYB-02 sub-requirements
- [ ] `tests/fixtures/tradingview_reference.csv` — TradingView parity data (10+ dates)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TradingView value collection | HYB-02e | Values must be read from TradingView UI data window | Open TradingView NASDAQ chart, hover over EMA/MACD indicators at 10+ reference dates, record values into CSV fixture |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
