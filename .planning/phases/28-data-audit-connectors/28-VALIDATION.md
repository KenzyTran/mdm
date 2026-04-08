---
phase: 28
slug: data-audit-connectors
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> See `28-RESEARCH.md` → Validation Architecture for rationale.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (Wave 0 installs `pytest` + adds `[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/ -m "not integration" -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10s (unit) / ~30s (full, incl. live DB integration) |

---

## Sampling Rate

- **After every task commit:** Run quick (`pytest -m "not integration"`)
- **After every plan wave:** Run full suite (includes `@pytest.mark.integration` DB tests)
- **Before `/gsd:verify-work`:** Full suite green + audit report committed
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 28-00-01 | 00 | 0 | infra | setup | `uv sync && uv run pytest --collect-only` | ❌ W0 | ⬜ pending |
| 28-01-01 | 01 | 1 | DATA-01 | unit | `pytest tests/test_connectors_postgres.py -q` | ❌ W0 | ⬜ pending |
| 28-01-02 | 01 | 1 | DATA-01 | integration | `pytest tests/test_connectors_postgres.py -m integration` | ❌ W0 | ⬜ pending |
| 28-02-01 | 02 | 1 | DATA-02 | unit | `pytest tests/test_connectors_mysql.py -q` | ❌ W0 | ⬜ pending |
| 28-02-02 | 02 | 1 | DATA-02 | integration | `pytest tests/test_connectors_mysql.py -m integration` | ❌ W0 | ⬜ pending |
| 28-03-01 | 03 | 2 | DATA-03 | unit | `pytest tests/test_adjust.py -q` | ❌ W0 | ⬜ pending |
| 28-04-01 | 04 | 2 | DATA-04 | unit | `pytest tests/test_eps_publish.py -q` | ❌ W0 | ⬜ pending |
| 28-05-01 | 05 | 3 | DATA-05,06,07 | script | `python scripts/run_phase28_audit.py --dry-run` | ❌ W0 | ⬜ pending |
| 28-05-02 | 05 | 3 | DATA-05,06,07 | manual | `test -f docs/audits/phase28-data-audit.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — add `sqlalchemy>=2.0`, `psycopg2-binary`, `pymysql`, `pytest>=7`
- [ ] `pyproject.toml` — add `[tool.pytest.ini_options]` with `markers = ["integration: requires live DB"]`
- [ ] `connectors/__init__.py` — empty package marker
- [ ] `tests/__init__.py` and `tests/conftest.py` — shared fixtures (fake OHLC DataFrame, env loader, skip-if-no-creds marker)
- [ ] `tests/test_connectors_postgres.py` — stub for DATA-01
- [ ] `tests/test_connectors_mysql.py` — stub for DATA-02
- [ ] `tests/test_adjust.py` — stub for DATA-03 (adjust_ohlc pure function)
- [ ] `tests/test_eps_publish.py` — stub for DATA-04 (resolve_eps_publish_date pure function)
- [ ] `docs/audits/` — directory created

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audit report narrative (delisted list, EPS coverage commentary) | DATA-05,06,07 | Requires human judgment on completeness vs. CANSLIM needs | Read `docs/audits/phase28-data-audit.md` — confirm it answers all 6 CONTEXT.md D-12 items |
| Adjusted-price spot check on 2–3 known-split tickers | DATA-03 | Visual sanity check of continuous series | Run `python scripts/spot_check_adjust.py TICKER` and eyeball output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
