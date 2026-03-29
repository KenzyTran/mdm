---
phase: 9
slug: rule-discovery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ (via uv dev-dependencies) |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_rule_discovery.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_rule_discovery.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | DISC-01 | unit | `uv run pytest tests/test_rule_discovery.py::test_boolean_frequency_profile -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | DISC-01 | unit | `uv run pytest tests/test_rule_discovery.py::test_continuous_stats_profile -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | DISC-02 | unit | `uv run pytest tests/test_rule_discovery.py::test_decision_tree_above_chance -x` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | DISC-03 | unit | `uv run pytest tests/test_rule_discovery.py::test_rule_extraction_format -x` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | DISC-04 | unit | `uv run pytest tests/test_rule_discovery.py::test_era_split_produces_separate_results -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rule_discovery.py` — stubs for DISC-01 through DISC-04
- [ ] scikit-learn dependency added to pyproject.toml — required for imports in test

*Existing infrastructure covers pytest framework and conftest fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Statistical profile reveals clear separation between Buy/Sell/Cash | DISC-01 | Visual interpretation of frequency distributions | Review printed frequency tables — differences between signal types should be visually obvious |
| Human-readable rules make domain sense | DISC-03 | Semantic correctness requires trading knowledge | Read extracted rules — verify they reference meaningful indicators, not noise |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
