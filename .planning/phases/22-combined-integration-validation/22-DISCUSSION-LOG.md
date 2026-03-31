# Phase 22: Combined Integration & Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 22-combined-integration-validation
**Areas discussed:** A/B comparison scope, Dashboard update, 8-combo integration test, CASH duration guard

---

## A/B Comparison Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Baseline vs all-on only | Single comparison: V2 baseline vs V2+all_filters. Clean, focused. | :heavy_check_mark: |
| Full matrix 8 combo | Compare all 8 combinations in one report with ranking table | |
| Progressive layering | Baseline -> +liquidity -> +sell_accel -> +buy_select | |

**User's choice:** Baseline vs all-on only (Recommended)
**Notes:** 8-combo test covers intermediate combos separately

| Option | Description | Selected |
|--------|-------------|----------|
| Script moi validate_combined.py | New script following validate_sell_acceleration.py pattern | :heavy_check_mark: |
| Mo rong validate_v2.py | Extend existing script | |

**User's choice:** New script validate_combined.py

| Option | Description | Selected |
|--------|-------------|----------|
| Chung 1 script | validate_combined.py runs A/B and walk-forward together | :heavy_check_mark: |
| Tach rieng | Separate walk-forward script | |

**User's choice:** Combined in one script

---

## Dashboard Update

| Option | Description | Selected |
|--------|-------------|----------|
| Metrics moi (total return, Sharpe) | Update performance metrics with filter-on results | :heavy_check_mark: |
| Global Liquidity overlay chart | Liquidity index over price chart with QE floor zones | :heavy_check_mark: |
| Signal quality annotations | Annotate signals with filter status (confirmed/rejected/delayed) | |
| Filter comparison table | Baseline vs all-on summary metrics table on dashboard | |

**User's choice:** Metrics + Global Liquidity overlay (2 of 4 selected)

| Option | Description | Selected |
|--------|-------------|----------|
| Mo rong export_dashboard_data.py | Extend existing export script | :heavy_check_mark: |
| Script export moi rieng | Separate new export script | |

**User's choice:** Extend existing export script

---

## 8-Combo Integration Test

| Option | Description | Selected |
|--------|-------------|----------|
| Parametrized pytest | @pytest.mark.parametrize with 8 combos, assert max drawdown | :heavy_check_mark: |
| Script chay tay | Manual script with results table | |
| Ca hai | Pytest + interactive script | |

**User's choice:** Parametrized pytest (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Chi NASDAQ | 8 combo x 2 sub-periods = 16 test cases | :heavy_check_mark: |
| Ca NASDAQ va VN30 | 8 combo x 2 markets x sub-periods = 24 test cases | |

**User's choice:** NASDAQ only (VN30 lacks 2008 data)

---

## CASH Duration Guard

| Option | Description | Selected |
|--------|-------------|----------|
| Tich hop trong validate_combined.py | Compute + WARNING if > 130% baseline | :heavy_check_mark: |
| Assert cung trong pytest | Hard fail in 8-combo test | |

**User's choice:** Integrated in validate_combined.py with WARNING (not hard fail)

---

## Claude's Discretion

- Chart formatting for Global Liquidity overlay
- Test file naming and location
- Report output format
- QE floor zone highlighting style
- Equity curve chart inclusion

## Deferred Ideas

None — discussion stayed within phase scope
