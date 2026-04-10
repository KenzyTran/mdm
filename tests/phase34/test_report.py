"""Tests for v7.0 performance report (BT-05, BT-06, BT-07).

BT-05: Complete performance metrics (10 standard metrics + profit_factor)
BT-06: 5-way benchmark comparison (vnindex_bh, vn30_bh, mdm_only_index, deposit_12m, sjc_gold)
BT-07: Inflation-adjusted real CAGR for strategy and all benchmarks

Usage: uv run pytest tests/phase34/test_report.py -x -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
REPORT_JSON = REPO_ROOT / "docs" / "audits" / "phase34" / "v7_report.json"
REPORT_MD = REPO_ROOT / "docs" / "audits" / "phase34" / "v7_report.md"
SCRIPT = REPO_ROOT / "analysis" / "generate_v7_report.py"

_report: dict | None = None


def _load_report() -> dict:
    global _report
    if _report is None:
        if not REPORT_JSON.exists():
            # Run script to generate report
            result = subprocess.run(
                ["uv", "run", "python", str(SCRIPT)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                pytest.fail(
                    f"generate_v7_report.py failed:\nSTDOUT:\n{result.stdout}\n"
                    f"STDERR:\n{result.stderr}"
                )
        with open(REPORT_JSON) as f:
            _report = json.load(f)
    return _report


@pytest.fixture(scope="module")
def report() -> dict:
    """Load v7_report.json, running the script if needed."""
    return _load_report()


REQUIRED_STRATEGY_KEYS = {
    "CAGR",
    "Sharpe_rf3",
    "MaxDD",
    "MaxDD_duration_days",
    "hit_rate",
    "profit_factor",
    "avg_hold_days",
    "turnover",
    "total_cost_drag_pct",
    "num_trades",
}

REQUIRED_BENCHMARKS = {
    "vnindex_bh",
    "vn30_bh",
    "mdm_only_index",
    "deposit_12m",
    "sjc_gold",
}


def test_metrics_complete(report: dict) -> None:
    """BT-05: All 10 strategy metrics are present in the report."""
    strategy = report["strategy"]
    missing = REQUIRED_STRATEGY_KEYS - set(strategy.keys())
    assert not missing, f"Missing strategy metrics: {missing}"


def test_profit_factor_positive(report: dict) -> None:
    """BT-05: profit_factor must be a float greater than 0."""
    pf = report["strategy"]["profit_factor"]
    assert isinstance(pf, (int, float)), f"profit_factor is not numeric: {type(pf)}"
    assert pf > 0, f"profit_factor must be > 0, got {pf}"


def test_benchmarks(report: dict) -> None:
    """BT-06: Exactly 5 benchmarks, each with at least a CAGR key."""
    benchmarks = report["benchmarks"]
    actual_keys = set(benchmarks.keys())
    assert actual_keys == REQUIRED_BENCHMARKS, (
        f"Expected benchmarks {REQUIRED_BENCHMARKS}, got {actual_keys}"
    )
    for name, val in benchmarks.items():
        assert "CAGR" in val, f"Benchmark '{name}' missing CAGR key"


def test_real_cagr(report: dict) -> None:
    """BT-07: real_CAGR present in strategy and all benchmarks; real < nominal for positive inflation."""
    strategy = report["strategy"]
    assert "real_CAGR" in strategy, "strategy missing real_CAGR"

    nominal_cagr = strategy["CAGR"]
    real_cagr = strategy["real_CAGR"]
    assert real_cagr < nominal_cagr, (
        f"strategy real_CAGR ({real_cagr:.4f}) should be < nominal CAGR ({nominal_cagr:.4f})"
    )

    benchmarks = report["benchmarks"]
    for name, val in benchmarks.items():
        assert "real_CAGR" in val, f"Benchmark '{name}' missing real_CAGR"
        bm_nominal = val["CAGR"]
        bm_real = val["real_CAGR"]
        assert bm_real < bm_nominal, (
            f"Benchmark '{name}' real_CAGR ({bm_real:.4f}) should be < nominal CAGR ({bm_nominal:.4f})"
        )


def test_markdown_exists() -> None:
    """BT-06/BT-07: Markdown report exists and contains required sections."""
    assert REPORT_MD.exists(), f"Markdown report not found: {REPORT_MD}"
    content = REPORT_MD.read_text(encoding="utf-8")
    assert "Benchmark Comparison" in content, (
        "v7_report.md missing '## Benchmark Comparison' section"
    )
    assert "profit_factor" in content.lower() or "Profit Factor" in content, (
        "v7_report.md missing profit_factor mention"
    )
