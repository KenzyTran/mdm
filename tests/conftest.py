"""
Shared test configuration and fixtures for MDM project tests.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work from tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Path to test fixture files
FIXTURES = Path(__file__).parent / 'fixtures'
