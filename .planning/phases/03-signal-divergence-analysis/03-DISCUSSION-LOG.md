# Phase 3: Signal Divergence Analysis - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 03-signal-divergence-analysis
**Areas discussed:** Signal matching logic, Divergence classification, Visual overlay design, Comparison scope

---

## Signal Matching Logic

### State-to-signal mapping
| Option | Description | Selected |
|--------|-------------|----------|
| State-to-signal mapping | Map HOLDING->Buy, SHORT->Sell, CASH+WAITING_SELL->Cash. Compare state transitions against published signal changes. | ✓ |
| Transition-event matching | Extract transition events from both model and published, match events by date. | |
| Daily state comparison | For every trading day, compare model's active state vs published signal's active state. | |

**User's choice:** State-to-signal mapping
**Notes:** Most natural fit since published signals represent position state, not actions.

### Timing tolerance
| Option | Description | Selected |
|--------|-------------|----------|
| Exact date match only | Model signal on date X only matches published signal on date X. | ✓ |
| Window match (+/-N days) | Configurable window for near matches. | |
| Both metrics | Report exact and window match rates side by side. | |

**User's choice:** Exact date match only

### Match metrics
| Option | Description | Selected |
|--------|-------------|----------|
| Match rate + per-type breakdown | Overall match rate plus separate rates for Buy, Sell, Cash. | ✓ |
| Match rate + timing offset stats | Overall rate plus average/median timing offset. | |
| Full confusion matrix | NxN matrix of published vs model signal types. | |

**User's choice:** Match rate + per-type breakdown

### Engine design
| Option | Description | Selected |
|--------|-------------|----------|
| Reusable module in core/ | Create core/signal_comparator.py. Phase 4 reuses directly. | ✓ |
| Standalone analysis script | Single script in analysis/. Simpler but less reusable. | |
| You decide | Claude picks during implementation. | |

**User's choice:** Reusable module in core/

---

## Divergence Classification

### Classification taxonomy
| Option | Description | Selected |
|--------|-------------|----------|
| Four-type taxonomy | THRESHOLD, TIMING, STRUCTURAL, IRREPRODUCIBLE. | ✓ |
| Simple match/mismatch | Just flag as mismatch without categorization. | |
| Two-level: auto + manual | Auto-classify detectable types, flag rest for manual review. | |

**User's choice:** Four-type taxonomy

### Classification method
| Option | Description | Selected |
|--------|-------------|----------|
| Auto with heuristics | Classify via rules: +/-5 days -> TIMING, Cash state -> STRUCTURAL, near threshold -> THRESHOLD, else -> IRREPRODUCIBLE. | ✓ |
| Manual annotation | Generate list, manually label each divergence. | |
| Auto + manual override | Auto-classify first, allow manual corrections. | |

**User's choice:** Auto with heuristics

### Report format
| Option | Description | Selected |
|--------|-------------|----------|
| CSV + text summary | Detailed CSV per divergence plus text summary with counts. | ✓ |
| Markdown report only | Structured markdown with tables. | |
| DataFrame output only | Return pandas DataFrame, render in scripts/notebooks. | |

**User's choice:** CSV + text summary

---

## Visual Overlay Design

### Chart structure
| Option | Description | Selected |
|--------|-------------|----------|
| Price + dual signal tracks | Main price panel, two color-coded signal tracks below. | ✓ |
| Single chart with markers | Price with triangle markers for signals. | |
| Side-by-side subplots | Two separate stacked price charts. | |

**User's choice:** Price + dual signal tracks

### Divergence highlighting
| Option | Description | Selected |
|--------|-------------|----------|
| Shaded divergence zones | Light red/pink vertical bands where signals disagree. | ✓ |
| Marker annotations only | Diamond/X markers at divergence dates. | |
| No extra highlighting | Let dual track color differences speak for themselves. | |

**User's choice:** Shaded divergence zones

### Output type
| Option | Description | Selected |
|--------|-------------|----------|
| Script generating PNG | Script in analysis/ generating high-res PNG. | |
| Notebook with inline plots | Jupyter notebook with interactive matplotlib. | |
| Both script and notebook | Script for canonical chart, notebook for exploration. | ✓ |

**User's choice:** Both script and notebook

---

## Comparison Scope

### Signal set
| Option | Description | Selected |
|--------|-------------|----------|
| NASDAQ signals | Compare against nasdaq_signals.csv. Most direct validation. | ✓ |
| Both NASDAQ and TECL | Run comparison against both independently. | |
| TECL signals only | TECL has most detailed history. | |

**User's choice:** NASDAQ signals

### Time period
| Option | Description | Selected |
|--------|-------------|----------|
| Full period 2019-2026 | Entire published signal range. | ✓ |
| Split: 2019 baseline + 2020-2026 focus | Separate scores for transition year vs steady state. | |
| 2017-2026 including pre-change | Full model run with scoring where published signals exist. | |

**User's choice:** Full period 2019-2026

### Data source for classic model
| Option | Description | Selected |
|--------|-------------|----------|
| Unified DataLoader from core/ | Use core/data_loader.py with market='nasdaq'. | ✓ |
| Adapt classic engine's loader | Modify strategies/mdm_classic/data_loader.py for NASDAQ. | |
| You decide | Claude picks during implementation. | |

**User's choice:** Unified DataLoader from core/

---

## Claude's Discretion

- Exact heuristic thresholds for auto-classification
- Internal data structures for comparison results
- Chart styling details
- Notebook structure and cell organization
- Text summary formatting

## Deferred Ideas

None — discussion stayed within phase scope
