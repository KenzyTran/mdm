# Phase 36: Momentum Scorer - Research

**Researched:** 2026-04-10
**Domain:** Stock selection pipeline refactoring (CANSLIM fundamentals -> RS momentum)
**Confidence:** HIGH

## Summary

Phase 36 replaces the CANSLIM C/A fundamental rules (EPS YoY, EPS CAGR) with an RS momentum filter (RS >= 70) while keeping the N rule (within 15% of 52-week high) and leaving Option A/C entry confirmation and PortfolioEngine untouched. The change is concentrated in the pipeline orchestrator (`analysis/_vn100_pipeline.py`) and specifically the `_apply_canslim_thresholds` function and `build_canslim_raw_frame` helper. The CanslimScorer itself (Phase 29) is bypassed in the v8.0 pipeline -- the pipeline already builds its own raw frame and applies thresholds independently.

The key insight is that the PortfolioEngine's interface is **already RS-aware**: it accepts `scorer_frame` (columns: `date, ticker, canslim_score`) and `rs_frame` (columns: `date, ticker, rs_value`) as separate inputs. The scorer_frame controls which candidates are allowed (NaN score = dropped), while rs_frame drives RS-based exit ranking and streak exits. The minimal change is to modify `_apply_canslim_thresholds` to use `rs_rank >= 70 AND n_prox <= 0.15` instead of `eps_yoy_q0 >= threshold AND eps_cagr_3y >= threshold AND n_prox <= threshold`.

**Primary recommendation:** Create a new `MomentumScorer` module (or modify `_apply_canslim_thresholds` in the pipeline) that produces the same `scorer_frame` schema (`date, ticker, canslim_score`) using RS >= 70 + N rule, then wire it into `run_vn100_backtest`. Remove MySQL dependency from the precompute path. EntryEngine and PortfolioEngine remain untouched.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MSCO-01 | RS >= 70 filter (top 30% VN100) as buy eligibility | RS percentile rank already computed in `build_canslim_raw_frame` as `rs_rating` column. Change `_apply_canslim_thresholds` to gate on `rs_rating >= 70` instead of `eps_yoy_q0 >= c_threshold AND eps_cagr_3y >= a_threshold`. |
| MSCO-02 | N rule -- stock within 15% of 52-week high | Already computed as `n_prox` in `build_canslim_raw_frame`. Keep `n_pass = n_prox <= 0.15`. No change needed in computation, only in threshold application. |
| MSCO-03 | Volume surge at entry day kept (Option A/C already has it) | Volume surge is handled entirely within `detect_option_a` and `detect_option_c` in `strategies/entry/`. These are called by `_compute_fills` in the pipeline. **Zero changes needed.** |
| MSCO-04 | Remove C/A rules entirely -- no MySQL fundamentals | Remove `eps_yoy_q0` and `eps_cagr_3y` computation from `build_canslim_raw_frame`. Remove MySQL import/connection from `precompute_static`. Remove `fundamentals` cache file. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Code-Docs Sync Rule: when modifying strategy logic, update corresponding docs in `docs/rules_*.md` in the same commit
- GSD Workflow Enforcement: use GSD commands before making changes
- Equity formula rule: must use state[i-1] not state[i] to avoid look-ahead bias
- snake_case naming, 4-space indentation, dataclass pattern for config
- No explicit formatter/linter configured

## Architecture: Current Pipeline Flow

### End-to-end data flow (v7.0 / Phase 32)

```
precompute_static(period)
  -> universe (Postgres: VN100 constituents)
  -> ohlc (Postgres: stock_eod + adjust_ohlc)
  -> fundamentals (MySQL: is_quarter_nonbank)     <-- REMOVE
  -> foreign (Postgres: stock_foreign_eod)        <-- KEEP but unused by v8.0 scorer
  -> mdm_gate (HybridEngine on VN-Index)
  -> rs (Postgres: stock_rs table OR computed)

run_vn100_backtest(canslim_cfg, portfolio_cfg, entry_option, period, precomputed)
  1. Shape OHLC panel -> PortfolioEngine schema
  2. Build canslim_raw_frame (per-ticker per-day metrics):
     - eps_yoy_q0      <-- REMOVE (MSCO-04)
     - eps_cagr_3y     <-- REMOVE (MSCO-04)
     - n_prox          <-- KEEP (MSCO-02)
     - vol_ratio       <-- KEEP (used by S rule, but S is in entry detector too)
     - rs_rating       <-- KEEP (MSCO-01, already computed cross-sectionally)
  3. _apply_canslim_thresholds(raw, canslim_cfg) -> scorer_frame:
     - Currently: score=100 iff C_pass AND A_pass AND N_pass AND S_pass
     - v8.0: score=100 iff RS_pass (>=70) AND N_pass (<=0.15)
  4. Build rs_frame (DB RS with computed RS gap-fill)
  5. _compute_fills via EntryEngine (Option A/C detectors)
  6. PortfolioEngine.run() -> PortfolioResult
```

### Interface Contracts

**PortfolioEngine constructor expects:**

| Input | Schema | Source |
|-------|--------|--------|
| `scorer_frame` | `{date, ticker, canslim_score}` where NaN = drop candidate | `_apply_canslim_thresholds` output |
| `rs_frame` | `{date, ticker, rs_value}` | DB or computed RS |
| `fills` | List of `_PortfolioFill(signal_date, fill_date, ticker, fill_price, window_id, detector_tag)` | EntryEngine output |
| `price_panel` | `{date, ticker, open, high, low, close, volume}` | Adjusted OHLC |
| `mdm_state` | `pd.Series` indexed by date, values `BUY/CASH/SELL` | HybridEngine |

**Critical: `canslim_score` column name is hardcoded** in `REQUIRED_SCORER_COLS` (line 48 of `portfolio/engine.py`) and in `_scorer_lookup` builder. The v8.0 scorer must produce a column named `canslim_score` (or the constant must be renamed). Recommend keeping the column name as-is for zero PortfolioEngine changes, even though the semantics shift from "CANSLIM composite" to "momentum eligibility".

**EntryEngine CANSLIM gate (`CANSLIM_GATE_COLS`):**
The EntryEngine has an optional `canslim_scores` parameter with gate columns `(c_pass, a_pass, n_pass, s_pass, l_pass, liq_pass)`. In the current v7.0 pipeline, this is NOT used -- `_compute_fills` constructs `EntryEngine(mdm_state=gate, config=cfg)` without passing `canslim_scores`. The gating happens at the PortfolioEngine level via `scorer_frame`. So EntryEngine CANSLIM gate is irrelevant to this phase.

### PortfolioEngine candidate flow (lines 506-589)

```python
# Step 5 in main loop (gate == "BUY" and free slots):
fills_today = self._fills_by_signal_date.get(date, [])
candidates = self._dedupe_union(fills_today)        # dedupe by (ticker, window_id)
kept, dropped = sort_by_canslim(candidates, _score)  # sort desc by canslim_score
# dropped = candidates where canslim_score is NaN -> logged as unfilled
for cand in kept:
    # checks: free_slot, max_buys_per_ticker, ticker_weight_cap, cooldown,
    #         liquidity_gate, ceiling_lock, then schedule entry
```

**Key:** `sort_by_canslim` (in `portfolio/sizing.py`) drops any candidate whose `canslim_score` is NaN. This is the gating mechanism. If the scorer produces `canslim_score = 100.0` for stocks passing RS+N, and `NaN` for failures, the existing PortfolioEngine logic works without modification.

## Exact Changes Needed

### 1. New: `strategies/momentum/scorer.py` (or modify pipeline directly)

Create a momentum scorer that replaces the CANSLIM threshold logic:

```python
def apply_momentum_thresholds(
    raw: pd.DataFrame,
    rs_threshold: float = 70.0,
    n_within_high: float = 0.15,
) -> pd.DataFrame:
    """Convert raw frame into scorer_frame for PortfolioEngine.

    Score = 100.0 iff rs_rating >= rs_threshold AND n_prox <= n_within_high.
    NaN rs_rating or n_prox -> NaN score -> candidate dropped.
    """
    rs_pass = raw["rs_rating"] >= rs_threshold
    n_pass = raw["n_prox"] <= n_within_high
    all_pass = rs_pass & n_pass
    return pd.DataFrame({
        "date": raw["date"],
        "ticker": raw["ticker"],
        "canslim_score": np.where(all_pass, 100.0, np.nan),
    })
```

### 2. Modify: `analysis/_vn100_pipeline.py`

**`build_canslim_raw_frame`:**
- Remove the entire MySQL fundamentals section (lines 484-531, fund_lookup construction)
- Remove `eps_yoy_q0` and `eps_cagr_3y` computation (lines 561-599)
- Keep `n_prox` computation (lines 542-549)
- Keep `vol_ratio` computation (lines 552-558) -- still useful for diagnostics
- Keep RS rating computation (lines 620-639)

**`_apply_canslim_thresholds`:**
- Replace `c_pass & a_pass & n_pass & s_pass` with `rs_pass & n_pass`
- Or replace the call entirely with `apply_momentum_thresholds`

**`precompute_static`:**
- Remove `fundamentals` from cache_files dict
- Remove MySQL import and `mysql.load_is_quarter` call
- Remove `fundamentals.to_parquet` cache write
- Keep returning `fundamentals: pd.DataFrame()` in the dict for backward compat (or remove if `run_vn100_backtest` no longer checks for it)

**`run_vn100_backtest`:**
- Remove `"fundamentals"` from the required precomputed keys check (line 327)
- Wire new scorer instead of `_apply_canslim_thresholds`

### 3. Modify: `strategies/canslim/config.py` (or create new config)

Either:
- **Option A (minimal):** Add `rs_filter_threshold: float = 70.0` to CanslimConfig and set `c_threshold = 0.0`, `a_threshold = 0.0` to effectively disable C/A. Hacky but zero new files.
- **Option B (clean):** Create `strategies/momentum/scorer_config.py` with a `MomentumScorerConfig` dataclass containing only `rs_threshold` and `n_within_high`. Create a new `run_v8_backtest` function or add a `scorer_mode` parameter.

**Recommendation:** Option B is cleaner and satisfies MSCO-04 (no fundamentals code at all). The sweep script for Phase 37 needs to iterate over RS thresholds anyway.

### 4. No changes to:

- `strategies/entry/engine.py` -- EntryEngine (MSCO-03: unchanged)
- `strategies/entry/option_a.py` -- Option A detector
- `strategies/entry/option_c.py` -- Option C detector
- `strategies/entry/window.py` -- BUY window logic
- `strategies/portfolio/engine.py` -- PortfolioEngine
- `strategies/portfolio/config.py` -- PortfolioConfig
- `strategies/portfolio/state.py` -- Position/Trade dataclasses
- `strategies/portfolio/sizing.py` -- sort_by_canslim (name misleading but logic is generic)
- `strategies/portfolio/exits.py` -- exit logic
- `strategies/momentum/rs.py` -- RS computation (Phase 35, already done)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RS percentile computation | Custom per-ticker ranking loop | `compute_rs_panel` from Phase 35 or inline `groupby().rank(pct=True)` already in `build_canslim_raw_frame` | Cross-sectional rank is already implemented and tested |
| N rule (52-week high proximity) | New high-tracking logic | Existing `n_prox` computation in `build_canslim_raw_frame` (rolling 252d max) | Already vectorized and tested |
| Candidate gating | New PortfolioEngine filter logic | Existing `canslim_score` NaN-drop mechanism in `sort_by_canslim` | Works perfectly -- NaN = dropped, non-NaN = allowed |

## Common Pitfalls

### Pitfall 1: Dual RS Sources Confusion
**What goes wrong:** Phase 35 `compute_rs_panel` outputs `rs_rank` (0-100 percentile). The pipeline's `build_canslim_raw_frame` independently computes `rs_rating` using the same weighted-ROC formula. The DB `stock_rs` table provides yet another `rs_value`. Three different RS numbers could disagree.
**Why it happens:** The codebase evolved incrementally -- Phase 29 added in-pipeline RS, Phase 35 added the standalone module, and the DB has a pre-existing column.
**How to avoid:** Use a single RS source. The pipeline's inline `rs_rating` computation (lines 620-639 of `_vn100_pipeline.py`) uses the same formula as Phase 35. For Phase 36, use this `rs_rating` for the scorer gate. For `rs_frame` (PortfolioEngine exit ranking), continue using DB RS with computed fallback -- this is the existing behavior and is correct.
**Warning signs:** RS threshold of 70 filters out too many/too few stocks. Verify the distribution of `rs_rating` values at a sample date.

### Pitfall 2: canslim_score Column Name
**What goes wrong:** Renaming `canslim_score` to `momentum_score` breaks `REQUIRED_SCORER_COLS` in PortfolioEngine (line 48) and `_scorer_lookup` builder.
**Why it happens:** Natural desire to rename semantically.
**How to avoid:** Keep the column name `canslim_score` in scorer_frame output. The name is a wire protocol, not a semantic label. Document the mismatch in a comment.
**Warning signs:** `ValueError: scorer_frame missing required columns: {'canslim_score'}` at PortfolioEngine construction.

### Pitfall 3: Stale Cache Files
**What goes wrong:** Old `canslim_raw_*.parquet` cache files contain `eps_yoy_q0` / `eps_cagr_3y` columns. If the cache shape check passes (tickers match), the old frame is returned and the new scorer sees missing RS columns or stale fundamentals.
**Why it happens:** `build_canslim_raw_frame` has a cache check that only verifies ticker coverage, not column set.
**How to avoid:** Either (a) change the cache filename pattern for v8.0 so old caches are ignored, or (b) add a column-presence check to the cache validator, or (c) delete old cache files as a migration step.
**Warning signs:** KeyError on `rs_rating` column, or unexpected C/A pass rates in v8.0 backtest.

### Pitfall 4: MySQL Import Still Attempted
**What goes wrong:** Even after removing fundamentals logic, other code paths in `precompute_static` may still `from connectors import mysql`. If MySQL is unavailable, the entire precompute fails.
**Why it happens:** The import is at the top of the live-load branch alongside `postgres`.
**How to avoid:** Remove `mysql` from the import statement in the live-load path. Grep for all MySQL references in the modified files.

### Pitfall 5: Look-Ahead in RS Ranking
**What goes wrong:** RS at date t uses close[t] in the ROC calculation, which is fine for filtering (you know the close when deciding next-day entry). But if the RS rank changes the `canslim_score` at date t, and the PortfolioEngine uses `canslim_score` at the signal_date to decide whether to allow the entry fill at t+1, this is correct (signal fires at close of t, fill at open of t+1).
**How to avoid:** Verify that `rs_rating` at date t uses only close[t] and earlier -- which it does (ROC = close[t] / close[t-N] - 1). No shift needed.

## Architecture Patterns

### Recommended Approach: Pipeline-Level Replacement

The cleanest approach is to modify `_apply_canslim_thresholds` and `build_canslim_raw_frame` in the pipeline, because:

1. The CanslimScorer (Phase 29) is **not used** in the v7.0+ pipeline -- the pipeline builds its own raw metrics frame
2. The PortfolioEngine interface is already correct (scorer_frame + rs_frame)
3. EntryEngine does not use CANSLIM gating in the pipeline

### Recommended Project Structure

```
strategies/
  momentum/
    __init__.py          # existing
    config.py            # existing RSConfig (Phase 35)
    rs.py                # existing compute_rs_panel (Phase 35)
    scorer.py            # NEW: MomentumScorer with apply_momentum_thresholds
    scorer_config.py     # NEW: MomentumScorerConfig(rs_threshold, n_within_high)
  canslim/               # UNCHANGED (kept for v7.0 backward compat)
  entry/                 # UNCHANGED
  portfolio/             # UNCHANGED

analysis/
  _vn100_pipeline.py     # MODIFIED: wire momentum scorer, remove MySQL
```

### Config Dataclass Pattern

```python
@dataclass
class MomentumScorerConfig:
    """v8.0 momentum scorer thresholds.

    Replaces CANSLIM C/A rules with RS momentum + N rule.
    """
    rs_threshold: float = 70.0       # MSCO-01: RS percentile >= 70
    n_within_high: float = 0.15      # MSCO-02: within 15% of 52-week high
    min_history_days: int = 252      # Need 252 days for RS + N computation

    def __post_init__(self) -> None:
        if not (0 <= self.rs_threshold <= 100):
            raise ValueError(f"rs_threshold must be in [0, 100], got {self.rs_threshold}")
        if not (0 < self.n_within_high <= 1):
            raise ValueError(f"n_within_high must be in (0, 1], got {self.n_within_high}")
```

## Code Examples

### Scorer function (verified pattern from existing `_apply_canslim_thresholds`)

```python
# Source: analysis/_vn100_pipeline.py lines 650-676 (existing pattern)
def apply_momentum_thresholds(
    raw: pd.DataFrame,
    rs_threshold: float = 70.0,
    n_within_high: float = 0.15,
) -> pd.DataFrame:
    """v8.0 scorer: RS >= threshold AND within N% of 52-week high.

    Produces scorer_frame compatible with PortfolioEngine (columns:
    date, ticker, canslim_score). NaN = candidate dropped.
    """
    if raw.empty:
        return pd.DataFrame(columns=["date", "ticker", "canslim_score"])
    rs_pass = raw["rs_rating"] >= rs_threshold
    n_pass = raw["n_prox"] <= n_within_high
    all_pass = rs_pass & n_pass
    return pd.DataFrame({
        "date": raw["date"],
        "ticker": raw["ticker"],
        "canslim_score": np.where(all_pass, 100.0, np.nan),
    })
```

### Simplified build_raw_frame (removing fundamentals)

```python
# Key change: remove MySQL load, remove eps_yoy_q0 / eps_cagr_3y columns
# Keep: n_prox, vol_ratio, rs_rating
def build_momentum_raw_frame(panel: pd.DataFrame) -> pd.DataFrame:
    all_rows = []
    for tk, g in panel.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        close = g["close"].astype(float).values
        high = g["high"].astype(float).values

        # N-rule: 1 - close / rolling 252d max high
        high_series = pd.Series(high)
        roll_max = high_series.rolling(252, min_periods=252).max().values
        n_prox = np.where(
            (roll_max > 0) & np.isfinite(roll_max),
            1.0 - close / roll_max,
            np.nan,
        )
        all_rows.append(pd.DataFrame({
            "date": g["date"].values,
            "ticker": tk,
            "n_prox": n_prox,
            "close": close,
        }))

    raw = pd.concat(all_rows, ignore_index=True)

    # Cross-sectional RS rating (same formula as v7.0)
    raw = raw.sort_values(["ticker", "date"]).reset_index(drop=True)
    for lb in (63, 126, 189, 252):
        raw[f"_close_lag{lb}"] = raw.groupby("ticker")["close"].shift(lb)
    weights = {63: 0.4, 126: 0.2, 189: 0.2, 252: 0.2}
    raw["_raw_rs"] = sum(
        w * (raw["close"] / raw[f"_close_lag{lb}"] - 1.0)
        for lb, w in weights.items()
    )
    raw["rs_rating"] = (
        raw.groupby("date")["_raw_rs"]
        .rank(pct=True, na_option="keep") * 100.0
    )
    raw = raw.drop(columns=[c for c in raw.columns if c.startswith("_")])
    raw = raw.drop(columns=["close"], errors="ignore")
    return raw
```

## Risk Areas

### Tight Coupling: `run_vn100_backtest` signature
The function signature takes `canslim_cfg: CanslimConfig` as first arg with type-check validation (line 314). Phase 37's sweep script will need to call this function. Options:
- Add a `momentum_cfg` parameter alongside `canslim_cfg` (with one being None)
- Create a new `run_v8_backtest` wrapper that takes `MomentumScorerConfig`
- Make `canslim_cfg` optional (default None for v8.0 mode)

**Recommendation:** Create `run_v8_backtest` wrapper that internally calls the shared pipeline code. This keeps v7.0 reproducible and v8.0 clean.

### Cache Invalidation
Old parquet caches under `docs/audits/phase32/cache/` will have stale schemas. Need explicit cache-busting strategy. Simplest: use a different cache filename prefix (e.g., `momentum_raw_` instead of `canslim_raw_`).

### `precomputed` dict key contract
`run_vn100_backtest` line 327 checks for keys `("universe", "ohlc", "fundamentals", "foreign", "mdm_gate")`. The v8.0 version should NOT require `"fundamentals"`. But removing it breaks v7.0 backward compat. Solution: either make it optional or create the v8 wrapper.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run python -m pytest tests/strategies/momentum/ -x` |
| Full suite command | `uv run python -m pytest tests/strategies/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MSCO-01 | RS >= 70 filter produces correct pass/fail | unit | `uv run python -m pytest tests/strategies/momentum/test_scorer.py::test_rs_threshold_filter -x` | Wave 0 |
| MSCO-02 | N rule filters stocks > 15% below 52-week high | unit | `uv run python -m pytest tests/strategies/momentum/test_scorer.py::test_n_rule_filter -x` | Wave 0 |
| MSCO-03 | Volume surge logic unchanged in Option A/C | integration | `uv run python -m pytest tests/strategies/entry/ -x` (existing tests) | Existing |
| MSCO-04 | No MySQL references in v8.0 scorer pipeline | unit | `uv run python -m pytest tests/strategies/momentum/test_scorer.py::test_no_mysql_dependency -x` | Wave 0 |

### Wave 0 Gaps
- [ ] `tests/strategies/momentum/test_scorer.py` -- covers MSCO-01, MSCO-02, MSCO-04
- [ ] `tests/strategies/momentum/test_pipeline_v8.py` -- integration test for full v8 pipeline (scorer -> portfolio engine accepts output)

## Open Questions

1. **RS source: Phase 35 `compute_rs_panel` vs inline pipeline computation?**
   - What we know: Both use the same weighted-ROC formula. The pipeline inline version is already integrated. Phase 35's `compute_rs_panel` is a cleaner, standalone module.
   - What's unclear: Should Phase 36 switch the pipeline to use Phase 35's module, or keep the inline computation?
   - Recommendation: Keep the inline computation for now (less refactoring risk). Phase 37 sweep can optionally use `compute_rs_panel` for formula comparison (weighted_roc vs roc126).

2. **Should the S rule (volume ratio) stay in the scorer?**
   - What we know: Currently `_apply_canslim_thresholds` includes `s_pass` in the composite. But volume surge is already enforced by Option A/C entry detectors (MSCO-03).
   - What's unclear: Is the S rule in the scorer redundant with Option A/C volume check?
   - Recommendation: Remove S from the scorer (it's a double-filter). Option A already requires `vol >= vol_mult * avg50`. Keep `vol_ratio` in the raw frame for diagnostics.

3. **v7.0 backward compatibility**
   - What we know: Phase 37 needs to compare v8.0 vs v7.0 results.
   - Recommendation: Keep `_apply_canslim_thresholds` and `build_canslim_raw_frame` intact. Create parallel v8 functions. A mode flag or separate entry point selects the version.

## Sources

### Primary (HIGH confidence)
- `strategies/portfolio/engine.py` -- PortfolioEngine interface (scorer_frame schema, rs_frame schema, REQUIRED_SCORER_COLS)
- `analysis/_vn100_pipeline.py` -- Pipeline orchestrator (build_canslim_raw_frame, _apply_canslim_thresholds, run_vn100_backtest)
- `strategies/canslim/config.py` -- Current CANSLIM config (C/A thresholds)
- `strategies/entry/engine.py` -- EntryEngine (CANSLIM_GATE_COLS, _canslim_pass unused in pipeline)
- `strategies/momentum/rs.py` -- Phase 35 RS module (compute_rs_panel interface)
- `.planning/REQUIREMENTS.md` -- MSCO-01..04 requirement definitions
- `.planning/ROADMAP.md` -- Phase 36 success criteria

### Secondary (MEDIUM confidence)
- `strategies/canslim/rules/fundamental.py` -- C/A rule implementation (compute_fundamentals, MySQL dependency)
- `strategies/canslim/rules/technical.py` -- N rule implementation (compute_n, 252d high)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all code is existing Python/pandas, no new dependencies
- Architecture: HIGH - read every relevant source file, traced full data flow
- Pitfalls: HIGH - identified from direct code analysis (cache, naming, imports)

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable -- no external dependency changes expected)
