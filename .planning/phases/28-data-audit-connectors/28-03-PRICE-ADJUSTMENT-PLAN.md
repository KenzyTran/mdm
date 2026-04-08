---
phase: 28-data-audit-connectors
plan: 03
type: execute
wave: 2
depends_on: ["28-01"]
files_modified:
  - connectors/adjust.py
  - tests/test_adjust.py
  - scripts/spot_check_adjust.py
  - docs/audits/phase28-price-adjustment.md
autonomous: true
requirements: [DATA-03]
must_haves:
  truths:
    - "adjust_ohlc(df) returns a DataFrame with adjusted open/high/low/close columns equal to raw price * totaladjustrate"
    - "Original raw columns are preserved alongside adjusted columns"
    - "Helper raises ValueError if totaladjustrate column is missing"
    - "Spot-check script can dump raw vs adjusted close for a given ticker for visual sanity"
    - "Documentation states the convention: adjusted = raw * totaladjustrate, volume left as-is per D-05"
  artifacts:
    - path: connectors/adjust.py
      provides: "adjust_ohlc pure function"
      exports: ["adjust_ohlc"]
      min_lines: 25
    - path: tests/test_adjust.py
      provides: "unit tests for adjust_ohlc"
    - path: scripts/spot_check_adjust.py
      provides: "CLI script that pulls a ticker from postgres and prints raw vs adjusted close"
    - path: docs/audits/phase28-price-adjustment.md
      provides: "Documented adjustment convention"
      contains: "totaladjustrate"
  key_links:
    - from: scripts/spot_check_adjust.py
      to: "connectors.postgres.load_stock_eod"
      via: "import + call"
      pattern: "load_stock_eod"
    - from: scripts/spot_check_adjust.py
      to: "connectors.adjust.adjust_ohlc"
      via: "import + call"
      pattern: "adjust_ohlc"
---

<objective>
Implement the price-adjustment helper, unit-test it, and ship a spot-check script + doc. Closes DATA-03.

Purpose: Phase 29+ backtest must use adjusted prices (splits/divs/rights) — this provides the canonical helper and proves it works on real tickers.
Output: Pure function `adjust_ohlc(df)`, unit tests, spot-check CLI, audit doc.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/28-data-audit-connectors/28-CONTEXT.md
@.planning/phases/28-data-audit-connectors/28-01-SUMMARY.md
@connectors/postgres.py
@CLAUDE.md

<interfaces>
```python
# connectors/adjust.py
import pandas as pd

def adjust_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Add adjusted_open/high/low/close columns = raw * totaladjustrate.

    Input: DataFrame with columns openprice, highestprice, lowestprice,
    closeprice, totaladjustrate.
    Output: same DataFrame + columns adj_open, adj_high, adj_low, adj_close.
    Volume not adjusted (per D-05).
    Raises ValueError if totaladjustrate missing.
    """
```

Per D-05/D-06: adjusted_price = raw * totaladjustrate; openprice, closeprice, highestprice, lowestprice all adjusted; totalvol left as-is.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement adjust_ohlc + unit tests</name>
  <files>connectors/adjust.py, tests/test_adjust.py</files>
  <read_first>
    - tests/conftest.py (fake_ohlc_df fixture has totaladjustrate=[2,2,2,1,1])
    - .planning/phases/28-data-audit-connectors/28-CONTEXT.md (D-05, D-06, D-07)
  </read_first>
  <behavior>
    - adjust_ohlc(fake_ohlc_df) returns df with adj_close == closeprice * totaladjustrate (rows 0-2: closeprice*2, rows 3-4: closeprice*1)
    - Same for adj_open, adj_high, adj_low
    - Original columns preserved
    - totalvol unchanged
    - Missing totaladjustrate -> ValueError("missing column 'totaladjustrate'")
    - Empty DataFrame returns empty DataFrame with new columns added
  </behavior>
  <action>
    Create `connectors/adjust.py`:

    ```python
    """Price adjustment helper for stock_eod.

    Per phase 28 D-05/D-06: adjusted_price = raw_price * totaladjustrate.
    Volume left unadjusted unless audit shows otherwise.
    """
    from __future__ import annotations

    import pandas as pd

    _RAW_TO_ADJ = {
        "openprice":    "adj_open",
        "highestprice": "adj_high",
        "lowestprice":  "adj_low",
        "closeprice":   "adj_close",
    }


    def adjust_ohlc(df: pd.DataFrame) -> pd.DataFrame:
        """Return df with adj_open/high/low/close = raw * totaladjustrate."""
        if "totaladjustrate" not in df.columns:
            raise ValueError("missing column 'totaladjustrate'")
        out = df.copy()
        rate = out["totaladjustrate"].astype(float)
        for raw, adj in _RAW_TO_ADJ.items():
            if raw not in out.columns:
                raise ValueError(f"missing column {raw!r}")
            out[adj] = out[raw].astype(float) * rate
        return out
    ```

    Replace stub `tests/test_adjust.py` with:

    ```python
    """Tests for connectors.adjust — DATA-03."""
    import pandas as pd
    import pytest

    from connectors.adjust import adjust_ohlc


    def test_adjust_ohlc_applies_rate(fake_ohlc_df):
        out = adjust_ohlc(fake_ohlc_df)
        # rows 0-2 have rate=2.0, rows 3-4 have rate=1.0
        assert out.loc[0, "adj_close"] == pytest.approx(10.2 * 2.0)
        assert out.loc[2, "adj_close"] == pytest.approx(12.2 * 2.0)
        assert out.loc[3, "adj_close"] == pytest.approx(13.2 * 1.0)
        assert out.loc[4, "adj_close"] == pytest.approx(14.2 * 1.0)
        assert out.loc[0, "adj_open"]  == pytest.approx(10.0 * 2.0)
        assert out.loc[0, "adj_high"]  == pytest.approx(10.5 * 2.0)
        assert out.loc[0, "adj_low"]   == pytest.approx( 9.5 * 2.0)


    def test_adjust_ohlc_preserves_raw_and_volume(fake_ohlc_df):
        out = adjust_ohlc(fake_ohlc_df)
        for col in ("openprice","highestprice","lowestprice","closeprice","totalvol"):
            assert col in out.columns
        # volume unchanged
        assert (out["totalvol"] == fake_ohlc_df["totalvol"]).all()


    def test_adjust_ohlc_missing_totaladjustrate_raises():
        df = pd.DataFrame({"closeprice": [1.0]})
        with pytest.raises(ValueError, match="totaladjustrate"):
            adjust_ohlc(df)


    def test_adjust_ohlc_empty_df():
        df = pd.DataFrame(columns=[
            "openprice","highestprice","lowestprice","closeprice","totaladjustrate"
        ])
        out = adjust_ohlc(df)
        for col in ("adj_open","adj_high","adj_low","adj_close"):
            assert col in out.columns
        assert len(out) == 0
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/test_adjust.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `test -f connectors/adjust.py`
    - `grep -q 'def adjust_ohlc' connectors/adjust.py`
    - `grep -q 'totaladjustrate' connectors/adjust.py`
    - `grep -q 'adj_close' connectors/adjust.py`
    - `grep -q 'test_adjust_ohlc_applies_rate' tests/test_adjust.py`
    - `uv run pytest tests/test_adjust.py -q` exits 0 with 4 passed
  </acceptance_criteria>
  <done>adjust_ohlc applies rate correctly, preserves raw/volume, raises on missing column, all 4 unit tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Spot-check script + audit doc</name>
  <files>scripts/spot_check_adjust.py, docs/audits/phase28-price-adjustment.md</files>
  <read_first>
    - connectors/postgres.py (load_stock_eod signature)
    - connectors/adjust.py (adjust_ohlc signature)
  </read_first>
  <action>
    Create `scripts/spot_check_adjust.py`:

    ```python
    """Spot-check price adjustment for a given ticker.

    Usage: uv run python scripts/spot_check_adjust.py VNM 2018-01-01 2024-12-31
    Prints raw vs adjusted closeprice around days where totaladjustrate changes
    (split/dividend events).
    """
    from __future__ import annotations

    import sys

    from connectors.postgres import load_stock_eod
    from connectors.adjust import adjust_ohlc


    def main(ticker: str, start: str, end: str) -> int:
        df = load_stock_eod([ticker], start, end)
        if df.empty:
            print(f"No rows for {ticker} in [{start}, {end}]")
            return 1
        df = adjust_ohlc(df)
        # Highlight rate-change boundaries
        df["rate_change"] = df["totaladjustrate"].diff().fillna(0) != 0
        events = df[df["rate_change"]]
        print(f"=== {ticker}: {len(df)} rows, {len(events)} adjustment events ===")
        cols = ["tradingdate", "closeprice", "totaladjustrate", "adj_close"]
        if not events.empty:
            print("Around adjustment events:")
            for idx in events.index:
                window = df.loc[max(0, idx - 2): idx + 2, cols]
                print(window.to_string(index=False))
                print("---")
        else:
            print("No rate changes in window. Head/tail:")
            print(df[cols].head().to_string(index=False))
            print(df[cols].tail().to_string(index=False))
        return 0


    if __name__ == "__main__":
        if len(sys.argv) != 4:
            print("Usage: spot_check_adjust.py TICKER START END")
            sys.exit(2)
        sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
    ```

    Create `docs/audits/phase28-price-adjustment.md`:

    ```markdown
    # Phase 28 — Price Adjustment Convention

    **Source table:** `stock_eod` (Postgres, `vpt_wong_stock_v1`)
    **Adjustment column:** `totaladjustrate`
    **Helper:** `connectors.adjust.adjust_ohlc`

    ## Convention (locked, per phase 28 D-05/D-06)

    `stock_eod` price columns are **unadjusted**. To get a continuous series
    suitable for backtesting:

    ```
    adj_open   = openprice    * totaladjustrate
    adj_high   = highestprice * totaladjustrate
    adj_low    = lowestprice  * totaladjustrate
    adj_close  = closeprice   * totaladjustrate
    adj_volume = totalvol                       # NOT adjusted (D-05)
    ```

    All downstream backtest code (Phases 29+) MUST consume `adj_*` columns.

    ## Spot-check protocol

    Run for 2-3 known split/dividend tickers:

    ```bash
    uv run python scripts/spot_check_adjust.py VNM 2018-01-01 2024-12-31
    uv run python scripts/spot_check_adjust.py HPG 2018-01-01 2024-12-31
    uv run python scripts/spot_check_adjust.py FPT 2018-01-01 2024-12-31
    ```

    Confirm visually that `adj_close` produces a continuous curve across
    rate-change boundaries (no step discontinuity).

    ## Volume note

    `totalvol` is intentionally NOT adjusted in v1. If a future audit shows
    volume discontinuities at split boundaries, revisit per D (deferred ideas).
    ```
  </action>
  <verify>
    <automated>uv run python -c "import scripts.spot_check_adjust" && test -f docs/audits/phase28-price-adjustment.md</automated>
  </verify>
  <acceptance_criteria>
    - `test -f scripts/spot_check_adjust.py`
    - `test -f docs/audits/phase28-price-adjustment.md`
    - `grep -q 'load_stock_eod' scripts/spot_check_adjust.py`
    - `grep -q 'adjust_ohlc' scripts/spot_check_adjust.py`
    - `grep -q 'totaladjustrate' docs/audits/phase28-price-adjustment.md`
    - `grep -q 'adj_close' docs/audits/phase28-price-adjustment.md`
    - `grep -q 'NOT adjusted' docs/audits/phase28-price-adjustment.md`
    - Script importable without error
  </acceptance_criteria>
  <done>Spot-check script runs against live Postgres for any ticker, doc clearly states the convention.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_adjust.py -q` 4 passed
- DATA-03 closed: helper exists, tested, documented, spot-check script available
</verification>

<success_criteria>
- adjust_ohlc unit-tested with 4 cases
- Spot-check CLI works against live Postgres
- Convention documented under docs/audits/
</success_criteria>

<output>
Create `.planning/phases/28-data-audit-connectors/28-03-SUMMARY.md` after completion.
</output>
