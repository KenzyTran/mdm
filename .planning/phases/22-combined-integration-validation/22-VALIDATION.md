---
phase: 22
slug: combined-integration-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | VAL-05 | integration | `uv run python analysis/validate_combined.py` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | VAL-07 | integration | `uv run python analysis/validate_combined.py` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | VAL-05 | unit | `uv run pytest tests/test_combined_integration.py -v` | ❌ W0 | ⬜ pending |
| 22-02-01 | 02 | 2 | VAL-06 | integration | `uv run python scripts/export_dashboard_data.py` | ✅ | ⬜ pending |
| 22-02-02 | 02 | 2 | VAL-06 | manual | S3 dashboard visual check | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_combined_integration.py` — stubs for 8-combo parametrized test (VAL-05)
- [ ] `analysis/validate_combined.py` — A/B + walk-forward validation script (VAL-05, VAL-07)

*Existing test infrastructure (pytest, conftest) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| S3 dashboard displays updated metrics and Global Liquidity overlay | VAL-06 | Visual verification of deployed S3 static site | 1. Run `scripts/deploy_dashboard.sh` 2. Open S3 URL 3. Verify new metrics and liquidity chart visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
