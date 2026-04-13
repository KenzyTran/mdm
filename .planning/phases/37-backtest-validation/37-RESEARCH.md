# Phase 37: Backtest & Validation - Research

**Researched:** 2026-04-13
**Domain:** VN100 backtest pipeline, RS formula sweep, OOS validation, v7.0 vs v8.0 comparison
**Confidence:** HIGH (all findings from direct codebase inspection)

## Summary

Phase 37 is the final validation gate for v8.0. It runs an in-sample sweep (2016-2018) to pick the best RS formula between IBD Weighted ROC and ROC-126, then validates OOS (2019-2025) and compares against v7.0 baseline. All required infrastructure already exists: `run_v8_backtest` is live in `analysis/_vn100_pipeline.py`, both RS formulas are implemented in `strategies/momentum/rs.py`, and the sweep pattern (multiprocessing, parquet caching, CSV output) is established by Phase 32's `analysis/sweep_vn100.py`.

The phase has a narrow, well-defined parameter space: 2 RS formulas x 2 entry options x N threshold combos = small grid (compared to Phase 32's 1,536). The critical design decision is what threshold grid to sweep on `rs_threshold` and `n_within_high`, since those are the only free parameters for v8.0 (unlike v7.0 which swept c_yoy/a_cagr/n_proximity/hard_stop/slots).

**Primary recommendation:** Copy the sweep pattern from `analysis/sweep_vn100.py`, replace `CanslimConfig` with `MomentumScorerConfig`, set `PERIOD = ("2016-01-01", "2018-12-31")`, and output a comparison table with the locked v7.0 baseline numbers.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BT-01 | In-sample sweep 2016-2018 comparing IBD Weighted ROC vs ROC-126, select better formula | `run_v8_backtest` + `build_momentum_raw_frame` support both formulas via `MomentumScorerConfig`; sweep pattern from `sweep_vn100.py` |
| BT-02 | OOS 2019-2025 with formula selected from in-sample | Same `run_v8_backtest` call with `PERIOD = ("2019-01-01", "2025-12-31")` — same as `backtest_vn100_oos.py` pattern |
| BT-03 | Compare v8.0 vs v7.0 baseline (CAGR=10.18%, Sharpe_rf3=0.813, MaxDD=-16.31%) and VN-Index B&H | Baseline numbers confirmed in `docs/audits/phase33/oos_metrics.json` and `baselines.json` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0.0 | DataFrame ops, parquet read/write, result aggregation | Already used throughout |
| numpy | >= 1.24.0 | Metric computation (CAGR, Sharpe, MaxDD) | Already used |
| multiprocessing.Pool | stdlib | Parallel sweep workers | Pattern established in sweep_vn100.py |
| itertools.product | stdlib | Cartesian product for param grid | Pattern established |
| pathlib.Path | stdlib | File paths for output CSV/JSON | Pattern established |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tqdm | any | Progress bar for sweep | Already used in sweep_vn100.py — soft dep, falls back if absent |
| json | stdlib | Write metrics JSON | OOS metrics output |

**Installation:** No new dependencies needed. All are already in the project.

## Architecture Patterns

### Recommended Project Structure
```
analysis/
├── sweep_vn100_v8.py         # BT-01: in-sample sweep for RS formula selection
├── backtest_vn100_v8_oos.py  # BT-02: OOS validation with locked formula
└── _vn100_pipeline.py        # existing — run_v8_backtest + run_vn100_backtest

docs/audits/phase37/
├── sweep_v8_results.csv      # BT-01 output
├── locked_params_v8.json     # best config from in-sample
├── oos_metrics_v8.json       # BT-02 OOS metrics
├── oos_nav_v8.csv            # BT-02 NAV series
├── oos_trades_v8.csv         # BT-02 trade log
└── comparison_table.json     # BT-03 v8.0 vs v7.0 vs VN-Index B&H
```

### Pattern 1: v8.0 Sweep Script (`sweep_vn100_v8.py`)

The Phase 32 sweep script (`analysis/sweep_vn100.py`) is the direct template. The only changes needed are:

1. Replace `CanslimConfig` with `MomentumScorerConfig`
2. Replace `run_vn100_backtest` with `run_v8_backtest`
3. Update `PERIOD` to `("2016-01-01", "2018-12-31")`
4. Update `GRID` to v8.0 parameter space (see Parameter Space section)
5. Update `GRID_COLS` and `OUTPUT_CSV`

```python
# Source: analysis/sweep_vn100.py (direct model)
from analysis._vn100_pipeline import run_v8_backtest, precompute_static
from strategies.momentum.scorer_config import MomentumScorerConfig
from strategies.portfolio.config import PortfolioConfig

PERIOD: Tuple[str, str] = ("2016-01-01", "2018-12-31")

GRID: Dict[str, List[Any]] = {
    "rs_formula":    ["weighted_roc", "roc126"],
    "rs_threshold":  [60.0, 70.0, 80.0],
    "n_within_high": [0.10, 0.15, 0.20],
    "hard_stop":     [0.06, 0.07, 0.08],
    "slots":         [5, 8],
    "entry_option":  ["A", "C"],
}
# Total: 2 * 3 * 3 * 3 * 2 * 2 = 216 configs

def _worker(args):
    config, _precomputed = args
    momentum_cfg = MomentumScorerConfig(
        rs_threshold=float(config["rs_threshold"]),
        n_within_high=float(config["n_within_high"]),
    )
    portfolio_cfg = PortfolioConfig(
        max_slots=int(config["slots"]),
        hard_stop_pct=float(config["hard_stop"]),
    )
    result = run_v8_backtest(
        momentum_cfg,
        portfolio_cfg,
        config["entry_option"],
        PERIOD,
        precomputed=None,
    )
    metrics = result["metrics"]
    row = {**config, **{k: metrics.get(k, float("nan")) for k in METRIC_COLS}}
    ...
```

**Critical:** `run_v8_backtest` uses `build_momentum_raw_frame` which computes the IBD Weighted ROC formula internally. To test `roc126`, the formula needs to be passed through — see Formula Selection section below.

### Pattern 2: RS Formula Selection Issue

**Important finding:** `build_momentum_raw_frame` in `_vn100_pipeline.py` (lines 785-860) hardcodes the IBD Weighted ROC formula — it always uses `{63: 0.4, 126: 0.2, 189: 0.2, 252: 0.2}`. There is NO formula parameter passed through to it.

The `compute_rs_panel` function in `strategies/momentum/rs.py` accepts a `formula` argument ("weighted_roc" or "roc126"), but `build_momentum_raw_frame` does NOT expose this parameter.

**Consequence for BT-01:** To sweep RS formulas, `run_v8_backtest` must either:
- Accept a `formula` parameter and pass it down to `build_momentum_raw_frame`, OR
- Accept a pre-built `momentum_raw` frame in `precomputed` dict (already supported — line 513)

**Recommended approach:** Pre-build the raw frame for each formula using `get_rs_rankings` / `compute_rs_panel`, then inject via `precomputed["momentum_raw"]`. Alternatively, add a `formula` parameter to `build_momentum_raw_frame`. The precomputed injection path is already coded and tested.

```python
# Inject pre-built raw frame to test roc126:
from strategies.momentum.rs import get_rs_rankings

rs_roc126 = get_rs_rankings("roc126", period, mode="current-vn100")
# rs_roc126 has columns [date, ticker, rs_raw, rs_rank]
# rename rs_rank -> rs_rating, add n_prox from panel
```

However, `build_momentum_raw_frame` computes n_prox internally (the 252-day rolling high proximity). So the cleanest approach is to add a `formula` kwarg to `build_momentum_raw_frame` or call `build_momentum_raw_frame` once for n_prox, then patch in the formula-specific `rs_rating`. This is a small code change needed in `_vn100_pipeline.py` — the planner must include it as a Wave 0 task.

### Pattern 3: OOS Validation (`backtest_vn100_v8_oos.py`)

```python
# Source: analysis/backtest_vn100_oos.py (direct model)
from analysis._vn100_pipeline import run_v8_backtest
from strategies.momentum.scorer_config import MomentumScorerConfig
from strategies.portfolio.config import PortfolioConfig

PERIOD = ("2019-01-01", "2025-12-31")
OUT_DIR = Path("docs/audits/phase37")

# Load best config from sweep
with open("docs/audits/phase37/locked_params_v8.json") as f:
    best = json.load(f)

momentum_cfg = MomentumScorerConfig(
    rs_threshold=best["rs_threshold"],
    n_within_high=best["n_within_high"],
)
portfolio_cfg = PortfolioConfig(
    max_slots=best["slots"],
    hard_stop_pct=best["hard_stop"],
)
result = run_v8_backtest(momentum_cfg, portfolio_cfg, best["entry_option"], PERIOD)
```

### Pattern 4: Comparison Table (BT-03)

The locked baseline numbers from Phase 33 are confirmed in code:

```python
# Source: docs/audits/phase33/oos_metrics.json (verified 2026-04-13)
V7_BASELINE = {
    "CAGR": 0.10182,        # 10.18%
    "Sharpe_rf3": 0.81335,  # 0.813
    "MaxDD": -0.16309,      # -16.31%
    "num_trades": 59,
    "avg_hold_days": 41.25,
}

# Source: docs/audits/phase33/baselines.json
VNINDEX_BH = {
    "CAGR": 0.10421,        # 10.42%
    "Sharpe_rf3": 0.38349,  # 0.383
    "MaxDD": -0.40343,      # -40.34%
}
```

Comparison table format:

| Metric | v7.0 (CANSLIM+MDM) | v8.0 (RS+N+MDM) | VN-Index B&H |
|--------|-------------------|-----------------|--------------|
| CAGR | 10.18% | TBD | 10.42% |
| Sharpe_rf3 | 0.813 | TBD | 0.383 |
| MaxDD | -16.31% | TBD | -40.34% |
| num_trades | 59 | TBD | — |
| avg_hold_days | 41.25 | TBD | — |

### Anti-Patterns to Avoid

- **Sharing precomputed between in-sample and OOS:** `precompute_static` caches by (mode, start, end). Different periods use different cache files — no contamination.
- **Using `run_vn100_backtest` for v8.0:** v7.0 function requires `fundamentals` key (MySQL). Use `run_v8_backtest` which only requires `universe/ohlc/mdm_gate`.
- **Passing `formula` to `run_v8_backtest` before fixing `build_momentum_raw_frame`:** Currently the function hardcodes IBD Weighted ROC. This must be fixed before BT-01 can run both formulas.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel sweep | Custom threading | `multiprocessing.Pool` | Already pattern in sweep_vn100.py; handles Windows spawn, pickling |
| Parquet caching | Custom CSV caching | `pandas.to_parquet / read_parquet` | Already used; schema-stable, fast |
| Metric computation | Custom Sharpe/CAGR | `_compute_metrics()` in `_vn100_pipeline.py` | Already handles rf=3%, MaxDD duration, Sharpe_rf3 — the locked metric definitions |
| RS computation | New RS logic | `build_momentum_raw_frame()` or `compute_rs_panel()` | Already implemented with both formulas |

**Key insight:** Phase 37 is glue code — assembling existing functions. No new mathematical logic is needed.

## Common Pitfalls

### Pitfall 1: Formula Parameter Gap in `build_momentum_raw_frame`
**What goes wrong:** `build_momentum_raw_frame` always uses IBD Weighted ROC. Running a sweep that sets `rs_formula = "roc126"` will silently run IBD Weighted ROC for both formula variants, producing identical results.
**Why it happens:** `run_v8_backtest` calls `build_momentum_raw_frame(panel)` with no formula argument; the function hardcodes `{63: 0.4, 126: 0.2, 189: 0.2, 252: 0.2}` weights.
**How to avoid:** Add `formula: str = "weighted_roc"` parameter to `build_momentum_raw_frame` and wire it through. This is a ~10-line change. Must be done before the sweep script.
**Warning signs:** Both formula variants producing identical CAGR/Sharpe in sweep output CSV.

### Pitfall 2: In-sample Period Cache Collision with v7.0
**What goes wrong:** Phase 32 cached `canslim_raw_2014-01-02_2018-12-31.parquet`. If Phase 37 uses period `("2016-01-01", "2018-12-31")`, the cache key `momentum_raw_2016-01-01_2018-12-31.parquet` is new and won't collide. But if the sweep period starts at a different date than the DB precompute (which fetches a 400-day warm-up), the cache dates in the parquet filename may differ from `panel["date"].min()`.
**Why it happens:** `build_momentum_raw_frame` uses `panel["date"].min()` as cache key, not the requested `period[0]`. The actual panel start date (first trading date after 2016-01-01) will be used.
**How to avoid:** Run `precompute_static(("2016-01-01", "2018-12-31"))` first to prime the ohlc cache. Then let `run_v8_backtest` compute the raw frame — it will cache to `momentum_raw_{actual_start}_{actual_end}.parquet`.

### Pitfall 3: `precomputed["fundamentals"]` Not Required but Triggers Warning
**What goes wrong:** If `precomputed` from `precompute_static` is passed to `run_v8_backtest`, the `fundamentals` key IS present (precompute_static always loads it). This is fine — v8 ignores it.
**Why it happens:** `precompute_static` always fetches fundamentals for v7.0 compatibility.
**How to avoid:** No action needed — v8 explicitly skips the fundamentals check.

### Pitfall 4: In-sample Period Start (2016 vs 2014)
**What goes wrong:** Phase 32 used 2014-2018 in-sample. Phase 37 uses 2016-2018. The VN100 universe may differ. The `precompute_static` call will re-fetch from DB (no 2016 cache exists).
**Why it happens:** New period = new cache files.
**How to avoid:** Run `precompute_static(("2016-01-01", "2018-12-31"))` once to prime cache before spawning workers.

### Pitfall 5: `MomentumScorerConfig.min_history_days` Not Swept
**What goes wrong:** Treating `min_history_days` as a free sweep parameter. It controls RS warm-up only, not the model behavior.
**Why it happens:** It looks like a threshold parameter.
**How to avoid:** Keep at default 252. Only sweep `rs_threshold` and `n_within_high`.

## API Signatures (Complete Reference)

### `run_v8_backtest`
```python
# Source: analysis/_vn100_pipeline.py lines 440-569
def run_v8_backtest(
    momentum_cfg: MomentumScorerConfig,
    portfolio_cfg: PortfolioConfig,
    entry_option: str,           # "A" or "C"
    period: Tuple[str, str],     # ("YYYY-MM-DD", "YYYY-MM-DD")
    precomputed: Optional[Mapping[str, Any]] = None,
    entry_cfg=None,              # optional EntryConfig override
) -> Dict[str, Any]:
    # Returns: {"metrics": {...}, "nav": DataFrame, "trades": DataFrame, "positions": DataFrame}
    # precomputed required keys: "universe", "ohlc", "mdm_gate"
    # precomputed optional keys: "momentum_raw" (pre-built raw frame), "rs", "fills"
```

### `run_vn100_backtest` (v7.0 — for comparison)
```python
# Source: analysis/_vn100_pipeline.py lines 288-434
def run_vn100_backtest(
    canslim_cfg: CanslimConfig,
    portfolio_cfg: PortfolioConfig,
    entry_option: str,           # "A" or "C"
    period: Tuple[str, str],
    precomputed: Optional[Mapping[str, Any]] = None,
    entry_cfg=None,
) -> Dict[str, Any]:
    # precomputed required keys: "universe", "ohlc", "fundamentals", "foreign", "mdm_gate"
```

### `precompute_static`
```python
# Source: analysis/_vn100_pipeline.py lines 100-282
def precompute_static(
    period: Tuple[str, str],
    mode: str = "current-vn100",
) -> Dict[str, Any]:
    # Returns: {"universe", "ohlc", "fundamentals", "foreign", "mdm_gate", "rs"}
    # Caches to docs/audits/phase32/cache/ keyed by (mode, start, end)
```

### `MomentumScorerConfig`
```python
# Source: strategies/momentum/scorer_config.py
@dataclass
class MomentumScorerConfig:
    rs_threshold: float = 70.0       # RS percentile >= rs_threshold to pass
    n_within_high: float = 0.15      # (high_52w - close) / high_52w <= n_within_high
    min_history_days: int = 252      # warm-up guard (not a sweep param)
```

### `RSConfig`
```python
# Source: strategies/momentum/config.py
@dataclass
class RSConfig:
    roc_days: Tuple[int, ...] = (63, 126, 189, 252)
    roc_weights: Tuple[float, ...] = (0.4, 0.2, 0.2, 0.2)
    min_history_days: int = 252
    # IBD Weighted ROC: 0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252
    # ROC-126: just pct_change(126)
```

### `build_momentum_raw_frame` (needs formula param — see Pitfall 1)
```python
# Source: analysis/_vn100_pipeline.py lines 785-860
def build_momentum_raw_frame(
    panel: pd.DataFrame,
    # formula: str = "weighted_roc"  <-- MISSING, needs to be added
) -> pd.DataFrame:
    # Returns: [date, ticker, n_prox, rs_rating]
    # Caches to docs/audits/phase32/cache/momentum_raw_{start}_{end}.parquet
```

### `_compute_metrics` (called internally by run_v8_backtest)
```python
# Source: analysis/_vn100_pipeline.py lines 930-1007
# Returns:
{
    "CAGR": float,                # annualized return (not percent)
    "Sharpe_rf3": float,          # (CAGR - 0.03) / ann_vol
    "MaxDD": float,               # negative fraction (e.g. -0.163)
    "MaxDD_duration_days": int,   # longest underwater stretch in trading days
    "hit_rate": float,            # win rate (0-1)
    "turnover": float,            # total_buy_notional / mean_nav
    "total_cost_drag_pct": float, # total costs / initial NAV
    "num_trades": int,
    "avg_hold_days": float,
}
```

## Parameter Space for BT-01 Sweep

### Recommended Grid (small, fast)

```python
GRID = {
    "rs_formula":    ["weighted_roc", "roc126"],  # BT-01 key variable
    "rs_threshold":  [60.0, 70.0, 80.0],          # top 40% / top 30% / top 20%
    "n_within_high": [0.10, 0.15, 0.20],          # N rule proximity
    "hard_stop":     [0.06, 0.07, 0.08],          # 6-8% stop
    "slots":         [5, 8],                       # position count
    "entry_option":  ["A", "C"],                  # entry detector
}
# Total: 2 * 3 * 3 * 3 * 2 * 2 = 216 configs
```

216 configs is fast enough for single-process execution (Phase 32 ran 1,536 configs with multiprocessing). Multiprocessing still recommended for speed.

### Selection Criterion
Rank by Sharpe_rf3 descending. Then check CAGR >= 5% and MaxDD >= -30% as sanity gates. Select best config per formula (top Sharpe), then compare the two formula winners to select the overall best.

## Locked v7.0 Baseline Numbers

All confirmed from `docs/audits/phase33/oos_metrics.json` and `baselines.json`:

```
v7.0 (CANSLIM+MDM, OOS 2019-2025):
  CAGR             = 10.18%
  Sharpe_rf3       = 0.813
  MaxDD            = -16.31%
  MaxDD_duration   = 938 days
  hit_rate         = 30.5%
  num_trades       = 59
  avg_hold_days    = 41.25

CANSLIM-only (no MDM gate, OOS 2019-2025):
  CAGR             = 16.43%
  Sharpe_rf3       = 1.047
  MaxDD            = -32.24%

VN-Index B&H (OOS 2019-2025):
  CAGR             = 10.42%
  Sharpe_rf3       = 0.383
  MaxDD            = -40.34%
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CANSLIM C/A (EPS fundamental, MySQL) | RS momentum (price-computed, no DB) | Phase 36 | Removes MySQL dep; works from 2016 (not 2019) |
| Fixed single CANSLIM scorer | MomentumScorerConfig (rs_threshold, n_within_high) | Phase 36 | Two free params instead of 4+ |
| v7.0 sweep (1,536 configs) | v8.0 sweep (216 configs) | Phase 37 | Fewer params; formula comparison is the main variable |

## Open Questions

1. **Formula parameter gap in `build_momentum_raw_frame`**
   - What we know: The function hardcodes IBD Weighted ROC weights; `compute_rs_panel` supports both formulas
   - What's unclear: Whether to add `formula` kwarg to `build_momentum_raw_frame` OR pre-build raw frame outside and inject via `precomputed["momentum_raw"]`
   - Recommendation: Add `formula` kwarg to `build_momentum_raw_frame` — simpler worker function, one line change in `run_v8_backtest` to pass it through

2. **In-sample period data availability from 2016**
   - What we know: Phase 32 used 2014-2018; Phase 35 confirmed stock_eod goes back past 2016 (precompute_static tested with 2019-2025)
   - What's unclear: Whether all VN100 tickers have full 252-day RS warm-up by early 2016 (need 400-day pre-start = 2014-12-01)
   - Recommendation: Use period `("2016-01-01", "2018-12-31")` but precompute_static with warm-up from 2014-12-01 is automatic (lines 70-71 in rs.py: `timedelta(days=400)`)

3. **Whether to include in-sample metrics in comparison table**
   - What we know: BT-03 only requires OOS comparison; v7.0 comparison is OOS 2019-2025
   - What's unclear: Whether the report should show in-sample metrics for context
   - Recommendation: Include in-sample Sharpe for both formulas as secondary info; primary comparison is OOS

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Postgres (vpt_wong_stock_v1) | precompute_static, OHLC data | Assumed yes (used in Phase 36) | — | Parquet cache from prior phases |
| uv / Python 3.10+ | Script execution | Assumed yes (project standard) | Python 3.10+ | — |
| tqdm | Progress display | Soft dep | — | Falls back gracefully (see sweep_vn100.py lines 155-159) |

**Note:** If the precompute cache from Phase 32 (2014-2018) or prior phases (2019-2025) is available, the DB dependency is optional for re-runs. Cache files are at `docs/audits/phase32/cache/`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none detected (run from repo root) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BT-01 | Sweep produces CSV with both formulas represented | smoke | `uv run python analysis/sweep_vn100_v8.py` (check CSV exists + has both formula rows) | No — Wave 0 |
| BT-01 | Formula column takes exactly "weighted_roc" / "roc126" | unit | `pytest tests/phase37/test_sweep_v8.py::test_formula_values` | No — Wave 0 |
| BT-02 | OOS metrics match PortfolioResult schema | smoke | `uv run python analysis/backtest_vn100_v8_oos.py` | No — Wave 0 |
| BT-03 | Comparison table includes all 3 rows (v8, v7, BH) | integration | `pytest tests/phase37/test_comparison.py` | No — Wave 0 |

### Wave 0 Gaps
- [ ] `analysis/sweep_vn100_v8.py` — BT-01 sweep script
- [ ] `analysis/backtest_vn100_v8_oos.py` — BT-02 OOS script
- [ ] `tests/phase37/` — test directory and tests
- [ ] Formula parameter in `build_momentum_raw_frame` — required before sweep can compare formulas

## Sources

### Primary (HIGH confidence)
- `analysis/_vn100_pipeline.py` — `run_v8_backtest` signature, `build_momentum_raw_frame`, `_compute_metrics`, `precompute_static` (lines 100-1017, read directly)
- `strategies/momentum/scorer_config.py` — `MomentumScorerConfig` fields and defaults (read directly)
- `strategies/momentum/scorer.py` — `apply_momentum_thresholds` contract (read directly)
- `strategies/momentum/config.py` — `RSConfig` fields, formula descriptions (read directly)
- `strategies/momentum/rs.py` — `compute_rs_panel`, `get_rs_rankings`, formula="weighted_roc"/"roc126" (read directly)
- `strategies/portfolio/config.py` — `PortfolioConfig` all fields and constraints (read directly)
- `analysis/sweep_vn100.py` — sweep template: grid, worker, multiprocessing, output (read directly)
- `analysis/backtest_vn100_oos.py` — OOS template: load locked params, run, write artifacts (read directly)
- `docs/audits/phase33/oos_metrics.json` — v7.0 confirmed baseline CAGR=10.18%, Sharpe=0.813, MaxDD=-16.31% (read directly)
- `docs/audits/phase33/baselines.json` — VN-Index B&H and CANSLIM-only baselines (read directly)
- `.planning/phases/36-momentum-scorer/36-02-SUMMARY.md` — run_v8_backtest API, precomputed key requirements (read directly)
- `.planning/STATE.md` — v7.0 baseline numbers, v8.0 decisions (read directly)

## Metadata

**Confidence breakdown:**
- API signatures: HIGH — read directly from source code
- Sweep architecture: HIGH — direct model in sweep_vn100.py
- Formula gap (Pitfall 1): HIGH — confirmed by reading build_momentum_raw_frame source
- Baseline numbers: HIGH — confirmed from JSON files in repo

**Research date:** 2026-04-13
**Valid until:** Remains valid until `_vn100_pipeline.py` is modified (e.g., to add formula param)
