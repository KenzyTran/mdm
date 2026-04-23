# MDM Reverse-Engineering & VN30 Market Timing

This repository reverse-engineers Dr. K's post-2019 Market Direction Model (MDM) from a public 962-signal NASDAQ history spanning 1974-2026, then adapts the discovered rules to time Vietnam's VN30 index. The VN30 timing layer is further composed with a CANSLIM-style stock screen on VN100 to drive a long-only multi-stock portfolio. A separate Volume Spread Analysis (VSA) strategy is maintained in parallel as an independent research track. Everything here is backtest / research code: there is no live execution path, no broker integration, and no real-time signal generation. The goal is a faithful approximation of Dr. K's logic — exact replication is not a goal given the proprietary nature of the published model.

## Current Production Model

The production baseline on VN30 (2015-2026) is **v6.0 HybridEngine + fail-safe**: total return **+238.8%**, **CAGR 11.5%**, **MaxDD −28.2%**. This is the engine every newer milestone (v7.0, v8.0, v9.0, v10.0) is measured against.

A companion stack, **v7.0 CANSLIM + MDM gate**, runs on the VN100 universe and operates as a multi-stock long-only portfolio with the v6.0 engine acting as the market-direction filter. Out-of-sample (2019-2025) it delivers CAGR 10.18%, Sharpe_rf3 0.813, MaxDD −16.31%. See [docs/strategy_v7.md](docs/strategy_v7.md) for the full v7.0 spec and [docs/portfolio_system_overview.md](docs/portfolio_system_overview.md) for the end-to-end signal-to-portfolio flow.

The v6.0 engine's rule set is documented in [docs/rules_mdm_hybrid.md](docs/rules_mdm_hybrid.md).

## Milestone History

| Milestone   | Scope                                                                         | Status                              | Key result                                                                        |
| ----------- | ----------------------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------- |
| v1.0 - v5.0 | Foundation: reverse-engineering pipeline, Hybrid engine, QE / banding filters | SHIPPED                             | 962-signal dataset + Propose-Filter-Decide pipeline                               |
| v6.0        | Fail-safe + signal refinement on VN30                                         | SHIPPED (production)                | +238.8% / CAGR 11.5% / MaxDD −28.2% (2015-2026)                                   |
| v7.0        | CANSLIM + MDM gate on VN100 portfolio                                         | SHIPPED                             | OOS CAGR 10.18%, Sharpe 0.813, MaxDD −16.31% (2019-2025)                          |
| v8.0        | RS Momentum stock selection on VN100                                          | REJECTED                            | OOS Sharpe 0.645 trails v7.0 (0.813)                                              |
| v9.0        | VN30 whipsaw reduction (ATR Buffer + Refined DD)                              | REJECTED                            | Walk-forward degradation +67% to +96%; v6.0 retained                              |
| v10.0       | VN macro filter (DXY / EEM / SBV) + walk-forward grid                         | IN PROGRESS (retain-v6.0 branch)    | 0/39 combos accepted in Phase 45 grid; v6.0 retained for Phase 46                 |

## Quick Start

Python 3.10+ and the [uv](https://docs.astral.sh/uv/) package manager are required. All dependencies and the Python floor are declared in `pyproject.toml`.

```
uv sync
uv run python scripts/run_backtest.py           # MDM classic on NASDAQ
uv run python scripts/run_hybrid_backtest.py    # v6.0 HybridEngine
```

Inputs are CSV OHLCV panels (VN30, NASDAQ, S&P500, signals, liquidity proxies) located under `data/`. Column contracts, connector schemas, and adjustment helpers are specified in [docs/data_dictionary.md](docs/data_dictionary.md).

## Repo Layout

- `strategies/` — per-strategy subpackages: `mdm_classic`, `mdm_v2`, `mdm_hybrid`, `vsa`, `canslim`, `entry`, `portfolio`, `momentum`.
- `core/` — indicator engine, data loader, feature-snapshot helpers shared across strategies.
- `analysis/` — hypothesis testing, rule discovery, A/B and walk-forward validators.
- `connectors/` — Postgres (TA) and MySQL (fundamentals) connectors used by the v7.0 VN100 stack.
- `scripts/` — entry-point scripts (backtests, diagnostics, dashboard exports).
- `tests/` — pytest suite; regression tests are marked `@pytest.mark.regression`.
- `data/` — CSV inputs (VN30, NASDAQ, S&P500, MDM signals, VN liquidity proxies, SBV events).
- `output/` — generated reports, equity curves, grid-sweep results, reconciled-baseline artifacts.
- `docs/` — human-facing specs: `rules_mdm_classic.md`, `rules_mdm_v2.md`, `rules_mdm_hybrid.md`, `rules_vsa.md`, `rules_canslim.md`, `rules_canslim_mdm.md`, `rules_entry.md`, plus system overviews.
- `.planning/` — planning & milestone artifacts (internal workflow metadata).

Per-strategy trading rules live under `docs/rules_*.md` and MUST stay in sync with code changes in the corresponding `strategies/` package (see `CLAUDE.md` Code-Docs Sync Rule).

## Constraints

- Research & backtest only — no live trading, no real-time signal generation, no broker or execution adapters.
- US market OHLCV (NASDAQ, S&P500) is scaled ~1000x at source and normalized inside the loader before any indicator or signal runs against it.
- VN30 microstructure: T+2.5 settlement, 7% daily price limit, derivative expiry effects — reflected in the portfolio engine's fill logic and stop placement.
- Signal validation uses publicly delayed Dr. K history (up to 2 months lag for non-members); exact replication of the proprietary model is not a goal.

## Further Reading

- [docs/portfolio_system_overview.md](docs/portfolio_system_overview.md) — end-to-end signal-to-portfolio flow diagram.
- [docs/strategy_v7.md](docs/strategy_v7.md) — v7.0 CANSLIM + MDM + RS partial-liquidation spec.
- [docs/data_dictionary.md](docs/data_dictionary.md) — connector schemas, CANSLIM column contracts, adjustment helpers.
- [docs/rules_mdm_hybrid.md](docs/rules_mdm_hybrid.md) — v6.0 HybridEngine production rules.
- [docs/rules_vsa.md](docs/rules_vsa.md) — independent VSA strategy (maintained separately from MDM).

*Last updated: 2026-04-23*
