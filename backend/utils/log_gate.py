from __future__ import annotations

import os
from typing import Any


def should_print() -> bool:
    """
    Central gate for print noise in test/CI runs.

    - If TESSARIS_TEST_QUIET=1 => suppress prints.
    - Otherwise => allow prints.

    Keep this tiny + dependency-free so it can be imported anywhere.
    """
    return os.getenv("TESSARIS_TEST_QUIET", "") != "1"


def tprint(*args: Any, **kwargs: Any) -> None:
    """
    Tiny gated print. Drop-in replacement for print(...) in noisy modules.
    """
    if should_print():
        print(*args, **kwargs)
