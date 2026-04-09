---
phase: 30
slug: stock-level-entry-confirmation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/entry/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/entry/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 30-00-01 | 00 | 0 | (infra) | unit | `uv run pytest tests/entry/ -q` | ❌ W0 | ⬜ pending |

*To be completed by planner against ENTRY-01..ENTRY-05. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/entry/__init__.py` — package marker
- [ ] `tests/entry/conftest.py` — shared fixtures (synthetic OHLCV, MDM state series)
- [ ] `tests/entry/test_option_a.py` — stubs for ENTRY-01
- [ ] `tests/entry/test_option_c.py` — stubs for ENTRY-02
- [ ] `tests/entry/test_window.py` — stubs for ENTRY-03
- [ ] `tests/entry/test_execution.py` — stubs for ENTRY-04
- [ ] `tests/entry/test_ab_helper.py` — stubs for ENTRY-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A/B fill count plausibility on VN100 2014-2025 | ENTRY-05 | Requires full historical data; judgement call on result shape | Run A/B helper, eyeball side-by-side counts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
