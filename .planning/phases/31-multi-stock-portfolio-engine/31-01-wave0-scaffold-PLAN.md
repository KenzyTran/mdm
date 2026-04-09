---
phase: 31-multi-stock-portfolio-engine
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - strategies/portfolio/__init__.py
  - strategies/portfolio/config.py
  - strategies/portfolio/state.py
  - connectors/postgres.py
  - tests/strategies/portfolio/__init__.py
  - tests/strategies/portfolio/conftest.py
  - tests/strategies/portfolio/fixtures/__init__.py
  - tests/strategies/portfolio/fixtures/synthetic_panel.py
  - tests/strategies/portfolio/test_config.py
  - tests/strategies/portfolio/test_rs_reader.py
autonomous: true
requirements: [GATE-01, PORT-01, PORT-06, PORT-10]
must_haves:
  truths:
    - "PortfolioConfig dataclass exists with fail-loud validation"
    - "load_stock_rs reader exists in connectors/postgres.py and passes ≥2-row historical validation"
    - "Synthetic panel fixtures exist for downstream test files"
    - "PositionBook / SlotState / CooldownRegistry / Trade / Position dataclasses exist as empty stubs"
  artifacts:
    - path: strategies/portfolio/config.py
      provides: "PortfolioConfig dataclass"
      contains: "class PortfolioConfig"
    - path: strategies/portfolio/state.py
      provides: "PositionBook, SlotState, CooldownRegistry, Trade, Position dataclasses"
      contains: "class PositionBook"
    - path: connectors/postgres.py
      provides: "load_stock_rs function"
      contains: "def load_stock_rs"
    - path: tests/strategies/portfolio/conftest.py
      provides: "shared fixtures"
      contains: "synthetic_panel"
  key_links:
    - from: tests/strategies/portfolio/test_rs_reader.py
      to: connectors/postgres.py::load_stock_rs
      via: import
      pattern: "from connectors.postgres import load_stock_rs"
---

<objective>
Wave-0 scaffold for Phase 31. Create the `strategies/portfolio/` package skeleton (config + state dataclasses), the `stock_rs` postgres reader with historical-row validation, and the shared test fixtures that every subsequent plan depends on.

Purpose: Every downstream plan in Phase 31 needs PortfolioConfig, state dataclasses, and synthetic panel fixtures. RS reader must be unblocked first because its schema is the only unknown (CONTEXT Open Question 1).

Output: Importable `strategies.portfolio.config.PortfolioConfig`, `strategies.portfolio.state.*`, `connectors.postgres.load_stock_rs`, plus green tests for config validation and RS reader.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md
@.planning/phases/31-multi-stock-portfolio-engine/31-RESEARCH.md
@.planning/phases/31-multi-stock-portfolio-engine/31-VALIDATION.md
@strategies/entry/config.py
@strategies/entry/engine.py
@connectors/postgres.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: PortfolioConfig dataclass + config validation tests</name>
  <files>strategies/portfolio/__init__.py, strategies/portfolio/config.py, tests/strategies/portfolio/__init__.py, tests/strategies/portfolio/test_config.py</files>
  <read_first>strategies/entry/config.py (fail-loud __post_init__ precedent), .planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-03, D-05, D-08, D-09, D-17..D-24)</read_first>
  <behavior>
    - PortfolioConfig with fields: max_slots=8, slot_weight=0.125, lot_size=100, entry_mode="union", hard_stop_pct=0.08, ma50_vol_mult=1.25, rs_threshold=70, rs_streak_days=5, cooldown_days=5, t_plus=2 (settlement offset, earliest_sell_bar=buy_bar+3), entry_commission=0.0025, entry_slippage=0.0010, exit_commission=0.0025, exit_tax=0.0010, exit_slippage=0.0010, adv_mult=10, ceiling_pct=0.07, floor_pct=0.07
    - __post_init__ raises ValueError on: max_slots<1 or >20, slot_weight not in (0,1], lot_size<1, entry_mode not in {"A","C","union"}, hard_stop_pct not in (0,1), rs_threshold<0 or >100, any cost pct<0 or >0.05, adv_mult<1
    - Test: default config instantiates cleanly
    - Test: entry_mode="X" raises ValueError containing "entry_mode"
    - Test: max_slots=0 raises ValueError
    - Test: hard_stop_pct=1.5 raises ValueError
    - Test: negative cost raises ValueError
  </behavior>
  <action>
    Create `strategies/portfolio/__init__.py` (empty module docstring only).
    Create `strategies/portfolio/config.py` with `@dataclass` PortfolioConfig containing exactly the fields and defaults listed in &lt;behavior&gt;. Field types: int for counts, float for pcts, str for entry_mode. Implement `__post_init__` performing each listed validation and raising `ValueError(f"...")` with the offending field name in the message. Import style: `from dataclasses import dataclass, field`.
    Create `tests/strategies/portfolio/__init__.py` (empty).
    Create `tests/strategies/portfolio/test_config.py` with the 5 test functions listed in &lt;behavior&gt; using plain `pytest.raises(ValueError, match=...)`.
    Per D-03 / D-05 / memory "project_best_model.md": fail-loud, no YAML, no silent fallback.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_config.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "class PortfolioConfig" strategies/portfolio/config.py returns a match
    - grep "entry_mode" strategies/portfolio/config.py returns a match
    - grep "raise ValueError" strategies/portfolio/config.py returns ≥4 matches
    - pytest command above exits 0 with ≥5 tests collected
  </acceptance_criteria>
  <done>Config dataclass importable, 5 validation tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: State dataclasses (PositionBook, SlotState, CooldownRegistry, Trade, Position)</name>
  <files>strategies/portfolio/state.py, tests/strategies/portfolio/fixtures/__init__.py, tests/strategies/portfolio/fixtures/synthetic_panel.py, tests/strategies/portfolio/conftest.py</files>
  <read_first>strategies/entry/engine.py (Fill/Unfilled dataclass shape), .planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-09, D-11, D-17, D-20, D-21, D-27)</read_first>
  <behavior>
    - Position dataclass: ticker:str, buy_bar:int, buy_date:pd.Timestamp, buy_price:float, shares:int, cost_basis:float, earliest_sell_bar:int (=buy_bar+3 per D-17)
    - Trade dataclass: ticker, buy_date, buy_price, buy_cost_vnd, sell_date, sell_price, sell_cost_vnd, pnl_vnd, pnl_pct, exit_reason
    - SlotState dataclass: max_slots:int, open_positions:list[Position]; method `free_slots()->int`; method `has_open(ticker)->bool`
    - CooldownRegistry: method `register(ticker, exit_bar_idx)` and `is_cooling(ticker, current_bar_idx, cooldown_days)->bool`. Per D-21 earliest re-entry bar = exit_bar_idx + cooldown_days + 1 (D+6 when cooldown_days=5).
    - PositionBook = thin container: `slots: SlotState`, `cooldowns: CooldownRegistry`, `completed_trades: list[Trade]`, `unfilled: list[dict]`
    - Synthetic panel fixture generates 3 tickers × 60 bars with deterministic OHLCV (columns: date, ticker, open, high, low, close, volume, ceiling, floor). Ceiling/floor computed as prev_close * 1.07 / 0.93. Provide hook parameters to force ceiling-lock/floor-lock on specific bars for downstream tests.
  </behavior>
  <action>
    Create `strategies/portfolio/state.py`:
    - Import `from dataclasses import dataclass, field`, `import pandas as pd`, `from typing import Optional`.
    - Define `Position`, `Trade` (both with the exact fields in &lt;behavior&gt;), `SlotState`, `CooldownRegistry`, `PositionBook` dataclasses.
    - `SlotState.free_slots()` returns `self.max_slots - len(self.open_positions)`.
    - `SlotState.has_open(ticker)` iterates `open_positions` checking `p.ticker == ticker`.
    - `CooldownRegistry.register(ticker, exit_bar_idx)` stores `{ticker: exit_bar_idx}` in an internal dict. `is_cooling(ticker, current_bar_idx, cooldown_days)` returns `True` if `ticker in dict and current_bar_idx < dict[ticker] + cooldown_days + 1`. Per D-21.
    - `PositionBook.__init__` takes `max_slots:int` and builds `SlotState(max_slots=max_slots, open_positions=[])`, empty `CooldownRegistry`, empty lists.
    Create `tests/strategies/portfolio/fixtures/__init__.py` (empty).
    Create `tests/strategies/portfolio/fixtures/synthetic_panel.py` with function `make_panel(tickers=("AAA","BBB","CCC"), n_bars=60, seed=42, lock_days=None)` returning a long-form DataFrame with columns: `date, ticker, open, high, low, close, volume, ceiling, floor`. Dates = pandas bdate_range starting 2020-01-02. Price walk via seeded numpy. `lock_days` = dict mapping ticker -> list of (bar_idx, "ceiling"|"floor") to force `open==high==low==ceiling_or_floor` at that bar.
    Create `tests/strategies/portfolio/conftest.py` exposing a pytest fixture `synthetic_panel` that calls `make_panel()` with defaults, and a fixture `config` returning `PortfolioConfig()`.
    NO tests in this task — subsequent plans consume the fixtures. Just verify import works via a single smoke test file... actually, add 2 smoke tests inside `tests/strategies/portfolio/test_config.py` appending: `test_state_imports` asserting `PositionBook(max_slots=8).slots.free_slots() == 8`, and `test_cooldown_clock` asserting earliest re-entry = exit_bar + 6 when cooldown_days=5 (D-21).
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_config.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "class PositionBook" strategies/portfolio/state.py matches
    - grep "earliest_sell_bar" strategies/portfolio/state.py matches
    - grep "class CooldownRegistry" strategies/portfolio/state.py matches
    - grep "def make_panel" tests/strategies/portfolio/fixtures/synthetic_panel.py matches
    - grep "ceiling" tests/strategies/portfolio/fixtures/synthetic_panel.py matches
    - pytest command exits 0 with ≥7 tests collected (5 config + 2 state smoke)
  </acceptance_criteria>
  <done>State dataclasses + fixtures importable; smoke tests pass; cooldown math matches D-21.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: load_stock_rs reader + historical-row validation test</name>
  <files>connectors/postgres.py, tests/strategies/portfolio/test_rs_reader.py</files>
  <read_first>connectors/postgres.py (existing get_engine + reader patterns), .planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-15, D-16), 31-RESEARCH.md Open Question 1 (schema spike required)</read_first>
  <behavior>
    - Schema spike MUST run first: SELECT column_name FROM information_schema.columns WHERE table_name='stock_rs' — record actual columns in a comment at the top of load_stock_rs
    - load_stock_rs(start:str, end:str, tickers:Optional[Iterable[str]]=None) -> pd.DataFrame with columns exactly ["date","ticker","rs_value"], date as pd.Timestamp, rs_value as float
    - Integration test: load_stock_rs for a known date range and assert ≥2 rows returned; assert exact column set {"date","ticker","rs_value"}; assert dtype of rs_value is numeric; test is skipped with `pytest.skip` if postgres env vars are absent (graceful local-dev)
  </behavior>
  <action>
    STEP 1 — schema spike: run via python REPL `from connectors.postgres import get_engine; import pandas as pd; print(pd.read_sql("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='stock_rs'", get_engine()))`. Record the resulting column list at the top of the new function as a comment.
    STEP 2 — append to `connectors/postgres.py` a new function `load_stock_rs(start, end, tickers=None)` following the template in 31-RESEARCH.md code example but substituting the actual column names discovered in step 1. Use `sqlalchemy.text` and `get_engine()`. Rename columns to the standard `["date","ticker","rs_value"]` on return. Cast `date` via `pd.to_datetime` and `rs_value` via `pd.to_numeric`. Fail-loud: `raise ValueError` if the returned frame is empty AND no tickers filter was supplied (catches config drift, per D-15 validation requirement).
    STEP 3 — create `tests/strategies/portfolio/test_rs_reader.py` with:
      - `test_load_stock_rs_schema`: calls `load_stock_rs("2023-01-01","2023-06-30")`, asserts columns == ["date","ticker","rs_value"], asserts len ≥ 2, asserts `pd.api.types.is_datetime64_any_dtype(df["date"])`, asserts `pd.api.types.is_numeric_dtype(df["rs_value"])`. Wrap in `try: get_engine() except: pytest.skip("postgres unavailable")`.
      - `test_load_stock_rs_ticker_filter`: calls with tickers=["VNM"] and asserts all returned ticker == "VNM" OR skips if VNM absent.
    Per D-15, reader MUST be validated against ≥2 known historical rows before use — this test IS that validation.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_rs_reader.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "def load_stock_rs" connectors/postgres.py matches
    - grep "stock_rs" connectors/postgres.py matches
    - grep "rs_value" tests/strategies/portfolio/test_rs_reader.py matches
    - pytest command exits 0 (either passes or skips cleanly if postgres unavailable; must NOT error)
  </acceptance_criteria>
  <done>RS reader exists, returns canonical 3-column frame, schema spike comment present, integration test green or cleanly skipped.</done>
</task>

</tasks>

<verification>
uv run pytest tests/strategies/portfolio/ -x -q
</verification>

<success_criteria>
- PortfolioConfig fails loud on bad values
- PositionBook / SlotState / CooldownRegistry / Position / Trade dataclasses exist
- Synthetic panel fixture importable from tests
- load_stock_rs reader validated against real postgres rows (or cleanly skips in envs without DB)
- All Wave 1 tests green
</success_criteria>

<output>
After completion, create `.planning/phases/31-multi-stock-portfolio-engine/31-01-SUMMARY.md`
</output>
