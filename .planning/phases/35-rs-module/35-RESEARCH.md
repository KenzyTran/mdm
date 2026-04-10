# Phase 35: RS Module - Research

**Researched:** 2026-04-10
**Domain:** Relative Strength computation, cross-sectional percentile ranking, parquet caching
**Confidence:** HIGH

## Summary

Phase 35 builds a standalone RS (Relative Strength) module that computes two formula variants -- IBD Weighted ROC and simple ROC-126 -- as cross-sectional percentile ranks [0,100] for every VN100 ticker on every trading day. The existing codebase already contains a working RS computation in `strategies/canslim/rules/rs.py` that implements the IBD Weighted ROC formula, but it computes per-date on demand (single `as_of_date` at a time) and is tightly coupled to `CanslimConfig`. Phase 35 must extract and generalize this into a standalone, vectorized module that computes RS for **all dates** at once, caches results as parquet, and supports both formulas in parallel.

The existing `analysis/_vn100_pipeline.py` `precompute_static()` function establishes the project's parquet caching pattern: files keyed by `{datatype}_{mode}_{start}_{end}.parquet` under a cache directory, with existence checks to skip recomputation. The RS module should follow this exact pattern.

**Primary recommendation:** Create `strategies/momentum/rs.py` as a new module (separate from canslim) with vectorized pandas computation, producing a DataFrame of (date, ticker, rs_rank) cached to parquet. Reuse `connectors/postgres.py` for data loading and `strategies/canslim/universe.py` for universe resolution.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOM-01 | RS Weighted ROC (IBD style): 0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252, percentile ranked [0,100] cross-sectionally per day | Existing formula in `strategies/canslim/rules/rs.py` (`_raw_rs`); needs vectorized rewrite for all-dates computation |
| MOM-02 | RS ROC 6-month (ROC126) computed in parallel for comparison | Simple variant -- single `pct_change(126)` then rank |
| MOM-03 | RS cache as parquet keyed by period/formula, no recomputation | Follow `precompute_static()` pattern from `analysis/_vn100_pipeline.py` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.10+, pandas >= 2.0, numpy >= 1.24
- snake_case naming, 4-space indentation
- Modular engine-based architecture with single-responsibility modules
- Data from Postgres `stock_eod` table via `connectors/postgres.py`
- Parquet for intermediate caching (pyarrow already a dependency)
- Code-Docs Sync Rule: update `docs/rules_*.md` if strategy logic changes
- GSD Workflow enforcement for all file changes

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >= 2.0 | Vectorized ROC computation, pivot/rank operations | Already project standard |
| numpy | >= 1.24 | NaN handling, numerical edge cases | Already project standard |
| pyarrow | >= 14.0 | Parquet read/write | Already installed, used by existing cache |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy | >= 2.0 | DB connection via postgres connector | Loading OHLC from stock_eod |
| python-dotenv | >= 1.2 | .env for DB credentials | Via `connectors/postgres.py` |

No new dependencies required. Everything needed is already installed.

## Architecture Patterns

### Recommended Project Structure
```
strategies/
  momentum/
    __init__.py
    rs.py           # RS computation + caching (MOM-01, MOM-02, MOM-03)
    config.py       # RSConfig dataclass
```

### Pattern 1: Vectorized Cross-Sectional RS Computation

**What:** Instead of the current per-ticker loop in `strategies/canslim/rules/rs.py`, use pandas pivot + pct_change + groupby.rank for full-universe, full-history computation in one pass.

**When to use:** Always -- this is the core computation pattern.

**Example:**
```python
def compute_rs_panel(
    ohlc: pd.DataFrame,
    formula: str,  # "weighted_roc" or "roc126"
    config: RSConfig,
) -> pd.DataFrame:
    """Compute RS percentile ranks for all (date, ticker) pairs.

    Args:
        ohlc: DataFrame with columns [stockcode, tradingdate, adj_close].
        formula: Which RS formula to use.
        config: RSConfig with lookback/weight parameters.

    Returns:
        DataFrame with columns [date, ticker, rs_raw, rs_rank].
        rs_rank is cross-sectional percentile [0, 100].
    """
    # Pivot to wide format: dates x tickers
    wide = ohlc.pivot(index="tradingdate", columns="stockcode", values="adj_close")

    if formula == "roc126":
        raw = wide.pct_change(126)
    elif formula == "weighted_roc":
        rocs = [wide.pct_change(lb) for lb in config.roc_days]
        raw = sum(w * r for w, r in zip(config.roc_weights, rocs))
    else:
        raise ValueError(f"Unknown formula: {formula}")

    # Cross-sectional percentile rank per date
    ranked = raw.rank(axis=1, pct=True, na_option="keep") * 100.0

    # Melt back to long format
    result = ranked.reset_index().melt(
        id_vars="tradingdate",
        var_name="ticker",
        value_name="rs_rank",
    ).rename(columns={"tradingdate": "date"})
    result = result.dropna(subset=["rs_rank"])
    return result.sort_values(["date", "ticker"]).reset_index(drop=True)
```

### Pattern 2: Parquet Cache with Period + Formula Key

**What:** Cache RS results following the existing `precompute_static` pattern but adding formula as a key dimension.

**When to use:** For MOM-03 compliance.

**Example:**
```python
CACHE_DIR = Path("docs/audits/phase32/cache")

def _cache_path(formula: str, mode: str, start: str, end: str) -> Path:
    return CACHE_DIR / f"rs_{formula}_{mode}_{start}_{end}.parquet"

def get_rs_rankings(
    formula: str,
    period: tuple[str, str],
    mode: str = "current-vn100",
    force: bool = False,
) -> pd.DataFrame:
    """Load or compute RS rankings, caching to parquet."""
    start, end = period
    path = _cache_path(formula, mode, start, end)
    if path.exists() and not force:
        return pd.read_parquet(path)
    # ... compute and save ...
    result.to_parquet(path, index=False)
    return result
```

### Pattern 3: RSConfig Dataclass

**What:** Lightweight config separate from CanslimConfig, carrying only RS-relevant parameters.

**When to use:** Decouples momentum module from CANSLIM.

**Example:**
```python
from dataclasses import dataclass
from typing import Tuple

@dataclass
class RSConfig:
    roc_days: Tuple[int, ...] = (63, 126, 189, 252)
    roc_weights: Tuple[float, ...] = (0.4, 0.2, 0.2, 0.2)
    min_history_days: int = 252

    def __post_init__(self) -> None:
        if len(self.roc_days) != len(self.roc_weights):
            raise ValueError("roc_days and roc_weights must align")
        if abs(sum(self.roc_weights) - 1.0) > 1e-9:
            raise ValueError("roc_weights must sum to 1.0")
```

### Anti-Patterns to Avoid
- **Per-ticker loop for RS:** The existing `compute_rs_ratings` loops over tickers one by one. For full-history computation across ~100 tickers x ~2500 days, use vectorized pivot+rank instead.
- **Reusing CanslimConfig:** Phase 35 must decouple from CANSLIM. Create a minimal RSConfig that the momentum module owns. CanslimConfig can delegate to it or be updated later.
- **Computing RS from raw prices:** Must use adjusted prices (`adj_close` from `connectors/adjust.py`) to handle stock splits/dividends correctly. The existing `precompute_static` already adjusts OHLC.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile ranking | Manual sorting/counting | `pd.DataFrame.rank(axis=1, pct=True)` | Handles NaN, ties, edge cases |
| ROC calculation | Manual division loops | `pd.DataFrame.pct_change(periods)` | Vectorized, handles missing data |
| Parquet I/O | Custom serialization | `pd.to_parquet()` / `pd.read_parquet()` | Already used, pyarrow installed |
| Price adjustment | Manual split handling | `connectors.adjust.adjust_ohlc()` | Proven, tested, D-05/D-06 compliant |
| Universe resolution | Direct SQL | `strategies.canslim.universe.UniverseLoader` | Handles modes, history filter |

## Common Pitfalls

### Pitfall 1: Survivorship Bias in Universe
**What goes wrong:** Using today's VN100 list for historical dates means tickers that were in VN100 in 2014 but not today are excluded, and vice versa.
**Why it happens:** `current-vn100` mode uses the current stock_list snapshot.
**How to avoid:** Document this limitation. The `liquidity-reconstructed` mode mitigates it by rebalancing semi-annually. Phase 37 backtest sweep should test both modes.
**Warning signs:** Unrealistically high RS for tickers that are small today but had recent IPO.

### Pitfall 2: Insufficient History for ROC-252
**What goes wrong:** ROC(252) needs 252+ trading days of data. Tickers with less history get NaN, creating sparse rankings in early dates.
**Why it happens:** VN100 composition changes; some tickers have shorter trading histories.
**How to avoid:** The `min_history_days=252` filter in UniverseLoader already handles this at universe level. RS computation should also produce NaN (not 0) for tickers with insufficient data, which `pct_change()` does naturally.
**Warning signs:** If < 50 tickers have valid RS on any given date, the percentile ranking is less meaningful.

### Pitfall 3: Using Raw vs Adjusted Prices
**What goes wrong:** Stock splits cause massive fake ROC values (e.g., 2:1 split looks like -50% drop).
**Why it happens:** `stock_eod.closeprice` is raw; `totaladjustrate` must be applied.
**How to avoid:** Always use `adj_close` from `connectors.adjust.adjust_ohlc()`. The pipeline already does this.
**Warning signs:** Outlier RS values (rank 99 for an otherwise mediocre stock).

### Pitfall 4: pct_change vs Manual ROC Formula Mismatch
**What goes wrong:** `pct_change(n)` computes `(close[i] - close[i-n]) / close[i-n]` which is `ROC = close/past - 1`. The existing `_roc()` in `rs.py` computes `(now/past) - 1.0` -- same formula. No mismatch here, but verify.
**Why it happens:** Different ROC definitions exist (log returns vs simple).
**How to avoid:** Use simple returns consistently (not log returns). Verify with spot checks.
**Warning signs:** Rankings diverge from manual calculation.

### Pitfall 5: Memory Pressure from Full Panel
**What goes wrong:** Pivoting ~100 tickers x ~3000 dates creates a 100x3000 matrix per ROC variant -- this is tiny (< 1MB). Not actually a problem here.
**How to avoid:** N/A -- VN100 universe is small enough.

## Code Examples

### Loading Adjusted OHLC for All VN100 Tickers
```python
from connectors import postgres
from connectors.adjust import adjust_ohlc
from strategies.canslim.universe import UniverseLoader

pg = postgres.get_engine()
loader = UniverseLoader(mode="current-vn100", pg_engine=pg)
tickers = sorted(loader.get(date(2025, 1, 1)))

raw = postgres.load_stock_eod(tickers, "2014-01-01", "2025-12-31")
ohlc = adjust_ohlc(raw)
# Use ohlc["adj_close"] for RS computation
```

### Cross-Sectional Rank
```python
# wide: DatetimeIndex x tickers, values = adj_close
roc63 = wide.pct_change(63)
# rank across columns (tickers) for each row (date)
rank = roc63.rank(axis=1, pct=True, na_option="keep") * 100.0
# rank.loc["2024-06-30", "VNM"]  -> percentile 0..100
```

### Spot-Check Validation
```python
def spot_check(rs_df: pd.DataFrame, check_date: str, expected_top: str):
    """Verify the top ticker on a given date matches expectation."""
    day = rs_df[rs_df["date"] == check_date]
    top = day.sort_values("rs_rank", ascending=False).head(1)
    assert top["ticker"].iloc[0] == expected_top, (
        f"Expected {expected_top} as top on {check_date}, "
        f"got {top['ticker'].iloc[0]} with rank {top['rs_rank'].iloc[0]:.1f}"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DB-stored RS (`stock_rs` rss/rsm/rsl) | Price-computed RS from OHLC | v8.0 (this phase) | Removes DB RS dependency (only from 2022), enables backtest from 2014 |
| Per-date RS computation in scorer | Full-panel vectorized RS | v8.0 (this phase) | Compute once, cache, reuse across sweep iterations |
| CANSLIM-coupled RS | Standalone momentum RS module | v8.0 (this phase) | Decouples from MySQL fundamentals |

## Open Questions

1. **Cache directory location**
   - What we know: Phase 32 uses `docs/audits/phase32/cache/`. Phase 35 is a new module, not a phase-32 audit.
   - What's unclear: Should RS cache go in `docs/audits/phase35/cache/` (per-phase convention) or a shared `data/cache/` directory?
   - Recommendation: Use `docs/audits/phase32/cache/` to stay consistent with existing parquet files that the backtest pipeline already reads from. The RS cache files are consumed by the same pipeline. Alternatively, Phase 35 can write to its own `docs/audits/phase35/cache/` but then Phase 37 backtest needs to know where to find them.

2. **Universe mode for RS computation**
   - What we know: Three modes exist (current-vn100, liquidity-reconstructed, vn30-only). Phase 32 sweep tested all three.
   - What's unclear: Which mode should be the default for RS computation in Phase 35?
   - Recommendation: Parameterize `mode` in the RS module. Default to `current-vn100` matching Phase 32 convention. Phase 37 sweep will compare modes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Postgres DB | OHLC data loading | Yes | via .env | Cached parquet files |
| Python 3.10+ | Runtime | Yes | 3.10+ | -- |
| pyarrow | Parquet I/O | Yes | >= 14.0 | -- |
| pandas | Computation | Yes | >= 2.0 | -- |

**Missing dependencies:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/strategies/momentum/ -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOM-01 | IBD Weighted ROC formula produces correct raw RS values | unit | `uv run pytest tests/strategies/momentum/test_rs.py::test_weighted_roc -x` | Wave 0 |
| MOM-01 | Cross-sectional percentile rank [0,100] for all tickers | unit | `uv run pytest tests/strategies/momentum/test_rs.py::test_rank_range -x` | Wave 0 |
| MOM-02 | ROC-126 formula computes correctly in parallel | unit | `uv run pytest tests/strategies/momentum/test_rs.py::test_roc126 -x` | Wave 0 |
| MOM-03 | Cache hit skips recomputation; cache miss computes and saves | unit | `uv run pytest tests/strategies/momentum/test_rs.py::test_cache -x` | Wave 0 |
| SC-4 | Spot-check 3-5 tickers on known dates (cross-sectional correctness) | integration | `uv run pytest tests/strategies/momentum/test_rs.py::test_spot_check -x -m integration` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/strategies/momentum/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/strategies/momentum/__init__.py` -- package init
- [ ] `tests/strategies/momentum/test_rs.py` -- covers MOM-01, MOM-02, MOM-03, SC-4
- [ ] `tests/strategies/momentum/conftest.py` -- shared fixtures (synthetic OHLC panel)

## Sources

### Primary (HIGH confidence)
- `strategies/canslim/rules/rs.py` -- existing IBD Weighted ROC implementation (line-by-line review)
- `strategies/canslim/config.py` -- CanslimConfig with rs_roc_days=(63,126,189,252), rs_weights=(0.4,0.2,0.2,0.2)
- `analysis/_vn100_pipeline.py` -- precompute_static parquet cache pattern
- `connectors/postgres.py` -- load_stock_eod, load_stock_rs APIs
- `connectors/adjust.py` -- adjust_ohlc for price adjustment
- `strategies/canslim/universe.py` -- UniverseLoader with 3 modes
- Postgres DB probe: stock_eod has 2936 tickers through 2026-04-10, stock_list has 100 VN100 tickers

### Secondary (MEDIUM confidence)
- pandas `pct_change()` and `rank()` documentation -- standard pandas API, well-known behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in project
- Architecture: HIGH -- follows established project patterns (precompute_static, canslim rules)
- Pitfalls: HIGH -- well-understood domain (percentile ranking of price momentum)

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable domain, no external API changes expected)
