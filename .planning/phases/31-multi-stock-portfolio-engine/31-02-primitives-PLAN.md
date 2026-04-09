---
phase: 31-multi-stock-portfolio-engine
plan: 02
type: execute
wave: 2
depends_on: [31-01]
files_modified:
  - strategies/portfolio/microstructure.py
  - strategies/portfolio/costs.py
  - tests/strategies/portfolio/test_microstructure.py
  - tests/strategies/portfolio/test_costs.py
  - tests/strategies/portfolio/test_cooldown.py
autonomous: true
requirements: [GATE-03, GATE-04, PORT-05, PORT-07, PORT-08]
must_haves:
  truths:
    - "Ceiling-locked bar blocks new entry fill with unfilled log reason ceiling_lock"
    - "Floor-locked bar defers exit fill to the next non-locked bar, preserving original exit reason"
    - "T+2 helper computes earliest_sell_bar = buy_bar + 3"
    - "Entry cost = 0.35% (0.25 comm + 0.10 slip); exit cost = 0.45% (0.25 comm + 0.10 tax + 0.10 slip)"
    - "Cooldown allows re-entry only on bar D+6 after exit bar D (cooldown_days=5)"
    - "MDM SELL exit does NOT register cooldown"
  artifacts:
    - path: strategies/portfolio/microstructure.py
      provides: "compute_ceiling, compute_floor, is_ceiling_locked, is_floor_locked, t2_earliest_sell_bar"
      contains: "def is_ceiling_locked"
    - path: strategies/portfolio/costs.py
      provides: "apply_entry_cost, apply_exit_cost, entry_cost_basis"
      contains: "def apply_entry_cost"
  key_links:
    - from: tests/strategies/portfolio/test_microstructure.py
      to: strategies/portfolio/microstructure.py
      via: import
      pattern: "from strategies.portfolio.microstructure"
    - from: tests/strategies/portfolio/test_costs.py
      to: strategies/portfolio/costs.py
      via: import
      pattern: "from strategies.portfolio.costs"
---

<objective>
Build the pure-function primitives that the exit chain and engine will compose: Vietnam microstructure helpers (T+2, ceiling lock, floor lock), cost functions (entry/exit/tax/slippage), and cooldown registry semantics tests.

Purpose: Isolating these as stateless functions keeps the engine loop trivial to audit and lets us unit-test every edge case (limit-down, tax, D+6 re-entry) in milliseconds.

Output: Importable helpers + 3 green test files covering GATE-03, GATE-04, PORT-05, PORT-07, PORT-08.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md
@.planning/phases/31-multi-stock-portfolio-engine/31-RESEARCH.md
@strategies/portfolio/config.py
@strategies/portfolio/state.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: microstructure.py — T+2, ceiling/floor lock helpers</name>
  <files>strategies/portfolio/microstructure.py, tests/strategies/portfolio/test_microstructure.py</files>
  <read_first>.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-17, D-18, D-19), 31-RESEARCH.md Pitfall 5 (raw *1.07 acceptable)</read_first>
  <behavior>
    - compute_ceiling(prev_close:float, pct:float=0.07) -> float  (raw prev_close*(1+pct), TODO about tick rounding)
    - compute_floor(prev_close:float, pct:float=0.07) -> float
    - is_ceiling_locked(open_:float, high:float, low:float, ceiling:float, tol:float=1e-6) -> bool. True iff abs(open_-ceiling)<tol AND high==low==open_.
    - is_floor_locked(open_:float, high:float, low:float, floor:float, tol:float=1e-6) -> bool. Same shape.
    - t2_earliest_sell_bar(buy_bar_idx:int, t_plus:int=2) -> int returns buy_bar_idx + t_plus + 1 (== buy_bar+3 when t_plus=2, per D-17).
    - Tests:
      - test_ceiling_value: compute_ceiling(100)==107.0
      - test_floor_value: compute_floor(100)==93.0
      - test_ceiling_locked_true: open=high=low=107.0, ceiling=107.0 → True
      - test_ceiling_locked_false_range: open=107 but high!=low → False
      - test_ceiling_locked_false_below: open=106 → False
      - test_floor_locked_true / _false mirror tests
      - test_t2: buy_bar=10, t_plus=2 → earliest=13 (D+3 semantics)
  </behavior>
  <action>
    Create `strategies/portfolio/microstructure.py` with the 5 pure functions listed in &lt;behavior&gt; using only stdlib (no pandas). Add module docstring citing D-17/D-18/D-19. Add a TODO comment near compute_ceiling: "TODO: replace raw *1.07 with VN tick-rounding helper (per CONTEXT D-18)".
    Create `tests/strategies/portfolio/test_microstructure.py` with the 8 tests listed in &lt;behavior&gt;. Use plain `assert` comparisons.
    No pandas imports in this file — keep it stateless.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_microstructure.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "def is_ceiling_locked" strategies/portfolio/microstructure.py matches
    - grep "def t2_earliest_sell_bar" strategies/portfolio/microstructure.py matches
    - grep "buy_bar_idx + t_plus + 1" strategies/portfolio/microstructure.py matches
    - pytest exits 0 with ≥8 tests passed
  </acceptance_criteria>
  <done>All 8 microstructure tests green; helpers stateless and stdlib-only.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: costs.py — entry/exit cost functions</name>
  <files>strategies/portfolio/costs.py, tests/strategies/portfolio/test_costs.py</files>
  <read_first>.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-22, D-23)</read_first>
  <behavior>
    - apply_entry_cost(notional:float, cfg:PortfolioConfig) -> float: returns total cash debit = notional * (1 + entry_commission + entry_slippage). For default cfg: notional=100M → debit=100.35M.
    - apply_exit_cost(gross_proceeds:float, cfg:PortfolioConfig) -> float: returns net_cash_credit = gross_proceeds * (1 - exit_commission - exit_tax - exit_slippage). For default cfg: 100M → 99.55M.
    - entry_cost_basis(fill_price:float, cfg:PortfolioConfig) -> float: returns fill_price * (1 + entry_commission + entry_slippage). Used for P&L. Per D-22.
    - Tests:
      - test_entry_cost_default: cfg=PortfolioConfig(); apply_entry_cost(100_000_000, cfg) == 100_350_000
      - test_exit_cost_default: cfg=PortfolioConfig(); apply_exit_cost(100_000_000, cfg) == 99_550_000
      - test_entry_cost_basis: fill_price=25000 → basis=25087.5
      - test_cost_override: cfg with entry_commission=0.001 → apply_entry_cost(100M, cfg)==100_200_000 (0.001+0.001)
  </behavior>
  <action>
    Create `strategies/portfolio/costs.py` with the 3 functions. Import `PortfolioConfig` from `.config`. Use simple arithmetic — no loops. Add module docstring citing D-22.
    Create `tests/strategies/portfolio/test_costs.py` with the 4 tests using `pytest.approx` for float comparisons.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_costs.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "def apply_entry_cost" strategies/portfolio/costs.py matches
    - grep "def apply_exit_cost" strategies/portfolio/costs.py matches
    - grep "def entry_cost_basis" strategies/portfolio/costs.py matches
    - pytest exits 0 with ≥4 tests passed
  </acceptance_criteria>
  <done>Cost primitives match D-22 arithmetic; all tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Cooldown semantics tests (PORT-07, D-20/D-21)</name>
  <files>tests/strategies/portfolio/test_cooldown.py</files>
  <read_first>strategies/portfolio/state.py (CooldownRegistry from Plan 01), 31-CONTEXT.md (D-20, D-21)</read_first>
  <behavior>
    - test_cooldown_blocks_d_plus_5: register(ticker="AAA", exit_bar_idx=10); is_cooling("AAA", current_bar_idx=15, cooldown_days=5) == True (bar 15 = D+5, still blocked)
    - test_cooldown_allows_d_plus_6: is_cooling("AAA", current_bar_idx=16, cooldown_days=5) == False (D+6 earliest re-entry per D-21)
    - test_cooldown_unknown_ticker: is_cooling("BBB", 20, 5) == False
    - test_cooldown_mdm_sell_exempt: document via comment + test that the CALLER (engine) is responsible for not calling register() on MDM SELL exits. Sanity test: register was never called → is_cooling returns False. Per D-20 MDM SELL is exempt.
  </behavior>
  <action>
    Create `tests/strategies/portfolio/test_cooldown.py` with the 4 tests above, importing `CooldownRegistry` from `strategies.portfolio.state`. Each test builds a fresh `CooldownRegistry()`. Add a module-level docstring noting that D-20 MDM SELL exemption is enforced at the engine layer, not this class, and the engine plan must not call register() for MDM SELL exits.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_cooldown.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "def test_cooldown_allows_d_plus_6" tests/strategies/portfolio/test_cooldown.py matches
    - grep "MDM SELL" tests/strategies/portfolio/test_cooldown.py matches
    - pytest exits 0 with ≥4 tests passed
  </acceptance_criteria>
  <done>Cooldown tests green; D-21 D+6 semantics locked in by test.</done>
</task>

</tasks>

<verification>
uv run pytest tests/strategies/portfolio/test_microstructure.py tests/strategies/portfolio/test_costs.py tests/strategies/portfolio/test_cooldown.py -x -q
</verification>

<success_criteria>
- All microstructure, cost, and cooldown tests green
- Pure functions, no cross-module state
- Matches D-17..D-22 numerics exactly
</success_criteria>

<output>
After completion, create `.planning/phases/31-multi-stock-portfolio-engine/31-02-SUMMARY.md`
</output>
