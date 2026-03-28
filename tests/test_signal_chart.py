"""
Tests for the signal overlay Jupyter notebook structure.

Validates that notebooks/signal_overlay.ipynb exists, is valid JSON,
and contains the expected cells for interactive exploration.
"""

import json
from pathlib import Path

import pytest


NOTEBOOK_PATH = Path(__file__).resolve().parent.parent / 'notebooks' / 'signal_overlay.ipynb'


def test_notebook_exists():
    """Notebook exists and is valid JSON with 'cells' key."""
    assert NOTEBOOK_PATH.exists(), f"Expected {NOTEBOOK_PATH} to exist"
    with open(NOTEBOOK_PATH, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    assert 'cells' in nb, "Notebook JSON must have a 'cells' key"


def test_notebook_has_cells():
    """Notebook has at least 8 cells."""
    with open(NOTEBOOK_PATH, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    assert len(nb['cells']) >= 8, f"Expected at least 8 cells, got {len(nb['cells'])}"


def test_notebook_has_imports():
    """At least one code cell contains the signal_comparator import."""
    with open(NOTEBOOK_PATH, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    code_cells = [c for c in nb['cells'] if c.get('cell_type') == 'code']
    found = any(
        'from core.signal_comparator import' in ''.join(c.get('source', []))
        for c in code_cells
    )
    assert found, "Expected at least one code cell with 'from core.signal_comparator import'"
