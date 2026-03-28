"""
Tests for the signal divergence analysis pipeline.

Validates that analysis/signal_divergence.py produces correct output files:
  - output/divergence_report.csv
  - output/divergence_summary.txt
  - output/signal_overlay.png
"""

import os
import sys
import subprocess
from pathlib import Path

import pytest
import pandas as pd

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / 'output'


@pytest.fixture(scope="module", autouse=True)
def run_pipeline():
    """Run the divergence analysis pipeline once for all tests in this module."""
    from analysis.signal_divergence import main
    main()
    yield


def test_script_runs():
    """Pipeline produces divergence_report.csv."""
    csv_path = OUTPUT_DIR / 'divergence_report.csv'
    assert csv_path.exists(), f"Expected {csv_path} to exist after running pipeline"


def test_csv_format():
    """CSV has exactly the required columns."""
    csv_path = OUTPUT_DIR / 'divergence_report.csv'
    df = pd.read_csv(csv_path)
    expected_cols = ['date', 'published_signal', 'model_signal', 'divergence_type', 'context']
    assert list(df.columns) == expected_cols, f"Expected columns {expected_cols}, got {list(df.columns)}"


def test_summary_exists():
    """Summary text file exists and contains match rate."""
    summary_path = OUTPUT_DIR / 'divergence_summary.txt'
    assert summary_path.exists(), f"Expected {summary_path} to exist"
    content = summary_path.read_text(encoding='utf-8')
    assert 'Match rate:' in content, "Summary should contain 'Match rate:'"


def test_chart_exists():
    """Chart PNG exists and is of reasonable size."""
    chart_path = OUTPUT_DIR / 'signal_overlay.png'
    assert chart_path.exists(), f"Expected {chart_path} to exist"
    size = chart_path.stat().st_size
    assert size > 10_000, f"Chart PNG is too small ({size} bytes), expected > 10KB"


def test_divergence_types_valid():
    """All divergence_type values are from the expected set."""
    csv_path = OUTPUT_DIR / 'divergence_report.csv'
    df = pd.read_csv(csv_path)
    valid_types = {'TIMING', 'STRUCTURAL', 'THRESHOLD', 'IRREPRODUCIBLE'}
    actual_types = set(df['divergence_type'].dropna().unique())
    assert actual_types.issubset(valid_types), (
        f"Invalid divergence types: {actual_types - valid_types}"
    )


def test_script_produces_png():
    """Running script as subprocess produces the PNG output."""
    # Remove existing PNG to verify fresh generation
    chart_path = OUTPUT_DIR / 'signal_overlay.png'
    if chart_path.exists():
        chart_path.unlink()

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'analysis' / 'signal_divergence.py')],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert chart_path.exists(), "Script should produce signal_overlay.png"
    size = chart_path.stat().st_size
    assert size > 10_000, f"Chart PNG too small ({size} bytes)"
