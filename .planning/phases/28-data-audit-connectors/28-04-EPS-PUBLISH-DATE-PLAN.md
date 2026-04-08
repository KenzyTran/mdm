---
phase: 28-data-audit-connectors
plan: 04
type: execute
wave: 2
depends_on: ["28-02"]
files_modified:
  - connectors/eps.py
  - tests/test_eps_publish.py
autonomous: true
requirements: [DATA-04]
must_haves:
  truths:
    - "resolve_eps_publish_date(df) returns the input df with a publish_date column"
    - "If a real publish_date / announce_date / updated_at column exists in input, it is used directly"
    - "Otherwise: publish_date = period_end + 45 days for Q1-Q3, period_end + 90 days for Q4/annual"
    - "Function works on both yearly (lengthreport=12 or NaN) and quarterly rows"
    - "Function is pure: no DB calls, no env reads"
  artifacts:
    - path: connectors/eps.py
      provides: "resolve_eps_publish_date pure function + period_end derivation helper"
      exports: ["resolve_eps_publish_date"]
      min_lines: 40
    - path: tests/test_eps_publish.py
      provides: "unit tests covering real-column shortcut + Q1-Q4 imputation"
  key_links:
    - from: connectors/eps.py
      to: "pandas DateOffset"
      via: "publish_date computation"
      pattern: "DateOffset|Timedelta"
---

<objective>
Implement `resolve_eps_publish_date` per D-08/D-09/D-10 — uses real publish date column if present, otherwise imputes from yearreport+lengthreport. Closes DATA-04.

Purpose: Phase 29 CANSLIM C/A rules MUST filter EPS rows by `publish_date <= as_of_date` to avoid look-ahead bias. This is the canonical helper.
Output: Pure function + comprehensive unit tests.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/28-data-audit-connectors/28-CONTEXT.md
@.planning/phases/28-data-audit-connectors/28-02-SUMMARY.md
@CLAUDE.md

<interfaces>
```python
# connectors/eps.py
import pandas as pd

def resolve_eps_publish_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'publish_date' column to a fundamentals DataFrame.

    Resolution order (per D-08/D-09):
      1. If 'publish_date' or 'announce_date' or 'updated_at' is present and
         non-null for a row, use it.
      2. Otherwise impute from (yearreport, lengthreport):
         - lengthreport in {3, 6, 9}  -> period_end + 45 days
         - lengthreport in {12, None} -> period_end + 90 days
         where period_end = end of month given by lengthreport, year=yearreport.
         Defaults: lengthreport=3 -> 31 Mar, 6 -> 30 Jun, 9 -> 30 Sep, 12 -> 31 Dec.

    Pure function: no DB / env access.
    """
```

is_quarter_* / ratios_stock typically expose: stockcode, yearreport (int), lengthreport (3/6/9/12), eps, ...
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement resolve_eps_publish_date + tests</name>
  <files>connectors/eps.py, tests/test_eps_publish.py</files>
  <read_first>
    - .planning/phases/28-data-audit-connectors/28-CONTEXT.md (D-08, D-09, D-10)
    - tests/conftest.py (pattern for DataFrame fixtures)
  </read_first>
  <behavior>
    Imputation cases:
    - (yearreport=2023, lengthreport=3)  -> period_end=2023-03-31, publish=2023-05-15 (45d)
    - (yearreport=2023, lengthreport=6)  -> period_end=2023-06-30, publish=2023-08-14
    - (yearreport=2023, lengthreport=9)  -> period_end=2023-09-30, publish=2023-11-14
    - (yearreport=2023, lengthreport=12) -> period_end=2023-12-31, publish=2024-03-30 (90d)
    - (yearreport=2023, lengthreport=NaN)-> treat as annual, +90d
    Real-column shortcut:
    - If 'publish_date' column already present and non-null for a row, that value wins
    - If 'announce_date' present (no publish_date), it is renamed/copied
    - If 'updated_at' present (no publish_date/announce_date), use as fallback
    Mixed case:
    - publish_date present but NaN for some rows -> impute only the NaN rows
  </behavior>
  <action>
    Create `connectors/eps.py`:

    ```python
    """EPS publish-date resolution.

    Per phase 28 D-08/D-09/D-10. Pure function — no DB access.
    """
    from __future__ import annotations

    import pandas as pd

    _QUARTER_END_MONTH_DAY = {
        3:  (3, 31),
        6:  (6, 30),
        9:  (9, 30),
        12: (12, 31),
    }

    _REAL_COL_PRIORITY = ("publish_date", "announce_date", "updated_at")


    def _period_end(year: int, length: int | None) -> pd.Timestamp:
        L = 12 if (length is None or pd.isna(length)) else int(length)
        if L not in _QUARTER_END_MONTH_DAY:
            # Fall back to annual
            L = 12
        m, d = _QUARTER_END_MONTH_DAY[L]
        return pd.Timestamp(year=int(year), month=m, day=d)


    def _impute_one(year: int, length) -> pd.Timestamp:
        pe = _period_end(year, length)
        L = 12 if (length is None or pd.isna(length)) else int(length)
        offset_days = 90 if L == 12 else 45
        return pe + pd.Timedelta(days=offset_days)


    def resolve_eps_publish_date(df: pd.DataFrame) -> pd.DataFrame:
        """Add publish_date column per D-08/D-09/D-10."""
        out = df.copy()

        # 1. Seed publish_date from any real column in priority order.
        if "publish_date" not in out.columns:
            out["publish_date"] = pd.NaT
        out["publish_date"] = pd.to_datetime(out["publish_date"], errors="coerce")

        for col in _REAL_COL_PRIORITY[1:]:  # announce_date, updated_at
            if col in out.columns:
                fallback = pd.to_datetime(out[col], errors="coerce")
                out["publish_date"] = out["publish_date"].fillna(fallback)

        # 2. Impute remaining NaNs from yearreport/lengthreport.
        if "yearreport" not in out.columns:
            raise ValueError("missing column 'yearreport' — cannot impute")
        length_col = out["lengthreport"] if "lengthreport" in out.columns else pd.Series(
            [None] * len(out), index=out.index
        )

        mask = out["publish_date"].isna()
        if mask.any():
            imputed = [
                _impute_one(y, L)
                for y, L in zip(out.loc[mask, "yearreport"], length_col[mask])
            ]
            out.loc[mask, "publish_date"] = pd.to_datetime(imputed)

        return out
    ```

    Replace stub `tests/test_eps_publish.py` with:

    ```python
    """Tests for connectors.eps.resolve_eps_publish_date — DATA-04."""
    import numpy as np
    import pandas as pd
    import pytest

    from connectors.eps import resolve_eps_publish_date


    def _row(year, length, **extra):
        base = {"stockcode": "VNM", "yearreport": year, "lengthreport": length, "eps": 1.0}
        base.update(extra)
        return base


    def test_impute_q1_plus_45d():
        df = pd.DataFrame([_row(2023, 3)])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2023-05-15")


    def test_impute_q2_plus_45d():
        df = pd.DataFrame([_row(2023, 6)])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2023-08-14")


    def test_impute_q3_plus_45d():
        df = pd.DataFrame([_row(2023, 9)])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2023-11-14")


    def test_impute_q4_plus_90d():
        df = pd.DataFrame([_row(2023, 12)])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2024-03-30")


    def test_impute_annual_when_lengthreport_nan():
        df = pd.DataFrame([_row(2023, np.nan)])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2024-03-30")


    def test_real_publish_date_column_wins():
        df = pd.DataFrame([_row(2023, 3, publish_date="2023-04-20")])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2023-04-20")


    def test_announce_date_used_when_no_publish_date():
        df = pd.DataFrame([_row(2023, 3, announce_date="2023-04-22")])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2023-04-22")


    def test_updated_at_used_as_last_resort():
        df = pd.DataFrame([_row(2023, 3, updated_at="2023-04-25")])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2023-04-25")


    def test_mixed_real_and_imputed():
        df = pd.DataFrame([
            _row(2023, 3, publish_date="2023-04-20"),
            _row(2023, 6),  # no real -> impute
        ])
        out = resolve_eps_publish_date(df)
        assert out.loc[0, "publish_date"] == pd.Timestamp("2023-04-20")
        assert out.loc[1, "publish_date"] == pd.Timestamp("2023-08-14")


    def test_missing_yearreport_raises():
        df = pd.DataFrame([{"stockcode": "VNM", "eps": 1.0}])
        with pytest.raises(ValueError, match="yearreport"):
            resolve_eps_publish_date(df)
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/test_eps_publish.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `test -f connectors/eps.py`
    - `grep -q 'def resolve_eps_publish_date' connectors/eps.py`
    - `grep -q '_REAL_COL_PRIORITY' connectors/eps.py`
    - `grep -q 'publish_date' connectors/eps.py`
    - `grep -q 'test_impute_q4_plus_90d' tests/test_eps_publish.py`
    - `grep -q 'test_real_publish_date_column_wins' tests/test_eps_publish.py`
    - `uv run pytest tests/test_eps_publish.py -q` passes 10 tests
  </acceptance_criteria>
  <done>resolve_eps_publish_date implements priority + imputation rules; all 10 unit tests green.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_eps_publish.py -q` 10 passed
- DATA-04 closed
</verification>

<success_criteria>
- Pure function honors real columns when present (publish_date > announce_date > updated_at)
- Imputes Q1-Q3 +45d, Q4/annual +90d
- Raises on missing yearreport
- 10 unit tests pass
</success_criteria>

<output>
Create `.planning/phases/28-data-audit-connectors/28-04-SUMMARY.md` after completion.
</output>
