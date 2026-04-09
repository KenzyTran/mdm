"""Phase 32 scaffold env-check tests."""
from __future__ import annotations

import multiprocessing


def _double(x: int) -> int:
    """Top-level helper (must be picklable for Windows spawn)."""
    return x * 2


def test_imports_pyarrow() -> None:
    import pyarrow

    assert pyarrow.__version__


def test_imports_tqdm() -> None:
    import tqdm

    assert tqdm.__version__


def test_multiprocessing_pool() -> None:
    with multiprocessing.Pool(2) as pool:
        result = pool.map(_double, [1, 2, 3])
    assert result == [2, 4, 6]
