# Phase 4: MDM v2 Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 04-mdm-v2-engine
**Areas discussed:** Cash state behavior, v2 engine architecture, Hypothesis testing workflow, Parameter sweep design

---

## Cash State Behavior

### Cash trigger from Buy

| Option | Description | Selected |
|--------|-------------|----------|
| DD-count threshold | Cash triggers when DD count hits configurable threshold (3-4 DD). Parameterizable. | |
| Price-action heuristic | Cash triggers on specific price patterns (close below MA10, failed rally). | |
| Combined conditions | Cash triggers when EITHER DD count OR price action conditions are met. Most flexible. | ✓ |

**User's choice:** Combined conditions
**Notes:** User wants maximum flexibility -- both DD count and price action can independently trigger Cash.

### Cash exit transitions

| Option | Description | Selected |
|--------|-------------|----------|
| FTD/breakout -> Buy, MA breakdown -> Sell | Reuse existing FTD/MA50 breakout for Cash->Buy. New MA breakdown for Cash->Sell. | ✓ |
| Timeout-based | Stay in Cash for N days, then decide based on price trend. | |
| Separate rule set | Cash state has own independent entry/exit rules. | |

**User's choice:** FTD/breakout -> Buy, MA breakdown -> Sell
**Notes:** Keeps signal types consistent with classic engine patterns.

### SHORT state

| Option | Description | Selected |
|--------|-------------|----------|
| Keep SHORT state | Preserve SHORT for Sell signals. Published signals include Sell. | |
| Remove SHORT, Sell = go to Cash | Simplify by treating Sell as going flat (Cash). | ✓ |
| You decide | Claude's discretion | |

**User's choice:** Remove SHORT, Sell = go to Cash
**Notes:** Simplifies state machine to three states: Buy/Cash/Sell-then-Cash.

### Cash scoring

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, Cash is distinct | Cash is third signal type. Match rate counts Cash separately. | ✓ |
| Cash = partial Sell | Cash counts as partial match for Sell (0.5 weight). | |

**User's choice:** Cash is distinct signal type
**Notes:** Directly measures whether model correctly identifies Dr. K's Cash signals.

---

## v2 Engine Architecture

### Code relationship to classic

| Option | Description | Selected |
|--------|-------------|----------|
| Fork into strategies/mdm_v2/ | Copy classic into new package. Classic stays untouched as reference. | ✓ |
| Extend classic with v2 mode flag | Add version parameter to switch behavior. Less duplication but messier. | |
| Abstract base + two implementations | Base class with Classic/V2 subclasses. Cleanest long-term. | |

**User's choice:** Fork into strategies/mdm_v2/
**Notes:** Follows Phase 2 pattern of independent strategy packages.

### Hypothesis/sweep code location

| Option | Description | Selected |
|--------|-------------|----------|
| analysis/hypothesis/ | New subdirectory under analysis/. Follows existing analysis/ pattern. | ✓ |
| scripts/ | Alongside run_backtest.py. Simpler but wrong category. | |
| strategies/mdm_v2/ | Inside strategy package. Tighter coupling. | |

**User's choice:** analysis/hypothesis/
**Notes:** Consistent with analysis/ being for post-backtest research tools.

### Config design

| Option | Description | Selected |
|--------|-------------|----------|
| New MDMV2Config dataclass | Fresh dataclass with v2-specific parameters. Own schema. | ✓ |
| Extend MDMConfig | Add v2 params to existing config. Mixes concerns. | |
| You decide | Claude's discretion | |

**User's choice:** New MDMV2Config dataclass
**Notes:** Clean separation from classic config.

---

## Hypothesis Testing Workflow

### Hypothesis definition

| Option | Description | Selected |
|--------|-------------|----------|
| Config variations | Named MDMV2Config instances with different values. Purely config-driven. | ✓ |
| Rule override functions | Python functions that override engine rules. More expressive. | |
| YAML/JSON rule definitions | External config files. Most portable but adds parsing layer. | |

**User's choice:** Config variations
**Notes:** Simple, trackable, no code changes per hypothesis.

### Results reporting

| Option | Description | Selected |
|--------|-------------|----------|
| CSV + text summary | Results CSV with match rates and params. Plus text summary with ranking. | ✓ |
| Jupyter notebook only | Interactive with inline results and charts. | |
| Both CSV and notebook | CSV for programmatic, notebook for interactive. | |

**User's choice:** CSV + text summary
**Notes:** Consistent with Phase 3 output patterns.

### Structural vs parameter testing

| Option | Description | Selected |
|--------|-------------|----------|
| Parameters only for now | Phase 4 focuses on parameterized tuning. Structural changes tested manually. | ✓ |
| Both parameters and structural | Pluggable rule components. More powerful but more engineering. | |

**User's choice:** Parameters only for now
**Notes:** Keep framework simple for Phase 4.

---

## Parameter Sweep Design

### Search strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Grid search | Exhaustive over defined grid. Reproducible. Already used in optimize_mdm.py. | ✓ |
| Random search | Sample random combinations. Better for large spaces. | |
| Staged: coarse then fine | Two-pass approach. More efficient but more complex. | |

**User's choice:** Grid search
**Notes:** Follows existing optimize_mdm.py pattern.

### Training period

| Option | Description | Selected |
|--------|-------------|----------|
| 2019-2022 train | Post-2019 signals only. Held-out 2023-2026 for Phase 5. | ✓ |
| 2017-2022 train | Includes pre-2019 signals. Larger but may confuse optimization. | |
| You decide | Claude's discretion | |

**User's choice:** 2019-2022 train
**Notes:** Clean separation targeting post-2019 behavior specifically.

### Result ranking

| Option | Description | Selected |
|--------|-------------|----------|
| Match rate only | Rank by overall signal match rate. Per-type shown but not used for ranking. | ✓ |
| Weighted per-type match | Weight Cash/Buy/Sell differently. | |
| Match rate + complexity penalty | Penalize extreme parameter values to avoid overfitting. | |

**User's choice:** Match rate only
**Notes:** Simple and directly aligned with core project value.

---

## Claude's Discretion

- Exact parameter ranges and grid values for the sweep
- Internal state machine implementation details for Cash transitions
- Which classic engine modules to copy vs rewrite for v2
- CSV output formatting and text summary structure
- Hypothesis naming conventions and organization
