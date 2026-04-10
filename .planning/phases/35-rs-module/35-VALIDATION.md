---
phase: 35
slug: rs-module
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -q -x` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q -x`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 35-01-01 | 01 | 1 | MOM-01 | unit | `uv run pytest tests/test_rs_module.py::test_ibd_weighted_roc -q` | ❌ W0 | ⬜ pending |
| 35-01-02 | 01 | 1 | MOM-02 | unit | `uv run pytest tests/test_rs_module.py::test_roc126 -q` | ❌ W0 | ⬜ pending |
| 35-01-03 | 01 | 2 | MOM-03 | unit | `uv run pytest tests/test_rs_module.py::test_cache_skip -q` | ❌ W0 | ⬜ pending |
| 35-01-04 | 01 | 2 | MOM-01,MOM-02 | integration | `uv run pytest tests/test_rs_module.py::test_percentile_range -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rs_module.py` — stubs for MOM-01, MOM-02, MOM-03
- [ ] `tests/conftest.py` — shared fixtures (if not exists)

*Existing pytest infrastructure covers the phase; only new test file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-sectional correctness (top performer near rank 99) | MOM-01, MOM-02 | Requires real market data spot-check | Run RS module on known date, verify top 1-3 tickers have ranks ≥ 95 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
