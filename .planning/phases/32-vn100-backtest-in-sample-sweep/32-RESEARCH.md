# Phase 32: VN100 Backtest + In-Sample Sweep — Research

**Researched:** 2026-04-09
**Domain:** End-to-end backtest pipeline wiring + 1,536-config parameter sweep on VN100 2014-2018
**Confidence:** HIGH (all upstream code locked; pattern precedent exists in repo)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Universe (in-sample):**
- D-01: Universe = **current-VN100** (Phase 29 mode `current`). Survivorship bias accepted; sensitivity deferred to Phase 33.
- D-02: Semi-annual rebalance Jan/Jul (Phase 29 UNIV-02), no override.

**Sweep grid (exact, no extra dimensions):**
- D-03: `c_yoy ∈ {0.10, 0.15, 0.20, 0.25}` × `a_cagr ∈ {0.10, 0.15, 0.20, 0.25}` × `n_proximity ∈ {0.05, 0.10, 0.15, 0.20}` × `hard_stop ∈ {0.06, 0.07, 0.08, 0.10}` × `slots ∈ {5, 8, 10}` × `entry_option ∈ {A, C}` = **1,536 configs**. NO `union` entry mode.
- D-04: Locked (NOT swept): MDM gate = HybridEngine v6, costs 0.25%+0.10%+0.10%, cooldown 5d, ADV20>10×, exit priority chain, RS=70/5d, MA50 trail vol 1.25×.

**Runtime strategy:**
- D-05: Partial precompute → cache to `docs/audits/phase32/cache/`: VN100 membership timeline, raw EPS/price/volume/foreign, MDM gate state series, adjusted OHLC. Re-compute per config: CANSLIM mask, entry fills, portfolio run.
- D-06: `multiprocessing.Pool(cpu_count()-1)`. 1 worker = 1 config → metrics dict → aggregate DataFrame.
- D-07: Progress via tqdm or print/50. Fail-loud per-config (log + continue, do not abort sweep). Report crash count at end.

**Scripts:**
- D-08: Two scripts — `analysis/backtest_vn100.py` (single-run debug, SC1) and `analysis/sweep_vn100.py` (full grid).
- D-09: Period **2014-01-01 → 2018-12-31 hard-coded**, no CLI date overrides.

**Sharpe + selection:**
- D-10: Sharpe = `(annualized_return - 0.03) / annualized_vol`, vol = daily_returns × √252, rf = 3%.
- D-11: Top-3 = sort by Sharpe desc, take 3. No secondary filters (no CAGR floor, no MaxDD ceiling).
- D-12: Tie-breaker: higher CAGR → lower MaxDD.

**Sanity gate:**
- D-13: `>300% CAGR` = soft-flag column `sanity_flag` (`OK` / `CAGR_TOO_HIGH`). Sweep continues. If any top-3 row flagged → abort + manual review.

**Handoff:**
- D-14: `docs/audits/phase32/locked_params_top3.json` with `selected_at`, `selection_metric`, `period`, `universe`, `configs[{rank, params, metrics}]`.
- D-15: Phase 33 builds the loader helper, NOT Phase 32.

**Output artifacts (D-16):**
- `docs/audits/phase32-backtest-sweep.md` (report)
- `docs/audits/phase32/single_run_nav.csv`, `single_run_trades.csv`, `single_run_positions.csv`
- `docs/audits/phase32/sweep_results.csv` (1,536 rows)
- `docs/audits/phase32/locked_params_top3.json`
- `docs/audits/phase32/cache/` (gitignore if large)

**Metrics per config (D-17):** `CAGR, Sharpe_rf3, MaxDD, MaxDD_duration_days, hit_rate, turnover, total_cost_drag_pct, num_trades, avg_hold_days, sanity_flag`.

### Claude's Discretion
- Cache format (parquet/pickle/hdf5) + invalidation
- multiprocessing chunksize
- Crash log format
- joblib.Memory vs hand-rolled cache
- Report markdown layout (charts vs tables)
- Equity curve PNG for top-3 in report (optional)
- tqdm vs manual print

### Deferred Ideas (OUT OF SCOPE)
- OOS 2019-2025 + 3-universe sensitivity → Phase 33
- Liquidity-reconstructed in-sample rerun
- `entry_mode=union` sweep
- Cost sensitivity sweep → Phase 33
- Benchmarks + real CAGR → Phase 34
- Dashboard + `docs/rules_canslim_mdm.md` → Phase 34
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BT-01 | VN100 backtest engine wiring all layers (universe → CANSLIM → entry → portfolio → costs) | All upstream modules exist (`strategies/canslim/`, `strategies/entry/`, `strategies/portfolio/`, `connectors/`); only wiring needed. `analysis/backtest_vn100.py` realizes SC1. |
| BT-02 | In-sample 2014-2018 + parameter sweep (CANSLIM thresholds, entry option, stop, slots) | 1,536-config grid via `analysis/sweep_vn100.py`; multiprocessing pattern; precompute cache; top-3 by Sharpe → JSON for Phase 33. Realizes SC2–SC5. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **GSD enforcement:** all edits must occur via GSD workflow (this phase IS the workflow).
- **Code-Docs sync:** `docs/rules_canslim_mdm.md` does NOT need updating in Phase 32 (no logic change; only wiring + sweep). Phase 34 finalizes that doc.
- **`state[i-1]` discipline:** mandatory in any equity/NAV calculation to avoid look-ahead (the 707% bug). Phase 31 engine already enforces this; Phase 32 sweep metric code MUST also use it (see `feedback_equity_formula.md`, `analysis/sweep_vn30_params.py:32-38` precedent).
- **Adjusted OHLC only:** zero raw price reads — always go through `connectors/adjust.py::adjust_ohlc()`.
- **Naming:** snake_case modules, PascalCase classes, dataclass configs with `__post_init__` validation.
- **Strategy independence:** Phase 32 lives under `analysis/`, not under `strategies/` — it consumes engines, doesn't extend them.
- **Best VN30 model:** HybridEngine v6 (per `project_best_model.md`) is the MDM gate source — confirmed in Phase 31 D-07.

## Summary

Phase 32 is **integration + sweep, not new logic**. Every component (universe loader, CANSLIM scorer, entry detectors, portfolio engine, costs, MDM gate) is already locked from Phases 28–31. The work: write two analysis scripts that compose them, run a 1,536-config grid with multiprocessing + precompute caching, and emit a top-3 JSON for Phase 33 to load.

The single biggest risks are (1) **runtime** — naive serial sweep would take hours; partial precompute + multiprocessing is mandatory, (2) **look-ahead bugs** in metric computation — `state[i-1]` discipline is non-negotiable, and (3) **survivorship bias** — accepted by user, flagged in report, addressed in Phase 33.

**Primary recommendation:** Mirror `analysis/sweep_vn30_params.py` skeleton for grid + metrics; replace its serial loop with `multiprocessing.Pool.imap_unordered`; precompute the four heavy assets (universe membership, raw fundamentals, MDM gate series, adjusted OHLC) once into a parquet cache before forking workers; pass cache paths (not DataFrames) into worker function to avoid pickling overhead.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | ≥2.0 | DataFrames, time series, CSV/parquet I/O | Already project standard |
| numpy | ≥1.24 | Vectorized metrics (CAGR, Sharpe, drawdown) | Already project standard |
| pyarrow | (transitive via pandas) | Parquet cache backend | Fastest pandas-native columnar format; pickle is slower + version-fragile, hdf5 needs extra dep |
| multiprocessing (stdlib) | — | Parallel sweep workers | No new dependency; `Pool` is the documented pattern for CPU-bound grid search |
| tqdm | (already pulled in by jupyter ecosystem; check `uv pip list`) | Progress bar | Standard for sweeps; fall back to print/50 if missing |
| matplotlib | ≥3.7 | Equity curve PNG for top-3 (optional, D-discretion) | Already project standard |

### Supporting (already in repo, just import)
| Module | Purpose |
|--------|---------|
| `strategies/canslim/scorer.py` + `strategies/canslim/config.py` | Per-day CANSLIM mask; sweep mutates `c_yoy`, `a_cagr`, `n_proximity` via `CanslimConfig` |
| `strategies/canslim/universe.py` | VN100 membership semi-annual rebalance (UNIV-01/02) |
| `strategies/entry/engine.py` | EntryEngine producing Fill records; sweep mutates `option ∈ {A, C}` |
| `strategies/portfolio/engine.py` | PortfolioEngine (multi-stock state machine) |
| `strategies/portfolio/config.py` | PortfolioConfig — sweep mutates `hard_stop`, `slots` |
| `strategies/portfolio/ab_report.py` | CSV writers for trade/position/NAV (reuse for SC1 single-run output) |
| `strategies/mdm_hybrid/mdm_hybrid_engine.py` | HybridEngine v6 — run once on VN-Index for the period, feeds gate state |
| `connectors/postgres.py` | Load `stock_eod`, `stock_foreign_eod`, `stock_rs`, `index_eod` |
| `connectors/adjust.py::adjust_ohlc()` | Mandatory price/volume adjustment |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `multiprocessing.Pool` | `joblib.Parallel` | joblib has nicer caching (`Memory`) but adds dependency; user said discretion — Pool is zero-dep and matches stdlib precedent |
| parquet cache | pickle | Pickle is faster to write but version-brittle and opaque; parquet is inspectable + columnar |
| pandas-only metrics | empyrical / quantstats | Extra deps; we only need 5 metrics (Sharpe, CAGR, MaxDD, MaxDD duration, turnover) — trivial in numpy |
| Pool | concurrent.futures.ProcessPoolExecutor | Equivalent; Pool's `imap_unordered` is more idiomatic for "stream of independent tasks with progress" |

**Installation:** Nothing new required. Verify `pyarrow` and `tqdm` are available:
```bash
uv pip list | grep -iE "pyarrow|tqdm"
```
If `tqdm` is missing, fall back to `if i % 50 == 0: print(...)`. If `pyarrow` is missing, install via `uv pip install pyarrow` or fall back to pickle.

## Architecture Patterns

### Recommended Layout
```
analysis/
├── backtest_vn100.py        # SC1 single-run; default = Phase 31 defaults; period hard-coded
├── sweep_vn100.py           # SC2-SC5 full 1,536-config grid; multiprocessing
└── _vn100_pipeline.py       # SHARED helper module: precompute + run_one_config(cfg) -> metrics
docs/audits/phase32/
├── cache/                   # parquet precompute (gitignored if >50MB)
├── single_run_nav.csv
├── single_run_trades.csv
├── single_run_positions.csv
├── sweep_results.csv
└── locked_params_top3.json
docs/audits/phase32-backtest-sweep.md
```

The shared `_vn100_pipeline.py` is the **key abstraction**: both scripts import `run_one_config(canslim_cfg, portfolio_cfg, entry_option, precomputed)` so single-run and sweep cannot diverge. This eliminates the "single-run says X, sweep says Y" class of bug.

### Pattern 1: Precompute-then-fork
**What:** Compute heavy invariant data ONCE in main process, persist to parquet, then `Pool` workers re-load from disk.
**When to use:** Always when sweep size × precompute cost > sequential cost.
**Why disk not memory:** `multiprocessing.Pool` pickles arguments to workers. Passing 5 large DataFrames per task = massive serialization overhead. Workers re-reading from parquet (mmap'd by pyarrow) is faster and bounded by RAM.

```python
# Source: pattern; sweep_vn30_params.py uses serial loop, this is the multiproc adaptation
def precompute(period_start, period_end, cache_dir):
    cache_dir.mkdir(parents=True, exist_ok=True)
    universe = load_vn100_membership(period_start, period_end)
    universe.to_parquet(cache_dir / "universe.parquet")

    fundamentals = load_eps_fundamentals(universe.stockcode.unique(), period_start, period_end)
    fundamentals.to_parquet(cache_dir / "fundamentals.parquet")

    ohlc = adjust_ohlc(load_stock_eod(universe.stockcode.unique(), period_start, period_end))
    ohlc.to_parquet(cache_dir / "ohlc.parquet")

    foreign = load_stock_foreign_eod(...)
    foreign.to_parquet(cache_dir / "foreign.parquet")

    vnindex = load_index_eod("VNINDEX", period_start, period_end)
    mdm_state = HybridEngine(v6_config).run(vnindex)
    mdm_state.to_parquet(cache_dir / "mdm_gate.parquet")

    return cache_dir

def run_one_config(args):
    cache_dir, c_yoy, a_cagr, n_prox, hard_stop, slots, entry_opt = args
    # Re-load from parquet (fast, mmap'd)
    universe = pd.read_parquet(cache_dir / "universe.parquet")
    # ... etc
    canslim_cfg = CanslimConfig(c_yoy_threshold=c_yoy, a_cagr_threshold=a_cagr, n_proximity=n_prox)
    portfolio_cfg = PortfolioConfig(hard_stop_pct=hard_stop, max_slots=slots, ...)
    try:
        result = run_pipeline(canslim_cfg, portfolio_cfg, entry_opt, precomputed)
        metrics = compute_metrics(result.daily_nav)
        metrics.update({"c_yoy": c_yoy, "a_cagr": a_cagr, ..., "sanity_flag": "OK"})
        if metrics["CAGR"] > 300:
            metrics["sanity_flag"] = "CAGR_TOO_HIGH"
        return metrics
    except Exception as e:
        return {"c_yoy": c_yoy, ..., "error": repr(e), "sanity_flag": "CRASH"}

if __name__ == "__main__":
    cache_dir = precompute("2014-01-01", "2018-12-31", Path("docs/audits/phase32/cache"))
    grid = list(itertools.product(C_YOY, A_CAGR, N_PROX, HARD_STOP, SLOTS, ENTRY_OPT))
    args = [(cache_dir,) + g for g in grid]
    with Pool(cpu_count() - 1) as pool:
        results = list(tqdm(pool.imap_unordered(run_one_config, args, chunksize=4), total=len(args)))
    pd.DataFrame(results).to_csv("docs/audits/phase32/sweep_results.csv", index=False)
```

### Pattern 2: `state[i-1]` equity formula (MANDATORY)
**Source:** `analysis/sweep_vn30_params.py:32-38`, `feedback_equity_formula.md`
```python
eq = np.ones(n)
for i in range(1, n):
    if states[i - 1] == 'BUY':       # NOT states[i] — that's look-ahead
        eq[i] = eq[i - 1] * (closes[i] / closes[i - 1])
    elif states[i - 1] == 'SELL':
        eq[i] = eq[i - 1] * (closes[i - 1] / closes[i])
    else:
        eq[i] = eq[i - 1]
```
For Phase 32 the portfolio engine already produces `daily_nav`; metric code consumes it directly. The look-ahead risk lives in **how `daily_nav` is constructed inside Phase 31's PortfolioEngine** (already audited) and in **any post-hoc Sharpe/CAGR computation** the sweep does (must use the daily_nav as-is, not re-derive from positions).

### Pattern 3: Metric formulas
```python
def compute_metrics(daily_nav: pd.Series, trades: pd.DataFrame, period_start, period_end):
    daily_ret = daily_nav.pct_change().dropna()
    n_years = (period_end - period_start).days / 365.25
    cagr = (daily_nav.iloc[-1] / daily_nav.iloc[0]) ** (1 / n_years) - 1
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe_rf3 = (cagr - 0.03) / ann_vol if ann_vol > 0 else np.nan
    peak = daily_nav.cummax()
    dd = (daily_nav - peak) / peak
    max_dd = dd.min()
    # MaxDD duration = longest stretch where dd < 0
    in_dd = dd < 0
    max_dd_duration = max((sum(1 for _ in g) for k, g in itertools.groupby(in_dd) if k), default=0)
    hit_rate = (trades["pnl_pct"] > 0).mean() if len(trades) else np.nan
    avg_hold = trades["hold_days"].mean() if len(trades) else np.nan
    turnover = trades["notional"].sum() / daily_nav.mean() / n_years
    cost_drag = trades["total_cost"].sum() / daily_nav.iloc[0]
    return dict(CAGR=cagr*100, Sharpe_rf3=sharpe_rf3, MaxDD=max_dd*100,
                MaxDD_duration_days=max_dd_duration, hit_rate=hit_rate,
                turnover=turnover, total_cost_drag_pct=cost_drag*100,
                num_trades=len(trades), avg_hold_days=avg_hold)
```

### Anti-Patterns
- **Recomputing precompute inside workers** — defeats the purpose; verify by timing one worker call before parallelizing.
- **Passing DataFrames as Pool arguments** — pickling cost dominates; pass cache paths.
- **Re-deriving NAV from position log** — duplicates Phase 31 logic, risks divergence; consume the engine's `daily_nav` output.
- **Sweep abort on first crash** — D-07 forbids; wrap `run_one_config` in try/except per worker.
- **CLI date arguments in Phase 32 scripts** — D-09 forbids; period is hard-coded.
- **Adding `union` entry mode to grid** — D-03 forbids.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CANSLIM scoring | Re-implement C/A/N rules | `strategies/canslim/scorer.py` + `CanslimConfig` | Already locked, validated against `rank_top_stocks.diem_canslim` |
| Entry detection | New A/C detector | `strategies/entry/engine.py` with `option ∈ {A, C}` | Phase 30 deliverable |
| Portfolio state machine | New multi-stock loop | `strategies/portfolio/engine.py` | Phase 31, 28 locked decisions inside |
| Cost model | Manual commission/tax/slippage | `strategies/portfolio/costs.py` | Already wired; sweep doesn't change costs |
| OHLC adjustment | Manual split/div math | `connectors/adjust.py::adjust_ohlc()` | Single source of truth |
| MDM gate | New signal logic | `strategies/mdm_hybrid/mdm_hybrid_engine.py` (HybridEngine v6) | Best v6 model, locked in Phase 31 D-07 |
| Universe membership | Manual ticker list | `strategies/canslim/universe.py` mode `current` | Phase 29 UNIV-01/02 |
| Sharpe / drawdown | Pull empyrical | numpy 5-line implementation | 5 metrics, dependency-free |
| Process pool | Threading | `multiprocessing.Pool` | Sweep is CPU-bound; GIL kills threading |

## Common Pitfalls

### Pitfall 1: Pickling DataFrames into Pool workers
**What goes wrong:** Sweep starts but each task takes 30s+ even though logic is fast.
**Why:** Default `Pool.imap` pickles every argument per task. Passing a 200 MB OHLC DataFrame × 1,536 = TBs of pickle traffic.
**Avoid:** Pass **paths**, not DataFrames. Workers read parquet (mmap, near-instant).
**Warning sign:** CPU underutilization while disk/IPC is busy.

### Pitfall 2: Look-ahead in metric computation
**What goes wrong:** A config shows 700%+ CAGR.
**Why:** Equity uses today's state with today's return instead of yesterday's state.
**Avoid:** Trust the engine's `daily_nav` output (Phase 31 already enforces `state[i-1]`). Don't re-derive. Sanity flag (D-13) catches the symptom; rule prevents the cause.
**Warning sign:** sanity_flag column lights up; cross-check against single-run baseline NAV.

### Pitfall 3: Sweep abort on first config crash
**What goes wrong:** 1,400/1,536 configs lost because config #137 hit a divide-by-zero.
**Why:** Naive `pool.map` propagates exceptions and tears down the pool.
**Avoid:** Wrap entire `run_one_config` body in try/except returning a dict with `sanity_flag="CRASH"` and `error=repr(e)`. D-07 mandates this.
**Warning sign:** Crash count > 0 at sweep end — must be triaged before top-3 selection.

### Pitfall 4: Cache invalidation drift
**What goes wrong:** You edit a connector, re-run sweep, get stale results from old parquet.
**Avoid:** Cache filenames include data hash or git SHA; OR delete `cache/` at top of `precompute()` unless `--use-cache` flag passed. For Phase 32 simplicity: precompute always re-runs at script start (it's < 60s for 5 years × 100 stocks); cache is per-process, not persistent.

### Pitfall 5: Worker import side effects
**What goes wrong:** On Windows (this project's OS), `multiprocessing` uses spawn — workers re-import the module. If `analysis/sweep_vn100.py` does heavy work at import time, every worker pays the cost.
**Avoid:** Wrap entrypoint in `if __name__ == "__main__":`. Keep module-level code to imports + grid constants.

### Pitfall 6: Period boundary off-by-one
**What goes wrong:** Sweep includes 2019-01-02 bar → leaks OOS data into in-sample.
**Avoid:** Filter `df[df.tradingdate.between("2014-01-01", "2018-12-31")]` (inclusive both ends), assert `df.tradingdate.max() < pd.Timestamp("2019-01-01")` after load.

### Pitfall 7: Top-3 selection with NaN Sharpe
**What goes wrong:** A crashed config has Sharpe = NaN; pandas sort puts NaN last in some versions, top in others.
**Avoid:** `sweep_df.dropna(subset=["Sharpe_rf3"]).query("sanity_flag == 'OK'").sort_values("Sharpe_rf3", ascending=False).head(3)`.

## Runtime State Inventory

Not applicable — Phase 32 is greenfield script work + read-only data consumption. No rename, no migration.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All | ✓ | 3.10+ per pyproject | — |
| pandas ≥2.0 | All | ✓ | locked | — |
| numpy ≥1.24 | metrics | ✓ | locked | — |
| pyarrow | parquet cache | ⚠ verify | — | pickle (`df.to_pickle`) |
| tqdm | progress bar | ⚠ verify | — | `if i % 50 == 0: print(...)` |
| multiprocessing (stdlib) | sweep | ✓ | stdlib | — |
| Postgres connection (`vpt_wong_stock_v1`) | data load | ✓ verified Phase 28 | — | — |
| MySQL connection (`stocks_backend`) | EPS fundamentals | ✓ verified Phase 28 | — | — |
| matplotlib ≥3.7 | optional equity curve PNG | ✓ | locked | skip PNG |

**Verify before Wave 0:**
```bash
uv pip list | grep -iE "pyarrow|tqdm|pandas|numpy"
```

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** pyarrow → pickle; tqdm → print/50.

## Code Examples

### Loading universe + adjusted OHLC
```python
# Source: strategies/canslim/universe.py + connectors/adjust.py (Phase 29/28 patterns)
from strategies.canslim.universe import load_vn100_universe
from connectors.postgres import load_stock_eod
from connectors.adjust import adjust_ohlc

universe = load_vn100_universe(mode="current",
                               start="2014-01-01", end="2018-12-31",
                               rebalance="semi_annual_jan_jul")
tickers = universe.stockcode.unique()
raw = load_stock_eod(tickers, "2014-01-01", "2018-12-31")
ohlc = adjust_ohlc(raw)  # MANDATORY
```

### Building configs per sweep cell
```python
# Source: strategies/canslim/config.py + strategies/portfolio/config.py (Phase 29/31)
from strategies.canslim.config import CanslimConfig
from strategies.portfolio.config import PortfolioConfig
from strategies.entry.config import EntryConfig

canslim = CanslimConfig(
    c_yoy_threshold=c_yoy,
    a_cagr_threshold=a_cagr,
    n_proximity_pct=n_prox,
    # rest = Phase 29 defaults
)
portfolio = PortfolioConfig(
    hard_stop_pct=hard_stop,
    max_slots=slots,
    cooldown_days=5,
    commission_pct=0.0025,
    sell_tax_pct=0.0010,
    slippage_pct=0.0010,
    adv20_multiple=10,
    rs_threshold=70,
    rs_consecutive_days=5,
    ma50_trail_vol_mult=1.25,
    # rest = Phase 31 D-defaults
)
entry = EntryConfig(option=entry_option)  # 'A' or 'C'
```

### Single-run pipeline (SC1)
```python
# analysis/backtest_vn100.py — defaults = Phase 31 defaults; period hard-coded
def main():
    period = ("2014-01-01", "2018-12-31")
    pre = precompute(*period, Path("docs/audits/phase32/cache"))
    result = run_pipeline(
        CanslimConfig(),         # all defaults
        PortfolioConfig(),       # all defaults
        entry_option="A",
        precomputed=pre,
    )
    out = Path("docs/audits/phase32")
    result.daily_nav.to_csv(out / "single_run_nav.csv")
    result.trades.to_csv(out / "single_run_trades.csv", index=False)
    result.positions.to_csv(out / "single_run_positions.csv", index=False)
    print(compute_metrics(result.daily_nav, result.trades, *map(pd.Timestamp, period)))
```

### Sweep grid + parallelization (SC2)
See Pattern 1 example above.

### Top-3 selection + JSON emit (SC4)
```python
# In analysis/sweep_vn100.py after sweep_df built
ok = sweep_df.query("sanity_flag == 'OK'").dropna(subset=["Sharpe_rf3"])
top3 = ok.sort_values(
    ["Sharpe_rf3", "CAGR", "MaxDD"],
    ascending=[False, False, True],   # tie-breaker D-12
).head(3)

if (top3["sanity_flag"] != "OK").any():
    raise SystemExit("ABORT: top-3 contains flagged config — manual review required (D-13)")

payload = {
    "selected_at": dt.date.today().isoformat(),
    "selection_metric": "sharpe_rf3",
    "period": "2014-01-01..2018-12-31",
    "universe": "current-VN100",
    "configs": [
        {
            "rank": rank,
            "c_yoy": row.c_yoy, "a_cagr": row.a_cagr, "n_proximity": row.n_proximity,
            "hard_stop": row.hard_stop, "slots": row.slots, "entry_option": row.entry_option,
            "metrics": {
                "CAGR": row.CAGR, "Sharpe_rf3": row.Sharpe_rf3, "MaxDD": row.MaxDD,
                "MaxDD_duration_days": row.MaxDD_duration_days, "hit_rate": row.hit_rate,
                "turnover": row.turnover, "total_cost_drag_pct": row.total_cost_drag_pct,
                "num_trades": row.num_trades, "avg_hold_days": row.avg_hold_days,
            },
        }
        for rank, row in enumerate(top3.itertuples(), start=1)
    ],
}
Path("docs/audits/phase32/locked_params_top3.json").write_text(json.dumps(payload, indent=2))
```

## State of the Art

| Old Approach | Current Approach | When | Impact |
|--------------|------------------|------|--------|
| Serial sweep (`sweep_vn30_params.py`) | Multiprocessing Pool with precompute cache | Phase 32 introduces this pattern | First repo precedent for parallel sweep — set the bar carefully |
| Fresh recompute per config | Partial precompute (4 invariant assets cached, only CANSLIM/entry/portfolio re-run) | D-05 | Cuts per-config time by ~70-90% |

**No deprecations** — Phase 32 only consumes locked Phase 28-31 APIs.

## Open Questions

1. **Exact runtime budget for full sweep**
   - What we know: 1,536 configs, multi-core, partial precompute
   - What's unclear: Per-config wall-clock until measured
   - Recommendation: After single-run works, time it; estimate sweep = `single_run_seconds × 1536 / (cpu_count - 1)`. If > 2 hours, profile worker hot path before launching the full grid.

2. **Cache directory in git or gitignored?**
   - What we know: D-16 says "gitignore if dung lượng lớn"
   - Recommendation: Add `docs/audits/phase32/cache/` to `.gitignore`. Commit only the report + CSVs + JSON. Cache is reproducible.

3. **Equity curve PNGs for top-3 in report?**
   - Claude's discretion. Recommendation: include — the report consumer (Phase 33 planner + user) benefits from visual sanity check beyond the sanity_flag column. Cheap (matplotlib + 3 images).

4. **`tqdm` available?**
   - Verify in Wave 0 environment check; fall back to print/50 if missing.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (standard for repo, used in Phase 28-31) |
| Config file | None at repo root — convention is `tests/test_*.py`, runnable as `uv run pytest` |
| Quick run command | `uv run pytest tests/test_phase32_sweep.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| BT-01 | `analysis/backtest_vn100.py` runs end-to-end on a tiny fixture (3 stocks × 30 days) and emits non-empty trade/position/NAV CSVs | integration | `uv run pytest tests/test_phase32_pipeline.py::test_single_run_smoke -x` | ❌ Wave 0 |
| BT-01 | `_vn100_pipeline.run_pipeline` returns a result with `daily_nav`, `trades`, `positions` attributes | unit | `uv run pytest tests/test_phase32_pipeline.py::test_run_pipeline_contract -x` | ❌ Wave 0 |
| BT-01 | Adjusted OHLC is used (not raw) — verify `adjust_ohlc` is called in precompute | unit | `uv run pytest tests/test_phase32_pipeline.py::test_precompute_uses_adjusted_ohlc -x` | ❌ Wave 0 |
| BT-02 | `compute_metrics` produces all 10 columns (CAGR, Sharpe_rf3, MaxDD, MaxDD_duration_days, hit_rate, turnover, total_cost_drag_pct, num_trades, avg_hold_days, sanity_flag) | unit | `uv run pytest tests/test_phase32_metrics.py::test_metrics_schema -x` | ❌ Wave 0 |
| BT-02 | Sharpe formula uses rf=0.03 and √252 annualization (regression: pin a known input → known output) | unit | `uv run pytest tests/test_phase32_metrics.py::test_sharpe_rf3_formula -x` | ❌ Wave 0 |
| BT-02 | sanity_flag = `CAGR_TOO_HIGH` when CAGR > 300, else `OK` | unit | `uv run pytest tests/test_phase32_metrics.py::test_sanity_flag -x` | ❌ Wave 0 |
| BT-02 | Top-3 selection: sort by Sharpe desc, tie-breaker CAGR desc → MaxDD asc | unit | `uv run pytest tests/test_phase32_selection.py::test_top3_tiebreaker -x` | ❌ Wave 0 |
| BT-02 | Top-3 selection aborts if any selected row has sanity_flag != OK | unit | `uv run pytest tests/test_phase32_selection.py::test_top3_abort_on_flag -x` | ❌ Wave 0 |
| BT-02 | Locked-params JSON schema matches D-14 (selected_at, selection_metric, period, universe, configs[3] with rank+params+metrics) | unit | `uv run pytest tests/test_phase32_selection.py::test_locked_params_json_schema -x` | ❌ Wave 0 |
| BT-02 | Sweep grid enumerator yields exactly 1,536 unique configs | unit | `uv run pytest tests/test_phase32_sweep.py::test_grid_size -x` | ❌ Wave 0 |
| BT-02 | Worker `run_one_config` returns dict on exception (does not raise) | unit | `uv run pytest tests/test_phase32_sweep.py::test_worker_swallows_exceptions -x` | ❌ Wave 0 |
| BT-02 (manual) | Full 1,536 sweep on real data 2014-2018 produces sweep_results.csv with 1,536 rows | manual | `uv run python analysis/sweep_vn100.py` then check row count | manual — too long for CI |
| BT-01 (manual) | Single-run on real data 2014-2018 produces non-empty CSVs and plausible equity curve | manual | `uv run python analysis/backtest_vn100.py` | manual — needs DB |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_phase32_pipeline.py tests/test_phase32_metrics.py tests/test_phase32_selection.py tests/test_phase32_sweep.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full unit suite green; manual single-run + manual sweep executed and outputs spot-checked before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_phase32_pipeline.py` — pipeline contract + smoke (BT-01)
- [ ] `tests/test_phase32_metrics.py` — metric formulas + sanity flag (BT-02)
- [ ] `tests/test_phase32_selection.py` — top-3 + tie-breaker + JSON schema (BT-02)
- [ ] `tests/test_phase32_sweep.py` — grid size + worker exception handling (BT-02)
- [ ] `tests/fixtures/phase32_tiny_universe.parquet` — 3 stocks × 30 days fixture for smoke test
- [ ] Verify pyarrow + tqdm installed (Wave 0 env check)

## Sources

### Primary (HIGH confidence)
- `.planning/phases/32-vn100-backtest-in-sample-sweep/32-CONTEXT.md` — all D-01..D-17 decisions
- `.planning/REQUIREMENTS.md` BT-01, BT-02
- `.planning/ROADMAP.md` Phase 32 (lines 594-605) — SC1-SC5
- `analysis/sweep_vn30_params.py` — repo precedent for grid sweep + `state[i-1]` equity formula
- `strategies/portfolio/`, `strategies/canslim/`, `strategies/entry/`, `strategies/mdm_hybrid/` — locked upstream APIs
- `connectors/adjust.py`, `connectors/postgres.py` — data layer
- `c:/Users/trant/projects/mdm/CLAUDE.md` — project conventions, code-docs sync, GSD enforcement
- Auto-memory: `feedback_equity_formula.md` (look-ahead rule), `project_best_model.md` (HybridEngine v6 = MDM gate)

### Secondary
- Python stdlib `multiprocessing.Pool` documentation pattern (well-known, no citation needed)

### Tertiary
- None — phase is purely integration of locked components.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in repo, no new deps
- Architecture: HIGH — pattern is documented in upstream phases + sweep_vn30_params.py precedent
- Pitfalls: HIGH — `state[i-1]` and Pool pickling pitfalls are project-known (memory entries)
- Validation map: HIGH — requirements are narrow (BT-01, BT-02) and testable

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 days; phase will execute imminently)
