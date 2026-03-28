# MDM Reverse-Engineering & VN30 Market Timing

## What This Is

A research and trading system project to reverse-engineer Dr. K's post-2019 Market Direction Model (MDM) by analyzing public signal history against NASDAQ/S&P500 price data, then adapt and apply the discovered rules to Vietnam's VN30 index. The project also maintains a separate VSA (Volume Spread Analysis) strategy as an independent trading system.

## Core Value

Accurately reverse-engineer the post-2019 MDM logic so that backtested signals match Dr. K's published signal history — this is the foundation everything else depends on.

## Requirements

### Validated

- ✓ MDM original rules (pre-2019) implemented — existing `models/` package
- ✓ VSA strategy implemented — existing `vn30_vsa/` package
- ✓ Backtesting infrastructure — `run_backtest.py`, performance tracking
- ✓ Data loaders for VN30, NASDAQ, S&P500 — CSV format with OHLCV
- ✓ Kelly Criterion position management — existing implementation

### Active

- [x] Reorganize codebase into clearly separated strategies (MDM classic, MDM v2, VSA) — Validated in Phase 2: Codebase Organization
- [x] Normalize US market data (NASDAQ/S&P500 prices appear scaled by ~1000x) — Validated in Phase 1: Data Integrity
- [x] Run MDM classic rules on NASDAQ data and compare with published signals — Validated in Phase 3: Signal Divergence Analysis
- [x] Identify divergence points between classic rules output and actual post-2019 signals — Validated in Phase 3: Signal Divergence Analysis
- [ ] Analyze signal patterns to hypothesize new MDM v2 rules (Cash state behavior, faster signal switching, modified DD counting)
- [ ] Implement MDM v2 candidate rules
- [ ] Validate MDM v2 against published signal history (target: high match rate)
- [ ] Adapt MDM v2 parameters for VN30 market characteristics
- [ ] Backtest MDM v2 on VN30 with performance reporting

### Out of Scope

- Real-time trading or live signal generation — this is research/backtesting only
- Recreating the exact proprietary model — we're approximating based on public data
- Web scraping or automated data collection from Dr. K's website
- Options or derivatives strategies beyond basic long/short/cash
- Mobile app or web UI — command-line/notebook analysis only

## Context

**Dr. K's MDM history:**
- Original model dates back to ~2000, based on IBD/O'Neil methodology (Follow-Through Days, Distribution Days, Rally Attempts)
- Material change made Feb 9, 2019 that significantly improved performance
- Model trades NASDAQ Composite and leveraged ETF TECL
- Three signals: Buy (long), Sell (short), Cash (flat)
- Published signal history available from 2017-2026 on virtueofselfishinvesting.com

**Key observations about post-2019 behavior:**
1. Cash state appears between Buy and Sell — original rules don't have this intermediate state
2. Signal switching is much faster (sometimes same-day Buy→Cash)
3. Sell signals appear to trigger without full 5-DD accumulation
4. Model appears more responsive to short-term price action

**Existing codebase:**
- `strategies/mdm_classic/` — MDM classic implementation (migrated from `models/`)
- `strategies/vsa/` — Independent VSA strategy (migrated from `vn30_vsa/`)
- `scripts/` — Entry-point scripts (`run_backtest.py`, `optimize_mdm.py`, `check_date.py`)
- `analysis/` — Analysis tools (`analyze_drawdown.py`, `diagnose_vn30.py`)
- `data/` — NASDAQ, S&P500, VN30 OHLCV data
- Data format: US data normalized (Phase 1), VN30 data is native scale

**Published signal data (embedded in project):**
- TECL signals: 2017-01-30 to 2026-02-26 (100+ signals)
- NASDAQ Composite signals: same period
- Both include Buy/Sell/Cash with % gain/loss per trade

## Constraints

- **Data**: US market data prices appear to be scaled by ~1000x — must normalize before analysis
- **Validation**: Can only validate against publicly delayed signals (up to 2 months delay for non-members)
- **VN30 adaptation**: Vietnamese market has different microstructure (T+2.5 settlement, 7% price limit, derivative expiry effects)
- **Scope**: The reverse-engineered model will be an approximation — exact replication is unlikely without proprietary knowledge

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep VSA as separate strategy | User preference — independent trading system, not a filter for MDM | — Pending |
| Combined approach for reverse-engineering | Run classic rules + analyze patterns simultaneously for best coverage | — Pending |
| NASDAQ as primary validation index | Dr. K's model trades NASDAQ Composite; TECL is just leveraged exposure | — Pending |
| Organize strategies into separate packages | Clean separation enables independent development and testing | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-28 after Phase 3 completion*
