---
phase: 46-ab-oos-validation-hard-gate
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - analysis/validate_v10.py
findings:
  critical: 2
  warning: 8
  info: 7
  total: 17
status: issues_found
---

# Phase 46: Code Review Report

**Reviewed:** 2026-05-11
**Depth:** standard
**Files Reviewed:** 1 (`analysis/validate_v10.py`, 1149 lines)
**Status:** issues_found

## Summary

`analysis/validate_v10.py` wires the v10.0 HARD-acceptance gate pipeline for the VN30 milestone. Overall structure is sound: scenarios are built via `dataclasses.replace` (immutable), gate helpers are pure, the orchestrator preserves "no short-circuit + always write artifacts" discipline (D-06), and the verdict-string contract (D-09) is honored by emitting `VERDICT_PASS`/`VERDICT_FAIL` on a bare `log()` line so it remains greppable.

However the script has not yet executed end-to-end (Plan 46-04 is pending Windows App Control fix), and adversarial reading surfaces several real defects that would only manifest under uncommon-but-realistic paths:

1. A latent **`TypeError: NoneType is not subscriptable`** in `write_validation_report` when the `+all` full-period run errors — this **defeats the D-06 "always write artifacts" guarantee** for the failure mode the discipline was specifically designed to handle.
2. `run_parity_gate`'s docstring promises **"NEVER raises"** but only catches two of the realistic exception classes; subprocess errors like `PermissionError`, `OSError`, or `subprocess.SubprocessError` (and others) will propagate and abort the pipeline before report artifacts are written.

Several quality concerns also surface: emoji glyphs (`✓ ✗ ❌`) violate the project-wide "no emojis in code/print/logging" rule from `AGENTS.md`; the pytest summary regex is fragile (will mis-match strings like "0 passed" appearing in arbitrary stdout content); a hardcoded `'2025-12-01'` data-availability assert is inconsistent with `OOS_END = '2026-03-31'`; literal `999` is duplicated in report text instead of referencing `Z_EXTREME_POSITIVE`; and `bool(raw_accepted)` on the walk-forward CSV row can misclassify `NaN` as `True`.

## Critical Issues

### CR-001: `write_validation_report` raises `TypeError` if `+all` scenario errored during VAL-01

**File:** `analysis/validate_v10.py:809`
**Issue:** Line 809 unconditionally indexes:

```python
val_02_pass = gate_results['val_02_hard_gate'][hg_scenario]['passed']
```

where `hg_scenario = '+all'`. In `main()` (lines 1070-1086), `hard_gate_per_scenario['+all']` is explicitly set to `None` if the `+all` run errored (line 1074) or produced an OOS slice of fewer than 2 rows (line 1080). Subscripting `None['passed']` raises `TypeError: 'NoneType' object is not subscriptable`, propagates up to `main()`, and **prevents `write_validation_report` from completing** — directly violating D-06 ("all 3 artifacts write even on early fails"). The third deliverable (`output/v10_validation_report.txt`) will be missing or partially written on the very failure mode the discipline guards against.

The same risk exists at line 853 inside the `for name in OOS_SCENARIO_SUBSET` loop, but that branch IS guarded by `if verdict is None: log(...); continue`. The unguarded access is only at line 809 in the pre-compute block.

**Fix:**
```python
# Determine overall pass/fail
val_01_pass = gate_results['val_01_ab_complete']
hg_scenario = gate_results['hard_gate_scenario']
hg_result = gate_results['val_02_hard_gate'].get(hg_scenario)
val_02_pass = hg_result['passed'] if hg_result is not None else False
val_03_pass = gate_results['val_03_walkforward']['passed_gate']
val_04_pass = gate_results['val_04_parity']['passed']
all_passed = val_01_pass and val_02_pass and val_03_pass and val_04_pass
```

This makes "+all run failed" → VAL-02 FAIL → overall FAIL → `VERDICT_FAIL` written. The report artifact is preserved.

### CR-002: `run_parity_gate` docstring claims "NEVER raises" but only catches 2 of the realistic subprocess exception classes

**File:** `analysis/validate_v10.py:486-487,498-516`
**Issue:** Docstring states:

> Does NOT raise — subprocess failures (pytest not installed, test file missing, timeout) are captured in the return dict for report inclusion.

But the `try` block (lines 497-516) only catches `subprocess.TimeoutExpired` and `FileNotFoundError`. Any of the following will escape and abort `main()` before `write_validation_report` runs:
- `PermissionError` (uv binary present but not executable; Windows App Control denies _ctypes.pyd — the exact scenario blocking Plan 46-04 today)
- `OSError` (parent dir of `cwd` missing/inaccessible)
- `subprocess.SubprocessError` (other subprocess-level issues, e.g., `CalledProcessError` if `check=True` were ever added)
- `UnicodeDecodeError` (stdout contains non-UTF-8 bytes under `text=True`)
- `MemoryError`, `ValueError` from malformed arguments, etc.

Combined with the no-short-circuit D-06 discipline, this gap means a Windows-App-Control PermissionError (the failure mode the user is actively encountering) raises out of the pipeline, **none of the three deliverables are written**, and the verdict string is never emitted — Phase 47 cannot branch.

**Fix:**
```python
try:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
    )
    rc = proc.returncode
    stdout = proc.stdout
    stderr = proc.stderr
except subprocess.TimeoutExpired as exc:
    rc = -1
    stdout = (exc.stdout or '') + f"\n[TIMEOUT after {timeout_sec}s]"
    stderr = (exc.stderr or '') + f"\n[TIMEOUT after {timeout_sec}s]"
except FileNotFoundError as exc:
    rc = -2
    stdout = ''
    stderr = f"[subprocess FileNotFoundError: {exc}]"
except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
    # PermissionError (OSError subclass), Windows App Control denials, etc.
    rc = -3
    stdout = ''
    stderr = f"[subprocess {type(exc).__name__}: {exc}]"
```

Alternatively, broaden to `except Exception as exc:` if the contract truly is "never raise" — but the targeted-except form is preferable so KeyboardInterrupt still aborts cleanly.

## Warnings

### WR-001: Emoji/glyph characters in source violate project "no emojis" rule

**File:** `analysis/validate_v10.py:348-349, 1048`
**Issue:** `AGENTS.md` (loaded via `CLAUDE.md`) states: "Never use emojis in code or in print statements or logging." The file contains:

- Line 348: `cagr_glyph = '✓' if cagr_pass else '✗'`
- Line 349: `maxdd_glyph = '✓' if max_dd_pass else '✗'`
- Line 1048: `print(f'\n❌ D-02 ISOLATION LEAK: {exc}')`

The `✓ ✗ ❌` glyphs are Unicode symbols that the project rule treats as emojis (they're rendered as colorful emojis on most terminals). These also force the file's stdout reconfiguration code (lines 35-38) to exist solely to render them on Windows — remove the glyphs and the `reconfigure` dance becomes optional.

**Fix:**
```python
cagr_glyph = 'PASS' if cagr_pass else 'FAIL'
maxdd_glyph = 'PASS' if max_dd_pass else 'FAIL'
# ...
print(f'\nD-02 ISOLATION LEAK: {exc}')
```

(The Vietnamese-arrow `→` character at lines 7, 50, 594, 663, 820, 844, 1066 is also non-ASCII but is conventional for "to" in technical text and is widely accepted; the explicit emoji-coded glyphs are the violation.)

### WR-002: Pytest summary regex is fragile — matches "N passed/failed" anywhere in stdout, not just the summary line

**File:** `analysis/validate_v10.py:532-537`
**Issue:** The regex `r'(\d+) passed'` / `r'(\d+) failed'` uses `re.search` over the entire stdout, returning the FIRST match. If pytest's `-v` verbose output contains text like `test_assertion_failed_when_value_passed` in a test name, or if a test prints a string like "3 passed checks" as part of its output, the parser will lock onto the wrong number. Pytest's actual summary line has a distinctive prefix (`=== N passed in T.Ts ===` or `=== N failed, M passed in T.Ts ===`).

This is a quality concern not a correctness one (`passed: bool` uses `rc == 0` directly, which is correct); however, the `tests_passed`/`tests_failed` fields appear in the validation report and could mislead the auditor.

**Fix:**
```python
# Anchor to pytest summary line(s) — they appear after a row of '=' signs
summary_match = _re.search(
    r'=+\s*(?:(\d+)\s+failed)?[,\s]*(?:(\d+)\s+passed)?.*?\sin\s+[\d.]+s',
    stdout,
)
if summary_match:
    failed_str, passed_str = summary_match.groups()
    tests_passed = int(passed_str) if passed_str else (0 if rc == 0 else -1)
    tests_failed = int(failed_str) if failed_str else 0
```

### WR-003: Data-availability assert hardcodes `2025-12-01` while OOS window ends `2026-03-31`

**File:** `analysis/validate_v10.py:999-1002`
**Issue:**
```python
assert df_full['date'].max() >= pd.Timestamp('2025-12-01'), (
    f"Insufficient data: max date {df_full['date'].max()} — OOS window "
    f"requires through {OOS_END}"
)
```
The assert allows data through Dec 1 2025 to pass, but the error message says OOS requires data through `OOS_END = '2026-03-31'`. A run with data ending 2025-12-15 would slip past the guard with only ~3 weeks of OOS data, producing a degenerate OOS slice and pollution-by-near-empty CAGR/MaxDD/Sharpe values.

Also, using `assert` for production-flow validation is risky because Python with `-O` flag strips asserts; AGENTS.md "do not program defensively" applies, but this is a load-bearing precondition.

**Fix:**
```python
required_max = pd.Timestamp(OOS_END)
if df_full['date'].max() < required_max:
    raise RuntimeError(
        f"Insufficient data: max date {df_full['date'].max().date()} < "
        f"OOS_END {OOS_END}. Re-pull VN30 data."
    )
```

### WR-004: `bool(raw_accepted)` mis-classifies NaN and non-empty-string falsy values

**File:** `analysis/validate_v10.py:433-437`
**Issue:**
```python
raw_accepted = row['accepted']
if isinstance(raw_accepted, str):
    accepted = raw_accepted.strip().lower() == 'true'
else:
    accepted = bool(raw_accepted)
```

Three classes of CSV state can mislead this:
1. `bool(float('nan'))` returns `True` (NaN is not falsy), so a row with missing accepted value reports `accepted=True`.
2. If pandas loads the column as `numpy.bool_`, `bool(np.False_)` is `False` — OK; but if loaded as object-dtype containing strings `'True'`/`'False'`, the isinstance branch is correct.
3. If pandas loads the column with values `'0'`/`'1'` (string), `bool('0') == True` (non-empty string).

Since the walk-forward CSV is internal Phase 45 output it's unlikely to hit edge cases, but the lookup is on a "never re-run the sweep" external data file (D-07) — any future schema drift in Phase 45 affects this gate.

**Fix:**
```python
if isinstance(raw_accepted, str):
    accepted = raw_accepted.strip().lower() == 'true'
elif pd.isna(raw_accepted):
    accepted = False  # Treat missing as "not accepted"
else:
    accepted = bool(raw_accepted)
```

Apply analogous fix to lines 443-446 for the aggregate count.

### WR-005: Buy & Hold MaxDD/CAGR can raise on negative cumulative returns

**File:** `analysis/validate_v10.py:1052-1054`
**Issue:**
```python
bh_total_ret = (df_full['close'].iloc[-1] / df_full['close'].iloc[0] - 1) * 100
bh_years = (df_full['date'].iloc[-1] - df_full['date'].iloc[0]).days / 365.25
bh_cagr = ((1 + bh_total_ret / 100) ** (1 / bh_years) - 1) * 100 if bh_years > 0 else 0.0
```

If VN30 ever closes below its start price (e.g., a market crash slice), `(1 + bh_total_ret/100)` is negative, and `(negative) ** (1/bh_years)` for non-integer `1/bh_years` raises `ValueError: negative number cannot be raised to a fractional power` (or returns complex with `numpy`). For the full 2015-2026 window today this is safe, but if anyone re-runs the script on a stress-test window (e.g., 2022 only) it crashes.

Also `df_full['close'].iloc[0]` could be zero in degenerate data, causing `ZeroDivisionError`.

**Fix:**
```python
first_close = float(df_full['close'].iloc[0])
last_close = float(df_full['close'].iloc[-1])
if first_close <= 0:
    bh_total_ret = float('nan')
    bh_cagr = float('nan')
else:
    bh_total_ret = (last_close / first_close - 1) * 100
    if bh_years > 0 and (1 + bh_total_ret / 100) > 0:
        bh_cagr = ((1 + bh_total_ret / 100) ** (1 / bh_years) - 1) * 100
    else:
        bh_cagr = float('nan')
```

### WR-006: `os.makedirs(os.path.dirname(path), exist_ok=True)` raises if path lacks a dirname

**File:** `analysis/validate_v10.py:676, 771, 958`
**Issue:** When callers override `report_path` / `csv_path` with a bare filename (no directory component), `os.path.dirname('foo.txt')` returns `''`. `os.makedirs('', exist_ok=True)` raises `FileNotFoundError: [WinError 3]` on Windows (and `FileNotFoundError` on POSIX too). This is only hit by test code passing bare filenames, but the Plan 46-03 test harness does exactly that in one referenced fixture path.

**Fix:**
```python
parent = os.path.dirname(path)
if parent:
    os.makedirs(parent, exist_ok=True)
```

Apply consistently at all three write sites (lines 676, 771, 958).

### WR-007: `oos_slice = res_full[res_full['date'] >= OOS_START]` relies on implicit str-to-Timestamp coercion

**File:** `analysis/validate_v10.py:1077`
**Issue:** `OOS_START = '2025-01-01'` is a Python str. `res_full['date']` is a `pd.Timestamp` Series (set by `DataLoader` and `build_indicator_dataframe`). Pandas does coerce on `>=` comparison, but the coercion is locale-sensitive and silently succeeds even when the string format does not match — e.g., a string like `'2025/01/01'` would still produce a valid Timestamp; a typo like `'01-01-2025'` would not, but `pd.Timestamp('01-01-2025')` returns January 1, 2025 OR January 1, 2001 depending on `dayfirst` heuristics. For reproducibility across pandas versions, prefer an explicit Timestamp:

**Fix:**
```python
oos_start_ts = pd.Timestamp(OOS_START)
# ...
oos_slice = res_full[res_full['date'] >= oos_start_ts].copy().reset_index(drop=True)
```

(Define `oos_start_ts` once outside the loop.)

### WR-008: Hardcoded `999` literal in report text instead of `Z_EXTREME_POSITIVE` reference

**File:** `analysis/validate_v10.py:600, 603, 605`
**Issue:**
```python
log(f'Scenario isolation (D-02): +DXY / +EEM / +SBV-regime disable '
    f'OTHER factors via |z| >= 999 extremes and SBV multiplier = 2.5.')
log(f'  observed max |dxy_z| = {extremes_check["dxy_z_abs_max"]:.3f} '
    f'(headroom to 999: {999 - extremes_check["dxy_z_abs_max"]:.1f})')
log(f'  observed max |eem_z| = {extremes_check["eem_z_abs_max"]:.3f} '
    f'(headroom to 999: {999 - extremes_check["eem_z_abs_max"]:.1f})')
```

If anyone bumps `Z_EXTREME_POSITIVE` (the `verify_extremes_never_trigger` error message in lines 242-249 explicitly tells future maintainers to do this if observed |z| breaches the cap), the report text silently lies. Likewise `2.5` is hardcoded in the report string while the constant is `SBV_MULTIPLIER_NOOP`.

**Fix:**
```python
log(f'Scenario isolation (D-02): +DXY / +EEM / +SBV-regime disable '
    f'OTHER factors via |z| >= {Z_EXTREME_POSITIVE} extremes and '
    f'SBV multiplier = {SBV_MULTIPLIER_NOOP}.')
log(f'  observed max |dxy_z| = {extremes_check["dxy_z_abs_max"]:.3f} '
    f'(headroom to {Z_EXTREME_POSITIVE}: '
    f'{Z_EXTREME_POSITIVE - extremes_check["dxy_z_abs_max"]:.1f})')
log(f'  observed max |eem_z| = {extremes_check["eem_z_abs_max"]:.3f} '
    f'(headroom to {Z_EXTREME_POSITIVE}: '
    f'{Z_EXTREME_POSITIVE - extremes_check["eem_z_abs_max"]:.1f})')
```

## Info

### IN-001: Imports inside function body for `time` and `re`

**File:** `analysis/validate_v10.py:489-490`
**Issue:**
```python
def run_parity_gate(timeout_sec: int = 300) -> dict:
    """..."""
    import time
    import re as _re
```

The standard-library imports are deferred to function scope. The rest of the file imports `json`, `subprocess`, `traceback` etc. at module top. Inconsistent style; minor cost (microseconds on first call) but pollutes the "explicit import contract" reading at the top.

**Fix:** Move `import time` and `import re` to module-level imports (lines 24-30). Drop the `as _re` alias since there's no name conflict.

### IN-002: `verify_extremes_never_trigger` uses `assert` rather than explicit raise

**File:** `analysis/validate_v10.py:241-250`
**Issue:** The assertion is load-bearing for D-02 correctness (an "isolation leak" silently corrupts +DXY/+EEM/+SBV semantics). Running with `python -O` strips asserts. Convert to explicit `raise AssertionError(...)` or `ValueError`.

**Fix:**
```python
if dxy_abs_max >= Z_EXTREME_POSITIVE:
    raise AssertionError(
        f"observed |dxy_z| max = {dxy_abs_max:.3f} >= Z_EXTREME_POSITIVE "
        f"({Z_EXTREME_POSITIVE}); isolation extremes LEAK ..."
    )
# similar for eem
```

### IN-003: `main()` calls `sys.exit()` making the module hard to test

**File:** `analysis/validate_v10.py:1145`
**Issue:** `main()` ends with `sys.exit(exit_code)`. Unit tests importing `main` will exit the test runner. Convention is to have `main()` return the exit code and `__main__` block call `sys.exit(main())`.

**Fix:**
```python
def main() -> int:
    # ... existing body up to:
    exit_code = 0 if all_passed else 1
    print(f'\nFINAL VERDICT: {"PASS" if all_passed else "FAIL"} → exit {exit_code}')
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
```

This also keeps the no-hardcoded-`sys.exit(0)` rule (no literal "0" or "1" appears next to `sys.exit`).

### IN-004: `extremes_check` initial fallback dict duplicates the success-path key set

**File:** `analysis/validate_v10.py:1039-1040`
**Issue:** When `+all` scenario errors, `extremes_check` is initialized with three NaN keys to match the success-path shape. This works but the duplication is fragile — if `verify_extremes_never_trigger` gains a 4th return key, the fallback gets out of sync. Consider a single factory:

```python
def _empty_extremes_check() -> dict:
    return {'dxy_z_abs_max': float('nan'), 'eem_z_abs_max': float('nan'),
            'headroom': float('nan')}
```

### IN-005: `print` and `log` mix in writer functions, no logging module

**File:** `analysis/validate_v10.py` throughout
**Issue:** Console output uses `print()` and report writers use an in-function `log()` helper appending to a list. No use of Python `logging`. Matches the project convention (`CLAUDE.md` notes: "Console output via `print()` statements"). Not a defect — flagged here only to document the pattern is intentional and discoverable.

### IN-006: `traceback` import is used only inside one except block

**File:** `analysis/validate_v10.py:29, 1026`
**Issue:** `traceback` is imported at module top but used only in `main()`'s VAL-01 loop fallback. Acceptable, but a sharper reader might want a comment marking the single use-site, or move the import next to the use. Minor.

### IN-007: `WALKFORWARD_VN30_PRESET_COMBO = 'stage3_all_three-c1'` comment vs CONTEXT mismatch

**File:** `analysis/validate_v10.py:63-69`
**Issue:** The module comment block accurately documents that `stage3_all_three-c1` matches VN30_PRESET defaults, and explains that c0/c1/c2 trade identically because the SBV multiplier variation saturates. However the `46-CONTEXT.md` D-07 cite (line 91 of CONTEXT) names `stage3_all_three-c0` as "the row representing +all defaults". This is not a bug — the in-code comment supersedes by being more precise — but a downstream reader cross-referencing the context will see the c0/c1 difference and may flag it. Consider adding a one-line note: `# NOTE: CONTEXT D-07 cites c0; we use c1 because c1's sbv_mult=1.5 exactly equals VN30_PRESET.sbv_tightening_stop_loss_max_multiplier (c0 uses 1.0).`

---

_Reviewed: 2026-05-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
