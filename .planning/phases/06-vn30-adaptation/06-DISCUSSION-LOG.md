# Phase 6: VN30 Adaptation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 06-vn30-adaptation
**Areas discussed:** Price limit handling, Settlement & expiry, Parameter recalibration, Backtest scope

---

## Price Limit Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Filter signals on limit days | Skip signal generation on limit-up/limit-down days -- distorted volume/price action | |
| Flag but don't filter | Mark limit days in data but process signals normally -- let sweep decide | ✓ |
| Treat limit-up as forced DD | Limit-down counts as DD regardless of volume; limit-up ignored for DD | |

**User's choice:** Flag but don't filter
**Notes:** User prefers data-driven approach -- flag for analysis but let parameter optimization handle the impact.

### Follow-up: FTD on limit-up days

| Option | Description | Selected |
|--------|-------------|----------|
| No suppression | Limit-up FTD is valid -- 7% cap doesn't invalidate buying pressure | ✓ |
| Suppress and re-evaluate next day | Wait one more day to confirm move continues | |

**User's choice:** No suppression

### Follow-up: Detection logic location

| Option | Description | Selected |
|--------|-------------|----------|
| VN30 microstructure module | New `strategies/mdm_v2/vn30_filters.py` with detect_limit_day() | ✓ |
| Inside data loader | Detect limit days during data loading in core/data_loader.py | |

**User's choice:** VN30 microstructure module

---

## Settlement & Expiry

### T+2.5 Settlement

| Option | Description | Selected |
|--------|-------------|----------|
| Ignore settlement delay | MDM is daily-bar model -- settlement is execution constraint, not signal factor | ✓ |
| Add execution delay | Simulate T+2.5 by delaying Buy execution by 3 trading days | |
| Flag but execute same-day | Mark settlement-constrained trades, execute at signal day's close | |

**User's choice:** Ignore settlement delay

### Derivative Expiry

| Option | Description | Selected |
|--------|-------------|----------|
| Flag expiry days, no signal changes | Add is_expiry_day column, let sweep handle it | |
| Suppress DD counting on expiry | Don't count distribution days on derivative expiry dates | ✓ |
| Skip entirely | Don't implement any special handling | |

**User's choice:** Suppress DD counting on expiry

### Follow-up: Expiry date identification

| Option | Description | Selected |
|--------|-------------|----------|
| Compute algorithmically | Calculate 3rd Thursday of each month in code | ✓ |
| Hardcoded CSV of expiry dates | Maintain CSV of known expiry dates | |

**User's choice:** Compute algorithmically

---

## Parameter Recalibration

### Recalibration approach

| Option | Description | Selected |
|--------|-------------|----------|
| Fresh grid sweep on VN30 | Run parameter sweep over VN30 data using Phase 4 framework | ✓ |
| NASDAQ params + manual tuning | Start with best NASDAQ config, manually adjust | |
| Both: manual first, then narrow sweep | Use diagnose_vn30.py to narrow ranges, then sweep | |

**User's choice:** Fresh grid sweep on VN30

### Optimization objective

| Option | Description | Selected |
|--------|-------------|----------|
| Risk-adjusted return (Sharpe) | Maximize Sharpe ratio -- balances return and volatility | ✓ |
| Total return | Maximize total return -- simple but can overfit | |
| Drawdown-constrained return | Maximize return subject to max drawdown cap | |

**User's choice:** Risk-adjusted return (Sharpe)

### Framework reuse

| Option | Description | Selected |
|--------|-------------|----------|
| Adapt existing framework | Refactor parameter_sweep.py to accept scoring function | ✓ |
| New standalone sweep script | Build analysis/sweep_vn30.py from scratch | |

**User's choice:** Adapt existing framework

---

## Backtest Scope

### Date range

| Option | Description | Selected |
|--------|-------------|----------|
| Full available data (2014-2026) | Maximizes training data from vn30.csv | ✓ |
| 2019-2026 only | Align with post-2019 MDM v2 era | |
| 2017-2026 | Match NASDAQ backtest period | |

**User's choice:** Full available data

### Train/test split

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, 70/30 split | Train on first 70%, validate on last 30% | |
| No split, full-period sweep | Optimize over entire period | |
| Yes, pre/post-2020 split | Train pre-2020, test 2020-2026 (COVID regime shift) | ✓ |

**User's choice:** Pre/post-2020 split

### Baselines

| Option | Description | Selected |
|--------|-------------|----------|
| Buy-and-hold VN30 only | Simple, directly comparable | ✓ |
| Buy-and-hold + NASDAQ v2 params | Also show NASDAQ params on VN30 | |
| Buy-and-hold + VSA baseline | Include VSA strategy results | |

**User's choice:** Buy-and-hold VN30 only

---

## Claude's Discretion

- Exact parameter grid ranges and step sizes
- VN30 backtest report format and chart layout
- Internal implementation of vn30_filters.py
- Edge case handling in expiry date computation

## Deferred Ideas

None -- discussion stayed within phase scope
